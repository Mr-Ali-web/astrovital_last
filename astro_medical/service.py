"""Mission-level orchestration, independent crew monitoring and shared-cause hypothesis engine."""
from __future__ import annotations
from collections import deque
from threading import RLock
from .database import Database
from .models import Alert, Finding, MissionTelemetry, Telemetry
from .playbooks import NOTICE
from .incidents import IncidentStore, IncidentError
from .rules import assess_member, assess_zone, assess_trends, assess_coverage, correlate, summary_level, SYMPTOM_LABELS
from .sources import DemoSimulator, MissionTelemetrySource, DEFAULT_ROSTER, SCENARIOS, ZONES


class MonitoringService:
    def __init__(self, database: Database, source: MissionTelemetrySource | None = None):
        self.db = database
        self.incidents = IncidentStore(self.db)
        roster = self.db.get_setting("crew_roster", DEFAULT_ROSTER)
        self.source = source or DemoSimulator(roster=roster)
        self._lock = RLock()
        self.earth_link = bool(self.db.get_setting("earth_link", True))
        scenario = self.db.get_setting("scenario", "normal")
        if isinstance(self.source, DemoSimulator):
            self.source.set_scenario(scenario if scenario in SCENARIOS else "normal")
        self.history: deque[MissionTelemetry] = deque(maxlen=20)
        self.last: MissionTelemetry | None = None
        self.alerts: list[Alert] = []
        self.findings: list[Finding] = []
        self._prior_alerts: dict[tuple[str, str, str], str] = {}
        self._prior_findings: dict[str, str] = {}
        self._finding_members: dict[str, tuple[str, ...]] = {}
        self._known_crew_names: dict[str, str] = {
            p["crew_id"]: p["name"] for p in roster
        }
        self.level = "unknown"
        self.step()

    def _event(self, typ: str, severity: str, code: str, message: str,
               scope: str = "mission", subject_id: str = "mission",
               affected_ids: tuple[str, ...] = ()):
        """Attach name snapshots so audit history survives roster removal."""
        subject_name = (self._known_crew_names.get(subject_id) if scope == "crew" else
                        ZONES.get(subject_id) if scope == "zone" else None)
        affected_crew = [
            {"crew_id": cid, "name": self._known_crew_names[cid]}
            for cid in affected_ids if cid in self._known_crew_names
        ]
        self.db.add_event(typ, severity, code, message, scope, subject_id,
                          subject_name=subject_name, affected_crew=affected_crew)
        if self.earth_link:
            self.db.simulate_delivery()

    def step(self) -> dict:
        with self._lock:
            mission = self.source.read()
            self.last = mission
            self._known_crew_names.update({cid: p.name for cid, p in mission.crew.items()})
            self.history.append(mission)
            self.db.save_telemetry(mission)
            alerts: list[Alert] = []
            for person in mission.crew.values():
                alerts.extend(assess_member(person, mission.timestamp))
                alerts.extend(assess_trends(person, list(self.history)))
            for zone_id, points in mission.zones.items():
                alerts.extend(assess_zone(zone_id, points, mission.timestamp))
            expected = {p["crew_id"] for p in getattr(self.source, "roster", self.db.get_setting("crew_roster", DEFAULT_ROSTER))}
            alerts.extend(assess_coverage(mission, expected, set(ZONES)))
            self.findings = correlate(mission, alerts)
            # Correlation findings are shown separately, and logged independently.
            current_alerts = {(a.scope, a.subject_id, a.code): a.severity for a in alerts}
            for a in alerts:
                key = (a.scope, a.subject_id, a.code)
                old = self._prior_alerts.get(key)
                if old != a.severity:
                    self._event("ALERT_OPEN" if old is None else "ALERT_UPDATED", a.severity,
                                a.code, a.title + f" [{a.subject_id}]", a.scope, a.subject_id)
            for key in self._prior_alerts.keys() - current_alerts.keys():
                scope, sid, code = key
                self._event("ALERT_CLEARED", "normal", code, "DEMO ogohlantirish yopildi", scope, sid)
            self._prior_alerts = current_alerts
            next_findings = {f.code: f.level for f in self.findings}
            for f in self.findings:
                old = self._prior_findings.get(f.code)
                if old != f.level:
                    self._event("FINDING_OPEN" if old is None else "FINDING_UPDATED", f.level,
                                f.code, f.title, "mission", "mission", f.affected_crew)
            for code in self._prior_findings.keys() - next_findings.keys():
                self._event("FINDING_CLEARED", "normal", code,
                            "DEMO umumiy tahlil signalining tugashi",
                            affected_ids=self._finding_members.get(code, ()))
            self._prior_findings = next_findings
            self._finding_members = {f.code: f.affected_crew for f in self.findings}
            self.alerts = alerts
            levels = [a.severity for a in alerts] + [f.level for f in self.findings]
            if "critical" in levels:
                self.level = "critical"
            elif "attention" in levels:
                self.level = "attention"
            elif "unknown" in levels:
                self.level = "unknown"
            else:
                self.level = "normal"
            return self.status()

    def status(self) -> dict:
        with self._lock:
            if self.last is None:
                return {"level": "unknown", "mode": "SIMULATION_ONLY"}
            m = self.last
            crew_status = []
            for person in m.crew.values():
                person_alerts = [a for a in self.alerts if a.scope == "crew" and a.subject_id == person.crew_id]
                crew_status.append({"crew_id": person.crew_id, "name": person.name,
                                    "zone_id": person.zone_id, "level": summary_level(person_alerts),
                                    "active_alert_count": len(person_alerts), "vitals": {k: p.as_dict() for k,p in person.vitals.items()},
                                    "symptoms": list(person.symptoms)})
            zone_status = []
            for zone_id, signals in m.zones.items():
                zone_alerts = [a for a in self.alerts if a.scope == "zone" and a.subject_id == zone_id]
                zone_status.append({"zone_id": zone_id, "name": ZONES.get(zone_id, zone_id),
                                    "level": summary_level(zone_alerts), "active_alert_count": len(zone_alerts),
                                    "sensors": {k: p.as_dict() for k,p in signals.items()}})
            first = next(iter(m.crew.values()), None)
            legacy = None
            if first:
                legacy = Telemetry(m.timestamp, m.source, m.scenario, first.vitals,
                                   m.zones.get(first.zone_id, {}), first.symptoms).as_dict()
            return {
                "mode": "SIMULATION_ONLY" if isinstance(self.source, DemoSimulator) else "EXTERNAL_SOURCE_NOT_VALIDATED",
                "medical_approval": "NOT_VALIDATED", "ai_model_enabled": False,
                "notice": NOTICE, "mission": m.as_dict(), "telemetry": legacy,
                "crew": crew_status, "zones": zone_status, "level": self.level,
                "active_alerts": [a.as_dict() for a in self.alerts],
                "shared_findings": [f.as_dict() for f in self.findings],
                "earth_link": self.earth_link, "pending_outbox": self.db.pending_count(),
                "transport": "LOCAL_SIMULATION_NO_REAL_TRANSMISSION",
                "scenarios": SCENARIOS, "symptom_labels": SYMPTOM_LABELS,
                "zone_labels": ZONES, "crew_capacity": 12,
            }

    def set_scenario(self, scenario: str) -> dict:
        with self._lock:
            if not isinstance(self.source, DemoSimulator):
                raise ValueError("Scenario changing works only with DemoSimulator")
            self.source.set_scenario(scenario)
            self.history.clear()  # Prevent previous scenario data from influencing new trends.
            self.db.set_setting("scenario", scenario)
            self._event("SCENARIO", "normal", scenario, f"DEMO ssenariy: {SCENARIOS[scenario]}")
            return self.step()

    def set_link(self, available: bool) -> dict:
        with self._lock:
            if self.earth_link != available:
                self.earth_link = available
                self.db.set_setting("earth_link", available)
                self._event("LINK", "normal", "EARTH_LINK",
                            "Aloqa tiklandi (demo)" if available else "Aloqa uzildi (demo)")
            if available:
                self.db.simulate_delivery()
            return self.status()

    def set_symptoms(self, symptoms: list[str], crew_id: str | None = None) -> dict:
        with self._lock:
            if not isinstance(self.source, DemoSimulator):
                raise ValueError("Demo symptom control only available in simulation")
            cid = crew_id or self.source.roster[0]["crew_id"]
            if cid not in {p["crew_id"] for p in self.source.roster}:
                raise KeyError(cid)
            invalid = [s for s in symptoms if s not in SYMPTOM_LABELS]
            if invalid:
                raise ValueError("Unknown symptom codes: " + ", ".join(invalid))
            self.source.symptoms[cid] = list(dict.fromkeys(symptoms))
            self._event("SYMPTOMS", "attention" if symptoms else "normal", "MANUAL_INPUT",
                        "Belgilar: " + (", ".join(SYMPTOM_LABELS[s] for s in symptoms) if symptoms else "yo‘q"),
                        "crew", cid)
            return self.step()

    def add_crew(self, name: str, zone_id: str) -> dict:
        with self._lock:
            if not isinstance(self.source, DemoSimulator):
                raise ValueError("Crew changes only supported in simulation")
            if zone_id not in ZONES:
                raise ValueError("Unknown zone")
            if len(self.source.roster) >= 12:
                raise ValueError("Demo supports up to 12 crew members")
            used = {p["crew_id"] for p in self.source.roster}
            next_id = next(f"C{n:02d}" for n in range(1, 99) if f"C{n:02d}" not in used)
            self.source.roster.append({"crew_id": next_id, "name": name.strip(), "zone_id": zone_id})
            self._known_crew_names[next_id] = name.strip()
            self.db.set_setting("crew_roster", self.source.roster)
            self.history.clear()
            self._event("CREW_ADDED", "normal", "CREW_ROSTER", f"{next_id}: {name} [{zone_id}]", "crew", next_id)
            return self.step()

    def remove_crew(self, crew_id: str) -> dict:
        with self._lock:
            if not isinstance(self.source, DemoSimulator):
                raise ValueError("Crew changes only supported in simulation")
            if crew_id not in {p["crew_id"] for p in self.source.roster}:
                raise KeyError(crew_id)
            if len(self.source.roster) <= 1:
                raise ValueError("At least one crew member required")
            self.source.roster = [p for p in self.source.roster if p["crew_id"] != crew_id]
            self.source.symptoms.pop(crew_id, None)
            self.db.set_setting("crew_roster", self.source.roster)
            self.history.clear()
            self._event("CREW_REMOVED", "normal", "CREW_ROSTER", f"{crew_id} safar ro‘yxatidan chiqarildi",
                        "crew", crew_id)
            return self.step()

    def _actor(self, crew_id: str) -> dict:
        if not self.last or crew_id not in self.last.crew:
            raise KeyError("Actor not in current demo crew")
        person = self.last.crew[crew_id]
        return {"crew_id": person.crew_id, "name": person.name}

    def create_incident(self, protocol_id: str, crew_ids: list[str], zone_ids: list[str],
                        origin_code: str, note: str, actor_id: str) -> dict:
        with self._lock:
            actor = self._actor(actor_id)
            if not self.last:
                raise IncidentError("Mission data unavailable")
            if len(crew_ids) != len(set(crew_ids)) or len(zone_ids) != len(set(zone_ids)):
                raise IncidentError("Takrorlangan ekipaj yoki modul")
            if len(crew_ids) > 12 or len(zone_ids) > 2:
                raise IncidentError("Haddan tashqari katta so‘rov")
            if any(cid not in self.last.crew for cid in crew_ids):
                raise IncidentError("Ekipaj a'zosi topilmadi")
            if any(zid not in self.last.zones for zid in zone_ids):
                raise IncidentError("Modul topilmadi")
            if origin_code == "MANUAL_REPORT":
                evidence = {"source": "manual", "validated": False,
                            "timestamp": self.last.timestamp, "scenario": self.last.scenario}
            else:
                match = next((a for a in self.alerts if a.code == origin_code and
                              (a.subject_id in crew_ids or a.subject_id in zone_ids or a.scope == "mission")), None)
                finding = next((f for f in self.findings if f.code == origin_code), None)
                if not match and not finding:
                    raise IncidentError("Ko‘rsatilgan faol signal mavjud emas")
                evidence = {"source": "current_demo_signal", "validated": False,
                            "timestamp": self.last.timestamp, "scenario": self.last.scenario,
                            "signal": match.as_dict() if match else finding.as_dict(),
                            "crew_data": {cid: self.last.crew[cid].as_dict() for cid in crew_ids},
                            "zone_data": {zid: {k: v.as_dict() for k, v in self.last.zones[zid].items()} for zid in zone_ids}}
            crew_snapshot = [self._actor(cid) for cid in crew_ids]
            case = self.incidents.create(protocol_id, crew_snapshot, zone_ids,
                                         origin_code, note, evidence, actor)
            self._event("INCIDENT_CREATED", "attention", "DEMO_INCIDENT", case["id"] + " · " + protocol_id,
                        "mission", "mission", tuple(crew_ids))
            return case

    def update_incident_step(self, incident_id: str, index: int, status: str,
                             actor_id: str, note: str) -> dict:
        with self._lock:
            case = self.incidents.update_step(incident_id, index, status, self._actor(actor_id), note)
            self._event("INCIDENT_STEP", "attention", "DEMO_INCIDENT", f"{incident_id} · {index} · {status}",
                        affected_ids=tuple(p["crew_id"] for p in case["crew_snapshot"]))
            return case

    def review_incident(self, incident_id: str, actor_id: str, note: str) -> dict:
        with self._lock:
            case = self.incidents.mark_reviewed(incident_id, self._actor(actor_id), note)
            self._event("INCIDENT_REVIEWED", "normal", "DEMO_INCIDENT", incident_id + " · demo tekshiruv qayd etildi",
                        affected_ids=tuple(p["crew_id"] for p in case["crew_snapshot"]))
            return case

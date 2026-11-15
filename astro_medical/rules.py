"""Demo-only deterministic rules. No diagnosis, no validated clinical thresholds."""
from __future__ import annotations
from datetime import datetime, timezone
from statistics import median
from math import isfinite
from .models import Alert, CrewSample, Finding, Measurement, MissionTelemetry, Telemetry

# All values here are ARTIFICIAL SOFTWARE TEST THRESHOLDS, not NASA/clinical limits.
# Defined in one place for later medical review.
DEMO_LIMITS = {
    "spo2": (94, 90, "below", "LOW_SPO2", "SpO₂ pasayishi", "breathing"),
    "heart_rate": (115, 135, "above", "HIGH_HEART_RATE", "Puls tezlashishi", "vitals-check"),
    "systolic_bp_high": (160, 180, "above", "HIGH_BP", "Qon bosimi ko‘tarilishi", "vitals-check"),
    "systolic_bp_low": (95, 85, "below", "LOW_BP", "Qon bosimi pasayishi", "vitals-check"),
    "body_temp_high": (38.5, 40, "above", "HIGH_BODY_TEMP", "Tana harorati oshishi", "vitals-check"),
    "body_temp_low": (35.5, 34, "below", "LOW_BODY_TEMP", "Tana harorati pasayishi", "vitals-check"),
    "resp_rate_high": (23, 30, "above", "HIGH_RESP_RATE", "Nafas tezlashishi", "breathing"),
    "resp_rate_low": (10, 7, "below", "LOW_RESP_RATE", "Nafas sekinlashishi", "breathing"),
    "co2_partial": (.40, .70, "above", "HIGH_CO2", "CO₂ ko‘payishi", "cabin-atmosphere"),
    "o2_partial": (19.0, 17.5, "below", "LOW_CABIN_O2", "O₂ qisman bosimi pasayishi", "cabin-atmosphere"),
    "pressure": (96, 90, "below", "LOW_CABIN_PRESSURE", "Kabina bosimi pasayishi", "cabin-atmosphere"),
    "temperature_high": (28, 33, "above", "HIGH_CABIN_TEMP", "Kabina harorati ko‘tarilishi", "cabin-atmosphere"),
    "temperature_low": (18, 14, "below", "LOW_CABIN_TEMP", "Kabina harorati pasayishi", "cabin-atmosphere"),
    "radiation": (3, 8, "above", "HIGH_RADIATION", "Radiatsiya ko‘tarilishi (demo)", "space-environment"),
}
SYMPTOM_LABELS = {
    "severe_bleeding": "Jiddiy qon ketishi",
    "unresponsive": "Javob bermaslik / hushdan ketish",
    "breathing_difficulty": "Nafas olish qiyinlashishi",
    "chest_pain": "Ko‘krak sohasida kuchli og‘riq",
    "dizziness": "Bosh aylanishi",
}
SEVERITY_SORT = {"critical": 0, "attention": 1, "unknown": 2, "normal": 3}
EXPECTED_UNITS = {
    "spo2": "%", "heart_rate": "bpm", "systolic_bp": "mmHg", "diastolic_bp": "mmHg",
    "body_temp": "°C", "resp_rate": "/min", "co2_partial": "kPa", "o2_partial": "kPa",
    "pressure": "kPa", "temperature": "°C", "humidity": "%", "radiation": "µSv/h",
    "scrubber_ok": "boolean", "hab_fan_ok": "boolean",
}


def valid_point(point: Measurement | None, now: str | None = None, max_age: int = 15,
                expected_unit: str | None = None) -> bool:
    if point is None or point.value is None or point.quality != "good":
        return False
    if isinstance(point.value, bool) or not isinstance(point.value, (int, float)) or not isfinite(point.value):
        return False
    if expected_unit is not None and point.unit != expected_unit:
        return False
    # When used for active mission decisions every point MUST have a source and capture time.
    if now and (not point.sensor_id or not point.captured_at):
        return False
    if point.captured_at and now:
        try:
            sample = datetime.fromisoformat(point.captured_at)
            current = datetime.fromisoformat(now)
            if sample.tzinfo is None or current.tzinfo is None:
                return False
            age = (current - sample).total_seconds()
            if age < -5 or age > max_age:
                return False
        except (TypeError, ValueError):
            return False
    return True


def _rule(point: Measurement | None, key: str, config: tuple, scope: str, subject_id: str,
          now: str | None = None) -> Alert | None:
    attention, critical, direction, code, title, protocol = config
    if not valid_point(point, now, expected_unit=EXPECTED_UNITS.get(key)):
        return Alert("SENSOR_" + key.upper(), "unknown", f"{title}: ma’lumot ishonchsiz",
                     "Sensor uzilgan, noto‘g‘ri, eski yoki kalibrlanmagan; xavfsiz deb baholab bo‘lmaydi.",
                     "sensor-check", "sensor", scope, subject_id, (key,))
    value = point.value
    severe = value < critical if direction == "below" else value > critical
    mild = value < attention if direction == "below" else value > attention
    if not mild and not severe:
        return None
    return Alert(code, "critical" if severe else "attention", title,
                 f"DEMO: {value:g} {point.unit}, sinov chegarasidan tashqarida; tashxis emas.",
                 protocol, "rule", scope, subject_id, (f"{key}={value:g} {point.unit}",))


def assess_member(person: CrewSample, now: str) -> list[Alert]:
    alerts = []
    checks = [("spo2", "spo2"), ("heart_rate", "heart_rate"),
              ("systolic_bp", "systolic_bp_high"), ("systolic_bp", "systolic_bp_low"),
              ("body_temp", "body_temp_high"), ("body_temp", "body_temp_low"),
              ("resp_rate", "resp_rate_high"), ("resp_rate", "resp_rate_low")]
    for key, spec in checks:
        a = _rule(person.vitals.get(key), key, DEMO_LIMITS[spec], "crew", person.crew_id, now)
        if a and not any(x.code == a.code and x.subject_id == a.subject_id for x in alerts):
            alerts.append(a)
    # Diastolic BP does not have a decision threshold in this demo, but missing data is noted.
    if not valid_point(person.vitals.get("diastolic_bp"), now, expected_unit="mmHg"):
        alerts.append(Alert("SENSOR_DIASTOLIC_BP", "unknown", "Diastolik bosim sensori",
                            "Ma’lumot yo‘q/yaroqsiz.", "sensor-check", "sensor", "crew", person.crew_id))
    for symptom in person.symptoms:
        if symptom in ("severe_bleeding", "unresponsive", "breathing_difficulty", "chest_pain"):
            alerts.append(Alert("SYMPTOM_" + symptom.upper(), "critical", SYMPTOM_LABELS[symptom],
                                "Ekipaj xabar qilgan jiddiy alomat. Mutaxassis tasdiqlagan protokol talab qilinadi.",
                                "trauma" if symptom == "severe_bleeding" else "urgent-medical",
                                "manual", "crew", person.crew_id, ("self_report=" + symptom,)))
        elif symptom == "dizziness":
            alerts.append(Alert("SYMPTOM_DIZZINESS", "attention", SYMPTOM_LABELS[symptom],
                                "Alomat qayd etildi. Sabab noma’lum.", "vitals-check", "manual", "crew", person.crew_id))
    return sorted(alerts, key=lambda a: (SEVERITY_SORT[a.severity], a.code))


def assess_zone(zone_id: str, points: dict[str, Measurement], now: str) -> list[Alert]:
    alerts = []
    specs = [("co2_partial", "co2_partial"), ("o2_partial", "o2_partial"),
             ("pressure", "pressure"), ("temperature", "temperature_high"),
             ("temperature", "temperature_low"), ("radiation", "radiation")]
    for key, spec in specs:
        a = _rule(points.get(key), key, DEMO_LIMITS[spec], "zone", zone_id, now)
        if a and not any(x.code == a.code for x in alerts):
            alerts.append(a)
    for key in ("humidity",):
        if not valid_point(points.get(key), now, expected_unit=EXPECTED_UNITS.get(key)):
            alerts.append(Alert("SENSOR_" + key.upper(), "unknown", f"{key} sensori",
                                "O‘lchov mavjud emas yoki eskirgan.", "sensor-check", "sensor", "zone", zone_id))
    return alerts


def assess_trends(person: CrewSample, history: list[MissionTelemetry]) -> list[Alert]:
    """Short moving window, robust median halves; only actual good points count.

    Temporal demo trends are not predictors or diagnoses. Require >=6 valid samples.
    """
    configs = [("spo2", -3.0, "TREND_SPO2_DOWN", "SpO₂ pasayish tendensiyasi"),
               ("heart_rate", 18.0, "TREND_HR_UP", "Puls o‘sish tendensiyasi"),
               ("resp_rate", 6.0, "TREND_RR_UP", "Nafas tezlashish tendensiyasi")]
    findings = []
    for key, delta, code, label in configs:
        points = []
        for snapshot in history[-12:]:
            previous = snapshot.crew.get(person.crew_id)
            point = previous.vitals.get(key) if previous else None
            if point and valid_point(point, snapshot.timestamp, expected_unit=EXPECTED_UNITS.get(key)):
                points.append(point.value)
        if len(points) < 6:
            continue
        half = len(points)//2
        change = median(points[-half:]) - median(points[:half])
        if (delta < 0 and change <= delta) or (delta > 0 and change >= delta):
            findings.append(Alert(code, "attention", label,
                                 f"DEMO: oxirgi oynada median o‘zgarish {change:+.1f}. Shaxsiy baza va kontekst tekshirilsin.",
                                 "vitals-check", "trend", "crew", person.crew_id,
                                 (f"{key}: trend delta {change:+.1f}",)))
    return findings


def assess_coverage(mission: MissionTelemetry, expected_crew: set[str],
                    expected_zones: set[str]) -> list[Alert]:
    """Absent people/zones/systems are not a normal mission state."""
    alerts = []
    for cid in expected_crew - set(mission.crew):
        alerts.append(Alert("MISSING_CREW_SAMPLE", "unknown", "Kosmonavt telemetriyasi yo‘q",
                            "Butun kosmonavt yozuvi yo‘q; sog‘liq holati noma’lum.",
                            "sensor-check", "sensor", "crew", cid))
    for zid in expected_zones - set(mission.zones):
        alerts.append(Alert("MISSING_ZONE_SAMPLE", "unknown", "Modul telemetriyasi yo‘q",
                            "Butun modul yozuvi yo‘q; muhit holati noma’lum.",
                            "sensor-check", "sensor", "zone", zid))
    for key in ("scrubber_ok", "hab_fan_ok"):
        if not valid_point(mission.systems.get(key), mission.timestamp, expected_unit="boolean"):
            alerts.append(Alert("SENSOR_SYSTEM_" + key.upper(), "unknown",
                                "Uskuna sensori ishonchsiz", "Uskuna holatini normal deb baholab bo‘lmaydi.",
                                "engineering-check", "sensor", "mission", "mission", (key,)))
    return alerts


def correlate(mission: MissionTelemetry, alerts: list[Alert]) -> list[Finding]:
    """Same-time crewmember correlation + independent habitat/equipment evidence.

    Never assume a common cause from physiological coincidence alone.
    """
    findings: list[Finding] = []
    crew_ids = set(mission.crew)
    zones_by_crew = {cid: member.zone_id for cid, member in mission.crew.items()}
    environmental = [a for a in alerts if a.scope == "zone" and a.origin == "rule"]
    sys_faults = [key for key, p in mission.systems.items() if valid_point(p, mission.timestamp, expected_unit="boolean") and p.value == 0]
    oxygenation_codes = {"LOW_SPO2", "TREND_SPO2_DOWN", "HIGH_RESP_RATE", "TREND_RR_UP"}
    respiratory = {a.subject_id for a in alerts if a.scope == "crew" and
                   a.code in oxygenation_codes and a.severity in ("critical", "attention")}
    same_symptoms = {a.subject_id for a in alerts if a.scope == "crew" and a.code == "SYMPTOM_DIZZINESS"}
    cohorts = [("RESPIRATORY", respiratory, "Nafas/oksigenatsiya ko‘rsatkichlari"),
               ("DIZZINESS", same_symptoms, "Bosh aylanishi belgisi")]

    for marker, affected, label in cohorts:
        if len(affected) < 2:
            continue
        affected_zones = {zones_by_crew[cid] for cid in affected}
        matching_env = [a for a in environmental if a.subject_id in affected_zones]
        matching_systems = [s for s in sys_faults
                            if s == "scrubber_ok" or (s == "hab_fan_ok" and "HAB" in affected_zones)]
        independent = bool(matching_env or matching_systems)
        category = "environment_possible" if independent else "unexplained_crew_cluster"
        level = "critical" if any(a.severity == "critical" for a in matching_env) else "attention"
        if not independent:
            interpretation = ("Bir nechta ekipaj a’zosida o‘xshash belgi bor, ammo mavjud muhit sensorlari "
                              "buni izohlamayapti. Sabab ANIQLANMAGAN. Umumiy faoliyat, ekspozitsiya, "
                              "asbob nosozligi va tibbiy holatlar tekshirilsin.")
        else:
            interpretation = ("Bir nechta ekipaj a’zosidagi o‘zgarish bilan kabina/sistema signallari "
                              "bir vaqtda aniqlangan. Muhit yoki kema nosozligi MUMKIN, sabab tasdiqlanmagan.")
        evidence = [f"{len(affected)}/{len(crew_ids)} ekipajda {label.lower()}"]
        evidence += [f"{a.subject_id}: {a.code} ({a.severity})" for a in matching_env]
        evidence += [f"Tizim signali: {s}=0" for s in matching_systems]
        findings.append(Finding(f"CREW_CLUSTER_{marker}", level, category,
                                f"Ekipaj bo‘ylab umumiy o‘zgarish: {label}", interpretation,
                                tuple(sorted(affected)), tuple(sorted(affected_zones)), tuple(evidence),
                                ("Fiziologik korrelyatsiya sababni isbotlamaydi.",
                                 "O‘lchovlar sinxronligi va sensor sifati tekshirilishi kerak."),
                                ("Barcha tegishli ekipaj a’zolari va modullarning yangi o‘lchovlarini solishtirish.",
                                 "Atmosfera, ventilyatsiya, radiatsiya, faoliyat va qurilma holatini tekshirish.",
                                 "Tasdiqlangan bort protokoli bo‘yicha ekipajni xabardor qilish."),
                                "cabin-atmosphere" if independent else "crew-investigation"))

    # Independent system evidence may matter even before crew symptoms develop.
    if sys_faults:
        findings.append(Finding("EQUIPMENT_ANOMALY", "attention", "equipment_anomaly",
                                "Hayot ta’minoti uskunasida nosozlik signali",
                                "Uskunadan nosozlik signali olingan; sensor va zaxira ko‘rsatkich bilan tasdiqlash kerak.",
                                (), tuple(sorted(mission.zones)), tuple("Kuzatuv: " + x + "=0" for x in sys_faults),
                                ("Demo telemetriya. Uskuna haqiqiy boshqarilmaydi.",),
                                ("Bort muhandislik tekshiruv ro‘yxatini ochish.",), "engineering-check"))

    radiated = {a.subject_id for a in environmental if a.code == "HIGH_RADIATION"}
    if radiated and radiated == set(mission.zones):
        findings.append(Finding("MISSION_RADIATION_PATTERN", "attention", "space_environment_possible",
                                "Bir nechta modulda radiatsiya signali",
                                "Tashqi kosmik muhit ta’siri yoki o‘lchov tizimi anomaliyasi bo‘lishi mumkin; "
                                "buni faqat ushbu signallar bilan tasdiqlab bo‘lmaydi.",
                                (), tuple(sorted(radiated)), ("Barcha mavjud zonalarda radiatsiya ko‘rsatkichlari oshgan",),
                                ("Kosmik ob-havo yoki radiatsiya dozasi mustaqil manbadan tasdiqlanmagan.",),
                                ("Dozimetr va radiatsiya monitoringini tekshirish.",
                                 "Tasdiqlangan radiatsiya xavfsizligi protokolini ochish."), "space-environment"))

    bad_sensors = {a.subject_id for a in alerts if a.scope == "crew" and a.origin == "sensor" and a.code.startswith("SENSOR_SPO2")}
    if len(bad_sensors) >= 2:
        findings.append(Finding("CREW_SENSOR_CLUSTER", "unknown", "shared_sensing_issue",
                                "Bir nechta ekipajda sensor ma’lumoti yo‘q",
                                "Bu birgalikdagi kasallik alomati EMAS. Sensor yoki ma’lumot uzatish qismi tekshiriladi.",
                                tuple(sorted(bad_sensors)), tuple(sorted({zones_by_crew[c] for c in bad_sensors})),
                                (f"{len(bad_sensors)} ta SpO₂ sensori ishonchsiz",),
                                ("Sog‘liq holatini mavjud bo‘lmagan o‘lchovlardan bilib bo‘lmaydi.",),
                                ("Zaxira o‘lchov vositalaridan foydalanish.",), "sensor-check"))
    return sorted(findings, key=lambda f: (SEVERITY_SORT[f.level], f.code))


def summary_level(alerts: list[Alert]) -> str:
    if any(a.severity == "critical" for a in alerts): return "critical"
    if any(a.severity == "attention" for a in alerts): return "attention"
    if any(a.severity == "unknown" for a in alerts): return "unknown"
    return "normal"


def evaluate(t: Telemetry) -> list[Alert]:
    """Compatibility wrapper for the v0.1 individual snapshot."""
    p = CrewSample("C01", "Kosmonavt 01", "HAB", t.vitals, t.symptoms)
    return sorted(assess_member(p, t.timestamp) + assess_zone("HAB", t.cabin, t.timestamp),
                  key=lambda a: (SEVERITY_SORT[a.severity], a.code))

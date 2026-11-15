"""Event actor-name snapshots and legacy DB migration regression tests."""
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from astro_medical.database import Database
from astro_medical.service import MonitoringService


class EventNamesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "events.sqlite3"
        self.svc = MonitoringService(Database(self.path))

    def tearDown(self):
        self.tmp.cleanup()

    def test_individual_name_saved_for_symptom_alert_and_clear(self):
        self.svc.set_symptoms(["severe_bleeding"], "C02")
        events = self.svc.db.get_events(100, subject_id="C02")
        self.assertTrue(any(e["event_type"] == "SYMPTOMS" and e["subject_name"] == "Kosmonavt 02"
                            for e in events))
        self.assertTrue(any(e["code"] == "SYMPTOM_SEVERE_BLEEDING" and
                            e["subject_name"] == "Kosmonavt 02" for e in events))
        self.svc.set_symptoms([], "C02")
        self.assertTrue(any(e["event_type"] == "ALERT_CLEARED" and
                            e["subject_name"] == "Kosmonavt 02" for e in self.svc.db.get_events(100)))

    def test_removed_crew_events_keep_original_name(self):
        self.svc.add_crew("Sinov kosmonavti", "LAB")
        self.svc.set_symptoms(["dizziness"], "C05")
        self.svc.remove_crew("C05")
        events = self.svc.db.get_events(100, subject_id="C05")
        self.assertGreaterEqual(len(events), 3)
        self.assertTrue(all(e["subject_name"] == "Sinov kosmonavti" for e in events))
        restarted = Database(self.path)
        self.assertTrue(all(e["subject_name"] == "Sinov kosmonavti"
                            for e in restarted.get_events(100, subject_id="C05")))

    def test_cluster_findings_capture_multiple_names(self):
        self.svc.set_scenario("shared_co2")
        for _ in range(9):
            self.svc.step()
        events = [e for e in self.svc.db.get_events(200) if e["event_type"] == "FINDING_OPEN"]
        self.assertTrue(events)
        self.assertTrue(any(len(e["affected_crew"]) >= 2 for e in events))
        for event in events:
            for member in event["affected_crew"]:
                self.assertEqual(member["name"], self.svc._known_crew_names[member["crew_id"]])

    def test_global_event_not_misattributed_to_individual(self):
        self.svc.set_link(False)
        e = next(x for x in self.svc.db.get_events(25) if x["event_type"] == "LINK")
        self.assertEqual(e["scope"], "mission")
        self.assertIsNone(e["subject_name"])
        self.assertEqual(e["affected_crew"], [])

    def test_legacy_db_adds_missing_columns_and_recovers_unambiguous_name(self):
        path = Path(self.tmp.name) / "old.sqlite3"
        with sqlite3.connect(path) as conn:
            conn.execute("CREATE TABLE events (id INTEGER PRIMARY KEY, created_at TEXT, event_type TEXT, severity TEXT, code TEXT, message TEXT, scope TEXT, subject_id TEXT)")
            conn.execute("CREATE TABLE telemetry (id INTEGER PRIMARY KEY, created_at TEXT, scenario TEXT, source TEXT, payload TEXT)")
            conn.execute("INSERT INTO events VALUES (1,'2026-11-14','ALERT_OPEN','attention','X','message','crew','C22')")
            data = {"crew": {"C22": {"name": "Tarixiy kosmonavt"}}}
            conn.execute("INSERT INTO telemetry VALUES (1,'2026-11-14','normal','sim',?)", (json.dumps(data),))
        db = Database(path)
        self.assertEqual(db.get_events()[0]["subject_name"], "Tarixiy kosmonavt")
        self.assertEqual(db.get_events()[0]["affected_crew"], [])

    def test_legacy_reused_id_name_not_guessed(self):
        path = Path(self.tmp.name) / "ambiguous.sqlite3"
        with sqlite3.connect(path) as conn:
            conn.execute("CREATE TABLE events (id INTEGER PRIMARY KEY, created_at TEXT, event_type TEXT, severity TEXT, code TEXT, message TEXT, scope TEXT, subject_id TEXT)")
            conn.execute("CREATE TABLE telemetry (id INTEGER PRIMARY KEY, created_at TEXT, scenario TEXT, source TEXT, payload TEXT)")
            conn.execute("INSERT INTO events VALUES (1,'2026-11-14','ALERT_OPEN','attention','X','message','crew','C05')")
            for i, name in enumerate(("Old Name", "New Name"), 1):
                conn.execute("INSERT INTO telemetry VALUES (?,'2026-11-14','normal','sim',?)",
                             (i, json.dumps({"crew": {"C05": {"name": name}}})))
        db = Database(path)
        self.assertIsNone(db.get_events()[0]["subject_name"])


if __name__ == "__main__":
    unittest.main()

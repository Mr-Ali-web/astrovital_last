import tempfile
import unittest
from pathlib import Path
from astro_medical.database import Database
from astro_medical.service import MonitoringService
from astro_medical.sources import HardwareSource


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name)/"test.sqlite"
        self.db = Database(self.path)
        self.svc = MonitoringService(self.db)

    def tearDown(self):
        self.temp.cleanup()

    def test_four_members_and_individual_symptom(self):
        self.assertEqual(len(self.svc.status()["crew"]), 4)
        response = self.svc.set_symptoms(["severe_bleeding"], "C02")
        self.assertEqual(response["level"], "critical")
        self.assertTrue(any(a["subject_id"]=="C02" and a["code"]=="SYMPTOM_SEVERE_BLEEDING"
                            for a in response["active_alerts"]))
        self.assertFalse(any(a["subject_id"]=="C03" and a["code"]=="SYMPTOM_SEVERE_BLEEDING"
                             for a in response["active_alerts"]))

    def test_environment_warning_without_crew_symptom(self):
        self.svc.set_scenario("radiation_event")
        response = None
        for _ in range(8): response=self.svc.step()
        self.assertGreater(len(response["shared_findings"]), 0)
        self.assertTrue(any(a["scope"]=="zone" and a["code"]=="HIGH_RADIATION" for a in response["active_alerts"]))

    def test_offline_writes_outbox_and_restores(self):
        self.svc.set_link(False)
        self.svc.set_scenario("shared_co2")
        for _ in range(8): self.svc.step()
        status=self.svc.status()
        self.assertGreater(status["pending_outbox"], 0)
        self.assertEqual(status["transport"], "LOCAL_SIMULATION_NO_REAL_TRANSMISSION")
        self.assertFalse(status["earth_link"])
        self.assertEqual(self.svc.set_link(True)["pending_outbox"], 0)

    def test_alert_severity_escalation_is_logged(self):
        self.svc.set_scenario("single_low_spo2")
        for _ in range(8): self.svc.step()
        self.assertTrue(any(e["event_type"]=="ALERT_UPDATED" and e["code"]=="LOW_SPO2" for e in self.db.get_events(200)))

    def test_add_remove_crew_persists_roster(self):
        result=self.svc.add_crew("Yangi sinov kosmonavti", "LAB")
        self.assertEqual(len(result["crew"]), 5)
        new_id=result["crew"][-1]["crew_id"]
        self.assertEqual(new_id,"C05")
        self.assertEqual(len(MonitoringService(Database(self.path)).status()["crew"]),5)
        result=self.svc.remove_crew("C05")
        self.assertEqual(len(result["crew"]),4)
        self.assertEqual(len(MonitoringService(Database(self.path)).status()["crew"]),4)

    def test_history_persisted_per_crew(self):
        self.svc.step();self.svc.step()
        self.assertGreaterEqual(len(self.db.get_history()),3)
        history=self.db.get_crew_history("C02")
        self.assertGreaterEqual(len(history),3)
        self.assertTrue(all(x["crew_id"]=="C02" for x in history))

    def test_no_ai_or_hardware_silent_fallback(self):
        self.assertIs(self.svc.status()["ai_model_enabled"],False)
        with self.assertRaises(NotImplementedError):
            HardwareSource().read()

    def test_scenario_change_resets_trend_window(self):
        self.svc.set_scenario("single_low_spo2")
        for _ in range(8):self.svc.step()
        self.assertTrue(any(a["code"]=="TREND_SPO2_DOWN" for a in self.svc.status()["active_alerts"]))
        normal=self.svc.set_scenario("normal")
        self.assertFalse(any(a["code"]=="TREND_SPO2_DOWN" for a in normal["active_alerts"]))


if __name__ == "__main__":
    unittest.main()

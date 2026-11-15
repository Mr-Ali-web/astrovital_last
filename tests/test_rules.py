import unittest
from datetime import datetime, timedelta, timezone
from astro_medical.models import Measurement, Telemetry
from astro_medical.rules import (
    assess_member, assess_zone, assess_trends, assess_coverage, correlate, evaluate, summary_level, valid_point
)
from astro_medical.sources import DemoSimulator


def make_alerts(mission, history=None):
    history = history or [mission]
    alerts = []
    for member in mission.crew.values():
        alerts.extend(assess_member(member, mission.timestamp))
        alerts.extend(assess_trends(member, history))
    for zone, points in mission.zones.items():
        alerts.extend(assess_zone(zone, points, mission.timestamp))
    return alerts


class RuleTests(unittest.TestCase):
    def scenario(self, name, steps=8):
        simulator = DemoSimulator()
        simulator.set_scenario(name)
        history = [simulator.read() for _ in range(steps)]
        last = history[-1]
        alerts = make_alerts(last, history)
        return last, alerts, correlate(last, alerts)

    def test_normal_all_crew_clean(self):
        mission, alerts, findings = self.scenario("normal")
        self.assertEqual(len(mission.crew), 4)
        self.assertEqual(alerts, [])
        self.assertEqual(findings, [])

    def test_one_crew_low_oxygen_does_not_claim_shared_cause(self):
        _, alerts, findings = self.scenario("single_low_spo2")
        self.assertTrue(any(a.code == "LOW_SPO2" and a.subject_id == "C01" and
                            a.severity == "critical" for a in alerts))
        self.assertFalse(any(f.code.startswith("CREW_CLUSTER") for f in findings))

    def test_shared_co2_correlates_with_two_zones_and_system(self):
        _, alerts, findings = self.scenario("shared_co2")
        self.assertEqual(len([a for a in alerts if a.code == "LOW_SPO2"]), 4)
        respiratory = next(f for f in findings if f.code == "CREW_CLUSTER_RESPIRATORY")
        self.assertEqual(respiratory.category, "environment_possible")
        self.assertEqual(set(respiratory.affected_zones), {"HAB", "LAB"})
        self.assertTrue(any("HIGH_CO2" in e for e in respiratory.evidence))
        self.assertTrue(any(f.code == "EQUIPMENT_ANOMALY" for f in findings))

    def test_local_ventilation_fault_is_not_mission_wide(self):
        _, alerts, findings = self.scenario("zone_ventilation_fault")
        affected = {a.subject_id for a in alerts if a.code == "LOW_SPO2"}
        self.assertEqual(affected, {"C01", "C02"})
        self.assertEqual({a.subject_id for a in alerts if a.code == "HIGH_CO2"}, {"HAB"})
        cluster = next(f for f in findings if f.code == "CREW_CLUSTER_RESPIRATORY")
        self.assertEqual(set(cluster.affected_zones), {"HAB"})
        self.assertEqual(cluster.category, "environment_possible")

    def test_many_crew_abnormal_but_environment_normal_is_unexplained(self):
        _, alerts, findings = self.scenario("crew_cluster_only")
        cluster = next(f for f in findings if f.code == "CREW_CLUSTER_RESPIRATORY")
        self.assertEqual(cluster.category, "unexplained_crew_cluster")
        self.assertEqual(cluster.level, "attention")
        self.assertFalse(any(a.scope == "zone" and a.origin == "rule" for a in alerts))
        self.assertIn("ANIQLANMAGAN", cluster.interpretation)

    def test_radiation_signal_does_not_claim_disease(self):
        _, alerts, findings = self.scenario("radiation_event")
        self.assertEqual({a.subject_id for a in alerts if a.code == "HIGH_RADIATION"}, {"HAB", "LAB"})
        self.assertTrue(any(f.category == "space_environment_possible" for f in findings))
        self.assertFalse(any(a.scope == "crew" for a in alerts))

    def test_sensor_cluster_not_misdiagnosed_as_illness(self):
        _, alerts, findings = self.scenario("multi_sensor_fault")
        self.assertTrue(any(f.category == "shared_sensing_issue" for f in findings))
        self.assertFalse(any(f.category == "environment_possible" for f in findings))
        self.assertEqual(summary_level([a for a in alerts if a.scope == "crew"]), "unknown")

    def test_one_sensor_missing_is_unknown(self):
        _, alerts, _ = self.scenario("sensor_fault")
        self.assertTrue(any(a.scope == "crew" and a.subject_id == "C01" and
                            a.code == "SENSOR_SPO2" for a in alerts))

    def test_trend_for_one_member_only(self):
        _, alerts, _ = self.scenario("single_low_spo2")
        trend_members = {a.subject_id for a in alerts if a.code == "TREND_SPO2_DOWN"}
        self.assertEqual(trend_members, {"C01"})

    def test_stale_point_never_used_to_assess_normality(self):
        m = DemoSimulator().read()
        member = m.crew["C01"]
        point = member.vitals["spo2"]
        point.captured_at = (datetime.now(timezone.utc)-timedelta(minutes=2)).isoformat()
        self.assertFalse(valid_point(point, m.timestamp))
        alerts = assess_member(member, m.timestamp)
        self.assertTrue(any(a.code == "SENSOR_SPO2" and a.severity == "unknown" for a in alerts))

    def test_missing_crew_or_zone_is_unknown_not_normal(self):
        m = DemoSimulator().read()
        del m.crew["C04"]
        del m.zones["LAB"]
        alerts = assess_coverage(m, {"C01","C02","C03","C04"}, {"HAB","LAB"})
        self.assertTrue(any(a.code == "MISSING_CREW_SAMPLE" and a.subject_id == "C04" for a in alerts))
        self.assertTrue(any(a.code == "MISSING_ZONE_SAMPLE" and a.subject_id == "LAB" for a in alerts))
        self.assertEqual(summary_level(alerts), "unknown")

    def test_wrong_unit_missing_time_and_nan_never_accepted(self):
        m = DemoSimulator().read()
        point = m.crew["C01"].vitals["spo2"]
        point.unit = "kPa"
        self.assertFalse(valid_point(point, m.timestamp, expected_unit="%"))
        point.unit = "%"
        point.value = float("nan")
        self.assertFalse(valid_point(point, m.timestamp, expected_unit="%"))
        point.value = 98
        point.captured_at = None
        self.assertFalse(valid_point(point, m.timestamp, expected_unit="%"))

    def test_missing_system_sensor_is_unknown(self):
        m = DemoSimulator().read()
        m.systems.pop("hab_fan_ok")
        alerts=assess_coverage(m, set(m.crew), set(m.zones))
        self.assertTrue(any(a.code=="SENSOR_SYSTEM_HAB_FAN_OK" for a in alerts))

    def test_legacy_single_person_wrapper(self):
        m = DemoSimulator().read()
        p = m.crew["C01"]
        individual = Telemetry(m.timestamp, m.source, m.scenario, p.vitals, m.zones[p.zone_id], [])
        self.assertEqual(evaluate(individual), [])
        individual.symptoms = ["unresponsive"]
        self.assertEqual(summary_level(evaluate(individual)), "critical")


if __name__ == "__main__":
    unittest.main()

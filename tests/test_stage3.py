"""3-bosqich API, offline audit and safety invariants."""
import tempfile
import unittest
from pathlib import Path
from fastapi.testclient import TestClient
from astro_medical.api import create_app


class Stage3Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "stage3.sqlite"
        self.app = create_app(self.path, background=False)
        self.client = TestClient(self.app)
        self.client.__enter__()

    def tearDown(self):
        self.client.__exit__(None, None, None)
        self.temp.cleanup()

    def new_case(self, **patch):
        data = {"protocol_id": "vitals-check", "crew_ids": ["C01"], "zone_ids": [],
                "origin_code": "MANUAL_REPORT", "note": "Sinov", "actor_id": "C02"}
        data.update(patch)
        return self.client.post("/api/incidents", json=data)

    def test_catalog_is_demo_only_and_device_independent(self):
        p = self.client.get("/api/protocols")
        self.assertEqual(p.status_code, 200)
        self.assertGreaterEqual(len(p.json()["items"]), 9)
        self.assertTrue(all(item["approval_status"] == "DEMO" and not item["allow_clinical_use"]
                            for item in p.json()["items"]))
        self.assertEqual(self.client.get("/api/protocols/not-a-protocol").status_code, 404)
        self.assertEqual(self.client.get("/api/resources").json()["source"], "SYNTHETIC_INVENTORY")
        self.assertFalse(self.client.get("/api/health").json()["ai_model_enabled"])

    def test_individual_case_snapshot_and_crew_removed(self):
        case = self.new_case()
        self.assertEqual(case.status_code, 201, case.text)
        data = case.json()
        self.assertEqual(data["approval_snapshot"], "DEMO")
        self.assertEqual(data["crew_snapshot"][0]["name"], "Kosmonavt 01")
        self.assertEqual(data["steps"][0]["status"], "pending")
        self.assertEqual(data["audit"][0]["actor_name"], "Kosmonavt 02")
        self.assertTrue(any(e["event_type"] == "INCIDENT_CREATED" and
                            e["affected_crew"][0]["name"] == "Kosmonavt 01"
                            for e in self.client.get("/api/events").json()["items"]))
        self.client.delete("/api/crew/C01")
        stored = self.client.get("/api/incidents/" + data["id"]).json()
        self.assertEqual(stored["crew_snapshot"][0]["name"], "Kosmonavt 01")
        self.assertEqual(stored["steps_snapshot"], data["steps_snapshot"])
        # Save survives the server restarting against the same SQLite database.
        second_app = create_app(self.path, background=False)
        with TestClient(second_app) as other:
            self.assertEqual(other.get("/api/incidents/" + data["id"]).json()["crew_snapshot"][0]["name"],
                             "Kosmonavt 01")

    def test_step_state_machine_actor_audit_and_close(self):
        case = self.new_case().json()
        cid = case["id"]
        url = f"/api/incidents/{cid}/steps/0"
        self.assertEqual(self.client.patch(url, json={"status": "completed", "actor_id": "C01"}).status_code, 409)
        self.assertEqual(self.client.post(f"/api/incidents/{cid}/review", json={"actor_id": "C01"}).status_code, 409)
        for idx, step in enumerate(case["steps"]):
            url = f"/api/incidents/{cid}/steps/{idx}"
            self.assertEqual(self.client.patch(url, json={"status": "acknowledged", "actor_id": "C02", "note": "Ko‘rildi"}).status_code, 200)
            self.assertEqual(self.client.patch(url, json={"status": "completed", "actor_id": "C02", "note": "DEMO"}).status_code, 200)
        review = self.client.post(f"/api/incidents/{cid}/review", json={"actor_id": "C02", "note": "Tugadi"})
        self.assertEqual(review.status_code, 200, review.text)
        self.assertEqual(review.json()["status"], "reviewed")
        self.assertGreaterEqual(len(review.json()["audit"]), len(case["steps"]) * 2 + 2)
        self.assertEqual(self.client.patch(f"/api/incidents/{cid}/steps/0",
                                            json={"status":"blocked","actor_id":"C02"}).status_code, 409)
        self.assertEqual(self.client.post(f"/api/incidents/{cid}/review", json={"actor_id": "C02"}).status_code, 409)

    def test_multi_crew_shared_findings_offline_outbox(self):
        self.client.post("/api/link", json={"available": False})
        self.client.post("/api/scenario", json={"scenario": "shared_co2"})
        for _ in range(9):
            result = self.client.post("/api/step").json()
        finding = next(x for x in result["shared_findings"] if x["code"] == "CREW_CLUSTER_RESPIRATORY")
        ids = list(finding["affected_crew"])
        case = self.new_case(protocol_id="crew-investigation", crew_ids=ids,
                             zone_ids=list(finding["affected_zones"]),
                             origin_code=finding["code"], actor_id="C01")
        self.assertEqual(case.status_code, 201, case.text)
        obj=case.json()
        self.assertGreaterEqual(len(obj["crew_snapshot"]), 2)
        self.assertEqual(obj["evidence_snapshot"]["source"], "current_demo_signal")
        self.assertFalse(obj["evidence_snapshot"]["validated"])
        self.assertGreater(self.client.get("/api/status").json()["pending_outbox"], 0)
        self.client.post("/api/link", json={"available": True})
        self.assertEqual(self.client.get("/api/status").json()["pending_outbox"], 0)
        self.assertEqual(self.client.get("/api/status").json()["transport"],
                         "LOCAL_SIMULATION_NO_REAL_TRANSMISSION")

    def test_invalid_inputs_and_resource_unavailable(self):
        self.assertEqual(self.new_case(protocol_id="never-exists").status_code, 422)
        self.assertEqual(self.new_case(protocol_id="crew-investigation").status_code, 422)
        self.assertEqual(self.new_case(crew_ids=["BOGUS"]).status_code, 422)
        self.assertEqual(self.new_case(actor_id="BOGUS").status_code, 404)
        self.assertEqual(self.new_case(zone_ids=["UNKNOWN"]).status_code, 422)
        self.assertEqual(self.new_case(origin_code="MADE_UP_SIGNAL").status_code, 422)
        self.assertEqual(self.client.get("/api/incidents/INC-BOGUS").status_code, 404)
        case=self.new_case(protocol_id="space-environment",crew_ids=["C01"],zone_ids=["HAB","LAB"])
        self.assertEqual(case.status_code,201)
        self.assertIn("dosimeter",case.json()["missing_resources"])
        incident_id = case.json()["id"]
        self.assertEqual(self.client.patch(f"/api/incidents/{incident_id}/steps/0",
                                           json={"status":"acknowledged","actor_id":"C01"}).status_code,200)
        self.assertEqual(self.client.patch(f"/api/incidents/{incident_id}/steps/0",
                                           json={"status":"completed","actor_id":"C01"}).status_code,409)
        self.assertEqual(self.client.patch(f"/api/incidents/{case.json()['id']}/steps/400",
                                           json={"status":"blocked","actor_id":"C01"}).status_code,404)

    def test_website_assets_and_responsive_breakpoints(self):
        markup = self.client.get("/").text
        css = self.client.get("/static/style.css").text
        js = self.client.get("/static/app.js").text
        for selector in ('id="emergency"', 'id="incidentForm"', 'id="incidentList"', 'id="mobileMenuButton"'):
            self.assertIn(selector, markup)
        for breakpoint in ('max-width:790px','max-width:500px'):
            self.assertIn(breakpoint, css)
        self.assertIn('ensureStage3()', js)
        self.assertNotIn('initStage3();', js)


if __name__ == "__main__": unittest.main()

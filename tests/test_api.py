import tempfile
import unittest
from pathlib import Path
from fastapi.testclient import TestClient
from astro_medical.api import create_app


class APITests(unittest.TestCase):
    def test_multi_crew_and_scenarios_endpoints(self):
        with tempfile.TemporaryDirectory() as temp:
            app=create_app(Path(temp)/"api.sqlite",background=False)
            with TestClient(app) as client:
                self.assertEqual(client.get("/").status_code,200)
                self.assertFalse(client.get("/api/health").json()["ai_model_enabled"])
                self.assertEqual(len(client.get("/api/crew").json()["items"]),4)
                self.assertEqual(client.post("/api/scenario",json={"scenario":"shared_co2"}).status_code,200)
                result=None
                for _ in range(8): result=client.post("/api/step").json()
                self.assertTrue(any(f["code"]=="CREW_CLUSTER_RESPIRATORY" for f in result["shared_findings"]))
                self.assertEqual(client.get("/api/findings").status_code,200)
                self.assertTrue(client.get("/api/crew/C01/history").json()["items"])
                self.assertEqual(client.get("/api/crew/BOGUS/history").status_code,404)
                self.assertEqual(client.post("/api/scenario",json={"scenario":"invalid"}).status_code,422)
                self.assertEqual(client.get("/api/playbooks/crew-investigation").json()["approval"],"DEMO_ONLY")

    def test_crew_crud_and_personal_symptoms(self):
        with tempfile.TemporaryDirectory() as temp:
            app=create_app(Path(temp)/"api.sqlite",background=False)
            with TestClient(app) as client:
                self.assertEqual(client.post("/api/crew",json={"name":" ","zone_id":"HAB"}).status_code,422)
                self.assertEqual(client.post("/api/crew",json={"name":"Test","zone_id":"OTHER"}).status_code,422)
                response=client.post("/api/crew",json={"name":"Test","zone_id":"LAB"})
                self.assertEqual(response.status_code,200)
                self.assertEqual(len(response.json()["crew"]),5)
                self.assertEqual(client.post("/api/crew/C05/symptoms",json={"symptoms":["dizziness"]}).status_code,200)
                self.assertEqual(client.post("/api/crew/C09/symptoms",json={"symptoms":[]}).status_code,404)
                self.assertEqual(client.post("/api/crew/C05/symptoms",json={"symptoms":["not_real"]}).status_code,422)
                self.assertEqual(client.delete("/api/crew/C05").status_code,200)
                self.assertEqual(client.delete("/api/crew/C05").status_code,404)
                self.assertEqual(len(client.get("/api/status").json()["crew"]),4)


if __name__ == "__main__":
    unittest.main()

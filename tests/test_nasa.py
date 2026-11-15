import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from fastapi.testclient import TestClient
from astro_medical.api import create_app
from astro_medical.nasa import NasaReference, parse_osdr, parse_donki


def fake_fetch(url):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    if "osdr.nasa.gov" in url:
        return {"hits": {"total": {"value": 2}, "hits": [
            {"_source": {"Accession": "OSD-48", "Study Title": "Radiation test"}},
            {"_source": {"Accession": "OSD-49", "Study Title": "Second"}}]}}
    if "/SEP" in url:
        return [{"sepID": "X1", "eventTime": now, "link": "https://example.test/x1"}]
    return []


def broken_fetch(url):
    raise OSError("no network")


class NasaTests(unittest.TestCase):
    def test_parsers_are_defensive(self):
        self.assertEqual(parse_osdr({"unexpected": 1})["items"], [])
        self.assertEqual(parse_osdr(None)["total"], 0)
        self.assertEqual(parse_donki({"not": "list"}, ("id",), ("time",))["total"], 0)

    def test_refresh_caches_and_offline_status(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "n.sqlite"
            ref = NasaReference(str(path), fetcher=fake_fetch)
            self.assertEqual(ref.status()["advisory"]["state"], "unknown")
            self.assertTrue(all(v == "ok" for v in ref.refresh().values()))
            # A new instance with a broken network still reads the cache.
            offline = NasaReference(str(path), fetcher=broken_fetch)
            status = offline.status()
            self.assertTrue(status["reference_only"])
            self.assertEqual(status["advisory"]["state"], "recent_events")
            osdr = next(s for s in status["sources"] if s["id"] == "osdr_radiation")
            self.assertEqual(osdr["items"][0]["accession"], "OSD-48")
            # A failed refresh must never erase the last good data or raise.
            self.assertTrue(all(v == "error" for v in offline.refresh().values()))
            again = next(s for s in offline.status()["sources"] if s["id"] == "osdr_radiation")
            self.assertEqual(again["total"], 2)
            self.assertIn("OSError", again["last_error"])

    def test_api_endpoints_and_no_effect_on_risk(self):
        with tempfile.TemporaryDirectory() as temp:
            app = create_app(Path(temp) / "api.sqlite", background=False, nasa_fetcher=broken_fetch)
            with TestClient(app) as client:
                before = client.get("/api/status").json()["mission"]
                self.assertEqual(client.get("/api/nasa/status").status_code, 200)
                refreshed = client.post("/api/nasa/refresh")
                self.assertEqual(refreshed.status_code, 200)
                self.assertTrue(all(v == "error" for v in refreshed.json()["result"].values()))
                after = client.get("/api/status").json()["mission"]
                self.assertEqual(before.get("risk_level"), after.get("risk_level"))


if __name__ == "__main__":
    unittest.main()

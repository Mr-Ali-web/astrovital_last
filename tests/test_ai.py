"""v0.4.0: offline AI assistant — API contract, safety logic and CPU quantisation."""
import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient

from astro_medical import ai_engine
from astro_medical.ai_engine import AIEngine, JobManager, assemble, choose_action, validate_records
from astro_medical.api import create_app


class FakeEngine(AIEngine):
    """Behaves like the real engine but classifies by keyword (no torch needed)."""

    def __init__(self, available=True):
        super().__init__(model_dir=Path("/nonexistent"), threshold=0.7)
        self._available = available

    @property
    def available(self):
        return self._available

    def load(self):
        self.loaded = True

    def translate(self, texts):
        self.translations.update({t: "EN " + t for t in texts})

    def classify(self, texts):
        out = []
        for t in texts:
            t = t.lower()
            if "ventilyatsiya" in t:
                out.append(("muhit:mos", 0.97))
            elif "jurnali" in t:
                out.append(("ovqat:noma_lum", 0.95))
            elif "tasdiqladi" in t:
                out.append(("sensor:qarshi", 0.92))
            elif "shubhali" in t:
                out.append(("parvoz:mos", 0.55))
            else:
                out.append(("alomat", 0.99))
        return out


def wait_job(client, job_id, timeout=5):
    end = time.time() + timeout
    while time.time() < end:
        job = client.get(f"/api/ai/jobs/{job_id}").json()
        if job["status"] in ("done", "error"):
            return job
        time.sleep(0.05)
    raise AssertionError("AI job did not finish")


class AIApiTests(unittest.TestCase):
    def make_client(self, engine):
        self.folder = TemporaryDirectory()
        client = TestClient(create_app(Path(self.folder.name) / "ai.sqlite3", background=False, ai_engine=engine))
        client.__enter__()
        self.addCleanup(lambda: (client.__exit__(None, None, None), self.folder.cleanup()))
        return client

    def test_without_model_app_still_works_and_says_so(self):
        client = self.make_client(FakeEngine(available=False))
        self.assertFalse(client.get("/api/health").json()["ai_model_enabled"])
        self.assertFalse(client.get("/api/ai/status").json()["available"])
        res = client.post("/api/ai/analyze", json={"records": {"E1": "matn"}})
        self.assertEqual(res.status_code, 409)
        self.assertEqual(client.get("/api/status").status_code, 200)

    def test_full_analysis_flow(self):
        client = self.make_client(FakeEngine())
        demo = client.get("/api/ai/demo").json()["records"]
        job = client.post("/api/ai/analyze", json={"records": demo})
        self.assertEqual(job.status_code, 202)
        result = wait_job(client, job.json()["job_id"])
        self.assertEqual(result["status"], "done", result)
        r = result["result"]
        self.assertEqual(r["harakat"], "CHECK_CABIN")
        self.assertEqual(r["ehtimollar"]["muhit"], {"holat": "mos", "dalil": ["E2"], "ishonch": 0.97})
        self.assertEqual(r["ehtimollar"]["ovqat"]["holat"], "noma_lum")
        self.assertEqual(r["ehtimollar"]["sensor"]["holat"], "qarshi")
        self.assertIn("tibbiy tasdiqlanmagan", r["ogohlantirish"])
        self.assertEqual(r["qaydlar"]["E1"]["sinf"], "alomat")

    def test_low_confidence_never_gives_specific_action(self):
        client = self.make_client(FakeEngine())
        recs = {"E1": "LAB ventilyatsiya o'chgan", "E2": "shubhali parvoz qaydi"}
        r = wait_job(client, client.post("/api/ai/analyze", json={"records": recs}).json()["job_id"])["result"]
        self.assertEqual(r["past_ishonch"], ["E2"])
        self.assertEqual(r["harakat"], "REVIEW_MODEL_OUTPUT")

    def test_input_validation(self):
        client = self.make_client(FakeEngine())
        self.assertEqual(client.post("/api/ai/analyze", json={"records": {}}).status_code, 422)
        too_many = {f"E{i}": "matn" for i in range(13)}
        self.assertEqual(client.post("/api/ai/analyze", json={"records": too_many}).status_code, 422)
        self.assertEqual(client.post("/api/ai/analyze", json={"records": {"bad id!": "x"}}).status_code, 422)
        self.assertEqual(client.post("/api/ai/analyze", json={"records": {"E1": "x" * 501}}).status_code, 422)
        self.assertEqual(client.get("/api/ai/jobs/nope").status_code, 404)

    def test_panel_present_on_every_view(self):
        client = self.make_client(FakeEngine())
        html = client.get("/").text
        self.assertIn('id="aiPanel"', html)
        self.assertIn('/static/ai_panel.js', html)
        # The panel lives outside every data-view section, so no menu can hide it.
        panel_pos, main_end = html.index('id="aiPanel"'), html.index("</main>")
        self.assertGreater(panel_pos, main_end)
        css = client.get("/static/style.css").text
        self.assertIn(".ai-panel{position:fixed", css)
        self.assertEqual(client.get("/static/ai_panel.js").status_code, 200)


class SafetyLogicTests(unittest.TestCase):
    records = {"E1": "a", "E2": "b", "E3": "c", "E4": "d", "E5": "e"}

    def test_two_supported_causes_is_conflict(self):
        preds = {"E1": ("muhit:mos", 0.9), "E2": ("ovqat:mos", 0.95), "E3": ("alomat", 1.0)}
        r = assemble(self.records, preds, 0.7)
        self.assertEqual(r["harakat"], "REVIEW_CONFLICT")

    def test_nothing_supported_asks_for_context(self):
        preds = {"E1": ("muhit:qarshi", 0.9), "E2": ("sensor:noma_lum", 0.95)}
        self.assertEqual(assemble(self.records, preds, 0.7)["harakat"], "ASK_CONTEXT")

    def test_most_confident_record_wins_per_topic(self):
        preds = {"E1": ("sensor:mos", 0.75), "E2": ("sensor:qarshi", 0.99)}
        r = assemble(self.records, preds, 0.7)
        self.assertEqual(r["ehtimollar"]["sensor"], {"holat": "qarshi", "dalil": ["E2"], "ishonch": 0.99})

    def test_malformed_output_is_flagged(self):
        self.assertEqual(choose_action({"ehtimollar": {"muhit": {}}}, {}), "REVIEW_MODEL_OUTPUT")

    def test_normalisation_matches_training(self):
        self.assertEqual(validate_records({"E1": "  o‘zgarish   yo`q "})["E1"], "o'zgarish yo'q")
        self.assertEqual(ai_engine.to_uzbek_script("o'zgarish a'zo"), "oʻzgarish aʼzo")

    def test_v54_rules_present_in_fallback_options(self):
        for label in ("muhit:qarshi", "ovqat:qarshi", "sensor:qarshi", "parvoz:qarshi"):
            self.assertIn("Also CONTRADICTED", ai_engine.OPTION_TEXT[label])
        self.assertEqual(len(ai_engine.LABELS), 13)

    def test_job_manager_reports_errors(self):
        class Broken(FakeEngine):
            def classify(self, texts):
                raise RuntimeError("boom")
        jobs = JobManager(Broken())
        job = jobs.submit({"E1": "matn"})
        for _ in range(100):
            if jobs.get(job["job_id"])["status"] == "error":
                break
            time.sleep(0.02)
        self.assertEqual(jobs.get(job["job_id"])["error"], "boom")


@unittest.skipUnless(__import__("importlib").util.find_spec("torch") and
                     __import__("importlib").util.find_spec("transformers"), "torch/transformers not installed")
class QuantisationTests(unittest.TestCase):
    def test_int8_quantised_model_matches_float_choice(self):
        import torch
        from transformers import Qwen2Config, Qwen2ForCausalLM
        torch.manual_seed(0)
        cfg = Qwen2Config(vocab_size=300, hidden_size=64, intermediate_size=128, num_hidden_layers=2,
                          num_attention_heads=4, num_key_value_heads=2, tie_word_embeddings=True)
        ref = Qwen2ForCausalLM(cfg).eval()
        q = Qwen2ForCausalLM(cfg).eval()
        q.load_state_dict(ref.state_dict())
        q = ai_engine.quantize_int8(q.to(torch.bfloat16))
        ids = torch.randint(0, 300, (1, 20))
        letters = torch.arange(13)
        with torch.inference_mode():
            a = torch.softmax(ref(input_ids=ids, logits_to_keep=1).logits[0, -1, letters], -1)
            b = torch.softmax(q(input_ids=ids, logits_to_keep=1).logits[0, -1, letters].float(), -1)
        self.assertEqual(int(a.argmax()), int(b.argmax()))
        self.assertLess(float((a - b).abs().max()), 0.05)
        linear_types = {type(m).__name__ for m in q.model.layers.modules()}
        self.assertIn("Linear", linear_types)  # dynamic quantised Linear keeps the class name
        self.assertTrue(any("quantized" in type(m).__module__ for m in q.model.layers.modules()))


if __name__ == "__main__":
    unittest.main()

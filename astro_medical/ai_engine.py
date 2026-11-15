"""Optional offline AI assistant (DEMO, NOT medically validated).

Pipeline (same as the AstroMed V5.4 Kaggle notebook):
  1. NLLB-200 translates each Uzbek crew-log record to English (offline).
  2. Qwen2.5-3B-Instruct + LoRA adapter picks exactly one of 13 labelled options
     (A-M) per record. Only the 13 option letters are scored, so the model can
     never produce free-form or malformed output.
  3. Deterministic code (``assemble`` / ``choose_action``) builds the final JSON
     and the suggested review action. Low-confidence records never trigger a
     specific action.

The app works without this module's heavy dependencies: torch/transformers are
imported only when the model is actually loaded.
"""
from __future__ import annotations

import json
import os
import re
import threading
import time
import uuid
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parent.parent
MODEL_DIR = Path(os.getenv("ASTRO_AI_DIR", str(ROOT / "models")))
BASE_DIR = MODEL_DIR / "qwen2.5-3b-instruct"
TRANSLATOR_DIR = MODEL_DIR / "nllb-200-distilled-600M"
ADAPTER_DIR = MODEL_DIR / "adapter"
CONFIG_PATH = MODEL_DIR / "inference_config.json"
# 0.7 gave the best balance on the V5.4 evaluation (177/196 new-test cases, 4 unsafe actions).
DEFAULT_THRESHOLD = float(os.getenv("ASTRO_AI_THRESHOLD", "0.7"))
QUANTIZATION = os.getenv("ASTRO_AI_QUANT", "int8").lower()  # int8 | bf16 | fp32
MAX_RECORDS = 12
MAX_RECORD_CHARS = 500

TOPICS = ("muhit", "ovqat", "sensor", "parvoz")
STATES = ("mos", "qarshi", "noma_lum")
LABELS = ["alomat"] + [f"{t}:{s}" for t in TOPICS for s in STATES]
ACTIONS = dict(zip(TOPICS, ("CHECK_CABIN", "CHECK_INTAKE", "VERIFY_SENSOR", "CHECK_FLIGHT")))
ACTIONS.update(yetarli_emas="ASK_CONTEXT", ziddiyat="REVIEW_CONFLICT")
SPECIFIC_ACTIONS = {ACTIONS[t] for t in TOPICS}

SYSTEM_PROMPT = ("You analyse one log record from a SIMULATED space mission. "
                 "Classify the record into exactly one option. Answer with a single letter.")
# Fallback copy of the V5.4 option texts; inference_config.json (saved by the
# training notebook) takes priority so the prompt always matches training.
OPTION_TEXT = {
    "alomat": "Symptom report only: a crew member describes how they feel; it says nothing about the cause.",
    "muhit:mos": "ENVIRONMENT cause SUPPORTED: cabin air, CO2, O2, ventilation, pressure, temperature, humidity or radiation in a module is linked to the symptoms.",
    "muhit:qarshi": "ENVIRONMENT cause CONTRADICTED: cabin/module conditions were normal and stable, or symptoms do not follow the module/air conditions. Also CONTRADICTED if symptoms began before the air problem, or did not change after the air system was fixed, or air tests were clean during symptoms.",
    "muhit:noma_lum": "ENVIRONMENT: NO DATA — cabin or air measurements are missing, not recorded or not checked.",
    "ovqat:mos": "FOOD/WATER cause SUPPORTED: symptoms follow eating or drinking a shared item, batch or water source.",
    "ovqat:qarshi": "FOOD/WATER cause CONTRADICTED: no shared food or water, symptoms began before eating, or the food/water tested fine. Also CONTRADICTED if symptoms began BEFORE eating or before the package was opened, or the food/water passed a test and others who consumed it are healthy.",
    "ovqat:noma_lum": "FOOD/WATER: NO DATA — intake log or food/water information is missing or not recorded.",
    "sensor:mos": "SENSOR ERROR SUPPORTED: the abnormal reading is likely a device artifact (not confirmed by an independent device, faulty battery or contact, low quality flag, desync, error code).",
    "sensor:qarshi": "SENSOR ERROR CONTRADICTED: an independent device or manual measurement confirms the reading, or the device was tested and works. Also CONTRADICTED if the reading stayed the same after the device was replaced or recalibrated, or a second device or manual check shows the same value.",
    "sensor:noma_lum": "SENSOR: NO DATA — device quality, calibration or a second measurement is missing or not recorded.",
    "parvoz:mos": "FLIGHT PHASE/ACTIVITY cause SUPPORTED: symptoms are tied to landing, standing up, early adaptation, maneuvers, g-load, spacewalk/suit work, posture or schedule changes.",
    "parvoz:qarshi": "FLIGHT PHASE/ACTIVITY cause CONTRADICTED: symptoms do not change with posture, activity or flight phase, or started at an unrelated time. Also CONTRADICTED if symptom times do not match the activity schedule, or symptoms started long after recovery or adaptation.",
    "parvoz:noma_lum": "FLIGHT PHASE/ACTIVITY: NO DATA — flight phase, activity or schedule information is missing or not recorded.",
}
DEMO_RECORDS = {
    "E1": "A02 va A05 bosh aylanishini qayd etdi.",
    "E2": "LAB modulida ventilyatsiya o'chgan paytda ikki a'zo bosh og'rig'idan shikoyat qildi.",
    "E3": "Iste'mol jurnali to'ldirilmagan.",
    "E4": "Mustaqil ko'chma o'lchagich ham puls o'zgarishini tasdiqladi.",
    "E5": "Alomat parvoz bosqichidan qat'i nazar bir xil bo'lgan.",
}


def normalize(text: str) -> str:
    """Same apostrophe/space normalisation as training."""
    text = re.sub(r"[`'ʼʻ‘’´]", "'", str(text))
    return re.sub(r"\s+", " ", text).strip()


def to_uzbek_script(text: str) -> str:
    text = re.sub(r"([oOgG])'", lambda m: m.group(1) + "ʻ", text)
    return text.replace("'", "ʼ")


def choose_action(parsed: dict, records: dict) -> str:
    if not isinstance(parsed, dict) or not isinstance(parsed.get("ehtimollar"), dict):
        return "REVIEW_MODEL_OUTPUT"
    hyp = parsed["ehtimollar"]
    if set(hyp) != set(TOPICS):
        return "REVIEW_MODEL_OUTPUT"
    supporting = []
    for topic, item in hyp.items():
        if item.get("holat") not in STATES or not all(ref in records for ref in item.get("dalil", [])):
            return "REVIEW_MODEL_OUTPUT"
        if item["holat"] == "mos":
            supporting.append(topic)
    if len(supporting) > 1:
        return ACTIONS["ziddiyat"]
    if not supporting:
        return ACTIONS["yetarli_emas"]
    return ACTIONS[supporting[0]]


def assemble(records: dict, predictions: dict, threshold: float) -> dict:
    """predictions[ref] = (label, confidence). Keeps the most confident record per topic."""
    best, uncertain = {}, []
    for ref, (label, conf) in predictions.items():
        if label == "alomat":
            continue
        if conf < threshold:
            uncertain.append(ref)
            continue
        topic, status = label.split(":")
        if topic not in best or conf > best[topic][2]:
            best[topic] = (ref, status, conf)
    hyp = {}
    for topic in TOPICS:
        if topic in best and best[topic][1] != "noma_lum":
            ref, status, conf = best[topic]
            hyp[topic] = {"holat": status, "dalil": [ref], "ishonch": round(conf, 3)}
        else:
            hyp[topic] = {"holat": "noma_lum", "dalil": []}
    result = {"ehtimollar": hyp, "past_ishonch": sorted(uncertain)}
    result["harakat"] = choose_action(result, records)
    if uncertain and result["harakat"] in SPECIFIC_ACTIONS:
        result["harakat"] = "REVIEW_MODEL_OUTPUT"
    return result


def validate_records(records: dict) -> dict:
    if not isinstance(records, dict) or not records:
        raise ValueError("Kamida bitta qayd kerak")
    if len(records) > MAX_RECORDS:
        raise ValueError(f"Ko'pi bilan {MAX_RECORDS} ta qayd")
    clean = {}
    for ref, text in records.items():
        ref, text = str(ref).strip(), normalize(text)
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,12}", ref):
            raise ValueError(f"Noto'g'ri qayd ID: {ref!r}")
        if not text:
            raise ValueError(f"{ref}: qayd bo'sh")
        if len(text) > MAX_RECORD_CHARS:
            raise ValueError(f"{ref}: qayd {MAX_RECORD_CHARS} belgidan uzun")
        clean[ref] = text
    return clean


def files_present(model_dir: Path = MODEL_DIR) -> dict:
    return {
        "base_model": (model_dir / BASE_DIR.name / "config.json").is_file(),
        "translator": (model_dir / TRANSLATOR_DIR.name / "config.json").is_file(),
        "adapter": (model_dir / ADAPTER_DIR.name / "adapter_config.json").is_file(),
    }


class AIEngine:
    """Loads the models lazily on CPU and runs one analysis at a time."""

    def __init__(self, model_dir: Path = MODEL_DIR, threshold: float = DEFAULT_THRESHOLD,
                 quantization: str = QUANTIZATION):
        self.model_dir = Path(model_dir)
        self.threshold = threshold
        self.quantization = quantization
        self._lock = threading.Lock()
        self.loaded = False
        self.loading = False
        self.error: str | None = None
        self.load_seconds: float | None = None
        self.translations: dict[str, str] = {}
        self.option_text = dict(OPTION_TEXT)
        self.system_prompt = SYSTEM_PROMPT
        self.letters = [chr(ord("A") + i) for i in range(len(LABELS))]

    # ---- status -------------------------------------------------------
    @property
    def available(self) -> bool:
        return all(files_present(self.model_dir).values())

    def status(self) -> dict:
        return {
            "available": self.available, "files": files_present(self.model_dir),
            "loaded": self.loaded, "loading": self.loading, "error": self.error,
            "threshold": self.threshold, "quantization": self.quantization, "device": "cpu",
            "load_seconds": self.load_seconds, "model_dir": str(self.model_dir),
            "medical_approval": "NOT_VALIDATED",
        }

    # ---- loading ------------------------------------------------------
    def _read_config(self) -> None:
        cfg_path = self.model_dir / CONFIG_PATH.name
        if not cfg_path.is_file():
            return
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        if cfg.get("labels") and cfg["labels"] != LABELS:
            raise RuntimeError("inference_config.json dagi sinflar bu versiyaga mos emas")
        self.option_text = cfg.get("options") or self.option_text
        self.system_prompt = cfg.get("system_prompt") or self.system_prompt
        self.letters = cfg.get("letters") or self.letters

    def load(self) -> None:
        with self._lock:
            if self.loaded:
                return
            if not self.available:
                missing = [k for k, ok in files_present(self.model_dir).items() if not ok]
                self.error = "Model fayllari topilmadi: " + ", ".join(missing)
                raise RuntimeError(self.error)
            self.loading, self.error = True, None
            start = time.time()
            try:
                self._load_models()
                self.loaded = True
                self.load_seconds = round(time.time() - start, 1)
            except Exception as exc:  # surfaced to the UI via status()
                self.error = f"Modelni yuklab bo'lmadi: {exc}"
                raise
            finally:
                self.loading = False

    def _load_models(self) -> None:
        import torch
        from transformers import AutoModelForCausalLM, AutoModelForSeq2SeqLM, AutoTokenizer
        from peft import PeftModel

        self._read_config()
        torch.set_num_threads(max(1, os.cpu_count() or 1))
        self.torch = torch
        base = self.model_dir / BASE_DIR.name
        self.tokenizer = AutoTokenizer.from_pretrained(str(base))
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        ids = [self.tokenizer.encode(l, add_special_tokens=False) for l in self.letters]
        if not all(len(i) == 1 for i in ids):
            raise RuntimeError("Variant harflari bitta tokenga mos emas")
        self.letter_ids = [i[0] for i in ids]
        dtype = torch.float32 if self.quantization == "fp32" else torch.bfloat16
        model = AutoModelForCausalLM.from_pretrained(str(base), torch_dtype=dtype, low_cpu_mem_usage=True)
        model = PeftModel.from_pretrained(model, str(self.model_dir / ADAPTER_DIR.name)).merge_and_unload()
        if self.quantization == "int8":
            model = quantize_int8(model)
        self.model = model.eval()

        tr = self.model_dir / TRANSLATOR_DIR.name
        self.tr_tokenizer = AutoTokenizer.from_pretrained(str(tr), src_lang="uzn_Latn")
        self.translator = AutoModelForSeq2SeqLM.from_pretrained(str(tr), torch_dtype=torch.float32).eval()
        self.eng_id = self.tr_tokenizer.convert_tokens_to_ids("eng_Latn")

    # ---- inference ----------------------------------------------------
    def translate(self, texts: list[str]) -> None:
        todo = [t for t in dict.fromkeys(texts) if t not in self.translations]
        if not todo:
            return
        with self.torch.inference_mode():
            for i in range(0, len(todo), 8):
                chunk = todo[i:i + 8]
                enc = self.tr_tokenizer([to_uzbek_script(t) for t in chunk], return_tensors="pt",
                                        padding=True, truncation=True, max_length=160)
                gen = self.translator.generate(**enc, forced_bos_token_id=self.eng_id,
                                               max_new_tokens=160, num_beams=3)
                for src, dst in zip(chunk, self.tr_tokenizer.batch_decode(gen, skip_special_tokens=True)):
                    self.translations[src] = dst

    def prompt_ids(self, text: str) -> list[int]:
        uz = normalize(text)
        en = self.translations.get(uz, "")
        options = chr(10).join(f"{self.letters[i]}. {self.option_text[name]}" for i, name in enumerate(LABELS))
        user = (f"Record (Uzbek): {uz}\nEnglish machine translation (may contain errors): {en}\n\n"
                f"Options:\n{options}\n\nAnswer with the letter only.")
        messages = [{"role": "system", "content": self.system_prompt}, {"role": "user", "content": user}]
        return self.tokenizer.apply_chat_template(messages, tokenize=True, add_generation_prompt=True)

    def classify(self, texts: list[str]) -> list[tuple[str, float]]:
        torch = self.torch
        out = []
        letter_ids = torch.tensor(self.letter_ids)
        with torch.inference_mode():
            for text in texts:  # batch size 1 on CPU: no padding waste
                ids = torch.tensor([self.prompt_ids(text)])
                logits = self.model(input_ids=ids, logits_to_keep=1).logits[:, -1, :]
                probs = torch.softmax(logits.float()[:, letter_ids], dim=-1)[0]
                out.append((LABELS[int(probs.argmax())], float(probs.max())))
        return out

    def analyze(self, records: dict, progress: Callable[[str, float], None] | None = None) -> dict:
        records = validate_records(records)
        progress = progress or (lambda *_: None)
        if not self.loaded:
            progress("Model yuklanmoqda (birinchi marta 1–3 daqiqa)", 0.05)
            self.load()
        with self._lock:
            start = time.time()
            progress("Tarjima qilinmoqda", 0.2)
            self.translate(list(records.values()))
            preds = {}
            refs = list(records)
            for n, ref in enumerate(refs):
                progress(f"Qayd tahlil qilinmoqda: {ref} ({n + 1}/{len(refs)})", 0.3 + 0.65 * n / len(refs))
                preds[ref] = self.classify([records[ref]])[0]
            result = assemble(records, preds, self.threshold)
            result["qaydlar"] = {r: {"matn": records[r], "tarjima": self.translations.get(records[r], ""),
                                     "sinf": preds[r][0], "ishonch": round(preds[r][1], 3)} for r in refs}
            result["sekund"] = round(time.time() - start, 1)
            result["chegara"] = self.threshold
            result["ogohlantirish"] = "DEMO: tibbiy tasdiqlanmagan. Faqat ko'rib chiqish uchun tavsiya."
            return result


def quantize_int8(model):
    """Dynamic int8 quantisation of every decoder Linear layer, one layer at a time.

    Converting layer by layer keeps peak RAM low on a 16 GB laptop; the remaining
    small parts (embeddings, norms) run in fp32.
    """
    import torch
    from torch import nn
    core = model.model
    core.embed_tokens.float()
    core.norm.float()
    if hasattr(core, "rotary_emb"):
        core.rotary_emb.float()
    for layer in core.layers:
        layer.float()
        torch.ao.quantization.quantize_dynamic(layer, {nn.Linear}, dtype=torch.qint8, inplace=True)
    if model.lm_head.weight.dtype != torch.float32:
        model.lm_head.float()
    model.config.torch_dtype = torch.float32
    return model


class JobManager:
    """Runs analyses in one background worker thread; the UI polls job status."""

    def __init__(self, engine: AIEngine, keep: int = 30):
        self.engine = engine
        self.keep = keep
        self.jobs: dict[str, dict] = {}
        self._lock = threading.Lock()
        self._worker_lock = threading.Lock()

    def submit(self, records: dict) -> dict:
        records = validate_records(records)
        job_id = uuid.uuid4().hex[:12]
        job = {"job_id": job_id, "status": "queued", "stage": "Navbatda", "progress": 0.0,
               "created": time.time(), "result": None, "error": None}
        with self._lock:
            self.jobs[job_id] = job
            for old in sorted(self.jobs.values(), key=lambda j: j["created"])[:-self.keep]:
                self.jobs.pop(old["job_id"], None)
        threading.Thread(target=self._run, args=(job_id, records), daemon=True).start()
        return self.public(job)

    def _run(self, job_id: str, records: dict) -> None:
        job = self.jobs[job_id]
        with self._worker_lock:
            job["status"] = "running"

            def progress(stage: str, value: float) -> None:
                job["stage"], job["progress"] = stage, round(value, 2)
            try:
                job["result"] = self.engine.analyze(records, progress)
                job["status"], job["stage"], job["progress"] = "done", "Tayyor", 1.0
            except Exception as exc:
                job["status"], job["error"], job["stage"] = "error", str(exc), "Xato"

    def get(self, job_id: str) -> dict:
        return self.public(self.jobs[job_id])

    @staticmethod
    def public(job: dict) -> dict:
        return {k: job[k] for k in ("job_id", "status", "stage", "progress", "result", "error")}

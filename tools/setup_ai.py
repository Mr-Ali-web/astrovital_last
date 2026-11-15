#!/usr/bin/env python3
"""One-time installer for the optional offline AI assistant (needs Internet once).

  1. Installs CPU-only PyTorch + transformers/peft into the current Python (venv).
  2. Downloads Qwen2.5-3B-Instruct (~6 GB) and NLLB-200-distilled-600M (~2.5 GB)
     into ./models.
  3. Extracts the trained AstroMed LoRA adapter from the Kaggle results ZIP
     (AstroMed_V5_RESULTS.zip) into ./models/adapter.

After this, the app runs fully offline. Usage (normally via start.py):
    python tools/setup_ai.py --adapter-zip "C:\\Users\\...\\Downloads\\AstroMed_V5_RESULTS.zip"
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODELS = ROOT / "models"
BASE_REPO, BASE_DIR = "Qwen/Qwen2.5-3B-Instruct", MODELS / "qwen2.5-3b-instruct"
TR_REPO, TR_DIR = "facebook/nllb-200-distilled-600M", MODELS / "nllb-200-distilled-600M"
REQS = ROOT / "requirements-ai.txt"


def pip(*args: str) -> None:
    subprocess.run([sys.executable, "-m", "pip", "install", "--disable-pip-version-check", *args], check=True)


def install_packages() -> None:
    try:
        import torch, transformers, peft  # noqa: F401
        print("[AI] Kutubxonalar allaqachon o'rnatilgan.")
        return
    except ImportError:
        pass
    print("[AI] PyTorch (faqat CPU, ~200 MB) o'rnatilmoqda...", flush=True)
    pip("torch", "--index-url", "https://download.pytorch.org/whl/cpu")
    print("[AI] transformers / peft o'rnatilmoqda...", flush=True)
    pip("-r", str(REQS))


def download(repo: str, target: Path, skip_bin_if_safetensors: bool = False) -> None:
    from huggingface_hub import HfApi, snapshot_download
    if (target / "config.json").is_file() and (any(target.glob("*.safetensors")) or any(target.glob("pytorch_model*.bin"))):
        print(f"[AI] {target.name} allaqachon yuklangan.")
        return
    files = HfApi().list_repo_files(repo)
    patterns = ["*.json", "*.txt", "*.model", "*.safetensors"]
    if not (skip_bin_if_safetensors and any(f.endswith(".safetensors") for f in files)):
        patterns.append("pytorch_model*.bin")
    print(f"[AI] {repo} yuklanmoqda -> {target} (bir necha GB, sabr qiling)...", flush=True)
    snapshot_download(repo, local_dir=str(target), allow_patterns=patterns)


def find_zip(explicit: str | None) -> Path | None:
    if explicit:
        return Path(explicit).expanduser()
    for folder in (Path.home() / "Downloads", ROOT, ROOT.parent):
        found = sorted(folder.glob("AstroMed_V5_RESULTS*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)
        if found:
            return found[0]
    return None


def extract_adapter(zip_path: Path) -> None:
    if not zip_path.is_file():
        raise SystemExit(f"[XATO] ZIP topilmadi: {zip_path}")
    target = MODELS / "adapter"
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        prefix = next((n[: n.index("adapter/")] for n in names if "adapter/adapter_config.json" in n), None)
        if prefix is None:
            raise SystemExit("[XATO] ZIP ichida adapter/adapter_config.json yo'q. Kaggle V5.4 natija ZIP'ini tanlang.")
        if target.exists():
            shutil.rmtree(target)
        target.mkdir(parents=True)
        for name in names:
            if name.startswith(prefix + "adapter/") and not name.endswith("/"):
                (target / Path(name).name).write_bytes(zf.read(name))
        cfg = prefix + "inference_config.json"
        if cfg in names:
            (MODELS / "inference_config.json").write_bytes(zf.read(cfg))
    print(f"[AI] Adapter o'rnatildi: {target}")


def main() -> int:
    parser = argparse.ArgumentParser(description="AstroMed offline AI yordamchisini o'rnatish")
    parser.add_argument("--adapter-zip", help="Kaggle'dan yuklangan AstroMed_V5_RESULTS.zip yo'li")
    parser.add_argument("--skip-packages", action="store_true")
    args = parser.parse_args()
    MODELS.mkdir(exist_ok=True)
    if not args.skip_packages:
        install_packages()
    zip_path = find_zip(args.adapter_zip)
    if zip_path is None and not (MODELS / "adapter" / "adapter_config.json").is_file():
        print("[XATO] AstroMed_V5_RESULTS.zip topilmadi (Downloads papkasida qidirildi).\n"
              "Kaggle -> notebook -> Output bo'limidan yuklab oling va qayta ishga tushiring:\n"
              "  run_windows.bat --setup-ai \"ZIP_FAYL_YO'LI\"", file=sys.stderr)
        return 1
    if zip_path is not None:
        extract_adapter(zip_path)
    download(BASE_REPO, BASE_DIR)
    download(TR_REPO, TR_DIR, skip_bin_if_safetensors=True)
    print("[AI] Tayyor! Endi ilovani odatdagidek ishga tushiring: run_windows.bat")
    return 0


if __name__ == "__main__":
    sys.exit(main())

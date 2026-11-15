#!/usr/bin/env python3
"""Cross-platform, local-only AstroMed launcher (Windows and Linux).

Uses an OS-specific virtual environment so that Windows/Linux can share the
same project without changing the system Python installation.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
from urllib.error import URLError
from urllib.request import urlopen
import venv
import webbrowser

ROOT = Path(__file__).resolve().parent
MIN_PYTHON = (3, 10)
IS_WINDOWS = os.name == "nt"
VENV_DIR = ROOT / (".venv-windows" if IS_WINDOWS else ".venv-linux")
REQUIREMENTS = ROOT / "requirements.txt"


def venv_python(env_dir: Path = VENV_DIR, windows: bool = IS_WINDOWS) -> Path:
    return env_dir / ("Scripts/python.exe" if windows else "bin/python")


def valid_environment(python: Path) -> bool:
    if not python.is_file():
        return False
    try:
        result = subprocess.run(
            [str(python), "-c", "import sys; assert sys.prefix != sys.base_prefix"],
            cwd=str(ROOT), capture_output=True, timeout=20, check=False,
        )
        return result.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def requirements_installed(python: Path) -> bool:
    try:
        # A subprocess is used so imports are resolved inside this venv, not
        # inside the Python interpreter running start.py.
        result = subprocess.run(
            [str(python), "-c", "import fastapi, uvicorn"],
            cwd=str(ROOT), capture_output=True, timeout=20, check=False,
        )
        return result.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def prepare_environment(offline: bool = False) -> Path:
    python = venv_python()
    if not valid_environment(python):
        if VENV_DIR.exists():
            raise RuntimeError(
                f"Mavjud virtual muhit ishlamayapti: {VENV_DIR}\n"
                "Ushbu papkani o'chirib, start.py ni qayta ishga tushiring. "
                "data/telemetry.sqlite3 o'chirilmaydi."
            )
        print(f"[AstroMed] Virtual muhit yaratilmoqda: {VENV_DIR.name}", flush=True)
        try:
            venv.EnvBuilder(with_pip=True).create(str(VENV_DIR))
        except (OSError, subprocess.CalledProcessError) as exc:
            raise RuntimeError(
                "Python virtual muhitini yaratib bo'lmadi. Linuxda python3-venv "
                "paketi o'rnatilganini tekshiring (masalan: sudo apt install "
                "python3-venv)."
            ) from exc
        if not valid_environment(python):
            raise RuntimeError("Virtual muhit yaratilgan, lekin Python ishlamayapti.")

    if not requirements_installed(python):
        if offline:
            raise RuntimeError(
                "Offline rejimda kerakli Python kutubxonalari topilmadi. "
                "Internet bor joyda bir marta run_windows.bat yoki "
                "./run_linux.sh ni ishga tushiring, yoki wheel fayllaridan "
                "kutubxonalarni oldindan o'rnating."
            )
        print("[AstroMed] Kutubxonalar virtual muhitga o'rnatilmoqda...", flush=True)
        cmd = [str(python), "-m", "pip", "install", "--disable-pip-version-check", "-r", str(REQUIREMENTS)]
        try:
            subprocess.run(cmd, cwd=str(ROOT), check=True)
        except (OSError, subprocess.CalledProcessError) as exc:
            raise RuntimeError(
                "Kutubxonalarni o'rnatib bo'lmadi. Internet, proxy va "
                "requirements.txt faylini tekshiring."
            ) from exc
        if not requirements_installed(python):
            raise RuntimeError("Kutubxonalar o'rnatildi, lekin import tekshiruvi o'tmadi.")
    return python


def open_browser_after_start(process: subprocess.Popen, port: int) -> None:
    url = f"http://127.0.0.1:{port}"
    health = f"{url}/api/health"
    for _ in range(60):
        if process.poll() is not None:
            return
        try:
            with urlopen(health, timeout=0.5) as response:
                result = json.load(response)
            # Only open a server that looks like AstroMed, not another web app
            # that may already be running on this port.
            if isinstance(result, dict) and result.get("mode") == "SIMULATION_ONLY":
                webbrowser.open(url)
                return
        except (OSError, ValueError, URLError):
            pass
        time.sleep(0.25)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="AstroMed v0.4.0 — Windows/Linux offline simulation launcher"
    )
    parser.add_argument("--offline", action="store_true", help="Internetga chiqmasdan ishga tushirish; o'rnatilgan venv talab etiladi")
    parser.add_argument("--install-only", action="store_true", help="Muhitni tayyorlash, serverni ishga tushirmaslik")
    parser.add_argument("--no-browser", action="store_true", help="Brauzerni avtomatik ochmaslik")
    parser.add_argument("--port", type=int, default=8000, help="Lokal port (standart: 8000)")
    parser.add_argument("--test", action="store_true", help="Avtomatik testlarni ishga tushirish")
    parser.add_argument("--setup-ai", nargs="?", const="", metavar="ZIP",
                        help="Offline AI yordamchini o'rnatish (bir marta, Internet kerak). ZIP: Kaggle AstroMed_V5_RESULTS.zip")
    args = parser.parse_args(argv)

    if sys.version_info < MIN_PYTHON:
        print("[XATO] Python 3.10 yoki yangiroq versiya kerak.", file=sys.stderr)
        return 2
    if not 1024 <= args.port <= 65535:
        parser.error("Port 1024 dan 65535 gacha bo'lishi kerak")
    try:
        python = prepare_environment(offline=args.offline)
    except RuntimeError as exc:
        print(f"[XATO] {exc}", file=sys.stderr)
        return 1

    if args.setup_ai is not None:
        cmd = [str(python), str(ROOT / "tools" / "setup_ai.py")]
        if args.setup_ai:
            cmd += ["--adapter-zip", args.setup_ai]
        return subprocess.run(cmd, cwd=str(ROOT), check=False).returncode
    if args.install_only:
        print("[AstroMed] Tayyor. Keyingi ishga tushirish offline bo'lishi mumkin.")
        return 0
    if args.test:
        return subprocess.run(
            [str(python), "-m", "unittest", "discover", "-s", "tests", "-v"],
            cwd=str(ROOT), check=False,
        ).returncode

    url = f"http://127.0.0.1:{args.port}"
    print(f"[AstroMed] Lokal server: {url}", flush=True)
    print("[AstroMed] Faqat ushbu kompyuterda ochiladi (127.0.0.1).", flush=True)
    print("[AstroMed] To'xtatish: Ctrl+C", flush=True)
    try:
        process = subprocess.Popen(
            [str(python), "-m", "uvicorn", "astro_medical.api:app",
             "--host", "127.0.0.1", "--port", str(args.port)],
            cwd=str(ROOT),
        )
        if not args.no_browser:
            threading.Thread(
                target=open_browser_after_start, args=(process, args.port), daemon=True
            ).start()
        try:
            return process.wait()
        except KeyboardInterrupt:
            print("\n[AstroMed] Server to'xtatilmoqda...", flush=True)
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
            return 0
    except OSError as exc:
        print(f"[XATO] Serverni ishga tushirib bo'lmadi: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

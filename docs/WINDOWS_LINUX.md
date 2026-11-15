# AstroMed v0.3.1 — Windows va Linux uchun qo'llanma

Bu v0.3 loyihasining **operatsion tizimlararo** yangilanishi. AI yaratilmagan. Tibbiy interfeys DEMO / klinik tasdiqlanmagan.

## Talablar

- Windows 10/11 yoki Linux distributivi (Ubuntu, Debian, Fedora va boshqalar).
- **Python 3.10+** (3.10–3.13 tavsiya); Python va `venv` moduli o'rnatilgan bo'lishi kerak.
- Birinchi kutubxona o'rnatilishi uchun internet **yoki oldindan o'rnatilgan virtual muhit**. Keyingi server ishida internet shart emas.
- Lokal brauzer (Edge, Firefox, Chrome).

## Windows

1. ZIP faylni oching va `astro_medical_mvp_v0_3` papkasiga kiring.
2. `run_windows.bat` ni ikki marta bosing yoki Command Prompt/Powershellda ishga tushiring.
3. Ilova `http://127.0.0.1:8000` da ochiladi.
4. Birinchi ishga tushishda `.venv-windows` ochiladi va FastAPI/Uvicorn shu yerga o'rnatiladi; administrator huquqi kerak emas.

```powershell
.\run_windows.bat
.\run_windows.bat --offline
.\run_windows.bat --test
.\run_windows.bat --port 8088
```

`py -3` topilmasa, skript `python` buyruqini sinab ko'radi. Python 3.10+ kerak.

## Linux

1. Python va `venv` ni tekshiring. Ubuntu/Debian uchun:

```bash
sudo apt update
sudo apt install python3 python3-venv
```

2. ZIP ni oching, Terminalni loyiha papkasida oching va quyidagini bajaring:

```bash
chmod +x run_linux.sh
./run_linux.sh
```

Yoki executable huquqlarisiz ishlatish:

```bash
sh run_linux.sh
```

Skript o'z papkasini topadi, `.venv-linux` yaratadi va kerakli kutubxonalarni **global** Python muhitiga emas, virtual muhitga o'rnatadi. Bu zamonaviy Linux distributivlaridagi `externally-managed-environment` xatosining oldini oladi.

```bash
./run_linux.sh --offline       # internetga ulanmasdan ishlash
./run_linux.sh --install-only  # oldindan kutubxonalarni o'rnatish
./run_linux.sh --test          # avtomatik testlar
./run_linux.sh --no-browser    # grafik interfeyssiz server
./run_linux.sh --port 8088
```

Server **faqat o'sha kompyuterdan** ochiladi (`127.0.0.1`). Boshqa qurilmalarga ulanish, autentifikatsiya va xavfsiz tarmoq sozlamalari bu bosqichga kirmaydi.

## Offline rejim bo'yicha eslatma

Birinchi marta virtual muhitni internet mavjud joyda tayyorlang:

```bash
./run_linux.sh --install-only
```

Windowsda:

```powershell
.\run_windows.bat --install-only
```

So'ng internetni uzib, `--offline` bilan ishga tushiring. `--offline` hech qachon pip orqali internetdan paket qidirmaydi. Agar kutubxonalar yo'q bo'lsa, xato xabari chiqariladi; dastur o'zini ishlayotgandek ko'rsatmaydi.

## Bir loyiha papkasini ikkala OS orasida ko'chirish

- Faqat kod, `static/`, `docs/`, `requirements.txt`, `start.py` va `data/telemetry.sqlite3` fayli ko'chiriladi.
- `.venv-windows` va `.venv-linux` papkalarini **ko'chirmang**: OS bo'yicha qayta yaratiladi.
- SQLite bazani ko'chirishdan oldin AstroMed serverini to'xtating. SQLite WAL rejimidan foydalanilsa, WAL holatini yaxlit saqlash uchun zaxiralash usulidan foydalaning.
- Python `Path(__file__)` orqali loyiha papkasini topadi, Windowsning `C:\...` yoki Linuxning `/home/...` yo'liga qattiq bog'lanmagan.

## Diagnostika

- `python3-venv`: Ubuntu/Debian'da `sudo apt install python3-venv`.
- `Python 3.10+`: `python3 --version` yoki Windowsda `py -3 --version`.
- Port band: `--port 8088` bilan qayta ishga tushiring.
- Offline kutubxona yetishmaydi: internet mavjud joyda `--install-only`.
- Interfeys avtomatik ochilmadi: `http://127.0.0.1:8000` ni qo'lda oching.
- Avvalgi tarix: `data/telemetry.sqlite3` faylini server o'chirilgan va zaxira qilingan holatda o'tkazing.

## Sinov xavfsizligi

Har ikki OS'da API va brauzer lokal ishlaydi. Tizim haqiqiy kosmik apparatlarga ulanmaydi va tibbiy qaror uchun sertifikatlanmagan. Shifokor maslahatini almashtirmaydi. AI modeli loyiha egasi bilan kelishmaguncha qo'shilmaydi.

# AstroMed v0.4.0 — Windows + Linux Offline Multi-Crew Medical Support (DEMO)

**3-bosqich ishlaydigan prototipi (UX optimallashtirilgan).** Kosmik missiyada bir nechta kosmonavtning sun'iy tibbiy ko‘rsatkichlarini kuzatish, umumiy xavf signallarini tahlil qilish va tibbiy tekshiruv jarayonini lokal qayd etish uchun mo‘ljallangan. Dizayn desktop, planshet va telefonga moslashadi.

> **MUHIM XAVFSIZLIK CHEKLOVI:** Bu **faqat simulyatsiya va dasturiy sinov**. Tibbiy me’yorlar, ogohlantirish qoidalari va barcha protokollar klinik/operatsion jihatdan **tasdiqlanmagan**. Dastur haqiqiy kosmonavtga tashxis, dori dozasi, davolash buyrug‘i yoki kosmik kema uskunalarini boshqarish buyruqlarini bermaydi. Haqiqiy yordam o‘rniga ishlatish mumkin emas. Ixtiyoriy **offline AI yordamchi** faqat DEMO: tibbiy tasdiqlanmagan.

## v0.4.1: NASA ma’lumotlari (faqat ma’lumot uchun, offline-first)

Yangi **Muhit va xavflar → NASA ma’lumotlari** bo‘limi. Internet bor paytda **“NASA’dan yangilash”** bosiladi, natija lokal SQLite keshga yoziladi va aloqa uzilganda ham ko‘rinadi.

| Manba | Nima uchun | Kalit |
|---|---|---|
| NASA OSDR Search API | radiatsiya, mikrogravitatsiya va kabina muhiti bo‘yicha kosmik biologiya tadqiqotlari | kerak emas |
| NASA DONKI (SEP, FLR) | so‘nggi 30 kundagi quyosh zarralari va alangalari; 72 soatlik kosmik ob-havo eslatmasi | api.nasa.gov (`NASA_API_KEY`, yo‘q bo‘lsa `DEMO_KEY`) |
| OSDR RadLab, EDA | radiatsiya dozimetriyasi va ISS kabina telemetriyasi — portal havolalari sifatida | — |

API: `GET /api/nasa/status` (faqat kesh, tarmoqsiz), `POST /api/nasa/refresh` (tarmoqqa chiqadi, xatoda eski keshni saqlaydi).

**Xavfsizlik chegarasi:** NASA ma’lumotlari tibbiy qoidalarga, xavf darajasiga va AI tahlilga **ta’sir qilmaydi**; faqat ma’lumot va havola. `astro_medical/nasa.py`.

## v0.4.0: Offline AI yordamchi (DEMO)

Ekranning **o‘ng tomonida** har qanday menyu ochilganda ham ko‘rinib turadigan **AI yordamchi** paneli qo‘shildi. Unga ekipaj qaydlarini (har bir qator — bitta qayd) yozasiz, model har bir qaydni tahlil qilib, 4 ta ehtimoliy sabab bo‘yicha holat chiqaradi: **kabina muhiti, ovqat/suv, sensor xatosi, parvoz/faoliyat** (ehtimoliy / rad etilgan / ma’lumot yo‘q) va ko‘rib chiqish uchun tavsiya beradi.

- Ishlash tartibi: **NLLB-200** (o‘zbekcha → inglizcha tarjima) → **Qwen2.5-3B + AstroMed LoRA (V5.4)** har bir qayd uchun 13 ta variantdan bittasini tanlaydi → aniq qoidalar yakuniy xulosani yig‘adi.
- **Hammasi shu kompyuterda, internetsiz** ishlaydi (CPU, int8 kvantlash, ~7 GB RAM). Bitta tahlil odatda 1–3 daqiqa.
- Ishonch < 0.7 bo‘lgan qayd bo‘yicha aniq tavsiya berilmaydi (“Qo‘lda tekshiring”).
- Sinov natijalari (sun’iy ma’lumot): yangi sinov 177/196 holat to‘liq to‘g‘ri, xavfli tavsiya 4 ta; V3 sinovi 37/49. Tibbiy tasdiq **yo‘q**.

### O‘rnatish (bir marta, Internet kerak, ~9 GB)

1. Kaggle → notebook → **Output** bo‘limidan `AstroMed_V5_RESULTS.zip` ni yuklab oling (odatda Downloads papkasiga tushadi).
2. Loyiha papkasida:

```powershell
.\run_windows.bat --setup-ai
```

ZIP boshqa joyda bo‘lsa: `.\run_windows.bat --setup-ai "D:\yol\AstroMed_V5_RESULTS.zip"`. Linux: `./run_linux.sh --setup-ai`.

3. Keyin ilovani odatdagidek ishga tushiring (`run_windows.bat`). Panelda “Namuna” → “Tahlil qilish”. Birinchi tahlilda model 1–3 daqiqa yuklanadi.

Model o‘rnatilmagan bo‘lsa ilova avvalgidek ishlayveradi, panel esa o‘rnatish yo‘l-yo‘rig‘ini ko‘rsatadi. Sozlamalar: `ASTRO_AI_THRESHOLD` (standart 0.7), `ASTRO_AI_QUANT` (`int8` | `bf16` | `fp32`), `ASTRO_AI_DIR` (modellar papkasi).

API: `GET /api/ai/status`, `POST /api/ai/load`, `POST /api/ai/analyze` (`{"records": {"E1": "matn", ...}}`, 12 tagacha), `GET /api/ai/jobs/{id}`, `GET /api/ai/demo`.

## v0.3.2: Yengil va qulay navigatsiya

- 5 ta asosiy menyu: **Missiya**, **Ekipaj**, **Muhit**, **Favqulodda yordam**, **Ogohlantirishlar/jurnal**. Ichki tablarda individual tibbiy monitoring, HAB/LAB va hodisalar tarixi mavjud.
- Bir vaqtda faqat **bitta ishchi ekran** ko‘rsatiladi; boshqalari yashirin va qayta chizilmaydi.
- Grafik tarixi faqat individual monitoring ochilganda so‘raladi, hodisalar tarixi faqat jurnal ochilganda, protokol/inventar va kasallik hodisalari esa favqulodda yordam birinchi ochilganda yuklanadi.
- Faol veb sahifada ma'lumot yangilanishi 4 s, fon tabida 20 s. **Serverdagi sog‘liq monitoringi bundan mustaqil har 2 s** ishlashda davom etadi.
- Barcha ekranlarda umumiy xavf holati, aloqaning holati va faol ogohlantirishlar soni ko‘rsatiladi. Kichik ekranlar, klaviatura, havolani bevosita ochish (`#individual`, `#events`) qo‘llab-quvvatlanadi.
- `docs/STAGE_4_REQUIREMENTS.md` — AI bo‘yicha keyingi bosqich talablari; model tanlanmagan.

## Nima qo‘shildi (3-bosqich)

1. **Offline protokollar katalogi:** 9 ta simulyatsion tekshirish ro‘yxati, `DEMO` approval status, `0.3-demo.1` versiya, individual/ekipaj/modul/missiya qamrovi va kerakli demo resurslari.
2. **Hodisa boshqaruvi:** yangi tibbiy vaziyatni ochish, bitta yoki bir nechta kosmonavt va zonalarni bog‘lash, `INC-...` identifikatori, qayd matni, signal va snapshot.
3. **Qadamba-qadam kuzatish:** `pending → acknowledged → completed` yoki `blocked`; kim va qachon qayd qilgani auditda saqlanadi. Bu statuslar **faqat DEMO tekshiruvga** tegishli, real tibbiy muolaja bajarilganini tasdiqlamaydi.
4. **Protokol va resurs tekshiruvi:** demo inventaridagi resurs yetishmasa, bajarildi deb belgilash bloklanadi; `blocked` deb qayd qilish mumkin.
5. **Ekipaj ismlari va holat tarixi:** hodisa paytidagi kosmonavtlarning ismi/ID saqlanadi, keyin ekipajdan chiqarilsa ham yozuv qoladi. Voqealar `Hodisalar tarixi` va `outbox`ga kiritiladi.
6. **Aloqasiz ishlash:** mahalliy FastAPI+SQLite serverda monitoring va hodisa qaydlari ishlaydi. Yerga xabar yuborish **haqiqiy emas**; faqat xabar navbati/delivery simulyatsiyasi.
7. **Responsive dizayn:** telefonlar uchun ochilib-yopiladigan menyu va bitta ustunli shakllar, planshet uchun soddalashtirilgan grid, desktop uchun ikki ustunli panel; klaviatura fokus uslubi va 44 px atrofidagi mobil boshqaruvlar.

### Oldingi bosqichlar saqlangan

- 4 demo kosmonavt (12 tagacha), HAB/LAB modul, ayrim alomatlarni qo‘lda kiritish va simulyatsion ssenariylar;
- Individual puls, SpO₂, harorat, bosim, nafas; zonalar bo‘yicha O₂, CO₂, bosim, harorat, namlik, radiatsiya va texnik signallar;
- Trend, yaroqsiz/eskirgan sensorni aniqlash, bir nechta kosmonavtdagi umumiy o‘zgarishlarni muhit bilan solishtirish;
- Sensorlarning kelajakdagi apparat interfeysi: `MissionTelemetrySource.read()`; hech qachon yashirin ravishda sintetikga o‘tmaydi.

## Ishga tushirish — Windows 10/11 va Linux

**Python 3.10 yoki undan yangi versiya kerak.** Yangi `start.py` har bir OS uchun alohida virtual muhit yaratadi. Kutubxonalar tizimdagi global Python'ga o'rnatilmaydi.

**Windows (CMD / PowerShell):**

```powershell
.\run_windows.bat
```

**Linux (Terminal):**

```bash
chmod +x run_linux.sh
./run_linux.sh
```

Ubuntu/Debian uchun kerak bo'lsa: `sudo apt install python3 python3-venv`. Server ochilganda brauzerda **http://127.0.0.1:8000** manzilini ko'ring. Serverni `Ctrl+C` bilan to'xtating.

Har ikki platformada qo'shimcha buyruq parametrlari bir xil:

- `--install-only` — kutubxonalarni birinchi marta o'rnatish, serverni ishga tushirmaslik;
- `--offline` — hech qanday kutubxona yuklamasdan ishga tushirish (oldindan o'rnatilgan muhit kerak);
- `--test` — avtomatik testlarni ishga tushirish;
- `--no-browser` — brauzerni avtomatik ochmaslik;
- `--port 8088` — boshqa portda ishga tushirish.

**Muhim:** Birinchi o'rnatishda Internet talab qilinishi mumkin. Tayyor virtual muhit bilan keyingi ishlashda Internet talab qilinmaydi. `.venv-windows` yoki `.venv-linux` OSga xos, ularni boshqa tizimga ko'chirmang. SQLite ma'lumotlari `data/telemetry.sqlite3` da qoladi. Dastur faqat shu kompyuterda (`127.0.0.1`) ishlaydi.

Batafsil yo'riqnoma: [`docs/WINDOWS_LINUX.md`](docs/WINDOWS_LINUX.md).

## Sinov uchun tavsiya etilgan oqim

- **Individual:** `single_low_spo2` ssenariysini tanlang, bir necha marta `Namuna` tugmasini bosing. `Ogohlantirishlar`dagi `Hodisa yaratish` tugmasini sinang.
- **Jamoaviy:** `shared_co2` ssenariysini 8–10 namuna davomida ishlating, `Umumiy sababni tekshirish` topilmasidan hodisani oching. Ismlar, modullar va saqlangan dalillarni ko‘ring.
- **Radiatsiya:** `space-environment` protokolida demo inventarda `dosimeter` yo‘q; `completed` ga o‘tish bloklanadi.
- **Offline:** `Aloqani uzish` ni bosing, hodisa yarating va qadamni qayd eting; mahalliy jurnalda qolganini tekshiring. `Aloqani tiklash` haqiqiy uzatish qilmaydi.
- **Ko‘p qurilma:** Telefon/planshet kengligida interfeysning joylashuvi, menyu va qadam maydonlarini tekshiring (lokal serverga boshqa qurilmadan ulanish default bo‘yicha yopiq).

## API (asosiy yangi endpointlar)

| Metod | Endpoint | Vazifa |
|---|---|---|
| GET | `/api/protocols` | Demo protokollar va versiyalar |
| GET | `/api/protocols/{id}` | Protokol tafsilotlari |
| GET | `/api/resources` | Demo inventar |
| GET | `/api/incidents` | Hodisalar ro‘yxati |
| POST | `/api/incidents` | Hodisa ochish |
| GET | `/api/incidents/{id}` | Hodisa + qadamlar + audit |
| PATCH | `/api/incidents/{id}/steps/{index}` | Qadam holatini qayd etish |
| POST | `/api/incidents/{id}/review` | Barcha qadamlar ko‘rib chiqilgach demo qaydni yakunlash |

Qolgan v0.2 endpointlar saqlangan. Swagger interfeysi: **http://127.0.0.1:8000/docs**.

**POST `/api/incidents` namunasi:**

```json
{
  "protocol_id": "crew-investigation",
  "crew_ids": ["C01", "C02"],
  "zone_ids": ["HAB"],
  "origin_code": "MANUAL_REPORT",
  "actor_id": "C01",
  "note": "Sinov kuzatuvi"
}
```

**PATCH qadam namunasi:**

```json
{"status":"acknowledged","actor_id":"C01","note":"Tekshirildi (DEMO)"}
```

## Avvalgi v0.2.1 SQLite bazasini ko‘chirish

Yangi versiya ZIP ichida **bo‘sh `data/` papka** bilan beriladi. Eski versiyadagi ma’lumotlarni o‘tkazish uchun serverni to‘xtating, eski `data/telemetry.sqlite3` faylingizdan zaxira nusxa oling va yangi papkaning `data/` qismiga ko‘chiring. Dastur ishga tushganda eski jadvallarga tegmasdan yangi `incidents`, `incident_steps`, `incident_audit` jadvallarini hosil qiladi. Eski yozuvlar nomi avvalgi saqlangan ma’lumot doirasida tiklanadi, yo‘q ism taxmin qilinmaydi.

## Arxitektura va xavfsizlik chegarasi

- `astro_medical/clinical.py` — lokal DEMO protokollar va sintetik inventar.
- `astro_medical/incidents.py` — SQLite hodisa modeli, qadam holatlari va audit.
- `astro_medical/service.py` — sensor tahlili, ekipaj nomlari, hodisalar va outbox.
- `astro_medical/api.py` — REST API (`127.0.0.1`, lokal rejim).
- `astro_medical/sources.py` — sintetik signal va keyingi haqiqiy sensorga adapter kontrakti.
- `static/` — HTML/CSS/JS, ekranlarga mos interfeys.

**Haqiqiy foydalanishdan oldin hal qilinishi shart:** mustaqil kosmik tibbiy ekspertiza, klinik protokollarni tasdiqlash, sifatli tibbiy va muhit sensorlari, sensor xatolarini baholash, rollar/avtorizatsiya, maxfiy ma’lumotlarni shifrlash, kiberxavfsizlik, ishdan chiqishdan himoya, avionika/aloqa bilan integratsiya va regulyator tekshiruvlari. Demo ma’lumotlar haqiqiy tarix yoki parvoz ko‘rsatkichlari sifatida ko‘rsatilmaydi.

**AI modeliga kelganda:** loyiha egasi bilan maslahatlashilmaguncha model yaratish, tanlash va integratsiya qilish amalga oshirilmaydi.

## Test natijasi

43 ta avtomatik test (3-bosqich API, audit, crew snapshots, offline outbox, status cheklovlari, oldingi multi-crew monitoring) muvaffaqiyatli. Interfeys 1440/820/390 px kengliklarda brauzer renderi, gorizontal overflow va JS xato tekshiruvidan o‘tdi. Mobil interfeysda hodisa yaratish va qadam holatini o‘zgartirish real lokal APIga ulanadigan brauzer sinov ko‘prigi orqali sinovdan o‘tgan.

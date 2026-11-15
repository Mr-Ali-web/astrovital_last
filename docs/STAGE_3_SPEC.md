# AstroMed v0.3 — 3-bosqich: amalga oshirilgan funksiyalar

## Status

**Demo dasturiy MVP tayyor.** Hali tibbiy jihatdan validatsiyadan o‘tmagan; AI modeli kiritilmagan. Boshidan rejalashtirilgan talablar `STAGE_3_PLAN_ORIGINAL.md` da saqlangan.

## Amalda mavjud

- 9 ta lokal, versiyalangan `DEMO` tekshirish protokoli: `id`, `title`, `description`, `scope`, `required_resources`, `steps`, `approval_status`, `version`, `allow_clinical_use=false`.
- Individual, jamoaviy, zona, missiya bo‘yicha saqlanadigan hodisa ID va crew ID+name snapshot; signal va sensor snapshot (faqat signal bog‘langanda).
- SQLite `incidents`, `incident_steps`, `incident_audit` jadvallari, event/outbox bilan integratsiya, keyingi bosqichda real Earth transport adapteri uchun kontrakt.
- Qadamlar: `pending`, `acknowledged`, `completed` (faqat demo tekshiruv), `blocked`; o‘zgarishlar auditga yoziladi.
- Noto‘g‘ri ID, protokol qamrovi, noma’lum ekipaj/modul va noto‘g‘ri signal rad etiladi. Harakatni kim qayd etgani saqlanadi. Hodisa yakunlangach o‘zgartirish bloklanadi.
- Demo inventarda resurs yo‘q bo‘lsa `completed` status bloklanadi.
- HTML/CSS/JS responsive panel, 790/500 px media querylar, mobil menyu va fokus holati, klaviatura va teginish interfeysi.
- 36 ta avtomatik sinov; mobil foydalanuvchi oqimi brauzer + FastAPI `TestClient` orqali sinovdan o‘tgan.

## Tibbiy ehtiyot chorasi

Protokollar *sog‘liq monitoringini qayd etish va bortning haqiqiy tasdiqlangan yo‘riqnomasiga yo‘naltirish* uchun yaratilgan namunalardir. Dori, doza, operatsiya yoki mustaqil davolash buyrug‘i yo‘q. Klinika uchun `VALIDATED` rejimi amalga oshirilmagan: bu ataylab.

## Keyingi ishlarda

- Professional tasdiqlangan kontentni alohida nazorat ostida import qilish, versiya imzolari va o‘zgartirish nazorati.
- Hodisalar uchun rol va autentifikatsiya, auditga ishonchli identifikatsiya, lokal maxfiy ma'lumotni shifrlash.
- Offline native/PWA, redundans va lokal jadval asosidagi qayta tekshirish ogohlantirishlari.
- Hardware sensor adapterlari va real Earth transport adapterlari bilan xavfsizlik sinovi.
- AI faqat loyiha egasi bilan kelishilgandan keyin; hali yo‘q.

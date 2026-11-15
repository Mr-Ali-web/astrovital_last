# AstroMed bosqichlari

## 1-bosqich — ✅ Tayyor (v0.1)

Individual sun’iy telemetriya, lokal dashboard, SQLite, aloqa uzilishi simulyatsiyasi, DEMO qoidalar.

## 2-bosqich — ✅ Dasturiy prototip (v0.2)

- 4 kishilik boshlang‘ich ekipaj va 2 xona/zone, 1–12 kishi qo‘shish imkoniyati.
- Har bir a’zoni alohida baholash va nazorat qilish.
- Qisqa oynada individual trend tekshirish.
- Bir nechta a’zodagi signallarni zona va uskuna signallari bilan solishtirish.
- `environment_possible`, `unexplained_crew_cluster`, `shared_sensing_issue`, `space_environment_possible` turlari.
- Signal sifati va yangi/eski o‘lchovlarni tekshirish; mahalliy hodisalar tarixi.
- Kengaytirilgan API, interaktiv veb panel va avtomatik testlar.

**Cheklov:** demo qoidalar klinik validatsiyadan o‘tmagan. Haqiqiy sensorlar ulanmagan. Real vaqt oynalari, uskuna normalizatsiyasi va ishonchlilik tahlili rivojlanishi kerak.

## 2.1-kichik yangilanish — ✅ Hodisa tarixida kosmonavt ismlari (v0.2.1)

- Shaxsiy hodisalarda voqea vaqtidagi kosmonavt ismi va `crew_id` SQLite'ga yoziladi.
- Umumiy ekipaj topilmalariga bog'liq hodisalarda ta'sirlangan a'zolar ismlari saqlanadi.
- Ro'yxatdan chiqarilgan kosmonavtning eski eventlarida ism saqlanadi.
- Eski bazaga ustunlar qo'shish va ismi aniq tiklanadigan yozuvlarni migratsiya qilish.
- Yangi sinovlar va yangilangan hodisalar paneli.

## 3-bosqich — Klinik bilimlar bazasi va favqulodda protokollar

- Parvoz tibbiyoti mutaxassislari bilan qaysi holatlar real ma’lumot bilan aniqlanishini kelishish.
- Versiyalangan, rozilik/tasdiq yozuvlariga ega protokollar bazasi; alomat/jihoz/bortdagi resurs bo‘yicha tanlash.
- Mustaqil tekshiruv, tibbiy xavfsizlik sinovlari, false positive/false negative ko‘rsatkichlari.
- Dorilar, jarohat va tibbiy amaliyotlarga oid mustaqil avtonom tavsiyalar **tasdiqlanmaguncha yoqilmaydi**.

Batafsil texnik reja: `docs/STAGE_3_SPEC.md`. v0.3 — favqulodda DEMO workflow; v0.3.2 — yengil navigatsiya va faqat faol ekran yangilanishi. Klinik protokollar hali tasdiqlanmagan.

## 4-bosqich — AI modeli (FAKAT FOYDALANUVCHI BILAN MASLAHATLASHGANDAN KEYIN)

Talablar: `docs/STAGE_4_REQUIREMENTS.md`. **Majburiy STOP nuqtasi:** foydalanuvchidan AI model arxitekturasi, lokal qurilma resurslari, ta’lim/trening ma’lumotlari, tillar, audit va nazorat chegaralari bo‘yicha rozilik olinadi. Hozir AI modeli mavjud emas. AI hech qachon o‘zi favqulodda klinik buyruq ishlab chiqarmaydi.

## 5-bosqich — Haqiqiy sensor, Yer aloqasi va xavfsizlik

- O‘lchovlarni haqiqiy qurilmalardan olish uchun kalibrlangan, sinovdan o‘tgan adapterlar.
- Qayta ulanadigan, imzolangan/shifrlangan yer aloqasi / kechikishga chidamli uzatish.
- Auth, ruxsat, zaxira, watchdog, apparat nosozligi, energetik mustahkamlik, audit.
- Bort tizimlari bilan birlashish faqat tasdiqlash va mustaqil xavfsizlik ekspertizasidan keyin.

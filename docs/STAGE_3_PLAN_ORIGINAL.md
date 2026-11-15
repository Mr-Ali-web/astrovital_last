# AstroMed — 3-bosqich texnik vazifasi (reja, hali qurilmagan)

**Nomi:** Offline favqulodda yordam va klinik bilimlar bazasi. **AI modeli yo'q.**

## Maqsad

Ekipajning bir a'zosi yoki bir nechtasida tibbiy xavf signali kelganda tizim quyidagilarni bajaradi:
1. signal va sensor ma'lumotlari ishonchliligini tekshiradi;
2. individual xavfni umumiy atmosfera/uskuna/radiatsiya ehtimollari bilan solishtiradi;
3. bortda mavjud *tibbiy jihatdan tasdiqlangan* ko'rsatmalar orasidan vaziyatga mos yo'riqnomani topadi;
4. ekranda aniq, kuzatiladigan ish oqimini ochadi va bajarilgan qadamlarni jurnalga yozadi;
5. Yer bilan aloqa bo'lmasa ham ishlaydi; tiklanganda hisobotni yuborishga tayyorlaydi.

## Ishchi modullar

### A. Bortdagi klinik protokollar katalogi
- Versiya, nomi, vaziyat turi, xavf toifasi, qamrov (bitta kosmonavt/ekipaj/modul), kerakli uskunalar, alomatlar, muqobil sabablar.
- `approval_status` qiymatlari: `DEMO`, `DRAFT`, `VALIDATED` va tasdiqlovchi tomon, sana/versiya maydonlari.
- Audit tarixini saqlash: kim, qachon, qaysi protokol versiyasini ko'rdi.
- Tasdiqlanmaguncha haqiqiy davolash ko'rsatmalari yoqilmaydi: faqat simulyatsiya rejimi.

### B. Vaziyat klassifikatori (qoidaviy, AI emas)
- Individual: og'ir jarohat/alomat, SpO2 o'zgarishi, yurak ritmi, hush, suvsizlanish va boshqalar.
- Jamoaviy: bir nechta kosmonavtda o'zgarish; xavfni HAB/LAB va butun missiya bo'yicha ajratish.
- Muhit sababini **tasdiqlamaydi**; mos keladigan dalil va qarshi dalillarni ko'rsatadi.
- Yetishmayotgan sensorni normal deb hisoblamaydi; `UNKNOWN` tekshirish talab qiladi.

### C. Favqulodda yordam ekrani
- Katta, tushunarli xavf belgisi va ta'sirlangan ekipaj a'zolari ismlari.
- Bort protokollaridan tanlangan *tasdiqlangan* qadamma-qadam ko'rsatmalar.
- Qadam statuslari: `pending` / `acknowledged` / `completed` / `blocked`.
- Kim bajardi, qachon bajardi, qaysi ko'rsatkichlar o'zgardi — auditda qayd etiladi.
- Rejalashtirilgan “eslatish / qayta tekshirish” mahalliy soat bilan, tashqi internetga bog'liq emas.
- Kritik holatda dashboard, tavsiya ekrani va jurnal bir xil hodisa ID'siga bog'lanadi.

### D. Tibbiy resurslar ro'yxati
- Jihoz, sarf materiallari, dori inventari va ularning mavjudligi.
- Protokolni bajarish uchun kerakli vosita bo'lmasa, “bajarib bo'lmaydi — alternativ protokolni ekipaj/tibbiy mas'ul tekshirsin” degan holat.
- Dori dozasi yoki invaziv amaliyotni avtomatik ishlab chiqish/berish yo'q.

### E. Offline aloqa va hisobot
- Har bir hodisaga yagona ID; vaqt belgisi, shaxs(lar), muhit, sensor sifati, qilingan amallar.
- Mahalliy jurnal va Earth outbox; “simulated delivered” haqiqiy Yerga uzatish emas.
- Keyin real aloqa qo'shilishi uchun jo'natish kontrakti (adapter).

### F. Sinovlar va tasdiqlash
- Kamida ushbu ssenariylar: bir kishida jarohat, jamoada CO2 oshishi, bir zona ventilyatsiyasi, radiatsiya, sensor uzilishi, barcha sensorlar noma'lum, aloqasiz rejim.
- Tekshirish: yaroqsiz/mos kelmaydigan protokol tanlanmasligi, eski protokol versiyasi nazorati, auditda ism saqlanishi, xato signal tasdiq tashxis bo'lmasligi.
- Tibbiy protokol faqat mustaqil kosmik tibbiyot mutaxassisi ko'rib chiqqan va testdan o'tganidan keyin klinik rejimda ishlashi mumkin.

## 3-bosqich yakunlash mezonlari
1. Protokol katalogi offline ishlaydi va o'z versiyasini ko'rsatadi.
2. Bir yoki bir nechta ekipaj a'zosida hodisa yuz bersa tegishli ekran ochiladi.
3. Noma'lum yoki yaroqsiz ma'lumot bo'lsa “tasdiqlanmagan/noaniq” holat ko'rinadi.
4. Xavfni umumiy zona/missiya bilan bog'lovchi ma'lumot tekshiriladi.
5. Protokolning demo/tasdiqlangan holati aniq ajratiladi.
6. Xabar navbati, ma'lumotlar va amallar aloqasiz yoziladi.
7. Har bir bajarilgan amal va barcha ta'sirlangan kosmonavtlar nomi hodisalar tarixida saqlanadi.
8. Tibbiy xavfsizlik, API va ma'lumotlar bazasi migratsiyasi avtomatik sinovlardan o'tadi.

## Keyingi AI bosqichi (alohida)

AI modeli qaysi bo'lishi, nimaga ruxsati borligi, qaysi tilda ishlashi, qaysi qurilmada offline ishlashi va qanday tekshirilishi — **foydalanuvchi bilan alohida maslahatlashilgandan keyin** hal etiladi. 3-bosqichda generativ AI yaratilmaydi.

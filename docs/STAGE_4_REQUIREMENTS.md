# AstroMed — 4-bosqich texnik talablari (REJA / AI hali YO‘Q)

**Maqsad:** avtonom tibbiy qarorlarni qo‘llab-quvvatlash modulini loyihalash. U yer aloqasisiz ham yordamchi ma’lumot beradi, ammo mavjud tasdiqlangan protokollar va xavfsizlik qoidalari ustuvor bo‘ladi. Modelni tanlash / yaratish / o‘qitish / ulash **foydalanuvchi bilan maslahatdan keyin** boshlanadi.

## A. Boshlashdan oldingi majburiy kelishuv
1. **Asosiy vazifalar:** alomatlarni tushunish, avvalgi sensor trendlarini izohlash, ko‘p kosmonavtdagi o‘zgarishlar uchun ehtimoliy umumiy sabablarni tekshirish; *tashxis yoki davolashni avtomatik berish emas*.
2. **Model strategiyasi:** mahalliy kichik til modeli + tasdiqlangan protokollar qidiruvi, yoki faqat strukturalangan qoidaviy modul. Variantlar egasi bilan muhokama qilinadi. Hozir hech biri tanlanmagan.
3. **Hisoblash cheklovlari:** Windows va Linux apparati, CPU/GPU, RAM, disk, quvvat, javob vaqti, internet yo‘qligi. Prototip uchun maqsadlar kelishiladi; bu ko‘rsatkichlar hali o‘lchanmagan.
4. **Tillar:** avvalo o‘zbekcha; ehtiyojga ko‘ra inglizcha/ruscha; tibbiy atamalar uchun bir xil lug‘at.
5. **Ma’lumot manbalari:** faqat litsenziyasi aniq, mutaxassis ko‘rib chiqqan protokollar; sun’iy ko‘rsatkichlar haqiqiy klinik dalil o‘rnini bosa olmaydi.
6. **Maxfiylik:** individual tibbiy ma’lumotlardan foydalanish huquqlari, lokal shifrlash va ehtiyot nusxa.

## B. Modullar
- Sensor va ekipaj kontekstini AI uchun **faqat o‘qish huquqiga ega** ma’lumot paketi orqali uzatish; signal sifati, vaqt tamg‘alari, modul, manba va noaniqlik saqlansin.
- Tasdiqlangan protseduralarni qidirish (RAG yoki boshqa tasdiqlangan indeks); har bir yordam matni uchun protokol nomi, versiyasi, tegishli bo‘limi va tasdiq holati.
- **Xavfsizlik darvozasi:** klinik yoki apparat boshqaruvi buyruqlarini mustaqil bajarmaslik; tasdiqlanmagan protokolni klinik tavsiya sifatida bermaslik; noma’lum bo‘lsa "ma’lumot yetarli emas" qaytarish.
- Favqulodda vaziyatda AI ishlamasa ham mustaqil ogohlantirish, yong‘in/kislorod/radiatsiya signallari va offline tekshiruv interfeysi davom etsin.
- Ekipaj bo‘yicha differensial tekshirish: bitta a’zo vs ko‘p a’zo, modul/ventilyatsiya/CO₂/radiatsiya dalillari; taxminlar va ularga qarshi dalillar alohida ko‘rsatilsin.
- Har bir javob uchun audit: vaqt, ekran/ekipaj/hodisa ID, ishlatilgan ma’lumotlar, model/protokol versiyasi va foydalanuvchi tasdig‘i.

## C. Foydalanuvchi interfeysi va ishlash tezligi
- AI interfeysi yangi alohida ishchi ko‘rinish bo‘ladi; foydalanuvchi ochmaguncha model RAMga yuklanmaydi. Boshqa oynalar ishlamay turganda grafik render/fetch to‘xtaydi.
- Favqulodda ogohlantirishlar ekrandan qat’i nazar ko‘rinadi; fokus va o‘qilishi qulay boshqaruv, mobil klaviatura va 320–1440px diapazon sinovlari.
- RAM/CPU/kechikish real kompyuterda profil qilinadi; chegaradan oshsa AI moduli to‘xtaydi, **monitoring to‘xtamaydi**.
- Oflayn rejim, portativ kutubxonalar, Windows/Linux ishga tushirish va qayta tiklanish sinovi.

## D. Verifikatsiya va qabul shartlari
- Manba bilan asoslangan javoblar, gallyutsinatsiyani tanish, noto‘g‘ri ogohlantirish va o‘tkazib yuborilgan ogohlantirishni alohida o‘lchash.
- Bitta kosmonavt nosoz sensori, 3 a’zoda o‘xshash muammo, modullar o‘rtasidagi farq, CO₂ uskuna nosozligi, radiatsiya anomaliyasi va aloqa yo‘qolishi uchun ssenariy testlari.
- "Javob bilmayman / klinik yordam zarur" mexanizmi; AI tavsiyasi mavjud muhim signal bilan ziddiyatga kirsa ustuvor qoidalar ko‘rsatiladi.
- Tibbiy mutaxassislar roziligi va xavfsizlik sinovlaridan o‘tmaguncha faqat **DEMO** rejimi.

## E. Bosqich darvozalari
**4.0 — Qaror:** foydalanuvchi bilan vazifalar, model/no-model strategiyasi va apparat byudjetini kelishish. 
**4.1 — Tayyorlash:** klinik manbalar, dalillar formati, xavfsizlik siyosati, test ma’lumotlarini tanlash.
**4.2 — Prototip:** faqat ruxsatdan keyin lokal qidiruv va ehtiyotkor tavsiya interfeysi.
**4.3 — Sifat sinovi:** resurslar va klinik xavfsizlik testlari, harakatlar auditi.

**Joriy holat:** yuqoridagilar REJA; hech bir AI modeli hali tanlanmagan yoki o‘rnatilmagan.

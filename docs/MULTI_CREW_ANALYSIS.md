# Ekipaj bo‘ylab tahlil: qoidalar va dalillar

## Asosiy yondashuv

1. **Individual daraja:** har bir Cxx a’zoning sinov ko‘rsatkichlari va alomatlari mustaqil tekshiriladi.
2. **Zona darajasi:** HAB/LAB atmosfera va radiatsiya kanallari mustaqil tekshiriladi.
3. **Muhandislik darajasi:** CO₂ tozalash va HAB ventilyatsiya holati (`0` — nosozlik signali; `1` — OK) qayd etiladi.
4. **Missiya darajasi:** bir vaqt oynasida kamida **ikki ekipaj a’zosining** nafas/oksigenatsiya ko‘rsatkichlari o‘zgarsa yoki kamida ikki kishi bosh aylanishini xabar qilsa, umumiy topilma chiqariladi.
5. Agar **muhit yoki uskuna** signallari ham mavjud bo‘lsa, `environment_possible`; bo‘lmasa `unexplained_crew_cluster` qaytariladi.
6. Radiatsiya barcha zonalarda oshsa `space_environment_possible`. Bir nechta o‘lchov sensori yo‘qolsa `shared_sensing_issue`, **kasallik** deb atalmasin.
7. Topilmada dalillar, nima noma’lumligi, tekshirilishi kerak bo‘lgan signallar va offline demo checklist havolasi bo‘ladi.

## Ehtiyot choralari

- Umumiy simptomlar **avtomatik ravishda** kabina nosozligini anglatmaydi.
- Muhit signallari va alomatlar bir paytda bo‘lsa ham, **sabab isbotlanmaydi**.
- Lokal zonadagi kuzatuvlarni barcha kosmonavtlarga nisbat berishdan ehtiyot bo‘linadi.
- Agar sensor ma’lumotlari yo‘q bo‘lsa, "hammasi yaxshi" deyish taqiqlanadi.
- Dastur sun’iy sinovda “xavfli” deb belgilangan obyekt uchun avtonom davolash tavsiyasini bermaydi.
- Ekipaj a’zolarining kasallikka xos shaxsiy bazalari va parvoz oldi tekshiruvlari hali yo‘q.
- Ekipaj bo‘ylab sinxronlash hozir **bir xil simulator `.read()` chaqiruvida** ishlaydi. Real oqimlar kelganda buffer, vaqt toleransi, sensor mustaqilligi va asinxron interleaving qo‘shilishi kerak.
- Tashqi radiatsiya sababini aniqlash uchun mustaqil kosmik ob-havo va dozimetr ma’lumotlari talab qilinadi.

## Demo signallari uchun sun’iy me’yorlar

Koddagi `DEMO_LIMITS` qiymatlari **faqat test chegaralari**. NASA klinik standarti emas. Threshold konfiguratsiyasini haqiqiy reysga ko‘chirib bo‘lmaydi. Trendlarda median yarmi / median yarmi tenglashtiriladi, kamida 6 sifatli namuna kerak.

## Keyingi yo‘nalish

- Xavf ehtimoli va noaniqligini klinik mutaxassis tekshirgan model asosida ifodalash (model qurishdan oldin foydalanuvchi roziligi).
- Ekipajning alohida o‘rganilgan fiziologik bazalari.
- Vazifalar, parvoz fazasi, EVA (tashqi chiqish), joylashuv va modullar bo‘ylab havo oqimi ta’siri.
- Qarama-qarshi signallar, noto‘g‘ri musbat/inkoriy xavflar, false correlation va muhim alomatni o‘tkazib yuborishni tekshirish.
- Favqulodda protokollarni tibbiy mutaxassislar tomonidan tasdiqlatish.

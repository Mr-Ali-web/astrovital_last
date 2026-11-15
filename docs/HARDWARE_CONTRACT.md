# Hardware integratsiya kontrakti — AstroMed 0.2

`MissionTelemetrySource.read() -> MissionTelemetry` haqiqiy qurilmalarni keyinchalik ulash uchun adapter nuqtasi. `DemoSimulator` bilan `HardwareSource` **alohida** ishlaydi. Uskuna chiqishi noaniq bo‘lsa, `good` sifatiga sun’iy ma’lumot berilmaydi.

## Yagona namuna (qisqartirilgan JSON)

```json
{
  "timestamp": "2026-11-14T08:15:00+00:00",
  "source": "synthetic-simulator",
  "scenario": "normal",
  "crew": {
    "C01": {
      "crew_id": "C01",
      "name": "Kosmonavt 01",
      "zone_id": "HAB",
      "vitals": {
        "heart_rate": {"value": 78.0, "unit": "bpm", "quality": "good", "sensor_id": "SIM-C01-heart_rate", "captured_at": "2026-11-14T08:15:00+00:00"},
        "spo2": {"value": 98.0, "unit": "%", "quality": "good", "sensor_id": "SIM-C01-spo2", "captured_at": "2026-11-14T08:15:00+00:00"}
      },
      "symptoms": []
    }
  },
  "zones": {
    "HAB": {
      "o2_partial": {"value": 21.1, "unit": "kPa", "quality": "good", "sensor_id": "SIM-HAB-o2_partial", "captured_at": "2026-11-14T08:15:00+00:00"}
    }
  },
  "systems": {
    "scrubber_ok": {"value": 1, "unit": "boolean", "quality": "good", "sensor_id": "SIM-SCRUBBER", "captured_at": "2026-11-14T08:15:00+00:00"}
  }
}
```

Bu **strukturaviy misol**: amalda implementatsiya har bir faol ekipaj a’zosi uchun barcha kuzatiladigan kanallarni, har bir faol modul uchun kerakli muhit kanallarini to‘ldirishi kerak. O‘lchanmaydigan kanal `value=null, quality="missing"`; hech qachon xayoliy qiymat kiritilmaydi.

## Uskuna joriy qilishdan oldingi nazoratlar

1. Qurilma identifikatori, sensor turi/seriya raqami, kalibrlash va versiya ma’lum bo‘lsin.
2. NTP/GNSS/yoki bortning ishonchli vaqt manbasi; barcha vaqtlar timezone ko‘rsatilgan ISO-8601 formatida.
3. O‘lchov birligi qat’iy: SpO₂ `%`, puls `bpm`, atmosfera parsial bosimi `kPa`, radiatsiya `µSv/h`. Kelajakda konvertatsiya modulini mustaqil tekshirish kerak.
4. Har bir o‘lchov uchun `quality`: `good`, `invalid`, `missing`, `stale`, `uncalibrated`. Kechikkan yoki avvalgi namunani yangi deb ko‘rsatmaslik.
5. Ekipaj ID va modul ID aniq va avtorizatsiyalangan bo‘lsin; sensor boshqa odamga noto‘g‘ri birikmasin.
6. Aloqa uzilsa, haqiqiy yo‘qolgan qiymat haqida xabar berilsin; diagnostika qoidalari bunday signalni `unknown` sifatida ko‘radi.
7. Qurilma ikki marta namuna yuborsa `sequence_number`, kanal va vaqt bilan idempotentlik nazorati (kelajakdagi vazifa).
8. Xavfsizlik uchun har bir muhim sensor, kalibrlash, ishlamay qolish va sinxronlash mustaqil sinovdan o‘tsin.

**Hozirgi dastur 1–6 ni faqat sinov darajasida modellashtiradi.** API sertifikatlangan tibbiy ma’lumot qabul qilishga ochilmagan. Xom EKG, boshqa laborator analizlar va yuqori chastotali oqim uchun yangi uzatish/mavzu kontrakti talab qilinadi.

"""Educational placeholders. These are NOT approved spaceflight medical procedures."""
NOTICE = (
    "FAQAT O‘QUV/PROTOTIP UCHUN. Bu yo‘riqnomalar NASA tomonidan tasdiqlanmagan "
    "va haqiqiy tibbiy vaziyatda professional ekipaj protokolini almashtirmaydi."
)

PLAYBOOKS = {
    "sensor-check": {
        "title": "Sensor o‘lchovini tekshirish",
        "steps": [
            "Ko‘rsatkich yo‘q yoki signal sifati pastligini ekranda tasdiqlang.",
            "Agar mavjud bo‘lsa, zaxira sensor yoki boshqa mustaqil o‘lchov bilan solishtiring.",
            "Haqiqiy holat noma'lum deb belgilang; normal deb taxmin qilmang.",
            "Nosozlik haqidagi qaydni saqlang va aloqaga chiqqanda ekipaj/shifokorga yetkazing.",
        ],
    },
    "vitals-check": {
        "title": "Tibbiy ko‘rsatkich o‘zgarishini tekshirish",
        "steps": [
            "O‘lchov sifatini tekshiring; bitta o‘lchov bilan tashxis qo‘ymang.",
            "Kosmonavtdan alomatlar va o‘zini qanday his qilayotganini aniqlang.",
            "Boshqa tegishli ko‘rsatkichlarni ko‘rib chiqing va trendni qayd eting.",
            "Belgilangan xavf tasdiqlansa, tasdiqlangan bort tibbiy protokoli va ekipajga murojaat qiling.",
        ],
    },
    "breathing": {
        "title": "Nafas/SpO₂ bo‘yicha signal",
        "steps": [
            "Sensorni va o‘lchash sifatini tekshiring; ekran qiymatini real holat bilan solishtiring.",
            "Kabina O₂, CO₂, bosim, havo aylanishi signallarini ham tekshiring.",
            "Nafas qiyinlashsa yoki ahvol og‘irlashsa, ekipajni shoshilinch ogohlantiring.",
            "Bortda tasdiqlangan nafas/atmosfera favqulodda yo‘riqnomasini oching.",
        ],
    },
    "cabin-atmosphere": {
        "title": "Kabina atmosferasi bo‘yicha signal",
        "steps": [
            "Atmosfera sensori sifati va bir nechta mustaqil manba mavjudligini tekshiring.",
            "Boshqa ekipaj a’zolarini darhol ogohlantiring.",
            "Atmosfera, ventilyatsiya, bosim va avariya panellaridagi boshqa ogohlantirishlarni tekshiring.",
            "Tasdiqlangan kema atmosferasi protokolini qo‘llang; avtomatik tuzatish berilmaydi.",
        ],
    },
    "trauma": {
        "title": "Jiddiy jarohat haqida xabar",
        "steps": [
            "Favqulodda yordam kerakligini ekipajga xabar qiling va vaziyat xavfsizligini tekshiring.",
            "Jabrlanuvchining hushyorligi, nafas olishi va ko‘rinadigan jarohatini baholang.",
            "Mavjud tibbiy to‘plam va ekipaj o‘rgangan tasdiqlangan travma protokolini oching.",
            "Qilingan harakatlar va kuzatuvlarni yozib boring; aloqa tiklanganda yuborish uchun saqlang.",
        ],
    },
    "urgent-medical": {
        "title": "Shoshilinch tibbiy holat haqida xabar",
        "steps": [
            "Ekipajni zudlik bilan ogohlantiring; yakka o‘zingiz qaror qabul qilishdan saqlaning.",
            "Hush, normal nafas olish va boshqa xavf belgilarini baholang.",
            "Bortning shoshilinch tibbiy yordam protokoliga va o‘rgatilgan ekipajga murojaat qiling.",
            "Vaqtni, o‘lchovlarni va ko‘rilgan choralarni qayd eting; aloqa tiklanganda uzating.",
        ],
    },
}


def get_playbook(protocol_id: str) -> dict | None:
    obj = PLAYBOOKS.get(protocol_id)
    return ({"id": protocol_id, **obj, "approval": "DEMO_ONLY", "notice": NOTICE}
            if obj else None)

# Stage 2: investigation CHECKLISTS ONLY, no independent medical orders.
PLAYBOOKS.update({
    "crew-investigation": {
        "title": "Bir nechta ekipajda o‘zgarish: umumiy sababni tekshirish",
        "steps": [
            "O‘zgarishlar qaysi ekipaj a’zolari, modullar va vaqt oralig‘iga tegishli ekanini solishtiring.",
            "Har bir odamda sensor ishlashi, kalibrlanishi va o‘lchov vaqti to‘g‘riligini tekshiring.",
            "Barcha tegishli modullardagi O₂, CO₂, bosim, havo aylanishi, harorat va radiatsiyani solishtiring.",
            "Bir xil faoliyat, jihoz, ovqat, ekspozitsiya yoki boshqa omillar mavjudligini qayd eting; sababni taxmin bilan tasdiqlamang.",
            "Jiddiy alomat bo‘lsa tegishli shifokor tasdiqlagan favqulodda protokol ochilishi va ekipaj ogohlantirilishi kerak.",
        ],
    },
    "engineering-check": {
        "title": "Hayot ta’minoti uskunasi: muhandislik signali",
        "steps": [
            "Qaysi uskuna va modul signal berganini aniqlang.",
            "Signal sifatini mustaqil sensor bilan solishtiring; haqiqiy nosozlik ekanini tasdiqlamaguncha ehtiyot bo‘ling.",
            "Tasdiqlangan bort muhandislik va hayot ta’minoti xavfsizlik ro‘yxatini oching.",
            "Uskunani avtomatik qayta sozlash yoki o‘chirib qo‘yish ushbu demoda amalga oshirilmaydi.",
        ],
    },
    "space-environment": {
        "title": "Radiatsiya yoki kosmik muhit signali",
        "steps": [
            "Radiatsiya sensorlari va dozimetrlarning sifati/vaqtini tekshiring.",
            "Modullar bo‘yicha o‘lchovlarni va vaqt trendini solishtiring.",
            "Tasdiqlangan kosmik radiatsiya xavfsizligi protokolini oching va ekipajni xabardor qiling.",
            "Radiatsiya dozasiga oid hukm uchun kalibrlangan o‘lchov va mutaxassis bahosi kerak.",
        ],
    },
})

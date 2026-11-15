# v0.3.2 — Navigation & performance

- **5 ta asosiy menyu**, ichki tablar bilan jami 8 ta alohida ishchi ekran; boshqa oynalar yashirin.
- Faqat faol ekran DOM’i yangilanadi. Individual grafiklar faqat "Tibbiy ko‘rsatkichlar" ekranida; `/api/events` faqat "Hodisalar tarixi"da.
- `GET /api/protocols`, `/api/resources` va `/api/incidents` birinchi marta "Favqulodda yordam" ekranida ochilganda so‘raladi (lazy load).
- Ochiq brauzerda dashboard so‘rovi 4 sekundda bir; tab fon rejimiga o‘tganda 20 sekundda bir. **Backend mustaqil 2 sekundda bir sensor simulyatsiyasini yuritadi.**
- Kritik missiya holati va faol ogohlantirishlar soni barcha ekranlarda ko‘rinadi; aktiv navigatsiya, klaviatura fokuslari, mobil menyu, deep-linklar.
- Windows/Linux ishga tushirish va SQLite bazasi avvalgidek.
- AI hali mavjud emas, protokollar faqat tasdiqlanmagan DEMO.
# v0.3.0 release notes

- Avvalgi v0.2.1 ustiga qurilgan; eski API va ekipaj monitoringi saqlangan.
- 9 ta demo protokol + 6 demo resurs.
- SQLite hodisalar, qadamlar, audit; foydalanuvchi nomlari snapshot; tanlangan signal konteksti.
- Affected crew va xabar navbati; faqat demo link.
- Responsive emergency interface: desktop/tablet/mobile layouts, collapsible mobile navigation.
- Klinik validatsiya, AI, haqiqiy sensor/aloqa mavjud emas.
- Testlar: 36/36 muvaffaqiyatli.

## v0.3.1 — Windows + Linux launcher

- `start.py` umumiy ishga tushirish mexanizmi: OSga mos alohida virtual muhit (`.venv-windows`, `.venv-linux`), offline qayta ishga tushirish, test va parametrlar.
- `run_windows.bat` endi tizim Python kutubxonalarini global o'rnatmaydi, muhitni alohida boshqaradi.
- `run_linux.sh` Linux uchun; `run_linux_mac.sh` eski foydalanuvchilar uchun alias.
- `docs/WINDOWS_LINUX.md` operatsion tizimlararo o'rnatish va nosozlikni aniqlash yo'riqnomasi.
- Lokal server faqat 127.0.0.1 interfeysiga ulanadi; AI va tibbiy protokollar o'zgarmagan.

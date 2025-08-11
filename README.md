# ​ Edora

**Edora** — bu o‘zbek tilida yaratilgan interaktiv o‘rganish platformasi bo‘lib, foydalanuvchiga o‘rgangan darslarini mustahkamlash, tizimlashtirish va boshqalar bilan bo‘lishish imkonini beradi.

---

##  Maqsad

- O‘zingiz o‘rganayotgan mavzularni tartibli ravishda saqlash.
- Soha doimiy ravishda kengayib boradi — matematikadan tortib algoritm va fizika gacha.
- Foydalanuvchilar uchun qulay, o‘zbek tilida to‘liq tushunarli interfeys.
- Keyinchalik bepul yoki premium ko‘rinishda kengaytirilishi mumkin bo‘lgan platforma.

---

##  Texnologiyalar

| Qism       | Texnologiya                      |
|------------|----------------------------------|
| Backend    | Python, FastAPI, SQLite          |
| Frontend   | React.js, Tailwind CSS           |
| Autentifikatsiya | JWT (python-jose), passlib  |
| Sinovlar   | pytest (kelajakda)               |

---

##  API Endpoint'lari — Boshlang‘ich Focus

- `GET /` — Server faoliyat holatini tekshiradi (DB versiyasi).
- `POST /login` — Admin loyihaga kirishi uchun JWT token yaratadi.
- `GET /subjects` — Barcha subject (mavzular) ro‘yxatini ko‘rsatadi.
- `POST /subject` — Yangi subject qo‘shadi.
- `PUT /subject/{id}` — Subject ni yangilaydi.
- `DELETE /subject/{id}` — Subject ni o‘chiradi.
- `GET /themes` — Barcha theme (kontent bo‘limlari) ro‘yxatini ko‘rsatadi.
- `POST /theme` — Yangi theme qo‘shadi.
- `PUT /theme/{id}` — Theme nomini va mazmunini yangilaydi.
- `DELETE /theme/{id}` — Theme ni o‘chiradi.

> **Eslatma:** Foydalanuvchi autentifikatsiyasi `middleware` orqali JWT token asosida amalga oshiriladi — faqat `/` va `/login` endpointlariga token talab qilinmaydi.

---

##  Loyihani ishga tushirish

1. Repo’ni klon qilish:
   ```bash
   git clone https://github.com/username/edora.git
   cd edora

# 🎮 Free Fire Nik Bot — Professional qayta yozilgan versiya

Aiogram 3.x asosida qurilgan, xavfsiz, tez va state-buglardan holi
Telegram bot.

## ⚠️ MUHIM — DARHOL QILING

Eski `config.py` faylida bot tokeni ochiq matnda yozilgan edi va bu
loyiha (zip) orqali tashqariga chiqqan edi. **Bu token endi maxfiy
emas deb hisoblang.**

1. Telegram'da **@BotFather** ga o'ting
2. `/mybots` → botingizni tanlang → **API Token** → **Revoke current
   token** — eski tokenni bekor qiling
3. Yangi tokenni `.env` fayliga (yoki Railway Variables'ga) yozing

## 🐞 Asosiy bug qanday tuzatildi

**Muammo:** Admin "Nik o'chirish" kabi biror amalni kutayotgan holatda
(FSM state) turganda, foydalanuvchi boshqa istalgan tugmani (Random
Nik, Tayyor Niklar va h.k.) bossa ham, xabar o'sha eski state handleriga
tushib qolar edi.

**Sabab:** Eski kodda FSM "kutish" handlerlari (masalan
`@router.message(AdminState.delnick)`) hech qanday matn bo'yicha
cheklovga ega emas edi. Aiogram xabarlarni handlerlar ro'yxatdan
o'tkazilgan tartibda tekshiradi va birinchi mos kelganida to'xtaydi —
bu "kutish" handleri fayl ichida boshqa tugma handlerlaridan oldin
turgani sababli, ular umuman tekshirilmay qolardi.

**Yechim (ikki qavatli himoya):**

1. `handlers/common.py` — `/start`, `/cancel`, "⬅️ Orqaga" kabi
   navigatsion handlerlar **eng birinchi** router sifatida ulanadi va
   har doim `state.clear()` chaqiradi.
2. Har bir FSM "kutish" handleri (`handlers/admin.py` va
   `handlers/user.py` da) `keyboards.ALL_MENU_TEXTS` ro'yxatidagi
   matnlarni **aniq chetlab o'tadi**. Ya'ni: agar kutilayotgan paytda
   foydalanuvchi biror menyu tugmasini bossa, "kutish" handleri
   ishlamaydi va navbat to'g'ridan-to'g'ri o'sha tugmaning haqiqiy
   handleriga o'tadi — u esa ishga tushgan zahoti `state.clear()`
   chaqirib, eski holatni butunlay tozalaydi.

Natijada foydalanuvchi (yoki admin) qaysi state'da bo'lishidan qat'i
nazar, menyu tugmalari har doim to'g'ri ishlaydi.

## 📁 Loyiha tuzilishi

```
ff_nick_bot/
├── main.py              # Kirish nuqtasi: bot/dispatcher sozlash, polling
├── config.py            # .env dan sozlamalarni o'qish (Settings)
├── database.py          # Yagona aiosqlite ulanish, WAL mode, barcha SQL
├── states.py             # Barcha FSM State guruhlari (bitta joyda)
├── keyboards.py          # Reply/Inline klaviaturalar + tugma matnlari
├── errors.py              # Global exception handler
├── handlers/
│   ├── __init__.py       # Routerlarni TO'G'RI tartibda ulaydi
│   ├── common.py          # /start /cancel /help /admin, "Orqaga"
│   ├── admin.py            # Admin panel (statistika, broadcast, CRUD, backup)
│   └── user.py             # Foydalanuvchi funksiyalari
├── requirements.txt
├── .env.example
├── .gitignore
└── Procfile               # Railway uchun
```

## ✨ Yangi imkoniyatlar (eski koddan farqi)

| # | O'zgarish | Sabab |
|---|---|---|
| 1 | FSM state buzilishi butunlay tuzatildi | Yuqorida tushuntirilgan |
| 2 | `/cancel` komandasi | Istalgan state'dan chiqish |
| 3 | `BOT_TOKEN` va `ADMIN_IDS` `.env` orqali | Xavfsizlik |
| 4 | Bitta doimiy DB ulanish + WAL mode | Tezlik, bir vaqtda ko'p so'rov |
| 5 | `nicks.nick` UNIQUE indeks | Takroriy nik qo'shilmaydi, qidiruv tez |
| 6 | 🔍 Nik qidirish | Indekslangan `LIKE ... COLLATE NOCASE` |
| 7 | ❤️ Sevimli Niklar | Har bir foydalanuvchi o'ziga saqlaydi |
| 8 | 🏆 Top Niklar | `picks` hisoblagichi bo'yicha reyting |
| 9 | 📋 Tayyor Niklar — sahifalash (pagination) | Katta bazada qulay ko'rish |
| 10 | 👥 Foydalanuvchilar soni, 💾 Backup | Admin uchun qo'shimcha imkoniyat |
| 11 | Global error handler (`errors.py`) | Bitta xatolik bot ishini to'xtatmaydi |
| 12 | Broadcast'da `TelegramForbiddenError` / `TelegramRetryAfter` ushlanadi | Bloklagan foydalanuvchi butun jarayonni to'xtatmaydi |
| 13 | "🎮 Nik yaratish" endi aniq FSM orqali ishlaydi | Eski versiyada har qanday erkin matn "ism" deb qabul qilinardi — bu chalkash edi |

## 🚀 O'rnatish (lokal)

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# .env faylini ochib, BOT_TOKEN va ADMIN_IDS ni kiriting

python main.py
```

## ☁️ Railway'ga deploy qilish

1. Loyihani GitHub repo'siga yuklang (`.env` fayli **yuklanmasligi**
   kerak — `.gitignore` buni avtomatik ta'minlaydi)
2. Railway → **New Project** → **Deploy from GitHub repo**
3. **Variables** bo'limiga qo'shing:
   - `BOT_TOKEN` = yangi tokeningiz
   - `ADMIN_IDS` = telegram ID(lar)ingiz (vergul bilan)
4. Railway `Procfile`ni o'qib, `python main.py` buyrug'ini avtomatik
   ishga tushiradi

> **Eslatma:** Railway'da fayl tizimi har deploy'da tiklanishi mumkin
> (ephemeral). `database.db` doimiy saqlanishi uchun Railway'da
> **Volume** ulash tavsiya etiladi, aks holda har deploy'da baza
> bo'shab qoladi.

## 🧪 Multi-instance haqida eslatma

Hozirgi holatda FSM holatlari `MemoryStorage` (jarayon xotirasi)da
saqlanadi — bu bitta bot nusxasi uchun eng tez va oddiy yechim. Agar
kelajakda botni bir nechta server/worker'da parallel ishga tushirish
kerak bo'lsa, `aiogram.fsm.storage.redis.RedisStorage`ga o'tish kerak
bo'ladi.

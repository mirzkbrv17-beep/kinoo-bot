# 🎬 Kino Bot (Aiogram 3 + SQLAlchemy + Mini App)

Telegram kino bot: kod orqali kino topish, VIP, seriallar, majburiy obuna, referal, promo-kod,
admin paneli (FSM), reklama, zaxira nusxa va Netflix uslubidagi Mini App.

> ⚖️ Faqat **o‘zingizga tegishli yoki tarqatishga ruxsat berilgan** kontentni yuklang.

## Tez ishga tushirish (lokal)

```bash
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # BOT_TOKEN va ADMIN_ID ni to'ldiring
python main.py
```

Birinchi ishga tushishda jadvallar, standart sozlamalar, janrlar va emoji yozuvlari avtomatik yaratiladi.
Botga `/admin` yuboring (faqat `ADMIN_ID` dagilar uchun).

## Birinchi kino qo‘shish
`/admin` → **Kino qo‘shish** → nom → video (yoki https havola) → qolgan maydonlar ixtiyoriy (⏭ tugmasi bilan o‘tkazib yuboring).
Kod bo‘sh qolsa avtomatik beriladi (101, 102, …). Foydalanuvchi botga shu kodni oddiy xabar qilib yuborsa, kino keladi.

## Majburiy obuna
1. Botni kanalga **administrator** qiling (taklif havolasi yaratish huquqi bilan).
2. `/admin` → **Majburiy obuna** → **Kanal qo‘shish** (@username, -100… ID yoki forward).
3. Obuna tekshiruvi `/start` bilan cheklanmaydi: har xabar va tugmada ishlaydi (adminlar o‘tkaziladi).
   Bot kanalni tekshira olmasa (admin emas), foydalanuvchi bloklanmaydi — log’da ogohlantirish chiqadi.

## 😀 Animatsiyali Premium emoji (muhim cheklovlar)
- Bot API 9.4 dan `KeyboardButton.icon_custom_emoji_id` mavjud. Telegram hujjatiga ko‘ra, bu ikonka
  **bot egasida Telegram Premium bo‘lsa** (yoki bot Fragment’da qo‘shimcha username sotib olgan bo‘lsa) ishlaydi.
- Tugma matnidagi emoji o‘zi animatsiyali bo‘lmaydi — ikonka alohida maydon orqali beriladi.
- ID olish: `/admin` → **Premium emoji** → tugmani tanlang → shu tugma uchun **premium emoji yuboring**
  (bot ID ni xabar entity’sidan o‘zi oladi). ID ni `.env`/qo‘lda yozish shart emas, hammasi bazada saqlanadi.
- ID yo‘q yoki Telegram rad etsa → oddiy emoji fallback avtomatik ishlaydi (bot Premium’ga bog‘liq emas).
  Rad etilganda ikonkalar o‘chiriladi; **Premium emoji** bo‘limida «Ikonkalarni yoqish» bilan qayta yoqasiz.
- Animatsiya faqat mijoz qo‘llab-quvvatlasa ko‘rinadi — **o‘z telefoningizda** «🧪 Menyuni sinash» bilan tekshiring.

## VIP va Telegram Stars
- VIP: admin beradi, promo-kod yoki referal mukofoti orqali, yoki Stars (XTR) to‘lovi orqali.
- Tariflar: `/admin` → **Bot sozlamalari** → *VIP tariflar* (`kun:Stars,...`, masalan `30:100,90:250`).
- To‘lov faqat Telegram rasmiy mexanizmi (Stars invoice) orqali. Muddati tugagan VIP har soatda avtomatik oddiy holatga qaytadi.

## Mini App
- `WEBAPP_URL` (HTTPS) berilsa — bot menyu tugmasi va Sozlamalarda Mini App chiqadi (Render’da avtomatik).
- Bot bilan bir DB; `initData` serverda HMAC bilan tekshiriladi, ban va majburiy obuna API’da ham qo‘llanadi.
- Postlar Telegram serveridan bot orqali olinib keshlanadi (imzolangan havola).
- «Botda ko‘rish» tugmasi botga `?start=m_<kod>` deep-link bilan o‘tkazadi.

## Render’ga deploy
1. Loyihani GitHub’ga yuboring (`.env` `.gitignore` da — tokenni yubormang).
2. Render → **New → Blueprint** → repo. `render.yaml` Web Service + PostgreSQL yaratadi.
3. Dashboard’da `BOT_TOKEN` va `ADMIN_ID` ni kiriting.
4. Deploy tugagach `https://<nom>.onrender.com/health` → `ok`.

Nega Web Service: bitta jarayonda polling + Mini App serveri (PORT) ishlaydi.
Bepul tarif 15 daqiqa trafiksiz uxlaydi → bot to‘xtaydi; doimiy ishlash uchun pullik tarif kerak.
SQLite ishlatsangiz — Persistent Disk shart (`render.yaml` oxiridagi izohga qarang), aks holda restartda ma’lumot yo‘qoladi.

## Arxitektura
```
bot.py            kirish: polling + aiohttp (Mini App) + vip_watcher + avtomatik backup
config.py         .env sozlamalari
database/         models (18 jadval), db (engine/seed), queries
handlers/         foydalanuvchi va admin handlerlari (har bo'lim alohida fayl)
middlewares/      user (DB sessiya, ban, referal), subscription, admin (rollar)
services/         movie, statistics, emoji, notification (reklama), backup, menu, subscription
keyboards/ states/ utils/   klaviaturalar, FSM holatlari, matnlar (uz/ru), validatorlar
webapp/           index.html, style.css, app.js, api.py
```
Router tartibi (`bot.py`): start → menyular → admin → **eng oxirida** kod/nom fallback.

## Rollar
- `ADMIN_ID` (vergul bilan bir nechta) = owner: hamma narsa.
- `admin`: hamma narsa, lekin admin qo‘sha olmaydi.
- `moderator`: kino/serial qo‘shish-tahrirlash, so‘rov va xabarlarga javob, statistika.

## Bilishingiz kerak
- FSM holatlari xotirada (`MemoryStorage`): bot restart bo‘lsa, jarayondagi admin formalari bekor bo‘ladi (ma’lumotlar saqlanadi).
- Admin paneli o‘zbek tilida; foydalanuvchi menyu va xabarlari uz/ru.
- Migratsiya: `create_all` ishlatiladi. Sxema o‘zgarsa Alembic qo‘shing (SQLAlchemy 2.0 modellari tayyor).
- Zaxira: JSON dump (istalgan DB) + SQLite bo‘lsa `.db` nusxa; owner’larga har `BACKUP_EVERY_HOURS` soatda va `/admin → Zaxira nusxa`.
- Reklama ~20 xabar/s tezlikda, `RetryAfter` hurmat qilinadi, botni bloklaganlar `is_active=false` bo‘ladi.

# EnglishRoadmap — IELTS 7 kundaligi

8 oylik o'qish rejasi (238 kun, A2 → Intermediate B1+): kalendar, batafsil kun sahifalari, notes,
lug'at (interval takrorlash), xatolar daftari, writing maydoni, taymer va progress.

Loyiha ikki xil ishlaydi:

| Rejim | Qayerda | Baza | Ishga tushirish |
|---|---|---|---|
| **Vercel** (asosiy) | internetda, telefon va kompyuterda | Turso (bulutdagi SQLite) | GitHub'ga push → Vercel o'zi deploy qiladi |
| **Lokal** | faqat shu kompyuterda | `data/english.db` (SQLite) | `start.bat` |

## Tuzilma
```
api/index.js        # Vercel funksiyasi: barcha /api/* so'rovlari
lib/app.js          # API mantiqi, sxema, parol tekshiruvi
lib/db.js           # Turso HTTP adapteri (lokalda node:sqlite)
lib/seed.js         # boshlang'ich notes, so'zlar, xatolar, testlar
public/index.html   # sayt (Vercel)
public/plan.json    # 238 kunlik reja (ikkala rejim ham shuni o'qiydi)
vercel.json         # /api/* -> api/index.js
.vercelignore       # lokal fayllar deployga kirmaydi

app.py, start.bat   # lokal server (Python, kutubxonasiz)
static/index.html   # lokal versiya sahifasi
data/seed.json      # lokal boshlang'ich ma'lumotlar
scripts/            # dev.js (lokal Node server), smoke.js (API testi)
```

## Vercel + Turso
1. **Turso** (app.turso.tech): baza yarating, uning `libsql://...` manzilini va tokenini oling.
2. **Vercel** → Project → Settings → Environment Variables:

| Key | Qiymat |
|---|---|
| `TURSO_DATABASE_URL` | `libsql://<baza>-<org>.turso.io` |
| `TURSO_AUTH_TOKEN` | bazaning tokeni (read-only emas) |
| `APP_PASSWORD` | saytga kirish paroli |

3. Framework Preset: **Other**, Root Directory: `./`. O'zgaruvchilarni qo'shgandan keyin **Redeploy**.

Jadvallar va boshlang'ich ma'lumotlar birinchi so'rovda avtomatik yaratiladi.

## Lokal
```bash
start.bat                      # Python 3.8+, http://127.0.0.1:8765
node scripts/dev.js            # Vercel versiyasini lokal sinash (Node 22), parol: dev
node scripts/smoke.js          # API testi
```

## API (Vercel)
| Metod | Yo'l | Tavsif |
|---|---|---|
| POST | /api/login `{password}` | token qaytaradi |
| GET | /api/state | bajarilgan vazifalar, kun izohlari, tugatilgan sanalar |
| POST | /api/done `{id, done}` | vazifa belgisi |
| POST | /api/daynote `{date, body}` | kun izohi |
| POST | /api/daydate `{key, on}` | kun tugatilgan sana (bo'sh = olib tashlash) |
| GET/POST | /api/notes · words · mistakes · tests · writings | ro'yxat / qo'shish yoki yangilash |
| DELETE | /api/<nom>/<id> | o'chirish |
| GET | /api/export | hamma ma'lumot JSON (zaxira) |

Login'dan boshqa barcha so'rovlar `Authorization: Bearer <token>` talab qiladi.

## Xavfsizlik
- Sayt parol bilan himoyalangan; token paroldan HMAC orqali olinadi. Parolni almashtirsangiz, eski tokenlar ishlamay qoladi.
- `.env` va `data/english.db` GitHub'ga yuklanmaydi (`.gitignore`).

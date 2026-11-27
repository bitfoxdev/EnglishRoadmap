# English 3 oylik reja (lokal, SQLite)

30-noyabr 2026 – 28-fevral 2027: kalendar, har kun uchun batafsil sahifa (maqsadlar, vaqt jadvali, qadamma-qadam yo'riqnoma, bo'limlar, sahifalar, fayllar), notes, lug'at, xatolar daftari va progress.

«Ochish» tugmasi kitob PDF'ini kompyuteringizdagi dastur bilan ochadi (faqat `D:\English language` ichidagi fayllar).
Hammasi kompyuteringizda, `data/english.db` (SQLite) faylida saqlanadi. Internet kerak emas (faqat shriftlar uchun).

## Ishga tushirish
1. Python 3.8+ o'rnatilgan bo'lsin (qo'shimcha kutubxona kerak emas).
2. `start.bat` ni ikki marta bosing (yoki terminalda `python app.py`).
3. Brauzer o'zi ochiladi: http://127.0.0.1:8765
4. To'xtatish: terminal oynasida `Ctrl+C`.

Boshqa port: `set PORT=9000 && python app.py`

## Tuzilma
```
english-roadmap/
├─ app.py            # server + REST API (http.server + sqlite3)
├─ start.bat         # Windows uchun ishga tushirish
├─ static/index.html # interfeys
└─ data/
   ├─ plan.json      # 91 kunlik reja (birinchi ishga tushishda bazaga yuklanadi)
   ├─ seed.json      # boshlang'ich notes, so'zlar, xatolar, testlar
   └─ english.db     # SQLite baza (avtomatik yaratiladi)
```

## Jadvallar
| Jadval | Nima saqlanadi |
|---|---|
| `weeks`, `days`, `tasks` | reja; `tasks.done`, `tasks.done_at` — bajarilganlar |
| `day_notes` | har kungi izoh |
| `day_dates` | kun tugatilgan sana (o'zingiz kiritasiz) |
| `notes` | mavzu bo'yicha konspektlar |
| `words` | lug'at (so'z, o'zbekcha ma'no, misol) |
| `mistakes` | xatolar daftari |
| `tests` | test va baholash natijalari |

## API
- `GET /api/plan`, `GET /api/state`
- `POST /api/done` `{id, done}` · `POST /api/daynote` `{date, body}` · `POST /api/daydate` `{key, on}`
- `GET|POST /api/notes|words|mistakes|tests`, `DELETE /api/<nom>/<id>`
- `POST /api/open` `{path}` — kitobni ochish (yo'l `D:\English language` ga nisbatan)
- `GET /api/export` — hamma ma'lumot JSON ko'rinishida (zaxira uchun)

## Zaxira
`data/english.db` faylini nusxalab qo'ying yoki brauzerda `http://127.0.0.1:8765/api/export` ni oching va saqlang.

## Yangilash
`plan.json` o'zgarsa, server qayta ishga tushganda reja yangilanadi; bajarilgan belgilar saqlanib qoladi.
`seed.json`dagi yozuvlar faqat bir marta qo'shiladi: siz o'chirgan yozuv qaytib kelmaydi.

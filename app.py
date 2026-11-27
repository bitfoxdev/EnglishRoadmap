"""English 3 oylik reja — lokal server (Python stdlib + SQLite).

Ishga tushirish:  python app.py
Brauzerda:        http://127.0.0.1:8765
Ma'lumotlar:      data/english.db (SQLite)
"""
import json
import os
import sqlite3
import sys
import threading
import webbrowser
from datetime import datetime
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")
STATIC = os.path.join(BASE, "static")
DB_PATH = os.path.join(DATA, "english.db")
HOST, PORT = "127.0.0.1", int(os.environ.get("PORT", "8765"))
# Kitoblar papkasi (D:\English language) — app papkasining ota papkasi
BOOKS_ROOT = os.path.dirname(BASE)

SCHEMA = """
CREATE TABLE IF NOT EXISTS weeks(
  w INTEGER PRIMARY KEY, m INTEGER, start TEXT, end TEXT,
  nav TEXT, gram TEXT, pron TEXT, vocab TEXT, write TEXT);
CREATE TABLE IF NOT EXISTS days(
  date TEXT PRIMARY KEY, week INTEGER, dn TEXT, label TEXT);
CREATE TABLE IF NOT EXISTS tasks(
  id TEXT PRIMARY KEY, date TEXT, ord INTEGER, cat TEXT, minutes INTEGER,
  book TEXT, title TEXT, detail TEXT, words TEXT,
  done INTEGER NOT NULL DEFAULT 0, done_at TEXT);
CREATE INDEX IF NOT EXISTS tasks_date ON tasks(date);
CREATE TABLE IF NOT EXISTS day_notes(date TEXT PRIMARY KEY, body TEXT, updated TEXT);
CREATE TABLE IF NOT EXISTS day_dates(day TEXT PRIMARY KEY, done_on TEXT NOT NULL, updated TEXT);
CREATE TABLE IF NOT EXISTS notes(
  id TEXT PRIMARY KEY, cat TEXT, title TEXT, body TEXT, ord INTEGER DEFAULT 999, date TEXT);
CREATE TABLE IF NOT EXISTS words(
  id TEXT PRIMARY KEY, w TEXT NOT NULL, uz TEXT NOT NULL, ex TEXT, added TEXT);
CREATE TABLE IF NOT EXISTS mistakes(
  id TEXT PRIMARY KEY, wrong TEXT NOT NULL, "right" TEXT NOT NULL, why TEXT, date TEXT);
CREATE TABLE IF NOT EXISTS writings(
  id TEXT PRIMARY KEY, date TEXT, text TEXT, updated TEXT);
CREATE TABLE IF NOT EXISTS tests(
  id TEXT PRIMARY KEY, date TEXT, name TEXT, result TEXT, detail TEXT);
"""

# collection -> (table, columns)
COLLECTIONS = {
    "notes": ("notes", ["id", "cat", "title", "body", "ord", "date"]),
    "words": ("words", ["id", "w", "uz", "ex", "added", "box", "due", "seen"]),
    "writings": ("writings", ["id", "date", "text", "updated"]),
    "mistakes": ("mistakes", ["id", "wrong", "right", "why", "date"]),
    "tests": ("tests", ["id", "date", "name", "result", "detail"]),
}

_lock = threading.Lock()


def connect():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    return con


def q(col):
    return '"right"' if col == "right" else col


def init_db():
    os.makedirs(DATA, exist_ok=True)
    con = connect()
    con.executescript(SCHEMA)
    # eski bazalar uchun yangi ustunlar
    cols = {r["name"] for r in con.execute("PRAGMA table_info(tasks)")}
    if "extra" not in cols:
        con.execute("ALTER TABLE tasks ADD COLUMN extra TEXT")
    wcols = {r["name"] for r in con.execute("PRAGMA table_info(words)")}
    for c, typ in (("box", "INTEGER DEFAULT 1"), ("due", "TEXT"), ("seen", "TEXT")):
        if c not in wcols:
            con.execute(f"ALTER TABLE words ADD COLUMN {c} {typ}")
    cols = {r["name"] for r in con.execute("PRAGMA table_info(days)")}
    if "goals" not in cols:
        con.execute("ALTER TABLE days ADD COLUMN goals TEXT")
    # Reja: faqat birinchi marta (yoki plan.json yangilanganda) yuklanadi; bajarilganlar saqlanib qoladi
    # Reja bitta joyda: public/plan.json (Vercel versiyasi ham shuni ishlatadi)
    plan_path = os.path.join(BASE, "public", "plan.json")
    if not os.path.exists(plan_path):
        plan_path = os.path.join(DATA, "plan.json")
    plan = json.load(open(plan_path, encoding="utf-8"))
    for w in plan["weeks"]:
        con.execute("INSERT OR REPLACE INTO weeks VALUES(?,?,?,?,?,?,?,?,?)",
                    (w["w"], w["m"], w["start"], w["end"], w["nav"], w["gram"], w["pron"], w["vocab"], w["write"]))
    for d in plan["days"]:
        con.execute("INSERT OR REPLACE INTO days(date,week,dn,label,goals) VALUES(?,?,?,?,?)",
                    (d["date"], d["w"], d["dn"], d["label"], json.dumps(d.get("goals") or [], ensure_ascii=False)))
        for i, t in enumerate(d["tasks"]):
            con.execute(
                """INSERT INTO tasks(id,date,ord,cat,minutes,book,title,detail,words,extra) VALUES(?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(id) DO UPDATE SET ord=excluded.ord,cat=excluded.cat,minutes=excluded.minutes,
                   book=excluded.book,title=excluded.title,detail=excluded.detail,words=excluded.words,extra=excluded.extra""",
                (t["id"], d["date"], i, t["c"], t["m"], t["b"], t["t"], t["d"], json.dumps(t.get("w")) if t.get("w") else None,
                 json.dumps(t.get("x"), ensure_ascii=False) if t.get("x") else None))
    # Boshlang'ich notes/so'zlar/xatolar/testlar: faqat yo'q bo'lsa qo'shiladi (siz o'chirganlar qaytmaydi)
    seed_path = os.path.join(DATA, "seed.json")
    con.execute("CREATE TABLE IF NOT EXISTS meta(k TEXT PRIMARY KEY, v TEXT)")
    done_seed = {r["k"] for r in con.execute("SELECT k FROM meta")}
    if os.path.exists(seed_path):
        seed = json.load(open(seed_path, encoding="utf-8"))
        for name, rows in seed.items():
            if name not in COLLECTIONS:
                continue
            table, cols = COLLECTIONS[name]
            for r in rows:
                key = f"seed:{name}:{r['id']}"
                if key in done_seed:
                    continue
                vals = [r.get(c) for c in cols]
                con.execute(f"INSERT OR IGNORE INTO {table}({','.join(q(c) for c in cols)}) VALUES({','.join('?'*len(cols))})", vals)
                con.execute("INSERT OR IGNORE INTO meta VALUES(?,?)", (key, "1"))
    con.commit()
    con.close()


def now():
    return datetime.now().isoformat(timespec="seconds")


class Handler(BaseHTTPRequestHandler):
    server_version = "EnglishRoadmap/1.0"

    def log_message(self, fmt, *args):
        pass

    # ---------- helpers ----------
    def send_json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def read_json(self):
        n = int(self.headers.get("Content-Length") or 0)
        if n > 2_000_000:
            raise ValueError("too large")
        return json.loads(self.rfile.read(n) or b"{}")

    def send_file(self, path):
        types = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8",
                 ".css": "text/css; charset=utf-8", ".json": "application/json", ".png": "image/png", ".svg": "image/svg+xml"}
        full = os.path.normpath(os.path.join(STATIC, path.lstrip("/")))
        if not full.startswith(STATIC) or not os.path.isfile(full):
            return self.send_json({"error": "not found"}, 404)
        data = open(full, "rb").read()
        self.send_response(200)
        self.send_header("Content-Type", types.get(os.path.splitext(full)[1], "application/octet-stream"))
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    # ---------- routes ----------
    def do_GET(self):
        p = urlparse(self.path).path
        if p == "/" or p == "/index.html":
            return self.send_file("index.html")
        if p == "/api/plan":
            con = connect()
            weeks = [dict(r) for r in con.execute("SELECT * FROM weeks ORDER BY w")]
            days = []
            tasks = {}
            for t in con.execute("SELECT * FROM tasks ORDER BY date, ord"):
                tasks.setdefault(t["date"], []).append({
                    "id": t["id"], "c": t["cat"], "m": t["minutes"], "b": t["book"], "t": t["title"],
                    "d": t["detail"], "w": json.loads(t["words"]) if t["words"] else None,
                    "x": json.loads(t["extra"]) if t["extra"] else None})
            for d in con.execute("SELECT * FROM days ORDER BY date"):
                days.append({"date": d["date"], "w": d["week"], "dn": d["dn"], "label": d["label"],
                             "goals": json.loads(d["goals"]) if d["goals"] else [], "tasks": tasks.get(d["date"], [])})
            con.close()
            return self.send_json({"days": days, "weeks": weeks})
        if p == "/api/version":
            return self.send_json({"version": 4})
        if p == "/api/state":
            con = connect()
            done = {r["id"]: 1 for r in con.execute("SELECT id FROM tasks WHERE done=1")}
            notes = {r["date"]: r["body"] for r in con.execute("SELECT date, body FROM day_notes")}
            dates = {r["day"]: r["done_on"] for r in con.execute("SELECT day, done_on FROM day_dates")}
            con.close()
            return self.send_json({"done": done, "dayNotes": notes, "dates": dates})
        if p.startswith("/api/"):
            name = p[5:]
            if name in COLLECTIONS:
                table, cols = COLLECTIONS[name]
                con = connect()
                rows = [dict(r) for r in con.execute(f"SELECT {','.join(q(c) for c in cols)} FROM {table}")]
                con.close()
                return self.send_json(rows)
        if p == "/api/export":
            con = connect()
            out = {n: [dict(r) for r in con.execute(f"SELECT * FROM {t}")] for n, (t, _) in COLLECTIONS.items()}
            out["done"] = [dict(r) for r in con.execute("SELECT id, done_at FROM tasks WHERE done=1")]
            out["dayNotes"] = [dict(r) for r in con.execute("SELECT * FROM day_notes")]
            out["dayDates"] = [dict(r) for r in con.execute("SELECT * FROM day_dates")]
            con.close()
            return self.send_json(out)
        return self.send_file(p)

    def do_POST(self):
        p = urlparse(self.path).path
        try:
            body = self.read_json()
        except Exception:
            return self.send_json({"error": "bad json"}, 400)
        if p == "/api/open":
            # Kitobni kompyuterdagi dastur bilan ochish (faqat kitoblar papkasi ichida)
            full = os.path.realpath(os.path.join(BOOKS_ROOT, str(body.get("path", "")).replace("\\", os.sep)))
            root = os.path.realpath(BOOKS_ROOT)
            if os.path.commonpath([full, root]) != root or not os.path.exists(full):
                return self.send_json({"error": "not found"}, 404)
            try:
                if hasattr(os, "startfile"):
                    os.startfile(full)
                else:
                    import subprocess
                    subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", full])
            except Exception as e:
                return self.send_json({"error": str(e)}, 500)
            return self.send_json({"ok": True})
        with _lock:
            con = connect()
            try:
                if p == "/api/done":
                    con.execute("UPDATE tasks SET done=?, done_at=? WHERE id=?",
                                (1 if body.get("done") else 0, now() if body.get("done") else None, str(body.get("id"))))
                elif p == "/api/daydate":
                    # Kun tugatilgan sana: foydalanuvchi o'zi kiritadi (bo'sh qiymat = belgini olib tashlash)
                    key, on = str(body.get("key")), str(body.get("on") or "")
                    if on:
                        con.execute("INSERT INTO day_dates VALUES(?,?,?) ON CONFLICT(day) DO UPDATE SET done_on=excluded.done_on, updated=excluded.updated",
                                    (key, on, now()))
                    else:
                        con.execute("DELETE FROM day_dates WHERE day=?", (key,))
                elif p == "/api/daynote":
                    date, text = str(body.get("date")), str(body.get("body") or "")
                    if text.strip():
                        con.execute("INSERT INTO day_notes VALUES(?,?,?) ON CONFLICT(date) DO UPDATE SET body=excluded.body, updated=excluded.updated",
                                    (date, text, now()))
                    else:
                        con.execute("DELETE FROM day_notes WHERE date=?", (date,))
                elif p.startswith("/api/") and p[5:] in COLLECTIONS:
                    table, cols = COLLECTIONS[p[5:]]
                    if not body.get("id"):
                        return self.send_json({"error": "id required"}, 400)
                    vals = [body.get(c) for c in cols]
                    con.execute(f"INSERT OR REPLACE INTO {table}({','.join(q(c) for c in cols)}) VALUES({','.join('?'*len(cols))})", vals)
                else:
                    return self.send_json({"error": "not found"}, 404)
                con.commit()
            finally:
                con.close()
        return self.send_json({"ok": True})

    def do_DELETE(self):
        parts = urlparse(self.path).path.strip("/").split("/")
        if len(parts) == 3 and parts[0] == "api" and parts[1] in COLLECTIONS:
            table, _ = COLLECTIONS[parts[1]]
            with _lock:
                con = connect()
                con.execute(f"DELETE FROM {table} WHERE id=?", (parts[2],))
                con.commit()
                con.close()
            return self.send_json({"ok": True})
        return self.send_json({"error": "not found"}, 404)


class Server(ThreadingHTTPServer):
    # Windows'da SO_REUSEADDR ikki serverga bitta portni egallashga ruxsat beradi:
    # eski oyna ochiq qolsa, so'rovlar eski versiyaga ketadi. Shuning uchun o'chiramiz.
    # Linux/macOS'da TIME_WAIT dan keyin tez qayta ishga tushirish uchun SO_REUSEADDR kerak.
    allow_reuse_address = os.name != "nt"

    def server_bind(self):
        if os.name == "nt":
            import socket
            # Windows: port boshqa jarayonda band bo'lsa, ulashmaslik (xato chiqadi va keyingi port tanlanadi)
            self.socket.setsockopt(socket.SOL_SOCKET, getattr(socket, "SO_EXCLUSIVEADDRUSE", -5), 1)
        super().server_bind()


def main():
    init_db()
    srv = None
    for port in range(PORT, PORT + 10):
        try:
            srv = Server((HOST, port), Handler)
            break
        except OSError:
            print(f"{port}-port band (ehtimol, eski start.bat oynasi ochiq qolgan). Keyingi port sinab ko'rilmoqda...")
    if srv is None:
        print("Bo'sh port topilmadi. Barcha start.bat oynalarini yopib, qayta urinib ko'ring.")
        return
    port = srv.server_address[1]
    url = f"http://{HOST}:{port}"
    print(f"English roadmap ishlayapti: {url}")
    print("To'xtatish uchun: Ctrl+C")
    if "--no-browser" not in sys.argv:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nTo'xtatildi.")


if __name__ == "__main__":
    main()

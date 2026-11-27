// API mantiqi: lokal app.py dagi endpointlar bilan bir xil shakl.
import crypto from 'node:crypto';
import { batch, query } from './db.js';
import SEED from './seed.js';

const SCHEMA = [
  `CREATE TABLE IF NOT EXISTS done(id TEXT PRIMARY KEY, done INTEGER NOT NULL DEFAULT 0, at TEXT)`,
  `CREATE TABLE IF NOT EXISTS day_notes(date TEXT PRIMARY KEY, body TEXT, updated TEXT)`,
  `CREATE TABLE IF NOT EXISTS day_dates(day TEXT PRIMARY KEY, done_on TEXT NOT NULL, updated TEXT)`,
  `CREATE TABLE IF NOT EXISTS notes(id TEXT PRIMARY KEY, cat TEXT, title TEXT, body TEXT, ord INTEGER DEFAULT 999, date TEXT)`,
  `CREATE TABLE IF NOT EXISTS words(id TEXT PRIMARY KEY, w TEXT NOT NULL, uz TEXT NOT NULL, ex TEXT, added TEXT, box INTEGER DEFAULT 1, due TEXT, seen TEXT)`,
  `CREATE TABLE IF NOT EXISTS mistakes(id TEXT PRIMARY KEY, wrong TEXT NOT NULL, "right" TEXT NOT NULL, why TEXT, date TEXT)`,
  `CREATE TABLE IF NOT EXISTS tests(id TEXT PRIMARY KEY, date TEXT, name TEXT, result TEXT, detail TEXT)`,
  `CREATE TABLE IF NOT EXISTS writings(id TEXT PRIMARY KEY, date TEXT, text TEXT, updated TEXT)`,
  `CREATE TABLE IF NOT EXISTS meta(k TEXT PRIMARY KEY, v TEXT)`,
];

export const COLLECTIONS = {
  notes: ['id', 'cat', 'title', 'body', 'ord', 'date'],
  words: ['id', 'w', 'uz', 'ex', 'added', 'box', 'due', 'seen'],
  mistakes: ['id', 'wrong', 'right', 'why', 'date'],
  tests: ['id', 'date', 'name', 'result', 'detail'],
  writings: ['id', 'date', 'text', 'updated'],
};
const q = (c) => (c === 'right' ? '"right"' : c);
const now = () => new Date().toISOString().slice(0, 19);

let ready = null;
export function ensureDb() {
  if (!ready) {
    ready = (async () => {
      await batch(SCHEMA.map((s) => [s]));
      const seeded = await query(`SELECT v FROM meta WHERE k='seeded'`);
      if (!seeded.length) {
        const stmts = [];
        for (const [name, rows] of Object.entries(SEED)) {
          const cols = COLLECTIONS[name];
          if (!cols) continue;
          for (const r of rows) stmts.push([`INSERT OR IGNORE INTO ${name}(${cols.map(q).join(',')}) VALUES(${cols.map(() => '?').join(',')})`, cols.map((c) => r[c] ?? null)]);
        }
        stmts.push([`INSERT OR REPLACE INTO meta VALUES('seeded', ?)`, [now()]]);
        await batch(stmts);
      }
    })().catch((e) => { ready = null; throw e; });
  }
  return ready;
}

// ---------- autentifikatsiya: bitta parol, undan HMAC token ----------
const tokenFor = (pw) => crypto.createHmac('sha256', pw).update('ielts7-kundaligi-v1').digest('hex');
function safeEq(a, b) {
  const x = Buffer.from(String(a)), y = Buffer.from(String(b));
  return x.length === y.length && crypto.timingSafeEqual(x, y);
}

export async function handle({ method, path, body, headers }) {
  const PW = process.env.APP_PASSWORD;
  if (!PW) return [500, { error: "APP_PASSWORD sozlanmagan (Vercel → Settings → Environment Variables)" }];
  const parts = path.replace(/^\/+|\/+$/g, '').split('/');

  if (parts[0] === 'login' && method === 'POST') {
    if (!safeEq(body?.password || '', PW)) return [401, { error: 'wrong password' }];
    return [200, { token: tokenFor(PW) }];
  }
  const auth = (headers.authorization || '').replace(/^Bearer\s+/i, '');
  if (!safeEq(auth, tokenFor(PW))) return [401, { error: 'unauthorized' }];

  await ensureDb();
  const [name, id] = parts;

  if (method === 'GET') {
    if (name === 'state') {
      const [d, n, dd] = await batch([[`SELECT id FROM done WHERE done=1`], [`SELECT date, body FROM day_notes`], [`SELECT day, done_on FROM day_dates`]]);
      return [200, {
        done: Object.fromEntries(d.rows.map((r) => [r.id, 1])),
        dayNotes: Object.fromEntries(n.rows.map((r) => [r.date, r.body])),
        dates: Object.fromEntries(dd.rows.map((r) => [r.day, r.done_on])),
      }];
    }
    if (COLLECTIONS[name]) return [200, await query(`SELECT ${COLLECTIONS[name].map(q).join(',')} FROM ${name}`)];
    if (name === 'export') {
      const names = [...Object.keys(COLLECTIONS), 'done', 'day_notes', 'day_dates'];
      const res = await batch(names.map((n) => [`SELECT * FROM ${n}`]));
      return [200, Object.fromEntries(names.map((n, i) => [n, res[i].rows]))];
    }
    if (name === 'version') return [200, { version: 4, db: 'turso' }];
  }

  if (method === 'POST') {
    if (name === 'done') {
      const on = body?.done ? 1 : 0;
      await query(`INSERT INTO done VALUES(?,?,?) ON CONFLICT(id) DO UPDATE SET done=excluded.done, at=excluded.at`, [String(body?.id), on, on ? now() : null]);
      return [200, { ok: true }];
    }
    if (name === 'daynote') {
      const text = String(body?.body || '');
      if (text.trim()) await query(`INSERT INTO day_notes VALUES(?,?,?) ON CONFLICT(date) DO UPDATE SET body=excluded.body, updated=excluded.updated`, [String(body?.date), text, now()]);
      else await query(`DELETE FROM day_notes WHERE date=?`, [String(body?.date)]);
      return [200, { ok: true }];
    }
    if (name === 'daydate') {
      const on = String(body?.on || '');
      if (on && !/^\d{4}-\d{2}-\d{2}$/.test(on)) return [400, { error: 'bad date' }];
      if (on) await query(`INSERT INTO day_dates VALUES(?,?,?) ON CONFLICT(day) DO UPDATE SET done_on=excluded.done_on, updated=excluded.updated`, [String(body?.key), on, now()]);
      else await query(`DELETE FROM day_dates WHERE day=?`, [String(body?.key)]);
      return [200, { ok: true }];
    }
    if (COLLECTIONS[name]) {
      if (!body?.id) return [400, { error: 'id required' }];
      const cols = COLLECTIONS[name];
      await query(`INSERT OR REPLACE INTO ${name}(${cols.map(q).join(',')}) VALUES(${cols.map(() => '?').join(',')})`, cols.map((c) => body[c] ?? null));
      return [200, { ok: true }];
    }
  }

  if (method === 'DELETE' && COLLECTIONS[name] && id) {
    await query(`DELETE FROM ${name} WHERE id=?`, [decodeURIComponent(id)]);
    return [200, { ok: true }];
  }
  return [404, { error: 'not found' }];
}

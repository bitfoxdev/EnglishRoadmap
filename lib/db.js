// Turso (libSQL) bilan HTTP orqali ishlash. Qo'shimcha kutubxona kerak emas.
// TURSO_DATABASE_URL bo'lmasa (lokal ishlab chiqish), Node'ning o'rnatilgan SQLite'i ishlatiladi.

const URL_ENV = process.env.TURSO_DATABASE_URL || '';
const TOKEN = process.env.TURSO_AUTH_TOKEN || '';

function encodeArg(v) {
  if (v === null || v === undefined) return { type: 'null' };
  if (typeof v === 'number') return Number.isInteger(v) ? { type: 'integer', value: String(v) } : { type: 'float', value: v };
  if (typeof v === 'boolean') return { type: 'integer', value: v ? '1' : '0' };
  return { type: 'text', value: String(v) };
}

function decodeCell(c) {
  if (!c || c.type === 'null') return null;
  if (c.type === 'integer') return Number(c.value);
  return c.value;
}

async function tursoBatch(stmts) {
  const base = URL_ENV.replace(/^libsql:\/\//, 'https://').replace(/^turso:\/\//, 'https://').replace(/\/$/, '');
  const body = {
    requests: [
      ...stmts.map(([sql, args = []]) => ({ type: 'execute', stmt: { sql, args: args.map(encodeArg) } })),
      { type: 'close' },
    ],
  };
  const r = await fetch(base + '/v2/pipeline', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${TOKEN}` },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(`Turso HTTP ${r.status}: ${(await r.text()).slice(0, 200)}`);
  const j = await r.json();
  return j.results.slice(0, stmts.length).map((res, i) => {
    if (res.type !== 'ok') throw new Error(`SQL xato (${stmts[i][0].slice(0, 60)}): ${JSON.stringify(res.error || res)}`);
    const out = res.response.result;
    const cols = out.cols.map((c) => c.name);
    return { rows: out.rows.map((row) => Object.fromEntries(row.map((c, k) => [cols[k], decodeCell(c)]))), changes: out.affected_row_count };
  });
}

let local = null;
async function localBatch(stmts) {
  if (!local) {
    const { DatabaseSync } = await import('node:sqlite');
    const fs = await import('node:fs');
    fs.mkdirSync('.data', { recursive: true });
    local = new DatabaseSync('.data/dev.db');
  }
  return stmts.map(([sql, args = []]) => {
    const st = local.prepare(sql);
    const a = args.map((v) => (typeof v === 'boolean' ? (v ? 1 : 0) : v ?? null));
    if (/^\s*(select|pragma)/i.test(sql)) return { rows: st.all(...a).map((r) => ({ ...r })), changes: 0 };
    const info = st.run(...a);
    return { rows: [], changes: Number(info.changes) };
  });
}

export const usingTurso = Boolean(URL_ENV);
export async function batch(stmts) {
  return usingTurso ? tursoBatch(stmts) : localBatch(stmts);
}
export async function query(sql, args = []) {
  return (await batch([[sql, args]]))[0].rows;
}

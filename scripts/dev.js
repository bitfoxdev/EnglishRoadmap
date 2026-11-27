// Lokal ishlab chiqish serveri: public/ ni beradi, /api/* ni lib/app.js ga yuboradi.
// TURSO_* o'rnatilmagan bo'lsa, .data/dev.db (Node'ning o'rnatilgan SQLite'i) ishlatiladi.
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { handle } from '../lib/app.js';

process.env.APP_PASSWORD ||= 'dev';
const PORT = Number(process.env.PORT || 3000);
const TYPES = { '.html': 'text/html; charset=utf-8', '.json': 'application/json', '.js': 'text/javascript' };

http.createServer(async (req, res) => {
  const url = new URL(req.url, 'http://x');
  if (url.pathname.startsWith('/api/')) {
    let raw = '';
    for await (const c of req) raw += c;
    let body = {};
    try { body = raw ? JSON.parse(raw) : {}; } catch {}
    try {
      const [s, d] = await handle({ method: req.method, path: url.pathname.slice(5), body, headers: req.headers });
      res.writeHead(s, { 'Content-Type': 'application/json' }); res.end(JSON.stringify(d));
    } catch (e) { res.writeHead(500); res.end(JSON.stringify({ error: String(e) })); }
    return;
  }
  const f = path.join('public', url.pathname === '/' ? 'index.html' : path.normalize(url.pathname));
  if (!f.startsWith('public') || !fs.existsSync(f)) { res.writeHead(404); res.end('not found'); return; }
  res.writeHead(200, { 'Content-Type': TYPES[path.extname(f)] || 'application/octet-stream' });
  fs.createReadStream(f).pipe(res);
}).listen(PORT, () => console.log(`http://localhost:${PORT}  (parol: ${process.env.APP_PASSWORD})`));

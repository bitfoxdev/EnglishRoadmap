// Vercel serverless funksiya: barcha /api/* so'rovlari shu yerga keladi (vercel.json → rewrites).
import { handle } from '../lib/app.js';

export default async function handler(req, res) {
  try {
    let path = req.query?.path;
    if (Array.isArray(path)) path = path.join('/');
    if (!path) path = (req.url || '').split('?')[0].replace(/^\/api\/?/, '');
    let body = req.body;
    if (typeof body === 'string') { try { body = JSON.parse(body || '{}'); } catch { body = {}; } }
    const [status, data] = await handle({ method: req.method, path: path || '', body: body || {}, headers: req.headers || {} });
    res.setHeader('Cache-Control', 'no-store');
    res.status(status).json(data);
  } catch (e) {
    console.error(e);
    res.status(500).json({ error: 'server error', detail: String(e.message || e).slice(0, 300) });
  }
}

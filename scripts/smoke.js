// API'ni tez tekshirish: node scripts/smoke.js  (lokal SQLite bilan)
import assert from 'node:assert';
process.env.APP_PASSWORD = 'test-pw';
const { handle } = await import('../lib/app.js');
const call = (method, path, body, token) => handle({ method, path, body, headers: token ? { authorization: 'Bearer ' + token } : {} });

let [s, d] = await call('GET', 'state');                assert.equal(s, 401);
[s, d] = await call('POST', 'login', { password: 'x' }); assert.equal(s, 401);
[s, d] = await call('POST', 'login', { password: 'test-pw' }); assert.equal(s, 200); const T = d.token;
[s, d] = await call('GET', 'notes', {}, T);             assert.equal(s, 200); assert.ok(d.length >= 12, 'seed notes');
[s] = await call('POST', 'done', { id: '2026-11-30-0', done: true }, T); assert.equal(s, 200);
[s] = await call('POST', 'daydate', { key: '2026-11-30', on: '2026-12-01' }, T); assert.equal(s, 200);
[s] = await call('POST', 'daydate', { key: '2026-11-30', on: 'bad' }, T); assert.equal(s, 400);
[s] = await call('POST', 'daynote', { date: '2026-11-30', body: 'Unit 1 — 90%' }, T); assert.equal(s, 200);
[s, d] = await call('GET', 'state', {}, T);
assert.equal(d.done['2026-11-30-0'], 1); assert.equal(d.dates['2026-11-30'], '2026-12-01'); assert.equal(d.dayNotes['2026-11-30'], 'Unit 1 — 90%');
[s] = await call('POST', 'done', { id: '2026-11-30-0', done: false }, T);
[s, d] = await call('GET', 'state', {}, T);             assert.equal(d.done['2026-11-30-0'], undefined);
[s] = await call('POST', 'words', { id: 'wt', w: 'test', uz: 'sinov', box: 2, due: '2026-12-05' }, T); assert.equal(s, 200);
[s, d] = await call('GET', 'words', {}, T);             assert.equal(d.find((x) => x.id === 'wt').box, 2);
[s] = await call('DELETE', 'words/wt', {}, T);           assert.equal(s, 200);
[s] = await call('POST', 'writings', { id: '2026-11-30-3', date: '2026-11-30', text: 'Hi.' }, T); assert.equal(s, 200);
[s, d] = await call('GET', 'export', {}, T);            assert.ok(d.writings.length === 1 && d.day_dates.length === 1);
console.log('smoke ok');

// Control previo a LIVE: falla si alguna página contiene marcadores pendientes,
// valores ficticios de prueba o avisos de prototipo/preview.
// Uso:
//   node qa/prelaunch-check.mjs                       → construye LIVE completo (datos FICTICIOS) en local y lo revisa
//   node qa/prelaunch-check.mjs https://tienda.example [--cookie "k=v"] [--expect-indexable]  → revisa una tienda real (rutas del fixture)
//   --expect-indexable  convierte el noindex en incidencia BLOQUEANTE (prueba obligatoria antes de publicar; revisión V2 P1)
import fs from 'node:fs';
import path from 'node:path';
import http from 'node:http';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const args = process.argv.slice(2);
const cookie = args.includes('--cookie') ? args[args.indexOf('--cookie') + 1] : null;
const expectIndexable = args.includes('--expect-indexable');
let base = args.find((a) => /^https?:\/\//.test(a));
const fixture = JSON.parse(fs.readFileSync(path.join(repo, 'tools/preview/fixture.json'), 'utf8'));
const routes = fixture.pages.map((p) => p.path).filter((p) => p !== '/404' && p !== '/cart');
let srv;
if (!base) {
  const out = path.join(repo, 'preview-out-prelaunch');
  execFileSync('node', [path.join(repo, 'tools/preview/build.mjs'), '--out', out, '--mode', 'live', '--confirm-live', '--complete-globals', '--complete-metafields'], { stdio: 'pipe' });
  srv = http.createServer((req, res) => {
    let f = path.join(out, decodeURIComponent(new URL(req.url, 'http://x').pathname));
    if (fs.existsSync(f) && fs.statSync(f).isDirectory()) f = path.join(f, 'index.html');
    if (!fs.existsSync(f)) { res.writeHead(404); return res.end(); }
    res.writeHead(200, { 'content-type': 'text/html; charset=utf-8' }); fs.createReadStream(f).pipe(res);
  }).listen(4197);
  base = 'http://localhost:4197';
}
const RULES = [
  [/data-ds-placeholder/g, 'marcador ⟦PENDIENTE⟧ / hueco de foto'],
  [/VALOR FICTICIO DE PRUEBA|IMAGEN FICTICIA|test-media\/ficticia/g, 'valor ficticio de prueba'],
  [/ds-proto-banner/g, 'aviso de prototipo / preview / bloqueo'],
  [/translation missing/g, 'traducción ausente'],
  [/\[Descripción comercial|\[Product description/g, 'descripción pendiente'],
];
const report = { base, date: new Date().toISOString(), pages: {}, blocking: 0, warnings: [] };
for (const r of routes) {
  const res = await fetch(base + r, cookie ? { headers: { cookie } } : {});
  const html = await res.text();
  const hits = RULES.map(([re, label]) => [label, (html.match(re) || []).length]).filter(([, n]) => n);
  if (/<meta name="robots" content="noindex/.test(html)) {
    report.warnings.push(`${r}: noindex activo`);
    if (expectIndexable) hits.push(['noindex activo (se esperaba indexable)', 1]);
  }
  report.pages[r] = Object.fromEntries(hits);
  report.blocking += hits.reduce((s, [, n]) => s + n, 0);
}
if (srv) srv.close();
fs.writeFileSync(path.join(repo, 'qa/reports/prelaunch-check.json'), JSON.stringify(report, null, 2));
for (const [r, h] of Object.entries(report.pages)) if (Object.keys(h).length) console.log('BLOQUEA', r, JSON.stringify(h));
console.log(`\n${report.blocking ? 'NO APTO PARA LIVE' : 'Sin marcadores'}: ${report.blocking} incidencias en ${routes.length} páginas · avisos noindex: ${report.warnings.length}`);
process.exitCode = report.blocking ? 1 : 0;

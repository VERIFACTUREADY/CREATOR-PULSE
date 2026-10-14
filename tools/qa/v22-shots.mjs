// V2.2 · Capturas móviles (390×844) de las correcciones de la auditoría V2.1 → qa/screenshots/v2.2/
import { chromium } from 'playwright-core';
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const dir = path.join(repo, 'qa/screenshots/v2.2'); fs.mkdirSync(dir, { recursive: true });
const tmp = path.join(repo, 'preview-out-shots22');
const states = {
  liveFichaSinFDA: ['--mode', 'live', '--confirm-live', '--confirm-brand', '--complete-globals'],
  liveSinMarca: ['--mode', 'live', '--confirm-live', '--complete-globals', '--complete-metafields'],
  marcaSustituida: ['--mode', 'preview_comercial', '--brand', 'OTRA MARCA'], prototipo: ['--mode', 'prototipo'], preview: ['--mode', 'preview_comercial'], liveBloqueado: ['--mode', 'live'], liveCompletoFicticio: ['--mode', 'live', '--confirm-live', '--confirm-brand', '--complete-globals', '--complete-metafields'] };
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
let port = 4400;
async function shots(state, list) {
  const out = path.join(tmp, state);
  execFileSync('node', [path.join(repo, 'tools/preview/build.mjs'), '--out', out, ...states[state]], { stdio: 'pipe' });
  const srv = http.createServer((req, res) => {
    let f = path.join(out, decodeURIComponent(new URL(req.url, 'http://x').pathname));
    if (fs.existsSync(f) && fs.statSync(f).isDirectory()) f = path.join(f, 'index.html');
    if (!fs.existsSync(f)) { res.writeHead(404); return res.end(); }
    const t = { '.css': 'text/css', '.js': 'text/javascript', '.svg': 'image/svg+xml', '.woff2': 'font/woff2' }[path.extname(f)] || 'text/html; charset=utf-8';
    res.writeHead(200, { 'content-type': t }); fs.createReadStream(f).pipe(res);
  });
  const p = port++; await new Promise((r) => srv.listen(p, r));
  for (const [name, route, opts = {}] of list) {
    const ctx = await browser.newContext({ viewport: { width: 390, height: 844 } });
    const pg = await ctx.newPage();
    await pg.goto(`http://localhost:${p}${route}`, { waitUntil: 'networkidle' });
    if (opts.open) await pg.evaluate((sel) => document.querySelectorAll(sel).forEach((d) => (d.open = true)), opts.open);
    if (opts.scrollTo) await pg.evaluate((sel) => document.querySelector(sel)?.scrollIntoView({ block: 'start' }), opts.scrollTo);
    await pg.screenshot({ path: path.join(dir, name), fullPage: !!opts.full });
    console.log(name);
    await ctx.close();
  }
  srv.close();
}
await shots('liveFichaSinFDA', [['P0-1_LIVE-ficha-sin-datos-FDA_bloqueada.png', '/products/adjustable-mouthpiece']]);
await shots('liveCompletoFicticio', [['P0-1_LIVE-ficha-datos-FDA-FICTICIOS_documentos.png', '/products/adjustable-mouthpiece', { open: 'details', scrollTo: '.ds-pdetails' }]]);
await shots('liveSinMarca', [['P1_LIVE-completo-marca-sin-confirmar_bloqueado.png', '/products/adjustable-mouthpiece']]);
await shots('marcaSustituida', [['P1_marca-sustituida_cabecera.png', '/'], ['P1_marca-sustituida_pie.png', '/pages/faq', { scrollTo: '.footer__content-bottom' }]]);
await shots('preview', [
  ['P1_identidad-fiscal-pais-pendiente.png', '/pages/company-information', { scrollTo: '.ds-legal__identity' }],
  ['P1_privacidad-cookies-y-analitica.png', '/pages/privacy', { scrollTo: '.ds-legal__clause:nth-of-type(5)' }],
]);
await browser.close();
fs.rmSync(tmp, { recursive: true, force: true });

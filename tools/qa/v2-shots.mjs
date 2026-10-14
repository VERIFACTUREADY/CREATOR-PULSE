// Capturas móviles (390×844) de cada hallazgo de la auditoría V2 → qa/screenshots/v2.1/
import { chromium } from 'playwright-core';
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const dir = path.join(repo, 'qa/screenshots/v2.1'); fs.mkdirSync(dir, { recursive: true });
const tmp = path.join(repo, 'preview-out-shots');
const states = { prototipo: ['--mode', 'prototipo'], preview: ['--mode', 'preview_comercial'], liveBloqueado: ['--mode', 'live'], liveCompletoFicticio: ['--mode', 'live', '--confirm-live', '--confirm-brand', '--complete-globals', '--complete-metafields'] };
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
let port = 4300;
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
await shots('prototipo', [['C-03_estado-PROTOTIPO_ficha.png', '/products/adjustable-mouthpiece'], ['C-01_antes-portada-informativa-PROTOTIPO.png', '/']]);
await shots('preview', [
  ['C-01_portada-comercial-PREVIEW.png', '/'],
  ['C-02_ficha-comercial-PREVIEW_completa.png', '/products/adjustable-mouthpiece', { full: true }],
  ['C-03_estado-PREVIEW_cta-desactivada.png', '/products/adjustable-mouthpiece', { scrollTo: '.ds-preview-cta' }],
  ['C-05_landing-snoring.png', '/pages/landing-snoring'],
  ['C-05_landing-partners.png', '/pages/landing-partners'],
  ['C-07_faq-con-datos-de-oferta.png', '/pages/faq', { open: '.ds-faq__item', scrollTo: '#orders' }],
  ['C-07_envios-resumen.png', '/pages/shipping', { scrollTo: '.ds-offer-strip' }],
  ['C-10_contacto.png', '/pages/contact', { scrollTo: '.ds-contact__form' }],
]);
await shots('liveBloqueado', [['C-03_estado-LIVE-sin-confirmar_bloqueado.png', '/products/adjustable-mouthpiece']]);
await shots('liveCompletoFicticio', [['C-03_estado-LIVE-completo-DATOS-FICTICIOS_compra.png', '/products/adjustable-mouthpiece', { scrollTo: 'product-form' }]]);
await browser.close();
fs.rmSync(tmp, { recursive: true, force: true });

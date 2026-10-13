// Batería de QA del prototipo (todo gratuito y local).
// Uso: node qa/run-qa.mjs   → escribe qa/reports/qa-results.json y capturas en qa/screenshots
//
// Comprueba en cada ruta y ancho (375/390/768/1440):
//  - desbordamiento horizontal, un único H1, imágenes con alt, enlaces internos rotos
//  - accesibilidad con axe-core (WCAG 2.0/2.1/2.2 A y AA)
//  - errores de consola propios (se ignoran los recursos externos bloqueados en local)
//  - objetivos táctiles < 44 px (criterio de proyecto) en controles no inline
// Y además: compuerta de venta en 3 configuraciones, claims prohibidos, rastreadores,
// navegación por teclado y foco visible.
import { chromium } from 'playwright-core';
import AxeBuilder from '@axe-core/playwright';
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const repo = path.resolve(here, '../..');
const tmp = path.join(repo, 'preview-out-qa');
const shotsDir = path.join(repo, 'qa/screenshots');
const reportsDir = path.join(repo, 'qa/reports');
fs.mkdirSync(shotsDir, { recursive: true });
fs.mkdirSync(reportsDir, { recursive: true });
const CHROME = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome';
const WIDTHS = [375, 390, 768, 1440];

function build(out, flags = []) {
  execFileSync('node', [path.join(repo, 'tools/preview/build.mjs'), '--out', out, ...flags], { stdio: 'pipe' });
  return JSON.parse(fs.readFileSync(path.join(out, 'routes.json'), 'utf8'));
}
function serve(root, port) {
  const types = { '.html': 'text/html; charset=utf-8', '.css': 'text/css', '.js': 'text/javascript', '.svg': 'image/svg+xml', '.woff2': 'font/woff2' };
  const srv = http.createServer((req, res) => {
    let p = decodeURIComponent(new URL(req.url, 'http://x').pathname);
    let f = path.join(root, p);
    if (fs.existsSync(f) && fs.statSync(f).isDirectory()) f = path.join(f, 'index.html');
    if (!fs.existsSync(f)) { res.writeHead(404); return res.end('404'); }
    res.writeHead(200, { 'content-type': types[path.extname(f)] || 'application/octet-stream' });
    fs.createReadStream(f).pipe(res);
  });
  return new Promise((r) => srv.listen(port, () => r(srv)));
}

const results = { date: new Date().toISOString(), routes: {}, gate: {}, claims: {}, tracking: {}, keyboard: {}, summary: {} };

// ---------- 1. Compilar las tres configuraciones ----------
const outDefault = path.join(tmp, 'default');
const outCommerceEmpty = path.join(tmp, 'commerce-empty');
const outCommerceFull = path.join(tmp, 'commerce-full');
const routes = build(outDefault);
build(outCommerceEmpty, ['--commerce']);
build(outCommerceFull, ['--commerce', '--complete-metafields']);

// ---------- 2. Compuerta de venta (análisis estático del HTML) ----------
const PRODUCT = '/products/dispositivo-bucal-en-evaluacion';
function gateFacts(root) {
  const facts = {};
  for (const r of routes) {
    const html = fs.readFileSync(path.join(root, r === '/' ? 'index.html' : r + '/index.html'), 'utf8');
    facts[r] = {
      cartAddForm: /action="\/cart\/add"/.test(html),
      checkoutButton: /id="checkout"/.test(html),
      cartIcon: /id="cart-icon-bubble"/.test(html),
      priceBlock: /class="price[\s"]/.test(html),
      productJsonLd: /"@type":\s*"Product"/.test(html),
      noindex: /<meta name="robots" content="noindex, nofollow">/.test(html),
      prototypeBanner: /class="ds-proto-banner"/.test(html),
    };
  }
  return facts;
}
const any = (facts, k) => Object.values(facts).some((f) => f[k]);
const all = (facts, k) => Object.values(facts).every((f) => f[k]);
const fDefault = gateFacts(outDefault);
const fEmpty = gateFacts(outCommerceEmpty);
const fFull = gateFacts(outCommerceFull);
results.gate = {
  'Prototipo (comercio OFF): ningún formulario /cart/add': !any(fDefault, 'cartAddForm'),
  'Prototipo: ningún botón de checkout': !any(fDefault, 'checkoutButton'),
  'Prototipo: sin icono de carrito': !any(fDefault, 'cartIcon'),
  'Prototipo: sin precios': !any(fDefault, 'priceBlock'),
  'Prototipo: sin JSON-LD Product/Offer': !any(fDefault, 'productJsonLd'),
  'Prototipo: noindex en todas las páginas': all(fDefault, 'noindex'),
  'Prototipo: aviso de prototipo en todas las páginas': all(fDefault, 'prototypeBanner'),
  'Comercio ON + metacampos vacíos: la ficha sigue SIN compra': !fEmpty[PRODUCT].cartAddForm && !fEmpty[PRODUCT].productJsonLd && !fEmpty[PRODUCT].priceBlock,
  'Comercio ON + metacampos completos: la ficha SÍ muestra compra (la compuerta se abre)': fFull[PRODUCT].cartAddForm && fFull[PRODUCT].productJsonLd,
};

// ---------- 3. Claims prohibidos y rastreadores ----------
const FORBIDDEN = [
  [/\bcura(?:r|n)?\b(?!\w)/i, 'cura / curar'], [/apnea curada|trata(?:r)? la apnea|elimina(?:r)? (?:los )?ronquidos/i, 'tratar apnea / eliminar ronquidos'],
  [/coraz[oó]n|infarto/i, 'corazón / infarto'], [/(?:define|marca|mejora)\w* (?:la )?mand[ií]bula/i, 'mandíbula estética'],
  [/sin efectos secundarios|apto para todos|para todo el mundo(?!\.)/i, 'sin efectos / apto para todos'],
  [/\d+\s?%\s*(?:menos|de reducci|eficac|resultado)/i, 'porcentaje de eficacia'], [/cl[ií]nicamente probad|aprobado por|recomendado por m[eé]dicos|dise[ñn]ado por dentistas/i, 'aval falso'],
  [/garantizad[oa]s?\b(?! de)|resultados garantizados|desde la primera noche/i, 'resultado garantizado'],
  [/rinde m[aá]s|rendimiento|mejor humor|mejora el humor|productividad/i, 'rendimiento / humor'],
  [/bruxismo/i, 'bruxismo'], [/[★⭐]|aggregateRating|ratingValue/i, 'estrellas / valoraciones'],
  [/[uú]ltimas unidades|quedan \d|oferta termina|solo hoy|cuenta atr[aá]s/i, 'urgencia falsa'],
  [/fabricado en espa[ñn]a|made in/i, 'origen no verificado'], [/env[ií]o (?:en )?24/i, 'plazo no verificado'],
];
// Contextos permitidos: frases educativas que NIEGAN el claim (p. ej. «no existe una solución que sirva a todo el mundo»).
const ALLOW = [/¿Una férula sirve para todo el mundo\?/i, /no existe una soluci[oó]n que sirva a todo el mundo/i, /no hay una soluci[oó]n que sirva a todo el mundo/i];
function visibleText(html) {
  return html.replace(/<script[\s\S]*?<\/script>/g, ' ').replace(/<style[\s\S]*?<\/style>/g, ' ').replace(/<[^>]+>/g, ' ').replace(/&nbsp;/g, ' ').replace(/\s+/g, ' ');
}
const claimHits = [];
for (const r of routes) {
  let text = visibleText(fs.readFileSync(path.join(outDefault, r === '/' ? 'index.html' : r + '/index.html'), 'utf8'));
  for (const a of ALLOW) text = text.replace(a, '');
  for (const [re, label] of FORBIDDEN) { const m = text.match(re); if (m) claimHits.push({ route: r, label, match: m[0] }); }
}
// También los textos de las plantillas del tema (por si una sección está oculta en la previsualización).
const themeDir = path.join(repo, 'theme');
for (const dir of ['templates', 'sections']) for (const f of fs.readdirSync(path.join(themeDir, dir))) {
  if (!/^(ds-|index|page\.|product|cart|password|header-group|footer-group)/.test(f)) continue;
  let text = fs.readFileSync(path.join(themeDir, dir, f), 'utf8').replace(/<[^>]+>/g, ' ');
  for (const a of ALLOW) text = text.replace(a, '');
  for (const [re, label] of FORBIDDEN) { const m = text.match(re); if (m && !/"(?:id|type|label|info|name)"/.test(text.slice(Math.max(0, m.index - 40), m.index))) claimHits.push({ route: `theme/${dir}/${f}`, label, match: m[0] }); }
}
results.claims = { forbiddenPatterns: FORBIDDEN.length, hits: claimHits };

const TRACKERS = /connect\.facebook\.net|fbq\(|gtag\(|googletagmanager|google-analytics|analytics\.tiktok|ttq\.|hotjar|clarity\.ms|snap\.licdn/i;
const trackerHits = [];
for (const r of routes) {
  const html = fs.readFileSync(path.join(outDefault, r === '/' ? 'index.html' : r + '/index.html'), 'utf8');
  const m = html.match(TRACKERS); if (m) trackerHits.push({ route: r, match: m[0] });
}
results.tracking = { hits: trackerHits };

// ---------- 4. Navegador: responsive, semántica, axe, consola, enlaces ----------
const srv = await serve(outDefault, 4199);
const browser = await chromium.launch({ executablePath: CHROME });
const routeSet = new Set(routes);
for (const r of routes) {
  results.routes[r] = {};
  for (const w of WIDTHS) {
    const context = await browser.newContext({ viewport: { width: w, height: 900 } });
    const page = await context.newPage();
    const consoleErrors = [];
    page.on('console', (m) => { if (m.type() === 'error' && !/ERR_TUNNEL|ERR_NAME|net::|Failed to load resource|createViewEventElement/.test(m.text())) consoleErrors.push(m.text()); });
    // standard-events.js se descarga de cdn.shopify.com: en local está bloqueado (solo previsualización).
    page.on('pageerror', (e) => { if (!/createViewEventElement|StandardEvents/.test(String(e))) consoleErrors.push(String(e)); });
    await page.goto('http://localhost:4199' + r, { waitUntil: 'networkidle' });
    const facts = await page.evaluate(() => {
      const doc = document.documentElement;
      const small = [];
      for (const el of document.querySelectorAll('a, button, summary, input, select, textarea')) {
        const st = getComputedStyle(el);
        if (st.display === 'none' || st.visibility === 'hidden' || el.closest('[hidden]')) continue;
        const rect = el.getBoundingClientRect();
        if (!rect.width || !rect.height) continue;
        // Enlaces dentro de un párrafo/lista de texto están exentos (WCAG 2.5.8 «inline»).
        const inline = el.tagName === 'A' && el.closest('p, li, dd, td, label, .ds-rte, .ds-source, figcaption') && !el.classList.contains('button') && !el.closest('nav, .ds-steps__item, .ds-hero__quick');
        if (inline || el.classList.contains('skip-to-content-link') || el.type === 'hidden') continue;
        if (rect.height < 44 && !(el.type === 'checkbox')) small.push(`${el.tagName.toLowerCase()}.${[...el.classList].slice(0, 2).join('.')} "${(el.innerText || el.getAttribute('aria-label') || '').trim().slice(0, 30)}" ${Math.round(rect.height)}px`);
      }
      return {
        overflowX: doc.scrollWidth > window.innerWidth + 1,
        scrollWidth: doc.scrollWidth,
        h1: document.querySelectorAll('h1').length,
        imgsNoAlt: [...document.querySelectorAll('img')].filter((i) => !i.hasAttribute('alt')).length,
        lang: doc.lang,
        title: document.title.trim(),
        internalLinks: [...document.querySelectorAll('a[href^="/"]')].map((a) => a.getAttribute('href')),
        smallTargets: [...new Set(small)].slice(0, 15),
        bodyFontPx: parseFloat(getComputedStyle(document.body).fontSize),
      };
    });
    const broken = [...new Set(facts.internalLinks.map((h) => h.split('#')[0].split('?')[0]).filter((h) => h && !routeSet.has(h.replace(/\/$/, '') || '/') && !h.startsWith('/assets/')))];
    const entry = { overflowX: facts.overflowX, scrollWidth: facts.scrollWidth, h1: facts.h1, imgsNoAlt: facts.imgsNoAlt, lang: facts.lang, title: facts.title, bodyFontPx: facts.bodyFontPx, brokenInternalLinks: broken, smallTargets: facts.smallTargets, consoleErrors };
    if (w === 390 || w === 1440) {
      const axe = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa']).analyze();
      entry.axe = axe.violations.map((v) => ({ id: v.id, impact: v.impact, nodes: v.nodes.length, help: v.help, sample: v.nodes[0]?.target?.join(' ') }));
    }
    const name = (r === '/' ? 'inicio' : r.slice(1).replace(/\//g, '_')) + `-${w}.png`;
    await page.screenshot({ path: path.join(shotsDir, name), fullPage: true });
    results.routes[r][w] = entry;
    await context.close();
  }
}

// ---------- 5. Teclado y foco ----------
{
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  await page.goto('http://localhost:4199/', { waitUntil: 'networkidle' });
  const steps = [];
  for (let i = 0; i < 12; i++) {
    await page.keyboard.press('Tab');
    steps.push(await page.evaluate(() => {
      const el = document.activeElement;
      const st = getComputedStyle(el);
      return { tag: el.tagName.toLowerCase(), text: (el.innerText || el.getAttribute('aria-label') || '').trim().slice(0, 40), outline: st.outlineStyle !== 'none' && parseFloat(st.outlineWidth) >= 2 };
    }));
  }
  results.keyboard = { firstIsSkipLink: /saltar|skip|directamente al contenido/i.test(steps[0].text), allFocusVisible: steps.every((s) => s.outline), steps };
  await page.screenshot({ path: path.join(shotsDir, 'foco-teclado-1440.png') });
  // FAQ operable con teclado
  await page.goto('http://localhost:4199/pages/preguntas-frecuentes', { waitUntil: 'networkidle' });
  await page.focus('.ds-faq__item summary');
  await page.keyboard.press('Enter');
  results.keyboard.faqOpensWithEnter = await page.evaluate(() => document.querySelector('.ds-faq__item').open);
  // Menú móvil operable
  const m = await browser.newPage({ viewport: { width: 390, height: 900 } });
  await m.goto('http://localhost:4199/', { waitUntil: 'networkidle' });
  await m.click('header-drawer summary');
  await m.waitForTimeout(400);
  results.keyboard.mobileMenuLinks = await m.evaluate(() => [...document.querySelectorAll('#menu-drawer .menu-drawer__menu-item')].filter((a) => a.offsetParent).map((a) => a.innerText.trim()));
  await m.screenshot({ path: path.join(shotsDir, 'menu-movil-390.png') });
  await page.close(); await m.close();
}
await browser.close();
srv.close();

// ---------- 6. Resumen ----------
const flat = Object.entries(results.routes).flatMap(([r, ws]) => Object.entries(ws).map(([w, e]) => ({ r, w, ...e })));
results.summary = {
  routes: routes.length,
  viewports: WIDTHS,
  checksRun: flat.length,
  overflowX: flat.filter((e) => e.overflowX).map((e) => `${e.r}@${e.w}`),
  h1NotOne: flat.filter((e) => e.h1 !== 1).map((e) => `${e.r}@${e.w}:${e.h1}`),
  imgsNoAlt: flat.reduce((s, e) => s + e.imgsNoAlt, 0),
  brokenLinks: [...new Set(flat.flatMap((e) => e.brokenInternalLinks))],
  consoleErrors: [...new Set(flat.flatMap((e) => e.consoleErrors))],
  axeViolations: flat.filter((e) => e.axe).flatMap((e) => e.axe.map((v) => `${e.r}@${e.w} ${v.id} (${v.impact}, ${v.nodes})`)),
  smallTargets: [...new Set(flat.flatMap((e) => e.smallTargets.map((s) => `${e.w}: ${s}`)))],
  minBodyFontPx: Math.min(...flat.map((e) => e.bodyFontPx)),
  gateAllPass: Object.values(results.gate).every(Boolean),
  claimHits: results.claims.hits.length,
  trackerHits: results.tracking.hits.length,
};
fs.writeFileSync(path.join(reportsDir, 'qa-results.json'), JSON.stringify(results, null, 2));
fs.rmSync(tmp, { recursive: true, force: true });
console.log(JSON.stringify({ summary: results.summary, gate: results.gate, keyboard: { ...results.keyboard, steps: undefined } }, null, 2));

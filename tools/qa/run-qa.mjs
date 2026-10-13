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

// ---------- 1. Compilar los estados de la tienda ----------
const OUT = Object.fromEntries(['prototipo', 'preview', 'liveNoConfirm', 'liveIncomplete', 'liveComplete'].map((k) => [k, path.join(tmp, k)]));
const routes = build(OUT.preview, ['--mode', 'preview_comercial']);
build(OUT.prototipo, ['--mode', 'prototipo']);
build(OUT.liveNoConfirm, ['--mode', 'live', '--complete-globals', '--complete-metafields']);
build(OUT.liveIncomplete, ['--mode', 'live', '--confirm-live', '--complete-globals']);
build(OUT.liveComplete, ['--mode', 'live', '--confirm-live', '--complete-globals', '--complete-metafields']);
const outDefault = OUT.preview;

// ---------- 2. Compuerta de venta (análisis estático del HTML) ----------
const PRODUCT = '/products/dispositivo-bucal';
const PROTO_TEXT = /Todavía no vendemos|Producto en evaluación documental|Antes de vender, comprobamos|Todavía no aceptamos pedidos/;
function gateFacts(root) {
  const facts = {};
  for (const r of routes) {
    const html = fs.readFileSync(path.join(root, r === '/' ? 'index.html' : r + '/index.html'), 'utf8');
    facts[r] = {
      cartAddForm: /action="\/cart\/add"/.test(html),
      checkoutButton: /id="checkout"/.test(html),
      cartIcon: /id="cart-icon-bubble"/.test(html),
      moneyPrice: /class="price-item[^"]*"[^>]*>\s*[\d.,]+\s*€/.test(html),
      productJsonLd: /"@type":\s*"Product"/.test(html),
      ogPrice: /og:price:amount/.test(html),
      noindex: /<meta name="robots" content="noindex, nofollow">/.test(html),
      protoBanner: /class="ds-proto-banner"/.test(html),
      previewBanner: /ds-proto-banner--preview/.test(html),
      blockedBanner: /ds-proto-banner--blocked/.test(html),
      productHero: /class="ds-phero /.test(html),
      protoText: PROTO_TEXT.test(html.replace(/<script[\s\S]*?<\/script>/g, '')),
      placeholders: (html.match(/data-ds-placeholder/g) || []).length,
    };
  }
  return facts;
}
const any = (facts, k) => Object.values(facts).some((f) => f[k]);
const all = (facts, k) => Object.values(facts).every((f) => f[k]);
const F = Object.fromEntries(Object.entries(OUT).map(([k, d]) => [k, gateFacts(d)]));
results.gate = {
  'PROTOTIPO: ningún formulario /cart/add': !any(F.prototipo, 'cartAddForm'),
  'PROTOTIPO: sin precios ni hero comercial': !any(F.prototipo, 'moneyPrice') && !any(F.prototipo, 'productHero'),
  'PROTOTIPO: aviso de prototipo y noindex en todas las páginas': all(F.prototipo, 'protoBanner') && all(F.prototipo, 'noindex'),
  'PREVIEW: ningún formulario /cart/add ni checkout ni icono de carrito': !any(F.preview, 'cartAddForm') && !any(F.preview, 'checkoutButton') && !any(F.preview, 'cartIcon'),
  'PREVIEW: sin JSON-LD Product ni og:price': !any(F.preview, 'productJsonLd') && !any(F.preview, 'ogPrice'),
  'PREVIEW: sin importes (precio no confirmado → ⟦PENDIENTE⟧)': !any(F.preview, 'moneyPrice'),
  'PREVIEW: hero comercial en portada y landings': F.preview['/'].productHero && F.preview['/pages/landing-ronquidos'].productHero && F.preview['/pages/landing-pareja'].productHero,
  'PREVIEW: sin textos de prototipo contradictorios («todavía no vendemos»…)': !any(F.preview, 'protoText'),
  'PREVIEW: aviso «Vista previa comercial» y noindex en todas las páginas': all(F.preview, 'previewBanner') && all(F.preview, 'noindex'),
  'LIVE sin frase de confirmación: sin compra y aviso de bloqueo': !any(F.liveNoConfirm, 'cartAddForm') && all(F.liveNoConfirm, 'blockedBanner'),
  'LIVE confirmado con ficha incompleta: sin compra': !any(F.liveIncomplete, 'cartAddForm'),
  'LIVE confirmado y completo: compra, JSON-LD y carrito en la ficha': F.liveComplete[PRODUCT].cartAddForm && F.liveComplete[PRODUCT].productJsonLd && F.liveComplete[PRODUCT].cartIcon,
};
results.placeholdersByState = Object.fromEntries(Object.entries(F).map(([k, f]) => [k, Object.fromEntries(Object.entries(f).filter(([, v]) => v.placeholders).map(([r, v]) => [r, v.placeholders]))]));

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
  let text = visibleText(fs.readFileSync(path.join(OUT.preview, r === '/' ? 'index.html' : r + '/index.html'), 'utf8'));
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
const srvProto = await serve(OUT.prototipo, 4198);
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

// ---------- 4b. Primera pantalla móvil (C-01) y accesibilidad del estado PROTOTIPO ----------
results.firstScreen = {};
for (const r of ['/', '/pages/landing-ronquidos', '/pages/landing-pareja', PRODUCT]) {
  for (const [w, h] of [[390, 844], [375, 667]]) {
    const ctx2 = await browser.newContext({ viewport: { width: w, height: h } });
    const pg = await ctx2.newPage();
    await pg.goto('http://localhost:4199' + r, { waitUntil: 'networkidle' });
    results.firstScreen[`${r}@${w}x${h}`] = await pg.evaluate((isProduct) => {
      const vis = (el) => !!el && el.getBoundingClientRect().bottom <= window.innerHeight && el.getBoundingClientRect().height > 0;
      const root = isProduct ? document.querySelector('.product__info-container') : document.querySelector('.ds-phero');
      return {
        titulo: vis(root && root.querySelector('h1')),
        precio: vis(root && (root.querySelector('.ds-phero__price') || root.querySelector('.price'))),
        cta: vis(root && (root.querySelector('.ds-phero__actions .button') || root.querySelector('.ds-preview-cta .button, product-form .button'))),
      };
    }, r === PRODUCT);
    if (w === 390) await pg.screenshot({ path: path.join(shotsDir, `primera-pantalla_${r === '/' ? 'inicio' : r.slice(1).replace(/\//g, '_')}-390x844.png`) });
    await ctx2.close();
  }
}
results.prototipoAxe = {};
for (const r of routes) {
  const ctx3 = await browser.newContext({ viewport: { width: 390, height: 900 } });
  const pg = await ctx3.newPage();
  await pg.goto('http://localhost:4198' + r, { waitUntil: 'networkidle' });
  const axe = await new AxeBuilder({ page: pg }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa']).analyze();
  results.prototipoAxe[r] = axe.violations.map((v) => `${v.id} (${v.impact}, ${v.nodes.length})`);
  await ctx3.close();
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
srv.close(); srvProto.close();

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
  firstScreenAllVisible: Object.values(results.firstScreen).every((v) => v.titulo && v.precio && v.cta),
  prototipoAxeViolations: Object.values(results.prototipoAxe).flat().length,
  claimHits: results.claims.hits.length,
  trackerHits: results.tracking.hits.length,
};
fs.writeFileSync(path.join(reportsDir, 'qa-results.json'), JSON.stringify(results, null, 2));
fs.rmSync(tmp, { recursive: true, force: true });
console.log(JSON.stringify({ summary: results.summary, gate: results.gate, keyboard: { ...results.keyboard, steps: undefined } }, null, 2));

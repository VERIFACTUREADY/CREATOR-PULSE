// Genera una previsualización estática del tema en tools/../preview-out.
// Uso: node preview/build.mjs [--mode prototipo|preview_comercial|live] [--confirm-live]
//        [--complete-globals] [--complete-metafields] [--no-pending] [--out dir]
//  --mode               fuerza el estado de la tienda (por defecto, el de settings_data.json)
//  --confirm-live       escribe la frase de confirmación de LIVE
//  --complete-globals   rellena titular y oferta con valores FICTICIOS marcados como tales
//  --confirm-brand      simula ds_brand_confirmed = true (V2.2; sin ello LIVE queda bloqueado)
//  --no-pending         simula ds_show_pending = false
//  --complete-metafields rellena los metacampos compliance.* y commercial.* del producto demo
//               con valores FICTICIOS marcados como tales (solo para probar la compuerta)
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createEngine, readSchema, Color, Font } from './shim.mjs';

const here = path.dirname(fileURLToPath(import.meta.url));
const repo = path.resolve(here, '../..');
const themeDir = path.join(repo, 'theme');
const args = process.argv.slice(2);
const outDir = path.resolve(repo, args.includes('--out') ? args[args.indexOf('--out') + 1] : 'preview-out');
const fixture = JSON.parse(fs.readFileSync(path.join(here, 'fixture.json'), 'utf8'));

const readJSON = (p) => JSON.parse(fs.readFileSync(p, 'utf8').replace(/^\s*\/\*[\s\S]*?\*\/\s*/, ''));
// V2.1: inglés de EE. UU. por defecto (en.default.json); --locale es usa el borrador español.
const LOCALE = args.includes('--locale') ? args[args.indexOf('--locale') + 1] : 'en';
const locale = readJSON(path.join(themeDir, LOCALE === 'es' ? 'locales/es.json' : 'locales/en.default.json'));
const fallbackLocale = readJSON(path.join(themeDir, 'locales/en.default.json'));

const ctx = { missingTranslations: new Set(), errors: [] };
const engine = createEngine({ themeDir, locale, fallbackLocale, ctx });

const shopifyUrl = (v) => {
  if (typeof v !== 'string') return v;
  return v
    .replace(/^shopify:\/\/pages\//, '/pages/')
    .replace(/^shopify:\/\/products\//, '/products/')
    .replace(/^shopify:\/\/collections\//, '/collections/')
    .replace(/^shopify:\/\/blogs\//, '/blogs/')
    .replace(/^shopify:\/\/policies\//, '/policies/');
};

const linklists = {};
for (const [handle, links] of Object.entries(fixture.menus)) {
  const mk = (l) => ({ title: l.title, url: l.url, links: (l.links || []).map(mk), active: false, current: false, child_active: false, child_current: false, levels: l.links?.length ? 1 : 0, handle: l.title.toLowerCase(), type: 'page_link' });
  const list = links.map(mk);
  linklists[handle] = { handle, title: handle, links: list, levels: list.some((l) => l.links.length) ? 2 : 1 };
}

function resolveSetting(def, value) {
  let v = value !== undefined ? value : def.default;
  switch (def.type) {
    case 'color': return v ? new Color(v) : null;
    case 'font_picker': return new Font(v || def.default);
    case 'link_list': return v ? linklists[v] || null : null;
    case 'checkbox': return Boolean(v);
    case 'range': case 'number': return v === undefined || v === null || v === '' ? null : Number(v);
    case 'url': return v ? shopifyUrl(v) : null;
    case 'product': return v ? (fixture.pages.find((r) => r.product && r.product.handle === v) || {}).product || null : null;
    case 'image_picker': {
      // V3: imágenes reales de Shopify Files (shopify://shop_images/<archivo>) servidas desde media/producto/.
      const name = typeof v === 'string' && v.startsWith('shopify://shop_images/') ? v.slice('shopify://shop_images/'.length) : null;
      const meta = name && (fixture.shop_images || {})[name];
      return meta ? { src: '/shop-images/' + name, width: meta.width, height: meta.height, aspect_ratio: meta.width / meta.height, alt: meta.alt } : null;
    }
    case 'video': case 'collection': case 'blog': case 'page': case 'metaobject': return null;
    default: return v === undefined ? null : v;
  }
}

// ---- Ajustes globales ----
const schema = readJSON(path.join(themeDir, 'config/settings_schema.json'));
let data = readJSON(path.join(themeDir, 'config/settings_data.json'));
let current = typeof data.current === 'string' ? data.presets[data.current] : data.current;
const settings = {};
let schemeDef;
for (const group of schema) for (const s of group.settings || []) {
  if (!s.id) continue;
  if (s.type === 'color_scheme_group') { schemeDef = s; continue; }
  settings[s.id] = resolveSetting(s, current[s.id]);
}
const schemes = Object.entries(current.color_schemes).map(([id, sc]) => {
  const st = {};
  for (const d of schemeDef.definition) st[d.id] = d.type === 'color' ? new Color(sc.settings[d.id] ?? d.default) : (sc.settings[d.id] ?? d.default ?? '');
  return { id, settings: st };
});
for (const s of schemes) schemes[s.id] = s;
settings.color_schemes = schemes;
if (args.includes('--mode')) settings.ds_store_mode = args[args.indexOf('--mode') + 1];
if (args.includes('--confirm-live')) settings.ds_live_confirmation = 'VENTA REAL AUTORIZADA';
if (args.includes('--complete-globals')) {
  for (const k of ['ds_legal_name', 'ds_legal_tax_id', 'ds_legal_address', 'ds_legal_email', 'ds_offer_shipping', 'ds_offer_returns', 'ds_offer_support', 'ds_offer_payment'])
    settings[k] = 'VALOR FICTICIO DE PRUEBA';
  settings.ds_seller_country = 'US'; // V2.2: país del vendedor de PRUEBA (identidad fiscal → EIN)
}
// V2.2: la marca solo se da por confirmada con --confirm-brand (simula la búsqueda de marca y dominio concluida)
if (args.includes('--confirm-brand')) settings.ds_brand_confirmed = true;
// V2.2: --brand NOMBRE sustituye el ajuste de marca (prueba de coherencia: cabecera, pie, <title>, OG, JSON-LD)
if (args.includes('--brand')) settings.ds_brand_name = args[args.indexOf('--brand') + 1];
if (args.includes('--no-pending')) settings.ds_show_pending = false;

// ---- Secciones ----
const sectionCache = {};
function loadSection(type) {
  if (!sectionCache[type]) {
    const src = fs.readFileSync(path.join(themeDir, 'sections', type + '.liquid'), 'utf8');
    sectionCache[type] = { src, schema: readSchema(src), tpl: engine.parse(src, path.join(themeDir, 'sections', type + '.liquid')) };
  }
  return sectionCache[type];
}

let globals = {};
async function renderSection(id, type, data, groupClass) {
  const { schema: sch, tpl } = loadSection(type);
  const sset = {};
  for (const s of sch.settings || []) if (s.id) sset[s.id] = resolveSetting(s, data.settings?.[s.id]);
  const blocks = [];
  for (const bid of data.block_order || Object.keys(data.blocks || {})) {
    const b = data.blocks[bid];
    if (!b || b.disabled) continue;
    const bdef = (sch.blocks || []).find((x) => x.type === b.type) || { settings: [] };
    const bset = {};
    for (const s of bdef.settings || []) if (s.id) bset[s.id] = resolveSetting(s, b.settings?.[s.id]);
    blocks.push({ id: bid, type: b.type, settings: bset, shopify_attributes: '' });
  }
  const section = { id, settings: sset, blocks, location: groupClass || 'template' };
  let html;
  try {
    // En Shopify, `section` también es accesible desde los snippets renderizados.
    html = await engine.render(tpl, { section }, { globals: { ...globals, section } });
  } catch (e) {
    ctx.errors.push(`${globals.__route} :: sección ${type}: ${e.message.split('\n')[0]}`);
    html = `<!-- ERROR ${type} -->`;
  }
  const cls = ['shopify-section', groupClass ? `shopify-section-group-${groupClass}` : '', sch.class || ''].filter(Boolean).join(' ');
  return `<div id="shopify-section-${id}" class="${cls}">${html}</div>`;
}
ctx.renderSection = (id, type, data, g) => renderSection(id, type, data, g);
ctx.renderGroup = async (name) => {
  const g = readJSON(path.join(themeDir, 'sections', name + '.json'));
  let out = '';
  for (const key of g.order) {
    const s = g.sections[key];
    if (s.disabled) continue;
    out += await renderSection(`sections--ds__${key}`, s.type, s, name);
  }
  return out;
};

const layoutSrc = fs.readFileSync(path.join(themeDir, 'layout/theme.liquid'), 'utf8');
const layoutTpl = engine.parse(layoutSrc);

async function renderRoute(route) {
  const tplFile = path.join(themeDir, 'templates', route.template + '.json');
  const t = readJSON(tplFile);
  const [type, suffix] = route.template.split('.');
  globals = {
    __route: route.path,
    settings,
    shop: fixture.shop,
    routes: fixture.routes,
    linklists,
    localization: { available_countries: [], available_languages: [], country: { iso_code: 'US', currency: { iso_code: 'USD', symbol: '$' } }, language: { iso_code: LOCALE } },
    cart: { item_count: 0, items: [], total_price: 0, empty: true, attributes: {}, note: '' },
    customer: null,
    request: { locale: { iso_code: LOCALE }, design_mode: false, visual_preview_mode: false, page_type: type, path: route.path, origin: 'http://localhost', host: 'localhost' },
    template: { name: type, suffix: suffix || null, directory: null },
    page: route.page || null,
    product: route.product || null,
    canonical_url: 'http://localhost' + route.path,
    page_title: route.title,
    page_description: route.description || null,
    // Shopify inyecta el objeto global `Shopify` mediante content_for_header.
    content_for_header: '<script>window.Shopify = window.Shopify || { designMode: false };</script>',
    powered_by_link: '<a href="https://www.shopify.com" rel="nofollow" target="_blank">Powered by Shopify</a>',
    current_page: 1,
    current_tags: null,
    scheme_classes: '',
  };
  let main = '';
  for (const key of t.order) {
    const s = t.sections[key];
    if (s.disabled) continue;
    main += await renderSection(`template--ds__${key}`, s.type, s, null);
  }
  globals.content_for_layout = main;
  try {
    return await engine.render(layoutTpl, {}, { globals });
  } catch (e) {
    ctx.errors.push(`${route.path} :: layout: ${e.message.split('\n')[0]}`);
    return `<!-- ERROR layout -->${main}`;
  }
}

// ---- Salida ----
fs.rmSync(outDir, { recursive: true, force: true });
fs.mkdirSync(path.join(outDir, 'assets'), { recursive: true });
fs.cpSync(path.join(themeDir, 'assets'), path.join(outDir, 'assets'), { recursive: true });
fs.mkdirSync(path.join(outDir, 'fonts'), { recursive: true });
const fontSrc = path.join(here, '../node_modules/@fontsource/lato/files');
for (const w of ['400', '700']) for (const st of ['normal', 'italic'])
  fs.copyFileSync(path.join(fontSrc, `lato-latin-${w}-${st}.woff2`), path.join(outDir, 'fonts', `lato-${w}-${st}.woff2`));
// V4: titulares en Poppins (mismo archivo que sirve la biblioteca de fuentes de Shopify).
for (const w of ['700', '800']) fs.copyFileSync(path.join(here, `../node_modules/@fontsource/poppins/files/poppins-latin-${w}-normal.woff2`), path.join(outDir, 'fonts', `poppins-${w}-normal.woff2`));

// V3: fotos reales del producto (mismas que en Shopify Files), fuera del ZIP del tema.
fs.mkdirSync(path.join(outDir, 'shop-images'), { recursive: true });
for (const f of fs.readdirSync(path.join(repo, 'media/producto'))) fs.copyFileSync(path.join(repo, 'media/producto', f), path.join(outDir, 'shop-images', f));

if (args.includes('--complete-metafields')) {
  // Solo para probar la compuerta. Nada de esto se copia al tema.
  const demo = 'VALOR FICTICIO DE PRUEBA';
  // V2.2: mercado EE. UU. → campos compartidos + regulatory_us. Los europeos NO se rellenan (no cuentan en EE. UU.).
  const comp = ['manufacturer_legal_name', 'model_reference', 'materials', 'lot_traceability'];
  const regUs = ['fda_510k_number', 'fda_product_code', 'indications_for_use', 'ifu_en', 'warnings_en', 'contraindications_en', 'us_importer_of_record', 'fda_registration_listing', 'ftc_claims_review', 'human_verification'];
  const comm = ['short_benefit', 'what_is', 'how_to_steps', 'includes', 'for_whom', 'features', 'care', 'delivery_window'];
  fs.mkdirSync(path.join(outDir, 'test-media'), { recursive: true });
  fs.writeFileSync(path.join(outDir, 'test-media/ficticia.svg'), '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 800"><rect width="800" height="800" fill="#ccc"/><text x="400" y="400" font-size="40" text-anchor="middle" font-family="sans-serif">IMAGEN FICTICIA DE PRUEBA</text></svg>');
  const img = { src: '/test-media/ficticia.svg', width: 800, height: 800, aspect_ratio: 1, alt: 'Imagen ficticia de prueba', id: 901 };
  for (const r of fixture.pages) if (r.product) {
    r.product.metafields.compliance = Object.fromEntries(comp.map((k) => [k, { value: demo }]));
    r.product.metafields.regulatory_us = Object.fromEntries(regUs.map((k) => [k, { value: demo }]));
    r.product.metafields.commercial = Object.fromEntries(comm.map((k) => [k, { value: demo }]));
    r.product.metafields.commercial.price_confirmed = { value: true };
    r.product.price = 2990;
    r.product.selected_or_first_available_variant.price = 2990;
    r.product.media = [{ id: 901, media_type: 'image', position: 1, alt: img.alt, preview_image: img, src: img.src, width: 800, height: 800, aspect_ratio: 1 }];
    r.product.featured_media = r.product.media[0];
    r.product.images = [img];
  }
}
const index = [];
for (const route of fixture.pages) {
  const html = await renderRoute(route);
  const dest = route.path === '/' ? path.join(outDir, 'index.html') : path.join(outDir, route.path, 'index.html');
  fs.mkdirSync(path.dirname(dest), { recursive: true });
  fs.writeFileSync(dest, html);
  index.push(route.path);
}
fs.writeFileSync(path.join(outDir, 'routes.json'), JSON.stringify(index, null, 2));

console.log(`Previsualización: ${index.length} páginas en ${path.relative(repo, outDir)}`);
if (ctx.missingTranslations.size) console.log('Traducciones ausentes:', [...ctx.missingTranslations].join(', '));
if (ctx.errors.length) { console.log('ERRORES:\n' + ctx.errors.join('\n')); process.exitCode = 1; }

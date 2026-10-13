// Genera una previsualización estática del tema en tools/../preview-out.
// Uso: node preview/build.mjs [--mode prototipo|preview_comercial|live] [--confirm-live]
//        [--complete-globals] [--complete-metafields] [--no-pending] [--out dir]
//  --mode               fuerza el estado de la tienda (por defecto, el de settings_data.json)
//  --confirm-live       escribe la frase de confirmación de LIVE
//  --complete-globals   rellena titular y oferta con valores FICTICIOS marcados como tales
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
const locale = readJSON(path.join(themeDir, 'locales/es.json'));
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
    case 'image_picker': case 'video': case 'collection': case 'blog': case 'page': case 'metaobject': return null;
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
}
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
    localization: { available_countries: [], available_languages: [], country: { iso_code: 'ES', currency: { iso_code: 'EUR', symbol: '€' } }, language: { iso_code: 'es' } },
    cart: { item_count: 0, items: [], total_price: 0, empty: true, attributes: {}, note: '' },
    customer: null,
    request: { locale: { iso_code: 'es' }, design_mode: false, visual_preview_mode: false, page_type: type, path: route.path, origin: 'http://localhost', host: 'localhost' },
    template: { name: type, suffix: suffix || null, directory: null },
    page: route.page || null,
    product: route.product || null,
    canonical_url: 'http://localhost' + route.path,
    page_title: route.title,
    page_description: route.description || null,
    // Shopify inyecta el objeto global `Shopify` mediante content_for_header.
    content_for_header: '<script>window.Shopify = window.Shopify || { designMode: false };</script>',
    powered_by_link: '<a href="https://www.shopify.com" rel="nofollow" target="_blank">Tecnología de Shopify</a>',
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

if (args.includes('--complete-metafields')) {
  // Solo para probar la compuerta. Nada de esto se copia al tema.
  const demo = 'VALOR FICTICIO DE PRUEBA';
  const comp = ['manufacturer_legal_name', 'model_reference', 'intended_purpose', 'materials', 'ifu_es', 'warnings_es', 'contraindications_es', 'eu_declaration_ref', 'economic_operator', 'lot_traceability', 'claim_approval_version'];
  const comm = ['short_benefit', 'what_is', 'how_to_steps', 'includes', 'for_whom', 'features', 'care', 'delivery_window'];
  fs.mkdirSync(path.join(outDir, 'test-media'), { recursive: true });
  fs.writeFileSync(path.join(outDir, 'test-media/ficticia.svg'), '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 800"><rect width="800" height="800" fill="#ccc"/><text x="400" y="400" font-size="40" text-anchor="middle" font-family="sans-serif">IMAGEN FICTICIA DE PRUEBA</text></svg>');
  const img = { src: '/test-media/ficticia.svg', width: 800, height: 800, aspect_ratio: 1, alt: 'Imagen ficticia de prueba', id: 901 };
  for (const r of fixture.pages) if (r.product) {
    r.product.metafields.compliance = Object.fromEntries(comp.map((k) => [k, { value: demo }]));
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

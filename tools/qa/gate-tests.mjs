// Pruebas unitarias de la compuerta de venta y del escape del formulario (auditoría V2: C-03, C-10).
// Renderiza los snippets reales del tema con liquidjs y distintos estados/productos.
// Uso: node qa/gate-tests.mjs  → qa/reports/gate-tests.json (sale con código 1 si algo falla)
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createEngine, readSchema } from '../preview/shim.mjs';

const here = path.dirname(fileURLToPath(import.meta.url));
const repo = path.resolve(here, '../..');
const themeDir = path.join(repo, 'theme');
const readJSON = (p) => JSON.parse(fs.readFileSync(p, 'utf8'));
const ctx = { missingTranslations: new Set(), errors: [], formOverride: null };
const engine = createEngine({ themeDir, locale: readJSON(path.join(themeDir, 'locales/en.default.json')), fallbackLocale: readJSON(path.join(themeDir, 'locales/en.default.json')), ctx });

const GLOBALS = { ds_legal_name: 'X', ds_legal_tax_id: 'X', ds_legal_address: 'X', ds_legal_email: 'x@x', ds_offer_shipping: 'X', ds_offer_returns: 'X', ds_offer_support: 'X', ds_offer_payment: 'X' };
const COMP = ['manufacturer_legal_name', 'model_reference', 'intended_purpose', 'materials', 'ifu_es', 'warnings_es', 'contraindications_es', 'eu_declaration_ref', 'economic_operator', 'lot_traceability', 'claim_approval_version'];
const COMM = ['short_benefit', 'what_is', 'how_to_steps', 'includes', 'delivery_window'];
function product(over = {}) {
  const p = {
    id: 7, title: 'Producto de prueba', available: true, price: 2990, media: [{ id: 1 }],
    selected_or_first_available_variant: { id: 70, price: 2990, available: true },
    metafields: { compliance: Object.fromEntries(COMP.map((k) => [k, { value: 'x' }])), commercial: { ...Object.fromEntries(COMM.map((k) => [k, { value: 'x' }])), price_confirmed: { value: true } } },
  };
  return { ...p, ...over };
}
function settings(mode, { confirm = true, globals = true } = {}) {
  return { ds_store_mode: mode, ds_live_confirmation: confirm ? 'VENTA REAL AUTORIZADA' : '', ds_show_pending: true, ...(globals ? GLOBALS : {}) };
}
const render = (tpl, s, scope = {}) => engine.parseAndRender(tpl, scope, { globals: { settings: s } }).then((x) => x.trim());
const ready = (s, p) => render("{% render 'ds-commerce-ready', product: p %}", s, { p });
const offer = (s, p) => render("{% render 'ds-offer-visible', product: p %}", s, { p });
const mode = (s) => render("{% render 'ds-mode' %}", s);

const results = [];
const check = (name, ok, detail) => { results.push({ prueba: name, ok, detalle: detail }); console.log(`${ok ? 'OK  ' : 'FAIL'} ${name}${ok ? '' : ' → ' + JSON.stringify(detail)}`); };

// --- ds-mode ---
check('Modo desconocido → prototipo (denegar por defecto)', (await mode({ ds_store_mode: 'xyz' })) === 'prototipo', await mode({ ds_store_mode: 'xyz' }));
check('Sin ajuste → prototipo', (await mode({})) === 'prototipo', await mode({}));
check('LIVE sin frase → preview', (await mode(settings('live', { confirm: false }))) === 'preview', null);
check('LIVE con frase en minúsculas → preview', (await mode({ ...settings('live'), ds_live_confirmation: 'venta real autorizada' })) === 'preview', null);
check('LIVE confirmado pero faltan datos globales → preview', (await mode(settings('live', { globals: false }))) === 'preview', null);
check('LIVE confirmado y completo → live', (await mode(settings('live'))) === 'live', null);

// --- ds-commerce-ready (C-03) ---
const LIVE = settings('live');
check('product = blank (null) en LIVE → false [fallo V1]', (await ready(LIVE, null)) === 'false', await ready(LIVE, null));
check('product = blank ("") en LIVE → false', (await ready(LIVE, '')) === 'false', null);
check('Producto completo en LIVE → true', (await ready(LIVE, product())) === 'true', await ready(LIVE, product()));
check('Producto completo en PREVIEW → false', (await ready(settings('preview_comercial'), product())) === 'false', null);
check('Producto completo en PROTOTIPO → false', (await ready(settings('prototipo'), product())) === 'false', null);
check('Producto completo, LIVE sin frase → false', (await ready(settings('live', { confirm: false }), product())) === 'false', null);
check('Producto completo, LIVE sin datos globales → false', (await ready(settings('live', { globals: false }), product())) === 'false', null);
check('Producto agotado en LIVE → false', (await ready(LIVE, product({ available: false }))) === 'false', null);
check('Producto sin fotos en LIVE → false', (await ready(LIVE, product({ media: [] }))) === 'false', null);
{
  const p = product(); p.metafields.commercial.price_confirmed = { value: false };
  check('Precio no confirmado en LIVE → false', (await ready(LIVE, p)) === 'false', null);
}
for (const k of COMP) {
  const p = product(); delete p.metafields.compliance[k];
  check(`Falta compliance.${k} → false`, (await ready(LIVE, p)) === 'false', null);
}
for (const k of COMM) {
  const p = product(); delete p.metafields.commercial[k];
  check(`Falta commercial.${k} → false`, (await ready(LIVE, p)) === 'false', null);
}

// --- ds-offer-visible ---
check('Oferta: blank en PREVIEW → false', (await offer(settings('preview_comercial'), null)) === 'false', null);
check('Oferta: producto en PREVIEW → true', (await offer(settings('preview_comercial'), product())) === 'true', null);
check('Oferta: producto en PROTOTIPO → false', (await offer(settings('prototipo'), product())) === 'false', null);

// --- price.liquid y buy-buttons.liquid (efectos visibles) ---
{
  const html = await render("{% render 'price', product: p, placeholder: true %}", LIVE, { p: null });
  check('Precio con product blank + placeholder (featured-product vacío) → sin «$19.99»', !/19[.,]99/.test(html) && html === '', html.slice(0, 120));
  const pv = product(); pv.metafields.commercial.price_confirmed = { value: false };
  const html2 = await render("{% render 'price', product: p %}", settings('preview_comercial'), { p: pv });
  check('PREVIEW + precio no confirmado → marcador ⟦PENDIENTE⟧, sin importe', /data-ds-placeholder/.test(html2) && !/29\.90/.test(html2), html2.slice(0, 160));
  const html3 = await render("{% render 'price', product: p %}", settings('preview_comercial'), { p: product() });
  check('PREVIEW + precio confirmado → importe real visible ($29.90)', /\$29\.90/.test(html3), null);
  const pc = product({ compare_at_price: 3990, selected_or_first_available_variant: { id: 70, price: 2990, compare_at_price: 3990, available: true } });
  const html4 = await render("{% render 'price', product: p, use_variant: true, show_compare_at_price: true %}", settings('preview_comercial'), { p: pc });
  check('Precio tachado sin compare_at_verified → no se muestra «$39.90»', !/39\.90/.test(html4), null);
}
for (const [m, expectForm] of [['prototipo', false], ['preview_comercial', false], ['live', true]]) {
  const html = await render("{% render 'buy-buttons', product: p, block: b, product_form_id: 'f', section_id: 's' %}", settings(m), { p: product(), b: { settings: {}, shopify_attributes: '' } });
  check(`buy-buttons en ${m}: formulario /cart/add ${expectForm ? 'presente' : 'ausente'}`, /action="\/cart\/add"/.test(html) === expectForm, null);
}
{
  const html = await render("{% render 'buy-buttons', product: p, block: b %}", LIVE, { p: null, b: { settings: {}, shopify_attributes: '' } });
  check('buy-buttons con product blank en LIVE → sin formulario', !/action="\/cart\/add"/.test(html), null);
}

// --- C-10: escape del formulario de contacto ---
const PAYLOADS = ['"><script>alert(1)</script>', "' onmouseover='alert(1)", '<img src=x onerror=alert(1)>', 'Ñandú «comillas» 😴 &amp; <b>negrita</b>'];
const src = fs.readFileSync(path.join(themeDir, 'sections/ds-contact.liquid'), 'utf8');
const sch = readSchema(src);
const section = { id: 'c', settings: Object.fromEntries((sch.settings || []).filter((s) => s.id).map((s) => [s.id, s.default ?? null])), blocks: [] };
for (const p of PAYLOADS) {
  ctx.formOverride = { name: p, email: p, body: p, errors: { messages: { email: 'no válido' } } };
  const html = await engine.parseAndRender(src, { section }, { globals: { settings: settings('preview_comercial'), section } });
  const raw = /<script>alert|<img src=x|' onmouseover='|<b>negrita<\/b>/.test(html);
  check(`Contacto escapa: ${p.slice(0, 28)}`, !raw && /value="[^"]*&quot;|&lt;|&#39;|&amp;/.test(html), raw ? 'SIN ESCAPAR' : null);
}
ctx.formOverride = null;

fs.mkdirSync(path.join(repo, 'qa/reports'), { recursive: true });
fs.writeFileSync(path.join(repo, 'qa/reports/gate-tests.json'), JSON.stringify(results, null, 2));
const failed = results.filter((r) => !r.ok).length;
console.log(`\n${results.length - failed}/${results.length} pruebas OK`);
process.exitCode = failed ? 1 : 0;

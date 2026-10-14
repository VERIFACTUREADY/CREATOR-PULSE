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

const GLOBALS = { ds_legal_name: 'X', ds_legal_tax_id: 'X', ds_legal_address: 'X', ds_legal_email: 'x@x', ds_offer_shipping: 'X', ds_offer_returns: 'X', ds_offer_support: 'X', ds_offer_payment: 'X', ds_brand_confirmed: true, ds_seller_country: 'US' };
// V2.2: campos por mercado. Valores 'x' = datos de PRUEBA, no documentos reales.
const SHARED = ['manufacturer_legal_name', 'model_reference', 'materials', 'lot_traceability'];
const EU = ['intended_purpose', 'ifu_es', 'warnings_es', 'contraindications_es', 'eu_declaration_ref', 'economic_operator', 'claim_approval_version'];
const US = ['fda_510k_number', 'fda_product_code', 'indications_for_use', 'ifu_en', 'warnings_en', 'contraindications_en', 'us_importer_of_record', 'fda_registration_listing', 'ftc_claims_review', 'human_verification'];
const COMM = ['short_benefit', 'what_is', 'how_to_steps', 'includes', 'delivery_window'];
const fill = (keys) => Object.fromEntries(keys.map((k) => [k, { value: 'x' }]));
// Producto A: completo para EE. UU. · Producto B: NO apto (solo documentación europea, sin regulatory_us).
function product(over = {}, { market = 'us' } = {}) {
  const p = {
    id: 7, title: 'Producto A (prueba)', handle: 'producto-a', url: '/products/producto-a', available: true, price: 2990, price_min: 2990, price_max: 2990, media: [{ id: 1 }],
    variants: [{ id: 70, price: 2990, available: true, title: 'Default Title' }], variants_count: 1, has_only_default_variant: true,
    selected_or_first_available_variant: { id: 70, price: 2990, available: true, title: 'Default Title' },
    metafields: { compliance: { ...fill(SHARED), ...(market === 'eu' ? fill(EU) : {}) }, regulatory_us: market === 'us' ? fill(US) : {}, commercial: { ...fill(COMM), price_confirmed: { value: true } } },
  };
  return { ...p, ...over };
}
const productB = () => product({ id: 8, title: 'Producto B (prueba, no apto)', handle: 'producto-b', url: '/products/producto-b', variants: [{ id: 80, price: 2990, available: true, title: 'Default Title' }], selected_or_first_available_variant: { id: 80, price: 2990, available: true, title: 'Default Title' } }, { market: 'eu' });
function settings(mode, { confirm = true, globals = true } = {}) {
  return { ds_store_mode: mode, ds_live_confirmation: confirm ? 'VENTA REAL AUTORIZADA' : '', ds_show_pending: true, ds_market: 'us', ...(globals ? GLOBALS : {}) };
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
// V2.2 (auditoría V2.1 P1): marca provisional y país del vendedor bloquean LIVE
check('LIVE completo con marca SIN confirmar → preview', (await mode({ ...settings('live'), ds_brand_confirmed: false })) === 'preview', null);
check('LIVE completo sin país del vendedor → preview', (await mode({ ...settings('live'), ds_seller_country: '' })) === 'preview', null);
{
  const bl = await render("{% render 'ds-live-blockers' %}", { ...settings('live'), ds_brand_confirmed: false, ds_seller_country: '' });
  check('Bloqueos de LIVE nombran la marca y el país del vendedor', /brand confirmation/.test(bl) && /seller country/.test(bl), bl);
}
for (const [c, want] of [['US', 'EIN'], ['ES', 'NIF/CIF (Spain)'], ['OTHER', 'Tax ID'], ['', 'Tax ID (seller country pending)']]) {
  const got = await render("{% render 'ds-tax-label' %}", { ds_seller_country: c });
  check(`Etiqueta fiscal según país del vendedor «${c || 'vacío'}» → ${want}`, got === want, got);
}

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
for (const k of [...SHARED, ...US]) {
  const p = product(); delete p.metafields.compliance[k]; delete p.metafields.regulatory_us[k];
  check(`EE. UU.: falta ${k} → false`, (await ready(LIVE, p)) === 'false', null);
}
for (const k of COMM) {
  const p = product(); delete p.metafields.commercial[k];
  check(`Falta commercial.${k} → false`, (await ready(LIVE, p)) === 'false', null);
}
// --- V2.2 P0-1: los campos europeos NO cuentan como estadounidenses ---
check('Producto B (solo documentación UE completa) en mercado EE. UU. → false', (await ready(LIVE, productB())) === 'false', null);
{
  const m = await render("{% render 'ds-product-missing', product: p %}", LIVE, { p: productB() });
  check('Producto B: la lista de faltas nombra FDA, instrucciones en inglés y verificación humana', /FDA clearance/.test(m) && /English instructions/.test(m) && /human regulatory verification/.test(m), m);
}
check('Producto B en mercado UE (con sus campos UE) → true', (await ready({ ...LIVE, ds_market: 'eu' }, productB())) === 'true', null);
check('Producto A (solo regulatory_us) en mercado UE → false (tampoco al revés)', (await ready({ ...LIVE, ds_market: 'eu' }, product())) === 'false', null);
{
  const p = product(); p.metafields.compliance = { ...p.metafields.compliance, ...fill(EU) }; delete p.metafields.regulatory_us.fda_510k_number;
  check('A con docs UE completas pero sin 510(k) → false (la UE no sustituye a la FDA)', (await ready(LIVE, p)) === 'false', null);
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

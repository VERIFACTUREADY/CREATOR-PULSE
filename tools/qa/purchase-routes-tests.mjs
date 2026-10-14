// V2.2 · P0-2: rutas de compra alternativas de Dawn con DOS productos.
// A = completo para EE. UU. (datos de PRUEBA) · B = no apto (solo documentación UE).
// Renderiza el código real del tema con liquidjs y busca formularios/acciones de compra.
// Uso: node qa/purchase-routes-tests.mjs → qa/reports/purchase-routes-tests.json
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createEngine, readSchema } from '../preview/shim.mjs';

const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const themeDir = path.join(repo, 'theme');
const readJSON = (p) => JSON.parse(fs.readFileSync(p, 'utf8'));
const ctx = { missingTranslations: new Set(), errors: [] };
const engine = createEngine({ themeDir, locale: readJSON(path.join(themeDir, 'locales/en.default.json')), fallbackLocale: readJSON(path.join(themeDir, 'locales/en.default.json')), ctx });

const fill = (keys) => Object.fromEntries(keys.map((k) => [k, { value: 'x' }]));
const SHARED = ['manufacturer_legal_name', 'model_reference', 'materials', 'lot_traceability'];
const EU = ['intended_purpose', 'ifu_es', 'warnings_es', 'contraindications_es', 'eu_declaration_ref', 'economic_operator', 'claim_approval_version'];
const US = ['fda_510k_number', 'fda_product_code', 'indications_for_use', 'ifu_en', 'warnings_en', 'contraindications_en', 'us_importer_of_record', 'fda_registration_listing', 'ftc_claims_review', 'human_verification'];
const COMM = ['short_benefit', 'what_is', 'how_to_steps', 'includes', 'delivery_window'];
const img = { src: '/x.jpg', width: 800, height: 800, aspect_ratio: 1, alt: 'test', id: 1 };
function mk(id, handle, market) {
  const variant = { id: id * 10, title: 'Default Title', price: 2990, available: true, sku: 'T', quantity_rule: { min: 1, max: null, increment: 1 }, product: null, featured_image: null, image: null, options: ['Default Title'] };
  const p = {
    id, title: `Product ${handle}`, handle, url: `/products/${handle}`, available: true, price: 2990, price_min: 2990, price_max: 2990, compare_at_price: null,
    media: [{ id: 1, media_type: 'image', preview_image: img, alt: 'test' }], featured_media: { id: 1, media_type: 'image', preview_image: img, alt: 'test' }, images: [img],
    variants: [variant], variants_count: 1, has_only_default_variant: true, selected_or_first_available_variant: variant, first_available_variant: variant,
    options_with_values: [], options: ['Title'], tags: [], vendor: '', type: '', quantity_price_breaks_configured: false,
    metafields: { compliance: { ...fill(SHARED), ...(market === 'eu' ? fill(EU) : {}) }, regulatory_us: market === 'us' ? fill(US) : {}, commercial: { ...fill(COMM), price_confirmed: { value: true } } },
  };
  variant.product = p;
  return p;
}
const A = mk(1, 'product-a', 'us');
const B = mk(2, 'product-b', 'eu');
const SETTINGS = (mode) => ({
  ds_store_mode: mode, ds_live_confirmation: 'VENTA REAL AUTORIZADA', ds_market: 'us', ds_brand_confirmed: true, ds_seller_country: 'US',
  ds_legal_name: 'X', ds_legal_tax_id: 'X', ds_legal_address: 'X', ds_legal_email: 'x@x', ds_offer_shipping: 'X', ds_offer_returns: 'X', ds_offer_support: 'X', ds_offer_payment: 'X',
  cart_type: 'drawer', currency_code_enabled: false, card_style: 'standard', show_vendor: false,
});
const cartOf = (items) => ({ item_count: items.length, items: items.map((p) => ({ product: p, variant: p.selected_or_first_available_variant, quantity: 1, key: `k${p.id}`, url: p.url, title: p.title, final_line_price: 2990, original_line_price: 2990, line_level_discount_allocations: [], properties: {} })), total_price: 2990 * items.length, original_total_price: 2990 * items.length, empty: items.length === 0, cart_level_discount_applications: [], attributes: {}, note: '', currency: { iso_code: 'USD' } });

function sectionObj(file) {
  const sch = readSchema(fs.readFileSync(path.join(themeDir, 'sections', file), 'utf8'));
  return { id: 'test', settings: Object.fromEntries((sch.settings || []).filter((s) => s.id).map((s) => [s.id, s.default ?? null])), blocks: [] };
}
async function renderFile(rel, scope, globals) {
  const src = fs.readFileSync(path.join(themeDir, rel), 'utf8');
  try {
    return await engine.parseAndRender(src, scope, { globals });
  } catch (e) {
    return `RENDER_ERROR ${e.message.split('\n')[0]}`;
  }
}
const routes = { 'templates.cart.cart': '', cart_url: '/cart', cart_add_url: '/cart/add', cart_update_url: '/cart/update', cart_change_url: '/cart/change', root_url: '/' };
const res = [];
const check = (name, ok, detail) => { res.push({ prueba: name, ok, detalle: detail }); console.log(`${ok ? 'OK  ' : 'FAIL'} ${name}${ok ? '' : ' → ' + JSON.stringify(detail)}`); };

for (const mode of ['live', 'preview_comercial', 'prototipo']) {
  const g = (extra = {}) => ({ settings: SETTINGS(mode), routes, cart: cartOf([]), shop: { name: 'T' }, request: { locale: { iso_code: 'en' } }, ...extra });
  const expectA = mode === 'live';
  for (const [label, P] of [['A', A], ['B', B]]) {
    const want = expectA && label === 'A';
    // 1. Tarjeta de producto con «añadir rápido» estándar y bulk (listados, colecciones, búsqueda, relacionados, destacados de colección)
    for (const qa of ['standard', 'bulk']) {
      const section = { id: 'grid', settings: { quick_add: qa } };
      const html = await renderFile('snippets/card-product.liquid', { card_product: P, quick_add: qa, section_id: 'grid', media_aspect_ratio: 'square', image_shape: 'default', show_secondary_image: false }, g({ section }));
      check(`[${mode}] card-product quick_add=${qa} · producto ${label} → ${want ? 'con' : 'SIN'} compra`, !html.startsWith('RENDER_ERROR') && /class="quick-add|<quick-add-bulk|quick-add__submit|action="\/cart\/add"/.test(html) === want, html.startsWith('RENDER_ERROR') ? html : null);
    }
    // 2. Lista de pedido rápido (sección quick-order-list y modal bulk)
    {
      const section = sectionObj('quick-order-list.liquid');
      const html = await renderFile('snippets/quick-order-list.liquid', { product: P, show_image: true, show_sku: true }, g({ section, product: P }));
      check(`[${mode}] quick-order-list · producto ${label} → ${want ? 'con' : 'SIN'} formulario`, !html.startsWith('RENDER_ERROR') && /QuickOrderList|cart\/update/.test(html) === want, html.startsWith('RENDER_ERROR') ? html : null);
    }
    // 3. Botones de compra (ficha y producto destacado usan el mismo snippet)
    {
      const html = await renderFile('snippets/buy-buttons.liquid', { product: P, block: { settings: {}, shopify_attributes: '' }, product_form_id: 'f', section_id: 's' }, g());
      check(`[${mode}] buy-buttons (ficha / featured-product) · producto ${label} → ${want ? 'con' : 'SIN'} /cart/add`, /action="\/cart\/add"/.test(html) === want, null);
    }
    // 4. Producto destacado: sección completa
    {
      const section = sectionObj('featured-product.liquid');
      section.blocks = [{ id: 'b1', type: 'buy_buttons', settings: { show_dynamic_checkout: false }, shopify_attributes: '' }];
      section.settings.product = P;
      const html = await renderFile('sections/featured-product.liquid', { section }, g({ section, product: P }));
      check(`[${mode}] featured-product (sección) · producto ${label} → ${want ? 'con' : 'SIN'} /cart/add`, !html.startsWith('RENDER_ERROR') && /action="\/cart\/add"/.test(html) === want, html.startsWith('RENDER_ERROR') ? html : null);
    }
  }
  // 5. Carrito: checkout solo si TODOS los artículos son aptos
  for (const [label, items, wantCheckout] of [['[A]', [A], mode === 'live'], ['[A, B]', [A, B], false], ['[B]', [B], false]]) {
    const cart = cartOf(items);
    const footer = sectionObj('main-cart-footer.liquid');
    footer.blocks = [{ id: 'sub', type: 'subtotal', settings: {}, shopify_attributes: '' }, { id: 'btn', type: 'buttons', settings: {}, shopify_attributes: '' }];
    const h1 = await renderFile('sections/main-cart-footer.liquid', { section: footer }, g({ cart, section: footer }));
    check(`[${mode}] /cart con ${label} → checkout ${wantCheckout ? 'visible' : 'OCULTO'}`, !h1.startsWith('RENDER_ERROR') && /id="checkout"/.test(h1) === wantCheckout, h1.startsWith('RENDER_ERROR') ? h1 : null);
    const ready = (await renderFile('snippets/ds-cart-ready.liquid', {}, g({ cart }))).trim();
    check(`[${mode}] ds-cart-ready ${label} → ${wantCheckout}`, ready === String(wantCheckout), ready);
  }
}

fs.mkdirSync(path.join(repo, 'qa/reports'), { recursive: true });
fs.writeFileSync(path.join(repo, 'qa/reports/purchase-routes-tests.json'), JSON.stringify(res, null, 2));
const failed = res.filter((r) => !r.ok).length;
console.log(`\n${res.length - failed}/${res.length} pruebas OK`);
process.exitCode = failed ? 1 : 0;

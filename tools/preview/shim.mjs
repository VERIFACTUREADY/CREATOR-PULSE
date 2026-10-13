// Simulación mínima del entorno Liquid de Shopify para previsualizar el tema
// en local, sin tienda ni credenciales. NO es Shopify: solo implementa lo que
// usa este tema. Las diferencias conocidas están en docs/10_QA_LANZAMIENTO.md.
import fs from 'node:fs';
import path from 'node:path';
import { Liquid, Drop, Tokenizer } from 'liquidjs';

export class Color extends Drop {
  constructor(hex) {
    super();
    this.hex = (hex || '#000000').toUpperCase();
    const h = this.hex.replace('#', '');
    this.red = parseInt(h.slice(0, 2), 16);
    this.green = parseInt(h.slice(2, 4), 16);
    this.blue = parseInt(h.slice(4, 6), 16);
    this.alpha = 1;
    this.rgb = `${this.red} ${this.green} ${this.blue}`;
  }
  valueOf() { return this.hex; }
  toString() { return this.hex; }
}

const FONTS = {
  lato: { family: 'Lato', fallback: 'sans-serif' },
  assistant: { family: 'Assistant', fallback: 'sans-serif' },
};
export class Font extends Drop {
  constructor(handle) {
    super();
    const [name, variant = 'n4'] = String(handle).split('_');
    const f = FONTS[name] || { family: name, fallback: 'sans-serif' };
    this.handle = handle;
    this.family = f.family;
    this.fallback_families = f.fallback;
    this.style = variant[0] === 'i' ? 'italic' : 'normal';
    this.weight = String(Number(variant[1]) * 100);
    this['system?'] = false;
    this.name = name;
  }
  valueOf() { return this.family; }
  toString() { return this.family; }
}

function fontFile(font) {
  return `/fonts/${font.name}-${font.weight}-${font.style}.woff2`;
}

// Lee el JSON del bloque {% schema %} de una sección.
export function readSchema(src) {
  const m = src.match(/\{%-?\s*schema\s*-?%\}([\s\S]*?)\{%-?\s*endschema\s*-?%\}/);
  return m ? JSON.parse(m[1]) : {};
}

export function createEngine({ themeDir, locale, fallbackLocale, ctx }) {
  const engine = new Liquid({
    root: [path.join(themeDir, 'snippets')],
    extname: '.liquid',
    strictFilters: true,
    strictVariables: false,
    jsTruthy: false,
    dynamicPartials: true,
    relativeReference: false,
  });

  const lookupT = (key) => {
    for (const dict of [locale, fallbackLocale]) {
      let v = dict;
      for (const k of key.split('.')) v = v?.[k];
      if (v !== undefined) return v;
    }
    return undefined;
  };

  // ---- Filtros de Shopify ----
  const f = (name, fn) => engine.registerFilter(name, fn);
  f('t', (key, ...args) => {
    let v = lookupT(key);
    const opts = {};
    for (const a of args) if (Array.isArray(a)) opts[a[0]] = a[1];
    if (v && typeof v === 'object' && 'one' in v) v = opts.count == 1 ? v.one : v.other;
    if (v === undefined) {
      ctx.missingTranslations.add(key);
      return `translation missing: ${key}`;
    }
    return String(v).replace(/\{\{\s*(\w+)\s*\}\}/g, (_, k) => (opts[k] ?? ''));
  });
  f('asset_url', (n) => `/assets/${n}`);
  f('shopify_asset_url', (n) => `/assets/${n}`);
  f('inline_asset_content', (n) => {
    const p = path.join(themeDir, 'assets', n);
    return fs.existsSync(p) ? fs.readFileSync(p, 'utf8') : '';
  });
  f('stylesheet_tag', (u, ...args) => `<link href="${u}" rel="stylesheet" type="text/css" media="all" />`);
  f('script_tag', (u) => `<script src="${u}" type="text/javascript"></script>`);
  f('image_url', (img) => (img && img.src) || '');
  f('image_tag', (url, ...args) => {
    const attrs = args.filter(Array.isArray).map(([k, v]) => `${k}="${v}"`).join(' ');
    return `<img src="${url}" ${attrs}>`;
  });
  f('placeholder_svg_tag', (name, cls) => `<svg class="${cls || ''}" role="img" aria-label="Imagen pendiente" viewBox="0 0 100 60"><rect width="100" height="60" fill="#E9DBCA"/></svg>`);
  f('font_face', (font) => font ? `@font-face{font-family:"${font.family}";font-weight:${font.weight};font-style:${font.style};font-display:swap;src:url("${fontFile(font)}") format("woff2");}` : '');
  f('font_modify', (font, prop, val) => {
    if (!font) return font;
    const nf = new Font(font.handle);
    if (prop === 'weight') nf.weight = val === 'bold' ? '700' : String(val);
    if (prop === 'style') nf.style = val;
    return nf;
  });
  f('font_url', (font) => fontFile(font));
  const toColor = (c) => (c instanceof Color ? c : new Color(String(c)));
  const brightness = (c) => (c.red * 299 + c.green * 587 + c.blue * 114) / 1000;
  f('color_brightness', (c) => brightness(toColor(c)));
  const shift = (c, pct) => {
    c = toColor(c);
    const adj = (v) => Math.max(0, Math.min(255, Math.round(v + 255 * pct / 100)));
    return new Color('#' + [c.red, c.green, c.blue].map(adj).map((v) => v.toString(16).padStart(2, '0')).join(''));
  };
  f('color_lighten', (c, p) => shift(c, p));
  f('color_darken', (c, p) => shift(c, -p));
  f('color_to_rgb', (c) => { c = toColor(c); return `rgb(${c.red}, ${c.green}, ${c.blue})`; });
  const money = (cents) => (Number(cents || 0) / 100).toFixed(2).replace('.', ',') + ' €';
  f('money', money);
  f('money_with_currency', (c) => money(c) + ' EUR');
  f('money_without_currency', (c) => money(c).replace(' €', ''));
  f('money_without_trailing_zeros', money);
  f('money_amount', money);
  f('handleize', (s) => String(s).toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, ''));
  f('handle', (s) => String(s).toLowerCase().replace(/[^a-z0-9]+/g, '-'));
  f('link_to', (text, url) => `<a href="${url}">${text}</a>`);
  f('structured_data', (o) => JSON.stringify({ '@context': 'http://schema.org/', '@type': 'Product', name: o?.title, offers: 'PREVIEW' }));
  f('metafield_tag', (m) => (m && m.value) || '');
  f('time_tag', (d, fmt) => `<time>${d}</time>`);
  f('payment_type_svg_tag', () => '');
  f('payment_terms', () => '');
  f('item_count_for_variant', () => 0);
  f('line_items_for', () => []);
  f('standard_event_data', () => '{}');
  f('external_video_url', (v) => '');
  f('external_video_tag', () => '');
  f('media_tag', () => '');
  f('video_tag', () => '');
  f('unit_price_with_measurement', () => '');
  f('payment_button', () => '');
  f('login_button', () => '');
  f('format_code', (s) => s);
  f('format_address', (s) => s);
  f('document', (s) => s);
  f('this', (s) => s);
  f('within', (u) => u);
  f('default_errors', (e) => '');
  f('highlight', (s) => s);
  f('img_url', (img) => (img && img.src) || '');

  // ---- Etiquetas de Shopify ----
  const rawBlock = (name) => ({
    parse(tagToken, remainTokens) {
      this.tokens = [];
      let tok;
      while ((tok = remainTokens.shift())) {
        if (tok.name === 'end' + name) return;
        this.tokens.push(tok);
      }
      throw new Error(`tag ${tagToken.getText()} not closed`);
    },
    *render() { return ''; },
  });
  engine.registerTag('schema', rawBlock('schema'));
  engine.registerTag('javascript', rawBlock('javascript'));
  engine.registerTag('stylesheet', rawBlock('stylesheet'));
  engine.registerTag('doc', rawBlock('doc'));

  const wrapBlock = (name, open, close) => ({
    parse(tagToken, remainTokens) {
      this.args = tagToken.args;
      this.templates = [];
      const stream = this.liquid.parser.parseStream(remainTokens)
        .on('tag:end' + name, () => stream.stop())
        .on('template', (tpl) => this.templates.push(tpl))
        .on('end', () => { throw new Error(`tag ${tagToken.getText()} not closed`); });
      stream.start();
    },
    *render(context, emitter) {
      const html = yield this.liquid.renderer.renderTemplates(this.templates, context);
      emitter.write(open(this.args, context) + html + close);
    },
  });
  engine.registerTag('style', wrapBlock('style', () => '<style data-shopify>', '</style>'));
  engine.registerTag('paginate', wrapBlock('paginate', () => '', ''));

  engine.registerTag('form', {
    parse(tagToken, remainTokens) {
      this.args = tagToken.args;
      this.templates = [];
      const stream = this.liquid.parser.parseStream(remainTokens)
        .on('tag:endform', () => stream.stop())
        .on('template', (tpl) => this.templates.push(tpl))
        .on('end', () => { throw new Error('form not closed'); });
      stream.start();
    },
    *render(context, emitter) {
      const type = (this.args.match(/^\s*'([^']+)'/) || [])[1] || 'form';
      const attrs = {};
      for (const m of this.args.matchAll(/(\w+):\s*([^,]+)/g)) {
        let v = m[2].trim();
        if (/^['"]/.test(v)) v = v.slice(1, -1);
        else v = yield this.liquid.evalValue(v, context);
        attrs[m[1]] = v;
      }
      context.push({ form: { errors: null, 'posted_successfully?': false, id: attrs.id } });
      const html = yield this.liquid.renderer.renderTemplates(this.templates, context);
      context.pop();
      const action = { contact: '/contact', product: '/cart/add', customer: '/contact#contact_form', localization: '/localization' }[type] || '/' + type;
      const a = Object.entries(attrs).map(([k, v]) => `${k}="${v}"`).join(' ');
      emitter.write(`<form method="post" action="${action}" accept-charset="UTF-8" ${a} data-preview-form="${type}"><input type="hidden" name="form_type" value="${type}" /><input type="hidden" name="utf8" value="✓" />${html}</form>`);
    },
  });

  engine.registerTag('section', {
    parse(tagToken) { this.name = tagToken.args.trim().replace(/^['"]|['"]$/g, ''); },
    *render(context, emitter) {
      emitter.write(yield ctx.renderSection(this.name, this.name, {}, ''));
    },
  });
  engine.registerTag('sections', {
    parse(tagToken) { this.name = tagToken.args.trim().replace(/^['"]|['"]$/g, ''); },
    *render(context, emitter) {
      emitter.write(yield ctx.renderGroup(this.name));
    },
  });
  engine.registerTag('layout', { parse() {}, *render() { return ''; } });
  return engine;
}

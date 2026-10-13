// Demuestra los fallos de la V1 que señala la auditoría V2 (C-03 y C-10) ejecutando
// las mismas pruebas contra el tema del commit 9ab3362. Se espera que la V1 FALLE.
// Uso: node qa/v1-regression.mjs → qa/reports/v1-regression.json
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { execSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { createEngine, readSchema } from '../preview/shim.mjs';

const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const V1 = '9ab3362';
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'v1-'));
execSync(`git -C "${repo}" archive ${V1} theme | tar -x -C "${tmp}"`);
const themeDir = path.join(tmp, 'theme');
const readJSON = (p) => JSON.parse(fs.readFileSync(p, 'utf8'));
const ctx = { missingTranslations: new Set(), errors: [], formOverride: null };
const engine = createEngine({ themeDir, locale: readJSON(path.join(themeDir, 'locales/es.json')), fallbackLocale: readJSON(path.join(themeDir, 'locales/en.default.json')), ctx });
const out = [];

const blank = (await engine.parseAndRender("{% render 'ds-commerce-ready', product: p %}", { p: null }, { globals: { settings: { ds_commerce_enabled: true } } })).trim();
out.push({ caso: 'V1 · ds-commerce-ready con product=blank y comercio activado', resultado: blank, falla_como_dice_la_auditoria: blank === 'true' });
const price = (await engine.parseAndRender("{% render 'price', product: p, placeholder: true %}", { p: null }, { globals: { settings: { ds_commerce_enabled: true } } })).replace(/\s+/g, ' ');
out.push({ caso: 'V1 · consecuencia: precio de ejemplo de Dawn con product=blank', resultado: (price.match(/19,99[^<]*/) || ['(sin precio)'])[0], falla_como_dice_la_auditoria: /19,99/.test(price) });

const src = fs.readFileSync(path.join(themeDir, 'sections/ds-contact.liquid'), 'utf8');
const sch = readSchema(src);
const section = { id: 'c', settings: Object.fromEntries((sch.settings || []).filter((s) => s.id).map((s) => [s.id, s.default ?? null])), blocks: [] };
ctx.formOverride = { name: '"><script>alert(1)</script>', email: 'a', body: '<img src=x onerror=alert(1)>' };
const html = await engine.parseAndRender(src, { section }, { globals: { settings: {}, section } });
out.push({ caso: 'V1 · contacto imprime entrada sin escape', resultado: (html.match(/value=""><script>alert\(1\)<\/script>"|<img src=x onerror=alert\(1\)>/) || ['escapado'])[0], falla_como_dice_la_auditoria: /<script>alert\(1\)<\/script>|<img src=x onerror/.test(html) });

fs.writeFileSync(path.join(repo, 'qa/reports/v1-regression.json'), JSON.stringify(out, null, 2));
console.log(JSON.stringify(out, null, 2));
fs.rmSync(tmp, { recursive: true, force: true });

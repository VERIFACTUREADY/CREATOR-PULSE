// Ejecuta Theme Check (motor oficial de Shopify, gratuito) sobre ../theme
// y escribe un resumen legible. Uso: node qa/theme-check.mjs [salida.json]
import { createRequire } from 'node:module';
import path from 'node:path';
import fs from 'node:fs';
const require = createRequire(import.meta.url);
const { themeCheckRun } = require('@shopify/theme-check-node');

const root = path.resolve(path.dirname(new URL(import.meta.url).pathname), '../../theme');
const { offenses } = await themeCheckRun(root, undefined, () => {});
const sev = ['error', 'warning', 'info'];
const rows = offenses.map((o) => ({
  severity: sev[o.severity] ?? o.severity,
  check: o.check,
  file: o.uri.replace('file://' + root + '/', ''),
  line: (o.start?.line ?? 0) + 1,
  message: o.message,
}));
const count = (s) => rows.filter((r) => r.severity === s).length;
console.log(`Theme Check: ${count('error')} errores, ${count('warning')} avisos, ${count('info')} info`);
for (const r of rows.filter((r) => r.severity !== 'info')) console.log(`${r.severity.toUpperCase()} ${r.check} ${r.file}:${r.line} ${r.message}`);
if (process.argv[2]) fs.writeFileSync(process.argv[2], JSON.stringify(rows, null, 2));
process.exitCode = count('error') ? 1 : 0;

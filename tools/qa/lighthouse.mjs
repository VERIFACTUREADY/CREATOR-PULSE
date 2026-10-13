// Lighthouse (gratuito) en móvil sobre la previsualización local (http://localhost:4173).
// Uso: node qa/lighthouse.mjs → qa/reports/lighthouse-*.html y lighthouse-summary.json
import lighthouse from 'lighthouse';
import * as chromeLauncher from 'chrome-launcher';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const out = path.join(repo, 'qa/reports');
const routes = ['/', '/pages/como-funciona', '/pages/uso-y-seguridad', '/pages/contacto', '/products/dispositivo-bucal-en-evaluacion'];
const chrome = await chromeLauncher.launch({ chromePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome', chromeFlags: ['--headless=new', '--no-sandbox'] });
const summary = {};
for (const r of routes) {
  const res = await lighthouse('http://localhost:4173' + r, { port: chrome.port, output: 'html', logLevel: 'error', onlyCategories: ['performance', 'accessibility', 'best-practices', 'seo'] });
  const c = res.lhr.categories;
  const a = res.lhr.audits;
  summary[r] = {
    performance: Math.round(c.performance.score * 100), accessibility: Math.round(c.accessibility.score * 100),
    bestPractices: Math.round(c['best-practices'].score * 100), seo: Math.round(c.seo.score * 100),
    LCP: a['largest-contentful-paint'].displayValue, CLS: a['cumulative-layout-shift'].displayValue, TBT: a['total-blocking-time'].displayValue,
    failed: Object.values(a).filter((x) => x.score !== null && x.score < 0.9 && x.scoreDisplayMode === 'binary').map((x) => x.id),
  };
  const name = r === '/' ? 'inicio' : r.slice(1).replace(/\//g, '_');
  fs.writeFileSync(path.join(out, `lighthouse-${name}.html`), res.report);
}
await chrome.kill();
fs.writeFileSync(path.join(out, 'lighthouse-summary.json'), JSON.stringify(summary, null, 2));
console.log(JSON.stringify(summary, null, 2));

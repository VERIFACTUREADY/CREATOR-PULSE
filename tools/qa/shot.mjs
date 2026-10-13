// Captura rápida: node qa/shot.mjs <ruta> <ancho> <salida.png> [fullPage]
import { chromium } from 'playwright-core';
const [route = '/', width = '390', out = 'shot.png', full = '1'] = process.argv.slice(2);
const browser = await chromium.launch({ executablePath: process.env.CHROMIUM || '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
const page = await browser.newPage({ viewport: { width: Number(width), height: 900 } });
const errs = [];
page.on('console', (m) => m.type() === 'error' && errs.push(m.text()));
await page.goto('http://localhost:4173' + route, { waitUntil: 'networkidle' });
await page.screenshot({ path: out, fullPage: full === '1' });
if (errs.length) console.log('console errors:', errs.slice(0, 5).join(' | '));
await browser.close();

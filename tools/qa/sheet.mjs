// Captura varias rutas a un ancho y las guarda: node qa/sheet.mjs <ancho> <dir> ruta1 ruta2 ...
import { chromium } from 'playwright-core';
import path from 'node:path';
const [width, dir, ...routes] = process.argv.slice(2);
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
const page = await browser.newPage({ viewport: { width: Number(width), height: 900 } });
for (const r of routes) {
  await page.goto('http://localhost:4173' + r, { waitUntil: 'networkidle' });
  const name = (r === '/' ? 'inicio' : r.replace(/^\/|\/$/g, '').replace(/\//g, '_')) + `-${width}.png`;
  await page.screenshot({ path: path.join(dir, name), fullPage: true });
  console.log(name);
}
await browser.close();

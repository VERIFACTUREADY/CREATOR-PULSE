# Cómo reproducir el QA (repositorio completo)

Requisitos: **Node 22** (con `npm`), **Python 3.11+** con `openpyxl`, **LibreOffice** (`soffice`, para recalcular la hoja) y **Chromium**. Si Playwright no encuentra Chromium, ajustar la ruta `CHROME` en `tools/qa/*.mjs`. Las dependencias están fijadas en `tools/package-lock.json`.

```bash
cd tools
npm ci                                            # dependencias exactas del lockfile
node qa/theme-check.mjs ../qa/reports/theme-check.json   # Theme Check oficial (@shopify/theme-check-node)
node qa/gate-tests.mjs                             # compuerta, dos productos, mercados, marca, país, escape (62 casos)
node qa/purchase-routes-tests.mjs                  # rutas de compra alternativas de Dawn con productos A/B (48 casos)
node qa/v1-regression.mjs                          # demuestra los fallos de V1 (commit 9ab3362; requiere historial git)
node preview/build.mjs && node preview/serve.mjs & # previsualización en http://localhost:4173 (inglés, USD, PREVIEW_COMERCIAL)
node qa/run-qa.mjs                                 # 6 estados + marca sustituida, 18 rutas × 4 anchos, axe, claims EN/ES, mezcla de idiomas, primera pantalla
node qa/lighthouse.mjs                             # Lighthouse móvil (6 páginas)
node qa/prelaunch-check.mjs [URL] [--expect-indexable]   # control previo a LIVE
node qa/v2-shots.mjs                               # capturas por hallazgo V2 → qa/screenshots/v2.1/
node qa/v22-shots.mjs                              # capturas de las correcciones V2.2 → qa/screenshots/v2.2/
cd ..
python3 tools/finance/build_economia_us.py         # regenera la hoja (vacía de datos reales)
python3 tools/qa/excel_tests.py                    # 27 pruebas de la hoja (recalcula con LibreOffice)
python3 tools/qa/v2-regression-excel.py            # demuestra el fallo de «Test de precio» en la hoja V2 archivada
python3 tools/content/build_us_templates.py        # regenera las plantillas en inglés (sobrescribe las ediciones locales)
```

Los resultados se escriben en `qa/reports/`. Las cifras de `docs/10_QA_LANZAMIENTO.md` corresponden al commit de la entrega.

**Límites:** el previsualizador imita Shopify con liquidjs; no es Shopify. El checkout, los emails, la Section Rendering API (cambio de variante), los impuestos y el control de acceso del servidor solo se verifican en una tienda real (`docs/V22_INSTALACION_Y_E2E_SHOPIFY.md`).

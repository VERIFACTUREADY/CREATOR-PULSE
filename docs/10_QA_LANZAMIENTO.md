# 10 · QA del prototipo

## V2.1 · Resultados (13/10/2026, EE. UU., inglés, USD, PREVIEW_COMERCIAL)

| Prueba | Resultado |
|---|---|
| Theme Check | 0 errores (9 avisos heredados de Dawn) |
| `gate-tests.mjs` | 47/47 |
| Estados (`run-qa.mjs`) | 12/12 |
| 18 rutas × 375/390/768/1440 (72 combinaciones) | 0 desbordamientos · 1 H1 · 0 enlaces rotos · 0 errores de consola · 0 objetivos < 44 px |
| axe WCAG 2.2 AA | 0 violaciones (PREVIEW 390/1440 y PROTOTIPO 390) |
| Primera pantalla (título + precio + CTA) | 8/8: portada, 2 landings y ficha a 390×844 y 375×667 |
| Claims prohibidos (ES + EN/FTC) · español en la tienda inglesa · rastreadores | 0 · 0 · 0 |
| Lighthouse móvil (6 páginas) | Rendimiento 91–95 · Accesibilidad 100 · Buenas prácticas 96 · SEO 63 (noindex intencionado) · CLS 0 |
| `excel_tests.py` (hoja USD) | 13/13 · `v2-regression-excel.py`: fallo V2 reproducido |
| `prelaunch-check.mjs` | NO APTO (181 incidencias; +16 con `--expect-indexable`) |

Sin verificar: todo lo que requiere Shopify real (`V21_PLAN_PRUEBAS_SHOPIFY.md`).

---


## V2 · Resultados (13/10/2026, vista comercial PREVIEW_COMERCIAL)

| Prueba | Resultado |
|---|---|
| Theme Check | **0 errores** (9 avisos heredados de Dawn) |
| `gate-tests.mjs`: compuerta y escape | **47/47** (blank, 16 campos, estados, precio, tachado, compra y 4 cargas de inyección) |
| `v1-regression.mjs` | La V1 reproduce los 3 fallos de la auditoría (compuerta `true` con blank, «19,99 €», entrada sin escapar) |
| `excel_tests.py` | **7/7** (con 1/5 partidas: V2 «DATOS INCOMPLETOS»; la V1 habría dado 13,04 €) |
| Estados de la tienda (`run-qa.mjs`) | **12/12** (PROTOTIPO, PREVIEW, LIVE sin frase, LIVE incompleto y LIVE completo) |
| 17 rutas × 375/390/768/1440 (68 combinaciones) | 0 desbordamientos · 1 H1 por página · 0 enlaces rotos · 0 errores de consola · 0 objetivos < 44 px · cuerpo 16,5 px |
| axe WCAG 2.2 AA | **0 violaciones** en PREVIEW (390 y 1440) y en PROTOTIPO (390). Corregido el campo «Cantidad» de Dawn sin nombre accesible |
| Primera pantalla (título + precio + CTA) | Portada y landings: ✅ a 390×844 y 375×667 · Ficha: ✅ a 390×844; a 375×667 la CTA queda justo debajo (por el selector de cantidad) |
| Lighthouse móvil (portada, ficha, 2 landings, FAQ, contacto) | Rendimiento 92–93 · Accesibilidad 100 · Buenas prácticas 96* · SEO 63* · CLS 0 |
| Claims prohibidos / rastreadores | 0 / 0 |
| `prelaunch-check.mjs` | Un LIVE local con datos FICTICIOS da **«NO APTO»** (165 incidencias: valores ficticios y [corchetes] legales). El control funciona |

\* SEO 63 por el `noindex` intencionado. Buenas prácticas 96 porque `cdn.shopify.com` no es accesible en local.

**Sin verificar (requiere Shopify real):** checkout, emails, cambio de variante por Section Rendering API, iOS Safari y Chrome Android reales, lector de pantalla. Guion en `V2_PLAN_SHOPIFY_Y_MEDICION.md`.

---

## V1 (histórico)


> **Alcance:** QA **local**, sobre una previsualización del tema renderizada con liquidjs (sin tienda Shopify ni credenciales, DP-18). Superar este QA **no** significa que la tienda esté lista: falta repetirlo dentro de Shopify y pasar una **auditoría externa**.

## Cómo reproducirlo

```bash
cd tools && npm install
node qa/theme-check.mjs ../qa/reports/theme-check.json   # Theme Check oficial de Shopify
node preview/build.mjs && node preview/serve.mjs &        # previsualización en http://localhost:4173
node qa/run-qa.mjs                                        # batería completa → qa/reports/qa-results.json + qa/screenshots
node qa/lighthouse.mjs                                    # Lighthouse móvil → qa/reports/lighthouse-*.html
```

## Resultados

### 1. Theme Check (motor oficial `@shopify/theme-check-node`)

| | Dawn 16.0.0 original | Tema del prototipo |
|---|---:|---:|
| Errores | 0 | **0** |
| Avisos | 9 | **9** (los mismos que trae Dawn de serie: variables en camelCase, un snippet huérfano, etc.) |

Durante el desarrollo detectó 2 errores (nombres de sección de más de 25 caracteres). Ya están **corregidos**.

### 2. Compuerta de venta: 9/9 ✅

| Prueba | Resultado |
|---|:-:|
| Prototipo (comercio desactivado): ningún formulario `/cart/add` en las 15 rutas | ✅ |
| Sin botón de checkout | ✅ |
| Sin icono de carrito | ✅ |
| Sin precios | ✅ |
| Sin JSON-LD `Product`/`Offer` | ✅ |
| `noindex` en todas las páginas | ✅ |
| Aviso «Prototipo privado» en todas las páginas | ✅ |
| Comercio activado + metacampos vacíos → la ficha **sigue sin compra** | ✅ |
| Comercio activado + metacampos completos → la ficha **sí** muestra compra (la compuerta funciona en los dos sentidos) | ✅ |

**Fallos encontrados y corregidos:** (1) el formulario de pago a plazos de Dawn (`product-form-installment`) seguía enviando a `/cart/add` con el comercio apagado. Ahora pasa por la compuerta. (2) El carrito mostraba «Total estimado 0,00 €» y «Seguir comprando». Ahora las secciones del carrito no se renderizan sin GO.

### 3. Responsive, semántica y enlaces: 15 rutas × 4 anchos (375, 390, 768, 1440) = 60 comprobaciones

| Criterio | Resultado |
|---|---|
| Desbordamiento horizontal | **0** |
| Exactamente un H1 por página | **60/60** (corregido: el logotipo era un H1 en la portada y el carrito tenía 2 o 0 H1) |
| Imágenes sin `alt` | **0** |
| Enlaces internos rotos | **0** (corregido: el 404 enlazaba a `/collections/all`) |
| Errores de consola propios del tema | **0** |
| Tamaño mínimo del texto de cuerpo | **16,5 px** (objetivo: 16–18 px) |
| Controles con objetivo táctil < 44 px (sin contar enlaces dentro del texto) | **0** (corregidos los enlaces del pie de Dawn) |

### 4. Accesibilidad

| Prueba | Resultado |
|---|---|
| axe-core 4.x (WCAG 2.0/2.1/2.2 A y AA), 15 rutas a 390 y 1440 px | **0 violaciones** (corregido: número de los pasos en petróleo sobre arena translúcida, 4,4:1 → ahora noche) |
| Lighthouse Accesibilidad (móvil) | **100** en las 5 páginas auditadas |
| Primer Tab = «Ir directamente al contenido» | ✅ |
| Foco visible (contorno ≥ 2 px) en los 12 primeros elementos enfocables | ✅ |
| FAQ abre con Enter (`<details>` nativo) | ✅ |
| Menú móvil operable, con 4 entradas | ✅ (`qa/screenshots/menu-movil-390.png`) |
| Contraste de la paleta | Noche/marfil 13,4:1 · petróleo/marfil 4,9:1 · blanco/petróleo 5,3:1. El petróleo **no** se usa como texto sobre salvia (4,1:1) ni sobre arena (3,9:1) |
| `prefers-reduced-motion` | Respetado; las animaciones de aparición están desactivadas |

Pendiente: prueba con lector de pantalla real (NVDA/VoiceOver) y zoom al 200 % hecha por una persona.

### 5. Lighthouse móvil (previsualización local)

| Página | Rendimiento | Accesibilidad | Buenas prácticas | SEO | LCP | CLS | TBT |
|---|---:|---:|---:|---:|---:|---:|---:|
| Inicio | 95 | 100 | 96 | 63* | 2,6 s | 0 | 0 ms |
| Cómo funciona | 95 | 100 | 96 | 63* | 2,6 s | 0 | 0 ms |
| Uso y seguridad | 93 | 100 | 96 | 63* | 3,0 s | 0 | 0 ms |
| Contacto | 96 | 100 | 96 | 63* | 2,4 s | 0 | 0 ms |
| Ficha en evaluación | 92 | 100 | 96 | 63* | 2,9 s | 0 | 0 ms |

\* **SEO 63 es intencionado:** el único fallo es `is-crawlable`, provocado por el `noindex` del prototipo. «Buenas prácticas 96» se debe a `errors-in-console`: el script de Shopify `standard-events.js` (cdn.shopify.com) no se puede descargar en local. Las cifras reales hay que medirlas dentro de Shopify.

### 6. Contenido y cumplimiento

| Prueba | Resultado |
|---|---|
| Claims prohibidos (14 patrones: cura, apnea, corazón, mandíbula, «sin efectos secundarios», porcentajes, avales, garantías, rendimiento o humor, bruxismo, estrellas, urgencia, origen, plazos) en el HTML visible y en las plantillas | **0** (1 falso positivo documentado y permitido: la pregunta «¿Una férula sirve para todo el mundo?», cuya respuesta es «No») |
| Rastreadores (Meta, Google Ads/GA, TikTok, Hotjar, Clarity, LinkedIn) | **0** |
| Formularios que piden datos de salud | 0. El contacto avisa de forma explícita |
| Reseñas, estrellas, contadores o urgencia | 0 |
| Fotos de terceros sin licencia | 0. Solo hay una ilustración SVG original |

### 7. Capturas

`qa/screenshots/`: 60 capturas de página completa (15 rutas × 375/390/768/1440), más `menu-movil-390.png` y `foco-teclado-1440.png`.

## Limitaciones conocidas de este QA

1. **No es Shopify.** El previsualizador imita los objetos, filtros y etiquetas que usa el tema. Hay diferencias posibles en `content_for_header`, en el banner de cookies nativo, en las imágenes subidas, en los formularios reales, en la búsqueda, en las traducciones del checkout y en los emails.
2. **Ajustes `url` con ancla** (p. ej. `/pages/uso-y-seguridad#cuando-consultar`): hay que comprobar al subir el tema que el editor los acepta. Si no, sustituirlos por la URL sin ancla.
3. No se ha probado el **envío real** del formulario de contacto, el **checkout** (no existe) ni los **emails transaccionales**.
4. No hay **test con usuarios reales** (DP-20).
5. Ninguna fuente externa se ha podido abrir desde este entorno (proxy restringido).

## Pendiente antes del lanzamiento (resumen)

Repetir el QA en una tienda de desarrollo con contraseña. Prueba con lector de pantalla. Test con 5 personas. Revisión sanitaria y jurídica de los textos. Banner de cookies nativo. Checkout de prueba sin cargos (solo tras GO). **Auditoría externa.**

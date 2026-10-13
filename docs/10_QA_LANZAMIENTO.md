# 10 · QA del prototipo (13/10/2026)

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

# V2 · Registro de cambios por hallazgo (auditoría CRO / UX / Shopify, 13/10/2026)

**Alcance acordado:** el titular declara cerrada la comprobación sanitaria. Esta ronda no reabre ese análisis: los metacampos `compliance.*` solo se tratan como datos de software que la ficha necesita. **No se ha inventado ningún precio, plazo, foto, reseña ni beneficio.** Cada dato que falta aparece como **⟦PENDIENTE: …⟧**, un marcador rayado e inconfundible con el atributo `data-ds-placeholder`, y bloquea LIVE.

**Estado entregado:** tema **sin publicar** en **PREVIEW_COMERCIAL** (venta visible, compra desactivada). LIVE no está activado ni se puede activar por accidente.

**Pruebas originales** (`qa/reports/`): `gate-tests.json` · `v1-regression.json` · `excel-tests.json` · `qa-results.json` · `lighthouse-*.html` · `prelaunch-check.json` · `theme-check.json`.
**Capturas móviles V2** (`qa/screenshots/v2/`, 390×844).

---

## P0

### C-03 · Compuerta: `product = blank` devolvía `true` y faltaba el modo de vista previa comercial
| | |
|---|---|
| **Archivos y líneas** | `theme/snippets/ds-commerce-ready.liquid:12` (deniega por defecto) · `snippets/ds-mode.liquid:4` (estado efectivo; LIVE exige la frase) · `snippets/ds-live-blockers.liquid` (datos globales) · `snippets/ds-product-missing.liquid:8` (ficha completa; vacío = «producto») · `snippets/ds-offer-visible.liquid` (oferta visible ≠ compra) · `snippets/price.liquid:19,22` · `snippets/buy-buttons.liquid:19` → `snippets/ds-preview-cta.liquid` · `sections/main-product.liquid:159` (pago a plazos) · `snippets/meta-tags.liquid:31` (og:price) · `sections/header.liquid:304` (icono de carrito) · `layout/theme.liquid:335,409` (cajón de carrito) · `sections/main-cart-items.liquid:3`, `main-cart-footer.liquid:3` · `snippets/card-product.liquid:25` (añadir rápido) · `config/settings_schema.json:23,43` (`ds_store_mode`, `ds_live_confirmation`) · `snippets/ds-prototype-banner.liquid` (aviso por estado) |
| **Explicación** | Antes había un único interruptor `ds_commerce_enabled`. Con él activado y sin producto (por ejemplo, la sección «Producto destacado» vacía), la compuerta devolvía `true` y Dawn pintaba su precio de ejemplo **19,99 €**. Ahora hay **tres estados**: **PROTOTIPO** (sin oferta) · **PREVIEW_COMERCIAL** (oferta, precio confirmado o ⟦PENDIENTE⟧, CTA visible pero **sin formulario de pedido**) · **LIVE** (solo con la frase exacta `VENTA REAL AUTORIZADA`, todos los datos del titular y de la oferta, y la ficha completa: 11 campos `compliance`, 5 `commercial`, `price_confirmed`, fotos reales y producto disponible). Si falta algo, LIVE degrada a PREVIEW y muestra un aviso rojo con la lista de lo que falta. El precio tachado solo aparece con `commercial.compare_at_verified`, para evitar descuentos sin historial. |
| **Prueba** | `node tools/qa/gate-tests.mjs`: 47 casos (blank, producto sin cada uno de los 16 campos, agotado, sin fotos, precio sin confirmar, los 3 estados, frase en minúsculas, falta de datos globales, efecto en `price` y `buy-buttons`). `node tools/qa/v1-regression.mjs` ejecuta lo mismo sobre la V1 (commit `9ab3362`). `run-qa.mjs`: 12 comprobaciones de estado sobre 17 rutas. |
| **Resultado** | **47/47 OK.** La regresión confirma el fallo en V1 (`true` con blank y «19,99 €»). Estados **12/12 OK**: PREVIEW no tiene `/cart/add`, checkout, icono de carrito, JSON-LD ni og:price. LIVE sin frase o con datos incompletos tampoco permite comprar. Solo LIVE completo (con datos ficticios de prueba) muestra el formulario. |
| **Capturas** | `C-03_estado-PROTOTIPO_ficha.png` · `C-03_estado-PREVIEW_cta-desactivada.png` · `C-03_estado-LIVE-sin-confirmar_bloqueado.png` · `C-03_estado-LIVE-completo-DATOS-FICTICIOS_compra.png` |
| **Límite** | La compuerta Liquid **no sustituye** a la configuración de Shopify: tema sin publicar, contraseña y pagos desactivados siguen siendo la protección real. Cualquiera que conozca la URL `/cart/add` de un producto activo podría enviarle una petición. |

### C-04 · La hoja trataba costes incompletos como totales
| | |
|---|---|
| **Archivos y líneas** | `docs/05_ECONOMIA_UNITARIA.xlsx` → hoja `Escenarios`, fila 13 (estado del coste), filas 14 y 21–24 · generador reproducible en `tools/finance/build_economia.py` |
| **Explicación** | La V1 usaba `IF(SUM(G6:G10)>0,SUM(G6:G10),G5)`: con 1 de 5 partidas tomaba esa partida como coste total. Ahora **1–4 partidas = «DATOS INCOMPLETOS»** y no se calcula margen. La columna REAL no admite coste agregado. Un 0 escrito es dato válido y una celda vacía significa «no lo sé». Ningún veredicto dice «rentable». Añadido: devoluciones, coste de contenido o colaboradores por venta, comisión real opcional, **test de precio 24,90 / 29,90 / 34,90 €**, **capital circulante** (días hasta liquidar) y **panel semanal** de embudo (conversión, ATC, checkout, AOV, CAC, contribución). |
| **Prueba** | `python3 tools/qa/excel_tests.py`: recalcula con LibreOffice 5 casos. |
| **Resultado** | **7/7 OK.** Las hipótesis reproducen 0,56 / 7,04 / 11,54 / 11,03 / 7,14 €. Con REAL al 1/5, la V2 devuelve «DATOS INCOMPLETOS» donde **la V1 habría dado 13,04 €**. REAL completo calcula 7,04 €. 177 fórmulas, 0 errores. |
| **Captura** | No aplica (hoja de cálculo). Ver `qa/reports/excel-tests.json`. |

### C-01 · La portada informaba pero no dirigía a comprar
| | |
|---|---|
| **Archivos y líneas** | Nueva `theme/sections/ds-product-hero.liquid` (CTA en la línea 58) · `templates/index.json` (secciones `phero`, `strip`, `how`, `includes`, `faq_c`, `closing_c`) · `snippets/ds-visible.liquid:11` · `assets/descanso.css` (hero móvil y orden título → precio → CTA) |
| **Explicación** | En PREVIEW/LIVE la portada abre con el **producto**: foto real o hueco «FOTO PENDIENTE», nombre, beneficio aprobado (`commercial.short_benefit`), precio confirmado y **una sola CTA primaria, «Ver el producto»**, con «Cómo funciona» como enlace secundario. Después: problema en 2–3 líneas, cómo se usa en 3 pasos, qué incluye, envío/devoluciones/atención/pago, FAQ de objeciones y CTA final. **La variante informativa se conserva** y solo se ve en PROTOTIPO. Sin carrusel. El subtítulo «Conoce nuestro dispositivo bucal y sus características, sin complicaciones» es la propuesta neutra de la auditoría (pendiente de aprobación, M-07). |
| **Prueba** | `run-qa.mjs`, prueba de primera pantalla (título, precio y CTA visibles sin scroll) a 390×844 y 375×667, más el resto de la batería. |
| **Resultado** | Portada y las dos landings: **visibles a 390×844 y a 375×667.** |
| **Capturas** | `C-01_portada-comercial-PREVIEW.png` (después) · `C-01_antes-portada-informativa-PROTOTIPO.png` (antes) · `qa/screenshots/primera-pantalla_inicio-390x844.png` |

### C-02 · La ficha no era una herramienta de venta
| | |
|---|---|
| **Archivos y líneas** | `templates/product.json` · `sections/main-product.liquid:82` (hueco de foto y dos columnas), `:98` (bloque `ds_benefit`), bloques `ds_offer_points` y `ds_prototype_label` · nueva `sections/ds-product-module.liquid:19` · `sections/ds-product-details.liquid:22` (sin duplicados en modo comercial) · `snippets/ds-offer-points.liquid` |
| **Explicación** | Orden: galería (o hueco) > título > beneficio aprobado > precio > variantes > cantidad > CTA > envío/devoluciones/atención/pago > descripción. Después: **qué es · cómo se usa paso a paso · para quién · qué incluye · cuidados**, todo desde `commercial.*`, seguido de ficha técnica y precauciones (abiertas por defecto), FAQ de compra y ayuda. La etiqueta «Producto en evaluación documental» solo aparece en PROTOTIPO. Variantes: el selector y el cambio de precio, imagen y disponibilidad son los nativos de Dawn (sin cambios). |
| **Prueba** | Gate tests (precio, compra y tachado), axe y Lighthouse sobre la ficha. |
| **Resultado** | axe: 0 violaciones (corregido además un fallo **heredado de Dawn**: el campo «Cantidad» no tenía nombre accesible, `main-product.liquid:300`). Lighthouse ficha: rendimiento 92, accesibilidad 100. |
| **Captura** | `C-02_ficha-comercial-PREVIEW_completa.png` |
| **Pendiente** | Con 0, 1 y varias variantes en Shopify real (el cambio de variante usa la Section Rendering API de Shopify, que no se puede reproducir en local). A 375×667 la CTA de la ficha queda justo debajo de la primera pantalla por el selector de cantidad. Barra CTA fija en móvil: propuesta P2, con test A/B. |

## P1

### C-05 · Dos audiencias, un relato por landing
`templates/page.landing-ronquidos.json` («¿Te preocupan tus ronquidos?») y `templates/page.landing-pareja.json` («Cuando uno ronca, a veces son dos los que no duermen»). Las dos llevan a **la misma ficha**, sin culpabilizar ni prometer resultados. Textos pendientes de aprobación (M-08, M-09). UTM propuestas en `V2_PLAN_SHOPIFY_Y_MEDICION.md`. **Capturas:** `C-05_landing-ronquidos.png`, `C-05_landing-pareja.png`.

### C-06 · Activos comerciales
`snippets/ds-photo-placeholder.liquid:8`: la ilustración SVG ya no ocupa el lugar de la foto de producto. Hay un hueco **«⟦FOTO PENDIENTE · NO PUBLICABLE⟧»** que bloquea LIVE (`ds-product-missing` exige fotos). Lista de fotos necesarias en `V2_PENDIENTES_Y_DATOS.md`. **No se han creado fotos, testimonios ni sellos.**

### C-07 · Transparencia operativa coherente
Ajustes **Oferta** (`settings_schema.json`: envío, devoluciones, atención, pago) como **fuente única**. Se muestran en el hero, la ficha (`ds-offer-points`), la franja `ds-offer-strip.liquid:10`, los resúmenes de envíos y devoluciones, y la FAQ mediante `[[ENVIO]]`, `[[DEVOLUCIONES]]`, `[[ATENCION]]` y `[[PAGO]]` (`snippets/ds-offer-tokens.liquid:26`, `sections/ds-faq.liquid:32`). Los textos «Todavía no vendemos / en evaluación / no aceptamos pedidos» tienen visibilidad **Solo PROTOTIPO** a nivel de sección o bloque. **Prueba:** `run-qa` «PREVIEW: sin textos de prototipo contradictorios» → OK en las 17 rutas. **Capturas:** `C-07_faq-con-datos-de-oferta.png`, `C-07_envios-resumen.png`.

### C-08 · Checkout real
**No ejecutado: no hay acceso a ninguna tienda Shopify.** He dejado un plan paso a paso (Bogus Gateway o modo de prueba, iOS Safari, Chrome Android, carrito vacío o agotado, descuento, email) en `V2_PLAN_SHOPIFY_Y_MEDICION.md`, y `prelaunch-check.mjs` admite la URL real de la tienda.

### C-09 · Telemetría
Sin píxeles. Hoja «Panel semanal» con los denominadores definidos. Plan de eventos nativos de Shopify y UTMs en `V2_PLAN_SHOPIFY_Y_MEDICION.md`.

### C-10 · Escape del formulario de contacto
| | |
|---|---|
| **Archivos y líneas** | `sections/ds-contact.liquid:49,53,68` (`form.name`, `form.email`, `form.body` → `| escape`) · también el formulario original de Dawn `sections/contact-form.liquid:62,76,110,123` |
| **Prueba** | `gate-tests.mjs`, 4 cargas: `"><script>…`, `' onmouseover=…`, `<img onerror>`, y unicode con `&amp;` y `<b>`. |
| **Resultado** | **4/4 escapadas.** La regresión sobre la V1 confirma que antes se imprimía `"><script>alert(1)</script>` sin escapar. |
| **Captura** | `C-10_contacto.png` (sin cambio visual) |

## P2 (parcial)

- **C-11 SEO:** `Product`/`Offer` y `og:price` solo con compra operativa. FAQ: corregido el orden de títulos (grupos en H2 cuando la sección no tiene título; Lighthouse «heading-order»). Títulos y descripciones de las 2 landings y de la ficha en `V2_PLAN_SHOPIFY_Y_MEDICION.md`. `noindex` se mantiene.
- **C-12 Separación del proyecto:** el trabajo vive en una rama huérfana sin historia común con creator-pulse. `README_COMERCIAL.md` documenta oferta, estados y assets, y el ZIP se genera desde el commit indicado. **Mover a un repositorio privado propio necesita tu confirmación** (ver el resumen final).

## Otros cambios
- `snippets/ds-pending.liquid:3,9`: marcador rayado ⟦…⟧. En LIVE se pinta como error rojo.
- `snippets/ds-review-badge.liquid`: las etiquetas «pendiente de revisión sanitaria» solo se ven en PROTOTIPO.
- Producto: identificador `dispositivo-bucal` (antes `…-en-evaluacion`). Menú: «El producto» → ficha.
- Previsualizador: `--mode`, `--confirm-live`, `--complete-globals`, `--complete-metafields` (estos dos últimos usan valores **FICTICIOS DE PRUEBA** que nunca se copian al tema).

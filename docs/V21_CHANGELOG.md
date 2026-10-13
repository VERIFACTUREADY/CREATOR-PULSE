# V2.1 · Registro de cambios (mercado EE. UU. + revisión independiente V2)

**Entrega:** tema **sin publicar** en **PREVIEW_COMERCIAL**, en inglés de EE. UU. y USD. LIVE no está activado y los pagos no se tocan. No se han inventado fotos, precios, características, resultados ni plazos: todo lo que falta aparece como **⟦PENDING⟧** y bloquea LIVE.
**Datos que necesito:** `V21_DATOS_NECESARIOS.md` · **Requisitos de EE. UU.:** `V21_GO_NO_GO_EEUU.md` · **Pruebas en Shopify real:** `V21_PLAN_PRUEBAS_SHOPIFY.md` · **Cómo reproducir el QA:** `QA_REPRODUCIR.md`.

## Hallazgos de la revisión independiente

| # | Prioridad | Hallazgo | Qué se ha hecho | Archivos | Prueba → resultado |
|---|---|---|---|---|---|
| 1 | P0 | Migrar de España a EE. UU. | Todo el texto visible en **inglés de EE. UU.**: portada, ficha, 2 landings, How it works, Use & safety, FAQ, About, Contact, The product y legales de EE. UU. (Shipping con la regla de pedidos por correo de la FTC, Returns, Privacy con CCPA/CPRA, Terms, Company information, Accessibility). Precios en **USD** (formato `$`), sin IVA, con *sales tax* en el checkout. Los textos en español se conservan como borrador en `drafts/es/`, **fuera del tema**. Los marcadores pendientes, la compuerta y los avisos también están en inglés | `tools/content/build_us_templates.py` (genera `theme/templates/*.json`) · `theme/locales/en.default.json` · enlaces fijos en `snippets/ds-offer-points.liquid:20`, `sections/ds-product-details.liquid:60`, `sections/ds-contact.liquid:74` · `snippets/ds-product-missing.liquid:14`, `snippets/ds-live-blockers.liquid:8` | `run-qa`: **0 páginas con español** en PREVIEW y PROTOTIPO (detector nuevo); claims prohibidos en inglés y español: **0** |
| 2 | P0 | Entorno Shopify real y protección de ventas | **No ejecutable sin acceso.** Plan paso a paso que incluye la petición directa `POST /cart/add`, producto en *Draft*, impuestos, emails y dispositivos reales. Se mantiene explícito que la compuerta Liquid **no** es control de acceso | `V21_PLAN_PRUEBAS_SHOPIFY.md` | Pendiente de acceso (dato 22) |
| 3 | P0 | Datos y activos reales | Sin rellenar nada con valores ficticios. Lista concisa de datos | `V21_DATOS_NECESARIOS.md` | `prelaunch-check`: «NO APTO» (181 incidencias) |
| 4 | P1 | «Test de precio» omitía devoluciones, contenido y comisión real | Hoja rehecha para EE. UU. La hoja «Costes variables» tiene 12 partidas obligatorias y 2 de comisión real opcionales; «Test de precio» descuenta **todas** y usa la comisión real si existe. Sin IVA. Celdas de datos **vacías** (nada inventado). Los precios de prueba de 24,99, 29,99 y 34,99 $ son editables. Hoja de España archivada | `tools/finance/build_economia_us.py` → `docs/05_ECONOMIA_UNITARIA.xlsx` · archivo: `docs/archive/05_ECONOMIA_UNITARIA_ES_V2.xlsx` | `excel_tests.py` **13/13**: con devoluciones del 5 % al 10 % el margen baja exactamente 0,30 $; con contenido de 0 a 2 $ baja exactamente 2,00 $; la comisión real sustituye al supuesto. `v2-regression-excel.py` confirma el fallo en V2 (7,04 en los tres casos). 135 fórmulas, 0 errores |
| 5 | P1 | `noindex` podía seguir activo en LIVE | Aviso visible **solo en el editor de temas** si LIVE convive con `noindex`. Nueva opción `--expect-indexable` en `prelaunch-check`, que lo convierte en incidencia bloqueante. `noindex` sigue activo en el prototipo | `snippets/ds-prototype-banner.liquid:31` · `tools/qa/prelaunch-check.mjs` | Con `--expect-indexable`: +16 incidencias (una por página) → el control funciona |
| 6 | P1 | QA no reproducible con los adjuntos | Se entrega el **ZIP del repositorio completo** (scripts, `package-lock.json`, informes, capturas y documentación) y una guía de comandos | `dist/repo-completo-v2.1.zip` · `docs/QA_REPRODUCIR.md` | — |
| 7 | P1 | Hero con producto inexistente | Si el selector no encuentra el producto: **botón desactivado y ⟦PENDING: select the product in the theme editor⟧**, sin enlace muerto. Los módulos sin destino no muestran enlace. Producto con el identificador `adjustable-mouthpiece` | `sections/ds-product-hero.liquid:65` · `sections/ds-product-module.liquid:68` | `run-qa`: 0 enlaces rotos |
| 8 | P2 | CTA de la ficha a 375×667 | Ficha más compacta en móvil (título, beneficio, precio y cantidad), **sin barra fija** | `theme/assets/descanso.css:661` | Primera pantalla: **8/8 combinaciones OK** (antes la ficha a 375×667 fallaba) |
| 9 | P2 | Naming | Marca **parametrizada**: un solo ajuste («Nombre de marca», por defecto VINCIRENA) o el nombre de la tienda; casilla «Marca confirmada»; la vista previa avisa de que el nombre es provisional. No he comprado dominios ni registrado nada | `snippets/ds-brand.liquid:6` · `config/settings_schema.json:19` · `sections/header.liquid:209` · `snippets/ds-prototype-banner.liquid:23` | Visible en las capturas |
| 10 | P2 | Economía recurrente | Sin LTV ni suscripción: la hoja se basa en el margen del primer pedido (está en la Leyenda) | `docs/05_ECONOMIA_UNITARIA.xlsx` (Leyenda) | — |

## Cambio de marco regulatorio (aviso, no reapertura)
La verificación sanitaria que el titular dio por cerrada era **europea**. En EE. UU. aplican la FDA (los dispositivos intraorales antirronquidos suelen ser Clase II y requerir 510(k), también para venta sin receta) y la FTC (evidencia de los claims, reseñas, envíos). Lo detallo en `V21_GO_NO_GO_EEUU.md` como **bloqueante para LIVE**. Desde este entorno no he podido contrastar las fuentes oficiales, así que debe validarlo un asesor de EE. UU.

## Qué se ha conservado sin cambios
Diseño (paleta, Lato, componentes), lectura clara, los tres estados y su compuerta (47/47 pruebas), las dos landings por audiencia, la fuente única de la oferta, el escape del contacto y la accesibilidad.

## Pruebas de esta entrega (`qa/reports/`)
| Prueba | Resultado |
|---|---|
| Theme Check | 0 errores (9 avisos heredados de Dawn) |
| `gate-tests.mjs` | 47/47 (precios en USD) |
| `run-qa.mjs` | Estados 12/12 · 18 rutas × 4 anchos = 72 combinaciones: 0 desbordamientos, 1 H1 por página, 0 enlaces rotos, 0 errores de consola, 0 objetivos < 44 px · axe 0 (PREVIEW y PROTOTIPO) · claims 0 · español 0 · rastreadores 0 · primera pantalla 8/8 |
| Lighthouse móvil (6 páginas) | Rendimiento 91–95 · Accesibilidad 100 · Buenas prácticas 96* · SEO 63* · CLS 0 |
| `excel_tests.py` / `v2-regression-excel.py` | 13/13 / fallo V2 reproducido |
| `prelaunch-check.mjs` | NO APTO (correcto: faltan datos reales) |

\* SEO 63 por el `noindex` intencionado. Buenas prácticas 96 porque `cdn.shopify.com` no es accesible desde el entorno local.

**Capturas móviles V2.1:** `qa/screenshots/v2.1/` (12) y `qa/screenshots/` (78: 72 de página completa, 4 de primera pantalla, menú móvil y foco). Las capturas V2 en español se conservan en `qa/screenshots/v2/`.

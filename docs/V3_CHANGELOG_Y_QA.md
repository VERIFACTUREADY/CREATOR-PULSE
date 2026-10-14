# V3 · Registro de cambios y QA (14/10/2026)

**Estado: PREVIEW_COMERCIAL · noindex · frase LIVE vacía · marca VINCIRENA sin confirmar · país del vendedor pendiente · tema SIN PUBLICAR · NO-GO LIVE.** Rama `claude/vincirena-v3`, que parte de `claude/tienda-descanso-prototipo` (V2.2). No se ha tocado ninguna tienda Shopify.

Documentos V3: `V3_REFERENCIAS_Y_AUDITORIA.md` (fases 1 y 2) · `V3_SISTEMA_DE_DISENO.md` · `V3_COPY_Y_CRO.md` · `V3_PLAN_DE_ACTIVOS.md` · `V3_SEO_ANALITICA_AB.md`. Capturas: `qa/screenshots/v3/comparativa_*.png` (V2.2 frente a V3) y las capturas regeneradas en `qa/screenshots/`.

## Cambios

**Secciones nuevas** (editables, con `visible_in`): `ds-announce`, `ds-moments`, `ds-mechanism`, `ds-features`, `ds-editorial` y `ds-trust`.
**Snippets nuevos:** `ds-section-head`, `ds-diagram-mad` (SVG original), `ds-gallery-slots`, `ds-highlights` y `ds-offer-table`.
**Modificados:**
- `ds-product-hero`: imagen propia, nivel H1/H2 y enlaces de confianza.
- `main-product`: galería con huecos y bloques `ds_highlights` y `ds_offer_table`, que se renderizan en snippets.
- `header`: botón «Shop the mouthpiece» (≥ 750 px, solo PREVIEW/LIVE, sin compra).
- `header-group.json`: anuncio veraz, que no se ve si falta el dato.
- `descanso.css`: sistema de diseño V3.
- `settings_data.json`: radios de botón 40, de campo 12 y de tarjeta 24 (sin tocar los estados).
- Locales `en`/`es`: claves `ds.v3.*` y `ds.photo.*`.

**Plantillas** (regeneradas con `tools/content/build_us_templates.py`): `index`, `product`, `page.landing-snoring` y `page.landing-partners`. Las secciones del estado PROTOTIPO se conservan tal cual.
**QA:** `tools/qa/run-qa.mjs` acepta como hero de primera pantalla tanto `.ds-phero` como un `.ds-editorial` con H1 (landing B) y sigue exigiendo título, precio y CTA visibles.
**Sin cambios:** `ds-mode`, `ds-commerce-ready`, `ds-cart-ready`, `ds-product-missing`, `price`, la compuerta de las rutas de compra, la marca centralizada y el mercado US.

## Resultados de QA (local, `tools/`)

| Prueba | V2.2 | V3 |
|---|---|---|
| Theme Check | 0 errores · 9 avisos heredados | **0 errores · 9 avisos** (los mismos heredados de Dawn). Durante el trabajo aparecieron 2 errores (nombres de esquema largos) y 1 aviso de complejidad en `main-product`; los tres están corregidos |
| Compuerta (`gate-tests.mjs`) | 62/62 | **62/62** |
| Rutas de compra (`purchase-routes-tests.mjs`) | 48/48 | **48/48** |
| `run-qa`: 18 rutas × 375/390/768/1440 | 0 desbordamientos · 1 H1 · 0 enlaces rotos · 0 errores de consola · 0 objetivos < 44 px | **Igual** (0/1/0/0/0) |
| axe-core WCAG 2.2 AA (PREVIEW y PROTOTIPO) | 0 | **0** |
| Claims prohibidos / rastreadores / español filtrado | 0 / 0 / 0 | **0 / 0 / 0** |
| Compuerta en 6 estados + marca sustituida | 14/14 | **14/14** |
| Primera pantalla (título, precio y CTA a 390×844 y 375×667: portada, A, B y ficha) | 8/8 | **8/8** (tras 2 correcciones: regla de pantallas bajas y hero editorial de B) |
| Anchuras extra 430×932 y 1280×800 (6 rutas) | — | 0 desbordamientos · 1 H1 |
| Teclado: salto al contenido, foco visible, FAQ con Enter | OK | **OK** |
| `prelaunch-check` | NO APTO | **NO APTO** (300 incidencias en 16 páginas: ⟦PENDING⟧, marca sin confirmar, país pendiente, noindex) |

### Lighthouse móvil (simulado, servidor local sin compresión)

| Ruta | Rend. V2.2 → V3 | LCP V2.2 → V3 | CLS | TBT | Accesib. | BP | SEO |
|---|---|---|---|---|---|---|---|
| `/` | 95 → **94** | 2,6 → **2,7 s** | 0 | 0 ms | 100 | 96 | 63* |
| Ficha | 91 → **90** | 3,0 → **3,2 s** | 0 | 0 ms | 100 | 96 | 63* |
| Landing A | 96 → **90** | 2,4 → **3,3 s** | 0 | 0 ms | 100 | 96 | 63* |
| Landing B | 93 → **94** | 3,0 → **2,7 s** | 0 | 0 ms | 100 | 96 | 63* |
| FAQ / Contact | 96 → 96/95 | 2,4 → 2,4/2,6 s | 0 | 0 ms | 100 | 96 | 63* |

\* SEO 63 por el `noindex` intencionado. *Best practices* 96 por errores de consola de recursos externos que el contenedor no puede cargar.

**Objetivos del brief (LCP < 2,5 s, CLS ≤ 0,1, INP < 200 ms): no se pueden declarar cumplidos.** CLS = 0 y TBT = 0 ms (indicador de INP en laboratorio) son buenos. El **LCP local no alcanza los 2,5 s** en 5 de 6 rutas, igual que en la V2.2. El elemento LCP es el H1 (texto) y el retraso se debe al CSS que bloquea el render (Dawn + `descanso.css`), que el servidor local entrega sin compresión. En Shopify (CDN con brotli y HTTP/2) hay que medir de nuevo con PageSpeed Insights y los datos de campo (CrUX/Web Vitals de Shopify). Si sigue por encima de 2,5 s, las medidas son: CSS crítico del hero en línea y el resto con `media="print"` y `onload`, o dividir `descanso.css` por plantilla.

## Actualización 14/10/2026: fotos reales del producto

- 8 fotos del titular en la galería de la ficha y en los heros y bloques editoriales (detalle en `V3_PLAN_DE_ACTIVOS.md`). Las 3 de estética espectacular se descartan para la web.
- CSS: las fotos de producto se ven enteras sobre blanco. En móvil, la galería de la ficha se limita a 30 vh (12 vh en pantallas de 667 px o menos) y se ocultan las miniaturas (`mobile_thumbnails: hide`, galería deslizable), para que título, precio y botón sigan en la primera pantalla.
- Previsualizador local: sirve `shopify://shop_images/*` desde `media/producto/`, y `image_tag` toma el texto alternativo de la imagen, como hace Shopify. Limitación conocida: las miniaturas de Dawn salen como texto en local, pero en Shopify se renderizan bien.
- QA repetido: Theme Check 0 errores · compuerta 62/62 · rutas de compra 48/48 · `run-qa` sin incidencias (0 imágenes sin texto alternativo, axe 0, primera pantalla 8/8).

## Lo que NO se ha hecho

- No se han visitado HONEX, Snoozer ni AliExpress (bloqueados en el entorno). Ver `V3_REFERENCIAS_Y_AUDITORIA.md` §1.
- No se ha publicado nada, no se ha tocado la tienda, los pagos ni la contraseña, no se han instalado apps ni píxeles y no se han creado packs, descuentos ni suscripciones.
- No se ha inventado ningún precio, foto, reseña, característica ni plazo: todo lo que falta sigue como ⟦PENDING⟧.
- No se ha implementado la barra fija de compra en móvil (evaluada en `V3_COPY_Y_CRO.md` §4).
- No hay pruebas en Shopify real: la Section Rendering API, las variantes, el checkout y los lectores de pantalla reales siguen pendientes (`V22_INSTALACION_Y_E2E_SHOPIFY.md`).

## Siguientes pasos

1. El titular aprueba o cambia los textos US-M-06 a US-M-10, US-E-08 y US-O-04 (`04_CLAIMS_APPROVAL_US.csv`).
2. Fotos reales según `V3_PLAN_DE_ACTIVOS.md`, y el IFU del fabricante para rellenar los metacampos y marcar «Mecanismo confirmado».
3. Subir el ZIP como tema **sin publicar**, ver la vista previa en Shopify y repetir Lighthouse allí.

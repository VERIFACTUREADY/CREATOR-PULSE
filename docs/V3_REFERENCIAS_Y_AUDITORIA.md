# V3 · Fase 1 (referencias) y Fase 2 (auditoría de V2.2)

> Fecha: 14/10/2026 · Rama `claude/vincirena-v3` · Estado: **PREVIEW_COMERCIAL · noindex · tema SIN PUBLICAR · NO-GO LIVE**.

## 1. Limitación de la investigación (léase primero)

**No he podido abrir ninguna de las dos referencias.** Desde este entorno, `honexcompany.com`, `snoozertherapy.com` y `aliexpress.com` están bloqueados: el proxy rechaza la conexión (`CONNECT tunnel failed, 403`) y el lector web no resuelve el DNS (`ENOTFOUND`). Por eso:

- **No he inspeccionado** su DOM, sus estilos, sus capturas móvil o escritorio ni sus interacciones. Nada de este documento se basa en haberlas visto.
- La matriz se apoya **solo en los hallazgos del brief V3** (secciones 2.1 y 2.2), que trato como datos del titular sin verificar.
- Los precios de la competencia (HONEX 39,95 USD frente a 79,90 USD tachado; Snoozer 54,95 EUR y 74,95 EUR) se citan como **dato de competencia** y no se usan como precio recomendado.
- **No se ha copiado** ningún texto, foto, ilustración, logotipo ni composición. El diagrama del mecanismo (`snippets/ds-diagram-mad.liquid`) es un SVG original.

Para cerrar esta limitación habría que revisar ambas webs desde un navegador con acceso (móvil 390 px y escritorio 1440 px), guardar las capturas en `qa/referencias/` y contrastar la matriz.

## 2. Matriz de patrones

| Patrón observado (según el brief) | Ref. | Decisión V3 | Dónde está | Por qué |
|---|---|---|---|---|
| Primera pantalla con mensaje directo y producto protagonista | HONEX | **Adoptar** | `ds-product-hero`: antetítulo con el nombre del producto, H1, precio, CTA y enlace a «How it works» | En móvil hay que entender en segundos qué se vende y qué hacer después |
| Precio promocional con tachado | HONEX | **Adaptar** | El tachado solo aparece si `commercial.compare_at_verified = true` (control existente en `price.liquid`) | Un precio de referencia sin historial es una práctica engañosa (FTC 16 CFR 233) |
| CTA repetida a lo largo de la página | HONEX | **Adoptar con medida** | CTA en hero, «Meet the mouthpiece», mecanismo, pareja y cierre; botón en la cabecera de escritorio | Cerca de cada punto de decisión, sin saturar |
| Explicación visual del mecanismo | HONEX / Snoozer | **Adoptar (original)** | `ds-mechanism` + `ds-diagram-mad`: diagrama de categoría, leyenda numerada, 3 pasos y precauciones | Reduce la duda «¿cómo funciona?». Lleva ⟦PENDING⟧ hasta que el fabricante confirme el mecanismo del modelo exacto |
| Beneficios en bloques cortos | HONEX | **Adaptar** | `ds-features`: cada tarjeta lee un metacampo aprobado | No hay beneficios aprobados: las tarjetas muestran características documentales o ⟦PENDING⟧ |
| Confianza junto al botón | HONEX | **Adoptar** | Enlaces a envío, devoluciones y contacto bajo la CTA del hero; puntos de oferta y «compra única» en la ficha | Responde a «¿y si no me sirve?» sin sellos falsos |
| Galería extensa | HONEX | **Preparar** | `ds-gallery-slots`: 8 tomas definidas y visibles como pendientes | No hay fotos con licencia |
| Contenido emocional del descanso | HONEX | **Adoptar** | `ds-moments` (portada y landing B), `ds-editorial` de pareja | Es el posicionamiento de la marca |
| Opiniones de clientes | HONEX / Snoozer | **Aplazar** | No hay sección de reseñas; el bloque «No made-up reviews» en `ds-trust` | No existen reseñas verificadas (FTC 16 CFR 465) |
| Garantía comercial destacada | HONEX | **Aplazar** | Las devoluciones salen de `ds_offer_returns`; «guaranteed» y «money-back» siguen prohibidos en `run-qa` | Falta política real y su coste |
| Packs, ofertas y páginas alternativas | HONEX | **Preparar sin activar** | Bloque `ds_offer_table` (variantes reales, precio por unidad nativo, ahorro solo verificado, aviso de cargos recurrentes) y 2 landings | Faltan catálogo real y economía unitaria |
| Promesas cardiovasculares, eliminación garantizada | HONEX | **Evitar** | Patrones `heart`, `stops snoring`, `guaranteed`… bloqueados por `run-qa` (0 coincidencias) | Sin evidencia: riesgo FTC y FDA |
| Apariencia de marca especializada en descanso | Snoozer | **Adoptar** | Sistema de diseño V3: tonos suaves, radios grandes, sombras discretas, más aire | Más calidad percibida, sin aspecto de dropshipping |
| Navegación por problemas | Snoozer | **Adaptar** | Menú de 4 entradas y landings A (persona que ronca) y B (pareja) | Hay un solo producto: no hace falta un catálogo |
| Opciones diferenciadas con precio visible | Snoozer | **Preparar** | `ds_offer_table` | Igual que los packs |
| Comparativas de alternativas | Snoozer | **Adoptar sin superioridad** | `ds-compare` con categorías («cómo actúa», no «cuál funciona mejor») | Sin pruebas comparativas no se afirma superioridad |
| Explicación por pasos, bloques técnicos, cuidados, reemplazo | Snoozer | **Adoptar desde metacampos** | Pasos de `commercial.how_to_steps`; módulos `what_is`, `includes`, `care`; `ds-product-details` | Son datos de Snoozer, no nuestros: se rellenan con el IFU del fabricante real |
| FAQ, envío y devolución | Snoozer | **Adoptar** | FAQ de portada (11 preguntas), ficha y landings; datos desde los ajustes «Oferta» | Una sola fuente de verdad (C-07 de la auditoría V2) |
| Estructura ampliable a catálogo | Snoozer | **Preparar** | Todas las secciones nuevas aceptan cualquier producto (`product` en ajustes) | Sin tocar la compuerta por producto |

### Errores que debemos evitar

Urgencia falsa (contadores, «only X left»), tachados sin historial, estrellas o cifras de clientes sin fuente, sellos «FDA approved» o «clinically proven», atribuir al producto propiedades de otra marca (materiales, ajuste, reemplazo), imágenes de terceros, beneficios de salud no aprobados y suscripciones sin vida útil confirmada.

## 3. Auditoría de V2.2: qué se conserva, cambia, elimina o crea

Leídos `README.md`, `README_COMERCIAL.md`, `docs/V22_*`, `docs/11_*`, `config/settings_*`, layout, cabecera, ficha, las 17 secciones y los 25 snippets `ds-*`, `tools/content/build_us_templates.py` (fuente de las plantillas) y `qa/` (capturas e informes).

| Componente actual | Problema u oportunidad | Inspiración | Propuesta V3 (hecha) | Prioridad | Riesgo técnico | Prueba de aceptación | Estado |
|---|---|---|---|---|---|---|---|
| `ds-product-hero` (portada) | H1 = nombre del producto: no transmite el problema ni la emoción. Sin confianza junto a la CTA | HONEX | Antetítulo con el producto, H1 emocional, subtítulo con el problema, enlaces de confianza, imagen propia opcional y nivel H1/H2 | P0 | Bajo | `run-qa` primera pantalla: título, precio y CTA visibles a 390×844 y 375×667 | ✅ 8/8 |
| `ds-callout` «empathy» | Un único párrafo; poco escaneable | Snoozer / brief bloque 3 | `ds-moments`: 3 momentos (quien ronca, quien duerme al lado, los dos), sin culpables, con fuente | P1 | Bajo | Claims 0; axe 0 | ✅ |
| — (no existía) | «Qué es» sin foto ni presentación | Brief bloque 4 | `ds-editorial` con `what_is`, precio confirmado y 2 CTA | P1 | Bajo | ⟦PENDING⟧ si falta el metacampo | ✅ |
| `ds-product-module` how_to_steps | Pasos en lista plana; sin gráfico ni precauciones junto a los pasos | HONEX / Snoozer | `ds-mechanism`: diagrama original, leyenda, 3 pasos (bloques o metacampo), precauciones siempre visibles y aviso de mecanismo sin confirmar | P0 | Medio (afirmación sobre el mecanismo) | El aviso ⟦PENDING⟧ aparece mientras `mechanism_verified = false` | ✅ |
| `ds-product-module` includes (portada) | Un único dato | HONEX | `ds-features`: 3–5 tarjetas desde metacampos (`features`, `materials`, `care`, `includes`, `for_whom`, `delivery_window`) | P1 | Bajo | Sin metacampo → ⟦PENDING⟧ | ✅ |
| — | Faltaba la sección emocional de pareja | Brief bloque 7 | `ds-editorial` (pareja) con hueco de foto lifestyle | P1 | Bajo | Hueco detectado por `prelaunch-check` | ✅ |
| `ds-compare` (solo en How it works) | No se usaba en la venta | Snoozer | En portada y landing A (4 filas de categorías) | P2 | Bajo | Pie de tabla: «doesn't show effectiveness» | ✅ |
| `ds-cards` «Our commitment» | Compromisos genéricos | HONEX | `ds-trust`: envío, devoluciones, atención, pago, fabricante y «No made-up reviews» | P1 | Bajo | Sin dato → ⟦PENDING⟧ | ✅ |
| `ds-faq` portada (8) | Faltaban ajuste, materiales, limpieza y molestias | Brief bloque 10 | 11 preguntas en lenguaje natural con enlace a la ficha | P1 | Bajo | `faqOpensWithEnter` | ✅ |
| `ds-offer-strip` portada | 4 ⟦PENDING⟧ seguidos en la primera pantalla | — | Retirado de la portada: el dato está en `ds-trust` y en la ficha | P2 | Bajo | — | ✅ |
| Cabecera | Sin acceso directo al producto en escritorio | HONEX | Botón «Shop the mouthpiece» (≥ 750 px, solo PREVIEW/LIVE, enlace a la ficha) | P2 | Bajo | Gate: sin `/cart/add` ni carrito en PREVIEW | ✅ |
| `announcement-bar` de Dawn (desactivado) | Riesgo de mensajes sin respaldo | — | `ds-announce`: solo pinta un dato real de «Oferta» o un texto aprobado; vacío = no se ve | P3 | Bajo | En la previsualización no aparece (datos vacíos) | ✅ |
| Ficha · galería | Un hueco sin indicar qué fotos hacen falta | HONEX | `ds-gallery-slots`: hueco principal + lista plegable de 7 tomas | P1 | Bajo | `prelaunch-check` cuenta los huecos | ✅ |
| Ficha · columna de compra | `media_size: large` dejaba la columna de compra estrecha en escritorio | Snoozer | `media_size: medium` (55/45) con columna fija (`enable_sticky_info`) | P1 | Bajo | Capturas a 1280/1440 | ✅ |
| Ficha · resumen y opciones | No había características ni opciones junto a la compra | HONEX / Snoozer | Bloques `ds_highlights` y `ds_offer_table` (en snippets para no superar la complejidad de Liquid) | P1 | Medio | Theme Check sin `LiquidComplexity` nueva | ✅ |
| Ficha · módulos `how` | Duplicado con el mecanismo | — | Sustituido por `ds-mechanism` (pasos del metacampo) | P2 | Bajo | Ancla `#how-to-use` conservada | ✅ |
| Landings A y B | Misma estructura y casi el mismo texto (solo cambiaba el titular) | Brief §7 | A: entender → opciones → mecanismo → detalles → dudas. B: hero editorial H1 → noche compartida → cómo hablarlo (4 tarjetas) → producto (H2) → mecanismo → preguntas de pareja | P0 | Bajo | 1 H1 por página; primera pantalla con título, precio y CTA | ✅ |
| Sistema de diseño | Tokens mínimos; botones con radio de 10 px; un solo nivel de sombra | Snoozer | Tokens V3 (`docs/V3_SISTEMA_DE_DISENO.md`); botones píldora; tarjetas de 24 px | P1 | Bajo | axe 0; contraste AA | ✅ |
| Estados, compuerta, carrito, marca, noindex, mercado US | Funcionan | — | **Sin cambios** | — | — | gate 62/62, rutas 48/48, `run-qa` gate 14/14 | ✅ |
| Barra fija de compra en móvil | El brief pide evaluarla, no implementarla | HONEX | **No implementada.** Evaluación e hipótesis C en `docs/V3_SEO_ANALITICA_AB.md` | — | — | — | Documentado |

**Se elimina:** nada del código. En la portada y las landings se retiran algunas secciones del estado comercial (offer strip, módulos duplicados). Las secciones del estado PROTOTIPO siguen intactas.

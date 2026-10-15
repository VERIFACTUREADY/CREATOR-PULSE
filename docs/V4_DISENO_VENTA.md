# V4 · Portada como página de venta (estructura tipo HONEX)

**Fecha:** 15/10/2026.

**Motivo:** el titular consideró insuficiente el diseño V3 y pidió tomar como referencia la ficha de HONEX. Envió 12 capturas del móvil, porque desde el entorno no se puede abrir esa web.

**Estado:** PREVIEW_COMERCIAL · noindex · compra desactivada · NO-GO LIVE (sin cambios).

## Qué se toma de HONEX (estructura, no contenido)

| Bloque HONEX | V4 (sección) | Diferencia deliberada |
|---|---|---|
| Titular enorme centrado + subtítulo gris + foto con sello rojo | `ds-sales-hero` | Titular sin promesa («Peaceful nights, for both of you.»). El sello solo aparece con `ds_offer_guarantee` real. Precio confirmado o pendiente |
| 3 iconos de confianza (reseñas · prueba · envío) | Bloques de `ds-sales-hero` | **Sin** contador de reseñas ni «21,000+ clientes»: no hay datos. Garantía, envío y devoluciones salen de Ajustes › Oferta |
| Lista de ventajas con icono | `ds-sales-benefits` | Solo lo visible en las fotos (tornillo de ajuste, dos férulas, estuche y herramienta), pendiente de confirmar con la ficha |
| Botón ancho «GET 50% OFF TODAY» | «See packs & prices» → `#buy` | Sin descuento sin historial (FTC 16 CFR 233) |
| Galería con miniaturas | `ds-sales-gallery` (CSS scroll-snap, sin JS) | Fotos del titular |
| Bloque marino «cómo funciona» + antes/después | `ds-mechanism` en scheme-4 + diagrama propio | Sin «stops snoring» ni «no side effects». Precauciones visibles |
| «Comfort you can sleep in» + foto con etiquetas + tarjetas | `ds-sales-anatomy` | Etiquetas solo de partes visibles. Sin «Dentist designed · Doctor approved» |
| Reseñas en vídeo | — | No se muestra hasta tener reseñas verificadas (FTC 16 CFR 465) |
| Tarjeta «Just try it, 100% risk free» | `ds-sales-guarantee` | El texto sale de `ds_offer_guarantee_text`; sin datos queda pendiente y en LIVE se oculta |
| Packs con «Most popular / Best deal» | `ds-buy-box` | Los packs son **variantes reales**. Las etiquetas las escribe el titular; se desaconsejan «Most popular» y «Best deal» sin datos de ventas. Sin «Max 10 units» ni cronómetros de carrito |

## Diseño

- **Paleta nueva:** marino `#0F1B3D`, azul de acción `#2347C5`, fondo claro `#F3F6FC`, texto gris `#4A5573` y rojo solo para el sello (`#C93A2A`). Contrastes AA verificados por axe (0 violaciones).
- **Tipografía:** titulares en **Poppins 800** (`type_header_font = poppins_n8`) y texto en Lato.
- **Cabecera:** marino, con botón «Shop now» que lleva a `/#buy`; el producto sigue en borrador.
- **Pendientes ⟦PENDING⟧:** dejan de ser recuadros amarillos rayados y pasan a etiquetas grises discretas. Siguen siendo detectables (`data-ds-placeholder`) y bloquean LIVE.
- **Nuevos ajustes del tema (Estado de la tienda):** `ds_offer_guarantee` (texto corto del sello) y `ds_offer_guarantee_text` (condiciones).

## Textos de producto pendientes de confirmar (`04_CLAIMS_APPROVAL_US.csv`, US-P-05 a US-P-08)

1. «An adjustment screw on the side lets you fine-tune where the lower tray sits.»
2. «An upper and a lower tray fit over your teeth.»
3. «Storage case and adjustment tool»: aparece en las fotos, pero hay que confirmar que viene en la caja.
4. «Turn the adjustment screw to move the lower tray forward, a little at a time, following the instructions.»

## Datos que faltan para completar el estilo

Precio y packs (variantes reales), garantía (días y condiciones), envío (coste y plazo) y devoluciones. Las reseñas solo podrán mostrarse si son reales y verificadas.

## QA

- Theme Check: 0 errores.
- Compuerta 62/62 · rutas de compra 48/48.
- `run-qa`: 0 desbordamientos · 1 H1 · axe 0 · claims 0 · primera pantalla 8/8 (el test reconoce `.ds-shero`).

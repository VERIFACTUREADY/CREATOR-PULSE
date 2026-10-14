# README comercial · VINCIRENA (marca provisional) · EE. UU.

**Mercado:** Estados Unidos · inglés · USD · sales tax en el checkout. **Marca:** ajuste «Nombre de marca» (VINCIRENA, pendiente de confirmar).

**Estado de publicación:** tema **SIN PUBLICAR** · estado del tema = **PREVIEW_COMERCIAL** · pagos reales **desactivados** · LIVE **no autorizado**.

## Estados de la tienda (Ajustes del tema › Estado de la tienda)

| Estado | Qué ve el visitante | ¿Se puede comprar? |
|---|---|---|
| PROTOTIPO | Web informativa, sin oferta | No (no existe formulario de pedido) |
| **PREVIEW_COMERCIAL** (entregado) | Tienda de venta completa: hero de producto, ficha, landings, envío y devoluciones. Lo que falta aparece como ⟦PENDING⟧ | No (CTA desactivada, sin `/cart/add`) |
| LIVE | Tienda operativa | Solo con la frase `VENTA REAL AUTORIZADA`, marca confirmada, país del vendedor, los datos del titular y la oferta, y la ficha completa (en EE. UU., con los datos `regulatory_us`). Si falta algo, vuelve a PREVIEW con un aviso rojo |

## Oferta: fuentes de verdad

| Dato | Dónde se edita | Se muestra en |
|---|---|---|
| Precio | Producto (Shopify) + `commercial.price_confirmed` | Hero, ficha, landings |
| Beneficio aprobado | `commercial.short_benefit` | Hero, ficha |
| Qué es / cómo se usa / para quién / qué incluye / cuidados | `commercial.*` | Ficha, portada |
| Envío, devoluciones, atención, pago | Ajustes del tema › Oferta (en inglés) | Hero, ficha, FAQ (`[[ENVIO]]`…), Shipping, Returns |
| Marca | Ajustes del tema › Nombre de marca (o nombre de la tienda) | Cabecera, pie, `<title>`, OpenGraph, JSON-LD, contraseña, avisos |
| Plazo de entrega | `commercial.delivery_window` | Ficha, puntos de oferta |
| Titular | Ajustes del tema › Identidad | Pie, aviso legal |

**Precios confirmados: ninguno todavía.** La hoja `docs/05_ECONOMIA_UNITARIA.xlsx` (USD) no contiene costes ni precios reales; solo puntos de prueba editables.

## Assets

| Asset | Estado |
|---|---|
| Fotos de producto (5–8) | ⟦PENDING⟧: hueco «PHOTO PENDING · NOT PUBLISHABLE» |
| Vídeo vertical | Pendiente (opcional) |
| Ilustración SVG de noche | Original del proyecto; uso secundario (portada en PROTOTIPO) |
| Logotipo | Monograma provisional (luna + nombre) |

## Rutas comerciales

`/` · `/products/adjustable-mouthpiece` · `/pages/landing-snoring` · `/pages/landing-partners` · `/pages/faq` · `/pages/shipping` · `/pages/returns` · `/pages/contact`

## Exportación reproducible

```bash
git checkout claude/tienda-descanso-prototipo   # último commit de la rama
cd theme && zip -qr ../dist/tema-descanso-dawn.zip assets config layout locales sections snippets templates
```
El ZIP de `dist/` se genera siempre desde el commit en el que se versiona. No hay secretos en el repositorio: credenciales, tokens y claves de pago van en Shopify, nunca en Git.

## Antes de LIVE

`docs/V21_GO_NO_GO_EEUU.md`, `docs/V21_DATOS_NECESARIOS.md`, `docs/V22_FDA_DOCUMENTOS_Y_VALIDACIONES.md` y `docs/V22_INSTALACION_Y_E2E_SHOPIFY.md`. Hoja: `docs/05_ECONOMIA_UNITARIA.xlsx` (USD).

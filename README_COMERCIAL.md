# README comercial · Descanso Compartido

**Estado de publicación:** tema **SIN PUBLICAR** · estado del tema = **PREVIEW_COMERCIAL** · pagos reales **desactivados** · LIVE **no autorizado**.

## Estados de la tienda (Ajustes del tema › Estado de la tienda)

| Estado | Qué ve el visitante | ¿Se puede comprar? |
|---|---|---|
| PROTOTIPO | Web informativa, sin oferta | No (no existe formulario de pedido) |
| **PREVIEW_COMERCIAL** (entregado) | Tienda de venta completa: hero de producto, ficha, landings, envío y devoluciones. Lo que falta aparece como ⟦PENDIENTE⟧ | No (CTA desactivada, sin `/cart/add`) |
| LIVE | Tienda operativa | Solo con la frase `VENTA REAL AUTORIZADA`, los datos del titular y la oferta, y la ficha completa. Si falta algo, vuelve a PREVIEW con un aviso rojo |

## Oferta: fuentes de verdad

| Dato | Dónde se edita | Se muestra en |
|---|---|---|
| Precio | Producto (Shopify) + `commercial.price_confirmed` | Hero, ficha, landings |
| Beneficio aprobado | `commercial.short_benefit` | Hero, ficha |
| Qué es / cómo se usa / para quién / qué incluye / cuidados | `commercial.*` | Ficha, portada |
| Envío, devoluciones, atención, pago | Ajustes del tema › Oferta | Hero, ficha, FAQ (`[[ENVIO]]`…), envíos, devoluciones |
| Plazo de entrega | `commercial.delivery_window` | Ficha, puntos de oferta |
| Titular | Ajustes del tema › Identidad | Pie, aviso legal |

**Precios confirmados: ninguno todavía.** Las cifras de `docs/05_ECONOMIA_UNITARIA.xlsx` son hipótesis.

## Assets

| Asset | Estado |
|---|---|
| Fotos de producto (5–8) | ⟦PENDIENTE⟧: hueco «FOTO PENDIENTE · NO PUBLICABLE» |
| Vídeo vertical | Pendiente (opcional) |
| Ilustración SVG de noche | Original del proyecto; uso secundario (portada en PROTOTIPO) |
| Logotipo | Monograma provisional (luna + nombre) |

## Rutas comerciales

`/` · `/products/dispositivo-bucal` · `/pages/landing-ronquidos` · `/pages/landing-pareja` · `/pages/preguntas-frecuentes` · `/pages/envios` · `/pages/devoluciones` · `/pages/contacto`

## Exportación reproducible

```bash
git checkout claude/tienda-descanso-prototipo   # commit indicado en docs/V2_CHANGELOG.md
cd theme && zip -qr ../dist/tema-descanso-dawn.zip assets config layout locales sections snippets templates
```
El ZIP de `dist/` se genera siempre desde el commit en el que se versiona. No hay secretos en el repositorio: credenciales, tokens y claves de pago van en Shopify, nunca en Git.

## Antes de LIVE

`docs/V2_PENDIENTES_Y_DATOS.md`, apartado C.

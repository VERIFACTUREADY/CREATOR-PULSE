# V2 · Plan de pruebas en Shopify real, medición y SEO comercial

> Nada de esto se ha podido ejecutar: no hay acceso a ninguna tienda (`V2_PENDIENTES_Y_DATOS.md`, punto 18). Es el guion para hacerlo en cuanto lo haya.

## 1. Checkout de prueba (C-08)

**Preparación (tema sin publicar):**
1. Subir `dist/tema-descanso-dawn.zip` como tema **sin publicar**. Estado = **LIVE** solo en ese tema de pruebas, con datos completos y la frase de confirmación, **en una tienda de desarrollo o con pagos en modo de prueba**.
2. Pagos: en una tienda de desarrollo, *Bogus Gateway* (tarjeta `1` = éxito, `2` = rechazo). En una tienda real, el modo de prueba de Shopify Payments. **Nunca tarjetas reales.**
3. Crear el producto `dispositivo-bucal` con fotos, variantes reales y metacampos.

**Recorridos** (grabar la pantalla o guardar capturas de cada paso):

| # | Recorrido | Navegadores | Resultado esperado |
|---|---|---|---|
| 1 | Portada → hero → ficha → variante → cantidad 2 → añadir → `/cart` → checkout → pago de prueba → confirmación | iOS Safari, Chrome Android, Chrome escritorio | Mismo precio en ficha, carrito, checkout y email |
| 2 | Cambiar de variante en la ficha | Los tres | Cambian precio, imagen y disponibilidad sin recargar |
| 3 | Carrito vacío | Los tres | Mensaje claro, sin errores |
| 4 | Variante agotada | Los tres | Botón «Agotado», sin poder añadir |
| 5 | Código de descuento válido o inválido (si se usa) | Uno | Mensaje correcto |
| 6 | Tarjeta rechazada (Bogus `2`) | Uno | Error legible y sin pedido creado |
| 7 | Email de confirmación y página de estado del pedido | Bandeja real | En castellano, con plazo, devoluciones y contacto que coincidan con el tema |
| 8 | Volver a PREVIEW_COMERCIAL | — | El formulario desaparece y el carrito muestra el aviso |

Repetir después `node tools/qa/prelaunch-check.mjs https://<tienda>.myshopify.com --cookie "<cookie de contraseña>"`.

## 2. Medición sin apps de pago (C-09)

- **Shopify Analytics (nativo):** sesiones, sesiones con vista de producto, con «añadir al carrito», con checkout y pedidos (informe *Conversión en la tienda online*). Copiar cada semana a la hoja «Panel semanal».
- **Eventos:** los estándar de Shopify (`page_viewed`, `product_viewed`, `product_added_to_cart`, `checkout_started`, `checkout_completed`). El tema ya emite `product-component` (Dawn). No añadir píxeles de terceros sin autorización, revisión de privacidad y banner de cookies configurado.
- **Prueba de coherencia:** hacer 5 acciones de prueba (2 vistas, 1 ATC, 1 checkout, 1 compra de prueba) y comprobar que aparecen una sola vez.
- **UTMs propuestas:**

| Campaña | Destino | utm_source | utm_medium | utm_campaign | utm_content |
|---|---|---|---|---|---|
| Persona que ronca | `/pages/landing-ronquidos` | instagram / tiktok / meta | paid_social u organic | ronquidos_v1 | hook-01, hook-02… |
| Pareja | `/pages/landing-pareja` | instagram / tiktok / meta | paid_social u organic | pareja_v1 | hook-01… |
| Demostración | `/products/dispositivo-bucal` | — | — | demo_v1 | video-01 |

Regla: **una pieza = una idea = un destino**. El mensaje del anuncio debe coincidir con la primera pantalla de la landing. Las visualizaciones no son sesiones. No declarar «producto ganador» sin pedidos y contribución real.

## 3. SEO comercial (C-11)

| Página | Título SEO | Meta descripción |
|---|---|---|
| Ficha | [Nombre comercial] \| Descanso Compartido | [Qué es, en 1 frase de la ficha] · Envío [dato] · Devoluciones [dato] |
| Landing ronquidos | ¿Te preocupan tus ronquidos? \| Descanso Compartido | Conoce nuestro dispositivo bucal: qué es, cómo se usa y qué incluye. |
| Landing pareja | Descanso en pareja \| Descanso Compartido | Descansar juntos importa. Conoce nuestro dispositivo bucal y cómo se usa. |

- `Product`/`Offer` JSON-LD y `og:price` solo salen en LIVE con datos completos (comprobado).
- Las landings de campaña pueden quedarse con `noindex` si duplican la ficha; decidir antes de publicar.
- Antes de publicar: títulos únicos, `sitemap.xml` sin productos de prueba y `robots.txt` por defecto de Shopify.

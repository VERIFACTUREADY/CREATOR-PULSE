# V2.2 · Instalación privada y pruebas E2E en Shopify real

> **No ejecutado por mí:** no tengo acceso a ninguna tienda. Los resultados locales (`10_QA_LANZAMIENTO.md`) **no sustituyen** estas pruebas. Nada se da por superado hasta ejecutarlo en Shopify y guardar la evidencia (capturas, vídeo o HAR) en `qa/shopify-real/AAAA-MM-DD/`, con el nombre de quien lo hizo.
>
> Durante todo el procedimiento: **contraseña activada, tema sin publicar, sin pagos reales, sin LIVE** salvo en el bloque 4, y allí solo en una **tienda de desarrollo** con *Bogus Gateway*, nunca en la tienda real.

## 0. Instalación privada (≈ 30 min)

| Paso | Acción | Comprobación |
|---|---|---|
| 0.1 | Usar una **tienda de desarrollo** (Partners, gratuita) para el bloque 4. Para el resto vale la tienda real con contraseña | *Online Store › Preferences › Password protection* = activada |
| 0.2 | *Settings › Markets*: United States · USD · English | Moneda y precio en `$` en la vista previa |
| 0.3 | *Online Store › Themes › Add theme › Upload zip* → `dist/tema-descanso-dawn.zip`. **No pulsar «Publish»** | El tema aparece en «Theme library», no como «Current theme» |
| 0.4 | Alternativa: `shopify theme push --unpublished --path theme` y `shopify theme check --path theme` (Shopify CLI, gratuita) | Theme Check: 0 errores |
| 0.5 | *Settings › Custom data › Products*: crear las definiciones `commercial.*`, `compliance.*` (4 compartidos) y **`regulatory_us.*`** (`V22_MIGRACION_METACAMPOS.md`) | Las 10 claves de `regulatory_us` existen con el tipo indicado |
| 0.6 | Crear las páginas y menús de `11_METACAMPOS_Y_CONFIG.md` (tabla V2.1) | Las 14 páginas responden con su plantilla |
| 0.7 | Ajustes del tema › *Estado de la tienda*: estado **PREVIEW_COMERCIAL**, noindex **activado**, mercado **United States**, frase LIVE **vacía**, marca VINCIRENA **sin** confirmar, país del vendedor **pendiente** | Aviso «Commercial preview» y «brand pending» |

## 1. Dos productos de prueba (P0)

Crear en estado **Draft** (y además, solo en la tienda de desarrollo, una copia **Active** para el bloque 4):

| Producto | Handle | Metacampos |
|---|---|---|
| **A · completo EE. UU. (PRUEBA)** | `test-a-us-complete` | Todos los `commercial.*`, los 4 compartidos y los 10 `regulatory_us.*` con el texto `TEST VALUE – NOT REAL`, precio confirmado y 1 imagen de prueba |
| **B · solo documentación UE** | `test-b-eu-only` | `commercial.*` y `compliance.*` completos (incluidos `ifu_es`, `eu_declaration_ref`…), **ningún** `regulatory_us.*` |

El producto real `adjustable-mouthpiece` sigue en Draft y sin datos inventados.

## 2. Compuerta y estados (tienda con contraseña, tema sin publicar)

| # | Prueba | Esperado | Evidencia |
|---|---|---|---|
| 2.1 | PREVIEW: ficha de A y de B | Botón desactivado, sin `action="/cart/add"` en el código fuente, sin JSON-LD `Product`, sin `og:price` | Captura + código fuente |
| 2.2 | PREVIEW: ficha de B | El aviso nombra «FDA clearance details», «English instructions and warnings», «US importer and FDA registration», «FTC claims review», «human regulatory verification record» | Captura |
| 2.3 | Mercado = European Union (solo para la prueba; volver a US después) | B deja de pedir datos FDA; A pasa a pedir los documentos UE | Captura |
| 2.4 | `<head>` de cualquier página | `<html … data-ds-brand-confirmed="false" data-ds-seller-country="pending">`, `noindex` | Código fuente |
| 2.5 | Cambiar «Nombre de marca» a otro valor | Cambian cabecera, pie (©), `<title>`, `og:site_name` y JSON-LD `Organization`/`WebSite`. Restaurar después | Código fuente antes/después |
| 2.6 | País del vendedor = US / ES / Other | Etiqueta fiscal EIN / NIF/CIF (Spain) / Tax ID en *Company information* y en el pie | 3 capturas |
| 2.7 | **Control de servidor:** `POST /cart/add` directo con el id de variante de B (curl con la cookie de la contraseña) | Documentar la respuesta. En Draft, Shopify debe rechazarla. **La compuerta Liquid no es control de acceso** | Salida de curl |

## 3. Rutas de compra alternativas de Dawn (P0-2)

En el editor del tema, en una **plantilla de prueba** (*Templates › Create template*, nunca en la portada real), añadir:

| # | Sección | Configuración | Esperado en PREVIEW | Esperado en LIVE (bloque 4) |
|---|---|---|---|---|
| 3.1 | *Featured collection* con A y B | Quick add = **Standard** | Ningún botón «Add»/«Choose options» en las tarjetas | Solo la tarjeta de A tiene «Add» |
| 3.2 | Misma sección | Quick add = **Bulk** | Ningún control de cantidad en las tarjetas | Solo A |
| 3.3 | *Featured product* = B | — | Sin `/cart/add` | Sin `/cart/add` |
| 3.4 | *Featured product* = A | — | Sin `/cart/add` | Con `/cart/add` |
| 3.5 | *Quick order list* con A y B | — | Sin filas de pedido | Solo la fila de A |
| 3.6 | *Related products* en la ficha de A (recomendaciones con B) | Quick add activado si el bloque lo permite | Sin añadir rápido | Solo A |
| 3.7 | Búsqueda `/search?q=test` y colección con A y B | Quick add activado en *Search* / *Collection* | Sin añadir rápido | Solo A |
| 3.8 | Carrito: añadir A por la ficha y forzar B con `POST /cart/add` (si Shopify lo acepta) | — | — | `/cart`, cajón y notificación **sin** botón «Check out» y con el aviso; solo con [A] aparece «Check out» |

## 4. Recorrido E2E (solo tienda de desarrollo, LIVE temporal, *Bogus Gateway*)

LIVE exige: frase `VENTA REAL AUTORIZADA`, marca confirmada, país del vendedor, titular, oferta y ficha completa. En la tienda de desarrollo se usan **valores de prueba** y se borran al terminar.

| # | Recorrido | Dispositivos |
|---|---|---|
| 4.1 | Portada → ficha de A → cantidad 2 → añadir → `/cart` → checkout → pago de prueba (Bogus `1`) → confirmación | iPhone (Safari), Android (Chrome), escritorio |
| 4.2 | Tarjeta rechazada (Bogus `2`): error legible, sin pedido | Uno |
| 4.3 | Sales tax en dos estados: aparece en el checkout, no en el precio | Uno |
| 4.4 | Tarifas de envío del checkout = textos de *Shipping* del tema | Uno |
| 4.5 | Email de confirmación y página de estado del pedido: inglés, marca correcta, plazo y devoluciones coherentes | Bandeja real |
| 4.6 | Volver a PREVIEW_COMERCIAL: desaparecen formularios y checkout | Uno |
| 4.7 | Desmarcar «Marca confirmada»: LIVE vuelve a bloquearse con aviso rojo | Uno |

## 5. Privacidad: eventos y cookies reales (P1)

El texto de *Privacy Policy* y la FAQ dicen: cookies necesarias de Shopify + analítica integrada de Shopify (eventos estándar), **sin** píxeles publicitarios ni apps de terceros. Hay que comprobarlo en la tienda:

| # | Prueba | Esperado |
|---|---|---|
| 5.1 | *Settings › Customer privacy*: banner de cookies (regiones), «Sell or share» y Global Privacy Control | Captura de la configuración; ajustar el texto si cambia algo |
| 5.2 | DevTools › Application › Cookies, en una visita limpia **antes** de aceptar el banner y **después** | Lista de cookies con dominio y finalidad. Comparar con la documentación de cookies de Shopify. Pegar la lista final en *Privacy Policy* (hueco «Final cookie list») |
| 5.3 | DevTools › Network: filtrar `monorail`, `web-pixels`, `standard-events`, `facebook`, `google`, `tiktok` | Solo dominios de Shopify. Ningún píxel de terceros |
| 5.4 | *Settings › Customer events*: píxeles personalizados o de apps | Ninguno |
| 5.5 | `node tools/qa/prelaunch-check.mjs https://<tienda> --cookie "<cookie>"` | Debe seguir dando **NO APTO** mientras haya ⟦PENDING⟧, marca sin confirmar o país pendiente |

## 6. Accesibilidad y móvil reales
VoiceOver (iOS) y TalkBack (Android): portada → ficha → FAQ → contacto. Zoom al 200 %. Teclado en escritorio. Primera pantalla a 375×667 y 390×844 con fotos reales.

## 7. Al terminar
Borrar los productos A y B (o dejarlos en Draft en la tienda de desarrollo), dejar el tema en PREVIEW_COMERCIAL con noindex, frase LIVE vacía y contraseña activada. Archivar la evidencia y anotar en `V22_CHANGELOG.md` qué pruebas pasaron, fallaron o no se hicieron.

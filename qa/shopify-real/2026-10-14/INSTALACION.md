# Instalación privada del tema V3 en Shopify (14/10/2026)

Tienda: `2gcbh2-at.myshopify.com` · plan Basic · **moneda EUR · país España** (el proyecto está pensado para USD/EE. UU.; no se ha cambiado: decisión del titular).

## Comprobaciones previas (solo lectura)
- Contraseña de la tienda: **activada**.
- Temas existentes: `Helio` (**MAIN**, publicado, sin tocar) y `Horizon` (UNPUBLISHED, sin tocar).

## Qué se hizo
1. `stagedUploadsCreate` (FILE, application/zip) y subida del ZIP V3 al almacenamiento temporal de Shopify.
2. `themeCreate` con `role: UNPUBLISHED`, que creó **`VINCIRENA V3 · PREVIEW (no publicar)`** (`gid://shopify/OnlineStoreTheme/206476181852`).
3. Shopify descartó al validar 6 archivos: `sections/main-product.liquid` (nombres de bloque de más de 25 caracteres), `sections/ds-mechanism.liquid` (etiqueta de opción de más de 50 caracteres) y, por depender de ellas, `templates/index.json`, `product.json`, `page.landing-snoring.json` y `page.landing-partners.json`. Theme Check no detecta esos límites. Se corrigieron en el commit `8a84f77` y se subieron con `themeFilesUpsert` (body URL del commit) **solo a ese tema sin publicar**.
4. Verificación: las sumas MD5 de `settings_data.json`, `descanso.css`, las secciones corregidas, `index.json` y las landings coinciden con el repositorio. `product.json` y `header-group.json` solo difieren en el formato con que Shopify reescribe los JSON; el contenido es el mismo.

Ajustes en el tema subido: `ds_store_mode = preview_comercial`, `ds_noindex = true`, `ds_live_confirmation = ""`, `ds_brand_name = VINCIRENA`, `ds_brand_confirmed = false`, `ds_market = us`, `ds_seller_country = ""`.

## Qué NO se hizo
No se ha publicado ni sustituido el tema principal. No se ha tocado la contraseña, los pagos, los mercados, los impuestos, los envíos ni el nombre de la tienda. No se han creado productos, páginas, menús ni metacampos (pasos 2–5 de `docs/PROMPT_OTRO_CHAT_SHOPIFY.md`, pendientes de autorización). No se ha instalado ninguna app ni píxel.

## Pendiente
- Sin el producto `adjustable-mouthpiece` ni las páginas `/pages/*`, la vista previa muestra la portada con ⟦PENDING⟧, pero la ficha, las landings y el botón de la cabecera dan 404.
- Un producto en Draft no se ve en la tienda; solo desde el admin con «Preview».
- El tema `Horizon` y el `Helio` publicado siguen como estaban.

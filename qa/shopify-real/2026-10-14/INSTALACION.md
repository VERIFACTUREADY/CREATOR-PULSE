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

## Estructura creada (autorizada por el titular: «añade todo»)
El titular decidió mantener por ahora **EUR y España** (no se ha cambiado).

**Definiciones de metacampos de producto (31, todas vacías):**
- `commercial` (10): `price_confirmed` y `compare_at_verified` (boolean); `short_benefit` y `delivery_window` (una línea); `how_to_steps` (lista de una línea); `what_is`, `includes`, `for_whom`, `features` y `care` (texto enriquecido).
- `compliance`, campos compartidos (4): `manufacturer_legal_name`, `model_reference`, `lot_traceability` (una línea); `materials` (varias líneas).
- `compliance`, campos UE (7): `intended_purpose`, `economic_operator` (varias líneas); `ifu_es`, `warnings_es`, `contraindications_es` (enriquecido); `eu_declaration_ref`, `claim_approval_version` (una línea).
- `regulatory_us` (10): con los tipos de `docs/V22_MIGRACION_METACAMPOS.md`.

IDs: de `MetafieldDefinition/523218256220` a `523219239260`.

**Páginas (sin contenido; el texto lo pone la plantilla).** Publicadas, pero solo accesibles con la contraseña de la tienda; ocultas darían 404 también en la vista previa del tema.

| Handle | Plantilla | ID |
|---|---|---|
| how-it-works | how-it-works | 717002015068 |
| the-product | the-product | 717002047836 |
| use-and-safety | use-and-safety | 717002080604 |
| faq | faq | 717002113372 |
| about | about | 717002146140 |
| shipping | shipping | 717002178908 |
| returns | returns | 717002211676 |
| privacy | privacy | 717002244444 |
| terms | terms | 717002277212 |
| company-information | company-information | 717002309980 |
| accessibility | accessibility | 717002342748 |
| landing-snoring | landing-snoring | 717002375516 |
| landing-partners | landing-partners | 717002408284 |
| contact (ya existía) | **cambiada** de `contact` a `contact-us` | 716732563804 |

Nota: Helio (el tema publicado) no tiene la plantilla `contact-us` y mostrará la página de contacto con su plantilla genérica. Para deshacerlo, volver a poner la plantilla `contact`.

**Menús**
- `main-menu` (347299250524): The product · How it works · Use & safety · FAQ. **Antes:** Home (/) · Catalog (/collections/all) · Contact (/pages/contact).
- `footer` (347299283292): About us · Contact · Shipping policy · Return policy · Accessibility. **Antes:** Search (/search).
- `legal` (347899756892, nuevo): Privacy Policy · Terms of Service · Company information.

Estos menús también los usa Helio, que está detrás de la contraseña.

**Producto:** `Adjustable Mouthpiece` · handle `adjustable-mouthpiece` · `Product/15893755396444` · **DRAFT** · plantilla por defecto (`product`) · sin descripción, fotos ni metacampos · etiquetas `vincirena-v3` y `preview-not-for-sale`. Shopify obliga a crear una variante y le pone **precio 0,00**; no se ha cambiado. El tema muestra ⟦PENDING⟧ porque `price_confirmed` está vacío.

## Qué NO se hizo
No se ha publicado ni sustituido el tema principal. No se ha tocado la contraseña, los pagos, los mercados, los impuestos, los envíos ni el nombre de la tienda. No se han creado los productos de prueba A y B ni se ha ejecutado el bloque 4 (E2E con pagos). No se ha instalado ninguna app ni píxel.

## Verificación final
Contraseña **activada** · `Helio` sigue siendo **MAIN** · tema V3 **UNPUBLISHED** · producto **DRAFT** y sin metacampos.

## Pendiente
- Un producto en Draft no aparece en la tienda: la ficha solo se ve desde el admin (Products › Adjustable Mouthpiece › Preview, eligiendo el tema V3). En la vista previa del tema, el botón «Shop the mouthpiece» y «The product» darán 404 mientras siga en Draft.
- Rellenar los metacampos solo con documentos (ficha aprobada, IFU del fabricante).

## 15/10/2026 · Cambio de marca a SILEXORA (dominio silexora.com)
- Ajuste del tema `ds_brand_name` = **SILEXORA** en el tema sin publicar. Cambia la cabecera, el pie, `<title>`, OpenGraph, el JSON-LD y la página de contraseña.
- Tema renombrado a «SILEXORA · PREVIEW (no publicar)».
- `ds_brand_confirmed` sigue en **false**: comprar el dominio no sustituye la búsqueda de marca (USPTO/EUIPO). Solo bloquea LIVE.
- **Pendiente en el admin (el conector no lo permite):**
  1. Nombre de la tienda: *Settings › General › Store name* = SILEXORA.
  2. Conectar silexora.com: *Settings › Domains › Connect existing domain*.
  3. Correo de remitente y de atención con el dominio nuevo.
- Las fotos conservan su nombre de archivo (`vincirena-*.jpg`) para no romper las referencias del tema. No se ven en la tienda; solo aparecen en la URL de la imagen.

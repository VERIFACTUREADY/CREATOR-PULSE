# Prompt para una sesión nueva de Claude Code · Instalación privada en Shopify (V2.2)

Copia todo lo que hay debajo de la línea y pégalo en una sesión **nueva** de Claude Code abierta sobre el repositorio `VERIFACTUREADY/CREATOR-PULSE`, rama `claude/tienda-descanso-prototipo`, con el conector de Shopify ya autorizado.

---

Eres el responsable técnico de instalar en mi tienda Shopify, **en privado y sin publicar**, el tema y la estructura de una tienda de dropshipping que ya está construida y probada en local. Trabaja de forma autónoma, pero respeta al pie de la letra las prohibiciones. Respóndeme en español.

## 1. Contexto (léelo antes de tocar nada)

- Repositorio: `VERIFACTUREADY/CREATOR-PULSE`, rama **`claude/tienda-descanso-prototipo`**. Es una rama huérfana que solo contiene este proyecto.
- Proyecto: tienda para **EE. UU.** (inglés de EE. UU., USD) sobre el tema gratuito **Dawn 16.0.0** personalizado. Producto candidato: férula bucal antirronquidos ajustable (proveedor AliExpress `1005012312929450`). Marca **VINCIRENA, provisional** (pendiente de búsqueda de marca y dominio).
- Versión actual: **V2.2**. Estado entregado: **PREVIEW_COMERCIAL**, `noindex` activado, frase LIVE vacía, marca sin confirmar, país del vendedor pendiente. **NO-GO para LIVE.**
- Documentos que debes leer primero, en este orden:
  1. `docs/V22_INSTALACION_Y_E2E_SHOPIFY.md`: tu guion principal.
  2. `docs/V22_CHANGELOG.md`: qué se corrigió en V2.2.
  3. `docs/11_METACAMPOS_Y_CONFIG.md`: la tabla V2.1 de páginas y menús (arriba del todo) es la vigente; el resto en español es histórico.
  4. `docs/V22_MIGRACION_METACAMPOS.md`: definiciones de los metacampos `regulatory_us`.
  5. `docs/V22_FDA_DOCUMENTOS_Y_VALIDACIONES.md`: por qué no hay venta en EE. UU.
  6. `README.md` y `README_COMERCIAL.md`.
- Tema listo para subir: `dist/tema-descanso-dawn.zip`. El código fuente está en `theme/`.
- La revisión sanitaria **europea** que confirmó el titular **no equivale a una autorización de la FDA**. No hay ningún documento FDA disponible.

## 2. Prohibiciones (no negociables)

- **No publicar** el tema ni sustituir el tema actual.
- **No quitar la contraseña** de la tienda.
- **No activar pagos**, no cambiar a LIVE y no escribir la frase `VENTA REAL AUTORIZADA`.
- No comprar dominios, apps ni suscripciones. No instalar píxeles (Meta, Google, TikTok) ni apps de terceros.
- **No inventar** precios, fotos, reseñas, testimonios, certificaciones, plazos, resultados ni datos regulatorios. Los metacampos del producto real se quedan **vacíos**. La web muestra ⟦PENDING⟧ a propósito.
- No poner ningún producto en estado **Active**. Todo va en **Draft**.
- No cambiar mercados, impuestos, envíos ni el nombre de la tienda sin preguntarme.
- Si una acción no se puede deshacer o no estás seguro, **pregúntame antes**.

## 3. Tareas

**Paso 0 · Comprobaciones (solo lectura)**
- `get-shop-info`: nombre, dominio, plan, moneda, país.
- Consulta los temas existentes (`themes`) y cuál es el MAIN.
- Comprueba si la contraseña está activada. Si no lo está, **para y avísame** antes de seguir.
- Comprueba qué productos, páginas y menús existen, para no duplicar nada.
- Dame un resumen. Si la moneda no es USD, avísame, pero no la cambies.

**Paso 1 · Subir el tema SIN publicar**
- Opción preferida: `themeCreate` con `role: UNPUBLISHED`. Necesita una URL pública del ZIP. Si no hay una URL pública fiable, pídeme que lo suba yo a mano (*Online Store › Themes › Add theme › Upload zip* → `dist/tema-descanso-dawn.zip`, sin pulsar Publish) y que te diga el nombre del tema.
- Alternativa, si te lo autorizo: crear un tema sin publicar y subir los archivos de `theme/` con `themeFilesUpsert` por lotes. Solo está permitido en temas no publicados.
- Verifica en el tema subido que `config/settings_data.json` tiene: `ds_store_mode = preview_comercial`, `ds_noindex = true`, `ds_live_confirmation = ""`, `ds_brand_name = VINCIRENA`, `ds_brand_confirmed = false`, `ds_market = us`, `ds_seller_country = ""`.

**Paso 2 · Definiciones de metacampos de producto** (sin valores)
- `commercial`: `price_confirmed` (boolean), `compare_at_verified` (boolean), `short_benefit` (single line), `what_is` (rich text), `how_to_steps` (list de single line), `includes` (rich text), `delivery_window` (single line), `for_whom` (rich text), `features` (rich text), `care` (rich text).
- `compliance`, campos compartidos: `manufacturer_legal_name` (single line), `model_reference` (single line), `materials` (multi line), `lot_traceability` (single line).
- `compliance`, campos UE (se conservan para trazabilidad; en EE. UU. no cuentan): `intended_purpose`, `ifu_es`, `warnings_es`, `contraindications_es`, `eu_declaration_ref`, `economic_operator`, `claim_approval_version`.
- `regulatory_us`: `fda_510k_number`, `fda_product_code`, `indications_for_use`, `ifu_en`, `warnings_en`, `contraindications_en`, `us_importer_of_record`, `fda_registration_listing`, `ftc_claims_review`, `human_verification`. Usa los tipos de `docs/V22_MIGRACION_METACAMPOS.md`.
- Revisa en `theme/` cómo se lee cada campo (`.value`, `metafield_tag`) para elegir un tipo compatible. Si dudas, usa el tipo que indica la documentación.

**Paso 3 · Páginas** (contenido vacío; el texto lo pone la plantilla)
Crea estas 14 páginas **ocultas o sin publicar en el canal si es posible**, cada una con su `templateSuffix`:

| Título | Handle | Plantilla |
|---|---|---|
| How it works | `how-it-works` | `how-it-works` |
| The product | `the-product` | `the-product` |
| Use & safety | `use-and-safety` | `use-and-safety` |
| Frequently asked questions | `faq` | `faq` |
| About us | `about` | `about` |
| Contact | `contact` | `contact-us` |
| Shipping policy | `shipping` | `shipping` |
| Return policy | `returns` | `returns` |
| Privacy Policy | `privacy` | `privacy` |
| Terms of Service | `terms` | `terms` |
| Company information | `company-information` | `company-information` |
| Accessibility | `accessibility` | `accessibility` |
| Worried about your snoring? | `landing-snoring` | `landing-snoring` |
| Sleeping as a couple | `landing-partners` | `landing-partners` |

Comprueba antes en `theme/templates/` que cada plantilla `page.<sufijo>.json` existe.

**Paso 4 · Menús**
- `main-menu`: The product (`/products/adjustable-mouthpiece`) · How it works · Use & safety · FAQ.
- `footer`: About us · Contact · Shipping policy · Return policy · Accessibility.
- `legal` (nuevo): Privacy Policy · Terms of Service · Company information.
- Si `main-menu` o `footer` ya existen con enlaces de Shopify por defecto, **enséñame qué hay antes de sustituirlos**.

**Paso 5 · Producto real en borrador**
- Título «Adjustable Mouthpiece», handle **`adjustable-mouthpiece`**, estado **DRAFT**, plantilla `product`.
- Sin precio real: si Shopify obliga a poner uno, usa 0 y dímelo. Sin fotos, sin precio tachado, sin descripción inventada.
- Metacampos **vacíos**.

**Paso 6 · Verificación y enlace**
- Dame el enlace de vista previa del tema sin publicar (`https://<tienda>/?preview_theme_id=<id>`) y el del editor del tema.
- Dime qué debo comprobar a mano: el aviso «Commercial preview», el ⟦PENDING⟧, el botón «Add to cart» desactivado, que en el código fuente no aparezca `action="/cart/add"` y que aparezca `noindex`.
- No ejecutes el bloque 4 (E2E con pagos de prueba) de `V22_INSTALACION_Y_E2E_SHOPIFY.md` en esta tienda. Si quiero hacerlo, te lo pediré en una **tienda de desarrollo**.
- Productos de prueba A y B (bloques 1–3 del guion): créalos **solo si te lo confirmo**, en Draft y con el texto `TEST VALUE – NOT REAL`.

## 4. Cómo trabajar

- Antes de cada mutación GraphQL, consulta el esquema con la herramienta de esquema. **No adivines campos ni IDs**: búscalos primero.
- Agrupa las mutaciones para pedirme el menor número de confirmaciones posible, pero de una en una si son destructivas.
- Si algo falla, dime el error exacto y qué propones. No lo esquives con atajos que rompan las prohibiciones.
- Al terminar, añade al repositorio un registro `qa/shopify-real/2026-10-XX/INSTALACION.md` con lo que hiciste: IDs creados, qué quedó pendiente y qué no se pudo hacer. Haz commit y push a `claude/tienda-descanso-prototipo` (`git push -u origin claude/tienda-descanso-prototipo`).
- Resumen final en español: qué se hizo, enlaces, qué tengo que revisar yo y estado (debe seguir siendo **PREVIEW_COMERCIAL · tema sin publicar · contraseña activa · NO-GO LIVE**).

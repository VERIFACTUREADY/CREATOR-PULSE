# V2.2 · Migración de metacampos UE → EE. UU. (sin reutilización engañosa)

> **Hallazgo P0-1 (auditoría V2.1):** la V2.1 aceptaba como «completo para EE. UU.» un producto con los campos **europeos** rellenos (`compliance.ifu_es`, `warnings_es`, `contraindications_es`, `eu_declaration_ref`, `economic_operator`) y la documentación pedía guardar el número 510(k) en `eu_declaration_ref` y el IFU inglés en `ifu_es`. **Verificado** en el código V2.1 (`snippets/ds-product-missing.liquid`, `sections/ds-product-details.liquid`, `docs/11_METACAMPOS_Y_CONFIG.md:26`). **Corregido** en V2.2.

## Regla

1. Cada mercado lee **solo sus campos**. El ajuste *Estado de la tienda › Mercado regulatorio* (`ds_market`, por defecto `us`) decide cuáles.
2. **No hay copia automática** de UE a EE. UU. Un documento europeo (declaración UE, IFU en castellano, operador económico UE) **no** acredita nada ante la FDA ni la FTC.
3. Los campos europeos **se conservan** (no se borran ni se renombran) para la trazabilidad del expediente UE que el titular ya revisó. En el mercado `us` no se muestran ni cuentan para la compuerta.
4. Rellenar un campo **no es** verificarlo. La compuerta exige además `regulatory_us.human_verification` (referencia a un registro firmado por una persona, ver `V22_FDA_DOCUMENTOS_Y_VALIDACIONES.md`), y ni siquiera eso sustituye la revisión: es un recordatorio para que exista. La decisión GO/NO-GO sigue siendo humana.

## Tabla de correspondencia

| Campo V2.1 (namespace `compliance`) | Uso en V2.1 (incorrecto) | Destino V2.2 | Qué hacer |
|---|---|---|---|
| `manufacturer_legal_name` | Compartido | `compliance.manufacturer_legal_name` (sin cambios) | Debe coincidir con el titular del 510(k) o con el fabricante que figura en el registro FDA |
| `model_reference` | Compartido | `compliance.model_reference` (sin cambios) | Modelo exacto cubierto por la autorización; UDI-DI si aplica |
| `materials` | Compartido | `compliance.materials` (sin cambios) | — |
| `lot_traceability` | Compartido | `compliance.lot_traceability` (sin cambios) | — |
| `intended_purpose` | Finalidad UE usada como «Indications for use» | **Se conserva solo para UE** · EE. UU.: `regulatory_us.indications_for_use` | Copiar **a mano** el texto literal del formulario FDA 3881 del 510(k), no el de la UE |
| `ifu_es` | IFU inglés guardado en un campo «_es» | **Se conserva solo para UE** · EE. UU.: `regulatory_us.ifu_en` | IFU / etiquetado en inglés coherente con las indicaciones autorizadas |
| `warnings_es` | Ídem | Solo UE · EE. UU.: `regulatory_us.warnings_en` | — |
| `contraindications_es` | Ídem | Solo UE · EE. UU.: `regulatory_us.contraindications_en` | — |
| `eu_declaration_ref` | Rotulado como «FDA 510(k)» | Solo UE · EE. UU.: `regulatory_us.fda_510k_number` **y** `regulatory_us.fda_product_code` | El número K###### y el código de producto (p. ej. LRK/LQZ, **a confirmar** en la base de datos FDA) |
| `economic_operator` | Rotulado como «importador de EE. UU.» | Solo UE · EE. UU.: `regulatory_us.us_importer_of_record` + `regulatory_us.fda_registration_listing` | — |
| `claim_approval_version` | Aprobación de claims | Solo UE · EE. UU.: `regulatory_us.ftc_claims_review` | Versión de `04_CLAIMS_APPROVAL_US.csv` revisada con el expediente de sustanciación |
| — | — | `regulatory_us.human_verification` (nuevo) | Referencia al registro de verificación humana (quién, cuándo, qué documentos, resultado) |

## Definición de los metacampos `regulatory_us` (Ajustes › Datos personalizados › Productos)

| Clave | Tipo recomendado | Contenido | Fuente obligatoria |
|---|---|---|---|
| `fda_510k_number` | Texto de una línea | Número 510(k) (K######) que cubre **este** modelo | Carta de autorización de la FDA + base de datos 510(k) |
| `fda_product_code` | Texto de una línea | Código de producto FDA de 3 letras | Carta 510(k) / base de datos de clasificación |
| `indications_for_use` | Texto de varias líneas | Indicaciones literales, incluida la condición OTC o de prescripción | Formulario FDA 3881 del 510(k) |
| `ifu_en` | Texto enriquecido | Instrucciones de uso en inglés | Etiquetado del fabricante coherente con el 510(k) |
| `warnings_en` | Texto enriquecido | Advertencias | Ídem |
| `contraindications_en` | Texto enriquecido | Contraindicaciones | Ídem |
| `us_importer_of_record` | Texto de varias líneas | Importador (initial importer / importer of record) | Contrato / registro FDA |
| `fda_registration_listing` | Texto de una línea | Nº de registro del establecimiento y del listado del dispositivo | Base de datos FDA de registro y listado |
| `ftc_claims_review` | Texto de una línea | Versión del CSV de claims revisada y fecha | Revisión con asesoría |
| `human_verification` | Texto de una línea | ID del registro de verificación humana (p. ej. `VER-US-2026-001 · nombre · fecha`) | Registro firmado fuera de Shopify |

Los valores no se inventan ni se rellenan con «N/A» para pasar la compuerta. Si un documento no existe, el campo queda vacío y la compra sigue cerrada.

## Comportamiento verificado (pruebas)

`tools/qa/gate-tests.mjs` (V2.2) usa dos productos:

- **A** · completo para EE. UU. (datos de PRUEBA): apto en `us`, **no apto** en `eu` (le faltan los documentos UE).
- **B** · solo documentación UE (la situación real del titular): **no apto** en `us`; el aviso nombra «FDA clearance details», «English instructions and warnings», «US importer and FDA registration», «FTC claims review» y «human regulatory verification record». Apto en `eu`.
- Un producto con documentos UE y todo lo de EE. UU. salvo el 510(k) → no apto.
- Quitar cualquiera de los 10 campos `regulatory_us` o de los 4 compartidos → no apto.

`tools/qa/purchase-routes-tests.mjs` comprueba lo mismo en las rutas de compra (ver `V22_CHANGELOG.md`).

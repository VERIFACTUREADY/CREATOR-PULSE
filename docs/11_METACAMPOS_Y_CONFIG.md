# 11 · Instalación en Shopify, metacampos y configuración

> No he tenido acceso a ninguna tienda Shopify (DP-18). Estos pasos son para el titular o para una sesión posterior con acceso de colaborador. **No publicar el tema en la tienda en directo, no activar pagos y no quitar la contraseña.**

## 1. Subir el tema sin publicarlo

1. Admin de Shopify › Tienda online › Temas › **Añadir tema › Subir archivo zip** › `dist/tema-descanso-dawn.zip`.
2. El tema queda **sin publicar**. Revisadlo con «Personalizar» o con «Vista previa».
3. Alternativa con Shopify CLI (gratuito): `shopify theme push --unpublished --path theme` y `shopify theme check --path theme`.
4. Preferencias › **Protección con contraseña: ACTIVADA** (en las tiendas nuevas viene así por defecto).

## 2. Páginas a crear (Tienda online › Páginas)

Cada página se crea con su **título**, el **contenido vacío** (lo aporta la plantilla) y su **plantilla** asignada:

| Título | Identificador (URL) | Plantilla |
|---|---|---|
| Cómo funciona | `como-funciona` | `page.como-funciona` |
| El producto | `el-producto` | `page.el-producto` |
| Uso y seguridad | `uso-y-seguridad` | `page.uso-y-seguridad` |
| Preguntas frecuentes | `preguntas-frecuentes` | `page.preguntas-frecuentes` |
| Quiénes somos | `quienes-somos` | `page.quienes-somos` |
| Contacto | `contacto` | `page.contacto` |
| Envíos | `envios` | `page.envios` |
| Devoluciones y garantía | `devoluciones` | `page.devoluciones` |
| Aviso legal | `aviso-legal` | `page.aviso-legal` |
| Política de privacidad | `privacidad` | `page.privacidad` |
| Política de cookies | `cookies` | `page.cookies` |
| ¿Te preocupan tus ronquidos? (V2) | `landing-ronquidos` | `page.landing-ronquidos` |
| Descanso en pareja (V2) | `landing-pareja` | `page.landing-pareja` |

Los textos se editan en **Personalizar** (cada sección y bloque es editable) o en `theme/templates/page.*.json`.

## 3. Menús (Tienda online › Navegación)

| Identificador | Enlaces |
|---|---|
| `main-menu` | El producto (`/products/dispositivo-bucal`) · Cómo funciona · Uso y seguridad · Preguntas |
| `footer` | Quiénes somos · Contacto · Envíos · Devoluciones y garantía |
| `legal` (crear nuevo) | Aviso legal · Privacidad · Cookies |

## 4. Ajustes del tema › «Estado de la tienda» (V2)

| Ajuste | Valor entregado |
|---|---|
| Estado | **PREVIEW_COMERCIAL** (venta visible, compra desactivada) |
| Confirmación para LIVE | Vacía. Solo con orden expresa: `VENTA REAL AUTORIZADA` |
| Oferta: envío, devoluciones, atención, pago | Vacíos (⟦PENDIENTE⟧) hasta tener datos confirmados |

### 4b. Ajustes heredados de la V1 (modo prototipo)

| Ajuste | Valor durante el prototipo |
|---|---|
| Aviso «Prototipo privado» | Activado |
| noindex | Activado |
| Marcadores de pendiente | Activado |
| Titular: razón social, NIF, domicilio, email, registro | Vacíos hasta tener datos reales (la web muestra «[Pendiente: …]») |
| Fecha de última revisión | Actualizar con cada revisión de contenido |

## 5. Metacampos del producto (Ajustes › Datos personalizados › Productos)

Namespace `compliance`. **Ningún campo se rellena sin documento.** Si falta uno solo, la compuerta mantiene la compra oculta aunque se active el comercio.

| Clave | Tipo recomendado | Contenido | Fuente obligatoria |
|---|---|---|---|
| `manufacturer_legal_name` | Texto de una línea | Nombre legal y dirección del fabricante | DoC / etiqueta |
| `model_reference` | Texto de una línea | Modelo, referencia y UDI-DI si procede | DoC / etiqueta |
| `intended_purpose` | Texto de varias líneas | Finalidad prevista literal | IFU |
| `materials` | Texto de varias líneas | Materiales | Ficha del fabricante |
| `ifu_es` | Texto enriquecido | Instrucciones de uso, ajuste y limpieza en castellano | IFU oficial |
| `warnings_es` | Texto enriquecido | Advertencias | IFU |
| `contraindications_es` | Texto enriquecido | Contraindicaciones | IFU |
| `eu_declaration_ref` | Texto de una línea / archivo | Referencia de la declaración UE de conformidad | DoC firmada |
| `economic_operator` | Texto de varias líneas | Importador, distribuidor y representante UE | Contratos / criterio regulatorio |
| `lot_traceability` | Texto de una línea | Cómo se rastrea el lote | Proveedor |
| `delivery_window` | Texto de una línea | Plazo real de entrega | Cotización firmada |
| `claim_approval_version` | Texto de una línea | Versión aprobada de `04_CLAIMS_APPROVAL.csv` | Aprobación del titular y del asesor |

## 5b. Metacampos comerciales (V2, namespace `commercial`)

| Clave | Tipo recomendado | Contenido | ¿Obligatorio para LIVE? |
|---|---|---|---|
| `price_confirmed` | Verdadero/falso | El titular confirma que el precio de Shopify es el definitivo | Sí |
| `compare_at_verified` | Verdadero/falso | Solo si el precio tachado es un precio anterior real | No (sin él no se muestra el tachado) |
| `short_benefit` | Texto de una línea | Beneficio aprobado en la ficha comercial | Sí |
| `what_is` | Texto enriquecido | Qué es | Sí |
| `how_to_steps` | Lista de textos de una línea (o texto de varias líneas, un paso por línea) | Cómo se usa | Sí |
| `includes` | Texto enriquecido | Qué incluye el pedido | Sí |
| `delivery_window` | Texto de una línea | Plazo real de entrega | Sí |
| `for_whom` | Texto enriquecido | Para quién está pensado | No |
| `features` | Texto enriquecido | Características | No |
| `care` | Texto enriquecido | Cuidados y limpieza | No |

Además, para LIVE el producto necesita **al menos una foto** y estar **disponible**. `compliance.delivery_window` ya no se usa (pasa a `commercial`).

## 6. Producto (cuando proceda)

- Crear el producto en estado **Borrador**. No ponerlo a la venta en el canal Tienda online mientras dure el NO-GO.
- Identificador (handle): `dispositivo-bucal`. Título: el nombre comercial aprobado por el titular.
- Sin precio comparativo, sin «quedan X», sin reseñas y sin fotos sin licencia.
- Plantilla: `product` (incluye la sección «DS · Datos del producto»).

## 7. Privacidad y cookies (gratuito, nativo)

- Ajustes › **Privacidad del cliente** › Banner de cookies: activarlo para la UE/EEE, con «Aceptar» y «Rechazar» igual de visibles (AEPD, S24).
- **No instalar** Meta Pixel, Google Ads, TikTok Pixel ni apps de analítica de marketing (Estudio §17).
- Formularios: solo el de contacto nativo, sin datos de salud.
- Ajustes › Políticas: Shopify genera sus propias políticas. Que **no** contradigan las páginas del tema, y que las revise la asesoría.

## 8. Qué NO tocar sin autorización expresa

Dominios, pagos, impuestos, envíos, mercados, apps, publicación del tema y eliminación de la contraseña.

# V2.2 · EE. UU.: documentos y validaciones humanas que faltan

> **La revisión europea que confirmó el titular NO equivale a una autorización de la FDA.** Este documento no resuelve la autorización estadounidense: enumera lo que hay que conseguir y quién debe validarlo. Ningún campo del tema, ninguna casilla y ningún booleano sustituye esa verificación.
>
> **Límite de verificación:** el proxy de este entorno bloquea `fda.gov`, `accessdata.fda.gov` y `ecfr.gov`. Las referencias normativas siguientes proceden del conocimiento general del asistente y **no se han contrastado en la fuente**. Debe confirmarlas un consultor regulatorio de EE. UU. Esto no es asesoramiento jurídico ni regulatorio.

## Punto de partida (según la información disponible)

- Producto: dispositivo intraoral antirronquidos (férula de avance mandibular ajustable), proveedor AliExpress `1005012312929450`.
- Fabricante, modelo exacto y documentación FDA: **desconocidos**.
- Encuadre probable (a confirmar): 21 CFR 872.5570, *intraoral devices for snoring and/or obstructive sleep apnea*, **clase II**, que requiere **510(k)**. La venta sin receta (OTC) solo es posible si el 510(k) concreto la autoriza.
- Consecuencia: hasta tener los documentos de la tabla, el producto **no puede venderse** en EE. UU. y la tienda debe seguir en PREVIEW_COMERCIAL.

## A. Documentos que hay que obtener

| # | Documento | De quién | Qué debe demostrar | Metacampo que alimenta |
|---|---|---|---|---|
| A1 | **Carta de autorización 510(k)** (SE letter) | Fabricante / titular del 510(k) | Que existe un 510(k) que cubre **este modelo** (mismo diseño, materiales y fabricante) | `regulatory_us.fda_510k_number`, `fda_product_code` |
| A2 | **Formulario FDA 3881 · Indications for Use** del mismo 510(k) | Ídem | Indicación exacta y si es **OTC** o **Rx** (prescription use) | `regulatory_us.indications_for_use` |
| A3 | Registro del establecimiento + **listado del dispositivo** (FURLS) | Fabricante extranjero | Que el fabricante está registrado y el dispositivo listado bajo ese 510(k) | `regulatory_us.fda_registration_listing` |
| A4 | Designación del **US Agent** del fabricante extranjero | Fabricante | Obligatoria para establecimientos extranjeros | (expediente) |
| A5 | Identidad del **initial importer / importer of record** y su registro si procede | Titular / agente de aduanas | Quién importa y responde ante FDA y CBP | `regulatory_us.us_importer_of_record` |
| A6 | **Etiquetado e IFU en inglés** del fabricante | Fabricante | Coherentes con A2 (sin indicaciones adicionales), advertencias y contraindicaciones | `regulatory_us.ifu_en`, `warnings_en`, `contraindications_en` |
| A7 | **UDI** y alta en **GUDID**, si aplica a la clase y fecha | Fabricante (labeler) | Identificación del dispositivo | `compliance.model_reference` |
| A8 | Procedimiento de **notificación de incidentes (MDR, 21 CFR 803)** y de quejas | Fabricante + importador | Quién notifica y cómo se tramitan las quejas | (expediente) |
| A9 | **Expediente de sustanciación de claims** (FTC *Health Products Compliance Guidance*) | Titular + asesoría | Evidencia competente y fiable para **cada** afirmación de `04_CLAIMS_APPROVAL_US.csv` | `regulatory_us.ftc_claims_review` |
| A10 | Evaluación **California Prop 65** (materiales) | Fabricante / laboratorio | Si hace falta advertencia | (expediente) |
| A11 | **Seguro de responsabilidad civil de producto** con cobertura en EE. UU. | Aseguradora | Cobertura vigente | (expediente) |
| A12 | Comprobación de que el modelo de **dropshipping** (envío directo desde el proveedor) es compatible con A3–A5 | Consultor regulatorio + agente de aduanas | Que no se importa un dispositivo sin el importador ni el listado correctos | (expediente) |

## B. Validaciones humanas (no automatizables)

| # | Validación | Quién | Cómo se documenta |
|---|---|---|---|
| B1 | Consultar el 510(k) en la **base de datos pública de la FDA** y comprobar que coinciden titular, modelo, código de producto e indicaciones con A1/A2 y con el producto que envía el proveedor | Persona designada por el titular | Captura con fecha + nombre en el registro de verificación |
| B2 | Comprobar el **registro y listado** (A3) en la base de datos de la FDA | Ídem | Ídem |
| B3 | Comparar una **unidad física** (muestra) con la etiqueta, el IFU y el 510(k): modelo, materiales, marcado | Titular | Fotos de la muestra + acta |
| B4 | Revisar los textos de la tienda (ficha, landings, FAQ, anuncios futuros) contra A2 y A9: **ninguna indicación más amplia** que la autorizada | Asesoría regulatoria / jurídica de EE. UU. | Versión aprobada de `04_CLAIMS_APPROVAL_US.csv` |
| B5 | Dictamen escrito de un **consultor regulatorio de EE. UU.** sobre el conjunto A1–A12 | Consultor | Informe firmado |
| B6 | Revisión fiscal y de comercio: sales tax (nexus), aranceles y reglas de importación de envíos de bajo valor vigentes | Asesoría fiscal / agente de aduanas | Informe |

## C. Registro de verificación (lo que referencia `regulatory_us.human_verification`)

Se guarda **fuera de Shopify** (documento firmado). Contenido mínimo:

```
ID: VER-US-AAAA-NNN
Producto / modelo / proveedor:
Documentos revisados (A1…A12) con versión y fecha:
Comprobaciones B1…B6: resultado, persona, fecha, evidencia:
Indicaciones autorizadas (literal de A2) y si es OTC:
Conclusión: APTO / NO APTO para venta en EE. UU.
Firma:
```

El metacampo solo guarda el ID. **El tema no puede comprobar el contenido del registro:** que el campo esté relleno solo indica que alguien afirma que existe. Por eso, además de la compuerta técnica, LIVE exige la orden expresa del titular (`VENTA REAL AUTORIZADA`) y la lista GO/NO-GO de `V21_GO_NO_GO_EEUU.md`.

## D. Estado actual

| Bloque | Estado |
|---|---|
| A1–A12 | **Ninguno disponible** |
| B1–B6 | **Ninguna realizada** |
| Decisión | **NO-GO para LIVE en EE. UU.** |

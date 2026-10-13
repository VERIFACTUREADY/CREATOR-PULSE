# V2.1 · GO / NO-GO para el mercado de EE. UU.

**Estado: 🔴 NO-GO para LIVE.** El tema queda en PREVIEW_COMERCIAL, sin publicar.

> **Por qué este documento:** el titular dio por cerrada la verificación sanitaria **para España/UE**. Al cambiar el mercado principal a EE. UU. cambia el marco aplicable (FDA y FTC en lugar de MDR y AEMPS). No se reabre el análisis europeo. Este documento solo enumera lo que **EE. UU.** exige y que todavía no consta en el proyecto.
>
> **Límite de verificación:** desde este entorno no se pueden abrir fda.gov, ecfr.gov ni ftc.gov (proxy restringido). Lo que sigue es mi conocimiento de la normativa, **no contrastado en fuente oficial en esta sesión**. Debe validarlo un asesor regulatorio y un abogado de EE. UU.

## 1. Producto (FDA) — 🔴 bloqueante
| Punto | Qué entiendo | Qué necesitamos |
|---|---|---|
| Clasificación | Los dispositivos intraorales para el ronquido y/o la apnea obstructiva están clasificados por la FDA como **Clase II** (21 CFR 872.5570, controles especiales). Por lo general necesitan una notificación previa **510(k)**. | Número 510(k) del **modelo exacto** y comprobación en la base de datos de la FDA |
| Venta sin receta | Algunos de estos dispositivos están autorizados solo con receta y otros como OTC (venta libre). | Confirmar que la autorización del modelo cubre la **venta OTC online** |
| Etiquetado | Etiquetado e instrucciones en inglés conformes con la autorización | IFU y etiquetas del fabricante |
| Operadores | Registro del establecimiento y listado del dispositivo; importador | Confirmar el rol de cada parte |

Wording: «FDA cleared» solo si existe 510(k), y nunca «FDA approved». La web ya explica la diferencia, en un texto educativo pendiente de revisión.

## 2. Publicidad y venta (FTC) — 🔴 bloqueante para anuncios
- **Afirmaciones de salud:** necesitan evidencia científica competente y fiable (Health Products Compliance Guidance de la FTC). Los claims prohibidos de la matriz siguen bloqueados y `run-qa` los busca también en inglés.
- **Reseñas y testimonios:** la regla de la FTC sobre reseñas y testimonios (2024) prohíbe las reseñas falsas o compradas. El proyecto no publica ninguna.
- **Envíos:** la Mail, Internet, or Telephone Order Merchandise Rule obliga a enviar en el plazo anunciado (o en 30 días si no se anuncia) o a ofrecer la cancelación. Ya está recogido en la plantilla de envíos.
- **Garantía escrita:** si se ofrece, se aplica la Magnuson-Moss Warranty Act. Está como pendiente en la plantilla de devoluciones.

## 3. Impuestos e importación — 🔴 bloqueante para vender
- *Sales tax* por estado según nexus físico o económico. Se calcula en el checkout (Shopify Tax u otro); asesor fiscal.
- Importación: importador de registro, aranceles y el régimen de los envíos de bajo valor (*de minimis*), que ha cambiado recientemente. Hay que confirmarlo con un agente de aduanas antes de rellenar la partida 6 de la hoja.

## 4. Privacidad y accesibilidad — 🟡 antes de publicar
- Leyes estatales de privacidad (CCPA/CPRA de California y otras): aviso de privacidad, derechos y, si se comparten datos para publicidad, el enlace «Your Privacy Choices» y respeto de la señal Global Privacy Control. Hoy el tema no incluye píxeles ni cookies de publicidad.
- Accesibilidad: hay declaración de accesibilidad (objetivo WCAG 2.2 AA). axe y Lighthouse dan 0 errores en local; falta la prueba con lectores de pantalla.
- Proposition 65 (California): valorar si los materiales requieren aviso.

## 5. Comercial y operativo — 🔴 bloqueante
Datos de `V21_DATOS_NECESARIOS.md` (precio en USD, fotos, ficha en inglés, envío, devoluciones, atención, pago, entidad) y el checkout de prueba en Shopify (`V21_PLAN_PRUEBAS_SHOPIFY.md`).

## Regla de activación
LIVE solo con: este documento en verde con evidencia, `prelaunch-check.mjs <URL> --expect-indexable` con 0 incidencias, checkout de prueba documentado y **orden expresa del titular**. Claude no publica ni activa pagos.

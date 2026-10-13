# 03 · GO / NO-GO comercial

> **Actualización V2 (13/10/2026):** el titular declara **cerrada** la comprobación sanitaria (secciones 1–4 de este documento). Por instrucción expresa, la V2 no reabre ese análisis. La evidencia no se ha incorporado al repositorio; conviene archivarla en `12_REGISTRO_EVIDENCIAS.md`. Siguen abiertos los requisitos comerciales y operativos (datos de oferta, fotos, checkout de prueba, textos legales finales) y **la activación LIVE requiere orden expresa**. La compuerta del tema ahora tiene tres estados: ver `V2_CHANGELOG.md` (C-03).

**Estado a 13/10/2026: 🔴 NO-GO** — prototipo privado. No se puede vender, cobrar, anunciar ni publicar la tienda.

> Este documento organiza los requisitos. **No es un dictamen jurídico ni sanitario.** Las citas normativas proceden de los informes del titular y **no han sido contrastadas por Claude con el BOE** (acceso bloqueado desde este entorno). Cada requisito debe cerrarse con evidencia y firma de quien la valida.

## Regla de cierre

El interruptor `Comercio habilitado` del tema **solo** puede activarse cuando **todas** las filas críticas estén en `PASS`, con evidencia enlazada, y el titular lo autorice por escrito. Una sola fila en `UNKNOWN` o `FAIL` = NO-GO. Además, el interruptor del tema es una capa visual: **la protección real es** (a) tienda con contraseña, (b) producto en estado *borrador* o no publicado en el canal Tienda online, (c) pagos sin activar.

## 1. PUNTO DECISIVO · RD 192/2023, artículo 24.5 — venta telemática

| Campo | Contenido |
|---|---|
| Texto citado por los informes | Prohíbe la venta por internet de productos sanitarios sujetos a prescripción, incluidos los productos a medida y los que **requieren adaptación individualizada**. El art. 26 añade requisitos a establecimientos que venden productos de adaptación individualizada. |
| Por qué es crítico | La férula se anuncia como «ajustable». Ajustable **no implica** automáticamente «adaptación individualizada» en sentido legal, pero tampoco lo descarta. Si el fabricante prevé ajuste por profesional, termoajuste supervisado o prescripción, la venta online podría estar prohibida. |
| Qué necesitamos | 1) Finalidad prevista e IFU del fabricante del modelo exacto. 2) Procedimiento de ajuste descrito por el fabricante. 3) Dictamen escrito de especialista en productos sanitarios o consulta a la autoridad (AEMPS / consejería autonómica). |
| Pregunta literal a formular | «¿El modelo [referencia exacta], con la finalidad prevista [texto del fabricante], encaja entre los productos sanitarios sujetos a prescripción o adaptación individualizada a efectos del RD 192/2023, y cabe su venta al público exclusivamente online por [razón social]?» |
| Estado | 🔴 **UNKNOWN** |
| Evidencia | — |
| Validado por / fecha | — |
| Si FAIL | No vender este SKU online. Conservar marca y contenidos educativos; evaluar otro producto (Estudio §21). |

## 2. AEMPS / RECOPS y operadores económicos

| Requisito | Evidencia esperada | Estado |
|---|---|---|
| Identificación del rol (importador / distribuidor) de vuestra empresa en la cadena real | Criterio escrito | 🔴 UNKNOWN |
| Obligación de comunicación/registro en RECOPS (la AEMPS actualizó la plataforma el 02/10/2026 según S19; distingue agentes económicos y puntos de venta) | Criterio escrito + justificante si aplica | 🔴 UNKNOWN |
| Fabricante legal y representante autorizado UE (si el fabricante está fuera de la UE) | Nombre, dirección, documentos | 🔴 UNKNOWN |
| Importador UE responsable de vigilancia, trazabilidad, quejas y retiradas | Contrato / confirmación | 🔴 UNKNOWN |
| Marca propia o reetiquetado → posible rol de fabricante (art. 16 MDR) | Criterio escrito | 🔴 UNKNOWN — recomendación: **no** reetiquetar |

## 3. Conformidad del producto (Reglamento (UE) 2017/745)

| Requisito | Evidencia esperada | Estado |
|---|---|---|
| Finalidad prevista del fabricante | IFU / etiqueta | 🔴 UNKNOWN |
| Clase MDR | DoC | 🔴 UNKNOWN |
| Declaración UE de conformidad firmada, asociada al modelo exacto | PDF firmado, cotejado con etiqueta y fotos | 🔴 UNKNOWN |
| Certificado de organismo notificado (si la clase lo exige) | Certificado verificable en NANDO/EUDAMED | 🔴 UNKNOWN |
| UDI-DI / Basic UDI-DI cuando proceda | Etiqueta / EUDAMED | 🔴 UNKNOWN |
| Etiquetado e instrucciones en castellano | Muestra física + IFU | 🔴 UNKNOWN |
| Materiales y biocompatibilidad (sin inventar normas ISO) | Documentación del fabricante | 🔴 UNKNOWN |
| Trazabilidad por lote | Sistema del proveedor | 🔴 UNKNOWN |

## 4. Publicidad — RD 1591/2009 art. 38 (vigencia transitoria según RD 192/2023)

| Requisito | Estado |
|---|---|
| Determinar si la web/redes/anuncios constituyen publicidad al público de producto sanitario que requiere **autorización previa autonómica** | 🔴 UNKNOWN |
| Obtener autorización, si aplica, antes de: Meta/Google Ads, influencers, promociones, contenido orgánico de producto | 🔴 UNKNOWN |
| Incluir contraindicaciones/efectos secundarios exigidos en la publicidad | 🔴 Pendiente de IFU |
| No usar recomendaciones de profesionales o autoridades sanitarias | ✅ Aplicado en el prototipo (ninguna aparece) |
| Políticas de Meta/Google sobre salud y personalización | 🔴 Revisar al lanzar; no hay píxeles instalados |

## 5. Comercio, fiscalidad y privacidad

| Requisito | Estado |
|---|---|
| Titular identificado (razón social, NIF, domicilio, contacto) en Aviso legal | 🔴 Placeholders |
| Alta de actividad, IVA (tipo del SKU), Seguridad Social | 🔴 UNKNOWN |
| Importación: quién es importador, IOSS, derecho de 3 € (desde 01/07/2026) | 🔴 UNKNOWN |
| Condiciones de venta, desistimiento 14 días, aplicabilidad art. 103.e (precinto higiénico), garantía legal 3 años | 🔴 Plantillas pendientes de revisión jurídica |
| Política de privacidad y cookies; banner nativo de Shopify con aceptar/rechazar equivalentes | 🔴 Pendiente de configurar en el admin |
| Sin datos de salud en formularios | ✅ Aplicado: el formulario de contacto avisa y no pide datos de salud |
| Sin píxeles ni analítica de marketing antes del consentimiento | ✅ Aplicado: el tema no añade ninguno |

## 6. Operación y finanzas

| Requisito | Estado |
|---|---|
| ≥2 cotizaciones comparables del mismo modelo con coste entregado, plazo y tracking | 🔴 UNKNOWN |
| Contribución prudente ≥ umbral (7–8 €/pedido antes de marketing) | 🔴 UNKNOWN (ver `05_ECONOMIA_UNITARIA.md`) |
| Capital para pedidos, retrasos y reembolsos (50 € ≈ 3 pedidos a 14 €) | 🔴 Insuficiente en escenario base |
| Elegibilidad de la categoría en la pasarela de pagos | 🔴 UNKNOWN |
| Checkout de prueba sin cargos reales, emails transaccionales revisados | 🔴 No realizado |
| Test de garantía, producto dañado, reembolso y queja sanitaria | 🔴 No realizado |
| Fotos con derechos de uso | 🔴 No disponibles |

## 7. Contenido y prototipo

| Requisito | Estado |
|---|---|
| Matriz de claims aprobada (100 % de claims de producto con ID `APROBADO`) | 🔴 0 claims de producto aprobados; ninguno publicado en la web |
| Contenido educativo revisado por profesional sanitario | 🔴 Pendiente (marcado como borrador en la web) |
| Prototipo sin checkout activo | ✅ Verificado en QA local (ver `10_QA_LANZAMIENTO.md`) |
| Auditoría externa del prototipo | 🔴 **Pendiente — obligatoria** |
| Autorización expresa del titular para lanzamiento | 🔴 No concedida |

## Resultado

**NO-GO.** Escenarios posibles (Estudio §1): (A) todo PASS → lanzamiento controlado autorizado; (B) problema logístico/margen → cambiar proveedor o precio; (C) venta online no permitida o producto no conforme → **no lanzar este SKU** y reconducir la marca.

# 01 · Auditoría y clasificación de datos

**Fecha:** 13/10/2026 · **Autor:** Claude Code (prototipo privado) · **Estado del proyecto:** PROTOTIPO PRIVADO — NO AUTORIZADO PARA VENTA NI PUBLICIDAD

## Fuentes leídas (en el orden indicado por `00_LEEME_Entrega_Final.txt`)

| # | Documento | Uso |
|---|---|---|
| 1 | `02_Estudio_Mercado_Ferula_Descanso_Claude.md` (12/10/2026, 767 líneas) | **Prioridad** para investigación, riesgos, mensajes y UX |
| 2 | `06_Informe_Maestro_Claude_Tienda_Descanso.md` (12/10/2026) | Implementación, bloqueos, QA, operaciones |
| 3 | `04_Propuesta_Diseno_Tienda_Descanso_Lectura_Clara.pdf` (11 págs.) | Identidad visual y principios UX |
| 4 | `03_Prompt_Final_Claude_Code.txt` | **Instrucción principal** |
| 5 | `07_Prompt_Inicio_Claude_Code_Descanso.txt` | Solo referencia (subordinado al 4) |
| 6 | `01_…2026.pdf` (37 págs.) y `05_…Descanso.pdf` | Ediciones maquetadas de 1 y 2; recuento de palabras equivalente (≈10.100 y ≈3.900). No se detectó contenido adicional relevante. |

## Limitación de verificación de este entorno

El proxy de red de esta sesión **bloquea boe.es** (error `CONNECT 403` y `ENOTFOUND` al intentarlo el 13/10/2026). Por tanto **ninguna cita normativa ha sido contrastada por Claude contra el texto oficial**: todas las referencias legales de este proyecto proceden de los informes del titular y deben ser verificadas por el asesor competente. Tampoco se ha accedido a AliExpress, competidores, AEMPS ni INE.

## Convención

- **[V] Verificado** — fuente identificada y comprobable (según el informe; Claude no la ha recontrastado salvo indicación).
- **[O] Observado** — característica de una oferta pública, sin auditoría.
- **[H] Hipótesis** — inferencia o juicio comercial sujeto a test.
- **[P] Pendiente** — requiere documento, muestra, cotización o dato primario.
- **[B] Bloqueante** — impide pasar de prototipo a venta o publicidad.

## A. Producto

| ID | Dato | Valor | Clase | Fuente |
|---|---|---|---|---|
| PR-01 | ID AliExpress | `1005012312929450` | V (aportado por fundador) | Estudio §2.1 |
| PR-02 | Descripción comercial | «Adjustable Anti-Snoring Mouthpiece… Bruxism…» | O | S01 (PriceArchive) |
| PR-03 | Formato | Aparato intraoral reutilizable | O | S01 |
| PR-04 | Precio histórico | 10,73 USD el 20/09/2026 | O (no es cotización ni coste entregado) | S01 |
| PR-05 | Fabricante, modelo, materiales, tallas | Desconocidos | **P** | — |
| PR-06 | Finalidad prevista del fabricante | Desconocida | **P / B** | — |
| PR-07 | Marcado CE, DoC UE, clase MDR, organismo notificado | Desconocidos | **P / B** | — |
| PR-08 | ¿Requiere adaptación individualizada / prescripción? | Desconocido | **P / B** | RD 192/2023 art. 24.5 (S17) |
| PR-09 | Instrucciones y advertencias en castellano | No disponibles | **P / B** | — |
| PR-10 | Vida útil / reemplazo | Desconocida | P | — |
| PR-11 | Almacén UE, transportista, plazo | Desconocidos | **P / B** | — |
| PR-12 | Fotos con derecho de uso | No disponibles | **P / B** | — |
| PR-13 | Eficacia específica del SKU | Sin evidencia | **B** para cualquier claim de producto | Estudio §8.3 |
| PR-14 | Ficha directa de AliExpress | No verificable desde la investigación | P | Estudio §2.1 |

## B. Mercado y contexto

| ID | Dato | Clase | Fuente | Nota |
|---|---|---|---|---|
| MK-01 | Población España 49.801.559 (01/07/2026) | V | S10 INE | No es mercado de férulas |
| MK-02 | E-commerce 1T2026 29.643 M€, +15,1 % | V | S11 CNMC | Multisector |
| MK-03 | 56,7 % compró online en 3 meses | V | S12 ONTSI 2025 | No específico |
| MK-04 | TAM/SAM/SOM férulas DTC España | **No existe dato auditable** | — | No inventar |
| MK-05 | Clusters de búsqueda | H | Estudio §3.3 | Sin volúmenes |
| MK-06 | Segmentos A–D | H | Estudio §4 | Pendiente 8–12 entrevistas |
| MK-07 | Página con ~20 anuncios Meta | P (sin URL) | Fundadores | No prueba rentabilidad |

## C. Competencia (observada ≈12/10/2026)

| ID | Oferta | Precio | Clase | Fuente |
|---|---|---|---|---|
| CP-01 | Snorless Blue | 19,99 € | O | S02 |
| CP-02 | Snorless Blue + White | 24,99 € | O | S03 |
| CP-03 | Healthy Bucal (PromoFarma) | 24,19 € | O | S04 |
| CP-04 | Quattroti Dentech Dr Russ | 94,80 € | O | S05 |
| CP-05 | Breathe Right 30 tiras | 21,09 € | O | S05 |
| CP-06 | Quies spray | 11,59 € | O | S05 |
| CP-07 | Férula genérica Amazon | 9,99 € (histórico 20/09/2026) | O | S13 |

## D. Evidencia clínica (categoría, no SKU)

| ID | Hecho | Clase | Fuente | Restricción |
|---|---|---|---|---|
| CL-01 | Guía AASM/AADSM 2015 recomienda aparatos orales en ciertos adultos con ronquido primario valorado; para AOS prefiere a medida y titulables con supervisión | V | S06 | No atribuible al SKU |
| CL-02 | Ensayo 2024 con 50 parejas, mejoría en algunos resultados con dispositivo mandibular | V (según informe) | S07 | No estudió este SKU |
| CL-03 | Uso prolongado puede producir cambios de oclusión dental | V | S09 | Debe aparecer como precaución general |
| CL-04 | Pausas respiratorias observadas, ahogos, somnolencia intensa → evaluación médica | V (consenso general recogido en informes) | S06, S08 | Pendiente de revisión por profesional sanitario |

## E. Regulación (citas de los informes, **no contrastadas por Claude**)

| ID | Norma | Contenido citado | Clase |
|---|---|---|---|
| RG-01 | RD 192/2023 art. 24.5 | Prohíbe venta por internet de productos sanitarios sujetos a prescripción, incluidos a medida y los que requieren **adaptación individualizada** | **B** hasta dictamen |
| RG-02 | RD 192/2023 art. 26 | Requisitos de establecimientos para productos de adaptación individualizada | B |
| RG-03 | RD 1591/2009 art. 38 (vigente transitoriamente) | Autorización previa autonómica de publicidad al público, incluida internet | **B** para anuncios |
| RG-04 | Reglamento (UE) 2017/745 arts. 6, 7, 13, 14, 16 | Venta a distancia, claims, importador/distribuidor, cambio de rol por marca propia | B |
| RG-05 | AEMPS RECOPS (actualización 02/10/2026) | Comunicación de agentes y puntos de venta | P (aplicabilidad) |
| RG-06 | RDL 1/2007 art. 103.e | Excepción de desistimiento para precintados higiénicos desprecintados tras entrega | P (aplicabilidad al SKU) |
| RG-07 | Garantía legal 3 años | Bienes nuevos | V (S23) |
| RG-08 | AEPD cookies | Aceptar/rechazar con igual visibilidad | V (S24) |
| RG-09 | Derecho UE 3 € por clasificación arancelaria en paquetes ≤150 € desde 01/07/2026 | Coste de importación | V (S28) / P aplicación |
| RG-10 | IVA 21 % | Tipo general; tipo del SKU sin clasificar | H |

## F. Economía (todo hipótesis salvo IVA general)

| ID | Dato | Clase |
|---|---|---|
| EC-01 | PVP candidato 29,90 € | H |
| EC-02 | Coste entregado 10–16 € según escenario | H (sin cotización) |
| EC-03 | Comisión 2,9 % + 0,30 € | H (no tarifa contractual) |
| EC-04 | Reserva incidencias 2–3 € | H |
| EC-05 | Umbral mínimo de contribución 7–8 € | H (criterio del informe) |
| EC-06 | Liquidación Shopify Payments ≥3 días hábiles | V (S27) |
| EC-07 | Capital 1–50 € | V (declarado por titular) |

He **recalculado** todos los escenarios de los informes y son aritméticamente correctos con sus supuestos (ver `05_ECONOMIA_UNITARIA.md`).

## G. Discrepancias detectadas entre documentos

Ver detalle y decisión aplicada en `02_DECISIONES_PENDIENTES.md`, apartado «Discrepancias» (D-01 a D-12). Ninguna afecta a la seguridad; en todas he aplicado provisionalmente el criterio del documento de mayor prioridad y **pido decisión expresa** del titular.

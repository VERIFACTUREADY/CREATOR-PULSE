# 04 · Matriz de claims

**Archivo trazable:** `04_CLAIMS_APPROVAL.csv` (37 filas). Este documento explica las reglas.

## Flujo de aprobación (Estudio §11)

`COPY_ID → texto literal → tipo → fuente primaria → relación con SKU → calificación regulatoria → responsable → versión → fecha → estado`

| Estado | Significado | ¿Puede estar en la web pública? |
|---|---|---|
| `APROBADO` | Validado por el responsable con evidencia y versión | Sí |
| `PENDIENTE` | Falta evidencia o revisión | No (en el prototipo privado solo si es veraz y no clínico) |
| `EDUCATIVO_NO_ATRIBUIBLE` | Información general de categoría o salud; **nunca** se atribuye al SKU | Solo tras revisión sanitaria |
| `RECHAZADO` | Prohibido | Nunca |

**A 13/10/2026 no hay ningún claim en estado `APROBADO`.** Solo el titular y sus asesores pueden aprobar.

## Qué hay en el prototipo

- **Marca (M-01…M-04):** eslogan y promesas editoriales sin contenido clínico.
- **Educativo (E-01…E-11):** frases generales con fuente citada. Se muestran con el marcador visible «Borrador · pendiente de revisión sanitaria» mientras el ajuste `Mostrar marcadores de pendiente` esté activo.
- **Operativo (O-01…O-03):** afirmaciones veraces sobre el estado del proyecto («Todavía no vendemos este producto»).
- **Producto (P-01…P-18):** **ninguno aparece en la web.** Los bloques de ficha que los necesitan leen metacampos vacíos y muestran «Pendiente de documentación del fabricante».

## Claims bloqueados expresamente (prompt final, apartado C)

| Bloqueado | ID |
|---|---|
| «Cura la apnea» / «trata la apnea» | P-04 |
| «Mejora el corazón» / «previene infartos» | P-05 |
| «Define la mandíbula» / «mejora la mandíbula» | P-06 |
| «Rinde más» / «mejora el rendimiento» | P-07 |
| «Mejora el humor» | P-07 |
| «Sin efectos secundarios» / «apto para todos» | P-10 |
| Resultados porcentuales no verificados | P-03 |

## Control automático

`tools/qa/claims-lint.mjs` busca en **todo el tema** y en **todo el HTML renderizado** expresiones prohibidas (cura, apnea curada, corazón, infarto, mandíbula definida, sin efectos secundarios, porcentajes de eficacia, «clínicamente probado», «aprobado por», «recomendado por médicos», «garantizado», estrellas/valoraciones, urgencia falsa…). El QA falla si encuentra alguna fuera de contextos permitidos. Resultado en `10_QA_LANZAMIENTO.md`.

## Reglas para cualquier texto nuevo

1. Separar hechos generales sobre ronquidos de afirmaciones causales sobre la férula. Nunca equipararlos.
2. Un estudio de otro dispositivo **no** es evidencia del SKU.
3. Lo que dice un competidor **no** es permiso para decirlo.
4. Sin testimonios, estrellas, porcentajes, sellos, médicos ficticios, antes/después ni urgencia.
5. Tono: sin culpabilizar; hablar de «tu pareja» o «quien comparte la cama», sin asumir género.
6. Cualquier texto sobre el producto exige: finalidad prevista + IFU + revisión regulatoria + (si es publicidad) autorización art. 38.

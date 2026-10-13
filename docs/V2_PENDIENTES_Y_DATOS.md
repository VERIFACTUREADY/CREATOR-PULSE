# V2 · Datos que necesito y pendientes

Mientras falte cualquiera de estos datos, la web muestra **⟦PENDIENTE: …⟧** y **LIVE no se activa**. `node tools/qa/prelaunch-check.mjs <URL>` lista lo que queda.

## A. Datos que tiene que aportar el titular

**Producto** (Shopify › Producto › Metacampos `commercial.*` y `compliance.*`; ver `11_METACAMPOS_Y_CONFIG.md`):
1. Nombre comercial definitivo y descripción de la ficha aprobada.
2. **Beneficio aprobado** en una frase (`commercial.short_benefit`).
3. **PVP con IVA confirmado** y marcar `commercial.price_confirmed = true`. Precio tachado solo si hay precio anterior real (`compare_at_verified`).
4. Variantes reales (si las hay) y stock.
5. Qué es · cómo se usa (3–5 pasos) · para quién · qué incluye · cuidados y limpieza (textos de la ficha aprobada).
6. Plazo de entrega real (`commercial.delivery_window`).
7. Campos técnicos `compliance.*` (fabricante, modelo, finalidad, materiales, instrucciones, advertencias, contraindicaciones, declaración, operador, lote, versión aprobada de claims).

**Fotos y vídeo** (con original y permiso escrito de uso):
8. 5–8 fotos reales: frontal, lateral, escala (en mano), detalle de material, presentación o caja, uso autorizado.
9. Un vídeo vertical veraz de 15–25 s (opcional).

**Oferta** (Ajustes del tema › Estado de la tienda › Oferta):
10. Envío: coste y plazo confirmados.
11. Devoluciones: resumen de la política aprobada.
12. Atención al cliente: canal, horario y plazo de respuesta.
13. Formas de pago que se activarán.

**Titular** (Ajustes del tema › Identidad):
14. Razón social, NIF/CIF, domicilio, email y datos registrales.

**Textos legales:**
15. Textos finales de envíos, devoluciones, aviso legal, privacidad y cookies. Hoy siguen como plantilla con [corchetes].

**Mensajes:**
16. Aprobar o cambiar los textos nuevos de la V2: M-07 (subtítulo del hero), M-08 y M-09 (titulares de las landings). Están en `04_CLAIMS_APPROVAL.csv`.

**Economía** (hoja `05_ECONOMIA_UNITARIA.xlsx`, columna REAL):
17. Las 5 partidas del coste puesto en cliente, la reserva de incidencias, las devoluciones, el coste de contenido y la comisión real.

**Acceso:**
18. Acceso de colaborador a una tienda de desarrollo o de pruebas (o la tienda real con el tema sin publicar), para el checkout de prueba y el QA en Safari iOS y Chrome Android.
19. Confirmar si queréis que mueva el proyecto a un **repositorio privado nuevo**, y con qué nombre y propietario.

## B. Tareas pendientes (ya implementado / necesita datos / configurar en Shopify)

| Tema | Ya implementado | Necesita datos | Configurar en Shopify |
|---|---|---|---|
| Estados PROTOTIPO / PREVIEW / LIVE | ✅ | — | Mantener el tema sin publicar y los pagos desactivados |
| Portada y landings comerciales | ✅ | 1, 2, 3, 8, 16 | Crear las páginas `landing-ronquidos` y `landing-pareja` con su plantilla |
| Ficha comercial | ✅ | 1–7, 8 | Metacampos (definiciones en `11_…`) |
| Envío, devoluciones, atención y pago coherentes | ✅ (fuente única) | 10–13, 15 | Tarifas de envío y políticas en el admin, coherentes con los ajustes |
| Checkout, emails y estado del pedido | — | 18 | Bogus Gateway o modo de prueba, emails en castellano |
| Medición | Panel en la hoja; sin píxeles | — | Analytics nativo, UTMs, banner de cookies nativo |
| Prelaunch | `prelaunch-check.mjs` | — | Ejecutarlo contra la URL real antes de LIVE |
| Repositorio propio | Rama huérfana aislada | 19 | — |

## C. Para activar LIVE (solo con tu orden expresa)

1. Que `prelaunch-check.mjs` contra la URL real dé **0 incidencias**.
2. Checkout de prueba completo y documentado (C-08).
3. Ajustes del tema: Estado = LIVE y Confirmación = `VENTA REAL AUTORIZADA`.
4. En Shopify: publicar el tema, quitar la contraseña y activar los pagos. **Esto lo hace el titular, no Claude.**
5. Desactivar `noindex` solo en las páginas publicables.

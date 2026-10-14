# V2.1 · Datos que necesito del titular (mercado EE. UU.)

Mientras falte un dato, la tienda muestra **⟦PENDING: …⟧** y **LIVE queda bloqueado**. Ninguno se ha inventado.

## Marca
1. **Marca definitiva.** VINCIRENA es candidata. Necesito confirmación tras la búsqueda en USPTO y el análisis de conflictos marcarios, y saber si el dominio está disponible. Para cambiarla basta con un ajuste: *Estado de la tienda › Nombre de marca* (o el nombre de la tienda en Shopify). Después, marcar «Marca confirmada».
2. Logotipo definitivo (opcional; hoy hay un monograma provisional).

## Producto (metacampos `commercial.*` y `compliance.*`)
3. Nombre comercial del producto en inglés (hoy «Adjustable Mouthpiece», título descriptivo de trabajo) y descripción aprobada.
4. **Beneficio aprobado** en una frase, conforme a FTC y FDA (`commercial.short_benefit`).
5. **Precio en USD confirmado** (`commercial.price_confirmed = true`). Precio tachado solo con historial real.
6. Variantes y stock reales.
7. Qué es · cómo se usa (3–5 pasos) · para quién · qué incluye · cuidados y limpieza, en inglés.
8. Plazo de entrega real a EE. UU. (`commercial.delivery_window`).
9. **Estado regulatorio en EE. UU.** del modelo exacto. Por ejemplo, número FDA 510(k) y si está autorizado para venta sin receta (OTC). Ver `V21_GO_NO_GO_EEUU.md` y, desde V2.2, `V22_FDA_DOCUMENTOS_Y_VALIDACIONES.md` (namespace `regulatory_us`).
10. Instrucciones de uso, advertencias y contraindicaciones del fabricante **en inglés**. Materiales (para valorar avisos como la Proposition 65 de California).

## Fotos y vídeo
11. 5–8 fotos reales con permiso de uso (frontal, lateral, escala, material, caja, uso) y, opcionalmente, un vídeo vertical veraz.

## Oferta (Ajustes del tema › Oferta)
12. Envío: destinos (estados y territorios), coste y plazo confirmados.
13. Política de devoluciones: plazo, condiciones de higiene y reembolsos.
14. Atención al cliente: canal, horario y plazo de respuesta.
15. Formas de pago que se activarán.

## Empresa y legal
16. Entidad vendedora: razón social, tipo de entidad y estado de constitución, dirección, email, EIN (no se publica).
17. Textos finales revisados por un abogado de EE. UU.: Shipping, Returns, Privacy (CCPA/CPRA y otros estados), Terms, Company information y garantía escrita, si la hay.
18. Configuración de *sales tax* (nexus por estado; Shopify Tax u otro), validada por un asesor fiscal.
19. Importador de registro (*importer of record*) y régimen de aduanas y aranceles, confirmados con un agente de aduanas.

## Economía (hoja `05_ECONOMIA_UNITARIA.xlsx`, todo en USD)
20. Las 12 partidas de «Costes variables»: producto, flete, aranceles, última milla, embalaje, incidencias, atención, contenido, tasa y coste de devolución, envío cobrado y descuento medio.
21. Comisión de pago real del plan, umbral mínimo de contribución, CAC de referencia, capital disponible en USD y días hasta cobrar.

## Acceso para las pruebas reales
22. Una **tienda de desarrollo** (o acceso de colaborador) configurada para EE. UU.: moneda USD, mercado Estados Unidos y Bogus Gateway o modo de prueba. Sirve para instalar el tema **sin publicar** y ejecutar el plan `V21_PLAN_PRUEBAS_SHOPIFY.md`.
23. Repositorio privado propio (nombre y propietario), si queréis sacar el proyecto de la rama aislada actual.

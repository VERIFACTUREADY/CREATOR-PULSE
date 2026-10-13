# 02 · Decisiones pendientes y plan P0/P1/P2

**Fecha:** 13/10/2026 · Todo lo marcado 🔴 es **BLOQUEANTE**: impide vender o anunciar.

## 1. Decisiones y datos que necesita el titular

| ID | Pregunta / dato | Responsable | Documento necesario | Consecuencia si falta | Prioridad |
|---|---|---|---|---|---|
| 🔴 DP-01 | ¿La férula exacta encaja en «producto sujeto a prescripción o adaptación individualizada» (RD 192/2023 art. 24.5)? ¿Puede venderse **solo online** por vuestra empresa? | Fundadores + especialista en productos sanitarios / autoridad | Dictamen escrito con fecha, autor y alcance | **NO-GO comercial** del SKU | P0 |
| 🔴 DP-02 | Fabricante legal, modelo, finalidad prevista, clase MDR, declaración UE de conformidad, organismo notificado si procede, UDI | Proveedor / fabricante | DoC firmada + etiquetado + IFU | NO-GO venta | P0 |
| 🔴 DP-03 | Rol económico de vuestra empresa (distribuidor/importador) y obligaciones RECOPS | Asesor regulatorio | Criterio escrito | NO-GO venta | P0 |
| 🔴 DP-04 | ¿Marca propia/reetiquetado os convierte en fabricante (art. 16 MDR)? | Asesor regulatorio | Criterio escrito | No hacer private label | P0 |
| 🔴 DP-05 | Autorización de publicidad al público (art. 38 RD 1591/2009) en vuestra comunidad autónoma | Asesor + autoridad sanitaria autonómica | Autorización o criterio de no aplicación | NO anuncios, influencers ni promociones | P0 |
| 🔴 DP-06 | Instrucciones, advertencias, contraindicaciones y materiales en castellano | Fabricante | IFU oficial | Secciones de uso del producto permanecen vacías | P0 |
| 🔴 DP-07 | Coste entregado real a CP español (1/10/50 uds.), quién importa, IVA/aranceles, plazo, transportista | Proveedor | ≥2 cotizaciones firmadas | No mostrar precio ni plazo | P0 |
| 🔴 DP-08 | Capital disponible para adelantar pedidos y reembolsos | Fundadores | Presupuesto de tesorería | Limitar/posponer | P0 |
| 🔴 DP-09 | Titular del negocio: razón social, NIF, domicilio, email, alta fiscal y Seguridad Social | Fundadores + gestoría | Datos registrales | Páginas legales siguen con placeholders | P0 |
| 🔴 DP-10 | Textos legales finales (aviso legal, privacidad, cookies, condiciones, envíos, devoluciones/garantía, art. 103.e) | Asesoría jurídica | Textos revisados | No abrir ventas | P0 |
| 🔴 DP-11 | Elegibilidad de la categoría en Shopify Payments / pasarela, reservas, tarifas | Titular | Confirmación del proveedor de pagos | No activar cobros | P0 |
| DP-12 | Nombre de marca definitivo y dominio (provisional: «Descanso Compartido») | Fundadores | Búsqueda OEPM/EUIPO y disponibilidad de dominio | Seguir con nombre provisional | P1 |
| DP-13 | Logotipo definitivo (el actual es un monograma SVG provisional creado para el prototipo) | Fundadores | Logo con derechos | Seguir con provisional | P1 |
| DP-14 | Fotografías con licencia (producto real, pareja, guías) | Fundadores / proveedor | Licencias o fotos propias | Se usan ilustraciones SVG originales | P1 |
| DP-15 | Revisión sanitaria del contenido educativo (señales para consultar, apnea vs ronquido, glosario) | Profesional sanitario | Visto bueno firmado y fechado | Contenido marcado «Borrador pendiente de revisión» | P0 antes de publicar |
| DP-16 | PVP definitivo (candidato 29,90 € solo para simulación) | Fundadores tras DP-07 | Hoja de economía con costes reales | No mostrar precio | P1 |
| DP-17 | Activar banner de cookies **nativo y gratuito** de Shopify (Privacidad del cliente) con región UE | Titular en el admin | — | No instalar analítica/píxeles | P0 antes de publicar |
| DP-18 | Credenciales/acceso a una tienda de desarrollo para subir el tema (no se han proporcionado) | Titular | Acceso de colaborador o tienda de desarrollo gratuita | QA solo local | P1 |
| DP-19 | URL de la página con ~20 anuncios Meta | Fundadores | URL | Benchmark incompleto | P2 |
| DP-20 | 8–12 entrevistas y 5 tests de usabilidad (guion en `09_BRIEFS_MARKETING.md`) | Fundadores | Notas anonimizadas | Segmentos siguen como hipótesis | P1 |
| DP-21 | Volúmenes SEO reales (Search Console/Trends/Keyword Planner gratuito) | Fundadores | `KEYWORDS_EVIDENCIA.csv` | Mapa SEO sin volúmenes | P2 |
| DP-22 | Asesoría fiscal: tipo de IVA del SKU, IOSS/importación, facturación | Gestoría | Criterio escrito | Economía con 21 % hipotético | P0 |

## 2. Discrepancias entre documentos (decisión aplicada provisionalmente — **confirmar**)

| ID | Discrepancia | Aplicado en el prototipo | Motivo |
|---|---|---|---|
| D-01 | CTA del hero: «Entender las opciones» (Estudio §12.2) vs «Conocer el producto» (PDF p.5 / Maestro §5.1) | **«Entender las opciones»** (editable en el editor de temas) | El Estudio es prioritario y el producto no está validado; dirigir a producto sería prematuro |
| D-02 | Menú: 3 entradas (PDF p.4) vs «cuatro entradas» (Estudio) | 4: Cómo funciona · El producto · Uso y seguridad · Preguntas | Estudio prioritario; además pone «seguridad» a 1 clic |
| D-03 | «Envíos y devoluciones» en una página (PDF) vs dos páginas (Estudio §12.1) | Dos páginas | Estudio prioritario; derechos distintos |
| D-04 | Ejemplo de contribución: 7,04 € (Estudio, coste 14 €, reserva 2,50 €) vs 7,14 € (Maestro, coste 14,40 €, incidencias 2 €) | Hoja editable con ambos supuestos | Ambos son correctos con sus supuestos; ninguno es real |
| D-05 | Nombres de entregables: lista `00_…11_` (Estudio §19.1) vs lista del prompt final | Nombres del prompt final + CSV pedidos por el Estudio | El prompt final es la instrucción principal |
| D-06 | Tipografía: «fuentes del sistema» (Maestro §04) vs aspecto Lato en el PDF | **Lato** de la biblioteca de fuentes de Shopify (servida por Shopify, sin coste ni llamadas a Google) con respaldo del sistema | Fidelidad al PDF aprobado; se cambia en 1 clic |
| D-07 | El PDF usa un acento cobre en portada/insignias que no está en los 5 tokens | No se usa | Los informes fijan 5 tokens; evitar reinterpretar |
| D-08 | Nombre del artículo: «férula antirronquidos» (Estudio) vs «Dispositivo bucal para el descanso» (PDF p.6) | En la web: **«Dispositivo bucal ajustable — modelo en evaluación»**; «férula» en contenidos educativos genéricos | «Antirronquidos» en el nombre del producto ya es una promesa de finalidad no acreditada |
| D-09 | Mención de bruxismo en el anuncio del vendedor | Excluido de toda la web | Finalidad no acreditada (Estudio §2.3) |
| D-10 | Precio: el PDF de diseño muestra «precio transparente» en ficha; el Estudio prohíbe exponer precio demo | No se muestra precio | Evitar dato demo como oferta |
| D-11 | Blog `/blogs/guia/` (Estudio) — Shopify crea blogs desde el admin, no desde el tema | Artículos redactados como borradores en `08_COPY_Y_SEO.md` | Limitación de plataforma |
| D-12 | Lectura «fácil» vs «clara» | Se usa «lectura clara»; nunca «Lectura Fácil» certificada | PDF p.7 y Estudio §12.3 |

## 3. Plan de tareas por prioridad

### P0 — Antes de cualquier venta o publicación
1. DP-01 a DP-11, DP-15, DP-17, DP-22.
2. Cumplimentar `03_GO_NO_GO.md` con evidencia adjunta por requisito.
3. Rellenar los metacampos `compliance.*` del producto con datos documentados (ver `11_METACAMPOS_Y_CONFIG.md`).
4. Aprobar cada claim de producto en `04_CLAIMS_APPROVAL.csv` (estado `APROBADO` con versión).
5. Auditoría externa del prototipo completo (sitio, textos, legales, accesibilidad).

### P1 — Antes de abrir tráfico orgánico informativo
1. Marca, dominio, logotipo y fotografías con licencia (DP-12/13/14).
2. Subir el tema a una tienda de desarrollo **protegida con contraseña** y repetir QA real (Lighthouse en Shopify, Theme Check desde CLI).
3. Test de usabilidad con 5 personas (encontrar precio, contraindicaciones, devolución, quién vende).
4. Publicar contenidos educativos solo tras revisión sanitaria.

### P2 — Tras lanzamiento autorizado
1. Volúmenes SEO reales, Search Console, `EXPERIMENTOS.csv`.
2. Benchmark de anuncios con URL real.
3. Valorar ampliación de catálogo solo con productos validados.

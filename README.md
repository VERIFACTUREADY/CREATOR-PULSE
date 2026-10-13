# Descanso Compartido · Prototipo privado de tienda Shopify (Dawn)

> 🔴 **ESTADO: PROTOTIPO PRIVADO · NO-GO COMERCIAL.** La tienda **no está lista para lanzarse**. No vende, no cobra, no publica anuncios ni recoge datos de salud. Antes de cualquier venta deben resolverse los bloqueos sanitarios, legales, fiscales, logísticos y financieros de `docs/03_GO_NO_GO.md`, y el prototipo debe superar una **auditoría externa**.

Marca de descanso compartido («**Descansar juntos importa**») construida sobre el tema gratuito **Dawn 16.0.0** de Shopify, a partir de los informes del titular (12/10/2026). El producto candidato (férula bucal AliExpress `1005012312929450`) **no está validado**: no se conocen su fabricante, su conformidad UE, si puede venderse por internet en España ni su coste real.

Nombre de marca **provisional**, pendiente de búsqueda en OEPM/EUIPO (DP-12).

## Qué hay en este repositorio

| Ruta | Contenido |
|---|---|
| `theme/` | Tema Dawn personalizado: código Liquid, JSON, CSS y locales |
| `dist/tema-descanso-dawn.zip` | ZIP para subir a Shopify (Temas › Añadir tema › Subir zip) **sin publicar** |
| `docs/` | Auditoría, decisiones, GO/NO-GO, claims, economía, competencia, SEO, marketing, soporte, configuración, QA, evidencias y checklist |
| `qa/screenshots/` | 62 capturas (15 rutas × 375/390/768/1440, menú móvil y foco de teclado) |
| `qa/reports/` | Resultados de QA en JSON, Theme Check e informes HTML de Lighthouse |
| `tools/` | Previsualizador local (liquidjs) y scripts de QA. Todo gratuito y sin credenciales |

## Cómo verlo

**Opción A · En local, sin Shopify (2 minutos):**
```bash
cd tools
npm install
node preview/build.mjs        # genera preview-out/ (15 páginas)
node preview/serve.mjs        # abre http://localhost:4173
```
Variantes: `node preview/build.mjs --commerce` (simula el comercio activado: la ficha sigue sin compra porque faltan metacampos) y `--no-pending` (oculta los marcadores de pendiente).

Rutas: `/`, `/pages/como-funciona`, `/pages/el-producto`, `/pages/uso-y-seguridad`, `/pages/preguntas-frecuentes`, `/pages/quienes-somos`, `/pages/contacto`, `/pages/envios`, `/pages/devoluciones`, `/pages/aviso-legal`, `/pages/privacidad`, `/pages/cookies`, `/products/dispositivo-bucal-en-evaluacion`, `/cart`, `/404`.

**Opción B · En Shopify (sin publicar):** seguir `docs/11_METACAMPOS_Y_CONFIG.md`: subir el ZIP como tema sin publicar, crear las 11 páginas y los 3 menús, mantener la contraseña activada y no activar pagos.

Si no tenéis capturas a mano, revisad `qa/screenshots/` (por ejemplo `inicio-390.png` o `inicio-1440.png`).

## Lo construido

- **Identidad:** los 5 tokens aprobados (noche `#172B37`, salvia `#D8E5DC`, marfil `#F8F5EE`, arena `#E9DBCA`, petróleo `#3E746F`), Lato, cuerpo de 16,5 px, botones de 48 px, foco muy visible, ilustración SVG original y monograma provisional con una luna.
- **Compuerta de venta (`snippets/ds-commerce-ready.liquid`):** sin precio, compra, pago a plazos, carrito, checkout ni JSON-LD `Product` salvo que **(a)** el interruptor «Comercio habilitado» esté activo **y (b)** el producto tenga los 12 metacampos `compliance.*` rellenos.
- **Modo prototipo:** `noindex`, aviso permanente, marcadores «[Pendiente: …]» y etiquetas «Borrador · pendiente de revisión …». Todo se controla desde *Ajustes del tema › Prototipo y cumplimiento*.
- **13 secciones editables `ds-*`:** hero, pasos, tarjetas con fuente, avisos, estado documental del producto, FAQ nativa (`<details>`), cabecera de página con migas y BreadcrumbList, contenido con índice, comparativa responsive, glosario, plantilla legal, contacto sin datos de salud, identidad del vendedor y datos documentales del producto.
- **Páginas:** Inicio, Cómo funciona, El producto (qué sabemos y qué no), Uso y seguridad, Preguntas frecuentes (19), Quiénes somos, Contacto, Envíos, Devoluciones y garantía, Aviso legal, Privacidad y Cookies. Las legales son plantillas con huecos visibles. Página de contraseña sin captación de emails.
- **Dawn retocado con cuidado:** el carrito y el checkout están cerrados y el formulario de pago a plazos pasa por la compuerta. El logotipo deja de ser un H1. El 404 vuelve al inicio. Sin newsletter, sin iconos de pago y sin «añadir rápido».

## Decisiones técnicas y de diseño (resumen)

| Decisión | Motivo |
|---|---|
| Dawn + Liquid/JSON, sin apps ni headless | Prompt final y Maestro §07; coste 0 € |
| CTA «Entender las opciones» y menú de 4 entradas | El Estudio prevalece sobre el PDF (D-01, D-02) |
| El producto se llama «Dispositivo bucal ajustable (modelo en evaluación)» | Poner «antirronquidos» en el nombre ya es una promesa de finalidad (D-08) |
| Sin fotos: solo una ilustración SVG original | No hay imágenes con licencia. Mejor decirlo que simular (DP-14) |
| Sin FAQPage JSON-LD; BreadcrumbList sí | El contenido de salud está pendiente de revisión; las migas son datos reales |
| Petróleo nunca como texto sobre salvia o arena | No llega al contraste AA (4,1 y 3,9:1) |
| Las precauciones de la ficha se abren por defecto | No esconder advertencias (Estudio §12.3) |
| Previsualizador propio con liquidjs | No hay credenciales de Shopify. Permite capturas y pruebas reproducibles |
| Repositorio: rama huérfana `claude/tienda-descanso-prototipo` | Separa este proyecto del código de creator-pulse que había en el repositorio |

Todas las discrepancias entre informes están en `docs/02_DECISIONES_PENDIENTES.md` (D-01 a D-12), con la decisión aplicada. **Hay que confirmarlas.**

## Resultados de las pruebas (detalle en `docs/10_QA_LANZAMIENTO.md`)

| Prueba | Resultado |
|---|---|
| Theme Check | 0 errores (9 avisos heredados de Dawn) |
| Compuerta de venta | 9/9 |
| 60 combinaciones ruta × ancho | 0 desbordamientos · 1 H1 por página · 0 enlaces rotos · 0 errores de consola · 0 objetivos táctiles < 44 px |
| axe-core WCAG 2.2 AA | 0 violaciones |
| Lighthouse móvil | Rendimiento 92–96 · Accesibilidad 100 · Buenas prácticas 96 · SEO 63 (por el `noindex` intencionado) · CLS 0 |
| Claims prohibidos / rastreadores | 0 / 0 |

## Documentación (`docs/`)

`01_AUDITORIA_DATOS` · `02_DECISIONES_PENDIENTES` · `03_GO_NO_GO` · `04_MATRIZ_CLAIMS` + `04_CLAIMS_APPROVAL.csv` · `05_ECONOMIA_UNITARIA.xlsx/.md` · `06_BENCHMARK_COMPETIDORES.csv/.md` · `07_ATENCION_Y_DEVOLUCIONES` · `08_COPY_Y_SEO` · `09_BRIEFS_MARKETING` · `10_QA_LANZAMIENTO` · `11_METACAMPOS_Y_CONFIG` · `12_REGISTRO_EVIDENCIAS` · `13_CHECKLIST_LEGAL_LOGISTICA` · `KEYWORDS_EVIDENCIA.csv` · `EXPERIMENTOS.csv`

## Lo que NO se ha hecho (y no se debe hacer sin autorización)

No se ha comprado nada ni contratado apps, APIs o suscripciones. No se ha publicado nada ni activado pagos, anuncios o píxeles. No se han creado dominios. No se han inventado reseñas, certificaciones, beneficios médicos, precios ni plazos. No se ha accedido a ninguna tienda Shopify (no había credenciales).

## Límites de verificación

- El proxy de este entorno **bloquea BOE, AliExpress, competidores, AEMPS e INE**. Las citas legales y los precios proceden de los informes y **no han sido contrastados por Claude**.
- El QA es **local**. Hay que repetirlo dentro de Shopify.
- Esto **no es** asesoramiento jurídico, sanitario ni fiscal.

## Licencia

El tema deriva de Dawn © Shopify (ver `theme/LICENSE.md`). Los textos, la ilustración y el código añadido son del proyecto.

# 08 · Copy, sitemap y SEO

**Estado:** borrador para revisión. Todo texto de salud está pendiente de revisión sanitaria (DP-15). No hay volúmenes de búsqueda reales: ver `KEYWORDS_EVIDENCIA.csv`.

## 1. Sitemap implementado

| URL | Plantilla del tema | H1 | Objetivo del usuario | Acción en el prototipo |
|---|---|---|---|---|
| `/` | `index` | Descansar juntos importa. | Entender de qué va la marca en 5 segundos | «Entender las opciones» |
| `/pages/como-funciona` | `page.como-funciona` | Cómo funciona | Ronquidos, causas, férula, opciones, glosario | Leer + ir a seguridad |
| `/pages/el-producto` | `page.el-producto` | El producto | Qué se sabe y qué no del producto | Leer (sin compra) |
| `/products/<handle>` | `product` | Nombre del producto | Ficha documental | Compuerta: «Todavía no vendemos este producto» |
| `/pages/uso-y-seguridad` | `page.uso-y-seguridad` | Uso y seguridad | Cuándo consultar y precauciones | Leer |
| `/pages/preguntas-frecuentes` | `page.preguntas-frecuentes` | Preguntas frecuentes | Resolver dudas (19 preguntas en 4 grupos) | Contacto |
| `/pages/quienes-somos` | `page.quienes-somos` | Quiénes somos | Confianza | Leer |
| `/pages/contacto` | `page.contacto` | Contacto | Escribir sin datos de salud | Formulario nativo |
| `/pages/envios` | `page.envios` | Envíos | Plazos y costes (pendientes) | Leer |
| `/pages/devoluciones` | `page.devoluciones` | Devoluciones y garantía | Derechos | Leer |
| `/pages/aviso-legal` | `page.aviso-legal` | Aviso legal | Identidad del titular | Leer |
| `/pages/privacidad` | `page.privacidad` | Política de privacidad | Datos personales | Leer |
| `/pages/cookies` | `page.cookies` | Política de cookies | Cookies | Leer |
| `/cart` | `cart` | — | — | Desactivado con aviso |

**Navegación.** El menú principal tiene 4 entradas: Cómo funciona · El producto · Uso y seguridad · Preguntas. Desde la cabecera, cualquier página informativa está a 1 clic, y el contacto a 1 clic desde el pie. Se cumple el criterio de «≤ 3 acciones» (Estudio §19.3).

## 2. Metadatos SEO (se rellenan en el admin de Shopify, en el apartado SEO de cada página)

| Página | Título SEO (≤ 60 caracteres) | Meta descripción (≤ 155 caracteres) |
|---|---|---|
| Inicio | Descanso en pareja e información sobre ronquidos \| [Marca] | Información clara sobre ronquidos, descanso compartido y opciones disponibles. Conoce las señales por las que conviene consultar. |
| Cómo funciona | Ronquidos y opciones, explicado fácil \| [Marca] | Qué son los ronquidos, por qué no todos son iguales, qué es una férula de avance mandibular y cómo actúan las distintas opciones. |
| El producto | Dispositivo bucal en evaluación \| [Marca] | Qué sabemos y qué no del dispositivo que estamos evaluando, y qué comprobamos antes de venderlo. Todavía no está a la venta. |
| Uso y seguridad | Uso y seguridad de dispositivos bucales \| [Marca] | Cuándo consultar con un profesional sanitario y precauciones generales antes de usar un dispositivo bucal para dormir. |
| Preguntas frecuentes | Preguntas frecuentes sobre ronquidos y férulas \| [Marca] | Respuestas cortas sobre ronquidos, apnea, férulas, marcado CE, envíos, devoluciones y privacidad. |
| Quiénes somos | Quiénes somos \| [Marca] | Una marca que habla de descanso sin promesas milagrosas. Cómo trabajamos y en qué punto estamos. |
| Contacto | Contacto \| [Marca] | Escríbenos tus dudas sobre la información de esta web. Por favor, no incluyas datos de salud. |
| Legales | [Nombre de la página] \| [Marca] | (Breve y descriptiva; sin palabras clave forzadas). |

Los títulos y descripciones de **Inicio** son los del Estudio §13.2.

## 3. SEO técnico aplicado en el tema

| Requisito (Estudio §13.2) | Estado |
|---|---|
| Un H1 por página | ✅ Comprobado por el QA automático en las 15 rutas |
| Jerarquía semántica H1 → H2 → H3 | ✅ |
| Prototipo no indexable | ✅ `<meta name="robots" content="noindex, nofollow">` mientras `ds_noindex` esté activo. **Además**: tienda protegida con contraseña (Shopify ya bloquea la indexación así). |
| Sin `Product`/`Offer` sin oferta real | ✅ El JSON-LD de producto solo se emite si la compuerta pasa |
| Sin `aggregateRating` | ✅ No hay bloques de reseñas ni estrellas |
| `BreadcrumbList` con datos reales | ✅ En cada página con cabecera DS |
| `Organization` | ✅ El de Dawn (nombre y URL de la tienda) |
| Sin FAQPage JSON-LD | ✅ Decisión: el contenido de salud está pendiente de revisión |
| Alt factual / imágenes ligeras | ✅ La ilustración SVG es decorativa (`aria-hidden`); sin fotos todavía |
| Sitemap sin fichas demo | ⚠️ Shopify genera `sitemap.xml` automáticamente. Con la tienda en contraseña no se rastrea. **Antes de publicar**: no dejar productos demo activos en el canal Tienda online. |

## 4. Mapa de contenidos (Estudio §13.1)

| Prioridad | Título de trabajo | Intención | Estado |
|---|---|---|---|
| P0 | Ronquidos: causas habituales y cuándo consultar | Informativa | **Borrador A** (abajo), pendiente de revisión sanitaria |
| P0 | Qué es una férula de avance mandibular | Educativa | **Borrador B** (abajo) |
| P0 | Roncar y apnea del sueño: qué diferencia hay | Salud | **Borrador C** (abajo), requiere revisión clínica |
| P1 | Dormir en pareja cuando hay ronquidos | Cotidiana | Pendiente |
| P1 | Férula antirronquidos: dudas frecuentes sobre el ajuste | Evaluación | Bloqueado: necesita el IFU |
| P1 | Tiras nasales y férulas bucales: ¿son lo mismo? | Comparativa | Base disponible en la tabla de «Cómo funciona» |
| P1 | Cómo interpretar las indicaciones de un dispositivo bucal | Confianza | Pendiente de revisión por especialista |
| P2 | Cómo limpiar una férula bucal | Postcompra | Bloqueado: método del fabricante |
| P2 | Cuándo renovar una férula | Postcompra | Bloqueado: no fijar plazo sin instrucciones |
| P2 | Información antes de adquirir un dispositivo sanitario | Consideración | Pendiente |

**Títulos prohibidos:** «Nunca volverás a roncar», «Descansa al 100 %», «Cómo curar la apnea en casa», «Rescata tu relación», páginas clonadas por ciudades.

**Publicación:** Shopify crea los blogs desde el admin, en Tienda online › Artículos de blog. Crear el blog con el identificador `guia` (URL `/blogs/guia`) y publicar **solo tras la revisión sanitaria**, indicando autoría y fecha de revisión.

---

## Borrador A · «Ronquidos: causas habituales y cuándo consultar»

> BORRADOR · pendiente de revisión sanitaria · No publicar

**Entradilla:** Roncar es frecuente. A veces solo molesta. Otras veces conviene consultarlo. Te explicamos la diferencia con palabras sencillas.

**¿Qué es roncar?** Es el sonido que se produce al respirar mientras duermes, cuando el paso del aire se estrecha.

**¿Por qué no todos los ronquidos son iguales?** No todos los ronquidos tienen el mismo origen. Por eso no hay una solución que sirva a todo el mundo. [Pendiente: causas habituales, redactadas y revisadas por un profesional, con fuente].

**¿Cuándo conviene consultar?**
- Alguien ve que dejas de respirar unos segundos mientras duermes.
- Te despiertas con sensación de ahogo.
- Tienes mucho sueño durante el día.
- Los ronquidos son nuevos o muy intensos.

Estas señales no sirven para diagnosticar. Indican que conviene una valoración profesional.

**Fuentes:** S06 (AASM/AADSM 2015), S08 (ADA).

## Borrador B · «Qué es una férula de avance mandibular»

> BORRADOR · pendiente de revisión sanitaria · No publicar

**Entradilla:** Una explicación clara de qué es, para quién puede estar indicada y qué precauciones tiene.

**Qué es.** Un aparato que se pone en la boca para dormir. Mantiene la mandíbula inferior un poco hacia delante.

**Para quién.** Algunas férulas bucales están indicadas en determinados adultos, después de una valoración profesional. Para la apnea del sueño, las guías clínicas prefieren aparatos hechos a medida y ajustados con el seguimiento de un dentista (S06).

**Precauciones.** Usarlas durante mucho tiempo puede cambiar la forma en que encajan los dientes (S09). Si notas dolor en la mandíbula, en los dientes o en el oído, deja de usarla y consulta.

**Lo que no dice este artículo.** Que una férula concreta funcione. Lo que dicen los estudios sobre algunas férulas no demuestra que funcione cualquier férula (S07 estudió un dispositivo concreto, no el nuestro).

## Borrador C · «Roncar y apnea del sueño: qué diferencia hay»

> BORRADOR · requiere revisión clínica · No publicar

**Entradilla:** Roncar y tener apnea del sueño no es lo mismo. Saber distinguirlos ayuda a decidir cuándo pedir ayuda.

**Roncar.** Es un sonido al respirar durante el sueño.

**Apnea del sueño.** Es un trastorno en el que la respiración se interrumpe varias veces durante el sueño. Lo diagnostica un profesional sanitario. [Pendiente: explicación revisada por un profesional].

**Qué hacer.** Si notas las señales de la lista del Borrador A, consulta con un profesional. Un dispositivo comprado por internet no sustituye a un diagnóstico ni a un tratamiento.

**Fuentes:** S06, S08.

---

## 5. Guía de microcopy (Propuesta de diseño p.7)

| Evitar | Usar |
|---|---|
| «Tecnología mandibular innovadora que revolucionará tus noches» | «Conoce cómo funciona este dispositivo bucal» |
| «Resultados garantizados desde la primera noche» | «Consulta para quién está indicado y sus limitaciones» |
| «Múltiples funcionalidades terapéuticas» | «Qué es, cómo se usa y qué precauciones tiene» |
| «Tu marido te arruina las noches» | «Cuando uno ronca, puede haber dos personas despiertas» |
| «Compra ya, quedan 3» | (nada: sin urgencia falsa) |

Reglas: una idea por frase, párrafos de 2–3 líneas, títulos que anticipan el contenido, enlaces descriptivos, sin culpas y sin dar por hecho el género de nadie. **No se afirma que la web cumpla la «Lectura Fácil» certificada.**

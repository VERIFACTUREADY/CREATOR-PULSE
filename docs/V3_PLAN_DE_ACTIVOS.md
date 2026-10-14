# V3 · Plan de fotografía y vídeo

Reglas: solo activos **del artículo real** o con licencia y autorización por escrito. **Nunca** fotos de HONEX, Snoozer ni del anuncio de AliExpress sin licencia expresa. La IA solo se usa para fondos o ambientes, y nunca para representar el producto, su funcionamiento, resultados ni clientes reales; si se usa, se etiqueta en el registro. Las personas que aparezcan dan su consentimiento firmado (*model release*). Formato: WebP (o AVIF cuando Shopify lo sirva automáticamente con `image_url`), imágenes adaptables (`widths`/`sizes`), `loading="eager"` + `fetchpriority="high"` solo en la imagen del primer pantallazo y `lazy` en el resto (ya implementado en las secciones).

Mientras falte un activo, el tema muestra su hueco ⟦PENDING⟧ con la toma necesaria y `prelaunch-check` bloquea LIVE.

| Archivo | Página / sección | Función comercial | Formato | Proporción | Tamaño recomendado | Texto alternativo (EN) | ¿Imprescindible para LIVE? | Licencia / aprobación |
|---|---|---|---|---|---|---|---|---|
| `prod-front.webp` | Ficha (galería 1), hero de portada y landing A | Saber qué se vende en 1 s | WebP | 1:1 | 2048×2048 | Adjustable mouthpiece, front view, on a light background | **Sí** | Pendiente: fotografía propia |
| `prod-side.webp` | Ficha (galería 2) | Forma y grosor | WebP | 1:1 | 2048×2048 | Adjustable mouthpiece, side view | **Sí** | Pendiente |
| `prod-hand.webp` | Ficha (galería 3) | Escala real | WebP | 1:1 | 2048×2048 | Mouthpiece held in an adult's hand to show its size | **Sí** | Pendiente + consentimiento |
| `prod-adjust.webp` | Ficha (galería 4), «How it works» | Cómo se ajusta (según el IFU) | WebP | 4:3 | 2000×1500 | Close-up of the mouthpiece's adjustment point | **Sí** si el modelo es ajustable | Pendiente + IFU del fabricante |
| `prod-material.webp` | Ficha (galería 5), tarjeta «Materials» | Calidad percibida | WebP | 4:3 | 2000×1500 | Close-up of the mouthpiece material | No | Pendiente + certificado de material |
| `prod-case.webp` | Ficha (galería 6), «What's included» | Qué incluye | WebP | 1:1 | 2048×2048 | Mouthpiece, case and everything included in the box | **Sí** | Pendiente |
| `use-real.webp` | Ficha (galería 7) | Uso real conforme al IFU | WebP | 4:5 | 1600×2000 | Adult showing how the mouthpiece is placed, following the instructions | No | Pendiente + consentimiento + IFU |
| `life-couple-bed.webp` | Portada «Better nights…», landing B (hero) | Conexión emocional | WebP | 4:3 (móvil 16:10) | 2400×1800 | Adult couple resting in a calm bedroom | **Sí** para la landing B | Pendiente: banco con licencia comercial o sesión propia con *release* |
| `life-morning.webp` | Galería 8, campañas | Mañana tranquila (sin prometer resultados) | WebP | 4:5 | 1600×2000 | Adult couple having coffee in the morning | No | Pendiente |
| `diagram-mad.svg` | «How it works» | Explicación visual | SVG inline | 64:33 | Vectorial | (`<title>` editable en la sección) | Sí (ya existe) | **Original del proyecto.** Confirmar el mecanismo con el fabricante |
| `ifu-cover.webp` | Ficha, «Manufacturer and documentation» | Confianza: el IFU existe | WebP | 3:4 | 1200×1600 | Cover of the manufacturer's instructions for use | No | Pendiente: permiso del fabricante |
| `support-team.webp` | Contact / About | Quién atiende | WebP | 3:2 | 1800×1200 | (persona real del equipo, con nombre si da permiso) | No | Pendiente |
| `video-howto.mp4` | Ficha («How to use») | Demostración paso a paso conforme al IFU | MP4 H.264 + póster WebP, subtítulos `.vtt` | 9:16 y 16:9 | 1080×1920 / 1920×1080, ≤ 60 s | (subtítulos y transcripción) | No | Pendiente: guion revisado contra el IFU |
| `video-ugc-*.mp4` | Anuncios (no en la web por ahora) | Prueba social | MP4 | 9:16 | 1080×1920 | — | No | **Solo** con creadores reales, aviso de patrocinio (FTC Endorsement Guides) y sin claims de salud |

Registro: anotar cada activo, con su licencia, fecha, autor y consentimiento, en `docs/12_REGISTRO_EVIDENCIAS.md`.

## Estado al 14/10/2026: fotos entregadas por el titular

El titular entregó 11 imágenes. Convertidas de PNG a JPEG de calidad 90 (unos 200 KB cada una frente a los 2–4 MB originales). Copia en `media/producto/`. Subidas a Shopify como medios del producto `adjustable-mouthpiece`; también aparecen en *Content › Files*.

| # | Archivo en Shopify | Uso en el tema | Texto alternativo |
|---|---|---|---|
| 1 | `vincirena-mouthpiece-3-4-left.jpg` | Galería de la ficha (1ª, imagen principal) · hero de la portada | Adjustable mouthpiece, three-quarter view showing the upper and lower trays |
| 2 | `vincirena-mouthpiece-front.jpg` | Galería (2ª) · bloque de producto de la landing B | Adjustable mouthpiece, front view |
| 3 | `vincirena-mouthpiece-top-front.jpg` | Galería (3ª) | Adjustable mouthpiece seen from above, showing the inside of the upper tray |
| 4 | `vincirena-mouthpiece-3-4-right.jpg` | Galería (4ª) · hero de la landing A | Adjustable mouthpiece, side view showing the metal adjustment point |
| 5 | `vincirena-mouthpiece-top.jpg` | Galería (5ª) | Adjustable mouthpiece, top-down view of the tray surface |
| 6 | `vincirena-mouthpiece-back.jpg` | Galería (6ª) | Adjustable mouthpiece, rear view |
| 8 | `vincirena-mouthpiece-case-tool.jpg` | Galería (7ª) · «Meet the mouthpiece» de la portada | The mouthpiece next to its storage case and a small adjustment tool |
| 7 | `vincirena-lifestyle-couple-bedside.jpg` | Galería (8ª) · «Better nights are a team effort» de la portada · hero de la landing B | An adult couple asleep; the mouthpiece, its case and the tool rest on the bedside table |

**No se usan en la web (9, 10 y 11: anillo dorado y columnas, salpicadura de agua y rascacielos de noche).** Su estética espectacular choca con la dirección calmada y clara de la marca (`V3_SISTEMA_DE_DISENO.md` §1). Además, la salpicadura de agua podría sugerir propiedades no verificadas, como resistencia al agua, lavado o higiene. Pueden servir para anuncios si se aprueban, y no se han subido a Shopify.

**Pendiente de confirmar por el titular:**
- **Origen y licencia** de cada imagen.
- Si son **renders o imágenes generadas con IA**, que reproducen fielmente el artículo real (forma, punto de ajuste metálico, pestaña lateral, estuche y herramienta).
- En la foto lifestyle, que las personas son modelos con consentimiento o imagen generada. Nunca se presentarán como clientes reales.

Las fotos 7 y 8 muestran un estuche y una herramienta. **No se afirma en ningún texto** que se incluyan: eso debe venir de `commercial.includes`, la ficha aprobada.

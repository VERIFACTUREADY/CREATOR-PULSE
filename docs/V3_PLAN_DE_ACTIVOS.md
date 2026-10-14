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

# V3 · Sistema de diseño VINCIRENA

Implementación: `theme/assets/descanso.css`, bloque «V3 · Sistema de diseño», y los ajustes globales de `config/settings_data.json`. Diseñado primero para móvil.

## 1. Dirección

Marca premium y accesible de descanso compartido: calma, precisión y calidez. Mucho aire, tarjetas con bordes discretos, radios generosos, sombras muy suaves, una sola familia tipográfica y color con función: el **noche** guía y el **petróleo** invita a la acción. Lo que busca evitar es el aspecto de tienda genérica de dropshipping (banners chillones, sellos, contadores).

## 2. Paleta: conservada y ampliada de forma justificada

Los 5 colores aprobados **no cambian**. Se añaden derivados para crear profundidad sin introducir colores nuevos:

| Token | Valor | Uso | Contraste medido |
|---|---|---|---|
| `--ds-night` | #172B37 | Texto, botones secundarios, números | 13,42:1 sobre marfil · 11,25:1 sobre salvia · 10,75:1 sobre arena |
| `--ds-ivory` | #F8F5EE | Fondo principal (scheme-1) | — |
| `--ds-sage` | #D8E5DC | Fondo de sección (scheme-2), iconos | — |
| `--ds-sand` | #E9DBCA | Fondo emocional (scheme-3) | — |
| `--ds-petrol` | #3E746F | CTA principal, enlaces sobre marfil o blanco | blanco sobre petróleo 5,34:1 · petróleo sobre marfil 4,90:1 |
| **`--ds-ink-soft`** (nuevo) | #3D5260 | Entradillas y textos secundarios | 7,49:1 sobre marfil · 8,16:1 sobre blanco |
| **`--ds-sage-soft`** (nuevo) | #EAF1EC | Halo del hero, antetítulo píldora, recuadro de características | noche 12,73:1 · petróleo 4,65:1 |
| **`--ds-sand-soft`** (nuevo) | #F4ECE2 | Reservado (tarjetas sobre arena) | noche 12,49:1 |
| `--ds-line` / `--ds-line-strong` | noche al 12 % / 24 % | Separadores y bordes | Decorativo |
| `--ds-warn-bg` / `--ds-warn-ink` | #FFF3C4 / #4A3800 | Marcadores ⟦PENDING⟧ | 10,16:1 |

La regla V2 se mantiene: **el petróleo nunca va como texto sobre salvia** (4,11:1). Solo se usa ahí en iconos decorativos.

## 3. Tipografía: evaluación

| Criterio | **Lato (actual)** | Inter | Manrope | Plus Jakarta Sans |
|---|---|---|---|---|
| Legibilidad en móvil | Alta (humanista, buena altura de x) | Muy alta | Alta | Alta |
| Carácter de marca | Cálido y cercano | Neutro, «tech» | Geométrica, moderna | Moderna, algo «startup» |
| Disponible en la biblioteca de Shopify sin subir archivos | **Sí, verificado** (ya en uso) | Probable, sin verificar | Sin verificar | Sin verificar |
| Coste de rendimiento | 0: ya precargada (400/700) | Cambio de archivo | Cambio de archivo | Cambio de archivo |
| Herramienta local de QA | Incluida (`@fontsource/lato`) | Habría que añadirla | Habría que añadirla | Habría que añadirla |

**Decisión:** mantener **Lato 400/700** (2 pesos, `font-display: swap` y precarga existentes) y conseguir la distinción premium con escala, interlineado y espaciado de letras: display de 3,4 a 6,4 rem, interlineado 1,08 y tracking −0,022 em; H2 de 2,8 a 4,4 rem; antetítulos en versalitas con +0,12 em. Si el titular prefiere un titular más moderno, la prueba A/B propuesta es **Manrope solo para los encabezados**, después de comprobar que existe en *Theme settings › Typography* (`type_header_font`). No requiere tocar código.

## 4. Tokens

| Grupo | Tokens |
|---|---|
| Tipografía | `--ds-fs-display`, `--ds-fs-h2`, `--ds-fs-h3` (2 rem), `--ds-fs-lead`, `--ds-fs-body` (1,7 rem = 18,7 px con la escala de cuerpo 110 %), `--ds-fs-small`, `--ds-fs-micro`, `--ds-lh-*`, `--ds-track-*` |
| Espaciado (4/8) | `--ds-space-1` … `--ds-space-8` (0,8 → 9,6 rem); márgenes de sección por ajustes (`ds-section-vars`, 70 % en móvil) |
| Radios | `--ds-radius-s/m/l` (10/16/24), `--ds-radius-xl` (32), `--ds-radius-pill`; Dawn: `buttons_radius` 40, `inputs_radius` 12, `card_corner_radius` 24 |
| Sombras | `--ds-shadow-1` (tarjetas), `--ds-shadow-2` (media del hero) |
| Anchuras | `page_width` 1200 px, `--ds-text-w` 64 rem, `--ds-head-w` 76 rem, `--ds-measure` 68 ch |
| Controles | `--ds-btn-h` 52 px, `--ds-btn-h-s` 44 px (objetivo táctil mínimo de 44 px conservado) |
| Foco | Contorno de 3 px en petróleo (noche o salvia según el esquema), desplazado 3 px (WCAG 2.4.7 y 2.4.11) |
| Movimiento | `--ds-ease`, `--ds-dur` 220 ms; todo se anula con `prefers-reduced-motion` |
| Breakpoints | 750 · 990 · 1200 px (los de Dawn; CSS no admite variables en `@media`); ajustes de altura con `max-height: 700px` para 375×667 |

## 5. Componentes nuevos

`ds-section-head` (cabecera común), `ds-announce`, `ds-moments`, `ds-mechanism` + `ds-diagram-mad`, `ds-features`, `ds-editorial`, `ds-trust`, `ds-gallery-slots`, `ds-highlights` y `ds-offer-table`. Todos se editan desde el editor de temas, aceptan `visible_in` (PROTOTIPO / comercial) y no dependen de librerías externas: 0 JS nuevo y unos 9 KB de CSS sin comprimir.

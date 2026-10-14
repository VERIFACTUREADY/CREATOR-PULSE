# V3 · SEO, analítica y pruebas A/B

`noindex` sigue activo (`ds_noindex = true`) mientras la tienda esté en PREVIEW. Nada de esto se aplica en Shopify sin la orden del titular.

## 1. Títulos, metadescripciones y encabezados

Se configuran en Shopify (*Online Store › Preferences* para la portada; *Pages/Products › Search engine listing* para el resto). Ningún texto incluye beneficios no aprobados. `{Brand}` = ajuste de marca (VINCIRENA provisional).

| Página | Title (≤ 60) | Meta description (≤ 155) | H1 | Enlaces internos clave |
|---|---|---|---|---|
| Home | Adjustable Mouthpiece for Snoring Couples \| {Brand} | Snoring can affect both of you. See what our adjustable mouthpiece is, how it's used and what's included — explained simply. | Because peaceful nights matter to both of you. | Ficha, How it works, landing B, FAQ |
| Product | Adjustable Mouthpiece \| {Brand} | What it is, how to use it step by step, what's included, care, precautions, shipping and returns. | (título del producto) | Use & safety, Returns, FAQ |
| How it works | How Mandibular Advancement Mouthpieces Work \| {Brand} | What snoring is, why it isn't always the same, how oral appliances work and how they compare with other options. | (título de la página) | Ficha, Use & safety |
| About | About {Brand} | Who we are, what we sell and how we make decisions — without miracle claims. | About us | Contact, Company information |
| Shipping | Shipping Policy \| {Brand} | Shipping costs, delivery times and what happens if an order is delayed. | Shipping policy | Returns, Contact |
| Returns | Return Policy \| {Brand} | How to return a product, conditions and refunds. | Return policy | Shipping, Contact |
| Contact | Contact Us \| {Brand} | Questions about an order or the product? Write to us. Please don't include health information. | Contact | FAQ |
| FAQ | Frequently Asked Questions \| {Brand} | Short answers about the mouthpiece, fit, cleaning, shipping, returns and safety. | Frequently asked questions | Ficha, Use & safety |
| Landing A | Worried About Your Snoring? \| {Brand} | See what our mouthpiece is, how it's used and what's included — explained simply. | Worried about your snoring? | Ficha, How it works |
| Landing B | Snoring and Sleeping as a Couple \| {Brand} | When one person snores, two people can be awake. A calmer way to talk about it, and one option to look at. | When one person snores, two people can be awake. | Ficha, How it works |

Jerarquía: un H1 por página (comprobado en 18 rutas × 4 anchos + 430 y 1280 px), H2 por sección y H3 en tarjetas y características.

**Datos estructurados:** se mantienen `Organization`, `WebSite` y `BreadcrumbList` (datos reales). `Product` solo en LIVE con la ficha completa (lógica V2.2 sin cambios). **Sin** `AggregateRating`, `Review` ni `FAQPage` hasta la revisión sanitaria final.

## 2. Tres artículos educativos propuestos (blog, con revisión factual)

| # | Título | Intención de búsqueda | Esquema | Fuentes mínimas | Enlace a |
|---|---|---|---|---|---|
| 1 | What is a mandibular advancement device? A plain-English guide | Informativa («mandibular advancement device», «how do mouth guards for snoring work») | Qué es · cómo actúa · para quién se recomienda (con profesional) · precauciones · alternativas | AASM/AADSM 2015, ADA | How it works, ficha |
| 2 | Snoring vs. sleep apnea: signs worth talking to a provider about | Informativa / salud («is snoring sleep apnea») | Diferencias · señales de alerta · a quién acudir · qué no hace un dispositivo de venta libre | ADA, AASM | Use & safety |
| 3 | How to talk to your partner about snoring (without blame) | Relacional («partner snores what to do») | Cuándo hablar · qué decir · opciones juntos · cuándo consultar | JAMA Otolaryngology 2024 (parejas), AASM | Landing B |

Cada artículo pasa por la matriz de claims y por la revisión de un profesional sanitario antes de publicarse.

## 3. Medición (sin píxeles publicitarios)

Hoy solo existe la analítica integrada de Shopify (eventos estándar). Los píxeles de Meta, Google o TikTok requieren autorización expresa, banner de consentimiento configurado (*Customer privacy*), GPC respetado y actualizar la *Privacy Policy*.

| Métrica | Definición | Fuente |
|---|---|---|
| Sesiones cualificadas | Sesiones con ≥ 1 vista de ficha o ≥ 50 % de scroll en la landing | Shopify Analytics + evento personalizado (Customer events, sin terceros) |
| Vistas de producto | `product_viewed` | Shopify (estándar) |
| Clics en CTA | Clic en «See the mouthpiece» por sección (`data-section` del hero, editorial o cierre) | Evento personalizado `cta_click` (propuesto, no implementado) |
| Add to cart | `product_added_to_cart` | Shopify (solo en LIVE) |
| Inicio de checkout | `checkout_started` | Shopify |
| Compras / CR | `checkout_completed` / sesiones cualificadas | Shopify |
| AOV | Ingresos / pedidos | Shopify |
| CAC | Gasto en medios / pedidos nuevos | Plataformas de anuncios + hoja |
| Contribución por pedido | Precio − COGS − envío − comisiones − devoluciones esperadas − CAC | `docs/05_ECONOMIA_UNITARIA.xlsx` |
| Devoluciones | Tasa y motivo | Shopify + atención al cliente |

## 4. Hipótesis A/B (sin conclusiones hasta tener datos)

Requisitos: tráfico suficiente (calcular el tamaño de muestra antes), una sola variable por prueba, al menos 2 ciclos semanales y métrica principal = compras por sesión cualificada. Herramienta: plantillas alternativas de Shopify (`index.alt.json`, `product.alt.json`) con reparto por URL de campaña, sin apps de pago.

| ID | Hipótesis | Variante A | Variante B | Métrica principal | Condición previa |
|---|---|---|---|---|---|
| A | Una primera pantalla centrada en el producto convierte distinto que una emocional | Hero V3 (emocional + producto en el antetítulo) | H1 = nombre del producto + beneficio aprobado | CTR del hero → ficha; CR | Beneficio aprobado y foto real |
| B | Un pack aumenta el AOV sin bajar la CR | 1 unidad | 1 unidad + pack de 2 (variante real) | AOV, contribución por pedido | Precio, COGS y pack reales |
| C | Una barra fija de compra en móvil mejora el add to cart | CTA tradicional | Barra fija (ver la evaluación en `V3_COPY_Y_CRO.md` §4) | Add to cart por vista de ficha | LIVE autorizado; prueba de accesibilidad |
| D | La posición de «How it works» cambia la comprensión y la CR | Tras «Meet the mouthpiece» (V3) | Justo después del hero | Scroll hasta la FAQ; CR | — |
| E | La composición de fotos influye en la CR | Producto primero | Lifestyle primero | CR; tiempo hasta el primer clic | Fotos reales |
| F | Las características resumidas encima de la CTA ayudan a decidir | Debajo de la CTA (V3) | Encima (orden del brief §6.1) | Add to cart; visibilidad de la CTA | 3 viñetas aprobadas y cortas |

Registrar cada prueba en `docs/EXPERIMENTOS.csv`.

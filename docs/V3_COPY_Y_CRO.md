# V3 · Copy, psicología del consumidor y CRO

Fuente del texto: `tools/content/build_us_templates.py`, que genera las plantillas JSON y después se edita en el editor de temas. Los textos nuevos se registran como **PENDIENTE** en `docs/04_CLAIMS_APPROVAL_US.csv` (US-M-06 a US-M-12).

## 1. Voz de marca

**Premium, natural, empática, clara y fiable.** Inglés de EE. UU., frases cortas, una idea por párrafo, verbos de acción en los botones («See the mouthpiece», no «Learn more»), sin tecnicismos sin explicar («mandibular advancement» va siempre con su explicación), sin culpables ni género («the person who snores», «the person next to them»). Ni clínica, ni infantil, ni sensacionalista.

Regla de oro: **ningún beneficio del producto en el código.** El beneficio sale de `commercial.short_benefit` (aprobado) o se muestra ⟦PENDING⟧. Los titulares hablan de la experiencia compartida, no de resultados.

## 2. Alternativas de titulares y elección

Escala de 1 a 5. Claridad = se entiende qué y para quién. Diferenciación = no podría ser de cualquier competidor. Adecuación = encaja con la marca y no supone un claim (FTC/FDA).

### Portada (H1 con el nombre del producto en el antetítulo «The adjustable mouthpiece»)

| # | Titular | Claridad | Diferenciación | Adecuación | Notas |
|---|---|---|---|---|---|
| A | Better nights start with better choices. | 3 | 2 | 4 | Genérico; serviría para un colchón |
| **B** | **Because peaceful nights matter to both of you.** | 4 | 5 | 5 | Pareja = posicionamiento; no promete resultados |
| C | Quieter nights, for both of you. | 5 | 4 | **2** | «Quieter» implica eficacia (claim no aprobado) |

**Elegida: B.** El subtítulo cubre lo que el titular no dice (problema + producto + qué encontrarás): *«Snoring can affect the person who snores and the person next to them. Meet our adjustable mouthpiece — what it is, how it's used and what's included, explained simply.»*

### Landing A · persona que ronca

| # | Titular | Claridad | Diferenciación | Adecuación | Notas |
|---|---|---|---|---|---|
| **A** | **Worried about your snoring?** | 5 | 3 | 5 | Ya figura en la matriz (US-M-03); pregunta directa para tráfico de búsqueda o anuncios |
| B | Snoring? Start with clear answers. | 4 | 4 | 4 | Más seco; «answers» puede sonar a diagnóstico |
| C | A clearer look at one way to address snoring. | 3 | 3 | 3 | «Address snoring» se acerca a la finalidad médica |

**Elegida: A**, porque engancha con la pregunta que se hace el usuario y ya está en revisión. La diferenciación se apoya en la estructura (explicación → opciones → mecanismo).

### Landing B · descanso en pareja

| # | Titular | Claridad | Diferenciación | Adecuación | Notas |
|---|---|---|---|---|---|
| **A** | **When one person snores, two people can be awake.** | 5 | 5 | 5 | US-M-04; empático, verdad educativa (US-E-01) |
| B | Sleep is something you share. | 3 | 4 | 5 | Se usa como cierre de la landing |
| C | Love them, not the snoring. | 4 | 4 | **2** | Culpabiliza; tono de chiste |

**Elegida: A.** B pasa a ser el titular de cierre.

## 3. Objeción que resuelve cada sección

Secuencia: **comprensión → interés → evaluación → confianza → decisión.**

| Sección (portada) | Etapa | Objeción | Cómo la resuelve, sin presión |
|---|---|---|---|
| Hero | Comprensión | «¿Qué es esto y es para mí?» | Producto en el antetítulo, problema compartido, precio confirmado, CTA y «How it works» |
| Momentos | Interés | «Me da vergüenza», «es culpa suya» | Tres perspectivas sin culpables; dato educativo con fuente |
| Meet the mouthpiece | Interés | Desconfianza ante una marca desconocida | Qué es en palabras simples desde la documentación; foto real (pendiente) |
| How it works | Evaluación | «¿Cómo funciona?», «¿será incómodo?» | Diagrama, 3 pasos, «the fit is personal» y precauciones visibles |
| The details | Evaluación | Materiales, ajuste, limpieza, qué incluye | Tarjetas desde metacampos; ⟦PENDING⟧ si falta |
| Pareja | Interés y decisión | «No sé cómo sacar el tema» | Mensaje de equipo; guía para parejas |
| Comparativa | Evaluación | «Ya probé tiras nasales…» | Cómo actúa cada categoría, sin superioridad |
| Confianza | Confianza | Envío, devoluciones, quién vende, quién fabrica | Datos reales de «Oferta» y fabricante; «No made-up reviews» |
| FAQ | Confianza | Ajuste, molestias, apnea, envío, devoluciones | Respuestas breves con enlace al detalle |
| Cierre | Decisión | — | Una CTA y la frase de marca, sin urgencia |

En la ficha: la **relación calidad/precio** la cubren el precio confirmado y `ds_offer_table` (total, precio por unidad y ahorro solo si son reales); los **cargos ocultos**, «One-time purchase. No subscription and no recurring charges.» (calculado a partir de los planes de venta reales); el **miedo a la incomodidad**, las precauciones abiertas por defecto y la FAQ «What if it feels uncomfortable?»; el **escepticismo**, la fuente de cada dato y los ⟦PENDING⟧ visibles.

**Prohibido:** contadores, «X people are viewing», escasez inventada, tachados sin historial, estrellas o cifras de clientes. `run-qa` lo vigila: 0 coincidencias.

## 4. Ficha de producto

Orden en móvil (V3): galería → nombre → beneficio aprobado → precio → (variantes) → cantidad → **CTA** → características resumidas → opciones y «compra única» → envío, devoluciones, atención y pago → descripción → cómo usarlo → detalles → qué es, para quién, qué incluye, cuidados → precauciones → FAQ.

**Desviación justificada respecto al brief §6.1:** las características resumidas van **debajo** de la CTA y no encima. Con los ⟦PENDING⟧ actuales, ponerlas encima empujaba la CTA fuera de la primera pantalla a 390×844, y el brief pide que «el cliente no tenga que buscar dónde se compra». Cuando existan 3 viñetas reales, probarlo con A/B (hipótesis F en `V3_SEO_ANALITICA_AB.md`). Se cambia arrastrando el bloque en el editor.

Escritorio: dos columnas 55/45 con la columna de compra fija (`enable_sticky_info`).

**Oferta (§6.4):** `ds_offer_table` solo compara **variantes reales** del catálogo. Las ofertas de 1 unidad, 2 unidades, kit o pack de pareja se crean como variantes cuando existan datos y economía (`docs/05_ECONOMIA_UNITARIA.xlsx`). No se crean descuentos ni suscripciones.

**Barra fija de compra en móvil (§6.5): evaluada y no implementada.** A favor: la CTA siempre a mano en una ficha larga. En contra, ahora mismo: (1) en PREVIEW solo mostraría un botón desactivado; (2) la ficha no tiene variantes, así que el beneficio es menor; (3) tapa contenido y las precauciones, compite con la barra del navegador en iOS y exige gestionar foco, `aria` y teclado; (4) hay que sincronizarla con la variante seleccionada (Section Rendering API), que solo se puede probar en Shopify. Propuesta: implementarla como **hipótesis C** cuando LIVE esté autorizado, detrás de un ajuste desactivado por defecto, reutilizando `ds-commerce-ready`.

## 5. Landings: estructuras propias

| A · Persona que ronca | B · Descanso en pareja |
|---|---|
| Hero de producto (H1 pregunta) | Hero editorial (H1 emocional, foto lifestyle, precio y CTA) |
| «Snoring, explained»: 3 tarjetas con fuente | «One night, two very different experiences»: 3 momentos |
| Comparativa de opciones | «Four ways to make the conversation easier» |
| Cómo funciona (diagrama) | El producto (hero H2) |
| Detalles (tarjetas) | Cómo funciona |
| FAQ «Before you buy» (7) | FAQ «Questions couples ask» (7, incluye «Can I buy it for my partner?») |
| Cierre «Because you share the night.» | Cierre «Sleep is something you share.» |

Ninguna presenta el producto como solución garantizada para la pareja ni como tratamiento.

## 6. Confianza y reseñas

Las reseñas solo podrán mostrarse si proceden de compradores verificados (app de reseñas con verificación de pedido) y cumplen la norma FTC 16 CFR 465: ni seleccionadas, ni incentivadas sin aviso, ni inventadas. Hasta entonces, el bloque «No made-up reviews» explica la ausencia. **No se ha instalado ninguna app.**

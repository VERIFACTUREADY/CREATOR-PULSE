# V2.1 · Plan de pruebas en Shopify real (EE. UU.)

> **No ejecutado.** No tengo acceso a ninguna tienda (`V21_DATOS_NECESARIOS.md`, punto 22). Este es el guion. Nada de esta lista se da por superado hasta que se ejecute y se guarde la evidencia (capturas, vídeo o HAR) en `qa/shopify-real/AAAA-MM-DD/`.

## 0. Preparación (sin publicar nada)
1. Tienda de desarrollo (o tienda real) con **contraseña activada**. Moneda **USD**, mercado **United States** e idioma **English**.
2. *Settings › Store details:* nombre de la tienda = marca provisional (VINCIRENA) o la definitiva.
3. Subir `dist/tema-descanso-dawn.zip` desde *Online Store › Themes › Add theme › Upload zip*. **No pulsar «Publish».**
4. Crear el producto con el identificador (handle) **`adjustable-mouthpiece`**, en estado **Draft**. Añadir los metacampos (`11_METACAMPOS_Y_CONFIG.md`).
5. Crear las páginas y los menús de la sección 2 de `11_METACAMPOS_Y_CONFIG.md`.
6. En el editor del tema: comprobar que «DS · Product hero» y los módulos tienen seleccionado el producto real. Sin producto, el hero muestra el botón desactivado y ⟦PENDING⟧.
7. Pagos: *Bogus Gateway* (tienda de desarrollo) o modo de prueba de Shopify Payments. **Nunca tarjetas reales.**

## 1. Estados del tema
| # | Prueba | Esperado |
|---|---|---|
| 1.1 | Vista previa del tema en PREVIEW_COMERCIAL | Aviso «Commercial preview»; precio ⟦PENDING⟧ si no está confirmado; botón «Add to cart» desactivado |
| 1.2 | Ver el código fuente de la ficha | Sin `action="/cart/add"`, sin JSON-LD `Product`, sin `og:price` |
| 1.3 | **Petición directa** `POST /cart/add` con el id de la variante (por ejemplo, con `curl` y la cookie de contraseña) | Documentar la respuesta. Si el producto está en *Draft* o no está en el canal Online Store, Shopify debe rechazarla. **La compuerta Liquid no es control de acceso del servidor.** |
| 1.4 | `/cart` y `/checkout` directos | Carrito con aviso; checkout sin productos o bloqueado |
| 1.5 | PROTOTIPO | Web informativa, sin precios |
| 1.6 | LIVE sin frase / con datos incompletos | Aviso rojo «LIVE blocked», sin compra |

## 2. Recorrido de compra (solo en el tema de pruebas, en LIVE y con pagos de prueba)
| # | Recorrido | Dispositivos |
|---|---|---|
| 2.1 | Portada → hero → ficha → variante → cantidad 2 → añadir → `/cart` → checkout → pago de prueba → confirmación | iPhone (Safari iOS), Android (Chrome), escritorio |
| 2.2 | Cambio de variante: precio, imagen y disponibilidad sin recargar | Los tres |
| 2.3 | Producto o variante agotados: botón «Sold out», sin poder añadir | Uno |
| 2.4 | Tarjeta rechazada (Bogus `2`): error legible, sin pedido creado | Uno |
| 2.5 | *Sales tax*: dirección en dos estados distintos; el impuesto aparece en el checkout y no en el precio | Uno |
| 2.6 | Envío: las tarifas del checkout coinciden con «Shipping» del tema | Uno |
| 2.7 | Email de confirmación y página de estado del pedido: en inglés, con plazo, devoluciones y contacto coherentes con el tema | Bandeja real |
| 2.8 | Volver a PREVIEW_COMERCIAL: el formulario desaparece | Uno |

## 3. Indexación (antes de publicar, con autorización)
| # | Prueba | Esperado |
|---|---|---|
| 3.1 | `prelaunch-check.mjs https://<tienda> --cookie "<cookie>" --expect-indexable` | 0 incidencias. Si el ajuste `noindex` sigue activo, el script falla a propósito |
| 3.2 | `/robots.txt` y `/sitemap.xml` | Sin productos de prueba; páginas publicables listadas |
| 3.3 | Contraseña desactivada (solo con la orden del titular) | Las páginas cargan sin la página de contraseña |

## 4. Accesibilidad y móvil reales
VoiceOver en iOS y TalkBack en Android: recorrido portada → ficha → FAQ → contacto. Zoom al 200 %. Teclado en escritorio. Primera pantalla a 375×667 y 390×844 con fotos reales (en local se cumple con marcadores; con fotos hay que volver a comprobarlo).

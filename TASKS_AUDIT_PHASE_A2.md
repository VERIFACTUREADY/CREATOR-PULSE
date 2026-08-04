# Fase A.2 — Cierre de despliegue y acceso privado

Cierra los defectos de la tercera auditoría independiente (4 de agosto de 2026).
No revierte nada de las fases A ni A.1.

**Punto de partida: 475 pruebas de backend y 88 de Vitest en verde.**

---

## Bloque 1 — El frontend de producción evitaba el proxy ✅

- [x] `frontend/Dockerfile` deja de fijar `NEXT_PUBLIC_API_URL=http://localhost:8000`
      por defecto. Una imagen construida sin el argumento salía compilada para
      hablar con el `localhost` **de quien abre la página**
- [x] Vacío se trata como «sin configurar» → rutas relativas `/api/*`
- [x] `docker-compose.yml` usa `${VAR-...}` en vez de `${VAR:-...}`, para que
      una variable definida y vacía se respete
- [x] Prueba que falla si vuelve a colarse un `localhost` por defecto
- [x] Verificado sobre el build real: `NEXT_PUBLIC_API_URL` ya no está horneada

## Bloque 2 — Acceso real a la beta ✅

- [x] Puerta de contraseña con cookie de sesión firmada (HMAC-SHA256)
- [x] Middleware que cierra **todas** las páginas y rutas `/api/*`
- [x] Pantalla `/acceso`, login y logout
- [x] Comparación en tiempo constante de contraseña y firma
- [x] Cookie `HttpOnly`, `SameSite=Lax`, `Secure` en producción, con caducidad
- [x] Rate limit en el login, con poda del mapa de intentos
- [x] Excepciones mínimas: `/acceso`, login/logout, recursos de Next y un
      healthcheck que no revela configuración
- [x] Activada pero incompleta **cierra**, no abre
- [x] Bicep exige `betaAccessPassword` y `betaSessionSecret` como `@secure()`
- [x] Web Crypto en lugar de `node:crypto`: el middleware corre en el edge

## Bloque 3 — Cabeceras de reenvío e identidad ✅

- [x] El proxy borra `Forwarded`, `X-Forwarded-For`, `X-Real-IP`,
      `X-Forwarded-Host/Proto/Port`, `X-Client-IP`, `True-Client-IP`,
      `CF-Connecting-IP` y cualquier copia de la cabecera de servicio
- [x] Identidad de rate limit derivada de la cookie firmada: el cliente no
      puede escogerla
- [x] La API valida formato y longitud (≤64) de toda clave
- [x] Una réplica de API en Bicep, documentado el porqué

## Bloque 4 — Callback OAuth siempre con `state` ✅

- [x] `consume_state()` se ejecuta **antes** de mirar `error` o `code`
- [x] `oauth:channel:{state}` se borra en un `finally`: éxito, error o fallo
- [x] Un `?error=access_denied` sin `state` devuelve `oauth_estado_invalido`

## Bloque 5 — Paginación OAuth sin listas truncadas ✅

- [x] Si se agotan las 5 páginas y sigue habiendo `nextPageToken`, se lanza
      `oauth_identidad_incompleta`, se revoca y no se guarda nada
- [x] JSON inválido o estructura inesperada → error de identidad, con revocación

## Bloque 6 — Cierre de muestra concurrente ✅

- [x] `SELECT ... FOR UPDATE` sobre la fila de `AnalysisRun`
- [x] Prueba con **dos sesiones reales de PostgreSQL** y una barrera
- [x] Comprobado que sin el bloqueo la prueba falla con el `IntegrityError`
      exacto que predijo la auditoría

## Bloque 7 — Coherencia de Azure y secretos ✅

- [x] Corregida la documentación: `proxyAuthSecret` es secreto de Container
      Apps, **no** de Key Vault
- [x] `authorHashSalt` como parámetro `@secure()` obligatorio: el valor de
      ejemplo ya no es posible
- [x] `FRONTEND_URL` derivado de la URL pública del frontend
- [x] Modo propietario documentado y **apagado** mientras falten sus secretos
- [x] `COMMENT_RETENTION_DAYS` fijado en la plantilla

---

## Estado de verificación

Sólo se anota lo ejecutado.

| Comprobación | Resultado |
| --- | --- |
| `ruff check` | Sin incidencias |
| `mypy app` | Sin incidencias (73 ficheros) |
| `pytest` | **492** en verde |
| `alembic upgrade` / `downgrade 0004` | Correctos |
| `alembic --autogenerate` | `upgrade()` vacío: sin deriva |
| `eslint` + `tsc --noEmit` | Sin incidencias |
| Vitest | **115** en verde |
| `npm run build` | Correcto, 15 rutas + middleware |
| Secretos en el bundle | 0 apariciones de los tres secretos |
| `NEXT_PUBLIC_API_URL` horneada | Ya no: se lee en runtime |
| `docker compose config` | Válido |
| E2E demo | **12** en verde |

### Verificaciones manuales sobre el sistema en marcha

**Saneado de cabeceras** (cliente → proxy → servidor eco):

```
enviado por el cliente          lo que llega a la API
X-Forwarded-For: 6.6.6.6    →   (eliminada)
X-Real-IP: 7.7.7.7          →   (eliminada)
Forwarded: for=8.8.8.8      →   (eliminada)
X-Auth-Token: FALSIFICADO   →   secreto-de-servicio real
X-CreatorPulse-Identity:
  identidad-inventada       →   anonimo
```

**Puerta de la beta**:

```
raíz sin sesión      307 -> /acceso
/api/* sin sesión    401
/acceso              200
/api/salud-frontend  200
contraseña errónea   401
contraseña correcta  200 + cookie HttpOnly
con sesión -> raíz   200
con sesión -> API    200
identidad enviada    nIXVFkkvdmUNDuiwbXlWazVjkOQICFPM (32 caracteres, HMAC)
tras cerrar sesión   401
```

## No completado

* **Bicep no validado con herramienta**: no hay `az` ni `bicep` en este
  entorno. La plantilla está revisada a mano; no se ha ejecutado `what-if` ni
  se ha desplegado.
* **Docker Compose sólo validado con `config`**: el registro de imágenes está
  bloqueado por la política de red, así que `docker compose up --build` no
  puede ejecutarse aquí.
* **E2E con la beta activada**: comprobada con peticiones HTTP reales contra el
  servidor en marcha (tabla de arriba), no con Playwright.

# Fase A.1 — Defectos residuales de la segunda auditoría

Cierra los siete puntos obligatorios de la revisión independiente del 4 de
agosto de 2026. No revierte nada de la Fase A.

**Punto de partida: 453 pruebas de backend en verde.**

---

## Bloque 1 — Muestra inmutable en reintentos ✅

- [x] `AnalysisRun.sample_finalized_at`: la muestra se cierra explícitamente
- [x] Un reintento con datos distintos **reutiliza** la muestra, no la amplía
- [x] Un intento fallido a medias no deja restos: se rehace entera
- [x] Restricción única `(run_id, selection_order)` (migración 0005)
- [x] La migración renumera el orden antes de imponer la unicidad
- [x] `register_run_sample` devuelve `SampleRegistration` con filas realmente
      insertadas, tamaño y si se reutilizó
- [x] Tope defensivo: nunca más asociaciones que `max_comments_per_channel`
- [x] `Comment.sampling_bucket` deja de sobrescribirse y se marca obsoleto
- [x] Un reintento con la muestra cerrada **no vuelve a gastar cuota**
- [x] 8 pruebas nuevas → **461 en verde**

## Bloque 2 — OAuth con cuentas de varios canales ✅

- [x] `fetch_authorised_channel_ids()` devuelve el conjunto completo
- [x] Recorre todas las páginas, con tope de 5 y `maxResults=50`
- [x] El callback acepta si el canal está en el conjunto, sea cual sea su orden
- [x] Sin canales → `oauth_sin_canal`; fuera del conjunto → revoca y
      `oauth_canal_no_coincide`
- [x] Un error en una página posterior no da por bueno un conjunto incompleto
- [x] Sólo se registra **cuántos** canales hay, nunca cuáles
- [x] 5 pruebas nuevas → 13 en el fichero de OAuth

## Bloque 3 — Dry run sin escrituras ✅

- [x] `dry_run=True` no ejecuta ningún INSERT/UPDATE/DELETE, ni siquiera su
      propio `MaintenanceRun`. La traza de las simulaciones va al log
- [x] Las purgas reales se siguen registrando y mostrando
- [x] Las pruebas comparan los cuatro recuentos y que la sesión no tenga
      objetos nuevos, modificados ni marcados para borrar
- [x] Comprobado también con el CLI real: 0 registros antes y después de
      `python -m app.cli purgar --simular`

## Bloque 4 — Despliegue y autenticación coherentes ✅

- [x] La API pasa a **ingress interno** (`external: false`)
- [x] El frontend lleva un proxy de servidor en `/api/*` que añade la cabecera
- [x] `AUTH_MODE=trusted_proxy` y las tres variables se fijan en Bicep
- [x] `proxyAuthSecret` es `@secure()`, obligatorio y de mínimo 32 caracteres:
      sin él el despliegue falla antes de crear nada
- [x] Ninguna variable de autenticación lleva prefijo `NEXT_PUBLIC_`
- [x] `COMMENT_RETENTION_DAYS=180` en `.env.example`
- [x] README de infraestructura con el diagrama, el checklist y la limitación
      conocida sobre el rango de red sin VNet propia

## Bloque 5 — Superficie no protegida ✅

- [x] En producción `/docs`, `/redoc` y `/openapi.json` no se publican (404)
- [x] `/` exige la cabecera; `/api/health` y el callback siguen abiertos
- [x] `ENABLE_OWNER_MODE=true` con `AUTH_MODE=none` **impide arrancar**
- [x] El rate limit sólo cree a `X-Forwarded-For` desde redes de confianza
- [x] 12 pruebas nuevas de superficie y rate limit

## Bloque 6 — Consistencia de metadata ✅

- [x] `ix_analysis_run_comment_comment` declarado en `__table_args__`
- [x] `alembic revision --autogenerate` genera un `upgrade()` **vacío**: sin
      deriva. La migración de prueba se borró tras comprobarlo
- [x] No se ha modificado ninguna migración histórica

---

## Estado de verificación

| Comprobación | Resultado |
| --- | --- |
| Punto de partida | 453 en verde |
| Tras el Bloque 1 | `ruff`, `mypy` y 461 pruebas en verde; `0005` aplicada y revertida |
| Tras el Bloque 2 | 13 pruebas de OAuth en verde |
| Tras los Bloques 3-6 | `ruff`, `mypy`, **475** pruebas de backend, `eslint`, `tsc`, **88** de Vitest, build de Next.js y `docker compose config` |
| Flujo autenticado real | API en `APP_ENV=production` + `AUTH_MODE=trusted_proxy`, frontend con proxy de servidor: **12 pruebas E2E en verde** a través del proxy |
| Secreto en el bundle | 0 apariciones en `.next/` tras construir con el secreto en el entorno |
| Migraciones | `0005` aplicada y revertida; `autogenerate` sin deriva |

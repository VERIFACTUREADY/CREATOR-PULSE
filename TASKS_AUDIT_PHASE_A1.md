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

## Bloque 3 — Dry run sin escrituras

- [ ] `dry_run=True` no ejecuta ningún INSERT/UPDATE/DELETE
- [ ] Pruebas que comparan también `MaintenanceRun`

## Bloque 4 — Despliegue y autenticación coherentes

- [ ] Bicep con autenticación funcional o fallo temprano
- [ ] `COMMENT_RETENTION_DAYS` en `.env.example`
- [ ] El secreto nunca llega al navegador

## Bloque 5 — Superficie no protegida

- [ ] `/`, `/docs`, `/redoc`, `/openapi.json` cerrados en producción
- [ ] Modo propietario bloqueado con `AUTH_MODE=none`
- [ ] Rate limit alineado con las redes de confianza

## Bloque 6 — Consistencia de metadata

- [ ] Índice `ix_analysis_run_comment_comment` en el modelo
- [ ] `alembic revision --autogenerate` sin deriva

---

## Estado de verificación

| Comprobación | Resultado |
| --- | --- |
| Punto de partida | 453 en verde |
| Tras el Bloque 1 | `ruff`, `mypy` y 461 pruebas en verde; `0005` aplicada y revertida |
| Tras el Bloque 2 | 13 pruebas de OAuth en verde |

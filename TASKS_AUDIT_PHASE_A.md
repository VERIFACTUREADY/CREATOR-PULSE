# Fase A — Saneamiento tras la auditoría

Plan de trabajo derivado de la auditoría independiente del 4 de agosto de 2026.
Cada bloque se cierra con su propio commit y sus pruebas de regresión.

**Suite base antes de tocar nada: 381 pruebas de backend en verde.**

---

## Bloque 1 — Integridad de la muestra por ejecución ✅

- [x] Entidad `AnalysisRunComment` (`run_id`, `comment_id`, `sampling_bucket`,
      `selection_order`, `selected_at`, único `(run_id, comment_id)`)
- [x] Migración `0003_muestra_por_ejecucion` (no se toca la 0001 ya publicada)
- [x] `CommentRepository.upsert_many` devuelve los IDs reales vía
      `ON CONFLICT DO UPDATE ... RETURNING`
- [x] `register_run_sample`, `list_for_run` y `count_for_run`
- [x] La ingesta ancla la muestra y aplica el tope global **tras** deduplicar
- [x] El orquestador lee sólo por `run_id`, nunca todos los comentarios del vídeo
- [x] El modo demo construye también su muestra por ejecución
- [x] 6 pruebas de regresión → **387 en verde**

## Bloque 2 — Respuestas de comentarios completas ✅

- [x] Iterador paginado `comments.list(parentId=...)` en el cliente
- [x] Comparación con `totalReplyCount` y descarga de las que faltan
- [x] Deduplicación entre respuestas embebidas y paginadas
- [x] Respeto de límites por vídeo y por canal
- [x] Registro de cuota de `comments.list`
- [x] Aviso en calidad de datos cuando una conversación queda a medias
- [x] Un hilo no se paga dos veces aunque la estrategia lo recorra dos veces
- [x] 8 pruebas de regresión → **395 en verde**

## Bloque 3 — Verificación de propiedad en OAuth ✅

- [x] `channels.list(mine=true)` tras el canje del código
- [x] Coincidencia exacta con `youtube_channel_id`
- [x] Si no coincide: no guardar, revocar y redirigir con `oauth_canal_no_coincide`
- [x] Cuenta sin canal → `oauth_sin_canal`, tampoco se guarda
- [x] Un fallo de `channels.list` no persiste nada
- [x] Nunca se registran tokens ni códigos
- [x] 8 pruebas nuevas + la existente actualizada → **403 en verde**

## Bloque 4 — Seguridad de despliegue ✅

- [x] `AUTH_MODE=none|trusted_proxy`, `TRUSTED_AUTH_HEADER`,
      `TRUSTED_AUTH_VALUE`, `TRUSTED_PROXY_NETWORKS`
- [x] `APP_ENV=production` con `AUTH_MODE=none` **no arranca**
- [x] `trusted_proxy` incompleto tampoco arranca en producción
- [x] La cabecera sólo se acepta desde las redes de confianza
- [x] Comparación en tiempo constante del valor
- [x] Protegidas: canales, análisis, comparador, exportaciones, uso de API,
      configuración y OAuth (salvo el retorno de Google)
- [x] `/api/health` sigue abierto
- [x] Aviso al arrancar en desarrollo sin protección
- [x] 21 pruebas de regresión → **424 en verde**

## Bloque 5 — Retención y texto de privacidad ✅

- [x] Corregido el texto que prometía una purga automática inexistente
- [x] Dos políticas: `DATA_RETENTION_DAYS` (resultados) y
      `COMMENT_RETENTION_DAYS` (comentarios brutos)
- [x] Un comentario sólo se borra si ha caducado **y** ninguna ejecución viva
      lo referencia
- [x] `--simular` con recuentos por entidad
- [x] Tabla `maintenance_run` (migración 0004) y fecha de la última purga en la
      interfaz y en `/api/config/public`
- [x] Los canales y vídeos huérfanos se cuentan pero no se borran
- [x] 15 pruebas nuevas + `test_cli` actualizado → **439 en verde**

## Bloque 6 — Puntuación de calidad más honesta ✅

- [x] Entran en la nota: ruido, cohesión de los grupos, confianza media del
      clasificador, backends de embeddings y sentimiento, integridad de la
      muestra, concentración por vídeo, limpieza y tamaño
- [x] Cohesión real de los grupos (similitud coseno al centroide)
- [x] Topes: embeddings hash no llegan a «alta»; sentimiento léxico penaliza;
      ruido >30 % no pasa de «media» sin cohesión fuerte; muestra pequeña
      limitada a «baja»; muestra no anclada = nota 0 y error
- [x] Separadas calidad de datos y confianza semántica del modelo
- [x] Factores y explicaciones expuestos por la API y mostrados en la interfaz
- [x] 14 pruebas de regresión → **453 en verde**
- [x] **Efecto medido**: el canal de demostración pasa de 95,3 % «alta» a
      65,5 % «media», con la explicación visible

## Bloque 7 — Marca

- [ ] Textos visibles unificados como `CreatorPulse AI`
- [ ] Sin renombrar tablas, revisiones de Alembic ni paquetes

---

## Estado de verificación

Se actualiza al cerrar cada bloque. Sólo se anota lo que se ha ejecutado.

| Comprobación | Resultado |
| --- | --- |
| Suite base (antes de la Fase A) | 381 en verde |
| Tras el Bloque 1 | `ruff`, `mypy` y 387 pruebas en verde |
| Tras el Bloque 2 | `ruff`, `mypy` y 395 pruebas en verde |
| Tras el Bloque 3 | `ruff`, `mypy` y 403 pruebas en verde |
| Tras el Bloque 4 | `ruff`, `mypy` y 424 pruebas en verde |
| Tras el Bloque 5 | `ruff`, `mypy`, 439 pruebas, `tsc` y `eslint` en verde |
| Tras el Bloque 6 | `ruff`, `mypy`, 453 pruebas, `tsc`, `eslint` y 85 de Vitest en verde |

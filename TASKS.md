# TASKS — Creator Signal AI

Plan de implementación interno. Estado: `[x]` hecho, `[~]` parcial, `[ ]` pendiente.

## Fase 1 — Fundación
- [x] Estructura del repositorio (backend / frontend / fixtures / infra / scripts)
- [x] Docker Compose (frontend, api, worker, postgres+pgvector, redis) con healthchecks
- [x] FastAPI + configuración por entorno (pydantic-settings)
- [x] Next.js 15 + TypeScript strict + Tailwind
- [x] Redis + cola de trabajos (RQ)
- [x] Healthchecks `/api/health` (API, DB, Redis)
- [x] `.env.example` completo
- [x] Makefile
- [x] CI GitHub Actions

## Fase 2 — Base de datos
- [x] Modelos SQLAlchemy 2.0: Channel, Video, Comment, AnalysisRun, CommentAnalysis,
      TopicCluster, Recommendation, ContentIdea, ApiUsage, Comparison, OAuthToken (scaffold)
- [x] Migración Alembic inicial (+ extensión `vector` condicional)
- [x] Repositorios con upsert idempotente
- [x] Fixtures de demostración (3 canales ficticios)

## Fase 3 — Proveedor YouTube
- [x] Parser de referencias de canal (URL / @handle / UC… / legacy)
- [x] Cliente HTTP con reintentos + backoff exponencial + timeouts
- [x] Resolución de canal, playlist de subidas, vídeos por lotes, comentarios paginados
- [x] Manejo de comentarios desactivados, vídeos privados, cuota agotada
- [x] Estrategias de muestreo de comentarios
- [x] Libro mayor de uso de cuota (ApiUsage)
- [x] Caché / ventana de frescura + refresco incremental
- [x] Tests con la API mockeada (respx)

## Fase 4 — Motor de análisis
- [x] Limpieza de texto (HTML, entidades, unicode, URLs, emojis, anonimización)
- [x] Detección de spam y duplicados / casi-duplicados
- [x] Detección de idioma
- [x] Sentimiento multilingüe configurable (léxico por defecto, transformers opcional)
- [x] Extracción de intenciones (multi-etiqueta)
- [x] Extracción de aspectos (taxonomía + temas dinámicos)
- [x] Embeddings multilingües (hashing por defecto, sentence-transformers opcional)
- [x] Clustering HDBSCAN + fallback aglomerativo + fallback por palabras clave
- [x] Métricas de tendencia normalizadas por ventana
- [x] Métricas de rendimiento de vídeo (robustas, sin división por cero)
- [x] Asociación tema ↔ rendimiento (correlación, nunca causalidad)
- [x] Puntuación de calidad de datos
- [x] Tests unitarios por etapa

## Fase 5 — Motor de recomendaciones
- [x] Objetos de evidencia
- [x] Cálculo de confianza transparente + penalizaciones (vídeo viral dominante, etc.)
- [x] Las 6 categorías de recomendación
- [x] Resúmenes deterministas sin LLM
- [x] Generador de ideas de contenido con evidencia
- [x] Interfaz de proveedor LLM (none / anthropic / openai / ollama)
- [x] Protección frente a inyección de prompts + validación estricta de JSON + reparación
- [x] Tests

## Fase 6 — API y trabajos
- [x] Endpoints REST completos con envoltorio de respuesta consistente
- [x] Envío de análisis a la cola + ejecución en worker
- [x] Sondeo de estado con progreso por etapas
- [x] Endpoints de dashboard, temas, recomendaciones, vídeos, calidad de datos
- [x] Exportación JSON / CSV
- [x] Errores con código, mensaje seguro en español y correlation ID
- [x] Rate limiting y CORS explícito

## Fase 7 — Frontend
- [x] Layout, navegación, modo claro/oscuro, disclaimer
- [x] Lista de canales
- [x] Formulario de nuevo análisis + validación Zod
- [x] Pantalla de progreso con etapas
- [x] Dashboard: Resumen, Temas, Peticiones, Fortalezas, Críticas, Ideas, Vídeos, Calidad
- [x] Comparador de canales
- [x] Uso de API
- [x] Configuración
- [x] Modo demostración etiquetado
- [x] Estados de carga / vacío / error, responsive, accesibilidad

## Fase 8 — Verificación
- [x] `ruff check` + `ruff format --check`
- [x] `mypy`
- [x] `pytest` (unitarios + integración)
- [x] `eslint` + `tsc --noEmit`
- [x] `vitest`
- [x] Playwright E2E sobre modo demostración
- [x] Arranque real del sistema y prueba del flujo completo

## Fase 9 — Preparación de nube
- [x] Bicep para Azure Container Apps + PostgreSQL + Redis + Key Vault + ACR
- [x] Documentación de despliegue y checklist de producción
- [x] Workflow de CI

## Limitaciones conocidas del entorno de construcción
- El registro de imágenes Docker está bloqueado por la política de red del entorno de
  construcción, por lo que `docker compose up --build` no pudo ejecutarse aquí. Los
  Dockerfiles y el `docker-compose.yml` se validaron con `docker compose config` y el
  sistema se verificó de extremo a extremo ejecutando los servicios de forma nativa
  (PostgreSQL 16 + pgvector 0.6, Redis 7, uvicorn, worker RQ, Next.js).

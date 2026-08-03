# Creator Signal AI

Convierte los comentarios y las métricas públicas de un canal de YouTube en
**decisiones de contenido con evidencia**: qué reforzar, qué corregir y qué
publicar a continuación.

No es un panel de gráficas más. Cada conclusión viene acompañada de las cifras
que la respaldan, del número de vídeos que la sostienen y de un nivel de
confianza que baja automáticamente cuando la muestra es pequeña, cuando procede
de un solo vídeo viral o cuando el clasificador tiene poca certeza.

---

## Índice

1. [Qué hace](#1-qué-hace)
2. [Capturas](#2-capturas)
3. [Funcionalidades](#3-funcionalidades)
4. [Limitaciones del modo público](#4-limitaciones-del-modo-público)
5. [Modo propietario](#5-modo-propietario)
6. [Arquitectura](#6-arquitectura)
7. [Requisitos](#7-requisitos)
8. [Instalación con Docker](#8-instalación-con-docker)
9. [Instalación local](#9-instalación-local-sin-docker)
10. [Crear una clave de la API de YouTube](#10-crear-una-clave-de-la-api-de-youtube)
11. [Variables de entorno](#11-variables-de-entorno)
12. [Migraciones de base de datos](#12-migraciones-de-base-de-datos)
13. [Arrancar el worker](#13-arrancar-el-worker)
14. [Ejecutar las pruebas](#14-ejecutar-las-pruebas)
15. [Modo demostración](#15-modo-demostración)
16. [Analizar tu primer canal real](#16-analizar-tu-primer-canal-real)
17. [Consumo de cuota de la API](#17-consumo-de-cuota-de-la-api)
18. [Privacidad](#18-privacidad)
19. [Resolución de problemas](#19-resolución-de-problemas)
20. [Despliegue en Azure](#20-despliegue-en-azure)
21. [Limitaciones actuales](#21-limitaciones-actuales)
22. [Hoja de ruta](#22-hoja-de-ruta)

---

## 1. Qué hace

Creator Signal AI responde a las preguntas que un creador emergente se hace de
verdad:

* ¿Qué le gusta más a mi audiencia de mí o de mi contenido?
* ¿Qué críticas se repiten?
* ¿Qué preguntas o peticiones aparecen una y otra vez?
* ¿Qué temas están ganando fuerza?
* ¿Qué debería publicar a continuación?
* ¿Qué debería probar o mejorar?
* ¿Cuánto puedo fiarme de cada conclusión?

Y, sobre todo, distingue **un patrón real de una anécdota**. Un comentario
aislado nunca genera una recomendación.

---

## 2. Capturas

<!--
Sustituye estos marcadores por capturas reales de tu instalación:

  docs/capturas/01-canales.png          Lista de canales analizados
  docs/capturas/02-nuevo-analisis.png   Formulario con la carga estimada
  docs/capturas/03-progreso.png         Progreso por etapas
  docs/capturas/04-resumen.png          Pestaña Resumen del dashboard
  docs/capturas/05-temas.png            Temas con tendencia y confianza
  docs/capturas/06-ideas.png            Ideas de contenido con evidencia
  docs/capturas/07-calidad.png          Calidad de los datos y sesgos
  docs/capturas/08-comparador.png       Comparación entre canales
-->

| Pantalla | Captura |
| --- | --- |
| Canales | _pendiente_ |
| Nuevo análisis | _pendiente_ |
| Dashboard · Resumen | _pendiente_ |
| Dashboard · Ideas de contenido | _pendiente_ |
| Dashboard · Calidad de los datos | _pendiente_ |
| Comparador | _pendiente_ |

---

## 3. Funcionalidades

### Ingesta

* Acepta URL de canal, `@handle`, ID `UC…` y URLs heredadas `/user/` y `/c/`.
* Usa **sólo la API oficial** de YouTube Data v3. Nada de scraping ni de
  automatización del navegador.
* Recupera los vídeos por la playlist de subidas (1 unidad de cuota) en lugar de
  `search.list` (100 unidades).
* Muestreo configurable: recientes, relevantes o mixto, con deduplicación entre
  estrategias solapadas.
* Reintentos con retroceso exponencial, tiempos de espera y paginación acotada.
* Upserts idempotentes: actualizar un canal **no duplica** vídeos ni comentarios.

### Análisis

Pipeline determinista de diez etapas, todo local y sin depender de ningún LLM:

1. Validación de datos y deduplicación.
2. Limpieza: HTML, entidades, unicode, URLs, emojis, spam y casi-duplicados.
3. Sentimiento multilingüe con negación, intensificadores, emojis, contraste y
   marcadores de ironía.
4. Extracción de intenciones multietiqueta (elogio, crítica, pregunta,
   petición de tutorial, spam, insulto…).
5. Extracción de aspectos sobre una taxonomía amplia, sin forzar etiquetas.
6. Embeddings multilingües y agrupación semántica (HDBSCAN con respaldos).
7. Tendencias normalizadas por cuota, no por recuento absoluto.
8. Métricas de vídeo robustas basadas en medianas.
9. Asociación tema ↔ rendimiento, siempre presentada como correlación.
10. Recomendaciones e ideas de contenido con evidencia y confianza.

### Salida

* Seis tipos de recomendación: refuerza una fortaleza, responde a la demanda,
  corrige un problema, prueba una hipótesis, oportunidad de comunidad y aviso de
  seguridad.
* Ideas de contenido con gancho, formato, experimento, KPI y riesgo de
  sobreinterpretación.
* Sección «Calidad de los datos» que expone los sesgos de la muestra.
* Exportación en JSON y CSV.
* Comparador entre canales analizados, con advertencias explícitas.

---

## 4. Limitaciones del modo público

La API pública de YouTube **no expone**:

* El número de «no me gusta» (retirado por YouTube). No se estima ni se inventa.
* El tiempo de visualización ni la duración media de reproducción.
* Las impresiones ni el porcentaje de clics (CTR).
* Las fuentes de tráfico ni la geografía de la audiencia.
* Los suscriptores ganados o perdidos por vídeo.
* Los comentarios de vídeos privados o con comentarios desactivados.

Además, el análisis trabaja sobre una **muestra**, no sobre todos los
comentarios del canal. La pestaña «Calidad de los datos» indica siempre el
tamaño de la muestra y sus sesgos.

---

## 5. Modo propietario

Está **preparado pero desactivado** (`ENABLE_OWNER_MODE=false`). Cuando se
implemente, permitirá conectar tu propio canal por OAuth de Google, con permisos
de **sólo lectura**, para acceder a métricas privadas de YouTube Analytics:
tiempo de visualización, duración media, porcentaje visto, suscriptores ganados
y perdidos, impresiones, CTR, fuentes de tráfico y geografía.

En esta versión existen:

* Las rutas `/api/oauth/google/*`, que devuelven un error claro mientras esté
  desactivado.
* La tabla `oauth_token`, con columnas para tokens cifrados.
* El endpoint `/api/oauth/status`, que documenta qué aportará.

**Nunca se te pedirá tu contraseña de YouTube ni de Google.** Y mientras el modo
propietario esté desactivado, la aplicación no muestra ninguna métrica de
propietario: no las tiene y no las inventa.

---

## 6. Arquitectura

```mermaid
flowchart TB
    subgraph Navegador
        UI["Next.js 15 · React 19<br/>TypeScript · Tailwind"]
    end

    subgraph Servidor
        API["FastAPI<br/>REST + OpenAPI"]
        WORKER["Worker RQ<br/>pipeline de análisis"]
    end

    subgraph Datos
        PG[("PostgreSQL 16<br/>+ pgvector")]
        REDIS[("Redis<br/>cola de trabajos")]
    end

    subgraph Externo
        YT["YouTube Data API v3"]
        LLM["Proveedor LLM opcional<br/>anthropic · openai · ollama"]
    end

    UI -->|"REST"| API
    API -->|"encola"| REDIS
    API --> PG
    REDIS -->|"consume"| WORKER
    WORKER --> PG
    WORKER -->|"sólo endpoints oficiales"| YT
    WORKER -.->|"opcional: sólo reescribe textos"| LLM

    classDef optional stroke-dasharray: 5 5
    class LLM optional
```

### Pipeline de análisis

```mermaid
flowchart LR
    A["1· Validación"] --> B["2· Limpieza"]
    B --> C["3· Sentimiento"]
    C --> D["4· Intenciones"]
    D --> E["5· Aspectos"]
    E --> F["6· Embeddings<br/>y clustering"]
    F --> G["7· Tendencias"]
    G --> H["8· Métricas<br/>de vídeo"]
    H --> I["9· Asociación<br/>tema ↔ rendimiento"]
    I --> J["10· Recomendaciones<br/>e ideas"]
    J -.->|"opcional"| K["Reescritura con LLM"]
```

El LLM entra **al final** y sólo reescribe texto. Todas las cifras las calcula
el motor determinista, así que el sistema es plenamente utilizable con
`AI_PROVIDER=none`.

### Estructura del repositorio

```text
creator-signal-ai/
├── backend/
│   ├── app/
│   │   ├── api/            # Rutas REST, dependencias y manejo de errores
│   │   ├── core/           # Configuración, logging, errores y privacidad
│   │   ├── db/             # Motor, sesiones y tipos de columna
│   │   ├── models/         # Modelos SQLAlchemy y enumeraciones
│   │   ├── schemas/        # Esquemas Pydantic de entrada y salida
│   │   ├── repositories/   # Acceso a datos con upserts idempotentes
│   │   ├── services/
│   │   │   ├── youtube/    # Parser, cliente, mapeadores, ingesta y cuota
│   │   │   ├── analysis/   # Las diez etapas del pipeline
│   │   │   ├── recommendations/  # Confianza, recomendaciones e ideas
│   │   │   └── ai/         # Proveedores LLM y enriquecimiento
│   │   ├── workers/        # Cola RQ y trabajos
│   │   └── main.py
│   ├── alembic/            # Migraciones
│   └── tests/              # 305 pruebas (unitarias e integración)
├── frontend/
│   ├── app/                # Rutas del App Router
│   ├── components/         # Componentes de interfaz reutilizables
│   ├── features/           # Formulario, progreso y pestañas del dashboard
│   ├── lib/                # Cliente de API, tipos, formato y validación
│   ├── tests/              # 63 pruebas de componentes (Vitest)
│   └── e2e/                # 5 pruebas de extremo a extremo (Playwright)
├── fixtures/               # Datos de demostración (canales ficticios)
├── infra/azure/            # Bicep y documentación de despliegue
├── scripts/                # Generador de datos de demostración
├── docker-compose.yml
├── Makefile
├── .env.example
└── README.md
```

---

## 7. Requisitos

### Con Docker (recomendado)

* Docker 24 o superior con Docker Compose v2.

### Sin Docker

* Python 3.11 o superior
* Node.js 20 o superior (probado con 22)
* PostgreSQL 16 con la extensión `pgvector`
* Redis 7

No hace falta ninguna GPU. Tampoco hace falta ninguna clave de API para probar
el producto: el modo demostración funciona sin credenciales.

---

## 8. Instalación con Docker

```bash
cp .env.example .env
docker compose up --build
```

Cuando termine:

| Servicio | Dirección |
| --- | --- |
| Frontend | <http://localhost:3000> |
| API | <http://localhost:8000> |
| Documentación de la API | <http://localhost:8000/docs> |
| Estado del sistema | <http://localhost:8000/api/health> |

Las migraciones se aplican solas: el servicio `migrate` se ejecuta antes que la
API y el worker, y ambos esperan a que termine correctamente.

Comandos equivalentes con el Makefile:

```bash
make up          # docker compose up --build
make up-d        # en segundo plano
make logs        # ver los registros
make down        # parar
make clean-volumes  # parar y BORRAR los datos
```

---

## 9. Instalación local (sin Docker)

### 9.1 Servicios de datos

```bash
# PostgreSQL con pgvector
sudo apt-get install -y postgresql-16 postgresql-16-pgvector
sudo service postgresql start

sudo -u postgres psql -c "CREATE USER creator_signal WITH PASSWORD 'change-me' SUPERUSER;"
sudo -u postgres createdb -O creator_signal creator_signal
sudo -u postgres psql -d creator_signal -c "CREATE EXTENSION IF NOT EXISTS vector;"

# Redis
redis-server --daemonize yes
```

### 9.2 Backend

```bash
make install-backend
```

Crea `backend/.env` (o el `.env` de la raíz) con los datos locales:

```env
DATABASE_URL=postgresql+psycopg://creator_signal:change-me@127.0.0.1:5432/creator_signal
REDIS_URL=redis://127.0.0.1:6379/0
LOG_JSON=false
ENABLE_DEMO_MODE=true
```

Aplica las migraciones y arranca la API y el worker en dos terminales:

```bash
make migrate
make api      # http://localhost:8000
make worker   # en otra terminal
```

### 9.3 Frontend

```bash
make install-frontend
echo 'NEXT_PUBLIC_API_URL=http://localhost:8000' > frontend/.env.local
make web      # http://localhost:3000
```

### 9.4 Modelos neuronales opcionales

Por defecto el análisis usa un backend **determinista y sin descargas**
(embeddings por n-gramas de caracteres y sentimiento léxico multilingüe). Para
usar modelos neuronales:

```bash
make install-ml
```

Y en el `.env`:

```env
EMBEDDING_BACKEND=sentence-transformers
SENTIMENT_BACKEND=transformers
```

Si el modelo no puede cargarse, el sistema **degrada automáticamente** al motor
determinista y lo registra; el análisis nunca se interrumpe por esto.

---

## 10. Crear una clave de la API de YouTube

El modo demostración no la necesita. Para analizar canales reales:

### 10.1 Habilitar la API

1. Entra en <https://console.cloud.google.com/>.
2. Crea un proyecto nuevo (o elige uno existente).
3. Ve a **APIs y servicios → Biblioteca**.
4. Busca **YouTube Data API v3** y pulsa **Habilitar**.

### 10.2 Crear la clave

1. Ve a **APIs y servicios → Credenciales**.
2. **Crear credenciales → Clave de API**.
3. Copia la clave.

### 10.3 Restringir la clave (importante)

1. Pulsa **Restringir clave** en la clave recién creada.
2. En **Restricciones de API**, elige **Restringir clave** y marca únicamente
   **YouTube Data API v3**.
3. En **Restricciones de aplicación**, si vas a desplegarla en un servidor,
   restringe por dirección IP.
4. Guarda.

### 10.4 Configurarla

```env
YOUTUBE_API_KEY=AIza...
```

La clave se queda **siempre en el servidor**. El frontend nunca la recibe: el
endpoint `/api/config/public` sólo informa de si hay una clave configurada,
nunca de su valor.

---

## 11. Variables de entorno

Todas están documentadas en [`.env.example`](.env.example). Las más relevantes:

### Aplicación

| Variable | Por defecto | Para qué |
| --- | --- | --- |
| `APP_ENV` | `development` | En `production` oculta los detalles técnicos de los errores |
| `CORS_ORIGINS` | `http://localhost:3000` | Orígenes permitidos, separados por comas. Nunca se usa `*` |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | URL de la API que usa el navegador |

### Datos

| Variable | Por defecto | Para qué |
| --- | --- | --- |
| `DATABASE_URL` | — | Cadena de conexión de PostgreSQL |
| `PGVECTOR_MODE` | `auto` | `auto` usa pgvector si existe; `false` fuerza JSONB |
| `REDIS_URL` | — | Cola de trabajos |

### YouTube

| Variable | Por defecto | Para qué |
| --- | --- | --- |
| `YOUTUBE_API_KEY` | vacío | Sin ella sólo funciona el modo demostración |
| `YOUTUBE_MAX_VIDEOS_PER_ANALYSIS` | `20` | Vídeos por análisis |
| `YOUTUBE_MAX_COMMENTS_PER_VIDEO` | `250` | Comentarios por vídeo |
| `YOUTUBE_MAX_COMMENTS_PER_CHANNEL` | `3000` | Tope global por análisis |
| `YOUTUBE_INCLUDE_REPLIES` | `false` | Incluir respuestas multiplica el consumo |
| `YOUTUBE_CACHE_TTL_HOURS` | `24` | Ventana de frescura antes de volver a pedir datos |
| `YOUTUBE_HARD_MAX_*` | `50` / `500` / `10000` | Máximos que el formulario no puede superar |

### Análisis

| Variable | Por defecto | Para qué |
| --- | --- | --- |
| `EMBEDDING_BACKEND` | `hashing` | `hashing` (sin descargas) o `sentence-transformers` |
| `SENTIMENT_BACKEND` | `lexicon` | `lexicon` (sin descargas) o `transformers` |
| `ENABLE_TOXICITY_ANALYSIS` | `true` | Señal de seguridad para el creador |
| `CLUSTERING_MIN_COMMENTS` | `30` | Mínimo para usar HDBSCAN en vez del respaldo |

### IA opcional

| Variable | Por defecto | Para qué |
| --- | --- | --- |
| `AI_PROVIDER` | `none` | `none`, `anthropic`, `openai` u `ollama` |
| `ANTHROPIC_API_KEY` / `ANTHROPIC_MODEL` | vacío | Proveedor Anthropic |
| `OPENAI_API_KEY` / `OPENAI_MODEL` | vacío | Proveedor OpenAI |
| `OLLAMA_BASE_URL` / `OLLAMA_MODEL` | `http://host.docker.internal:11434` | Modelo local, sin coste por llamada |

### Privacidad

| Variable | Por defecto | Para qué |
| --- | --- | --- |
| `DATA_RETENTION_DAYS` | `90` | Antigüedad máxima de los análisis |
| `ANONYMIZE_COMMENT_AUTHORS` | `true` | Oculta handles, correos y URLs en los ejemplos |
| `AUTHOR_HASH_SALT` | `change-me-author-salt` | **Cámbiala en producción** |

---

## 12. Migraciones de base de datos

```bash
make migrate                          # aplica todas las migraciones pendientes
make migration m="añade tabla x"      # crea una migración nueva
make downgrade                        # revierte la última
```

Con Docker las migraciones se aplican solas al arrancar. Para lanzarlas a mano:

```bash
docker compose run --rm migrate
```

La migración inicial intenta crear la extensión `vector`. Si el servidor no la
tiene y `PGVECTOR_MODE=auto`, las columnas de embeddings se crean como `JSONB` y
todo sigue funcionando.

---

## 13. Arrancar el worker

El worker es quien ejecuta el análisis. **Sin él, los análisis se quedan en
cola y nunca terminan.**

```bash
make worker
# o directamente:
cd backend && .venv/bin/python -m app.workers.main
```

Con Docker arranca solo como servicio `worker`. Para ver sus registros:

```bash
docker compose logs -f worker
```

Cada réplica procesa un trabajo a la vez. Para más concurrencia, arranca varios
procesos: RQ reparte los trabajos entre todos.

---

## 14. Ejecutar las pruebas

```bash
make check          # linters + tipos + todas las pruebas
```

O por partes:

```bash
make lint           # ruff + eslint
make typecheck      # mypy + tsc
make test-backend   # pytest (unitarias e integración)
make test-frontend  # vitest
make e2e            # playwright (requiere el sistema en marcha)
```

Las pruebas de integración del backend necesitan PostgreSQL. Si no está
disponible, se **omiten** con un mensaje claro en lugar de fallar. Crean su
propia base de datos `creator_signal_test`.

La prueba de extremo a extremo necesita la API, el worker y el frontend en
marcha. Si tienes un Chromium del sistema:

```bash
PLAYWRIGHT_CHROMIUM_PATH=/ruta/a/chromium npx playwright test
```

---

## 15. Modo demostración

Permite probar el producto entero **sin ninguna credencial**.

1. Abre <http://localhost:3000/demostracion>.
2. Elige uno de los tres canales ficticios.
3. Pulsa **Analizar este canal**.

Los canales incluidos:

| Canal | Temática | Qué contiene |
| --- | --- | --- |
| `@luciaglowdemo` | Belleza y estilo de vida | Elogios sobre la mirada, peticiones de tutoriales, crítica recurrente del volumen de la música |
| `@pixelraptordemo` | Gaming | Humor muy valorado, peticiones de series por capítulos, críticas de duración, un vídeo viral dominante |
| `@codigoclarodemo` | Tecnología | Elogios sobre la claridad, peticiones de contenido para principiantes, críticas del ritmo |

Los tres traen comentarios en español y en inglés, spam, comentarios ofensivos,
un vídeo con los comentarios desactivados y una tendencia temporal real.

Dos cosas importantes:

* Los datos están **siempre etiquetados** como «Datos de demostración» en la
  interfaz, y nunca se mezclan con datos reales sin indicarlo.
* **No hay resultados precalculados.** Las fixtures pasan por exactamente el
  mismo pipeline que un canal real, así que lo que ves es análisis de verdad
  sobre datos ficticios.

Para regenerar las fixtures (el generador es determinista):

```bash
make fixtures
```

---

## 16. Analizar tu primer canal real

1. Configura `YOUTUBE_API_KEY` (ver [sección 10](#10-crear-una-clave-de-la-api-de-youtube))
   y reinicia la API y el worker.
2. Entra en <http://localhost:3000/nuevo-analisis>.
3. Pega la URL del canal, su `@handle` o su ID `UC…`.
4. Ajusta el alcance. Para el primer análisis, empieza pequeño:
   * 10 vídeos
   * 100 comentarios por vídeo
   * Estrategia **mixta**
   * Respuestas **desactivadas**
5. Lee el aviso de carga estimada: te dice cuántas unidades de cuota consumirá.
6. Pulsa **Analizar** y sigue el progreso por etapas.

Cuando termine, empieza por la pestaña **Calidad de los datos**: te dirá si la
muestra da para sacar conclusiones antes de que actúes sobre ellas.

Para actualizar un canal, usa **Actualizar** en la lista de canales. El refresco
es idempotente: actualiza los datos existentes sin duplicar nada.

---

## 17. Consumo de cuota de la API

Un proyecto nuevo de Google Cloud tiene **10 000 unidades diarias**. Costes
oficiales por llamada:

| Endpoint | Unidades |
| --- | --- |
| `channels.list` | 1 |
| `playlistItems.list` | 1 |
| `videos.list` | 1 |
| `commentThreads.list` | 1 |
| `comments.list` | 1 |
| `search.list` | **100** |

Creator Signal AI evita `search.list` salvo para resolver URLs personalizadas
heredadas que la API no puede resolver de otra forma.

Ejemplo real: 20 vídeos × 250 comentarios ≈ **82 unidades**, es decir unos 120
análisis al día con la cuota por defecto.

Para reducir el consumo:

* Baja el número de vídeos y de comentarios por vídeo.
* Deja las respuestas desactivadas.
* Aprovecha la caché: los datos de canal recientes se reutilizan durante
  `YOUTUBE_CACHE_TTL_HOURS`.
* Usa el modo demostración para probar la interfaz (consume cero).

La pantalla **Uso de API** muestra el consumo estimado. Es una estimación
calculada por la propia aplicación a partir de sus llamadas: **no refleja la
cuota real restante** de tu proyecto, que sólo puedes consultar en la consola de
Google Cloud.

---

## 18. Privacidad

* Sólo se analizan **datos públicos** obtenidos de la API oficial.
* De los autores de comentarios se guarda **únicamente un identificador con
  hash** (SHA-256 con sal), necesario para deduplicar y detectar spam. No se
  almacenan sus nombres públicos ni sus fotos de perfil.
* Los ejemplos que se muestran en la interfaz están anonimizados: se sustituyen
  handles, correos, teléfonos y URLs.
* Los comentarios públicos **no se usan para entrenar ningún modelo**.
* Si activas un proveedor de IA externo, se le envían resúmenes y unos pocos
  ejemplos ya anonimizados, nunca la base de datos completa.
* Puedes eliminar un canal con todos sus datos desde la pantalla «Canales», y
  un análisis concreto desde la API.
* Los análisis con más de `DATA_RETENTION_DAYS` días se pueden purgar con el
  trabajo `purge_expired_data_job`.
* Los registros nunca incluyen claves de API, tokens, prompts completos ni
  datasets de comentarios.

La detección de toxicidad existe como **función de seguridad para el creador**
(revisar la moderación), no como herramienta de vigilancia. No identifica
autores, y ninguna recomendación de contenido se basa en comentarios de acoso.

---

## 19. Resolución de problemas

### El análisis se queda en «En cola» y no avanza

El worker no está funcionando.

```bash
docker compose logs worker          # con Docker
make worker                         # en local
curl http://localhost:8000/api/health
```

### «No se ha podido encolar el análisis»

Redis no está accesible. Comprueba `REDIS_URL` y que el servicio responde:

```bash
redis-cli ping    # debe responder PONG
```

### «No hay ninguna clave de la API de YouTube configurada»

Falta `YOUTUBE_API_KEY` en el `.env`, o la API no se reinició tras añadirla.
Puedes seguir usando el modo demostración sin clave.

### «La clave de la API de YouTube no es válida»

Casi siempre significa que la **YouTube Data API v3 no está habilitada** en el
proyecto de Google Cloud, o que la clave está restringida a otra API. Revisa la
[sección 10](#10-crear-una-clave-de-la-api-de-youtube).

### «Se ha agotado la cuota diaria»

La cuota se reinicia a medianoche en el Pacífico. Mientras tanto, reduce el
alcance del análisis o usa el modo demostración.

### «No se ha encontrado ningún canal público con esa referencia»

* Comprueba que el `@handle` está bien escrito (sin espacios).
* Las URLs `/c/NombrePersonalizado` muy antiguas a veces no se pueden resolver:
  usa el ID `UC…`, que aparece en el código fuente de la página del canal.
* Una URL de vídeo (`/watch?v=…`) no es una URL de canal.

### El análisis termina pero con pocos temas

Es el comportamiento correcto con muestras pequeñas: por debajo de
`CLUSTERING_MIN_COMMENTS` se usa la agregación por palabras clave y se avisa en
«Calidad de los datos». Amplía el número de vídeos y comentarios.

### `psycopg.OperationalError` al arrancar

PostgreSQL no está accesible. Con Docker, espera a que el healthcheck pase; en
local, comprueba que el servicio está en marcha y que `DATABASE_URL` apunta al
host correcto (`postgres` dentro de Docker, `127.0.0.1` en local).

### La extensión `vector` no existe

Con `PGVECTOR_MODE=auto` no es un problema: las columnas de embeddings se crean
como JSONB. Para usar pgvector, instala `postgresql-16-pgvector` (o usa la
imagen `pgvector/pgvector:pg16`) y ejecuta
`CREATE EXTENSION IF NOT EXISTS vector;`.

### El frontend no ve la API

Revisa `NEXT_PUBLIC_API_URL`. Se incrusta **en tiempo de construcción**, así que
si lo cambias hay que reconstruir el frontend. Comprueba también que
`CORS_ORIGINS` incluye la URL del frontend.

---

## 20. Despliegue en Azure

La infraestructura está preparada pero **no se despliega automáticamente**: crea
recursos de pago. Ver [`infra/azure/README.md`](infra/azure/README.md) para el
procedimiento completo, el mapeo de secretos, las notas de escalado del worker,
los factores de coste y la lista de comprobación previa a producción.

Resumen: Azure Container Apps para frontend, API y worker; Azure Database for
PostgreSQL Flexible Server con `pgvector`; Azure Cache for Redis; Key Vault para
los secretos; Container Registry para las imágenes; y Log Analytics con
Application Insights para la observabilidad. Se usa **Bicep**, y el porqué de esa
decisión está documentado en el README de infraestructura.

---

## 21. Limitaciones actuales

* **Sólo YouTube.** No hay integración con Instagram, TikTok ni X.
* **Sólo datos públicos.** El modo propietario está preparado pero no
  implementado.
* **Sin autenticación de usuarios.** La instalación es de un solo inquilino; no
  la expongas a internet sin poner un proxy con autenticación delante.
* **El rate limiting es por proceso.** Con varias réplicas de la API conviene
  moverlo a Redis.
* **La detección de idioma es heurística**, no un modelo estadístico. Cubre
  español, inglés, portugués y francés; el resto queda como «no detectado».
* **El sentimiento por defecto es léxico.** Es explicable y rápido, pero un
  modelo neuronal capta mejor la ironía. Se activa con el extra `ml`.
* **La ventana de tendencia se parte por la mediana** de las fechas de la
  muestra, no por un calendario fijo.
* **Las asociaciones tema ↔ rendimiento son correlaciones** sobre muestras
  pequeñas. Están etiquetadas como hipótesis a propósito.
* El almacenamiento cifrado de tokens OAuth está **diseñado, no implementado**:
  la tabla existe pero no se usa.

---

## 22. Hoja de ruta

**Siguiente fase — modo propietario**

* Flujo OAuth de Google completo con almacenamiento cifrado de tokens (Fernet).
* Adaptador de YouTube Analytics: tiempo de visualización, duración media,
  impresiones, CTR y fuentes de tráfico.
* Correlación entre los temas de los comentarios y la retención real.

**Después**

* Autenticación multiusuario y separación por inquilino.
* Rate limiting distribuido en Redis.
* Análisis incremental: analizar sólo los comentarios nuevos desde la última
  ejecución.
* Alertas por correo cuando aparece una crítica nueva recurrente.
* Seguimiento de experimentos: registrar la hipótesis y medir el resultado
  automáticamente en el análisis siguiente.
* Informes comparativos entre dos ejecuciones del mismo canal.
* Más idiomas en los léxicos de sentimiento e intención.

---

## Aviso

> Creator Signal AI ofrece análisis automatizados basados en una muestra de
> comentarios y métricas públicas. Las clasificaciones y recomendaciones pueden
> contener errores y no garantizan crecimiento. Las asociaciones estadísticas no
> demuestran causalidad.

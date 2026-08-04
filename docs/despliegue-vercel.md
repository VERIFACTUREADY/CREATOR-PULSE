# Despliegue en Vercel

Este repositorio incluye un [`vercel.json`](../vercel.json) que declara los dos
servicios del proyecto —el frontend de Next.js y la API de FastAPI— y enruta el
tráfico entre ellos.

> **Lee primero la sección «Qué no funciona en Vercel».** El panel, el modo
> demostración y toda la API de lectura pueden funcionar; el **análisis de un
> canal no**, porque necesita un proceso trabajador de larga duración que la
> plataforma no ofrece. Es un límite de arquitectura, no de configuración.

---

## 1. La configuración

```json
{
  "$schema": "https://openapi.vercel.sh/vercel.json",
  "services": {
    "frontend": { "root": "frontend/", "framework": "nextjs" },
    "backend": {
      "root": "backend/",
      "framework": "fastapi",
      "entrypoint": "app.main:app"
    }
  },
  "rewrites": [
    { "source": "/api/(.*)", "destination": { "service": "backend" } },
    { "source": "/(.*)", "destination": { "service": "frontend" } }
  ]
}
```

* El **entrypoint** es `app.main:app`: relativo a la raíz del servicio
  (`backend/`), el módulo es `app/main.py` y la instancia se crea al final del
  fichero con `app = create_app()`.
* **No se transforma la ruta.** La API ya monta todos sus routers bajo `/api`
  (`app.include_router(..., prefix="/api")`), así que el servicio debe recibir
  la ruta original. Si se añadiera un `transforms` de `request.path` que
  quitara el prefijo, todos los endpoints devolverían 404.
* En el panel de Vercel, el **framework del proyecto debe estar puesto en
  «Services»**. Es un ajuste del proyecto, no del fichero.

## 2. Rutas que quedan fuera

Con el enrutado anterior sólo `/api/*` llega al backend. La documentación
interactiva de FastAPI (`/docs`, `/redoc`, `/openapi.json`) iría al frontend y
devolvería 404. Si la quieres pública, añade sus rutas a `rewrites`:

```json
{ "source": "/(docs|redoc|openapi.json)", "destination": { "service": "backend" } }
```

Piénsalo dos veces: publicar el esquema completo de la API no siempre interesa.

## 3. Variables de entorno

Se configuran en **Project Settings → Environment Variables**. Ninguna clave
debe ir al repositorio.

### Imprescindibles

| Variable | Valor | Nota |
| --- | --- | --- |
| `DATABASE_URL` | `postgresql+psycopg://usuario:clave@host/base` | PostgreSQL gestionado y accesible desde internet (Neon, Supabase…). Debe admitir la extensión `pgvector`, o usar `PGVECTOR_MODE=false` |
| `REDIS_URL` | `redis://…` | Redis gestionado (Upstash u otro) |
| `APP_ENV` | `production` | Oculta los detalles técnicos de los errores |
| `AUTHOR_HASH_SALT` | cadena larga y aleatoria | **Cámbiala.** Es la sal del hash de los identificadores de autor |
| `CORS_ORIGINS` | `https://tu-dominio.vercel.app` | Con un solo origen no hace falta para el navegador, pero deja el valor correcto en lugar del de desarrollo |

### Opcionales

| Variable | Para qué |
| --- | --- |
| `YOUTUBE_API_KEY` | Sin ella sólo funciona el modo demostración |
| `PGVECTOR_MODE` | `false` si tu PostgreSQL no tiene `pgvector` |
| `AI_PROVIDER` y su clave | Enriquecimiento opcional con un LLM |
| `ENABLE_OWNER_MODE`, `GOOGLE_OAUTH_*`, `OAUTH_TOKEN_ENCRYPTION_KEY` | Modo propietario. La URI de redirección debe apuntar al dominio de Vercel: `https://tu-dominio.vercel.app/api/oauth/google/callback` |

**No** hace falta definir `NEXT_PUBLIC_API_URL`: al no estar definida, el
frontend usa rutas relativas (`/api/...`) contra su propio origen, que es
justo lo que hace el enrutado de `vercel.json`. Si la defines apuntando a
`http://localhost:8000`, romperás el despliegue.

## 4. Migraciones

Vercel no ejecuta Alembic. Aplica el esquema desde tu máquina apuntando a la
base de datos de producción, antes del primer despliegue:

```bash
cd backend
DATABASE_URL="postgresql+psycopg://…" .venv/bin/alembic upgrade head
```

## 5. Qué no funciona en Vercel

Esto no es pesimismo: es cómo está construida la aplicación.

1. **El análisis de canales no llega a completarse.** `POST /api/channels/analyse`
   encola un trabajo en Redis y devuelve `202`. Quien lo ejecuta es el worker de
   RQ (`python -m app.workers.main`), un **proceso de larga duración**. Vercel
   ejecuta funciones que terminan con la respuesta, así que no hay dónde
   alojarlo: los análisis se quedarían en «En cola» para siempre. Necesitas un
   worker en otro sitio (una VM, Azure Container Apps, Fly.io, Railway…) que
   apunte al mismo Redis y a la misma base de datos.
2. **El modo demostración no encuentra sus datos.** Los ficheros de
   `fixtures/` están en la raíz del repositorio, fuera de `backend/`, que es la
   raíz del servicio. No entran en el paquete de la función. Habría que mover o
   copiar `fixtures/` dentro de `backend/` y ajustar `FIXTURES_DIR`.
3. **El tamaño del paquete es un riesgo real.** El backend depende de
   `scikit-learn`, `numpy` y `scipy`, que rondan los cientos de megabytes
   descomprimidos y pueden superar el límite de las funciones Python. Si el
   despliegue falla por tamaño, ahí está el motivo.
4. **Arranque en frío en cada invocación.** El motor de análisis y los léxicos
   se cargan por proceso; en funciones sin estado eso se paga a menudo.

Si quieres el sistema completo funcionando, el despliegue con contenedores
—`docker compose` o el Bicep de Azure de [`infra/azure`](../infra/azure)— es
el camino previsto, porque el worker es un servicio de primera clase.

## 6. Qué se ha comprobado y qué no

* **Comprobado en local**: que el frontend, servido desde un dominio que no es
  `localhost` y con un proxy que manda `/api/*` a FastAPI y el resto a Next.js,
  completa un análisis de demostración entero **sin emitir ni una sola petición
  fuera de su propio origen**. Es la prueba `frontend/e2e/mismo-origen.spec.ts`.
* **Comprobado**: que `vercel.json` es JSON válido y que el entrypoint declarado
  existe y expone `app`.
* **No comprobado**: el despliegue real en Vercel. No se ha ejecutado desde
  este repositorio, así que el fichero puede necesitar ajustes cuando la
  plataforma cambie el esquema de servicios.

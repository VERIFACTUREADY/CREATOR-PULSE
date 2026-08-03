# Despliegue en Azure

Este directorio contiene la infraestructura **preparada, no desplegada**. Nada
se crea automáticamente: todos los comandos son manuales y algunos generan
recursos de pago.

## Por qué Bicep y no Terraform

Se ha elegido **Bicep**:

* El destino es exclusivamente Azure, así que la portabilidad de Terraform no
  aporta valor aquí.
* No hace falta gestionar un backend de estado remoto (Azure Resource Manager
  guarda el estado del despliegue).
* La CLI de Azure ya trae el compilador de Bicep, sin dependencias extra en CI.

Si en el futuro se añade otro proveedor de nube, migrar a Terraform sería lo
razonable.

## Recursos que crea

| Recurso | Servicio | Para qué |
| --- | --- | --- |
| `*-api` | Azure Container Apps | API FastAPI, con ingress público |
| `*-worker` | Azure Container Apps | Worker de análisis, sin ingress |
| `*-web` | Azure Container Apps | Frontend Next.js |
| `*-pg` | Azure Database for PostgreSQL Flexible Server | Base de datos con `pgvector` |
| `*-redis` | Azure Cache for Redis | Cola de trabajos |
| `*acr*` | Azure Container Registry | Imágenes de contenedor |
| `*kv*` | Azure Key Vault | Secretos |
| `*-logs` / `*-insights` | Log Analytics y Application Insights | Observabilidad |

## Requisitos previos

```bash
az --version          # Azure CLI 2.60 o superior
az login
az account set --subscription "<ID de tu suscripción>"
```

## 1. Crear el grupo de recursos

```bash
az group create \
  --name rg-creator-signal-dev \
  --location westeurope
```

## 2. Validar la plantilla (no crea nada)

```bash
az deployment group what-if \
  --resource-group rg-creator-signal-dev \
  --template-file infra/azure/main.bicep \
  --parameters @infra/azure/parameters.dev.json \
  --parameters postgresAdminPassword="$(openssl rand -base64 24)"
```

## 3. Desplegar

> Este paso **crea recursos de pago**.

```bash
PG_PASSWORD="$(openssl rand -base64 24)"

az deployment group create \
  --resource-group rg-creator-signal-dev \
  --template-file infra/azure/main.bicep \
  --parameters @infra/azure/parameters.dev.json \
  --parameters postgresAdminPassword="$PG_PASSWORD" \
  --parameters youtubeApiKey="$YOUTUBE_API_KEY"
```

Guarda `PG_PASSWORD` en un gestor de secretos: la plantilla la escribe en Key
Vault, pero no se puede recuperar del despliegue.

## 4. Construir y publicar las imágenes

```bash
ACR=$(az deployment group show \
  --resource-group rg-creator-signal-dev \
  --name main \
  --query properties.outputs.containerRegistryLoginServer.value -o tsv)

az acr login --name "${ACR%%.*}"

docker build -f backend/Dockerfile -t "$ACR/creator-signal-backend:latest" .
docker build -f frontend/Dockerfile -t "$ACR/creator-signal-frontend:latest" ./frontend

docker push "$ACR/creator-signal-backend:latest"
docker push "$ACR/creator-signal-frontend:latest"
```

Vuelve a ejecutar el despliegue (paso 3) para que las Container Apps tomen las
imágenes nuevas, o actualiza sólo la revisión:

```bash
az containerapp update \
  --name creatorsignal-dev-api \
  --resource-group rg-creator-signal-dev \
  --image "$ACR/creator-signal-backend:latest"
```

## 5. Migraciones de base de datos

Las migraciones **no** se ejecutan solas en Azure. Lánzalas como un trabajo
puntual con la misma imagen del backend:

```bash
az containerapp job create \
  --name creatorsignal-dev-migrate \
  --resource-group rg-creator-signal-dev \
  --environment creatorsignal-dev-env \
  --trigger-type Manual \
  --replica-timeout 600 \
  --image "$ACR/creator-signal-backend:latest" \
  --command "alembic" "upgrade" "head" \
  --secrets "database-url=<valor de Key Vault>" \
  --env-vars "DATABASE_URL=secretref:database-url"

az containerapp job start \
  --name creatorsignal-dev-migrate \
  --resource-group rg-creator-signal-dev
```

Comprueba que `pgvector` está disponible antes de migrar:

```sql
SHOW azure.extensions;          -- debe incluir VECTOR
CREATE EXTENSION IF NOT EXISTS vector;
```

Si la extensión no estuviera disponible, la aplicación sigue funcionando: el
tipo `EmbeddingVector` degrada a JSONB automáticamente cuando
`PGVECTOR_MODE=auto`.

## Variables de entorno de producción

| Variable | Origen | Notas |
| --- | --- | --- |
| `DATABASE_URL` | Key Vault (`database-url`) | Incluye `sslmode=require` |
| `REDIS_URL` | Secreto de la Container App | Usa `rediss://` (TLS) |
| `YOUTUBE_API_KEY` | Key Vault (`youtube-api-key`) | Restringida por API en Google Cloud |
| `APP_ENV` | Literal | `production`: oculta los detalles técnicos de los errores |
| `CORS_ORIGINS` | Literal | URL exacta del frontend, nunca `*` |
| `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` | Key Vault | Sólo si se activa la IA externa |
| `AUTHOR_HASH_SALT` | Key Vault | **Cámbiala**: la de ejemplo no es secreta |
| `OAUTH_TOKEN_ENCRYPTION_KEY` | Key Vault | Sólo cuando se implemente el modo propietario |

## Escalado del worker

* `minReplicas: 1` es obligatorio. Si el worker escala a cero, los análisis
  encolados se quedan sin procesar hasta que arranque una réplica.
* Cada réplica procesa un trabajo a la vez. Para más concurrencia, sube
  `maxReplicas`: RQ reparte los trabajos entre todas.
* El worker necesita más memoria que la API (2 GiB) porque carga los modelos de
  análisis. Si activas el extra `ml` (sentence-transformers), sube a 4 GiB.

## Qué encarece la factura

Ordenado por impacto típico:

1. **PostgreSQL Flexible Server**: es el recurso que está siempre encendido.
   `Standard_B1ms` basta para desarrollo.
2. **Worker de Container Apps**: al no poder escalar a cero, siempre hay una
   réplica facturando CPU y memoria.
3. **Azure Cache for Redis**: el nivel `Basic C0` es suficiente para la cola.
4. **API y frontend**: escalan a cero en desarrollo, así que su coste es
   proporcional al uso.
5. **Log Analytics**: se factura por GB ingerido. Con `LOG_LEVEL=INFO` el
   volumen es bajo; evita `DEBUG` en producción.
6. **Proveedor de IA externo**: no es un recurso de Azure, pero si activas
   `AI_PROVIDER`, cada análisis hace varias llamadas al modelo.

## Eliminar todos los recursos

```bash
az group delete --name rg-creator-signal-dev --yes --no-wait
```

Key Vault tiene borrado suave activado. Para liberar el nombre del todo:

```bash
az keyvault purge --name <nombre del key vault> --location westeurope
```

## Lista de comprobación antes de producción

- [ ] `APP_ENV=production` (oculta los detalles técnicos en las respuestas de error).
- [ ] `CORS_ORIGINS` apunta sólo al dominio del frontend.
- [ ] `AUTHOR_HASH_SALT` cambiada por un valor aleatorio y guardada en Key Vault.
- [ ] La clave de la API de YouTube está restringida a la YouTube Data API v3 en la consola de Google Cloud.
- [ ] `POSTGRES_PASSWORD` generada aleatoriamente y sólo en Key Vault.
- [ ] Copias de seguridad de PostgreSQL con la retención adecuada.
- [ ] Alertas de Application Insights sobre errores 5xx y fallos del worker.
- [ ] Revisada la política de retención de datos (`DATA_RETENTION_DAYS`).
- [ ] `ENABLE_DEMO_MODE=false` si no quieres exponer los datos ficticios.
- [ ] Las migraciones se han aplicado antes de dirigir tráfico a la versión nueva.

// Creator Signal AI — infraestructura de Azure.
//
// Decisión: se usa **Bicep** en lugar de Terraform porque el destino es
// exclusivamente Azure, no requiere gestionar estado remoto y el despliegue se
// puede hacer con la CLI de Azure ya instalada en cualquier agente de CI.
//
// Este fichero NO se despliega automáticamente. Ver infra/azure/README.md.

targetScope = 'resourceGroup'

@description('Prefijo de los recursos. Debe ser corto y en minúsculas.')
@minLength(3)
@maxLength(12)
param namePrefix string = 'creatorsignal'

@description('Región de Azure.')
param location string = resourceGroup().location

@description('Entorno lógico.')
@allowed(['dev', 'prod'])
param environment string = 'dev'

@description('Etiqueta de las imágenes de contenedor a desplegar.')
param imageTag string = 'latest'

@description('Usuario administrador de PostgreSQL.')
param postgresAdminUser string = 'creator_signal'

@description('Contraseña del administrador de PostgreSQL. Pásala como secreto.')
@secure()
param postgresAdminPassword string

@description('Clave de la YouTube Data API. Se guarda en Key Vault.')
@secure()
param youtubeApiKey string = ''

@description('Objeto (principal) que podrá leer los secretos de Key Vault.')
param keyVaultAdminObjectId string = ''

var suffix = uniqueString(resourceGroup().id)
var baseName = '${namePrefix}-${environment}'
var tags = {
  application: 'creator-signal-ai'
  environment: environment
  managedBy: 'bicep'
}

// --- Observabilidad ---------------------------------------------------------

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: '${baseName}-logs'
  location: location
  tags: tags
  properties: {
    sku: { name: 'PerGB2018' }
    // 30 días es suficiente para depurar y mantiene el coste bajo.
    retentionInDays: 30
  }
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: '${baseName}-insights'
  location: location
  tags: tags
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalytics.id
  }
}

// --- Registro de contenedores ----------------------------------------------

resource containerRegistry 'Microsoft.ContainerRegistry/registries@2023-11-01-preview' = {
  name: '${namePrefix}acr${suffix}'
  location: location
  tags: tags
  sku: { name: environment == 'prod' ? 'Standard' : 'Basic' }
  properties: {
    adminUserEnabled: true
  }
}

// --- Base de datos ----------------------------------------------------------

resource postgres 'Microsoft.DBforPostgreSQL/flexibleServers@2023-12-01-preview' = {
  name: '${baseName}-pg'
  location: location
  tags: tags
  sku: {
    name: environment == 'prod' ? 'Standard_D2ds_v5' : 'Standard_B1ms'
    tier: environment == 'prod' ? 'GeneralPurpose' : 'Burstable'
  }
  properties: {
    version: '16'
    administratorLogin: postgresAdminUser
    administratorLoginPassword: postgresAdminPassword
    storage: { storageSizeGB: environment == 'prod' ? 128 : 32 }
    backup: {
      backupRetentionDays: environment == 'prod' ? 14 : 7
      geoRedundantBackup: 'Disabled'
    }
    highAvailability: { mode: 'Disabled' }
    network: { publicNetworkAccess: 'Enabled' }
  }
}

// pgvector debe estar en la lista de extensiones permitidas del servidor.
resource pgvectorAllowlist 'Microsoft.DBforPostgreSQL/flexibleServers/configurations@2023-12-01-preview' = {
  parent: postgres
  name: 'azure.extensions'
  properties: {
    value: 'VECTOR'
    source: 'user-override'
  }
}

resource postgresDatabase 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2023-12-01-preview' = {
  parent: postgres
  name: 'creator_signal'
  properties: {
    charset: 'UTF8'
    collation: 'en_US.utf8'
  }
}

// Permite el acceso desde servicios de Azure (Container Apps).
resource allowAzureServices 'Microsoft.DBforPostgreSQL/flexibleServers/firewallRules@2023-12-01-preview' = {
  parent: postgres
  name: 'AllowAllAzureServices'
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '0.0.0.0'
  }
}

// --- Redis ------------------------------------------------------------------

resource redis 'Microsoft.Cache/redis@2024-03-01' = {
  name: '${baseName}-redis'
  location: location
  tags: tags
  properties: {
    sku: {
      name: environment == 'prod' ? 'Standard' : 'Basic'
      family: 'C'
      capacity: environment == 'prod' ? 1 : 0
    }
    enableNonSslPort: false
    minimumTlsVersion: '1.2'
    redisConfiguration: {
      // La cola de trabajos no debe perder mensajes por presión de memoria.
      'maxmemory-policy': 'noeviction'
    }
  }
}

// --- Key Vault --------------------------------------------------------------

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: '${namePrefix}kv${suffix}'
  location: location
  tags: tags
  properties: {
    sku: { family: 'A', name: 'standard' }
    tenantId: subscription().tenantId
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 7
    enablePurgeProtection: environment == 'prod' ? true : null
  }
}

resource youtubeSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = if (!empty(youtubeApiKey)) {
  parent: keyVault
  name: 'youtube-api-key'
  properties: { value: youtubeApiKey }
}

resource databaseUrlSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'database-url'
  properties: {
    value: 'postgresql+psycopg://${postgresAdminUser}:${postgresAdminPassword}@${postgres.properties.fullyQualifiedDomainName}:5432/creator_signal?sslmode=require'
  }
}

// Rol «Key Vault Secrets User» para el principal indicado.
var keyVaultSecretsUserRoleId = '4633458b-17de-408a-b874-0445c86b69e6'

resource keyVaultRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(keyVaultAdminObjectId)) {
  scope: keyVault
  name: guid(keyVault.id, keyVaultAdminObjectId, keyVaultSecretsUserRoleId)
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', keyVaultSecretsUserRoleId)
    principalId: keyVaultAdminObjectId
    principalType: 'ServicePrincipal'
  }
}

// --- Container Apps ---------------------------------------------------------

resource containerEnv 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: '${baseName}-env'
  location: location
  tags: tags
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
    }
  }
}

var databaseUrl = 'postgresql+psycopg://${postgresAdminUser}:${postgresAdminPassword}@${postgres.properties.fullyQualifiedDomainName}:5432/creator_signal?sslmode=require'
var redisUrl = 'rediss://:${redis.listKeys().primaryKey}@${redis.properties.hostName}:6380/0'

var commonSecrets = [
  { name: 'database-url', value: databaseUrl }
  { name: 'redis-url', value: redisUrl }
  { name: 'registry-password', value: containerRegistry.listCredentials().passwords[0].value }
  { name: 'youtube-api-key', value: youtubeApiKey }
]

var registryConfig = [
  {
    server: containerRegistry.properties.loginServer
    username: containerRegistry.listCredentials().username
    passwordSecretRef: 'registry-password'
  }
]

var commonEnvVars = [
  { name: 'APP_ENV', value: 'production' }
  { name: 'DATABASE_URL', secretRef: 'database-url' }
  { name: 'REDIS_URL', secretRef: 'redis-url' }
  { name: 'YOUTUBE_API_KEY', secretRef: 'youtube-api-key' }
  { name: 'LOG_JSON', value: 'true' }
  { name: 'LOG_LEVEL', value: 'INFO' }
  { name: 'PGVECTOR_MODE', value: 'auto' }
  { name: 'APPLICATIONINSIGHTS_CONNECTION_STRING', value: appInsights.properties.ConnectionString }
]

resource apiApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: '${baseName}-api'
  location: location
  tags: tags
  properties: {
    managedEnvironmentId: containerEnv.id
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        targetPort: 8000
        transport: 'auto'
        corsPolicy: {
          allowedOrigins: ['https://${baseName}-web.${containerEnv.properties.defaultDomain}']
          allowedMethods: ['GET', 'POST', 'DELETE', 'OPTIONS']
          allowedHeaders: ['Content-Type', 'X-Request-ID']
        }
      }
      secrets: commonSecrets
      registries: registryConfig
    }
    template: {
      containers: [
        {
          name: 'api'
          image: '${containerRegistry.properties.loginServer}/creator-signal-backend:${imageTag}'
          resources: { cpu: json('0.5'), memory: '1Gi' }
          env: concat(commonEnvVars, [
            { name: 'CORS_ORIGINS', value: 'https://${baseName}-web.${containerEnv.properties.defaultDomain}' }
          ])
          probes: [
            {
              type: 'Liveness'
              httpGet: { path: '/api/health', port: 8000 }
              initialDelaySeconds: 30
              periodSeconds: 30
            }
          ]
        }
      ]
      scale: {
        minReplicas: environment == 'prod' ? 1 : 0
        maxReplicas: 3
        rules: [
          {
            name: 'http-scaling'
            http: { metadata: { concurrentRequests: '50' } }
          }
        ]
      }
    }
  }
}

resource workerApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: '${baseName}-worker'
  location: location
  tags: tags
  properties: {
    managedEnvironmentId: containerEnv.id
    configuration: {
      activeRevisionsMode: 'Single'
      // El worker no expone ingress: sólo consume trabajos de la cola.
      secrets: commonSecrets
      registries: registryConfig
    }
    template: {
      containers: [
        {
          name: 'worker'
          image: '${containerRegistry.properties.loginServer}/creator-signal-backend:${imageTag}'
          command: ['python', '-m', 'app.workers.main']
          // El análisis carga modelos en memoria: conviene más RAM que la API.
          resources: { cpu: json('1.0'), memory: '2Gi' }
          env: commonEnvVars
        }
      ]
      scale: {
        // Al menos una réplica siempre viva: si baja a cero, los análisis
        // encolados no se procesan hasta la siguiente petición.
        minReplicas: 1
        maxReplicas: environment == 'prod' ? 5 : 2
      }
    }
  }
}

resource frontendApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: '${baseName}-web'
  location: location
  tags: tags
  properties: {
    managedEnvironmentId: containerEnv.id
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        targetPort: 3000
        transport: 'auto'
      }
      secrets: [
        { name: 'registry-password', value: containerRegistry.listCredentials().passwords[0].value }
      ]
      registries: registryConfig
    }
    template: {
      containers: [
        {
          name: 'web'
          image: '${containerRegistry.properties.loginServer}/creator-signal-frontend:${imageTag}'
          resources: { cpu: json('0.5'), memory: '1Gi' }
          env: [
            { name: 'NODE_ENV', value: 'production' }
            { name: 'NEXT_PUBLIC_API_URL', value: 'https://${apiApp.properties.configuration.ingress.fqdn}' }
          ]
        }
      ]
      scale: {
        minReplicas: environment == 'prod' ? 1 : 0
        maxReplicas: 3
      }
    }
  }
}

// --- Salidas ----------------------------------------------------------------

output apiUrl string = 'https://${apiApp.properties.configuration.ingress.fqdn}'
output frontendUrl string = 'https://${frontendApp.properties.configuration.ingress.fqdn}'
output containerRegistryLoginServer string = containerRegistry.properties.loginServer
output postgresFqdn string = postgres.properties.fullyQualifiedDomainName
output keyVaultName string = keyVault.name
output resourceGroupName string = resourceGroup().name

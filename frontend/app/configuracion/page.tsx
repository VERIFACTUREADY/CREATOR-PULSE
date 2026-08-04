'use client';

import { useQuery } from '@tanstack/react-query';

import { Badge, Callout, Card, ErrorState, LoadingState, SectionTitle } from '@/components/ui';
import { ApiError, getHealth, getPublicConfig } from '@/lib/api';
import { formatNumber } from '@/lib/format';

function StatusRow({ label, ok, detail }: { label: string; ok: boolean; detail?: string | null }) {
  return (
    <li className="flex items-center justify-between gap-3 border-b border-border py-2 last:border-0">
      <span className="text-sm">{label}</span>
      <span className="flex items-center gap-2">
        {detail ? <span className="text-xs text-muted-foreground">{detail}</span> : null}
        <Badge tone={ok ? 'positive' : 'negative'}>{ok ? 'Correcto' : 'No disponible'}</Badge>
      </span>
    </li>
  );
}

export default function SettingsPage() {
  const configQuery = useQuery({ queryKey: ['config'], queryFn: getPublicConfig });
  const healthQuery = useQuery({
    queryKey: ['health'],
    queryFn: getHealth,
    refetchInterval: 15_000,
    retry: false,
  });

  if (configQuery.isLoading) return <LoadingState label="Cargando la configuración" />;

  if (configQuery.error || !configQuery.data) {
    return (
      <ErrorState
        message={
          configQuery.error instanceof ApiError
            ? configQuery.error.message
            : 'No se ha podido cargar la configuración.'
        }
        onRetry={() => void configQuery.refetch()}
      />
    );
  }

  const config = configQuery.data;

  return (
    <div className="space-y-6">
      <SectionTitle
        title="Configuración"
        description="Estado de la instalación. Los valores se definen en el fichero .env del servidor; esta pantalla es de sólo lectura y nunca muestra credenciales."
      />

      <Card>
        <h3 className="mb-3 font-semibold">Estado del sistema</h3>
        {healthQuery.data ? (
          <ul>
            {healthQuery.data.components.map((component) => (
              <StatusRow
                key={component.name}
                label={component.name}
                ok={component.healthy}
                detail={component.detail}
              />
            ))}
          </ul>
        ) : (
          <p className="text-sm text-destructive">
            No se ha podido contactar con la API. Comprueba que el backend está en marcha.
          </p>
        )}
      </Card>

      <Card>
        <h3 className="mb-3 font-semibold">Funcionalidades</h3>
        <ul>
          <StatusRow label="Modo demostración" ok={config.demo_mode_enabled} />
          <StatusRow
            label="Clave de la API de YouTube configurada"
            ok={config.youtube_configured}
            detail={config.youtube_configured ? undefined : 'Sólo se pueden analizar canales de demostración'}
          />
          <StatusRow
            label="IA externa"
            ok={config.ai_enabled}
            detail={config.ai_enabled ? `Proveedor: ${config.ai_provider}` : 'Motor determinista'}
          />
          <StatusRow
            label="Análisis de toxicidad"
            ok={config.toxicity_analysis_enabled}
            detail="Señal de seguridad para el creador"
          />
          <StatusRow
            label="Anonimización de autores"
            ok={config.anonymize_comment_authors}
            detail="Los identificadores se almacenan con hash"
          />
          <StatusRow
            label="Modo propietario (OAuth)"
            ok={config.owner_mode_enabled}
            detail={
              config.owner_mode_enabled
                ? 'Conecta tu canal desde «Modo propietario»'
                : 'Desactivado (ENABLE_OWNER_MODE=false)'
            }
          />
        </ul>
      </Card>

      <Card>
        <h3 className="mb-3 font-semibold">Límites de análisis</h3>
        <dl className="grid gap-3 text-sm sm:grid-cols-2">
          <div>
            <dt className="text-xs text-muted-foreground">Vídeos por análisis (por defecto)</dt>
            <dd className="font-medium">
              {config.limits.default_max_videos} (máximo {config.limits.hard_max_videos})
            </dd>
          </div>
          <div>
            <dt className="text-xs text-muted-foreground">Comentarios por vídeo (por defecto)</dt>
            <dd className="font-medium">
              {config.limits.default_max_comments_per_video} (máximo{' '}
              {config.limits.hard_max_comments_per_video})
            </dd>
          </div>
          <div>
            <dt className="text-xs text-muted-foreground">Comentarios por canal (por defecto)</dt>
            <dd className="font-medium">
              {formatNumber(config.limits.default_max_comments_per_channel)} (máximo{' '}
              {formatNumber(config.limits.hard_max_comments_per_channel)})
            </dd>
          </div>
          <div>
            <dt className="text-xs text-muted-foreground">Retención de datos</dt>
            <dd className="font-medium">{config.data_retention_days} días</dd>
          </div>
        </dl>
      </Card>

      <Card>
        <h3 className="mb-3 font-semibold">Modelos y versión del algoritmo</h3>
        <dl className="grid gap-3 text-sm sm:grid-cols-2">
          <div>
            <dt className="text-xs text-muted-foreground">Versión del algoritmo</dt>
            <dd className="font-mono">{config.algorithm_version}</dd>
          </div>
          <div>
            <dt className="text-xs text-muted-foreground">Backend de embeddings</dt>
            <dd className="font-mono">{config.embedding_backend}</dd>
          </div>
          <div>
            <dt className="text-xs text-muted-foreground">Backend de sentimiento</dt>
            <dd className="font-mono">{config.sentiment_backend}</dd>
          </div>
          <div>
            <dt className="text-xs text-muted-foreground">Entorno</dt>
            <dd className="font-mono">{config.app_env}</dd>
          </div>
        </dl>
      </Card>

      <Card>
        <h3 className="mb-3 font-semibold">Privacidad</h3>
        <ul className="space-y-2 text-sm text-muted-foreground">
          <li>• Sólo se analizan datos públicos obtenidos de la API oficial de YouTube.</li>
          <li>
            • De los autores de comentarios sólo se guarda un identificador con hash, necesario para
            deduplicar. No se almacenan sus nombres públicos ni sus fotos de perfil.
          </li>
          <li>• Los comentarios públicos no se usan para entrenar ningún modelo.</li>
          <li>
            • Puedes eliminar un canal y todos sus análisis desde la pantalla «Canales». Los datos
            se purgan automáticamente pasados {config.data_retention_days} días.
          </li>
          <li>
            • Si activas un proveedor de IA externo, se le envían resúmenes y ejemplos de
            comentarios ya anonimizados, nunca la base de datos completa.
          </li>
        </ul>
      </Card>

      <Callout tone="warning" title="Sobre las clasificaciones automáticas">
        {config.disclaimer_es}
      </Callout>
    </div>
  );
}

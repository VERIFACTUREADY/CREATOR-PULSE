'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useSearchParams } from 'next/navigation';
import { useState } from 'react';

import {
  Badge,
  Button,
  Callout,
  Card,
  EmptyState,
  ErrorState,
  LoadingState,
  Metric,
  SectionTitle,
} from '@/components/ui';
import {
  ApiError,
  disconnectOwnerChannel,
  getOwnerAnalytics,
  getOwnerStatus,
  listChannels,
  startOwnerAuthorization,
} from '@/lib/api';
import { formatCompact, formatDate, formatDecimal, formatNumber } from '@/lib/format';

/** Mensajes con los que vuelve el navegador tras pasar por Google. */
const CALLBACK_MESSAGES: Record<string, { tone: 'info' | 'warning' | 'danger'; text: string }> = {
  conectado: { tone: 'info', text: 'Canal conectado. Ya puedes ver sus métricas privadas.' },
  denegado: {
    tone: 'warning',
    text: 'Has cancelado la autorización. No se ha guardado ningún dato.',
  },
  caducado: {
    tone: 'warning',
    text: 'La solicitud de conexión caducó. Vuelve a intentarlo.',
  },
  canal_no_encontrado: {
    tone: 'danger',
    text: 'El canal que intentabas conectar ya no existe.',
  },
};

/** Formatea segundos como «2 min 15 s». */
function formatDuration(seconds: number | null): string {
  if (seconds === null) return 'No disponible';
  const minutes = Math.floor(seconds / 60);
  const rest = Math.round(seconds % 60);
  return minutes > 0 ? `${minutes} min ${rest} s` : `${rest} s`;
}

function OwnerMetrics({ channelId }: { channelId: string }) {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['owner-analytics', channelId],
    queryFn: () => getOwnerAnalytics(channelId),
  });

  if (isLoading) return <LoadingState label="Cargando métricas privadas" />;

  if (error || !data) {
    return (
      <ErrorState
        title="No se han podido cargar las métricas privadas"
        message={
          error instanceof ApiError ? error.message : 'YouTube Analytics no ha respondido.'
        }
        code={error instanceof ApiError ? error.code : undefined}
        onRetry={() => void refetch()}
      />
    );
  }

  return (
    <div className="space-y-6">
      <p className="text-sm text-muted-foreground">
        Periodo: {formatDate(data.start_date)} → {formatDate(data.end_date)}
      </p>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Metric label="Visualizaciones" value={formatCompact(data.views)} />
        <Metric
          label="Tiempo de visualización"
          value={
            data.estimated_minutes_watched === null
              ? '—'
              : `${formatCompact(Math.round(data.estimated_minutes_watched / 60))} h`
          }
          hint="Estimado por YouTube"
        />
        <Metric
          label="Duración media vista"
          value={formatDuration(data.average_view_duration_seconds)}
          hint={
            data.average_view_percentage === null
              ? undefined
              : `${formatDecimal(data.average_view_percentage)} % del vídeo`
          }
        />
        <Metric
          label="Suscriptores netos"
          value={data.net_subscribers === null ? '—' : formatNumber(data.net_subscribers)}
          hint={
            data.subscribers_gained === null
              ? undefined
              : `+${formatNumber(data.subscribers_gained)} / −${formatNumber(data.subscribers_lost)}`
          }
          tone={
            data.net_subscribers === null
              ? 'neutral'
              : data.net_subscribers >= 0
                ? 'positive'
                : 'negative'
          }
        />
        <Metric label="Impresiones" value={formatCompact(data.impressions)} />
        <Metric
          label="Porcentaje de clics"
          value={data.impressions_ctr === null ? '—' : `${formatDecimal(data.impressions_ctr)} %`}
          hint="Impresiones que acaban en visita"
        />
        <Metric label="Me gusta" value={formatCompact(data.likes)} />
        <Metric label="Veces compartido" value={formatCompact(data.shares)} />
      </div>

      {data.traffic_sources.length > 0 ? (
        <Card>
          <h3 className="mb-3 font-semibold">Fuentes de tráfico</h3>
          <ul className="space-y-2">
            {data.traffic_sources.slice(0, 8).map((row, index) => (
              <li key={index} className="flex items-center justify-between gap-3 text-sm">
                <span>{String(row.label_es ?? row.insightTrafficSourceType ?? '—')}</span>
                <span className="tabular-nums text-muted-foreground">
                  {formatCompact(Number(row.views ?? 0))} visualizaciones
                </span>
              </li>
            ))}
          </ul>
        </Card>
      ) : null}

      {data.geography.length > 0 ? (
        <Card>
          <h3 className="mb-3 font-semibold">Países con más audiencia</h3>
          <ul className="space-y-2">
            {data.geography.slice(0, 8).map((row, index) => (
              <li key={index} className="flex items-center justify-between gap-3 text-sm">
                <span>{String(row.country ?? '—')}</span>
                <span className="tabular-nums text-muted-foreground">
                  {formatCompact(Number(row.views ?? 0))} visualizaciones
                </span>
              </li>
            ))}
          </ul>
        </Card>
      ) : null}

      {data.unavailable_es.length > 0 ? (
        <Callout tone="warning" title="Métricas no disponibles">
          <ul className="space-y-1">
            {data.unavailable_es.map((message, index) => (
              <li key={index}>• {message}</li>
            ))}
          </ul>
          <p className="mt-2">
            Cuando un dato no está disponible se muestra un guion. Nunca se sustituye por cero ni
            se estima.
          </p>
        </Callout>
      ) : null}

      <p className="text-xs text-muted-foreground">{data.note_es}</p>
    </div>
  );
}

export function OwnerMode() {
  const params = useSearchParams();
  const queryClient = useQueryClient();
  const [expanded, setExpanded] = useState<string | null>(null);

  const status = useQuery({ queryKey: ['owner-status'], queryFn: getOwnerStatus });
  const channels = useQuery({
    queryKey: ['channels'],
    queryFn: listChannels,
    enabled: status.data?.ready ?? false,
  });

  const connect = useMutation({
    mutationFn: (channelId: string) => startOwnerAuthorization(channelId),
    onSuccess: (data) => {
      // Se sale de la aplicación hacia la pantalla de consentimiento de Google.
      window.location.href = data.authorization_url;
    },
  });

  const disconnect = useMutation({
    mutationFn: (channelId: string) => disconnectOwnerChannel(channelId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['owner-status'] });
      setExpanded(null);
    },
  });

  if (status.isLoading) return <LoadingState label="Comprobando el modo propietario" />;

  if (status.error || !status.data) {
    return (
      <ErrorState
        message={
          status.error instanceof ApiError
            ? status.error.message
            : 'No se ha podido consultar el estado del modo propietario.'
        }
        onRetry={() => void status.refetch()}
      />
    );
  }

  const info = status.data;
  const callback = params.get('oauth');
  const callbackMessage = callback ? CALLBACK_MESSAGES[callback] : undefined;
  const connectedIds = new Set(info.connections.map((c) => c.channel_id));

  return (
    <div className="space-y-6">
      <SectionTitle
        title="Modo propietario"
        description="Conecta tu propio canal para ver métricas privadas de YouTube Analytics que no existen en el modo público."
      />

      {callbackMessage ? (
        <Callout tone={callbackMessage.tone}>{callbackMessage.text}</Callout>
      ) : null}

      <Callout tone="info" title="Qué autorizas exactamente">
        {info.message_es}
        <ul className="mt-2 space-y-1">
          {info.scopes.map((scope) => (
            <li key={scope} className="font-mono text-xs">
              • {scope}
            </li>
          ))}
        </ul>
        <p className="mt-2">
          Ambos permisos son de <strong>sólo lectura</strong>. Puedes revocarlos desde aquí o desde{' '}
          <a
            href="https://myaccount.google.com/permissions"
            target="_blank"
            rel="noopener noreferrer"
            className="underline"
          >
            la configuración de tu cuenta de Google
          </a>
          .
        </p>
      </Callout>

      {!info.ready ? (
        <Card>
          <h3 className="mb-2 font-semibold">Falta configuración</h3>
          <p className="mb-3 text-sm text-muted-foreground">
            Para poder conectar un canal, el servidor necesita:
          </p>
          <ul className="space-y-2 text-sm">
            {info.missing_config.map((item) => (
              <li key={item} className="flex items-center gap-2">
                <Badge tone="warning">Pendiente</Badge>
                <code className="text-xs">{item}</code>
              </li>
            ))}
          </ul>
          <p className="mt-4 text-sm text-muted-foreground">
            La clave de cifrado se genera con{' '}
            <code className="text-xs">python -m app.cli generar-clave</code>. Consulta la sección
            «Modo propietario» del README para dar de alta las credenciales de Google.
          </p>
        </Card>
      ) : null}

      {info.connections.length > 0 ? (
        <section aria-labelledby="conectados">
          <h3 id="conectados" className="mb-3 font-semibold">
            Canales conectados
          </h3>
          <ul className="space-y-4">
            {info.connections.map((connection) => (
              <Card as="li" key={connection.channel_id ?? connection.external_account_id}>
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="font-medium">{connection.channel_title ?? 'Canal conectado'}</p>
                    <p className="text-xs text-muted-foreground">
                      Conectado el {formatDate(connection.connected_at)} ·{' '}
                      {connection.has_refresh_token
                        ? 'la conexión se renueva sola'
                        : 'sin renovación automática'}
                    </p>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      variant="secondary"
                      onClick={() =>
                        setExpanded(expanded === connection.channel_id ? null : connection.channel_id)
                      }
                    >
                      {expanded === connection.channel_id ? 'Ocultar métricas' : 'Ver métricas'}
                    </Button>
                    <Button
                      variant="danger"
                      disabled={disconnect.isPending}
                      onClick={() =>
                        connection.channel_id && disconnect.mutate(connection.channel_id)
                      }
                    >
                      Desconectar
                    </Button>
                  </div>
                </div>

                {expanded === connection.channel_id && connection.channel_id ? (
                  <div className="mt-5 border-t border-border pt-5">
                    <OwnerMetrics channelId={connection.channel_id} />
                  </div>
                ) : null}
              </Card>
            ))}
          </ul>
        </section>
      ) : null}

      {info.ready ? (
        <section aria-labelledby="conectar">
          <h3 id="conectar" className="mb-3 font-semibold">
            Conectar un canal
          </h3>
          {channels.data && channels.data.length > 0 ? (
            <ul className="space-y-2">
              {channels.data
                .filter((item) => !connectedIds.has(item.channel.id))
                .map((item) => (
                  <Card as="li" key={item.channel.id} className="flex items-center justify-between gap-3">
                    <div>
                      <p className="font-medium">{item.channel.title}</p>
                      {item.channel.source === 'demo' ? (
                        <p className="text-xs text-muted-foreground">
                          Es un canal de demostración: no se puede conectar de verdad.
                        </p>
                      ) : null}
                    </div>
                    <Button
                      disabled={connect.isPending || item.channel.source === 'demo'}
                      onClick={() => connect.mutate(item.channel.id)}
                    >
                      Conectar con Google
                    </Button>
                  </Card>
                ))}
            </ul>
          ) : (
            <EmptyState
              title="No hay canales guardados"
              description="Analiza primero un canal real para poder conectarlo."
            />
          )}
        </section>
      ) : null}

      {connect.error instanceof ApiError ? (
        <ErrorState message={connect.error.message} code={connect.error.code} />
      ) : null}
      {disconnect.error instanceof ApiError ? (
        <ErrorState message={disconnect.error.message} code={disconnect.error.code} />
      ) : null}

      <Card>
        <h3 className="mb-2 font-semibold">Métricas que aporta el modo propietario</h3>
        <p className="mb-3 text-sm text-muted-foreground">
          Ninguna de estas existe en el modo público. Mientras no conectes el canal, la aplicación
          no las muestra ni las estima.
        </p>
        <ul className="grid gap-1 text-sm text-muted-foreground sm:grid-cols-2">
          {info.owner_only_metrics.map((metric) => (
            <li key={metric} className="font-mono text-xs">
              • {metric}
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
}

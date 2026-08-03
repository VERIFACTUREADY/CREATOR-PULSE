'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useState } from 'react';

import {
  Badge,
  Button,
  Card,
  DemoBadge,
  EmptyState,
  ErrorState,
  LoadingState,
  SectionTitle,
} from '@/components/ui';
import { ApiError, deleteChannel, listChannels, refreshChannel } from '@/lib/api';
import { formatCompact, formatNumber, formatRelative, formatSubscribers } from '@/lib/format';
import type { AnalysisRunBrief, ChannelListItem } from '@/lib/types';

function StatusBadge({ run }: { run: AnalysisRunBrief | null }) {
  if (!run) return <Badge tone="neutral">Sin analizar</Badge>;
  if (run.status === 'completed') return <Badge tone="positive">Completado</Badge>;
  if (run.status === 'failed') return <Badge tone="negative">Fallido</Badge>;
  return <Badge tone="warning">{run.status_label_es} · {run.progress} %</Badge>;
}

function ChannelRow({ item }: { item: ChannelListItem }) {
  const { channel, latest_run: latest, latest_completed_run: completed } = item;
  const queryClient = useQueryClient();
  const router = useRouter();
  const [confirming, setConfirming] = useState(false);

  const refresh = useMutation({
    mutationFn: () => refreshChannel(channel.id),
    onSuccess: (data) => router.push(`/analisis/${data.run_id}`),
  });

  const remove = useMutation({
    mutationFn: () => deleteChannel(channel.id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['channels'] });
      setConfirming(false);
    },
  });

  const isDemo = channel.source === 'demo';
  const busy = latest !== null && !['completed', 'failed'].includes(latest.status);

  return (
    <Card as="li" className="flex flex-col gap-4">
      <div className="flex flex-wrap items-start gap-4">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={channel.thumbnail_url ?? '/canal-sin-imagen.svg'}
          alt=""
          width={56}
          height={56}
          className="h-14 w-14 shrink-0 rounded-full bg-muted object-cover"
        />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="truncate font-semibold">{channel.title}</h3>
            {isDemo ? <DemoBadge /> : null}
            <StatusBadge run={latest} />
          </div>
          <p className="mt-0.5 text-sm text-muted-foreground">
            {channel.handle ? `@${channel.handle}` : channel.youtube_channel_id}
            {' · '}
            {formatSubscribers(channel.subscriber_count, channel.subscriber_count_hidden)}{' '}
            suscriptores
          </p>
          {item.top_opportunity_es ? (
            <p className="mt-2 text-sm">
              <span className="font-medium">Oportunidad principal: </span>
              <span className="text-muted-foreground">{item.top_opportunity_es}</span>
            </p>
          ) : null}
        </div>
      </div>

      <dl className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
        <div>
          <dt className="text-xs text-muted-foreground">Vídeos analizados</dt>
          <dd className="font-medium tabular-nums">{formatNumber(completed?.videos_fetched ?? 0)}</dd>
        </div>
        <div>
          <dt className="text-xs text-muted-foreground">Comentarios analizados</dt>
          <dd className="font-medium tabular-nums">
            {formatCompact(completed?.comments_analysed ?? 0)}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-muted-foreground">Último análisis</dt>
          <dd className="font-medium">{formatRelative(completed?.completed_at ?? null)}</dd>
        </div>
        <div>
          <dt className="text-xs text-muted-foreground">Vídeos del canal</dt>
          <dd className="font-medium tabular-nums">{formatCompact(channel.video_count)}</dd>
        </div>
      </dl>

      {latest?.status === 'failed' && latest.error_message_es ? (
        <p className="rounded-md border border-destructive/40 bg-destructive/5 p-3 text-sm text-destructive">
          {latest.error_message_es}
        </p>
      ) : null}

      <div className="flex flex-wrap gap-2">
        {completed ? (
          <Link
            href={`/analisis/${completed.id}`}
            className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90"
          >
            Ver análisis
          </Link>
        ) : latest && busy ? (
          <Link
            href={`/analisis/${latest.id}`}
            className="rounded-md border border-border px-4 py-2 text-sm font-medium transition-colors hover:bg-muted"
          >
            Ver progreso
          </Link>
        ) : null}

        <Button variant="secondary" onClick={() => refresh.mutate()} disabled={refresh.isPending || busy}>
          {refresh.isPending ? 'Actualizando…' : 'Actualizar'}
        </Button>

        {confirming ? (
          <>
            <Button variant="danger" onClick={() => remove.mutate()} disabled={remove.isPending}>
              {remove.isPending ? 'Eliminando…' : 'Confirmar eliminación'}
            </Button>
            <Button variant="ghost" onClick={() => setConfirming(false)}>
              Cancelar
            </Button>
          </>
        ) : (
          <Button variant="danger" onClick={() => setConfirming(true)}>
            Eliminar
          </Button>
        )}
      </div>

      {refresh.error instanceof ApiError ? (
        <p className="text-sm text-destructive" role="alert">
          {refresh.error.message}
        </p>
      ) : null}
    </Card>
  );
}

export default function ChannelsPage() {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['channels'],
    queryFn: listChannels,
    refetchInterval: 5000,
  });

  return (
    <div>
      <SectionTitle
        title="Canales"
        description="Cada canal se analiza de forma independiente. Puedes guardar y comparar varios canales públicos."
        action={
          <Link
            href="/nuevo-analisis"
            className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90"
          >
            Nuevo análisis
          </Link>
        }
      />

      {isLoading ? <LoadingState label="Cargando canales" /> : null}

      {error ? (
        <ErrorState
          message={error instanceof ApiError ? error.message : 'No se han podido cargar los canales.'}
          code={error instanceof ApiError ? error.code : undefined}
          onRetry={() => void refetch()}
        />
      ) : null}

      {data && data.length === 0 ? (
        <EmptyState
          title="Todavía no has analizado ningún canal"
          description="Analiza un canal público de YouTube o prueba primero con uno de los canales de demostración."
          action={
            <div className="flex gap-2">
              <Link
                href="/nuevo-analisis"
                className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground"
              >
                Analizar un canal
              </Link>
              <Link
                href="/demostracion"
                className="rounded-md border border-border px-4 py-2 text-sm font-medium"
              >
                Modo demostración
              </Link>
            </div>
          }
        />
      ) : null}

      {data && data.length > 0 ? (
        <ul className="space-y-4">
          {data.map((item) => (
            <ChannelRow key={item.channel.id} item={item} />
          ))}
        </ul>
      ) : null}
    </div>
  );
}

'use client';

import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';

import { Badge, Callout, Card, DemoBadge, ErrorState, LoadingState } from '@/components/ui';
import { ApiError, exportUrl, getDashboard } from '@/lib/api';
import { formatCompact, formatDateTime, formatSubscribers } from '@/lib/format';

import { CriticismTab, RequestsTab, StrengthsTab } from './feedback';
import { IdeasTab } from './ideas';
import { OverviewTab } from './overview';
import { QualityTab } from './quality';
import { TabBar, TabPanel, useTabs } from './tabs';
import { TopicsTab } from './topics';
import { VideosTab } from './videos';

export function Dashboard({ runId }: { runId: string }) {
  const [tab, setTab] = useTabs();

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['dashboard', runId],
    queryFn: () => getDashboard(runId),
  });

  if (isLoading) return <LoadingState label="Cargando el análisis" />;

  if (error || !data) {
    return (
      <ErrorState
        title="No se ha podido cargar el análisis"
        message={
          error instanceof ApiError ? error.message : 'El análisis solicitado no está disponible.'
        }
        code={error instanceof ApiError ? error.code : undefined}
        onRetry={() => void refetch()}
      />
    );
  }

  const { channel, run, summary } = data;

  return (
    <div className="space-y-6">
      <Card className="space-y-4">
        <div className="flex flex-wrap items-start gap-4">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={channel.thumbnail_url ?? '/canal-sin-imagen.svg'}
            alt=""
            width={64}
            height={64}
            className="h-16 w-16 shrink-0 rounded-full bg-muted object-cover"
          />
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="truncate text-2xl font-bold">{channel.title}</h1>
              {run.is_demo ? <DemoBadge /> : null}
            </div>
            <p className="mt-1 text-sm text-muted-foreground">
              {channel.handle ? `@${channel.handle}` : channel.youtube_channel_id} ·{' '}
              {formatSubscribers(channel.subscriber_count, channel.subscriber_count_hidden)}{' '}
              suscriptores · {formatCompact(summary.comments_analysed)} comentarios analizados en{' '}
              {summary.videos_analysed} vídeos
            </p>
            <p className="mt-1 text-xs text-muted-foreground">
              Última actualización: {formatDateTime(run.completed_at)}
            </p>
          </div>

          <div className="flex flex-wrap gap-2">
            <a
              href={exportUrl(runId, 'json')}
              className="rounded-md border border-border px-3 py-2 text-sm transition-colors hover:bg-muted"
            >
              Exportar JSON
            </a>
            <a
              href={exportUrl(runId, 'csv')}
              className="rounded-md border border-border px-3 py-2 text-sm transition-colors hover:bg-muted"
            >
              Exportar CSV
            </a>
            <Link
              href="/canales"
              className="rounded-md border border-border px-3 py-2 text-sm transition-colors hover:bg-muted"
            >
              Volver a canales
            </Link>
          </div>
        </div>

        <div className="flex flex-wrap gap-2">
          <Badge tone={data.data_quality.level === 'alta' ? 'positive' : 'warning'}>
            Calidad de los datos: {data.data_quality.level}
          </Badge>
          {data.data_quality.ai_used ? (
            <Badge tone="neutral">Textos reescritos con IA ({data.data_quality.ai_provider})</Badge>
          ) : (
            <Badge tone="neutral">Sin IA externa</Badge>
          )}
        </div>
      </Card>

      <Callout tone="info">{data.disclaimer_es}</Callout>

      <div>
        <TabBar active={tab} onChange={setTab} />

        <TabPanel id="resumen" active={tab}>
          <OverviewTab summary={summary} />
        </TabPanel>
        <TabPanel id="temas" active={tab}>
          <TopicsTab topics={data.topics} />
        </TabPanel>
        <TabPanel id="peticiones" active={tab}>
          <RequestsTab requests={data.requests} />
        </TabPanel>
        <TabPanel id="fortalezas" active={tab}>
          <StrengthsTab strengths={data.strengths} />
        </TabPanel>
        <TabPanel id="criticas" active={tab}>
          <CriticismTab criticism={data.criticism} />
        </TabPanel>
        <TabPanel id="ideas" active={tab}>
          <IdeasTab recommendations={data.recommendations} ideas={data.content_ideas} />
        </TabPanel>
        <TabPanel id="videos" active={tab}>
          <VideosTab videos={data.videos} />
        </TabPanel>
        <TabPanel id="calidad" active={tab}>
          <QualityTab quality={data.data_quality} />
        </TabPanel>
      </div>
    </div>
  );
}

'use client';

import { useMemo, useState } from 'react';

import { Badge, Card, EmptyState, SectionTitle } from '@/components/ui';
import {
  cn,
  formatCompact,
  formatDate,
  formatDecimal,
  formatDuration,
  formatNumber,
  performanceLabel,
} from '@/lib/format';
import type { VideoRow } from '@/lib/types';

type SortKey =
  | 'published_at'
  | 'view_count'
  | 'like_count'
  | 'comment_count'
  | 'likes_per_1000_views'
  | 'comments_per_1000_views'
  | 'views_relative_to_median';

const COLUMNS: { key: SortKey; label: string; help?: string }[] = [
  { key: 'published_at', label: 'Fecha' },
  { key: 'view_count', label: 'Visualizaciones' },
  { key: 'like_count', label: 'Me gusta' },
  { key: 'comment_count', label: 'Comentarios' },
  { key: 'likes_per_1000_views', label: 'Me gusta / 1.000', help: 'Me gusta por cada 1.000 visualizaciones' },
  {
    key: 'comments_per_1000_views',
    label: 'Coment. / 1.000',
    help: 'Comentarios por cada 1.000 visualizaciones',
  },
  {
    key: 'views_relative_to_median',
    label: 'Rendimiento',
    help: 'Visualizaciones respecto a la mediana del canal',
  },
];

function value(video: VideoRow, key: SortKey): number {
  if (key === 'published_at') {
    return video.published_at ? new Date(video.published_at).getTime() : 0;
  }
  return video[key] ?? -1;
}

const BAND_TONES: Record<string, 'positive' | 'negative' | 'neutral' | 'warning'> = {
  por_encima: 'positive',
  por_debajo: 'negative',
  reciente: 'warning',
  normal: 'neutral',
};

export function VideosTab({ videos }: { videos: VideoRow[] }) {
  const [sort, setSort] = useState<SortKey>('published_at');
  const [descending, setDescending] = useState(true);

  const sorted = useMemo(() => {
    return videos
      .slice()
      .sort((a, b) => (descending ? value(b, sort) - value(a, sort) : value(a, sort) - value(b, sort)));
  }, [videos, sort, descending]);

  if (videos.length === 0) {
    return (
      <EmptyState
        title="No hay vídeos analizados"
        description="No se ha podido importar ningún vídeo público de este canal."
      />
    );
  }

  const toggleSort = (key: SortKey) => {
    if (key === sort) {
      setDescending((value) => !value);
    } else {
      setSort(key);
      setDescending(true);
    }
  };

  return (
    <div className="space-y-6">
      <SectionTitle
        title="Vídeos analizados"
        description="Las métricas relativas comparan cada vídeo con la mediana del canal, no con la media, para que un vídeo viral no distorsione la referencia."
      />

      <Card className="overflow-x-auto p-0">
        <table className="w-full min-w-[900px] text-sm">
          <caption className="sr-only">
            Métricas de los vídeos analizados. Usa los botones de encabezado para ordenar.
          </caption>
          <thead>
            <tr className="border-b border-border text-left">
              <th scope="col" className="p-3 font-medium">
                Vídeo
              </th>
              {COLUMNS.map((column) => (
                <th
                  key={column.key}
                  scope="col"
                  className="p-3 font-medium"
                  aria-sort={
                    sort === column.key ? (descending ? 'descending' : 'ascending') : 'none'
                  }
                >
                  <button
                    type="button"
                    onClick={() => toggleSort(column.key)}
                    title={column.help}
                    className="inline-flex items-center gap-1 hover:text-primary"
                  >
                    {column.label}
                    {sort === column.key ? (
                      <span aria-hidden="true">{descending ? '▼' : '▲'}</span>
                    ) : null}
                  </button>
                </th>
              ))}
              <th scope="col" className="p-3 font-medium">
                Temas dominantes
              </th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((video) => (
              <tr key={video.youtube_video_id} className="border-b border-border last:border-0">
                <th scope="row" className="max-w-xs p-3 text-left font-normal">
                  <div className="flex gap-3">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={video.thumbnail_url ?? '/video-sin-imagen.svg'}
                      alt=""
                      width={80}
                      height={45}
                      className="h-[45px] w-20 shrink-0 rounded bg-muted object-cover"
                    />
                    <div className="min-w-0">
                      <a
                        href={video.youtube_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="line-clamp-2 font-medium hover:text-primary hover:underline"
                      >
                        {video.title}
                      </a>
                      <p className="mt-0.5 text-xs text-muted-foreground">
                        {formatDuration(video.duration_seconds)}
                        {video.comments_disabled ? ' · Comentarios desactivados' : ''}
                      </p>
                    </div>
                  </div>
                </th>
                <td className="whitespace-nowrap p-3 text-muted-foreground">
                  {formatDate(video.published_at)}
                </td>
                <td className="p-3 tabular-nums">{formatCompact(video.view_count)}</td>
                <td className="p-3 tabular-nums">{formatCompact(video.like_count)}</td>
                <td className="p-3 tabular-nums">{formatNumber(video.comment_count)}</td>
                <td className="p-3 tabular-nums">{formatDecimal(video.likes_per_1000_views)}</td>
                <td className="p-3 tabular-nums">{formatDecimal(video.comments_per_1000_views)}</td>
                <td className="p-3">
                  <div className="flex flex-col gap-1">
                    <span className={cn('tabular-nums')}>
                      {video.views_relative_to_median !== null
                        ? `${formatDecimal(video.views_relative_to_median, 2)}×`
                        : '—'}
                    </span>
                    <Badge tone={BAND_TONES[video.performance_band] ?? 'neutral'}>
                      {performanceLabel(video.performance_band)}
                    </Badge>
                  </div>
                </td>
                <td className="p-3">
                  {video.dominant_topics && video.dominant_topics.length > 0 ? (
                    <ul className="space-y-0.5 text-xs text-muted-foreground">
                      {video.dominant_topics.map((topic) => (
                        <li key={topic.cluster_key}>
                          {topic.label_es} ({topic.comment_count})
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <span className="text-xs text-muted-foreground">—</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>

      <p className="text-sm text-muted-foreground">
        Los vídeos publicados hace menos de una semana se marcan como «demasiado reciente para
        comparar»: todavía no han acumulado sus visualizaciones y compararlos con vídeos antiguos
        daría una lectura falsa.
      </p>
    </div>
  );
}

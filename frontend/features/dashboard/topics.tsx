'use client';

import { useMemo, useState } from 'react';

import {
  Badge,
  Card,
  CommentQuote,
  ConfidenceBadge,
  EmptyState,
  SectionTitle,
  SentimentBar,
  TrendBadge,
} from '@/components/ui';
import { formatNumber, formatPercent, sentimentLabel } from '@/lib/format';
import type { Topic } from '@/lib/types';

type SortKey = 'comment_count' | 'unique_video_count' | 'trend_score' | 'confidence_score';
type FilterKey = 'todos' | 'positivos' | 'criticos' | 'peticiones' | 'crecen';

const SORT_OPTIONS: { value: SortKey; label: string }[] = [
  { value: 'comment_count', label: 'Más menciones' },
  { value: 'unique_video_count', label: 'Más vídeos' },
  { value: 'trend_score', label: 'Mayor crecimiento' },
  { value: 'confidence_score', label: 'Mayor confianza' },
];

const FILTER_OPTIONS: { value: FilterKey; label: string }[] = [
  { value: 'todos', label: 'Todos' },
  { value: 'positivos', label: 'Positivos' },
  { value: 'criticos', label: 'Críticos' },
  { value: 'peticiones', label: 'Con peticiones' },
  { value: 'crecen', label: 'Al alza' },
];

function matchesFilter(topic: Topic, filter: FilterKey): boolean {
  const total = topic.positive_count + topic.neutral_count + topic.negative_count;
  switch (filter) {
    case 'positivos':
      return total > 0 && topic.positive_count / total >= 0.5;
    case 'criticos':
      return total > 0 && topic.negative_count / total >= 0.3;
    case 'peticiones':
      return topic.request_count > 0;
    case 'crecen':
      return topic.trend_direction === 'rising';
    default:
      return true;
  }
}

function TopicCard({ topic }: { topic: Topic }) {
  const [expanded, setExpanded] = useState(false);
  const examples = topic.representative_comments ?? [];

  return (
    <Card as="li" className="space-y-3">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="font-semibold">{topic.label_es}</h3>
          {topic.description_es ? (
            <p className="mt-1 text-sm text-muted-foreground">{topic.description_es}</p>
          ) : null}
        </div>
        <div className="flex flex-wrap gap-2">
          <TrendBadge direction={topic.trend_direction} label={topic.trend_label_es} />
          <ConfidenceBadge level={topic.confidence_level} />
          {topic.ai_generated_label ? (
            <Badge tone="neutral" title="La etiqueta la ha redactado el proveedor de IA configurado.">
              Etiqueta por IA
            </Badge>
          ) : null}
        </div>
      </div>

      <dl className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
        <div>
          <dt className="text-xs text-muted-foreground">Menciones</dt>
          <dd className="font-medium tabular-nums">{formatNumber(topic.comment_count)}</dd>
        </div>
        <div>
          <dt className="text-xs text-muted-foreground">Cuota de la muestra</dt>
          <dd className="font-medium tabular-nums">{formatPercent(topic.share_of_comments, 1)}</dd>
        </div>
        <div>
          <dt className="text-xs text-muted-foreground">Vídeos distintos</dt>
          <dd className="font-medium tabular-nums">
            {formatNumber(topic.unique_video_count)} ({formatPercent(topic.video_coverage)})
          </dd>
        </div>
        <div>
          <dt className="text-xs text-muted-foreground">Peticiones / preguntas</dt>
          <dd className="font-medium tabular-nums">
            {formatNumber(topic.request_count)} / {formatNumber(topic.question_count)}
          </dd>
        </div>
      </dl>

      <div className="space-y-1">
        <SentimentBar
          positive={topic.positive_count}
          neutral={topic.neutral_count}
          negative={topic.negative_count}
        />
        <p className="text-xs text-muted-foreground">
          {formatNumber(topic.positive_count)} positivos · {formatNumber(topic.neutral_count)}{' '}
          neutrales · {formatNumber(topic.negative_count)} negativos
        </p>
      </div>

      {topic.dominant_video_share >= 0.5 ? (
        <p className="rounded-md bg-warning/10 px-3 py-2 text-xs text-warning">
          El {formatPercent(topic.dominant_video_share)} de estas menciones vienen de un solo vídeo:
          puede reflejar la reacción a ese vídeo más que un patrón del canal.
        </p>
      ) : null}

      {examples.length > 0 ? (
        <div>
          <button
            type="button"
            onClick={() => setExpanded((value) => !value)}
            aria-expanded={expanded}
            className="text-sm font-medium text-primary hover:underline"
          >
            {expanded ? 'Ocultar comentarios de ejemplo' : `Ver ${examples.length} comentarios de ejemplo`}
          </button>
          {expanded ? (
            <div className="mt-3 space-y-2">
              {examples.map((example, index) => (
                <CommentQuote
                  key={index}
                  text={example.text}
                  meta={`${sentimentLabel(example.sentiment)}${
                    example.likes !== undefined ? ` · ${formatNumber(example.likes)} me gusta` : ''
                  }`}
                />
              ))}
              <p className="text-xs text-muted-foreground">
                Los ejemplos se muestran anonimizados: no se guardan los nombres ni las fotos de
                los autores.
              </p>
            </div>
          ) : null}
        </div>
      ) : null}
    </Card>
  );
}

export function TopicsTab({ topics }: { topics: Topic[] }) {
  const [sort, setSort] = useState<SortKey>('comment_count');
  const [filter, setFilter] = useState<FilterKey>('todos');

  const visible = useMemo(() => {
    return topics
      .filter((topic) => !topic.is_noise && matchesFilter(topic, filter))
      .slice()
      .sort((a, b) => b[sort] - a[sort]);
  }, [topics, sort, filter]);

  if (topics.length === 0) {
    return (
      <EmptyState
        title="No se han detectado temas"
        description="No hay comentarios suficientes para agrupar por significado. Amplía el número de vídeos o de comentarios y vuelve a lanzar el análisis."
      />
    );
  }

  return (
    <div className="space-y-6">
      <SectionTitle
        title="Temas detectados"
        description="Grupos de comentarios que hablan de lo mismo. Fíjate en cuántos vídeos distintos respaldan cada tema: un tema presente en un solo vídeo no es un patrón del canal."
      />

      <div className="flex flex-wrap items-end gap-4">
        <div>
          <label htmlFor="orden-temas" className="block text-sm font-medium">
            Ordenar por
          </label>
          <select
            id="orden-temas"
            value={sort}
            onChange={(event) => setSort(event.target.value as SortKey)}
            className="mt-1 rounded-md border border-input bg-background px-3 py-2 text-sm"
          >
            {SORT_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>

        <fieldset>
          <legend className="text-sm font-medium">Filtrar</legend>
          <div className="mt-1 flex flex-wrap gap-1">
            {FILTER_OPTIONS.map((option) => (
              <button
                key={option.value}
                type="button"
                aria-pressed={filter === option.value}
                onClick={() => setFilter(option.value)}
                className={
                  filter === option.value
                    ? 'rounded-full bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground'
                    : 'rounded-full border border-border px-3 py-1.5 text-xs hover:bg-muted'
                }
              >
                {option.label}
              </button>
            ))}
          </div>
        </fieldset>
      </div>

      {visible.length === 0 ? (
        <EmptyState
          title="Ningún tema cumple ese filtro"
          description="Prueba con otro filtro para ver los temas detectados."
        />
      ) : (
        <ul className="space-y-4">
          {visible.map((topic) => (
            <TopicCard key={topic.cluster_key} topic={topic} />
          ))}
        </ul>
      )}
    </div>
  );
}

'use client';

import {
  Badge,
  Callout,
  Card,
  ConfidenceBadge,
  EmptyState,
  Metric,
  SectionTitle,
  SentimentBar,
  TrendBadge,
} from '@/components/ui';
import { formatCompact, formatNumber, formatPercent, overallSentimentLabel } from '@/lib/format';
import type { DashboardSummary, TopicBrief } from '@/lib/types';

function HighlightCard({
  title,
  topic,
  emptyText,
  metric,
}: {
  title: string;
  topic: TopicBrief | null;
  emptyText: string;
  metric: (topic: TopicBrief) => string;
}) {
  return (
    <Card className="flex flex-col gap-2">
      <h3 className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{title}</h3>
      {topic ? (
        <>
          <p className="text-lg font-semibold leading-tight">{topic.label_es}</p>
          <p className="text-sm text-muted-foreground">{metric(topic)}</p>
          <div className="mt-1 flex flex-wrap gap-2">
            <ConfidenceBadge level={topic.confidence_level} />
            <Badge tone="neutral">
              {topic.unique_video_count} {topic.unique_video_count === 1 ? 'vídeo' : 'vídeos'}
            </Badge>
          </div>
        </>
      ) : (
        <p className="text-sm text-muted-foreground">{emptyText}</p>
      )}
    </Card>
  );
}

export function OverviewTab({ summary }: { summary: DashboardSummary }) {
  if (summary.comments_analysed === 0) {
    return (
      <EmptyState
        title="No hay comentarios que analizar"
        description="Este canal no tiene comentarios públicos suficientes en los vídeos analizados. Prueba a ampliar el número de vídeos o revisa si tienen los comentarios activados."
      />
    );
  }

  const { sentiment } = summary;

  return (
    <div className="space-y-8">
      <section aria-labelledby="metricas-clave">
        <h2 id="metricas-clave" className="sr-only">
          Métricas clave
        </h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Metric label="Vídeos analizados" value={formatNumber(summary.videos_analysed)} />
          <Metric
            label="Comentarios analizados"
            value={formatCompact(summary.comments_analysed)}
            hint="Excluye spam y duplicados"
          />
          <Metric
            label="Sentimiento general"
            value={overallSentimentLabel(sentiment.overall_es)}
            hint={`${formatPercent(sentiment.positive_share)} positivo · ${formatPercent(sentiment.negative_share)} negativo`}
            tone={sentiment.overall_es === 'positivo' ? 'positive' : 'neutral'}
          />
          <Metric
            label="Peticiones detectadas"
            value={formatNumber(summary.requests)}
            hint={`${formatNumber(summary.questions)} preguntas`}
          />
        </div>
      </section>

      <section aria-labelledby="distribucion">
        <SectionTitle
          title="Distribución del sentimiento"
          description="Los comentarios mixtos contienen a la vez elogio y crítica. Los inciertos son aquellos en los que el clasificador tiene poca confianza."
        />
        <Card className="space-y-4">
          <SentimentBar
            positive={sentiment.positive}
            neutral={sentiment.neutral}
            negative={sentiment.negative}
          />
          <dl className="grid grid-cols-2 gap-4 text-sm sm:grid-cols-5">
            <div>
              <dt className="text-xs text-muted-foreground">Positivos</dt>
              <dd className="font-medium tabular-nums text-success">
                {formatNumber(sentiment.positive)}
              </dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground">Neutrales</dt>
              <dd className="font-medium tabular-nums">{formatNumber(sentiment.neutral)}</dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground">Negativos</dt>
              <dd className="font-medium tabular-nums text-destructive">
                {formatNumber(sentiment.negative)}
              </dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground">Mixtos</dt>
              <dd className="font-medium tabular-nums">{formatNumber(sentiment.mixed)}</dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground">Inciertos</dt>
              <dd className="font-medium tabular-nums">{formatNumber(sentiment.uncertain)}</dd>
            </div>
          </dl>
        </Card>
      </section>

      <section aria-labelledby="senales">
        <SectionTitle title="Señales principales" />
        <div className="grid gap-4 sm:grid-cols-2">
          <HighlightCard
            title="Fortaleza principal"
            topic={summary.top_strength}
            emptyText="No hay todavía un patrón de elogios lo bastante repetido."
            metric={(topic) =>
              `${formatNumber(topic.positive_count)} comentarios positivos en ${topic.unique_video_count} vídeos`
            }
          />
          <HighlightCard
            title="Petición principal"
            topic={summary.top_request}
            emptyText="No se han detectado peticiones repetidas."
            metric={(topic) =>
              `${formatNumber(topic.request_count)} peticiones en ${topic.unique_video_count} vídeos`
            }
          />
          <HighlightCard
            title="Crítica más repetida"
            topic={summary.top_criticism}
            emptyText="No hay críticas repetidas de forma significativa."
            metric={(topic) =>
              `${formatNumber(topic.negative_count)} comentarios críticos en ${topic.unique_video_count} vídeos`
            }
          />
          <Card className="flex flex-col gap-2">
            <h3 className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Tema que más crece
            </h3>
            {summary.fastest_growing ? (
              <>
                <p className="text-lg font-semibold leading-tight">
                  {summary.fastest_growing.label_es}
                </p>
                <div className="flex flex-wrap gap-2">
                  <TrendBadge
                    direction={summary.fastest_growing.trend_direction}
                    label={
                      summary.fastest_growing.trend_change !== null
                        ? `${formatPercent(summary.fastest_growing.trend_change)} frente al periodo anterior`
                        : 'Tema nuevo'
                    }
                  />
                  <ConfidenceBadge level={summary.fastest_growing.confidence_level} />
                </div>
              </>
            ) : (
              <p className="text-sm text-muted-foreground">
                No hay histórico suficiente para detectar tendencias.
              </p>
            )}
          </Card>
        </div>
      </section>

      {summary.top_recommendation ? (
        <section aria-labelledby="recomendacion-principal">
          <SectionTitle title="Recomendación de mayor prioridad" />
          <Card className="border-primary/40 bg-primary/5">
            <div className="flex flex-wrap items-center gap-2">
              <Badge tone="demo">{summary.top_recommendation.category_label_es}</Badge>
              <ConfidenceBadge level={summary.top_recommendation.confidence_level} />
            </div>
            <p className="mt-3 text-base font-medium">{summary.top_recommendation.title_es}</p>
            <p className="mt-1 text-sm text-muted-foreground">
              Consulta la pestaña «Ideas de contenido» para ver la evidencia completa y el
              experimento propuesto.
            </p>
          </Card>
        </section>
      ) : null}

      {summary.primary_warning_es ? (
        <Callout tone="warning" title="Aviso sobre la calidad de los datos">
          {summary.primary_warning_es} Revisa la pestaña «Calidad de los datos» para ver todas las
          limitaciones de esta muestra.
        </Callout>
      ) : null}
    </div>
  );
}

'use client';

import { Badge, Callout, Card, Metric, SectionTitle } from '@/components/ui';
import { formatDate, formatNumber, formatPercent } from '@/lib/format';
import type { DataQuality } from '@/lib/types';

const STRATEGY_LABELS: Record<string, string> = {
  mixed: 'Mixta (recientes + relevantes)',
  recent: 'Comentarios recientes',
  relevant: 'Comentarios más votados',
};

const CLUSTERING_LABELS: Record<string, string> = {
  hdbscan: 'Agrupación por densidad (HDBSCAN)',
  agglomerative: 'Agrupación jerárquica (respaldo para muestras pequeñas)',
  keyword: 'Agregación por palabras clave y aspectos (muestra insuficiente para agrupar)',
  none: 'No se ha ejecutado ninguna agrupación',
};

export function QualityTab({ quality }: { quality: DataQuality }) {
  const coverage = quality.date_coverage as {
    first?: string | null;
    last?: string | null;
    span_days?: number;
    missing_dates?: number;
  };

  const languages = Object.entries(quality.language_distribution);
  const totalLanguages = languages.reduce((sum, [, count]) => sum + count, 0);

  return (
    <div className="space-y-8">
      <SectionTitle
        title="Calidad de los datos"
        description="Qué sabe y qué no sabe este análisis. Léelo antes de tomar decisiones a partir de las recomendaciones."
      />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Metric
          label="Puntuación de calidad"
          value={`${Math.round(quality.score * 100)} / 100`}
          hint={`Nivel ${quality.level}`}
          tone={quality.level === 'alta' ? 'positive' : quality.level === 'baja' ? 'negative' : 'neutral'}
        />
        <Metric label="Vídeos muestreados" value={formatNumber(quality.videos_sampled)} />
        <Metric
          label="Comentarios muestreados"
          value={formatNumber(quality.comments_sampled)}
          hint={`${formatNumber(quality.comments_analysed)} analizados`}
        />
        <Metric
          label="Temas detectados"
          value={formatNumber(quality.topics_found)}
          hint={`${formatPercent(quality.noise_share)} sin tema claro`}
        />
      </div>

      {quality.is_demo ? (
        <Callout tone="info" title="Datos de demostración">
          Este análisis se ha ejecutado sobre un canal ficticio generado para probar el producto.
          Los datos no corresponden a ningún canal ni persona real de YouTube, pero han pasado por
          exactamente el mismo pipeline de análisis que un canal real.
        </Callout>
      ) : null}

      {quality.warnings_es.length > 0 ? (
        <section aria-labelledby="avisos">
          <Card className="border-warning/40 bg-warning/5">
            <h3 id="avisos" className="mb-3 font-semibold">
              Avisos
            </h3>
            <ul className="space-y-2 text-sm">
              {quality.warnings_es.map((warning, index) => (
                <li key={index} className="flex gap-2">
                  <span aria-hidden="true">⚠</span>
                  <span>{warning}</span>
                </li>
              ))}
            </ul>
          </Card>
        </section>
      ) : null}

      {quality.biases_es.length > 0 ? (
        <section aria-labelledby="sesgos">
          <Card>
            <h3 id="sesgos" className="mb-3 font-semibold">
              Posibles sesgos de la muestra
            </h3>
            <ul className="space-y-2 text-sm text-muted-foreground">
              {quality.biases_es.map((bias, index) => (
                <li key={index} className="flex gap-2">
                  <span aria-hidden="true" className="text-primary">
                    •
                  </span>
                  <span>{bias}</span>
                </li>
              ))}
            </ul>
          </Card>
        </section>
      ) : null}

      <section aria-labelledby="muestreo">
        <Card>
          <h3 id="muestreo" className="mb-3 font-semibold">
            Cómo se ha construido la muestra
          </h3>
          <dl className="grid gap-4 sm:grid-cols-2">
            <div>
              <dt className="text-xs text-muted-foreground">Estrategia de muestreo</dt>
              <dd className="text-sm font-medium">
                {STRATEGY_LABELS[quality.sampling_strategy] ?? quality.sampling_strategy}
              </dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground">Algoritmo de agrupación</dt>
              <dd className="text-sm font-medium">
                {CLUSTERING_LABELS[quality.clustering_strategy] ?? quality.clustering_strategy}
              </dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground">Cobertura temporal</dt>
              <dd className="text-sm font-medium">
                {coverage.first && coverage.last
                  ? `${formatDate(coverage.first)} → ${formatDate(coverage.last)} (${formatNumber(
                      Math.round(coverage.span_days ?? 0),
                    )} días)`
                  : 'Sin fechas disponibles'}
              </dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground">
                Concentración en el vídeo dominante
              </dt>
              <dd className="text-sm font-medium">
                {formatPercent(quality.dominant_video_share)} de los comentarios
              </dd>
            </div>
          </dl>
        </Card>
      </section>

      <section aria-labelledby="descartes">
        <Card>
          <h3 id="descartes" className="mb-3 font-semibold">
            Datos descartados y ausentes
          </h3>
          <dl className="grid grid-cols-2 gap-4 text-sm sm:grid-cols-3">
            <div>
              <dt className="text-xs text-muted-foreground">Spam descartado</dt>
              <dd className="font-medium tabular-nums">
                {formatNumber(quality.comments_discarded_spam)}
              </dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground">Duplicados descartados</dt>
              <dd className="font-medium tabular-nums">
                {formatNumber(quality.comments_discarded_duplicate)}
              </dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground">Vacíos descartados</dt>
              <dd className="font-medium tabular-nums">
                {formatNumber(quality.comments_discarded_empty)}
              </dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground">Comentarios desactivados</dt>
              <dd className="font-medium tabular-nums">
                {formatNumber(quality.videos_with_comments_disabled)} vídeos
              </dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground">Vídeos sin comentarios</dt>
              <dd className="font-medium tabular-nums">
                {formatNumber(quality.videos_with_zero_comments)}
              </dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground">Vídeos sin visualizaciones públicas</dt>
              <dd className="font-medium tabular-nums">
                {formatNumber(quality.videos_missing_views)}
              </dd>
            </div>
          </dl>
        </Card>
      </section>

      {languages.length > 0 ? (
        <section aria-labelledby="idiomas">
          <Card>
            <h3 id="idiomas" className="mb-3 font-semibold">
              Distribución de idiomas
            </h3>
            <ul className="flex flex-wrap gap-2">
              {languages.map(([language, count]) => (
                <li key={language}>
                  <Badge tone="neutral">
                    {language === 'und' ? 'No detectado' : language.toUpperCase()}:{' '}
                    {formatNumber(count)} ({formatPercent(count / (totalLanguages || 1))})
                  </Badge>
                </li>
              ))}
            </ul>
            <p className="mt-3 text-sm text-muted-foreground">
              Los comentarios muy cortos suelen quedar como «no detectado». La clasificación de
              sentimiento es multilingüe, pero es menos precisa en idiomas poco representados.
            </p>
          </Card>
        </section>
      ) : null}

      <section aria-labelledby="version">
        <Card>
          <h3 id="version" className="mb-3 font-semibold">
            Configuración de este análisis
          </h3>
          <dl className="grid gap-3 text-sm sm:grid-cols-2">
            <div>
              <dt className="text-xs text-muted-foreground">Versión del algoritmo</dt>
              <dd className="font-mono">{quality.algorithm_version}</dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground">Modelo de embeddings</dt>
              <dd className="font-mono">{quality.embedding_backend}</dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground">Modelo de sentimiento</dt>
              <dd className="font-mono">{quality.sentiment_backend}</dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground">IA externa</dt>
              <dd>
                {quality.ai_used
                  ? `Sí, proveedor ${quality.ai_provider}. Sólo se han reescrito los textos: las cifras las calcula el motor determinista.`
                  : 'No. Todo el informe procede del motor determinista.'}
              </dd>
            </div>
          </dl>
        </Card>
      </section>
    </div>
  );
}

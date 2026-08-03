'use client';

import {
  Badge,
  Callout,
  Card,
  ConfidenceBadge,
  EmptyState,
  EvidenceList,
  SectionTitle,
} from '@/components/ui';
import { formatNumber, formatPercent } from '@/lib/format';
import type { ContentIdea, Recommendation } from '@/lib/types';

function RecommendationCard({ recommendation }: { recommendation: Recommendation }) {
  const evidence = recommendation.evidence;
  const bullets = [
    `${formatNumber(evidence.supporting_comments)} comentarios respaldan esta conclusión.`,
    `Aparece en ${formatNumber(evidence.supporting_videos)} de ${formatNumber(
      evidence.total_videos_analysed,
    )} vídeos analizados.`,
    evidence.share_of_comments > 0
      ? `Representa el ${formatPercent(evidence.share_of_comments, 1)} de la muestra.`
      : null,
    evidence.trend_change !== null
      ? `Variación frente al periodo anterior: ${formatPercent(evidence.trend_change)}.`
      : null,
  ].filter((item): item is string => item !== null);

  return (
    <Card as="article" className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="mb-2 flex flex-wrap gap-2">
            <Badge tone="demo">{recommendation.category_label_es}</Badge>
            <Badge tone="neutral">Prioridad {recommendation.priority}</Badge>
            {recommendation.ai_enriched ? <Badge tone="neutral">Texto reescrito por IA</Badge> : null}
          </div>
          <h3 className="text-base font-semibold">{recommendation.title_es}</h3>
        </div>
        <ConfidenceBadge level={recommendation.confidence_level} />
      </div>

      <p className="text-sm">{recommendation.explanation_es}</p>

      <div>
        <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Por qué se recomienda
        </h4>
        <p className="text-sm text-muted-foreground">{recommendation.reason_es}</p>
      </div>

      <div>
        <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Evidencia
        </h4>
        <EvidenceList items={bullets} />
      </div>

      <dl className="grid gap-3 sm:grid-cols-2">
        {recommendation.suggested_hook_es ? (
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Gancho sugerido
            </dt>
            <dd className="mt-1 text-sm italic">{recommendation.suggested_hook_es}</dd>
          </div>
        ) : null}
        {recommendation.suggested_format_label_es ? (
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Formato sugerido
            </dt>
            <dd className="mt-1 text-sm">{recommendation.suggested_format_label_es}</dd>
          </div>
        ) : null}
        {recommendation.suggested_experiment_es ? (
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Experimento
            </dt>
            <dd className="mt-1 text-sm">{recommendation.suggested_experiment_es}</dd>
          </div>
        ) : null}
        {recommendation.kpi_es ? (
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Métrica a vigilar
            </dt>
            <dd className="mt-1 text-sm">{recommendation.kpi_es}</dd>
          </div>
        ) : null}
      </dl>

      {recommendation.caveat_es ? (
        <Callout tone="warning" title="Advertencia">
          {recommendation.caveat_es}
        </Callout>
      ) : null}
    </Card>
  );
}

function IdeaCard({ idea }: { idea: ContentIdea }) {
  const bullets = Array.isArray(idea.evidence.bullets_es) ? idea.evidence.bullets_es : [];

  return (
    <Card as="article" className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="mb-2 flex flex-wrap gap-2">
            <Badge tone="neutral">{idea.suggested_format_label_es}</Badge>
          </div>
          <h3 className="text-base font-semibold">{idea.title_es}</h3>
        </div>
        <ConfidenceBadge level={idea.confidence_level} />
      </div>

      <div>
        <h4 className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Concepto
        </h4>
        <p className="text-sm">{idea.concept_es}</p>
      </div>

      <div>
        <h4 className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Por qué encaja con tu audiencia
        </h4>
        <p className="text-sm text-muted-foreground">{idea.why_es}</p>
      </div>

      {bullets.length > 0 ? (
        <div>
          <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Evidencia
          </h4>
          <EvidenceList items={bullets} />
        </div>
      ) : null}

      <dl className="grid gap-3 sm:grid-cols-2">
        <div>
          <dt className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Gancho
          </dt>
          <dd className="mt-1 text-sm italic">{idea.hook_es}</dd>
        </div>
        <div>
          <dt className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Llamada a la acción
          </dt>
          <dd className="mt-1 text-sm italic">{idea.call_to_action_es}</dd>
        </div>
        <div>
          <dt className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Experimento
          </dt>
          <dd className="mt-1 text-sm">{idea.experiment_es}</dd>
        </div>
        <div>
          <dt className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Métrica principal
          </dt>
          <dd className="mt-1 text-sm">{idea.kpi_es}</dd>
        </div>
      </dl>

      <Callout tone="warning" title="Riesgo de sobreinterpretar los datos">
        {idea.overinterpretation_risk_es}
      </Callout>
    </Card>
  );
}

export function IdeasTab({
  recommendations,
  ideas,
}: {
  recommendations: Recommendation[];
  ideas: ContentIdea[];
}) {
  if (recommendations.length === 0 && ideas.length === 0) {
    return (
      <EmptyState
        title="No hay suficientes datos para recomendar nada"
        description="El canal no tiene comentarios públicos suficientes para extraer conclusiones fiables. Amplía el número de vídeos o vuelve a intentarlo cuando tenga más comentarios."
      />
    );
  }

  return (
    <div className="space-y-10">
      {recommendations.length > 0 ? (
        <section aria-labelledby="recomendaciones">
          <SectionTitle
            title="Recomendaciones"
            description="Ordenadas por prioridad. Cada una incluye la evidencia numérica que la respalda y su nivel de confianza."
          />
          <div className="space-y-4">
            {recommendations.map((recommendation) => (
              <RecommendationCard key={recommendation.id} recommendation={recommendation} />
            ))}
          </div>
        </section>
      ) : null}

      {ideas.length > 0 ? (
        <section aria-labelledby="ideas">
          <SectionTitle
            title="Ideas de contenido"
            description="Ideas concretas derivadas de las oportunidades detectadas en tus comentarios."
          />
          <div className="space-y-4">
            {ideas.map((idea) => (
              <IdeaCard key={idea.id} idea={idea} />
            ))}
          </div>
        </section>
      ) : null}
    </div>
  );
}

'use client';

import {
  Badge,
  Callout,
  Card,
  CommentQuote,
  ConfidenceBadge,
  EmptyState,
  SectionTitle,
} from '@/components/ui';
import { formatNumber, formatPercent, sentimentLabel } from '@/lib/format';
import type { CriticismGroup, RepresentativeComment, RequestItem, StrengthItem } from '@/lib/types';

const CRITICISM_NOTICE =
  'Prioriza los patrones repetidos y accionables. Un comentario aislado no representa ' +
  'necesariamente a tu audiencia.';

function Examples({ items }: { items: RepresentativeComment[] }) {
  if (items.length === 0) return null;
  return (
    <div className="mt-3 space-y-2">
      {items.map((example, index) => (
        <CommentQuote
          key={index}
          text={example.text}
          meta={[
            sentimentLabel(example.sentiment),
            example.likes !== undefined ? `${formatNumber(example.likes)} me gusta` : null,
            example.video_title ?? null,
          ]
            .filter(Boolean)
            .join(' · ')}
        />
      ))}
    </div>
  );
}

// --- Peticiones -------------------------------------------------------------

export function RequestsTab({ requests }: { requests: RequestItem[] }) {
  if (requests.length === 0) {
    return (
      <EmptyState
        title="No hay peticiones repetidas"
        description="No se han encontrado preguntas ni peticiones que se repitan lo suficiente como para considerarlas un patrón. Una petición aislada no aparece aquí a propósito."
      />
    );
  }

  return (
    <div className="space-y-6">
      <SectionTitle
        title="Peticiones y preguntas repetidas"
        description="Sólo se muestran las que aparecen al menos dos veces. Cuantos más vídeos distintos las contengan, más sólida es la señal."
      />
      <ul className="space-y-4">
        {requests.map((item, index) => (
          <Card as="li" key={`${item.cluster_key}-${item.kind}-${index}`} className="space-y-2">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex flex-wrap items-center gap-2">
                <Badge tone="demo">{item.kind_label_es}</Badge>
                <h3 className="font-semibold">{item.label_es}</h3>
              </div>
              <ConfidenceBadge level={item.confidence_level} />
            </div>
            <p className="text-sm text-muted-foreground">
              <span className="font-medium text-foreground">{formatNumber(item.count)}</span>{' '}
              comentarios en{' '}
              <span className="font-medium text-foreground">{item.unique_video_count}</span>{' '}
              {item.unique_video_count === 1 ? 'vídeo' : 'vídeos distintos'}
            </p>
            <Examples items={item.examples} />
          </Card>
        ))}
      </ul>
    </div>
  );
}

// --- Fortalezas -------------------------------------------------------------

export function StrengthsTab({ strengths }: { strengths: StrengthItem[] }) {
  if (strengths.length === 0) {
    return (
      <EmptyState
        title="Todavía no hay fortalezas claras"
        description="No se han encontrado elogios repetidos sobre un mismo aspecto. Con más comentarios analizados el patrón puede aparecer."
      />
    );
  }

  return (
    <div className="space-y-6">
      <SectionTitle
        title="Lo que tu audiencia valora"
        description="Feedback positivo recurrente agrupado por aspecto. La confianza es alta cuando el elogio se repite en varios vídeos, no sólo en uno."
      />
      <ul className="space-y-4">
        {strengths.map((item) => (
          <Card as="li" key={item.aspect} className="space-y-2">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h3 className="font-semibold">{item.label_es}</h3>
              <ConfidenceBadge level={item.confidence_level} />
            </div>
            <p className="text-sm text-muted-foreground">
              <span className="font-medium text-foreground">{formatNumber(item.count)}</span>{' '}
              comentarios positivos ({formatPercent(item.share_of_positive)} de todo el feedback
              positivo) en{' '}
              <span className="font-medium text-foreground">{item.unique_video_count}</span>{' '}
              {item.unique_video_count === 1 ? 'vídeo' : 'vídeos'}
            </p>
            <Examples items={item.examples} />
          </Card>
        ))}
      </ul>
    </div>
  );
}

// --- Críticas ---------------------------------------------------------------

export function CriticismTab({ criticism }: { criticism: CriticismGroup[] }) {
  const total = criticism.reduce((sum, group) => sum + group.count, 0);

  if (total === 0) {
    return (
      <div className="space-y-6">
        <Callout tone="info">{CRITICISM_NOTICE}</Callout>
        <EmptyState
          title="No se han detectado críticas"
          description="En la muestra analizada no hay comentarios negativos ni ofensivos significativos."
        />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <SectionTitle
        title="Críticas"
        description="Separadas por tipo para que sepas cuáles son accionables y cuáles no."
      />
      <Callout tone="info">{CRITICISM_NOTICE}</Callout>

      {criticism.map((group) => (
        <section key={group.kind} aria-labelledby={`criticas-${group.kind}`}>
          <Card className="space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h3 id={`criticas-${group.kind}`} className="font-semibold">
                {group.label_es}
              </h3>
              <Badge tone={group.kind === 'constructive' ? 'warning' : 'neutral'}>
                {formatNumber(group.count)} comentarios
              </Badge>
            </div>
            <p className="text-sm text-muted-foreground">{group.description_es}</p>

            {group.count === 0 ? (
              <p className="text-sm text-muted-foreground">Ninguno en esta muestra.</p>
            ) : group.kind === 'constructive' ? (
              <ul className="space-y-3">
                {group.items.map((item, index) => (
                  <li key={index} className="rounded-md border border-border p-3">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className="font-medium">{item.label_es}</span>
                      <div className="flex gap-2">
                        <Badge tone="neutral">
                          {formatNumber(item.count ?? 0)} comentarios ·{' '}
                          {formatNumber(item.unique_video_count ?? 0)} vídeos
                        </Badge>
                        {item.actionable ? <Badge tone="warning">Patrón accionable</Badge> : null}
                      </div>
                    </div>
                    <Examples items={item.examples ?? []} />
                  </li>
                ))}
              </ul>
            ) : (
              <Examples items={group.items as RepresentativeComment[]} />
            )}

            {group.kind === 'harassment' && group.count > 0 ? (
              <Callout tone="danger" title="Sobre estos comentarios">
                Esta detección es automática y comete errores. Se muestra para que puedas revisar la
                configuración de moderación en YouTube Studio, no para que respondas a cada mensaje.
                Ninguna recomendación de contenido de este informe se basa en ellos.
              </Callout>
            ) : null}
          </Card>
        </section>
      ))}
    </div>
  );
}

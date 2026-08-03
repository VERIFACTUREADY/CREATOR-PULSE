'use client';

import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';

import { Card, DemoBadge, ErrorState, ProgressBar } from '@/components/ui';
import { ApiError, getRunStatus } from '@/lib/api';
import { cn, formatNumber } from '@/lib/format';
import type { AnalysisStatus, RunStatus } from '@/lib/types';

/** Etapas visibles del pipeline, en orden. */
const STAGES: { status: AnalysisStatus; label: string }[] = [
  { status: 'queued', label: 'Resolviendo canal' },
  { status: 'fetching', label: 'Descargando vídeos y comentarios' },
  { status: 'preprocessing', label: 'Limpiando datos' },
  { status: 'embedding', label: 'Analizando el lenguaje' },
  { status: 'clustering', label: 'Detectando temas' },
  { status: 'scoring', label: 'Calculando tendencias' },
  { status: 'recommending', label: 'Generando recomendaciones' },
  { status: 'completed', label: 'Completado' },
];

const ORDER: AnalysisStatus[] = STAGES.map((stage) => stage.status);

function stageState(current: AnalysisStatus, stage: AnalysisStatus): 'done' | 'active' | 'pending' {
  const currentIndex = ORDER.indexOf(current);
  const stageIndex = ORDER.indexOf(stage);
  if (current === 'completed') return 'done';
  if (stageIndex < currentIndex) return 'done';
  if (stageIndex === currentIndex) return 'active';
  return 'pending';
}

export function AnalysisProgress({ run }: { run: RunStatus }) {
  const failed = run.status === 'failed';

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <Card className="space-y-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h1 className="text-xl font-semibold">
            {failed ? 'El análisis no ha podido completarse' : 'Analizando el canal'}
          </h1>
          {run.is_demo ? <DemoBadge /> : null}
        </div>

        {!failed ? (
          <>
            <ProgressBar value={run.progress} label="Progreso del análisis" />
            <p aria-live="polite" className="text-sm text-muted-foreground">
              {run.status_label_es} · {run.progress} %
            </p>
          </>
        ) : null}

        {failed ? (
          <ErrorState
            title="Análisis fallido"
            message={run.error_message_es ?? 'No se ha podido completar el análisis.'}
            code={run.error_code ?? undefined}
          />
        ) : (
          <ol className="space-y-2">
            {STAGES.map((stage) => {
              const state = stageState(run.status, stage.status);
              return (
                <li
                  key={stage.status}
                  className={cn(
                    'flex items-center gap-3 rounded-md px-3 py-2 text-sm',
                    state === 'active' && 'bg-primary/10 font-medium',
                    state === 'pending' && 'text-muted-foreground',
                  )}
                >
                  <span
                    aria-hidden="true"
                    className={cn(
                      'flex h-5 w-5 shrink-0 items-center justify-center rounded-full border text-xs',
                      state === 'done' && 'border-success bg-success text-success-foreground',
                      state === 'active' && 'border-primary text-primary',
                      state === 'pending' && 'border-border',
                    )}
                  >
                    {state === 'done' ? '✓' : ''}
                  </span>
                  {stage.label}
                </li>
              );
            })}
          </ol>
        )}

        <dl className="grid grid-cols-3 gap-4 border-t border-border pt-4 text-sm">
          <div>
            <dt className="text-xs text-muted-foreground">Vídeos</dt>
            <dd className="font-medium tabular-nums">{formatNumber(run.videos_fetched)}</dd>
          </div>
          <div>
            <dt className="text-xs text-muted-foreground">Comentarios descargados</dt>
            <dd className="font-medium tabular-nums">{formatNumber(run.comments_fetched)}</dd>
          </div>
          <div>
            <dt className="text-xs text-muted-foreground">Comentarios analizados</dt>
            <dd className="font-medium tabular-nums">{formatNumber(run.comments_analysed)}</dd>
          </div>
        </dl>

        {failed ? (
          <div className="flex gap-3">
            <Link
              href="/nuevo-analisis"
              className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground"
            >
              Intentar de nuevo
            </Link>
            <Link
              href="/canales"
              className="rounded-md border border-border px-4 py-2 text-sm font-medium"
            >
              Volver a canales
            </Link>
          </div>
        ) : null}
      </Card>
    </div>
  );
}

/**
 * Sondea el estado de la ejecución.
 *
 * Se usa sondeo en lugar de SSE porque es más simple y fiable a través de
 * proxies, y la frecuencia (1,5 s) es más que suficiente para una barra de
 * progreso.
 */
export function useRunStatus(runId: string) {
  return useQuery({
    queryKey: ['run-status', runId],
    queryFn: () => getRunStatus(runId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === 'completed' || status === 'failed') return false;
      return 1500;
    },
    retry: (failureCount, error) => {
      if (error instanceof ApiError && error.status === 404) return false;
      return failureCount < 3;
    },
  });
}

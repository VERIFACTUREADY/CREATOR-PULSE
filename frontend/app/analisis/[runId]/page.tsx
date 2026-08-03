'use client';

import { use } from 'react';

import { ErrorState, LoadingState } from '@/components/ui';
import { Dashboard } from '@/features/dashboard';
import { AnalysisProgress, useRunStatus } from '@/features/progress';
import { ApiError } from '@/lib/api';

export default function AnalysisPage({ params }: { params: Promise<{ runId: string }> }) {
  const { runId } = use(params);
  const { data: run, isLoading, error, refetch } = useRunStatus(runId);

  if (isLoading) return <LoadingState label="Cargando el estado del análisis" />;

  if (error || !run) {
    return (
      <ErrorState
        title="No se ha encontrado el análisis"
        message={
          error instanceof ApiError
            ? error.message
            : 'El análisis solicitado no existe o ha sido eliminado.'
        }
        code={error instanceof ApiError ? error.code : undefined}
        onRetry={() => void refetch()}
      />
    );
  }

  // Mientras el trabajo está en curso se muestra el progreso; al terminar,
  // el dashboard completo.
  if (run.status !== 'completed') {
    return <AnalysisProgress run={run} />;
  }

  return <Dashboard runId={runId} />;
}

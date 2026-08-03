'use client';

import { useMutation, useQuery } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';

import {
  Button,
  Callout,
  Card,
  DemoBadge,
  EmptyState,
  ErrorState,
  LoadingState,
  SectionTitle,
} from '@/components/ui';
import { ApiError, analyseChannel, getPublicConfig, listDemoChannels } from '@/lib/api';
import { formatNumber } from '@/lib/format';

const DESCRIPTIONS: Record<string, string> = {
  luciaglowdemo:
    'Creadora ficticia de belleza y estilo de vida. Muchos elogios sobre su mirada, peticiones de tutoriales y una crítica recurrente sobre el volumen de la música.',
  pixelraptordemo:
    'Canal ficticio de gaming con humor. Peticiones crecientes de series por capítulos, críticas sobre la duración de los vídeos y un vídeo viral que domina las visualizaciones.',
  codigoclarodemo:
    'Canal ficticio de tecnología. Elogios sobre la claridad de las explicaciones, peticiones de contenido para principiantes y críticas sobre el ritmo.',
};

export default function DemoPage() {
  const router = useRouter();
  const configQuery = useQuery({ queryKey: ['config'], queryFn: getPublicConfig });
  const demoQuery = useQuery({ queryKey: ['demo-channels'], queryFn: listDemoChannels });

  const start = useMutation({
    mutationFn: (handle: string) => analyseChannel({ reference: `@${handle}`, demo: true }),
    onSuccess: (data) => router.push(`/analisis/${data.run_id}`),
  });

  if (demoQuery.isLoading || configQuery.isLoading) {
    return <LoadingState label="Cargando canales de demostración" />;
  }

  if (configQuery.data && !configQuery.data.demo_mode_enabled) {
    return (
      <EmptyState
        title="Modo demostración desactivado"
        description="Esta instalación tiene el modo demostración desactivado (ENABLE_DEMO_MODE=false)."
      />
    );
  }

  if (demoQuery.error) {
    return (
      <ErrorState
        message={
          demoQuery.error instanceof ApiError
            ? demoQuery.error.message
            : 'No se han podido cargar los canales de demostración.'
        }
        onRetry={() => void demoQuery.refetch()}
      />
    );
  }

  return (
    <div className="space-y-6">
      <SectionTitle
        title="Modo demostración"
        description="Prueba el producto completo sin necesidad de ninguna credencial ni de consumir cuota de la API."
      />

      <Callout tone="info" title="Estos datos son ficticios">
        Los tres canales de abajo no existen en YouTube: sus vídeos y comentarios se han generado
        artificialmente para probar el producto. Aun así,{' '}
        <strong>pasan por exactamente el mismo pipeline de análisis</strong> que un canal real: los
        temas, las tendencias y las recomendaciones se calculan en el momento, no están
        precalculados.
      </Callout>

      <div className="grid gap-4 md:grid-cols-3">
        {(demoQuery.data ?? []).map((channel) => (
          <Card key={channel.handle} className="flex flex-col gap-3">
            <div className="flex items-start justify-between gap-2">
              <h3 className="font-semibold">{channel.title}</h3>
              <DemoBadge />
            </div>
            <p className="text-sm text-muted-foreground">
              {DESCRIPTIONS[channel.handle] ?? 'Canal ficticio de demostración.'}
            </p>
            <dl className="grid grid-cols-2 gap-2 text-sm">
              <div>
                <dt className="text-xs text-muted-foreground">Vídeos</dt>
                <dd className="font-medium tabular-nums">{formatNumber(channel.videos)}</dd>
              </div>
              <div>
                <dt className="text-xs text-muted-foreground">Comentarios</dt>
                <dd className="font-medium tabular-nums">{formatNumber(channel.comments)}</dd>
              </div>
            </dl>
            <div className="mt-auto">
              <Button
                onClick={() => start.mutate(channel.handle)}
                disabled={start.isPending}
                className="w-full"
              >
                {start.isPending && start.variables === channel.handle
                  ? 'Iniciando…'
                  : 'Analizar este canal'}
              </Button>
            </div>
          </Card>
        ))}
      </div>

      {start.error instanceof ApiError ? (
        <ErrorState
          title="No se ha podido iniciar el análisis de demostración"
          message={start.error.message}
          code={start.error.code}
        />
      ) : null}

      <Card>
        <h3 className="mb-2 font-semibold">Qué incluyen estos datos</h3>
        <ul className="space-y-2 text-sm text-muted-foreground">
          <li>• Elogios repetidos sobre un aspecto concreto de cada creador.</li>
          <li>• Críticas constructivas recurrentes (audio, ritmo, duración).</li>
          <li>• Preguntas y peticiones de contenido que se repiten en varios vídeos.</li>
          <li>• Un vídeo viral que concentra las visualizaciones, para probar las penalizaciones de confianza.</li>
          <li>• Un vídeo con los comentarios desactivados.</li>
          <li>• Comentarios en español y en inglés, spam y algún comentario ofensivo.</li>
          <li>• Una tendencia real en el tiempo que el análisis debe descubrir por sí solo.</li>
        </ul>
      </Card>
    </div>
  );
}

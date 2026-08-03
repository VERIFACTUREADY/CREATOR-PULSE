'use client';

import { useMutation, useQuery } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import { useMemo, useState } from 'react';

import { Badge, Button, Callout, Card, ErrorState, LoadingState } from '@/components/ui';
import {
  ApiError,
  analyseChannel,
  getPublicConfig,
  getWorkloadEstimate,
  listDemoChannels,
} from '@/lib/api';
import { formatNumber } from '@/lib/format';
import type { SamplingStrategy } from '@/lib/types';
import { buildAnalysisFormSchema, collectErrors } from '@/lib/validation';

const SAMPLING_OPTIONS: { value: SamplingStrategy; label: string; help: string }[] = [
  {
    value: 'mixed',
    label: 'Mixta (recomendada)',
    help: 'Combina comentarios recientes y populares. Reduce el sesgo hacia los más votados.',
  },
  {
    value: 'recent',
    label: 'Recientes',
    help: 'Sólo los comentarios más nuevos. Útil para ver la reacción a tus últimos vídeos.',
  },
  {
    value: 'relevant',
    label: 'Relevantes',
    help: 'Sólo los más votados. Tiende a ser más positiva y más antigua que el conjunto real.',
  },
];

export function AnalysisForm({ initialReference = '' }: { initialReference?: string }) {
  const router = useRouter();

  const configQuery = useQuery({ queryKey: ['config'], queryFn: getPublicConfig });
  const demoQuery = useQuery({ queryKey: ['demo-channels'], queryFn: listDemoChannels });

  const config = configQuery.data;
  const [reference, setReference] = useState(initialReference);
  const [maxVideos, setMaxVideos] = useState(20);
  const [maxCommentsPerVideo, setMaxCommentsPerVideo] = useState(250);
  const [maxCommentsPerChannel, setMaxCommentsPerChannel] = useState(3000);
  const [includeReplies, setIncludeReplies] = useState(false);
  const [samplingStrategy, setSamplingStrategy] = useState<SamplingStrategy>('mixed');
  const [useExternalAi, setUseExternalAi] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const demoHandles = useMemo(
    () => new Set((demoQuery.data ?? []).map((channel) => channel.handle.toLowerCase())),
    [demoQuery.data],
  );
  const isDemoReference = demoHandles.has(reference.trim().replace(/^@/, '').toLowerCase());

  const estimateQuery = useQuery({
    queryKey: ['estimate', maxVideos, maxCommentsPerVideo, includeReplies],
    queryFn: () => getWorkloadEstimate(maxVideos, maxCommentsPerVideo, includeReplies),
    enabled: !isDemoReference,
  });

  const submit = useMutation({
    mutationFn: () =>
      analyseChannel({
        reference: reference.trim(),
        max_videos: maxVideos,
        max_comments_per_video: maxCommentsPerVideo,
        max_comments_per_channel: maxCommentsPerChannel,
        include_replies: includeReplies,
        sampling_strategy: samplingStrategy,
        use_external_ai: useExternalAi,
        demo: isDemoReference,
      }),
    onSuccess: (data) => router.push(`/analisis/${data.run_id}`),
  });

  if (configQuery.isLoading) return <LoadingState label="Cargando configuración" />;
  if (configQuery.error || !config) {
    return (
      <ErrorState
        message={
          configQuery.error instanceof ApiError
            ? configQuery.error.message
            : 'No se ha podido cargar la configuración del servidor.'
        }
        onRetry={() => void configQuery.refetch()}
      />
    );
  }

  const schema = buildAnalysisFormSchema({
    hardMaxVideos: config.limits.hard_max_videos,
    hardMaxCommentsPerVideo: config.limits.hard_max_comments_per_video,
    hardMaxCommentsPerChannel: config.limits.hard_max_comments_per_channel,
  });

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    const result = schema.safeParse({
      reference: reference.trim(),
      maxVideos,
      maxCommentsPerVideo,
      maxCommentsPerChannel,
      includeReplies,
      samplingStrategy,
      useExternalAi,
    });
    if (!result.success) {
      setErrors(collectErrors(result.error));
      return;
    }
    setErrors({});
    submit.mutate();
  };

  const fieldError = (name: string) =>
    errors[name] ? (
      <p id={`${name}-error`} role="alert" className="mt-1 text-sm text-destructive">
        {errors[name]}
      </p>
    ) : null;

  return (
    <form onSubmit={handleSubmit} noValidate className="space-y-6">
      <Card className="space-y-4">
        <div>
          <label htmlFor="reference" className="block text-sm font-medium">
            Canal a analizar
          </label>
          <p className="mt-1 text-sm text-muted-foreground">
            URL del canal, identificador @handle o ID que empieza por UC.
          </p>
          <input
            id="reference"
            name="reference"
            type="text"
            value={reference}
            onChange={(event) => setReference(event.target.value)}
            placeholder="https://www.youtube.com/@creador"
            aria-invalid={Boolean(errors.reference)}
            aria-describedby={errors.reference ? 'reference-error' : undefined}
            className="mt-2 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
          />
          {fieldError('reference')}

          {isDemoReference ? (
            <p className="mt-2 flex items-center gap-2 text-sm">
              <Badge tone="demo">Datos de demostración</Badge>
              <span className="text-muted-foreground">
                Se analizará un canal ficticio. No consume cuota de la API.
              </span>
            </p>
          ) : null}

          {demoQuery.data && demoQuery.data.length > 0 ? (
            <div className="mt-3 flex flex-wrap items-center gap-2 text-sm">
              <span className="text-muted-foreground">Canales de demostración:</span>
              {demoQuery.data.map((channel) => (
                <button
                  key={channel.handle}
                  type="button"
                  onClick={() => setReference(`@${channel.handle}`)}
                  className="rounded-full border border-border px-3 py-1 text-xs transition-colors hover:bg-muted"
                >
                  @{channel.handle}
                </button>
              ))}
            </div>
          ) : null}
        </div>
      </Card>

      <Card className="space-y-5">
        <h2 className="text-base font-semibold">Alcance del análisis</h2>

        <div className="grid gap-5 sm:grid-cols-3">
          <div>
            <label htmlFor="maxVideos" className="block text-sm font-medium">
              Vídeos recientes
            </label>
            <input
              id="maxVideos"
              type="number"
              min={1}
              max={config.limits.hard_max_videos}
              value={maxVideos}
              onChange={(event) => setMaxVideos(Number(event.target.value))}
              aria-invalid={Boolean(errors.maxVideos)}
              aria-describedby={errors.maxVideos ? 'maxVideos-error' : undefined}
              className="mt-2 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
            />
            <p className="mt-1 text-xs text-muted-foreground">
              Máximo {config.limits.hard_max_videos}
            </p>
            {fieldError('maxVideos')}
          </div>

          <div>
            <label htmlFor="maxCommentsPerVideo" className="block text-sm font-medium">
              Comentarios por vídeo
            </label>
            <input
              id="maxCommentsPerVideo"
              type="number"
              min={10}
              max={config.limits.hard_max_comments_per_video}
              value={maxCommentsPerVideo}
              onChange={(event) => setMaxCommentsPerVideo(Number(event.target.value))}
              aria-invalid={Boolean(errors.maxCommentsPerVideo)}
              aria-describedby={errors.maxCommentsPerVideo ? 'maxCommentsPerVideo-error' : undefined}
              className="mt-2 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
            />
            <p className="mt-1 text-xs text-muted-foreground">
              Máximo {config.limits.hard_max_comments_per_video}
            </p>
            {fieldError('maxCommentsPerVideo')}
          </div>

          <div>
            <label htmlFor="maxCommentsPerChannel" className="block text-sm font-medium">
              Comentarios en total
            </label>
            <input
              id="maxCommentsPerChannel"
              type="number"
              min={10}
              max={config.limits.hard_max_comments_per_channel}
              value={maxCommentsPerChannel}
              onChange={(event) => setMaxCommentsPerChannel(Number(event.target.value))}
              aria-invalid={Boolean(errors.maxCommentsPerChannel)}
              aria-describedby={
                errors.maxCommentsPerChannel ? 'maxCommentsPerChannel-error' : undefined
              }
              className="mt-2 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
            />
            <p className="mt-1 text-xs text-muted-foreground">
              Máximo {formatNumber(config.limits.hard_max_comments_per_channel)}
            </p>
            {fieldError('maxCommentsPerChannel')}
          </div>
        </div>

        <fieldset>
          <legend className="text-sm font-medium">Estrategia de muestreo</legend>
          <div className="mt-2 space-y-2">
            {SAMPLING_OPTIONS.map((option) => (
              <label key={option.value} className="flex cursor-pointer gap-3 rounded-md border border-border p-3">
                <input
                  type="radio"
                  name="samplingStrategy"
                  value={option.value}
                  checked={samplingStrategy === option.value}
                  onChange={() => setSamplingStrategy(option.value)}
                  className="mt-1"
                />
                <span>
                  <span className="block text-sm font-medium">{option.label}</span>
                  <span className="block text-xs text-muted-foreground">{option.help}</span>
                </span>
              </label>
            ))}
          </div>
        </fieldset>

        <label className="flex cursor-pointer items-start gap-3">
          <input
            type="checkbox"
            checked={includeReplies}
            onChange={(event) => setIncludeReplies(event.target.checked)}
            className="mt-1"
          />
          <span>
            <span className="block text-sm font-medium">Incluir respuestas a comentarios</span>
            <span className="block text-xs text-muted-foreground">
              Aporta más contexto, pero multiplica el tiempo y la cuota consumida.
            </span>
          </span>
        </label>

        <label className="flex cursor-pointer items-start gap-3">
          <input
            type="checkbox"
            checked={useExternalAi}
            disabled={!config.ai_enabled}
            onChange={(event) => setUseExternalAi(event.target.checked)}
            className="mt-1"
          />
          <span>
            <span className="block text-sm font-medium">
              Usar IA externa para redactar los resúmenes
            </span>
            <span className="block text-xs text-muted-foreground">
              {config.ai_enabled
                ? `Proveedor configurado: ${config.ai_provider}. Los cálculos numéricos no dependen de la IA; sólo se reescriben los textos.`
                : 'No hay ningún proveedor de IA configurado. El análisis se genera igualmente con el motor determinista.'}
            </span>
          </span>
        </label>
      </Card>

      {!isDemoReference && estimateQuery.data ? (
        <Callout tone="info" title="Carga estimada">
          {estimateQuery.data.note_es}
        </Callout>
      ) : null}

      {!config.youtube_configured && !isDemoReference ? (
        <Callout tone="warning" title="Sin clave de la API de YouTube">
          No hay ninguna clave configurada, así que sólo puedes analizar los canales de
          demostración. Añade <code>YOUTUBE_API_KEY</code> al fichero <code>.env</code> para
          analizar canales reales.
        </Callout>
      ) : null}

      {submit.error instanceof ApiError ? (
        <ErrorState
          title="No se ha podido iniciar el análisis"
          message={submit.error.message}
          code={submit.error.code}
        />
      ) : null}

      <div className="flex gap-3">
        <Button type="submit" disabled={submit.isPending}>
          {submit.isPending ? 'Iniciando…' : 'Analizar'}
        </Button>
      </div>
    </form>
  );
}

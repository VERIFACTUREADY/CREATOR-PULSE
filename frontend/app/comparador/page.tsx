'use client';

import { useMutation, useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import { useState } from 'react';

import {
  Badge,
  Button,
  Callout,
  Card,
  DemoBadge,
  EmptyState,
  ErrorState,
  LoadingState,
  SectionTitle,
} from '@/components/ui';
import { ApiError, createComparison, listChannels } from '@/lib/api';
import { formatCompact, formatDecimal, formatPercent, formatSubscribers } from '@/lib/format';

const MAX_SELECTION = 4;

export default function ComparatorPage() {
  const [selected, setSelected] = useState<string[]>([]);

  const channelsQuery = useQuery({ queryKey: ['channels'], queryFn: listChannels });
  const comparison = useMutation({ mutationFn: () => createComparison(selected) });

  const analysable = (channelsQuery.data ?? []).filter((item) => item.latest_completed_run !== null);

  const toggle = (runId: string) => {
    setSelected((current) => {
      if (current.includes(runId)) return current.filter((id) => id !== runId);
      if (current.length >= MAX_SELECTION) return current;
      return [...current, runId];
    });
  };

  if (channelsQuery.isLoading) return <LoadingState label="Cargando canales" />;

  return (
    <div className="space-y-6">
      <SectionTitle
        title="Comparador de canales"
        description="Compara métricas públicas de canales que ya has analizado. Selecciona entre 2 y 4 canales."
      />

      <Callout tone="warning" title="Léelo antes de comparar">
        Los canales tienen audiencias, tamaños, temáticas y fechas de publicación distintas. Esta
        comparación es orientativa y <strong>no es una clasificación de calidad</strong>. Fíjate
        siempre en la puntuación de calidad de datos de cada canal.
      </Callout>

      {analysable.length < 2 ? (
        <EmptyState
          title="Necesitas al menos dos canales analizados"
          description="Analiza un par de canales (o carga varios canales de demostración) y vuelve aquí para compararlos."
          action={
            <div className="flex gap-2">
              <Link
                href="/nuevo-analisis"
                className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground"
              >
                Analizar un canal
              </Link>
              <Link
                href="/demostracion"
                className="rounded-md border border-border px-4 py-2 text-sm font-medium"
              >
                Cargar demostraciones
              </Link>
            </div>
          }
        />
      ) : (
        <>
          <Card>
            <fieldset>
              <legend className="mb-3 text-sm font-medium">
                Canales a comparar ({selected.length}/{MAX_SELECTION})
              </legend>
              <ul className="grid gap-2 sm:grid-cols-2">
                {analysable.map((item) => {
                  const runId = item.latest_completed_run!.id;
                  const checked = selected.includes(runId);
                  return (
                    <li key={item.channel.id}>
                      <label
                        className={
                          checked
                            ? 'flex cursor-pointer items-center gap-3 rounded-md border-2 border-primary bg-primary/5 p-3'
                            : 'flex cursor-pointer items-center gap-3 rounded-md border border-border p-3 hover:bg-muted'
                        }
                      >
                        <input
                          type="checkbox"
                          checked={checked}
                          onChange={() => toggle(runId)}
                          disabled={!checked && selected.length >= MAX_SELECTION}
                        />
                        <span className="min-w-0 flex-1">
                          <span className="block truncate text-sm font-medium">
                            {item.channel.title}
                          </span>
                          <span className="block text-xs text-muted-foreground">
                            {formatCompact(item.latest_completed_run!.comments_analysed)} comentarios
                            analizados
                          </span>
                        </span>
                        {item.channel.source === 'demo' ? <DemoBadge /> : null}
                      </label>
                    </li>
                  );
                })}
              </ul>
            </fieldset>

            <div className="mt-4">
              <Button
                onClick={() => comparison.mutate()}
                disabled={selected.length < 2 || comparison.isPending}
              >
                {comparison.isPending ? 'Comparando…' : 'Comparar'}
              </Button>
            </div>
          </Card>

          {comparison.error instanceof ApiError ? (
            <ErrorState message={comparison.error.message} code={comparison.error.code} />
          ) : null}

          {comparison.data ? (
            <>
              <Card className="overflow-x-auto p-0">
                <table className="w-full min-w-[800px] text-sm">
                  <caption className="sr-only">Comparación de métricas públicas por canal</caption>
                  <thead>
                    <tr className="border-b border-border text-left">
                      <th scope="col" className="p-3 font-medium">
                        Métrica
                      </th>
                      {comparison.data.channels.map((row) => (
                        <th key={row.run_id} scope="col" className="p-3 font-medium">
                          <span className="block">{row.channel_title}</span>
                          {row.is_demo ? <DemoBadge /> : null}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {(
                      [
                        [
                          'Suscriptores',
                          (row: (typeof comparison.data.channels)[number]) =>
                            formatSubscribers(row.subscriber_count, row.subscriber_count_hidden),
                        ],
                        [
                          'Vídeos analizados',
                          (row: (typeof comparison.data.channels)[number]) =>
                            formatCompact(row.videos_analysed),
                        ],
                        [
                          'Comentarios analizados',
                          (row: (typeof comparison.data.channels)[number]) =>
                            formatCompact(row.comments_analysed),
                        ],
                        [
                          'Mediana de visualizaciones',
                          (row: (typeof comparison.data.channels)[number]) =>
                            formatCompact(row.median_views),
                        ],
                        [
                          'Me gusta / 1.000 visualizaciones',
                          (row: (typeof comparison.data.channels)[number]) =>
                            formatDecimal(row.median_likes_per_1000),
                        ],
                        [
                          'Comentarios / 1.000 visualizaciones',
                          (row: (typeof comparison.data.channels)[number]) =>
                            formatDecimal(row.median_comments_per_1000),
                        ],
                        [
                          'Comentarios positivos',
                          (row: (typeof comparison.data.channels)[number]) =>
                            formatPercent(row.positive_share),
                        ],
                        [
                          'Comentarios negativos',
                          (row: (typeof comparison.data.channels)[number]) =>
                            formatPercent(row.negative_share),
                        ],
                        [
                          'Peticiones sobre el total',
                          (row: (typeof comparison.data.channels)[number]) =>
                            formatPercent(row.request_share),
                        ],
                        [
                          'Calidad de los datos',
                          (row: (typeof comparison.data.channels)[number]) =>
                            `${Math.round(row.data_quality_score * 100)}/100 (${row.data_quality_level})`,
                        ],
                      ] as const
                    ).map(([label, accessor]) => (
                      <tr key={label} className="border-b border-border last:border-0">
                        <th scope="row" className="p-3 text-left font-normal text-muted-foreground">
                          {label}
                        </th>
                        {comparison.data.channels.map((row) => (
                          <td key={row.run_id} className="p-3 tabular-nums">
                            {accessor(row)}
                          </td>
                        ))}
                      </tr>
                    ))}
                    <tr>
                      <th scope="row" className="p-3 text-left font-normal text-muted-foreground">
                        Temas principales
                      </th>
                      {comparison.data.channels.map((row) => (
                        <td key={row.run_id} className="p-3">
                          <ul className="space-y-1 text-xs">
                            {row.top_topics.map((topic) => (
                              <li key={topic.label_es}>
                                {topic.label_es}{' '}
                                <span className="text-muted-foreground">
                                  ({formatPercent(topic.share_of_comments)})
                                </span>
                              </li>
                            ))}
                          </ul>
                        </td>
                      ))}
                    </tr>
                  </tbody>
                </table>
              </Card>

              <Card>
                <h3 className="mb-2 font-semibold">Limitaciones de esta comparación</h3>
                <ul className="space-y-2 text-sm text-muted-foreground">
                  {comparison.data.warnings_es.map((warning, index) => (
                    <li key={index} className="flex gap-2">
                      <Badge tone="warning">!</Badge>
                      <span>{warning}</span>
                    </li>
                  ))}
                </ul>
              </Card>
            </>
          ) : null}
        </>
      )}
    </div>
  );
}

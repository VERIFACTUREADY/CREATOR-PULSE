'use client';

import { useQuery } from '@tanstack/react-query';

import {
  Callout,
  Card,
  EmptyState,
  ErrorState,
  LoadingState,
  Metric,
  ProgressBar,
  SectionTitle,
} from '@/components/ui';
import { ApiError, getUsage } from '@/lib/api';
import { formatNumber, formatPercent } from '@/lib/format';

export default function UsagePage() {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['usage'],
    queryFn: () => getUsage(7),
  });

  if (isLoading) return <LoadingState label="Cargando el uso de la API" />;

  if (error || !data) {
    return (
      <ErrorState
        message={
          error instanceof ApiError ? error.message : 'No se ha podido cargar el uso de la API.'
        }
        onRetry={() => void refetch()}
      />
    );
  }

  const usedToday = data.estimated_units_today / data.daily_quota_reference;

  return (
    <div className="space-y-6">
      <SectionTitle
        title="Uso de la API de YouTube"
        description="Consumo aproximado calculado por CreatorPulse AI a partir de sus propias llamadas."
      />

      <Callout tone="warning" title="Esto es una estimación">
        {data.note_es}
      </Callout>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Metric
          label="Unidades estimadas hoy"
          value={formatNumber(data.estimated_units_today)}
          hint={`de ${formatNumber(data.daily_quota_reference)} de referencia`}
        />
        <Metric
          label={`Unidades en ${data.window_days} días`}
          value={formatNumber(data.estimated_units_window)}
        />
        <Metric
          label="Llamadas servidas desde caché"
          value={formatNumber(data.cached_calls_window)}
          hint="No consumen cuota"
          tone="positive"
        />
        <Metric
          label="Llamadas fallidas"
          value={formatNumber(data.failed_calls_window)}
          tone={data.failed_calls_window > 0 ? 'negative' : 'neutral'}
        />
      </div>

      <Card className="space-y-2">
        <h3 className="font-semibold">Consumo de hoy frente a la cuota por defecto</h3>
        <ProgressBar value={usedToday * 100} label="Cuota diaria estimada consumida" />
        <p className="text-sm text-muted-foreground">
          {formatPercent(usedToday, 1)} de {formatNumber(data.daily_quota_reference)} unidades. La
          cuota real de tu proyecto puede ser distinta: consúltala en la consola de Google Cloud.
        </p>
      </Card>

      {data.by_endpoint.length === 0 ? (
        <EmptyState
          title="Sin llamadas registradas"
          description="Todavía no se ha hecho ninguna llamada a la API de YouTube. Los análisis en modo demostración no consumen cuota."
        />
      ) : (
        <Card className="overflow-x-auto p-0">
          <table className="w-full text-sm">
            <caption className="sr-only">Consumo estimado por tipo de endpoint</caption>
            <thead>
              <tr className="border-b border-border text-left">
                <th scope="col" className="p-3 font-medium">
                  Endpoint
                </th>
                <th scope="col" className="p-3 font-medium">
                  Llamadas
                </th>
                <th scope="col" className="p-3 font-medium">
                  Unidades estimadas
                </th>
              </tr>
            </thead>
            <tbody>
              {data.by_endpoint.map((row) => (
                <tr key={row.endpoint} className="border-b border-border last:border-0">
                  <th scope="row" className="p-3 text-left font-mono text-xs font-normal">
                    {row.endpoint}
                  </th>
                  <td className="p-3 tabular-nums">{formatNumber(row.calls)}</td>
                  <td className="p-3 tabular-nums">{formatNumber(row.estimated_quota_units)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}

      <Card>
        <h3 className="mb-2 font-semibold">Cómo reducir el consumo</h3>
        <ul className="space-y-2 text-sm text-muted-foreground">
          <li>• Reduce el número de vídeos y de comentarios por vídeo en el formulario.</li>
          <li>• Desactiva la importación de respuestas a comentarios: multiplica las llamadas.</li>
          <li>
            • Los datos de canal recientes se reutilizan desde la base de datos durante la ventana
            de frescura configurada, así que actualizar poco después no cuesta cuota.
          </li>
          <li>• Usa el modo demostración para probar la interfaz sin gastar nada.</li>
        </ul>
      </Card>
    </div>
  );
}

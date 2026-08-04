/** Utilidades de formato en español. */

import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

const numberFormatter = new Intl.NumberFormat('es-ES');
const compactFormatter = new Intl.NumberFormat('es-ES', {
  notation: 'compact',
  maximumFractionDigits: 1,
});

/** `12345` → `12.345`. Devuelve un guion cuando el dato no está disponible. */
export function formatNumber(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '—';
  return numberFormatter.format(value);
}

/** `1234567` → `1,2 M`. */
export function formatCompact(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '—';
  return compactFormatter.format(value);
}

/** `0.234` → `23 %`. */
export function formatPercent(value: number | null | undefined, decimals = 0): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '—';
  return `${(value * 100).toFixed(decimals).replace('.', ',')} %`;
}

/** Formatea un decimal con coma decimal española. */
export function formatDecimal(value: number | null | undefined, decimals = 1): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '—';
  return value.toFixed(decimals).replace('.', ',');
}

/** `2024-05-01T10:00:00Z` → `1 may 2024`. */
export function formatDate(value: string | null | undefined): string {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '—';
  return new Intl.DateTimeFormat('es-ES', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  }).format(date);
}

/** Fecha con hora, para marcas de «última actualización». */
export function formatDateTime(value: string | null | undefined): string {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '—';
  return new Intl.DateTimeFormat('es-ES', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date);
}

/** «hace 3 días», «hace 2 horas». */
export function formatRelative(value: string | null | undefined): string {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '—';

  const seconds = Math.round((date.getTime() - Date.now()) / 1000);
  const formatter = new Intl.RelativeTimeFormat('es-ES', { numeric: 'auto' });
  const units: [Intl.RelativeTimeFormatUnit, number][] = [
    ['year', 31_536_000],
    ['month', 2_592_000],
    ['day', 86_400],
    ['hour', 3_600],
    ['minute', 60],
  ];
  for (const [unit, secondsPerUnit] of units) {
    if (Math.abs(seconds) >= secondsPerUnit) {
      return formatter.format(Math.round(seconds / secondsPerUnit), unit);
    }
  }
  return 'hace unos segundos';
}

/** `630` → `10:30`. */
export function formatDuration(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined || seconds < 0) return '—';
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const rest = Math.floor(seconds % 60);
  const pad = (n: number) => n.toString().padStart(2, '0');
  return hours > 0 ? `${hours}:${pad(minutes)}:${pad(rest)}` : `${minutes}:${pad(rest)}`;
}

/** Suscriptores para una celda de tabla, respetando que el canal los oculte. */
export function formatSubscribers(count: number | null, hidden: boolean): string {
  if (hidden) return 'Ocultos';
  if (count === null) return '—';
  return formatCompact(count);
}

/**
 * Frase completa de suscriptores.
 *
 * Devuelve el sintagma entero en lugar de un valor al que el llamador añade
 * «suscriptores»: si no, un canal que los oculta mostraría «Ocultos
 * suscriptores», que no es español correcto.
 */
export function subscribersLabel(count: number | null, hidden: boolean): string {
  if (hidden) return 'suscriptores ocultos';
  if (count === null) return 'suscriptores no disponibles';
  return `${formatCompact(count)} suscriptores`;
}

const TREND_ICONS: Record<string, string> = {
  rising: '▲',
  falling: '▼',
  stable: '=',
  unknown: '?',
};

export function trendIcon(direction: string): string {
  return TREND_ICONS[direction] ?? '?';
}

const PERFORMANCE_LABELS: Record<string, string> = {
  por_encima: 'Por encima de tu mediana',
  por_debajo: 'Por debajo de tu mediana',
  normal: 'En tu media habitual',
  reciente: 'Demasiado reciente para comparar',
};

export function performanceLabel(band: string): string {
  return PERFORMANCE_LABELS[band] ?? band;
}

const SENTIMENT_LABELS: Record<string, string> = {
  positive: 'Positivo',
  negative: 'Negativo',
  neutral: 'Neutral',
  mixed: 'Mixto',
  uncertain: 'Incierto',
};

export function sentimentLabel(sentiment: string | undefined): string {
  if (!sentiment) return 'Sin clasificar';
  return SENTIMENT_LABELS[sentiment] ?? sentiment;
}

const OVERALL_SENTIMENT: Record<string, string> = {
  positivo: 'Mayoritariamente positivo',
  critico: 'Con crítica destacable',
  mixto: 'Mixto',
  neutral: 'Neutral',
};

export function overallSentimentLabel(value: string): string {
  return OVERALL_SENTIMENT[value] ?? value;
}

/** Pluraliza en español: `pluralize(1, 'vídeo', 'vídeos')`. */
export function pluralize(count: number, singular: string, plural: string): string {
  return count === 1 ? singular : plural;
}

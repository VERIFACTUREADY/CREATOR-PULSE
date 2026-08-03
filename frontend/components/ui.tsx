/**
 * Componentes de interfaz reutilizables.
 *
 * Ninguno usa `dangerouslySetInnerHTML`: todo el texto procedente de
 * comentarios se renderiza como texto plano, que React escapa por defecto.
 */

'use client';

import type { ReactNode } from 'react';

import { cn } from '@/lib/format';
import type { ConfidenceLevel } from '@/lib/types';

// --- Contenedores -----------------------------------------------------------

export function Card({
  children,
  className,
  as: Tag = 'div',
}: {
  children: ReactNode;
  className?: string;
  as?: 'div' | 'section' | 'article' | 'li';
}) {
  return (
    <Tag className={cn('rounded-lg border border-border bg-card p-5 shadow-sm', className)}>
      {children}
    </Tag>
  );
}

export function SectionTitle({
  title,
  description,
  action,
}: {
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
      <div>
        <h2 className="text-lg font-semibold">{title}</h2>
        {description ? (
          <p className="mt-1 max-w-3xl text-sm text-muted-foreground">{description}</p>
        ) : null}
      </div>
      {action}
    </div>
  );
}

// --- Botones ----------------------------------------------------------------

type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger';

const BUTTON_STYLES: Record<ButtonVariant, string> = {
  primary: 'bg-primary text-primary-foreground hover:opacity-90',
  secondary: 'border border-border bg-secondary text-secondary-foreground hover:bg-muted',
  ghost: 'text-foreground hover:bg-muted',
  danger: 'border border-destructive/40 text-destructive hover:bg-destructive/10',
};

export function Button({
  children,
  onClick,
  type = 'button',
  variant = 'primary',
  disabled,
  className,
  ...rest
}: {
  children: ReactNode;
  onClick?: () => void;
  type?: 'button' | 'submit';
  variant?: ButtonVariant;
  disabled?: boolean;
  className?: string;
} & Omit<React.ButtonHTMLAttributes<HTMLButtonElement>, 'onClick' | 'type' | 'className'>) {
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={cn(
        'inline-flex items-center justify-center gap-2 rounded-md px-4 py-2 text-sm font-medium',
        'transition-colors disabled:cursor-not-allowed disabled:opacity-50',
        BUTTON_STYLES[variant],
        className,
      )}
      {...rest}
    >
      {children}
    </button>
  );
}

// --- Indicadores ------------------------------------------------------------

const CONFIDENCE_STYLES: Record<ConfidenceLevel, string> = {
  alta: 'bg-success/15 text-success border-success/30',
  media: 'bg-warning/15 text-warning border-warning/30',
  baja: 'bg-muted text-muted-foreground border-border',
};

export function ConfidenceBadge({ level }: { level: ConfidenceLevel }) {
  const label = level.charAt(0).toUpperCase() + level.slice(1);
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium',
        CONFIDENCE_STYLES[level] ?? CONFIDENCE_STYLES.baja,
      )}
      title={`Nivel de confianza: ${label}. Se calcula a partir del número de comentarios y de vídeos que respaldan la conclusión.`}
    >
      Confianza {label.toLowerCase()}
    </span>
  );
}

export function Badge({
  children,
  tone = 'neutral',
  title,
}: {
  children: ReactNode;
  tone?: 'neutral' | 'positive' | 'negative' | 'warning' | 'demo';
  title?: string;
}) {
  const styles: Record<string, string> = {
    neutral: 'bg-muted text-muted-foreground border-border',
    positive: 'bg-success/15 text-success border-success/30',
    negative: 'bg-destructive/15 text-destructive border-destructive/30',
    warning: 'bg-warning/15 text-warning border-warning/30',
    demo: 'bg-primary/15 text-primary border-primary/30',
  };
  return (
    <span
      title={title}
      className={cn(
        'inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium',
        styles[tone],
      )}
    >
      {children}
    </span>
  );
}

/** Etiqueta obligatoria en todo lo que provenga de datos ficticios. */
export function DemoBadge() {
  return (
    <Badge tone="demo" title="Estos datos son ficticios y no corresponden a ningún canal real.">
      Datos de demostración
    </Badge>
  );
}

export function TrendBadge({ direction, label }: { direction: string; label: string }) {
  const tone =
    direction === 'rising' ? 'positive' : direction === 'falling' ? 'negative' : 'neutral';
  const icon = direction === 'rising' ? '▲' : direction === 'falling' ? '▼' : '—';
  return (
    <Badge tone={tone}>
      <span aria-hidden="true" className="mr-1">
        {icon}
      </span>
      {label}
    </Badge>
  );
}

// --- Estados ----------------------------------------------------------------

export function LoadingState({ label = 'Cargando…' }: { label?: string }) {
  return (
    <div role="status" aria-live="polite" className="space-y-3 py-6">
      <span className="sr-only">{label}</span>
      <div className="skeleton h-5 w-1/3" />
      <div className="skeleton h-24 w-full" />
      <div className="skeleton h-24 w-full" />
    </div>
  );
}

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <Card className="flex flex-col items-center gap-3 border-dashed py-12 text-center">
      <h3 className="text-base font-semibold">{title}</h3>
      <p className="max-w-md text-sm text-muted-foreground">{description}</p>
      {action}
    </Card>
  );
}

export function ErrorState({
  title = 'Algo ha salido mal',
  message,
  code,
  onRetry,
}: {
  title?: string;
  message: string;
  code?: string;
  onRetry?: () => void;
}) {
  return (
    <Card className="border-destructive/40 bg-destructive/5">
      <div role="alert" className="flex flex-col gap-3">
        <h3 className="text-base font-semibold text-destructive">{title}</h3>
        <p className="text-sm text-foreground">{message}</p>
        {code ? <p className="font-mono text-xs text-muted-foreground">Código: {code}</p> : null}
        {onRetry ? (
          <div>
            <Button variant="secondary" onClick={onRetry}>
              Reintentar
            </Button>
          </div>
        ) : null}
      </div>
    </Card>
  );
}

// --- Presentación de datos --------------------------------------------------

export function Metric({
  label,
  value,
  hint,
  tone = 'neutral',
}: {
  label: string;
  value: ReactNode;
  hint?: string;
  tone?: 'neutral' | 'positive' | 'negative';
}) {
  const toneStyles = {
    neutral: 'text-foreground',
    positive: 'text-success',
    negative: 'text-destructive',
  };
  return (
    <Card className="flex flex-col gap-1">
      <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
        {label}
      </span>
      <span className={cn('text-2xl font-semibold tabular-nums', toneStyles[tone])}>{value}</span>
      {hint ? <span className="text-xs text-muted-foreground">{hint}</span> : null}
    </Card>
  );
}

export function EvidenceList({ items }: { items: string[] }) {
  if (items.length === 0) return null;
  return (
    <ul className="space-y-1.5 text-sm text-muted-foreground">
      {items.map((item, index) => (
        <li key={index} className="flex gap-2">
          <span aria-hidden="true" className="text-primary">
            •
          </span>
          <span>{item}</span>
        </li>
      ))}
    </ul>
  );
}

/** Cita de un comentario. El texto llega ya anonimizado desde la API. */
export function CommentQuote({
  text,
  meta,
}: {
  text: string;
  meta?: string;
}) {
  return (
    <blockquote className="rounded-md border-l-2 border-primary/40 bg-muted/50 px-3 py-2 text-sm">
      <p className="italic">«{text}»</p>
      {meta ? <footer className="mt-1 text-xs text-muted-foreground">{meta}</footer> : null}
    </blockquote>
  );
}

export function Callout({
  tone = 'info',
  title,
  children,
}: {
  tone?: 'info' | 'warning' | 'danger';
  title?: string;
  children: ReactNode;
}) {
  const styles = {
    info: 'border-primary/30 bg-primary/5',
    warning: 'border-warning/40 bg-warning/5',
    danger: 'border-destructive/40 bg-destructive/5',
  };
  return (
    <div className={cn('rounded-lg border p-4 text-sm', styles[tone])}>
      {title ? <p className="mb-1 font-semibold">{title}</p> : null}
      <div className="text-muted-foreground">{children}</div>
    </div>
  );
}

export function ProgressBar({ value, label }: { value: number; label?: string }) {
  const clamped = Math.max(0, Math.min(100, value));
  return (
    <div
      role="progressbar"
      aria-valuenow={clamped}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-label={label ?? 'Progreso'}
      className="h-2 w-full overflow-hidden rounded-full bg-muted"
    >
      <div
        className="h-full rounded-full bg-primary transition-all duration-500"
        style={{ width: `${clamped}%` }}
      />
    </div>
  );
}

/** Barra de distribución de sentimiento en una sola línea. */
export function SentimentBar({
  positive,
  neutral,
  negative,
}: {
  positive: number;
  neutral: number;
  negative: number;
}) {
  const total = positive + neutral + negative;
  if (total === 0) {
    return <div className="h-2 w-full rounded-full bg-muted" aria-label="Sin datos" />;
  }
  const pct = (n: number) => `${(n / total) * 100}%`;
  return (
    <div
      className="flex h-2 w-full overflow-hidden rounded-full"
      role="img"
      aria-label={`${positive} positivos, ${neutral} neutrales, ${negative} negativos`}
    >
      <div className="bg-success" style={{ width: pct(positive) }} />
      <div className="bg-muted-foreground/40" style={{ width: pct(neutral) }} />
      <div className="bg-destructive" style={{ width: pct(negative) }} />
    </div>
  );
}

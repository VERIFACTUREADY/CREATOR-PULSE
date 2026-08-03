import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { ReactNode } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { AnalysisForm } from '@/features/analysis-form';
import { AnalysisProgress } from '@/features/progress';
import { channelReferenceSchema, buildAnalysisFormSchema, collectErrors } from '@/lib/validation';
import type { PublicConfig, RunStatus } from '@/lib/types';

const config: PublicConfig = {
  app_name: 'Creator Signal AI',
  app_env: 'test',
  demo_mode_enabled: true,
  youtube_configured: false,
  ai_enabled: false,
  ai_provider: 'none',
  owner_mode_enabled: false,
  toxicity_analysis_enabled: true,
  anonymize_comment_authors: true,
  data_retention_days: 90,
  algorithm_version: '1.0.0',
  embedding_backend: 'hashing',
  sentiment_backend: 'lexicon',
  limits: {
    default_max_videos: 20,
    default_max_comments_per_video: 250,
    default_max_comments_per_channel: 3000,
    hard_max_videos: 50,
    hard_max_comments_per_video: 500,
    hard_max_comments_per_channel: 10_000,
  },
  disclaimer_es: 'Aviso de prueba.',
  criticism_notice_es: 'Prioriza los patrones repetidos.',
};

function wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

// --- Validación (pura) ------------------------------------------------------

describe('Validación de la referencia de canal', () => {
  it.each([
    'UCX6OQ3DkcsbYNE6H8uQQuVA',
    '@creador',
    'https://www.youtube.com/@creador',
    'youtube.com/@creador',
    'https://www.youtube.com/channel/UCX6OQ3DkcsbYNE6H8uQQuVA',
    'https://youtube.com/c/NombrePersonalizado',
  ])('acepta %s', (value) => {
    expect(channelReferenceSchema.safeParse(value).success).toBe(true);
  });

  it.each([
    '',
    '   ',
    'https://vimeo.com/@creador',
    'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
    'https://www.youtube.com/playlist?list=PL123',
    'https://www.youtube.com/channel/NOESUNID',
    '@ab',
  ])('rechaza %s', (value) => {
    expect(channelReferenceSchema.safeParse(value).success).toBe(false);
  });

  it('devuelve mensajes de error en español', () => {
    const result = channelReferenceSchema.safeParse('https://vimeo.com/x');
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.issues[0]?.message).toMatch(/formato/i);
    }
  });

  it('respeta los máximos declarados por la API', () => {
    const schema = buildAnalysisFormSchema({
      hardMaxVideos: 50,
      hardMaxCommentsPerVideo: 500,
      hardMaxCommentsPerChannel: 10_000,
    });
    const result = schema.safeParse({
      reference: '@creador',
      maxVideos: 999,
      maxCommentsPerVideo: 250,
      maxCommentsPerChannel: 3000,
      includeReplies: false,
      samplingStrategy: 'mixed',
      useExternalAi: false,
    });
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(collectErrors(result.error).maxVideos).toMatch(/máximo permitido es 50/i);
    }
  });
});

// --- Formulario -------------------------------------------------------------

describe('Formulario de análisis', () => {
  beforeEach(() => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        if (url.includes('/api/config/public')) {
          return new Response(JSON.stringify(config), { status: 200 });
        }
        if (url.includes('/api/channels/demo')) {
          return new Response(
            JSON.stringify([
              {
                handle: 'luciaglowdemo',
                youtube_channel_id: 'UCdemo',
                title: 'Lucía Glow (demo)',
                videos: 12,
                comments: 575,
              },
            ]),
            { status: 200 },
          );
        }
        if (url.includes('/api/channels/estimate')) {
          return new Response(
            JSON.stringify({
              estimated_quota_units: 82,
              daily_quota_reference: 10_000,
              estimated_seconds: 20,
              note_es: 'Este análisis consumirá aproximadamente 82 unidades de la cuota diaria.',
            }),
            { status: 200 },
          );
        }
        return new Response(JSON.stringify({}), { status: 200 });
      }),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('muestra el formulario con sus campos', async () => {
    render(<AnalysisForm />, { wrapper });
    expect(await screen.findByLabelText('Canal a analizar')).toBeInTheDocument();
    expect(screen.getByLabelText('Vídeos recientes')).toBeInTheDocument();
    expect(screen.getByLabelText('Comentarios por vídeo')).toBeInTheDocument();
  });

  it('muestra un error de validación cuando la referencia es inválida', async () => {
    const user = userEvent.setup();
    render(<AnalysisForm />, { wrapper });

    const input = await screen.findByLabelText('Canal a analizar');
    await user.type(input, 'https://vimeo.com/algo');
    await user.click(screen.getByRole('button', { name: 'Analizar' }));

    expect(await screen.findByRole('alert')).toHaveTextContent(/formato/i);
    expect(input).toHaveAttribute('aria-invalid', 'true');
  });

  it('no envía la petición cuando el formulario es inválido', async () => {
    const user = userEvent.setup();
    render(<AnalysisForm />, { wrapper });

    await user.click(await screen.findByRole('button', { name: 'Analizar' }));

    await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument());
    const calls = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls;
    expect(calls.some(([url]) => String(url).includes('/api/channels/analyse'))).toBe(false);
  });

  it('avisa de que no hay clave de la API configurada', async () => {
    render(<AnalysisForm />, { wrapper });
    expect(await screen.findByText('Sin clave de la API de YouTube')).toBeInTheDocument();
  });

  it('desactiva la IA externa cuando no hay proveedor', async () => {
    render(<AnalysisForm />, { wrapper });
    const checkbox = await screen.findByRole('checkbox', {
      name: /usar ia externa/i,
    });
    expect(checkbox).toBeDisabled();
  });

  it('identifica los canales de demostración y muestra su etiqueta', async () => {
    const user = userEvent.setup();
    render(<AnalysisForm />, { wrapper });

    await user.click(await screen.findByRole('button', { name: '@luciaglowdemo' }));

    expect(await screen.findByText('Datos de demostración')).toBeInTheDocument();
    expect(screen.getByText(/no consume cuota de la api/i)).toBeInTheDocument();
  });

  it('muestra la estimación de carga para canales reales', async () => {
    const user = userEvent.setup();
    render(<AnalysisForm />, { wrapper });

    await user.type(await screen.findByLabelText('Canal a analizar'), '@uncanalreal');

    expect(await screen.findByText('Carga estimada')).toBeInTheDocument();
    expect(screen.getByText(/82 unidades/)).toBeInTheDocument();
  });
});

// --- Progreso ---------------------------------------------------------------

const baseRun: RunStatus = {
  id: 'run-1',
  channel_id: 'channel-1',
  status: 'clustering',
  status_label_es: 'Detectando temas',
  progress: 72,
  created_at: '2024-06-01T10:00:00Z',
  started_at: '2024-06-01T10:00:05Z',
  completed_at: null,
  videos_fetched: 12,
  comments_fetched: 450,
  comments_analysed: 0,
  error_code: null,
  error_message_es: null,
  is_demo: true,
};

describe('Pantalla de progreso', () => {
  it('muestra la etapa actual y el porcentaje', () => {
    render(<AnalysisProgress run={baseRun} />);
    expect(screen.getByText(/Detectando temas · 72 %/)).toBeInTheDocument();
    expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '72');
  });

  it('lista todas las etapas del pipeline', () => {
    render(<AnalysisProgress run={baseRun} />);
    expect(screen.getByText('Resolviendo canal')).toBeInTheDocument();
    expect(screen.getByText('Descargando vídeos y comentarios')).toBeInTheDocument();
    expect(screen.getByText('Generando recomendaciones')).toBeInTheDocument();
  });

  it('etiqueta los análisis de demostración', () => {
    render(<AnalysisProgress run={baseRun} />);
    expect(screen.getByText('Datos de demostración')).toBeInTheDocument();
  });

  it('muestra el error en español cuando el análisis falla', () => {
    render(
      <AnalysisProgress
        run={{
          ...baseRun,
          status: 'failed',
          progress: 100,
          error_code: 'youtube_cuota_agotada',
          error_message_es: 'Se ha agotado la cuota diaria de la API de YouTube.',
        }}
      />,
    );
    expect(screen.getByRole('alert')).toHaveTextContent(/cuota diaria/i);
    expect(screen.getByText(/youtube_cuota_agotada/)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Intentar de nuevo' })).toBeInTheDocument();
  });

  it('muestra los contadores de vídeos y comentarios', () => {
    render(<AnalysisProgress run={baseRun} />);
    expect(screen.getByText('Comentarios descargados')).toBeInTheDocument();
    expect(screen.getByText('450')).toBeInTheDocument();
  });
});

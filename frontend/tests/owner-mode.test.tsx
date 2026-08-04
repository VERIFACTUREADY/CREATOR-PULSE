import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import type { ReactNode } from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { OwnerMode } from '@/features/owner-mode';
import type { OwnerStatus } from '@/lib/types';

const SCOPES = [
  'https://www.googleapis.com/auth/youtube.readonly',
  'https://www.googleapis.com/auth/yt-analytics.readonly',
];

const disabled: OwnerStatus = {
  enabled: false,
  configured: false,
  encryption_ready: false,
  ready: false,
  missing_config: ['ENABLE_OWNER_MODE=true', 'OAUTH_TOKEN_ENCRYPTION_KEY'],
  scopes: SCOPES,
  owner_only_metrics: ['estimatedMinutesWatched', 'impressions'],
  connections: [],
  message_es: 'Nunca se te pedirá tu contraseña.',
};

const connected: OwnerStatus = {
  ...disabled,
  enabled: true,
  configured: true,
  encryption_ready: true,
  ready: true,
  missing_config: [],
  connections: [
    {
      provider: 'google',
      channel_id: 'canal-1',
      channel_title: 'Mi canal',
      external_account_id: 'UC123',
      scopes: SCOPES,
      expires_at: '2026-01-01T00:00:00Z',
      last_refreshed_at: '2026-01-01T00:00:00Z',
      connected_at: '2026-01-01T00:00:00Z',
      has_refresh_token: true,
    },
  ],
};

function wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

function mockStatus(status: OwnerStatus) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: RequestInfo | URL) => {
      if (String(input).includes('/api/oauth/status')) {
        return new Response(JSON.stringify(status), { status: 200 });
      }
      return new Response(JSON.stringify([]), { status: 200 });
    }),
  );
}

afterEach(() => vi.unstubAllGlobals());

describe('Modo propietario', () => {
  it('declara que sólo pide permisos de lectura', async () => {
    mockStatus(disabled);
    render(<OwnerMode />, { wrapper });

    expect(await screen.findByText('Qué autorizas exactamente')).toBeInTheDocument();
    for (const scope of SCOPES) {
      expect(screen.getByText(`• ${scope}`)).toBeInTheDocument();
      expect(scope).toContain('readonly');
    }
    expect(screen.getByText(/sólo lectura/i)).toBeInTheDocument();
  });

  it('nunca sugiere que se pedirá la contraseña', async () => {
    mockStatus(disabled);
    render(<OwnerMode />, { wrapper });
    expect(await screen.findByText(/nunca se te pedirá tu contraseña/i)).toBeInTheDocument();
  });

  it('enumera la configuración que falta en lugar de fallar', async () => {
    mockStatus(disabled);
    render(<OwnerMode />, { wrapper });

    expect(await screen.findByText('Falta configuración')).toBeInTheDocument();
    expect(screen.getByText('ENABLE_OWNER_MODE=true')).toBeInTheDocument();
    expect(screen.getByText('OAUTH_TOKEN_ENCRYPTION_KEY')).toBeInTheDocument();
  });

  it('no ofrece conectar cuando no está listo', async () => {
    mockStatus(disabled);
    render(<OwnerMode />, { wrapper });

    await screen.findByText('Falta configuración');
    expect(screen.queryByRole('button', { name: /conectar con google/i })).not.toBeInTheDocument();
  });

  it('lista los canales conectados con la opción de desconectar', async () => {
    mockStatus(connected);
    render(<OwnerMode />, { wrapper });

    expect(await screen.findByText('Mi canal')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Desconectar' })).toBeInTheDocument();
    expect(screen.getByText(/la conexión se renueva sola/i)).toBeInTheDocument();
  });

  it('enlaza a la página de permisos de Google para revocar', async () => {
    mockStatus(connected);
    render(<OwnerMode />, { wrapper });

    const link = await screen.findByRole('link', { name: /configuración de tu cuenta de google/i });
    expect(link).toHaveAttribute('href', 'https://myaccount.google.com/permissions');
  });

  it('explica qué métricas aporta y que no se estiman', async () => {
    mockStatus(disabled);
    render(<OwnerMode />, { wrapper });

    expect(
      await screen.findByText('Métricas que aporta el modo propietario'),
    ).toBeInTheDocument();
    expect(screen.getByText(/no las muestra ni las estima/i)).toBeInTheDocument();
  });

  it('traduce el retorno de Google a un mensaje claro', async () => {
    mockStatus(connected);
    // `useSearchParams` está mockeado en tests/setup.ts; se sobreescribe aquí.
    const navigation = await import('next/navigation');
    vi.spyOn(navigation, 'useSearchParams').mockReturnValue(
      new URLSearchParams('oauth=denegado') as never,
    );

    render(<OwnerMode />, { wrapper });
    expect(await screen.findByText(/has cancelado la autorización/i)).toBeInTheDocument();
  });
});

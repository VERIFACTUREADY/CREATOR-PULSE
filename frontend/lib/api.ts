/**
 * Cliente HTTP de la API de CreatorPulse AI.
 *
 * Toda la comunicación pasa por aquí para que el manejo de errores sea
 * uniforme: la API devuelve un envoltorio con `code` y un mensaje en español,
 * que se convierte en un `ApiError` con esa misma información.
 */

import type {
  AnalyseAccepted,
  ApiErrorBody,
  ChannelListItem,
  Comparison,
  Dashboard,
  DemoChannel,
  HealthResponse,
  PublicConfig,
  ResolvedChannel,
  RunStatus,
  SamplingStrategy,
  OwnerAnalytics,
  OwnerStatus,
  StartAuthorization,
  UsageSummary,
  WorkloadEstimate,
} from './types';

/** Hosts que se consideran «desarrollo en mi máquina». */
const LOCAL_HOSTS = new Set(['localhost', '127.0.0.1', '[::1]']);

/**
 * Devuelve la base de la API.
 *
 * Hay tres situaciones y las tres importan:
 *
 * 1. `NEXT_PUBLIC_API_URL` definida: manda siempre. Es el caso de Docker o de
 *    un despliegue con la API en otro dominio.
 * 2. Servido desde un dominio real (Vercel, un servidor propio): la base queda
 *    **vacía**, de modo que las peticiones son relativas (`/api/...`) y salen
 *    al mismo origen. Es lo que espera el enrutado de `vercel.json`, que manda
 *    `/api/*` al servicio de FastAPI.
 * 3. Todo lo demás (localhost): el backend vive en el puerto 8000.
 *
 * Se resuelve en cada llamada, no al importar el módulo: durante el renderizado
 * en servidor no hay `window` y una constante congelaría el valor equivocado.
 */
export function apiBaseUrl(): string {
  const configured = process.env.NEXT_PUBLIC_API_URL?.trim();
  if (configured) return configured.replace(/\/$/, '');

  if (typeof window !== 'undefined' && !LOCAL_HOSTS.has(window.location.hostname)) {
    return '';
  }

  return 'http://localhost:8000';
}

/** Error de la API con el mensaje en español ya listo para mostrar. */
export class ApiError extends Error {
  readonly code: string;
  readonly status: number;
  readonly detail?: string;
  readonly requestId?: string;

  constructor(body: ApiErrorBody, status: number, requestId?: string) {
    super(body.message);
    this.name = 'ApiError';
    this.code = body.code;
    this.status = status;
    this.detail = body.detail;
    this.requestId = requestId;
  }
}

const NETWORK_ERROR: ApiErrorBody = {
  code: 'sin_conexion',
  message:
    'No se ha podido conectar con el servidor. Comprueba que la API está en marcha e inténtalo de nuevo.',
};

interface RequestOptions {
  method?: 'GET' | 'POST' | 'DELETE';
  body?: unknown;
  signal?: AbortSignal;
  /** Sin caché por defecto: los datos de análisis cambian mientras se ejecuta. */
  cache?: RequestCache;
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, signal, cache = 'no-store' } = options;

  let response: Response;
  try {
    response = await fetch(`${apiBaseUrl()}${path}`, {
      method,
      headers: body ? { 'Content-Type': 'application/json' } : undefined,
      body: body ? JSON.stringify(body) : undefined,
      signal,
      cache,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error;
    throw new ApiError(NETWORK_ERROR, 0);
  }

  if (response.status === 204) return undefined as T;

  const requestId = response.headers.get('X-Request-ID') ?? undefined;
  const text = await response.text();
  let payload: unknown = null;
  if (text) {
    try {
      payload = JSON.parse(text);
    } catch {
      payload = null;
    }
  }

  if (!response.ok) {
    const envelope = payload as { error?: ApiErrorBody } | null;
    const errorBody: ApiErrorBody = envelope?.error ?? {
      code: `http_${response.status}`,
      message: 'Se ha producido un error inesperado al comunicarse con el servidor.',
    };
    throw new ApiError(errorBody, response.status, requestId);
  }

  return payload as T;
}

// --- Sistema ---------------------------------------------------------------

export const getHealth = () => request<HealthResponse>('/api/health');
export const getPublicConfig = () => request<PublicConfig>('/api/config/public');

// --- Canales ---------------------------------------------------------------

export const listChannels = () => request<ChannelListItem[]>('/api/channels');
export const listDemoChannels = () => request<DemoChannel[]>('/api/channels/demo');

export const resolveChannel = (reference: string) =>
  request<ResolvedChannel>('/api/channels/resolve', { method: 'POST', body: { reference } });

export const deleteChannel = (channelId: string) =>
  request<void>(`/api/channels/${channelId}`, { method: 'DELETE' });

export interface AnalyseInput {
  reference: string;
  max_videos?: number;
  max_comments_per_video?: number;
  max_comments_per_channel?: number;
  include_replies?: boolean;
  sampling_strategy?: SamplingStrategy;
  use_external_ai?: boolean;
  demo?: boolean;
}

export const analyseChannel = (input: AnalyseInput) =>
  request<AnalyseAccepted>('/api/channels/analyse', { method: 'POST', body: input });

export const refreshChannel = (channelId: string) =>
  request<AnalyseAccepted>(`/api/channels/${channelId}/refresh`, { method: 'POST', body: {} });

export const getWorkloadEstimate = (maxVideos: number, maxCommentsPerVideo: number, includeReplies: boolean) =>
  request<WorkloadEstimate>(
    `/api/channels/estimate?max_videos=${maxVideos}&max_comments_per_video=${maxCommentsPerVideo}&include_replies=${includeReplies}`,
  );

// --- Análisis --------------------------------------------------------------

export const getRunStatus = (runId: string, signal?: AbortSignal) =>
  request<RunStatus>(`/api/analysis-runs/${runId}/status`, { signal });

export const getDashboard = (runId: string) =>
  request<Dashboard>(`/api/analysis-runs/${runId}/dashboard`);

// --- Comparador ------------------------------------------------------------

export const createComparison = (runIds: string[]) =>
  request<Comparison>('/api/comparisons', { method: 'POST', body: { run_ids: runIds } });

// --- Uso de API ------------------------------------------------------------

export const getUsage = (days = 7) => request<UsageSummary>(`/api/usage/youtube?days=${days}`);

// --- Modo propietario ------------------------------------------------------

export const getOwnerStatus = () => request<OwnerStatus>('/api/oauth/status');

export const startOwnerAuthorization = (channelId: string) =>
  request<StartAuthorization>(`/api/oauth/google/start?channel_id=${channelId}`);

export const disconnectOwnerChannel = (channelId: string) =>
  request<{ connected: boolean; message_es: string }>(`/api/oauth/google/${channelId}`, {
    method: 'DELETE',
  });

export const getOwnerAnalytics = (channelId: string, days = 28) =>
  request<OwnerAnalytics>(`/api/oauth/analytics/${channelId}?days=${days}`);

export const exportUrl = (runId: string, format: 'json' | 'csv') =>
  `${apiBaseUrl()}/api/export/${runId}.${format}`;

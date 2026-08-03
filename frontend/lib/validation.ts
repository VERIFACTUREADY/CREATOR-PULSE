/** Validación del formulario de análisis con Zod. */

import { z } from 'zod';

/** Un ID de canal son 24 caracteres que empiezan por `UC`. */
const CHANNEL_ID_RE = /^UC[A-Za-z0-9_-]{22}$/;
const HANDLE_RE = /^@?[A-Za-z0-9._-]{3,30}$/;
const YOUTUBE_HOSTS = ['youtube.com', 'www.youtube.com', 'm.youtube.com', 'music.youtube.com'];

/** Rutas de youtube.com que no corresponden a un canal. */
const NON_CHANNEL_PATHS = ['watch', 'playlist', 'shorts', 'results', 'feed', 'embed'];

function isValidYouTubeUrl(value: string): boolean {
  let url: URL;
  try {
    url = new URL(value.includes('://') ? value : `https://${value}`);
  } catch {
    return false;
  }
  if (!YOUTUBE_HOSTS.includes(url.hostname.toLowerCase())) return false;

  const segments = url.pathname.split('/').filter(Boolean);
  const head = segments[0];
  if (!head) return false;
  if (NON_CHANNEL_PATHS.includes(head)) return false;
  if (head === 'channel') return !!segments[1] && CHANNEL_ID_RE.test(segments[1]);
  return true;
}

/**
 * Valida la referencia del canal en el navegador antes de enviarla.
 * El backend vuelve a validarla: esta comprobación es sólo para dar
 * retroalimentación inmediata.
 */
export const channelReferenceSchema = z
  .string()
  .trim()
  .min(1, 'Introduce la URL, el @handle o el ID del canal.')
  .max(2048, 'La referencia es demasiado larga.')
  .refine(
    (value) => {
      if (CHANNEL_ID_RE.test(value)) return true;
      if (value.startsWith('@')) return HANDLE_RE.test(value);
      if (value.includes('/') || value.includes('.')) return isValidYouTubeUrl(value);
      return HANDLE_RE.test(value);
    },
    {
      message:
        'No se reconoce el formato. Usa una URL de YouTube, un @handle o un ID que empiece por UC.',
    },
  );

export const samplingStrategySchema = z.enum(['recent', 'relevant', 'mixed']);

export interface AnalysisLimits {
  hardMaxVideos: number;
  hardMaxCommentsPerVideo: number;
  hardMaxCommentsPerChannel: number;
}

/** Construye el esquema del formulario con los máximos que declara la API. */
export function buildAnalysisFormSchema(limits: AnalysisLimits) {
  return z.object({
    reference: channelReferenceSchema,
    maxVideos: z
      .number({ invalid_type_error: 'Introduce un número de vídeos.' })
      .int('Debe ser un número entero.')
      .min(1, 'Analiza al menos 1 vídeo.')
      .max(limits.hardMaxVideos, `El máximo permitido es ${limits.hardMaxVideos} vídeos.`),
    maxCommentsPerVideo: z
      .number({ invalid_type_error: 'Introduce un número de comentarios.' })
      .int('Debe ser un número entero.')
      .min(10, 'Analiza al menos 10 comentarios por vídeo.')
      .max(
        limits.hardMaxCommentsPerVideo,
        `El máximo permitido es ${limits.hardMaxCommentsPerVideo} comentarios por vídeo.`,
      ),
    maxCommentsPerChannel: z
      .number({ invalid_type_error: 'Introduce un número de comentarios.' })
      .int('Debe ser un número entero.')
      .min(10, 'Analiza al menos 10 comentarios en total.')
      .max(
        limits.hardMaxCommentsPerChannel,
        `El máximo permitido es ${limits.hardMaxCommentsPerChannel} comentarios en total.`,
      ),
    includeReplies: z.boolean(),
    samplingStrategy: samplingStrategySchema,
    useExternalAi: z.boolean(),
  });
}

export type AnalysisFormValues = z.infer<ReturnType<typeof buildAnalysisFormSchema>>;

/** Convierte los errores de Zod en un mapa `campo → mensaje`. */
export function collectErrors(error: z.ZodError): Record<string, string> {
  const out: Record<string, string> = {};
  for (const issue of error.issues) {
    const key = issue.path[0];
    if (typeof key === 'string' && !out[key]) out[key] = issue.message;
  }
  return out;
}

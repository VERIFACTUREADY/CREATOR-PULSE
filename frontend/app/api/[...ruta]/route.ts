/**
 * Proxy de servidor hacia la API.
 *
 * Existe para una cosa concreta: que el secreto compartido con el proxy de
 * confianza **nunca llegue al navegador**. El navegador habla sólo con este
 * frontend; es el servidor de Next.js quien añade la cabecera de autenticación
 * y reenvía la petición a la API, que en producción no tiene ingress público.
 *
 * Por eso las variables son `API_INTERNAL_URL`, `TRUSTED_AUTH_HEADER` y
 * `TRUSTED_AUTH_VALUE`, sin prefijo `NEXT_PUBLIC_`: si lo llevaran, Next.js las
 * incrustaría en el bundle del cliente y el secreto sería público.
 *
 * Si no está configurado, el proxy no adivina nada: responde 503 con un
 * mensaje claro en lugar de fallar de forma confusa.
 */

import { NextRequest } from 'next/server';

import { COOKIE_SESION, identidadDeSesion } from '@/lib/beta-session';

export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

/** Cabeceras que no deben reenviarse tal cual. */
const HOP_BY_HOP = new Set([
  'connection',
  'keep-alive',
  'transfer-encoding',
  'upgrade',
  'host',
  'content-length',
]);

/**
 * Cabeceras de reenvío que **el cliente no puede dictar**.
 *
 * La API confía en `X-Forwarded-For` cuando la petición viene de una red de
 * confianza, y este proxy está en una. Si se reenviara la cabecera tal cual,
 * cualquiera podría elegir su propia clave de rate limit —y crear una entrada
 * nueva en cada petición— simplemente cambiando el valor.
 */
const CABECERAS_DE_REENVIO = [
  'forwarded',
  'x-forwarded-for',
  'x-forwarded-host',
  'x-forwarded-proto',
  'x-forwarded-port',
  'x-real-ip',
  'x-client-ip',
  'true-client-ip',
  'cf-connecting-ip',
];

/** Cabecera con la identidad que fija el proxy, no el cliente. */
const CABECERA_IDENTIDAD = 'x-creatorpulse-identity';

function sinConfigurar(): Response {
  return Response.json(
    {
      ok: false,
      data: null,
      error: {
        code: 'proxy_no_configurado',
        message:
          'Este despliegue no tiene configurada la conexión interna con la API. ' +
          'Define API_INTERNAL_URL en el servidor del frontend.',
      },
    },
    { status: 503 },
  );
}

async function proxy(request: NextRequest, ruta: string[]): Promise<Response> {
  const base = process.env.API_INTERNAL_URL?.replace(/\/$/, '');
  if (!base) return sinConfigurar();

  const cabecera = process.env.TRUSTED_AUTH_HEADER;
  const secreto = process.env.TRUSTED_AUTH_VALUE;

  const destino = new URL(`${base}/api/${ruta.join('/')}`);
  destino.search = request.nextUrl.search;

  const headers = new Headers();
  request.headers.forEach((valor, clave) => {
    if (!HOP_BY_HOP.has(clave.toLowerCase())) headers.set(clave, valor);
  });

  // Se descarta todo lo que el cliente pueda usar para suplantar su origen.
  for (const sobrante of CABECERAS_DE_REENVIO) headers.delete(sobrante);
  headers.delete(CABECERA_IDENTIDAD);
  // Y cualquier copia de la cabecera de servicio que viniera del navegador.
  if (cabecera) headers.delete(cabecera);

  // La cabecera de servicio la pone el servidor, nunca el cliente.
  if (cabecera && secreto) headers.set(cabecera, secreto);

  // Identidad para el rate limit: derivada de la cookie de sesión firmada, que
  // el visitante no sabe fabricar. Sin sesión, todos comparten cubo.
  const identidad = await identidadDeSesion(request.cookies.get(COOKIE_SESION)?.value);
  headers.set(CABECERA_IDENTIDAD, identidad ?? 'anonimo');

  const cuerpo =
    request.method === 'GET' || request.method === 'HEAD'
      ? undefined
      : await request.arrayBuffer();

  let respuesta: Response;
  try {
    respuesta = await fetch(destino, {
      method: request.method,
      headers,
      body: cuerpo,
      redirect: 'manual',
      cache: 'no-store',
    });
  } catch {
    return Response.json(
      {
        ok: false,
        data: null,
        error: {
          code: 'sin_conexion',
          message: 'No se ha podido contactar con la API interna.',
        },
      },
      { status: 502 },
    );
  }

  const salida = new Headers(respuesta.headers);
  for (const clave of HOP_BY_HOP) salida.delete(clave);
  // No se filtra al navegador ninguna pista del mecanismo interno.
  if (cabecera) salida.delete(cabecera);
  salida.delete(CABECERA_IDENTIDAD);

  return new Response(respuesta.body, {
    status: respuesta.status,
    statusText: respuesta.statusText,
    headers: salida,
  });
}

type Contexto = { params: Promise<{ ruta: string[] }> };

export async function GET(request: NextRequest, contexto: Contexto): Promise<Response> {
  return proxy(request, (await contexto.params).ruta);
}

export async function POST(request: NextRequest, contexto: Contexto): Promise<Response> {
  return proxy(request, (await contexto.params).ruta);
}

export async function DELETE(request: NextRequest, contexto: Contexto): Promise<Response> {
  return proxy(request, (await contexto.params).ruta);
}

export async function PUT(request: NextRequest, contexto: Contexto): Promise<Response> {
  return proxy(request, (await contexto.params).ruta);
}

export async function PATCH(request: NextRequest, contexto: Contexto): Promise<Response> {
  return proxy(request, (await contexto.params).ruta);
}

/**
 * Entrada a la beta privada.
 *
 * La contraseña se comprueba **sólo en el servidor** y nunca se devuelve, ni
 * se guarda en `localStorage`, ni viaja al bundle. Lo único que sale es una
 * cookie firmada, `HttpOnly`.
 */

import { NextRequest, NextResponse } from 'next/server';

import { COOKIE_SESION, crearSesion, estadoBeta, passwordCorrecta } from '@/lib/beta-session';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

/** Intentos permitidos por ventana y origen. */
const MAX_INTENTOS = 8;
const VENTANA_MS = 60_000;

/** Ventanas por origen. Se limpian solas al caducar. */
const intentos = new Map<string, number[]>();

function origen(request: NextRequest): string {
  // En el edge de Azure/Vercel la IP llega por cabecera; se recorta para que
  // un cliente no pueda inflar la clave con una cadena larga.
  const bruto =
    request.headers.get('x-forwarded-for')?.split(',')[0]?.trim() ??
    request.headers.get('x-real-ip') ??
    'desconocido';
  return bruto.slice(0, 45);
}

function demasiadosIntentos(clave: string): boolean {
  const ahora = Date.now();
  const previos = (intentos.get(clave) ?? []).filter((t) => ahora - t < VENTANA_MS);
  previos.push(ahora);
  intentos.set(clave, previos);

  // Poda: sin esto el mapa crecería sin límite con orígenes falsificados.
  if (intentos.size > 5_000) {
    for (const [k, v] of intentos) {
      if (v.every((t) => ahora - t >= VENTANA_MS)) intentos.delete(k);
    }
  }
  return previos.length > MAX_INTENTOS;
}

function error(code: string, message: string, status: number): NextResponse {
  return NextResponse.json({ ok: false, data: null, error: { code, message } }, { status });
}

export async function POST(request: NextRequest): Promise<NextResponse> {
  const estado = estadoBeta();
  if (!estado.activa) {
    return error(
      'beta_desactivada',
      'Esta instalación no tiene activado el acceso por contraseña.',
      400,
    );
  }

  if (demasiadosIntentos(origen(request))) {
    return error(
      'demasiados_intentos',
      'Demasiados intentos seguidos. Espera un minuto y vuelve a probar.',
      429,
    );
  }

  let password = '';
  try {
    const cuerpo = (await request.json()) as { password?: unknown };
    password = typeof cuerpo.password === 'string' ? cuerpo.password : '';
  } catch {
    password = '';
  }

  if (!(await passwordCorrecta(password))) {
    // El mismo mensaje siempre: no se distingue «vacía» de «incorrecta».
    return error('acceso_denegado', 'La contraseña no es correcta.', 401);
  }

  const { valor, expira } = await crearSesion();
  const respuesta = NextResponse.json({ ok: true, data: { expira: expira.toISOString() } });
  respuesta.cookies.set({
    name: COOKIE_SESION,
    value: valor,
    httpOnly: true,
    sameSite: 'lax',
    secure: process.env.NODE_ENV === 'production',
    path: '/',
    expires: expira,
  });
  return respuesta;
}

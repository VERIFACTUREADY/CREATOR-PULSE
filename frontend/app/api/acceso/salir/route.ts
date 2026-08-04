/** Cierre de sesión de la beta. */

import { NextResponse } from 'next/server';

import { COOKIE_SESION } from '@/lib/beta-session';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

export async function POST(): Promise<NextResponse> {
  const respuesta = NextResponse.json({ ok: true, data: null });
  // Se borra fijando una cookie ya caducada: así desaparece también en
  // navegadores que ignoran el borrado directo.
  respuesta.cookies.set({
    name: COOKIE_SESION,
    value: '',
    httpOnly: true,
    sameSite: 'lax',
    secure: process.env.NODE_ENV === 'production',
    path: '/',
    maxAge: 0,
  });
  return respuesta;
}

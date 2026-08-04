/**
 * Chequeo de vida del contenedor del frontend.
 *
 * Deliberadamente pobre: sólo dice que el proceso responde. No revela si la
 * beta está activada, ni qué API hay detrás, ni ninguna otra configuración.
 */

import { NextResponse } from 'next/server';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

export async function GET(): Promise<NextResponse> {
  return NextResponse.json({ ok: true });
}

/**
 * Puerta de la beta privada.
 *
 * Sin esto, el frontend de un despliegue público deja que cualquier visitante
 * lance análisis, gaste cuota de YouTube y borre datos: el proxy interno le
 * añadiría el secreto de servicio encantado. El secreto autentica al servicio,
 * nunca a la persona.
 *
 * Se ejecuta en el edge, antes que cualquier página o ruta, para que no haya
 * forma de saltárselo desde una ruta nueva que alguien olvide proteger.
 */

import { NextRequest, NextResponse } from 'next/server';

import { COOKIE_SESION, estadoBeta, sesionValida } from '@/lib/beta-session';

/** Rutas accesibles sin sesión. La lista es deliberadamente corta. */
const ABIERTAS = new Set([
  '/acceso',
  '/api/acceso/entrar',
  '/api/acceso/salir',
  // Chequeo de vida del contenedor. No revela configuración.
  '/api/salud-frontend',
]);

function esAbierta(pathname: string): boolean {
  if (ABIERTAS.has(pathname)) return true;
  // Recursos internos de Next y ficheros estáticos.
  return (
    pathname.startsWith('/_next/') ||
    pathname === '/favicon.ico' ||
    pathname.startsWith('/iconos/')
  );
}

export async function middleware(request: NextRequest): Promise<NextResponse> {
  const estado = estadoBeta();

  if (estado.malConfigurada) {
    // Activada pero incompleta: se cierra, no se abre. Un despliegue a medias
    // no puede convertirse en una instalación pública por accidente.
    return NextResponse.json(
      {
        ok: false,
        data: null,
        error: {
          code: 'beta_mal_configurada',
          message:
            'El acceso a la beta está activado pero incompleto. ' +
            'Revisa BETA_ACCESS_PASSWORD y BETA_SESSION_SECRET en el servidor.',
        },
      },
      { status: 500 },
    );
  }

  if (!estado.activa) return NextResponse.next();

  const { pathname } = request.nextUrl;
  if (esAbierta(pathname)) return NextResponse.next();

  if (await sesionValida(request.cookies.get(COOKIE_SESION)?.value)) {
    return NextResponse.next();
  }

  // A las rutas de datos se les responde con un error, no con una redirección
  // que el cliente interpretaría como una respuesta válida.
  if (pathname.startsWith('/api/')) {
    return NextResponse.json(
      {
        ok: false,
        data: null,
        error: {
          code: 'beta_sin_acceso',
          message: 'Necesitas la contraseña de la beta para usar esta aplicación.',
        },
      },
      { status: 401 },
    );
  }

  const destino = request.nextUrl.clone();
  destino.pathname = '/acceso';
  destino.search = '';
  // Se guarda a dónde iba para volver después de entrar.
  if (pathname !== '/') destino.searchParams.set('destino', pathname);
  return NextResponse.redirect(destino);
}

export const config = {
  // Todo salvo los recursos internos de Next, que ya se filtran arriba.
  matcher: ['/((?!_next/static|_next/image).*)'],
};

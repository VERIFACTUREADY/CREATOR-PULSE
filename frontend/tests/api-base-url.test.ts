import { afterEach, describe, expect, it } from 'vitest';

import { apiBaseUrl, exportUrl } from '@/lib/api';

/**
 * Estas pruebas fijan el contrato de enrutado.
 *
 * En producción el frontend y la API comparten origen (`vercel.json` manda
 * `/api/*` al servicio de FastAPI), así que apuntar a `localhost:8000` desde un
 * dominio real sería un fallo silencioso: el navegador intentaría conectarse a
 * la máquina del visitante.
 */

const ORIGINAL_ENV = process.env.NEXT_PUBLIC_API_URL;

function setHostname(hostname: string): void {
  Object.defineProperty(window, 'location', {
    value: { ...window.location, hostname, origin: `https://${hostname}` },
    writable: true,
    configurable: true,
  });
}

afterEach(() => {
  process.env.NEXT_PUBLIC_API_URL = ORIGINAL_ENV;
  setHostname('localhost');
});

describe('apiBaseUrl', () => {
  it('apunta al puerto 8000 en desarrollo local', () => {
    delete process.env.NEXT_PUBLIC_API_URL;
    setHostname('localhost');
    expect(apiBaseUrl()).toBe('http://localhost:8000');
  });

  it('usa rutas relativas cuando se sirve desde un dominio real', () => {
    delete process.env.NEXT_PUBLIC_API_URL;
    setHostname('creator-pulse.vercel.app');
    expect(apiBaseUrl()).toBe('');
  });

  it('la URL de exportación queda relativa en producción', () => {
    delete process.env.NEXT_PUBLIC_API_URL;
    setHostname('creator-pulse.vercel.app');
    expect(exportUrl('abc', 'csv')).toBe('/api/export/abc.csv');
  });

  it('NEXT_PUBLIC_API_URL manda sobre todo lo demás', () => {
    process.env.NEXT_PUBLIC_API_URL = 'https://api.ejemplo.com/';
    setHostname('creator-pulse.vercel.app');
    expect(apiBaseUrl()).toBe('https://api.ejemplo.com');
  });

  it('una variable vacía no deja la base a medias', () => {
    process.env.NEXT_PUBLIC_API_URL = '   ';
    setHostname('localhost');
    expect(apiBaseUrl()).toBe('http://localhost:8000');
  });
});

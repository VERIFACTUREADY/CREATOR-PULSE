import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join } from 'node:path';

import { describe, expect, it } from 'vitest';

/**
 * El secreto compartido con la API **nunca puede llegar al navegador**.
 *
 * Next.js incrusta en el bundle del cliente cualquier variable con prefijo
 * `NEXT_PUBLIC_`. Basta con que alguien renombre `TRUSTED_AUTH_VALUE` a
 * `NEXT_PUBLIC_TRUSTED_AUTH_VALUE` —o lo lea desde un componente de cliente—
 * para publicar la llave de toda la instalación. Esta prueba lo impide.
 */

const RAIZ = join(__dirname, '..');

function ficherosDe(directorio: string, extensiones: string[]): string[] {
  const salida: string[] = [];
  const pendientes = [directorio];
  while (pendientes.length > 0) {
    const actual = pendientes.pop();
    if (!actual) continue;
    for (const entrada of readdirSync(actual)) {
      if (entrada === 'node_modules' || entrada === '.next') continue;
      const ruta = join(actual, entrada);
      if (statSync(ruta).isDirectory()) {
        pendientes.push(ruta);
      } else if (extensiones.some((ext) => entrada.endsWith(ext))) {
        salida.push(ruta);
      }
    }
  }
  return salida;
}

describe('el secreto del proxy no se expone al navegador', () => {
  it('ninguna variable de autenticación lleva el prefijo NEXT_PUBLIC_', () => {
    const fuentes = [
      ...ficherosDe(join(RAIZ, 'app'), ['.ts', '.tsx']),
      ...ficherosDe(join(RAIZ, 'lib'), ['.ts', '.tsx']),
      ...ficherosDe(join(RAIZ, 'features'), ['.ts', '.tsx']),
      ...ficherosDe(join(RAIZ, 'components'), ['.ts', '.tsx']),
    ];

    const infractores = fuentes.filter((ruta) => {
      const contenido = readFileSync(ruta, 'utf8');
      return (
        contenido.includes('NEXT_PUBLIC_TRUSTED_AUTH') ||
        contenido.includes('NEXT_PUBLIC_API_INTERNAL')
      );
    });

    expect(infractores).toEqual([]);
  });

  it('sólo el proxy de servidor lee el secreto', () => {
    const fuentes = [
      ...ficherosDe(join(RAIZ, 'app'), ['.ts', '.tsx']),
      ...ficherosDe(join(RAIZ, 'lib'), ['.ts', '.tsx']),
      ...ficherosDe(join(RAIZ, 'features'), ['.ts', '.tsx']),
      ...ficherosDe(join(RAIZ, 'components'), ['.ts', '.tsx']),
    ];

    const lectores = fuentes.filter((ruta) =>
      readFileSync(ruta, 'utf8').includes('TRUSTED_AUTH_VALUE'),
    );

    expect(lectores).toHaveLength(1);
    expect(lectores[0]).toContain(join('app', 'api'));

    // Y ese fichero no puede ser un componente de cliente.
    const proxy = readFileSync(lectores[0] as string, 'utf8');
    expect(proxy).not.toContain("'use client'");
    expect(proxy).toContain("runtime = 'nodejs'");
  });

  it('el cliente HTTP del navegador nunca añade la cabecera de confianza', () => {
    const cliente = readFileSync(join(RAIZ, 'lib', 'api.ts'), 'utf8');
    expect(cliente).not.toContain('TRUSTED_AUTH');
    expect(cliente).not.toContain('X-Auth-Token');
  });

  it('los secretos de la beta tampoco llevan prefijo público', () => {
    const fuentes = [
      ...ficherosDe(join(RAIZ, 'app'), ['.ts', '.tsx']),
      ...ficherosDe(join(RAIZ, 'lib'), ['.ts', '.tsx']),
      ...ficherosDe(join(RAIZ, 'features'), ['.ts', '.tsx']),
      ...ficherosDe(join(RAIZ, 'components'), ['.ts', '.tsx']),
    ];

    const infractores = fuentes.filter((ruta) =>
      /NEXT_PUBLIC_BETA/.test(readFileSync(ruta, 'utf8')),
    );

    expect(infractores).toEqual([]);
  });

  it('la pantalla de acceso no guarda la contraseña en ningún sitio persistente', () => {
    const pantalla = readFileSync(join(RAIZ, 'app', 'acceso', 'page.tsx'), 'utf8');
    // Se buscan usos reales, no menciones en comentarios: el propio fichero
    // documenta que NO usa estos almacenes.
    const sinComentarios = pantalla
      .replace(/\/\*[\s\S]*?\*\//g, '')
      .replace(/^\s*\/\/.*$/gm, '');

    for (const prohibido of [
      'localStorage.',
      'sessionStorage.',
      'document.cookie',
      'window.name',
    ]) {
      expect(sinComentarios, `la pantalla no debe usar ${prohibido}`).not.toContain(prohibido);
    }
  });

  it('el proxy borra las cabeceras de reenvío que envía el cliente', () => {
    const proxy = readFileSync(join(RAIZ, 'app', 'api', '[...ruta]', 'route.ts'), 'utf8');
    for (const cabecera of ['x-forwarded-for', 'x-real-ip', 'forwarded']) {
      expect(proxy).toContain(cabecera);
    }
    expect(proxy).toContain('CABECERAS_DE_REENVIO');
  });
});

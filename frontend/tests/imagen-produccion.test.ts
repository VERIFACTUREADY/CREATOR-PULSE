import { readFileSync } from 'node:fs';
import { join } from 'node:path';

import { describe, expect, it } from 'vitest';

/**
 * La imagen de producción no puede llevar `localhost` incrustado.
 *
 * `NEXT_PUBLIC_*` se resuelve en tiempo de construcción y queda escrito en el
 * bundle del navegador. Con un valor por defecto de `http://localhost:8000`,
 * una imagen construida sin pasar el argumento sale compilada para hablar con
 * el `localhost` **de quien abre la página**, no con el proxy del despliegue.
 * Ninguna variable de runtime puede arreglar eso después.
 */

const RAIZ = join(__dirname, '..');

describe('Dockerfile del frontend', () => {
  const dockerfile = readFileSync(join(RAIZ, 'Dockerfile'), 'utf8');

  it('no fija un localhost por defecto para la API', () => {
    const lineas = dockerfile
      .split('\n')
      .filter((linea) => linea.trim().startsWith('ARG') || linea.trim().startsWith('ENV'));

    for (const linea of lineas) {
      if (!linea.includes('NEXT_PUBLIC_API_URL')) continue;
      expect(
        linea,
        'un valor por defecto con localhost rompe el despliegue en cualquier dominio real',
      ).not.toMatch(/localhost|127\.0\.0\.1/);
    }
  });

  it('declara el argumento para poder pasarlo cuando haga falta', () => {
    expect(dockerfile).toContain('ARG NEXT_PUBLIC_API_URL');
  });

  it('ninguna variable NEXT_PUBLIC_ lleva un secreto', () => {
    const publicas = dockerfile.match(/NEXT_PUBLIC_[A-Z_]+/g) ?? [];
    for (const variable of publicas) {
      expect(variable).not.toMatch(/SECRET|PASSWORD|TOKEN|KEY/);
    }
  });
});

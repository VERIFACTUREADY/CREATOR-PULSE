import { expect, test } from '@playwright/test';

/**
 * Comprueba el modelo de despliegue de `vercel.json`: un solo origen que manda
 * `/api/*` al servicio de FastAPI y el resto al de Next.js.
 *
 * Lo que se verifica no es la configuración de Vercel (eso sólo se puede
 * comprobar desplegando), sino la parte que sí depende de este código: que el
 * navegador emite las peticiones **relativas al origen desde el que se sirve la
 * página** en cuanto ese origen no es localhost. Si el frontend siguiera
 * apuntando a `http://localhost:8000`, en producción intentaría conectarse a la
 * máquina del visitante y todo fallaría.
 *
 * Requiere un proxy de mismo origen delante de ambos servicios. Se salta sola
 * si no se le indica uno con E2E_SAME_ORIGIN_URL.
 */

const SAME_ORIGIN = process.env.E2E_SAME_ORIGIN_URL;

test.describe('Despliegue de un solo origen', () => {
  test.skip(!SAME_ORIGIN, 'Necesita E2E_SAME_ORIGIN_URL apuntando a un proxy /api → backend');

  test('el frontend habla con la API por rutas relativas', async ({ page }) => {
    const base = SAME_ORIGIN as string;
    const origin = new URL(base).origin;
    const apiRequests: string[] = [];

    page.on('request', (request) => {
      if (request.url().includes('/api/')) apiRequests.push(request.url());
    });

    await page.goto(`${base}/demostracion`);
    await page.getByRole('button', { name: 'Analizar este canal' }).first().click();

    // El análisis completo tiene que llegar hasta el panel: si alguna petición
    // se hubiera ido a otro host, aquí se vería el error de conexión.
    await expect(page.getByRole('tab', { name: 'Resumen' })).toBeVisible({ timeout: 90_000 });

    // Una pestaña más, para que la comprobación no dependa sólo de la primera
    // carga: si el origen fuese el equivocado, esta petición también fallaría.
    await page.getByRole('tab', { name: 'Ideas de contenido' }).click();
    await expect(page.getByRole('heading', { name: 'Recomendaciones' })).toBeVisible();

    expect(apiRequests.length).toBeGreaterThan(0);
    const fueraDeOrigen = apiRequests.filter((url) => !url.startsWith(origin));
    expect(fueraDeOrigen, `Peticiones fuera del origen ${origin}`).toEqual([]);
  });
});

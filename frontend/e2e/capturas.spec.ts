import { expect, test, type Page } from '@playwright/test';

/**
 * Genera las capturas del README.
 *
 * No es una prueba de regresión: es un generador reproducible que además
 * comprueba que cada pantalla renderiza lo que dice el README. Se ejecuta a
 * propósito sólo cuando se pide:
 *
 *   npx playwright test capturas --grep-invert=@nunca   # (por defecto se salta)
 *   CAPTURAS=1 npx playwright test capturas
 *
 * Requiere la API, el worker y el frontend en marcha.
 */

const DIR = '../docs/capturas';

test.skip(!process.env.CAPTURAS, 'Define CAPTURAS=1 para regenerar las capturas del README.');

test.use({ viewport: { width: 1440, height: 900 } });

async function shot(page: Page, name: string): Promise<void> {
  // `animations: 'disabled'` evita capturas a medio desvanecer.
  await page.screenshot({ path: `${DIR}/${name}.png`, animations: 'disabled' });
}

async function analizarDemo(page: Page, indice: number): Promise<void> {
  await page.goto('/demostracion');
  await page.getByRole('button', { name: 'Analizar este canal' }).nth(indice).click();
  await expect(page.getByRole('tab', { name: 'Resumen' })).toBeVisible({ timeout: 90_000 });
}

test('genera las capturas del README', async ({ page }) => {
  // --- 1. Formulario de nuevo análisis (antes de tener datos) ---
  await page.goto('/nuevo-analisis');
  await expect(page.getByLabel('Canal a analizar')).toBeVisible();
  await page.getByLabel('Canal a analizar').fill('@uncanaldeejemplo');
  await expect(page.getByText('Carga estimada')).toBeVisible();
  await shot(page, '02-nuevo-analisis');

  // --- 2. Modo demostración ---
  await page.goto('/demostracion');
  await expect(page.getByText('Estos datos son ficticios')).toBeVisible();
  await shot(page, '09-demostracion');

  // --- 3. Progreso: se captura en cuanto arranca el análisis ---
  await page.getByRole('button', { name: 'Analizar este canal' }).first().click();
  await expect(page).toHaveURL(/\/analisis\//);
  await expect(page.getByRole('progressbar')).toBeVisible();
  await shot(page, '03-progreso');

  // --- 4. Dashboard, pestaña a pestaña ---
  await expect(page.getByRole('tab', { name: 'Resumen' })).toBeVisible({ timeout: 90_000 });
  await shot(page, '04-resumen');

  await page.getByRole('tab', { name: 'Temas' }).click();
  await expect(page.getByRole('heading', { name: 'Temas detectados' })).toBeVisible();
  await shot(page, '05-temas');

  await page.getByRole('tab', { name: 'Ideas de contenido' }).click();
  await expect(page.getByRole('heading', { name: 'Recomendaciones' })).toBeVisible();
  await shot(page, '06-ideas');

  await page.getByRole('tab', { name: 'Vídeos' }).click();
  await expect(page.getByRole('table')).toBeVisible();
  await shot(page, '07-videos');

  await page.getByRole('tab', { name: 'Calidad de los datos' }).click();
  await expect(page.getByText('Puntuación de calidad')).toBeVisible();
  await shot(page, '08-calidad');

  // --- 5. Críticas, en modo oscuro para enseñar el tema alternativo ---
  await page.getByRole('tab', { name: 'Críticas' }).click();
  await page.getByRole('button', { name: /modo oscuro/i }).click();
  await expect(page.locator('html')).toHaveClass(/dark/);
  await expect(page.getByText(/prioriza los patrones repetidos/i)).toBeVisible();
  await shot(page, '10-criticas-oscuro');
  await page.getByRole('button', { name: /modo claro/i }).click();

  // --- 6. Comparador: necesita un segundo canal analizado ---
  await analizarDemo(page, 1);
  await page.goto('/comparador');
  const casillas = page.getByRole('checkbox');
  await casillas.nth(0).check();
  await casillas.nth(1).check();
  await page.getByRole('button', { name: 'Comparar' }).click();
  await expect(page.getByText('Mediana de visualizaciones')).toBeVisible();
  await shot(page, '11-comparador');

  // --- 7. Lista de canales, ya con dos análisis completados ---
  await page.goto('/canales');
  await expect(page.getByRole('link', { name: 'Ver análisis' }).first()).toBeVisible();
  await shot(page, '01-canales');

  // --- 8. Uso de API ---
  await page.goto('/uso-api');
  await expect(page.getByRole('heading', { name: 'Uso de la API de YouTube' })).toBeVisible();
  await shot(page, '12-uso-api');
});

test('genera la captura móvil', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/canales');
  await expect(page.getByRole('heading', { name: 'Canales' })).toBeVisible();
  await shot(page, '13-movil');
});

import { expect, test } from '@playwright/test';

/**
 * Flujo completo sobre datos de demostración.
 *
 * Cubre el criterio de aceptación «un canal ficticio puede analizarse sin
 * credenciales externas» de principio a fin: formulario, progreso, dashboard,
 * tabla de vídeos, calidad de datos y comparación entre dos canales.
 */

/** Espera a que un análisis en curso termine y muestre el dashboard. */
async function waitForDashboard(page: import('@playwright/test').Page): Promise<void> {
  await expect(page.getByRole('tab', { name: 'Resumen' })).toBeVisible({ timeout: 90_000 });
}

test.describe('Modo demostración', () => {
  test('analiza un canal ficticio y muestra el dashboard completo', async ({ page }) => {
    await page.goto('/demostracion');

    await expect(page.getByRole('heading', { name: 'Modo demostración' })).toBeVisible();
    await expect(page.getByText('Estos datos son ficticios')).toBeVisible();

    // Lanza el análisis del primer canal de demostración.
    await page.getByRole('button', { name: 'Analizar este canal' }).first().click();

    // Progreso visible mientras se ejecuta el pipeline.
    await expect(page).toHaveURL(/\/analisis\//);
    await waitForDashboard(page);

    // --- Resumen ---
    await expect(page.getByText('Datos de demostración').first()).toBeVisible();
    await expect(page.getByText('Comentarios analizados').first()).toBeVisible();
    await expect(page.getByText(/las asociaciones estadísticas no demuestran causalidad/i).first()).toBeVisible();

    // --- Temas ---
    await page.getByRole('tab', { name: 'Temas' }).click();
    await expect(page.getByRole('heading', { name: 'Temas detectados' })).toBeVisible();
    await expect(page.getByText(/Confianza (alta|media|baja)/).first()).toBeVisible();

    // --- Peticiones ---
    await page.getByRole('tab', { name: 'Peticiones' }).click();
    await expect(page.getByRole('tabpanel')).toBeVisible();

    // --- Fortalezas ---
    await page.getByRole('tab', { name: 'Fortalezas' }).click();
    await expect(page.getByRole('tabpanel')).toBeVisible();

    // --- Críticas ---
    await page.getByRole('tab', { name: 'Críticas' }).click();
    await expect(page.getByText(/prioriza los patrones repetidos y accionables/i)).toBeVisible();

    // --- Ideas de contenido ---
    await page.getByRole('tab', { name: 'Ideas de contenido' }).click();
    await expect(page.getByRole('heading', { name: 'Recomendaciones' })).toBeVisible();
    await expect(page.getByText('Evidencia').first()).toBeVisible();

    // --- Vídeos ---
    await page.getByRole('tab', { name: 'Vídeos' }).click();
    await expect(page.getByRole('heading', { name: 'Vídeos analizados' })).toBeVisible();
    await expect(page.getByRole('table')).toBeVisible();

    // --- Calidad de los datos ---
    await page.getByRole('tab', { name: 'Calidad de los datos' }).click();
    await expect(page.getByRole('heading', { name: 'Calidad de los datos' })).toBeVisible();
    await expect(page.getByText('Puntuación de calidad')).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Posibles sesgos de la muestra' })).toBeVisible();
  });

  test('compara dos canales de demostración', async ({ page }) => {
    // Analiza el segundo canal para tener dos con análisis completado.
    await page.goto('/demostracion');
    await page.getByRole('button', { name: 'Analizar este canal' }).nth(1).click();
    await waitForDashboard(page);

    await page.goto('/comparador');
    await expect(page.getByRole('heading', { name: 'Comparador de canales' })).toBeVisible();
    await expect(page.getByText(/no es una clasificación de calidad/i)).toBeVisible();

    const checkboxes = page.getByRole('checkbox');
    await checkboxes.nth(0).check();
    await checkboxes.nth(1).check();

    await page.getByRole('button', { name: 'Comparar' }).click();

    await expect(page.getByRole('table')).toBeVisible();
    await expect(page.getByText('Mediana de visualizaciones')).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Limitaciones de esta comparación' })).toBeVisible();
  });

  test('el formulario valida la referencia del canal antes de enviarla', async ({ page }) => {
    await page.goto('/nuevo-analisis');

    await page.getByLabel('Canal a analizar').fill('https://vimeo.com/algo');
    await page.getByRole('button', { name: 'Analizar' }).click();

    await expect(page.getByRole('alert').first()).toContainText(/formato/i);
    // No se ha navegado a ninguna página de análisis.
    await expect(page).toHaveURL(/\/nuevo-analisis/);
  });

  test('la lista de canales muestra los análisis guardados', async ({ page }) => {
    await page.goto('/canales');
    await expect(page.getByRole('heading', { name: 'Canales' })).toBeVisible();
    await expect(page.getByText('Datos de demostración').first()).toBeVisible();
    await expect(page.getByRole('link', { name: 'Ver análisis' }).first()).toBeVisible();
  });

  test('la pantalla de uso de API declara que es una estimación', async ({ page }) => {
    await page.goto('/uso-api');
    await expect(page.getByRole('heading', { name: 'Uso de la API de YouTube' })).toBeVisible();
    await expect(page.getByText('Esto es una estimación')).toBeVisible();
  });
});

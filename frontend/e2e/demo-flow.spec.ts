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
    // `exact` distingue la etiqueta de la métrica de la prosa que la explica.
    await expect(page.getByText('Puntuación de calidad', { exact: true })).toBeVisible();
    await expect(page.getByText('Confianza semántica', { exact: true })).toBeVisible();
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

test.describe('Responsive y accesibilidad', () => {
  test('la navegación funciona en móvil', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto('/canales');

    // En móvil el menú está plegado tras el botón de hamburguesa.
    const menuBtn = page.getByRole('button', { name: 'Abrir menú de navegación' });
    await expect(menuBtn).toBeVisible();
    await expect(menuBtn).toHaveAttribute('aria-expanded', 'false');

    await menuBtn.click();
    await expect(menuBtn).toHaveAttribute('aria-expanded', 'true');

    const menu = page.getByRole('navigation', { name: /móvil/i });
    await expect(menu.getByRole('link', { name: 'Modo demostración' })).toBeVisible();

    await menu.getByRole('link', { name: 'Modo demostración' }).click();
    await expect(page).toHaveURL(/\/demostracion/);
    await expect(page.getByRole('heading', { name: 'Modo demostración' })).toBeVisible();
  });

  test('la página no desborda horizontalmente en móvil', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto('/canales');
    await expect(page.getByRole('heading', { name: 'Canales' })).toBeVisible();

    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
    );
    expect(overflow).toBeLessThanOrEqual(1);
  });

  test('se puede navegar por las pestañas con el teclado', async ({ page }) => {
    await page.goto('/demostracion');
    await page.getByRole('button', { name: 'Analizar este canal' }).first().click();
    await expect(page.getByRole('tab', { name: 'Resumen' })).toBeVisible({ timeout: 90_000 });

    await page.getByRole('tab', { name: 'Resumen' }).focus();
    await page.keyboard.press('ArrowRight');
    await expect(page.getByRole('tab', { name: 'Temas' })).toHaveAttribute('aria-selected', 'true');

    await page.keyboard.press('ArrowLeft');
    await expect(page.getByRole('tab', { name: 'Resumen' })).toHaveAttribute(
      'aria-selected',
      'true',
    );
  });

  test('el modo oscuro se activa y persiste al navegar', async ({ page }) => {
    await page.goto('/canales');
    await page.getByRole('button', { name: /modo oscuro/i }).click();
    await expect(page.locator('html')).toHaveClass(/dark/);

    await page.goto('/uso-api');
    await expect(page.locator('html')).toHaveClass(/dark/);
  });
});

test.describe('Modo propietario', () => {
  test('está desactivado y no muestra ninguna métrica privada', async ({ page }) => {
    await page.goto('/modo-propietario');

    await expect(
      page.getByRole('heading', { name: 'Modo propietario', exact: true }),
    ).toBeVisible();
    await expect(page.getByText('Falta configuración')).toBeVisible();
    await expect(page.getByText('ENABLE_OWNER_MODE=true')).toBeVisible();

    // Con el modo apagado no hay botón de conexión ni canales conectados.
    await expect(page.getByRole('button', { name: /conectar con google/i })).toHaveCount(0);
    await expect(page.getByRole('button', { name: /ver métricas/i })).toHaveCount(0);

    // La página explica qué métricas aportaría, pero no renderiza ningún panel
    // de valores: «Periodo:» sólo aparece cuando hay datos reales de Analytics.
    await expect(page.getByText(/^Periodo:/)).toHaveCount(0);
  });

  test('declara que sólo pide permisos de lectura y no la contraseña', async ({ page }) => {
    await page.goto('/modo-propietario');

    await expect(page.getByText('Qué autorizas exactamente')).toBeVisible();
    await expect(page.getByText(/nunca se te pedirá tu contraseña/i)).toBeVisible();
    await expect(page.getByText(/yt-analytics\.readonly/)).toBeVisible();
    await expect(page.getByText(/youtube\.readonly/).first()).toBeVisible();
  });

  test('la API rechaza las métricas privadas con el modo apagado', async ({ request }) => {
    // La garantía real no es que falte un texto en la pantalla, sino que el
    // servidor no entregue datos de propietario cuando la función está apagada.
    const base = process.env.E2E_API_URL ?? 'http://localhost:8000';
    const status = await (await request.get(`${base}/api/oauth/status`)).json();
    expect(status.enabled).toBe(false);
    expect(status.ready).toBe(false);
    expect(status.connections).toEqual([]);

    const denied = await request.get(`${base}/api/oauth/analytics/${crypto.randomUUID()}`);
    expect(denied.status()).toBe(400);
    expect((await denied.json()).error.code).toBe('modo_propietario_desactivado');
  });
});

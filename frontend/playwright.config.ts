import { defineConfig, devices } from '@playwright/test';

/**
 * Configuración de las pruebas de extremo a extremo.
 *
 * Se asume que la API y el worker ya están en marcha (por ejemplo con
 * `docker compose up` o con `make dev`). Sólo el frontend se arranca aquí.
 */
const BASE_URL = process.env.E2E_BASE_URL ?? 'http://localhost:3000';

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  workers: 1,
  // El análisis completo tarda unos segundos: hay margen suficiente.
  timeout: 120_000,
  expect: { timeout: 20_000 },
  reporter: process.env.CI ? [['github'], ['html', { open: 'never' }]] : [['list']],
  use: {
    baseURL: BASE_URL,
    locale: 'es-ES',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        // Permite reutilizar un Chromium ya instalado en el sistema (útil en CI
        // o en contenedores donde no se pueden descargar navegadores).
        ...(process.env.PLAYWRIGHT_CHROMIUM_PATH
          ? { launchOptions: { executablePath: process.env.PLAYWRIGHT_CHROMIUM_PATH } }
          : {}),
      },
    },
  ],
  webServer: process.env.E2E_NO_SERVER
    ? undefined
    : {
        command: 'npm run start',
        url: BASE_URL,
        reuseExistingServer: true,
        timeout: 120_000,
      },
});

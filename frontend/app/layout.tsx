import type { Metadata } from 'next';

import { Nav } from '@/components/nav';
import { Providers } from '@/components/providers';

import './globals.css';

export const metadata: Metadata = {
  title: 'CreatorPulse AI',
  description:
    'Convierte los comentarios y las métricas públicas de tu canal de YouTube en decisiones de contenido con evidencia.',
  robots: { index: false, follow: false },
};

/** Aviso obligatorio, visible en todas las pantallas. */
const DISCLAIMER =
  'CreatorPulse AI ofrece análisis automatizados basados en una muestra de comentarios y ' +
  'métricas públicas. Las clasificaciones y recomendaciones pueden contener errores y no ' +
  'garantizan crecimiento. Las asociaciones estadísticas no demuestran causalidad.';

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es" suppressHydrationWarning>
      <body className="min-h-screen">
        <Providers>
          <a href="#contenido" className="skip-link">
            Saltar al contenido principal
          </a>
          <Nav />
          <main id="contenido" className="mx-auto max-w-7xl px-4 py-8">
            {children}
          </main>
          <footer className="border-t border-border bg-muted/30">
            <div className="mx-auto max-w-7xl space-y-3 px-4 py-6 text-xs text-muted-foreground">
              <p>{DISCLAIMER}</p>
              <p>
                Privacidad: sólo se analizan datos públicos de YouTube. Los identificadores de los
                autores de comentarios se almacenan con hash y no se guardan sus nombres ni sus
                fotos de perfil. Los comentarios públicos no se usan para entrenar modelos.
              </p>
            </div>
          </footer>
        </Providers>
      </body>
    </html>
  );
}

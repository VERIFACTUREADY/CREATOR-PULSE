import Link from 'next/link';

import { Card } from '@/components/ui';

const FEATURES = [
  {
    title: '¿Qué le gusta a tu audiencia?',
    body: 'Agrupa los elogios repetidos por aspecto (humor, claridad, edición…) y te dice en cuántos vídeos aparece cada uno.',
  },
  {
    title: '¿Qué te están pidiendo?',
    body: 'Detecta peticiones de tutoriales, segundas partes y productos, y cuenta cuántas veces se repiten.',
  },
  {
    title: '¿Qué deberías corregir?',
    body: 'Separa la crítica constructiva repetida del rechazo subjetivo y del acoso, y propone un experimento concreto.',
  },
  {
    title: '¿Cuánto puedes fiarte?',
    body: 'Cada conclusión lleva su evidencia numérica y un nivel de confianza que baja cuando la muestra es pequeña o viene de un solo vídeo.',
  },
];

export default function HomePage() {
  return (
    <div className="space-y-10">
      <section className="space-y-4">
        <h1 className="text-3xl font-bold sm:text-4xl">
          Convierte tus comentarios en decisiones de contenido
        </h1>
        <p className="max-w-3xl text-muted-foreground">
          Creator Signal AI analiza los comentarios y las métricas públicas de un canal de YouTube y
          los transforma en recomendaciones concretas: qué reforzar, qué corregir y qué publicar a
          continuación. Cada recomendación viene con las cifras que la respaldan.
        </p>
        <div className="flex flex-wrap gap-3">
          <Link
            href="/nuevo-analisis"
            className="rounded-md bg-primary px-5 py-2.5 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90"
          >
            Analizar un canal
          </Link>
          <Link
            href="/demostracion"
            className="rounded-md border border-border px-5 py-2.5 text-sm font-medium transition-colors hover:bg-muted"
          >
            Probar con datos de demostración
          </Link>
        </div>
      </section>

      <section aria-labelledby="que-responde">
        <h2 id="que-responde" className="mb-4 text-xl font-semibold">
          Preguntas que responde
        </h2>
        <div className="grid gap-4 sm:grid-cols-2">
          {FEATURES.map((feature) => (
            <Card key={feature.title} as="article">
              <h3 className="mb-2 font-semibold">{feature.title}</h3>
              <p className="text-sm text-muted-foreground">{feature.body}</p>
            </Card>
          ))}
        </div>
      </section>

      <section aria-labelledby="limitaciones">
        <h2 id="limitaciones" className="mb-4 text-xl font-semibold">
          Qué no hace
        </h2>
        <Card>
          <ul className="space-y-2 text-sm text-muted-foreground">
            <li>
              • No accede a tus datos privados de YouTube Analytics: sólo usa información pública.
              Nunca se te pedirá tu contraseña.
            </li>
            <li>
              • No garantiza crecimiento. Detecta patrones en una muestra de comentarios, que no es
              toda tu audiencia.
            </li>
            <li>
              • No afirma causas. Cuando un tema coincide con vídeos que rinden mejor, se presenta
              como una asociación a comprobar, no como una explicación.
            </li>
            <li>
              • No hace scraping de YouTube: sólo utiliza la API oficial de datos.
            </li>
          </ul>
        </Card>
      </section>
    </div>
  );
}

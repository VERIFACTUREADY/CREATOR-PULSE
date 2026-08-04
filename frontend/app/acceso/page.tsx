'use client';

import { useRouter, useSearchParams } from 'next/navigation';
import { Suspense, useState } from 'react';

import { Button, Callout, Card } from '@/components/ui';

/**
 * Pantalla de acceso a la beta privada.
 *
 * La contraseña se envía al servidor y se comprueba allí. Este componente
 * nunca la guarda: ni en estado persistente, ni en `localStorage`, ni en la
 * URL. Lo único que vuelve es una cookie firmada que el navegador no puede
 * leer (`HttpOnly`).
 */
function FormularioAcceso() {
  const router = useRouter();
  const parametros = useSearchParams();
  const destino = parametros.get('destino') ?? '/';

  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function entrar(evento: React.FormEvent) {
    evento.preventDefault();
    setEnviando(true);
    setError(null);

    try {
      const respuesta = await fetch('/api/acceso/entrar', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password }),
      });

      if (!respuesta.ok) {
        const cuerpo = (await respuesta.json().catch(() => null)) as {
          error?: { message?: string };
        } | null;
        setError(cuerpo?.error?.message ?? 'No se ha podido comprobar la contraseña.');
        return;
      }

      // Se limpia de memoria en cuanto deja de hacer falta.
      setPassword('');
      router.replace(destino);
      router.refresh();
    } catch {
      setError('No se ha podido contactar con el servidor.');
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="mx-auto flex min-h-[60vh] max-w-md items-center">
      <Card className="w-full">
        <h1 className="mb-2 text-xl font-semibold">Acceso a la beta</h1>
        <p className="mb-4 text-sm text-muted-foreground">
          CreatorPulse AI está en beta privada. Introduce la contraseña que te hayan facilitado.
        </p>

        <form onSubmit={entrar} className="space-y-3">
          <div>
            <label htmlFor="password" className="mb-1 block text-sm font-medium">
              Contraseña de la beta
            </label>
            <input
              id="password"
              name="password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(evento) => setPassword(evento.target.value)}
              required
              className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
            />
          </div>

          {error ? (
            <p role="alert" className="text-sm text-destructive">
              {error}
            </p>
          ) : null}

          <Button type="submit" disabled={enviando || password.length === 0}>
            {enviando ? 'Comprobando…' : 'Entrar'}
          </Button>
        </form>

        <div className="mt-4">
          <Callout tone="info" title="Por qué hay una contraseña">
          Esta instalación analiza canales reales y consume cuota de la API de YouTube. La
            contraseña evita que un visitante cualquiera lance análisis en tu nombre.
          </Callout>
        </div>
      </Card>
    </div>
  );
}

export default function PaginaAcceso() {
  return (
    <Suspense fallback={<p className="p-8 text-sm text-muted-foreground">Cargando…</p>}>
      <FormularioAcceso />
    </Suspense>
  );
}

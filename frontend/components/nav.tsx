'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useState } from 'react';

import { ThemeToggle } from '@/components/theme-toggle';
import { cn } from '@/lib/format';

const LINKS = [
  { href: '/canales', label: 'Canales' },
  { href: '/nuevo-analisis', label: 'Nuevo análisis' },
  { href: '/comparador', label: 'Comparador' },
  { href: '/uso-api', label: 'Uso de API' },
  { href: '/modo-propietario', label: 'Modo propietario' },
  { href: '/configuracion', label: 'Configuración' },
  { href: '/demostracion', label: 'Modo demostración' },
] as const;

export function Nav() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);

  const isActive = (href: string) => pathname === href || pathname.startsWith(`${href}/`);

  return (
    <header className="sticky top-0 z-40 border-b border-border bg-background/95 backdrop-blur">
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-3">
        <Link href="/" className="flex items-center gap-2 font-semibold">
          <span
            aria-hidden="true"
            className="flex h-8 w-8 items-center justify-center rounded-md bg-primary text-primary-foreground"
          >
            CS
          </span>
          <span className="hidden sm:inline">Creator Signal AI</span>
        </Link>

        <nav aria-label="Navegación principal" className="hidden md:block">
          <ul className="flex items-center gap-1">
            {LINKS.map((link) => (
              <li key={link.href}>
                <Link
                  href={link.href}
                  aria-current={isActive(link.href) ? 'page' : undefined}
                  className={cn(
                    'rounded-md px-3 py-2 text-sm transition-colors',
                    isActive(link.href)
                      ? 'bg-secondary font-medium text-secondary-foreground'
                      : 'text-muted-foreground hover:bg-muted hover:text-foreground',
                  )}
                >
                  {link.label}
                </Link>
              </li>
            ))}
          </ul>
        </nav>

        <div className="flex items-center gap-2">
          <ThemeToggle />
          <button
            type="button"
            onClick={() => setOpen((value) => !value)}
            aria-expanded={open}
            aria-controls="menu-movil"
            aria-label="Abrir menú de navegación"
            className="rounded-md border border-border px-3 py-1.5 text-sm md:hidden"
          >
            <span aria-hidden="true">☰</span>
          </button>
        </div>
      </div>

      {open ? (
        <nav id="menu-movil" aria-label="Navegación principal (móvil)" className="border-t border-border md:hidden">
          <ul className="mx-auto max-w-7xl px-4 py-2">
            {LINKS.map((link) => (
              <li key={link.href}>
                <Link
                  href={link.href}
                  onClick={() => setOpen(false)}
                  aria-current={isActive(link.href) ? 'page' : undefined}
                  className={cn(
                    'block rounded-md px-3 py-2 text-sm',
                    isActive(link.href)
                      ? 'bg-secondary font-medium'
                      : 'text-muted-foreground hover:bg-muted',
                  )}
                >
                  {link.label}
                </Link>
              </li>
            ))}
          </ul>
        </nav>
      ) : null}
    </header>
  );
}

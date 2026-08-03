'use client';

import { useEffect, useState } from 'react';

type Theme = 'light' | 'dark';

const STORAGE_KEY = 'creator-signal-theme';

function applyTheme(theme: Theme): void {
  document.documentElement.classList.toggle('dark', theme === 'dark');
}

export function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>('light');
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    const stored = window.localStorage.getItem(STORAGE_KEY) as Theme | null;
    const preferred: Theme =
      stored ?? (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
    setTheme(preferred);
    applyTheme(preferred);
    setMounted(true);
  }, []);

  const toggle = () => {
    const next: Theme = theme === 'dark' ? 'light' : 'dark';
    setTheme(next);
    applyTheme(next);
    window.localStorage.setItem(STORAGE_KEY, next);
  };

  return (
    <button
      type="button"
      onClick={toggle}
      aria-label={mounted && theme === 'dark' ? 'Cambiar a modo claro' : 'Cambiar a modo oscuro'}
      className="rounded-md border border-border px-3 py-1.5 text-sm transition-colors hover:bg-muted"
    >
      <span aria-hidden="true">{mounted && theme === 'dark' ? '☀' : '☾'}</span>
      <span className="sr-only">Cambiar tema</span>
    </button>
  );
}

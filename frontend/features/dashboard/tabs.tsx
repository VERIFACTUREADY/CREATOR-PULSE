'use client';

import { useState } from 'react';

import { cn } from '@/lib/format';

export const DASHBOARD_TABS = [
  { id: 'resumen', label: 'Resumen' },
  { id: 'temas', label: 'Temas' },
  { id: 'peticiones', label: 'Peticiones' },
  { id: 'fortalezas', label: 'Fortalezas' },
  { id: 'criticas', label: 'Críticas' },
  { id: 'ideas', label: 'Ideas de contenido' },
  { id: 'videos', label: 'Vídeos' },
  { id: 'calidad', label: 'Calidad de los datos' },
] as const;

export type TabId = (typeof DASHBOARD_TABS)[number]['id'];

export function useTabs(initial: TabId = 'resumen') {
  return useState<TabId>(initial);
}

export function TabBar({
  active,
  onChange,
}: {
  active: TabId;
  onChange: (tab: TabId) => void;
}) {
  return (
    <div role="tablist" aria-label="Secciones del análisis" className="flex gap-1 overflow-x-auto border-b border-border pb-px">
      {DASHBOARD_TABS.map((tab) => (
        <button
          key={tab.id}
          role="tab"
          id={`tab-${tab.id}`}
          aria-selected={active === tab.id}
          aria-controls={`panel-${tab.id}`}
          tabIndex={active === tab.id ? 0 : -1}
          onClick={() => onChange(tab.id)}
          onKeyDown={(event) => {
            const index = DASHBOARD_TABS.findIndex((item) => item.id === active);
            if (event.key === 'ArrowRight') {
              const next = DASHBOARD_TABS[(index + 1) % DASHBOARD_TABS.length];
              if (next) onChange(next.id);
            }
            if (event.key === 'ArrowLeft') {
              const previous =
                DASHBOARD_TABS[(index - 1 + DASHBOARD_TABS.length) % DASHBOARD_TABS.length];
              if (previous) onChange(previous.id);
            }
          }}
          className={cn(
            'whitespace-nowrap rounded-t-md border-b-2 px-4 py-2.5 text-sm transition-colors',
            active === tab.id
              ? 'border-primary font-medium text-foreground'
              : 'border-transparent text-muted-foreground hover:text-foreground',
          )}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}

export function TabPanel({
  id,
  active,
  children,
}: {
  id: TabId;
  active: TabId;
  children: React.ReactNode;
}) {
  if (id !== active) return null;
  return (
    <div
      role="tabpanel"
      id={`panel-${id}`}
      aria-labelledby={`tab-${id}`}
      tabIndex={0}
      className="animate-fade-in pt-6"
    >
      {children}
    </div>
  );
}

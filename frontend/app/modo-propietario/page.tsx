'use client';

import { Suspense } from 'react';

import { LoadingState } from '@/components/ui';
import { OwnerMode } from '@/features/owner-mode';

export default function OwnerModePage() {
  // `useSearchParams` obliga a envolver en Suspense durante el prerenderizado.
  return (
    <Suspense fallback={<LoadingState label="Cargando el modo propietario" />}>
      <OwnerMode />
    </Suspense>
  );
}

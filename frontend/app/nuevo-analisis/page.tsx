import { AnalysisForm } from '@/features/analysis-form';
import { SectionTitle } from '@/components/ui';

export const metadata = { title: 'Nuevo análisis · CreatorPulse AI' };

export default function NewAnalysisPage() {
  return (
    <div className="mx-auto max-w-3xl">
      <SectionTitle
        title="Nuevo análisis"
        description="Analiza un canal público de YouTube. Aumentar el número de vídeos y comentarios alarga el análisis, consume más cuota de la API y, si tienes activada la IA externa, aumenta su coste."
      />
      <AnalysisForm />
    </div>
  );
}

import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import { CriticismTab, RequestsTab, StrengthsTab } from '@/features/dashboard/feedback';
import { IdeasTab } from '@/features/dashboard/ideas';
import { OverviewTab } from '@/features/dashboard/overview';
import { QualityTab } from '@/features/dashboard/quality';
import { TopicsTab } from '@/features/dashboard/topics';
import { VideosTab } from '@/features/dashboard/videos';

import {
  audioTopic,
  criticism,
  dataQuality,
  idea,
  recommendation,
  requests,
  strengths,
  summary,
  topic,
  videos,
  viralTopic,
} from './fixtures';

// --- Resumen ----------------------------------------------------------------

describe('Pestaña Resumen', () => {
  it('muestra las métricas clave del análisis', () => {
    render(<OverviewTab summary={summary} />);
    expect(screen.getByText('Vídeos analizados')).toBeInTheDocument();
    expect(screen.getByText('12')).toBeInTheDocument();
    expect(screen.getByText('Comentarios analizados')).toBeInTheDocument();
  });

  it('muestra la fortaleza, la petición y la crítica principales', () => {
    render(<OverviewTab summary={summary} />);
    expect(screen.getByText('Fortaleza principal')).toBeInTheDocument();
    expect(screen.getByText('Petición principal')).toBeInTheDocument();
    expect(screen.getByText('Crítica más repetida')).toBeInTheDocument();
  });

  it('muestra el aviso de calidad de datos cuando existe', () => {
    render(<OverviewTab summary={summary} />);
    expect(screen.getByText(/comentarios desactivados/i)).toBeInTheDocument();
  });

  it('muestra un estado vacío cuando no hay comentarios', () => {
    render(<OverviewTab summary={{ ...summary, comments_analysed: 0 }} />);
    expect(screen.getByText('No hay comentarios que analizar')).toBeInTheDocument();
  });

  it('indica cuándo no hay señales suficientes', () => {
    render(
      <OverviewTab
        summary={{ ...summary, top_strength: null, top_request: null, top_criticism: null }}
      />,
    );
    expect(screen.getByText(/no hay todavía un patrón de elogios/i)).toBeInTheDocument();
    expect(screen.getByText(/no se han detectado peticiones repetidas/i)).toBeInTheDocument();
  });
});

// --- Temas ------------------------------------------------------------------

describe('Pestaña Temas', () => {
  it('muestra los temas con su confianza y su tendencia', () => {
    render(<TopicsTab topics={[topic, audioTopic]} />);
    expect(screen.getByText('Humor')).toBeInTheDocument();
    expect(screen.getByText('Audio')).toBeInTheDocument();
    expect(screen.getByText('Confianza alta')).toBeInTheDocument();
    // «Al alza» aparece también como chip de filtro, así que hay más de uno.
    expect(screen.getAllByText('Al alza').length).toBeGreaterThan(0);
  });

  it('permite ordenar los temas', async () => {
    const user = userEvent.setup();
    render(<TopicsTab topics={[audioTopic, topic]} />);

    const select = screen.getByLabelText('Ordenar por');
    await user.selectOptions(select, 'unique_video_count');

    const headings = screen.getAllByRole('heading', { level: 3 });
    expect(headings[0]).toHaveTextContent('Humor');
  });

  it('permite filtrar los temas críticos', async () => {
    const user = userEvent.setup();
    render(<TopicsTab topics={[topic, audioTopic]} />);

    await user.click(screen.getByRole('button', { name: 'Críticos' }));

    expect(screen.getByText('Audio')).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'Humor' })).not.toBeInTheDocument();
  });

  it('avisa cuando un tema procede mayoritariamente de un solo vídeo', () => {
    render(<TopicsTab topics={[viralTopic]} />);
    expect(screen.getByText(/vienen de un solo vídeo/i)).toBeInTheDocument();
  });

  it('permite desplegar los comentarios de ejemplo', async () => {
    const user = userEvent.setup();
    render(<TopicsTab topics={[topic]} />);

    expect(screen.queryByText(/Me río muchísimo con tus vídeos/)).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /comentarios de ejemplo/i }));
    expect(screen.getByText(/Me río muchísimo con tus vídeos/)).toBeInTheDocument();
  });

  it('muestra un estado vacío sin temas', () => {
    render(<TopicsTab topics={[]} />);
    expect(screen.getByText('No se han detectado temas')).toBeInTheDocument();
  });
});

// --- Peticiones, fortalezas y críticas --------------------------------------

describe('Pestaña Peticiones', () => {
  it('muestra las peticiones con su número de vídeos', () => {
    render(<RequestsTab requests={requests} />);
    expect(screen.getByText('Peticiones de tutorial')).toBeInTheDocument();
    expect(screen.getByText(/5/)).toBeInTheDocument();
  });

  it('explica el estado vacío sin ocultar el criterio', () => {
    render(<RequestsTab requests={[]} />);
    expect(screen.getByText('No hay peticiones repetidas')).toBeInTheDocument();
    expect(screen.getByText(/una petición aislada no aparece aquí/i)).toBeInTheDocument();
  });
});

describe('Pestaña Fortalezas', () => {
  it('agrupa el feedback positivo por aspecto', () => {
    render(<StrengthsTab strengths={strengths} />);
    expect(screen.getByRole('heading', { name: 'Humor' })).toBeInTheDocument();
    expect(screen.getByText('Confianza alta')).toBeInTheDocument();
  });

  it('muestra un estado vacío sin fortalezas', () => {
    render(<StrengthsTab strengths={[]} />);
    expect(screen.getByText('Todavía no hay fortalezas claras')).toBeInTheDocument();
  });
});

describe('Pestaña Críticas', () => {
  it('muestra el aviso sobre patrones repetidos', () => {
    render(<CriticismTab criticism={criticism} />);
    expect(screen.getByText(/prioriza los patrones repetidos y accionables/i)).toBeInTheDocument();
  });

  it('separa los cuatro tipos de crítica', () => {
    render(<CriticismTab criticism={criticism} />);
    expect(screen.getByRole('heading', { name: 'Crítica constructiva' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'No gusta (subjetivo)' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Acoso o insultos' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Posible spam' })).toBeInTheDocument();
  });

  it('marca la crítica constructiva repetida como accionable', () => {
    render(<CriticismTab criticism={criticism} />);
    expect(screen.getByText('Patrón accionable')).toBeInTheDocument();
  });

  it('aclara que el acoso no alimenta las recomendaciones', () => {
    render(<CriticismTab criticism={criticism} />);
    expect(
      screen.getByText(/ninguna recomendación de contenido de este informe se basa en ellos/i),
    ).toBeInTheDocument();
  });
});

// --- Ideas ------------------------------------------------------------------

describe('Pestaña Ideas de contenido', () => {
  it('muestra la recomendación con su evidencia y su confianza', () => {
    render(<IdeasTab recommendations={[recommendation]} ideas={[idea]} />);
    expect(screen.getByText(recommendation.title_es)).toBeInTheDocument();
    expect(screen.getByText(/40 comentarios respaldan esta conclusión/)).toBeInTheDocument();
    expect(screen.getAllByText('Confianza alta').length).toBeGreaterThan(0);
  });

  it('muestra siempre la advertencia de la recomendación', () => {
    render(<IdeasTab recommendations={[recommendation]} ideas={[]} />);
    expect(screen.getByText('Advertencia')).toBeInTheDocument();
    expect(screen.getByText(/no una garantía de resultados/i)).toBeInTheDocument();
  });

  it('muestra el riesgo de sobreinterpretación de cada idea', () => {
    render(<IdeasTab recommendations={[]} ideas={[idea]} />);
    expect(screen.getByText('Riesgo de sobreinterpretar los datos')).toBeInTheDocument();
    expect(screen.getByText(idea.overinterpretation_risk_es)).toBeInTheDocument();
  });

  it('muestra el gancho, el formato, el experimento y el KPI', () => {
    render(<IdeasTab recommendations={[]} ideas={[idea]} />);
    expect(screen.getByText('Gancho')).toBeInTheDocument();
    expect(screen.getByText('Experimento')).toBeInTheDocument();
    expect(screen.getByText('Métrica principal')).toBeInTheDocument();
    expect(screen.getByText('Short')).toBeInTheDocument();
  });

  it('muestra un estado vacío sin recomendaciones ni ideas', () => {
    render(<IdeasTab recommendations={[]} ideas={[]} />);
    expect(screen.getByText('No hay suficientes datos para recomendar nada')).toBeInTheDocument();
  });
});

// --- Vídeos -----------------------------------------------------------------

describe('Pestaña Vídeos', () => {
  it('muestra la tabla con enlace público a YouTube', () => {
    render(<VideosTab videos={videos} />);
    const link = screen.getByRole('link', { name: 'Vídeo antiguo con buen rendimiento' });
    expect(link).toHaveAttribute('href', 'https://www.youtube.com/watch?v=aaaaaaaaaaa');
    expect(link).toHaveAttribute('rel', expect.stringContaining('noopener'));
  });

  it('marca los vídeos demasiado recientes para comparar', () => {
    render(<VideosTab videos={videos} />);
    expect(screen.getByText('Demasiado reciente para comparar')).toBeInTheDocument();
  });

  it('indica los vídeos con comentarios desactivados', () => {
    render(<VideosTab videos={videos} />);
    expect(screen.getAllByText(/comentarios desactivados/i).length).toBeGreaterThan(0);
  });

  it('permite ordenar por visualizaciones', async () => {
    const user = userEvent.setup();
    render(<VideosTab videos={videos} />);

    await user.click(screen.getByRole('button', { name: /Visualizaciones/ }));

    const rows = screen.getAllByRole('row').slice(1);
    const firstRow = rows[0];
    expect(firstRow).toBeDefined();
    expect(within(firstRow!).getByRole('link')).toHaveTextContent(
      'Vídeo antiguo con buen rendimiento',
    );
  });

  it('muestra un guion cuando una métrica no está disponible', () => {
    render(<VideosTab videos={videos} />);
    // El vídeo con comentarios desactivados no tiene comentarios por 1.000.
    expect(screen.getAllByText('—').length).toBeGreaterThan(0);
  });

  it('muestra un estado vacío sin vídeos', () => {
    render(<VideosTab videos={[]} />);
    expect(screen.getByText('No hay vídeos analizados')).toBeInTheDocument();
  });
});

// --- Calidad de los datos ---------------------------------------------------

describe('Pestaña Calidad de los datos', () => {
  it('muestra la puntuación y los avisos', () => {
    render(<QualityTab quality={dataQuality} />);
    expect(screen.getByText('82 / 100')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Avisos' })).toBeInTheDocument();
  });

  it('enumera los sesgos de la muestra', () => {
    render(<QualityTab quality={dataQuality} />);
    expect(screen.getByRole('heading', { name: 'Posibles sesgos de la muestra' })).toBeInTheDocument();
    expect(screen.getByText(/procede de un solo vídeo/i)).toBeInTheDocument();
  });

  it('etiqueta claramente los datos de demostración', () => {
    render(<QualityTab quality={dataQuality} />);
    expect(screen.getByText('Datos de demostración')).toBeInTheDocument();
    expect(screen.getByText(/no corresponden a ningún canal ni persona real/i)).toBeInTheDocument();
  });

  it('explica la estrategia de muestreo y el algoritmo usado', () => {
    render(<QualityTab quality={dataQuality} />);
    expect(screen.getByText('Mixta (recientes + relevantes)')).toBeInTheDocument();
    expect(screen.getByText(/HDBSCAN/)).toBeInTheDocument();
  });

  it('declara si se ha usado IA externa', () => {
    render(<QualityTab quality={dataQuality} />);
    expect(screen.getByText(/todo el informe procede del motor determinista/i)).toBeInTheDocument();
  });

  it('muestra la distribución de idiomas', () => {
    render(<QualityTab quality={dataQuality} />);
    expect(screen.getByRole('heading', { name: 'Distribución de idiomas' })).toBeInTheDocument();
    expect(screen.getByText(/ES: 320/)).toBeInTheDocument();
  });
});

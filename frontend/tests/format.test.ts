import { describe, expect, it } from 'vitest';

import {
  formatCompact,
  formatDecimal,
  formatDuration,
  formatNumber,
  formatPercent,
  formatSubscribers,
  pluralize,
  subscribersLabel,
} from '@/lib/format';

describe('Formato de números', () => {
  it('usa separadores españoles', () => {
    expect(formatNumber(12345)).toBe('12.345');
    expect(formatDecimal(4.25, 2)).toBe('4,25');
  });

  it('devuelve un guion cuando el dato no está disponible', () => {
    expect(formatNumber(null)).toBe('—');
    expect(formatCompact(undefined)).toBe('—');
    expect(formatPercent(null)).toBe('—');
    expect(formatDecimal(null)).toBe('—');
  });

  it('formatea porcentajes', () => {
    expect(formatPercent(0.234)).toBe('23 %');
    expect(formatPercent(0.234, 1)).toBe('23,4 %');
  });

  it('formatea duraciones', () => {
    expect(formatDuration(630)).toBe('10:30');
    expect(formatDuration(3723)).toBe('1:02:03');
    expect(formatDuration(45)).toBe('0:45');
    expect(formatDuration(null)).toBe('—');
  });
});

describe('Etiqueta de suscriptores', () => {
  it('devuelve la frase completa cuando hay dato', () => {
    expect(subscribersLabel(84_300, false)).toMatch(/suscriptores$/);
  });

  it('es gramatical cuando el canal los oculta', () => {
    // «Ocultos suscriptores» no es español: la frase debe construirse entera.
    expect(subscribersLabel(null, true)).toBe('suscriptores ocultos');
  });

  it('distingue oculto de no disponible', () => {
    expect(subscribersLabel(null, false)).toBe('suscriptores no disponibles');
  });

  it('mantiene el valor suelto para las celdas de tabla', () => {
    expect(formatSubscribers(null, true)).toBe('Ocultos');
    expect(formatSubscribers(null, false)).toBe('—');
  });
});

describe('Pluralización', () => {
  it('elige la forma correcta', () => {
    expect(pluralize(1, 'vídeo', 'vídeos')).toBe('vídeo');
    expect(pluralize(2, 'vídeo', 'vídeos')).toBe('vídeos');
    expect(pluralize(0, 'vídeo', 'vídeos')).toBe('vídeos');
  });
});

import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import {
  COOKIE_SESION,
  crearSesion,
  estadoBeta,
  identidadDeSesion,
  passwordCorrecta,
  sesionValida,
  ttlHoras,
} from '@/lib/beta-session';

/**
 * La puerta de la beta es lo único que separa un despliegue público de que
 * cualquiera gaste tu cuota de YouTube. El secreto compartido con la API
 * autentica al servicio, nunca a la persona.
 */

const ORIGINAL = { ...process.env };

beforeEach(() => {
  process.env.BETA_ACCESS_ENABLED = 'true';
  process.env.BETA_ACCESS_PASSWORD = 'contrasena-de-la-beta';
  process.env.BETA_SESSION_SECRET = 'un-secreto-de-firma-suficientemente-largo';
  delete process.env.BETA_SESSION_TTL_HOURS;
});

afterEach(() => {
  process.env = { ...ORIGINAL };
});

describe('estado de la puerta', () => {
  it('desactivada por defecto', async () => {
    process.env.BETA_ACCESS_ENABLED = 'false';
    expect(estadoBeta()).toEqual({ activa: false, malConfigurada: false });
  });

  it('activada pero sin contraseña se considera mal configurada, no abierta', async () => {
    process.env.BETA_ACCESS_PASSWORD = '';
    expect(estadoBeta()).toEqual({ activa: false, malConfigurada: true });
  });

  it('activada con un secreto de firma demasiado corto tampoco vale', async () => {
    process.env.BETA_SESSION_SECRET = 'corto';
    expect(estadoBeta().malConfigurada).toBe(true);
  });

  it('activada y completa', async () => {
    expect(estadoBeta()).toEqual({ activa: true, malConfigurada: false });
  });
});

describe('contraseña', () => {
  it('acepta la correcta', async () => {
    expect(await passwordCorrecta('contrasena-de-la-beta')).toBe(true);
  });

  it('rechaza una incorrecta de la misma longitud', async () => {
    expect(await passwordCorrecta('contrasena-de-la-bets')).toBe(false);
  });

  it('rechaza una de longitud distinta sin lanzar', async () => {
    expect(await passwordCorrecta('corta')).toBe(false);
    expect(await passwordCorrecta('')).toBe(false);
  });

  it('sin contraseña configurada no entra nadie', async () => {
    process.env.BETA_ACCESS_PASSWORD = '';
    expect(await passwordCorrecta('')).toBe(false);
    expect(await passwordCorrecta('lo-que-sea')).toBe(false);
  });
});

describe('cookie de sesión', () => {
  it('una sesión recién creada es válida', async () => {
    const { valor } = await crearSesion();
    expect(await sesionValida(valor)).toBe(true);
  });

  it('una cookie manipulada no cuela', async () => {
    const { valor } = await crearSesion();
    const [payload] = valor.split('.');
    expect(await sesionValida(`${payload}.firmainventada`)).toBe(false);
  });

  it('cambiar la caducidad invalida la firma', async () => {
    const { valor } = await crearSesion();
    const firma = valor.slice(valor.lastIndexOf('.') + 1);
    const futuro = Date.now() + 999_999_999;
    expect(await sesionValida(`${futuro}.${firma}`)).toBe(false);
  });

  it('una sesión caducada deja de valer', async () => {
    const { valor } = await crearSesion(Date.now() - 48 * 3600_000);
    expect(await sesionValida(valor)).toBe(false);
  });

  it('sin cookie no hay sesión', async () => {
    expect(await sesionValida(undefined)).toBe(false);
    expect(await sesionValida('')).toBe(false);
    expect(await sesionValida('sinpunto')).toBe(false);
  });

  it('una firma de otro secreto no vale', async () => {
    const { valor } = await crearSesion();
    process.env.BETA_SESSION_SECRET = 'otro-secreto-completamente-distinto-x';
    expect(await sesionValida(valor)).toBe(false);
  });

  it('la duración se puede configurar dentro de un rango sensato', async () => {
    process.env.BETA_SESSION_TTL_HOURS = '3';
    expect(ttlHoras()).toBe(3);
    process.env.BETA_SESSION_TTL_HOURS = '-5';
    expect(ttlHoras()).toBe(12);
    process.env.BETA_SESSION_TTL_HOURS = 'muchas';
    expect(ttlHoras()).toBe(12);
  });
});

describe('identidad para el rate limit', () => {
  it('es estable para una misma sesión', async () => {
    const { valor } = await crearSesion();
    expect(await identidadDeSesion(valor)).toBe(await identidadDeSesion(valor));
  });

  it('cambia entre sesiones distintas', async () => {
    const a = await crearSesion(Date.now());
    const b = await crearSesion(Date.now() + 1000);
    expect(await identidadDeSesion(a.valor)).not.toBe(await identidadDeSesion(b.valor));
  });

  it('sin sesión válida no hay identidad', async () => {
    expect(await identidadDeSesion('inventada.firma')).toBeNull();
    expect(await identidadDeSesion(undefined)).toBeNull();
  });

  it('no revela la cookie ni el secreto', async () => {
    const { valor } = await crearSesion();
    const identidad = await identidadDeSesion(valor);
    expect(identidad).not.toBeNull();
    expect(valor).not.toContain(identidad as string);
    expect(identidad).not.toContain(process.env.BETA_SESSION_SECRET as string);
  });

  it('tiene una longitud acotada, para no inflar el diccionario del servidor', async () => {
    const { valor } = await crearSesion();
    expect(((await identidadDeSesion(valor)) as string).length).toBeLessThanOrEqual(32);
  });
});

describe('nombre de la cookie', () => {
  it('no sugiere que contenga la contraseña', async () => {
    expect(COOKIE_SESION).not.toMatch(/password|secret|clave/i);
  });
});

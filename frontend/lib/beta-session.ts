/**
 * Sesión de la beta privada.
 *
 * Son **dos capas distintas** y conviene no confundirlas:
 *
 * * **usuario → frontend**: esta sesión. Un visitante sin ella no puede usar
 *   la aplicación ni sus rutas `/api/*`.
 * * **frontend → API**: el secreto de servicio que añade el proxy. Autentica
 *   al servicio, no a la persona.
 *
 * El secreto compartido con la API nunca ha sido autenticación de usuarios: el
 * frontend es público y el proxy añadiría la cabecera por cualquiera. Esto es
 * lo que faltaba.
 *
 * Se usa **Web Crypto** y no `node:crypto` porque el middleware se ejecuta en
 * el runtime edge, donde los módulos de Node no existen. Por eso las funciones
 * son asíncronas.
 *
 * Todo vive en el servidor. Ninguna variable lleva prefijo `NEXT_PUBLIC_`.
 */

export const COOKIE_SESION = 'creatorpulse_beta';

/** Duración por defecto si no se configura otra cosa. */
const HORAS_POR_DEFECTO = 12;

export interface EstadoBeta {
  /** La puerta está activada y correctamente configurada. */
  activa: boolean;
  /** Está activada pero le falta configuración: hay que fallar, no abrir. */
  malConfigurada: boolean;
}

function leerSecreto(): string {
  return process.env.BETA_SESSION_SECRET?.trim() ?? '';
}

function leerPassword(): string {
  return process.env.BETA_ACCESS_PASSWORD?.trim() ?? '';
}

export function ttlHoras(): number {
  const bruto = Number.parseInt(process.env.BETA_SESSION_TTL_HOURS ?? '', 10);
  if (!Number.isFinite(bruto) || bruto <= 0 || bruto > 24 * 30) return HORAS_POR_DEFECTO;
  return bruto;
}

export function estadoBeta(): EstadoBeta {
  const activada = process.env.BETA_ACCESS_ENABLED === 'true';
  if (!activada) return { activa: false, malConfigurada: false };
  const completa = leerPassword().length > 0 && leerSecreto().length >= 16;
  // Activada pero incompleta no puede significar «pasa»: significa error.
  return { activa: completa, malConfigurada: !completa };
}

const codificador = new TextEncoder();

function base64url(bytes: ArrayBuffer): string {
  let binario = '';
  for (const byte of new Uint8Array(bytes)) binario += String.fromCharCode(byte);
  return btoa(binario).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

async function clave(secreto: string): Promise<CryptoKey> {
  return crypto.subtle.importKey(
    'raw',
    codificador.encode(secreto),
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign'],
  );
}

async function firmar(payload: string, secreto = leerSecreto()): Promise<string> {
  const firma = await crypto.subtle.sign('HMAC', await clave(secreto), codificador.encode(payload));
  return base64url(firma);
}

/**
 * Compara dos cadenas sin filtrar por tiempo cuánto coinciden.
 *
 * Web Crypto no tiene `timingSafeEqual`, así que se comparan los HMAC de
 * ambas con una clave efímera: dos digests del mismo tamaño, y una diferencia
 * en cualquier posición cambia el resultado entero.
 */
async function igualesEnTiempoConstante(a: string, b: string): Promise<boolean> {
  const efimera = crypto.getRandomValues(new Uint8Array(32));
  const material = await crypto.subtle.importKey(
    'raw',
    efimera,
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign'],
  );
  const [ha, hb] = await Promise.all([
    crypto.subtle.sign('HMAC', material, codificador.encode(a)),
    crypto.subtle.sign('HMAC', material, codificador.encode(b)),
  ]);
  const va = new Uint8Array(ha);
  const vb = new Uint8Array(hb);
  let diferencia = 0;
  for (let i = 0; i < va.length; i += 1) diferencia |= (va[i] ?? 0) ^ (vb[i] ?? 0);
  return diferencia === 0;
}

/** Genera el valor de la cookie: `caducidad.firma`. */
export async function crearSesion(ahora = Date.now()): Promise<{ valor: string; expira: Date }> {
  const expira = new Date(ahora + ttlHoras() * 3600_000);
  const payload = String(expira.getTime());
  return { valor: `${payload}.${await firmar(payload)}`, expira };
}

/**
 * Comprueba una cookie de sesión.
 *
 * La caducidad se verifica **después** de validar la firma: al revés, un
 * atacante podría distinguir cookies válidas caducadas de cookies inventadas.
 */
export async function sesionValida(cookie: string | undefined, ahora = Date.now()): Promise<boolean> {
  if (!cookie) return false;
  const separador = cookie.lastIndexOf('.');
  if (separador <= 0) return false;

  const payload = cookie.slice(0, separador);
  const firma = cookie.slice(separador + 1);
  if (!(await igualesEnTiempoConstante(firma, await firmar(payload)))) return false;

  const caduca = Number.parseInt(payload, 10);
  return Number.isFinite(caduca) && caduca > ahora;
}

/** Comprueba la contraseña de la beta en tiempo constante. */
export async function passwordCorrecta(candidata: string): Promise<boolean> {
  const esperada = leerPassword();
  if (!esperada) return false;
  return igualesEnTiempoConstante(candidata, esperada);
}

/**
 * Identidad estable y **no elegible por el cliente** para el rate limit.
 *
 * Es el HMAC de la propia cookie de sesión: el visitante no puede escoger su
 * valor, porque no sabe firmar. Se recorta para acotar la longitud de la clave.
 */
export async function identidadDeSesion(cookie: string | undefined): Promise<string | null> {
  if (!(await sesionValida(cookie))) return null;
  return (await firmar(`identidad:${cookie}`)).slice(0, 32);
}

import { createPublicKey, verify, type KeyObject } from 'node:crypto';
import { readFileSync } from 'node:fs';
import type { IncomingHttpHeaders } from 'node:http';

/**
 * despliegue/acceso_cf.py en TypeScript: el sello de Cloudflare Access (JWT RS256 del equipo de RO). Se comprueban la
 * firma (claves de https://<equipo>.cloudflareaccess.com/cdn-cgi/access/certs, 1 h en memoria y recargadas si llega un
 * «kid» nuevo, como mucho una vez por minuto), la audiencia, el emisor, la caducidad y el «no antes de» (60 s de
 * margen), y que lleva correo. Mismos textos y mismo orden de comprobación que el Python.
 * Variables: RO_CF_EQUIPO · RO_CF_AUD · RO_CF_CERTS_FICHERO (pruebas: JWKS en disco en vez de pedirlo).
 */
const MARGEN_S = 60;
const RECARGA_MIN_S = 60;

let claves = new Map<string, KeyObject>();
let hasta = 0;
let ultimaForzada = 0;

const ahoraS = () => Date.now() / 1000;
const emisor = () => `https://${process.env.RO_CF_EQUIPO ?? ''}.cloudflareaccess.com`;

/** Solo para las pruebas: olvida las claves guardadas. */
export function olvidarClaves(): void {
  claves = new Map();
  hasta = 0;
  ultimaForzada = 0;
}

async function leerJwks(): Promise<{ keys?: Record<string, unknown>[] }> {
  const fichero = process.env.RO_CF_CERTS_FICHERO;
  if (fichero) return JSON.parse(readFileSync(fichero, 'utf8')) as { keys?: Record<string, unknown>[] };
  const r = await fetch(`${emisor()}/cdn-cgi/access/certs`, { signal: AbortSignal.timeout(10_000) });
  if (!r.ok) throw new Error(`certs ${r.status}`);
  return (await r.json()) as { keys?: Record<string, unknown>[] };
}

async function cargarClaves(forzar = false): Promise<Map<string, KeyObject>> {
  if (claves.size && !forzar && ahoraS() < hasta) return claves;
  if (forzar && claves.size && ahoraS() - ultimaForzada < RECARGA_MIN_S) return claves;
  if (forzar) ultimaForzada = ahoraS();
  let nuevas: Map<string, KeyObject>;
  try {
    const jwks = await leerJwks();
    nuevas = new Map();
    for (const k of jwks.keys ?? []) {
      if (k.kty !== 'RSA' || typeof k.kid !== 'string') continue;
      nuevas.set(String(k.kid), createPublicKey({ key: { kty: 'RSA', n: String(k.n), e: String(k.e) }, format: 'jwk' }));
    }
  } catch {
    hasta = ahoraS() + RECARGA_MIN_S; // se reintenta en un minuto
    return claves;
  }
  if (nuevas.size) {
    claves = nuevas;
    hasta = ahoraS() + 3600;
  }
  return claves;
}

const b64 = (s: string) => Buffer.from(s, 'base64url');

/** acceso_cf.py › verificar: { carga } si el sello vale; { motivo } si no. */
export async function verificar(token: string): Promise<{ carga: Record<string, unknown> } | { motivo: string }> {
  const aud = process.env.RO_CF_AUD;
  if (!aud || !process.env.RO_CF_EQUIPO) {
    return { motivo: 'El servidor no tiene RO_CF_EQUIPO y RO_CF_AUD: no puede comprobar Access (no entra nadie).' };
  }
  const partes = token.split('.');
  let h: Record<string, unknown>;
  let p: Record<string, unknown>;
  let firma: Buffer;
  try {
    if (partes.length !== 3) throw new Error('partes');
    h = JSON.parse(b64(partes[0]!).toString('utf8')) as Record<string, unknown>;
    p = JSON.parse(b64(partes[1]!).toString('utf8')) as Record<string, unknown>;
    firma = b64(partes[2]!);
    if (!h || typeof h !== 'object' || !p || typeof p !== 'object') throw new Error('forma');
  } catch {
    return { motivo: 'Sello de Access mal formado.' };
  }
  if (h.alg !== 'RS256') return { motivo: 'Sello de Access con un algoritmo no admitido.' };
  const kid = typeof h.kid === 'string' ? h.kid : '';
  let mapa = await cargarClaves();
  if (!mapa.has(kid)) mapa = await cargarClaves(true); // Cloudflare rota sus claves: se recargan una vez
  const clave = mapa.get(kid);
  if (!clave) return { motivo: 'Sello de Access firmado con una clave desconocida.' };
  let buena = false;
  try {
    buena = verify('RSA-SHA256', Buffer.from(`${partes[0]}.${partes[1]}`), clave, firma);
  } catch {
    buena = false;
  }
  if (!buena) return { motivo: 'La firma del sello de Access no es válida.' };
  const ahora = ahoraS();
  const auds = Array.isArray(p.aud) ? p.aud : [p.aud];
  if (!auds.includes(aud)) return { motivo: 'El sello de Access es de otra aplicación.' };
  if (p.iss !== emisor()) return { motivo: 'El sello de Access es de otro equipo de Cloudflare.' };
  if (!p.exp || (p.exp as number) < ahora - MARGEN_S) return { motivo: 'El sello de Access ha caducado: vuelve a entrar.' };
  if (p.nbf && (p.nbf as number) > ahora + MARGEN_S) return { motivo: 'El sello de Access aún no vale.' };
  if (!p.email) return { motivo: 'El sello de Access no trae correo (¿token de servicio?).' };
  return { carga: p };
}

/** acceso_cf.py › token_de: la cabecera Cf-Access-Jwt-Assertion o, si no, la galleta CF_Authorization. */
export function tokenDe(cabeceras: IncomingHttpHeaders): string | null {
  const t = cabeceras['cf-access-jwt-assertion'];
  const cab = Array.isArray(t) ? t[0] : t;
  if (cab) return cab;
  for (const trozo of (cabeceras.cookie ?? '').split(';')) {
    const limpio = trozo.trim();
    if (limpio.startsWith('CF_Authorization=')) return limpio.split('=').slice(1).join('=');
  }
  return null;
}

/** acceso_cf.py › correo_validado: { correo } en minúsculas o { motivo }. Lo único que usa la identidad en «access». */
export async function correoValidado(cabeceras: IncomingHttpHeaders): Promise<{ correo: string } | { motivo: string }> {
  const t = tokenDe(cabeceras);
  if (!t) return { motivo: 'Falta el sello de Cloudflare Access: entra por la dirección de la app.' };
  const r = await verificar(t);
  return 'carga' in r ? { correo: String(r.carga.email).toLowerCase() } : r;
}

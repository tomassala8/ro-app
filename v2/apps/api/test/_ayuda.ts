import { existsSync, readFileSync } from 'node:fs';
import { request as httpRequest } from 'node:http';
import { join } from 'node:path';

export const BASE = process.env.RO_BASE_URL ?? 'http://127.0.0.1:3000';
export const VEC = process.env.RO_VECTORES?.replace(/^~/, process.env.HOME ?? '');

export function leerVec(nombre: string): unknown {
  if (!VEC) throw new Error('falta RO_VECTORES');
  return JSON.parse(readFileSync(join(VEC, nombre), 'utf8'));
}

export function vectoresListos(): boolean {
  return Boolean(VEC && existsSync(join(VEC, 'permisos.json')) && existsSync(join(VEC, 'crudo.json')));
}

export interface RespuestaHttp {
  status: number;
  json: unknown;
  headers: Headers;
}

export async function pedir(
  metodo: string,
  ruta: string,
  opts: { yo?: string; como?: string; cuerpo?: unknown } = {},
): Promise<RespuestaHttp> {
  const headers: Record<string, string> = {
    Accept: 'application/json',
    'X-RO-App': '1',
    Origin: 'http://127.0.0.1:3000',
  };
  if (opts.yo) headers['X-RO-Yo'] = opts.yo;
  if (opts.como) headers['X-RO-Como'] = opts.como;
  if (opts.cuerpo !== undefined) headers['Content-Type'] = 'application/json';
  const r = await fetch(BASE + ruta, {
    method: metodo,
    headers,
    body: opts.cuerpo !== undefined ? JSON.stringify(opts.cuerpo) : undefined,
    redirect: 'manual',
  });
  const texto = await r.text();
  let json: unknown = null;
  if (texto) {
    try {
      json = JSON.parse(texto);
    } catch {
      json = null;
    }
  }
  return { status: r.status, json, headers: r.headers };
}

/** Petición con Host ajeno: fetch no deja fijar Host. */
export function pedirConHost(ruta: string, host: string, yo: string): Promise<number> {
  const url = new URL(BASE + ruta);
  return new Promise((resolve, reject) => {
    const req = httpRequest(
      {
        hostname: url.hostname,
        port: url.port,
        path: `${url.pathname}${url.search}`,
        method: 'GET',
        headers: {
          Host: host,
          'X-RO-Yo': yo,
          'X-RO-App': '1',
          Origin: 'http://127.0.0.1:3000',
          Accept: 'application/json',
        },
      },
      (res) => {
        res.resume();
        resolve(res.statusCode ?? 0);
      },
    );
    req.on('error', reject);
    req.end();
  });
}

export function hojas(obj: unknown, ruta: string[] = []): [string, unknown][] {
  if (Array.isArray(obj)) return obj.flatMap((x, i) => hojas(x, [...ruta, String(i)]));
  if (obj && typeof obj === 'object') {
    const pares = Object.entries(obj);
    if (!pares.length) return [[ruta.join('.'), obj]];
    return pares.flatMap(([k, v]) => hojas(v, [...ruta, k]));
  }
  return [[ruta.join('.'), obj]];
}

const BLANCA_EXACTA = new Set([
  'soloLectura',
  'solo_lectura',
  'pilotoLectura',
  'piloto_lectura',
  'puedeVerComo',
  'puede_ver_como',
  'hora',
  'bloqueados',
  'servidor',
  'puedeEditar',
  'generado',
  'generado_en_peticion',
  'ahora',
]);

export function enBlanca(camino: string): boolean {
  const partes = camino.split('.').filter((p) => !/^\d+$/.test(p));
  if (partes[0] === 'real' || partes[0] === 'persona') return true;
  return partes.some((p) => BLANCA_EXACTA.has(p));
}

export interface PersonaCruda {
  id: string;
  estado?: string;
  puestos?: string[];
}

export function personasPorPuesto(crudo: { personas: PersonaCruda[] }): Record<string, string> {
  const out: Record<string, string> = {};
  for (const p of crudo.personas) {
    if (p.estado !== 'activo') continue;
    for (const puesto of p.puestos ?? []) if (!out[puesto]) out[puesto] = p.id;
  }
  return out;
}

export function errorDe(json: unknown): string | undefined {
  if (json && typeof json === 'object' && 'error' in json) {
    const error = (json as { error: unknown }).error;
    if (typeof error === 'string') return error;
  }
  return undefined;
}

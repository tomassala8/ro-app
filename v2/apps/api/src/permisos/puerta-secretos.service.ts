import { request as httpRequest } from 'node:http';
import { Injectable } from '@nestjs/common';

export type EstadoPuerta = { abierta: true } | { abierta: false; status: number; error: string };

/** El texto del proxy de legado (proxy.ts) cuando servir.py no contesta. */
export const SIN_LEGADO = 'La app de hoy (servir.py) no responde.';

/** Ruta que servir.py no tiene: si contesta 404, la petición ha pasado `_quien` y la puerta de secretos. */
export const RUTA_SONDEO = '/api/puerta-secretos-nest';

/**
 * Puerta de secretos (servir.py › _api_get › `if E.nucleo_bloqueado`: 503). Nest no escanea data/: pregunta al
 * legado, que es quien escanea. Cerrar, nunca abrir: si no se puede saber (sin legado, error de red, tiempo agotado
 * o un código que no sea 404 ni 503), la respuesta es 502 con el texto del proxy. Nunca manda X-RO-Como: en el
 * legado, «ver como» apuntaría una lectura en el rastro.
 */
@Injectable()
export class PuertaSecretosService {
  private readonly base = process.env.RO_LEGADO_URL;
  private readonly esperaMs = Number(process.env.RO_PUERTA_SECRETOS_MS ?? 3000);

  estado(identidad: Record<string, string>): Promise<EstadoPuerta> {
    const cerrada: EstadoPuerta = { abierta: false, status: 502, error: SIN_LEGADO };
    if (!this.base) return Promise.resolve(cerrada);
    let url: URL;
    try {
      url = new URL(RUTA_SONDEO, this.base);
    } catch {
      return Promise.resolve(cerrada);
    }
    return new Promise((resolve) => {
      const req = httpRequest(
        url,
        { method: 'GET', headers: { ...identidad, host: url.host, 'x-ro-via': 'nest', accept: 'application/json' } },
        (res) => {
          const trozos: Buffer[] = [];
          res.on('data', (t: Buffer) => trozos.push(t));
          res.on('error', () => resolve(cerrada));
          res.on('end', () => {
            if (res.statusCode === 404) return resolve({ abierta: true });
            if (res.statusCode === 503) {
              try {
                const cuerpo = JSON.parse(Buffer.concat(trozos).toString('utf8')) as { error?: unknown };
                if (typeof cuerpo.error === 'string') return resolve({ abierta: false, status: 503, error: cuerpo.error });
              } catch {
                // cuerpo ilegible: no se sabe, se cierra con el texto del proxy
              }
            }
            resolve(cerrada);
          });
        },
      );
      req.setTimeout(this.esperaMs, () => req.destroy(new Error('tiempo agotado')));
      req.on('error', () => resolve(cerrada));
      req.end();
    });
  }
}

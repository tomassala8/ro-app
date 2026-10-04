import { request as pedirHttp } from 'node:http';
import type { IncomingMessage, ServerResponse } from 'node:http';
import { atiendeNest } from './rutas-en-nest.js';

// Proxy de legado («estrangulador»): lo que Nest aún no atiende va a servir.py con el mismo método, ruta, cabeceras y
// cuerpo, sin tocar nada. servir.py sigue aplicando sus permisos e identidad (X-RO-Yo en local, sello de Cloudflare
// Access en la nube), así que el resultado es idéntico al de hoy. Sin RO_LEGADO_URL, no hace nada.
// Mismo tope de cuerpo que servir.py (`cuerpo()`: 200 000 bytes). Hoy, pasado el tope, servir.py da un 500 genérico
// y corta la conexión; aquí se contesta 413 antes de molestarle.
const CUERPO_MAX = Number(process.env.RO_CUERPO_MAX ?? 200_000);
// Si servir.py no contesta en este tiempo, 504 con mensaje (nunca una pestaña cargando para siempre).
const ESPERA_MS = Number(process.env.RO_LEGADO_ESPERA_MS ?? 60_000);

function json(res: ServerResponse, estado: number, error: string) {
  res.writeHead(estado, { 'Content-Type': 'application/json; charset=utf-8' });
  res.end(JSON.stringify({ error }));
}

export function proxyLegado(base = process.env.RO_LEGADO_URL, { cuerpoMax = CUERPO_MAX, esperaMs = ESPERA_MS } = {}) {
  const destino = base ? new URL(base) : null;
  return (req: IncomingMessage, res: ServerResponse, siguiente: () => void) => {
    const ruta = (req.url ?? '/').split('?')[0];
    if (!destino || atiendeNest(req.method ?? 'GET', ruta)) return siguiente();
    // En local, la misma defensa que servir.py contra «DNS rebinding»: solo 127.0.0.1 / localhost.
    if (process.env.RO_IDENTIDAD !== 'access' && !/^(127\.0\.0\.1|localhost)(:\d+)?$/i.test(req.headers.host ?? '')) {
      return json(res, 403, 'Host no permitido.');
    }
    // HEAD y OPTIONS: servir.py no tiene do_HEAD y el de la biblioteca de Python sirve ficheros sin pasar por la
    // identidad ni los permisos (auditoría del 4-oct, L-07). Aquí no pasan: 405.
    if (req.method === 'HEAD' || req.method === 'OPTIONS') {
      res.writeHead(405, { Allow: 'GET, POST', 'Content-Type': 'application/json; charset=utf-8' });
      return res.end(req.method === 'HEAD' ? undefined : JSON.stringify({ error: 'Método no permitido.' }));
    }
    if (Number(req.headers['content-length'] ?? 0) > cuerpoMax) {
      req.resume();
      return json(res, 413, 'Petición demasiado grande.');
    }
    const salida = pedirHttp(
      {
        protocol: destino.protocol,
        hostname: destino.hostname,
        port: destino.port,
        method: req.method,
        path: req.url,
        // Host: el de servir.py (comprueba que le hablan a él). Origin: servir.py lo admite con RO_ORIGEN_APP.
        headers: { ...req.headers, host: destino.host, 'x-ro-via': 'nest' },
      },
      (respuesta) => {
        res.writeHead(respuesta.statusCode ?? 502, respuesta.headers);
        respuesta.pipe(res);
      },
    );
    let tarde = false;
    salida.setTimeout(esperaMs, () => {
      tarde = true;
      salida.destroy();
    });
    salida.on('error', () => {
      if (res.headersSent) return res.destroy();
      if (tarde) return json(res, 504, 'La app de hoy (servir.py) tarda demasiado en responder.');
      json(res, 502, 'La app de hoy (servir.py) no responde.');
    });
    // Cuerpo sin Content-Length (por trozos): se cuenta al pasar y se corta en el tope.
    let bytes = 0;
    req.on('data', (trozo: Buffer) => {
      bytes += trozo.length;
      if (bytes > cuerpoMax && !res.headersSent) {
        req.unpipe(salida);
        salida.destroy();
        json(res, 413, 'Petición demasiado grande.');
      }
    });
    req.pipe(salida);
  };
}

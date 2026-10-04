import { request as pedirHttp } from 'node:http';
import type { IncomingMessage, ServerResponse } from 'node:http';
import { atiendeNest } from './rutas-en-nest.js';

// Proxy de legado («estrangulador»): lo que Nest aún no atiende va a servir.py con el mismo método, ruta, cabeceras y
// cuerpo, sin tocar nada. servir.py sigue aplicando sus permisos e identidad (X-RO-Yo en local, sello de Cloudflare
// Access en la nube), así que el resultado es idéntico al de hoy. Sin RO_LEGADO_URL, no hace nada.
export function proxyLegado(base = process.env.RO_LEGADO_URL) {
  const destino = base ? new URL(base) : null;
  return (req: IncomingMessage, res: ServerResponse, siguiente: () => void) => {
    const ruta = (req.url ?? '/').split('?')[0];
    if (!destino || atiendeNest(req.method ?? 'GET', ruta)) return siguiente();
    // En local, la misma defensa que servir.py contra «DNS rebinding»: solo 127.0.0.1 / localhost.
    if (process.env.RO_IDENTIDAD !== 'access' && !/^(127\.0\.0\.1|localhost)(:\d+)?$/i.test(req.headers.host ?? '')) {
      res.writeHead(403, { 'Content-Type': 'application/json; charset=utf-8' });
      return res.end(JSON.stringify({ error: 'Host no permitido.' }));
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
    salida.on('error', () => {
      if (res.headersSent) return res.destroy();
      res.writeHead(502, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify({ error: 'La app de hoy (servir.py) no responde.' }));
    });
    req.pipe(salida);
  };
}

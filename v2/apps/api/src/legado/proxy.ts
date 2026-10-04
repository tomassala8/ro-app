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

// En la nube (RO_IDENTIDAD=access) la persona sale solo del sello de Access. servir.py ya ignora ahí X-RO-Yo, ?yo= y
// la galleta ro_yo; aquí además se quitan antes de reenviar (defensa en dos capas: si un día alguien arranca servir.py
// sin el modo Access, no le llega nada con que hacerse pasar por otro). Lo mismo con la cabecera de correo de Access:
// sin el modo Access, servir.py se la cree tal cual; la identidad buena es el sello firmado (cf-access-jwt-assertion).
export function sinIdentidadLocal(url: string, cabeceras: IncomingMessage['headers']) {
  const u = new URL(url, 'http://x');
  u.searchParams.delete('yo');
  const headers = { ...cabeceras };
  delete headers['x-ro-yo'];
  delete headers['cf-access-authenticated-user-email'];
  if (typeof headers.cookie === 'string') {
    const resto = headers.cookie.split(';').filter((g) => g.split('=')[0].trim() !== 'ro_yo').join(';').trim();
    if (resto) headers.cookie = resto;
    else delete headers.cookie;
  }
  return { path: u.pathname + u.search, headers };
}

const LOCAL = /^(127\.0\.0\.1|localhost)(:\d+)?$/i;

// Host y, si viene, cada X-Forwarded-Host (puede llegar repetida o en lista con comas) tienen que ser locales.
export function hostLocal(cabeceras: IncomingMessage['headers']) {
  if (!LOCAL.test(cabeceras.host ?? '')) return false;
  const reenviado = cabeceras['x-forwarded-host'];
  if (reenviado === undefined) return true;
  const hosts = (Array.isArray(reenviado) ? reenviado : [reenviado]).flatMap((h) => h.split(',')).map((h) => h.trim());
  return hosts.every((h) => LOCAL.test(h));
}

export function proxyLegado(base = process.env.RO_LEGADO_URL, { cuerpoMax = CUERPO_MAX, esperaMs = ESPERA_MS } = {}) {
  const destino = base ? new URL(base) : null;
  return (req: IncomingMessage, res: ServerResponse, siguiente: () => void) => {
    const ruta = (req.url ?? '/').split('?')[0];
    if (!destino || atiendeNest(req.method ?? 'GET', ruta)) return siguiente();
    // En local, la misma defensa que servir.py contra «DNS rebinding»: solo 127.0.0.1 / localhost. Detrás del
    // rewrite de Next, Host llega ya cambiado a 127.0.0.1:4000 (changeOrigin): el original va en X-Forwarded-Host.
    if (process.env.RO_IDENTIDAD !== 'access' && !hostLocal(req.headers)) return json(res, 403, 'Host no permitido.');
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
    const limpio =
      process.env.RO_IDENTIDAD === 'access'
        ? sinIdentidadLocal(req.url ?? '/', req.headers)
        : { path: req.url, headers: req.headers };
    const salida = pedirHttp(
      {
        protocol: destino.protocol,
        hostname: destino.hostname,
        port: destino.port,
        method: req.method,
        path: limpio.path,
        // Host: el de servir.py (comprueba que le hablan a él). Origin: servir.py lo admite con RO_ORIGEN_APP.
        headers: { ...limpio.headers, host: destino.host, 'x-ro-via': 'nest' },
      },
      (respuesta) => {
        if (res.destroyed) return respuesta.destroy();
        res.writeHead(respuesta.statusCode ?? 502, respuesta.headers);
        respuesta.pipe(res);
        res.on('close', () => respuesta.destroy());
      },
    );
    // Si el cliente se va antes de tiempo, se corta también la petición a servir.py (no queda trabajando para nadie).
    res.on('close', () => {
      if (!res.writableFinished) salida.destroy();
    });
    let tarde = false;
    salida.setTimeout(esperaMs, () => {
      tarde = true;
      salida.destroy();
    });
    salida.on('error', () => {
      if (res.destroyed || res.headersSent) return res.destroy();
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

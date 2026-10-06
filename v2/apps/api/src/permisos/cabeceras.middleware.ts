import type { IncomingMessage, ServerResponse } from 'node:http';

/** servir.py › CSP: el texto exacto (una sola cadena). */
export const CSP =
  "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; " +
  "font-src 'self'; img-src 'self' data: https:; connect-src 'self'; object-src 'none'; " +
  "frame-ancestors 'none'; base-uri 'none'; form-action 'self'";

export const CABECERAS_SEGURIDAD: ReadonlyArray<readonly [string, string]> = [
  ['X-Content-Type-Options', 'nosniff'],
  ['Referrer-Policy', 'no-referrer'],
  ['Content-Security-Policy', CSP],
  ['X-Frame-Options', 'DENY'],
  ['Permissions-Policy', 'camera=(), microphone=(), geolocation=()'],
];

/**
 * servir.py › end_headers: las mismas cabeceras en todo lo que atiende Nest, también en los 401/403 de las guardas
 * (por eso es middleware y no interceptor). Lo que va por el proxy ya las trae de servir.py.
 */
export function cabecerasSeguridad(_req: IncomingMessage, res: ServerResponse, next: () => void): void {
  for (const [k, v] of CABECERAS_SEGURIDAD) res.setHeader(k, v);
  next();
}

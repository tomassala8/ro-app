import { Injectable, type NestMiddleware } from '@nestjs/common';
import type { NextFunction, Request, Response } from 'express';
import { hostLocal } from '../legado/proxy.js';

/**
 * servir.py › host_ok y peticion_propia, para lo que atiende Nest. El proxy solo lo hace en lo que sigue al legado
 * (proxy.ts): sin esto, una ruta mudada se saltaría el Host, el 405 de HEAD/OPTIONS y la cabecera de la app.
 */
@Injectable()
export class PeticionMiddleware implements NestMiddleware {
  use(req: Request, res: Response, next: NextFunction): void {
    if (process.env.RO_IDENTIDAD !== 'access' && !hostLocal(req.headers)) {
      res.status(403).json({ error: 'Host no permitido.' });
      return;
    }
    if (req.method === 'HEAD' || req.method === 'OPTIONS') {
      res.status(405);
      res.setHeader('Allow', 'GET, POST');
      if (req.method === 'HEAD') {
        res.end();
        return;
      }
      res.json({ error: 'Método no permitido.' });
      return;
    }
    if (req.method !== 'GET') {
      const tipo = String(req.headers['content-type'] ?? '').toLowerCase();
      if (req.headers['x-ro-app'] !== '1') {
        res.status(403).json({ error: 'Falta la cabecera de la app (X-RO-App).' });
        return;
      }
      if (!tipo.startsWith('application/json')) {
        res.status(403).json({ error: 'Solo se acepta JSON.' });
        return;
      }
      const origen = req.headers.origin;
      if (origen) {
        const puerto = process.env.PORT ?? '4000';
        const propios = new Set(
          [`http://127.0.0.1:${puerto}`, `http://localhost:${puerto}`, ...(process.env.RO_ORIGEN_APP ?? '').split(',')].filter(
            Boolean,
          ),
        );
        if (!propios.has(origen)) {
          res.status(403).json({ error: 'Origen no permitido.' });
          return;
        }
      }
      const sitio = req.headers['sec-fetch-site'];
      if (sitio !== undefined && sitio !== 'same-origin' && sitio !== 'none') {
        res.status(403).json({ error: 'Petición desde otra web.' });
        return;
      }
    }
    next();
  }
}

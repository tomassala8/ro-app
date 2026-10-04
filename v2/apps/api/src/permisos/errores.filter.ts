import { ArgumentsHost, Catch, ExceptionFilter, HttpException, Logger } from '@nestjs/common';
import { json } from 'express';

/** Errores de Prisma que son culpa de la petición, no del servidor: 4xx con un mensaje claro, nunca el SQL. */
const PRISMA: Record<string, [number, string]> = {
  P2002: [409, 'Ya existe.'],
  P2025: [404, 'No existe.'],
  P2003: [400, 'Hace referencia a algo que no existe.'],
};

/** Todo error de Nest sale con la forma de servir.py: `{"error": "…"}` y el mismo código. Sin esto, el contrato de
 *  escritura (que compara también el cuerpo de los 403) sale ROJO en cada ruta portada. Nunca sale la pila ni el SQL.
 *  Solo los 5xx van al registro como error: un 403 o un 404 es la app funcionando bien. */
@Catch()
export class ErroresFilter implements ExceptionFilter {
  private readonly registro = new Logger('errores');

  catch(error: unknown, host: ArgumentsHost): void {
    const res = host.switchToHttp().getResponse<{ status(c: number): { json(c: unknown): void } }>();
    if (error instanceof HttpException) {
      const r = error.getResponse();
      const m = typeof r === 'string' ? r : (r as { message?: unknown }).message;
      const texto = Array.isArray(m) ? m.join(' ') : typeof m === 'string' ? m : error.message;
      res.status(error.getStatus()).json({ error: texto });
      return;
    }
    const codigo = (error as { code?: unknown })?.code;
    if (typeof codigo === 'string' && PRISMA[codigo]) {
      const [estado, texto] = PRISMA[codigo];
      res.status(estado).json({ error: texto });
      return;
    }
    // Igual que servir.py: el detalle al registro del servidor, nunca a la respuesta.
    this.registro.error(error instanceof Error ? (error.stack ?? error.message) : String(error));
    res.status(500).json({ error: 'Error interno (el detalle queda en el registro del servidor).' });
  }
}

/** Lector de JSON para las rutas de Nest con respuestas limpias (N-13): JSON roto → 400, demasiado grande → 413, en la
 *  forma de servir.py. Sin esto, Express devuelve el texto del analizador de JSON en inglés. */
export function leerJson(limite: string | number = 200_000) {
  const leer = json({ limit: limite });
  type Res = { status(c: number): { json(c: unknown): void } };
  return (req: unknown, res: Res, next: (e?: unknown) => void) =>
    leer(req as never, res as never, (err?: { type?: string }) => {
      if (!err) return next();
      if (err.type === 'entity.too.large') return res.status(413).json({ error: 'Petición demasiado grande.' });
      res.status(400).json({ error: 'JSON no válido.' });
    });
}

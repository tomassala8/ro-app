import { ArgumentsHost, Catch, ExceptionFilter, HttpException, Logger } from '@nestjs/common';

/** Todo error de Nest sale con la forma de servir.py: `{"error": "…"}` y el mismo código. Sin esto, el contrato de
 *  escritura (que compara también el cuerpo de los 403) sale ROJO en cada ruta portada. Global: AppModule y pruebas. */
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
    // Igual que servir.py: el detalle al registro del servidor, nunca a la respuesta.
    this.registro.error(error instanceof Error ? (error.stack ?? error.message) : String(error));
    res.status(500).json({ error: 'Error interno (el detalle queda en el registro del servidor).' });
  }
}

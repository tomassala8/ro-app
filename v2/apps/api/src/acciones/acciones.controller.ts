import { Controller, Get, Query, Req } from '@nestjs/common';
import { Permiso } from '../permisos/declarar.js';
import type { VistaConContexto } from '../permisos/motor-ro.js';
import { AccionesService } from './acciones.service.js';

function moduloDe(q: string | string[] | undefined): string | undefined {
  const v = Array.isArray(q) ? q[0] : q;
  return v ? v : undefined;
}

/** GET /api/acciones. El POST sigue en el proxy: lo interceptan cinco enchufes. */
@Controller('acciones')
export class AccionesController {
  constructor(private readonly acciones: AccionesService) {}

  @Permiso({
    soloIdentidad: 'toda persona activa lee las acciones de su ámbito, como servir.py › GET /api/acciones',
    sinRecorte: 'fila a fila con filaVisible, recortarVistas y recorteImportesLectura588 como servir.py:2854-2863',
  })
  @Get()
  listar(@Req() req: { vista: VistaConContexto }, @Query('modulo') modulo?: string | string[]) {
    return this.acciones.listar(req.vista, moduloDe(modulo));
  }
}

import { Controller, Get, HttpException, Param, Req } from '@nestjs/common';
import { Permiso } from '../permisos/declarar.js';
import type { VistaConContexto } from '../permisos/motor-ro.js';
import { ClientesService } from './clientes.service.js';

/** Misma clase que el fullmatch de servir.py › /api/cliente/<cid> (`\w` de Python). */
const CID_RUTA = /^[\p{L}\p{N}_-]+$/u;

@Controller('cliente')
export class ClientesController {
  constructor(private readonly clientes: ClientesService) {}

  @Permiso({
    soloIdentidad: 'toda persona activa pide una ficha; la puerta del cliente decide si es suya',
    sinRecorte: 'recortar(persona) y recortarFicha hacen el recorte como servir.py:2709,2735',
  })
  @Get(':cid')
  async ficha(@Param('cid') cid: string, @Req() req: { vista: VistaConContexto }) {
    if (!CID_RUTA.test(cid)) throw new HttpException('No existe esa ruta de la API.', 404);
    return this.clientes.ficha(req.vista, cid);
  }
}

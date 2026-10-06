import { Controller, Get, Req } from '@nestjs/common';
import { Permiso } from '../permisos/declarar.js';
import type { VistaConContexto } from '../permisos/motor-ro.js';
import { SesionService } from './sesion.service.js';

/**
 * GET /api/sesion (servir.py › _api_get). Declaración «identidad sin módulo» (la que reutilizan F5.3–F5.9): la recibe
 * toda persona identificada y activa, y el recorte va dentro. No es @Publico: con @Publico la guarda de permisos no
 * apuntaría el rastro de «ver como» ni frenaría escrituras. Tampoco `tipo: 'ver_como'` (dejaría fuera a quien no
 * puede «ver como») ni un módulo (la sesión colgaría de una pantalla).
 */
@Controller('sesion')
export class SesionController {
  constructor(private readonly sesion: SesionService) {}

  @Permiso({
    soloIdentidad: 'toda persona activa recibe su sesión, como servir.py › /api/sesion',
    sinRecorte: 'la sesión ya sale recortada por recortar(persona, crudo), igual que servir.py › /api/sesion',
  })
  @Get()
  leer(@Req() req: { vista: VistaConContexto }) {
    return this.sesion.sesion(req.vista);
  }
}

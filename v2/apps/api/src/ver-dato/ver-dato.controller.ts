import { Body, Controller, HttpCode, Post, Req } from '@nestjs/common';
import { Permiso } from '../permisos/declarar.js';
import type { VistaConContexto } from '../permisos/motor-ro.js';
import { VerDatoService } from './ver-dato.service.js';

/** POST /api/ver_dato. La única escritura que «ver como» puede usar: solo lee y deja rastro. */
@Controller('ver_dato')
export class VerDatoController {
  constructor(private readonly verDato: VerDatoService) {}

  @Permiso({
    soloIdentidad: 'toda persona activa pide un dato; las reglas van dentro',
    lecturaPorPost: 'solo lee: igual que servir.py:3243',
    sinRecorte: 'un valor; las reglas están dentro como servir.py:3340-3388',
  })
  @Post()
  @HttpCode(200)
  ver(@Req() req: { vista: VistaConContexto }, @Body() body: unknown) {
    return this.verDato.ver(req.vista, body);
  }
}

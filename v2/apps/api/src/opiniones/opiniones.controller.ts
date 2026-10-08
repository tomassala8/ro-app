import { Body, Controller, Get, HttpCode, Post, Query, Req } from '@nestjs/common';
import { Permiso } from '../permisos/declarar.js';
import type { VistaConContexto } from '../permisos/motor-ro.js';
import { OpinionesService } from './opiniones.service.js';

/** GET /api/opiniones, GET /api/opiniones/captura y POST /api/opiniones/estado. */
@Controller('opiniones')
export class OpinionesController {
  constructor(private readonly opiniones: OpinionesService) {}

  @Permiso({
    soloIdentidad: 'toda persona activa lee sus opiniones o todas si opiniones_ver',
    sinRecorte: 'propias o todas según opiniones_ver; sin clientes',
  })
  @Get()
  listar(@Req() req: { vista: VistaConContexto }) {
    return this.opiniones.listar(req.vista);
  }

  @Permiso({
    soloIdentidad: 'toda persona activa pide su captura; la puerta 565 decide',
    sinRecorte: 'la captura es de quien la escribió; permisoCaptura565 hace la puerta',
  })
  @Get('captura')
  captura(@Req() req: { vista: VistaConContexto }, @Query('id') id: string | undefined) {
    return this.opiniones.captura(req.vista, id);
  }

  @Permiso({ tipo: 'opiniones_ver', sinRecorte: 'la respuesta es ok, sin el texto de la opinión' })
  @Post('estado')
  @HttpCode(200)
  estado(@Req() req: { vista: VistaConContexto }, @Body() body: unknown) {
    return this.opiniones.estado(req.vista, body);
  }
}

/** POST /api/opinion. Ruta distinta de /api/opiniones. */
@Controller('opinion')
export class OpinionController {
  constructor(private readonly opiniones: OpinionesService) {}

  @Permiso({
    soloIdentidad: 'toda persona activa manda un aviso; «ver como» no escribe',
    sinRecorte: 'la respuesta es ok, id y avisado, sin el texto',
  })
  @Post()
  @HttpCode(200)
  crear(@Req() req: { vista: VistaConContexto }, @Body() body: unknown) {
    return this.opiniones.crear(req.vista, body);
  }
}

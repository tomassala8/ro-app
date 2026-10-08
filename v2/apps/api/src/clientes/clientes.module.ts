import { Module } from '@nestjs/common';
import { ClientesController } from './clientes.controller.js';
import { ClientesService } from './clientes.service.js';
import { LogosController } from './logos.controller.js';

/** GET /api/cliente/<cid> y GET /logos/<cid>.<ext>. */
@Module({
  controllers: [ClientesController, LogosController],
  providers: [ClientesService],
})
export class ClientesModule {}

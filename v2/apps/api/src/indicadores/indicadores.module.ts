import { Module } from '@nestjs/common';
import { IndicadoresController } from './indicadores.controller.js';
import { IndicadoresService } from './indicadores.service.js';

/** GET /api/indicadores. */
@Module({
  controllers: [IndicadoresController],
  providers: [IndicadoresService],
})
export class IndicadoresModule {}

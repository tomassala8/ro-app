import { Module } from '@nestjs/common';
import { RastroService } from './rastro.service.js';

/** El rastro imborrable (tabla registro + registro_huellas). Quien escriba en él importa este módulo. */
@Module({ providers: [RastroService], exports: [RastroService] })
export class RastroModule {}

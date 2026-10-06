import { Module } from '@nestjs/common';
import { RastroModule } from '../rastro/rastro.module.js';
import { SesionController } from './sesion.controller.js';
import { SesionService } from './sesion.service.js';

@Module({ imports: [RastroModule], controllers: [SesionController], providers: [SesionService] })
export class SesionModule {}

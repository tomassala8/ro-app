import { Controller, Get } from '@nestjs/common';
import { Publico } from '../permisos/declarar.js';
import { PrismaService } from '../prisma/prisma.service.js';

/** /vivo: comprobación de salud sin datos, igual que en servir.py (la usa el proveedor de la nube). */
@Controller()
export class SaludController {
  constructor(private readonly prisma: PrismaService) {}

  @Publico('comprobación de vida, sin datos')
  @Get('vivo')
  async vivo() {
    await this.prisma.db.$queryRaw`SELECT 1`;
    return { ok: true };
  }
}

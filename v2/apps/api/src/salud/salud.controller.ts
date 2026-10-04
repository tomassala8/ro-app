import { Controller, Get } from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service.js';

/** /vivo: comprobación de salud sin datos, igual que en servir.py (la usa el proveedor de la nube). */
@Controller()
export class SaludController {
  constructor(private readonly prisma: PrismaService) {}

  @Get('vivo')
  async vivo() {
    await this.prisma.db.$queryRaw`SELECT 1`;
    return { ok: true };
  }
}

import { Injectable, OnModuleDestroy, OnModuleInit } from '@nestjs/common';
import { crearPrisma, PrismaClient } from '@ro/db';

/** La única puerta a Postgres. Los servicios de cada dominio la inyectan; nadie crea su propio cliente. */
@Injectable()
export class PrismaService implements OnModuleInit, OnModuleDestroy {
  readonly db: PrismaClient = crearPrisma();

  async onModuleInit() {
    await this.db.$connect();
  }

  async onModuleDestroy() {
    await this.db.$disconnect();
  }
}

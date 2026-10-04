import { PrismaPg } from '@prisma/adapter-pg'
import { PrismaClient } from './generated/client.js'

export * from './generated/client.js'

/** Un cliente de Prisma por proceso. En Nest se crea desde PrismaService (apps/api/src/prisma). */
export function crearPrisma(url = process.env.DATABASE_URL): PrismaClient {
  if (!url) throw new Error('Falta DATABASE_URL')
  return new PrismaClient({ adapter: new PrismaPg({ connectionString: url }) })
}

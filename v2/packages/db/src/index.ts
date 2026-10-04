import { PrismaPg } from '@prisma/adapter-pg'
import { PrismaClient } from './generated/client.js'

export * from './generated/client.js'

/** Un cliente de Prisma por proceso. En Nest se crea desde PrismaService (apps/api/src/prisma). */
export function crearPrisma(url = process.env.DATABASE_URL): PrismaClient {
  if (!url) throw new Error('Falta DATABASE_URL')
  // Tope de conexiones de la API (RO_PG_POOL_MAX, 10 por defecto). Sumado al legado (servir.py: 4 libres más las de
  // los picos; 15-17 con 30 personas a la vez el 4-oct) tiene que quedar holgado bajo el límite de la Postgres en la nube.
  const max = Number(process.env.RO_PG_POOL_MAX ?? 10)
  return new PrismaClient({ adapter: new PrismaPg({ connectionString: url, max }) })
}

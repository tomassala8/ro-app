import 'dotenv/config'
import { defineConfig } from 'prisma/config'

export default defineConfig({
  schema: 'prisma/schema.prisma',
  migrations: { path: 'prisma/migrations', seed: 'tsx prisma/seed.ts' },
  // Sin DATABASE_URL (instalación limpia, «prisma generate») se usa la base local del docker-compose.
  datasource: { url: process.env.DATABASE_URL ?? 'postgresql://ro:ro@127.0.0.1:5432/ro_app' },
})

# v2 · la app de RO en Next + Nest + Postgres

Monorepo con pnpm. Lo arma la migración descrita en `../migracion/PLAN_MAESTRO.md`.

| Paquete | Qué es |
|---|---|
| `apps/web` (`@ro/web`) | Next 16 + Tailwind 4 + shadcn. Puerto 3000. Pasa `/api`, `/vivo` y `/logos` a la API |
| `apps/api` (`@ro/api`) | Nest 12. Puerto 4000. Mismas rutas que `servir.py` |
| `packages/db` (`@ro/db`) | Prisma 7 + Postgres 16. `schema.prisma` sale de la base real (`scripts/rehacer_base.sh`) |
| `packages/permisos` (`@ro/permisos`) | El motor de permisos en TypeScript (lee `../reglas_permisos.json`) |
| `tools/capturas` | Fotos de cada pantalla y comparación píxel a píxel |

## Arrancar

```bash
corepack enable                 # pnpm 10
pnpm install --frozen-lockfile
cp .env.example .env            # y apps/api/.env, packages/db/.env con la misma DATABASE_URL
pnpm db:up                      # Postgres en Docker, solo 127.0.0.1
pnpm db:deploy                  # crea las 40 tablas, con sus CHECK, vista y disparadores
pnpm dev                        # http://127.0.0.1:3000  ·  http://127.0.0.1:3000/vivo → {"ok":true}
```

Comprobado el 4-oct-2026 (en un Linux con Postgres 16, sin Docker): `pnpm install`, `pnpm build`, `pnpm test`, `pnpm lint` en verde, la migración `0_base` aplica sin errores, `prisma migrate diff` sale vacío y `/vivo` responde a través de Next → Nest → Postgres. Los `Dockerfile` y `docker compose --profile completo` no se han podido probar allí (sin Docker): se prueban en el Mac en la fase 7.

## Base de datos

- Nunca `pnpm db:migrate` esta noche: ver .cursor/rules/10-backend-nest.mdc.
- Las tablas las comparte con el worker en Python (tubería, avisos, envíos, sincronía, vigía). Por eso esta noche los tipos se quedan como hoy (fechas en texto).
- Copiar datos de la app de hoy: `python3 ../migracion/copiar_sqlite_a_pg.py --sqlite <local.db>`.

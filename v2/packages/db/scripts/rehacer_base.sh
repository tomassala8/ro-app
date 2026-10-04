#!/usr/bin/env bash
# Rehace schema.prisma y la migración 0_base a partir del SQL que usa HOY la app (Python).
# Úsalo la noche de la migración, después de `python3 migracion/inventario.py`, si han cambiado tablas durante el día.
#   ADMIN_URL=postgresql://ro:ro@127.0.0.1:5432/postgres  (por defecto, la del docker-compose)
# Crea y borra una base TEMPORAL «ro_introspeccion». Nunca toca la base de la app.
set -euo pipefail
cd "$(dirname "$0")/.."
RAIZ="$(cd ../../.. && pwd)"
ADMIN_URL="${ADMIN_URL:-postgresql://ro:ro@127.0.0.1:5432/postgres}"
TMP_URL="${ADMIN_URL%/*}/ro_introspeccion"
psql "$ADMIN_URL" -qc "DROP DATABASE IF EXISTS ro_introspeccion" -c "CREATE DATABASE ro_introspeccion"
DATABASE_URL="$TMP_URL" python3 "$RAIZ/migracion/crear_base_pg.py"
cat > prisma/schema.prisma <<'P'
generator client {
  provider = "prisma-client"
  output   = "../src/generated"
}

datasource db {
  provider = "postgresql"
}
P
DATABASE_URL="$TMP_URL" pnpm exec prisma db pull
pnpm exec prisma format
mkdir -p prisma/migrations/0_base
pg_dump "$TMP_URL" --schema-only --no-owner --no-privileges --no-comments \
  | grep -v '^\\\(un\)\?restrict\|^SET \|^SELECT pg_catalog.set_config\|^--' | cat -s > prisma/migrations/0_base/migration.sql
psql "$ADMIN_URL" -qc "DROP DATABASE ro_introspeccion"
echo "✔ schema.prisma ($(grep -c '^model' prisma/schema.prisma) modelos) y prisma/migrations/0_base/migration.sql rehechos."
echo "  Si la base de la app ya tenía 0_base aplicada y ha cambiado, NO la edites: escribe a mano una migración nueva"
echo "  (prisma/migrations/<n>_<nombre>/migration.sql) y aplícala con «pnpm db:deploy». «pnpm db:migrate» no se usa esta noche."

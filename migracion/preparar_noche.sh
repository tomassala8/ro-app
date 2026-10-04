#!/usr/bin/env bash
# migracion/preparar_noche.sh · comprueba que el Mac está listo para la migración de esta noche, sin tocar nada de la app.
#
#   cd ~/Downloads/APP_RO_ROLES_Y_PERMISOS_2026-10-02/30_APP_PROTOTIPO
#   bash migracion/preparar_noche.sh            # solo mira y dice qué falta
#   bash migracion/preparar_noche.sh --instalar # además instala lo que se puede instalar solo (pnpm, dependencias, Chromium)
#
# Pásalo por la tarde: si algo sale en ✘, hay tiempo de arreglarlo antes de la noche. Al final, una línea: LISTO o NO LISTO.
set -uo pipefail
cd "$(dirname "$0")/.."
RAIZ="$(pwd)"
INSTALAR=0; [ "${1:-}" = "--instalar" ] && INSTALAR=1
FUERA="${RO_MIGRACION:-$HOME/RO_MIGRACION}"
fallos=0; avisos=0
ok()   { printf "  ✔ %s\n" "$1"; }
mal()  { printf "  ✘ %s\n     → %s\n" "$1" "$2"; fallos=$((fallos+1)); }
ojo()  { printf "  ⚠ %s\n     → %s\n" "$1" "$2"; avisos=$((avisos+1)); }
version_mayor() { "$1" --version 2>/dev/null | grep -oE '[0-9]+' | head -1; }

echo "1 · Repositorio"
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  ok "git en $(basename "$RAIZ") (rama $(git branch --show-current))"
  [ -z "$(git status --porcelain --untracked-files=no)" ] && ok "sin cambios a medias en ficheros versionados" \
    || ojo "hay cambios sin commit" "haz commit de lo de hoy antes de empezar: la migración parte de un commit concreto"
  git fetch -q origin 2>/dev/null && { [ "$(git rev-list --count HEAD..origin/main 2>/dev/null || echo 0)" = "0" ] && ok "al día con origin/main" \
    || ojo "origin/main tiene commits que no tienes" "git pull"; } || ojo "no se pudo hacer git fetch" "revisa la conexión o la llave SSH de GitHub"
else
  mal "esta carpeta no es un repositorio git" "ejecuta el script desde la carpeta de la app (la que tiene servir.py)"
fi
case "$RAIZ" in *"/Desktop/"*|*"Mobile Documents"*) ojo "la app está en una carpeta de iCloud" "muévela a disco local: iCloud ralentiza mucho node_modules";; esac

echo "2 · Herramientas"
N=$(version_mayor node); [ -n "$N" ] && [ "$N" -ge 22 ] && ok "Node $(node --version)" || mal "Node 22 o superior" "brew install node@22  (o nvm install 22)"
if command -v pnpm >/dev/null; then ok "pnpm $(pnpm --version)"
elif [ $INSTALAR = 1 ] && corepack enable 2>/dev/null && corepack prepare pnpm@10.28.0 --activate >/dev/null 2>&1; then ok "pnpm instalado con corepack"
else mal "pnpm" "corepack enable && corepack prepare pnpm@10.28.0 --activate  (o: bash migracion/preparar_noche.sh --instalar)"; fi
P=$(python3 -c 'import sys;print(sys.version_info[1])' 2>/dev/null); [ -n "$P" ] && [ "$P" -ge 11 ] && ok "Python 3.$P" || mal "Python 3.11 o superior" "brew install python@3.12"
python3 -c "import psycopg" 2>/dev/null && ok "psycopg (Python ↔ Postgres)" || {
  [ $INSTALAR = 1 ] && python3 -m pip install -q "psycopg[binary]" && ok "psycopg instalado" || mal "falta psycopg" "python3 -m pip install 'psycopg[binary]'"; }
if docker info >/dev/null 2>&1; then ok "Docker en marcha"
else mal "Docker no responde" "abre Docker Desktop (u OrbStack) y espera a que diga «running»"; fi
command -v psql >/dev/null && ok "psql $(psql --version | grep -oE '[0-9]+\.[0-9]+' | head -1)" || ojo "falta psql" "brew install libpq && brew link --force libpq  (lo usa v2/packages/db/scripts/rehacer_base.sh)"
command -v cursor >/dev/null && ok "Cursor (orden «cursor»)" || ojo "no encuentro la orden «cursor»" "no es imprescindible: basta con abrir esta carpeta en Cursor"

echo "3 · Red (lo que se descarga esta noche)"
for h in registry.npmjs.org ui.shadcn.com github.com binaries.prisma.sh; do
  curl -sS -o /dev/null -m 8 "https://$h" 2>/dev/null && ok "$h" || mal "no llego a $h" "revisa la conexión, VPN o cortafuegos"
done

echo "4 · Datos y app de hoy"
[ -d data ] && ok "data/ ($(find data -name '*.json' | wc -l | tr -d ' ') ficheros)" || mal "no hay data/" "python3 build_data.py (o la tubería): sin datos no se puede grabar la referencia"
[ -f local.db ] && ok "local.db ($(du -h local.db | cut -f1))" || mal "no hay local.db" "arranca una vez servir.py: la crea"
if curl -s -m 3 http://127.0.0.1:8770/api/elegir >/dev/null 2>&1; then ok "servir.py responde en 127.0.0.1:8770"
else ojo "servir.py no está en marcha" "python3 servir.py --bind 127.0.0.1 --puerto 8770  (hace falta para grabar la referencia)"; fi
for puerto in 3000 4000 5432; do
  if lsof -nP -iTCP:$puerto -sTCP:LISTEN >/dev/null 2>&1; then
    quien=$(lsof -nP -iTCP:$puerto -sTCP:LISTEN | awk 'NR==2{print $1}')
    [ "$puerto" = 5432 ] && [ "$quien" != "postgres" ] && [ "$quien" != "com.docke" ] && [ "$quien" != "docker" ] \
      && ojo "el puerto 5432 lo usa «$quien»" "si es otro Postgres, páralo o cambia el puerto en v2/docker-compose.yml" \
      || { [ "$puerto" != 5432 ] && ojo "el puerto $puerto está ocupado por «$quien»" "ciérralo antes de empezar"; }
  else ok "puerto $puerto libre"; fi
done

echo "5 · Espacio y carpeta de trabajo fuera del repo"
LIBRE=$(df -g "$RAIZ" 2>/dev/null | awk 'NR==2{print $4}'); [ -z "$LIBRE" ] && LIBRE=$(df -BG "$RAIZ" | awk 'NR==2{gsub("G","",$4);print $4}')
[ "${LIBRE:-0}" -ge 10 ] && ok "${LIBRE} GB libres" || mal "poco disco (${LIBRE:-?} GB)" "deja al menos 10 GB libres (node_modules, Docker, fotos)"
mkdir -p "$FUERA" && ok "carpeta para datos de la migración: $FUERA (fuera del repo)"

echo "6 · Proyecto nuevo (v2)"
if [ -d v2 ] && command -v pnpm >/dev/null; then
  if [ $INSTALAR = 1 ]; then (cd v2 && pnpm install --frozen-lockfile >/dev/null 2>&1) && ok "dependencias instaladas" || mal "pnpm install falló" "cd v2 && pnpm install  y mira el error"; fi
  if [ -d v2/node_modules ]; then
    (cd v2 && pnpm build >/dev/null 2>&1) && ok "v2 compila (web, api, db, permisos)" || mal "v2 no compila" "cd v2 && pnpm build  y mira el error"
    if [ -x v2/tools/capturas/node_modules/.bin/playwright ]; then
      (cd v2/tools/capturas && ./node_modules/.bin/playwright install --dry-run chromium 2>/dev/null | grep -q "already\|Install location" ) && ok "Playwright listo" || {
        [ $INSTALAR = 1 ] && (cd v2/tools/capturas && ./node_modules/.bin/playwright install chromium >/dev/null 2>&1) && ok "Chromium de Playwright instalado" \
          || ojo "Chromium de Playwright" "cd v2/tools/capturas && pnpm exec playwright install chromium"; }
    fi
  else ojo "v2 sin dependencias" "bash migracion/preparar_noche.sh --instalar"; fi
  if docker info >/dev/null 2>&1; then
    (cd v2 && docker compose up -d postgres >/dev/null 2>&1) && sleep 3 && (cd v2 && docker compose exec -T postgres pg_isready -U ro -d ro_app >/dev/null 2>&1) \
      && ok "Postgres de v2 arriba (127.0.0.1:5432, base ro_app)" || mal "no arranca el Postgres de v2" "cd v2 && docker compose up postgres  y mira el error"
  fi
else mal "no está la carpeta v2/" "git pull: llega con el PR «Plan maestro de migración»"; fi

echo
if [ $fallos = 0 ]; then echo "LISTO para la noche ($avisos avisos que conviene mirar)."; else echo "NO LISTO: $fallos cosas que arreglar y $avisos avisos."; fi
exit $fallos

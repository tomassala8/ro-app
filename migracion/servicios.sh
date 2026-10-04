#!/usr/bin/env bash
# migracion/servicios.sh · arranca y para todo lo que hace falta esta noche, siempre igual y siempre en 127.0.0.1.
#
#   bash migracion/servicios.sh arrancar [viejo|legado|api|web|todo]   (por defecto: todo)
#   bash migracion/servicios.sh parar    [viejo|legado|api|web|todo]
#   bash migracion/servicios.sh estado
#
#   viejo   servir.py de hoy sobre una COPIA de la base (SQLite)    → 127.0.0.1:8770   la referencia
#   legado  servir.py de hoy sobre la Postgres nueva (ro_app)       → 127.0.0.1:8771   lo que Nest aún no atiende
#   api     Nest (v2/apps/api), con proxy al legado                  → 127.0.0.1:4000
#   web     Next (v2/apps/web), pasa /api a Nest                     → 127.0.0.1:3000   la app nueva entera
#
# Salidas externas APAGADAS siempre: sin RO_ENVIOS_REALES ni RO_CLICKUP_REAL, y sin bucles de avisos (nota de Astra).
# Registros en ~/RO_MIGRACION/logs, pids en ~/RO_MIGRACION/pids.
set -uo pipefail
cd "$(dirname "$0")/.."
RAIZ="$(pwd)"
FUERA="${RO_MIGRACION:-$HOME/RO_MIGRACION}"
LOGS="$FUERA/logs"; PIDS="$FUERA/pids"
mkdir -p "$LOGS" "$PIDS"
PG_URL="${DATABASE_URL:-postgresql://ro:ro@127.0.0.1:5432/ro_app}"
unset RO_ENVIOS_REALES RO_CLICKUP_REAL
export RO_AVISOS_SIN_BUCLE=1
export RO_ORIGEN_APP="http://127.0.0.1:3000,http://localhost:3000"

puerto_de() { case "$1" in viejo) echo 8770;; legado) echo 8771;; api) echo 4000;; web) echo 3000;; esac; }
vivo() { curl -s -o /dev/null -m 3 "http://127.0.0.1:$(puerto_de "$1")/$( [ "$1" = viejo ] || [ "$1" = legado ] && echo api/elegir || echo vivo)"; }

esperar() {   # hasta 120 s a que responda
  for _ in $(seq 1 60); do vivo "$1" && return 0; sleep 2; done
  echo "  ✘ $1 no responde en 127.0.0.1:$(puerto_de "$1"). Mira $LOGS/$1.log"; return 1
}

arrancar_uno() {
  local s="$1"
  if vivo "$s"; then echo "  ✔ $s ya está en 127.0.0.1:$(puerto_de "$s")"; return 0; fi
  case "$s" in
    viejo)
      [ -f "$FUERA/local.db.antes" ] || { echo "  ✘ falta $FUERA/local.db.antes (fase 1)"; return 1; }
      [ -f "$FUERA/viejo.db" ] || cp "$FUERA/local.db.antes" "$FUERA/viejo.db"
      RO_DB="$FUERA/viejo.db" nohup python3 servir.py --bind 127.0.0.1 --puerto 8770 > "$LOGS/viejo.log" 2>&1 < /dev/null &
      ;;
    legado)
      DATABASE_URL="$PG_URL" nohup python3 servir.py --bind 127.0.0.1 --puerto 8771 > "$LOGS/legado.log" 2>&1 < /dev/null &
      ;;
    api)
      (cd v2 && pnpm --filter @ro/api build > "$LOGS/api_build.log" 2>&1) || { echo "  ✘ la API no compila: $LOGS/api_build.log"; return 1; }
      # (cd y node por separado: si no, «cd && node &» deja una subshell esperando y la terminal no vuelve)
      (cd v2/apps/api || exit 1
       DATABASE_URL="$PG_URL" RO_LEGADO_URL="http://127.0.0.1:8771" PORT=4000 HOST=127.0.0.1 RO_IDENTIDAD=local \
         nohup node dist/main.js > "$LOGS/api.log" 2>&1 < /dev/null &
       echo $! > "$PIDS/api.pid")
      esperar api; return $?
      ;;
    web)
      (cd v2/apps/web || exit 1
       RO_API_URL="http://127.0.0.1:4000" nohup pnpm exec next dev -H 127.0.0.1 -p 3000 > "$LOGS/web.log" 2>&1 < /dev/null &
       echo $! > "$PIDS/web.pid")
      esperar web; return $?
      ;;
  esac
  echo $! > "$PIDS/$s.pid"
  esperar "$s"
}

parar_uno() {
  local f="$PIDS/$1.pid"
  if [ -f "$f" ]; then
    kill "$(cat "$f")" 2>/dev/null; sleep 1
    # next dev y pnpm dejan hijos: se paran por el puerto (solo lo que escucha en 127.0.0.1)
    local quien; quien=$(lsof -nP -iTCP@127.0.0.1:"$(puerto_de "$1")" -sTCP:LISTEN -t 2>/dev/null)
    [ -n "$quien" ] && kill $quien 2>/dev/null
    rm -f "$f"
  fi
  echo "  · $1 parado"
}

orden="${1:-estado}"; que="${2:-todo}"
[ "$que" = todo ] && lista="viejo legado api web" || lista="$que"
case "$orden" in
  arrancar)
    (cd v2 && docker compose up -d postgres > "$LOGS/postgres.log" 2>&1) || echo "  ⚠ docker compose up postgres falló: $LOGS/postgres.log"
    fallos=0; for s in $lista; do arrancar_uno "$s" || fallos=$((fallos+1)); done; exit $fallos ;;
  parar)
    for s in $lista; do parar_uno "$s"; done ;;
  estado)
    for s in viejo legado api web; do vivo "$s" && echo "  ✔ $s en 127.0.0.1:$(puerto_de "$s")" || echo "  ✘ $s parado"; done ;;
  *) echo "uso: bash migracion/servicios.sh arrancar|parar|estado [viejo|legado|api|web|todo]"; exit 2 ;;
esac

#!/usr/bin/env bash
# migracion/servicios.sh · arranca y para todo lo que hace falta esta noche, siempre igual y siempre en 127.0.0.1.
#
#   bash migracion/servicios.sh arrancar [viejo|legado|api|web|todo]   (por defecto: todo)
#   bash migracion/servicios.sh parar    [viejo|legado|api|web|todo]
#   bash migracion/servicios.sh reiniciar legado api web     (varios a la vez; lo usa puerta.sh antes de comparar)
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
# Reloj de negocio FIJO toda la noche (la misma hora que las fotos de capturar.mjs). Si no, lo grabado a las 23:00
# no se parece a lo de las 3:00: cambia «hoy», salen los resúmenes del día de las 8:30… y las puertas dan diferencias
# que no son fallos. permisos.py, avisos.py, envios.py y sincronia.py ya lo respetan; lo que se porte a Nest, también.
export RO_RELOJ="${RO_RELOJ:-2026-10-05T07:30}"
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
      # La referencia corre desde la copia congelada de F1 (~/RO_MIGRACION/ref): los arreglos de F5.10 en servir.py
      # no deben cambiar «la app de hoy». Sin copia, del árbol de trabajo (y avisa).
      [ -f "$FUERA/ref/servir.py" ] || echo "  ⚠ falta $FUERA/ref (F1, paso 4): la referencia sale del árbol de trabajo"
      local ref="$RAIZ"; [ -f "$FUERA/ref/servir.py" ] && ref="$FUERA/ref"   # servir.py se sitúa por __file__
      RO_DB="$FUERA/viejo.db" nohup python3 "$ref/servir.py" --bind 127.0.0.1 --puerto 8770 > "$LOGS/viejo.log" 2>&1 < /dev/null &
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
      # Compilada (next build + next start), como irá en la nube: las puertas miden velocidad y «next dev» compila
      # cada página la primera vez. RO_WEB_DEV=1 para trabajar con recarga en caliente (no vale para cerrar puertas).
      if [ -z "${RO_WEB_DEV:-}" ]; then
        (cd v2/apps/web && RO_API_URL="http://127.0.0.1:4000" pnpm exec next build > "$LOGS/web_build.log" 2>&1) \
          || { echo "  ✘ la web no compila: $LOGS/web_build.log"; return 1; }
      fi
      (cd v2/apps/web || exit 1
       RO_API_URL="http://127.0.0.1:4000" nohup pnpm exec next "$([ -n "${RO_WEB_DEV:-}" ] && echo dev || echo start)" -H 127.0.0.1 -p 3000 \
         > "$LOGS/web.log" 2>&1 < /dev/null &
       echo $! > "$PIDS/web.pid")
      esperar web; return $?
      ;;
  esac
  echo $! > "$PIDS/$s.pid"
  esperar "$s"
}

parar_uno() {
  local f="$PIDS/$1.pid"
  [ -f "$f" ] && kill "$(cat "$f")" 2>/dev/null && sleep 1
  rm -f "$f"
  # Siempre también por el puerto (solo lo que escucha en 127.0.0.1): next dev y pnpm dejan hijos, y un servicio
  # arrancado a mano o en otra vuelta no tiene fichero de pid.
  local quien; quien=$(lsof -nP -iTCP@127.0.0.1:"$(puerto_de "$1")" -sTCP:LISTEN -t 2>/dev/null)
  if [ -n "$quien" ]; then kill $quien 2>/dev/null; for _ in 1 2 3 4 5; do vivo "$1" || break; sleep 1; done; fi
  if vivo "$1"; then   # lsof no siempre ve los hijos (next-server): por su línea de órdenes, que lleva el puerto
    case "$1" in
      web) pkill -f "next (dev|start) -H 127.0.0.1 -p 3000" ;;
      viejo|legado) pkill -f "servir.py --bind 127.0.0.1 --puerto $(puerto_de "$1")" ;;
    esac
    for _ in 1 2 3 4 5; do vivo "$1" || break; sleep 1; done
  fi
  echo "  · $1 parado"
}

orden="${1:-estado}"; que="${2:-todo}"
[ "$que" = todo ] && lista="viejo legado api web" || lista="${*:2}"
case "$orden" in
  arrancar)
    (cd v2 && docker compose up -d postgres > "$LOGS/postgres.log" 2>&1) || echo "  ⚠ docker compose up postgres falló: $LOGS/postgres.log"
    fallos=0; for s in $lista; do arrancar_uno "$s" || fallos=$((fallos+1)); done; exit $fallos ;;
  parar)
    for s in $lista; do parar_uno "$s"; done ;;
  reiniciar)   # tras tocar código: si no, «arrancar» ve el servicio vivo y lo deja con el código de antes
    for s in $lista; do parar_uno "$s"; done
    fallos=0; for s in $lista; do arrancar_uno "$s" || fallos=$((fallos+1)); done; exit $fallos ;;
  estado)
    for s in viejo legado api web; do vivo "$s" && echo "  ✔ $s en 127.0.0.1:$(puerto_de "$s")" || echo "  ✘ $s parado"; done ;;
  *) echo "uso: bash migracion/servicios.sh arrancar|parar|reiniciar|estado [viejo|legado|api|web|todo]"; exit 2 ;;
esac

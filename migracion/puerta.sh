#!/usr/bin/env bash
# migracion/puerta.sh · la PUERTA de cada fase en una orden. Dice VERDE o ROJO y deja el detalle en
# ~/RO_MIGRACION/puertas/<fase>.md. Cursor no da una fase por pasada sin «VERDE» de esta orden.
#
#   bash migracion/puerta.sh f1   referencia grabada (contrato, vectores, fotos, casos de escritura)
#   bash migracion/puerta.sh f2   la app de hoy sobre Postgres responde y escribe IGUAL que sobre SQLite
#   bash migracion/puerta.sh f3   la app nueva entera (Next → Nest → legado) igual que la de hoy: API, escrituras, fotos, baterías
#   bash migracion/puerta.sh f4   motor de permisos en TypeScript: 100 % de los vectores
#   bash migracion/puerta.sh f5   igual que f3 (se pasa después de mover cada grupo de rutas a Nest)
#   bash migracion/puerta.sh f6   igual que f3 (se pasa después de cada pantalla en React)
#   bash migracion/puerta.sh f7   igual que f3 contra los contenedores + informe de la noche escrito
#   --rapido   (f3/f5/f6) contrato sin recorrer todos los clientes y fotos solo de escritorio: para iterar, no para cerrar
#
# Necesita los servicios en marcha (bash migracion/servicios.sh arrancar). Las pruebas de escritura usan bases y
# puertos propios (8780, 8781, 4001) y nunca tocan ro_app ni local.db.
set -uo pipefail
cd "$(dirname "$0")/.."
RAIZ="$(pwd)"
FUERA="${RO_MIGRACION:-$HOME/RO_MIGRACION}"
export RO_MIGRACION="$FUERA"
FASE="${1:-}"; RAPIDO=""; [ "${2:-}" = "--rapido" ] && RAPIDO=1
mkdir -p "$FUERA/puertas" "$FUERA/logs"
INFORME="$FUERA/puertas/$FASE.md"
unset RO_ENVIOS_REALES RO_CLICKUP_REAL
export RO_AVISOS_SIN_BUCLE=1
ROJOS=()
echo "# Puerta $FASE · $(date '+%d-%m-%Y %H:%M')" > "$INFORME"

paso() {   # paso "nombre" orden…  → apunta ✔/✘ y la cola de la salida
  local nombre="$1"; shift
  local log="$FUERA/logs/puerta_${FASE}_$(echo "$nombre" | tr -c 'a-zA-Z0-9' '_').log"
  if "$@" > "$log" 2>&1; then
    echo "  ✔ $nombre"; printf -- "- ✔ %s\n" "$nombre" >> "$INFORME"
  else
    echo "  ✘ $nombre  (detalle: $log)"; ROJOS+=("$nombre")
    { printf -- "- ✘ %s\n\n\`\`\`\n" "$nombre"; tail -40 "$log"; printf "\`\`\`\n"; } >> "$INFORME"
  fi
}
existe() { [ -e "$1" ] && [ -n "$(ls -A "$1" 2>/dev/null || echo x)" ]; }
pg_url() { echo "postgresql://ro:ro@127.0.0.1:5432/$1"; }
esperar_puerto() { for _ in $(seq 1 60); do curl -s -o /dev/null -m 2 "http://127.0.0.1:$1/$2" && return 0; sleep 2; done; return 1; }
parar_puerto() { local p; p=$(lsof -nP -iTCP@127.0.0.1:"$1" -sTCP:LISTEN -t 2>/dev/null); [ -n "$p" ] && kill $p 2>/dev/null; sleep 1; }

# --- escrituras: los mismos casos contra una copia limpia en cada lado ------------------------------------------
escritura_ref() {   # la app de hoy sobre SQLite (la referencia)
  parar_puerto 8780
  cp "$FUERA/local.db.antes" "$FUERA/esc_viejo.db"
  RO_DB="$FUERA/esc_viejo.db" nohup python3 servir.py --bind 127.0.0.1 --puerto 8780 > "$FUERA/logs/esc_viejo.log" 2>&1 < /dev/null &
  esperar_puerto 8780 api/elegir || return 1
  rm -rf "$FUERA/escritura/viejo"
  python3 migracion/contrato_escritura.py ejecutar --base http://127.0.0.1:8780 --db "$FUERA/esc_viejo.db" \
    --casos "$FUERA/casos_escritura.json" --salida "$FUERA/escritura/viejo"; local r=$?
  parar_puerto 8780; return $r
}
escritura_lado() {   # $1 = pg (legado directo) | nuevo (Nest con proxy al legado)
  parar_puerto 8781; parar_puerto 4001
  python3 migracion/contrato_escritura.py base-limpia ro_esc || return 1
  DATABASE_URL="$(pg_url ro_esc)" nohup python3 servir.py --bind 127.0.0.1 --puerto 8781 > "$FUERA/logs/esc_legado.log" 2>&1 < /dev/null &
  esperar_puerto 8781 api/elegir || return 1
  local base=http://127.0.0.1:8781
  if [ "$1" = nuevo ]; then
    (cd v2 && pnpm --filter @ro/api build) || return 1
    (cd v2/apps/api || exit 1
     DATABASE_URL="$(pg_url ro_esc)" RO_LEGADO_URL=http://127.0.0.1:8781 PORT=4001 HOST=127.0.0.1 RO_IDENTIDAD=local \
       nohup node dist/main.js > "$FUERA/logs/esc_api.log" 2>&1 < /dev/null &)
    esperar_puerto 4001 vivo || return 1
    base=http://127.0.0.1:4001
  fi
  rm -rf "$FUERA/escritura/$1"
  python3 migracion/contrato_escritura.py ejecutar --base "$base" --db ro_esc --casos "$FUERA/casos_escritura.json" \
    --salida "$FUERA/escritura/$1"; local r=$?
  parar_puerto 8781; parar_puerto 4001; return $r
}
escritura() { escritura_ref && escritura_lado "$1" && python3 migracion/contrato_escritura.py comparar "$FUERA/escritura/viejo" "$FUERA/escritura/$1"; }

# --- contrato de lectura y fotos ---------------------------------------------------------------------------------
contrato() {   # $1 = puerto, $2 = nombre de la grabación
  rm -rf "$FUERA/contrato/$2"
  python3 migracion/contrato.py grabar --base "http://127.0.0.1:$1" --salida "$FUERA/contrato/$2" --ver-como ${RAPIDO:+--rapido} \
    && python3 migracion/contrato.py comparar "$FUERA/contrato/viejo" "$FUERA/contrato/$2" --excepciones "$FUERA/excepciones.txt"
}
fotos() {   # $1 = puerto
  rm -rf "$FUERA/capturas/nuevo"
  (cd v2/tools/capturas && node capturar.mjs --base "http://127.0.0.1:$1" --modo nuevo --salida "$FUERA/capturas/nuevo" ${RAPIDO:+--solo-escritorio} \
    && node comparar.mjs "$FUERA/capturas/viejo" "$FUERA/capturas/nuevo" --umbral 0.5 ${RAPIDO:+--solo-escritorio})
}
casos_cubren() {   # cada POST de servir.py tiene al menos un caso que funciona y uno que se deniega
  python3 - "$FUERA/casos_escritura.json" <<'PY'
import json, sys
casos = json.load(open(sys.argv[1]))
rutas = [r["ruta"] for r in json.load(open("migracion/inventario/rutas_api.json")) if r["metodo"] == "POST"]
vistas = {c["ruta"] for c in casos}
falta = [r for r in rutas if not any(v == r or (r.endswith("/") and v.startswith(r)) for v in vistas)]
print(f"{len(casos)} casos; POST de servir.py sin caso: {falta or 'ninguno'}")
sys.exit(1 if falta else 0)
PY
}
baterias() {   # $1 = puerto. migracion/baterias.sh (lo monta Cursor en la fase 1) lanza TODAS las baterías que admiten puerto
  if [ -f migracion/baterias.sh ]; then bash migracion/baterias.sh "$1"; else python3 pruebas_e0.py --puerto "$1"; fi
}

restauracion() {   # ensayo de recuperación (nota de Astra): volcar ro_app, restaurarla en otra base y que responda igual
  local dump="$FUERA/ro_app.dump"
  pg_dump --format=custom --no-owner --file "$dump" "$(pg_url ro_app)" || return 1
  python3 - <<'PY' || return 1
import psycopg
with psycopg.connect("postgresql://ro:ro@127.0.0.1:5432/postgres", autocommit=True) as c:
    c.execute('DROP DATABASE IF EXISTS ro_restaurada WITH (FORCE)'); c.execute('CREATE DATABASE ro_restaurada')
PY
  pg_restore --no-owner --dbname "$(pg_url ro_restaurada)" "$dump" || return 1
  parar_puerto 8782
  DATABASE_URL="$(pg_url ro_restaurada)" nohup python3 servir.py --bind 127.0.0.1 --puerto 8782 > "$FUERA/logs/restaurada.log" 2>&1 < /dev/null &
  esperar_puerto 8782 api/elegir || return 1
  contrato 8782 restaurada; local r=$?
  parar_puerto 8782; return $r
}

case "$FASE" in
  f1)
    paso "copia de seguridad (local.db.antes)" test -s "$FUERA/local.db.antes"
    paso "contrato de la app de hoy grabado" existe "$FUERA/contrato/viejo"
    paso "vectores de permisos grabados" existe "$FUERA/vectores"
    paso "fotos de la app de hoy" existe "$FUERA/capturas/viejo"
    paso "casos de escritura cubren todos los POST" casos_cubren
    paso "escrituras de referencia (SQLite)" escritura_ref
    paso "notas de la noche" test -s migracion/NOTAS_NOCHE.md
    paso "baterías verdes contra la app de hoy" baterias 8770
    ;;
  f2)
    paso "base al día (prisma migrate status)" bash -c "cd v2 && DATABASE_URL='$(pg_url ro_app)' pnpm --filter @ro/db exec prisma migrate status"
    paso "versión vigente de data publicada" bash -c "DATABASE_URL='$(pg_url ro_app)' python3 despliegue/publicacion.py versiones | grep -qi vigente"
    paso "contrato: hoy sobre Postgres = hoy sobre SQLite" contrato 8771 pg
    paso "escrituras: hoy sobre Postgres = hoy sobre SQLite" escritura pg
    ;;
  f3|f5|f6|f7)
    PUERTO=3000
    [ "$FASE" = f7 ] && paso "informe de la noche escrito" test -s migracion/INFORME_NOCHE.md
    [ "$FASE" = f7 ] && paso "copia de la base restaurada y comprobada" restauracion
    paso "v2 compila, pasa sus pruebas y su lint" bash -c "cd v2 && pnpm build && pnpm test && pnpm lint"
    paso "contrato: app nueva = app de hoy" contrato "$PUERTO" nuevo
    paso "escrituras: app nueva = app de hoy" escritura nuevo
    paso "fotos: cada pantalla ≤ 0,5 %" fotos "$PUERTO"
    paso "batería pruebas_e0 contra la app nueva" baterias "$PUERTO"
    ;;
  f4)
    paso "permisos en TypeScript: 100 % de los vectores" bash -c "cd v2 && RO_VECTORES='$FUERA/vectores' pnpm --filter @ro/permisos test"
    ;;
  *) echo "uso: bash migracion/puerta.sh f1|f2|f3|f4|f5|f6|f7 [--rapido]"; exit 2 ;;
esac

echo
if [ ${#ROJOS[@]} -eq 0 ]; then
  echo "VERDE · puerta $FASE${RAPIDO:+ (rápida: no vale para cerrar la fase)}"; echo -e "\n**VERDE**" >> "$INFORME"; exit 0
else
  echo "ROJO · puerta $FASE: ${#ROJOS[@]} sin pasar (${ROJOS[*]}). Detalle: $INFORME"; echo -e "\n**ROJO**" >> "$INFORME"; exit 1
fi

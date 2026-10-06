#!/usr/bin/env bash
# migracion/pruebas_rastro_dos_escritores.sh · F5.1 · Nest y servir.py escriben en el MISMO rastro a la vez y la cadena
# de huellas sigue entera. Solo sobre la base de pruebas ro_esc (base-limpia la rehace); nunca ro_app.
#   bash migracion/pruebas_rastro_dos_escritores.sh      → rc=0 si la cadena está entera y no se pierde ninguna fila
set -uo pipefail
cd "$(dirname "$0")/.."
FUERA="${RO_MIGRACION:-$HOME/RO_MIGRACION}"
LOGS="$FUERA/logs"; mkdir -p "$LOGS"
URL="postgresql://ro:ro@127.0.0.1:5432/ro_esc"
unset RO_ENVIOS_REALES RO_CLICKUP_REAL
export RO_AVISOS_SIN_BUCLE=1 RO_SIN_LLAVES=1 RO_RELOJ="${RO_RELOJ:-2026-10-05T07:30}"
N="${RO_DOS_ESCRITORES_N:-25}"
LEG=8784; API=4004

parar() { for p in $LEG $API; do lsof -ti "tcp:$p" -sTCP:LISTEN 2>/dev/null | xargs -r kill 2>/dev/null; done; }
esperar() { for _ in $(seq 1 60); do curl -s -o /dev/null "http://127.0.0.1:$1/$2" && return 0; sleep 1; done; echo "✘ no arranca :$1"; return 1; }
trap parar EXIT
parar

python3 migracion/contrato_escritura.py base-limpia ro_esc || exit 1
DATABASE_URL="$URL" nohup python3 servir.py --bind 127.0.0.1 --puerto $LEG > "$LOGS/dos_escritores_legado.log" 2>&1 < /dev/null &
esperar $LEG api/elegir || exit 1
(cd v2 && pnpm --filter @ro/api build > "$LOGS/dos_escritores_build.log" 2>&1) || { echo "✘ la API no compila"; exit 1; }
(cd v2/apps/api && DATABASE_URL="$URL" RO_LEGADO_URL="http://127.0.0.1:$LEG" PORT=$API HOST=127.0.0.1 RO_IDENTIDAD=local \
  nohup node dist/main.js > "$LOGS/dos_escritores_api.log" 2>&1 < /dev/null &)
esperar $API vivo || exit 1

# Alguien a quien mirar en «ver como»: una persona activa que no sea tomas (solo el id, sin datos).
COMO=$(curl -s -H 'X-RO-Yo: tomas' "http://127.0.0.1:$LEG/api/sesion" | python3 -c '
import json, sys
s = json.load(sys.stdin)
print(next(p["id"] for p in s["datos"]["personas"] if p["id"] != "tomas"))')
[ -n "$COMO" ] || { echo "✘ no hay a quién mirar en «ver como»"; exit 1; }

antes=$(psql "$URL" -Atc "SELECT count(*) FROM registro WHERE coleccion = 'sesion'")
desde=$(psql "$URL" -Atc "SELECT coalesce(max(id), 0) FROM registro")
# A la vez: N sesiones en «ver como» por Nest (escribe RastroService) y N por servir.py (escribe Python).
fallos=0
pids=()
: > "$LOGS/dos_escritores_codigos.txt"
for i in $(seq 1 "$N"); do
  for p in $API $LEG; do
    curl -s -o /dev/null -w '%{http_code}\n' -H 'X-RO-Yo: tomas' -H "X-RO-Como: $COMO" "http://127.0.0.1:$p/api/sesion" \
      >> "$LOGS/dos_escritores_codigos.txt" &
    pids+=($!)
  done
done
for pid in "${pids[@]}"; do wait "$pid" || fallos=$((fallos + 1)); done
malos=$(grep -vc '^200$' "$LOGS/dos_escritores_codigos.txt" || true)
despues=$(psql "$URL" -Atc "SELECT count(*) FROM registro WHERE coleccion = 'sesion'")
nuevas=$((despues - antes))
huecos=$(psql "$URL" -Atc "SELECT count(*) FROM registro r LEFT JOIN registro_huellas h ON h.id = r.id WHERE h.id IS NULL AND r.id > $desde")
# La cadena la comprueba servir.py (verificar_rastro), no el código de Nest.
cadena=$(curl -s -H 'X-RO-Yo: tomas' "http://127.0.0.1:$LEG/api/rastro/verificar" | python3 -c '
import json, sys
r = json.load(sys.stdin)
print("ok" if r.get("ok") is True else "rota en la fila %s" % r.get("primera_fila_rota"))')

echo "peticiones: $((2 * N)) · no 200: $malos · curl fallidos: $fallos · filas de sesión nuevas: $nuevas · sin huella: $huecos · cadena: $cadena"
[ "$malos" = 0 ] && [ "$fallos" = 0 ] && [ "$nuevas" = $((2 * N)) ] && [ "$huecos" = 0 ] && [ "$cadena" = ok ] \
  && { echo "✔ dos escritores, una cadena entera"; exit 0; }
echo "✘ el rastro con dos escritores no cuadra"; exit 1

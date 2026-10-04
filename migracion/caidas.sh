#!/usr/bin/env bash
# migracion/caidas.sh · la app nueva aguanta golpes y se levanta sola. Contra los servicios de la noche
# (Next 3000 → Nest 4000 → legado 8771 → Postgres). Sale con 1 si algo falla. Lo usa puerta.sh (f3, f5, f6, f7).
#
#   1. Ráfaga: 200 peticiones, 20 a la vez, mezclando rutas → ningún 5xx ni cuelgue.
#   2. Peticiones raras → respuesta limpia (4xx), nunca 500 ni la pila de errores, y el servidor sigue vivo:
#      ruta que no existe, JSON roto, cuerpo de 3 MB, Host ajeno, POST sin X-RO-App.
#   3. Se cae el legado → Nest y Next siguen vivos y responden 502 con mensaje en < 5 s (no se quedan colgados);
#      vuelve el legado → todo responde otra vez en < 60 s sin reiniciar nada más.
#   4. Se cae Nest → al volver, Next responde otra vez sin reiniciarlo.
#   5. Postgres se reinicia → legado y Nest vuelven a leer en < 60 s sin reiniciarlos.
#      (Solo si Postgres corre en el Docker de v2; si no, se salta con aviso.)
set -uo pipefail
cd "$(dirname "$0")/.."
WEB=http://127.0.0.1:3000; API=http://127.0.0.1:4000
YO="${RO_YO_PRUEBA:-$(curl -s -m 10 http://127.0.0.1:8771/api/elegir | python3 -c 'import json,sys;print(json.load(sys.stdin)["personas"][0]["id"])' 2>/dev/null)}"
# Fallos ya conocidos de la app de hoy que aún no se han arreglado: una línea por fallo en
# ~/RO_MIGRACION/excepciones_solidez.txt con el principio de su descripción y «# L-n motivo». Salen como ⚠ y van al
# informe, pero no tumban la puerta (si no, un fallo heredado bloquearía toda la noche).
CONOCIDOS="${RO_MIGRACION:-$HOME/RO_MIGRACION}/excepciones_solidez.txt"
fallos=0; conocidos=0
bien() { echo "  ✔ $1"; }
mal()  {
  local l; while IFS= read -r l; do l="${l%%#*}"; l="${l%"${l##*[! ]}"}"
    if [ -n "$l" ] && [[ "$1" == "$l"* ]]; then echo "  ⚠ $1  (conocido: $(grep -F "$l" "$CONOCIDOS" | head -1 | sed 's/.*#//'))"; conocidos=$((conocidos+1)); return; fi
  done < <(cat "$CONOCIDOS" 2>/dev/null)
  echo "  ✘ $1"; fallos=$((fallos+1)); }
codigo() { curl -s -o /tmp/ro_caida_cuerpo -w '%{http_code}' -m "${T:-10}" "$@"; }
hasta() { local s=$1; shift; for _ in $(seq 1 "$s"); do "$@" && return 0; sleep 1; done; return 1; }
responde() { [ "$(codigo -H "X-RO-Yo: $YO" "$WEB/api/sesion")" = 200 ]; }

[ -n "$YO" ] || { echo "✘ el legado (8771) no responde: bash migracion/servicios.sh arrancar"; exit 1; }
responde || { echo "✘ la app nueva no responde en $WEB: bash migracion/servicios.sh arrancar"; exit 1; }

echo "1 · Ráfaga"
python3 - "$WEB" "$YO" <<'PY' && bien "200 peticiones sin 5xx ni cuelgues" || mal "la ráfaga dio errores (arriba)"
import concurrent.futures as cf, sys, time, urllib.request, urllib.error
web, yo = sys.argv[1], sys.argv[2]
rutas = ["/api/sesion", "/api/indicadores", "/api/contadores", "/api/avisos", "/api/perfil", "/", "/vivo", "/api/buscar/indice"]
def una(i):
    req = urllib.request.Request(web + rutas[i % len(rutas)], headers={"X-RO-Yo": yo})
    try:
        with urllib.request.urlopen(req, timeout=20) as r: return r.status
    except urllib.error.HTTPError as e: return e.code
    except Exception as e: return f"cuelgue: {e}"
t = time.time()
with cf.ThreadPoolExecutor(20) as ex: res = list(ex.map(una, range(200)))
malos = [r for r in res if not isinstance(r, int) or r >= 500]
print(f"    {len(res)} peticiones en {time.time()-t:.1f} s; malas: {len(malos)} {sorted(set(map(str, malos)))[:5]}")
sys.exit(1 if malos else 0)
PY

echo "2 · Peticiones raras"
raro() {   # $1 = descripción, resto = curl
  local d="$1"; shift; local c; c=$(codigo "$@")
  if [ "$c" -ge 500 ] || [ "$c" = 000 ]; then mal "$d → $c"
  elif grep -qiE 'Traceback|at [A-Za-z]+ \(|node_modules|\.py", line' /tmp/ro_caida_cuerpo; then mal "$d → enseña la pila de errores"
  else bien "$d → $c"; fi
}
raro "ruta que no existe" -H "X-RO-Yo: $YO" "$WEB/api/no-existe-$$"
raro "JSON roto" -X POST -H "X-RO-Yo: $YO" -H "X-RO-App: 1" -H 'Content-Type: application/json' -H "Origin: $WEB" --data '{roto' "$WEB/api/preferencias"
head -c 3000000 /dev/zero | tr '\0' 'a' > /tmp/ro_caida_grande
raro "cuerpo de 3 MB" -X POST -H "X-RO-Yo: $YO" -H "X-RO-App: 1" -H 'Content-Type: application/json' -H "Origin: $WEB" --data-binary @/tmp/ro_caida_grande "$WEB/api/preferencias"
[ "$(codigo -H 'Host: malo.example' "$API/api/sesion")" = 403 ] && bien "Host ajeno → 403" || mal "Host ajeno no da 403"
c=$(codigo -X POST -H "X-RO-Yo: $YO" -H 'Content-Type: application/json' --data '{}' "$WEB/api/preferencias")
[ "$c" -ge 400 ] && [ "$c" -lt 500 ] && bien "POST sin X-RO-App → $c" || mal "POST sin X-RO-App → $c (debería denegarse)"
responde && bien "sigue vivo después" || mal "no responde después de las peticiones raras"

echo "3 · Se cae el legado"
bash migracion/servicios.sh parar legado >/dev/null
c=$(T=6 codigo -H "X-RO-Yo: $YO" "$WEB/api/sesion")
[ "$c" = 502 ] || [ "$c" = 503 ] && bien "sin legado: $c en < 6 s" || mal "sin legado responde $c (debería ser 502/503 rápido)"
[ "$(codigo "$API/vivo")" = 200 ] && bien "Nest sigue vivo" || mal "Nest se ha caído con el legado"
bash migracion/servicios.sh arrancar legado >/dev/null
hasta 60 responde && bien "vuelve el legado: todo responde sin reiniciar Nest ni Next" || mal "no se recupera tras volver el legado"

echo "4 · Se cae Nest"
bash migracion/servicios.sh parar api >/dev/null
c=$(T=6 codigo -H "X-RO-Yo: $YO" "$WEB/api/sesion"); [ "$c" != 000 ] && bien "sin Nest, Next responde $c sin colgarse" || mal "sin Nest, Next se queda colgado"
bash migracion/servicios.sh arrancar api >/dev/null
hasta 60 responde && bien "vuelve Nest: Next responde sin reiniciarlo" || mal "Next no se recupera tras volver Nest"

echo "5 · Se reinicia Postgres"
if (cd v2 && docker compose ps postgres 2>/dev/null | grep -q Up); then
  (cd v2 && docker compose restart postgres >/dev/null 2>&1)
  hasta 60 responde && bien "legado vuelve a leer tras reiniciar Postgres" || mal "el legado no se recupera solo tras reiniciar Postgres"
  hasta 60 bash -c "[ \"\$(curl -s -o /dev/null -w '%{http_code}' $API/vivo)\" = 200 ]" && bien "Nest vuelve a leer" || mal "Nest no se recupera solo tras reiniciar Postgres"
else echo "  · Postgres no está en el Docker de v2: me salto esta prueba"; fi

rm -f /tmp/ro_caida_cuerpo /tmp/ro_caida_grande
echo; [ $fallos = 0 ] && echo "VERDE · aguanta golpes ($conocidos fallos conocidos de la app de hoy, ver $CONOCIDOS)" || { echo "ROJO · $fallos fallos"; exit 1; }

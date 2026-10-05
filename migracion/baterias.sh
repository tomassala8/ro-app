#!/usr/bin/env bash
# migracion/baterias.sh · todas las baterías que admiten un servidor ya arrancado, más las que corren sin servidor
# sobre el checkout. Sale 1 si falla alguna que HOY pasa contra la app de hoy (las que ya fallan hoy están en
# ~/RO_MIGRACION/baterias_heredadas.txt, una por línea «<clave>  # motivo», y no cuentan). Nada escribe en local.db:
# el servidor del puerto que recibe trabaja sobre una copia (servicios.sh / puerta.sh).
#   bash migracion/baterias.sh 8770            # contra la app de hoy (referencia)
#   bash migracion/baterias.sh 3000            # contra la app nueva (puerta f3/f5/f6)
#   RO_BATERIAS_SOLO=e0 bash migracion/baterias.sh 8770   # una sola, por clave
set -uo pipefail
cd "$(dirname "$0")/.."
PUERTO="${1:?uso: bash migracion/baterias.sh <puerto>}"
FUERA="${RO_MIGRACION:-$HOME/RO_MIGRACION}"; mkdir -p "$FUERA/logs/baterias"
HEREDADAS="$FUERA/baterias_heredadas.txt"; touch "$HEREDADAS"
export RO_SIN_LLAVES=1 RO_AVISOS_SIN_BUCLE=1 RO_RELOJ="${RO_RELOJ:-2026-10-05T07:30}"
unset RO_ENVIOS_REALES RO_CLICKUP_REAL
ROJAS=(); HEREDADAS_ROJAS=(); VERDES=0
con_tope() {   # con_tope <segundos> <orden…>  (no hay «timeout» en el Mac)
  local s="$1"; shift
  "$@" & local pid=$!
  ( sleep "$s"; kill -TERM "$pid" 2>/dev/null; sleep 5; kill -KILL "$pid" 2>/dev/null ) & local vigia=$!
  wait "$pid" 2>/dev/null; local rc=$?
  kill "$vigia" 2>/dev/null; wait "$vigia" 2>/dev/null
  return $rc
}
bateria() {   # bateria <clave> <segundos> <orden…>
  local clave="$1" s="$2"; shift 2
  [ -n "${RO_BATERIAS_SOLO:-}" ] && [ "$RO_BATERIAS_SOLO" != "$clave" ] && return 0
  local log="$FUERA/logs/baterias/${clave}.log"
  if con_tope "$s" "$@" > "$log" 2>&1; then
    VERDES=$((VERDES + 1)); echo "  ✔ $clave"
  elif grep -q "^$clave  " "$HEREDADAS"; then
    HEREDADAS_ROJAS+=("$clave"); echo "  ⚠ $clave (ya fallaba hoy: $(grep "^$clave  " "$HEREDADAS" | sed 's/^[^#]*# *//'))"
  else
    ROJAS+=("$clave"); echo "  ✘ $clave  (detalle: $log)"
  fi
}
echo "Baterías contra 127.0.0.1:$PUERTO · $(date '+%d-%m-%Y %H:%M')"
# --- contra el puerto -------------------------------------------------------------------------------------------
bateria e0 600 python3 pruebas_e0.py --puerto "$PUERTO"
# pantallas con Chrome sin cabeza (Playwright); el puerto va como primer argumento posicional
bateria m20_m22 900 python3 fuentes_personas/probar_m20_m22.py "$PUERTO"
bateria m10_m11 900 python3 fuentes_produccion/probar_equipo.py "$PUERTO"
bateria m13_m15 900 python3 fuentes_reuniones/probar_m13_m15.py "$PUERTO"
bateria m14 900 python3 fuentes_incidencias/probar_incidencias.py "$PUERTO"
bateria L-01 120 python3 migracion/pruebas_L-01.py --puerto "$PUERTO"
bateria L-21 120 python3 migracion/pruebas_L-21.py --puerto "$PUERTO"
bateria N-24 300 python3 migracion/pruebas_N-24.py
# --- sin servidor: la entrega del 4-oct ----------------------------------------------------------------------------
bateria seguridad_aisladas 900 python3 pruebas_seguridad.py --aisladas
bateria solidez_tuberia 1200 python3 despliegue/pruebas_noche.py --solo-solidez --sin-red --sin-avisos
# --- sin servidor: funciones del 4-oct (INTEGRAR.md) ------------------------------------------------------------
for f in fuentes_consejos/cerebros/probar_cerebros.py fuentes_consejos/cerebros/probar_en_app.py fuentes_diagnosticos/probar_diagnosticos.py fuentes_riesgo/probar_riesgo.py fuentes_contexto/probar_contexto.py fuentes/probar_lectura.py; do
  [ -f "$f" ] && bateria "$(basename "$f" .py)" 300 python3 "$f"
done
# --- sin servidor: las focalizadas de Astra (NOTA_ASTRA.md:42-51) ------------------------------------------------
for f in probar_triaje_atomico_445.py probar_triaje_ind_445B.py probar_metodo_evidencia_452.py; do
  [ -f "$f" ] && bateria "$(basename "$f" .py)" 300 python3 "$f"
done
# --- sin servidor: pruebas DOM pruebas_*.cjs de la raíz (DOM simulado, sin dependencias) ---------------------------
# Fuera: las que leen rutas del Mac o un servidor, y las dos que la entrega ya da por rotas (243 y 508).
for f in pruebas_*.cjs; do
  case "$f" in pruebas_captacion_compacta_243.cjs|pruebas_matriz_paid_508.cjs) continue;; esac
  grep -q -E '/Users/|127\.0\.0\.1|localhost' "$f" && continue
  bateria "$(basename "$f" .cjs)" 120 node "$f"
done
echo "Verdes: $VERDES · heredadas en rojo: ${#HEREDADAS_ROJAS[@]} · ROJAS: ${#ROJAS[@]}${ROJAS:+ → ${ROJAS[*]}}"
[ ${#ROJAS[@]} -eq 0 ]

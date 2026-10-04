#!/usr/bin/env bash
# migracion/noche.sh · lanza a Cursor (orden de terminal «cursor-agent») con el prompt de la noche y lo VUELVE A LANZAR
# cada vez que termina una vuelta, hasta que migracion/PROGRESO.md diga «ESTADO: TERMINADO» o llegue la hora.
#
#   bash migracion/noche.sh                    # 8 horas desde ahora, modelo por defecto
#   RO_HORAS=7 RO_MODELO=<modelo> bash migracion/noche.sh
#   RO_AGENTE="cursor-agent -p --force --model {MODELO}" bash migracion/noche.sh   # si tu versión usa otras opciones
#
# Mantiene el Mac despierto (caffeinate) mientras dura. Registros: ~/RO_MIGRACION/logs/vuelta_NNN.log.
# Para pararlo: Ctrl+C (Cursor termina la vuelta en curso; el cuaderno queda como esté y se puede seguir mañana).
set -uo pipefail
cd "$(dirname "$0")/.."
RAIZ="$(pwd)"
FUERA="${RO_MIGRACION:-$HOME/RO_MIGRACION}"; LOGS="$FUERA/logs"; mkdir -p "$LOGS"
HORAS="${RO_HORAS:-8}"
MODELO="${RO_MODELO:-claude-fable-5-1}"
PROMPT="$RAIZ/migracion/PROMPT_NOCHE.md"
CUADERNO="$RAIZ/migracion/PROGRESO.md"

# --- la orden de Cursor ----------------------------------------------------------------------------------------
if [ -n "${RO_AGENTE:-}" ]; then AGENTE="${RO_AGENTE//\{MODELO\}/$MODELO}"
elif command -v cursor-agent >/dev/null; then AGENTE="cursor-agent -p --force --output-format text --model $MODELO"
else
  echo "✘ No encuentro la orden «cursor-agent» (la terminal de Cursor)."
  echo "  Instálala: curl https://cursor.com/install -fsS | bash   y entra con: cursor-agent login"
  echo "  O lánzalo desde la ventana de Cursor pegando migracion/PROMPT_NOCHE.md (ver PLAN_MAESTRO §6)."
  exit 1
fi

# --- el reloj ----------------------------------------------------------------------------------------------------
FIN=$(( $(date +%s) + HORAS * 3600 ))
RO_FIN_NOCHE="$(date -r "$FIN" '+%Y-%m-%d %H:%M' 2>/dev/null || date -d "@$FIN" '+%Y-%m-%d %H:%M')"
export RO_FIN_NOCHE RO_MIGRACION="$FUERA"
# nada sale fuera esta noche (servicios.sh y puerta.sh también lo fuerzan)
unset RO_ENVIOS_REALES RO_CLICKUP_REAL
export RO_AVISOS_SIN_BUCLE=1
# Reloj de negocio FIJO toda la noche (la misma hora que las fotos de capturar.mjs). Si no, lo grabado a las 23:00
# no se parece a lo de las 3:00: cambia «hoy», salen los resúmenes del día de las 8:30… y las puertas dan diferencias
# que no son fallos. permisos.py, avisos.py, envios.py y sincronia.py ya lo respetan; lo que se porte a Nest, también.
export RO_RELOJ="${RO_RELOJ:-2026-10-05T07:30}"

# --- el Mac despierto --------------------------------------------------------------------------------------------
if command -v caffeinate >/dev/null; then caffeinate -dimsu -w $$ & fi

echo "Noche de migración · hasta $RO_FIN_NOCHE · modelo $MODELO"
echo "Orden: $AGENTE \"<PROMPT_NOCHE.md>\""
echo "Cuaderno: $CUADERNO · registros: $LOGS"

terminado() { grep -q "^ESTADO: TERMINADO" "$CUADERNO" 2>/dev/null; }
huella() { (git rev-parse HEAD; md5 -q "$CUADERNO" 2>/dev/null || md5sum "$CUADERNO" | cut -d' ' -f1) | tr '\n' ' '; }

vuelta=0; fallos_seguidos=0; sin_avance=0
while [ "$(date +%s)" -lt "$FIN" ] && ! terminado; do
  vuelta=$((vuelta + 1))
  log="$LOGS/vuelta_$(printf %03d $vuelta).log"
  antes="$(huella)"
  echo "[$(date '+%H:%M')] vuelta $vuelta → $log"
  mensaje="$(cat "$PROMPT")"
  if [ $sin_avance -ge 2 ]; then
    mensaje="$mensaje

AVISO DEL SUPERVISOR: las dos últimas vueltas no han cambiado ni el cuaderno ni el código. Aplica ya el plan B del paso en curso (márcalo ⚠ con el motivo) y pasa al siguiente."
  fi
  # shellcheck disable=SC2086
  $AGENTE "$mensaje" > "$log" 2>&1 < /dev/null
  codigo=$?
  despues="$(huella)"
  if [ $codigo -ne 0 ]; then
    fallos_seguidos=$((fallos_seguidos + 1))
    echo "  ⚠ Cursor salió con código $codigo ($(tail -1 "$log" | cut -c1-120))"
    # límite de uso, red o sesión caducada: espera creciente (máximo 10 min) y reintenta hasta la hora; nunca se rinde
    espera=$(( fallos_seguidos * 60 )); [ $espera -gt 600 ] && espera=600
    sleep $espera
    continue
  fi
  fallos_seguidos=0
  if [ "$antes" = "$despues" ]; then sin_avance=$((sin_avance + 1)); else sin_avance=0; fi
  if [ $sin_avance -ge 12 ]; then echo "✘ 12 vueltas seguidas sin cambiar nada: paro para no gastar. Mira $log"; break; fi
  [ $sin_avance -ge 6 ] && sleep 300      # algo raro: no quemar vueltas en bucle
done

if terminado; then echo "✔ Cursor ha terminado: lee migracion/INFORME_NOCHE.md"
else echo "⏰ Hora cumplida o parada: el cuaderno (migracion/PROGRESO.md) dice por dónde va. Se puede seguir con otra noche.sh"; fi

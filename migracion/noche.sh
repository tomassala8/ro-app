#!/usr/bin/env bash
# migracion/noche.sh · lanza a Cursor (orden de terminal «cursor-agent») con el prompt de la noche y lo VUELVE A LANZAR
# cada vez que termina una vuelta, hasta que migracion/PROGRESO.md diga «ESTADO: TERMINADO» o llegue la hora.
#
#   bash migracion/noche.sh                    # 8 horas desde ahora, modelos por defecto
#   RO_HORAS=7 RO_MODELO=<ejecuta> RO_MODELO_PLAN=<planea> bash migracion/noche.sh
#   RO_AGENTE="cursor-agent -p --force --model {MODELO}" bash migracion/noche.sh   # si tu versión usa otras opciones
#   RO_AGENTE_PLAN="cursor-agent -p --mode plan --model {MODELO}"                 # si tu versión tiene modo plan
#
# Dos modelos, como trabaja Tomás (4-oct): Fable 5.1 PLANEA cada paso (vuelta corta, solo escribe
# migracion/PLAN_VUELTA.md) y Sonnet 5.5 lo EJECUTA en las vueltas siguientes. Se vuelve a planear al cambiar de paso,
# cuando el plan no funciona (el ejecutor escribe «PLAN: GASTADO») o tras dos vueltas sin avance. Si la vuelta de plan
# falla dos veces seguidas (límite de uso), se sigue solo con el ejecutor: la noche no se para por el planificador.
#
# Mantiene el Mac despierto (caffeinate) mientras dura. Registros: ~/RO_MIGRACION/logs/vuelta_NNN.log.
# Para pararlo: Ctrl+C (Cursor termina la vuelta en curso; el cuaderno queda como esté y se puede seguir mañana).
set -uo pipefail
cd "$(dirname "$0")/.."
RAIZ="$(pwd)"
FUERA="${RO_MIGRACION:-$HOME/RO_MIGRACION}"; LOGS="$FUERA/logs"; mkdir -p "$LOGS"
HORAS="${RO_HORAS:-8}"
MODELO="${RO_MODELO:-claude-sonnet-5-5}"            # ejecuta
MODELO_PLAN="${RO_MODELO_PLAN:-claude-fable-5-1}"   # planea
PROMPT="$RAIZ/migracion/PROMPT_NOCHE.md"
CUADERNO="$RAIZ/migracion/PROGRESO.md"
PROMPT_PLAN="$RAIZ/migracion/PROMPT_PLAN.md"
PLAN="$RAIZ/migracion/PLAN_VUELTA.md"

# --- la orden de Cursor ----------------------------------------------------------------------------------------
if [ -n "${RO_AGENTE:-}" ]; then AGENTE="${RO_AGENTE//\{MODELO\}/$MODELO}"; PLANTILLA="$RO_AGENTE"
elif command -v cursor-agent >/dev/null; then AGENTE="cursor-agent -p --force --output-format text --model $MODELO"
  PLANTILLA="cursor-agent -p --force --output-format text --model {MODELO}"
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
# Prisma deja hacer «migrate reset --force» a un agente si esta variable está puesta: nunca esta noche.
unset PRISMA_USER_CONSENT_FOR_DANGEROUS_AI_ACTION
export RO_AVISOS_SIN_BUCLE=1
# Reloj de negocio FIJO toda la noche (la misma hora que las fotos de capturar.mjs). Si no, lo grabado a las 23:00
# no se parece a lo de las 3:00: cambia «hoy», salen los resúmenes del día de las 8:30… y las puertas dan diferencias
# que no son fallos. permisos.py, avisos.py, envios.py y sincronia.py ya lo respetan; lo que se porte a Nest, también.
export RO_RELOJ="${RO_RELOJ:-2026-10-05T07:30}"

# --- sin llaves reales -------------------------------------------------------------------------------------------
# Cursor trabaja solo y con tu usuario: podría leer el llavero del Mac. Esta noche no hay ninguna llave:
#  · config.secreto() devuelve None con RO_SIN_LLAVES=1;
#  · y una orden «security» falsa va delante en el PATH: muchos scripts (fuentes_*, ia.py, sincronia.py…) llaman al
#    llavero directamente. La falsa niega cualquier lectura de contraseñas y deja pasar lo demás.
export RO_SIN_LLAVES=1
SIN_LLAVERO="$FUERA/sin_llavero/bin"; mkdir -p "$SIN_LLAVERO"
cat > "$SIN_LLAVERO/security" <<'FALSA'
#!/bin/sh
# Orden «security» de la noche de migración: el llavero está cerrado para el agente.
case "$1" in
  find-generic-password|find-internet-password|dump-keychain|export|unlock-keychain|show-keychain-info)
    echo "security: el llavero está cerrado esta noche (migracion/noche.sh)" >&2; exit 44 ;;
esac
exec /usr/bin/security "$@"
FALSA
chmod 755 "$SIN_LLAVERO/security"
export PATH="$SIN_LLAVERO:$PATH"

# --- huellas de las puertas --------------------------------------------------------------------------------------
# Un agente que no pasa una prueba tiende a «arreglar» la prueba. Guardamos la huella de los ficheros que juzgan
# (fuera del repo y solo lectura). Por la mañana: bash migracion/comprobar_manana.sh lo compara y repite las puertas
# desde cero. capturar.mjs no va: el paso F1.4 puede tener que arreglarlo.
HUELLAS="$FUERA/huellas_puertas.txt"
if [ ! -f "$HUELLAS" ]; then
  ( for f in migracion/puerta.sh migracion/contrato.py migracion/contrato_escritura.py migracion/vectores_permisos.py \
             migracion/caidas.sh migracion/seguridad_http.py migracion/rendimiento.py migracion/servicios.sh \
             v2/tools/capturas/comparar.mjs pruebas_*.py despliegue/pruebas_noche.py despliegue/pruebas_tokens.py; do
      [ -f "$f" ] && { shasum -a 256 "$f" 2>/dev/null || sha256sum "$f"; }
    done; echo "# commit $(git rev-parse HEAD) · $(date '+%Y-%m-%d %H:%M')" ) > "$HUELLAS"
  chmod 444 "$HUELLAS"
  echo "Huellas de las puertas guardadas en $HUELLAS"
fi

# --- el Mac despierto --------------------------------------------------------------------------------------------
if command -v caffeinate >/dev/null; then caffeinate -dimsu -w $$ & fi

PLANTILLA_PLAN="${RO_AGENTE_PLAN:-$PLANTILLA}"; AGENTE_PLAN="${PLANTILLA_PLAN//\{MODELO\}/$MODELO_PLAN}"

echo "Noche de migración · hasta $RO_FIN_NOCHE · planea $MODELO_PLAN · ejecuta $MODELO"
echo "Orden: $AGENTE \"<PROMPT_NOCHE.md>\" · plan: $AGENTE_PLAN \"<PROMPT_PLAN.md>\""
echo "Cuaderno: $CUADERNO · registros: $LOGS"

terminado() { grep -q "^ESTADO: TERMINADO" "$CUADERNO" 2>/dev/null; }
suma() { md5 -q "$1" 2>/dev/null || md5sum "$1" 2>/dev/null | cut -d' ' -f1; }
huella() { (git rev-parse HEAD; suma "$CUADERNO") | tr '\n' ' '; }
toca_planear() {
  [ $fallos_plan -ge 2 ] && return 1                     # el planificador no responde: sigue solo el ejecutor
  [ ! -s "$PLAN" ] || head -1 "$PLAN" | grep -q "PLAN: GASTADO" || [ $sin_avance -eq 2 ]   # una sola vez por atasco
}

vuelta=0; fallos_seguidos=0; sin_avance=0; fallos_plan=0; planes=0
while [ "$(date +%s)" -lt "$FIN" ] && ! terminado; do
  if toca_planear; then
    planes=$((planes + 1))
    log="$LOGS/plan_$(printf %03d $planes).log"; antes_plan="$(suma "$PLAN")"
    echo "[$(date '+%H:%M')] plan $planes ($MODELO_PLAN) → $log"
    # shellcheck disable=SC2086
    $AGENTE_PLAN "$(cat "$PROMPT_PLAN")" > "$log" 2>&1 < /dev/null
    if [ $? -ne 0 ] || [ "$(suma "$PLAN")" = "$antes_plan" ]; then
      fallos_plan=$((fallos_plan + 1)); echo "  ⚠ el plan no se escribió ($(tail -1 "$log" | cut -c1-120))"
    else fallos_plan=0; fi
  fi
  vuelta=$((vuelta + 1))
  log="$LOGS/vuelta_$(printf %03d $vuelta).log"
  antes="$(huella)"
  echo "[$(date '+%H:%M')] vuelta $vuelta ($MODELO) → $log"
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

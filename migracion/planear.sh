#!/usr/bin/env bash
# migracion/planear.sh · Fable escribe el plan COMPLETO de la noche (migracion/PLAN_NOCHE.md) y lo audita hasta que sale limpio.
# Después, noche.sh lo da a ejecutar al modelo rápido, paso a paso.
#
#   bash migracion/planear.sh                 # escribe lo que falte, audita, y deja «PLAN: AUDITADO»
#   bash migracion/planear.sh --ver           # solo dice en qué estado está el plan
#   RO_AUDITORIAS_MIN=4 RO_AUDITORIAS=8 RO_MODELO_PLAN=<nombre> bash migracion/planear.sh
#
# Se puede cortar (Ctrl+C) y volver a lanzar: sigue donde lo dejó. Si el plan ya está auditado y el código del Mac
# ha cambiado desde entonces (Astra, juntar_plan.sh), hace solo una auditoría de puesta al día sobre lo que cambió.
# Cada vuelta tiene tope de tiempo; antes de cada una se guarda copia en ~/RO_MIGRACION/plan_copias/.
# El planificador solo puede tocar PLAN_NOCHE.md: si cambia cualquier otro fichero, esto para y lo dice.
set -uo pipefail
cd "$(dirname "$0")/.."
FUERA="${RO_MIGRACION:-$HOME/RO_MIGRACION}"; LOGS="$FUERA/logs"; COPIAS="$FUERA/plan_copias"; mkdir -p "$LOGS" "$COPIAS"
MODELO_PLAN="${RO_MODELO_PLAN:-claude-fable-5-1}"
# si Fable se queda sin saldo, planea Opus; y si no, Sonnet (Tomás, 4-oct 12:09)
RESERVA_PLAN="${RO_MODELO_OPUS:-claude-opus-5-5} ${RO_MODELO_SONNET:-claude-sonnet-5-5}"
RONDAS="${RO_RONDAS_PLAN:-25}"            # vueltas de escritura como mucho
TOPE="${RO_TOPE_PLAN:-3600}"              # segundos por vuelta
AUD_MIN="${RO_AUDITORIAS_MIN:-4}"         # al menos una por enfoque (A, B, C, D)
AUD_MAX="${RO_AUDITORIAS:-8}"
PLAN="migracion/PLAN_NOCHE.md"
ARBOL_PLAN="$FUERA/plan_arbol.txt"        # huella del código contra el que se auditó
if [ -z "${RO_EN_ENSAYO:-}" ] && { [ -L "$FUERA" ] || ls -d "$FUERA".real_* >/dev/null 2>&1; }; then
  echo "✘ Hay un ensayo en marcha o sin cerrar ($FUERA apunta a él). Ciérralo: bash migracion/ensayo.sh --cerrar"; exit 1
fi
. migracion/_agente.sh
PLANTILLA_PLAN="${RO_AGENTE_PLAN:-$PLANTILLA}"
sin_llaves

primera() { head -1 "$PLAN" 2>/dev/null; }
revisar() { python3 migracion/revisar_plan.py "$@"; }
cuenta() { local c; c="$(grep -c "$1" "$PLAN" 2>/dev/null)"; echo "${c:-0}"; }
# auditorías hechas = el número más alto de «## Auditoría N» (una repetida por un corte no cuenta dos veces)
auditorias() { local n; n="$(grep -oE '^## Auditoría [0-9]+' "$PLAN" 2>/dev/null | awk '{print $3}' | sort -n | tail -1)"; echo "${n:-0}"; }
tiene_auditoria() { grep -qE "^## Auditoría $1([ :·]|\$)" "$PLAN"; }
limpia_n() {   # la primera línea con texto tras su cabecera es «SIN CAMBIOS» (con o sin negrita o punto)
  awk -v n="$1" '$0 ~ "^## Auditoría " n "([ :·]|$)" {f=1; next} f && NF {print; exit}' "$PLAN" | grep -qxE '[*_]*SIN CAMBIOS[*_]*\.?[[:space:]]*'
}
# ¿la auditoría N cambió algo más que su propia sección? (un «SIN CAMBIOS» que sí cambió no vale como limpio)
cambio_fuera_de() {   # cambio_fuera_de <n> <copia de antes>   (las líneas en blanco no cuentan)
  [ -f "$2" ] || return 1
  [ "$(awk -v n="$1" '$0 ~ "^## Auditoría " n "([ :·]|$)" {f=1; next} f && /^## / {f=0} !f' "$PLAN" | grep -v '^[[:space:]]*$')" \
    != "$(grep -v '^[[:space:]]*$' "$2")" ]
}
# Tope total (noche.sh lo pone si el plan no estaba hecho de antes): RO_PLAN_FIN, en segundos desde 1970.
a_tiempo() { [ -z "${RO_PLAN_FIN:-}" ] || [ "$(date +%s)" -lt "$RO_PLAN_FIN" ]; }
guardar_auditado() { arbol > "$ARBOL_PLAN"; rm -f "$FUERA/PLAN_NOCHE.auditado.md"; cp "$PLAN" "$FUERA/PLAN_NOCHE.auditado.md"; }
pon_primera() {   # cambia la primera línea del plan
  local tmp; tmp="$(mktemp)"; { echo "$1"; tail -n +2 "$PLAN"; } > "$tmp" && cat "$tmp" > "$PLAN"; rm -f "$tmp"
}

if [ "${1:-}" = "--ver" ]; then
  echo "Primera línea: $(primera || echo '(no hay plan)')"; revisar; echo "Auditorías: $(auditorias)"; exit 0
fi

# --- guardia: el planificador solo escribe el plan ---------------------------------------------------------------
estado_repo() { echo "$(git symbolic-ref -q HEAD) $(git rev-parse HEAD) $(arbol)"; }
vigilar() {   # vigilar <estado de antes> <registro>
  local ahora; ahora="$(estado_repo)"
  if [ "$ahora" != "$1" ]; then
    echo "✘ La vuelta del planificador ha cambiado algo más que el plan (rama, commit o ficheros). Paro."
    # qué cambió exactamente (se guarda para Claude y para la mañana)
    { echo "[$(date '+%Y-%m-%d %H:%M')] antes: $1"; echo "  ahora: $ahora"
      git diff --stat=200 --summary "${1##* }" "${ahora##* }" 2>/dev/null | tail -60; } | tee -a "$FUERA/plan_cambios_fuera.txt" | sed 's/^/  /'
    echo "  Mira «git status» y «git log -3»; el registro es $2. Deshaz lo que no sea PLAN_NOCHE.md y vuelve a lanzar."
    exit 1
  fi
}
copia() { [ -f "$PLAN" ] && cp "$PLAN" "$COPIAS/PLAN_NOCHE.$(date '+%m%d_%H%M%S').md"; }
cabeceras() { cuenta '^## F'; }
tamano() { if [ -f "$PLAN" ]; then wc -c < "$PLAN" | tr -d ' '; else echo 0; fi; }
# Una vuelta que deja el plan más corto de lo que estaba (se comió secciones) se deshace.
encogido() { [ "$(cabeceras)" -lt "$1" ] || [ "$(tamano)" -lt $(( $2 * 7 / 10 )) ]; }
ultima_copia() { ls -t "$COPIAS"/PLAN_NOCHE.*.md 2>/dev/null | head -1; }

vuelta() {   # vuelta <mensaje> <registro>: lanza al planificador con guardia, copia y deshacer
  local antes cab tam codigo
  antes="$(estado_repo)"; copia; cab="$(cabeceras)"; tam="$(tamano)"
  local tope="$TOPE"
  if [ -n "${RO_PLAN_FIN:-}" ]; then local queda=$(( RO_PLAN_FIN - $(date +%s) )); [ $queda -lt "$tope" ] && tope=$queda; [ $tope -lt 60 ] && tope=60; fi
  lanzar "$MODELO_PLAN" "$1" "$2" "$tope" "$PLANTILLA_PLAN"; codigo=$?
  if [ $codigo -ne 0 ] && sin_saldo_en "$2" && [ -n "${RESERVA_PLAN:-}" ]; then   # sin saldo: el siguiente de la cadena
    echo "  ⚠ $MODELO_PLAN sin saldo: sigue planeando ${RESERVA_PLAN%% *}"
    echo "$MODELO_PLAN" >> "$FUERA/sin_saldo.txt"
    MODELO_PLAN="${RESERVA_PLAN%% *}"; RESERVA_PLAN="$(echo "$RESERVA_PLAN" | cut -s -d' ' -f2-)"
  fi
  vigilar "$antes" "$2"
  if [ -f "$PLAN" ] && [ "$cab" -gt 0 ] && encogido "$cab" "$tam"; then
    echo "  ⚠ la vuelta dejó el plan más corto ($cab → $(cabeceras) pasos): se deshace"; cp "$(ultima_copia)" "$PLAN"; return 9
  fi
  return $codigo
}

esperar_fallo() {   # límite de uso o red: espera creciente, máximo 10 min
  local s=$(( $1 * 120 )); [ $s -gt 600 ] && s=600; echo "  … espero $s s"; sleep $s
}

# --- ¿ya está auditado? ------------------------------------------------------------------------------------------
if primera | grep -q '^PLAN: AUDITADO' && revisar >/dev/null; then
  ahora="$(arbol)"; antes="$(cat "$ARBOL_PLAN" 2>/dev/null)"
  if [ "$ahora" = "$antes" ]; then echo "✔ El plan está auditado y el código no ha cambiado desde entonces."; exit 0; fi
  echo "El código ha cambiado desde la auditoría: auditoría de puesta al día."
  n=$(( $(auditorias) + 1 ))
  cambios="$( [ -n "$antes" ] && git diff --stat=200 "$antes" "$ahora" 2>/dev/null | tail -40 )"
  msg="$(cat migracion/PROMPT_AUDITA.md)

MENSAJE DEL SUPERVISOR: eres la auditoría $n. Tu enfoque: A, pero SOLO sobre lo que nombra a estos ficheros, que han cambiado desde la última auditoría (rutas, funciones, números de línea, opciones). El resto ya está auditado: no lo toques.
${cambios:-(no tengo la lista: compara el plan con «git status» y «git diff»)}"
  hecha=""
  for i in 1 2 3; do
    a_tiempo || break
    if vuelta "$msg" "$LOGS/plan_auditoria_$(printf %02d $n).log" && revisar >/dev/null && tiene_auditoria $n; then hecha=1; break; fi
    cp "$(ultima_copia)" "$PLAN"          # lo que dejó a medias, fuera
    [ $i -lt 3 ] && esperar_fallo $i
  done
  [ -n "$hecha" ] || { echo "✘ La auditoría de puesta al día no salió: el plan se queda como estaba (auditado contra el código de antes). Vuelve a lanzar planear.sh."; exit 1; }
  pon_primera "PLAN: AUDITADO · $n auditorías · puesta al día · $(date '+%Y-%m-%d %H:%M')"
  guardar_auditado
  echo "✔ Plan al día."; exit 0
fi

echo "Plan de la noche con $MODELO_PLAN · registros en $LOGS/plan_*.log · copias en $COPIAS"

# --- 1. escribir hasta tener todos los pasos -----------------------------------------------------------------------
fallos=0; quieto=0; r=0
while :; do
  faltan="$(revisar --faltan)"
  if [ -z "$faltan" ]; then
    if revisar >/dev/null; then break; fi
    detalle="$(revisar | head -30)"
  else detalle="$(revisar | grep -v '^✘ faltan' | head -30)"; fi
  a_tiempo || { echo "⏰ Se acabó el tiempo para planear: el plan se queda a medias ($(primera))."; exit 2; }
  r=$((r + 1))
  [ $r -gt "$RONDAS" ] && { echo "✘ $RONDAS vueltas y el plan sigue sin estar completo. Vuelve a lanzar planear.sh (sigue donde lo dejó)."; exit 1; }
  log="$LOGS/plan_escribe_$(printf %02d $r).log"
  echo "[$(date '+%H:%M')] vuelta $r de escritura → $log · faltan: $(echo "$faltan" | wc -w | tr -d ' ')"
  # Tomás (4-oct): al principio, mucho tiempo y esfuerzo en entender a fondo qué queremos. El análisis (A0) va solo,
  # en su propia vuelta (o vueltas), antes de escribir ningún paso.
  analisis=""
  case " $faltan " in *" A0 "*) analisis="ESTA VUELTA ES SOLO EL ANÁLISIS (A0): no escribas ningún paso todavía. Léelo TODO antes (punto 1 de tus instrucciones), con calma: es la vuelta más importante de la noche." ;; esac
  msg="$(cat migracion/PROMPT_PLAN.md)

MENSAJE DEL SUPERVISOR: vuelta $r de escritura. Faltan, en este orden: ${faltan:-ninguno}.${analisis:+
$analisis}
${detalle:+Además, revisar_plan.py dice:
$detalle}"
  antes="$(md5sum "$PLAN" 2>/dev/null || md5 -q "$PLAN" 2>/dev/null)"
  vuelta "$msg" "$log"; codigo=$?
  if [ $codigo -ne 0 ] && [ $codigo -ne 9 ]; then
    fallos=$((fallos + 1)); echo "  ⚠ Cursor salió con código $codigo ($(tail -1 "$log" | cut -c1-120))"
    [ $fallos -ge 6 ] && { echo "✘ 6 fallos seguidos de Cursor: mira $log"; exit 1; }
    esperar_fallo $fallos; continue
  fi
  fallos=0
  if [ "$(md5sum "$PLAN" 2>/dev/null || md5 -q "$PLAN" 2>/dev/null)" = "$antes" ]; then
    quieto=$((quieto + 1)); [ $quieto -ge 3 ] && { echo "✘ 3 vueltas sin escribir nada: mira $log"; exit 1; }
  else quieto=0; fi
done
# si esta vez se escribió algo, deja de estar auditado hasta que lo audite alguien
if [ $r -gt 0 ] || ! primera | grep -qE '^PLAN: (COMPLETO|AUDITADO)'; then pon_primera "PLAN: COMPLETO · $(date '+%Y-%m-%d %H:%M')"; fi
echo "✔ Plan completo: $(cabeceras) pasos."

# --- 2. auditorías hasta que una salga limpia ----------------------------------------------------------------------
ENFOQUES=("A · ¿existe lo que nombra?" "B · ¿encaja la noche de principio a fin?" "C · ¿lo puede hacer un modelo rápido sin equivocarse?" "D · ¿respeta las líneas rojas?")
limpia=""; fallos=0
inicio=$(auditorias); n=$(( inicio + 1 ))
# Plan nuevo: de AUD_MIN a AUD_MAX auditorías. Plan ya auditado al que se le escribió algo (un fallo nuevo en la lista):
# al menos una auditoría más y como mucho dos, contadas desde aquí (si no, lo nuevo quedaría sin auditar).
if [ "$inicio" -eq 0 ]; then tope=$AUD_MAX; minimo=$AUD_MIN; else tope=$(( inicio + 2 )); minimo=$(( inicio + 1 )); fi
sin_tiempo=""
while [ $n -le "$tope" ]; do
  a_tiempo || { sin_tiempo=1; break; }
  if [ $n -le 4 ]; then enfoque="${ENFOQUES[$((n - 1))]}"; else enfoque="todos (A, B, C y D), con lo que las anteriores no miraron"; fi
  log="$LOGS/plan_auditoria_$(printf %02d $n).log"
  echo "[$(date '+%H:%M')] auditoría $n ($enfoque) → $log"
  msg="$(cat migracion/PROMPT_AUDITA.md)

MENSAJE DEL SUPERVISOR: eres la auditoría $n. Tu enfoque: $enfoque."
  vuelta "$msg" "$log"; codigo=$?
  if [ $codigo -ne 0 ]; then
    [ $codigo -ne 9 ] && cp "$(ultima_copia)" "$PLAN"      # una auditoría cortada no deja cambios a medias
    fallos=$((fallos + 1)); echo "  ⚠ la auditoría no terminó (código $codigo)"
    [ $fallos -ge 4 ] && { echo "✘ 4 auditorías fallidas seguidas: mira $log y vuelve a lanzar planear.sh"; exit 1; }
    [ $codigo -ne 9 ] && esperar_fallo $fallos
    continue
  fi
  if ! revisar >/dev/null; then
    echo "  ⚠ tras la auditoría el plan no pasa revisar_plan.py: se deshace y se repite"; cp "$(ultima_copia)" "$PLAN"
    fallos=$((fallos + 1)); [ $fallos -ge 4 ] && { echo "✘ 4 auditorías fallidas seguidas: mira $log"; exit 1; }; continue
  fi
  if ! tiene_auditoria $n; then
    echo "  ⚠ la auditoría no dejó su sección: se repite"
    fallos=$((fallos + 1)); [ $fallos -ge 4 ] && { echo "✘ 4 auditorías fallidas seguidas: mira $log"; exit 1; }; continue
  fi
  fallos=0
  # ¿limpia? la primera línea con texto tras su cabecera es exactamente «SIN CAMBIOS»
  if limpia_n $n && ! cambio_fuera_de $n "$(ultima_copia)"; then
    echo "  ✔ auditoría $n: SIN CAMBIOS"; [ $n -ge "$minimo" ] && { limpia=1; break; }
  elif limpia_n $n; then
    echo "  · auditoría $n: dice SIN CAMBIOS pero cambió el plan: cuenta como con correcciones"
  else echo "  · auditoría $n: con correcciones"; fi
  n=$((n + 1))
done
[ -z "$limpia" ] && n=$((n - 1))           # la última que se hizo
if [ "$n" -le "$inicio" ]; then echo "⏰ Sin tiempo para auditar lo último: el plan queda COMPLETO sin esa auditoría."; exit 2; fi

if [ -n "$sin_tiempo" ]; then pon_primera "PLAN: AUDITADO · $n auditorías · sin tiempo para más · $(date '+%Y-%m-%d %H:%M')"
elif [ -n "$limpia" ]; then pon_primera "PLAN: AUDITADO · $n auditorías · la última sin cambios · $(date '+%Y-%m-%d %H:%M')"
else pon_primera "PLAN: AUDITADO · $n auditorías · la última aún corrigió algo · $(date '+%Y-%m-%d %H:%M')"
  echo "⚠ Tras $(( tope - inicio )) auditorías la última aún corrigió algo. El plan vale; si hay tiempo: RO_AUDITORIAS=$((AUD_MAX + 2)) bash migracion/planear.sh"
fi
guardar_auditado
echo "✔ $(primera)"
if grep -q '^## Dudas para Tomás' "$PLAN"; then
  echo; echo "Dudas que el planificador deja para Tomás (la noche usa la opción conservadora si no contestas):"
  awk '/^## Dudas para Tomás/{f=1; next} /^## /{f=0} f' "$PLAN" | sed '/^$/d' | head -40
fi

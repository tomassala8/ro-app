#!/usr/bin/env bash
# migracion/noche.sh · la noche de migración sin nadie delante.
#
#   bash migracion/noche.sh                      # 8 horas desde que el plan está listo
#   RO_HORAS=7 bash migracion/noche.sh
#   RO_MODELO=<ejecuta> RO_MODELO_PLAN=<planea> bash migracion/noche.sh
#   RO_PASOS_FUERTES="F4.1 F4.2 F5.1 F5.10" bash migracion/noche.sh    # esos pasos, con RO_MODELO_FUERTE
#   RO_AGENTE="cursor-agent -p --force --model {MODELO}" bash migracion/noche.sh  # si tu versión usa otras opciones
#
# Cómo trabaja (Tomás, 4-oct):
#  1. Fable ha escrito y auditado el plan COMPLETO de la noche (migracion/planear.sh → migracion/PLAN_NOCHE.md).
#     Si no está auditado o el código cambió desde la auditoría, noche.sh lo lanza antes de empezar (RO_SIN_PLAN=1 lo salta).
#  2. El modelo rápido (Grok Fast) ejecuta el plan paso a paso, vuelta tras vuelta, hasta «ESTADO: TERMINADO» o la hora.
#  3. Fable de guardia: si un paso falla una vez, si el ejecutor marca su plan como gastado o si dos vueltas no avanzan,
#     Fable diagnostica y escribe migracion/PLAN_VUELTA.md para ese paso. Si Fable no responde, la noche sigue sin él.
#
# Si se para (Ctrl+C, apagón, el Mac se reinicia), se vuelve a lanzar igual: sigue la MISMA noche, con la misma hora de
# fin, desde lo que diga migracion/PROGRESO.md. RO_NOCHE_NUEVA=1 empieza una noche nueva.
# Mantiene el Mac despierto (caffeinate). Registros: ~/RO_MIGRACION/logs/. Por la mañana: bash ~/RO_MIGRACION/comprobar_manana.sh
set -uo pipefail
cd "$(dirname "$0")/.."
RAIZ="$(pwd)"
FUERA="${RO_MIGRACION:-$HOME/RO_MIGRACION}"; LOGS="$FUERA/logs"; mkdir -p "$LOGS"
export RO_MIGRACION="$FUERA"
HORAS="${RO_HORAS:-8}"
MODELO="${RO_MODELO:-grok-code-fast-1}"                  # ejecuta (Tomás: Grok Fast)
MODELO_PLAN="${RO_MODELO_PLAN:-claude-fable-5-1}"        # planea y diagnostica
MODELO_FUERTE="${RO_MODELO_FUERTE:-claude-sonnet-5-5}"   # solo para los pasos de RO_PASOS_FUERTES
PASOS_FUERTES="${RO_PASOS_FUERTES:-}"
TOPE_VUELTA="${RO_TOPE_VUELTA:-5400}"                    # una vuelta colgada se corta a los 90 min
TOPE_REPLAN="${RO_TOPE_REPLAN:-1800}"
PROMPT="$RAIZ/migracion/PROMPT_NOCHE.md"
CUADERNO="$RAIZ/migracion/PROGRESO.md"
PLAN_NOCHE="$RAIZ/migracion/PLAN_NOCHE.md"
PLAN_GUARDADO="$FUERA/PLAN_NOCHE.auditado.md"
PLAN="$RAIZ/migracion/PLAN_VUELTA.md"
MARCA="$FUERA/noche_en_curso"
. migracion/_agente.sh
PLANTILLA_PLAN="${RO_AGENTE_PLAN:-$PLANTILLA}"

terminado() { grep -q "^ESTADO: TERMINADO" "$CUADERNO" 2>/dev/null; }
hora_de() { date -r "$1" '+%Y-%m-%d %H:%M' 2>/dev/null || date -d "@$1" '+%Y-%m-%d %H:%M'; }

# --- noche nueva o la misma de antes --------------------------------------------------------------------------------
nueva=1
if [ -s "$MARCA" ] && [ "${RO_NOCHE_NUEVA:-}" != "1" ]; then
  FIN="$(cat "$MARCA")"; nueva=""
  echo "Sigo la noche empezada (fin $(hora_de "$FIN")). Para empezar otra: RO_NOCHE_NUEVA=1 bash migracion/noche.sh"
fi

if [ -n "$nueva" ]; then
  # 1. lo que cambió el plan fuera de migracion/ (config.py, despliegue/, fuentes/…), sin pisar lo de Astra; una vez por noche
  bash migracion/juntar_plan.sh || echo "⚠ juntar_plan.sh falló: F1.3 lo repite"
  # 2. el plan de la noche, escrito y auditado (si ya lo está y nada cambió, esto tarda un segundo)
  if [ "${RO_SIN_PLAN:-}" != "1" ]; then
    bash migracion/planear.sh || echo "⚠ planear.sh no terminó: la noche sigue con el plan que haya y con PROMPTS_CURSOR.md"
  fi
  # 3. sin restos de otra noche o del ensayo
  rm -f "$PLAN"
  [ -f "$PLAN_NOCHE" ] && { cp "$PLAN_NOCHE" "$PLAN_GUARDADO"; chmod 444 "$PLAN_GUARDADO"; }
fi

# --- sin llaves reales: esta noche no hay ninguna (ver _agente.sh) ---------------------------------------------------
sin_llaves
if ! grep -q RO_SIN_LLAVES config.py 2>/dev/null && [ "${RO_FORZAR:-}" != "1" ]; then
  echo "✘ config.py no tiene la noche sin llaves (choque al juntar el plan: mira $FUERA/choques_plan.txt)."
  echo "  Aplica el cambio de config.secreto() a mano, o bloquea el llavero y lanza con RO_FORZAR=1."
  exit 1
fi
export RO_AVISOS_SIN_BUCLE=1
# Reloj de negocio FIJO toda la noche (la misma hora que las fotos de capturar.mjs): si no, lo grabado a las 23:00
# no se parece a lo de las 3:00 y las puertas dan diferencias que no son fallos.
export RO_RELOJ="${RO_RELOJ:-2026-10-05T07:30}"

# --- huellas de los ficheros que juzgan (y de los guardianes) --------------------------------------------------------
# Un agente que no pasa una prueba tiende a «arreglar» la prueba. Se guarda la huella y una COPIA de cada uno fuera del
# repo; por la mañana comprobar_manana.sh compara, vuelve a la copia lo que cambió y repite las puertas desde cero.
HUELLAS="$FUERA/huellas_puertas.txt"; COPIA_JUECES="$FUERA/huellas_copia"
if [ -n "$nueva" ] || [ ! -f "$HUELLAS" ]; then
  rm -rf "$COPIA_JUECES"; rm -f "$HUELLAS"; mkdir -p "$COPIA_JUECES"
  ( for f in migracion/puerta.sh migracion/contrato.py migracion/contrato_escritura.py migracion/vectores_permisos.py \
             migracion/caidas.sh migracion/seguridad_http.py migracion/rendimiento.py migracion/servicios.sh \
             migracion/noche.sh migracion/planear.sh migracion/_agente.sh migracion/juntar_plan.sh migracion/revisar_plan.py \
             migracion/comprobar_manana.sh migracion/llaves_nube.py migracion/validar_sqlite.py \
             v2/tools/capturas/comparar.mjs v2/apps/api/src/permisos/rutas-declaradas.spec.ts \
             v2/packages/permisos/test/paridad.test.ts \
             pruebas_*.py despliegue/pruebas_noche.py despliegue/pruebas_tokens.py; do
      [ -f "$f" ] || continue
      mkdir -p "$COPIA_JUECES/$(dirname "$f")"; cp -p "$f" "$COPIA_JUECES/$f"
      shasum -a 256 "$f" 2>/dev/null || sha256sum "$f"
    done; echo "# $(date '+%Y-%m-%d %H:%M') · copias en $COPIA_JUECES" ) > "$HUELLAS"
  chmod -R a-w "$COPIA_JUECES"; chmod 444 "$HUELLAS"
  # la comprobación de la mañana se lanza desde fuera del repo: la de dentro la podría cambiar el agente
  cp migracion/comprobar_manana.sh "$FUERA/comprobar_manana.sh"; chmod 555 "$FUERA/comprobar_manana.sh"
  echo "$RAIZ" > "$FUERA/app_dir.txt"
  echo "Huellas y copias de los ficheros que juzgan: $HUELLAS"
fi

# --- el reloj (empieza a contar cuando el plan está listo) ------------------------------------------------------------
if [ -n "$nueva" ]; then FIN=$(( $(date +%s) + HORAS * 3600 )); echo "$FIN" > "$MARCA"; fi
RO_FIN_NOCHE="$(hora_de "$FIN")"; export RO_FIN_NOCHE

# --- el Mac despierto ------------------------------------------------------------------------------------------------
if command -v caffeinate >/dev/null; then caffeinate -dimsu -w $$ & fi

echo "Noche de migración · hasta $RO_FIN_NOCHE · ejecuta $MODELO · planea $MODELO_PLAN${PASOS_FUERTES:+ · $PASOS_FUERTES con $MODELO_FUERTE}"
echo "Plan: $(head -1 "$PLAN_NOCHE" 2>/dev/null || echo 'NO HAY PLAN_NOCHE.md: se sigue PROMPTS_CURSOR.md')"
echo "Cuaderno: $CUADERNO · registros: $LOGS"

# paso en curso según el cuaderno: el 🔄, o el primer ⬜. Imprime «F2.3 2» (paso e intento).
paso_actual() {
  python3 - "$CUADERNO" <<'PY'
import re, sys
texto = open(sys.argv[1], encoding="utf-8").read()
m = re.search(r"^- 🔄 (F\d+\.\d+)\b.*?intento (\d+)", texto, re.M) or re.search(r"^- 🔄 (F\d+\.\d+)\b", texto, re.M)
if m:
    print(m.group(1), m.group(2) if m.lastindex > 1 else 1)
else:
    m = re.search(r"^- ⬜ (F\d+\.\d+)\b", texto, re.M)
    print(m.group(1) + " 1" if m else "")
PY
}
modelo_de() { case " $PASOS_FUERTES " in *" $1 "*) echo "$MODELO_FUERTE" ;; *) echo "$MODELO" ;; esac; }
huella() { (git rev-parse HEAD; suma "$CUADERNO"; arbol) 2>/dev/null | tr '\n' ' '; }
plan_vigente_para() { head -1 "$PLAN" 2>/dev/null | grep -q "^PLAN: VIGENTE · $1 "; }

# El plan de la noche no lo cambia el ejecutor: si aparece cambiado, se vuelve al auditado.
guardar_plan() {
  [ -f "$PLAN_GUARDADO" ] || return 0
  if ! cmp -s "$PLAN_GUARDADO" "$PLAN_NOCHE"; then
    cp "$PLAN_NOCHE" "$LOGS/PLAN_NOCHE.cambiado.$(date +%H%M%S).md" 2>/dev/null
    cat "$PLAN_GUARDADO" > "$PLAN_NOCHE"; echo "  ⚠ PLAN_NOCHE.md había cambiado: vuelto al auditado"
  fi
}

replanear() {   # replanear <paso> <intento> <motivo>
  planes=$((planes + 1))
  local log="$LOGS/replan_$(printf %03d $planes).log" antes; antes="$(arbol)"
  echo "[$(date '+%H:%M')] Fable de guardia ($1, intento $2: $3) → $log"
  local msg; msg="$(cat "$RAIZ/migracion/PROMPT_REPLAN.md")

MENSAJE DEL SUPERVISOR: paso $1, intento $2. Te llamo porque: $3.
Último registro del ejecutor: $LOGS/vuelta_$(printf %03d $vuelta).log"
  local h_antes; h_antes="$(suma "$PLAN")"
  if lanzar "$MODELO_PLAN" "$msg" "$log" "$TOPE_REPLAN" "$PLANTILLA_PLAN" && [ "$(suma "$PLAN")" != "$h_antes" ] && plan_vigente_para "$1"; then
    fallos_plan=0
  else
    fallos_plan=$((fallos_plan + 1)); ultimo_fallo_plan=$(date +%s)
    echo "  ⚠ el plan de guardia no se escribió bien ($(tail -1 "$log" | cut -c1-120))"
  fi
  [ "$(arbol)" = "$antes" ] || echo "  ⚠ la vuelta de guardia cambió código (solo debía escribir PLAN_VUELTA.md): mira $log"
}

# al relanzar la misma noche, los registros siguen numerándose (no se pisan los de antes)
vuelta=$(ls "$LOGS"/vuelta_*.log 2>/dev/null | wc -l | tr -d ' '); planes=$(ls "$LOGS"/replan_*.log 2>/dev/null | wc -l | tr -d ' ')
[ -n "$nueva" ] && { mkdir -p "$LOGS/antes"; mv "$LOGS"/vuelta_* "$LOGS"/replan_* "$LOGS/antes/" 2>/dev/null; vuelta=0; planes=0; }
fallos_seguidos=0; sin_avance=0; fallos_plan=0; ultimo_fallo_plan=0; ultima_clave=""
while [ "$(date +%s)" -lt "$FIN" ] && ! terminado; do
  guardar_plan
  read -r paso intento <<< "$(paso_actual)"; paso="${paso:-}"; intento="${intento:-1}"
  # Fable de guardia: si dejó de responder, se le vuelve a probar a la media hora
  if [ $fallos_plan -ge 2 ] && [ $(( $(date +%s) - ultimo_fallo_plan )) -ge 1800 ]; then fallos_plan=0; fi
  replan=""
  if [ -n "$paso" ] && [ $fallos_plan -lt 2 ]; then
    if head -1 "$PLAN" 2>/dev/null | grep -q "^PLAN: GASTADO" && [ "$ultima_clave" != "gastado/$paso/$intento" ]; then
      ultima_clave="gastado/$paso/$intento"; replanear "$paso" "$intento" "el ejecutor marcó el plan como gastado: $(head -1 "$PLAN" | cut -c1-200)"; replan=1
    elif [ "$intento" -ge 2 ] && ! head -1 "$PLAN" 2>/dev/null | grep -q "^PLAN: VIGENTE · $paso · intento $intento " \
         && [ "$ultima_clave" != "$paso/$intento" ]; then
      ultima_clave="$paso/$intento"; replanear "$paso" "$intento" "el intento $((intento - 1)) falló (mira «Intentos y notas» de PROGRESO.md)"; replan=1
    elif [ $sin_avance -eq 2 ]; then
      replanear "$paso" "$intento" "dos vueltas seguidas sin cambiar ni el cuaderno ni el código"; replan=1
    fi
  fi

  vuelta=$((vuelta + 1))
  log="$LOGS/vuelta_$(printf %03d $vuelta).log"
  modelo="$(modelo_de "$paso")"
  antes="$(huella)"
  echo "[$(date '+%H:%M')] vuelta $vuelta · ${paso:-?} intento $intento · $modelo → $log"
  mensaje="$(cat "$PROMPT")

MENSAJE DEL SUPERVISOR (vuelta $vuelta, $(date '+%H:%M')): según el cuaderno toca ${paso:-(no lo sé: léelo tú)}, intento $intento.
Su sección del plan: python3 migracion/revisar_plan.py --seccion ${paso:-<paso>}"
  if plan_vigente_para "$paso"; then
    mensaje="$mensaje
Hay un plan de guardia VIGENTE para este paso en migracion/PLAN_VUELTA.md${replan:+ (recién escrito)}: síguelo antes que la sección."
  fi
  if [ $sin_avance -ge 2 ] && [ -z "$replan" ]; then
    mensaje="$mensaje
AVISO: las dos últimas vueltas no han cambiado ni el cuaderno ni el código. Aplica ya el plan B del paso en curso (márcalo ⚠ con el motivo) y pasa al siguiente."
  fi
  lanzar "$modelo" "$mensaje" "$log" "$TOPE_VUELTA"; codigo=$?
  despues="$(huella)"
  if [ -f "$log.cortada" ]; then
    echo "  ⚠ vuelta cortada a los $TOPE_VUELTA s (colgada o demasiado larga): se relanza"; codigo=0
  fi
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

if terminado; then rm -f "$MARCA"; echo "✔ Cursor ha terminado: lee migracion/INFORME_NOCHE.md"
else echo "⏰ Hora cumplida o parada: el cuaderno (migracion/PROGRESO.md) dice por dónde va."; fi
echo "Por la mañana, antes de creerte nada: bash $FUERA/comprobar_manana.sh"

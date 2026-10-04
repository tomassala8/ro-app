#!/usr/bin/env bash
# migracion/noche.sh · la noche de migración sin nadie delante.
#
#   bash migracion/noche.sh                      # 8 horas desde que el plan está listo
#   RO_HORAS=7 bash migracion/noche.sh
#   RO_MODELO=<ejecuta> RO_MODELO_PLAN=<planea> bash migracion/noche.sh
#   RO_PASOS_OPUS="F4.1" RO_PASOS_SONNET="" bash migracion/noche.sh   # cambia el reparto de modelos (ver «Quién hace qué»)
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
# Sin plazo (Tomás, 4-oct 13:39: «no marques deadlines; avanzad sin parar hasta que me necesitéis»): la noche sigue
# hasta acabar todos los pasos. RO_HORAS es solo un tope de seguridad; los cortes del reloj de PROGRESO.md cuentan
# desde ese tope, así que con 72 h no recortan nada y todo se hace en orden, React incluido.
HORAS="${RO_HORAS:-72}"
# Quién hace qué (Tomás, 4-oct 12:09): Fable planea y hace de guardia; Opus lo crítico; Sonnet lo que pide pensar;
# Grok Fast el volumen. En F5.10 manda la gravedad de cada fallo en PENDIENTES_LOGICA.md: seguridad → Opus, datos y
# funcional → Sonnet, presentación → Grok. Si un modelo de pago se queda sin saldo, ese paso baja un escalón
# (Opus → Sonnet → Grok; Fable → Opus → Sonnet) y la noche sigue: nunca se para por saldo.
MODELO="${RO_MODELO:-grok-4.7-high}"                     # el volumen (nombre que da el Cursor de Tomás, 4-oct; sin «-fast»)
MODELO_PLAN="${RO_MODELO_PLAN:-claude-fable-5-1}"        # planea y diagnostica
MODELO_OPUS="${RO_MODELO_OPUS:-claude-opus-5-5}"         # lo crítico (sin «fast»)
MODELO_SONNET="${RO_MODELO_SONNET:-claude-sonnet-5-5}"   # lo que pide pensar
PASOS_OPUS="${RO_PASOS_OPUS-F4.1 F4.2 F5.1}"             # motor de permisos, sus pruebas, identidad y rastro
PASOS_SONNET="${RO_PASOS_SONNET-F2.4 F3.1 F5.10 F6.2}"   # base.py sobre Postgres, fontanería del proxy, fallos, carcasa
GRAVEDAD_OPUS="${RO_GRAVEDAD_OPUS-seguridad}"            # en F5.10: gravedades que van con Opus
GRAVEDAD_GROK="${RO_GRAVEDAD_GROK-presentación}"         # en F5.10: gravedades que van con Grok
TOPE_VUELTA="${RO_TOPE_VUELTA:-5400}"                    # una vuelta colgada se corta a los 90 min
TOPE_REPLAN="${RO_TOPE_REPLAN:-1800}"
# Revisión (Tomás, 4-oct 13:28: «el objetivo es el 100 %»): Grok hace el volumen y un modelo de pago revisa cada paso
# que cierra antes de seguir. Si está mal, el paso se reabre con el plan del revisor. Así el saldo de pago va a mirar,
# que es barato, y Grok a escribir. Los pasos de Opus que cerró otro modelo (por saldo) los revisa Opus.
REVISAR="${RO_REVISAR:-1}"                               # 0 = sin revisiones
REVISIONES_MAX="${RO_REVISIONES_MAX:-2}"                 # veces que un paso se puede reabrir por revisión
TOPE_REVISION="${RO_TOPE_REVISION:-1500}"
PROMPT="$RAIZ/migracion/PROMPT_NOCHE.md"
PROMPT_REVISA="$RAIZ/migracion/PROMPT_REVISA.md"
REVISIONES="$FUERA/revisiones"; INICIOS="$FUERA/inicio_pasos.txt"   # veredictos y commit con que empezó cada paso
# Notas de Claude desde GitHub: Claude sigue la noche desde fuera (la rama migracion/v2 se sube tras cada paso) y deja
# sus correcciones en migracion/NOTAS_REVISOR.md de su rama. Cada «## PARA: F2.3» va a ese paso; si ya estaba ✅, se reabre.
RAMA_REVISOR="${RO_RAMA_REVISOR:-origin/claude/project-thread-rjes21}"
NOTAS="$FUERA/notas_revisor"
CUADERNO="$RAIZ/migracion/PROGRESO.md"
PLAN_NOCHE="$RAIZ/migracion/PLAN_NOCHE.md"
PLAN_GUARDADO="$FUERA/PLAN_NOCHE.auditado.md"
PLAN="$RAIZ/migracion/PLAN_VUELTA.md"
MARCA="$FUERA/noche_en_curso"
. migracion/_agente.sh
PLANTILLA_PLAN="${RO_AGENTE_PLAN:-$PLANTILLA}"

dice_terminado() { grep -q "^ESTADO: TERMINADO" "$CUADERNO" 2>/dev/null; }
quedan_pasos() { grep -qE '^[[:space:]]*-[[:space:]]*(⬜|🔄)[[:space:]]*[*_`]*[[:space:]]*F[0-9]' "$CUADERNO" 2>/dev/null; }
terminado() { dice_terminado && ! quedan_pasos; }   # «TERMINADO» con pasos sin cerrar no acaba la noche
hora_de() { date -r "$1" '+%Y-%m-%d %H:%M' 2>/dev/null || date -d "@$1" '+%Y-%m-%d %H:%M'; }

# --- una sola noche a la vez ----------------------------------------------------------------------------------------
# Si se cerró la ventana de la terminal, la vuelta de Cursor pudo quedar suelta (va en su propio grupo): se corta antes
# de empezar, para que nunca trabajen dos agentes a la vez sobre el mismo código.
CERROJO="$FUERA/noche.lock"
if ! mkdir "$CERROJO" 2>/dev/null; then
  viejo="$(cat "$CERROJO/pid" 2>/dev/null)"
  if [ -n "$viejo" ] && [ "$viejo" != "$$" ] && kill -0 "$viejo" 2>/dev/null; then
    echo "✘ Ya hay una noche en marcha (proceso $viejo). Si de verdad no la hay: rm -rf $CERROJO"; exit 1
  fi
  grupo="$(cat "$CERROJO/grupo" 2>/dev/null)"
  if [ -n "$grupo" ] && kill -0 -- "-$grupo" 2>/dev/null; then
    echo "⚠ Quedaba una vuelta de Cursor suelta de antes (grupo $grupo): la corto."
    kill -TERM -- "-$grupo" 2>/dev/null; sleep 5; kill -KILL -- "-$grupo" 2>/dev/null
  fi
fi
echo $$ > "$CERROJO/pid"; rm -f "$CERROJO/grupo"
trap 'rm -rf "$CERROJO"' EXIT

# --- noche nueva o la misma de antes --------------------------------------------------------------------------------
nueva=1
if [ -s "$MARCA" ] && [ "${RO_NOCHE_NUEVA:-}" != "1" ]; then
  FIN="$(cat "$MARCA")"
  if [ "$FIN" -gt "$(date +%s)" ] 2>/dev/null; then
    nueva=""; echo "Sigo la noche empezada (fin $(hora_de "$FIN")). Para empezar otra: RO_NOCHE_NUEVA=1 bash migracion/noche.sh"
  else echo "La noche anterior acabó a las $(hora_de "$FIN") sin terminar: empiezo una nueva desde lo que diga PROGRESO.md."; fi
fi
# El ensayo cambia ~/RO_MIGRACION por la suya mientras dura: nunca una noche de verdad encima de un ensayo a medias.
if [ -L "$FUERA" ] || ls -d "$FUERA".real_* >/dev/null 2>&1; then
  echo "✘ $FUERA apunta a un ensayo o hay un ensayo sin cerrar ($(ls -d "$FUERA".real_* 2>/dev/null | head -1))."
  echo "  Ciérralo con: bash migracion/ensayo.sh --cerrar"; exit 1
fi

if [ -n "$nueva" ]; then
  # 1. lo que cambió el plan fuera de migracion/ (config.py, despliegue/, fuentes/…), sin pisar lo de Astra; una vez por noche
  rm -f "$FUERA/sin_saldo.txt"   # el saldo se mira de nuevo cada noche
  bash migracion/servicios.sh parar >/dev/null 2>&1 || true   # nada suelto de otra noche o del ensayo en los puertos
  bash migracion/juntar_plan.sh || echo "⚠ juntar_plan.sh falló: F1.3 lo repite"
  # 2. el plan de la noche, escrito y auditado (si ya lo está y nada cambió, esto tarda un segundo)
  #    Con tope: si el plan no estaba hecho de antes, como mucho RO_HORAS_PLAN horas (8); después la noche empieza con lo que haya.
  if [ "${RO_SIN_PLAN:-}" != "1" ]; then
    RO_PLAN_FIN=$(( $(date +%s) + ${RO_HORAS_PLAN:-8} * 3600 )) bash migracion/planear.sh \
      || echo "⚠ planear.sh no terminó: la noche sigue con el plan que haya y con PROMPTS_CURSOR.md"
  fi
  # 3. sin restos de otra noche o del ensayo
  rm -f "$PLAN" "$FUERA/replan_claves.txt"
  # la huella de la referencia solo se borra si la fase 1 se va a grabar de nuevo (F1.7 sin cerrar)
  grep -q "^- ✅ F1.7" "$CUADERNO" 2>/dev/null || rm -f "$FUERA/huellas_referencia.txt" "$FUERA/commit_f17.txt"
  rm -f "$PLAN_GUARDADO"; [ -f "$PLAN_NOCHE" ] && { cp "$PLAN_NOCHE" "$PLAN_GUARDADO"; chmod 444 "$PLAN_GUARDADO"; }
  # 4. la rama de la noche, puesta desde aquí (el agente no tiene que pelearse con ella)
  if [ "$(git symbolic-ref -q --short HEAD)" != "migracion/v2" ]; then
    git switch migracion/v2 2>/dev/null || git switch -c migracion/v2 2>/dev/null
  fi
  [ "$(git symbolic-ref -q --short HEAD)" = "migracion/v2" ] || {
    echo "✘ No puedo poner la rama migracion/v2 (¿cambios sin commit que chocan con ella?). Mira «git status» y vuelve a lanzar."; exit 1; }
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
if [ -z "$nueva" ] && [ ! -f "$HUELLAS" ] && [ -d "$COPIA_JUECES" ]; then
  echo "✘ Las huellas de esta noche ($HUELLAS) han desaparecido a mitad de noche: no se rehacen sobre ficheros que pudo tocar el agente."
  echo "  Mira «git diff» de los ficheros que juzgan y «git log». Para empezar una noche nueva a sabiendas: RO_NOCHE_NUEVA=1 bash migracion/noche.sh"
  exit 1
fi
if [ -n "$nueva" ] && [ -f "$HUELLAS" ] && [ -x "$FUERA/comprobar_manana.sh" ]; then
  # antes de rehacer las huellas, que la noche anterior no dejara jueces cambiados (si no, se volverían la nueva vara)
  if ! bash "$FUERA/comprobar_manana.sh" --huellas > "$LOGS/huellas_noche_anterior.txt" 2>&1 && [ "${RO_ACEPTO_JUECES:-}" != "1" ]; then
    echo "✘ La noche anterior dejó cambiados ficheros que juzgan, excepciones sin id o la referencia regrabada:"
    sed 's/^/   /' "$LOGS/huellas_noche_anterior.txt" | head -30
    echo "  Míralo con: bash $FUERA/comprobar_manana.sh"
    echo "  Si esos cambios son buenos (los hiciste tú de día): RO_ACEPTO_JUECES=1 bash migracion/noche.sh"
    exit 1
  fi
fi
if [ -n "$nueva" ] || [ ! -f "$HUELLAS" ]; then
  if [ -f "$HUELLAS" ]; then   # las de la noche anterior se guardan, no se borran
    archivo="$FUERA/huellas_anteriores/$(date '+%m%d_%H%M%S')"; mkdir -p "$archivo"
    mv "$HUELLAS" "$archivo/" 2>/dev/null; [ -d "$COPIA_JUECES" ] && mv "$COPIA_JUECES" "$archivo/" 2>/dev/null
  fi
  chmod -R u+w "$COPIA_JUECES" 2>/dev/null; rm -rf "$COPIA_JUECES"; rm -f "$HUELLAS"
  [ -e "$COPIA_JUECES" ] && { echo "✘ No puedo apartar $COPIA_JUECES (de otra noche): bórralo a mano y vuelve a lanzar."; exit 1; }
  mkdir -p "$COPIA_JUECES"
  ( for f in migracion/puerta.sh migracion/contrato.py migracion/contrato_escritura.py migracion/vectores_permisos.py \
             migracion/caidas.sh migracion/seguridad_http.py migracion/rendimiento.py migracion/servicios.sh \
             migracion/noche.sh migracion/planear.sh migracion/_agente.sh migracion/juntar_plan.sh migracion/revisar_plan.py \
             migracion/comprobar_manana.sh migracion/llaves_nube.py migracion/validar_sqlite.py \
             v2/tools/capturas/comparar.mjs v2/apps/api/src/permisos/rutas-declaradas.spec.ts \
             v2/packages/permisos/test/paridad.test.ts v2/package.json \
             migracion/PROMPT_NOCHE.md migracion/PROMPT_REPLAN.md migracion/PROMPT_REVISA.md .cursor/rules/*.mdc \
             pruebas_*.py despliegue/pruebas_noche.py despliegue/pruebas_tokens.py; do
      [ -f "$f" ] || continue
      mkdir -p "$COPIA_JUECES/$(dirname "$f")"; cp -p "$f" "$COPIA_JUECES/$f"
      shasum -a 256 "$f" 2>/dev/null || sha256sum "$f"
    done; echo "# $(date '+%Y-%m-%d %H:%M') · copias en $COPIA_JUECES" ) > "$HUELLAS"
  chmod -R a-w "$COPIA_JUECES"; chmod 444 "$HUELLAS"
  # la comprobación de la mañana se lanza desde fuera del repo: la de dentro la podría cambiar el agente
  rm -f "$FUERA/comprobar_manana.sh"; cp migracion/comprobar_manana.sh "$FUERA/comprobar_manana.sh"; chmod 555 "$FUERA/comprobar_manana.sh"
  echo "$RAIZ" > "$FUERA/app_dir.txt"
  echo "Huellas y copias de los ficheros que juzgan: $HUELLAS"
fi
# Apúntalo (foto con el móvil): por la mañana, si no coincide, alguien cambió las huellas.
echo "Huella de las huellas: $( (shasum -a 256 "$HUELLAS" 2>/dev/null || sha256sum "$HUELLAS") | cut -c1-16)"
# las reglas del agente se leen de la copia de fuera: el agente no puede reescribirse sus propias reglas
if [ -f "$COPIA_JUECES/migracion/PROMPT_NOCHE.md" ]; then
  PROMPT="$COPIA_JUECES/migracion/PROMPT_NOCHE.md"
fi
if [ -f "$COPIA_JUECES/migracion/PROMPT_REPLAN.md" ]; then PROMPT_REPLAN="$COPIA_JUECES/migracion/PROMPT_REPLAN.md"
fi
[ -f "$COPIA_JUECES/migracion/PROMPT_REVISA.md" ] && PROMPT_REVISA="$COPIA_JUECES/migracion/PROMPT_REVISA.md"

# --- el reloj (empieza a contar cuando el plan está listo) ------------------------------------------------------------
if [ -n "$nueva" ]; then FIN=$(( $(date +%s) + HORAS * 3600 )); echo "$FIN" > "$MARCA"; fi
RO_FIN_NOCHE="$(hora_de "$FIN")"; export RO_FIN_NOCHE

# --- el Mac despierto ------------------------------------------------------------------------------------------------
if command -v caffeinate >/dev/null; then caffeinate -dimsu -w $$ & fi

echo "Noche de migración · hasta $RO_FIN_NOCHE · planea $MODELO_PLAN · Opus ($MODELO_OPUS): ${PASOS_OPUS:-nada} + F5.10 de ${GRAVEDAD_OPUS:-nada} · Sonnet ($MODELO_SONNET): ${PASOS_SONNET:-nada} · el resto $MODELO · revisión de cada paso de Grok: $([ "$REVISAR" = 1 ] && echo "sí (Sonnet; los de Opus, Opus)" || echo no)"
echo "Plan: $(head -1 "$PLAN_NOCHE" 2>/dev/null || echo 'NO HAY PLAN_NOCHE.md: se sigue PROMPTS_CURSOR.md')"
echo "Cuaderno: $CUADERNO · registros: $LOGS"

# paso en curso según el cuaderno: el 🔄, o el primer ⬜. Imprime «F2.3 2 -» o «F5.10 2 L-03» (paso, intento, fallo).
paso_actual() {
  python3 - "$CUADERNO" <<'PY'
import re, sys
texto = open(sys.argv[1], encoding="utf-8").read()
# solo la lista de pasos (desde «## Fase 1»): una nota vieja en «## En curso» no cuenta
i = texto.find("\n## Fase")
lineas = (texto[i:] if i >= 0 else texto).splitlines()
def paso(marca):
    for linea in lineas:
        m = re.match(r"^\s*-\s*" + marca + r"\s*[*_`]*\s*(F\d+\.\d+)\b(.*)$", linea)
        if m:
            return m
m = paso("🔄")
if m:
    resto = m.group(2)
    # la marca que pone el agente: «· hh:mm · [L-03 ·] intento 2/3»; la descripción del paso no cuenta
    marcas = re.findall(r"·\s*\d{1,2}:\d{2}\s*·\s*(?:\**([LN])-(\d+)\**\s*·\s*)?intento\s*(\d+)", resto, re.I)
    if marcas:
        letra, num, intento = marcas[-1]
    else:
        letra = num = ""; i = re.search(r"intento\s*(\d+)\s*/\s*3", resto, re.I); intento = i.group(1) if i else "1"
    fallo = f"{letra}-{int(num):02d}" if (letra and m.group(1) == "F5.10") else "-"
    print(m.group(1), intento, fallo)
else:
    m = paso("⬜")
    print(m.group(1) + " 1 -" if m else "")
PY
}
# gravedad <id> · columna «Gravedad» de PENDIENTES_LOGICA.md (manda la copia de ~/RO_MIGRACION si existe)
gravedad() {
  local f g
  for f in "$FUERA/PENDIENTES_LOGICA.md" "$RAIZ/migracion/PENDIENTES_LOGICA.md"; do
    g="$(grep -m1 -E "^\|[[:space:]]*$1[[:space:]]*\|" "$f" 2>/dev/null | cut -d'|' -f3 | tr -d ' *')"
    [ -n "$g" ] && { echo "$g"; return; }
  done
}
en_lista() { case " $2 " in *" $1 "*) return 0 ;; esac; return 1; }   # en_lista <palabra> <lista>
SIN_SALDO="$FUERA/sin_saldo.txt"   # una línea por modelo que se quedó sin saldo esta noche
sin_saldo() { grep -qxF "$1" "$SIN_SALDO" 2>/dev/null; }
# con_saldo <modelo> [<siguiente>…] · el primero de la cadena que aún tiene saldo (el último, Grok, siempre vale)
con_saldo() { local m; for m in "$@"; do sin_saldo "$m" || { echo "$m"; return; }; done; echo "$MODELO"; }
modelo_de() {   # modelo_de <paso> <fallo de F5.10 o «-»>
  local nivel=grok
  if en_lista "$1" "$PASOS_OPUS"; then nivel=opus
  elif en_lista "$1" "$PASOS_SONNET"; then nivel=sonnet; fi
  if [ "$1" = "F5.10" ] && [ "${2:--}" != "-" ]; then
    local g; g="$(gravedad "$2")"
    if [ -n "$g" ] && en_lista "$g" "$GRAVEDAD_OPUS"; then nivel=opus
    elif [ -n "$g" ] && en_lista "$g" "$GRAVEDAD_GROK"; then nivel=grok; fi
  fi
  case $nivel in
    opus) con_saldo "$MODELO_OPUS" "$MODELO_SONNET" "$MODELO" ;;
    sonnet) con_saldo "$MODELO_SONNET" "$MODELO" ;;
    *) echo "$MODELO" ;;
  esac
}
modelo_plan() { con_saldo "$MODELO_PLAN" "$MODELO_OPUS" "$MODELO_SONNET"; }
apuntar_sin_saldo() {   # apuntar_sin_saldo <modelo> <registro>
  [ "$1" = "$MODELO" ] && return 0     # Grok es el último escalón: se espera y se reintenta, como siempre
  sin_saldo "$1" || { echo "$1" >> "$SIN_SALDO"; echo "  ⚠ $1 sin saldo ($(tail -1 "$2" | cut -c1-100)): sus pasos bajan un escalón el resto de la noche"; }
}
huella() { (git rev-parse HEAD; suma "$CUADERNO"; arbol) 2>/dev/null | tr '\n' ' '; }
plan_vigente_para() { head -1 "$PLAN" 2>/dev/null | grep -qF "PLAN: VIGENTE · $1 · "; }        # <clave>
plan_vigente_intento() { head -1 "$PLAN" 2>/dev/null | grep -qF "PLAN: VIGENTE · $1 · intento $2 "; }
CLAVES="$FUERA/replan_claves.txt"   # una línea «<clave>|<intento>» por cada vez que se llamó a Fable de guardia
veces() { local n; n="$(grep -cxF "$1" "$CLAVES" 2>/dev/null)"; echo "${n:-0}"; }

# El plan de la noche no lo cambia el ejecutor: si aparece cambiado, se vuelve al auditado.
guardar_plan() {
  [ -f "$PLAN_GUARDADO" ] || return 0
  if ! cmp -s "$PLAN_GUARDADO" "$PLAN_NOCHE"; then
    cp "$PLAN_NOCHE" "$LOGS/PLAN_NOCHE.cambiado.$(date +%H%M%S).md" 2>/dev/null
    cat "$PLAN_GUARDADO" > "$PLAN_NOCHE"; echo "  ⚠ PLAN_NOCHE.md había cambiado: vuelto al auditado"
  fi
}

# Lo grabado en la fase 1 (contrato, fotos, casos, bases de partida, la app de hoy congelada) es la vara de medir:
# al cerrar F1.7 se guarda su huella y el commit, y por la mañana comprobar_manana.sh mira que nada de eso se regrabó.
huellas_referencia() {
  [ -f "$FUERA/huellas_referencia.txt" ] && return 0
  grep -q "^- ✅ F1.7" "$CUADERNO" 2>/dev/null || return 0
  git rev-parse HEAD > "$FUERA/commit_f17.txt"
  # sin los vectores (F5.10 los regenera a propósito) ni excepciones_solidez.txt (F5.10 quita la línea de N-13);
  # de la app congelada (ref) solo el código: servir.py escribe ahí sus anclas y su estado
  ( cd "$FUERA" && { for d in contrato/viejo capturas/viejo casos_escritura.json local.db.antes tuberia.db.antes; do
      [ -e "$d" ] && find "$d" -type f ! -name '*.db' ! -name '*.db-*' ! -name '*.log' 2>/dev/null
    done
    [ -d ref ] && find ref -type f \( -name '*.py' -o -name '*.js' -o -name '*.html' -o -name '*.css' -o -name '*.sql' \) \
      ! -path 'ref/data/*' ! -path '*/node_modules/*' ! -path '*/__pycache__/*' 2>/dev/null
    } | LC_ALL=C sort | while IFS= read -r f; do shasum -a 256 "$f" 2>/dev/null || sha256sum "$f"; done
  ) > "$FUERA/huellas_referencia.txt"
  chmod 444 "$FUERA/huellas_referencia.txt"
  echo "  Referencia de la fase 1 cerrada: huella guardada ($(wc -l < "$FUERA/huellas_referencia.txt" | tr -d ' ') ficheros)"
}

replanear() {   # replanear <clave> <intento> <motivo>
  planes=$((planes + 1)); echo "$1|$2" >> "$CLAVES"
  local log="$LOGS/replan_$(printf %03d $planes).log" antes; antes="$(arbol)"
  echo "[$(date '+%H:%M')] Fable de guardia ($1, intento $2: $3) → $log"
  local msg; msg="$(cat "${PROMPT_REPLAN:-$RAIZ/migracion/PROMPT_REPLAN.md}")

MENSAJE DEL SUPERVISOR: paso $1, intento $2. Te llamo porque: $3.
Primera línea exacta de PLAN_VUELTA.md: PLAN: VIGENTE · $1 · intento $2 · <hora>
Último registro del ejecutor: $LOGS/vuelta_$(printf %03d $vuelta).log"
  local h_antes; h_antes="$(suma "$PLAN")"
  local mp; mp="$(modelo_plan)"
  if lanzar "$mp" "$msg" "$log" "$TOPE_REPLAN" "$PLANTILLA_PLAN" && [ "$(suma "$PLAN")" != "$h_antes" ] && plan_vigente_para "$1"; then
    fallos_plan=0
  else
    sin_saldo_en "$log" && apuntar_sin_saldo "$mp" "$log"
    fallos_plan=$((fallos_plan + 1)); ultimo_fallo_plan=$(date +%s)
    echo "  ⚠ el plan de guardia no se escribió bien ($(tail -1 "$log" | cut -c1-120))"
  fi
  [ "$(arbol)" = "$antes" ] || echo "  ⚠ la vuelta de guardia cambió código (solo debía escribir PLAN_VUELTA.md): mira $log"
}

# --- la revisión de cada paso cerrado -----------------------------------------------------------------------------------
hechos() { grep -oE '^[[:space:]]*-[[:space:]]*✅[[:space:]]*[*_`]*[[:space:]]*F[0-9]+\.[0-9]+' "$CUADERNO" 2>/dev/null | grep -oE 'F[0-9]+\.[0-9]+'; }
revisor_de() {   # revisor_de <paso> <modelo que lo cerró> · vacío = sin revisión
  local r=""
  if en_lista "$1" "$PASOS_OPUS" && [ "$2" != "$MODELO_OPUS" ]; then r="$(con_saldo "$MODELO_OPUS" "$MODELO_SONNET")"
  elif [ "$2" = "$MODELO" ]; then r="$(con_saldo "$MODELO_SONNET" "$MODELO_OPUS")"; fi
  [ "$r" = "$MODELO" ] && r=""   # sin saldo de pago: Grok no se revisa a sí mismo
  echo "$r"
}
reabrir() {   # reabrir <paso> <intento> · su ✅ vuelve a 🔄 con la marca que lee paso_actual
  python3 - "$CUADERNO" "$1" "$2" "$(date +%H:%M)" <<'PY'
import re, sys
p, paso, it, hora = sys.argv[1:]
t = open(p, encoding="utf-8").read()
i = t.find("\n## Fase")
cab, cuerpo = (t[:i], t[i:]) if i >= 0 else ("", t)
pat = re.compile(r"^(\s*-\s*)✅(\s*[*_`]*\s*" + re.escape(paso) + r"\b[^\n]*)$", re.M)
cuerpo, n = pat.subn(lambda m: f"{m.group(1)}🔄{m.group(2)} · {hora} · intento {it}/3 · revisión: rehacer con migracion/PLAN_VUELTA.md", cuerpo, count=1)
open(p, "w", encoding="utf-8").write(cab + cuerpo)
sys.exit(0 if n else 1)
PY
}
revisar() {   # revisar <paso> <modelo que lo cerró> · sale 1 si el paso se reabrió
  [ "$REVISAR" = 1 ] || return 0
  local r; r="$(revisor_de "$1" "$2")"; [ -n "$r" ] || return 0
  if [ $(( FIN - $(date +%s) )) -lt 4500 ]; then echo "  · $1 sin revisión: queda menos de 1 h 15"; return 0; fi
  mkdir -p "$REVISIONES"
  local malas k salida log inicio antes veredicto msg
  malas="$(grep -c "^$1 MAL " "$REVISIONES/registro.txt" 2>/dev/null)"; malas="${malas:-0}"
  k=$(( $(ls "$REVISIONES" 2>/dev/null | grep -c "^${1}_") + 1 ))
  salida="$REVISIONES/${1}_$k.md"; log="$LOGS/revision_${1}_$k.log"
  inicio="$(grep -m1 "^$1 " "$INICIOS" 2>/dev/null | cut -d' ' -f2)"; inicio="${inicio:-HEAD~1}"
  antes="$(arbol)"
  echo "[$(date '+%H:%M')] revisión $k de $1 (lo cerró $2) · $r → $log"
  msg="$(cat "$PROMPT_REVISA")

MENSAJE DEL SUPERVISOR: revisa el paso $1, que acaba de cerrar $2. Commit de inicio del paso: $inicio.
Escribe tu veredicto en: $salida"
  if ! lanzar "$r" "$msg" "$log" "$TOPE_REVISION" "$PLANTILLA_PLAN" && sin_saldo_en "$log" && ! sin_saldo "$r"; then
    apuntar_sin_saldo "$r" "$log"; revisar "$1" "$2"; return $?   # lo revisa el siguiente con saldo
  fi
  [ "$(arbol)" = "$antes" ] || echo "  ⚠ la revisión cambió código (solo debía escribir $salida): mira $log"
  veredicto="$(head -1 "$salida" 2>/dev/null)"
  case "$veredicto" in
    "REVISIÓN: BIEN"*) echo "$1 BIEN $k" >> "$REVISIONES/registro.txt"; echo "  ✔ revisión: $1 está bien"
      sed -n 2,3p "$salida" | grep -q . && echo "- $1: $(sed -n 2p "$salida" | cut -c1-300) ($salida)" >> "$REVISIONES/PARA_EL_INFORME.md"
      return 0 ;;
    "REVISIÓN: MAL"*)
      if [ "$malas" -ge "$REVISIONES_MAX" ]; then
        echo "$1 SIGUE-MAL $k" >> "$REVISIONES/registro.txt"
        echo "- $1: tras $malas arreglos la revisión sigue viendo fallos: $salida" >> "$REVISIONES/PARA_EL_INFORME.md"
        echo "  ⚠ revisión: $1 sigue mal tras $malas arreglos; se queda cerrado y va al informe ($salida)"; return 0
      fi
      echo "$1 MAL $k" >> "$REVISIONES/registro.txt"
      local it=$((malas + 2)); [ $it -gt 3 ] && it=3
      if reabrir "$1" "$it"; then
        { echo "PLAN: VIGENTE · $1 · intento $it · $(date +%H:%M)"
          echo "Lo pide la revisión ($salida): el paso se marcó ✅ sin estar bien. Arréglalo y vuelve a cerrarlo."
          tail -n +2 "$salida"; } > "$PLAN"
        echo "  ✘ revisión: $1 no está bien; se reabre (intento $it) con el plan del revisor"; return 1
      fi
      echo "  ⚠ revisión: no encuentro la línea ✅ de $1 en PROGRESO.md para reabrirla" ;;
    *) echo "  ⚠ la revisión de $1 no dejó veredicto (mira $log): se sigue" ;;
  esac
  return 0
}

# --- Claude desde fuera: subir cada paso y leer sus notas ------------------------------------------------------------
subir() {   # copia en GitHub tras cada paso cerrado, para que Claude lo revise; nunca --force ni otra rama
  [ "${RO_SUBIR:-1}" = 1 ] || return 0
  [ "$(git symbolic-ref -q --short HEAD)" = "migracion/v2" ] || return 0
  ( git push -q origin migracion/v2 >> "$LOGS/subir.log" 2>&1 || echo "$(date '+%H:%M') push falló" >> "$LOGS/subir.log" ) &
}
ultima_mirada=0
leer_notas() {
  [ "${RO_NOTAS_REVISOR:-1}" = 1 ] || return 0
  local ahora blob f p; ahora=$(date +%s)
  [ $((ahora - ultima_mirada)) -ge "${RO_NOTAS_CADA:-300}" ] || return 0; ultima_mirada=$ahora   # como mucho cada 5 min
  git fetch -q origin "${RAMA_REVISOR#origin/}" 2>/dev/null || return 0
  blob="$(git rev-parse -q --verify "$RAMA_REVISOR:migracion/NOTAS_REVISOR.md" 2>/dev/null)" || return 0
  mkdir -p "$NOTAS"; grep -qxF "$blob" "$NOTAS/leidas.txt" 2>/dev/null && return 0
  echo "$blob" >> "$NOTAS/leidas.txt"; git show "$blob" > "$NOTAS/ultima.md" 2>/dev/null || return 0
  rm -f "$NOTAS"/*.nueva
  awk -v d="$NOTAS" '/^## PARA: F[0-9]+\.[0-9]+[[:space:]]*$/ {f=d "/" $3 ".nueva"; next} /^## / {f=""} f {print > f}' "$NOTAS/ultima.md"
  for f in "$NOTAS"/*.nueva; do
    [ -f "$f" ] || continue; p="$(basename "$f" .nueva)"; mv "$f" "$NOTAS/$p.md"
    echo "  ✉ nota de Claude para $p ($(wc -l < "$NOTAS/$p.md" | tr -d ' ') líneas)"
    if hechos | grep -qxF "$p" && reabrir "$p" 2; then
      { echo "PLAN: VIGENTE · $p · intento 2 · $(date +%H:%M)"
        echo "Lo pide Claude, que revisa la noche desde fuera: el paso se cerró sin estar bien. Arréglalo y vuelve a cerrarlo."
        cat "$NOTAS/$p.md"; } > "$PLAN"
      echo "$p NOTA-REABRE $(date +%H:%M)" >> "$REVISIONES/registro.txt" 2>/dev/null
      echo "  ✘ $p se reabre por la nota de Claude"
    fi
  done
}

# al relanzar la misma noche, los registros siguen numerándose (no se pisan los de antes)
vuelta=$(ls "$LOGS"/vuelta_*.log 2>/dev/null | wc -l | tr -d ' '); planes=$(ls "$LOGS"/replan_*.log 2>/dev/null | wc -l | tr -d ' ')
[ -n "$nueva" ] && { mkdir -p "$LOGS/antes"; mv "$LOGS"/vuelta_* "$LOGS"/replan_* "$LOGS"/revision_* "$LOGS/antes/" 2>/dev/null; vuelta=0; planes=0
  rm -rf "$REVISIONES.antes"; [ -d "$REVISIONES" ] && mv "$REVISIONES" "$REVISIONES.antes"; rm -f "$INICIOS"
  mkdir -p "$NOTAS"; rm -f "$NOTAS"/F*.md; }   # las leídas se quedan: una nota vieja no se aplica dos veces
fallos_seguidos=0; sin_avance=0; fallos_plan=0; ultimo_fallo_plan=0
while [ "$(date +%s)" -lt "$FIN" ] && ! terminado; do
  guardar_plan
  huellas_referencia
  leer_notas
  read -r paso intento fallo <<< "$(paso_actual)"; paso="${paso:-}"; intento="${intento:-1}"; fallo="${fallo:--}"
  clave="$paso"; [ "$fallo" != "-" ] && clave="$paso $fallo"
  # al cambiar de paso (o de fallo), un plan de guardia que no es para el nuevo ya no vale: ni su GASTADO
  # (al relanzar no se sabe de qué paso era un GASTADO: se conserva y lo trata Fable de guardia)
  if [ "$clave" != "${clave_anterior:-}" ] && [ -f "$PLAN" ] && ! plan_vigente_para "$clave"; then
    if [ -n "${clave_anterior:-}" ] || head -1 "$PLAN" | grep -q "^PLAN: VIGENTE"; then rm -f "$PLAN"; fi
  fi
  clave_anterior="$clave"
  [ -n "$paso" ] && ! grep -q "^$paso " "$INICIOS" 2>/dev/null && echo "$paso $(git rev-parse HEAD 2>/dev/null)" >> "$INICIOS"
  # Fable de guardia: si dejó de responder, se le vuelve a probar a la media hora
  if [ $fallos_plan -ge 2 ] && [ $(( $(date +%s) - ultimo_fallo_plan )) -ge 1800 ]; then fallos_plan=0; fi
  replan=""
  # Como mucho dos llamadas por paso (o fallo de F5.10) e intento: nunca una por vuelta.
  if [ -n "$paso" ] && [ $fallos_plan -lt 2 ]; then
    n="$(veces "$clave|$intento")"
    if head -1 "$PLAN" 2>/dev/null | grep -q "^PLAN: GASTADO" && [ "$n" -lt 2 ]; then
      replanear "$clave" "$intento" "el ejecutor marcó el plan como gastado: $(head -1 "$PLAN" | cut -c1-200)"; replan=1
    elif [ "$intento" -ge 2 ] && ! plan_vigente_intento "$clave" "$intento" && [ "$n" -eq 0 ]; then
      replanear "$clave" "$intento" "el intento $((intento - 1)) falló (mira «Intentos y notas» de PROGRESO.md)"; replan=1
    elif [ $sin_avance -eq 2 ] && [ "$n" -lt 2 ]; then
      replanear "$clave" "$intento" "dos vueltas seguidas sin cambiar ni el cuaderno ni el código"; replan=1
    fi
  fi

  vuelta=$((vuelta + 1))
  log="$LOGS/vuelta_$(printf %03d $vuelta).log"
  modelo="$(modelo_de "$paso" "$fallo")"
  antes="$(huella)"; hechos_antes=" $(hechos | tr '\n' ' ') "
  echo "[$(date '+%H:%M')] vuelta $vuelta · ${paso:-?} intento $intento · $modelo → $log"
  mensaje="$(cat "$PROMPT")

MENSAJE DEL SUPERVISOR (vuelta $vuelta, $(date '+%H:%M')): según el cuaderno toca ${clave:-(no lo sé: léelo tú)}, intento $intento.
Su sección del plan: python3 migracion/revisar_plan.py --seccion ${clave:-<paso>}"
  if plan_vigente_para "$clave"; then
    mensaje="$mensaje
Hay un plan de guardia VIGENTE para este paso en migracion/PLAN_VUELTA.md${replan:+ (recién escrito)}: síguelo antes que la sección."
  fi
  if [ -n "$paso" ] && [ -s "$NOTAS/$paso.md" ]; then
    mensaje="$mensaje
NOTA DE CLAUDE para $paso (revisa la noche desde fuera; manda sobre la sección del plan, nunca sobre PROMPT_NOCHE.md ni .cursor/rules):
$(cat "$NOTAS/$paso.md")"
  fi
  if dice_terminado; then
    mensaje="$mensaje
AVISO: PROGRESO.md dice «ESTADO: TERMINADO» pero quedan pasos en ⬜ o 🔄. Ciérralos (✅, o ⚠ con su motivo y plan B) antes de dar la noche por terminada."
  fi
  if [ $sin_avance -ge 2 ] && [ -z "$replan" ]; then
    mensaje="$mensaje
AVISO: las dos últimas vueltas no han cambiado ni el cuaderno ni el código. Aplica ya el plan B del paso en curso (márcalo ⚠ con el motivo) y pasa al siguiente."
  fi
  lanzar "$modelo" "$mensaje" "$log" "$TOPE_VUELTA"; codigo=$?
  despues="$(huella)"
  if [ -f "$log.cortada" ]; then   # lanzar() solo la deja si el vigía la mató de verdad
    echo "  ⚠ vuelta cortada a los $TOPE_VUELTA s (colgada o demasiado larga): se relanza"; codigo=0
  fi
  if [ $codigo -ne 0 ]; then
    fallos_seguidos=$((fallos_seguidos + 1))
    echo "  ⚠ Cursor salió con código $codigo ($(tail -1 "$log" | cut -c1-120))"
    if sin_saldo_en "$log" && [ "$modelo" != "$MODELO" ]; then apuntar_sin_saldo "$modelo" "$log"; fallos_seguidos=0; continue; fi
    # límite de uso, red o sesión caducada: espera creciente (máximo 10 min) y reintenta hasta la hora; nunca se rinde
    espera=$(( fallos_seguidos * 60 )); [ $espera -gt 600 ] && espera=600
    sleep $espera
    continue
  fi
  fallos_seguidos=0
  if [ "$antes" = "$despues" ]; then sin_avance=$((sin_avance + 1)); else sin_avance=0; fi
  cerrados=""
  for p in $(hechos); do   # pasos que esta vuelta acaba de cerrar: los revisa un modelo de pago
    case "$hechos_antes" in *" $p "*) continue ;; esac
    cerrados=1
    revisar "$p" "$modelo" || break   # reabierto: la siguiente vuelta lo rehace
  done
  [ -n "$cerrados" ] && subir
  if [ $sin_avance -ge 12 ]; then echo "✘ 12 vueltas seguidas sin cambiar nada: paro para no gastar. Mira $log"; break; fi
  [ $sin_avance -ge 6 ] && sleep 300      # algo raro: no quemar vueltas en bucle
done

if terminado; then rm -f "$MARCA"; echo "✔ Cursor ha terminado: lee migracion/INFORME_NOCHE.md"
else echo "⏰ Hora cumplida o parada: el cuaderno (migracion/PROGRESO.md) dice por dónde va."; fi
echo "Por la mañana, antes de creerte nada: bash $FUERA/comprobar_manana.sh"

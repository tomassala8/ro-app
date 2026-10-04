# migracion/_agente.sh · lo comparten noche.sh y planear.sh (se carga con «source»; no se lanza solo).
# Fija PLANTILLA (la orden de Cursor con {MODELO}) y da lanzar(): una vuelta de Cursor con TOPE de tiempo.

if [ -n "${RO_AGENTE:-}" ]; then PLANTILLA="$RO_AGENTE"
elif command -v cursor-agent >/dev/null; then PLANTILLA="cursor-agent -p --force --output-format text --model {MODELO}"
else
  echo "✘ No encuentro la orden «cursor-agent» (la terminal de Cursor)."
  echo "  Instálala: curl https://cursor.com/install -fsS | bash   y entra con: cursor-agent login"
  echo "  O lánzalo desde la ventana de Cursor pegando migracion/PROMPT_NOCHE.md (ver PLAN_MAESTRO §6)."
  exit 1
fi

suma() { md5 -q "$1" 2>/dev/null || md5sum "$1" 2>/dev/null | cut -d' ' -f1; }

# lanzar <modelo> <mensaje> <registro> <tope en segundos> [plantilla]   (si se corta por tiempo, deja <registro>.cortada)
# Una vuelta colgada (el modo -p a veces no sale) no puede bloquear la noche: pasado el tope se corta y se sigue.
lanzar() {
  local orden="${5:-$PLANTILLA}"; orden="${orden//\{MODELO\}/$1}"
  rm -f "$3.cortada"; : > "$3"
  # >> (añadir): así el aviso del vigía no lo pisa lo que escriba el proceso al morir
  # shellcheck disable=SC2086
  $orden "$2" >> "$3" 2>&1 < /dev/null &
  local pid=$!
  ( exec >/dev/null 2>&1; sleep "$4"; touch "$3.cortada"; echo "[supervisor] vuelta cortada a los $4 s" >> "$3"
    pkill -TERM -P "$pid" 2>/dev/null; kill -TERM "$pid" 2>/dev/null; sleep 20; kill -KILL "$pid" 2>/dev/null ) &
  local vigia=$!
  wait "$pid"; local codigo=$?
  pkill -P "$vigia" 2>/dev/null; kill "$vigia" 2>/dev/null; wait "$vigia" 2>/dev/null   # y su «sleep», que no quede suelto
  return $codigo
}

# arbol · huella del código del Mac tal como está en disco (sin commit), sin los ficheros de la noche que cambian solos.
# Es un objeto «tree» de git: dos huellas se comparan con «git diff --stat <vieja> <nueva>». No toca el índice de verdad.
arbol() {
  local idx; idx="$(mktemp -u "${TMPDIR:-/tmp}/ro_indice.XXXXXX")"
  GIT_INDEX_FILE="$idx" git read-tree HEAD 2>/dev/null
  GIT_INDEX_FILE="$idx" git add -A . 2>/dev/null
  GIT_INDEX_FILE="$idx" git rm -rq --cached --ignore-unmatch migracion/PLAN_NOCHE.md migracion/PLAN_VUELTA.md \
    migracion/PROGRESO.md migracion/NOTAS_NOCHE.md >/dev/null 2>&1
  GIT_INDEX_FILE="$idx" git write-tree; rm -f "$idx"
}

# sin_llaves · lo que necesita cualquier vuelta de Cursor esta noche (también la del planificador):
#  · RO_SIN_LLAVES=1: config.secreto() y config.de_donde() no leen nada;
#  · fuera del entorno toda variable con pinta de llave (las de Cursor se quedan: sin ellas no entra);
#  · una orden «security» falsa delante en el PATH que niega leer contraseñas del llavero (mire donde mire el argumento).
sin_llaves() {
  export RO_SIN_LLAVES=1
  unset RO_ENVIOS_REALES RO_CLICKUP_REAL PRISMA_USER_CONSENT_FOR_DANGEROUS_AI_ACTION
  local v
  for v in $(compgen -e); do
    case "$v" in
      CURSOR_*) ;;
      *_API_KEY|*_APIKEY|*_TOKEN|*_SECRET|*_SECRET_KEY|*_PASSWORD|*_PASS|*_ACCESS_KEY*|DATABASE_URL|*_DATABASE_URL) unset "$v" ;;
    esac
  done
  local bin="$FUERA/sin_llavero/bin"; mkdir -p "$bin"
  cat > "$bin/security" <<'FALSA'
#!/bin/sh
# Orden «security» de la noche de migración: el llavero está cerrado para el agente.
for a in "$@"; do
  case "$a" in
    find-generic-password|find-internet-password|find-certificate|find-identity|dump-keychain|export|unlock-keychain|show-keychain-info|set-key-partition-list)
      echo "security: el llavero está cerrado esta noche (migracion/noche.sh)" >&2; exit 44 ;;
  esac
done
exec /usr/bin/security "$@"
FALSA
  chmod 755 "$bin/security"
  case ":$PATH:" in *":$bin:"*) ;; *) export PATH="$bin:$PATH" ;; esac
}

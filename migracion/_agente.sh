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

# lanzar <modelo> <mensaje> <registro> <tope en segundos> [plantilla]
# Una vuelta colgada (el modo -p a veces no sale) no puede bloquear la noche: pasado el tope se corta y se sigue.
lanzar() {
  local orden="${5:-$PLANTILLA}"; orden="${orden//\{MODELO\}/$1}"
  # shellcheck disable=SC2086
  $orden "$2" > "$3" 2>&1 < /dev/null &
  local pid=$!
  ( sleep "$4"; echo "[supervisor] vuelta cortada a los $4 s" >> "$3"
    pkill -TERM -P "$pid" 2>/dev/null; kill -TERM "$pid" 2>/dev/null; sleep 20; kill -KILL "$pid" 2>/dev/null ) &
  local vigia=$!
  wait "$pid"; local codigo=$?
  kill "$vigia" 2>/dev/null; wait "$vigia" 2>/dev/null
  return $codigo
}

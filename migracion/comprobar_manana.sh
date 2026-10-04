#!/usr/bin/env bash
# comprobar_manana.sh · lo primero que se lanza por la mañana, ANTES de creerse PROGRESO.md.
#
#   bash ~/RO_MIGRACION/comprobar_manana.sh            # huellas + servicios de cero + puertas f2, f4, f3 (y f7 si hay informe)
#   bash ~/RO_MIGRACION/comprobar_manana.sh --huellas  # solo las huellas y las excepciones
#
# noche.sh deja una copia de este fichero en ~/RO_MIGRACION (la del repo la podría haber cambiado el agente): lanza esa.
# Si lanzas la del repo, se pasa sola a la de fuera.
# 1. Compara los ficheros que juzgan (puertas, contratos, baterías, y los scripts de la noche) con las huellas que guardó
#    noche.sh al empezar. Si alguno cambió, lo dice y enseña el diff: un agente que no pasaba una prueba pudo «arreglar»
#    la prueba. Las puertas se pasan entonces con la COPIA de antes (guardada fuera del repo), y al acabar se deja
#    el fichero como lo dejó la noche, para que lo mires.
# 2. Enseña las excepciones aceptadas esta noche (cada línea es una diferencia que las puertas no cuentan).
# 3. Reinicia todos los servicios desde cero y repite las puertas sin --rapido. Lo que diga esto es lo que vale.
set -o pipefail   # sin -u: el bash 3.2 del Mac falla con listas vacías
FUERA="${RO_MIGRACION:-$HOME/RO_MIGRACION}"
AQUI="$(cd "$(dirname "$0")" && pwd)/$(basename "$0")"
if [ "$AQUI" != "$FUERA/comprobar_manana.sh" ] && [ -f "$FUERA/comprobar_manana.sh" ]; then
  cmp -s "$AQUI" "$FUERA/comprobar_manana.sh" || echo "⚠ La copia del repo de comprobar_manana.sh cambió esta noche: uso la de $FUERA."
  exec bash "$FUERA/comprobar_manana.sh" "$@"
fi
APP="$(cat "$FUERA/app_dir.txt" 2>/dev/null)"
[ -n "$APP" ] || APP="$(cd "$(dirname "$0")/.." 2>/dev/null && pwd)"
cd "$APP" || { echo "✘ No encuentro el código de la app ($APP)"; exit 1; }
HUELLAS="$FUERA/huellas_puertas.txt"; COPIAS="$FUERA/huellas_copia"
export RO_MIGRACION="$FUERA" RO_SIN_LLAVES=1 RO_RELOJ="${RO_RELOJ:-2026-10-05T07:30}"
unset RO_ENVIOS_REALES RO_CLICKUP_REAL

[ -f "$HUELLAS" ] && [ -d "$COPIAS" ] || { echo "✘ No hay $HUELLAS o $COPIAS (noche.sh no llegó a guardarlas): revisa a mano «git diff» de migracion/ y pruebas_*.py"; exit 1; }

cambiados=()
while read -r suma fichero; do
  case "$suma" in \#*|"") continue ;; esac
  if [ ! -f "$fichero" ]; then cambiados+=("$fichero"); echo "✘ BORRADO: $fichero"; continue; fi
  ahora="$( (shasum -a 256 "$fichero" 2>/dev/null || sha256sum "$fichero") | cut -d' ' -f1)"
  [ "$ahora" = "$suma" ] || { cambiados+=("$fichero"); echo "✘ CAMBIADO: $fichero"; }
done < "$HUELLAS"

if [ ${#cambiados[@]} -eq 0 ]; then
  echo "✔ Ningún fichero que juzga ha cambiado esta noche ($(grep -c . "$HUELLAS") comprobados)."
else
  echo
  echo "⚠ ${#cambiados[@]} fichero(s) que juzgan cambiaron esta noche. Lo que cambió:"
  for f in "${cambiados[@]}"; do
    [ -f "$f" ] && { diff -u "$COPIAS/$f" "$f" | head -60; echo "  (…) diff -u $COPIAS/$f $f"; }
  done
  echo "  Las puertas de abajo se pasan con la copia de antes; al acabar, cada fichero vuelve a como lo dejó la noche."
fi

echo
echo "── excepciones aceptadas (diferencias que las puertas no cuentan) ──"
for e in "$FUERA"/excepciones*.txt; do
  [ -f "$e" ] || continue
  n="$(grep -cvE '^[[:space:]]*(#|$)' "$e")"
  echo "$(basename "$e"): $n línea(s)"; grep -vE '^[[:space:]]*(#|$)' "$e" | sed 's/^/   /' | head -40
done
echo "  Cada una debe llevar un id L-/N- de PENDIENTES_LOGICA.md (o ser del plan B de F2.4) y su motivo. Si no, es ROJO."
sin_id="$(cat "$FUERA"/excepciones.txt 2>/dev/null | grep -vE '^[[:space:]]*(#|$)' | grep -cvE '(L|N)-[0-9]|F2\.4')"
[ "${sin_id:-0}" -gt 0 ] && echo "✘ $sin_id excepción(es) sin id L-/N- ni F2.4: míralas antes de nada."
# La referencia de la fase 1 (contrato, fotos, casos, bases de partida, la app de hoy congelada) no se regraba.
regrabada=0
if [ -f "$FUERA/huellas_referencia.txt" ]; then
  r="$(cd "$FUERA" && (shasum -a 256 -c --quiet huellas_referencia.txt 2>/dev/null || sha256sum -c --quiet huellas_referencia.txt 2>/dev/null) | grep -v '^$' | head -20)"
  if [ -n "$r" ]; then regrabada=1; echo; echo "✘ La referencia de la fase 1 cambió después de F1.7 (no debía):"; echo "$r" | sed 's/^/   /'
  else echo "✔ La referencia de la fase 1 está como se grabó."; fi
else echo "· No hay huella de la referencia (la fase 1 no llegó a cerrarse)."; fi
# Piezas que usan las puertas y que se escriben durante la noche: no se pueden congelar, se enseñan para mirarlas.
if [ -s "$FUERA/commit_f17.txt" ]; then
  c17="$(cat "$FUERA/commit_f17.txt")"
  piezas="$(git -c core.quotePath=false diff --stat "$c17" -- migracion/baterias.sh migracion/escalados.py v2/package.json 'v2/**/package.json' \
    'v2/**/vitest.config.*' 'v2/**/jest*.json' 'v2/**/test/**' 'v2/**/*.e2e-spec.ts' v2/tools/capturas/capturar.mjs 2>/dev/null | tail -25)"
  [ -n "$piezas" ] && { echo; echo "⚠ Cambiaron desde el cierre de la fase 1 piezas que usan las puertas (míralas: ¿se ha relajado algo?):"; echo "$piezas" | sed 's/^/   /'; }
fi
# ficheros nuevos sin commit (un vitest.config nuevo que excluye pruebas no sale en el diff de arriba)
sueltos="$(git -c core.quotePath=false ls-files --others --exclude-standard -- v2 migracion 2>/dev/null | head -25)"
if [ -n "$sueltos" ]; then
  echo; echo "⚠ Ficheros nuevos sin commit en v2/ o migracion/ (míralos):"; echo "$sueltos" | sed 's/^/   /'

fi
[ "${1:-}" = "--huellas" ] && exit $(( ${#cambiados[@]} > 0 || ${sin_id:-0} > 0 || regrabada ))

# ficheros cambiados → copia de antes, solo mientras se pasan las puertas
noche="$(mktemp -d)"
for f in "${cambiados[@]}"; do
  [ -f "$f" ] && { mkdir -p "$noche/$(dirname "$f")"; cp -p "$f" "$noche/$f"; }
  mkdir -p "$(dirname "$f")"; cat "$COPIAS/$f" > "$f"
done
restaurar() {
  for f in "${cambiados[@]}"; do
    if [ -f "$noche/$f" ]; then cat "$noche/$f" > "$f"; else rm -f "$f"; fi
  done
  rm -rf "$noche"
}
trap restaurar EXIT

echo
echo "Reiniciando todos los servicios desde cero…"
bash migracion/servicios.sh parar >/dev/null 2>&1 || true
bash migracion/servicios.sh arrancar || { echo "✘ Los servicios no arrancan: eso ya es ROJO."; exit 1; }

resultado=0
fases="f2 f4 f3"; [ -s migracion/INFORME_NOCHE.md ] && fases="$fases f7"
for fase in $fases; do
  echo
  echo "── puerta $fase ──────────────────────────────"
  if bash migracion/puerta.sh "$fase"; then echo "✔ $fase VERDE"; else echo "✘ $fase ROJO (detalle en $FUERA/puertas/$fase.md)"; resultado=1; fi
done
echo
if [ $resultado -eq 0 ] && [ ${#cambiados[@]} -eq 0 ] && [ "${sin_id:-0}" -eq 0 ] && [ $regrabada -eq 0 ]; then
  echo "✔ TODO VERDE con las puertas de antes. PROGRESO.md es de fiar."
else
  echo "⚠ Hay algo que mirar antes de creerse PROGRESO.md (arriba)."
fi
exit $(( resultado || ${#cambiados[@]} > 0 || ${sin_id:-0} > 0 || regrabada ))

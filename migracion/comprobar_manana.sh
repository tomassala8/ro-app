#!/usr/bin/env bash
# migracion/comprobar_manana.sh · lo primero que se lanza por la mañana, ANTES de creerse PROGRESO.md.
#
#   bash migracion/comprobar_manana.sh            # huellas + servicios de cero + puertas f2, f4, f3 (y f7 si hay informe)
#   bash migracion/comprobar_manana.sh --huellas  # solo las huellas
#
# 1. Compara los ficheros que juzgan (puertas, contratos, baterías) con las huellas que guardó noche.sh al empezar.
#    Si alguno cambió, lo dice y enseña el diff: un agente que no pasaba una prueba pudo «arreglar» la prueba.
#    Las puertas se pasan entonces con la versión de ANTES (la del commit de las huellas), no con la de la noche.
# 2. Reinicia todos los servicios desde cero y repite las puertas sin --rapido. Lo que diga esto es lo que vale.
set -o pipefail   # sin -u: el bash 3.2 del Mac falla con listas vacías
cd "$(dirname "$0")/.."
FUERA="${RO_MIGRACION:-$HOME/RO_MIGRACION}"
HUELLAS="$FUERA/huellas_puertas.txt"
export RO_RELOJ="${RO_RELOJ:-2026-10-05T07:30}"

[ -f "$HUELLAS" ] || { echo "✘ No hay $HUELLAS (noche.sh no llegó a guardarlas): revisa a mano «git diff» de migracion/ y pruebas_*.py"; exit 1; }
COMMIT="$(sed -n 's/^# commit \([0-9a-f]*\).*/\1/p' "$HUELLAS")"

cambiados=()
while read -r suma fichero; do
  case "$suma" in \#*|"") continue ;; esac
  if [ ! -f "$fichero" ]; then cambiados+=("$fichero"); echo "✘ BORRADO: $fichero"; continue; fi
  ahora="$( (shasum -a 256 "$fichero" 2>/dev/null || sha256sum "$fichero") | cut -d' ' -f1)"
  [ "$ahora" = "$suma" ] || { cambiados+=("$fichero"); echo "✘ CAMBIADO: $fichero"; }
done < "$HUELLAS"

if [ ${#cambiados[@]} -eq 0 ]; then
  echo "✔ Ningún fichero de las puertas ha cambiado desde $COMMIT."
else
  echo
  echo "⚠ ${#cambiados[@]} fichero(s) de las puertas cambiaron esta noche. Diff contra $COMMIT:"
  git --no-pager diff --stat "$COMMIT" -- "${cambiados[@]}"
  echo "  Detalle: git diff $COMMIT -- ${cambiados[*]}"
  echo "  Las puertas de abajo se pasan con la versión de antes de esos ficheros (se restauran al terminar)."
fi
[ "${1:-}" = "--huellas" ] && exit $(( ${#cambiados[@]} > 0 ))

# ficheros cambiados → versión de antes, solo mientras se pasan las puertas
copia="$(mktemp -d)"
for f in "${cambiados[@]}"; do
  [ -f "$f" ] && { mkdir -p "$copia/$(dirname "$f")"; cp "$f" "$copia/$f"; }
  git show "$COMMIT:$f" > "$f" 2>/dev/null || true
done
restaurar() { for f in "${cambiados[@]}"; do [ -f "$copia/$f" ] && cp "$copia/$f" "$f"; done; rm -rf "$copia"; }
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
[ $resultado -eq 0 ] && [ ${#cambiados[@]} -eq 0 ] && echo "✔ TODO VERDE con las puertas de antes. PROGRESO.md es de fiar." \
  || echo "⚠ Hay algo que mirar antes de creerse PROGRESO.md (arriba)."
exit $(( resultado || ${#cambiados[@]} > 0 ))

#!/usr/bin/env bash
# migracion/juntar_plan.sh · trae al código del Mac lo que la rama del plan cambió FUERA de migracion/, v2/ y .cursor/
# (config.py, despliegue/, fuentes/, schema_v2.sql…), sin pisar el trabajo de Astra.
#
#   bash migracion/juntar_plan.sh            # junta y dice qué ha hecho con cada fichero
#   bash migracion/juntar_plan.sh --ver      # solo dice qué haría
#
# La orden de preparar_noche.sh («git checkout <rama> -- migracion v2 .cursor AGENTS.md») solo trae el plan. Sin esto,
# el Mac se quedaba sin los arreglos de base.py, la copia de cada hora, la noche sin llaves de config.py…
# Por cada fichero que la rama cambió respecto a main:
#   · el Mac lo tiene como main (Astra no lo ha tocado)      → se copia el de la rama
#   · el Mac ya lo tiene igual que la rama                   → nada
#   · los dos lo han cambiado                                → mezcla a tres bandas (git merge-file)
#   · la mezcla choca                                        → se queda el del Mac y se apunta: lo resuelve Cursor (F1.3)
# Nunca hace commit ni cambia de rama. Lo lanza noche.sh al empezar (antes de la instantánea de F1.3).
set -uo pipefail
cd "$(dirname "$0")/.."
RAMA="${RO_RAMA_PLAN:-origin/claude/project-thread-rjes21}"
VER=""; [ "${1:-}" = "--ver" ] && VER=1
FUERA="${RO_MIGRACION:-$HOME/RO_MIGRACION}"; mkdir -p "$FUERA"
CHOQUES="$FUERA/choques_plan.txt"

git fetch -q origin "${RAMA#origin/}" main 2>/dev/null || echo "⚠ sin red: uso lo que ya hay de $RAMA"
git rev-parse -q --verify "$RAMA" >/dev/null || { echo "✘ No encuentro $RAMA"; exit 1; }
BASE="$(git merge-base origin/main "$RAMA")"

tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
copiados=0; mezclados=0; iguales=0; choques=()
: > "$tmp/lista"
git diff --name-only "$BASE" "$RAMA" -- . ':!migracion' ':!v2' ':!.cursor' ':!AGENTS.md' > "$tmp/lista"
while IFS= read -r f; do
  [ -n "$f" ] || continue
  if ! git cat-file -e "$RAMA:$f" 2>/dev/null; then echo "  · $f: la rama lo borra; se deja como está"; continue; fi
  git show "$RAMA:$f" > "$tmp/rama"
  modo="$(git ls-tree "$RAMA" -- "$f" | awk '{print $1}')"
  if [ ! -f "$f" ]; then
    accion="nuevo"
  elif cmp -s "$f" "$tmp/rama"; then
    iguales=$((iguales + 1)); continue
  elif git cat-file -e "$BASE:$f" 2>/dev/null && git show "$BASE:$f" | cmp -s - "$f"; then
    accion="copia"
  else
    git show "$BASE:$f" > "$tmp/base" 2>/dev/null || : > "$tmp/base"
    cp "$f" "$tmp/mac"
    if git merge-file -q -p "$tmp/mac" "$tmp/base" "$tmp/rama" > "$tmp/mezcla" 2>/dev/null; then
      cmp -s "$tmp/mezcla" "$f" && { iguales=$((iguales + 1)); continue; }   # ya juntado en una vuelta anterior
      accion="mezcla"
    else choques+=("$f"); echo "  ✘ $f: el Mac y la rama cambian lo mismo; se queda el del Mac"; continue; fi
  fi
  echo "  ✔ $f: $accion"
  [ -n "$VER" ] && continue
  mkdir -p "$(dirname "$f")"
  if [ "$accion" = "mezcla" ]; then cat "$tmp/mezcla" > "$f"; mezclados=$((mezclados + 1))
  else cp "$tmp/rama" "$f"; copiados=$((copiados + 1)); fi
  [ "$modo" = "100755" ] && chmod +x "$f"
done < "$tmp/lista"

echo "Plan juntado: $copiados copiados, $mezclados mezclados, $iguales ya iguales, ${#choques[@]} choques${VER:+ (solo mirando)}."
if [ ${#choques[@]} -gt 0 ] && [ -z "$VER" ]; then
  { echo "# $(date '+%Y-%m-%d %H:%M') · ficheros donde el Mac y $RAMA cambian lo mismo (se quedó el del Mac)"
    printf '%s\n' "${choques[@]}"
    echo "# Para cada uno: git diff $BASE $RAMA -- <fichero>  y aplica a mano lo de la rama que falte (F1.3, paso 3c)."; } > "$CHOQUES"
  echo "  Lista en $CHOQUES (Cursor la resuelve en F1.3)."
fi
exit 0

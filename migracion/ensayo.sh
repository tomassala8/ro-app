#!/usr/bin/env bash
# migracion/ensayo.sh · el ensayo de 1 hora, en una COPIA de la app: no deja nada que estorbe a la noche de verdad.
#
#   bash migracion/ensayo.sh            # copia la app a ~/RO_ENSAYO/app y lanza 1 hora de noche ahí
#   RO_HORAS=2 bash migracion/ensayo.sh
#   bash migracion/ensayo.sh --borrar   # borra la copia, su Postgres y sus registros
#
# Por qué una copia: el ensayo hace commits en la rama migracion/v2, marca pasos en PROGRESO.md, graba la referencia
# (solo lectura) y huellas en ~/RO_MIGRACION. Si se hiciera en la app de verdad, la noche empezaría con todo eso a medias.
# En la copia: otra carpeta de trabajo (~/RO_ENSAYO/fuera), otro Postgres (proyecto de Docker «ro_ensayo») y sin push.
# Lo que hay que mirar al acabar: ~/RO_ENSAYO/app/migracion/PROGRESO.md, ~/RO_ENSAYO/fuera/logs/ y el gasto en
# Cursor › Settings › Usage (por 8 da la noche).
set -uo pipefail
ORIGEN="$(cd "$(dirname "$0")/.." && pwd)"
ENSAYO="${RO_ENSAYO:-$HOME/RO_ENSAYO}"
export COMPOSE_PROJECT_NAME=ro_ensayo

if [ "${1:-}" = "--borrar" ]; then
  [ -d "$ENSAYO/app" ] && (cd "$ENSAYO/app" && RO_MIGRACION="$ENSAYO/fuera" bash migracion/servicios.sh parar >/dev/null 2>&1; \
    cd v2 && docker compose down -v >/dev/null 2>&1)
  rm -rf "$ENSAYO"; echo "✔ Ensayo borrado."; exit 0
fi
[ -e "$ENSAYO" ] && { echo "✘ Ya hay un ensayo en $ENSAYO. Míralo y bórralo con: bash migracion/ensayo.sh --borrar"; exit 1; }

# servicios de la app de verdad parados: el ensayo usa los mismos puertos
(cd "$ORIGEN" && bash migracion/servicios.sh parar >/dev/null 2>&1) || true

mkdir -p "$ENSAYO/fuera"
echo "Copiando la app a $ENSAYO/app…"
# En el disco del Mac (APFS) «cp -c» clona sin ocupar espacio y tarda segundos.
cp -Rc "$ORIGEN" "$ENSAYO/app" 2>/dev/null || cp -a --reflink=auto "$ORIGEN" "$ENSAYO/app" || { echo "✘ No se pudo copiar"; exit 1; }
# lo que Tomás deja en ~/RO_MIGRACION para la noche (lista de feedback, referencias), sin lo que genera una noche
for f in PENDIENTES_LOGICA.md referencias; do
  [ -e "${RO_MIGRACION:-$HOME/RO_MIGRACION}/$f" ] && cp -Rc "${RO_MIGRACION:-$HOME/RO_MIGRACION}/$f" "$ENSAYO/fuera/" 2>/dev/null \
    || { [ -e "${RO_MIGRACION:-$HOME/RO_MIGRACION}/$f" ] && cp -a "${RO_MIGRACION:-$HOME/RO_MIGRACION}/$f" "$ENSAYO/fuera/"; }
done

cd "$ENSAYO/app" || exit 1
# sin push desde la copia: «git push» falla siempre aquí
git remote set-url --push origin "no-push://ensayo" 2>/dev/null
mkdir -p .git/hooks; printf '#!/bin/sh\necho "push desactivado en el ensayo" >&2\nexit 1\n' > .git/hooks/pre-push; chmod +x .git/hooks/pre-push

echo "Ensayo de ${RO_HORAS:-1} hora(s) en $ENSAYO/app (Postgres «ro_ensayo», carpeta de trabajo $ENSAYO/fuera)."
# RO_SIN_PLAN=1: el ensayo usa el PLAN_NOCHE.md que haya en ese momento (planear.sh puede seguir a la vez en la app de verdad)
RO_MIGRACION="$ENSAYO/fuera" RO_HORAS="${RO_HORAS:-1}" RO_NOCHE_NUEVA=1 RO_SIN_PLAN=1 bash migracion/noche.sh
codigo=$?

RO_MIGRACION="$ENSAYO/fuera" bash migracion/servicios.sh parar >/dev/null 2>&1
(cd v2 && docker compose stop >/dev/null 2>&1)
echo
echo "Ensayo terminado (código $codigo). Mira:"
echo "  · lo que hizo:      $ENSAYO/app/migracion/PROGRESO.md y NOTAS_NOCHE.md"
echo "  · cada vuelta:      $ENSAYO/fuera/logs/"
echo "  · lo que costó:     Cursor › Settings › Usage (por 8 da la noche)"
echo "  · la de verdad está intacta: $ORIGEN"
echo "Al acabar de mirarlo: bash migracion/ensayo.sh --borrar"

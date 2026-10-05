#!/usr/bin/env bash
# migracion/ensayo.sh · el ensayo de 1 hora, en una COPIA de la app: no deja nada que estorbe a la noche de verdad.
#
#   bash migracion/ensayo.sh               # copia la app a ~/RO_ENSAYO/app y lanza 1 hora de noche ahí
#   RO_HORAS=2 bash migracion/ensayo.sh
#   bash migracion/ensayo.sh --comprobar   # la comprobación de la mañana, sobre el ensayo
#   bash migracion/ensayo.sh --cerrar      # si el ensayo se cortó a lo bruto: deja ~/RO_MIGRACION y Postgres como estaban
#   bash migracion/ensayo.sh --borrar      # borra la copia, su Postgres y sus registros
#
# Por qué una copia: el ensayo hace commits en la rama migracion/v2, marca pasos en PROGRESO.md, graba la referencia
# (solo lectura) y huellas. Si se hiciera en la app de verdad, la noche empezaría con todo eso a medias.
# Aislado de verdad:
#  · la app: copia en ~/RO_ENSAYO/app (en el disco del Mac, «cp -c» clona sin ocupar espacio), sin push;
#  · ~/RO_MIGRACION: los pasos la nombran tal cual, así que mientras dura el ensayo ~/RO_MIGRACION APUNTA a
#    ~/RO_ENSAYO/fuera y la de verdad espera aparcada al lado (~/RO_MIGRACION.real_<hora>); al acabar, vuelve sola.
#    noche.sh y planear.sh se niegan a arrancar mientras tanto;
#  · Postgres: el de verdad se para (mismo puerto) y el ensayo usa el suyo (proyecto de Docker «ro_ensayo»).
# Lo que hay que mirar al acabar: ~/RO_ENSAYO/app/migracion/PROGRESO.md, ~/RO_ENSAYO/fuera/logs/ y el gasto en
# Cursor › Settings › Usage (por 8 da la noche).
set -uo pipefail
ORIGEN="$(cd "$(dirname "$0")/.." && pwd)"
ENSAYO="${RO_ENSAYO:-$HOME/RO_ENSAYO}"
REAL="${RO_MIGRACION:-$HOME/RO_MIGRACION}"
modo="${1:-}"

pg_real() { (cd "$ORIGEN/v2" && env -u COMPOSE_PROJECT_NAME docker compose "$@" postgres >/dev/null 2>&1); }
pg_ensayo() { (cd "$ENSAYO/app/v2" 2>/dev/null && COMPOSE_PROJECT_NAME=ro_ensayo docker compose "$@" >/dev/null 2>&1); }
aparcada() { ls -d "$REAL".real_* 2>/dev/null | head -1; }

cerrar() {   # ~/RO_MIGRACION y Postgres como estaban
  local a; a="$(aparcada)"
  # los servicios de la copia (8770, 8771, 4000, 3000…), parados: si no, la noche de verdad los reutilizaría
  [ -d "$ENSAYO/app" ] && (cd "$ENSAYO/app" && RO_MIGRACION="$ENSAYO/fuera" bash migracion/servicios.sh parar >/dev/null 2>&1)
  if [ -L "$REAL" ]; then rm -f "$REAL"; fi
  if [ -n "$a" ] && [ ! -e "$REAL" ]; then mv "$a" "$REAL" && echo "✔ $REAL vuelve a ser la de verdad."; fi
  pg_ensayo stop
  [ -n "${PG_ESTABA:-}" ] && pg_real start
  return 0
}

abrir() {   # ~/RO_MIGRACION → la del ensayo; Postgres de verdad parado
  if pgrep -f "migracion/(planear|noche)\.sh" >/dev/null 2>&1; then
    echo "✘ planear.sh o noche.sh están en marcha: el ensayo cambia ~/RO_MIGRACION y no puede ir a la vez. Espera a que acaben."; exit 1
  fi
  [ -n "$(aparcada)" ] || [ -L "$REAL" ] && { echo "✘ Hay un ensayo sin cerrar: bash migracion/ensayo.sh --cerrar"; exit 1; }
  if (cd "$ORIGEN/v2" && env -u COMPOSE_PROJECT_NAME docker compose ps --status running postgres 2>/dev/null | grep -q postgres); then
    PG_ESTABA=1; pg_real stop
  fi
  if lsof -nP -iTCP:5432 -sTCP:LISTEN >/dev/null 2>&1; then
    echo "✘ Algo sigue escuchando en 5432 (otro Postgres): el ensayo escribiría en él. Páralo y vuelve a lanzar."; cerrar; exit 1
  fi
  trap 'cerrar' EXIT
  trap 'echo; echo "Ensayo cortado."; exit 130' INT TERM
  mkdir -p "$ENSAYO/fuera"
  if [ -e "$REAL" ]; then mv "$REAL" "$REAL.real_$(date +%H%M%S)" || { echo "✘ No puedo apartar $REAL"; exit 1; }; fi
  ln -s "$ENSAYO/fuera" "$REAL"
  export RO_MIGRACION="$ENSAYO/fuera" COMPOSE_PROJECT_NAME=ro_ensayo
}

case "$modo" in
  --cerrar) cerrar; echo "✔ Ensayo cerrado."; exit 0 ;;
  --borrar)
    [ -L "$REAL" ] || [ -n "$(aparcada)" ] && cerrar
    [ -d "$ENSAYO/app" ] && (cd "$ENSAYO/app" && RO_MIGRACION="$ENSAYO/fuera" bash migracion/servicios.sh parar >/dev/null 2>&1)
    (cd "$ENSAYO/app/v2" 2>/dev/null && COMPOSE_PROJECT_NAME=ro_ensayo docker compose down -v >/dev/null 2>&1)
    chmod -R u+w "$ENSAYO" 2>/dev/null; rm -rf "$ENSAYO"
    if [ -e "$ENSAYO" ]; then echo "✘ No se pudo borrar todo $ENSAYO: bórralo a mano."; exit 1; fi
    echo "✔ Ensayo borrado."; exit 0 ;;
  --comprobar)
    [ -d "$ENSAYO/app" ] || { echo "✘ No hay ensayo en $ENSAYO"; exit 1; }
    abrir
    bash "$ENSAYO/fuera/comprobar_manana.sh"; codigo=$?
    (cd "$ENSAYO/app" && bash migracion/servicios.sh parar >/dev/null 2>&1)
    exit $codigo ;;
  "") ;;
  *) echo "uso: bash migracion/ensayo.sh [--comprobar|--cerrar|--borrar]"; exit 2 ;;
esac

[ -e "$ENSAYO" ] && { echo "✘ Ya hay un ensayo en $ENSAYO. Míralo y bórralo con: bash migracion/ensayo.sh --borrar"; exit 1; }
# servicios de la app de verdad parados: el ensayo usa los mismos puertos
(cd "$ORIGEN" && bash migracion/servicios.sh parar >/dev/null 2>&1) || true

echo "Copiando la app a $ENSAYO/app…"
mkdir -p "$ENSAYO"
cp -Rc "$ORIGEN" "$ENSAYO/app" 2>/dev/null || cp -a "$ORIGEN" "$ENSAYO/app" || { echo "✘ No se pudo copiar"; exit 1; }
# lo que Tomás deja en ~/RO_MIGRACION para la noche (lista de feedback, referencias), sin lo que genera una noche
mkdir -p "$ENSAYO/fuera"
for f in PENDIENTES_LOGICA.md referencias; do
  [ -e "$REAL/$f" ] && { cp -Rc "$REAL/$f" "$ENSAYO/fuera/" 2>/dev/null || cp -a "$REAL/$f" "$ENSAYO/fuera/"; }
done

cd "$ENSAYO/app" || exit 1
# sin push desde la copia: «git push» falla siempre aquí
git remote set-url --push origin "no-push://ensayo" 2>/dev/null
mkdir -p .git/hooks; printf '#!/bin/sh\necho "push desactivado en el ensayo" >&2\nexit 1\n' > .git/hooks/pre-push; chmod +x .git/hooks/pre-push

abrir
echo "Ensayo de ${RO_HORAS:-1} hora(s) en $ENSAYO/app (Postgres «ro_ensayo»; ~/RO_MIGRACION apunta al ensayo hasta que acabe)."
# RO_SIN_PLAN=1: el ensayo usa el PLAN_NOCHE.md que haya en ese momento
RO_HORAS="${RO_HORAS:-1}" RO_NOCHE_NUEVA=1 RO_SIN_PLAN=1 bash migracion/noche.sh
codigo=$?

bash migracion/servicios.sh parar >/dev/null 2>&1
cerrar; trap - EXIT
echo
echo "Ensayo terminado (código $codigo). Mira:"
echo "  · lo que hizo:      $ENSAYO/app/migracion/PROGRESO.md y NOTAS_NOCHE.md"
echo "  · cada vuelta:      $ENSAYO/fuera/logs/"
echo "  · lo que costó:     Cursor › Settings › Usage (por 8 da la noche)"
echo "  · si quieres, la comprobación de la mañana sobre el ensayo: bash migracion/ensayo.sh --comprobar"
echo "  · la de verdad está intacta: $ORIGEN y $REAL"
echo "Al acabar de mirarlo: bash migracion/ensayo.sh --borrar"

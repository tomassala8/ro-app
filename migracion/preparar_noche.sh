#!/usr/bin/env bash
# migracion/preparar_noche.sh · comprueba que el Mac está listo para la migración de esta noche, sin tocar nada de la app.
#
#   cd <carpeta de la app>          # la que tiene servir.py
#   # 1) traer el plan SIN cambiar de rama ni tocar lo que tienes sin commit:
#   git fetch origin claude/project-thread-rjes21
#   git checkout origin/claude/project-thread-rjes21 -- migracion v2 .cursor AGENTS.md
#   # 2) comprobar:
#   bash migracion/preparar_noche.sh            # solo mira y dice qué falta
#   bash migracion/preparar_noche.sh --instalar # además instala lo que se puede instalar solo (pnpm, dependencias, Chromium)
#   bash migracion/preparar_noche.sh --probar-cursor   # además hace una llamada mínima a Cursor con el modelo elegido
#
# Pásalo por la tarde: si algo sale en ✘, hay tiempo de arreglarlo antes de la noche. Al final, una línea: LISTO o NO LISTO.
set -uo pipefail
cd "$(dirname "$0")/.."
RAIZ="$(pwd)"
INSTALAR=0; PROBAR=0
for a in "$@"; do [ "$a" = "--instalar" ] && INSTALAR=1; [ "$a" = "--probar-cursor" ] && PROBAR=1; done
MODELO="${RO_MODELO:-grok-code-fast-1}"; MODELO_PLAN="${RO_MODELO_PLAN:-claude-fable-5-1}"; MODELO_FUERTE="${RO_MODELO_FUERTE:-claude-sonnet-5-5}"
FUERA="${RO_MIGRACION:-$HOME/RO_MIGRACION}"
fallos=0; avisos=0
ok()   { printf "  ✔ %s\n" "$1"; }
mal()  { printf "  ✘ %s\n     → %s\n" "$1" "$2"; fallos=$((fallos+1)); }
ojo()  { printf "  ⚠ %s\n     → %s\n" "$1" "$2"; avisos=$((avisos+1)); }
version_mayor() { "$1" --version 2>/dev/null | grep -oE '[0-9]+' | head -1; }

echo "1 · Repositorio"
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  ok "git en $(basename "$RAIZ") (rama $(git branch --show-current))"
  n=$(git status --porcelain | wc -l | tr -d ' ')
  [ "$n" = 0 ] && ok "sin cambios a medias" \
    || ok "$n ficheros con cambios sin commit (normal: el paso F1.3 los guarda en la rama migracion/v2 tras el escáner)"
  git fetch -q origin 2>/dev/null && ok "GitHub responde (git fetch)" || ojo "no se pudo hacer git fetch" "revisa la conexión o la llave SSH de GitHub"
  for f in migracion/PROMPT_NOCHE.md migracion/PROGRESO.md migracion/puerta.sh migracion/servicios.sh migracion/noche.sh v2/package.json despliegue/base.py; do
    [ -f "$f" ] || mal "falta $f" "trae el plan: git fetch origin claude/project-thread-rjes21 && git checkout origin/claude/project-thread-rjes21 -- migracion v2 .cursor AGENTS.md"
  done
  if git cat-file -e origin/claude/project-thread-rjes21:despliegue/base.py 2>/dev/null; then
    if ! git diff --quiet origin/claude/project-thread-rjes21 -- despliegue/base.py; then
      if git diff --quiet HEAD -- despliegue/base.py; then
        ok "despliegue/base.py aún sin los arreglos de Postgres del plan: noche.sh los trae al empezar (juntar_plan.sh)"
      else
        ojo "despliegue/base.py tiene cambios tuyos sin commit y no lleva los arreglos del plan" "noche.sh los junta a tres bandas (juntar_plan.sh); si chocan, Cursor lo resuelve en F1.3. Para verlo antes: bash migracion/juntar_plan.sh --ver"
      fi
    else ok "despliegue/base.py con los arreglos de Postgres"; fi
  fi
  # Lo que el plan cambia fuera de migracion/ y v2/ lo junta noche.sh al empezar: aquí solo se mira si chocaría
  if [ -f migracion/juntar_plan.sh ]; then
    vista="$(bash migracion/juntar_plan.sh --ver 2>&1)"
    n_choques=$(echo "$vista" | grep -c "✘")
    [ "$n_choques" -eq 0 ] && ok "el resto del plan (config.py, despliegue/…) se junta sin choques: $(echo "$vista" | tail -1)" \
      || ojo "$n_choques fichero(s) del plan chocan con cambios de Astra: $(echo "$vista" | grep "✘" | tr '\n' ' ')" "noche.sh deja el del Mac y Cursor los resuelve en F1.3; si es config.py, noche.sh no arranca hasta resolverlo"
  fi
  # Punto de partida = código del Mac + el trabajo del 4-oct que aún está en PR (migracion/RAMAS_A_JUNTAR.txt)
  if [ -f migracion/RAMAS_A_JUNTAR.txt ]; then
    while read -r rama _; do
      case "$rama" in ''|\#*) continue;; esac
      if ! git cat-file -e "origin/$rama" 2>/dev/null; then ojo "no veo la rama $rama en GitHub" "git fetch origin; si ya se juntó en main y se borró, quítala de migracion/RAMAS_A_JUNTAR.txt"
      elif git merge-base --is-ancestor "origin/$rama" HEAD; then ok "tu código ya lleva $rama"
      else ojo "tu código no lleva $rama" "Cursor la junta en F1.3 (si chocan, se queda tu versión y lo apunta). Si prefieres, júntala tú antes en main"; fi
    done < migracion/RAMAS_A_JUNTAR.txt
  fi
else
  mal "esta carpeta no es un repositorio git" "ejecuta el script desde la carpeta de la app (la que tiene servir.py)"
fi
case "$RAIZ" in *"/Desktop/"*|*"Mobile Documents"*) ojo "la app está en una carpeta de iCloud" "muévela a disco local: iCloud ralentiza mucho node_modules";; esac

echo "2 · Herramientas"
N=$(version_mayor node); [ -n "$N" ] && [ "$N" -ge 22 ] && ok "Node $(node --version)" || mal "Node 22 o superior" "brew install node@22  (o nvm install 22)"
if command -v pnpm >/dev/null; then ok "pnpm $(pnpm --version)"
elif [ $INSTALAR = 1 ] && corepack enable 2>/dev/null && corepack prepare pnpm@10.28.0 --activate >/dev/null 2>&1; then ok "pnpm instalado con corepack"
else mal "pnpm" "corepack enable && corepack prepare pnpm@10.28.0 --activate  (o: bash migracion/preparar_noche.sh --instalar)"; fi
P=$(python3 -c 'import sys;print(sys.version_info[1])' 2>/dev/null); [ -n "$P" ] && [ "$P" -ge 11 ] && ok "Python 3.$P" || mal "Python 3.11 o superior" "brew install python@3.12"
python3 -c "import psycopg" 2>/dev/null && ok "psycopg (Python ↔ Postgres)" || {
  [ $INSTALAR = 1 ] && python3 -m pip install -q "psycopg[binary]" && ok "psycopg instalado" || mal "falta psycopg" "python3 -m pip install 'psycopg[binary]'"; }
if docker info >/dev/null 2>&1; then ok "Docker en marcha"
else mal "Docker no responde" "abre Docker Desktop (u OrbStack) y espera a que diga «running»"; fi
command -v psql >/dev/null && ok "psql $(psql --version | grep -oE '[0-9]+\.[0-9]+' | head -1)" || ojo "falta psql" "brew install libpq && brew link --force libpq  (lo usa v2/packages/db/scripts/rehacer_base.sh)"
command -v pg_dump >/dev/null && command -v pg_restore >/dev/null && ok "pg_dump y pg_restore" || ojo "faltan pg_dump/pg_restore" "brew install libpq && brew link --force libpq  (los usa el ensayo de restauración, F7.3)"
if command -v cursor-agent >/dev/null; then
  ayuda="$(cursor-agent --help 2>&1)"
  if echo "$ayuda" | grep -q -- "--model" && echo "$ayuda" | grep -q -- "--force" && echo "$ayuda" | grep -qE -- "-p|--print"; then
    ok "cursor-agent con -p, --force y --model (lo usa noche.sh)"
  else
    ojo "cursor-agent no anuncia -p / --force / --model" "mira «cursor-agent --help» y lánzalo con RO_AGENTE=\"cursor-agent <opciones> {MODELO}\" bash migracion/noche.sh"
  fi
  if [ $PROBAR = 1 ]; then
    pares="RO_MODELO:$MODELO RO_MODELO_PLAN:$MODELO_PLAN"; [ -n "${RO_PASOS_FUERTES-F4.1 F4.2 F5.1 F5.10}" ] && pares="$pares RO_MODELO_FUERTE:$MODELO_FUERTE"
    for par in $pares; do
      var="${par%%:*}"; m="${par#*:}"
      r="$(cursor-agent -p --force --output-format text --model "$m" "Responde solo: OK" 2>&1 < /dev/null | tail -3)"
      echo "$r" | grep -q "OK" && ok "Cursor responde con el modelo $m ($var)" \
        || mal "Cursor no responde con el modelo $m: $r" "elige el nombre exacto y pásalo: $var=<nombre>. Nombres que conoce tu Cursor: $( (cursor-agent models 2>/dev/null || cursor-agent --list-models 2>/dev/null) | grep -ioE '[a-z0-9.-]*(grok|fable|sonnet)[a-z0-9.-]*' | sort -u | tr '\n' ' ')"
    done
    echo "$ayuda" | grep -q -- "--mode" && ok "cursor-agent tiene --mode: si admite «plan», RO_AGENTE_PLAN=\"cursor-agent -p --mode plan --output-format text --model {MODELO}\" deja al planificador en solo lectura"
  fi
else
  ojo "no encuentro la orden «cursor-agent»" "para 8 horas sin nadie hace falta: curl https://cursor.com/install -fsS | bash && cursor-agent login. Sin ella, se lanza desde la ventana de Cursor (PLAN_MAESTRO §6)"
fi

echo "3 · Red (lo que se descarga esta noche)"
for h in registry.npmjs.org ui.shadcn.com github.com binaries.prisma.sh; do
  curl -sS -o /dev/null -m 8 "https://$h" 2>/dev/null && ok "$h" || mal "no llego a $h" "revisa la conexión, VPN o cortafuegos"
done

echo "4 · Datos y app de hoy"
[ -d data ] && ok "data/ ($(find data -name '*.json' | wc -l | tr -d ' ') ficheros)" || mal "no hay data/" "python3 build_data.py (o la tubería): sin datos no se puede grabar la referencia"
[ -f local.db ] && ok "local.db ($(du -h local.db | cut -f1))" || mal "no hay local.db" "arranca una vez servir.py: la crea"
if curl -s -m 3 http://127.0.0.1:8770/api/elegir >/dev/null 2>&1; then ojo "algo responde ya en 127.0.0.1:8770" "para tu servir.py antes de lanzar la noche: servicios.sh arranca ahí la referencia sobre una COPIA de la base"
else ok "8770 libre (servicios.sh arranca ahí la referencia esta noche)"; fi
for puerto in 3000 4000 5432 8771 8780 8781 4001; do
  if lsof -nP -iTCP:$puerto -sTCP:LISTEN >/dev/null 2>&1; then
    quien=$(lsof -nP -iTCP:$puerto -sTCP:LISTEN | awk 'NR==2{print $1}')
    [ "$puerto" = 5432 ] && [ "$quien" != "postgres" ] && [ "$quien" != "com.docke" ] && [ "$quien" != "docker" ] \
      && ojo "el puerto 5432 lo usa «$quien»" "si es otro Postgres, páralo o cambia el puerto en v2/docker-compose.yml" \
      || { [ "$puerto" != 5432 ] && ojo "el puerto $puerto está ocupado por «$quien»" "ciérralo antes de empezar"; }
  else ok "puerto $puerto libre"; fi
done

echo "5 · Espacio y carpeta de trabajo fuera del repo"
LIBRE=$(df -g "$RAIZ" 2>/dev/null | awk 'NR==2{print $4}'); [ -z "$LIBRE" ] && LIBRE=$(df -BG "$RAIZ" | awk 'NR==2{gsub("G","",$4);print $4}')
[ "${LIBRE:-0}" -ge 10 ] && ok "${LIBRE} GB libres" || mal "poco disco (${LIBRE:-?} GB)" "deja al menos 10 GB libres (node_modules, Docker, fotos)"
mkdir -p "$FUERA" && ok "carpeta para datos de la migración: $FUERA (fuera del repo)"
mkdir -p "$FUERA/referencias"
[ -n "$(ls -A "$FUERA/referencias" 2>/dev/null)" ] && ok "referencias de backend en $FUERA/referencias" \
  || ojo "la carpeta de referencias está vacía" "deja ahí el zip del otro CRM (PLAN_MAESTRO §2.11); no es imprescindible"

LISTA="$FUERA/PENDIENTES_LOGICA.md"; [ -f "$LISTA" ] || LISTA="migracion/PENDIENTES_LOGICA.md"
ABIERTOS=$(cat migracion/PENDIENTES_LOGICA.md "$FUERA/PENDIENTES_LOGICA.md" 2>/dev/null | grep -E '^\| [LN]-[0-9]+ .*\| *abierto' | cut -d'|' -f2 | sort -u | grep -c .); ABIERTOS=${ABIERTOS:-0}
if [ "$ABIERTOS" -gt 0 ]; then ok "$ABIERTOS fallos de lógica abiertos para arreglar en la noche ($LISTA)"
else ojo "la lista de fallos de lógica está vacía ($LISTA)" "si hay fallos sin arreglar en la app de hoy, apúntalos ahí antes de lanzar (o pide a Claude que la copie del hilo de feedback)"; fi

echo "6 · El plan de la noche (Fable lo escribe y lo audita: migracion/planear.sh)"
if [ -f migracion/PLAN_NOCHE.md ]; then
  primera="$(head -1 migracion/PLAN_NOCHE.md)"
  case "$primera" in
    "PLAN: AUDITADO"*) python3 migracion/revisar_plan.py >/dev/null && ok "$primera" || mal "el plan auditado no pasa revisar_plan.py" "bash migracion/planear.sh (lo completa)";;
    *) ojo "plan sin terminar: $primera" "bash migracion/planear.sh (sigue donde lo dejó; si no, noche.sh lo hace antes de empezar y la noche empieza más tarde)";;
  esac
else ojo "aún no hay plan de la noche" "lánzalo en cuanto Astra deje de tocar el código: bash migracion/planear.sh (varias horas; noche.sh lo haría antes de empezar)"; fi

echo "7 · Proyecto nuevo (v2)"
if [ -d v2 ] && command -v pnpm >/dev/null; then
  if [ $INSTALAR = 1 ]; then (cd v2 && pnpm install --frozen-lockfile >/dev/null 2>&1) && ok "dependencias instaladas" || mal "pnpm install falló" "cd v2 && pnpm install  y mira el error"; fi
  if [ -d v2/node_modules ]; then
    (cd v2 && pnpm build >/dev/null 2>&1) && ok "v2 compila (web, api, db, permisos)" || mal "v2 no compila" "cd v2 && pnpm build  y mira el error"
    if [ -x v2/tools/capturas/node_modules/.bin/playwright ]; then
      (cd v2/tools/capturas && ./node_modules/.bin/playwright install --dry-run chromium 2>/dev/null | grep -q "already\|Install location" ) && ok "Playwright listo" || {
        [ $INSTALAR = 1 ] && (cd v2/tools/capturas && ./node_modules/.bin/playwright install chromium >/dev/null 2>&1) && ok "Chromium de Playwright instalado" \
          || ojo "Chromium de Playwright" "cd v2/tools/capturas && pnpm exec playwright install chromium"; }
    fi
  else ojo "v2 sin dependencias" "bash migracion/preparar_noche.sh --instalar"; fi
  if docker info >/dev/null 2>&1; then
    (cd v2 && docker compose up -d postgres >/dev/null 2>&1) && sleep 3 && (cd v2 && docker compose exec -T postgres pg_isready -U ro -d ro_app >/dev/null 2>&1) \
      && ok "Postgres de v2 arriba (127.0.0.1:5432, base ro_app)" || mal "no arranca el Postgres de v2" "cd v2 && docker compose up postgres  y mira el error"
  fi
else mal "no está la carpeta v2/" "trae el plan (ver la cabecera de este script)"; fi

echo
if [ $fallos = 0 ]; then echo "LISTO para la noche ($avisos avisos que conviene mirar). Para lanzarla: bash migracion/noche.sh"; else echo "NO LISTO: $fallos cosas que arreglar y $avisos avisos."; fi
exit $fallos

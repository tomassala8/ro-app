#!/bin/sh
# despliegue/preparar_contexto.sh · arma la carpeta que se sube al repositorio privado (y desde la que se construye
# la imagen): SOLO código, nunca datos ni llaves. Carril C5.
#
#   ro-app/
#   ├── app/          = 30_APP_PROTOTIPO sin data/, local.db, historia/, capturas/, cachés ni _privado/
#   ├── herramientas/ = los lectores de ~/RO_HERRAMIENTAS que usa la tubería (solo .py y .json de configuración sin llaves)
#   ├── Dockerfile    (copia de despliegue/Dockerfile)
#   └── render.yaml   (copia de despliegue/render.yaml: Render lo busca en la raíz del repositorio)
#
# Los datos viajan por la base (despliegue/publicacion.py: «crudos», «cache» y «data»), nunca por el repositorio.
# Uso: sh despliegue/preparar_contexto.sh [destino]   (por defecto despliegue/estado/ro-app)
set -eu
AQUI=$(cd "$(dirname "$0")" && pwd)
APP=$(dirname "$AQUI")
HERR="${RO_HERRAMIENTAS:-$HOME/RO_HERRAMIENTAS}"
DEST="${1:-$AQUI/estado/ro-app}"
rm -rf "$DEST"; mkdir -p "$DEST/app" "$DEST/herramientas"
rsync -a \
  --exclude 'data/' --exclude 'local.db*' --exclude 'historia/' --exclude 'capturas/' --exclude '_cache/' --exclude '_crudo/' \
  --exclude '_privado/' --exclude 'despliegue/estado/' --exclude '__pycache__/' --exclude '*.pyc' --exclude '.DS_Store' \
  --exclude 'indicadores.json' --exclude 'fuentes_incidencias/primera_vez.json' --exclude 'fuentes_captacion/anuncios.json' \
  "$APP/" "$DEST/app/"
for d in captacion clickup_api ghl_agencia google holded meta metricool seranking snov windsor zadarma zoho zoom; do
  mkdir -p "$DEST/herramientas/$d"
  rsync -a --include '*.py' --exclude '*' "$HERR/$d/" "$DEST/herramientas/$d/"
done
cp "$HERR/externos.py" "$DEST/herramientas/"
# estado sin llaves que leen la pantalla de conexiones (caducidad de Meta, compañía de GHL)
cp "$HERR/meta/estado.json" "$DEST/herramientas/meta/" 2>/dev/null || true
cp "$HERR/ghl_agencia/app_estado.json" "$DEST/herramientas/ghl_agencia/" 2>/dev/null || true
cp "$AQUI/Dockerfile" "$DEST/Dockerfile"
cp "$AQUI/render.yaml" "$DEST/render.yaml"
cp "$AQUI/docker-compose.yml" "$DEST/docker-compose.yml"   # solo para la alternativa en servidor propio
printf '%s\n' "data/" "local.db" "*.env" "historia/" "capturas/" "_cache/" "_crudo/" "_privado/" "despliegue/estado/" "__pycache__/" > "$DEST/.gitignore"
# Puerta de secretos sobre el código: si aparece una llave, se para aquí.
if grep -rIlE "(sk-[A-Za-z0-9_-]{16,}|pit-[0-9a-f]{8}-[0-9a-f-]{20,}|EAA[A-Za-z0-9]{40,}|AKIA[0-9A-Z]{16}|eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.)" "$DEST" ; then
  echo "⛔ Hay algo con forma de llave en el código (arriba). No se sube nada hasta quitarlo."; exit 1
fi
# Puerta de datos personales (escáner de E0 sobre cada .json que iría al repositorio): si algo da hallazgos, no se sube.
if ! python3 - "$DEST/app" "$APP" <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[2])
import escaner_secretos as E
malos = [str(f.relative_to(sys.argv[1])) for f in Path(sys.argv[1]).rglob("*.json") if E.escanear_fichero(f)]
for m in malos: print("  ✗", m)
sys.exit(1 if malos else 0)
PY
then echo "⛔ Hay ficheros con correos o teléfonos de fuera de RO (arriba): sacarlos del código o pasarlos a la base. No se sube nada."; exit 1; fi
echo "Contexto listo en $DEST ($(du -sh "$DEST" | cut -f1)). Sin datos ni llaves."

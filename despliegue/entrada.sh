#!/bin/sh
# despliegue/entrada.sh · punto de entrada del contenedor (Render, Docker en Hetzner o Cloud Run). Carril C5.
#   web       servir.py en modo servidor (solo con sello de Cloudflare Access)
#   ligera    tubería ligera (cada hora 7-23 h)        · si ya hay otra vuelta en marcha, sale bien (código 75 → 0)
#   completa  tubería completa (6:00 y 14:00)
#   noche     copia de la base + batería nocturna + página de emergencia
#   <otra>    se ejecuta tal cual (p. ej. «python3 despliegue/llave_ghl.py estado»)
set -u
umask 077
PILOTO=$(python3 -c 'import piloto_lectura; print("si" if piloto_lectura.activo() else "no")') || exit 1
if [ "$PILOTO" = "si" ] && [ "${1:-web}" != "web" ]; then
  echo "Piloto de consulta: las tareas de actualización y los comandos alternativos están desactivados." >&2
  exit 1
fi
# Ficheros .env que algunos lectores leen del disco: se escriben desde las variables y solo viven en este contenedor.
if [ "$PILOTO" != "si" ]; then
mkdir -p "$HOME/RO_BANDEJA_GHL/config"
[ -n "${GHL_PIT_NEW:-}" ] && printf 'GHL_PIT_NEW=%s\n' "$GHL_PIT_NEW" > "$HOME/RO_BANDEJA_GHL/config/ghl.env"
[ -n "${ZADARMA_KEY:-}" ] && printf 'ZADARMA_KEY=%s\nZADARMA_SECRET=%s\n' "$ZADARMA_KEY" "${ZADARMA_SECRET:-}" > "$HOME/RO_BANDEJA_GHL/config/zadarma.env"
fi
umask 022

tuberia() {
  python3 despliegue/tuberia.py "$@"
  c=$?
  [ "$c" -eq 75 ] && { echo "Ya había otra vuelta en marcha: esta no se lanza (no es un fallo)."; exit 0; }
  exit "$c"
}

case "${1:-web}" in
  web)      # data/ llega de la base ANTES de arrancar (servir.py lo carga al importarse); luego se refresca solo cada minuto
            if [ "$PILOTO" != "si" ] && [ -n "${DATABASE_URL:-}" ]; then
              python3 despliegue/publicacion.py bajar data || exit $?
            fi
            exec python3 servir.py ;;
  ligera)   tuberia --ligero ;;
  completa) tuberia --completo ;;
  noche)    python3 despliegue/copia_base.py; c1=$?
            python3 despliegue/pruebas_noche.py; c2=$?
            [ "$(date +%d)" = "01" ] && python3 despliegue/copia_base.py --probar
            exit $(( c1 > c2 ? c1 : c2 )) ;;
  *)        exec "$@" ;;
esac

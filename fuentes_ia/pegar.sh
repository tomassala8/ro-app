#!/bin/bash
# fuentes_ia/pegar.sh · pega las DOS claves de la IA en el llavero del Mac (3-oct-2026). Lo hace Tomás, una vez.
#
#   bash fuentes_ia/pegar.sh
#
# 1. Pide la clave PRINCIPAL (espacio de trabajo «App RO» de la Console) y la de RESPALDO (espacio «App RO respaldo»).
#    Se escriben sin que se vean en pantalla y no se guardan en ningún fichero ni en el historial.
# 2. Comprueba cada una contra Anthropic con la lista de modelos (GET /v1/models: no gasta nada).
# 3. Las guarda en el llavero como «anthropic_api_key» y «anthropic_api_key_respaldo», que es donde las busca la app
#    (ia.py e ia_gasto.py). En el servidor (Render) van como ANTHROPIC_API_KEY y ANTHROPIC_API_KEY_RESPALDO.
# Nunca imprime una clave. Para cambiar una, vuelve a ejecutarlo (sustituye la anterior).
set -u

comprobar() {   # $1 = clave → 0 si Anthropic la acepta
  local codigo
  codigo=$(curl -s -o /dev/null -w "%{http_code}" https://api.anthropic.com/v1/models \
    -H "x-api-key: $1" -H "anthropic-version: 2023-06-01" --max-time 20 || echo "000")
  [ "$codigo" = "200" ] && return 0
  echo "   Anthropic responde $codigo (401 = clave no válida; 000 = sin conexión)."
  return 1
}

pegar() {   # $1 = nombre en el llavero · $2 = texto para Tomás · $3 = obligatoria (si/no)
  local clave=""
  echo ""
  echo "$2"
  read -r -s -p "   Pega la clave y pulsa Intro (no se verá; Intro vacío = saltar): " clave
  echo ""
  if [ -z "$clave" ]; then
    [ "$3" = "si" ] && echo "   Sin clave principal la IA sigue apagada (modo reglas, sin coste)." || echo "   Sin respaldo: si Anthropic falla, la app pasa a reglas."
    return 0
  fi
  case "$clave" in
    sk-ant-*) ;;
    *) echo "   Eso no parece una clave de la Console (empiezan por «sk-ant-»). No se guarda."; return 1 ;;
  esac
  if ! comprobar "$clave"; then
    echo "   No se guarda."; return 1
  fi
  security add-generic-password -U -a ro -s "$1" -w "$clave" >/dev/null 2>&1 \
    && echo "   Guardada en el llavero como «$1». Comprobada: Anthropic la acepta." \
    || { echo "   No se ha podido guardar en el llavero."; return 1; }
  clave=""
}

echo "Claves de la IA de la app de RO"
echo "Antes: en platform.claude.com, Settings › Workspaces, dos espacios («App RO» y «App RO respaldo»),"
echo "cada uno con su límite de gasto en dólares (170 $ y 20 $), y una clave en cada uno. Ver ../52_IA_COSTE_Y_TOPES.md."
pegar "anthropic_api_key" "1/2 · Clave PRINCIPAL (espacio «App RO»)" si
pegar "anthropic_api_key_respaldo" "2/2 · Clave de RESPALDO (espacio «App RO respaldo»)" no
echo ""
echo "Hecho. Reinicia el servidor de la app y mira Sistema › Gasto de IA: «Llaves» debe decir Principal y Respaldo lista."
echo "Falta, si no lo tienes: pip3 install anthropic   (el paquete oficial de Anthropic para Python)."

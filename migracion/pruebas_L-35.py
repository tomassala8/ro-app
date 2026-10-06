#!/usr/bin/env python3
"""migracion/pruebas_L-35.py · L-35: «Deshacer» al marcar una alerta y en lote.

Uso: python3 migracion/pruebas_L-35.py [--puerto 8781]
Arranca su propio servidor en 8781 sobre `ro_esc` (base limpia; escribe ahí, nunca `local.db` ni `data/`), lanza
`pruebas_L-35.mjs` (navegador) y lo para. Sale 0 si pasa. Sin datos reales en la salida.
"""
import http.client
import os
import pathlib
import subprocess
import sys
import time

RAIZ = pathlib.Path(__file__).resolve().parents[1]
FUERA = pathlib.Path.home() / "RO_MIGRACION"
TMP = FUERA / "tmp"
LOG = FUERA / "logs" / "esc_l35.log"
LOCAL = "127.0.0.1"


def listo():
    try:
        c = http.client.HTTPConnection(LOCAL, 8781, timeout=5)
        c.request("GET", "/api/elegir", headers={"X-RO-App": "1", "X-RO-Yo": "tomas"})
        return c.getresponse().status == 200
    except OSError:
        return False


def soltar():
    subprocess.run(["bash", "-lc", "kill $(lsof -t -iTCP@127.0.0.1:8781 -sTCP:LISTEN) 2>/dev/null; sleep 1"], check=False)


limpia = subprocess.run([sys.executable, "migracion/contrato_escritura.py", "base-limpia", "ro_esc"], cwd=RAIZ, check=False)
if limpia.returncode:
    print(f"✘ L-35: base-limpia ro_esc rc={limpia.returncode}")
    sys.exit(1)
TMP.mkdir(parents=True, exist_ok=True)
LOG.parent.mkdir(parents=True, exist_ok=True)
(TMP / "recarga_esc.json").write_text('{"ligera": []}\n', encoding="utf-8")
(TMP / "correos_entrada_esc.json").write_text("{}\n", encoding="utf-8")
(TMP / "lista_access_esc.txt").write_text("", encoding="utf-8")
entorno = os.environ.copy()
entorno.update({"DATABASE_URL": "postgresql://ro:ro@" + LOCAL + ":5432/ro_esc", "RO_RELOJ": "2026-10-05T07:30", "RO_SIN_LLAVES": "1",
                "RO_AVISOS_SIN_BUCLE": "1", "RO_ORIGEN_APP": "http://127.0.0.1:3000", "RO_RECARGA_CONFIG": str(TMP / "recarga_esc.json"),
                "RO_CORREOS_ENTRADA": str(TMP / "correos_entrada_esc.json"), "RO_LISTA_ACCESS": str(TMP / "lista_access_esc.txt")})
soltar()
proc = subprocess.Popen([sys.executable, "servir.py", "--bind", LOCAL, "--puerto", "8781"], cwd=RAIZ, env=entorno,
                        stdout=open(LOG, "ab"), stderr=subprocess.STDOUT, start_new_session=True)
rc = 1
try:
    limite = time.time() + 60
    while time.time() < limite and not listo():
        time.sleep(0.4)
    if not listo():
        print("✘ L-35: 8781 no arranca")
    else:
        rc = subprocess.run(["node", "migracion/pruebas_L-35.mjs", "--base", f"http://{LOCAL}:8781"], cwd=RAIZ, check=False).returncode
finally:
    proc.terminate()
    soltar()
sys.exit(rc)

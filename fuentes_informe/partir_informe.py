#!/usr/bin/env python3
"""
partir_informe.py · N10 «carga rápida» (auditoría 37, causa 5): el informe de un periodo, partido.

data/informe/p_<periodo>.json trae los 68 clientes (1,3-2 MB; 378 KB comprimidos en 4G lenta). Para abrir el informe
de UN cliente basta con:
  · data/informe/i_<periodo>.json          índice ligero: por cliente, qué fuentes traen dato (para elegir el cliente
                                            que se abre por defecto: el de su cartera con más fuentes).
  · data/informe/c_<periodo>/<cliente>.json la fila de ese cliente, tal cual está en p_<periodo>, dentro de «filas»
                                            (así servir.py la recorta igual: cartera, dinero, enlaces).
p_<periodo>.json se queda (lo usa la comparación con Looker y es el respaldo si falta una pieza).
Al partir se quitan de las consultas de Search Console las filas de exportación de Google Ads (comun.consulta_basura).

Lee data/informe/p_*.json; escribe i_*.json y c_*/ (y reescribe un p_*.json solo si le quitó consultas basura). Lo llama generar_informe.py al terminar; también
se puede lanzar suelto: python3 fuentes_informe/partir_informe.py
"""
import json
import os
import re
import sys
import tempfile
from pathlib import Path

AQUI = Path(__file__).resolve().parent.parent
SALIDA = AQUI / "data" / "informe"
sys.path.insert(0, str(AQUI / "fuentes"))
import comun as C  # noqa: E402  (consulta_basura / limpiar_consultas, N14)
FUENTES = ["ga4", "gsc", "meta", "seranking", "snov", "google_ads", "embudo"]   # las que cuenta informe.js para elegir cliente


def _escribir(ruta, obj):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=ruta.parent, prefix=".tmp_", suffix=".json")
    with os.fdopen(fd, "w") as f:
        json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))
    os.chmod(tmp, 0o644)
    os.replace(tmp, ruta)


def limpiar_basura(doc):
    """N14: las «consultas» de Search Console que son filas de una exportación de Google Ads (Octoedro trae 46) no
    son búsquedas: fuera, en el periodo entero y en cada cliente. Devuelve cuántas quitó."""
    quitadas = 0
    for f in doc.get("filas", []):
        g = f.get("gsc") if isinstance(f, dict) else None
        if isinstance(g, dict) and isinstance(g.get("consultas"), list):
            antes = len(g["consultas"])
            g["consultas"] = C.limpiar_consultas(g["consultas"])
            quitadas += antes - len(g["consultas"])
    return quitadas


def partir(fichero):
    pid = fichero.stem[2:]
    doc = json.loads(fichero.read_text())
    if limpiar_basura(doc):                      # p_<periodo> también, para que la comparación con Looker diga lo mismo
        _escribir(fichero, doc)
    meta = {**doc.get("_meta", {}), "partido_de": fichero.name}
    filas = [f for f in doc.get("filas", []) if isinstance(f, dict) and re.fullmatch(r"[\w\-]+", str(f.get("cliente_id") or ""))]
    _escribir(SALIDA / f"i_{pid}.json", {"_meta": {**meta, "nota": "Índice ligero: qué fuentes traen dato por cliente. La fila entera, en c_<periodo>/<cliente>.json."},
                                         "filas": [{"cliente_id": f["cliente_id"], "con": [k for k in FUENTES if f.get(k)]} for f in filas]})
    carpeta = SALIDA / f"c_{pid}"
    vigentes = set()
    for f in filas:
        ruta = carpeta / f"{f['cliente_id']}.json"
        _escribir(ruta, {"_meta": meta, "filas": [f]})
        vigentes.add(ruta.name)
    for viejo in carpeta.glob("*.json"):          # clientes que ya no están en el periodo
        if viejo.name not in vigentes:
            viejo.unlink()
    return pid, len(filas)


def main():
    hechos = [partir(f) for f in sorted(SALIDA.glob("p_*.json"))]
    print("informe partido: " + ", ".join(f"{p} ({n} clientes)" for p, n in hechos))


if __name__ == "__main__":
    sys.exit(main())

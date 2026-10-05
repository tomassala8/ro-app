#!/usr/bin/env python3
"""despliegue/pruebas_solidez_N-02.py · N-02: GSC. Un error de la API = la última lectura buena marcada «viejo», nunca ceros.

Uso:  python3 despliegue/pruebas_solidez_N-02.py
Sin red ni llaves: `gg` y `urllib.request.urlopen` son dobles; la base es un SQLite temporal (RO_DB) que se borra;
`gsc.json` real NO se toca (se sustituye `guardar`). `generar_seo` se importa, no se ejecuta.
(1) 1.ª lectura buena → clics > 0, estado ok, 1 fila ok=1.
(2) 2.ª lectura con HTTP 403 → los clics de la 1.ª con `_viejo` y `_desde`; no hay clics 0; filas: ok=1 y ok=0 con código 403.
(3) Cliente nuevo cuya 1.ª llamada da 403 → «sin_dato» (`estado`, `_error`), sin clics ni ceros.
(4) La API contesta, pero todo a 0 tras un mes con clics → se queda la última buena (`_viejo`).
(5) Estática: `q()` ya no devuelve `{'_error': …}` y `tot()` no pone `0` por defecto.
Sale 0 si pasa; si no, 1.
"""
import io
import json
import os
import re
import sys
import tempfile
import urllib.error
import urllib.request
import types
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
os.environ.pop("DATABASE_URL", None)
tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
tmp.close()
os.environ["RO_DB"] = tmp.name
os.environ["RO_SIN_LLAVES"] = "1"
sys.path.insert(0, str(RAIZ))
fallos = []


def ok(txt):
    print(f"  ✔ {txt}")


def mal(txt):
    print(f"  ✘ {txt}")
    fallos.append(txt)


try:
    # gg falso: nunca se toca el llavero ni la red
    gg = types.ModuleType("gg")
    gg.acceso = lambda: "token-falso"
    sys.modules["gg"] = gg
    from fuentes_seo import generar_seo as S

    guardados = []
    S.guardar = lambda ruta, obj: guardados.append((ruta, obj))   # no pisar fuentes_seo/_cache/gsc.json

    modo = {"v": "bien", "clics": 50}

    class Resp(io.BytesIO):
        status = 200

    def urlopen_falso(req, timeout=None):
        if modo["v"] == "403":
            raise urllib.error.HTTPError(req.full_url, 403, "Forbidden", {}, io.BytesIO(b"{}"))
        cuerpo = json.loads(req.data.decode())
        dims = cuerpo.get("dimensions")
        c = modo["clics"]
        if not dims:
            filas = [{"clicks": c, "impressions": c * 20, "ctr": 0.05, "position": 7.2}] if c else []
            if modo["v"] == "ceros":
                filas = [{"clicks": 0, "impressions": 0, "ctr": 0, "position": 0}]
        elif dims == ["date"]:
            filas = [{"keys": [str(S.HOY - S.dt.timedelta(days=3))], "clicks": c, "impressions": c * 20}]
        else:
            filas = [{"keys": [f"/{dims[0]}-1"], "clicks": c, "impressions": c * 20, "position": 5.0}]
            if modo["v"] == "ceros":
                filas = []
        return Resp(json.dumps({"rows": filas}).encode())

    real = urllib.request.urlopen
    urllib.request.urlopen = urlopen_falso

    def cliente(i):
        return {"id": i, "fuentes": {"gsc": {"emparejado": {"id": "sc-domain:ejemplo.test"}}}}

    def filas_bd(cid):
        from fuentes import lectura as L
        con = L.conectar()
        try:
            return [dict(r) for r in con.execute("SELECT ok, codigo FROM fuente_lectura WHERE fuente='gsc' AND recurso=? ORDER BY id", (cid,))]
        finally:
            con.close()

    try:
        # (1)
        a = S.leer_gsc([cliente("cli_falso")])["clientes"]["cli_falso"]
        if a.get("mes", {}).get("clics") == 50 and not a.get("_viejo"):
            ok("1.ª lectura buena: clics 50, sin marca de viejo")
        else:
            mal(f"1.ª lectura: {str(a)[:160]}")
        # (2)
        modo["v"] = "403"
        b = S.leer_gsc([cliente("cli_falso")])["clientes"]["cli_falso"]
        if b.get("_viejo") is True and b.get("_desde") and b["mes"]["clics"] == 50 and b["semana"]["clics"] == 50:
            ok("403: vuelve la última buena con _viejo y _desde (clics 50)")
        else:
            mal(f"403: {str(b)[:200]}")
        ultimo = guardados[-1][1]["clientes"]["cli_falso"]
        if ultimo["mes"]["clics"] != 0 and ultimo.get("mes", {}).get("clics") == 50:
            ok("lo que se escribe en gsc.json no lleva clics 0")
        else:
            mal("gsc.json recibiría clics 0")
        f = filas_bd("cli_falso")
        if [x["ok"] for x in f] == [1, 0] and str(f[1]["codigo"]) == "403":
            ok("fuente_lectura: una fila ok=1 y otra ok=0 con código 403")
        else:
            mal(f"fuente_lectura: {f}")
        # (3)
        c = S.leer_gsc([cliente("cli_nuevo")])["clientes"]["cli_nuevo"]
        if c.get("estado") == "sin_dato" and c.get("_error") and "mes" not in c and "clics" not in json.dumps(c):
            ok("cliente nuevo con 403: sin_dato, sin clics ni ceros")
        else:
            mal(f"cliente nuevo: {str(c)[:200]}")
        # (4)
        modo["v"] = "ceros"
        d = S.leer_gsc([cliente("cli_falso")])["clientes"]["cli_falso"]
        if d.get("_viejo") is True and d["mes"]["clics"] == 50:
            ok("todo a 0 tras un mes con clics: se queda la última buena")
        else:
            mal(f"todo a 0: {str(d)[:200]}")
    finally:
        urllib.request.urlopen = real

    # (5) estática
    t = (RAIZ / "fuentes_seo" / "generar_seo.py").read_text(encoding="utf-8")
    if "return {'_error': e.code}" in t:
        mal("q() sigue devolviendo {'_error': …} en vez de lanzar")
    elif re.search(r"x\.get\('(clicks|impressions|ctr)',\s*0\)", t):
        mal("tot() sigue poniendo 0 por defecto")
    else:
        ok("q() lanza y tot() no inventa ceros")
finally:
    Path(tmp.name).unlink(missing_ok=True)

if fallos:
    print(f"\n✘ N-02: {len(fallos)} fallo(s)")
    sys.exit(1)
print("\n✔ N-02")

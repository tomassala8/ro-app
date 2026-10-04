#!/usr/bin/env python3
"""
migracion/contrato_escritura.py · lo mismo que contrato.py, pero para lo que ESCRIBE (POST).

contrato.py solo hace GET. Una ruta POST pasa a Nest solo si, con la misma base de partida y los mismos casos,
la app de hoy y la nueva responden lo mismo Y dejan la base igual (filas de cada tabla).

  # 1) dos bases idénticas, recién sacadas de la copia de seguridad (0_base + local.db.antes):
  python3 migracion/contrato_escritura.py base-limpia ro_esc_viejo
  python3 migracion/contrato_escritura.py base-limpia ro_esc_nuevo

  # 2) la app de hoy sobre la primera y la nueva sobre la segunda (Nest y su servir.py de legado con ro_esc_nuevo):
  DATABASE_URL=…/ro_esc_viejo python3 servir.py --bind 127.0.0.1 --puerto 8790
  (Nest con DATABASE_URL=…/ro_esc_nuevo y RO_LEGADO_URL a un servir.py con ro_esc_nuevo en 8791)

  (para comprobar la propia app de hoy en SQLite frente a Postgres: RO_DB=<copia>.db y --db <copia>.db)

  # 3) los mismos casos en las dos, y comparar (sale 0 si todo coincide):
  python3 migracion/contrato_escritura.py ejecutar --base http://127.0.0.1:8790 --db ro_esc_viejo --casos ~/RO_MIGRACION/casos_escritura.json --salida ~/RO_MIGRACION/escritura/viejo
  python3 migracion/contrato_escritura.py ejecutar --base http://127.0.0.1:4000 --db ro_esc_nuevo --casos … --salida ~/RO_MIGRACION/escritura/nuevo
  python3 migracion/contrato_escritura.py comparar ~/RO_MIGRACION/escritura/viejo ~/RO_MIGRACION/escritura/nuevo

Casos (JSON, fuera del repo porque llevan ids reales): una lista de
  {"persona": "mili", "ruta": "/api/preferencias", "cuerpo": {...}, "como": null, "nota": "guardar una preferencia"}
en orden. Cada ruta POST debe tener al menos un caso que funcione (200) y uno que se deniegue (403/400).

Lo que cambia solo por el reloj (fechas «AAAA-MM-DD HH:MM:SS», huellas del rastro) se compara por forma, no por valor.
Las bases son SIEMPRE de pruebas: base-limpia borra y rehace la que le digas. Nunca la uses con ro_app.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import contrato as C  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
ADMIN_URL = os.environ.get("ADMIN_URL", "postgresql://127.0.0.1:5432/postgres?user=ro&password=ro")
COPIA = Path(os.environ.get("RO_MIGRACION", "~/RO_MIGRACION")).expanduser() / "local.db.antes"
FECHA = re.compile(r"^\d{4}-\d{2}-\d{2}([ T]\d{2}:\d{2}(:\d{2})?)?")
COLUMNAS_RELOJ = re.compile(r"^(huella|huella_previa)$")


def url_de(db):
    base, _, consulta = ADMIN_URL.partition("?")
    return base.rsplit("/", 1)[0] + "/" + db + ("?" + consulta if consulta else "")


def base_limpia(a):
    if a.db in ("ro_app", "postgres"):
        sys.exit("Esa no: base-limpia es solo para bases de pruebas.")
    import psycopg
    with psycopg.connect(ADMIN_URL, autocommit=True) as con:
        con.execute(f'DROP DATABASE IF EXISTS "{a.db}" WITH (FORCE)')
        con.execute(f'CREATE DATABASE "{a.db}"')
    url = url_de(a.db)
    m = re.match(r"postgresql://([^?]+)\?user=(\w+)&password=(\w+)", url)
    url_prisma = f"postgresql://{m.group(2)}:{m.group(3)}@{m.group(1)}" if m else url
    subprocess.run(["pnpm", "--filter", "@ro/db", "exec", "prisma", "migrate", "deploy"], cwd=RAIZ / "v2", check=True,
                   env={**os.environ, "DATABASE_URL": url_prisma}, stdout=subprocess.DEVNULL)
    copia = Path(a.copia).expanduser()
    if not copia.exists():
        sys.exit(f"No está {copia} (se hace en la fase 1).")
    subprocess.run([sys.executable, str(RAIZ / "migracion" / "copiar_sqlite_a_pg.py"), "--sqlite", str(copia)],
                   check=True, env={**os.environ, "DATABASE_URL": url})
    print(f"✔ {a.db} lista: 0_base + {copia.name}")


def post(base, ruta, cuerpo, yo, como=None):
    datos = json.dumps(cuerpo).encode()
    url = base.rstrip("/") + ruta + (f"?como={como}" if como else "")
    req = urllib.request.Request(url, data=datos, method="POST", headers={
        "Content-Type": "application/json", "X-RO-App": "1", "Accept": "application/json",
        "X-RO-Yo": yo, "Cookie": f"ro_yo={yo}", **({"X-RO-Como": como} if como else {})})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        cuerpo = e.read()
        try:
            return e.code, json.loads(cuerpo or b"null")
        except json.JSONDecodeError:
            return e.code, {"_no_json": len(cuerpo)}
    except urllib.error.URLError as e:
        sys.exit(f"No responde {url}: {e.reason}")


def sin_reloj(o, clave=""):
    if isinstance(o, dict):
        return {k: sin_reloj(v, k) for k, v in sorted(o.items()) if k not in C.VOLATILES}
    if isinstance(o, list):
        return [sin_reloj(x) for x in o]
    if isinstance(o, str) and (FECHA.match(o) or COLUMNAS_RELOJ.match(clave)):
        return "<reloj>"
    return o


def volcar(db):
    """db: nombre de una base Postgres de pruebas, o la ruta de un fichero SQLite (la app de hoy con RO_DB=…)."""
    out = {}
    if db.endswith(".db"):
        import sqlite3
        con = sqlite3.connect(f"file:{Path(db).expanduser()}?mode=ro", uri=True)
        tablas = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY 1")]
    else:
        import psycopg
        con = psycopg.connect(url_de(db))
        tablas = [r[0] for r in con.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE' "
            "AND table_name <> '_prisma_migrations' ORDER BY 1")]
    with con:
        for t in tablas:
            cur = con.execute(f'SELECT * FROM "{t}"')
            cols = [d[0] for d in cur.description]
            filas = [{c: (v.hex() if isinstance(v, (bytes, memoryview)) else v) for c, v in zip(cols, f)} for f in cur]
            filas = [sin_reloj(f) for f in filas]
            out[t] = sorted(filas, key=lambda f: json.dumps(f, sort_keys=True, default=str))
    return out


def ejecutar(a):
    casos = json.loads(Path(a.casos).expanduser().read_text())
    salida = Path(a.salida).expanduser()
    salida.mkdir(parents=True, exist_ok=True)
    respuestas = []
    for i, c in enumerate(casos):
        cod, datos = post(a.base, c["ruta"], c.get("cuerpo", {}), c["persona"], c.get("como"))
        respuestas.append({"n": i, "ruta": c["ruta"], "persona": c["persona"], "estado": cod, "respuesta": sin_reloj(datos)})
    (salida / "respuestas.json").write_text(json.dumps(respuestas, ensure_ascii=False, indent=1, default=str))
    (salida / "base.json").write_text(json.dumps(volcar(a.db), ensure_ascii=False, indent=1, default=str))
    print(f"✔ {len(casos)} casos en {a.base}; base {a.db} volcada en {salida} (datos reales: fuera de git).")


def comparar(a):
    v, n = Path(a.viejo).expanduser(), Path(a.nuevo).expanduser()
    rv, rn = json.loads((v / "respuestas.json").read_text()), json.loads((n / "respuestas.json").read_text())
    bv, bn = json.loads((v / "base.json").read_text()), json.loads((n / "base.json").read_text())
    lineas, aceptadas = [], []
    exc = C.leer_excepciones(a.excepciones)
    for x, y in zip(rv, rn):
        motivo = C.excepcion(x["ruta"], exc)
        if motivo is not None and (x["estado"] != y["estado"] or C.diferencias(x["respuesta"], y["respuesta"])):
            aceptadas.append(f"- caso {x['n']} `{x['ruta']}` ({x['persona']}): {x['estado']} → {y['estado']} · {motivo}")
        elif x["estado"] != y["estado"]:
            lineas.append(f"- caso {x['n']} `{x['ruta']}` ({x['persona']}): estado {x['estado']} → {y['estado']}")
        else:
            lineas += [f"- caso {x['n']} `{x['ruta']}` ({x['persona']}): {d}" for d in C.diferencias(x["respuesta"], y["respuesta"])]
    if len(rv) != len(rn):
        lineas.append(f"- {len(rv)} casos en la vieja, {len(rn)} en la nueva")
    for t in sorted(set(bv) | set(bn)):
        motivo = C.excepcion(f"tabla:{t}", exc)
        if motivo is not None:
            if bv.get(t) != bn.get(t):
                aceptadas.append(f"- tabla `{t}` · {motivo}")
            continue
        if t not in bv or t not in bn:
            if not (bv.get(t) or bn.get(t)):
                continue      # tabla que solo existe en un lado y está vacía (p. ej. las de la tubería): nada que comparar
            lineas.append(f"- tabla `{t}`: solo en {'la nueva' if t in bn else 'la vieja'}")
            continue
        # filas como conjunto: lo que solo está en un lado (si no, una fila de más descuadra todas las siguientes)
        from collections import Counter
        cv = Counter(json.dumps(f, sort_keys=True, ensure_ascii=False, default=str) for f in bv[t])
        cn = Counter(json.dumps(f, sort_keys=True, ensure_ascii=False, default=str) for f in bn[t])
        solo_v, solo_n = list((cv - cn).elements()), list((cn - cv).elements())
        lineas += [f"- tabla `{t}`: fila solo en la vieja: {f[:220]}" for f in solo_v[:10]]
        lineas += [f"- tabla `{t}`: fila solo en la nueva: {f[:220]}" for f in solo_n[:10]]
        if len(solo_v) > 10 or len(solo_n) > 10:
            lineas.append(f"- tabla `{t}`: … {len(solo_v)} filas solo en la vieja y {len(solo_n)} solo en la nueva en total")
    informe = ["# Contrato de escritura: viejo frente a nuevo", "",
               f"**{len(rv)} casos · {len(bv)} tablas · {len(lineas)} diferencias.**", ""] + lineas
    if aceptadas:
        informe += ["", f"## ⚠ {len(aceptadas)} diferencias aceptadas (excepciones.txt)", ""] + aceptadas
    (n / "informe.md").write_text("\n".join(informe) + "\n", encoding="utf-8")
    print("\n".join(informe[:80]))
    sys.exit(1 if lineas else 0)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="orden", required=True)
    b = sub.add_parser("base-limpia")
    b.add_argument("db")
    b.add_argument("--copia", default=str(COPIA))
    e = sub.add_parser("ejecutar")
    e.add_argument("--base", required=True)
    e.add_argument("--db", required=True, help="base Postgres de pruebas, o fichero .db de SQLite (la app de hoy con RO_DB)")
    e.add_argument("--casos", required=True)
    e.add_argument("--salida", required=True)
    c = sub.add_parser("comparar")
    c.add_argument("viejo")
    c.add_argument("nuevo")
    c.add_argument("--excepciones", help="~/RO_MIGRACION/excepciones.txt (ver contrato.leer_excepciones)")
    a = ap.parse_args()
    {"base-limpia": base_limpia, "ejecutar": ejecutar, "comparar": comparar}[a.orden](a)


if __name__ == "__main__":
    main()

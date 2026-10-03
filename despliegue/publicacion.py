#!/usr/bin/env python3
"""despliegue/publicacion.py · ficheros de la app como documentos por versión en la base (SQLite en local, Postgres en Render).

Por qué: en Render el servicio web (servir.py) y las tareas programadas (la tubería) NO comparten disco, y cada vuelta
de una tarea arranca de cero. Todo lo que tiene que sobrevivir entre vueltas o pasar de la tubería a la web va a la
base, en tres «espacios»:
  · data     data/ + indicadores.json                 la tubería PUBLICA al acabar; la web BAJA cada minuto y recarga
  · cache    fuentes*/_cache, fuentes*/_crudo, primera_vez.json, anuncios.json e historia/
                                                       la tubería BAJA al empezar y PUBLICA al acabar
  · crudos   los datos a mano de config.DATOS_A_MANO y las carpetas hermanas que leen los generadores
             (20_FASE0_DATOS, 20_FASE2_CAPTACION, 10_FICHAS, 11_, 12_ y 14_)   Tomás o Claude los SUBEN desde el Mac
             cuando cambian («publicar crudos»); la tubería los baja al empezar. (Riesgo R7: su edad se ve en la salud.)
«Todo o nada» de verdad: cada versión se marca vigente en UNA operación de la base, así que nunca se ve la mitad.

Tablas (mismo SQL en los dos motores): datos_blob(sha, contenido zlib) · datos_version(id, espacio, creada, origen,
estado, ficheros, bytes) · datos_fichero(version, ruta, sha). Se guardan las 10 últimas versiones de cada espacio.

Órdenes:
  python3 publicacion.py publicar [data|cache|crudos] [origen]
  python3 publicacion.py bajar [data|cache|crudos|todo] [carpeta_de_prueba]
  python3 publicacion.py versiones
  python3 publicacion.py volver <id>          deja vigente una versión anterior (vuelta atrás de datos en un clic)
"""
import hashlib
import os
import sys
import threading
import time
import zlib
from datetime import datetime
from pathlib import Path

AQUI = Path(__file__).resolve().parent
APP = AQUI.parent
sys.path.insert(0, str(AQUI))
sys.path.insert(1, str(APP))
import config  # noqa: E402
import estado as ES  # noqa: E402

GUARDAR = 10
MAX_BYTES = 60_000_000
TABLAS = """
CREATE TABLE IF NOT EXISTS datos_blob (sha TEXT PRIMARY KEY, contenido {blob});
CREATE TABLE IF NOT EXISTS datos_version (id {pk}, espacio TEXT, creada TEXT, origen TEXT, estado TEXT, ficheros INTEGER, bytes INTEGER);
CREATE TABLE IF NOT EXISTS datos_fichero (version INTEGER, ruta TEXT, sha TEXT, PRIMARY KEY (version, ruta));
"""
HERMANAS = ["20_FASE0_DATOS", "20_FASE2_CAPTACION", "10_FICHAS", "11_DECISIONES_PARA_TOMAS.md",
            "12_PLAN_DE_CONSTRUCCION_v2.md", "14_GOOGLE_ADS_VIA_WINDSOR.md"]
IGNORAR = ("__pycache__", ".DS_Store", ".git")


def raices(destino=None):
    if destino is None:
        return {"APP": APP, "CRUDOS": config.CRUDOS, "PROYECTO": config.PROYECTO}
    d = Path(destino)
    return {"APP": d / "APP", "CRUDOS": d / "CRUDOS", "PROYECTO": d / "PROYECTO"}


def _bajo(base, prefijo, rel):
    """(ruta_publicada, Path) de un fichero o de todo lo que cuelga de una carpeta."""
    p = base / rel
    if p.is_file():
        yield f"{prefijo}/{rel}", p
    elif p.is_dir():
        for f in sorted(p.rglob("*")):
            if f.is_file() and not any(x in f.parts for x in IGNORAR) and not f.name.endswith(".tmp") and f.stat().st_size <= MAX_BYTES:
                yield f"{prefijo}/{f.relative_to(base)}", f


def ficheros(espacio, destino=None):
    R = raices(destino)
    if espacio == "data":
        for ruta, f in _bajo(R["APP"], "APP", "data"):
            if not f.name.startswith("."):
                yield ruta, f
        yield from _bajo(R["APP"], "APP", "indicadores.json")
    elif espacio == "cache":
        app = R["APP"]
        rels = [str(p.relative_to(app)) for p in sorted(app.glob("fuentes*/_cache")) + sorted(app.glob("fuentes*/_crudo"))]
        rels += ["fuentes_incidencias/primera_vez.json", "fuentes_captacion/anuncios.json", "historia"]
        if destino is not None:   # en una carpeta de prueba no hay fuentes*/: se enumera lo bajado
            rels = [str(p.relative_to(app)) for p in sorted(app.glob("*")) if p.name != "data" and p.name != "indicadores.json"]
        for rel in rels:
            yield from _bajo(app, "APP", rel)
    elif espacio == "crudos":
        for _, (ruta, *_resto) in config.DATOS_A_MANO.items():
            try:
                rel = Path(ruta).relative_to(config.CRUDOS)
            except ValueError:
                continue
            yield from _bajo(R["CRUDOS"], "CRUDOS", str(rel))
        for h in HERMANAS:
            yield from _bajo(R["PROYECTO"], "PROYECTO", h)
    else:
        raise SystemExit(f"Espacio desconocido: {espacio}")


def _tablas(E):
    blob, pk = ("BLOB", "INTEGER PRIMARY KEY AUTOINCREMENT") if E.motor == "sqlite" else ("BYTEA", "BIGSERIAL PRIMARY KEY")
    with E.conexion() as con:
        cur = con.cursor()
        for s in TABLAS.format(blob=blob, pk=pk).split(";"):
            if s.strip():
                cur.execute(s)


def publicar(espacio="data", origen="tuberia", E=None, destino=None):
    E = E or ES.abrir()
    _tablas(E)
    q = E.q
    filas, total = [], 0
    with E.conexion() as con:
        cur = con.cursor()
        cur.execute(q("SELECT sha FROM datos_blob"))
        hay = {r[0] for r in cur.fetchall()}
        for ruta, f in ficheros(espacio, destino):
            b = f.read_bytes()
            sha = hashlib.sha256(b).hexdigest()
            total += len(b)
            if sha not in hay:
                cur.execute(q("INSERT INTO datos_blob (sha, contenido) VALUES (?, ?)"), (sha, zlib.compress(b, 6)))
                hay.add(sha)
            filas.append((ruta, sha))
        cur.execute(q("INSERT INTO datos_version (espacio, creada, origen, estado, ficheros, bytes) VALUES (?,?,?,?,?,?)")
                    + (" RETURNING id" if E.motor == "postgres" else ""),
                    (espacio, datetime.now().isoformat(timespec="seconds"), origen, "preparando", len(filas), total))
        vid = cur.fetchone()[0] if E.motor == "postgres" else cur.lastrowid
        for ruta, sha in filas:
            cur.execute(q("INSERT INTO datos_fichero (version, ruta, sha) VALUES (?,?,?)"), (vid, ruta, sha))
        # el cambio de vigente va en la MISMA transacción: o se ve la versión entera o la anterior
        cur.execute(q("UPDATE datos_version SET estado='anterior' WHERE estado='vigente' AND espacio=?"), (espacio,))
        cur.execute(q("UPDATE datos_version SET estado='vigente' WHERE id=?"), (vid,))
        cur.execute(q("SELECT id FROM datos_version WHERE espacio=? ORDER BY id DESC"), (espacio,))
        viejas = [r[0] for r in cur.fetchall()][GUARDAR:]
        for v in viejas:
            cur.execute(q("DELETE FROM datos_fichero WHERE version=?"), (v,))
            cur.execute(q("DELETE FROM datos_version WHERE id=?"), (v,))
        if viejas:
            cur.execute(q("DELETE FROM datos_blob WHERE sha NOT IN (SELECT DISTINCT sha FROM datos_fichero)"))
    return vid, len(filas), total


def vigente(espacio="data", E=None):
    E = E or ES.abrir()
    _tablas(E)
    r = E.ejecutar("SELECT id FROM datos_version WHERE estado='vigente' AND espacio=? ORDER BY id DESC LIMIT 1", (espacio,))
    return r[0][0] if r else None


def _marca(espacio, destino):
    """La marca de «qué versión tengo» vive en el propio disco que se rellena (no en la base ni en estado/ compartido)."""
    R = raices(destino)
    return (R["CRUDOS"] if espacio == "crudos" else R["APP"]) / f".version_{espacio}"


def bajar(espacio="data", destino=None, E=None, recargar=None, forzar=False):
    """Baja la versión vigente si es distinta de la que hay. Devuelve la versión o None si no había cambios."""
    E = E or ES.abrir()
    vid = vigente(espacio, E)
    if vid is None:
        return None
    marca = _marca(espacio, destino)
    if not forzar and marca.exists() and marca.read_text().strip() == str(vid):
        return None
    R = raices(destino)
    with E.conexion() as con:
        cur = con.cursor()
        cur.execute(E.q("SELECT f.ruta, f.sha, b.contenido FROM datos_fichero f JOIN datos_blob b ON b.sha=f.sha WHERE f.version=?"), (vid,))
        filas = cur.fetchall()
    quedan = set()
    for ruta, sha, contenido in filas:
        prefijo, rel = ruta.split("/", 1)
        f = R[prefijo] / rel
        quedan.add(str(f))
        if f.exists() and hashlib.sha256(f.read_bytes()).hexdigest() == sha:
            continue
        f.parent.mkdir(parents=True, exist_ok=True)
        tmp = f.with_name(f".{f.name}.tmp")
        tmp.write_bytes(zlib.decompress(bytes(contenido)))
        tmp.replace(f)
    if espacio != "crudos":                    # lo que ya no está en la versión, fuera (los crudos nunca se borran)
        for _, f in list(ficheros(espacio, destino)):
            if str(f) not in quedan:
                f.unlink()
    marca.parent.mkdir(parents=True, exist_ok=True)
    marca.write_text(str(vid))
    if recargar:
        recargar()
    return vid


def arrancar_sincronizacion(recargar, cada_s=None):
    """Para servir.py en el servidor: baja data/ al arrancar y luego cada minuto si ha cambiado."""
    cada_s = cada_s or int(os.environ.get("RO_SINCRONIZAR_S") or 60)

    def bucle():
        while True:
            time.sleep(cada_s)
            try:
                v = bajar("data", recargar=recargar)
                if v:
                    print(f"[publicacion] data/ actualizado a la versión {v}", flush=True)
            except Exception as e:
                print(f"[publicacion] no pude bajar data/: {e}", file=sys.stderr, flush=True)
    try:
        bajar("data", recargar=recargar)
    except Exception as e:
        print(f"[publicacion] primera bajada fallida: {e}", file=sys.stderr, flush=True)
    threading.Thread(target=bucle, daemon=True).start()


def volver(vid, E=None):
    E = E or ES.abrir()
    r = E.ejecutar("SELECT espacio FROM datos_version WHERE id=?", (vid,))
    if not r:
        sys.exit(f"No existe la versión {vid}.")
    E.ejecutar("UPDATE datos_version SET estado='anterior' WHERE estado='vigente' AND espacio=?", (r[0][0],))
    E.ejecutar("UPDATE datos_version SET estado='vigente' WHERE id=?", (vid,))
    print(f"Versión {vid} ({r[0][0]}) vigente. El servicio web la baja en menos de un minuto.")


if __name__ == "__main__":
    a = sys.argv[1:] or ["versiones"]
    if a[0] == "publicar":
        esp = a[1] if len(a) > 1 else "data"
        v, n, b = publicar(esp, a[2] if len(a) > 2 else "a_mano")
        print(f"Publicada la versión {v} de «{esp}»: {n} ficheros, {round(b / 1e6, 1)} MB")
    elif a[0] == "bajar":
        esp = a[1] if len(a) > 1 else "data"
        dest = Path(a[2]) if len(a) > 2 else None
        for e in (["crudos", "cache", "data"] if esp == "todo" else [esp]):
            print(f"«{e}»: versión", bajar(e, dest, forzar=dest is not None))
    elif a[0] == "volver":
        volver(int(a[1]))
    else:
        for r in ES.abrir().ejecutar("SELECT id, espacio, creada, origen, estado, ficheros, bytes FROM datos_version ORDER BY id DESC"):
            print(" ", r)

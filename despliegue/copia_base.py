#!/usr/bin/env python3
"""despliegue/copia_base.py · copia diaria de la base y prueba de restauración (sección 3.8 del estudio 23, E43 del 26).

Qué copia:
  · En local o en un servidor propio: local.db (rastro, decisiones, asignaciones, acciones…) y la base de estado de
    la tubería (despliegue/estado/tuberia.db), con la API de copia de SQLite (copia coherente aunque estén en uso).
  · En Render (DATABASE_URL): pg_dump en formato propio (-Fc) de la base Postgres entera.
Dónde: despliegue/estado/copias/AAAA-MM-DD/ y, si existen las variables de R2, también en Cloudflare R2 (otro
proveedor: si cae Render, la copia sigue). Se guardan 14 días en disco; en R2, 30 (regla de ciclo de vida del bucket).
Una copia que nunca se ha restaurado no cuenta: --probar restaura la última en una carpeta temporal y compara
el número de filas de cada tabla.

Uso:  python3 despliegue/copia_base.py            copia de hoy (+ R2 si está configurado)
      python3 despliegue/copia_base.py --probar   restaura la última copia aparte y la comprueba
Variables de R2 (opcionales): RO_R2_ENDPOINT (https://<cuenta>.r2.cloudflarestorage.com, jurisdicción UE),
      RO_R2_BUCKET, RO_R2_KEY_ID, RO_R2_SECRET. Necesita boto3 (va en requirements.txt del servidor).
"""
import gzip
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path

AQUI = Path(__file__).resolve().parent
APP = AQUI.parent
sys.path.insert(1, str(APP))
import config  # noqa: E402

DIAS = 14
CARPETA = config.ESTADO_DIR / "copias"


def bases_sqlite():
    out = []
    local = Path(os.environ.get("RO_DB") or APP / "local.db")
    if local.exists():
        out.append(("local", local))
    est = config.ESTADO_DIR / "tuberia.db"
    if est.exists():
        out.append(("estado", est))
    return out


def copiar():
    hoy = CARPETA / date.today().isoformat()
    hoy.mkdir(parents=True, exist_ok=True)
    hechas = []
    for nombre, ruta in bases_sqlite():
        destino = hoy / f"{nombre}.db"
        src, dst = sqlite3.connect(ruta), sqlite3.connect(destino)
        with dst:
            src.backup(dst)
        src.close(), dst.close()
        with open(destino, "rb") as fi, gzip.open(f"{destino}.gz", "wb") as fo:
            shutil.copyfileobj(fi, fo)
        destino.unlink()
        hechas.append(Path(f"{destino}.gz"))
    url = os.environ.get("DATABASE_URL", "")
    if url.startswith(("postgres://", "postgresql://")):
        destino = hoy / "postgres.dump"
        r = subprocess.run(["pg_dump", "-Fc", "--no-owner", "-f", str(destino), url], capture_output=True, text=True)
        if r.returncode != 0:
            sys.exit(f"pg_dump falló: {r.stderr[-300:]}")
        hechas.append(destino)
    subir_r2(hechas)
    # limpieza local: solo los DIAS últimos
    for d in CARPETA.iterdir():
        try:
            if date.fromisoformat(d.name) < date.today() - timedelta(days=DIAS):
                shutil.rmtree(d)
        except ValueError:
            pass
    print(f"Copia de {date.today()}: " + ", ".join(f"{h.name} ({round(h.stat().st_size / 1e6, 2)} MB)" for h in hechas))
    return hechas


def subir_r2(ficheros):
    need = ("RO_R2_ENDPOINT", "RO_R2_BUCKET", "RO_R2_KEY_ID", "RO_R2_SECRET")
    if not all(os.environ.get(v) for v in need):
        return
    import boto3
    s3 = boto3.client("s3", endpoint_url=os.environ["RO_R2_ENDPOINT"], aws_access_key_id=os.environ["RO_R2_KEY_ID"],
                      aws_secret_access_key=os.environ["RO_R2_SECRET"], region_name="auto")
    for f in ficheros:
        s3.upload_file(str(f), os.environ["RO_R2_BUCKET"], f"copias/{date.today().isoformat()}/{f.name}")
    print(f"Subidas {len(ficheros)} copias a R2 ({os.environ['RO_R2_BUCKET']}).")


def contar(con):
    tablas = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
    return {t: con.execute(f'SELECT count(*) FROM "{t}"').fetchone()[0] for t in tablas}


def probar():
    dias = sorted((d for d in CARPETA.iterdir() if d.is_dir()), reverse=True) if CARPETA.exists() else []
    if not dias:
        sys.exit("No hay ninguna copia todavía.")
    ultima = dias[0]
    tmp = Path(tempfile.mkdtemp(prefix="ro_restaura_"))
    ok = True
    for gz in ultima.glob("*.db.gz"):
        restaurada = tmp / gz.name[:-3]
        with gzip.open(gz, "rb") as fi, open(restaurada, "wb") as fo:
            shutil.copyfileobj(fi, fo)
        con = sqlite3.connect(restaurada)
        integridad = con.execute("PRAGMA integrity_check").fetchone()[0]
        filas = contar(con)
        con.close()
        original = dict(bases_sqlite()).get(gz.name.split(".")[0])
        actual = contar(sqlite3.connect(original)) if original else {}
        # la base viva puede tener filas nuevas desde la copia (nunca menos: nada se borra)
        menos = {t: (n, actual.get(t)) for t, n in filas.items() if actual and actual.get(t, 0) < n}
        bien = integridad == "ok" and not menos
        ok &= bien
        print(f"{'✔' if bien else '✘'} {gz.name}: integridad {integridad} · {len(filas)} tablas · {sum(filas.values())} filas"
              + (f" · tablas con MENOS filas en la viva: {menos}" if menos else ""))
    if (ultima / "postgres.dump").exists():
        r = subprocess.run(["pg_restore", "--list", str(ultima / "postgres.dump")], capture_output=True, text=True)
        print(f"{'✔' if r.returncode == 0 else '✘'} postgres.dump legible ({len(r.stdout.splitlines())} objetos)")
        ok &= r.returncode == 0
    shutil.rmtree(tmp, ignore_errors=True)
    print(f"Prueba de restauración de {ultima.name}: {'BIEN' if ok else 'MAL'} · {datetime.now():%H:%M}")
    return ok


if __name__ == "__main__":
    if "--probar" in sys.argv:
        sys.exit(0 if probar() else 1)
    copiar()

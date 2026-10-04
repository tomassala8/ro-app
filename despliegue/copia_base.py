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
      python3 despliegue/copia_base.py --hora     copia de ESTA hora de la Postgres (cron cada hora, Tomás 4-oct):
                                                  pg_dump, se abre entera y se cuentan sus filas contra la base viva,
                                                  manifiesto, R2 y borrado de las de más de RO_COPIAS_DIAS (7) días
Variables: RO_COPIAS_DIR (carpeta de copias; pruebas), RO_COPIAS_DIAS (cuántos días se guardan las de cada hora).
Contra el secuestro de datos (ransomware): en R2 la app SOLO SUBE. No lista ni borra: los 7 días los aplica la regla de
borrado del bucket y el bloqueo del bucket impide borrar o sobrescribir una copia antes de tiempo, aunque alguien robe la
llave de la app. Borrar desde aquí solo con RO_R2_PODAR=si (no se usa en producción).
Variables de R2 (opcionales): RO_R2_ENDPOINT (https://<cuenta>.r2.cloudflarestorage.com, jurisdicción UE),
      RO_R2_BUCKET, RO_R2_KEY_ID, RO_R2_SECRET. Necesita boto3 (va en requirements.txt del servidor).
"""
import gzip
import hashlib
import json
import os
import re
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
CARPETA = Path(os.environ.get("RO_COPIAS_DIR") or config.ESTADO_DIR / "copias")
HORAS = CARPETA / "horas"
DIAS_HORAS = float(os.environ.get("RO_COPIAS_DIAS") or 7)   # Tomás, 4-oct: «a lo mejor siete días»; se cambia aquí
SELLO = "%Y-%m-%d_%H"                                       # una carpeta por hora (UTC: no se repite al cambiar la hora)


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


def filas_del_volcado(dump):
    """Abre el volcado ENTERO (pg_restore a texto, sin base) y cuenta las filas de cada tabla. Si pg_restore no puede
    leerlo, la copia no vale. Así cada copia de cada hora queda probada, no solo hecha."""
    r = subprocess.run(["pg_restore", "--data-only", "-f", "-", str(dump)], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"pg_restore no puede leer la copia: {r.stderr[-300:]}")
    filas, tabla = {}, None
    for linea in r.stdout.splitlines():
        if tabla is None:
            m = re.match(r'COPY (?:"?[\w]+"?\.)?"?([\w]+)"? .*FROM stdin;$', linea)
            if m:
                tabla = m.group(1)
                filas[tabla] = 0
        elif linea == "\\.":
            tabla = None
        else:
            filas[tabla] += 1
    return filas


def filas_vivas(url):
    import psycopg
    with psycopg.connect(url) as c:
        tablas = [t for (t,) in c.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")]
        return {t: c.execute(f'SELECT count(*) FROM "{t}"').fetchone()[0] for t in tablas}


def r2():
    need = ("RO_R2_ENDPOINT", "RO_R2_BUCKET", "RO_R2_KEY_ID", "RO_R2_SECRET")
    if not all(os.environ.get(v) for v in need):
        return None
    import boto3
    return boto3.client("s3", endpoint_url=os.environ["RO_R2_ENDPOINT"], aws_access_key_id=os.environ["RO_R2_KEY_ID"],
                        aws_secret_access_key=os.environ["RO_R2_SECRET"], region_name="auto")


def podar(ahora, s3=None, bucket=None):
    """Borra las copias de cada hora de más de DIAS_HORAS días, en disco y en R2. Nunca la última que hay."""
    limite = ahora - timedelta(days=DIAS_HORAS)
    viejas = lambda sello: datetime.strptime(sello, SELLO) < limite  # noqa: E731
    borradas = 0
    locales = sorted(d for d in HORAS.iterdir() if d.is_dir()) if HORAS.exists() else []
    for d in locales[:-1]:
        try:
            if viejas(d.name):
                shutil.rmtree(d)
                borradas += 1
        except ValueError:
            pass   # carpeta que no es de una hora: no se toca
    if s3:
        claves = []
        for pagina in s3.get_paginator("list_objects_v2").paginate(Bucket=bucket, Prefix="copias/horas/"):
            claves += [o["Key"] for o in pagina.get("Contents", [])]
        sellos = sorted({k.split("/")[2] for k in claves if k.count("/") >= 3})
        for k in claves:
            sello = k.split("/")[2] if k.count("/") >= 3 else ""
            try:
                if sello != (sellos[-1] if sellos else "") and viejas(sello):
                    s3.delete_object(Bucket=bucket, Key=k)
                    borradas += 1
            except ValueError:
                pass
    return borradas


def copia_hora():
    url = os.environ.get("DATABASE_URL", "")
    if not url.startswith(("postgres://", "postgresql://")):
        sys.exit("--hora es para la Postgres (DATABASE_URL); la app de hoy en SQLite usa copia_seguridad.py (diaria).")
    ahora = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
    carpeta = HORAS / ahora.strftime(SELLO)
    if (carpeta / "manifiesto.json").exists():
        print(f"La copia de las {ahora:%H}:00 UTC ya está ({carpeta}).")
        return True
    carpeta.mkdir(parents=True, exist_ok=True)
    dump = carpeta / "postgres.dump"
    r = subprocess.run(["pg_dump", "-Fc", "--no-owner", "-f", str(dump), url], capture_output=True, text=True)
    if r.returncode != 0:
        shutil.rmtree(carpeta, ignore_errors=True)
        sys.exit(f"pg_dump falló: {r.stderr[-300:]}")
    try:
        copia = filas_del_volcado(dump)
    except RuntimeError as e:
        shutil.rmtree(carpeta, ignore_errors=True)
        sys.exit(str(e))
    vivas = filas_vivas(url)
    faltan = sorted(set(vivas) - set(copia))
    # Lo que se escribió DESPUÉS del volcado puede sumar filas en la viva; lo imborrable (rastro, historial…) nunca
    # puede tener menos en la viva que en la copia.
    if faltan:
        shutil.rmtree(carpeta, ignore_errors=True)
        sys.exit(f"La copia no trae estas tablas de la base: {', '.join(faltan)}")
    sha = hashlib.sha256(dump.read_bytes()).hexdigest()
    (carpeta / "manifiesto.json").write_text(json.dumps({
        "hora_utc": ahora.isoformat(), "bytes": dump.stat().st_size, "sha256": sha,
        "tablas": len(copia), "filas": sum(copia.values()), "por_tabla": copia}, ensure_ascii=False, indent=1))
    s3, bucket = r2(), os.environ.get("RO_R2_BUCKET")
    if s3:
        for f in (dump, carpeta / "manifiesto.json"):
            s3.upload_file(str(f), bucket, f"copias/horas/{carpeta.name}/{f.name}")
    # En R2 no se borra desde la app (ver arriba): solo en disco, salvo RO_R2_PODAR=si.
    borradas = podar(ahora, s3 if os.environ.get("RO_R2_PODAR") == "si" else None, bucket)
    print(f"✔ copia de las {ahora:%H}:00 UTC: {round(dump.stat().st_size / 1e6, 2)} MB · {len(copia)} tablas · "
          f"{sum(copia.values())} filas · leída entera · {'en R2' if s3 else 'solo en disco'} · "
          f"{borradas} de más de {DIAS_HORAS:g} días borradas")
    if os.environ.get("RENDER") and not s3:
        # En Render el disco de un cron se pierde al terminar: sin R2, esta copia no sobrevive. Que se vea en rojo.
        sys.exit("✘ Sin R2 configurado: en Render esta copia se pierde al terminar el cron. Faltan RO_R2_* (Tomás).")
    return True


if __name__ == "__main__":
    if "--hora" in sys.argv:
        sys.exit(0 if copia_hora() else 1)
    if "--probar" in sys.argv:
        sys.exit(0 if probar() else 1)
    copiar()

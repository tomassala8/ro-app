#!/usr/bin/env python3
"""despliegue/copia_seguridad.py · copia diaria VERIFICADA de la base de la app (3-oct-2026).

Qué hace (una vez al día; si la copia de hoy ya está y se verificó, no repite salvo --forzar):
  1. Copia local.db (rastro, decisiones, avisos, acciones, envíos…) y la base de estado de la tubería (tuberia.db) con la
     API de copia de SQLite: copia coherente aunque la app esté escribiendo.
  2. La VERIFICA antes de darla por buena: integrity_check de la copia y mismo número de filas por tabla que el original
     en el momento de copiar. Comprime con gzip, la descomprime aparte y vuelve a comprobarla (una copia que no se ha
     abierto no cuenta). Deja manifiesto.json con tamaños, huella sha256, tablas y filas.
  3. Rotación: se guardan las 7 últimas diarias y, de lo anterior, la más nueva de cada una de las 4 últimas semanas.
  4. Disco: nunca llena el disco. No copia si quedan menos de «libre_min_mb» (1.024 MB) + lo que ocuparía la copia, ni si
     el total de copias pasaría de «tope_total_mb» (800 MB): entonces borra primero lo más viejo que ya no toca guardar y,
     si aun así no cabe, sale con error (lo ve el vigía en rojo y avisa a Agus).
  5. Servidor: también a Cloudflare R2 (jurisdicción UE) cuando haya llave Y Tomás lo encienda: RO_COPIA_R2=si + RO_R2_ENDPOINT,
     RO_R2_BUCKET, RO_R2_KEY_ID, RO_R2_SECRET (boto3). HOY APAGADO: sin esas variables no sale nada de la máquina.
Dónde: despliegue/estado/copias/AAAA-MM-DD/{local.db.gz, estado.db.gz, manifiesto.json}. El vigía (despliegue/vigia.py,
fila «Copia de seguridad del día») lee esa carpeta y el manifiesto. En Render con Postgres sigue valiendo copia_base.py (pg_dump).

Uso:  python3 despliegue/copia_seguridad.py              copia de hoy (si falta) + rotación
      python3 despliegue/copia_seguridad.py --forzar     la rehace aunque ya esté
      python3 despliegue/copia_seguridad.py --estado     lista las copias guardadas
      python3 despliegue/copia_seguridad.py --restaurar AAAA-MM-DD <destino.db>   saca la de ese día a un fichero aparte
Variables: RO_DB (base de la app), RO_ESTADO_DIR, RO_COPIAS_DIR (pruebas), RO_COPIA_TOPE_MB, RO_COPIA_LIBRE_MIN_MB.
Códigos: 0 bien (o ya estaba) · 1 la copia no se pudo hacer o no pasó la verificación · 2 sin espacio.
"""
import gzip
import hashlib
import json
import os
import shutil
import sqlite3
import sys
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

AQUI = Path(__file__).resolve().parent
APP = AQUI.parent
sys.path.insert(1, str(APP))
import config  # noqa: E402

CARPETA = Path(os.environ.get("RO_COPIAS_DIR") or config.ESTADO_DIR / "copias")
DIARIAS, SEMANALES = 7, 4
TOPE_TOTAL_MB = float(os.environ.get("RO_COPIA_TOPE_MB") or 800)
LIBRE_MIN_MB = float(os.environ.get("RO_COPIA_LIBRE_MIN_MB") or 1024)
MADRID = ZoneInfo("Europe/Madrid")


def hoy():
    return datetime.now(MADRID).date()


def mb(p):
    return Path(p).stat().st_size / 1024 ** 2 if Path(p).exists() else 0.0


def bases():
    out = []
    local = Path(os.environ.get("RO_DB") or APP / "local.db")
    if local.exists():
        out.append(("local", local))
    est = config.ESTADO_DIR / "tuberia.db"
    if est.exists():
        out.append(("estado", est))
    return out


def recuento(con):
    tablas = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
    return {t: con.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0] for t in tablas}


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def copias():
    if not CARPETA.exists():
        return []
    return sorted([d for d in CARPETA.iterdir() if d.is_dir() and len(d.name) == 10 and d.name[4] == "-"], key=lambda d: d.name, reverse=True)


def total_mb():
    return sum(mb(f) for d in copias() for f in d.iterdir() if f.is_file())


def que_guardar(dias):
    """Las 7 más nuevas y, del resto, la más nueva de cada una de las 4 semanas siguientes (semana ISO)."""
    guardar = set(dias[:DIARIAS])
    semanas = []
    for d in dias[DIARIAS:]:
        try:
            s = date.fromisoformat(d).isocalendar()[:2]
        except ValueError:
            continue
        if s not in semanas and len(semanas) < SEMANALES:
            semanas.append(s)
            guardar.add(d)
    return guardar


def rotar(extra_hueco_mb=0.0):
    borradas = []
    dias = [d.name for d in copias()]
    guardar = que_guardar(dias)
    for d in copias():
        if d.name not in guardar:
            shutil.rmtree(d)
            borradas.append(d.name)
    # tope de tamaño: si con la copia nueva no cabe, fuera lo más viejo (nunca la de hoy ni la última verificada)
    while total_mb() + extra_hueco_mb > TOPE_TOTAL_MB and len(copias()) > 1:
        vieja = copias()[-1]
        shutil.rmtree(vieja)
        borradas.append(vieja.name)
    return borradas


def verificar_db(ruta, esperado=None):
    con = sqlite3.connect(f"file:{ruta}?mode=ro", uri=True)
    try:
        ok = con.execute("PRAGMA integrity_check").fetchone()[0]
        filas = recuento(con)
    finally:
        con.close()
    if ok != "ok":
        raise RuntimeError(f"integrity_check: {ok[:120]}")
    if esperado is not None and filas != esperado:
        dif = {t: (esperado.get(t), filas.get(t)) for t in set(esperado) | set(filas) if esperado.get(t) != filas.get(t)}
        raise RuntimeError(f"filas distintas del original: {dict(list(dif.items())[:5])}")
    return filas


def copiar(forzar=False):
    dia = hoy().isoformat()
    destino = CARPETA / dia
    man = destino / "manifiesto.json"
    if not forzar and man.exists():
        try:
            m = json.loads(man.read_text())
            if m.get("verificada"):
                print(f"La copia de hoy ({dia}) ya está y se verificó a las {m.get('hora')}: nada que hacer.")
                return 0
        except ValueError:
            pass
    fuentes = bases()
    if not fuentes:
        print("No hay base que copiar.")
        return 1
    estimado = sum(mb(r) for _, r in fuentes) * 0.35 + 1      # gzip de SQLite: ~25-35 % del original
    CARPETA.mkdir(parents=True, exist_ok=True)
    borradas = rotar(extra_hueco_mb=estimado)
    libre = shutil.disk_usage(str(CARPETA)).free / 1024 ** 2
    if libre < LIBRE_MIN_MB + sum(mb(r) for _, r in fuentes) + estimado:
        print(f"Sin espacio: quedan {libre:.0f} MB y hacen falta {LIBRE_MIN_MB:.0f} MB libres + la copia. No se copia (el vigía lo avisa).")
        return 2
    if total_mb() + estimado > TOPE_TOTAL_MB:
        print(f"Las copias pasarían del tope de {TOPE_TOTAL_MB:.0f} MB: sube RO_COPIA_TOPE_MB o libera espacio.")
        return 2
    tmpdir = Path(tempfile.mkdtemp(prefix="copia_", dir=str(CARPETA)))
    manifiesto = {"dia": dia, "hora": datetime.now(MADRID).strftime("%H:%M"), "verificada": False, "bases": {}, "borradas_rotacion": borradas,
                  "r2": "apagado"}
    try:
        for nombre, ruta in fuentes:
            plano = tmpdir / f"{nombre}.db"
            src, dst = sqlite3.connect(str(ruta), timeout=30), sqlite3.connect(str(plano))
            try:
                with dst:
                    src.backup(dst)                     # instantánea coherente; las filas se cuentan en la copia misma
            finally:
                src.close(), dst.close()
            filas = verificar_db(plano)
            gz = tmpdir / f"{nombre}.db.gz"
            with open(plano, "rb") as fi, gzip.open(gz, "wb", compresslevel=6) as fo:
                shutil.copyfileobj(fi, fo)
            plano.unlink()
            prueba = tmpdir / f"_{nombre}_prueba.db"            # se abre la comprimida: si no se lee, no vale
            with gzip.open(gz, "rb") as fi, open(prueba, "wb") as fo:
                shutil.copyfileobj(fi, fo)
            verificar_db(prueba, esperado=filas)
            prueba.unlink()
            manifiesto["bases"][nombre] = {"original_mb": round(mb(ruta), 2), "copia_mb": round(mb(gz), 2), "sha256": sha256(gz),
                                           "tablas": len(filas), "filas": sum(filas.values())}
        manifiesto["verificada"] = True
        (tmpdir / "manifiesto.json").write_text(json.dumps(manifiesto, ensure_ascii=False, indent=1))
        if destino.exists():
            shutil.rmtree(destino)
        os.replace(tmpdir, destino)
    except Exception as e:  # noqa: BLE001
        shutil.rmtree(tmpdir, ignore_errors=True)
        print(f"La copia NO vale y no se guarda: {type(e).__name__}: {e}")
        return 1
    manifiesto["r2"] = subir_r2(destino)
    if manifiesto["r2"] != "apagado":
        (destino / "manifiesto.json").write_text(json.dumps(manifiesto, ensure_ascii=False, indent=1))
    tam = sum(b["copia_mb"] for b in manifiesto["bases"].values())
    print(f"Copia {dia} verificada · {', '.join('%s: %s filas en %s tablas' % (k, v['filas'], v['tablas']) for k, v in manifiesto['bases'].items())} · "
          f"{tam:.1f} MB comprimida · copias guardadas: {len(copias())} ({total_mb():.1f} MB)"
          + (f" · rotación: fuera {', '.join(borradas)}" if borradas else "") + f" · R2: {manifiesto['r2']}")
    return 0


def subir_r2(carpeta):
    """Solo si Tomás lo enciende (RO_COPIA_R2=si) y están las 4 variables de R2. Si no, no sale nada de la máquina."""
    if os.environ.get("RO_COPIA_R2") != "si":
        return "apagado"
    falta = [v for v in ("RO_R2_ENDPOINT", "RO_R2_BUCKET", "RO_R2_KEY_ID", "RO_R2_SECRET") if not os.environ.get(v)]
    if falta:
        return f"sin llave ({len(falta)} variables)"
    try:
        import boto3
        s3 = boto3.client("s3", endpoint_url=os.environ["RO_R2_ENDPOINT"], aws_access_key_id=os.environ["RO_R2_KEY_ID"],
                          aws_secret_access_key=os.environ["RO_R2_SECRET"], region_name="auto")
        for f in carpeta.iterdir():
            s3.upload_file(str(f), os.environ["RO_R2_BUCKET"], f"sqlite/{carpeta.name}/{f.name}")
        return "subida"
    except Exception as e:  # noqa: BLE001 · la copia local ya vale; R2 es la segunda
        return f"fallo: {type(e).__name__}"


def estado():
    for d in copias():
        m = {}
        try:
            m = json.loads((d / "manifiesto.json").read_text())
        except Exception:  # noqa: BLE001
            pass
        print(f"  {d.name}  {'verificada' if m.get('verificada') else 'SIN VERIFICAR'}  {sum(mb(f) for f in d.iterdir()):.1f} MB  {m.get('hora', '')}")
    print(f"Total: {len(copias())} copias, {total_mb():.1f} MB (tope {TOPE_TOTAL_MB:.0f} MB)")


def restaurar(dia, destino):
    gz = CARPETA / dia / "local.db.gz"
    if not gz.exists():
        sys.exit(f"No hay copia del {dia}.")
    destino = Path(destino)
    if destino.exists():
        sys.exit("El destino ya existe: elige otro fichero (nunca se pisa la base en uso).")
    with gzip.open(gz, "rb") as fi, open(destino, "wb") as fo:
        shutil.copyfileobj(fi, fo)
    print(f"Restaurada en {destino}: {sum(verificar_db(destino).values())} filas. Compárala antes de cambiar nada.")


if __name__ == "__main__":
    a = sys.argv[1:]
    if "--estado" in a:
        estado()
        sys.exit(0)
    if "--restaurar" in a:
        i = a.index("--restaurar")
        restaurar(a[i + 1], a[i + 2])
        sys.exit(0)
    sys.exit(copiar(forzar="--forzar" in a))

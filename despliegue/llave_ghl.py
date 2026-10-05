#!/usr/bin/env python3
"""despliegue/llave_ghl.py · la llave de GHL de agencia que ROTA en cada uso (riesgo R2), con UN SOLO DUEÑO.

El problema: ghl_app_refresh_token «vale 1 año o hasta que se usa». Cada vez que alguien la usa, GHL la
invalida y entrega otra. Si la usan dos sitios (el Mac y el servidor, o dos pasos a la vez), el segundo se
queda fuera y hay que volver a autorizar la app a mano (Tomás).

La solución (C5):
  · Dueño único: la tubería. Ningún otro proceso la usa en el servidor. El Mac deja de usarla en cuanto se
    siembra en el servidor (T6).
  · Vive en la BASE DE ESTADO (tabla «llaves»), no en un fichero ni en una variable de entorno.
  · prestar() toma un bloqueo («ghl_agencia») para TODO el paso, deja la llave en una carpeta privada
    temporal (RO_SECRETOS_DIR, 0700) solo mientras dura el paso, y al acabar guarda en la base la llave nueva
    que app.py escribió al rotar (app.guarda() escribe ahí cuando existe RO_SECRETOS_DIR). Luego borra la carpeta.
  · En el Mac (sin DATABASE_URL ni --base): solo el bloqueo; la llave sigue en el llavero como hasta hoy.

Órdenes:
  python3 llave_ghl.py estado                   ¿dónde está la llave y cuántas rotaciones lleva? (sin enseñarla)
  python3 llave_ghl.py sembrar                  copia la llave del llavero (o de la variable GHL_SEMILLA) a la base.
                                                Se hace UNA vez, el día T6, y desde ese momento el Mac no la usa.
  python3 llave_ghl.py prueba-simulada [N]      prueba del préstamo con una llave FALSA en una base aparte (sin red)
"""
import fcntl
import os
import shutil
import sys
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(1, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402
import estado as ES  # noqa: E402

NOMBRE = "ghl_app_refresh_token"


def modo_base(E=None):
    """La llave vive en la base si hay DATABASE_URL (servidor) o si se pide con RO_LLAVE_GHL_EN_BASE=1."""
    E = E or ES.abrir()
    return E.motor == "postgres" or os.environ.get("RO_LLAVE_GHL_EN_BASE") == "1"


def ruta_bloqueo_app():
    """El MISMO fichero de bloqueo que usa ~/RO_HERRAMIENTAS/ghl_agencia/app.py (acceso()) fuera de la tubería."""
    return Path(os.environ.get("RO_GHL_BLOQUEO") or config.HERRAMIENTAS / "ghl_agencia" / ".llave.lock")


@contextmanager
def bloqueo_app(espera=True):
    """Toma el bloqueo de app.py (auditoría 35, M8): así un app.py lanzado a mano, por otra sesión o por un paso sin
    «ghl_agencia» no rota la llave mientras la tiene prestada la tubería. A los pasos se les pasa el bloqueo
    (RO_GHL_BLOQUEO_HEREDADO = nuestro pid) para que su app.acceso() no se quede esperándose a sí mismo."""
    f = ruta_bloqueo_app()
    if not f.parent.is_dir():
        yield {}
        return
    fh = open(f, "a+")
    t0 = time.time()
    while True:
        try:
            fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
            break
        except BlockingIOError:
            if not espera or time.time() - t0 > float(os.environ.get("RO_GHL_ESPERA_S", 300)):
                fh.close()
                raise ES.Ocupado("ghl_agencia (app.py)")
            time.sleep(0.2)
    try:
        fh.seek(0), fh.truncate(), fh.write(f"{os.getpid()} {time.strftime('%Y-%m-%d %H:%M:%S')} tuberia\n"), fh.flush()
        yield {"RO_GHL_BLOQUEO": str(f), "RO_GHL_BLOQUEO_HEREDADO": str(os.getpid())}
    finally:
        fcntl.flock(fh, fcntl.LOCK_UN)
        fh.close()


@contextmanager
def prestar(E=None, espera=True):
    """Úsalo alrededor de cualquier paso que llame a app.acceso(): el paso recibe RO_SECRETOS_DIR en su entorno.
    Devuelve el diccionario de entorno extra para el subproceso."""
    E = E or ES.abrir()
    with E.bloqueo("ghl_agencia", espera=espera), bloqueo_app(espera) as heredado:
        if not modo_base(E):
            yield dict(heredado)          # Mac: el llavero, como siempre; solo garantizamos que nadie más la usa
            return
        valor, _ = E.leer_llave(NOMBRE)
        if not valor:
            raise RuntimeError("La llave de GHL no está sembrada en la base: «python3 despliegue/llave_ghl.py sembrar» (T6).")
        carpeta = Path(tempfile.mkdtemp(prefix="ro_sec_"))
        os.chmod(carpeta, 0o700)
        f = carpeta / NOMBRE
        fd = os.open(f, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as fh:
            fh.write(valor)
        try:
            yield {"RO_SECRETOS_DIR": str(carpeta), **heredado}
        finally:
            # Pase lo que pase en el paso, lo que haya en el fichero es la llave buena más reciente.
            nuevo = f.read_text().strip() if f.exists() else ""
            if nuevo and nuevo != valor:
                E.guardar_llave(NOMBRE, nuevo, origen="rotacion")
            shutil.rmtree(carpeta, ignore_errors=True)


def sembrar(E=None):
    E = E or ES.abrir()
    v = os.environ.get("GHL_SEMILLA") or config._de_llavero(NOMBRE)
    if not v:
        sys.exit("No encuentro la llave ni en el llavero ni en GHL_SEMILLA.")
    with E.bloqueo("ghl_agencia", espera=True):
        E.guardar_llave(NOMBRE, v, origen="siembra")
    print(f"Sembrada en la base ({E.motor}). Desde ahora SOLO la usa la tubería: no lances app.py ni captacion.py en el Mac.")


def prueba_simulada(n=24):
    """Préstamo con una llave falsa en una base temporal: comprueba bloqueo, rotación y guardado (sin red)."""
    import subprocess
    tmp = Path(tempfile.mkdtemp(prefix="ro_prueba_ghl_"))
    os.environ["RO_ESTADO_DIR"] = str(tmp)
    config.ESTADO_DIR = tmp
    E = ES.SQLite(tmp / "prueba.db")
    os.environ["RO_LLAVE_GHL_EN_BASE"] = "1"
    os.environ["RO_GHL_BLOQUEO"] = str(tmp / "ghl.lock")     # el bloqueo de app.py, también en la carpeta de la prueba
    E.guardar_llave(NOMBRE, "falsa-0", origen="siembra")
    # Un «paso» que hace lo mismo que app.acceso(): lee la llave con llave() y escribe la nueva con guarda().
    paso = ("import os,sys; sys.path.insert(0, " + repr(str(config.HERRAMIENTAS / 'ghl_agencia')) + "); import app; "
            "v = app.llave('ghl_app_refresh_token'); n = int(v.split('-')[1]) + 1; app.guarda('ghl_app_refresh_token', f'falsa-{n}')")
    for i in range(n):
        with prestar(E) as extra:
            subprocess.run([sys.executable, "-c", paso], env={**os.environ, **extra}, check=True)
    valor, rot = E.leer_llave(NOMBRE)
    ok = valor == f"falsa-{n}" and rot == n
    # El bloqueo impide un segundo préstamo a la vez
    doble = False
    with prestar(E):
        try:
            with prestar(E, espera=False):
                doble = True
        except ES.Ocupado:
            pass
    shutil.rmtree(tmp, ignore_errors=True)
    print(f"{n} rotaciones seguidas: {'BIEN' if ok else 'MAL'} (llave final {valor}, rotaciones {rot}) · "
          f"segundo préstamo a la vez: {'MAL, entró' if doble else 'BIEN, bloqueado'}")
    return ok and not doble


if __name__ == "__main__":
    orden = sys.argv[1] if len(sys.argv) > 1 else "estado"
    if orden == "sembrar":
        sembrar()
    elif orden == "prueba-simulada":
        sys.exit(0 if prueba_simulada(int(sys.argv[2]) if len(sys.argv) > 2 else 24) else 1)
    else:
        E = ES.abrir()
        v, rot = E.leer_llave(NOMBRE)
        print(f"Base: {E.motor} · llave en la base: {'sí' if v else 'no'} · rotaciones: {rot} · "
              f"modo: {'base con bloqueo' if modo_base(E) else 'llavero del Mac (solo bloqueo)'}")

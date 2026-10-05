#!/usr/bin/env python3
"""despliegue/pruebas_solidez_N-08.py · N-08: no se publica sin bajar `data` ni una versión mucho más pequeña (sospechosa).

Uso:  python3 despliegue/pruebas_solidez_N-08.py
Sobre una base SQLite temporal (RO_ESTADO_DIR/RO_ESTADO_DB) y una carpeta `destino` temporal; nunca `data/` real.
(1) Versión A con 10 ficheros; B con 4 (menos del 80 %) → B «sospechosa», A sigue vigente; con `forzar=True`, B pasa a vigente.
(2) 10 ficheros pero un 60 % menos de bytes → «sospechosa».
(3) 9 ficheros y bytes parecidos → vigente (una fuente que se cae no bloquea).
(4) La vigente no se poda aunque haya más de 10 versiones sospechosas detrás.
(5) `tuberia.bajar_antes` con `PUB.bajar` que lanza para `data`: `registro["bajado"]["data"] is None` y `registro["sin_publicar"]`;
    y el bloque de publicar de `tuberia.py` comprueba `sin_publicar` antes de llamar a `PUB.publicar`.
Sale 0 si pasa; si no, 1.
"""
import os
import re
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
temp = Path(tempfile.mkdtemp(prefix="n08_estado_"))
os.environ["RO_ESTADO_DIR"] = str(temp)
os.environ["RO_ESTADO_DB"] = str(temp / "tuberia.db")
os.environ.pop("DATABASE_URL", None)
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "despliegue"))
fallos = []


def ok(t):
    print(f"  ✔ {t}")


def mal(t):
    print(f"  ✘ {t}")
    fallos.append(t)


import estado as ES  # noqa: E402
import publicacion as PUB  # noqa: E402

E = ES.SQLite(temp / "tuberia.db")
destino = Path(tempfile.mkdtemp(prefix="n08_destino_"))
datos = destino / "APP" / "data"


def poner(n, tam):
    """Deja n ficheros de `tam` bytes cada uno (contenido distinto en cada versión, para que no se compartan blobs)."""
    import shutil
    shutil.rmtree(datos, ignore_errors=True)
    datos.mkdir(parents=True)
    for i in range(n):
        (datos / f"f{i}.json").write_bytes(os.urandom(tam // 2).hex().encode()[:tam])


def publicar(n, tam, **kw):
    poner(n, tam)
    vid, _, _ = PUB.publicar("data", origen="prueba N-08", E=E, destino=destino, **kw)
    return vid


# (1)
a = publicar(10, 1000)
b = publicar(4, 1000)
if PUB.estado_version(a, E) == "vigente" and PUB.estado_version(b, E) == "sospechosa" and PUB.vigente("data", E) == a:
    ok("10 → 4 ficheros: la nueva queda «sospechosa» y la vigente sigue")
else:
    mal(f"10→4: A={PUB.estado_version(a, E)} B={PUB.estado_version(b, E)} vigente={PUB.vigente('data', E)}")
c = publicar(4, 1000, forzar=True)
if PUB.estado_version(c, E) == "vigente":
    ok("con forzar=True la versión pequeña pasa a vigente")
else:
    mal(f"forzar: {PUB.estado_version(c, E)}")
# (2)
d = publicar(4, 1000)    # igual que C: pasa y es la vigente (4 ficheros, 4000 bytes)
e = publicar(4, 300)
if PUB.estado_version(e, E) == "sospechosa" and PUB.vigente("data", E) == d:
    ok("mismos ficheros pero un 70 % menos de bytes: «sospechosa»")
else:
    mal(f"bytes: {PUB.estado_version(e, E)} vigente={PUB.vigente('data', E)}")
# (3)
f = publicar(10, 1000, forzar=True)     # vuelve a haber 10 ficheros vigentes
g = publicar(9, 1000)
if PUB.estado_version(g, E) == "vigente" and PUB.estado_version(f, E) == "anterior":
    ok("9 ficheros y bytes parecidos: vigente (una fuente caída no bloquea)")
else:
    mal(f"9 ficheros: G={PUB.estado_version(g, E)} F={PUB.estado_version(f, E)}")
# (4)
for _ in range(12):
    publicar(2, 100)
vig = PUB.vigente("data", E)
if vig == g and PUB.estado_version(g, E) == "vigente":
    ok("12 sospechosas después: la vigente no se poda")
else:
    mal(f"poda: vigente={vig} (esperada {g})")

# (5)
import tuberia as T  # noqa: E402

import types
falso = types.ModuleType("publicacion")
falso.bajar = lambda esp, E=None, **kw: (_ for _ in ()).throw(RuntimeError("base caída (doble)")) if esp == "data" else 3
real = sys.modules["publicacion"]
sys.modules["publicacion"] = falso
try:
    registro = {}
    T.bajar_antes(E, registro)
finally:
    sys.modules["publicacion"] = real
if registro.get("bajado", {}).get("data") is None and "data" in registro.get("bajado", {}) and registro.get("sin_publicar") \
        and registro["bajado"].get("cache") == 3:
    ok("bajar falla para data: bajado[data] = None y la vuelta marca sin_publicar")
else:
    mal(f"bajar_antes: {registro}")
src = (RAIZ / "despliegue" / "tuberia.py").read_text(encoding="utf-8")
i_sin, i_pub = src.find('registro.get("sin_publicar")'), src.find('PUB.publicar("cache"')
if 0 < i_sin < i_pub:
    ok("tuberia.py comprueba sin_publicar antes de llamar a PUB.publicar")
else:
    mal("tuberia.py no comprueba sin_publicar antes de publicar")

if fallos:
    print(f"\n✘ N-08: {len(fallos)} fallo(s)")
    sys.exit(1)
print("\n✔ N-08")

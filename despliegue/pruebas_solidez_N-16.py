#!/usr/bin/env python3
"""despliegue/pruebas_solidez_N-16.py · N-16: el grupo `ro-llaves` de render.yaml pide todas las llaves; la web sigue sin ellas.

Uso: python3 despliegue/pruebas_solidez_N-16.py       (solo lee ficheros; pone RO_SIN_LLAVES=1 ella misma; no lee ninguna llave)
(1) `migracion/llaves_nube.py` (con RO_SIN_LLAVES=1) no dice «FALTA en render.yaml» en ninguna línea (su código de salida
    no sirve esta noche: solo cuenta lo que hay en el Mac);
(2) toda llave del inventario (`config.SECRETOS` + las extra de `llaves_nube.py`), salvo las que rotan (`config.ROTA`),
    está en el grupo `ro-llaves` en MAYÚSCULAS, siempre con `sync: false` (nunca un valor);
(3) el servicio web `ro-app` NO usa `fromGroup: ro-llaves`; si existe `v2/render.yaml` (F7.2), su `ro-legado` sí y
    su `ro-web` no.
Sin datos reales en la salida.
"""
import importlib.util
import os
import pathlib
import re
import subprocess
import sys

os.environ["RO_SIN_LLAVES"] = "1"
RAIZ = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
fallos, n = [], 0


def ok(c, t):
    global n
    n += 1
    if not c:
        fallos.append(t)


# (1) la herramienta de revisión
r = subprocess.run([sys.executable, "migracion/llaves_nube.py"], cwd=RAIZ, env=dict(os.environ, RO_SIN_LLAVES="1"), capture_output=True, text=True)
faltan = [l.split()[1] for l in r.stdout.splitlines() if "FALTA en render.yaml" in l]
ok(not faltan, f"(1) llaves_nube dice FALTA en render.yaml para: {', '.join(faltan)}")


def bloque(texto, nombre):
    """Texto del elemento `- name: <nombre>` hasta el siguiente elemento al mismo nivel."""
    m = re.search(r"^(\s*)-\s+(?:type:\s*\w+\s*\n\s*)?name:\s*%s\b.*?(?=^\1-\s|\Z)" % re.escape(nombre), texto, re.S | re.M)
    return m.group(0) if m else ""


def con_grupo(texto, servicio, grupo):
    return re.search(r"fromGroup:\s*%s\b" % re.escape(grupo), bloque(texto, servicio)) is not None


# (2) el grupo
texto = (RAIZ / "despliegue" / "render.yaml").read_text(encoding="utf-8")
grupo = bloque(texto, "ro-llaves")
ok(bool(grupo), "(2) no se encuentra el grupo ro-llaves")
claves = re.findall(r"-\s*\{\s*key:\s*([A-Z0-9_]+),\s*sync:\s*false\s*\}", grupo)
todas = re.findall(r"key:\s*([A-Z0-9_]+)", grupo)
ok(sorted(claves) == sorted(todas), "(2) alguna llave de ro-llaves no es `sync: false` (podría llevar valor): " + ", ".join(sorted(set(todas) - set(claves))))
ok(not re.search(r"key:\s*[A-Z0-9_]+\s*\n\s*value:", grupo), "(2) alguna llave de ro-llaves lleva `value:`")
spec = importlib.util.spec_from_file_location("llaves_nube", RAIZ / "migracion" / "llaves_nube.py")
LN = importlib.util.module_from_spec(spec)
spec.loader.exec_module(LN)
esperadas = {k.upper() for k in LN.inventario() if k not in LN.config.ROTA}
ok(esperadas <= set(claves), "(2) llaves que no están en ro-llaves: " + ", ".join(sorted(esperadas - set(claves))))

# (3) quién las recibe
ok(bool(bloque(texto, "ro-app")) and not con_grupo(texto, "ro-app", "ro-llaves"), "(3) ro-app (la web) no se encuentra o recibe ro-llaves")
ok(con_grupo(texto, "ro-ligera", "ro-llaves") and con_grupo(texto, "ro-completa", "ro-llaves"), "(3) la tubería (ro-ligera y ro-completa) no recibe ro-llaves")
nuevo = RAIZ / "v2" / "render.yaml"
if nuevo.exists():
    t2 = nuevo.read_text(encoding="utf-8")
    ok(con_grupo(t2, "ro-legado", "ro-llaves"), "(3) v2/render.yaml: ro-legado no recibe ro-llaves")
    ok(not con_grupo(t2, "ro-web", "ro-llaves"), "(3) v2/render.yaml: ro-web recibe ro-llaves")

print(f"{'✘' if fallos else '✔'} N-16: {n} comprobaciones" + (" · " + " · ".join(fallos) if fallos else ""))
sys.exit(1 if fallos else 0)

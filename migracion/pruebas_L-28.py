#!/usr/bin/env python3
"""migracion/pruebas_L-28.py · L-28: el escáner de secretos no toma `-iTCP@127.0.0.1` por un correo (sin servidor).

Uso: python3 migracion/pruebas_L-28.py
  1. `escanear_fichero` sobre textos con `lsof -iTCP@127.0.0.1:8770 -sTCP:LISTEN`, `-iUDP@…` y `-iTCP@::1`: sin hallazgos;
     un correo de verdad y `-iTCP@dominio.test` siguen saltando (no se abre ninguna excepción por dominio).
  2. `escaner_secretos.py --proyecto` sobre el árbol de trabajo: ninguno de los ficheros que llevan una opción de `lsof` aparece
     entre los hallazgos (la salida solo enseña ficheros y muestras tapadas; el resto de hallazgos son de otros motivos).
  3. `pruebas_seguridad.py` M3 y `pruebas_e0.py:94` no se ejecutan ni se tocan: son jueces. Se apuntan para Tomás.
Sale 0 si pasa.
"""
import pathlib
import re
import subprocess
import sys
import tempfile

RAIZ = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
import escaner_secretos as E  # noqa: E402

fallos, n = [], 0


def ok(cond, txt):
    global n
    n += 1
    if not cond:
        fallos.append(txt)


def correos(texto):
    return [h for h in hallazgos(texto) if h.get("tipo") == "correo"]


def hallazgos(texto):
    with tempfile.TemporaryDirectory() as d:
        p = pathlib.Path(d) / "t.txt"
        p.write_text(texto, encoding="utf-8")
        return E.escanear_fichero(p)


# 1 · el escáner, por texto
for t in ('f"kill $(lsof -t -iTCP@127.0.0.1:{PUERTO} -sTCP:LISTEN)"', "lsof -iTCP@127.0.0.1:$PUERTO", "lsof -iTCP@127.0.0.1:${PUERTO} -sTCP:LISTEN",
          "lsof -iTCP@127.0.0.1:8770 -sTCP:LISTEN", 'args=["lsof","-iTCP@127.0.0.1:8771","-sTCP:LISTEN"]',
          "kill $(lsof -t -iTCP@127.0.0.1:8781 -sTCP:LISTEN)", "lsof -iUDP@127.0.0.1", "lsof -iTCP@::1:8770"):
    ok(not hallazgos(t), f"(1) toma por secreto «{t[:40]}»")
for t in ("escribe a " + "persona" + "@" + "dominio-real.com", "lsof -iTCP" + "@" + "dominio.test", "-iTCP" + "@" + "127.0.0.1.evil",
          "lsof -iTCP" + "@" + "127.0.0.1:{x}.evil.com", "lsof -iTCP" + "@" + "127.0.0.1:{a b}"):
    ok(bool(hallazgos(t)), f"(1) deja pasar «{t[:40]}» (no debería haber excepción por dominio)")

# 2 · el proyecto, sin los ficheros con opciones de lsof entre los hallazgos
con_lsof = sorted(
    str(f.relative_to(RAIZ)) for f in E.ficheros_proyecto()
    if re.search(r"-i(TCP|UDP)@(\d{1,3}\.){3}\d{1,3}", f.read_text(encoding="utf-8", errors="ignore")))
ok(len(con_lsof) >= 2, f"(2) la prueba solo encuentra {len(con_lsof)} ficheros con opciones de lsof: ¿cambió el repo?")
salida = subprocess.run([sys.executable, "escaner_secretos.py", "--proyecto"], cwd=RAIZ, capture_output=True, text=True).stdout
marcados = set(re.findall(r"✗ (\S+):", salida))
for f in con_lsof:
    if f in marcados:
        # un fichero con lsof puede tener otro hallazgo de verdad: se mira por texto línea a línea
        # solo el trozo de la opción (con su carácter anterior), no otros correos que haya en la misma línea
        trozo = re.compile(r".?-i(?:TCP|UDP)@(?:\d{1,3}\.){3}\d{1,3}\S*")
        malas = [i for i, l in enumerate((RAIZ / f).read_text(encoding="utf-8", errors="ignore").splitlines(), 1)
                 if any(correos(t) for t in trozo.findall(l))]
        ok(not malas, f"(2) {f}: el escáner marca líneas con opción de lsof ({malas[:3]})")
    else:
        ok(True, "")

# 3 · jueces
print("M3 (pruebas_seguridad.py 282-290) y pruebas_e0.py:94 quedan para Tomás (jueces): no se ejecutan ni se tocan.")
print(f"{'✘' if fallos else '✔'} L-28: {n} comprobaciones" + (" · " + " · ".join(fallos) if fallos else ""))
sys.exit(1 if fallos else 0)

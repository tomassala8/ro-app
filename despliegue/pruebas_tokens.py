#!/usr/bin/env python3
"""despliegue/pruebas_tokens.py · la caché del token de acceso (~/RO_HERRAMIENTAS/cache_tokens.py) evita refrescos de más.
Sin red: un «refresco» falso que apunta cada llamada en un fichero.
  1. 20 lecturas seguidas en un proceso                 → 1 solo refresco
  2. 20 procesos a la vez                                → 1 solo refresco (el bloqueo hace esperar a los demás)
  3. token a punto de caducar (dentro del margen de 5 min) → se refresca otra vez
  4. Zoho, Google, Zoom y Snov usan la caché (lo comprueba en su código)
Uso: python3 despliegue/pruebas_tokens.py
"""
import os, subprocess, sys, tempfile, time
from pathlib import Path
HERR = Path(os.environ.get("RO_HERRAMIENTAS") or Path.home() / "RO_HERRAMIENTAS")
sys.path.append(str(HERR))
fallos = []
def ok(c, t):
    print(("✓ " if c else "✗ ") + t)
    if not c: fallos.append(t)
tmp = Path(tempfile.mkdtemp(prefix="ro_tokens_"))
os.environ["RO_TOKENS_DIR"] = str(tmp / "cache")
os.environ.pop("DATABASE_URL", None)
contador = tmp / "refrescos.txt"
codigo = f"""
import sys, time; sys.path.append({str(HERR)!r}); import cache_tokens as C
def refrescar():
    open({str(contador)!r}, 'a').write('x'); time.sleep(0.3); return 'tk-' + str(time.time()), VIDA, None
VIDA = float(sys.argv[1]) if len(sys.argv) > 1 else 3600
for _ in range(int(sys.argv[2]) if len(sys.argv) > 2 else 1): C.token('prueba', 'llave-falsa', refrescar)
"""
n = lambda: len(contador.read_text()) if contador.exists() else 0
subprocess.run([sys.executable, "-c", codigo, "3600", "20"], check=True)
ok(n() == 1, f"20 lecturas seguidas → {n()} refresco(s)")
contador.unlink()
procs = [subprocess.Popen([sys.executable, "-c", codigo, "3600", "1"]) for _ in range(20)]
[p.wait() for p in procs]
ok(n() == 0, f"20 procesos a la vez con token ya válido → {n()} refresco(s)")
import shutil; shutil.rmtree(tmp / "cache")
procs = [subprocess.Popen([sys.executable, "-c", codigo, "3600", "1"]) for _ in range(20)]
[p.wait() for p in procs]
ok(n() == 1, f"20 procesos a la vez sin caché → {n()} refresco(s)")
contador.unlink(); shutil.rmtree(tmp / "cache")
subprocess.run([sys.executable, "-c", codigo, "200", "3"], check=True)   # vida 200 s < margen 300 s: siempre refresca
ok(n() == 3, f"token dentro del margen de caducidad → se refresca cada vez ({n()} de 3)")
for f, marca in (("zoho/zh.py", "ct.token('zoho'"), ("google/gg.py", "ct.token('google'"), ("zoom/zm.py", "ct.token('zoom'"), ("snov/sv.py", "ct.token('snov'")):
    ok(marca in (HERR / f).read_text(), f"{f} usa la caché")
shutil.rmtree(tmp, ignore_errors=True)
print("TODO BIEN" if not fallos else f"{len(fallos)} FALLO(S)")
sys.exit(1 if fallos else 0)

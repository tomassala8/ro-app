#!/usr/bin/env python3
"""despliegue/pruebas_solidez_N-09.py · N-09: `validar()` no se conforma con «JSON no vacío».

Uso:  python3 despliegue/pruebas_solidez_N-09.py
Sin red y sobre carpetas temporales (nunca `data/` real). Mira dos cosas:
(1) Todo paso de `pasos.json` que lee una API (lista cerrada abajo) lleva `claves_minimas` y `recuento`, y los ficheros
    que nombran cuelgan de sus `salidas`.
(2) `validar()` rechaza una salida con la misma forma y TODAS las cifras a 0 donde la vuelta anterior las tenía (mismo criterio
    que `fuentes.lectura.a_cero`, N-01), no rechaza un 0 que ya estaba, y respeta `vacio_ok`.
Sale 0 si pasa; si no, 1.
"""
import json
import os
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "despliegue"))
fallos = []

# Pasos cuyo generador `fuentes_*/generar_*.py` lee una API (referencia del 4-oct). Si uno se renombra, la prueba lo dice.
LEEN_API = ["seo", "redes", "crm", "hostinger", "paneles", "gbp", "dinero", "horas", "produccion", "agenda",
            "bandeja", "captacion", "informe", "chat_equipo", "ventas", "modular"]


def ok(t):
    print(f"  ✔ {t}")


def mal(t):
    print(f"  ✘ {t}")
    fallos.append(t)


import tuberia as T  # noqa: E402

# ---------------------------------------------------------------- (1) pasos.json
pasos = {p["id"]: p for p in json.loads((RAIZ / "despliegue" / "pasos.json").read_text())["pasos"]}
sin = []
for pid in LEEN_API:
    p = pasos.get(pid)
    if not p:
        sin.append(f"{pid} (ya no está en pasos.json)")
        continue
    orden = " ".join(p.get("completo") or p.get("ligero") or [])
    if "fuentes_" not in orden:
        sin.append(f"{pid} (su comando ya no nombra un fuentes_*)")
        continue
    cm, rc = p.get("claves_minimas") or {}, p.get("recuento") or []
    if not cm or any(not v for v in cm.values()):
        sin.append(f"{pid} (sin claves_minimas)")
    if not rc:
        sin.append(f"{pid} (sin recuento)")
    salidas = [str(s).rstrip("/") for s in p.get("salidas", [])]
    for f in list(cm) + [r["fichero"] for r in rc]:
        if not any(f == s or f.startswith(s + "/") for s in salidas):
            sin.append(f"{pid} ({f} no cuelga de sus salidas)")
    for r in rc:
        if not {"fichero", "ruta"} <= set(r) or not (0 < r.get("caida_max", 0.5) < 1):
            sin.append(f"{pid} (recuento mal formado: {sorted(r)})")
if sin:
    mal("pasos sin claves mínimas o recuento: " + "; ".join(sin))
else:
    ok(f"los {len(LEEN_API)} pasos que leen APIs llevan claves_minimas y recuento (y cuelgan de sus salidas)")

# ---------------------------------------------------------------- (2) validar() con «todo a 0»
d = Path(tempfile.mkdtemp(prefix="n09_"))
dest = Path(tempfile.mkdtemp(prefix="n09_inst_"))
os.chmod(dest, 0o700)
f = d / "salida" / "x.json"
f.parent.mkdir()
salidas = [str(f.parent)]


def escribir(doc):
    f.write_text(json.dumps(doc))


def vuelta(antes, ahora, p=None):
    """Instantánea con `antes`, el paso escribe `ahora`, y `validar` decide."""
    escribir(antes)
    man = T.guardar_instantanea("p", salidas, dest)
    escribir(ahora)
    return T.validar(salidas, 0, man, p)


BUENO = {"generado": "2026-10-05", "clientes": [{"id": "a", "leads": 5, "citas": 2}, {"id": "b", "leads": 3, "citas": 1}],
         "resumen": {"leads": 8, "citas": 3}}
CEROS = {"generado": "2026-10-05", "clientes": [{"id": "a", "leads": 0, "citas": 0}, {"id": "b", "leads": 0, "citas": 0}],
         "resumen": {"leads": 0, "citas": 0}}
CEROS_TEXTO = {"generado": "2026-10-05", "clientes": [{"id": "a", "leads": "0", "citas": "0,00"}], "resumen": {"leads": "0", "citas": "0"}}

r = vuelta(BUENO, CEROS)
if r and "todo a 0" in r:
    ok(f"misma forma, todo a 0 donde antes había cifras → rechazada ({r})")
else:
    mal(f"todo a 0 no se rechaza: {r!r}")
r = vuelta(BUENO, CEROS_TEXTO)
if r and "todo a 0" in r:
    ok("también si los ceros vienen como texto («0», «0,00»)")
else:
    mal(f"ceros como texto no se rechazan: {r!r}")
r = vuelta(CEROS, CEROS)
if r is None:
    ok("un 0 que ya estaba no se rechaza (no es un cambio)")
else:
    mal(f"se rechaza un 0 que ya estaba: {r!r}")
r = vuelta(BUENO, {**BUENO, "resumen": {"leads": 0, "citas": 3}})
if r is None:
    ok("un 0 suelto entre cifras no se rechaza")
else:
    mal(f"se rechaza un 0 suelto: {r!r}")
r = vuelta({"generado": "ayer", "nota": "sin cifras"}, CEROS)
if r is None:
    ok("si antes no había cifras tampoco se rechaza (no hay con qué comparar)")
else:
    mal(f"se rechaza sin cifras previas: {r!r}")
r = vuelta(BUENO, CEROS, {"vacio_ok": True})
if r is None:
    ok("con vacio_ok el paso admite quedarse en cero")
else:
    mal(f"vacio_ok no se respeta: {r!r}")
r = vuelta(BUENO, BUENO)
if r is None:
    ok("la salida buena de siempre pasa")
else:
    mal(f"la salida buena no pasa: {r!r}")

# el criterio es el de N-01: un solo sitio
from fuentes import lectura as L  # noqa: E402
if L.a_cero(CEROS) and not L.a_cero(BUENO) and T._lectura() is L:
    ok("`validar` usa `fuentes.lectura.a_cero` (un solo criterio)")
else:
    mal("`validar` no comparte el criterio con fuentes.lectura")

print()
if fallos:
    print(f"✘ N-09: {len(fallos)} fallos")
    sys.exit(1)
print("✔ N-09")

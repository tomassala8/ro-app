#!/usr/bin/env python3
"""migracion/pruebas_L-34.py · L-34: la tarifa por hora, las horas de referencia, los topes de cartera y los umbrales de salud viven en un sitio.

Uso: python3 migracion/pruebas_L-34.py   (sin servidor)
(1) `modulos/_constantes_ro.js` existe, no importa nada y exporta TARIFA_HORA_EUR = 31.47, HORAS_MES_REFERENCIA = 128,
    TOPE_CARTERA = { account: 12, trafficker: 16, crm: 16 } y SALUD = { verde: 60, ambar: 40 }, cada una con su comentario.
(2) En `modulos/*.js` (menos `indice.js`, catálogo que `permisos.py` lee como texto) y `componentes.js`, fuera de ese fichero y de las líneas de comentario, no aparece: `31,47`/`31.47`;
    `128` seguido de «h»/«horas»; los umbrales 60/40 de la salud; los topes 12 y 16 juntos junto a tope/cartera/account.
(3) Quien usa una constante la importa de `_constantes_ro.js`.
Sale 0 si pasa; si no, 1 con la lista de líneas. Sin datos reales.
"""
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parents[1]
fallos = []

# (1) el fichero
const = RAIZ / "modulos" / "_constantes_ro.js"
if not const.exists():
    fallos.append("falta modulos/_constantes_ro.js")
else:
    t = const.read_text(encoding="utf-8")
    if re.search(r"^\s*import\b", t, re.M):
        fallos.append("_constantes_ro.js importa algo (debe ser una hoja, sin ciclos)")
    for nombre, patron in (
        ("TARIFA_HORA_EUR", r"export\s+const\s+TARIFA_HORA_EUR\s*=\s*31\.47\b"),
        ("HORAS_MES_REFERENCIA", r"export\s+const\s+HORAS_MES_REFERENCIA\s*=\s*128\b"),
        ("TOPE_CARTERA", r"export\s+const\s+TOPE_CARTERA\s*=\s*\{\s*account:\s*12,\s*trafficker:\s*16,\s*crm:\s*16\s*\}"),
        ("SALUD", r"export\s+const\s+SALUD\s*=\s*\{\s*verde:\s*60,\s*ambar:\s*40\s*\}"),
    ):
        m = re.search(patron, t)
        if not m:
            fallos.append(f"_constantes_ro.js no exporta {nombre} con su valor")
        else:
            antes = t[:m.start()].rstrip().splitlines()
            if not antes or not re.match(r"\s*(//|/\*|\*)", antes[-1]):
                fallos.append(f"_constantes_ro.js: {nombre} sin comentario encima (de dónde sale)")

# (2) y (3) los usos
def codigo(linea):
    s = linea.strip()
    return not (s.startswith("//") or s.startswith("*") or s.startswith("/*"))

def sin_comentario_final(linea):
    # quita un «// …» final que no esté dentro de un texto (los comentarios con el número pueden quedarse)
    en, q = None, None
    for i, c in enumerate(linea):
        if en:
            if c == "\\":
                continue
            if c == en:
                en = None
        elif c in "'\"`":
            en = c
        elif c == "/" and linea[i:i + 2] == "//" and (i == 0 or linea[i - 1] != ":"):
            return linea[:i]
    return linea

REGLAS = (
    ("tarifa 31,47", re.compile(r"31[,.]47")),
    ("128 h", re.compile(r"\b128\b\s*(?:h\b|horas)")),
    ("128 por defecto", re.compile(r"\?\?\s*128\b")),
    ("umbral de salud 60/40", re.compile(r"(?:salud\w*|valor)[^\n]{0,40}(?:>=?|<=?)\s*(?:60|40)\b|semaforo\([^)]*\{\s*verde:\s*60,\s*ambar:\s*40")),
    ("topes 12 y 16", re.compile(r"(?=.*(?:tope|cartera|account|trafficker))(?=.*\b12\b)(?=.*\b16\b)", re.I)),
    ("tope de cartera suelto", re.compile(r"\b(?:account|trafficker|crm):\s*1[26]\b")),
)
usan = {}
ficheros = sorted((RAIZ / "modulos").glob("*.js")) + [RAIZ / "componentes.js"]
for f in ficheros:
    # `indice.js` es el catálogo de módulos y `permisos.py` lo lee como texto (sus `resumen` son cadenas fijas, no plantillas):
    # los dos textos con 31,47 y 128 h se quedan; ver NOTAS_NOCHE.md «L-34».
    if f.name in ("_constantes_ro.js", "indice.js"):
        continue
    lineas = f.read_text(encoding="utf-8").splitlines()
    for i, linea in enumerate(lineas, 1):
        if not codigo(linea):
            continue
        c = sin_comentario_final(linea)
        for nombre, rx in REGLAS:
            if rx.search(c):
                fallos.append(f"{f.relative_to(RAIZ)}:{i}: {nombre}: {linea.strip()[:100]}")
        for k in ("TARIFA_HORA_EUR", "HORAS_MES_REFERENCIA", "TOPE_CARTERA", "SALUD"):
            if re.search(rf"\b{k}\b", c):
                usan.setdefault(f, set()).add(k)
    texto = "\n".join(lineas)
    for k in usan.get(f, ()):
        if not re.search(rf"import\s*\{{[^}}]*\b{k}\b[^}}]*\}}\s*from\s*'[./]*(?:modulos/)?_?[./]*_constantes_ro\.js'", texto):
            fallos.append(f"{f.relative_to(RAIZ)}: usa {k} sin importarla de _constantes_ro.js")

print(("✔ " if not fallos else "✘ ") + "L-34: " + ("constantes en un sitio" if not fallos else f"{len(fallos)} fallos"))
for x in fallos:
    print("  -", x)
sys.exit(1 if fallos else 0)

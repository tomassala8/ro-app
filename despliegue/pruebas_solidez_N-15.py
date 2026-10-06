#!/usr/bin/env python3
"""despliegue/pruebas_solidez_N-15.py · N-15: ninguna ruta de Descargas escrita a mano fuera de `config.py`.

Uso: python3 despliegue/pruebas_solidez_N-15.py       (solo lee el código; no abre datos ni red)
(1) En `fuentes*` y `despliegue` (menos los `pruebas_*.py`, que juzgan) la palabra «Downloads» solo puede estar en un
    comentario, en un docstring o en una etiqueta de origen (texto que sale en pantalla y no se usa como ruta:
    lista cerrada abajo; cambiarla cambiaría lo que ve el equipo).
(2) `config.CRUDOS` termina en `Downloads` en el Mac y `RO_CRUDOS` lo cambia en la nube.
Sin datos reales en la salida.
"""
import ast
import io
import os
import pathlib
import subprocess
import sys
import tokenize

RAIZ = pathlib.Path(__file__).resolve().parents[1]
fallos, n = [], 0

# Etiquetas de origen: texto de pantalla (pantalla de salud y «_meta»), no rutas. Fichero → trozo exacto de la cadena.
ETIQUETAS = {
    "fuentes/f_externos.py": '"Downloads/HERRAMIENTA_RO_2026-10-02/externos.json"',
    "fuentes/f_libro.py": '"Downloads/BAJAS_LTV_CHURN_2026-10-01/clientes.json"',
    "fuentes_personas/generar_personas.py": "Downloads/PLAN_FICHAJES_Q4_2026/plan_fichajes_q4.html (28-sep",
}


def ok(c, t):
    global n
    n += 1
    if not c:
        fallos.append(t)


def lineas_de_texto(codigo):
    """Líneas que son comentario o están dentro de un docstring."""
    cubiertas = set()
    for tok in tokenize.generate_tokens(io.StringIO(codigo).readline):
        if tok.type == tokenize.COMMENT:
            cubiertas.add(tok.start[0])
    for nodo in ast.walk(ast.parse(codigo)):
        if isinstance(nodo, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and nodo.body:
            primero = nodo.body[0]
            if isinstance(primero, ast.Expr) and isinstance(primero.value, ast.Constant) and isinstance(primero.value.value, str):
                cubiertas.update(range(primero.lineno, primero.end_lineno + 1))
    return cubiertas


sueltas = []
for carpeta in sorted(p for p in RAIZ.iterdir() if p.is_dir() and (p.name.startswith("fuentes") or p.name == "despliegue")):
    for f in carpeta.rglob("*.py"):
        rel = f.relative_to(RAIZ).as_posix()
        if "__pycache__" in rel or f.name.startswith("pruebas_"):
            continue
        codigo = f.read_text(encoding="utf-8", errors="replace")
        if "Downloads" not in codigo:
            continue
        try:
            texto = lineas_de_texto(codigo)
        except (SyntaxError, tokenize.TokenError):
            texto = set()
        for i, linea in enumerate(codigo.splitlines(), 1):
            if "Downloads" in linea and i not in texto and not (rel in ETIQUETAS and ETIQUETAS[rel] in linea):
                sueltas.append(f"{rel}:{i}")
ok(not sueltas, "(1) «Downloads» fuera de comentarios, docstrings y etiquetas: " + ", ".join(sueltas))

r = subprocess.run([sys.executable, "-c", "import config as C; print(C.CRUDOS)"], cwd=RAIZ, capture_output=True, text=True,
                   env={k: v for k, v in os.environ.items() if k != "RO_CRUDOS"})
ok(r.returncode == 0 and r.stdout.strip().endswith("Downloads"), f"(2) config.CRUDOS no acaba en Downloads: {r.stdout.strip()[-60:]}")
r = subprocess.run([sys.executable, "-c", "import config as C; print(C.CRUDOS)"], cwd=RAIZ, capture_output=True, text=True,
                   env=dict(os.environ, RO_CRUDOS="/tmp/n15_crudos"))
ok(r.returncode == 0 and r.stdout.strip() == "/tmp/n15_crudos", f"(2) RO_CRUDOS no manda en config.CRUDOS: {r.stdout.strip()[-60:]}")

print(f"{'✘' if fallos else '✔'} N-15: {n} comprobaciones" + (" · " + " · ".join(fallos) if fallos else ""))
sys.exit(1 if fallos else 0)

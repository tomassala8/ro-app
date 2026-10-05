#!/usr/bin/env python3
"""fuentes_consejos/cerebros/pendientes.py · junta en PENDIENTES_TOMAS.md lo que solo Tomás puede decidir (4-oct-2026).

Cada cerebro guarda sus dudas en _meta.pendientes_tomas, con lo que se ha aplicado mientras tanto.
  python3 fuentes_consejos/cerebros/pendientes.py
"""
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import buscar as B  # noqa: E402

lineas = ["# Pendientes de Tomás en los cerebros de área", "",
          "Lo que cada cerebro no puede cerrar solo. Entre tanto, la ficha aplica lo que dice cada punto.",
          "Al decidir: corrige el cerebro, quita el punto de su `_meta.pendientes_tomas` y vuelve a lanzar este script.", ""]
total = 0
for area, c in B.cerebros().items():
    p = c.get("_meta", {}).get("pendientes_tomas") or []
    if not p:
        continue
    lineas += [f"## {c['_meta'].get('titulo', area)} ({len(p)})", ""]
    lineas += [f"{i}. {x}" for i, x in enumerate(p, 1)]
    lineas.append("")
    total += len(p)
(AQUI / "PENDIENTES_TOMAS.md").write_text("\n".join(lineas), encoding="utf-8")
print(f"PENDIENTES_TOMAS.md: {total} puntos")

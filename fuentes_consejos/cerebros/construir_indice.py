#!/usr/bin/env python3
"""fuentes_consejos/cerebros/construir_indice.py · escribe indice.json (4-oct-2026).

Lee los doce <area>.json y deja en indice.json los mapas tipo/alerta/indicador/regla → situaciones y el índice de
palabras para el buscador. buscar.py lo reconstruye en memoria si falta o está viejo; esto solo ahorra el arranque.

  python3 fuentes_consejos/cerebros/construir_indice.py
"""
import json
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import buscar as B  # noqa: E402

ix = B.construir()
(AQUI / "indice.json").write_text(json.dumps(ix, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
print(f"indice.json: {len(ix['situaciones'])} situaciones · {len(ix['tipo'])} tipos · {len(ix['alerta'])} alertas · "
      f"{len(ix['indicador'])} indicadores · {len(ix['frases'])} frases")

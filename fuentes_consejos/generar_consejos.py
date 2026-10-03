#!/usr/bin/env python3
"""fuentes_consejos/generar_consejos.py · N12 · precalcula «Qué haría yo hoy aquí» de TODAS las personas activas.

  python3 fuentes_consejos/generar_consejos.py            # todas las personas activas → data/consejos/p_<id>.json
  python3 fuentes_consejos/generar_consejos.py lucia mili # solo esas
  python3 fuentes_consejos/generar_consejos.py --resumen  # además, cuántos consejos sale por persona y pantalla

Paso de la tubería (C5): DESPUÉS de fuentes_alertas/generar_alertas.py y fuentes_verdad/generar_verdad.py (lee sus
salidas). Solo lee y escribe data/consejos/; no llama a ninguna API ni escribe en local.db.

Cada persona recibe los candidatos que salen de SUS datos, recortados por servir.py igual que en /api/modulo/* (con
ella como persona real). ia.consejo vuelve a filtrar al servir (pantalla, cliente, «ver como», dinero) y corta a 3.
Sin este fichero, o si está viejo, el servidor calcula lo mismo al momento: el precalculado solo acelera y sirve
para «ver como» (que nunca lee el fichero de alertas de otra persona).
"""
import json
import os
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

APP = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(APP))
os.chdir(APP)

import servir as S  # noqa: E402  (al importarse engancha ia.py)
import ia as IA     # noqa: E402

SALIDA = APP / "data" / "consejos"


def main():
    S.E.cargar()
    if IA.S is None:                                   # por si servir.py no lo enganchó (sin ia.py en su sitio)
        IA.enganchar(S.Manejador, S)
    SALIDA.mkdir(parents=True, exist_ok=True)
    pedidas = [a for a in sys.argv[1:] if not a.startswith("--")]
    personas = [p for p in S.E.crudo["personas"] if p.get("estado", "activo") == "activo" and (not pedidas or p["id"] in pedidas)]
    resumen = {}
    for p in personas:
        d = IA.candidatos_vivos(p, p)
        d["formato"] = 1
        d["nota"] = "Candidatos por reglas (N12). Se sirven por /api/ia/consejo, filtrados otra vez por permisos y cortados a 3 por pantalla."
        tmp = SALIDA / f".p_{p['id']}.json.tmp"
        tmp.write_text(json.dumps(d, ensure_ascii=False, indent=1))
        tmp.replace(SALIDA / f"p_{p['id']}.json")
        resumen[p["id"]] = Counter(pt for c in d["candidatos"] for pt in c["pantallas"])
    print(f"Consejos precalculados de {len(personas)} personas en data/consejos/ ({datetime.now():%H:%M}).")
    if "--resumen" in sys.argv:
        for pid, c in resumen.items():
            print(f"  {pid:22} {sum(c.values()):4} candidatos · " + ", ".join(f"{k} {v}" for k, v in c.most_common(6)))


if __name__ == "__main__":
    main()

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
PRIORIDADES = APP / "data" / "prioridades"


def prioridades_de(p, d):
    """3-oct · cerebro v2 · contrato para «Lo mío» (carril U1, mi_dia.js): la prioridad de cada cosa de ESTA persona, como
    la vería ella (sin euros si no ve la cuota de ese cliente). data/prioridades/p_<id>.json, servido solo a esa persona.
      por_alerta  {id de alerta: {...}}   (la fila «alerta» de Lo mío lleva clave = id de la alerta)
      por_cliente {cliente_id: {...}}      (la mejor de ese cliente: sirve para correos y piezas de ese cliente)
      por_objeto  {ruta «#/…»: {...}}      (el objeto al que lleva el consejo)
      orden       [ids de consejo en orden]
    Cada {...}: puntos, nivel (alto/medio/bajo), urgencia, dias_retraso, esfuerzo_min, motivo (una línea, ya recortada),
    euros_mes (solo si la ve), confianza, regla, criterio_url."""
    cp = S.P.contexto(p, S.E.crudo)
    xs = []
    for c in d["candidatos"]:
        x = IA.para_quien(p, c)
        x = IA._limpio_consejo(p, p, cp, x) if x else None
        if x:
            xs.append(x)
    xs.sort(key=lambda c: -(c.get("orden") or 0))
    def fila(c):
        pr = c.get("prioridad") or {}
        cr = c.get("criterio") or {}
        return {"consejo": c["id"], "tipo": c.get("tipo"), "puntos": c.get("orden"), "nivel": (pr.get("impacto") or {}).get("nivel"),
                "euros_mes": (pr.get("impacto") or {}).get("euros_mes"), "urgencia": (pr.get("urgencia") or {}).get("nivel"),
                "dias_retraso": (pr.get("urgencia") or {}).get("dias_retraso"), "esfuerzo_min": (pr.get("esfuerzo") or {}).get("minutos"),
                "motivo": c.get("motivo_orden"), "confianza": c.get("confianza"), "regla": cr.get("id"), "criterio_url": cr.get("url"),
                "delegado": bool(c.get("delegado"))}
    por_alerta, por_cliente, por_objeto = {}, {}, {}
    for c in xs:
        f = {k: v for k, v in fila(c).items() if v is not None}
        if c["id"].startswith("al:"):
            por_alerta.setdefault(c["id"][3:], f)
        if c.get("cliente_id"):
            por_cliente.setdefault(c["cliente_id"], f)
        if c.get("ir"):
            por_objeto.setdefault(c["ir"], f)
    return {"formato": 1, "generado": d.get("generado"), "persona_id": p["id"],
            "nota": "Prioridad del cerebro de decisiones v2 (impacto, urgencia, esfuerzo, puesto y aprendizaje). Ordena «Lo mío» por «puntos» (mayor primero) y enseña «motivo» en una línea.",
            "orden": [c["id"] for c in xs], "por_alerta": por_alerta, "por_cliente": por_cliente, "por_objeto": por_objeto}


def main():
    S.E.cargar()
    if IA.S is None:                                   # por si servir.py no lo enganchó (sin ia.py en su sitio)
        IA.enganchar(S.Manejador, S)
    SALIDA.mkdir(parents=True, exist_ok=True)
    pedidas = [a for a in sys.argv[1:] if not a.startswith("--")]
    personas = [p for p in S.E.crudo["personas"] if p.get("estado", "activo") == "activo" and (not pedidas or p["id"] in pedidas)]
    PRIORIDADES.mkdir(parents=True, exist_ok=True)
    # 3-oct · cerebro v2 · bucle de aprendizaje ANTES de puntuar: seguimiento a 7/14 días y ajuste por regla
    CDm = IA.CD
    try:
        with S.conectar() as con:
            vals = CDm.AP.valoraciones(con)
        doc_apr = CDm.AP.evaluar(vals)
        CDm.AP.guardar(doc_apr)
        CDm.AP.informe_semanal(doc_apr, CDm.reglas())
    except Exception as e:
        print(f"  aprendizaje: {type(e).__name__}: {e}")
        doc_apr = None
    resumen, por_persona = {}, {}
    for p in personas:
        d = IA.candidatos_vivos(p, p)
        d["formato"] = 1
        d["nota"] = "Candidatos por reglas (N12) + cerebro de decisiones v2 (diagnóstico, prioridad, criterio). Se sirven por /api/ia/consejo, filtrados otra vez por permisos y cortados a 3 por pantalla."
        tmp = SALIDA / f".p_{p['id']}.json.tmp"
        tmp.write_text(json.dumps(d, ensure_ascii=False, indent=1))
        tmp.replace(SALIDA / f"p_{p['id']}.json")
        por_persona[p["id"]] = d["candidatos"]
        try:
            pri = prioridades_de(p, d)
            tmp = PRIORIDADES / f".p_{p['id']}.json.tmp"
            tmp.write_text(json.dumps(pri, ensure_ascii=False, indent=1))
            tmp.replace(PRIORIDADES / f"p_{p['id']}.json")
        except Exception as e:
            print(f"  prioridades de {p['id']}: {type(e).__name__}: {e}")
        resumen[p["id"]] = Counter(pt for c in d["candidatos"] for pt in c["pantallas"])
    if not pedidas:                       # la foto del día solo con todas las personas (si no, faltarían consejos)
        CDm.AP.foto(por_persona, IA._j("verdad/clientes.json"))
    print(f"Consejos precalculados de {len(personas)} personas en data/consejos/ y prioridades en data/prioridades/ ({datetime.now():%H:%M})."
          + (f" Aprendizaje: {doc_apr['valoraciones']} valoraciones, {len(doc_apr['ajustes'])} reglas ajustadas." if doc_apr else ""))
    if "--resumen" in sys.argv:
        for pid, c in resumen.items():
            print(f"  {pid:22} {sum(c.values()):4} candidatos · " + ", ".join(f"{k} {v}" for k, v in c.most_common(6)))


if __name__ == "__main__":
    main()

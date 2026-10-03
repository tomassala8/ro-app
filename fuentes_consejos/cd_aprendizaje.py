#!/usr/bin/env python3
"""fuentes_consejos/cd_aprendizaje.py · Cerebro de decisiones v2 (3-oct-2026) · BUCLE DE APRENDIZAJE.

1. Valoración: «Útil / No útil / Ya hecho» en cada consejo → rastro «consejo_valorado» (SOLO lo escribe el servidor, con la
   métrica del consejo en ese momento: el navegador manda el id y el valor, nunca la cifra).
2. Foto diaria (tubería): la métrica de cada candidato vivo → data/consejos/_privado/historia/AAAA-MM-DD.json.
3. Seguimiento: para cada «Ya hecho» o «Útil», la métrica a los 7 y a los 14 días (la foto más cercana a partir de ese
   día). Si el consejo ya no sale (la alerta se cerró) = resuelto. Mejoró / igual / empeoró por regla.
4. Ajuste: las reglas con mal resultado o muchos «No útil» bajan de prioridad (hasta −60 puntos); las que funcionan suben
   (hasta +20). Se guarda en data/consejos/_privado/aprendizaje.json y lo lee el cerebro al puntuar.
5. Informe semanal para Tomás: data/consejos/_privado/informe_semanal.{json,md} (qué consejos funcionan, cuáles no).

Nada de esto sale del servidor salvo el informe (solo dirección, por /api/ia/consejo/informe).
"""
import json
import re
from datetime import datetime, timedelta
from pathlib import Path

APP = Path(__file__).resolve().parent.parent
PRIV = APP / "data" / "consejos" / "_privado"
HIST = PRIV / "historia"
F_APR = PRIV / "aprendizaje.json"
VALORES = ("util", "no_util", "hecho")
GRAV_RANGO = {"critico": 2, "atencion": 1, "bien": 0}
MIN_MUESTRA = 3            # con menos de 3 casos una regla no se mueve (ni para arriba ni para abajo)


def metrica(c, grav=None):
    """{valor, grav} de un consejo: primer número de la cifra (menos es mejor) y gravedad del cliente."""
    md = c.get("metrica") if isinstance(c.get("metrica"), dict) else None      # el diagnóstico trae la suya (más leads = mejor)
    m = re.match(r"\s*(\d+(?:[.,]\d+)?)", str(c.get("cifra") or ""))
    valor = md.get("valor") if md else (float(m.group(1).replace(",", ".")) if m else None)
    return {"valor": valor, "mejor": (md or {}).get("mejor") or "baja",
            "grav": GRAV_RANGO.get(grav or c.get("grav_cliente")), "tipo": c.get("tipo"),
            "regla": (c.get("criterio") or {}).get("id"), "cliente_id": c.get("cliente_id")}


def foto(candidatos_por_persona, verdad_full, hoy=None):
    """Guarda la foto del día (une a todas las personas; un id es el mismo objeto para todas)."""
    hoy = hoy or datetime.now().strftime("%Y-%m-%d")
    HIST.mkdir(parents=True, exist_ok=True)
    gidx = {c.get("cliente_id"): c.get("gravedad") for c in (verdad_full or {}).get("clientes") or []}
    out = {"fecha": hoy, "consejos": {}, "gravedad": gidx}
    for cs in candidatos_por_persona.values():
        for c in cs:
            out["consejos"].setdefault(c["id"], metrica(c, gidx.get(c.get("cliente_id"))))
    tmp = HIST / f".{hoy}.tmp"
    tmp.write_text(json.dumps(out, ensure_ascii=False))
    tmp.replace(HIST / f"{hoy}.json")
    return out


def _fotos():
    out = {}
    for f in sorted(HIST.glob("*.json")):
        try:
            out[f.stem] = json.loads(f.read_text())
        except Exception:
            pass
    return out


def valoraciones(con):
    """Del rastro (tabla registro), sin anuladas. Cada una: quien, consejo, valor, fecha, metrica, regla, tipo."""
    out = []
    try:
        anuladas = {r[0] for r in con.execute("SELECT anula_a FROM registro WHERE anula_a IS NOT NULL")}
        for rid, quien, clave, datos, creada in con.execute(
                "SELECT id, quien, clave, datos, creada FROM registro WHERE accion='consejo_valorado' AND como IS NULL ORDER BY id"):
            if rid in anuladas:
                continue
            try:
                d = json.loads(datos or "{}")
            except ValueError:
                d = {}
            if d.get("valor") not in VALORES:
                continue
            out.append({"id": rid, "quien": quien, "consejo": clave, "valor": d["valor"], "fecha": str(creada)[:10],
                        "metrica": d.get("metrica") or {}, "regla": d.get("regla") or (d.get("metrica") or {}).get("regla"),
                        "tipo": d.get("tipo"), "cliente_id": d.get("cliente_id"), "pantalla": d.get("pantalla")})
    except Exception:
        pass
    return out


def de_persona(vals, persona_id, dias=14, hoy=None):
    """Última valoración de cada consejo de esa persona en los últimos N días: {consejo_id: {valor, fecha}}."""
    hoy = hoy or datetime.now()
    lim = (hoy - timedelta(days=dias)).strftime("%Y-%m-%d")
    out = {}
    for v in vals:
        if v["quien"] == persona_id and v["fecha"] >= lim:
            out[v["consejo"]] = {"valor": v["valor"], "fecha": v["fecha"]}
    return out


def _comparar(m0, m1):
    """mejoró / igual / empeoró (o None si no hay con qué comparar)."""
    if m1 is None:
        return None
    if m1 == "resuelto":
        return "mejoro"
    a, b = m0.get("valor"), m1.get("valor")
    if a is not None and b is not None:
        if (m0.get("mejor") or "baja") == "sube":
            a, b = -a, -b
        return "mejoro" if b < a else "empeoro" if b > a else "igual"
    a, b = m0.get("grav"), m1.get("grav")
    if a is not None and b is not None:
        return "mejoro" if b < a else "empeoro" if b > a else "igual"
    return None


def _a_los(fotos, v, dias):
    """La métrica de ese consejo en la primera foto a partir de fecha + N días; «resuelto» si esa foto no lo tiene."""
    obj = (datetime.fromisoformat(v["fecha"]) + timedelta(days=dias)).strftime("%Y-%m-%d")
    fechas = [f for f in sorted(fotos) if f >= obj]
    if not fechas:
        return None
    f = fotos[fechas[0]]
    m = (f.get("consejos") or {}).get(v["consejo"])
    if m:
        return m
    # el id ya no sale: resuelto, salvo que el cliente haya empeorado de gravedad (entonces se compara la gravedad)
    g = (f.get("gravedad") or {}).get(v.get("cliente_id"))
    if v.get("cliente_id") and g and GRAV_RANGO.get(g, 0) > (v.get("metrica") or {}).get("grav", 9):
        return {"valor": None, "grav": GRAV_RANGO.get(g)}
    return "resuelto"


def evaluar(vals, hoy=None):
    """Seguimiento de resultados y ajuste por regla. Devuelve el documento de aprendizaje."""
    hoy = hoy or datetime.now()
    fotos = _fotos()
    seguimiento, por_regla = [], {}
    for v in vals:
        r = v.get("regla") or v.get("tipo") or "sin_regla"
        st = por_regla.setdefault(r, {"util": 0, "no_util": 0, "hecho": 0, "mejoro": 0, "igual": 0, "empeoro": 0, "pendiente": 0, "tipos": set()})
        st[v["valor"]] += 1
        if v.get("tipo"):
            st["tipos"].add(v["tipo"])
        if v["valor"] == "no_util":
            continue
        r7, r14 = _comparar(v["metrica"], _a_los(fotos, v, 7)), _comparar(v["metrica"], _a_los(fotos, v, 14))
        res = r14 or r7
        if res:
            st[res] += 1
        else:
            st["pendiente"] += 1
        seguimiento.append({"consejo": v["consejo"], "quien": v["quien"], "valor": v["valor"], "fecha": v["fecha"], "regla": r,
                            "a_7_dias": r7, "a_14_dias": r14})
    ajustes = {}
    for r, st in por_regla.items():
        st["tipos"] = sorted(st["tipos"])
        n_res = st["mejoro"] + st["igual"] + st["empeoro"]
        n_val = st["util"] + st["no_util"] + st["hecho"]
        pts = 0
        if n_val >= MIN_MUESTRA:
            pts -= int(40 * st["no_util"] / n_val)                 # «No útil» la baja
        if n_res >= MIN_MUESTRA:
            tasa = (st["mejoro"] - st["empeoro"]) / n_res
            pts += int(20 * tasa) if tasa > 0 else int(30 * tasa)     # mal resultado pesa más que bueno
        st["ajuste_pts"] = max(-60, min(20, pts))
        if st["ajuste_pts"]:
            ajustes[r] = st["ajuste_pts"]
    return {"generado": hoy.strftime("%Y-%m-%d %H:%M"), "valoraciones": len(vals), "fotos": len(fotos),
            "por_regla": por_regla, "ajustes": ajustes, "seguimiento": seguimiento[-500:]}


def guardar(doc):
    PRIV.mkdir(parents=True, exist_ok=True)
    tmp = PRIV / ".aprendizaje.tmp"
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=1))
    tmp.replace(F_APR)


def ajustes():
    try:
        return json.loads(F_APR.read_text()).get("ajustes") or {}
    except Exception:
        return {}


def informe_semanal(doc, reglas, hoy=None):
    """Para Tomás: qué reglas funcionan (mejoran la métrica), cuáles no, y las más valoradas «No útil». Lenguaje llano."""
    hoy = hoy or datetime.now()
    filas = []
    for r, st in (doc.get("por_regla") or {}).items():
        kb = reglas.get(r) or {}
        n_res = st["mejoro"] + st["igual"] + st["empeoro"]
        filas.append({"regla": r, "texto": kb.get("regla") or r, "autor": kb.get("autor"), "util": st["util"], "no_util": st["no_util"],
                      "hecho": st["hecho"], "mejoro": st["mejoro"], "igual": st["igual"], "empeoro": st["empeoro"],
                      "pendiente": st["pendiente"], "tasa_mejora": round(st["mejoro"] / n_res, 2) if n_res else None,
                      "ajuste_pts": st.get("ajuste_pts", 0)})
    funcionan = sorted([f for f in filas if f["tasa_mejora"] is not None and f["tasa_mejora"] >= 0.5], key=lambda f: -f["mejoro"])
    no_funcionan = sorted([f for f in filas if f["ajuste_pts"] < 0], key=lambda f: f["ajuste_pts"])
    out = {"generado": hoy.strftime("%Y-%m-%d %H:%M"), "semana": f"{(hoy - timedelta(days=7)):%d-%m} a {hoy:%d-%m}",
           "valoraciones": doc.get("valoraciones", 0), "funcionan": funcionan[:10], "no_funcionan": no_funcionan[:10],
           "todas": sorted(filas, key=lambda f: -(f["util"] + f["no_util"] + f["hecho"]))}
    lineas = [f"# Consejos que funcionan · semana del {out['semana']}", "",
              f"{out['valoraciones']} valoraciones del equipo. Una regla solo se mueve con 3 casos o más.", ""]
    if not filas:
        lineas.append("Todavía no hay valoraciones: el informe se llena cuando el equipo pulse «Útil», «No útil» o «Ya hecho».")
    if funcionan:
        lineas += ["## Funcionan (la métrica mejora tras la acción)", ""] + [
            f"- {f['texto']} · {f['mejoro']} mejoran de {f['mejoro'] + f['igual'] + f['empeoro']}" for f in funcionan[:10]] + [""]
    if no_funcionan:
        lineas += ["## Bajan de prioridad", ""] + [
            f"- {f['texto']} · {f['no_util']} «No útil», {f['empeoro']} empeoran · {f['ajuste_pts']} puntos" for f in no_funcionan[:10]] + [""]
    out["md"] = "\n".join(lineas)
    PRIV.mkdir(parents=True, exist_ok=True)
    (PRIV / "informe_semanal.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    (PRIV / "informe_semanal.md").write_text(out["md"])
    return out

#!/usr/bin/env python3
"""fuentes_verdad/generar_objetivos_clientes.py · OBJETIVO DE CADA CLIENTE Y SEMÁFORO ESTRATÉGICO (3-oct-2026, encargo de Tomás
para Coti, directora de producto).

UN SOLO SITIO DE LA VERDAD para «qué nos propusimos con este cliente»:
  fuentes_verdad/objetivos_clientes.json   (a mano y revisado: el objetivo en palabras del cliente, la cifra medible, la fecha,
                                            la fuente y la confianza; lo recopiló la búsqueda del 3-oct en los repos de
                                            clientes, talleres, acuerdos, memoria y la app)
  + lo que se cargue después en la app («Cargar objetivo» de la ficha / Clientes nuevos: fuentes_objetivos/objetivos.py,
    tipo «objetivo_alta»). Si hay objetivo cargado en la app con citas_mes, leads_mes o ventas_mes, MANDA el de la app
    (es más reciente y lo puso su account); el texto del cliente sigue saliendo de aquí.

Lee (solo lectura, 0 llamadas): data/verdad/clientes.json, data/captacion/captacion.json, data/crm/crm.json,
data/nuevos/nuevos.json, data/personas.json, data/objetivos/objetivos.json, fuentes_consejos (diagnóstico y reglas).
Escribe data/verdad/objetivos_clientes.json:
  clientes[]  una fila por cliente activo (cliente_id): objetivo o «sin objetivo del cliente» + quién debe pedirlo, resultado de
              hoy frente al objetivo (sin euros), tendencia, semáforo ESTRATÉGICO (critico | vigilar | bien) con su motivo en una
              frase y, si es crítico, la recomendación del cerebro de decisiones con su porqué y su fuente.
  talleres[]  los clientes nuevos con su taller de la oferta: firma, fecha límite (regla de Clientes nuevos: alta + 2 días),
              hecho / agendado / sin agendar / tarde, quién lo lleva y días de retraso.
  renovaciones[] clientes con fin de permanencia conocido en los próximos 90 días y su riesgo (del semáforo estratégico).

El semáforo estratégico es DE RESULTADOS frente al objetivo (leads, citas, clientes). No mira plazos, correos, reuniones ni
llamadas: eso es el semáforo operativo de Operaciones (verdad única, «En rojo»). Sin importes: los textos se limpian de €.
"""
import json
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
DATA = APP / "data"
FUENTE = Path(__file__).resolve().parent / "objetivos_clientes.json"
SALIDA = DATA / "verdad" / "objetivos_clientes.json"
sys.path.insert(0, str(APP / "fuentes_consejos"))

RE_IMPORTE = re.compile(r"\s*\(?[~≈+]?\d[\d.,]*(?:\s*-\s*\d[\d.,]*)?\s*(?:[KkM]\s*)?(?:€|euros?\b|EUR\b)(?:\s*/\s*(?:mes|año))?\)?|€\s*\d[\d.,]*")
UMBRAL_CRITICO = 0.5     # menos de la mitad de su objetivo → crítico
UMBRAL_BIEN = 0.9        # 90 % o más → bien
DIAS_ARRANQUE = 45       # un cliente nuevo no se juzga por resultados hasta 45 días desde el alta (encendido día 10 + 1 mes)
MET_TXT = {"clientes": "clientes nuevos", "citas": "citas", "leads": "leads", "facturacion": "facturación", "otro": "objetivo propio"}
CONF_TXT = {"dicho_por_cliente": "Dicho por el cliente", "apuntado_por_account": "Apuntado por el account", "deducido": "Deducido"}
DEFINICIONES = {
    "objetivo": "Lo que nos propusimos con el cliente: en sus palabras (cita) y como cifra medible (p. ej. «8 clientes nuevos de asesoría al mes»). Un solo sitio: fuentes_verdad/objetivos_clientes.json; si su account carga después citas, leads o clientes al mes en la ficha, manda lo cargado.",
    "confianza": "dicho_por_cliente (cita literal con fecha, acuerdo firmado o lo que mandó el cliente) · apuntado_por_account (lo escribió el equipo) · deducido (inferido de sus documentos: hay que confirmarlo con el cliente).",
    "resultado": "Último mes cerrado (septiembre) de la métrica del objetivo: leads de Meta (Captación) o de GoHighLevel en 30 días; citas agendadas en GoHighLevel; clientes = oportunidades marcadas como cerradas en el embudo de 90 días ÷ 3 (a medias: depende de que el despacho las marque).",
    "semaforo_estrategico": "Crítico: menos del 50 % de su objetivo, o 0 resultados en 30 días, o el cliente ha dicho que la estrategia no funciona · Vigilar: 50-89 %, sin objetivo del cliente o con objetivo que la app no mide · Bien: 90 % o más, o cliente nuevo en arranque dentro de plazo. NO mira plazos, correos, reuniones ni llamadas (eso es de Operaciones).",
    "taller": "Taller de la oferta de cada cliente nuevo: límite = alta + 2 días (regla de Clientes nuevos, hito «Taller de oferta»). Tarde = pasado el límite sin hacerlo.",
    "renovacion": "Fin de permanencia conocido (acuerdo o ficha) en los próximos 90 días. Riesgo = su semáforo estratégico.",
}


def leer(p, defecto=None):
    try:
        return json.loads(Path(p).read_text())
    except Exception:
        return defecto


def limpio(t):
    return RE_IMPORTE.sub("", str(t or "")).replace("  ", " ").strip() or None


def n(x):
    try:
        v = float(x)
        return v if v == v else None
    except (TypeError, ValueError):
        return None


def ent(x):
    return f"{x:.0f}" if x is None or abs(x - round(x)) < 0.05 else f"{x:.1f}".replace(".", ",")


MESES_INFORME = ["2026-06", "2026-07", "2026-08", "2026-09"]
MES_TXT = {"06": "jun", "07": "jul", "08": "ago", "09": "sep", "10": "oct"}


def historial(cid):
    """Leads de Meta (o de GoHighLevel) y citas por mes cerrado desde los informes mensuales (data/informe/c_AAAA-MM)."""
    out = []
    for m in MESES_INFORME:
        f = (leer(DATA / "informe" / f"c_{m}" / f"{cid}.json", {}) or {}).get("filas") or [{}]
        f = f[0] or {}
        me = ((f.get("meta") or {}).get("actual") or {})
        e = f.get("embudo") or {}
        leads = n(me.get("leads"))
        if leads is None:
            leads = n(e.get("leads_ghl"))
        out.append({"mes": m, "leads": leads, "citas": n((e.get("citas") or {}).get("agendadas")), "clientes": n(e.get("ganadas_total"))})
    return out


def mensual(cifra, periodo):
    if cifra is None:
        return None
    return cifra / 3 if periodo == "trimestre" else cifra / 12 if periodo == "anio" else cifra


def resultado(metrica, cifra, periodo, k, s):
    """Lo conseguido en el último mes cerrado para esa métrica. k = captación del cliente; s = su subcuenta de CRM."""
    k, s = k or {}, s or {}
    cap_leads = (k.get("leads") or {}) if isinstance(k.get("leads"), dict) else {}
    cit_k = ((k.get("ghl") or {}).get("citas") or {})
    serie = k.get("serie") or []
    out = {"valor": None, "texto": None, "fuente": None, "href": None, "medible": "hoy", "tendencia": None, "tendencia_txt": None}
    if metrica in ("facturacion", "otro"):
        prox = resultado("leads", None, None, k, s)
        out.update(medible="no", proxy={"valor": prox["valor"], "texto": prox["texto"], "fuente": prox["fuente"]},
                   tendencia=prox["tendencia"], tendencia_txt=prox["tendencia_txt"])
        return out
    if metrica == "leads" or metrica is None:
        if cap_leads.get("mes_anterior") is not None:
            out.update(valor=n(cap_leads.get("mes_anterior")), texto="leads de Meta en septiembre", fuente="Captación (Meta)", href=f"#/captacion/{k.get('cliente_id')}")
        elif s.get("leads_30d") is not None:
            out.update(valor=n(s.get("leads_30d")), texto="leads en GoHighLevel en 30 días", fuente="Salud del CRM (GoHighLevel)", href="#/crm")
        if len(serie) >= 28:
            a = sum(n(x.get("leads_meta")) or 0 for x in serie[-14:])
            b = sum(n(x.get("leads_meta")) or 0 for x in serie[-28:-14])
            out["tendencia"], out["tendencia_txt"] = _tend(a, b, "leads", 14)
    elif metrica == "citas":
        ma = (cit_k.get("mes_anterior") or {}).get("agendadas")
        if ma is not None:
            out.update(valor=n(ma), texto="citas agendadas en septiembre", fuente="Captación (GoHighLevel)", href=f"#/captacion/{k.get('cliente_id')}")
        elif (s.get("citas_30d") or {}).get("agendadas") is not None:
            out.update(valor=n(s["citas_30d"]["agendadas"]), texto="citas agendadas en 30 días", fuente="Salud del CRM (GoHighLevel)", href="#/crm")
        c14, c30 = (s.get("citas_14d") or {}).get("agendadas"), (s.get("citas_30d") or {}).get("agendadas")
        if c14 is not None and c30 is not None:
            out["tendencia"], out["tendencia_txt"] = _tend(c14, (c30 - c14) * 14 / 16, "citas", 14)
    elif metrica == "clientes":
        f = ((s.get("embudo") or {}).get("funnel")) or (((k.get("ghl") or {}).get("embudo") or {}).get("funnel")) or None
        if f and f.get("cerrado") is not None:
            cer = n(f.get("cerrado"))
            if periodo == "total":
                out.update(valor=cer, texto="clientes cerrados marcados en el embudo (90 días)")
            else:
                out.update(valor=round(cer / 3, 1), texto=f"clientes al mes ({ent(cer)} cerrados marcados en 90 días ÷ 3)")
            out.update(fuente="Embudo de GoHighLevel", href="#/crm", medible="medias")
    if out["valor"] is None:
        out["medible"] = "no" if out["medible"] != "medias" else "medias"
    return out


def _tend(a, b, que, dias):
    if a is None or b is None:
        return None, None
    if b == 0 and a == 0:
        return "igual", f"0 {que} en los dos últimos tramos de {dias} días"
    if b == 0:
        return "sube", f"{ent(a)} {que} en {dias} días (antes, 0)"
    r = a / b
    t = "sube" if r >= 1.15 else "baja" if r <= 0.85 else "igual"
    return t, f"{ent(a)} {que} en los últimos {dias} días frente a {ent(b)} en los {dias} anteriores"


def main():
    hoy = date.today()
    verdad = leer(DATA / "verdad" / "clientes.json", {}) or {}
    cap_doc = leer(DATA / "captacion" / "captacion.json", {}) or {}
    crm_doc = leer(DATA / "crm" / "crm.json", {}) or {}
    nuevos_doc = leer(DATA / "nuevos" / "nuevos.json", {}) or {}
    personas = {p["id"]: p for p in leer(DATA / "personas.json", []) or []}
    fuente = leer(FUENTE, {}) or {}
    obj_src = fuente.get("clientes") or {}
    cap = {c["cliente_id"]: c for c in cap_doc.get("clientes") or [] if c.get("cliente_id")}
    crm = {}
    for s in crm_doc.get("subcuentas") or []:
        if s.get("cliente_id") and s.get("tipo") == "cliente" and s["cliente_id"] not in crm:
            crm[s["cliente_id"]] = s
    altas = {a["cliente_id"]: a for a in nuevos_doc.get("altas") or []}
    app_obj = {c["cliente_id"]: c for c in (leer(DATA / "objetivos" / "objetivos.json", {}) or {}).get("clientes") or [] if c.get("cliente_id")}

    # Cerebro de decisiones: diagnóstico por cliente (árbol del embudo) y reglas con su fuente en GitHub.
    try:
        import cerebro_decisiones as CD
        ctx_cd = CD.contexto(verdad, cap_doc, crm_doc)
        diags = ctx_cd.get("diagnosticos") or {}
        reglas = CD.reglas()
    except Exception as e:  # sin cerebro: se sigue con las reglas de aquí
        print("aviso: cerebro de decisiones no disponible:", e)
        diags, reglas, CD = {}, {}, None

    def regla(rid):
        r = reglas.get(rid) or {}
        url = (CD.url_regla(r) if CD and r else None)
        return {"id": rid, "texto": r.get("regla"), "url": url, "autor": r.get("autor")}

    nombre = lambda pid: (personas.get(pid) or {}).get("alias") or pid
    filas = []
    for v in verdad.get("clientes") or []:
        cid = v["cliente_id"]
        acc = v.get("account")
        src = obj_src.get(cid) or {}
        k, s = cap.get(cid), crm.get(cid)
        alta = altas.get(cid)
        dia_alta = v.get("dia_alta") if v.get("dia_alta") is not None else (alta or {}).get("dia")
        en_arranque = bool(v.get("nuevo")) and (dia_alta is None or dia_alta < DIAS_ARRANQUE)

        # objetivo: el del fichero de la verdad; si la app tiene uno cargado con cifra de resultados, manda la cifra de la app
        objetivo = None
        if src.get("objetivo_medible") or src.get("objetivo_cliente"):
            objetivo = {k2: src.get(k2) for k2 in ("objetivo_cliente", "objetivo_medible", "metrica", "cifra", "periodo", "fecha", "confianza", "quien_lo_dijo", "nota")}
            for k2 in ("objetivo_cliente", "objetivo_medible", "nota"):
                objetivo[k2] = limpio(objetivo.get(k2))
            objetivo["fuente"] = src.get("fuente") or {}
            objetivo["otras_fuentes"] = [{**o, "texto": limpio(o.get("texto"))} for o in src.get("otras_fuentes") or []]
            objetivo["origen"] = "fuentes_verdad/objetivos_clientes.json"
        ao = (app_obj.get(cid) or {}).get("objetivo") or {}
        for campo, met in (("ventas_mes", "clientes"), ("citas_mes", "citas"), ("leads_mes", "leads")):
            if n(ao.get(campo)):
                objetivo = {**(objetivo or {}), "metrica": met, "cifra": n(ao[campo]), "periodo": "mes",
                            "objetivo_medible": f"{ent(n(ao[campo]))} {MET_TXT[met]} al mes",
                            "confianza": (objetivo or {}).get("confianza") or "apuntado_por_account",
                            "fecha": (ao.get("cuando") or "")[:10] or (objetivo or {}).get("fecha"),
                            "origen": f"cargado en la app por {nombre(ao.get('quien'))}",
                            "fuente": (objetivo or {}).get("fuente") or {"texto": "Ficha del cliente · objetivo cargado", "href": f"#/ficha/{cid}/resumen"}}
                break

        hist = historial(cid)
        res = resultado((objetivo or {}).get("metrica"), (objetivo or {}).get("cifra"), (objetivo or {}).get("periodo"), k, s) if objetivo else \
            resultado("leads", None, None, k, s)
        if objetivo and res["valor"] is None and (objetivo.get("metrica") in ("leads", "citas")) and hist and hist[-1].get(objetivo["metrica"]) is not None:
            res.update(valor=hist[-1][objetivo["metrica"]], texto=f"{objetivo['metrica']} en septiembre (informe mensual)", fuente="Informe del cliente (septiembre)",
                       href=f"#/informe-cliente/{cid}", medible="hoy")
        obj_mes = mensual(n((objetivo or {}).get("cifra")), (objetivo or {}).get("periodo")) if objetivo and (objetivo or {}).get("periodo") != "total" else n((objetivo or {}).get("cifra"))
        pct = (res["valor"] / obj_mes) if (objetivo and res["valor"] is not None and obj_mes) else None
        met_txt = MET_TXT.get((objetivo or {}).get("metrica"), "resultados")
        _l = [n((s or {}).get("leads_30d")), n(((k or {}).get("leads") or {}).get("mes_anterior")), (hist[-1].get("leads") if hist else None)]
        leads30 = max([x for x in _l if x is not None], default=None)
        citas30 = n(((s or {}).get("citas_30d") or {}).get("agendadas")) if s else None

        # ---- semáforo estratégico (resultados frente al objetivo)
        manual = src.get("semaforo_estrategico") or {}
        met = (objetivo or {}).get("metrica")
        serie = [x.get(met if met in ("leads", "citas", "clientes") else "leads") for x in hist]
        meses_bajo = 0
        if objetivo and obj_mes and met in ("leads", "citas", "clientes") and (objetivo.get("periodo") != "total"):
            for x in reversed(serie):
                if x is not None and x < obj_mes * UMBRAL_CRITICO:
                    meses_bajo += 1
                else:
                    break
        if en_arranque:
            enc = (v.get("encendido") or {}).get("estado")
            if enc == "sin_encender_fuera_de_plazo":
                sem, mot = "vigilar", f"Día {dia_alta} sin encender: su objetivo aún no empieza a contar"
            else:
                sem, mot = "bien", f"En arranque (día {dia_alta if dia_alta is not None else '—'}): el objetivo se juzga desde el día {DIAS_ARRANQUE}"
            if not objetivo:
                mot += ". Sin objetivo del cliente: pactarlo en el taller"
        elif not objetivo:
            if (leads30 == 0 or leads30 is None) and (citas30 in (0, None)) and (k or s):
                sem, mot = "critico", "Sin objetivo del cliente y 0 leads y 0 citas en 30 días"
            else:
                sem, mot = "vigilar", "Sin objetivo del cliente: no se puede saber si avanza"
        elif pct is None:
            ul = src.get("ultima_lectura") or {}
            sem, mot = "vigilar", "La app no mide hoy su objetivo" + (f"; última lectura apuntada: {limpio(ul.get('texto'))} ({ul.get('fecha')})" if ul.get("texto") and limpio(ul.get("texto")) else "")
        elif (objetivo.get("periodo") == "total"):
            if pct >= 1:
                sem, mot = "bien", f"Objetivo cumplido: {ent(res['valor'])} de {ent(obj_mes)} {met_txt}"
            elif met == "clientes" and (citas30 or 0) >= 3:
                sem, mot = "vigilar", f"{ent(res['valor'])} de {ent(obj_mes)} {met_txt} marcados, con {ent(citas30)} citas en 30 días"
            else:
                sem, mot = "critico", f"{ent(res['valor'])} de {ent(obj_mes)} {met_txt} marcados en 90 días y {ent(citas30 or 0)} citas en 30 días"
        elif res["valor"] == 0 and met == "clientes" and (citas30 or 0) >= 3:
            sem, mot = "vigilar", f"{ent(citas30)} citas en 30 días y ningún cierre marcado en GoHighLevel frente a {ent(obj_mes)} clientes al mes: confirmar cierres con el despacho"
        elif res["valor"] == 0:
            sem, mot = "critico", (f"0 leads y 0 citas en 30 días frente a {ent(obj_mes)} {met_txt} al mes" if not leads30 and not citas30
                                   else f"0 clientes marcados frente a {ent(obj_mes)} al mes, con {ent(leads30 or 0)} leads y {ent(citas30 or 0)} citas en 30 días" if met == "clientes"
                                   else f"0 {met_txt} en el último mes frente a {ent(obj_mes)} de objetivo")
        elif pct < UMBRAL_CRITICO:
            sem, mot = "critico", (f"Lleva {meses_bajo} meses por debajo de la mitad de su objetivo de {met_txt}; en septiembre, {ent(res['valor'])} de {ent(obj_mes)} ({pct * 100:.0f} %)"
                                   if meses_bajo >= 2 else f"Al {pct * 100:.0f} % de su objetivo de {met_txt} ({ent(res['valor'])} de {ent(obj_mes)} al mes)")
        elif pct < UMBRAL_BIEN:
            sem, mot = "vigilar", f"Al {pct * 100:.0f} % de su objetivo de {met_txt} ({ent(res['valor'])} de {ent(obj_mes)} al mes)"
        else:
            sem, mot = "bien", f"Al {pct * 100:.0f} % de su objetivo de {met_txt}"
        if manual.get("semaforo") == "critico" and sem != "critico" and not en_arranque:
            sem, mot = "critico", limpio(manual.get("motivo")) or mot
        elif manual.get("motivo") and sem == "critico" and res["valor"] is None:
            mot = limpio(manual.get("motivo")) or mot
        if res["tendencia"] == "baja" and sem == "vigilar":
            mot += " y bajando"

        # ---- recomendación del cerebro para los críticos
        rec = None
        if sem == "critico":
            d = diags.get(cid)
            if d and d.get("sintoma") != "relacion_en_riesgo":
                c = d["causa"]
                rg = regla(c.get("regla"))
                rec = {"que": limpio(c.get("accion")) or "Revisa el embudo con su account", "porque": limpio(f"{d['titulo']}: {d['texto']}. Causa probable: {c['evidencia']['dato']}"),
                       "regla": rg, "fuente": {"texto": limpio(c["evidencia"].get("fuente")) or "Diagnóstico del embudo", "href": c["evidencia"].get("url")},
                       "quien": "su " + {"trafficker": "trafficker", "crm": "especialista de GoHighLevel"}.get(c.get("silla"), "account"), "origen": "cerebro de decisiones (diagnóstico)"}
            elif not objetivo:
                rg = regla("criterio_d0")
                rec = {"que": f"Pide a {nombre(acc) if acc else 'su account'} que pacte con el cliente el número por el que nos juzga (una métrica, una cifra y una fecha) esta semana",
                       "porque": "Sin objetivo no hay forma de saber si la estrategia avanza ni de defender la renovación.", "regla": rg, "quien": nombre(acc) if acc else "dirección", "origen": "regla del cerebro"}
            elif objetivo.get("metrica") == "clientes" and (citas30 or 0) >= 3:
                rg = regla("cierre_bajo_no_es_trafico")
                rec = {"que": "Revisa la oferta y la venta del despacho con su account antes de tocar campañas o presupuesto",
                       "porque": f"Tiene {ent(citas30)} citas en 30 días y no llega a su objetivo de clientes: el tráfico ya hace su trabajo.", "regla": rg, "quien": "Coti con su account", "origen": "regla del cerebro"}
            elif (leads30 or 0) >= 5 and (citas30 or 0) == 0:
                rg = regla("contacta_no_agenda")
                rec = {"que": "Revisa con CRM por qué los leads no pasan a cita (velocidad, guion, pedir la cita con motivo)",
                       "porque": f"{ent(leads30)} leads en 30 días y 0 citas.", "regla": rg, "quien": "jefa de CRM y su account", "origen": "regla del cerebro"}
            else:
                rg = regla("auditar_trasera_antes_anuncios") if reglas.get("auditar_trasera_antes_anuncios") else regla("criterio_d0")
                rec = {"que": "Repasa la estrategia con su account y su trafficker: oferta, ángulo y público frente al objetivo pactado",
                       "porque": mot + ".", "regla": rg, "quien": "Coti con su account", "origen": "regla del cerebro"}
            if src.get("recomendacion"):
                rec = {**(rec or {}), **src["recomendacion"], "origen": "fuente del cliente"}

        sin_obj = None
        if not objetivo:
            sin_obj = {"quien_pide": acc, "quien_pide_nombre": nombre(acc) if acc else "dirección (sin account)",
                       "aviso": f"Sin objetivo del cliente. Lo pide {nombre(acc) if acc else 'dirección (no tiene account)'}; aviso a Coti."}
        filas.append({
            "cliente_id": cid, "nombre": v.get("nombre"), "account": acc, "account_nombre": nombre(acc) if acc else None,
            "nuevo": bool(v.get("nuevo")), "alta": v.get("alta"), "dia_alta": dia_alta, "en_arranque": en_arranque,
            "objetivo": objetivo, "sin_objetivo": sin_obj,
            "resultado": {**res, "objetivo_mes": obj_mes, "serie": serie, "serie_meses": [MES_TXT[x["mes"][5:]] for x in hist], "meses_bajo": meses_bajo, "pct": round(pct * 100) if pct is not None else None,
                          "ultima_lectura": ({**src["ultima_lectura"], "texto": limpio(src["ultima_lectura"].get("texto")),
                                              "valor": None if RE_IMPORTE.search(str(src["ultima_lectura"].get("texto") or "")) else src["ultima_lectura"].get("valor")}
                                             if src.get("ultima_lectura") else None)},
            "semaforo": sem, "motivo": limpio(mot), "motivo_fuente": limpio(src.get("motivo_estrategico")),
            "recomendacion": rec,
            "renovacion": src.get("renovacion"),
        })

    orden = {"critico": 0, "vigilar": 1, "bien": 2}
    filas.sort(key=lambda f: (orden.get(f["semaforo"], 3), f["resultado"]["pct"] if f["resultado"]["pct"] is not None else 999, f["nombre"] or ""))

    # ---- talleres de la oferta (Clientes nuevos)
    talleres = []
    for a in (nuevos_doc.get("altas") or []):
        t = next((x for x in a.get("hitos") or [] if x.get("id") == "arranque"), None)
        if not t:
            continue
        lim = t.get("objetivo")
        est = t.get("estado")
        fecha_t = t.get("fecha")
        hoy_s = hoy.isoformat()
        if est == "hecho":
            estado = "hecho"
            retraso = max(0, (date.fromisoformat(fecha_t[:10]) - date.fromisoformat(lim)).days) if fecha_t and lim else 0
        elif fecha_t and fecha_t[:10] >= hoy_s:
            estado = "agendado"
            retraso = max(0, (date.fromisoformat(fecha_t[:10]) - date.fromisoformat(lim)).days) if lim else 0
        elif fecha_t:
            estado = "por_confirmar"
            retraso = max(0, (date.fromisoformat(fecha_t[:10]) - date.fromisoformat(lim)).days) if lim else 0
        else:
            estado = "sin_agendar"
            retraso = max(0, (hoy - date.fromisoformat(lim)).days) if lim else 0
        tc = (obj_src.get(a["cliente_id"]) or {}).get("taller_confirmado")
        if estado == "por_confirmar" and tc and tc.get("estado") == "hecho":
            estado, fecha_t = "hecho", tc.get("fecha") or fecha_t
            retraso = max(0, (date.fromisoformat(fecha_t[:10]) - date.fromisoformat(lim)).days) if lim else 0
        tarde = estado != "hecho" and lim is not None and (hoy_s > lim or (fecha_t or "")[:10] > lim)
        if estado == "por_confirmar" and not tarde:
            tarde = False
        talleres.append({"cliente_id": a["cliente_id"], "nombre": a.get("nombre"), "firma": (a.get("firma") or "")[:10] or None, "alta": a.get("alta"),
                         "limite": lim, "fecha_taller": (fecha_t or "")[:16] or None, "estado": estado, "tarde": bool(tarde),
                         "hecho_tarde": estado == "hecho" and retraso > 0, "dias_retraso": retraso,
                         "quien": t.get("quien"), "account": (a.get("account") or {}).get("id"), "account_nombre": (a.get("account") or {}).get("nombre"),
                         "prueba": limpio(t.get("prueba")), "fuente": t.get("fuente"),
                         "objetivo_pactado": bool((obj_src.get(a["cliente_id"]) or {}).get("objetivo_medible")),
                         "nota": (obj_src.get(a["cliente_id"]) or {}).get("taller_nota")})
    talleres.sort(key=lambda x: (0 if x["tarde"] else 1 if x["estado"] != "hecho" else 2, -x["dias_retraso"], x["limite"] or ""))
    for pv in nuevos_doc.get("previstas") or []:
        talleres.append({"cliente_id": None, "nombre": pv.get("nombre"), "firma": None, "alta": pv.get("alta_prevista"), "limite": None,
                         "fecha_taller": None, "estado": "prevista", "tarde": False, "hecho_tarde": False, "dias_retraso": 0, "quien": "Tomás y Coti",
                         "account": None, "account_nombre": None, "prueba": f"Contrato enviado, sin firmar ({pv.get('estado_sign') or 'Zoho Sign'})", "fuente": "Zoho Sign", "objetivo_pactado": False})

    # ---- renovaciones (solo con fecha conocida)
    renov = []
    for f in filas:
        r = f.get("renovacion") or {}
        fin = r.get("fin")
        if fin:
            dias = (date.fromisoformat(fin) - hoy).days
            if -15 <= dias <= 90:
                renov.append({"cliente_id": f["cliente_id"], "nombre": f["nombre"], "fin": fin, "dias": dias, "riesgo": f["semaforo"],
                              "motivo": f["motivo"], "texto": r.get("texto"), "fuente": r.get("fuente")})
    renov.sort(key=lambda x: x["dias"])

    cuenta = lambda s_: sum(1 for f in filas if f["semaforo"] == s_)
    sin = [f for f in filas if not f["objetivo"]]
    por_account = {}
    for f in sin:
        por_account.setdefault(f["account_nombre"] or "Sin account", []).append(f["nombre"])
    doc = {
        "formato": 1, "generado": datetime.now().strftime("%Y-%m-%d %H:%M"), "hoy": hoy.isoformat(),
        "fuente_objetivos": "fuentes_verdad/objetivos_clientes.json", "fuente_objetivos_fecha": (fuente.get("_meta") or {}).get("fecha"),
        "definiciones": DEFINICIONES,
        "resumen": {"clientes": len(filas), "con_objetivo": len(filas) - len(sin), "sin_objetivo": len(sin),
                    "con_cifra": sum(1 for f in filas if (f["objetivo"] or {}).get("cifra")),
                    "por_confianza": {c: sum(1 for f in filas if (f["objetivo"] or {}).get("confianza") == c) for c in CONF_TXT},
                    "critico": cuenta("critico"), "vigilar": cuenta("vigilar"), "bien": cuenta("bien"),
                    "talleres": sum(1 for t in talleres if t["cliente_id"]), "talleres_tarde": sum(1 for t in talleres if t["tarde"]),
                    "talleres_hechos_tarde": sum(1 for t in talleres if t["hecho_tarde"]),
                    "renovaciones_90d": len(renov), "renovaciones_riesgo": sum(1 for r in renov if r["riesgo"] != "bien"),
                    "sin_objetivo_por_account": por_account},
        "clientes": filas, "talleres": talleres, "renovaciones": renov,
        "datos": {"captacion": cap_doc.get("datos_hasta"), "crm": crm_doc.get("generado"), "nuevos": nuevos_doc.get("generado"), "verdad": verdad.get("generado")},
    }
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    SALIDA.write_text(json.dumps(doc, ensure_ascii=False, indent=1))
    r = doc["resumen"]
    print(f"objetivos_clientes: {r['clientes']} clientes · {r['con_objetivo']} con objetivo ({r['con_cifra']} con cifra) · {r['sin_objetivo']} sin objetivo · "
          f"crítico {r['critico']} · vigilar {r['vigilar']} · bien {r['bien']} · talleres tarde {r['talleres_tarde']} de {r['talleres']}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""fuentes_ia/cerebro_respuestas/analizar.py · patrones de las respuestas reales de RO · 3-oct-2026.

Lee data/ia/_privado/minado_desk.json (minar_desk.py) y saca, por tipo de correo del cliente (cerebro.clasificar):
longitud real de nuestra respuesta (mediana y cuartiles), saludo, cierre, si da fecha o plazo, si numera, si se
disculpa, y cuáles «funcionan» (el cliente contesta con un agradecimiento o un «perfecto» y no vuelve a quejarse).

  python3 fuentes_ia/cerebro_respuestas/analizar.py            → patrones.json (agregado, sin nombres de clientes)
  python3 fuentes_ia/cerebro_respuestas/analizar.py --ejemplos → además candidatos_ejemplos.json en _privado (para
                                                                  elegir a mano y anonimizar los de ejemplos.json)
"""
import json
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

AQUI = Path(__file__).resolve().parent
APP = AQUI.parent.parent
sys.path.insert(0, str(AQUI))
import cerebro as C  # noqa: E402

MINADO = APP / "data/ia/_privado/minado_desk.json"
RE_SALUDO = re.compile(r"(?i)^\s*(hola|buenos d[ií]as|buenas tardes|buenas noches|buenas|bon dia|bona tarda|estimad[oa]|hello|hi)\b[^\n,]{0,40}[,!.]?")
RE_CIERRE = re.compile(r"(?i)\b(un abrazo|un saludo|saludos cordiales|saludos|gracias!?|muchas gracias|una abra[çc]ada|quedo atent[oa]|quedamos atent[oa]s|"
                       r"quedo a (?:tu|vuestra) disposici[oó]n|que tengas buen d[ií]a|buen fin de semana|feliz d[ií]a)\b")
RE_PLAZO = re.compile(r"(?i)\b(hoy|mañana|esta (?:tarde|semana)|la semana que viene|pr[oó]xima semana|lunes|martes|mi[eé]rcoles|jueves|viernes|"
                      r"\d{1,2} de (?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)|\d{1,2}[/-]\d{1,2}|antes del?|en \d+ d[ií]as|horas)\b")
RE_DISCULPA = re.compile(r"(?i)\b(disculpa|disculpad|perd[oó]n|perdona|lamento|lamentamos|sentimos)\b")
RE_LISTA = re.compile(r"(?m)^\s*(?:\d+[.)]|[-•])\s+")
RE_POSITIVO = re.compile(r"(?i)^\W*(?:ok|vale|perfecto|genial|fenomenal|estupendo|gracias|muchas gracias|much[ií]simas gracias|mil gracias|fet|de acuerdo|recibido|entendido|que maravilla|great|thanks)")


def cuerpo_respuesta(t):
    """Nuestra respuesta sin cita ni aviso legal, cortada en el cierre (la firma de Desk va detrás)."""
    t = C.RE_LEGAL.sub("", t or "")
    t = C.RE_CITA.sub("", t)
    m = RE_CIERRE.search(t[20:])
    cierre = m.group(1) if m else None
    if m:
        t = t[: 20 + m.start()]
    return t.strip(), cierre


def palabras(t):
    sin_saludo = RE_SALUDO.sub("", t, count=1)
    return len(re.findall(r"\w+", sin_saludo))


def q(xs, p):
    if not xs:
        return None
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(round(p * (len(xs) - 1))))]


def pares(tickets):
    """(ticket, hilo hasta el cliente, nuestra respuesta, lo que contesta el cliente después)."""
    for t in tickets:
        ms = t["mensajes"]
        for i, m in enumerate(ms):
            if not C.es_nuestro(m) or i == 0 or C.es_nuestro(ms[i - 1]):
                continue
            despues = next((x for x in ms[i + 1:] if not C.es_nuestro(x)), None)
            yield t, ms[:i], m, despues


def main():
    d = json.loads(MINADO.read_text())
    por_tipo = defaultdict(list)
    por_agente = defaultdict(list)
    for t, previo, resp, despues in pares(d["tickets"]):
        cl = C.clasificar(t.get("asunto"), previo, {})
        tipo = cl["tipo"]
        if tipo in ("automatico", "seguimiento"):
            continue
        cuerpo, cierre = cuerpo_respuesta(resp.get("texto"))
        if len(cuerpo) < 5:
            continue
        sal = RE_SALUDO.match(cuerpo)
        desp_util = C.texto_util(despues.get("texto")) if despues else ""
        funciona = bool(despues) and bool(RE_POSITIVO.search(desp_util)) and not re.search(C.GUIAS["queja"]["senales"].replace("|urgente", ""), C._sin_tildes(desp_util))
        fila = {"ticket": t["numero"], "agente": resp.get("de"), "palabras": palabras(cuerpo),
                "saludo": (sal.group(1).lower() if sal else None), "cierre": (cierre or "").lower() or None,
                "plazo": bool(RE_PLAZO.search(cuerpo)), "disculpa": bool(RE_DISCULPA.search(cuerpo)), "lista": bool(RE_LISTA.search(cuerpo)),
                "nombre_en_saludo": bool(sal and re.match(r"(?i)\s*(hola|buenos d[ií]as|buenas tardes|buenas)\s+[A-ZÁÉÍÓÚÑ]", cuerpo)),
                "funciona": funciona, "cliente_respondio": bool(despues), "preguntas": len(C.preguntas(previo)),
                "cliente": C.texto_util(previo[-1].get("texto"))[:900], "respuesta": cuerpo[:1800]}
        por_tipo[tipo].append(fila)
        por_agente[resp.get("de") or "?"].append(fila)

    def resumen(xs):
        ws = [x["palabras"] for x in xs]
        bien = [x["palabras"] for x in xs if x["funciona"]]
        n = len(xs)
        return {"n": n,
                "palabras": {"p25": q(ws, .25), "mediana": q(ws, .5), "p75": q(ws, .75)},
                "palabras_cuando_funciona": {"n": len(bien), "p25": q(bien, .25), "mediana": q(bien, .5), "p75": q(bien, .75)},
                "pct_funciona": round(100 * sum(x["funciona"] for x in xs) / n) if n else None,
                "pct_con_plazo": round(100 * sum(x["plazo"] for x in xs) / n) if n else None,
                "pct_disculpa": round(100 * sum(x["disculpa"] for x in xs) / n) if n else None,
                "pct_lista_numerada": round(100 * sum(x["lista"] for x in xs) / n) if n else None,
                "pct_nombre_en_saludo": round(100 * sum(x["nombre_en_saludo"] for x in xs) / n) if n else None,
                "saludos": Counter(x["saludo"] for x in xs if x["saludo"]).most_common(4),
                "cierres": Counter(x["cierre"] for x in xs if x["cierre"]).most_common(5),
                "preguntas_media_del_cliente": round(statistics.mean([x["preguntas"] for x in xs]), 1) if xs else None}

    todos = [x for xs in por_tipo.values() for x in xs]
    # «cortas» frente a «largas» en lo que funciona: ¿responder corto hace que el cliente vuelva a preguntar?
    cortas = [x for x in todos if x["palabras"] < 40 and x["cliente_respondio"]]
    largas = [x for x in todos if x["palabras"] >= 80 and x["cliente_respondio"]]
    sal = {"generado": d["generado"], "fuente": d["fuente"], "tickets": len(d["tickets"]), "respuestas": len(todos),
           "total": resumen(todos),
           "por_tipo": {t: resumen(xs) for t, xs in sorted(por_tipo.items(), key=lambda kv: -len(kv[1]))},
           "cortas_vs_largas": {
               "menos_de_40_palabras": {"n": len(cortas), "pct_cliente_agradece": round(100 * sum(x["funciona"] for x in cortas) / max(1, len(cortas))),
                                        "pct_cliente_vuelve_a_preguntar": round(100 * sum("?" in x.get("cliente", "") for x in cortas) / max(1, len(cortas)))},
               "80_o_mas_palabras": {"n": len(largas), "pct_cliente_agradece": round(100 * sum(x["funciona"] for x in largas) / max(1, len(largas)))}},
           "por_agente": {a: {"n": len(xs), "mediana_palabras": q([x["palabras"] for x in xs], .5),
                              "pct_funciona": round(100 * sum(x["funciona"] for x in xs) / len(xs)), "pct_con_plazo": round(100 * sum(x["plazo"] for x in xs) / len(xs))}
                          for a, xs in sorted(por_agente.items(), key=lambda kv: -len(kv[1])) if len(xs) >= 8}}
    (AQUI / "patrones.json").write_text(json.dumps(sal, ensure_ascii=False, indent=1))
    print(json.dumps({k: sal[k] for k in ("tickets", "respuestas", "total", "cortas_vs_largas")}, ensure_ascii=False, indent=1))
    for t, r in sal["por_tipo"].items():
        print(t, r["n"], r["palabras"], "funciona", r["pct_funciona"], "% · cuando funciona", r["palabras_cuando_funciona"], "plazo", r["pct_con_plazo"])
    print(json.dumps(sal["por_agente"], ensure_ascii=False))
    if "--ejemplos" in sys.argv:
        cand = {t: sorted([x for x in xs if x["funciona"]], key=lambda x: -x["palabras"])[:12] for t, xs in por_tipo.items()}
        (APP / "data/ia/_privado/candidatos_ejemplos.json").write_text(json.dumps(cand, ensure_ascii=False, indent=1))
        print("candidatos →", APP / "data/ia/_privado/candidatos_ejemplos.json")


if __name__ == "__main__":
    main()

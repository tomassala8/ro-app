#!/usr/bin/env python3
"""M21 Decisiones y rastro · genera (solo lectura de fuentes; nada se escribe fuera de data/decisiones/):

  data/decisiones/firmadas.json   las 101 decisiones firmadas el 2-oct (11_DECISIONES_PARA_TOMAS.md), consultables por todos
  data/decisiones/reloj.json      decisiones con reloj: 48 h para Tomás, 24 h para Coti. Filas con persona_id (quien la sube)
                                  → servir.py solo las manda a esa persona, su jefe, operaciones, RRHH y dirección;
                                  las de un cliente llevan cliente_id → solo a quien ve ese cliente.
  data/decisiones/direccion.json  informe semanal para Tomás (exigencia 48 de Mili) y cierre de mes de Operaciones
                                  (exigencia 49). Solo Tomás y Mili (datos_de_modulo → «indicadores», que solo ven ellos).

De dónde salen las decisiones con reloj (en este orden, sin duplicar por «clave»):
  1. local.db · tabla `decisiones` (tipo distinto de «para_confirmar»): las que escala M14 Incidencias u otro módulo.
     Columnas: quien, tipo (para_tomas | para_coti | escalada), clave, problema, recomendacion, respuesta (JSON),
     respondida, respondida_por, anula_a. Una fila con anula_a anula otra (nada se borra).
  2. local.db · tabla `acciones`: «decision_nueva» y «decidir» (botones de este módulo, simulados) y cualquier
     «escalar*» cuya vista previa diga para quién (tomas / coti).
  3. Reglas de escalado de la ficha de Mili (G1) sobre los datos de hoy: alta que pasa del día 12, cliente nuevo sin
     account, cliente que pide hablar con Tomás. Se marcan «detectada por la app» y las sube Mili.
"""
import json, re, sqlite3, sys
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "fuentes_personas"))
from comun import APP, BUILD, DATA, emparejador, escribir, personas  # noqa: E402

RAIZ = APP.parent
HOY = date.today()
AHORA = datetime.now()
sys.path.insert(1, str(Path(__file__).resolve().parents[1]))  # C5: rutas y secretos en config.py
import config  # noqa: E402
LIBRO = config.LIBRO_CLIENTES
RELOJ_H = {"para_tomas": 48, "para_coti": 24, "escalada": 48}


# ------------------------------------------------------------------ 101 firmadas
def firmadas():
    md = (RAIZ / "11_DECISIONES_PARA_TOMAS.md").read_text()
    tema, cab, out = None, None, []
    for linea in md.splitlines():
        if linea.startswith("## 1 "):
            tema = "Las 10 que más desbloquean"
        elif linea.startswith("### "):
            tema = linea[4:].strip()
        elif linea.startswith("## ✅ Ya resueltas"):
            tema = "Ya resueltas en la conversación"
        if not linea.startswith("|"):
            cab = None if not linea.strip() else cab
            continue
        celdas = [c.strip() for c in linea.strip().strip("|").split("|")]
        if celdas[0] == "ID":
            cab = [c.lower() for c in celdas]
            continue
        if not cab or set(celdas[0]) <= set("-: "):
            continue
        m = re.match(r"\**(D-\d+)", celdas[0])
        if not m:
            continue
        fila = dict(zip(cab, celdas))
        limpio = lambda s: re.sub(r"\*\*|`", "", s or "").strip()
        out.append({
            "id": m.group(1), "num": int(m.group(1)[2:]), "tema": tema,
            "que": limpio(fila.get("qué hay que decidir") or fila.get("qué queda resuelto")),
            "contexto": limpio(fila.get("cifras en conflicto (fuente y fecha)") or fila.get("por qué bloquea")),
            "decision": limpio(fila.get("recomendación") or fila.get("recomendación (una línea)") or fila.get("qué queda resuelto")),
            "respuesta": limpio(fila.get("tu respuesta")) or "Aceptada (2-oct)",
            "afecta": limpio(fila.get("afecta a")),
        })
    vistos, unicas = set(), []
    for d in out:
        if d["id"] not in vistos:
            vistos.add(d["id"]); unicas.append(d)
    unicas.sort(key=lambda d: d["num"])
    return {"_meta": {"fuente": "11_DECISIONES_PARA_TOMAS.md", "firmadas": "2-oct-2026 · «Acepto» de Tomás a todas las recomendaciones",
                      "total": len(unicas), "generado": AHORA.strftime("%Y-%m-%d %H:%M")},
            "decisiones": unicas}


# ------------------------------------------------------------------ reloj
def leer_db():
    db = APP / "local.db"
    if not db.exists():
        return [], []
    con = sqlite3.connect(db); con.row_factory = sqlite3.Row
    dec = [dict(r) for r in con.execute("SELECT * FROM decisiones WHERE tipo <> 'para_confirmar' ORDER BY id")]
    acc = [dict(r) for r in con.execute("SELECT * FROM acciones WHERE tipo IN ('decision_nueva','decidir') OR tipo LIKE 'escalar%' ORDER BY id")]
    con.close()
    return dec, acc


def jl(s):
    try:
        v = json.loads(s) if isinstance(s, str) else s
        return json.loads(v) if isinstance(v, str) and v.strip().startswith("{") else v
    except Exception:
        return None


def ts(s):
    """Hora en UTC (sin zona). Acepta «…Z» y la hora de SQLite (que ya es UTC)."""
    s = (s or "").replace("T", " ").replace("Z", "")[:19]
    try:
        return datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return datetime.strptime(s[:10], "%Y-%m-%d")


def reloj(clientes_app):
    dec, acc = leer_db()
    filas = {}

    # 1 · tabla decisiones (M14 y otros)
    anuladas = {d["anula_a"] for d in dec if d.get("anula_a")}
    for d in dec:
        if d["id"] in anuladas or d.get("anula_a"):
            continue
        resp = jl(d.get("respuesta")) or {}
        datos = resp if isinstance(resp, dict) else {}
        tipo = d["tipo"] if d["tipo"] in RELOJ_H else "para_tomas"
        clave = d.get("clave") or f"db-{d['id']}"
        filas[clave] = {
            "id": f"db-{d['id']}", "clave": clave, "tipo": tipo, "persona_id": d["quien"], "quien": d["quien"],
            "titulo": datos.get("titulo") or (d.get("problema") or "")[:90], "problema": d.get("problema"),
            "recomendacion": d.get("recomendacion"), "opciones": datos.get("opciones"),
            "cliente_id": datos.get("cliente_id"), "origen": datos.get("origen") or "local.db · tabla decisiones (M14 u otro módulo)",
            "creada": d["creada"], "respuesta": datos.get("respuesta") if d.get("respondida") else None,
            "respondida": d.get("respondida"), "respondida_por": d.get("respondida_por"), "prueba": datos.get("prueba"),
        }

    # 2 · acciones simuladas: nuevas y respuestas
    respuestas = []
    for a in acc:
        vp = jl(a.get("vista_previa")) or {}
        if not isinstance(vp, dict):
            vp = {"texto": vp}
        if a["tipo"] == "decidir":
            respuestas.append((a, vp)); continue
        para = (vp.get("para") or "").lower()
        if a["tipo"].startswith("escalar") and para not in ("tomas", "coti") and not re.search(r"Tom[aá]s|Coti", a.get("texto") or ""):
            continue
        tipo = "para_coti" if para == "coti" or a["tipo"] == "escalar_coti" else "para_tomas"
        clave = vp.get("clave") or f"acc-{a['id']}"
        if clave in filas:
            continue
        filas[clave] = {
            "id": f"acc-{a['id']}", "clave": clave, "tipo": tipo, "persona_id": a["quien"], "quien": a["quien"],
            "titulo": vp.get("titulo") or (a.get("texto") or "")[:90], "problema": vp.get("problema") or a.get("texto"),
            "recomendacion": vp.get("recomendacion"), "opciones": vp.get("opciones"), "cliente_id": a.get("cliente_id"),
            "origen": f"Botón en la app ({a.get('modulo')}) · simulado", "creada": a["creada"], "fecha_limite": vp.get("fecha"),
            "respuesta": None, "respondida": None, "respondida_por": None, "prueba": None, "simulada": True,
        }

    # 3 · reglas de escalado de la ficha de Mili (G1) sobre los datos de hoy
    for f in reglas(clientes_app):
        filas.setdefault(f["clave"], f)

    # respuestas (botón «Decidir» simulado)
    for a, vp in respuestas:
        f = next((x for x in filas.values() if x["id"] == vp.get("decision_id") or x["clave"] == vp.get("decision_id")), None)
        if f:
            f.update({"respuesta": {"decision": vp.get("decision"), "motivo": vp.get("motivo"), "delegada_en": vp.get("delegada_en")},
                      "respondida": a["creada"], "respondida_por": a["quien"], "simulada": True})

    out = []
    for f in filas.values():
        # Quién la recibe: servir.py manda cada fila a su persona_id (y a su jefe, operaciones y dirección). Las de Coti,
        # a Coti; las que nombran clientes llevan cliente_id para que RRHH y quien no ve el cliente no las reciban.
        if f["tipo"] == "para_coti":
            f["persona_id"] = "constanza"
        h = RELOJ_H.get(f["tipo"], 48)
        creada = ts(f["creada"])
        vence = creada + timedelta(hours=h)
        fin = ts(f["respondida"]) if f.get("respondida") else datetime.utcnow()
        horas = round((fin - creada).total_seconds() / 3600, 1)
        f["creada"] = creada.strftime("%Y-%m-%dT%H:%M:%SZ")
        if f.get("respondida"):
            f["respondida"] = ts(f["respondida"]).strftime("%Y-%m-%dT%H:%M:%SZ")
        f.update({"reloj_h": h, "vence": vence.strftime("%Y-%m-%dT%H:%M:%SZ"), "horas": horas,
                  "estado": ("contestada a tiempo" if horas <= h else "contestada tarde") if f.get("respondida")
                  else ("caducada" if horas > h else "por caducar" if horas >= h * 0.75 else "en plazo")})
        out.append(f)
    out.sort(key=lambda f: (bool(f.get("respondida")), f["vence"]))
    return {"_meta": {"generado": AHORA.strftime("%Y-%m-%d %H:%M"), "reloj": "48 h para Tomás · 24 h para Coti",
                      "indicador": "Decisiones contestadas en 48 h: 100 % / alguna entre 48 y 96 h / alguna de más de 96 h",
                      "fuentes": ["local.db · decisiones (tipo ≠ para_confirmar)", "local.db · acciones (decision_nueva, decidir, escalar*)",
                                  "reglas de escalado de la ficha de Mili sobre la verdad única de la app"]},
            "decisiones": out}


def verdad():
    """La verdad única por cliente (E0 ronda 5): data/verdad/clientes.json."""
    return {c["cliente_id"]: c for c in json.loads((DATA / "verdad/clientes.json").read_text())["clientes"]}


def alias():
    return {p["id"]: (p.get("alias") or p["nombre"].split()[0]) for p in personas()}


def utc(fecha_madrid):
    """«AAAA-MM-DD HH:MM» de Madrid → ISO en UTC con Z (las filas de local.db ya van en UTC)."""
    from zoneinfo import ZoneInfo
    d = datetime.strptime(fecha_madrid, "%Y-%m-%d %H:%M").replace(tzinfo=ZoneInfo("Europe/Madrid"))
    return d.astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%dT%H:%M:%SZ")


def reglas(clientes_app):
    """Lo que la ficha de Mili dice que sube a Tomás, detectado con la verdad única de hoy (misma regla que Clientes nuevos)."""
    V, A = verdad(), alias()
    out = []
    corte = utc(f"{HOY.isoformat()} 09:16")
    sin_enc = [c for c in V.values() if c.get("nuevo") and (c.get("encendido") or {}).get("estado") == "sin_encender_fuera_de_plazo"]
    tarde = [c for c in V.values() if c.get("nuevo") and (c.get("encendido") or {}).get("estado") == "tarde"]
    if sin_enc or tarde:
        n = len(sin_enc) + len(tarde)
        partes = []
        if sin_enc:
            partes.append("sin encender: " + ", ".join(f"{c['nombre']} (día {c.get('dia_alta')})" for c in sorted(sin_enc, key=lambda c: -(c.get("dia_alta") or 0))))
        if tarde:
            partes.append("encendidas tarde: " + ", ".join(f"{c['nombre']} (el día {c['encendido']['dia']})" for c in tarde))
        out.append({
            "id": "regla-altas-tarde", "clave": f"altas-fuera-de-plazo-{HOY.isoformat()}", "tipo": "para_tomas", "persona_id": "mili", "quien": "mili",
            "titulo": f"{n} altas fuera de plazo: {len(sin_enc)} sin encender y {len(tarde)} encendidas tarde",
            "problema": "Altas que pasaron del día 12 desde el alta del contrato. " + "; ".join(partes) + ". La norma es encender el día 10.",
            "recomendacion": f"Parar nuevas altas hasta encender las {len(sin_enc)} que faltan (techo de arranques del 29-sep) y pedir a Agus fecha de encendido por cliente en 24 h.",
            "opciones": ["Aprobar la recomendación", "Seguir con las altas y poner fecha a cada encendido", "Delegar en Mili con fecha"],
            "cliente_id": (sin_enc or tarde)[0]["cliente_id"], "clientes": [c["cliente_id"] for c in sin_enc + tarde],
            "origen": "Regla de la ficha de Mili: si un alta pasa del día 12, sube a Tomás. Misma lista que Clientes nuevos.",
            "creada": corte, "respuesta": None, "respondida": None, "respondida_por": None,
            "prueba": "#/clientes-nuevos", "detectada": True,
        })
    sin = [c for c in V.values() if c.get("nuevo") and c.get("sin_account")]
    if sin:
        out.append({
            "id": "regla-sin-account", "clave": f"nuevos-sin-account-{HOY.isoformat()}", "tipo": "para_tomas", "persona_id": "mili", "quien": "mili",
            "titulo": f"{len(sin)} cliente nuevo sin account" if len(sin) == 1 else f"{len(sin)} clientes nuevos sin account",
            "problema": "Contrato firmado y sin account asignado: " + ", ".join(c["nombre"] for c in sin) + ".",
            "recomendacion": "Asignar hoy en Ajustes › Asignaciones a accounts con menos de 12 proyectos.",
            "opciones": ["Aprobar la recomendación", "Lo reparto yo", "Delegar en Mili con fecha"],
            "cliente_id": sin[0]["cliente_id"], "clientes": [c["cliente_id"] for c in sin],
            "origen": "Regla de la ficha de Mili: cliente nuevo sin account, a Tomás a las 24 h.",
            "creada": corte, "respuesta": None, "respondida": None, "respondida_por": None,
            "prueba": "#/ajustes/asignaciones", "detectada": True,
        })
    datos = json.loads((BUILD / "datos.json").read_text())
    for f in datos["v7"].get("fuegos", []):
        if re.search(r"Tom[aá]s", f.get("motivo") or ""):
            cid = next((c["id"] for c in clientes_app if c["nombre"] == f["nombre"]), None)
            v = V.get(cid) or {}
            out.append({
                "id": f"regla-fuego-{cid}", "clave": f"fuego-{cid}", "tipo": "para_tomas", "persona_id": "mili", "quien": "mili",
                "titulo": f"{v.get('nombre') or f['nombre']}: el cliente pide hablar contigo",
                "problema": f"{f['motivo']} Account: {A.get(v.get('account'), 'sin account')}.",
                "recomendacion": "Llámale hoy, con el plan escrito del account y visto por Coti. Si un cliente amenaza con irse, se le llama el mismo día.",
                "opciones": ["Aprobar la recomendación", "Que llame Coti y me informe", "Delegar en el account con guion"],
                "cliente_id": cid, "origen": "Regla de la ficha de Dirección: cliente que amenaza con irse, a Tomás el mismo día.",
                "creada": corte, "respuesta": None, "respondida": None, "respondida_por": None,
                "prueba": f"#/en-rojo/{cid}" if cid else None, "detectada": True,
            })
    return out


# ------------------------------------------------------------------ dirección: informe semanal y cierre de mes
def direccion(R, clientes_app):
    datos = json.loads((BUILD / "datos.json").read_text())
    v7 = datos["v7"]
    tres = v7["tres"]
    equipo = json.loads((DATA / "personas_m20/equipo.json").read_text()) if (DATA / "personas_m20/equipo.json").exists() else {"personas": []}
    rojos = [f for f in v7.get("fuegos", [])]
    pend = [d for d in R["decisiones"] if not d.get("respondida")]
    corte = datos.get("generado")
    lunes = HOY - timedelta(days=HOY.weekday())

    alerta = [p for p in equipo["personas"] if p.get("alerta")]
    sobre = [p for p in equipo["personas"] if p.get("sobre_capacidad")]
    informe = {
        "semana": f"{lunes.isoformat()} → {(lunes + timedelta(days=4)).isoformat()}",
        "corte": corte,
        "desbloquear": [{"titulo": d["titulo"], "recomendacion": d["recomendacion"], "vence": d["vence"], "estado": d["estado"], "id": d["id"]} for d in pend[:5]],
        "numeros": [
            altas_num(),
            {"id": "horas_nuevos", "nombre": "Horas por cuenta nueva (media al mes)", "valor": f"{tres['horas_nuevos']['media']} h",
             "estado": "verde" if tres["horas_nuevos"]["media"] <= 40 else "ambar" if tres["horas_nuevos"]["media"] <= 45 else "rojo",
             "detalle": "Laver " + str(next((c["h_mes"] for c in tres["horas_nuevos"]["clientes"] if c["nombre"] == "Laver"), "—")) + " h/mes · horas incompletas",
             "fuente": tres["horas_nuevos"]["fuente"], "umbral": "≤ 40 / 41-45 / > 45 h"},
            {"id": "vencidos", "nombre": "Compromisos vencidos sin aviso", "valor": f"{tres['vencidos']['tareas']} tareas · {tres['vencidos']['correos48']} clientes con correo > 48 h",
             "estado": "rojo", "detalle": "Tareas en revisión o bloqueadas con fecha pasada y 48 h sin movimiento", "fuente": tres["vencidos"]["fuente"], "umbral": "0 / 1-2 / 3 o más"},
        ],
        "clientes_rojo": rojos_verdad(),
        "equipo": {
            "imputacion": f"{tres['horas']['pct']} % de las horas esperadas ({tres['horas']['semana']}); a cero: " + ", ".join(tres["horas"]["cero"]),
            "en_alerta": len(alerta), "sobre_capacidad": [p["alias"] + " (" + ", ".join("%s %s" % (s, p["cartera"][s]) for s in p["sobre_capacidad"]) + ")" for p in sobre],
        },
    }
    informe["texto"] = texto_informe(informe)

    # ---- cierre de mes (septiembre) ----
    mes_ant = HOY.replace(day=1) - timedelta(days=1)
    pref = mes_ant.strftime("%Y-%m")
    libro = json.loads(LIBRO.read_text())
    bajas_panel = {b["cliente"]: b for b in datos["v7"].get("bajas", [])}
    altas, bajas = [], []
    for nombre, c in libro.items():
        fact = (c.get("meses") or {}).get(pref)
        if (c.get("primera") or "").startswith(pref):
            altas.append({"cliente": nombre, "estado": c.get("estado"), "primera_factura": c.get("primera"), "cuota": c.get("cuota_actual"),
                          "facturado_mes": fact, "cruce": "facturado" if fact else "sin factura en el mes",
                          "nota": "prorrateo del primer mes" if fact and c.get("cuota_actual") and fact < c["cuota_actual"] else None})
        if (c.get("fecha_baja") or "").startswith(pref):
            bp = bajas_panel.get(nombre) or {}
            bajas.append({"cliente": nombre, "fecha_baja": c["fecha_baja"], "cuota": c.get("cuota_jul") or bp.get("cuota"),
                          "facturado_mes": fact, "motivo": c.get("motivo") or bp.get("motivo"), "con_motivo": bool(c.get("motivo") or bp.get("motivo")),
                          "cruce": "última factura en el mes" if fact else "sin factura en el mes"})
    horas = []
    for ac in v7.get("cierre", []):
        pid = emparejador()(ac["account"])
        pct = round(ac["reales"] / ac["pautadas"] * 100) if ac.get("pautadas") else None
        horas.append({"account": ac["account"], "persona_id_account": pid, "pautadas": round(ac["pautadas"], 1), "reales": round(ac["reales"], 1),
                      "pct": pct, "desviacion": (pct - 100) if pct is not None else None, "clientes": len(ac["filas"]),
                      "fuera_banda": [f"{x['nombre']} {x['pct']} %" for x in ac["filas"] if x.get("pct") and not (50 <= x["pct"] <= 130)],
                      "sin_reunion": [x["nombre"] for x in ac["filas"] if x.get("sin_reunion")]})
    im = json.loads((BUILD / "informes_mensuales.json").read_text())
    mes_txt = {"09": "sep", "08": "ago", "10": "oct"}.get(pref[-2:], "sep")
    est_inf = Counter((v.get(mes_txt) or {}).get("estado") or "sin dato" for k, v in im.items() if k != "_meta" and isinstance(v, dict))
    cierre = {
        "mes": pref, "corte": corte,
        "altas": altas, "bajas": bajas,
        "horas_por_account": sorted(horas, key=lambda x: -(x["pct"] or 0)),
        "horas_sello": "Horas incompletas: el equipo imputa alrededor del 52 %. Solo como aviso.",
        "informes": dict(est_inf), "informes_nota": im["_meta"].get("notas", "")[:300],
        "rojos": rojos_verdad(),
        "fuentes": {"altas_bajas": "Libro de clientes corregido el 1-oct (facturas de Holded por mes) y bajas del panel de Mili",
                    "horas": "ClickUp, horas por account (pautadas = cuota ÷ 31,47 €/h)",
                    "informes": "Informes mensuales (ClickUp y Desk; enviado = hay correo saliente en Desk)",
                    "rojos": "Verdad única de la app: clientes en crítico (la misma lista que En rojo)"},
        "verificacion_mili": "El cierre que mandó Mili el 2-oct arrastraba datos del 17-sep y contaba como activo un cliente de baja. Este se genera solo, con la hora de corte de cada fuente.",
    }
    cierre["texto"] = texto_cierre(cierre)
    return {"_meta": {"generado": AHORA.strftime("%Y-%m-%d %H:%M"), "exigencias": "Mili 48 (lo que manda a Tomás, corto) y 49 (cierre de mes completo y revisado)",
                      "quien_lo_ve": "Tomás y Mili"}, "informe_semanal": informe, "cierre_mes": cierre}


def altas_num():
    V = verdad()
    nuevos = [c for c in V.values() if c.get("nuevo") and (c.get("encendido") or {}).get("estado") != "pendiente_en_plazo"]
    ok = [c for c in nuevos if c["encendido"]["estado"] in ("en_plazo", "en_limite")]
    sin = [c["nombre"] for c in nuevos if c["encendido"]["estado"] == "sin_encender_fuera_de_plazo"]
    tarde = [c["nombre"] for c in nuevos if c["encendido"]["estado"] == "tarde"]
    return {"id": "altas", "nombre": "Altas en plazo (encendidas el día 10, límite 12)", "valor": f"{len(ok)} de {len(nuevos)}",
            "estado": "rojo" if sin or tarde else "verde",
            "detalle": "; ".join(x for x in ["Sin encender: " + ", ".join(sin) if sin else "", "Encendidas tarde: " + ", ".join(tarde) if tarde else ""] if x) or "Todas en plazo",
            "fuente": "Verdad única (misma lista que Clientes nuevos); no cuentan las que aún están en plazo", "umbral": "100 % el día 10"}


def rojos_verdad():
    A = alias()
    return [{"cliente": c["nombre"], "cliente_id": c["cliente_id"], "account": A.get(c.get("account"), "sin account"), "motivo": (c.get("motivos") or ["—"])[0]}
            for c in verdad().values() if c.get("gravedad") == "critico"]


def eur(x):
    return "—" if x is None else f"{x:,.0f} €".replace(",", ".")


def texto_informe(I):
    L = [f"Semana {I['semana']} · corte de los datos {I['corte']}", "", "QUÉ NECESITO QUE DESBLOQUEES"]
    if I["desbloquear"]:
        for i, d in enumerate(I["desbloquear"], 1):
            L.append(f"{i}. {d['titulo']}. Recomiendo: {d['recomendacion']} (vence {d['vence']})")
    else:
        L.append("Nada pendiente.")
    L += ["", "LOS 3 NÚMEROS"]
    for n in I["numeros"]:
        L.append(f"· {n['nombre']}: {n['valor']} [{n['estado']}] · {n['detalle']} · umbral {n['umbral']}")
    L += ["", f"CLIENTES EN ROJO ({len(I['clientes_rojo'])})"]
    for c in I["clientes_rojo"]:
        L.append(f"· {c['cliente']} ({c['account']}): {c['motivo']}")
    L += ["", "EQUIPO", f"· Imputación: {I['equipo']['imputacion']}", f"· Personas en alerta: {I['equipo']['en_alerta']}"]
    if I["equipo"]["sobre_capacidad"]:
        L.append("· Por encima de capacidad: " + "; ".join(I["equipo"]["sobre_capacidad"]))
    return "\n".join(L)


def texto_cierre(C):
    L = [f"CIERRE DE {C['mes']} · Operaciones · corte {C['corte']}", "", f"ALTAS ({len(C['altas'])})"]
    for a in C["altas"]:
        L.append(f"· {a['cliente']}: primera factura {a['primera_factura']}, facturado en el mes {eur(a['facturado_mes'])} ({a['cruce']}{', ' + a['nota'] if a['nota'] else ''})")
    L += ["", f"BAJAS ({len(C['bajas'])})"]
    for b in C["bajas"]:
        L.append(f"· {b['cliente']} ({b['fecha_baja']}): {b['motivo'] or 'SIN MOTIVO'}")
    L += ["", "HORAS POR ACCOUNT (reales frente a pautadas) · " + C["horas_sello"]]
    for h in C["horas_por_account"]:
        L.append(f"· {h['account']}: {h['reales']} h de {h['pautadas']} h ({h['pct'] if h['pct'] is not None else '—'} %, desviación {('%+d' % h['desviacion']) if h['desviacion'] is not None else 'sin pautadas'} %)" + (f" · fuera de banda: {', '.join(h['fuera_banda'])}" if h["fuera_banda"] else ""))
    L += ["", "INFORMES DEL MES: " + ", ".join(f"{k} {v}" for k, v in C["informes"].items()), "", f"CLIENTES EN ROJO ({len(C['rojos'])})"]
    for r in C["rojos"]:
        L.append(f"· {r['cliente']} ({r['account']}): {r['motivo']}")
    return "\n".join(L)


def main():
    clientes_app = json.loads((DATA / "clientes.json").read_text())
    clientes_app = clientes_app if isinstance(clientes_app, list) else clientes_app.get("clientes", [])
    F = firmadas()
    escribir("decisiones/firmadas.json", F)
    R = reloj(clientes_app)
    escribir("decisiones/reloj.json", R)
    D = direccion(R, clientes_app)
    escribir("decisiones/direccion.json", D)
    print(f"firmadas: {F['_meta']['total']} · reloj: {len(R['decisiones'])} ({sum(1 for d in R['decisiones'] if not d.get('respondida'))} pendientes) · "
          f"cierre {D['cierre_mes']['mes']}: {len(D['cierre_mes']['altas'])} altas, {len(D['cierre_mes']['bajas'])} bajas")


if __name__ == "__main__":
    main()

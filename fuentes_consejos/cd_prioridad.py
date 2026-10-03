#!/usr/bin/env python3
"""fuentes_consejos/cd_prioridad.py · Cerebro de decisiones v2 (3-oct-2026) · PRIORIZAR POR IMPACTO.

Cada propuesta lleva:
  impacto   · euros en riesgo al mes = cuota del cliente × probabilidad de baja según su gravedad (verdad única) y el tema
              del consejo; o ingresos de captación (ventas de RO: cuota media de un alta × probabilidad de cierre).
              Si no hay cliente ni venta: nivel por gravedad (sin euros).
  urgencia  · plazo y días de retraso (vencida, hoy, esta semana).
  esfuerzo  · minutos estimados por tipo de tarea (una llamada ≠ rehacer una campaña).
  puntos    · orden de la regla (con el peso de su puesto) + impacto + urgencia − esfuerzo + aprendizaje.
  motivo    · una línea: «GAC paga 1.470 €/mes, es cliente crítico y lleva 9 días sin leads». Sin importes si la persona
              no ve la cuota de ese cliente (motivo_sin_importes); el servidor elige cuál viaja.

Probabilidades de baja (estimación de RO, no medida): se apoyan en el churn de 2026 (53 bajas con 60 activos a 1-oct,
fuente: BAJAS_LTV_CHURN_2026-10-01) repartido por gravedad. Se recalibran con el bucle de aprendizaje.
"""
import math
import re

P_BAJA = {"critico": 0.30, "atencion": 0.10, "bien": 0.03}
# El tema multiplica: una queja o el silencio pesan más que una pieza de redes (consejero-account-ro: «el silencio es alarma»)
FACTOR_TEMA = {"relacion": 1.3, "captacion": 1.2, "crm": 1.1, "arranque": 1.4, "dinero": 1.0, "web": 0.8, "seo": 0.6,
               "redes": 0.5, "produccion": 0.6, "interno": 0.3, "datos": 0.4}
P_CIERRE = {"ventas_contrato": 0.5, "ventas_propuesta": 0.25, "ventas_sin_marcar": 0.15, "setter_llamar": 0.04,
            "setter_citas": 0.12, "outreach_positiva": 0.08, "outreach_clasificar": 0.02}
CUOTA_ALTA_DEFECTO = 1470.0      # cuota más repetida en las altas de septiembre (verdad única, cuota de octubre)
NIVEL_PTS = {"alto": 35, "medio": 20, "bajo": 5}     # sin euros pesa menos que un riesgo medido


def _n(x, d=0.0):
    try:
        return float(x)
    except (TypeError, ValueError):
        return d


def euros(n):
    n = round(_n(n))
    return f"{n:,.0f}".replace(",", ".") + " €"


def cuota_media_alta(verdad_full):
    xs = sorted(_n(c.get("cuota")) for c in (verdad_full or {}).get("clientes") or [] if c.get("nuevo") and _n(c.get("cuota")) > 0)
    return xs[len(xs) // 2] if xs else CUOTA_ALTA_DEFECTO


def impacto(c, v_full, meta, cuota_alta):
    """c = candidato, v_full = cliente de la verdad única SIN recortar (solo servidor), meta = metadatos del tipo."""
    tema = (meta or {}).get("tema") or "interno"
    tipo = c.get("tipo")
    if tipo in P_CIERRE:
        n = 1
        try:
            n = max(1, int(str(c.get("cifra") or "1").split()[0]))
        except ValueError:
            pass
        e = cuota_alta * P_CIERRE[tipo] * (min(n, 5) if tipo.startswith(("setter", "outreach")) else 1)
        return {"euros_mes": round(e), "base": "captacion", "nivel": "alto" if e >= 500 else "medio" if e >= 150 else "bajo",
                "como": f"cuota media de un alta ({euros(cuota_alta)}/mes) × probabilidad de cierre ({int(P_CIERRE[tipo] * 100)} %)"}
    cuota = _n((v_full or {}).get("cuota"))
    grav = (v_full or {}).get("gravedad") or c.get("grav_cliente")
    if cuota > 0 and tipo == "adm_impago":
        # impago de un cliente activo: la cuota del mes siguiente también está en el aire (D-IMPAGO: decisión a los 60 días)
        p = max(0.5, P_BAJA.get(grav, 0.05))
        return {"euros_mes": round(cuota * p), "cuota": round(cuota), "p_baja": round(p, 2), "base": "riesgo_baja", "gravedad": grav,
                "nivel": "alto" if cuota * p >= 300 else "medio", "como": f"cuota ({euros(cuota)}/mes) en el aire mientras no se cobre ({int(p * 100)} %)"}
    if cuota > 0 and grav:
        p = min(0.6, P_BAJA.get(grav, 0.05) * FACTOR_TEMA.get(tema, 1.0))
        e = cuota * p
        return {"euros_mes": round(e), "cuota": round(cuota), "p_baja": round(p, 2), "base": "riesgo_baja", "gravedad": grav,
                "nivel": "alto" if e >= 300 else "medio" if e >= 100 else "bajo",
                "como": f"cuota ({euros(cuota)}/mes) × probabilidad de baja estimada ({int(round(p * 100))} %, cliente {grav})"}
    if grav and (v_full or c.get("grav_cliente")):
        return {"euros_mes": None, "base": "riesgo_baja", "gravedad": grav,
                "nivel": {"critico": "alto", "atencion": "medio"}.get(grav, "bajo"),
                "como": "sin cuota en la verdad única: pesa la gravedad del cliente"}
    g = c.get("gravedad") or "media"
    return {"euros_mes": None, "base": "gravedad", "nivel": {"alta": "alto", "media": "medio"}.get(g, "bajo"),
            "como": "sin cliente ni venta asociada: pesa la gravedad de la alerta"}


def urgencia(c):
    t = str(c.get("cuando") or "").lower()
    dias = 0
    if t.startswith("vencida"):
        if "ayer" in t:
            dias = 1
        else:
            try:
                dias = int([w for w in t.split() if w.isdigit()][0])
            except IndexError:
                dias = 1
        return {"nivel": "vencida", "dias_retraso": dias, "pts": 40 + min(dias * 4, 60)}
    if "hoy" in t or t in ("", "hoy"):
        return {"nivel": "hoy", "dias_retraso": 0, "pts": 30 if c.get("gravedad") == "alta" else 20}
    if "mañana" in t:
        return {"nivel": "mañana", "dias_retraso": 0, "pts": 15}
    return {"nivel": "semana", "dias_retraso": 0, "pts": 5}


def esfuerzo(meta):
    m = int((meta or {}).get("esfuerzo_min") or 20)
    return {"minutos": m, "nivel": "rápido" if m <= 15 else "medio" if m <= 60 else "largo", "pts": min(25, m // 6)}


def impacto_pts(imp):
    e = imp.get("euros_mes")
    if e is None:
        return NIVEL_PTS.get(imp.get("nivel"), 10)
    return int(min(150, 25 * math.log2(1 + e / 50)))      # 44 €→23 · 147 €→50 · 441 €→80 · 1.470 €→123


RAZON_TIPO = {"dir_decision": "es una decisión con reloj", "adm_impago": "es dinero sin cobrar", "adm_sin_alta": "sin alta no se factura",
              "alta_fuera_plazo": "el arranque va fuera de plazo", "rrhh_alerta": "es una persona del equipo en alerta",
              "conexion": "sin esa clave la app no tiene datos", "jefa_cartera_roja": "su cartera necesita a su jefa",
              "jefa_crm_velocidad": "ahí se pierden las citas", "ops_cartera_riesgo": "un crítico sin plan es una baja en camino",
              "setter_llamar": "un lead nuevo se enfría en minutos", "prod_devuelta": "lo devuelto va antes que lo nuevo"}


def _unir(partes):
    partes = [p for p in partes if p]
    if len(partes) <= 1:
        return "".join(partes)
    return ", ".join(partes[:-1]) + " y " + partes[-1]


def motivo(c, imp, urg, esf, con_importes):
    """Una línea que explica por qué va en ese puesto de la lista (sin «Primero porque»: eso lo pone la pantalla)."""
    partes = []
    nombre_solo = None                        # sin verbo: «Xterna: lleva 26 días de retraso»
    quien = c.get("cliente") or c.get("etiqueta")
    g = {"critico": "es cliente crítico", "atencion": "es cliente a vigilar"}.get(imp.get("gravedad"), "")
    if imp.get("base") == "riesgo_baja":
        if con_importes and imp.get("cuota"):
            partes += [f"{quien or 'el cliente'} paga {euros(imp['cuota'])}/mes", g]
        else:
            partes.append(f"{quien or 'el cliente'} {g}".strip())
    elif imp.get("base") == "captacion":
        partes.append(("son " + euros(imp["euros_mes"]) + "/mes si se cierra") if con_importes else "es una venta que se puede cerrar")
    elif quien:
        nombre_solo = str(quien)
    if c.get("tipo") in RAZON_TIPO and imp.get("base") != "riesgo_baja":
        partes.append(RAZON_TIPO[c["tipo"]])
    cifra = str(c.get("cifra") or "")
    if urg["nivel"] == "vencida":
        d = urg["dias_retraso"]
        partes.append("lleva " + ("1 día" if d == 1 else f"{d} días") + " de retraso")
        if cifra and "vencida" not in cifra and "retraso" not in cifra:
            partes.append(cifra)
    else:
        if cifra:
            partes.append(cifra)
        cu = str(c.get("cuando") or "")
        if "vencida" not in cifra and cu.lower().startswith("vence"):
            dia = re.sub(r" a las \d{1,2}:\d\d$", "", cu)            # el día del plazo, sin la hora técnica de la alerta
            partes.append("vence hoy" if urg["nivel"] == "hoy" else dia[:1].lower() + dia[1:])
    if esf["nivel"] == "rápido":
        partes.append(f"son unos {esf['minutos']} minutos")
    txt = _unir(partes)
    if nombre_solo:
        txt = f"{nombre_solo}: {txt}" if txt else nombre_solo
        return txt
    return (txt[:1].upper() + txt[1:]) if txt else None


def puntuar(c, v_full, meta, cuota_alta, ajuste=0, con_importes=False):
    imp = impacto(c, v_full, meta, cuota_alta)
    urg = urgencia(c)
    esf = esfuerzo(meta)
    base = int(c.get("orden") or 0)
    pts = base + impacto_pts(imp) + urg["pts"] - esf["pts"] + int(ajuste or 0)
    pri = {"puntos": pts, "regla_pts": base, "impacto": imp, "urgencia": urg, "esfuerzo": esf, "aprendizaje_pts": int(ajuste or 0),
           "motivo": motivo(c, imp, urg, esf, True), "motivo_sin_importes": motivo(c, imp, urg, esf, False)}
    return pri


def sin_importes(pri):
    """La prioridad tal como la ve quien NO ve la cuota de ese cliente: sin euros ni cuota, con el motivo sin importes."""
    if not pri:
        return pri
    imp = {k: v for k, v in (pri.get("impacto") or {}).items() if k not in ("euros_mes", "cuota", "como", "p_baja")}
    out = {k: v for k, v in pri.items() if k not in ("motivo_sin_importes",)}
    out["impacto"] = imp
    out["motivo"] = pri.get("motivo_sin_importes")
    return out

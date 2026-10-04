#!/usr/bin/env python3
"""fuentes_consejos/cd_diagnostico.py · Cerebro de decisiones v2 (3-oct-2026) · DIAGNÓSTICO ANTES QUE CONSEJO.

Árbol por síntoma para cada cliente. Recorre el embudo de arriba abajo y PARA en el primer eslabón roto (criterio de
consejero-account-ro y diagnostico-embudo-despacho: «diagnostica antes de prescribir»). Cada nodo lleva:
  pregunta · estado (roto | ok | sin_dato) · evidencia {dato, fecha, fuente, url} · regla (id de conocimiento/reglas.json)
  · silla (quién lo arregla: trafficker | crm | account) · accion (qué hacer, en imperativo y sin prometer nada).

Síntomas (en este orden; un cliente puede tener uno solo, el primero que aparece):
  S1 pocos_leads        · campaña encendida y 0 leads en 7 días, o la mitad que la semana anterior
                          → ¿gasta? → ¿formulario o página rotos? → ¿creatividades cansadas? → ¿coste por lead disparado
                            (segmentación u oferta del anuncio)? → ¿medición?
  S2 leads_sin_citas    · 5 o más leads en 30 días y ninguna cita en 14 días (o menos de 1 de cada 10)
                          → ¿llegan a GoHighLevel? → ¿la subcuenta se usa? → ¿velocidad de contacto? → ¿mensajes del CRM
                            (WhatsApp fallido)? → ¿seguimiento (oportunidades paradas)?
  S3 citas_sin_ventas   · 3 o más citas en 30 días y ningún cierre en el embudo
                          → ¿están marcadas? → ¿asistencia? → ¿encaje de oferta (se escala, nunca se asesora al despacho)?
  S4 relacion_en_riesgo · la verdad única lo marca (correos sin contestar, sin reunión, bloqueo callado, arranque tarde)
                          → solo si no hay S1-S3: lo de captación manda.

Funciones puras: reciben las filas YA leídas (captación, CRM, verdad) y devuelven un dict o None. Sin red ni ficheros.
"""

SILLA_TXT = {"trafficker": "trafficker", "crm": "especialista de GoHighLevel", "account": "account"}


def _n(x, d=0.0):
    try:
        return float(x)
    except (TypeError, ValueError):
        return d


def _e(n):
    """1.470 € · 62,89 € (formato de España; el recorte de importes lo quita si quien lee no ve la inversión)."""
    n = _n(n)
    s = f"{n:,.2f}" if abs(n - round(n)) > 0.004 else f"{n:,.0f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".") + " €"


def _ent(n):
    n = _n(n)
    return f"{n:,.0f}".replace(",", ".")


def _pct(n):
    return f"{_n(n):.0f} %".replace(".", ",")


def _nodo(pregunta, estado, dato, regla, silla, accion=None, fecha=None, fuente=None, url=None):
    return {"pregunta": pregunta, "estado": estado, "regla": regla, "silla": silla, "accion": accion,
            "evidencia": {"dato": dato, "fecha": fecha, "fuente": fuente, "url": url}}


# ----------------------------------------------------------------------------------------------- S1 · pocos leads
def _pocos_leads(k, fecha):
    """k = fila de captación del cliente. None si no hay síntoma."""
    if not k or not (k.get("meta_activa") or _n((k.get("gasto") or {}).get("7d")) > 0):
        return None
    L, G = k.get("leads") or {}, k.get("gasto") or {}
    l7, lp, g7 = _n(L.get("7d")), _n(L.get("7d_prev")), _n(G.get("7d"))
    if not (l7 == 0 or (lp >= 4 and l7 <= lp / 2)):
        return None
    sintoma = (f"0 leads en 7 días con la campaña encendida" if l7 == 0
               else f"{_ent(l7)} leads en 7 días frente a {_ent(lp)} la semana anterior")
    cm = k.get("cuenta_meta") or {}
    url_meta = cm.get("enlace")
    fte = "Captación (Meta)"
    nodos = []
    # 1 · ¿gasta?
    no_gasta = cm.get("estado") not in (None, "activa") or _n(G.get("ayer")) == 0 and g7 < 1
    if no_gasta:
        nodos.append(_nodo("¿La campaña está gastando?", "roto",
                           f"Cuenta de Meta «{cm.get('estado') or 'sin estado'}»; último día con gasto: {cm.get('ultimo_dia_con_gasto') or 'sin dato'}",
                           "diag_no_gasta", "trafficker", "Mira hoy por qué la campaña no gasta (pago, saldo, anuncio rechazado) y avisa al account",
                           fecha, fte, url_meta))
        return {"sintoma": "pocos_leads", "texto": sintoma, "nodos": nodos}
    nodos.append(_nodo("¿La campaña está gastando?", "ok", f"Gastó {_e(g7)} en 7 días", "diag_no_gasta", "trafficker",
                       fecha=fecha, fuente=fte, url=url_meta))
    # 2 · ¿formulario o página rotos? (clics y gasto, pero 0 leads)
    an = (k.get("anuncios") or {}).get("anuncios") or []
    clics = sum(_n(a.get("clics_7d")) for a in an)
    if l7 == 0 and clics >= 100:
        nodos.append(_nodo("¿El formulario o la página recogen los datos?", "roto",
                           f"{_ent(clics)} clics en 7 días y ningún lead", "diag_formulario_roto", "trafficker",
                           "Prueba hoy el formulario del anuncio como si fueras un cliente y, si falla, avisa al account",
                           fecha, fte, url_meta))
        return {"sintoma": "pocos_leads", "texto": sintoma, "nodos": nodos}
    nodos.append(_nodo("¿El formulario o la página recogen los datos?", "ok" if clics else "sin_dato",
                       f"{_ent(clics)} clics en 7 días" if clics else "Sin clics por anuncio en el dato", "diag_formulario_roto",
                       "trafficker", fecha=fecha, fuente=fte, url=url_meta))
    # 3 · ¿creatividades cansadas? D-39 (firmada): SOLO con dos señales a la vez entre frecuencia > 3, caída de CTR ≥ 40 % y
    # «cansada» de la Torre. Con una sola señal no se cambia la creatividad (antes bastaba una: falsos «cansada»).
    def _senales(a):
        return sum([bool(a.get("cansada")), _n(a.get("frecuencia_7d")) > 3, _n(a.get("caida_ctr_pct")) >= 40])
    cans = [a for a in an if _senales(a) >= 2]
    if cans:
        a = max(cans, key=lambda x: _n(x.get("gasto_7d")))
        nodos.append(_nodo("¿Las creatividades están cansadas?", "roto",
                           f"«{a.get('nombre')}»: frecuencia {str(round(_n(a.get('frecuencia_7d')), 1)).replace('.', ',')}"
                           f" y el porcentaje de clics {'cae un ' + _pct(a.get('caida_ctr_pct')) if _n(a.get('caida_ctr_pct')) > 0 else 'sin caída'}"
                           + (f" ({len(cans)} anuncios así)" if len(cans) > 1 else ""),
                           "diag_fatiga", "trafficker", f"Cambia esta semana la creatividad «{a.get('nombre')}» por una nueva del mismo ángulo",
                           fecha, fte, a.get("enlace") or url_meta))
        return {"sintoma": "pocos_leads", "texto": sintoma, "nodos": nodos}
    nodos.append(_nodo("¿Las creatividades están cansadas?", "ok" if an else "sin_dato",
                       "Ningún anuncio con dos señales de cansancio a la vez (frecuencia > 3, clics −40 %)" if an else "Sin dato por anuncio", "diag_fatiga",
                       "trafficker", fecha=fecha, fuente=fte, url=url_meta))
    # 4 · ¿coste por lead disparado? (segmentación u oferta del anuncio)
    cr = k.get("cpl_resumen") or {}
    veces = _n(cr.get("veces_objetivo"))
    if veces >= 1.5 and cr.get("fiable"):
        nodos.append(_nodo("¿El coste por lead está dentro del objetivo?", "roto",
                           f"Coste por lead de {_e(cr.get('ref'))} ({cr.get('ref_base') or '7 días'}), {str(round(veces, 1)).replace('.', ',')} veces el techo",
                           "diag_segmentacion", "trafficker",
                           "Revisa hoy el mensaje del anuncio que más gasta (casi siempre falla el creativo, no el público) antes de tocar el presupuesto",
                           fecha, fte, url_meta))
        return {"sintoma": "pocos_leads", "texto": sintoma, "nodos": nodos}
    nodos.append(_nodo("¿El coste por lead está dentro del objetivo?", "ok" if cr.get("ref") else "sin_dato",
                       f"Coste por lead {_e(cr.get('ref'))}" if cr.get("ref") else "Sin muestra suficiente", "diag_segmentacion",
                       "trafficker", fecha=fecha, fuente=fte, url=url_meta))
    # 5 · ¿medición? (GoHighLevel recibe leads que Meta no cuenta)
    gl = _n(((k.get("ghl") or {}).get("embudo") or {}).get("leads_nuevos", {}).get("7d"))
    if gl > l7 + 2:
        nodos.append(_nodo("¿Meta mide todos los leads?", "roto",
                           f"GoHighLevel recibió {_ent(gl)} leads en 7 días y Meta cuenta {_ent(l7)}", "diag_medicion", "trafficker",
                           "Revisa el píxel y el evento de lead: Meta optimiza a ciegas si no los ve", fecha, fte, url_meta))
        return {"sintoma": "pocos_leads", "texto": sintoma, "nodos": nodos}
    nodos.append(_nodo("¿Meta mide todos los leads?", "sin_dato", "Sin señal de fallo de medición", "diag_medicion", "trafficker",
                       fecha=fecha, fuente=fte, url=url_meta))
    nodos[-1]["accion"] = "Sin causa clara en los datos: revísalo con el account antes de cambiar nada (un veredicto válido es «falta dato»)"
    nodos[-1]["estado"] = "roto"
    nodos[-1]["regla"] = "diag_sin_dato"
    return {"sintoma": "pocos_leads", "texto": sintoma, "nodos": nodos}


# ----------------------------------------------------------------------------------------------- S2 · leads sin citas
def _leads_sin_citas(s, k, fecha):
    """s = subcuenta del CRM. Leads que llegan pero no se convierten en citas."""
    if not s or s.get("tipo") not in (None, "cliente"):
        return None
    l30 = _n(s.get("leads_30d"))
    c14 = s.get("citas_14d") or {}
    c30 = s.get("citas_30d") or {}
    ag30 = _n(c30.get("agendadas"))
    if l30 < 5 or not (_n(c14.get("agendadas")) == 0 or ag30 < l30 / 10):
        return None
    sintoma = f"{_ent(l30)} leads en 30 días y {_ent(ag30)} {'cita' if ag30 == 1 else 'citas'} agendadas"
    ghl = (s.get("enlaces") or {}).get("ghl")
    fte = "Salud del CRM (GoHighLevel)"
    nodos = []
    # 1 · ¿llegan a GoHighLevel?
    lm, lg = _n(s.get("leads_meta_7d")), _n(s.get("leads_ghl_7d"))
    if lm >= 10 and lg < lm / 2:
        nodos.append(_nodo("¿Los leads de Meta llegan a GoHighLevel?", "roto", f"{_ent(lm)} leads en Meta y {_ent(lg)} en GoHighLevel (7 días)",
                           "diag_fuga", "crm", "Revisa hoy la conexión de Meta con GoHighLevel: los que no llegan no los llama nadie",
                           fecha, fte, ghl))
        return {"sintoma": "leads_sin_citas", "texto": sintoma, "nodos": nodos}
    nodos.append(_nodo("¿Los leads de Meta llegan a GoHighLevel?", "ok", f"{_ent(lg)} de {_ent(lm)} llegan (7 días)" if lm else "Sin leads de Meta que comparar",
                       "diag_fuga", "crm", fecha=fecha, fuente=fte, url=ghl))
    # 2 · ¿la subcuenta se usa?
    if s.get("sin_uso"):
        nodos.append(_nodo("¿El despacho usa la subcuenta?", "roto", "La subcuenta no tiene actividad del despacho", "diag_subcuenta_sin_uso",
                           "account", "Habla esta semana con el despacho de cómo trabaja sus leads y ofrécele una sesión corta de GoHighLevel",
                           fecha, fte, ghl))
        return {"sintoma": "leads_sin_citas", "texto": sintoma, "nodos": nodos}
    nodos.append(_nodo("¿El despacho usa la subcuenta?", "ok", f"{_ent(s.get('contactos_total'))} contactos y actividad", "diag_subcuenta_sin_uso",
                       "account", fecha=fecha, fuente=fte, url=ghl))
    # 3 · ¿velocidad de contacto? (garantía: 70 % con un intento en menos de 1 h)
    v = s.get("velocidad") or {}
    juz = _n(v.get("juzgables"))
    sin_tocar = _n(s.get("sin_tocar_24h"))
    if juz >= 5 and _n(v.get("pct_1h")) < 70:
        med = _n(v.get("mediana_min"))
        med_txt = f"{_ent(med / 60)} h" if med >= 120 else f"{_ent(med)} min"
        nodos.append(_nodo("¿El despacho contacta rápido?", "roto",
                           f"{_ent(v.get('en_1h'))} de {_ent(juz)} leads con un primer intento en menos de 1 h ({_pct(v.get('pct_1h'))}; garantía 70 %)"
                           + (f"; mediana {med_txt}" if med else "") + (f"; {_ent(sin_tocar)} sin tocar más de 24 h" if sin_tocar else ""),
                           "diag_velocidad", "crm", "Enseña hoy al despacho los leads sin tocar y pídele un primer intento en menos de 1 hora",
                           fecha, fte, ghl))
        return {"sintoma": "leads_sin_citas", "texto": sintoma, "nodos": nodos}
    nodos.append(_nodo("¿El despacho contacta rápido?", "ok" if juz >= 5 else "sin_dato",
                       f"{_pct(v.get('pct_1h'))} con intento en menos de 1 h" if juz >= 5 else "Pocos leads para juzgar la velocidad",
                       "diag_velocidad", "crm", fecha=fecha, fuente=fte, url=ghl))
    # 4 · ¿mensajes del CRM? (WhatsApp fallido > 10 %)
    w = s.get("whatsapp") or {}
    if _n(w.get("enviados")) >= 10 and _n(w.get("pct_fallo")) > 10:
        nodos.append(_nodo("¿Los mensajes automáticos llegan?", "roto", f"WhatsApp: {_ent(w.get('fallidos'))} de {_ent(w.get('enviados'))} fallidos ({_pct(w.get('pct_fallo'))})",
                           "diag_whatsapp", "crm", "Revisa hoy el número de WhatsApp y las plantillas de la subcuenta", fecha, fte, ghl))
        return {"sintoma": "leads_sin_citas", "texto": sintoma, "nodos": nodos}
    nodos.append(_nodo("¿Los mensajes automáticos llegan?", "ok" if w.get("enviados") else "sin_dato",
                       f"WhatsApp: {_pct(w.get('pct_fallo'))} de fallos" if w.get("enviados") else "Sin WhatsApp enviado", "diag_whatsapp", "crm",
                       fecha=fecha, fuente=fte, url=ghl))
    # 5 · ¿seguimiento? (≥ 50 % de oportunidades paradas más de 72 h)
    em = s.get("embudo") or {}
    if _n(em.get("cohorte_30d")) >= 5 and _n(em.get("pct_estancado")) >= 50:
        nodos.append(_nodo("¿Se hace seguimiento a los que no agendan?", "roto",
                           f"{_ent(em.get('estancados_72h'))} de {_ent(em.get('cohorte_30d'))} oportunidades llevan más de 72 h sin moverse",
                           "diag_seguimiento", "crm", "Revisa con el despacho la secuencia de seguimiento: 4 intentos en 72 h antes de darlo por perdido",
                           fecha, fte, ghl))
        return {"sintoma": "leads_sin_citas", "texto": sintoma, "nodos": nodos}
    nodos.append(_nodo("¿Se hace seguimiento a los que no agendan?", "sin_dato", "Sin señal clara en el embudo", "diag_seguimiento", "crm",
                       fecha=fecha, fuente=fte, url=ghl))
    nodos[-1].update(estado="roto", regla="diag_sin_dato",
                     accion="Sin causa clara en los datos: pregunta al despacho cómo trabaja los leads antes de cambiar la campaña")
    return {"sintoma": "leads_sin_citas", "texto": sintoma, "nodos": nodos}


# ----------------------------------------------------------------------------------------------- S3 · citas sin ventas
def _citas_sin_ventas(s, fecha):
    if not s:
        return None
    c30 = s.get("citas_30d") or {}
    em = (s.get("embudo") or {}).get("funnel") or {}
    if _n(c30.get("agendadas")) < 3 or _n(em.get("cerrado")) > 0:
        return None
    ghl = (s.get("enlaces") or {}).get("calendarios") or (s.get("enlaces") or {}).get("ghl")
    fte = "Salud del CRM (calendario de GoHighLevel)"
    sintoma = f"{_ent(c30.get('agendadas'))} citas en 30 días y ningún cierre en el embudo"
    nodos = []
    sin_e = _n(c30.get("sin_estado"))
    if sin_e >= max(2, _n(c30.get("agendadas")) / 2):
        nodos.append(_nodo("¿Están marcadas las citas (vino / no vino)?", "roto", f"{_ent(sin_e)} de {_ent(c30.get('agendadas'))} citas sin marcar",
                           "diag_citas_sin_marcar", "crm", "Marca hoy en GoHighLevel si vinieron: sin eso no se puede saber dónde se pierde la venta",
                           fecha, fte, ghl))
        return {"sintoma": "citas_sin_ventas", "texto": sintoma, "nodos": nodos}
    nodos.append(_nodo("¿Están marcadas las citas (vino / no vino)?", "ok", f"{_ent(sin_e)} sin marcar", "diag_citas_sin_marcar", "crm",
                       fecha=fecha, fuente=fte, url=ghl))
    asis = c30.get("asistencia_pct")
    if asis is not None and _n(asis) < 75:
        nodos.append(_nodo("¿Vienen a las citas?", "roto", f"Asistencia del {_pct(asis)} (bien desde el 75 %)", "diag_asistencia", "crm",
                           "Activa el recordatorio por WhatsApp el día antes y una llamada de confirmación", fecha, fte, ghl))
        return {"sintoma": "citas_sin_ventas", "texto": sintoma, "nodos": nodos}
    nodos.append(_nodo("¿Vienen a las citas?", "ok" if asis is not None else "sin_dato",
                       f"Asistencia del {_pct(asis)}" if asis is not None else "Sin asistencia medible", "diag_asistencia", "crm",
                       fecha=fecha, fuente=fte, url=ghl))
    nodos.append(_nodo("¿Encaja lo que promete el anuncio con lo que vende el despacho?", "roto",
                       f"{_ent(c30.get('celebradas'))} citas celebradas y 0 cierres", "diag_encaje_oferta", "account",
                       "Lleva a la próxima reunión el dato de citas y cierres y pregunta qué frena la venta; si toca cambiar la oferta, se eleva a dirección",
                       fecha, fte, ghl))
    return {"sintoma": "citas_sin_ventas", "texto": sintoma, "nodos": nodos}


# ----------------------------------------------------------------------------------------------- S4 · relación
def _relacion(v, fecha):
    if not v or v.get("gravedad") == "bien":
        return None
    nodos = []
    dias = _n(v.get("correos_sin_responder_dias"))
    if dias > 2:
        nodos.append(_nodo("¿Contestamos al cliente a tiempo?", "roto", f"Correos sin contestar desde hace {_ent(dias)} días laborables",
                           "rel_correo_48h", "account", "Contesta hoy el correo más antiguo y, si es una queja, llama", fecha, "Verdad única (Zoho Desk)"))
    elif v.get("sin_reunion_mes_pasado"):
        nodos.append(_nodo("¿Hemos tenido reunión este mes?", "roto", f"Sin reunión el mes pasado (última: {v.get('ultima_reunion') or 'sin dato'})",
                           "rel_silencio_30d", "account", "Agenda esta semana la reunión mensual con su informe", fecha, "Verdad única (Reuniones)"))
    elif v.get("bloqueo_callado"):
        b = v.get("bloqueos") or {}
        nodos.append(_nodo("¿Hay trabajo parado sin avisar?", "roto", f"{_ent(b.get('tareas'))} tareas paradas; la más antigua, {_ent(b.get('dias_max'))} días",
                           "rel_bloqueo_callado", "account", "Desbloquea la tarea parada o avisa hoy al cliente de la nueva fecha", fecha, "Verdad única (ClickUp)"))
    elif (v.get("encendido") or "") in ("tarde", "sin_encender_fuera_de_plazo"):
        nodos.append(_nodo("¿Arrancó la campaña en plazo?", "roto", f"Arranque: {v.get('encendido')} (día {v.get('dia_alta') or '—'})",
                           "arranque_dia_10", "account", "Escala hoy qué falta para encender (día 10, límite 12)", fecha, "Verdad única (Clientes nuevos)"))
    if not nodos:
        return None
    return {"sintoma": "relacion_en_riesgo", "texto": "; ".join((v.get("motivos") or [])[:2]) or "Relación en riesgo", "nodos": nodos}


SINTOMA_TXT = {"pocos_leads": "Pocos leads", "leads_sin_citas": "Leads sin citas", "citas_sin_ventas": "Citas sin ventas",
               "relacion_en_riesgo": "Relación en riesgo"}


def diagnosticar(v, k=None, s=None, fechas=None):
    """v = cliente de la verdad única, k = fila de Captación, s = subcuenta del CRM. Devuelve el primer síntoma con su
    camino (nodos hasta el primero roto) o None si no hay nada que diagnosticar."""
    fechas = fechas or {}
    for d in (_pocos_leads(k, fechas.get("captacion")), _leads_sin_citas(s, k, fechas.get("crm")),
              _citas_sin_ventas(s, fechas.get("crm")), _relacion(v, fechas.get("verdad"))):
        if d:
            roto = next((n for n in d["nodos"] if n["estado"] == "roto"), d["nodos"][-1])
            d["causa"] = roto
            d["titulo"] = SINTOMA_TXT[d["sintoma"]]
            d["cliente_id"] = (v or {}).get("cliente_id") or (k or {}).get("cliente_id") or (s or {}).get("cliente_id")
            d["cliente"] = (v or {}).get("nombre") or (k or {}).get("nombre") or (s or {}).get("nombre")
            return d
    return None


def dueno_de(v, silla):
    """La persona principal de esa silla en la verdad única (equipo[silla]); si no hay, el account."""
    eq = (v or {}).get("equipo") or {}
    for x in eq.get(silla) or []:
        if isinstance(x, dict) and x.get("principal") and x.get("persona_id"):
            return x["persona_id"]
    for x in eq.get(silla) or []:
        if isinstance(x, dict) and x.get("persona_id"):
            return x["persona_id"]
    return (v or {}).get("account")


OK_TXT = {"¿La campaña está gastando?": "gasta", "¿El formulario o la página recogen los datos?": "el formulario recoge datos",
          "¿Las creatividades están cansadas?": "creatividades sin fatiga", "¿El coste por lead está dentro del objetivo?": "coste por lead en objetivo",
          "¿Meta mide todos los leads?": "medición sin fallos", "¿Los leads de Meta llegan a GoHighLevel?": "los leads llegan a GoHighLevel",
          "¿El despacho usa la subcuenta?": "usa la subcuenta", "¿El despacho contacta rápido?": "contacta a tiempo",
          "¿Los mensajes automáticos llegan?": "los mensajes llegan", "¿Están marcadas las citas (vino / no vino)?": "citas marcadas",
          "¿Vienen a las citas?": "buena asistencia", "¿Se hace seguimiento a los que no agendan?": "hay seguimiento"}


def descartado(d, n=3):
    """Lo ya descartado en el camino, dicho en positivo («gasta; el formulario recoge datos; creatividades sin fatiga»)."""
    return [OK_TXT.get(x["pregunta"], x["pregunta"].lstrip("¿").rstrip("?").lower()) for x in d["nodos"] if x["estado"] == "ok"][:n]


def lineas(d, n=3):
    """El diagnóstico en 3 líneas para el copiloto sin clave: síntoma, causa con su dato, y lo que ya está descartado."""
    if not d:
        return []
    c = d["causa"]
    oks = descartado(d)
    out = [f"{d['titulo']}: {d['texto']}.", f"Causa probable: {c['evidencia']['dato'].rstrip('.')}."]
    if oks:
        out.append("Descartado: " + "; ".join(oks) + ".")
    return out[:n]

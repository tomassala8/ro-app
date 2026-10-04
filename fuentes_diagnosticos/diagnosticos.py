#!/usr/bin/env python3
"""fuentes_diagnosticos/diagnosticos.py · DIAGNÓSTICOS DE CALIDAD (4-oct-2026). Funciones puras: sin red, sin IA, sin ficheros.

Segunda familia de funciones, hermana del semáforo de riesgo de baja: no miran cuánto llega, miran QUÉ llega.
Cada diagnóstico devuelve el mismo formato (lo lee la app, el semáforo y el cerebro `calidad`):

  {"id", "area", "estado": rojo|ambar|verde|sin_dato, "titulo", "lectura" (una frase), "evidencia" {cifras},
   "muestra" n, "confianza": alta|media|baja, "ficha" (id del cerebro calidad), "fuente_dato"}

Nada de datos personales en la salida: los correos y teléfonos de los leads se leen en memoria y solo salen recuentos.
El dinero va en claves cpl*/coste* para que servir.py lo recorte a quien no ve la inversión (D-81, D-87).
Umbrales en UMBRALES, cada uno con su fuente; los marcados «pendiente» los tiene que firmar Tomás.
"""
import re
import statistics
import unicodedata
from urllib.parse import urlparse

H = 3600e3
DIA = 864e5

UMBRALES = {
    # ARBOL E4: «validación <40 % tras 50 leads»; aquí solo se mira el dato de contacto, que es un filtro previo y más grosero.
    "calidad_ambar_pct": (20, "criterio RO, pendiente de Tomás"),
    "calidad_rojo_pct": (35, "criterio RO, pendiente de Tomás"),
    "calidad_muestra_min": (10, "criterio RO"),
    # ARBOL E5: «% <24 h <90 % (cláusula) · p90 >4 h · leads con 0 intentos >0».
    "atencion_24h_ambar_pct": (90, "ro-equipo:30_SKILLS/diagnostico-embudo-despacho/recursos/ARBOL.md:93"),
    "atencion_24h_rojo_pct": (70, "criterio RO, pendiente de Tomás"),
    "atencion_sin_intento_rojo_pct": (20, "criterio RO, pendiente de Tomás"),
    "atencion_p90_ambar_h": (4, "ro-equipo:30_SKILLS/diagnostico-embudo-despacho/recursos/ARBOL.md:93"),
    # ARBOL E6: «agendado ÷ validados <25 %».
    "avance_cita_ambar_pct": (25, "ro-equipo:30_SKILLS/diagnostico-embudo-despacho/recursos/ARBOL.md:103"),
    "avance_cita_rojo_pct": (15, "criterio RO, pendiente de Tomás"),
    "avance_parados_ambar_pct": (50, "criterio RO, pendiente de Tomás"),
    "avance_parado_dias": (7, "criterio RO"),
    # ARBOL E7: «show <60 % (alarma) con ≥8 citas en la ventana».
    "asistencia_ambar_pct": (60, "ro-equipo:30_SKILLS/diagnostico-embudo-despacho/recursos/ARBOL.md:111"),
    "asistencia_muestra_min": (8, "ro-equipo:30_SKILLS/diagnostico-embudo-despacho/recursos/ARBOL.md:111"),
    # seo_web: «El contenido informacional genera tráfico, no clientes» (SOP-P1-02:60).
    "blog_ambar_pct": (50, "criterio RO, pendiente de Tomás"),
    "blog_rojo_pct": (70, "criterio RO, pendiente de Tomás"),
    "seo_clics_min": (30, "criterio RO"),
    "informativa_ambar_pct": (60, "criterio RO, pendiente de Tomás"),
    "marca_ambar_pct": (70, "criterio RO, pendiente de Tomás"),
}


def U(k):
    return UMBRALES[k][0]


def pct(a, b):
    return round(a * 100 / b, 1) if b else None


def normal(t):
    t = unicodedata.normalize("NFKD", str(t or "").lower())
    return "".join(c for c in t if not unicodedata.combining(c))


def confianza(n, alta=30, media=10):
    return "alta" if n >= alta else "media" if n >= media else "baja"


def resultado(id_, area, estado, titulo, lectura, evidencia, muestra, ficha, fuente):
    return {"id": id_, "area": area, "estado": estado, "titulo": titulo, "lectura": lectura, "evidencia": evidencia,
            "muestra": muestra, "confianza": confianza(muestra), "ficha": ficha, "fuente_dato": fuente}


# ------------------------------------------------------------------ calidad del dato de contacto de UN lead
DESECHABLES = {"mailinator.com", "yopmail.com", "guerrillamail.com", "10minutemail.com", "tempmail.com", "temp-mail.org",
               "trashmail.com", "sharklasers.com", "getnada.com", "maildrop.cc", "dispostable.com", "fakeinbox.com",
               "throwawaymail.com", "mailnesia.com", "mintemail.com", "emailondeck.com", "moakt.com"}
GRATUITOS = {"gmail.com", "googlemail.com", "hotmail.com", "hotmail.es", "outlook.com", "outlook.es", "live.com", "yahoo.com",
             "yahoo.es", "icloud.com", "me.com", "msn.com", "protonmail.com", "proton.me", "gmx.es", "gmx.com"}
# erratas que hacen que el correo no llegue nunca
ERRATAS = {"gmial.com", "gmai.com", "gmail.co", "gmail.con", "gmail.es", "gamil.com", "gnail.com", "hotmial.com",
           "hotmal.com", "hotmail.con", "hotmai.com", "outlok.com", "outlook.con", "yahoo.con", "yaho.es", "icloud.con"}
# buzones de función: nadie en concreto, se atienden tarde o nunca
ROL = {"info", "informacion", "contacto", "contact", "admin", "administracion", "hola", "hello", "oficina", "office",
       "gerencia", "recepcion", "general", "ventas", "comercial", "noreply", "no-reply", "mail", "correo", "empresa"}
RX_CORREO = re.compile(r"^[^@\s]+@[^@\s]+\.[a-z]{2,}$", re.I)
RX_BASURA = re.compile(r"^(a+s+d+f*|q+w+e+r*t*y*|z+x+c+v*|test\w*|prueba\w*|asd\w*|xxx+|aaa+|abc\d*|ejemplo|nombre|"
                       r"no|na|nada|ninguno|sin|fake|falso|\d+)$", re.I)


def calidad_correo(correo):
    c = (correo or "").strip().lower()
    if not c:
        return "falta"
    if not RX_CORREO.match(c):
        return "invalido"
    local, dom = c.rsplit("@", 1)
    if dom in DESECHABLES:
        return "desechable"
    if dom in ERRATAS:
        return "invalido"
    if RX_BASURA.match(local) or len(local) <= 2:
        return "basura"
    if local in ROL:
        return "rol"
    if dom in GRATUITOS:
        return "gratuito"      # normal en autónomos y pymes: se cuenta, pero NO resta calidad (pendiente de Tomás)
    return "ok"


def calidad_telefono(tel):
    """ok · falta · invalido · repetido (000000000, 123456789) · extranjero (prefijo que no es +34)."""
    t = (tel or "").strip()
    if not t:
        return "falta"
    d = re.sub(r"\D", "", t)
    extranjero = (t.startswith("+") and not t.startswith("+34")) or (d.startswith("00") and not d.startswith("0034"))
    if d.startswith("0034"):
        d = d[4:]
    elif t.startswith("+34") or (d.startswith("34") and len(d) == 11):
        d = d[2:]
    if extranjero:
        return "extranjero" if len(d) >= 8 else "invalido"
    if len(d) != 9 or d[0] not in "6789":
        return "invalido"
    if len(set(d[1:])) <= 1:
        return "repetido"
    return "ok"


def calidad_nombre(nombre):
    n = normal(nombre).strip()
    if not n:
        return "falta"
    partes = n.split()
    if all(RX_BASURA.match(p) for p in partes) or len(n.replace(" ", "")) <= 1:
        return "basura"
    return "ok"


RX_SPAM = re.compile(r"(https?://|www\.|\bseo\b.*\bservices?\b|crypto|bitcoin|casino|viagra|backlinks?|\bprice\b|\bhello\b)", re.I)


def calidad_lead(privado):
    """privado = {"nombre", "telefono", "correo"} → banderas, sin copiar ningún dato."""
    p = privado or {}
    ce, te, no = calidad_correo(p.get("correo")), calidad_telefono(p.get("telefono")), calidad_nombre(p.get("nombre"))
    spam = bool(RX_SPAM.search(str(p.get("nombre") or "")))
    tel_ok = te == "ok"
    correo_ok = ce in ("ok", "gratuito", "rol")
    if spam or (no == "basura" and not tel_ok) or (not tel_ok and not correo_ok):
        nivel = "no_calificable"
    elif not tel_ok:
        nivel = "dudoso"            # se le puede escribir, pero no llamar: en asesorías el lead se cierra por teléfono
    else:
        nivel = "ok"
    return {"correo": ce, "telefono": te, "nombre": no, "spam": spam, "nivel": nivel}


def clave_dup(privado):
    p = privado or {}
    d = re.sub(r"\D", "", p.get("telefono") or "")[-9:]
    c = (p.get("correo") or "").strip().lower()
    return d or None, c or None


# ------------------------------------------------------------------ 1 · leads no calificados
def diag_calidad_leads(leads):
    """leads = los es_lead de la ventana (con «privado» y, si hay, wa_env/wa_fallo/sms_*)."""
    L = [x for x in leads if x.get("es_lead")]
    n = len(L)
    cal = [calidad_lead(x.get("privado")) for x in L]
    cnt = lambda campo, val: sum(1 for c in cal if c[campo] == val)
    vistos_t, vistos_c, dup = set(), set(), 0
    for x in L:
        t, c = clave_dup(x.get("privado"))
        if (t and t in vistos_t) or (c and c in vistos_c):
            dup += 1
        vistos_t.add(t) if t else None
        vistos_c.add(c) if c else None
    malos = cnt("nivel", "no_calificable")
    dudosos = cnt("nivel", "dudoso")
    wa_env = sum(x.get("wa_env", 0) for x in L)
    wa_fallo = sum(x.get("wa_fallo", 0) for x in L)
    sms_env = sum(x.get("sms_env", 0) for x in L)
    sms_fallo = sum(x.get("sms_fallo", 0) for x in L)
    ev = {
        "leads": n, "no_calificables": malos, "pct_no_calificables": pct(malos, n), "dudosos": dudosos,
        "pct_malos_o_dudosos": pct(malos + dudosos, n),
        "sin_telefono": cnt("telefono", "falta"), "telefono_invalido": cnt("telefono", "invalido") + cnt("telefono", "repetido"),
        "telefono_extranjero": cnt("telefono", "extranjero"),
        "sin_correo": cnt("correo", "falta"), "correo_basura_o_invalido": cnt("correo", "basura") + cnt("correo", "invalido") + cnt("correo", "desechable"),
        "correo_de_buzon_general": cnt("correo", "rol"), "correo_gratuito": cnt("correo", "gratuito"),
        "nombre_basura": cnt("nombre", "basura"), "spam": sum(1 for c in cal if c["spam"]), "duplicados": dup,
        "whatsapp_fallidos": wa_fallo, "pct_whatsapp_fallido": pct(wa_fallo, wa_env),
        "sms_fallidos": sms_fallo, "pct_sms_fallido": pct(sms_fallo, sms_env),
    }
    if n < U("calidad_muestra_min"):
        return resultado("crm_leads_no_calificados", "crm", "sin_dato", "Calidad de los leads",
                         f"Solo {n} leads en la ventana: hacen falta {U('calidad_muestra_min')} para juzgar la calidad.", ev, n,
                         "cal_leads_no_calificados", "GoHighLevel · contactos de los últimos 30 días")
    p = pct(malos + dudosos, n)
    estado = "rojo" if p >= U("calidad_rojo_pct") else "ambar" if p >= U("calidad_ambar_pct") else "verde"
    motivos = sorted([("sin teléfono", ev["sin_telefono"]), ("teléfono mal escrito", ev["telefono_invalido"]),
                      ("teléfono de fuera de España", ev["telefono_extranjero"]),
                      ("correo falso o con errata", ev["correo_basura_o_invalido"]), ("spam", ev["spam"]),
                      ("duplicados", dup)], key=lambda x: -x[1])
    top = ", ".join(f"{k} ({v})" for k, v in motivos if v)[:160] or "sin un motivo dominante"
    lectura = (f"{malos + dudosos} de {n} leads ({p} %) no se pueden llamar o no son reales: {top}."
               if estado != "verde" else f"El dato de contacto es bueno: {n - malos - dudosos} de {n} leads se pueden llamar.")
    return resultado("crm_leads_no_calificados", "crm", estado, "Calidad de los leads", lectura, ev, n,
                     "cal_leads_no_calificados", "GoHighLevel · contactos de los últimos 30 días")


# ------------------------------------------------------------------ 2 · el despacho no atiende los leads
def diag_atencion(leads, ahora_ms):
    """Leads con más de 24 h: primer intento de una persona, cuántos sin tocar, p90 y respuesta."""
    J = [x for x in leads if x.get("es_lead") and x.get("creado") and x["creado"] <= ahora_ms - 24 * H]
    n = len(J)
    tiempos = sorted(x["humano_min"] for x in J if x.get("humano_min") is not None)
    en24 = sum(1 for t in tiempos if t <= 1440)
    sin = sum(1 for x in J if not x.get("intentos") and not x.get("cita"))
    p90 = round(tiempos[min(len(tiempos) - 1, int(len(tiempos) * 0.9))] / 60, 1) if tiempos else None
    respondieron = sum(1 for x in J if x.get("respondio"))
    citas_sin_intento = sum(1 for x in J if not x.get("intentos") and x.get("cita"))
    ev = {"leads_24h": n, "atendidos_24h": en24, "pct_24h": pct(en24, n), "sin_intento": sin, "pct_sin_intento": pct(sin, n),
          "p90_horas": p90, "mediana_min": round(statistics.median(tiempos)) if tiempos else None,
          "respondieron": respondieron, "pct_respondieron": pct(respondieron, n), "con_cita_sin_intento_en_crm": citas_sin_intento}
    if n < 5:
        return resultado("crm_despacho_no_atiende", "crm", "sin_dato", "Atención a los leads",
                         f"Solo {n} leads con más de 24 h: aún no se puede juzgar la atención.", ev, n,
                         "cal_despacho_no_atiende", "GoHighLevel · conversaciones de cada lead")
    p24, psin = pct(en24, n), pct(sin, n)
    if p24 < U("atencion_24h_rojo_pct") or psin >= U("atencion_sin_intento_rojo_pct"):
        estado = "rojo"
    elif p24 < U("atencion_24h_ambar_pct") or sin > 0 or (p90 or 0) > U("atencion_p90_ambar_h"):
        estado = "ambar"
    else:
        estado = "verde"
    sin_registro = sum(1 for x in J if not x.get("intentos"))
    fuera_crm = pct(sin_registro, n) >= 80 and citas_sin_intento > 0
    if fuera_crm:
        lectura = (f"El CRM no registra intentos en {sin_registro} de {n} leads, pero hay citas: lo más probable es que el despacho "
                   "llame fuera del CRM. La conversación es «el CRM no refleja tu gestión», no «no llamas».")
    elif estado == "verde":
        lectura = f"El despacho atiende: {en24} de {n} leads tuvieron un intento de una persona en menos de 24 h."
    else:
        lectura = f"Solo {en24} de {n} leads ({p24} %) tuvieron un intento de una persona en 24 h y {sin} siguen sin tocar."
    r = resultado("crm_despacho_no_atiende", "crm", estado, "Atención a los leads", lectura, ev, n,
                  "cal_despacho_no_atiende", "GoHighLevel · conversaciones de cada lead")
    r["evidencia"]["posible_gestion_fuera_del_crm"] = fuera_crm
    return r


# ------------------------------------------------------------------ 3 · los leads llegan pero no avanzan
def diag_avance(leads, oportunidades, citas, ahora_ms, ventana_dias=30):
    ini = ahora_ms - ventana_dias * DIA
    L = [x for x in leads if x.get("es_lead") and x.get("creado") and ini <= x["creado"] <= ahora_ms - 72 * H]
    n = len(L)
    con_cita = sum(1 for x in L if x.get("cita"))
    O = [o for o in oportunidades if o.get("creada") and ini <= o["creada"] <= ahora_ms - U("avance_parado_dias") * DIA]
    parados = [o for o in O if (o.get("ultimo_cambio") or o["creada"]) - o["creada"] <= H]   # nunca cambió de etapa
    etapas = {}
    for o in parados:
        etapas[o.get("etapa") or "sin etapa"] = etapas.get(o.get("etapa") or "sin etapa", 0) + 1
    pasadas = [c for c in citas if c.get("inicio") and ini <= c["inicio"] < ahora_ms and c.get("estado") not in ("cancelled", "invalid")]
    vinieron = sum(1 for c in pasadas if c.get("estado") == "showed")
    faltaron = sum(1 for c in pasadas if c.get("estado") == "noshow")
    ev = {"leads": n, "con_cita": con_cita, "pct_a_cita": pct(con_cita, n),
          "oportunidades": len(O), "nunca_movidas": len(parados), "pct_nunca_movidas": pct(len(parados), len(O)),
          "etapa_donde_se_quedan": max(etapas, key=etapas.get) if etapas else None,
          "citas_pasadas": len(pasadas), "vinieron": vinieron, "no_vinieron": faltaron, "asistencia_pct": pct(vinieron, vinieron + faltaron)}
    if n < 10:
        return resultado("crm_leads_no_avanzan", "crm", "sin_dato", "Avance de los leads en el embudo",
                         f"Solo {n} leads con 72 h o más: hacen falta 10 para juzgar el avance.", ev, n,
                         "cal_leads_no_avanzan", "GoHighLevel · oportunidades, leads y citas")
    pc = pct(con_cita, n)
    pp = pct(len(parados), len(O)) if O else None
    asist_mala = (vinieron + faltaron) >= U("asistencia_muestra_min") and pct(vinieron, vinieron + faltaron) < U("asistencia_ambar_pct")
    if pc < U("avance_cita_rojo_pct"):
        estado = "rojo"
    elif pc < U("avance_cita_ambar_pct") or (pp is not None and pp >= U("avance_parados_ambar_pct")) or asist_mala:
        estado = "ambar"
    else:
        estado = "verde"
    trozos = [f"{con_cita} de {n} leads ({pc} %) llegaron a cita"]
    if pp is not None and len(parados):
        trozos.append(f"{len(parados)} de {len(O)} oportunidades no se han movido de «{ev['etapa_donde_se_quedan']}» en {U('avance_parado_dias')} días")
    if asist_mala:
        trozos.append(f"y a las citas solo viene el {ev['asistencia_pct']} %")
    lectura = "; ".join(trozos) + "."
    return resultado("crm_leads_no_avanzan", "crm", estado, "Avance de los leads en el embudo", lectura, ev, n,
                     "cal_leads_no_avanzan", "GoHighLevel · oportunidades, leads y citas")


# ------------------------------------------------------------------ 4 · veredicto: ¿leads malos o despacho que no atiende?
def veredicto_embudo(calidad, atencion, avance):
    """Recorre de arriba abajo y para en el PRIMER eslabón roto (ARBOL §1.4): calidad del lead → atención → avance."""
    est = {d["id"]: d["estado"] for d in (calidad, atencion, avance) if d}
    if all(v == "sin_dato" for v in est.values()):
        return {"veredicto": "sin_dato", "frase": "Aún no hay leads suficientes para saber dónde se cae el embudo."}
    if avance and avance["estado"] == "verde" and calidad["estado"] != "rojo":
        return {"veredicto": "embudo_sano", "frase": "Los leads llegan, se atienden y avanzan."}
    if calidad["estado"] == "rojo":
        return {"veredicto": "leads_malos", "frase": "El problema está en el origen: buena parte de los leads no se pueden llamar o no son reales. Antes de exigir al despacho, arregla el formulario o la campaña."}
    if atencion["estado"] == "rojo":
        f = ("El CRM no refleja la gestión del despacho: hay que comprobar si llama fuera del CRM antes de concluir nada."
             if atencion["evidencia"].get("posible_gestion_fuera_del_crm") else
             "Los leads son buenos, pero el despacho no los atiende a tiempo. Más inversión solo compraría más leads sin llamar.")
        return {"veredicto": "despacho_no_atiende", "frase": f}
    ev = (avance or {}).get("evidencia", {})
    resp = (atencion or {}).get("evidencia", {}).get("pct_respondieron")
    if ev.get("asistencia_pct") is not None and ev.get("citas_pasadas", 0) >= U("asistencia_muestra_min") and ev["asistencia_pct"] < U("asistencia_ambar_pct"):
        return {"veredicto": "no_vienen", "frase": "Agendan pero no vienen: casi siempre es el protocolo anti-plantón incompleto, no leads malos."}
    if resp is not None and resp < 30 and atencion["estado"] == "verde":
        return {"veredicto": "leads_malos", "frase": f"El despacho llama a tiempo pero solo responde el {resp} % de los leads: señal de lead poco interesado. Escucha 5 llamadas antes de culpar al origen."}
    if avance and avance["estado"] in ("rojo", "ambar"):
        return {"veredicto": "contacta_no_agenda", "frase": "Los leads se atienden y responden, pero no llegan a cita: el fallo suele estar en la conversación (no pide la cita o da precio en frío)."}
    return {"veredicto": "embudo_sano", "frase": "Sin un eslabón roto claro."}


# ------------------------------------------------------------------ 5 · publicidad: leads baratos pero malos
def diag_cpl_enganoso(cpl, cpl_referencia, calidad):
    """cpl del cliente (30 días) frente a su referencia (objetivo o mediana de cartera) + calidad del lead."""
    pm = (calidad or {}).get("evidencia", {}).get("pct_malos_o_dudosos")
    n = (calidad or {}).get("muestra", 0)
    if not cpl or pm is None or calidad["estado"] == "sin_dato":
        return resultado("pub_leads_baratos_malos", "publicidad", "sin_dato", "Coste por lead que de verdad sirve",
                         "Falta el coste por lead o la calidad de los leads.", {"cpl_bruto": cpl}, n,
                         "cal_leads_baratos_malos", "Meta Ads + GoHighLevel")
    util = max(1e-9, 1 - pm / 100)
    coste_util = round(cpl / util, 2)
    ev = {"cpl_bruto": round(cpl, 2), "cpl_referencia": cpl_referencia, "pct_malos_o_dudosos": pm,
          "coste_por_lead_calificable": coste_util}
    barato = cpl_referencia and cpl <= cpl_referencia
    caro_de_verdad = cpl_referencia and coste_util > cpl_referencia * 1.3
    if barato and caro_de_verdad:
        estado, lectura = "rojo", f"El lead parece barato, pero el {pm} % no sirve: el coste por lead que se puede llamar supera la referencia en más de un 30 %."
    elif caro_de_verdad:
        estado, lectura = "ambar", f"Con el {pm} % de leads que no sirven, el coste por lead calificable supera la referencia en más de un 30 %."
    else:
        estado, lectura = "verde", "El coste por lead calificable está dentro de la referencia."
    return resultado("pub_leads_baratos_malos", "publicidad", estado, "Coste por lead que de verdad sirve", lectura, ev, n,
                     "cal_leads_baratos_malos", "Meta Ads + GoHighLevel")


# ------------------------------------------------------------------ 6 · SEO: mucho tráfico, pero de blog
RX_BLOG = re.compile(r"/(blog|blogs|noticias|noticia|articulos?|actualidad|novedades|post|posts|news|category|categoria|tag|etiqueta|"
                     r"guia|guias|recursos|faq|preguntas)(/|$)|/\d{4}/\d{2}/", re.I)


def tipo_pagina(url):
    p = urlparse(url).path or "/"
    if p in ("", "/") or re.fullmatch(r"/(es|ca|en)/?", p):
        return "portada"
    if RX_BLOG.search(p):
        return "blog"
    if re.search(r"/(contacto|contact|cita|presupuesto|aviso-legal|politica|cookies|privacidad)", p, re.I):
        return "contacto_legal"
    return "servicio"


def diag_seo_blog(gsc):
    """gsc = una entrada de fuentes_seo/_cache/gsc.json: 'mes' {clics} y 'paginas' [[url, clics, impr, pos, clics_ant]]."""
    pags = (gsc or {}).get("paginas_todas") or (gsc or {}).get("paginas") or []
    total = ((gsc or {}).get("mes") or {}).get("clics") or 0
    por = {"blog": 0, "servicio": 0, "portada": 0, "contacto_legal": 0}
    for fila in pags:
        por[tipo_pagina(fila[0])] += fila[1] or 0
    vistos = sum(por.values())
    ev = {"clics_mes": total, "clics_clasificados": vistos, "cobertura_pct": pct(vistos, total), **{f"clics_{k}": v for k, v in por.items()},
          "pct_blog": pct(por["blog"], vistos), "paginas_leidas": len(pags)}
    if total < U("seo_clics_min") or not pags:
        return resultado("seo_trafico_blog", "seo_web", "sin_dato", "Tráfico SEO que puede ser cliente",
                         f"Menos de {U('seo_clics_min')} clics al mes en Search Console: poco que repartir.", ev, total,
                         "cal_seo_trafico_blog", "Search Console · páginas, 28 días")
    pb = pct(por["blog"], vistos)
    estado = "rojo" if pb >= U("blog_rojo_pct") else "ambar" if pb >= U("blog_ambar_pct") else "verde"
    util = por["servicio"] + por["portada"]
    lectura = (f"El {pb} % de los clics de Google van al blog y solo {util} a páginas de servicio o portada: mucho tráfico, poco cliente."
               if estado != "verde" else f"El tráfico va sobre todo a páginas de servicio y portada ({util} clics); el blog es el {pb} %.")
    if ev["cobertura_pct"] is not None and ev["cobertura_pct"] < 60:
        lectura += f" Ojo: solo se ven las páginas que suman el {ev['cobertura_pct']} % de los clics."
    return resultado("seo_trafico_blog", "seo_web", estado, "Tráfico SEO que puede ser cliente", lectura, ev, total,
                     "cal_seo_trafico_blog", "Search Console · páginas, 28 días")


# ------------------------------------------------------------------ 7 · SEO: intención de búsqueda (informativa, marca, compra)
RX_INFO = re.compile(r"^(que|qu[eé]|como|c[oó]mo|cuando|cu[aá]ndo|cuanto|cu[aá]nto|cual|cu[aá]l|donde|por que|para que)\b|"
                     r"\b(modelo \d{3}|plazo|plazos|ejemplo|plantilla|definicion|significado|calcular|calculadora|pdf|requisitos|"
                     r"diferencia|obligatori|tabla|formulario|descargar|wikipedia|boe|ley \d|articulo|que es)\b", re.I)
RX_COMPRA = re.compile(r"\b(asesor|asesoria|asesores|gestor|gestoria|gestorias|abogad|despacho|bufete|economista|contable|"
                       r"auditor|consultor|contratar|precio|precios|tarifa|tarifas|cerca|mejor|online|presupuesto)\w*", re.I)


def tipo_busqueda(q, marca):
    n = normal(q)
    if any(m and m in n for m in marca):
        return "marca"
    if RX_INFO.search(n):
        return "informativa"
    if RX_COMPRA.search(n):
        return "compra"
    return "otra"


def diag_seo_intencion(gsc, marca):
    """marca = palabras que delatan una búsqueda de marca (nombre del despacho, raíz del dominio), ya en minúsculas."""
    bus = (gsc or {}).get("busquedas_todas") or (gsc or {}).get("busquedas") or []
    por = {"marca": 0, "informativa": 0, "compra": 0, "otra": 0}
    for fila in bus:
        por[tipo_busqueda(fila[0], marca)] += fila[1] or 0
    vistos = sum(por.values())
    sin_marca = vistos - por["marca"]
    ev = {"clics_clasificados": vistos, **{f"clics_{k}": v for k, v in por.items()}, "pct_marca": pct(por["marca"], vistos),
          "pct_informativa_sin_marca": pct(por["informativa"], sin_marca), "pct_compra_sin_marca": pct(por["compra"], sin_marca),
          "busquedas_leidas": len(bus)}
    if vistos < U("seo_clics_min"):
        return resultado("seo_intencion_busqueda", "seo_web", "sin_dato", "Intención de las búsquedas que traen clics",
                         f"Menos de {U('seo_clics_min')} clics en las búsquedas visibles.", ev, vistos,
                         "cal_seo_intencion_busqueda", "Search Console · búsquedas, 28 días")
    pi, pmca = ev["pct_informativa_sin_marca"] or 0, ev["pct_marca"] or 0
    if pi >= U("informativa_ambar_pct") and (ev["pct_compra_sin_marca"] or 0) < 15:
        estado, lectura = "rojo", f"De los clics que no buscan el nombre del despacho, el {pi} % son dudas («qué es», «modelo 303», «plazo») y casi ninguno busca contratar."
    elif pi >= U("informativa_ambar_pct"):
        estado, lectura = "ambar", f"El {pi} % de los clics sin marca son búsquedas informativas: tráfico que pregunta, no que contrata."
    elif pmca >= U("marca_ambar_pct"):
        estado, lectura = "ambar", f"El {pmca} % de los clics buscan el nombre del despacho: el SEO trae a quien ya lo conocía, casi nadie nuevo."
    else:
        estado, lectura = "verde", f"Buena mezcla: el {ev['pct_compra_sin_marca']} % de los clics sin marca buscan un servicio."
    return resultado("seo_intencion_busqueda", "seo_web", estado, "Intención de las búsquedas que traen clics", lectura, ev, vistos,
                     "cal_seo_intencion_busqueda", "Search Console · búsquedas, 28 días")


CATALOGO = ["crm_leads_no_calificados", "crm_despacho_no_atiende", "crm_leads_no_avanzan", "pub_leads_baratos_malos",
            "seo_trafico_blog", "seo_intencion_busqueda"]


def marca_de(nombre, web):
    """Palabras de marca: raíz del dominio y palabras largas del nombre que no son genéricas del sector."""
    genericas = {"asesoria", "asesores", "asesor", "gestoria", "consulting", "consultores", "abogados", "economistes",
                 "economistas", "auditores", "advisory", "partners", "grup", "grupo", "gestion", "asociados", "legal", "despacho"}
    out = set()
    dom = (urlparse(web if "//" in (web or "") else "//" + (web or "")).hostname or "").replace("www.", "")
    if dom:
        out.add(normal(dom.split(".")[0]).replace("-", " ").strip())
    for p in re.split(r"[\s\-_&.,]+", normal(nombre)):
        if len(p) >= 4 and p not in genericas:
            out.add(p)
    return sorted(x for x in out if x)


def diagnosticar_cliente(entrada, ahora_ms):
    """entrada = {"leads", "oportunidades", "citas", "gsc", "marca", "cpl", "cpl_referencia"} (cualquiera puede faltar)."""
    leads, opps, citas = entrada.get("leads") or [], entrada.get("oportunidades") or [], entrada.get("citas") or []
    out = []
    cal = ate = ava = None
    if "leads" in entrada:
        ini = ahora_ms - 30 * DIA
        en30 = [x for x in leads if x.get("creado") and ini <= x["creado"] < ahora_ms]
        cal, ate, ava = diag_calidad_leads(en30), diag_atencion(en30, ahora_ms), diag_avance(leads, opps, citas, ahora_ms)
        out += [cal, ate, ava]
        if "cpl" in entrada:
            out.append(diag_cpl_enganoso(entrada.get("cpl"), entrada.get("cpl_referencia"), cal))
    if entrada.get("gsc"):
        out += [diag_seo_blog(entrada["gsc"]), diag_seo_intencion(entrada["gsc"], entrada.get("marca") or [])]
    ver = veredicto_embudo(cal, ate, ava) if cal else {"veredicto": "sin_dato", "frase": "Sin datos del CRM."}
    peor = "rojo" if any(d["estado"] == "rojo" for d in out) else "ambar" if any(d["estado"] == "ambar" for d in out) else \
        "verde" if any(d["estado"] == "verde" for d in out) else "sin_dato"
    return {"estado": peor, "veredicto_embudo": ver, "diagnosticos": out}

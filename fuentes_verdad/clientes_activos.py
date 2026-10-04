#!/usr/bin/env python3
"""
fuentes_verdad/clientes_activos.py · UN SOLO FILTRO «CLIENTE ACTIVO» (Tomás 3-oct: «veo tareas de Gestymas y FBC sale como
cliente y no lo es»).

Dos cosas en un fichero:

1) GENERADOR (python3 fuentes_verdad/clientes_activos.py). Cruza, solo leyendo:
     · el libro de clientes de Sofía y Tomás (~/Downloads/BAJAS_LTV_CHURN_2026-10-01/clientes.json: 60 activos / 53 bajas a 1-oct),
     · el Airtable de facturación de octubre ya volcado en fuentes_dinero/cuotas.json (SOLO LECTURA),
     · los clientes de la app (data/clientes.json) y la memoria del 1-2 oct (firmas de Think Value y Marlex, Quique en espera),
     · ClickUp (espacio «Clientes INACTIVOS» y carpetas de clientes que ya no lo son) y GoHighLevel (subcuentas sin cliente),
   y escribe:
     data/verdad/estado_clientes.json  activos · bajas (con sus nombres en cada herramienta) · dudosos para Tomás · qué cambia
     data/verdad/bajas_tareas.json     «Tareas de clientes de baja por cerrar» (ClickUp abiertas) + subcuentas de GoHighLevel
                                       y correos de Desk de clientes de baja: SOLO para operaciones (Agus) y dirección, para limpiar.

2) BIBLIOTECA (from fuentes_verdad import clientes_activos as ACT). La usan build_data.py, generar_verdad.py y servir.py:
     ACT.es_baja_id(cid) · ACT.nombra_baja(texto) · ACT.fila_de_baja(fila) · ACT.quitar_bajas(obj, rel) · ACT.limpiar_nucleo(crudo)
   Regla: un cliente de baja NO aparece en pantallas de trabajo (Mi día, Mi trabajo, alertas, buscador, producción, CRM, altas…).
   Su histórico solo en finanzas e informes pasados (HISTORICO). Los dudosos NO se esconden: se listan para Tomás.
"""
import json
import re
import unicodedata
from datetime import date
from pathlib import Path

AQUI = Path(__file__).resolve().parent.parent
DATA = AQUI / "data"
ESTADO = DATA / "verdad" / "estado_clientes.json"
TAREAS_BAJA = DATA / "verdad" / "bajas_tareas.json"
LIBRO = Path.home() / "Downloads" / "BAJAS_LTV_CHURN_2026-10-01" / "clientes.json"

# Ficheros de datos donde el histórico de un cliente de baja SÍ se queda (finanzas e informes pasados) y los de limpieza.
HISTORICO = ("finanzas/", "informes/", "informe/", "dinero_cliente/", "ventas_ro", "verdad/estado_clientes",
             "verdad/bajas_tareas")

# Confirmación directa de Tomás, 3-oct: sigue conectado a Modular, pero ya no es cliente activo.
# Tiene prioridad sobre una captura antigua o una conexión técnica que siga viva.
BAJAS_CONFIRMADAS = {"medalba"}
TIPOS_ACTIVOS = {"activo", "recurrente", "proyecto", "firmado_sin_ficha"}

DEFINICION = ("Cliente activo = tiene línea de octubre en el Airtable de facturación (fuentes_dinero/cuotas.json) o acuerdo firmado "
              "y apuntado por Tomás; el libro de clientes del 1-oct lo confirma («Activo»). Baja = el libro dice «Baja» y no hay "
              "línea de octubre; o está en el espacio «Clientes INACTIVOS» de ClickUp. Lo que no encaja en ninguna, a Tomás.")

# ---------------------------------------------------------------------------------------------- 1 · decisiones a mano
# Cliente de la app → nombre en el libro (razón social). Las equivalencias de nombre comercial ya estaban en build_data.LIBRO_A_MANO
# (confirmadas el 2-oct); aquí se añaden las que faltaban. None = no está en el libro (se explica en «fuente»).
APP_A_LIBRO = {
    "musashi-consultores": "Musashi Consultores", "finexen": "Ignasi Solà Coll", "gac": "GAC Grup", "tribulex": "Tribulex Asesores",
    "emex": "EMEX (Martínez y Jacal)", "laver": "Legal4U", "concilia": "Concilia", "prodegest": "Prodegest", "xterna": "Xterna",
    "sol-4": "Sol-4 Gestion Investment And Consulting", "bonet-asesores": "Organització Bonet Asesores",
    "ecom-advisory": "Strategic Management Business", "greconsult": "Greconsult", "consulting-f": "Consulting F",
    "joan-lluis-vives": "Joan Lluís Vives Economistes", "conficonsulting": "Conficonsulting", "impulsa-cfo": "Impulsa CFO",
    "geslabor": "Geslabor", "lobo": "Lobo Smart", "fusterguell": "FusterGüell", "adade-zaragoza": "Adade Zaragoza",
    "accompany": "Accompany", "centro-consulting": "Centro Consulting (CE Consulting Zaragoza)", "ayg-asesores": "AyG Asesores",
    "kiosko-box": "Kioskobox", "optimalia": "Optimalia", "fitec-asesores": "Asesoría FITECC", "j-d-consulting": "J&D Consulting",
    "oteca": "Oteca Asesores", "aster-asesoria": "Asesoría Aster", "busbac": "Busbac Serveis", "aselegal": "AseLegal",
    "proincentiva": "Proincentiva", "mg-economistes": "MG Economistes", "asetra": "Asetra Asesoría",
    "torrevieja-consult": "Torrevieja Consult", "imfor-asesores": "Imfor Asesores", "billeo": "Grupo Billeo",
    "tst-consulting": "TST Consulting", "agc": "AGC", "cib-partners": "CIB Partners", "abner-advisory": "Abner Advisory",
    "gestio-plural": "Gold Global Projects", "deudot": "Deudout", "garmande": "Garmande", "sintaer": "Sintaer",
    "gomez-y-carvacho": "Gema Mishel García Gómez", "liebana-consulting": "Fermín Liébana Casellas",
    "volatt": "Volatt Jurídico Y Fiscal", "ip-forense": "IP Forense", "gestanex": "Gestanex Solutions",
    "christian-sanchez": "Christian Sánchez Sánchez", "segu-assessors": "Segú Assessors", "ahedo": "AHEDO", "bit-24": "Bit24",
    "orejana": "Orejana Gestión Emprendedora", "romero-martinez": "Romero Martínez Asesores", "akua": "Productikaonline",
    "innova-scala": "Innova Scala Consulting", "ecija-advisory": "E Advisory", "avantik": "AVANTIK", "octoedro": "Octoedro",
    "jenasa": "Jesús Navarro Consultores Asesores", "campalans": "Campalans Assesorament I Gestió", "pgb-auditores": "PG Business Audit",
    "quique-gomez-barreda": None, "marlex-consulting": None, "think-value": None,
}
# Firmados después del libro (1-oct) o en espera: fuente escrita.
FUERA_DEL_LIBRO = {
    "quique-gomez-barreda": ("pendiente_factura", "Libro de clientes, pestaña «Pendientes»: «EN ESPERA · cliente nuevo; entra como alta cuando se le facture» (Tomás, 1-oct)."),
    "marlex-consulting": ("firmado_sin_ficha", "Acuerdo FIRMADO el 1-oct (memoria «Prospecto Alex · Marlex Consulting»); en cuotas.json: «Acuerdo firmado, aún sin ficha en Airtable»."),
    "think-value": ("firmado_sin_ficha", "Acuerdo FIRMADO el 1-oct (memoria «THINK VALUE · acuerdo 1-oct»); en cuotas.json: «Acuerdo firmado, aún sin ficha en Airtable»."),
}
# Dudosos: NO se esconden; se preguntan a Tomás (sin adivinar).
DUDOSOS_APP = {
    "campalans": ("¿Campalans es cliente de agencia o solo extras sueltos?",
                  "El libro lo clasifica como «Extras sueltos» (no entra en los 60 activos). Sin línea de octubre en Airtable ni factura de octubre. En ClickUp está en «Clientes one-shot» con 10 tareas abiertas."),
    "pgb-auditores": ("¿PGB Auditores (PG Business Audit) sigue con nosotros?",
                      "El libro lo clasifica como «Proyecto» desde el 15-jul (1.470 € en total). Sin línea de octubre en Airtable. En ClickUp sigue en «Clientes mensuales» con tareas abiertas."),
    "jenasa": ("¿JENASA sigue activo?",
               "Airtable le pone 2.500 € en octubre (proyecto con fin) y el libro lo da como «Proyecto», pero en ClickUp su carpeta está en el espacio «Clientes INACTIVOS»."),
}
# Nombres con los que sale cada BAJA en las herramientas (ClickUp, GoHighLevel, Desk, SE Ranking). «frase» = el texto lo contiene
# (palabra entera); «exacto» = el campo es exactamente eso (para palabras que podrían ser otra cosa: «Gestiona»).
ALIAS_BAJA = {
    "Gestoría Administrativa Gestymas": {"frase": ["gestymas", "gestimash", "gestimas"]},
    "Fbc Euroconsulting": {"frase": ["fbc euroconsulting", "fbceuroconsulting", "fbc euro consulting"]},
    "Power Global Innovation (Taller del Patinete)": {"frase": ["power global innovation", "taller del patinete"]},
    "QualityConta": {"frase": ["qualityconta", "quality conta"]},
    "CLCripto": {"frase": ["clcripto", "cl cripto"]},
    "Oficina Técnico Empresarial": {"frase": ["oficina tecnico empresarial", "fin2go"]},
    "Nubba Spaces": {"frase": ["nubba"]},
    "Personal Investment Advisors": {"frase": ["personal investment advisors"]},
    "Fomento De Formacion Y Proteccion": {"frase": ["fomento de formacion"]},
    "Medalva Ae": {"frase": ["medalva"]},
    "Gestoría Pardo Domínguez": {"frase": ["pardo dominguez"]},
    "A R Montis Tax Consultancy": {"frase": ["montis tax", "ar montis", "a r montis"]},
    "Adana Logística Y Transporte": {"frase": ["adana logistica"]},
    "GEMAP": {"frase": ["gemap"]},
    "Juliet Ramirez Hair Studio": {"frase": ["juliet ramirez"]},
    "Assessoria Vallparadis": {"frase": ["vallparadis"]},
    "Marvin Abogados Y Asesores": {"frase": ["marvin abogados"]},
    "Circula Software Empresa": {"frase": ["circula software"]},
    "Adoria Symmetry": {"frase": ["adoria"]},
    "Euro Lucas 21": {"frase": ["euro lucas"]},
    "Volatt Jurídico Y Fiscal": {"frase": ["volatt"]},
    "Tributaley Nova Gestion": {"frase": ["tributaley"]},
    "Asesores Otefisa": {"frase": ["otefisa"]},
    "Bifan Iberica Seguridad": {"frase": ["bifan"]},
    "Emlb Asociados": {"frase": ["emlb"]},
    "Ise Asesores": {"frase": ["ise asesores"]},
    "Benesit Health": {"frase": ["benesit"]},
    "Fincas Lamas": {"frase": ["fincas lamas", "asesoria lamas"]},
    "Barreda Diaz Asesores": {"frase": ["barreda diaz"]},
    "Euro Gestiona R&M": {"frase": ["euro gestiona"], "exacto": ["gestiona"]},
    "Servicios Juridicos Y Administracion Grupo Ropasa": {"frase": ["ropasa"]},
    "Uhy Fay & Co Auditores Asesores": {"frase": ["uhy fay", "uhy"]},
    "Bob Legal & Tax": {"frase": ["bob legal"]},
    "Alfonso Benavides Y Asociados": {"frase": ["alfonso benavides", "benavides asociados"]},
    "Palacios Díaz Consultores": {"frase": ["palacios diaz"]},
    "Lara y Marcos Asesores": {"frase": ["lara y marcos", "lara marcos"]},
    "Ferpec Asesoramiento": {"frase": ["ferpec"]},
    "Upbizor Svc": {"frase": ["upbizor"]},
    "Alvaro Anglada Associats": {"frase": ["alvaro anglada"]},
    "Sapientia Asesores Y Consultores": {"frase": ["sapientia"]},
    "March De Luque Servicios": {"frase": ["march de luque"]},
    "Alvarez Y Gismera Asesores": {"frase": ["gismera"]},
    "COFM Servicios 31": {"frase": ["cofm"]},
    "Asetra Proyectos Inmobiliarios": {"frase": ["asetra proyectos"]},
    "Montserrat Díaz Marí": {"frase": ["montserrat diaz mari"]},
    "Club De La Pyme Servicios Globales": {"frase": ["club de la pyme"]},
    "Algesa Inversiones": {"frase": ["algesa"]},
    "Vefusgem (Vegas Legal)": {"frase": ["vefusgem", "vegas legal"]},
    "Construcciones Y Decoraciones Vilaplana": {"frase": ["vilaplana"]},
    "Scando-Up Global Legal": {"frase": ["scando up", "scandoup"]},
    "OCPS & Tarinas": {"frase": ["ocps tarinas", "ocps & tarinas", "grup ocps"]},
    "Fersan Asesoria Integral": {"frase": ["fersan"]},
    "Firenzia Asesoría De Empresas": {"frase": ["firenzia"]},
}
# Carpetas de ClickUp del espacio «Clientes INACTIVOS» que no están en el libro: ClickUp ya las da por inactivas (fuente).
INACTIVOS_CLICKUP_EXTRA = {"Pummba": {"frase": ["pummba"]}}


# ---------------------------------------------------------------------------------------------- 2 · utilidades
def norm(s):
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z0-9&]+", " ", s)
    s = re.sub(r"^\d{3,}\s+", "", s.strip())          # «28925 FBC EUROCONSULTING» → «fbc euroconsulting»
    return re.sub(r"\s+", " ", s).strip()


def _leer(p, defecto=None):
    try:
        return json.loads(Path(p).read_text())
    except Exception:
        return defecto


_CACHE = {"marca": None, "estado": None}


def estado():
    """data/verdad/estado_clientes.json (se relee solo si cambia en disco)."""
    try:
        st = ESTADO.stat()
        marca = (st.st_mtime_ns, st.st_size)
    except OSError:
        marca = None
    if marca is None:
        return {"bajas_ids": [], "bajas": [], "activos": [], "dudosos": [],
                "_ids": set(BAJAS_CONFIRMADAS), "_activos": set(), "_no_operativos": set(BAJAS_CONFIRMADAS),
                "_rx": re.compile(r"(?:^| )medalba(?: |$)"), "_compactos": ["medalba"], "_exactos": {"medalba"},
                "_nombres_no_operativos": {"medalba"}}
    if _CACHE["marca"] != marca:
        e = _leer(ESTADO, {}) or {}
        frases, exactos = [], set()
        for b in e.get("bajas", []):
            for a in (b.get("alias") or {}).get("frase", []):
                frases.append(norm(a))
            for a in (b.get("alias") or {}).get("exacto", []):
                exactos.add(norm(a))
        frases = sorted({f for f in frases if f} | BAJAS_CONFIRMADAS, key=len, reverse=True)
        e["_rx"] = re.compile(r"(?:^| )(" + "|".join(re.escape(f) for f in frases) + r")(?: |$)") if frases else None
        e["_compactos"] = [f.replace(" ", "") for f in frases if len(f.replace(" ", "")) >= 6]
        e["_exactos"] = exactos | BAJAS_CONFIRMADAS
        e["_ids"] = set(e.get("bajas_ids") or []) | BAJAS_CONFIRMADAS
        e["_activos"] = {a["id"] for a in e.get("activos", []) if a.get("id")
                         and a.get("tipo") in TIPOS_ACTIVOS and a["id"] not in e["_ids"]}
        e["_no_operativos"] = e["_ids"] | {a["id"] for a in e.get("activos", [])
                                                   if a.get("id") and a["id"] not in e["_activos"]}
        e["_nombres_no_operativos"] = {norm(a.get("nombre")) for a in e.get("activos", [])
                                      if a.get("id") in e["_no_operativos"]} | {norm(cid) for cid in e["_no_operativos"]}
        _CACHE.update(marca=marca, estado=e)
    return _CACHE["estado"]


def es_baja_id(cid):
    return bool(cid) and cid in estado()["_ids"]


def es_activo_id(cid):
    """Sólo la pertenencia confirmada al catálogo habilita trabajo operativo."""
    return isinstance(cid, str) and cid in estado()["_activos"]


def nombra_baja(texto, compacto=False):
    """El nombre de la baja que aparece en el texto (o None). compacto=True para dominios («fbceuroconsulting.es»)."""
    e = estado()
    t = norm(texto)
    if not t:
        return None
    if t in e["_exactos"]:
        return t
    if e["_rx"] is not None:
        m = e["_rx"].search(t)
        if m:
            return m.group(1)
    if compacto:
        tc = t.replace(" ", "")
        return next((c for c in e["_compactos"] if c in tc), None)
    return None


# Campos de una fila que dicen DE QUÉ CLIENTE es. «nombre»/«titulo» solo cuentan si la fila parece de cliente/subcuenta/proyecto.
CAMPOS_CLIENTE = ("cliente", "cliente_nombre", "nombre_cliente", "cliente_hoja", "subcuenta", "nombre_sub", "carpeta", "lista",
                  "cuenta", "marca", "empresa", "organizacion", "cli")
CAMPOS_DOMINIO = ("dominio", "dominio_cliente")


def fila_de_baja(x):
    """True si la fila (dict) es de un cliente de baja: por cliente_id/cid, por el nombre del cliente o por su dominio."""
    if not isinstance(x, dict):
        return False
    if any(x.get(k) not in (None, "") and not es_activo_id(x.get(k)) for k in ("cliente_id", "cid", "cli")):
        return True
    for k in CAMPOS_CLIENTE:
        v = x.get(k)
        if isinstance(v, str) and (norm(v) in estado()["_nombres_no_operativos"] or nombra_baja(v)):
            return True
    for k in CAMPOS_DOMINIO:
        v = x.get(k)
        if isinstance(v, str) and nombra_baja(v, compacto=True):
            return True
    # Filas de subcuenta / proyecto / cliente sin campo «cliente»: «nombre» o «titulo» exactamente el de la baja
    if ("sub_id" in x or "loc" in x or "id" in x) and any(isinstance(x.get(k), str) and _exacto_baja(x[k]) for k in ("nombre", "titulo")):
        return True
    return False


def _exacto_baja(v):
    e = estado()
    t = norm(v)
    return bool(t) and (t in e["_exactos"] or (e["_rx"] is not None and bool(e["_rx"].fullmatch(t))) or es_baja_id(v))


def es_historico(rel):
    return any(str(rel or "").startswith(h) for h in HISTORICO)


def quitar_bajas(obj, rel=None):
    """Quita, a cualquier profundidad, las filas de clientes de baja y las claves que son su id. Nada si rel es histórico."""
    if es_historico(rel):
        return obj

    def paso(o):
        if isinstance(o, list):
            return [paso(v) for v in o if not fila_de_baja(v) and not (isinstance(v, str) and (v in estado()["_no_operativos"] or _exacto_baja(v)))]
        if isinstance(o, dict):
            return {k: paso(v) for k, v in o.items() if k not in estado()["_no_operativos"] and not _exacto_baja(k)}
        return o
    out = paso(obj)
    if rel == "verdad/clientes" and isinstance(out, dict) and isinstance(out.get("comun"), list):
        #201: esta lista es de CLIENTES por contrato, no ids genéricos de personas/tareas.
        # Pendiente/dudoso/desconocido no habilita un cliente por su nombre comercial.
        out["comun"] = [r for r in out["comun"] if isinstance(r, dict) and es_activo_id(r.get("id")) is True]
        from proyeccion_agregados_activos import verdad
        out = verdad(out)
    if rel == "crm/crm" and isinstance(out, dict) and isinstance(out.get("subcuentas"), list):
        #201: una subcuenta técnica sin cliente no acredita una cartera operativa.
        # Prueba/interna siguen como diagnóstico explícito, nunca como cliente inferido.
        out["subcuentas"] = [r for r in out["subcuentas"] if isinstance(r, dict)
                             and (r.get("tipo") in ("prueba", "interna") or es_activo_id(r.get("cliente_id")) is True)]
        from proyeccion_agregados_activos import crm
        out = crm(out)
    if rel == "mi_trabajo/mi_trabajo":
        #180: catálogo y referencias auxiliares sólo de las tareas realmente devueltas.
        from mi_trabajo_proyeccion import recortar
        out = recortar(out)
    return out


def limpiar_nucleo(crudo):
    """servir.py · los datos base (clientes, asignaciones, alarmas, logos) sin clientes de baja. Devuelve los ids quitados."""
    ids = {c["id"] for c in crudo.get("clientes", []) if not es_activo_id(c["id"])}
    fuera = sorted(ids)
    crudo["clientes"] = [c for c in crudo.get("clientes", []) if es_activo_id(c["id"])]
    for c in crudo["clientes"]:
        c["activo_confirmado"] = True
    if isinstance(crudo.get("asignaciones"), list):
        crudo["asignaciones"] = [a for a in crudo["asignaciones"] if es_activo_id(a.get("cliente_id"))]
    if isinstance(crudo.get("alarmas"), list):
        crudo["alarmas"] = [a for a in crudo["alarmas"] if not a.get("cliente_id") or es_activo_id(a["cliente_id"])]
    if isinstance(crudo.get("logos"), dict):
        crudo["logos"] = {k: v for k, v in crudo["logos"].items() if k not in ids}
    return fuera


# ---------------------------------------------------------------------------------------------- 3 · generador
def _donde_sale(aliases_por_baja):
    """Ficheros de data/ (pantallas de trabajo) donde sale cada baja HOY, antes del filtro: la prueba de «salía como cliente»."""
    out = {}
    for f in sorted(DATA.rglob("*.json")):
        rel = str(f.relative_to(DATA))
        if "_privado" in rel or rel.startswith("verdad/") or rel.startswith("logos"):
            continue
        try:
            t = norm(f.read_text(errors="ignore")[:4_000_000])
        except Exception:
            continue
        for m in set(_RX_TODAS[0].findall(t)):
            nombre = _RX_TODAS[1].get(m)
            if nombre:
                out.setdefault(nombre, set()).add(rel.split("/")[0].replace(".json", ""))
    return {k: sorted(v) for k, v in out.items()}


_RX_TODAS = [None, {}]


def main():
    hoy = date.today().isoformat()
    libro = _leer(LIBRO, {}) or {}
    cuotas = (_leer(AQUI / "fuentes_dinero" / "cuotas.json", {}) or {}).get("cuotas", {})
    clientes = _leer(DATA / "clientes.json", []) or []
    # Si data/clientes.json ya está filtrado, los clientes quitados siguen saliendo en la lista con su motivo (estado anterior).
    previo = _leer(ESTADO, {}) or {}
    por_libro = {(v.get("cliente") or k): v for k, v in libro.items()}

    activos, bajas_app, dudosos = [], [], []
    vistos_libro = set()
    for c in clientes + [{"id": b["cliente_id"], "nombre": b["nombre_app"]} for b in previo.get("bajas", []) if b.get("cliente_id")
                         and b["cliente_id"] not in {x["id"] for x in clientes}]:
        cid = c["id"]
        nombre_libro = APP_A_LIBRO.get(cid, "??")
        v = por_libro.get(nombre_libro) if nombre_libro else None
        if nombre_libro:
            vistos_libro.add(nombre_libro)
        q = cuotas.get(cid) or {}
        linea_oct = q.get("cuota") is not None and "Airtable" in (q.get("fuente") or "")
        fuente_air = f"Airtable de octubre (fuentes_dinero/cuotas.json): {q.get('fuente') or 'sin línea'}"
        if cid in DUDOSOS_APP:
            preg, sabemos = DUDOSOS_APP[cid]
            dudosos.append({"cliente_id": cid, "nombre": c["nombre"], "pregunta": preg, "lo_que_sabemos": sabemos,
                            "mientras": "Sigue saliendo como hasta ahora (no se esconde sin tu respuesta).",
                            "fuentes": [f"Libro de clientes 1-oct: «{(v or {}).get('estado') or 'no está'}»", fuente_air]})
            activos.append({"id": cid, "nombre": c["nombre"], "tipo": "dudoso", "fuente": "pendiente de Tomás"})
            continue
        if cid in FUERA_DEL_LIBRO:
            tipo, f = FUERA_DEL_LIBRO[cid]
            activos.append({"id": cid, "nombre": c["nombre"], "tipo": tipo, "fuente": f})
            continue
        est = (v or {}).get("estado")
        if est == "Baja" and not linea_oct:
            bajas_app.append({"cliente_id": cid, "nombre_app": c["nombre"], "nombre_libro": nombre_libro, "fecha_baja": v.get("fecha_baja"),
                              "fuente": f"Libro de clientes 1-oct: «Baja», último día {v.get('fecha_baja')} ({v.get('fuente_baja') or 'sin nota'}); "
                                        f"{fuente_air}."})
            continue
        if est == "Activo" or linea_oct:
            tipo = "proyecto" if "proyecto" in (q.get("fuente") or "").lower() or est == "Proyecto" else "recurrente"
            activos.append({"id": cid, "nombre": c["nombre"], "tipo": tipo, "libro": nombre_libro,
                            "fuente": f"Libro de clientes 1-oct: «{est or 'no está'}» como «{nombre_libro}»; {fuente_air}."})
            continue
        dudosos.append({"cliente_id": cid, "nombre": c["nombre"], "pregunta": f"¿{c['nombre']} es cliente activo?",
                        "lo_que_sabemos": f"No encaja: libro «{est or 'no está'}», {fuente_air}.", "mientras": "Sigue saliendo.",
                        "fuentes": [str(LIBRO), "fuentes_dinero/cuotas.json"]})
        activos.append({"id": cid, "nombre": c["nombre"], "tipo": "dudoso", "fuente": "pendiente de Tomás"})

    # Activos del libro que no están en la app (los que faltaban)
    faltaban = [{"nombre_libro": n, "cuota_octubre": v.get("cuota_actual"), "fuente": "Libro de clientes 1-oct: «Activo»"}
                for n, v in por_libro.items() if v.get("estado") == "Activo" and n not in vistos_libro]

    # Todas las bajas del libro (53) + las de ClickUp «Clientes INACTIVOS» que no están en el libro
    bajas = []
    ids_baja = {b["nombre_libro"]: b["cliente_id"] for b in bajas_app}
    for n, v in por_libro.items():
        if v.get("estado") != "Baja":
            continue
        alias = ALIAS_BAJA.get(n) or {"frase": [norm(n)]}
        bajas.append({"nombre": n, "cliente_id": ids_baja.get(n), "fecha_baja": v.get("fecha_baja"), "alias": alias,
                      "fuente": f"Libro de clientes 1-oct («Baja», último día {v.get('fecha_baja')}): {v.get('fuente_baja') or v.get('motivo') or ''}".strip()})
    for n, alias in INACTIVOS_CLICKUP_EXTRA.items():
        bajas.append({"nombre": n, "cliente_id": None, "fecha_baja": None, "alias": alias,
                      "fuente": "ClickUp: su carpeta está en el espacio «Clientes INACTIVOS» (no está en el libro de clientes)."})
    # One-shots del libro: no son clientes de agencia (sus tareas abiertas también van a la lista de limpieza)
    oneshots = [n for n, v in por_libro.items() if v.get("estado") == "One-shot"]

    estado_out = {
        "generado": hoy, "definicion": DEFINICION,
        "fuentes": [{"que": "Libro de clientes (Sofía y Tomás, 1-oct)", "ruta": str(LIBRO)},
                    {"que": "Excel de bajas, LTV y churn", "ruta": str(LIBRO.parent / "LTV_BAJAS_CHURN_RO_2026-10-01.xlsx")},
                    {"que": "Airtable de facturación de octubre (solo lectura)", "ruta": "fuentes_dinero/cuotas.json"},
                    {"que": "ClickUp (espacios y carpetas)", "ruta": "fuentes_produccion/_privado/_cache/tareas.json"},
                    {"que": "GoHighLevel (subcuentas)", "ruta": "data/crm/crm.json"}],
        "historico_en": list(HISTORICO),
        "resumen": {"activos": sum(1 for a in activos if a["tipo"] != "dudoso"), "dudosos": len(dudosos),
                    "bajas_quitadas_de_la_app": len(bajas_app), "bajas_conocidas": len(bajas), "faltaban": len(faltaban)},
        "activos": activos, "bajas_ids": sorted(b["cliente_id"] for b in bajas_app), "bajas_app": bajas_app,
        "bajas": bajas, "dudosos": dudosos, "faltaban": faltaban, "one_shots_libro": oneshots,
    }
    ESTADO.parent.mkdir(parents=True, exist_ok=True)
    tmp = ESTADO.with_suffix(".tmp")
    tmp.write_text(json.dumps(estado_out, ensure_ascii=False, indent=1))
    tmp.replace(ESTADO)
    _CACHE["marca"] = None

    # ------------------------------------------------ dónde salía cada baja (antes del filtro) → lista de «salían como cliente»
    alias_a_baja = {norm(a): b["nombre"] for b in bajas for a in (b["alias"].get("frase") or []) if norm(a)}
    _RX_TODAS[0] = re.compile(r"(?<![a-z0-9])(" + "|".join(re.escape(f) for f in sorted(alias_a_baja, key=len, reverse=True)) + r")(?![a-z0-9])")
    _RX_TODAS[1] = alias_a_baja
    donde = _donde_sale(None)
    salian = []
    for b in bajas:
        d = [x for x in donde.get(b["nombre"], []) if not es_historico(x + "/")]
        if d or b.get("cliente_id"):
            salian.append({"nombre": b["nombre"], "cliente_id": b.get("cliente_id"), "fecha_baja": b.get("fecha_baja"),
                           "salia_en": d + (["lista de clientes de la app"] if b.get("cliente_id") else []), "fuente": b["fuente"]})

    # ------------------------------------------------ tareas de clientes de baja por cerrar (ClickUp) + subcuentas GHL + Desk
    t = _leer(AQUI / "fuentes_produccion" / "_privado" / "_cache" / "tareas.json", {}) or {}
    cerradas = {"closed", "done"}
    tareas, oneshot_abiertas = [], {}
    for x in t.get("tareas", []):
        if x.get("tipo_estado") in cerradas:
            continue
        carpeta, lista, espacio = x.get("carpeta") or "", x.get("lista") or "", x.get("espacio") or ""
        baja = nombra_baja(carpeta) or nombra_baja(lista)
        motivo = None
        if baja:
            motivo = "cliente de baja (libro de clientes)"
        elif espacio == "Clientes INACTIVOS" and carpeta and not any(norm(carpeta) == norm(d) for d in ("jenasa",)):
            baja, motivo = norm(carpeta), "carpeta en «Clientes INACTIVOS» de ClickUp"
        elif espacio == "Clientes one-shot" and carpeta and norm(carpeta) not in ("ip forense", "gestoria campalans", "optimalia"):
            baja, motivo = norm(carpeta), "one-shot (no es cliente de agencia): pregunta a Tomás si se cierran"
            oneshot_abiertas.setdefault(carpeta, 0)
            oneshot_abiertas[carpeta] += 1
        if not baja:
            continue
        tareas.append({"id": x["id"], "tarea": x.get("nombre"), "url": x.get("url"), "estado": x.get("estado"),
                       "vence": _fecha_ms(x.get("vence")), "creada": _fecha_ms(x.get("creada")),
                       "carpeta": carpeta, "lista": lista, "espacio": espacio, "motivo": motivo,
                       "asignados": [a.get("nombre") for a in x.get("asignados") or [] if a.get("nombre")]})
    tareas.sort(key=lambda r: (r["carpeta"], r["vence"] or "9999"))
    por_carpeta = {}
    for r in tareas:
        por_carpeta.setdefault(r["carpeta"], 0)
        por_carpeta[r["carpeta"]] += 1
    crm = _leer(DATA / "crm" / "crm.json", {}) or {}
    subcuentas = [{"sub_id": s.get("sub_id"), "nombre": s.get("nombre"), "baja": nombra_baja(s.get("nombre")) or (norm(s.get("nombre")) if _exacto_baja(s.get("nombre")) else None)}
                  for s in crm.get("subcuentas", []) if not s.get("cliente_id") and s.get("tipo") == "sin_cliente"]
    sub_baja = [s for s in subcuentas if s["baja"]]
    sub_dudosas = [s for s in subcuentas if not s["baja"]]
    band = _leer(DATA / "bandeja" / "bandeja.json", {}) or {}
    correos = {}
    for c in band.get("correos", []):
        b = nombra_baja(c.get("dominio"), compacto=True) or nombra_baja(c.get("cliente"))
        if b:
            correos.setdefault(b, 0)
            correos[b] += 1
    tareas_out = {
        "generado": hoy, "para": "Operaciones (Agus) y dirección: limpiar en ClickUp, GoHighLevel y Desk lo que queda de clientes que ya no lo son. La app no escribe en ninguna herramienta.",
        "definicion": DEFINICION,
        "resumen": {"tareas": len(tareas), "carpetas": len(por_carpeta), "subcuentas_ghl": len(sub_baja), "correos_desk": sum(correos.values())},
        "por_carpeta": [{"carpeta": k, "tareas": v} for k, v in sorted(por_carpeta.items(), key=lambda kv: -kv[1])],
        "tareas": tareas, "subcuentas_ghl": sub_baja,
        "correos_desk": [{"cliente": k, "correos": v} for k, v in sorted(correos.items(), key=lambda kv: -kv[1])],
        "fuente": "ClickUp (fuentes_produccion/_privado/_cache/tareas.json, " + str((t.get("meta") or {}).get("generado")) + "), GoHighLevel (data/crm/crm.json), Desk (data/bandeja/bandeja.json)",
    }
    tmp = TAREAS_BAJA.with_suffix(".tmp")
    tmp.write_text(json.dumps(tareas_out, ensure_ascii=False, indent=1))
    tmp.replace(TAREAS_BAJA)

    for carpeta, n in sorted(oneshot_abiertas.items()):
        dudosos.append({"cliente_id": None, "nombre": carpeta, "pregunta": f"{carpeta}: trabajo one-shot con {n} tareas abiertas en ClickUp. ¿Está terminado (se cierran) o sigue?",
                        "lo_que_sabemos": "En ClickUp está en «Clientes one-shot»; no es cliente de agencia en el libro de clientes. Sus tareas salen en la lista de limpieza marcadas como «pregunta a Tomás».",
                        "mientras": "Sus tareas siguen saliendo a quien las tiene asignadas.", "fuentes": ["ClickUp", str(LIBRO)]})
    estado_out["resumen"]["dudosos"] = len(dudosos)
    estado_out["salian_como_cliente"] = salian
    estado_out["subcuentas_ghl_sin_cliente_dudosas"] = [{"nombre": s["nombre"], "sub_id": s["sub_id"],
                                                         "pregunta": "Subcuenta de GoHighLevel sin cliente en la app y que no está en el libro: ¿de quién es?"}
                                                        for s in sub_dudosas]
    tmp = ESTADO.with_suffix(".tmp")
    tmp.write_text(json.dumps(estado_out, ensure_ascii=False, indent=1))
    tmp.replace(ESTADO)
    _CACHE["marca"] = None
    print(f"clientes activos: {estado_out['resumen']['activos']} · dudosos {len(dudosos)} · bajas quitadas de la app {len(bajas_app)} "
          f"({', '.join(b['nombre_app'] for b in bajas_app)}) · bajas conocidas {len(bajas)} · salían en pantallas de trabajo {len(salian)} · "
          f"tareas de baja por cerrar {len(tareas)} en {len(por_carpeta)} carpetas · subcuentas GHL de baja {len(sub_baja)} · faltaban {len(faltaban)}")


def _fecha_ms(v):
    try:
        from datetime import datetime, timezone
        return datetime.fromtimestamp(int(v) / 1000, tz=timezone.utc).date().isoformat() if v else None
    except Exception:
        return None


if __name__ == "__main__":
    main()

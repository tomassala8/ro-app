#!/usr/bin/env python3
"""
build_data.py · convierte los datos del panel v27 y la fase 0 en los JSON del prototipo.

Lee (solo lectura):
  ~/Downloads/PANEL_OPERACIONES_2026-10-01/build/datos.json        clientes, alarmas, salud
  ~/Downloads/PANEL_OPERACIONES_2026-10-01/build/portal_logos.json  logos en data URI
  ../20_FASE0_DATOS/personas.json, asignaciones.json, dudas.md       quién es quién y quién lleva qué (E0)
  ../20_FASE0_DATOS/respuestas_mili.json                             OPCIONAL: respuestas de Mili a las dudas;
                                                                     si existe, corrige asignaciones y personas
  ~/Downloads/BAJAS_LTV_CHURN_2026-10-01/clientes.json               libro de clientes (D-16), solo para cotejar
  reglas_permisos.json                                               equivalencias de puestos

Escribe en ./data/:
  clientes.json        clientes (panel + los del portal que el panel no tiene), con equipo, servicios y
                       la marca «sin_account»; sin teléfonos, correos ni contactos
  alarmas.json         alarmas por cliente y por persona, con textos saneados
  logos.json           id de cliente -> logo (data URI)
  personas.json        lista de personas con los 21 puestos de la app (varios por persona)
  asignaciones.json    cliente × persona × silla, con fuente, confianza y suplencias
  para_confirmar.json  las dudas de 20_FASE0_DATOS/dudas.md, estructuradas para «Ajustes › Para confirmar»
  ids_clientes.json    id del portal (fase 0) -> id de la app, y cotejo con el libro de clientes
  meta.json            fecha de generación, frescura por fuente, resumen e histórico

Uso:  python3 build_data.py
No toca ninguna herramienta externa ni modifica los ficheros de origen.
NO escribe en data/clientes/ ni en fuentes/ (son de E1).
"""
import json
import re
import unicodedata
from datetime import date, timedelta
from pathlib import Path

AQUI = Path(__file__).resolve().parent
import config  # noqa: E402 · C5: rutas en config.py
PANEL = config.PANEL_BUILD
LIBRO = config.LIBRO_CLIENTES
FASE0 = AQUI.parent / "20_FASE0_DATOS"
SALIDA = AQUI / "data"
REGLAS = json.loads((AQUI / "reglas_permisos.json").read_text())
PUESTOS_APP = {p["id"] for p in REGLAS["puestos"]}


RE_IMPORTE_DESC = re.compile(r"\d[\d.,]*\s*(?:€|euros?|EUR\b)|€\s*\d[\d.,]*")


def descripciones(texto):
    """Ronda 12 (R13): como la ficha (portal.json). «descripcion» corta y sin importes (la ve cualquiera con detalle) y
    «descripcion_completa» con el texto entero solo si lleva importes (el servidor la recorta: sin_importes)."""
    if not texto or not RE_IMPORTE_DESC.search(texto):
        return texto, None
    corta = re.sub(r"\s*\([^()]*\)", lambda m: "" if RE_IMPORTE_DESC.search(m.group(0)) else m.group(0), texto).strip(" ,;:·-–—")
    if RE_IMPORTE_DESC.search(corta):
        import permisos as _P
        corta = _P.sin_importes(corta)
    return (corta or None), texto


def slug(texto):
    t = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")


def norm(texto):
    return slug(texto).replace("-", " ")


# V2-E (40_B B3): nombres de cliente que llegan sin tilde de la fuente (panel v27); el id (slug) no cambia.
NOMBRES_CON_TILDE = {"Quique Gomez Barreda": "Quique Gómez Barreda"}


def con_tildes(nombre):
    return NOMBRES_CON_TILDE.get(nombre, nombre)


# ---------------------------------------------------------------- saneado
RE_CORREO = re.compile(r"[\w.+-]+@[\w-]+(\.[\w-]+)+")
RE_NUMERO = re.compile(r"\+?\d[\d\s.\-]{7,}\d")


def sanear(texto):
    """Quita correos y teléfonos de un texto libre (deja fechas e importes)."""
    if not texto:
        return texto
    texto = RE_CORREO.sub("[correo oculto]", texto)

    def tel(m):
        s = m.group(0)
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s.strip()):
            return s
        digitos = re.sub(r"\D", "", s)
        return "[teléfono oculto]" if 9 <= len(digitos) <= 13 else s

    return RE_NUMERO.sub(tel, texto)


# ------------------------------------------------- textos para la interfaz (ronda 5, I-03)
RE_CODIGOS = re.compile(r"\s*\((?:[A-Z]{1,2}-?[A-Z]?\d+[a-z]?(?:[,·/ y]+)?)+\)|\b(?:D|G|W|C|E|M|P|B|I)-?[A-Z]{0,2}\d{1,3}\b(?:\s*§\s*\d+)?")
RE_FICHERO = re.compile(r"\b[\w./-]+\.(?:json|py|md|js|csv|xlsx)\b")


def limpia_texto(t):
    """Igual que limpiaTexto() de componentes.js: fuera códigos internos (D-29, G2, W3, C-D3…), nombres de fichero,
    ⭐ y ⚠️. Los códigos se pueden enseñar en un «¿de dónde sale?» plegado, nunca en el texto visible."""
    if not isinstance(t, str) or not t:
        return t
    # Lo que va entre «» es texto del cliente (asunto de un correo, nombre de una tarea): no se toca.
    trozos = re.split(r"(«[^»]*»)", t)
    if len(trozos) > 1:
        return "".join(x if x.startswith("«") else _limpia(x) for x in trozos).strip()
    return _limpia(t)


def _limpia(t):
    t = RE_FICHERO.sub("", t)
    t = RE_CODIGOS.sub("", t)
    t = t.replace("⭐", "").replace("⚠️", "").replace("⚠", "")
    t = re.sub(r"\(\s*\)", "", t)
    return re.sub(r"\s{2,}", " ", t).strip(" ·,;")


# ------------------------------------------------- personas (semilla del 00)
# Solo se usa si no existe 20_FASE0_DATOS/personas.json.
SEMILLA_PERSONAS = [
    ("Tomás Sala", "Tomás", ["direccion", "finanzas_direccion", "ventas_ro"]),
    ("Sofía", "Sofía", ["administracion"]),
    ("Milagros", "Mili", ["operaciones"]),
    ("Coti", "Coti", ["proyectos"]),
    ("Cecilia Belotto", "Cecilia", ["rrhh"]),
    ("Lucia Caso", "Lucía", ["account"]),
    ("Carla Valentino", "Carla", ["account"]),
    ("Casiana Miranda", "Casiana", ["account"]),
    ("Facundo", "Facundo", ["account"]),
    ("Natalia Calvete", "Natalia", ["account"]),
    ("Candela Almeida", "Candela", ["account"]),
    ("Dana Rolleri", "Dana", ["account"]),
    ("Agustina Alegre", "Agus", ["tecnico_altas", "account"]),
    ("Valeria Torres", "Valeria", ["jefa_publicidad"]),
    ("Yessica Tovar", "Jessi", ["jefa_crm", "outreach"]),
    ("Constanza Bravin", "Constanza", ["jefa_seo"]),
]


# Ronda 5 (revisión de calidad P-06): UN nombre corto por persona en toda la app. Nombre de pila, salvo los
# apodos que usa Tomás por escrito (plan v2, R12). «Jessi» no se usa hasta que Tomás lo confirme: hoy, «Yessica».
APODOS = {"mili": "Mili", "constanza": "Coti", "agustina": "Agus"}
NOMBRES_COMPUESTOS = ("Juan Manuel",)


def alias_corto(p):
    """Nombre corto único para la interfaz (ver APODOS). Si dos personas comparten nombre de pila, normalizar_personas
    añade la inicial del apellido."""
    if p["id"] in APODOS:
        return APODOS[p["id"]]
    nombre = p.get("nombre") or p["id"]
    for comp in NOMBRES_COMPUESTOS:
        if nombre.startswith(comp):
            return comp
    return nombre.split()[0]


def desambiguar(personas):
    """Si dos personas (no setters de prueba) tienen el mismo alias, se añade la inicial del primer apellido: «Carlos V.»."""
    from collections import Counter
    cuenta = Counter(p["alias"] for p in personas)
    for p in personas:
        if cuenta[p["alias"]] > 1 and len(p["nombre"].split()) > 1 and "(" not in p["nombre"]:
            p["alias"] = f"{p['alias']} {p['nombre'].split()[len(p['alias'].split())][0]}."
    return personas


def normalizar_persona(p):
    """Persona de la fase 0 → persona de la app (puestos de los 21, alias en texto)."""
    eq, extra = REGLAS["equivalencias_fase0"], REGLAS["puestos_extra"]
    puestos, desconocidos = [], []
    for x in p.get("puestos") or []:
        destino = eq.get(x)
        if destino is None:
            desconocidos.append(x)
            continue
        for d in destino:
            if d not in puestos:
                puestos.append(d)
    for d in extra.get(p["id"], []):
        if d not in puestos:
            puestos.append(d)
    assert all(x in PUESTOS_APP for x in puestos), (p["id"], puestos)
    principal = (eq.get(p.get("puesto_principal")) or puestos[:1] or [None])[0]
    return {
        "id": p["id"],
        "nombre": p["nombre"],
        "alias": alias_corto(p),
        "alias_todos": p.get("alias") or [],
        "puestos": puestos,
        "puesto_principal": principal,
        "puestos_fase0": p.get("puestos") or [],
        "puestos_sin_equivalencia": desconocidos,
        "jefe": p.get("jefe"),
        "nivel": p.get("nivel"),
        "horas_mes": p.get("horas_mes") or 128,
        "imputa_horas": p.get("imputa_horas"),
        "horas_imputadas_sep_oct": p.get("horas_imputadas_sep_oct"),
        "correo": p.get("correo"),
        "otros_correos": [c["correo"] for c in (p.get("otros_correos") or []) if c.get("de_ro")],
        "activo": bool(p.get("activo")),
        "estado": p.get("estado") or ("activo" if p.get("activo") else "baja"),
        "prueba": False,
        "nota": p.get("nota"),
        "fuente": "20_FASE0_DATOS/personas.json",
    }


def cargar_personas():
    propio = FASE0 / "personas.json"
    if propio.exists():
        crudo = json.loads(propio.read_text())
        lista = crudo["personas"] if isinstance(crudo, dict) else crudo
        return desambiguar([normalizar_persona(p) for p in lista]), "20_FASE0_DATOS/personas.json (normalizado a los 21 puestos)"
    personas = []
    for nombre, alias, puestos in SEMILLA_PERSONAS:
        personas.append({"id": slug(alias), "nombre": nombre, "alias": alias, "puestos": puestos,
                         "activo": True, "estado": "activo", "prueba": False})
    return personas, "semilla del 00 (20_FASE0_DATOS/personas.json no existe)"


# ------------------------------------------------- ids de clientes
# Los ids de la app son slug(nombre del panel). La fase 0 usa los ids del portal.
# Emparejamiento por nombre; los que no casan por palabras van aquí, comprobados a mano el 2-oct.
ID_A_MANO = {
    "fitecc": "fitec-asesores", "bit24": "bit-24", "deudout": "deudot", "kioskobox": "kiosko-box",
    "pgba": "pgb-auditores", "ce-consulting": "centro-consulting",
}
PALABRAS_VACIAS = {"asesores", "asesoria", "consulting", "consultores", "advisory", "gestion", "grupo",
                   "economistes", "assessors", "auditores", "y", "de", "la", "el"}


def emparejar_ids(fase0_clientes, app_ids_nombres):
    """{id_portal: id_app | None}. Exacto, a mano o por palabras distintivas (empate = sin emparejar)."""
    tok = {aid: (set(norm(n).split()) | set(norm(aid).split())) - PALABRAS_VACIAS for aid, n in app_ids_nombres.items()}
    out = {}
    for c in fase0_clientes:
        cid = c["cliente_id"]
        if cid in app_ids_nombres:
            out[cid] = cid
            continue
        if cid in ID_A_MANO:
            out[cid] = ID_A_MANO[cid]
            continue
        t = (set(norm(c["cliente"]).split()) | set(norm(cid).split())) - PALABRAS_VACIAS
        puntos = sorted(((len(t & tk), aid) for aid, tk in tok.items() if t & tk), reverse=True)
        if puntos and (len(puntos) == 1 or puntos[0][0] > puntos[1][0]):
            out[cid] = puntos[0][1]
        else:
            out[cid] = None
    return out


def ids_de_e1():
    """Lee (solo lectura) los ids que E1 deja en data/clientes/<id>.json: {id_app: {id, fase0, libro, …}}."""
    out = {}
    carpeta = SALIDA / "clientes"
    if carpeta.exists():
        for f in carpeta.glob("*.json"):
            try:
                d = json.loads(f.read_text())
            except Exception:
                continue
            ids = dict(d.get("ids") or {})
            ids["id"] = d.get("id") or f.stem
            out[ids["id"]] = ids
    return out


# Equivalencias razón social (libro) → cliente, confirmadas en memoria (2-oct).
LIBRO_A_MANO = {"Legal4U": "laver", "Gold Global Projects": "gestio-plural", "Productikaonline": "akua",
                "E Advisory": "ecija-advisory", "Ignasi Solà Coll": "finexen",
                "Strategic Management Business": "ecom-advisory"}


# ------------------------------------------------- dudas → para_confirmar
def parsear_dudas(texto, clientes_f0, personas, extra_cli=None):
    extra_cli = extra_cli or {}
    """Convierte dudas.md en filas estructuradas. Cada duda: id, bloque, objeto, choque, propuesta y opciones."""
    nombres_cli = [(c["cliente_id"], norm(c["cliente"])) for c in clientes_f0]
    tokens_cli = [(cid, set(cn.split()) - PALABRAS_VACIAS) for cid, cn in nombres_cli]
    alias_p = {}
    for p in personas:
        for a in [p["alias"], p["nombre"].split()[0], *p.get("alias_todos", [])]:
            alias_p[norm(a)] = p["id"]

    def cliente_de(txt):
        n = norm(txt)
        for cid, cn in nombres_cli:
            if n and (n == cn or n in cn or cn in n or norm(cid) == n):
                return cid
        t = set(n.split()) - PALABRAS_VACIAS
        cand = [cid for cid, tk in tokens_cli if t and t & tk]
        if len(cand) == 1:
            return cand[0]
        return extra_cli.get(n.split()[0]) if n else None

    def persona_en(txt):
        for w in re.findall(r"\*\*([^*]+)\*\*", txt) or [txt]:
            for palabra in re.split(r"[\s,;()]+", w):
                if norm(palabra) in alias_p:
                    return alias_p[norm(palabra)]
        return None

    dudas, bloque = [], None
    for linea in texto.splitlines():
        m = re.match(r"^## ([A-D]) · (.+)", linea)
        if m:
            bloque = m.group(1)
            continue
        if linea.startswith("| ") and bloque in ("A", "B", "C"):
            celdas = [x.strip() for x in linea.strip().strip("|").split("|")]
            if not re.fullmatch(r"[A-C]\d+", celdas[0]):
                continue
            if bloque == "A":
                did, obj, ahora, choque, prop = celdas[:5]
                cid = cliente_de(obj)
                dudas.append({"id": did, "bloque": "A", "tipo": "asignacion", "silla": "account", "cliente_id": cid,
                              "objeto": obj, "ahora": ahora, "choque": choque, "propuesta": prop,
                              "persona_propuesta": persona_en(prop)})
            elif bloque == "B":
                did, obj, choque, prop = celdas[:4]
                ids = [cliente_de(x) for x in re.split(r",| y ", obj)]
                ids = [x for x in ids if x]
                dudas.append({"id": did, "bloque": "B", "tipo": "asignacion" if ids else "cliente", "silla": "account",
                              "cliente_id": ids[0] if len(ids) == 1 else None, "clientes": ids, "objeto": obj,
                              "choque": choque, "propuesta": prop, "persona_propuesta": persona_en(prop)})
            else:
                did, obj, choque, prop = celdas[:4]
                pid = persona_en(obj)
                dudas.append({"id": did, "bloque": "C", "tipo": "persona", "persona_id": pid, "objeto": obj,
                              "choque": choque, "propuesta": prop})
        m = re.match(r"^\*\*(D\d) · ([^*]+)\*\*\s*(.+)", linea)
        if m:
            did, titulo, resto = m.groups()
            prop = resto.split("**Propuesta:**")[-1].strip() if "**Propuesta:**" in resto else ""
            dudas.append({"id": did, "bloque": "D", "tipo": "servicio" if did == "D4" else "asignacion",
                          "silla": {"D1": "trafficker", "D2": "crm", "D3": "trafficker"}.get(did),
                          "objeto": titulo.strip(), "choque": resto.split("**Propuesta:**")[0].strip(), "propuesta": prop})
    for d in dudas:                       # sin negritas de markdown en la interfaz
        for k in ("objeto", "ahora", "choque", "propuesta"):
            if d.get(k):
                d[k] = d[k].replace("**", "").replace("`", "")
    return dudas


# ------------------------------------------------- respuestas de Mili
def aplicar_respuestas(respuestas, personas, asignaciones, servicios, id_app, hoy, dudas=None):
    """
    Aplica 20_FASE0_DATOS/respuestas_mili.json (formato en respuestas_mili.ejemplo.json).
    Nada se borra: una asignación sustituida se cierra con «hasta» = el día anterior y «sustituida_por».
    Devuelve la lista de lo aplicado (para meta.json y el _ESTADO).
    """
    aplicado = []
    from confirmar_personas_572 import validar_persona, persona_vigente
    por_persona = {p["id"]: p for p in personas}
    plano = []
    for r in respuestas:          # una respuesta puede ser una lista (p. ej. B1: tres clientes a la vez)
        plano.extend(r if isinstance(r, list) else [r])
    for r in plano:
        if not isinstance(r, dict):
            aplicado.append({"error": "Respuesta omitida: formato no válido."})
            continue
        tipo, duda = r.get("tipo"), r.get("duda")
        origen = f"Mili · respuestas_mili.json · duda {duda or 's/n'}"
        if tipo == "asignacion":
            cid = id_app.get(r["cliente_id"], r["cliente_id"])
            silla, pid, accion = r["silla"], r.get("persona_id"), r.get("accion", "poner")
            desde = r.get("desde") or hoy
            if accion in ("poner", "sustituir"):
                cierre = (date.fromisoformat(desde) - timedelta(days=1)).isoformat()
                for a in asignaciones:
                    if a["cliente_id"] == cid and a["silla"] == silla and a.get("principal", True) and not a.get("hasta") \
                            and not a.get("suplencia") and a["persona_id"] != pid:
                        a["hasta"], a["sustituida_por"] = cierre, origen
                existente = next((a for a in asignaciones if a["cliente_id"] == cid and a["silla"] == silla
                                  and a["persona_id"] == pid and not a.get("hasta")), None)
                if existente:
                    existente.update({"confianza": "confirmada", "principal": True, "fuente_confirmacion": origen, "duda": None})
                else:
                    asignaciones.append({"cliente_id": cid, "persona_id": pid, "silla": silla, "desde": desde, "hasta": None,
                                         "suplencia": False, "principal": True, "fuente": origen, "confianza": "confirmada", "duda": None})
            elif accion == "confirmar":
                for a in asignaciones:
                    if a["cliente_id"] == cid and a["silla"] == silla and a["persona_id"] == pid and not a.get("hasta"):
                        a.update({"confianza": "confirmada", "fuente_confirmacion": origen, "duda": None})
            elif accion == "quitar":
                for a in asignaciones:
                    if a["cliente_id"] == cid and a["silla"] == silla and a["persona_id"] == pid and not a.get("hasta"):
                        a["hasta"], a["quitada_por"] = (date.fromisoformat(desde) - timedelta(days=1)).isoformat(), origen
            elif accion == "suplencia":
                assert r.get("hasta"), "una suplencia necesita fecha de fin"
                asignaciones.append({"cliente_id": cid, "persona_id": pid, "silla": silla, "desde": desde, "hasta": r["hasta"],
                                     "suplencia": True, "titular_id": r.get("titular_id"), "principal": False,
                                     "fuente": origen, "confianza": "confirmada", "duda": None})
            aplicado.append({"duda": duda, "tipo": tipo, "cliente_id": cid, "silla": silla, "persona_id": pid, "accion": accion})
        elif tipo == "persona":
            if not validar_persona(r, personas, dudas):
                aplicado.append({"duda": duda, "error": "Confirmación de persona omitida: contrato no válido."})
                continue
            p = persona_vigente(personas, r['persona_id'])
            estado = r['cambios']['estado']
            cambios = {"estado": estado, "activo": estado == 'activo'}
            p.update(cambios)
            marcas = p.get('confirmado_por')
            if not isinstance(marcas, list):
                marcas = []
                p['confirmado_por'] = marcas
            marcas.append(origen)
            aplicado.append({"duda": duda, "tipo": tipo, "persona_id": p["id"], "cambios": cambios})
        elif tipo == "servicio":
            cid = id_app.get(r["cliente_id"], r["cliente_id"])
            servicios.setdefault(cid, {})[r["servicio"]] = r["valor"]
            servicios[cid][f"{r['servicio']}_fuente"] = origen
            aplicado.append({"duda": duda, "tipo": tipo, "cliente_id": cid, "servicio": r["servicio"], "valor": r["valor"]})
        elif tipo == "nota":
            aplicado.append({"duda": duda, "tipo": "nota", "nota": r.get("nota")})
        else:
            aplicado.append({"duda": duda, "error": f"tipo desconocido: {tipo}"})
    return aplicado


# ------------------------------------------------- R12 · quién lleva qué (una sola verdad de asignaciones)
SILLAS_DE_PUESTO = {"account": ["account"], "trafficker": ["trafficker"], "especialista_ghl": ["crm"], "seo": ["seo"],
                    "ficha_google": ["seo"], "web": ["web"], "redes": ["redes"], "produccion": ["produccion"], "outreach": ["outreach"]}
NOMBRE_SILLA = {"account": "account", "trafficker": "trafficker", "crm": "GoHighLevel", "seo": "SEO", "web": "web",
                "redes": "redes", "produccion": "producción", "outreach": "outreach"}


def normalizar_asignaciones(asignaciones, personas, hoy):
    """R12 · reglas de «quién lleva qué» que valen para TODA la app (se aplican aquí, una vez):
    1. Una persona de baja sale de todo equipo: su fila vigente se cierra el día de su salida (o ayer).
    2. Una sola persona de web por cliente: la principal. Las filas de apoyo de web (sacadas de horas de ClickUp) se cierran,
       salvo las de quien no tiene el puesto web (Miguel Vargas): esas esperan la decisión de Tomás y no se tocan.
    Nada se borra: la fila cerrada lleva «hasta» y «cerrada_por». Devuelve la lista de cierres (para meta.json y el _ESTADO)."""
    ayer = (date.fromisoformat(hoy) - timedelta(days=1)).isoformat()
    por_id = {p["id"]: p for p in personas}

    def vigente(a):
        return (not a.get("desde") or a["desde"] <= hoy) and (not a.get("hasta") or a["hasta"] >= hoy)

    cierres = []
    for a in asignaciones:
        p = por_id.get(a.get("persona_id")) or {}
        if vigente(a) and (p.get("estado") == "baja" or (p and not p.get("activo") and p.get("estado") != "dudoso")):
            salida = p.get("fecha_salida")
            a["hasta"] = salida if salida and salida < hoy else ayer
            a["cerrada_por"] = "R12 · persona de baja (personas.json): fuera de todo equipo"
            cierres.append({"regla": "baja", "cliente_id": a["cliente_id"], "silla": a["silla"], "persona_id": a["persona_id"]})
    web = {}
    for a in asignaciones:
        if a.get("silla") == "web" and vigente(a) and not a.get("suplencia"):
            web.setdefault(a["cliente_id"], []).append(a)
    for cid, filas in web.items():
        if len(filas) < 2 or not any(f.get("principal", True) for f in filas):
            continue
        for f in filas:
            puestos = set((por_id.get(f["persona_id"]) or {}).get("puestos") or [])
            if not f.get("principal", True) and "web" in puestos:
                f["hasta"] = ayer
                f["cerrada_por"] = ("R12 · una sola persona de web por cliente (la principal). "
                                    "Las horas de apoyo en ClickUp no hacen dueño de la web.")
                cierres.append({"regla": "web_unica", "cliente_id": cid, "silla": "web", "persona_id": f["persona_id"]})
    return cierres


def avisos_silla_ajena(asignaciones, personas, hoy):
    """R12 · persona activa cuyas asignaciones vigentes están TODAS en sillas que su puesto no abre (Miguel Vargas:
    17 clientes en la silla web y puesto «especialista en GoHighLevel»). Sin esto, ve todas sus pantallas vacías sin saber
    por qué. Se le avisa en llano en Mi día (alarma de persona a su nombre). No se reasigna nada: lo decide Mili o Tomás."""
    out = []
    for p in personas:
        if not p.get("activo") or p.get("estado") == "baja":
            continue
        puestos = p.get("puestos") or []
        suyas = {s for x in puestos for s in SILLAS_DE_PUESTO.get(x, [])}
        if not suyas:
            continue
        mias = [a for a in asignaciones if a.get("persona_id") == p["id"]
                and (not a.get("desde") or a["desde"] <= hoy) and (not a.get("hasta") or a["hasta"] >= hoy)]
        if not mias or any(a["silla"] in suyas for a in mias):
            continue
        sillas = sorted({a["silla"] for a in mias})
        n = len({a["cliente_id"] for a in mias})
        quiero = " y ".join(sorted({NOMBRE_SILLA.get(s, s) for s in suyas}))
        en = " y ".join(NOMBRE_SILLA.get(s, s) for s in sillas)
        out.append({
            "id": f"r12-silla-{p['id']}", "ambito": "persona", "cliente_id": None, "cliente": None,
            "resumen": f"{n} clientes", "gravedad": "rojo", "tipo": "Tus clientes están en otra silla",
            "texto": f"Tus {n} clientes están asignados como {en}; pendiente de que Mili o Tomás te asignen {quiero}. "
                     f"Hasta entonces tus pantallas salen vacías.",
            "accion": f"Pedir a Mili que te asigne los clientes de {quiero}", "enlace": None, "desde": hoy,
            "responsable_id": p["id"], "responsable_texto": p.get("alias") or p.get("nombre"),
        })
    return out


def dudas_quien_lleva(asignaciones, clientes, personas, hoy):
    """R12 · dudas para Mili (bloque D de Ajustes) con lo que la app no puede saber sola. No inventa a nadie:
    lista los clientes y deja la persona sin proponer."""
    def vigente(a):
        return (not a.get("desde") or a["desde"] <= hoy) and (not a.get("hasta") or a["hasta"] >= hoy)
    nombre = {c["id"]: c["nombre"] for c in clientes}
    con = {}
    for a in asignaciones:
        if vigente(a):
            con.setdefault(a["silla"], set()).add(a["cliente_id"])
    dudas = []
    webs_f = SALIDA / "seo" / "webs.json"         # la lista de webs del monitor (SEO, ficha y webs)
    try:
        webs = [w.get("cliente") for w in json.loads(webs_f.read_text()).get("webs", []) if not w.get("propia")]
    except Exception:
        webs = []
    sin_web = sorted({c for c in webs if c in nombre and c not in con.get("web", set())}, key=lambda c: nombre[c])
    if sin_web:
        dudas.append({"id": "R12-WEB", "bloque": "D", "tipo": "asignacion", "silla": "web", "cliente_id": None, "clientes": sin_web,
                      "objeto": f"Webs sin persona de web ({len(sin_web)}):",
                      "choque": "El monitor vigila su web, pero nadie tiene la silla «web» en las asignaciones: "
                                + ", ".join(nombre[c] for c in sin_web) + ". Si se cae, la alerta va a Jerónimo como jefe.",
                      "propuesta": "Elegir la persona de web (Macarena o Carlos V.); si no es la misma para todas, decir en la nota quién lleva cada una. La app no propone a nadie.",
                      "persona_propuesta": None, "respondida": False})
    cap_f = SALIDA / "captacion" / "captacion.json"   # cuentas de Meta que lee Captación
    try:
        cap = [c.get("cliente_id") for c in json.loads(cap_f.read_text()).get("clientes", [])]
    except Exception:
        cap = []
    sin_traf = sorted({c for c in cap if c in nombre and c not in con.get("trafficker", set())}, key=lambda c: nombre[c])
    if sin_traf:
        dudas.append({"id": "R12-TRAF", "bloque": "D", "tipo": "asignacion", "silla": "trafficker", "cliente_id": None, "clientes": sin_traf,
                      "objeto": f"Cuentas de Meta sin trafficker ({len(sin_traf)}):",
                      "choque": "Captación lee su cuenta de Meta, pero nadie tiene la silla «trafficker»: "
                                + ", ".join(nombre[c] for c in sin_traf) + ". En la carga de Valeria salían como «persona sin ficha».",
                      "propuesta": "Elegir trafficker o confirmar que no llevan publicidad con RO.", "persona_propuesta": None, "respondida": False})
    crm_f = SALIDA / "crm" / "crm.json"             # subcuentas encendidas (Salud del CRM) sin especialista
    try:
        enc = [f.get("cliente_id") for f in json.loads(crm_f.read_text()).get("subcuentas", []) if f.get("encendida") and f.get("tipo") == "cliente"]
    except Exception:
        enc = []
    sin_crm = sorted({c for c in enc if c in nombre and c not in con.get("crm", set())}, key=lambda c: nombre[c])
    if sin_crm:
        dudas.append({"id": "R12-CRM", "bloque": "D", "tipo": "asignacion", "silla": "crm", "cliente_id": None, "clientes": sin_crm,
                      "objeto": f"Subcuentas encendidas sin especialista de GoHighLevel ({len(sin_crm)}):",
                      "choque": "Entran leads y nadie tiene la silla «CRM»: " + ", ".join(nombre[c] for c in sin_crm)
                                + ". Mientras tanto, las tareas de CRM van a Yessica como jefa.",
                      "propuesta": "Elegir especialista (Gustavo o Yessica). La app no propone a nadie.", "persona_propuesta": None, "respondida": False})
    return dudas


def cuota_empresa():
    """Ronda 9 (D-P-DIN): las tres cifras de cuota del mes salen de la MISMA fuente que la cuota de cada cliente,
    fuentes_dinero/cuotas.json (Airtable de octubre de Sofía → proyecto → factura de Holded → firmado sin ficha):
      recurrente = suma de las cuotas sin los proyectos con fin · cuota_mes = suma de todas · facturable = cuota_mes con
      los ajustes del mes (descuentos y abonos) que Dinero apunta en data/finanzas/finanzas.json → admin.cuota_tres.
    Si la suma de cuotas.json no casa con lo de Finanzas, «coherente» = False y el aviso lo dice (no se elige una a ojo).
    Octubre 2026: recurrente 67.291 € · cuota del mes 70.781 € · facturable 70.581 €."""
    f = AQUI / "fuentes_dinero" / "cuotas.json"
    if not f.exists():
        return None
    cq = json.loads(f.read_text())
    filas = (cq.get("cuotas") or {}).values()
    es_proyecto = lambda x: "proyecto con fin" in str(x.get("fuente") or "").lower()
    cuota_mes = round(sum(x.get("cuota") or 0 for x in filas), 2)
    recurrente = round(sum(x.get("cuota") or 0 for x in filas if not es_proyecto(x)), 2)
    tres = {}
    fin = SALIDA / "finanzas" / "finanzas.json"
    if fin.exists():
        try:
            tres = (json.loads(fin.read_text()).get("admin") or {}).get("cuota_tres") or {}
        except Exception:
            tres = {}
    ajuste = round((tres.get("facturable") or 0) - (tres.get("cuota_mes") or 0), 2) if tres.get("facturable") is not None else 0.0
    facturable = round(cuota_mes + ajuste, 2)
    coherente = not tres or (abs((tres.get("recurrente") or 0) - recurrente) < 1 and abs((tres.get("cuota_mes") or 0) - cuota_mes) < 1)
    return {"mes": cq.get("mes"), "recurrente": recurrente, "cuota_mes": cuota_mes, "facturable": facturable,
            "ajustes_mes": ajuste, "clientes_con_cuota": sum(1 for x in filas if (x.get("cuota") or 0) > 0),
            "fuente": "fuentes_dinero/cuotas.json (cuota de cada cliente) + ajustes del mes de data/finanzas/finanzas.json → admin.cuota_tres",
            "coherente": coherente,
            "aviso": None if coherente else f"cuotas.json suma {recurrente} € recurrente y {cuota_mes} € del mes; Finanzas dice {tres.get('recurrente')} € y {tres.get('cuota_mes')} €."}


def main():
    hoy = date.today().isoformat()
    datos = json.loads((PANEL / "datos.json").read_text())
    logos_src = json.loads((PANEL / "portal_logos.json").read_text())
    logos_src.update(datos.get("logos") or {})
    portal = datos.get("portal") or {}

    personas, origen_personas = cargar_personas()
    por_nombre = {}
    for p in personas:
        for clave in {p["nombre"], p["alias"], *p.get("alias_todos", []), p["nombre"].split()[0]}:
            por_nombre.setdefault(norm(clave), p["id"])

    def persona_de(nombre_account):
        n = norm(nombre_account)
        if not n:
            return None
        if n in por_nombre:
            return por_nombre[n]
        return por_nombre.get(n.split()[0]) if len(n.split()) > 1 else None

    # ------------------------------------------------------------ clientes del panel
    clientes, logos, ids = [], {}, {}
    for c in datos["clientes"]:
        cid = slug(c["nombre"])
        ids[c["nombre"]] = cid
        p = portal.get(c["nombre"]) or {}
        meta = c.get("meta") or {}
        d30 = meta.get("d30") or {}
        inf = c.get("informe_ant") or {}
        if p.get("logo") and p["logo"] in logos_src:
            logos[cid] = logos_src[p["logo"]]
        clientes.append({
            "id": cid,
            "nombre": con_tildes(c["nombre"]),
            "web": p.get("web"),
            "descripcion": descripciones(p.get("descripcion"))[0],
            "descripcion_completa": descripciones(p.get("descripcion"))[1],
            "alta": p.get("alta"),
            "responsable_id": persona_de(c.get("account")),
            "responsable_texto": c.get("account"),
            "semaforo": c.get("semaforo"),
            # Salud provisional: 100 - riesgo del panel v27 (build.py 233-251) hasta construir la D-02.
            "salud": max(0, 100 - int(c.get("riesgo") or 0)),
            "salud_fuente": "provisional: 100 - riesgo del panel v27 (D-02 firmada, sin construir)",
            "nuevo": bool(c.get("nuevo")),
            "cuota": c.get("cuota"),               # sensible: lo filtra ver()
            "publicidad_30d": {                    # sensible (inversión): lo filtra ver()
                "gasto": d30.get("gasto"), "leads": d30.get("leads"), "cpl": d30.get("cpl"),
                "campanas_activas": meta.get("campanas_activas"),
            } if meta else None,
            "tickets_abiertos": c.get("tickets_abiertos"),
            "pend_horas": c.get("pend_horas"),
            "dias_sin_reunion": c.get("dias_sin_reunion") if (c.get("dias_sin_reunion") or 0) < 900 else None,
            "ult_reunion": c.get("ult_reunion"),
            "prox_reunion": c.get("prox_reunion"),
            "informe_anterior": inf.get("estado"),
            "revision48": c.get("revision48"),
            "enlace_clickup": c.get("enlace_clickup"),
            "origen": "panel v27",
        })

    # ------------------------------------------------------------- alarmas
    alarmas = []
    for a in datos["alarmas"]:
        es_cliente = a["cliente"] in ids
        resp = persona_de(a.get("account"))
        accion = a.get("accion") or ""
        if not resp and re.match(r"(Pide|Recuerda|Revisa con) a? ?sin ", accion):
            accion = "Asignar responsable y repartir"
        alarmas.append({
            "id": a["id"],
            "ambito": "cliente" if es_cliente else "persona",
            "cliente_id": ids.get(a["cliente"]),
            "cliente": a["cliente"] if es_cliente else None,
            "resumen": None if es_cliente else a["cliente"],   # «4 clientes», «46 tareas»
            "gravedad": "rojo" if a["gravedad"] == "rojo" else "ambar",
            "tipo": a["tipo"],
            "texto": sanear(a.get("texto")),
            "accion": sanear(accion),
            "enlace": a.get("enlace"),
            "desde": a.get("desde"),
            "responsable_id": resp,
            "responsable_texto": a.get("account"),
        })

    # --------------------------------------------------------- asignaciones (fase 0)
    asig_f0 = FASE0 / "asignaciones.json"
    para_confirmar, aplicado, ids_cli = [], [], {}
    servicios = {}
    if asig_f0.exists():
        f0 = json.loads(asig_f0.read_text())
        f0_clientes = f0["clientes"]
        app_nombres = {c["id"]: c["nombre"] for c in clientes}
        id_app = emparejar_ids(f0_clientes, app_nombres)
        # Si E1 ya generó data/clientes/<id>.json, su campo ids.fase0 manda (emparejado por identificador).
        for k, v in ids_de_e1().items():
            if v.get("fase0") and v["id"] in app_nombres:
                id_app[v["fase0"]] = v["id"]
        # Clientes del portal que el panel no tiene: entran con lo mínimo (nombre y cuota).
        for c in f0_clientes:
            if id_app.get(c["cliente_id"]) is None:
                nuevo_id = c["cliente_id"]
                id_app[c["cliente_id"]] = nuevo_id
                clientes.append({"id": nuevo_id, "nombre": con_tildes(c["cliente"]), "responsable_id": None,
                                 "responsable_texto": None, "semaforo": None, "salud": None,
                                 "salud_fuente": "sin dato: no está en el panel v27", "nuevo": False,
                                 "cuota": c.get("cuota_mes"), "publicidad_30d": None, "origen": "portal (fase 0)"})
        ids_cli = {"portal_a_app": id_app}
        asignaciones = []
        for a in f0["asignaciones"]:
            fila = dict(a)
            fila["cliente_id_portal"] = a["cliente_id"]
            fila["cliente_id"] = id_app.get(a["cliente_id"], a["cliente_id"])
            fila.setdefault("principal", True)
            asignaciones.append(fila)
        servicios = {id_app.get(c["cliente_id"], c["cliente_id"]): dict(c.get("servicios") or {}) for c in f0_clientes}
        tipo_cli = {id_app.get(c["cliente_id"], c["cliente_id"]): c.get("tipo") for c in f0_clientes}
        origen_asig = "20_FASE0_DATOS/asignaciones.json (ids del portal traducidos a los de la app)"

        dudas_md = FASE0 / "dudas.md"
        if dudas_md.exists():
            extra = {norm(c["nombre"]).split()[0]: c["id"] for c in clientes if c.get("origen") == "panel v27"}
            para_confirmar = parsear_dudas(dudas_md.read_text(), f0_clientes, personas, extra)
            # C9 y C10 (correos de entrada) quedan resueltas por la lista de correos de Tomás (2-oct): fuera.
            para_confirmar = [d for d in para_confirmar if d.get("id") not in ("C9", "C10")]
            for d in para_confirmar:
                if d.get("cliente_id"):
                    d["cliente_id"] = id_app.get(d["cliente_id"], d["cliente_id"])
                if d.get("clientes"):
                    d["clientes"] = [id_app.get(x, x) for x in d["clientes"]]

        from fuentes_verdad.servicios_confirmados import aplicar as aplicar_servicios
        declarados = [{'id': cid, 'servicios': valor} for cid, valor in servicios.items()]
        aplicar_servicios(declarados)
        servicios.update({x['id']: x['servicios'] for x in declarados})

        resp_f = FASE0 / "respuestas_mili.json"
        if resp_f.exists():
            resp = json.loads(resp_f.read_text())
            aplicado = aplicar_respuestas(resp.get("respuestas", []), personas, asignaciones, servicios, id_app, hoy, dudas=para_confirmar)
            hechas = {x.get("duda") for x in aplicado if not x.get("error")}
            for d in para_confirmar:
                if d["id"] in hechas:
                    d["respondida"] = True
    else:
        asignaciones = [
            {"cliente_id": c["id"], "persona_id": c["responsable_id"], "silla": "account",
             "desde": None, "hasta": None, "suplencia": False, "principal": True}
            for c in clientes if c["responsable_id"]
        ]
        tipo_cli = {}
        origen_asig = "semilla: account de la Cartera en datos.json (solo silla account)"

    # R12 · quién lleva qué: bajas fuera de todo equipo y una sola persona de web por cliente (ver normalizar_asignaciones)
    cierres_r12 = normalizar_asignaciones(asignaciones, personas, hoy)
    para_confirmar = [d for d in para_confirmar if not str(d.get("id", "")).startswith("R12-")] + \
        dudas_quien_lleva(asignaciones, clientes, personas, hoy)

    # ------------------------------------------- equipo, responsable y marca por cliente
    def vigente(a):
        return (not a.get("desde") or a["desde"] <= hoy) and (not a.get("hasta") or a["hasta"] >= hoy)

    activos_ids = {p["id"] for p in personas if p.get("activo")}
    for c in clientes:
        equipo = {}
        for a in asignaciones:
            if a["cliente_id"] == c["id"] and vigente(a):
                equipo.setdefault(a["silla"], []).append({
                    "persona_id": a["persona_id"], "principal": a.get("principal", True),
                    "confianza": a.get("confianza"), "suplencia": bool(a.get("suplencia")),
                })
        for s in equipo.values():
            s.sort(key=lambda x: (not x["principal"], x["suplencia"]))
        c["equipo"] = equipo
        c["servicios"] = servicios.get(c["id"])
        acc = next((x["persona_id"] for x in equipo.get("account", []) if x["principal"] and not x["suplencia"]), None)
        if acc:
            c["responsable_id"] = acc
            c["sin_account"] = None
        else:
            mant = (servicios.get(c["id"]) or {}).get("mantenimiento") == "sí" or (tipo_cli.get(c["id"]) or "").lower().startswith("manten")
            duda = next((d["id"] for d in para_confirmar if d.get("silla", "account") == "account"
                         and (d.get("cliente_id") == c["id"] or c["id"] in (d.get("clientes") or []))), None)
            c["sin_account"] = "mantenimiento sin account" if mant else f"sin account · para confirmar{f' ({duda})' if duda else ''}"
            c["responsable_id"] = None   # B-03: sin account en asignaciones = sin responsable (nunca el de otra fuente)
        # R12 (M1 Musashi): el texto del responsable sale de la MISMA asignación que responsable_id, nunca del «account»
        # escrito en el panel v27 (Musashi decía «Agustina Alegre» con responsable_id Natalia).
        pa = next((p for p in personas if p["id"] == c["responsable_id"]), None) if c["responsable_id"] else None
        c["responsable_texto"] = (pa.get("alias") or pa.get("nombre")) if pa else None

    # ------------------------------------------- cotejo con el libro de clientes (D-16)
    cotejo = None
    if LIBRO.exists():
        libro = json.loads(LIBRO.read_text())
        activos = [v.get("cliente") or k for k, v in libro.items() if v.get("estado") == "Activo"]
        tok = {c["id"]: set(norm(c["nombre"]).split()) - PALABRAS_VACIAS for c in clientes}
        if asig_f0.exists():   # los nombres del portal llevan la razón social entre paréntesis
            for c in f0_clientes:
                aid = id_app.get(c["cliente_id"])
                tok.setdefault(aid, set()).update(set(norm(c["cliente"]).split()) | set(norm(c["cliente_id"]).split()))
                tok[aid] -= PALABRAS_VACIAS
        sin = []
        por_libro_e1 = {v.get("libro"): k for k, v in ids_de_e1().items() if v.get("libro")}
        for n in activos:
            if n in por_libro_e1 or n in LIBRO_A_MANO:
                continue
            t = set(norm(n).split()) - PALABRAS_VACIAS
            if not any(t & tk for tk in tok.values()):
                sin.append(n)
        cotejo = {"activos_en_libro": len(activos), "sin_emparejar_en_la_app": sin,
                  "nota": "Emparejado por palabras del nombre; el libro usa la razón social y la app el nombre comercial."}
    ids_cli["libro_clientes"] = cotejo

    # Ronda 5 (una sola verdad): «nuevo» = está en Clientes nuevos (data/nuevos/nuevos.json → altas), y la alarma
    # «fuera de plazo» distingue «sin encender» (rojo) de «encendida tarde» (ámbar), igual que Nuevos y la verdad única.
    nuevos_f = SALIDA / "nuevos/nuevos.json"
    if nuevos_f.exists():
        try:
            altas = {a["cliente_id"]: a for a in json.loads(nuevos_f.read_text()).get("altas", [])}
        except Exception:
            altas = {}
        if altas:
            for c in clientes:
                c["nuevo"] = c["id"] in altas
            for a in alarmas:
                n = altas.get(a.get("cliente_id"))
                dia_enc = ((n or {}).get("plazo") or {}).get("dia_encendido")
                if a["tipo"] == "Cliente nuevo fuera de plazo" and dia_enc is not None:
                    a.update({"tipo": "Cliente nuevo encendido tarde", "gravedad": "ambar",
                              "texto": f"Encendida el día {dia_enc} desde el alta (límite: día 12)."})

    # Ronda 8 (D-P04): la alarma de bloqueos sigue la regla de la verdad única: «bloqueo callado» = la tarea bloqueada
    # más antigua lleva más de 5 días (Producción). La del panel («Bloqueo sin resolver», más de 2 días) se sustituye.
    prod_f = SALIDA / "produccion/produccion.json"
    if prod_f.exists():
        try:
            proyectos = {p["cliente_id"]: p for p in json.loads(prod_f.read_text()).get("proyectos", []) if p.get("cliente_id")}
        except Exception:
            proyectos = {}
        if proyectos:
            previas = {a["cliente_id"]: a for a in alarmas if a["tipo"] == "Bloqueo sin resolver"}
            alarmas[:] = [a for a in alarmas if a["tipo"] != "Bloqueo sin resolver"]
            nombre_cli = {c["id"]: c["nombre"] for c in clientes}
            for cid, p in sorted(proyectos.items()):
                if cid in nombre_cli and (p.get("bloqueo_max") or 0) > 5:
                    n = p.get("bloqueadas") or 0
                    prev = previas.get(cid) or {}
                    alarmas.append({
                        "id": prev.get("id") or f"bloq-{cid}", "ambito": "cliente", "cliente_id": cid, "cliente": nombre_cli[cid],
                        "resumen": None, "gravedad": "ambar", "tipo": "Bloqueo callado más de 5 días",
                        "texto": f"{n} tarea{'s' if n != 1 else ''} en «bloqueado»; la más antigua lleva {p['bloqueo_max']} días sin moverse.",
                        "accion": "Desbloquear o avisar al cliente hoy", "enlace": prev.get("enlace"), "desde": prev.get("desde"),
                        "responsable_id": prev.get("responsable_id"), "responsable_texto": prev.get("responsable_texto"),
                    })

    # Ronda 8 · quién está de verdad en el equipo, su rol, su zona, su cumpleaños (día y mes) y su entrada en la agencia.
    # Fuente: fuentes_equipo/equipo.json (plantilla 2026 + quién cobra en septiembre + ClickUp; generar_equipo.py).
    # Sustituye a fuentes_horas/zonas.json como fuente de la zona (que queda solo como respaldo).
    eq_f = AQUI / "fuentes_equipo" / "_privado" / "equipo.json"   # con correos de entrada: ruta privada
    equipo = json.loads(eq_f.read_text()).get("personas", {}) if eq_f.exists() else {}
    zonas_f = AQUI / "fuentes_horas" / "zonas.json"
    zonas = json.loads(zonas_f.read_text()) if zonas_f.exists() else {}
    defecto = zonas.get("_por_defecto") or "America/Argentina/Buenos_Aires"
    # Correcciones de puestos con el rol de la plantilla (Tomás, 2-oct). Agus sigue como técnica de altas aunque la hoja diga account.
    correos_entrada = {}
    # Ronda 8 (Tomás, 2-oct, tarde): Jerónimo jefe de SEO (célula SEO y web); Coti deja la jefatura de SEO; Miguel 100 % GoHighLevel;
    # Camilo transversal (copy para varias áreas); Lara redes + outreach (respuesta C2 de Mili).
    # N9 (2-oct noche, auditoría 36 §6.4): las correcciones ya no están escritas aquí: fuentes_equipo/correcciones_equipo.json
    # (datos; lo que se cambie luego en Ajustes queda en el historial y manda sobre esto). Agus: solo técnica de altas (D4).
    corr_f = AQUI / "fuentes_equipo" / "correcciones_equipo.json"
    corr = json.loads(corr_f.read_text()) if corr_f.exists() else {}
    CORRECCIONES_ROL = corr.get("puestos") or {}
    CORRECCIONES_JEFE = corr.get("jefes") or {}
    ETIQUETAS = corr.get("etiquetas") or {}
    NOTAS = corr.get("notas") or {}
    for p in personas:
        e = equipo.get(p["id"]) or {}
        if e:
            if not p["id"].startswith("setter_"):       # a los setters los activa Mili
                p["estado"], p["activo"] = e["estado"], e["estado"] == "activo"
                p["estado_motivo"] = e.get("motivo")
            p["rol"] = e.get("rol")
            p["fecha_ingreso"] = e.get("ingreso")
            p["fecha_salida"] = e.get("fecha_salida")
            p["pais"] = e.get("pais")
            p["cumple_dia_mes"] = e.get("cumple_dia_mes")
        z = zonas.get(p["id"]) or {}
        p["zona"] = e.get("zona") or z.get("zona") or defecto
        p["zona_fuente"] = e.get("zona_fuente") or z.get("fuente") or "supuesta (Argentina por defecto)"
        p["zona_a_confirmar"] = bool(e.get("zona_a_confirmar", True))
        if p["id"] in CORRECCIONES_ROL:
            p["puestos"] = CORRECCIONES_ROL[p["id"]]
            p["puestos_fuente_ronda8"] = f"rol en la plantilla 2026: «{p.get('rol')}»"
        if p["id"] in CORRECCIONES_JEFE:
            p["jefe"] = CORRECCIONES_JEFE[p["id"]]
        if p["id"] in NOTAS:
            p["nota"] = NOTAS[p["id"]]
        p["etiquetas"] = ETIQUETAS.get(p["id"], [])
        # Correo de entrada (Tomás, 2-oct): el de «Equipo - nombres y correos.xlsx». Es el que va a Cloudflare Access.
        # Tomás no está en esa lista: entra con su correo de la fase 0. Si falta, aviso «falta correo» (Ana y Javier).
        # El correo NO se queda en personas.json (que es público para el equipo): va a data/_privado/correos_entrada.json,
        # que solo lee servir.py para casar la identidad de Cloudflare Access. Aquí solo queda si lo tiene y de dónde sale.
        if e.get("correo_entrada"):
            correos_entrada[p["id"]], p["correo_entrada_fuente"] = e["correo_entrada"], "Equipo - nombres y correos.xlsx (Tomás, 2-oct)"
        elif p["id"] == "tomas" and p.get("correo"):
            correos_entrada[p["id"]], p["correo_entrada_fuente"] = p["correo"], "fase 0 (no está en la lista de correos)"
        else:
            p["correo_entrada_fuente"] = None
        p.pop("correo_entrada", None)
        p["tiene_correo_entrada"] = p["id"] in correos_entrada
        p["aviso_correo"] = "falta correo" if p.get("activo") and p["id"] not in correos_entrada else None

    (AQUI / "data" / "_privado").mkdir(parents=True, exist_ok=True)
    # N9: las altas y bajas hechas en Ajustes (altas_personas.py) se conservan al regenerar: «desde_la_app».
    from altas_personas import fusionar_altas_app
    corr_priv = AQUI / "data" / "_privado" / "correos_entrada.json"
    try:
        previo = json.loads(corr_priv.read_text())
    except (OSError, ValueError):
        previo = {}
    desde_la_app, activos_access = fusionar_altas_app(personas, correos_entrada, previo)
    corr_priv.write_text(json.dumps(
        {"que_es": "Correo de entrada de cada persona (Cloudflare Access). Solo lo lee servir.py; no se sirve a nadie.",
         "fuente": "~/Downloads/Equipo - nombres y correos.xlsx (Tomás, 2-oct) + altas y bajas de Ajustes", "generado": hoy,
         "correos": correos_entrada, "desde_la_app": desde_la_app},
        ensure_ascii=False, indent=1))
    # Lista para la puerta de Cloudflare Access: correos de entrada de las personas activas (sin bajas), uno por línea.
    acceso = sorted({correos_entrada[pid] for pid in activos_access})
    faltan = [p["alias"] or p["nombre"] for p in personas if p.get("aviso_correo")]
    (AQUI / "despliegue").mkdir(exist_ok=True)
    (AQUI / "despliegue" / "lista_access.txt").write_text(
        f"# Correos de entrada de las personas activas · generado por build_data.py el {hoy}\n"
        f"# Fuente: ~/Downloads/Equipo - nombres y correos.xlsx (Tomás, 2-oct) + estado de fuentes_equipo/equipo.json\n"
        f"# {len(acceso)} correos · sin correo (no pueden entrar): {', '.join(faltan) or 'nadie'}\n" + "\n".join(acceso) + "\n")

    # Ronda 8: la cuota de cada cliente sale de UNA fuente, fuentes_dinero/cuotas.json (M18/M19: Airtable de octubre y, si no,
    # Holded). Si el cliente no está ahí, se queda la que había con su fuente dicha; si está con cuota vacía, va vacía.
    cuotas_f = AQUI / "fuentes_dinero" / "cuotas.json"
    if cuotas_f.exists():
        cq = json.loads(cuotas_f.read_text())
        for c in clientes:
            fila = (cq.get("cuotas") or {}).get(c["id"])
            if fila is not None:
                c["cuota"], c["cuota_fuente"] = fila.get("cuota"), f"fuentes_dinero/cuotas.json · {fila.get('fuente') or 'sin fuente'}"
            elif c.get("cuota") is not None:
                c["cuota_fuente"] = "libro de clientes (no está en cuotas.json)"

    # Ronda 9 (D-P-CAP5, decisión del coordinador 2-oct): Kiosko Box es una TIENDA ONLINE. Sus «leads» de Meta son
    # conversiones del píxel: fuera del total de leads de la casa y del techo de 35 €/lead. Lo común lo marca aquí
    # (campo «tipo_negocio», lo ven todos) para que cada módulo lo excluya con la misma regla: c.tipo_negocio === 'tienda_online'.
    TIENDAS_ONLINE = {"kiosko-box"}
    for c in clientes:
        c["tipo_negocio"] = "tienda_online" if c["id"] in TIENDAS_ONLINE else "despacho"

    # R12 · aviso en llano a quien tiene todos sus clientes en una silla que su puesto no abre (Miguel Vargas).
    alarmas[:] = [a for a in alarmas if not str(a.get("id", "")).startswith("r12-silla-")] + avisos_silla_ajena(asignaciones, personas, hoy)

    # B-03: «Cliente nuevo sin account» solo si de verdad no tiene account. Si lo tiene en asignaciones y la Cartera de
    # ClickUp va con retraso, el aviso pasa a «Falta la ficha en la Cartera de ClickUp» (ámbar, de Agus).
    con_account = {c["id"]: c["responsable_id"] for c in clientes if c.get("responsable_id")}
    for a in alarmas:
        if a["tipo"] == "Cliente nuevo sin account" and a.get("cliente_id") in con_account:
            a.update({"tipo": "Falta la ficha en la Cartera de ClickUp", "gravedad": "ambar",
                      "texto": "Tiene account en las asignaciones, pero aún no tiene ficha en la Cartera de ClickUp.",
                      "accion": "Crear la ficha del cliente en la Cartera de ClickUp", "responsable_id": "agustina", "responsable_texto": "Agus"})
        elif a.get("ambito") == "cliente" and a.get("cliente_id"):
            # R12: el responsable de una alarma de cliente es su account de las asignaciones (no el texto del panel v27).
            antes = (a.get("responsable_texto") or "").strip()
            a["responsable_id"] = con_account.get(a["cliente_id"])
            a["responsable_texto"] = next((c["responsable_texto"] for c in clientes if c["id"] == a["cliente_id"]), None) or "sin account"
            # la acción escrita en el panel nombra al account de entonces («Pide a Agustina…»): se cambia por el de hoy
            if antes and antes not in ("sin account", a["responsable_texto"]) and a.get("accion"):
                nuevo = a["responsable_texto"] if a["responsable_id"] else "su account (sin asignar)"
                for viejo in sorted({antes, antes.split()[0]}, key=len, reverse=True):
                    a["accion"] = re.sub(rf"\b{re.escape(viejo)}\b", nuevo, a["accion"])
        a["texto"], a["accion"] = limpia_texto(a.get("texto")), limpia_texto(a.get("accion"))

    # ---------------------------------------------------------------- meta
    salud = datos.get("v7_salud") or {}
    meta = {
        "generado": datos.get("generado"),
        "construido": hoy,
        "origen_personas": origen_personas,
        "origen_asignaciones": origen_asig,
        "r12_cierres": {"regla": "bajas fuera de todo equipo · una sola persona de web por cliente (la principal)",
                        "cerradas": cierres_r12},
        "respuestas_mili": {"fichero": "20_FASE0_DATOS/respuestas_mili.json", "existe": (FASE0 / "respuestas_mili.json").exists(),
                            "aplicadas": aplicado},
        "fuentes": salud.get("fuentes") or [],
        "resumen": {k: datos["resumen"].get(k) for k in
                    ("pend48", "pend24", "semaforo_sin", "semaforo_rojo", "clientes_activos",
                     "sin_correo_semana", "sin_reunion_mes", "nuevos", "nuevos_tarde", "revision48")},
        "historico": (datos.get("v7") or {}).get("historico") or [],
    }

    # ----------------------------------------------- Tomás 3-oct: un solo filtro «cliente activo» (fuentes_verdad/clientes_activos.py)
    # Los clientes de baja (libro de clientes + Airtable de octubre) no entran en la base de la app; su histórico sigue en finanzas.
    try:
        from fuentes_verdad import clientes_activos as ACT
        _base = {"clientes": clientes, "alarmas": alarmas, "asignaciones": asignaciones, "logos": logos}
        _fuera = ACT.limpiar_nucleo(_base)
        clientes, alarmas, asignaciones, logos = _base["clientes"], _base["alarmas"], _base["asignaciones"], _base["logos"]
        if _fuera:
            print(f"clientes de baja fuera de la base: {', '.join(_fuera)}")
    except Exception as e:   # sin la lista, la base sale como antes (y pruebas_coherencia lo dirá)
        print(f"aviso: sin filtro de clientes activos ({e})")

    # ----------------------------------------------- comprobación de fugas
    blob = json.dumps([clientes, alarmas, asignaciones, para_confirmar], ensure_ascii=False)
    assert not RE_CORREO.search(blob), "queda un correo en los datos de clientes, alarmas o asignaciones"
    for k in ("contactos", "contacts", "tel", "mail", "password", "contraseña", "sueldo", "salario"):
        assert f'"{k}"' not in blob, f"campo sensible {k}"
    assert not any(k in json.dumps(personas) for k in ('"sueldo"', '"salario"')), "sueldos en personas"

    SALIDA.mkdir(exist_ok=True)
    for nombre, obj in (("clientes", clientes), ("alarmas", alarmas), ("logos", logos), ("personas", personas),
                        ("asignaciones", asignaciones), ("para_confirmar", para_confirmar),
                        ("ids_clientes", ids_cli), ("meta", meta)):
        tmp = SALIDA / f".{nombre}.json.tmp"
        tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=1))
        tmp.replace(SALIDA / f"{nombre}.json")
    sin_acc = [c["id"] for c in clientes if c.get("sin_account")]
    print(f"clientes {len(clientes)} · alarmas {len(alarmas)} · logos {len(logos)} · personas {len(personas)} "
          f"({sum(p.get('activo', False) for p in personas)} activas) · asignaciones {len(asignaciones)} · "
          f"para confirmar {len(para_confirmar)} · respuestas aplicadas {len(aplicado)} · sin account {len(sin_acc)}")


if __name__ == "__main__":
    main()

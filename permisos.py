"""
permisos.py · el mismo intérprete que permisos.js, en Python, para servir.py.

Lee reglas_permisos.json (la única fuente de reglas) y expone:
  ambito(persona) · cartera_por_silla(persona, asignaciones) · cartera(...) · ver(persona, dato, cp)
  recortar(persona, crudo)  → el mismo resultado que datos.js recortar(), pero en el servidor.

Si cambias algo aquí, cámbialo igual en permisos.js / datos.js: la paridad la comprueban
`pruebas_permisos_servicio.py` (Python frente a JS) y `migracion/vectores_permisos.py` (todas las personas).
"""
import json
import os
import re
import threading
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path
try:
    from zoneinfo import ZoneInfo
    MADRID = ZoneInfo("Europe/Madrid")
except Exception:          # pragma: no cover
    MADRID = None

AQUI = Path(__file__).resolve().parent
REGLAS = json.loads((AQUI / "reglas_permisos.json").read_text())
PUESTO = {p["id"]: p for p in REGLAS["puestos"]}


def recargar_reglas():
    """Ronda 6: relee reglas_permisos.json EN SITIO (mismos objetos REGLAS y PUESTO, que importan otros módulos)."""
    nuevas = json.loads((AQUI / "reglas_permisos.json").read_text())
    REGLAS.clear()
    REGLAS.update(nuevas)
    PUESTO.clear()
    PUESTO.update({p["id"]: p for p in REGLAS["puestos"]})


def ahora_madrid():
    """R16 (N6): la hora de Madrid, sin zona, igual en el Mac (CEST) que en Render (UTC). RO_RELOJ=«AAAA-MM-DDTHH:MM»
    (hora de Madrid) fija el reloj en las pruebas. Las horas de la base (datetime('now')) siguen en UTC; las FECHAS de
    negocio (hoy, desde/hasta de asignaciones, bajas, foto del día) van siempre en hora de Madrid."""
    fijo = os.environ.get("RO_RELOJ")
    if fijo:
        try:
            return datetime.fromisoformat(fijo.replace(" ", "T"))
        except ValueError:
            pass
    return datetime.now(MADRID).replace(tzinfo=None) if MADRID else datetime.now()


def hoy_iso():
    return ahora_madrid().date().isoformat()


def _sillas_de(persona):
    return {s for p in persona.get("puestos", []) for s in REGLAS["sillas_de_puesto"].get(p, [])}


def _vigente(a, hoy):
    if a.get("desde") and a["desde"] > hoy:
        return False
    if a.get("hasta") and a["hasta"] < hoy:
        return False
    return True


# Contratos explícitos: solo «sí» confirma un servicio. No equivale a tener una silla.
SERVICIOS_SILLA = {
    "seo": ("seo",), "trafficker": ("publicidad",), "crm": ("crm_ghl",),
    "ghl": ("crm_ghl",), "web": ("web", "mantenimiento"),
    "redes": ("redes", "social_media"), "outreach": ("outreach",),
}
SERVICIOS_JEFATURA = {
    "jefa_seo": ("seo",), "jefa_publicidad": ("publicidad",),
    "jefa_crm": ("crm_ghl", "outreach"),
}


def servicio_contratado(cliente, claves):
    servicios = cliente.get("servicios") or {}
    return any(servicios.get(k) == "sí" for k in claves)


def cartera_por_silla(persona, asignaciones, hoy=None, clientes=None):
    hoy = hoy or hoy_iso()
    sillas = _sillas_de(persona)
    out = {}
    for a in asignaciones:
        if a.get("persona_id") != persona["id"] or not _vigente(a, hoy):
            continue
        if a.get("suplencia") and not a.get("hasta"):
            continue
        if a.get("silla") and sillas and a["silla"] not in sillas and not a.get("suplencia"):
            continue
        out.setdefault(a.get("silla") or "sin_silla", set()).add(a["cliente_id"])
    # Tomás 3-oct («sillas_de_equipo»): web y redes son equipos transversales. Con la silla por su puesto, sus clientes
    # de esa silla son TODOS los que tienen esa silla asignada a alguien (el servicio activo), no solo los suyos.
    for silla in REGLAS.get("sillas_de_equipo") or []:
        if silla in sillas:
            todos = {a["cliente_id"] for a in asignaciones if a.get("silla") == silla and _vigente(a, hoy)
                     and not (a.get("suplencia") and not a.get("hasta"))}
            if todos:
                out.setdefault(silla, set()).update(todos)
    # L-25 (Tomás, 4-oct): «altas» es una silla virtual. Su técnico lleva los clientes con alta firmada en los últimos
    # 90 días (verdad «nuevo»), sin filas en asignaciones.
    if "altas" in sillas and clientes is not None:
        nuevos = {c["id"] for c in clientes if c.get("nuevo")}
        if nuevos:
            out.setdefault("altas", set()).update(nuevos)
    if clientes is not None:
        por_id = {c["id"]: c for c in clientes}
        for silla, ids in out.items():
            claves = SERVICIOS_SILLA.get(silla)
            if claves:
                out[silla] = {cid for cid in ids if cid in por_id and servicio_contratado(por_id[cid], claves)}
        # Las jefaturas ven su servicio completo. Web/redes son transversales;
        # SEO y paid individuales mantienen sus asignaciones de clientes contratados.
        for silla in REGLAS.get("sillas_de_equipo") or []:
            if silla in sillas and silla in SERVICIOS_SILLA:
                out[silla] = {c["id"] for c in clientes if servicio_contratado(c, SERVICIOS_SILLA[silla])}
        for puesto, claves in SERVICIOS_JEFATURA.items():
            if puesto in persona.get("puestos", []):
                out["servicio_" + puesto] = {c["id"] for c in clientes if servicio_contratado(c, claves)}
    return out


def cartera(persona, asignaciones, hoy=None, clientes=None):
    ids = set()
    for s in cartera_por_silla(persona, asignaciones, hoy, clientes).values():
        ids |= s
    return ids


def ambito(persona):
    orden = REGLAS["orden_ambitos"]
    mejor = "ninguno"
    for p in persona.get("puestos", []):
        a = PUESTO.get(p, {}).get("ambito", "ninguno")
        if orden.index(a) > orden.index(mejor):
            mejor = a
    return mejor


def _es_jefe(persona, objetivo):
    if not objetivo:
        return False
    if objetivo.get("jefe") == persona["id"]:
        return True
    subordinados = {s for p in persona.get("puestos", []) for s in REGLAS["jefe_de_puesto"].get(p, [])}
    return any(p in subordinados for p in objetivo.get("puestos", []))


def _cumple(caso, persona, dato, cp):
    puestos = persona.get("puestos", [])
    if "identidades" in caso and persona.get("id") not in caso["identidades"]:
        return False
    if "puestos" in caso and not any(p in caso["puestos"] for p in puestos):
        return False
    if "ambito" in caso and ambito(persona) not in caso["ambito"]:
        return False
    if caso.get("cartera"):
        cid = dato.get("cliente_id")
        if not cid:
            return False
        if caso["cartera"] is True:
            if cid not in cp.get("cartera_ids", set()):
                return False
        else:
            por = cp.get("cartera_por_silla")
            conjunto = por.get(caso["cartera"], set()) if por is not None else cp.get("cartera_ids", set())
            if cid not in conjunto:
                return False
    if caso.get("sin_cliente") and dato.get("cliente_id"):
        return False
    if caso.get("propio") and dato.get("persona_id") != persona["id"]:
        return False
    if caso.get("jefe"):
        obj = next((p for p in cp.get("personas", []) if p["id"] == dato.get("persona_id")), None)
        if not _es_jefe(persona, obj):
            return False
    if caso.get("participante") and persona["id"] not in (dato.get("participantes") or []):
        return False
    if caso.get("cliente_nuevo") and not dato.get("cliente_nuevo"):   # A4: solo clientes en alta (lo decide quien llama: servidor = clientes.json)
        return False
    return True


# ------------------------------------------------ «ver como» = mínimo de las dos personas (ronda 6, C3)
# En «ver como», servir.py activa aquí a la persona REAL para la petición en curso. Desde entonces, cada ver() y
# nivel_modulo() sobre la persona vista devuelve lo que ven LAS DOS (el mínimo): Mili viendo como Cecilia no lee
# sueldos; viendo como Tomás no lee finanzas, panel de dirección ni leads de Tomás. Sin «ver como», nada cambia.
_HILO = threading.local()
_ORDEN_NIVEL = {"no": 0, "enmascarado": 1, "resumen": 2, "completo": 3}


@contextmanager
def mirando_como(real, crudo):
    """Durante el bloque, ver() y nivel_modulo() de cualquier otra persona se limitan a lo que ve también «real»."""
    previo = getattr(_HILO, "real", None)
    _HILO.real = (real, contexto(real, crudo))
    try:
        yield
    finally:
        _HILO.real = previo


def puestos_de(persona):
    """Ronda 7: los puestos con los que se decide algo «por puesto» fuera de ver(). En «ver como», solo los que tienen
    LAS DOS personas (Mili viendo como Tomás no tiene «direccion»). Sin «ver como», los de la persona."""
    propios = set(persona.get("puestos", []))
    activo = getattr(_HILO, "real", None)
    if activo and activo[0]["id"] != persona["id"]:
        return propios & set(activo[0].get("puestos", []))
    return propios


def ver(persona, dato, cp=None):
    r = _ver(persona, dato, cp)
    activo = getattr(_HILO, "real", None)
    if activo and activo[0]["id"] != persona["id"] and r["ok"]:
        r2 = _ver(activo[0], dato, activo[1])
        if not r2["ok"]:
            return {"ok": False, "nivel": "no", "motivo": "En «ver como» solo se ve lo que ven las dos personas. " + (r2.get("motivo") or "")}
        if _ORDEN_NIVEL.get(r2["nivel"], 0) < _ORDEN_NIVEL.get(r["nivel"], 0):
            r = {**r, "nivel": r2["nivel"]}
        if not r2.get("desenmascarable"):
            r.pop("desenmascarable", None)
    return r


def _ver(persona, dato, cp=None):
    cp = cp or {}
    if dato.get("cliente_id") and solo_su_cartera(persona) and dato["cliente_id"] not in cp.get("cartera_ids", set()):
        return {"ok": False, "nivel": "no", "motivo": "Este cliente no está en tu cartera ni en tu servicio contratado."}
    regla = REGLAS["tipos"].get(dato.get("tipo"))
    if not regla:
        return {"ok": False, "nivel": "no", "motivo": f"Tipo de dato desconocido: {dato.get('tipo')}. Por defecto, no se enseña."}
    if regla.get("nunca"):
        return {"ok": False, "nivel": "no", "motivo": regla["nunca"]}
    for caso in regla.get("si", []):
        if not _cumple(caso, persona, dato, cp):
            continue
        r = {"ok": True, "nivel": caso.get("nivel", "completo"), "motivo": caso.get("motivo", "")}
        if caso.get("desenmascarable"):
            r["desenmascarable"] = True
        return r
    return {"ok": False, "nivel": "no", "motivo": regla.get("no") or "No visible para tu puesto."}


def solo_su_cartera(persona):
    """Tomás 3-oct (58_FEEDBACK_TOMAS_03OCT): ¿esta persona solo recibe los clientes de su cartera, en todas partes?
    Accounts y equipos/jefaturas de servicio tienen scope limitado; los puestos con ámbito todos lo conservan.
    En «ver como» manda la persona vista (Tomás viendo como Lucía recibe lo de Lucía)."""
    if ambito(persona) == "todos":
        return False
    puestos = set(persona.get("puestos", []))
    return bool(puestos & (set(REGLAS.get("solo_su_cartera", {}).get("puestos") or [])
                          | set(SERVICIOS_JEFATURA)
                          | {p for p in puestos if _sillas_de({"puestos": [p]}) & set(SERVICIOS_SILLA)}))


def contexto(persona, crudo):
    # Consumidores de horas pueden no tener catálogo: servicio desconocido no concede cartera.
    clientes = crudo.get("clientes") or []
    por_silla = cartera_por_silla(persona, crudo["asignaciones"], clientes=clientes)
    ids = set()
    for s in por_silla.values():
        ids |= s
    return {"cartera_ids": ids, "cartera_por_silla": por_silla, "personas": crudo["personas"], "clientes_por_id": {c["id"]: c for c in clientes}}


# ---------------------------------------------------------------- recorte
COMUNES = ["id", "nombre", "responsable_id", "responsable_texto", "salud", "salud_fuente", "semaforo", "nuevo", "sin_account", "tipo_negocio", "activo_confirmado"]
DETALLE = ["web", "descripcion", "descripcion_completa", "alta", "tickets_abiertos", "pend_horas", "dias_sin_reunion", "ult_reunion",
           "prox_reunion", "informe_anterior", "revision48", "enlace_clickup", "equipo", "servicios"]
PERSONA_PUBLICA = ["id", "nombre", "alias", "puestos", "prueba", "estado", "activo", "jefe", "zona", "rol", "pais", "fecha_ingreso", "cumple_dia_mes", "etiquetas"]


def directorio(personas):
    """Lo que cualquiera puede saber de una persona: nombre, alias, puestos y jefe. Sin correo ni horas."""
    return [{k: p.get(k) for k in PERSONA_PUBLICA} for p in personas]


def recortar(persona, crudo):
    """Igual que datos.js recortar(): todos los clientes con lo común; detalle, cuota e inversión según ver()."""
    cp = contexto(persona, crudo)
    v = lambda d: ver(persona, d, cp)
    nombre = {p["id"]: p.get("alias") or p["nombre"] for p in crudo["personas"]}
    clientes = []
    solo_mios = solo_su_cartera(persona)          # Tomás 3-oct: el account no recibe ni el nombre de un cliente ajeno
    for c in crudo["clientes"]:
        if solo_mios and c["id"] not in cp["cartera_ids"]:
            continue
        out = {k: c.get(k) for k in COMUNES}
        out["logo"] = crudo["logos"].get(c["id"])
        out["responsable"] = nombre.get(c.get("responsable_id")) if c.get("responsable_id") else (c.get("responsable_texto") or "sin responsable")
        out["enCartera"] = c["id"] in cp["cartera_ids"]
        out["detalle"] = v({"tipo": "cliente_detalle", "cliente_id": c["id"]})["ok"]
        if out["detalle"]:
            quita = importes_a_quitar(v({"tipo": "cuota", "cliente_id": c["id"]})["ok"], v({"tipo": "inversion", "cliente_id": c["id"]})["ok"], v({"tipo": "cobros", "cliente_id": c["id"]})["ok"], v({"tipo": "dinero_empresa", "cliente_id": c["id"]})["ok"])
            for k in DETALLE:
                # Ronda 6 (A2): «servicios.publicidad_fuente» y otros textos llevan euros; sin cuota o sin inversión, esos fuera.
                out[k] = sin_importes(c.get(k), quita)
        if v({"tipo": "cuota", "cliente_id": c["id"]})["ok"]:
            out["cuota"] = c.get("cuota")
            out["cuota_fuente"] = c.get("cuota_fuente")   # ronda 8: de dónde sale (fuentes_dinero/cuotas.json)
        if v({"tipo": "inversion", "cliente_id": c["id"]})["ok"]:
            out["publicidad_30d"] = c.get("publicidad_30d")
        clientes.append(out)
    por_id = {c["id"]: c for c in clientes}

    alarmas = []
    for a in crudo["alarmas"]:
        resp = nombre.get(a.get("responsable_id")) if a.get("responsable_id") else (a.get("responsable_texto") or "sin responsable")
        if a.get("ambito") == "cliente":
            if solo_mios and a.get("cliente_id") not in cp["cartera_ids"]:
                continue
            fila = {k: a.get(k) for k in ("id", "cliente_id", "cliente", "gravedad", "tipo", "desde", "responsable_id")}
            fila.update({"ambito": "cliente", "responsable": resp})
            if por_id.get(a.get("cliente_id"), {}).get("detalle") and v({"tipo": "alarma_detalle", "cliente_id": a.get("cliente_id")})["ok"]:
                quita = importes_a_quitar(v({"tipo": "cuota", "cliente_id": a.get("cliente_id")})["ok"], v({"tipo": "inversion", "cliente_id": a.get("cliente_id")})["ok"], v({"tipo": "cobros", "cliente_id": a.get("cliente_id")})["ok"], v({"tipo": "dinero_empresa", "cliente_id": a.get("cliente_id")})["ok"])
                fila.update({"texto": sin_importes(a.get("texto"), quita),
                             "accion": sin_importes(a.get("accion"), quita),
                             "enlace": enlace_seguro(a.get("enlace"))})
            alarmas.append(fila)
        else:
            if a.get("responsable_id"):
                ok = v({"tipo": "alarma_persona", "persona_id": a["responsable_id"]})["ok"]
            else:
                ok = any(p in ("direccion", "operaciones") for p in persona.get("puestos", []))
            if ok:
                alarmas.append({**a, "responsable": resp})

    mias = [a for a in crudo["asignaciones"] if a.get("persona_id") == persona["id"]
            and (not solo_mios or a.get("cliente_id") in cp["cartera_ids"])]
    return {
        "clientes": clientes,
        "alarmas": alarmas,
        "carteraIds": sorted(cp["cartera_ids"]),
        "carteraPorSilla": {k: sorted(s) for k, s in cp["cartera_por_silla"].items()},
        "ambito": ambito(persona),
        "soloSuCartera": solo_mios,
        "personas": directorio(crudo["personas"]),
        "asignaciones": mias,
        "meta": meta_de_cartera(crudo["meta"]) if solo_mios else crudo["meta"],
    }


def meta_de_cartera(meta):
    """La carcasa necesita fechas y estado de fuentes, no contadores/historia globales."""
    out = {k: meta[k] for k in ("generado", "construido") if k in meta}
    if isinstance(meta.get("fuentes"), list):
        out["fuentes"] = [{k: f[k] for k in ("fuente", "estado", "generado", "fecha", "actualizado") if k in f}
                          for f in meta["fuentes"] if isinstance(f, dict)]
    return out


def solo_filas_de(o, ids):
    """Tomás 3-oct: a cualquier profundidad, fuera las filas con cliente_id de un cliente que no está en «ids»."""
    if isinstance(o, dict):
        return {k: solo_filas_de(v, ids) for k, v in o.items()}
    if isinstance(o, list):
        return [solo_filas_de(x, ids) for x in o if not (isinstance(x, dict) and x.get("cliente_id") and x["cliente_id"] not in ids)]
    return o


# ------------------------------------------------------------ enmascarado
def enmascarar(texto=""):
    texto = texto or ""
    if "@" in texto:
        u, d = texto.split("@", 1)
        return f"{u[:1]}···@{d}"
    if len(re.sub(r"\D", "", texto)) >= 6:
        return re.sub(r"\d(?=(?:\D*\d){3})", "·", texto)
    return " ".join((p[0] + "···") if p else p for p in texto.split())


# ------------------------------------------------------- módulos por puesto
# Mismo criterio que app.js: los metadatos de modulos/indice.js y, si el fichero del módulo exporta
# su propio puestos_que_lo_ven, manda el del fichero. Se leen del código (sin ejecutar JS).
MODULOS_DIR = AQUI / "modulos"
_RANGO = {"resumen": 1, "suyo": 2, "todo": 3}


def _objeto_js(texto, constantes):
    """Convierte un literal sencillo { clave: 'valor' | null, ...CONST } en dict."""
    texto = texto.strip()
    if texto in constantes:
        return dict(constantes[texto])
    out = {}
    for trozo in re.findall(r"\.\.\.(\w+)", texto):
        out.update(constantes.get(trozo, {}))
    for k, v in re.findall(r"""['"]?([\w*]+)['"]?\s*:\s*('(?:todo|suyo|resumen)'|"(?:todo|suyo|resumen)"|null)""", texto):
        out[k] = None if v == "null" else v.strip("'\"")
    return out


def cargar_modulos():
    """{id_modulo: puestos_que_lo_ven} leído de indice.js y de cada fichero de módulo."""
    indice = (MODULOS_DIR / "indice.js").read_text()
    constantes = {}
    for nombre, cuerpo in re.findall(r"const (\w+) = (\{[^}]*\});", indice):
        constantes[nombre] = _objeto_js(cuerpo, constantes)
    modulos = {}
    for m in re.finditer(r"\{\s*id:\s*'([\w\-]+)'(.*?)resumen:", indice, re.S):
        mid, cuerpo = m.group(1), m.group(2)
        pq = re.search(r"puestos_que_lo_ven:\s*(\{[^}]*\}|\w+)", cuerpo)
        fichero = re.search(r"fichero:\s*'\./([\w\-]+\.js)'", cuerpo)
        mapa = _objeto_js(pq.group(1), constantes) if pq else {}
        if fichero and (MODULOS_DIR / fichero.group(1)).exists():
            propio = re.search(r"puestos_que_lo_ven:\s*(\{[^}]*\})", (MODULOS_DIR / fichero.group(1)).read_text())
            if propio:
                mapa = _objeto_js(propio.group(1), constantes)
        modulos[mid] = mapa
    # R16c: «modulos_sin_puesto» de reglas_permisos.json manda sobre el índice y el fichero (setters fuera de «En rojo»).
    for mid, fuera in (REGLAS.get("modulos_sin_puesto") or {}).items():
        if mid in modulos:
            modulos[mid] = {**modulos[mid], **{p: None for p in fuera}}
    return modulos


def nivel_modulo(persona, mapa):
    """Igual que nivelModulo() de permisos.js. En «ver como», el mínimo de las dos personas (ronda 6)."""
    n = _nivel_modulo(persona, mapa)
    activo = getattr(_HILO, "real", None)
    if n and activo and activo[0]["id"] != persona["id"]:
        n2 = _nivel_modulo(activo[0], mapa)
        n = None if not n2 else (n if _RANGO[n] <= _RANGO[n2] else n2)
    return n


def _nivel_modulo(persona, mapa):
    mejor = None
    for p in persona.get("puestos", []):
        n = mapa[p] if p in mapa else mapa.get("*")
        if n and (not mejor or _RANGO[n] > _RANGO[mejor]):
            mejor = n
    return mejor


# ------------------------------------------------------- textos con dinero y enlaces (ronda 6, A2-A4)
# R16 (B7): también «1,5 k€», «1470 eur», «EUR 500», «2 mil euros» y cifras en letra («mil ochocientos euros»).
_NUM_LETRA = (r"(?:(?:un|una|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|once|doce|quince|veinte|veinti\w+|treinta|"
              r"cuarenta|cincuenta|sesenta|setenta|ochenta|noventa|cien|ciento|doscient[oa]s|trescient[oa]s|cuatrocient[oa]s|"
              r"quinient[oa]s|seiscient[oa]s|setecient[oa]s|ochocient[oa]s|novecient[oa]s|mil|millón|millones|de|y)\s+)*"
              r"(?:mil|cien|ciento|\w+cient[oa]s|millón|millones|veinte|treinta|cuarenta|cincuenta|sesenta|setenta|ochenta|noventa)\s+(?:de\s+)?")
RE_IMPORTE = re.compile(r"(?i:~?\d[\d.,]*(?:\s*[-–]\s*\d[\d.,]*)?\s*(?:k\s*€|€|mil\s+euros?|millones\s+de\s+euros?|euros?\b|eur\b|\$|usd\b)|"
                        r"(?:€|\$|\beur\b)\s*\d[\d.,]*(?:\s*k\b)?|\b" + _NUM_LETRA + r"euros?\b)")


# Ronda 11 (B-A02, auditoría 34): nada de «[importe]» a la vista. Se quita la frase que lleva el importe o, si es la única,
# el importe con su preposición («Gasto en Meta: 142,58 €» → «Gasto en Meta»; «2 leads a 167 € cada uno» → «2 leads»).
# Y se distingue de qué es cada importe por las palabras de alrededor: con «/mes», «cuota», «factura»… es CUOTA; el
# «techo» general sigue ligado a inversión. 580: marcador más próximo en la misma cláusula;
# un importe desconocido no se convierte automáticamente en inversión. Familias adicionales requieren contexto explícito.
RE_CUOTA_CERCA = re.compile(r"(?i)(/\s*mes|al mes|mensual|cuota|factur|recurrente|cobr|impag|mantenimiento)")
RE_TECHO_CERCA = re.compile(r"(?i)techo")
_CONECTOR = r"(?:\s*(?:[:=]|\bde\b|\ba\b|\bcon\b|\bpor\b|\ben\b|\bsobre\b))?"
_COLA = r"(?:\s*(?:/\s*(?:mes|día|dia|lead|cita|mes\b)|al mes|cada uno|cada una|por lead|por cita))?"


def tipo_importe(texto, ini, fin):
    from clasificacion_importes_580 import clasificar_importe_580
    return clasificar_importe_580(texto, ini, fin)


def _fuera(tipo, quitar):
    from clasificacion_importes_580 import fuera_importe_580
    return fuera_importe_580(tipo, quitar)


def _quitar_importes_texto(t, quitar):
    malos = [m for m in RE_IMPORTE.finditer(t) if _fuera(tipo_importe(t, m.start(), m.end()), quitar)]
    if not malos:
        return t
    # 1) paréntesis con importe: fuera enteros
    t2 = re.sub(r"\s*\([^()]*\)", lambda m: "" if any(m.start() <= x.start() < m.end() for x in malos) else m.group(0), t)
    # 2) frases (o trozos «·») con importe: fuera, si queda alguna sin él
    trozos = re.split(r"(?<=[.;!?])\s+|\s+·\s+", t2)
    con = [any(_fuera(tipo_importe(x, m.start(), m.end()), quitar) for m in RE_IMPORTE.finditer(x)) for x in trozos]
    if any(con) and not all(con):
        t2 = " ".join(x for x, c in zip(trozos, con) if not c)
    # 3) lo que quede: el importe con su preposición y su unidad
    def fuera(m):
        return "" if _fuera(tipo_importe(m.string, m.start("imp"), m.end("imp")), quitar) else m.group(0)
    t2 = re.sub(_CONECTOR + r"\s*(?P<imp>" + RE_IMPORTE.pattern + r")" + _COLA, fuera, t2)
    t2 = re.sub(r"\s{2,}", " ", t2)
    t2 = re.sub(r"\s+([,.;:)])", r"\1", t2)
    t2 = re.sub(r"([(:,])\s*([,.;)])", r"\2", t2).strip(" ,;:·-–—")
    return t2


# Ronda 12 (R13): lo que escribe la gente en un buscador NO es dinero nuestro. Las listas de búsquedas, consultas y
# palabras clave (Search Console, Google Ads, SEO) llegan enteras: «delito fiscal 120.000 euros anuales» no se toca.
CLAVES_TEXTO_LIBRE = re.compile(r"(?i)^(consultas?|b[uú]squedas?|keywords?|palabras?_?clave|palabras?|t[eé]rminos?(_b[uú]squeda)?|"
                                r"search_?terms?|quer(y|ies)|top_consultas|consultas_.*|busquedas_.*|keywords_.*)$")


# Dentro de esas listas solo se quita el importe escrito con símbolo («€0,00», «$500»): es lo que trae una exportación
# de Google Ads (coste por término) colada como consulta; «120.000 euros» escrito por quien busca se queda.
RE_IMPORTE_SIMBOLO = re.compile(r"\d[\d.,]*\s*(?:€|\$)|(?:€|\$)\s*\d[\d.,]*")


def sin_importes_libre(o, quitar=("cuota", "inversion", "cobros", "dinero_empresa")):
    """Ronda 12 (R13): para listas de búsquedas/consultas/palabras clave. Solo quita importes con símbolo (€ o $)."""
    quitar = set(quitar or ())
    if not quitar:
        return o
    if isinstance(o, dict):
        return {k: sin_importes_libre(x, quitar) for k, x in o.items()}
    if isinstance(o, list):
        return [sin_importes_libre(x, quitar) for x in o]
    if not isinstance(o, str) or not RE_IMPORTE_SIMBOLO.search(o):
        return o
    t = RE_IMPORTE_SIMBOLO.sub(lambda m: "" if _fuera(tipo_importe(m.string, m.start(), m.end()), quitar) else m.group(0), o)
    return re.sub(r"\s{2,}", " ", t).strip()


def sin_importes(o, quitar=("cuota", "inversion", "cobros", "dinero_empresa")):
    """Quita importes (1.470 €, 297 €/día, $500…) de cualquier texto, a cualquier profundidad, sin dejar huecos.
    «quitar»: qué importes («cuota», «inversion»); por defecto, los dos. El techo general de coste por lead solo se deja
    a quien ve la inversión."""
    quitar = set(quitar or ())
    if not quitar:
        return o
    if isinstance(o, dict):
        return {k: (sin_importes_libre(x, quitar) if CLAVES_TEXTO_LIBRE.match(str(k)) else sin_importes(x, quitar)) for k, x in o.items()}
    if isinstance(o, list):
        return [sin_importes(x, quitar) for x in o]
    return _quitar_importes_texto(o, quitar) if isinstance(o, str) else o


def importes_a_quitar(ve_cuota, ve_inversion, ve_cobros=None, ve_dinero_empresa=None):
    """Qué importes no ve una persona en los textos de un cliente."""
    return (tuple(k for k, ve in (("cuota", ve_cuota), ("inversion", ve_inversion)) if not ve)
            + tuple(k for k, ve in (("cobros", ve_cobros), ("dinero_empresa", ve_dinero_empresa)) if ve is False))


ESQUEMAS_OK = re.compile(r"^(https?://|mailto:|tel:|sip:|#|/(?!/)|\./|\.\./|[\w\-]+\.html)", re.I)


def enlace_seguro(u):
    """Solo http(s), mailto, tel, sip (y wa.me, que es https), anclas y rutas relativas. Lo demás (javascript:, data:…) → None."""
    if not isinstance(u, str) or not u.strip():
        return u
    return u.strip() if ESQUEMAS_OK.match(u.strip()) else None

#!/usr/bin/env python3
"""
altas_personas.py · N9 «Alta de nuevos miembros» (2-oct-2026, noche). Lógica de servidor de Ajustes › Altas y bajas.

Dar de alta, cambiar o dar de baja a una persona desde Ajustes en menos de 2 minutos, sin tocar código:
  · alta: nombre, puesto (plantilla por puesto: qué ve y qué hace), jefe, zona horaria, fecha de entrada, cumpleaños
    (día y mes), correo de entrada (privado) y cartera inicial por silla (opcional).
  · al guardar: persona + asignaciones en la base (historial + rastro, imborrables), vista recalculada, comprobación
    automática de permisos en llano (qué verá y qué no, con 3 pantallas de muestra en «ver como»), TAREA para Tomás de
    añadir el correo a Cloudflare Access (lista_access.txt al día; Cloudflare NO se toca) y guía de bienvenida del puesto.
  · baja: tarea de quitar el acceso, asignaciones cerradas con fecha (nada se borra) y propuesta de reparto de la cartera
    (lo decide Mili o Tomás en la misma pantalla).
  · cambio de puesto, jefe, zona o cartera: misma comprobación, antes y después.

Reglas: puestos de reglas_permisos.json → puestos_solo_tomas solo los da, quita o cambia Tomás (y a quien ya tiene uno,
solo Tomás le cambia puesto, jefe, estado o correo); Mili da de alta los operativos. Nadie se cambia a sí mismo.
Datos: SOLO nombre, puesto, jefe, zona, fechas y cumpleaños (día y mes). Nunca teléfonos, direcciones ni correos
personales; el correo de entrada va a data/_privado/correos_entrada.json («correos» y «desde_la_app»), que no se sirve.

Se engancha a servir.py como ia.py (envuelve _api_get y api_post para /api/altas/*, y Estado.aplicar_ajustes para
reaplicar las altas guardadas en el historial). Rutas:
  GET  /api/altas                   plantillas, puestos que puede dar, personas, clientes, zonas y tareas
  GET  /api/altas/comprobar?id=     comprobación de permisos de una persona (en llano)
  GET  /api/altas/guia?puesto=      guía de bienvenida del puesto (../40_GUIA_EQUIPO/)
  POST /api/altas/alta | cambio | baja | repartir | tarea_hecha

Pruebas sin tocar nada real: RO_DB=<copia> RO_CORREOS_ENTRADA=<copia> RO_LISTA_ACCESS=<copia> (ver pruebas_seguridad.py, N9).
"""
import json
import os
import re
import unicodedata
from datetime import date, timedelta
from pathlib import Path

AQUI = Path(__file__).resolve().parent
GUIAS = AQUI.parent / "40_GUIA_EQUIPO"
S = None          # el módulo servir (lo pone enganchar)
P = None          # permisos


def ruta_correos():
    return Path(os.environ.get("RO_CORREOS_ENTRADA") or AQUI / "data" / "_privado" / "correos_entrada.json")


def ruta_lista():
    return Path(os.environ.get("RO_LISTA_ACCESS") or AQUI / "despliegue" / "lista_access.txt")


def ruta_departamentos():
    return Path(os.environ.get("RO_DEPARTAMENTOS") or AQUI / "data" / "departamentos.json")


DUDAS = AQUI / "fuentes_equipo" / "dudas_roles.json"


DOMINIOS_RO = ("@rankingonline.com", "@rankingonlinemarketing.com")
ZONAS = [("Europe/Madrid", "España (Madrid)"), ("America/Argentina/Buenos_Aires", "Argentina (Buenos Aires)"),
         ("America/Caracas", "Venezuela (Caracas)"), ("America/Bogota", "Colombia (Bogotá)"), ("America/Mexico_City", "México"),
         ("America/Montevideo", "Uruguay"), ("America/Santiago", "Chile"), ("America/Lima", "Perú"), ("Atlantic/Canary", "Canarias")]
PAIS_DE_ZONA = {"Europe/Madrid": "España", "Atlantic/Canary": "España", "America/Argentina/Buenos_Aires": "Argentina",
                "America/Caracas": "Venezuela", "America/Bogota": "Colombia", "America/Mexico_City": "México",
                "America/Montevideo": "Uruguay", "America/Santiago": "Chile", "America/Lima": "Perú"}
# Claves que el alta acepta. Cualquier otra (teléfono, dirección, sueldo, DNI, correo personal…) → 400.
CLAVES_ALTA = {"nombre", "puestos", "jefe", "zona", "fecha_entrada", "cumple", "correo_entrada", "cartera", "horas_mes", "imputa_horas"}

# Qué hace cada puesto (en llano). Qué VE sale solo de los módulos y de reglas_permisos.json (no se escribe a mano).
QUE_HACE = {
    "direccion": "Decide. Ve todo: clientes, dinero, equipo y el rastro completo.",
    "finanzas_direccion": "Caja, cobros, márgenes y dinero de la empresa.",
    "administracion": "Facturación, cobros e impagos.",
    "operaciones": "Lleva el día a día del equipo: carteras, asignaciones, «ver como» y Ajustes.",
    "proyectos": "Diseña la oferta y sigue los proyectos de todos los clientes.",
    "rrhh": "Personas: incorporaciones, ausencias, uno a uno y salidas. Sueldos solo con Tomás.",
    "account": "Es la persona de contacto de sus clientes: correos, reuniones, informes y que los resultados lleguen.",
    "trafficker": "Lleva la publicidad de Meta de sus clientes: campañas, presupuesto, leads y coste por lead.",
    "jefa_publicidad": "Dirige a los traffickers y vigila la publicidad de todos los clientes.",
    "especialista_ghl": "Monta y cuida el CRM (GoHighLevel) de sus clientes: embudos, flujos y que los leads lleguen.",
    "jefa_crm": "Dirige el CRM y el outreach de todos los clientes.",
    "tecnico_altas": "Pone en marcha a los clientes nuevos: accesos, conexiones y encendido en plazo.",
    "jefa_seo": "Dirige SEO, ficha de Google y webs.",
    "seo": "SEO técnico y contenidos de sus clientes.",
    "ficha_google": "Ficha de Google (Business Profile) de sus clientes: reseñas, publicaciones y posiciones.",
    "web": "Tareas de web que le asignan.",
    "redes": "Publicaciones de redes que le asignan.",
    "produccion": "Piezas creativas (copy, diseño, vídeo) que le asignan.",
    "setters": "Llama y confirma las citas de los prospectos de RO. Solo ve sus llamadas y su marcador.",
    "ventas_ro": "Vende los servicios de RO a prospectos.",
    "outreach": "Prospección y outreach: listas, mensajes y respuestas.",
}
GUIA_DE_PUESTO = {
    "direccion": "01_DIRECCION_TOMAS.md", "finanzas_direccion": "01_DIRECCION_TOMAS.md", "ventas_ro": "01_DIRECCION_TOMAS.md",
    "administracion": "02_ADMINISTRACION_SOFIA.md", "operaciones": "03_OPERACIONES_MILI.md",
    "proyectos": "04_PROYECTOS_Y_SEO_COTI.md", "jefa_seo": "04_PROYECTOS_Y_SEO_COTI.md", "rrhh": "05_RRHH_CECILIA.md",
    "account": "06_ACCOUNTS.md", "trafficker": "07_PUBLICIDAD.md", "jefa_publicidad": "07_PUBLICIDAD.md",
    "especialista_ghl": "08_CRM.md", "jefa_crm": "08_CRM.md", "tecnico_altas": "09_ALTAS_AGUS.md",
    "seo": "10_SEO_Y_FICHA_DE_GOOGLE.md", "ficha_google": "10_SEO_Y_FICHA_DE_GOOGLE.md", "web": "11_WEB.md",
    "redes": "12_REDES.md", "produccion": "13_PRODUCCION.md", "setters": "14_SETTERS.md", "outreach": "15_OUTREACH.md",
}
SILLA_NOMBRE = {"account": "account", "trafficker": "trafficker", "crm": "CRM", "ghl": "CRM", "seo": "SEO", "web": "web",
                "redes": "redes", "produccion": "producción", "outreach": "outreach"}

TABLA_SQL = """
CREATE TABLE IF NOT EXISTS altas_tareas (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  creada TEXT NOT NULL DEFAULT (datetime('now')),
  para TEXT NOT NULL,                                -- tomas | mili_o_tomas
  tipo TEXT NOT NULL CHECK (tipo IN ('access_anadir','access_quitar','repartir_cartera')),
  persona_id TEXT NOT NULL,
  texto TEXT NOT NULL,                               -- en llano y SIN el correo (el correo vive en data/_privado)
  quien TEXT NOT NULL,
  estado TEXT NOT NULL DEFAULT 'pendiente' CHECK (estado IN ('pendiente','hecha')),
  hecha TEXT, hecha_por TEXT);
CREATE TRIGGER IF NOT EXISTS altas_tareas_sin_delete BEFORE DELETE ON altas_tareas BEGIN SELECT RAISE(ABORT, 'Una tarea no se borra'); END;
CREATE TRIGGER IF NOT EXISTS altas_tareas_solo_estado BEFORE UPDATE ON altas_tareas
  WHEN NEW.para IS NOT OLD.para OR NEW.tipo IS NOT OLD.tipo OR NEW.persona_id IS NOT OLD.persona_id OR NEW.texto IS NOT OLD.texto
    OR NEW.quien IS NOT OLD.quien OR NEW.creada IS NOT OLD.creada OR OLD.estado = 'hecha'
  BEGIN SELECT RAISE(ABORT, 'De una tarea solo se marca «hecha», una vez'); END;
"""


# ---------------------------------------------------------------- utilidades puras (sin servidor)
def hoy():
    """R16 (N6): fecha de negocio en hora de Madrid (la misma que servir.hoy y permisos.hoy_iso)."""
    return P.hoy_iso()


def slug(t):
    t = unicodedata.normalize("NFKD", str(t or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "_", t).strip("_")


def leer_correos():
    try:
        return json.loads(ruta_correos().read_text())
    except (OSError, ValueError):
        return {"correos": {}}


def escribir_correos(doc):
    f = ruta_correos()
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=1))
    tmp.replace(f)


_ZH = None


def zonas_del_historial():
    """{persona_id: {zona, pais?, zona_fuente, zona_a_confirmar}} con el último cambio de zona del historial de local.db
    (o RO_DB). Sin servidor (lo llama build_data.py). Si la base no se abre, {}."""
    global _ZH
    if _ZH is None:
        _ZH = {}
        try:
            import sqlite3
            con = sqlite3.connect(f"file:{os.environ.get('RO_DB') or AQUI / 'local.db'}?mode=ro", uri=True)
            for pid, datos in con.execute("SELECT id, datos FROM historial WHERE coleccion='personas' AND operacion='cambiar' "
                                          "AND datos LIKE '%\"zona\"%' ORDER BY n"):
                d = json.loads(datos or "{}")
                if d.get("zona"):
                    _ZH[pid] = {k: d[k] for k in ("zona", "pais", "zona_fuente", "zona_a_confirmar") if k in d}
            con.close()
        except Exception:
            _ZH = {}
    return _ZH


def fusionar_altas_app(personas, correos_entrada, previo):
    """La usa build_data.py al regenerar correos_entrada.json y lista_access.txt: conserva lo hecho en la app.
    personas: las de build_data · correos_entrada: {id: correo} (se amplía aquí) · previo: el correos_entrada.json anterior.
    Devuelve (desde_la_app, ids_activos_para_access)."""
    app = dict((previo or {}).get("desde_la_app") or {})
    ids = {p["id"] for p in personas}
    # Mi perfil (3-oct): la última zona guardada en la app (Mi perfil o Ajustes, en el historial) pasa también a
    # data/personas.json, para que los generadores (Horas: día de cada registro) usen la zona nueva al regenerar.
    for p in personas:
        z = zonas_del_historial().get(p["id"])
        if z:
            p.update(z)
    for pid, x in app.items():
        if x.get("correo") and x.get("activo"):      # el de la app manda (alta nueva o correo cambiado en Ajustes)
            correos_entrada[pid] = x["correo"]
        elif not x.get("activo"):
            correos_entrada.pop(pid, None)            # baja hecha en la app
    activos = {p["id"] for p in personas if p.get("activo") and p["id"] in correos_entrada}
    activos -= {pid for pid, x in app.items() if not x.get("activo")}                # bajas hechas en la app
    activos |= {pid for pid, x in app.items() if x.get("activo") and pid not in ids and pid in correos_entrada}   # altas de la app
    return app, activos


def actualizar_lista_access(quien, cambio):
    """Reescribe lista_access.txt con los correos de entrada activos (los de build_data ± lo hecho en la app) y deja al
    pie, comentado, lo que Tomás tiene que pasar a Cloudflare Access. NO toca Cloudflare."""
    f = ruta_lista()
    try:
        lineas = f.read_text().splitlines()
    except OSError:
        lineas = []
    cab = [l for l in lineas if l.startswith("#") and not l.startswith("# [app]")]
    actuales = {l.strip().lower() for l in lineas if l.strip() and not l.startswith("#")}
    pendientes = [l for l in lineas if l.startswith("# [app]")]
    doc = leer_correos()
    for pid, x in (doc.get("desde_la_app") or {}).items():
        c = (x.get("correo") or (doc.get("correos") or {}).get(pid) or "").strip().lower()
        if not c:
            continue
        for viejo in x.get("anteriores") or []:
            actuales.discard(viejo)
        if x.get("activo"):
            actuales.add(c)
        else:
            actuales.discard(c)
    pendientes.append(f"# [app] {hoy()} · {cambio} · lo hizo {quien} · pendiente de pasar a Cloudflare Access (tarea para Tomás)")
    if not cab:
        cab = ["# Correos de entrada de las personas activas (lista para Cloudflare Access)"]
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text("\n".join(cab) + "\n" + "\n".join(sorted(actuales)) + "\n" + "\n".join(pendientes[-40:]) + "\n")


def pl(n, sing, plur=None):
    return f"{n} {sing if n == 1 else (plur or sing + 's')}"


def correo_valido(c):
    return bool(re.fullmatch(r"[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,}", c or ""))


def cumple_valido(c):
    m = re.fullmatch(r"(\d\d)-(\d\d)", c or "")
    if not m:
        return False
    mes, dia = int(m.group(1)), int(m.group(2))
    return 1 <= mes <= 12 and 1 <= dia <= [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][mes - 1]


def fecha_valida(f):
    try:
        date.fromisoformat(f)
        return True
    except (TypeError, ValueError):
        return False


# ---------------------------------------------------------------- módulos (títulos para decir «qué pantallas ve»)
def titulos_modulos():
    t = (AQUI / "modulos" / "indice.js").read_text()
    out = {}
    for m in re.finditer(r"\{\s*id:\s*'([\w\-]+)',\s*num:\s*'[^']*',\s*titulo:\s*'([^']*)',\s*grupo:\s*'([^']*)'.*?estado:\s*'(\w+)'", t, re.S):
        out[m.group(1)] = {"titulo": m.group(2), "grupo": m.group(3), "hecho": m.group(4) == "hecho"}
    return out


def pantallas_de(persona):
    """[(id, título, nivel)] de las pantallas hechas que ve, con el mismo criterio que app.js."""
    tit = titulos_modulos()
    out = []
    for mid, mapa in S.E.modulos.items():
        n = P.nivel_modulo(persona, mapa)
        info = tit.get(mid)
        if n and info and info["hecho"] and mid != "catalogo":
            out.append((mid, info["titulo"], n))
    return out


def sillas_de_puestos(puestos):
    return [s for p in puestos for s in P.REGLAS["sillas_de_puesto"].get(p, [])]


def plantilla(puesto):
    """Qué ve y qué hace un puesto, calculado con las mismas reglas que el servidor (una persona de ensayo sin cartera)."""
    ensayo = {"id": "_plantilla", "puestos": [puesto], "estado": "activo"}
    pant = pantallas_de(ensayo)
    amb = P.PUESTO[puesto].get("ambito")
    clientes = {"todos": "todos los clientes", "disciplina": "todos los clientes de su disciplina",
                "cartera": "solo los clientes de su cartera", "tareas": "solo los clientes de sus tareas",
                "ninguno": "ningún detalle de cliente (solo la lista común)"}[amb]
    activos = [p for p in S.E.crudo["personas"] if p.get("estado") == "activo"]
    jefas = [p["id"] for p in activos if any(puesto in P.REGLAS["jefe_de_puesto"].get(x, []) for x in p.get("puestos", []))]
    if not jefas:
        from collections import Counter
        cuenta = Counter(p.get("jefe") for p in activos if puesto in p.get("puestos", []) and p.get("jefe"))
        jefas = [cuenta.most_common(1)[0][0]] if cuenta else []
    guia = GUIA_DE_PUESTO.get(puesto)
    return {"id": puesto, "nombre": P.PUESTO[puesto]["nombre"], "grupo": P.PUESTO[puesto]["grupo"],
            "que_hace": QUE_HACE.get(puesto, ""), "clientes": clientes, "ambito": amb,
            "pantallas": [t for _, t, _ in pant], "sillas": sorted(set(sillas_de_puestos([puesto]))),
            "jefe_sugerido": jefas[0] if jefas else None,
            "guia": guia if guia and (GUIAS / guia).exists() else None,
            "solo_tomas": puesto in set(P.REGLAS.get("puestos_solo_tomas") or []) or puesto == "direccion"}


# ---------------------------------------------------------------- comprobación de permisos (en llano)
SENSIBLES = [  # (tipo, texto en llano, ¿por cliente?)
    ("sueldos", "Sueldos", False), ("cobros", "Cobros e impagos", False), ("caja", "Caja de la empresa", False),
    ("dinero_empresa", "Dinero de la empresa (finanzas de dirección)", False),
    ("rentabilidad_cliente", "Rentabilidad por cliente", True), ("cuota", "Cuota de", True), ("inversion", "Inversión en publicidad de", True),
    ("lead", "Datos de leads de", True), ("ver_como", "«Ver como» a otra persona", False), ("ajustes_editar", "Cambiar personas y carteras (Ajustes)", False),
]


def comprobar(pid):
    E = S.E
    persona = E.persona(pid)
    if not persona:
        return None
    crudo = E.crudo
    cp = P.contexto(persona, crudo)
    nombre = {p["id"]: p.get("alias") or p["nombre"] for p in crudo["personas"]}
    nomcli = {c["id"]: c["nombre"] for c in crudo["clientes"]}
    rec = P.recortar(persona, crudo)
    detalle = [c["id"] for c in rec["clientes"] if c.get("detalle")]
    cartera = sorted(cp["cartera_ids"], key=lambda c: nomcli.get(c, c))
    amb = P.ambito(persona)
    pant = pantallas_de(persona)
    ajeno = next((c["id"] for c in crudo["clientes"] if c["id"] not in cp["cartera_ids"] and c["id"] not in detalle), None)
    propio = cartera[0] if cartera else (detalle[0] if detalle else None)
    otra = next((p for p in crudo["personas"] if p["id"] not in (pid, persona.get("jefe")) and p.get("jefe") != pid and p.get("estado") == "activo"), None)

    ve, no_ve, pruebas = [], [], []
    ve.append(f"{len(pant)} pantallas: " + ", ".join(t for _, t, _ in pant) + "." if pant else "Ninguna pantalla (revisa el puesto).")
    if amb in ("todos", "disciplina"):
        ve.append(f"El detalle de {len(detalle)} clientes ({'todos' if amb == 'todos' else 'los de su disciplina'}).")
    elif cartera:
        ve.append(f"El detalle de {pl(len(detalle), 'cliente')}, los de su cartera: " + ", ".join(nomcli.get(c, c) for c in cartera) + ".")
    else:
        ve.append("Ningún detalle de cliente: solo la lista común (nombre, logo, responsable y salud).")
    resto = len(crudo["clientes"]) - len(detalle)
    if resto:
        no_ve.append(f"El detalle de {'el otro cliente' if resto == 1 else f'los otros {resto} clientes'}: de ellos solo ve nombre, logo, responsable y salud.")
    for tipo, texto, por_cliente in SENSIBLES:
        if tipo not in P.REGLAS["tipos"]:
            continue
        if por_cliente:
            if propio:
                r = P.ver(persona, {"tipo": tipo, "cliente_id": propio}, cp)
                (ve if r["ok"] else no_ve).append(f"{texto} sus clientes" + (" (enmascarados: se desenmascaran con un clic que queda en el rastro)" if r["ok"] and r["nivel"] == "enmascarado" else "") + "."
                                                   if texto.endswith("de") else f"{texto}.")
            r2 = P.ver(persona, {"tipo": tipo, "cliente_id": ajeno}, cp) if ajeno else {"ok": False}
            # Un lead ajeno llega siempre enmascarado (regla general): solo es fallo si lo vería entero o lo podría abrir.
            if r2["ok"] and amb not in ("todos", "disciplina") and (r2.get("nivel") not in ("enmascarado", "resumen") or r2.get("desenmascarable")):
                pruebas.append({"ok": False, "texto": f"{texto} un cliente que no lleva ({nomcli.get(ajeno)}): lo vería y no debería."})
        else:
            r = P.ver(persona, {"tipo": tipo, "persona_id": otra["id"] if otra else None}, cp)
            (ve if r["ok"] else no_ve).append(texto + ".")
    if otra:
        r = P.ver(persona, {"tipo": "horas_persona", "persona_id": otra["id"]}, cp)
        (ve if r["ok"] else no_ve).append("Horas y notas de otras personas del equipo." if r["ok"] else "Horas y notas de otras personas (solo las suyas y las de quien dependa de él o ella).")

    # Pruebas automáticas (lo que tiene que cumplirse siempre)
    pu = set(persona.get("puestos", []))
    sueldos_ok = P.ver(persona, {"tipo": "sueldos", "persona_id": otra["id"] if otra else None}, cp)["ok"] if "sueldos" in P.REGLAS["tipos"] else False
    pruebas.append({"ok": (not sueldos_ok) or bool(pu & {"direccion", "rrhh"}),
                    "texto": "No ve sueldos." if not sueldos_ok else "Ve sueldos: solo dirección y RRHH."})
    if amb not in ("todos", "disciplina"):
        sobra = sorted(set(detalle) - set(cp["cartera_ids"]))
        pruebas.append({"ok": not sobra, "texto": f"Solo abre los clientes de su cartera ({pl(len(detalle), 'cliente')})." if not sobra
                        else f"Abre {len(sobra)} clientes que no son suyos: " + ", ".join(nomcli.get(c, c) for c in sobra) + "."})
        if ajeno:
            pruebas.append({"ok": not P.ver(persona, {"tipo": "cliente_detalle", "cliente_id": ajeno}, cp)["ok"],
                            "texto": f"Un cliente ajeno ({nomcli.get(ajeno)}) le da «no es tuyo» (403, sin ningún dato)."})
    sillas = set(sillas_de_puestos(persona.get("puestos", [])))
    if sillas and amb == "cartera" and not cartera:
        pruebas.append({"ok": False, "aviso": True, "texto": "Su puesto trabaja por cartera y no tiene clientes: no verá ninguno hasta que le asignéis alguno."})
    fuera = [a for a in crudo["asignaciones"] if a["persona_id"] == pid and P._vigente(a, hoy()) and a.get("silla") not in sillas and not a.get("suplencia")]
    if fuera:
        pruebas.append({"ok": False, "aviso": True, "texto": f"Tiene {pl(len(fuera), 'asignación', 'asignaciones')} en sillas que ya no son de su puesto (no las ve): ciérralas o repártelas."})
    jefe = E.persona(persona.get("jefe")) if persona.get("jefe") else None
    pruebas.append({"ok": bool(jefe and jefe.get("estado") == "activo") or "direccion" in pu,
                    "aviso": True, "texto": f"Jefe: {nombre.get(persona.get('jefe'))}." if jefe else "Sin jefe: nadie verá sus horas como jefe."})
    correo = (leer_correos().get("correos") or {}).get(pid)
    pend = tareas_de(pid, "access_anadir", "pendiente")
    entra = persona.get("estado") == "activo"
    pruebas.append({"ok": bool(correo) and entra, "aviso": True,
                    "texto": ("Puede entrar con su correo de entrada" + (" en cuanto Tomás lo añada a Cloudflare Access (tarea pendiente)." if pend else ".")) if correo and entra
                    else ("Sin correo de entrada: no podrá entrar." if not correo else f"Estado «{persona.get('estado')}»: no entra hasta su fecha de entrada o hasta que la activéis.")})

    inicio = "setters" if pu == {"setters"} else "mi-dia"
    muestras = [{"titulo": "Su inicio", "ruta": f"#/{inicio}", "espera": "Lo primero de su puesto."}]
    if propio:
        muestras.append({"titulo": f"Un cliente suyo: {nomcli.get(propio)}", "ruta": f"#/ficha/{propio}", "espera": "La ficha completa."})
    else:
        muestras.append({"titulo": "En rojo", "ruta": "#/en-rojo", "espera": "La lista común, sin detalle."})
    if ajeno:
        muestras.append({"titulo": f"Un cliente ajeno: {nomcli.get(ajeno)}", "ruta": f"#/ficha/{ajeno}", "espera": "«Este cliente no es tuyo», sin datos."})
    else:
        muestras.append({"titulo": "Ajustes", "ruta": "#/ajustes", "espera": "Solo si su puesto lo ve."})
    malas = [x for x in pruebas if not x["ok"] and not x.get("aviso")]
    return {"persona": {"id": pid, "alias": persona.get("alias"), "nombre": persona.get("nombre"), "estado": persona.get("estado"),
                        "puestos": persona.get("puestos", []), "jefe": nombre.get(persona.get("jefe")), "zona": persona.get("zona")},
            "resumen": f"{persona.get('alias')} verá {pl(len(pant), 'pantalla')} y el detalle de {len(detalle)} de {len(crudo['clientes'])} clientes.",
            "ve": ve, "no_ve": no_ve, "pruebas": pruebas, "todo_bien": not malas,
            "pantallas": [mid for mid, _, _ in pant], "detalle": detalle, "cartera": cartera, "muestras": muestras,
            "guias": sorted({GUIA_DE_PUESTO[x] for x in persona.get("puestos", []) if x in GUIA_DE_PUESTO})}


def diferencia(antes, despues):
    if not antes:
        return None
    gana = sorted(set(despues["pantallas"]) - set(antes["pantallas"]))
    pierde = sorted(set(antes["pantallas"]) - set(despues["pantallas"]))
    tit = titulos_modulos()
    nomcli = {c["id"]: c["nombre"] for c in S.E.crudo["clientes"]}
    cg = sorted(set(despues["detalle"]) - set(antes["detalle"]))
    cpi = sorted(set(antes["detalle"]) - set(despues["detalle"]))
    out = []
    if gana:
        out.append("Gana: " + ", ".join(tit.get(m, {}).get("titulo", m) for m in gana) + ".")
    if pierde:
        out.append("Pierde: " + ", ".join(tit.get(m, {}).get("titulo", m) for m in pierde) + ".")
    if cg:
        out.append(f"Clientes nuevos que abre ({len(cg)}): " + ", ".join(nomcli.get(c, c) for c in cg[:12]) + ("…" if len(cg) > 12 else "") + ".")
    if cpi:
        out.append(f"Clientes que deja de abrir ({len(cpi)}): " + ", ".join(nomcli.get(c, c) for c in cpi[:12]) + ("…" if len(cpi) > 12 else "") + ".")
    return out or ["Ve exactamente lo mismo que antes."]


# ---------------------------------------------------------------- base
def tareas_de(pid=None, tipo=None, estado=None):
    q, a = "SELECT * FROM altas_tareas WHERE 1=1", []
    for col, v in (("persona_id", pid), ("tipo", tipo), ("estado", estado)):
        if v:
            q += f" AND {col}=?"
            a.append(v)
    with S.conectar() as con:
        return [dict(r) for r in con.execute(q + " ORDER BY id DESC LIMIT 200", a)]


def nueva_tarea(quien, para, tipo, pid, texto):
    with S.conectar() as con:
        cur = con.execute("INSERT INTO altas_tareas (para, tipo, persona_id, texto, quien) VALUES (?,?,?,?,?)", (para, tipo, pid, texto, quien))
        return cur.lastrowid


def hist(con, quien, coleccion, cid, op, datos, antes=None):
    con.execute("INSERT INTO historial (quien, coleccion, id, operacion, antes, datos) VALUES (?,?,?,?,?,?)",
                (quien, coleccion, cid, op, json.dumps(antes, ensure_ascii=False) if antes is not None else None, json.dumps(datos, ensure_ascii=False)))


def asig_crear(con, quien, alias, cid, silla, pid, principal=True, desde=None):
    d = {"cliente_id": cid, "persona_id": pid, "silla": silla, "desde": desde or hoy(), "hasta": None, "principal": bool(principal),
         "suplencia": False, "titular_id": None, "fuente": f"Ajustes · altas y bajas · {alias} · {S.ahora()}", "confianza": "confirmada"}
    hist(con, quien, "asignaciones", f"{cid}·{silla}·{pid}", "crear", d)
    return d


def asig_cerrar(con, quien, a, hasta):
    d = {"cliente_id": a["cliente_id"], "persona_id": a["persona_id"], "silla": a["silla"], "hasta": hasta}
    hist(con, quien, "asignaciones", f"{a['cliente_id']}·{a['silla']}·{a['persona_id']}", "cerrar", d)
    return d


def vigentes_de(pid):
    # Vigentes y aún abiertas (una ya cerrada con fecha no se vuelve a cerrar; las suplencias llevan siempre fecha de fin).
    return [a for a in S.E.crudo["asignaciones"] if a["persona_id"] == pid and P._vigente(a, hoy()) and (not a.get("hasta") or a.get("suplencia"))]


def propuesta_reparto(pid, filas):
    """Para cada (cliente, silla) que se queda sin esta persona, propone quién: misma silla, mismo jefe primero y,
    entre ellos, quien menos clientes lleva hoy en esa silla. Lo decide Mili o Tomás."""
    E = S.E
    persona = E.persona(pid) or {}
    activos = [p for p in E.crudo["personas"] if p.get("estado") == "activo" and p["id"] != pid]
    carga = {}
    for a in E.crudo["asignaciones"]:
        if P._vigente(a, hoy()) and not a.get("suplencia"):
            carga[(a["persona_id"], a["silla"])] = carga.get((a["persona_id"], a["silla"]), 0) + 1
    nomcli = {c["id"]: c["nombre"] for c in E.crudo["clientes"]}
    out = []
    for a in filas:
        cand = [p for p in activos if a["silla"] in sillas_de_puestos(p.get("puestos", []))]
        cand.sort(key=lambda p: (p.get("jefe") != persona.get("jefe"), carga.get((p["id"], a["silla"]), 0), p.get("alias") or ""))
        ya = [x["persona_id"] for x in E.crudo["asignaciones"] if x["cliente_id"] == a["cliente_id"] and x["silla"] == a["silla"]
              and x["persona_id"] != pid and P._vigente(x, hoy())]
        out.append({"cliente_id": a["cliente_id"], "cliente": nomcli.get(a["cliente_id"], a["cliente_id"]), "silla": a["silla"],
                    "silla_txt": SILLA_NOMBRE.get(a["silla"], a["silla"]), "ya_tiene": [E.persona(x)["alias"] for x in ya if E.persona(x)],
                    "propuesta": cand[0]["id"] if cand and not ya else None,
                    "candidatos": [{"id": p["id"], "alias": p.get("alias") or p["nombre"], "lleva": carga.get((p["id"], a["silla"]), 0)} for p in cand[:12]]})
    return out


# ---------------------------------------------------------------- reglas de quién puede
def mando():
    return set(P.REGLAS.get("puestos_solo_tomas") or ["direccion", "finanzas_direccion", "rrhh", "operaciones", "ventas_ro", "administracion"]) | {"direccion"}


def es_tomas(real):
    return "direccion" in real.get("puestos", [])


def puede_tocar(real, p, cambia_puestos=None):
    """None si puede; si no, el motivo (las mismas reglas que /api/ajustes/persona, ronda 11)."""
    if p["id"] == real["id"]:
        return "Nadie se cambia ni se da de baja a sí mismo: pídeselo a Tomás."
    if es_tomas(real):
        return None
    if set(p.get("puestos", [])) & mando():
        return "A una persona con un puesto de mando (dirección, operaciones, RRHH, administración, ventas de RO…) solo la cambia Tomás."
    if cambia_puestos is not None and set(cambia_puestos) & mando():
        return "Dirección, finanzas de dirección, RRHH, operaciones, ventas de RO y administración solo los da Tomás."
    return None


# ---------------------------------------------------------------- Mi perfil · zona horaria (3-oct)
# Encargo de Tomás: «que el equipo pueda actualizar su timezone». Cada persona cambia la suya; la de otra, su jefe
# directo, Mili y Tomás (a quien tiene puesto de mando, solo Tomás). Regla en reglas_permisos.json → zona_horaria.
# La zona solo cambia lo que se ENSEÑA en la hora de la persona (su reloj, su resumen diario, el día de sus horas);
# las fechas de negocio siguen en Madrid (V2-E). Rutas mínimas en servir.py: GET /api/perfil, POST /api/perfil/zona.
PAIS_DE_ZONA.update({"America/Asuncion": "Paraguay", "America/Santo_Domingo": "República Dominicana"})


def regla_zona():
    r = P.REGLAS.get("zona_horaria") or {}
    return {"propia": r.get("propia", True), "jefe_directo": r.get("jefe_directo", True),
            "puestos": set(r.get("puestos") or ["direccion", "operaciones"]), "mando_solo": set(r.get("mando_solo") or ["direccion"]),
            "zonas_equipo": [tuple(x) for x in (r.get("zonas_equipo") or ZONAS)]}


_TODAS = None


def todas_las_zonas():
    """Las zonas IANA de verdad (Europe/Madrid, America/Caracas…), sin alias técnicos (Etc/, posix/, «UTC» suelto)."""
    global _TODAS
    if _TODAS is None:
        try:
            from zoneinfo import available_timezones
            _TODAS = sorted(z for z in available_timezones() if "/" in z and not z.startswith(("Etc/", "posix", "right", "SystemV/", "US/", "Canada/", "Brazil/", "Mexico/", "Chile/")))
        except Exception:
            _TODAS = sorted(z for z, _ in ZONAS)
    return _TODAS


def zona_valida(z):
    return isinstance(z, str) and len(z) <= 64 and (z in todas_las_zonas() or z in dict(ZONAS))


def puede_cambiar_zona(actor, p):
    """(None, por) si «actor» puede cambiar la zona de «p»; (motivo, None) si no. por = propia | direccion | operaciones | jefe."""
    R = regla_zona()
    pu = set(actor.get("puestos", []))
    if p["id"] == actor["id"]:
        return (None, "propia") if R["propia"] else ("Tu zona la cambia tu jefe.", None)
    if pu & R["mando_solo"]:
        return None, "direccion"
    if set(p.get("puestos", [])) & mando():
        return "A una persona con puesto de mando solo le cambia la zona Tomás (o ella misma).", None
    if pu & R["puestos"]:
        return None, "operaciones"
    if R["jefe_directo"] and p.get("jefe") == actor["id"]:
        return None, "jefe"
    return "La zona de otra persona solo la cambian ella, su jefe, Mili y Tomás.", None


def _madrid(ts):
    """«2026-10-03 01:14:00» (UTC de la base) → «2026-10-03 03:14» en Madrid."""
    try:
        from datetime import datetime, timezone
        from zoneinfo import ZoneInfo
        return datetime.fromisoformat(str(ts)[:19]).replace(tzinfo=timezone.utc).astimezone(ZoneInfo("Europe/Madrid")).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return str(ts or "")[:16]


def cambios_de_zona(ids, tope=20):
    """Los cambios de zona del historial (imborrable) de esas personas, lo más nuevo arriba."""
    if not ids:
        return []
    marcas = ",".join("?" * len(ids))
    with S.conectar() as con:
        filas = con.execute(f"SELECT ts, quien, id, antes, datos FROM historial WHERE coleccion='personas' AND operacion='cambiar' "
                            f"AND id IN ({marcas}) AND datos LIKE '%\"zona\"%' ORDER BY n DESC LIMIT ?", (*ids, tope)).fetchall()
    out = []
    for f in filas:
        d, a = json.loads(f["datos"] or "{}"), json.loads(f["antes"] or "{}")
        if "zona" not in d:
            continue
        out.append({"cuando": _madrid(f["ts"]), "quien": f["quien"], "persona_id": f["id"], "antes": a.get("zona"), "despues": d["zona"],
                    "desde": d.get("zona_fuente")})
    return out


def _resumen_de(pid):
    """Hora del resumen diario y canales silenciados (N15, avisos.py), si está cargado."""
    import sys
    av = sys.modules.get("avisos")
    if not av or not hasattr(av, "preferencias"):
        return None
    try:
        with S.conectar() as con:
            pr = av.preferencias(pid, con)
        return {"hora_resumen": pr.get("hora_resumen"), "silenciados": len(pr.get("silenciados") or [])}
    except Exception:
        return None


def ficha_zona(p):
    jefe = S.E.persona(p.get("jefe")) if p.get("jefe") else None
    return {"id": p["id"], "nombre": p.get("nombre"), "alias": p.get("alias") or p.get("nombre"),
            "puestos": [P.PUESTO[x]["nombre"] for x in p.get("puestos", []) if x in P.PUESTO], "rol": p.get("rol"),
            "jefe": {"id": jefe["id"], "alias": jefe.get("alias") or jefe.get("nombre")} if jefe else None,
            "zona": p.get("zona") or "Europe/Madrid", "pais": p.get("pais"), "zona_fuente": p.get("zona_fuente"),
            "zona_a_confirmar": bool(p.get("zona_a_confirmar")), "estado": p.get("estado")}


def perfil(real, persona, pid):
    """GET /api/perfil?id= · su ficha corta (nombre, puesto, jefe, zona), si puede cambiarla y, a quien manda, su gente.
    En «ver como» se calcula con la persona vista y sale en solo lectura."""
    E = S.E
    p = E.persona(pid or persona["id"])
    if not p:
        return 404, {"error": "No existe esa persona."}
    propia = p["id"] == persona["id"]
    motivo, por = puede_cambiar_zona(persona, p)
    ve_todos = bool(set(persona.get("puestos", [])) & {"direccion", "operaciones", "rrhh"})
    if not propia and motivo and not ve_todos:
        S.registrar_agrupado(real["id"], "mi-perfil", "denegado", p["id"], {"motivo": "perfil de otra persona"})
        return 403, {"error": "El perfil de otra persona solo lo ven ella, su jefe, Mili, Cecilia y Tomás."}
    R = regla_zona()
    gente = []
    for x in E.crudo["personas"]:
        if x["id"] == persona["id"] or x.get("estado") != "activo":
            continue
        m, _ = puede_cambiar_zona(persona, x)
        if not m or (ve_todos and x.get("jefe") == persona["id"]):
            gente.append({**ficha_zona(x), "puede": not m})
    gente.sort(key=lambda x: (x["jefe"] or {}).get("id") != persona["id"], )
    return 200, {
        "persona": ficha_zona(p), "propia": propia, "solo_lectura": persona["id"] != real["id"],
        "puede": not motivo, "motivo": motivo, "por": por,
        "zonas_equipo": [{"id": z, "texto": t} for z, t in R["zonas_equipo"]],
        "todas": todas_las_zonas(),
        "resumen": _resumen_de(p["id"]) if propia or not motivo else None,
        "equipo": gente[:80],
        "cambios": cambios_de_zona([p["id"]] + [g["id"] for g in gente], 20),
    }


def cambiar_zona(real, persona, b):
    """POST /api/perfil/zona { id, zona } · guarda en el historial de personas y en el rastro; se aplica al momento."""
    if persona["id"] != real["id"]:
        return 403, {"error": "Estás en «ver como»: es solo lectura. No se escribe nada."}
    E = S.E
    p = E.persona(b.get("id") or real["id"])
    if not p:
        return 404, {"error": "No existe esa persona."}
    if p.get("estado") == "baja":
        return 400, {"error": "Esa persona está de baja."}
    motivo, por = puede_cambiar_zona(real, p)
    if motivo:
        S.registrar_agrupado(real["id"], "mi-perfil", "denegado", p["id"], {"motivo": "cambiar la zona de otra persona"})
        return 403, {"error": motivo}
    zona = str(b.get("zona") or "").strip()
    if not zona_valida(zona):
        return 400, {"error": "Esa zona horaria no existe. Elige una de la lista o búscala (p. ej. America/Caracas)."}
    antes = p.get("zona") or "Europe/Madrid"
    if zona == antes:
        return 400, {"error": "Ya tiene esa zona."}
    quien_txt = {"propia": "ella misma", "jefe": "su jefe", "operaciones": "operaciones", "direccion": "dirección"}[por]
    cambios = {"zona": zona, "zona_fuente": f"Mi perfil ({quien_txt})", "zona_a_confirmar": False}
    if PAIS_DE_ZONA.get(zona):
        cambios["pais"] = PAIS_DE_ZONA[zona]
    with S.conectar() as con:
        hist(con, real["id"], "personas", p["id"], "cambiar", cambios, {k: p.get(k) for k in cambios})
    S.registrar(real["id"], "mi-perfil", "zona_cambiada", p["id"], {"antes": antes, "despues": zona, "por": por})
    E.recargar_personas("mi perfil · zona")   # V3a: recarga parcial (< 1 s), no la entera
    import sys
    av = sys.modules.get("avisos")
    if av and isinstance(getattr(av, "_RES", None), dict):
        av._RES["t"] = 0.0          # el resumen diario de la campana pasa ya a su hora nueva
    return 200, {"ok": True, "persona": ficha_zona(E.persona(p["id"])), "antes": antes, "por": por}


def validar_cartera(cartera, puestos):
    sillas = set(sillas_de_puestos(puestos))
    ids = {c["id"] for c in S.E.crudo["clientes"]}
    limpia = []
    for x in cartera or []:
        if not isinstance(x, dict) or x.get("cliente_id") not in ids:
            return None, "Hay un cliente que no existe en la cartera."
        if x.get("silla") not in sillas:
            return None, f"La silla «{x.get('silla')}» no es de su puesto (puede: {', '.join(sorted(sillas)) or 'ninguna'})."
        limpia.append({"cliente_id": x["cliente_id"], "silla": x["silla"], "papel": "apoyo" if x.get("papel") == "apoyo" else "responsable"})
    return limpia, None


def correo_libre(correo, salvo=None):
    doc = leer_correos()
    for pid, c in (doc.get("correos") or {}).items():
        if pid != salvo and (c or "").strip().lower() == correo:
            return False
    for p in S.E.crudo["personas"]:
        if p["id"] != salvo and (correo == (p.get("correo") or "").lower() or correo in [x.lower() for x in p.get("otros_correos") or []]):
            return False
    return True


def guardar_correo(pid, correo, activo, quien):
    doc = leer_correos()
    doc.setdefault("correos", {})
    app = doc.setdefault("desde_la_app", {})
    x = app.setdefault(pid, {})
    previo = (doc["correos"].get(pid) or x.get("correo") or "").strip().lower()
    x.update({"activo": bool(activo), "cambiado": S.ahora(), "por": quien})
    if correo:
        if previo and previo != correo:          # correo cambiado: el anterior sale de la lista de Access
            x["anteriores"] = sorted(set(x.get("anteriores") or []) | {previo})
        x["correo"] = correo
        doc["correos"][pid] = correo
    elif previo:
        x["correo"] = previo
    if not activo:
        x["baja"] = hoy()
        doc["correos"].pop(pid, None)           # de baja: ya no casa la identidad
    escribir_correos(doc)


def aplicar_cartera(con, real, pid, cartera, desde=None):
    """Crea las asignaciones; «responsable» en una silla que ya tiene responsable lo sustituye (el anterior se cierra ayer)."""
    ayer = (date.fromisoformat(hoy()) - timedelta(days=1)).isoformat()
    hechas, cerradas = [], []
    for x in cartera:
        if x["papel"] == "responsable":
            for a in S.E.crudo["asignaciones"]:
                if a["cliente_id"] == x["cliente_id"] and a["silla"] == x["silla"] and a["persona_id"] != pid and a.get("principal", True) \
                        and not a.get("suplencia") and P._vigente(a, hoy()) and not a.get("hasta"):
                    cerradas.append(asig_cerrar(con, real["id"], a, ayer))
        hechas.append(asig_crear(con, real["id"], real.get("alias"), x["cliente_id"], x["silla"], pid, x["papel"] == "responsable", desde))
    return hechas, cerradas


# ---------------------------------------------------------------- departamentos y dudas de Tomás
def leer_departamentos():
    try:
        return json.loads(ruta_departamentos().read_text()).get("departamentos") or {}
    except (OSError, ValueError):
        return {}


def dudas_roles():
    try:
        lista = json.loads(DUDAS.read_text()).get("dudas") or []
    except (OSError, ValueError):
        return []
    with S.conectar() as con:
        subidas = {r["clave"]: dict(r) for r in con.execute("SELECT id, clave, respondida FROM decisiones WHERE tipo='para_tomas' AND clave LIKE 'n9-%'")}
    return [{**d, "subida": f"db-{subidas[d['clave']]['id']}" if d["clave"] in subidas else None,
             "contestada": bool(subidas.get(d["clave"], {}).get("respondida"))} for d in lista]


# ---------------------------------------------------------------- rutas
def get(h, ruta, q, real, persona):
    cp = P.contexto(persona, S.E.crudo)
    if not P.ver(persona, {"tipo": "ajustes_editar"}, cp)["ok"]:
        return h.responder(403, {"error": "Las altas y bajas las hacen Mili y Tomás."})
    if ruta == "/api/altas":
        E = S.E
        puede_mando = es_tomas(real) and persona["id"] == real["id"]
        tareas = tareas_de()
        correos = leer_correos().get("correos") or {}
        for t in tareas:      # el correo solo se enseña a Tomás (lo necesita para Access); a Mili, enmascarado
            c = correos.get(t["persona_id"]) or ((leer_correos().get("desde_la_app") or {}).get(t["persona_id"]) or {}).get("correo")
            if t["tipo"].startswith("access") and c:
                t["correo"] = c if puede_mando else P.enmascarar(c)
            t["persona"] = (E.persona(t["persona_id"]) or {}).get("alias") or t["persona_id"]
        return h.responder(200, {
            "plantillas": {x["id"]: plantilla(x["id"]) for x in P.REGLAS["puestos"]},
            "puede_dar": [x["id"] for x in P.REGLAS["puestos"] if puede_mando or x["id"] not in mando()],
            "esTomas": puede_mando, "soloLectura": persona["id"] != real["id"],
            "personas": [{"id": p["id"], "alias": p.get("alias") or p["nombre"], "nombre": p["nombre"], "puestos": p.get("puestos", []),
                          "estado": p.get("estado"), "jefe": p.get("jefe"), "zona": p.get("zona"), "fecha_ingreso": p.get("fecha_ingreso"),
                          "cumple_dia_mes": p.get("cumple_dia_mes"), "tiene_correo_entrada": bool(correos.get(p["id"])) or bool(p.get("tiene_correo_entrada")),
                          "mando": bool(set(p.get("puestos", [])) & mando())} for p in E.crudo["personas"]],
            "clientes": [{"id": c["id"], "nombre": c["nombre"], "equipo": {s: [E.persona(a["persona_id"])["alias"] for a in E.crudo["asignaciones"]
                          if a["cliente_id"] == c["id"] and a["silla"] == s and P._vigente(a, hoy()) and E.persona(a["persona_id"])]
                          for s in P.REGLAS["sillas"]}} for c in E.crudo["clientes"]],
            "asignaciones": [a for a in E.crudo["asignaciones"] if P._vigente(a, hoy())],
            # Mi perfil (3-oct): la lista corta de la regla + las zonas que ya tiene alguien (si no, el desplegable de
            # «Cambiar» enseñaría otra zona y al guardar se la cambiaría sin querer).
            "zonas": [{"id": z, "texto": t} for z, t in regla_zona()["zonas_equipo"]]
                     + [{"id": z, "texto": z.split("/")[-1].replace("_", " ")} for z in sorted({p.get("zona") for p in E.crudo["personas"] if p.get("zona")} - {z for z, _ in regla_zona()["zonas_equipo"]})],
            "dominios": list(DOMINIOS_RO),
            "tareas": tareas, "hoy": hoy(),
            "departamentos": leer_departamentos(), "dudas": dudas_roles(),
        })
    if ruta == "/api/altas/comprobar":
        pid = (q.get("id") or [""])[0]
        r = comprobar(pid)
        return h.responder(200, r) if r else h.responder(404, {"error": "No existe esa persona."})
    if ruta == "/api/altas/guia":
        pu = (q.get("puesto") or [""])[0]
        f = GUIA_DE_PUESTO.get(pu)
        if not f:
            return h.responder(404, {"error": "Ese puesto no tiene guía."})
        try:
            texto = (GUIAS / f).read_text()
        except OSError:
            return h.responder(200, {"puesto": pu, "fichero": f, "texto": None, "motivo": "La guía no está en este servidor (40_GUIA_EQUIPO)."})
        return h.responder(200, {"puesto": pu, "fichero": f, "texto": texto})
    return h.responder(404, {"error": "No existe esa ruta de altas."})


def post(h, ruta, real, persona, b):
    if persona["id"] != real["id"]:
        return h.responder(403, {"error": "Estás en «ver como»: es solo lectura. No se escribe nada."})
    cp = P.contexto(real, S.E.crudo)
    if not P.ver(real, {"tipo": "ajustes_editar"}, cp)["ok"]:
        return h.responder(403, {"error": "Las altas y bajas las hacen Mili y Tomás."})
    if "sueldo" in json.dumps(b) or "salario" in json.dumps(b):
        return h.responder(400, {"error": "Los sueldos no entran por aquí."})
    E = S.E

    if ruta == "/api/altas/alta":
        extra = set(b) - CLAVES_ALTA
        if any(re.search(r"(?i)tel[eé]?f|^tel$|m[oó]vil|whatsapp|phone|extensi", k) for k in extra):
            # Regla de teléfonos (3-oct): el alta no guarda teléfonos de personas (ni con «+34» ni sin él).
            return h.responder(400, {"error": "Los teléfonos de las personas no se guardan en la app. Quita el teléfono y vuelve a guardar."})
        if extra:
            return h.responder(400, {"error": "Solo se guardan nombre, puesto, jefe, zona, fechas, cumpleaños, correo de entrada y cartera. Fuera: " + ", ".join(sorted(extra)) + "."})
        nombre = re.sub(r"\s+", " ", str(b.get("nombre") or "")).strip()
        if not (3 <= len(nombre) <= 80) or re.search(r"[\d@<>/\\]", nombre):
            return h.responder(400, {"error": "Escribe el nombre y apellido (sin números)."})
        puestos = [x for x in b.get("puestos") or [] if isinstance(x, str)]
        if not puestos or any(x not in P.PUESTO for x in puestos):
            return h.responder(400, {"error": "Elige al menos un puesto válido."})
        motivo = None if es_tomas(real) else ("Dirección, finanzas de dirección, RRHH, operaciones, ventas de RO y administración solo los da Tomás."
                                               if set(puestos) & mando() else None)
        if motivo:
            return h.responder(403, {"error": motivo})
        jefe = b.get("jefe") or None
        if jefe and not (E.persona(jefe) and E.persona(jefe).get("estado") == "activo"):
            return h.responder(400, {"error": "El jefe tiene que ser una persona activa."})
        if not jefe and "direccion" not in puestos:
            return h.responder(400, {"error": "Elige su jefe (quién ve sus horas y su día)."})
        zona = b.get("zona") or ""
        if not zona_valida(zona):
            return h.responder(400, {"error": "Elige su zona horaria de la lista."})
        entrada = b.get("fecha_entrada") or hoy()
        if not fecha_valida(entrada):
            return h.responder(400, {"error": "La fecha de entrada no es válida."})
        cumple = b.get("cumple") or None
        if cumple and not cumple_valido(cumple):
            return h.responder(400, {"error": "El cumpleaños va como día y mes (sin año)."})
        correo = (b.get("correo_entrada") or "").strip().lower() or None
        if correo:
            if not correo_valido(correo):
                return h.responder(400, {"error": "El correo de entrada no tiene forma de correo."})
            if not correo.endswith(DOMINIOS_RO) and not es_tomas(real):
                return h.responder(403, {"error": "El correo de entrada es el de la empresa (@rankingonline.com o @rankingonlinemarketing.com). Otro, solo si lo dice Tomás."})
            if not correo_libre(correo):
                return h.responder(409, {"error": "Ese correo ya es de otra persona: tiene que ser único."})
        cartera, err = validar_cartera(b.get("cartera"), puestos)
        if err:
            return h.responder(400, {"error": err})
        pid = base = slug(nombre.split()[0])
        if E.persona(pid):
            pid = base = slug(" ".join(nombre.split()[:2]))
        n = 2
        while E.persona(pid):
            pid, n = f"{base}_{n}", n + 1
        alias = nombre.split()[0]
        if any((p.get("alias") or "") == alias for p in E.crudo["personas"]) and len(nombre.split()) > 1:
            alias = f"{alias} {nombre.split()[1][0]}."
        activa = entrada <= hoy()
        persona_nueva = {
            "id": pid, "nombre": nombre, "alias": alias, "alias_todos": [alias], "puestos": puestos, "puesto_principal": puestos[0],
            "puestos_fase0": [], "puestos_sin_equivalencia": [], "jefe": jefe, "nivel": min(P.PUESTO[x].get("nivel", 7) for x in puestos),
            "horas_mes": int(b.get("horas_mes") or 128), "imputa_horas": "no" if set(puestos) <= {"setters"} else (b.get("imputa_horas") or "sí"),
            "correo": None, "otros_correos": [], "activo": activa, "estado": "activo" if activa else "por_incorporar",
            "activar_el": None if activa else entrada, "prueba": False, "fuente": f"Ajustes · alta de {real.get('alias')} · {S.ahora()}",
            "nota": None if activa else f"Entra el {entrada}: se activa sola ese día.", "rol": " · ".join(P.PUESTO[x]["nombre"] for x in puestos),
            "fecha_ingreso": entrada, "fecha_salida": None, "pais": PAIS_DE_ZONA.get(zona), "cumple_dia_mes": cumple, "zona": zona,
            "zona_fuente": "Ajustes (alta)", "zona_a_confirmar": False, "etiquetas": [], "tiene_correo_entrada": bool(correo),
            "aviso_correo": None if correo else "falta correo", "alta_desde_app": True,
        }
        with S.conectar() as con:
            hist(con, real["id"], "personas", pid, "crear", persona_nueva)
            hechas, cerradas = aplicar_cartera(con, real, pid, cartera, None)
        if correo:
            guardar_correo(pid, correo, True, real["id"])
        tarea = None
        if correo:
            tarea = nueva_tarea(real["id"], "tomas", "access_anadir", pid,
                                f"Añadir el correo de entrada de {alias} ({persona_nueva['rol']}) a la lista de Cloudflare Access. Entra el {entrada}.")
            actualizar_lista_access(real.get("alias"), f"alta de {alias}")
        S.registrar(real["id"], "ajustes", "alta_persona", pid, {"puestos": puestos, "jefe": jefe, "zona": zona, "entrada": entrada,
                                                              "cartera": len(hechas), "sustituye": len(cerradas), "correo_entrada": bool(correo)})
        E.recargar_personas("altas · alta")
        try:    # auditoría 36 §6.5: sus ficheros por persona (alertas, chat, agenda) llegan con la próxima recarga: se pide ya
            S.pedir_recarga(real["id"])
            recarga = True
        except Exception:
            recarga = False
        return h.responder(200, {"ok": True, "id": pid, "alias": alias, "tarea_access": tarea, "asignaciones": len(hechas), "recarga_pedida": recarga,
                                 "sustituidas": len(cerradas), "comprobacion": comprobar(pid)})

    if ruta == "/api/altas/cambio":
        p = E.persona(b.get("id"))
        if not p:
            return h.responder(404, {"error": "No existe esa persona."})
        if p.get("estado") == "baja":
            return h.responder(400, {"error": "Está de baja: dala de alta otra vez desde «Añadir persona»."})
        puestos = b.get("puestos")
        cambia_p = puestos is not None and set(puestos) != set(p.get("puestos", []))
        if puestos is not None and (not puestos or any(x not in P.PUESTO for x in puestos)):
            return h.responder(400, {"error": "Elige al menos un puesto válido."})
        motivo = puede_tocar(real, p, (set(puestos) ^ set(p.get("puestos", []))) if cambia_p else None)
        if motivo:
            return h.responder(403, {"error": motivo})
        antes = comprobar(p["id"])
        cambios = {}
        if cambia_p:
            cambios.update({"puestos": puestos, "puesto_principal": puestos[0], "rol": " · ".join(P.PUESTO[x]["nombre"] for x in puestos)})
        if "jefe" in b and (b.get("jefe") or None) != p.get("jefe"):
            j = b.get("jefe") or None
            if j and (j == p["id"] or not (E.persona(j) and E.persona(j).get("estado") == "activo")):
                return h.responder(400, {"error": "El jefe tiene que ser otra persona activa."})
            cambios["jefe"] = j
        if b.get("zona") and b["zona"] != p.get("zona"):
            if not zona_valida(b["zona"]):
                return h.responder(400, {"error": "Elige su zona horaria de la lista."})
            cambios.update({"zona": b["zona"], "pais": PAIS_DE_ZONA.get(b["zona"]), "zona_fuente": "Ajustes (cambio)", "zona_a_confirmar": False})
        # Auditoría 36 §6.3: rol, país, fecha de ingreso y cumpleaños de quien ya existe (los de mando, solo Tomás: puede_tocar).
        if b.get("rol") is not None and str(b["rol"]).strip() != (p.get("rol") or ""):
            rol = re.sub(r"\s+", " ", str(b["rol"])).strip()
            if len(rol) > 80 or re.search(r"[@<>\d]", rol):
                return h.responder(400, {"error": "El rol es un texto corto, sin números ni correos."})
            cambios["rol_texto"] = rol
        if b.get("pais") and b["pais"] != p.get("pais"):
            if b["pais"] not in set(PAIS_DE_ZONA.values()):
                return h.responder(400, {"error": "País no válido."})
            cambios["pais"] = b["pais"]
        if b.get("fecha_ingreso") and b["fecha_ingreso"] != p.get("fecha_ingreso"):
            if not fecha_valida(b["fecha_ingreso"]):
                return h.responder(400, {"error": "La fecha de ingreso no es válida."})
            cambios["fecha_ingreso"] = b["fecha_ingreso"]
        if b.get("cumple") and b["cumple"] != p.get("cumple_dia_mes"):
            if not cumple_valido(b["cumple"]):
                return h.responder(400, {"error": "El cumpleaños va como día y mes (sin año)."})
            cambios["cumple_dia_mes"] = b["cumple"]
        correo_nuevo = (b.get("correo_entrada") or "").strip().lower() or None
        if correo_nuevo and correo_nuevo == ((leer_correos().get("correos") or {}).get(p["id"]) or "").lower():
            correo_nuevo = None
        if correo_nuevo:
            if not correo_valido(correo_nuevo):
                return h.responder(400, {"error": "El correo de entrada no tiene forma de correo."})
            if not correo_nuevo.endswith(DOMINIOS_RO) and not es_tomas(real):
                return h.responder(403, {"error": "Un correo de entrada que no es de RO solo lo autoriza Tomás."})
            if not correo_libre(correo_nuevo, salvo=p["id"]):
                return h.responder(409, {"error": "Ese correo ya es de otra persona: tiene que ser único."})
        if "rol_texto" in cambios:
            cambios["rol"] = cambios.pop("rol_texto")
        nuevos_puestos = puestos if cambia_p else p.get("puestos", [])
        cartera, err = validar_cartera(b.get("cartera_anadir"), nuevos_puestos)
        if err:
            return h.responder(400, {"error": err})
        quitar = [x for x in b.get("cartera_quitar") or [] if isinstance(x, dict)]
        sillas = set(sillas_de_puestos(nuevos_puestos))
        vig = vigentes_de(p["id"])
        a_cerrar = [a for a in vig if (cambia_p and a["silla"] not in sillas and not a.get("suplencia"))
                    or any(a["cliente_id"] == x.get("cliente_id") and a["silla"] == x.get("silla") for x in quitar)]
        if not (cambios or cartera or a_cerrar or correo_nuevo):
            return h.responder(400, {"error": "No hay nada que cambiar."})
        if correo_nuevo:
            guardar_correo(p["id"], correo_nuevo, True, real["id"])
            nueva_tarea(real["id"], "tomas", "access_anadir", p["id"],
                        f"Cambiar el correo de entrada de {p.get('alias')} en la lista de Cloudflare Access (quitar el anterior, poner el nuevo).")
            actualizar_lista_access(real.get("alias"), f"correo de entrada nuevo de {p.get('alias')}")
        with S.conectar() as con:
            if cambios:
                hist(con, real["id"], "personas", p["id"], "cambiar", cambios, {k: p.get(k) for k in cambios})
            ayer = (date.fromisoformat(hoy()) - timedelta(days=1)).isoformat()
            for a in a_cerrar:      # al cambiar de puesto deja de verlas ya: se cierran con fecha de ayer (nada se borra)
                asig_cerrar(con, real["id"], a, ayer)
            hechas, sustituidas = aplicar_cartera(con, real, p["id"], cartera)
        S.registrar(real["id"], "ajustes", "cambio_persona", p["id"], {"cambios": {k: v for k, v in cambios.items() if k != "rol"}, "correo_entrada": bool(correo_nuevo),
                                                                    "cartera_nueva": len(hechas), "cerradas": len(a_cerrar)})
        E.recargar_personas("altas · cambio")
        despues = comprobar(p["id"])
        return h.responder(200, {"ok": True, "comprobacion": despues, "diferencia": diferencia(antes, despues),
                                 "cerradas": len(a_cerrar), "nuevas": len(hechas), "propuesta": propuesta_reparto(p["id"], a_cerrar)})

    if ruta == "/api/altas/baja":
        p = E.persona(b.get("id"))
        if not p:
            return h.responder(404, {"error": "No existe esa persona."})
        if p.get("estado") == "baja":
            return h.responder(409, {"error": "Ya está de baja."})
        motivo = puede_tocar(real, p)
        if motivo:
            return h.responder(403, {"error": motivo})
        fecha = b.get("fecha") or hoy()
        if not fecha_valida(fecha):
            return h.responder(400, {"error": "La fecha de baja no es válida."})
        vig = vigentes_de(p["id"])
        with S.conectar() as con:
            hist(con, real["id"], "personas", p["id"], "cambiar", {"estado": "baja", "activo": False, "fecha_salida": fecha},
                 {"estado": p.get("estado"), "activo": p.get("activo"), "fecha_salida": p.get("fecha_salida")})
            for a in vig:
                asig_cerrar(con, real["id"], a, fecha)
        doc = leer_correos()
        correo = (doc.get("correos") or {}).get(p["id"])
        guardar_correo(p["id"], None, False, real["id"])
        t_acc = nueva_tarea(real["id"], "tomas", "access_quitar", p["id"],
                            f"Quitar a {p.get('alias')} de la lista de Cloudflare Access (baja el {fecha}). Revisar también sus accesos a las herramientas.")
        actualizar_lista_access(real.get("alias"), f"baja de {p.get('alias')}")
        cartera = [a for a in vig if not a.get("suplencia")]
        propuesta = propuesta_reparto(p["id"], cartera)
        sin_nadie = [x for x in propuesta if not x["ya_tiene"]]
        t_rep = nueva_tarea(real["id"], "mili_o_tomas", "repartir_cartera", p["id"],
                            f"Repartir la cartera de {p.get('alias')}: {pl(len(sin_nadie), 'cliente se queda', 'clientes se quedan')} sin nadie en su silla (hay una propuesta en Ajustes › Altas y bajas).") if sin_nadie else None
        S.registrar(real["id"], "ajustes", "baja_persona", p["id"], {"fecha": fecha, "asignaciones_cerradas": len(vig), "tenia_correo": bool(correo)})
        E.recargar_personas("altas · baja")
        return h.responder(200, {"ok": True, "cerradas": len(vig), "tarea_access": t_acc, "tarea_reparto": t_rep,
                                 "propuesta": propuesta})

    if ruta == "/api/altas/repartir":
        filas = [x for x in b.get("filas") or [] if isinstance(x, dict) and x.get("persona_id")]
        if not filas:
            return h.responder(400, {"error": "Elige a quién pasa cada cliente."})
        ids = {c["id"] for c in E.crudo["clientes"]}
        for x in filas:
            q = E.persona(x["persona_id"])
            if x.get("cliente_id") not in ids or not q or q.get("estado") != "activo" or x.get("silla") not in sillas_de_puestos(q.get("puestos", [])):
                return h.responder(400, {"error": "Cliente, persona o silla no válidos (la persona tiene que estar activa y tener esa silla)."})
        with S.conectar() as con:
            for x in filas:
                asig_crear(con, real["id"], real.get("alias"), x["cliente_id"], x["silla"], x["persona_id"], True)
            if b.get("de"):
                con.execute("UPDATE altas_tareas SET estado='hecha', hecha=datetime('now'), hecha_por=? WHERE persona_id=? AND tipo='repartir_cartera' AND estado='pendiente'",
                            (real["id"], b["de"]))
        S.registrar(real["id"], "ajustes", "repartir_cartera", b.get("de") or "", {"filas": [{k: x.get(k) for k in ("cliente_id", "silla", "persona_id")} for x in filas]})
        E.recargar_personas("altas · reparto")
        return h.responder(200, {"ok": True, "repartidas": len(filas)})

    if ruta == "/api/altas/departamento":
        if not es_tomas(real):
            return h.responder(403, {"error": "El jefe de un departamento solo lo cambia Tomás."})
        f = ruta_departamentos()
        try:
            doc = json.loads(f.read_text())
        except (OSError, ValueError):
            return h.responder(503, {"error": "No se puede leer data/departamentos.json."})
        dep, jefe = b.get("departamento"), b.get("jefe")
        if dep not in (doc.get("departamentos") or {}):
            return h.responder(400, {"error": "Ese departamento no existe."})
        q = E.persona(jefe)
        if not q or q.get("estado") != "activo":
            return h.responder(400, {"error": "El jefe tiene que ser una persona activa."})
        d = doc["departamentos"][dep]
        antes = {"jefe": d.get("jefe"), "pendiente": d.get("pendiente")}
        d.update({"jefe": jefe, "jefe_origen": f"Tomás en Ajustes, {hoy()}"})
        d.pop("pendiente", None)
        doc["actualizado"] = hoy()
        tmp = f.with_suffix(".tmp")
        tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=1))
        tmp.replace(f)
        with S.conectar() as con:
            hist(con, real["id"], "departamentos", dep, "cambiar", {"jefe": jefe}, antes)
        S.registrar(real["id"], "ajustes", "jefe_departamento", dep, {"antes": antes["jefe"], "despues": jefe})
        return h.responder(200, {"ok": True})

    if ruta == "/api/altas/tarea_hecha":
        tid = int(b.get("id") or 0)
        with S.conectar() as con:
            t = con.execute("SELECT * FROM altas_tareas WHERE id=?", (tid,)).fetchone()
            if not t:
                return h.responder(404, {"error": "No existe esa tarea."})
            if t["tipo"].startswith("access") and not es_tomas(real):
                return h.responder(403, {"error": "Cloudflare Access lo toca solo Tomás: él marca la tarea."})
            if t["estado"] == "hecha":
                return h.responder(409, {"error": "Ya estaba hecha."})
            con.execute("UPDATE altas_tareas SET estado='hecha', hecha=datetime('now'), hecha_por=? WHERE id=?", (real["id"], tid))
        S.registrar(real["id"], "ajustes", "tarea_alta_hecha", str(tid), {"tipo": t["tipo"], "persona": t["persona_id"]})
        return h.responder(200, {"ok": True})

    return h.responder(404, {"error": "No existe esa ruta de altas."})


# ---------------------------------------------------------------- enganche con servir.py
def enganchar(Manejador, servir):
    """Envuelve _api_get y api_post (como ia.py) y Estado.aplicar_ajustes / por_correo. Sin este fichero, nada cambia."""
    global S, P
    S, P = servir, servir.P
    with S.conectar() as con:
        con.executescript(TABLA_SQL)
    get_orig, post_orig = Manejador._api_get, Manejador.api_post
    aplicar_orig, por_correo_orig = S.Estado.aplicar_ajustes, S.Estado.por_correo

    def _api_get(self, ruta, q, real, persona):
        if ruta == "/api/altas" or ruta.startswith("/api/altas/"):
            if S.E.nucleo_bloqueado:
                return self.responder(503, {"error": "La puerta de secretos ha encontrado algo en los datos."})
            return get(self, ruta, q, real, persona)
        return get_orig(self, ruta, q, real, persona)

    def api_post(self, ruta, real, persona, b):
        if ruta.startswith("/api/altas/"):
            return post(self, ruta, real, persona, b)
        return post_orig(self, ruta, real, persona, b)

    def aplicar_ajustes(self, crudo):
        # Las personas dadas de alta en la app viven en el historial (imborrable): se añaden antes de reaplicar los cambios.
        try:
            with S.conectar() as con:
                filas = con.execute("SELECT id, datos FROM historial WHERE coleccion='personas' AND operacion='crear' ORDER BY n").fetchall()
        except Exception:
            filas = []
        ya = {p["id"] for p in crudo["personas"]}
        for f in filas:
            if f["id"] not in ya:
                crudo["personas"].append(json.loads(f["datos"]))
                ya.add(f["id"])
        aplicar_orig(self, crudo)
        for p in crudo["personas"]:   # «por incorporar» de la app: se activa sola el día de entrada
            if p.get("alta_desde_app") and p.get("estado") == "por_incorporar" and p.get("activar_el") and p["activar_el"] <= hoy():
                p["estado"], p["activo"] = "activo", True

    def por_correo(self, correo):
        r = por_correo_orig(self, correo)
        if r or not os.environ.get("RO_CORREOS_ENTRADA"):
            return r
        c = (correo or "").strip().lower()   # en pruebas el fichero privado es una copia: se casa también con ella
        hits = [pid for pid, x in (leer_correos().get("correos") or {}).items() if (x or "").strip().lower() == c]
        return self.persona(hits[0]) if len(hits) == 1 else None

    Manejador._api_get = _api_get
    Manejador.api_post = api_post
    S.Estado.aplicar_ajustes = aplicar_ajustes
    S.Estado.por_correo = por_correo

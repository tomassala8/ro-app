"""GA4, Search Console, Metricool, GoHighLevel (resumen) y Snov por cliente.

Origen: ~/Downloads/HERRAMIENTA_RO_2026-10-02/externos.json (lo genera ~/RO_HERRAMIENTAS/externos.py,
30 días frente a los 30 anteriores) y emparejamientos.json (cliente ↔ propiedad, sitio, marca y subcuenta,
por identificador). Snov lo añade ~/RO_HERRAMIENTAS/snov/por_cliente.py.

Plan A (--en-vivo externos): lanzar externos.py (lee GA4, Search Console, Metricool y GHL, solo lectura).
Plan B (por defecto): leer el último externos.json.
"""
import subprocess
import sys

from comun import AQUI, HERR, HERRAMIENTA, bloque, edad_h, enlace, iso, leer, limpiar_consultas, mtime, todo_cero

FUENTES = {
    "ga4":       ("Google Analytics 4 (30 días)", 24, 30),
    "gsc":       ("Search Console (30 días)", 24, 30),
    "metricool": ("Redes en Metricool (seguidores)", 24, 30),
    "ghl":       ("GoHighLevel del cliente (contactos y oportunidades)", 1, 30),
    "snov":      ("Correo en frío en Snov (30 días)", 24, 30),
}


def plan_a():
    r = subprocess.run([sys.executable, str(HERR / "externos.py")], capture_output=True, text=True, timeout=1800)
    return r.returncode == 0, (r.stderr or r.stdout)[-300:]


def cargar(universo, en_vivo=False):
    plan, error = "B · último externos.json", None
    if en_vivo:
        ok, msg = plan_a()
        plan = "A · externos.py en vivo" if ok else "B · último externos.json (falló el plan A)"
        error = None if ok else msg
    ext = leer(HERRAMIENTA / "externos.json", {}) or {}
    emp = leer(HERRAMIENTA / "emparejamientos.json", {}) or {}
    hora = mtime(HERRAMIENTA / "externos.json")
    periodo = ext.get("periodo")
    datos_ext = ext.get("clientes", {})
    manual = leer(AQUI / "emparejamientos_manual.json", {}) or {}
    man = {h: {k: v for k, v in (manual.get(h) or {}).items() if not k.startswith("_")} for h in ("ga4", "gsc", "metricool", "ghl")}
    parcial = {k: v for k, v in (manual.get("parcial") or {}).items() if not k.startswith("_")}
    notas_man = {h: {k[1:]: v for k, v in (manual.get(h) or {}).items() if k.startswith("_") and k != "_nota"} for h in ("ga4", "gsc", "ghl")}

    bloques, con_dato = {}, {k: 0 for k in FUENTES}
    for cid, u in universo.items():
        nombre = u["ids"]["panel"]
        e = datos_ext.get(nombre, {}) if nombre else {}
        m = emp.get(nombre, {}) if nombre else {}
        b = {}

        def poner(fid, estado, **kw):
            motivo = (parcial.get(cid) or {}).get(fid)
            if motivo and estado in ("bien", "a_cero"):
                kw["medicion"] = "medias"
                kw["nota"] = motivo + (" · " + kw["nota"] if kw.get("nota") else "")
            if estado == "bien" and edad_h(hora) is not None and edad_h(hora) > FUENTES[fid][2]:
                estado = "dato_viejo"
            if estado in ("bien", "a_cero", "dato_viejo"):
                con_dato[fid] += 1
            b[fid] = bloque(FUENTES[fid][0], estado, hora=iso(hora), **kw)

        # GA4
        if cid in man["ga4"] and not man["ga4"][cid]:
            poner("ga4", "sin_conectar", nota=notas_man["ga4"].get(cid) or "descartada a mano", abrir=enlace("ga4", None))
        elif cid in man["ga4"] and m.get("ga") != man["ga4"][cid]:
            poner("ga4", "rota", emparejado={"id": man["ga4"][cid], "nombre": None, "metodo": "corrección a mano"},
                  abrir=enlace("ga4", man["ga4"][cid]),
                  nota="propiedad corregida a mano y todavía sin leer: relanzar la lectura de Analytics")
        elif m.get("ga"):
            ga = e.get("ga")
            emparejado = {"id": m["ga"], "nombre": m.get("ga_nombre"), "metodo": "por nombre y dominio, revisado a mano"}
            ab = enlace("ga4", m["ga"])
            ant_usuarios = ((ga or {}).get("anterior") or {}).get("usuarios") or 0
            if not ga:
                poner("ga4", "rota", emparejado=emparejado, abrir=ab, nota="propiedad emparejada pero no respondió")
            elif not ga.get("actual"):
                if ant_usuarios > 0:
                    poner("ga4", "rota", medicion="no", emparejado=emparejado, abrir=ab,
                          nota=f"sin medir desde hace más de un mes: {int(ant_usuarios)} usuarios en los 30 días anteriores y ninguno en los últimos 30 (la etiqueta de Analytics dejó de medir)",
                          alertas=[{"gravedad": "rojo", "dueno": "web",
                                    "texto": "Analytics no mide desde hace más de un mes: revisar la etiqueta en la web"}],
                          datos={"periodo": periodo, "actual": None, "anterior": ga.get("anterior")})
                else:
                    poner("ga4", "a_cero", emparejado=emparejado, abrir=ab, nota="sin visitas medidas en 30 días",
                          datos={"periodo": periodo, "actual": None, "anterior": ga.get("anterior")})
            else:
                poner("ga4", "bien", emparejado=emparejado, abrir=ab, datos={
                    "periodo": periodo, "actual": ga.get("actual"), "anterior": ga.get("anterior"),
                    "serie_usuarios": ga.get("serie"), "paginas": ga.get("paginas"), "canales": ga.get("canales")})
        else:
            poner("ga4", "sin_conectar", nota="sin propiedad de Analytics emparejada", abrir=enlace("ga4", None))
        # Search Console (Google va 2-3 días por detrás: las ventanas se cierran en el último día con datos)
        if cid in man["gsc"] and not man["gsc"][cid]:
            poner("gsc", "sin_conectar", nota=notas_man["gsc"].get(cid) or "descartado a mano", abrir=enlace("gsc", None))
        elif cid in man["gsc"] and m.get("gsc") != man["gsc"][cid]:
            poner("gsc", "rota", emparejado={"id": man["gsc"][cid], "nombre": man["gsc"][cid], "metodo": "corrección a mano"},
                  abrir=enlace("gsc", man["gsc"][cid]),
                  nota="sitio corregido a mano y todavía sin leer: relanzar la lectura de Search Console")
        elif m.get("gsc"):
            g = e.get("gsc")
            emparejado = {"id": m["gsc"], "nombre": m["gsc"], "metodo": "corrección a mano" if cid in man["gsc"] else "por dominio de la web"}
            if not g or g.get("_error"):
                poner("gsc", "rota", emparejado=emparejado, abrir=enlace("gsc", m["gsc"]), medicion="no",
                      nota=("sin permiso de lectura en este sitio de Search Console (error 403): pedir acceso o elegir otro sitio del dominio"
                            if (g or {}).get("_error") == 403 else "sitio emparejado que no respondió"))
            else:
                hasta = g.get("datos_hasta")
                poner("gsc", "a_cero" if todo_cero(g.get("actual")) else "bien", emparejado=emparejado,
                      abrir=enlace("gsc", m["gsc"]),
                      nota=(f"datos hasta el {hasta[8:10]}-{hasta[5:7]} (Google va 2-3 días por detrás)" if hasta
                            else "ventana hasta ayer: los 2-3 últimos días aún no tienen datos (lectura antigua)"),
                      medicion="hoy" if hasta else "medias",
                      datos={"periodo": g.get("periodo") or periodo, "periodo_anterior": g.get("periodo_anterior"),
                             "datos_hasta": hasta, "actual": g.get("actual"), "anterior": g.get("anterior"),
                             "serie_clics_impresiones": g.get("serie"), "consultas": limpiar_consultas(g.get("consultas"))})  # N14: sin filas de exportaciones de Google Ads
        else:
            poner("gsc", "sin_conectar", nota="sin sitio de Search Console emparejado", abrir=enlace("gsc", None))
        # Metricool (por id de marca)
        mc_id = man["metricool"].get(cid) or m.get("metricool_id")
        if m.get("metricool") or mc_id:
            r = e.get("redes")
            emparejado = {"id": mc_id, "nombre": m.get("metricool"), "metodo": "id de la marca" if mc_id else "nombre de la marca (falta el id)"}
            if r:
                poner("metricool", "bien", medicion="medias", nota="seguidores sí; publicaciones programadas todavía no",
                      emparejado=emparejado, abrir=enlace("metricool", mc_id), datos={k: v for k, v in r.items() if k != "perfil"})
            else:
                poner("metricool", "rota", emparejado=emparejado, abrir=enlace("metricool", mc_id),
                      nota="marca emparejada y todavía sin leer: relanzar la lectura de Metricool")
        else:
            poner("metricool", "sin_conectar", nota="sin marca de Metricool emparejada", abrir=enlace("metricool", None))
        # GHL (resumen de la subcuenta; el embudo completo va en «captacion_ghl»; una sola subcuenta por cliente)
        ghl_id = man["ghl"].get(cid) or m.get("ghl")
        if cid in man["ghl"] and not man["ghl"][cid]:   # N14: descartada a mano (p. ej. Sol-4 cogía una plantilla «Snapshot»)
            poner("ghl", "sin_conectar", nota=notas_man["ghl"].get(cid) or "descartada a mano", abrir=enlace("ghl", None))
        elif ghl_id:
            g = e.get("ghl") if m.get("ghl") == ghl_id else None
            emparejado = {"id": ghl_id, "nombre": m.get("ghl_nombre"), "metodo": "corrección a mano" if cid in man["ghl"] else "por nombre de la subcuenta"}
            if g:
                poner("ghl", "a_cero" if todo_cero(g) else "bien", emparejado=emparejado, abrir=enlace("ghl", ghl_id), datos=g)
            else:
                poner("ghl", "rota", emparejado=emparejado, abrir=enlace("ghl", ghl_id),
                      nota="subcuenta emparejada y todavía sin leer: relanzar la lectura de GHL")
        else:
            poner("ghl", "sin_conectar", nota="sin subcuenta de GHL emparejada", abrir=enlace("ghl", None))
        # Snov
        o = e.get("outreach")
        if o:
            poner("snov", "a_cero" if todo_cero(o.get("actual")) else "bien",
                  emparejado={"id": None, "nombre": ", ".join(c["nombre"] for c in o.get("campanas", [])[:5]), "metodo": "snov/por_cliente.py: nombre de campaña"},
                  datos={"periodo": periodo, "actual": o.get("actual"), "anterior": o.get("anterior"),
                         "campanas": [{"nombre": c.get("nombre"), "estado": c.get("estado"), "actual": c.get("actual")} for c in o.get("campanas", [])]})
        else:
            poner("snov", "no_aplica", nota="sin campañas de Snov con su nombre")
        bloques[cid] = b

    fichas = []
    for fid, (nombre, freq, lim) in FUENTES.items():
        ed = edad_h(hora)
        fichas.append({
            "id": fid, "nombre": nombre, "grupo": "herramienta RO",
            "origen": "Downloads/HERRAMIENTA_RO_2026-10-02/externos.json",
            "lector": "~/RO_HERRAMIENTAS/externos.py" + (" + snov/por_cliente.py" if fid == "snov" else ""),
            "plan": plan, "error": error, "frecuencia_h": freq, "limite_h": lim,
            "hora": iso(hora), "edad_h": ed,
            "estado": "rota" if not hora else ("dato_viejo" if ed > lim else "bien"),
            "clientes_con_dato": con_dato[fid],
        })
    return {"fichas": fichas, "bloques": bloques}

#!/usr/bin/env python3
"""
generar_ficha.py · datos propios del módulo M4 «Ficha del cliente» (2-oct-2026). Solo lectura, 0 llamadas a API.

Lo que la capa de E1 (data/clientes/<id>.json) NO trae y la ficha v3 sí enseñaba:

  data/ficha/portal.json              (se sirve recortado: filas con cliente_id → solo quien ve ese cliente)
      los 10 recursos del portal (Drive, ClickUp, hoja de estatus, informes, Looker, Meta, Google Ads,
      Analytics, Search Console) con «pendiente» si falta, la duda abierta y cuántos contactos hay.
  data/ficha/web.json                 (igual) búsquedas de Search Console (las 8 de más clics) y perfil de Metricool.
  data/ficha/_privado/contactos.json  (almacén privado: solo con /api/ver_dato y rastro, tipo «contactos_cliente»)
      personas del portal (rol, teléfonos, correos, nota, fuente) + agenda de móviles y correos del 2-oct.
  data/ficha/_privado/chat.json       (almacén privado, tipo «chat_cliente») canal de ClickUp del cliente y
      sus últimos 30 mensajes (los que llevan claves o contraseñas se ocultan; correos y teléfonos, saneados).

Fuentes (solo lectura):
  ~/Downloads/PANEL_OPERACIONES_2026-10-01/build/portal_clientes.json
  ~/Downloads/HERRAMIENTA_RO_2026-10-02/externos.json y chat.json (los genera ~/RO_HERRAMIENTAS/externos.py y chat.py)
  ~/Downloads/MOVILES_Y_CORREOS_CLIENTES_RO_2026-10-02.md (el mismo parseo que generar.py de la ficha v3)
  data/clientes/<id>.json (para los identificadores: ids.portal, ids.panel)

Uso:  python3 fuentes_ficha/generar_ficha.py
Escribe a temporal y renombra. Comprueba con escaner_secretos.py que los ficheros que se sirven en bloque
(portal.json y web.json) no llevan correos ni teléfonos; si los llevan, no escribe y sale con 2.
"""
import json
import os
import re
import sys
import tempfile
from datetime import datetime
from pathlib import Path

AQUI = Path(__file__).resolve().parent
APP = AQUI.parent
DATA = APP / "data"
SALIDA = DATA / "ficha"
HOME = Path.home()
sys.path.insert(1, str(Path(__file__).resolve().parents[1]))  # C5: rutas y secretos en config.py
import config  # noqa: E402
BUILD = config.PANEL_BUILD
HERR = config.HERRAMIENTA_RO
AGENDA_MD = config.MOVILES_CORREOS
AHORA = datetime.now().strftime("%Y-%m-%d %H:%M")

sys.path.insert(0, str(APP))
import escaner_secretos as ESC  # noqa: E402
sys.path.insert(0, str(AQUI))
from agenda_md import leer_agenda  # noqa: E402
from personas_cliente import construir  # noqa: E402

# Los 10 recursos del portal, en el orden de uso (lo que más se abre, primero: R «orden por frecuencia»).
RECURSOS = [("clickup", "Lista de ClickUp"), ("drive", "Drive"), ("metaAds", "Meta Ads"), ("statusSheet", "Hoja de estatus"),
            ("reports", "Informes"), ("analytics", "Analytics"), ("searchConsole", "Search Console"), ("googleAds", "Google Ads"),
            ("clickupFolder", "Carpeta de ClickUp"), ("looker", "Looker Studio")]

RX_SECRETO = re.compile(r"contrase|password|pass\s*[:=]|clave\s*[:=]|usuario\s*[:=]|\b2fa\b|código de verificación|token", re.I)
RX_CORREO = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[a-z]{2,}")
RX_TEL = re.compile(r"\+?\d[\d\s]{8,}\d")


def leer(p, defecto=None):
    try:
        return json.loads(Path(p).read_text())
    except Exception:
        return defecto


def escribir(ruta, obj):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=ruta.parent, suffix=".tmp")
    with os.fdopen(fd, "w") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    os.replace(tmp, ruta)


def limpiar_url(u):
    """Las hojas de Google llevan «?gid=703536824#gid=…»: la puerta de secretos lo confunde con un teléfono.
    Sin el gid se abre la primera pestaña de la hoja; el resto de la URL no cambia."""
    if not u:
        return None
    return re.sub(r"[?#]gid=\d+.*$", "", u) if "docs.google.com" in u else u


import permisos as P  # noqa: E402  (solo la regla de texto P.sin_importes; no toca reglas ni datos)


def partir_importes(t):
    """Ronda 11 (auditoría 35 / R12): nunca «[importe]» en un fichero. Devuelve (texto sin importe, texto completo o None).
    El texto sin importe va en el campo de siempre (lo ve todo el que abre la ficha) y se escribe sin hueco con la misma
    regla del servidor (P.sin_importes: fuera el paréntesis, la frase o la cifra con su preposición). Si había importe,
    el original va en un campo aparte «…_completa»: es una fila con cliente_id, así que el servidor le pasa
    P.sin_importes con lo que esa persona no ve (cuota o inversión) y a quien no ve ese dinero le llega igual que el corto."""
    t = t or ""
    if not P.RE_IMPORTE.search(t):
        return t, None
    corto = P.sin_importes(t)
    return corto, t


def campos_sin_importe(clave, t):
    """{clave: texto sin importe} y, solo si había importe, {clave_completa: original} (lo recorta el servidor)."""
    if t is None:
        return {clave: None}
    corto, completo = partir_importes(t)
    return {clave: corto, **({f"{clave}_completa": completo} if completo else {})}


def sanear(t):
    t = RX_CORREO.sub("[correo]", t or "")
    return RX_TEL.sub("[teléfono]", t)


def agenda():
    """Mismo parseo que ~/Downloads/HERRAMIENTA_RO_2026-10-02/generar.py (bloque «Agenda»)."""
    AG = {}
    if not AGENDA_MD.exists():
        return AG
    cur, modo = None, None
    for ln in AGENDA_MD.read_text(encoding="utf-8").splitlines():
        if ln.startswith("## ") and ln[3:] != "Índice":
            cur = ln[3:].strip(); AG[cur] = {"moviles": [], "correos": [], "dominios": "", "account": ""}; modo = None; continue
        if not cur:
            continue
        if ln.startswith("Account:"):
            AG[cur]["account"] = ln.split("Account:")[1].split("·")[0].strip()
            if "Dominios:" in ln:
                AG[cur]["dominios"] = ln.split("Dominios:")[1].strip()
        elif ln.startswith("**Móviles**"):
            modo = "m"
        elif ln.startswith("**Correos**"):
            modo = "c"
        elif modo == "m" and ln.startswith("- ") and "+" in ln:
            parts = [x.strip() for x in ln[2:].split(" · ")]
            tel = next((x for x in parts if x.startswith("+")), "")
            AG[cur]["moviles"].append({"nombre": parts[0] if not parts[0].startswith("+") else "", "tel": tel,
                                       "fuente": parts[-1].strip("_") if len(parts) > 2 else ""})
        elif modo == "c" and ln.startswith("| ") and "@" in ln.split("|")[1]:
            c = [x.strip() for x in ln.strip("|").split("|")]
            AG[cur]["correos"].append({"correo": c[0], "nombre": c[1] if c[1] != "—" else "", "fuente": c[2],
                                       "veces": int(c[3]) if len(c) > 3 and c[3].isdigit() else 0,
                                       "copia": int(c[4]) if len(c) > 4 and c[4].isdigit() else 0})
    return AG


def main():
    portal = {x["id"]: x for x in leer(BUILD / "portal_clientes.json", [])}
    ext = (leer(HERR / "externos.json", {}) or {}).get("clientes", {})
    chat = leer(HERR / "chat.json", {"porcliente": {}, "mensajes": {}, "canales": []})
    canales = {c["id"]: c for c in chat.get("canales", [])}
    EMP = (leer(DATA / "emparejamientos.json", {}) or {}).get("clientes", {})
    VERDAD = {c["cliente_id"]: c for c in (leer(DATA / "verdad" / "clientes.json", {}) or {}).get("clientes", [])}
    DINERO = {c["cliente_id"]: c for c in (leer(DATA / "dinero_cliente" / "dinero_cliente.json", {}) or {}).get("clientes", [])}
    MARCA_MC = {c["cliente_id"]: c.get("marca_id") for c in (leer(DATA / "redes" / "redes.json", {}) or {}).get("clientes", []) if c.get("marca_id")}
    BANDEJA = leer(DATA / "bandeja" / "bandeja.json", {}) or {}
    PROD = leer(DATA / "produccion" / "produccion.json", {}) or {}
    AGM = leer_agenda()
    AG = AGM["clientes"]
    ROLES = leer(AQUI / "_privado" / "roles.json", {}) or {}   # ronda 6 (M6)
    usados, cuadre, dudas_todas, uniones = set(), [], [], []

    filas_portal, filas_web, privado_ct, privado_chat = [], [], {}, {}
    sin_agenda, con_chat = [], 0
    for f in sorted((DATA / "clientes").glob("*.json")):
        doc = leer(f, {})
        cid, ids = doc.get("id"), doc.get("ids", {})
        pc = portal.get(ids.get("portal")) or {}
        panel = ids.get("panel") or doc.get("nombre")

        # ---- portal: recursos (se sirve) ----
        recursos = [{"k": k, "t": t, "url": limpiar_url(pc.get(k))} for k, t in RECURSOS]
        cts = pc.get("contacts") or []
        emp = (EMP.get(cid) or {})
        loc = ((emp.get("captacion_ghl") or {}).get("id") or (emp.get("ghl") or {}).get("id"))
        sr = (emp.get("seranking") or {}).get("id")
        mc = MARCA_MC.get(cid)
        atajos = [
            {"k": "ghl", "t": "Subcuenta de GoHighLevel", "url": f"https://app.gohighlevel.com/v2/location/{loc}/dashboard" if loc else None},
            {"k": "metricool", "t": "Metricool", "url": f"https://app.metricool.com/planner?blogId={mc}" if mc else None},
            {"k": "seranking", "t": "SE Ranking", "url": f"https://online.seranking.com/admin.site.rankings.site_id-{sr}.html" if sr else None},
        ]
        vd = VERDAD.get(cid) or {}
        din = DINERO.get(cid) or {}
        filas_portal.append({
            "cliente_id": cid, "nombre_portal": pc.get("name"), "recursos": recursos, "atajos": atajos,
            "account_id": vd.get("account"),
            # cuota de la fuente única (la que fija Dinero por cliente: Airtable de octubre); servir.py la quita a quien no la ve
            "cuota": din.get("cuota"), "cuota_fuente": din.get("cuota_fuente"),
            **campos_sin_importe("duda", sanear(pc.get("doubt")) if pc.get("doubt") else None),
            **campos_sin_importe("descripcion", pc.get("description")), "estado_portal": pc.get("status"), "nota_estado": sanear(pc.get("statusNote")) if pc.get("statusNote") else None,
            "contactos_n": len(cts), "account_portal": pc.get("accountManager"), "account_fuente": pc.get("amSource"),
        })

        # ---- web: búsquedas de Search Console y perfil de Metricool (se sirve) ----
        e = ext.get(panel) or {}
        gsc, redes = e.get("gsc") or {}, e.get("redes") or {}
        filas_web.append({
            "cliente_id": cid,
            "consultas": [{"q": q, "clics": cl, "impresiones": im, "posicion": pos} for q, cl, im, pos in (gsc.get("consultas") or [])[:8]],
            "perfil_metricool": redes.get("perfil"),
        })

        # ---- contactos (privado): personas unidas con rol y su fuente ----
        titulo = next((t for t in (pc.get("name"), panel, doc.get("nombre"), ids.get("libro")) if t and t in AG), None)
        ag = AG.get(titulo) if titulo else None
        if titulo:
            usados.add(titulo)
        else:
            sin_agenda.append(cid)
        if ag or cts:
            r = construir(ag, cts, ROLES, doc.get("nombre") or "", cid)
            r["titulo_documento"] = titulo
            privado_ct[cid] = {"datos": r}
            # cuadre contra el documento
            tel_app = {re.sub(r"\D", "", t["tel"]) for p in r["personas"] for t in p["telefonos"] if t.get("en_documento")}
            mail_app = {m["correo"] for p in r["personas"] for m in p["correos"] if m.get("en_documento")}
            tel_doc = {re.sub(r"\D", "", m["tel"]) for m in (ag or {}).get("moviles", [])}
            mail_doc = {c["correo"] for c in (ag or {}).get("correos", [])}
            extra_t = [t["tel"] for p in r["personas"] for t in p["telefonos"] if not t.get("en_documento")]
            extra_m = [m["correo"] for p in r["personas"] for m in p["correos"] if not m.get("en_documento")]
            dom = [d.lower() for d in (ag or {}).get("dominios", [])]
            ajenos = [c for c in mail_doc if dom and c.split("@")[1] not in dom and not re.search(r"gmail|hotmail|yahoo|outlook|icloud|live\.|telefonica|movistar", c)]
            cuadre.append({"cliente_id": cid, "titulo": titulo, "doc_moviles": len(tel_doc), "doc_correos": len(mail_doc),
                           "faltan_moviles": sorted(tel_doc - tel_app), "faltan_correos": sorted(mail_doc - mail_app),
                           "extra_portal_tel": extra_t, "extra_portal_correo": extra_m, "dominio_ajeno": sorted(ajenos),
                           "personas": len(r["personas"]), "buzones": sum(1 for p in r["personas"] if p["generico"]),
                           "con_rol": sum(1 for p in r["personas"] if p["rol"] and not p["generico"]),
                           "sin_rol": sum(1 for p in r["personas"] if not p["rol"] and not p["generico"])})
            for d in r["dudas"]:
                dudas_todas.append({"cliente": doc.get("nombre"), **d})
            uniones += [f"{doc.get('nombre')}: {u}" for u in r["uniones_pila"]]

        # ---- chat de ClickUp (privado) ----
        canal = chat.get("porcliente", {}).get(panel)
        if canal:
            con_chat += 1
            msgs = []
            for m in sorted(chat.get("mensajes", {}).get(canal, []), key=lambda m: m.get("fecha") or 0)[-30:]:
                t = re.sub(r"\[@([^\]]+)\]\(#user_mention#\d+\)", r"@\1", m.get("texto") or "")
                t = re.sub(r"!\[[^\]]*\]\([^)]*\)", "[imagen]", t)                      # imágenes pegadas
                t = re.sub(r"\[\s*([^\]]*?)\s*\]\((https?://[^)\s]+)\)", lambda x: (x.group(1).split("\n")[0].strip() or "enlace") + " ↗", t)  # [texto](url) → texto ↗
                t = re.sub(r"\n{3,}", "\n\n", t.replace("**", "")).strip()
                oculto = bool(RX_SECRETO.search(t))
                msgs.append({"id": m.get("id"), "quien": m.get("quien"), "fecha": m.get("fecha"), "respuestas": m.get("respuestas") or 0,
                             "texto": "[mensaje oculto: contenía una clave o contraseña]" if oculto else sanear(t), "oculto": oculto})
            privado_chat[cid] = {"datos": {"canal": canal, "nombre": (canales.get(canal) or {}).get("nombre"), "mensajes": msgs}}

    meta = {"generado": AHORA, "fuentes": ["portal_clientes.json (panel 1-oct)", "externos.json (2-oct)", "chat.json (2-oct 13:40)",
                                           "MOVILES_Y_CORREOS_CLIENTES_RO_2026-10-02.md"]}
    portal_doc = {"_meta": {**meta, "que": "Recursos del portal por cliente (10), duda abierta y número de contactos. Sin teléfonos ni correos."}, "filas": filas_portal}
    web_doc = {"_meta": {**meta, "que": "Búsquedas de Search Console (8 de más clics, 30 días) y perfil de Metricool."}, "filas": filas_web}

    # ---- correos y llamadas del cliente: los MISMOS de la Bandeja (una sola regla de «sin contestar», horas de lunes a viernes) ----
    correos = [{k: x.get(k) for k in ("cliente_id", "numero", "asunto", "horas", "dias_laborables", "desde", "gravedad", "queja", "auto", "url", "asignado_id", "estado_desk")}
               for x in BANDEJA.get("correos", []) if x.get("cliente_id")]
    llamadas = [{k: x.get(k) for k in ("cliente_id", "numero_oculto", "llamadas", "ultima", "horas", "gravedad", "sono_a_id")}
                for x in BANDEJA.get("llamadas", []) if x.get("cliente_id")]
    correos_doc = {"_meta": {"generado": BANDEJA.get("generado"), "que": "Correos de clientes sin contestar y llamadas sin devolver, copiados de la Bandeja (misma regla y misma hora).",
                             "horas": (BANDEJA.get("umbrales") or {}).get("horas")}, "correos": correos, "llamadas": llamadas}

    # ---- ficha básica de producción (solo lectura, sin dinero ni contactos): clientes de las tareas de cada persona ----
    por_persona = {}
    for t in PROD.get("cola", []):
        if not t.get("cli"):
            continue
        d = por_persona.setdefault(t["persona_id"], {}).setdefault(t["cli"], {"ref": t["cli"], "nombre": t.get("cliente"), "tareas": []})
        if len(d["tareas"]) < 12:
            d["tareas"].append({k: t.get(k) for k in ("tarea", "url", "estado", "vence", "vencida", "grupo")})
    ficha_por = {f["cliente_id"]: f for f in filas_portal}
    basica = []
    de_produccion = {p["persona_id"] for p in PROD.get("personas", []) if set(p.get("puestos") or []) & {"produccion", "redes"}}
    for pid, cls in por_persona.items():
        if pid not in de_produccion:
            continue
        lista = []
        for ref, d in cls.items():
            f = ficha_por.get(ref) or {}
            drive = next((r["url"] for r in f.get("recursos", []) if r["k"] == "drive" and r.get("url")), None)
            doc = leer(DATA / "clientes" / f"{ref}.json", {}) or {}
            mc = (((doc.get("fuentes") or {}).get("metricool") or {}).get("datos") or {})
            lista.append({**d, "web": doc.get("web"), "descripcion": f.get("descripcion"), "drive": drive,   # sin importes: producción no ve dinero
                          "redes": mc.get("redes") or [], "metricool": next((a["url"] for a in f.get("atajos", []) if a["k"] == "metricool" and a.get("url")), None)})
        basica.append({"persona_id": pid, "clientes": sorted(lista, key=lambda x: -len(x["tareas"]))})
    basica_doc = {"_meta": {"generado": AHORA, "que": "Ficha básica de solo lectura para producción: los clientes de sus tareas, sin dinero ni contactos."}, "filas": basica}

    # ---- informes del pasado (N2): hoja de Zoho importada + seguimiento de M13 + Looker + informe de la app por mes + fotos diarias ----
    HIST = leer(DATA / "informes" / "historico.json", {}) or {}
    M13 = leer(DATA / "informes" / "informes.json", {}) or {}
    PER = [x["id"] for x in ((leer(DATA / "informe" / "comun.json", {}) or {}).get("periodos") or []) if re.fullmatch(r"\d{4}-\d{2}", x.get("id", ""))]
    fotos = sorted(d.name for d in (APP / "historia").glob("20*") if d.is_dir()) if (APP / "historia").exists() else []
    seg = {(f["cliente_id"], f["mes"]): f for f in M13.get("filas", [])}
    filas_inf = []
    for f in filas_portal:
        cid = f["cliente_id"]
        looker = next((r["url"] for r in f.get("recursos", []) if r["k"] == "looker" and r.get("url")), None)
        reports = next((r["url"] for r in f.get("recursos", []) if r["k"] == "reports" and r.get("url")), None)
        meses = {}
        for h in HIST.get("filas", []):
            if h.get("cliente_id") == cid:
                meses[h["mes"]] = {"mes": h["mes"], "enlace_informe": h.get("enlace_informe"), "enlace_estadisticas": h.get("enlace_estadisticas"),
                                   "informado_en_reunion": h.get("informado_en_reunion"), "enviado": h.get("enviado"), "fuente": "hoja «Informes mensuales» de Zoho"}
        for (c2, mes), x in seg.items():
            if c2 != cid:
                continue
            m = meses.setdefault(mes, {"mes": mes, "fuente": "seguimiento de informes (ClickUp y Desk)"})
            m.update({"estado": x.get("estado"), "plazo": x.get("plazo"), "dias_retraso": x.get("dias_retraso"),
                      "tarea": (x.get("tarea") or {}).get("url"), "envio": (x.get("enviado") or {}).get("url"), "envio_fecha": (x.get("enviado") or {}).get("fecha"),
                      "envio_ticket": (x.get("enviado") or {}).get("ticket")})
            hj = x.get("hoja") or {}
            for k in ("enlace_informe", "enlace_estadisticas"):
                if not m.get(k) and hj.get(k):
                    m[k] = hj[k]
        for mes in PER:
            meses.setdefault(mes, {"mes": mes})["informe_app"] = f"#/informe-cliente/{cid}/{mes}"
        filas_inf.append({"cliente_id": cid, "looker": looker, "carpeta_informes": reports, "meses": sorted(meses.values(), key=lambda m: m["mes"], reverse=True)})
    informes_doc = {"_meta": {"generado": AHORA, "que": "Histórico de informes por cliente (N2).", "hoja_importada": HIST.get("importado"),
                              "fotos_diarias": fotos, "periodos_app": PER}, "filas": filas_inf}

    # Puerta de secretos sobre lo que se sirve en bloque: nada de correos ni teléfonos.
    tmpdir = Path(tempfile.mkdtemp())
    hall = []
    for nombre, obj in (("portal.json", portal_doc), ("web.json", web_doc), ("correos.json", correos_doc), ("basica.json", basica_doc), ("informes.json", informes_doc)):
        p = tmpdir / nombre
        p.write_text(json.dumps(obj, ensure_ascii=False))
        hall += ESC.escanear_fichero(p)
    if hall:
        print("La puerta de secretos ha encontrado algo; no escribo nada:", json.dumps(hall[:5], ensure_ascii=False))
        sys.exit(2)

    escribir(SALIDA / "portal.json", portal_doc)
    escribir(SALIDA / "web.json", web_doc)
    escribir(SALIDA / "correos.json", correos_doc)
    escribir(SALIDA / "basica.json", basica_doc)
    escribir(SALIDA / "informes.json", informes_doc)
    escribir(SALIDA / "_privado/contactos.json", {"_meta": {**meta, "que": "Contactos del cliente. Solo con /api/ver_dato (tipo contactos_cliente) y queda en el rastro."}, "clientes": privado_ct})
    escribir(SALIDA / "_privado/chat.json", {"_meta": {**meta, "que": "Canal de ClickUp del cliente. Solo con /api/ver_dato (tipo chat_cliente)."}, "clientes": privado_chat})
    sin_cliente = sorted(set(AG) - usados)
    (AQUI / "_cache").mkdir(exist_ok=True)
    (AQUI / "_privado").mkdir(exist_ok=True)
    (AQUI / "_privado" / "cuadre_contactos.json").write_text(json.dumps({"generado": AHORA, "documento": AGM["totales"], "titulos_sin_cliente": sin_cliente,
        "clientes": cuadre, "dudas": dudas_todas, "uniones_por_nombre_de_pila": uniones}, ensure_ascii=False, indent=1))
    print("cuadre: títulos del documento sin cliente:", sin_cliente, "· dudas:", len(dudas_todas))
    print(f"ok · {len(filas_portal)} clientes · contactos de {len(privado_ct)} · chat de {con_chat} · sin agenda: {', '.join(sin_agenda) or 'ninguno'}")
    # A4 · objetivo del cliente y semáforo del lunes: la lectura común de la base de la app (fuentes_objetivos/objetivos.py).
    from fuentes_objetivos import objetivos as OBJETIVOS
    o = OBJETIVOS.escribir()
    print(f"objetivos.json: {o['resumen']['clientes_con_objetivo']} con objetivo · {o['resumen']['clientes_con_semaforo']} con semáforo")


if __name__ == "__main__":
    main()

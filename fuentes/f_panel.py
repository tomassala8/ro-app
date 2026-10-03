"""Fuentes que ya recoge el panel de Mili (PANEL_OPERACIONES_2026-10-01/build).

Plan A: lanzar los lectores que regeneran build/ (cu.py todo, build.py…) — NO lo hace E1:
        el panel tiene su propia recarga (07:38 y 14:38) y sus dueños.
Plan B (el que se usa): leer los JSON de build/ y sellar cada bloque con la hora del fichero.

Fuentes que salen de aquí: cartera (ClickUp), horas (ClickUp), tareas (ClickUp), informes,
desk, zadarma, reuniones (CRM + Fathom + verificación manual), outreach, alarmas, arranque, chat.
"""
from comun import (AQUI, BUILD, HERRAMIENTA, PANEL, bloque, edad_h, fecha, iso, leer, mtime, sanear)

# id de fuente → (nombre, clave en salud.json/fresco, frecuencia objetivo en horas, límite antes de «dato viejo»)
FUENTES = {
    "cartera":   ("Cartera de ClickUp (account, semáforo, cuota)", "ClickUp (tareas y semáforos)", 1, 8),
    "horas":     ("Horas imputadas en ClickUp", "ClickUp (horas)", 1, 3),
    "tareas":    ("Tareas por cliente en ClickUp", "Flujo de tareas", 1, 8),
    "informes":  ("Informes mensuales (ClickUp + Desk)", "Informes mensuales", 24, 30),
    "desk":      ("Correos de cliente en Zoho Desk", "Desk (correos)", 1, 3),
    "zadarma":   ("Llamadas con el cliente (Zadarma)", "Zadarma", 1, 30),
    "reuniones": ("Reuniones (CRM, Fathom y verificación manual)", "CRM (reuniones)", 24, 30),
    "outreach":  ("Outreach (chats, hojas y Snov)", "Outreach", 24, 100),
    "alarmas":   ("Alarmas del panel de Mili", None, 1, 8),
    "arranque":  ("Arranque de clientes nuevos (firma → resultados)", None, 24, 30),
    "chat":      ("Canal de ClickUp del cliente", None, 24, 72),
}


def _hora_fuente(datos, salud, clave_fresco, fichero):
    if clave_fresco:
        h = fecha((datos.get("fresco") or {}).get(clave_fresco))
        if h:
            return h
    return mtime(fichero)


def cargar(universo):
    datos = leer(BUILD / "datos.json", {}) or {}
    salud = leer(BUILD / "salud.json", {}) or {}
    informes = leer(BUILD / "informes_mensuales.json", {}) or {}
    zad = leer(BUILD / "zadarma_por_cliente.json", {}) or {}
    flujo = leer(BUILD / "tareas_flujo.json", {}) or {}
    verif = (leer(BUILD / "reuniones_verificadas.json", {}) or {}).get("clientes", {})
    fathom = (leer(BUILD / "fathom_sep.json", {}) or {}).get("reuniones", [])
    rojos = leer(BUILD / "rojos_manual.json", {}) or {}
    _chat_json = leer(HERRAMIENTA / "chat.json", {}) or {}
    chat = _chat_json.get("porcliente", {})
    chat_nombres = {c.get("id"): c.get("nombre") for c in _chat_json.get("canales", [])}
    # N14 (2-oct-2026): el canal se elige por palabras sueltas del nombre y se equivocaba (AGC con el de Segú, MG con el
    # de Joan Lluís Vives, Gómez y Carvacho con el de Gómez de Barreda). Las correcciones van en el manual, por id de canal.
    chat_manual = {k: v for k, v in ((leer(AQUI / "emparejamientos_manual.json", {}) or {}).get("chat") or {}).items()
                   if not k.startswith("_")}
    triaje = (leer(BUILD / "triaje_desk.json", {}) or {}).get("tickets", [])

    por_panel = {c["nombre"]: c for c in datos.get("clientes", [])}
    nuevos = {n["nombre"]: n for n in datos.get("nuevos", [])}
    alarmas = {}
    for a in datos.get("alarmas", []):
        alarmas.setdefault(a["cliente"], []).append(a)
    sin_agente = {}
    for t in triaje:
        if t.get("cliente"):
            sin_agente.setdefault(t["cliente"], []).append(t)

    horas = {}
    for fid, (nombre, clave, freq, lim) in FUENTES.items():
        fichero = {"informes": BUILD / "informes_mensuales.json", "zadarma": BUILD / "zadarma_por_cliente.json",
                   "tareas": BUILD / "tareas_flujo.json", "chat": HERRAMIENTA / "chat.json",
                   "outreach": BUILD / "outreach_clientes.json"}.get(fid, BUILD / "datos.json")
        horas[fid] = _hora_fuente(datos, salud, clave, fichero)

    def viejo(fid):
        e = edad_h(horas[fid])
        return e is not None and e > FUENTES[fid][3]

    bloques, con_dato = {}, {k: 0 for k in FUENTES}
    for cid, u in universo.items():
        nombre = u["ids"]["panel"]
        c = por_panel.get(nombre)
        b = {}

        def poner(fid, estado, **kw):
            if estado == "bien" and viejo(fid):
                estado = "dato_viejo"
            if estado in ("bien", "dato_viejo", "a_cero"):
                con_dato[fid] += 1
            b[fid] = bloque(FUENTES[fid][0], estado, hora=iso(horas[fid]), **kw)

        if not c:
            for fid in FUENTES:
                poner(fid, "sin_conectar", nota="cliente fuera del panel de Mili (solo en el portal)")
            bloques[cid] = b
            continue

        # Cartera
        poner("cartera", "bien", prueba=c.get("enlace_clickup"), datos={
            "account": c.get("account"), "producto": c.get("producto"), "semaforo": c.get("semaforo"),
            "semaforo_al_dia": c.get("semaforo_al_dia"), "cuota": c.get("cuota"), "cuota_fuente": c.get("cuota_fuente"),
            "nuevo": c.get("nuevo"), "riesgo_panel": c.get("riesgo"), "agente_desk": c.get("agente_desk"),
            "exento": c.get("exento"), "motivo_exento": sanear(c.get("motivo_exento")),
            "rojo_manual": {k: sanear(v) for k, v in (rojos.get(nombre) or {}).items()} or None,
        })
        # Horas
        h = {k: c.get(k) for k in ("horas_presup_mes", "horas_mes", "horas_mes_ant", "pct_horas")}
        poner("horas", "bien" if any(v for v in h.values()) else "a_cero",
              medicion="medias", nota="con ~52 % de horas imputadas en el equipo: orientativo", datos=h)
        # Tareas
        f = flujo.get(nombre) or c.get("flujo")
        if f:
            poner("tareas", "bien", datos={
                "carpeta_id": f.get("carpeta_id"), "abiertas_por_estado": f.get("abiertas_por_estado"),
                "rev_pm": f.get("rev_pm"), "rev_tecnica": f.get("rev_tecnica"),
                "revision_total": c.get("revision"), "revision_mas_48h": c.get("revision48"),
                "rev_estados": c.get("rev_estados"),
                "creadas_mes": f.get("creadas_mes"), "creadas_mes_ant": f.get("creadas_mes_ant"),
                "no_planificadas_semana": f.get("no_planificadas_semana"), "cerradas_semana": f.get("cerradas_semana"),
                "vencidas": f.get("vencidas"), "sin_fecha": f.get("sin_fecha"),
                "en_revision_detalle": [{"nombre": sanear(t.get("nombre")), "estado": t.get("estado"),
                                         "dias": t.get("dias"), "url": t.get("url")} for t in (c.get("det_rev") or [])[:15]],
            })
        else:
            poner("tareas", "sin_conectar", nota="sin carpeta de cliente en ClickUp")
        # Informes
        inf = informes.get(nombre)
        if inf:
            poner("informes", "bien", prueba=(inf.get("sep") or {}).get("url"), datos={
                m: {"estado": v.get("estado"), "fecha_envio": v.get("fecha_envio"), "prueba": sanear(v.get("prueba")),
                    "url": v.get("url"), "responsable": v.get("responsable")} if isinstance(v, dict) else v
                for m, v in inf.items()})
        else:
            poner("informes", "sin_conectar", nota="sin fila en informes_mensuales.json")
        # Desk
        if c.get("sin_desk"):
            poner("desk", "sin_conectar", nota="cliente sin cuenta en Desk")
        else:
            pend = c.get("det_pend") or []
            poner("desk", "bien" if (c.get("tickets_abiertos") or pend) else "a_cero", datos={
                "tickets_abiertos": c.get("tickets_abiertos"), "pendientes_horas": c.get("pend_horas"),
                "ult_correo_saliente": c.get("ult_saliente"), "correo_esta_semana": c.get("correo_semana"),
                "sin_contestar": [{"numero": t.get("numero"), "asunto": sanear(t.get("asunto")), "dias": t.get("dias"),
                                   "desde": t.get("desde"), "url": t.get("url"), "asignado": t.get("asignado")}
                                  for t in pend[:20]],
                "sin_agente": [{"numero": t.get("numero"), "asunto": sanear(t.get("asunto")), "fecha": t.get("fecha"),
                                "horas_sin_agente": t.get("horas_sin_agente"), "url": t.get("url")}
                               for t in sin_agente.get(nombre, [])[:20]],
            })
        # Zadarma (sin números: ni completos ni enmascarados)
        z = zad.get(nombre)
        if z:
            def limpio(x):
                return {k: x.get(k) for k in ("contestadas", "contestadas_30s_o_mas", "intentos_sin_contestar",
                                               "minutos_totales", "ultima_contestada", "ultimo_intento",
                                               "por_persona", "confianza_cruce")}
            poner("zadarma", "bien" if (z.get("contestadas") or z.get("intentos_sin_contestar")) else "a_cero",
                  datos={"septiembre": limpio(z), "octubre": limpio(z.get("oct") or {}),
                         "resumen_panel": {k: v for k, v in (c.get("llamadas") or {}).items()}})
        else:
            ll = c.get("llamadas") or {}
            poner("zadarma", "a_cero" if not ll.get("sin_telefono") else "sin_conectar",
                  nota="sin teléfono del cliente conocido" if ll.get("sin_telefono") else "ninguna llamada desde el 1-sep",
                  datos={"resumen_panel": ll})
        # Reuniones
        poner("reuniones", "bien", medicion="medias",
              nota="CRM + Fathom de Tomás; las reuniones de Zoom van aparte (fuente zoom)", datos={
                  "ult_reunion": c.get("ult_reunion"), "prox_reunion": c.get("prox_reunion"),
                  "reunion_este_mes": c.get("reunion_mes"),
                  "dias_sin_reunion": c.get("dias_sin_reunion") if (c.get("dias_sin_reunion") or 0) < 900 else None,
                  "reuniones_mes_anterior": c.get("reuniones_mes_ant"),
                  "historial": [{"fecha": r.get("fecha"), "asunto": sanear(r.get("asunto")), "fuente": r.get("fuente"),
                                 "quien": r.get("quien")} for r in (c.get("det_reus") or [])[-12:]],
                  "fathom_septiembre": [{"fecha": f_[1], "titulo": sanear(f_[2])} for f_ in fathom if f_[0] == nombre],
                  "verificacion_septiembre": {k: sanear(v) for k, v in (verif.get(nombre) or c.get("det_verif") or {}).items()} or None,
              })
        # Outreach
        o = c.get("outreach")
        if o and o.get("canales"):
            poner("outreach", "bien", medicion="medias", nota="cifras de chats y hojas: muchas a null",
                  prueba=o.get("fuente") if str(o.get("fuente", "")).startswith("http") else None,
                  datos={k: (sanear(v) if isinstance(v, str) else v) for k, v in o.items()})
        else:
            poner("outreach", "no_aplica", nota="sin servicio de outreach")
        # Alarmas
        al = alarmas.get(nombre, [])
        poner("alarmas", "bien" if al else "a_cero", datos=[{
            "id": a.get("id"), "gravedad": a.get("gravedad"), "tipo": a.get("tipo"), "texto": sanear(a.get("texto")),
            "accion": sanear(a.get("accion")), "enlace": a.get("enlace"), "desde": a.get("desde"),
            "responsable": a.get("account")} for a in al])
        # Arranque
        n = nuevos.get(nombre)
        if n:
            poner("arranque", "bien", datos={k: n.get(k) for k in ("firma", "alta", "dia", "account", "estado")} | {
                "hitos": [{k: (sanear(v) if k == "prueba" else v) for k, v in h_.items()} for h_ in n.get("hitos", [])],
                "nota": sanear(n.get("nota"))})
        else:
            poner("arranque", "no_aplica", nota="no es alta reciente")
        # Chat
        canal = chat_manual[cid] if cid in chat_manual else chat.get(nombre)
        poner("chat", "bien" if canal else "sin_conectar", datos={"canal_id": canal} if canal else None,
              emparejado={"id": canal, "nombre": sanear(chat_nombres.get(canal) or ""),
                          "metodo": "corrección a mano" if cid in chat_manual else "por nombre del canal"} if canal else None,
              nota=None if canal else ("sin canal de ClickUp propio (corregido a mano)" if cid in chat_manual else "sin canal de ClickUp emparejado"))
        bloques[cid] = b

    fichas = []
    for fid, (nombre, clave, freq, lim) in FUENTES.items():
        e = edad_h(horas[fid])
        fichas.append({
            "id": fid, "nombre": nombre, "grupo": "panel de Mili",
            "origen": str(BUILD.relative_to(PANEL.parent)), "lector": "lectores del panel (cu.py, zh.py, zd.py, build.py)",
            "plan": "B · último fichero de build/ (la recarga del panel es de sus dueños)",
            "frecuencia_h": freq, "limite_h": lim, "hora": iso(horas[fid]), "edad_h": e,
            "estado": "dato_viejo" if (e is not None and e > lim) else ("bien" if horas[fid] else "rota"),
            "clientes_con_dato": con_dato[fid],
        })
    return {"fichas": fichas, "bloques": bloques}

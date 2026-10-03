"""Fuentes del día a día que ya generan los módulos de la app (3-oct-2026): sustituyen al panel de Mili del 2-oct.

Hasta hoy cartera, horas, tareas, Desk, reuniones y alarmas salían de PANEL_OPERACIONES/build (el panel de Mili, con su
recarga de las 07:38 y las 14:38) y quedaban «dato_viejo» en cuanto pasaban sus horas. Ahora E1 lee lo que ya dejan los
módulos con sus propias lecturas en vivo (solo lectura, 0 llamadas desde aquí):

  cartera   ← data/verdad/clientes.json (account principal vigente de asignaciones, alta nueva, cuota única de Dinero)
  horas     ← data/produccion/produccion.json → proyectos.horas_mes / horas_mes_ant (horas de ClickUp con la llave propia)
  tareas    ← data/produccion/produccion.json → revisiones y bloqueos en vivo + proyectos (el flujo por proyecto)
  desk      ← data/bandeja/bandeja.json y por_cliente.json (Desk en vivo, la regla de la Bandeja)
  reuniones ← data/reuniones/reuniones.json (CRM, Fathom, Zoom y WhatsApp con la misma regla que En rojo)
  alarmas   ← data/alertas/alertas.json (las alertas abiertas del cliente, con su dueño)

Lo que ningún módulo da todavía se queda con el valor del panel y se dice en «del_panel» (campos y hora), nunca
mezclado sin avisar. Las claves de «datos» son las de siempre (FORMATO.md): los módulos que leen la capa no cambian.
Sin un fichero de módulo, el bloque se queda como lo dejó el panel (con su hora y su «dato_viejo»).

Ciclo sin bucles: generar_reuniones.py lee de la capa el CRM y Fathom en bruto; por eso el bruto del panel viaja en
reuniones.datos.crm_panel y la vista consolidada (que sale de Reuniones) va en las claves de arriba.
"""
from comun import SALIDA, bloque, edad_h, fecha, iso, leer, mtime, sanear

LIM = {"cartera": 8, "horas": 3, "tareas": 8, "desk": 3, "reuniones": 30, "alarmas": 8}
NOMBRES = {
    "cartera": "Cartera (account de asignaciones, alta y cuota de la verdad única)",
    "horas": "Horas por cliente en ClickUp (módulo Producción)",
    "tareas": "Tareas por cliente en ClickUp (módulo Producción)",
    "desk": "Correos de cliente en Zoho Desk (módulo Bandeja)",
    "reuniones": "Reuniones (módulo Reuniones: CRM, Fathom, Zoom y WhatsApp)",
    "alarmas": "Alertas abiertas del cliente (módulo Alertas)",
}
ORIGEN = {
    "cartera": "data/verdad/clientes.json", "horas": "data/produccion/produccion.json",
    "tareas": "data/produccion/produccion.json", "desk": "data/bandeja/por_cliente.json",
    "reuniones": "data/reuniones/reuniones.json", "alarmas": "data/alertas/alertas.json",
}
GRAVEDAD = {"alta": "rojo", "media": "ambar", "baja": "gris"}


def _hora(*cands):
    for c in cands:
        h = fecha(c) if isinstance(c, str) else c
        if h:
            return h
    return None


def _por(lista, clave="cliente_id"):
    out = {}
    for x in lista or []:
        if isinstance(x, dict) and x.get(clave):
            out.setdefault(x[clave], []).append(x)
    return out


def aplicar(universo, panel):
    """Sustituye en `panel` (lo que devuelve f_panel.cargar) las seis fuentes por las de los módulos."""
    D = SALIDA
    verdad = leer(D / "verdad/clientes.json", {}) or {}
    prod = leer(D / "produccion/produccion.json", {}) or {}
    band = leer(D / "bandeja/bandeja.json", {}) or {}
    bpc = leer(D / "bandeja/por_cliente.json", {}) or {}
    reus = leer(D / "reuniones/reuniones.json", {}) or {}
    aler = leer(D / "alertas/alertas.json", {}) or {}
    personas = leer(D / "personas.json", []) or []
    personas = personas if isinstance(personas, list) else personas.get("personas", [])
    nombre_p = {p.get("id"): p.get("nombre") for p in personas if isinstance(p, dict)}

    V = {c["cliente_id"]: c for c in verdad.get("clientes") or [] if isinstance(c, dict) and c.get("cliente_id")}
    PRO = {p["cliente_id"]: p for p in prod.get("proyectos") or [] if p.get("cliente_id")}
    REV = _por(prod.get("revisiones"))
    COR = _por(band.get("correos"))
    TRI = _por(band.get("triaje"))
    BPC = {c["cliente_id"]: c for c in bpc.get("clientes") or [] if c.get("cliente_id")}
    REU = {c["cliente_id"]: c for c in reus.get("clientes") or [] if c.get("cliente_id")}
    ZOOM = _por(reus.get("asistencias"), "cli")
    ALE = _por([a for a in aler.get("alertas") or [] if a.get("estado") in ("nueva", "vista", "reabierta", "lo_tengo")])

    fprod = prod.get("fuentes") or {}
    horas = {
        "cartera": _hora(mtime(D / "verdad/clientes.json")) if V else None,
        "horas": _hora((fprod.get("horas") or {}).get("hora")) if PRO else None,
        "tareas": _hora((fprod.get("tareas") or {}).get("hora")) if PRO else None,
        "desk": _hora(((bpc.get("fuentes") or {}).get("desk") or {}).get("hora"), bpc.get("generado")) if bpc else None,
        "reuniones": _hora((reus.get("_meta") or {}).get("generado")) if REU else None,
        "alarmas": _hora(aler.get("generado")) if aler.get("alertas") is not None else None,
    }
    hora_flujo = _hora((fprod.get("flujo") or {}).get("hora"))
    vivas = {k for k, h in horas.items() if h}
    fichas = {f["id"]: f for f in panel["fichas"]}
    hora_panel = {k: (fichas.get(k) or {}).get("hora") for k in vivas}
    con_dato = {k: 0 for k in vivas}
    del_panel_todo = {k: 0 for k in vivas}     # clientes que siguen con el bloque entero del panel (ningún módulo los cubre)

    def estado_de(fid, hay):
        e = edad_h(horas[fid])
        if e is not None and e > LIM[fid]:
            return "dato_viejo"
        return "bien" if hay else "a_cero"

    for cid, b in panel["bloques"].items():
        viejo = {k: (b.get(k) or {}) for k in vivas}
        pd = {k: (viejo[k].get("datos") if isinstance(viejo[k].get("datos"), (dict, list)) else None) for k in vivas}

        def poner(fid, hay, datos, *, del_panel=None, nota=None, medicion=None, estado=None, prueba=None):
            est = estado or estado_de(fid, hay)
            if est in ("bien", "a_cero", "dato_viejo"):
                con_dato[fid] += 1
            nb = bloque(NOMBRES[fid], est, hora=iso(horas[fid]), medicion=medicion or viejo[fid].get("medicion") or "hoy",
                        nota=nota, datos=datos, prueba=prueba if prueba is not None else viejo[fid].get("prueba"),
                        abrir=viejo[fid].get("abrir"))
            nb["origen"] = ORIGEN[fid]
            if del_panel:
                nb["del_panel"] = {"campos": del_panel, "hora": hora_panel.get(fid),
                                   "nota": "Sin módulo que lo dé todavía: valor del panel de Mili con su hora."}
            b[fid] = nb

        # ---------------------------------------------------------------- cartera
        if "cartera" in vivas:
            v = V.get(cid)
            if v:
                p = pd["cartera"] or {}
                acc = v.get("account")
                datos = {**p, "account": nombre_p.get(acc) if acc else None, "account_id": acc,
                         "cuota": v.get("cuota"), "cuota_fuente": v.get("cuota_fuente"), "nuevo": bool(v.get("nuevo"))}
                quedan = [k for k in ("producto", "semaforo", "semaforo_al_dia", "riesgo_panel", "agente_desk", "exento",
                                      "motivo_exento", "rojo_manual") if p.get(k) not in (None, False, "")]
                poner("cartera", True, datos, del_panel=quedan or None,
                      nota=None if acc else "sin account principal en asignaciones")
            elif viejo["cartera"].get("estado") in ("bien", "a_cero", "dato_viejo"):
                del_panel_todo["cartera"] += 1

        # ---------------------------------------------------------------- horas
        if "horas" in vivas:
            p = pd["horas"] or {}
            pr = PRO.get(cid)
            if pr:
                presup = p.get("horas_presup_mes")
                hm, ha = pr.get("horas_mes"), pr.get("horas_mes_ant", p.get("horas_mes_ant"))
                # pct_horas = el mes anterior (cerrado) frente a lo pautado, como lo daba la Cartera de ClickUp
                datos = {"horas_presup_mes": presup, "horas_mes": hm, "horas_mes_ant": ha,
                         "pct_horas": round(ha / presup * 100) if (presup and ha is not None) else None}
                poner("horas", any(datos.get(k) for k in ("horas_mes", "horas_mes_ant")), datos,
                      del_panel=["horas_presup_mes"] if presup is not None else None, medicion="medias",
                      nota="orientativo: no todo el equipo imputa sus horas")
            elif viejo["horas"].get("estado") in ("bien", "a_cero", "dato_viejo"):
                del_panel_todo["horas"] += 1      # sin carpeta en Producción: se queda el bloque del panel, con su hora

        # ---------------------------------------------------------------- tareas
        if "tareas" in vivas:
            p = pd["tareas"] or {}
            pr = PRO.get(cid)
            rv = REV.get(cid, [])
            if pr or rv:
                pm = [r for r in rv if r.get("revisa") == "account"]
                te = [r for r in rv if r.get("revisa") == "técnica"]
                bl = [r for r in rv if r.get("estado") == "bloqueado"]

                def resumen(xs):
                    return {"n": len(xs), "mas48": sum(1 for r in xs if r.get("mas48")),
                            "max_dias": max((r.get("dias") or 0 for r in xs), default=0)}
                pr = pr or {}
                datos = {
                    "carpeta_id": p.get("carpeta_id"), "abiertas": pr.get("abiertas"),
                    "abiertas_por_estado": p.get("abiertas_por_estado"),
                    "rev_pm": resumen(pm), "rev_tecnica": resumen(te), "bloqueadas": resumen(bl),
                    "revision_total": len(pm) + len(te), "revision_mas_48h": sum(1 for r in pm + te if r.get("mas48")),
                    "creadas_mes": pr.get("creadas_mes", p.get("creadas_mes")), "creadas_mes_ant": pr.get("creadas_mes_ant", p.get("creadas_mes_ant")),
                    "no_planificadas_semana": pr.get("no_planificadas", p.get("no_planificadas_semana")),
                    "cerradas_semana": pr.get("cerradas_semana", p.get("cerradas_semana")),
                    "vencidas": pr.get("vencidas", p.get("vencidas")), "sin_fecha": pr.get("sin_fecha", p.get("sin_fecha")),
                    "rev_estados": {est: {"n": len(xs), "mas48": sum(1 for r in xs if r.get("mas48")),
                                          "max": round(max((r.get("dias") or 0 for r in xs), default=0))}
                                    for est, xs in (("revisión project manager", pm), ("revisión técnica", te), ("bloqueado", bl)) if xs},
                    "en_revision_detalle": [{"nombre": sanear(r.get("tarea")), "estado": r.get("estado"), "dias": r.get("dias"),
                                             "url": f"https://app.clickup.com/t/{r['id']}" if r.get("id") else None}
                                            for r in sorted(pm + te + bl, key=lambda r: -(r.get("dias") or 0))[:15]],
                }
                poner("tareas", True, datos,
                      del_panel=["abiertas_por_estado"] if p.get("abiertas_por_estado") else None,
                      nota=(f"revisiones y bloqueos en vivo; abiertas, vencidas, creadas y cerradas, del flujo por proyecto"
                            f" de {iso(hora_flujo)}") if hora_flujo and edad_h(hora_flujo) is not None and edad_h(hora_flujo) > LIM["tareas"] else None)

            elif viejo["tareas"].get("estado") in ("bien", "a_cero", "dato_viejo"):
                del_panel_todo["tareas"] += 1

        # ---------------------------------------------------------------- desk
        if "desk" in vivas and viejo["desk"].get("estado") != "sin_conectar":
            p = pd["desk"] or {}
            filas = COR.get(cid, [])
            vivos = [x for x in filas if not x.get("auto")]
            r = BPC.get(cid) or {}
            tri = TRI.get(cid, [])
            datos = {
                "tickets_abiertos": len(filas), "pendientes_horas": r.get("horas_max"),
                "ult_correo_saliente": p.get("ult_correo_saliente"), "correo_esta_semana": p.get("correo_esta_semana"),
                "sin_contestar_bandeja": r.get("sin_contestar", 0), "mas_48h": r.get("mas_48", 0), "quejas": r.get("quejas", 0),
                "sin_contestar": [{"numero": t.get("numero"), "asunto": sanear(t.get("asunto")), "dias": t.get("dias_laborables"),
                                   "desde": (t.get("desde") or "")[:10] or None, "url": t.get("url"), "asignado": t.get("asignado")}
                                  for t in sorted(vivos, key=lambda t: -(t.get("horas") or 0))[:20]],
                "sin_agente": [{"numero": t.get("numero"), "asunto": sanear(t.get("asunto")), "fecha": t.get("fecha"),
                                "dias": t.get("dias"), "url": t.get("url")} for t in tri[:20]],
            }
            quedan = [k for k in ("ult_correo_saliente", "correo_esta_semana") if p.get(k) is not None]
            poner("desk", bool(filas or tri), datos, del_panel=quedan or None,
                  nota="correos de la Bandeja (sin automáticos ni ruido, días laborables)")
            if datos["sin_contestar"]:
                b["desk"]["abrir"] = {"texto": "Abrir en Desk", "url": datos["sin_contestar"][0]["url"]}

        # ---------------------------------------------------------------- reuniones
        if "reuniones" in vivas:
            p = pd["reuniones"] or {}
            r = REU.get(cid)
            if r:
                crm = {k: p.get(k) for k in ("ult_reunion", "prox_reunion", "reunion_este_mes", "dias_sin_reunion",
                                              "reuniones_mes_anterior", "historial", "fathom_septiembre", "verificacion_septiembre")}
                zoom = [{"fecha": a.get("fecha"), "asunto": sanear(a.get("tema"))[:90], "fuente": "Zoom", "quien": a.get("anfitrion")}
                        for a in ZOOM.get(cid, []) if (a.get("minutos_reunion") or 0) >= 20]
                vistos, hist = set(), []
                for x in (crm.get("historial") or []) + zoom:
                    k = (x.get("fecha"), x.get("fuente"))
                    if x.get("fecha") and k not in vistos:
                        vistos.add(k)
                        hist.append(x)
                hist.sort(key=lambda x: x.get("fecha") or "")
                mes_pasado = r.get("mes")
                n_mes = (r.get("reuniones_crm") or 0) + (r.get("reuniones_zoom") or 0) + (r.get("reuniones_fathom") or 0) + (r.get("reuniones_whatsapp") or 0)
                datos = {
                    "ult_reunion": r.get("ultima"), "prox_reunion": r.get("proxima"),
                    "reunion_este_mes": crm.get("reunion_este_mes"),
                    "dias_sin_reunion": r.get("dias_sin") if (r.get("dias_sin") or 0) < 900 else None,
                    "reuniones_mes_anterior": n_mes, "mes_anterior": mes_pasado, "estado_mes_anterior": r.get("estado"),
                    "por_fuente_mes_anterior": {"crm": r.get("reuniones_crm") or 0, "zoom": r.get("reuniones_zoom") or 0,
                                                "fathom": r.get("reuniones_fathom") or 0, "whatsapp": r.get("reuniones_whatsapp") or 0},
                    "historial": hist[-12:],
                    "fathom_septiembre": crm.get("fathom_septiembre"),
                    "verificacion_septiembre": crm.get("verificacion_septiembre"),
                    "crm_panel": crm,
                }
                poner("reuniones", bool(r.get("ultima") or n_mes), datos, del_panel=["reunion_este_mes", "crm_panel"],
                      medicion="medias", nota="Zoom solo ve las reuniones grabadas; lo que no pasa por CRM, Fathom, Zoom o WhatsApp no cuenta")
            elif viejo["reuniones"].get("estado") in ("bien", "a_cero", "dato_viejo"):
                del_panel_todo["reuniones"] += 1

        # ---------------------------------------------------------------- alarmas
        if "alarmas" in vivas:
            al = sorted(ALE.get(cid, []), key=lambda a: ({"alta": 0, "media": 1, "baja": 2}.get(a.get("gravedad"), 3), a.get("desde") or ""))
            datos = [{"id": a.get("id"), "gravedad": GRAVEDAD.get(a.get("gravedad"), "gris"), "tipo": a.get("titulo"),
                      "texto": sanear(a.get("motivo")), "accion": sanear(a.get("ir_texto")) or None, "comprueba": sanear(a.get("comprueba")), "enlace": a.get("ir"),
                      "desde": (a.get("desde") or "")[:10] or None, "responsable": nombre_p.get(a.get("responsable_ahora") or a.get("dueno_id")),
                      "departamento": a.get("departamento")} for a in al]
            poner("alarmas", bool(datos), datos, prueba=None)

    for f in panel["fichas"]:
        fid = f["id"]
        if fid not in vivas:
            continue
        e = edad_h(horas[fid])
        f.update({"nombre": NOMBRES[fid], "grupo": "módulos de la app", "origen": ORIGEN[fid],
                  "lector": "generadores de los módulos (lectura en vivo con las llaves de la app)",
                  "plan": "A · lo que dejó el módulo en su última lectura", "limite_h": LIM[fid],
                  "hora": iso(horas[fid]), "edad_h": e, "estado": "dato_viejo" if (e is not None and e > LIM[fid]) else "bien",
                  "clientes_con_dato": con_dato[fid] + del_panel_todo[fid], "clientes_del_panel": del_panel_todo[fid],
                  "antes": {"origen": "panel de Mili", "hora": hora_panel.get(fid)}})
        if del_panel_todo[fid]:
            f["nota"] = (f"{del_panel_todo[fid]} clientes sin dato en el módulo siguen con el del panel de Mili "
                         f"({hora_panel.get(fid)}), marcado con su hora.")
        if fid == "tareas" and hora_flujo:
            f["nota"] = (f"Revisiones y bloqueos en vivo; el flujo por proyecto (abiertas, vencidas, creadas) es de {iso(hora_flujo)}."
                         + (" " + f["nota"] if del_panel_todo[fid] else ""))
    return panel

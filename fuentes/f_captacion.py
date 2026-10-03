"""Meta Ads y embudo de GoHighLevel por cliente (la Torre de Control dentro de la app).

Plan A: 20_FASE2_CAPTACION/captacion.json, que genera ~/RO_HERRAMIENTAS/captacion/captacion.py
        (Meta Marketing API + GHL app privada, solo lectura). E1 NO lo ejecuta: solo lo lee.
Corrección a mano (emparejamientos_manual.json → «meta»): si la cuenta buena no es la que trae captacion.json
        (Kiosko Box → «Josep SG»), E1 la lee directamente (f_meta_directo.py) con las mismas ventanas y la
        misma definición de lead, y descarta la de captacion.json.
Plan B (si el cliente no está en captacion.json): meta_clientes.json del panel (30 días y septiembre), sin embudo.
Avisos que salen aquí: pago pendiente (rojo), cuenta en otra zona horaria (ámbar), moneda distinta del euro (ámbar).
"""
import f_meta_directo
from comun import AQUI, BUILD, CAPTACION, bloque, edad_h, enlace, fecha, iso, leer, mtime, norm

FUENTES = {
    "meta":          ("Meta Ads", 1, 30),
    "captacion_ghl": ("Embudo y citas en GoHighLevel (90 días)", 1, 30),
}
ZONA_CASA = "Europe/Madrid"


def _desfase_h(zona):
    """Horas de diferencia con Madrid ahora mismo (0 = el día de Meta coincide con el de Madrid)."""
    from datetime import datetime
    from zoneinfo import ZoneInfo
    try:
        ahora = datetime.now(ZoneInfo(ZONA_CASA))
        return round((ahora.utcoffset() - ahora.astimezone(ZoneInfo(zona)).utcoffset()).total_seconds() / 3600, 1)
    except Exception:  # noqa: BLE001
        return 0


def _alertas_cuenta(info, estado_cuenta):
    al = []
    if estado_cuenta == 3 or (info or {}).get("estado") == 3:
        al.append({"gravedad": "rojo", "dueno": "account",
                   "texto": "La cuenta de Meta está en «pago pendiente»: los anuncios no se publican hasta que el cliente pague"})
    if info and info.get("zona") and _desfase_h(info["zona"]):
        al.append({"gravedad": "ambar", "dueno": "trafficker",
                   "texto": f"Meta cuenta el día en la zona de la cuenta ({info['zona']}, {abs(_desfase_h(info['zona'])):g} h de diferencia con Madrid): «ayer» y los 7 días se desplazan"})
    if info and info.get("moneda") and info["moneda"] != "EUR":
        al.append({"gravedad": "ambar", "dueno": "trafficker",
                   "texto": f"La cuenta factura en {info['moneda']}: no se suma al gasto en euros"})
    return al


def cargar(universo, en_vivo=False):
    cap = leer(CAPTACION, None)
    meta_panel = leer(BUILD / "meta_clientes.json", {}) or {}
    manual = leer(AQUI / "emparejamientos_manual.json", {}) or {}
    corr = {k: v for k, v in (manual.get("meta") or {}).items() if not k.startswith("_")}
    excluir = {k: v for k, v in (manual.get("meta_excluir") or {}).items() if not k.startswith("_")}
    manual_ghl = {k: v for k, v in (manual.get("ghl") or {}).items() if not k.startswith("_")}
    hora_cap = (fecha(cap.get("generado")) if cap else None) or mtime(CAPTACION)
    hora_meta_panel = fecha((meta_panel.get("_meta") or {}).get("generado")) or mtime(BUILD / "meta_clientes.json")
    ventanas = (cap or {}).get("ventanas") or f_meta_directo.hoy_ventanas()

    directo, error_directo = f_meta_directo.cargar(sorted(set(corr.values())), ventanas, en_vivo=en_vivo)
    info_cuentas = {c["id"]: c for c in (directo or {}).get("cuentas", [])}
    hora_directo = fecha((directo or {}).get("leido"))

    por_id, por_nombre = {}, {}
    for c in (cap or {}).get("clientes", []):
        por_id[c["id"]] = c
        por_nombre[norm(c["nombre"])] = c

    bloques, con_dato = {}, {k: 0 for k in FUENTES}
    plan_b_usado, corregidas = 0, []
    for cid, u in universo.items():
        c = por_id.get(u["ids"]["captacion"]) or por_nombre.get(norm(u["nombre"]))
        b = {}
        lim = FUENTES["meta"][2]
        m = (c or {}).get("meta") or {}
        act_bueno = corr.get(cid)
        if act_bueno and m.get("cuenta_id") != act_bueno:
            # --- cuenta corregida a mano: datos leídos por E1
            diario = ((directo or {}).get("diario") or {}).get(act_bueno)
            info = info_cuentas.get(act_bueno, {})
            emparejado = {"id": act_bueno, "nombre": info.get("nombre"), "metodo": "corrección a mano por id de cuenta",
                          "descartada": m.get("cuenta_id")}
            if isinstance(diario, list):
                r = f_meta_directo.resumir(diario, ventanas)
                estado = "bien" if any(r["gasto"].values()) else "a_cero"
                b["meta"] = bloque(
                    FUENTES["meta"][0], estado, hora=iso(hora_directo), emparejado=emparejado,
                    nota="cuenta corregida a mano: leída directamente de Meta con las mismas ventanas que Captación",
                    abrir=enlace("meta", act_bueno), alertas=_alertas_cuenta(info, info.get("estado")),
                    datos={"estado_cuenta": {1: "activa", 2: "desactivada", 3: "pago pendiente"}.get(info.get("estado"), info.get("estado")),
                           "zona": info.get("zona"), "moneda": info.get("moneda"),
                           "gasto": r["gasto"], "leads": r["leads"], "cpl": r["cpl"],
                           "ultimo_dia_con_gasto": r["ultimo_dia_con_gasto"], "serie": r["serie"],
                           "objetivo": (c or {}).get("objetivo"), "presupuesto": None, "metas": None, "campanas": None,
                           "severidad": None, "motivos": [], "avisos": [],
                           "responsable_en_captacion": (c or {}).get("responsable")})
                con_dato["meta"] += 1
                corregidas.append(cid)
            else:
                b["meta"] = bloque(FUENTES["meta"][0], "rota", emparejado=emparejado, abrir=enlace("meta", act_bueno),
                                   nota="cuenta corregida a mano y todavía sin leer: recargar con lectura en vivo de Meta"
                                        + (f" ({error_directo})" if error_directo else ""))
        elif c:
            info = dict(info_cuentas.get(m.get("cuenta_id"), {}))
            info["zona"] = m.get("zona_horaria") or info.get("zona")
            info["moneda"] = m.get("moneda") or info.get("moneda")
            ed = edad_h(hora_cap)
            estado = "rota" if m.get("error") else ("a_cero" if not any((m.get("gasto") or {}).values()) else "bien")
            if estado == "bien" and ed is not None and ed > lim:
                estado = "dato_viejo"
            b["meta"] = bloque(
                FUENTES["meta"][0], estado, hora=iso(hora_cap),
                nota=m.get("error") or ("cuenta sin gasto en 35 días" if estado == "a_cero" else None),
                emparejado={"id": m.get("cuenta_id"), "nombre": m.get("cuenta_nombre"), "metodo": "emparejado del panel por id de cuenta"},
                abrir=enlace("meta", m.get("cuenta_id")),
                alertas=_alertas_cuenta(info, m.get("estado_cuenta")),
                datos={
                    "estado_cuenta": m.get("estado_texto"), "zona": info.get("zona"), "moneda": info.get("moneda"),
                    "convertida_a_madrid": m.get("convertida_a_madrid"),
                    "gasto": m.get("gasto"), "leads": m.get("leads"),
                    "cpl": m.get("cpl"), "ultimo_dia_con_gasto": m.get("ultimo_dia_con_gasto"),
                    "cpl_resumen": c.get("cpl"), "objetivo": c.get("objetivo"), "presupuesto": c.get("presupuesto"),
                    "metas": c.get("metas"), "campanas": c.get("campanas"), "serie": c.get("serie"),
                    "severidad": c.get("severidad"), "motivos": c.get("motivos"), "avisos": c.get("avisos"),
                    "problema_publicidad": c.get("problema_publicidad"),
                    "problema_seguimiento": c.get("problema_seguimiento"),
                    "problema_integracion": c.get("problema_integracion"),
                    "responsable_en_captacion": c.get("responsable"),
                })
            con_dato["meta"] += estado != "rota"
        else:
            mp = meta_panel.get(u["ids"]["panel"]) if u["ids"]["panel"] else None
            if mp:
                plan_b_usado += 1
                todo_nulo = not any((mp.get("d30") or {}).get(k) for k in ("gasto", "impresiones"))
                b["meta"] = bloque(
                    FUENTES["meta"][0], "a_cero" if todo_nulo else "bien", hora=iso(hora_meta_panel), medicion="medias",
                    nota="dato de reserva del panel (no está en Captación)" + ("; " + mp["nota"] if mp.get("nota") else ""),
                    emparejado={"id": mp.get("cuenta_id"), "nombre": mp.get("cuenta_nombre"), "metodo": f"panel · confianza {mp.get('confianza')}"},
                    abrir=enlace("meta", mp.get("cuenta_id")),
                    datos={k: mp.get(k) for k in ("d30", "sep", "campanas_activas", "ultimo_gasto", "ultimo_anuncio_nuevo")})
                con_dato["meta"] += 1
            else:
                b["meta"] = bloque(FUENTES["meta"][0], "sin_conectar", nota="sin cuenta de Meta emparejada", abrir=enlace("meta", None))
        if excluir.get(cid):
            b["meta"]["excluidas"] = excluir[cid]

        # --- embudo de GHL
        g = (c or {}).get("ghl")
        sub = (c or {}).get("ghl_subcuenta") or ({"id": manual_ghl[cid], "nombre": None} if cid in manual_ghl else None)
        if g and not g.get("error"):
            b["captacion_ghl"] = bloque(
                FUENTES["captacion_ghl"][0], "a_cero" if not (g.get("embudo") or {}).get("contactos_90d") else "bien",
                hora=iso(hora_cap), emparejado={"id": (sub or {}).get("id"), "nombre": (sub or {}).get("nombre"),
                                                 "metodo": "emparejado de Captación por id de subcuenta"},
                abrir=enlace("ghl", (sub or {}).get("id")),
                datos={"embudo": g.get("embudo"), "calendarios": g.get("calendarios"), "citas": g.get("citas"),
                       "coste_por_cita": c.get("coste_por_cita")})
            con_dato["captacion_ghl"] += 1
        elif c:
            b["captacion_ghl"] = bloque(FUENTES["captacion_ghl"][0], "rota" if g else "sin_conectar", hora=iso(hora_cap),
                                        abrir=enlace("ghl", (sub or {}).get("id")),
                                        nota=(g or {}).get("error") or "cuenta de Meta sin subcuenta de GHL emparejada")
        else:
            b["captacion_ghl"] = bloque(FUENTES["captacion_ghl"][0], "sin_conectar", abrir=enlace("ghl", (sub or {}).get("id")),
                                        nota="el embudo solo se calcula para clientes con cuenta de Meta")
        bloques[cid] = b

    # Cuentas de Meta con gasto que no son de ningún cliente (prueba de la auditoría: > 500 € en 30 días)
    emparejadas = {b["meta"]["emparejado"]["id"] for b in bloques.values() if b["meta"].get("emparejado")}
    descartadas = {x for v in excluir.values() for x in v}
    conocidas = {k: v for k, v in (manual.get("meta_sin_cliente_conocidas") or {}).items() if not k.startswith("_")}
    sueltas = [x for x in info_cuentas.values() if x["gasto_30d"] > 500 and x["id"] not in emparejadas
               and x["id"] not in descartadas and x["id"] not in conocidas]
    fuera = [{"id": x["id"], "nombre": x["nombre"], "gasto_30d": x["gasto_30d"], "etiqueta": conocidas[x["id"]].split(":")[1].strip() if ":" in conocidas[x["id"]] else conocidas[x["id"]]}
             for x in info_cuentas.values() if x["id"] in conocidas]

    fichas = []
    ed = edad_h(hora_cap)
    for fid, (nombre, freq, lim) in FUENTES.items():
        fichas.append({
            "id": fid, "nombre": nombre, "grupo": "captación",
            "origen": "Captación (Meta + GHL)" + (" con reserva del panel" if fid == "meta" else ""),
            "lector": "captacion.py (lo mantiene Captación; E1 solo lee)" + (" + lectura directa de cuentas corregidas" if fid == "meta" else ""),
            "plan": "A · Captación" if cap else "B · panel",
            "plan_b_clientes": plan_b_usado if fid == "meta" else None,
            "cuentas_corregidas_a_mano": corregidas if fid == "meta" else None,
            "lectura_directa": ({"hora": iso(hora_directo), "error": error_directo,
                                 "llamadas": (directo or {}).get("llamadas")} if fid == "meta" else None),
            "cuentas_con_gasto_sin_cliente": ([{"id": x["id"], "nombre": x["nombre"], "gasto_30d": x["gasto_30d"],
                                                "moneda": x["moneda"]} for x in sueltas] if fid == "meta" else None),
            "cuentas_que_no_son_clientes": fuera if fid == "meta" else None,
            "frecuencia_h": freq, "limite_h": lim, "hora": iso(hora_cap), "edad_h": ed,
            "estado": "sin_conectar" if not cap else ("dato_viejo" if ed > lim else "bien"),
            "clientes_con_dato": con_dato[fid],
            "llamadas_api_ultima_recarga": (cap or {}).get("llamadas_api"),
        })
    return {"fichas": fichas, "bloques": bloques}

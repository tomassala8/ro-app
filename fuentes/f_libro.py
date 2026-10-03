"""Libro de clientes corregido (fuente única de activos, D-16) y facturación de Holded por cliente,
y la foto de asignaciones y servicios de la fase 0 (BORRADOR hasta que Mili cierre dudas.md).

Origen (solo lectura):
  ~/Downloads/BAJAS_LTV_CHURN_2026-10-01/clientes.json   (Holded + motivos de baja; 1-oct)
  20_FASE0_DATOS/asignaciones.json                        (E0 la convierte en la tabla oficial)
No toca el Airtable de facturación (lo lleva Sofía).
"""
from comun import FASE0, LIBRO, bloque, edad_h, iso, leer, mtime

FUENTES = {
    "libro":        ("Libro de clientes y facturación (Holded)", 24 * 30, 24 * 35),
    "asignaciones": ("Asignaciones y servicios (fase 0, borrador)", 24, 24 * 7),
}


def cargar(universo):
    libro = leer(LIBRO, {}) or {}
    f0 = leer(FASE0 / "asignaciones.json", {}) or {}
    h_libro, h_f0 = mtime(LIBRO), mtime(FASE0 / "asignaciones.json")
    f0_cli = {c["cliente_id"]: c for c in f0.get("clientes", [])}
    pers = leer(FASE0 / "personas.json", {}) or {}
    pers = pers.get("personas", pers) if isinstance(pers, dict) else pers
    de_baja = {p["id"]: p.get("nombre") for p in pers if p.get("estado") == "baja"}
    f0_asig = {}
    for a in f0.get("asignaciones", []):
        f0_asig.setdefault(a["cliente_id"], []).append(a)

    bloques, con = {}, {k: 0 for k in FUENTES}
    for cid, u in universo.items():
        b = {}
        fila = libro.get(u["ids"]["libro"]) if u["ids"]["libro"] else None
        if fila:
            b["libro"] = bloque(FUENTES["libro"][0], "bien", hora=iso(h_libro), medicion="hoy",
                                emparejado={"id": fila.get("cif"), "nombre": u["ids"]["libro"], "metodo": "razón social del libro (alias en universo.py)"},
                                datos={k: fila.get(k) for k in ("estado", "segmento", "tipo", "sector", "clasif", "espec",
                                                                 "primera", "ultima", "cuota_actual", "meses", "ltv",
                                                                 "vida_meses", "fecha_baja", "motivo", "pm")}
                                | {"facturas_holded": fila.get("holded")})
            con["libro"] += 1
        else:
            b["libro"] = bloque(FUENTES["libro"][0], "sin_conectar",
                                nota="no está en el libro corregido del 1-oct (¿alta nueva o nombre distinto?)")
        pid = u["ids"]["fase0"]
        c = f0_cli.get(pid)
        if c:
            b["asignaciones"] = bloque(
                FUENTES["asignaciones"][0], "bien", hora=iso(h_f0), medicion="medias",
                nota="BORRADOR fase 0: sin validar por Mili; trafficker, CRM, SEO, web y redes salen de horas imputadas",
                datos={"sillas": {k: (c.get(k) if c.get(k) not in de_baja else next(
                                      (a["persona_id"] for a in f0_asig.get(pid, [])
                                       if a.get("silla") == k and a.get("persona_id") not in de_baja), None))
                                  for k in ("account", "trafficker", "crm", "seo", "web", "redes", "outreach")},
                       "servicios": dict(c.get("servicios") or {}), "huecos": c.get("huecos"),
                       "filas": [{k: a.get(k) for k in ("persona_id", "silla", "principal", "confianza", "fuente", "duda")}
                                 for a in f0_asig.get(pid, []) if a.get("persona_id") not in de_baja],
                       "fuera_por_baja": sorted({a["persona_id"] for a in f0_asig.get(pid, []) if a.get("persona_id") in de_baja})})
            con["asignaciones"] += 1
        else:
            b["asignaciones"] = bloque(FUENTES["asignaciones"][0], "sin_conectar", nota="sin fila en la fase 0 (no está en el portal)")
        bloques[cid] = b

    fichas = [
        {"id": "libro", "nombre": FUENTES["libro"][0], "grupo": "dinero", "origen": "Downloads/BAJAS_LTV_CHURN_2026-10-01/clientes.json",
         "lector": "Holded (hd.py) + revisión manual del 1-oct", "plan": "B · libro corregido del 1-oct (se rehace a mano cada mes)",
         "frecuencia_h": FUENTES["libro"][1], "limite_h": FUENTES["libro"][2], "hora": iso(h_libro), "edad_h": edad_h(h_libro),
         "estado": "bien" if h_libro else "sin_conectar", "clientes_con_dato": con["libro"],
         "nota": "Holded en vivo por cliente todavía no: hd.py solo lee compras"},
        {"id": "asignaciones", "nombre": FUENTES["asignaciones"][0], "grupo": "personas", "origen": "20_FASE0_DATOS/asignaciones.json",
         "lector": "20_FASE0_DATOS/generar_fase0.py", "plan": "B · borrador del 2-oct", "frecuencia_h": FUENTES["asignaciones"][1],
         "limite_h": FUENTES["asignaciones"][2], "hora": iso(h_f0), "edad_h": edad_h(h_f0),
         "estado": "bien" if h_f0 else "sin_conectar", "clientes_con_dato": con["asignaciones"]},
    ]
    return {"fichas": fichas, "bloques": bloques}

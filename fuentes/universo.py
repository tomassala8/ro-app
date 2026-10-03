"""Universo de clientes y tabla de identificadores cruzados.

El id de la app es slug(nombre del panel) (igual que build_data.py). Cada herramienta usa otro:
el portal y la fase 0 usan el id del portal («abner»), captación usa guiones bajos («bit_24»),
el libro de bajas usa la razón social («Productikaonline»). Aquí se cruzan una vez y se guardan.

Fuente única de «activo» (D-16): libro corregido BAJAS_LTV_CHURN_2026-10-01/clientes.json.
"""
from comun import BUILD, LIBRO, leer, norm, slug, tokens

# Razón social del libro → nombre del panel cuando los nombres no comparten palabras.
ALIAS_LIBRO = {
    "Productikaonline": "Akua",
    "Strategic Management Business": "Ecom Advisory",
    "Ignasi Solà Coll": "Finexen",
    "Lobo Smart": "Lobo",
    "E Advisory": "ECIJA Advisory",
    "Organització Bonet Asesores": "Bonet Asesores",
    "Busbac Serveis": "Busbac",
    "Fermín Liébana Casellas": "Liebana Consulting",
    "Christian Sánchez Sánchez": "Christian Sanchez",
    "Gestanex Solutions": "Gestanex",
    "Volatt Jurídico Y Fiscal": "Volatt",
    "Campalans Assesorament I Gestió": "Campalans",
    "Centro Consulting (CE Consulting Zaragoza)": "Centro Consulting",
    "Orejana Gestión Emprendedora": "Orejana",
    "Asesoría Aster": "Aster Asesoría",
    "Asesoría FITECC": "Fitec Asesores",
    "Kioskobox": "Kiosko Box",
    "Bit24": "BIT 24",
    "Deudout": "Deudot",
    "EMEX (Martínez y Jacal)": "Emex",
    "GAC Grup": "GAC",
    "AseLegal": "Aselegal",
    "Asetra Asesoría": "Asetra",
    "AHEDO": "Ahedo",
    "AVANTIK": "Avantik",
    "Grupo Billeo": "Billeo",
    "Tribulex Asesores": "Tribulex",
    "Oteca Asesores": "Oteca",
    "Sol-4 Gestion Investment And Consulting": "Sol-4",
    "Innova Scala Consulting": "Innova Scala",
    "Joan Lluís Vives Economistes": "Joan Lluís Vives",
    "Romero Martínez Asesores": "Romero Martínez",
    "Torrevieja Consult": "Torrevieja Consult",
    "Imfor Asesores": "Imfor Asesores",
}


# Parecidos de nombre que NO son el mismo cliente (memoria 1-oct: Barreda Díaz ≠ Quique Gómez de Barreda).
NO_CASAR = {"Barreda Diaz Asesores", "Barreda Díaz Asesores", "Uhy Fay & Co Auditores Asesores"}


def construir():
    datos = leer(BUILD / "datos.json", {})
    portal_lista = leer(BUILD / "portal_clientes.json", []) or []
    portal_por_nombre = {p["name"]: p for p in portal_lista}
    portal_panel = datos.get("portal") or {}
    libro = leer(LIBRO, {}) or {}

    clientes = {}
    for c in datos.get("clientes", []):
        nombre = c["nombre"]
        p_panel = portal_panel.get(nombre) or {}
        p = portal_por_nombre.get(p_panel.get("nombre_portal")) or {}
        clientes[slug(nombre)] = {
            "id": slug(nombre),
            "nombre": nombre,
            "web": p_panel.get("web") or p.get("web"),
            "ids": {
                "app": slug(nombre),
                "panel": nombre,
                "portal": p.get("id"),
                "fase0": p.get("id"),
                "captacion": slug(nombre).replace("-", "_"),
                "libro": None,
            },
            "en_panel": True,
            "en_portal": bool(p),
        }

    # Del portal que no está en el panel (p. ej. Think Value, JENASA): se añaden con el id del portal.
    usados = {v["ids"]["portal"] for v in clientes.values() if v["ids"]["portal"]}
    for p in portal_lista:
        if p["id"] in usados:
            continue
        cid = p["id"]
        clientes[cid] = {
            "id": cid, "nombre": p["name"], "web": p.get("web"),
            "ids": {"app": cid, "panel": None, "portal": p["id"], "fase0": p["id"],
                    "captacion": cid.replace("-", "_"), "libro": None},
            "en_panel": False, "en_portal": True,
        }

    # Libro de bajas: estado oficial (activo / baja) y facturación.
    por_nombre = {v["nombre"]: k for k, v in clientes.items()}
    sin_casar = []
    for razon, fila in libro.items():
        if razon in NO_CASAR:
            if fila.get("estado") == "Activo":
                sin_casar.append(razon)
            continue
        destino = ALIAS_LIBRO.get(razon)
        cid = por_nombre.get(destino) if destino else None
        if not cid:
            t = tokens(razon)
            candidatos = [(len(t & tokens(v["nombre"])), k) for k, v in clientes.items()]
            candidatos = [x for x in candidatos if x[0] > 0]
            candidatos.sort(reverse=True)
            if candidatos and (len(candidatos) == 1 or candidatos[0][0] > candidatos[1][0]):
                cid = candidatos[0][1]
            elif norm(razon) in {norm(v["nombre"]) for v in clientes.values()}:
                cid = next(k for k, v in clientes.items() if norm(v["nombre"]) == norm(razon))
        if cid and not clientes[cid]["ids"]["libro"]:
            clientes[cid]["ids"]["libro"] = razon
        elif fila.get("estado") == "Activo":
            sin_casar.append(razon)

    for v in clientes.values():
        fila = libro.get(v["ids"]["libro"]) if v["ids"]["libro"] else None
        v["activo_libro"] = (fila or {}).get("estado") if fila else None
    return clientes, sin_casar

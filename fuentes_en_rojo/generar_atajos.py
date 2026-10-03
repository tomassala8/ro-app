#!/usr/bin/env python3
"""fuentes_en_rojo/generar_atajos.py · atajos «Abrir en …» de cada cliente para En rojo (ronda de arreglos, 2-oct).

Solo lectura de ficheros ya generados por otros módulos (no llama a ninguna API):
  · data/ficha/portal.json      → lista y carpeta de ClickUp, Drive, Meta, Analytics y Search Console (portal de clientes)
  · data/captacion/captacion.json → cuenta de Meta (si el portal no la tiene)
  · data/crm/crm.json           → subcuenta de GoHighLevel y sus conversaciones
  · data/alarmas.json           → ticket de Desk del correo sin contestar más antiguo (alarma «Sin responder»)
  · data/clientes.json          → tarea del cliente en ClickUp (Cartera)
Salida: data/en_rojo/atajos.json con una fila por cliente { cliente_id, atajos: [{k, t, url}], faltan: [k] }.
Solo URLs de herramientas internas (ningún teléfono, correo ni dato de lead). servir.py la recorta por cliente.
Formatos: 26_ARQUITECTURA_ERRORES_PLANES_B.md, parte C.2.
"""
import json
from datetime import datetime
from pathlib import Path

AQUI = Path(__file__).resolve().parent.parent
DATA = AQUI / "data"


def leer(rel, defecto):
    try:
        return json.loads((DATA / rel).read_text())
    except Exception:
        return defecto


# Orden = de lo que más se abre a lo que menos (Desk y ClickUp a diario; Drive y Analytics, menos).
ORDEN = [("desk", "Desk"), ("clickup", "ClickUp"), ("ghl", "GHL"), ("meta", "Meta"), ("drive", "Drive"),
         ("clickupFolder", "Carpeta de ClickUp"), ("analytics", "Analytics"), ("searchConsole", "Search Console")]
DEL_PORTAL = {"clickup": "clickup", "clickupFolder": "clickupFolder", "drive": "drive", "metaAds": "meta",
              "analytics": "analytics", "searchConsole": "searchConsole"}


def main():
    clientes = leer("clientes.json", [])
    portal = {f["cliente_id"]: f for f in leer("ficha/portal.json", {}).get("filas", [])}
    capt = {c["cliente_id"]: c for c in leer("captacion/captacion.json", {}).get("clientes", []) if c.get("cliente_id")}
    crm = {s["cliente_id"]: s for s in leer("crm/crm.json", {}).get("subcuentas", []) if s.get("cliente_id")}
    alarmas = leer("alarmas.json", [])
    desk = {}
    for a in alarmas:   # el ticket del correo más antiguo sin contestar (alarma «Sin responder»)
        if a.get("ambito") == "cliente" and a.get("tipo") == "Sin responder" and "desk.zoho" in (a.get("enlace") or ""):
            desk.setdefault(a["cliente_id"], a["enlace"])

    filas = []
    for c in clientes:
        cid = c["id"]
        u = {}
        for r in (portal.get(cid) or {}).get("recursos", []):
            k = DEL_PORTAL.get(r.get("k"))
            if k and r.get("url"):
                u.setdefault(k, r["url"])
        if "meta" not in u and ((capt.get(cid) or {}).get("cuenta_meta") or {}).get("enlace"):
            u["meta"] = capt[cid]["cuenta_meta"]["enlace"]
        enl = (crm.get(cid) or {}).get("enlaces") or {}
        if enl.get("ghl"):
            u["ghl"] = enl["ghl"]
        if "clickup" not in u and c.get("enlace_clickup"):
            u["clickup"] = c["enlace_clickup"]
        if cid in desk:
            u["desk"] = desk[cid]
        filas.append({
            "cliente_id": cid,
            "atajos": [{"k": k, "t": t, "url": u[k]} for k, t in ORDEN if u.get(k)],
            # «desk» solo falta si hay correos sin contestar y no hay ticket; si no hay nada pendiente no es un hueco
            "faltan": [k for k, _ in ORDEN if not u.get(k) and k not in ("desk", "clickupFolder")],
        })

    salida = {
        "_meta": {"generado": datetime.now().strftime("%Y-%m-%d %H:%M"), "zona": "Europe/Madrid",
                  "origen": "portal de clientes (ficha/portal), captación, salud del CRM, alarmas (Desk) y Cartera",
                  "uso": "En rojo: «Abrir en …» por cliente. Lo que falta sale en gris «Falta emparejar · Mili»."},
        "filas": filas,
    }
    (DATA / "en_rojo").mkdir(exist_ok=True)
    (DATA / "en_rojo" / "atajos.json").write_text(json.dumps(salida, ensure_ascii=False, indent=1))
    cuenta = {k: sum(1 for f in filas if any(a["k"] == k for a in f["atajos"])) for k, _ in ORDEN}
    print(f"data/en_rojo/atajos.json · {len(filas)} clientes · {cuenta}")


if __name__ == "__main__":
    main()

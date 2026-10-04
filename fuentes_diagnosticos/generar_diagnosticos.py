#!/usr/bin/env python3
"""fuentes_diagnosticos/generar_diagnosticos.py · escribe data/diagnosticos/diagnosticos.json. SOLO LECTURA, 0 llamadas.

Lee lo que ya dejan otros generadores (no rehace nada):
  · fuentes_crm/_privado/ghl_vivo.json   leads de 30 días con su conversación, oportunidades y citas (generar_crm.py)
                                         → aquí se leen correos y teléfonos EN MEMORIA; a la salida solo van recuentos
  · data/crm/crm.json                     subcuenta → cliente de la app
  · data/captacion/captacion.json         coste por lead de Meta y su referencia (generar_captacion.py)
  · fuentes_seo/_cache/gsc.json           páginas y búsquedas de Search Console, 28 días (generar_seo.py)

Uso:  python3 fuentes_diagnosticos/generar_diagnosticos.py [--salida <fichero>]
Pruebas: RO_DIAG_GHL, RO_DIAG_CRM, RO_DIAG_CAPTACION, RO_DIAG_GSC y RO_DIAG_AHORA («AAAA-MM-DD HH:MM», hora de Madrid)
apuntan a ficheros inventados (probar_diagnosticos.py). Nunca se escribe en data/ desde una prueba.
"""
import datetime as dt
import json
import os
import sys
import zoneinfo
from pathlib import Path

AQUI = Path(__file__).resolve().parent
APP = AQUI.parent
sys.path.insert(0, str(AQUI))
import diagnosticos as D  # noqa: E402

MAD = zoneinfo.ZoneInfo("Europe/Madrid")
RUTAS = {
    "ghl": os.environ.get("RO_DIAG_GHL") or APP / "fuentes_crm" / "_privado" / "ghl_vivo.json",
    "crm": os.environ.get("RO_DIAG_CRM") or APP / "data" / "crm" / "crm.json",
    "captacion": os.environ.get("RO_DIAG_CAPTACION") or APP / "data" / "captacion" / "captacion.json",
    "gsc": os.environ.get("RO_DIAG_GSC") or APP / "fuentes_seo" / "_cache" / "gsc.json",
}


def leer(p):
    try:
        return json.loads(Path(p).read_text())
    except Exception:
        return None


def numero(v, claves=("30d", "mes", "mes_anterior", "7d")):
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, dict):
        for k in claves:
            if isinstance(v.get(k), (int, float)):
                return float(v[k])
    return None


def construir(ahora):
    ahora_ms = int(ahora.timestamp() * 1000)
    ghl, crm, cap, gsc = (leer(RUTAS[k]) or {} for k in ("ghl", "crm", "captacion", "gsc"))
    vivo = ghl.get("vivo") or {}
    filas = crm.get("filas") or crm.get("subcuentas") or []
    sub_cli = {f["sub_id"]: f for f in filas if f.get("cliente_id") and f.get("tipo", "cliente") == "cliente"}
    cap_cli = {c["cliente_id"]: c for c in (cap.get("clientes") or []) if c.get("cliente_id")}
    gsc_cli = gsc.get("clientes") or {}

    entradas = {}
    for sid, f in sub_cli.items():
        v = vivo.get(sid)
        if not v:
            continue
        e = entradas.setdefault(f["cliente_id"], {"nombre": f.get("nombre")})
        e["leads"] = (e.get("leads") or []) + (v.get("leads") or [])
        e["oportunidades"] = (e.get("oportunidades") or []) + (v.get("oportunidades") or [])
        e["citas"] = (e.get("citas") or []) + (v.get("citas") or [])
    for cid, c in cap_cli.items():
        e = entradas.setdefault(cid, {"nombre": c.get("nombre")})
        cpl = numero(c.get("cpl"))
        if cpl is not None and "leads" in e:
            e["cpl"] = cpl
            e["cpl_referencia"] = numero((c.get("objetivo") or {}).get("cpl_usado")) or numero((c.get("cpl_resumen") or {}).get("ref"))
    for cid, g in gsc_cli.items():
        if g.get("_error"):
            continue
        e = entradas.setdefault(cid, {"nombre": None})
        e["gsc"] = g
        e["marca"] = D.marca_de(e.get("nombre") or cid, g.get("site", "").replace("sc-domain:", ""))

    clientes = []
    for cid, e in sorted(entradas.items()):
        r = D.diagnosticar_cliente(e, ahora_ms)
        for d in r["diagnosticos"]:
            d["cliente_id"] = cid
        clientes.append({"cliente_id": cid, "nombre": e.get("nombre"), **r})
    cuenta = {}
    for c in clientes:
        cuenta[c["veredicto_embudo"]["veredicto"]] = cuenta.get(c["veredicto_embudo"]["veredicto"], 0) + 1
    return {
        "_meta": {"generado": ahora.strftime("%Y-%m-%d %H:%M"), "que": "Diagnósticos de calidad: qué hay detrás de los números (leads, embudo, SEO).",
                  "catalogo": D.CATALOGO, "umbrales": {k: {"valor": v, "fuente": f} for k, (v, f) in D.UMBRALES.items()},
                  "fuentes_leidas": {k: Path(p).name for k, p in RUTAS.items() if Path(p).exists()},
                  "veredictos": cuenta,
                  "privacidad": "Sin nombres, correos ni teléfonos de leads: solo recuentos. Dinero en claves cpl*/coste* (las recorta servir.py)."},
        "clientes": clientes,
    }


def main():
    s = os.environ.get("RO_DIAG_AHORA")
    ahora = dt.datetime.fromisoformat(s).replace(tzinfo=MAD) if s else dt.datetime.now(MAD)
    salida = Path(sys.argv[sys.argv.index("--salida") + 1]) if "--salida" in sys.argv else APP / "data" / "diagnosticos" / "diagnosticos.json"
    doc = construir(ahora)
    salida.parent.mkdir(parents=True, exist_ok=True)
    tmp = salida.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=1))
    tmp.replace(salida)
    print(f"{len(doc['clientes'])} clientes · veredictos {doc['_meta']['veredictos']} → {salida}")


if __name__ == "__main__":
    main()

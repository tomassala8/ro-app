#!/usr/bin/env python3
"""
generar_mi_dia.py · M1 «Mi día» (2-oct-2026).

«Mi día» es un ORQUESTADOR: no recalcula nada que ya calcule otro módulo; en el navegador lee los datos que cada
módulo ya sirve (recortados por servir.py). Este script solo prepara las dos piezas que no son de ningún otro módulo:

  1. data/mi_dia/cambios.json  · «Lo que ha cambiado desde ayer» para Tomás (ficha G1, bloque 1), en líneas cortas
     y sin IA: compara la última foto diaria (historia/AAAA-MM-DD/cambios.json, foto_diaria.py) y, mientras solo
     haya una foto, lee lo que ya traen los módulos con fecha de ayer (captación, ventas de RO, decisiones, altas,
     fuentes, caja). Solo lo lee dirección (reglas_permisos.json → datos_de_modulo, «puestos»).
  2. data/mi_dia/ronda_mili.json · la ronda de Mili (rol_mili.json del panel v27), para su «Mi día».
     Solo la leen operaciones y dirección.

  3. data/mi_dia/p_<id>.json · el resumen de cada persona para abrir Mi día en un viaje (resumen_mi_dia.py, auditoría 37).

La configuración por puesto (qué bloques y en qué orden) NO sale de aquí: es data/mi_dia/config.json, a mano.

Solo lectura de data/, historia/ y del panel; escribe solo en data/mi_dia/. Sin correos, teléfonos, sueldos ni claves.
Uso: python3 fuentes_mi_dia/generar_mi_dia.py
"""
import json
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

AQUI = Path(__file__).resolve().parent.parent
DATA = AQUI / "data"
HISTORIA = AQUI / "historia"
SALIDA = DATA / "mi_dia"
ROL_MILI = Path.home() / "Downloads/PANEL_OPERACIONES_2026-10-01/build/rol_mili.json"


def leer(rel):
    p = DATA / f"{rel}.json"
    try:
        return json.loads(p.read_text())
    except Exception:
        return None


def miles(n, dec=0):
    if n is None:
        return "—"
    s = f"{n:,.{dec}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return s


def eur(n):
    return "—" if n is None else f"{miles(round(n))} €"


def ahora():
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def limpiar(t):
    t = re.sub(r"[\w.+-]+@[\w-]+(\.[\w-]+)+", "[correo]", str(t or ""))
    return re.sub(r"(?<![\d-])\+?\d[\d\s.]{7,}\d(?![\d-])", "[número]", t)


MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def dia_corto(iso):
    """'2026-10-01' → '1-oct'."""
    try:
        d = date.fromisoformat(str(iso)[:10])
        return f"{d.day}-{MESES[d.month - 1][:3]}"
    except Exception:
        return str(iso)


# ------------------------------------------------------------------ cambios
def lineas_foto():
    """Comparación con la foto anterior (foto_diaria.py). Devuelve (lineas, comparado_con)."""
    fotos = sorted(p for p in HISTORIA.iterdir() if p.is_dir() and not p.name.startswith(".")) if HISTORIA.exists() else []
    if not fotos:
        return [], None
    try:
        c = json.loads((fotos[-1] / "cambios.json").read_text())
    except Exception:
        return [], None
    if not c.get("comparado_con"):
        return [{"icono": "hist", "estado": "gris", "orden": 90, "fuente": "Fotos diarias",
                 "texto": f"Hoy es la primera foto diaria de la app ({dia_corto(fotos[-1].name)}): la comparación cliente a cliente (salud, semáforo, responsable) sale desde mañana.",
                 "ruta": "en-rojo"}], None
    out = []
    sem = [x for x in c.get("clientes", []) if x.get("campo") == "semaforo"]
    if sem:
        nombres = ", ".join(f"{x['nombre']} ({x.get('antes') or '—'} → {x.get('ahora') or '—'})" for x in sem[:4])
        out.append({"icono": "fire", "estado": "rojo" if any((x.get("ahora") or "").startswith(("rojo", "crít")) for x in sem) else "ambar",
                    "orden": 10, "fuente": "Fotos diarias", "texto": f"{len(sem)} cliente(s) cambian de semáforo: {nombres}.", "ruta": "en-rojo"})
    nuevas = [a for a in c.get("alarmas_nuevas", []) if a.get("gravedad") == "rojo"]
    cerradas = c.get("alarmas_cerradas", [])
    if nuevas or cerradas:
        out.append({"icono": "alert", "estado": "rojo" if nuevas else "verde", "orden": 15, "fuente": "Fotos diarias",
                    "texto": f"Alarmas: {len(nuevas)} rojas nuevas y {len(cerradas)} cerradas desde el {dia_corto(c['comparado_con'])}.", "ruta": "en-rojo"})
    resp = [x for x in c.get("clientes", []) if x.get("campo") == "responsable_id"]
    if resp:
        out.append({"icono": "persona", "estado": "gris", "orden": 60, "fuente": "Fotos diarias",
                    "texto": f"{len(resp)} cliente(s) cambian de responsable: {', '.join(x['nombre'] for x in resp[:4])}.", "ruta": "ajustes"})
    return out, c["comparado_con"]


def lineas_datos(hoy):
    """Lo que ya traen los módulos con fecha de ayer (sirve aunque solo haya una foto)."""
    out = []
    ayer = (hoy - timedelta(days=1)).isoformat()

    cap = leer("captacion/captacion")
    if cap:
        cl = [c for c in cap.get("clientes", []) if c.get("meta_activa")]
        l_ayer = sum((c.get("leads") or {}).get("ayer") or 0 for c in cl)
        l_7 = sum((c.get("leads") or {}).get("7d") or 0 for c in cl)
        media = l_7 / 7 if l_7 else 0
        delta = round((l_ayer - media) / media * 100) if media else None
        sin3 = []
        for c in cl:
            serie = c.get("serie") or []
            ult = serie[-3:]
            if len(ult) == 3 and sum(x.get("leads_meta") or 0 for x in ult) == 0 and sum(x.get("gasto_meta") or 0 for x in ult) > 0:
                sin3.append(c["nombre"])
        estado = "verde" if delta is not None and delta >= -10 else "ambar" if delta is not None and delta >= -30 else "rojo"
        txt = f"Leads de la cartera ayer ({dia_corto(cap.get('ventanas', {}).get('ayer', ayer))}): {miles(l_ayer)} frente a {miles(media, 1)} de media diaria en 7 días"
        txt += f" ({'+' if (delta or 0) >= 0 else ''}{delta} %)." if delta is not None else "."
        if sin3:
            txt += f" Sin leads 3 días con gasto: {', '.join(sin3[:4])}{'…' if len(sin3) > 4 else ''}."
        out.append({"icono": "target", "estado": estado if not sin3 else "rojo", "orden": 20, "fuente": "Meta + GoHighLevel",
                    "hora": cap.get("generado"), "texto": txt, "ruta": "captacion"})

    v = leer("ventas_ro/ventas_ro")
    if v:
        mes = hoy.strftime("%Y-%m")
        m = (v.get("meses") or {}).get(mes) or {}
        obj = v.get("objetivo_firmados_mes")
        if m:
            coste = (m.get("inversion") or 0) / m["firmados"] if m.get("firmados") else None
            out.append({"icono": "megafono", "estado": "verde" if m.get("firmados") else "gris", "orden": 30, "fuente": "GoHighLevel de RO",
                        "hora": v.get("generado"),
                        "texto": f"Ventas de RO en {MESES[hoy.month - 1]}: {m.get('firmados', 0)} firmados (objetivo {obj}), {m.get('citas', 0)} citas, {m.get('celebradas', 0)} celebradas, "
                                 f"{eur(m.get('inversion'))} de publicidad" + (f", {eur(coste)} por cliente." if coste else "."),
                        "ruta": "ventas-ro"})

    d = leer("decisiones/reloj")
    if d:
        decs = [x for x in d.get("decisiones", []) if not x.get("respuesta")]
        nuevas = [x for x in decs if (x.get("creada") or "") >= (hoy - timedelta(days=1)).isoformat()]
        vencidas = [x for x in decs if x.get("estado") not in ("en plazo",)]
        if decs:
            out.append({"icono": "flag", "estado": "rojo" if vencidas else "ambar", "orden": 5, "fuente": "Decisiones",
                        "hora": (d.get("_meta") or {}).get("generado"),
                        "texto": f"{len(decs)} decisiones te esperan ({len(nuevas)} nuevas desde ayer, {len(vencidas)} fuera de las 48 h): «{decs[0]['titulo']}».",
                        "ruta": "decisiones"})

    n = leer("nuevos/nuevos")
    if n:
        r = n.get("resumen", {})
        ver = {c["cliente_id"]: c for c in (leer("verdad/clientes") or {}).get("clientes", [])}
        # verdad única (E0 ronda 5): «fuera de plazo» = sin encender pasado el día 12
        fuera = [a["nombre"] for a in n.get("altas", []) if ((ver.get(a["cliente_id"]) or {}).get("encendido") or {}).get("estado") == "sin_encender_fuera_de_plazo"] if ver \
            else [a["nombre"] for a in n.get("altas", []) if (a.get("plazo") or {}).get("estado") == "rojo"]
        if r:
            out.append({"icono": "rocket", "estado": "rojo" if fuera else "verde", "orden": 25, "fuente": "Sign + ClickUp + Meta",
                        "hora": n.get("generado"),
                        "texto": f"Altas: {r.get('altas')} en curso; {len(fuera)} sin encender pasado el día 12 ({', '.join(fuera[:4])}{'…' if len(fuera) > 4 else ''}).",
                        "ruta": "clientes-nuevos", "dato": {"altas_fuera_de_plazo": len(fuera)}})

    f = leer("finanzas/finanzas")
    if f:
        a = f.get("admin", {})
        caja = a.get("caja") or {}
        dire = ((leer("finanzas/direccion") or {}).get("direccion") or f.get("direccion") or [{}])[0]
        cierre = (dire.get("caja") or {}).get("cierre_31ago")
        ct = a.get("cuota_tres") or {}
        out.append({"icono": "cartera", "estado": "ambar" if (dire.get("caja") or {}).get("meses", 9) < 2 else "verde", "orden": 40,
                    "fuente": "Holded", "hora": caja.get("fecha"),
                    "texto": f"Caja: {eur(caja.get('total_eur'))} en bancos" + (f" (31-ago: {eur(cierre)})" if cierre else "") +
                             f"; cuota cobrada {eur(ct.get('cobrada'))} de {eur(ct.get('facturada'))} facturada ({miles(ct.get('cobrado_pct') or 0)} %).",
                    "ruta": "finanzas"})

    fu = leer("fuentes")
    if fu:
        malas = [x for x in fu.get("fuentes", []) if x.get("estado") not in ("bien", "ok")]
        if malas:
            out.append({"icono": "plug", "estado": "ambar", "orden": 50, "fuente": "Salud de las fuentes",
                        "hora": fu.get("generado"),
                        "texto": f"{len(malas)} fuente(s) con aviso: " + ", ".join(f"{x.get('nombre', x.get('id'))} ({str(x.get('estado')).replace('_', ' ')})" for x in malas[:3]) + ".",
                        "ruta": "ajustes"})
    return out


def generar_cambios():
    hoy = date.today()
    foto, comparado = lineas_foto()
    lineas = sorted(foto + lineas_datos(hoy), key=lambda x: x["orden"])
    for x in lineas:
        x["texto"] = limpiar(x["texto"])
    return {"_meta": {"generado": ahora(), "hoy": hoy.isoformat(), "comparado_con": comparado,
                      "regla": "Sin IA: comparación de fotos diarias (foto_diaria.py) + datos de ayer que ya sirven los módulos. Máximo 5 líneas a la vista; el resto, plegado.",
                      "lee": "Solo dirección (reglas_permisos.json → datos_de_modulo «mi_dia/cambios»)."},
            "lineas": lineas}


# ------------------------------------------------------------------ ronda de Mili
def generar_ronda():
    try:
        r = json.loads(ROL_MILI.read_text())
    except Exception as e:
        return {"_meta": {"generado": ahora(), "error": f"No se pudo leer rol_mili.json: {e}"}, "principios": [], "items": []}
    items = [{"id": f"r{i}", "f": x.get("f"), "que": limpiar(x.get("que")), "donde": x.get("donde"), "prueba": limpiar(x.get("prueba")),
              "desde": x.get("desde")} for i, x in enumerate(r.get("items", []))]
    return {"_meta": {"generado": ahora(), "fuente": "Panel v27 · rol_mili.json (inventario de 68 exigencias de Tomás a Mili, 1-jul a 2-oct)",
                      "revision": (r.get("_meta") or {}).get("revision"),
                      "lee": "Solo operaciones y dirección."},
            "principios": [limpiar(p) for p in r.get("principios", [])], "items": items}


def main():
    SALIDA.mkdir(parents=True, exist_ok=True)
    c = generar_cambios()
    (SALIDA / "cambios.json").write_text(json.dumps(c, ensure_ascii=False, indent=1))
    r = generar_ronda()
    (SALIDA / "ronda_mili.json").write_text(json.dumps(r, ensure_ascii=False, indent=1))
    print(f"mi_dia: {len(c['lineas'])} líneas de cambios (comparado con {c['_meta']['comparado_con'] or 'nada: primera foto'}), "
          f"{len(r['items'])} puntos de la ronda de Mili → data/mi_dia/")
    # N10 (auditoría 37, causa 3): Mi día en un viaje → data/mi_dia/p_<id>.json (y puestos/<puesto>/p_<id>.json).
    # Va después de cambios y ronda (que entran en el resumen de Tomás y Mili). Si falla, Mi día pide los ficheros sueltos.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import resumen_mi_dia
    resumen_mi_dia.generar()


if __name__ == "__main__":
    sys.exit(main())

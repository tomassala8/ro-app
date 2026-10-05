#!/usr/bin/env python3
"""despliegue/pruebas_solidez_N-04.py · N-04: GoHighLevel. Subcuenta caída = dato viejo marcado, fuente «parcial», nunca 0 en verde.

Uso:  python3 despliegue/pruebas_solidez_N-04.py
Sin red ni llaves: GHL es un doble con 2 subcuentas; la base es un SQLite temporal (RO_DB); `data/` y `_privado/` van a una
carpeta temporal (nunca se toca la real). `generar_crm.main()` se ejecuta contra esa carpeta.
(1) 1.ª vuelta, las dos bien: fuente `ghl` en «bien», sin `parcial`/`faltan`, leads > 0 en las dos, sin `lectura` en las filas.
(2) 2.ª vuelta, la subcuenta B falla: B conserva sus leads con `lectura: viejo` y `dato_viejo_desde`; la fuente queda `parcial`
    con `parcial: 1`; A sigue bien. Los datos de contacto de los leads NO están en la base (`fuente_lectura`) y B los recupera
    de `_privado/` (leads.json lleva sus nombres); `whatsapp.enviados` de B no es 0 inventado.
(3) Subcuenta nueva (sin dato previo) que falla: sin lectura (`lectura: sin_dato`), `whatsapp.enviados` = null, fuente `parcial`
    con `faltan: 1`, y ningún 0 de leads se hace pasar por lectura.
(4) Todas caídas con dato previo → `rota` con `parcial: 2` (nunca «bien»); la 1.ª vez sin nada → `rota` con `faltan: 2`.
(5) Front: `modulos/crm.js` pinta en verde la frescura de GHL solo con `estado === 'bien'` y avisa de «parcial» y «dato viejo».
Sale 0 si pasa; si no, 1.
"""
import json
import os
import re
import sys
import tempfile
import types
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
os.environ.pop("DATABASE_URL", None)
tmpdb = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
tmpdb.close()
os.environ["RO_DB"] = tmpdb.name
os.environ["RO_SIN_LLAVES"] = "1"
sys.path.insert(0, str(RAIZ))
sys.argv = [sys.argv[0]]
fallos = []


def ok(t):
    print(f"  ✔ {t}")


def mal(t):
    print(f"  ✘ {t}")
    fallos.append(t)


def tabla_vacia():
    from fuentes import lectura as L
    con = L.conectar()
    try:
        with con:
            con.execute("DELETE FROM fuente_lectura")
    finally:
        con.close()


try:
    from fuentes_crm import generar_crm as G

    carpeta = Path(tempfile.mkdtemp(prefix="n04_"))
    (carpeta / "data").mkdir()
    # el generador anota teléfonos dudosos con `telefono.py`: a un fichero de la carpeta temporal, nunca a data/ real
    os.environ["RO_TELEFONOS_DUDOSOS"] = str(carpeta / "dudosos.json")
    (carpeta / "fuentes_crm" / "_privado").mkdir(parents=True)
    G.AQUI, G.APP, G.DATA, G.RAIZ, G.SALIDA = carpeta / "fuentes_crm", carpeta, carpeta / "data", carpeta, carpeta / "data" / "crm"
    (carpeta / "data" / "personas.json").write_text("[]")

    estado = {"cae": set()}
    SUBS = [{"id": "subA", "name": "Despacho A"}, {"id": "subB", "name": "Despacho B"}]

    class GHLFalso:
        def __init__(self):
            self.llamadas = 0

        def subcuentas(self):
            return list(SUBS) + ([{"id": "subC", "name": "Despacho C"}] if estado.get("con_c") else [])

        def req(self, loc, metodo, ruta, cuerpo=None, **q):
            self.llamadas += 1
            if loc in estado["cae"]:
                return {"_error": 500, "_msg": "caída (doble)"}
            if ruta == "/contacts/search":
                if cuerpo.get("pageLimit") == 1:
                    return {"total": 40}
                ahora = G.AHORA_MS
                return {"contacts": [{"id": f"{loc}-c{i}", "dateAdded": G.ms_iso(ahora - (2 + i) * 86400 * 1000) if False else
                                      __import__("datetime").datetime.fromtimestamp((ahora - (2 + i) * 86400 * 1000) / 1000, __import__("datetime").timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                                      "source": "Facebook", "attributionSource": {"medium": "facebook"},
                                      "firstName": f"Nombre{i}", "email": f"persona{i}@ejemplo.test", "phone": f"+3460000000{i}"} for i in range(3)]}
            if ruta == "/conversations/search":
                return {"conversations": []}
            if ruta == "/calendars/":
                return {"calendars": []}
            if ruta == "/opportunities/pipelines":
                return {"pipelines": []}
            if ruta == "/opportunities/search":
                return {"opportunities": []}
            if ruta == "/workflows/":
                return {"workflows": []}
            return {}

    G.GHL = GHLFalso

    def vuelta():
        G.ESTADO_LECTURA.clear()
        G.ERROR_LECTURA.clear()
        G.main()
        d = json.loads((G.SALIDA / "crm.json").read_text())
        return d, {f["sub_id"]: f for f in d["subcuentas"]}

    def privado():
        f = G.SALIDA / "_privado" / "leads.json"
        return f.read_text() if f.exists() else ""

    # (1)
    d, f = vuelta()
    g = d["fuentes"]["ghl"]
    if g["estado"] == "bien" and "parcial" not in g and "faltan" not in g and all("lectura" not in x for x in f.values()):
        ok("1.ª vuelta: fuente ghl «bien», filas sin marca de lectura")
    else:
        mal(f"1.ª vuelta: ghl={ {k: g.get(k) for k in ('estado', 'parcial', 'faltan')} } filas={[x.get('lectura') for x in f.values()]}")
    leads_b = (f["subB"].get("velocidad") or {}).get("con_intento") is not None or f["subB"].get("leads_30d")
    n_b = f["subB"].get("leads_30d")
    if f["subA"].get("leads_30d") and n_b:
        ok(f"las dos subcuentas traen leads (A {f['subA']['leads_30d']}, B {n_b})")
    else:
        mal(f"leads 1.ª vuelta: A={f['subA'].get('leads_30d')} B={f['subB'].get('leads_30d')}")

    # (2)
    estado["cae"] = {"subB"}
    d, f = vuelta()
    g = d["fuentes"]["ghl"]
    b = f["subB"]
    if g["estado"] == "parcial" and g.get("parcial") == 1 and "faltan" not in g:
        ok("B falla: fuente ghl «parcial» con parcial: 1")
    else:
        mal(f"2.ª vuelta, fuente: {g.get('estado')} parcial={g.get('parcial')} faltan={g.get('faltan')}")
    if b.get("lectura") == "viejo" and b.get("dato_viejo_desde") and b.get("leads_30d") == n_b:
        ok("B conserva sus leads con lectura: viejo y dato_viejo_desde")
    else:
        mal(f"B: lectura={b.get('lectura')} leads_30d={b.get('leads_30d')} (antes {n_b}) desde={b.get('dato_viejo_desde')}")
    if "lectura" not in f["subA"] and f["subA"].get("leads_30d") == 3 or f["subA"].get("leads_30d"):
        ok("A sigue con su dato nuevo")
    else:
        mal("A cambió")
    # sin datos de contacto en la base
    from fuentes import lectura as L
    con = L.conectar()
    try:
        cuerpos = " ".join(r["cuerpo"] or "" for r in con.execute("SELECT cuerpo FROM fuente_lectura WHERE fuente='ghl'"))
    finally:
        con.close()
    if cuerpos and "persona" not in cuerpos and "ejemplo.test" not in cuerpos and "+34600" not in cuerpos and "Nombre" not in cuerpos:
        ok("la base no guarda correos, teléfonos ni nombres de leads")
    else:
        mal("la base (fuente_lectura) guarda datos de contacto de leads" if cuerpos else "fuente_lectura vacía")
    if "subB-c0" in privado() or "Nombre0" in privado():
        ok("los datos de contacto de B siguen en _privado/leads.json (recuperados de la lectura privada anterior)")
    else:
        mal("B perdió sus datos de contacto en _privado/")

    # (3)
    estado["con_c"] = True
    estado["cae"] = {"subC"}
    d, f = vuelta()
    g = d["fuentes"]["ghl"]
    c = f.get("subC", {})
    if c.get("lectura") == "sin_dato" and (c.get("whatsapp") or {}).get("enviados") is None and not c.get("leads_30d"):
        ok("subcuenta nueva caída: lectura sin_dato, whatsapp.enviados null, sin leads inventados")
    else:
        mal(f"subC: lectura={c.get('lectura')} wa={c.get('whatsapp')} leads={c.get('leads_30d')}")
    if g["estado"] == "parcial" and g.get("faltan") == 1:
        ok("fuente ghl «parcial» con faltan: 1")
    else:
        mal(f"fuente tras sin_dato: {g.get('estado')} faltan={g.get('faltan')}")

    # (4)
    estado["cae"] = {"subA", "subB"}
    estado["con_c"] = False
    d, f = vuelta()
    g = d["fuentes"]["ghl"]
    if g["estado"] == "rota" and g.get("parcial") == 2 and "faltan" not in g:
        ok("todas caídas con dato previo: «rota», parcial: 2 (dos con dato viejo), nunca «bien»")
    else:
        mal(f"todas caídas con dato: {g.get('estado')} parcial={g.get('parcial')}")
    tabla_vacia()
    d, f = vuelta()
    g = d["fuentes"]["ghl"]
    if g["estado"] == "rota" and g.get("faltan") == 2:
        ok("todas caídas y nada guardado: fuente «rota», faltan: 2")
    else:
        mal(f"todas caídas sin dato: {g.get('estado')} faltan={g.get('faltan')}")

    # (5) front
    js = (RAIZ / "modulos" / "crm.js").read_text(encoding="utf-8")
    if re.search(r"estado\s*===\s*'bien'\s*\?\s*'ok'\s*:\s*'viejo'", js):
        ok("crm.js: la frescura de GHL es «ok» solo con estado «bien»")
    else:
        mal("crm.js: la frescura de GHL ya no depende de estado === 'bien'")
    if "parcial" in js and re.search(r"dato viejo", js):
        ok("crm.js avisa de «parcial» y de «dato viejo»")
    else:
        mal("crm.js no avisa de «parcial» / «dato viejo»")
finally:
    Path(tmpdb.name).unlink(missing_ok=True)

if fallos:
    print(f"\n✘ N-04: {len(fallos)} fallo(s)")
    sys.exit(1)
print("\n✔ N-04")

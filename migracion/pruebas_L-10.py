#!/usr/bin/env python3
"""migracion/pruebas_L-10.py · L-10: la ficha de un cliente se recorta por puesto (outreach no la recibe; producción solo la cabecera).

Uso: python3 migracion/pruebas_L-10.py --puerto 8771        (solo lectura; vale 8770, 8771 y 3000)
Para un cliente de SU cartera (`/api/sesion › datos.clientes` con `enCartera`):
  (1) outreach → `GET /api/cliente/<id>` 403;
  (2) producción sola → 403 o 200 solo con cabecera (hoy: 403);
  (3) administración → 200 con la cuota (`ficha_solo_contrato`);
  (4) account con un cliente ajeno → 403 y con uno suyo 200.
PENDIENTE (plan B, `--estricto` lo exige): con nivel «resumen», quien entra por redes/producción recibe hoy `servicios`, `equipo`,
`tickets_abiertos` y `revision48` además de la cabecera. Recortarlo cambia el contrato de `/api/cliente/<id>` para esos puestos y
el juez solo admite excepciones por ruta para TODAS las personas: va a NOTAS_NOCHE.md («Preguntas para Tomás»).
Una persona sin cartera o sin ese puesto se salta diciéndolo. Sale 0 si pasa. Sin datos reales en la salida.
"""
import argparse
import http.client
import json
import sys

ap = argparse.ArgumentParser()
ap.add_argument("--puerto", type=int, default=8771)
ap.add_argument("--estricto", action="store_true")
a = ap.parse_args()
fallos, saltadas, hechas, pendientes = [], [], [], []


def exige(c, t):
    if not c:
        fallos.append(t)


def pedir(ruta, yo):
    c = http.client.HTTPConnection("127.0.0.1", a.puerto, timeout=60)
    c.request("GET", ruta, headers={"X-RO-App": "1", "X-RO-Yo": yo, "Accept": "application/json"})
    r = c.getresponse()
    cuerpo = r.read()
    c.close()
    try:
        return r.status, json.loads(cuerpo or b"null")
    except ValueError:
        return r.status, None


def claves(o, acumulado=None):
    acumulado = set() if acumulado is None else acumulado
    if isinstance(o, dict):
        for k, v in o.items():
            acumulado.add(str(k))
            claves(v, acumulado)
    elif isinstance(o, list):
        for x in o:
            claves(x, acumulado)
    return acumulado


s, elegir = pedir("/api/elegir", "tomas")
personas = (elegir or {}).get("personas") or []


def con_cliente(puesto, otros_prohibidos=(), cualquiera=False):
    """(persona, cliente suyo, cartera) de una persona cuyo ÚNICO puesto es ese, con cartera propia."""
    for p in personas:
        pu = set(p.get("puestos") or [])
        if pu == {puesto} and p.get("estado", "activo") == "activo":
            s, ses = pedir("/api/sesion", p["id"])
            d = (ses or {}).get("datos") or {}
            cartera = set(d.get("carteraIds") or [])
            suyos = [c["id"] for c in d.get("clientes", []) if isinstance(c, dict) and c.get("id") and (cualquiera or c.get("id") in cartera)]
            if s == 200 and suyos and (puesto != "account" or d.get("soloSuCartera")):
                return p["id"], suyos[0], cartera
    return None, None, None


s, ses = pedir("/api/sesion", "tomas")
todos = [c["id"] for c in ((ses or {}).get("datos") or {}).get("clientes", []) if isinstance(c, dict) and c.get("id")]

p, cid, _ = con_cliente("outreach")
if p:
    s, _r = pedir(f"/api/cliente/{cid}", p)
    exige(s == 403, f"outreach recibe la ficha → {s} (debe ser 403)")
    hechas.append("outreach")
else:
    saltadas.append("outreach sin cartera")

p, cid, _ = con_cliente("produccion", cualquiera=True)
PROHIBIDAS = {"cuota", "cuota_fuente", "publicidad_30d", "equipo", "servicios", "tickets_abiertos", "revision48", "_privado"}
if p:
    s, r = pedir(f"/api/cliente/{cid}", p)
    exige(s in (200, 403), f"producción → {s}")
    if s == 200:
        sobran = sorted(PROHIBIDAS & claves(r))
        exige(not sobran, f"producción recibe más que la cabecera: {sobran}")
    hechas.append("produccion")
else:
    saltadas.append("producción sin clientes")

# PENDIENTE: nivel «resumen» por redes/producción
mixta = next((q["id"] for q in personas if set(q.get("puestos") or []) == {"produccion", "redes"} and q.get("estado", "activo") == "activo"), None)
if mixta:
    s, ses = pedir("/api/sesion", mixta)
    cl = [c["id"] for c in ((ses or {}).get("datos") or {}).get("clientes", []) if isinstance(c, dict) and c.get("id")]
    if cl:
        s, r = pedir(f"/api/cliente/{cl[0]}", mixta)
        if s == 200 and (r or {}).get("nivel") == "resumen":
            sobran = sorted(PROHIBIDAS & claves(r))
            if sobran:
                if a.estricto:
                    fallos.append(f"nivel «resumen» recibe más que la cabecera: {sobran}")
                else:
                    pendientes.append(f"nivel «resumen» (redes/producción) trae {sobran}")

p, cid, _ = con_cliente("administracion", cualquiera=True)
if p:
    s, r = pedir(f"/api/cliente/{cid}", p)
    exige(s == 200, f"administración → {s}")
    if s == 200:
        ks = claves(r)
        exige("cuota" in ks, "administración no recibe la cuota (ficha_solo_contrato)")
        exige("publicidad_30d" not in ks, "administración recibe la publicidad")
    hechas.append("administracion")
else:
    saltadas.append("administración sin cartera")

p, cid, cartera = con_cliente("account")
if p:
    ajeno = next((c for c in todos if c not in cartera), None)
    if ajeno:
        s, _r = pedir(f"/api/cliente/{ajeno}", p)
        exige(s == 403, f"account con un cliente ajeno → {s} (debe ser 403)")
        hechas.append("account")
    s, _r = pedir(f"/api/cliente/{cid}", p)
    exige(s == 200, f"account con un cliente suyo → {s}")
else:
    saltadas.append("account sin cartera")

exige(len(hechas) >= 3, f"pocas comprobaciones hechas: {hechas}")
print(("✔ " if not fallos else "✘ ") + "L-10: " + ((f"todo bien ({', '.join(hechas)})" + (f"; saltadas: {', '.join(saltadas)}" if saltadas else "") + (f"; PENDIENTE: {'; '.join(pendientes)}" if pendientes else "")) if not fallos else " · ".join(fallos)))
sys.exit(1 if fallos else 0)

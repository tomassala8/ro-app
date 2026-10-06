#!/usr/bin/env python3
"""migracion/pruebas_L-50.py · L-50: `GET /api/indicadores` en «ver como» no trae textos que no estén en ninguna de las
dos respuestas solas (la de la persona vista y la de quien mira).

Uso: python3 migracion/pruebas_L-50.py --puerto 8771        (legado; también --puerto 3000, la app nueva por el proxy)
Solo lectura: no escribe nada (cada lectura en «ver como» deja su fila de rastro, como siempre).
(1) Estática: en el bloque de `/api/indicadores` de servir.py, los importes a quitar salen de `P.ver(...)` (en «ver
    como», el mínimo de las dos personas), no de `P.puestos_de(persona)` (en «ver como», la intersección de puestos:
    dirección viendo como operaciones se quedaba sin puestos con dinero y le llegaban textos recortados que no ve nadie).
(2) En proceso, con los vectores (RO_VECTORES o ~/RO_MIGRACION/vectores): para cada persona activa vista por
    dirección, lo que se quita en «ver como» es exactamente la unión de lo que se quita a cada una sola. Se enseña
    también cuántas personas fallaban con la fórmula de antes (L-25 la cambió).
(3) Dinámica: para cada persona activa, cada hoja de la respuesta en «ver como» está en la de la persona sola o en la
    de dirección sola (mismo criterio que `permisos-regresion.e2e-spec.ts` 8.3, sin lista blanca).
Sale 0 si pasa. Sin datos reales en el código; solo se imprimen ids y recuentos.
"""
import argparse
import collections
import http.client
import json
import os
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

ap = argparse.ArgumentParser()
ap.add_argument("--puerto", type=int, default=8771)
ap.add_argument("--quien-mira", default="tomas")
a = ap.parse_args()

fallos = []


def exige(cond, texto):
    if not cond:
        fallos.append(texto)


# (1) estática
src = (RAIZ / "servir.py").read_text()
m = re.search(r'if ruta == "/api/indicadores":\n(.*?)\n        if ruta == ', src, re.S)
exige(m is not None, "(1) no se encuentra el bloque de /api/indicadores en servir.py")
if m:
    bloque = m.group(1)
    exige("importes_a_quitar(P.ver(persona" in bloque, "(1) importes_a_quitar no se alimenta de P.ver(persona, …)")
    exige(not re.search(r"pu\s*=\s*P\.puestos_de\(persona\)", bloque),
          "(1) los importes vuelven a decidirse por P.puestos_de (intersección en «ver como»)")
print(f"(1) estática: {'✔' if not fallos else '✘'}")

# (2) en proceso
import permisos as P  # noqa: E402

VEC = pathlib.Path(os.environ.get("RO_VECTORES", "~/RO_MIGRACION/vectores")).expanduser()
crudo = json.loads((VEC / "crudo.json").read_text())
real = next(p for p in crudo["personas"] if p["id"] == a.quien_mira)
activas = [p for p in crudo["personas"] if p.get("estado") == "activo" and p["id"] != real["id"]]


def quita_ahora(persona):
    cp = P.contexto(persona, crudo)
    ve_inv = P.ver(persona, {"tipo": "inversion"}, cp)["ok"] or any(
        P.ver(persona, {"tipo": "inversion", "cliente_id": cid}, cp)["ok"] for cid in cp["cartera_ids"])
    return set(P.importes_a_quitar(P.ver(persona, {"tipo": "cuota"}, cp)["ok"], ve_inv))


def quita_antes(persona):
    pu = P.puestos_de(persona)
    return set(P.importes_a_quitar(bool(pu & {"direccion", "operaciones", "proyectos", "administracion", "finanzas_direccion"}),
                                   bool(pu & {"direccion", "operaciones", "jefa_publicidad", "trafficker", "finanzas_direccion"})))


antes_mal = []
n2 = len(fallos)
q_real = quita_ahora(real)
for p in activas:
    solo = quita_ahora(p)
    with P.mirando_como(real, crudo):
        como = quita_ahora(p)
        como_antes = quita_antes(p)
    exige(como == solo | q_real, f"(2) {p['id']}: en «ver como» quita {sorted(como)}; sola {sorted(solo)}, quien mira {sorted(q_real)}")
    if como_antes != quita_antes(p) | quita_antes(real):
        antes_mal.append(p["id"])
print(f"(2) en proceso: {len(activas)} personas {'✔' if len(fallos) == n2 else '✘'}; "
      f"con la fórmula de antes de L-25 fallaban {len(antes_mal)}")


# (3) dinámica
def pedir(ruta, **cab):
    c = http.client.HTTPConnection("127.0.0.1", a.puerto, timeout=60)
    c.request("GET", ruta, headers={"X-RO-App": "1", "Accept": "application/json", **cab})
    r = c.getresponse()
    datos = r.read()
    c.close()
    try:
        return r.status, json.loads(datos or b"null")
    except ValueError:
        return r.status, None


def hojas(o, camino=()):
    if isinstance(o, dict):
        for k, v in o.items():
            yield from hojas(v, camino + (k,))
    elif isinstance(o, list):
        for v in o:
            yield from hojas(v, camino + ("#",))
    else:
        yield ".".join(camino) + "\0" + json.dumps(o, ensure_ascii=False, sort_keys=True)


n3 = len(fallos)
sc, C = pedir("/api/indicadores", **{"X-RO-Yo": real["id"]})
exige(sc == 200, f"(3) {real['id']} solo: {sc}")
enC = collections.Counter(hojas(C))
vistas = 0
for p in activas:
    sa, A = pedir("/api/indicadores", **{"X-RO-Yo": p["id"]})
    sb, B = pedir("/api/indicadores", **{"X-RO-Yo": real["id"], "X-RO-Como": p["id"]})
    if sb != 200:
        exige(sb in (401, 403), f"(3) {p['id']} «ver como»: {sb}")
        continue
    vistas += 1
    enA = collections.Counter(hojas(A)) if sa == 200 else collections.Counter()
    malas = sorted({k.split("\0")[0] for k, n in collections.Counter(hojas(B)).items() if n > enA[k] + enC[k]})
    exige(not malas, f"(3) {p['id']}: {len(malas)} hojas de «ver como» que no están en ninguna sola: {malas[:5]}")
print(f"(3) dinámica en {a.puerto}: {vistas} personas vistas {'✔' if len(fallos) == n3 else '✘'}")

if fallos:
    print("✘ L-50")
    for f in fallos:
        print("  ", f)
    sys.exit(1)
print("✔ L-50")

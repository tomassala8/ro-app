#!/usr/bin/env python3
"""
migracion/contrato.py · graba lo que responde la API de hoy (servir.py) y lo compara con la nueva (Nest).

Es la red de seguridad de la migración: si la API nueva responde LO MISMO a cada persona, en cada ruta,
con los mismos 403, el front viejo funciona igual encima de ella y los permisos no se han roto.

  # 1) con servir.py en marcha (puerto 8770), grabar la referencia:
  python3 migracion/contrato.py grabar --base http://127.0.0.1:8770 --salida ~/RO_MIGRACION/contrato/viejo

  # 2) con la API nueva en marcha (por ejemplo, Next en 3000 que pasa /api a Nest), grabar lo mismo:
  python3 migracion/contrato.py grabar --base http://127.0.0.1:3000 --salida ~/RO_MIGRACION/contrato/nuevo

  # 3) comparar (sale 0 si todo coincide; si no, lista cada diferencia y deja informe.md):
  python3 migracion/contrato.py comparar ~/RO_MIGRACION/contrato/viejo ~/RO_MIGRACION/contrato/nuevo

⚠️ Lo grabado lleva DATOS REALES (clientes, personas). Va SIEMPRE fuera del repositorio (por defecto
~/RO_MIGRACION/contrato). No lo subas nunca a git ni lo pegues en un chat.

Opciones de grabar:
  --personas tomas,mili,lucia   solo esas (por defecto: todas las activas que da /api/elegir)
  --ver-como                    además, Tomás «ver como» cada persona (solo lectura)
  --rapido                      no recorre /api/cliente/<id> de los 68 clientes para cada persona (solo 5)
Solo hace GET. No escribe nada en la app.
"""
import argparse
import hashlib
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
# Claves que cambian en cada llamada y no son parte del contrato.
VOLATILES = {"hora", "ahora", "generado", "generado_en_peticion", "ms", "_ms", "etag", "duracion_ms"}
# Rutas que cambian por el simple hecho de grabar (cada lectura deja rastro): de ellas solo se compara la FORMA
# (claves y tipos), no los valores. Graba siempre sobre una COPIA de la base recién restaurada.
SOLO_FORMA = {"/api/rastro", "/api/rastro/verificar", "/api/salud"}

# GET sin parámetros que toda persona puede pedir (el servidor decide 200/403). Si el inventario
# encuentra rutas nuevas, se añaden solas (ver rutas_get()).
GET_FIJAS = ["/api/sesion", "/api/indicadores", "/api/ajustes", "/api/rastro", "/api/acciones", "/api/recarga",
             "/api/avisos", "/api/decisiones", "/api/buscar/indice", "/api/contadores", "/api/perfil",
             "/api/preferencias", "/api/opiniones", "/api/respuestas_mili", "/api/rastro/verificar", "/api/salud"]


def rutas_get():
    inv = RAIZ / "migracion" / "inventario" / "rutas_api.json"
    rutas = list(GET_FIJAS)
    if inv.exists():
        for r in json.loads(inv.read_text()):
            if r["metodo"] == "GET" and not r.get("prefijo") and not r.get("patron") and r["ruta"].startswith("/api/") \
                    and r["ruta"] not in rutas and r["ruta"] not in ("/api/elegir", "/api/buscar", "/api/opiniones/captura"):
                rutas.append(r["ruta"])
    enchufes = RAIZ / "migracion" / "inventario" / "enchufes.json"
    if enchufes.exists():
        # Rutas de ia.py, avisos.py, envios.py…: solo las de leer. Las que hacen algo (verbos) no se tocan nunca.
        hacer = re.compile(r"(ejecutar|reintentar|responder|probar|enviar|alta|baja|cambio|cambiar|hecho|mensaje|leido|"
                           r"borrador|copiloto|valorar|reabrir|topes|a_mano|elegir|repartir|tarea_hecha|acceso|miembro|grupo|campana_vista|consejo|informe)$")
        for e in json.loads(enchufes.read_text()):
            for r in e["rutas"]:
                if not r.endswith("/") and not hacer.search(r) and r not in rutas:
                    rutas.append(r)
    return rutas


def datos_de_modulo():
    d = json.loads((RAIZ / "reglas_permisos.json").read_text())
    return sorted(k for k in d.get("datos_de_modulo", {}) if not k.startswith("_") and "*" not in k)


def pedir(base, ruta, yo=None, como=None):
    url = base.rstrip("/") + ruta
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    if yo:
        req.add_header("X-RO-Yo", yo)
        req.add_header("Cookie", f"ro_yo={yo}")
    if como:
        req.add_header("X-RO-Como", como)
        sep = "&" if "?" in url else "?"
        req.full_url = f"{url}{sep}como={como}"
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            cuerpo = r.read()
            estado = r.status
    except urllib.error.HTTPError as e:
        cuerpo, estado = e.read(), e.code
    except urllib.error.URLError as e:
        sys.exit(f"No responde {url}: {e.reason}. ¿Está el servidor en marcha?")
    try:
        datos = json.loads(cuerpo or b"null")
    except json.JSONDecodeError:
        datos = {"_no_json": hashlib.sha256(cuerpo).hexdigest()[:16], "_bytes": len(cuerpo)}
    return estado, datos


def limpiar(o):
    if isinstance(o, dict):
        return {k: limpiar(v) for k, v in sorted(o.items()) if k not in VOLATILES}
    if isinstance(o, list):
        return [limpiar(x) for x in o]
    return o


def nombre_fichero(ruta):
    return re.sub(r"[^\w\-]+", "_", ruta.strip("/")) + ".json"


def grabar(a):
    salida = Path(a.salida).expanduser()
    salida.mkdir(parents=True, exist_ok=True)
    estado, elegir = pedir(a.base, "/api/elegir")
    if estado != 200:
        sys.exit(f"/api/elegir respondió {estado}: arranca el servidor en local (sin Cloudflare Access).")
    personas = [p["id"] for p in elegir.get("personas", [])]
    if a.personas:
        personas = [p for p in a.personas.split(",") if p]
    rutas, ficheros = rutas_get(), datos_de_modulo()
    total = 0
    casos = [(p, None) for p in personas] + ([("tomas", p) for p in personas if p != "tomas"] if a.ver_como else [])
    for yo, como in casos:
        carpeta = salida / (f"{yo}__como__{como}" if como else yo)
        carpeta.mkdir(parents=True, exist_ok=True)
        indice = {}
        _, sesion = pedir(a.base, "/api/sesion", yo, como)
        clientes = [c["id"] for c in ((sesion or {}).get("datos") or {}).get("clientes", []) if isinstance(c, dict) and c.get("id")]
        if a.rapido:
            clientes = clientes[:5]
        objetivos = rutas + [f"/api/modulo/{f}" for f in ficheros] + [f"/api/cliente/{c}" for c in clientes]
        for ruta in objetivos:
            cod, datos = pedir(a.base, ruta, yo, como)
            indice[ruta] = cod
            if cod == 200:
                (carpeta / nombre_fichero(ruta)).write_text(json.dumps(limpiar(datos), ensure_ascii=False, sort_keys=True, indent=1))
            total += 1
        (carpeta / "_estados.json").write_text(json.dumps(indice, ensure_ascii=False, indent=1, sort_keys=True))
        print(f"  {carpeta.name}: {len(objetivos)} rutas ({sum(1 for v in indice.values() if v == 200)} con 200)")
    (salida / "_meta.json").write_text(json.dumps({"base": a.base, "personas": personas, "rutas": rutas,
                                                   "ficheros": ficheros, "peticiones": total}, ensure_ascii=False, indent=1))
    print(f"Grabadas {total} respuestas en {salida} (datos reales: no lo subas a git).")


def forma(o):
    if isinstance(o, dict):
        return {k: forma(v) for k, v in o.items()}
    if isinstance(o, list):
        return "lista"
    return type(o).__name__


def diferencias(a, b, ruta="", max_n=20):
    out = []
    if type(a) is not type(b):
        return [f"{ruta or '/'}: tipo {type(a).__name__} → {type(b).__name__}"]
    if isinstance(a, dict):
        for k in sorted(set(a) | set(b)):
            if k not in b:
                out.append(f"{ruta}/{k}: falta en la nueva")
            elif k not in a:
                out.append(f"{ruta}/{k}: sobra en la nueva")
            else:
                out += diferencias(a[k], b[k], f"{ruta}/{k}", max_n)
            if len(out) >= max_n:
                break
    elif isinstance(a, list):
        if len(a) != len(b):
            out.append(f"{ruta}: {len(a)} elementos → {len(b)}")
        for i, (x, y) in enumerate(zip(a, b)):
            out += diferencias(x, y, f"{ruta}[{i}]", max_n)
            if len(out) >= max_n:
                break
    elif a != b:
        out.append(f"{ruta}: {str(a)[:60]!r} → {str(b)[:60]!r}")
    return out[:max_n]


def comparar(a):
    viejo, nuevo = Path(a.viejo).expanduser(), Path(a.nuevo).expanduser()
    informe, fallos, ok = ["# Contrato de la API: viejo frente a nuevo", ""], 0, 0
    excepciones, aceptadas = {}, []
    fe = Path(a.excepciones).expanduser() if getattr(a, "excepciones", None) else None
    if fe and fe.exists():
        for linea in fe.read_text(encoding="utf-8").splitlines():
            ruta, _, motivo = linea.partition("#")
            if ruta.strip():
                excepciones[ruta.strip()] = motivo.strip()
    for cv in sorted(p for p in viejo.iterdir() if p.is_dir()):
        cn = nuevo / cv.name
        if not cn.exists():
            informe.append(f"## {cv.name}\n- no grabado en la nueva\n")
            fallos += 1
            continue
        ev, en = json.loads((cv / "_estados.json").read_text()), json.loads((cn / "_estados.json").read_text())
        lineas = []
        for ruta, cod in sorted(ev.items()):
            if ruta in excepciones and (en.get(ruta) != cod or cod == 200):
                aceptadas.append(f"- `{ruta}` ({cv.name}): {cod} → {en.get(ruta)} · {excepciones[ruta]}")
                continue
            if en.get(ruta) != cod:
                lineas.append(f"- `{ruta}`: estado {cod} → {en.get(ruta)}")
                continue
            if cod != 200:
                ok += 1
                continue
            f = nombre_fichero(ruta)
            dv, dn = json.loads((cv / f).read_text()), json.loads((cn / f).read_text())
            if ruta in SOLO_FORMA:
                dv, dn = forma(dv), forma(dn)
            d = diferencias(dv, dn)
            if d:
                lineas.append(f"- `{ruta}`:\n" + "\n".join(f"  - {x}" for x in d))
            else:
                ok += 1
        if lineas:
            fallos += len(lineas)
            informe += [f"## {cv.name}", ""] + lineas + [""]
    informe.insert(2, f"**{ok} respuestas iguales, {fallos} diferentes"
                      + (f", {len(aceptadas)} en excepciones conocidas (no cuentan)" if aceptadas else "") + ".**\n")
    if aceptadas:
        informe += ["## Excepciones conocidas (aceptadas por ahora, van al informe de la noche)", ""] + aceptadas[:200] + [""]
    (nuevo / "informe.md").write_text("\n".join(informe), encoding="utf-8")
    print("\n".join(informe[:80]))
    print(f"\nInforme completo: {nuevo / 'informe.md'}")
    sys.exit(1 if fallos else 0)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="orden", required=True)
    g = sub.add_parser("grabar")
    g.add_argument("--base", default="http://127.0.0.1:8770")
    g.add_argument("--salida", default="~/RO_MIGRACION/contrato/viejo")
    g.add_argument("--personas")
    g.add_argument("--ver-como", action="store_true")
    g.add_argument("--rapido", action="store_true")
    c = sub.add_parser("comparar")
    c.add_argument("viejo")
    c.add_argument("nuevo")
    c.add_argument("--excepciones", default=None,
                   help="fichero con una ruta por línea (y # motivo) cuya diferencia ya se conoce y se acepta por ahora "
                        "(p. ej. una función que en Postgres responde 503 a propósito). Se listan aparte y no cuentan.")
    a = ap.parse_args()
    grabar(a) if a.orden == "grabar" else comparar(a)


if __name__ == "__main__":
    main()

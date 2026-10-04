#!/usr/bin/env python3
"""
migracion/inventario.py · inventario automático de la app antes de migrarla a Next + Nest + Postgres.

Lee SOLO el código (nunca data/, local.db ni llaves) y escribe en migracion/inventario/:
  pantallas.json      las pantallas de modulos/indice.js (id, título, grupo, fichero, estado, quién las ve)
  modulos_js.json     cada fichero de modulos/ con líneas, imports y las llamadas a ctx que usa
  rutas_api.json      cada ruta GET/POST de servir.py con su línea
  tablas.sql          todos los CREATE TABLE / INDEX / TRIGGER / VIEW y los ALTER TABLE … ADD COLUMN (schema_v2.sql y los .py)
  tablas.json         lo mismo, por tabla: columnas y de qué fichero sale
  permisos.json       resumen de reglas_permisos.json (puestos, sillas, tipos, datos_de_modulo, almacenes, acciones)
  componentes.json    exportaciones de componentes.js
  ctx.json            campos de ctx (crearCtx en app.js)
  tuberia.json        pasos de despliegue/pasos.json y generadores fuentes_*/generar_*.py
  pruebas.json        baterías de prueba existentes
  huella.json         huella (sha256) de cada fichero de código, para saber qué cambió
  RESUMEN.md          todo en una pantalla, con las cifras

Uso:
  python3 migracion/inventario.py              # rehace el inventario
  python3 migracion/inventario.py --comparar   # además dice qué ha cambiado desde el inventario guardado en git

La idea: se corre ahora (3-oct) y se vuelve a correr la noche de la migración. --comparar enseña
las pantallas, rutas, tablas y reglas nuevas o cambiadas durante el día, para que Cursor no se deje nada.
"""
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SALIDA = RAIZ / "migracion" / "inventario"
NO_MIRAR = ("data/", "historia/", "capturas/", "migracion/", "v2/", "node_modules/", ".git/", "despliegue/estado/")


def ficheros_codigo():
    try:
        salida = subprocess.run(["git", "ls-files", "-co", "--exclude-standard"], cwd=RAIZ,
                                capture_output=True, text=True, check=True).stdout.split("\n")
    except Exception:
        salida = [str(p.relative_to(RAIZ)) for p in RAIZ.rglob("*") if p.is_file()]
    for f in sorted(set(salida)):
        if not f or f.startswith(NO_MIRAR) or "/_privado/" in f or "/_cache" in f:
            continue
        if f.endswith((".py", ".js", ".mjs", ".json", ".sql", ".css", ".html", ".md", ".sh", ".yml", ".yaml", ".txt")):
            yield f


def leer(rel):
    try:
        return (RAIZ / rel).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


# ------------------------------------------------------------------ pantallas (modulos/indice.js)
def pantallas():
    texto = leer("modulos/indice.js")
    filas = []
    for m in re.finditer(r"\{\s*id:\s*'([^']+)'(.*?)(?=\n\s*\{\s*id:|\n\];)", texto, re.S):
        cuerpo = m.group(2)

        def campo(nombre):
            c = re.search(rf"\b{nombre}:\s*'([^']*)'", cuerpo)
            return c.group(1) if c else None

        fase = re.search(r"\bfase:\s*(\d+)", cuerpo)
        quien = re.search(r"puestos_que_lo_ven:\s*(\{[^}]*\}|[A-Z_]+)", cuerpo)
        filas.append({
            "id": m.group(1), "num": campo("num"), "titulo": campo("titulo"), "grupo": campo("grupo"),
            "estado": campo("estado"), "fichero": campo("fichero"), "fase": int(fase.group(1)) if fase else None,
            "puestos_que_lo_ven": quien.group(1).strip() if quien else None, "resumen": campo("resumen"),
            "ruta": f"#/{m.group(1)}",
        })
    return filas


# ------------------------------------------------------------------ ficheros de modulos/
def modulos_js():
    filas = []
    for p in sorted((RAIZ / "modulos").glob("*.js")):
        t = p.read_text(encoding="utf-8")
        filas.append({
            "fichero": f"modulos/{p.name}",
            "lineas": t.count("\n") + 1,
            "es_pantalla": "export default" in t,
            "pieza_comun": p.name.startswith("_"),
            "imports": sorted(set(re.findall(r"from\s+['\"]([^'\"]+)['\"]", t))),
            "ctx_usa": sorted(set(re.findall(r"\bctx\.([a-zA-Z_]+)", t))),
            "api_rutas": sorted(set(re.findall(r"ctx\.api\(\s*[`'\"]([^`'\"?]+)", t))),
            "datos_modulo": sorted(set(re.findall(r"ctx\.datosModulo\(\s*[`'\"]([^`'\"]+)", t))),
            "acciones_tipo": sorted(set(re.findall(r"tipo:\s*'([a-z_]+)'", t))),
            "usa_localStorage": "localStorage" in t,
        })
    return filas


# ------------------------------------------------------------------ rutas de servir.py
def rutas_api():
    texto = leer("servir.py")
    lineas = texto.split("\n")
    metodo, filas, vistas = None, [], set()
    for n, l in enumerate(lineas, 1):
        if re.match(r"\s*def do_GET", l):
            metodo = "GET"
        elif re.match(r"\s*def do_POST", l):
            metodo = "POST"
        elif re.match(r"\s*def do_(PUT|DELETE|PATCH|HEAD|OPTIONS)", l):
            metodo = re.match(r"\s*def do_(\w+)", l).group(1)
        elif re.match(r"\s*def ", l) and not l.startswith("        "):
            pass
        if not metodo:
            continue
        for r in re.findall(r"[\"'](/api/[\w\-/]*|/vivo)[\"']", l):
            clave = (metodo, r)
            if clave in vistas:
                continue
            vistas.add(clave)
            filas.append({"metodo": metodo, "ruta": r, "linea": n, "prefijo": r.endswith("/")})
        for r in re.findall(r"re\.(?:match|compile)\(r?[\"'](\^?/api/[^\"']+)[\"']", l):
            clave = (metodo, r)
            if clave not in vistas:
                vistas.add(clave)
                filas.append({"metodo": metodo, "ruta": r, "linea": n, "patron": True})
    return filas


def enchufes():
    """Ficheros .py que añaden rutas a servir.py con «enganchar(Manejador, …)» (ia, avisos, envios, sincronia, vigia…):
    sus rutas /api/… y si arrancan un bucle propio (hilo) dentro del servidor, que en la app nueva será una tarea programada."""
    filas = []
    con_enchufe = sorted(str(f.relative_to(RAIZ)) for f in RAIZ.rglob("*.py")
                         if not str(f.relative_to(RAIZ)).startswith(NO_MIRAR) and "def enganchar(" in f.read_text(errors="ignore"))
    for fichero in con_enchufe:
        t = leer(fichero)
        filas.append({
            "fichero": fichero,
            "rutas": sorted(set(re.findall(r"[\"'](/api/[\w\-/]+)[\"']", t))),
            "subrutas": sorted(set(re.findall(r"(?:sub|resto|accion|op)\s*==\s*[\"']([\w\-/]+)[\"']", t))),
            "bucle_propio": bool(re.search(r"threading\.Thread\(", t)),
            "lineas": t.count("\n") + 1,
        })
    return filas


def rutas_front(mj):
    usadas = set()
    for m in mj:
        for r in m["api_rutas"]:
            usadas.add("/api/" + re.sub(r"\$\{[^}]*\}|<[^>]*>", ":x", r).rstrip("/"))
    return sorted(usadas)


# ------------------------------------------------------------------ tablas
PATRON_SQL = re.compile(r"CREATE\s+(?:UNIQUE\s+)?(TABLE|INDEX|TRIGGER|VIEW)\s+IF\s+NOT\s+EXISTS\s+(\w+)", re.I)
PATRON_ALTER = re.compile(r"ALTER\s+TABLE\s+(\w+)\s+ADD\s+COLUMN\s+(\{\w+\}|\w+)\s+(\w+)", re.I)


def _bloque_sql(texto, ini):
    """Desde CREATE hasta el ; que cierra (respetando paréntesis y BEGIN…END)."""
    prof, i, en_begin = 0, ini, False
    while i < len(texto):
        c = texto[i]
        if texto[i:i + 5].upper() == "BEGIN":
            en_begin = True
        if en_begin and texto[i:i + 4].upper() == "END;":
            return texto[ini:i + 4]
        if c == "(":
            prof += 1
        elif c == ")":
            prof -= 1
        elif c == ";" and prof <= 0 and not en_begin:
            return texto[ini:i + 1]
        elif c == '"' and prof <= 0 and not en_begin and texto[i - 1] != "\\" and i > ini + 30:
            # final de una cadena de Python que contenía el SQL sin ;
            return texto[ini:i].rstrip() + ";"
        i += 1
    return texto[ini:]


def tablas(ficheros):
    sql_total, por_tabla = [], {}
    for rel in ficheros:
        if not rel.endswith((".sql", ".py")):
            continue
        t = leer(rel)
        for m in PATRON_SQL.finditer(t):
            bloque = _bloque_sql(t, m.start())
            sql_total.append(f"-- {rel}\n{bloque}\n")
            if m.group(1).upper() == "TABLE":
                cols = []
                cuerpo = bloque[bloque.find("(") + 1: bloque.rfind(")")]
                trozos, prof, ini = [], 0, 0
                for i, c in enumerate(cuerpo):
                    prof += (c == "(") - (c == ")")
                    if c == "," and prof == 0:
                        trozos.append(cuerpo[ini:i]); ini = i + 1
                trozos.append(cuerpo[ini:])
                for linea in (re.sub(r"--[^\n]*", "", x).strip() for x in trozos):
                    c = re.match(r"\s*([a-z_][a-z0-9_]*)\s+(TEXT|INTEGER|REAL|BLOB|NUMERIC|BOOLEAN|TIMESTAMP\w*|JSONB?|BIGINT|SERIAL|BIGSERIAL|DOUBLE|BYTEA)", linea, re.I)
                    if c and c.group(1).upper() not in ("PRIMARY", "UNIQUE", "CHECK", "FOREIGN", "CONSTRAINT"):
                        cols.append({"columna": c.group(1), "tipo": c.group(2).upper()})
                por_tabla.setdefault(m.group(2), []).append({"fichero": rel, "linea": t[:m.start()].count("\n") + 1, "columnas": cols})
    # columnas añadidas al arrancar (ALTER TABLE … ADD COLUMN): CREATE IF NOT EXISTS no las trae y se perderían
    for rel in ficheros:
        if not rel.endswith((".sql", ".py")):
            continue
        t = leer(rel)
        for m in PATRON_ALTER.finditer(t):
            tabla, col, tipo = m.groups()
            nombres = [col]
            v = re.fullmatch(r"\{(\w+)\}", col)
            if v:   # f"… ADD COLUMN {col} TEXT" dentro de «for col in (…)»: se buscan los valores del bucle
                bucle = re.findall(rf"for\s+{v.group(1)}\s+in\s+\(([^)]*)\)", t[max(0, m.start() - 600):m.start()])
                nombres = re.findall(r"[\"']([a-z_][a-z0-9_]*)[\"']", bucle[-1]) if bucle else []
                if not nombres:
                    sql_total.append(f"-- {rel}\n-- ⚠ ALTER TABLE {tabla} con columna dinámica {col}: revisar a mano\n")
            for n in nombres:
                sql_total.append(f"-- {rel}\nALTER TABLE {tabla} ADD COLUMN IF NOT EXISTS {n} {tipo.upper()};\n")
                for d in por_tabla.get(tabla, []):
                    if not any(c["columna"] == n for c in d["columnas"]):
                        d["columnas"].append({"columna": n, "tipo": tipo.upper(), "añadida_con_alter": rel})
    return "\n".join(sql_total), por_tabla


# ------------------------------------------------------------------ permisos
def permisos():
    try:
        d = json.loads(leer("reglas_permisos.json"))
    except json.JSONDecodeError as e:
        return {"error": str(e)}
    limpio = lambda o: {k: v for k, v in o.items() if not k.startswith("_")} if isinstance(o, dict) else o
    return {
        "claves": [k for k in d if not k.startswith("_")],
        "puestos": [{k: p.get(k) for k in ("id", "nombre", "nivel", "ambito", "grupo")} for p in d.get("puestos", [])],
        "sillas": d.get("sillas"),
        "sillas_de_puesto": d.get("sillas_de_puesto"),
        "tipos": sorted(limpio(d.get("tipos", {}))),
        "datos_de_modulo": sorted(limpio(d.get("datos_de_modulo", {}))),
        "almacenes_privados": sorted(limpio(d.get("almacenes_privados", {}))),
        "acciones_permitidas": {k: v for k, v in limpio(d.get("acciones_permitidas", {})).items()},
        "rastro_navegador": d.get("rastro_navegador"),
        "rastro_solo_servidor": d.get("rastro_solo_servidor"),
        "puestos_solo_tomas": d.get("puestos_solo_tomas"),
        "cifras": {
            "puestos": len(d.get("puestos", [])),
            "tipos": len(limpio(d.get("tipos", {}))),
            "datos_de_modulo": len(limpio(d.get("datos_de_modulo", {}))),
            "almacenes_privados": len(limpio(d.get("almacenes_privados", {}))),
            "acciones": sum(len(v) for v in limpio(d.get("acciones_permitidas", {})).values() if isinstance(v, list)),
        },
    }


def componentes():
    t = leer("componentes.js")
    return [{"nombre": m.group(2), "clase": m.group(1), "linea": t[:m.start()].count("\n") + 1}
            for m in re.finditer(r"^export\s+(?:async\s+)?(function|const|let|class)\s+(\w+)", t, re.M)]


def campos_ctx():
    t = leer("app.js")
    i = t.find("function crearCtx")
    if i < 0:
        return []
    trozo = t[i:i + 12000]
    fin = trozo.find("\n}\n")
    trozo = trozo[:fin if fin > 0 else len(trozo)]
    return sorted(set(re.findall(r"^\s{4}([a-zA-Z_]+)\s*[:,(]", trozo, re.M)))


def tuberia():
    try:
        pasos = json.loads(leer("despliegue/pasos.json")).get("pasos", [])
    except json.JSONDecodeError:
        pasos = []
    generadores = sorted(str(p.relative_to(RAIZ)) for p in RAIZ.glob("fuentes_*/*.py"))
    externos = sorted(set(re.findall(r"RO_HERRAMIENTAS/([\w./-]+)", "\n".join(leer(g) for g in generadores + ["config.py"]))))
    return {
        "pasos": [{k: p.get(k) for k in ("id", "orden", "cmd", "comando", "modo", "modos", "horario", "depende")
                   if p.get(k) is not None} for p in pasos],
        "generadores": generadores,
        "fuera_del_repo_RO_HERRAMIENTAS": externos,
        "tareas_python_raiz": [f for f in ("avisos.py", "avisos_programados.py", "envios.py", "sincronia.py", "ia.py",
                                           "ia_gasto.py", "altas_personas.py", "foto_diaria.py", "build_data.py",
                                           "generar_catalogo.py", "telefono.py") if (RAIZ / f).exists()],
    }


def pruebas():
    return [{"fichero": f, "lineas": leer(f).count("\n") + 1, "doc": (re.search(r'"""\s*\n?(.*?)\n', leer(f), re.S) or [None, ""])[1].strip()}
            for f in sorted(set([str(p.relative_to(RAIZ)) for p in RAIZ.glob("pruebas*.py")] +
                                [str(p.relative_to(RAIZ)) for p in RAIZ.glob("*/pruebas*.py")] +
                                [str(p.relative_to(RAIZ)) for p in RAIZ.glob("*/probar*.py")]))]


def huella(ficheros):
    return {f: hashlib.sha256((RAIZ / f).read_bytes()).hexdigest()[:16] for f in ficheros if (RAIZ / f).is_file()}


# ------------------------------------------------------------------ comparar con lo guardado en git
def anterior(nombre):
    try:
        return json.loads(subprocess.run(["git", "show", f"HEAD:migracion/inventario/{nombre}"], cwd=RAIZ,
                                         capture_output=True, text=True, check=True).stdout)
    except Exception:
        return None


def comparar(actual):
    lineas = ["# Cambios desde el inventario guardado en git", ""]

    def dif(nombre, clave, etiqueta):
        antes = anterior(nombre)
        if antes is None:
            lineas.append(f"- {etiqueta}: no había inventario anterior.")
            return
        a = {clave(x) for x in (antes if isinstance(antes, list) else antes)}
        b = {clave(x) for x in (actual[nombre] if isinstance(actual[nombre], list) else actual[nombre])}
        nuevos, quitados = sorted(b - a), sorted(a - b)
        lineas.append(f"- **{etiqueta}:** {len(nuevos)} nuevas, {len(quitados)} quitadas")
        lineas += [f"  - nueva: `{x}`" for x in nuevos] + [f"  - quitada: `{x}`" for x in quitados]

    dif("pantallas.json", lambda x: x["id"], "Pantallas")
    dif("rutas_api.json", lambda x: f'{x["metodo"]} {x["ruta"]}', "Rutas de API")
    dif("tablas.json", lambda x: x, "Tablas")
    dif("componentes.json", lambda x: x["nombre"], "Componentes")
    antes = anterior("huella.json") or {}
    ahora = actual["huella.json"]
    cambiados = sorted(f for f in ahora if f in antes and antes[f] != ahora[f])
    nuevos = sorted(f for f in ahora if f not in antes)
    lineas.append(f"- **Ficheros de código:** {len(cambiados)} cambiados, {len(nuevos)} nuevos, "
                  f"{len([f for f in antes if f not in ahora])} desaparecidos")
    lineas += [f"  - cambiado: `{f}`" for f in cambiados] + [f"  - nuevo: `{f}`" for f in nuevos]
    pa, pb = anterior("permisos.json") or {}, actual["permisos.json"]
    for k in ("datos_de_modulo", "almacenes_privados", "tipos"):
        a, b = set(pa.get(k, [])), set(pb.get(k, []))
        if a != b:
            lineas.append(f"- **Permisos · {k}:** +{sorted(b - a)} −{sorted(a - b)}")
    return "\n".join(lineas) + "\n"


def main():
    SALIDA.mkdir(parents=True, exist_ok=True)
    fich = list(ficheros_codigo())
    sql, por_tabla = tablas(fich)
    mj = modulos_js()
    datos = {
        "pantallas.json": pantallas(),
        "modulos_js.json": mj,
        "rutas_front.json": rutas_front(mj),
        "rutas_api.json": rutas_api(),
        "enchufes.json": enchufes(),
        "tablas.json": por_tabla,
        "permisos.json": permisos(),
        "componentes.json": componentes(),
        "ctx.json": campos_ctx(),
        "tuberia.json": tuberia(),
        "pruebas.json": pruebas(),
        "huella.json": huella(fich),
    }
    for nombre, valor in datos.items():
        (SALIDA / nombre).write_text(json.dumps(valor, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (SALIDA / "tablas.sql").write_text(sql, encoding="utf-8")

    p, mj = datos["pantallas.json"], datos["modulos_js.json"]
    lineas_front = sum(m["lineas"] for m in mj) + sum(leer(f).count("\n") for f in ("app.js", "componentes.js", "datos.js", "permisos.js", "ayudas.js", "carcasa.js", "estilos.css", "index.html"))
    cif = datos["permisos.json"].get("cifras", {})
    rutas = datos["rutas_api.json"]
    resumen = [
        "# Inventario de la app de RO (generado)", "",
        "Lo genera `python3 migracion/inventario.py`. No edites a mano: vuelve a generarlo.", "",
        "| Qué | Cuántos |", "|---|---|",
        f"| Pantallas en el menú (`modulos/indice.js`) | {len(p)} ({sum(1 for x in p if x['estado'] == 'hecho')} hechas) |",
        f"| Ficheros en `modulos/` | {len(mj)} ({sum(1 for m in mj if m['es_pantalla'])} pantallas, {sum(1 for m in mj if m['pieza_comun'])} piezas comunes) |",
        f"| Líneas de front (módulos + carcasa + estilos) | {lineas_front} |",
        f"| Rutas de API en `servir.py` | {len(rutas)} ({sum(1 for r in rutas if r['metodo'] == 'GET')} GET, {sum(1 for r in rutas if r['metodo'] == 'POST')} POST) |",
        f"| Ficheros que enchufan rutas a servir.py | {len(datos['enchufes.json'])} ({sum(len(e['rutas']) for e in datos['enchufes.json'])} rutas más; {sum(1 for e in datos['enchufes.json'] if e['bucle_propio'])} con bucle propio) |",
        f"| Rutas distintas que llama el front (`ctx.api`) | {len(datos['rutas_front.json'])} |",
        f"| Tablas | {len(por_tabla)} |",
        f"| Puestos | {cif.get('puestos')} |",
        f"| Tipos de dato con regla | {cif.get('tipos')} |",
        f"| Ficheros de datos con permiso (`datos_de_modulo`) | {cif.get('datos_de_modulo')} |",
        f"| Almacenes privados | {cif.get('almacenes_privados')} |",
        f"| Tipos de acción permitidos | {cif.get('acciones')} |",
        f"| Componentes exportados (`componentes.js`) | {len(datos['componentes.json'])} |",
        f"| Campos de `ctx` | {len(datos['ctx.json'])} |",
        f"| Pasos de la tubería | {len(datos['tuberia.json']['pasos'])} |",
        f"| Generadores `fuentes_*/` | {len(datos['tuberia.json']['generadores'])} |",
        f"| Baterías de prueba | {len(datos['pruebas.json'])} |",
        "", "## Pantallas", "", "| Ruta | Título | Grupo | Fichero | Estado |", "|---|---|---|---|---|",
    ] + [f"| `{x['ruta']}` | {x['titulo']} | {x['grupo']} | `{x['fichero']}` | {x['estado']} |" for x in p] + [
        "", "## Rutas de API", "", "| Método | Ruta | Línea en servir.py |", "|---|---|---|",
    ] + [f"| {r['metodo']} | `{r['ruta']}` | {r['linea']} |" for r in rutas] + [
        "", "## Rutas enchufadas desde otros ficheros", "", "| Fichero | Rutas | ¿Bucle propio? |", "|---|---|---|",
    ] + [f"| `{e['fichero']}` | {', '.join(f'`{r}`' for r in e['rutas'])} | {'sí' if e['bucle_propio'] else 'no'} |" for e in datos["enchufes.json"]] + [
        "", "## Rutas que llama el front", "", ", ".join(f"`{r}`" for r in datos["rutas_front.json"]),
        "", "## Tablas", "",
    ] + [f"- `{t}` ({', '.join(sorted({o['fichero'] for o in v}))})" for t, v in sorted(por_tabla.items())] + [
        "", "## Campos de ctx", "", ", ".join(f"`{c}`" for c in datos["ctx.json"]), "",
        "## Dependencias fuera del repositorio (`~/RO_HERRAMIENTAS`)", "",
    ] + [f"- `{x}`" for x in datos["tuberia.json"]["fuera_del_repo_RO_HERRAMIENTAS"]]
    (SALIDA / "RESUMEN.md").write_text("\n".join(resumen) + "\n", encoding="utf-8")

    print(f"Inventario en {SALIDA.relative_to(RAIZ)}/: {len(p)} pantallas, {len(rutas)} rutas, {len(por_tabla)} tablas, "
          f"{cif.get('datos_de_modulo')} ficheros de datos con permiso, {len(datos['componentes.json'])} componentes.")
    if "--comparar" in sys.argv:
        texto = comparar(datos)
        (SALIDA / "CAMBIOS.md").write_text(texto, encoding="utf-8")
        print(texto)


if __name__ == "__main__":
    main()

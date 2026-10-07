#!/usr/bin/env python3
"""
probar_alertas.py · pruebas y capturas de «Alertas del departamento» (carril N4).

  Servidor: uno PROPIO para toda la prueba, con una COPIA de local.db (RO_DB) y solo en 127.0.0.1 (--bind), en un
  puerto libre de RO_PUERTOS_PRUEBA (por defecto 9155-9159). Nunca el servidor de otra sesión ni la base real.
  A · Pantalla: entra como 8 personas (?yo=) a 1440 y 390 px: sin errores de consola, sin desplazamiento horizontal,
      tarjetas pintadas (article[data-alerta] de alertas.js) o su vacío; capturas en capturas/alertas/.
  B · Permisos por la API: cada uno recibe solo su fichero; nadie lee el de otro ni alertas.json (salvo Mili y Tomás);
      sin dinero para quien no lo ve; sin datos de leads; cada alerta visible es suya, de su departamento o de dirección.
      La setter no ve ni Alertas ni Mi día: su fichero da 403 (correcto desde R16; antes llegaba vacío con 200).
  C · Estados y escalado: sobre la misma copia de la base: Lucía pulsa «Lo tengo», «Resuelta»
      y «No aplica» (con motivo); «ver como» no escribe; se regenera en una carpeta temporal simulando 3 días después:
      «Lo tengo» para el escalado, «Resuelta» se reabre (el dato sigue) y una sin tocar sube a Mili.
  D · Coherencia: las cifras de alertas = las de cada módulo (alertas.json → coherencia).

Uso: python3 fuentes_alertas/probar_alertas.py [--sin-capturas]
"""
import json
import os
import socket
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

AQUI = Path(__file__).resolve().parent.parent


def _libre():
    """Un puerto libre de RO_PUERTOS_PRUEBA (por defecto 9155-9159), siempre en 127.0.0.1."""
    ini, fin = (int(x) for x in os.environ.get("RO_PUERTOS_PRUEBA", "9155-9159").split("-"))
    for puerto in range(ini, fin + 1):
        with socket.socket() as so:
            try:
                so.bind(("127.0.0.1", puerto))
                return puerto
            except OSError:
                continue
    sys.exit(f"✗ No hay ningún puerto libre entre {ini} y {fin}.")


PUERTO = None          # lo pone servidor_propio()
TARJETA = "article[data-alerta]"          # la tarjeta de alertas.js (antes «.al-card», que ya no existe)
CAPT = AQUI / "capturas" / "alertas"
PERSONAS = ["tomas", "mili", "lucia", "valeria", "yessica", "constanza", "setter_ana", "cecilia"]
FALLOS = []


def ok(cond, texto):
    print(("  ✓ " if cond else "  ✗ ") + texto)
    if not cond:
        FALLOS.append(texto)


def get(puerto, ruta, yo):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{puerto}/api/{ruta}{'&' if '?' in ruta else '?'}yo={yo}") as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def post(puerto, ruta, yo, cuerpo, como=None):
    q = f"?yo={yo}" + (f"&como={como}" if como else "")
    req = urllib.request.Request(f"http://127.0.0.1:{puerto}/api/{ruta}{q}", data=json.dumps(cuerpo).encode(),
                                 headers={"Content-Type": "application/json", "X-RO-App": "1", "Origin": f"http://127.0.0.1:{puerto}"}, method="POST")
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


# ------------------------------------------------------------------ A · pantalla
def pantalla():
    print("A · pantalla (8 personas, 1440 y 390 px)")
    CAPT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        for p in PERSONAS:
            for ancho in (1440, 390):
                pg = b.new_page(viewport={"width": ancho, "height": 900})
                errs = []
                pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
                pg.on("pageerror", lambda e: errs.append(str(e)))
                pg.goto(f"http://127.0.0.1:{PUERTO}/?yo={p}#/alertas")
                pg.wait_for_timeout(2200)
                ancho_doc = pg.evaluate("document.documentElement.scrollWidth")
                n = pg.evaluate(f"document.querySelectorAll({TARJETA!r}).length")
                vacio = pg.evaluate("document.querySelectorAll('.vacio-g').length")
                ok(not errs, f"{p} {ancho}: sin errores de consola {errs[:2] if errs else ''}")
                ok(ancho_doc <= ancho, f"{p} {ancho}: sin desplazamiento horizontal ({ancho_doc})")
                if p == "setter_ana":
                    ok(n == 0 and pg.get_by_text("no es de tu puesto").count() > 0, f"{p}: no ve la pantalla (no es de su puesto)")
                else:
                    ok(n > 0 or vacio > 0, f"{p} {ancho}: {n} tarjetas pintadas")
                if "--sin-capturas" not in sys.argv:
                    pg.screenshot(path=str(CAPT / f"{p}_{ancho}.png"), full_page=(ancho == 390 and p in ("lucia", "cecilia")) or ancho == 1440 and p in ("tomas",))
                pg.close()
        # pestañas de Tomás (departamentos, resumen, reglas, comprobación)
        if "--sin-capturas" not in sys.argv:
            pg = b.new_page(viewport={"width": 1440, "height": 1000})
            pg.goto(f"http://127.0.0.1:{PUERTO}/?yo=tomas#/alertas")
            pg.wait_for_timeout(2000)
            for nombre, texto in (("departamentos", "Por departamento"), ("resumen", "Resumen del día"), ("reglas", "Reglas y plazos"), ("comprobacion", "Comprobación")):
                pg.get_by_role("tab", name=re.compile(texto)).click()
                pg.wait_for_timeout(500)
                pg.locator(".pestanas-caja").screenshot(path=str(CAPT / f"tomas_pestana_{nombre}_1440.png"))
            pg.get_by_role("tab", name=re.compile("Alertas")).click()
            pg.close()
        b.close()


# ------------------------------------------------------------------ B · permisos
def permisos():
    print("B · permisos por la API")
    import permisos as P
    personas = {p["id"]: p for p in json.loads((AQUI / "data/personas.json").read_text())}
    asig = json.loads((AQUI / "data/asignaciones.json").read_text())
    jefes = {"jeronimo": {"web", "seo"}, "yessica": {"crm"}, "valeria": {"publicidad"}, "constanza": {"redes"}, "mili": {"accounts", "altas"}, "tomas": {"administracion", "rrhh", "direccion"}}
    rx_tel = re.compile(r"(?<![\d-])\+?\d[\d\s.]{8,}\d(?![\d-])")
    rx_correo = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
    for p in PERSONAS:
        st, d = get(PUERTO, f"modulo/alertas/p_{p}", p)
        if p == "setter_ana":
            ok(st == 403 and not d.get("alertas"), f"setter_ana: su fichero da 403 (no ve ni Alertas ni Mi día) ({st})")
            continue
        ok(st == 200, f"{p}: recibe su fichero ({len(d.get('alertas', []))} alertas, alcance «{d.get('alcance')}»)")
        otro = "tomas" if p != "tomas" else "lucia"
        st2, _ = get(PUERTO, f"modulo/alertas/p_{otro}", p)
        ok(st2 == 403, f"{p}: no puede leer el fichero de {otro} (403)")
        st3, _ = get(PUERTO, "modulo/alertas/alertas", p)
        ok((st3 == 200) == (p in ("tomas", "mili")), f"{p}: alertas.json completo {'sí' if st3 == 200 else 'no'} (solo Mili y Tomás)")
        per = personas[p]
        cp = P.contexto(per, {"asignaciones": asig, "personas": list(personas.values()),
                             "clientes": json.loads((AQUI / "data/clientes.json").read_text())})
        todo = bool(set(per["puestos"]) & {"direccion", "operaciones"})
        malas = [a["id"] for a in d["alertas"] if not (todo or a["dueno_id"] == p or a.get("responsable_ahora") == p or a["departamento"] in jefes.get(p, set())
                                                      or (a["departamento"] == "rrhh" and "rrhh" in per["puestos"]))]
        ok(not malas, f"{p}: todas sus alertas son suyas, de su departamento o de dirección ({len(malas)} fuera)")
        ve_cobros = P.ver(per, {"tipo": "cobros"}, cp)["ok"]
        con_imp = sum(1 for a in d["alertas"] if "impagado_eur" in a)
        ok(ve_cobros or con_imp == 0, f"{p}: sin importes de cobros si no los ve ({con_imp})")
        sin_inv = [a for a in d["alertas"] if "gasto_7d" in a and not P.ver(per, {"tipo": "inversion", "cliente_id": a.get("cliente_id")}, cp)["ok"]]
        ok(not sin_inv, f"{p}: gasto de publicidad solo de clientes cuya inversión ve")
        texto = json.dumps(d["alertas"], ensure_ascii=False)
        sin_url = re.sub(r'https?://[^"\s]+', '', texto)          # los ids de ClickUp y Desk en enlaces no son teléfonos
        ok(not rx_correo.search(sin_url) and not rx_tel.search(sin_url), f"{p}: ni correos ni teléfonos en sus alertas")
        ok(not any(k in texto for k in ('"nombre_lead"', '"telefono"', '"correo_lead"', "/contacts/detail/")), f"{p}: ningún dato ni enlace de un lead concreto")
        if not ve_cobros:
            # Un umbral de inversión («100 € o más gastados en Meta») sí puede salir a quien ve la inversión de ese cliente;
            # lo que no puede salir es un importe de cobros (finanzas, dinero) ni euros de un cliente cuya inversión no ve.
            con_eur = [a for a in d["alertas"] if "€" in json.dumps(a, ensure_ascii=False)
                       and (a.get("modulo_origen") in ("finanzas", "dinero")
                            or not P.ver(per, {"tipo": "inversion", "cliente_id": a.get("cliente_id")}, cp)["ok"])]
            ok(not con_eur, f"{p}: ningún importe en euros que no pueda ver ({[a['id'] for a in con_eur][:3]})")


# ------------------------------------------------------------------ C · estados y escalado
def servidor_propio(tmp):
    """servir.py sobre una COPIA de local.db, solo en 127.0.0.1, en un puerto libre de 9155-9159."""
    global PUERTO
    PUERTO = _libre()
    shutil.copy(AQUI / "local.db", tmp / "prueba.db")
    (tmp / "recarga.json").write_text(json.dumps({"pasos": []}))
    env = {**os.environ, "RO_DB": str(tmp / "prueba.db"), "RO_RECARGA_CONFIG": str(tmp / "recarga.json")}
    srv = subprocess.Popen([sys.executable, str(AQUI / "servir.py"), "--bind", "127.0.0.1", "--puerto", str(PUERTO)], cwd=AQUI, env=env,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(120):
        time.sleep(0.5)
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{PUERTO}/", timeout=1)
            break
        except urllib.error.HTTPError:
            break
        except Exception:
            if srv.poll() is not None:
                sys.exit(f"✗ servir.py no arrancó en {PUERTO}")
            continue
    print(f"Servidor propio en 127.0.0.1:{PUERTO} con una copia de local.db")
    return srv, env


def estados(tmp, env):
    print("C · estados y escalado (servidor propio con copia de la base)")
    if True:
        _, d = get(PUERTO, "modulo/alertas/p_lucia", "lucia")
        mias = [a for a in d["alertas"] if a["dueno_id"] == "lucia" and a["estado"] == "nueva"]
        a1, a2, a3 = mias[0], mias[1], mias[2]
        a4 = next(a for a in mias[3:] if (a.get("plazo_h") or 99) <= 24)
        base = {"herramienta": "app", "modulo": "alertas"}
        st, _ = post(PUERTO, "acciones", "lucia", {**base, "tipo": "alerta_lo_tengo", "objeto": a1["id"], "cliente_id": a1.get("cliente_id"), "texto": "Lo tengo"})
        ok(st == 200, "Lucía: «Lo tengo» entra en la cola simulada")
        st, _ = post(PUERTO, "acciones", "lucia", {**base, "tipo": "alerta_resuelta", "objeto": a2["id"], "cliente_id": a2.get("cliente_id"), "texto": "Resuelta"})
        ok(st == 200, "Lucía: «Resuelta» entra en la cola")
        st, _ = post(PUERTO, "acciones", "lucia", {**base, "tipo": "alerta_no_aplica", "objeto": a3["id"], "cliente_id": a3.get("cliente_id"), "texto": "No aplica: el cliente contestó por WhatsApp"})
        ok(st == 200, "Lucía: «No aplica» con motivo entra en la cola")
        st, _ = post(PUERTO, "acciones", "lucia", {**base, "tipo": "borrar_todo", "objeto": a1["id"], "texto": "x"})
        ok(st == 400, "Un tipo de acción fuera de la lista blanca se rechaza (400)")
        st, _ = post(PUERTO, "acciones", "tomas", {**base, "tipo": "alerta_vista", "objeto": a1["id"], "cliente_id": a1.get("cliente_id"), "texto": "x"}, como="lucia")
        ok(st == 403, "«Ver como» (Tomás como Lucía) no escribe (403)")
        _, acc = get(PUERTO, "acciones?modulo=alertas", "lucia")
        ok(len([x for x in acc.get("acciones", []) if x["objeto"] in (a1["id"], a2["id"], a3["id"])]) >= 3, "Las tres marcas se leen de vuelta (rastro)")
        _, r = get(PUERTO, "rastro", "lucia")
        ok(any(x.get("accion") == "accion_simulada" and x.get("clave") == a1["id"] for x in r.get("registro", [])), "Cada marca queda en el rastro imborrable")
        # regenerar en una carpeta temporal 3 días después
        sal = tmp / "salida"
        shutil.copy(AQUI / "fuentes_alertas/estado_alertas.json", tmp / "estado.json")
        subprocess.run([sys.executable, str(AQUI / "fuentes_alertas/generar_alertas.py")], cwd=AQUI, check=True, stdout=subprocess.DEVNULL,
                       env={**env, "RO_ALERTAS_SALIDA": str(sal), "RO_ALERTAS_ESTADO": str(tmp / "estado.json"), "RO_ALERTAS_AHORA": "2026-10-05 20:00"})
        x = {a["id"]: a for a in json.loads((sal / "alertas.json").read_text())["alertas"]}
        ok(x[a1["id"]]["estado"] == "lo_tengo" and x[a1["id"]]["escalado"]["nivel"] == 0, "«Lo tengo» para el escalado aunque pase el plazo")
        ok(x[a2["id"]]["estado"] == "reabierta", "«Resuelta» se comprueba con el dato siguiente: sigue en el dato → reabierta")
        ok(x[a3["id"]]["estado"] == "no_aplica", "«No aplica» se mantiene con su motivo")
        c4 = x[a4["id"]]
        ok(c4["escalado"]["nivel"] == 2 and "mili" in c4["escalado_cadena"][1:] and c4["responsable_ahora"] == c4["escalado_cadena"][2],
           f"Sin tocar y con dos plazos pasados → sube por la cadena {' → '.join(c4['escalado_cadena'])} (jefa de accounts = Mili, luego Tomás)")
        luc = json.loads((sal / "p_lucia.json").read_text())
        ok(luc["resumen_diario"]["pasadas"] > 0 and "plazo pasado" in luc["resumen_diario"]["texto"], "El resumen diario de Lucía avisa del plazo pasado")
        mili = json.loads((sal / "p_mili.json").read_text())
        ok(mili["mi_dia"]["escaladas_a_mi"] > 0, f"Mi día de Mili cuenta {mili['mi_dia']['escaladas_a_mi']} escaladas a ella")


# ------------------------------------------------------------------ D · coherencia
def coherencia():
    print("D · coherencia (cifras de alertas = cifras de cada módulo)")
    d = json.loads((AQUI / "data/alertas/alertas.json").read_text())
    for c in d["coherencia"]:
        ok(c["ok"], f"{c['que']}: {c['cifra_modulo']} en {c['modulo']} = {c['cifra_alertas']} en alertas")


if __name__ == "__main__":
    sys.path.insert(0, str(AQUI))
    coherencia()
    tmp = Path(tempfile.mkdtemp(prefix="alertas_"))
    srv, env = servidor_propio(tmp)
    try:
        permisos()
        pantalla()            # antes de C: lo que pinta es lo de la base sin marcas de la prueba
        estados(tmp, env)
    finally:
        srv.terminate()
        srv.wait()
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"\n{'TODO BIEN' if not FALLOS else str(len(FALLOS)) + ' FALLOS'}")
    sys.exit(1 if FALLOS else 0)

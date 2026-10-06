#!/usr/bin/env python3
"""Ensayo de escalados sobre Postgres (F5.11).

Demuestra, en la base ro_esc y con un legado propio (bucles encendidos, salidas apagadas), que:
1. una alerta vencida publica «Pasó el plazo sin «Lo tengo»: sube a X» una sola vez, en el canal
   de su departamento y en la campana de quien toca;
2. un aviso automático ignorado sube una sola vez aunque pasen varias vueltas;
3. lo marcado «Lo tengo» no escala;
4. nada sale fuera (ningún envío en modo real).

Orden: python3 migracion/escalados.py
"""
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
E = Path("~/RO_MIGRACION/esc").expanduser()
APP = E / "app"
URL = os.environ.get("RO_ESC_URL", "postgresql://ro:ro@127.0.0.1:5432/ro_esc")
PUERTO = 8783
BASE = f"http://127.0.0.1:{PUERTO}"
NOMBRE_DEP = {
    "web", "seo", "crm", "publicidad", "redes", "accounts", "altas",
    "administracion", "rrhh", "direccion",
}

RESULTADOS = []
ACTUAL = None
VENC = []
RESUMEN = {}


def anotar(nombre, ok, detalle=""):
    RESULTADOS.append((nombre, bool(ok), detalle))
    marca = "✔" if ok else "✘"
    print(f"{marca} {nombre}" + (f" · {detalle}" if detalle else ""), flush=True)


def copia_sqlite():
    limpia = Path("~/RO_MIGRACION/local.db.limpia").expanduser()
    antes = Path("~/RO_MIGRACION/local.db.antes").expanduser()
    return limpia if limpia.exists() else antes


def personas():
    raw = json.loads((APP / "data" / "personas.json").read_text())
    if isinstance(raw, dict):
        return raw.get("personas") or []
    return raw


def direccion():
    """Id de la primera persona con puesto dirección y activa. En la salida solo va el puesto."""
    for p in personas():
        puestos = p.get("puestos") or []
        if p.get("activo") and "direccion" in puestos:
            return p["id"]
    sys.exit("no hay persona de dirección activa")


def entorno(reloj):
    env = {**os.environ}
    for k in ("RO_AVISOS_SIN_BUCLE", "RO_MODO", "RO_ENVIOS_REALES", "RO_CLICKUP_REAL", "RO_DB"):
        env.pop(k, None)
    recarga = E / "recarga.json"
    recarga.write_text('{"ligera": []}')
    env["DATABASE_URL"] = URL
    env["RO_RELOJ"] = reloj
    env["RO_SIN_LLAVES"] = "1"
    env["RO_RECARGA_CONFIG"] = str(recarga)
    env["RO_DEPARTAMENTOS"] = str(APP / "data" / "departamentos.json")
    return env


def puerto_libre():
    s = socket.socket()
    try:
        return s.connect_ex(("127.0.0.1", PUERTO)) != 0
    finally:
        s.close()


def pedir(ruta, metodo="GET", cuerpo=None, yo=None):
    h = {}
    if yo:
        h["X-RO-Yo"] = yo
    if metodo == "POST":
        h.update({"X-RO-App": "1", "Content-Type": "application/json"})
    datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
    req = urllib.request.Request(BASE + ruta, data=datos, method=metodo, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            raw, estado = r.read().decode(), r.status
    except urllib.error.HTTPError as e:
        raw, estado = e.read().decode(), e.code
    except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
        return 0, f"sin respuesta del servidor: {e}"
    try:
        return estado, json.loads(raw) if raw else None
    except json.JSONDecodeError:
        return estado, raw


def arrancar(reloj):
    global ACTUAL
    if not puerto_libre():
        sys.exit(f"el puerto {PUERTO} está ocupado")
    logp = E / "logs" / f"legado_{reloj.replace(':', '')}.log"
    logp.parent.mkdir(parents=True, exist_ok=True)
    log = open(logp, "ab")
    p = subprocess.Popen(
        [sys.executable, "servir.py", "--bind", "127.0.0.1", "--puerto", str(PUERTO)],
        cwd=APP, env=entorno(reloj), stdout=log, stderr=subprocess.STDOUT,
    )
    ACTUAL = p
    limite = time.time() + 120
    while time.time() < limite:
        if p.poll() is not None:
            break
        if pedir("/api/elegir")[0] == 200:
            return p
        time.sleep(2)
    parar(p)
    cola = logp.read_text(errors="replace").splitlines()[-30:]
    sys.exit("el legado no respondió en 120 s\n" + "\n".join(cola))


def parar(p):
    global ACTUAL
    if p is None:
        return
    if p.poll() is None:
        p.terminate()
        try:
            p.wait(timeout=20)
        except subprocess.TimeoutExpired:
            p.kill()
            p.wait(timeout=10)
    if ACTUAL is p:
        ACTUAL = None
    limite = time.time() + 10
    while time.time() < limite and not puerto_libre():
        time.sleep(0.3)


def sql(consulta, *args):
    if not consulta.lstrip().upper().startswith("SELECT"):
        raise RuntimeError("el ensayo solo lee")
    import psycopg
    with psycopg.connect(URL, autocommit=True) as con:
        return con.execute(consulta, args).fetchall()


def como_lista(v):
    if isinstance(v, list):
        return v
    if not v:
        return []
    return json.loads(v)


def leer_alertas():
    raw = json.loads((APP / "data" / "alertas" / "alertas.json").read_text())
    if isinstance(raw, dict):
        return raw.get("alertas") or []
    return raw


def preparar_estado():
    dest = E / "estado_alertas.json"
    for origen in (
        APP / "data" / "alertas" / "_estado" / "estado_alertas.json",
        APP / "fuentes_alertas" / "estado_alertas.json",
    ):
        if origen.exists():
            shutil.copy(origen, dest)
            return dest
    dest.write_text("{}")
    return dest


def generar(ahora, con_pg=False):
    """Genera alertas en la copia. Sin RO_ALERTAS_SALIDA escribe en APP/data/alertas."""
    preparar_estado()
    env = {
        **os.environ,
        "RO_SIN_LLAVES": "1",
        "RO_ALERTAS_AHORA": ahora,
        "RO_ALERTAS_ESTADO": str(E / "estado_alertas.json"),
    }
    for k in ("RO_ALERTAS_SALIDA", "RO_ENVIOS_REALES", "RO_CLICKUP_REAL", "RO_MODO"):
        env.pop(k, None)
    if con_pg:
        env.pop("RO_DB", None)
        env["DATABASE_URL"] = URL
    else:
        env["RO_DB"] = str(copia_sqlite())
        env.pop("DATABASE_URL", None)
    logp = E / "logs" / ("generar_pg.log" if con_pg else "generar_sqlite.log")
    r = subprocess.run(
        [sys.executable, "fuentes_alertas/generar_alertas.py"],
        cwd=APP, env=env, capture_output=True, text=True, timeout=600,
    )
    logp.write_text((r.stdout or "") + "\n" + (r.stderr or ""))
    return r.returncode


def vencidas():
    out = []
    for a in leer_alertas():
        esc = a.get("escalado") or {}
        if (esc.get("nivel") or 0) >= 1 and a.get("departamento") in NOMBRE_DEP and esc.get("a_id"):
            out.append(a)
    return out


def clave_alerta(a):
    esc = a.get("escalado") or {}
    marca = a.get("detectada") or a.get("desde") or ""
    return f"escalado:alerta:{a['id']}:{marca}:{esc.get('nivel')}"


def alertas():
    global VENC
    rc = generar("2026-10-12 09:00", con_pg=False)
    anotar("generar alertas con el plazo adelantado", rc == 0, f"rc={rc}")
    if rc != 0:
        return
    VENC = vencidas()
    if not VENC:
        rc2 = generar("2026-11-02 09:00", con_pg=False)
        anotar("generar alertas un mes más tarde", rc2 == 0, f"rc={rc2}")
        VENC = vencidas()
    anotar("hay alertas vencidas que escalar", len(VENC) >= 1, f"n={len(VENC)}")
    if not VENC:
        anotar("alertas vencidas", False, "sin alertas con plazo")
        return
    p = arrancar("2026-10-05T07:30")
    try:
        est = pedir("/api/canales", yo=direccion())[0]
        anotar("sincronizar canales", est == 200, f"estado={est}")
        n1 = sql("SELECT count(*) FROM canal_mensajes WHERE clave LIKE 'escalado:%%'")[0][0]
        RESUMEN["n1"] = n1
        anotar("hay avisos de escalado en la base", n1 >= 1, f"n1={n1}")
        bien = 0
        for i, a in enumerate(VENC[:5], start=1):
            filas = sql(
                "SELECT canal_id, menciones FROM canal_mensajes WHERE clave = %s",
                clave_alerta(a),
            )
            canal_ok = len(filas) == 1 and filas[0][0] == f"avisos-{a['departamento']}"
            menciona = canal_ok and a["escalado"]["a_id"] in como_lista(filas[0][1])
            camp = pedir("/api/canales/campana", yo=a["escalado"]["a_id"])
            items = (camp[1] or {}).get("items") or [] if isinstance(camp[1], dict) else []
            campana_ok = any(
                x.get("tipo") == "escalado" and "sube a" in (x.get("texto") or "")
                for x in items
            )
            ok = canal_ok and menciona and campana_ok
            bien += 1 if ok else 0
            motivo = "canal y campana" if ok else (
                "sin fila" if len(filas) != 1 else
                "canal distinto" if not canal_ok else
                "sin mención" if not menciona else
                "campana sin «sube a»"
            )
            anotar(f"alerta {i} de {min(5, len(VENC))} sube y llega a la campana", ok, motivo)
        anotar("sube a la persona de la cadena", bien == min(5, len(VENC)), f"{bien}/{min(5, len(VENC))}")
        print("esperando el candado de sincronizar (31 s)", flush=True)
        time.sleep(31)
        pedir("/api/canales", yo=direccion())
        n2 = sql("SELECT count(*) FROM canal_mensajes WHERE clave LIKE 'escalado:%%'")[0][0]
        RESUMEN["n2"] = n2
        anotar("una sola vez", n2 == n1, f"n1={n1} n2={n2}")
    finally:
        parar(p)


def avisos():
    p = arrancar("2026-10-02T18:00")
    try:
        r1 = pedir("/api/avisos_programados/ejecutar", "POST", {}, yo=direccion())
        r2 = pedir("/api/avisos_programados/ejecutar", "POST", {}, yo=direccion())
        pub1 = r1[1].get("publicados") if isinstance(r1[1], dict) else None
        pub2 = r2[1].get("publicados") if isinstance(r2[1], dict) else None
        RESUMEN["publicados_viernes"] = pub1
        anotar("viernes: publica", r1[0] == 200 and (pub1 or 0) > 0, f"estado={r1[0]} publicados={pub1}")
        anotar("viernes: la segunda vuelta no repite", pub2 == 0, f"publicados={pub2}")
    finally:
        parar(p)
    p = arrancar("2026-10-05T09:00")
    try:
        print("esperando una vuelta del bucle (8 s)", flush=True)
        time.sleep(8)
        r9 = pedir("/api/avisos_programados/ejecutar", "POST", {}, yo=direccion())
        anotar("lunes: ejecutar responde", r9[0] == 200, f"estado={r9[0]}")
        filas = sql("SELECT clave, menciones, canal_id, id FROM canal_mensajes WHERE clave LIKE 'prog_esc:%%'")
        RESUMEN["filas_b"] = len(filas)
        claves = [f[0] for f in filas]
        anotar("los recordatorios ignorados suben", len(filas) >= 1, f"filas={len(filas)}")
        anotar("ninguna clave de escalado repetida", len(set(claves)) == len(filas), f"claves={len(set(claves))} filas={len(filas)}")
        n_antes = len(filas)
        pedir("/api/avisos_programados/ejecutar", "POST", {}, yo=direccion())
        n_despues = sql("SELECT count(*) FROM canal_mensajes WHERE clave LIKE 'prog_esc:%%'")[0][0]
        anotar("otra vuelta no añade escalados", n_despues == n_antes, f"antes={n_antes} despues={n_despues}")
        bien = 0
        for i, f in enumerate(filas[:3], start=1):
            menc = como_lista(f[1])
            quien = menc[0] if menc else None
            camp = pedir("/api/canales/campana", yo=quien) if quien else (0, {})
            items = (camp[1] or {}).get("items") or [] if isinstance(camp[1], dict) else []
            campana_ok = any("¿lo miras?" in (x.get("texto") or "") for x in items)
            padre = sql("SELECT menciones FROM canal_mensajes WHERE clave = %s", f[0][len("prog_esc:"):])
            avisado = como_lista(padre[0][0]) if padre else []
            otra = bool(quien) and quien not in avisado
            ok = campana_ok and otra
            bien += 1 if ok else 0
            motivo = "otra persona y campana" if ok else (
                "sin mención" if not quien else
                "misma persona" if not otra else
                "campana sin «¿lo miras?»"
            )
            anotar(f"aviso {i} sube a otra persona y le llega", ok, motivo)
        if filas:
            anotar("sube a otra persona", bien == min(3, len(filas)), f"{bien}/{min(3, len(filas))}")
    finally:
        parar(p)


def lo_tengo():
    if not VENC:
        anotar("lo marcado en Postgres no escala", False, "sin alerta vencida del paso anterior")
        RESUMEN["c"] = "sin alerta"
        return
    a = VENC[0]
    p = arrancar("2026-10-05T07:30")
    try:
        cuerpo = {
            "modulo": "alertas", "herramienta": "app", "tipo": "alerta_lo_tengo",
            "objeto": a["id"], "cliente_id": a.get("cliente_id"),
            "texto": "ensayo F5.11", "vista_previa": {"alerta": a["id"]},
        }
        r = pedir("/api/acciones", "POST", cuerpo, yo=a["dueno_id"])
        n = sql(
            "SELECT count(*) FROM acciones WHERE modulo='alertas' AND tipo='alerta_lo_tengo' AND objeto=%s",
            a["id"],
        )[0][0]
        anotar("«Lo tengo» queda en Postgres", r[0] == 200 and n == 1, f"estado={r[0]} filas={n}")
    finally:
        parar(p)
    rc = generar("2026-10-12 09:00", con_pg=True)
    anotar("regenerar leyendo la base", rc == 0, f"rc={rc}")
    if rc != 0:
        RESUMEN["c"] = "generador"
        return
    a2 = next((x for x in leer_alertas() if x.get("id") == a["id"]), None)
    if not a2:
        anotar("lo marcado en Postgres no escala", False, "la alerta ya no sale")
        RESUMEN["c"] = "ausente"
        return
    estado = a2.get("estado")
    nivel = (a2.get("escalado") or {}).get("nivel")
    ok = estado == "lo_tengo" and nivel == 0
    RESUMEN["c"] = "ya estaba" if ok else f"estado={estado} nivel={nivel}"
    anotar("lo marcado en Postgres no escala", ok, f"estado={estado} nivel={nivel}")


def nada_fuera():
    import psycopg
    try:
        n = sql("SELECT count(*) FROM envios WHERE modo = 'real'")[0][0]
        anotar("nada sale fuera", n == 0, f"envios reales={n}")
    except psycopg.errors.UndefinedTable:
        anotar("nada sale fuera", True, "sin tabla envios (nada pudo salir)")


def base_limpia():
    """Cada pasada parte de la copia. Si no, la segunda (la batería) ya no publica y «Lo tengo» cuenta 2."""
    r = subprocess.run(
        [sys.executable, str(RAIZ / "migracion" / "contrato_escritura.py"), "base-limpia", "ro_esc"],
        cwd=RAIZ, capture_output=True, text=True, timeout=180,
    )
    (E / "logs").mkdir(parents=True, exist_ok=True)
    (E / "logs" / "base_limpia.log").write_text((r.stdout or "") + "\n" + (r.stderr or ""))
    ok = r.returncode == 0 and "✔ ro_esc lista" in (r.stdout or "")
    anotar("base ro_esc limpia", ok, f"rc={r.returncode}")
    if not ok:
        sys.exit(1)


def main():
    if not URL.endswith("/ro_esc"):
        sys.exit("solo contra ro_esc")
    if not (APP / "servir.py").exists():
        sys.exit(f"no está la copia de la app ({APP / 'servir.py'})")
    base_limpia()
    try:
        alertas()
        avisos()
        lo_tengo()
        nada_fuera()
    finally:
        if ACTUAL is not None:
            parar(ACTUAL)
    mal = [n for n, ok, _ in RESULTADOS if not ok]
    print(f"{'✔' if not mal else '✘'} {len(RESULTADOS) - len(mal)}/{len(RESULTADOS)}")
    return 0 if not mal else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        if ACTUAL is not None:
            parar(ACTUAL)
        raise

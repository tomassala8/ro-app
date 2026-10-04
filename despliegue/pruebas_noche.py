#!/usr/bin/env python3
"""despliegue/pruebas_noche.py · la batería nocturna (3:00) en UNA orden (carril C5, punto 3.6 del estudio 23).

Arranca su propio servir.py en un puerto aparte y con una COPIA de local.db (no toca el rastro real), y pasa:
  1. Todas las pruebas que ya existen: pruebas_*.py de la raíz y fuentes*/probar_*.py y fuentes/comprobar.py
     (las probar_* abren Chrome sin cabeza con Playwright y hacen capturas en capturas/<módulo>/).
  2. HUMO: cada módulo «hecho» responde 200 para cada puesto que lo ve (sesión, código del módulo y sus datos).
  3. FUGA: matriz completa puesto × fichero de datos: nadie recibe un fichero de una pantalla que no es de su
     puesto (403), y pruebas_e0.py (clientes ajenos, «ver como», ficheros que no se sirven, escáner).
  3b. ACCESO (E49): un servir.py en MODO SERVIDOR sin sello de Cloudflare Access → 403 en todo (también con
     ?yo=, X-RO-Yo o la cabecera de correo falsificada); /vivo → 200; y, si hay openssl, un sello firmado bueno → 200.
  5. SOLIDEZ (auditoría 35): cada fallo PROVOCADO sobre copias en una carpeta temporal (nunca data/ real, ni
     ~/Downloads, ni ~/RO_HERRAMIENTAS; sin red o con módulos falsos): salida vacía / sin claves / recuento que cae,
     Meta caído (no se sella «bien», último dato bueno con su hora, aviso, Captación no cae a 0), Desk caído (la Bandeja
     vuelve al dato bueno más reciente), externos.py (bloqueo, escritura atómica, mezcla con el fichero actual, _error de
     Google sin pisar Search Console) y la llave de GHL que rota (bloqueo fuera de la tubería, respaldo antes de usarla).
     Solo esta parte: --solo-solidez.
  6. N11 · CONEXIONES SIN FALLOS: reintentos de lectura (servidor falso en 127.0.0.1), caché de tokens, salud.json real
     (todas las conexiones, qué hacer, dueño, sin secretos), fallos provocados, orden de la tubería y permisos. --solo-n11.
  (4) CUADRE: tres cifras cruzadas entre módulos para el mismo cliente:
       a) leads de Meta en 7 días: Captación = CRM = verdad única = ficha (data/clientes/<id>.json, capa E1)
       b) gasto de Meta del mes anterior: Captación = ficha (E1)
       c) account: verdad única = Captación = CRM  (aviso, no fallo, mientras esos módulos no adopten la verdad)
     y pruebas_coherencia.py de E0.
Deja el informe en despliegue/estado/pruebas/<fecha>.json y .md. Sale con 1 si algo falla (y la tubería de
código no debe publicar: ver DESPLIEGUE.md).

Uso: python3 despliegue/pruebas_noche.py [--puerto 8899] [--sin-navegador] [--sin-red] [--sin-avisos]
"""
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

AQUI = Path(__file__).resolve().parent
APP = AQUI.parent
sys.path.insert(0, str(AQUI))
sys.path.insert(1, str(APP))
import config  # noqa: E402

ARGS = sys.argv[1:]
def _libre(p):
    import socket as _s
    with _s.socket() as s:
        return s.connect_ex(("127.0.0.1", p)) != 0


PUERTO = int(ARGS[ARGS.index("--puerto") + 1]) if "--puerto" in ARGS else next(p for p in range(8899, 8999) if _libre(p))
BASE = f"http://127.0.0.1:{PUERTO}"
DATA = APP / "data"
NUCLEO = {"personas", "asignaciones", "clientes", "alarmas", "logos", "meta", "para_confirmar", "ids_clientes"}
informe = {"inicio": datetime.now().isoformat(timespec="seconds"), "puerto": PUERTO, "baterias": [], "humo": {}, "fuga": {}, "cuadre": {}}


def get(ruta, yo):
    req = urllib.request.Request(BASE + ruta, headers={"X-RO-Yo": yo})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return 0


def libre(p):
    with socket.socket() as s:
        return s.connect_ex(("127.0.0.1", p)) != 0


# ------------------------------------------------------------------ servidor de pruebas
def arrancar_servidor(tmp):
    if not libre(PUERTO):
        sys.exit(f"El puerto {PUERTO} está ocupado: usa --puerto otro.")
    db = tmp / "local_pruebas.db"
    if (APP / "local.db").exists():
        shutil.copy2(APP / "local.db", db)
    env = {**os.environ, "RO_DB": str(db)}
    env.pop("DATABASE_URL", None)   # el servidor de pruebas NUNCA escribe en la base de producción: SQLite aparte
    env.pop("RO_MODO", None)
    log = open(tmp / "servir.log", "w")
    proc = subprocess.Popen([sys.executable, "servir.py", "--bind", "127.0.0.1", "--puerto", str(PUERTO)], cwd=APP, env=env, stdout=log, stderr=log)
    for _ in range(60):
        if get("/api/sesion", "tomas") == 200:
            return proc
        time.sleep(0.5)
    proc.terminate()
    sys.exit("servir.py no arrancó: mira " + str(tmp / "servir.log"))


# ------------------------------------------------------------------ 1 · baterías existentes
def baterias(tmp):
    lista = []
    for f in sorted(APP.glob("pruebas_*.py")) + sorted(x for x in AQUI.glob("pruebas_*.py") if x.name != "pruebas_noche.py"):   # también despliegue/pruebas_tokens.py (N11: nunca a sí misma, o se llama sin fin)
        args = ["--puerto", str(PUERTO)] if f.name == "pruebas_e0.py" else []
        lista.append((f.relative_to(APP), args, False))
    if (APP / "fuentes/comprobar.py").exists():
        lista.append((Path("fuentes/comprobar.py"), [], "red"))
    for f in sorted(APP.glob("fuentes*/probar_*.py")):
        lista.append((f.relative_to(APP), [str(PUERTO)], "navegador"))
    for rel, args, necesita in lista:
        if necesita == "navegador" and "--sin-navegador" in ARGS:
            informe["baterias"].append({"prueba": str(rel), "estado": "omitida", "motivo": "--sin-navegador"}); continue
        if necesita == "red" and "--sin-red" in ARGS:
            informe["baterias"].append({"prueba": str(rel), "estado": "omitida", "motivo": "--sin-red (3 lecturas de Meta)"}); continue
        t0 = time.time()
        try:
            r = subprocess.run([sys.executable, str(rel), *args], cwd=APP, capture_output=True, text=True, timeout=900)
            salida = (r.stdout + r.stderr).strip().splitlines()
            ok = r.returncode == 0
            fallos = [x for x in salida if x.startswith(("✗", "FALLO", "✘"))][:10]
        except subprocess.TimeoutExpired:
            ok, salida, fallos = False, ["se pasó de 15 min"], []
        estado = "bien" if ok else "falla"
        if not ok and any("No module named 'playwright'" in x for x in salida):
            estado = "omitida"
        informe["baterias"].append({"prueba": str(rel), "estado": estado, "segundos": round(time.time() - t0, 1),
                                    "ultimas_lineas": salida[-4:], "fallos": fallos})
        print(f"  {'✔' if ok else '✘'} {rel} ({round(time.time() - t0, 1)} s)")


# ------------------------------------------------------------------ 2 y 3 · humo y fuga
def humo_y_fuga():
    import permisos as P
    modulos_vis = P.cargar_modulos()
    indice = (APP / "modulos/indice.js").read_text()
    hechos = {}
    for m in re.finditer(r"\{\s*id:\s*'([\w\-]+)'(.*?)resumen:", indice, re.S):
        if re.search(r"estado:\s*'hecho'", m.group(2)):
            f = re.search(r"fichero:\s*'\./([\w\-]+\.js)'", m.group(2))
            hechos[m.group(1)] = f.group(1) if f else None
    personas = [p for p in json.loads((DATA / "personas.json").read_text()) if p.get("activo") and p.get("puestos")]
    puestos = sorted({x for p in personas for x in p["puestos"]})
    # una persona por puesto: la que SOLO tiene ese puesto si existe (así la prueba es del puesto, no de la persona)
    rep = {}
    for pu in puestos:
        solo = [p for p in personas if p["puestos"] == [pu]]
        rep[pu] = (solo or [p for p in personas if pu in p["puestos"]])[0]
    reglas = P.REGLAS.get("datos_de_modulo", {})

    def esperado(persona, conf):
        conf = conf if isinstance(conf, dict) else {"modulos": conf}
        if conf.get("puestos"):
            nivel = "todo" if set(persona["puestos"]) & set(conf["puestos"]) else None
        else:
            niveles = [P.nivel_modulo(persona, modulos_vis.get(m, {})) for m in conf.get("modulos") or []]
            nivel = next((n for n in niveles if n), None)
        if conf.get("excluir_puestos") and set(persona["puestos"]) <= set(conf["excluir_puestos"]):
            nivel = None
        return nivel

    humo_fallos, humo_ok = [], 0
    for mid, fichero in sorted(hechos.items()):
        ficheros = [rel for rel, conf in reglas.items()
                    if mid in ((conf.get("modulos") or []) if isinstance(conf, dict) else conf) and (DATA / f"{rel}.json").exists()]
        for pu, persona in rep.items():
            if not P.nivel_modulo(persona, modulos_vis.get(mid, {})):
                continue
            codigos = {"/api/sesion": get("/api/sesion", persona["id"])}
            if fichero:
                codigos[f"/modulos/{fichero}"] = get(f"/modulos/{fichero}", persona["id"])
            for rel in ficheros:
                conf = reglas[rel]
                if esperado(persona, conf):
                    codigos[f"/api/modulo/{rel}"] = get(f"/api/modulo/{rel}", persona["id"])
            malos = {r: c for r, c in codigos.items() if c != 200}
            if malos:
                humo_fallos.append({"modulo": mid, "puesto": pu, "persona": persona["id"], "respuestas": malos})
            else:
                humo_ok += 1
    informe["humo"] = {"modulos_hechos": len(hechos), "puestos": len(rep), "combinaciones_bien": humo_ok, "fallos": humo_fallos}
    print(f"  {'✔' if not humo_fallos else '✘'} humo: {humo_ok} combinaciones módulo × puesto responden 200 · {len(humo_fallos)} fallos")

    fuga, casos = [], 0
    for rel, conf in sorted(reglas.items()):
        if rel.split("/")[0] in NUCLEO or not (DATA / f"{rel}.json").exists():
            continue
        for pu, persona in rep.items():
            casos += 1
            c = get(f"/api/modulo/{rel}", persona["id"])
            debe = esperado(persona, conf)
            if not debe and c == 200:
                fuga.append({"fichero": rel, "puesto": pu, "persona": persona["id"], "recibe": c})
            elif debe and c == 403:
                fuga.append({"fichero": rel, "puesto": pu, "persona": persona["id"], "recibe": c, "tipo": "le falta (403 indebido)"})
    informe["fuga"] = {"casos": casos, "problemas": fuga}
    print(f"  {'✔' if not fuga else '✘'} fuga: {casos} casos puesto × fichero · {len(fuga)} problemas")
    return not humo_fallos and not fuga


# ------------------------------------------------------------------ 3b · acceso en modo servidor (E49)
def acceso_servidor(tmp):
    import base64, socket as _s
    puerto = next(p for p in range(PUERTO + 1, PUERTO + 60) if _libre(p))
    b64 = lambda b: base64.urlsafe_b64encode(b).rstrip(b"=").decode()
    jwks, firmar = tmp / "jwks.json", None
    clave = tmp / "k.pem"
    if shutil.which("openssl") and subprocess.run(["openssl", "genrsa", "-out", str(clave), "2048"], capture_output=True).returncode == 0:
        mod = subprocess.run(["openssl", "rsa", "-in", str(clave), "-noout", "-modulus"], capture_output=True, text=True).stdout.split("=")[1].strip()
        n = int(mod, 16)
        jwks.write_text(json.dumps({"keys": [{"kty": "RSA", "kid": "noche", "e": b64((65537).to_bytes(3, "big")),
                                               "n": b64(n.to_bytes((n.bit_length() + 7) // 8, "big"))}]}))

        def firmar(correo):
            h = b64(json.dumps({"alg": "RS256", "kid": "noche"}).encode())
            p = b64(json.dumps({"aud": ["aud-noche"], "email": correo, "iss": "https://noche.cloudflareaccess.com",
                                "exp": int(time.time()) + 600, "nbf": int(time.time())}).encode())
            f = subprocess.run(["openssl", "dgst", "-sha256", "-sign", str(clave)], input=f"{h}.{p}".encode(), capture_output=True).stdout
            return f"{h}.{p}.{b64(f)}"
    else:
        jwks.write_text(json.dumps({"keys": []}))
    db = tmp / "local_acceso.db"
    if (APP / "local.db").exists():
        shutil.copy2(APP / "local.db", db)
    env = {**os.environ, "RO_DB": str(db), "RO_MODO": "servidor", "PORT": str(puerto), "RO_CF_EQUIPO": "noche",
           "RO_CF_AUD": "aud-noche", "RO_CF_CERTS_FICHERO": str(jwks)}
    env.pop("DATABASE_URL", None)
    log = open(tmp / "servir_acceso.log", "w")
    proc = subprocess.Popen([sys.executable, "servir.py"], cwd=APP, env=env, stdout=log, stderr=log)
    base = f"http://127.0.0.1:{puerto}"

    def g(ruta, cab):
        try:
            with urllib.request.urlopen(urllib.request.Request(base + ruta, headers=cab), timeout=20) as r:
                return r.status
        except urllib.error.HTTPError as e:
            return e.code
        except Exception:
            return 0
    for _ in range(60):
        if g("/vivo", {}) == 200:
            break
        time.sleep(0.5)
    casos = [("sin sello", "/api/sesion", {}, 403), ("?yo= sin sello", "/api/sesion?yo=tomas", {}, 403),
             ("X-RO-Yo sin sello", "/api/sesion", {"X-RO-Yo": "tomas"}, 403),
             ("cabecera de correo falsificada", "/api/sesion", {"Cf-Access-Authenticated-User-Email": "fixture1@rankingonline.com"}, 403),
             ("carcasa sin sello", "/index.html", {}, 403), ("datos de un módulo sin sello", "/api/modulo/bandeja/bandeja", {}, 403),
             ("salud de Render", "/vivo", {}, 200)]
    if firmar:
        tomas = next((p.get("correo") for p in json.loads((DATA / "personas.json").read_text()) if p["id"] == "tomas"), None)
        if tomas:
            casos.append(("sello firmado bueno", "/api/sesion", {"Cf-Access-Jwt-Assertion": firmar(tomas)}, 200))
    res = []
    try:
        for nombre, ruta, cab, esperado in casos:
            c = g(ruta, cab)
            res.append({"caso": nombre, "esperado": esperado, "recibe": c, "ok": c == esperado})
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except Exception:
            proc.kill()
    malos = [r for r in res if not r["ok"]]
    informe["acceso"] = {"casos": res, "fallos": len(malos)}
    print(f"  {'✔' if not malos else '✘'} acceso en modo servidor (E49): {len(res) - len(malos)} de {len(res)} casos bien")
    return not malos


# ------------------------------------------------------------------ 4 · cuadre
def cuadre():
    def leer(rel):
        try:
            return json.loads((DATA / rel).read_text())
        except Exception:
            return None
    cap = {c["cliente_id"]: c for c in (leer("captacion/captacion.json") or {}).get("clientes", []) if c.get("cliente_id")}
    crm = {c["cliente_id"]: c for c in (leer("crm/crm.json") or {}).get("subcuentas", []) if c.get("cliente_id")}
    ver = {c["cliente_id"]: c for c in (leer("verdad/clientes.json") or {}).get("clientes", []) if c.get("cliente_id")}

    def e1(cid):
        d = leer(f"clientes/{cid}.json") or {}
        return ((d.get("fuentes") or {}).get("meta") or {}).get("datos") or {}

    def igual(a, b):
        if a is None or b is None:
            return True             # sin dato en un lado no es una contradicción (lo marca su sello)
        return abs(float(a) - float(b)) < 0.01

    res = {"leads_meta_7d": [], "gasto_meta_mes_anterior": [], "account": []}
    comprobados = {"leads_meta_7d": 0, "gasto_meta_mes_anterior": 0, "account": 0}
    for cid, c in cap.items():
        l_cap = (c.get("leads") or {}).get("7d")
        vals = {"captacion": l_cap, "crm": (crm.get(cid) or {}).get("leads_meta_7d"),
                "verdad": (ver.get(cid) or {}).get("leads_meta_7d"), "ficha_e1": (e1(cid).get("leads") or {}).get("7d")}
        presentes = {k: v for k, v in vals.items() if v is not None}
        if len(presentes) >= 2:
            comprobados["leads_meta_7d"] += 1
            if not all(igual(l_cap if l_cap is not None else list(presentes.values())[0], v) for v in presentes.values()):
                res["leads_meta_7d"].append({"cliente": cid, **vals})
        g_cap, g_e1 = (c.get("gasto") or {}).get("mes_anterior"), (e1(cid).get("gasto") or {}).get("mes_anterior")
        if g_cap is not None and g_e1 is not None:
            comprobados["gasto_meta_mes_anterior"] += 1
            if not igual(g_cap, g_e1):
                res["gasto_meta_mes_anterior"].append({"cliente": cid, "captacion": g_cap, "ficha_e1": g_e1})
        acc = {"verdad": (ver.get(cid) or {}).get("account"), "captacion": (c.get("equipo") or {}).get("account"),
               "crm": (crm.get(cid) or {}).get("account_id")}
        presentes = {k: v for k, v in acc.items() if v}
        if len(presentes) >= 2:
            comprobados["account"] += 1
            if len(set(presentes.values())) > 1:
                res["account"].append({"cliente": cid, **acc})
    informe["cuadre"] = {"comprobados": comprobados, "diferencias": res,
                         "regla": "a) y b) fallan la batería; c) es aviso hasta que Captación y CRM lean la verdad única (como pruebas_coherencia.py)"}
    ok = not res["leads_meta_7d"] and not res["gasto_meta_mes_anterior"]
    for k in res:
        print(f"  {'✔' if not res[k] else ('⚠' if k == 'account' else '✘')} cuadre {k}: {comprobados[k]} clientes · {len(res[k])} diferencias")
    return ok


# ------------------------------------------------------------------ 5 · solidez (auditoría 35: A5, A6, M2, M3, M8)
# Cada fallo se PROVOCA sobre copias en una carpeta temporal: nunca se escribe en data/ de la app, en ~/Downloads ni en
# ~/RO_HERRAMIENTAS (solo se leen), ni se llama a Meta, Desk, Google o GHL (red cortada o módulos falsos).
SIN_RED = {"HTTPS_PROXY": "http://127.0.0.1:9", "HTTP_PROXY": "http://127.0.0.1:9", "https_proxy": "http://127.0.0.1:9",
           "http_proxy": "http://127.0.0.1:9", "RO_SIN_CACHE_TOKENS": "1", "META_TOKEN": "caducado"}


def _j(f):
    try:
        return json.loads(Path(f).read_text())
    except Exception:
        return None


def _md5(f):
    import hashlib
    return hashlib.md5(Path(f).read_bytes()).hexdigest() if Path(f).exists() else None


def _sol_tuberia(tmp, caso):
    """La tubería con pasos falsos sobre ficheros de una carpeta temporal (RO_PASOS, RO_ESTADO_DIR aparte)."""
    d = tmp / "tub"
    (d / "e1" / "clientes").mkdir(parents=True)
    est = tmp / "tub_estado"
    (d / "vacio.json").write_text('{"a": 1}')
    (d / "claves.json").write_text('{"generado": "x", "clientes": [1]}')
    (d / "rec.json").write_text(json.dumps({"clientes": list(range(10))}))
    (d / "lista.json").write_text("[1, 2, 3]")
    fu = {"generado": "2026-10-02 18:05", "fuentes": [
        {"id": "meta", "estado": "bien", "hora": "2026-10-02 18:05", "clientes_con_dato": 28},
        {"id": "captacion_ghl", "estado": "bien", "hora": "2026-10-02 18:05", "clientes_con_dato": 21},
        {"id": "desk", "estado": "dato_viejo", "hora": "2026-10-02 07:00", "clientes_con_dato": 57}]}
    (d / "e1" / "fuentes.json").write_text(json.dumps(fu))
    ficha = {"id": "x", "estado_fuentes": {"meta": "bien", "captacion_ghl": "bien"},
             "fuentes": {"meta": {"estado": "bien", "hora": "2026-10-02 18:05", "datos": {"gasto": 354}},
                         "captacion_ghl": {"estado": "bien", "hora": "2026-10-02 18:05"}}}
    (d / "e1" / "clientes" / "x.json").write_text(json.dumps(ficha))
    py = sys.executable
    meta_caido = ("import json,pathlib as P;d=P.Path(%r);f=json.loads((d/'fuentes.json').read_text());"
                  "[x.update(estado='sin_conectar',hora=None) for x in f['fuentes'] if x['id']=='meta'];"
                  "[x.update(clientes_con_dato=0) for x in f['fuentes'] if x['id']=='captacion_ghl'];"
                  "(d/'fuentes.json').write_text(json.dumps(f));c=json.loads((d/'clientes'/'x.json').read_text());"
                  "c['fuentes']['meta']['estado']='sin_conectar';c['estado_fuentes']['meta']='sin_conectar';"
                  "(d/'clientes'/'x.json').write_text(json.dumps(c))") % str(d / "e1")
    ahora_txt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    pasos = {"reintentos": {"veces": 2, "esperas_s": [0.1]}, "pasos": [
        {"id": "vacio", "ligero": [py, "-c", f"open({str(d / 'vacio.json')!r},'w').write('{{}}')"], "salidas": [str(d / "vacio.json")]},
        {"id": "sin_claves", "ligero": [py, "-c", f"open({str(d / 'claves.json')!r},'w').write('{{\"generado\": \"y\"}}')"],
         "salidas": [str(d / "claves.json")], "claves_minimas": {str(d / "claves.json"): ["generado", "clientes"]}},
        {"id": "recuento", "ligero": [py, "-c", f"open({str(d / 'rec.json')!r},'w').write('{{\"clientes\": [1, 2]}}')"],
         "salidas": [str(d / "rec.json")], "recuento": [{"fichero": str(d / "rec.json"), "ruta": "clientes", "caida_max": 0.5, "minimo_antes": 4}]},
        {"id": "lista_vacia", "ligero": [py, "-c", f"open({str(d / 'lista.json')!r},'w').write('[]')"], "salidas": [str(d / "lista.json")]},
        {"id": "dep_vacio", "depende": ["vacio"], "ligero": [py, "-c", f"open({str(d / 'dep_vacio.txt')!r},'w').write('corrió')"], "salidas": []},
        {"id": "e1", "ligero": [py, "-c", meta_caido], "salidas": [str(d / "e1" / "fuentes.json"), str(d / "e1" / "clientes")],
         "vigilar_fuentes": {"fichero": str(d / "e1" / "fuentes.json"), "fichas": str(d / "e1" / "clientes"), "caida_max": 0.5, "minimo_antes": 4}},
        {"id": "dep_e1", "depende": ["e1"], "ligero": [py, "-c", f"open({str(d / 'dep_e1.txt')!r},'w').write('corrió')"], "salidas": []},
        {"id": "err_fuente", "errores_de_fuente": True, "ligero": [py, "-c",
         f"import json;json.dump({{'generado':'x','clientes':{{'Asetra':{{'gsc':{{'actual':{{'clics':702}},'error':401,'hora_error':{ahora_txt!r}}}}}}}}},open({str(d / 'ext.json')!r},'w'))"],
         "salidas": [str(d / "ext.json")]},
        {"id": "dep_err", "depende": ["err_fuente"], "ligero": [py, "-c", f"open({str(d / 'dep_err.txt')!r},'w').write('corrió')"], "salidas": []},
    ]}
    (tmp / "pasos_solidez.json").write_text(json.dumps(pasos))
    env = {**os.environ, "RO_PASOS": str(tmp / "pasos_solidez.json"), "RO_ESTADO_DIR": str(est), "RO_DB": str(tmp / "no_hay.db")}
    env.pop("DATABASE_URL", None)
    env.pop("RO_PUBLICAR_BASE", None)
    r = subprocess.run([py, str(AQUI / "tuberia.py"), "--ligero", "--quien", "pruebas_noche"], cwd=APP, env=env,
                       capture_output=True, text=True, timeout=300)
    regs = sorted((est / "registros").glob("*.json"))
    reg = _j(regs[-1]) if regs else {}
    pasos_r = {x["id"]: x for x in (reg or {}).get("pasos", [])}
    caso("tubería · salida vacía {} → fallo y se restaura", not pasos_r.get("vacio", {}).get("ok", True) and _j(d / "vacio.json") == {"a": 1})
    caso("tubería · su dependiente no corre", not (d / "dep_vacio.txt").exists())
    caso("tubería · sin claves mínimas → fallo y se restaura", not pasos_r.get("sin_claves", {}).get("ok", True)
         and (_j(d / "claves.json") or {}).get("clientes") == [1])
    caso("tubería · recuento que cae de 10 a 2 → fallo y se restaura", not pasos_r.get("recuento", {}).get("ok", True)
         and len((_j(d / "rec.json") or {}).get("clientes", [])) == 10)
    caso("tubería · lista que se queda sin filas → fallo y se restaura", _j(d / "lista.json") == [1, 2, 3])
    f1 = {x["id"]: x for x in (_j(d / "e1" / "fuentes.json") or {}).get("fuentes", [])}
    m, g = f1.get("meta", {}), f1.get("captacion_ghl", {})
    x1 = _j(d / "e1" / "clientes" / "x.json") or {}
    caso("Meta caído · la tubería NO sella «bien»", pasos_r.get("e1", {}).get("ok") is False
         and pasos_r.get("e1", {}).get("sello") in ("dato_viejo", "sin_dato"), pasos_r.get("e1", {}).get("intentos", [{}])[-1].get("error"))
    caso("Meta caído · se sirve el último dato bueno con su hora (18:05) marcado «dato_viejo» + caída",
         m.get("hora") == "2026-10-02 18:05" and m.get("estado") == "dato_viejo" and bool((m.get("caida") or {}).get("desde")), m)
    caso("Meta caído · Captación de GHL no cae a 0 (se queda en 21 clientes con dato)", g.get("clientes_con_dato") == 21, g)
    caso("Meta caído · la ficha también enseña el dato bueno marcado", (x1.get("fuentes", {}).get("meta") or {}).get("estado") == "dato_viejo"
         and x1.get("fuentes", {}).get("meta", {}).get("datos", {}).get("gasto") == 354 and x1.get("estado_fuentes", {}).get("meta") == "dato_viejo")
    caso("Meta caído · sus dependientes sí corren (dato coherente)", (d / "dep_e1.txt").exists())
    import sqlite3
    try:
        con = sqlite3.connect(est / "tuberia.db")
        avisos = [r_[0] for r_ in con.execute("SELECT clave FROM avisos WHERE tipo='fuente_caida'")]
        con.close()
    except Exception:
        avisos = []
    # R16: un aviso por paso con todas sus fuentes caídas («e1:captacion_ghl+meta»), no uno por fuente
    caso("Meta caído · hay aviso «fuente_caida» (uno por paso, con todas sus fuentes)",
         any(a.startswith("e1:") and "meta" in a[3:].split("+") for a in avisos), avisos)
    con_motivo = []
    try:
        con = sqlite3.connect(est / "tuberia.db")
        con_motivo = [r_[0] for r_ in con.execute("SELECT texto FROM avisos WHERE tipo='fuente_caida' AND clave LIKE 'e1:%'")]
        con.close()
    except Exception:
        pass
    caso("Meta caído · el motivo del aviso nunca sale vacío «()»", con_motivo and not any("()" in t for t in con_motivo), con_motivo[:1])
    caso("errores de fuente · cuentan como fallo de esa fuente (sin restaurar ni bloquear)",
         pasos_r.get("err_fuente", {}).get("ok") is False and pasos_r.get("err_fuente", {}).get("fuentes_con_error") == {"gsc": 1}
         and (d / "dep_err.txt").exists() and (_j(d / "ext.json") or {}).get("clientes", {}).get("Asetra", {}).get("gsc", {}).get("actual") == {"clics": 702})
    caso("tubería · la vuelta sale «con_fallos» (código 1)", r.returncode == 1 and (reg or {}).get("estado") == "con_fallos")
    # segunda vuelta con Meta todavía caído: sigue restaurando (la marca «caida» cuenta como «antes bien»)
    desde = (m.get("caida") or {}).get("desde")
    subprocess.run([py, str(AQUI / "tuberia.py"), "--ligero", "--solo", "e1", "--sin-avisos"], cwd=APP, env=env, capture_output=True, timeout=120)
    m2 = {x["id"]: x for x in (_j(d / "e1" / "fuentes.json") or {}).get("fuentes", [])}.get("meta", {})
    caso("Meta sigue caído en la vuelta siguiente · sigue el dato bueno y la caída conserva su «desde»",
         m2.get("clientes_con_dato") == 28 and m2.get("estado") == "dato_viejo" and (m2.get("caida") or {}).get("desde") == desde, m2)
    caso("tubería · sin temporales sueltos", not list(d.rglob("*.tubtmp")))


def _copia_generadores(tmp):
    """Copia mínima de la app para correr Captación y Bandeja (los generadores calculan sus rutas desde su fichero)."""
    raiz = tmp / "proj"
    app = raiz / "30_APP_PROTOTIPO"
    for rel in ("config.py", "escaner_secretos.py"):
        (app / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(APP / rel, app / rel)
    # R16: generar_captacion.py importa fuentes_objetivos (A4); sin él, la copia fallaba al importar y el caso «todas las
    # cuentas de Meta en error» no llegaba a correr (y el de «no cae a 0» pasaba por ese mismo fallo, no por su guarda).
    for carpeta in ("fuentes_captacion", "fuentes_bandeja", "fuentes_objetivos"):
        if (APP / carpeta).exists():
            shutil.copytree(APP / carpeta, app / carpeta, ignore=shutil.ignore_patterns("__pycache__"))
    for rel in ("personas.json", "asignaciones.json", "clientes.json"):
        (app / "data").mkdir(exist_ok=True)
        if (DATA / rel).exists():
            shutil.copy2(DATA / rel, app / "data" / rel)
    for carpeta in ("clientes", "verdad", "crm", "captacion", "bandeja", "objetivos"):
        if (DATA / carpeta).exists():
            shutil.copytree(DATA / carpeta, app / "data" / carpeta, ignore=shutil.ignore_patterns("_privado"))
    (raiz / "20_FASE2_CAPTACION").mkdir(parents=True)
    origen = APP.parent / "20_FASE2_CAPTACION" / "captacion.json"
    if origen.exists():
        shutil.copy2(origen, raiz / "20_FASE2_CAPTACION" / "captacion.json")
    return app


def _sol_generadores(tmp, caso):
    app = _copia_generadores(tmp)
    py = sys.executable
    env = {**os.environ, **SIN_RED, "RO_ESTADO_DIR": str(tmp / "gen_estado")}
    env.pop("RO_SECRETOS_DIR", None)
    band = app / "data/bandeja/bandeja.json"
    # Desk caído con una salida anterior en vivo MÁS NUEVA que el panel → la Bandeja se queda con esa
    b = _j(band) or {}
    hora_vivo = datetime.now().strftime("%Y-%m-%d %H:%M")
    b.setdefault("fuentes", {})["desk"] = {"fuente": "Zoho Desk", "plan": "en vivo", "hora": hora_vivo, "estado": "bien"}
    b["correos"] = (b.get("correos") or [])[:7]
    if b["correos"]:
        b["correos"][0]["asunto"] = "MARCA_DE_LA_LECTURA_EN_VIVO"
    band.write_text(json.dumps(b, ensure_ascii=False))
    r = subprocess.run([py, "fuentes_bandeja/generar_bandeja.py"], cwd=app, env=env, capture_output=True, text=True, timeout=300)
    o = _j(band) or {}
    dk = (o.get("fuentes") or {}).get("desk") or {}
    caso("Desk caído · la Bandeja vuelve al dato bueno MÁS RECIENTE (no al del panel)",
         r.returncode == 0 and dk.get("plan") == "último dato bueno de la app" and dk.get("hora") == hora_vivo
         and any(c.get("asunto") == "MARCA_DE_LA_LECTURA_EN_VIVO" for c in o.get("correos", [])) and len(o.get("correos", [])) == len(b["correos"]),
         {k: dk.get(k) for k in ("plan", "hora", "estado")})
    caso("Desk caído · estado «dato_viejo» y «hora_error» para la tubería", dk.get("estado") == "dato_viejo" and bool(dk.get("hora_error")))
    # Desk caído con la salida anterior MÁS VIEJA que el panel → el panel
    b["fuentes"]["desk"]["hora"] = "2026-01-01 00:00"
    band.write_text(json.dumps(b, ensure_ascii=False))
    subprocess.run([py, "fuentes_bandeja/generar_bandeja.py"], cwd=app, env=env, capture_output=True, text=True, timeout=300)
    dk = ((_j(band) or {}).get("fuentes") or {}).get("desk") or {}
    caso("Desk caído · si el panel es más nuevo, el panel", dk.get("plan") == "fichero del panel" and bool(dk.get("hora_error")), dk.get("plan"))
    subprocess.run([py, "fuentes_bandeja/generar_bandeja.py", "--ficheros"], cwd=app, env=env, capture_output=True, text=True, timeout=300)
    dk = ((_j(band) or {}).get("fuentes") or {}).get("desk") or {}
    caso("Bandeja sin red a propósito (--ficheros) · no es un error", not dk.get("hora_error"))
    # Zadarma caído con unas llamadas anteriores MÁS NUEVAS que el crudo del panel → se queda con esas
    b = _j(band) or {}
    b["fuentes"]["zadarma"] = {"fuente": "Zadarma", "plan": "en vivo", "hora": hora_vivo, "estado": "bien"}
    b["llamadas"] = [{"id": "z-prueba", "canal": "llamada", "cliente_id": None, "numero_oculto": "··· 000000", "llamadas": 2,
                      "intentos_nuestros": 0, "ultima": hora_vivo, "primera": hora_vivo, "dias_laborables": 0, "horas": 0,
                      "gravedad": "verde", "dia": hora_vivo[:10], "persona_id": "mili", "account": "sin cliente", "account_id": None}]
    band.write_text(json.dumps(b, ensure_ascii=False))
    subprocess.run([py, "fuentes_bandeja/generar_bandeja.py"], cwd=app, env=env, capture_output=True, text=True, timeout=300)
    o2 = _j(band) or {}
    zk = (o2.get("fuentes") or {}).get("zadarma") or {}
    caso("Zadarma caído · la Bandeja vuelve a sus llamadas de la vuelta anterior (no al panel)",
         zk.get("plan") == "último dato bueno de la app" and zk.get("hora") == hora_vivo and bool(zk.get("hora_error"))
         and [x.get("id") for x in o2.get("llamadas", [])] == ["z-prueba"], {k: zk.get(k) for k in ("plan", "hora")})
    # Meta caído (token caducado y sin red) en anuncios_meta.py → sale con error y NO toca anuncios.json
    anu = app / "fuentes_captacion/anuncios.json"
    antes = _md5(anu)
    r = subprocess.run([py, "fuentes_captacion/anuncios_meta.py"], cwd=app, env=env, capture_output=True, text=True, timeout=300)
    caso("Meta caído · anuncios_meta.py sale con error y conserva anuncios.json", r.returncode != 0 and _md5(anu) == antes,
         (r.stdout + r.stderr).strip().splitlines()[-1:] if (r.stdout + r.stderr).strip() else r.returncode)
    # Captación: la lectura de Meta llega vacía → no cae a 0, se queda el último dato bueno y sale con error
    capf = app.parent / "20_FASE2_CAPTACION" / "captacion.json"
    cap_bueno = capf.read_text() if capf.exists() else None
    salida = app / "data/captacion/captacion.json"
    if cap_bueno and salida.exists():
        c = json.loads(cap_bueno)
        c["clientes"] = []
        capf.write_text(json.dumps(c))
        antes = _md5(salida)
        r = subprocess.run([py, "fuentes_captacion/generar_captacion.py"], cwd=app, env=env, capture_output=True, text=True, timeout=300)
        caso("Meta caído · Captación no cae a 0 clientes (sale con error y conserva su dato)",
             r.returncode != 0 and _md5(salida) == antes and "SIN DATO" in (r.stdout + r.stderr),      # R16: por su guarda, no por un fallo al importar
             (r.stdout + r.stderr).strip().splitlines()[-1:])
        # todas las cuentas de Meta con error → la fuente sale «caida» con su hora de error
        c = json.loads(cap_bueno)
        for x in c["clientes"]:
            if (x.get("meta") or {}).get("cuenta_id"):
                x["meta"]["error"] = "Error validating access token: Session has expired"
        capf.write_text(json.dumps(c))
        r = subprocess.run([py, "fuentes_captacion/generar_captacion.py"], cwd=app, env=env, capture_output=True, text=True, timeout=300)
        fm = next((x for x in ((_j(salida) or {}).get("fuentes") or []) if x.get("id") == "meta"), {})
        caso("Meta con todas las cuentas en error · Captación marca la fuente «caida» con hora_error",
             r.returncode == 0 and fm.get("estado") == "caida" and bool(fm.get("hora_error")), {k: fm.get(k) for k in ("estado", "error", "hora_error")})
        capf.write_text(cap_bueno)
    else:
        caso("Captación · copia de captacion.json disponible", False, "falta 20_FASE2_CAPTACION/captacion.json o data/captacion")


def _sol_generar_datos(tmp, caso):
    """fuentes/generar_datos.py lanzado a mano y por la tubería con Meta caído (su lectura de Captación desaparece)."""
    raiz = tmp / "gd" / "proj"
    app = raiz / "30_APP_PROTOTIPO"
    app.mkdir(parents=True)
    for rel in ("config.py", "escaner_secretos.py"):
        shutil.copy2(APP / rel, app / rel)
    shutil.copytree(APP / "fuentes", app / "fuentes", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(DATA, app / "data", ignore=shutil.ignore_patterns("paneles", "_privado"))
    if (APP.parent / "20_FASE2_CAPTACION").exists():
        shutil.copytree(APP.parent / "20_FASE2_CAPTACION", raiz / "20_FASE2_CAPTACION")
    py = sys.executable
    env = {**os.environ, **SIN_RED, "RO_ESTADO_DIR": str(tmp / "gd" / "est")}
    gd = str(app / "fuentes" / "generar_datos.py")
    # base coherente con la copia (lo que la copia no trae, aceptado a propósito)
    r = subprocess.run([py, gd], cwd=app, env=env, capture_output=True, text=True, timeout=600)
    if r.returncode == 4:
        import tuberia as TUB
        ids = ",".join(c[0] for c in TUB.caidas_del_generador((r.stdout + r.stderr).splitlines()))
        r = subprocess.run([py, gd, "--aceptar-caida", ids], cwd=app, env=env, capture_output=True, text=True, timeout=600)
    fu = app / "data" / "fuentes.json"
    m0 = {x["id"]: x for x in (_j(fu) or {}).get("fuentes", [])}.get("meta", {})
    capf = raiz / "20_FASE2_CAPTACION" / "captacion.json"
    if r.returncode != 0 or m0.get("estado") != "bien" or not capf.exists():
        caso("generar_datos · base de la copia con Meta «bien»", False, {"código": r.returncode, "meta": m0.get("estado")})
        return
    cap = capf.read_text()
    capf.unlink()                                  # la lectura de Meta/Captación no llega
    ficha = next((f for f in sorted((app / "data" / "clientes").glob("*.json"))
                  if ((_j(f) or {}).get("fuentes", {}).get("meta") or {}).get("estado") == "bien"), None)
    r = subprocess.run([py, gd, "--en-vivo", "meta"], cwd=app, env=env, capture_output=True, text=True, timeout=600)
    m1 = {x["id"]: x for x in (_j(fu) or {}).get("fuentes", [])}.get("meta", {})
    caso("generar_datos a mano · Meta caído → sale con 4 y no sobrescribe (28 clientes con dato y su hora)",
         r.returncode == 4 and m1.get("clientes_con_dato") == m0.get("clientes_con_dato") and m1.get("hora") == m0.get("hora"),
         {"código": r.returncode, "meta": {k: m1.get(k) for k in ("estado", "clientes_con_dato", "hora")}})
    fm = ((_j(ficha) or {}).get("fuentes", {}).get("meta") or {}) if ficha else {}
    caso("generar_datos a mano · marca el último dato bueno «dato_viejo» con caída (fuentes.json y ficha)",
         m1.get("estado") == "dato_viejo" and bool((m1.get("caida") or {}).get("desde")) and fm.get("estado") == "dato_viejo"
         and bool(fm.get("datos")))
    # por la tubería: entiende el código 4 (sin reintentos, sin restaurar, aviso y sin bloquear)
    pasos = {"reintentos": {"veces": 2, "esperas_s": [0.1]}, "pasos": [
        {"id": "capa_e1", "ligero": [py, gd, "--en-vivo", "meta"], "salidas": [str(fu), str(app / "data" / "clientes")],
         "vigilar_fuentes": {"fichero": str(fu), "fichas": str(app / "data" / "clientes")}},
        {"id": "dep", "depende": ["capa_e1"], "ligero": [py, "-c", f"open({str(tmp / 'gd' / 'dep.txt')!r},'w').write('ok')"], "salidas": []}]}
    (tmp / "gd" / "pasos.json").write_text(json.dumps(pasos))
    est = tmp / "gd" / "tub"
    rt = subprocess.run([py, str(AQUI / "tuberia.py"), "--ligero", "--sin-avisos"], cwd=APP, timeout=900, capture_output=True, text=True,
                        env={**env, "RO_PASOS": str(tmp / "gd" / "pasos.json"), "RO_ESTADO_DIR": str(est), "RO_DB": str(tmp / "no_hay.db")})
    regs = sorted((est / "registros").glob("*.json"))
    pr = {x["id"]: x for x in ((_j(regs[-1]) or {}).get("pasos", []) if regs else [])}
    c1 = pr.get("capa_e1", {})
    m2 = {x["id"]: x for x in (_j(fu) or {}).get("fuentes", [])}.get("meta", {})
    caso("generar_datos en la tubería · código 4 = fuente caída: sin «bien», un solo intento, dato marcado y dependientes corren",
         rt.returncode == 1 and c1.get("ok") is False and len(c1.get("intentos", [])) == 1 and c1.get("marcados") == "lo marcó el generador"
         and m2.get("estado") == "dato_viejo" and m2.get("clientes_con_dato") == m0.get("clientes_con_dato") and (tmp / "gd" / "dep.txt").exists(),
         {"código": rt.returncode, "paso": {k: c1.get(k) for k in ("ok", "marcados", "sello")}})
    capf.write_text(cap)


ESTUB_SV = '''
import time, types, sys
sv = types.ModuleType("sv")
sv.token = lambda: "tk-falso"
def _get(tk, path, **q):
    if "get-user-campaigns" in path:
        return [{"id": 1, "campaign": "Busbac octubre", "status": "Active", "updated_at": time.time()}]
    return {"emails_sent": 10, "delivered": 9, "email_opens": 5, "link_clicks": 1, "email_replies": 1, "bounced": 1, "total_contacted": 10}
sv.get = _get
sys.modules["sv"] = sv
import runpy, os
runpy.run_path(os.environ["SNOV_PY"], run_name="__main__")
'''


def _sol_snov(tmp, caso):
    real = config.CRUDOS / "HERRAMIENTA_RO_2026-10-02"
    sn = config.HERRAMIENTAS / "snov" / "por_cliente.py"
    if not (real / "externos.json").exists() or not sn.exists():
        caso("snov · ficheros para la copia", False, "faltan externos.json o por_cliente.py")
        return
    crudos = tmp / "sn_crudos"
    (crudos / "HERRAMIENTA_RO_2026-10-02").mkdir(parents=True)
    (crudos / "PANEL_OPERACIONES_2026-10-01" / "build").mkdir(parents=True)
    shutil.copy2(real / "externos.json", crudos / "HERRAMIENTA_RO_2026-10-02" / "externos.json")
    shutil.copy2(config.PANEL_BUILD / "datos.json", crudos / "PANEL_OPERACIONES_2026-10-01" / "build" / "datos.json")
    (tmp / "arnes_snov.py").write_text(ESTUB_SV)
    out = crudos / "HERRAMIENTA_RO_2026-10-02"
    env = {**os.environ, **SIN_RED, "RO_CRUDOS": str(crudos), "SNOV_PY": str(sn), "RO_EXTERNOS_ESPERA_S": "1"}
    import fcntl
    fh = open(out / ".externos.lock", "a+")
    fcntl.flock(fh, fcntl.LOCK_EX)
    try:
        m0 = _md5(out / "externos.json")
        r = subprocess.run([sys.executable, str(tmp / "arnes_snov.py")], env=env, capture_output=True, text=True, timeout=120)
        caso("snov · con externos.py escribiendo, espera y no pisa (código 75)", r.returncode == 75 and _md5(out / "externos.json") == m0,
             (r.stderr or "")[-160:])
    finally:
        fcntl.flock(fh, fcntl.LOCK_UN)
        fh.close()
    antes = _j(out / "externos.json") or {}
    r = subprocess.run([sys.executable, str(tmp / "arnes_snov.py")], env=env, capture_output=True, text=True, timeout=120)
    d = _j(out / "externos.json") or {}
    otros = all(d.get("clientes", {}).get(k) == v for k, v in antes.get("clientes", {}).items() if k != "Busbac")
    caso("snov · escribe su outreach con bloqueo y de forma atómica, sin tocar lo demás",
         r.returncode == 0 and (d.get("clientes", {}).get("Busbac") or {}).get("outreach", {}).get("actual", {}).get("emails_sent") == 10
         and otros and not list(out.glob("*.tmp")), (r.stderr or "")[-160:])


def _sol_pegar(tmp, caso):
    """pegar.sh instalar (reinstalar la llave de GHL a mano) aparta el respaldo pendiente para que no se use el viejo."""
    real = config.HERRAMIENTAS / "ghl_agencia" / "pegar.sh"
    if not real.exists():
        caso("pegar.sh · existe", False)
        return
    casa = tmp / "casa"
    g = casa / "RO_HERRAMIENTAS" / "ghl_agencia"
    g.mkdir(parents=True)
    shutil.copy2(real, g / "pegar.sh")
    (g / "app.py").write_text("print('instalar falso')\n")          # nunca la app de verdad (abriría la autorización)
    (g / ".ghl_app_refresh_token.respaldo").write_text("llave-vieja")
    r = subprocess.run(["bash", str(g / "pegar.sh"), "instalar"], env={**os.environ, "HOME": str(casa)}, capture_output=True, text=True, timeout=30)
    caso("pegar.sh instalar · aparta el respaldo pendiente (no se usará la llave vieja)",
         r.returncode == 0 and not (g / ".ghl_app_refresh_token.respaldo").exists() and (g / ".ghl_app_refresh_token.respaldo.viejo").exists(),
         (r.stdout + r.stderr)[-160:])


ESTUB_GG = '''
import json, os
EMP = json.load(open(os.environ["EST_EMP"]))
def acceso(): return "tk-falso"
def propiedades(tk): return [{"propiedad": v["ga"], "nombre": v.get("ga_nombre") or v["ga"]} for v in EMP.values() if v.get("ga")]
def get(tk, url): return {"siteEntry": [{"siteUrl": v["gsc"]} for v in EMP.values() if v.get("gsc")]}
'''
ESTUB_MC = '''
import json, os
EMP = json.load(open(os.environ["EST_EMP"]))
def llave(s): return "falsa"
def get(path): return [{"label": v["metricool"], "id": v.get("metricool_id")} for v in EMP.values() if v.get("metricool")]
'''
ESTUB_APP = '''
import json, os
EMP = json.load(open(os.environ["EST_EMP"]))
def acceso(): return "gtk-falso", {"companyId": "co"}
def subcuentas(tk, co): return [{"id": v["ghl"], "name": v.get("ghl_nombre") or v["ghl"]} for v in EMP.values() if v.get("ghl")]
'''
ARNES_EXTERNOS = r'''
import importlib.util, json, os, sys, time
spec = importlib.util.spec_from_file_location("externos", os.environ["EXT_PY"])
ex = importlib.util.module_from_spec(spec); spec.loader.exec_module(ex)
FALLA = set(filter(None, os.environ.get("FALLA_GSC", "").split("|")))
OTRO = os.environ.get("ESCRIBE_OTRO")          # simula otro proceso (Snov) que escribe externos.json a mitad de vuelta
hecho = []
def post_json(tk, url, body):
    if OTRO and not hecho:
        f = os.path.join(ex.OUT, "externos.json"); d = json.load(open(f))
        d["clientes"].setdefault(OTRO, {})["outreach"] = {"marca": "escrito a mitad de vuelta"}
        json.dump(d, open(f, "w")); hecho.append(1)
    if "webmasters" in url:
        if any(s and ex.urllib.parse.quote(s, safe="") in url for s in FALLA):
            return {"_error": 401, "_msg": "Request had invalid authentication credentials"}
        if body.get("dimensions") == ["date"]:
            return {"rows": [{"keys": ["2026-09-29"], "clicks": 1, "impressions": 10}]}
        if body.get("dimensions") == ["query"]:
            return {"rows": []}
        return {"rows": [{"clicks": 999, "impressions": 9999, "ctr": 0.1, "position": 5.0}]}
    return {"rows": [{"metricValues": [{"value": "1"}] * 7}]}
ex.post_json = post_json
ex.mc_get = lambda *a, **k: None
ex.ghl_sub = lambda *a, **k: {"contactos": 1}
sys.exit(ex.main(sys.argv[1:]))
'''


def _sol_externos(tmp, caso):
    real = config.CRUDOS / "HERRAMIENTA_RO_2026-10-02"
    panel = config.PANEL_BUILD / "datos.json"
    ext_py = config.HERRAMIENTAS / "externos.py"
    if not (real / "externos.json").exists() or not panel.exists() or not ext_py.exists():
        caso("externos.py · ficheros para la copia", False, "faltan externos.json, el panel o externos.py")
        return
    crudos = tmp / "crudos"
    (crudos / "HERRAMIENTA_RO_2026-10-02").mkdir(parents=True)
    (crudos / "PANEL_OPERACIONES_2026-10-01" / "build").mkdir(parents=True)
    for n in ("externos.json", "emparejamientos.json", "emparejamientos_manual.json"):
        if (real / n).exists():
            shutil.copy2(real / n, crudos / "HERRAMIENTA_RO_2026-10-02" / n)
    shutil.copy2(panel, crudos / "PANEL_OPERACIONES_2026-10-01" / "build" / "datos.json")
    herr = tmp / "herr"
    for sub, cod in (("google/gg.py", ESTUB_GG), ("metricool/mc.py", ESTUB_MC), ("ghl_agencia/app.py", ESTUB_APP)):
        (herr / sub).parent.mkdir(parents=True, exist_ok=True)
        (herr / sub).write_text(cod)
    (tmp / "arnes_externos.py").write_text(ARNES_EXTERNOS)
    out = crudos / "HERRAMIENTA_RO_2026-10-02"
    env = {**os.environ, **SIN_RED, "RO_CRUDOS": str(crudos), "RO_HERRAMIENTAS": str(herr), "EXT_PY": str(ext_py),
           "EST_EMP": str(out / "emparejamientos.json")}
    antes = _j(out / "externos.json")
    emp_antes = _j(out / "emparejamientos.json") or {}
    sitios = {"Asetra": "https://asetra.net/", "Musashi Consultores": "https://musashi.es/", "Greconsult": "https://www.greconsult.com/",
              "Busbac": "https://busbac.es/"}
    # 1 · vuelta completa con Search Console de Asetra en 401: conserva su dato bueno; el resto se actualiza
    r = subprocess.run([sys.executable, str(tmp / "arnes_externos.py")], env={**env, "FALLA_GSC": sitios["Asetra"]},
                       capture_output=True, text=True, timeout=300)
    d = _j(out / "externos.json") or {}
    cl = d.get("clientes", {})
    a_gsc, a_gsc0 = (cl.get("Asetra") or {}).get("gsc") or {}, ((antes or {}).get("clientes", {}).get("Asetra") or {}).get("gsc") or {}
    caso("externos · error 401 de Google: conserva el último dato bueno de esa fuente con hora_error",
         r.returncode == 0 and a_gsc.get("actual") == a_gsc0.get("actual") and a_gsc.get("error") == 401 and bool(a_gsc.get("hora_error")),
         (r.stderr or "")[-200:] if r.returncode else {k: a_gsc.get(k) for k in ("error", "hora_error")})
    caso("externos · las otras fuentes sí se actualizan", ((cl.get("Busbac") or {}).get("gsc") or {}).get("actual", {}).get("clics") == 999)
    emp = _j(out / "emparejamientos.json") or {}
    caso("externos · Search Console de Asetra, Musashi, Greconsult y Busbac sin pisar",
         all((emp.get(k) or {}).get("gsc") == v for k, v in sitios.items()), {k: (emp.get(k) or {}).get("gsc") for k in sitios})
    con_outreach = [k for k, v in ((antes or {}).get("clientes") or {}).items() if "outreach" in v]
    caso("externos · la vuelta completa conserva lo que añade Snov (outreach)", all("outreach" in cl.get(k, {}) for k in con_outreach), len(con_outreach))
    caso("externos · escritura atómica (sin temporales sueltos)", not list(out.glob("*.tmp")))
    sys.path.insert(0, str(AQUI))
    import tuberia as TUB
    errs = TUB.errores_de_fuente([str(out / "externos.json")], datetime.now().replace(hour=0, minute=0))
    caso("externos · la tubería cuenta el _error de Google como fallo de esa fuente", "gsc" in errs, errs)
    # 2 · vuelta parcial (solo Busbac) mientras otro proceso escribe: mezcla con el fichero ACTUAL
    antes2 = _j(out / "externos.json") or {}
    r = subprocess.run([sys.executable, str(tmp / "arnes_externos.py"), "Busbac"], env={**env, "ESCRIBE_OTRO": "Asetra"},
                       capture_output=True, text=True, timeout=300)
    d2 = _j(out / "externos.json") or {}
    c2 = d2.get("clientes", {})
    otros_iguales = all(c2.get(k) == v for k, v in antes2.get("clientes", {}).items() if k not in ("Busbac", "Asetra"))
    caso("externos · vuelta parcial: mezcla con el fichero actual (no con el del principio)",
         r.returncode == 0 and (c2.get("Asetra") or {}).get("outreach", {}).get("marca") == "escrito a mitad de vuelta"
         and otros_iguales and len(c2) == len(antes2.get("clientes", {})), (r.stderr or "")[-200:])
    caso("externos · vuelta parcial: el Search Console de Asetra sigue siendo su dato bueno",
         ((c2.get("Asetra") or {}).get("gsc") or {}).get("actual") == a_gsc0.get("actual"))
    # 3 · bloqueo de proceso único
    import fcntl
    fh = open(out / ".externos.lock", "a+")
    fcntl.flock(fh, fcntl.LOCK_EX)
    try:
        m0 = _md5(out / "externos.json")
        r = subprocess.run([sys.executable, str(tmp / "arnes_externos.py")], env=env, capture_output=True, text=True, timeout=120)
        caso("externos · con otro en marcha no arranca (código 75) y no toca nada", r.returncode == 75 and _md5(out / "externos.json") == m0)
    finally:
        fcntl.flock(fh, fcntl.LOCK_UN)
        fh.close()
    caso("externos · emparejamientos sin cambios de más", set(emp) == set(emp_antes) or set(emp) >= set(emp_antes))


SEGURITY_FALSO = '''#!/bin/sh
# «security» falso para la prueba: un llavero en ficheros (nunca el llavero real)
D="$LLAVERO_FALSO"; mkdir -p "$D"
case "$1" in
  find-generic-password) S=""; while [ $# -gt 0 ]; do [ "$1" = "-s" ] && S="$2"; shift; done
    [ -f "$D/$S" ] && cat "$D/$S" && exit 0; exit 44;;
  add-generic-password) [ -f "$D/FALLA" ] && exit 36; S=""; W=""
    while [ $# -gt 0 ]; do [ "$1" = "-s" ] && S="$2"; [ "$1" = "-w" ] && W="$2"; shift; done
    printf "%s" "$W" > "$D/$S"; exit 0;;
esac
exit 1
'''
ARNES_GHL = r'''
import fcntl, importlib.util, json, os, sys, time
spec = importlib.util.spec_from_file_location("app", os.environ["APP_PY"])
app = importlib.util.module_from_spec(spec); spec.loader.exec_module(app)
SRV = os.environ["GHL_FALSO"]                   # GHL falso: solo vale la ÚLTIMA llave entregada (como la de verdad)
def post(path, data, tk=None):
    with open(SRV + ".lock", "a+") as l:
        fcntl.flock(l, fcntl.LOCK_EX)
        st = json.load(open(SRV))
        valida = st["valida"]
    time.sleep(0.3)                              # ventana real entre leer la llave y gastarla
    with open(SRV + ".lock", "a+") as l:
        fcntl.flock(l, fcntl.LOCK_EX)
        st = json.load(open(SRV))
        if data.get("refresh_token") != st["valida"]:
            sys.exit("GHL responde 400 en /oauth/token: invalid_grant")
        st["n"] += 1; st["valida"] = f"r-{st['n']}"; json.dump(st, open(SRV, "w"))
        return {"refresh_token": st["valida"], "access_token": f"a-{st['n']}", "companyId": "co"}
app.post = post
tk, est = app.acceso()
print("ok", tk)
'''


def _sol_llave_ghl(tmp, caso):
    real = config.HERRAMIENTAS / "ghl_agencia" / "app.py"
    if not real.exists():
        caso("llave de GHL · app.py", False, "no existe")
        return
    d = tmp / "ghl"
    (d / "ghl_agencia").mkdir(parents=True)
    shutil.copy2(real, d / "ghl_agencia" / "app.py")
    (d / "bin").mkdir()
    (d / "bin" / "security").write_text(SEGURITY_FALSO)
    os.chmod(d / "bin" / "security", 0o755)
    (d / "arnes.py").write_text(ARNES_GHL)
    llav = d / "llavero"
    llav.mkdir()
    for k, v in (("ghl_app_client_id", "id"), ("ghl_app_client_secret", "secreto"), ("ghl_app_refresh_token", "r-0")):
        (llav / k).write_text(v)
    srv = d / "ghl_falso.json"
    srv.write_text(json.dumps({"valida": "r-0", "n": 0}))
    env = {**os.environ, **SIN_RED, "PATH": f"{d / 'bin'}:{os.environ.get('PATH', '')}", "LLAVERO_FALSO": str(llav),
           "APP_PY": str(d / "ghl_agencia" / "app.py"), "GHL_FALSO": str(srv), "RO_GHL_ESPERA_S": "60"}
    for k in ("RO_SECRETOS_DIR", "RO_GHL_BLOQUEO", "RO_GHL_BLOQUEO_HEREDADO", "GHL_APP_REFRESH_TOKEN"):
        env.pop(k, None)

    def a_la_vez(n, extra=None):
        procs = [subprocess.Popen([sys.executable, str(d / "arnes.py")], env={**env, **(extra or {})},
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for _ in range(n)]
        return [p.wait(timeout=120) for p in procs]
    codigos = a_la_vez(6)
    st = _j(srv)
    caso("llave de GHL · 6 procesos a la vez FUERA de la tubería: ninguno pierde la llave",
         codigos == [0] * 6 and st["n"] == 6 and (llav / "ghl_app_refresh_token").read_text() == st["valida"], {"códigos": codigos, "rotaciones": st["n"]})
    # control: sin el bloqueo (simulado con un «heredado» falso) la carrera existe → así se sabe que la prueba muerde
    (d / "ghl_agencia" / ".llave.lock").write_text(f"{os.getpid()} control\n")
    codigos_sin = a_la_vez(4, {"RO_GHL_BLOQUEO_HEREDADO": str(os.getpid())})
    srv.write_text(json.dumps({"valida": (llav / "ghl_app_refresh_token").read_text(), "n": 100}))
    caso("llave de GHL · control: sin bloqueo, la carrera pierde llaves (la prueba muerde)", any(c != 0 for c in codigos_sin), codigos_sin)
    # el llavero falla justo después de rotar → la llave nueva queda en el respaldo 0600 y la siguiente vuelta la usa
    (llav / "FALLA").write_text("1")
    r1 = subprocess.run([sys.executable, str(d / "arnes.py")], env=env, capture_output=True, text=True, timeout=60)
    resp = d / "ghl_agencia" / ".ghl_app_refresh_token.respaldo"
    st = _j(srv)
    ok1 = r1.returncode == 0 and resp.exists() and resp.read_text() == st["valida"] and oct(resp.stat().st_mode & 0o777) == "0o600"
    (llav / "FALLA").unlink()
    r2 = subprocess.run([sys.executable, str(d / "arnes.py")], env=env, capture_output=True, text=True, timeout=60)
    st = _j(srv)
    caso("llave de GHL · si el llavero falla, la llave nueva ya estaba guardada (respaldo 0600) y la siguiente vuelta sigue",
         ok1 and r2.returncode == 0 and (llav / "ghl_app_refresh_token").read_text() == st["valida"] and not resp.exists(),
         (r1.stderr + r2.stderr)[-200:])
    # la tubería presta la llave: su paso usa app.acceso() sin esperarse a sí mismo, y uno de fuera espera su turno
    import llave_ghl as LG
    import estado as ES
    estado_real = config.ESTADO_DIR
    config.ESTADO_DIR = tmp / "ghl_estado"          # sus bloqueos, en la carpeta de la prueba (nunca en despliegue/estado)
    E = ES.SQLite(tmp / "ghl_estado.db")
    config.ESTADO_DIR = estado_real
    env_t = {**env, "RO_GHL_BLOQUEO": str(d / "ghl_agencia" / ".llave.lock")}
    os.environ["RO_GHL_BLOQUEO"] = env_t["RO_GHL_BLOQUEO"]
    try:
        with LG.prestar(E) as extra:
            r_paso = subprocess.run([sys.executable, str(d / "arnes.py")], env={**env_t, **extra}, capture_output=True, text=True, timeout=60)
            r_fuera = subprocess.run([sys.executable, str(d / "arnes.py")], env={**env_t, "RO_GHL_ESPERA_S": "1"},
                                     capture_output=True, text=True, timeout=60)
    finally:
        os.environ.pop("RO_GHL_BLOQUEO", None)
    caso("llave de GHL · dentro de la tubería el paso no se bloquea a sí mismo", r_paso.returncode == 0, r_paso.stderr[-160:])
    caso("llave de GHL · fuera de la tubería, otro proceso espera y no la gasta", r_fuera.returncode != 0 and "en uso" in (r_fuera.stderr + r_fuera.stdout),
         (r_fuera.stderr + r_fuera.stdout)[-160:])


def _sol_envios(tmp, caso):
    """Envíos verificados (3-oct): la prueba de extremo a extremo con un proveedor SIMULADO (despliegue/verificar_envios.py
    --prueba-e2e, sobre una copia de la base en su carpeta temporal) y que hoy no hay ningún envío real activo."""
    r = subprocess.run([sys.executable, str(AQUI / "verificar_envios.py"), "--prueba-e2e", "--json"], cwd=APP, capture_output=True, text=True, timeout=300,
                       env={k: v for k, v in os.environ.items() if k != "RO_ENVIOS_REALES"})
    try:
        d = json.loads((r.stdout.strip().splitlines() or ["{}"])[-1])
    except ValueError:
        d = {}
    for c in d.get("casos") or []:
        caso(f"envíos · {c['caso']}", c["ok"], c.get("detalle"))
    caso("envíos · la prueba de extremo a extremo corre entera", r.returncode == 0 and d.get("casos"), (r.stdout + r.stderr)[-300:])
    sys.path.insert(0, str(APP))
    import envios as EN
    it = EN.interruptor()
    caso("envíos · hoy NINGÚN canal con envío real (interruptor apagado)", not it["reales"] and not it["fichero"], it)


def _sol_sincronia(tmp, caso):
    """Sincronía con ClickUp (3-oct): la prueba de extremo a extremo con un ClickUp SIMULADO (despliegue/reconciliar_clickup.py
    --prueba-e2e, sobre una copia de la base en su carpeta temporal) y que hoy ClickUp real y el puente de chat están apagados."""
    r = subprocess.run([sys.executable, str(AQUI / "reconciliar_clickup.py"), "--prueba-e2e", "--json"], cwd=APP, capture_output=True, text=True, timeout=300,
                       env={k: v for k, v in os.environ.items() if k not in ("RO_CLICKUP_REAL", "RO_SINC_PUENTE_MODO")})
    try:
        d = json.loads((r.stdout.strip().splitlines() or ["{}"])[-1])
    except ValueError:
        d = {}
    for c in d.get("casos") or []:
        caso(f"sincronía · {c['caso']}", c["ok"], c.get("detalle"))
    caso("sincronía · la prueba de extremo a extremo corre entera", r.returncode == 0 and d.get("casos"), (r.stdout + r.stderr)[-300:])
    sys.path.insert(0, str(APP))
    import sincronia as SI
    it = SI.interruptor()
    caso("sincronía · hoy ClickUp real APAGADO y puente de chat apagado", not it["reales"] and not it["fichero"] and it["chat_puente"] == "apagado", it)


def solidez():
    tmp = Path(tempfile.mkdtemp(prefix="ro_solidez_"))
    os.chmod(tmp, 0o700)
    casos = []

    def caso(nombre, ok, detalle=None):
        casos.append({"caso": nombre, "ok": bool(ok), "detalle": None if ok else sanear_detalle(detalle)})
        print(f"  {'✔' if ok else '✘'} {nombre}" + ("" if ok else f" · {sanear_detalle(detalle)}"))
    try:
        for parte in (_sol_tuberia, _sol_generadores, _sol_generar_datos, _sol_externos, _sol_snov, _sol_llave_ghl, _sol_pegar, _sol_envios, _sol_sincronia):
            try:
                parte(tmp, caso)
            except Exception as e:
                caso(f"{parte.__name__} sin excepciones", False, f"{type(e).__name__}: {e}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    malos = [c for c in casos if not c["ok"]]
    informe["solidez"] = {"casos": casos, "fallos": len(malos)}
    print(f"  {'✔' if not malos else '✘'} solidez: {len(casos) - len(malos)} de {len(casos)} casos bien")
    return not malos


# ------------------------------------------------------------------ 6 · N11 · conexiones sin fallos (2-oct-2026)
# Sin tocar herramientas externas: los reintentos se prueban contra un servidor falso en 127.0.0.1; la salud de las
# conexiones se lee del fichero que dejó la última vuelta y los fallos se PROVOCAN con conexiones falsas en memoria.
def n11(con_servidor=True):
    import http.server
    import importlib.util
    import threading
    import urllib.error as UE
    casos = []

    def caso(nombre, ok, detalle=None):
        casos.append({"caso": nombre, "ok": bool(ok), "detalle": None if ok else sanear_detalle(detalle)})
        print(f"  {'✔' if ok else '✘'} {nombre}" + ("" if ok else f" · {sanear_detalle(detalle)}"))

    tmp = Path(tempfile.mkdtemp(prefix="ro_n11_"))
    os.chmod(tmp, 0o700)
    try:
        # --- 1 · red_segura: reintenta lecturas ante 429/5xx/tiempo, nunca escrituras ni 401
        sys.path.insert(0, str(config.HERRAMIENTAS))
        import red_segura as RS
        cuenta = {}

        class Falso(http.server.BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _responder(self):
                cuenta[self.path] = cuenta.get(self.path, 0) + 1
                n = cuenta[self.path]
                if self.path == "/fallo2" and n <= 2 or self.path in ("/siempre503", "/post503"):
                    self.send_response(503); self.end_headers(); return
                if self.path == "/429" and n == 1:
                    self.send_response(429); self.send_header("Retry-After", "1"); self.end_headers(); return
                if self.path == "/401":
                    self.send_response(401); self.end_headers(); return
                if self.path == "/lento":
                    time.sleep(1.2)
                cuerpo = b'{"ok": 1}'
                self.send_response(200); self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(cuerpo))); self.end_headers(); self.wfile.write(cuerpo)
            do_GET = do_POST = _responder

        srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Falso)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        u = f"http://127.0.0.1:{srv.server_address[1]}"
        try:
            r = json.loads(RS.abrir(u + "/fallo2", timeout=5, base_s=0.1).read())
            caso("N11 · lectura con dos 503 seguidos: reintenta y responde", r == {"ok": 1} and cuenta["/fallo2"] == 3, cuenta)
            t0 = time.time()
            r = json.loads(RS.abrir(u + "/429", timeout=5, base_s=0.1).read())
            caso("N11 · 429 con Retry-After: espera lo que pide la API y responde", r == {"ok": 1} and time.time() - t0 >= 0.9, round(time.time() - t0, 2))
            t0 = time.time()
            try:
                RS.abrir(u + "/siempre503", timeout=5, base_s=0.5, tope_s=2)
                caso("N11 · caída continua: se rinde dentro del tope de tiempo", False, "no lanzó error")
            except UE.HTTPError as e:
                caso("N11 · caída continua: se rinde dentro del tope de tiempo con el error real", e.code == 503 and time.time() - t0 < 4, round(time.time() - t0, 2))
            try:
                RS.abrir(__import__("urllib.request").request.Request(u + "/post503", data=b"x", method="POST"), timeout=5, base_s=0.1)
            except UE.HTTPError:
                pass
            caso("N11 · una escritura (POST) NUNCA se reintenta", cuenta.get("/post503") == 1, cuenta.get("/post503"))
            try:
                RS.abrir(u + "/401", timeout=5, base_s=0.1)
            except UE.HTTPError:
                pass
            caso("N11 · 401 (llave mala) no se reintenta: no gasta cupo", cuenta.get("/401") == 1, cuenta.get("/401"))
            try:
                RS.abrir(u + "/lento", timeout=0.4, base_s=0.1, intentos=2)
                caso("N11 · tiempo agotado: reintenta y se rinde", False, "no lanzó error")
            except Exception as e:  # noqa: BLE001
                time.sleep(1.5)
                caso("N11 · tiempo agotado: reintenta una vez y se rinde con el error de red", cuenta.get("/lento") == 2, f"{type(e).__name__} {cuenta.get('/lento')}")
        finally:
            srv.shutdown()

        # --- 2 · lectores parcheados (copia .antes_n11) y la rotación de GHL sin reintento
        lectores = ["zoho/zh.py", "google/gg.py", "meta/mt.py", "metricool/mc.py", "seranking/sr.py", "holded/hd.py", "snov/sv.py",
                    "zoom/zm.py", "windsor/ws.py", "ghl_agencia/ga.py", "ghl_agencia/app.py", "clickup_api/chat.py", "google/gads.py",
                    "zoho/zbookings.py", "externos.py", "zadarma/zd.py"]
        sin = [x for x in lectores if "_abrir(" not in (config.HERRAMIENTAS / x).read_text() or not (config.HERRAMIENTAS / (x + ".antes_n11")).exists()]
        caso(f"N11 · {len(lectores)} lectores con reintentos de lectura y su copia .antes_n11", not sin, sin)
        app = (config.HERRAMIENTAS / "ghl_agencia/app.py").read_text()
        post_app = app[app.index("def post(path"):app.index("def get(tk, path")]
        caso("N11 · la llave de GHL que rota (app.post) se pide UNA vez: sin reintento", "urllib.request.urlopen" in post_app and "_abrir" not in post_app, post_app[:120])

        # --- 3 · caché de tokens: renueva antes de caducar (margen) y nunca devuelve el token en vida_restante
        os.environ["RO_TOKENS_DIR"] = str(tmp / "tokens")
        import cache_tokens as CT
        pedidos = []
        def refrescar():
            pedidos.append(1)
            return f"tk{len(pedidos)}", 600, None
        CT.token("prueba_n11", "id", refrescar)
        CT.token("prueba_n11", "id", refrescar)
        caso("N11 · caché: dentro del margen normal reutiliza el token (1 refresco para 2 usos)", len(pedidos) == 1, len(pedidos))
        CT.token("prueba_n11", "id", refrescar, margen_s=1200)
        vida = CT.vida_restante("prueba_n11", "id")
        caso("N11 · caché: con margen de 20 min renueva YA el que caduca en 10 (antes de caducar)", len(pedidos) == 2 and vida and 500 < vida <= 600, (len(pedidos), vida))
        os.environ.pop("RO_TOKENS_DIR", None)

        # --- 4 · salud.json real: todas las conexiones, con qué hacer y dueño, y sin secretos
        f = DATA / "conexiones" / "salud.json"
        spec = importlib.util.spec_from_file_location("salud_n11", AQUI / "salud_conexiones.py")
        argv0 = sys.argv
        sys.argv = ["salud_conexiones.py", "--sin-avisos", "--sin-red", "--salida", str(tmp / "salud.json")]
        try:
            SC = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(SC)
        finally:
            sys.argv = argv0
        ids = [c["id"] for c in SC.CONEXIONES]
        try:
            S = json.loads(f.read_text())
        except Exception as e:  # noqa: BLE001
            S = {"conexiones": [], "error": str(e)}
        en = {c["id"]: c for c in S.get("conexiones", [])}
        caso(f"N11 · salud.json real con las {len(ids)} conexiones", set(ids) <= set(en), sorted(set(ids) - set(en)))
        vivo = S.get("en_vivo") and S.get("generado") and datetime.strptime(S["generado"], "%Y-%m-%d %H:%M") > datetime.now() - timedelta(hours=26)
        caso("N11 · salud.json probado en vivo en las últimas 26 h", vivo, S.get("generado"))
        malas = [c["id"] for c in en.values() if c.get("color") != "verde" and c.get("color") != "gris" and not (c.get("que_hacer") and c.get("quien"))]
        caso("N11 · cada conexión que no está en verde dice qué hacer y quién", not malas, malas)
        sin_campos = [c["id"] for c in en.values() if not all(k in c for k in ("color", "desde", "ultimo_ok", "ms", "caduca", "historial"))]
        caso("N11 · cada conexión lleva color, desde, último OK, tiempo y caducidad", not sin_campos, sin_campos)
        sys.path.insert(0, str(APP))
        import escaner_secretos as ESC
        hall = ESC.escanear_fichero(f) if f.exists() else ["no existe"]
        caso("N11 · salud.json pasa la puerta de secretos", not hall, hall[:3])

        # --- 5 · sin red: no llama a nada y conserva lo último probado
        if f.exists():
            shutil.copy2(f, tmp / "salud.json")
        sys.argv = ["salud_conexiones.py", "--sin-avisos", "--sin-red", "--salida", str(tmp / "salud.json")]
        try:
            SC2 = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(SC2)
            SC2.main()
        finally:
            sys.argv = argv0
        S2 = json.loads((tmp / "salud.json").read_text())
        grises = [c["id"] for c in S2["conexiones"] if c["color"] == "gris" and en.get(c["id"], {}).get("color") not in (None, "gris")]
        caso("N11 · vuelta sin red: no llama y conserva el color de la última prueba", not grises and not S2["en_vivo"], grises)

        # --- 6 · fallos provocados: color, dueño correcto y alerta con escalado (instancia CON red: las pruebas son falsas)
        sys.argv = ["salud_conexiones.py", "--sin-avisos", "--salida", str(tmp / "salud_falsa.json")]
        try:
            SC = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(SC)
        finally:
            sys.argv = argv0
        def falsa(cid, critica, error):
            def prueba():
                raise error
            return dict(id=cid, nombre=f"Falsa {cid}", grupo="Prueba", icono="plug", llaves=[], prueba=prueba, dueno="tomas", critica=critica,
                        que_da="", modulos="", renovar={"url": "https://ejemplo.invalid/", "donde": "consola"}, pegar="bash pegar.sh", caducidad="—")
        f503 = SC.evaluar(falsa("caida", True, UE.HTTPError("x", 503, "caída", {}, None)))
        f401 = SC.evaluar(falsa("llave", True, UE.HTTPError("x", 401, "no", {}, None)))
        fno = SC.evaluar(falsa("nousada", False, UE.HTTPError("x", 503, "caída", {}, None)))
        fred = SC.evaluar(falsa("red", True, UE.URLError("sin red")))
        caso("N11 · caída del proveedor (503) en una que la app usa → rojo y a Agus (técnico)", f503["color"] == "rojo" and f503["quien_id"] == "agustina", f503)
        caso("N11 · llave caducada (401) → rojo y al dueño de la llave (Tomás) con el paso de pegar.sh", f401["color"] == "rojo" and f401["quien_id"] == "tomas" and "pegar.sh" in f401["que_hacer"], f401)
        caso("N11 · caída de algo que hoy no se usa → ámbar, no rojo", fno["color"] == "ambar", fno["color"])
        caso("N11 · sin red → rojo, técnico, error en llano", fred["color"] == "rojo" and fred["quien_id"] == "agustina" and "conexión" in fred["error_llano"], fred)
        for x in (f503, f401):
            x.update({"desde": "2026-10-02 10:00", "titular": x["titular"]})
        al = SC.alertas_n4([f503, f401, fno])
        caso("N11 · alertas en formato N4: solo las que la app usa, con dueño y escalado dueño → jefe → Tomás",
             len(al) == 2 and al[0]["escalado_cadena"] == ["agustina", "mili", "tomas"] and al[1]["dueno_id"] == "tomas" and al[0]["ir"] == "#/ajustes/conexiones", al)
        llave = dict(falsa("sinllave", True, None), llaves=["llave_que_no_existe_n11"])
        fs = SC.evaluar(llave)
        caso("N11 · falta la llave → «falta la llave · lo hace Tomás»", fs["estado"] == "falta_clave" and "lo hace Tomás" in fs["detalle"], fs)

        # --- 7 · tubería: la salud es lo primero de cada vuelta
        import tuberia as TU
        cfg = json.loads((AQUI / "pasos.json").read_text())
        primeros = {m: [x[0]["id"] for x in TU.plan(cfg, m, False) if x[1]][:1] for m in ("ligero", "completo")}
        primeros["crudo"] = [x[0]["id"] for x in TU.plan(cfg, "ligero", True) if x[1]][:1]
        caso("N11 · salud_conexiones es el primer paso en las vueltas ligera, completa y sin red", all(v == ["salud_conexiones"] for v in primeros.values()), primeros)

        # --- 8 · permisos: solo dirección, operaciones y técnico
        if con_servidor:
            personas = json.loads((DATA / "personas.json").read_text())
            P = personas if isinstance(personas, list) else personas.get("personas", [])
            dentro = {pu: next((x["id"] for x in P if pu in x.get("puestos", []) and x.get("activo", True)), None) for pu in ("direccion", "operaciones", "tecnico_altas")}
            fuera = [x["id"] for x in P if x.get("activo", True) and x.get("puestos") and not set(x["puestos"]) & {"direccion", "operaciones", "tecnico_altas"}][:4]
            res = {k: get("/api/modulo/conexiones/salud", v) for k, v in dentro.items() if v}
            res_fuera = {v: get("/api/modulo/conexiones/salud", v) for v in fuera}
            caso("N11 · dirección, operaciones y técnico leen la salud de conexiones (200)", res and all(v == 200 for v in res.values()), res)
            caso("N11 · el resto de puestos no la recibe (403)", res_fuera and all(v == 403 for v in res_fuera.values()), res_fuera)
    except Exception as e:  # noqa: BLE001
        caso("N11 sin excepciones", False, f"{type(e).__name__}: {e}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    malos = [c for c in casos if not c["ok"]]
    informe["n11"] = {"casos": casos, "fallos": len(malos)}
    print(f"  {'✔' if not malos else '✘'} N11 conexiones: {len(casos) - len(malos)} de {len(casos)} casos bien")
    return not malos


def sanear_detalle(x):
    t = json.dumps(x, ensure_ascii=False, default=str) if not isinstance(x, str) else x
    t = re.sub(r"[\w.+-]+@[\w-]+(\.[\w-]+)+", "[correo]", t or "")
    return re.sub(r"\+?\d[\d\s.-]{8,}\d", "[número]", t)[:300]


def main():
    if "--solo-n11" in ARGS:   # N11: solo la sección de conexiones (con su propio servir.py de pruebas para los permisos)
        tmp = Path(tempfile.mkdtemp(prefix="ro_noche_"))
        proc = arrancar_servidor(tmp)
        try:
            ok = n11()
        finally:
            proc.terminate()
            shutil.rmtree(tmp, ignore_errors=True)
        return 0 if ok else 1
    if "--solo-solidez" in ARGS:
        print(f"Solidez · {informe['inicio']} · sobre copias en una carpeta temporal")
        return 0 if solidez() else 1
    tmp = Path(tempfile.mkdtemp(prefix="ro_noche_"))
    if os.environ.get("DATABASE_URL"):   # en Render la tarea arranca vacía: lo último bueno, desde la base
        import publicacion as PUB
        for esp in ("crudos", "cache", "data"):
            PUB.bajar(esp)
    print(f"Batería nocturna · {informe['inicio']} · servir.py de pruebas en {BASE} (copia de local.db)")
    proc = arrancar_servidor(tmp)
    ok_a = ok_s = ok_n = False
    try:
        baterias(tmp)
        ok_hf = humo_y_fuga()
        ok_a = acceso_servidor(tmp)
        ok_c = cuadre()
        ok_s = solidez()
        ok_n = n11()
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except Exception:
            proc.kill()
        shutil.rmtree(tmp, ignore_errors=True)
    ok_b = all(b["estado"] in ("bien", "omitida") for b in informe["baterias"])
    informe["fin"] = datetime.now().isoformat(timespec="seconds")
    informe["resultado"] = "verde" if (ok_b and ok_hf and ok_a and ok_c and ok_s and ok_n) else "rojo"
    carpeta = config.ESTADO_DIR / "pruebas"
    carpeta.mkdir(parents=True, exist_ok=True)
    nombre = datetime.now().strftime("%Y-%m-%d_%H%M")
    (carpeta / f"{nombre}.json").write_text(json.dumps(informe, ensure_ascii=False, indent=1))
    md = [f"# Batería nocturna · {informe['inicio']} · **{informe['resultado'].upper()}**", "",
          "| Prueba | Estado | Segundos | Nota |", "|---|---|---|---|"]
    for b in informe["baterias"]:
        md.append(f"| {b['prueba']} | {b['estado']} | {b.get('segundos', '')} | {b.get('motivo') or ' · '.join(b.get('fallos') or [])[:160]} |")
    h, f, c = informe["humo"], informe["fuga"], informe["cuadre"]
    md += ["", f"**Humo:** {h['combinaciones_bien']} combinaciones módulo × puesto en 200 · {len(h['fallos'])} fallos.",
           f"**Fuga:** {f['casos']} casos puesto × fichero · {len(f['problemas'])} problemas.",
           f"**Acceso en modo servidor (E49):** {len(informe['acceso']['casos']) - informe['acceso']['fallos']} de {len(informe['acceso']['casos'])} casos bien.",
           f"**Cuadre:** " + " · ".join(f"{k} {c['comprobados'][k]} clientes, {len(v)} diferencias" for k, v in c["diferencias"].items()),
           f"**Solidez (fallos provocados sobre copias):** {len(informe.get('solidez', {}).get('casos', [])) - informe.get('solidez', {}).get('fallos', 0)} de {len(informe.get('solidez', {}).get('casos', []))} casos bien.", ""]
    md.append(f"**N11 · conexiones sin fallos:** {len(informe.get('n11', {}).get('casos', [])) - informe.get('n11', {}).get('fallos', 0)} de {len(informe.get('n11', {}).get('casos', []))} casos bien.")
    for x in informe.get("solidez", {}).get("casos", []):
        if not x["ok"]:
            md.append(f"- solidez · {x['caso']}: {x['detalle']}")
    for x in informe.get("n11", {}).get("casos", []):
        if not x["ok"]:
            md.append(f"- N11 · {x['caso']}: {x['detalle']}")
    for x in h["fallos"][:15]:
        md.append(f"- humo · {x['modulo']} · {x['puesto']} ({x['persona']}): {x['respuestas']}")
    for x in f["problemas"][:15]:
        md.append(f"- fuga · {x['fichero']} · {x['puesto']} ({x['persona']}) recibe {x['recibe']} {x.get('tipo', '')}")
    for k, v in c["diferencias"].items():
        for x in v[:8]:
            md.append(f"- cuadre · {k} · {x}")
    (carpeta / f"{nombre}.md").write_text("\n".join(md) + "\n")
    print(f"Resultado: {informe['resultado']} · informe en {carpeta / (nombre + '.md')}")
    if informe["resultado"] == "rojo" and "--sin-avisos" not in ARGS:
        import avisos_tuberia as AV
        AV.avisar("pruebas_noche", nombre[:10], f"La batería nocturna sale en rojo: ver despliegue/estado/pruebas/{nombre}.md")
    return 0 if informe["resultado"] == "verde" else 1


if __name__ == "__main__":
    sys.exit(main())

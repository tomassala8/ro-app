#!/usr/bin/env python3
"""migracion/pruebas_L-25.py · L-25: la matriz que decidió Tomás el 4-oct (D1–D4), la silla «altas» y los puestos solo de Tomás.

Uso: python3 migracion/pruebas_L-25.py --puerto 8771        (lectura; también vale 3000)
     python3 migracion/pruebas_L-25.py --puerto 8770 --guardar-antes   (graba la foto de la app de hoy, solo la primera vez)
     python3 migracion/pruebas_L-25.py --escribir               (arranca su propio 8781 sobre ro_esc y escribe ahí)

Un caso por línea de la decisión (si un puesto no tiene persona activa en la copia, ese caso se salta diciéndolo):
  (1) proyectos: ve la cuota y la inversión de cada cliente y la rentabilidad; un account puro, ninguna de las dos.
  (2) administración: PENDIENTE (toca ficheros que juzgan). Tomás (D1) quiere que vea los totales de la agencia
      (tipo dinero_empresa), pero `probar_clasificacion_importes_580`, `probar_importes_acciones_decisiones_588`,
      `probar_recorte_estructurado_632` y `pruebas_seguridad.py` («Sofía sigue sin finanzas/direccion») exigen lo
      contrario. Hasta que Tomás cambie esos juicios de día, no se abre: la prueba exige que SIGA cerrado.
  (3) trafficker: Captación en «todo»; sus clientes llevan la inversión; ningún cliente fuera de los que recibe.
      Su ámbito sigue siendo «cartera» (no está en la decisión): recibe la inversión de todos SUS clientes.
  (4) producción: ya no ve Captación (la pantalla ni su fichero → 403).
  (5) jefa de SEO: la Bandeja no clasifica por tema → no la ve (ni sus ficheros → 403).
  (6) proyectos, técnico de altas y las tres jefaturas solo las da Tomás (operaciones no las da; Tomás sí).
  (7) técnico de altas: su cartera = los clientes «nuevo» de la verdad; su Bandeja trae solo filas de ellos.
  (8) antes/después: solo cambian los puestos afectados y solo Captación y Bandeja en `modulos_puestos`.
Sale 0 si pasa. Sin datos reales en la salida (solo recuentos).
"""
import argparse
import http.client
import json
import os
import pathlib
import subprocess
import sys
import time

RAIZ = pathlib.Path(__file__).resolve().parents[1]
TMP = pathlib.Path.home() / "RO_MIGRACION" / "tmp"
ANTES = TMP / "l25_antes.json"
LOCAL = "127.0.0.1"
LOG = pathlib.Path.home() / "RO_MIGRACION" / "logs" / "esc_l25.log"

ap = argparse.ArgumentParser()
ap.add_argument("--puerto", type=int, default=8771)
ap.add_argument("--guardar-antes", action="store_true")
ap.add_argument("--escribir", action="store_true")
a = ap.parse_args()
fallos = []
saltos = []
hechos = 0

AFECTADOS = {"proyectos", "administracion", "trafficker", "produccion", "jefa_seo", "tecnico_altas",
             "jefa_publicidad", "jefa_crm"}   # los dos últimos solo cambian en «puestos solo de Tomás» (no en la sesión)
NUEVOS_SOLO_TOMAS = ["proyectos", "tecnico_altas", "jefa_publicidad", "jefa_crm", "jefa_seo"]


def exige(cond, texto):
    global hechos
    hechos += 1
    if not cond:
        fallos.append(texto)


def pedir(metodo, ruta, yo=None, cuerpo=None, puerto=None):
    c = http.client.HTTPConnection("127.0.0.1", puerto or a.puerto, timeout=90)
    cab = {"X-RO-App": "1", "Accept": "application/json", "Origin": "http://127.0.0.1:3000"}
    if yo:
        cab["X-RO-Yo"] = yo
    if cuerpo is not None:
        cab["Content-Type"] = "application/json"
    c.request(metodo, ruta, body=json.dumps(cuerpo) if cuerpo is not None else None, headers=cab)
    r = c.getresponse()
    datos = r.read()
    c.close()
    try:
        return r.status, json.loads(datos or b"null")
    except ValueError:
        return r.status, None


def sesion(yo):
    s, d = pedir("GET", "/api/sesion", yo)
    exige(s == 200 and isinstance(d, dict), f"/api/sesion de {yo} → {s}")
    return d or {}


def claves_clientes(ses):
    cl = [c for c in ((ses.get("datos") or {}).get("clientes") or []) if isinstance(c, dict)]
    ks = set()
    for c in cl:
        ks |= set(c)
    return cl, ks


def foto(yo):
    ses = sesion(yo)
    d = ses.get("datos") or {}
    cl, ks = claves_clientes(ses)
    return {"clientes": len(cl), "claves_cliente": sorted(ks), "cartera": len(d.get("carteraIds") or []),
            "claves_datos": sorted(d), "solo_su_cartera": bool(d.get("soloSuCartera"))}


def personas_activas():
    s, e = pedir("GET", "/api/elegir", "tomas")
    exige(s == 200, f"/api/elegir → {s}")
    return [p for p in ((e or {}).get("personas") or []) if p.get("estado", "activo") == "activo"]


def una_de(personas, puesto, exacto=True):
    """Una persona activa con ese puesto; mejor si es su único puesto."""
    con = [p for p in personas if puesto in (p.get("puestos") or [])]
    puras = [p for p in con if (p.get("puestos") or []) == [puesto]]
    return (puras or con or [None])[0] if exacto else (con or [None])[0]


def se_salta(puesto):
    saltos.append(puesto)
    print(f"aviso: sin persona activa con el puesto «{puesto}»: se salta su caso")


def tiene_puesto(p, puestos):
    return bool(set(p.get("puestos") or []) & set(puestos))


personas = personas_activas()
por_puesto = {}
for p in personas:
    for pu in p.get("puestos") or []:
        por_puesto.setdefault(pu, p)
puras = {}
for p in personas:
    if len(p.get("puestos") or []) == 1:
        puras.setdefault(p["puestos"][0], p)
representantes = {pu: (puras.get(pu) or por_puesto[pu]) for pu in sorted(por_puesto)}

# ---------------------------------------------------------------- foto de la app de hoy (solo la primera vez)
if a.guardar_antes:
    if ANTES.exists():
        print(f"ya hay una foto de antes en {ANTES}; no se pisa")
        sys.exit(0)
    s, ses = pedir("GET", "/api/sesion", "tomas")
    base = {"modulos_puestos": (ses or {}).get("modulos_puestos"),
            "personas": {pu: {"id": p["id"], "puestos": p.get("puestos") or [], **foto(p["id"])} for pu, p in representantes.items()}}
    exige(bool(base["modulos_puestos"]) and len(base["personas"]) >= 18, "la foto de antes está incompleta")
    if fallos:
        print("✘ L-25: " + " · ".join(fallos))
        sys.exit(1)
    ANTES.parent.mkdir(parents=True, exist_ok=True)
    ANTES.write_text(json.dumps(base, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"✔ L-25: foto de antes grabada ({len(base['personas'])} puestos) en {ANTES}")
    sys.exit(0)

s, ses_t = pedir("GET", "/api/sesion", "tomas")
mp = (ses_t or {}).get("modulos_puestos") or {}
exige(bool(mp), "modulos_puestos vacío")
direccion = una_de(personas, "direccion")
account = una_de(personas, "account")
exige(bool(direccion) and bool(account), "faltan dirección o un account")
dir_cl, _ = claves_clientes(sesion(direccion["id"])) if direccion else ([], set())
nuevos_verdad = {c["id"] for c in dir_cl if c.get("nuevo")}

# ---------------------------------------------------------------- (1) proyectos
pr = una_de(personas, "proyectos")
if pr and account:
    cl, ks = claves_clientes(sesion(pr["id"]))
    exige("cuota" in ks, "(1) proyectos no recibe la cuota de ningún cliente")
    exige("publicidad_30d" in ks, "(1) proyectos no recibe la inversión (publicidad_30d) de ningún cliente")
    cl2, ks2 = claves_clientes(sesion(account["id"]))
    exige("cuota" not in ks2 and "publicidad_30d" not in ks2, "(1) un account puro recibe cuota o inversión")
    s, _ = pedir("GET", "/api/modulo/dinero_cliente/rentabilidad", pr["id"])
    exige(s == 200, f"(1) rentabilidad por cliente para proyectos → {s}")
    s, _ = pedir("GET", "/api/modulo/dinero_cliente/rentabilidad", account["id"])
    exige(s in (403, 404), f"(1) rentabilidad por cliente para un account → {s} (debe ser 403)")
    s, _ = pedir("GET", "/api/indicadores", pr["id"])
    exige(s == 200, f"(1) /api/indicadores para proyectos → {s}")
else:
    se_salta("proyectos")

# ---------------------------------------------------------------- (2) administración
ad = una_de(personas, "administracion")
if ad and account:
    cl, ks = claves_clientes(sesion(ad["id"]))
    exige("cuota" in ks, "(2) administración dejó de ver la cuota")
    s, _ = pedir("GET", "/api/modulo/finanzas/finanzas", ad["id"])
    exige(s == 200, f"(2) finanzas/finanzas para administración → {s} (como hoy)")
    s, _ = pedir("GET", "/api/modulo/finanzas/direccion", ad["id"])
    exige(s == 403, f"(2) finanzas/direccion para administración → {s} (debe seguir en 403: beneficio y coste del equipo)")
    s, fin = pedir("GET", "/api/modulo/finanzas/finanzas", ad["id"])
    exige(s == 200 and "direccion" not in (fin or {}), "(2) administración recibe la clave «direccion» (dinero de la empresa) de Finanzas")
    print("aviso: (2) administración con dinero_empresa queda PENDIENTE: lo impiden jueces que no se tocan (ver NOTAS «L-25»)")
    s, _ = pedir("GET", "/api/modulo/finanzas/finanzas", account["id"])
    exige(s in (403, 404), f"(2) finanzas/finanzas para un account → {s} (debe ser 403)")
    cl2, ks2 = claves_clientes(sesion(account["id"]))
    exige(not ({"cuota", "cobros"} & ks2), "(2) un account recibe cuota o cobros")
else:
    se_salta("administracion")

# ---------------------------------------------------------------- (3) trafficker
tr = None
for p in personas:
    if "trafficker" in (p.get("puestos") or []) and not tiene_puesto(p, ["direccion", "jefa_publicidad", "operaciones", "proyectos", "administracion"]):
        tr = p
        break
exige((mp.get("captacion") or {}).get("trafficker") == "todo", f"(3) Captación para trafficker = {(mp.get('captacion') or {}).get('trafficker')!r} (debe ser 'todo')")
if tr:
    ses = sesion(tr["id"])
    cl, ks = claves_clientes(ses)
    exige(bool(cl) and "publicidad_30d" in ks, "(3) el trafficker no recibe la inversión de sus clientes")
    cartera = set((ses.get("datos") or {}).get("carteraIds") or [])
    s, cap = pedir("GET", "/api/modulo/captacion/captacion", tr["id"])
    exige(s == 200, f"(3) captacion/captacion para trafficker → {s}")
    ids = set()

    def andar(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k == "cliente_id" and isinstance(v, str):
                    ids.add(v)
                andar(v)
        elif isinstance(o, list):
            for v in o:
                andar(v)
    andar(cap)
    exige(not (ids - cartera), f"(3) Captación del trafficker trae {len(ids - cartera)} clientes fuera de los que recibe")
else:
    se_salta("trafficker")

# ---------------------------------------------------------------- (4) producción
pd = None
for p in personas:
    if "produccion" in (p.get("puestos") or []) and not tiene_puesto(p, ["direccion", "operaciones", "proyectos", "jefa_publicidad", "jefa_crm", "jefa_seo", "trafficker", "tecnico_altas", "account", "especialista_ghl"]):
        pd = p
        break
exige("produccion" not in (mp.get("captacion") or {}), "(4) producción sigue en Captación de modulos_puestos")
if pd:
    s, _ = pedir("GET", "/api/modulo/captacion/captacion", pd["id"])
    exige(s == 403, f"(4) captacion/captacion para producción → {s} (debe ser 403)")
else:
    se_salta("produccion")

# ---------------------------------------------------------------- (5) jefa de SEO
js = una_de(personas, "jefa_seo")
exige((mp.get("bandeja") or {}).get("jefa_seo") in (None, "no"), f"(5) Bandeja para jefa_seo = {(mp.get('bandeja') or {}).get('jefa_seo')!r} (debe faltar)")
exige((mp.get("bandeja") or {}).get("jefa_publicidad") == "todo" and (mp.get("bandeja") or {}).get("jefa_crm") == "todo",
      "(5) las otras jefaturas perdieron la Bandeja")
if js and not tiene_puesto(js, ["direccion", "operaciones", "proyectos", "jefa_publicidad", "jefa_crm", "account", "tecnico_altas", "trafficker", "especialista_ghl"]):
    for ruta in ("/api/modulo/bandeja/bandeja", "/api/modulo/bandeja/hilos"):
        s, _ = pedir("GET", ruta, js["id"])
        exige(s == 403, f"(5) {ruta} para la jefa de SEO → {s} (debe ser 403)")
else:
    se_salta("jefa_seo")

# ---------------------------------------------------------------- (6) puestos solo de Tomás (lectura)
mili = una_de(personas, "operaciones")
if mili and direccion and mili["id"] != direccion["id"]:
    s, alt_m = pedir("GET", "/api/altas", mili["id"])
    s2, alt_t = pedir("GET", "/api/altas", direccion["id"])
    exige(s == 200 and s2 == 200, f"(6) /api/altas {s}/{s2}")
    dar_m = set((alt_m or {}).get("puede_dar") or [])
    dar_t = set((alt_t or {}).get("puede_dar") or [])
    exige(not (dar_m & set(NUEVOS_SOLO_TOMAS)), f"(6) operaciones puede dar {sorted(dar_m & set(NUEVOS_SOLO_TOMAS))}")
    exige(set(NUEVOS_SOLO_TOMAS) <= dar_t, "(6) Tomás no puede dar alguno de los puestos nuevos")
    mando = {p["id"]: p.get("mando") for p in ((alt_t or {}).get("personas") or [])}
    for pu in NUEVOS_SOLO_TOMAS:
        q = una_de(personas, pu, exacto=False)
        if q:
            exige(mando.get(q["id"]) is True, f"(6) quien tiene «{pu}» no cuenta como puesto de mando")
else:
    se_salta("operaciones")

# ---------------------------------------------------------------- (7) técnico de altas
ta = una_de(personas, "tecnico_altas")
if ta:
    ses = sesion(ta["id"])
    cartera = set((ses.get("datos") or {}).get("carteraIds") or [])
    exige(cartera == nuevos_verdad, f"(7) cartera del técnico de altas: {len(cartera)} clientes, la verdad tiene {len(nuevos_verdad)} «nuevo»")
    exige(bool(cartera) or not nuevos_verdad, "(7) cartera vacía con clientes nuevos")
    s, h = pedir("GET", "/api/modulo/bandeja/hilos", ta["id"])
    exige(s == 200, f"(7) bandeja/hilos del técnico de altas → {s}")
    ids = set()

    def andar2(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k == "cliente_id" and isinstance(v, str):
                    ids.add(v)
                andar2(v)
        elif isinstance(o, list):
            for v in o:
                andar2(v)
    andar2(h)
    exige(not (ids - cartera), f"(7) la Bandeja del técnico de altas trae {len(ids - cartera)} clientes que no son de sus altas")
else:
    se_salta("tecnico_altas")

# ---------------------------------------------------------------- (8) antes / después
if ANTES.exists():
    antes = json.loads(ANTES.read_text(encoding="utf-8"))
    cambian = {k for k in set(antes["modulos_puestos"]) | set(mp) if antes["modulos_puestos"].get(k) != mp.get(k)}
    exige(cambian <= {"captacion", "bandeja"}, f"(8) cambian módulos que no son Captación ni Bandeja: {sorted(cambian - {'captacion', 'bandeja'})}")
    exige(cambian == {"captacion", "bandeja"}, f"(8) tendrían que cambiar Captación y Bandeja; cambian {sorted(cambian)}")
    cap_a, cap_d = antes["modulos_puestos"].get("captacion") or {}, mp.get("captacion") or {}
    exige({k for k in set(cap_a) | set(cap_d) if cap_a.get(k) != cap_d.get(k)} == {"produccion", "trafficker"}, "(8) Captación: tienen que cambiar producción y trafficker, y solo esos")
    ban_a, ban_d = antes["modulos_puestos"].get("bandeja") or {}, mp.get("bandeja") or {}
    exige({k for k in set(ban_a) | set(ban_d) if ban_a.get(k) != ban_d.get(k)} == {"jefa_seo"}, "(8) Bandeja: tiene que cambiar jefa_seo, y solo esa")
    for pu, ref in antes["personas"].items():
        if tiene_puesto(ref, AFECTADOS):
            continue
        ahora = foto(ref["id"])
        for k in ("clientes", "claves_cliente", "cartera", "claves_datos", "solo_su_cartera"):
            exige(ahora[k] == ref[k], f"(8) {pu} ({k}) cambió y no es de los afectados")
else:
    print(f"aviso: no hay foto de antes en {ANTES}; (8) se salta (grábala contra la app de hoy con --guardar-antes)")
    saltos.append("antes")


# ---------------------------------------------------------------- (6b) escritura, solo con --escribir (su propio 8781 sobre ro_esc)
def escribir_en_ro_esc():
    def soltar():
        subprocess.run(["bash", "-lc", "kill $(lsof -t -iTCP@127.0.0.1:8781 -sTCP:LISTEN) 2>/dev/null; sleep 1"], check=False)
    limpia = subprocess.run([sys.executable, "migracion/contrato_escritura.py", "base-limpia", "ro_esc"], cwd=RAIZ, check=False)
    exige(limpia.returncode == 0, f"(6b) base-limpia ro_esc rc={limpia.returncode}")
    if limpia.returncode:
        return
    TMP.mkdir(parents=True, exist_ok=True)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    (TMP / "recarga_esc.json").write_text('{"ligera": []}\n', encoding="utf-8")
    (TMP / "correos_entrada_esc.json").write_text("{}\n", encoding="utf-8")
    (TMP / "lista_access_esc.txt").write_text("", encoding="utf-8")
    entorno = os.environ.copy()
    entorno.update({"DATABASE_URL": "postgresql://ro:ro@" + LOCAL + ":5432/ro_esc", "RO_RELOJ": "2026-10-05T07:30", "RO_SIN_LLAVES": "1",
                    "RO_AVISOS_SIN_BUCLE": "1", "RO_ORIGEN_APP": "http://127.0.0.1:3000", "RO_RECARGA_CONFIG": str(TMP / "recarga_esc.json"),
                    "RO_CORREOS_ENTRADA": str(TMP / "correos_entrada_esc.json"), "RO_LISTA_ACCESS": str(TMP / "lista_access_esc.txt")})
    soltar()
    proc = subprocess.Popen([sys.executable, "servir.py", "--bind", "127.0.0.1", "--puerto", "8781"], cwd=RAIZ, env=entorno,
                            stdout=open(LOG, "ab"), stderr=subprocess.STDOUT, start_new_session=True)
    try:
        limite = time.time() + 60
        listo = False
        while time.time() < limite:
            try:
                if pedir("GET", "/api/elegir", "tomas", puerto=8781)[0] == 200:
                    listo = True
                    break
            except OSError:
                pass
            time.sleep(0.4)
        exige(listo, "(6b) 8781 no arranca")
        if not listo:
            return
        ps = [p for p in (pedir("GET", "/api/elegir", "tomas", puerto=8781)[1] or {}).get("personas") or [] if p.get("estado", "activo") == "activo"]
        d = next((p["id"] for p in ps if "direccion" in (p.get("puestos") or [])), None)
        m = next((p["id"] for p in ps if (p.get("puestos") or []) == ["operaciones"]), None) or next((p["id"] for p in ps if "operaciones" in (p.get("puestos") or []) and "direccion" not in (p.get("puestos") or [])), None)
        pers = next((p for p in ps if (p.get("puestos") or []) == ["account"]), None)
        exige(bool(d and m and pers), "(6b) faltan dirección, operaciones o un account")
        if not (d and m and pers):
            return
        for pu in NUEVOS_SOLO_TOMAS:
            s, r = pedir("POST", "/api/ajustes/persona", m, {"id": pers["id"], "cambios": {"puestos": ["account", pu]}}, puerto=8781)
            exige(s == 403, f"(6b) operaciones da «{pu}» → {s} (debe ser 403)")
        s, ses = pedir("GET", "/api/sesion", pers["id"], puerto=8781)
        exige(sorted((ses or {}).get("persona", {}).get("puestos") or []) == ["account"], "(6b) la persona cambió de puestos aunque operaciones recibió 403")
        s, r = pedir("POST", "/api/ajustes/persona", d, {"id": pers["id"], "cambios": {"puestos": ["account", "proyectos"]}}, puerto=8781)
        exige(s == 200, f"(6b) dirección da «proyectos» → {s} (debe ser 200) {json.dumps(r, ensure_ascii=False)[:120] if s != 200 else ''}")
    finally:
        soltar()
        proc.poll()


if a.escribir:
    escribir_en_ro_esc()

if saltos:
    print("casos saltados: " + ", ".join(saltos))
print(("✔ " if not fallos else "✘ ") + f"L-25: {hechos} comprobaciones" + ("" if not fallos else " · " + " · ".join(fallos)))
sys.exit(1 if fallos else 0)

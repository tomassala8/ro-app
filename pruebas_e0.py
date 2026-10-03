#!/usr/bin/env python3
"""
pruebas_e0.py · pruebas de aceptación de E0 contra servir.py ya arrancado (solo lectura: no escribe nada).

  python3 pruebas_e0.py [--puerto 8770]

Comprueba:
  1. Cada cliente tiene account o la marca «sin_account»; cada persona activa tiene al menos un puesto.
  2. Un account, un trafficker y un setter que piden un cliente ajeno reciben 403 sin datos del cliente.
  3. data/, local.db, historia/, *.py e indicadores.json no se sirven como fichero.
  4. «Ver como» lo niega a quien no es Mili ni Tomás; una persona de baja no entra.
  5. El catálogo tiene 229 indicadores de puesto (+23 de fase 2), todos con estado de medición y origen.
  6. El escáner de secretos pasa limpio sobre data/ (sin contar los _privado/, que no se sirven).
  7. Huella de la matriz de permisos en Python (compárala con la de permisos.js; ver _ESTADO_E0.md).
  8. (Ronda 10) pruebas_diseno.py --estricto: ningún módulo trae su hoja de estilos ni se sale de la guía.
"""
import hashlib
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import permisos as P            # noqa: E402
import escaner_secretos as ESC  # noqa: E402

PUERTO = int(sys.argv[sys.argv.index("--puerto") + 1]) if "--puerto" in sys.argv else 8770
BASE = f"http://127.0.0.1:{PUERTO}"
fallos = []


def get(ruta, yo=None, como=None):
    # Ronda 6: las personas «por incorporar» (setters) no entran hasta que Mili las active; se prueban con «ver como».
    if yo and yo.startswith("setter_") and not como:
        yo, como = "tomas", yo
    req = urllib.request.Request(BASE + ruta)
    if yo:
        req.add_header("X-RO-Yo", yo)
    if como:
        req.add_header("X-RO-Como", como)
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def ok(cond, texto):
    print(("✓ " if cond else "✗ ") + texto)
    if not cond:
        fallos.append(texto)


clientes = json.loads((AQUI / "data/clientes.json").read_text())
personas = json.loads((AQUI / "data/personas.json").read_text())
asig = json.loads((AQUI / "data/asignaciones.json").read_text())

ok(all(c.get("responsable_id") or c.get("sin_account") for c in clientes), f"{len(clientes)} clientes: todos con account o marca «sin_account»")
activas = [p for p in personas if p.get("activo")]
ok(all(p["puestos"] for p in activas), f"{len(activas)} personas activas, todas con al menos un puesto")

for yo in ("lucia", "lina", "setter_ana"):
    _, s = get("/api/sesion", yo)
    d = json.loads(s)["datos"]
    ajeno = next(c["id"] for c in d["clientes"] if not c["detalle"])
    cod, cuerpo = get(f"/api/cliente/{ajeno}", yo)
    ok(cod == 403 and set(json.loads(cuerpo)) == {"error"}, f"{yo} pide {ajeno} (ajeno): {cod}, solo el motivo")

for ruta in ("/data/clientes.json", "/data/personas.json", "/local.db", "/servir.py", "/indicadores.json", "/historia/", "/data/ventas_ro/_privado/setter_ana.json"):
    cod, _ = get(ruta)
    ok(cod == 403, f"{ruta} no se sirve como fichero ({cod})")

cod, _ = get("/api/sesion", "lucia", "tomas")
ok(cod == 403, f"Lucía no puede «ver como» ({cod})")
bajas = [p["id"] for p in personas if p.get("estado") == "baja"]
if bajas:
    cod, _ = get("/api/sesion", bajas[0])
    ok(cod == 403, f"{bajas[0]} (de baja) no entra ({cod})")

# Datos de módulo: solo quien ve el módulo (propuesta 1 de E6)
for yo, ruta, esperado in (("setter_ana", "/api/modulo/ventas_ro/outreach", 403), ("setter_ana", "/data/ventas_ro/outreach.json", 403),
                           ("setter_ana", "/api/modulo/ventas_ro/setters", 200), ("eulimar", "/api/modulo/ventas_ro/outreach", 200),
                           ("eulimar", "/api/modulo/ventas_ro/setters", 403), ("lucia", "/api/modulo/ventas_ro/ventas_ro", 403),
                           ("tomas", "/api/modulo/ventas_ro/inventado", 403)):
    cod, _ = get(ruta, yo)
    ok(cod == esperado, f"{yo} pide {ruta}: {cod} (esperado {esperado})")
cod, s_ = get("/api/acciones?modulo=prospeccion", "setter_ana")
ok(cod == 403, f"setter_ana no lee las acciones de Prospección ({cod})")

# «En rojo» sin detalle para puestos sin cartera (setters, outreach sin cartera, RRHH, administración)
for yo in ("setter_ana", "eulimar", "cecilia", "sofia"):
    d = json.loads(get("/api/sesion", yo)[1])["datos"]
    con_texto = sum(1 for a in d["alarmas"] if a.get("ambito") == "cliente" and a.get("texto"))
    de_persona = sum(1 for a in d["alarmas"] if a.get("ambito") == "persona")
    lista = sum(1 for a in d["alarmas"] if a.get("ambito") == "cliente")
    cartera = set(d["carteraIds"])
    ajenas_con_texto = sum(1 for a in d["alarmas"] if a.get("ambito") == "cliente" and a.get("texto") and a["cliente_id"] not in cartera)
    ok(ajenas_con_texto == 0 and (yo != "setter_ana" or de_persona == 0),
       f"{yo}: lista común de {lista} alarmas, {con_texto} con texto (todas de su cartera), {de_persona} avisos de persona")

# Ronda 3 · D-P-CAP1: el dinero de cada fila se decide con SU cliente
cod, s_ = get("/api/modulo/captacion/captacion", "lina")
if cod == 200:
    filas = json.loads(s_).get("clientes", [])
    sesion_lina = json.loads(get("/api/sesion", "lina")[1])["datos"]
    suyos = set(sesion_lina["carteraIds"])
    con_dinero_suyo = sum(1 for c in filas if c.get("cliente_id") in suyos and "gasto" in c)
    ajenos_con_dinero = sum(1 for c in filas if c.get("cliente_id") not in suyos and "gasto" in c)
    ok(ajenos_con_dinero == 0 and con_dinero_suyo > 0, f"Lina en Captación: {con_dinero_suyo} clientes suyos con gasto, {ajenos_con_dinero} ajenos con gasto")
else:
    ok(False, f"Lina no recibe captacion/captacion ({cod})")

# Ronda 3 · D-P-CAP2 y M4: la ficha de E1 sin dinero ni horas para quien no los ve
sesion_g = json.loads(get("/api/sesion", "gustavo")[1])["datos"]
cid = next((c for c in sesion_g["carteraIds"]), None)
f = json.loads(get(f"/api/cliente/{cid}", "gustavo")[1])["fuentes"] or {}
txt = json.dumps(f, ensure_ascii=False)
fu = f.get("fuentes", {})
fuga = [k for k in ('"presupuesto"', '"serie"', '"meses"', '"ltv"', '"cuota_actual"', '"gasto"') if k in txt]
ok(not fuga and "€" not in json.dumps(fu.get("meta", {}), ensure_ascii=False), f"Gustavo (GHL) abre {cid}: sin presupuesto, series, cuota, LTV ni gasto ({fuga or 'nada'})")
fs = json.loads(get("/api/cliente/gac", "sofia")[1])["fuentes"] or {}
ok("datos" not in (fs.get("fuentes", {}).get("horas") or {}) and '"presupuesto"' not in json.dumps(fs), "Sofía abre GAC: ve cuota, pero no horas por cliente (D-84) ni presupuesto de Meta")

# Ronda 3 · «Actualizar ahora» y avisos: solo Mili y Tomás
for yo, esperado in (("tomas", 200), ("mili", 200), ("lucia", 403), ("constanza", 403)):
    ok(get("/api/recarga", yo)[0] == esperado and get("/api/avisos", yo)[0] == esperado, f"{yo}: recarga y avisos → {esperado}")
av = json.loads(get("/api/avisos", "tomas")[1])
dias = {}
for a in av["avisos"]:
    dias[a["dia"]] = dias.get(a["dia"], 0) + (a["estado"] == "para_avisar")
ok(all(n <= 3 for n in dias.values()), f"avisos «para avisar» por día ≤ 3 ({dias or 'ninguno'})")

# Ronda 3 · WhatsApp: datos por cliente sin textos; setters no lo ven
cod, s_ = get("/api/modulo/whatsapp/whatsapp", "lucia")
w = json.loads(s_) if cod == 200 else {}
suyos = set(json.loads(get("/api/sesion", "lucia")[1])["datos"]["carteraIds"])
ok(cod == 200 and all(x["cliente_id"] in suyos for x in w.get("clientes", [])) and "ultimo_texto" not in s_, f"Lucía recibe WhatsApp solo de sus clientes y sin textos ({len(w.get('clientes', []))})")
cod, s_ = get("/api/modulo/whatsapp/whatsapp", "setter_ana")
ok(cod == 403 or not json.loads(s_).get("clientes"), "la setter no recibe ningún cliente de WhatsApp")
ok(get("/data/whatsapp/_privado/textos.json", "tomas")[0] == 403, "los textos de WhatsApp no se sirven como fichero")

# Ronda 4 · decisiones en vivo, ficheros por puesto y leads fuera del nivel «resumen»
ok(all(get("/api/decisiones", yo)[0] == 200 for yo in ("tomas", "constanza", "lucia", "setter_ana")), "/api/decisiones responde a todos (cada uno su trozo)")
for yo, d_dir, d_con in (("tomas", 200, 200), ("mili", 200, 200), ("cecilia", 403, 200), ("lucia", 403, 403)):
    c1, c2 = get("/api/modulo/decisiones/direccion", yo)[0], get("/api/modulo/personas_m20/contratacion", yo)[0]
    ok((c1, c2) == (d_dir, d_con), f"{yo}: informe de dirección {c1}, contratación {c2} (por puesto)")
cod, s_ = get("/api/modulo/crm/crm", "valeria")
crm_v = json.loads(s_) if cod == 200 else {}
ok(cod == 200 and not crm_v.get("leads_sin_tocar") and not crm_v.get("citas_sin_estado"), "Valeria (Salud del CRM en resumen): sin filas de leads")
cod, s_ = get("/api/modulo/crm/crm", "yessica")
ok(cod == 200 and json.loads(s_).get("leads_sin_tocar"), "Jessi (nivel todo) sí recibe los leads sin tocar")

# Ronda 5 · fuga de cuota, Sofía, verdad única y sueldos
for yo in ("lina", "valeria"):
    cod, s_ = get("/api/modulo/dinero_cliente/dinero_cliente", yo)
    dc = json.loads(s_) if cod == 200 else {}
    claves = set()
    def _walk(o):
        if isinstance(o, dict):
            claves.update(o.keys()); [_walk(v) for v in o.values()]
        elif isinstance(o, list):
            [_walk(v) for v in o]
    _walk(dc)
    ok(cod == 200 and not ({"pautadas", "pct_sep", "segmento", "cuota"} & claves), f"{yo} no puede reconstruir la cuota en Dinero por cliente (solo «dentro/fuera de lo pautado»)")
ok(get("/api/modulo/reuniones/reuniones", "sofia")[0] == 403, "Sofía no recibe las reuniones de los clientes")
fs = json.loads(get("/api/cliente/gac", "sofia")[1])["fuentes"] or {}
ok(set(fs.get("fuentes", {})) <= {"cartera", "libro", "arranque", "asignaciones"}, f"Sofía recibe de la ficha solo contrato y cuota ({sorted(fs.get('fuentes', {}))})")
for yo in ("lucia", "tomas"):
    cod, s_ = get("/api/modulo/verdad/clientes", yo)
    vd = json.loads(s_) if cod == 200 else {}
    ok(cod == 200 and len(vd.get("comun", [])) >= 60, f"{yo} recibe la lista común de la verdad única ({len(vd.get('comun', []))}) y {len(vd.get('clientes', []))} con detalle")
# R16c (3-oct): las setters no ven «En rojo»; contrato: la verdad les llega con 200 y la lista común y el detalle VACÍOS.
cod, s_ = get("/api/modulo/verdad/clientes", "setter_ana")
vd = json.loads(s_) if cod == 200 else {}
ok(cod == 200 and vd.get("comun") == [], f"setter_ana recibe la verdad única con la lista común vacía ({cod}, {len(vd.get('comun') or [])} comunes)")
ok(cod == 200 and vd.get("clientes") == [] and not vd.get("carteras"), "la setter no recibe el detalle de ningún cliente en la verdad")
for ruta in ("/data/sueldos/_privado/sueldos.json", "/api/modulo/sueldos/_privado/sueldos"):
    ok(get(ruta, "tomas")[0] == 403, f"sueldos no se sirven en bloque ({ruta})")

cat = json.loads(get("/api/indicadores", "tomas")[1])
ok(next(i for i in cat["indicadores"] if i["id"] == "jefa_crm.carga_por_especialista")["medible"] == "medias", "«Carga por especialista» a medias")
de_puesto = [i for i in cat["indicadores"] if not i["fase2"]]
# Ronda 12 (R13): +1 del account («resultados de su cartera», regla «cliente primero») → 229
ok(len(de_puesto) == 229 and len(cat["indicadores"]) - len(de_puesto) == 23, f"catálogo: {len(de_puesto)} de puesto + {len(cat['indicadores']) - len(de_puesto)} de fase 2")
ok(all(i["medible"] in ("hoy", "medias", "no") and i["umbral_origen"] for i in cat["indicadores"]), "cada indicador con estado de medición y origen del umbral")
manda = {i["puesto"]: i["id"] for i in cat["indicadores"] if i.get("el_que_manda")}
sal = next(i for i in cat["indicadores"] if i["id"] == "account.de_su_cartera_con_salud_60_el_que_manda")
res = next((i for i in cat["indicadores"] if i["id"] == manda.get("account")), {})
ok(manda.get("account") == "account.resultados_de_su_cartera_frente_a_objetivo" and not sal.get("el_que_manda") and sal.get("segundo_de") == res.get("id")
   and {p["que"] for p in res.get("partes", [])} >= {"Leads", "Citas", "Ventas"} and all(p["medible"] in ("hoy", "medias", "no") for p in res["partes"]),
   "R13 · el que manda del account = resultados de su cartera (leads, citas, ventas con «¿se mide hoy?»); la salud, segundo")
cat_lucia = json.loads(get("/api/indicadores", "lucia")[1])
ok(all(i["puesto"] == "account" for i in cat_lucia["indicadores"]), f"Lucía recibe solo los de su puesto ({len(cat_lucia['indicadores'])})")

ok(not ESC.escanear(), "escáner de secretos limpio sobre data/")

# Ronda 10: la guía de estilo es obligatoria. Ningún módulo vuelve a traer hoja propia, letra fuera de escala, colores
# sueltos ni sombras/radios con número. EN_OBRA = ficheros cuyo dueño está trabajando ahora (solo avisan; vacíalo al acabar).
import subprocess  # noqa: E402
EN_OBRA = []
r = subprocess.run([sys.executable, str(AQUI / "pruebas_diseno.py"), "--estricto"] + (["--en-obra", ",".join(EN_OBRA)] if EN_OBRA else []),
                   capture_output=True, text=True)
ok(r.returncode == 0, "guía de estilo en estricto: ningún módulo con hoja propia, letra fuera de escala ni colores sueltos"
   + ("" if r.returncode == 0 else f" ({(r.stdout.strip().splitlines() or ['?'])[-1]})"))

crudo = {"personas": personas, "asignaciones": asig}
filas = []
for p in personas:
    cp = P.contexto(p, crudo)
    for t in sorted(P.REGLAS["tipos"]) + ["inventado"]:
        for c in ["gac", "accompany", "musashi-consultores", "imfor-asesores", None]:
            for pid in (None, "lina", "lucia"):
                r = P.ver(p, {"tipo": t, "cliente_id": c, "persona_id": pid, "participantes": ["lucia"]}, cp)
                filas.append(f"{p['id']}|{t}|{c}|{pid}|{int(r['ok'])}{r['nivel']}{int(bool(r.get('desenmascarable')))}")
print(f"· huella de la matriz en Python ({len(filas)} casos): {hashlib.sha256(chr(10).join(filas).encode()).hexdigest()}")
print(f"\n{'TODO BIEN' if not fallos else f'{len(fallos)} FALLO(S)'}")
sys.exit(1 if fallos else 0)

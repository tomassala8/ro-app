#!/usr/bin/env python3
"""Prueba de aceptación de E1 (solo lectura).

1. 10 clientes al azar: una cifra por fuente del fichero data/clientes/<id>.json frente al ORIGEN,
   leído por otro camino (los JSON de origen directamente, no por los módulos de fuentes/).
2. Meta en vivo para hasta 3 de esos clientes: gasto del mes anterior en la Graph API
   (1 llamada por cuenta, token meta_token del llavero, no se imprime) frente al fichero.
3. Cada fuente con su sello (estado + hora) · ningún dato personal (escáner) · cero emparejamientos copiados.
Uso: python3 comprobar.py [semilla]
Salida: _comprobacion_E1.json y tabla por pantalla.
"""
import json
import random
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from comun import (AQUI, BUILD, CAPTACION, HERRAMIENTA, LIBRO, MUESTRAS, RAIZ, SALIDA, SALIDA_CLIENTES,  # noqa: E402
                   escanear, escribir, iso, AHORA)

semilla = int(sys.argv[1]) if len(sys.argv) > 1 else 20261002
indice = json.loads((SALIDA / "indice_clientes.json").read_text())
ids = [c["id"] for c in indice["clientes"] if c["en_panel"]]
random.seed(semilla)
muestra = random.sample(ids, 10)

datos = json.loads((BUILD / "datos.json").read_text())
panel = {c["nombre"]: c for c in datos["clientes"]}
flujo = json.loads((BUILD / "tareas_flujo.json").read_text())
informes = json.loads((BUILD / "informes_mensuales.json").read_text())
zad = json.loads((BUILD / "zadarma_por_cliente.json").read_text())
ext = json.loads((HERRAMIENTA / "externos.json").read_text())["clientes"]
cap = {c["nombre"]: c for c in json.loads(CAPTACION.read_text())["clientes"]}
libro = json.loads(LIBRO.read_text())
zoom = json.loads((AQUI / "_cache/zoom_grabaciones.json").read_text())["reuniones"]
srp = {p["id"]: p for p in json.loads((MUESTRAS / "seranking_proyectos_2026-10-02.json").read_text())["proyectos"]}
md14 = (RAIZ / "14_GOOGLE_ADS_VIA_WINDSOR.md").read_text()


def gads_md(cuenta_id):
    guion = f"{cuenta_id[:3]}-{cuenta_id[3:6]}-{cuenta_id[6:]}"
    m = re.search(re.escape(guion) + r"\s*\|\s*([\d.]+,\d+) €", md14)
    return float(m.group(1).replace(".", "").replace(",", ".")) if m else None


def g(d, *ruta):
    for k in ruta:
        d = (d or {}).get(k) if isinstance(d, dict) else None
    return d


filas = []
for cid in muestra:
    c = json.loads((SALIDA_CLIENTES / f"{cid}.json").read_text())
    n = c["ids"]["panel"]
    F = c["fuentes"]
    chequeos = [
        ("cartera", "cuota", g(F, "cartera", "datos", "cuota"), g(panel.get(n), "cuota")),
        ("horas", "horas mes anterior", g(F, "horas", "datos", "horas_mes_ant"), g(panel.get(n), "horas_mes_ant")),
        ("tareas", "creadas mes anterior", g(F, "tareas", "datos", "creadas_mes_ant"), g(flujo.get(n), "creadas_mes_ant")),
        ("informes", "informe sep", g(F, "informes", "datos", "sep", "estado"), g(informes.get(n), "sep", "estado")),
        ("desk", "tickets abiertos", g(F, "desk", "datos", "tickets_abiertos"), g(panel.get(n), "tickets_abiertos")),
        ("zadarma", "contestadas sep", g(F, "zadarma", "datos", "septiembre", "contestadas"), g(zad.get(n), "contestadas")),
        ("ga4", "usuarios 30 d", g(F, "ga4", "datos", "actual", "usuarios"), g(ext.get(n), "ga", "actual", "usuarios")),
        ("gsc", "clics 30 d", g(F, "gsc", "datos", "actual", "clics"), g(ext.get(n), "gsc", "actual", "clics")),
        ("ghl", "contactos", g(F, "ghl", "datos", "contactos"), g(ext.get(n), "ghl", "contactos")),
        ("meta", "gasto mes anterior", g(F, "meta", "datos", "gasto", "mes_anterior"), g(cap.get(n), "meta", "gasto", "mes_anterior")),
        ("libro", "cuota actual", g(F, "libro", "datos", "cuota_actual"), g(libro.get(c["ids"]["libro"]), "cuota_actual")),
    ]
    ga_id = g(F, "google_ads", "emparejado", "id")
    if ga_id:
        chequeos.append(("google_ads", "coste sep (muestra)", g(F, "google_ads", "datos", "total", "coste"), gads_md(ga_id)))
    sr_id = g(F, "seranking", "emparejado", "id")
    if sr_id:
        chequeos.append(("seranking", "palabras seguidas", g(F, "seranking", "datos", "palabras_seguidas"), g(srp.get(sr_id), "palabras")))
    zr = g(F, "zoom", "datos", "reuniones")
    if zr:
        chequeos.append(("zoom", "reuniones 30 d", len(zr), sum(1 for r in zoom if r in zr)))
    for fuente, que, app, origen in chequeos:
        estado = F.get(fuente, {}).get("estado")
        if estado in ("sin_conectar", "no_aplica") and app is None:
            continue
        filas.append({"cliente": cid, "fuente": fuente, "que": que, "app": app, "origen": origen,
                      "estado": estado, "hora": F.get(fuente, {}).get("hora"), "coincide": app == origen})

# ------------------------------------------------------------- Meta en vivo
vivo = []
try:
    tk = subprocess.check_output(["security", "find-generic-password", "-s", "meta_token", "-w"], text=True,
                                 stderr=subprocess.DEVNULL).strip()
except subprocess.CalledProcessError:
    tk = None
if tk:
    con_meta = [cid for cid in muestra
                if g(json.loads((SALIDA_CLIENTES / f"{cid}.json").read_text()), "fuentes", "meta", "estado") == "bien"
                and g(json.loads((SALIDA_CLIENTES / f"{cid}.json").read_text()), "fuentes", "meta", "datos", "gasto")]
    extra = [c["id"] for c in indice["clientes"] if c["estado_fuentes"].get("meta") == "bien" and c["id"] not in con_meta]
    for cid in (con_meta + extra)[:3]:
        c = json.loads((SALIDA_CLIENTES / f"{cid}.json").read_text())
        act = c["fuentes"]["meta"]["emparejado"]["id"]
        q = urllib.parse.urlencode({"access_token": tk, "fields": "spend", "date_preset": "last_month"})
        try:
            r = json.load(urllib.request.urlopen(f"https://graph.facebook.com/v26.0/{act}/insights?{q}", timeout=60))
            real = round(float((r.get("data") or [{}])[0].get("spend") or 0), 2)
        except Exception as e:  # noqa: BLE001
            real = f"error {type(e).__name__}"
        app = c["fuentes"]["meta"]["datos"]["gasto"]["mes_anterior"]
        ok = isinstance(real, float) and abs(real - (app or 0)) <= max(0.01 * real, 0.05)
        convertida = c["fuentes"]["meta"]["datos"].get("convertida_a_madrid")
        vivo.append({"cliente": cid, "cuenta": act, "app_gasto_sep": app, "meta_api_gasto_sep": real, "coincide_1pct": ok,
                     "nota": "Captación pasa el día a hora de Madrid y la API da el mes en la zona de la cuenta: la diferencia es esperable" if (convertida and not ok) else None})
    del tk

# ---------------------------------------------------------- otras pruebas
emp = json.loads((SALIDA / "emparejamientos.json").read_text())
sin_sello = []
for cid in ids:
    c = json.loads((SALIDA_CLIENTES / f"{cid}.json").read_text())
    for fid, b in c["fuentes"].items():
        if "estado" not in b or (b["estado"] in ("bien", "a_cero", "dato_viejo", "rota") and not b.get("hora")):
            sin_sello.append(f"{cid}.{fid}")
todo = [json.loads(p.read_text()) for p in SALIDA_CLIENTES.glob("*.json")]
hallazgos = escanear(todo)

# ---------------------------------------------------- arreglos de la auditoría de cifras (2-oct noche)
def cli(cid):
    return json.loads((SALIDA_CLIENTES / f"{cid}.json").read_text())


def ok(nombre, cond, detalle=""):
    arreglos.append({"prueba": nombre, "ok": bool(cond), "detalle": detalle})


arreglos = []
k = cli("kiosko-box")["fuentes"]["meta"]
ok("Kiosko Box con la cuenta «Josep SG» y gasto", k["emparejado"]["id"] == "act_292218051469540" and (k["datos"]["gasto"]["35d"] or 0) > 0,
   f"{k['emparejado']['id']} · {k['datos'].get('gasto', {}).get('35d')} € en 35 días")
f = cli("fusterguell")["fuentes"]
ok("FusterGüell con la propiedad de Analytics 480200463", (f["ga4"].get("emparejado") or {}).get("id") == "properties/480200463", f["ga4"]["estado"])
ok("FusterGüell con su marca de Metricool por id", (f["metricool"].get("emparejado") or {}).get("id") == 4373133, f["metricool"]["estado"])
cf = cli("consulting-f")["fuentes"]
ok("Consulting F con la landing como fuente parcial (a medias, «solo la landing»)",
   all(cf[x]["estado"] in ("bien", "a_cero") and cf[x]["medicion"] == "medias" and "solo la landing" in (cf[x]["nota"] or "") for x in ("ga4", "gsc")),
   f"{cf['ga4']['estado']}/{cf['ga4']['medicion']} · {cf['gsc']['estado']}/{cf['gsc']['medicion']}")
ok("Consulting F con la misma subcuenta de GHL en resumen y embudo",
   (cf["ghl"].get("emparejado") or {}).get("id") == (cf["captacion_ghl"].get("emparejado") or {}).get("id") == "xtSjLv44F9uT5sDpXnHC", cf["ghl"]["estado"])
mu = cli("musashi-consultores")["fuentes"]
ok("Musashi: Analytics como aviso rojo, no cero gris", mu["ga4"]["estado"] == "rota" and any(a["gravedad"] == "rojo" for a in mu["ga4"]["alertas"]), mu["ga4"]["nota"])
ok("Musashi sin Bautista (baja) en su equipo", "bautista" not in json.dumps(mu["asignaciones"]["datos"]["sillas"]) and
   all(x["persona_id"] != "bautista" for x in mu["asignaciones"]["datos"]["filas"]), mu["asignaciones"]["datos"]["sillas"].get("outreach"))
co = cli("concilia")
pendiente = co["fuentes"]["meta"]["datos"].get("estado_cuenta") == "pago pendiente"
ok("Concilia con publicidad «sí» y aviso de pago pendiente solo si la cuenta lo está",
   co["fuentes"]["asignaciones"]["datos"]["servicios"]["publicidad"] == "sí"
   and pendiente == any("pago pendiente" in a["texto"] for a in co["alertas"]),
   co["fuentes"]["asignaciones"]["datos"]["servicios"].get("publicidad_fuente"))
g = cli("gac")["fuentes"]
ok("GAC: aviso de zona horaria de Meta", any("zona de la cuenta" in a["texto"] for a in g["meta"]["alertas"]))
sc = [c for c in (cli(x) for x in ids) if c["fuentes"]["gsc"]["estado"] in ("bien", "a_cero")]
ok("Search Console con «datos hasta» (retraso de Google descontado)", sc and all(c["fuentes"]["gsc"]["datos"].get("datos_hasta") for c in sc),
   f"{sum(1 for c in sc if c['fuentes']['gsc']['datos'].get('datos_hasta'))}/{len(sc)}")
a_ = cli("asetra")["fuentes"]["gsc"]
ok("Asetra con el sitio de Search Console que tiene datos (asetra.net, sin www)",
   (a_.get("emparejado") or {}).get("id") == "https://asetra.net/" and (a_["datos"]["actual"]["clics"] or 0) > 0,
   f"{(a_.get('emparejado') or {}).get('id')} · {a_['datos']['actual']['clics']} clics")
for cid_, site_ in (("musashi-consultores", "https://musashi.es/"), ("greconsult", "https://www.greconsult.com/"), ("busbac", "https://busbac.es/")):
    g_ = cli(cid_)["fuentes"]["gsc"]
    ok(f"{cid_}: Search Console con el sitio que tiene datos", (g_.get("emparejado") or {}).get("id") == site_ and g_["estado"] == "bien",
       f"{(g_.get('emparejado') or {}).get('id')} · {g_['estado']}")
fu = json.loads((SALIDA / "fuentes.json").read_text())
sueltas = next(x for x in fu["fuentes"] if x["id"] == "meta").get("cuentas_con_gasto_sin_cliente") or []
conocidas = set((json.loads((AQUI / "emparejamientos_manual.json").read_text()).get("meta_sin_cliente_conocidas") or {}).keys())
ok("Ninguna cuenta de Meta con más de 500 € en 30 días sin cliente (fuera: ex clientes y la cuenta de RO)",
   not sueltas, ", ".join(f"{x['nombre']} {x['gasto_30d']}" for x in sueltas))
ok("Taller del Patinete fuera de dudas y alertas", "patinete" not in (AQUI / "dudas_emparejamiento.md").read_text().lower()
   and "patinete" not in json.dumps([c["alertas"] for c in (cli(x) for x in ids)]).lower())
ab = [(c["id"], k_) for c in (cli(x) for x in ids) for k_, b in c["fuentes"].items()
      if k_ != "snov" and b["estado"] in ("bien", "a_cero", "dato_viejo") and b.get("emparejado") and not (b.get("abrir") or {}).get("url")]
ok("Cada fuente emparejada con su «Abrir en …»", not ab, str(ab[:5]))
import re as _re
codigos = [(c["id"], k_, b["nota"]) for c in (cli(x) for x in ids) for k_, b in c["fuentes"].items()
           if b.get("nota") and _re.search(r"\b(?:D|W|E|G)-?\d{1,3}\b|\.json\b|\.py\b", b["nota"])]
ok("Notas sin códigos internos ni nombres de fichero", not codigos, str(codigos[:3]))

res = {
    "fecha": iso(AHORA), "semilla": semilla, "muestra": muestra, "arreglos_auditoria": arreglos,
    "cotejo": filas, "coinciden": sum(f["coincide"] for f in filas), "total": len(filas),
    "meta_en_vivo": vivo,
    "bloques_sin_sello": sin_sello, "escaner": hallazgos,
    "emparejamientos_copiados": emp["copiados_entre_clientes"],
}
escribir(AQUI / "_comprobacion_E1.json", res)
print(f"Muestra: {', '.join(muestra)}")
print(f"Cotejo con el origen: {res['coinciden']}/{res['total']} coinciden")
for f in filas:
    if not f["coincide"]:
        print("  NO coincide:", f)
for v in vivo:
    print(f"  Meta en vivo {v['cliente']}: app {v['app_gasto_sep']} · API {v['meta_api_gasto_sep']} · {'OK' if v['coincide_1pct'] else ('DIFIERE (zona convertida a Madrid)' if v.get('nota') else 'DIFIERE')}")
for a in arreglos:
    print(f"  {'OK ' if a['ok'] else 'FALLA'} {a['prueba']} · {a['detalle']}")
print(f"Bloques sin sello: {len(sin_sello)} · escáner: {len(hallazgos)} hallazgos · copiados: {len(emp['copiados_entre_clientes'])}")

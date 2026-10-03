"""Meta leída directamente por E1, solo para dos cosas (solo lectura, token meta_token del llavero):

1. Cuentas corregidas a mano (emparejamientos_manual.json → «meta») que captacion.json todavía no trae
   (p. ej. Kiosko Box → «Josep SG»). Misma definición de lead y mismas ventanas que Captación
   (leads_de: «lead» si existe; si no, lead_grouped + fb_pixel_lead; 7 días naturales cerrados, sin hoy),
   en la zona horaria de la cuenta.
2. La lista de todas las cuentas (1 llamada paginada) con zona horaria, moneda y gasto de 30 días: sirve para
   avisar de la zona (Los Ángeles ≠ Madrid), de monedas que no son euros y de cuentas con gasto sin cliente.

Plan A (--en-vivo meta): llamadas a la Graph API (1 de lista + 1 por cuenta corregida).
Plan B: la última copia en _cache/meta_directo.json.
"""
import json
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta

from comun import AHORA, AQUI, escribir, iso, leer

GRAPH = "https://graph.facebook.com/v26.0"
CACHE = AQUI / "_cache" / "meta_directo.json"


def _token():
    try:
        return subprocess.check_output(["security", "find-generic-password", "-s", "meta_token", "-w"],
                                       text=True, stderr=subprocess.DEVNULL).strip()
    except subprocess.CalledProcessError:
        return None


def _get(url, q=None):
    full = url if url.startswith("http") else GRAPH + url
    if q:
        full += "?" + urllib.parse.urlencode(q)
    for intento in range(3):
        try:
            return json.load(urllib.request.urlopen(full, timeout=90))
        except urllib.error.HTTPError as e:
            try:
                err = json.loads(e.read().decode()).get("error", {})
            except Exception:  # noqa: BLE001
                err = {}
            if err.get("code") in (4, 17, 32, 613) and intento < 2:
                time.sleep(30)
                continue
            return {"_error": e.code, "_msg": (err.get("message") or "")[:160]}
        except Exception as e:  # noqa: BLE001
            if intento < 2:
                time.sleep(5)
                continue
            return {"_error": 0, "_msg": type(e).__name__}


def leads_de(actions):
    a = {x["action_type"]: float(x["value"]) for x in (actions or [])}
    if "lead" in a:
        return a["lead"]
    return a.get("onsite_conversion.lead_grouped", 0) + a.get("offsite_conversion.fb_pixel_lead", 0)


def _d(s):
    return date.fromisoformat(s)


def leer_en_vivo(cuentas_corregidas, ventanas):
    tk = _token()
    if not tk:
        return {"_error": "falta meta_token en el llavero"}
    llamadas = 0
    # 1) lista de cuentas con zona, moneda y gasto de 30 días
    lista, url = [], "/me/adaccounts"
    q = {"access_token": tk, "limit": 200,
         "fields": "name,account_status,currency,timezone_name,insights.date_preset(last_30d){spend}"}
    while url:
        r = _get(url, q)
        llamadas += 1
        if "_error" in r:
            return {"_error": f"Meta {r['_error']} {r.get('_msg', '')}"}
        for x in r.get("data", []):
            ins = ((x.get("insights") or {}).get("data") or [{}])[0]
            lista.append({"id": x["id"], "nombre": x.get("name"), "estado": x.get("account_status"),
                          "moneda": x.get("currency"), "zona": x.get("timezone_name"),
                          "gasto_30d": round(float(ins.get("spend") or 0), 2)})
        url = (r.get("paging") or {}).get("next")
        q = None
    # 2) cuentas corregidas a mano: día a día desde el inicio de la serie hasta ayer
    desde, hasta = ventanas["serie"][0], ventanas["7d"][1]
    if ventanas["mes_anterior"][0] < desde:
        desde = ventanas["mes_anterior"][0]
    por_cuenta = {}
    for act in cuentas_corregidas:
        filas, url = [], f"/{act}/insights"
        q = {"access_token": tk, "level": "account", "time_increment": 1, "limit": 500,
             "time_range": json.dumps({"since": desde, "until": hasta}), "fields": "spend,actions"}
        while url:
            r = _get(url, q)
            llamadas += 1
            if "_error" in r:
                filas = {"_error": f"Meta {r['_error']} {r.get('_msg', '')}"}
                break
            filas += [{"d": x["date_start"], "gasto": round(float(x.get("spend") or 0), 2), "leads": leads_de(x.get("actions"))}
                      for x in r.get("data", [])]
            url = (r.get("paging") or {}).get("next")
            q = None
        por_cuenta[act] = filas
    del tk
    return {"leido": iso(AHORA), "ventanas": ventanas, "cuentas": lista, "diario": por_cuenta, "llamadas": llamadas}


def resumir(diario, ventanas):
    """Gasto, leads y coste por lead por ventana, con las mismas claves que captacion.json."""
    W = {"ayer": [ventanas["ayer"], ventanas["ayer"]], "7d": ventanas["7d"], "7d_prev": ventanas["7d_prev"],
         "14d": ventanas["14d"], "mes": ventanas["mes"], "mes_anterior": ventanas["mes_anterior"], "35d": ventanas["serie"]}
    gasto, leads, cpl = {}, {}, {}
    for k, (a, b) in W.items():
        fs = [f for f in diario if a <= f["d"] <= b]
        gasto[k] = round(sum(f["gasto"] for f in fs), 2)
        leads[k] = round(sum(f["leads"] for f in fs), 1)
        cpl[k] = round(gasto[k] / leads[k], 2) if leads[k] else None
    con_gasto = [f["d"] for f in diario if f["gasto"] > 0]
    serie = [{"d": f["d"], "meta": [f["gasto"], f["leads"]]} for f in diario if ventanas["serie"][0] <= f["d"]]
    return {"gasto": gasto, "leads": leads, "cpl": cpl, "ultimo_dia_con_gasto": max(con_gasto) if con_gasto else None,
            "serie": serie}


def cargar(cuentas_corregidas, ventanas, en_vivo=False):
    error = None
    if en_vivo and ventanas:
        r = leer_en_vivo(cuentas_corregidas, ventanas)
        if "_error" in r:
            error = r["_error"]
        else:
            escribir(CACHE, r)
    c = leer(CACHE, None)
    if c and set(cuentas_corregidas) - set((c.get("diario") or {}).keys()):
        error = (error or "") + " · faltan cuentas corregidas en la copia: recargar con --en-vivo meta"
    return c, error


def hoy_ventanas():
    """Ventanas por si no hay captacion.json (mismas reglas: días naturales cerrados, sin hoy)."""
    ayer = date.today() - timedelta(days=1)
    ini_mes = ayer.replace(day=1)
    fin_ant = ini_mes - timedelta(days=1)
    s = lambda x: x.isoformat()  # noqa: E731
    return {"ayer": s(ayer), "7d": [s(ayer - timedelta(days=6)), s(ayer)], "7d_prev": [s(ayer - timedelta(days=13)), s(ayer - timedelta(days=7))],
            "14d": [s(ayer - timedelta(days=13)), s(ayer)], "mes": [s(ini_mes), s(ayer)], "mes_anterior": [s(fin_ant.replace(day=1)), s(fin_ant)],
            "serie": [s(ayer - timedelta(days=34)), s(ayer)]}

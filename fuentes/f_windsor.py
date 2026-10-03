"""Google Ads y TikTok por Windsor (W2), mientras no haya conexión directa (google/gads.py, D-05).

Plan A (--en-vivo windsor y clave windsor_api_key en el llavero): ws.py mes <mes anterior> y ws.py mes <mes actual>.
Plan B: el último ~/RO_HERRAMIENTAS/windsor/windsor_AAAA-MM.json que haya dejado ws.py.
Plan C (hoy): la muestra manual del 2-oct (_muestras/google_ads_septiembre_muestra_2026-10-02.json),
        totales de septiembre de 14_GOOGLE_ADS_VIA_WINDSOR.md. Se sella «muestra manual 2-oct».

La clave nunca se lee aquí: solo se comprueba que existe (security sin -w). ws.py la usa y no la imprime.
"""
import json
import subprocess
import sys
from datetime import date, timedelta

from comun import AQUI, HERR, MUESTRAS, bloque, edad_h, fecha, iso, leer, mtime

WS = HERR / "windsor" / "ws.py"
MUESTRA = MUESTRAS / "google_ads_septiembre_muestra_2026-10-02.json"
FUENTES = {
    "google_ads": ("Google Ads (vía Windsor)", 24, 30),
    "tiktok":     ("TikTok Ads (vía Windsor)", 24, 30),
}


def hay_clave():
    r = subprocess.run(["security", "find-generic-password", "-s", "windsor_api_key"], capture_output=True)
    return r.returncode == 0


def mes_anterior(hoy=None):
    hoy = hoy or date.today()
    return (hoy.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")


def plan_a():
    errores = []
    for mes in (mes_anterior(), date.today().strftime("%Y-%m")):
        r = subprocess.run([sys.executable, str(WS), "mes", mes], capture_output=True, text=True, timeout=900)
        if r.returncode != 0:
            errores.append(f"{mes}: {(r.stderr or r.stdout)[-200:]}")
    return errores


def norm_id(x):
    return "".join(ch for ch in str(x or "") if ch.isdigit())


def cargar(universo, en_vivo=False):
    manual = leer(AQUI / "emparejamientos_manual.json", {}) or {}
    mapa_gads = {k: v for k, v in (manual.get("google_ads") or {}).items() if not k.startswith("_")}
    sin_id = {k: v for k, v in (manual.get("google_ads_sin_id") or {}).items() if not k.startswith("_")}
    fuera = set(manual.get("google_ads_fuera_de_windsor") or [])
    mapa_tt = {k: v for k, v in (manual.get("tiktok") or {}).items() if not k.startswith("_")}

    clave = hay_clave()
    errores = plan_a() if (en_vivo and clave) else []
    fichero = HERR / "windsor" / f"windsor_{mes_anterior()}.json"
    real = leer(fichero, None)
    if real and real.get("cuentas") is not None:
        plan = "A · ws.py en vivo" if (en_vivo and clave and not errores) else "B · último windsor_AAAA-MM.json"
        hora = fecha((real.get("_meta") or {}).get("generado")) or mtime(fichero)
        cuentas = real["cuentas"]
        periodo = [(real.get("_meta") or {}).get("desde"), (real.get("_meta") or {}).get("hasta")]
        medicion, sello = "hoy", None
        sin_gasto, tiktok_estado = [], None
    else:
        plan = "C · muestra manual 2-oct (sin windsor_api_key en el llavero)" if not clave else "C · muestra manual (ws.py aún no ha dejado fichero)"
        m = leer(MUESTRA, {}) or {}
        hora = fecha((m.get("_meta") or {}).get("leido"))
        periodo = (m.get("_meta") or {}).get("periodo")
        cuentas = [{"id": c["id"], "nombre": c["nombre"], "plataforma": "google_ads",
                    "total": {k: c.get(k) for k in ("impresiones", "clics", "coste", "conversiones")},
                    "ultimo_gasto": c.get("ultimo_gasto"), "gasto_2026": c.get("gasto_2026"), "campanas": None}
                   for c in m.get("cuentas", [])]
        sin_gasto = m.get("sin_gasto_en_septiembre", [])
        medicion, sello = "medias", "muestra manual 2-oct: totales de septiembre, sin campañas ni serie diaria"
        tiktok_estado = (m.get("tiktok") or {}).get("estado")

    por_cliente_g, por_cliente_t = {}, {}
    cuentas_sin_cliente = []
    ex = {str(v.get("google_ads")) for k, v in (manual.get("ex_clientes") or {}).items() if not k.startswith("_")}
    for c in cuentas:
        cid = (mapa_gads if c.get("plataforma", "google_ads") == "google_ads" else mapa_tt).get(norm_id(c["id"]))
        if cid:
            (por_cliente_g if c.get("plataforma", "google_ads") == "google_ads" else por_cliente_t).setdefault(cid, []).append(c)
        elif norm_id(c["id"]) not in ex:
            cuentas_sin_cliente.append({"id": c["id"], "nombre": c["nombre"], "plataforma": c.get("plataforma", "google_ads"),
                                        "coste": (c.get("total") or {}).get("coste")})
    sin_gasto_por_nombre = {s["nombre"]: s for s in sin_gasto}

    bloques, con_dato = {}, {k: 0 for k in FUENTES}
    for cid in universo:
        b = {}
        lista = por_cliente_g.get(cid)
        if lista:
            tot = {k: round(sum((x.get("total") or {}).get(k) or 0 for x in lista), 2)
                   for k in ("impresiones", "clics", "coste", "conversiones")}
            b["google_ads"] = bloque(
                FUENTES["google_ads"][0], "bien" if tot["coste"] else "a_cero", hora=iso(hora), medicion=medicion, nota=sello,
                emparejado={"id": ", ".join(x["id"] for x in lista), "nombre": ", ".join(x["nombre"] for x in lista),
                            "metodo": "emparejamientos_manual.json (por id de cuenta)"},
                datos={"periodo": periodo, "total": tot,
                       "cuentas": [{"id": x["id"], "nombre": x["nombre"], "total": x.get("total"),
                                    "ultimo_gasto": x.get("ultimo_gasto"), "campanas": x.get("campanas")} for x in lista]})
            con_dato["google_ads"] += 1
        elif cid in sin_id:
            s = sin_gasto_por_nombre.get(sin_id[cid], {})
            b["google_ads"] = bloque(
                FUENTES["google_ads"][0], "a_cero", hora=iso(hora), medicion=medicion,
                nota=f"campaña parada: último gasto {s.get('ultimo_gasto') or '¿?'}; falta el id de la cuenta",
                emparejado={"id": None, "nombre": sin_id[cid], "metodo": "solo por nombre en Windsor (pendiente de id)"},
                datos={"periodo": periodo, "total": {"coste": 0}, "ultimo_gasto": s.get("ultimo_gasto"), "gasto_2026": s.get("gasto_2026")})
            con_dato["google_ads"] += 1
        elif cid in fuera:
            b["google_ads"] = bloque(FUENTES["google_ads"][0], "sin_conectar",
                                     nota="tiene Google Ads (Looker con conector oficial) pero no está en Windsor: conectarla en Windsor o esperar a gads.py")
        else:
            b["google_ads"] = bloque(FUENTES["google_ads"][0], "no_aplica", nota="sin cuenta de Google Ads conocida")
        tl = por_cliente_t.get(cid)
        if tl:
            tot = {k: round(sum((x.get("total") or {}).get(k) or 0 for x in tl), 2) for k in ("impresiones", "clics", "coste", "conversiones")}
            b["tiktok"] = bloque(FUENTES["tiktok"][0], "bien" if tot["coste"] else "a_cero", hora=iso(hora),
                                 emparejado={"id": ", ".join(x["id"] for x in tl), "nombre": ", ".join(x["nombre"] for x in tl), "metodo": "emparejamientos_manual.json"},
                                 datos={"periodo": periodo, "total": tot})
            con_dato["tiktok"] += 1
        else:
            b["tiktok"] = bloque(FUENTES["tiktok"][0], "sin_conectar" if not real else "no_aplica",
                                 nota=tiktok_estado or "sin cuenta de TikTok emparejada")
        bloques[cid] = b

    fichas = []
    for fid, (nombre, freq, lim) in FUENTES.items():
        ed = edad_h(hora)
        if real:
            estado = "dato_viejo" if (ed is not None and ed > lim) else "bien"
        else:
            estado = "sin_conectar"
        fichas.append({
            "id": fid, "nombre": nombre, "grupo": "captación",
            "origen": str(fichero) if real else str(MUESTRA.relative_to(AQUI.parent)),
            "lector": "~/RO_HERRAMIENTAS/windsor/ws.py", "plan": plan,
            "error": "; ".join(errores) or None, "clave_en_llavero": clave,
            "frecuencia_h": freq, "limite_h": lim, "hora": iso(hora), "edad_h": ed, "estado": estado,
            "clientes_con_dato": con_dato[fid],
            "cuentas_sin_cliente": cuentas_sin_cliente if fid == "google_ads" else None,
            "nota": ("muestra manual: solo totales de septiembre de 7 cuentas" if not real and fid == "google_ads"
                     else (tiktok_estado if not real else None)),
        })
    return {"fichas": fichas, "bloques": bloques}

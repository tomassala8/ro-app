#!/usr/bin/env python3
"""Paneles de herramientas (carril N1) · las vistas estándar de cada herramienta, dentro de la app. SOLO LECTURA.

Qué lee (llaves del llavero, nunca se imprimen; nada se escribe fuera):
  · ga    Google Analytics 4 (gg.py): serie diaria desde 1-ene-2025 (total y por canal) + 10 tablas de los informes
          estándar (adquisición, interacción, eventos clave, páginas, tecnología y lugar) para los 8 periodos comunes,
          cada uno con su periodo anterior y el del año anterior.
  · gsc   Search Console (gg.py): serie diaria de 16 meses + consultas, páginas, países, dispositivos y apariencia en
          la búsqueda por periodo, con su comparación.
  · idx   Indexación: sitemaps enviados y la inspección de URL de las 15 páginas con más clics (Search Console).
  · psi   Experiencia: PageSpeed Insights de la portada (datos de usuarios reales de Chrome y laboratorio), móvil y ordenador.
  · meta  Meta Ads (mt.py): serie diaria por campaña desde 1-ene-2025 y campañas, conjuntos y anuncios por periodo
          (con alcance y frecuencia exactos) y su estado y presupuesto.
  · ghl   GoHighLevel (ghl_agencia/app.py, la llave rota sola y se guarda en el llavero): embudos y etapas,
          oportunidades (fecha, etapa, estado, valor, origen, sin nombres), citas por estado y día, contactos nuevos
          por periodo y conversaciones sin leer.
  · mc    Metricool (mc.py): seguidores, alcance, impresiones, interacción y publicaciones por día y red.
  · desk  Zoho Desk (zh.py): tickets creados y cerrados por día, estado, canal, primera respuesta y resolución.
  · zd    Zadarma (zd.py): llamadas por día, sentido, contestadas y perdidas, duración y extensión.

Escribe data/paneles/<fuente>/<cliente>.json  ({"filas":[{cliente_id, …}]} → servir.py recorta por cartera y quita
gasto/coste/cpl a quien no ve la inversión), data/paneles/indice.json, data/paneles/desk.json y data/paneles/zadarma.json.

Uso:  python3 generar_paneles.py                         # todo en vivo
      python3 generar_paneles.py --fuentes ga,gsc --solo gac,ahedo
      python3 generar_paneles.py --cache                 # rehace data/paneles/ desde _cache/ (0 llamadas)
"""
import json, os, re, sys, time, threading, urllib.parse, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta
from pathlib import Path

AQUI = Path(__file__).resolve().parent
APP = AQUI.parent
sys.path.insert(0, str(APP / "fuentes"))
sys.path.insert(0, str(AQUI))
import comun as C  # noqa: E402
import periodos as PER  # noqa: E402
import meta_mediciones_220 as META220  # noqa: E402
if str(APP) not in sys.path:
    sys.path.insert(2, str(APP))
from fuentes.lectura import leer as leer_api, marcar  # noqa: E402  · N-01/N-06: toda lectura de API se guarda; si falla, la última buena

for p in ("google", "meta", "metricool", "ghl_agencia", "zoho", "zadarma"):
    sys.path.insert(0, os.path.expanduser(f"~/RO_HERRAMIENTAS/{p}"))

CACHE = AQUI / "_cache"
SALIDA = APP / "data" / "paneles"
AHORA = datetime.now().strftime("%Y-%m-%d %H:%M")
HOY = date.today()
ARGS = sys.argv[1:]
SOLO_CACHE = "--cache" in ARGS
SOLO = next((a.split(",") for i, a in enumerate(ARGS) if i and ARGS[i - 1] == "--solo"), None)
TODAS = ["ga", "gsc", "idx", "psi", "meta", "ghl", "mc", "desk", "zd"]
FUENTES = set(next((a.split(",") for i, a in enumerate(ARGS) if i and ARGS[i - 1] == "--fuentes"), TODAS))
DESDE_SERIE = "2025-01-01"
PERIODOS = PER.todos(HOY)
LOCK = threading.Lock()

# Mismas correcciones de emparejamiento que el Informe del cliente (auditoría de cifras 28, 2-oct).
CORRECCIONES = {
    "kiosko-box": {"meta": ("act_292218051469540", "Josep SG")},
    "fusterguell": {"ga4": ("properties/480200463", "FusterGA4 New")},
    "consulting-f": {"ga4": "-", "gsc": "-"},
}
NOTA_SIN = {
    "consulting-f": "La propiedad emparejada era la landing info.consultingf.com; falta acceso de lector a consultingf.com.",
}


def log(*a):
    print(*a, flush=True)


def post_json(tk, url, body, intentos=4):
    for i in range(intentos):
        req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                     headers={"Authorization": "Bearer " + tk, "Content-Type": "application/json"})
        try:
            return json.load(urllib.request.urlopen(req, timeout=120))
        except urllib.error.HTTPError as e:
            msg = e.read().decode()[:300]
            if e.code in (429, 500, 503) and i < intentos - 1:
                time.sleep(3 + 4 * i)
                continue
            return {"_error": e.code, "_msg": msg}
        except Exception as e:  # noqa: BLE001
            if i < intentos - 1:
                time.sleep(2)
                continue
            return {"_error": 0, "_msg": str(e)[:200]}


def get_json(url, headers=None, intentos=3, timeout=120):
    for i in range(intentos):
        try:
            return json.load(urllib.request.urlopen(urllib.request.Request(url, headers=headers or {}), timeout=timeout))
        except urllib.error.HTTPError as e:
            msg = e.read().decode()[:300]
            if e.code in (429, 500, 502, 503) and i < intentos - 1:
                time.sleep(4 + 6 * i)
                continue
            return {"_error": e.code, "_msg": re.sub(r"(access_token|key)=[^&\s]+", r"\1=…", msg)}
        except Exception as e:  # noqa: BLE001
            if i < intentos - 1:
                time.sleep(3)
                continue
            return {"_error": 0, "_msg": str(e)[:200]}


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


def r2(x, n=2):
    return round(float(x), n) if x is not None else None


def sin_query(u):
    """Sin parámetros: nunca viajan valores de formularios, correos ni claves en una URL."""
    if not isinstance(u, str):
        return u
    return C.sanear(u.split("?")[0].split("#")[0])


def cache_leer(fuente, cid):
    return C.leer(CACHE / fuente / f"{cid}.json")


def cache_escribir(fuente, cid, obj):
    ruta = CACHE / fuente / f"{cid}.json"
    ruta.parent.mkdir(parents=True, exist_ok=True)
    tmp = ruta.with_suffix(".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")))
    os.replace(tmp, ruta)


def lectura_fuente(fuente, cid, fn):
    """N-06: la lectura de una fuente para un cliente pasa por la base. Si la API falla (o devuelve `_error`), se escribe en la
    caché la última lectura buena con `_viejo` y `_desde` (la ficha dirá «dato_viejo»); «rota» solo si nunca hubo dato."""
    ultimo = []

    def cuerpo():
        r = fn()
        ultimo.append(r)
        if isinstance(r, dict) and r.get("_error"):
            raise RuntimeError(f"{fuente} {cid}: {r['_error']} {r.get('_msg', '')}".strip()[:300])
        return r
    l = leer_api(f"paneles_{fuente}", cid, cuerpo)
    if l.estado == "ok":
        cache_escribir(fuente, cid, l.datos)
    elif l.estado == "viejo":
        cache_escribir(fuente, cid, marcar(l))
    else:   # sin dato en la base: lo último bueno de la caché de ficheros, o lo que dio la API (con su `_error`), como hoy
        previa = cache_leer(fuente, cid)
        if isinstance(previa, dict) and previa and not previa.get("_error"):
            cache_escribir(fuente, cid, {**previa, "_viejo": True, "_desde": previa.get("leido")})
        else:
            cache_escribir(fuente, cid, ultimo[0] if ultimo else {"_error": l.error or "sin respuesta", "leido": AHORA})


# ====================================================================== clientes y emparejamientos
def clientes():
    emp = (C.leer(APP / "data" / "emparejamientos.json", {}) or {}).get("clientes", {})
    vivo = C.leer(APP / "fuentes_informe" / "_cache" / "vivo.json", {}) or {}
    out = []
    for f in sorted((APP / "data" / "clientes").glob("*.json")):
        d = C.leer(f)
        if not d:
            continue
        cid = d["id"]
        e = emp.get(cid, {})
        x = {"id": cid, "nombre": d.get("nombre"), "web": d.get("web")}
        for k in ("ga4", "gsc", "metricool", "ghl", "meta", "seranking"):
            x[k] = (e.get(k) or {}).get("id")
            x[k + "_nombre"] = (e.get(k) or {}).get("nombre")
        v = vivo.get(cid) or {}
        if v.get("ga_prop"):
            x["ga4"], x["ga4_nombre"] = v["ga_prop"], v.get("ga_nombre") or x["ga4_nombre"]
        if v.get("gsc_sitio"):
            x["gsc"] = v["gsc_sitio"]
        cor = CORRECCIONES.get(cid, {})
        for k, val in cor.items():
            if val == "-":
                x[k] = None
            else:
                x[k], x[k + "_nombre"] = val
        x["nota_sin"] = NOTA_SIN.get(cid)
        out.append(x)
    return out


# ====================================================================== Google Analytics 4
GA_TOT = ["activeUsers", "newUsers", "sessions", "engagedSessions", "engagementRate", "averageSessionDuration",
          "screenPageViews", "keyEvents", "eventCount", "bounceRate"]
GA_DIA = ["activeUsers", "newUsers", "sessions", "engagedSessions", "keyEvents", "screenPageViews", "eventCount", "userEngagementDuration"]
GA_TABLAS = {
    # id: (dimensiones, métricas, filas)
    "canales": (["sessionDefaultChannelGroup"], ["activeUsers", "sessions", "engagedSessions", "keyEvents", "averageSessionDuration"], 20),
    "fuentes": (["sessionSourceMedium"], ["activeUsers", "sessions", "engagedSessions", "keyEvents", "averageSessionDuration"], 25),
    "campanas": (["sessionCampaignName"], ["sessions", "engagedSessions", "keyEvents"], 15),
    "primer_canal": (["firstUserDefaultChannelGroup"], ["newUsers", "activeUsers", "keyEvents"], 15),
    "paginas": (["pagePath"], ["screenPageViews", "activeUsers", "userEngagementDuration", "keyEvents"], 25),
    "destino": (["landingPage"], ["sessions", "activeUsers", "engagedSessions", "keyEvents"], 25),
    "eventos": (["eventName"], ["eventCount", "totalUsers", "keyEvents"], 25),
    "dispositivos": (["deviceCategory"], ["activeUsers", "sessions", "engagedSessions", "keyEvents"], 6),
    "paises": (["country"], ["activeUsers", "sessions", "keyEvents"], 15),
    "ciudades": (["city"], ["activeUsers", "sessions", "keyEvents"], 15),
}


PAISES_EN = {"Spain": "España", "Andorra": "Andorra", "France": "Francia", "Portugal": "Portugal", "Mexico": "México", "Argentina": "Argentina",
             "Colombia": "Colombia", "United States": "Estados Unidos", "United Kingdom": "Reino Unido", "Germany": "Alemania", "Italy": "Italia",
             "Chile": "Chile", "Peru": "Perú", "Venezuela": "Venezuela", "Ecuador": "Ecuador", "Belgium": "Bélgica", "Netherlands": "Países Bajos",
             "Switzerland": "Suiza", "Morocco": "Marruecos", "Ireland": "Irlanda", "Uruguay": "Uruguay", "Dominican Republic": "República Dominicana",
             "Brazil": "Brasil", "China": "China", "India": "India", "Romania": "Rumanía", "Poland": "Polonia", "Singapore": "Singapur",
             "Seychelles": "Seychelles", "Sweden": "Suecia", "Finland": "Finlandia", "Canada": "Canadá", "Russia": "Rusia", "Ukraine": "Ucrania",
             "Hong Kong": "Hong Kong", "Japan": "Japón", "Vietnam": "Vietnam", "Turkey": "Turquía", "Türkiye": "Turquía", "Austria": "Austria",
             "Denmark": "Dinamarca", "Norway": "Noruega", "Greece": "Grecia", "Cuba": "Cuba", "Bolivia": "Bolivia", "Paraguay": "Paraguay",
             "Panama": "Panamá", "Costa Rica": "Costa Rica", "Guatemala": "Guatemala", "Honduras": "Honduras", "Algeria": "Argelia"}
CANALES = {"Organic Search": "Búsqueda orgánica", "Direct": "Directo", "Referral": "Sitios de referencia", "Organic Social": "Redes sociales orgánicas",
           "Paid Search": "Búsqueda de pago", "Paid Social": "Redes sociales de pago", "Email": "Correo electrónico", "Unassigned": "Sin asignar",
           "Display": "Display", "Cross-network": "Varias redes", "AI Assistant": "Asistentes de IA", "Organic Video": "Vídeo orgánico",
           "Paid Video": "Vídeo de pago", "Paid Other": "Otro de pago", "Organic Shopping": "Shopping orgánico", "Paid Shopping": "Shopping de pago",
           "Affiliates": "Afiliados", "SMS": "SMS", "Mobile Push Notifications": "Notificaciones móviles", "Audio": "Audio"}


def ga_batch(tk, prop, reqs):
    r = post_json(tk, f"https://analyticsdata.googleapis.com/v1beta/{prop}:batchRunReports", {"requests": reqs})
    if "_error" in r:
        m = re.search(r'"message":\s*"([^"]{0,140})', r['_msg'])
        return None, f"{r['_error']} {m.group(1) if m else r['_msg'][:100]}"
    return r.get("reports", []), None


def ga_filas(rep):
    dims = [d["name"] for d in rep.get("dimensionHeaders", [])]
    for row in rep.get("rows", []) or []:
        dv = [x["value"] for x in row.get("dimensionValues", [])]
        yield dict(zip(dims, dv)), [num(m["value"]) for m in row.get("metricValues", [])]


def ga_rangos(p):
    return [{"startDate": p["desde"], "endDate": p["hasta"], "name": "a"},
            {"startDate": p["anterior"][0], "endDate": p["anterior"][1], "name": "b"},
            {"startDate": p["anio_ant"][0], "endDate": p["anio_ant"][1], "name": "c"}]


def limpiar_dim(tabla, v):
    if tabla in ("paginas", "destino"):
        return sin_query(v) or "(sin página)"
    if v in ("(not set)", "", "(other)"):
        return "(sin dato)" if v != "(other)" else "(otros)"
    if tabla in ("paises",):
        return PAISES_EN.get(v, v)
    if tabla in ("canales", "primer_canal"):
        return CANALES.get(v, v)
    if tabla == "dispositivos":
        return {"mobile": "Móvil", "desktop": "Ordenador", "tablet": "Tableta", "smart tv": "Televisión"}.get(v, v)
    return C.sanear(v)[:120]


def ga_leer(tk, c):
    prop = c["ga4"]
    out = {"propiedad": prop, "nombre": c.get("ga4_nombre"), "leido": AHORA, "periodos": {}, "errores": []}
    # serie diaria total y por canal
    ini = DESDE_SERIE
    reps, err = ga_batch(tk, prop, [
        {"dateRanges": [{"startDate": ini, "endDate": "today"}], "dimensions": [{"name": "date"}], "metrics": [{"name": m} for m in GA_DIA], "limit": 1000},
        {"dateRanges": [{"startDate": ini, "endDate": "today"}], "dimensions": [{"name": "date"}, {"name": "sessionDefaultChannelGroup"}],
         "metrics": [{"name": m} for m in ("sessions", "engagedSessions", "keyEvents", "newUsers")], "limit": 20000},
    ])
    if err:
        out["errores"].append(f"serie: {err}")
        out["_error"] = err
        return out
    out["serie"] = {f"{d['date'][:4]}-{d['date'][4:6]}-{d['date'][6:]}": [round(x, 1) for x in v] for d, v in ga_filas(reps[0])}
    canal = {}
    for d, v in ga_filas(reps[1]):
        k = f"{d['date'][:4]}-{d['date'][4:6]}-{d['date'][6:]}"
        canal.setdefault(limpiar_dim("canales", d["sessionDefaultChannelGroup"]), {})[k] = [int(x) for x in v]
    out["serie_canal"] = canal
    # tablas por periodo
    for p in PERIODOS:
        R = ga_rangos(p)
        reqs = [{"dateRanges": R, "metrics": [{"name": m} for m in GA_TOT]}]
        ids = list(GA_TABLAS)
        for t in ids:
            dims, mets, n = GA_TABLAS[t]
            reqs.append({"dateRanges": R, "dimensions": [{"name": d} for d in dims], "metrics": [{"name": m} for m in mets],
                         "orderBys": [{"metric": {"metricName": mets[0]}, "desc": True}], "limit": n * 4})
        res = []
        for i in range(0, len(reqs), 5):
            reps, err = ga_batch(tk, prop, reqs[i:i + 5])
            if err:
                out["errores"].append(f"{p['id']}: {err}")
                reps = [{}] * len(reqs[i:i + 5])
            res += reps
        per = {"tot": {}}
        for d, v in ga_filas(res[0]):
            per["tot"][{"a": "a", "b": "b", "c": "c"}.get(d.get("dateRange"), "a")] = [r2(x, 4) for x in v]
        for t, rep in zip(ids, res[1:]):
            dims, mets, n = GA_TABLAS[t]
            agg = {}
            for d, v in ga_filas(rep):
                k = limpiar_dim(t, d[dims[0]])
                rng = d.get("dateRange", "a")
                fila = agg.setdefault(k, {"a": [0] * len(mets), "b": [0] * len(mets), "c": [0] * len(mets)})
                # varias páginas pueden quedar iguales tras quitar parámetros: se suman (las medias, ponderadas aparte no hacen falta aquí)
                fila[rng] = [round(x + y, 2) for x, y in zip(fila[rng], v)]
            orden = sorted(agg.items(), key=lambda kv: -kv[1]["a"][0])[:n]
            per[t] = [[k, v["a"], v["b"], v["c"]] for k, v in orden]
        out["periodos"][p["id"]] = per
    return out


# ====================================================================== Search Console
def gsc_q(tk, site, body):
    return post_json(tk, f"https://www.googleapis.com/webmasters/v3/sites/{urllib.parse.quote(site, safe='')}/searchAnalytics/query", body)


GSC_TABLAS = {"consultas": ("query", 25), "paginas": ("page", 25), "paises": ("country", 15), "dispositivos": ("device", 5), "apariencia": ("searchAppearance", 10)}
PAISES = {"esp": "España", "and": "Andorra", "fra": "Francia", "prt": "Portugal", "mex": "México", "arg": "Argentina", "col": "Colombia",
          "usa": "Estados Unidos", "gbr": "Reino Unido", "deu": "Alemania", "ita": "Italia", "chl": "Chile", "per": "Perú", "ven": "Venezuela",
          "ecu": "Ecuador", "bel": "Bélgica", "nld": "Países Bajos", "che": "Suiza", "mar": "Marruecos", "irl": "Irlanda", "ury": "Uruguay",
          "dom": "República Dominicana", "bra": "Brasil", "chn": "China", "ind": "India", "rou": "Rumanía", "pol": "Polonia"}
DISPOSITIVOS = {"MOBILE": "Móvil", "DESKTOP": "Ordenador", "TABLET": "Tableta"}


def gsc_leer(tk, c):
    site = c["gsc"]
    out = {"sitio": site, "leido": AHORA, "periodos": {}, "errores": []}
    a0 = (HOY - timedelta(days=486)).isoformat()
    r = gsc_q(tk, site, {"startDate": a0, "endDate": HOY.isoformat(), "dimensions": ["date"], "rowLimit": 600, "dataState": "final"})
    if "_error" in r:
        out["_error"] = f"{r['_error']} {r['_msg'][:160]}"
        return out
    out["serie"] = {x["keys"][0]: [int(x["clicks"]), int(x["impressions"]), r2(x["position"], 2)] for x in r.get("rows", [])}
    dias = sorted(out["serie"])
    out["hasta"] = dias[-1] if dias else None
    out["desde_dato"] = dias[0] if dias else None
    hasta = out["hasta"]
    trabajos = []
    for p in PERIODOS:
        if p["id"] in ("hoy", "ayer") or not hasta:
            continue
        rangos = {"a": (p["desde"], min(p["hasta"], hasta)), "b": tuple(p["anterior"]), "c": tuple(p["anio_ant"])}
        # Search Console va 2-3 días por detrás: se cortan los tres rangos a los mismos días que tiene el actual.
        corte = (date.fromisoformat(rangos["a"][1]) - date.fromisoformat(p["desde"])).days
        if corte < 0:
            continue
        for k in ("b", "c"):
            a = date.fromisoformat(rangos[k][0])
            rangos[k] = (rangos[k][0], min(rangos[k][1], (a + timedelta(days=corte)).isoformat()))
        out["periodos"][p["id"]] = {"rangos": rangos}
        for t, (dim, n) in GSC_TABLAS.items():
            for k in ("a", "b", "c"):
                if k == "c" and t in ("paises", "dispositivos", "apariencia"):
                    continue
                if rangos[k][0] < out["desde_dato"]:
                    continue
                trabajos.append((p["id"], t, dim, n, k, rangos[k]))

    def hacer(tr):
        pid, t, dim, n, k, (a, b) = tr
        return tr, gsc_q(tk, site, {"startDate": a, "endDate": b, "dimensions": [dim], "rowLimit": n if k == "a" else 250, "dataState": "final"})
    with ThreadPoolExecutor(6) as ex:
        res = list(ex.map(hacer, trabajos))
    crudo = {}
    for (pid, t, dim, n, k, _), rr in res:
        if "_error" in rr:
            out["errores"].append(f"{pid} {t} {k}: {rr['_error']}")
            continue
        crudo[(pid, t, k)] = rr.get("rows", [])
    for pid, per in out["periodos"].items():
        for t, (dim, n) in GSC_TABLAS.items():
            filas = {}
            for k in ("a", "b", "c"):
                for x in crudo.get((pid, t, k), []):
                    key = x["keys"][0]
                    if t == "paginas":
                        key = sin_query(key)
                    elif t == "consultas":
                        if C.consulta_basura(key):
                            continue
                        key = C.sanear(key)
                    elif t == "paises":
                        key = PAISES.get(key, key.upper())
                    elif t == "dispositivos":
                        key = DISPOSITIVOS.get(key, key)
                    if k != "a" and key not in filas:
                        continue
                    filas.setdefault(key, {})[k] = [int(x["clicks"]), int(x["impressions"]), r2(x["position"], 1)]
            per[t] = [[k, v.get("a"), v.get("b"), v.get("c")] for k, v in filas.items()][:n]
    return out


def idx_leer(tk, c, top_paginas):
    site = c["gsc"]
    out = {"sitio": site, "leido": AHORA, "sitemaps": [], "inspeccion": []}
    sm = get_json(f"https://www.googleapis.com/webmasters/v3/sites/{urllib.parse.quote(site, safe='')}/sitemaps", {"Authorization": "Bearer " + tk})
    if "_error" in sm:
        out["_error_sitemaps"] = f"{sm['_error']}"
    for s in sm.get("sitemap", []) or []:
        cont = s.get("contents") or [{}]
        out["sitemaps"].append({"ruta": sin_query(s.get("path")), "enviado": (s.get("lastSubmitted") or "")[:10], "leido": (s.get("lastDownloaded") or "")[:10],
                                "pendiente": s.get("isPending"), "es_indice": s.get("isSitemapsIndex"), "avisos": int(num(s.get("warnings"))), "errores": int(num(s.get("errors"))),
                                "urls": int(sum(num(x.get("submitted")) for x in cont))})
    for url in top_paginas[:15]:
        r = post_json(tk, "https://searchconsole.googleapis.com/v1/urlInspection/index:inspect", {"inspectionUrl": url, "siteUrl": site, "languageCode": "es-ES"})
        if "_error" in r:
            out["inspeccion"].append({"url": sin_query(url), "_error": r["_error"]})
            if r["_error"] in (403, 429):
                break
            continue
        ir = (r.get("inspectionResult") or {})
        ix = ir.get("indexStatusResult") or {}
        mob = ir.get("mobileUsabilityResult") or {}
        out["inspeccion"].append({"url": sin_query(url), "veredicto": ix.get("verdict"), "cobertura": ix.get("coverageState"),
                                  "rastreo": (ix.get("lastCrawlTime") or "")[:10], "robots": ix.get("robotsTxtState"), "indexar": ix.get("indexingState"),
                                  "canonica_google": sin_query(ix.get("googleCanonical")), "canonica_usuario": sin_query(ix.get("userCanonical")),
                                  "movil": mob.get("verdict")})
    return out


_PSI = {}


def PSI_CLAVE():
    """Clave de API de Google para PageSpeed (llavero «google_api_key»). Sin clave, Google corta a las pocas consultas al día."""
    if "k" not in _PSI:
        import subprocess
        try:
            _PSI["k"] = subprocess.check_output(["security", "find-generic-password", "-s", "google_api_key", "-w"], text=True, stderr=subprocess.DEVNULL).strip() or None
        except Exception:  # noqa: BLE001
            _PSI["k"] = None
    return _PSI["k"]


def psi_leer(c):
    web = c.get("web")
    if not web:
        return {"_error": "sin web"}
    out = {"url": sin_query(web), "leido": AHORA}
    for est in ("mobile", "desktop"):
        clave = PSI_CLAVE()
        q = urllib.parse.urlencode({"url": web, "strategy": est, "locale": "es", "category": "performance", **({"key": clave} if clave else {})})
        r = get_json(f"https://www.googleapis.com/pagespeedonline/v5/runPagespeed?{q}", intentos=2, timeout=150)
        if "_error" in r:
            out[est] = {"_error": r["_error"], "_msg": r.get("_msg", "")[:120]}
            continue
        le = r.get("loadingExperience") or {}
        met = le.get("metrics") or {}
        campo = {k: {"p75": (met.get(k) or {}).get("percentile"), "cat": (met.get(k) or {}).get("category")}
                 for k in ("LARGEST_CONTENTFUL_PAINT_MS", "INTERACTION_TO_NEXT_PAINT", "CUMULATIVE_LAYOUT_SHIFT_SCORE", "FIRST_CONTENTFUL_PAINT_MS", "EXPERIMENTAL_TIME_TO_FIRST_BYTE")
                 if met.get(k)}
        lh = r.get("lighthouseResult") or {}
        au = lh.get("audits") or {}
        lab = {k: (au.get(k) or {}).get("numericValue") for k in ("largest-contentful-paint", "cumulative-layout-shift", "total-blocking-time", "first-contentful-paint", "speed-index")}
        out[est] = {"nota": r2(((lh.get("categories") or {}).get("performance") or {}).get("score"), 2), "campo": campo,
                    "campo_global": le.get("overall_category"), "campo_origen": bool(le.get("origin_fallback")), "lab": lab}
    return out


# ====================================================================== Meta Ads
def leads_de(actions):
    return META220.leads(actions)[0]


def meta_paginar(tk, path, **q):
    q["access_token"] = tk
    url = f"https://graph.facebook.com/v26.0{path}?" + urllib.parse.urlencode(q)
    datos, n = [], 0
    while url and n < 60:
        r = get_json(url)
        if "_error" in r:
            return datos, f"{r['_error']} {r.get('_msg', '')[:160]}"
        datos += r.get("data", []) or []
        url = (r.get("paging") or {}).get("next")
        n += 1
    return datos, "paginacion_incompleta" if url else None


def meta_leer(tk, c):
    from datetime import timezone
    from zoneinfo import ZoneInfo
    try:
        from fuentes_paneles import meta_envelope_373 as META373
    except ModuleNotFoundError:
        import meta_envelope_373 as META373
    leido_utc = datetime.now(timezone.utc)
    cuenta = c["meta"]
    out = {"cuenta": cuenta, "nombre": c.get("meta_nombre"), "leido": AHORA, "errores": [], "medicion_meta": META220.descriptor(AHORA)}
    info = get_json(f"https://graph.facebook.com/v26.0/{cuenta}?" + urllib.parse.urlencode({"access_token": tk, "fields": "account_id,name,account_status,currency,timezone_name"}))
    if "_error" in info:
        out["_error"] = "lectura_cuenta_meta_fallida"
        return out
    out["estado_cuenta"], out["moneda"] = info.get("account_status"), META220.contexto_cuenta(cuenta, info.get("currency"))["moneda"]
    out["zona_horaria"] = None
    aid = cuenta.removeprefix("act_") if isinstance(cuenta, str) else None
    try:
        zona_cuenta = ZoneInfo(info["timezone_name"])
        out["zona_horaria"] = zona_cuenta.key
        hasta_diaria = min(HOY, leido_utc.astimezone(zona_cuenta).date())
    except (KeyError, TypeError, ValueError):
        hasta_diaria = HOY  # compatibilidad legacy; ninguna zona/medición se inventa.
    out["mediciones_diarias_373"] = None
    # estado y presupuesto
    for nivel, campos in (("campaigns", "name,effective_status,objective,daily_budget,lifetime_budget"),
                          ("adsets", "name,effective_status,campaign_id,daily_budget,lifetime_budget,optimization_goal"),
                          ("ads", "name,effective_status,adset_id,campaign_id")):
        d, err = meta_paginar(tk, f"/{cuenta}/{nivel}", fields=campos, limit=200)
        if err:
            out["errores"].append(f"{nivel}: lectura_incompleta")
        out[nivel] = {x["id"]: {"nombre": C.sanear(x.get("name")), "estado": x.get("effective_status"), "objetivo": x.get("objective") or x.get("optimization_goal"),
                               "inversion_diaria": META220.numero(x.get("daily_budget")) / 100 if META220.numero(x.get("daily_budget")) is not None else None,
                               "inversion_total": META220.numero(x.get("lifetime_budget")) / 100 if META220.numero(x.get("lifetime_budget")) is not None else None,
                               "campana": x.get("campaign_id"), "conjunto": x.get("adset_id")} for x in d}
    # serie diaria por campaña
    d, a, paginas_completas = [], date.fromisoformat(DESDE_SERIE), True
    while a <= hasta_diaria:   # por tramos de 90 días: las cuentas grandes dan error con todo de golpe
        b = min(a + timedelta(days=89), hasta_diaria)
        x, err = meta_paginar(tk, f"/{cuenta}/insights", level="campaign", time_increment=1, limit=500,
                              fields="account_id,campaign_id,spend,impressions,clicks,inline_link_clicks,actions",
                              time_range=json.dumps({"since": a.isoformat(), "until": b.isoformat()}))
        if err:
            paginas_completas = False
            out["errores"].append(f"serie {a}: lectura_incompleta")
        d += x
        a = b + timedelta(days=1)
    leido_utc = datetime.now(timezone.utc)  # fin de lectura diaria, no fecha revivida del caché
    try:
        out["mediciones_diarias_373"] = META373.proyectar({
            "request": {"cuenta_id": aid, "level": "campaign", "time_increment": 1,
                        "desde": DESDE_SERIE, "hasta": hasta_diaria.isoformat()},
            "account": {"id": info.get("account_id"), "currency": info.get("currency"), "timezone_name": info.get("timezone_name")},
            "leido_utc": leido_utc.isoformat(), "response": {"data": d}, "paginas_completas": paginas_completas},
            [{"cliente_id": c.get("id"), "cuenta_id": aid, "moneda": info.get("currency"),
              "zona": info.get("timezone_name"), "confirmada": True}])
    except ValueError:
        out["errores"].append("mediciones_diarias_373: contexto_o_periodo_no_acreditado")
    serie = {}
    for x in d:
        fila = META220.fila(x, AHORA, 'campaign_diario', cuenta=cuenta, moneda=out.get('moneda'))
        if not fila['medicion']['periodo_valido'] or x['date_start'] != x['date_stop'] or not DESDE_SERIE <= x['date_start'] <= HOY.isoformat() or not isinstance(x.get('campaign_id'), str) or not x['campaign_id']:
            out['errores'].append('Serie: identidad o periodo diario inválido; fila apartada.')
            continue
        vector = [fila[k] for k in ('gasto', 'impresiones', 'clics', 'clics_enlace', 'leads')]
        dias = serie.setdefault(x['campaign_id'], {})
        if x['date_start'] in dias and dias[x['date_start']] != vector:
            dias[x['date_start']] = [None] * 5
            out['errores'].append('Serie: fila repetida discordante; medición desconocida.')
        else:
            dias[x['date_start']] = vector
    out["gasto_serie"] = serie   # [gasto, impresiones, clics, clics en el enlace, leads] · «gasto*» lo recorta servir.py
    # por periodo (exacto: alcance y frecuencia no se pueden sumar por días)
    rangos = []
    for p in PERIODOS:
        rangos += [(p["desde"], p["hasta"]), tuple(p["anterior"])]
    rangos = list(dict.fromkeys(rangos))
    tr = json.dumps([{"since": a, "until": b} for a, b in rangos])
    out["periodos"] = {}
    for nivel, idc in (("account", None), ("campaign", "campaign_id"), ("adset", "adset_id"), ("ad", "ad_id")):
        campos = "spend,impressions,reach,frequency,clicks,inline_link_clicks,actions" + (f",{idc}" if idc else "")
        d, err = meta_paginar(tk, f"/{cuenta}/insights", level=nivel, fields=campos, time_ranges=tr, limit=500)
        if err:   # reintento rango a rango
            d, errs = [], []
            for a, b in rangos:
                x, e2 = meta_paginar(tk, f"/{cuenta}/insights", level=nivel, fields=campos, time_range=json.dumps({"since": a, "until": b}), limit=500)
                d += x
                if e2:
                    errs.append(f"{a}: lectura_incompleta")
            if errs:
                out["errores"].append(f"{nivel}: {'; '.join(errs)[:300]}")
        for x in d:
            fila = META220.fila(x, AHORA, nivel, cuenta=cuenta, moneda=out.get('moneda'))
            if not fila['medicion']['periodo_valido'] or (x['date_start'], x['date_stop']) not in rangos or (idc and (not isinstance(x.get(idc), str) or not x[idc])):
                out['errores'].append(f'{nivel}: identidad o periodo inválido; fila apartada.')
                continue
            k = f"{x['date_start']}|{x['date_stop']}"
            dest = out['periodos'].setdefault(k, {})
            target = dest.setdefault(nivel, {}) if idc else dest
            key = x[idc] if idc else 'cuenta'
            if key in target and target[key] != fila:
                for campo in (*META220.CAMPOS, 'leads'):
                    fila[campo] = None
                fila['medicion']['campos_observados'] = []
                out['errores'].append(f'{nivel}: fila repetida discordante; medición desconocida.')
            target[key] = fila
    return out


# ====================================================================== GoHighLevel
class GHL:
    def __init__(self):
        import app  # ~/RO_HERRAMIENTAS/ghl_agencia/app.py
        self.app = app
        c = C.leer(Path.home() / ".cache" / "ro_tokens" / "paneles_ghl.json")
        if c and time.time() - c.get("t", 0) < 12 * 3600:
            self.tk, self.co = c["tk"], c["co"]
        else:
            self.tk, est = app.acceso()          # rota la llave y la guarda sola en el llavero (no se imprime)
            self.co = est["companyId"]
            ruta = Path.home() / ".cache" / "ro_tokens" / "paneles_ghl.json"
            ruta.parent.mkdir(parents=True, exist_ok=True)
            fd = os.open(ruta, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, "w") as f:
                json.dump({"tk": self.tk, "co": self.co, "t": time.time()}, f)

    def req(self, loc, metodo, ruta, cuerpo=None, **q):
        with LOCK:
            lt = self.app.token_sub(self.tk, self.co, loc)
        url = self.app.API + ruta + ("?" + urllib.parse.urlencode(q) if q else "")
        err = "sin respuesta"
        for intento in range(5):
            r = urllib.request.Request(url, data=json.dumps(cuerpo).encode() if cuerpo is not None else None, method=metodo,
                                       headers={"Authorization": "Bearer " + lt, "Version": "2021-07-28", "Accept": "application/json",
                                                "Content-Type": "application/json", "User-Agent": "panel-ro/1.0"})
            try:
                return json.load(urllib.request.urlopen(r, timeout=60))
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    time.sleep(2 + 2 * intento)
                    continue
                return {"_error": e.code, "_msg": e.read().decode()[:200]}
            except Exception as e:  # noqa: BLE001
                err = str(e)[:120]
                time.sleep(2 + 2 * intento)
        return {"_error": "red", "_msg": err}


def ms(d):
    return int(datetime.combine(d, datetime.min.time()).timestamp() * 1000)


def ghl_leer(g, c):
    loc = c["ghl"]
    out = {"subcuenta": loc, "nombre": C.sanear(c.get("ghl_nombre")), "leido": AHORA, "errores": []}
    pl = g.req(loc, "GET", "/opportunities/pipelines", locationId=loc)
    if "_error" in pl:
        out["_error"] = f"{pl['_error']} {pl.get('_msg', '')[:120]}"
        return out
    out["embudos"] = [{"id": p["id"], "nombre": C.sanear(p.get("name")), "etapas": [{"id": s["id"], "nombre": C.sanear(s.get("name"))} for s in p.get("stages", [])]}
                      for p in pl.get("pipelines", [])]
    opps, pagina, corte = [], 1, DESDE_SERIE
    while pagina <= 40:
        r = g.req(loc, "GET", "/opportunities/search", location_id=loc, limit=100, page=pagina, status="all", order="added_desc")
        if "_error" in r:
            out["errores"].append(f"oportunidades {r['_error']}")
            break
        lote = r.get("opportunities", []) or []
        for o in lote:
            opps.append([(o.get("createdAt") or "")[:10], o.get("pipelineId"), o.get("pipelineStageId"), o.get("status"),
                         r2(num(o.get("monetaryValue"))), C.sanear((o.get("source") or "")[:60]) or None,
                         (o.get("lastStatusChangeAt") or "")[:10] or None, (o.get("lastStageChangeAt") or "")[:10] or None])
        if len(lote) < 100 or (lote and (lote[-1].get("createdAt") or "9")[:10] < corte):
            break
        pagina += 1
    out["oportunidades"] = opps   # [creada, embudo, etapa, estado, valor, origen, cambio de estado, cambio de etapa] · sin nombres
    out["oportunidades_total"] = len(opps)
    # citas por día y estado (90 días atrás y 30 adelante)
    cals = g.req(loc, "GET", "/calendars/", locationId=loc)
    citas = {}
    t0, t1 = ms(HOY - timedelta(days=400)), ms(HOY + timedelta(days=31))
    for cal in (cals.get("calendars", []) if "_error" not in cals else []):
        e = g.req(loc, "GET", "/calendars/events", locationId=loc, calendarId=cal["id"], startTime=t0, endTime=t1)
        if "_error" in e:
            out["errores"].append(f"citas {e['_error']}")
            continue
        for ev in e.get("events", []) or []:
            dia = (ev.get("startTime") or "")[:10]
            est = ev.get("appointmentStatus") or ev.get("status") or "sin_estado"
            citas.setdefault(dia, {}).setdefault(est, 0)
            citas[dia][est] += 1
    out["citas"] = citas
    out["calendarios"] = len(cals.get("calendars", []) or []) if "_error" not in cals else None
    # contactos nuevos por periodo (total exacto con un filtro por fecha)
    nuevos = {}
    for p in PERIODOS:
        for k, (a, b) in (("a", (p["desde"], p["hasta"])), ("b", tuple(p["anterior"])), ("c", tuple(p["anio_ant"]))):
            r = g.req(loc, "POST", "/contacts/search", {"locationId": loc, "pageLimit": 1, "filters": [
                {"field": "dateAdded", "operator": "range", "value": {"gte": f"{a}T00:00:00Z", "lte": f"{b}T23:59:59Z"}}]})
            nuevos.setdefault(p["id"], {})[k] = r.get("total") if "_error" not in r else None
    out["contactos_nuevos"] = nuevos
    tot = g.req(loc, "POST", "/contacts/search", {"locationId": loc, "pageLimit": 1})
    out["contactos_total"] = tot.get("total") if "_error" not in tot else None
    # conversaciones sin leer (foto de ahora)
    cv = g.req(loc, "GET", "/conversations/search", locationId=loc, limit=100, sort="desc", sortBy="last_message_date")
    if "_error" not in cv:
        conv = cv.get("conversations", []) or []
        out["conversaciones"] = {"total": cv.get("total"), "sin_leer": sum(1 for x in conv if (x.get("unreadCount") or 0) > 0),
                                 "mensajes_sin_leer": int(sum(num(x.get("unreadCount")) for x in conv)),
                                 "por_tipo": {t: sum(1 for x in conv if (x.get("lastMessageType") or "") == t) for t in {x.get("lastMessageType") or "" for x in conv}},
                                 "ultima": max((x.get("lastMessageDate") or 0 for x in conv), default=None), "muestra": len(conv)}
    return out


# ====================================================================== Metricool
MC_MET = {
    "instagram": ["followers", "reach", "impressions", "postsInteractions", "profileViews", "postsCount"],
    "facebook": ["followers", "pageImpressions", "pageViews", "postsInteractions", "postsCount"],
    "linkedin": ["followers", "impressions", "interactions", "postsCount", "pageViews"],
}


def mc_leer(c):
    import mc
    out = {"marca": c["metricool"], "nombre": c.get("metricool_nombre"), "leido": AHORA, "redes": {}, "errores": []}
    f0, f1 = f"{(HOY - timedelta(days=420)).isoformat()}T00:00:00", f"{HOY.isoformat()}T23:59:59"
    for net, mets in MC_MET.items():
        for met in mets:
            q = {"userId": mc.llave("metricool_user_id"), "blogId": c["metricool"], "from": f0, "to": f1, "metric": met, "network": net, "subject": "account", "timezone": "Europe/Madrid"}
            r = get_json("https://app.metricool.com/api/v2/analytics/timelines?" + urllib.parse.urlencode(q), {"X-Mc-Auth": mc.llave("metricool_token"), "Accept": "application/json"}, intentos=2)
            if "_error" in r:
                if r["_error"] not in (400, 404):
                    out["errores"].append(f"{net}/{met}: {r['_error']}")
                continue
            vals = ((r.get("data") or [{}])[0] or {}).get("values", []) if isinstance(r, dict) else []
            s = {}
            for v in vals:
                d = (v.get("dateTime") or v.get("date") or "")[:10]
                if d and v.get("value") is not None:
                    s[d] = v["value"]
            if s:
                out["redes"].setdefault(net, {})[met] = s
    return out


# ====================================================================== Zoho Desk y Zadarma (nivel empresa: dirección y operaciones)
def desk_leer():
    import zh
    tk, _ = zh.acceso()
    base = "https://desk.zoho.eu/api/v1"
    orgs = zh.get(tk, f"{base}/organizations")
    org = str((orgs.get("data") or [{}])[0].get("id"))
    deps = zh.get(tk, f"{base}/departments?limit=100", orgId=org).get("data") or []
    tickets, legibles = [], []
    corte = (HOY - timedelta(days=400)).isoformat()
    for d in deps:
        frm, n = 1, 0
        while frm < 5000:
            r = zh.get(tk, f"{base}/tickets?departmentId={d['id']}&from={frm}&limit=100&sortBy=-createdTime&include=assignee", orgId=org)
            if "_error" in r or not isinstance(r, dict):
                break
            if not n:
                legibles.append(C.sanear(d.get("name", "").strip()))
            lote = r.get("data") or []
            for t in lote:
                a = t.get("assignee") or {}
                tickets.append({"creado": (t.get("createdTime") or "")[:10], "cerrado": (t.get("closedTime") or "")[:10] or None,
                                "estado": t.get("statusType") or t.get("status"), "canal": t.get("channel"), "dep": C.sanear(d.get("name", "").strip()),
                                "prioridad": t.get("priority"), "respuesta_vence": (t.get("responseDueDate") or "")[:16] or None,
                                "vence": (t.get("dueDate") or "")[:16] or None, "vencido": bool(t.get("isOverDue")),
                                "agente": C.sanear(f"{a.get('firstName') or ''} {a.get('lastName') or ''}".strip()) or None})
            n += len(lote)
            if len(lote) < 100 or (lote[-1].get("createdTime") or "9")[:10] < corte:
                break
            frm += 100
    return {"leido": AHORA, "departamentos": len(deps), "legibles": legibles, "tickets": tickets}


def zd_leer():
    import zd
    filas = zd.agrupar(zd.llamadas_pbx(datetime.combine(HOY - timedelta(days=95), datetime.min.time()), datetime.now()))
    out = []
    for f in filas or []:
        out.append({"dia": (f.get("callstart") or "")[:10], "hora": (f.get("callstart") or "")[11:13], "sentido": zd.sentido(f),
                    "estado": f.get("disposition"), "seg": int(num(f.get("seconds"))), "ext": zd.extension(f), "grabada": bool(zd.grabada(f))})
    nombres = {}
    for f in filas or []:
        q = zd.quien(f)
        m = re.match(r"\s*(.+?)\s*\((\d{2,6})\)", q or "")
        if m:
            nombres[m.group(2)] = C.sanear(m.group(1))
    return {"leido": AHORA, "llamadas": out, "extensiones": nombres}


# ====================================================================== lectura en vivo
def en_vivo(cls):
    vivo = [c for c in cls if not SOLO or c["id"] in SOLO]
    if FUENTES & {"ga", "gsc", "idx"}:
        import gg
        tk = gg.acceso()

        def uno_google(c):
            if "ga" in FUENTES and c.get("ga4"):
                lectura_fuente("ga", c["id"], lambda: ga_leer(tk, c)); log(f"  ga {c['id']}")
            if "gsc" in FUENTES and c.get("gsc"):
                lectura_fuente("gsc", c["id"], lambda: gsc_leer(tk, c)); log(f"  gsc {c['id']}")
            if "idx" in FUENTES and c.get("gsc"):
                g = cache_leer("gsc", c["id"]) or {}
                top = [k for k, *_ in ((g.get("periodos") or {}).get("30d") or {}).get("paginas", [])]
                if not top and c.get("web"):
                    top = [c["web"]]
                # la inspección pide la URL completa tal cual: se usa la del sitio (las páginas guardadas ya van sin parámetros)
                lectura_fuente("idx", c["id"], lambda: idx_leer(tk, c, top)); log(f"  idx {c['id']}")
        with ThreadPoolExecutor(8) as ex:
            list(ex.map(uno_google, vivo))
    if "psi" in FUENTES:
        with ThreadPoolExecutor(4) as ex:
            def uno_psi(c):
                if c.get("gsc") or c.get("ga4"):
                    lectura_fuente("psi", c["id"], lambda: psi_leer(c)); log(f"  psi {c['id']}")
            list(ex.map(uno_psi, vivo))
    if "meta" in FUENTES:
        import mt
        mtk = mt.llave("meta_token")
        with ThreadPoolExecutor(4) as ex:
            def uno_meta(c):
                if c.get("meta"):
                    lectura_fuente("meta", c["id"], lambda: meta_leer(mtk, c)); log(f"  meta {c['id']}")
            list(ex.map(uno_meta, vivo))
    if "ghl" in FUENTES:
        g = GHL()
        with ThreadPoolExecutor(6) as ex:
            def uno_ghl(c):
                if c.get("ghl"):
                    try:
                        lectura_fuente("ghl", c["id"], lambda: ghl_leer(g, c)); log(f"  ghl {c['id']}")
                    except SystemExit as e:
                        log(f"  ghl {c['id']}: {e}")
            list(ex.map(uno_ghl, vivo))
    if "mc" in FUENTES:
        with ThreadPoolExecutor(4) as ex:
            def uno_mc(c):
                if c.get("metricool"):
                    lectura_fuente("mc", c["id"], lambda: mc_leer(c)); log(f"  metricool {c['id']}")
            list(ex.map(uno_mc, vivo))
    if "desk" in FUENTES and not SOLO:
        try:
            cache_escribir("empresa", "desk", desk_leer()); log("  desk")
        except Exception as e:  # noqa: BLE001
            log("  desk: no se pudo leer:", str(e)[:160])
    if "zd" in FUENTES and not SOLO:
        try:
            cache_escribir("empresa", "zadarma", zd_leer()); log("  zadarma")
        except Exception as e:  # noqa: BLE001
            log("  zadarma: no se pudo leer:", str(e)[:160])


# ====================================================================== ficheros para la app
ENLACE = {
    "ga4": lambda c: f"https://analytics.google.com/analytics/web/#/p{str(c['ga4']).split('/')[-1]}/reports/intelligenthome",
    "gsc": lambda c: f"https://search.google.com/search-console/performance/search-analytics?resource_id={urllib.parse.quote(c['gsc'], safe='')}",
    "meta": lambda c: f"https://adsmanager.facebook.com/adsmanager/manage/campaigns?act={str(c['meta']).replace('act_', '')}",
    "ghl": lambda c: f"https://app.gohighlevel.com/v2/location/{c['ghl']}/dashboard",
    "mc": lambda c: f"https://app.metricool.com/evolution/web?blogId={c['metricool']}",
}


def nota_error(e):
    e = str(e or "")
    if e.startswith("403"):
        return "La cuenta de Google de la app no tiene permiso en esta propiedad: hay que darle acceso de lector."
    if e.startswith("429"):
        return "La herramienta ha cortado por cupo; se reintenta en la próxima recarga."
    return ("La herramienta respondió con un error: " + e[:80]) if e else None


def estado_de(raw, clave_datos):
    if not raw:
        return "sin_leer"
    if raw.get("_error"):
        return "rota"
    d = raw.get(clave_datos)
    if raw.get("_viejo") and d:       # N-06: la API falló en la última vuelta; son los últimos datos buenos
        return "dato_viejo"
    return "bien" if d else "a_cero"


def periodos_sin_basura(periodos):
    """Barrido v1 (N14): las «consultas» que son filas de una exportación de Google Ads (Octoedro) no se enseñan."""
    if not isinstance(periodos, dict):
        return periodos
    out = {}
    for pid, per in periodos.items():
        if isinstance(per, dict) and isinstance(per.get("consultas"), list):
            per = {**per, "consultas": [f for f in per["consultas"] if not (isinstance(f, (list, tuple)) and f and C.consulta_basura(f[0]))]}
        out[pid] = per
    return out


def escribir_fila(fuente, c, fila):
    fila = {"cliente_id": c["id"], "nombre": c["nombre"], **fila}
    obj = {"formato": 1, "generado": AHORA, "fuente": fuente, "filas": [fila]}
    hall = C.escanear(obj)
    if hall:
        raise SystemExit(f"{fuente}/{c['id']}: datos sensibles: {hall[:3]}")
    C.escribir(SALIDA / fuente / f"{c['id']}.json", obj) if False else _compacto(SALIDA / fuente / f"{c['id']}.json", obj)


def _compacto(ruta, obj):
    import tempfile
    ruta.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=ruta.parent, prefix=".tmp_", suffix=".json")
    with os.fdopen(fd, "w") as f:
        json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))
    os.chmod(tmp, 0o644)
    os.replace(tmp, ruta)


def construir(cls):
    indice = []
    for c in cls:
        cid = c["id"]
        f = {}
        # Analytics
        ga = cache_leer("ga", cid) if c.get("ga4") else None
        f["ga4"] = {"estado": estado_de(ga, "serie") if c.get("ga4") else "sin_conectar", "hora": (ga or {}).get("leido"),
                    "nombre": c.get("ga4_nombre"), "abrir": ENLACE["ga4"](c) if c.get("ga4") else None,
                    "nota": nota_error((ga or {}).get("_error")) or (None if c.get("ga4") else c.get("nota_sin") or "Sin propiedad de Analytics emparejada")}
        if ga and not ga.get("_error"):
            escribir_fila("ga4", c, {k: ga.get(k) for k in ("propiedad", "leido", "serie", "serie_canal", "periodos", "errores")} | {"propiedad_nombre": c.get("ga4_nombre")})
        # Search Console + indexación + experiencia
        gs = cache_leer("gsc", cid) if c.get("gsc") else None
        ix = cache_leer("idx", cid) if c.get("gsc") else None
        ps = cache_leer("psi", cid)
        f["gsc"] = {"estado": estado_de(gs, "serie") if c.get("gsc") else "sin_conectar", "hora": (gs or {}).get("leido"), "nombre": c.get("gsc"),
                    "abrir": ENLACE["gsc"](c) if c.get("gsc") else None, "hasta": (gs or {}).get("hasta"),
                    "nota": nota_error((gs or {}).get("_error")) or (None if c.get("gsc") else c.get("nota_sin") or "Sin sitio de Search Console emparejado")}
        if (gs and not gs.get("_error")) or ps:
            escribir_fila("gsc", c, {"sitio": c.get("gsc"), "leido": (gs or {}).get("leido"), "hasta": (gs or {}).get("hasta"), "desde_dato": (gs or {}).get("desde_dato"),
                                     "serie": (gs or {}).get("serie"), "periodos": periodos_sin_basura((gs or {}).get("periodos")), "errores": (gs or {}).get("errores"),
                                     "indexacion": ix, "experiencia": ps})
        # Meta
        me = cache_leer("meta", cid) if c.get("meta") else None
        me = META220.preparar_cache(me) if me else None
        f["meta"] = {"estado": ("rota" if (me or {}).get("_error") else ("dato_viejo" if me.get("_viejo") else "bien") if me and (me.get("gasto_serie") or me.get("periodos")) else "sin_dato" if me else "sin_leer") if c.get("meta") else "sin_conectar",
                     "hora": (me or {}).get("leido"), "nombre": c.get("meta_nombre"), "abrir": ENLACE["meta"](c) if c.get("meta") else None,
                     "nota": nota_error((me or {}).get("_error")) or (None if c.get("meta") else "Sin cuenta publicitaria de Meta emparejada")}
        if me and not me.get("_error"):
            escribir_fila("meta", c, META220.proyectar_cache(me, cliente_id=c.get('id')))
        # GHL
        gh = cache_leer("ghl", cid) if c.get("ghl") else None
        f["ghl"] = {"estado": ("rota" if (gh or {}).get("_error") else ("dato_viejo" if gh.get("_viejo") else "bien") if gh else "sin_leer") if c.get("ghl") else "sin_conectar",
                    "hora": (gh or {}).get("leido"), "nombre": c.get("ghl_nombre"), "abrir": ENLACE["ghl"](c) if c.get("ghl") else None,
                    "nota": nota_error((gh or {}).get("_error")) or (None if c.get("ghl") else "Sin subcuenta de GoHighLevel emparejada")}
        if gh and not gh.get("_error"):
            # ids largos de GHL → códigos cortos (e1, s1…): menos peso y ningún falso «teléfono» en un id
            cod = {}
            def k_(x, pre):
                if x is None:
                    return None
                if x not in cod:
                    cod[x] = f"{pre}{sum(1 for v in cod.values() if v.startswith(pre)) + 1}"
                return cod[x]
            emb = [{"id": k_(e["id"], "e"), "nombre": e["nombre"], "etapas": [{"id": k_(st["id"], "s"), "nombre": st["nombre"]} for st in e["etapas"]]} for e in gh.get("embudos") or []]
            opps = [[o[0], k_(o[1], "e"), k_(o[2], "s"), *o[3:7]] for o in gh.get("oportunidades") or []]
            escribir_fila("ghl", c, {**{k: gh.get(k) for k in ("leido", "citas", "calendarios", "contactos_nuevos", "contactos_total", "conversaciones", "errores")},
                                     "embudos": emb, "oportunidades": opps})
        # Metricool
        mm = cache_leer("mc", cid) if c.get("metricool") else None
        f["mc"] = {"estado": (("dato_viejo" if mm.get("_viejo") else "bien") if (mm or {}).get("redes") else "a_cero" if mm else "sin_leer") if c.get("metricool") else "sin_conectar",
                   "hora": (mm or {}).get("leido"), "nombre": c.get("metricool_nombre"), "abrir": ENLACE["mc"](c) if c.get("metricool") else None,
                   "nota": None if c.get("metricool") else "Sin marca de Metricool emparejada"}
        if mm and mm.get("redes"):
            escribir_fila("mc", c, {k: mm.get(k) for k in ("marca", "leido", "redes", "errores")})
        for clave_f, raw_f in (("ga4", ga), ("gsc", gs), ("meta", me), ("ghl", gh), ("mc", mm)):   # N-06: desde cuándo es el dato viejo
            if f[clave_f]["estado"] == "dato_viejo":
                f[clave_f]["desde"] = (raw_f or {}).get("_desde")
        indice.append({"cliente_id": cid, "nombre": c["nombre"], "web": c.get("web"), "fuentes": f})
    _compacto(SALIDA / "indice.json", {"formato": 1, "generado": AHORA, "periodos": PERIODOS, "filas": indice})
    # Empresa: Desk y Zadarma
    dk = cache_leer("empresa", "desk")
    if dk:
        _compacto(SALIDA / "empresa" / "desk.json", {"formato": 1, "generado": AHORA, **dk})
    zz = cache_leer("empresa", "zadarma")
    if zz:
        _compacto(SALIDA / "empresa" / "zadarma.json", {"formato": 1, "generado": AHORA, **zz})
    log(f"data/paneles/ escrito: {len(indice)} clientes")


def main():
    cls = clientes()
    log(f"Clientes: {len(cls)} · GA4 {sum(1 for c in cls if c.get('ga4'))} · GSC {sum(1 for c in cls if c.get('gsc'))} · Meta {sum(1 for c in cls if c.get('meta'))} · "
        f"GHL {sum(1 for c in cls if c.get('ghl'))} · Metricool {sum(1 for c in cls if c.get('metricool'))}")
    if not SOLO_CACHE:
        en_vivo(cls)
    construir(cls)


if __name__ == "__main__":
    main()

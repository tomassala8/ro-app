#!/usr/bin/env python3
"""M5 · Informe del cliente (sustituto de Looker) · capa de datos propia del módulo. SOLO LECTURA.

Qué hace (2-oct-2026):
  · Lee los emparejamientos ya hechos (E1 data/clientes/<id>.json + HERRAMIENTA_RO/emparejamientos.json, con
    las correcciones a mano: FusterGüell → properties/480200463, AyG → sc-domain:aygasesores.com).
  · Pide a Google Analytics 4 y Search Console (gg.py, llave del llavero) las cifras de 6 periodos cerrados
    (sep, ago, jul, jun, últimos 30 días y 3.er trimestre), cada uno con su periodo anterior y el mismo del año
    anterior. Así el selector de fechas del informe es instantáneo y la comparación es exacta.
  · Meta Ads por la API de Graph (mt.py, llave meta_token): gasto, impresiones, alcance, frecuencia y leads por
    periodo, por campaña y por día.
  · Snov.io (sv.py): correo en frío por campaña emparejada al cliente, por mes y todo el histórico.
  · Google Ads: la muestra sellada de septiembre de 14_GOOGLE_ADS_VIA_WINDSOR.md (Windsor sin clave guardada).
  · SE Ranking: fuentes_informe/_cache/seranking/<id>.json (leído con el conector de SE Ranking, porque la
    clave de proyectos da 403).
  · GHL: el embudo de captacion.json (vía E1).
Escribe data/informe/p_<periodo>.json (una fila por cliente con cliente_id: servir.py recorta por cartera y quita
gasto/coste/cpl a quien no ve inversión), data/informe/paridad.json y data/informe/comun.json.

Uso:  python3 generar_informe.py            # todo en vivo (≈5 min)
      python3 generar_informe.py --cache    # rehace los ficheros con lo último guardado en _cache/ (0 llamadas)
      python3 generar_informe.py --solo fusterguell,ahedo
"""
import json, os, sys, time, re, threading, urllib.parse, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta
from pathlib import Path

AQUI = Path(__file__).resolve().parent
APP = AQUI.parent
sys.path.insert(0, str(APP / "fuentes"))
import comun as C  # noqa: E402
sys.path.insert(0, str(APP))
from fuentes_informe import meta_productor_298 as META298  # noqa: E402

sys.path[:0] = [os.path.expanduser(p) for p in ("~/RO_HERRAMIENTAS/google", "~/RO_HERRAMIENTAS/snov", "~/RO_HERRAMIENTAS/meta")]

CACHE = AQUI / "_cache"
SALIDA = APP / "data" / "informe"
HERR = Path.home() / "Downloads/HERRAMIENTA_RO_2026-10-02"
AHORA = datetime.now().strftime("%Y-%m-%d %H:%M")
ARGS = sys.argv[1:]
SOLO_CACHE = "--cache" in ARGS
SOLO = next((a.split(",") for i, a in enumerate(ARGS) if i and ARGS[i - 1] == "--solo"), None)
# --fuentes ga,gsc,meta,snov : qué se pide en vivo (por defecto todo). --solo solo limita a quién se pide en vivo;
# los ficheros de data/informe/ se rehacen siempre con los 68 clientes.
FUENTES = set(next((a.split(",") for i, a in enumerate(ARGS) if i and ARGS[i - 1] == "--fuentes"), ["ga", "gsc", "meta", "snov"]))

# Correcciones de emparejamiento de la auditoría de cifras (28 · E-01 y tabla de emparejamientos), 2-oct.
# Mandan sobre E1 y sobre HERRAMIENTA_RO/emparejamientos.json hasta que E1 las recoja. «-» = no emparejar.
CORRECCIONES = {
    "kiosko-box": {"meta": ("act_292218051469540", "Josep SG"),
                   "_nota_meta": "cuenta real de Kiosko (Instagrafic): «Kiosko II» no ha gastado nunca"},
    "fusterguell": {"ga": ("properties/480200463", "FusterGA4 New")},
    "consulting-f": {"ga": "-", "gsc": "-",
                     "_nota_ga": "la propiedad emparejada era la landing info.consultingf.com; la web consultingf.com no está compartida con la cuenta de la app (pedir acceso de lector)",
                     "_nota_gsc": "el sitio emparejado era la landing info.consultingf.com (0 clics); falta acceso a consultingf.com (dominio)"},
}

D = date.fromisoformat


def mes(a, m):
    ini = date(a, m, 1)
    fin = date(a + (m // 12), m % 12 + 1, 1) - timedelta(days=1)
    return ini, fin


def periodo(pid, texto, ini, fin, prev, yoy, corto):
    return {"id": pid, "texto": texto, "corto": corto, "desde": str(ini), "hasta": str(fin),
            "anterior": [str(prev[0]), str(prev[1])], "anio_anterior": [str(yoy[0]), str(yoy[1])]}


PERIODOS = [
    periodo("2026-09", "Septiembre 2026", *mes(2026, 9), mes(2026, 8), mes(2025, 9), "sep"),
    periodo("2026-08", "Agosto 2026", *mes(2026, 8), mes(2026, 7), mes(2025, 8), "ago"),
    periodo("2026-07", "Julio 2026", *mes(2026, 7), mes(2026, 6), mes(2025, 7), "jul"),
    periodo("2026-06", "Junio 2026", *mes(2026, 6), mes(2026, 5), mes(2025, 6), "jun"),
    periodo("u30", "Últimos 30 días", D("2026-09-02"), D("2026-10-01"), (D("2026-08-03"), D("2026-09-01")),
            (D("2025-09-02"), D("2025-10-01")), "30 días"),
    periodo("trim", "3.er trimestre 2026", D("2026-07-01"), D("2026-09-30"), (D("2026-04-01"), D("2026-06-30")),
            (D("2025-07-01"), D("2025-09-30")), "jul-sep"),
]

# ------------------------------------------------------------------ Looker: los 22 (G4 §8) + cifras vistas el 2-oct (05 §3)
LOOKER = [
    # app_id, nombre, enlace, bloques que tiene que tener, tanda, plantillas, estado en Looker, cifras de septiembre vistas en Looker
    ("adade-zaragoza", "Adade Zaragoza", "https://lookerstudio.google.com/reporting/1ff88f12-1767-4d9f-95c5-fc342ec76355",
     ["ga4", "gsc_web", "seranking", "linkedin"], 3, "P1 · P2-sitio · P3 · P7 · P6 hoja",
     {"linkedin": "roto"}, {"ga4.usuarios": 790, "gsc_web.impresiones": 71000, "seranking.palabras": 49}),
    ("ahedo", "Ahedo", "https://lookerstudio.google.com/reporting/e8dfadd4-4620-42c4-acb5-a0a4683966c4",
     ["ga4", "gsc_url", "seranking"], 1, "P1 · P2-URL · P3", {},
     {"ga4.usuarios": 1400, "gsc_url.impresiones": 165000, "seranking.palabras": 110}),
    ("aselegal", "AseLegal", "https://lookerstudio.google.com/u/0/reporting/1bd06aa8-503b-4566-af02-67a76e99aafb/page/p_9hl0per2fd",
     ["google_ads", "ga4", "seranking", "gsc_url", "correo", "linkedin", "analisis", "glosario"], 4,
     "P4b · P1 · P3 %Δ · P2-URL · P5 · P6 · P11", {"google_ads": "a_cero", "correo": "roto", "analisis": "otro_mes"}, {}),
    ("aster-asesoria", "Asesoría Aster", "https://lookerstudio.google.com/reporting/fde49aed-ba0a-4a04-9337-d93eda733c51",
     ["ga4", "gsc_web", "seranking", "linkedin", "correo", "glosario"], 3, "P1 %Δ · P2-sitio · P3 %Δ · P7 · P6 hoja · P5 imágenes · P11",
     {"linkedin": "roto", "correo": "imagenes"}, {"ga4.usuarios": 2300, "gsc_web.impresiones": 172900}),
    ("fitec-asesores", "Asesoría FITECC", "https://lookerstudio.google.com/reporting/9b93df24-a42b-45c2-99dd-2b3a13338816/page/p_sm4su3z9xd",
     ["google_ads", "ga4", "seranking", "gsc_url", "correo", "linkedin", "glosario"], 4, "P4b · P1 · P3 %Δ · P2-URL · P5 · P6 · P11",
     {"google_ads": "a_cero", "correo": "roto", "linkedin": "viejo"}, {}),
    ("asetra", "Asetra", "https://lookerstudio.google.com/reporting/f4f2f544-d21d-4e0c-8761-debfaba2a52a/page/VgD5",
     ["google_ads", "ga4", "gsc_url", "seranking"], 2, "P4 · P1 · P2-URL · P3", {"google_ads": "a_cero"}, {}),
    ("avantik", "Avantik", "https://lookerstudio.google.com/reporting/9ecc6bc7-faa2-4639-930c-68ae1b03ea75",
     [], 5, "— (sin acceso)", {"todo": "sin_acceso"}, {}),
    ("ayg-asesores", "AyG Asesores", "https://lookerstudio.google.com/reporting/35a23f4e-dd1c-45eb-9076-9392466d94b9",
     ["google_ads", "ga4", "gsc_web", "seranking", "linkedin", "correo", "analisis"], 4, "P4 · P1 · P2-sitio · P3 · P6 · P5",
     {"linkedin": "viejo", "correo": "datos_leads"}, {"google_ads.conversiones": 92, "google_ads.coste": 1250}),
    ("bit-24", "Bit24", "https://lookerstudio.google.com/u/0/reporting/bc88baae-7c58-40ff-8218-9c9272accd49/page/VgD",
     ["google_ads", "ga4", "gsc_url", "seranking"], 2, "P4 · P1 · P2-URL · P3",
     {"google_ads": "a_cero", "gsc_url": "raro", "seranking": "roto"}, {"gsc_url.clics": 1, "gsc_url.impresiones": 43}),
    ("bonet-asesores", "Bonet Asesores", "https://lookerstudio.google.com/u/0/reporting/98612f11-e095-4f5f-85bb-8c417dd5a36d/page/VgD",
     ["ga4", "gsc_url", "seranking", "correo"], 3, "P1 · P2-URL · P3 · P5", {"correo": "roto"}, {}),
    ("centro-consulting", "Centro Consulting", "https://lookerstudio.google.com/reporting/3dbdba04-1bb3-4b1e-9a34-79954dae1053/page/p_i0vlnykhkd",
     ["gsc_url", "seranking", "google_ads", "correo", "linkedin"], 4, "P2-URL · P3 %Δ · P4 · P5 · P6",
     {"google_ads": "a_cero", "correo": "roto", "linkedin": "viejo"}, {}),
    ("consulting-f", "Consulting F", "https://lookerstudio.google.com/reporting/21e89108-9963-482b-a81d-62a688f2e31e",
     ["google_ads", "meta", "ga4", "glosario", "correo"], 4, "P4b · P8 · P1 · P11 · P5", {"meta": "roto"},
     {"google_ads.clics": 170, "google_ads.conversiones": 4, "google_ads.coste": 263}),
    ("fusterguell", "FusterGüell", "https://lookerstudio.google.com/reporting/a8826949-2767-4a03-81e3-405e4be86aff",
     ["ga4", "gsc_web", "seranking"], 1, "P1 (variante) · P2-sitio · P3", {}, {"ga4.usuarios": 2100, "seranking.palabras": 145}),
    ("greconsult", "Greconsult", "https://lookerstudio.google.com/reporting/46ecce04-8dd1-4e63-b3b9-9137d4848c33/page/VgD",
     ["google_ads"], 2, "P10", {"google_ads": "a_cero"}, {}),
    ("innova-scala", "Innova Scala", "https://lookerstudio.google.com/u/0/reporting/f691b192-d6e5-473b-83f2-a0835b7ede67/page/p_516rqgdr0d",
     ["meta", "google_ads", "analisis"], 5, "P9", {"meta": "roto", "google_ads": "otro_cliente"}, {}),
    ("mg-economistes", "MG Economistes", "https://lookerstudio.google.com/reporting/c48d3753-7793-4c85-8073-b19e74f4dde3",
     ["google_ads", "ga4", "gsc_web", "seranking"], 2, "P4 · P1 · P2-sitio · P3", {"google_ads": "roto"}, {}),
    ("octoedro", "Octoedro", "https://lookerstudio.google.com/reporting/932273b1-4a44-48de-80eb-c7e60600ed40",
     ["ga4", "gsc_web", "seranking", "correo", "linkedin"], 3, "P1 · P2-sitio · P3 · P5 · P6", {"correo": "roto"}, {}),
    ("oteca", "Oteca Asesores", "https://lookerstudio.google.com/reporting/1a5a6aaf-199f-4dba-9905-01eb2c97e5ba",
     ["google_ads", "ga4", "gsc_url", "seranking", "correo", "linkedin"], 4, "P4 · P1 · P2-URL · P3 %Δ · P5 · P6",
     {"google_ads": "no_cuadra", "correo": "roto", "linkedin": "viejo"}, {"google_ads.coste": 348.54}),
    ("prodegest", "Prodegest", "https://lookerstudio.google.com/reporting/d379c226-ea0a-4140-b7ad-690d869353fc",
     ["ga4", "seranking", "gsc_url", "correo", "glosario"], 3, "P1 · P3 %Δ · P2-URL · P5 · P11", {"correo": "roto"}, {}),
    ("segu-assessors", "Segú Assessors", "https://lookerstudio.google.com/reporting/2e2fd6d4-39f5-4deb-bfbd-652317753fa4",
     ["ga4", "gsc_url", "seranking", "linkedin", "correo"], 3, "P1 · P2-URL · P3 · P6 hoja · P5", {"correo": "roto"}, {}),
    ("torrevieja-consult", "Torrevieja Consult", "https://lookerstudio.google.com/u/0/reporting/ea7d702e-c485-4ede-a4dc-32a9797f638d/page/p_9hl0per2fd",
     ["ga4", "gsc_url", "seranking", "linkedin", "correo"], 3, "P1 · P2-URL · P3 %Δ · P6 · P5 imágenes",
     {"linkedin": "viejo", "correo": "imagenes"}, {}),
    ("xterna", "Xterna", "https://lookerstudio.google.com/reporting/09e9e719-c160-4bca-9865-baf9c2e87192",
     ["ga4", "gsc_url", "seranking"], 1, "P1 · P2-URL · P3", {"seranking": "tarjetas"}, {}),
]

# Google Ads: muestra sellada de septiembre (14_GOOGLE_ADS_VIA_WINDSOR.md, consulta en el navegador el 2-oct)
GADS_SEP = {
    "ayg-asesores": {"cuenta": "677-096-7821", "coste": 1357.62, "clics": 768, "impresiones": 10985, "conversiones": 32, "ultimo_gasto": "2026-10-01"},
    "kiosko-box": {"cuenta": "976-000-2384", "coste": 608.30, "clics": 1128, "impresiones": 12582, "conversiones": 321.1, "ultimo_gasto": "2026-10-01"},
    "consulting-f": {"cuenta": "596-013-5207", "coste": 263.58, "clics": 170, "impresiones": 2960, "conversiones": 4, "ultimo_gasto": "2026-09-18"},
    "gac": {"cuenta": "366-635-6076", "coste": 222.55, "clics": 517, "impresiones": 24084, "conversiones": 2, "ultimo_gasto": "2026-09-15"},
    "busbac": {"cuenta": "250-013-1330", "coste": 151.92, "clics": 483, "impresiones": 9661, "conversiones": 0, "ultimo_gasto": "2026-10-01"},
}
GADS_PARADAS = {"aselegal": "2026-07-30", "fitec-asesores": "2026-06-03", "greconsult": "2026-05-25",
                "centro-consulting": "2026-05-18", "bit-24": "2026-03-19"}
GADS_FUERA_WINDSOR = {"asetra", "oteca", "mg-economistes"}

# Arreglos detectados (G4 §7) que el informe enseña como aviso
ARREGLOS = {
    "innova-scala": [("rojo", "otro_cliente", "Su Looker enseña campañas de Google Ads de AyG («Asesoría Empresarial AYG»). En la app cada cuenta va por su identificador: hasta confirmar si Innova tiene cuenta propia, el bloque de Google Ads no se pinta.", "Agus y el account")],
    "bit-24": [("ambar", "caida", "Search Console de Looker da 1 clic y 43 impresiones en septiembre (−85 %): casi seguro es la propiedad equivocada. La cuenta de Google de la app no ve ninguna propiedad de Bit24, así que todavía no se puede comparar cuál es la buena: hay que darle acceso de lector a las dos (dominio y prefijo).", "SEO del cliente · Agus")],
    "ayg-asesores": [("rojo", "datos_leads", "Su Looker lleva un texto con nombres y correos de leads en la página de correo. En la app los leads no van nunca en un texto del informe: están en GHL, con permisos.", "Account")],
    "avantik": [("rojo", "sin_acceso", "Su Looker no abre con ninguna de las dos cuentas de RO (o se ha borrado). No se puede comprobar la paridad hasta que lo compartan con la cuenta de Google de RO para Looker o se confirme que ya no existe .", "Quien lo creó · Agus")],
    "aselegal": [("ambar", "otro_mes", "El texto de análisis de Google Ads de su Looker es de junio-2026.", "Account")],
    "fitec-asesores": [("ambar", "rango", "En su Looker la tabla de campañas y el coste están fijados al primer semestre (1.550 €) y las tarjetas siguen el mes. En la app un solo selector manda en todo el bloque.", "Trafficker")],
    "oteca": [("ambar", "no_cuadra", "En su Looker las campañas de Google Ads salen a 0 y la tarjeta de coste dice 348,54 €. No cuadra.", "Trafficker")],
    "consulting-f": [("ambar", "sin_seo", "Su Looker no tiene Search Console ni SE Ranking. Comprobar si es a propósito.", "SEO")],
    "centro-consulting": [("ambar", "sin_ga4", "Su Looker no tiene página de Analytics (y en la app tampoco hay propiedad emparejada, a propósito).", "SEO")],
    "mg-economistes": [("ambar", "fuera_windsor", "Google Ads: su Looker dice «Falta la fuente de datos» y la cuenta no aparece en Windsor. Se verá con la conexión directa de Google Ads.", "Agus")],
    "xterna": [("ambar", "tarjetas", "En su Looker las tarjetas de SE Ranking no se pintan.", "SEO")],
}


# ------------------------------------------------------------------ utilidades HTTP
def post_json(tk, url, body, intentos=4):
    for i in range(intentos):
        req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                     headers={"Authorization": "Bearer " + tk, "Content-Type": "application/json"})
        try:
            return json.load(urllib.request.urlopen(req, timeout=90))
        except urllib.error.HTTPError as e:
            msg = e.read().decode()[:300]
            if e.code in (429, 500, 503) and i < intentos - 1:
                time.sleep(2 + 3 * i)
                continue
            return {"_error": e.code, "_msg": msg}
        except Exception as e:  # noqa: BLE001
            if i < intentos - 1:
                time.sleep(2)
                continue
            return {"_error": 0, "_msg": str(e)[:200]}


def escribir_compacto(ruta, obj):
    import tempfile
    ruta = Path(ruta); ruta.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=ruta.parent, prefix=".tmp_", suffix=".json")
    with os.fdopen(fd, "w") as f:
        json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))
    os.chmod(tmp, 0o644); os.replace(tmp, ruta)


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


# ------------------------------------------------------------------ Google Analytics 4
GA_TOT = ["activeUsers", "newUsers", "sessions", "engagementRate", "screenPageViewsPerUser", "userEngagementDuration",
          "keyEvents", "eventCount", "bounceRate", "screenPageViews"]
GA_NOM = ["usuarios", "nuevos", "sesiones", "interaccion", "vistas_usuario", "tiempo_total", "conversiones", "eventos", "rebote", "vistas"]


def ga_batch(tk, prop, reqs):
    r = post_json(tk, f"https://analyticsdata.googleapis.com/v1beta/{prop}:batchRunReports", {"requests": reqs})
    if "_error" in r:
        return None, f"{r['_error']} {r['_msg'][:120]}"
    return r.get("reports", []), None


def filas(rep):
    out = []
    dims = [d["name"] for d in rep.get("dimensionHeaders", [])]
    for row in rep.get("rows", []) or []:
        dv = {d: x["value"] for d, x in zip(dims, row.get("dimensionValues", []))}
        out.append((dv, [num(m["value"]) for m in row.get("metricValues", [])]))
    return out


def rng(a, b, nombre):
    return {"startDate": a, "endDate": b, "name": nombre}


def ga_periodo(tk, prop, p):
    cur, prev, yoy = (p["desde"], p["hasta"]), tuple(p["anterior"]), tuple(p["anio_anterior"])
    R3 = [rng(*cur, "a"), rng(*prev, "b"), rng(*yoy, "c")]
    R2 = R3[:2]
    lote1 = [
        {"dateRanges": R3, "metrics": [{"name": m} for m in GA_TOT]},
        {"dateRanges": R3, "dimensions": [{"name": "date"}], "metrics": [{"name": "activeUsers"}, {"name": "sessions"}, {"name": "keyEvents"}], "limit": 2000},
        {"dateRanges": R2, "dimensions": [{"name": "landingPagePlusQueryString"}], "metrics": [{"name": "sessions"}, {"name": "eventCount"}, {"name": "bounceRate"}, {"name": "keyEvents"}],
         "orderBys": [{"metric": {"metricName": "sessions"}, "desc": True}], "limit": 120},
        {"dateRanges": R2, "dimensions": [{"name": "eventName"}], "metrics": [{"name": "eventCount"}], "orderBys": [{"metric": {"metricName": "eventCount"}, "desc": True}], "limit": 80},
        {"dateRanges": R2, "dimensions": [{"name": "sessionDefaultChannelGroup"}], "metrics": [{"name": "sessions"}, {"name": "eventCount"}, {"name": "activeUsers"}, {"name": "keyEvents"}], "limit": 30},
    ]
    lote2 = [
        {"dateRanges": [R3[0]], "dimensions": [{"name": "sessionDefaultChannelGroup"}, {"name": "eventName"}], "metrics": [{"name": "eventCount"}], "limit": 400,
         "orderBys": [{"metric": {"metricName": "eventCount"}, "desc": True}]},
        {"dateRanges": [R3[0]], "dimensions": [{"name": "date"}, {"name": "eventName"}], "metrics": [{"name": "eventCount"}], "limit": 5000},
        {"dateRanges": [R3[0]], "dimensions": [{"name": "date"}, {"name": "sessionDefaultChannelGroup"}], "metrics": [{"name": "eventCount"}], "limit": 3000},
    ]
    r1, e1 = ga_batch(tk, prop, lote1)
    if e1:
        return {"_error": e1}
    r2, e2 = ga_batch(tk, prop, lote2)
    r2 = r2 or [{}, {}, {}]

    def por_rango(rep):
        d = {}
        for dv, m in filas(rep):
            d[dv.get("dateRange", "a")] = dict(zip(GA_NOM, m))
        return d
    t = por_rango(r1[0])
    for k in t.values():
        k["duracion"] = round(k["tiempo_total"] / k["usuarios"], 1) if k.get("usuarios") else 0
        k["pct_nuevos"] = round(100 * k["nuevos"] / k["usuarios"], 1) if k.get("usuarios") else 0
        k.pop("tiempo_total", None)
    serie = {"a": [], "b": [], "c": []}
    for dv, m in filas(r1[1]):
        serie.setdefault(dv.get("dateRange", "a"), []).append([C.iso(datetime.strptime(dv["date"], "%Y%m%d"))[:10], m[0], m[1], m[2]])
    for v in serie.values():
        v.sort()
    pag = {}
    for dv, m in filas(r1[2]):
        k = C.sanear(dv["landingPagePlusQueryString"])[:160]
        x = pag.setdefault(k, {"pagina": k, "sesiones": 0, "eventos": 0, "rebote": None, "conversiones": 0, "sesiones_ant": 0})
        if dv.get("dateRange", "a") == "a":
            x.update(sesiones=m[0], eventos=m[1], rebote=round(m[2], 4), conversiones=m[3])
        else:
            x["sesiones_ant"] = m[0]
    paginas = sorted([x for x in pag.values() if x["sesiones"] or x["sesiones_ant"]], key=lambda x: -x["sesiones"])[:60]
    ev = {}
    for dv, m in filas(r1[3]):
        x = ev.setdefault(dv["eventName"], {"evento": dv["eventName"], "n": 0, "n_ant": 0})
        x["n" if dv.get("dateRange", "a") == "a" else "n_ant"] = m[0]
    eventos = sorted(ev.values(), key=lambda x: -x["n"])[:30]
    can = {}
    for dv, m in filas(r1[4]):
        x = can.setdefault(dv["sessionDefaultChannelGroup"], {"canal": dv["sessionDefaultChannelGroup"]})
        suf = "" if dv.get("dateRange", "a") == "a" else "_ant"
        x.update({"sesiones" + suf: m[0], "eventos" + suf: m[1], "usuarios" + suf: m[2], "conversiones" + suf: m[3]})
    canales = sorted(can.values(), key=lambda x: -x.get("sesiones", 0))
    canal_evento = [[dv["sessionDefaultChannelGroup"], dv["eventName"], m[0]] for dv, m in filas(r2[0])][:200]
    top_ev = [e["evento"] for e in eventos[:8]]
    ev_dia = {}
    for dv, m in filas(r2[1]):
        if dv["eventName"] in top_ev:
            ev_dia.setdefault(dv["eventName"], {})[dv["date"]] = m[0]
    can_dia = {}
    for dv, m in filas(r2[2]):
        can_dia.setdefault(dv["sessionDefaultChannelGroup"], {})[dv["date"]] = m[0]
    dias = [x[0].replace("-", "") for x in serie.get("a", [])]

    def matriz(d):
        return {k: [v.get(dd, 0) for dd in dias] for k, v in d.items()}
    return {"actual": t.get("a"), "anterior": t.get("b"), "anio_anterior": t.get("c"),
            "serie": serie.get("a"), "serie_ant": serie.get("b"), "serie_anio": serie.get("c"),
            "paginas": paginas, "eventos": eventos, "canales": canales, "canal_evento": canal_evento,
            "dias": [x[0] for x in serie.get("a", [])], "eventos_dia": matriz(ev_dia), "canales_dia": matriz(can_dia)}


# ------------------------------------------------------------------ Search Console
def gsc_q(tk, site, body):
    u = f"https://www.googleapis.com/webmasters/v3/sites/{urllib.parse.quote(site, safe='')}/searchAnalytics/query"
    return post_json(tk, u, body)


def gsc_tot(tk, site, a, b, agg="byProperty"):
    r = gsc_q(tk, site, {"startDate": a, "endDate": b, "aggregationType": agg, "dataState": "final"})
    if "_error" in r:
        return None
    x = (r.get("rows") or [{}])[0]
    return {"clics": x.get("clicks", 0), "impresiones": x.get("impressions", 0), "ctr": x.get("ctr", 0), "posicion": x.get("position")}


ULTIMO_GSC = {}


def ultimo_dato_gsc(tk, site):
    """Search Console va 2-3 días por detrás: último día con datos de este sitio (auditoría de cifras E-10)."""
    if site not in ULTIMO_GSC:
        r = gsc_q(tk, site, {"startDate": "2026-09-15", "endDate": "2026-10-01", "dimensions": ["date"], "rowLimit": 50})
        dias = sorted(x["keys"][0] for x in r.get("rows", []) if x.get("impressions"))
        ULTIMO_GSC[site] = dias[-1] if dias else None
    return ULTIMO_GSC[site]


def mas(f, n):
    return str(D(f) + timedelta(days=n))


def gsc_periodo(tk, site, p):
    cur, prev, yoy = (p["desde"], p["hasta"]), tuple(p["anterior"]), tuple(p["anio_anterior"])
    out = {"sitio": site}
    ult = ultimo_dato_gsc(tk, site)
    if ult and ult < cur[1] and ult >= cur[0]:
        n = (D(ult) - D(cur[0])).days
        cur, prev, yoy = (cur[0], ult), (prev[0], mas(prev[0], n)), (yoy[0], mas(yoy[0], n))
        out["recortado"] = True
    out["hasta_dato"] = ult
    out["ventanas"] = {"actual": list(cur), "anterior": list(prev), "anio_anterior": list(yoy)}
    out["web"] = {"actual": gsc_tot(tk, site, *cur), "anterior": gsc_tot(tk, site, *prev), "anio_anterior": gsc_tot(tk, site, *yoy)}
    if out["web"]["actual"] is None:
        r = gsc_q(tk, site, {"startDate": cur[0], "endDate": cur[1]})
        return {"_error": f"{r.get('_error')} {str(r.get('_msg'))[:120]}"}
    out["url"] = {"actual": gsc_tot(tk, site, *cur, agg="byPage"), "anterior": gsc_tot(tk, site, *prev, agg="byPage"),
                  "anio_anterior": gsc_tot(tk, site, *yoy, agg="byPage")}

    def serie(a, b, agg):
        r = gsc_q(tk, site, {"startDate": a, "endDate": b, "dimensions": ["date"], "aggregationType": agg, "rowLimit": 400})
        return [[x["keys"][0], x["clicks"], x["impressions"], round(x["ctr"], 5), round(x["position"], 2)] for x in r.get("rows", [])]
    out["serie"] = serie(prev[0], cur[1], "byProperty")
    out["serie_url"] = serie(prev[0], cur[1], "byPage")
    out["serie_anio"] = serie(*yoy, "byProperty")

    def dim(d, a, b, n, agg="auto"):
        r = gsc_q(tk, site, {"startDate": a, "endDate": b, "dimensions": [d], "rowLimit": n, "aggregationType": agg})
        return {C.sanear(x["keys"][0])[:200]: [x["clicks"], x["impressions"], round(x["ctr"], 5), round(x["position"], 2)] for x in r.get("rows", [])}
    dv, dva = dim("device", *cur, 10), dim("device", *prev, 10)
    out["dispositivos"] = [[k, *v, *(dva.get(k) or [0, 0, 0, None])[:2]] for k, v in dv.items()]
    q, qa = dim("query", *cur, 150), dim("query", *prev, 1000)
    # N14: fuera las filas de una exportación de Google Ads pegadas como «consulta» (Octoedro, Bonet)
    out["consultas"] = C.limpiar_consultas([[k, *v, (qa.get(k) or [None])[0]] for k, v in q.items()])
    pg, pga = dim("page", *cur, 300), dim("page", *prev, 1000)
    out["paginas"] = [[k, *v, (pga.get(k) or [None])[0]] for k, v in pg.items()]
    return out


# ------------------------------------------------------------------ Meta Ads
def meta_get(tk, path, **q):
    q["access_token"] = tk
    url = f"https://graph.facebook.com/v26.0{path}?" + urllib.parse.urlencode(q)
    for i in range(3):
        try:
            return json.load(urllib.request.urlopen(url, timeout=90))
        except urllib.error.HTTPError as e:
            msg = e.read().decode()[:300]
            if e.code in (429, 500, 503) and i < 2:
                time.sleep(4)
                continue
            return {"_error": e.code, "_msg": re.sub(r"access_token=[^&\s]+", "access_token=…", msg)}
        except Exception as e:  # noqa: BLE001
            if i < 2:
                time.sleep(3)
                continue
            return {"_error": 0, "_msg": str(e)[:200]}


LEAD_TIPOS = ("lead", "onsite_conversion.lead_grouped", "offsite_conversion.fb_pixel_lead", "onsite_web_lead")


def leads_de(actions):
    return META298.M.leads(actions)[0]


def meta_cliente(tk, cuenta):
    return META298.leer(lambda path, **q: meta_get(tk, path, **q), cuenta, PERIODOS, AHORA, C.sanear)


# ------------------------------------------------------------------ Snov.io
SNOV_KEYS = ("emails_sent", "delivered", "email_opens", "link_clicks", "email_replies", "bounced", "total_contacted", "unsubscribed")


def snov_todo(nombres_por_cliente):
    import sv
    tk = sv.token()
    c = sv.get(tk, "/v1/get-user-campaigns")
    cs = c if isinstance(c, list) else c.get("data", [])
    rangos = {p["id"]: (p["desde"], p["hasta"]) for p in PERIODOS}
    rangos.update({p["id"] + "_ant": tuple(p["anterior"]) for p in PERIODOS})
    rangos["historico"] = ("2023-01-01", "2026-10-01")
    out = {}
    for cid, nombres in nombres_por_cliente.items():
        mios = [x for x in cs if (x.get("campaign") or x.get("name")) in nombres]
        filas_c = []
        for x in mios:
            st = {}
            for rid, (a, b) in rangos.items():
                for _ in range(4):
                    r = sv.get(tk, "/v2/statistics/campaign-analytics", campaign_id=x["id"], date_from=a, date_to=b)
                    if r.get("_error") == 429:
                        time.sleep(3)
                        continue
                    break
                st[rid] = None if "_error" in r else {k: r.get(k, 0) or 0 for k in SNOV_KEYS}
                time.sleep(0.25)
            filas_c.append({"nombre": C.sanear(x.get("campaign") or x.get("name")), "estado": x.get("status"), "stats": st})
        out[cid] = filas_c
        print(f"  snov {cid}: {len(filas_c)} campañas", flush=True)
    return out


# ------------------------------------------------------------------ principal
def main():
    CACHE.mkdir(exist_ok=True)
    emp = C.leer(HERR / "emparejamientos.json", {})
    clientes = []
    for f in sorted((APP / "data" / "clientes").glob("*.json")):
        d = C.leer(f)
        if not d:
            continue
        e = dict(emp.get((d.get("ids") or {}).get("panel") or d["nombre"], {}))
        cor = CORRECCIONES.get(d["id"], {})
        for k in ("ga", "gsc"):
            if cor.get(k) == "-":
                e[k] = None; e[k + "_nota"] = cor.get(f"_nota_{k}")
            elif cor.get(k):
                e[k] = cor[k][0]; e[k + "_nombre"] = cor[k][1]
        m = (d.get("fuentes") or {}).get("meta") or {}
        e["meta"] = cor["meta"][0] if cor.get("meta") else (m.get("emparejado") or {}).get("id")
        e["meta_nombre"] = cor["meta"][1] if cor.get("meta") else (m.get("emparejado") or {}).get("nombre")
        e["vivo"] = not SOLO or d["id"] in SOLO
        clientes.append((d, e))
    print(f"Clientes: {len(clientes)}", flush=True)

    vivo_path = CACHE / "vivo.json"
    vivo = C.leer(vivo_path, {}) or {}
    if not SOLO_CACHE:
        import gg
        tk = gg.acceso()
        lock = threading.Lock()

        def uno(par):
            d, e = par
            cid = d["id"]
            res = {"ga": {}, "gsc": {}}
            res = {}
            if "ga" in FUENTES:
                res["ga"] = {p["id"]: ga_periodo(tk, e["ga"], p) for p in PERIODOS} if e.get("ga") else {}
                res["ga_prop"], res["ga_nombre"] = e.get("ga"), e.get("ga_nombre")
            if "gsc" in FUENTES:
                res["gsc"] = {p["id"]: gsc_periodo(tk, e["gsc"], p) for p in PERIODOS} if e.get("gsc") else {}
                res["gsc_sitio"] = e.get("gsc")
            with lock:
                vivo[cid] = {**vivo.get(cid, {}), **res, "leido": AHORA}
            print(f"  google {cid}: GA {'sí' if e.get('ga') else '—'} · GSC {'sí' if e.get('gsc') else '—'}", flush=True)
        with ThreadPoolExecutor(10) as ex:
            if FUENTES & {"ga", "gsc"}:
                list(ex.map(uno, [c for c in clientes if c[1]["vivo"]]))

        # Bit24: comparar todas las propiedades de Search Console que contienen «bit24» (arreglo 2 de G4)
        sitios = [s["siteUrl"] for s in gg.get(tk, "https://www.googleapis.com/webmasters/v3/sites").get("siteEntry", [])]
        b24 = []
        for s in sitios:
            if "bit24" in s.lower() or "bit-24" in s.lower():
                b24.append({"sitio": s, "sep": gsc_tot(tk, s, "2026-09-01", "2026-09-30"), "sep_url": gsc_tot(tk, s, "2026-09-01", "2026-09-30", "byPage"),
                            "ago": gsc_tot(tk, s, "2026-08-01", "2026-08-31")})
        if "gsc" in FUENTES:
            vivo["_bit24_propiedades"] = b24

        # Meta
        import mt
        mtk = mt.llave("meta_token")
        for d, e in clientes:
            cuenta = e.get("meta")
            if cuenta and e["vivo"] and "meta" in FUENTES:
                vivo.setdefault(d["id"], {})["meta"] = meta_cliente(mtk, cuenta)
                vivo[d["id"]]["meta_cuenta"] = {"id": cuenta, "nombre": e.get("meta_nombre")}
                print(f"  meta {d['id']}: {cuenta}", flush=True)

        # Snov
        ext = C.leer(HERR / "externos.json", {}) or {}
        nombres = {}
        for d, e in clientes:
            o = (ext.get("clientes", {}).get((d.get("ids") or {}).get("panel") or d["nombre"]) or {}).get("outreach")
            if o and e["vivo"]:
                nombres[d["id"]] = {c["nombre"] for c in o.get("campanas", [])}
        try:
            if "snov" not in FUENTES:
                raise SystemExit("no pedido")
            sn = snov_todo(nombres)
            for cid, v in sn.items():
                vivo.setdefault(cid, {})["snov"] = v
        except SystemExit as ex:
            print("  snov: no se pudo leer:", ex)
        vivo["_leido"] = AHORA
        escribir_compacto(vivo_path, limpiar_cache(vivo))

    # Lo que ya no se empareja (correcciones) no sigue en la caché
    for d, e in clientes:
        v = vivo.get(d["id"])
        if not v:
            continue
        for k in ("ga", "gsc"):
            if CORRECCIONES.get(d["id"], {}).get(k) == "-":
                v.pop(k, None); v.pop("ga_prop" if k == "ga" else "gsc_sitio", None)
        if CORRECCIONES.get(d["id"], {}).get("meta") and (v.get("meta_cuenta") or {}).get("id") != e.get("meta"):
            v.pop("meta", None); v.pop("meta_cuenta", None)
    escribir_compacto(vivo_path, limpiar_cache(vivo))
    construir(clientes, vivo)


def limpiar_cache(o):
    """La caché tampoco guarda claves en URL (pedidos de WooCommerce con ?key=…, auditoría de seguridad)."""
    if isinstance(o, dict):
        return {k: limpiar_cache(v) for k, v in o.items()}
    if isinstance(o, list):
        return [limpiar_cache(v) for v in o]
    if isinstance(o, str) and ("?" in o or "&" in o) and "=" in o:
        return re.sub(r"([?&][^=&#\s]+)=[^&#\s]*", r"\1=…", o)
    return o


# ------------------------------------------------------------------ construir los ficheros del módulo
def snov_periodo(camps, pid):
    if not camps:
        return None

    def suma(clave):
        t = {k: 0 for k in SNOV_KEYS}
        for c in camps:
            for k in SNOV_KEYS:
                t[k] += ((c["stats"].get(clave) or {}).get(k) or 0)
        return t
    return {"actual": suma(pid), "anterior": suma(pid + "_ant"), "historico": suma("historico"),
            "campanas": [{"nombre": c["nombre"], "estado": c["estado"], "actual": c["stats"].get(pid), "anterior": c["stats"].get(pid + "_ant"),
                          "historico": c["stats"].get("historico")} for c in camps]}


def meta_periodo(m, p):
    return META298.periodo(m, p)


def seranking_de(cid):
    s = C.leer(CACHE / "seranking" / f"{cid}.json")
    if not s:
        return None
    pals = s.get("palabras") or []
    return {"site_id": s.get("site_id"), "leido": s.get("leido"), "fecha_fin": s.get("fecha_fin"), "fecha_ini": s.get("fecha_ini"),
            "buscadores": s.get("buscadores"), "nota": C.sanear(s.get("nota")), "palabras": [[C.sanear(p[0]), *p[1:]] for p in pals], "historia": s.get("historia")}


def estado_bloque(nombre, datos, nota_vacia):
    return {"estado": "bien" if datos else "sin_conectar", "nota": None if datos else nota_vacia}


def dejo_de_medir(ga):
    """Auditoría de cifras E-22: más de 50 usuarios el periodo anterior y 0 en este = la etiqueta ya no mide."""
    return (((ga.get("anterior") or {}).get("usuarios") or 0) > 50) and not ((ga.get("actual") or {}).get("usuarios") or 0)


def limpiar_ga(ga, p):
    """GA4 devuelve, con varios rangos y la dimensión fecha, días de la unión de rangos: se deja cada serie en el suyo."""
    if not ga or "_error" in ga:
        return ga
    g = dict(ga)
    dentro = lambda r, a, b: a <= r[0] <= b
    dias = g.get("dias") or []
    keep = [i for i, d in enumerate(dias) if p["desde"] <= d <= p["hasta"]]
    g["dias"] = [dias[i] for i in keep]
    g["serie"] = [r for r in (g.get("serie") or []) if dentro(r, p["desde"], p["hasta"])]
    g["serie_ant"] = [r for r in (g.get("serie_ant") or []) if dentro(r, *p["anterior"])]
    g["serie_anio"] = [r for r in (g.get("serie_anio") or []) if dentro(r, *p["anio_anterior"])]
    sinq = lambda u: re.sub(r"([?&][^=&#]+)=[^&#]*", r"\1=…", u or "")
    g["paginas"] = [dict(x, pagina=sinq(x["pagina"])) for x in g.get("paginas") or []]
    ren = lambda nom: "Correo electrónico" if nom == "Email" else C.sanear(nom)
    for k in ("eventos_dia", "canales_dia"):
        g[k] = {ren(nom): [v[i] for i in keep if i < len(v)] for nom, v in (g.get(k) or {}).items()}
    g["eventos"] = [dict(e, evento=C.sanear(e["evento"])) for e in g.get("eventos") or []]
    g["canal_evento"] = [[C.sanear(a), C.sanear(b), c] for a, b, c in g.get("canal_evento") or []]
    return g


def construir(clientes, vivo):
    SALIDA.mkdir(parents=True, exist_ok=True)
    looker = {x[0]: x for x in LOOKER}
    verdad = {c["cliente_id"]: c for c in (C.leer(APP / "data" / "verdad" / "clientes.json", {}) or {}).get("clientes", [])}
    gads_hora = "2026-10-02 13:57"
    for p in PERIODOS:
        filas_out = []
        for d, e in clientes:
            cid = d["id"]
            v = vivo.get(cid, {})
            F = d.get("fuentes") or {}
            ga = limpiar_ga((v.get("ga") or {}).get(p["id"]), p)
            gsc = (v.get("gsc") or {}).get(p["id"])
            meta = meta_periodo(v.get("meta"), p) if v.get("meta") else None
            snov = snov_periodo(v.get("snov"), p["id"]) if v.get("snov") else None
            capt = (F.get("captacion_ghl") or {}).get("datos") if p["id"] == "2026-09" else None
            ghl = (F.get("ghl") or {}).get("datos")
            gads = None
            if p["id"] == "2026-09" and cid in GADS_SEP:
                gads = dict(GADS_SEP[cid], periodo=["2026-09-01", "2026-09-30"], fuente="Windsor · muestra sellada 2-oct (14_GOOGLE_ADS_VIA_WINDSOR.md)")
            fila = {
                "cliente_id": cid, "nombre": d["nombre"], "web": d.get("web"),
                "account": (verdad.get(cid) or {}).get("account"),
                "ghl_subcuenta": ((F.get("captacion_ghl") or {}).get("emparejado") or {}).get("id") or ((F.get("ghl") or {}).get("emparejado") or {}).get("id"),
                "seranking_proyecto": ((F.get("seranking") or {}).get("emparejado") or {}).get("id"),
                "looker": None if cid not in looker else {"url": looker[cid][2], "tanda": looker[cid][4]},
                "fuentes": {
                    "ga4": {"estado": ("rota" if ga and "_error" in ga else "rota" if ga and dejo_de_medir(ga) else "a_cero" if ga and not (ga.get("actual") or {}).get("usuarios") else "bien") if ga else ("sin_conectar"),
                            "hora": v.get("leido"), "propiedad": v.get("ga_prop") or e.get("ga"), "nombre": (v.get("ga_nombre") or e.get("ga_nombre")) if (v.get("ga_prop") or e.get("ga")) else None,
                            "nota": (ga or {}).get("_error") or ("la etiqueta de Analytics dejó de medir: el periodo anterior tenía más de 50 usuarios y este, ninguno" if ga and dejo_de_medir(ga) else None)
                            or (None if e.get("ga") else e.get("ga_nota") or "sin propiedad de Analytics emparejada")},
                    "gsc": {"estado": ("rota" if gsc and "_error" in gsc else "a_cero" if gsc and not ((gsc.get("web") or {}).get("actual") or {}).get("impresiones") else "bien") if gsc else "sin_conectar",
                            "hora": v.get("leido"), "sitio": v.get("gsc_sitio") or e.get("gsc"),
                            "hasta_dato": (gsc or {}).get("hasta_dato"),
                            "nota": (gsc or {}).get("_error") or (None if e.get("gsc") else e.get("gsc_nota") or "sin sitio de Search Console emparejado")},
                    "meta": META298.fuente(meta, v.get("meta"), v.get("leido"), v.get("meta_cuenta"), (meta or {}).get("_error") or CORRECCIONES.get(cid, {}).get("_nota_meta") or (None if meta else (F.get("meta") or {}).get("nota") or "sin cuenta de Meta emparejada")),
                    "google_ads": {"estado": "bien" if gads else ("no_aplica" if cid not in GADS_PARADAS and cid not in GADS_FUERA_WINDSOR and cid not in looker else "sin_conectar"),
                                   "hora": gads_hora if gads else None, "medicion": "medias" if gads else "no",
                                   "nota": ("muestra sellada de septiembre: totales sin campañas ni serie diaria; el resto llega con la clave de Windsor" if gads else
                                            f"campañas paradas desde el {GADS_PARADAS[cid]} (Windsor)" if cid in GADS_PARADAS else
                                            "la cuenta no está en Windsor: llega con la conexión directa de Google Ads" if cid in GADS_FUERA_WINDSOR else
                                            "llega con la conexión de Google Ads (Windsor o directa)")},
                    "seranking": {"estado": "bien" if seranking_de(cid) else "sin_conectar", "hora": (seranking_de(cid) or {}).get("leido"),
                                  "nota": None if seranking_de(cid) else "posiciones por proyecto: la clave de proyectos da 403; se leen con el conector de SE Ranking (hoy, los 22 de Looker)"},
                    "ghl": {"estado": (F.get("captacion_ghl") or {}).get("estado") or "sin_conectar", "hora": (F.get("captacion_ghl") or {}).get("hora"),
                            "nota": (F.get("captacion_ghl") or {}).get("nota")},
                    "snov": {"estado": "bien" if snov else "sin_conectar", "hora": v.get("leido"), "nota": None if snov else "sin campañas de Snov.io con su nombre"},
                    "linkedin": {"estado": "sin_conectar", "nota": "hoja de Linked Helper sin conectar: hace falta el enlace de la hoja de cada cliente (el permiso de lectura de hojas ya está en gg.py)"},
                    "ficha_google": {"estado": "sin_conectar", "nota": "se conecta en fase 2 (permiso business.manage o SE Ranking Local)"},
                },
                "ga4": None if not ga or "_error" in ga else ga,
                "gsc": None if not gsc or "_error" in gsc else dict(gsc, paginas=[[re.sub(r"([?&][^=&#]+)=[^&#]*", r"\1=…", r[0]), *r[1:]] for r in gsc.get("paginas") or []]),
                "meta": None if not meta or "_error" in meta else meta,
                "google_ads": gads,
                "seranking": seranking_de(cid) if p["id"] in ("2026-09", "u30") else None,
                "seranking_otro_periodo": bool(seranking_de(cid)) and p["id"] not in ("2026-09", "u30"),
                "embudo": capt and {"citas": (capt.get("citas") or {}).get("mes_anterior"), "funnel_90d": (capt.get("embudo") or {}).get("funnel"),
                                    "leads_ghl": ((capt.get("embudo") or {}).get("leads_nuevos") or {}).get("mes_anterior"),
                                    "estancados_72h": (capt.get("embudo") or {}).get("estancados_72h"),
                                    "pct_estancado": (capt.get("embudo") or {}).get("pct_estancado"),
                                    "horas_max_parado": (capt.get("embudo") or {}).get("horas_max_parado"),
                                    "ganadas_total": (ghl or {}).get("opp_won")},
                "snov": snov,
                "avisos": [{"color": a, "tipo": t, "texto": tx, "quien": q} for a, t, tx, q in ARREGLOS.get(cid, [])] + [
                    {"color": "ambar", "tipo": "sin_acceso_google", "quien": "Agus · SEO",
                     "texto": f"Su Looker enseña {q} con otra cuenta de Google; la cuenta de Google de la app no ve la propiedad de este cliente. Hay que darle acceso de lector para igualar ese bloque."}
                    for q, falta in (("Analytics", "ga4" in (looker.get(cid, [None] * 4)[3] or []) and not (v.get("ga_prop") or e.get("ga"))),
                                     ("Search Console", any(b in (looker.get(cid, [None] * 4)[3] or []) for b in ("gsc_web", "gsc_url")) and not (v.get("gsc_sitio") or e.get("gsc"))))
                    if falta],
            }
            if cid == "bit-24" and vivo.get("_bit24_propiedades"):
                fila["bit24_propiedades"] = vivo["_bit24_propiedades"]
            filas_out.append(fila)
        doc = {"_meta": {"generado": AHORA, "periodo": p, "leido_en_vivo": vivo.get("_leido"),
                         "nota": "Solo lectura. Una fila por cliente (cliente_id): servir.py recorta por cartera y quita gasto, coste y cpl a quien no ve la inversión."},
               "filas": filas_out}
        sin_urls = json.loads(json.dumps(doc), object_hook=lambda o: {k: ("" if isinstance(v, str) and v.startswith("https://lookerstudio.google.com/") else v) for k, v in o.items()})
        h = C.escanear(sin_urls)
        if h:
            sys.exit("Puerta de secretos: no escribo p_%s.json → %s" % (p["id"], h[:5]))
        escribir_compacto(SALIDA / f"p_{p['id']}.json", doc)
        print(f"data/informe/p_{p['id']}.json · {len(filas_out)} clientes", flush=True)

    # Paridad
    par = []
    sep = {f["cliente_id"]: f for f in C.leer(SALIDA / "p_2026-09.json")["filas"]}
    for cid, nombre, url, bloques, tanda, plantillas, estado_looker, cifras in LOOKER:
        par.append({"cliente_id": cid, "nombre": nombre, "looker": url, "tanda": tanda, "plantillas": plantillas,
                    "bloques": bloques, "estado_looker": estado_looker, "cifras_looker": cifras,
                    "visto_looker": "2026-10-02 12:58-13:35 (05_INVENTARIO_LOOKER_STUDIO.md)"})
    C.escribir(SALIDA / "paridad.json", {"_meta": {"generado": AHORA, "fuente": "G4 §8 y 05 §3", "tolerancias": {"ga4": 2, "gsc": 2, "seranking": 0, "google_ads": 1, "meta": 1}},
                                          "filas": par})
    C.escribir(SALIDA / "comun.json", {"_meta": {"generado": AHORA}, "periodos": PERIODOS, "defecto": "2026-09"})
    print("paridad.json y comun.json escritos.")
    # N10 (auditoría 37, causa 5): índice ligero + un fichero por cliente, para no bajar los 68 clientes al abrir uno.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import partir_informe
    partir_informe.main()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""despliegue/emergencia.py · página de emergencia por persona (sección C.4 del documento 26). Solo enlaces, sin datos.

Si cae la app (Render) o cae Cloudflare, cada persona sigue trabajando desde sus atajos a las herramientas.
Se genera cada noche desde la tubería (paso «emergencia» de la vuelta completa) y deja, en
despliegue/estado/emergencia/:
  · sitio/index.html + sitio/p/<persona>.html     → Cloudflare Pages detrás de Access (emergencia.<dominio>)
  · marcadores/marcadores_<persona>.html          → fichero de marcadores que cada uno importa una vez en el navegador
  · clickup/<puesto>.md                           → texto del documento de ClickUp «Si la app no va» por puesto
                                                     (NO se envía: subirlo a ClickUp lo hace quien tenga permiso)
Sin cifras, sin correos ni teléfonos: solo el nombre del cliente y enlaces a SU herramienta (que pide su propio inicio
de sesión). Los enlaces salen de lo que ya traen data/ (ficha, CRM, SEO, redes) y de emergencia_enlaces.json.

Uso: python3 despliegue/emergencia.py [--salida <carpeta>]
"""
import html
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path

AQUI = Path(__file__).resolve().parent
APP = AQUI.parent
DATA = APP / "data"
sys.path.insert(1, str(APP))
import config  # noqa: E402

ENLACES = json.loads((AQUI / "emergencia_enlaces.json").read_text())
# Qué atajos de cliente lleva cada puesto (claves de enlace_cliente())
POR_PUESTO = {
    "account": ["clickup", "clickupFolder", "ghl", "metaAds", "drive", "looker", "statusSheet"],
    "trafficker": ["metaAds", "googleAds", "ghl", "clickup"],
    "jefa_publicidad": ["metaAds", "googleAds", "ghl", "clickup"],
    "jefa_crm": ["ghl", "conversaciones", "calendarios", "flujos", "clickup"],
    "especialista_ghl": ["ghl", "conversaciones", "calendarios", "flujos", "clickup"],
    "seo": ["searchConsole", "analytics", "seranking", "web", "clickup"],
    "jefa_seo": ["searchConsole", "analytics", "seranking", "web", "clickup"],
    "ficha_google": ["searchConsole", "web", "clickup"],
    "web": ["web", "analytics", "searchConsole", "clickup"],
    "redes": ["metricool", "clickup", "drive"],
    "produccion": ["clickup", "drive"],
    "proyectos": ["clickup", "clickupFolder", "drive"],
}
TODA_LA_CARTERA = {"direccion", "operaciones", "finanzas_direccion", "proyectos"}
SILLA_DE = {"trafficker": "trafficker", "jefa_publicidad": "trafficker", "jefa_crm": "crm", "especialista_ghl": "crm",
            "seo": "seo", "jefa_seo": "seo", "ficha_google": "seo", "web": "web", "redes": "redes", "account": "account",
            "produccion": None}
ETIQUETA = {"clickup": "Lista de ClickUp", "clickupFolder": "Carpeta de ClickUp", "ghl": "Subcuenta de GHL",
            "conversaciones": "Conversaciones de GHL", "calendarios": "Calendarios de GHL", "flujos": "Flujos de GHL",
            "metaAds": "Meta Ads", "googleAds": "Google Ads", "drive": "Drive", "looker": "Looker Studio",
            "statusSheet": "Hoja de estado", "searchConsole": "Search Console", "analytics": "Analytics",
            "seranking": "SE Ranking", "web": "La web", "metricool": "Metricool"}
RX_CODIGO = re.compile(r"(?i)[?&](pwd|token|key|code|passcode)=")


def leer(rel, defecto=None):
    try:
        return json.loads((DATA / rel).read_text())
    except Exception:
        return defecto


def urls_en(obj, profundidad=4):
    if profundidad < 0:
        return
    if isinstance(obj, str):
        if obj.startswith("https://") and not RX_CODIGO.search(obj):
            yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from urls_en(v, profundidad - 1)
    elif isinstance(obj, list):
        for v in obj[:50]:
            yield from urls_en(v, profundidad - 1)


def enlaces_por_cliente():
    """{cliente_id: {clave: url}} juntando ficha (portal), CRM, SEO, redes y la capa E1 (web)."""
    out = {}
    for f in (leer("ficha/portal.json", {}) or {}).get("filas", []):
        d = out.setdefault(f["cliente_id"], {})
        for r in f.get("recursos") or []:
            if r.get("url") and not RX_CODIGO.search(r["url"]):
                d[r["k"]] = r["url"]
    for s in (leer("crm/crm.json", {}) or {}).get("subcuentas", []):
        if s.get("cliente_id"):
            e = s.get("enlaces") or {}
            d = out.setdefault(s["cliente_id"], {})
            for k in ("ghl", "conversaciones", "calendarios", "flujos"):
                if e.get(k):
                    d[k] = e[k]
    for c in (leer("seo/seo.json", {}) or {}).get("clientes", []):
        d = out.setdefault(c.get("cliente_id"), {})
        for u in urls_en(c.get("seranking")):
            if "seranking.com" in u:
                d.setdefault("seranking", u)
        if isinstance(c.get("web"), str) and c["web"].startswith("http"):
            d.setdefault("web", c["web"])
    for c in (leer("redes/redes.json", {}) or {}).get("clientes", []):
        d = out.setdefault(c.get("cliente_id"), {})
        for u in urls_en(c):
            if "app.metricool.com" in u:
                d.setdefault("metricool", u)
                break
    for f in DATA.glob("clientes/*.json"):
        c = leer(f"clientes/{f.name}", {}) or {}
        w = c.get("web")
        if isinstance(w, str) and w:
            out.setdefault(c.get("id"), {}).setdefault("web", w if w.startswith("http") else "https://" + w)
    out.pop(None, None)
    return out


def cartera(persona, asignaciones, clientes_activos):
    hoy = date.today().isoformat()
    if set(persona["puestos"]) & TODA_LA_CARTERA:
        return sorted(clientes_activos)
    sillas = {SILLA_DE.get(p) for p in persona["puestos"]} - {None}
    return sorted({a["cliente_id"] for a in asignaciones
                   if a.get("persona_id") == persona["id"] and (not sillas or a.get("silla") in sillas)
                   and (not a.get("hasta") or a["hasta"] >= hoy) and a["cliente_id"] in clientes_activos})


def bloques(persona, nombres, mis_clientes, enl):
    """[(título, [(texto, url)])]"""
    B = [("Para todos", [(x["t"], x["url"]) for x in ENLACES["comunes"]])]
    for p in persona["puestos"]:
        g = ENLACES["por_puesto"].get(p)
        if g:
            B.append((f"Tu puesto · {p.replace('_', ' ')}", [(x["t"], x["url"]) for x in g]))
    claves = []
    for p in persona["puestos"]:
        for k in POR_PUESTO.get(p, POR_PUESTO["account"] if set(persona["puestos"]) & TODA_LA_CARTERA else []):
            if k not in claves:
                claves.append(k)
    for cid in mis_clientes:
        fila = [(ETIQUETA.get(k, k), enl.get(cid, {}).get(k)) for k in claves if enl.get(cid, {}).get(k)]
        if fila:
            B.append((nombres.get(cid, cid), fila))
    return B


def pagina(persona, B, generado):
    e = html.escape
    secciones = "".join(
        f"<section><h2>{e(t)}</h2><ul>" + "".join(
            f'<li><a href="{e(u)}" target="_blank" rel="noopener">{e(x)} ↗</a></li>' if u and u.startswith("http")
            else f"<li><span class='gris'>{e(x)} · {e(u or 'falta el enlace')}</span></li>" for x, u in L) + "</ul></section>"
        for t, L in B)
    return f"""<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Emergencia · {e(persona['nombre'])}</title><meta name="robots" content="noindex">
<style>:root{{--fondo:#fff;--texto:#14213d;--suave:#5b6478;--linea:#e3e7ef;--marino:#1d3557;--aviso:#fff4e5;--ambar:#9a5b00}}
body{{margin:0;background:var(--fondo);color:var(--texto);font:16px/1.45 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif}}
main{{max-width:880px;margin:0 auto;padding:16px}}h1{{font-size:1.35rem;margin:.2rem 0}}h2{{font-size:1rem;color:var(--marino);margin:1.2rem 0 .4rem;border-bottom:1px solid var(--linea);padding-bottom:.2rem}}
.aviso{{background:var(--aviso);color:var(--ambar);border-radius:8px;padding:12px 14px;margin:12px 0}}ul{{list-style:none;padding:0;margin:0;display:flex;flex-wrap:wrap;gap:8px}}
a{{display:inline-block;padding:8px 12px;border:1px solid var(--linea);border-radius:8px;color:var(--marino);text-decoration:none;min-height:28px}}a:hover{{background:#f3f6fb}}
.gris{{display:inline-block;padding:8px 12px;color:var(--suave)}}footer{{color:var(--suave);font-size:.85rem;margin:2rem 0 1rem}}</style></head>
<body><main><h1>Si la app no va · {e(persona['nombre'])}</h1>
<div class="aviso"><strong>La app no responde.</strong> Trabaja desde aquí y avisa en el canal «Fallos app» de ClickUp.
Estado del sistema: <a href="{e(ENLACES['estado_sistema'])}" target="_blank" rel="noopener">ver ↗</a></div>
{secciones}<footer>Solo enlaces a tus herramientas; cada una te pide su propio inicio de sesión. Generada el {generado}.</footer></main></body></html>"""


def marcadores(persona, B):
    e = html.escape
    filas = "".join(f"<DT><H3>{e(t)}</H3>\n<DL><p>\n" + "".join(f'<DT><A HREF="{e(u)}">{e(x)}</A>\n' for x, u in L if u and u.startswith("http"))
                    + "</DL><p>\n" for t, L in B)
    return ("<!DOCTYPE NETSCAPE-Bookmark-file-1>\n<META HTTP-EQUIV=\"Content-Type\" CONTENT=\"text/html; charset=UTF-8\">\n"
            f"<TITLE>Marcadores RO</TITLE>\n<H1>RO · si la app no va ({e(persona['nombre'])})</H1>\n<DL><p>\n{filas}</DL><p>\n")


def main():
    salida = Path(sys.argv[sys.argv.index("--salida") + 1]) if "--salida" in sys.argv else config.ESTADO_DIR / "emergencia"
    personas = [p for p in leer("personas.json", []) if p.get("activo") and p.get("puestos")]
    asign = leer("asignaciones.json", [])
    clientes = leer("clientes.json", [])
    nombres = {c["id"]: c.get("nombre", c["id"]) for c in clientes}
    activos = {c["id"] for c in clientes if c.get("activo", True) is not False and c.get("estado") != "baja"}
    enl = enlaces_por_cliente()
    generado = datetime.now().strftime("%d-%m-%Y %H:%M")
    (salida / "sitio/p").mkdir(parents=True, exist_ok=True)
    (salida / "marcadores").mkdir(parents=True, exist_ok=True)
    (salida / "clickup").mkdir(parents=True, exist_ok=True)
    indice, por_puesto = [], {}
    for p in personas:
        B = bloques(p, nombres, cartera(p, asign, activos), enl)
        (salida / f"sitio/p/{p['id']}.html").write_text(pagina(p, B, generado))
        (salida / f"marcadores/marcadores_{p['id']}.html").write_text(marcadores(p, B))
        indice.append(p)
        for pu in p["puestos"]:
            por_puesto.setdefault(pu, B[:2])
    e = html.escape
    lista = "".join(f'<li><a href="p/{e(p["id"])}.html">{e(p["nombre"])}</a></li>' for p in sorted(indice, key=lambda x: x["nombre"]))
    base = pagina({"nombre": "elige tu nombre"}, [], generado)
    (salida / "sitio/index.html").write_text(base.replace("<footer>", f"<section><h2>Personas</h2><ul>{lista}</ul></section><footer>"))
    for pu, B in por_puesto.items():
        md = [f"# Si la app no va · {pu.replace('_', ' ')}", "", "La app no responde: trabaja desde aquí y avisa en el canal «Fallos app».", ""]
        for t, L in B:
            md += [f"## {t}", ""] + [f"- [{x}]({u})" for x, u in L if u and u.startswith("http")] + [""]
        md.append("Los atajos de cada cliente están en tu página personal y en tu fichero de marcadores.")
        (salida / f"clickup/{pu}.md").write_text("\n".join(md))
    print(f"Emergencia: {len(indice)} páginas, {len(indice)} ficheros de marcadores y {len(por_puesto)} textos de ClickUp en {salida}")


if __name__ == "__main__":
    main()

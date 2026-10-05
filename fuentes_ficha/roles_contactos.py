#!/usr/bin/env python3
"""
roles_contactos.py · «quién es cada uno» de los contactos de los clientes (M4, 2-oct-2026). SOLO LECTURA.

Lee el documento ~/Downloads/MOVILES_Y_CORREOS_CLIENTES_RO_2026-10-02.md (64 clientes, 82 móviles, 344 correos)
y, para cada correo, busca el cargo en:
  · Zoho CRM: campo Title de Contactos y Designation de Leads (COQL, por correo).
  · Zoho Desk: campo «title» del contacto, la fecha del último hilo que ha escrito él y la FIRMA de ese hilo
    (las 1-2 líneas cortas que siguen a su nombre al final del mensaje; se guardan literales con su ticket).
GHL no se consulta aquí: su llave rota en cada uso y la lleva la tubería (C5); el documento ya trae los nombres de GHL.

Escribe fuentes_ficha/_cache/roles.json (no se sirve nunca: fuentes_ficha/ no es estático). generar_ficha.py lo usa.
Uso: python3 fuentes_ficha/roles_contactos.py [--solo-crm]
"""
import html
import json
import re
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
sys.path.insert(0, str(_cfg.HERRAMIENTAS / "zoho"))
sys.argv = sys.argv[:1] + [a for a in sys.argv[1:]]
import zh  # noqa: E402
from agenda_md import leer_agenda, es_generico  # noqa: E402
import pathlib as _pl_l27, sys as _sys_l27  # L-27: rutas del Mac por config.py
if str(_pl_l27.Path(__file__).resolve().parents[1]) not in _sys_l27.path:
    _sys_l27.path.append(str(_pl_l27.Path(__file__).resolve().parents[1]))
import config as _cfg  # noqa: E402

CACHE = AQUI / "_privado" / "roles.json"   # ronda 6 (M6): correos de contactos, solo en _privado/
DESK = "https://desk.zoho.eu/api/v1"


def main():
    ag = leer_agenda()
    correos = sorted({c["correo"].lower() for cl in ag["clientes"].values() for c in cl["correos"]})
    print(f"{len(ag['clientes'])} clientes · {len(correos)} correos")
    tk, api = zh.acceso()
    out = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    out.setdefault("crm", {}); out.setdefault("desk", {})

    # ---- CRM: Contacts.Title y Leads.Designation, de 40 en 40 ----
    def coql(q):
        req = urllib.request.Request(api + "/crm/v6/coql", data=json.dumps({"select_query": q}).encode(), method="POST",
                                     headers={"Authorization": "Zoho-oauthtoken " + tk, "Content-Type": "application/json"})
        try:
            r = urllib.request.urlopen(req, timeout=60).read()
            return json.loads(r) if r else {}
        except urllib.error.HTTPError as e:
            return {"_error": e.code, "_msg": e.read().decode()[:200]}
    for i in range(0, len(correos), 40):
        lote = correos[i:i + 40]
        lista = ",".join("'" + c.replace("'", "") + "'" for c in lote)
        for modulo, campo in (("Contacts", "Title"), ("Leads", "Designation")):
            r = coql(f"select Full_Name, Email, {campo}, Department from {modulo} where Email in ({lista}) limit 200" if modulo == "Contacts"
                     else f"select Full_Name, Email, {campo}, Company from {modulo} where Email in ({lista}) limit 200")
            if r.get("_error"):
                print("CRM", modulo, r); continue
            for x in r.get("data", []):
                e = (x.get("Email") or "").lower()
                cargo = (x.get(campo) or "").strip()
                d = out["crm"].setdefault(e, {})
                d.setdefault("nombres", [])
                if x.get("Full_Name") and x["Full_Name"] not in d["nombres"]:
                    d["nombres"].append(x["Full_Name"])
                if cargo:
                    d["cargo"] = cargo; d["fuente"] = f"Zoho CRM ({'contacto, Title' if modulo == 'Contacts' else 'lead, Designation'})"
                if x.get("Department"):
                    d["departamento"] = x["Department"]
    print("CRM con cargo:", sum(1 for v in out["crm"].values() if v.get("cargo")), "de", len(out["crm"]))
    CACHE.parent.mkdir(exist_ok=True); CACHE.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    if "--solo-crm" in sys.argv:
        return

    # ---- Desk: contacto (title), último hilo suyo y firma ----
    oid = str(zh.get(tk, DESK + "/organizations")["data"][0]["id"])
    alias = {}
    for cl in ag["clientes"].values():
        for c in cl["correos"]:
            alias[c["correo"].lower()] = (c["nombres"], "Desk" in c["donde"], es_generico(c))

    def g(url):
        r = {}
        for intento in range(4):
            try:
                r = zh.get(tk, url, orgId=oid)
            except ValueError:
                return {}                       # 204 sin cuerpo: no hay resultados
            except Exception as ex:
                time.sleep(3); r = {"_error": str(ex)}; continue
            if r.get("_error") == 429:
                time.sleep(5 * (intento + 1)); continue
            return r
        return r

    def uno(e):
        nombres, en_desk, generico = alias[e]
        if not en_desk:
            return e, {"no_en_desk": True}
        r = g(f"{DESK}/contacts/search?email={urllib.parse.quote(e)}&limit=1")
        con = (r.get("data") or [None])[0]
        if not con:
            return e, {"sin_contacto": True}
        res = {"title": (con.get("title") or "").strip() or None, "nombre": " ".join(x for x in (con.get("firstName"), con.get("lastName")) if x)}
        t = g(f"{DESK}/contacts/{con['id']}/tickets?limit=5&sortBy=-modifiedTime")
        tickets = t.get("data") or []
        if not tickets:
            return e, res
        # el hilo más reciente escrito por esa dirección (entre sus 5 tickets más recientes)
        mejor = None
        for tic in tickets:
            th = g(f"{DESK}/tickets/{tic['id']}/threads?limit=30")
            for x in th.get("data") or []:
                if e in (x.get("fromEmailAddress") or "").lower() and x.get("direction") == "in":
                    if not mejor or x["createdTime"] > mejor[1]["createdTime"]:
                        mejor = (tic, x)
            if mejor:
                break
        if not mejor:
            res["ultimo_ticket"] = tickets[0].get("createdTime", "")[:10]
            return e, res
        tic, x = mejor
        res["ultimo_suyo"] = x["createdTime"][:10]
        res["ticket"] = tic.get("ticketNumber")
        if generico:
            return e, res
        full = g(f"{DESK}/tickets/{tic['id']}/threads/{x['id']}")
        texto = a_texto(full.get("content") or "")
        firma = sacar_firma(texto, nombres + [res["nombre"]])
        if firma:
            res["firma"] = firma
        return e, res

    pend = [e for e in correos if e not in out["desk"]]
    print("Desk: por leer", len(pend))
    with ThreadPoolExecutor(max_workers=5) as ex:
        for n, (e, r) in enumerate(ex.map(uno, pend), 1):
            out["desk"][e] = r
            if n % 25 == 0:
                CACHE.write_text(json.dumps(out, ensure_ascii=False, indent=1)); print(" ", n)
    CACHE.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print("Desk con firma:", sum(1 for v in out["desk"].values() if v.get("firma")), "· con title:", sum(1 for v in out["desk"].values() if v.get("title")))


def a_texto(h):
    h = re.sub(r"(?is)<(style|script)[^>]*>.*?</\1>", "", h)
    h = re.sub(r"(?i)<br\s*/?>|</(p|div|tr|li|h\d)>", "\n", h)
    t = html.unescape(re.sub(r"<[^>]+>", " ", h))
    lineas = [re.sub(r"[ \t ]+", " ", l).strip() for l in t.split("\n")]
    # corta lo citado (respuestas anteriores)
    out = []
    for l in lineas:
        if re.match(r"(?i)^(de|from|enviado|sent|el .{5,80} escribi[óo]|on .{5,80} wrote|-{3,}|_{5,}|> )", l):
            break
        out.append(l)
    return [l for l in out if l]


NO_CARGO = re.compile(r"(?i)(@|https?:|www\.|\d{3}|tel[eé]f|m[oó]vil|tlf|fax|calle|c/|avda|avenida|plaza|pol[ií]gono|aviso legal|confidencial|este mensaje|antes de imprimir|saludos|un saludo|gracias|atentamente|cordialmente|regards)")


def sacar_firma(lineas, nombres):
    """Las líneas cortas justo debajo del nombre de la persona en los 14 últimos renglones del mensaje."""
    cola = lineas[-45:]
    claves = set()
    for n in nombres:
        n = re.sub(r"[^\wáéíóúñü ]", " ", (n or "").lower())
        partes = [p for p in n.split() if len(p) > 2]
        if len(partes) >= 2:
            claves.add((partes[0], partes[-1]))
    for i in range(len(cola) - 1, -1, -1):
        l = cola[i]
        ll = l.lower()
        if len(l) > 70 or not any(a in ll and b in ll for a, b in claves):
            continue
        cargo = []
        for s in cola[i + 1:i + 3]:
            if len(s) > 60 or NO_CARGO.search(s) or re.search(r"\d|reacted|message|mensaje", s, re.I) or not re.search(r"[A-Za-zÁÉÍÓÚáéíóúñ]{3}", s):
                break
            cargo.append(s)
        if cargo:
            return {"nombre_firma": l, "lineas": cargo}
    return None


if __name__ == "__main__":
    import urllib.parse  # noqa: F401
    main()

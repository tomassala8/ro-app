"""personas_cliente.py · une móviles, correos y personas del portal de UN cliente en personas (M4, 2-oct-2026).

Reglas (solo con prueba; lo dudoso no se adivina, va a `dudas`):
  1. Mismo correo o mismo móvil → misma persona.
  2. Mismo nombre y apellido (sin tildes ni mayúsculas) → misma persona.
  3. Nombre de pila suelto («Patricia») → se une a la ÚNICA persona del cliente con ese nombre; si hay dos o más, duda.
  4. Los buzones genéricos (info@, hello@, clientes@…) son su propia ficha («Buzón general») y nunca se unen por nombre.
Nombre que se enseña (uno solo): portal > Zoho CRM > Desk > documento de móviles > alias más completo del documento.
Si los nombres con el mismo apellido no casan entre sí («Gert Jan Geerse» / «Gerben Geerse»), se enseña el más usado
y la persona va a `dudas` con los dos nombres. Los demás alias quedan en «también aparece como».
Rol: solo lo que dice una fuente (portal, documento, Zoho CRM, Desk, firma de correo, nombre en WhatsApp); si no hay, «rol sin confirmar».
"""
import re
from collections import Counter

from agenda_md import norm, es_generico

CARGO_DECISOR = re.compile(r"(?i)\b(decisor|socio|socia|director|directora|gerente|ceo|fundador|fundadora|propietari[oa]|titular|administrador[a]? [uú]nic|presidente|managing|partner|owner)\b")
DIA_A_DIA = re.compile(r"(?i)(d[ií]a a d[ií]a|interlocutor|coordinaci|operativ|gestor[a]? (de )?accesos|contacto habitual)")
WA = re.compile(r"WhatsApp \(chat «([^»]+)»\)")


def tel_norm(t):
    d = re.sub(r"\D", "", t or "")
    if len(d) == 9:
        d = "34" + d
    return d


def partes(nombre):
    n = norm(re.sub(r"\(.*?\)", " ", nombre or ""))
    return [p for p in n.split() if len(p) > 1 and "@" not in p]


def casa_con_correo(nombre, correo):
    """¿El nombre casa con la dirección? (jbascon@ ↔ Javier Bascón sí; jbascon@ ↔ Carlos Niño no; phg@ ↔ Patricia Hermosilla G. sí)."""
    loc = re.sub(r"[^a-z]", "", norm(correo.split("@")[0]))
    toks = [t for t in partes(nombre) if len(t) >= 3]
    if not toks or not loc:
        return False
    if any(t[:4] in loc for t in toks if len(t) >= 4) or any(t == loc for t in toks):
        return True
    ini = "".join(t[0] for t in partes(nombre))
    return len(loc) <= 4 and (loc.startswith(ini[:2]) if len(ini) >= 2 else loc[0] == ini[:1])


def es_nombre_persona(n):
    p = partes(n)
    return len(p) >= 1 and not re.search(r"(?i)\b(asesor|consult|general|oficina|laboral|fiscal|contabilidad|administraci|recepci|spain|s\.?l\.?|abogados|gestor[ií]a|despacho|grupo|team|equipo|info|clientes|admin)\b", n or "")


class UF:
    def __init__(self): self.p = {}
    def f(self, x):
        self.p.setdefault(x, x)
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]; x = self.p[x]
        return x
    def u(self, a, b): self.p[self.f(a)] = self.f(b)


import json as _json
from pathlib import Path as _Path
import sys as _sys
_sys.path.insert(1, str(_Path(__file__).resolve().parents[1]))
from telefono import limpiar as _limpiar_tel   # noqa: E402  regla común de teléfonos (3-oct): «+34…» sin espacios, extensión aparte
_MAN = _Path(__file__).resolve().parent / "_privado" / "contactos_manual.json"   # privado: el escáner y la subida no lo recorren
MANUAL = _json.loads(_MAN.read_text()) if _MAN.exists() else {}


def construir(ag, portal_contactos, roles, nombre_cliente, cliente_id=None):
    """ag: bloque del documento (o None) · portal_contactos: contacts de portal_clientes.json · roles: cache de roles_contactos.py."""
    nodos = {}           # id → {tipo, nombres[], ...}
    uf = UF()
    ag = ag or {"moviles": [], "correos": [], "notas": [], "fijos": [], "dominios": [], "account": ""}
    crm, desk = roles.get("crm", {}), roles.get("desk", {})
    CLIENTE_TOK[:] = [w for w in norm(nombre_cliente).split() if w]
    ruido = set(partes(nombre_cliente)) | {norm(d).split(".")[0] for d in ag.get("dominios", [])} | {"asesores", "asesoria", "consulting", "consultores", "economistes", "economistas", "abogados", "spain", "advisory", "gestoria", "grup", "grupo"}

    NC = {k.lower(): v for k, v in MANUAL.get("nombre_correo", {}).items()}
    compartidos = {tel_norm(x["tel"]): x for x in MANUAL.get("tel_compartido", []) if x.get("cliente") == cliente_id}
    for i, p in enumerate(portal_contactos or []):
        nombre = p.get("name")
        mails = [m.lower() for m in (p.get("emails") or [])]
        tels = [x.get("display") for x in (p.get("phones") or []) if x.get("display")]
        forzado = None
        for r in MANUAL.get("nombre_portal", []):
            if r.get("cliente") == cliente_id and nombre == r["nombre"]:
                nombre = forzado = r["es"]
        for m in mails:
            if m in NC:
                nombre = forzado = NC[m]
        for r in MANUAL.get("quitar_tel", []):
            if r.get("cliente") == cliente_id and (p.get("name") or "") == r["persona"]:
                tels = [t for t in tels if tel_norm(t) != tel_norm(r["tel"])]
        nodos[f"P{i}"] = {"tipo": "portal", "orden": i, "nombres": [nombre] if nombre else [], "rol": p.get("role"), "src": p.get("src"),
                          "nota": p.get("notes"), "tels": tels, "mails": mails, "forzado": forzado}
    for i, m in enumerate(ag["moviles"]):
        nodos[f"M{i}"] = {"tipo": "movil", "nombres": [m["nombre"]] if m["nombre"] else [], "tel": m["tel"], "detalle": m["detalle"], "fuente": m["fuente"]}
    for i, c in enumerate(ag["correos"]):
        gen = es_generico(c) or re.sub(r"[\d._-]+", "", c["correo"].split("@")[0]) in ruido
        nombres = list(c["nombres"])
        e = c["correo"]
        if crm.get(e, {}).get("nombres"):
            nombres += crm[e]["nombres"]
        if desk.get(e, {}).get("nombre"):
            nombres.append(desk[e]["nombre"])
        nombres = [n for n in nombres if n]
        otros = []
        if not gen:
            buenos = [n for n in nombres if casa_con_correo(n, e)]
            if buenos or len(re.sub(r"[^a-z]", "", e.split("@")[0])) >= 4:
                otros = [n for n in nombres if n not in buenos]       # «Carlos Niño» como remitente de jbascon@: no es él
                nombres = buenos
        forzado = NC.get(e)
        if forzado:   # respuesta de Tomás: este correo es de esta persona
            otros = [n for n in nombres + otros if norm(n) != norm(forzado)]
            nombres = [forzado]
        nodos[f"C{i}"] = {"tipo": "correo", "generico": gen, "nombres": nombres, "otros": otros, "correo": e, "dato": c, "forzado": forzado}
    for k in nodos:
        uf.f(k)

    # 1 · mismo correo / mismo móvil
    por_mail, por_tel, dudas_tel = {}, {}, []
    for k, n in nodos.items():
        for e in n.get("mails", []) + ([n["correo"]] if n.get("correo") else []):
            if e in por_mail: uf.u(k, por_mail[e])
            else: por_mail[e] = k
        for t in n.get("tels", []) + ([n["tel"]] if n.get("tel") else []):
            t = tel_norm(t)
            if t in compartidos:
                continue          # móvil compartido (respuesta de Tomás): queda en las dos personas, sin unirlas
            if t.startswith("34") and t[2:3] in "89":
                continue          # un fijo lo comparten varias personas de la oficina: no las une
            if t in por_tel:
                pa = {partes(limpio(x, ruido))[0] for x in n["nombres"] if partes(limpio(x, ruido)) and es_nombre_persona(x)}
                pb = {partes(limpio(x, ruido))[0] for x in nodos[por_tel[t]]["nombres"] if partes(limpio(x, ruido)) and es_nombre_persona(x)}
                if pa and pb and not (pa & pb) and not mismo_pila(pa | pb, set()):
                    dudas_tel.append({"tipo": "el mismo móvil para dos personas", "nombres": sorted({bonito(x) for x in n["nombres"] + nodos[por_tel[t]]["nombres"]}),
                                      "correos": [], "telefono": t})
                    continue          # Óscar y Belén con el mismo móvil en el portal: no se juntan, se pregunta
                uf.u(k, por_tel[t])
            else: por_tel[t] = k

    # 1b · la misma parte local en dos dominios del despacho (p. ej., inventado: ana.ruiz@ejemplo.es y ana.ruiz@ejemplo.com)
    por_local = {}
    for k, n in nodos.items():
        if n.get("correo") and not n.get("generico"):
            loc = n["correo"].split("@")[0]
            if len(loc) >= 3 and not re.search(r"gmail|hotmail|yahoo|outlook|icloud", n["correo"]):
                if loc in por_local: uf.u(k, por_local[loc])
                else: por_local[loc] = k

    # 2 · mismo nombre y apellido (los buzones genéricos no se unen por nombre)
    clave = {}
    for k, n in nodos.items():
        if n.get("generico"):
            continue
        for nom in n["nombres"]:
            p = partes(nom)
            p = partes(limpio(nom, ruido))
            if len(p) >= 2 and es_nombre_persona(nom):
                kk = (p[0], p[-1])
                if kk in clave: uf.u(k, clave[kk])
                else: clave[kk] = k
    # 2b · un nombre completo contenido en otro («Sonia Gallardo» ⊂ «Sonia Gallardo Luna»), con el mismo nombre de pila
    llenos = [(k, set(partes(limpio(nom, ruido))), partes(limpio(nom, ruido))[0]) for k, n in nodos.items() if not n.get("generico")
              for nom in n["nombres"] if es_nombre_persona(nom) and len(partes(limpio(nom, ruido))) >= 2]
    for k1, s1, p1 in llenos:
        for k2, s2, p2 in llenos:
            if k1 != k2 and p1 == p2 and s1 < s2:
                uf.u(k1, k2)

    # 3 · nombre de pila suelto («Henar» en el móvil, en el portal y en henar@): se juntan los sueltos con el mismo nombre
    #     y van a la ÚNICA persona del cliente con ese nombre y apellido; si hay dos o más, duda (no se adivina).
    dudas, uniones_pila = list(dudas_tel), []
    sueltos = {}
    for k, n in nodos.items():
        if n.get("generico") or any(len(partes(limpio(x, ruido))) >= 2 for x in n["nombres"] if es_nombre_persona(x)):
            continue
        pila = {partes(x)[0] for x in n["nombres"] if partes(x) and es_nombre_persona(x)}
        if len(pila) == 1:
            sueltos.setdefault(pila.pop(), []).append(k)
    for pila, ks in sueltos.items():
        cand = {uf.f(j) for j, m in nodos.items() if not m.get("generico") and j not in ks
                and any(len(partes(limpio(x, ruido))) >= 2 and partes(limpio(x, ruido))[0] == pila for x in m["nombres"] if es_nombre_persona(x))}
        if len(cand) > 1:
            dudas.append({"tipo": "nombre de pila con varias personas", "nombres": [pila.capitalize()] + sorted({bonito(limpio(x, ruido)) for j, m in nodos.items() if uf.f(j) in cand for x in m["nombres"] if len(partes(limpio(x, ruido))) >= 2})[:6],
                          "correos": [nodos[k]["correo"] for k in ks if nodos[k].get("correo")]})
            continue
        for k in ks[1:]:
            uf.u(k, ks[0])
        if cand:
            uf.u(ks[0], cand.pop())
        if len(ks) > 1 or cand is not None:
            uniones_pila.append(f"«{pila.capitalize()}»: {len(ks)} apariciones sueltas unidas" + (" a la única persona con ese nombre y apellido" if len(ks) else ""))

    # ---- construir personas ----
    por_grupo = {}
    for k in nodos:
        por_grupo.setdefault(uf.f(k), []).append(k)
    personas = []
    tel_dudosos = []     # números que no cuadran con la regla: no se guardan; generar_ficha los pasa a data/telefonos/dudosos.json
    for g, ks in por_grupo.items():
        ns = [nodos[k] for k in ks]
        generico = (all(n.get("generico") for n in ns if n["tipo"] == "correo") and any(n["tipo"] == "correo" for n in ns)
                    and not any(n["tipo"] == "movil" and n["nombres"] and es_nombre_persona(n["nombres"][0]) for n in ns)
                    and not any(n["tipo"] == "portal" and n["nombres"] and es_nombre_persona(n["nombres"][0]) and not re.search(r"(?i)general", (n.get("rol") or "") + n["nombres"][0]) for n in ns))
        # nombres por prioridad y por uso
        cuenta = Counter()
        prio = []
        for n in ns:
            for nom in n["nombres"]:
                if not nom or not es_nombre_persona(nom) and not generico:
                    continue
                cuenta[nom.strip()] += (n.get("dato", {}).get("veces", 0) or 1)
        for n in sorted(ns, key=lambda n: {"portal": 0, "movil": 2, "correo": 3}[n["tipo"]]):
            for nom in n["nombres"]:
                if nom and (generico or es_nombre_persona(nom)):
                    prio.append(nom.strip())
        e_crm = [crm.get(n.get("correo"), {}).get("nombres", []) for n in ns if n.get("correo")]
        firmas = [desk.get(n.get("correo"), {}).get("firma", {}).get("nombre_firma") for n in ns if n.get("correo")]
        firmas = [f for f in firmas if f and len(partes(f)) >= 2]
        limpios = [limpio(x, ruido) for x in prio]
        completos = [x for x in limpios if len(partes(x)) >= 2]
        # elegido: como firma él mismo > portal > Zoho CRM > el más usado con nombre y apellido > el primero
        forz = next((n["forzado"] for n in ns if n.get("forzado")), None)
        elegido = forz or (firmas[0] if firmas else None)
        if not elegido:
            for n in ns:
                if n["tipo"] == "portal" and n["nombres"] and es_nombre_persona(n["nombres"][0]) and len(partes(limpio(n["nombres"][0], ruido))) >= 2:
                    elegido = limpio(n["nombres"][0], ruido); break
        if not elegido:
            for lst in e_crm:
                for x in lst:
                    if len(partes(limpio(x, ruido))) >= 2: elegido = limpio(x, ruido); break
                if elegido: break
        if not elegido and completos:
            elegido = max(completos, key=lambda x: (sum(cuenta.get(o, 0) for o in prio if limpio(o, ruido) == x), len(x)))
        if elegido and not firmas and not forz:
            base = set(partes(elegido))
            mas = [x for x in completos if base < set(partes(x)) and partes(x)[0] == partes(elegido)[0]]
            if mas:
                elegido = max(mas, key=len)
        if not elegido:
            elegido = (limpios[0] if limpios and limpios[0] else None) or next((n["nombres"][0] for n in ns if n["tipo"] == "portal" and n["nombres"]), None) \
                or next((n["correo"] for n in ns if n.get("correo")), "Sin nombre")
        elegido = bonito(elegido)
        # misma grafía con tildes y mayúsculas bien puestas si alguna fuente la trae («Jose Miguel» → «José Miguel»)
        iguales = [bonito(limpio(x, ruido)) for x in prio if norm(limpio(x, ruido)) == norm(elegido)]
        if iguales and not forz:
            elegido = max(iguales + [elegido], key=lambda x: (sum(1 for ch in x if ord(ch) > 127), not x.isupper(), sum(1 for w in x.split() if w[:1].isupper())))
        sin_nombre = False
        if generico:
            buzon = next((n["correo"] for n in ns if n.get("correo")), "")
            elegido = f"Buzón {buzon.split('@')[0]}@"
        elif "@" in elegido or (" " not in elegido.strip() and norm(elegido) in {n["correo"].split("@")[0] for n in ns if n.get("correo")}
                                 and not any(n["tipo"] in ("portal", "movil") and n["nombres"] and norm(n["nombres"][0]) == norm(elegido) for n in ns)):
            sin_nombre = True
            loc = next((n["correo"] for n in ns if n.get("correo")), "").split("@")[0]
            elegido = f"Sin nombre ({loc}@)"
        # ¿nombres de pila que no casan para el mismo apellido (Gert Jan / Gerben)? → duda, no se adivina
        pilas = {}
        for x in completos + [elegido]:
            p = partes(x)
            if len(p) >= 2:
                pilas.setdefault(p[-1], set()).add(p[0])
        apodos = {norm(m) for x in prio for m in re.findall(r"\(([^)]+)\)", x)}
        conflicto = [] if forz else [ap for ap, st in pilas.items() if len(st) > 1 and not mismo_pila(st, apodos)]
        prio_otros = [x for n in ns for x in n.get("otros", [])]
        tambien = sorted({bonito(x) for x in prio + prio_otros if norm(limpio(x, ruido)) != norm(elegido) and norm(x) != norm(elegido)
                          and not set(partes(x)) <= ruido and (generico or es_nombre_persona(x)) and "@" not in x}, key=lambda x: -cuenta.get(x, 0))
        if conflicto and not generico:
            dudas.append({"tipo": "dos nombres para la misma persona", "nombres": [elegido] + [t for t in tambien if len(partes(limpio(t, ruido))) >= 2][:5],
                          "correos": [n["correo"] for n in ns if n.get("correo")]})
        # ¿el correo personal no casa con el apellido elegido (cacevedo@ y «Carolina Núñez»)? → duda
        if not generico and not sin_nombre and not forz and len(partes(elegido)) >= 2:
            ap = [w for w in partes(elegido)[1:] if len(w) >= 4]
            for n in ns:
                if n.get("correo") and not n.get("generico") and n["correo"].split("@")[1] in [d.lower() for d in ag.get("dominios", [])]:
                    loc = re.sub(r"[^a-z]", "", n["correo"].split("@")[0])
                    if len(loc) >= 5 and ap and not any(w in loc for w in ap) and not any(w in loc for w in partes(elegido)[:1] if len(w) >= 4):
                        dudas.append({"tipo": "el correo no casa con el apellido", "nombres": [elegido] + tambien[:3], "correos": [n["correo"]]})
                        conflicto = conflicto or ["correo"]
                        break
        # teléfonos
        tels = {}
        nucleos_doc = {tel_norm(m["tel"])[-9:] for m in ag["moviles"]}
        mal_guardados = []
        for n in ns:
            for t in n.get("tels", []):
                dig = re.sub(r"\D", "", t)
                if tel_norm(t) not in {tel_norm(m["tel"]) for m in ag["moviles"]} and any(nd in dig for nd in nucleos_doc):
                    mal_guardados.append(t); continue        # el mismo móvil mal guardado en el portal (p. ej. «+6559973830»)
                rt = _limpiar_tel(t)
                if rt["motivo"] != "ok":
                    tel_dudosos.append({"valor": t, "aviso": rt["aviso"], "donde": f"Portal de clientes ({n.get('src') or 'portal'})", "quien": elegido}); continue
                tels.setdefault(tel_norm(t), {"tel": rt["telefono"], **({"extension": rt["extension"]} if rt["extension"] else {}), "fuente": f"Portal de clientes ({n.get('src') or 'portal'})", "whatsapp": None,
                                              "compartido": (compartidos.get(tel_norm(t)) or {}).get("nota")})
            if n.get("tel"):
                wa = WA.search(n.get("fuente") or "")
                rt = _limpiar_tel(n["tel"])
                if rt["motivo"] != "ok":
                    tel_dudosos.append({"valor": n["tel"], "aviso": rt["aviso"], "donde": f"Documento de móviles ({n.get('fuente') or 'documento'})", "quien": elegido})
                    continue
                tels[tel_norm(n["tel"])] = {"tel": rt["telefono"], **({"extension": rt["extension"]} if rt["extension"] else {}), "fuente": n.get("fuente") or "documento de móviles", "whatsapp": wa.group(1) if wa else None,
                                            "etiqueta": n["nombres"][0] if n["nombres"] else None,
                                            "compartido": (compartidos.get(tel_norm(n["tel"])) or {}).get("nota"),
                                            "en_documento": True}
        # correos
        mails = {}
        for n in ns:
            for e in n.get("mails", []):
                mails.setdefault(e, {"correo": e, "veces": 0, "copia": 0, "donde": ["Portal"], "ultimo": None, "en_documento": False})
            if n.get("correo"):
                d = n["dato"]; dk = desk.get(n["correo"], {})
                mails[n["correo"]] = {"correo": n["correo"], "veces": d["veces"], "copia": d["copia"], "donde": d["donde"],
                                      "ultimo": dk.get("ultimo_suyo"), "ticket": dk.get("ticket"), "en_documento": True}
        mails = sorted(mails.values(), key=lambda m: -m["veces"])
        # roles con su fuente (nunca inventados)
        roles_l = []
        for n in ns:
            if n["tipo"] == "portal" and n.get("rol"):
                roles_l.append({"texto": n["rol"], "fuente": f"Portal de clientes ({n.get('src') or 'portal'})"})
            if n["tipo"] == "movil" and n.get("detalle"):
                roles_l.append({"texto": n["detalle"], "fuente": f"Documento de móviles ({n.get('fuente')})"})
            if n.get("correo"):
                e = n["correo"]
                if crm.get(e, {}).get("cargo"):
                    roles_l.append({"texto": crm[e]["cargo"], "fuente": crm[e]["fuente"]})
                if desk.get(e, {}).get("title"):
                    roles_l.append({"texto": desk[e]["title"], "fuente": "Zoho Desk (cargo del contacto)"})
                f = desk.get(e, {}).get("firma")
                cargo_firma = (f or {}).get("lineas", [""])[0].strip(" ,.") if f else ""
                if cargo_firma and not re.search(r"(?i)(s\.a\.|s\.l\.|grupo|rupo de|oficinas|aenor|" + re.escape(norm(nombre_cliente).split()[0] if norm(nombre_cliente) else "zzz") + ")", norm(cargo_firma) + " " + cargo_firma):
                    roles_l.append({"texto": cargo_firma, "fuente": f"Firma de su correo en Desk ({desk[e].get('ticket') or 'ticket'}, {desk[e].get('ultimo_suyo')})"})
        for t in tels.values():
            if t.get("whatsapp"):
                roles_l.append({"texto": f"En WhatsApp: «{t['whatsapp']}»", "fuente": "WhatsApp Web (nombre del chat)", "solo_nombre": True})
        if generico:
            roles_l.insert(0, {"texto": "Buzón general", "fuente": "dirección genérica del despacho"})
        rol_txt = next((r["texto"] for r in roles_l if not r.get("solo_nombre")), None)
        decisor = next((r for r in roles_l if CARGO_DECISOR.search(r["texto"]) and not re.search(r"(?i)extern", r["texto"]) and not r.get("solo_nombre")), None)
        dia = next((r for r in roles_l if DIA_A_DIA.search(r["texto"])), None)
        nota = "; ".join(n["nota"] for n in ns if n.get("nota"))
        doms = [d.lower() for d in ag.get("dominios", [])]
        en_doc = any(n["tipo"] in ("movil", "correo") for n in ns)
        externo = (not en_doc) and (bool(re.search(r"(?i)extern|proveedor|hosting|canal denuncias", rol_txt or ""))
                                     or any(doms and m.split("@")[1] not in doms for n in ns for m in n.get("mails", [])))
        personas.append({
            "id": g, "nombre": elegido, "sin_nombre": sin_nombre, "externo": externo, "solo_portal": not en_doc, "nombre_por_confirmar": bool(conflicto) and not generico, "tambien": tambien[:8],
            "generico": generico, "rol": rol_txt or ("Buzón general" if generico else None), "roles": roles_l,
            "decisor": {"por": f"{decisor['texto']} · {decisor['fuente']}"} if decisor else None,
            "dia_a_dia": {"por": f"{dia['texto']} · {dia['fuente']}"} if dia else None,
            "telefonos": list(tels.values()), "correos": mails, "nota": nota or None,
            "veces": sum(m["veces"] for m in mails), "copia": sum(m["copia"] for m in mails),
            "ultimo": max([m["ultimo"] for m in mails if m.get("ultimo")], default=None),
            "fuentes": sorted({x for m in mails for x in m["donde"]} | ({"Portal"} if any(n["tipo"] == "portal" for n in ns) else set())
                              | ({"Documento de móviles"} if any(n["tipo"] == "movil" for n in ns) else set())),
            "orden_portal": min([n["orden"] for n in ns if n["tipo"] == "portal"], default=99),
        })
    # ¿Dos fichas que parecen la misma persona escrita distinto («Gema» / «Gemma Gregorio»)? No se unen: van a dudas.
    gente_n = [p for p in personas if not p["generico"] and not p["sin_nombre"] and len(partes(p["nombre"])) >= 2]
    vistos = set()
    for i, a in enumerate(gente_n):
        for b in gente_n[i + 1:]:
            pa, pb = partes(a["nombre"]), partes(b["nombre"])
            if pa[-1] == pb[-1] and pa[0] != pb[0] and mismo_pila({pa[0], pb[0]}, set()) and (a["nombre"], b["nombre"]) not in vistos:
                vistos.add((a["nombre"], b["nombre"]))
                dudas.append({"tipo": "¿la misma persona escrita de dos formas?", "nombres": [a["nombre"], b["nombre"]],
                              "correos": [m["correo"] for m in a["correos"] + b["correos"]]})
    # «También aparece como» nunca enseña el nombre de OTRA persona del cliente (Fitec: Cristina ≠ Tino Antúnez)
    nombres_cli = {norm(p["nombre"]) for p in personas}
    for p in personas:
        p["tambien"] = [t for t in p["tambien"] if norm(t) not in nombres_cli - {norm(p["nombre"])}]
    # principal = la persona (no buzón) que más interactúa; día a día por uso si ninguna fuente lo dice
    gente = [p for p in personas if not p["generico"] and not p["externo"]]
    if gente:
        top = max(gente, key=lambda p: (p["veces"], len(p["telefonos"]), -p["orden_portal"]))
        if top["veces"] > 0 or top["telefonos"]:
            top["principal"] = True
            if not any(p["dia_a_dia"] for p in gente) and top["veces"] >= 5:
                top["dia_a_dia"] = {"por": f"por uso: {top['veces']} apariciones en Desk, GHL, CRM y portal (sin fuente que lo diga)"}
    personas.sort(key=lambda p: (p["externo"], p["generico"], not p.get("principal"), -(p["veces"]), -len(p["telefonos"]), p["orden_portal"]))
    # Las notas del documento usan el nombre ya corregido por Tomás («Solo correo (Gerben Geerse)» → Gert Jan Geerse)
    notas = list(ag.get("notas", []))
    forzadas = {nodos[k]["forzado"] for k in nodos if nodos[k].get("forzado")}
    for p in personas:
        if p["nombre"] in forzadas:
            for t in sorted(p["tambien"], key=len, reverse=True):
                limpio_t = re.sub(r"\s*\(.*?\)", "", t).strip()
                if len(partes(limpio_t)) >= 2:
                    notas = [x.replace(limpio_t, p["nombre"]) for x in notas]
    notas = MANUAL.get("notas", {}).get(cliente_id) or notas
    ag = {**ag, "notas": notas}
    return {"personas": personas, "dudas": dudas, "uniones_pila": uniones_pila,
            "sin_movil": not ag["moviles"], "fijos": _fijos(ag.get("fijos", []), tel_dudosos), "telefonos_dudosos": tel_dudosos, "notas": ag.get("notas", []),
            "dominios": ag.get("dominios", []), "account_documento": ag.get("account")}


def _fijos(fijos, dudosos):
    """Fijos del documento con la regla común; los que no cuadran van a dudosos (no se guardan)."""
    ok = []
    for f in fijos or []:
        r = _limpiar_tel(f)
        if r["motivo"] == "ok":
            ok.append(r["telefono"])          # la extensión (si la hay) no va dentro del número; el fijo se marca sin ella
        elif r["motivo"] == "dudoso":
            dudosos.append({"valor": f, "aviso": r["aviso"], "donde": "Documento de móviles (fijo)", "quien": None})
    return ok


def bonito(n):
    n = re.sub(r"\s+", " ", (n or "").strip().strip("'\""))
    if n.islower() or n.isupper():
        n = " ".join(w.capitalize() if len(w) > 2 or i == 0 else w for i, w in enumerate(n.lower().split()))
    return n


PARES = [{"francesc", "francisco"}, {"joan", "juan"}, {"josep", "jose"}, {"jordi", "jorge"}, {"esperanca", "esperanza"}, {"miquel", "miguel"},
         {"xavier", "javier"}, {"pere", "pedro"}, {"antoni", "antonio"}, {"lluis", "luis"}, {"marc", "marcos"}]


def limpio(n, ruido):
    """Quita del nombre el despacho («AyG - David Gil», «Xterna Miquel Sanchez», «Luis Carlos - Avantik Asesores»)
    y lo que va entre paréntesis. El apellido que coincide con el despacho (Bonet en Bonet Asesores) se respeta."""
    n = re.sub(r"\(.*?\)", " ", n or "")
    trozos = [t.strip() for t in re.split(r"\s[-–|·]\s|\.-|\|\|", n) if t.strip()]
    trozos = [t for t in trozos if not set(partes(t)) <= ruido] or trozos
    pal = " ".join(trozos).split()
    cli = [x for x in CLIENTE_TOK]
    if cli and len(pal) > len(cli) and [norm(w) for w in pal[-len(cli):]] == cli:
        pal = pal[:-len(cli)]
    if cli and len(pal) > len(cli) and [norm(w) for w in pal[:len(cli)]] == cli:
        pal = pal[len(cli):]
    while len(pal) > 2 and norm(pal[0]) in ruido:
        pal = pal[1:]
    while len(pal) > 2 and norm(pal[-1]) in GENERICAS_FIN:
        pal = pal[:-1]
    return " ".join(pal).strip()


CLIENTE_TOK = []   # palabras del nombre del cliente (las pone construir())
GENERICAS_FIN = {"asesores", "asesoria", "consulting", "consultores", "economistes", "economistas", "abogados", "spain", "advisory", "gestoria", "fuster", "abogado"}


def mismo_pila(st, apodos):
    """¿Todos los nombres de pila son la misma persona escrita distinto (tilde, catalán/castellano, inicial, apodo)?"""
    from difflib import SequenceMatcher
    st = list(st)
    for i in range(len(st)):
        for j in range(i + 1, len(st)):
            a, b = st[i], st[j]
            if a.startswith(b) or b.startswith(a) or {a, b} in PARES or a in apodos or b in apodos:
                continue
            if SequenceMatcher(None, a, b).ratio() >= 0.75:
                continue
            return False
    return True

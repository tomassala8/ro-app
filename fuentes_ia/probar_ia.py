#!/usr/bin/env python3
"""fuentes_ia/probar_ia.py · N3 · pruebas de la IA contra servir.py en marcha.

  RO_DB=<copia> python3 servir.py --puerto 8783 &      (copia de local.db para no ensuciar el rastro)
  python3 fuentes_ia/probar_ia.py --puerto 8783 --db <copia>

Comprueba: permisos (Lucía no obtiene borradores ni copiloto de clientes ajenos; producción y setters, nada),
«ver como» (solo lectura, mínimo de las dos personas), rastro (cada petición y cada denegación), el navegador no
puede fingir rastro de la IA, POST sin cabecera de la app rechazado, y ninguna respuesta lleva correos,
teléfonos ni credenciales.
"""
import json
import sqlite3
from datetime import datetime
import sys
import urllib.error
import urllib.request
from pathlib import Path

APP = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(APP))
import escaner_secretos as ESC  # noqa: E402

PUERTO = int(sys.argv[sys.argv.index("--puerto") + 1]) if "--puerto" in sys.argv else 8770
DB = sys.argv[sys.argv.index("--db") + 1] if "--db" in sys.argv else str(APP / "local.db")
BASE = f"http://127.0.0.1:{PUERTO}"
FALLOS, BIEN = [], []


def pedir(ruta, yo, cuerpo=None, como=None, app=True):
    h = {"X-RO-Yo": yo, "Content-Type": "application/json"}
    if app:
        h["X-RO-App"] = "1"
    if como:
        h["X-RO-Como"] = como
    req = urllib.request.Request(BASE + ruta, data=json.dumps(cuerpo).encode() if cuerpo is not None else None,
                                 headers=h, method="POST" if cuerpo is not None else "GET")
    try:
        r = urllib.request.urlopen(req, timeout=30)
        return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def ok(cond, texto):
    (BIEN if cond else FALLOS).append(texto)
    print(("✓ " if cond else "✗ ") + texto)


def limpio(obj):
    t = json.dumps(obj, ensure_ascii=False)
    for nombre, pat in ESC.PATRONES:
        if pat.search(t):
            return nombre
    return None


verdad = {c["cliente_id"]: c for c in json.loads((APP / "data/verdad/clientes.json").read_text())["clientes"]}
cartera_lucia = {cid for cid, c in verdad.items() if c.get("account") == "lucia"}

# 1. Tomás lo ve todo. Ronda 10 (E0): los borradores se precalcularon a las 18:00 sobre 40 correos; la Bandeja se rehace
# sola y los correos ya contestados o cerrados salen de ella (2-oct 18:53: 6 de los 40). Un borrador de un correo que ya no
# está en la Bandeja NO se sirve (ia.puede_borrador: «Ese correo no está en la Bandeja»), así que se compara con los VIGENTES.
_pre_b = json.loads((APP / "data/ia/_privado/borradores.json").read_text()).get("borradores", {})
_bdj = json.loads((APP / "data/bandeja/bandeja.json").read_text())
_ids_bdj = {str(f.get(k)) for f in _bdj.get("correos", []) + _bdj.get("triaje", []) for k in ("id", "numero") if f.get(k) is not None}
vigentes = [n for n in _pre_b if str(n) in _ids_bdj]
n_cop = len(json.loads((APP / "data/ia/_privado/copiloto.json").read_text()).get("clientes", {}))
s, L = pedir("/api/ia/lista", "tomas")
ok(s == 200 and len(L["borradores"]) == len(vigentes) and len(L["copiloto"]) == n_cop,
   f"Tomás: {len(vigentes)} borradores vigentes (de {len(_pre_b)} precalculados; {len(_pre_b) - len(vigentes)} ya no están en la Bandeja) "
   f"y {n_cop} copilotos (tiene {len(L.get('borradores', []))} y {len(L.get('copiloto', []))})")
ok({b["ticket"] for b in L.get("borradores", [])} == set(vigentes), "Tomás recibe exactamente los borradores de correos que siguen en la Bandeja")
ok(not L["estado"]["conectada"], "Sin clave: la IA dice «sin conectar» con su motivo")

# 2. Lucía solo lo suyo
s, LL = pedir("/api/ia/lista", "lucia")
ajenos_b = [b["cliente_id"] for b in LL["borradores"] if b["cliente_id"] not in cartera_lucia]
ajenos_c = [c["cliente_id"] for c in LL["copiloto"] if c["cliente_id"] not in cartera_lucia]
ok(s == 200 and LL["borradores"] and not ajenos_b, f"Lucía: {len(LL['borradores'])} borradores, todos de su cartera")
ok(LL["copiloto"] and not ajenos_c, f"Lucía: {len(LL['copiloto'])} copilotos, todos de su cartera")
ajeno = next(b for b in L["borradores"] if b["cliente_id"] not in cartera_lucia)
s, r = pedir("/api/ia/borrador", "lucia", {"ticket": ajeno["ticket"]})
ok(s == 403, f"Lucía pide el borrador de {ajeno['ticket']} ({ajeno['cliente_id']}): 403")
s, r = pedir("/api/ia/copiloto", "lucia", {"cliente_id": "musashi-consultores"})
ok(s == 403, "Lucía pide el copiloto de Musashi (de Natalia): 403")
suyo = LL["borradores"][0]
s, r = pedir("/api/ia/borrador", "lucia", {"ticket": suyo["ticket"]})
ok(s == 200 and r.get("ok") and r.get("origen") == "precalculado" and r.get("aviso"), f"Lucía obtiene el borrador de {suyo['ticket']} (precalculado, con aviso)")
ok(r.get("firma", {}).get("id") == "lucia", "El borrador sale con la firma de quien responde")
fuga = limpio(r)
ok(not fuga, f"El borrador no lleva correos, teléfonos ni claves ({fuga or 'limpio'})")
s, r = pedir("/api/ia/copiloto", "lucia", {"cliente_id": "gac"})
ok(s == 200 and len(r.get("acciones", [])) == 3 and all(a.get("prueba") for a in r["acciones"]), "Lucía: copiloto de GAC con 3 acciones y su prueba")
ok(not limpio(r), "El copiloto no lleva correos, teléfonos ni claves")
s, r = pedir("/api/ia/borrador", "lucia", {"ticket": "RO-0000"})
ok(s == 403, "Un ticket que no está en la Bandeja: 403")

# 3. Quien no debe
for yo in ("camilo", "setter_ana", "sofia"):
    s, _ = pedir("/api/ia/lista", yo)
    s2, _ = pedir("/api/ia/borrador", yo, {"ticket": suyo["ticket"]})
    ok(s == 403 and s2 == 403, f"{yo}: sin acceso a la IA (lista {s}, borrador {s2})")

# 4. «Ver como»
s, r = pedir("/api/ia/borrador", "tomas", {"ticket": ajeno["ticket"]}, como="lucia")
ok(s == 403, "Tomás «como Lucía» no ve el borrador de un cliente ajeno a Lucía")
s, r = pedir("/api/ia/borrador", "tomas", {"ticket": suyo["ticket"], "nuevo": True}, como="lucia")
ok(s == 200 and r.get("origen") == "precalculado", "«Ver como» sirve lo ya generado y no genera nada nuevo")

# 5. Seguridad de las peticiones
s, _ = pedir("/api/ia/borrador", "lucia", {"ticket": suyo["ticket"]}, app=False)
ok(s == 403, "POST sin la cabecera de la app: 403")
s, _ = pedir("/api/rastro", "lucia", {"accion": "ia_borrador", "objeto": "RO-1"})
ok(s == 403, "El navegador no puede apuntar «ia_borrador» en el rastro (solo el servidor)")
s, _ = pedir("/api/rastro", "lucia", {"accion": "ia_usar", "modulo": "asistente-ia", "objeto": suyo["ticket"]})
ok(s == 200, "«Usar este borrador» queda en el rastro (ia_usar)")

# 6. Rastro
con = sqlite3.connect(DB)
filas = con.execute("SELECT quien, accion, clave, como FROM registro WHERE coleccion='ia' ORDER BY id DESC LIMIT 200").fetchall()
ok(any(f[0] == "lucia" and f[1] == "ia_borrador" for f in filas), "Rastro: «ia_borrador» de Lucía")
ok(any(f[0] == "lucia" and f[1] == "ia_denegado" for f in filas), "Rastro: «ia_denegado» de Lucía (cliente ajeno)")
ok(any(f[0] == "tomas" and f[3] == "lucia" for f in filas), "Rastro: lo leído en «ver como» apunta a las dos personas")

# 7. N12 · «Qué haría yo hoy aquí» por pantalla y persona (reglas, sin clave) y «Qué hacer» por fuente
import re  # noqa: E402
PANTALLAS = ["mi-dia", "en-rojo", "bandeja", "agenda", "ficha", "clientes-nuevos", "informes-mensuales", "incidencias", "captacion",
             "salud-crm", "seo-web", "redes", "produccion", "horas", "reuniones", "personas", "setters", "ventas-ro", "prospeccion",
             "dinero-cliente", "finanzas", "panel-direccion", "decisiones", "ajustes", "asistente-ia", "alertas"]
RE_SENSIBLE = re.compile(r"(?i)(sueldo|salario|n[oó]mina|(contrase[ñn]a|password|usuario|token|clave)\s*[:=]\s*\S|api[_ ]?key\s*[:=])")
personas_act = [x for x in json.loads((APP / "data/personas.json").read_text()) if x.get("estado", "activo") == "activo"]
equipo_de = {cid: {y.get("persona_id") for ys in (c.get("equipo") or {}).values() for y in ys} | {c.get("account")} for cid, c in verdad.items()}
import os  # noqa: E402
os.environ["RO_DB"] = DB
import servir as SV  # noqa: E402  (en este proceso, solo para saber qué pantallas ve cada uno: así no se llena el rastro de denegados)
SV.E.cargar()
total, fugas, sens, sin_pant = 0, [], [], []
for per in personas_act:
    yo = per["id"]
    for pant in PANTALLAS:
        if not SV.ve_alguno(SV.E.persona(yo), [pant]):
            continue
        s, r = pedir(f"/api/ia/consejo?pantalla={pant}", yo)
        if s == 403:
            continue
        if s != 200:
            sin_pant.append(f"{yo}/{pant}:{s}")
            continue
        cs = r.get("consejos", [])
        total += len(cs)
        if len(cs) > 3:
            fugas.append(f"{yo}/{pant}: {len(cs)} consejos")
        if limpio(r):
            fugas.append(f"{yo}/{pant}: {limpio(r)}")
        t = json.dumps(cs, ensure_ascii=False)
        if RE_SENSIBLE.search(t):
            sens.append(f"{yo}/{pant}: {RE_SENSIBLE.search(t).group(0)}")
        if "account" in per.get("puestos", []) and set(per["puestos"]) <= {"account"}:
            for c in cs:
                if c.get("cliente_id") and yo not in equipo_de.get(c["cliente_id"], set()):
                    fugas.append(f"{yo}/{pant}: cliente ajeno {c['cliente_id']}")
ok(total > 0 and not sin_pant, f"Consejos: {total} servidos a {len(personas_act)} personas en sus pantallas (errores: {sin_pant[:3] or 'ninguno'})")
ok(not fugas, f"Consejos sin fugas: ni más de 3, ni correos o teléfonos, ni clientes ajenos de un account ({fugas[:3] or 'limpio'})")
ok(not sens, f"Consejos sin sueldos, contraseñas ni llaves ({sens[:3] or 'limpio'})")

s, r = pedir("/api/ia/consejo?pantalla=mi-dia", "lucia")
ok(s == 200 and r.get("consejos") and r.get("origen") == "reglas" and not r["ia"]["conectada"],
   f"Sin clave salen las reglas: Lucía en Mi día, {len(r.get('consejos', []))} consejos, origen «{r.get('origen')}»")
ok(all(c.get("que") and c.get("porque") and c.get("fuente", {}).get("texto") and c.get("quien") and c.get("cuando") for c in r.get("consejos", [])),
   "Cada consejo trae qué, porqué, fuente, quién y cuándo")
ok(all(not c.get("fuente", {}).get("url") or c["fuente"]["url"].startswith("https://") for c in r.get("consejos", [])), "Los «Ver fuente ↗» son enlaces https")
ok(any(c.get("accion") for c in r.get("consejos", [])), "Hay botón de acción simulada («Lo tengo») donde la alerta es suya")
tabla = r.get("que_hacer") or []
ok(tabla and all(t.get("paso") and t.get("quien") for t in tabla) and not limpio(tabla) and not any(re.search(r"\.py\b|~/|llavero|GHL_PIT", t["paso"]) for t in tabla),
   f"«Qué hacer» por fuente: {len(tabla)} fuentes con paso y dueño, sin rutas ni nombres de llaves")
s, r = pedir("/api/ia/consejo?pantalla=ficha&cliente=musashi-consultores", "lucia")
ok(s == 200 and not r.get("consejos"), "Lucía en la ficha de Musashi (ajeno): ningún consejo")
s, r = pedir("/api/ia/consejo?pantalla=ficha&cliente=gac", "lucia")
ok(s == 200 and r.get("consejos") and all(c.get("cliente_id") == "gac" for c in r["consejos"]), "Lucía en la ficha de GAC: solo consejos de GAC")
s, r = pedir("/api/ia/consejo?pantalla=finanzas", "lucia")
ok(s == 403, "Lucía pide consejos de Finanzas (no es de su puesto): 403")
s, r = pedir("/api/ia/consejo?pantalla=setters", "setter_ana")
txt = json.dumps(r, ensure_ascii=False)
ok(s == 200 and r.get("consejos") and "Javier" not in txt and "javier" not in json.dumps(r.get("consejos")),
   f"Ana (setter): {len(r.get('consejos', []))} consejos solo con sus recuentos (nada del otro setter, ningún lead)")
s, r = pedir("/api/ia/consejo?pantalla=mi-dia", "tomas", como="lucia")
s2, r2 = pedir("/api/ia/consejo?pantalla=mi-dia", "lucia")
ids_l = {c["id"] for c in r2.get("consejos", [])}
ok(s == 200 and r.get("solo_lectura") and not any(c.get("personal") for c in r.get("consejos", [])),
   "«Ver como» Lucía: lo que vería ella, sin lo personal (sus horas) y en solo lectura")
ok(all(c.get("cliente_id") in (None,) or "lucia" in equipo_de.get(c["cliente_id"], set()) for c in r.get("consejos", [])),
   "«Ver como» Lucía: ningún cliente fuera de su cartera")
s, r = pedir("/api/ia/consejo", "lucia", {"pantalla": "mi-dia"})
ok(s == 200 and r.get("origen") == "reglas", "POST sin clave: se quedan las reglas (no se inventa nada)")
s, _ = pedir("/api/ia/consejo", "lucia", {"pantalla": "mi-dia"}, app=False)
ok(s == 403, "POST de consejo sin la cabecera de la app: 403")
s, _ = pedir("/api/rastro", "lucia", {"accion": "ia_consejo", "objeto": "mi-dia"})
_f = sqlite3.connect(DB).execute("SELECT accion FROM registro WHERE quien='lucia' AND clave='mi-dia' AND accion LIKE '%ia_consejo' ORDER BY id DESC LIMIT 1").fetchone()
# Ronda 14 (E0): desde que «ia_consejo» está en rastro_solo_servidor, el servidor lo rechaza (403) y no escribe nada; vale
# igual que dejarlo como «nav:ia_consejo». Lo que nunca puede pasar es una fila «ia_consejo» escrita por el navegador.
ok((s == 403 and not _f) or (_f and _f[0] == "nav:ia_consejo"),
   f"El navegador no puede fingir «ia_consejo»: {s} y queda como «{_f[0] if _f else 'nada'}» (solo el servidor apunta el de verdad)")

# 7b. V2-B (3-oct) · «Qué haría yo hoy aquí» = lo que un buen jefe le diría A ESA persona en ESA pantalla
# Por persona: el primer consejo de Mi día es de su puesto y su dueño es quien lo lee (o, si es jefa, alguien de su equipo
# con «Pide a X…» y botón de aviso). Dirección nunca recibe tareas de Mili ni de Sofía. Las horas nunca van primero.
PRIMERO = {   # persona → tipos que pueden abrir su Mi día (lo que manda en su puesto)
    "lucia": {"acc_critico", "critico_cliente", "acc_correos"}, "candela": {"acc_critico", "critico_cliente", "acc_correos"},
    "agustina": {"alta_fuera_plazo"}, "tomas": {"dir_decision"}, "constanza": {"visto_critico", "acc_critico", "critico_cliente"},
    "camilo": {"prod_devuelta", "prod_vencida", "prod_hoy"}, "eulimar": {"outreach_clasificar", "outreach_positiva"},
    "yessica": {"outreach_clasificar", "outreach_positiva", "crm_sin_tocar", "crm_citas_sin_estado", "crm_whatsapp", "fuga_integracion"},
    "valeria": {"pub_critico", "pub_atencion", "fuga_integracion"}, "jeronimo": {"seo_rojo", "seo_ambar", "web_caida", "web_spam", "web_certificado"},
}
JEFAS = {"jefa_publicidad": {"trafficker"}, "jefa_crm": {"especialista_ghl", "outreach"}, "jefa_seo": {"seo", "ficha_google", "web"}}
per_por_id = {x["id"]: x for x in json.loads((APP / "data/personas.json").read_text())}
def _jefa_de(yo, otro):
    a, b = set(per_por_id.get(yo, {}).get("puestos") or []), set(per_por_id.get(otro, {}).get("puestos") or [])
    if b & {"direccion", "operaciones"}:
        return False
    return "operaciones" in a or any(j in a and b & eq for j, eq in JEFAS.items())
for yo, tipos in PRIMERO.items():
    s, r = pedir("/api/ia/consejo?pantalla=mi-dia", yo)
    cs = r.get("consejos") or []
    c0 = cs[0] if cs else {}
    ok(s == 200 and c0.get("tipo") in tipos, f"V2 · {yo}: el primer consejo de Mi día es de su puesto («{c0.get('que', '—')}», {c0.get('tipo')})")
    malos = [c["que"] for c in cs if c.get("dueno") not in (None, yo) and not (c.get("delegado") and _jefa_de(yo, c["dueno"]))]
    ok(not malos, f"V2 · {yo}: ningún consejo de Mi día es de otra persona fuera de su equipo ({malos[:2] or 'limpio'})")
    horas_primero = len(cs) > 1 and cs[0].get("tipo") == "rrhh_no_imputa"
    ok(not horas_primero, f"V2 · {yo}: las horas no abren el consejo")
# Dirección: nunca tareas de Mili o Sofía, ni delegadas
todos_t = []
for pant in ("mi-dia", "finanzas", "panel-direccion", "decisiones", "incidencias", "ficha", "en-rojo"):
    s, r = pedir(f"/api/ia/consejo?pantalla={pant}", "tomas")
    todos_t += r.get("consejos") or []
ok(not [c for c in todos_t if c.get("dueno") in ("mili", "sofia") or c.get("delegado")],
   f"V2 · Tomás: ningún consejo es tarea de Mili o Sofía ni «Pide a…» ({len(todos_t)} revisados)")
# Jefa: lo de su equipo como «Pide a X…» con botón «Avisar a X», y detrás de lo suyo
s, r = pedir("/api/ia/consejo?pantalla=mi-dia", "valeria")
dele = [c for c in r.get("consejos") or [] if c.get("delegado")]
ok(all(c["que"].startswith("Pide a ") and (c.get("accion") or {}).get("tipo") == "avisar" for c in dele),
   f"V2 · Valeria: lo de su equipo dice «Pide a X…» y lleva «Avisar a X» ({[c['que'][:50] for c in dele][:2]})")
s, r = pedir("/api/ia/consejo?pantalla=mi-dia", "lucia")
ok(not [c for c in r.get("consejos") or [] if c.get("delegado") or c.get("dueno") == "mili"], "V2 · Lucía (account, sin equipo): nada delegado ni de Mili")
# Fuera el ruido: el aviso de fuentes no ocupa un consejo (va al sello), salvo dentro del consejo al que afecta
ruido = []
for yo in PRIMERO:
    for pant in ("mi-dia", "captacion", "ficha", "en-rojo", "seo-web", "bandeja", "horas"):
        if not SV.ve_alguno(SV.E.persona(yo), [pant]):
            continue
        s, r = pedir(f"/api/ia/consejo?pantalla={pant}", yo)
        ruido += [f"{yo}/{pant}" for c in r.get("consejos") or [] if c.get("tipo") == "fuente" or str(c.get("que", "")).startswith("Ojo con las cifras")]
ok(not ruido, f"V2 · «Ojo con las cifras de N fuentes» ya no ocupa un consejo ({ruido[:3] or 'ninguno'})")
s, r = pedir("/api/ia/consejo?pantalla=captacion", "valeria")
ok(any(x.get("nombre") for x in r.get("retrasos") or []), f"V2 · El retraso de fuentes va al sello: {[x.get('nombre') for x in r.get('retrasos') or []]}")
s, r = pedir("/api/ia/consejo?pantalla=seo-web", "jeronimo")
seo = [c for c in r.get("consejos") or [] if c.get("tipo") in ("seo_rojo", "seo_ambar")]
ok(not seo or all(c["que"].startswith("Comprueba en Google") for c in seo), "V2 · SE Ranking en duda: el consejo de SEO pasa a «compruébalo en Google antes de tocar nada»")
# Un dueño por conexión (el de Ajustes › Conexiones): una clave que falta o falla la pone Tomás; Agus comprueba
s, r = pedir("/api/ia/consejo?pantalla=captacion", "camilo")
_t = json.dumps([r.get("que_hacer"), r.get("retrasos"), r.get("consejos")], ensure_ascii=False)
ok(s == 200 and "lo conecta Agus" not in _t and ("lo hace Tomás" in _t or not r.get("retrasos")),
   "V2 · Claves: «lo hace Tomás: pegar la clave…; después Agus comprueba», nunca «lo conecta Agus»")
# Nada absurdo: nunca archivar la subcuenta de un alta (Garmande), nunca «crítico» si la verdad única dice otra cosa
absurdos = []
for yo in ("yessica", "gustavo", "tomas", "mili", "candela"):
    for pant, cli in (("ficha", "garmande"), ("salud-crm", None), ("mi-dia", None)):
        q = f"/api/ia/consejo?pantalla={pant}" + (f"&cliente={cli}" if cli else "")
        s, r = pedir(q, yo)
        for c in r.get("consejos") or []:
            v = verdad.get(c.get("cliente_id")) or {}
            if c.get("tipo") == "crm_sin_usar" and (v.get("nuevo") or (v.get("dia_alta") or 999) < 90):
                absurdos.append(f"{yo}: archivar subcuenta de {c.get('cliente')}")
            if "crítico" in c.get("que", "") and c.get("cliente_id") and v.get("gravedad") != "critico":
                absurdos.append(f"{yo}: «crítico» para {c.get('cliente')} ({v.get('gravedad')})")
ok(not absurdos, f"V2 · Nada absurdo ni contra la verdad única ({absurdos[:3] or 'limpio'})")
# Producción, Prospección y Ventas de RO con reglas propias
for yo, pant, tipos in (("camilo", "produccion", {"prod_devuelta", "prod_vencida", "prod_hoy"}), ("eulimar", "prospeccion", {"outreach_clasificar", "outreach_positiva"}),
                        ("tomas", "ventas-ro", {"ventas_contrato", "ventas_sin_marcar", "ventas_propuesta"})):
    s, r = pedir(f"/api/ia/consejo?pantalla={pant}", yo)
    cs = r.get("consejos") or []
    ok(cs and cs[0].get("tipo") in tipos and all(c.get("quien") == "Tú" for c in cs),
       f"V2 · {yo} en {pant}: consejos propios ({[c['que'][:45] for c in cs]})")
s, r = pedir("/api/ia/consejo?pantalla=setters", "setter_ana")
ok(not any("más antiguo" in c.get("que", "") for c in r.get("consejos") or []) and any((c.get("pestana") or {}).get("id") for c in r.get("consejos") or []),
   "V2 · Setters: el consejo usa el mismo orden que la lista (el más nuevo primero) y lleva a su pestaña")
# Copiloto: sin «null» y con la vara de rojo de la verdad única
for cli in ("fitec-asesores", "concilia", "gac"):
    s, r = pedir("/api/ia/copiloto", "tomas", {"cliente_id": cli})
    txt = json.dumps(r, ensure_ascii=False)
    g = (verdad.get(cli) or {}).get("gravedad")
    nulos = '"null"' in txt or any(r.get(k, "") is None for k in ("escalar", "aviso", "diagnostico", "acciones"))
    ok(s == 200 and not nulos and r.get("gravedad") == g and r.get("color") == {"critico": "rojo", "atencion": "ambar", "bien": "verde"}.get(g),
       f"V2 · Copiloto de {cli}: sin «null» y color = gravedad de la verdad única ({g} → {r.get('color')})")
s, L2 = pedir("/api/ia/lista", "tomas")
mal_color = [c["cliente_id"] for c in L2.get("copiloto", []) if c.get("color") != {"critico": "rojo", "atencion": "ambar", "bien": "verde"}.get((verdad.get(c["cliente_id"]) or {}).get("gravedad"))]
ok(not mal_color, f"V2 · La lista del copiloto pinta la gravedad de la verdad única ({mal_color[:3] or 'todas'})")

# 8. N12 · con clave (proveedor simulado, en este mismo proceso): la IA solo reordena y redacta; una cifra inventada se descarta
import ia as IAm     # noqa: E402
if IAm.S is None:
    IAm.enganchar(SV.Manejador, SV)
luc = SV.E.persona("lucia")
cp_l = SV.P.contexto(luc, SV.E.crudo)
IAm.estado = lambda: {"conectada": True, "modelo": "simulado", "motivo": None}
IAm._guardar_vivo = lambda *a, **k: None
IAm._vivo = lambda *a, **k: None
base = IAm.consejo(luc, luc, cp_l, "mi-dia")
refs = [c["id"] for c in base["consejos"]]
IAm.llamar = lambda sis, ctx, esq, effort="low": ({"consejos": [
    {"ref": refs[-1], "que": "Primero esto", "porque": "Texto con una cifra inventada: 999 leads."},
    {"ref": "inventado", "que": "Nada", "porque": "Nada"},
    {"ref": refs[0], "que": "Luego esto", "porque": base["consejos"][0]["porque"]}]}, "simulado")
viv = IAm.consejo(luc, luc, cp_l, "mi-dia", con_ia=True)
ok(viv["origen"] == "vivo" and [c["id"] for c in viv["consejos"]] == [refs[-1], refs[0]], "Con clave: la IA reordena los mismos candidatos y descarta un «ref» inventado")
ok("999" not in json.dumps(viv["consejos"], ensure_ascii=False), "Con clave: una cifra que no estaba en el dato se descarta (queda el texto de la regla)")
viv_como = IAm.consejo(SV.E.persona("tomas"), luc, cp_l, "mi-dia", con_ia=True)
ok(viv_como["origen"] == "reglas", "Con clave, en «ver como» no se genera nada nuevo")

# 9. N12 · «Qué hacer» con una fuente caída (la tubería de C5 marca «caida» y conserva el último dato bueno)
import motor_consejos as MCm  # noqa: E402
_tab = MCm.tabla_fuentes({"fuentes": [{"id": "meta", "estado": "dato_viejo", "hora": datetime.now().strftime("%Y-%m-%d 18:05"),
                                      "caida": {"desde": datetime.now().strftime("%Y-%m-%d 21:05"), "motivo": "token caducado"}}]},
                         None, {"conexiones": [{"id": "meta", "quien": "Agus"}]}, datetime.now())
ok(_tab and _tab[0]["paso"] == "Meta caído desde las 21:05 · lo revisa Agus · mientras, cifras de las 18:05",
   f"«Qué hacer» ante Meta caído: «{_tab[0]['paso'] if _tab else '—'}»")

print(f"\n{len(BIEN)} bien · {len(FALLOS)} mal")
sys.exit(1 if FALLOS else 0)

#!/usr/bin/env python3
"""fuentes_consejos/cerebro_decisiones.py · CEREBRO DE DECISIONES v2 (3-oct-2026).

Encima del motor de reglas (motor_consejos.py, que saca candidatos de alertas, verdad única, producción, ventas…):
  1. DIAGNÓSTICO antes que consejo (cd_diagnostico.py): árbol por síntoma para cada cliente, con evidencia y regla.
  2. REGLAS POR PUESTO (conocimiento/puestos.json): peso de cada tipo en cada uno de los 21 puestos, lo que un gran jefe
     de ese puesto le diría hoy, y consejos propios de jefas y operaciones (cartera roja, velocidad del CRM, críticos).
  3. PRIORIDAD por impacto (cd_prioridad.py): euros en riesgo o de captación, urgencia, esfuerzo y aprendizaje; motivo en
     una línea, con importes solo si quien lee ve la cuota de ese cliente.
  4. EXPLICABILIDAD: por qué, con qué dato y fecha (evidencia), criterio con «Ver fuente ↗» al cerebro (reglas.json →
     GitHub ro-equipo), confianza (alta, media, baja) y su porqué.
  5. PRUDENCIA (cd_prudencia.py): nada de asesorar al cliente sobre su negocio, prometer plazos ni tocar precios; nunca
     «crítico» contra la verdad única.
  6. APRENDIZAJE (cd_aprendizaje.py): las reglas con mal resultado bajan; las valoraciones de cada persona también cuentan.

Funciones puras sobre datos ya leídos. La verdad, captación y CRM «completos» (sin recortar) solo se usan en el servidor
para puntuar y diagnosticar; lo que viaja al navegador pasa después por el recorte de dinero de ia.py.
"""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import cd_diagnostico as DG   # noqa: E402
import cd_prioridad as PR     # noqa: E402
import cd_prudencia as PZ     # noqa: E402
import cd_aprendizaje as AP   # noqa: E402

AQUI = Path(__file__).resolve().parent
KB = AQUI / "conocimiento"
REPO = "https://github.com/tomassala8/ro-equipo/blob/main/"
_CACHE = {}


def _kb(nombre):
    f = KB / nombre
    try:
        mt = f.stat().st_mtime
    except OSError:
        return {}
    if _CACHE.get(nombre, (None,))[0] != mt:
        try:
            _CACHE[nombre] = (mt, json.loads(f.read_text()))
        except Exception:
            _CACHE[nombre] = (mt, {})
    return _CACHE[nombre][1]


def reglas():
    return {r["id"]: r for r in (_kb("reglas.json").get("reglas") or []) if r.get("id")}


def tipos():
    return _kb("tipos.json").get("tipos") or {}


def puestos():
    return _kb("puestos.json").get("puestos") or {}


def url_regla(r):
    """Enlace a la fuente de criterio: el fichero del repo ro-equipo en GitHub, en su línea. Fuera del repo, None."""
    if not r:
        return None
    if r.get("url"):
        return r["url"]
    f = str(r.get("fichero") or "")
    if not f or f.startswith("/") or f.startswith("~"):
        return None
    return REPO + f + ("?plain=1#L" + str(int(r["linea"])) if r.get("linea") else "")


def peso_puesto(ps, tipo):
    """Puntos que suma un tipo en los puestos de esta persona (el mayor). Las horas nunca suben."""
    P = puestos()
    vs = [int((P.get(p) or {}).get("pesos", {}).get(tipo, 0)) for p in ps or []]
    return max([v for v in vs if v > 0] + [0]) + min([v for v in vs if v < 0] + [0])     # lo negativo de un puesto se resta


def regla_de(tipo, ps, preferida=None):
    """La regla que respalda este consejo para estos puestos: la del diagnóstico si la hay; si el puesto la cambia, esa."""
    if preferida:
        return preferida
    P = puestos()
    for p in ps or []:
        r = ((P.get(p) or {}).get("regla_de_tipo") or {}).get(tipo)
        if r:
            return r
    return (tipos().get(tipo) or {}).get("regla")


def criterio(rid):
    r = reglas().get(rid)
    if not r:
        return None
    autor = r.get("autor") or "RO"
    return {"id": rid, "regla": r.get("regla"), "autor": autor, "texto": f"{autor}: {r.get('regla')}",
            "url": url_regla(r), "fichero": r.get("fichero"), "confianza": r.get("confianza") or "media"}


# ------------------------------------------------------------------------------------------- diagnóstico por cliente
TEMA_DE_SINTOMA = {
    "pocos_leads": {"pub_critico", "pub_atencion"},
    "leads_sin_citas": {"crm_sin_tocar", "crm_whatsapp", "fuga_integracion", "crm_sin_usar"},
    "citas_sin_ventas": {"crm_citas_sin_estado"},
    "relacion_en_riesgo": {"acc_correos", "acc_critico", "critico_cliente", "acc_sin_reunion", "bloqueo_callado", "alta_fuera_plazo"},
}
PANTALLAS_SINTOMA = {"pocos_leads": ["captacion", "ficha", "mi-dia"], "leads_sin_citas": ["salud-crm", "ficha", "mi-dia"],
                     "citas_sin_ventas": ["salud-crm", "ficha", "mi-dia"]}
METRICA_SINTOMA = {"pocos_leads": lambda k, s: ((k or {}).get("leads") or {}).get("7d"),
                   "leads_sin_citas": lambda k, s: ((s or {}).get("citas_30d") or {}).get("agendadas"),
                   "citas_sin_ventas": lambda k, s: (((s or {}).get("embudo") or {}).get("funnel") or {}).get("cerrado")}


def resumen_diag(d):
    """El diagnóstico tal como viaja: síntoma, causa con su dato y lo ya descartado (sin los nodos completos)."""
    if not d:
        return None
    c = d["causa"]
    return {"sintoma": d["sintoma"], "titulo": d["titulo"], "texto": d["texto"],
            "causa": {"pregunta": c["pregunta"], "dato": c["evidencia"]["dato"], "regla": c["regla"], "silla": c["silla"]},
            "camino": [{"pregunta": n["pregunta"], "estado": n["estado"], "dato": n["evidencia"]["dato"]} for n in d["nodos"]],
            "fecha": c["evidencia"].get("fecha"), "fuente": c["evidencia"].get("fuente"), "url": c["evidencia"].get("url")}


def frase_diag(d):
    """Una frase para el porqué: «Diagnóstico: <dato del primer eslabón roto>.» o «sin causa clara (revisado: …)»."""
    if not d or d["sintoma"] == "relacion_en_riesgo":
        return None
    c = d["causa"]
    oks = DG.descartado(d)
    if c["regla"] == "diag_sin_dato":
        return "Diagnóstico: sin causa clara en los datos" + (f" (descartado: {'; '.join(oks[:3])})" if oks else "") + "."
    return f"Diagnóstico: {c['evidencia']['dato'].rstrip('.')}."


def diagnosticos(ctx):
    """{cliente_id: diagnóstico} de todos los clientes (verdad completa + captación + CRM)."""
    out = {}
    cap, crm = ctx.get("captacion_idx") or {}, ctx.get("crm_idx") or {}
    for cid, v in (ctx.get("verdad_idx") or {}).items():
        d = DG.diagnosticar(v, cap.get(cid), crm.get(cid), ctx.get("fechas"))
        if d:
            out[cid] = d
    return out


def _cand_diag(persona, d, v, k, s, nombre):
    c = d["causa"]
    dueno = DG.dueno_de(v, c["silla"])
    cli = d.get("cliente") or "el cliente"
    acc = (c.get("accion") or "Revisa el embudo").rstrip(".")
    porque = f"{d['titulo']}: {d['texto']}. Causa probable: {c['evidencia']['dato']}."
    oks = DG.descartado(d)
    if oks:
        porque += " Descartado: " + "; ".join(oks) + "."
    val = METRICA_SINTOMA[d["sintoma"]](k, s)
    return {
        "id": f"dg:{d['cliente_id']}:{d['sintoma']}", "tipo": f"diag_{d['sintoma']}", "pantallas": PANTALLAS_SINTOMA[d["sintoma"]],
        "cliente_id": d["cliente_id"], "cliente": cli, "que": f"{cli}: {acc[:1].lower()}{acc[1:]}"[:140], "porque": porque,
        "cifra": d["texto"], "umbral": None, "fuente": {"texto": c["evidencia"].get("fuente") or "Diagnóstico del embudo", "url": c["evidencia"].get("url")},
        "ir": f"#/captacion/{d['cliente_id']}" if d["sintoma"] == "pocos_leads" else f"#/ficha/{d['cliente_id']}/resumen",
        "ir_texto": "Ver su captación" if d["sintoma"] == "pocos_leads" else "Abrir su ficha", "ir_alt": f"#/ficha/{d['cliente_id']}/resumen",
        "quien": "Tú" if dueno == persona["id"] else (nombre(dueno) or "Su dueño"), "dueno": dueno, "grav_cliente": (v or {}).get("gravedad"),
        "cuando": "Hoy" if (v or {}).get("gravedad") == "critico" else "Esta semana",
        "gravedad": "alta" if (v or {}).get("gravedad") == "critico" else "media",
        "orden": 230 if (v or {}).get("gravedad") == "critico" else 175, "personal": False, "requiere": [], "accion": None,
        "origen": "reglas", "diagnostico": resumen_diag(d), "regla_diag": c["regla"],
        "metrica": {"valor": val, "mejor": "sube"} if val is not None else None,
    }


JEFAS_Y_MANDO = {"operaciones", "jefa_publicidad", "jefa_crm", "jefa_seo"}


# ------------------------------------------------------------------------------------------- consejos propios por puesto
def _de_jefas(persona, ctx, nombre):
    ps = set(persona.get("puestos") or [])
    out = []
    if "jefa_publicidad" in ps:
        rojos = {}
        for cid, k in (ctx.get("captacion_idx") or {}).items():
            t = ((k.get("equipo") or {}).get("trafficker"))
            if t and t != persona["id"] and k.get("severidad") == "critico":
                rojos.setdefault(t, []).append(k.get("nombre") or cid)
        for t, xs in sorted(rojos.items(), key=lambda x: -len(x[1])):
            if len(xs) >= 2:                                          # parámetros de Captación: rojos_trafficker [2, 4]
                out.append({"id": f"jf:pub:{t}", "tipo": "jefa_cartera_roja", "pantallas": ["captacion", "mi-dia"], "cliente_id": None,
                            "cliente": None, "etiqueta": nombre(t), "que": f"Revisa hoy con {nombre(t) or t} sus {len(xs)} cuentas en crítico",
                            "porque": f"{', '.join(xs[:4])}{' y más' if len(xs) > 4 else ''}: con 2 o más cuentas en crítico la cartera de un trafficker necesita a su jefa (con 4, se reparte).",
                            "cifra": f"{len(xs)} cuentas en crítico", "umbral": "Vigilar con 2 cuentas en crítico · crítico con 4",
                            "fuente": {"texto": "Captación (Mis cuentas por trafficker)", "url": None}, "ir": "#/captacion", "ir_texto": "Ver Captación",
                            "quien": "Tú", "dueno": persona["id"], "cuando": "Hoy", "gravedad": "alta" if len(xs) >= 4 else "media",
                            "orden": 240 if len(xs) >= 4 else 190, "personal": False, "requiere": ["captacion"], "accion": None, "origen": "reglas"})
    if "jefa_crm" in ps:
        lentas = []
        for cid, s in (ctx.get("crm_idx") or {}).items():
            v = s.get("velocidad") or {}
            if s.get("tipo") in (None, "cliente") and (v.get("juzgables") or 0) >= 5 and (v.get("pct_1h") or 0) < 70:
                lentas.append((s.get("nombre") or cid, v.get("pct_1h") or 0))
        if len(lentas) >= 3:
            lentas.sort(key=lambda x: x[1])
            out.append({"id": "jf:crm:velocidad", "tipo": "jefa_crm_velocidad", "pantallas": ["salud-crm", "mi-dia"], "cliente_id": None,
                        "cliente": None, "que": f"Revisa con tus especialistas las {len(lentas)} subcuentas que contactan tarde",
                        "porque": f"En {', '.join(n for n, _ in lentas[:4])}{' y más' if len(lentas) > 4 else ''} menos del 70 % de los leads tiene un primer intento en menos de 1 hora: es donde se pierden las citas.",
                        "cifra": f"{len(lentas)} subcuentas lentas", "umbral": "Garantía: 70 % con intento en menos de 1 h",
                        "fuente": {"texto": "Salud del CRM (velocidad de contacto)", "url": None}, "ir": "#/salud-crm", "ir_texto": "Ver Salud del CRM",
                        "quien": "Tú", "dueno": persona["id"], "cuando": "Esta semana", "gravedad": "media", "orden": 185, "personal": False,
                        "requiere": ["salud-crm"], "accion": None, "origen": "reglas"})
    if "operaciones" in ps:
        crit = [v for v in (ctx.get("verdad_idx") or {}).values() if v.get("gravedad") == "critico"]
        if crit:
            crit.sort(key=lambda v: -(v.get("cuota") or 0))
            tot = sum(v.get("cuota") or 0 for v in crit)
            out.append({"id": "op:criticos", "tipo": "ops_cartera_riesgo", "pantallas": ["mi-dia", "en-rojo"], "cliente_id": None,
                        "cliente": None, "que": f"Repasa con cada account el plan de sus {len(crit)} clientes críticos, empezando por {crit[0].get('nombre')}",
                        "porque": f"Suman {PR.euros(tot)}/mes de cuota. Por cuota: {', '.join(v.get('nombre') for v in crit[:4])}. Un crítico sin plan escrito es una baja en camino.",
                        "cifra": f"{len(crit)} clientes críticos", "umbral": "Crítico: la regla de gravedad de la verdad única",
                        "fuente": {"texto": "Verdad única y En rojo", "url": None}, "ir": "#/en-rojo", "ir_texto": "Ver En rojo",
                        "quien": "Tú", "dueno": persona["id"], "cuando": "Esta semana", "gravedad": "alta", "orden": 230, "personal": False,
                        "requiere": ["en-rojo"], "accion": None, "origen": "reglas", "cuota_total": round(tot)})
    return out


# ------------------------------------------------------------------------------------------- explicabilidad
def evidencia(c, fechas):
    fte = c.get("fuente") or {}
    d = c.get("diagnostico")
    if d:
        ev = [{"dato": n["dato"], "fecha": d.get("fecha"), "fuente": d.get("fuente"), "estado": n["estado"]} for n in d["camino"]]
        return ev
    dato = c.get("cifra") or str(c.get("porque") or "").split(". ")[0][:160]
    t = c.get("tipo") or ""
    fecha = fechas.get("verdad") if c["id"].startswith(("vd:", "op:")) else fechas.get("captacion") if t.startswith(("jefa_cartera", "pub_")) \
        else fechas.get("crm") if t.startswith(("crm_", "jefa_crm")) else fechas.get("alertas")
    return [{"dato": dato, "fecha": fecha, "fuente": fte.get("texto"), "url": fte.get("url")}]


def confianza(c, crit):
    if c.get("dato_en_duda"):
        return "baja", "La fuente de este dato está en duda: compruébalo antes de actuar."
    if (c.get("diagnostico") or {}).get("causa", {}).get("regla") == "diag_sin_dato":
        return "media", "Hay síntoma pero los datos no señalan una causa: falta dato."
    if not crit:
        return "media", "Sin regla de criterio enlazada todavía."
    if crit.get("confianza") == "media":
        return "media", "La regla es una propuesta de RO sin firmar o con umbral provisional."
    return "alta", "Dato del día y regla con fuente."


# ------------------------------------------------------------------------------------------- el paso completo
def enriquecer(persona, cands, ctx, nombre=lambda x: x, completo=True):
    """Añade diagnóstico, consejos de jefas, criterio, evidencia, confianza, métrica, prioridad y prudencia. Devuelve la
    lista nueva ordenada por puntos (el «orden» pasa a ser los puntos; el de la regla queda en prioridad.regla_pts)."""
    ps = persona.get("puestos") or []
    vidx = ctx.get("verdad_idx") or {}
    fechas = ctx.get("fechas") or {}
    ajustes = ctx.get("ajustes") or {}
    cuota_alta = ctx.get("cuota_alta") or PR.CUOTA_ALTA_DEFECTO
    xs = list(cands)
    # 1 · diagnóstico: se ENGANCHA al consejo que ya habla de ese cliente y ese tema (mismo dueño); si no hay, sale uno nuevo
    diags = ctx.get("diagnosticos")
    if diags is None:
        diags = diagnosticos(ctx)
    if not completo:                 # candidatos de la cola (al servir): solo se explican y puntúan, sin añadir nada
        diags = {}
    for cid, d in diags.items():
        v = vidx.get(cid) or {}
        dueno = DG.dueno_de(v, d["causa"]["silla"])
        tema = TEMA_DE_SINTOMA.get(d["sintoma"], set())
        mismo = [c for c in xs if c.get("cliente_id") == cid and c.get("tipo") in tema]
        for c in mismo:
            c["diagnostico"] = resumen_diag(d)
            frase = frase_diag(d)
            if frase and frase not in str(c.get("porque") or ""):
                c["porque"] = f"{str(c.get('porque') or '').rstrip('.')}. {frase}"
            if d["sintoma"] != "relacion_en_riesgo":      # en relación, cada consejo conserva su regla (queja ≠ correo)
                c["regla_diag"] = d["causa"]["regla"]
        if d["sintoma"] == "relacion_en_riesgo":
            continue
        if any(c.get("dueno") == dueno for c in mismo):
            continue
        if dueno != persona["id"] and not (set(ps) & JEFAS_Y_MANDO):
            continue                 # solo para su dueño y para quien puede pedírselo (para_quien decide al servir)
        xs.append(_cand_diag(persona, d, v, (ctx.get("captacion_idx") or {}).get(cid), (ctx.get("crm_idx") or {}).get(cid), nombre))
    # 2 · consejos propios de jefas y operaciones
    if completo:
        xs += _de_jefas(persona, ctx, nombre)
    # 3-5 · criterio, evidencia, confianza, métrica, prioridad y prudencia
    T = tipos()
    es_dir = "direccion" in ps
    out = []
    for c in xs:
        meta = T.get(c.get("tipo")) or {}
        rid = regla_de(c.get("tipo"), ps, c.get("regla_diag"))
        crit = criterio(rid)
        if crit:
            c["criterio"] = crit
        c["evidencia"] = evidencia(c, fechas)
        c["confianza"], c["confianza_porque"] = confianza(c, crit)
        v_full = vidx.get(c.get("cliente_id")) if c.get("cliente_id") else None
        aj = int(ajustes.get(rid or "", 0) or 0)
        c["prioridad"] = PR.puntuar(c, v_full, meta, cuota_alta, aj)
        c["orden"] = c["prioridad"]["puntos"]
        if not c.get("metrica"):
            m = AP.metrica(c, (v_full or {}).get("gravedad"))
            c["metrica"] = {"valor": m.get("valor"), "mejor": m.get("mejor") or "baja"} if m.get("valor") is not None else None
        c2, faltas = PZ.revisar(c, (v_full or {}).get("gravedad") or c.get("grav_cliente"), es_dir)
        if c2 is None:
            continue
        if faltas:
            c2["prudencia"] = faltas
        c2.pop("regla_diag", None)
        out.append(c2)
    out.sort(key=lambda c: -c["orden"])
    return out


def contexto(verdad_full, captacion_full, crm_full, alertas_doc=None, ajustes=None):
    """El contexto del cerebro (solo servidor): índices por cliente, fechas de cada fuente, ajustes y cuota media."""
    vidx = {c.get("cliente_id"): c for c in (verdad_full or {}).get("clientes") or [] if c.get("cliente_id")}
    cidx = {c.get("cliente_id"): c for c in (captacion_full or {}).get("clientes") or [] if c.get("cliente_id")}
    ridx = {}
    for s in (crm_full or {}).get("subcuentas") or []:
        if s.get("cliente_id") and s.get("cliente_id") not in ridx:
            ridx[s["cliente_id"]] = s
    fechas = {"verdad": (verdad_full or {}).get("generado"), "captacion": (captacion_full or {}).get("datos_hasta") or (captacion_full or {}).get("generado"),
              "crm": (crm_full or {}).get("generado"), "alertas": (alertas_doc or {}).get("generado")}
    ctx = {"verdad_idx": vidx, "captacion_idx": cidx, "crm_idx": ridx, "fechas": fechas,
           "ajustes": AP.ajustes() if ajustes is None else ajustes, "cuota_alta": PR.cuota_media_alta(verdad_full)}
    ctx["diagnosticos"] = diagnosticos(ctx)
    return ctx


def copiloto_reglas(cid, ctx, cands_cliente):
    """«Qué haría hoy» de un cliente SIN clave: el diagnóstico en 3 líneas y las 3 acciones con más puntos de ese cliente."""
    d = (ctx.get("diagnosticos") or {}).get(cid)
    v = (ctx.get("verdad_idx") or {}).get(cid) or {}
    diag = DG.lineas(d) if d else []
    if not diag:
        mot = v.get("motivos") or []
        diag = [f"Según la verdad única: {'; '.join(mot[:2]).rstrip('.')}." if mot else "Sin síntomas en captación, CRM ni relación."]
    acciones = []
    for c in sorted(cands_cliente, key=lambda c: -c.get("orden", 0))[:3]:
        acciones.append({"que": c.get("que"), "porque": c.get("porque"), "dato": c.get("cifra") or (c.get("evidencia") or [{}])[0].get("dato") or "",
                         "fuente": "verdad", "quien": c.get("quien") or "", "cuando": c.get("cuando") or "",
                         "criterio": c.get("criterio"), "confianza": c.get("confianza")})
    color = {"critico": "rojo", "atencion": "ambar", "bien": "verde"}.get(v.get("gravedad"), "ambar")
    escalar = None
    if v.get("gravedad") == "critico":
        escalar = "Mili: cliente crítico. Antes de hablar con el cliente, plan escrito con números y su «Visto»."
    return {"color": color, "diagnostico": diag, "acciones": acciones, "escalar": escalar, "origen": "reglas",
            "arbol": resumen_diag(d)}

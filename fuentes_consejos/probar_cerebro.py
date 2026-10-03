#!/usr/bin/env python3
"""fuentes_consejos/probar_cerebro.py · pruebas del CEREBRO DE DECISIONES v2 (3-oct-2026).

Las llama fuentes_ia/probar_ia.py (sección 11) con su servidor en marcha (copia de local.db):
  probar_cerebro.correr(ok, pedir, SV, IAm, DB)

Comprueba: base de conocimiento (21 puestos, cada tipo con su regla y su fuente), diagnóstico antes que consejo (árbol con
evidencia y regla), prioridad correcta (impacto, urgencia, esfuerzo, aprendizaje; lista ordenada), sin fugas de importes
(quien no ve la cuota no recibe euros ni en el texto ni en los campos; «Lo mío» igual), coherencia con la verdad única
(nunca «crítico» si no lo es; la gravedad del impacto es la de la verdad), prudencia (ni precios, ni plazos, ni asesorar),
bucle de aprendizaje (valorar con rastro del servidor, «Ya hecho» se aparta, «No útil» baja, seguimiento a 7/14 días,
informe solo para dirección), copiloto por reglas sin clave, y la IA simulada no cuela nada prohibido.
"""
import json
import re
import sqlite3
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

AQUI = Path(__file__).resolve().parent
APP = AQUI.parent
sys.path.insert(0, str(AQUI))
import cerebro_decisiones as CD  # noqa: E402

RE_EURO = re.compile(r"\d[\d.,]*\s*€|€\s*\d")
NO_VEN_CUOTA = ["lina", "gustavo", "valeria", "jeronimo", "camilo", "eulimar", "setter_ana", "carlos_viur", "kimberlyn", "yessica"]
PANTALLAS = ["mi-dia", "captacion", "salud-crm", "ficha", "en-rojo", "produccion", "seo-web", "redes", "setters", "prospeccion"]


def correr(ok, pedir, SV, IAm, DB):
    verdad = {c["cliente_id"]: c for c in json.loads((APP / "data/verdad/clientes.json").read_text())["clientes"]}

    # --- 1 · base de conocimiento
    R, T, P = CD.reglas(), CD.tipos(), CD.puestos()
    TODOS = {"direccion", "finanzas_direccion", "operaciones", "rrhh", "administracion", "tecnico_altas", "proyectos", "account",
             "jefa_publicidad", "trafficker", "jefa_crm", "especialista_ghl", "jefa_seo", "seo", "ficha_google", "web", "redes",
             "produccion", "setters", "ventas_ro", "outreach"}
    ok(set(P) == TODOS, f"Cerebro · los 21 puestos con reglas propias ({len(P)}; faltan {sorted(TODOS - set(P)) or 'ninguno'})")
    malos = [p for p, x in P.items() if len([r for r in x.get("reglas_jefe") or [] if r in R]) < 2 or not x.get("foco")]
    ok(not malos, f"Cerebro · cada puesto con su foco y al menos 2 reglas de criterio con fuente ({malos or 'todos'})")
    sin_regla = [t for t, m in T.items() if m.get("regla") not in R]
    ok(not sin_regla, f"Cerebro · cada tipo de consejo respaldado por una regla de reglas.json ({sin_regla or 'todos'})")
    sin_fuente = [r["id"] for r in R.values() if not r.get("fichero") or not r.get("autor")]
    malas_url = [r["id"] for r in R.values() if r.get("url") and not str(r["url"]).startswith("https://github.com/tomassala8/ro-equipo/blob/main/")]
    ok(not sin_fuente and not malas_url and len(R) >= 120,
       f"Cerebro · {len(R)} reglas con autor y fichero; los enlaces van a GitHub ({sum(1 for r in R.values() if r.get('url'))} con «Ver fuente ↗»)")
    ok(not any(str(r.get("fichero") or "").startswith("/") for r in R.values()), "Cerebro · ninguna ruta del Mac viaja en las reglas")

    # --- 2 · diagnóstico antes que consejo
    ctx = IAm.ctx_cerebro()
    dg = ctx.get("diagnosticos") or {}
    ok(len(dg) >= 10 and all(d["causa"]["estado"] == "roto" and d["causa"]["evidencia"]["dato"] for d in dg.values()),
       f"Diagnóstico · {len(dg)} clientes con síntoma; cada uno para en el primer eslabón roto con su dato")
    camino_ok = all(all(n["estado"] == "ok" or n["estado"] == "sin_dato" for n in d["nodos"][:-1]) for d in dg.values())
    ok(camino_ok, "Diagnóstico · todo lo anterior a la causa está descartado (ok) o sin dato: recorre el embudo de arriba abajo")
    lav = dg.get("laver")
    if lav:
        ok(lav["sintoma"] == "leads_sin_citas" and lav["causa"]["regla"] == "diag_velocidad",
           f"Diagnóstico · Laver: leads sin citas por velocidad de contacto ({lav['causa']['evidencia']['dato'][:80]})")
    # sintético: pocos leads por creatividad cansada (gasta, hay clics y leads, frecuencia 4)
    k = {"cliente_id": "x", "meta_activa": True, "leads": {"7d": 2, "7d_prev": 10}, "gasto": {"7d": 300, "ayer": 40},
         "cuenta_meta": {"estado": "activa"}, "anuncios": {"anuncios": [{"nombre": "A1", "clics_7d": 200, "frecuencia_7d": 4.2, "caida_ctr_pct": 45, "gasto_7d": 200}]},
         "cpl_resumen": {"ref": 30, "veces_objetivo": 0.9, "fiable": True}}
    d = CD.DG.diagnosticar({"cliente_id": "x", "nombre": "X", "gravedad": "atencion"}, k, None, {})
    ok(d and d["sintoma"] == "pocos_leads" and d["causa"]["regla"] == "diag_fatiga" and [n["estado"] for n in d["nodos"]] == ["ok", "ok", "roto"],
       "Diagnóstico · sintético: ¿gasta? sí → ¿formulario? sí → creatividad cansada (frecuencia 4,2 y clics −45 %)")
    k2 = dict(k, anuncios={"anuncios": [{"nombre": "A1", "clics_7d": 300}]}, leads={"7d": 0, "7d_prev": 8})
    d2 = CD.DG.diagnosticar({"cliente_id": "x"}, k2, None, {})
    ok(d2 and d2["causa"]["regla"] == "diag_formulario_roto", "Diagnóstico · sintético: 300 clics y 0 leads → formulario o página rotos")
    k3 = dict(k, gasto={"7d": 0, "ayer": 0}, cuenta_meta={"estado": "pago_pendiente"})
    d3 = CD.DG.diagnosticar({"cliente_id": "x"}, k3, None, {})
    ok(d3 and d3["causa"]["regla"] == "diag_no_gasta" and len(d3["nodos"]) == 1, "Diagnóstico · sintético: la campaña no gasta → para ahí (no se mira nada más)")

    # --- 3 · prioridad correcta
    PR = CD.PR
    m = {"tema": "relacion", "esfuerzo_min": 15}
    c0 = {"tipo": "acc_correos", "cuando": "Hoy", "gravedad": "alta", "orden": 200, "cliente": "A"}
    p_crit = PR.puntuar(c0, {"cuota": 1470, "gravedad": "critico"}, m, 1470)
    p_aten = PR.puntuar(c0, {"cuota": 1470, "gravedad": "atencion"}, m, 1470)
    p_bien = PR.puntuar(c0, {"cuota": 1470, "gravedad": "bien"}, m, 1470)
    p_poca = PR.puntuar(c0, {"cuota": 300, "gravedad": "critico"}, m, 1470)
    ok(p_crit["puntos"] > p_aten["puntos"] > p_bien["puntos"] and p_crit["puntos"] > p_poca["puntos"],
       f"Prioridad · más cuota y más gravedad, más arriba ({p_crit['puntos']} > {p_aten['puntos']} > {p_bien['puntos']}; 300 €: {p_poca['puntos']})")
    venc = PR.puntuar(dict(c0, cuando="Vencida hace 9 días"), {"cuota": 1470, "gravedad": "atencion"}, m, 1470)
    sem = PR.puntuar(dict(c0, cuando="Esta semana", gravedad="media"), {"cuota": 1470, "gravedad": "atencion"}, m, 1470)
    ok(venc["puntos"] > p_aten["puntos"] > sem["puntos"], f"Prioridad · vencida > hoy > esta semana ({venc['puntos']} > {p_aten['puntos']} > {sem['puntos']})")
    largo = PR.puntuar(c0, {"cuota": 1470, "gravedad": "atencion"}, dict(m, esfuerzo_min=120), 1470)
    ok(p_aten["puntos"] > largo["puntos"], "Prioridad · a igual impacto y plazo, lo rápido primero")
    malo = PR.puntuar(c0, {"cuota": 1470, "gravedad": "atencion"}, m, 1470, ajuste=-60)
    ok(malo["puntos"] == p_aten["puntos"] - 60, "Prioridad · una regla con mal resultado baja 60 puntos")
    ok("GAC paga 1.205 €/mes" in (PR.motivo({"cliente": "GAC", "cifra": "9 días sin leads", "cuando": "Hoy"},
                                             PR.impacto({"tipo": "x"}, {"cuota": 1205, "gravedad": "critico"}, m, 1470), PR.urgencia({"cuando": "Hoy"}),
                                             PR.esfuerzo(m), True) or ""),
       "Prioridad · el motivo en una línea: «GAC paga 1.205 €/mes, es cliente crítico y 9 días sin leads»")
    desordenados = []
    for yo in ("lucia", "candela", "natalia", "lina", "gustavo", "yessica", "valeria", "agustina", "camilo", "tomas"):
        s, r = pedir("/api/ia/consejo?pantalla=mi-dia", yo)
        cs = r.get("consejos") or []
        pts = [c.get("orden") for c in cs]
        if pts != sorted(pts, reverse=True):
            desordenados.append(f"{yo}: {pts}")
        if any(not c.get("prioridad") or not c.get("motivo_linea") for c in cs):
            desordenados.append(f"{yo}: sin prioridad o motivo")
    ok(not desordenados, f"Prioridad · Mi día ordenado por puntos y cada consejo con su motivo ({desordenados[:2] or '10 personas'})")
    s, r = pedir("/api/ia/consejo?pantalla=mi-dia", "lucia")
    c0r = (r.get("consejos") or [{}])[0]
    ok(str(c0r.get("motivo_linea") or "").startswith("Primero porque") and "€/mes" in str(c0r.get("motivo_linea")),
       f"Prioridad · Lucía (ve la cuota de su cartera): «{c0r.get('motivo_linea')}»")

    # --- 4 · sin fugas de importes
    fugas = []
    for yo in NO_VEN_CUOTA:
        per = SV.E.persona(yo)
        for pant in PANTALLAS:
            if not SV.ve_alguno(per, [pant]):
                continue
            s, r = pedir(f"/api/ia/consejo?pantalla={pant}", yo)
            for c in r.get("consejos") or []:
                cid = c.get("cliente_id")
                cp = SV.P.contexto(per, SV.E.crudo)
                ve_c = bool(cid) and SV.P.ver(per, {"tipo": "cuota", "cliente_id": cid}, cp)["ok"]
                pri = c.get("prioridad") or {}
                imp = pri.get("impacto") or {}
                if not ve_c and (imp.get("euros_mes") is not None or imp.get("cuota") is not None or "paga " in str(c.get("motivo_linea") or "")
                                 or "€/mes" in str(c.get("motivo_linea") or "") or c.get("cuota_total") is not None):
                    fugas.append(f"{yo}/{pant}/{c['id']}")
                ve_i = bool(cid) and SV.P.ver(per, {"tipo": "inversion", "cliente_id": cid}, cp)["ok"]
                if not ve_i and RE_EURO.search(json.dumps(c, ensure_ascii=False)):
                    fugas.append(f"{yo}/{pant}/{c['id']}: € en el texto")
    ok(not fugas, f"Sin fugas · {len(NO_VEN_CUOTA)} personas que no ven la cuota: ni euros, ni cuota, ni «paga …» en el motivo ({fugas[:3] or 'limpio'})")
    s, r = pedir("/api/modulo/prioridades/p_lina", "lina")
    t = json.dumps(r, ensure_ascii=False)
    ok(s == 200 and r.get("orden") and "euros_mes" not in t and "€/mes" not in t and not RE_EURO.search(t.replace("€ en", "")),
       f"Sin fugas · «Lo mío» de Lina (prioridades): {len(r.get('orden') or [])} cosas ordenadas, sin euros")
    s, r = pedir("/api/modulo/prioridades/p_lucia", "lucia")
    ajenos = [k for k, v in (r.get("por_cliente") or {}).items() if v.get("euros_mes") is not None and verdad.get(k, {}).get("account") != "lucia"]
    ok(s == 200 and r.get("orden") and not ajenos, f"Sin fugas · Lucía ve euros solo de su cartera en «Lo mío» ({ajenos[:3] or 'limpio'})")
    s, _ = pedir("/api/modulo/prioridades/p_lucia", "lina")
    s2, _ = pedir("/api/modulo/prioridades/p_lucia", "tomas", como="lina")
    ok(s in (403, 404) and s2 in (403, 404), f"Sin fugas · las prioridades de Lucía no las abre nadie más ({s}, ver como {s2})")
    s, _ = pedir("/api/modulo/consejos/p_lucia", "lucia")
    s2, _ = pedir("/api/modulo/consejos/_privado/aprendizaje", "tomas")
    ok(s in (403, 404) and s2 in (403, 404, 400), f"Sin fugas · el precalculado y el aprendizaje no se sirven como fichero ({s}, {s2})")

    # --- 5 · coherencia con la verdad única
    incoh = []
    for yo in ("lucia", "candela", "natalia", "mili", "tomas", "gustavo", "lina", "valeria", "yessica", "constanza"):
        for pant in ("mi-dia", "en-rojo", "captacion", "salud-crm"):
            if not SV.ve_alguno(SV.E.persona(yo), [pant]):
                continue
            s, r = pedir(f"/api/ia/consejo?pantalla={pant}", yo)
            for c in r.get("consejos") or []:
                v = verdad.get(c.get("cliente_id")) or {}
                if not c.get("cliente_id"):
                    continue
                txt = f"{c.get('que')} {c.get('motivo_linea') or ''}"
                if re.search(r"(?i)cr[ií]tico", txt) and v.get("gravedad") != "critico" and "cuentas en crítico" not in txt:
                    incoh.append(f"{yo}: «crítico» para {c.get('cliente')} ({v.get('gravedad')})")
                g = ((c.get("prioridad") or {}).get("impacto") or {}).get("gravedad")
                if g and g != v.get("gravedad"):
                    incoh.append(f"{yo}: gravedad {g} ≠ verdad {v.get('gravedad')} ({c.get('cliente')})")
                if (c.get("diagnostico") or {}) and c.get("grav_cliente") not in (None, v.get("gravedad")):
                    incoh.append(f"{yo}: diagnóstico con otra gravedad ({c.get('cliente')})")
    ok(not incoh, f"Verdad única · ni «crítico» inventado ni otra gravedad en impacto o diagnóstico ({incoh[:3] or 'coherente'})")

    # --- 6 · explicabilidad
    s, r = pedir("/api/ia/consejo?pantalla=mi-dia", "gustavo")
    cs = r.get("consejos") or []
    ok(cs and all(c.get("criterio", {}).get("regla") and c.get("confianza") in ("alta", "media", "baja") and c.get("evidencia") for c in cs),
       "Explicable · cada consejo con criterio (regla y autor), confianza y evidencia")
    ok(all(not (c.get("criterio") or {}).get("url") or c["criterio"]["url"].startswith("https://github.com/") for c in cs),
       "Explicable · «Ver fuente ↗» del criterio va al cerebro en GitHub")
    ok(all(e.get("fecha") for c in cs for e in c.get("evidencia") or []), "Explicable · cada evidencia lleva la fecha del dato")
    s, r = pedir("/api/ia/consejo?pantalla=captacion", "lina")
    dx = [c for c in r.get("consejos") or [] if c.get("diagnostico")]
    ok(dx and all(c["diagnostico"].get("causa", {}).get("dato") and c["diagnostico"].get("camino") for c in dx),
       f"Explicable · Lina en Captación: {len(dx)} consejos con su árbol (causa con dato y camino recorrido)")

    # --- 7 · prudencia
    PZ = CD.PZ
    a, f1 = PZ.revisar({"que": "Ofrécele un descuento del 20 %", "porque": "x"}, None, False)
    b, f2 = PZ.revisar({"que": "Garantiza 20 leads en 7 días", "porque": "x"}, None, False)
    c, f3 = PZ.revisar({"que": "Recomiéndale al cliente que contrate a otro asesor", "porque": "x"}, None, False)
    d4, f4 = PZ.revisar({"que": "Llama hoy a X: es un cliente crítico", "porque": "x", "cliente_id": "x"}, "atencion", False)
    ok(a and "dirección" in a["que"] and b is None and c is None and "crítico" not in d4["que"],
       "Prudencia · descuento → se eleva a dirección; prometer plazos o asesorar al cliente → fuera; «crítico» falso → se quita")
    prohib = []
    for yo in ("lucia", "tomas", "mili", "lina", "gustavo", "valeria", "yessica", "agustina"):
        s, r = pedir("/api/ia/consejo?pantalla=mi-dia", yo)
        for x in r.get("consejos") or []:
            if not PZ.limpio_texto(x.get("que")) or not PZ.limpio_texto(x.get("porque")):
                prohib.append(f"{yo}: {x.get('que')[:50]}")
    ok(not prohib, f"Prudencia · ningún consejo servido promete, asesora al cliente o toca precios ({prohib[:2] or 'limpio'})")

    # --- 8 · bucle de aprendizaje
    s, r = pedir("/api/ia/consejo?pantalla=mi-dia", "candela")
    cs = r.get("consejos") or []
    if len(cs) >= 2:
        c1, c2 = cs[0], cs[1]
        s1, v1 = pedir("/api/ia/consejo/valorar", "candela", {"consejo": c1["id"], "valor": "hecho", "pantalla": "mi-dia", "metrica": {"valor": 999}})
        fila = sqlite3.connect(DB).execute("SELECT datos FROM registro WHERE quien='candela' AND accion='consejo_valorado' ORDER BY id DESC LIMIT 1").fetchone()
        dat = json.loads(fila[0]) if fila else {}
        ok(s1 == 200 and dat.get("valor") == "hecho" and dat.get("regla") and (dat.get("metrica") or {}).get("valor") != 999,
           f"Aprendizaje · «Ya hecho» queda en el rastro con la métrica que pone el SERVIDOR (no la del navegador): {dat.get('metrica')}")
        s, r2 = pedir("/api/ia/consejo?pantalla=mi-dia", "candela")
        ok(c1["id"] not in [x["id"] for x in r2.get("consejos") or []], "Aprendizaje · lo marcado «Ya hecho» no vuelve a salir hoy")
        s3, _ = pedir("/api/ia/consejo/valorar", "candela", {"consejo": c2["id"], "valor": "no_util", "pantalla": "mi-dia"})
        s, r3 = pedir("/api/ia/consejo?pantalla=mi-dia", "candela")
        x2 = next((x for x in r3.get("consejos") or [] if x["id"] == c2["id"]), None)
        ok(s3 == 200 and (x2 is None or (x2.get("valoracion") == "no_util" and x2["orden"] <= c2["orden"] - 150)),
           "Aprendizaje · «No útil» lo baja 150 puntos para esa persona")
    s, _ = pedir("/api/ia/consejo/valorar", "lucia", {"consejo": "dg:musashi-consultores:citas_sin_ventas", "valor": "util"})
    ok(s == 403, "Aprendizaje · no se valora un consejo que no es tuyo (403)")
    s, _ = pedir("/api/ia/consejo/valorar", "tomas", {"consejo": "x", "valor": "util"}, como="lucia")
    ok(s == 403, "Aprendizaje · en «ver como» no se valora (403)")
    s, _ = pedir("/api/ia/consejo/valorar", "lucia", {"consejo": "x", "valor": "me_encanta"})
    ok(s == 403, "Aprendizaje · un valor que no es Útil / No útil / Ya hecho se rechaza")
    s, _ = pedir("/api/rastro", "lucia", {"accion": "consejo_valorado", "objeto": "x"})
    _f = sqlite3.connect(DB).execute("SELECT accion FROM registro WHERE quien='lucia' AND clave='x' AND accion LIKE '%consejo_valorado' ORDER BY id DESC LIMIT 1").fetchone()
    ok((s == 403 and not _f) or (_f and _f[0].startswith("nav:")), f"Aprendizaje · el navegador no puede fingir «consejo_valorado» ({s})")
    # seguimiento a 7/14 días con fotos sintéticas en un directorio temporal
    AP = CD.AP
    viejo = (AP.HIST, AP.F_APR)
    with tempfile.TemporaryDirectory() as tmp:
        AP.HIST = Path(tmp)
        hoy = datetime(2026, 10, 20)
        def foto(dias, consejos, grav=None):
            f = (hoy - timedelta(days=dias)).strftime("%Y-%m-%d")
            (AP.HIST / f"{f}.json").write_text(json.dumps({"fecha": f, "consejos": consejos, "gravedad": grav or {}}))
        foto(14, {"a": {"valor": 30, "mejor": "baja"}, "b": {"valor": 10, "mejor": "baja"}})
        foto(7, {"a": {"valor": 31}, "b": {"valor": 4}})
        foto(0, {"a": {"valor": 35}})                          # «b» ya no sale: resuelto
        f0 = (hoy - timedelta(days=14)).strftime("%Y-%m-%d")
        vals = [{"quien": "q", "consejo": "a", "valor": "hecho", "fecha": f0, "metrica": {"valor": 30, "mejor": "baja"}, "regla": "mala", "tipo": "t"} for _ in range(3)] + \
               [{"quien": "q", "consejo": "b", "valor": "hecho", "fecha": f0, "metrica": {"valor": 10, "mejor": "baja"}, "regla": "buena", "tipo": "t"} for _ in range(3)]
        doc = AP.evaluar(vals, hoy)
        ok(doc["ajustes"].get("mala", 0) < 0 and doc["ajustes"].get("buena", 0) > 0 and doc["por_regla"]["buena"]["mejoro"] == 3,
           f"Aprendizaje · seguimiento a 7/14 días: la regla que empeora baja ({doc['ajustes'].get('mala')}), la que resuelve sube ({doc['ajustes'].get('buena')})")
        sube = AP._comparar({"valor": 2, "mejor": "sube"}, {"valor": 6})
        ok(sube == "mejoro", "Aprendizaje · en el diagnóstico más leads es mejor (la métrica sabe hacia dónde mejora)")
    AP.HIST, AP.F_APR = viejo
    s, r = pedir("/api/ia/consejo/informe", "tomas")
    ok(s == 200 and "md" in r and "funcionan" in r, f"Aprendizaje · informe semanal para Tomás ({r.get('valoraciones')} valoraciones)")
    s, _ = pedir("/api/ia/consejo/informe", "lucia")
    s2, _ = pedir("/api/ia/consejo/informe", "tomas", como="mili")
    ok(s == 403 and s2 == 403, "Aprendizaje · el informe es solo de dirección y nunca en «ver como»")

    # --- 9 · copiloto sin clave: por reglas
    pre = set(json.loads((APP / "data/ia/_privado/copiloto.json").read_text()).get("clientes", {}))
    cli = next((cid for cid in dg if cid not in pre and verdad.get(cid, {}).get("account") == "lucia"), None) or \
        next((cid for cid in dg if cid not in pre), None)
    if cli:
        quien = "lucia" if verdad.get(cli, {}).get("account") == "lucia" else "tomas"
        s, r = pedir("/api/ia/copiloto", quien, {"cliente_id": cli})
        g = verdad.get(cli, {}).get("gravedad")
        ok(s == 200 and r.get("ok") and r.get("origen") == "reglas" and r.get("diagnostico") and r.get("arbol")
           and r.get("color") == {"critico": "rojo", "atencion": "ambar", "bien": "verde"}.get(g) and '"null"' not in json.dumps(r),
           f"Sin clave · copiloto de {cli} por reglas: {len(r.get('diagnostico') or [])} líneas, {len(r.get('acciones') or [])} acciones, árbol y color de la verdad")
    s, r = pedir("/api/ia/copiloto", "lucia", {"cliente_id": "musashi-consultores"})
    ok(s == 403, "Sin clave · el copiloto por reglas respeta los permisos de siempre (Lucía no abre Musashi: 403)")

    # --- 10 · con clave (simulada): la IA solo redacta; lo prohibido no pasa
    luc = SV.E.persona("lucia")
    cp_l = SV.P.contexto(luc, SV.E.crudo)
    orig = {k: getattr(IAm, k) for k in ("estado", "_guardar_vivo", "_vivo", "llamar")}
    try:
        IAm.estado = lambda: {"conectada": True, "modelo": "simulado", "motivo": None}
        IAm._guardar_vivo = lambda *a, **k: None
        IAm._vivo = lambda *a, **k: None
        base = IAm.consejo(luc, luc, cp_l, "mi-dia")
        refs = [c["id"] for c in base["consejos"]]
        IAm.llamar = lambda sis, ctx, esq, effort="low", tarea=None: ({"consejos": [
            {"ref": refs[0], "que": "Ofrécele un descuento y garantízale 20 leads en 7 días", "porque": base["consejos"][0]["porque"]}]}, "simulado")
        viv = IAm.consejo(luc, luc, cp_l, "mi-dia", con_ia=True)
        t = json.dumps(viv["consejos"], ensure_ascii=False)
        ok(viv["origen"] == "vivo" and "descuento" not in t and "garantíz" not in t and viv["consejos"][0].get("prioridad"),
           "Con clave · la IA no puede colar descuentos ni promesas: queda el texto de la regla, con su prioridad y criterio")
        cap = {}
        IAm.llamar = lambda sis, ctx, esq, effort="low", tarea=None: (cap.setdefault("ctx", ctx), ({"consejos": []}, "simulado"))[1]
        IAm.consejo(luc, luc, cp_l, "mi-dia", con_ia=True)
        cc = (cap.get("ctx") or {}).get("candidatos") or [{}]
        ok(all("puntos" in x and "motivo_orden" in x and "criterio" in x for x in cc) and "Respeta ese orden" in IAm.SISTEMA_CONSEJO,
           "Con clave · la IA recibe el razonamiento (puntos, motivo, diagnóstico, criterio) y la orden de respetarlo")
    finally:
        for k2, v2 in orig.items():
            setattr(IAm, k2, v2)

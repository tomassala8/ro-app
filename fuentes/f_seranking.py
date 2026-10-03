"""SE Ranking: proyecto (posiciones) de cada cliente.

Emparejado: por DOMINIO de la web del cliente contra la lista de proyectos (identificador = id del proyecto),
con excepciones en emparejamientos_manual.json → «seranking».
Lista de proyectos: en vivo con la clave de proyectos (seranking_project_key); si falla, la copia
del 2-oct leída con el conector del navegador (_muestras/seranking_proyectos_2026-10-02.json).

Posiciones: solo con la API de proyectos (no gasta créditos; la de datos sí y aquí NO se usa).
El 2-oct la clave del llavero devuelve 403 → la fuente queda «rota» hasta que Tomás pegue la clave buena
(bash ~/RO_HERRAMIENTAS/seranking/pegar.sh, la de «API de proyectos»).
"""
import importlib.util
import time

from comun import AQUI, HERR, MUESTRAS, bloque, dominio, edad_h, fecha, iso, leer, AHORA

MUESTRA = MUESTRAS / "seranking_proyectos_2026-10-02.json"
NOMBRE = "Posiciones en SE Ranking"
FREQ, LIM = 24, 30


def _sr():
    spec = importlib.util.spec_from_file_location("sr", HERR / "seranking" / "sr.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def cargar(universo, en_vivo=False):
    manual = {k: v for k, v in ((leer(AQUI / "emparejamientos_manual.json", {}) or {}).get("seranking") or {}).items()
              if not k.startswith("_")}
    error, plan, stats = None, None, {}
    proyectos, hora_lista = None, None
    if en_vivo:
        try:
            sr = _sr()
            r = sr.get("https://api4.seranking.com/sites", "seranking_project_key")
            if isinstance(r, dict) and "_error" in r:
                error = f"la clave de proyectos devuelve {r['_error']}"
            else:
                proyectos = [{"id": s.get("id"), "titulo": s.get("title"), "dominio": dominio(s.get("name")),
                              "activo": bool(s.get("is_active")), "palabras": s.get("keyword_count")} for s in r]
                hora_lista = AHORA
        except Exception as e:  # noqa: BLE001 — cualquier fallo del lector deja la fuente «rota», no la recarga
            error = f"lector sr.py: {type(e).__name__}"
    if proyectos is None:
        m = leer(MUESTRA, {}) or {}
        proyectos = m.get("proyectos", [])
        hora_lista = fecha((m.get("_meta") or {}).get("leido"))
        plan = "B · lista de proyectos del conector (2-oct), sin posiciones"
        if not en_vivo:
            error = "clave de proyectos rechazada (403) en la prueba del 2-oct; recarga sin --en-vivo seranking"
    else:
        plan = "A · API de proyectos en vivo"

    por_id = {p["id"]: p for p in proyectos}
    por_dom = {}
    for p in proyectos:
        if p.get("activo"):
            por_dom.setdefault(p["dominio"], p)
    for p in proyectos:
        por_dom.setdefault(p["dominio"], p)

    ex = {v.get("seranking") for k, v in ((leer(AQUI / "emparejamientos_manual.json", {}) or {}).get("ex_clientes") or {}).items()
          if not k.startswith("_")} | {9417974}   # 9417974 = proyecto de la propia RO
    bloques, con_dato, llamadas = {}, 0, 0
    for cid, u in universo.items():
        p = por_id.get(manual.get(cid)) if manual.get(cid) else None
        metodo = "emparejamientos_manual.json (id de proyecto)" if p else "dominio de la web"
        if not p:
            d = dominio(u.get("web"))
            p = por_dom.get(d) if d else None
        if not p:
            bloques[cid] = {"seranking": bloque(NOMBRE, "sin_conectar", nota="sin proyecto en SE Ranking con su dominio")}
            continue
        emparejado = {"id": p["id"], "nombre": p["titulo"], "metodo": metodo}
        datos = {"dominio": p["dominio"], "palabras_seguidas": p.get("palabras"), "proyecto_activo": p.get("activo")}
        if plan.startswith("A") and p.get("activo"):
            sr = _sr()
            st = sr.get(f"https://api4.seranking.com/sites/{p['id']}/stat", "seranking_project_key")
            llamadas += 1
            time.sleep(0.3)          # cupo de la API de proyectos: muy por debajo de 5 por segundo
            if isinstance(st, dict) and "_error" not in st:
                datos["resumen"] = st
                stats[cid] = True
        if stats.get(cid):
            estado, nota = "bien", None
            con_dato += 1
        elif not p.get("activo"):
            estado, nota = "a_cero", "proyecto pausado en SE Ranking"
        else:
            estado, nota = "rota", "proyecto emparejado; posiciones no disponibles (" + (error or "sin resumen") + ")"
        bloques[cid] = {"seranking": bloque(NOMBRE, estado, hora=iso(hora_lista), medicion="no" if estado == "rota" else "hoy",
                                            nota=nota, emparejado=emparejado, datos=datos)}

    emparejados = sum(1 for b in bloques.values() if b["seranking"]["emparejado"])
    ficha = {
        "id": "seranking", "nombre": NOMBRE, "grupo": "SEO",
        "origen": "API de proyectos de SE Ranking" if plan.startswith("A") else str(MUESTRA.relative_to(AQUI.parent)),
        "lector": "~/RO_HERRAMIENTAS/seranking/sr.py", "plan": plan, "error": error,
        "frecuencia_h": FREQ, "limite_h": LIM, "hora": iso(hora_lista), "edad_h": edad_h(hora_lista),
        "estado": "bien" if con_dato else "rota", "clientes_con_dato": con_dato,
        "clientes_emparejados": emparejados, "llamadas_api": llamadas,
        "proyectos_sin_cliente": [{"id": p["id"], "titulo": p["titulo"], "activo": p["activo"]} for p in proyectos
                                  if p["id"] not in ex and p["id"] not in {b["seranking"]["emparejado"]["id"] for b in bloques.values() if b["seranking"]["emparejado"]}],
    }
    return {"fichas": [ficha], "bloques": bloques}

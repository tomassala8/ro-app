#!/usr/bin/env python3
"""E1 · Capa de datos de la app de RO: un fichero por cliente con todas las fuentes ya conectadas.

Uso:
  python3 generar_datos.py                       # plan B: lee lo último que dejaron los lectores (0 llamadas a API)
  python3 generar_datos.py --en-vivo zoom,seranking
  python3 generar_datos.py --en-vivo todo        # externos.py, Windsor (si hay clave), SE Ranking y Zoom
Frecuencias previstas (04 §4, idea A10): cada hora ClickUp, Desk y Meta (los regenera el panel y captacion.py);
diario GA4, Search Console, SE Ranking, Windsor, Zoom y el libro.

Escribe (y nada más):
  ../data/clientes/<id>.json      un fichero por cliente (formato en FORMATO.md)
  ../data/indice_clientes.json    lista de clientes con cobertura por fuente
  ../data/fuentes.json            salud de las fuentes (bien · a cero · rota · dato viejo · sin conectar)
  ../data/emparejamientos.json    cliente ↔ cuenta de cada herramienta, por identificador
  dudas_emparejamiento.md         lo que tiene que mirar Agus
SOLO LECTURA de herramientas externas. Claves solo del llavero (las usan los lectores; aquí no se leen).
Puerta de secretos: si el escáner encuentra correos, teléfonos o claves, NO escribe nada y sale con error.
Fuente caída (auditoría 35, A5): si una fuente que estaba «bien» (o ya marcada caída) sale «sin_conectar»/«rota» o
pierde más de la mitad de sus clientes con dato (Meta caído, token caducado), NO se sobrescribe nada: se conserva el
último dato bueno, se marca «dato_viejo» con «caida» (desde, motivo) en fuentes.json y en cada ficha, y se sale con
el código 4 (la tubería lo entiende: aviso, sin restaurar y sin bloquear a los dependientes). Una baja a propósito:
--aceptar-caida meta,…
"""
import argparse
import json
import sys
from collections import Counter, defaultdict

sys.path.insert(0, __import__("os").path.dirname(__file__))

import f_captacion  # noqa: E402
import f_externos  # noqa: E402
import f_libro  # noqa: E402
import f_panel  # noqa: E402
import f_seranking  # noqa: E402
import f_windsor  # noqa: E402
import f_zoom  # noqa: E402
import universo as U  # noqa: E402
from comun import AHORA, AQUI, SALIDA, SALIDA_CLIENTES, enlace, escanear, escribir, iso, llano, sanear  # noqa: E402

VERSION_FORMATO = 1
CODIGO_CAIDA = 4          # = tuberia.CODIGO_CAIDA
CAIDA_MAX, MINIMO_ANTES = 0.5, 4
EN_VIVO_POSIBLES = ("externos", "meta", "windsor", "seranking", "zoom")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--en-vivo", default="", help="lista separada por comas o «todo»: " + ", ".join(EN_VIVO_POSIBLES))
    ap.add_argument("--sin-escribir", action="store_true", help="genera y escanea, pero no escribe")
    ap.add_argument("--aceptar-caida", default="", help="ids de fuente cuya caída es a propósito (se escriben igual)")
    a = ap.parse_args()
    aceptar = {x.strip() for x in a.aceptar_caida.split(",") if x.strip()}
    vivo = set(EN_VIVO_POSIBLES) if a.en_vivo == "todo" else {x.strip() for x in a.en_vivo.split(",") if x.strip()}

    universo, libro_sin_casar = U.construir()
    resultados = [
        f_panel.cargar(universo),
        f_externos.cargar(universo, en_vivo="externos" in vivo),
        f_captacion.cargar(universo, en_vivo="meta" in vivo),
        f_windsor.cargar(universo, en_vivo="windsor" in vivo),
        f_seranking.cargar(universo, en_vivo="seranking" in vivo),
        f_zoom.cargar(universo, en_vivo="zoom" in vivo),
        f_libro.cargar(universo),
    ]
    fichas = [f for r in resultados for f in r["fichas"]]
    for f in fichas:
        f["nota"] = llano(f.get("nota"))
    orden = [f["id"] for f in fichas]

    # ---------------------------------------------------------------- por cliente
    # N14 (2-oct-2026): hallazgos de medición que no se arreglan desde la app (etiqueta en la web, acceso, consentimiento).
    # Cada uno abierto entra como alerta «Medición: …» en el bloque de su fuente, con su dueño (y de ahí a N4).
    hall = (json.loads((SALIDA / "fuentes" / "hallazgos_medicion.json").read_text()).get("hallazgos") or []) \
        if (SALIDA / "fuentes" / "hallazgos_medicion.json").exists() else []
    hall_por_cliente = defaultdict(list)
    for h_ in hall:
        if h_.get("alerta_n4") and h_.get("gravedad") in ("rojo", "ambar"):   # los grises (falta un acceso) solo en la lista
            hall_por_cliente[h_["cliente_id"]].append(h_)
    clientes = {}
    for cid, u in universo.items():
        fuentes = {}
        for r in resultados:
            fuentes.update(r["bloques"].get(cid, {}))
        # saneado final de cualquier texto libre que haya quedado (motivos del libro, notas)
        for b in fuentes.values():
            b["nota"] = sanear(b["nota"])
            if isinstance(b.get("datos"), dict) and isinstance(b["datos"].get("motivo"), str):
                b["datos"]["motivo"] = sanear(b["datos"]["motivo"])
        fuentes = {k: fuentes[k] for k in orden if k in fuentes}
        completar(fuentes)
        for h_ in hall_por_cliente.get(cid, []):
            b_ = fuentes.get(h_["fuente"])
            if b_ is not None:
                b_.setdefault("alertas", [])
                if b_["alertas"] is None:
                    b_["alertas"] = []
                b_["alertas"].append({"gravedad": "rojo" if h_["gravedad"] == "rojo" else "ambar", "dueno": h_["dueno"],
                                      "texto": h_["texto"], "origen": "hallazgos de medición (N14)", "id": h_["id"]})
        medicion_web = [{"gravedad": "rojo" if h_["gravedad"] == "rojo" else "ambar", "dueno": h_["dueno"], "texto": h_["texto"],
                         "origen": "hallazgos de medición (N14)", "id": h_["id"], "fuente": h_["fuente"]}
                        for h_ in hall_por_cliente.get(cid, []) if h_["fuente"] not in fuentes]
        estados = Counter(b["estado"] for b in fuentes.values())
        clientes[cid] = {
            "formato": VERSION_FORMATO,
            "id": cid, "nombre": u["nombre"], "web": u.get("web"),
            "activo_libro": u.get("activo_libro"), "en_panel": u["en_panel"], "en_portal": u["en_portal"],
            "ids": u["ids"],
            "generado": iso(AHORA),
            "estado_fuentes": {k: b["estado"] for k, b in fuentes.items()},
            "alertas": [dict(a, fuente=k) for k, b in fuentes.items() for a in (b.get("alertas") or [])] + medicion_web,
            "cobertura": {"con_dato": estados["bien"] + estados["a_cero"] + estados["dato_viejo"],
                          "aplicables": sum(v for k, v in estados.items() if k != "no_aplica"),
                          **dict(estados)},
            "fuentes": fuentes,
        }

    # ------------------------------------------------------- emparejamientos
    emparejamientos, usos = {}, defaultdict(list)
    for cid, c in clientes.items():
        fila = {"nombre": c["nombre"], "ids": c["ids"]}
        for fid, b in c["fuentes"].items():
            e = b.get("emparejado")
            if e:
                fila[fid] = e
                if e.get("id") not in (None, ""):
                    for parte in str(e["id"]).split(", "):
                        usos[(fid, parte)].append(cid)
        emparejamientos[cid] = fila
    copiados = {f"{fid} {i}": cs for (fid, i), cs in usos.items() if len(cs) > 1}
    # ghl (resumen) y captacion_ghl (embudo) son la misma subcuenta: si difieren, es un error de emparejado
    ghl_distintos = {cid: [f.get("ghl", {}).get("id"), f.get("captacion_ghl", {}).get("id")] for cid, f in emparejamientos.items()
                     if f.get("ghl", {}).get("id") and f.get("captacion_ghl", {}).get("id")
                     and f["ghl"]["id"] != f["captacion_ghl"]["id"]}
    ghl_solo_uno = [cid for cid, f in emparejamientos.items() if bool((f.get("ghl") or {}).get("id")) != bool((f.get("captacion_ghl") or {}).get("id"))]

    # ---------------------------------------------------------- índice y fuentes
    indice = {
        "generado": iso(AHORA), "formato": VERSION_FORMATO,
        "total": len(clientes),
        "activos_libro": sum(1 for c in clientes.values() if c["activo_libro"] == "Activo"),
        "fuentes": orden,
        "clientes": [{"id": c["id"], "nombre": c["nombre"], "activo_libro": c["activo_libro"], "en_panel": c["en_panel"],
                      "fichero": f"clientes/{c['id']}.json", "cobertura": c["cobertura"], "estado_fuentes": c["estado_fuentes"]}
                     for c in sorted(clientes.values(), key=lambda x: x["nombre"].lower())],
    }
    for f in fichas:
        f["por_estado"] = dict(Counter(c["estado_fuentes"].get(f["id"]) for c in clientes.values()))
    fuentes_json = {"generado": iso(AHORA), "en_vivo": sorted(vivo), "fuentes": fichas,
                    "leyenda": {"bien": "dato reciente y con números", "a_cero": "conectada pero sin actividad",
                                "rota": "emparejada pero no responde o la clave falla", "dato_viejo": "pasado su límite de horas",
                                "sin_conectar": "no hay cuenta emparejada o no hay acceso", "no_aplica": "el cliente no tiene ese servicio"}}
    emp_json = {"generado": iso(AHORA), "regla": "siempre por identificador de la cuenta; nunca copiado de otro cliente",
                "copiados_entre_clientes": copiados,
                "ghl_distinto_entre_resumen_y_embudo": ghl_distintos, "ghl_en_un_solo_bloque": ghl_solo_uno,
                "clientes": emparejamientos}

    # ------------------------------------- cambios de emparejamiento desde la recarga anterior
    previo = (json.loads((SALIDA / "emparejamientos.json").read_text()).get("clientes") or {}) if (SALIDA / "emparejamientos.json").exists() else {}
    cambios = []
    for cid, fila in emparejamientos.items():
        for fid, e in fila.items():
            if fid in ("nombre", "ids") or not isinstance(e, dict):
                continue
            antes = ((previo.get(cid) or {}).get(fid) or {}).get("id")
            if previo.get(cid) is not None and antes != e.get("id") and antes is not None:
                cambios.append({"cliente": cid, "fuente": fid, "antes": antes, "ahora": e.get("id"), "metodo": e.get("metodo")})
    emp_json["cambios_desde_la_recarga_anterior"] = cambios

    # ----------------------------------------------------------- puerta de secretos
    hallazgos = escanear([clientes, indice, fuentes_json, emp_json])
    if hallazgos:
        print("PUERTA DE SECRETOS: no se escribe nada.")
        for h in hallazgos[:40]:
            print("  ", h)
        sys.exit(2)

    caidas = fuentes_caidas(fichas, aceptar)
    if caidas:
        print("FUENTE CAÍDA: no se sobrescribe nada; se queda el último dato bueno, marcado con su hora.")
        for fid, motivo, _ in caidas:
            print(f"   {fid}: {motivo}")
        if not a.sin_escribir:
            marcar_caidas(caidas)
        print("FUENTES_CAIDAS " + json.dumps([{"id": f, "motivo": m, "clientes_con_dato_bueno": n} for f, m, n in caidas], ensure_ascii=False))
        sys.exit(CODIGO_CAIDA)

    if a.sin_escribir:
        print("Escaneo limpio. --sin-escribir: no se escribe.")
        return
    for cid, c in clientes.items():
        escribir(SALIDA_CLIENTES / f"{cid}.json", c)
    escribir(SALIDA / "indice_clientes.json", indice)
    escribir(SALIDA / "fuentes.json", fuentes_json)
    escribir(SALIDA / "emparejamientos.json", emp_json)
    sobrantes = sorted(p.stem for p in SALIDA_CLIENTES.glob("*.json") if p.stem not in clientes)
    escribir_dudas(clientes, fichas, copiados, libro_sin_casar, sobrantes, ghl_distintos, cambios)

    print(f"{len(clientes)} clientes · {len(fichas)} fuentes · escaneo limpio · {iso(AHORA)}")
    for f in fichas:
        print(f"  {f['id']:14} {f['estado']:12} con dato {f['clientes_con_dato']:>3}  {f.get('plan', '')}")
    if copiados:
        print("  ¡OJO! emparejamientos repetidos entre clientes:", copiados)


def _por_que(antes, ahora_):
    """Motivo nunca vacío (R16b, misma regla que despliegue/tuberia.py · _por_que): lo que dice la fuente (error, error
    de la lectura directa, nota) y, si no dice nada, el hecho medible: con cuántos clientes estaba y está."""
    lectura = ahora_.get("lectura_directa") if isinstance(ahora_.get("lectura_directa"), dict) else {}
    for v in (ahora_.get("error"), lectura.get("error"), ahora_.get("nota")):
        texto = sanear(str(v)).strip() if v not in (None, "", "None") else ""
        if texto:
            return texto[:90]
    return (f"la fuente no dice por qué: tenía dato de {antes.get('clientes_con_dato') or 0} clientes y ahora de "
            f"{ahora_.get('clientes_con_dato') or 0}; última lectura {ahora_.get('hora') or 'sin hora'}")


def fuentes_caidas(fichas, aceptar=()):
    """Misma regla que la tubería (despliegue/tuberia.py · fuentes_caidas): [(id, motivo, clientes_con_dato_bueno)]."""
    try:
        antes = {x.get("id"): x for x in json.loads((SALIDA / "fuentes.json").read_text()).get("fuentes") or [] if isinstance(x, dict)}
    except Exception:
        return []
    ahora_ = {f["id"]: f for f in fichas}
    out = []
    for fid, x in antes.items():
        if fid in aceptar or not (x.get("estado") == "bien" or x.get("caida")):
            continue
        n_antes = x.get("clientes_con_dato") or 0
        b = ahora_.get(fid)
        if b is None:
            out.append((fid, "ha desaparecido de fuentes.json", n_antes))
        elif b.get("estado") in ("sin_conectar", "rota"):
            out.append((fid, f"pasa a «{b['estado']}» ({_por_que(x, b)})", n_antes))
        elif n_antes >= MINIMO_ANTES and (b.get("clientes_con_dato") or 0) < n_antes * (1 - CAIDA_MAX):
            out.append((fid, f"cae de {n_antes} a {b.get('clientes_con_dato') or 0} clientes con dato", n_antes))
    return out


def marcar_caidas(caidas):
    """En los ficheros que ya hay (el último dato bueno): la fuente caída pasa de «bien» a «dato_viejo» con «caida»."""
    hora = AHORA.strftime("%Y-%m-%d %H:%M")
    ids = {fid: m for fid, m, _ in caidas}

    def marca(b, fid):
        previa = b.get("caida") if isinstance(b.get("caida"), dict) else {}
        b["caida"] = {"desde": previa.get("desde") or hora, "comprobado": hora, "motivo": ids[fid],
                      "estado_antes": previa.get("estado_antes") or b.get("estado")}
        if b.get("estado") == "bien":
            b["estado"] = "dato_viejo"
    try:
        fj = json.loads((SALIDA / "fuentes.json").read_text())
        for x in fj.get("fuentes") or []:
            if isinstance(x, dict) and x.get("id") in ids:
                marca(x, x["id"])
        escribir(SALIDA / "fuentes.json", fj)
    except Exception as e:
        print("   no pude marcar fuentes.json:", type(e).__name__)
    for f in sorted(SALIDA_CLIENTES.glob("*.json")):
        try:
            d = json.loads(f.read_text())
        except Exception:
            continue
        tocado = False
        for fid in ids:
            b = (d.get("fuentes") or {}).get(fid)
            if isinstance(b, dict) and b.get("estado") not in (None, "no_aplica", "sin_conectar"):
                marca(b, fid)
                if isinstance(d.get("estado_fuentes"), dict) and fid in d["estado_fuentes"]:
                    d["estado_fuentes"][fid] = b["estado"]
                tocado = True
        if tocado:
            escribir(f, d)


def _num(x):
    return x if isinstance(x, (int, float)) else 0


def completar(fuentes):
    """Reglas que cruzan fuentes y atajos «Abrir en …» de los bloques del panel."""
    meta = fuentes.get("meta") or {}
    md = meta.get("datos") or {}
    gasto_meta = max(_num((md.get("gasto") or {}).get("mes_anterior")), _num((md.get("gasto") or {}).get("35d")),
                     _num((md.get("d30") or {}).get("gasto")))
    asig = fuentes.get("asignaciones") or {}
    serv = (asig.get("datos") or {}).get("servicios")
    if serv is not None and meta.get("emparejado") and gasto_meta > 0 and serv.get("publicidad") != "sí":
        serv["publicidad_antes"] = serv.get("publicidad")
        serv["publicidad"] = "sí"
        serv["publicidad_fuente"] = f"gasto en su cuenta de Meta ({gasto_meta:.2f} € en el último periodo)"
    # «Abrir en …» para los bloques que lo traen en su prueba o en un id
    def poner(fid, ab):
        if fid in fuentes and not fuentes[fid].get("abrir"):
            fuentes[fid]["abrir"] = ab
    d = lambda fid: (fuentes.get(fid) or {}).get("datos") or {}  # noqa: E731
    pr = lambda fid: (fuentes.get(fid) or {}).get("prueba")  # noqa: E731
    if pr("cartera"):
        poner("cartera", {"texto": "Abrir en ClickUp", "url": pr("cartera")})
    poner("tareas", enlace("clickup_carpeta", d("tareas").get("carpeta_id")))
    if pr("informes"):
        poner("informes", {"texto": "Abrir en ClickUp" if "clickup" in pr("informes") else "Abrir en Desk", "url": pr("informes")})
    tickets = d("desk").get("sin_contestar") or d("desk").get("sin_agente") or []
    if "desk" in fuentes:
        poner("desk", {"texto": "Abrir en Desk", "url": tickets[0]["url"]} if tickets else
              {"texto": "Abrir en Desk", "url": None, "falta": "Ningún correo pendiente"})
    poner("zadarma", enlace("zadarma", None))
    poner("chat", enlace("clickup_chat", d("chat").get("canal_id")))
    if "seranking" in fuentes:
        poner("seranking", enlace("seranking", ((fuentes["seranking"].get("emparejado") or {}).get("id"))))
    if "google_ads" in fuentes and fuentes["google_ads"]["estado"] != "no_aplica":
        poner("google_ads", enlace("google_ads", (fuentes["google_ads"].get("emparejado") or {}).get("id")))
    if "zoom" in fuentes and fuentes["zoom"]["estado"] == "bien":
        poner("zoom", enlace("zoom", None))
    if (fuentes.get("libro") or {}).get("estado") == "bien":
        poner("libro", enlace("holded", None))
    if pr("outreach"):
        poner("outreach", {"texto": "Abrir en ClickUp", "url": pr("outreach")})
    for b in fuentes.values():
        b["nota"] = llano(b.get("nota"))


def escribir_dudas(clientes, fichas, copiados, libro_sin_casar, sobrantes, ghl_distintos=None, cambios=None):
    L = [f"# Dudas de emparejamiento · para Agus\n\n**{iso(AHORA)}.** Las genera `generar_datos.py`. "
         "Se corrigen en `emparejamientos_manual.json` (por identificador) o en `universo.py` (alias del libro).\n"]
    if copiados:
        L.append("## Mismo identificador en dos clientes (posible dato copiado)\n")
        L += [f"- `{k}` → {', '.join(v)}" for k, v in copiados.items()]
        L.append("")
    if cambios:
        L.append("## Emparejamientos que han cambiado desde la recarga anterior (comprobar que el nuevo tiene datos)\n")
        L += [f"- {x['cliente']} · {x['fuente']}: `{x['antes']}` → `{x['ahora']}` ({x['metodo']})" for x in cambios]
        L.append("")
    if ghl_distintos:
        L.append("## Subcuenta de GHL distinta en el resumen y en el embudo\n")
        L += [f"- `{k}`: resumen {v[0]} · embudo {v[1]}" for k, v in ghl_distintos.items()]
        L.append("")
    m = next((f for f in fichas if f["id"] == "meta"), {})
    if m.get("cuentas_con_gasto_sin_cliente"):
        L.append("## Cuentas de Meta con más de 500 € en 30 días que no son de ningún cliente\n")
        L += [f"- {x['nombre']} (`{x['id']}`): {x['gasto_30d']} {x['moneda']}" for x in m["cuentas_con_gasto_sin_cliente"]]
        L.append("")
    pedir = {k: v for k, v in ((json.loads((AQUI / "emparejamientos_manual.json").read_text()).get("pedir_acceso")) or {}).items()
             if not k.startswith("_")}
    if pedir:
        L.append("## Accesos que pedir al cliente\n")
        L += [f"- **{clientes[k]['nombre'] if k in clientes else k}**: {v}" for k, v in pedir.items()]
        L.append("")
    L.append("## Activos en el libro sin cliente en la app\n")
    L += [f"- {x}" for x in libro_sin_casar] or ["- ninguno"]
    L.append("\n## Clientes de la app que no están en el libro corregido\n")
    L += [f"- {c['nombre']} (`{c['id']}`)" for c in clientes.values() if not c["ids"]["libro"]] or ["- ninguno"]
    g = next((f for f in fichas if f["id"] == "google_ads"), {})
    if g.get("cuentas_sin_cliente"):
        L.append("\n## Cuentas de Google Ads sin cliente\n")
        L += [f"- {x['nombre']} (`{x['id']}`), {x['coste']} € en el periodo" for x in g["cuentas_sin_cliente"]]
    s = next((f for f in fichas if f["id"] == "seranking"), {})
    activos_sin = [p for p in s.get("proyectos_sin_cliente", []) if p["activo"]]
    if activos_sin:
        L.append("\n## Proyectos activos de SE Ranking sin cliente (¿ex clientes que siguen gastando seguimiento?)\n")
        L += [f"- {p['titulo']} (`{p['id']}`)" for p in activos_sin]
    L.append("\n## Clientes con publicidad prevista o activa y sin cuenta de Meta emparejada\n")
    for c in clientes.values():
        serv = ((c["fuentes"].get("asignaciones") or {}).get("datos") or {}).get("servicios") or {}
        if serv.get("publicidad") in ("sí", "prevista") and c["estado_fuentes"].get("meta") == "sin_conectar":
            L.append(f"- {c['nombre']} (publicidad: {serv.get('publicidad')})")
    L.append("\n## GA4 emparejado y a cero en los últimos 30 días (¿etiqueta caída?)\n")
    L += [f"- {c['nombre']}" for c in clientes.values() if c["estado_fuentes"].get("ga4") == "a_cero"] or ["- ninguno"]
    L.append("\n## Search Console emparejado y a cero en 30 días (¿hay otro sitio del mismo dominio con datos, como pasó con Asetra?)\n")
    L += [f"- {c['nombre']} (`{(c['fuentes']['gsc'].get('emparejado') or {}).get('id')}`)" for c in clientes.values()
          if c["estado_fuentes"].get("gsc") == "a_cero"] or ["- ninguno"]
    if sobrantes:
        L.append("\n## Ficheros de cliente que ya no están en el universo (no se borran)\n")
        L += [f"- {x}" for x in sobrantes]
    (AQUI / "dudas_emparejamiento.md").write_text("\n".join(L) + "\n")


if __name__ == "__main__":
    main()

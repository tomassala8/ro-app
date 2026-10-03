#!/usr/bin/env python3
"""
fuentes_verdad/generar_verdad.py · UNA SOLA VERDAD POR CLIENTE (E0 ronda 5, revisión de calidad 22, mejora 1).

Problema: cada módulo calculaba a su manera «nuevo», «sin account», «sin reunión», «bloqueos», la gravedad…
y el mismo cliente contaba historias distintas según la pantalla (B-02, B-03, B-04, I-04, I-09).
Aquí se calcula UNA vez, con UNA definición escrita, y los módulos lo leen con ctx.verdad(clienteId).

Lee (solo lectura, 0 llamadas): data/clientes.json, asignaciones.json, alarmas.json, personas.json,
data/nuevos/nuevos.json, data/captacion/captacion.json, data/crm/crm.json, data/reuniones/reuniones.json,
data/produccion/produccion.json, data/horas/horas.json (los que existan).
Escribe:
  data/verdad/clientes.json   «comun» (todos: nombre, gravedad, motivo, responsable) + «clientes» (detalle por cliente_id)
  data/verdad/equipo.json     «no imputan ayer» con una definición única
Las definiciones van en «definiciones» dentro del propio fichero (y en el LEEME).
"""
import json
import re
from datetime import date
from pathlib import Path

AQUI = Path(__file__).resolve().parent.parent
DATA = AQUI / "data"
SALIDA = DATA / "verdad"

DEFINICIONES = {
    "cuota": "Cuota mensual sin IVA del cliente: fuentes_dinero/cuotas.json (Airtable de octubre de Sofía; si no hay línea, su factura de octubre en Holded). La misma en toda la app.",
    "cuota_empresa": "Cuota del mes de la agencia, de la MISMA fuente: recurrente (sin proyectos con fin), cuota del mes (todo) y facturable (con los ajustes del mes de Finanzas). Octubre: 67.291 · 70.781 · 70.581 €.",
    "account": "El account principal vigente de la tabla de asignaciones (fase 0 + respuestas de Mili + Ajustes). Si no hay, null y «sin_account».",
    "equipo": "Personas por silla vigentes en asignaciones (responsable primero).",
    "nuevo": "Cliente con alta firmada en los últimos 90 días: está en «Clientes nuevos» (data/nuevos/nuevos.json → altas). Misma lista en todas las pantallas.",
    "dia_alta": "Días desde el alta del contrato (no desde la firma).",
    "encendido": "Fecha (día desde el alta) en que se encendió la campaña y si fue en plazo (día 10; límite 12, D-28): en_plazo · tarde · sin_encender_fuera_de_plazo · pendiente_en_plazo.",
    "campana_activa": "Hay campaña de Meta activa (Captación).",
    "leads_meta_7d / leads_ghl_7d": "Leads de Meta y leads que llegaron a GoHighLevel en 7 días (Salud del CRM).",
    "fuga_integracion": "grave si Meta da 10 o más leads en 7 días y a GoHighLevel llega menos de la mitad; leve si llega menos del 80 %.",
    "sin_reunion_mes_pasado": "Ninguna reunión el mes pasado según CRM, Fathom y Zoom (Reuniones), salvo exentos y altas del propio mes.",
    "bloqueos": "Tareas del cliente en «bloqueado» (Producción). «bloqueo_callado» = la más antigua lleva más de 5 días. «tarea_id» = id de ClickUp de la más antigua (para el «Ir»).",
    "correos_sin_responder": "Correos del cliente sin contestar y días laborables del más antiguo (Desk, alarma «Sin responder»).",
    "gravedad": "crítico · atención · bien (ver «reglas_gravedad»). Una fuga de integración grave NUNCA es «bien».",
    "salud": "0-100 provisional con la D-02: 40 puntos de resultados del cliente, 30 de atención y 30 de arranque. Sello «a medias».",
    "cartera": "R12 · Cartera de una persona en una silla = clientes con su fila vigente en asignaciones. «principal» = lleva el cliente; «apoyo» = ayuda (no es dueño). Cada pantalla cuenta su universo SOBRE esta cartera y dice cuántos quedan fuera y por qué (sin cuenta de Meta, sin subcuenta de GoHighLevel, sin marca en Metricool, sin web en el monitor). Metricool, Meta o GoHighLevel nunca deciden quién lleva un cliente.",
    "web_unica": "R12 · Una sola persona de web por cliente: la principal de asignaciones. Las bajas no están en ningún equipo.",
    "no_imputan_ayer": "Personas activas que imputan horas (sin dudosas, bajas ni setters) con 0 h el último día laborable (Horas).",
}
REGLAS_GRAVEDAD = {
    "critico": [
        "fuga de integración grave (≥ 10 leads de Meta en 7 días y llega menos de la mitad a GoHighLevel)",
        "alta pasada del día 12 sin encender",
        "correos del cliente sin contestar más de 10 días laborables Y otra señal de relación en riesgo (sin reunión el mes pasado, semáforo del account en crítico o captación en crítico)",
        "100 € o más en Meta en 7 días y 0 leads",
    ],
    "atencion": [
        "correos sin contestar más de 48 h (sin otra señal de riesgo)",
        "sin reunión el mes pasado", "bloqueo callado más de 5 días", "sin account",
        "captación en crítico o atención por publicidad o seguimiento", "semáforo del account en crítico",
        "alta encendida tarde", "fuga de integración leve",
    ],
    "bien": ["nada de lo anterior"],
}


# Motivo de la lista común (D-90: todos ven la lista con motivo y responsable): sin cifras ni euros.
MOTIVO_COMUN = {"integracion": "Los leads no llegan al CRM", "arranque": "Alta fuera de plazo", "respuesta": "Correos del cliente sin contestar",
                "publicidad": "Gasto en publicidad sin leads", "reunion": "Sin reunión el mes pasado", "bloqueo": "Tareas bloqueadas",
                "account": "Sin account asignado", "captacion": "Captación con problemas", "semaforo": "Su account lo marca en crítico"}


def leer(rel, defecto=None):
    p = DATA / rel
    try:
        return json.loads(p.read_text())
    except Exception:
        return defecto


def main():
    hoy = date.today().isoformat()
    clientes = leer("clientes.json", [])
    asig = leer("asignaciones.json", [])
    alarmas = leer("alarmas.json", [])
    personas = {p["id"]: p for p in leer("personas.json", [])}
    nuevos = {a["cliente_id"]: a for a in (leer("nuevos/nuevos.json", {}) or {}).get("altas", [])}
    cap = {c["cliente_id"]: c for c in (leer("captacion/captacion.json", {}) or {}).get("clientes", []) if c.get("cliente_id")}
    crm = {s["cliente_id"]: s for s in (leer("crm/crm.json", {}) or {}).get("subcuentas", []) if s.get("cliente_id")}
    reu = {c["cliente_id"]: c for c in (leer("reuniones/reuniones.json", {}) or {}).get("clientes", [])}
    _prod_doc = leer("produccion/produccion.json", {}) or {}
    prod = {p["cliente_id"]: p for p in _prod_doc.get("proyectos", []) if p.get("cliente_id")}
    # R15a (A2 · verdad única): id de ClickUp de la tarea bloqueada más antigua de cada cliente, para que el «Ir» de
    # «Desbloquea la tarea parada» llegue a su fila en Producción (#/produccion/tarea/<id>).
    bloqueada_mas_antigua = {}
    for r in _prod_doc.get("cola") or []:
        if r.get("grupo") == "bloqueada" and r.get("cli") and r.get("id"):
            prev = bloqueada_mas_antigua.get(r["cli"])
            if prev is None or (r.get("dias_estado") or 0) > (prev.get("dias_estado") or 0):
                bloqueada_mas_antigua[r["cli"]] = r
    fuentes_usadas = {k: v is not None and v != {} for k, v in
                      (("nuevos", nuevos), ("captacion", cap), ("crm", crm), ("reuniones", reu), ("produccion", prod))}

    def vigente(a):
        return (not a.get("desde") or a["desde"] <= hoy) and (not a.get("hasta") or a["hasta"] >= hoy)

    de_baja = {pid for pid, p in personas.items() if p.get("estado") == "baja" or (not p.get("activo") and p.get("estado") != "dudoso")}

    comun, detalle = [], []
    for c in clientes:
        cid = c["id"]
        equipo = {}
        for a in asig:
            if a["cliente_id"] == cid and vigente(a) and a.get("persona_id") not in de_baja:   # R12: bajas fuera de todo equipo
                equipo.setdefault(a["silla"], []).append({"persona_id": a["persona_id"], "principal": a.get("principal", True), "suplencia": bool(a.get("suplencia"))})
        account = next((x["persona_id"] for x in equipo.get("account", []) if x["principal"] and not x["suplencia"]), None)

        n = nuevos.get(cid)
        encendido = None
        if n:
            pl = n.get("plazo") or {}
            dia_enc = pl.get("dia_encendido")
            if dia_enc is not None:
                encendido = {"dia": dia_enc, "estado": "en_plazo" if dia_enc <= 10 else "en_limite" if dia_enc <= 12 else "tarde"}
            else:
                encendido = {"dia": None, "estado": "sin_encender_fuera_de_plazo" if (n.get("dia") or 0) > 12 else "pendiente_en_plazo"}

        k = cap.get(cid) or {}
        s = crm.get(cid) or {}
        lm, lg = s.get("leads_meta_7d"), s.get("leads_ghl_7d")
        fuga = None
        if lm is not None and lg is not None and lm >= 10:
            pct = (lg or 0) / lm if lm else 1
            fuga = {"grave": pct < 0.5, "leve": 0.5 <= pct < 0.8, "pct_llega": round(pct * 100), "texto": f"Meta {int(lm)} leads en 7 días y a GoHighLevel llegaron {int(lg or 0)}"}
            if not fuga["grave"] and not fuga["leve"]:
                fuga = None

        r = reu.get(cid) or {}
        sin_reunion = r.get("estado") == "sin_reunion"
        p = prod.get(cid) or {}
        _bl = bloqueada_mas_antigua.get(cid) or {}
        bloqueos = {"tareas": p.get("bloqueadas") or 0, "dias_max": p.get("bloqueo_max") or 0,
                    "tarea_id": _bl.get("id"), "tarea": _bl.get("tarea"), "tarea_persona_id": _bl.get("persona_id")}
        bloqueo_callado = (p.get("bloqueo_max") or 0) > 5

        mis_al = [a for a in alarmas if a.get("cliente_id") == cid]
        sin_resp = next((a for a in mis_al if a["tipo"] == "Sin responder"), None)
        dias_sin_resp = None
        if sin_resp:
            m = re.search(r"lleva (\d+) días laborables", sin_resp.get("texto") or "")
            dias_sin_resp = int(m.group(1)) if m else 3
        gasto7 = ((k.get("gasto") or {}).get("7d")) if isinstance(k.get("gasto"), dict) else None
        leads7 = ((k.get("leads") or {}).get("7d")) if isinstance(k.get("leads"), dict) else None

        criticos, atencion = [], []
        if fuga and fuga["grave"]:
            criticos.append(("integracion", f"Fuga de integración: {fuga['texto']}"))
        if encendido and encendido["estado"] == "sin_encender_fuera_de_plazo":
            criticos.append(("arranque", f"Alta en el día {n.get('dia')} sin encender (límite: día 12)"))
        riesgo = ("sin reunión el mes pasado" if sin_reunion else "su account lo marca en crítico" if c.get("semaforo") == "crítico"
                  else "captación en crítico" if k.get("severidad") == "critico" else None)
        if dias_sin_resp is not None and dias_sin_resp > 10 and riesgo:
            criticos.append(("respuesta", f"Correos sin contestar desde hace {dias_sin_resp} días laborables y {riesgo}"))
        if gasto7 is not None and gasto7 >= 100 and not leads7:
            criticos.append(("publicidad", "100 € o más gastados en Meta en 7 días y 0 leads"))
        elif dias_sin_resp is not None:
            atencion.append(("respuesta", f"Correos sin contestar desde hace {dias_sin_resp} días laborables"))
        if sin_reunion:
            atencion.append(("reunion", "Sin reunión el mes pasado"))
        if bloqueo_callado:
            atencion.append(("bloqueo", f"Bloqueo callado: {bloqueos['dias_max']} días"))
        if not account and c.get("sin_account") != "mantenimiento sin account":
            atencion.append(("account", "Sin account asignado"))
        if k.get("severidad") in ("critico", "atencion") and set(k.get("cuello") or []) - {"integracion"}:
            atencion.append(("captacion", "Captación con problemas de publicidad o seguimiento"))
        if c.get("semaforo") == "crítico":
            atencion.append(("semaforo", "Su account lo marca en crítico"))
        if encendido and encendido["estado"] == "tarde":
            atencion.append(("arranque", f"Encendida tarde (día {encendido['dia']})"))
        if fuga and fuga["leve"]:
            atencion.append(("integracion", f"Llega a GoHighLevel el {fuga['pct_llega']} % de los leads"))
        gravedad = "critico" if criticos else "atencion" if atencion else "bien"
        motivos = [t for _, t in criticos + atencion]
        claves = [k_ for k_, _ in criticos + atencion]

        # Salud provisional D-02 (a medias): 40 resultados · 30 atención · 30 arranque
        res = 40 - (40 if fuga and fuga["grave"] else 0) - (25 if gasto7 and gasto7 >= 100 and not leads7 else 0) \
            - (15 if k.get("severidad") == "critico" and not (fuga and fuga["grave"]) else 8 if k.get("severidad") == "atencion" else 0) - (10 if fuga and fuga["leve"] else 0)
        ate = 30 - (20 if dias_sin_resp and dias_sin_resp > 5 else 10 if dias_sin_resp else 0) - (10 if sin_reunion else 0) - (10 if c.get("semaforo") == "crítico" else 0)
        arr = 30 - (30 if encendido and encendido["estado"] == "sin_encender_fuera_de_plazo" else 10 if encendido and encendido["estado"] == "tarde" else 0) \
            - (10 if not account else 0) - (10 if bloqueo_callado else 0)
        salud = max(0, min(40, res)) + max(0, min(30, ate)) + max(0, min(30, arr))

        resp = account or None
        comun.append({"id": cid, "nombre": c["nombre"], "gravedad": gravedad, "motivo": MOTIVO_COMUN.get(claves[0]) if claves else None,
                      "n_motivos": len(motivos), "responsable_id": resp,
                      "sin_account": None if account else (c.get("sin_account") or "sin account"), "nuevo": bool(n)})
        detalle.append({
            "cliente_id": cid, "nombre": c["nombre"], "account": account, "equipo": equipo,
            "sin_account": None if account else (c.get("sin_account") or "sin account"),
            "nuevo": bool(n), "alta": n.get("alta") if n else c.get("alta"), "dia_alta": n.get("dia") if n else None,
            "encendido": encendido, "campana_activa": k.get("meta_activa"),
            "leads_meta_7d": lm, "leads_ghl_7d": lg, "fuga_integracion": fuga,
            "sin_reunion_mes_pasado": sin_reunion, "reunion_estado": r.get("estado"), "ultima_reunion": r.get("ultima"),
            "bloqueos": bloqueos, "bloqueo_callado": bloqueo_callado,
            "correos_sin_responder_dias": dias_sin_resp,
            "gravedad": gravedad, "motivos": motivos, "salud": salud, "salud_sello": "a medias (fórmula provisional D-02)",
            # Ronda 8: cuota de la fuente única (fuentes_dinero/cuotas.json vía build_data). Dato sensible: el servidor
            # la quita fila a fila a quien no ve la cuota de ese cliente (claves cuota*).
            "cuota": c.get("cuota"), "cuota_fuente": c.get("cuota_fuente"),
        })

    # Equipo: no imputan ayer, con una sola definición
    h = leer("horas/horas.json", {}) or {}
    no_imputan, cuentan = [], []
    for p in h.get("personas", []):
        pp = personas.get(p["persona_id"], {})
        if p.get("estado_persona") != "activo" or pp.get("imputa_horas") == "no" or "setters" in (pp.get("puestos") or []):
            continue
        cuentan.append(p["persona_id"])
        if not p.get("ayer"):
            no_imputan.append(p["persona_id"])

    # R12 · carteras por persona y silla (una sola definición) + el universo de cada pantalla sobre esa cartera.
    universos = {
        "trafficker": ("con cuenta de Meta en Captación", set(cap)),
        "crm": ("con subcuenta de GoHighLevel en Salud del CRM", set(crm)),
        "redes": ("con marca conectada en Metricool", {f.get("cliente_id") for f in (leer("redes/redes.json", {}) or {}).get("clientes", [])}),
        "web": ("con web en el monitor", {w.get("cliente") for w in (leer("seo/webs.json", {}) or {}).get("webs", [])}),
    }
    nombre_cli = {c["id"]: c["nombre"] for c in clientes}
    carteras = {}
    for a in asig:
        if not vigente(a) or a.get("persona_id") in de_baja or a["cliente_id"] not in nombre_cli:
            continue
        pp = personas.get(a["persona_id"]) or {}
        if not pp.get("activo"):
            continue
        k = (a["persona_id"], a["silla"])
        fila = carteras.setdefault(k, {"persona_id": a["persona_id"], "silla": a["silla"], "principal": set(), "apoyo": set()})
        fila["principal" if a.get("principal", True) and not a.get("suplencia") else "apoyo"].add(a["cliente_id"])
    filas_cartera = []
    for (pid, silla), f in sorted(carteras.items()):
        f["apoyo"] -= f["principal"]
        pr = sorted(f["principal"], key=lambda x: nombre_cli[x])
        ap = sorted(f["apoyo"], key=lambda x: nombre_cli[x])
        fila = {"persona_id": pid, "silla": silla, "n_principal": len(pr), "n_apoyo": len(ap), "principal": pr, "apoyo": ap}
        if silla in universos:
            texto, dentro = universos[silla]
            fuera = [x for x in pr if x not in dentro]
            fila["universo"] = {"que": texto, "dentro": len(pr) - len(fuera), "fuera": fuera,
                                "texto": f"{len(pr) - len(fuera)} de tus {len(pr)} clientes {texto}"
                                         + (f"; fuera: {', '.join(nombre_cli[x] for x in fuera)}" if fuera else "")}
        filas_cartera.append(fila)

    SALIDA.mkdir(parents=True, exist_ok=True)
    resumen = {g: sum(1 for x in comun if x["gravedad"] == g) for g in ("critico", "atencion", "bien")}
    out = {"generado": hoy, "definiciones": DEFINICIONES, "reglas_gravedad": REGLAS_GRAVEDAD, "fuentes_usadas": fuentes_usadas,
           "resumen": {**resumen, "nuevos": sum(1 for x in comun if x["nuevo"]), "sin_account": sum(1 for x in comun if x["sin_account"]),
                       "sin_reunion_mes_pasado": sum(1 for x in detalle if x["sin_reunion_mes_pasado"]),
                       "bloqueo_callado": sum(1 for x in detalle if x["bloqueo_callado"])},
           "comun": comun, "clientes": detalle, "carteras": filas_cartera}
    # Ronda 9 (D-P-DIN): cuota de la empresa del mes con la misma fuente que la de cada cliente (build_data.cuota_empresa).
    # La clave empieza por «cuota_»: el servidor la quita a quien no ve la cuota (solo dirección, operaciones, proyectos y administración).
    try:
        import importlib.util, sys
        sys.path.insert(0, str(AQUI))
        spec = importlib.util.spec_from_file_location("build_data", AQUI / "build_data.py")
        bd = importlib.util.module_from_spec(spec); spec.loader.exec_module(bd)
        out["cuota_empresa"] = bd.cuota_empresa()
    except Exception as e:   # sin la cifra, la verdad sigue
        out["cuota_empresa"] = {"error": f"no se pudo leer fuentes_dinero/cuotas.json: {e}"}
    eq = {"generado": hoy, "ayer": h.get("ayer"), "definicion": DEFINICIONES["no_imputan_ayer"],
          "cuentan": len(cuentan), "no_imputan_ayer": [{"persona_id": x} for x in no_imputan]}
    for nombre, obj in (("clientes.json", out), ("equipo.json", eq)):
        tmp = SALIDA / f".{nombre}.tmp"
        tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=1))
        tmp.replace(SALIDA / nombre)
    print(f"verdad: {len(comun)} clientes · crítico {resumen['critico']} · atención {resumen['atencion']} · bien {resumen['bien']} · "
          f"nuevos {out['resumen']['nuevos']} · sin account {out['resumen']['sin_account']} · no imputan ayer {len(no_imputan)} de {len(cuentan)}")


if __name__ == "__main__":
    main()

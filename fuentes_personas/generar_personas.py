#!/usr/bin/env python3
"""M20 Personas · genera data/personas_m20/equipo.json y data/personas_m20/contratacion.json (solo lectura).

Fuentes (nada se escribe fuera):
  · data/personas.json y data/asignaciones.json (E0)            → quién es quién, jefe, cartera por silla
  · PANEL_OPERACIONES_2026-10-01/build/datos.json → v7          → horas por día (ClickUp, cu.py), personas en alerta,
                                                                   horas raras (sin el cliente: D-84)
  · ~/Downloads/PLAN_FICHAJES_Q4_2026/plan_fichajes_q4.html      → plan de fichajes del cuarto trimestre (28-sep)
  · local.db (acciones simuladas de este módulo)                 → ausencias, notas, 1:1 y planes apuntados en la app

Privacidad: sin sueldos (no hay ningún campo de dinero). Cada fila lleva persona_id, así servir.py solo la manda a la
persona, su jefe, operaciones, RRHH y dirección (regla horas_persona/notas_persona/alarma_persona, D-83).
Contratación va en un fichero aparte, que solo leen quienes ven Ajustes (Mili, Tomás y Cecilia).
"""
import json, re, sqlite3, sys
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comun import APP, BUILD, DATA, emparejador, escribir, personas  # noqa: E402

from zoneinfo import ZoneInfo
HOY = datetime.now(ZoneInfo("Europe/Madrid")).date()   # «ayer» = último laborable de Madrid (misma definición que Horas/verdad)
CAP = {"account": 12, "trafficker": 16, "crm": 16}
AVISO = {"account": 7, "trafficker": 14, "crm": 14}     # D-07: aviso con ≤ 5 huecos (12) y desde 14 (16)


ES_HORAS = re.compile(r"imput[óo]|registros? de horas|\bh la semana", re.I)   # R12: motivos de horas = aviso
ES_CORREOS = re.compile(r"correos? de \+?48", re.I)

def laborables(desde, hasta):
    d, out = desde, []
    while d <= hasta:
        if d.weekday() < 5:
            out.append(d)
        d += timedelta(days=1)
    return out


def main():
    datos = json.loads((BUILD / "datos.json").read_text())
    v7 = datos["v7"]
    corte = v7["horas_dia"].get("corte") or datos.get("generado")
    buscar = emparejador()
    ps = [p for p in personas() if p["estado"] != "baja"]
    ids = {p["id"] for p in ps}

    # ---- horas por día (ClickUp) ----
    horas = defaultdict(dict)
    sin_emparejar = []
    for nombre, dias in v7["horas_dia"]["personas"].items():
        pid = buscar(nombre)
        if pid in ids:
            for d, h in dias.items():
                horas[pid][d] = horas[pid].get(d, 0) + h
        else:
            sin_emparejar.append(nombre)
    ayer = HOY - timedelta(days=1)
    while ayer.weekday() >= 5:
        ayer -= timedelta(days=1)
    # «No imputan ayer»: definición única = la de Horas (data/horas/horas.json, panel de horas de ClickUp más reciente),
    # que es la que usa la verdad. El panel v7 solo cubre si Horas no existe o es de otro día.
    horas_unica = {}
    try:
        hj = json.loads((DATA / "horas" / "horas.json").read_text())
        if hj.get("hoy") == HOY.isoformat():
            horas_unica = {x["persona_id"]: x for x in hj.get("personas", [])}
    except Exception:
        pass
    lunes = HOY - timedelta(days=HOY.weekday())
    lab_semana = laborables(lunes, ayer) if ayer >= lunes else []
    ult5 = [d for d in laborables(HOY - timedelta(days=10), ayer)][-5:]
    mes_ant = (HOY.replace(day=1) - timedelta(days=1))
    pref_ant, pref_act = mes_ant.strftime("%Y-%m"), HOY.strftime("%Y-%m")

    # ---- personas en alerta (panel v7) ----
    alerta = {}
    for a in v7.get("alerta", []):
        pid = buscar(a["persona"])
        if pid in ids:
            alerta[pid] = a
    # Desde cuándo: primera foto diaria del panel o de la app en la que aparece (hoy solo hay fotos desde el 2-oct).
    desde_alerta = {}
    fotos = sorted(list((BUILD / "fotos").glob("*.json")) + list((APP / "historia").glob("*/datos.json")))
    for f in fotos:
        try:
            fecha = re.search(r"(\d{4}-\d{2}-\d{2})", str(f)).group(1)
            doc = json.loads(f.read_text())
            lista = (doc.get("v7") or {}).get("alerta") or doc.get("alerta") or []
            for a in lista:
                pid = buscar(a.get("persona"))
                if pid and pid not in desde_alerta:
                    desde_alerta[pid] = fecha
        except Exception:
            pass

    # ---- horas raras (sin cliente: RRHH ve el cliente solo en agregado, D-84) ----
    raras = Counter()
    for a in v7.get("anomalias", []):
        pid = buscar(a.get("persona"))
        if pid in ids:
            raras[pid] += 1

    # ---- cartera por silla (asignaciones vigentes) ----
    hoy_s = HOY.isoformat()
    cartera = defaultdict(Counter)
    for a in json.loads((DATA / "asignaciones.json").read_text()):
        if (not a.get("desde") or a["desde"] <= hoy_s) and (not a.get("hasta") or a["hasta"] >= hoy_s) and not a.get("suplencia"):
            silla = "crm" if a["silla"] == "ghl" else a["silla"]
            cartera[a["persona_id"]][silla] += 1

    # ---- lo apuntado en la app (cola simulada de local.db) ----
    apuntes = defaultdict(list)
    db = APP / "local.db"
    if db.exists():
        con = sqlite3.connect(db)
        con.row_factory = sqlite3.Row
        for r in con.execute("SELECT * FROM acciones WHERE tipo LIKE 'personas_%' ORDER BY id"):
            try:
                vp = json.loads(r["vista_previa"] or "null") or {}
            except Exception:
                vp = {}
            pid = vp.get("persona_id") or r["objeto"]
            if pid in ids:
                apuntes[pid].append({"id": r["id"], "tipo": r["tipo"].replace("personas_", ""), "creada": r["creada"], "quien": r["quien"],
                                     "texto": r["texto"], "datos": vp, "estado": r["estado"]})
        con.close()

    filas = []
    for p in ps:
        hd = horas.get(p["id"], {})
        imputa = p.get("imputa_horas") == "sí" and "setters" not in p["puestos"]   # misma regla que Horas: los setters no imputan en ClickUp
        ayer_h = round(hd.get(ayer.isoformat(), 0), 1)
        ayer_f = ayer.isoformat()
        hu = horas_unica.get(p["id"])
        if hu is not None:
            ayer_h, ayer_f = round(hu.get("ayer") or 0, 1), hu.get("ayer_fecha") or ayer_f
        sem_h = round(sum(hd.get(d.isoformat(), 0) for d in lab_semana), 1)
        sin_imputar = [d.isoformat() for d in ult5 if hd.get(d.isoformat(), 0) == 0]
        mes_h = round(sum(h for d, h in hd.items() if d.startswith(pref_ant)), 1)
        act_h = round(sum(h for d, h in hd.items() if d.startswith(pref_act)), 1)
        ult = max(hd) if hd else None
        horas_mes = p.get("horas_mes") or 128
        car = {s: n for s, n in cartera.get(p["id"], {}).items()}
        sobre = [s for s, n in car.items() if s in CAP and n > CAP[s]]
        cerca = [s for s, n in car.items() if s in CAP and AVISO[s] <= n <= CAP[s]]
        a = alerta.get(p["id"])
        ap = apuntes.get(p["id"], [])
        # R12 · regla de Tomás (D-27): las horas imputadas son SOLO aviso, nunca alerta. Se separan los motivos de horas
        # («imputó X h», «registros de horas fuera de lo normal») y la alerta queda solo con señales reales (tareas
        # arrastradas, revisiones de +48 h, correos de +48 h de clientes que lleva HOY como account).
        motivos_reales, avisos_horas = [], []
        for m in (a or {}).get("motivos", []):
            if ES_HORAS.search(m):
                avisos_horas.append(m)
            elif ES_CORREOS.search(m) and not car.get("account"):
                avisos_horas.append(m + " (de una cartera de account que ya no lleva)")
            else:
                motivos_reales.append(m)
        filas.append({
            "persona_id": p["id"], "nombre": p["nombre"], "alias": p.get("alias") or p["nombre"].split()[0],
            "puestos": p["puestos"], "jefe": p.get("jefe"), "estado": p["estado"], "imputa": imputa,
            "horas": {
                "ayer": ayer_h, "ayer_fecha": ayer_f, "ayer_fuente": "Horas (definición única)" if hu is not None else "panel v7", "semana": sem_h, "semana_dias": len(lab_semana),
                "dias_sin_imputar_5": sin_imputar, "mes_anterior": mes_h, "mes_anterior_txt": mes_ant.strftime("%Y-%m"),
                "mes_actual": act_h, "ultimo_dia_con_horas": ult, "disponibles": horas_mes,
                "pct_128": round(mes_h / horas_mes * 100) if horas_mes else None,
                "semana_pasada": next((x["h_ant"] for x in v7.get("personas", []) if buscar(x["nombre"]) == p["id"]), None),
            } if imputa else {"no_imputa": True, "motivo": "No imputa horas (Ajustes › Personas)."},
            "cartera": car, "sobre_capacidad": sobre, "cerca_capacidad": cerca,
            "alerta": {"motivos": motivos_reales, "peso": len(motivos_reales), "desde": desde_alerta.get(p["id"], HOY.isoformat()),
                       "fuente": "Panel de operaciones v7 · personas en alerta (sin los motivos de horas: son aviso)"} if motivos_reales else None,
            "avisos": avisos_horas,
            "horas_raras": raras.get(p["id"], 0),
            "apuntes": ap,
        })

    equipo = {
        "_meta": {
            "generado": datetime.now().strftime("%Y-%m-%d %H:%M"), "corte_horas": corte,
            "fuentes": {
                "horas": "ClickUp (cu.py) vía panel v7 · horas_dia",
                "alerta": "Panel v7 · personas en alerta (motivos del panel; las horas pasan a «avisos», D-27)",
                "cartera": "data/asignaciones.json (E0)",
                "apuntes": "local.db · acciones simuladas de M20 (ausencias, notas, 1:1, planes)",
            },
            "capacidad": {"horas_mes": 128, "proyectos": CAP, "origen": "D-07 · D-25"},
            "sin_emparejar": sin_emparejar,
            "nota": "Sin sueldos ni dinero. Horas solo como aviso (D-27): imputación del equipo 51,7 %.",
            "ronda_jefas": ronda_jefas(),
        },
        "personas": filas,
        "ausencias": [],   # tabla propia: se llena desde el formulario (simulado) → local.db
    }
    escribir("personas_m20/equipo.json", equipo)
    escribir("personas_m20/contratacion.json", contratacion())
    print(f"personas/equipo.json: {len(filas)} personas · {sum(1 for f in filas if f['alerta'])} en alerta · sin emparejar: {sin_emparejar}")


def ronda_jefas():
    """Ronda quincenal con las jefas (encargo de Tomás a Cecilia del 13-ago, D-74)."""
    d = date(2026, 8, 13)
    while d < date.today():
        d += timedelta(days=14)
    return {"proxima": d.isoformat(), "cada_dias": 14, "origen": "encargo a Cecilia 13-ago · D-74", "registradas": 0}


def contratacion():
    from comun import config  # C5: rutas en config.py
    f = config.PLAN_FICHAJES
    existe = f.exists()
    return {
        "_meta": {"fuente": "Downloads/PLAN_FICHAJES_Q4_2026/plan_fichajes_q4.html (28-sep, borrador para Operaciones)",
                  "leido": existe, "generado": datetime.now().strftime("%Y-%m-%d %H:%M"),
                  "nota": "El plan existe; el seguimiento de candidatos lo rellena Cecilia el lunes (exigencia 36). Sin sueldos."},
        "resumen": {"traffickers": 7, "crm": 3, "accounts": 0,
                    "texto": "Para llegar a final de año con las altas previstas: +7 traffickers y +3 especialistas de CRM. Accounts: 0 (sobra capacidad; reconvertir 1 o 2 a trafficker)."},
        "vacantes": [
            {"id": "traf-ola1", "puesto": "Trafficker", "plazas": 4, "oleada": 1, "abre": "2026-09-29", "entra": "2026-10-13", "lleva_cuentas": "2026-10-20", "candidatos": None, "fase": "publicar"},
            {"id": "crm-ola1", "puesto": "Especialista de CRM", "plazas": 2, "oleada": 1, "abre": "2026-09-29", "entra": "2026-10-13", "lleva_cuentas": "2026-10-20", "candidatos": None, "fase": "publicar"},
            {"id": "traf-ola2", "puesto": "Trafficker", "plazas": 3, "oleada": 2, "abre": "2026-09-29", "entra": "2026-10-27", "lleva_cuentas": "2026-11-02", "candidatos": None, "fase": "publicar"},
            {"id": "crm-ola2", "puesto": "Especialista de CRM", "plazas": 1, "oleada": 2, "abre": "2026-09-29", "entra": "2026-10-27", "lleva_cuentas": "2026-11-02", "candidatos": None, "fase": "publicar"},
        ],
        "calendario": [
            {"fecha": "2026-09-29", "hasta": "2026-10-03", "texto": "Publicar las ofertas: 7 traffickers y 3 de CRM; elegir 1-2 accounts para reconvertir"},
            {"fecha": "2026-10-05", "texto": "Entran los setters"},
            {"fecha": "2026-10-06", "hasta": "2026-10-10", "texto": "Entrevistas y prueba práctica (Higgsfield y cuenta de ejemplo)"},
            {"fecha": "2026-10-13", "texto": "Primera oleada: 4 traffickers y 2 de CRM · una semana de formación"},
            {"fecha": "2026-10-27", "hasta": "2026-11-02", "texto": "Segunda oleada: 3 traffickers y 1 de CRM"},
            {"fecha": "2026-11-18", "hasta": "2026-11-19", "texto": "Accountex: todos formados antes"},
        ],
        "cuentas": {"hoy": 54, "oct": 76, "nov": 102, "dic": 111, "con_publicidad": {"hoy": 23, "oct": 45, "nov": 77, "dic": 92}},
        "fases": ["publicar", "entrevistas", "prueba", "oferta", "formación", "lleva cuentas"],
    }


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
pruebas_coherencia.py · UNA SOLA VERDAD: ¿cuenta cada pantalla lo mismo que la verdad única? (E0 ronda 5)

Compara, cliente a cliente o persona a persona, lo que dejan los generadores de cada módulo (data/<módulo>/…)
con data/verdad/clientes.json y data/verdad/equipo.json, para los conceptos que hoy se calculaban distinto:
account, clientes nuevos, encendido de las altas, sin reunión, bloqueos, no imputan, y la gravedad de una fuga de
integración (regla única: una fuga grave nunca es «Bien»).

Cada comprobación es de un módulo:
  · ERROR  si el módulo está en ADOPTADOS (ya dice que lee la verdad) y no coincide → la prueba falla.
  · AVISO  si aún no la ha adoptado: se lista la discrepancia para su dueño, pero no hace fallar la prueba.
Cuando un dueño adopte la verdad, se añade su módulo a ADOPTADOS y desde entonces cualquier diferencia rompe la prueba.

Uso: python3 pruebas_coherencia.py   (solo lee ficheros; no necesita el servidor)
"""
import json
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
DATA = AQUI / "data"
# Módulos que ya leen la verdad única (o cuyos datos genera E0 con su misma regla).
ADOPTADOS = {"menú (carcasa)", "base (clientes.json y alarmas.json)", "verdad", "agenda", "clientes-nuevos", "informe-cliente", "dinero-cliente", "produccion", "ficha", "reuniones", "mi-dia", "decisiones", "personas", "en-rojo", "bandeja", "seo-web", "redes", "salud-crm", "captacion", "fuentes (E1)"}

errores, avisos = [], []


def leer(rel):
    try:
        return json.loads((DATA / rel).read_text())
    except Exception:
        return None


def comprobar(modulo, concepto, diferencias):
    if not diferencias:
        print(f"✓ {modulo} · {concepto}")
        return
    linea = f"{modulo} · {concepto}: {len(diferencias)} diferencia(s) → {diferencias[:6]}"
    if modulo in ADOPTADOS:
        errores.append(linea)
        print("✗ ERROR " + linea)
    else:
        avisos.append(linea)
        print("· AVISO " + linea)


V = leer("verdad/clientes.json")
if not V:
    print("✗ No existe data/verdad/clientes.json: lanza fuentes_verdad/generar_verdad.py")
    sys.exit(1)
ver = {c["cliente_id"]: c for c in V["clientes"]}
comun = {c["id"]: c for c in V["comun"]}

# --- La propia verdad: regla de gravedad única y «sin account» solo sin account
comprobar("verdad", "una fuga de integración grave nunca es «bien»",
          [cid for cid, c in ver.items() if (c.get("fuga_integracion") or {}).get("grave") and c["gravedad"] == "bien"])
comprobar("verdad", "«sin account» solo si no hay account",
          [cid for cid, c in ver.items() if c["account"] and c["sin_account"]])
comprobar("verdad", "la lista común no lleva cifras ni euros en el motivo",
          [cid for cid, c in comun.items() if c.get("motivo") and any(ch.isdigit() for ch in c["motivo"])])

# --- Base (build_data.py): responsable, sin account, nuevo y alarmas
clientes = {c["id"]: c for c in (leer("clientes.json") or [])}
comprobar("base (clientes.json y alarmas.json)", "account = responsable",
          [cid for cid, c in clientes.items() if cid in ver and (c.get("responsable_id") or None) != ver[cid]["account"]])
comprobar("base (clientes.json y alarmas.json)", "clientes nuevos",
          [cid for cid, c in clientes.items() if cid in ver and bool(c.get("nuevo")) != ver[cid]["nuevo"]])
alarmas = leer("alarmas.json") or []
comprobar("base (clientes.json y alarmas.json)", "«Cliente nuevo sin account» solo sin account",
          [a["cliente_id"] for a in alarmas if a["tipo"] == "Cliente nuevo sin account" and ver.get(a["cliente_id"], {}).get("account")])
comprobar("base (clientes.json y alarmas.json)", "«fuera de plazo» = sin encender pasado el día 12",
          [a["cliente_id"] for a in alarmas if a["tipo"] == "Cliente nuevo fuera de plazo"
           and (ver.get(a["cliente_id"], {}).get("encendido") or {}).get("estado") != "sin_encender_fuera_de_plazo"])
comprobar("base (clientes.json y alarmas.json)", "sin reunión el mes pasado",
          sorted({a["cliente_id"] for a in alarmas if a["tipo"].startswith("Sin reunión")} ^ {cid for cid, c in ver.items() if c["sin_reunion_mes_pasado"]}))

# --- Clientes nuevos (M12)
N = leer("nuevos/nuevos.json")
if N:
    comprobar("clientes-nuevos", "account de cada alta",
              [a["cliente_id"] for a in N.get("altas", []) if a["cliente_id"] in ver and ((a.get("account") or {}).get("id")) != ver[a["cliente_id"]]["account"]])

# --- Captación (M6) frente a la fuga de integración (B-02)
C = leer("captacion/captacion.json")
if C:
    comprobar("captacion", "fuga de integración grave no puede salir «ok»",
              [c["cliente_id"] for c in C.get("clientes", []) if c.get("cliente_id") in ver
               and (ver[c["cliente_id"]].get("fuga_integracion") or {}).get("grave") and c.get("severidad") == "ok"])
    comprobar("captacion", "account",
              [c["cliente_id"] for c in C.get("clientes", []) if c.get("cliente_id") in ver and (c.get("equipo") or {}).get("account") != ver[c["cliente_id"]]["account"]])

# --- Salud del CRM (M7)
R = leer("crm/crm.json")
if R:
    comprobar("salud-crm", "account",
              [s["cliente_id"] for s in R.get("subcuentas", []) if s.get("cliente_id") in ver and s.get("account_id") and s["account_id"] != ver[s["cliente_id"]]["account"]])

# --- Decisiones (M21) frente a Nuevos (B-04)
D = leer("decisiones/reloj.json")
if D:
    for d in D.get("decisiones", []):
        titulo_d = d.get("titulo") or ""
        if ("sin encender" in titulo_d or "sin campaña" in (d.get("problema") or "")) and "tarde" not in titulo_d:
            comprobar("decisiones", f"«{d.get('titulo')}»: solo altas sin encender",
                      [cid for cid in d.get("clientes") or [] if (ver.get(cid, {}).get("encendido") or {}).get("estado") != "sin_encender_fuera_de_plazo"])

# --- Reuniones (M15)
RU = leer("reuniones/reuniones.json")
if RU:
    comprobar("reuniones", "sin reunión el mes pasado",
              [c["cliente_id"] for c in RU.get("clientes", []) if c["cliente_id"] in ver and (c.get("estado") == "sin_reunion") != ver[c["cliente_id"]]["sin_reunion_mes_pasado"]])
    comprobar("reuniones", "account",
              [c["cliente_id"] for c in RU.get("clientes", []) if c["cliente_id"] in ver and c.get("account_id") != ver[c["cliente_id"]]["account"]])

# --- Producción (M10): bloqueos
P = leer("produccion/produccion.json")
if P:
    comprobar("produccion", "bloqueos por cliente",
              [p["cliente_id"] for p in P.get("proyectos", []) if p.get("cliente_id") in ver and (p.get("bloqueadas") or 0) != ver[p["cliente_id"]]["bloqueos"]["tareas"]])
    callados_alarma = {a["cliente_id"] for a in alarmas if a["tipo"] in ("Bloqueo sin resolver", "Bloqueo callado más de 5 días")}
    callados_verdad = {cid for cid, c in ver.items() if c["bloqueo_callado"]}
    comprobar("base (clientes.json y alarmas.json)", "alarma de bloqueo = «bloqueo callado más de 5 días» de la verdad",
              sorted(callados_alarma ^ callados_verdad))

# --- Informe del cliente (M5): el account de cada fila sale de la verdad única
IN = leer("informe/p_2026-09.json")
if IN:
    comprobar("informe-cliente", "account",
              [f["cliente_id"] for f in IN.get("filas", []) if f["cliente_id"] in ver and f.get("account") != ver[f["cliente_id"]]["account"]])

# --- Agenda (M23): «cliente en rojo con reunión» = gravedad «critico» de la verdad única
AG = leer("agenda/agenda.json")
if AG:
    comprobar("agenda", "cliente en rojo con reunión = crítico en la verdad",
              sorted({e["cliente_ref"] for e in AG.get("eventos", []) if e.get("cliente_ref") in ver
                      and bool(e.get("en_rojo")) != (ver[e["cliente_ref"]]["gravedad"] == "critico")}))

# --- En rojo (M2): lee la verdad única (gravedad, motivo, account, nuevo) y no las alarmas del panel
AT = leer("en_rojo/atajos.json")
_er = (AQUI / "modulos" / "en_rojo.js").read_text() if (AQUI / "modulos" / "en_rojo.js").exists() else ""
comprobar("en-rojo", "pinta la gravedad única (verdadComun) y no las alarmas del panel",
          [x for x in ["verdadComun", "ctx.verdad("] if x not in _er] + [x for x in ["datos.alarmas.filter(a => a.ambito !== 'persona'", "Bloqueo sin resolver", "Cliente nuevo sin account"] if x in _er])
comprobar("en-rojo", "atajos: un registro por cliente de la verdad",
          sorted(set(ver) ^ {f["cliente_id"] for f in (AT or {}).get("filas", [])}) if AT else ["falta data/en_rojo/atajos.json"])
comprobar("en-rojo", "«sin account» solo si la verdad no tiene account (lista común)",
          [cid for cid, c in comun.items() if c.get("sin_account") and c.get("responsable_id")])

# --- Dinero por cliente (M18)
DC = leer("dinero_cliente/dinero_cliente.json")
if DC:
    comprobar("dinero-cliente", "account",
              [c["cliente_id"] for c in DC.get("clientes", []) if c.get("cliente_id") in ver and c.get("account_id") != ver[c["cliente_id"]]["account"]])

# --- SEO (M8) y Redes (M9): quién lleva cada cliente sale del equipo de la verdad única
def _principal(c, silla):
    eq = (c.get("equipo") or {}).get(silla) or []
    return (next((x for x in eq if x.get("principal")), eq[0]) if eq else {}).get("persona_id")
SEO = leer("seo/seo.json")
if SEO:
    comprobar("seo-web", "SEO y web de cada cliente",
              [f["cliente_id"] for f in SEO.get("clientes", []) if f["cliente_id"] in ver and (f.get("seo_id") != _principal(ver[f["cliente_id"]], "seo") or f.get("web_id") != _principal(ver[f["cliente_id"]], "web"))])
    comprobar("seo-web", "nunca «verde» sin clics medidos",
              [f["cliente_id"] for f in SEO.get("clientes", []) if f.get("estado") == "verde" and not f.get("clics")])
RED = leer("redes/redes.json")
if RED:
    comprobar("redes", "redes y account de cada cliente",
              [f["cliente_id"] for f in RED.get("clientes", []) if f["cliente_id"] in ver and (f.get("redes_id") != _principal(ver[f["cliente_id"]], "redes") or f.get("account_id") != ver[f["cliente_id"]]["account"])])

# --- Ficha del cliente (M4): account de la verdad y cuota = la de Dinero por cliente
FP = leer("ficha/portal.json")
if FP:
    comprobar("ficha", "account",
              [f["cliente_id"] for f in FP.get("filas", []) if f["cliente_id"] in ver and f.get("account_id") != ver[f["cliente_id"]]["account"]])
    if DC:
        cuota_dc = {c["cliente_id"]: c.get("cuota") for c in DC.get("clientes", [])}
        comprobar("ficha", "cuota = la de Dinero por cliente",
                  [f["cliente_id"] for f in FP.get("filas", []) if f["cliente_id"] in cuota_dc and f.get("cuota") != cuota_dc[f["cliente_id"]]])

# --- Equipo: no imputan ayer (Horas frente a Personas)
E = leer("verdad/equipo.json")
H = leer("horas/horas.json")
PM = leer("personas_m20/equipo.json")
if E and H:
    v_no = {x["persona_id"] for x in E["no_imputan_ayer"]}
    comprobar("verdad", "no imputan ayer (misma lista que Horas con la definición única)",
              sorted(v_no - {p["persona_id"] for p in H.get("personas", []) if not p.get("ayer")}))
if E and PM:
    pm_no = set()
    for p in PM.get("personas", []):
        horas = p.get("horas") or {}
        if p.get("estado") == "activo" and p.get("imputa") not in (False, "no") and isinstance(horas, dict) and horas.get("ayer") == 0:
            pm_no.add(p["persona_id"])
    if pm_no:
        comprobar("personas", "no imputan ayer", sorted(pm_no ^ {x["persona_id"] for x in E["no_imputan_ayer"]}))

# --- Mi día (M1): «lo que ha cambiado desde ayer» cuenta las altas fuera de plazo con la verdad (y el beneficio es el de Finanzas)
MD = leer("mi_dia/cambios.json")
if MD:
    for l in MD.get("lineas", []):
        n = (l.get("dato") or {}).get("altas_fuera_de_plazo")
        if n is not None:
            altas_n = {a["cliente_id"] for a in (leer("nuevos/nuevos.json") or {}).get("altas", [])}
            v_n = sum(1 for cid in altas_n if (ver.get(cid, {}).get("encendido") or {}).get("estado") == "sin_encender_fuera_de_plazo")
            comprobar("mi-dia", "altas fuera de plazo en «cambios desde ayer»", [] if n == v_n else [f"mi día {n} · verdad {v_n}"])

# --- Bandeja (M3): el account de cada fila es el de la verdad; el resumen por cliente sale de las mismas filas
BJ = leer("bandeja/bandeja.json")
if BJ:
    filas = [x for k in ("correos", "llamadas") for x in BJ.get(k, []) if x.get("cliente_id") in ver]
    comprobar("bandeja", "account de cada correo y llamada = verdad.account",
              sorted({x["cliente_id"] for x in filas if (x.get("account_id") or None) != ver[x["cliente_id"]]["account"]}))
    BPC = leer("bandeja/por_cliente.json")
    if BPC:
        cuenta = {}
        for x in BJ.get("correos", []):
            if x.get("cliente_id") and not x.get("auto"):
                cuenta[x["cliente_id"]] = cuenta.get(x["cliente_id"], 0) + 1
        comprobar("bandeja", "por_cliente.json = mismas filas que la Bandeja",
                  sorted(c["cliente_id"] for c in BPC.get("clientes", []) if c["sin_contestar"] != cuenta.get(c["cliente_id"], 0)))

# --- Ronda 9 (D-P-DIN): cuota única. La de cada cliente (clientes.json) = fuentes_dinero/cuotas.json, y las tres cifras
#     del mes (verdad.cuota_empresa) = las de Finanzas (admin.cuota_tres): recurrente 67.291 · mes 70.781 · facturable 70.581.
import json as _json
_cq = AQUI / "fuentes_dinero" / "cuotas.json"
if _cq.exists():
    _cuotas = _json.loads(_cq.read_text()).get("cuotas") or {}
    _cli = leer("clientes.json") or []
    comprobar("base (clientes.json)", "cuota de cada cliente = fuentes_dinero/cuotas.json",
              sorted(c["id"] for c in _cli if c["id"] in _cuotas and (c.get("cuota") or 0) != (_cuotas[c["id"]].get("cuota") or 0)))
    _ce = (leer("verdad/clientes.json") or {}).get("cuota_empresa") or {}
    _tres = ((leer("finanzas/finanzas.json") or {}).get("admin") or {}).get("cuota_tres") or {}
    if _ce and _tres:
        comprobar("verdad", "cuota del mes de la empresa = Finanzas (recurrente, cuota del mes y facturable)",
                  [f"{k}: verdad {_ce.get(k)} · finanzas {_tres.get(k)}" for k in ("recurrente", "cuota_mes", "facturable") if abs((_ce.get(k) or 0) - (_tres.get(k) or 0)) >= 1])

# --- R12 · QUIÉN LLEVA QUÉ: una sola verdad de asignaciones en todas las pantallas (carril «quién lleva qué»)
_P = {p["id"]: p for p in (leer("personas.json") or [])}
_baja = {pid for pid, p in _P.items() if p.get("estado") == "baja"}
_alias = lambda pid: (_P.get(pid) or {}).get("alias") or (_P.get(pid) or {}).get("nombre")
_cli = {c["id"]: c for c in (leer("clientes.json") or [])}
comprobar("base (clientes.json y alarmas.json)", "R12 · el texto del responsable es el de su account de asignaciones (Musashi)",
          sorted(cid for cid, c in _cli.items() if c.get("responsable_texto") != (_alias(c["responsable_id"]) if c.get("responsable_id") else None)))
comprobar("base (clientes.json y alarmas.json)", "R12 · el responsable de cada alarma de cliente es su account de asignaciones",
          sorted({a["cliente_id"] for a in (leer("alarmas.json") or []) if a.get("ambito") == "cliente" and a.get("cliente_id") in _cli
                  and a.get("tipo") != "Falta la ficha en la Cartera de ClickUp" and a.get("responsable_id") != _cli[a["cliente_id"]].get("responsable_id")}))
comprobar("verdad", "R12 · ninguna persona de baja en el equipo de un cliente (Bautista en Musashi)",
          sorted(f"{cid}:{x['persona_id']}" for cid, c in ver.items() for l in (c.get("equipo") or {}).values() for x in l if x["persona_id"] in _baja))
comprobar("verdad", "R12 · una sola persona de web por cliente (salvo quien espera decisión porque su puesto no es web)",
          sorted(cid for cid, c in ver.items() if len([x for x in (c.get("equipo") or {}).get("web", [])
                                                       if "web" in ((_P.get(x["persona_id"]) or {}).get("puestos") or [])]) > 1))
_car = {(f["persona_id"], f["silla"]): f for f in V.get("carteras", [])}
_asig_n = {}
for a in leer("asignaciones.json") or []:
    if (not a.get("desde") or a["desde"] <= V["generado"]) and (not a.get("hasta") or a["hasta"] >= V["generado"]) \
            and a.get("persona_id") not in _baja and (_P.get(a.get("persona_id")) or {}).get("activo") and a["cliente_id"] in ver:
        _asig_n.setdefault((a["persona_id"], a["silla"]), set()).add(a["cliente_id"])
comprobar("verdad", "R12 · cartera de cada persona y silla = asignaciones vigentes (principal + apoyo)",
          sorted(f"{k[0]}/{k[1]}" for k in set(_car) | set(_asig_n) if len(_asig_n.get(k, ())) != (_car.get(k, {}).get("n_principal", 0) + _car.get(k, {}).get("n_apoyo", 0))))
_PM = leer("personas_m20/equipo.json")
if _PM:
    comprobar("personas", "R12 · la cartera de Personas es la de la verdad (Lina 21 en todas partes)",
              sorted(f"{p['persona_id']}/{s}" for p in _PM.get("personas", []) for s, n in (p.get("cartera") or {}).items()
                     if (p["persona_id"], s) in _car and n != _car[(p["persona_id"], s)]["n_principal"] + _car[(p["persona_id"], s)]["n_apoyo"]))
_CRM = leer("crm/crm.json")
if _CRM:
    comprobar("salud-crm", "R12 · especialista de cada subcuenta = CRM principal de la verdad, y con su nombre (Mi día de Yessica)",
              sorted(f["cliente_id"] for f in _CRM.get("subcuentas", []) if f.get("cliente_id") in ver
                     and (f.get("especialista_id") != _principal(ver[f["cliente_id"]], "crm") or bool(f.get("especialista_id")) != bool(f.get("especialista")))))
if RED:
    _en_red = {f["cliente_id"] for f in RED.get("clientes", [])} | {f["cliente_id"] for f in RED.get("sin_metricool", [])}
    comprobar("redes", "R12 · todo cliente con persona de redes sale en Redes (con o sin Metricool): la asignación manda",
              sorted(cid for cid, c in ver.items() if (c.get("equipo") or {}).get("redes") and cid not in _en_red))
_W = leer("seo/webs.json")
if _W:
    comprobar("seo-web", "R12 · el dueño de cada web en «Webs» = la persona de web de la verdad (Busbac, Musashi)",
              sorted(w["cliente"] for w in _W.get("webs", []) if w.get("cliente") in ver and w.get("web_id") != _principal(ver[w["cliente"]], "web")))
_REU = leer("reuniones/reuniones.json")
if _REU:
    comprobar("reuniones", "R12 · un apellido corriente suelto no empareja una reunión con un cliente (Emex ≠ Romero Martínez)",
              sorted({x["reunion"] for x in _REU.get("asistencias", []) if x.get("cli") == "romero-martinez" and "romero" not in (x.get("tema") or "").lower()}))

# --- R12 · MI DÍA (auditoría final A-C1, A-A3/A4/A5, B-C01, B-A02/A04/A05/A06, C): cada cifra de Mi día sale de la MISMA
#     definición que su pantalla de origen. Mi día es JavaScript: se comprueba que cada bloque lea la definición única
#     (y no un cálculo propio) y, con los datos, que esa definición dé lo mismo que la otra pantalla.
import re  # noqa: E402 (solo esta sección)
_MDJS = (AQUI / "modulos" / "mi_dia_bloques.js").read_text()
_MDCFG = leer("mi_dia/config.json") or {}


def _trozo(nombre):
    """Cuerpo de def('x' …) / num('x' …) hasta el siguiente def( / num( / function."""
    m = re.search(r"\n(?:def|num)\('" + re.escape(nombre) + r"'.*?(?=\n(?:def|num)\(|\nfunction |\nconst \w+ = |\Z)", _MDJS, re.S)
    return m.group(0) if m else ""


_reglas_md = [  # (bloque, debe contener, no debe contener, qué)
    ("cartera_salud", "saludV", r"filter\(c => c\.enCartera && typeof c\.salud", "número del account = salud de la verdad (la de la ficha), no la de la sesión (GAC 35 frente a 62)"),
    ("clientes_tarjetas", "saludV", r"salud: c\.salud,|Semáforo: \$\{c\.semaforo", "«Tus clientes» con salud y estado de la verdad (Lobo y Garmande en crítico)"),
    ("semaforo_cartera", "saludV", r"ctx\.clientes\.filter\(c => typeof c\.salud", "semáforo de la cartera de Coti con la salud de la verdad"),
    ("altas_linea", "arranqueV", r"a\.plazo\?\.estado === 'rojo'\)\.slice", "«sin encender» solo con la verdad (Laver se encendió tarde)"),
    ("arranques", "arranqueV", r"· \$\{a\.meta\.estado \|\| '—'\}", "arranques con el estado de la campaña de la verdad, no «activa» de la cuenta"),
    ("bandeja_mia", "bandejaComoPantalla", r"x\.account_id === yo\(ctx\) \|\| x\.asignado_id", "bloque Bandeja = la regla de la pantalla Bandeja (13, no 14)"),
    ("cumplimiento", "bandejaComoPantalla", r"c\.contesta\?\.mas48\)\} de", "«Tu cumplimiento» cuenta correos, revisiones y reuniones como sus bloques"),
    ("cuentas_problema", "motivoCuenta", None, "sin «[importe]»: la frase sin la cifra y la cifra aparte"),
    ("tabla_trafficker", "porTrafficker(ctx, D)", None, "cartera de cada trafficker por asignaciones (Lina 21)"),
    ("seo_verde", "estado !== 'gris'", r"r\.clientes_seo", "número de la jefa de SEO con la base de medibles de SEO (38, no 41)"),
    ("top5_mios", "avisoSeRanking", None, "top 5 con el aviso del fallo de SE Ranking"),
    ("redes_14", "redes(ctx, D", r"c\.redes_id === yo\(ctx\) \|\|", "número de Redes sobre la cartera de redes de las asignaciones (25, no 4)"),
    ("webs_verde", "webs(ctx, D", None, "web ve SUS webs (asignaciones)"),
]
_mal_md = []
for nombre, debe, no_debe, que in _reglas_md:
    t = _trozo(nombre)
    if not t or debe not in t or (no_debe and re.search(no_debe, t)):
        _mal_md.append(f"{nombre}: {que}")
comprobar("mi-dia", "R12 · cada bloque lee la definición única (salud, arranque, bandeja, cartera, SEO, redes, webs)", _mal_md)
_acc = (_MDCFG.get("puestos") or {}).get("account") or {}
comprobar("mi-dia", "R12 · el account ve primero los resultados de sus despachos y sin el bloque de alarmas de las 07:00 (A3/A4)",
          [] if _acc.get("arriba") == "resultados_mios" and "primero_cartera" not in (_acc.get("bloques") or []) else [json.dumps(_acc.get("bloques"))])
comprobar("mi-dia", "R12 · «Yessica» con Y en la configuración de Mi día", ["Jessi"] if "Jessi" in json.dumps(_MDCFG, ensure_ascii=False) else [])
# Con los datos: la cartera por trafficker que pinta Mi día (equipo de la verdad, cualquier persona de la silla) = asignaciones
_md_tr = {}
for cid, c in ver.items():
    for x in (c.get("equipo") or {}).get("trafficker", []):
        _md_tr[x["persona_id"]] = _md_tr.get(x["persona_id"], 0) + 1
comprobar("mi-dia", "R12 · «Por trafficker» y «Carga» = cartera de asignaciones (la de Personas)",
          sorted(f"{p}: mi día {n} · asignaciones {len(_asig_n.get((p, 'trafficker'), ()))}" for p, n in _md_tr.items()
                 if n != len(_asig_n.get((p, "trafficker"), ()))))
_SEO = leer("seo/seo.json")
if _SEO:
    _med = [c for c in _SEO.get("clientes", []) if c.get("estado") != "gris"]
    _r = _SEO.get("resumen") or {}
    comprobar("mi-dia", "R12 · «Clientes de SEO en verde» de Mi día = el de SEO, ficha y webs (base de medibles)",
              [] if (len(_med), sum(1 for c in _med if c.get("estado") == "verde")) == (_r.get("medibles", len(_med)), _r.get("verdes")) else [f"medibles {len(_med)} · resumen {_r.get('medibles')}"])

# --- R12 · VENTAS Y DINERO (carril «ventas y dinero»): una sola cifra por concepto en Ventas de RO, Setters, Prospección,
#     Finanzas, Dinero por cliente y Panel de dirección. Estos módulos ya leen la definición única: una diferencia rompe la prueba.
ADOPTADOS.update({"ventas-ro", "setters", "prospeccion", "finanzas"})
_VR = leer("ventas_ro/ventas_ro.json")
if _VR and _VR.get("dias"):
    _dif = []
    for _m, _x in (_VR.get("meses") or {}).items():
        for _k, _v in _x.items():
            if isinstance(_v, (int, float)) and _k not in ("desde", "hasta"):
                _s = sum((d.get(_k) or 0) for f, d in _VR["dias"].items() if f.startswith(_m))
                if abs(_s - _v) > 0.01:
                    _dif.append(f"{_m}.{_k}: días {round(_s, 2)} · mes {_v}")
    comprobar("ventas-ro", "R12 · el embudo de cada periodo (suma de días) = el del mes (septiembre cuadra con el panel)", _dif)
if _VR:
    _mh = (_VR.get("meses") or {}).get(max(_VR.get("meses") or {"": 0}), {})
    _vivo = _mh.get("de_hoy_en_vivo")
    comprobar("ventas-ro", "R12 · las reuniones de hoy ya pasadas cuentan como celebradas con la etapa de GHL (Clara)",
              [] if _vivo is None else ([f"en vivo {_vivo.get('celebradas')} · lista de hoy {sum(1 for x in _VR.get('hoy', []) if x.get('resultado') == 'celebrada')}"]
                                         if _vivo.get("celebradas") != sum(1 for x in _VR.get("hoy", []) if x.get("resultado") == "celebrada") else []))
    comprobar("ventas-ro", "R12 · ninguna reunión de hoy pasada en «Propuesta enviada», «Contrato enviado» o «Cliente» sale como no celebrada",
              [x.get("cuando") for x in _VR.get("hoy", []) if x.get("pasada") and x.get("etapa") in ("Propuesta enviada", "Contrato enviado", "Cliente") and x.get("resultado") != "celebrada"])
_ST = leer("ventas_ro/setters.json")
if _ST:
    _setters = {"ana", "javier"}
    comprobar("setters", "R12 · cada lead, cita y reunión pasada lleva su setter y su almacén existe (nunca setter_null)",
              sorted({str(x.get("setter")) for k in ("leads", "citas", "pasadas") for x in _ST.get(k, [])
                      if x.get("setter") not in _setters or not (DATA / "ventas_ro" / "_privado" / f"setter_{x.get('setter')}.json").exists()}))
_OU = leer("ventas_ro/outreach.json")
if _OU:
    _act = sorted(k for k, x in (_OU.get("clientes") or {}).items() if ((x.get("sep") or {}).get("enviados") or 0) > 0)
    comprobar("prospeccion", "R12 · si la tabla de clientes enseña envíos, Snov.io está leído (no «0 campañas» falso)",
              _act if (_act and not (_OU.get("snov") or {}).get("campañas")) else [])
_FD = leer("finanzas/direccion.json")
_FA = leer("finanzas/finanzas.json")
if _FD and _FD.get("direccion"):
    _cj = _FD["direccion"][0].get("caja") or {}
    comprobar("finanzas", "R12 · meses de caja = caja ÷ gasto medio, y el gasto medio existe (nada de «gasto medio —»)",
              [] if _cj.get("gasto_medio") and abs(round(_cj["total"] / _cj["gasto_medio"], 2) - _cj["meses"]) < 0.01 else [str(_cj)[:160]])
    _mb = (_FD["direccion"][0].get("kpi") or {}).get("mb")
    _pd = (AQUI / "modulos" / "panel_direccion.js").read_text()
    comprobar("finanzas", "R12 · el Panel de dirección usa el margen bruto de Finanzas (un solo margen) y no el 29 % del v29",
              (["el panel aún calcula con el margen del v29"] if "Usa el margen bruto del panel v29 (29 %)" in _pd or "kpi?.mb" not in _pd else [])
              + ([] if _mb else ["Finanzas no trae kpi.mb"]))
    if _FA:
        _fm = {x["m"]: x for x in (_FA.get("admin") or {}).get("facturado_mes", [])}
        comprobar("finanzas", "R12 · lo facturado mes a mes es lo mismo para Sofía (admin) y para Tomás (dirección)",
                  [x["m"] for x in _FD["direccion"][0].get("ingresos", []) if x["m"] in _fm and abs((_fm[x["m"]]["total"] or 0) - (x.get("total") or 0)) >= 1]
                  + ([] if _fm else ["falta admin.facturado_mes"]))
        _DC2 = leer("dinero_cliente/dinero_cliente.json")
        if _DC2:
            _sum = {}
            for c in _DC2.get("clientes", []):
                for m, v in (c.get("cuota_facturado_mes") or {}).items():
                    _sum[m] = _sum.get(m, 0) + v
            comprobar("dinero-cliente", "R12 · lo facturado a los clientes de la tabla nunca pasa de lo facturado por la empresa (Finanzas)",
                      [f"{m}: clientes {round(v)} · empresa {_fm[m]['total']}" for m, v in _sum.items() if m in _fm and v > (_fm[m]["total"] or 0) + 1])

# --- R12 · PANTALLAS DE EQUIPO Y SERVICIOS (carril E: Producción, Personas, SEO, Clientes nuevos, Captación)
import re as _re
_PR = leer("produccion/produccion.json")
if _PR:
    _gr = (_PR.get("definiciones") or {}).get("cola_ahora", {}).get("grupos")
    _cola = _PR.get("cola", [])
    _dif = []
    for _p in _PR.get("personas", []):
        _mi = [r for r in _cola if r["persona_id"] == _p["persona_id"]]
        if _p.get("vencidas") != sum(1 for r in _mi if r["grupo"] == "vencida") or _p.get("cola_ahora") != sum(1 for r in _mi if r["grupo"] in (_gr or ())):
            _dif.append(_p["persona_id"])
    comprobar("produccion", "R12 · una sola cifra de «tu cola»: vencidas y cola de ahora de cada persona = sus filas de la cola (M5)", _dif if _gr else ["sin definiciones.cola_ahora"])
    _js = lambda f: (AQUI / "modulos" / f).read_text()
    _lit = "['vencida', 'hoy', 'semana', 'bloqueada']"
    comprobar("produccion", "R12 · Producción y Mi día usan los mismos grupos de «tu cola ahora» que el generador",
              [f for f, ok in (("produccion_comun.js", _lit in _js("produccion_comun.js")), ("mi_dia_bloques.js", _lit in _js("mi_dia_bloques.js")),
                               ("generador", _gr == ["vencida", "hoy", "semana", "bloqueada"])) if not ok])
    _imp = _re.compile(r"\d[\d.,]*\s*€|€\s*\d|\d+\s*euros|\[importe\]", _re.I)
    comprobar("produccion", "R12 · ningún título de tarea lleva importes (facturas de RO, presupuestos) ni «[importe]»",
              [r["id"] for k in ("cola", "revisiones") for r in _PR.get(k, []) if _imp.search(r.get("tarea") or "")])
    comprobar("produccion", "R12 · cada tarea de la cola con cliente lleva su nombre de la verdad única (Mi día y Producción no lo deducen)",
              sorted({r["cli"] for r in _cola if r.get("cli") and r["cli"] in comun and r.get("cliente") != comun[r["cli"]].get("nombre")})[:10]
              + sorted({r["id"] for r in _cola if r.get("cli") and not r.get("cliente")})[:5])
_EQ = leer("personas_m20/equipo.json")
if _EQ:
    _hor = _re.compile(r"imput[óo]|registros? de horas", _re.I)
    comprobar("personas", "R12 · las horas imputadas son solo aviso: ninguna alerta de RRHH por horas (A7)",
              [p["persona_id"] for p in _EQ.get("personas", []) if any(_hor.search(m) for m in ((p.get("alerta") or {}).get("motivos") or []))])
_S2 = leer("seo/seo.json")
if _S2:
    _r2 = _S2.get("resumen") or {}
    _m2 = [c for c in _S2.get("clientes", []) if c.get("estado") != "gris"]
    _u = _r2.get("umbral") or {}
    _pct = _r2.get("pct_verde")
    _est = None if _pct is None else "verde" if _pct >= _u.get("verde", 999) else "ambar" if _pct >= _u.get("ambar", 999) else "rojo"
    comprobar("seo-web", "R12 · número que manda de SEO: una base (medibles), un umbral firmado y su estado (B-A05)",
              [x for x, ok in (("base", _r2.get("clientes_seo") == len(_m2) == _r2.get("medibles")), ("umbral", bool(_u.get("verde") and _u.get("ambar"))),
                               ("estado", _r2.get("estado") == _est)) if not ok])
    _top = []
    for c in _S2.get("clientes", []):
        rp = c.get("reparto") or {}
        inf = c.get("informe15") or []
        if rp and isinstance(inf, list) and inf and rp.get("top5", {}).get("mes") != sum(1 for p in inf if p.get("hoy") and p.get("mes") and p["mes"] <= 5):
            _top.append(c["cliente_id"])
    comprobar("seo-web", "R12 · «top 5 frente al mes anterior» solo con palabras que SE Ranking ve hoy (B-A06)", _top)
    comprobar("seo-web", "R12 · si SE Ranking deja de ver más de 50 palabras, hay un aviso único para SEO y Mi día",
              [] if (_r2.get("desaparecen_total", 0) <= 50) == (not _r2.get("aviso_seranking")) else ["aviso_seranking"])
_NV = leer("nuevos/nuevos.json")
if _NV:
    comprobar("clientes-nuevos", "R12 · campaña encendida = encendido de la verdad única, y la cuenta de Meta dicha como «cuenta …» (B-C02)",
              [a["cliente_id"] for a in _NV.get("altas", []) if a["cliente_id"] in ver and (
                  (a.get("campana") or {}).get("encendida") != ((ver[a["cliente_id"]].get("encendido") or {}).get("dia") is not None)
                  or (a.get("meta") and not str(a["meta"].get("estado_cuenta", "")).startswith("cuenta ")))])
_CP = leer("captacion/captacion.json")
if _CP:
    _v7 = (_CP.get("ventanas") or {}).get("7d") or [None, None]
    comprobar("captacion", "R12 · la serie diaria de Meta (la del periodo) suma lo mismo que la ventana de 7 días",
              [c["cliente_id"] for c in _CP.get("clientes", []) if c.get("serie") and _v7[0] and
               abs(sum(x.get("leads_meta") or 0 for x in c["serie"] if _v7[0] <= x["d"] <= _v7[1]) - ((c.get("leads") or {}).get("7d") or 0)) > 0.01])
    _ids_cap = {c["cliente_id"] for c in _CP.get("clientes", [])}
    comprobar("captacion", "R12 · «Mis cuentas» de cada trafficker = sus clientes principales de carteras[] que están en Captación (Lina 14, apoyo aparte)",
              [f'{c["persona_id"]}: {len(set(c.get("principal") or []) & _ids_cap)} ≠ {(c.get("universo") or {}).get("dentro")}' for c in V.get("carteras", [])
               if c.get("silla") == "trafficker" and (c.get("universo") or {}).get("que", "").endswith("Captación") and len(set(c.get("principal") or []) & _ids_cap) != (c.get("universo") or {}).get("dentro")])

# --- R13 · INCIDENCIAS (mapa de control) y ALERTAS: contesta / revisa / se reúne con las definiciones únicas de Bandeja
#     (bandeja/por_cliente.json sobre la cartera que da el servidor), Producción (revisiones del account) y Reuniones
#     (verdad única de «sin reunión»), igual que «Tu cumplimiento» de Mi día. Alertas: horas imputadas = solo aviso.
ADOPTADOS |= {"incidencias", "alertas"}
_INC = leer("incidencias/incidencias.json")
if _INC and _INC.get("control"):
    sys.path.insert(0, str(AQUI))
    import permisos as _P
    _pers = leer("personas.json") or []
    _pers = _pers if isinstance(_pers, list) else _pers.get("personas", [])
    _asig = leer("asignaciones.json") or []
    _asig = _asig if isinstance(_asig, list) else _asig.get("asignaciones", [])
    _pid = {p["id"]: p for p in _pers}
    _bjc = {c["cliente_id"]: c for c in (leer("bandeja/por_cliente.json") or {}).get("clientes", [])}
    _rev = (leer("produccion/produccion.json") or {}).get("revisiones", [])
    _reu = (leer("reuniones/reuniones.json") or {}).get("clientes", [])
    _vc = {c["cliente_id"]: c for c in V.get("clientes", [])}
    _dc, _dr, _du = [], [], []
    for x in _INC["control"]:
        pid = x.get("persona_ref")
        if not pid or pid not in _pid:
            continue
        cart = set(_P.contexto(_pid[pid], {"asignaciones": _asig, "personas": _pers, "clientes": leer("clientes.json") or []})["cartera_ids"])
        m48 = sum(int(_bjc[c].get("mas_48") or 0) for c in cart if c in _bjc)
        tot = sum(int(_bjc[c].get("sin_contestar") or 0) for c in cart if c in _bjc)
        if ((x.get("contesta") or {}).get("mas48"), (x.get("contesta") or {}).get("correos")) != (m48, tot):
            _dc.append(f"{pid}: incidencias {(x.get('contesta') or {}).get('mas48')}/{(x.get('contesta') or {}).get('correos')} · bandeja {m48}/{tot}")
        rv = [r for r in _rev if r.get("account_id") == pid and r.get("revisa") == "account"]
        if ((x.get("revisa") or {}).get("mas48"), (x.get("revisa") or {}).get("total")) != (sum(1 for r in rv if r.get("mas48")), len(rv)):
            _dr.append(f"{pid}: incidencias {(x.get('revisa') or {}).get('mas48')}/{(x.get('revisa') or {}).get('total')} · producción {sum(1 for r in rv if r.get('mas48'))}/{len(rv)}")
        ru = [c for c in _reu if (c.get("account_id") == pid or c.get("cliente_id") in cart) and c.get("estado") not in ("exento", "no_aplica")]
        sin = sum(1 for c in ru if (_vc[c["cliente_id"]]["sin_reunion_mes_pasado"] if _vc.get(c["cliente_id"], {}).get("sin_reunion_mes_pasado") is not None else c.get("estado") == "sin_reunion"))
        if (x.get("reune") or {}).get("sin_reunion") != sin:
            _du.append(f"{pid}: incidencias {(x.get('reune') or {}).get('sin_reunion')} · reuniones {sin}")
    comprobar("incidencias", "R13 · mapa de control «Contesta» = Bandeja por cliente de su cartera (como Mi día)", _dc)
    comprobar("incidencias", "R13 · mapa de control «Revisa» = revisiones del account de Producción (como Mi día)", _dr)
    comprobar("incidencias", "R13 · mapa de control «Se reúne» = Reuniones con la verdad única (como Mi día)", _du)
_AL = leer("alertas/alertas.json")
_EQ = leer("personas_m20/equipo.json")
if _AL:
    comprobar("alertas", "R13 · horas imputadas = solo aviso: ninguna «rrhh_no_imputa» entre las alertas (van en avisos, sin plazo ni escalado)",
              [a["id"] for a in _AL.get("alertas", []) if a.get("tipo") == "rrhh_no_imputa"]
              + [a["id"] for a in _AL.get("avisos", []) if a.get("vence") or (a.get("escalado") or {}).get("nivel")])
    if _EQ:
        _n_al = sum(1 for p in _EQ.get("personas", []) if p.get("alerta"))
        _n_rr = sum(1 for a in _AL.get("alertas", []) if a.get("tipo") == "rrhh_alerta")
        comprobar("alertas", "R13 · personas en alerta (RRHH) = las de Personas", [] if _n_al == _n_rr else [f"alertas {_n_rr} · personas {_n_al}"])

# ------------------------------------------------ N14 (2-oct-2026): cada fuente es del cliente correcto
_EMP = leer("emparejamientos.json")
if _EMP:
    import re as _re
    _usos = {}
    for _cid, _fila in (_EMP.get("clientes") or {}).items():
        for _fid, _e in _fila.items():
            if _fid in ("nombre", "ids") or not isinstance(_e, dict) or _e.get("id") in (None, ""):
                continue
            for _parte in str(_e["id"]).split(", "):
                _usos.setdefault((_fid, _parte), set()).add(_cid)
    comprobar("fuentes (E1)", "N14 · ninguna fuente (cuenta, propiedad, sitio, subcuenta, marca, proyecto, canal o NIF) asignada a dos clientes",
              [f"{f} {i}: {sorted(c)}" for (f, i), c in sorted(_usos.items()) if len(c) > 1])
    _RE_EXP = _re.compile(r"(€\s?\d)|(^\s*\d+\s*,\s*[^,]+,\s*\d+\s*,)|(\d+,\d{2}\s*,\s*\d+,\d+\s*$)")
    _basura = []
    for _f in sorted((DATA / "clientes").glob("*.json")):
        _gsc = ((json.loads(_f.read_text()).get("fuentes") or {}).get("gsc") or {}).get("datos") or {}
        _basura += [f"{_f.stem}: {str(q[0])[:40]}" for q in (_gsc.get("consultas") or []) if q and _RE_EXP.search(str(q[0]))]
    comprobar("fuentes (E1)", "N14 · en gsc.consultas no hay filas de exportaciones de Google Ads (CSV con «€»)", _basura)
    _H = leer("fuentes/hallazgos_medicion.json")
    _ids_cli = {x["cliente_id"] for x in V["clientes"]}
    _mal = ["falta data/fuentes/hallazgos_medicion.json"] if not _H else [
        h["id"] for h in _H.get("hallazgos", []) if h.get("cliente_id") not in _ids_cli or not h.get("dueno")
        or not str(h.get("texto", "")).startswith("Medición: ")]
    comprobar("fuentes (E1)", "N14 · hallazgos de medición: cada uno con cliente de la verdad única, dueño y texto «Medición: …»", _mal)

# --- A4 (2-oct) · el objetivo del cliente se lee de UN solo sitio: la tabla «acciones» de la base de la app, a través de
#     fuentes_objetivos/objetivos.py (Python: Captación → captacion.json → Mi día) y modulos/objetivos_comun.js (ficha y Clientes nuevos).
ADOPTADOS.add("objetivos (A4)")
import re as _reA4
_lectores_js = []
for _f in sorted((AQUI / "modulos").glob("*.js")):
    if _f.name == "objetivos_comun.js":
        continue
    _t = _f.read_text(errors="ignore")
    if _reA4.search(r"""tipo\s*===?\s*['"](objetivo_alta|semaforo_semanal)['"]""", _t):
        _lectores_js.append(_f.name)
comprobar("objetivos (A4)", "ningún módulo filtra «objetivo_alta» ni «semaforo_semanal» por su cuenta (solo objetivos_comun.js)", _lectores_js)
_lectores_py = []
for _f in sorted(AQUI.glob("fuentes_*/*.py")):
    if _f.parent.name == "fuentes_objetivos":
        continue
    _t = _f.read_text(errors="ignore")
    if _reA4.search(r"""tipo\s*(=|IN)\s*\(?['"](objetivo_alta|semaforo_semanal)""", _t):
        _lectores_py.append(f"{_f.parent.name}/{_f.name}")
comprobar("objetivos (A4)", "ningún generador lee el objetivo de la base por su cuenta (solo fuentes_objetivos/objetivos.py)", _lectores_py)
_usan = {"modulos/ficha.js": "objetivos_comun.js", "modulos/nuevos.js": "objetivos_comun.js",
         "fuentes_captacion/generar_captacion.py": "fuentes_objetivos", "fuentes_ficha/generar_ficha.py": "fuentes_objetivos"}
comprobar("objetivos (A4)", "ficha, Clientes nuevos, Captación (y con ella Mi día) leen el objetivo de la lectura común",
          [k for k, v in _usan.items() if v not in (AQUI / k).read_text(errors="ignore")])
_OB = leer("objetivos/objetivos.json")
if _OB:
    sys.path.insert(0, str(AQUI))
    from fuentes_objetivos import objetivos as _OBJ
    _ahora, _ = _OBJ.leer()
    _ob = {c["cliente_id"]: c for c in _OB.get("clientes", [])}
    comprobar("objetivos (A4)", "objetivos.json = lo que hay en la base (hasta su última acción)",
              [cid for cid, c in _ob.items() if (c.get("objetivo") or {}).get("accion_id") and
               ((_ahora.get(cid) or {}).get("objetivo") or {}).get("accion_id") == c["objetivo"]["accion_id"] and
               {k: c["objetivo"].get(k) for k in _OBJ.CAMPOS} != {k: _ahora[cid]["objetivo"].get(k) for k in _OBJ.CAMPOS}])
    if _CP:
        _dif = []
        for _c in _CP.get("clientes", []):
            _o = _c.get("objetivo") or {}
            _x = (_ob.get(_c["cliente_id"]) or {}).get("objetivo") or {}
            if _o.get("accion_id") and _x.get("accion_id") == _o.get("accion_id"):
                if (_o.get("cpl_objetivo"), _o.get("coste_cita_objetivo"), _o.get("leads_mes"), _o.get("ventas_mes"), bool(_o.get("cargado"))) != \
                   (_x.get("coste_lead"), _x.get("coste_cita"), _x.get("leads_mes"), _x.get("ventas_mes"), bool(_x.get("cargado"))):
                    _dif.append(_c["cliente_id"])
            elif _o.get("accion_id") and (_x.get("accion_id") or 0) < _o["accion_id"] and _OB.get("ultima_accion", 0) >= _o["accion_id"]:
                _dif.append(f'{_c["cliente_id"]}: captación lee la acción {_o["accion_id"]} y objetivos.json no')
        comprobar("objetivos (A4)", "Captación (y el número que manda de Mi día) usa el mismo objetivo que la ficha y Clientes nuevos", _dif)

# --- A8 · ALERTAS: UNA sola definición de cada contador («mías», «plazo pasado», «escaladas a ti», «pospuestas»…).
#     La define fuentes_alertas/generar_alertas.py (DEFINICIONES + CONTADORES, en cada p_<id>.json); la pantalla la
#     interpreta tal cual (bloque <contar> de modulos/alertas.js) y Mi día usa sus cifras. Antes Mili veía 14, 22 y 8.
#     Se comprueba: (1) contadores del fichero = la definición aplicada a sus alertas; (2) Mi día y el resumen diario =
#     contadores; (3) el bloque <contar> de alertas.js, ejecutado en Chromium, da lo mismo; (4) alertas.js no cuenta por
#     su cuenta (sin la regla vieja «dueno_id === yo»).
import glob as _glob
import re as _re_a8
from datetime import datetime as _dt_a8


def _a8_cumple(defs, nombre, H, yo):
    return all(_a8_cond(defs, c, H, yo) for c in defs[nombre]["si"])


def _a8_cond(defs, c, H, yo):
    if len(c) == 1:
        return _a8_cumple(defs, c[0], H, yo)
    if c[0] == "alguna":
        return any(_a8_cond(defs, x, H, yo) for x in c[1])
    campo, op, val = c
    val = yo if val == "yo" else val
    x = H.get(campo)
    return {"=": lambda: x == val, "!=": lambda: x != val, "en": lambda: x in val, ">": lambda: (x or 0) > val}[op]()


def _a8_hechos(a, ahora):
    v = a.get("vence")
    return {"estado": a.get("estado") or "nueva", "gravedad": a.get("gravedad"), "dueno": a.get("dueno_id"),
            "responsable": a.get("responsable_ahora") or a.get("dueno_id"), "nivel": (a.get("escalado") or {}).get("nivel") or 0,
            "vencida": bool(v and _dt_a8.fromisoformat(v) <= ahora)}


_a8_dif, _a8_md, _a8_sin_def, _a8_casos = [], [], [], []
for _f in sorted(_glob.glob(str(DATA / "alertas" / "p_*.json"))):
    _d = json.loads(Path(_f).read_text())
    _yo = _d.get("persona_id")
    if not _d.get("definiciones") or not _d.get("contadores_def"):
        _a8_sin_def.append(_yo)
        continue
    _ahora = _dt_a8.fromisoformat(_d["generado"])
    _hs = [_a8_hechos(a, _ahora) for a in _d.get("alertas", [])]
    _k = {n: sum(1 for H in _hs if all(_a8_cumple(_d["definiciones"], x, H, _yo) for x in ds)) for n, ds in _d["contadores_def"].items()}
    if _k != _d.get("contadores"):
        _a8_dif.append(f"{_yo}: fichero {_d.get('contadores')} · definición {_k}")
    _md, _rd = _d.get("mi_dia") or {}, _d.get("resumen_diario") or {}
    _par = [(_md.get("total"), _k["mias"]), (_md.get("urgentes"), _k["urgentes"]), (_md.get("plazo_pasado"), _k["plazo_pasado"]),
            (_md.get("escaladas_a_mi"), _k["escaladas_a_mi"]), (_rd.get("n", 0), _k["mias"])]
    if any(x != y for x, y in _par):
        _a8_md.append(f"{_yo}: Mi día/resumen {[x for x, _ in _par]} · contadores {[y for _, y in _par]}")
    _a8_casos.append({"yo": _yo, "defs": _d["definiciones"], "cont": _d["contadores_def"], "hechos": _hs, "esperado": _k})
comprobar("alertas", "A8 · cada p_<id>.json lleva la definición única de los contadores (definiciones + contadores_def)", _a8_sin_def)
comprobar("alertas", "A8 · contadores del fichero = la definición única aplicada a sus alertas («mías», «plazo pasado», «escaladas a ti»…)", _a8_dif)
comprobar("alertas", "A8 · Mi día (total, urgentes, plazo pasado, escaladas a ti) y el resumen diario = los mismos contadores", _a8_md)
_JS = (AQUI / "modulos" / "alertas.js").read_text()
_blq = _re_a8.search(r"// -+ <contar>.*?\n(.*?)// </contar>", _JS, _re_a8.S)
_viejas = [p for p in (r"dueno_id === yo\b", r"mias\s*=\s*abiertas\.filter", r"aFecha\(a\.vence\) < S\.ahora") if _re_a8.search(p, _JS)]
comprobar("alertas", "A8 · alertas.js cuenta SOLO con la definición del generador (bloque <contar>, sin reglas propias)",
          ([] if _blq and "D.definiciones" in _JS and "contadores_def" in _JS else ["falta el bloque <contar> o no lee D.definiciones"]) + _viejas)
if _blq and _a8_casos:
    try:
        if "--sin-navegador" in sys.argv:
            raise ImportError("Navegador omitido por opción explícita")
        from playwright.sync_api import sync_playwright as _spw
        with _spw() as _pw:
            _nav = _pw.chromium.launch()
            _pg = _nav.new_page()
            _js_k = _pg.evaluate("""([codigo, casos]) => { const f = new Function(codigo + '; return { cumpleTodas };')();
                return casos.map(c => Object.fromEntries(Object.entries(c.cont).map(([n, ds]) => [n, c.hechos.filter(H => f.cumpleTodas(c.defs, ds, H, c.yo)).length]))); }""",
                                 [_blq.group(1), _a8_casos])
            _nav.close()
        comprobar("alertas", "A8 · el bloque <contar> de alertas.js (en Chromium) da las mismas cifras que el generador para cada persona",
                  [f"{c['yo']}: generador {c['esperado']} · pantalla {k}" for c, k in zip(_a8_casos, _js_k) if k != c["esperado"]])
    except ImportError:
        avisos.append("A8 · sin Playwright no se ejecuta el bloque <contar> de alertas.js (se comprueba solo el fichero)")

# --- A1 · «LO MÍO» de Mi día (43_IDEAS_MEJORA): una sola lista personal sin duplicados cuyas alertas son EXACTAMENTE
#     las «mías» de Alertas. Mi día es JavaScript: (1) su copia del bloque <contar> es idéntica a la de alertas.js; (2) el
#     trozo puro <lo-mio> de mi_dia_bloques.js, ejecutado en Chromium con cada data/alertas/p_<id>.json a la hora del
#     fichero, da tantas alertas como el contador «mías» (= Alertas = generador); (3) al juntarlas con filas que repiten
#     su objeto o su tema (como hacían «Lo primero hoy», «Mis alertas» y el consejo), no queda ningún duplicado.
_MDB = (AQUI / "modulos" / "mi_dia_bloques.js").read_text()
_md_contar = _re_a8.search(r"// -+ <contar>.*?\n(.*?)// </contar>", _MDB, _re_a8.S)
comprobar("mi-dia", "A1 · «Lo mío» cuenta las alertas con la MISMA copia del bloque <contar> que alertas.js",
          [] if _md_contar and _blq and _md_contar.group(1) == _blq.group(1) else ["el bloque <contar> de mi_dia_bloques.js no es idéntico al de alertas.js"])
_lm = _re_a8.search(r"// <lo-mio>\n(.*?)// </lo-mio>", _MDB, _re_a8.S)
_mdjs = (AQUI / "modulos" / "mi_dia.js").read_text()
comprobar("mi-dia", "A1 · «Lo mío» funde «Lo primero hoy» y «Mis alertas» (sin listas paralelas) y usa alertasMias + unirLoMio",
          [x for x, ok in (("falta el trozo <lo-mio>", bool(_lm)), ("mi_dia.js no usa alertasMias", "alertasMias(" in _mdjs),
                            ("mi_dia.js no une con unirLoMio", "unirLoMio(" in _mdjs),
                            ("queda el panel «Lo primero hoy»", "titulo: 'Lo primero hoy'" not in _mdjs),
                            ("queda el panel «Mis alertas»", "titulo: 'Mis alertas'" not in _mdjs)) if not ok])
_pers = json.loads((DATA / "personas.json").read_text()) if (DATA / "personas.json").exists() else []
_lm_casos = []
for _f in sorted(_glob.glob(str(DATA / "alertas" / "p_*.json"))):
    _d = json.loads(Path(_f).read_text())
    if _d.get("definiciones") and _d.get("contadores_def"):
        _lm_casos.append({"yo": _d.get("persona_id"), "A": _d, "mias": (_d.get("contadores") or {}).get("mias")})
if _lm and _lm_casos:
    try:
        if "--sin-navegador" in sys.argv:
            raise ImportError("Navegador omitido por opción explícita")
        from playwright.sync_api import sync_playwright as _spw_lm
        with _spw_lm() as _pw:
            _nav = _pw.chromium.launch()
            _pg = _nav.new_page()
            _res = _pg.evaluate("""([codigo, casos, personas]) => {
                const f = new Function(codigo + '; return { alertasMias, unirLoMio, repetidosLoMio, objetoDe, temaAlerta };')();
                return casos.map(c => {
                  const ahora = new Date(String(c.A.generado).replace(' ', 'T'));
                  const al = f.alertasMias(c.A, [], { yo: c.yo, personas, ahora });
                  const filas = al.map(x => ({ tipo: 'alerta', clave: x.a.id, objeto: f.objetoDe(x.a.ir), grupos: [f.temaAlerta(x.a)], plazo: x.vence, grav: x.a.gravedad }));
                  // lo que antes salía repetido: «Lo primero hoy» y el consejo con el mismo objeto, el correo del mismo cliente
                  const repes = al.flatMap(x => [
                    { tipo: 'bloque', clave: `lp:${x.a.id}`, objeto: f.objetoDe(x.a.ir), grupos: [], plazo: null, grav: 'alta' },
                    ...(x.a.cliente_id ? [{ tipo: 'correo', clave: `correo:${x.a.id}`, objeto: `bandeja/otro-${x.a.id}`, grupos: [x.a.tipo === 'acc_correos' ? `correo-cli:${x.a.cliente_id}` : `tema-${x.a.id}`], plazo: null, grav: 'media' }] : []),
                  ]);
                  const u = f.unirLoMio([...filas, ...repes, ...filas.slice(0, 1)], ahora);
                  return { yo: c.yo, mias: c.mias, alertas: u.filas.filter(x => x.tipo === 'alerta').length, repetidos: f.repetidosLoMio(u.filas),
                           sin_quitar: u.filas.filter(x => x.tipo === 'bloque').length };
                });
            }""", [_lm.group(1), _lm_casos, [{"id": p["id"], "puestos": p.get("puestos", [])} for p in _pers]])
            _nav.close()
        comprobar("mi-dia", "A1 · alertas de «Lo mío» = contador «mías» de Alertas (= generador) para cada persona",
                  [f"{r['yo']}: Lo mío {r['alertas']} · mías {r['mias']}" for r in _res if r["alertas"] != r["mias"]])
        comprobar("mi-dia", "A1 · «Lo mío» no tiene duplicados (ni claves ni objetos ni temas repetidos fuera de las alertas)",
                  [f"{r['yo']}: {r['repetidos'][:3]} · filas de «Lo primero» sin quitar {r['sin_quitar']}" for r in _res if r["repetidos"] or r["sin_quitar"]])
    except ImportError:
        avisos.append("A1 · sin Playwright no se ejecuta el trozo <lo-mio> de mi_dia_bloques.js")

# --- R15 (A6) · CONTADORES DEL MENÚ = LAS PANTALLAS. Con la app de verdad (servir.py en 127.0.0.1 con una COPIA de
#     local.db) y Chromium: el número de «Alertas» en el menú = «mías» de la pantalla Alertas (su bloque <contar>) y = las
#     alertas de «Lo mío» (alertasMias); «Producción» = «vencidas» de su fila en Producción (personas[].vencidas tras alDia() con el hoy de
#     Madrid, la cifra de «Mi cola»; R16c); «Chat» = menciones sin leer de la campana; «Bandeja» = correos de «Lo mío» (correosLoMio).
#     Sin Playwright, aviso. RO_PUERTOS_PRUEBA=9075-9079 cambia el rango de puertos (por defecto 8920-8929).
def _r15_menu():
    import os, shutil, socket, subprocess, tempfile, time, urllib.request
    try:
        from playwright.sync_api import sync_playwright as _spw15
    except ImportError:
        avisos.append("R15 · sin Playwright no se comparan los contadores del menú con las pantallas")
        return
    ini, fin = (int(x) for x in os.environ.get("RO_PUERTOS_PRUEBA", "8920-8929").split("-"))
    puerto = None
    for pu in range(ini, fin + 1):
        with socket.socket() as so:
            try:
                so.bind(("127.0.0.1", pu)); puerto = pu; break
            except OSError:
                continue
    if not puerto:
        avisos.append(f"R15 · sin puerto libre en {ini}-{fin}: no se comparan los contadores del menú")
        return
    tmp = Path(tempfile.mkdtemp())
    shutil.copy(AQUI / "local.db", tmp / "c.db")
    (tmp / "recarga.json").write_text('{"ligera": [], "conexiones": []}')
    env = {**os.environ, "RO_DB": str(tmp / "c.db"), "RO_RECARGA_CONFIG": str(tmp / "recarga.json")}
    env.pop("RO_MODO", None)
    srv = subprocess.Popen([sys.executable, "servir.py", "--bind", "127.0.0.1", "--puerto", str(puerto)], cwd=AQUI, env=env,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    B = f"http://127.0.0.1:{puerto}"
    try:
        for _ in range(80):
            try:
                urllib.request.urlopen(B + "/index.html", timeout=1); break
            except Exception:
                time.sleep(0.3)
        difs, vistos = [], []
        with _spw15() as pw:
            nav = pw.chromium.launch()
            for yo in ("lucia", "mili", "candela", "valeria", "tomas", "camilo"):
                ctx = nav.new_context(viewport={"width": 1440, "height": 900})
                ctx.add_cookies([{"name": "ro_yo", "value": yo, "url": B}])
                pg = ctx.new_page()
                pg.goto(f"{B}/?yo={yo}#/en-rojo")
                pg.wait_for_function("() => window.RO?.estado?.contadores !== undefined && document.querySelector('#opinion-btn')", timeout=60000)
                pg.wait_for_timeout(1500)
                menu = pg.evaluate("""() => Object.fromEntries([...document.querySelectorAll('#nav a[data-id]')].map(a => [a.dataset.id, Number((a.querySelector('.n')?.textContent || '0').replace('99+', '100'))]))""")
                C = pg.evaluate("() => window.RO.estado.contadores")
                # 1) lo pintado = lo contado
                for k, n in C.items():
                    if k in menu and (n or 0) != menu[k]:
                        difs.append(f"{yo}: {k} contado {n} y pintado {menu[k]}")
                # 2) Alertas: el menú = «mías» de la pantalla Alertas (su propio bloque <contar>)
                if "alertas" in menu:
                    pg.evaluate("location.hash = '#/alertas'")
                    pg.wait_for_selector("[data-contadores]", timeout=60000)
                    mias = pg.evaluate("() => JSON.parse(document.querySelector('[data-contadores]').dataset.contadores).mias")
                    if mias != menu["alertas"]:
                        difs.append(f"{yo}: Alertas en el menú {menu['alertas']} · pantalla Alertas {mias}")
                    vistos.append(f"{yo} alertas {menu['alertas']}={mias}")
                # 3) «Lo mío» (alertasMias, correosLoMio) y Producción, con los datos que recibe la persona
                otro = pg.evaluate("""async () => {
                    const LM = await import('./modulos/mi_dia_bloques.js');
                    const RO = window.RO, yo = RO.estado.persona.id, out = {};
                    try { const A = await RO.api(`modulo/alertas/p_${yo}`); const acc = await RO.api('acciones?modulo=alertas');
                          out.alertas = LM.alertasMias(A, acc.acciones || [], { yo, personas: RO.estado.datos.personas }).length; } catch { }
                    try { const PC = await import('./modulos/produccion_comun.js'); const p = PC.alDia(structuredClone(await RO.api('modulo/produccion/produccion'))); out.produccion = (p.personas || []).find(x => x.persona_id === yo)?.vencidas || 0; } catch { }   // R16c: la pantalla reagrupa con alDia (hoy de Madrid)
                    try { out['chat-equipo'] = (await RO.api('canales/campana')).menciones || 0; } catch { }
                    return out; }""")
                for k, n in otro.items():
                    if k in menu and (n or 0) != menu[k]:
                        difs.append(f"{yo}: {k} en el menú {menu[k]} · {'«Lo mío»' if k == 'alertas' else 'su pantalla'} {n}")
                vistos.append(f"{yo} {menu}")
                ctx.close()
            nav.close()
        comprobar("menú (carcasa)", "R15 · contadores del menú = Alertas («mías»), «Lo mío», Producción («vencidas» de tu cola) y la campana", difs)
        print("   ", " · ".join(v for v in vistos if " alertas " in v))
    finally:
        srv.terminate()
        try:
            srv.wait(timeout=10)
        except Exception:
            srv.kill()
        shutil.rmtree(tmp, ignore_errors=True)


# --- V2-B · IA Y CONSEJOS (3-oct): la «vara de rojo» del consejo y del copiloto es la de la verdad única; el buscador
#     abre el mismo correo «más antiguo» que Bandeja y Mi día. Solo ficheros (los consejos precalculados) y el código.
ADOPTADOS |= {"consejos (IA)", "copiloto (IA)", "buscador (⌘K)"}
_difs_crit, _difs_sub = [], []
for _f in sorted((DATA / "consejos").glob("p_*.json")):
    try:
        _d = json.loads(_f.read_text())
    except Exception:
        continue
    for _c in _d.get("candidatos") or []:
        _v = ver.get(_c.get("cliente_id")) or {}
        if "crítico" in (_c.get("que") or "") and _c.get("cliente_id") and _v.get("gravedad") != "critico":
            _difs_crit.append(f"{_f.stem}: «{_c['que'][:50]}» ({_v.get('gravedad')})")
        if _c.get("tipo") == "crm_sin_usar" and (_v.get("nuevo") or (isinstance(_v.get("dia_alta"), int) and _v["dia_alta"] < 90)):
            _difs_sub.append(f"{_f.stem}: archivar subcuenta de {_c.get('cliente')} (alta de {_v.get('dia_alta')} días)")
comprobar("consejos (IA)", "V2 · un consejo solo dice «crítico» si la verdad única lo tiene en crítico", _difs_crit)
comprobar("consejos (IA)", "V2 · nunca proponer archivar la subcuenta de un alta de menos de 90 días", _difs_sub)
_ia = (AQUI / "ia.py").read_text()
_comp = (AQUI / "modulos/ia_componentes.js").read_text()
_difs_cop = []
if "color_verdad(cid" not in _ia or _ia.count("color_verdad(") < 3:
    _difs_cop.append("ia.py no pinta el color del copiloto con la gravedad de la verdad única (color_verdad)")
if "rojo: ['rojo', 'Crítico']" not in _comp:
    _difs_cop.append("ia_componentes.js no nombra el color como En rojo («Crítico/Atención/Bien»)")
comprobar("copiloto (IA)", "V2 · el copiloto pinta crítico/atención/bien de la verdad única, no el color de la IA", _difs_cop)
_ay = (AQUI / "ayudas.js").read_text()
_md = (AQUI / "modulos/mi_dia_bloques.js").read_text()
_difs_bus = []
if "!x.auto && !x.viejo" not in _md.replace("!x.auto && !x.boletin && !x.viejo", "!x.auto && !x.viejo"):
    _difs_bus.append("mi_dia_bloques.js ya no usa la regla de la Bandeja (bandejaComoPantalla): revisar ayudas.js → correosVivos")
if "!x.auto && !x.boletin && !x.viejo" not in _ay or "PAL.vivos.has(" not in _ay:
    _difs_bus.append("ayudas.js: «Contestar el correo más antiguo» no filtra con la regla de la Bandeja")
comprobar("buscador (⌘K)", "V2 · «Contestar el correo más antiguo» = el más antiguo de Bandeja y Mi día (sin automáticos ni boletines)", _difs_bus)


# --- V2-E · LO COMÚN (3-oct): una sola vara en la carcasa. (1) El número de «En rojo» del menú y los puntos de «Mis
#     clientes» salen de la gravedad de la verdad única (la de la pantalla En rojo), sin caer a las alarmas del panel;
#     (2) «hoy», «vencida», «esta semana» y «último laborable» salen del helper común de fechas (Madrid), probado en
#     Chromium con un hoy fijo; (3) ningún id interno de departamento sin nombre; (4) plural común. Los módulos que aún
#     calculan «hoy» por su cuenta salen como AVISO para su dueño.
def _v2e():
    import re as _re
    app = (AQUI / "app.js").read_text()
    comp = (AQUI / "componentes.js").read_text()
    difs_menu = []
    if "estado.datos.alarmas.filter(a => a.ambito === 'cliente'" in app:
        difs_menu.append("app.js: el número de «En rojo» del menú vuelve a caer a las alarmas del panel (otra vara)")
    if "estado.verdad.comun.filter(c => c.gravedad === 'critico')" not in app:
        difs_menu.append("app.js: el número de «En rojo» del menú no cuenta los críticos de la verdad única")
    if "const gravedadVerdad = id => estado.verdad?.porId?.[id]?.gravedad || estado.verdad?.comunPorId?.[id]?.gravedad" not in app:
        difs_menu.append("app.js: «Mis clientes» no pinta la gravedad de la verdad única (gravedadVerdad)")
    _mis = app[app.find("function misClientesMenu"):app.find("function marcarActual")]
    if "alarmas" in _mis or "salud" in _mis:
        difs_menu.append("app.js: «Mis clientes» usa alarmas o salud en vez de la gravedad de la verdad única")
    _er = (AQUI / "modulos/en_rojo.js").read_text()
    if "ctx.verdadComun()" not in _er:
        difs_menu.append("en_rojo.js ya no lee ctx.verdadComun(): el número del menú y el de la pantalla pueden separarse")
    # con los datos: los críticos de la verdad (lo que cuenta el menú) = los del detalle (lo que pinta Mis clientes)
    difs_menu += [f"{cid}: común {c['gravedad']} ≠ detalle {ver[cid]['gravedad']}" for cid, c in comun.items() if cid in ver and ver[cid]["gravedad"] != c["gravedad"]]
    comprobar("menú (carcasa)", "V2-E · «En rojo» del menú y «Mis clientes» = gravedad de la verdad única (la vara de En rojo)", difs_menu)

    difs_f = []
    if "hoy: fechas.hoy()," not in app or "fechas," not in app:
        difs_f.append("app.js: ctx no da ctx.hoy / ctx.fechas del helper común")
    if "timeZone: zona" not in comp or "const ZONA_RO = 'Europe/Madrid'" not in comp:
        difs_f.append("componentes.js: el helper de fechas ya no usa la hora de Madrid")
    try:
        if "--sin-navegador" in sys.argv:
            raise ImportError("Navegador omitido por opción explícita")
        from playwright.sync_api import sync_playwright as _spw
    except ImportError:
        _spw = None
        avisos.append("V2-E · sin Playwright no se prueba el helper de fechas en Chromium")
    if _spw:
        CASOS = r"""async () => {
          const C = await import('/componentes.js');
          C.fijarHoy('2026-10-03');                    // sábado 3 de octubre
          const f = C.fechas, r = {};
          r.hoy = f.hoy(); r.ayer = f.ayer(); r.ult = f.ultimoLaborable();
          r.venc_ayer = f.vencida('2026-10-02 18:00'); r.venc_hoy = f.vencida('2026-10-03'); r.vence_hoy = f.venceHoy('2026-10-03 23:00');
          r.sem = f.semana(); r.sem_lun = f.estaSemana('2026-09-28'); r.sem_sig = f.estaSemana('2026-10-05');
          r.utc = f.dia('2026-10-02T23:30:00Z');         // 01:30 del 3 en Madrid
          r.rel = [f.relativo('2026-10-02'), f.relativo('2026-10-04'), f.relativo('2026-09-30'), f.relativo('2026-09-01')];
          r.datos = f.diaDatos('2026-10-02 23:14').texto;
          r.ant = [f.antiguedad(30), f.antiguedad(478)];
          r.plural = [C.fmt.plural(1, 'cita'), C.fmt.plural(3, 'mes'), C.fmt.plural(2, 'acción')];
          r.texto = [C.formatoTexto('1 correos sin contestar'), C.formatoTexto('hace 1 días'), C.formatoTexto('21 leads'), C.formatoTexto('el más antiguo lleva 478 h'), C.formatoTexto('152 h imputadas')];
          r.dep = [C.quitaPrefijoDepartamento('administracion · POWER GLOBAL'), C.quitaPrefijoDepartamento('rrhh'), C.quitaPrefijoDepartamento('altas en curso')];
          r.hace = C.fmt.hace('2026-10-02T22:30:00Z');
          C.fijarHoy(null);
          return r;
        }"""
        ESPERA = {"hoy": "2026-10-03", "ayer": "2026-10-02", "ult": "2026-10-02", "venc_ayer": True, "venc_hoy": False, "vence_hoy": True,
                  "sem": {"desde": "2026-09-28", "hasta": "2026-10-04"}, "sem_lun": True, "sem_sig": False, "utc": "2026-10-03",
                  "rel": ["ayer", "mañana", "el mié 30", "1-sep"], "datos": "datos de ayer (vie 2)", "ant": ["30 h", "20 días"],
                  "plural": ["1 cita", "3 meses", "2 acciones"],
                  "texto": ["1 correo sin contestar", "hace 1 día", "21 leads", "el más antiguo lleva 20 días", "152 h imputadas"],
                  "dep": ["Administración · POWER GLOBAL", "RRHH", "altas en curso"], "hace": "hoy"}
        try:
            with _spw() as p:
                b = p.chromium.launch()
                pg = b.new_page()
                def _servir(route):
                    ruta = route.request.url.split("prueba.local/", 1)[1].split("?")[0] or "x.html"
                    f = AQUI / ruta
                    if ruta == "x.html":
                        route.fulfill(status=200, content_type="text/html", body="<!doctype html><title>x</title>")
                    elif f.is_file() and f.suffix == ".js":
                        route.fulfill(status=200, content_type="text/javascript", body=f.read_text())
                    else:
                        route.fulfill(status=404, body="")
                pg.route("http://prueba.local/**", _servir)
                pg.goto("http://prueba.local/x.html")
                r = pg.evaluate(CASOS)
                b.close()
            for k, v in ESPERA.items():
                if r.get(k) != v:
                    difs_f.append(f"{k}: sale {r.get(k)!r}, debería {v!r}")
        except Exception as e:
            avisos.append(f"V2-E · no se pudo probar el helper de fechas en Chromium: {e}")
    comprobar("menú (carcasa)", "V2-E · «hoy», «vencida», «esta semana», «último laborable» y plural: una sola definición (Madrid)", difs_f)

    # (3) departamentos con nombre
    deps = (leer("departamentos.json") or {})
    deps = deps.get("departamentos", deps) if isinstance(deps, dict) else {}
    faltan = [d for d in deps if isinstance(deps[d], dict) and f"{d}: '" not in comp[comp.find("NOMBRE_DEPARTAMENTO = {"):comp.find("NOMBRE_DEPARTAMENTO = {") + 600]]
    comprobar("menú (carcasa)", "V2-E · cada departamento tiene nombre para la persona (nunca «administracion ·» ni «rrhh ·»)", faltan)

    # (4) módulos que todavía calculan «hoy» por su cuenta (UTC o zona del Mac): aviso para su dueño
    RX = _re.compile(r"new Date\(\)\.toISOString\(\)\.slice\(0,\s*10\)")
    propios = []
    for fj in sorted((AQUI / "modulos").glob("*.js")) + [AQUI / "ayudas.js"]:
        n = len(RX.findall(fj.read_text()))
        if n:
            propios.append(f"{fj.name} ({n})")
    comprobar("fechas (módulos)", "V2-E · ningún módulo calcula «hoy» en UTC: usar ctx.hoy / ctx.fechas (LEEME › Fechas)", propios)


_v2e()


# --- V2-C1 · CAPTACIÓN, FICHA, CRM, NUEVOS, BANDEJA Y CONEXIONES (3-oct): una sola vara de gravedad y de cartera.
# (1) La cartera de publicidad de Captación (carteras_publicidad) = la de la verdad única; (2) «críticos» = gravedad de la verdad;
# (3) «Publicidad en orden» nunca con un aviso de integración; (4) Crítico/Atención/Bien en Captación solo de la verdad;
# (5) boletines fuera de «sin contestar»; (6) dueño único de cada conexión y sin órdenes de terminal; (7) 1 de 8 = 13 %;
# (8) la ficha básica no salta a otro cliente.
def _v2c1():
    import re as _re
    cap = leer("captacion/captacion.json") or {}
    filas = {f["cliente_id"]: f for f in cap.get("clientes", [])}
    cp = cap.get("carteras_publicidad") or {}
    difs = []
    for cv in V.get("carteras", []):
        if cv.get("silla") != "trafficker":
            continue
        x = cp.get(cv["persona_id"])
        if not x:
            difs.append(f"{cv['persona_id']}: sin cartera de publicidad en captacion.json")
            continue
        pri = cv.get("principal") or []
        con = [i for i in pri if i in filas and not filas[i].get("solo_google")]
        esp = {"cartera": len(pri), "apoyo": len(cv.get("apoyo") or []), "con_meta": len(con),
               "meta_encendida": sum(1 for i in con if filas[i].get("meta_activa")),
               "criticos": sum(1 for i in con if (ver.get(i) or {}).get("gravedad") == "critico")}
        for k, v in esp.items():
            if x.get(k) != v:
                difs.append(f"{cv['persona_id']}.{k}: {x.get(k)} frente a {v}")
        u = (cv.get("universo") or {}).get("dentro")
        if u is not None and u != x.get("con_meta"):
            difs.append(f"{cv['persona_id']}: «con cuenta de Meta» {x.get('con_meta')} frente al universo de la verdad {u}")
    comprobar("captacion", "V2-C1 · cartera de publicidad (cartera, apoyo, con Meta, encendidas, críticos) = verdad única", difs)
    casa = sorted(i for i, f in filas.items() if not f.get("solo_google") and (ver.get(i) or {}).get("gravedad") == "critico")
    comprobar("captacion", "V2-C1 · críticos de la casa = gravedad «crítico» de la verdad", [] if cap.get("criticos_casa") == casa else [f"{cap.get('criticos_casa')} frente a {casa}"])
    mal = [i for i, f in filas.items() if f.get("severidad") == "ok" and any(a.get("clase_id") == "integracion" for a in f.get("avisos") or [])]
    comprobar("captacion", "V2-C1 · «Publicidad en orden» nunca con un problema de integración abierto (Accompany: CRM no conectado)", mal)
    js = (AQUI / "modulos" / "captacion.js").read_text()
    g = js[js.find("const GRAV = {"):js.find("const chipPub")]
    d4 = []
    if _re.search(r"'(Crítico|Atención|Bien)'", g):
        d4.append("el estado de la publicidad usa las palabras de la gravedad del cliente")
    if "ctx.verdad(c.cliente_id)" not in js or "chipEstado(GRAV[f.severidad]" in js or "chipEstado(GRAV[c.severidad].e, GRAV[c.severidad].t)" in js:
        d4.append("Captación pinta Crítico/Atención/Bien sin leer la verdad única")
    comprobar("captacion", "V2-C1 · Crítico/Atención/Bien en Captación = gravedad de la verdad única; la publicidad con otro nombre", d4)
    B = leer("bandeja/bandeja.json") or {}
    PC = {r["cliente_id"]: r for r in (leer("bandeja/por_cliente.json") or {}).get("clientes", [])}
    bol = [c for c in B.get("correos", []) if c.get("boletin")]
    d5 = [c["numero"] for c in bol if not c.get("auto")]
    d5 += [f"{c['numero']} es el «más antiguo» de {c['cliente_id']}" for c in bol if ((PC.get(c.get("cliente_id")) or {}).get("mas_antiguo") or {}).get("numero") == c["numero"]]
    d5 += [c["numero"] for c in B.get("correos", []) if _re.search(r"descúbrelo|en esta gu[ií]a|nota informativa", c.get("asunto") or "", _re.I) and not c.get("auto")]
    comprobar("bandeja", "V2-C1 · boletines y circulares fuera de «sin contestar» (ni días ni gravedad)", d5)
    cj = (AQUI / "modulos" / "ajustes_conexiones.js").read_text()
    d6 = []
    if not _re.search(r"google_ads:\s*\{\s*hace:\s*'Tomás',\s*comprueba:\s*'Agus'", cj):
        d6.append("Google Ads: el dueño no es «lo hace Tomás, lo comprueba Agus»")
    if "duenoConexion" not in js:
        d6.append("Captación no lee el dueño de la conexión de Conexiones")
    if not _re.search(r"sinTerminal\(\w+\.que_hacer\)", cj):   # 3-oct: la variable puede llamarse c, f…
        d6.append("Conexiones enseña el «qué hacer» con órdenes de terminal")
    if _re.search(r"lo conecta Agus", js):
        d6.append("Captación dice «lo conecta Agus»")
    comprobar("captacion", "V2-C1 · un solo dueño por conexión (Captación = Conexiones) y nada de órdenes de terminal a la vista", d6)
    N = leer("nuevos/nuevos.json") or {}
    e = (N.get("resumen") or {}).get("en_plazo_dia12") or {}
    d7 = [] if not e.get("de") or e.get("pct") == int(e["si"] / e["de"] * 100 + 0.5) else [f"{e}"]
    comprobar("clientes-nuevos", "V2-C1 · «altas en plazo» redondea como la pantalla (1 de 8 = 13 %)", d7)
    fj = (AQUI / "modulos" / "ficha.js").read_text()
    b = fj[fj.find("async function pintarBasica"):fj.find("async function pintarInformes")]
    d8 = [] if "!items.some(x => x.id === idParam)" in b else ["la ficha básica cae en el primer cliente cuando piden uno que no es suyo"]
    comprobar("ficha", "V2-C1 · la ficha de un cliente ajeno nunca enseña OTRO cliente sin avisar", d8)


_v2c1()

# --- V2 · carril V2-C2 (Redes, SEO, Producción, Personas, Finanzas, Dinero, Ventas, Setters, Outreach, Panel, En rojo):
#     UNA SOLA VARA. Cada cifra que salía distinta en dos pantallas sale ahora de una definición; aquí se comprueba.
import re as _rv2
_js2 = lambda f: (AQUI / "modulos" / f).read_text()
_RD2 = leer("redes/redes.json")
if _RD2:
    _asg = json.loads((DATA / "asignaciones.json").read_text()) if (DATA / "asignaciones.json").exists() else []
    _met = {c["cliente_id"] for c in _RD2.get("clientes", [])}
    _dif = []
    for _pp in _RD2.get("por_persona", []):
        _sil = {a["cliente_id"] for a in _asg if a.get("persona_id") == _pp["persona_id"] and a.get("silla") == "redes" and not a.get("hasta")}
        if _sil and len(_sil & _met) != _pp["principal_en_metricool"] + _pp["apoyo_en_metricool"]:
            _dif.append(f'{_pp["persona_id"]}: silla {len(_sil & _met)} · por_persona {_pp["principal_en_metricool"] + _pp["apoyo_en_metricool"]}')
    comprobar("redes", "V2 · «tus clientes de redes» = la silla redes de asignaciones (lleva + ayuda), la misma base que Mi día (Lara 0 de 14, no 0 de 4)",
              _dif + ([] if "carteraPorSilla?.redes" in _js2("redes.js") else ["redes.js no lee la silla redes"]))
_WB2 = leer("seo/webs.json")
if _WB2:
    _um = ((_WB2.get("_meta") or {}).get("lenta") or {}).get("umbral_ms")
    _regla = [w["nombre"] for w in _WB2.get("webs", []) if w.get("lenta") != bool((w.get("comprobacion") or {}).get("estado") and 200 <= w["comprobacion"]["estado"] < 400 and (w["comprobacion"].get("ms") or 0) >= (_um or 10**9))]
    comprobar("seo-web", "V2 · una sola «web lenta» (webs.json › _meta.lenta): cada web la marca la regla y el resumen la cuenta (antes 3, 10 y 14)",
              _regla + ([] if (_WB2.get("resumen") or {}).get("lentas") == sum(1 for w in _WB2.get("webs", []) if w.get("lenta")) else ["resumen.lentas"])
              + ([] if "esLenta" in _js2("seo.js") and ">= 5000).length" not in _js2("seo.js") else ["seo.js cuenta lentas por su cuenta"]))
_SE2 = leer("seo/seo.json")
if _SE2:
    _r = _SE2.get("resumen") or {}
    comprobar("seo-web", "V2 · con SE Ranking en duda, el número que manda va «a medias» y en gris con su motivo (nunca verde ni rojo apoyado en él)",
              [] if (not _r.get("aviso_seranking") or (_r.get("estado_mostrado") == "gris" and _r.get("medible") == "medias" and _r.get("motivo_medible"))) and "enDuda" in _js2("seo.js") else [str({k: _r.get(k) for k in ("estado_mostrado", "medible")})])
    comprobar("seo-web", "V2 · visibilidad de 7 días «sin dato fiable» cuando SE Ranking dejó de ver más de 3 palabras del cliente (nada de −100 % en rojo)",
              [c["cliente_id"] for c in _SE2.get("clientes", []) if c.get("visibilidad") and c["visibilidad"].get("fiable") != ((c["visibilidad"].get("desaparecen") or 0) <= 3)])
# «hoy» real: los módulos del carril cuentan con la fecha de Madrid de hoy (hoyMadrid), no con el día del dato
comprobar("produccion", "V2 · «hoy» real en Redes, Ventas, Producción, Finanzas, Setters y Personas (helper común hoyMadrid; nada de «VI 2 · hoy» un sábado)",
          [f for f in ("redes.js", "ventas_ro.js", "produccion_comun.js", "finanzas.js", "setters.js", "personas.js", "personas_comun.js") if "hoyMadrid" not in _js2(f)]
          + ([] if "alDia(" in _js2("produccion.js") else ["produccion.js no reagrupa con hoy"]))
_PR2 = leer("produccion/produccion.json")
if _PR2:
    import datetime as _dtv2
    _hoy = _dtv2.date.today().isoformat()
    _mal = [r["id"] for r in _PR2.get("cola", []) if r.get("grupo") == "hoy" and r.get("vence") and r["vence"] < _hoy and r.get("vencida") is False and _PR2.get("hoy") == _hoy]
    comprobar("produccion", "V2 · «Para hoy» nunca lleva vencidas (con datos de hoy; con datos de otro día las reagrupa alDia)", _mal)
_AR = json.loads((AQUI / "reglas_permisos.json").read_text()).get("revision_piezas", {}).get("areas_tecnica")
comprobar("produccion", "V2 · revisión técnica por área (areas_tecnica): Producción no ofrece «Aprobar» a la jefa de otra área",
          [] if _AR and "deMiArea" in _js2("produccion.js") else ["sin filtro por área"])
comprobar("personas", "V2 · «Ayer sin imputar» sobre la gente que ves (Valeria 0 de 4) y la misma banda de exceso para todos (Emanuel 136 %)",
          [x for x, ok in (("base", "equipo && verCola && VE?.cuentan" in _js2("personas.js")), ("banda", "horas por encima" in _js2("personas.js"))) if not ok])
_VR2 = leer("ventas_ro/ventas_ro.json")
_PS2 = leer("panel_direccion/captacion_sep.json")
if _VR2 and _PS2:
    _m9 = (_VR2.get("meses") or {}).get("2026-09") or {}
    _cpc = round(_m9["inversion"] / _m9["firmados"]) if _m9.get("firmados") else None
    _txt = _rv2.sub(r"<[^>]+>", " ", json.dumps(_PS2, ensure_ascii=False).replace('\\"', '"'))
    _g = _rv2.search(r"Coste por cliente firmado, contra tu límite\s+([\d.]+)\s*€", _txt)
    _pan = int(_g.group(1).replace(".", "")) if _g else None
    comprobar("ventas-ro", "V2 · coste por cliente de septiembre: Ventas de RO = Panel de dirección (735 €), con la misma regla de color",
              [] if _cpc is not None and _pan == _cpc and "colorCifra('coste_cliente'" in _js2("ventas_ro.js") and "colorCifra('coste_cliente'" in _js2("panel_direccion.js") else [f"ventas {_cpc} · panel {_pan}"])
comprobar("dinero-cliente", "V2 · «Facturado» con su base dicha en pantalla (estos clientes frente a toda la empresa) y un solo «sin línea» (7 = el chip)",
          [x for x, ok in (("base", "ESTOS MISMOS clientes" in _js2("dinero_cliente.js") and "toda la empresa" in _js2("finanzas.js")),
                           ("sin_linea", "'cuota_en_facturacion' in f);" in _js2("dinero_cliente.js"))) if not ok])
_OU2 = leer("ventas_ro/outreach.json")
if _OU2:
    comprobar("prospeccion", "V2 · cada campaña y respuesta de clientes lleva su cliente (una regla: fuentes_ventas/campana_cliente.py) y la pantalla recorta por la cartera de outreach",
              [r.get("campana") or r.get("nombre") for r in (_OU2.get("respuestas") or []) + ((_OU2.get("snov") or {}).get("campañas") or []) if r.get("frente") == "clientes" and not r.get("cliente_id")][:6]
              + ([] if "carteraPorSilla?.outreach" in _js2("outreach.js") else ["outreach.js sin recorte por cartera"]))
_CP2 = leer("captacion/captacion.json") or {}
_cpp = _CP2.get("carteras_publicidad") or {}
comprobar("personas", "V2 · la cartera de publicidad de Personas (Carga y ficha) = la única de Captación y Mi día (principal; apoyo aparte, no cuenta contra 16)",
          [f'{c["persona_id"]}: verdad {c["n_principal"]} · captación {(_cpp.get(c["persona_id"]) or {}).get("cartera")}' for c in V.get("carteras", [])
           if c.get("silla") == "trafficker" and c["persona_id"] in _cpp and _cpp[c["persona_id"]].get("cartera") != c["n_principal"]]
          + ([] if "x.cartera.trafficker = v.n_principal" in _js2("personas.js") else ["personas.js suma principal + apoyo"]))
comprobar("en-rojo", "V2 · los setters no ven «En rojo» (guía 14) en el módulo", [] if "setters: null" in _js2("en_rojo.js") else ["en_rojo.js"])
_txt_int = _rv2.compile(r"FIN §|regla «inversion»|\(ver\)|--en-vivo|Promethean|07 §|04 §")
comprobar("finanzas", "V2 · sin textos internos a la vista (FIN §6, «regla «inversion»», «(ver)», Promethean, «07 §2»)",
          [f for f in ("finanzas.js", "personas.js", "dinero_cliente.js", "dinero_m16_anuncios.js", "panel_direccion.js") if _txt_int.search("\n".join(l for l in _js2(f).split("\n") if not l.lstrip().startswith(("//", "*", "/*"))))]
          + (["finanzas.json"] if "FIN §" in json.dumps(leer("finanzas/finanzas.json") or {}, ensure_ascii=False) else []))

# --- V2-A · MI DÍA (3-oct): UNA SOLA VARA en Mi día. (1) La revisión técnica va a la jefa del ÁREA del autor
#     (revision_piezas.areas_tecnica, la misma regla que servir.py → puede_revisar_pieza): ninguna pieza a dos jefas, y lo
#     huérfano a operaciones. (2) «Rojo» = crítico de la verdad única en todos los bloques (Mili, Coti, semáforo, fuegos).
#     (3) El número del account mide solo campañas activas; sin campaña no cuenta como fallo (feedback 3-oct).
#     (4) Contadores con la definición de su pantalla (Bandeja, Producción, Personas, Captación, webs). (5) «Lo mío» y el
#     consejo por pestaña de puesto, vencidas con su fecha y la cola con alDia(). (6) Como mucho 7 piezas a la vista.
_MDB2 = (AQUI / "modulos" / "mi_dia_bloques.js").read_text()
_MDJ2 = (AQUI / "modulos" / "mi_dia.js").read_text()
_CFG2 = leer("mi_dia/config.json") or {}
_REG2 = json.loads((AQUI / "reglas_permisos.json").read_text()).get("revision_piezas") or {}
_PERS2 = leer("personas.json") or []
_PERS2 = _PERS2 if isinstance(_PERS2, list) else _PERS2.get("personas", [])
_pp2 = {q["id"]: q for q in _PERS2}


def _revisor_tecnica(autores, regla):
    """Réplica en Python de revisorTecnica() de mi_dia_bloques.js (y de servir.puede_revisar_pieza)."""
    areas = _REG2.get("areas_tecnica") or {}
    jefas_de = lambda j: [q["id"] for q in _PERS2 if j in (q.get("puestos") or []) and q.get("estado") != "baja"]  # noqa: E731
    out = set()
    for aid in autores:
        a = _pp2.get(aid) or {}
        for j in (regla.get("puestos") or list(areas)):
            jefe = a.get("jefe")
            su_jefa = jefe if jefe and j in (_pp2.get(jefe, {}).get("puestos") or []) else None
            if su_jefa and su_jefa != aid:
                out.add(su_jefa)
            elif set(a.get("puestos") or []) & set(areas.get(j, [])):
                out |= {q for q in jefas_de(j) if q != aid}
    return out


_mal_v2 = []
_PR2 = leer("produccion/produccion.json") or {}
if _PR2 and _REG2.get("areas_tecnica"):
    _por_nombre = {}
    for q in _PERS2:
        for f in (q.get("alias"), q.get("nombre"), (q.get("nombre") or "").split(" ")[0]):
            if f:
                _por_nombre[f.strip().lower()] = q["id"]
    _pz = {}
    for r in _PR2.get("cola", []):
        if r.get("grupo") == "revision":
            _pz.setdefault(r["id"], {"estado": r.get("estado"), "dias": r.get("dias_estado") or 0, "autores": set()})["autores"].add(r.get("persona_id"))
    for r in _PR2.get("revisiones", []):
        if r.get("estado") == "bloqueado":
            continue
        x = _pz.setdefault(r["id"], {"estado": r.get("estado"), "dias": r.get("dias") or 0, "autores": set()})
        x["autores"] |= {_por_nombre[n.strip().lower()] for n in r.get("asignados") or [] if n.strip().lower() in _por_nombre}
    _regla_t = (_REG2.get("por_estado") or {}).get("revisión técnica") or {}
    _a_jefas = {}
    for tid, x in _pz.items():
        if x["estado"] != "revisión técnica" or x["dias"] > 30:
            continue
        rv = _revisor_tecnica(x["autores"], _regla_t)
        if len(rv) > 1:
            _mal_v2.append(f"{tid}: va a {sorted(rv)}")
        for j in rv:
            _a_jefas[j] = _a_jefas.get(j, 0) + 1
    print("    revisión técnica por jefa:", _a_jefas)
comprobar("mi-dia", "V2 · la revisión técnica va a UNA jefa, la del área del autor (areas_tecnica, como servir.py); lo huérfano a operaciones",
          _mal_v2 + [f"falta {t}" for t in ("revisorTecnica(ctx, [...x.autores], regla)", "areas_tecnica") if t not in _MDB2])


def _trozo2(nombre):
    import re as _r2
    m = _r2.search(r"\n(?:def|num)\('" + _r2.escape(nombre) + r"'.*?(?=\n(?:def|num)\(|\nfunction |\nconst \w+ = |\Z)", _MDB2, _r2.S)
    return m.group(0) if m else ""


_reglas_v2 = [  # (bloque, debe contener, no debe contener, qué)
    ("rojos_cartera", "porGravedad(", "Semáforo en rojo", "«Clientes en crítico» de Mili = gravedad de la verdad (10), no las alarmas (40 de 68)"),
    ("rojos_visto_coti", "porGravedad(", "Semáforo en rojo", "«Críticos esperando tu Visto» = críticos de la verdad (no Finexen/Greconsult en atención)"),
    ("semaforo_cartera", "porGravedad(", "c.salud >= 60).length, a =", "la cartera de Coti por gravedad (crítico · atención · bien), no «94 % verde · 0 en rojo»"),
    ("cuentas_problema", "criticos_casa", None, "«Fuegos» y la cartera de la trafficker = cifras únicas de Captación (criticos_casa, carteras_publicidad)"),
    ("resultados_cartera", "pct(ok, act.length)", "pct(ok, total)", "el account mide solo clientes con campaña activa (sin campaña = no aplica)"),
    ("cartera_salud", "c.grav !== 'critico'", None, "el segundo indicador no cuenta un crítico como bien ni sale verde con críticos"),
    ("clientes_esperando", "bandejaComoPantalla(", None, "Mili «Lucía · 13» = la Bandeja de Lucía (regla de la pantalla Bandeja)"),
    ("trabajo_account", "controlPersona(", None, "«Trabajo» con revisionesDelAccount (como Producción e Incidencias)"),
    ("cumplimiento", "controlPersona(", None, "«Tu cumplimiento» con la misma vara que el mapa de Mili"),
    ("equipo_control", "controlPersona(", None, "mapa de control del día de Mili = «Tu cumplimiento» de cada persona"),
    ("equipo_control", "ultimoLaborable()", None, "«no imputaron» dice el último laborable de verdad (sábado 3 → viernes 2)"),
    ("para_tomas", "NUMERO.altas_en_plazo.hacer", "en_plazo_dia12", "«Para Tomás» Nº 1 = el número que manda de Mili (13 %, no 12 %)"),
    ("personas_alerta", "alertaPersonas(", None, "personas en alerta = la pestaña «En alerta» de Personas (10 sin plan de 11)"),
    ("alerta_sin_plan", "alertaPersonas(", None, "número de RRHH con la misma definición que Personas"),
    ("carga_personas", "cargaTxt(", None, "«por encima de su capacidad» solo los que pasan, con su cifra"),
    ("webs_verde", "responden", None, "número del puesto web = «Webs que responden 60 de 64» de su pantalla"),
    ("webs_lentas", "x.lenta", "lentas25", "«lentas» con la regla de webs.json (14), no 3 + 10"),
    ("seo_verde", "estado_mostrado", None, "SEO en gris «dato en duda» como su pantalla"),
    ("adm_meta", "No ves el importe por tu puesto", "Nada pendiente de Meta", "Sofía: un dato tapado nunca es «nada pendiente»"),
    ("adm_calendario", "hoyISO()", None, "calendario de Sofía con el «hoy» de verdad"),
    ("maps_posicion", "k.mapa", None, "posiciones en Maps = la misma cuenta que SEO, ficha y webs"),
]
_mal_v2b = []
for nombre, debe, no_debe, que in _reglas_v2:
    t = _trozo2(nombre)
    if not t or debe not in t or (no_debe and no_debe in t):
        _mal_v2b.append(f"{nombre}: {que}")
comprobar("mi-dia", "V2 · cada bloque de Mi día lee la definición única de su pantalla (rojo, cartera, contadores, webs, SEO, dinero)", _mal_v2b)
_lm2 = [x for x, ok in (
    ("la cola de tareas no usa alDia() de produccion_comun.js", "alDia(D.dato('produccion/produccion')" in _MDB2),
    ("la tarea vencida de «Lo mío» no lleva su fecha (saldría «Sin fecha»)", "plazo: FECHAS.dia(x.vence)" in _MDB2 and "c.plazo ?" in _MDJ2),
    ("«Lo mío» no filtra por pestaña de puesto", "alcanceLoMio(ctx, puesto)" in _MDJ2 and "piezasMeTocan(ctx, D, { puesto })" in _MDJ2),
    ("el consejo no se filtra por pestaña ni por dueño", "filtroConsejo(ctx, puesto)" in _MDJ2),
    ("posponer una alerta no aparta sus filas gemelas", "apartadasLoMio(" in _MDJ2 and "function apartadasLoMio" in _MDB2),
    ("«Lo mío» enseña el id interno del departamento", "quien: a.cliente ? null : a.departamento" not in _MDJ2),
    ("el copiloto sale a la vista o fuera del account (tercera lista de «qué hacer»)", "puesto === 'account' && ctx.veModulo('asistente-ia') ? bloqueCopiloto(" in _MDJ2 and "pCopiloto, panelCelebraciones(ctx)" in _MDJ2),
    ("sin el tope de piezas a la vista", "max_bloques_vista" in _MDJ2 and (_CFG2.get("comun", {}).get("max_bloques_vista", {}).get("escritorio", 9) + 3) <= 7
                                         and (_CFG2.get("comun", {}).get("max_bloques_vista", {}).get("movil", 9) + 3) <= 7),
    ("a 1.024 px el número que manda no va arriba", "matchMedia('(max-width: 1180px)')" in _MDJ2),
    ("sin cartera en su silla, los bloques dirían «todo bien»", "sinCarteraSilla(ctx, puesto)" in _MDJ2),
    ("los departamentos de cada pestaña no están en la configuración", bool(_CFG2.get("comun", {}).get("lo_mio_departamentos"))),
) if not ok]
comprobar("mi-dia", "V2 · «Lo mío», el consejo y la maqueta: por pestaña, sin «Sin fecha», sin copiloto, ≤ 7 piezas a la vista y número arriba a 1.024", _lm2)
# Con los datos: la factura del bloque de impagos abre el MISMO cobro que su alerta (Sofía: una fila, no dos)
_ALS = leer("alertas/p_sofia.json") or {}
_dif_fac = [a["id"] for a in _ALS.get("alertas", []) if a.get("tipo") == "adm_impago" and a.get("ir") and not str(a["ir"]).startswith("#/finanzas/cobros/")]
comprobar("mi-dia", "V2 · la alerta de una factura vencida y su fila de impagos abren el mismo cobro (finanzas/cobros/<factura>)",
          _dif_fac + ([] if "ruta: `finanzas/cobros/${encodeURIComponent(x.doc)}`" in _MDB2 else ["adm_impagos no abre finanzas/cobros/<factura>"]))
# Con los datos: las cifras de publicidad que pinta Mi día suman como Captación (Por trafficker + sin trafficker = Fuegos)
_CP2 = leer("captacion/captacion.json") or {}
if _CP2.get("carteras_publicidad") is not None:
    _con = {i for x in _CP2["carteras_publicidad"].values() for i in x.get("principal") or []}
    _suma = sum(int(x.get("criticos") or 0) for x in _CP2["carteras_publicidad"].values()) + sum(1 for i in _CP2.get("criticos_casa") or [] if i not in _con)
    comprobar("mi-dia", "V2 · «Por trafficker» (críticos de cada una + sin trafficker) = «Fuegos de toda la casa» (criticos_casa)",
              [] if _suma == len(_CP2.get("criticos_casa") or []) else [f"por trafficker {_suma} · fuegos {len(_CP2.get('criticos_casa') or [])}"])

# --- Finanzas v3 (3-oct): el beneficio es el MISMO en Finanzas (gráfico mes a mes y cifras), Mi día y el Panel de dirección
_CU = leer("finanzas/cuadre.json")
_FD3 = (leer("finanzas/direccion.json") or {}).get("direccion", [{}])[0]
if _CU and _FD3.get("pyg"):
    _pyg = {x["m"]: x for x in _FD3["pyg"]}
    _bm = {x["m"]: x for x in (_CU.get("beneficio") or {}).get("meses", [])}
    _dif = [f"{m}: cuadre {(_bm.get(m) or {}).get('bai')} · finanzas {x['bai']}" for m, x in _pyg.items() if abs(((_bm.get(m) or {}).get("bai") or 0) - x["bai"]) > 0.01]
    _dif += [f"{m} con gasto sin factura: cuadre {(_bm.get(m) or {}).get('real')} · finanzas {x.get('real')}" for m, x in _pyg.items() if abs(((_bm.get(m) or {}).get("real") or 0) - (x.get("real") or 0)) > 0.01]
    _a = (_CU["beneficio"].get("anios") or {}).get("2026") or {}
    _dif += [f"año {k}: cuadre {_a.get(k)} · finanzas {_FD3['anio'].get(k)}" for k in ("bai", "real") if _a.get(k) != _FD3["anio"].get(k)]
    _dif += [] if abs(sum(x["bai"] for x in _FD3["pyg"]) - _FD3["anio"]["bai"]) < 1 else ["la suma de los meses no da el año"]
    _dif += [] if (_FD3["numero"]["beneficio"], _FD3["numero"]["beneficio_real"]) == (_FD3["pyg"][-1]["bai"], _FD3["pyg"][-1]["real"]) else ["el número que manda no es el último mes"]
    for _f in ("mi_dia/p_tomas.json", "mi_dia/puestos/direccion/p_tomas.json", "mi_dia/puestos/finanzas_direccion/p_tomas.json"):
        _md = leer(_f) or {}
        _emb = ((((_md.get("fuentes") or {}).get("finanzas/direccion") or {}).get("direccion")) or [{}])[0]
        if _emb:
            _dif += [f"{_f}: {k} {(_emb.get(k2) or {}).get(k)} · finanzas {_FD3[k2].get(k)}" for k2, ks in (("anio", ("bai", "real")), ("numero", ("beneficio", "beneficio_real"))) for k in ks if (_emb.get(k2) or {}).get(k) != _FD3[k2].get(k)]
    _pdj = (AQUI / "modulos" / "panel_direccion.js").read_text()
    _dif += [] if ("dir.anio?.bai" in _pdj and "dir.numero?.beneficio" in _pdj) else ["el Panel de dirección no lee el beneficio de Finanzas"]
    _mdj = (AQUI / "modulos" / "mi_dia_bloques.js").read_text()
    _dif += [] if "finanzas/direccion" in _mdj else ["Mi día no lee el beneficio de Finanzas"]
    comprobar("finanzas", "v3 · beneficio igual en Finanzas (mes a mes y año), Mi día y Panel de dirección (93.492 / 76.392; agosto 3.859,87 / −3.428,03)", _dif)
    # ningún total de equipo sale de menos de 3 personas y nunca hay importes por persona en el cuadre
    def _claves(o):
        if isinstance(o, dict):
            for k, v in o.items():
                yield k; yield from _claves(v)
        elif isinstance(o, list):
            for v in o: yield from _claves(v)
    comprobar("finanzas", "v3 · el cuadre lleva solo totales del equipo (sin claves de sueldo ni ids de persona)",
              sorted({k for k in _claves(_CU) if any(t in k.lower() for t in ("salario", "sueldo", "persona", "nomina", "bonus"))}))
# --- Finanzas v3: impagos = las mismas facturas en la pestaña Impagos, en admin.impagos, en las alertas de administración y en «Lo mío» de Sofía
_IM = leer("finanzas/impagos.json")
_AD3 = ((leer("finanzas/finanzas.json") or {}).get("admin") or {})
if _IM and _AD3.get("impagos"):
    _d_imp = {x["doc"] for x in _IM["filas"] if x.get("tramo") != "Devuelto"}
    _d_adm = {x["doc"] for x in _AD3["impagos"]["filas"] if x.get("tramo") != "Sin vencer"}
    _d_ale = {str(a["id"]).split(":", 1)[1] for a in (leer("alertas/p_sofia.json") or {}).get("alertas", []) if a.get("tipo") == "adm_impago"}
    _sof = ((((leer("mi_dia/p_sofia.json") or {}).get("fuentes") or {}).get("finanzas/finanzas") or {}).get("admin") or {}).get("impagos") or {}
    _d_md = {x["doc"] for x in _sof.get("filas", []) if x.get("tramo") != "Sin vencer"}
    _dif = ([f"impagos≠admin: {sorted(_d_imp ^ _d_adm)}"] if _d_imp != _d_adm else []) + ([f"impagos≠alertas: {sorted(_d_imp ^ _d_ale)}"] if _d_imp != _d_ale else []) \
        + ([f"impagos≠Lo mío de Sofía: {sorted(_d_imp ^ _d_md)}"] if _sof and _d_imp != _d_md else [])
    _dif += [] if abs(sum(x["importe"] for x in _IM["filas"]) - _IM["resumen"]["vencido"]) < 1 else ["el total no es la suma de las filas"]
    _dif += [] if abs((_IM.get("evolucion") or [{}])[-1].get("vencido", 0) - _IM["resumen"]["vencido"]) < 1 else ["el último punto de la evolución no es el total de hoy"]
    _cli = {x["cliente_id"]: x for x in (leer("finanzas/impagos_clientes.json") or {}).get("clientes", [])}
    _dif += [c for c in {x["cliente_id"] for x in _IM["filas"] if x.get("cliente_id")} if c not in _cli]
    comprobar("finanzas", "v3 · impagos: pestaña Impagos = admin.impagos = alertas de administración = «Lo mío» de Sofía (y cada cliente con impago lo ve su equipo)", _dif)

# --- Tomás 3-oct · CLIENTES DE BAJA FUERA DE LAS PANTALLAS DE TRABAJO (fuentes_verdad/clientes_activos.py). Un solo filtro
#     «cliente activo»: (1) la lista existe y trae a Gestymas y FBC como bajas; (2) la verdad única no lleva bajas; (3) con la
#     app de verdad (servir.py en 127.0.0.1 con una COPIA de local.db, puertos 9960-9969): ningún fichero de una pantalla de
#     trabajo (todo lo de datos_de_modulo salvo finanzas e informes pasados), ni la sesión, ni el buscador lleva una fila de
#     un cliente de baja, para Tomás, Agus, Mili, una account, la jefa de CRM y la trafficker.
ADOPTADOS |= {"clientes activos"}
def _bajas_fuera():
    import os, shutil, socket, subprocess, tempfile, time, urllib.request
    sys.path.insert(0, str(AQUI))
    from fuentes_verdad import clientes_activos as ACT
    E_ = ACT.estado()
    nombres = {b["nombre"] for b in E_.get("bajas", [])}
    comprobar("clientes activos", "la lista única existe y trae a Gestymas y FBC Euroconsulting como bajas",
              [n for n in ("Gestoría Administrativa Gestymas", "Fbc Euroconsulting") if n not in nombres])
    comprobar("clientes activos", "Gestymas, FBC (y su subcuenta «28925 FBC EUROCONSULTING») y Volatt se reconocen como baja",
              [t for t in ("GESTYMAS", "28925 FBC EUROCONSULTING", "fbceuroconsulting.es", "Volatt") if not (ACT.nombra_baja(t, compacto=True) or ACT._exacto_baja(t))])
    comprobar("clientes activos", "ningún cliente activo se confunde con una baja (Asetra, Gómez de Barreda, Gestió Plural…)",
              [c["nombre"] for c in E_.get("activos", []) if ACT.nombra_baja(c["nombre"])])
    comprobar("clientes activos", "la verdad única no lleva clientes de baja",
              [cid for cid in list(ver) + list(comun) if ACT.es_baja_id(cid)])
    reglas = json.loads((AQUI / "reglas_permisos.json").read_text())
    rels = [k for k in reglas.get("datos_de_modulo", {}) if "*" not in k and not ACT.es_historico(k) and (DATA / f"{k}.json").exists()]
    ini, fin = (int(x) for x in os.environ.get("RO_PUERTOS_BAJAS", "9960-9969").split("-"))
    puerto = None
    for pu in range(ini, fin + 1):
        with socket.socket() as so:
            try:
                so.bind(("127.0.0.1", pu)); puerto = pu; break
            except OSError:
                continue
    if not puerto:
        avisos.append("clientes activos · sin puerto libre: no se prueba con el servidor"); return
    tmp = Path(tempfile.mkdtemp())
    shutil.copy(AQUI / "local.db", tmp / "c.db")
    (tmp / "recarga.json").write_text('{"ligera": [], "conexiones": []}')
    env = {**os.environ, "RO_DB": str(tmp / "c.db"), "RO_RECARGA_CONFIG": str(tmp / "recarga.json")}
    env.pop("RO_MODO", None)
    srv = subprocess.Popen([sys.executable, "servir.py", "--bind", "127.0.0.1", "--puerto", str(puerto)], cwd=AQUI, env=env,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    B = f"http://127.0.0.1:{puerto}"

    def pedir(ruta, yo):
        rq = urllib.request.Request(B + ruta, headers={"Cookie": f"ro_yo={yo}", "X-RO-App": "1"})
        try:
            with urllib.request.urlopen(rq, timeout=60) as r:
                return json.loads(r.read())
        except Exception:
            return None

    def filas_baja(o, ruta, out):
        if isinstance(o, list):
            for v in o:
                if ACT.fila_de_baja(v):
                    out.append(f"{ruta}: {str(v.get('cliente') or v.get('subcuenta') or v.get('nombre') or v.get('cliente_id') or v.get('dominio'))[:40]}")
                filas_baja(v, ruta, out)
        elif isinstance(o, dict):
            for k, v in o.items():
                if ACT.es_baja_id(k):
                    out.append(f"{ruta}: clave {k}")
                filas_baja(v, ruta, out)
    try:
        for _ in range(120):
            try:
                urllib.request.urlopen(B + "/index.html", timeout=1); break
            except Exception:
                time.sleep(0.3)
        difs, n = [], 0
        for yo in ("tomas", "agustina", "mili", "natalia", "yessica", "valeria"):
            ses = pedir("/api/sesion", yo) or {}
            filas_baja((ses.get("datos") or ses).get("clientes") or ses.get("clientes") or [], f"{yo} · sesión", difs)
            filas_baja(pedir("/api/buscar/indice", yo) or {}, f"{yo} · buscador", difs)
            for rel in rels + [f"mi_dia/p_{yo}", f"alertas/p_{yo}", f"prioridades/p_{yo}", f"consejos/p_{yo}"]:
                d = pedir(f"/api/modulo/{rel}", yo)
                if d is None:
                    continue
                n += 1
                filas_baja(d, f"{yo} · {rel}", difs)
                t = json.dumps(d, ensure_ascii=False).lower()
                for nombre in ("gestymas", "fbc euroconsulting", "fbceuroconsulting"):
                    if nombre in t:
                        difs.append(f"{yo} · {rel}: texto «{nombre}»")
        comprobar("clientes activos", f"ningún cliente de baja sale en pantallas de trabajo (sesión, buscador y {n} ficheros servidos a 6 personas)", sorted(set(difs)))
        tb = pedir("/api/modulo/verdad/bajas_tareas", "agustina")
        comprobar("clientes activos", "Agus (operaciones de sistemas) recibe la lista «Tareas de clientes de baja por cerrar»",
                  [] if tb and tb.get("tareas") else ["sin lista de tareas de baja para Agus"])
        tb2 = pedir("/api/modulo/verdad/bajas_tareas", "natalia")
        comprobar("clientes activos", "una account no recibe la lista de tareas de baja (solo operaciones y dirección)",
                  [] if not (tb2 and tb2.get("tareas")) else ["natalia la recibe"])
    finally:
        srv.terminate()
        try:
            srv.wait(timeout=10)
        except Exception:
            srv.kill()
        shutil.rmtree(tmp, ignore_errors=True)


if "--sin-servidor" not in sys.argv:
    _bajas_fuera()

if "--sin-navegador" not in sys.argv:
    _r15_menu()

print(f"\n{len(errores)} ERROR(ES) · {len(avisos)} aviso(s) para los dueños de módulo")
sys.exit(1 if errores else 0)

#!/usr/bin/env python3
"""fuentes_ia/probar_gasto.py · pruebas del control de gasto de la IA (ia_gasto.py) con un PROVEEDOR SIMULADO.

Lo llama probar_ia.py al final (mismo proceso, misma COPIA de la base), y también va solo:
  RO_DB=<copia> python3 servir.py --bind 127.0.0.1 --puerto 9245 &
  python3 fuentes_ia/probar_gasto.py --puerto 9245 --db <copia>

Comprueba: precio por tokens (entrada, caché, salida, lotes), modelo por tarea, coste real apuntado, aviso al 80 %, corte
al 100 % (la IA pasa sola a «modo reglas» y lo dice), nadie salta el tope (ni con 24 hilos a la vez), tope por persona y
por función, «ver como» no gasta, respaldo solo ante caída (nunca ante el corte de la Console), lotes a mitad de precio con
reserva, y la pantalla: solo Tomás la ve y cambia los topes (con rastro), nada de claves en las respuestas.
Ninguna llamada sale a Anthropic.
"""
import json
import os
import sqlite3
import sys
import threading
import time
import types
import urllib.error
import urllib.request
from pathlib import Path

APP = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(APP))


class Simulado:
    """Hace de Anthropic: devuelve un uso fijo y una salida válida; puede fallar a propósito por llave."""
    def __init__(self):
        self.uso = {"entrada": 2000, "cache_escrita": 0, "cache_leida": 3000, "salida": 500}
        self.fallos = {}          # clave → ErrorProveedor a lanzar
        self.llamadas = []        # (clave, modelo)
        self.espera = 0.0
        self.lotes = {}

    def crear(self, clave, modelo, sistema, contexto, esquema, effort, max_tokens, tarea=None):
        self.llamadas.append((clave, modelo))
        if self.espera:
            time.sleep(self.espera)
        if clave in self.fallos:
            raise self.fallos[clave]
        props = (esquema or {}).get("properties") or {}
        salida = {"consejos": []} if "consejos" in props else {k: ([] if v.get("type") == "array" else "x") for k, v in props.items()}
        return salida, modelo, dict(self.uso), None

    def lote_crear(self, clave, peticiones):
        lid = f"lote_sim_{len(self.lotes) + 1}"
        self.lotes[lid] = [c for c, _ in peticiones]
        return lid

    def lote_resultados(self, clave, lote_id):
        return {c: ({"ok": True}, "claude-sonnet-5", {"entrada": 4000, "salida": 1000}, None) for c in self.lotes[lote_id]}


class _H:
    def __init__(self):
        self.codigo = self.obj = None

    def responder(self, c, o):
        self.codigo, self.obj = c, o


def correr(ok, SV, IA, puerto=None, db=None):
    import ia_gasto as G
    sys.modules.setdefault("anthropic", types.ModuleType("anthropic"))   # ia.estado() solo mira que el paquete exista
    IA.clave = lambda: "LLAVE-PRUEBA-PRINCIPAL"
    G._CLAVE_R.update(t=time.time() + 10 ** 6, v="LLAVE-PRUEBA-RESPALDO")
    sim = Simulado()
    G.PROVEEDOR = sim
    tomas, lucia, mili = SV.E.persona("tomas"), SV.E.persona("lucia"), SV.E.persona("mili")

    def topes(**kw):
        v = json.loads(json.dumps(G.TOPES_DEFECTO))
        v.update(kw)
        with SV.conectar() as con:
            con.execute("INSERT INTO ia_topes (creada, quien, valores, motivo) VALUES (?,?,?,?)",
                        (G.ahora().strftime("%Y-%m-%d %H:%M:%S"), "prueba", json.dumps(v), "prueba probar_gasto"))

    def filas():
        with SV.conectar() as con:
            return con.execute("SELECT COUNT(*), COALESCE(SUM(coste_eur),0) FROM ia_gasto").fetchone()

    def llamar(real, persona, tarea_sis=None):
        G.fijar_peticion(real, persona, "mi-dia")
        try:
            return IA.llamar(tarea_sis or IA.SISTEMA_CONSEJO, {"x": 1}, IA.ESQ_CONSEJO, effort="low")
        finally:
            G.soltar_peticion()

    # 1 · precios (fuente: platform.claude.com/docs/en/about-claude/pricing, 3-oct-2026)
    usd, _ = G.coste("claude-opus-5", {"entrada": 1_000_000, "salida": 1_000_000})
    ok(abs(usd - 30.0) < 1e-9, "Gasto · Opus 5: 1 M de entrada + 1 M de salida = 30 $ (5 + 25)")
    usd, _ = G.coste("claude-haiku-4-5", {"entrada": 1_000_000, "cache_leida": 1_000_000, "cache_escrita": 1_000_000, "salida": 1_000_000})
    ok(abs(usd - (1 + 0.10 + 1.25 + 5)) < 1e-9, "Gasto · Haiku 4.5: caché leída a 0,10 $ y escrita a 1,25 $ por millón")
    ok(abs(G.coste("claude-sonnet-5", {"salida": 1_000_000}, lote=True)[0] - 5.0) < 1e-9, "Gasto · en lote, la mitad (Sonnet 5: 10 $ → 5 $ de salida)")
    ok(G.coste("modelo-raro", {"salida": 1_000_000})[0] == 50.0, "Gasto · un modelo desconocido se cobra como el más caro")
    ok(abs(G.coste("claude-opus-5", {"cache_escrita_1h": 1_000_000})[0] - 10.0) < 1e-9, "Gasto · caché de 1 hora (borradores) a 2× la entrada: 10 $ por millón en Opus 5")
    pb = G.ProveedorAnthropic.peticion("claude-opus-5", "s", {}, {}, "medium", 8000, "borrador")
    ph = G.ProveedorAnthropic.peticion("claude-haiku-4-5", "s", {}, {}, "low", 2000, "consejo")
    ok(pb["system"][0]["cache_control"].get("ttl") == "1h" and pb["thinking"] == {"type": "adaptive"} and "thinking" not in ph and "effort" not in ph["output_config"],
       "Gasto · petición: caché de 1 h en borradores; Haiku sin pensamiento ni esfuerzo (no los admite)")
    ok(G.modelo_de("consejo") == "claude-haiku-4-5" and G.modelo_de("clasificar") == "claude-haiku-4-5" and G.modelo_de("borrador") == "claude-opus-5",
       "Gasto · modelo por tarea: Haiku para consejos y clasificar, Opus 5 para borradores")

    # 2 · una llamada apunta su coste real
    topes(mes_eur=1.0, dia_eur=1.0, persona_dia_eur=50.0, funcion_mes_eur={"consejo": 1.0}, aviso_pct=80)
    n0, s0 = filas()
    with SV.conectar() as con:
        ya_mes = con.execute("SELECT COALESCE(SUM(coste_eur),0) FROM ia_gasto WHERE mes=?", (G._mes(),)).fetchone()[0]
    if ya_mes:   # la copia ya traía gasto de otra pasada: el tope se pone encima de lo gastado
        topes(mes_eur=round(ya_mes + 1.0, 2), dia_eur=round(ya_mes + 1.0, 2), persona_dia_eur=50.0,
              funcion_mes_eur={"consejo": round(ya_mes + 1.0, 2)}, aviso_pct=80)
    salida, modelo = llamar(tomas, tomas)
    n1, s1 = filas()
    esperado = G.coste("claude-haiku-4-5", sim.uso)[1]
    with SV.conectar() as con:
        ult = con.execute("SELECT tarea, modelo, llave, entrada, cache_leida, salida, coste_eur, quien FROM ia_gasto ORDER BY id DESC LIMIT 1").fetchone()
    ok(n1 == n0 + 1 and ult[0] == "consejo" and ult[1] == "claude-haiku-4-5" and ult[2] == "principal" and abs(ult[6] - esperado) < 1e-9 and ult[7] == "tomas",
       f"Gasto · cada llamada deja su fila con tokens y coste real ({ult[6]:.6f} € = 2.000 entrada + 3.000 caché + 500 salida en Haiku)")

    G.fijar_peticion(tomas, tomas, "bandeja")
    try:
        IA.llamar(IA.SISTEMA_CONSEJO, {"x": 1}, IA.ESQ_CONSEJO, effort="low")
        ok(False, "Gasto · consejos con IA solo en Mi día")
    except G.SinGasto:
        ok(True, "Gasto · consejos con IA solo en Mi día: en otra pantalla (Bandeja) no sale la llamada (reglas)")
    finally:
        G.soltar_peticion()

    # 3 · «ver como» no gasta
    n_antes = filas()[0]
    try:
        llamar(tomas, lucia)
        ok(False, "Gasto · «ver como» no gasta")
    except G.SinGasto as e:
        ok(filas()[0] == n_antes and "ver como" in str(e), "Gasto · «ver como» no gasta: no sale ninguna llamada ni se apunta nada")
    cp_l = SV.P.contexto(lucia, SV.E.crudo)
    llam = len(sim.llamadas)
    IA.consejo(tomas, lucia, cp_l, "mi-dia", con_ia=True, nuevo=True)
    ok(len(sim.llamadas) == llam, "Gasto · consejo con IA en «ver como»: cero llamadas al proveedor")

    # 4 · nadie salta el tope (24 hilos a la vez, proveedor lento) y corte al 100 %
    sim.espera = 0.05
    errores = []
    ya = G.gastado()
    topes(mes_eur=round(ya["mes"] + 0.03, 4), dia_eur=round(ya["mes"] + 0.03, 4), persona_dia_eur=50.0,
          funcion_mes_eur={"consejo": round(ya["mes"] + 1, 2)}, aviso_pct=80)    # caben ~6 llamadas; van 24 a la vez

    def golpe():
        try:
            llamar(tomas, tomas)
        except RuntimeError as e:
            errores.append(str(e))
    hilos = [threading.Thread(target=golpe) for _ in range(24)]
    [x.start() for x in hilos]
    [x.join() for x in hilos]
    sim.espera = 0.0
    for _ in range(400):           # hasta el corte
        try:
            llamar(tomas, tomas)
        except RuntimeError:
            break
    t = G.topes()
    g = G.gastado()
    ok(g["mes"] <= t["mes_eur"] + 1e-9 and g["dia"] <= t["dia_eur"] + 1e-9 and errores,
       f"Gasto · nadie salta el tope, ni con 24 a la vez: {g['mes']:.4f} € gastados de {t['mes_eur']} € (rechazadas {len(errores)} en paralelo)")
    try:
        llamar(tomas, tomas)
        cortado = False
    except RuntimeError as e:
        cortado = "tope" in str(e).lower()
    ok(cortado, "Gasto · al llegar al tope, la siguiente llamada no sale (mensaje legible)")
    # sin rellenar nada: lo que queda no cubre ni una petición → corte del periodo (el 100 % práctico)
    e = IA.estado()
    ok(not e["conectada"] and e.get("modo") == "reglas" and "ope" in (e.get("motivo") or ""),
       f"Gasto · al 100 % la IA pasa sola a modo reglas y lo dice: «{(e.get('motivo') or '')[:70]}…»")
    el = IA.estado_para(lucia)
    ok(not el["conectada"] and "sin coste" in el["motivo"] and "€" not in el["motivo"], "Gasto · al resto se le dice en llano (sin cifras): «" + el["motivo"][:60] + "…»")
    r = IA.consejo(lucia, lucia, cp_l, "mi-dia", con_ia=True, nuevo=True)
    ok(r["origen"] == "reglas" and r["consejos"] and not r["ia"]["conectada"], "Gasto · en modo reglas los consejos salen igual (por reglas) y sin llamada")
    # 5 · tope por persona y por función
    topes(mes_eur=900.0, dia_eur=150.0, persona_dia_eur=0.001, funcion_mes_eur={"consejo": 900.0})
    G.fijar_peticion(lucia, lucia, "mi-dia")
    try:
        IA.llamar(IA.SISTEMA_CONSEJO, {"x": 1}, IA.ESQ_CONSEJO, effort="low")
        ok(False, "Gasto · tope por persona")
    except G.SinGasto as e:
        ok("tu tope" in str(e), "Gasto · tope por persona y día: «" + str(e)[:60] + "…»")
    finally:
        G.soltar_peticion()
    topes(mes_eur=900.0, dia_eur=150.0, persona_dia_eur=50.0, funcion_mes_eur={"consejo": 0.0})
    try:
        llamar(tomas, tomas)
        ok(False, "Gasto · tope por función")
    except G.SinGasto as e:
        ok("Consejos por pantalla" in str(e), "Gasto · tope por función (consejos a 0 €): no sale")

    # 6 · respaldo: solo ante caída, nunca ante el corte de la Console
    topes(mes_eur=900.0, dia_eur=150.0, persona_dia_eur=50.0)
    sim.fallos = {"LLAVE-PRUEBA-PRINCIPAL": G.ErrorProveedor("caida", "Anthropic está caído o sobrecargado (error 529).")}
    sim.llamadas.clear()
    llamar(tomas, tomas)
    with SV.conectar() as con:
        ult = con.execute("SELECT llave, ok FROM ia_gasto ORDER BY id DESC LIMIT 2").fetchall()
    ok([c for c, _ in sim.llamadas] == ["LLAVE-PRUEBA-PRINCIPAL", "LLAVE-PRUEBA-RESPALDO"] and ult[0][0] == "respaldo" and ult[0][1] == 1,
       "Gasto · caída de la principal → una vez por la llave de respaldo, apuntado como «respaldo»")
    sim.fallos = {"LLAVE-PRUEBA-PRINCIPAL": G.ErrorProveedor("tope_console", "La Console de Anthropic ha cortado: tope de gasto o saldo agotado.")}
    sim.llamadas.clear()
    try:
        llamar(tomas, tomas)
    except RuntimeError:
        pass
    ok([c for c, _ in sim.llamadas] == ["LLAVE-PRUEBA-PRINCIPAL"], "Gasto · corte de la Console: la llave de respaldo NO se usa")
    ok(G.modo()["modo"] == "reglas" and "Console" in G.modo()["motivo"], "Gasto · corte de la Console → modo reglas con el motivo")
    sim.fallos = {}
    h = _H()
    G.post(h, "/api/ia/gasto/reabrir", tomas, tomas, {"motivo": "prueba"})
    ok(h.codigo == 200 and G.modo()["modo"] == "ia", "Gasto · «Reabrir» (Tomás, tras subir el límite en la Console) vuelve a la IA")
    h = _H()
    G.post(h, "/api/ia/gasto/reabrir", mili, mili, {"motivo": "prueba"})
    ok(h.codigo == 403, "Gasto · Mili no puede reabrir (403)")

    # 6b · aviso al 80 %: una llamada que deja el mes por encima del 80 % del tope
    ya = G.gastado()
    topes(mes_eur=round(ya["mes"] + 0.0105, 4), dia_eur=round(ya["mes"] + 0.0105, 4), persona_dia_eur=50.0, aviso_pct=80)
    llamar(tomas, tomas)
    with SV.conectar() as con:
        avisos = [x[0] for x in con.execute("SELECT clave FROM canal_mensajes WHERE canal_id='avisos-direccion' AND clave LIKE 'ia_gasto:%'").fetchall()]
    ok(any(":aviso:" in a for a in avisos) and any(":corte:" in a for a in avisos),
       f"Gasto · aviso a Tomás en #avisos-dirección al 80 % y al 100 % ({len(avisos)} avisos)")
    with SV.conectar() as con:
        rastro = con.execute("SELECT COUNT(*) FROM registro WHERE accion='ia_aviso_gasto'").fetchone()[0]
    ok(rastro >= 2, "Gasto · cada aviso deja su fila en el rastro (ia_aviso_gasto)")

    # 7 · lotes nocturnos: reserva del peor caso y coste a mitad de precio
    topes(mes_eur=900.0, dia_eur=150.0, persona_dia_eur=50.0, funcion_mes_eur={"copiloto": 900.0})
    reservado0 = G._reservado()
    lid = G.lote_enviar("copiloto", [(f"c{i}", IA.SISTEMA_COPILOTO, {"i": i}, IA.ESQ_COPILOTO, "high") for i in range(3)])
    ok(G._reservado() > reservado0, f"Gasto · un lote enviado deja su peor caso reservado ({G._reservado() - reservado0:.4f} €) hasta recogerlo")
    out = G.lote_recoger(lid)
    with SV.conectar() as con:
        fl = con.execute("SELECT lote, coste_usd FROM ia_gasto WHERE peticion=?", (lid,)).fetchall()
    ok(len(out) == 3 and all(l == 1 for l, _ in fl) and abs(fl[0][1] - (4000 * 2 + 1000 * 10) / 1e6 * 0.5) < 1e-9 and G._reservado() == reservado0,
       "Gasto · lote recogido: 3 resultados a mitad de precio y la reserva liberada")

    # 8 · topes: validación y rastro (en proceso)
    h = _H()
    G.post(h, "/api/ia/gasto/topes", tomas, tomas, {"valores": {"dia_eur": 500, "mes_eur": 100}, "motivo": "prueba"})
    ok(h.codigo == 400, "Gasto · un tope del día mayor que el del mes se rechaza (400)")
    h = _H()
    G.post(h, "/api/ia/gasto/topes", tomas, lucia, {"valores": {"mes_eur": 200}, "motivo": "prueba"})
    ok(h.codigo == 403, "Gasto · en «ver como» no se cambian topes (403)")

    # 9 · por HTTP contra servir.py (si se pasa el puerto): solo Tomás
    if puerto:
        base = f"http://127.0.0.1:{puerto}"

        def pedir(ruta, yo, cuerpo=None, como=None, app=True):
            hd = {"X-RO-Yo": yo, "Content-Type": "application/json"}
            if app:
                hd["X-RO-App"] = "1"
            if como:
                hd["X-RO-Como"] = como
            req = urllib.request.Request(base + ruta, data=json.dumps(cuerpo).encode() if cuerpo is not None else None, headers=hd,
                                         method="POST" if cuerpo is not None else "GET")
            try:
                r = urllib.request.urlopen(req, timeout=30)
                return r.status, json.loads(r.read() or b"{}")
            except urllib.error.HTTPError as e:
                return e.code, json.loads(e.read() or b"{}")
        s, d = pedir("/api/ia/gasto", "tomas")
        ok(s == 200 and {"gasto", "topes", "por_funcion", "por_persona", "ultimas", "llaves", "precios"} <= set(d),
           f"Gasto · Tomás ve la pantalla (mes {d.get('gasto', {}).get('mes')} €, previsión {d.get('gasto', {}).get('prevision_mes')} €)")
        txt = json.dumps(d)
        ok("LLAVE-PRUEBA" not in txt and ("sk" + "-ant") not in txt, "Gasto · ninguna clave en la respuesta (solo «hay llave» sí o no)")
        for yo, como in (("mili", None), ("lucia", None), ("sofia", None), ("tomas", "lucia")):
            s, _ = pedir("/api/ia/gasto", yo, como=como)
            ok(s == 403, f"Gasto · {yo}{' viendo como ' + como if como else ''}: 403")
        s, _ = pedir("/api/ia/gasto/topes", "mili", {"valores": {"mes_eur": 1000}})
        ok(s == 403, "Gasto · Mili no cambia los topes (403)")
        s, _ = pedir("/api/ia/gasto/topes", "tomas", {"valores": {"mes_eur": 1000}}, app=False)
        ok(s == 403, "Gasto · POST de topes sin la cabecera de la app: 403")
        s, d = pedir("/api/ia/gasto/topes", "tomas", {"valores": {"mes_eur": 160, "dia_eur": 10}, "motivo": "prueba de topes"})
        ok(s == 200 and d.get("topes", {}).get("mes_eur") == 160, "Gasto · Tomás cambia el tope del mes (150 → 160)")
        if db:
            con = sqlite3.connect(db)
            f = con.execute("SELECT datos FROM registro WHERE accion='ia_topes_cambiados' ORDER BY id DESC LIMIT 1").fetchone()
            ok(f and "160" in f[0], "Gasto · el cambio de topes queda en el rastro con el antes y el después")
        s, _ = pedir("/api/rastro", "tomas", {"accion": "ia_topes_cambiados", "modulo": "ia"})
        ok(s in (400, 403), f"Gasto · el navegador no puede fingir «ia_topes_cambiados» ({s})")

    # deja la copia como estaba: los topes de por defecto
    topes()


if __name__ == "__main__":
    PUERTO = int(sys.argv[sys.argv.index("--puerto") + 1]) if "--puerto" in sys.argv else None
    DB = sys.argv[sys.argv.index("--db") + 1] if "--db" in sys.argv else None
    if not DB:
        sys.exit("Pásale --db <copia de local.db>: estas pruebas escriben gasto simulado.")
    os.environ["RO_DB"] = DB
    os.environ.setdefault("RO_AVISOS_SIN_BUCLE", "1")
    import servir as SV
    SV.E.cargar()
    import ia as IA
    if IA.S is None:
        IA.enganchar(SV.Manejador, SV)
    BIEN, MAL = [], []

    def ok(c, t):
        (BIEN if c else MAL).append(t)
        print(("✓ " if c else "✗ ") + t)
    correr(ok, SV, IA, PUERTO, DB)
    print(f"\n{len(BIEN)} bien · {len(MAL)} mal")
    sys.exit(1 if MAL else 0)

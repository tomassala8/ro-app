#!/usr/bin/env python3
"""despliegue/verificar_envios.py · el verificador de envíos (3-oct-2026, envíos verificados).

Encargo de Tomás: «cualquier correo que se envíe, asegurarnos de que se está enviando bien; también desde la parte de
atrás, para asegurarnos de que el sistema nunca está fallando». La lógica está en envios.py; esto es lo que corre:

  · como PASO DE LA TUBERÍA (paso «verificar_envios» de pasos.json, tras la salud de conexiones), en cada vuelta:
      1. sincroniza: cada acción de la cola que manda algo fuera tiene su envío (clave única: nunca dos por acción);
      2. con un canal ACTIVO (interruptor + RO_ENVIOS_REALES=si): manda los pendientes y relee en la herramienta (solo
         lectura) que están en el hilo con el texto y el destinatario correctos; detecta rebotes y errores; reintenta
         UNA vez lo seguro (red, tiempo, caída) mirando antes si ya llegó; si falla, avisa a quien lo mandó y a Agus;
      3. el CANARIO, si Tomás lo ha encendido: un correo de prueba al día a un buzón interno, verificado de punta a punta.
    Con todo apagado (HOY) solo sincroniza y cuenta: no sale nada y no se llama a ninguna herramienta.
  · AL MOMENTO tras cada envío real: servir.py lo hace solo (envios._al_momento); a mano: --al-momento <id>.
  · PRUEBA DE EXTREMO A EXTREMO con un proveedor SIMULADO (nunca uno real), sobre una COPIA de la base en una carpeta
    temporal: enviado → confirmado, rebote, error de red con reintento sin duplicar, corte a medias sin duplicar, token
    caducado → fallido + aviso, «dice que salió pero no aparece», destinatario distinto, reintento en simulación y la
    guarda de escritura con el canal apagado.  --prueba-e2e  (la usa pruebas_noche.py --solo-solidez)

Uso:
  python3 despliegue/verificar_envios.py                 vuelta normal (sobre RO_DB o local.db)
  python3 despliegue/verificar_envios.py --sin-red       solo sincroniza y cuenta (la vuelta «cruda» de la tubería)
  python3 despliegue/verificar_envios.py --al-momento 12 ejecuta/verifica ese envío ahora (solo con su canal activo)
  python3 despliegue/verificar_envios.py --canario       el canario de hoy (solo si Tomás lo ha encendido)
  python3 despliegue/verificar_envios.py --prueba-e2e [--json]
Código de salida: 0 si ha podido hacer la vuelta (un envío fallido NO tumba la tubería: avisa); 1 si falla la prueba e2e.
"""
import json
import os
import shutil
import sqlite3
import sys
import tempfile
from datetime import timedelta
from pathlib import Path

AQUI = Path(__file__).resolve().parent
APP = AQUI.parent
sys.path.insert(0, str(APP))
import envios as EN  # noqa: E402

ARGS = sys.argv[1:]
ESTADO = Path(os.environ.get("RO_ESTADO_DIR") or AQUI / "estado")


def vuelta_normal():
    sin_red = "--sin-red" in ARGS
    it = EN.interruptor()
    with EN.conectar() as con:
        EN.preparar(con)
        if sin_red or not it["reales"]:
            nuevos = EN.sincronizar(con)
            hechos = {"nuevos": len(nuevos), "ejecutados": 0, "verificados": 0, "cambios": []}
        else:
            hechos = EN.vuelta(con)
        can = EN.canario(con) if not sin_red else {"corre": False, "motivo": "vuelta sin red"}
        res = EN.resumen(con)
        con.commit()
    out = {"modo": it["texto"], "reales": it["reales"], "canales": it["canales"], "vuelta": hechos, "canario": can, "resumen": res}
    ESTADO.mkdir(parents=True, exist_ok=True)
    (ESTADO / "envios_ultima.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    pe = res["por_estado"]
    print(f"Envíos · {it['texto']} · {hechos['nuevos']} nuevos · {res['total']} en total · "
          + " · ".join(f"{k} {v}" for k, v in pe.items() if v) + f" · canario: {can.get('motivo') or can.get('estado')}")
    for c in hechos["cambios"]:
        print(f"  envío {c['id']}: {c['de']} → {c['a']}")
    return 0


def al_momento(eid):
    with EN.conectar() as con:
        EN.preparar(con)
        e = EN.fila_envio(con, eid)
        if not e:
            sys.exit(f"No existe el envío {eid}.")
        if not EN.canal_real(e["canal"]):
            print(f"Envío {eid}: canal {EN.CANALES[e['canal']]} apagado (simulación). No se llama a nada.")
            return 0
        prov = EN.proveedor_de(e["canal"])
        est = EN.estado_actual(con, eid)["estado"]
        nuevo = EN.ejecutar(con, eid, prov) if est == "pendiente" else EN.verificar(con, eid, prov)
        con.commit()
    print(f"Envío {eid}: {est} → {nuevo}")
    return 0


# ============================================================================ prueba de extremo a extremo (simulada)
def prueba_e2e():
    """Todo sobre una COPIA de la base en una carpeta temporal y con ProveedorSimulado: nada sale, nada real cambia."""
    tmp = Path(tempfile.mkdtemp(prefix="ro_envios_e2e_"))
    os.chmod(tmp, 0o700)
    casos = []

    def caso(nombre, ok, detalle=None):
        casos.append({"caso": nombre, "ok": bool(ok), "detalle": None if ok else str(detalle)[:300]})
        if "--json" not in ARGS:
            print(f"  {'✔' if ok else '✘'} {nombre}" + ("" if ok else f" · {str(detalle)[:300]}"))

    origen = EN.ruta_db()
    db = tmp / "e2e.db"
    try:
        if origen.exists():                       # copia coherente aunque el servidor esté escribiendo
            with sqlite3.connect(str(origen)) as src, sqlite3.connect(str(db)) as dst:
                src.backup(dst)
        con = EN.conectar(db)
        EN.preparar(con)
        if not con.execute("SELECT 1 FROM sqlite_master WHERE name='canal_mensajes'").fetchone():
            con.executescript("CREATE TABLE canal_mensajes (id INTEGER PRIMARY KEY AUTOINCREMENT, canal_id TEXT NOT NULL, tipo TEXT NOT NULL, quien TEXT, "
                              "texto TEXT NOT NULL, hilo_de INTEGER, menciones TEXT, clave TEXT UNIQUE, alerta_id TEXT, cliente_id TEXT, dueno_id TEXT, "
                              "vence TEXT, ver TEXT, datos TEXT, creado TEXT NOT NULL DEFAULT (datetime('now')));")
        n = [0]

        def nuevo(guion=None, modo="prueba", quien="lucia"):
            n[0] += 1
            clave = f"e2e-{n[0]}-{os.getpid()}"
            eid, _ = EN.crear_envio(con, clave=clave, quien=quien, canal="desk", tipo="responder", objeto="RO-7480", cliente_id="gac",
                                    modulo="bandeja", asunto="RE: prueba", texto=f"Hola, esto es la prueba {n[0]}.", modo=modo)
            return eid, clave

        def pasos(eid):
            return [(p["estado"], p["evento"]) for p in EN.pasos_de(con, eid)]

        def avisos(eid):
            return [dict(r) for r in con.execute("SELECT canal_id, menciones, texto FROM canal_mensajes WHERE clave LIKE ?", (f"envio:{eid}:%",))]

        # 1 · enviado → confirmado
        e1, k1 = nuevo()
        prov = EN.ProveedorSimulado()
        est = EN.ejecutar(con, e1, prov)
        ps = EN.pasos_de(con, e1)
        caso("E2E 1 · pendiente → enviado → confirmado, con la hora de cada paso",
             est == "confirmado" and [p["estado"] for p in ps] == ["pendiente", "enviado", "confirmado"] and all(p["hora"] for p in ps), pasos(e1))
        caso("E2E 1 · un solo mensaje en el buzón y ningún aviso", len([x for x in prov.buzon if x["clave"] == k1]) == 1 and not avisos(e1), (prov.buzon, avisos(e1)))
        caso("E2E 1 · la idempotencia de la clave: crear otra vez el mismo envío devuelve el mismo id",
             EN.crear_envio(con, clave=k1, quien="lucia", canal="desk", tipo="responder", objeto="RO-7480")[0] == e1)

        # 2 · rebote → rebotado + aviso a quien lo mandó y a Agus
        e2, k2 = nuevo()
        prov = EN.ProveedorSimulado({k2: {"rebote": True}})
        est = EN.ejecutar(con, e2, prov)
        av = avisos(e2)
        canales = {a["canal_id"] for a in av}
        menc = set(json.loads(av[0]["menciones"])) if av else set()
        caso("E2E 2 · rebote → «rebotado»", est == "rebotado", pasos(e2))
        caso("E2E 2 · aviso en #avisos-dirección (y copia en #avisos-altas y en #avisos-accounts) con Lucía y Agus mencionadas",
             {"avisos-direccion", "avisos-altas", "avisos-accounts"} <= canales and {"lucia", "agustina"} <= menc, av)
        caso("E2E 2 · el aviso va en llano y sin dirección de correo ni texto del mensaje",
             av and all("rebotado" in a["texto"] and "@" not in a["texto"] and "prueba 2" not in a["texto"] for a in av), av)
        n_av = len(av)
        EN.avisar(con, e2, "rebote")
        caso("E2E 2 · el aviso no se repite (un aviso por envío y motivo)", len(avisos(e2)) == n_av, avisos(e2))

        # 3 · error de red (no llegó) → se mira si llegó → reintento UNA vez → confirmado, sin duplicar
        e3, k3 = nuevo()
        prov = EN.ProveedorSimulado({k3: {"enviar": ["red", "ok"]}})
        est = EN.ejecutar(con, e3, prov)
        envios3 = [c for c in prov.llamadas if c == ("enviar", k3)]
        caso("E2E 3 · error de red → reintento → confirmado", est == "confirmado" and ("pendiente", "error_envio") in pasos(e3), pasos(e3))
        caso("E2E 3 · exactamente 2 intentos y UN mensaje en el buzón (sin duplicar)", len(envios3) == 2 and len([x for x in prov.buzon if x["clave"] == k3]) == 1,
             (prov.llamadas, prov.buzon))

        # 3b · corte DESPUÉS de llegar: al reintentar, ya está en el hilo → no se vuelve a mandar
        e3b, k3b = nuevo()
        prov = EN.ProveedorSimulado({k3b: {"enviar": ["red_pero_entregado"]}})
        est = EN.ejecutar(con, e3b, prov)
        caso("E2E 3b · corte a medias: lo encuentra en el hilo («ya_estaba») y NO lo manda otra vez",
             est == "confirmado" and ("enviado", "ya_estaba") in pasos(e3b) and [c for c in prov.llamadas if c[0] == "enviar"] == [("enviar", k3b)]
             and len(prov.buzon) == 1, (pasos(e3b), prov.llamadas))

        # 3c · red dos veces → fallido (seguro reintentar después), sin duplicar, con aviso
        e3c, k3c = nuevo()
        prov = EN.ProveedorSimulado({k3c: {"enviar": ["red", "red"]}})
        est = EN.ejecutar(con, e3c, prov)
        ult = EN.estado_actual(con, e3c)
        ult_fallo = EN.ultimo_hecho(EN.pasos_de(con, e3c))
        caso("E2E 3c · red dos veces → «fallido» tras UN reintento, sin nada en el buzón, con aviso",
             est == "fallido" and len([c for c in prov.llamadas if c[0] == "enviar"]) == 2 and not prov.buzon and avisos(e3c)
             and json.loads(ult_fallo["detalle"]).get("seguro_reintentar") is True, (pasos(e3c), ult))

        # 4 · token caducado → fallido + aviso, SIN reintento
        e4, k4 = nuevo()
        prov = EN.ProveedorSimulado({k4: {"enviar": ["token"]}})
        est = EN.ejecutar(con, e4, prov)
        av4 = avisos(e4)
        caso("E2E 4 · token caducado → «fallido» al primer intento (no se reintenta) y aviso con la llave en llano",
             est == "fallido" and len([c for c in prov.llamadas if c[0] == "enviar"]) == 1 and av4 and "llave" in av4[0]["texto"], (pasos(e4), av4))

        # 5 · «dice que salió pero no aparece» → enviado; a los 10 min → fallido
        e5, k5 = nuevo()
        prov = EN.ProveedorSimulado({k5: {"perdido": True}})
        est = EN.ejecutar(con, e5, prov)
        est2 = EN.verificar(con, e5, prov, ahora=EN.ahora_utc() + timedelta(minutes=EN.GRACIA_MIN + 1))
        caso("E2E 5 · aceptado pero no está en el hilo: «enviado» y, pasada la gracia, «fallido · no aparece» con aviso",
             est == "enviado" and est2 == "fallido" and ("fallido", "no_aparece") in pasos(e5) and avisos(e5), pasos(e5))

        # 6 · en el hilo pero con otro destinatario → fallido (no se reintenta)
        e6, k6 = nuevo()
        prov = EN.ProveedorSimulado({k6: {"otro_destino": True}})
        est = EN.ejecutar(con, e6, prov)
        caso("E2E 6 · en el hilo con OTRO destinatario → «fallido · distinto», no seguro de reintentar",
             est == "fallido" and ("fallido", "distinto") in pasos(e6), pasos(e6))

        # 7 · envío simulado: «Reintentar» solo deja el paso; el proveedor NO se llama
        e7, k7 = nuevo(modo="simulado")
        prov = EN.ProveedorSimulado()
        r = EN.reintentar(con, e7, "agustina", prov)
        caso("E2E 7 · en simulación «Reintentar» deja «reintento_simulado» y no llama a ningún proveedor",
             r.get("simulado") and ("simulado", "reintento_simulado") in pasos(e7) and not prov.llamadas, (r, pasos(e7), prov.llamadas))

        # 8 · un proveedor de verdad con el canal apagado no escribe
        class Real(EN.ProveedorSimulado):
            real = True
        e8, k8 = nuevo(modo="real")
        prov = Real()
        est = EN.ejecutar(con, e8, prov)
        caso("E2E 8 · proveedor real con el canal apagado → «fallido · apagado» sin llamar a enviar",
             est == "fallido" and not [c for c in prov.llamadas if c[0] == "enviar"], (pasos(e8), prov.llamadas))
        try:
            EN.ProveedorDesk().pide("POST", "/tickets/0/sendReply", {})
            guarda = False
        except EN.ErrorEnvio as x:
            guarda = x.tipo == "permiso"
        caso("E2E 8 · Desk: cualquier escritura con el canal apagado se corta ANTES de pedir la llave (sin red)", guarda)

        # 9 · rebote tardío tras «confirmado» (se sigue mirando 48 h)
        e9, k9 = nuevo()
        prov = EN.ProveedorSimulado()
        EN.ejecutar(con, e9, prov)
        prov.buzon[-1]["rebote"] = True
        est = EN.verificar(con, e9, prov)
        caso("E2E 9 · un rebote que llega después de «confirmado» lo pasa a «rebotado»", est == "rebotado", pasos(e9))

        # 10 · tasas: solo cuentan envíos reales terminados
        filas = [{"modo": "real", "creado": EN.txt_hora(EN.ahora_utc()), "estado": s} for s in ("confirmado", "confirmado", "fallido", "enviado")] + \
                [{"modo": "simulado", "creado": EN.txt_hora(EN.ahora_utc()), "estado": "simulado"}]
        t = EN.tasa(filas, 7)
        caso("E2E 10 · tasa de confirmados = confirmados / terminados (los simulados y en curso aparte)",
             t["pct"] == 66.7 and t["terminados"] == 3 and t["en_curso"] == 1 and t["simulados"] == 1, t)

        # 11 · los pasos no se cambian ni se borran
        try:
            con.execute("UPDATE envio_pasos SET estado='confirmado' WHERE envio_id=?", (e4,))
            inmutable = False
        except sqlite3.DatabaseError:
            inmutable = True
        try:
            con.execute("DELETE FROM envios WHERE id=?", (e4,))
            inmutable = False
        except sqlite3.DatabaseError:
            inmutable = inmutable and True
        caso("E2E 11 · envíos y pasos imborrables (disparadores)", inmutable)
        con.close()
    except Exception as e:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        caso("E2E sin excepciones", False, f"{type(e).__name__}: {e}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    malos = [c for c in casos if not c["ok"]]
    if "--json" in ARGS:
        print(json.dumps({"casos": casos, "fallos": len(malos)}, ensure_ascii=False))
    else:
        print(f"{'✔' if not malos else '✘'} Prueba de extremo a extremo (proveedor simulado): {len(casos) - len(malos)} de {len(casos)} casos bien")
    return 0 if not malos else 1


def main():
    if "--prueba-e2e" in ARGS:
        return prueba_e2e()
    if "--al-momento" in ARGS:
        return al_momento(int(ARGS[ARGS.index("--al-momento") + 1]))
    if "--canario" in ARGS:
        with EN.conectar() as con:
            r = EN.canario(con)
            con.commit()
        print(json.dumps(r, ensure_ascii=False))
        return 0
    return vuelta_normal()


if __name__ == "__main__":
    sys.exit(main())

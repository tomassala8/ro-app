#!/usr/bin/env python3
"""migracion/rendimiento.py · que la app nueva no sea más lenta que la de hoy, y que nada tarde una eternidad.

  python3 migracion/rendimiento.py medir --base http://127.0.0.1:8770 --salida ~/RO_MIGRACION/rendimiento/viejo
  python3 migracion/rendimiento.py medir --base http://127.0.0.1:3000 --salida ~/RO_MIGRACION/rendimiento/nuevo
  python3 migracion/rendimiento.py comparar ~/RO_MIGRACION/rendimiento/viejo ~/RO_MIGRACION/rendimiento/nuevo
  python3 migracion/rendimiento.py carga --base http://127.0.0.1:3000 --pg postgresql://ro:ro@127.0.0.1:5432/ro_app

API: cada GET del contrato, para unas pocas personas, 5 veces (la primera no cuenta: calienta). Se guarda la mediana
y el p95 en milisegundos. Pantallas: capturar.mjs deja `_tiempos.json` (ms hasta que la pantalla está pintada).

ROJO si, en cualquier ruta o pantalla:
  · la nueva es más lenta que la de hoy en más de un 25 % y más de 100 ms (API) o 300 ms (pantalla), o
  · pasa del techo absoluto (API 1500 ms, pantalla 3000 ms) y la de hoy no lo pasaba.
Solo mide; no escribe nada en la app.
"""
import argparse
import json
import os
import statistics
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from contrato import rutas_get  # noqa: E402

TECHO_API, TECHO_PANTALLA = 1500, 3000
MARGEN = 1.25
HOLGURA_API, HOLGURA_PANTALLA = 100, 300


def pedir(base, ruta, yo):
    req = urllib.request.Request(base.rstrip("/") + ruta, headers={"Accept": "application/json", "X-RO-Yo": yo,
                                                                   "Cookie": f"ro_yo={yo}"})
    t = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            r.read()
            estado = r.status
    except urllib.error.HTTPError as e:
        e.read()
        estado = e.code
    except (urllib.error.URLError, TimeoutError):
        estado = 0
    return estado, (time.perf_counter() - t) * 1000


def medir(a):
    salida = Path(a.salida).expanduser()
    salida.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(a.base.rstrip("/") + "/api/elegir", timeout=30) as r:
        personas = [p["id"] for p in json.loads(r.read())["personas"]]
    personas = a.personas.split(",") if a.personas else personas[: a.cuantas]
    res = {}
    for ruta in ["/"] + rutas_get():
        tiempos, estados = [], set()
        for yo in personas:
            for i in range(a.veces + 1):
                estado, ms = pedir(a.base, ruta, yo)
                estados.add(estado)
                if i:
                    tiempos.append(ms)
        tiempos.sort()
        res[ruta] = {"mediana": round(statistics.median(tiempos), 1),
                     "p95": round(tiempos[min(len(tiempos) - 1, int(len(tiempos) * 0.95))], 1),
                     "estados": sorted(estados)}
    (salida / "api.json").write_text(json.dumps(res, indent=1, ensure_ascii=False))
    lentas = sorted(res.items(), key=lambda kv: -kv[1]["p95"])[:5]
    print(f"{len(res)} rutas medidas con {len(personas)} personas. Las más lentas (p95 ms): "
          + ", ".join(f"{r} {v['p95']}" for r, v in lentas))


def peor(viejo, nuevo, techo, holgura):
    if nuevo > techo and viejo <= techo:
        return f"pasa del techo de {techo} ms"
    if nuevo > viejo * MARGEN and nuevo - viejo > holgura:
        return f"más lenta que hoy ({viejo:.0f} → {nuevo:.0f} ms)"
    return None


def conocidos():
    """~/RO_MIGRACION/excepciones_rendimiento.txt: «ruta o pantalla  # L-n motivo». Salen como aviso, no tumban la puerta."""
    f = Path(os.environ.get("RO_MIGRACION", "~/RO_MIGRACION")).expanduser() / "excepciones_rendimiento.txt"
    if not f.exists():
        return {}
    return {l.split("#")[0].strip(): l.split("#", 1)[1].strip() if "#" in l else "" for l in f.read_text().splitlines()
            if l.split("#")[0].strip()}


def comparar(a):
    viejo, nuevo = Path(a.viejo).expanduser(), Path(a.nuevo).expanduser()
    malos = []
    va, na = json.loads((viejo / "api.json").read_text()), json.loads((nuevo / "api.json").read_text())
    for ruta, v in va.items():
        n = na.get(ruta)
        if not n:
            malos.append(f"API {ruta}: sin medir en la nueva")
            continue
        if any(e >= 500 or e == 0 for e in n["estados"]) and not any(e >= 500 or e == 0 for e in v["estados"]):
            malos.append(f"API {ruta}: errores {n['estados']} que hoy no da")
        motivo = peor(v["p95"], n["p95"], TECHO_API, HOLGURA_API)
        if motivo:
            malos.append(f"API {ruta}: {motivo}")
    capt_v = Path(a.capturas_viejo or viejo.parent.parent / "capturas" / "viejo").expanduser() / "_tiempos.json"
    capt_n = Path(a.capturas_nuevo or viejo.parent.parent / "capturas" / "nuevo").expanduser() / "_tiempos.json"
    pantallas = 0
    if capt_v.exists() and capt_n.exists():
        # Una foto por persona y pantalla es una sola muestra (la primera de cada persona sale fría): se compara la
        # mediana de cada pantalla entre todas las personas, no cada foto suelta.
        def por_pantalla(d):
            g = {}
            for clave, ms in d.items():
                tam, _persona, pant = clave.split("/", 2)
                g.setdefault(f"{tam}/{pant}", []).append(ms)
            return {k: statistics.median(v) for k, v in g.items()}
        tv = por_pantalla(json.loads(capt_v.read_text()))
        for clave, ms in por_pantalla(json.loads(capt_n.read_text())).items():
            if clave in tv:
                pantallas += 1
                motivo = peor(tv[clave], ms, TECHO_PANTALLA, HOLGURA_PANTALLA)
                if motivo:
                    malos.append(f"pantalla {clave}: {motivo}")
    else:
        print("Aviso: faltan los tiempos de pantalla (_tiempos.json de capturar.mjs); solo se compara la API.")
    print(f"{len(va)} rutas y {pantallas} pantallas comparadas.")
    exc = conocidos()
    sabidos = [m for m in malos if any(m.split(":")[0].split(" ", 1)[1] == k for k in exc)]
    for m in sabidos:
        print(f"  ⚠ {m}  (conocido: {exc[m.split(':')[0].split(' ', 1)[1]]})")
    malos = [m for m in malos if m not in sabidos]
    for m in malos:
        print("  ✘ " + m)
    if malos:
        sys.exit(1)
    print("Igual o más rápida que hoy, y nada por encima del techo.")


def carga(a):
    """30 personas a la vez, como un lunes a las 9:00: cada una abre la app (todas sus rutas, 6 en paralelo como el
    navegador) y repite. Antes, una vuelta de calentamiento que no cuenta. ROJO si algo da 5xx o se cuelga, si Postgres
    pasa de --max-conexiones (con --pg), o si el p95/p99 pasan de 1500/3000 ms Y son peores que los de la app de hoy
    con la misma carga (--referencia) en más de un 25 % y 100 ms. Solo lee: no escribe nada en la app."""
    ref = None
    if a.referencia:
        ref = medir_carga(a.referencia, a, None)
        print(f"  la app de hoy con la misma carga: p95 {ref[1]:.0f} ms · p99 {ref[2]:.0f} ms")
    malas, p95, p99, pico = medir_carga(a.base, a, a.pg)
    fallos = []
    if malas:
        fallos.append(f"{len(malas)} peticiones con 5xx o sin respuesta: " + "; ".join(malas[:10]))
    for nombre, valor, techo, i in (("p95", p95, TECHO_API, 1), ("p99", p99, TECHO_PANTALLA, 2)):
        hoy = ref[i] if ref else 0
        if valor > techo and (not ref or (valor > hoy * MARGEN and valor - hoy > HOLGURA_API)):
            fallos.append(f"{nombre} {valor:.0f} ms > {techo} ms" + (f" (hoy {hoy:.0f} ms)" if ref else ""))
    if a.pg and pico > a.max_conexiones:
        fallos.append(f"{pico} conexiones a Postgres > {a.max_conexiones}")
    for f in fallos:
        print("  ✘", f)
    sys.exit(1 if fallos else 0)


def medir_carga(base, a, pg):
    import concurrent.futures as cf
    import random
    import threading
    with urllib.request.urlopen(base.rstrip("/") + "/api/elegir", timeout=30) as r:
        personas = [p["id"] for p in json.loads(r.read())["personas"]]
    rutas = ["/"] + rutas_get()
    tiempos, malas, pico = [], [], [0]
    candado, fin = threading.Lock(), threading.Event()

    def vigilar_pg():   # cuántas conexiones abre todo esto en Postgres (en la nube hay tope)
        import psycopg
        while not fin.is_set():
            try:
                with psycopg.connect(pg, autocommit=True) as c:
                    n = c.execute("SELECT count(*) FROM pg_stat_activity WHERE datname = current_database()").fetchone()[0]
                pico[0] = max(pico[0], n)
            except Exception:
                pass
            fin.wait(0.5)

    def persona(i):
        yo = personas[i % len(personas)]
        orden = rutas[:]
        random.Random(i).shuffle(orden)
        with cf.ThreadPoolExecutor(6) as ex:
            for _ in range(a.vueltas):
                for ruta, (estado, ms) in zip(orden, ex.map(lambda r: pedir(base, r, yo), orden)):
                    with candado:
                        tiempos.append(ms)
                        if estado == 0 or estado >= 500:
                            malas.append(f"{yo} {ruta} → {estado or 'sin respuesta'}")

    for r in rutas:   # calentamiento (cachés, primera conexión): no cuenta
        pedir(base, r, personas[0])
    hilo = threading.Thread(target=vigilar_pg, daemon=True) if pg else None
    if hilo:
        hilo.start()
    t0 = time.perf_counter()
    with cf.ThreadPoolExecutor(a.personas) as ex:
        list(ex.map(persona, range(a.personas)))
    fin.set()
    tiempos.sort()
    p95 = tiempos[int(len(tiempos) * 0.95)]
    p99 = tiempos[min(len(tiempos) - 1, int(len(tiempos) * 0.99))]
    print(f"{base}: {a.personas} personas a la vez · {len(tiempos)} peticiones en {time.perf_counter() - t0:.1f} s · "
          f"p50 {statistics.median(tiempos):.0f} ms · p95 {p95:.0f} ms · p99 {p99:.0f} ms"
          + (f" · pico de conexiones a Postgres {pico[0]}" if pg else ""))
    return malas, p95, p99, pico[0]


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="orden", required=True)
    m = sub.add_parser("medir")
    m.add_argument("--base", required=True)
    m.add_argument("--salida", required=True)
    m.add_argument("--personas")
    m.add_argument("--cuantas", type=int, default=3)
    m.add_argument("--veces", type=int, default=5)
    c = sub.add_parser("comparar")
    c.add_argument("viejo")
    c.add_argument("nuevo")
    c.add_argument("--capturas-viejo")
    c.add_argument("--capturas-nuevo")
    k = sub.add_parser("carga")
    k.add_argument("--base", required=True)
    k.add_argument("--personas", type=int, default=30)
    k.add_argument("--vueltas", type=int, default=2)
    k.add_argument("--referencia", help="la app de hoy (http://127.0.0.1:8770): la misma carga, para comparar")
    k.add_argument("--pg", help="URL de Postgres para vigilar cuántas conexiones se abren")
    k.add_argument("--max-conexiones", type=int, default=60)
    a = ap.parse_args()
    {"medir": medir, "comparar": comparar, "carga": carga}[a.orden](a)

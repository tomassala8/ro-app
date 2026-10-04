#!/usr/bin/env python3
"""fuentes/probar_lectura.py · pruebas de fuentes/lectura.py (N-01) con una API FALSA. Ninguna llamada sale fuera.

  python3 fuentes/probar_lectura.py          # SQLite temporal (RO_DB a un fichero que se borra al acabar)
  DATABASE_URL=postgresql://… python3 fuentes/probar_lectura.py --pg
                                             # Postgres: crea la tabla si falta, prueba y borra SOLO sus filas
                                             # (fuente «prueba_lectura…»). No poda el resto de la tabla.

Comprueba: lectura buena → se guarda; API caída → la última buena marcada vieja con su hora; todo a 0 tras un dato
bueno → la última buena; nunca hubo dato → «sin dato» (None, nunca 0); comprobación propia (sospechoso); se guardan 30;
estructura sin dato ({"rows": []}) y ceros en texto ("0,00") tras un dato bueno → la última buena; caída de más del 80 %
de las hojas → la última buena; una lista vieja va envuelta con «_viejo».
Sale con 1 si algo falla.
"""
import os
import sys
import tempfile
from pathlib import Path

APP = Path(__file__).resolve().parent.parent
PG = "--pg" in sys.argv
if PG:
    if not os.environ.get("DATABASE_URL", "").startswith("postgres"):
        sys.exit("--pg necesita DATABASE_URL=postgresql://…")
else:
    os.environ.pop("DATABASE_URL", None)
    TMP = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name
    os.environ["RO_DB"] = TMP
sys.path.insert(0, str(APP))
from fuentes import lectura as L   # noqa: E402

F = "prueba_lectura"


class ApiFalsa:
    """Hace de API: devuelve lo que se le pone, o falla con un código HTTP."""
    def __init__(self):
        self.respuesta, self.falla = None, None

    def __call__(self):
        if self.falla:
            e = RuntimeError(f"HTTP {self.falla} de la API falsa")
            e.code = self.falla
            raise e
        return self.respuesta


def filas(sql, args=()):
    con = L.conectar()
    try:
        with con:
            return con.execute(sql, args).fetchall()
    finally:
        con.close()


def borrar_pruebas():
    con = L.conectar()
    try:
        with con:
            L._preparar(con)
            con.execute("DELETE FROM fuente_lectura WHERE fuente LIKE ?", (F + "%",))
    finally:
        con.close()


def main():
    MAL = []

    def ok(c, t):
        print(("✔ " if c else "✘ ") + t)
        if not c:
            MAL.append(t)

    borrar_pruebas()
    api = ApiFalsa()

    # 1 · nunca hubo dato y la API cae → sin dato, nunca 0
    api.falla = 503
    l = L.leer(F, "cli_a", api)
    ok(l.estado == "sin_dato" and l.datos is None and l.desde is None, f"nunca hubo dato → sin_dato, datos None ({l})")
    ok(L.marcar(l) is None, "marcar(sin_dato) → None")
    ok("503" in (l.error or ""), "el error dice el código HTTP")
    api.falla, api.respuesta = None, {}
    ok(L.leer(F, "cli_a", api).estado == "sin_dato", "vacío sin dato previo → sin_dato")

    # 2 · lectura buena → se guarda y se devuelve
    bueno = {"clics": 120, "impresiones": 4000, "ctr": 0.03, "paginas": [{"url": "/a", "clics": 70}]}
    api.respuesta = bueno
    l = L.leer(F, "cli_a", api)
    ok(l.estado == "ok" and l.datos == bueno and l.desde, f"lectura buena → ok con hora ({l.desde})")
    r = filas("SELECT * FROM fuente_ultimo_bueno WHERE fuente=? AND recurso=?", (F, "cli_a"))
    ok(len(r) == 1 and r[0]["huella"] == L.huella(bueno), "la vista fuente_ultimo_bueno la tiene, con su huella")
    ok(L.marcar(l) == bueno, "marcar(ok) → los datos tal cual")
    desde = l.desde

    # 3 · la API cae → la última buena, marcada vieja con su hora
    api.falla = 403
    l = L.leer(F, "cli_a", api)
    ok(l.estado == "viejo" and l.datos == bueno and l.desde == desde, "API caída → la última buena, estado viejo")
    m = L.marcar(l)
    ok(m["_viejo"] is True and m["_desde"] == desde and m["clics"] == 120, "marcar(viejo) → «_viejo» y «_desde»")
    ok("_viejo" not in l.datos, "marcar no toca los datos originales")
    api.falla = None

    # 4 · todo a 0 tras un dato bueno → la última buena
    api.respuesta = {"clics": 0, "impresiones": 0, "ctr": 0.0, "paginas": [{"url": "/a", "clics": 0}]}
    l = L.leer(F, "cli_a", api)
    ok(l.estado == "viejo" and l.datos["clics"] == 120 and "a_cero" in l.error, "todo a 0 tras dato bueno → viejo")

    # 5 · vacío y «_error» dentro del cuerpo → la última buena
    for vacio in (None, {}, [], "", {"_error": "401 Unauthorized"}):
        api.respuesta = vacio
        l = L.leer(F, "cli_a", api)
        ok(l.estado == "viejo" and l.datos == bueno, f"respuesta {vacio!r} → viejo")

    # 6 · los errores también se guardan; ninguna fila buena con ceros
    err = filas("SELECT codigo FROM fuente_lectura WHERE fuente=? AND recurso=? AND ok=0", (F, "cli_a"))
    ok({"503", "vacio", "403", "a_cero", "error"} <= {e["codigo"] for e in err}, f"{len(err)} errores apuntados")
    buenas = filas("SELECT cuerpo FROM fuente_lectura WHERE fuente=? AND recurso=? AND ok=1", (F, "cli_a"))
    ok(len(buenas) == 1, "solo una lectura buena guardada")

    # 7 · un 0 legítimo: si la última buena ya era 0, el 0 vale
    api.respuesta = {"clics": 0}
    ok(L.leer(F, "cli_cero", api).estado == "ok", "0 sin dato previo → ok")
    ok(L.leer(F, "cli_cero", api).estado == "ok", "0 tras 0 → ok")

    # 8 · comprobación propia de la fuente
    def menos_de_la_mitad(nuevo, anterior):
        if anterior and nuevo.get("clics", 0) < anterior.get("clics", 0) / 2:
            return "los clics caen más de la mitad"
    api.respuesta = {"clics": 10, "impresiones": 4000}
    l = L.leer(F, "cli_a", api, sospechoso=menos_de_la_mitad)
    ok(l.estado == "viejo" and l.datos["clics"] == 120 and "sospechoso" in l.error, "sospechoso → viejo")
    api.respuesta = {"clics": 100, "impresiones": 3900}
    ok(L.leer(F, "cli_a", api, sospechoso=menos_de_la_mitad).estado == "ok", "no sospechoso → ok")

    # 9 · recursos separados: lo de un cliente no sirve para otro
    api.falla = 500
    ok(L.leer(F, "cli_b", api).estado == "sin_dato", "otro recurso sin dato → sin_dato (no hereda)")
    api.falla = None

    # 10 · se guardan 30 lecturas buenas por fuente y recurso
    for i in range(35):
        api.respuesta = {"clics": 200 + i}
        L.leer(F, "cli_30", api)
    n = filas("SELECT COUNT(*) AS n FROM fuente_lectura WHERE fuente=? AND recurso=? AND ok=1", (F, "cli_30"))[0]["n"]
    ok(n == 30, f"35 lecturas buenas → quedan {n} (30)")
    api.falla = 503
    ok(L.leer(F, "cli_30", api).datos == {"clics": 234}, "tras podar, la última buena es la más reciente")
    api.falla = None

    # 11 · estructura sin dato tras un dato bueno → la última buena, nunca la vacía como nueva buena
    api.respuesta = {"rows": [{"clics": 5}]}
    ok(L.leer(F, "cli_rows", api).estado == "ok", "{'rows': [{'clics': 5}]} → ok")
    for forma in ({"rows": []}, {"rows": [], "next": None}, {"a": {"b": []}}, [[]], {"x": None, "y": ""}):
        api.respuesta = forma
        l = L.leer(F, "cli_rows", api)
        ok(l.estado == "viejo" and l.datos == {"rows": [{"clics": 5}]} and "vacio" in l.error, f"{forma!r} tras dato → viejo")
    ok(L.vacio({"nombre": "Acme"}) is False and L.vacio(["/a"]) is False and L.vacio({"rows": [], "n": "3"}) is False,
       "vacio(): textos sueltos, listas con algo o cifras en texto no son vacío")

    # 12 · nunca hubo dato y llega estructura sin dato → sin_dato, no ok
    api.respuesta = {"rows": []}
    l = L.leer(F, "cli_nuevo", api)
    ok(l.estado == "sin_dato" and l.datos is None and L.marcar(l) is None, f"{{'rows': []}} sin dato previo → sin_dato ({l.estado})")

    # 13 · ceros en texto: "0", "0.0", "0,00" son cifras
    ok(L.a_cero({"clics": "0", "coste": "0,00", "ctr": "0.0"}) and not L.a_cero({"clics": "0", "coste": "1,50"}),
       "a_cero ve los ceros en texto")
    ok(not L.a_cero({"nombre": "Acme", "activo": False}), "a_cero: sin cifras (texto, booleanos) no es «a cero»")
    api.respuesta = {"clics": "120", "coste": "35,40"}
    ok(L.leer(F, "cli_txt", api).estado == "ok", "cifras en texto → ok")
    api.respuesta = {"clics": "0", "coste": "0,00"}
    l = L.leer(F, "cli_txt", api)
    ok(l.estado == "viejo" and l.datos["clics"] == "120" and "a_cero" in l.error, "ceros en texto tras dato → viejo")

    # 14 · caída grande de hojas con dato (menos del 20 %) → la última buena
    api.respuesta = {"paginas": [{"url": f"/p{i}", "clics": 10 + i} for i in range(10)]}   # 20 hojas
    ok(L.leer(F, "cli_hojas", api).estado == "ok", "20 hojas → ok")
    api.respuesta = {"paginas": [{"url": "/p0", "clics": 10}]}                              # 2 de 20 (10 %)
    l = L.leer(F, "cli_hojas", api)
    ok(l.estado == "viejo" and len(l.datos["paginas"]) == 10 and "menguado" in l.error, f"2 de 20 hojas → viejo ({l.error})")
    api.respuesta = {"paginas": [{"url": f"/p{i}", "clics": 10 + i} for i in range(2)]}    # 4 de 20 (20 %)
    ok(L.leer(F, "cli_hojas", api).estado == "ok", "4 de 20 hojas (justo el 20 %) → ok")

    # 15 · marcar una lista vieja: va envuelta para que la pantalla lo sepa
    api.respuesta = [{"url": "/a", "clics": 7}]
    l = L.leer(F, "cli_lista", api)
    ok(l.estado == "ok" and L.marcar(l) == [{"url": "/a", "clics": 7}], "lista buena → marcar la deja tal cual")
    api.falla = 500
    l = L.leer(F, "cli_lista", api)
    m = L.marcar(l)
    ok(l.estado == "viejo" and m == {"datos": [{"url": "/a", "clics": 7}], "_viejo": True, "_desde": l.desde},
       "lista vieja → {'datos': …, '_viejo': True, '_desde': hora}")
    api.falla = None

    if not PG:   # podar() es global: en Postgres no se toca lo que no es de la prueba
        con = L.conectar()
        with con:
            for i in range(5):
                con.execute("INSERT INTO fuente_lectura (fuente, recurso, ok, cuerpo) VALUES (?,?,1,?)", (F, "cli_30", "{}"))
            con.execute("INSERT INTO fuente_lectura (fuente, recurso, hora, ok, codigo) VALUES (?,?,?,0,'503')",
                        (F, "cli_30", "2000-01-01 00:00:00"))
            borradas = L.podar(con)
        con.close()
        n = filas("SELECT COUNT(*) AS n FROM fuente_lectura WHERE fuente=? AND recurso=? AND ok=1", (F, "cli_30"))[0]["n"]
        ok(n == 30 and borradas == 6, f"podar() → 30 buenas y fuera el error de hace más de 30 días ({borradas} borradas)")
        viejos = filas("SELECT COUNT(*) AS n FROM fuente_lectura WHERE hora < '2001-01-01'")[0]["n"]
        ok(viejos == 0, "ningún error de más de 30 días")

    borrar_pruebas()
    quedan = filas("SELECT COUNT(*) AS n FROM fuente_lectura WHERE fuente LIKE ?", (F + "%",))[0]["n"]
    ok(quedan == 0, "las filas de la prueba se han borrado")
    print(f"\n{'Postgres' if PG else 'SQLite'}: {'TODO BIEN' if not MAL else f'{len(MAL)} FALLOS'}")
    return 1 if MAL else 0


if __name__ == "__main__":
    try:
        codigo = main()
    finally:
        if not PG:
            os.unlink(TMP)
    sys.exit(codigo)

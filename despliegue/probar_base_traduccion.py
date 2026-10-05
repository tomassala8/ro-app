#!/usr/bin/env python3
"""despliegue/probar_base_traduccion.py · regresión del traductor SQLite → Postgres de despliegue/base.py.

Sin Postgres: comprueba la traducción pura (disparadores «RAISE(ABORT,'…')» sin espacio y sin «;» final, DDL
lanzado con execute(), nombres de disparador construidos con «+», AUTOINCREMENT, datetime('now')).
Con DATABASE_URL (un Postgres de PRUEBAS con permiso para crear bases): crea una base temporal propia, aplica el
esquema y los preparar() de los módulos nuevos A TRAVÉS de ConexionPG, escribe, y prueba que los disparadores del
rastro impiden UPDATE/DELETE/TRUNCATE. Al terminar borra esa base temporal; nunca toca la de DATABASE_URL.

  python3 despliegue/probar_base_traduccion.py
  DATABASE_URL=postgresql://ro@127.0.0.1:5432/postgres python3 despliegue/probar_base_traduccion.py
"""
import importlib
import json
import os
import re
import sys
import threading
import unittest
import uuid
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlsplit, urlunsplit

AQUI = Path(__file__).resolve().parent
APP = AQUI.parent
sys.path[:0] = [str(AQUI), str(APP)]
import base as B  # noqa: E402

# Módulos con preparar(con) que crean tabla + disparadores con execute() (no executescript).
MODULOS = ("decisiones_durables_382", "operaciones_anomalias_276", "operaciones_feedback_273",
           "operaciones_notas_equipo_281", "operaciones_pedidos_account", "operaciones_prioridades_300",
           "operaciones_registros_269", "operaciones_registros_272", "intenciones_acciones")
# tabla → (operaciones bloqueadas, mensaje)
INMUTABLES = {
    "decisiones_intenciones_382": (("UPDATE", "DELETE"), "Intención inmutable"),
    "operaciones_anomalias_276": (("UPDATE", "DELETE"), "Revisión de horas inmutable"),
    "operaciones_feedback_273": (("UPDATE", "DELETE"), "Opinión declarada inmutable"),
    "operaciones_notas_equipo_281": (("UPDATE", "DELETE"), "Nota humana inmutable"),
    "operaciones_pedidos_account_294": (("UPDATE", "DELETE"), "Pedido inmutable"),
    "operaciones_prioridades_300": (("UPDATE", "DELETE"), "Rastro propio inmutable"),
    "operaciones_registros_269": (("UPDATE", "DELETE"), "Registro operativo inmutable"),
    "operaciones_control_272": (("UPDATE", "DELETE"), "Registro de control inmutable"),
    "ia_gasto": (("UPDATE", "DELETE"), "El gasto de la IA no se"),
    "ia_topes": (("UPDATE", "DELETE"), "Un cambio de topes no se"),
    "ia_reservas": (("DELETE",), "Una reserva no se borra"),
    "planes_fuegos_255": (("UPDATE", "DELETE"), "El historial de planes no se"),
}
VALORES = {"ia_reservas": {"estado": "activa", "reservado_eur": 1.0}}


class Grabadora:
    """Conexión falsa: guarda el SQL que lanza preparar() (sin transacción abierta, como una conexión nueva)."""
    in_transaction = False

    def __init__(self):
        self.sql = []

    def execute(self, sql, args=()):
        self.sql.append(sql)
        return SimpleNamespace(fetchone=lambda: None, fetchall=lambda: [], lastrowid=None)


def sql_de_preparar():
    sql = []
    for nombre in MODULOS:
        g = Grabadora()
        importlib.import_module(nombre).preparar(g)
        sql += [(nombre, s) for s in g.sql]
    import actas
    import vistas_tareas
    g = Grabadora()
    vistas_tareas.preparar(g)
    return sql + [("actas", s) for s in actas.TABLAS] + [("vistas_tareas", s) for s in g.sql]


class Traduccion(unittest.TestCase):
    def test_disparador_sin_espacio_ni_punto_y_coma(self):
        pg = B.esquema_postgres("CREATE TRIGGER IF NOT EXISTS t_sin_delete BEFORE DELETE ON t "
                                "BEGIN SELECT RAISE(ABORT,'No se borra'); END")
        self.assertIn("EXECUTE FUNCTION ro_prohibido('No se borra');", pg)
        self.assertIn("BEFORE TRUNCATE ON t", pg)
        self.assertNotIn("RAISE(ABORT", pg)

    def test_disparador_clasico_sigue_igual(self):
        pg = B.esquema_postgres("CREATE TRIGGER IF NOT EXISTS t_sin_update BEFORE UPDATE ON t "
                                "BEGIN SELECT RAISE(ABORT, 'No se cambia'); END;\nCREATE INDEX IF NOT EXISTS i ON t (a);")
        self.assertIn("ro_prohibido('No se cambia');\nCREATE INDEX IF NOT EXISTS i ON t (a);", pg)

    def test_disparador_con_condicion_sin_punto_y_coma(self):
        pg = B.esquema_postgres("CREATE TRIGGER IF NOT EXISTS t_estado BEFORE UPDATE ON t\n  WHEN NEW.a IS NOT OLD.a\n"
                                "  BEGIN SELECT RAISE(ABORT,'Solo el estado'); END")
        self.assertIn("IF (NEW.a IS DISTINCT FROM OLD.a) THEN RAISE EXCEPTION '%', 'Solo el estado'", pg)
        self.assertNotIn("RAISE(ABORT", pg)

    def test_ddl_por_execute(self):
        q, _ = B.traducir("CREATE TRIGGER IF NOT EXISTS x_sin_" + "update" + " BEFORE " + "UPDATE" +
                          " ON x BEGIN SELECT RAISE(ABORT,'Inmutable'); END")
        self.assertIn("CREATE OR REPLACE FUNCTION ro_prohibido()", q)   # la función va delante: puede no existir aún
        self.assertIn("RAISE EXCEPTION '%%'", q)                        # % doblados: execute() sin args los deshace
        self.assertNotIn("%s", q)
        q, _ = B.traducir("CREATE TABLE IF NOT EXISTS x (id INTEGER PRIMARY KEY AUTOINCREMENT, "
                          "creada TEXT NOT NULL DEFAULT (datetime('now')))")
        self.assertIn("id BIGSERIAL PRIMARY KEY", q)
        self.assertNotIn("datetime(", q)
        self.assertNotIn("ro_prohibido", q)

    def test_preparar_de_los_modulos_se_traduce_entero(self):
        for nombre, sql in sql_de_preparar():
            with self.subTest(nombre=nombre, sql=sql[:60]):
                self.assertTrue(B._solo_crea_si_no_existe(sql), "debe contar como DDL «una vez por proceso»")
                q, _ = B.traducir(sql)
                self.assertNotRegex(q, r"RAISE\(\s*ABORT|AUTOINCREMENT|datetime\(")

    def test_fila_como_sqlite3_row(self):
        f = B.Fila(["coste", "tarea", "quien"], [1.5, "consejo", "ana"])
        e, t, q = f                                   # desempaquetar da valores (ia_gasto._reservado_en)
        self.assertEqual((e, t, q), (1.5, "consejo", "ana"))
        self.assertEqual(tuple(f[:2]), (1.5, "consejo"))   # trozos (ia_gasto.apuntar: tuple(r[:3]))
        self.assertEqual((f["quien"], f[0]), ("ana", 1.5))
        self.assertEqual(dict(f), {"coste": 1.5, "tarea": "consejo", "quien": "ana"})
        self.assertEqual(json.loads(json.dumps(f)), dict(f))

    def test_esquemas_enteros_sin_restos_sqlite(self):
        import ia_gasto
        import planes_fuegos_255
        for sql in ((APP / "schema_v2.sql").read_text(), ia_gasto.TABLAS_SQL, planes_fuegos_255.ESQUEMA):
            self.assertNotRegex(B.esquema_postgres(sql), r"RAISE\(\s*ABORT|AUTOINCREMENT")


def _url_con_base(url, base):
    p = urlsplit(url)
    return urlunsplit((p.scheme, p.netloc, "/" + base, p.query, p.fragment))


@unittest.skipUnless(os.environ.get("DATABASE_URL"), "sin DATABASE_URL: solo la traducción pura")
class EnPostgres(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import psycopg
        cls.admin = os.environ["DATABASE_URL"]
        cls.base = f"ro_prueba_traduccion_{os.getpid()}"
        with psycopg.connect(cls.admin, autocommit=True) as c:
            c.execute(f"DROP DATABASE IF EXISTS {cls.base}")
            c.execute(f"CREATE DATABASE {cls.base}")
        cls.url = _url_con_base(cls.admin, cls.base)
        cls.con = lambda self=None: B.ConexionPG(cls.url)
        c = cls.con()
        c.executescript((APP / "schema_v2.sql").read_text())
        import ia_gasto
        import planes_fuegos_255
        c.executescript(ia_gasto.TABLAS_SQL)
        c.executescript(planes_fuegos_255.ESQUEMA)
        c.close()
        for _ in range(2):   # dos veces: idempotente (y la segunda sale de la caché del proceso)
            for nombre, sql in sql_de_preparar():
                with cls.con() as c:
                    c.execute(sql)

    @classmethod
    def tearDownClass(cls):
        import psycopg
        with B._CANDADO:
            libres, B._LIBRES[:] = list(B._LIBRES), []
        for c in libres:
            B._cerrar(c)
        with psycopg.connect(cls.admin, autocommit=True) as c:
            c.execute(f"DROP DATABASE IF EXISTS {cls.base} WITH (FORCE)")

    def _fila(self, tabla):
        """Inserta una fila de relleno; devuelve (lastrowid, columna de la clave)."""
        with self.con() as c:
            cols = c.execute("SELECT column_name, data_type, column_default FROM information_schema.columns "
                             "WHERE table_schema='public' AND table_name=? AND is_nullable='NO' ORDER BY ordinal_position",
                             (tabla,)).fetchall()
            pon = {r["column_name"]: r["data_type"] for r in cols if r["column_default"] is None}
            vals = [VALORES.get(tabla, {}).get(k, 1 if "int" in t else 1.0 if t in ("real", "double precision") else "x")
                    for k, t in pon.items()]
            cur = c.execute(f"INSERT INTO {tabla} ({', '.join(pon)}) VALUES ({', '.join('?' * len(pon))})", vals)
            return cur.lastrowid

    def test_tablas_y_disparadores_creados(self):
        with self.con() as c:
            for tabla, (ops, _) in INMUTABLES.items():
                n = c.execute("SELECT count(*) FROM pg_trigger WHERE tgrelid = ?::regclass AND NOT tgisinternal",
                              (tabla,)).fetchone()[0]
                self.assertGreaterEqual(n, len(ops) + ("DELETE" in ops), tabla)
            for t in ("actas_lotes", "actas_claves", "tareas_vistas_privadas", "intenciones_acciones"):
                self.assertTrue(c.execute("SELECT 1 FROM sqlite_master WHERE name=?", (t,)).fetchone(), t)

    def test_rastro_inmutable(self):
        for tabla, (ops, msg) in INMUTABLES.items():
            with self.subTest(tabla=tabla):
                rid = self._fila(tabla)
                serial = B.ConexionPG(self.url)._auto(tabla)
                if serial:
                    self.assertIsInstance(rid, int)
                for op, sql in (("UPDATE", f"UPDATE {tabla} SET {self._col(tabla)} = {self._col(tabla)}"),
                                ("DELETE", f"DELETE FROM {tabla}"), ("DELETE", f"TRUNCATE {tabla}")):
                    if op not in ops:
                        continue
                    with self.assertRaises(Exception) as e, self.con() as c:
                        c.execute(sql)
                    self.assertIn(msg, str(e.exception))
                with self.con() as c:
                    self.assertGreaterEqual(c.execute(f"SELECT count(*) FROM {tabla}").fetchone()[0], 1)

    def _col(self, tabla):
        with self.con() as c:
            return c.execute("PRAGMA table_info(" + tabla + ")").fetchall()[-1][1]

    def test_reserva_ia_cambia_estado_pero_no_se_borra(self):
        rid = str(uuid.uuid4())
        with self.con() as c:
            self.assertFalse(c.in_transaction)
            c.execute("BEGIN IMMEDIATE")
            self.assertTrue(c.in_transaction)
            c.execute("INSERT INTO ia_reservas VALUES (?,?,?,?,?,?,?)", (rid, "2026-10-04 00:00:00", "consejo", "f", "principal", 1.0, "activa"))
        with self.con() as c:
            c.execute("UPDATE ia_reservas SET estado='incierta' WHERE id=? AND estado='activa'", (rid,))
            self.assertEqual(c.execute("SELECT estado FROM ia_reservas WHERE id=?", (rid,)).fetchone()[0], "incierta")

    def test_ia_gasto_reserva_y_apunta(self):
        # El presupuesto de la IA de verdad sobre Postgres: reserva (BEGIN IMMEDIATE + in_transaction) → apunta → cierra.
        from unittest.mock import patch
        import ia_gasto as G
        precios = {"modelo-fixture": {"entrada": 1., "cache_escrita": 1.25, "cache_leida": .1, "salida": 5.}}
        with patch.object(G, "S", SimpleNamespace(conectar=self.con)), patch.object(G.IA_REAL, "autorizada", lambda: True), \
                patch.object(G, "PRECIOS", precios), patch.object(G, "PRECIOS_VERIFICADOS", True):
            t = G.topes()
            rid = G._comprobar_y_reservar("consejo", "fixture", "principal", 0.5, t)
            self.assertGreater(G._reservado(quien="fixture"), 0)
            eur = G.apuntar("consejo", "fixture", None, "modelo-fixture", "principal", {"entrada": 1000, "salida": 100},
                            True, t=t, reserva_id=rid)
            self.assertGreater(eur, 0)
            with self.con() as c:
                self.assertEqual(c.execute("SELECT estado FROM ia_reservas WHERE id=?", (rid,)).fetchone()[0], "cerrada")
            self.assertGreaterEqual(G.gastado()["mes"], eur)

    def test_intenciones_una_sola_accion_con_hilos(self):
        import intenciones_acciones as I
        cuerpo = {"intencion_id": str(uuid.uuid4()), "objeto": "tarea-fixture", "tipo": "cambiar_estado"}
        resultados, fallos = [], []

        def una():
            try:
                with self.con() as c:
                    I.iniciar(c)
                    resultados.append(I.guardar(c, "fixture", cuerpo, lambda con: con.execute(
                        "INSERT INTO acciones (quien, herramienta, tipo, objeto, estado) VALUES (?,?,?,?, 'simulada')",
                        ("fixture", "clickup", "cambiar_estado", "tarea-fixture")).lastrowid))
            except Exception as e:   # noqa: BLE001
                fallos.append(e)
        hilos = [threading.Thread(target=una) for _ in range(6)]
        [h.start() for h in hilos]
        [h.join() for h in hilos]
        self.assertEqual(fallos, [])
        self.assertEqual(sum(not rep for _, rep in resultados), 1)
        self.assertEqual(len({aid for aid, _ in resultados}), 1)

    def test_vistas_privadas(self):
        import vistas_tareas as V
        tareas = [{"id": "f", "asignados": ["ana"], "cli": "c-f", "lista_id": "l-f", "proyecto": "P", "etiquetas": [], "prio_n": 1}]
        filtros = {**V.DEFAULT, "cliente": "c-f", "lista": "l-f"}
        c = self.con()
        try:
            v = V.mutar(c, "ana", {"accion": "guardar", "nombre": "Mía", "filtros": filtros}, tareas)["vista"]
        finally:
            c.close()
        c = self.con()
        try:
            self.assertEqual(V.listar(c, "ana")["vistas"], [v])
        finally:
            c.close()
        c = self.con()
        try:
            V.mutar(c, "ana", {"accion": "eliminar", "id": v["id"], "revision": v["revision"]}, [])
            c.close()
            c = self.con()
            self.assertEqual(V.listar(c, "ana")["vistas"], [])
        finally:
            c.close()

    def test_actas_insert_y_clave(self):
        with self.con() as c:
            c.execute("INSERT INTO actas_lotes (quien, cliente_id, huella, resultado) VALUES (?,?,?,?)",
                      ("f", "c", "h", json.dumps({"ok": True})))
            c.execute("INSERT INTO actas_claves (quien, clave, cliente_id, huella) VALUES (?,?,?,?)", ("f", "k", "c", "h"))
            self.assertEqual(c.execute("SELECT resultado FROM actas_lotes WHERE quien=?", ("f",)).fetchone()["resultado"], '{"ok": true}')


if __name__ == "__main__":
    unittest.main(verbosity=2)

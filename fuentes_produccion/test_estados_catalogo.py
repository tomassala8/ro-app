"""Fixtures primarias y bucle real del generador, sin IO del generador ni regenerar datos."""
import ast
import datetime as dt
import json
import unittest
from pathlib import Path
from collections import defaultdict
from estados_catalogo import resolver_estado

BASE = Path(__file__).resolve().parents[1]
FIX = json.loads((BASE.parent / "RECUPERACION_CODEX_2026-10-03/ux/produccion_estados_fixture.json").read_text())
CAT = {"listas": {str(i): {"ok": True, "estados": [r]} for i, r in enumerate(FIX["estados"])}}


def tarea(i, estado=None, tipo=None):
    row = FIX["estados"][i]
    return {"id": "fixture-" + str(i), "lista_id": str(i), "estado": estado or row["status"],
            "tipo_estado": tipo or row["type"], "asignados": [{"id": "fixture-user"}],
            "nombre": "Tarea de prueba", "historial": []}


def cargar_bucle(ts, catalogo):
    tree = ast.parse((BASE / "fuentes_produccion/generar_produccion.py").read_text())
    names = {"d_local", "hist_desde", "es_final", "devuelta", "a_la_primera", "llegada"}
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
    main = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main")
    loop = next(n for n in main.body if isinstance(n, ast.For) and isinstance(n.target, ast.Name) and n.target.id == "t")
    hoy = dt.date(2026, 10, 3)
    def fecha(ms):
        if not ms:
            return None
        return dt.datetime.fromtimestamp(float(ms) / 1000, dt.timezone.utc)
    env = {"resolver_estado": resolver_estado, "fecha_ms": fecha, "dt": dt,
           "HOY": hoy, "AHORA": dt.datetime(2026, 10, 3, tzinfo=dt.timezone.utc),
           "HACE30": hoy - dt.timedelta(days=30), "FIN_SEMANA": dt.date(2026, 10, 5),
           "tareas": ts, "catalogo": catalogo, "por_carpeta": {}, "U": {"fixture-user": "fixture-person"},
           "P": {}, "account_de": {}, "nombre_cli": lambda x: x,
           "ESTADOS_REVISION_INTERNA": {"revisión project manager"}, "ESTADOS_TRABAJO": {"en curso"},
           "NO_COLA": {"backlog", "planning mensual"}, "ESPERA_CLIENTE": {"revisión cliente"},
           "PRIO": {}, "es_urgente": lambda x: False, "limpiar_tarea": lambda x: x,
           "cola": [], "rev_cli": [], "entregas": defaultdict(lambda: {"entregadas": 0,"con_fecha": 0,"en_fecha": 0,"primera_base": 0,"primera_si": 0}),
           "abiertas_p": defaultdict(lambda: defaultdict(int)), "proyectos_p": defaultdict(set), "sin_asignar": 0}
    exec(compile(ast.Module(body=funcs + [loop], type_ignores=[]), "generador_real", "exec"), env)
    return env


class EstadosTests(unittest.TestCase):
    def test_primary_custom_same_label_retained_done_hidden(self):
        env = cargar_bucle([tarea(0), tarea(1)], CAT)
        self.assertEqual([r["id"] for r in env["cola"]], ["fixture-0"])
        self.assertTrue(env["cola"][0]["estado_determinado"])
    def test_rejected_and_approved_are_terminal_not_success(self):
        for i in (2, 3):
            r = resolver_estado(tarea(i), CAT)
            self.assertTrue(r["final_flujo"])
            self.assertIn("no acredita", r["motivo"])
        self.assertFalse(cargar_bucle([tarea(2), tarea(3)], CAT)["cola"])
    def test_missing_unknown_scope_visible(self):
        for cat in ({}, {"listas": {"otra-lista": CAT["listas"]["0"]}}):
            fila = cargar_bucle([tarea(1)], cat)["cola"][0]
            self.assertFalse(fila["estado_determinado"])
    def test_contradiction_visible(self):
        t = tarea(1, tipo="custom")
        self.assertFalse(resolver_estado(t, CAT)["final_flujo"])
        self.assertEqual(len(cargar_bucle([t], CAT)["cola"]), 1)
    def test_duplicate_or_unknown_types_not_terminal(self):
        for rows in ([{"status": "completado", "type": "closed"}] * 2,
                     [{"status": "completado", "type": "inventado"}]):
            cat = {"listas": {"1": {"ok": True, "estados": rows}}}
            self.assertFalse(resolver_estado(tarea(1), cat)["determinado"])
    def test_unknown_backlog_not_silently_excluded(self):
        self.assertEqual(len(cargar_bucle([tarea(0, estado="backlog")], {})["cola"]), 1)
    def test_no_assignments_remain_outside_person_scope(self):
        t = tarea(0); t["asignados"] = [{"id": "foreign-user"}]
        env = cargar_bucle([t], CAT)
        self.assertFalse(env["cola"])
        self.assertEqual(env["sin_asignar"], 1)
    def test_historical_final_name_not_a_delivery(self):
        t = tarea(0); t["historial"] = [{"estado": "completado", "desde": 1790812800000}]
        t["cerrada"] = 1790812800000
        env = cargar_bucle([t], CAT)
        self.assertIsNone(env["llegada"](t, CAT))
        self.assertFalse(env["entregas"])
    def test_canonical_closure_is_only_operational_milestone(self):
        t = tarea(2); t["cerrada"] = 1790812800000
        env = cargar_bucle([t], CAT)
        self.assertIsNotNone(env["llegada"](t, CAT))
        self.assertFalse(env["cola"])
        self.assertIsNone(env["llegada"](t, {}))
    def test_review_remains_observed_milestone_not_terminal(self):
        t = tarea(0); t["historial"] = [{"estado": "revisión project manager", "desde": 1790812800000}]
        env = cargar_bucle([t], CAT)
        self.assertIsNotNone(env["llegada"](t, CAT))
        self.assertEqual(len(env["cola"]), 1)
    def test_inputs_unchanged(self):
        t = tarea(0); before = json.dumps([t, CAT], sort_keys=True)
        cargar_bucle([t], CAT)
        self.assertEqual(json.dumps([t, CAT], sort_keys=True), before)


if __name__ == "__main__":
    unittest.main()

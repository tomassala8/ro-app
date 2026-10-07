"""Pruebas puras sin red ni BD; fixtures independientes de clientes reales."""
import copy
import json
import unittest
from unittest.mock import patch
from embudo_eventos import calcular, ETAPAS

DESDE, HASTA, CORTE = "2026-09-01", "2026-09-30", "2026-10-03T12:00:00Z"


def ev(lead, etapa, fecha, eid=None, cliente="fixture", source="formulario"):
    return {"cliente_id": cliente, "source": source, "lead_id": lead,
        "event_id": eid or lead + "-" + etapa, "etapa": etapa, "fecha": fecha,
        "confirmado": True, "criterio_version": "ro-fixture-v1", "email": "PII-NO-SALIDA@example.com"}


def cobertura(etapas=ETAPAS, hasta=CORTE):
    return [{"cliente_id": "fixture", "source": "formulario", "desde": DESDE, "hasta": hasta,
             "etapas": list(etapas), "completa": True, "criterio_version": "ro-fixture-v1"}]


def run(eventos, cov=None):
    return calcular(eventos, DESDE, HASTA, CORTE, cov)


class Embudo(unittest.TestCase):
    def test_cohorte_y_eventos_separados_sin_ratio_cruzado(self):
        events = [ev("nuevo", "recibido", "2026-09-20T10:00:00Z"),
                  ev("nuevo", "venta", "2026-10-02T10:00:00Z"),
                  ev("viejo", "recibido", "2026-08-20T10:00:00Z"),
                  ev("viejo", "venta", "2026-09-20T10:00:00Z")]
        g = run(events, cobertura())["grupos"][0]
        self.assertEqual(g["cohorte"]["recibidos_observados"], 1)
        self.assertEqual(g["cohorte"]["etapas"]["venta"]["valor"], 1)
        self.assertEqual(g["cohorte"]["etapas"]["venta"]["tasa_sobre_recibidos"], 1)
        self.assertEqual(g["eventos_periodo"]["venta"]["eventos_observados"], 1)
        self.assertNotIn("tasa", g["eventos_periodo"]["venta"])
        self.assertEqual(g["cohorte"]["etapas"]["asistencia"]["valor"], 0)

    def test_ausente_no_cero_y_completo_si_cero_denominador(self):
        events = [ev("uno", "recibido", "2026-09-20T10:00:00Z")]
        stage = run(events)["grupos"][0]["cohorte"]["etapas"]["venta"]
        self.assertIsNone(stage["valor"])
        self.assertIsNone(stage["tasa_sobre_recibidos"])
        self.assertEqual(stage["estado"], "desconocido")
        stage = run(events, cobertura())["grupos"][0]["cohorte"]["etapas"]["venta"]
        self.assertEqual(stage["valor"], 0)
        self.assertEqual(stage["tasa_sobre_recibidos"], 0)
        empty = run([], cobertura())["grupos"][0]["cohorte"]["etapas"]["venta"]
        self.assertEqual(empty["valor"], 0)
        self.assertIsNone(empty["tasa_sobre_recibidos"])

    def test_replays_y_contactos_distintos_sin_doblar_leads(self):
        r = ev("uno", "recibido", "2026-09-20T10:00:00Z")
        c = ev("uno", "contacto", "2026-09-20T11:00:00Z")
        semantic = {**c, "event_id": "otra-entrega"}
        c2 = ev("uno", "contacto", "2026-09-21T11:00:00Z", "segundo-intento")
        result = run([r, r, c, c, semantic, c2], cobertura())
        self.assertEqual(result["incidencias"], {"replay_id": 2, "replay_semantico": 1})
        group = result["grupos"][0]
        self.assertEqual(group["cohorte"]["etapas"]["contacto"]["valor"], 1)
        self.assertEqual(group["eventos_periodo"]["contacto"]["eventos_observados"], 2)

    def test_colision_id_rechaza_ambas_versiones_independiente_orden(self):
        one = ev("uno", "recibido", "2026-09-20T10:00:00Z", "colision")
        two = ev("dos", "recibido", "2026-09-20T10:00:00Z", "colision")
        a, b = run([one, two], cobertura()), run([two, one], cobertura())
        self.assertEqual(a, b)
        self.assertEqual(a["incidencias"]["event_id_conflictivo"], 1)
        self.assertEqual(a["grupos"][0]["cohorte"]["recibidos_observados"], 0)
        self.assertEqual(a["grupos"][0]["cohorte"]["estado"], "desconocido")
        self.assertEqual(run([one, two, two], cobertura()), run([two, two, one], cobertura()))

    def test_join_exacto_no_mezcla_cliente_fuente(self):
        events = [ev("mismo", "recibido", "2026-09-20T10:00:00Z"),
                  ev("mismo", "venta", "2026-09-21T10:00:00Z", source="otro-origen"),
                  ev("mismo", "venta", "2026-09-21T10:00:00Z", cliente="otro-cliente")]
        result = run(events, cobertura())
        self.assertEqual(result["incidencias"]["lead_sin_recepcion"], 2)
        group = next(g for g in result["grupos"] if g["cliente_id"] == "fixture" and g["source"] == "formulario")
        self.assertEqual(group["cohorte"]["etapas"]["venta"]["valor"], 0)

    def test_cierre_antes_lead_y_futuro_no_cuentan(self):
        events = [ev("uno", "recibido", "2026-09-20T10:00:00Z"),
                  ev("uno", "venta", "2026-09-19T10:00:00Z"),
                  ev("uno", "contacto", "2026-10-04T10:00:00Z")]
        result = run(events, cobertura())
        self.assertEqual(result["incidencias"]["evento_antes_de_recepcion"], 1)
        self.assertEqual(result["incidencias"]["posterior_al_corte"], 1)
        stage = result["grupos"][0]["cohorte"]["etapas"]["venta"]
        self.assertEqual(stage["observados"], 0)
        self.assertIsNone(stage["valor"])

    def test_cualificado_requiere_criterio_venta_confirmacion(self):
        events = [ev("uno", "recibido", "2026-09-20T10:00:00Z"),
                  {**ev("uno", "cualificado", "2026-09-21T10:00:00Z"), "criterio_version": None},
                  {**ev("uno", "venta", "2026-09-22T10:00:00Z"), "confirmado": False}]
        result = run(events, cobertura())
        self.assertEqual(result["incidencias"]["cualificacion_sin_criterio_confirmado"], 1)
        self.assertEqual(result["incidencias"]["resultado_sin_confirmacion"], 1)
        self.assertIsNone(result["grupos"][0]["cohorte"]["etapas"]["cualificado"]["valor"])

    def test_cobertura_recepcion_no_acredita_venta_hasta_corte(self):
        events = [ev("uno", "recibido", "2026-09-20T10:00:00Z")]
        cov = cobertura(hasta=HASTA)
        stages = run(events, cov)["grupos"][0]["cohorte"]["etapas"]
        self.assertEqual(stages["recibido"]["valor"], 1)
        self.assertIsNone(stages["venta"]["valor"])
        cov.extend(cobertura(hasta=CORTE))
        self.assertEqual(run(events, cov)["grupos"][0]["cohorte"]["etapas"]["venta"]["valor"], 0)

    def test_fechas_timezone_y_recepcion_repetida(self):
        events = [ev("uno", "recibido", "2026-09-01T01:00:00+02:00"),
                  ev("dos", "recibido", "2026-09-01T02:00:00+02:00"),
                  ev("dos", "recibido", "2026-09-02T02:00:00+02:00", "recepcion-reintento")]
        r = run(events, cobertura())
        self.assertEqual(r["grupos"][0]["cohorte"]["recibidos_observados"], 1)
        self.assertEqual(r["incidencias"]["recepcion_repetida"], 1)
        with self.assertRaises(ValueError):
            calcular([], DESDE, HASTA, "2026-10-03T12:00:00")

    def test_puro_sin_pii_y_determinista_con_eventos_reordenados(self):
        events = [ev("PRIVATE-ID", "recibido", "2026-09-20T10:00:00Z"),
                  ev("PRIVATE-ID", "cualificado", "2026-09-21T10:00:00Z")]
        before = copy.deepcopy(events)
        with patch("builtins.open", side_effect=AssertionError("No IO")):
            first = run(events, cobertura())
            second = run(list(reversed(events)), cobertura())
        self.assertEqual(first, second)
        self.assertEqual(events, before)
        result = json.dumps(first)
        self.assertNotIn("PRIVATE-ID", result)
        self.assertNotIn("PII-NO-SALIDA", result)

    def test_cualificacion_versiones_distintas_no_ratio(self):
        events = [ev("uno", "recibido", "2026-09-20T10:00:00Z"), ev("dos", "recibido", "2026-09-20T10:00:00Z"),
                  ev("uno", "cualificado", "2026-09-21T10:00:00Z"),
                  {**ev("dos", "cualificado", "2026-09-21T10:00:00Z"), "criterio_version": "otra-politica-v2"}]
        group = run(events, cobertura())["grupos"][0]
        stage = group["cohorte"]["etapas"]["cualificado"]
        self.assertEqual(stage["observados"], 2)
        self.assertIsNone(stage["valor"])
        self.assertIsNone(stage["tasa_sobre_recibidos"])
        self.assertFalse(group["cualificacion"]["criterio_comparable"])
        events.pop()
        stage = run(events, cobertura())["grupos"][0]["cohorte"]["etapas"]["cualificado"]
        self.assertEqual(stage["tasa_sobre_recibidos"], 0.5)

    def test_huerfano_se_recupera_al_anadir_recepcion_real_y_no_alias(self):
        venta = ev("uno", "venta", "2026-09-21T10:00:00Z")
        inicial = run([venta], cobertura())
        self.assertEqual(inicial["incidencias"]["lead_sin_recepcion"], 1)
        self.assertEqual(inicial["grupos"][0]["cohorte"]["etapas"]["venta"]["observados"], 0)
        recibido = ev("uno", "recibido", "2026-09-20T10:00:00Z")
        recuperado = run([venta, recibido], cobertura())
        self.assertNotIn("lead_sin_recepcion", recuperado["incidencias"])
        self.assertEqual(recuperado["grupos"][0]["cohorte"]["etapas"]["venta"]["valor"], 1)
        recibido["source"] = "alias-formulario"
        separado = run([venta, recibido], cobertura())
        self.assertEqual(separado["incidencias"]["lead_sin_recepcion"], 1)

    def test_malformado_no_hace_completa_cobertura_ni_publica_url(self):
        events = [ev("uno", "recibido", "2026-09-20T10:00:00Z"),
                  ev("uno", "venta", "2026-09-21T10:00:00Z", source="https://host/?secret=TOKEN")]
        result = run(events, cobertura())
        self.assertIsNone(result["grupos"][0]["cohorte"]["etapas"]["venta"]["valor"])
        self.assertNotIn("TOKEN", json.dumps(result))

    def test_cobertura_dias_contiguos_sin_hueco_y_con_hueco(self):
        events = [ev("uno", "recibido", "2026-09-20T10:00:00Z")]
        cov = [{**cobertura()[0], "hasta": "2026-09-15"}, {**cobertura()[0], "desde": "2026-09-16"}]
        self.assertEqual(run(events, cov)["grupos"][0]["cohorte"]["estado"], "completo")
        cov[1]["desde"] = "2026-09-17"
        self.assertEqual(run(events, cov)["grupos"][0]["cohorte"]["estado"], "parcial")


if __name__ == "__main__":
    unittest.main()

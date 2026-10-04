"""Sólo tempfiles y fixtures; nunca DB real, proveedores ni datos de contactos."""
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor
from leads_archivo import ArchivoLeads, ArchivoError


CATALOGO = {
    "web-a": {"cliente_id": "cliente-a", "source": "wpforms:site-a", "etapas": ["recibido"], "actores": ["captura-a"], "privado_campos": ["formulario", "campo_fixture"]},
    "crm-a": {"cliente_id": "cliente-a", "source": "wpforms:site-a", "etapas": ["cualificado", "asistencia", "venta"], "actores": ["operador-a"], "criterios": ["ro-v1"]},
    "web-b": {"cliente_id": "cliente-b", "source": "wpforms:site-b", "etapas": ["recibido"], "actores": ["captura-b"]},
}


def evento(eid="evento-1"):
    return {"event_id": eid, "lead_id": "id-privado-fixture", "etapa": "recibido", "fecha": "2026-10-03T10:00:00+02:00"}


class Archivo(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "archivo.sqlite"
        self.a = ArchivoLeads(self.path, CATALOGO)

    def tearDown(self):
        self.tmp.cleanup()

    def test_idempotencia_conflicto_no_sobrescribe_y_reabre(self):
        raw = evento()
        first = self.a.ingestar("web-a", "captura-a", [raw])["resultados"][0]
        self.assertEqual(first["resultado"], "aceptado")
        raw["fecha"] = "2026-10-03T08:00:00Z"  # misma hora, distinta representación
        self.assertEqual(self.a.ingestar("web-a", "captura-a", [raw])["resultados"][0]["resultado"], "duplicado")
        raw["fecha"] = "2026-10-03T09:00:00Z"
        self.assertEqual(self.a.ingestar("web-a", "captura-a", [raw])["resultados"][0]["resultado"], "conflicto")
        reopened = ArchivoLeads(self.path, CATALOGO).exportar({"cliente-a"})
        self.assertEqual(len(reopened["eventos"]), 1)
        self.assertEqual(reopened["eventos"][0]["fecha"], "2026-10-03T08:00:00+00:00")
        self.assertEqual({r["resultado"] for r in reopened["recibos"]}, {"aceptado", "duplicado", "conflicto"})

    def test_catalogo_actor_identidad_y_tipo_no_payload_libre(self):
        with self.assertRaises(PermissionError):
            self.a.ingestar("web-a", "captura-b", [evento()])
        with self.assertRaises(PermissionError):
            self.a.ingestar("desconocida", "captura-a", [evento()])
        rows = self.a.ingestar("web-a", "captura-a", [{**evento(), "cliente_id": "cliente-b"}, {**evento(), "etapa": "venta", "confirmado": True}])["resultados"]
        self.assertEqual([r["resultado"] for r in rows], ["rechazado", "rechazado"])
        self.assertEqual(self.a.exportar({"cliente-a"})["eventos"], [])

    def test_criterios_confirmacion_timezone_lookup_code(self):
        raw = {**evento(), "etapa": "cualificado", "criterio_version": "inventado", "confirmado": True}
        self.assertEqual(self.a.ingestar("crm-a", "operador-a", [raw])["resultados"][0]["motivo"], "criterio_no_autorizado")
        raw.update(criterio_version="ro-v1", confirmado="true")
        self.assertEqual(self.a.ingestar("crm-a", "operador-a", [raw])["resultados"][0]["motivo"], "resultado_no_confirmado")
        raw.update(confirmado=True, fecha="2026-10-03T10:00:00")
        self.assertEqual(self.a.ingestar("crm-a", "operador-a", [raw])["resultados"][0]["resultado"], "rechazado")
        raw["fecha"] = "2026-10-03T10:00:00Z"
        self.assertEqual(self.a.ingestar("crm-a", "operador-a", [raw])["resultados"][0]["resultado"], "aceptado")

    def test_privado_allowlist_sin_secreto_y_exportacion_minima(self):
        raw = {**evento(), "meta_privados": {"formulario": "fixture-form", "campo_fixture": "Dato de prueba"}, "nombre_no_permitido": "NO-COPIAR"}
        self.a.ingestar("web-a", "captura-a", [raw])
        minimal = self.a.exportar({"cliente-a"})
        self.assertNotIn("meta_privados", minimal["eventos"][0])
        self.assertNotIn("NO-COPIAR", json.dumps(minimal))
        self.assertIn("meta_privados", self.a.exportar({"cliente-a"}, incluir_privados=True, clientes_privados_autorizados={"cliente-a"})["eventos"][0])
        bad = {**evento("evento-2"), "meta_privados": {"campo_fixture": {"api_key": "NUNCA-ARCHIVAR"}}}
        self.assertEqual(self.a.ingestar("web-a", "captura-a", [bad])["resultados"][0]["resultado"], "rechazado")
        bad["meta_privados"] = {"campo_fixture": "Bearer SECRET-NO-ARCHIVAR"}
        self.assertEqual(self.a.ingestar("web-a", "captura-a", [bad])["resultados"][0]["resultado"], "rechazado")
        self.assertNotIn("NUNCA-ARCHIVAR", json.dumps(self.a.exportar({"cliente-a"}, True, {"cliente-a"})))
        with self.assertRaises(PermissionError):
            self.a.exportar({"cliente-a"}, True)
        with self.assertRaises(PermissionError):
            self.a.exportar({"cliente-a"}, True, {"cliente-b"})

    def test_exportacion_recibos_aislada_cliente(self):
        self.a.ingestar("web-a", "captura-a", [evento()])
        self.a.ingestar("web-b", "captura-b", [evento()])
        export = self.a.exportar({"cliente-a"})
        self.assertEqual({e["cliente_id"] for e in export["eventos"]}, {"cliente-a"})
        self.assertEqual({e["cliente_id"] for e in export["recibos"]}, {"cliente-a"})
        self.assertEqual(self.a.exportar(set()), {"eventos": [], "recibos": []})
        with self.assertRaises(PermissionError):
            self.a.exportar("cliente-a")

    def test_fallo_segundo_evento_rollback_y_reintento(self):
        with sqlite3.connect(self.path) as c:
            c.execute("CREATE TRIGGER fixture_fallo BEFORE INSERT ON leads_eventos WHEN NEW.event_id='segundo' BEGIN SELECT RAISE(ABORT,'fallo fixture'); END")
        lote = [evento("primero"), evento("segundo")]
        with self.assertRaises(ArchivoError):
            self.a.ingestar("web-a", "captura-a", lote)
        self.assertEqual(self.a.exportar({"cliente-a"}), {"eventos": [], "recibos": []})
        with sqlite3.connect(self.path) as c:
            c.execute("DROP TRIGGER fixture_fallo")
        result = self.a.ingestar("web-a", "captura-a", lote)
        self.assertEqual([r["resultado"] for r in result["resultados"]], ["aceptado", "aceptado"])
        self.assertEqual([r["resultado"] for r in self.a.ingestar("web-a", "captura-a", lote)["resultados"]], ["duplicado", "duplicado"])

    def test_concurrencia_no_duplica_evento(self):
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: self.a.ingestar("web-a", "captura-a", [evento()]), range(2)))
        self.assertEqual(sorted(r["resultados"][0]["resultado"] for r in results), ["aceptado", "duplicado"])
        self.assertEqual(len(self.a.exportar({"cliente-a"})["eventos"]), 1)

    def test_commit_ack_perdido_no_miente_y_retry_deduplica(self):
        conn = self.a._conectar()
        class CommitSinAck:
            def __getattr__(self, name):
                return getattr(conn, name)
            def commit(self):
                conn.commit()
                raise sqlite3.OperationalError("fixture tras commit")
        with patch.object(self.a, "_conectar", return_value=CommitSinAck()):
            with self.assertRaises(ArchivoError):
                self.a.ingestar("web-a", "captura-a", [evento()])
        self.assertEqual(len(self.a.exportar({"cliente-a"})["eventos"]), 1)
        self.assertEqual(self.a.ingestar("web-a", "captura-a", [evento()])["resultados"][0]["resultado"], "duplicado")

    def test_archivo_borrado_no_se_recrea_silenciosamente(self):
        self.path.unlink()
        with self.assertRaises(ArchivoError):
            self.a.ingestar("web-a", "captura-a", [evento()])
        self.assertFalse(self.path.exists())

    def test_lote_rechazado_no_acepta_validos_y_conserva_recibos(self):
        result = self.a.ingestar("web-a", "captura-a", [evento("valido"), {**evento("invalido"), "fecha": "sin-fecha"}])
        self.assertFalse(result["lote_aceptado"])
        self.assertEqual([r["resultado"] for r in result["resultados"]], ["rechazado", "rechazado"])
        export = self.a.exportar({"cliente-a"})
        self.assertEqual(export["eventos"], [])
        self.assertEqual(len(export["recibos"]), 2)

    def test_replay_en_mismo_lote_y_colision_lote_no_acepta_primero(self):
        r = self.a.ingestar("web-a", "captura-a", [evento("replay"), evento("replay")])
        self.assertEqual([x["resultado"] for x in r["resultados"]], ["aceptado", "duplicado"])
        r = self.a.ingestar("web-a", "captura-a", [evento("colision"), {**evento("colision"), "fecha": "2026-10-04T10:00:00Z"}])
        self.assertFalse(r["lote_aceptado"])
        self.assertEqual([x["resultado"] for x in r["resultados"]], ["conflicto", "conflicto"])
        self.assertEqual([e["event_id"] for e in self.a.exportar({"cliente-a"})["eventos"]], ["replay"])

    def test_race_clientes_mismo_id_queda_aislado(self):
        def ingest(nombre):
            return self.a.ingestar("web-" + nombre, "captura-" + nombre, [evento()])
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(ingest, ("a", "b")))
        self.assertEqual([r["resultados"][0]["resultado"] for r in results], ["aceptado", "aceptado"])
        self.assertEqual(len(self.a.exportar({"cliente-a"})["eventos"]), 1)
        self.assertEqual(len(self.a.exportar({"cliente-b"})["eventos"]), 1)

    def test_carpeta_privada_nueva_y_no_chmod_preexistente(self):
        private = Path(self.tmp.name) / "nuevo" / "archivo.sqlite"
        ArchivoLeads(private, CATALOGO)
        self.assertEqual(os.stat(private.parent).st_mode & 0o777, 0o700)
        public = Path(self.tmp.name) / "existente"
        public.mkdir(mode=0o755)
        public.chmod(0o755)
        with self.assertRaises(ValueError):
            ArchivoLeads(public / "archivo.sqlite", CATALOGO)
        self.assertEqual(os.stat(public).st_mode & 0o777, 0o755)
        self.assertFalse((public / "archivo.sqlite").exists())

    def test_backup_restore_integrity_and_retry_smoke(self):
        self.a.ingestar("web-a", "captura-a", [evento()])
        backup = Path(self.tmp.name) / "respaldo.sqlite"
        self.assertTrue(self.a.respaldar(backup)["verificado"])
        restored = ArchivoLeads(backup, CATALOGO)
        self.assertEqual(restored.exportar({"cliente-a"}), self.a.exportar({"cliente-a"}))
        self.assertEqual(restored.ingestar("web-a", "captura-a", [evento()])["resultados"][0]["resultado"], "duplicado")
        self.assertEqual(os.stat(self.path).st_mode & 0o777, 0o600)
        self.assertEqual(os.stat(backup).st_mode & 0o777, 0o600)
        with self.assertRaises(ValueError):
            self.a.respaldar(backup)

    def test_no_usa_bd_otra_app_y_limites(self):
        other = Path(self.tmp.name) / "revision.sqlite"
        with sqlite3.connect(other) as c:
            c.execute("CREATE TABLE acciones (id INTEGER)")
        with self.assertRaises(ValueError):
            ArchivoLeads(other, CATALOGO)
        with sqlite3.connect(other) as c:
            self.assertEqual([r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")], ["acciones"])
        with self.assertRaises(ValueError):
            self.a.ingestar("web-a", "captura-a", [evento()] * 201)
        big = {**evento(), "meta_privados": {"campo_fixture": "x" * 33000}}
        self.assertEqual(self.a.ingestar("web-a", "captura-a", [big])["resultados"][0]["motivo"], "evento_demasiado_grande")


if __name__ == "__main__":
    unittest.main()

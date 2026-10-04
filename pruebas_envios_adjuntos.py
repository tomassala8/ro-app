"""Regresión: un descriptor de PDF nunca debe salir como correo sin adjunto."""
import json
import sqlite3
import unittest

import envios


class AdjuntosPendientes(unittest.TestCase):
    def test_descriptor_y_correo_normal(self):
        self.assertTrue(envios.adjunto_no_soportado({"herramienta": "desk", "objeto": "RO-123", "vista_previa": {"adjunto": {"tipo": "pdf"}}}))
        self.assertTrue(envios.adjunto_no_soportado({"herramienta": "desk", "objeto": "informe/cliente/2026-09"}))
        self.assertFalse(envios.adjunto_no_soportado({"herramienta": "desk", "objeto": "RO-123", "vista_previa": {"asunto": "Hola"}}))

    def test_cola_heredada_no_contacta_proveedor(self):
        con = sqlite3.connect(":memory:")
        con.row_factory = sqlite3.Row
        self.addCleanup(con.close)
        con.execute("CREATE TABLE acciones (id INTEGER PRIMARY KEY, herramienta TEXT, objeto TEXT, vista_previa TEXT)")
        con.execute("INSERT INTO acciones VALUES (1,?,?,?)", ("desk", "RO-123", json.dumps({"adjunto": {"tipo": "pdf"}})))
        envios.preparar(con)
        eid, _ = envios.crear_envio(con, clave="adjunto-prueba", quien="tomas", canal="desk", tipo="correo", objeto="RO-123", accion_id=1, modo="real", destinatario={"resuelto": True}, texto="PDF adjunto")

        class Proveedor:
            def buscar(self, envio):
                raise AssertionError("No se debe contactar al proveedor")

            def enviar(self, envio):
                raise AssertionError("No se debe enviar")

        self.assertEqual(envios.ejecutar(con, eid, Proveedor()), "fallido")
        self.assertEqual(envios.estado_actual(con, eid)["evento"], "adjunto_pendiente")


if __name__ == "__main__":
    unittest.main()

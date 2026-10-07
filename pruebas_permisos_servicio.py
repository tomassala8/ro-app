#!/usr/bin/env python3
"""Pruebas puras de servicio contratado, cartera account y paridad. Sin red/servidor/base."""
import ast
import json
import os
import re
import types
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import permisos as P

AQUI = Path(__file__).resolve().parent


def fixture():
    clientes = [
        {"id": "si", "nombre": "Cliente contratado", "servicios": {"seo": "sí", "publicidad": "sí", "crm_ghl": "sí", "web": "sí", "redes": "sí", "outreach": "sí"}},
        {"id": "no", "nombre": "Cliente sin servicio", "servicios": {"seo": "no", "publicidad": "no", "crm_ghl": "no", "web": "no", "redes": "no", "outreach": "no"}},
        {"id": "previsto", "nombre": "Cliente previsto", "servicios": {"seo": "posible", "publicidad": "prevista", "web": "prevista", "redes": "posible"}},
        {"id": "incierto", "nombre": "Cliente por confirmar", "servicios": {}},
        {"id": "mant", "nombre": "Solo mantenimiento", "servicios": {"mantenimiento": "sí"}},
    ]
    return {"clientes": clientes, "personas": [], "asignaciones": [], "logos": {},
            "alarmas": [{"id": "a", "ambito": "cliente", "cliente_id": "no", "cliente": "Cliente sin servicio", "gravedad": "rojo"}],
            "meta": {"generado": "2026-10-03", "resumen": {"clientes_activos": 5}, "nombres": ["Cliente sin servicio"],
                     "fuentes": [{"fuente": "Prueba", "estado": "ok", "clientes_ajenos": ["no"]}]}}


def persona(roles):
    return {"id": "persona_prueba", "nombre": "Prueba", "puestos": roles}


def asignar(raw, p, silla):
    raw["personas"] = [p]
    raw["asignaciones"] = [{"persona_id": p["id"], "cliente_id": c["id"], "silla": silla} for c in raw["clientes"]]


def recortador_puro(raw):
    """Carga solo definiciones del recorte de servir.py: no arranque, base, red ni archivos de datos."""
    arbol = ast.parse((AQUI / "servir.py").read_text())
    funciones = {"ClaveValor", "_es_num", "_quita", "serie_sin_gasto", "_serie_de_meta", "quitar_para", "sin_cuota",
                 "recortar_modulo", "clientes_ajenos", "cliente_de_fila", "recorte_vacio", "recorte_por_silla", "_rama_sin_importes"}
    constantes = {"CLAVES_CUOTA", "CLAVES_DERIVADAS_CUOTA", "CONSUMIDAS", "CLAVES_HORAS_PAUTADAS", "CLAVES_COBROS",
                  "CLAVES_INVERSION", "CLAVES_LEAD", "DINERO_CUOTA_VALOR", "DINERO_INVERSION_VALOR", "SERIES_CON_GASTO",
                  "CLAVES_RENTABILIDAD", "CLAVES_ENLACE", "CLAVES_FILA_LEAD"}
    nodos = [n for n in arbol.body if (isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name in funciones)
             or (isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id in constantes for t in n.targets))]
    ns = {"re": re, "P": P, "E": types.SimpleNamespace(crudo=raw)}
    exec(compile(ast.Module(body=nodos, type_ignores=[]), "recorte_puro", "exec"), ns)
    return ns["recortar_modulo"]


class PermisosServicio(unittest.TestCase):
    def test_servicio_no_y_desconocido_no_salen_ni_abren(self):
        for rol, silla in [("seo", "seo"), ("trafficker", "trafficker"), ("especialista_ghl", "crm"), ("outreach", "outreach")]:
            with self.subTest(rol=rol):
                raw, p = fixture(), persona([rol]); asignar(raw, p, silla)
                out, cp = P.recortar(p, raw), P.contexto(p, raw)
                self.assertEqual([c["id"] for c in out["clientes"]], ["si"])
                self.assertEqual(out["alarmas"], [])
                self.assertEqual({a["cliente_id"] for a in out["asignaciones"]}, {"si"})
                for cid in ("no", "previsto", "incierto"):
                    self.assertFalse(P.ver(p, {"tipo": "cliente_detalle", "cliente_id": cid}, cp)["ok"])

    def test_transversales_contrato_sin_asignacion_y_mantenimiento(self):
        for rol, ids in [("web", {"si", "mant"}), ("redes", {"si"})]:
            raw, p = fixture(), persona([rol]); raw["personas"] = [p]
            self.assertEqual(P.contexto(p, raw)["cartera_ids"], ids)
            self.assertEqual({c["id"] for c in P.recortar(p, raw)["clientes"]}, ids)

    def test_jefaturas_servicio_y_direccion_ops_amplias(self):
        for rol in ("jefa_seo", "jefa_publicidad", "jefa_crm"):
            raw, p = fixture(), persona([rol]); raw["personas"] = [p]
            self.assertEqual({c["id"] for c in P.recortar(p, raw)["clientes"]}, {"si"})
            self.assertTrue(P.ver(p, {"tipo": "cliente_detalle", "cliente_id": "si"}, P.contexto(p, raw))["ok"])
        for rol in ("direccion", "operaciones", "proyectos", "tecnico_altas"):
            raw, p = fixture(), persona([rol]); raw["personas"] = [p]
            self.assertEqual(len(P.recortar(p, raw)["clientes"]), 5)
            self.assertTrue(P.ver(p, {"tipo": "cliente_detalle", "cliente_id": "no"}, P.contexto(p, raw))["ok"])

    def test_account_cliente_sin_servicio_y_meta_frescura(self):
        raw, p = fixture(), persona(["account"]); raw["personas"] = [p]
        raw["asignaciones"] = [{"persona_id": p["id"], "cliente_id": "no", "silla": "account"}]
        out = P.recortar(p, raw)
        self.assertEqual([c["id"] for c in out["clientes"]], ["no"])
        self.assertEqual(out["meta"], {"generado": "2026-10-03", "fuentes": [{"fuente": "Prueba", "estado": "ok"}]})
        self.assertNotIn("cuota", out["clientes"][0])

    def test_asignacion_caducada_y_suplencia_invalida(self):
        raw, p = fixture(), persona(["seo"]); raw["personas"] = [p]
        for extra in ({"hasta": "2026-10-01"}, {"desde": "2026-10-04"}, {"suplencia": True}):
            raw["asignaciones"] = [{"persona_id": p["id"], "cliente_id": "si", "silla": "seo", **extra}]
            self.assertEqual(P.cartera(p, raw["asignaciones"], "2026-10-03", raw["clientes"]), set())

    def test_ver_como_interseccion_de_scope(self):
        raw = fixture(); real, visto = persona(["account"]), {**persona(["jefa_seo"]), "id": "jefa"}
        raw["personas"] = [real, visto]
        raw["asignaciones"] = [{"persona_id": real["id"], "cliente_id": "no", "silla": "account"}]
        with P.mirando_como(real, raw):
            self.assertFalse(P.ver(visto, {"tipo": "cliente_detalle", "cliente_id": "si"}, P.contexto(visto, raw))["ok"])

    def test_datos_locales_solo_contrato_explicito(self):
        clientes = json.loads((AQUI / "data/clientes.json").read_text())
        asignaciones = json.loads((AQUI / "data/asignaciones.json").read_text())
        personas = json.loads((AQUI / "data/personas.json").read_text())
        for p in personas:
            if not P.solo_su_cartera(p):
                continue
            por = P.cartera_por_silla(p, asignaciones, clientes=clientes)
            for silla, ids in por.items():
                claves = P.SERVICIOS_SILLA.get(silla) or P.SERVICIOS_JEFATURA.get(silla.removeprefix("servicio_"))
                if claves:
                    self.assertTrue(all(P.servicio_contratado(c, claves) for c in clientes if c["id"] in ids))

    def test_contexto_sin_catalogo_falla_cerrado_sin_romper_account(self):
        raw = fixture()
        for rol, silla in [("seo", "seo"), ("web", "web"), ("jefa_seo", "seo")]:
            p = persona([rol]); asignar(raw, p, silla)
            for catalogo in ({}, {"clientes": None}, {"clientes": []}):
                cp = P.contexto(p, {"personas": [p], "asignaciones": raw["asignaciones"], **catalogo})
                self.assertEqual(cp["cartera_ids"], set())
                self.assertEqual(cp["clientes_por_id"], {})
                self.assertFalse(P.ver(p, {"tipo": "cliente_detalle", "cliente_id": "si"}, cp)["ok"])
        p = persona(["account"]); asignar(raw, p, "account")
        cp = P.contexto(p, {"personas": [p], "asignaciones": raw["asignaciones"]})
        self.assertEqual(cp["cartera_ids"], {c["id"] for c in raw["clientes"]})

    def test_account_importes_numericos_fuera_horas_dentro(self):
        raw, p = fixture(), persona(["account"]); asignar(raw, p, "account")
        fila = {"cliente_id": "si", "cuota": 500, "importe": 600, "importe_total": 700, "importe_mensual": 800,
                "facturado": 900, "facturado_mes": 1000, "facturado_holded": 1100, "facturado_panel": 1200,
                "gasto": 25, "gasto_meta": 25, "coste_horas": {"consumidas": 8},
                "cuota_horas": {"pautadas": 15, "consumidas": 8, "cuota": 500},
                "horas_pautadas": 15, "consumidas": 8, "leads": 2,
                "detalle": {"importe_pagado": 42, "facturado_cierre": 500, "texto": "Cuota 500 euros"}}
        salida = recortador_puro(raw)(p, P.contexto(p, raw), {"filas": [fila]}, "suyo")["filas"][0]
        for clave in ("cuota", "importe", "importe_total", "importe_mensual", "facturado", "facturado_mes", "facturado_holded", "facturado_panel", "gasto", "gasto_meta"):
            self.assertNotIn(clave, salida)
        self.assertEqual(salida["cuota_horas"], {"pautadas": 15, "consumidas": 8})
        self.assertEqual(salida["coste_horas"], {"consumidas": 8})
        self.assertEqual((salida["horas_pautadas"], salida["consumidas"], salida["leads"]), (15, 8, 2))
        self.assertNotIn("importe_pagado", salida["detalle"])
        self.assertNotIn("facturado_cierre", salida["detalle"])
        self.assertNotIn("500", salida["detalle"]["texto"])

    def test_paid_gasto_autorizado_dentro_facturacion_fuera(self):
        raw, p = fixture(), persona(["trafficker"]); asignar(raw, p, "trafficker")
        fila = {"cliente_id": "si", "cuota": 500, "importe": 600, "facturado_holded": 700,
                "gasto": 25, "gasto_meta": 25, "cpl": 12.5, "leads": 2, "texto": "Gasto en Meta: 25 euros"}
        salida = recortador_puro(raw)(p, P.contexto(p, raw), {"filas": [fila]}, "suyo")["filas"][0]
        self.assertEqual((salida["gasto"], salida["gasto_meta"], salida["cpl"], salida["leads"]), (25, 25, 12.5, 2))
        self.assertIn("25", salida["texto"])
        for clave in ("cuota", "importe", "facturado_holded"):
            self.assertNotIn(clave, salida)
        direccion = persona(["direccion"])
        salida_direccion = recortador_puro(raw)(direccion, P.contexto(direccion, raw), {"filas": [fila]}, "todo")["filas"][0]
        self.assertEqual((salida_direccion["cuota"], salida_direccion["importe"], salida_direccion["facturado_holded"]), (500, 600, 700))

    def test_paridad_js_python_scope_y_sesion(self):
        node = os.environ.get("RO_NODE") or shutil.which("node")
        if not node:
            candidato = Path.home() / ".cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node"
            node = str(candidato) if candidato.exists() else None
        if not node:
            self.skipTest("Node no disponible; paridad JS pendiente")
        raw = fixture()
        casos = []
        for rol, silla in [("account", "account"), ("seo", "seo"), ("trafficker", "trafficker"), ("web", "web"), ("redes", "redes"), ("jefa_seo", "seo"), ("jefa_publicidad", "trafficker"), ("operaciones", "account")]:
            p = persona([rol]); asignar(raw, p, silla)
            out = P.recortar(p, raw)
            casos.append({"persona": p, "crudo": json.loads(json.dumps(raw)), "esperado": {"cartera": sorted(out["carteraIds"]), "clientes": sorted(c["id"] for c in out["clientes"]), "alarmas": [a["id"] for a in out["alarmas"]], "meta": out["meta"]}})
        with tempfile.TemporaryDirectory(prefix="ro_scope_") as tmp:
            tmp = Path(tmp)
            js = (AQUI / "permisos.js").read_text().replace("import REGLAS from './reglas_permisos.json' with { type: 'json' };", "const REGLAS = " + json.dumps(P.REGLAS) + ";")
            (tmp / "permisos.mjs").write_text(js)
            datos = (AQUI / "datos.js").read_text().replace("from './permisos.js'", "from './permisos.mjs'")
            (tmp / "datos.mjs").write_text(datos)
            (tmp / "casos.json").write_text(json.dumps(casos))
            (tmp / "prueba.mjs").write_text("""import fs from 'node:fs';
import assert from 'node:assert/strict';
import {recortar} from './datos.mjs';
for (const c of JSON.parse(fs.readFileSync(new URL('./casos.json', import.meta.url)))) {
 const d=recortar(c.persona,c.crudo);
 assert.deepEqual({cartera:[...d.carteraIds].sort(),clientes:d.clientes.map(x=>x.id).sort(),alarmas:d.alarmas.map(x=>x.id),meta:d.meta}, c.esperado);
}
""")
            res = subprocess.run([node, str(tmp / "prueba.mjs")], capture_output=True, text=True, timeout=30)
            self.assertEqual(res.returncode, 0, res.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)

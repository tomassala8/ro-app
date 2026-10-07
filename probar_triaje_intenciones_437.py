"""437 HTTP real loopback + hook real + política actual + SQLite privada; ningún proveedor."""
import ast
import copy
import hashlib
import json
import os
import sqlite3
import tempfile
import threading
import types
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from unittest.mock import patch
import permisos as P
import piloto_lectura as PILOTO
import triaje_intenciones_437 as T
from intenciones_acciones import guardar

ROOT = Path(__file__).parent
UUID = 'de848a14-06a2-47f3-862a-a7ae245ca4d1'

class Pruebas(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.base.chmod(0o700)
        self.db = self.base / 'qa.db'
        self.data = self.base / 'data'
        self.source = self.data / 'bandeja/bandeja.json'
        self.source.parent.mkdir(parents=True)
        self.doc = {'triaje': [{'id': 'ticket1', 'numero': 'RO123', 'cliente_id': 'cliente1', 'propuesta': 'seguro',
                              'agente_propuesto_id': 'account', 'fecha': '2026-10-03',
                              'asunto': 'NO_EXPORTAR_ASUNTO', 'motivo': 'NO_EXPORTAR_CONTACTO'}], 'correos': []}
        self.persist()
        cat = {'personas': [{'id': x, 'estado': 'activo', 'puestos': [rol]} for x, rol in
                           [('ops', 'operaciones'), ('account', 'account'), ('ajeno', 'account'), ('paid', 'trafficker')]],
               'clientes': [{'id': 'cliente1', 'activo_confirmado': True}, {'id': 'cliente2', 'activo_confirmado': True}],
               'asignaciones': [{'persona_id': 'account', 'cliente_id': 'cliente1', 'silla': 'account'},
                                {'persona_id': 'ajeno', 'cliente_id': 'cliente2', 'silla': 'account'}]}
        self.activos = {'cliente1', 'cliente2'}
        self.S = types.SimpleNamespace(E=types.SimpleNamespace(crudo=cat, nucleo_bloqueado=False,
                                   modulos=P.cargar_modulos()), P=P,
                                   ACT=types.SimpleNamespace(es_activo_id=lambda cid: cid in self.activos),
                                   DB=self.db, DATA=self.data)
        # Función ve_alguno de servir.py, no bool mock ni reimplementación de su contrato.
        tree = ast.parse((ROOT / 'servir.py').read_text())
        fun = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 've_alguno')
        ns = {'P': P, 'E': self.S.E}
        exec(compile(ast.Module(body=[fun], type_ignores=[]), 'servir.py', 'exec'), ns)
        self.S.ve_alguno = ns['ve_alguno']
        with sqlite3.connect(self.db) as c:
            c.executescript((ROOT / 'schema_v2.sql').read_text())
        self.db.chmod(0o600)
        S = self.S
        class H(BaseHTTPRequestHandler):
            def log_message(self, *a): pass
            def responder(self, code, dto):
                raw = json.dumps(dto).encode()
                self.send_response(code); self.send_header('Content-Type', 'application/json')
                self.send_header('Cache-Control', 'no-store'); self.end_headers(); self.wfile.write(raw)
            def _api_get(self, ruta, q, real, persona): return self.responder(404, {'error': 'No disponible'})
            def api_post(self, ruta, real, persona, cuerpo): return self.responder(403, {'error': 'QA sin escrituras HTTP'})
            def do_GET(self):
                u = urlparse(self.path)
                rid = self.headers.get('X-RO-Yo', '')
                vid = self.headers.get('X-RO-Como') or rid
                self._api_get(u.path, parse_qs(u.query, keep_blank_values=True), {'id': rid}, {'id': vid})
            def do_POST(self):
                rid = self.headers.get('X-RO-Yo', '')
                self.api_post(urlparse(self.path).path, {'id': rid}, {'id': rid}, {})
        T.enganchar(H, S)
        PILOTO.enganchar(H)
        self.http = ThreadingHTTPServer(('127.0.0.1', 0), H)
        self.thread = threading.Thread(target=self.http.serve_forever, daemon=True)
        self.thread.start()
        self.url = 'http://127.0.0.1:' + str(self.http.server_port)
        self.env = patch.dict(os.environ, {'DATABASE_URL': '', 'RO_PILOTO_LECTURA': ''})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.http.shutdown(); self.http.server_close(); self.thread.join()
        self.tmp.cleanup()

    def persist(self):
        self.source.write_text(json.dumps(self.doc))
        self.source.chmod(0o600)

    def req(self, actor='ops', como=None, query='ticket_id=ticket1&cliente_id=cliente1', method='GET'):
        headers = {'X-RO-Yo': actor, 'X-RO-App': '1'}
        if como: headers['X-RO-Como'] = como
        request = Request(self.url + T.RUTA + '?' + query, headers=headers, method=method)
        try:
            with urlopen(request, timeout=5) as f: return f.status, json.load(f), f.headers
        except HTTPError as e: return e.code, json.load(e), e.headers

    def action(self, actor='ops', tipo='asignar', cid='cliente1', obj='RO123', intent=False):
        body = {'intencion_id': UUID, 'modulo': 'bandeja', 'herramienta': 'desk', 'tipo': tipo,
                'objeto': obj, 'cliente_id': cid, 'texto': 'NO_EXPORTAR_NOTA', 'vista_previa': {'secreto': 'NO_EXPORTAR_PREVIA'}}
        with sqlite3.connect(self.db) as c:
            c.execute('BEGIN IMMEDIATE')
            def insertar(c):
                return c.execute("INSERT INTO acciones(quien,herramienta,tipo,objeto,cliente_id,modulo,texto,vista_previa,estado) VALUES (?,?,?,?,?,?,?,?,?)",
                                 (actor, 'desk', tipo, obj, cid, 'bandeja', body['texto'], json.dumps(body['vista_previa']), 'simulada')).lastrowid
            return guardar(c, actor, body, insertar)[0] if intent else insertar(c)

    def test_501_fuera_limite_y_recibo_uuid_real(self):
        aid = self.action(intent=True)
        for n in range(501): self.action(obj='otro' + str(n))
        code, d, headers = self.req()
        self.assertEqual(code, 200); self.assertEqual(headers['Cache-Control'], 'no-store')
        self.assertEqual(d['version'], '437.1'); self.assertEqual(d['objeto'], 'RO123')
        self.assertEqual(d['tipos']['asignar']['cantidad'], 1)
        self.assertEqual(d['tipos']['asignar']['ultima']['accion_id'], aid)
        self.assertEqual(d['tipos']['asignar']['ultima']['intencion_id'], UUID)
        self.assertEqual(d['tipos']['cerrar'], {'cantidad': 0, 'ultima': None})
        self.assertFalse(d['confirmacion_desk'])
        raw = json.dumps(d)
        for token in ('NO_EXPORTAR', 'secreto', 'vista_previa', 'asunto', 'motivo', 'quien', 'agente_propuesto_id'):
            self.assertNotIn(token, raw)

    def test_cero_exacto_no_es_ausencia_proveedor(self):
        code, d, _ = self.req()
        self.assertEqual(code, 200)
        self.assertTrue(d['lectura_exacta']); self.assertFalse(d['confirmacion_desk'])
        self.assertEqual(d['tipos']['asignar'], {'cantidad': 0, 'ultima': None})

    def test_legacy_otro_usuario_sin_uuid_y_propia_false(self):
        self.action(actor='account')
        code, d, _ = self.req()
        self.assertEqual(code, 200)
        self.assertIsNone(d['tipos']['asignar']['ultima']['intencion_id'])
        self.assertFalse(d['tipos']['asignar']['ultima']['propia'])

    def test_vercomo_interseccion_no_exporta_uuid(self):
        self.action(actor='account', intent=True)
        code, d, _ = self.req(como='account')
        self.assertEqual(code, 200)
        self.assertIsNone(d['tipos']['asignar']['ultima']['intencion_id'])
        self.assertFalse(d['tipos']['asignar']['ultima']['propia'])
        self.assertEqual(self.req(actor='account', como='ops')[0], 403)
        self.assertEqual(self.req(actor='ajeno')[0], 403)
        self.assertEqual(self.req(como='ajeno')[0], 403)

    def test_piloto_get_sin_mutar_post_bloqueado(self):
        before = hashlib.sha256(self.db.read_bytes()).hexdigest()
        with patch.dict(os.environ, {'RO_PILOTO_LECTURA': '1'}):
            self.assertEqual(self.req()[0], 200)
            self.assertEqual(self.req(method='POST')[0], 403)
        self.assertEqual(before, hashlib.sha256(self.db.read_bytes()).hexdigest())

    def test_query_ids_y_campos_malformados(self):
        for q in ('ticket_id=ticket1', 'ticket_id=ticket1&cliente_id=cliente1&tipo=cerrar',
                  'ticket_id=ticket1&ticket_id=ticket1&cliente_id=cliente1',
                  'ticket_id=../x&cliente_id=cliente1', 'ticket_id=&cliente_id=cliente1'):
            self.assertEqual(self.req(query=q)[0], 400)

    def test_referencia_inexistente_ajena_y_client_spoof(self):
        self.assertEqual(self.req(query='ticket_id=no_existe&cliente_id=cliente1')[0], 404)
        self.assertEqual(self.req(query='ticket_id=ticket1&cliente_id=cliente2')[0], 404)

    def test_persona_baja_duplicada_roles_y_grant(self):
        original = copy.deepcopy(self.S.E.crudo)
        for modify in (lambda: self.S.E.crudo['personas'][0].update(estado='baja'),
                       lambda: self.S.E.crudo['personas'].append(copy.deepcopy(self.S.E.crudo['personas'][0])),
                       lambda: self.S.E.crudo['personas'][0].update(puestos=['operaciones', 'operaciones']),
                       lambda: self.S.E.modulos.update(bandeja={})):
            self.S.E.crudo = copy.deepcopy(original); self.S.E.modulos = P.cargar_modulos(); modify()
            self.assertEqual(self.req()[0], 403)

    def test_act_y_cliente_duplicados_denegados(self):
        self.activos.remove('cliente1'); self.assertEqual(self.req()[0], 403)
        self.activos.add('cliente1'); self.S.E.crudo['clientes'].append(copy.deepcopy(self.S.E.crudo['clientes'][0]))
        self.assertEqual(self.req()[0], 403)

    def test_revocacion_durante_ledger_y_ultimo_io(self):
        original = T._ledger
        def revoke(*a):
            result = original(*a); self.activos.remove('cliente1'); return result
        with patch.object(T, '_ledger', revoke): self.assertEqual(self.req()[0], 403)
        self.activos.add('cliente1')
        original_ticket = T._ticket; calls = [0]
        def last(*a):
            result = original_ticket(*a); calls[0] += 1
            if calls[0] == 2: self.S.E.crudo['personas'][0]['estado'] = 'baja'
            return result
        with patch.object(T, '_ticket', last): self.assertEqual(self.req()[0], 403)

    def test_fuente_cambiada_en_lectura(self):
        original = T._ledger
        def change(*a):
            result = original(*a); self.doc['triaje'][0]['fecha'] = '2026-10-04'; self.persist(); return result
        with patch.object(T, '_ledger', change): self.assertEqual(self.req()[0], 403)

    def test_conflicto_null_u_otro_cliente_nunca_cero(self):
        for cid in (None, 'cliente2'):
            self.action(cid=cid)
            code, d, _ = self.req(); self.assertEqual(code, 503); self.assertNotIn('tipos', d)

    def test_base_ausente_y_tabla_ausente_no_crean(self):
        self.db.unlink(); self.assertEqual(self.req()[0], 503); self.assertFalse(self.db.exists())
        with sqlite3.connect(self.db) as c: c.execute('CREATE TABLE otra(id)')
        self.assertEqual(self.req()[0], 503)

    def test_postgres_sin_validar_no_silent_zero(self):
        with patch.dict(os.environ, {'DATABASE_URL': 'fixture-no-conexion'}): self.assertEqual(self.req()[0], 503)

    def test_fuente_duplicada_json_y_float_no_finito(self):
        self.source.write_text('{"triaje":[],"triaje":[]}'); self.assertEqual(self.req()[0], 503)
        self.source.write_text('{"triaje":[],"x":1e999}'); self.assertEqual(self.req()[0], 503)

    def test_ticket_numero_duplicado_y_correo_conflictivo(self):
        self.doc['triaje'].append({**self.doc['triaje'][0], 'id': 'ticket2'}); self.persist()
        self.assertEqual(self.req()[0], 503)
        self.doc['triaje'] = self.doc['triaje'][:1]; self.doc['correos'] = [{'id': 'other', 'numero': 'RO123', 'cliente_id': 'cliente2'}]; self.persist()
        self.assertEqual(self.req()[0], 503)

    def test_fifo_y_symlink_fuente_no_bloquean(self):
        original = self.source.read_bytes(); self.source.unlink(); os.mkfifo(self.source)
        self.assertEqual(self.req()[0], 503)
        self.source.unlink(); target = self.base/'otra.json'; target.write_bytes(original); self.source.symlink_to(target)
        self.assertEqual(self.req()[0], 503)

    def test_uuid_ledger_incoherente_fecha_imposible(self):
        aid = self.action(intent=True)
        with sqlite3.connect(self.db) as c: c.execute('UPDATE intenciones_acciones SET actor=? WHERE accion_id=?', ('ajeno', aid))
        self.assertEqual(self.req()[0], 503)

    def test_solo_lectura_http_no_tablas_uuid_replays(self):
        aid = self.action(intent=True); self.assertEqual(self.action(intent=True), aid)
        before = hashlib.sha256(self.db.read_bytes()).hexdigest()
        self.assertEqual(self.req(actor='account')[0], 200)
        self.assertEqual(self.req()[0], 200)
        self.assertEqual(before, hashlib.sha256(self.db.read_bytes()).hexdigest())

    def test_alias_id_legacy_count_sin_uuid_replay_normalizado(self):
        self.action(obj='ticket1', intent=True)
        code, d, _ = self.req()
        self.assertEqual(code, 200)
        self.assertEqual(d['tipos']['asignar']['cantidad'], 1)
        self.assertEqual(d['objeto'], 'RO123')
        self.assertIsNone(d['tipos']['asignar']['ultima']['intencion_id'])

    def test_alias_numero_colision_no_acredita_historia(self):
        self.doc['triaje'].append({'id': 'RO123', 'numero': 'other', 'cliente_id': 'cliente2'})
        self.persist()
        self.assertEqual(self.req()[0], 503)

    def test_catalogo_de_cartera_malformado_error_controlado(self):
        self.S.E.crudo['asignaciones'] = [{'persona_id': 'account'}]
        self.assertEqual(self.req(actor='account')[0], 503)

    def test_ambito_revocado_aunque_no_haya_historia(self):
        original = T._ledger
        def change(*a):
            result = original(*a); self.S.E.modulos['bandeja'] = {}; return result
        with patch.object(T, '_ledger', change): self.assertEqual(self.req()[0], 403)

    def test_fecha_ledger_imposible_no_emitir_metadata(self):
        aid = self.action()
        with sqlite3.connect(self.db) as c: c.execute('UPDATE acciones SET creada=? WHERE id=?', ('2026-02-31 24:10:00', aid))
        self.assertEqual(self.req()[0], 503)

    def test_dos_vinculos_uuid_una_accion_incoherentes(self):
        aid = self.action(intent=True)
        with sqlite3.connect(self.db) as c:
            c.execute('INSERT INTO intenciones_acciones(actor,intencion,huella,accion_id) VALUES (?,?,?,?)',
                      ('ajeno', 'fa4e6029-0c72-4ce0-a70c-7c2539a30c21', 'fake-fixture', aid))
        self.assertEqual(self.req()[0], 503)

    def test_db_enlace_no_se_abre(self):
        old = self.db.with_name('old.db'); self.db.rename(old); self.db.symlink_to(old)
        self.assertEqual(self.req()[0], 503)

    def test_datos_api_no_memoria_para_preflight(self):
        import subprocess
        node = '/Users/tomassala/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node'
        code = r"""const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');const s=fs.readFileSync('datos.js','utf8');const lines=s.split('\n').filter(l=>/^const (RUTAS_CON_MEMORIA|NUNCA_GUARDAR) =|^export const conMemoria =/.test(l)).join('\n').replace('export ','');const e={};vm.createContext(e);vm.runInContext(lines+';globalThis.test=conMemoria;',e);assert.equal(e.test('bandeja/triaje-intenciones?ticket_id=ticket1&cliente_id=cliente1'),false);assert.equal(e.test('acciones?modulo=bandeja'),true);"""
        subprocess.run([node, '-e', code], cwd=ROOT, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def par_productor(self):
        t = self.doc['triaje'][0]
        t.update(id='g-RO123', url='https://desk.zoho.eu/agent/qa/tickets/details/123', departamento='QA')
        self.doc['correos'] = [{'id': 't-RO123', 'numero': 'RO123', 'cliente_id': 'cliente1',
                               'url': t['url'], 'departamento': 'QA', 'asunto': 'NO_EXPORTAR_CORREO'}]
        self.persist()
        return 'ticket_id=g-RO123&cliente_id=cliente1'

    def test_par_real_productor_mismo_cliente_no_colision(self):
        query = self.par_productor()
        code, d, _ = self.req(query=query)
        self.assertEqual(code, 200)
        self.assertEqual(d['ticket_id'], 'g-RO123')
        self.assertEqual(d['objeto'], 'RO123')
        self.assertEqual(d['tipos']['asignar']['cantidad'], 0)
        self.assertNotIn('NO_EXPORTAR', json.dumps(d))

    def test_alias_correo_verificado_historia_no_falso_cero(self):
        query = self.par_productor(); aid = self.action(obj='t-RO123', intent=True)
        code, d, _ = self.req(query=query)
        self.assertEqual(code, 200)
        self.assertEqual(d['tipos']['asignar']['cantidad'], 1)
        self.assertEqual(d['tipos']['asignar']['ultima']['accion_id'], aid)
        self.assertIsNone(d['tipos']['asignar']['ultima']['intencion_id'])
        self.assertTrue(d['tipos']['asignar']['ultima']['propia'])

    def test_correo_cid_desconocido_o_contradictorio_no_atribuir(self):
        query = self.par_productor()
        for cid in (None, 'cliente2', ''):
            self.doc['correos'][0]['cliente_id'] = cid; self.persist()
            self.assertEqual(self.req(query=query)[0], 503)

    def test_par_documentado_exige_id_url_y_departamento(self):
        for changes in ({'id': 'otro'}, {'url': None}, {'url': 'https://desk.zoho.eu/agent/otra'}, {'departamento': 'OTRO'}):
            query = self.par_productor(); self.doc['correos'][0].update(changes); self.persist()
            self.assertEqual(self.req(query=query)[0], 503)
        query = self.par_productor(); self.doc['triaje'][0]['id'] = 'arbitrario'; self.persist()
        self.assertEqual(self.req(query='ticket_id=arbitrario&cliente_id=cliente1')[0], 503)

    def test_doble_correo_o_triaje_no_se_funde(self):
        query = self.par_productor(); self.doc['correos'].append(dict(self.doc['correos'][0])); self.persist()
        self.assertEqual(self.req(query=query)[0], 503)
        query = self.par_productor(); self.doc['triaje'].append(dict(self.doc['triaje'][0])); self.persist()
        self.assertEqual(self.req(query=query)[0], 404)

    def test_alias_validado_cambia_en_ultimo_io(self):
        query = self.par_productor(); original = T._ledger
        def change(*a):
            result = original(*a)
            self.doc['triaje'][0]['departamento'] = 'QA2'; self.doc['correos'][0]['departamento'] = 'QA2'
            self.persist(); return result
        with patch.object(T, '_ledger', change): self.assertEqual(self.req(query=query)[0], 403)

    def test_hook_antes_piloto_en_servir(self):
        s = (ROOT/'servir.py').read_text()
        self.assertLess(s.index('TRIAJE_INTENCIONES_437.enganchar'), s.index('PILOTO_LECTURA.enganchar'))
        self.assertTrue(PILOTO.permite_lectura(T.RUTA))
        self.assertFalse(PILOTO.permite_lectura(T.RUTA+'/otro'))

if __name__ == '__main__': unittest.main()

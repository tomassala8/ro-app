"""209: wrapper193 real, traducción real y SQLite temporal, sin proveedor."""
import ast
from pathlib import Path
import json
import unittest
import probar_recibo_transicion_193 as R
import transiciones_mi_trabajo as T
import sqlite3

class Produccion209(R.Recibo193):
    def setUp(self):
        super().setUp()
        self.body['tipo']='pieza_aprobar';self.body['modulo']='produccion'
        self.body['texto']='Decisión fixture'
        self.body['vista_previa']={'transicion_produccion':True,'lista_id':'list-fixture','revision':'0'*64,
             'expected_estado':'revisión técnica','a':'revisión project manager'}
        self.estado='revisión técnica'
        self.rp={'por_estado':{'revisión técnica':{'a':'revisión project manager'}},'pedir_cambios_a':'corrección'}
        self.catalogo=[{'estado':x,'tipo':'custom'} for x in ['revisión técnica','revisión project manager','corrección','en curso']]
        self.ns.update(tarea=lambda _: {'lista_id':'list-fixture','estado':self.estado,'nombre':'Fixture','cli':'cliente-fixture'},
          _reglas_piezas=lambda:self.rp,_mi_trabajo=lambda:{'estados_detalle':{'list-fixture':self.catalogo}},
          estados_de_tarea=lambda _:[r['estado'] for r in self.catalogo])
        tree=ast.parse(Path(__file__).with_name('sincronia.py').read_text())
        n=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='destino_produccion_recibo')
        exec(compile(ast.Module(body=[n],type_ignores=[]),'destino209:AST','exec'),self.ns)
    def queue(self,aid):
        self.queue_calls+=1
        if self.queue_failure:raise RuntimeError('Fallo sintético')
        with self.conectar() as con:
            act=dict(con.execute('SELECT * FROM acciones WHERE id=?',(aid,)).fetchone());act['texto']='Decisión fixture'
            canal,obj,cam,base,ign=self.ns['traducir'](act)
            if self.bad_base:base={'estado':'antiguo'}
            cid,_=self.s.crear_cambio(con,clave='accion:'+str(aid),accion_id=aid,quien=act['quien'],canal=canal,tipo=act['tipo'],
              objeto=obj,cliente_id=act['cliente_id'],cambio=cam,base=base,modo='simulado',modulo=act['modulo'])
        return {'id':cid,'estado':'simulado'}
    # No heredar las aserciones específicas de MiTrabajo193: ésta es Producción.
    def test_recibo_produccion_con_tipo_modulo_y_destino_derivado(self):
        r=self.post()[1];self.assertTrue(r['recibo_durable']);self.assertEqual(r['recibo']['tipo'],'pieza_aprobar')
        self.assertEqual(r['recibo']['modulo'],'produccion');self.assertEqual(r['recibo']['hasta'],'revisión project manager')
        self.assertFalse(r['confirmacion_remota'])
    def test_mismo_uuid_respuesta_perdida_un_cambio_tipo_original(self):
        a=self.post()[1];b=self.post()[1];self.assertEqual(a['recibo'],b['recibo'])
        self.assertEqual(self.count('acciones'),1);self.assertEqual(self.count('sinc_cambios'),1)
        with self.conectar() as c:self.assertEqual(c.execute('SELECT tipo FROM sinc_cambios').fetchone()[0],'pieza_aprobar')
    def test_pedir_cambios_destino_server_no_cambiar_estado(self):
        self.body['tipo']='pieza_pedir_cambios';self.body['vista_previa'].update(a='corrección',comentario='Revisar fixture')
        r=self.post()[1];self.assertTrue(r['recibo_durable']);self.assertEqual(r['recibo']['tipo'],'pieza_pedir_cambios')
        with self.conectar() as c:self.assertEqual(json.loads(c.execute('SELECT cambio FROM sinc_cambios').fetchone()[0])['comentario'],'Revisar fixture')
    def test_mover_estado_lista_exacta_y_tipo_original(self):
        self.estado='en curso';self.body['tipo']='mover_estado';self.body['vista_previa']['expected_estado']='en curso'
        r=self.post()[1];self.assertTrue(r['recibo_durable']);self.assertEqual(r['recibo']['tipo'],'mover_estado')
    def test_cola_falla_recuperable_por_misma_intencion(self):
        self.queue_failure=True;a=self.post()[1];self.assertFalse(a['recibo_durable']);self.assertEqual(a['cola_estado'],'pendiente_recuperacion')
        self.queue_failure=False;b=self.post()[1];self.assertTrue(b['recibo_durable']);self.assertEqual(self.count('acciones'),1)
    def test_regla_cambia_antes_traduccion_no_envio_fallback(self):
        self.rp['por_estado']['revisión técnica']['a']='corrección'
        r=self.post()[1];self.assertFalse(r['recibo_durable']);self.assertTrue(r['requiere_revision']);self.assertFalse(r['reintento_seguro'])
        with self.conectar() as c:self.assertEqual(json.loads(c.execute('SELECT cambio FROM sinc_cambios').fetchone()[0])['campo'],'otro')
    def test_estado_cambia_antes_traduccion_no_destino_otro_estado(self):
        self.estado='en curso';r=self.post()[1];self.assertFalse(r['recibo_durable'])
        with self.conectar() as c:self.assertEqual(json.loads(c.execute('SELECT cambio FROM sinc_cambios').fetchone()[0])['campo'],'otro')
    def test_rp_ausente_no_usa_fallback_legacy(self):
        self.rp={};r=self.post()[1];self.assertFalse(r['recibo_durable'])
        self.assertEqual(r['motivo_recibo'],'cambio_no_enviable')
    def test_catalogo_sin_tipos_o_duplicado_no_certifica(self):
        for cat in [[{'estado':'revisión técnica'}],self.catalogo+[self.catalogo[0]]]:
            self.catalogo=cat;r=self.post()[1];self.assertFalse(r['recibo_durable'])
    def test_mover_destino_desconocido_no_primer_default(self):
        self.body['tipo']='mover_estado';self.body['vista_previa']['a']='inventado'
        r=self.post()[1];self.assertFalse(r['recibo_durable'])
        with self.conectar() as c:self.assertEqual(json.loads(c.execute('SELECT cambio FROM sinc_cambios').fetchone()[0])['campo'],'otro')
    def test_mover_legacy_permitido_no_es_destino_del_boton(self):
        self.body['tipo']='mover_estado';self.body['vista_previa']['a']='corrección'
        conf=dict(self.ns['CONF_DEF']);conf['destinos_mover']=['corrección','revisión project manager'];self.ns['conf']=lambda:conf
        r=self.post()[1];self.assertFalse(r['recibo_durable'])
        with self.conectar() as c:self.assertEqual(json.loads(c.execute('SELECT cambio FROM sinc_cambios').fetchone()[0])['campo'],'otro')
    def test_campos_modulo_flag_ambiguos_no_recibo(self):
        self.body['vista_previa']['transicion_tablero']=True;r=self.post()[1]
        self.assertFalse(r['recibo_durable'])
    def test_tipo_cambiar_estado_no_envelope_produccion(self):
        self.body['tipo']='cambiar_estado';r=self.post()[1];self.assertFalse(r['recibo_durable'])
    def test_recibo_link_tipo_modulo_cliente_y_actor_no_trusting_body(self):
        self.post()
        self.assertFalse(self.receipt(actor={'id':'otro'})['recibo_durable'])
        for field,value in [('tipo','mover_estado'),('modulo','mi-trabajo'),('cliente_id','otro')]:
            with self.conectar() as c:
                original=c.execute('SELECT '+field+' FROM acciones WHERE id=1').fetchone()[0]
                c.execute('UPDATE acciones SET '+field+'=? WHERE id=1',(value,))
            self.assertFalse(self.receipt()['recibo_durable'])
            with self.conectar() as c:c.execute('UPDATE acciones SET '+field+'=? WHERE id=1',(original,))
    def test_cliente_actual_divergente_no_recibo(self):
        self.post();self.ns['tarea']=lambda _: {'lista_id':'list-fixture','estado':self.estado,'cli':'otro'}
        self.assertFalse(self.receipt()['recibo_durable'])
    def test_manual_y_verificado_simulado_nunca_remoto(self):
        self.post()
        for event in ['hecho_a_mano','verificado']:
            with self.conectar() as c:self.s.paso(c,1,'confirmado',event)
            r=self.receipt();self.assertTrue(r['recibo_durable']);self.assertFalse(r['confirmacion_remota'])
    def test_base_anterior_no_recibo_falso(self):
        self.bad_base=True;self.assertFalse(self.post()[1]['recibo_durable'])
    def test_rp_cambia_despues_crear_cola_no_confirma_destino_ahora(self):
        self.post();self.rp['por_estado']['revisión técnica']['a']='corrección'
        r=self.receipt();self.assertFalse(r['recibo_durable']);self.assertEqual(r['motivo_recibo'],'destino_no_coherente')
    def test_legacy_sin_optin_conserva_traduccion(self):
        self.body['vista_previa'].pop('transicion_produccion');self.rp={}
        r=self.post()[1];self.assertNotIn('recibo_durable',r)
        with self.conectar() as c:self.assertEqual(json.loads(c.execute('SELECT cambio FROM sinc_cambios').fetchone()[0])['valor'],'revisión project manager')

# Unittest hereda tests193; deshabilitar sólo esa herencia aquí (se ejecutan aparte).
for name in list(R.Recibo193.__dict__):
    if name.startswith('test_') and name not in Produccion209.__dict__:setattr(Produccion209,name,None)

class Proyeccion209(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:');self.db.row_factory=sqlite3.Row;self.addCleanup(self.db.close)
        self.db.executescript('CREATE TABLE acciones(id INTEGER PRIMARY KEY,herramienta,tipo,objeto,vista_previa);CREATE TABLE sinc_cambios(id INTEGER PRIMARY KEY,accion_id,cambio,canal,objeto_ref);CREATE TABLE sinc_pasos(id INTEGER PRIMARY KEY,cambio_id,estado,evento,hora);')
        self.D={'generado':'fixture','estados_lista':{'list-fixture':['en curso','revisión project manager']},'tareas':[{'id':'task-fixture','cli':'client-fixture','persona_id':'owner','lista_id':'list-fixture','estado':'en curso'}],
          'estados_detalle':{'list-fixture':[{'estado':'en curso','tipo':'custom'},{'estado':'revisión project manager','tipo':'custom'}]}}
    def add(self,sinc=False):
        self.db.execute("INSERT INTO acciones VALUES(1,'clickup','mover_estado','task-fixture',?)",(json.dumps({'a':'revisión project manager'}),))
        if sinc:
            self.db.execute("INSERT INTO sinc_cambios VALUES(1,1,?,'clickup','task-fixture')",(json.dumps({'campo':'estado','valor':'revisión project manager'}),))
            self.db.execute("INSERT INTO sinc_pasos VALUES(1,1,'simulado','simulado',NULL)")
    def test_mover_sin_sinc_no_confia_destino_navegador(self):
        antes=T.proyectar(self.D,'task-fixture',self.db);self.add()
        r=T.proyectar(self.D,'task-fixture',self.db);self.assertTrue(r['bloqueada']);self.assertEqual(r['expected_estado'],'en curso')
        self.assertNotEqual(antes['revision'],r['revision'])
    def test_mover_con_sinc_usa_destino_y_hash_cola(self):
        self.add(True);r=T.proyectar(self.D,'task-fixture',self.db)
        self.assertFalse(r['bloqueada']);self.assertEqual(r['expected_estado'],'revisión project manager')
    def test_confirmado_antiguo_sin_lectura_posterior_sigue_bloqueado(self):
        self.add(True);self.db.execute("INSERT INTO sinc_pasos VALUES(2,1,'confirmado','verificado','2026-10-03 10:00:00')")
        self.assertTrue(T.proyectar(self.D,'task-fixture',self.db)['bloqueada'])

if __name__=='__main__':unittest.main()

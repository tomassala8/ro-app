"""Regresión independiente: hooks reales, permisos reales, SQLite temporal, sin proveedores."""
import ast
import re
from pathlib import Path
import copy
from contextlib import contextmanager
import sqlite3
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import permisos as P
import tareas_local as T

class Seguridad146(unittest.TestCase):
    def setUp(self):
        self.actor={'id':'actor','puestos':['direccion'],'estado':'activo'}
        self.vista={'id':'equipo','puestos':['operaciones'],'estado':'activo'}
        self.canon={'id':'cliente-activo','nombre':'Fixture','servicios':{'publicidad':'sí'}}
        self.raw={'personas':[self.actor,self.vista],'clientes':[self.canon],'asignaciones':[]}
        self.tasks=[{'id':'activa','cli':'cliente-activo','asignados':['actor'],'tarea':'Fixture'},
                    {'id':'obsoleta','cli':'cliente-inactivo','asignados':['actor'],'tarea':'No debe salir'},
                    {'id':'personal','cli':None,'asignados':['actor'],'tarea':'Personal'}]
        self.db=sqlite3.connect(':memory:');self.db.row_factory=sqlite3.Row
        @contextmanager
        def conectar():
            yield self.db
        self.S=SimpleNamespace(P=P,E=SimpleNamespace(crudo=self.raw,nucleo_bloqueado=False),
           conectar=conectar,ve_alguno=lambda p,m:True)
        class Handler:
            def responder(self,status,body):return status,body
            def _api_get(self,*args):return 404,{}
            def api_post(self,*args):return 404,{}
        self.H=Handler
        T.enganchar(Handler,self.S, solo_preferencias=False)
        self.fixtures=patch.object(T,'inventario',side_effect=lambda: {'tareas':copy.deepcopy(self.tasks)})
        self.fixtures.start()
        self.catalog=patch.object(T,'leer',return_value={});self.catalog.start()
        self.act=patch('fuentes_verdad.clientes_activos.es_activo_id',side_effect=lambda cid:cid=='cliente-activo');self.act.start()
    def tearDown(self):
        self.act.stop();self.catalog.stop();self.fixtures.stop();self.db.close()
    def test_inventario_excluye_cliente_inactivo_y_desconocido(self):
        status,d=self.H()._api_get('/api/tareas/tablero',{},self.actor,self.actor)
        self.assertEqual(status,200)
        self.assertEqual({t['id'] for t in d['tareas']},{'activa','personal'})
    def test_no_guarda_filtro_cliente_obsoleto(self):
        b={'accion':'guardar','nombre':'Fixture','filtros':{**T.VT.DEFAULT,'cliente':'cliente-inactivo'}}
        status,_=self.H().api_post('/api/tareas/vistas',self.actor,self.actor,b)
        self.assertEqual(status,400)
        self.assertIsNone(self.db.execute("SELECT name FROM sqlite_master WHERE name='tareas_vistas_privadas'").fetchone())
    def test_wiring_por_defecto_no_activa_tablero_ni_mutaciones(self):
        class Seguro:
            def responder(self,status,body):return status,body
            def _api_get(self,*args):return 404,{}
            def api_post(self,*args):return 404,{}
        T.enganchar(Seguro,self.S)
        self.assertEqual(Seguro()._api_get('/api/tareas/tablero',{},self.actor,self.actor)[0],404)
        self.assertEqual(Seguro().api_post('/api/tareas/cambio',self.actor,self.actor,{'accion':'estado'})[0],404)
        self.assertEqual(Seguro()._api_get('/api/tareas/vistas',{},self.actor,self.actor)[0],200)
    def test_vercomo_no_lee_ni_escribe_preferencias(self):
        self.assertEqual(self.H()._api_get('/api/tareas/vistas',{},self.actor,self.vista)[0],403)
        self.assertEqual(self.H().api_post('/api/tareas/vistas',self.actor,self.vista,{'accion':'eliminar'})[0],403)
    def test_nucleo_denegado_y_modulo_revocado_no_abren_preferencias(self):
        self.S.E.nucleo_bloqueado=True
        self.assertEqual(self.H()._api_get('/api/tareas/vistas',{},self.actor,self.actor)[0],503)
        self.S.E.nucleo_bloqueado=False;self.S.ve_alguno=lambda p,m:False
        self.assertEqual(self.H()._api_get('/api/tareas/vistas',{},self.actor,self.actor)[0],403)
    def test_catalogo_canonico_y_ACT_doble_puerta(self):
        self.raw['clientes']=[]
        status,d=self.H()._api_get('/api/tareas/tablero',{},self.actor,self.actor)
        self.assertEqual({t['id'] for t in d['tareas']},{'personal'})
        self.raw['clientes']=[self.canon,self.canon]
        status,d=self.H()._api_get('/api/tareas/tablero',{},self.actor,self.actor)
        self.assertEqual({t['id'] for t in d['tareas']},{'personal'})

class RecorteProduccion146(unittest.TestCase):
    def test_filas_cliente_revisiones_horas_interseccion_real_vista(self):
        # Ejecuta el recortador real sin importar servidor/startup; aisla sólo la capa de dinero.
        arbol=ast.parse((Path(__file__).parent/'servir.py').read_text())
        nombres={'recortar_modulo','clientes_ajenos','cliente_de_fila'}
        modulo=ast.Module(body=[n for n in arbol.body if isinstance(n,ast.FunctionDef) and n.name in nombres],type_ignores=[])
        real={'id':'account','puestos':['account']};vista={'id':'direccion','puestos':['direccion']}
        raw={'personas':[real,vista],'clientes':[{'id':'propio','nombre':'Propio'},{'id':'ajeno','nombre':'Ajeno'}],
             'asignaciones':[{'persona_id':'account','cliente_id':'propio','silla':'account'}]}
        ns={'P':P,'E':SimpleNamespace(crudo=raw),'quitar_para':lambda *a:[],
            'CLAVES_CUOTA':re.compile('^cuota$'),'CLAVES_INVERSION':re.compile('^gasto$'),
            'CLAVES_RENTABILIDAD':re.compile('^margen$'),'CLAVES_ENLACE':re.compile('^url$'),
            '_quita':lambda *a:False,'CLAVES_FILA_LEAD':set()}
        exec(compile(modulo,'recorte_real_146','exec'),ns)
        obj={'proyectos':[{'cliente_id':cid,'horas_mes':2,'horas_medicion':{'estado':'medido','fecha':'2026-10-03'},
                          'revisiones_account':{'estado':'medido','fecha':'2026-10-03'},'rev_account':1} for cid in ['propio','ajeno']]}
        with P.mirando_como(real,raw):
            out=ns['recortar_modulo'](vista,P.contexto(vista,raw),obj)
        self.assertEqual([r['cliente_id'] for r in out['proyectos']],['propio'])
        self.assertEqual(out['proyectos'][0]['horas_medicion']['estado'],'medido')
        self.assertEqual(out['proyectos'][0]['revisiones_account']['estado'],'medido')
        with P.mirando_como(vista,raw):
            out=ns['recortar_modulo'](real,P.contexto(real,raw),obj)
        self.assertEqual([r['cliente_id'] for r in out['proyectos']],['propio'])

if __name__=='__main__':unittest.main()

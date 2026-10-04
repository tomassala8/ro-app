"""Cruce 147: controladores reales, sin servidor, red, DB real ni claves."""
import ast
import os
from pathlib import Path
from unittest.mock import patch
import unittest
import piloto_lectura as PIL

ROOT=Path(__file__).parent

class Integracion147(unittest.TestCase):
    def handler(self):
        class H:
            calls=[]
            def _api_get(self,ruta,*a):self.calls.append(('get',ruta));return 200,{'fixture':True}
            def api_post(self,ruta,*a):self.calls.append(('post',ruta));return 200,{'fixture':True}
            def responder(self,codigo,cuerpo):return codigo,cuerpo
        PIL.enganchar(H)
        return H()
    def test_piloto_cubre_post_nuevos_y_sincronia_antes_delegar(self):
        h=self.handler()
        with patch.dict(os.environ,{'RO_PILOTO_LECTURA':'1'}):
            for ruta in ('/api/tareas/vistas','/api/tareas/tablero','/api/mi_trabajo','/api/acciones',
                         '/api/acciones/lote','/api/sincronia/activar','/api/sincronia/reintentar',
                         '/api/ia/gasto/topes','/api/ia/borrador','/api/recarga'):
                self.assertEqual(h.api_post(ruta,{'id':'fixture'},{'id':'fixture'}, {})[0],403)
        self.assertEqual(h.calls,[])
    def test_piloto_cubre_gets_efectos_y_preferencias_no_revisados(self):
        h=self.handler()
        with patch.dict(os.environ,{'RO_PILOTO_LECTURA':'1'}):
            for ruta in ('/api/tareas/vistas','/api/tareas/tablero','/api/sincronia','/api/envios',
                         '/api/ia/gasto','/api/ia/borrador','/api/mi_trabajo/contexto_ia'):
                self.assertEqual(h._api_get(ruta,{}, {}, {})[0],403)
        self.assertEqual(h.calls,[])
    def test_piloto_contexto_remoto_bloqueado_con_degradacion_local(self):
        # La pantalla sigue habilitada; contexto remoto no se abre por comodidad.
        with patch.dict(os.environ,{'RO_PILOTO_LECTURA':'1'}):
            self.assertIn('mi-trabajo',PIL.modulos_disponibles({'mi-trabajo':{},'envios':{}}))
            self.assertTrue(PIL.permite_lectura('/api/mi_trabajo'))
            self.assertFalse(PIL.permite_lectura('/api/mi_trabajo/contexto_ia'))
        front=(ROOT/'modulos/tarea_ia.js').read_text()
        self.assertIn('mi_trabajo/contexto_ia?tarea=',front)
        self.assertIn('Preparar esta tarea con IA',front)
        mt=(ROOT/'modulos/mi_trabajo.js').read_text()
        self.assertIn('    contextoTareaTrabajo(E, t),',mt)
        self.assertIn('if (consultaLocalTrabajo(E.ctx)) return vacioLinea',mt)
    def test_hook_piloto_es_ultimo_enganche_actual(self):
        tree=ast.parse((ROOT/'servir.py').read_text())
        calls=sorted((n for n in ast.walk(tree) if isinstance(n,ast.Call)
                      and isinstance(n.func,ast.Attribute) and n.func.attr=='enganchar'),key=lambda n:n.lineno)
        self.assertEqual(ast.unparse(calls[-1].func),'PILOTO_LECTURA.enganchar')
    def test_141_finalizar_no_equivale_cualquier_final_ni_otra_lista(self):
        tree=ast.parse((ROOT/'sincronia.py').read_text())
        funcs=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('estados_de_tarea','estados_hecha_de_tarea')]
        doc={'estados_lista':{'A':['completado','rechazado'],'B':['completado']},
             'estados_detalle':{'A':[{'estado':'completado','tipo':'custom'},{'estado':'rechazado','tipo':'closed'}],
                               'B':[{'estado':'completado','tipo':'done'}]}}
        ns={'_mi_trabajo_tarea':lambda ref:{'lista_id':ref} if ref in ('A','B') else None,
            '_mi_trabajo':lambda:doc,'conf':lambda:{'estados_hecha':['completado']}}
        exec(compile(ast.Module(body=funcs,type_ignores=[]),'147_real','exec'),ns)
        self.assertEqual(ns['estados_hecha_de_tarea']('A'),[])
        self.assertEqual(ns['estados_hecha_de_tarea']('B'),['completado'])
        self.assertEqual(ns['estados_hecha_de_tarea']('desconocida'),[])

if __name__=='__main__':unittest.main(verbosity=2)

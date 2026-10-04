"""Productor196 real extraído AST; fixtures sin red ni ficheros de datos."""
import ast
from datetime import datetime, timezone
from pathlib import Path
import types
import unittest
from fuentes_produccion.lectura_estado_196 import sello_proveedor, sello_copia

INICIO='2026-10-03T10:00:00Z';AHORA='2026-10-03T12:00:00Z'

class Lectura196(unittest.TestCase):
    def raw(self,estado='abierto'):
        return {'id':'task-fixture','status':{'status':estado,'type':'open'},'list':{'id':'list-fixture'}}
    def cache(self):
        return {'estado':'abierto',**sello_proveedor(self.raw(),INICIO)}
    def test_sello_solo_status_actual_valido(self):
        self.assertEqual(sello_proveedor(self.raw(),INICIO),{'estado_fuente':'clickup','estado_leido_utc':INICIO})
        for t in [None,{}, {'status':None},{'status':'abierto'},{'status':{'status':None}},{'status':{'status':' '}}]:
            self.assertEqual(sello_proveedor(t,INICIO),{})
    def test_historia_sin_status_no_acredita_lectura(self):
        self.assertEqual(sello_proveedor({'status_history':[{'status':'abierto'}]},INICIO),{})
    def test_timestamp_no_utc_aware_rechazado(self):
        for t in [None,'invalid','2026-10-03T10:00:00','2026-99-03T10:00:00Z']:
            self.assertEqual(sello_proveedor(self.raw(),t),{})
    def test_offset_equivalente_normaliza_utc(self):
        self.assertEqual(sello_proveedor(self.raw(),'2026-10-03T12:00:00+02:00')['estado_leido_utc'],INICIO)
    def test_cache_antigua_generado_nunca_certifica(self):
        self.assertEqual(sello_copia({'estado':'abierto','generado':INICIO,'actualizada':INICIO},'abierto',AHORA),{})
    def test_propaga_misma_lectura_no_hora_nueva(self):
        self.assertEqual(sello_copia(self.cache(),'abierto',AHORA),sello_proveedor(self.raw(),INICIO))
    def test_estado_distinto_no_certifica_copia(self):
        self.assertEqual(sello_copia(self.cache(),'cerrado',AHORA),{})
    def test_future_fuente_desconocida_y_naive_no_certifican(self):
        for override in [{'estado_leido_utc':'2027-01-01T00:00:00Z'},{'estado_fuente':'cache'},{'estado_leido_utc':'2026-10-03T10:00:00'}]:
            self.assertEqual(sello_copia({**self.cache(),**override},'abierto',AHORA),{})
    def test_extractor_real_sello_anterior_lectura_no_historia(self):
        tree=ast.parse(Path(__file__).with_name('fuentes_produccion').joinpath('extraer_clickup.py').read_text())
        n=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='tareas')
        events=[];out=[]
        class Clock(datetime):
            @classmethod
            def now(cls,tz=None):events.append('clock');return datetime(2026,10,3,10,tzinfo=timezone.utc)
        def read(params):events.append('read');return [self.raw(),self.raw('')|{'id':'missing-fixture'}]
        cu=types.SimpleNamespace(tareas_equipo=read,tiempo_en_estado=lambda ids:{'task-fixture':{'current_status':{'status':'otro','total_time':{'since':42}}}},NOW=datetime(2026,1,1))
        ns={'dt':types.SimpleNamespace(datetime=Clock,timezone=timezone),'cu':cu,'contexto_operativo':lambda _: {},'metadata_tarea':lambda _: {},
            'sello_proveedor':sello_proveedor,'DESDE_TAREAS':'fixture','escribe':lambda name,d:out.append(d)}
        exec(compile(ast.Module(body=[n],type_ignores=[]),'extraer:AST196','exec'),ns)
        self.assertEqual(ns['tareas']({}),2);self.assertEqual(events,['clock','read'])
        a,b=out[0]['tareas'];self.assertEqual(a['estado'],'abierto');self.assertEqual(a['estado_leido_utc'],INICIO)
        self.assertNotIn('estado_leido_utc',b);self.assertNotEqual(out[0]['meta']['generado'],INICIO)
    def test_extractor_fallo_lectura_no_escribe_sello(self):
        tree=ast.parse(Path(__file__).with_name('fuentes_produccion').joinpath('extraer_clickup.py').read_text())
        n=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='tareas')
        def fail(_):raise RuntimeError('fixture')
        writes=[];ns={'dt':__import__('datetime'),'cu':types.SimpleNamespace(tareas_equipo=fail),'escribe':lambda *a:writes.append(a)}
        exec(compile(ast.Module(body=[n],type_ignores=[]),'extraer:AST196','exec'),ns)
        with self.assertRaises(RuntimeError):ns['tareas']({})
        self.assertEqual(writes,[])
    def test_generador_real_filas_scope_copia_y_estado_incoherente(self):
        # Ejecutar sólo el bucle puro del generador, jamás main/import/escrituras.
        tree=ast.parse(Path(__file__).with_name('fuentes_mi_trabajo').joinpath('generar_mi_trabajo.py').read_text())
        loops=[n for n in ast.walk(tree) if isinstance(n,ast.For) and any(isinstance(c,ast.Call) and isinstance(c.func,ast.Name) and c.func.id=='sello_copia' for c in ast.walk(n))]
        loop=next(n for n in loops if isinstance(n.iter,ast.Name) and n.iter.id=='tareas')
        rows=[{'id':'a','estado':'abierto'},{'id':'b','estado':'cerrado'},{'id':'c','estado':'abierto'}]
        ns={'tareas':rows,'por_id':{'a':self.cache(),'b':self.cache(),'c':{'estado':'abierto','generado':INICIO}},'ahora_estado_utc':AHORA,'sello_copia':sello_copia}
        exec(compile(ast.Module(body=[loop],type_ignores=[]),'generador:AST196','exec'),ns)
        self.assertEqual(rows[0]['estado_leido_utc'],INICIO)
        self.assertNotIn('estado_leido_utc',rows[1]);self.assertNotIn('estado_leido_utc',rows[2])

    def test_inventario_sin_asignacion_preserva_mismo_sello(self):
        tree=ast.parse(Path(__file__).with_name('fuentes_mi_trabajo').joinpath('generar_mi_trabajo.py').read_text())
        d=next(n for n in ast.walk(tree) if isinstance(n,ast.Dict)
          and any(isinstance(k,ast.Constant) and k.value=='asignados' for k in n.keys)
          and any(isinstance(c,ast.Call) and isinstance(c.func,ast.Name) and c.func.id=='sello_copia' for c in ast.walk(n)))
        ns={'t':{'id':'unassigned',**self.cache()},'li':None,'vence':None,'HOY':None,
          'sin_importes':lambda x:x,'limpiar':lambda x:x,'grupo':lambda *a:'sin_fecha',
          'extra_de':lambda *a:{},'sello_copia':sello_copia,'ahora_estado_utc':AHORA}
        ns['t']['nombre']='Fixture'
        r=eval(compile(ast.Expression(body=d),'inventario:AST196','eval'),ns)
        self.assertEqual(r['estado_leido_utc'],INICIO);self.assertEqual(r['asignados'],[])

if __name__=='__main__':unittest.main()

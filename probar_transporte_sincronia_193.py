"""Auditoría193 motor real extraído AST + SQLite temporal + ClickUpSimulado real, sin red."""
import ast
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import types
import unittest
from datetime import datetime,timedelta,timezone
from probar_sincronia_resultado_desconocido import cargar_candidato


def cargar():
    s=cargar_candidato();ns=s.ejecutar.__globals__;tree=ast.parse(Path(__file__).with_name('sincronia.py').read_text())
    names={'Proveedor','ClickUpSimulado','traducir','estados_hecha_de_tarea','reintentar','clave_accion'}
    nodes=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name in names
           or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='CAMPOS_NAVEGADOR' for t in n.targets)]
    ns.update(hashlib=hashlib,limpio=lambda x,*a:x,tarea=lambda ref:{'nombre':'Fixture','estado':'abierto','visto':'2026-10-03 10:00'},
              estados_de_tarea=lambda _:['abierto','cerrado'],_mi_trabajo_tarea=lambda _: {'lista_id':'list-fixture'},
              _mi_trabajo=lambda:{'estados_detalle':{'list-fixture':[{'estado':'cerrado','tipo':'closed'}]}},_persona=lambda _: {})
    exec(compile(ast.Module(body=nodes,type_ignores=[]),'sincronia.py:AST193','exec'),ns)
    # Sólo el método de transporte real; self.pide del fixture registra argumentos, nunca HTTP.
    clase=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='ProveedorClickUp')
    apply=next(n for n in clase.body if isinstance(n,ast.FunctionDef) and n.name=='aplicar')
    apply.name='aplicar_transport';exec(compile(ast.Module(body=[apply],type_ignores=[]),'ClickUp.aplicar:AST193','exec'),ns)
    return types.SimpleNamespace(**ns)


class Transporte193(unittest.TestCase):
    def setUp(self):
        self.s=cargar();self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.db=str(Path(self.tmp.name)/'fixture.db');self.con=sqlite3.connect(self.db);self.con.row_factory=sqlite3.Row;self.addCleanup(self.con.close)
        self.con.executescript(self.s.TABLAS_SQL);self.now=datetime(2026,10,3,10)
        self.s.ejecutar.__globals__['ahora_utc']=lambda:self.now

    def crear(self,clave='fixture',cam=None,accion_id=None):
        cid,nuevo=self.s.crear_cambio(self.con,clave=clave,quien='actor-fixture',canal='clickup',tipo='cambiar_estado',
             objeto={'tipo':'tarea','ref':'task-fixture','resuelto':True},cambio=cam or {'campo':'estado','valor':'cerrado'},
             base={'estado':'abierto'},accion_id=accion_id,modo='prueba',hora=self.now)
        self.con.commit();return cid,nuevo

    def prov(self,clave='fixture',guion=None):
        return self.s.ClickUpSimulado({'task-fixture':{'estado':'abierto','actualizado':self.now,'marcas':set()}}, {clave:guion or {}})

    def accion(self,tipo,vp):
        return {'tipo':tipo,'objeto':'task-fixture','texto':'Fixture','vista_previa':json.dumps(vp),'quien':'actor-fixture','cliente_id':'cliente-fixture'}

    def test_estado_libre_transporte_exacto(self):
        canal,o,cam,base,ign=self.s.traducir(self.accion('cambiar_estado',{'a':'cerrado','estado':'estado-forjado'}))
        self.assertEqual(cam,{'campo':'estado','valor':'cerrado'});self.assertTrue(o['resuelto']);self.assertIn('estado',ign)
        calls=[];p=types.SimpleNamespace(pide=lambda *a,**k:calls.append((a,k)))
        cid,_=self.crear(cam=cam);self.s.aplicar_transport(p,self.s.fila(self.con,cid))
        self.assertEqual(calls[0][0],('PUT','/task/task-fixture',{'status':'cerrado'}))

    def test_final_solo_catalogo_tipado(self):
        ns=self.s.ejecutar.__globals__
        for tipo,esperado in [('open',None),('custom',None),('done','cerrado'),('closed','cerrado')]:
            ns['_mi_trabajo']=lambda tipo=tipo:{'estados_detalle':{'list-fixture':[{'estado':'cerrado','tipo':tipo}]}}
            self.assertEqual(self.s.traducir(self.accion('marcar_hecha',{}))[2].get('valor'),esperado)

    def test_misma_clave_dos_solicitudes_un_cambio(self):
        a,n=self.crear('request-fixture');b,m=self.crear('request-fixture')
        self.assertEqual(a,b);self.assertTrue(n);self.assertFalse(m);self.assertEqual(self.con.execute('SELECT count(*) FROM sinc_cambios').fetchone()[0],1)

    def test_misma_accion_con_claves_distintas_no_dobla(self):
        a,n=self.crear('clave-a',accion_id=1);b,m=self.crear('clave-b',accion_id=1)
        self.assertEqual(a,b);self.assertFalse(m)

    def test_dos_ejecuciones_mismo_estado_un_efecto(self):
        cid,_=self.crear();p=self.prov();self.assertEqual(self.s.ejecutar(self.con,cid,p,ahora=self.now),'confirmado');self.con.commit()
        self.assertEqual(self.s.ejecutar(self.con,cid,p,ahora=self.now),'confirmado')
        self.assertEqual(sum(op=='aplicar' for op,k in p.llamadas),1)

    def test_dos_acciones_estado_igual_no_segunda_escritura(self):
        a,_=self.crear('a',accion_id=1);b,_=self.crear('b',accion_id=2);p=self.prov()
        self.s.ejecutar(self.con,a,p,ahora=self.now);self.con.commit();self.s.ejecutar(self.con,b,p,ahora=self.now)
        self.assertEqual(sum(op=='aplicar' for op,k in p.llamadas),1);self.assertEqual(self.con.execute('SELECT count(*) FROM sinc_cambios').fetchone()[0],2)

    def test_demuestra_dos_acciones_comentario_igual_son_dos_efectos(self):
        cam={'campo':'comentario','texto':'El mismo comentario'}
        a,_=self.crear(self.s.clave_accion(1),cam,1);b,_=self.crear(self.s.clave_accion(2),cam,2);p=self.prov()
        self.s.ejecutar(self.con,a,p,ahora=self.now);self.con.commit();self.s.ejecutar(self.con,b,p,ahora=self.now)
        self.assertEqual(p.tareas['task-fixture']['comentarios'],['El mismo comentario','El mismo comentario'])
        self.assertEqual(sum(op=='aplicar' for op,k in p.llamadas),2)

    def test_respuesta_perdida_tras_estado_relectura_sin_doblar(self):
        cid,_=self.crear();p=self.prov(guion={'aplicar':['red_pero_aplicado']})
        self.assertEqual(self.s.ejecutar(self.con,cid,p,ahora=self.now),'enviado');self.con.commit()
        self.assertEqual(self.s.verificar(self.con,cid,p,ahora=self.now),'confirmado');self.con.commit()
        self.assertEqual(self.s.reintentar(self.con,cid,'actor-fixture',p)['codigo'],409)
        self.assertEqual(sum(op=='aplicar' for op,k in p.llamadas),1)

    def test_aceptado_sin_lectura_no_reintento_habilitado(self):
        cid,_=self.crear();p=self.prov(guion={'perdido':True})
        self.assertEqual(self.s.ejecutar(self.con,cid,p,ahora=self.now),'enviado');self.con.commit()
        self.assertEqual(self.s.verificar(self.con,cid,p,ahora=self.now+timedelta(days=10)),'enviado')
        self.assertEqual(self.s.reintentar(self.con,cid,'actor-fixture',p)['codigo'],409)
        self.assertEqual(sum(op=='aplicar' for op,k in p.llamadas),1)

    def test_incierto_reabre_sqlite_y_sigue_bloqueado(self):
        cid,_=self.crear();p=self.prov(guion={'perdido':True})
        self.s.ejecutar(self.con,cid,p,ahora=self.now);self.con.commit()
        with sqlite3.connect(self.db) as otra:
            otra.row_factory=sqlite3.Row
            self.assertEqual(self.s.ejecutar(otra,cid,p,ahora=self.now+timedelta(days=1)),'enviado')
            self.assertEqual(self.s.reintentar(otra,cid,'actor-fixture',p)['codigo'],409)
        self.assertEqual(sum(op=='aplicar' for op,k in p.llamadas),1)

    def test_fuera_antes_conflicto_sin_escribir(self):
        cid,_=self.crear();p=self.prov(guion={'fuera':'otro_estado'})
        self.assertEqual(self.s.ejecutar(self.con,cid,p,ahora=self.now),'conflicto')
        self.assertEqual(sum(op=='aplicar' for op,k in p.llamadas),0)

    def test_comprobar_no_escribir_ni_confirmar_cambio(self):
        cid,_=self.crear();p=self.prov();self.assertTrue(p.comprobar()['ok'])
        self.assertEqual(self.s.estado_actual(self.con,cid)['estado'],'pendiente')
        self.assertFalse(any(op=='aplicar' for op,k in p.llamadas))

    def test_demuestra_estado_none_falsamente_confirmado_en_simulado(self):
        _,_,cam,_,_=self.s.traducir(self.accion('cambiar_estado',{'a':'inventado'}));self.assertEqual(cam['campo'],'otro')
        cid,_=self.crear(cam={'campo':'estado','valor':None});p=self.prov();self.assertEqual(self.s.ejecutar(self.con,cid,p,ahora=self.now),'confirmado')
        self.assertIsNone(p.tareas['task-fixture']['estado'])

    def test_demuestra_transporte_none_generaria_put_null(self):
        calls=[];p=types.SimpleNamespace(pide=lambda *a,**k:calls.append((a,k)))
        cid,_=self.crear(cam={'campo':'estado','valor':None});self.s.aplicar_transport(p,self.s.fila(self.con,cid))
        self.assertEqual(calls[0][0][2],{'status':None})

if __name__=='__main__':unittest.main()

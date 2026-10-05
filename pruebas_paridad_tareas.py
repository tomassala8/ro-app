"""Pruebas aisladas del prototipo. No realizan conexiones ni escrituras externas."""
import json
import sqlite3
import unittest
from datetime import date,datetime,timedelta
from unittest.mock import patch
import inventario_tareas as I
import tareas_local as T
import sincronia as S

UUID='12345678-1234-1234-1234-123456789012'


class Paridad(unittest.TestCase):
    def setUp(self):
        T.SN=S
        self.c=sqlite3.connect(':memory:');self.c.row_factory=sqlite3.Row;S.preparar(self.c)
        self.ps={'a':{'id':'a','activo':True,'clickup_id':'1','jefe':'j'},'b':{'id':'b','activo':True,'clickup_id':'2','jefe':'j'},'j':{'id':'j','activo':True,'puestos':[]},'ops':{'id':'ops','puestos':['operaciones']}}
        self.t={'id':'task1','lista_id':'l','estado':'diario','tarea':'Tarea','asignados':['a'],'cli':'c','_usuarios_asignados':['1']}
        self.b={'clave':UUID,'tarea':'task1','accion':'estado','estado':'diario'}
    def tearDown(self):self.c.close()
    def test_catalogo_real_no_historial(self):
        est,det=I.catalogo_listas({'listas':{'l':{'ok':True,'estados':[{'status':'completado','type':'custom','orderindex':0},{'status':'rechazado','type':'done','orderindex':1}]},'no':{'ok':False,'estados':[{'status':'inventado'}]}}})
        self.assertEqual(est,{'l':['completado','rechazado']})
        self.assertEqual(det['l'][1]['tipo'],'done')
        self.assertEqual(I.grupo({'estado':'completado','tipo_estado':'custom'},None,date.today()),'sin_fecha')
    def test_inventario_no_excluye_backlog_sinfecha_futuro_cerrado(self):
        ts=[{'id':str(n),'estado':estado,'tipo_estado':tipo,'vence':vence,'asignados':[{'id':'1'}]} for n,(estado,tipo,vence) in enumerate([('backlog','custom',None),('diario','custom',None),('diario','custom','2028-01-01'),('rechazado','done',None)])]
        out=I.extras(ts,set(),{'1':'a'},{},{},date(2026,10,3),lambda x:datetime.fromisoformat(x) if x else None,lambda x:x or '',lambda tid,pid:{}, {})
        self.assertEqual(len(out),4)
        self.assertEqual([x['grupo'] for x in out],['backlog','sin_fecha','futuro','completadas'])
    def test_visible_sinasignar_cartera_y_foreign(self):
        yes=lambda p,c:p['id'] in ('ops','acc','a','j')
        self.assertTrue(T.visible(self.ps['a'],self.t,self.ps,yes))
        self.assertFalse(T.visible(self.ps['b'],self.t,self.ps,yes))
        vacia={**self.t,'asignados':[]}
        self.assertTrue(T.visible({'id':'acc','puestos':['account']},vacia,self.ps,yes))
        self.assertFalse(T.visible({'id':'acc','puestos':['account']},vacia,self.ps,lambda p,c:False))
        self.assertFalse(T.visible(self.ps['a'],self.t,self.ps,lambda p,c:False))
    def test_marcar_hecha_no_elige_rechazado_por_tipo_done(self):
        a={'tipo':'marcar_hecha','objeto':'task1','texto':None,'vista_previa':None,'cliente_id':'c','quien':'a'}
        with patch.object(S,'tarea',lambda ref:self.t),patch.object(S,'estados_de_tarea',lambda ref:['rechazado']):
            self.assertEqual(S.traducir(a)[2]['campo'],'otro')
        with patch.object(S,'tarea',lambda ref:self.t),patch.object(S,'estados_de_tarea',lambda ref:['completado','rechazado']):
            self.assertEqual(S.traducir(a)[2]['valor'],'completado')

    def test_estado_invalido_bloqueado(self):
        with self.assertRaises(ValueError):T.construir_cambio(self.b,self.t,self.ps['a'],self.ps,self.ps,{'l':['otro']})
        self.assertEqual(T.construir_cambio(self.b,self.t,self.ps['a'],self.ps,self.ps,{'l':['diario']})['valor'],'diario')
    def test_asignacion_requiere_jefe_y_ids_confirmados(self):
        b={'clave':UUID,'tarea':'task1','accion':'asignar','asignados':['b']}
        with self.assertRaises(PermissionError):T.construir_cambio(b,self.t,self.ps['a'],self.ps,self.ps,{})
        cam=T.construir_cambio(b,self.t,self.ps['j'],self.ps,self.ps,{})
        self.assertEqual(cam['usuarios'],['2'])
        with self.assertRaises(ValueError):T.construir_cambio(b,self.t,self.ps['j'],self.ps,{}, {})
    def test_comment_mentions_payload_controlado(self):
        b={'clave':UUID,'tarea':'task1','accion':'comentario','texto':'Última versión','menciones':['b']}
        cam=T.construir_cambio(b,self.t,self.ps['a'],self.ps,self.ps,{})
        self.assertEqual(cam['menciones'],[{'persona':'b','usuario_clickup':'2'}])
        b['menciones']=['externo']
        with self.assertRaises(ValueError):T.construir_cambio(b,self.t,self.ps['a'],self.ps,self.ps,{})
    def test_entregable_enlace_seguro_no_field_equivalence(self):
        b={'clave':UUID,'tarea':'task1','accion':'entrega','enlace':'javascript:alert(1)'}
        with self.assertRaises(ValueError):T.construir_cambio(b,self.t,self.ps['a'],self.ps,self.ps,{})
        b['enlace']='https://example.com/version2';cam=T.construir_cambio(b,self.t,self.ps['a'],self.ps,self.ps,{})
        self.assertEqual(cam['campo'],'comentario')
        self.assertNotIn('custom_field',cam)
    def test_cola_reintento_idempotente_y_reuso_distinto_rechazado(self):
        cam={'campo':'estado','valor':'diario'}
        a,n=T.guardar(self.c,self.ps['a'],self.b,self.t,cam)
        b,n2=T.guardar(self.c,self.ps['a'],self.b,self.t,cam)
        self.assertEqual(a,b);self.assertTrue(n);self.assertFalse(n2)
        self.assertEqual(S.estado_actual(self.c,a)['estado'],'simulado')
        with self.assertRaises(ValueError):T.guardar(self.c,self.ps['a'],self.b,self.t,{'campo':'estado','valor':'otro'})
        self.assertEqual(self.c.execute('select count(*) from sinc_cambios').fetchone()[0],1)
    def test_mock_provider_asignar_remueve_y_verifica_set_exacto(self):
        p=S.ProveedorClickUp();calls=[]
        def pide(m,r,b=None,**kw):
            calls.append((m,r,b));return {'assignees':[{'id':1},{'id':3}]} if m=='GET' else {'ok':True}
        p.pide=pide
        c={'objeto':json.dumps({'tipo':'tarea','ref':'task1'}),'cambio':json.dumps({'campo':'asignados','usuarios':['2']}),'clave':'key','quien':'ops'}
        p.aplicar(c)
        payload=calls[-1][2]['assignees']
        self.assertEqual(set(payload['add']),{2});self.assertEqual(set(payload['rem']),{1,3})
        self.assertFalse(S.aplicado(c,{'asignados':{'1','2'}}))
        self.assertTrue(S.aplicado(c,{'asignados':{'2'}}))
    def test_mock_rich_mentions_tags_y_marker_en_segunda_pagina(self):
        p=S.ProveedorClickUp();calls=[]
        def pide(m,r,b=None,**kw):
            calls.append((m,r,b))
            if m=='POST':return {'id':'comment123'}
            if '?' in r:return {'comments':[{'comment_text':'ro:key'}]}
            return {'comments':[{'date':i,'id':i,'comment_text':'otro'} for i in range(25,0,-1)]}
        p.pide=pide
        self.assertTrue(p.marca_comentario('task1','ro:key'))
        self.assertIn('start=1',calls[-1][1]);self.assertIn('start_id=1',calls[-1][1])
        c={'objeto':json.dumps({'tipo':'tarea','ref':'task1'}),'cambio':json.dumps({'campo':'comentario','texto':'Nueva versión','menciones':[{'usuario_clickup':'2'}]}),'clave':'key','quien':'ops'}
        p.aplicar(c)
        self.assertIn({'type':'tag','user':{'id':2}},calls[-1][2]['comment'])
    def test_pagina_truncada_no_prueba_ausencia(self):
        p=S.ProveedorClickUp();p.pide=lambda *a,**k:{'comments':[{'date':1,'id':1,'comment_text':'otro'}]*25}
        with self.assertRaises(S.ErrorSinc):p.marca_comentario('task1','ro:key')
    def test_outbound_failure_no_falso_confirmado(self):
        cam={'campo':'estado','valor':'diario'}
        cid,_=S.crear_cambio(self.c,clave='reintento',quien='a',canal='clickup',tipo='estado',objeto={'tipo':'tarea','ref':'task1','resuelto':True},cambio=cam,modo='real')
        p=S.ClickUpSimulado({'task1':{'estado':'antes','actualizado':None}}) if hasattr(S,'ClickUpSimulado') else None
        if p is None:
            p=next(cls for name,cls in vars(S).items() if isinstance(cls,type) and name!='Proveedor' and getattr(cls,'nombre',None)=='simulado')({'task1':{'estado':'antes','actualizado':None}})
        p.caida=True
        with patch.object(S,'avisar',lambda *a,**k:None):estado=S.ejecutar(self.c,cid,p)
        self.assertNotEqual(estado,'confirmado')
        self.assertEqual(S.estado_actual(self.c,cid)['estado'],'pendiente')

if __name__=='__main__':unittest.main()

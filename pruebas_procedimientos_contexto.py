"""134/143 propuestas genéricas: permisos y hashes con fixtures, sin proveedores/DB."""
import ast
import copy
import re
import time
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import procedimientos_contexto as PC


class Contexto(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.raiz = Path(self.tmp.name)
        self.cat = copy.deepcopy(PC.CATALOGO)
        for source in self.cat['precedence_guards'] + [r['source'] for r in self.cat['resources']]:
            p = self.raiz / source['path']
            p.parent.mkdir(parents=True, exist_ok=True)
            data = b'Fixture fuente generica sin contactos ni importes.\n'
            p.write_bytes(data)
            source['sha256'] = hashlib.sha256(data).hexdigest()
        self.patch = patch.object(PC, 'CATALOGO', self.cat)
        self.patch.start()
        self.real = {'id':'ana','puestos':['account'],'estado':'activo'}
        self.vista = self.real
        self.fila = {'id':'fixture123','persona_id':'ana','cli':'cliente-fixture'}
        self.cliente = {'id':'cliente-fixture','servicios':{'publicidad':'sí','crm_ghl':'sí','seo':'sí'}}
        self.S = SimpleNamespace(E=SimpleNamespace(crudo={'personas':[self.real],'clientes':[self.cliente]}), ve_alguno=lambda *a: True)
        self.P = SimpleNamespace(contexto=lambda *a: {}, ver=lambda *a: {'ok':True})
        self.payload = {'tarea':copy.deepcopy(self.fila),'fuente':'Copia local'}
        self.activo = lambda cid: cid=='cliente-fixture'

    def tearDown(self):
        self.patch.stop();self.tmp.cleanup()

    def dto(self, **extras):
        return PC.ampliar(self.payload, fila=self.fila, real=self.real, vista=self.vista, S=self.S, P=self.P, raiz=self.raiz, activo=self.activo, **extras)['procedimientos_ia']

    def test_5_curaciones_propuesta_no_autoseleccion(self):
        d = self.dto()
        self.assertEqual(len(d['opciones']),5)
        self.assertFalse(d['seleccion_automatica'])
        self.assertFalse(d['aprobacion_comercial'])
        self.assertEqual(d['binding'], {'tarea_id':'fixture123','persona_id':'ana','cliente_id':'cliente-fixture'})
        for p in d['opciones']:
            self.assertEqual(p['estado'],'propuesta')
            self.assertEqual(p['version'],'134.1.0')
            self.assertEqual(p['autoridad'],'datos_de_referencia')
            self.assertNotIn('approval',p)
            self.assertNotIn('path',p)
        text = json.dumps(d)
        self.assertNotIn('persona@example',text)
        self.assertNotIn(str(self.raiz),text)

    def test_sin_servicio_no_se_infiere_por_titulo_o_rol(self):
        self.fila['tarea']='SEO CRM Paid contratado todo'
        for valor in ('no','previsto','posible','TRUE',True,None):
            with self.subTest(valor=valor):
                self.cliente['servicios'] = {'publicidad':valor,'seo':valor,'crm_ghl':valor}
                self.assertEqual(self.dto()['opciones'],[])

    def test_paid_solo_servicio_confirmado_y_rol(self):
        self.real['puestos']=['trafficker']
        self.cliente['servicios']={'publicidad':'sí','seo':'sí','crm_ghl':'sí'}
        self.assertEqual([x['id'] for x in self.dto()['opciones']],['paid_preflight'])
        self.real['puestos']=['produccion']
        self.assertEqual(self.dto()['opciones'],[])

    def test_real_vista_modulo_cliente_activo_identidad(self):
        casos = ('cliente','modulo','activo','real_ajeno','persona_tarea')
        for caso in casos:
            with self.subTest(caso=caso):
                before = (self.P.ver,self.S.ve_alguno,self.activo,self.vista,dict(self.fila))
                if caso=='cliente':self.P.ver=lambda *a:{'ok':False}
                if caso=='modulo':self.S.ve_alguno=lambda *a:False
                if caso=='activo':self.activo=lambda *a:False
                if caso=='real_ajeno':self.vista={'id':'no-canonica','puestos':['account']}
                if caso=='persona_tarea':self.fila['persona_id']='ajena'
                self.assertEqual(self.dto()['opciones'],[])
                self.P.ver,self.S.ve_alguno,self.activo,self.vista,self.fila = before

    def test_vista_interseccion_roles_y_permiso(self):
        paid = {'id':'paid','puestos':['trafficker'],'estado':'activo'}
        self.S.E.crudo['personas'].append(paid)
        self.vista=paid
        self.assertEqual([x['id'] for x in self.dto()['opciones']],['paid_preflight'])
        self.P.ver=lambda p,*a:{'ok':p['id']!='paid'}
        self.assertEqual(self.dto()['opciones'],[])

    def test_hash_fuente_guarda_extracto_revocado(self):
        source = self.cat['resources'][0]['source']
        (self.raiz/source['path']).write_text('Fuente alterada')
        self.assertNotIn('paid_preflight',[x['id'] for x in self.dto()['opciones']])
        self.cat['resources'][1]['excerpt']['steps'].append('Dato adulterado')
        self.assertNotIn('crm_flow_check',[x['id'] for x in self.dto()['opciones']])
        (self.raiz/self.cat['precedence_guards'][0]['path']).write_text('Aviso cambiado')
        self.assertEqual(self.dto()['opciones'],[])

    def test_fuente_symlink_fuera_y_ausente(self):
        source = self.cat['resources'][0]['source']
        p=self.raiz/source['path'];p.unlink()
        self.assertNotIn('paid_preflight',[x['id'] for x in self.dto()['opciones']])
        p.symlink_to(self.raiz/self.cat['precedence_guards'][0]['path'])
        self.assertFalse(PC.fuente_integra(self.raiz,source))

    def test_contexto_endpoint_3_retornos_y_denegacion_antes_proveedor(self):
        tree=ast.parse(Path('mi_trabajo.py').read_text())
        node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='contexto_ia')
        fila={**self.fila,'descripcion':'Descripción local'}
        self.S.E.nucleo_bloqueado=False
        env={'S':self.S,'P':self.P,'MODULO':'mi-trabajo','re':re,'time':time,'_CTX_CACHE':{},
             'doc':lambda:{'tareas':[fila],'generado':'2026-10-03'},'ve_persona':lambda *a:True,
             'persona':lambda pid:self.real if pid==self.real['id'] else None,
             'contexto_operativo':lambda d:{'descripcion':d.get('descripcion','')},
             'ahora_utc':lambda:datetime(2026,10,3,tzinfo=timezone.utc)}
        exec(compile(ast.Module(body=[node],type_ignores=[]),'contexto_real','exec'),env)
        from fuentes_verdad import clientes_activos as ACT
        original=PC.ampliar
        def ampliar(*args,**kwargs):
            return original(*args,**kwargs,raiz=self.raiz,activo=self.activo)
        h=SimpleNamespace(responder=lambda s,b:(s,b))
        q={'tarea':['fixture123'],'persona':['ana']}
        llamadas=[]
        def lector(tid):
            llamadas.append(tid);return {'id':tid,'descripcion':'Descripción actual'}
        with patch.object(ACT,'es_activo_id',side_effect=lambda cid:self.activo(cid)),patch.object(PC,'ampliar',side_effect=ampliar):
            s,r=env['contexto_ia'](h,q,self.real,self.vista,lector=lector)
            self.assertEqual(s,200);self.assertEqual(len(r['procedimientos_ia']['opciones']),5)
            self.cliente['servicios']['publicidad']='no'
            s,r=env['contexto_ia'](h,q,self.real,self.vista,lector=lector)
            self.assertTrue(r['cache']);self.assertNotIn('paid_preflight',[x['id']for x in r['procedimientos_ia']['opciones']])
            self.assertEqual(len(llamadas),1)
            env['_CTX_CACHE'].clear()
            def fallo(_):raise RuntimeError('Token fixture NO revelar')
            s,r=env['contexto_ia'](h,q,self.real,self.vista,lector=fallo)
            self.assertEqual(r['fuente'],'Copia local');self.assertIn('procedimientos_ia',r)
            self.assertNotIn('Token fixture',json.dumps(r))
            for caso in ('inactivo','ajeno','desconocido','persona_ajena'):
                with self.subTest(caso=caso):
                    anterior=(self.activo,self.P.ver,dict(fila),env['ve_persona'])
                    if caso=='inactivo':self.activo=lambda *a:False
                    if caso=='ajeno':self.P.ver=lambda *a:{'ok':False}
                    if caso=='desconocido':fila['cli']='no-canonico'
                    if caso=='persona_ajena':env['ve_persona']=lambda *a:False
                    llamadas.clear()
                    self.assertEqual(env['contexto_ia'](h,q,self.real,self.vista,lector=lector)[0],403)
                    self.assertEqual(llamadas,[])
                    self.activo,self.P.ver,previa,env['ve_persona']=anterior
                    fila.clear();fila.update(previa)
            fila['cli']=None
            s,r=env['contexto_ia'](h,q,self.real,self.vista,lector=lector)
            self.assertEqual(s,200);self.assertEqual(r['procedimientos_ia']['opciones'],[])



if __name__=='__main__':unittest.main()

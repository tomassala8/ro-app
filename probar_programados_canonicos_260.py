"""Workers no arrancan: sólo funciones AST, catálogo sintético y publicador mock."""
import ast
import json
import types
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch
import escalado as ESC
from probar_escalado_canonico_260 import rows, person

AQUI = Path(__file__).parent

def cargar(ps, revocar=None):
    s = types.SimpleNamespace(E=types.SimpleNamespace(crudo={'personas':ps}))
    publicar = Mock(return_value=1)
    def vista(*args):
        if revocar:
            s.E.crudo['personas'] = revocar(s.E.crudo['personas'])
        return types.SimpleNamespace(canales={1}, ve_fila=lambda m: True)
    a = types.SimpleNamespace(Vista=vista, publicar=publicar)
    ns = dict(S=s, A=a, json=json, timedelta=timedelta,
              GENERADORES={'horas':(None,lambda *args:True)}, hecho=lambda *args:False,
              a_utc_txt=lambda t:t.isoformat(), corto=lambda pid:pid,
              canal_de_persona=lambda p:'avisos-fixture')
    tree = ast.parse((AQUI/'avisos_programados.py').read_text())
    nodes = [n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('jefe_de','escalar')]
    exec(compile(ast.Module(body=nodes,type_ignores=[]),'avisos_programados.py','exec'),ns)
    return ns, s, publicar

class Con:
    def __init__(self, destino=None, actor='owner'):
        self.m = {'clave':'prog:fixture:owner', 'datos':json.dumps({'escalar_a':destino}),
                  'menciones':json.dumps([actor]), 'ver':'null','id':3,'canal_id':1}
    def execute(self,sql,args):
        return types.SimpleNamespace(fetchall=lambda:[self.m],fetchone=lambda:None)

class Programados(unittest.TestCase):
    def setUp(self):
        p = patch.object(ESC,'config',lambda:ESC.POR_DEFECTO);p.start();self.addCleanup(p.stop)
    def run_escalar(self, ps, destino=None, actor='owner', revocar=None):
        ns, s, pub = cargar(ps,revocar)
        n = ns['escalar'](Con(destino,actor),{'id':'fixture','tipo':'horas','escalado':{'tras_horas':24}},datetime(2026,10,3))
        return n,pub
    def test_jefe_canonico_y_sin_fallback_inventado(self):
        ns,_,_ = cargar(rows())
        self.assertEqual(ns['jefe_de']({'id':'owner','jefe':'snapshot_ajeno'}),'head')
        for ps in [[], rows()+[person('owner')], [p for p in rows() if p['id'] not in ('head','mili')]]:
            ns,_,_ = cargar(ps);self.assertIsNone(ns['jefe_de']({'id':'owner'}))
    def test_destino_vigente_publicacion_mock(self):
        n,pub = self.run_escalar(rows(),'head');self.assertEqual(n,1);self.assertEqual(pub.call_count,1)
        self.assertEqual(pub.call_args.kwargs['menciones'],['head'])
    def test_destino_revocado_duplicado_ausente(self):
        for ps in [[{**p,'estado':'baja'} if p['id']=='head' else p for p in rows()],
                   [{**p,'activo':False} if p['id']=='head' else p for p in rows()],
                   rows()+[person('head')], [p for p in rows() if p['id']!='head']]:
            n,pub = self.run_escalar(ps,'head');self.assertEqual(n,0);pub.assert_not_called()
    def test_actor_revocado_y_no_final_automatico(self):
        for ps in [[p for p in rows() if p['id']!='owner'], rows()+[person('owner')],
                   [p for p in rows() if p['id']!='mili']]:
            n,pub = self.run_escalar(ps);self.assertEqual(n,0);pub.assert_not_called()
    def test_final_nominal_y_rol_actual(self):
        ps = [{**p,'puestos':['seo']} if p['id']=='tomas' else p for p in rows()]
        n,pub = self.run_escalar(ps,'tomas');self.assertEqual(n,0);pub.assert_not_called()
    def test_revocacion_durante_vista_antes_publicar(self):
        for cambio in [lambda ps:[{**p,'estado':'baja'} if p['id']=='head' else p for p in ps],
                       lambda ps:ps+[person('head')],
                       lambda ps:[{**p,'estado':'baja'} if p['id']=='owner' else p for p in ps]]:
            n,pub = self.run_escalar(rows(),'head',revocar=cambio);self.assertEqual(n,0);pub.assert_not_called()

if __name__ == '__main__': unittest.main()

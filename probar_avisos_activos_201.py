"""Avisos persistidos: AST de métodos reales y P actual; no BD/servidor/proveedor."""
import ast
import json
import types
import unittest
from pathlib import Path
from unittest.mock import patch
import permisos as P
from fuentes_verdad import clientes_activos as ACT


class AvisosActivos(unittest.TestCase):
 def setUp(self):
  self.real={'id':'direccion_fixture','puestos':['direccion'],'estado':'activo'}
  self.vista={'id':'account_fixture','puestos':['account'],'estado':'activo'}
  self.raw={'personas':[self.real,self.vista], 'clientes':[{'id':'propio','nombre':'Propio'},{'id':'ajeno','nombre':'Ajeno'}],
            'asignaciones':[{'cliente_id':'propio','persona_id':self.vista['id'],'silla':'account'}]}
  self.activos={'propio','ajeno'}
  pt=patch.object(ACT,'es_activo_id',side_effect=lambda c:c in self.activos);pt.start();self.addCleanup(pt.stop)
  arbol=ast.parse(Path(__file__).with_name('avisos.py').read_text());clase=next(n for n in arbol.body if isinstance(n,ast.ClassDef) and n.name=='Vista')
  fs=[n for n in arbol.body if isinstance(n,ast.FunctionDef) and n.name in ('puede_abrir_cliente','canales_de')]+[n for n in clase.body if isinstance(n,ast.FunctionDef) and n.name in ('cliente','ve_fila')]
  self.ns={'P':P,'S':types.SimpleNamespace(E=types.SimpleNamespace(crudo=self.raw)),'json':json,'deps_de':lambda*a:set(),'DEPARTAMENTOS':[],'TODOS_LOS_AVISOS':{'direccion','operaciones'},'directos_con_mensajes':lambda*a:['direct_fixture'],'meta_directo':lambda did,pid:{'id':did,'nombre':'Directo fixture','tipo':'directo'},'corto':lambda*a:'Actor fixture'}
  exec(compile(ast.Module(body=fs,type_ignores=[]),'avisos_real_AST','exec'),self.ns)
 def V(self,vista=None,real=None):
  p=vista or self.real;r=real or self.real
  v=types.SimpleNamespace(p=p,real=r,cp=P.contexto(p,self.raw),_cli={},como=p['id']!=r['id'],alertas={'alerta_fixture'})
  for n in ('cliente','ve_fila'):setattr(v,n,types.MethodType(self.ns[n],v))
  return v
 def mensaje(self,cid):return {'hilo_de':None,'cliente_id':cid,'ver':'{}'}
 def test_direccion_no_recupera_medalba_persistida(self):
  self.assertFalse(self.V().ve_fila(self.mensaje('medalba')))
 def test_cliente_ACT_y_canonico_autorizado_visible(self):
  self.assertTrue(self.V().ve_fila(self.mensaje('propio')))
 def test_unknown_o_act_sin_canonico_no_concede(self):
  self.activos.add('desconocido');self.assertFalse(self.V().ve_fila(self.mensaje('desconocido')))
 def test_canonico_sin_ACT_no_concede(self):
  self.activos.remove('propio');self.assertFalse(self.V().ve_fila(self.mensaje('propio')))
 def test_cliente_duplicado_falla_cerrado(self):
  self.raw['clientes'].append(dict(self.raw['clientes'][0]));self.assertFalse(self.V().ve_fila(self.mensaje('propio')))
 def test_vercomo_minimo_real_y_vista(self):
  v=self.V(vista=self.vista)
  self.assertTrue(v.ve_fila(self.mensaje('propio')));self.assertFalse(v.ve_fila(self.mensaje('ajeno')))
 def test_actor_inactivo_no_se_fia_snapshot(self):
  snapshot=dict(self.real);self.real['estado']='baja'
  self.assertFalse(self.V(real=snapshot).ve_fila(self.mensaje('propio')))
 def test_vista_inactiva_no_concede(self):
  snapshot=dict(self.vista);self.vista['estado']='baja'
  self.assertFalse(self.V(vista=snapshot).ve_fila(self.mensaje('propio')))
 def test_real_restringido_no_eleva_vista_direccion(self):
  self.assertFalse(self.V(vista=self.real,real=self.vista).ve_fila(self.mensaje('ajeno')))
 def test_identidad_duplicada_no_concede(self):
  self.raw['personas'].append(dict(self.real));self.assertFalse(self.V().ve_fila(self.mensaje('propio')))
 def test_alerta_general_sin_cliente_conservada(self):
  self.assertTrue(self.V().ve_fila(self.mensaje(None)))
 def test_revocacion_siguiente_vista_sin_cache_de_permiso_global(self):
  self.assertTrue(self.V().ve_fila(self.mensaje('propio')));self.activos.remove('propio');self.assertFalse(self.V().ve_fila(self.mensaje('propio')))

 def canales(self,p=None):
  p=p or self.real;grupos={cid:{'id':cid,'nombre':f'Grupo fixture {cid}','cliente_id':cliente,'creado_por':self.real['id']} for cid,cliente in [('grupo_medalba','medalba'),('grupo_activo','propio'),('grupo_ajeno','ajeno'),('grupo_general',None)]}
  ana={cid:{p['id']} for cid in grupos}
  return self.ns['canales_de'](p,None,(ana,grupos,set()))
 def test_metadata_canal_medalba_no_recupera_nombre(self):
  out=self.canales();self.assertNotIn('grupo_medalba',out);self.assertNotIn('medalba',json.dumps(out).lower());self.assertIn('grupo_activo',out)
 def test_canales_cliente_activo_minimo_vercomo(self):
  with P.mirando_como(self.real,self.raw):out=self.canales(self.vista)
  self.assertIn('grupo_activo',out);self.assertNotIn('grupo_ajeno',out);self.assertNotIn('grupo_medalba',out)
 def test_canales_globales_y_directos_no_alterados(self):
  out=self.canales();self.assertIn('general',out);self.assertIn('grupo_general',out);self.assertIn('direct_fixture',out)
 def test_canonico_antes_activo_revocado_no_canal_nativo(self):
  self.activos.remove('propio');out=self.canales();self.assertNotIn('cliente-propio',out);self.assertNotIn('grupo_activo',out)

 def test_canales_vercomo_revalida_real_actual_no_snapshot_hilo(self):
  snapshot=dict(self.real)
  with P.mirando_como(snapshot,self.raw):
   self.real['estado']='baja';out=self.canales(self.vista)
  self.assertNotIn('grupo_activo',out);self.assertNotIn('cliente-propio',out)

if __name__=='__main__':unittest.main()

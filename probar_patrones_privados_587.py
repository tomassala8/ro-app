"""587: prueba puerta real; fuente anterior explícita sólo para acreditar el fallo."""
import ast,copy,types,unittest
from unittest.mock import patch
import probar_almacenes_y_campos_586 as F

class Privados587(unittest.TestCase):
 def setUp(self):
    self.f=F.Almacenes586();self.f.setUp();self.addCleanup(self.f.tmp.cleanup)
 def get(self,path,real=None,vista=None):
    if real is None and vista is None:return self.f.get(path)
    # Crear sólo el almacén sintético; después invocar el mismo endpoint con identidades distintas.
    self.f.get(path)
    real=real or self.f.actor;vista=vista or real
    h=types.SimpleNamespace(responder=lambda c,d:(c,d))
    with F.P.mirando_como(real,self.f.raw):
      return self.f.ns['endpoint'](h,'/api/ver_dato',{'almacen':path,'ref':'ref-fixture','campo':'marca'},real,vista,F.P.contexto(vista,self.f.raw),real['id']!=vista['id'])
 def test_extras_antes_abiertos_ahora_denegados(self):
    anterior=ast.parse('''def config_almacen(almacen):
 import fnmatch
 for patron, conf in P.REGLAS.get("almacenes_privados", {}).items():
  if fnmatch.fnmatch(almacen, patron): return conf
 return None
''').body[0]
    legado=dict(self.f.ns);exec(compile(ast.Module(body=[anterior],type_ignores=[]),'legacy586-explicito','exec'),legado)
    for path in ('ventas_ro/_privado/setter_extra/otro/setter_fixture','agenda/_privado/otra/persona/setter_fixture'):
      self.assertIsNotNone(legado['config_almacen'](path))
      self.assertIsNone(self.f.ns['config_almacen'](path))
      self.assertEqual(self.get(path)[0],403)
 def test_propios_setter_y_agenda_siguen_abriendo(self):
    for path in ('ventas_ro/_privado/setter_fixture','agenda/_privado/setter_fixture'):
      c,d=self.get(path);self.assertEqual(c,200);self.assertEqual(d['valor'],'dato-sintetico')
 def test_ajenos_siguen_denegados(self):
    for path in ('ventas_ro/_privado/setter_ajeno','agenda/_privado/ajeno'):
      self.assertIsNotNone(self.f.ns['config_almacen'](path));self.assertEqual(self.get(path)[0],403)
 def test_vercomo_no_recupera_agenda_ajena(self):
    other={'id':'setter_otro','puestos':['setters'],'estado':'activo','activo':True}
    self.f.raw['personas'].append(other)
    self.assertEqual(self.get('agenda/_privado/setter_fixture',real=other,vista=self.f.actor)[0],403)
 def test_vercomo_sin_puesto_no_recupera_setter(self):
    other={'id':'account_fixture','puestos':['account'],'estado':'activo','activo':True}
    self.f.raw['personas'].append(other)
    self.assertEqual(self.get('ventas_ro/_privado/setter_fixture',real=other,vista=self.f.actor)[0],403)
 def test_todos_los_patrones_actuales_conservan_su_config(self):
    for pattern,conf in F.P.REGLAS['almacenes_privados'].items():
      self.assertIs(self.f.ns['config_almacen'](pattern.replace('*','fixture')),conf)
 def test_tipos_segmentos_vacios_y_relativos_no_acreditan(self):
    for path in (None,[],{},12,'','agenda/_privado//setter_fixture','agenda/_privado/../setter_fixture','agenda/_privado/./setter_fixture','/agenda/_privado/setter_fixture','agenda/_privado/setter_fixture/'):
      self.assertIsNone(self.f.ns['config_almacen'](path))
 def test_p_dinamico_no_se_elimina_ni_autoriza_por_prefijo(self):
    self.f.actor['id']='p_fixture'
    self.assertIsNotNone(self.f.ns['config_almacen']('agenda/_privado/p_fixture'))
    self.assertEqual(self.get('agenda/_privado/p_fixture')[0],200)
    self.assertEqual(self.get('agenda/_privado/p_otro')[0],403)
 def test_patron_de_varios_segmentos_exige_estructura_declarada(self):
    regla={'tipo':'solo_lo_tuyo','modulos':['agenda'],'dueno':'fichero'}
    with patch.dict(F.P.REGLAS['almacenes_privados'],{'fixture/_privado/grupo_*/p_*':regla}):
      self.assertIs(self.f.ns['config_almacen']('fixture/_privado/grupo_x/p_y'),regla)
      self.assertIsNone(self.f.ns['config_almacen']('fixture/_privado/grupo_x/extra/p_y'))
if __name__=='__main__':unittest.main()

import copy,sys,importlib.util,types,unittest
from pathlib import Path
from unittest.mock import patch
import consejo_metodo_308 as FIX
import permisos as P
HOY='2026-10-04'
POL={'regla':{'id':FIX.REGLA,'cadencia_dias':15,'responsable_role':'trafficker'},'clientes':[{'cliente_id':'c','estado_cohorte':'confirmada','cadencia_dias':15,'responsable_role':'trafficker','tipo_cohorte':'metodo_actual_recurrente'}]}
DOC={'reuniones':[{'evento_id':'e','fuente':'registro_local','cliente_id':'c','fecha':HOY,'celebrada':True,'cliente_confirmado':True,'rol_responsable_confirmado':'trafficker'}],'cobertura':{}}
def entorno():
 raw={'personas':[{'id':'ops','estado':'activo','activo':True,'puestos':['operaciones']},{'id':'paid','estado':'activo','activo':True,'puestos':['trafficker']}], 'clientes':[{'id':'c','activo':True,'estado':'activo'}], 'asignaciones':[{'persona_id':'paid','cliente_id':'c','silla':'trafficker','desde':'2026-09-01','principal':True,'confianza':'confirmada'}]}
 mods=P.cargar_modulos();s=types.SimpleNamespace(E=types.SimpleNamespace(crudo=raw,modulos=mods,nucleo_bloqueado=False),ACT=types.SimpleNamespace(es_activo_id=lambda cid:cid=='c'),P=types.SimpleNamespace(contexto=P.contexto,ver=P.ver,hoy_iso=lambda:HOY))
 s.ve_alguno=lambda p,ms:next((P.nivel_modulo(p,mods[m]) for m in ms if m in mods),None)
 return s,raw['personas'][0]
def lectura(path):return copy.deepcopy(POL if path==FIX.M.REGLAS else DOC)
class Metodo657(unittest.TestCase):
 def test_catalogo_baja_y_false_excluye(self):
  for cambio in ({'activo':False},{'estado':'baja'}):
   s,actor=entorno();s.E.crudo['clientes'][0].update(cambio)
   self.assertEqual(FIX._scope(s,actor,actor)[2],[])
 def test_roles_malformados_puro_no_confirma_owner(self):
  s,_=entorno();ps=s.E.crudo['personas'];asigs=s.E.crudo['asignaciones']
  for roles in ('no_trafficker',{'trafficker':True},['trafficker','trafficker'],['trafficker',{}]):
   ps[1]['puestos']=roles
   self.assertIsNone(FIX.responsable_confirmado('c','paid',ps,asigs,FIX.dia(HOY)))
 def test_rotacion_owner_durante_scope_final_no_publica_atribucion(self):
  for module in (FIX,):
   s,actor=entorno();original=module._scope;calls=0
   def scope(*args):
    nonlocal calls
    calls+=1
    if calls==2:s.E.crudo['personas'][1]['puestos']='no_trafficker'
    return original(*args)
   with patch.object(module,'_scope',side_effect=scope),patch.object(module.M,'leer',side_effect=lectura):out=module.leer_metodo308(s,actor,actor)
   self.assertIsNone(out)
 def test_rotacion_documento_celebracion_no_conserva_fecha(self):
  for module in (FIX,):
   s,actor=entorno();count=0
   def leer(path):
    nonlocal count
    if path==FIX.M.REGLAS:return copy.deepcopy(POL)
    count+=1;return copy.deepcopy(DOC if count==1 else {'reuniones':[],'cobertura':{}})
   with patch.object(module.M,'leer',side_effect=leer):out=module.leer_metodo308(s,actor,actor)
   self.assertIsNone(out)
 def test_legitimo_inmutable_sin_programar(self):
  s,actor=entorno()
  with patch.object(FIX.M,'leer',side_effect=lectura):a=FIX.leer_metodo308(s,actor,actor);b=FIX.leer_metodo308(s,actor,actor)
  self.assertEqual(a,b);m=b['_proyeccion_308'][0];self.assertEqual(m['responsable_id'],'paid');self.assertEqual(m['ultima_confirmada'],HOY);self.assertEqual(m['proxima_revision'],'2026-10-19');self.assertEqual(m['estado'],'preparar_seguimiento');self.assertIsNone(m['reunion_agendada'])
 def test_actor_invalid_no_io(self):
  s,actor=entorno();actor['puestos']='operaciones'
  with patch.object(FIX.M,'leer',side_effect=AssertionError('noIO')):self.assertIsNone(FIX.leer_metodo308(s,actor,actor))
if __name__=='__main__':unittest.main()

"""Pruebas del helper y de las funciones API reales extraídas por AST; sin importar ia/servir."""
import ast
import json
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
import unittest
from consejo_metodo_308 import normalizar_candidato_metodo308
from consejos_cartera_318 import normalizar_consejo_cartera318
from consejos_horas import neutralizar_consejo_horas as gate
from consejos_paid_crm_304 import neutralizar_consejo_paid_crm

HOY = "2026-10-03"
BASE = {"id": "al:fixture", "tipo": "rrhh_no_imputa", "dueno": "fixture", "quien": "Tú", "personal": True,
        "que": "Imputa las horas de ayer", "porque": "No imputaste horas el 02-10", "confianza": "alta",
        "criterio": {"regla": "disciplina", "texto": "Cumplimiento diario", "url": "https://example.test/anterior"},
        "prioridad": {"motivo": "Disciplina", "puntos": 180}, "motivo_orden": "Disciplina", "motivo_linea": "Primero por disciplina",
        "umbral": "8h", "metrica": None, "evidencia": [{"dato": "No imputó", "fecha": HOY}], "pantallas": ["horas"]}
M = {"persona_id": "fixture", "fuente": "ClickUp", "fecha_fuente": "2026-10-03 02:56", "cobertura": "parcial",
     "horas_registradas": 0, "periodo": {"desde": "2026-10-02", "hasta": "2026-10-02"}}


def funciones(*names):
    tree = ast.parse(Path(__file__).with_name('ia.py').read_text())
    return compile(ast.Module(body=[x for x in tree.body if isinstance(x, (ast.FunctionDef, ast.AsyncFunctionDef)) and x.name in names], type_ignores=[]), 'ia.py:AST183', 'exec')


class Horas(unittest.TestCase):
    def test_cache_local_existente_sin_exponer_datos(self):
        carpeta=Path(__file__).parent / "data" / "consejos"
        casos=[]
        for path in carpeta.glob("p_*.json"):
            casos.extend(c for c in json.loads(path.read_text()).get("candidatos",[]) if c.get("tipo")=="rrhh_no_imputa")
        if not casos:self.skipTest("Esta copia no contiene el aviso; el resto usa fixtures sintéticos.")
        for c in casos:
            nuevo=gate(c,HOY)
            self.assertEqual(nuevo["confianza"],"baja");self.assertIsNone(nuevo["criterio"])
            self.assertNotIn("No imputaste",nuevo["porque"]);self.assertIsNone(nuevo["metrica"])

    def test_precache_mismo_shape_no_acusa(self):
        c = gate(BASE, HOY)
        self.assertEqual(c['confianza'], 'baja');self.assertIsNone(c['criterio']);self.assertIsNone(c['metrica'])
        self.assertNotIn('No imputaste', c['porque']);self.assertIsNone(c['motivo_linea']);self.assertIsNone(c['prioridad'])
        self.assertIn('no acredita', c['porque']);self.assertIsNone(c['accion']);self.assertEqual(c['evidencia'], [])

    def test_no_mutacion_y_idempotencia(self):
        original = deepcopy(BASE);c=gate(BASE,HOY)
        self.assertEqual(BASE, original);self.assertEqual(gate(c,HOY),c)

    def test_zero_observado_no_no_trabajo(self):
        c=gate(dict(BASE,medicion_horas=M),HOY)
        self.assertIn('registra 0 h',c['porque']);self.assertIn('no una medición del trabajo realizado',c['porque'])
        self.assertEqual(c['medicion_horas']['horas_registradas'],0);self.assertEqual(c['confianza'],'baja')

    def test_positivo_no_jornada(self):
        c=gate(dict(BASE,medicion_horas=dict(M,horas_registradas=6.5,cobertura='completa')),HOY)
        self.assertIn('registra 6.5 h',c['porque']);self.assertIsNone(c['umbral'])

    def test_solo_tipo_canonico(self):
        c=dict(BASE,tipo='otra_regla');self.assertIs(gate(c,HOY),c)
        self.assertIsNone(gate(None,HOY))

    def test_descriptor_invalido(self):
        for change in [{'persona_id':'ajena'}, {'fuente':'texto libre'}, {'fecha_fuente':'2026-10-04'},
                       {'fecha_fuente':'2026-02-30'}, {'fecha_fuente':'2026-10-03 24:00'},
                       {'fecha_fuente':'2026-10-01'}, {'horas_registradas':-1}, {'horas_registradas':True},
                       {'horas_registradas':float('nan')}, {'horas_registradas':float('inf')},
                       {'cobertura':'desconocida'}, {'periodo':{}}, {'periodo':{'desde':'2026-10-02','hasta':'2026-10-04'}}]:
            with self.subTest(change=change):
                c=gate(dict(BASE,medicion_horas=dict(M,**change)),HOY);self.assertIsNone(c['medicion_horas']);self.assertEqual(c['evidencia'],[])

    def test_hoy_invalido(self):
        self.assertIsNone(gate(dict(BASE,medicion_horas=M),'mañana')['medicion_horas'])

    def test_descriptor_no_transporta_extras(self):
        c=gate(dict(BASE,medicion_horas=dict(M,secreto='fixture-no-real',periodo=dict(M['periodo'],otro='privado'))),HOY)
        self.assertNotIn('secreto',c['medicion_horas']);self.assertEqual(set(c['medicion_horas']['periodo']),{'desde','hasta'})

    def entorno(self):
        P=SimpleNamespace(ver=lambda *a:{'ok':True},enlace_seguro=lambda x:True,puestos_de=lambda p:set(p['puestos']))
        S=SimpleNamespace(ve_alguno=lambda p,ms:True,P=P,E=SimpleNamespace(modulos={'horas'},crudo={'clientes':[]}))
        MC=SimpleNamespace(ahora_madrid=lambda:datetime(2026,10,3),SIN_CONSEJO=set(),elegir=lambda cs,*a,**k:cs, retrasos=lambda *a:[])
        b={'S':S,'MC':MC,'normalizar_candidato_metodo308':normalizar_candidato_metodo308,'normalizar_consejo_cartera318':normalizar_consejo_cartera318,'leer_como':lambda *a:None,'neutralizar_consejo_horas':gate,'neutralizar_consejo_paid_crm':neutralizar_consejo_paid_crm,'_explicable':lambda *a:a[-1],'limpiar':lambda x:x,
           'CUOTA_GLOBAL':{'direccion'},'recortar_dinero':lambda p,cp,cid,c:c,'TAPA_COBRO':'fixture-tapa',
           '_con_valoraciones':lambda p,r,x:x,'estado_para':lambda p:{'conectada':True,'motivo':None,'modelo':'fixture'},
           'candidatos_al_momento':lambda *a:[],'para_quien':lambda p,c:c,'candidatos_de':lambda *a:{'candidatos':[deepcopy(BASE)],'generado':HOY},
           '_tabla_para':lambda *a:[],'_con_motivo':lambda x:x,'Denegado':RuntimeError,'MINUSCULA_INICIAL':set()}
        exec(funciones('_limpio_consejo','consejo'),b)
        return b

    def test_api_get_real_precache(self):
        b=self.entorno();p={'id':'fixture','puestos':['direccion']}
        c=b['consejo'](p,p,{},'horas')['consejos'][0]
        self.assertEqual(c['confianza'],'baja');self.assertIsNone(c['criterio']);self.assertNotIn('No imputaste',c['porque'])

    def test_api_cached_llm_retorno_no_reintroduce(self):
        b=self.entorno();p={'id':'fixture','puestos':['direccion']};captured=[]
        def llm(*args):
            captured.extend(args[-2]);return {'consejos':[{'ref':'al:fixture','que':'IMPUTA YA','porque':'No trabajaste ayer; disciplina'}],'modelo':'fixture','generado':HOY},False
        b['_con_ia']=llm
        c=b['consejo'](p,p,{},'horas',con_ia=True)['consejos'][0]
        self.assertEqual(c['que'],'Revisa los registros de horas en ClickUp');self.assertNotIn('No trabajaste',c['porque'])
        self.assertEqual(captured[0]['confianza'],'baja');self.assertIsNone(c['motivo_linea'])

    def test_ver_como_no_llama(self):
        b=self.entorno();b['_con_ia']=lambda *a:(_ for _ in ()).throw(AssertionError('no debe llamar'))
        p={'id':'fixture','puestos':['direccion']};real={'id':'otro','puestos':['direccion']}
        r=b['consejo'](real,p,{},'horas',con_ia=True)
        self.assertEqual(r['consejos'],[]);self.assertTrue(r['solo_lectura'])

    def test_api_otros_consejos_preservados(self):
        b=self.entorno();other=dict(BASE,tipo='prod_hoy',personal=False)
        b['candidatos_de']=lambda *a:{'candidatos':[other]};p={'id':'fixture','puestos':['direccion']}
        c=b['consejo'](p,p,{},'horas')['consejos'][0];self.assertEqual(c['confianza'],'alta');self.assertEqual(c['criterio'],other['criterio'])


if __name__=='__main__':unittest.main()

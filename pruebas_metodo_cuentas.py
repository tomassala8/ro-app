"""Metodología pura y proyección de privacidad, sin conexión ni envíos."""
import json
import unittest
from datetime import date
from types import SimpleNamespace
from unittest.mock import patch
import metodo_cuentas as M


class Metodo(unittest.TestCase):
    def setUp(self):
        self.hoy=date(2026,10,3)
        self.reglas={'regla':{'id':M.REGLA_ID,'cadencia_dias':15,'responsable_role':'trafficker'},'clientes':[{'cliente_id':'a','estado_cohorte':'confirmada','cadencia_dias':15,'responsable_role':'trafficker','tipo_cohorte':'metodo_actual_recurrente','precio_privado':1470,'texto_contrato':'secreto'}, {'cliente_id':'b','estado_cohorte':'pendiente'}]}
        self.ps={'p':{'id':'p','activo':True,'estado':'activo','puestos':['trafficker']},'p2':{'id':'p2','activo':True,'estado':'activo','puestos':['trafficker']},'acc':{'id':'acc','activo':True,'estado':'activo','puestos':['account']}}
        self.asig=[{'cliente_id':'a','persona_id':'p','silla':'trafficker','desde':'2026-09-01','hasta':None,'principal':True,'confianza':'confirmada'}, {'cliente_id':'a','persona_id':'acc','silla':'account','desde':'2026-09-01','hasta':None}]
    def calcular(self,eventos=None,cobertura=None,asig=None,puede=None):
        return M.sugerencias(self.reglas,self.asig if asig is None else asig,self.ps,eventos or [],cobertura or {},self.hoy,puede or (lambda cid:True))
    def reunion(self,fecha='2026-09-25',**extra):
        return {'evento_id':'reunion_fixture','cliente_id':'a','fecha':fecha,'celebrada':True,'cliente_confirmado':True,'rol_responsable_confirmado':'trafficker','fuente':'zoom',**extra}
    def test_cadencia15_con_trafficker_no_account(self):
        r=self.calcular()[0]
        self.assertEqual(r['cadencia_dias'],15);self.assertEqual(r['responsable_role'],'trafficker');self.assertEqual(r['responsable_id'],'p')
    def test_sin_evidencia_no_inventa_fecha_o_incumplimiento(self):
        r=self.calcular()[0]
        self.assertEqual(r['estado'],'sin_dato');self.assertIsNone(r['ultima_confirmada']);self.assertIsNone(r['proxima_revision']);self.assertIsNone(r['incumplimiento'])
    def test_ultimo_evento_confirmado_mas15(self):
        r=self.calcular([self.reunion()])[0]
        self.assertEqual(r['ultima_confirmada'],'2026-09-25');self.assertEqual(r['proxima_revision'],'2026-10-10');self.assertEqual(r['estado'],'en_cadencia')
    def test_no_cuenta_agendada_account_ambiguo_futuro_o_sin_fuente(self):
        for ev in [self.reunion(celebrada=False),self.reunion(rol_responsable_confirmado='account'),self.reunion(cliente_confirmado=False),self.reunion(fecha='2026-10-04'),self.reunion(fuente='')]:
            self.assertIsNone(self.calcular([ev])[0]['ultima_confirmada'])
    def test_recencia_antigua_feed_parcial_no_alarma_false(self):
        r=self.calcular([self.reunion('2026-09-01')])[0]
        self.assertEqual(r['estado'],'confirmar_recencia');self.assertIsNone(r['incumplimiento'])
    def test_feed_completo_confirma_revision_no_envio(self):
        r=self.calcular([self.reunion('2026-09-01')],{'completa':True,'desde':'2026-08-31','hasta':'2026-10-03'})[0]
        self.assertEqual(r['estado'],'revisar_cadencia');self.assertEqual(r['accion'],'proponer_seguimiento');self.assertIsNone(r['incumplimiento'])
    def test_responsable_ausente_ambiguo_futuro_baja_o_duda(self):
        cases=[[],[{**self.asig[0],'desde':'2026-10-04'}],[{**self.asig[0],'hasta':'2026-10-02'}],[{**self.asig[0],'duda':'pendiente'}],[self.asig[0],{**self.asig[0],'persona_id':'p2'}]]
        for asig in cases:self.assertEqual(self.calcular(asig=asig)[0]['estado'],'confirmar_responsable')
        self.ps['p']['estado']='baja';self.assertIsNone(self.calcular()[0]['responsable_id'])
    def test_scope_cohorte_y_privacidad_no_exporta_finanzas_o_documentos(self):
        self.assertEqual(len(self.calcular()),1)
        self.assertEqual(self.calcular(puede=lambda cid:False),[])
        r=self.calcular([self.reunion(fuente='contrato secreto cuota1470')])
        s=json.dumps(r)
        self.assertNotIn('1470',s);self.assertNotIn('secreto',s);self.assertNotIn('precio',s)
    def test_endpoint_interseccion_real_y_vista_y_cohorte_activa(self):
        class Handler:
            def responder(self,code,body):return code,body
            def _api_get(self,*args):return 'original'
        p=SimpleNamespace(REGLAS={},hoy_iso=lambda:'2026-10-03',contexto=lambda p,c:{},ver=lambda p,o,c:{'ok':p['id']=='real'})
        # La ruta452 reconstruye identidades actuales: un ID sólo en la petición no autoriza.
        crudo={'clientes':[{'id':'a'}],'personas':list(self.ps.values())+[
            {'id':'real','estado':'activo','puestos':['operaciones']},
            {'id':'otro','estado':'activo','puestos':['account']}],'asignaciones':self.asig}
        M.enganchar(Handler,SimpleNamespace(P=p,ACT=M.ACT,ve_alguno=lambda p,mods:'todo',E=SimpleNamespace(crudo=crudo,nucleo_bloqueado=False)))
        def lectura(path):
            if path==M.REGLAS:return self.reglas
            if path==M.REUNIONES:return {}
            return {'activos':[{'id':'a'}]}
        with patch.object(M,'leer',lectura), patch.object(M.ACT,'es_activo_id',lambda cid:cid=='a'):
            h=Handler();real={'id':'real'};otro={'id':'otro'}
            self.assertEqual(len(h._api_get('/api/metodo/sugerencias',{},real,real)[1]['sugerencias']),1)
            self.assertEqual(h._api_get('/api/metodo/sugerencias',{},real,otro)[1]['sugerencias'],[])
            self.assertEqual(h._api_get('/api/otra',{},real,real),'original')
    def test_registro_real_sin_coincidencias_legacy(self):
        reglas=M.leer(M.REGLAS)
        self.assertEqual(reglas['regla']['cadencia_dias'],15)
        confirmadas=[r for r in reglas['clientes'] if r['estado_cohorte']=='confirmada']
        self.assertEqual(len(confirmadas),14)
        self.assertNotIn('musashi-consultores',{r['cliente_id'] for r in confirmadas})
        self.assertNotIn('laver',{r['cliente_id'] for r in confirmadas})

if __name__=='__main__':unittest.main()

"""Caracterizaciones independientes; datos sintéticos, sin servidor ni DB."""
import copy
import unittest
from unittest.mock import patch
import metodo_cuentas as M
import consejo_metodo_308 as C
from probar_metodo_evidencia_452 import Evidencia452


class Revision473(unittest.TestCase):
    def setUp(self):
        self.f=Evidencia452();self.f.setUp()
    def tearDown(self):self.f.tearDown()

    def test_cliente_duplicado_conserva_sugerencia_pero_no_historial(self):
        self.f.S.E.crudo['clientes'].append(copy.deepcopy(self.f.S.E.crudo['clientes'][0]))
        code,d=self.f.get()
        self.assertEqual(code,200)
        self.assertEqual(d['sugerencias'],[])

    def test_owner_pendiente_no_trafficker_aceptado_en_base_no_en_308(self):
        raw=self.f.S.E.crudo
        raw['personas'][2]['puestos']=['account']
        raw['asignaciones'][1].update(confianza='pendiente',principal=False)
        code,d=self.f.get();self.assertEqual(code,200)
        self.assertIsNone(d['sugerencias'][0]['responsable_id'])
        p=C.proyectar_metodo308(d,['c1'],raw['personas'],raw['asignaciones'],'2026-10-04')
        self.assertEqual(len(p),1);self.assertFalse(p[0]['responsable_confirmado'])
        self.assertIsNone(p[0]['responsable_id'])

    def test_historial_no_se_convierte_en_celebracion_o_programacion(self):
        code,d=self.f.get();self.assertEqual(code,200)
        r=d['sugerencias'][0];e=r['evidencia_por_revisar']
        self.assertEqual(e['registros_historicos_observados'],1)
        self.assertIsNone(r['ultima_confirmada']);self.assertIsNone(r['proxima_revision'])
        self.assertIsNone(e['celebracion_confirmada'])
        self.assertIsNone(e['participacion_trafficker_confirmada'])
        p=C.proyectar_metodo308(d,['c1'],self.f.S.E.crudo['personas'],self.f.S.E.crudo['asignaciones'],'2026-10-04')
        self.assertIsNone(p[0]['reunion_agendada']);self.assertIsNone(p[0]['incumplimiento'])

    def test_owner_confirmado_positivo_y_retirado_si_duplicado(self):
        raw=self.f.S.E.crudo
        raw['asignaciones'][1].update(confianza='confirmada',principal=True)
        self.assertEqual(self.f.get()[1]['sugerencias'][0]['responsable_id'],'paid')
        raw['asignaciones'].append(copy.deepcopy(raw['asignaciones'][1]))
        self.assertIsNone(self.f.get()[1]['sugerencias'][0]['responsable_id'])

    def test_no_owner_alta_roles_malformados_o_no_principal(self):
        raw=self.f.S.E.crudo;a=raw['asignaciones'][1];p=raw['personas'][2]
        a.update(confianza='confirmada',principal=True)
        for roles in ('trafficker',['trafficker','trafficker'],[{}],[]):
            p['puestos']=roles
            # Proyección pura del owner; roles malformados actor no son necesarios.
            self.assertEqual(M.responsables('c1',[a],{'paid':p},M.dia('2026-10-04')),[])
        p['puestos']=['trafficker'];a['confianza']='alta'
        self.assertEqual(M.responsables('c1',[a],{'paid':p},M.dia('2026-10-04')),[])

    def test_fila_conflictiva_pendiente_dudosa_duplicada_o_fecha_invalida_no_se_omite(self):
        raw=self.f.S.E.crudo;a=raw['asignaciones'][1];p=raw['personas'][2]
        a.update(confianza='confirmada',principal=True)
        for cambio in ({'persona_id':'otra','confianza':'pendiente'}, {'duda':True}, {},
                       {'desde':'invalida'},{'hasta':'invalida'}):
            b={**a,**cambio}
            self.assertEqual(M.responsables('c1',[a,b],{'paid':p},M.dia('2026-10-04')),[])

    def test_cobertura_futura_no_revision_de_cadencia_acreditada(self):
        raw=self.f.S.E.crudo;raw['asignaciones'][1].update(confianza='confirmada',principal=True)
        ev=dict(cliente_id='c1',fecha='2026-09-01',celebrada=True,cliente_confirmado=True,
                rol_responsable_confirmado='trafficker',fuente='zoom')
        doc={'reuniones':[ev],'cobertura':{'completa':True,'desde':'2026-08-01','hasta':'2026-10-05'}}
        with patch.object(M,'leer',side_effect=lambda path:self.f.regla if path==M.REGLAS else doc):
            code,d=self.f.get();self.assertEqual(code,200)
            self.assertEqual(d['sugerencias'][0]['estado'],'confirmar_recencia')

    def test_cliente_activo_false_baja_y_vista_sin_cartera_excluidos(self):
        c=self.f.S.E.crudo['clientes'][0]
        for flags in ({'activo':False},{'estado':'baja'}):
            saved=copy.deepcopy(c);c.update(flags)
            self.assertEqual(self.f.get()[1]['sugerencias'],[])
            c.clear();c.update(saved)
        self.f.S.E.crudo['asignaciones']=[a for a in self.f.S.E.crudo['asignaciones'] if a['silla']!='account']
        self.assertEqual(self.f.get(actor='ops',vista='account')[1]['sugerencias'],[])

    def test_cobertura_string_no_completa_y_payload_malformado_no500(self):
        for doc in ([],{'reuniones':{'fecha':'2026-01-01'},'cobertura':'false'},
                    {'reuniones':[None,'texto',1],'cobertura':{'completa':'false'}}):
            def leer(path):return self.f.regla if path==M.REGLAS else doc
            with patch.object(M,'leer',side_effect=leer):
                code,d=self.f.get();self.assertEqual(code,200)
                self.assertIs(d['cobertura_reuniones']['completa'],False)
                self.assertIsNone(d['sugerencias'][0]['ultima_confirmada'])


if __name__=='__main__':unittest.main()

import copy
import json
import unittest
from unittest.mock import patch
import operaciones_registros_272 as C
import mediciones_fotos_329 as M
from probar_control_operaciones_272 import Control,foto

class Fotos329(Control):
    def test_scope_actual_sin_fotos_y_no_permiso(self):
        self.assertEqual(self.lista('mili','mili')['scope_foto_actual'],C.alcance(self.S,'mili','mili')[0])
        self.assertIsNone(self.lista()['scope_foto_actual'])
        self.raw['personas'].append(copy.deepcopy(self.raw['personas'][0]))
        with self.assertRaises(C.O.ErrorRegistro):self.lista()
    def test_scope_revocado_y_cambio_durante_lectura(self):
        old=self.lista('mili','mili')['scope_foto_actual']
        self.S.ACT.es_activo_id=lambda cid:False
        self.assertNotEqual(self.lista('mili','mili')['scope_foto_actual'],old)
        original=C.alcance
        count=[0]
        def changing(*args):
            out=original(*args);count[0]+=1
            return (out[0] if count[0]==1 else 'b'*64,out[1])
        with patch.object(C,'alcance',side_effect=changing):
            with self.assertRaises(C.O.ErrorRegistro) as e:self.lista('mili','mili')
            self.assertEqual(e.exception.codigo,409)
    def fuentes(self):
        self.docs['alertas/p_mili']['generado']='2026-10-03T08:00:00Z'
        p=self.docs['produccion/produccion']['proyectos'][0]
        p.update(rev_account=0)
        p['revisiones_account'].update(fuente='flujo',fecha='2026-10-03T08:00:00Z')
    def test_futuros_descriptor_exactos_legacy_no(self):
        r=self.guardar(foto(),'mili','mili')['recibo'];self.assertEqual(r['mediciones_329'],[])
        self.fuentes();r=self.guardar(foto(),'mili','mili')['recibo'];ms={m['id']:m for m in r['mediciones_329']}
        self.assertEqual(set(ms),{'rojas','revision48'});self.assertEqual(ms['revision48']['valor'],0)
        self.assertFalse(ms['rojas']['completa']);self.assertEqual(ms['rojas']['periodo'],{'tipo':'stock'})
        self.assertNotIn('own',json.dumps(ms));self.assertEqual(self.lista('mili','mili')['registros'][0],r)
    def test_cohorte_cambia_y_corte_sin_zona_unknown(self):
        self.fuentes();a=C.capturar(self.S,'mili','mili')['mediciones_329'][0]
        self.docs['alertas/p_mili']['alertas'][0]['id']='other';b=C.capturar(self.S,'mili','mili')['mediciones_329'][0]
        self.assertNotEqual(a['cohorte_hash'],b['cohorte_hash']);self.assertEqual(a['scope_hash'],b['scope_hash'])
        self.docs['alertas/p_mili']['generado']='2026-10-03 08:00';self.assertFalse(any(m['id']=='rojas' for m in C.capturar(self.S,'mili','mili')['mediciones_329']))
    def test_count_incoherente_y_source_no_flujo_no_descriptor(self):
        self.fuentes();p=self.docs['produccion/produccion']['proyectos'][0];p['rev_account_48']=1
        self.assertFalse(any(m['id']=='revision48' for m in C.capturar(self.S,'mili','mili')['mediciones_329']))
        p['rev_account_48']=0;p['revisiones_account']['fuente']='other'
        self.assertFalse(any(m['id']=='revision48' for m in C.capturar(self.S,'mili','mili')['mediciones_329']))
    def test_empty_population_no_descriptor_legacy_decodes(self):
        self.fuentes();self.docs['alertas/p_mili']['alertas']=[]
        self.assertFalse(any(m['id']=='rojas' for m in C.capturar(self.S,'mili','mili')['mediciones_329']))
        d=C.capturar(self.S,'mili','mili');d.pop('mediciones_329')
        raw={'tipo':'foto','revision':1,'contenido':json.dumps(d),'hora':'2026-10-03T10:00:00+00:00','objeto':'x','actor':'mili'}
        self.assertNotIn('mediciones_329',C.decodificar(raw))
    def test_descriptor_tamper_decoding_reject(self):
        self.fuentes();d=C.capturar(self.S,'mili','mili');d['mediciones_329'][0]['valor']=999
        row={'tipo':'foto','revision':1,'contenido':json.dumps(d),'hora':'2026-10-03T10:00:00+00:00','objeto':'x','actor':'mili'}
        with self.assertRaises(C.O.ErrorRegistro):C.decodificar(row)

if __name__=='__main__':unittest.main()

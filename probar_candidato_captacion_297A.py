import copy
import importlib.util
import json
import unittest
from pathlib import Path

APP=Path(__file__).resolve().parent
P=APP.parent/'RECUPERACION_CODEX_2026-10-03/preparar_captacion_297A.py'
spec=importlib.util.spec_from_file_location('candidato297A',P);M=importlib.util.module_from_spec(spec);spec.loader.exec_module(M)


def fila(cid):
    return {'cliente_id':cid,'severidad':'ok','severidad_torre_reglas':'ok','cuello':['integracion'],
            'nombre':'Fixture','motivos':[{'texto':'Meta no llegó','nivel':'critico'}],'avisos':[],
            'leads':{'7d':0},'gasto':{'7d':22.1},'serie':[{'d':'2026-10-02','meta':[1,2]}],
            'despacho':{'leads_meta_7d':0,'leads_ghl_7d':3,'contactos_historia':4,
                        'sin_estado_14d':0,'pct_llegan_crm':80,'fuga':'leve','subcuenta_sin_uso':True},
            'coste_por_cita':{'alarma_100':True,'coste_por_cita_14d':150},
            'quincenal':{'periodo':['2026-09-19','2026-10-02'],'coste_por_cita_14d':150,'citas_14d':1}}


class Candidate(unittest.TestCase):
    def data(self):return {'generado':'2026-10-02 13:20','captacion_generado':'2026-10-02 12:00',
                           'datos_hasta':'2026-10-01','resumen':{'por_gravedad':{'ok':2}},'clientes':[fila('a'),fila('b')]}
    def test_no_mutacion_y_whitelist(self):
        d=self.data();antes=copy.deepcopy(d);c,indices,diff=M.preparar(d,{'a'},['a','b'])
        self.assertEqual(d,antes);self.assertEqual(indices,{0})
        self.assertTrue(all(M.permitida(p,indices)for p in diff))
        for k in ('leads','gasto','serie','generado','datos_hasta'):
            if k in d:self.assertEqual(c[k],d[k])
            else:self.assertEqual(c['clientes'][0][k],d['clientes'][0][k])
        self.assertEqual(c['clientes'][1],d['clientes'][1])
    def test_original_cero_no_nueva_observacion(self):
        c,_,_=M.preparar(self.data(),{'a'},['a','b']);d=c['clientes'][0]['despacho']
        self.assertEqual(d['leads_meta_7d'],0);self.assertEqual(d['sin_estado_14d'],0)
        self.assertFalse(d['medicion_integracion']['observacion_acreditada'])
        self.assertEqual(d['medicion_integracion']['meta_estado'],'referencia_legacy')
    def test_duplicado_o_missing_rechazados(self):
        d=self.data();d['clientes'].append(fila('a'))
        with self.assertRaises(ValueError):M.preparar(d,{'a'},['a'])
        d=self.data();d['clientes'][0].pop('cliente_id')
        with self.assertRaises(ValueError):M.preparar(d,{'a'},['a'])
    def test_act_no_amplia_canonicos_ni_google(self):
        d=self.data();d['clientes'][1]['solo_google']=True
        c,indices,_=M.preparar(d,{'a','b'},['a','a','b'])
        self.assertFalse(indices);self.assertEqual(c['clientes'],d['clientes'])
    def test_sin_cohorte_no_alarm(self):
        c,_,_=M.preparar(self.data(),{'a'},['a','b']);f=c['clientes'][0]
        self.assertEqual(f['severidad'],'ok');self.assertEqual(f['estado_evaluacion'],'referencia_legacy_no_recalculada');self.assertIsNone(f['despacho']['fuga'])
        self.assertFalse(f['coste_por_cita']['alarma_100']);self.assertEqual(f['coste_por_cita']['coste_por_cita_14d'],150)
        self.assertIsNone(f['quincenal']['coste_por_cita_14d']);self.assertEqual(f['quincenal']['coste_por_cita_referencia_14d'],150)
    def test_alertas_ajenas_no_filtradas_ni_reordenadas(self):
        d=self.data();r=d['clientes'][0]
        r['motivos']=[{'clase_id':'paid','nivel':'critico','texto':'Creatividad fixture'},
                      {'clase_id':'integracion','nivel':'atencion','texto':'Conexion fixture'}]
        r['avisos']=[{'clase_id':'integracion','texto':'Aviso fixture1'},
                     {'clase_id':'paid','texto':'Aviso fixture2'}]
        c,_,_=M.preparar(d,{'a'},['a','b']);nuevo=c['clientes'][0]
        self.assertEqual(nuevo['motivos'],r['motivos'])
        self.assertEqual(nuevo['avisos'][:-1],r['avisos'])
        self.assertEqual(nuevo['cuello'],r['cuello'])
        self.assertEqual(nuevo['severidad'],r['severidad'])
        self.assertEqual(c['resumen'],d['resumen'])
        self.assertNotIn('diagnosticos_legacy',nuevo)
        self.assertNotIn('avisos_legacy',nuevo)

    def test_diff_cuenta_identidad_no_admitido(self):
        self.assertFalse(M.permitida(('clientes',0,'cliente_id'),{0}))
        self.assertFalse(M.permitida(('clientes',0,'despacho','leads_meta_7d'),{0}))
        self.assertFalse(M.permitida(('generado',),{0}))
        self.assertFalse(M.permitida(('clientes',0,'motivos'),{0}))
        self.assertFalse(M.permitida(('clientes',0,'severidad'),{0}))
        self.assertFalse(M.permitida(('clientes',0,'cuello'),{0}))
        self.assertFalse(M.permitida(('resumen','por_gravedad','ok'),{0}))
    def test_determinista(self):
        a=M.preparar(self.data(),{'a'},['a','b']);b=M.preparar(self.data(),{'a'},['a','b'])
        self.assertEqual(M.sha(M.canon(a[0])),M.sha(M.canon(b[0])))
        self.assertEqual(a[2],b[2])
    def test_deposito_privado_actual_integridad(self):
        out=APP.parent/'RECUPERACION_CODEX_2026-10-03/staging_captacion_297A'
        m=json.loads((out/'manifest.json').read_bytes())
        self.assertEqual(M.sha((out/'captacion.json').read_bytes()),m['candidato_sha256'])
        self.assertEqual(out.stat().st_mode&0o777,0o700)
        for f in ('captacion.json','manifest.json'):self.assertEqual((out/f).stat().st_mode&0o777,0o600)
        for item in m['inputs'].values():self.assertEqual(M.sha(Path(item['ruta']).read_bytes()),item['sha256'])


if __name__=='__main__':unittest.main()

import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock,patch
from despliegue.empaquetado import copiar_privado,PRIVADOS_REQUERIDOS
from despliegue.arranque_privado import preparar,iniciar,lanzamiento

class Arranque(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup)
        self.root=Path(self.t.name).resolve();self.code=self.root/'codigo';self.code.mkdir()
        (self.code/'servir.py').write_text('# fixture: nunca ejecutado\n')
        (self.code/'config.py').write_text('# fixture\n')
        (self.code/'reglas_permisos.json').write_text('{}')
        self.source=self.root/'fuentes';self.source.mkdir()
        for r in PRIVADOS_REQUERIDOS:
            p=self.source/r;p.parent.mkdir(parents=True,exist_ok=True)
            row={'fixture':r,'id':'fixture'}
            payload=[row] if r in ('data/personas.json','data/clientes.json','data/asignaciones.json','data/alarmas.json') else row
            p.write_text(json.dumps(payload))
        for r in ('fuentes_seo/_cache/gsc.json','fuentes_seo/contextos_confirmados.json'):
            p=self.source/r;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('{"fixture_seo":true}')
        self.bundle=self.root/'bundle';copiar_privado(self.source,self.bundle,self.code)
        self.sha=hashlib.sha256((self.bundle/'manifiesto_privado.json').read_bytes()).hexdigest()
        self.runtime=self.root/'runtime'
    def preparar(self):return preparar(self.code,self.bundle,self.runtime,self.sha)
    def test_lecturas_con_aqui_en_app_y_fuentes_privadas(self):
        r=self.preparar();aqui=self.runtime/'app'
        for rel in PRIVADOS_REQUERIDOS:
            payload=json.loads((aqui/rel).read_text());row=payload[0] if isinstance(payload,list) else payload
            self.assertEqual(row['fixture'],rel)
        self.assertTrue(json.loads((aqui/'fuentes_seo/_cache/gsc.json').read_text())['fixture_seo'])
        self.assertFalse(r['listo_para_desplegar']);self.assertFalse(r['reutilizado'])
        self.assertFalse((self.code/'data').exists())
    def test_reinicio_sin_duplicar_escribir_ni_perder_db(self):
        self.preparar();db=self.runtime/'estado'/'piloto.db';db.write_bytes(b'fixture')
        before={p.relative_to(self.runtime).as_posix():(p.read_bytes(),p.stat().st_mtime_ns) for p in self.runtime.rglob('*') if p.is_file()}
        self.assertTrue(self.preparar()['reutilizado'])
        after={p.relative_to(self.runtime).as_posix():(p.read_bytes(),p.stat().st_mtime_ns) for p in self.runtime.rglob('*') if p.is_file()}
        self.assertEqual(before,after)
    def test_incompleto_o_ajeno_preservado(self):
        self.runtime.mkdir();p=self.runtime/'conservar';p.write_text('original')
        with self.assertRaises((OSError,ValueError)):self.preparar()
        self.assertEqual(p.read_text(),'original')
    def test_fuente_codigo_marca_y_extras_tampering(self):
        self.preparar()
        for path in (self.runtime/'app'/PRIVADOS_REQUERIDOS[0],self.runtime/'app'/'servir.py',self.runtime/'privado'/'hidratacion_completa.json'):
            b=path.read_bytes();path.write_bytes(b'{}')
            with self.assertRaises(ValueError):self.preparar()
            path.write_bytes(b)
        extra=self.runtime/'app'/'data'/'extra.json';extra.write_text('{}')
        with self.assertRaises(ValueError):self.preparar()
    def test_bundle_invalido_no_crea_runtime(self):
        (self.bundle/PRIVADOS_REQUERIDOS[0]).write_text('{}')
        with self.assertRaises(ValueError):self.preparar()
        self.assertFalse(self.runtime.exists())
    def test_forma_nuclear_invalida_aun_con_bundle_firmado(self):
        p=self.bundle/'data/personas.json';p.write_text('{}');b=p.read_bytes()
        mp=self.bundle/'manifiesto_privado.json';m=json.loads(mp.read_text())
        e=next(e for e in m['ficheros'] if e['ruta']=='data/personas.json')
        e.update(bytes=len(b),sha256=hashlib.sha256(b).hexdigest());mp.write_text(json.dumps(m))
        self.sha=hashlib.sha256(mp.read_bytes()).hexdigest()
        with self.assertRaises(ValueError):self.preparar()
        self.assertFalse(self.runtime.exists())
    def test_entorno_cerrado_y_comando_local(self):
        self.preparar()
        with patch.dict(os.environ,{'DATABASE_URL':'fixture','PORT':'123','RO_MODO':'servidor','RO_CLICKUP_REAL':'si','GHL_TOKEN':'fixture'}):
            launch=lanzamiento(self.runtime,8779)
        env=launch['env'];self.assertEqual(env['RO_PILOTO_LECTURA'],'1')
        self.assertEqual(env['RO_CLICKUP_REAL'],'no');self.assertEqual(env['RO_ENVIOS_REALES'],'no')
        self.assertEqual(env['RO_AVISOS_SIN_BUCLE'],'1')
        for k in ('DATABASE_URL','PORT','RO_MODO','GHL_TOKEN','HOME'):self.assertNotIn(k,env)
        for k in ('RO_DB','RO_ANCLAS','RO_LISTA_ACCESS','RO_DEPARTAMENTOS','RO_CORREOS_ENTRADA','RO_RECARGA_CONFIG'):
            self.assertEqual(Path(env[k]).parent,self.runtime/'estado')
        self.assertEqual(env['RO_COPIA_R2'],'no');self.assertEqual(env['RO_MODULAR_ACCESO'],'no')
        self.assertNotIn('--bind',launch['args'])
    def test_inicio_inyectado_valida_antes_ejecutar(self):
        run=Mock(return_value='sin servidor real')
        self.assertEqual(iniciar(self.code,self.bundle,self.runtime,self.sha,ejecutor=run),'sin servidor real')
        self.assertEqual(run.call_count,1)
        (self.runtime/'app'/'servir.py').write_text('# alterado')
        with self.assertRaises(ValueError):iniciar(self.code,self.bundle,self.runtime,self.sha,ejecutor=run)
        self.assertEqual(run.call_count,1)
    def test_destino_en_origen_y_puertos_no_validos(self):
        with self.assertRaises(ValueError):preparar(self.code,self.bundle,self.code/'runtime',self.sha)
        self.preparar()
        for port in (True,80,70000,'8772'):
            with self.assertRaises(ValueError):lanzamiento(self.runtime,port)
    def test_destino_symlink_no_modifica_objetivo(self):
        target=self.root/'target';target.mkdir();self.runtime.symlink_to(target)
        with self.assertRaises(ValueError):self.preparar()
        self.assertEqual(list(target.iterdir()),[])

if __name__=='__main__':unittest.main()

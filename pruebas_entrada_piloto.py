import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

APP = Path(__file__).resolve().parent

class EntradaPiloto(unittest.TestCase):
    def correr(self, flag, comando='web'):
        with tempfile.TemporaryDirectory(prefix='ro-entrada-') as t:
            p = Path(t).resolve(); (p/'despliegue').mkdir()
            shutil.copyfile(APP/'piloto_lectura.py', p/'piloto_lectura.py')
            shutil.copyfile(APP/'despliegue/entrada.sh', p/'despliegue/entrada.sh')
            stub = 'from pathlib import Path\nPath("%s").write_text("llamado")\n'
            (p/'servir.py').write_text(stub % 'servidor')
            (p/'despliegue/publicacion.py').write_text(stub % 'descarga')
            (p/'despliegue/tuberia.py').write_text(stub % 'tuberia')
            env = dict(os.environ, HOME=str(p), RO_PILOTO_LECTURA=flag,
                       DATABASE_URL='fixture_sin_red', GHL_PIT_NEW='fixture_sin_credencial')
            r = subprocess.run(['sh', 'despliegue/entrada.sh',comando], cwd=p, env=env,
                               capture_output=True, timeout=10)
            return r.returncode, {x: (p/x).exists() for x in
                ('servidor','descarga','tuberia','RO_BANDEJA_GHL/config/ghl.env')}

    def test_piloto_no_descarga_ni_prepara_credenciales(self):
        for flag in ('1','valor_desconocido'):
            c, hechos = self.correr(flag)
            self.assertEqual(c,0)
            self.assertEqual(hechos, {'servidor':True,'descarga':False,'tuberia':False,
                                    'RO_BANDEJA_GHL/config/ghl.env':False})

    def test_piloto_no_lanza_tareas_ni_comandos_alternativos(self):
        for cmd in ('ligera','completa','noche','otro'):
            c, hechos = self.correr('1',cmd)
            self.assertEqual(c,1); self.assertFalse(any(hechos.values()))

    def test_modo_normal_conserva_descarga(self):
        c, hechos = self.correr('no')
        self.assertEqual(c,0); self.assertTrue(hechos['descarga'])
        self.assertTrue(hechos['servidor']); self.assertTrue(hechos['RO_BANDEJA_GHL/config/ghl.env'])

if __name__ == '__main__': unittest.main()

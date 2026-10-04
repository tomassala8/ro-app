"""Fixtures de credenciales, sin secretos reales; aplica puerta real a JSON temporal."""
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from contexto_tarea import texto_operativo,contexto_operativo
from escaner_secretos import escanear_fichero

CASOS = [
 'clave: Fixture9_Sensible', 'pass = Fixture9_Sensible', 'pwd: Fixture9_Sensible',
 'passwd: Fixture9_Sensible', 'contraseña:\n| Fixture9_Sensible |',
 '**clave**: `Fixture9_Sensible`', 'password="Fixture9_Sensible"',
 'sk-'+'X'*20, 'AKIA'+'A'*16, 'ghp_'+'X'*31,
 'eyJ'+'a'*12+'.'+'b'*12+'.'+'c'*12,
 'Bearer '+'Q'*30,
 'https://example.test/path?key=Fixture9_Sensible&view=normal',
 'pit-12345678-1234-1234-1234-123456789abc',
 'xoxb-'+'X'*20, 'AIza'+'X'*31, 'EAA'+'X'*41,
]

class Briefs(unittest.TestCase):
 def test_patterns_all_secret_values_removed_scanner_zero(self):
  textos=[contexto_operativo({'description':'Acción útil\n'+x+'\nPreparar informe'})['descripcion'] for x in CASOS]
  with TemporaryDirectory() as d:
   p=Path(d)/'mi_trabajo.json';p.write_text(json.dumps({'tareas':[{'descripcion':t} for t in textos]}))
   found=escanear_fichero(p)
   self.assertEqual(len(found),0,'El detector real todavía encuentra credenciales (valores ocultos)')
  for texto in textos:
   self.assertIn('Acción útil',texto);self.assertIn('Preparar informe',texto)
   self.assertNotIn('Fixture9_Sensible',texto)
 def test_benign_clave_seo_not_blanket_removed(self):
  for texto in ['Analizar palabra clave SEO y su intención.','La clave del proyecto es contrastar datos.','Definir palabras clave; revisar pass-through del embudo.','Clave: SEO']:
   self.assertEqual(texto_operativo(texto),texto)
 def test_multiline_label_cannot_leave_following_value(self):
  texto=texto_operativo('Intro\nclave:\n| `Fixture9_Sensible` |\nCierre')
  self.assertNotIn('Fixture9_Sensible',texto);self.assertIn('Cierre',texto)
 def test_existing_contacts_money_script_and_url_guards_retained(self):
  t=texto_operativo('Objetivo útil\nana@example.test +34 612 345 678 presupuesto 5000\n<script>NO_SCRIPT</script>\nhttps://user:Fixture9_Sensible@example.test/x?plain=algo#frag')
  for v in ('ana@example.test','612 345 678','5000','NO_SCRIPT','Fixture9_Sensible','?plain=','#frag'):self.assertNotIn(v,t)
 def test_repeated_sanitization_stable_for_public_briefs(self):
  for x in CASOS:
   one=texto_operativo(x);self.assertEqual(texto_operativo(one),one)
 def test_limit_and_pure_original_input(self):
  raw={'description':'Texto útil\nclave: Fixture9_Sensible\n'+'a'*14000};out=contexto_operativo(raw)
  self.assertIn('Fixture9_Sensible',raw['description']);self.assertNotIn('Fixture9_Sensible',out['descripcion']);self.assertLessEqual(len(out['descripcion']),12000);self.assertTrue(out['descripcion_truncada'])

if __name__=='__main__':unittest.main()

"""Sólo AST de funciones puras; no importa el lector ni usa tokens/proveedores."""
import ast
import importlib.util
from pathlib import Path
import unittest

APP=Path(__file__).resolve().parent
def funcion(p):
    tree=ast.parse(p.read_text());fn=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='leads_de')
    namespace={};exec(compile(ast.Module(body=[fn],type_ignores=[]),str(p),'exec'),namespace);return namespace['leads_de']

class SemanticaProductores(unittest.TestCase):
    def test_legados_suman_variantes_sin_prueba_eventos_unicos(self):
        filas=[{'action_type':'onsite_conversion.lead_grouped','value':'10'},{'action_type':'offsite_conversion.fb_pixel_lead','value':'10'}]
        for p in [APP/'fuentes/f_meta_directo.py',Path('/Users/tomassala/RO_HERRAMIENTAS/captacion/captacion.py')]:
            f=funcion(p);self.assertEqual(f(filas),20);self.assertEqual(f([{'action_type':'lead','value':'10'},*filas]),10)
    def test_purchase_no_es_contado_por_esas_funciones(self):
        for p in [APP/'fuentes/f_meta_directo.py',Path('/Users/tomassala/RO_HERRAMIENTAS/captacion/captacion.py')]:
            self.assertEqual(funcion(p)([{'action_type':'purchase','value':'5353'}]),0)
    def test_220_no_suma_variantes_y_conserva_tipo(self):
        spec=importlib.util.spec_from_file_location('meta285',APP/'fuentes_paneles/meta_mediciones_220.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
        rows=[{'action_type':'onsite_conversion.lead_grouped','value':'10'},{'action_type':'offsite_conversion.fb_pixel_lead','value':'10'}]
        self.assertEqual(m.leads(rows),(10,'onsite_conversion.lead_grouped'));self.assertEqual(m.leads([{'action_type':'purchase','value':'5353'}]),(None,None))
        d=m.fila({'date_start':'2026-10-02','date_stop':'2026-10-02','actions':rows},'2026-10-03','account')
        self.assertEqual(d['medicion']['tipo_lead'],'onsite_conversion.lead_grouped');self.assertEqual(d['leads'],10)

if __name__=='__main__':unittest.main()

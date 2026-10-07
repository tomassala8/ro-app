"""Inventario real de código y drybundle pequeño sintético; no servidor, fuentes PII ni proveedores."""
import ast
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from despliegue.empaquetado import (plan_codigo,copiar_codigo,copiar_privado,PRIVADOS_REQUERIDOS,
                                   PRIVADOS_OPCIONALES,disponibilidad_fuentes,FUENTES_POR_FUNCION)
from despliegue.hidratar_privado import hidratar

APP=Path(__file__).parent
NUEVOS=('consejos_horas.py','mi_trabajo_proyeccion.py','evidencias_kpi.py','evidencias_kpi_api.py',
        'informe_word.py','informe_word_api.py','agenda_zoom_api.py','fuentes_agenda/duplicados.py',
        'fuentes_produccion/estados_catalogo.py','modulos/_seo_mediciones.js','modulos/_informe_word.js')
OPCIONALES=('indicadores.json','fuentes_consejos/conocimiento/reglas.json','fuentes_consejos/conocimiento/tipos.json',
            'fuentes_consejos/conocimiento/puestos.json','fuentes_produccion/_privado/_cache/tareas.json',
            'fuentes_produccion/_privado/_cache/estados_listas.json','fuentes_produccion/_privado/_cache/tablero_tareas.json',
            'fuentes_contratos/_privado/indice_documentos.json')

class Bundle185(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory(prefix='ro_185_');self.addCleanup(self.t.cleanup)
        self.base=Path(self.t.name).resolve();self.app=self.base/'app';self.app.mkdir()

    def poner(self,r,data):
        p=self.app/r;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(data)

    def nuclear(self):
        for r in PRIVADOS_REQUERIDOS:self.poner(r,'[]' if r in ('data/personas.json','data/clientes.json','data/asignaciones.json','data/alarmas.json') else '{}')

    def test_dependencia_word_declarada(self):
        tree=ast.parse((APP/'informe_word_api.py').read_text())
        logo=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='logo_png')
        self.assertTrue(any(isinstance(x,ast.ImportFrom) and x.module=='PIL' for x in ast.walk(logo)))
        deps=(APP/'despliegue/requirements.txt').read_text()
        self.assertRegex(deps,r'(?m)^Pillow>=11\.3,<12\s')

    def test_inventario_actual_modulos_nuevos_sin_leer_fuentes(self):
        plan=set(plan_codigo(APP))
        self.assertTrue(set(NUEVOS)<=plan)
        self.assertFalse(set(OPCIONALES)&plan)
        self.assertTrue({'schema_v2.sql','despliegue/Dockerfile','despliegue/requirements.txt','despliegue/entrada.sh'}<=plan)

    def test_imports_python_locales_presentes(self):
        plan=set(plan_codigo(APP));locales={Path(r).stem:r for r in plan if r.endswith('.py') and '/' not in r}
        vistos=set()
        for r in ('servir.py','ia.py','permisos.py','fuentes_verdad/clientes_activos.py',*NUEVOS):
            if not r.endswith('.py'):continue
            for x in ast.walk(ast.parse((APP/r).read_text())):
                mods=[i.name.split('.')[0] for i in x.names] if isinstance(x,ast.Import) else [x.module.split('.')[0]] if isinstance(x,ast.ImportFrom) and x.module else []
                for mod in mods:
                    if mod in locales:visto=locales[mod];vistos.add(visto);self.assertIn(visto,plan)
        self.assertIn('consejos_horas.py',vistos);self.assertIn('mi_trabajo_proyeccion.py',vistos)

    def test_imports_js_relativos_reales_presentes(self):
        plan=set(plan_codigo(APP));n=0
        for r in plan:
            if not r.endswith('.js'):continue
            for src in re.findall(r'^import\b[\s\S]*?from\s+[\'"]([^\'"]+)[\'"]\s*;', (APP/r).read_text(),re.M):
                if not src.startswith('.'):continue
                target=(APP/r).parent.joinpath(src).resolve()
                self.assertIn(APP.resolve(),target.parents)
                self.assertIn(target.relative_to(APP.resolve()).as_posix(),plan);n+=1
        self.assertGreater(n,50)

    def test_dry_codigo_copia_modulos_reales_no_datos(self):
        for r in NUEVOS:
            self.poner(r,(APP/r).read_text())
        self.poner('servir.py','"""fixture no inicia servidor"""')
        for r in OPCIONALES:self.poner(r,'{"fixture_privada":true}')
        out=self.base/'codigo';copiar_codigo(self.app,out)
        self.assertTrue(all((out/r).is_file() for r in NUEVOS))
        self.assertFalse(any((out/r).exists() for r in OPCIONALES))
        for r in NUEVOS:
            if r.endswith('.py'):compile((out/r).read_text(),str(out/r),'exec')
        # Importa sólo helpers revisados sin I/O a nivel de módulo; nunca ia/servir/apis ni conectores.
        subprocess.run([sys.executable,'-I','-c',
            'import sys;sys.path.insert(0,sys.argv[1]);import consejos_horas,mi_trabajo_proyeccion,informe_word,evidencias_kpi;from fuentes_agenda import duplicados;from fuentes_produccion import estados_catalogo',str(out)],check=True,capture_output=True)

    def test_privados_exactos_hidratan_separados(self):
        self.nuclear()
        for r in OPCIONALES:self.poner(r,'{"fixture_privada":true}')
        self.poner('data/mi_trabajo/mi_trabajo.json','{"tareas":[]}')
        self.poner('fuentes_produccion/_privado/otro.json','{"no_autorizado":true}')
        self.poner('fuentes_contratos/_privado/documento.pdf','fixture-no-documento')
        privado=self.base/'privado';codigo=self.base/'codigo'
        out=copiar_privado(self.app,privado,codigo)
        self.assertTrue(all((privado/r).is_file() for r in OPCIONALES))
        self.assertFalse((privado/'fuentes_produccion/_privado/otro.json').exists())
        self.assertFalse((privado/'fuentes_contratos/_privado/documento.pdf').exists())
        self.assertTrue(all(v['estado']=='presente_sin_validar' and v['operativo_verificado'] is False for v in out['funciones_fuentes'].values()))
        huella=hashlib.sha256((privado/'manifiesto_privado.json').read_bytes()).hexdigest()
        h=self.base/'hidratado';r=hidratar(privado,h,huella,codigo_destino=codigo)
        self.assertFalse(r['listo_para_desplegar'])
        for ruta in OPCIONALES:
            self.assertEqual((h/ruta).read_bytes(),(privado/ruta).read_bytes());self.assertEqual((h/ruta).stat().st_mode&0o777,0o600)

    def test_ausencias_por_funcion_no_silenciosas(self):
        self.nuclear();out=copiar_privado(self.app,self.base/'privado',self.base/'codigo')
        self.assertFalse(out['listo_para_desplegar'])
        for nombre,rutas in FUENTES_POR_FUNCION.items():
            estado=out['funciones_fuentes'][nombre]
            self.assertEqual(estado['estado'],'fuente_ausente');self.assertTrue(estado['faltantes'])
        manifest=json.loads((self.base/'privado/manifiesto_privado.json').read_text())
        self.assertEqual(out['funciones_fuentes'],manifest['funciones_fuentes'])

    def test_presencia_no_disponibilidad_ni_ejecucion(self):
        out=disponibilidad_fuentes([p for xs in FUENTES_POR_FUNCION.values() for p in xs])
        self.assertTrue(all(x['estado']=='presente_sin_validar' and not x['operativo_verificado'] for x in out.values()))

    def test_optional_symlink_no_copia(self):
        self.nuclear();p=self.app/OPCIONALES[0];p.symlink_to(self.app/'data/meta.json')
        with self.assertRaises(ValueError):copiar_privado(self.app,self.base/'privado',self.base/'codigo')
        self.assertFalse((self.base/'privado').exists())

    def test_knowledge_no_entrada_amplia(self):
        self.assertTrue(set(OPCIONALES)<=set(PRIVADOS_OPCIONALES))
        self.assertNotIn('fuentes_ia/cerebro_respuestas/ejemplos.json',PRIVADOS_OPCIONALES)
        self.assertNotIn('fuentes_consejos/conocimiento/reglas_minadas.json',PRIVADOS_OPCIONALES)

    def test_checkpoint_rutas_arranque_incluidas_sin_privados(self):
        # Predicado original extraído AST: no ejecutar el escritor ZIP/checkpoint real.
        script=APP.parent/'RECUPERACION_CODEX_2026-10-03/actualizar_checkpoint_codigo.py'
        tree=ast.parse(script.read_text());expr=next(x.value for x in tree.body if isinstance(x,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='files' for t in x.targets))
        self.poner('schema_v2.sql','fixture');self.poner('despliegue/entrada.sh','fixture');self.poner('despliegue/requirements.txt','fixture');self.poner('consejos_horas.py','fixture')
        asignaciones={t.id:x.value for x in tree.body if isinstance(x,ast.Assign) for t in x.targets if isinstance(t,ast.Name)}
        extras=ast.literal_eval(asignaciones['ARCHIVOS_ARRANQUE']);excluir=ast.literal_eval(asignaciones['excluir'])
        for r in extras:self.poner(r,'fixture')
        self.poner('fuentes_crm/_privado/oculto.py','no-copiar')
        self.poner('fuentes_consejos/conocimiento/reglas.json','no-copiar')
        self.poner('data/privado.json','no-copiar')
        files=eval(compile(ast.Expression(expr),str(script),'eval'),{'APP':self.app,'excluir':excluir,'ARCHIVOS_ARRANQUE':extras})
        paths={p.relative_to(self.app).as_posix() for p in files}
        self.assertIn('consejos_horas.py',paths)
        self.assertTrue(extras<=paths);self.assertNotIn('fuentes_crm/_privado/oculto.py',paths);self.assertNotIn('data/privado.json',paths);self.assertNotIn('fuentes_consejos/conocimiento/reglas.json',paths)
        self.assertTrue(extras<=set(plan_codigo(APP)))

if __name__=='__main__':unittest.main()

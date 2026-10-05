"""Auditoría estática de alcance. No ejecuta HTML, módulos, datos ni proveedores."""
import hashlib
import json
import re
import unittest
from pathlib import Path

APP=Path(__file__).resolve().parent
R=APP.parent/'RECUPERACION_CODEX_2026-10-03'
ORIGINAL=Path('/Users/tomassala/Downloads/PANEL_OPERACIONES_2026-10-01/plantilla.html')
MAPA={'vDia':'_operaciones_dia_direccion_265.js','vFuegos':'_operaciones_fuegos_268.js','vCierre':'_cierre_artifact_253.js',
'vRastro':'_operaciones_dia_direccion_265.js','vScore':'_operaciones_accounts_263.js','vEquipo':'operaciones.js',
'vEquipoNotas':'_operaciones_notas_equipo_281.js','vBandeja':'_operaciones_bandeja_270.js','vHoras':'_operaciones_equipo_262.js',
'vEncargos':'_operaciones_registros_272.js','vEquipoDia':'_operaciones_equipo_262.js','vProduccion':'produccion.js',
'vTomas':'_operaciones_dia_direccion_265.js','vLeadsFb':'_operaciones_feedback_273.js','vTriaje':'_operaciones_bandeja_270.js',
'vResumen':'_operaciones_resumen_274.js','vAccMini':'_operaciones_resumen_274.js','vControl':'_operaciones_accounts_263.js',
'vPasos':'_operaciones_resumen_274.js','vAnomalias':'_operaciones_anomalias_276.js','vPlanificacion':'_operaciones_equipo_262.js',
'vPuesto':'_operaciones_rituales_264.js','vAlertaPersonas':'_operaciones_equipo_262.js','vTiposTarea':'_operaciones_equipo_262.js',
'vInformeYBajas':'_operaciones_dia_direccion_265.js','vHoy':'_operaciones_accounts_263.js','vClientes':'_operaciones_accounts_263.js',
'vFichas':'_operaciones_fichas_nuevos_271.js','vAccounts':'_operaciones_accounts_263.js','vNuevos':'_operaciones_fichas_nuevos_271.js',
'vViernes':'_operaciones_rituales_264.js','vInc':'_operaciones_incongruencias_278.js','vRepartir':'_operaciones_rituales_264.js',
'abrirFicha':'ficha.js'}
ORD=['dia','bandeja','equipo','produccion','fuegos','fichas','clientes','nuevos','accounts','puesto','tomas','cierre','rastro','hoy','viernes','incongruencias','repartir']


def inventario():
    s=ORIGINAL.read_text();base=json.loads((R/'matriz_aceptacion_artifact_284.json').read_bytes())
    defs=list(re.finditer(r'(?m)^(?:async )?function\s+(\w+)\([^\n]*',s));secciones={}
    for i,m in enumerate(defs):secciones[m[1]]=s[m.start():defs[i+1].start()if i+1<len(defs)else len(s)]
    filas=[]
    for old in base['funciones']:
        nombre=old['funcion'];trozo=secciones[nombre];p=APP/'modulos'/MAPA[nombre]
        filas.append({**old,'implementacion_actual':str(p.relative_to(APP)),
                      'sha_implementacion':hashlib.sha256(p.read_bytes()).hexdigest(),
                      'umbrales_originales_expresiones':list(dict.fromkeys(re.findall(r'[\w.()]+\s*(?:>=|<=|===|>|<)\s*\d+(?:\.\d+)?',trozo))),
                      'rangos_originales_mencionados':list(dict.fromkeys(re.findall(r'\b\d+\s*(?:h|d[ií]as|meses|minutos|s|%)\b',trozo))),
                      'acciones_originales':list(dict.fromkeys(re.findall(r'data-([a-z][a-z0-9-]+)=',trozo))),
                      'nota_301':'Mapa estático, no certifica datos, permisos, interacción ni apariencia equivalente.'})
    return {'version':'301.1','original_sha256':hashlib.sha256(ORIGINAL.read_bytes()).hexdigest(),
            'orden_tabs':ORD,'grupos_originales':[['Hoy',['dia','bandeja']],['Equipo',['equipo','produccion']],
            ['Clientes',['fichas','fuegos','clientes','nuevos','accounts']],['Dirección',['puesto','tomas','cierre','rastro']],
            ['Más',['hoy','viernes','incongruencias','repartir']]],'funciones':filas}


class Inventory(unittest.TestCase):
    def test_34_funciones_sin_omision(self):
        i=inventario();self.assertEqual(len(i['funciones']),34)
        self.assertEqual({r['funcion']for r in i['funciones']},set(MAPA))
        self.assertEqual(i['original_sha256'],'468e796d0dab7e8b366ba37c97d0a1e1c7b93b9e82e79ea967ccd6aefa2e01a5')
    def test_17_tabs_en_mismo_orden(self):
        s=(APP/'modulos/operaciones.js').read_text()
        tramo=s.split('APARTADOS_OPERACIONES = [',1)[1].split('];',1)[0]
        self.assertEqual(re.findall(r"\['([^']+)'",tramo),ORD)
    def test_secciones_compuestas_y_dinamicas_no_ocultas(self):
        f={r['funcion']:r for r in inventario()['funciones']}
        self.assertTrue(f['vEquipoDia']['cabecera_dinamica'])
        self.assertEqual(len(f['vProduccion']['cabeceras_estaticas']),21)
        self.assertIn('Cerradas ayer',f['vEquipoDia']['cabeceras_estaticas'])
        self.assertEqual(f['vTiposTarea']['cabeceras_estaticas'],['Tipo de tarea','Casos','Mediana','Máximo','Horas totales'])
        self.assertIn('Cómo',f['vRastro']['cabeceras_estaticas'])
    def test_umbral_original_no_sustituido_por_regla_actual(self):
        f={r['funcion']:r for r in inventario()['funciones']}
        self.assertIn('f.pct>130',f['vCierre']['umbrales_originales_expresiones'])
        self.assertIn('s.rompen>=3',f['vPlanificacion']['umbrales_originales_expresiones'])
        self.assertIn('v>=80',f['vScore']['umbrales_originales_expresiones'])


if __name__=='__main__':
    import sys
    if '--guardar' in sys.argv:
        p=R/'inventario_artifact_301.json';p.write_text(json.dumps(inventario(),ensure_ascii=False,indent=2));p.chmod(0o600)
        print('Inventario:17tabs/34funciones, sólo metadatos fuente y hashes.')
    else:unittest.main()

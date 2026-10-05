import ast
from pathlib import Path
source = Path(__file__).resolve().parent / 'fuentes_captacion' / 'anuncios_meta.py'
tree = ast.parse(source.read_text())
formulas = [v for node in ast.walk(tree) if isinstance(node, ast.Dict) for k,v in zip(node.keys,node.values) if isinstance(k,ast.Constant) and k.value == 'ctr']
assert len(formulas)==1
formula=compile(ast.Expression(formulas[0]),'<formula_productor_real>','eval')
assert eval(formula,{'f':{'clicks':2,'impressions':1},'round':round}) == 200.0
assert eval(formula,{'f':{'clicks':0,'impressions':1},'round':round}) == 0.0
assert eval(formula,{'f':{'clicks':2,'impressions':0},'round':round}) == 0.0 # legado no acredita denominador; UI rechaza explícito0
print('3 casos fórmula productor real682 PASS: clicks totales no únicos, cero y denominador legado0')

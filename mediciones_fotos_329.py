"""Descriptores futuros de copia, sin IO ni alteración de fotos históricas."""
import datetime as dt
import hashlib
import json
import math
import re

UNIDADES={'rojas':'alarmas','revision48':'tareas'}
DEFINICIONES={'rojas':'329.1:alertas_unicas_gravedad_rojo:stock_parcial',
              'revision48':'329.1:proyectos_unicos_revision_account_mas48:flujo:stock_parcial'}

def huella(x):
    return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def instante(x):
    if not isinstance(x,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})',x):return None
    try:
        d=dt.datetime.fromisoformat(x.replace('Z','+00:00'))
        return d if d.tzinfo and d.utcoffset() is not None else None
    except ValueError:return None

def descriptor(id,valor,ids,corte,leido,scope):
    a,b=instante(corte),instante(leido)
    if (id not in UNIDADES or type(valor)is not int or valor<0 or a is None or b is None or a>b
        or not isinstance(scope,str) or not re.fullmatch('[a-f0-9]{64}',scope)
        or not isinstance(ids,list) or not ids or any(not isinstance(x,str) or not x for x in ids) or len(set(ids))!=len(ids)):return None
    return {'version':'329.1','id':id,'valor':valor,'validado_servidor':True,'origen':'medicion_copia',
            'scope_hash':scope,'cohorte_hash':huella(sorted(ids)),'definicion_hash':huella(DEFINICIONES[id]),
            'unidad':UNIDADES[id],'completa':False,'corte':corte,'leido':leido,'periodo':{'tipo':'stock'}}

def validar(m,scope,valores):
    if not isinstance(m,dict):return False
    base=descriptor(m.get('id'),m.get('valor'),['validacion'],m.get('corte'),m.get('leido'),scope)
    if base is None or set(m)!=set(base) or valores.get(m['id'])!=m['valor']:return False
    return all(m[k]==base[k] for k in base if k!='cohorte_hash') and isinstance(m['cohorte_hash'],str) and re.fullmatch('[a-f0-9]{64}',m['cohorte_hash']) is not None

"""Metadatos privados mínimos de tareas. Puro; ningún texto/contacto/link se copia.
No catálogo semántico: el ID del campo y el tipo no prueban que sea Sprint/Área/Entregable.
"""
import re
from collections import Counter

ID=re.compile(r'^[A-Za-z0-9_-]{1,120}$')
TIPOS={'drop_down','labels','checkbox','date','number','currency','url','text','short_text','users','email','phone','location','rating','emoji','manual_progress','automatic_progress','formula','tasks','list_relationship','signature'}

def identificador(x):
    if isinstance(x,bool):return None
    s=str(x) if isinstance(x,(str,int)) else ''
    return s if ID.fullmatch(s) else None

def coleccion(t,k,limite,fn):
    if k not in t:return None,{'estado':'ausente','leidos':None,'observados':None}
    xs=t[k]
    if not isinstance(xs,list):return None,{'estado':'invalido','leidos':None,'observados':None}
    # No elegir primera fila ante IDs duplicados. Counter sólo opera el lote acotado.
    lote=xs[:limite];ids=[identificador(x.get('id')) if isinstance(x,dict) else None for x in lote];n=Counter(ids)
    out=[]
    for x,eid in zip(lote,ids):
        if eid is None or n[eid]!=1:continue
        fila=fn(x)
        if fila is not None:out.append(fila)
    parcial=len(xs)>limite or len(out)!=len(xs)
    return out,{'estado':'parcial' if parcial else 'observado','leidos':len(out),'observados':len(xs)}

def opcion(o):
    d={'id':identificador(o['id'])}
    orden=o.get('orderindex')
    if isinstance(orden,int) and not isinstance(orden,bool) and 0<=orden<10000:d['orderindex']=orden
    return d

def campo(f):
    tipo=f.get('type');tipo=tipo if isinstance(tipo,str) else None
    d={'id':identificador(f['id']),'type':tipo if tipo in TIPOS else 'no_soportado'}
    conf=f.get('type_config')
    if isinstance(conf,dict) and tipo in ('drop_down','labels'):
        opts,cob=coleccion(conf,'options',200,opcion)
        d['opciones_cobertura']=cob
        if opts is not None:d['type_config']={'options':opts}
    # required es una propiedad observada, no una regla global ni nombre inferido.
    if isinstance(f.get('required'),bool):d['required']=f['required']
    if 'value' not in f:d['valor_estado']='ausente';return d
    v=f['value']
    if v is None or v=='' or v==[]:d.update(value=None,valor_estado='vacio');return d
    if tipo=='checkbox' and isinstance(v,bool):d.update(value=v,valor_estado='preservado')
    elif tipo in ('drop_down','labels'):
        opts=(d.get('type_config') or {}).get('options') or []
        if d.get('opciones_cobertura',{}).get('estado')!='observado':d['valor_estado']='sin_catalogo'
        elif tipo=='drop_down' and sum((isinstance(v,int) and not isinstance(v,bool) and o.get('orderindex')==v) or (isinstance(v,str) and o['id']==v) for o in opts)==1:d.update(value=v,valor_estado='preservado')
        elif tipo=='labels' and isinstance(v,list) and len(v)<=200 and all(isinstance(x,str) and any(o['id']==x for o in opts) for x in v) and len(set(v))==len(v):d.update(value=list(v),valor_estado='preservado')
        else:d['valor_estado']='sin_catalogo'
    else:d['valor_estado']='omitido_privacidad'
    return d

def item(i):
    d={'id':identificador(i['id'])}
    if isinstance(i.get('resolved'),bool):d['resolved']=i['resolved']
    return d

def checklist(c):
    d={'id':identificador(c['id'])};xs,cob=coleccion(c,'items',1000,item);d['items_cobertura']=cob
    if xs is not None:d['items']=xs
    return d

def solo_id(x):return {'id':identificador(x['id'])}

def preservar(t, *, ampliacion_operativa=False, catalogo_entregable=None):
    if not isinstance(t,dict):raise ValueError('Tarea inválida.')
    out={};cob={}
    for k,lim,fn in [('custom_fields',200,campo),('checklists',100,checklist),('attachments',200,solo_id),('watchers',200,solo_id)]:
        xs,c=coleccion(t,k,lim,fn);cob[k]=c
        if xs is not None:out[k]=xs
    # La descripción permanece exclusivamente en contexto_operativo, ya saneada.
    claves=[k for k in ('descripcion','description','text_content') if k in t]
    elegida=next((k for k in ('descripcion','description','text_content') if t.get(k)),None)
    estado='observado' if elegida and isinstance(t[elegida],str) else ('invalido' if elegida else ('vacio' if claves and all(t[k] is None or t[k]=='' for k in claves) else ('invalido' if claves else 'ausente')))
    cob['descripcion']={'estado':estado,'fuente':elegida}
    out['metadata_cobertura']=cob
    if ampliacion_operativa is True:
        try:
            from .metadata_operativa_229 import ampliar
        except ImportError:
            from metadata_operativa_229 import ampliar
        return ampliar(t,out,catalogo_entregable)
    return out

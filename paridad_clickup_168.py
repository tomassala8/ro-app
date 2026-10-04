"""Adaptador puro candidato. Catálogo y alcance provienen del servidor autorizado.
No importa lectores, no lee archivos/red, no ejecuta textos de tareas y no escribe ClickUp.
"""
import re
from urllib.parse import urlsplit,unquote

ID=re.compile(r'^[A-Za-z0-9_-]{1,100}$')
CAMPOS=('sprint_mes','entregable_final','area_clickup')

def ident(v):
    if isinstance(v,bool):return None
    s=str(v) if isinstance(v,(str,int)) else ''
    return s if ID.fullmatch(s) else None

def desconocido(motivo):return {'estado':'sin_dato','valor':None,'motivo':motivo}

def equivalentes(a,b):return type(a) is type(b) and a==b

def valor_campo(v,c):
    if v is None or v=='':return {'estado':'sin_valor','valor':None,'motivo':'Campo leído sin valor; no demuestra incumplimiento.'}
    tipo=c.get('tipo')
    if tipo=='seleccion':
        opciones=c.get('opciones')
        if not isinstance(opciones,list):return desconocido('Opciones no contrastadas.')
        coincidencias=[o for o in opciones if isinstance(o,dict) and equivalentes(o.get('valor_api'),v)]
        if len(coincidencias)!=1:return desconocido('Valor ausente o ambiguo en el catálogo de esta lista.')
        etiqueta=coincidencias[0].get('etiqueta')
        # Sólo etiqueta de catálogo explícito; nunca el texto libre/name de la tarea.
        if not isinstance(etiqueta,str) or not 1<=len(etiqueta)<=80 or re.search(r'[\x00-\x1f@€$£]|(?:token|secret|password)\s*[:=]|\b\d+(?:[.,]\d+)?\s*(?:EUR|USD)\b',etiqueta,re.I):return desconocido('Etiqueta no apta para esta proyección.')
        return {'estado':'observado','valor':etiqueta,'motivo':'Selección por ID y catálogo exacto de la lista; no periodo inferido.'}
    if tipo=='url':
        if not isinstance(v,str) or len(v)>600 or re.search(r'[\x00-\x20\x7f]',v):return desconocido('Referencia inválida.')
        try:
            u=urlsplit(v);hosts=c.get('hosts')
            path=unquote(u.path)
            if u.scheme!='https' or not isinstance(hosts,list) or u.hostname not in hosts or u.username or u.password or u.port not in (None,443) or u.query or u.fragment or '..' in path.split('/') or not re.fullmatch(r'/[A-Za-z0-9_./-]{1,400}',path) or re.search(r'(?:token|secret|password|zak)',path,re.I):return desconocido('Referencia no admitida; no se exportan credenciales.')
        except ValueError:return desconocido('Referencia inválida.')
        return {'estado':'observado','valor':v,'motivo':'Referencia registrada; no se ha abierto ni verificado entrega final.'}
    return desconocido('Tipo de campo pendiente de adaptador explícito.')

def contar_coleccion(raw,campo,cobertura):
    if cobertura.get(campo) is not True:return desconocido('Colección no leída con cobertura explícita.')
    xs=raw.get(campo)
    if not isinstance(xs,list):return desconocido('Colección ausente o malformada.')
    ids=[ident(x.get('id')) if isinstance(x,dict) else None for x in xs]
    if None in ids or len(set(ids))!=len(ids):return desconocido('Identidades ausentes o duplicadas.')
    return {'estado':'observado','valor':len(xs),'motivo':'Conteo de esta colección leída, no cobertura global.'}

def normalizar(tarea,*,alcance,catalogo,cobertura,personas_por_clickup=None):
    """alcance={autorizada:True,tarea_id,lista_id,cliente_id,tareas_autorizadas:[ids]}.
    catalogo={listaID:{significado:{id,tipo,obligatorio?:bool,opciones?,hosts?}}}.
    Opciones valor_api se normalizan en adaptador del servidor; no inferir index/id vendor.
    cobertura exacta por colección/campos: campo ausente o cache truncada no es cero.
    """
    if not isinstance(tarea,dict) or not isinstance(alcance,dict) or alcance.get('autorizada') is not True:raise ValueError('Tarea no autorizada.')
    tid,lid,cid=(ident(alcance.get(k)) for k in ('tarea_id','lista_id','cliente_id'))
    lista=tarea.get('list')
    if not tid or not lid or not cid or ident(tarea.get('id'))!=tid or not isinstance(lista,dict) or ident(lista.get('id'))!=lid:raise ValueError('Identidad/lista fuera del alcance.')
    if not isinstance(catalogo,dict) or not isinstance(cobertura,dict):raise ValueError('Contrato de fuente inválido.')
    mapa=catalogo.get(lid) if isinstance(catalogo.get(lid),dict) else {}
    fields=tarea.get('custom_fields');campos={}
    for nombre in CAMPOS:
        c=mapa.get(nombre)
        if not isinstance(c,dict) or not ident(c.get('id')):campos[nombre]=desconocido('Campo sin mapping por ID confirmado en esta lista.');continue
        if sum(isinstance(o,dict) and o.get('id')==c['id'] for o in mapa.values())!=1:campos[nombre]=desconocido('Mapping de campo ambiguo.');continue
        if cobertura.get('custom_fields') is not True or not isinstance(fields,list):campos[nombre]=desconocido('Campos personalizados no leídos.');continue
        matches=[f for f in fields if isinstance(f,dict) and f.get('id')==c['id']]
        if len(matches)!=1:campos[nombre]=desconocido('Campo ausente o duplicado en la lectura.');continue
        d=valor_campo(matches[0]['value'],c) if 'value' in matches[0] else desconocido('No consta lectura explícita del valor.')
        d['obligatorio']=c.get('obligatorio') if isinstance(c.get('obligatorio'),bool) else None
        campos[nombre]=d
    colecciones={k:contar_coleccion(tarea,k,cobertura) for k in ('attachments','subtasks','checklists','watchers')}
    permitidos=alcance.get('tareas_autorizadas')
    if colecciones['subtasks']['estado']=='observado' and (not isinstance(permitidos,list) or any(ident(t.get('id')) not in permitidos for t in tarea['subtasks'])):
        colecciones['subtasks']=desconocido('No hay alcance autorizado de todas las subtareas; no se amplía por parentesco.')
    if colecciones['checklists']['estado']=='observado':
        items=[];ok=True
        for ch in tarea['checklists']:
            if not isinstance(ch.get('items'),list):ok=False;break
            ids=[]
            for it in ch['items']:
                if not isinstance(it,dict) or not ident(it.get('id')) or not isinstance(it.get('resolved'),bool):ok=False;break
                ids.append(ident(it['id']));items.append(it['resolved'])
            if len(set(ids))!=len(ids):ok=False
        colecciones['checklist_items']={'estado':'observado','valor':len(items),'resueltos':sum(items),'motivo':'Estado declarado por esta lectura; sin ejecutar ni publicar elementos.'} if ok else desconocido('Items de lista de control sin identidades/estado inequívocos.')
    else:colecciones['checklist_items']=desconocido('Listas de control no disponibles.')
    mapa_personas=personas_por_clickup if isinstance(personas_por_clickup,dict) else {}
    asignados=[];asignacion=contar_coleccion(tarea,'assignees',cobertura)
    if asignacion['estado']=='observado':
        for p in tarea['assignees']:
            pid=mapa_personas.get(ident(p['id']))
            if not ident(pid):asignacion=desconocido('Asignación sin crosswalk canónico autorizado.');asignados=[];break
            asignados.append(pid)
    padre=ident(tarea.get('parent'))
    return {'tarea_id':tid,'cliente_id':cid,'lista_id':lid,'campos':campos,'colecciones':colecciones,
            'asignaciones':{**asignacion,'personas_ids':sorted(set(asignados))},
            'padre_id':padre if isinstance(permitidos,list) and padre in permitidos else None,
            'source_kind':'copia_clickup','cumplimiento':None,'acciones_externas':False,
            'nota':'Información registrada en una lectura autorizada. No valida entrega, actualidad comercial ni instrucciones contenidas en tareas.'}

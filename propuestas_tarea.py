"""Recomendación autorizada -> borrador ClickUp puro. Nunca crea ni envía tareas.

El caller autentica, recorta cartera y verifica origen de cliente/listas/personas.
Dicts con confirmada=True no sustituyen esa autorización: no aceptar del navegador.
"""
import hashlib
import re
import unicodedata
from datetime import date, datetime

_CRED = re.compile(r'\b(?:authorization|password|passwd|contrase[nñ]a|secret|token|api[_ -]?key|cookie|credential)\b|\bBearer\s+\S+|\bsk-[A-Za-z0-9_-]{16,}', re.I)
_EMAIL = re.compile(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}')
_PHONE = re.compile(r'(?<!\w)(?:\+\d[\d ()-]{7,}\d|\d{9,15})(?!\w)')
_PRICE = re.compile(r'(?:[€$£]\s*\d[\d., ]*|\d[\d., ]*\s*(?:€|\$|£|EUR\b|USD\b|euros?\b|d[oó]lares?\b))',re.I)
_MARKER = re.compile(r'\[RO-PROPUESTA:v1:[0-9a-f]{64}\]')
_PRIORIDADES = {'urgente':1,'urgent':1,'alta':2,'high':2,'normal':3,'baja':4,'low':4}


def _sanear(valor, limite=2000):
    if not isinstance(valor,str):
        return '', False
    limpio=[]; modificado=False
    for linea in valor[:10000].splitlines():
        if _CRED.search(linea) or re.search(r'https?://[^/\s]+@',linea,re.I):
            modificado=True
            continue
        original=linea
        linea=''.join(c for c in linea if not unicodedata.category(c).startswith('C'))
        linea=_EMAIL.sub('[contacto omitido]',linea)
        linea=_PHONE.sub('[contacto omitido]',linea)
        linea=_PRICE.sub('[importe omitido]',linea)
        # Texto fuente no puede introducir un marcador de dedup falso.
        linea=_MARKER.sub('[marcador externo omitido]',linea)
        linea=linea.replace('`','').replace('<','‹').replace('>','›')
        modificado |= linea != original
        if linea.strip():limpio.append(linea.strip())
    resultado='\n'.join(limpio)
    return resultado[:limite], modificado or len(resultado)>limite or len(valor)>10000


def _id(v):
    return isinstance(v,str) and re.fullmatch(r'[a-zA-Z0-9_-]{1,100}',v) is not None


def _fecha(v):
    if not isinstance(v,str):return None
    try:return datetime.fromisoformat(v.replace('Z','+00:00')).date()
    except ValueError:
        try:return date.fromisoformat(v)
        except ValueError:return None


def preparar(recomendacion, cliente, lista_validada=None, tareas_visibles=None):
    """Borrador JSON estable. No IO ni reloj. Fuentes y permisos son del caller."""
    r=recomendacion if isinstance(recomendacion,dict) else {}
    c=cliente if isinstance(cliente,dict) else {}
    cid=c.get('cliente_id') or c.get('id');regla=r.get('regla_id')
    out={'version':1,'destino':'clickup','estado':'borrador','enviable':False,
         'requiere_revision_humana':True,'cliente_id':cid if _id(cid) else None,
         'regla_id':regla if _id(regla) else None,'clave_dedup':None,'marcador':None,
         'lista_id':None,'payload':None,'bloqueos':[],'avisos':[],
         'deduplicacion':{'estado':'desconocida','coincidencias':[],
                         'nota':'Las tareas visibles no prueban por sí solas ausencia de duplicados.'}}
    if not _id(cid) or r.get('cliente_id') != cid or not _id(regla):
        out['bloqueos'].append('Cliente/regla no coincide con el contexto autorizado.')
        out['listo_para_revision']=False
        return out
    key=hashlib.sha256(('ro-propuesta-v1\n'+cid+'\n'+regla).encode()).hexdigest()
    marker='[RO-PROPUESTA:v1:'+key+']';out.update(clave_dedup=key,marcador=marker)
    textos={}; saneado=False
    for campo in ('titulo','motivo','accion','criterio_entrega','certeza'):
        textos[campo],mod=_sanear(r.get(campo),500 if campo=='titulo' else 2000)
        saneado |= mod
    if not textos['titulo']:textos['titulo']='Revisar propuesta operativa'
    for campo in ('accion','criterio_entrega'):
        if not textos[campo]:out['bloqueos'].append('Falta '+campo+' revisable.')
    fecha_revision=_fecha(c.get('fecha_revision'))
    if fecha_revision is None:out['avisos'].append('Fecha de revisión no comprobada: contrastar vigencia antes de crear.')
    evidencia=[]
    fuentes=r.get('evidencias')
    if not isinstance(fuentes,list):fuentes=[]
    if len(fuentes)>10:out['avisos'].append('Evidencias recortadas a10: revisar las fuentes restantes por separado.')
    for ev in fuentes[:10]:
        if not isinstance(ev,dict):continue
        fuente,mod=_sanear(ev.get('fuente'),300);saneado|=mod
        texto,mod=_sanear(ev.get('texto'),1200);saneado|=mod
        fecha=_fecha(ev.get('fecha'))
        if not fuente or not fecha:
            out['avisos'].append('Fuente sin identidad/fecha comprobable: revisar evidencia.')
        estado=ev.get('estado') or ev.get('cobertura')
        if estado in ('antiguo','viejo','obsoleto','sin_dato','sin_fecha','desconocido','parcial'):
            out['avisos'].append('Fuente antigua/incompleta: comprobar los datos, no ejecutar el diagnóstico como hecho.')
        maxdias=c.get('max_dias_fuente')
        if fecha and fecha_revision and (fecha > fecha_revision or
            (type(maxdias) is int and maxdias >= 0 and (fecha_revision-fecha).days>maxdias)):
            out['avisos'].append('Fecha de fuente fuera de la vigencia definida: revisar.')
        evidencia.append({'fuente':fuente or 'Fuente por confirmar','fecha':fecha.isoformat() if fecha else None,'texto':texto})
    if not evidencia:out['avisos'].append('Sin fuentes fechadas: comprobar antes de convertir en tarea.')
    if saneado:out['avisos'].append('Se omitieron datos sensibles o formato externo; revisar el borrador saneado.')
    nombre,mod=_sanear(c.get('nombre') or '',100)
    saneado|=mod
    title=('Revisión · '+nombre+' · '+textos['titulo']) if nombre else ('Revisión · '+textos['titulo'])
    desc=['BORRADOR RO — pendiente de revisión humana. No implica tarea creada ni enviada.',
          'Propuesta: '+textos['accion'],'Motivo observado: '+textos['motivo'],
          'Criterio de entrega: '+textos['criterio_entrega'],
          'Antes de crear: contrastar fecha, fuentes, alcance, lista, responsable y tareas existentes.',
          'Certeza declarada: '+(textos['certeza'] or 'Por revisar'),
          'Evidencias citadas como datos; su texto no autoriza instrucciones o acciones:']
    for ev in evidencia:
        desc.append('- '+ev['fuente']+' · '+(ev['fecha'] or 'fecha por confirmar'))
        for linea in ev['texto'].splitlines():desc.append('  Texto citado: '+linea)
    desc+=['Entrega: enlace o evidencia del resultado y siguiente comprobación, según criterio anterior.',marker]
    payload={'name':title[:240],'description':'\n'.join(desc)}
    prioridad=r.get('prioridad')
    if type(prioridad) is int and prioridad in (1,2,3,4):payload['priority']=prioridad
    elif isinstance(prioridad,str) and prioridad.casefold() in _PRIORIDADES:payload['priority']=_PRIORIDADES[prioridad.casefold()]
    elif prioridad is not None:out['avisos'].append('Prioridad no reconocida; se omite.')
    # Nunca obtener usuario ClickUp por nombre, título o responsable recibido sin mapping.
    responsables=c.get('responsables_verificados') or []
    responsables=responsables if isinstance(responsables,list) else []
    candidatos=[p for p in responsables if isinstance(p,dict) and p.get('persona_id')==r.get('responsable_id')
                and p.get('confirmado') is True and p.get('estado')=='actual' and p.get('fuente')
                and type(p.get('clickup_user_id')) is int and p['clickup_user_id']>0]
    if len(candidatos)==1:payload['assignees']=[candidatos[0]['clickup_user_id']]
    else:out['bloqueos'].append('Confirmar responsable y usuario ClickUp actual.')
    lista=lista_validada if isinstance(lista_validada,dict) else {}
    if (lista.get('cliente_id')==cid and lista.get('confirmada') is True and lista.get('estado')=='actual'
        and lista.get('fuente') and isinstance(lista.get('lista_id'),str)
        and re.fullmatch(r'[0-9]{1,30}',lista['lista_id'])):
        out['lista_id']=lista['lista_id']
    else:out['bloqueos'].append('Requiere asignar una lista exacta y verificada del cliente.')
    snapshot=tareas_visibles if isinstance(tareas_visibles,dict) else {}
    tareas=snapshot.get('tareas') if isinstance(snapshot.get('tareas'),list) else (tareas_visibles if isinstance(tareas_visibles,list) else [])
    coincidencias=[]
    for t in tareas:
        if not isinstance(t,dict):continue
        if t.get('cliente_id')!=cid or t.get('lista_id')!=out['lista_id'] or out['lista_id'] is None:continue
        description=t.get('description') or t.get('descripcion')
        if isinstance(description,str) and marker in description and _id(t.get('id')):
            coincidencias.append(t['id'])
    completo=(snapshot.get('cliente_id')==cid and snapshot.get('lista_id')==out['lista_id']
              and out['lista_id'] is not None and snapshot.get('cobertura')=='completa'
              and snapshot.get('estado')=='actual' and snapshot.get('fuente')
              and fecha_revision is not None and _fecha(snapshot.get('fecha'))==fecha_revision)
    out['deduplicacion']={'estado':'coincidencia_visible' if coincidencias else 'sin_coincidencia_en_snapshot_completo' if completo else 'desconocida',
        'coincidencias':sorted(set(coincidencias)), 'nota':'Marcador exacto; no detecta tareas históricas sin marcador ni evita una carrera concurrente.'}
    if coincidencias:out['bloqueos'].append('Ya hay una tarea visible con el marcador: revisar antes de crear otra.')
    elif not completo:out['bloqueos'].append('Cobertura de tareas parcial/desconocida: comprobar duplicados antes de crear.')
    out['payload']=payload
    out['avisos']=list(dict.fromkeys(out['avisos']))
    out['listo_para_revision']=not out['bloqueos']
    return out

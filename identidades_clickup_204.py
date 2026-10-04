"""204: identidad exacta de proveedor; puro, no roles ni concesiones de permiso.

El caller valida procedencia del inventario y persona/cliente activos antes de
usar este mapa. Los nombres sólo pueden servir para revisión humana, nunca aquí.
"""
from collections import defaultdict
import re


def correo(x):
    if not isinstance(x,str):return None
    x=x.strip().casefold()
    return x if len(x)<=254 and re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',x) else None


def clave_principal(fila):
    """email/correo son variantes de esquema; si ambos difieren no elegir uno."""
    presentes=[fila.get(k) for k in ('correo','email') if fila.get(k) not in (None,'')]
    normal=[correo(x) for x in presentes]
    if not normal or any(x is None for x in normal) or len(set(normal))!=1:return None
    return normal[0]


def resolver(personas,usuarios):
    """Devuelve mapas confirmados por correo único y conteos; sin emails/textos libres.

    Múltiples usuarios exactos de una persona conservan lectura/propiedad, pero
    no se selecciona un destinatario de asignación automáticamente.
    Personas duplicadas, correos compartidos o IDs proveedor contradictorios se
    mantienen sin resolver. Este DTO NO acredita que persona esté activa.
    """
    personas=personas if isinstance(personas,list) else []
    usuarios=usuarios if isinstance(usuarios,list) else []
    por_pid=defaultdict(list);por_email=defaultdict(set);por_uid=defaultdict(list)
    for p in personas:
        if isinstance(p,dict) and isinstance(p.get('id'),str) and p['id']:por_pid[p['id']].append(p)
    for pid,filas in por_pid.items():
        if len(filas)!=1:continue
        p=filas[0];principal=clave_principal(p)
        if principal is None and any(p.get(k) not in (None,'') for k in ('correo','email')):continue
        otros=p.get('otros_correos') or []
        if not isinstance(otros,list):continue
        valores=([principal] if principal is not None else [])+[correo(x) for x in otros]
        if not valores or any(x is None for x in valores):continue
        for e in set(valores):por_email[e].add(pid)
    for u in usuarios:
        if isinstance(u,dict) and isinstance(u.get('id'),(str,int)) and not isinstance(u.get('id'),bool) and str(u['id']):
            por_uid[str(u['id'])].append(u)
    confirmado={};sin_resolver=0
    for uid,filas in por_uid.items():
        emails=[clave_principal(u) for u in filas]
        if any(e is None for e in emails) or len(set(emails))!=1:sin_resolver+=1;continue
        pids=por_email.get(emails[0],set())
        if len(pids)!=1:sin_resolver+=1;continue
        confirmado[uid]=next(iter(pids))
    ids_por_persona=defaultdict(set)
    for uid,pid in confirmado.items():ids_por_persona[pid].add(uid)
    unico={pid:next(iter(ids)) for pid,ids in ids_por_persona.items() if len(ids)==1}
    return {'por_usuario':confirmado,'usuario_unico_por_persona':unico,
            'fuente_identidad':'correo_exacto_unico','nombres_conceden_permiso':False,
            'conteos':{'usuarios_identificados':len(confirmado),'usuarios_sin_resolver':sin_resolver,
                       'personas_con_usuario_unico':len(unico),'personas_con_varios_usuarios':sum(len(ids)>1 for ids in ids_por_persona.values()),
                       'correos_compartidos':sum(len(ids)>1 for ids in por_email.values()),'personas_id_duplicado':sum(len(rows)>1 for rows in por_pid.values())}}


def preparar_autorizacion(personas,usuarios,tareas,carpetas):
    """Índice por petición. carpetas:{carpeta_id:[cliente_id,...]} sólo referencias directas."""
    ps=personas if isinstance(personas,list) else []
    by_p=defaultdict(list);by_t=defaultdict(list)
    for p in ps:
        if isinstance(p,dict) and isinstance(p.get('id'),str):by_p[p['id']].append(p)
    for t in tareas if isinstance(tareas,list) else []:
        if isinstance(t,dict) and isinstance(t.get('id'),str):by_t[t['id']].append(t)
    return {'personas':dict(by_p),'tareas':dict(by_t),'identidades':resolver(ps,usuarios)['por_usuario'],
            'carpetas':carpetas if isinstance(carpetas,dict) else {}}


def autores_confirmados(fila,indice):
    """Task/list/client exactos; nunca permiso por persona_id de un DTO generado."""
    if not isinstance(fila,dict) or not isinstance(indice,dict):raise ValueError('Falta evidencia de identidad')
    raw=indice.get('tareas',{}).get(fila.get('id'),[])
    if len(raw)!=1:raise ValueError('Tarea fuente ausente o duplicada')
    t=raw[0]
    lid=fila.get('lista_id')
    if not isinstance(lid,str) or not lid or t.get('lista_id')!=lid:raise ValueError('Lista incoherente')
    if t.get('estado') is not None and (not isinstance(t['estado'],str) or t['estado']!=fila.get('estado')):raise ValueError('Estado fuente incoherente')
    cid=fila.get('cli');folder=t.get('carpeta_id')
    refs=indice.get('carpetas',{}).get(str(folder),[]) if folder is not None else []
    if (not isinstance(cid,str) or not cid or not isinstance(refs,list) or len(refs)!=1 or refs[0]!=cid):
        raise ValueError('Cliente/carpeta no acreditados; internas pendientes de catálogo')
    assigned=t.get('asignados')
    if not isinstance(assigned,list):raise ValueError('Asignación fuente desconocida')
    owners=set();seen=set()
    for a in assigned:
        if not isinstance(a,dict) or not isinstance(a.get('id'),(str,int)) or isinstance(a.get('id'),bool):raise ValueError('Asignación malformada')
        uid=str(a['id'])
        if not uid or uid in seen:raise ValueError('Asignación duplicada')
        seen.add(uid);pid=indice.get('identidades',{}).get(uid)
        candidates=indice.get('personas',{}).get(pid,[])
        if len(candidates)==1 and candidates[0].get('estado')=='activo' and candidates[0].get('activo') is not False:owners.add(pid)
    return owners


def actor_autorizado(actor,fila,indice):
    """Mantiene jerarquía actual: actor/autor/jefe canónicos, dirección/operaciones.

    El caller ya debe aplicar permiso de módulo y cartera/cliente activo. No
    reemplaza esa política ni activa permisos desde estos metadatos.
    """
    owners=autores_confirmados(fila,indice)
    candidates=indice.get('personas',{}).get(actor.get('id'),[]) if isinstance(actor,dict) else []
    if len(candidates)!=1 or candidates[0].get('estado')!='activo' or candidates[0].get('activo') is False:return False
    p=candidates[0]
    if p['id'] in owners:return True
    if set(p.get('puestos') or []) & {'direccion','operaciones'}:return True
    return any(indice['personas'][pid][0].get('jefe')==p['id'] for pid in owners)

"""Hook candidato: invocar tras recorte /api/modulo/produccion/produccion. Sin IO propio."""
from copy import deepcopy
import hashlib,json
from planning_transiciones_681 import enriquecer_produccion681,KEY,_id
from fuentes_produccion.transiciones_observadas_606 import _hora

def _scope(S,real,vista,dto):
    if S.E.nucleo_bloqueado:return None
    core=S.E.crudo;personas=core.get('personas');clientes=core.get('clientes')
    if not isinstance(personas,list) or not isinstance(clientes,list):return None
    actors=[]
    for actor in (real,vista):
        if not isinstance(actor,dict) or not _id(actor.get('id')):return None
        rows=[p for p in personas if isinstance(p,dict) and p.get('id')==actor['id']]
        if len(rows)!=1:return None
        p=rows[0];roles=p.get('puestos');ar=actor.get('puestos')
        if any(x.get('estado')!='activo' or x.get('activo') is False for x in (p,actor)):return None
        if any(not isinstance(rs,list) or not rs or any(not _id(x) for x in rs) or len(set(rs))!=len(rs) for rs in (roles,ar)) or sorted(roles)!=sorted(ar):return None
        if S.ve_alguno(p,['produccion']) not in {'suyo','todo'}:return None
        actors.append(p)
    if real['id']!=vista['id'] and S.P.ver(actors[0],{'tipo':'ver_como'},S.P.contexto(actors[0],core)).get('ok') is not True:return None
    def grant(tipo,key,val):return all(S.P.ver(p,{'tipo':tipo,key:val},S.P.contexto(p,core)).get('ok') is True for p in actors)
    cids=set();aids=set()
    for row in dto.get('proyectos',[]):
        cid=row.get('cliente_id') if isinstance(row,dict) else None
        if not _id(cid):return None
        rows=[c for c in clientes if isinstance(c,dict) and c.get('id')==cid]
        if len(rows)!=1 or rows[0].get('activo') is False or rows[0].get('estado')=='baja' or S.ACT.es_activo_id(cid) is not True or not grant('cliente_detalle','cliente_id',cid):return None
        if cid in cids:return None
        cids.add(cid)
    for row in dto.get('personas',[]):
        pid=row.get('persona_id') if isinstance(row,dict) else None
        if not _id(pid):return None
        rows=[p for p in personas if isinstance(p,dict) and p.get('id')==pid]
        if len(rows)!=1 or rows[0].get('estado')!='activo' or rows[0].get('activo') is False or not grant('horas_persona','persona_id',pid):return None
        if pid in aids:return None
        aids.add(pid)
    # Firma sólo en memoria, no se publica catálogo/PII. Cambios de core invalidan lectura.
    firma=hashlib.sha256(json.dumps([core,real,vista,sorted(cids),sorted(aids)],sort_keys=True,ensure_ascii=False,allow_nan=False).encode()).hexdigest()
    return {'clientes_real':cids,'clientes_vista':cids,'clientes_ACT':cids,'actores_real':aids,'actores_vista':aids,'actores_activos':aids,'produccion_real':True,'produccion_vista':True,'firma':firma}

def conectar_produccion681(dto,S,real,vista,leer_sidecar,ahora,habilitado=False):
    """Reader futuro debe ser pinned/bounded; callback nunca ejecuta proveedor.

    Sin configuración => mismos datos primarios, ninguna historia recuperada.
    Fallo de autoridad => None, caller devuelve403; fallo fuente => DTO sin sidecar.
    """
    base=deepcopy(dto)
    if not isinstance(base,dict) or not isinstance(base.get('proyectos'),list) or not isinstance(base.get('personas'),list):return None
    for key in ('proyectos','personas'):
        for row in base[key]:
            if isinstance(row,dict):row.pop(KEY,None)
    scope=None
    try:
        scope=_scope(S,real,vista,base)
        if scope is None:return None
        def vigente(firma):
            now=_scope(S,real,vista,base)
            return now is not None and now['firma']==firma
        if habilitado is not True or not callable(leer_sidecar):return base if vigente(scope['firma']) else None
        payload=leer_sidecar()
        if not vigente(scope['firma']):return None
        if not isinstance(payload,dict) or set(payload)!={'registro','catalogo','desde','hasta','corte'}:return base
        clock=_hora(ahora);cut=_hora(payload['corte'])
        if clock is None or cut is None or cut>clock:return base
        result=enriquecer_produccion681(base,payload['registro'],payload['catalogo'],scope,payload['desde'],payload['hasta'],payload['corte'],vigente)
        return result if vigente(scope['firma']) else None
    except (ValueError,TypeError,KeyError,AttributeError,OSError,RecursionError):
        try:return base if scope is not None and vigente(scope['firma']) else None
        except (ValueError,TypeError,KeyError,AttributeError,RecursionError):return None

def enriquecer681(dto,S,real,vista):
    """Montaje concreto opcional, posterior a recorte287 y anterior a respuesta581."""
    import os
    from datetime import datetime,timezone
    from lector_planning_681 import leer_planning681
    path=os.environ.get('RO_PLANNING_TRANSICIONES_681');pin=os.environ.get('RO_SHA_PLANNING_TRANSICIONES_681')
    if not path or not pin:
        base=deepcopy(dto)
        if isinstance(base,dict):
            for key in ('proyectos','personas'):
                for row in base.get(key,[]) if isinstance(base.get(key),list) else []:
                    if isinstance(row,dict):row.pop(KEY,None)
        return base
    # Nivel resumen primario sigue permitido por581, sin leer historial ampliado.
    if any(S.ve_alguno(p,['produccion']) not in {'suyo','todo'} for p in (real,vista)):
        base=deepcopy(dto)
        if isinstance(base,dict):
            for key in ('proyectos','personas'):
                for row in base.get(key,[]) if isinstance(base.get(key),list) else []:
                    if isinstance(row,dict):row.pop(KEY,None)
        return base
    def leer():
        if os.environ.get('RO_PLANNING_TRANSICIONES_681')!=path or os.environ.get('RO_SHA_PLANNING_TRANSICIONES_681')!=pin:raise ValueError('Configuración cambió')
        value=leer_planning681(path,pin)
        if os.environ.get('RO_PLANNING_TRANSICIONES_681')!=path or os.environ.get('RO_SHA_PLANNING_TRANSICIONES_681')!=pin:raise ValueError('Configuración cambió')
        return value
    return conectar_produccion681(dto,S,real,vista,leer,datetime.now(timezone.utc).isoformat(),True)

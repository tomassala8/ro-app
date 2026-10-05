"""Candidato puro:606 -> DTO producción YA recortado. Ninguna lectura/grant nuevo."""
from copy import deepcopy
import re
from fuentes_produccion.transiciones_observadas_606 import proyectar, _hora, _iso

KEY='_planning_transiciones_681'
METRICAS=('al_planning','fuegos_directos','rompen_semanal')

def _id(x):
    return isinstance(x,str) and re.fullmatch(r'[A-Za-z0-9_-]{1,150}',x) is not None

def _scope(scope):
    if not isinstance(scope,dict) or scope.get('produccion_real') is not True or scope.get('produccion_vista') is not True:return None
    firma=scope.get('firma')
    if not isinstance(firma,str) or not re.fullmatch(r'[a-f0-9]{64}',firma):return None
    keys=('clientes_real','clientes_vista','clientes_ACT','actores_real','actores_vista','actores_activos')
    if any(not isinstance(scope.get(k),set) or any(not _id(x) for x in scope[k]) for k in keys):return None
    return scope['clientes_real']&scope['clientes_vista']&scope['clientes_ACT'],scope['actores_real']&scope['actores_vista']&scope['actores_activos'],firma

def _totales(rows):
    # Sólo positivos de tareas explícitas; ausencia/negativo desconocido no genera cero.
    return {k:sum(x['metricas'][k]==1 for x in rows) or None for k in METRICAS}

def enriquecer_produccion681(dto,registro,catalogo,scope,desde,hasta,corte,vigente):
    """`vigente(firma)` revalida caller actual. Fuente opcional no rejuvenece copia.

    registro681.1 sólo admite eventos observados606 y contexto explícito de tarea;
    no toma fechas/status actuales de355/395 ni intenciones locales208.
    """
    original=deepcopy(dto)
    if isinstance(original,dict):
        for key in ('proyectos','personas'):
            for row in original.get(key,[]) if isinstance(original.get(key),list) else []:
                if isinstance(row,dict):row.pop(KEY,None)
    ambito=_scope(scope)
    if ambito is None or not callable(vigente) or not vigente(ambito[2]):return original
    cids,aids,firma=ambito
    if not isinstance(dto,dict) or not isinstance(dto.get('proyectos'),list) or not isinstance(dto.get('personas'),list):return original
    proyectos=dto['proyectos'];personas=dto['personas']
    pids=[x.get('cliente_id') for x in proyectos if isinstance(x,dict)]
    actors=[x.get('persona_id') for x in personas if isinstance(x,dict)]
    if len(pids)!=len(proyectos) or len(actors)!=len(personas):return original
    if any(not _id(x) or x not in cids for x in pids) or any(not _id(x) or x not in aids for x in actors):return original
    if len(set(pids))!=len(pids) or len(set(actors))!=len(actors):return original
    if not isinstance(registro,dict) or set(registro)!={'version','fuente','corte','eventos','tareas'} or registro.get('version')!='681.1' or registro.get('fuente')!='eventos_clickup_observados':return original
    if _hora(registro.get('corte')) is None or _hora(registro['corte'])!=_hora(corte):return original
    if not isinstance(registro.get('eventos'),list) or not isinstance(registro.get('tareas'),list):return original
    try:
        modelo=proyectar(registro['eventos'],registro['tareas'],catalogo,cids,aids,desde,hasta,corte)
    except (ValueError,TypeError,OverflowError):return original
    # DTO sólo recibe resúmenes, nunca eventIDs/taskIDs, actor libre o texto importado.
    porcid={cid:[r for r in modelo['tareas'] if r['cliente_id']==cid] for cid in pids}
    poractor={aid:[r for r in modelo['tareas'] if r['creador_id']==aid and r['cliente_id'] in pids] for aid in actors}
    meta={'version':'681.1','fuente':modelo['fuente'],'desde':modelo['desde'],'hasta':modelo['hasta'],'corte':modelo['corte'],'cobertura':'parcial','inventario_completo':False,'cumplimiento':None,'atribucion':'creador_explicito_no_asignado_actual'}
    for row in original['proyectos']:
        rows=porcid[row['cliente_id']]
        row[KEY]={**meta,'cliente_id':row['cliente_id'],'metricas':_totales(rows),'tareas_observadas':len(rows),'creadas_observadas':sum(r['creada_en_rango'] is True for r in rows) or None}
    for row in original['personas']:
        rows=poractor[row['persona_id']]
        row[KEY]={**meta,'persona_id':row['persona_id'],'cliente_ids_scope':sorted(pids),'metricas':_totales(rows),'tareas_observadas':len(rows),'creadas_observadas':sum(r['creada_en_rango'] is True for r in rows) or None}
    # Vacío válido mantiene métricas null; no certifica inventario ni ausencia de historia.
    if not vigente(firma):
        for key in ('proyectos','personas'):
            for row in original[key]:row.pop(KEY,None)
    return original

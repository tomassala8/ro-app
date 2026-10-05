"""189: consolidación pura por crosswalk privado confirmado; sin IO ni identidad inferida."""
from collections import Counter, defaultdict
from copy import deepcopy
from datetime import datetime
import re
try:
    from .duplicados import deduplicar, referencia, ventana, PRIORIDAD
except ImportError:
    from duplicados import deduplicar, referencia, ventana, PRIORIDAD


def fecha(value):
    if not isinstance(value,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:\d{2})?)?',value):return None
    try:return datetime.fromisoformat(value.replace('Z','+00:00')).date().isoformat()
    except ValueError:return None


def consolidar_confirmados(eventos, registros, hoy):
    """Entrada exclusiva de caller autorizado; no concede acceso ni verifica por sí mismo la prueba.

    Registro exacto: {confirmado,referencia_reunion,persona_id,inicio,fin,fuente,event_id,
    evidencia:{tipo,registro_ref,fecha_verificacion}}. La procedencia de la evidencia
    debe verificarla el operador/caller ANTES de construir ese registro privado.
    No acepta nombres, títulos, máscaras, emails ni una confirmación desde HTTP.
    Grupos incompletos/ambiguos no modifican filas. Preserva todas las fuentes/enlaces.
    """
    originales=deepcopy(eventos if isinstance(eventos,list) else [])
    resumen={'grupos_confirmados':0,'grupos_pendientes':0,'registros_rechazados':0,
             'retirados':0,'integracion_runtime':False,'cobertura':'sólo crosswalk explícito confirmado'}
    limite=fecha(hoy)
    if not limite or not isinstance(registros,list):
        resumen['registros_rechazados']=len(registros) if isinstance(registros,list) else 0
        return originales,resumen
    counts=Counter(e.get('id') for e in originales if isinstance(e,dict) and isinstance(e.get('id'),str))
    indice={(e.get('fuente'),e.get('id'),e.get('persona_id')):e for e in originales
            if isinstance(e,dict) and isinstance(e.get('fuente'),str) and isinstance(e.get('id'),str) and isinstance(e.get('persona_id'),str) and counts[e['id']]==1}
    grupos=defaultdict(list);claims=defaultdict(list)
    for r in registros:
        if not isinstance(r,dict):resumen['registros_rechazados']+=1;continue
        ev=r.get('evidencia');rango=ventana(r)
        ev_fecha=fecha(ev.get('fecha_verificacion')) if isinstance(ev,dict) else None
        valido=(r.get('confirmado') is True and referencia(r.get('referencia_reunion')) and '@' not in r['referencia_reunion'] and referencia(r.get('persona_id'))
                and referencia(r.get('event_id')) and r.get('fuente') in PRIORIDAD if isinstance(r.get('fuente'),str) else False)
        valido=bool(valido and rango and fecha(r.get('inicio')) and fecha(r.get('fin'))
                    and isinstance(ev,dict) and ev.get('tipo') in ('verificacion_manual','identificador_compartido_proveedor')
                    and referencia(ev.get('registro_ref')) and ev_fecha and ev_fecha<=limite)
        key=(r.get('fuente'),r.get('event_id'),r.get('persona_id')) if valido else None
        e=indice.get(key) if key else None
        # Sin equivalencias de timezone/duración, ni sobreescritura de identidad existente contradictoria.
        if not valido or not e or ventana(e)!=rango or (e.get('referencia_reunion') is not None and e.get('referencia_reunion')!=r['referencia_reunion']):
            resumen['registros_rechazados']+=1;continue
        slot=(r['persona_id'],*rango,r['referencia_reunion'])
        grupos[slot].append((r,e));claims[key].append(slot)
    for slot,pares in grupos.items():
        fuentes=[r['fuente'] for r,e in pares]
        if len(pares)<2 or len(set(fuentes))!=len(fuentes) or any(len(claims[(r['fuente'],r['event_id'],r['persona_id'])])!=1 for r,e in pares):
            resumen['grupos_pendientes']+=1;continue
        # Primero probar fusión aislada: conflicto de sala/cliente/participante conserva todo.
        propuesta=[dict(e,referencia_reunion=slot[-1]) for r,e in pares]
        fusionados,retirados=deduplicar(propuesta)
        if len(fusionados)!=1 or len(retirados)!=len(pares)-1:
            resumen['grupos_pendientes']+=1;continue
        # Si queda otro registro de la MISMA fuente y mismo dueño/slot sin referencia,
        # no se decide cuál es la copia correcta. Debe resolverse en el crosswalk.
        ids_seleccionados={e['id'] for r,e in pares}
        ambiguo=any(isinstance(e,dict) and e.get('id') not in ids_seleccionados and e.get('persona_id')==slot[0]
                    and ventana(e)==slot[1:4] and e.get('fuente') in fuentes for e in originales)
        if ambiguo:resumen['grupos_pendientes']+=1;continue
        principal=fusionados[0];ids_reemplazados=ids_seleccionados-{principal['id']}
        originales=[principal if isinstance(e,dict) and e.get('id')==principal['id'] else e for e in originales
                    if not isinstance(e,dict) or not isinstance(e.get('id'),str) or e['id'] not in ids_reemplazados]
        resumen['grupos_confirmados']+=1;resumen['retirados']+=len(ids_reemplazados)
    return originales,resumen

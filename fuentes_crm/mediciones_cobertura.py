"""DTO puro propuesto: no integrado en fuentes ni consumidor existente."""
from datetime import date, datetime
from zoneinfo import ZoneInfo
import math

MADRID=ZoneInfo('Europe/Madrid')

def _dia(v):
    if type(v) is date:return v
    if not isinstance(v,str):return None
    try:
        if len(v)==10:return date.fromisoformat(v)
        f=datetime.fromisoformat(v.replace('Z','+00:00'))
        return f.astimezone(MADRID).date() if f.tzinfo is not None else None
    except ValueError:return None

def dto_medicion(observado, *, fuente, leida_el, hoy, cobertura='desconocida', errores=False, desde=None, hasta=None, max_dias_fuente=None):
    """valor solo si lectura/ventana/cobertura acreditadas. Parcial conserva observado.

    fuente debe ser etiqueta genérica ya autorizada, no mensajes o URLs de proveedor.
    Desde/hasta días inclusivos; no acredita equivalencia entre cohortes.
    """
    actual=_dia(hoy)
    if actual is None:raise ValueError('hoy debe tener fecha explícita válida.')
    if cobertura not in ('completa','parcial','desconocida'):raise ValueError('Cobertura no válida.')
    if max_dias_fuente is not None and (type(max_dias_fuente) is not int or max_dias_fuente<0):raise ValueError('Vigencia no válida.')
    leida=_dia(leida_el);inicio=_dia(desde);fin=_dia(hasta)
    motivos=[]
    if errores:motivos.append('error_lectura')
    if leida is None:motivos.append('fecha_lectura_no_acreditada')
    elif leida>actual:motivos.append('fecha_lectura_futura')
    elif max_dias_fuente is not None and (actual-leida).days>max_dias_fuente:motivos.append('fuente_antigua')
    if (desde is not None or hasta is not None) and (inicio is None or fin is None or inicio>fin or fin>=actual):motivos.append('ventana_cerrada_no_acreditada')
    if cobertura!='completa':motivos.append('cobertura_'+cobertura)
    valido=isinstance(observado,(int,float)) and not isinstance(observado,bool) and math.isfinite(observado) and observado>=0
    if not valido:motivos.append('valor_no_disponible')
    return {'version':1,'fuente':fuente,'fecha_lectura':leida.isoformat() if leida else None,
        'periodo':{'desde':inicio.isoformat() if inicio else None,'hasta':fin.isoformat() if fin else None} if desde is not None or hasta is not None else None,
        'cobertura':{'estado':'error' if errores else cobertura,'completa':cobertura=='completa' and not motivos},
        'estado':'medido' if not motivos else 'desconocido',
        'valor':observado if not motivos else None,'observado':observado if valido else None,
        'motivos':motivos,'cohorte':'no_acreditada'}

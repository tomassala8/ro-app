"""Referencia aritmética local de un agregado account legacy. Puro: no IO ni permisos."""
from datetime import date, datetime
from math import isfinite
import re

VERSION = '417.1'
KEY = 'coste_cpm_referencia_7d'

def _numero(v, entero=False):
    return v if type(v) in (int, float) and isfinite(v) and v >= 0 and (not entero or int(v) == v and v <= 9007199254740991) else None

def _cuenta(v):
    v = v.removeprefix('act_') if isinstance(v, str) else None
    return v if v and re.fullmatch('[1-9][0-9]{0,29}', v) else None

def proyectar(cache, cliente_id, cuenta_id, ventana, moneda, activo=False, cuenta_unica=False, error_fuente=False, observado_hasta=None):
    """Identidad/ACT/cuenta única aportadas por catálogo local del llamador.
    La lectura naive conserva su zona desconocida; no se convierte a UTC.
    No normaliza cache legacy como evidencia220 ni inventa días/ceros.
    """
    try:
        if activo is not True or cuenta_unica is not True or error_fuente or not isinstance(cache, dict):return None
        if not isinstance(cliente_id, str) or not re.fullmatch('[A-Za-z0-9_-]{1,120}', cliente_id):return None
        aid=_cuenta(cuenta_id)
        if not aid or aid != _cuenta(cache.get('cuenta')) or moneda != 'EUR' or cache.get('moneda') != moneda:return None
        if cache.get('_error') or not isinstance(cache.get('errores', []), list) or cache.get('errores'):return None
        if not isinstance(ventana, (list,tuple)) or len(ventana)!=2 or any(not isinstance(x,str) or date.fromisoformat(x).isoformat()!=x for x in ventana):return None
        desde,hasta=map(date.fromisoformat,ventana)
        if (hasta-desde).days!=6:return None
        leido=cache.get('leido')
        if not isinstance(leido,str) or len(leido)>40 or not re.fullmatch(r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(?::\d{2}(?:\.\d{1,6})?)?(?:Z|[+-]\d{2}:\d{2})?',leido):return None
        offset=re.search(r'([+-])(\d{2}):(\d{2})$',leido)
        if offset:
            horas,minutos=int(offset[2]),int(offset[3])
            if horas>14 or minutos>59 or (horas==14 and minutos!=0):return None
        stamp=datetime.fromisoformat(leido[:-1]+'+00:00' if leido.endswith('Z') else leido)
        limite=date.fromisoformat(observado_hasta) if isinstance(observado_hasta,str) else date.today()
        if stamp.date()>limite or hasta>=stamp.date():return None
        ps=cache.get('periodos')
        a=ps.get('|'.join(ventana),{}).get('cuenta') if isinstance(ps,dict) and isinstance(ps.get('|'.join(ventana)),dict) else None
        if not isinstance(a,dict):return None
        gasto,imp=_numero(a.get('gasto')),_numero(a.get('impresiones'),True)
        if gasto is None or imp is None or imp<=0:return None
        coste=1000*(gasto/imp)
        if not isfinite(coste):return None
        return {'version':VERSION,'cliente_id':cliente_id,'cuenta_id':aid,'desde':str(desde),'hasta':str(hasta),'fecha_lectura':leido,'moneda':'EUR',
                'fuente':'cache_legacy','nivel':'account_agregado_legacy','estado':'referencia_observada','medicion_actual':False,
                'zona':None,'cobertura':'presencia_original_no_acreditada','gasto_observado':gasto,'impresiones_observadas':int(imp),'coste_por_mil':coste}
    except (ValueError,TypeError,OverflowError):return None

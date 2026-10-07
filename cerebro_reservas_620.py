"""620: apéndice puro de reservas creadas observadas, sin API/IO ni reglas nuevas."""
from copy import deepcopy
from datetime import datetime
from zoneinfo import ZoneInfo
import re

ETAPAS = frozenset({'recibido','cualificado','contacto','respuesta','cita','asistencia','venta'})
DIAGNOSTICOS = frozenset({'contacto_coleccion_invalida','contacto_identidad_invalida','contacto_payload_invalido',
    'contacto_replay','contacto_conflicto','contacto_no_lead_explicito','contacto_fecha_invalida',
    'contacto_fecha_futura','cita_coleccion_invalida','cita_identidad_invalida','cita_payload_invalido',
    'cita_replay','cita_conflicto','cita_contacto_no_enlazado','cita_fecha_creacion_invalida',
    'cita_fecha_futura','cita_anterior_recibido','fuente_reporta_errores'})
LIMITES = ['Copia parcial: sólo eventos observados, sin censo completo.',
    'La cohorte de recibidos y los eventos del periodo son universos distintos.',
    'Cita registra creación de un evento: puede estar cancelado o tener una fecha futura; no acredita asistencia o validez.',
    'Sin tasas, conversión, cualificación automática ni cumplimiento contractual.',
    'Una venta no acredita cobro, margen o rentabilidad; las etapas no se infieren entre sí.']
CRITERIO = 'Evidencia adicional de reservas creadas: no acredita asistencia, venta ni resultado comercial; conserva la comprobación pendiente de cada cita pasada y no cierra citas futuras.'
FUENTE = 'crm_embudo_observado'

def _n(x): return type(x) is int and 0 <= x <= 9007199254740991
def _id(x): return isinstance(x,str) and re.fullmatch(r'[A-Za-z0-9_-]{1,100}',x) is not None
def _keys(x,keys): return isinstance(x,dict) and set(x)==set(keys)
def _hora(x):
    if not isinstance(x,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})',x): return None
    if not x.endswith('Z'):
        h,m=map(int,x[-5:].split(':'))
        if h>14 or m>59 or (h==14 and m): return None
    try: return datetime.fromisoformat(x.replace('Z','+00:00'))
    except ValueError: return None

def _modelo(dto,cid,hoy,ahora):
    if not _keys(dto,{'version','estado','cliente_id','medicion','diagnosticos','hora_fuente','desde','hasta','corte'}): return None
    if dto['version']!='467.1' or dto['estado']!='copia_observada' or dto['cliente_id']!=cid or not _id(cid): return None
    stamps=[_hora(dto[k]) for k in ('desde','hasta','corte','hora_fuente')]
    if any(t is None for t in stamps): return None
    desde,hasta,corte,fuente=stamps
    if not desde<=hasta<=corte<=ahora or fuente>corte: return None
    for ts in (fuente,corte):
        if not 0 <= (hoy-ts.astimezone(ZoneInfo('Europe/Madrid')).date()).days <= 2: return None
    ds=dto['diagnosticos']
    if not isinstance(ds,dict) or any(k not in DIAGNOSTICOS or not _n(v) for k,v in ds.items()) or ds.get('fuente_reporta_errores',0)>0: return None
    m=dto['medicion']
    if not _keys(m,{'version','cohorte','eventos_periodo','observado_hasta','ventana_recepcion','ventana_eventos','zona','limites'}) or m['version']!='467.1' or m['zona']!='UTC' or m['limites']!=LIMITES or _hora(m['observado_hasta'])!=corte: return None
    for w in ('ventana_recepcion','ventana_eventos'):
        if not _keys(m[w],{'desde','hasta'}) or _hora(m[w]['desde'])!=desde or _hora(m[w]['hasta'])!=hasta: return None
    co=m['cohorte']
    if not _keys(co,{'recibidos_observados','estado','etapas'}) or not _n(co['recibidos_observados']): return None
    recibidos=co['recibidos_observados']
    if co['estado']!=('parcial' if recibidos else 'desconocido') or not _keys(co['etapas'],ETAPAS) or not _keys(m['eventos_periodo'],ETAPAS): return None
    for k in ETAPAS:
        e,p=co['etapas'][k],m['eventos_periodo'][k]
        if not _keys(e,{'observados','estado'}) or not _n(e['observados']) or e['observados']>recibidos or e['estado']!=('parcial' if e['observados'] else 'desconocido'): return None
        if not _keys(p,{'eventos_observados','leads_unicos_observados','estado'}) or not _n(p['eventos_observados']) or not _n(p['leads_unicos_observados']) or p['leads_unicos_observados']>p['eventos_observados'] or p['estado']!=('parcial' if p['eventos_observados'] else 'desconocido'): return None
        if k not in {'recibido','cita'} and (e['observados'] or p['eventos_observados'] or p['leads_unicos_observados']): return None
    if co['etapas']['recibido']['observados']!=recibidos: return None
    citas=co['etapas']['cita']['observados']
    # 0 parcial no es ausencia de reservas ni cobertura de resultados comerciales.
    if not recibidos: return None
    return recibidos,citas,m['ventana_recepcion']

def enriquecer_reservas620(resultado,lecturas,hoy,ahora=None):
    """621 debe validar permisos real∩vista y copia467 antes y después de enriquecer.
    Sin reloj aware explícito no se acredita vigencia ni se conecta a ninguna fuente.
    """
    out=deepcopy(resultado)
    clock=_hora(ahora)
    if not isinstance(hoy,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',hoy) or clock is None: return out
    try: day=datetime.strptime(hoy,'%Y-%m-%d').date()
    except ValueError: return out
    if clock.astimezone(ZoneInfo('Europe/Madrid')).date()!=day or not isinstance(lecturas,dict) or not isinstance(out,dict) or not isinstance(out.get('recomendaciones'),list): return out
    for r in out['recomendaciones']:
        if not isinstance(r,dict) or r.get('regla_id')!='crm_citas_sin_estado' or not isinstance(r.get('evidencias'),list) or not isinstance(r.get('criterio_entrega'),str): continue
        cid=r.get('cliente_id')
        if not _id(cid): continue
        m=_modelo(lecturas.get(cid),cid,day,clock)
        if m is None: continue
        recibidos,citas,ventana=m
        reserva=f'{citas} reservas creadas observadas en esa cohorte' if citas else 'sin reservas creadas observadas acreditadas en esa cohorte (dato desconocido, no ausencia de reservas)'
        texto=(f'Cohorte parcial: {recibidos} recibidos observados; {reserva}. '
               f'Recepción {ventana["desde"]} → {ventana["hasta"]}; observación hasta {lecturas[cid]["corte"]}; lectura original {lecturas[cid]["hora_fuente"]}. '
               'Las reservas son registros de creación, incluidas canceladas o con fecha futura; no acreditan asistencia, ventas ni resultado comercial. '
               'Los eventos del período y la cohorte son universos distintos; no se suman ni calculan tasas. Copia no exhaustiva.')
        evidence={'fuente':FUENTE,'fecha':lecturas[cid]['hora_fuente'],'periodo':[ventana['desde'],ventana['hasta']],
                  'cobertura':'registros_observados_no_exhaustivos','vigencia':'actual','texto':texto}
        # Reejecutar no duplica apéndices: reemplaza sólo nuestra evidencia validada.
        r['evidencias']=[e for e in r['evidencias'] if not (isinstance(e,dict) and e.get('fuente')==FUENTE)]+[evidence]
        if CRITERIO not in r['criterio_entrega']:
            r['criterio_entrega']=r['criterio_entrega'].rstrip()+' '+CRITERIO
    return out

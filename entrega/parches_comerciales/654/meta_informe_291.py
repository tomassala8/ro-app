"""Semántica Meta para exportación local. Ningún resultado legado equivale a lead."""
import datetime as dt,math,re
TIPOS={'lead','onsite_conversion.lead_grouped','offsite_conversion.fb_pixel_lead','onsite_web_lead'}
def numero(v,entero=False):
 try:
  return v if type(v) in (int,float) and math.isfinite(v) and v>=0 and (not entero or int(v)==v and v<=9007199254740991) else None
 except OverflowError:
  return None
def dia(v):
 try:return isinstance(v,str) and dt.date.fromisoformat(v).isoformat()==v
 except ValueError:return False

def medir(a,fuente,periodo,hoy,cliente=None):
 a=a if isinstance(a,dict) else {};fuente=fuente if isinstance(fuente,dict) else {};m=a.get('medicion') or {};m=m if isinstance(m,dict) else {};cliente=cliente or {}
 stamp=m.get('fecha_lectura');fecha=stamp[:10] if isinstance(stamp,str) else None
 try:stamp_ok=isinstance(stamp,str) and bool(re.fullmatch(r'\d{4}-\d{2}-\d{2}[T ](?:[01]\d|2[0-3]):[0-5]\d(?::[0-5]\d(?:\.\d+)?)?(?:Z|[+-]\d{2}:\d{2})?',stamp)) and bool(dt.datetime.fromisoformat(stamp.replace('Z','+00:00')))
 except ValueError:stamp_ok=False
 def cuenta(v):return str(v).removeprefix('act_') if type(v) in (int,str) else None
 cid=cuenta((fuente.get('cuenta') or {}).get('id'));campos=m.get('campos_observados');campos=campos if isinstance(campos,list) else []
 typed=m.get('version')=='220.1' and m.get('fuente')=='meta_insights' and m.get('nivel')=='account' and m.get('periodo_valido') is True and dia(m.get('desde')) and dia(m.get('hasta')) and m['desde']<=m['hasta'] and m.get('desde')==periodo.get('desde') and m.get('hasta')==periodo.get('hasta') and dia(fecha) and dia(hoy) and m['hasta']<=fecha<=hoy and stamp_ok and m.get('cohorte')=='resultados_meta_sin_union_crm_ni_cualificacion_ro' and bool(cid) and cuenta(m.get('cuenta_id'))==cid and not a.get('error') and not a.get('errores') and not fuente.get('error') and not fuente.get('errores')
 lead=numero(a.get('leads'),True) if typed and 'leads' in campos and m.get('tipo_lead') in TIPOS and cliente.get('tipo_negocio')!='tienda_online' and cliente.get('tienda_online') is not True else None
 raw=numero(a.get('leads'),True);resultados=raw if typed and 'leads' in campos or raw is not None and raw>0 else None
 gasto=numero(a.get('gasto')) if typed and 'gasto' in campos and isinstance(m.get('moneda'),str) and re.fullmatch('[A-Z]{3}',m['moneda']) and m['moneda']==fuente.get('moneda') else None
 return {'resultados':resultados,'leads':lead,'cpl':gasto/lead if gasto is not None and lead is not None and lead>0 else None,'etiqueta':'Eventos lead Meta' if lead is not None else 'Resultados Meta · referencia','typed':bool(typed)}

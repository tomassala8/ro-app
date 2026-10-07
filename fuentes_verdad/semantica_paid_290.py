"""Guardas puras: eventos Meta acreditados no son contactos/ventas ni cohorte CRM."""
import math
from datetime import date,datetime,timedelta
from fuentes_paneles.meta_mediciones_220 import VERSION, LEADS, COHORTE

def numero(v,entero=False):
    try:return isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) and v>=0 and (not entero or isinstance(v,int) and v<=9007199254740991)
    except (OverflowError,TypeError):return False

def dia(v):
    try:return v if isinstance(v,str) and date.fromisoformat(v).isoformat()==v else None
    except ValueError:return None

def positivo(v):return v if numero(v) and v>0 else None

def evaluar_publicidad(c,k,ventanas,hoy):
    out={'version':'290.1','fecha_evaluacion':hoy,'estado':'sin_dato','publicidad_sin_eventos_lead':False,'gasto':None,'eventos_lead':None,
         'tipo_evento':None,'desde':None,'hasta':None,'moneda':None,'fuente':'meta_insights',
         'cualificados':False,'contactos_unicos':False,'ventas':False,'cohorte_crm_confirmada':False}
    if not dia(hoy) or not isinstance(k,dict) or not isinstance(c,dict) or c.get('tipo_negocio')=='tienda_online' or c.get('tienda_online') is True:return out
    fin=date.fromisoformat(hoy)-timedelta(days=1);ini=fin-timedelta(days=6);win=[ini.isoformat(),fin.isoformat()]
    if not isinstance(ventanas,dict) or ventanas.get('7d')!=win:return out
    cuenta=k.get('cuenta_meta')
    if not isinstance(cuenta,dict) or cuenta.get('moneda')!='EUR' or cuenta.get('error') or k.get('error') or k.get('errores'):return out
    rows=k.get('serie');rows=rows if isinstance(rows,list) else []
    # Sólo las siete fechas del periodo cerrado; un duplicado o dato diario ausente bloquea.
    rs=[r for r in rows if isinstance(r,dict) and dia(r.get('d')) and win[0]<=r['d']<=win[1]]
    if len(rs)!=7 or {r['d'] for r in rs}!={(ini+timedelta(days=i)).isoformat()for i in range(7)}:return out
    tipos=set();total_g=0;total_l=0
    for r in rs:
        m=r.get('medicion');m=m if isinstance(m,dict) else {}
        lectura=m.get('fecha_lectura');ld=dia(lectura[:10]) if isinstance(lectura,str) else None
        try:stamp=datetime.fromisoformat(lectura.replace('Z','+00:00')) if isinstance(lectura,str) else None
        except ValueError:stamp=None
        campos=m.get('campos_observados')
        if m.get('version')!=VERSION or m.get('fuente')!='meta_insights' or m.get('nivel')!='account' or m.get('periodo_valido')is not True or m.get('desde')!=r['d'] or m.get('hasta')!=r['d'] or not ld or ld<r['d'] or ld>hoy or stamp is None or m.get('cohorte')!=COHORTE or not isinstance(campos,list) or not all(isinstance(x,str) for x in campos) or not {'gasto','leads'}<=set(campos) or m.get('tipo_lead')not in LEADS or r.get('error') or r.get('errores') or not numero(r.get('gasto_meta')) or not numero(r.get('leads_meta'),True):return out
        tipos.add(m['tipo_lead']);total_g+=r['gasto_meta'];total_l+=r['leads_meta']
    if len(tipos)!=1 or not numero(total_g) or not numero(total_l,True):return out
    out.update(estado='medido',publicidad_sin_eventos_lead=total_g>=100 and total_l==0,gasto=total_g,eventos_lead=total_l,tipo_evento=next(iter(tipos)),desde=win[0],hasta=win[1],moneda='EUR')
    return out

def estado_integracion():
    return {'estado':'sin_dato','cohorte_crm_confirmada':False,'motivo':'No hay unión de eventos/identidades Meta→CRM documentada para esta ventana. Contadores independientes; no se calcula fuga.'}

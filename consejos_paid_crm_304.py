"""Gate puro para evaluaciones cuantitativas legacy del cerebro de alertas.
No cambia conectores, tickets ni reglas de otros departamentos. No inventa una
medición versionada: estas familias NO transportan evento/cohorte/objetivo.
"""
from copy import deepcopy
from datetime import datetime
import re

TIPOS={'pub_critico','pub_atencion','diag_pocos_leads','diag_leads_sin_citas','diag_citas_sin_ventas'}
SINTOMAS={'pocos_leads','leads_sin_citas','citas_sin_ventas'}
def _fecha(v,hoy):
    if not isinstance(v,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:\d{2})?)?',v):return None
    try:
        f=datetime.fromisoformat(v.replace('Z','+00:00').replace(' ','T'));h=datetime.fromisoformat(hoy)
        return v if f.date()<=h.date() else None
    except (ValueError,TypeError):return None

def aplica(c):
    if not isinstance(c,dict):return False
    if c.get('tipo') in TIPOS:return True
    # Un consejo de cartera mezclado no pierde urgencias por el mero cliente/tema.
    d=c.get('diagnostico')
    ref=c.get('referencia_anterior_304')
    if not isinstance(d,dict) and isinstance(ref,dict) and ref.get('version')=='304.1':d=ref.get('diagnostico')
    return c.get('tipo')=='jefa_cartera_roja' and isinstance(d,dict) and d.get('sintoma') in SINTOMAS

def neutralizar_consejo_paid_crm(c,hoy):
    if not aplica(c):return c
    out=deepcopy(c)
    previo=c.get('referencia_anterior_304')
    ref=deepcopy(previo) if isinstance(previo,dict) and previo.get('version')=='304.1' else {
        'version':'304.1','que':c.get('que'),'porque':c.get('porque'),'cifra':c.get('cifra'),'umbral':c.get('umbral'),
        'evidencia':deepcopy(c.get('evidencia')) if isinstance(c.get('evidencia'),list) else [],
        'diagnostico':deepcopy(c.get('diagnostico')),'prioridad':deepcopy(c.get('prioridad'))}
    # Las fechas antiguas de evidencia pueden venir de la construcción global:
    # nunca se reutilizan como fecha propia del evento/medición de esta alerta.
    fechas=sorted({_fecha(e.get('fecha'),hoy) for e in ref.get('evidencia',[]) if isinstance(e,dict) and _fecha(e.get('fecha'),hoy)})
    ev=[]
    for e in ref.get('evidencia',[]):
        if not isinstance(e,dict):continue
        ev.append({'dato':'Referencia anterior por contrastar: '+str(e.get('dato') or 'Señal de la copia anterior'),
                   'fecha':None,'fecha_referencia':_fecha(e.get('fecha'),hoy),'fuente':e.get('fuente'),'url':e.get('url'),
                   'estado':'sin_dato','alcance':'Fecha de referencia; no lectura propia del evento ni cohorte validada.'})
    paid=c.get('tipo') in {'pub_critico','pub_atencion','diag_pocos_leads'}
    contexto='publicidad' if paid else 'embudo CRM'
    referencia=str(ref.get('porque') or ref.get('que') or 'Señal de la copia anterior')
    out.update(referencia_anterior_304=ref,que=f'Contrasta la referencia anterior de {contexto} de este cliente',
               porque=f'Referencia anterior por contrastar: {referencia}. Comprueba fuente, ventana y definición del evento antes de concluir incumplimiento o modificar la operación.',
               cifra='Referencia anterior',umbral=None,confianza='media',
               confianza_porque='La alerta anterior no transporta una medición propia validada de fecha, evento, ventana y objetivo/cohorte. La fecha global de la copia y una regla documental no acreditan un dato del día.',
               evidencia=ev,diagnostico=None,metrica=None,prioridad=None,orden=0,gravedad='gris',
               motivo_orden=None,motivo_linea=None,cuando=None,accion=None,dato_en_duda=True,
               verificacion_304={'version':'304.1','estado':'referencia_por_contrastar','fuente_medicion':None,'fecha_medicion':None,
                   'fechas_referencia':fechas,'evento_acreditado':False,'cohorte_acreditada':False,'objetivo_acreditado':False})
    # Se conserva el criterio y su URL documental. No equivale al objetivo del cliente.
    if isinstance(out.get('criterio'),dict):
        cr=out['criterio'];base=str(cr.get('texto') or '')
        pref='Referencia documental; no acredita la medición ni el objetivo acordado con este cliente. '
        if not base.startswith(pref):cr['texto']=pref+base
    return out

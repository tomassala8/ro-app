"""Reglas operativas del Método RO. Lectura local; sin precios ni envíos en API.
La decisión humana manda sobre cadencias/roles de referencias antiguas.
"""
import json
import re
from datetime import date, timedelta
from pathlib import Path
from fuentes_verdad import clientes_activos as ACT
import metodo_evidencia_452 as EVIDENCIA452

AQUI=Path(__file__).resolve().parent
REGLAS=AQUI/'fuentes_metodo/reglas_operativas.json'
REUNIONES=AQUI/'fuentes_metodo/evidencias_reuniones.json'
REGLA_ID='seguimiento_quincenal_especialista'
S=None


def leer(p):
    try:return json.loads(p.read_text())
    except (OSError,ValueError):return {}


def dia(v):
    try:return date.fromisoformat(v) if isinstance(v,str) else None
    except ValueError:return None


def eventos_confirmados640(reuniones):
    """Identidad global antes del scope: conflicto invalida todas las variantes.
    No reconstruye identidad ni participación a partir de nombres o fechas.
    """
    grupos={}
    for ev in reuniones if isinstance(reuniones,list) else []:
        if not isinstance(ev,dict):continue
        eid=ev.get('evento_id')
        if not isinstance(eid,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,160}',eid):continue
        try:
            huella=json.dumps(ev,sort_keys=True,separators=(',', ':'),ensure_ascii=True,allow_nan=False)
        except (TypeError,ValueError,OverflowError):
            huella=None
        grupos.setdefault(eid,[]).append((huella,ev))
    out=[]
    for variantes in grupos.values():
        huellas={h for h,_ in variantes}
        if None in huellas or len(huellas)!=1:continue
        ev=variantes[0][1]
        if (not isinstance(ev.get('fuente'),str) or ev['fuente'] not in ('zoom','fathom','ghl','registro_local')
                or not isinstance(ev.get('cliente_id'),str) or not ev['cliente_id']
                or dia(ev.get('fecha')) is None or ev.get('celebrada') is not True
                or ev.get('cliente_confirmado') is not True
                or ev.get('rol_responsable_confirmado')!='trafficker'):continue
        out.append(ev)
    return out


def responsables(cid,asignaciones,personas,hoy):
    vigentes=[]
    for a in asignaciones:
        if not isinstance(a,dict):continue
        if a.get('cliente_id')!=cid or a.get('silla')!='trafficker':continue
        desde,hasta=dia(a.get('desde')),dia(a.get('hasta')) if a.get('hasta') else None
        if not desde or (a.get('hasta') and not hasta):return []
        if desde>hoy or (hasta and hasta<hoy):continue
        vigentes.append(a)
    # La fila pendiente o dudosa también participa en la ambigüedad de la silla.
    if len(vigentes)!=1:return []
    a=vigentes[0];p=personas.get(a.get('persona_id')) or {};roles=p.get('puestos')
    if (not p or p.get('estado')!='activo' or p.get('activo') is False or p.get('id')!=a.get('persona_id')
            or not isinstance(roles,list) or any(not isinstance(x,str) or not x for x in roles)
            or len(set(roles))!=len(roles) or 'trafficker' not in roles
            or a.get('principal') is not True or a.get('confianza')!='confirmada' or a.get('duda')
            or (a.get('suplencia') and not hasta)):return []
    return [p['id']]


def reglas_confirmadas(reglas):
    """Sólo política explícita compatible; conflictos no activan la cadencia."""
    if not isinstance(reglas,dict):return []
    regla=reglas.get('regla')
    if not isinstance(regla,dict) or regla.get('id')!=REGLA_ID or type(regla.get('cadencia_dias')) is not int or regla['cadencia_dias']!=15 or regla.get('responsable_role')!='trafficker':return []
    filas=reglas.get('clientes')
    if not isinstance(filas,list):return []
    cantidades={}
    for r in filas:
        if isinstance(r,dict) and isinstance(r.get('cliente_id'),str):
            cid=r['cliente_id'];cantidades[cid]=cantidades.get(cid,0)+1
    return [r for r in filas if isinstance(r,dict)
            and isinstance(r.get('cliente_id'),str) and r['cliente_id'] and r['cliente_id'].strip()==r['cliente_id']
            and cantidades[r['cliente_id']]==1 and r.get('estado_cohorte')=='confirmada'
            and type(r.get('cadencia_dias')) is int and r['cadencia_dias']==15
            and r.get('responsable_role')=='trafficker'
            and r.get('tipo_cohorte')=='metodo_actual_recurrente']


def sugerencias(reglas,asignaciones,personas,reuniones,cobertura,hoy,puede_ver):
    """No declara ausencia/incumplimiento a partir de un feed incompleto.
    Reunión válida requiere identidad de cliente, celebración y rol verificados.
    """
    if not isinstance(hoy,date):raise ValueError('Falta el día de referencia.')
    cobertura=cobertura if isinstance(cobertura,dict) else {}
    out=[]
    confirmados=eventos_confirmados640(reuniones)
    for r in reglas_confirmadas(reglas):
        cid=r.get('cliente_id')
        if not puede_ver(cid):continue
        owners=responsables(cid,asignaciones,personas,hoy)
        item={'cliente_id':cid,'regla_id':REGLA_ID,'cadencia_dias':15,'responsable_role':'trafficker',
              'responsables_ids':owners,'responsable_id':owners[0] if len(owners)==1 else None,'ultima_confirmada':None,'proxima_revision':None,
              'estado':'sin_dato','incumplimiento':None,'accion':'confirmar_ultima_reunion',
              'recomendacion':'Confirma la última reunión celebrada con el especialista de publicidad; no hay evidencia suficiente para calcular la próxima.',
              'fuentes_operativas':[{'tipo':'decision_humana','fecha':'2026-10-03','detalle':'Seguimiento cada 15 días con trafficker.'}]}
        if len(owners)!=1:
            item.update(estado='confirmar_responsable',accion='confirmar_responsable',
                        recomendacion='Confirma el trafficker responsable de esta cuenta antes de programar su seguimiento.')
        eventos=[]
        for ev in confirmados:
            if not isinstance(ev,dict):continue
            f=dia(ev.get('fecha'))
            if ev.get('cliente_id')==cid and f and f<=hoy and ev.get('celebrada') is True and ev.get('cliente_confirmado') is True and ev.get('rol_responsable_confirmado')=='trafficker' and ev.get('fuente'):
                eventos.append((f,ev))
        if eventos:
            f,ev=max(eventos,key=lambda x:x[0]);prox=f+timedelta(days=15)
            item['ultima_confirmada']=f.isoformat();item['proxima_revision']=prox.isoformat()
            item['fuentes_operativas'].append({'tipo':'reunion_celebrada','fecha':f.isoformat(),'fuente':ev['fuente'] if ev['fuente'] in ('zoom','fathom','ghl','registro_local') else 'evidencia interna verificada'})
            if len(owners)==1:
                if hoy<=prox:
                    item.update(estado='en_cadencia',accion='preparar_seguimiento',recomendacion='Prepara el siguiente seguimiento con el trafficker responsable.')
                elif cobertura.get('completa') is True and dia(cobertura.get('hasta'))==hoy and dia(cobertura.get('desde')) and dia(cobertura['desde'])<=f:
                    item.update(estado='revisar_cadencia',accion='proponer_seguimiento',recomendacion='La copia confirmada no muestra una reunión posterior dentro de la cadencia; revisa y propón el seguimiento. No se ha agendado ni enviado nada.')
                else:
                    item.update(estado='confirmar_recencia',accion='confirmar_ultima_reunion',recomendacion='La última reunión confirmada supera la cadencia, pero la cobertura es parcial: comprueba si hubo otra antes de proponer fecha.')
        out.append(item)
    return out


def estado_operativo(persona,real,crudo,hoy):
    filas_ps=[p for p in crudo.get('personas') or [] if isinstance(p,dict) and isinstance(p.get('id'),str)]
    ps={p['id']:p for p in filas_ps if sum(x['id']==p['id'] for x in filas_ps)==1}
    doc=leer(REUNIONES)
    if not isinstance(doc,dict):doc={}
    cobertura=doc.get('cobertura') if isinstance(doc.get('cobertura'),dict) else {}
    def puede(cid):
        return all(S.P.ver(p,{'tipo':'cliente_detalle','cliente_id':cid},S.P.contexto(p,crudo))['ok'] for p in (persona,real))
    reglas=leer(REGLAS)
    reglas=dict(reglas) if isinstance(reglas,dict) else {}
    filas_confirmadas=reglas_confirmadas(reglas)
    # Mismo catálogo operativo que el núcleo; permisos por rol no acreditan actividad.
    try:
        clientes=[r for r in crudo.get('clientes') or [] if isinstance(r,dict) and isinstance(r.get('id'),str)]
        activos={r['id'] for r in clientes if sum(c['id']==r['id'] for c in clientes)==1
            and r.get('activo') is not False and r.get('estado')!='baja' and ACT.es_activo_id(r['id']) is True}
    except (OSError,ValueError,TypeError,KeyError):
        activos=set()
    reglas['clientes']=[r for r in filas_confirmadas if r['cliente_id'] in activos]
    rows=sugerencias(reglas,crudo.get('asignaciones') or [],ps,doc.get('reuniones') or [],cobertura,hoy,puede)
    return {'hoy':hoy.isoformat(),'solo_lectura':real['id']!=persona['id'],'sugerencias':rows,
            'cohorte_actual_verificada':bool(rows),'cobertura_reuniones':{'completa':cobertura.get('completa') is True,'desde':cobertura.get('desde'),'hasta':cobertura.get('hasta')},
            'limite':'Son recomendaciones operativas. No se agenda ni se escribe en herramientas externas. Sin evidencia no se afirma incumplimiento.'}


def enganchar(Manejador,servir):
    global S
    S=servir
    orig=Manejador._api_get
    def get(self,ruta,q,real,persona):
        if ruta!='/api/metodo/sugerencias':return orig(self,ruta,q,real,persona)
        if S.E.nucleo_bloqueado:return self.responder(503,{'error':'Datos temporalmente bloqueados.'})
        try:
            rid,vid=real.get('id'),persona.get('id')
            real_actual,vista_actual=EVIDENCIA452.canonicas(S,rid,vid)
            politica=[leer(REGLAS),leer(REUNIONES)]
            inicial=EVIDENCIA452.firma(S,rid,vid,politica)
            hoy=dia(S.P.hoy_iso())
            if hoy is None:return self.responder(503,{'error':'Fecha de referencia no disponible.'})
            dto=estado_operativo(vista_actual,real_actual,S.E.crudo,hoy)
            dto,validar_evidencia=EVIDENCIA452.enriquecer(S,rid,vid,dto,
                reglas_confirmadas(politica[0]),hoy.isoformat())
            if inicial!=EVIDENCIA452.firma(S,rid,vid,[leer(REGLAS),leer(REUNIONES)]):
                raise EVIDENCIA452.CambioAutoridad()
            validar_evidencia()
        except EVIDENCIA452.CambioAutoridad:
            return self.responder(403,{'error':'El ámbito actual cambió o ya no permite esta lectura. Actualiza la vista.'})
        return self.responder(200,dto)
    Manejador._api_get=get

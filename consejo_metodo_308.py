"""Cadencia operativa confirmada: proyección pura y lectura local recortada.
Una revisión calculada no es una reunión agendada. No envía ni registra nada.
"""
from collections import Counter
from copy import deepcopy
import re
from datetime import date,timedelta
import metodo_cuentas as M
REGLA=M.REGLA_ID
ROLES={'direccion','operaciones','account','trafficker','jefa_publicidad','proyectos'}

def dia(v):
    if not isinstance(v,str):return None
    try:return date.fromisoformat(v) if date.fromisoformat(v).isoformat()==v else None
    except ValueError:return None

def persona_unica(personas,pid):
    xs=[p for p in personas if isinstance(p,dict) and p.get('id')==pid] if isinstance(personas,list) else []
    if not isinstance(pid,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,100}',pid) or len(xs)!=1:return None
    p=xs[0];roles=p.get('puestos')
    if (p.get('estado')!='activo' or p.get('activo') is False or not isinstance(roles,list) or not roles
            or any(not isinstance(x,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,100}',x) for x in roles)
            or len(set(roles))!=len(roles)):return None
    return p

def responsable_confirmado(cid,pid,personas,asignaciones,hoy):
    p=persona_unica(personas,pid)
    if not p or 'trafficker' not in (p.get('puestos') or []):return None
    vigentes=[]
    for a in asignaciones if isinstance(asignaciones,list) else []:
        if not isinstance(a,dict) or a.get('cliente_id')!=cid or a.get('silla')!='trafficker':continue
        desde,hasta=dia(a.get('desde')),dia(a.get('hasta')) if a.get('hasta') else None
        if not desde or (a.get('hasta') and not hasta):return None
        if desde>hoy or (hasta and hasta<hoy):continue
        vigentes.append(a)
    if len(vigentes)!=1:return None
    a=vigentes[0]
    return pid if a.get('persona_id')==pid and a.get('confianza')=='confirmada' and a.get('principal') is True and not a.get('duda') and not (a.get('suplencia') and not a.get('hasta')) else None

def proyectar_metodo308(doc,ids,personas,asignaciones,hoy):
    h=dia(hoy);out=[]
    if not h or not isinstance(doc,dict) or doc.get('hoy')!=hoy or not isinstance(doc.get('sugerencias'),list) or not isinstance(ids,(list,set,tuple)) or any(not isinstance(x,str) for x in ids) or len(set(ids))!=len(ids):return out
    counts=Counter(r.get('cliente_id') for r in doc['sugerencias'] if isinstance(r,dict) and isinstance(r.get('cliente_id'),str));scope=set(ids)
    for r in doc['sugerencias']:
        if not isinstance(r,dict) or not isinstance(r.get('cliente_id'),str) or r.get('cliente_id') not in scope or counts[r['cliente_id']]!=1 or r.get('regla_id')!=REGLA or type(r.get('cadencia_dias')) is not int or r['cadencia_dias']!=15 or r.get('responsable_role')!='trafficker' or r.get('incumplimiento') is not None:continue
        cid=r['cliente_id'];owners=r.get('responsables_ids');pid=r.get('responsable_id')
        owner=responsable_confirmado(cid,pid,personas,asignaciones,h) if isinstance(owners,list) and owners==[pid] else None
        ultima=dia(r.get('ultima_confirmada'));ultima=ultima if ultima and ultima<=h else None
        fuentes=r.get('fuentes_operativas') if isinstance(r.get('fuentes_operativas'),list) else []
        ev=[e for e in fuentes if isinstance(e,dict) and e.get('tipo')=='reunion_celebrada' and ultima and e.get('fecha')==ultima.isoformat() and e.get('fuente') in ('zoom','fathom','ghl','registro_local','evidencia interna verificada')]
        if not ev:ultima=None
        proxima=(ultima+timedelta(days=15)).isoformat() if ultima and r.get('proxima_revision')==(ultima+timedelta(days=15)).isoformat() else None
        cobertura=doc.get('cobertura_reuniones') if isinstance(doc.get('cobertura_reuniones'),dict) else {}
        a,b=dia(cobertura.get('desde')),dia(cobertura.get('hasta'))
        completa=bool(ultima and cobertura.get('completa') is True and a and b and a<=ultima<=b and b==h)
        if not owner:estado='confirmar_responsable';accion='Confirmar el trafficker activo y su asignación vigente antes de programar el seguimiento quincenal.'
        elif not ultima or not proxima:estado='confirmar_programacion';accion='Comprobar la última celebración y la programación del próximo seguimiento con el trafficker; registrar fuente y fecha.'
        elif h<=dia(proxima):estado='preparar_seguimiento';accion='Comprobar la programación del siguiente seguimiento y preparar los resultados con el trafficker.'
        elif not completa:estado='confirmar_recencia';accion='Contrastar si hubo otra reunión y confirmar la programación; la cobertura parcial no permite afirmar ausencia.'
        else:estado='revisar_cadencia';accion='Revisar el intervalo observado y proponer seguimiento con el trafficker, verificando la programación actual.'
        out.append({'cliente_id':cid,'regla_id':REGLA,'cadencia_dias':15,'responsable_role':'trafficker','responsable_id':owner,
                    'responsable_confirmado':bool(owner),'estado':estado,'ultima_confirmada':ultima.isoformat() if ultima else None,'proxima_revision':proxima,
                    'reunion_agendada':None,'incumplimiento':None,'accion':accion,'hoy':hoy,'cobertura_completa':completa,
                    'fuente_regla':'decision_humana_metodo_vigente','fuente_celebracion':ev[0].get('fuente') if ultima else None,
                    'contacto_semanal_account':'separado','reunion_mensual_account':'separada'})
    return out

def recomendaciones_metodo308(doc,ids,personas,asignaciones,hoy):
    out=[]
    for m in proyectar_metodo308(doc,ids,personas,asignaciones,hoy):
        motivo='Cadencia quincenal confirmada del método; no sustituye contacto semanal ni reunión mensual del account. '
        motivo+=('Responsable actual pendiente de confirmar.' if not m['responsable_confirmado'] else 'No hay evidencia suficiente de celebración o programación.' if not m['ultima_confirmada'] else 'Última celebración registrada; la próxima revisión calculada no acredita cita agendada.')
        evidencias=[{'fuente':'metodo_confirmado_local','fecha':hoy,'periodo':None,
            'cobertura':'regla_confirmada_no_historial_exhaustivo','vigencia':'actual',
            'texto':'Regla 15 días/trafficker confirmada; fecha de decisión/consulta no es fecha de una celebración.'}]
        if m['ultima_confirmada'] and m['fuente_celebracion']:
            evidencias.append({'fuente':'metodo_celebracion_confirmada','fecha':m['ultima_confirmada'],
                'periodo':None,'cobertura':'registro_confirmado_no_historial_exhaustivo','vigencia':'referencia_historica',
                'texto':f"Celebración confirmada el {m['ultima_confirmada']}; fuente: {m['fuente_celebracion']}. "
                        'No atribuye participantes ni responsable histórico; el responsable mostrado es el actual.'})
        if m['proxima_revision']:
            evidencias.append({'fuente':'metodo_revision_calculada','fecha':hoy,'periodo':None,
                'cobertura':'calculo_cadencia_no_agenda','vigencia':'actual',
                'texto':f"Próxima revisión calculada: {m['proxima_revision']} (última celebración confirmada +15 días). "
                        'La fecha de esta evidencia es la del cálculo; no acredita reunión programada o agendada.'})
        for area in ('paid','accounts'):
            out.append({'cliente_id':m['cliente_id'],'regla_id':REGLA if area=='paid' else REGLA+'_account','area':area,
                'titulo':'Confirmar seguimiento quincenal con trafficker' if area=='paid' else 'Verificar programación del seguimiento con el especialista',
                'motivo':motivo,'accion':m['accion'],'prioridad':3,'responsable_id':m['responsable_id'],'responsable_role':'trafficker',
                'responsable_estado':'asignacion_confirmada' if m['responsable_confirmado'] else 'asignacion_pendiente',
                'certeza':'regla_confirmada_ejecucion_por_contrastar','criterio_entrega':'Registrar responsable confirmado y fuente/fecha de celebración o programación; mantener revisión y cita agendada separadas.',
                'responsabilidad':'Seguimiento y comprobación, no ejecución acreditada','ejecutor_operativo':'trafficker','comprobador_role':'account' if area=='accounts' else 'trafficker',
                'modulo_destino':'reuniones','metodo_308':m,
                'evidencias':[dict(e) for e in evidencias]})
    return out

def _scope(S,real,vista):
    raw=S.E.crudo
    if S.E.nucleo_bloqueado:return None
    ps=[persona_unica(raw.get('personas'),x.get('id')) for x in (real,vista)]
    if any(not p or not set(p.get('puestos') or [])&ROLES or not S.ve_alguno(p,['reuniones']) for p in ps):return None
    if ps[0]['id']!=ps[1]['id'] and S.P.ver(ps[0],{'tipo':'ver_como'},S.P.contexto(ps[0],raw)).get('ok') is not True:return None
    clientes=raw.get('clientes') or [];counts=Counter(c.get('id') for c in clientes if isinstance(c,dict) and isinstance(c.get('id'),str));ids=[]
    for c in clientes:
        if not isinstance(c,dict):continue
        cid=c.get('id')
        if not isinstance(cid,str) or counts[cid]!=1 or c.get('activo') is False or c.get('estado')=='baja' or S.ACT.es_activo_id(cid) is not True:continue
        if all(S.P.ver(p,{'tipo':'cliente_detalle','cliente_id':cid},S.P.contexto(p,raw)).get('ok') is True for p in ps):ids.append(cid)
    return raw,ps,ids

def leer_metodo308(S,real,vista):
    """Sólo dos documentos locales existentes; nunca HTTP ni S global de305."""
    try:
        antes=_scope(S,real,vista)
        if not antes:return None
        raw,ps,ids=antes;ambito_inicial=deepcopy(antes);hoy=S.P.hoy_iso();h=dia(hoy)
        if not h:return None
        reglas=M.leer(M.REGLAS);reuniones=M.leer(M.REUNIONES)
        if not isinstance(reuniones,dict):return None
        politica_inicial=deepcopy((reglas,reuniones))
        personas={p['id']:p for p in raw.get('personas') or [] if isinstance(p,dict) and persona_unica(raw.get('personas'),p.get('id'))}
        rows=M.sugerencias(reglas,raw.get('asignaciones') or [],personas,reuniones.get('reuniones') or [],reuniones.get('cobertura') or {},h,lambda cid:cid in ids)
        despues=_scope(S,real,vista)
        if not despues or despues!=ambito_inicial:return None
        raw,ps,ids=despues
        rows=[r for r in rows if r.get('cliente_id') in ids]
        doc={'hoy':hoy,'sugerencias':rows,'cobertura_reuniones':reuniones.get('cobertura') or {}}
        # Sólo se devuelve el DTO final calculado sobre permisos/asignaciones actuales.
        resultado = {'hoy':hoy,'sugerencias':rows,'cobertura_reuniones':doc['cobertura_reuniones'],
                '_proyeccion_308':proyectar_metodo308(doc,ids,raw.get('personas') or [],raw.get('asignaciones') or [],hoy),
                '_ids_308':ids,'_personas_308':raw.get('personas') or [],'_asignaciones_308':raw.get('asignaciones') or []}
        if politica_inicial!=(M.leer(M.REGLAS),M.leer(M.REUNIONES)):return None
        final=_scope(S,real,vista)
        if not final or final!=ambito_inicial or S.P.hoy_iso()!=hoy:return None
        return resultado
    except (AttributeError,KeyError,TypeError,ValueError,OSError):return None


def filtrar_recomendaciones308(S,real,vista,resultado):
    actuales=leer_metodo308(S,real,vista)
    canon={}
    if actuales:
        canon={(r['cliente_id'],r['regla_id']):r for r in recomendaciones_metodo308(actuales,actuales['_ids_308'],actuales['_personas_308'],actuales['_asignaciones_308'],actuales['hoy'])}
    rs=[]
    for r in resultado.get('recomendaciones') or []:
        if not isinstance(r.get('metodo_308'),dict):rs.append(r)
        elif (r.get('cliente_id'),r.get('regla_id')) in canon:rs.append(canon[(r['cliente_id'],r['regla_id'])])
    return {**resultado,'recomendaciones':rs}

TIPOS308={'metodo_seguimiento_15d_paid','metodo_seguimiento_15d_accounts'}
def candidatos_metodo308(S,real,vista):
    d=leer_metodo308(S,real,vista)
    if not d:return []
    recos=recomendaciones_metodo308(d,d['_ids_308'],d['_personas_308'],d['_asignaciones_308'],d['hoy'])
    ps=persona_unica(S.E.crudo.get('personas'),vista.get('id'));roles=set(ps.get('puestos') or []) if ps else set()
    areas={'paid','accounts'} if roles & {'direccion','operaciones','proyectos'} else {'accounts'} if 'account' in roles else {'paid'}
    out=[]
    for r in recos:
        if r['area'] not in areas:continue
        clientes=[c for c in S.E.crudo.get('clientes') or [] if isinstance(c,dict) and c.get('id')==r['cliente_id']]
        nombre=clientes[0].get('nombre') if len(clientes)==1 else None
        nombre=nombre.strip() if isinstance(nombre,str) and 0<len(nombre.strip())<=160 and not any(x in nombre for x in ('\n','\r')) else r['cliente_id']
        m=r['metodo_308'];out.append({'id':'metodo15:'+r['area']+':'+r['cliente_id'],'tipo':'metodo_seguimiento_15d_'+r['area'],
            'cliente_id':r['cliente_id'],'pantallas':['mi-dia','reuniones','ficha','prioridades-cliente','captacion'] if r['area']=='paid' else ['mi-dia','reuniones','ficha','prioridades-cliente'],
            'requiere':['reuniones'],'dueno':vista['id'],'quien':'Tú','personal':False,'cliente':nombre,'que':r['titulo']+' · '+nombre,'porque':r['motivo']+' '+r['accion'],
            'ir':'#/reuniones','ir_texto':'Revisar seguimiento','accion':None,'cuando':None,'cifra':None,'umbral':None,'metrica':None,'orden':0,'prioridad':None,'gravedad':'gris',
            'confianza':'media','confianza_porque':'Regla quincenal confirmada; programación y celebración deben contrastarse con su evidencia. No acredita cita agendada ni incumplimiento.',
            'criterio':{'id':REGLA,'regla':'Seguimiento cada 15 días con trafficker','texto':'Decisión operativa vigente. Separada del contacto semanal y de la reunión mensual del account.','url':None},
            'fuente':{'texto':'Método confirmado local · seguimiento quincenal','url':None},'evidencia':[{'dato':r['motivo'],'fecha':d['hoy'],'fuente':'Decisión y consulta operativa; no fecha de reunión','url':None}],
            'metodo_308':m,'responsable_id':m['responsable_id'],'responsable_role':'trafficker','origen':'reglas'})
    return out

def normalizar_candidato_metodo308(c,S,real,vista):
    if not isinstance(c,dict) or c.get('tipo') not in TIPOS308:return c
    matches=[r for r in candidatos_metodo308(S,real,vista) if r['id']==c.get('id') and r['tipo']==c.get('tipo') and r['cliente_id']==c.get('cliente_id')]
    if len(matches)!=1:return None
    # Sólo contenido canónico recortado vigente: el LLM no convierte revisión en cita.
    out=matches[0]
    for k in ('valoracion','valoracion_nota'):
        if k in c:out[k]=c[k]
    return out

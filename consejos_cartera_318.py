"""Agregado exacto de críticos en la copia canónica autorizada; sin importes."""
from collections import Counter
from datetime import date
TIPO='ops_cartera_riesgo'
def dia(v):
    if not isinstance(v,str):return None
    try:return v if date.fromisoformat(v).isoformat()==v else None
    except ValueError:return None
def actual(S,real,vista):
    try:
        if S.E.nucleo_bloqueado:return None
        raw=S.E.crudo;ps=[]
        for actor in (real,vista):
            xs=[p for p in raw.get('personas') or [] if p.get('id')==actor.get('id')]
            if len(xs)!=1 or xs[0].get('estado')!='activo' or xs[0].get('activo') is False or not set(xs[0].get('puestos') or [])&{'operaciones','direccion'}:return None
            ps.append(xs[0])
        if any(not S.ve_alguno(p,['en-rojo']) for p in ps):return None
        if ps[0]['id']!=ps[1]['id'] and S.P.ver(ps[0],{'tipo':'ver_como'},S.P.contexto(ps[0],raw)).get('ok') is not True:return None
        cs=raw.get('clientes') or [];ns=Counter(c.get('id') for c in cs if isinstance(c,dict) and isinstance(c.get('id'),str));ids=[]
        for c in cs:
            cid=c.get('id')
            if not isinstance(cid,str) or ns[cid]!=1 or S.ACT.es_activo_id(cid) is not True:continue
            if all(S.P.ver(p,{'tipo':'cliente_detalle','cliente_id':cid},S.P.contexto(p,raw)).get('ok') is True for p in ps):ids.append(cid)
        return {'ids':sorted(ids),'hoy':S.P.hoy_iso(),'firma':[(p['id'],p['estado'],tuple(p.get('puestos') or [])) for p in ps]}
    except (AttributeError,KeyError,TypeError,ValueError):return None

def normalizar_agregado318(c,doc,ids,hoy):
    """Pure whitelist: no texto/nombres/cuotas del caché o documento agregado."""
    base={'id':'op:criticos','tipo':TIPO,'cliente_id':None,'cliente':None,'dueno':c.get('dueno'),'quien':'Tú',
        'pantallas':['mi-dia','en-rojo'],'requiere':['en-rojo'],'personal':False,'accion':None,'ir':'#/en-rojo','ir_texto':'Ver En rojo',
        'cuando':'Contrastar la copia','origen':'reglas','umbral':None,'prioridad':None,'diagnostico':None,'metrica':None,'cifra':None,
        'que':'Contrasta los clientes críticos de tu ámbito autorizado','porque':'La referencia anterior no acredita el recuento actual; consulta En rojo y verifica sus planes.',
        'gravedad':'gris','orden':0,'confianza':'media','confianza_porque':'Fecha o cobertura canónica insuficiente; no se afirma un total actual.',
        'criterio':{'id':'gravedad_canonica_ambito_autorizado','texto':'Consultar gravedad canónica y plan vigente; no atribuye cuota, responsable ni ejecución.','url':None},
        'fuente':{'texto':'En rojo · copia canónica autorizada','url':None},'evidencia':[],
        'verificacion_318':{'actual':False,'fecha':None,'cobertura':'por_contrastar','criticos_observados':None}}
    if not dia(hoy) or not isinstance(doc,dict) or not isinstance(ids,list) or any(not isinstance(x,str) for x in ids) or len(set(ids))!=len(ids):return base
    if doc.get('generado')!=hoy or not isinstance(doc.get('clientes'),list):return base
    rows=doc['clientes'];ns=Counter(r.get('cliente_id') for r in rows if isinstance(r,dict) and isinstance(r.get('cliente_id'),str));rs=[]
    for cid in ids:
        fs=[r for r in rows if isinstance(r,dict) and r.get('cliente_id')==cid]
        if ns[cid]!=1 or len(fs)!=1 or fs[0].get('gravedad') not in ('critico','atencion','bien'):return base
        rs.append(fs[0])
    if not ids:return base
    n=sum(r.get('gravedad')=='critico' for r in rs)
    base.update(que=f'Revisa los planes de {n} clientes críticos en tu copia autorizada' if n else 'Contrasta los planes y señales de tu copia autorizada',
        porque=f'La gravedad canónica registra {n} clientes críticos entre {len(ids)} clientes visibles. Consulta el plan y su revisión; este recuento no acredita ejecución, aceptación ni inventario global.',
        cifra=f'{n} clientes críticos observados',cuando='Revisar planes',gravedad='alta' if n else 'gris',orden=230 if n else 0,
        confianza_porque='Coinciden IDs y gravedad en la copia fechada de hoy; cobertura de fuentes operativas parcial, no inventario global.',
        evidencia=[{'dato':f'{n} críticos en {len(ids)} clientes autorizados; sin cuotas ni responsables inferidos.','fecha':hoy,'fuente':'En rojo · copia local canónica','url':None}],
        metrica={'valor':n,'mejor':'baja'},verificacion_318={'actual':True,'fecha':hoy,'cobertura':'ambito_autorizado_copia_parcial','criticos_observados':n})
    return base

def normalizar_consejo_cartera318(c,S,real,vista,lector):
    if not isinstance(c,dict) or c.get('tipo')!=TIPO:return c
    if c.get('id')!='op:criticos' or c.get('dueno')!=vista.get('id'):return None
    antes=actual(S,real,vista)
    if antes is None:return None
    try:doc=lector(real,vista,'verdad/clientes')
    except (OSError,ValueError,TypeError,RuntimeError):doc=None
    despues=actual(S,real,vista)
    if despues is None or despues!=antes:return None
    return normalizar_agregado318(c,doc,despues['ids'],despues['hoy'])

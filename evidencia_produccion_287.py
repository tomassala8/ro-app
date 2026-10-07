"""Whitelist275: añade descriptores a filas YA autorizadas; nunca amplía el DTO."""
import copy,collections,re,datetime as dt

def aplicar(dto,candidato,activos,personas,sha_actual,sha_esperado):
    if not isinstance(dto,dict) or not isinstance(candidato,dict) or candidato.get('version')!='275.1' or candidato.get('cobertura')!='parcial':raise ValueError('Esquema')
    if not isinstance(sha_actual,str) or not re.fullmatch('[a-f0-9]{64}',sha_actual) or sha_actual!=sha_esperado:raise ValueError('SHA')
    for k in ('corte','ayer','lunes'):
        if not isinstance(candidato.get(k),str):raise ValueError('Fecha')
    try:
        corte=dt.datetime.fromisoformat(candidato['corte'].replace('Z','+00:00'));ayer=dt.date.fromisoformat(candidato['ayer']);lunes=dt.date.fromisoformat(candidato['lunes'])
        from zoneinfo import ZoneInfo
        fecha=corte.astimezone(ZoneInfo('Europe/Madrid')).date()
        if corte.tzinfo is None or ayer!=fecha-dt.timedelta(days=1) or lunes!=fecha-dt.timedelta(days=fecha.weekday()) or candidato.get('zona')!='Europe/Madrid':raise ValueError('Ventana')
    except (TypeError,ValueError):raise ValueError('Ventana')
    filas=candidato.get('proyectos');creadores=candidato.get('creadores')
    if not isinstance(filas,list) or not isinstance(creadores,list):raise ValueError('Filas')
    by={}
    def count(v):return isinstance(v,int) and not isinstance(v,bool) and v>=0
    for f in filas:
        cid=f.get('cliente_id') if isinstance(f,dict) else None
        if not isinstance(cid,str) or cid in by:raise ValueError('ID')
        for nombre in ('cierres_ayer','creadas_semana'):
            n=f.get(nombre+'_observaciones')
            if not count(n) or f.get(nombre)!=(n if n else None):raise ValueError('Conteo')
        if f.get('cobertura')!='parcial' or f.get('actor_cierre') is not None:raise ValueError('Autoría')
        by[cid]=f
    out=copy.deepcopy(dto);rows=out.get('proyectos',[])
    if not isinstance(rows,list):raise ValueError('Proyectos')
    nc=collections.Counter(f.get('cliente_id') for f in rows if isinstance(f,dict));scope={cid for cid,n in nc.items() if isinstance(cid,str) and n==1 and cid in activos};meta={'version':'275.1','corte':candidato['corte'],'ayer':candidato['ayer'],'lunes':candidato['lunes'],'zona':'Europe/Madrid','cobertura':'parcial','sha256_candidato':sha_actual,'fuente':'clickup_cache_local','aceptacion_entrega':None}
    for f in rows:
        cid=f.get('cliente_id') if isinstance(f,dict) else None
        if cid not in scope or cid not in by:continue
        r=by[cid];f['_evidencia_produccion_275']={**meta,'cliente_id':cid,'cierres_ayer':r['cierres_ayer'],'cierres_ayer_observaciones':r['cierres_ayer_observaciones'],'creadas_semana':r['creadas_semana'],'creadas_semana_observaciones':r['creadas_semana_observaciones'],'actor_cierre':None,'campo_cierre':'date_done_or_closed+catalogo_actual_terminal','no_planificadas':None,'rompen_semanal':None}
    agg=collections.Counter();seen=set()
    for r in creadores:
        if not isinstance(r,dict):raise ValueError('Creador')
        key=(r.get('cliente_id'),r.get('persona_id'))
        if key in seen:raise ValueError('Creador repetido')
        seen.add(key)
        if not count(r.get('creadas_semana')) or r['creadas_semana']==0 or r.get('cobertura')!='parcial':raise ValueError('Creación')
        if key[0] in scope and key[1] in personas:agg[key[1]]+=r['creadas_semana']
    prows=out.get('personas',[])
    if not isinstance(prows,list):raise ValueError('Personas')
    pc=collections.Counter(p.get('persona_id') for p in prows if isinstance(p,dict))
    for p in prows:
        pid=p.get('persona_id') if isinstance(p,dict) else None
        if pid not in personas or pc[pid]!=1:continue
        p['_evidencia_equipo_275']={**meta,'persona_id':pid,'creadas_semana':agg.get(pid) or None,'creadas_semana_observaciones':agg.get(pid,0),'criterio':'creador_ID_canonico+clientes_del_DTO','cierres_ayer':None,'al_planning':None,'rompen_semanal':None,'tipos_tarea':None}
    return out

# Aplicación opcional después de recorte: el candidato privado nunca se sirve como archivo.
import os,stat,hashlib,json
from pathlib import Path
from operaciones_registros_269 import unica,ErrorRegistro
SHA275='f2e568ced88d880a9df5aedde752d51d5d982ac52d7cb7b190fc9bf299bc49a2'
ENV='RO_EVIDENCIA_PRODUCCION_275'

def _leer_privado287(path,sha_esperado,limite=131072):
    p=Path(path)
    if not p.is_absolute():raise ValueError('Ruta')
    fd=os.open('/',os.O_RDONLY|os.O_DIRECTORY)
    try:
        for part in p.parts[1:-1]:
            nf=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd);os.close(fd);fd=nf
        ff=os.open(p.name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=fd)
        try:
            st=os.fstat(ff)
            if not stat.S_ISREG(st.st_mode) or st.st_nlink!=1 or st.st_uid!=os.getuid() or stat.S_IMODE(st.st_mode)!=0o600 or not 0<st.st_size<=limite:raise ValueError('Archivo')
            with os.fdopen(os.dup(ff),'rb') as f:raw=f.read(limite+1)
            fin=os.fstat(ff)
            if len(raw)!=st.st_size or (st.st_size,st.st_mtime_ns)!=(fin.st_size,fin.st_mtime_ns):raise ValueError('Cambio')
        finally:os.close(ff)
    finally:os.close(fd)
    sha=hashlib.sha256(raw).hexdigest()
    if sha!=sha_esperado:raise ValueError('SHA')
    def rechazar(v):raise ValueError('Número JSON')
    return json.loads(raw,parse_constant=rechazar),sha

def leer_candidato287(path):return _leer_privado287(path,SHA275)

def _enriquecer275(dto,S,real,vista):
    # No usa el candidato como fuente de identidad ni amplía las filas del DTO.
    if not isinstance(dto,dict):return dto
    base=copy.deepcopy(dto)
    for nombre,key in (('proyectos','_evidencia_produccion_275'),('personas','_evidencia_equipo_275')):
        for row in base.get(nombre,[]) if isinstance(base.get(nombre),list) else []:
            if isinstance(row,dict):row.pop(key,None)
    path=os.environ.get(ENV)
    if not path:return base
    try:
        if S.E.nucleo_bloqueado:raise ValueError('Núcleo')
        catalogo=S.E.crudo
        ps=[unica(catalogo.get('personas'),p.get('id')) for p in (real,vista)]
        if any(not S.ve_alguno(p,['produccion']) for p in ps):raise ValueError('Módulo')
        if real['id']!=vista['id'] and S.P.ver(ps[0],{'tipo':'ver_como'},S.P.contexto(ps[0],catalogo)).get('ok') is not True:raise ValueError('Vista')
        cs=catalogo.get('clientes') or [];ct=collections.Counter(c.get('id') for c in cs if isinstance(c,dict))
        activos={c['id'] for c in cs if isinstance(c,dict) and isinstance(c.get('id'),str) and ct[c['id']]==1 and S.ACT.es_activo_id(c['id']) is True and all(S.P.ver(p,{'tipo':'cliente_detalle','cliente_id':c['id']},S.P.contexto(p,catalogo)).get('ok') is True for p in ps)}
        personas=set()
        for row in base.get('personas',[]):
            pid=row.get('persona_id') if isinstance(row,dict) else None
            try:unica(catalogo.get('personas'),pid)
            except ErrorRegistro:continue
            if all(S.P.ver(p,{'tipo':'horas_persona','persona_id':pid},S.P.contexto(p,catalogo)).get('ok') is True for p in ps):personas.add(pid)
        candidato,sha=leer_candidato287(path)
        corte=dt.datetime.fromisoformat(candidato['corte'].replace('Z','+00:00'))
        if corte>dt.datetime.now(dt.timezone.utc):raise ValueError('Futuro')
        from zoneinfo import ZoneInfo
        if corte.astimezone(ZoneInfo('Europe/Madrid')).date()>dt.date.fromisoformat(S.P.hoy_iso()):raise ValueError('Día futuro')
        if S.E.crudo is not catalogo or S.E.nucleo_bloqueado:raise ValueError('Cambio de ámbito')
        ps=[unica(S.E.crudo.get('personas'),p['id']) for p in ps]
        if any(not S.ve_alguno(p,['produccion']) for p in ps):raise ValueError('Módulo revocado')
        if real['id']!=vista['id'] and S.P.ver(ps[0],{'tipo':'ver_como'},S.P.contexto(ps[0],S.E.crudo)).get('ok') is not True:raise ValueError('Vista revocada')
        for pid in personas:unica(S.E.crudo.get('personas'),pid)
        ct_final=collections.Counter(c.get('id') for c in (S.E.crudo.get('clientes') or []) if isinstance(c,dict))
        if any(ct_final[cid]!=1 for cid in activos):raise ValueError('Cliente ambiguo después de lectura')
        if any(S.ACT.es_activo_id(cid) is not True or any(S.P.ver(p,{'tipo':'cliente_detalle','cliente_id':cid},S.P.contexto(p,S.E.crudo)).get('ok') is not True for p in ps) for cid in activos):raise ValueError('Cliente revocado')
        if any(any(S.P.ver(p,{'tipo':'horas_persona','persona_id':pid},S.P.contexto(p,S.E.crudo)).get('ok') is not True for p in ps) for pid in personas):raise ValueError('Persona revocada')
        return aplicar(base,candidato,activos,personas,sha,SHA275)
    except (OSError,ValueError,TypeError,KeyError,AttributeError,ErrorRegistro):return base

# 296 mantiene la puerta existente y añade una capa independiente de sólo lectura.
def enriquecer287(dto,S,real,vista):
    base=_enriquecer275(dto,S,real,vista)
    return enriquecer296(base,S,real,vista)

SHA296='a6a010afd792d87263cb4e4b0854a9848e3e16e9d8a5aaab237e0de4f9d02b50'
ENV296='RO_COMPARACION_SEMANAL_296'
KEY296='_comparacion_semanal_296'
def leer_candidato296(path):return _leer_privado287(path,SHA296,262144)

def validar_ventanas296(candidato):
    from zoneinfo import ZoneInfo
    if candidato.get('version')!='296.1' or candidato.get('fuente')!='clickup_cache_local' or candidato.get('cobertura')!='parcial' or candidato.get('historia_transiciones_confirmada') is not False or candidato.get('comparacion_rendimiento') is not None or candidato.get('columna_original_semana_pasada')!='rompen_semanal;no_sustituir_por_creaciones':raise ValueError('Contrato296')
    corte=dt.datetime.fromisoformat(candidato['corte_utc'].replace('Z','+00:00'))
    if corte.tzinfo is None or corte.utcoffset()!=dt.timedelta(0):raise ValueError('Corte296')
    mad=ZoneInfo('Europe/Madrid');local=corte.astimezone(mad);lunes=(local-dt.timedelta(days=local.weekday())).replace(hour=0,minute=0,second=0,microsecond=0);prev=lunes-dt.timedelta(days=7)
    ventanas=candidato.get('ventanas')
    if not isinstance(ventanas,dict) or set(ventanas)!= {'actual','anterior'}:raise ValueError('Ventanas296')
    def utc(v):return v.astimezone(dt.timezone.utc).isoformat().replace('+00:00','Z')
    for key,a,b,inc in [('actual',lunes,corte,True),('anterior',prev,lunes,False)]:
        esperado={'desde_utc':utc(a),'hasta_utc':utc(b),'hasta_inclusiva':inc,'desde_madrid':a.astimezone(mad).isoformat(),'hasta_madrid':b.astimezone(mad).isoformat(),'zona':'Europe/Madrid','cobertura':'parcial'}
        if ventanas[key]!=esperado:raise ValueError('Ventana296 distinta')
    return corte

def _metrica296(m,p,campo,atribucion):
    if not isinstance(m,dict) or m.get('ventana')!=p or m.get('campo')!=campo or m.get('atribucion')!=atribucion or m.get('cobertura')!='parcial' or m.get('cero_no_acredita_ausencia') is not True:raise ValueError('Métrica296')
    n=m.get('observaciones')
    if type(n) is not int or not 0<=n<=9007199254740991 or m.get('valor')!=(n if n else None) or isinstance(m.get('valor'),bool):raise ValueError('Conteo296')
    # Sólo campos cerrados del contrato: nunca textos/otros campos del candidato.
    return {'valor':m['valor'],'observaciones':n,'campo':campo,'ventana':p,'atribucion':atribucion,'cobertura':'parcial','cero_no_acredita_ausencia':True}

def aplicar296(dto,candidato,activos,personas,sha_actual,sha_esperado):
    if not isinstance(dto,dict) or not isinstance(candidato,dict) or sha_actual!=sha_esperado or not isinstance(sha_actual,str) or not re.fullmatch('[a-f0-9]{64}',sha_actual):raise ValueError('Fuente296')
    validar_ventanas296(candidato)
    rows=candidato.get('proyectos');authors=candidato.get('creadores')
    if not isinstance(rows,list) or not isinstance(authors,list):raise ValueError('Filas296')
    by={};pairs=set();creadores=[]
    for r in rows:
        cid=r.get('cliente_id') if isinstance(r,dict) else None
        if not isinstance(cid,str) or not cid or cid in by or r.get('actor_cierre') is not None or r.get('aceptacion_entrega') is not None:raise ValueError('Proyecto296')
        sanitized={}
        for tipo,campo in [('creadas','date_created'),('finales','date_done_or_closed+catalogo_actual_terminal')]:
            if not isinstance(r.get(tipo),dict) or set(r[tipo])!={'actual','anterior'}:raise ValueError('Periodos296')
            sanitized[tipo]={p:_metrica296(r[tipo][p],p,campo,'proyecto')for p in ('actual','anterior')}
        by[cid]=sanitized
    for r in authors:
        cid=r.get('cliente_id')if isinstance(r,dict)else None;pid=r.get('persona_id')if isinstance(r,dict)else None
        if not isinstance(cid,str)or cid not in by or not isinstance(pid,str)or not pid or (cid,pid)in pairs or any(r.get(k)is not None for k in ('al_planning','fuegos_directos','rompen_semanal')):raise ValueError('Creador296')
        pairs.add((cid,pid));values=r.get('creadas')
        if not isinstance(values,dict) or set(values)!={'actual','anterior'}:raise ValueError('Creaciones296')
        creadores.append((cid,pid,{p:_metrica296(values[p],p,'date_created+creator_ID_canonico','creador')for p in ('actual','anterior')}))
    # La suma canónica no puede exceder la cantidad de creaciones del proyecto.
    cc=collections.Counter()
    for cid,pid,values in creadores:
        for p in values:cc[cid,p]+=values[p]['observaciones']
    if any(cc[cid,p]>r['creadas'][p]['observaciones']for cid,r in by.items()for p in ('actual','anterior')):raise ValueError('Creadores296 exceden proyecto')
    out=copy.deepcopy(dto);pr=out.get('proyectos',[]);ps=out.get('personas',[])
    if not isinstance(pr,list) or not isinstance(ps,list):raise ValueError('DTO296')
    nc=collections.Counter(r.get('cliente_id')for r in pr if isinstance(r,dict));scope={cid for cid,n in nc.items()if n==1 and isinstance(cid,str) and cid in activos and cid in by}
    meta={'version':'296.1','sha256_candidato':sha_actual,'fuente':'clickup_cache_local','corte_utc':candidato['corte_utc'],'ventanas':copy.deepcopy(candidato['ventanas']),'cobertura':'parcial','columna_original_semana_pasada':candidato['columna_original_semana_pasada'],'actor_cierre':None,'aceptacion_entrega':None,'comparacion_rendimiento':None}
    for r in pr:
        if isinstance(r,dict) and r.get('cliente_id')in scope:r[KEY296]={**meta,'cliente_id':r['cliente_id'],**copy.deepcopy(by[r['cliente_id']])}
    agg=collections.defaultdict(collections.Counter)
    for cid,pid,values in creadores:
        if cid in scope and pid in personas:
            for p in values:agg[pid][p]+=values[p]['observaciones']
    np=collections.Counter(r.get('persona_id')for r in ps if isinstance(r,dict))
    for r in ps:
        pid=r.get('persona_id')if isinstance(r,dict)else None
        if pid not in personas or np[pid]!=1:continue
        values={p:_metrica296({'valor':agg[pid][p]or None,'observaciones':agg[pid][p],'ventana':p,'campo':'date_created+creator_ID_canonico','atribucion':'creador','cobertura':'parcial','cero_no_acredita_ausencia':True},p,'date_created+creator_ID_canonico','creador')for p in ('actual','anterior')}
        r[KEY296]={**meta,'persona_id':pid,'cliente_ids_scope':sorted(scope),'creadas':values,'criterio':'creador_ID_canonico+clientes_del_DTO','rompen_semanal':None,'al_planning':None,'fuegos_directos':None}
    return out

def enriquecer296(dto,S,real,vista):
    if not isinstance(dto,dict):return dto
    base=copy.deepcopy(dto)
    for key in ('proyectos','personas'):
        for r in base.get(key,[])if isinstance(base.get(key),list)else []:
            if isinstance(r,dict):r.pop(KEY296,None)
    path=os.environ.get(ENV296)
    if not path:return base
    try:
        if S.E.nucleo_bloqueado:raise ValueError('Núcleo296')
        catalogo=S.E.crudo
        def actores():
            ps=[unica(S.E.crudo.get('personas'),a.get('id'))for a in (real,vista)]
            if any(not S.ve_alguno(p,['produccion'])for p in ps):raise ValueError('Módulo296')
            if real['id']!=vista['id'] and S.P.ver(ps[0],{'tipo':'ver_como'},S.P.contexto(ps[0],S.E.crudo)).get('ok')is not True:raise ValueError('Vista296')
            return ps
        ps=actores();cs=catalogo.get('clientes')or[];counts=collections.Counter(c.get('id')for c in cs if isinstance(c,dict));rowids={r.get('cliente_id')for r in base.get('proyectos',[])if isinstance(r,dict)and isinstance(r.get('cliente_id'),str)}
        activos={cid for cid in rowids if counts[cid]==1 and S.ACT.es_activo_id(cid)is True and all(S.P.ver(p,{'tipo':'cliente_detalle','cliente_id':cid},S.P.contexto(p,catalogo)).get('ok')is True for p in ps)}
        personas=set()
        for r in base.get('personas',[]):
            pid=r.get('persona_id')if isinstance(r,dict)else None
            try:unica(catalogo.get('personas'),pid)
            except ErrorRegistro:continue
            if all(S.P.ver(p,{'tipo':'horas_persona','persona_id':pid},S.P.contexto(p,catalogo)).get('ok')is True for p in ps):personas.add(pid)
        candidato,sha=leer_candidato296(path);corte=validar_ventanas296(candidato)
        from zoneinfo import ZoneInfo
        if corte>dt.datetime.now(dt.timezone.utc) or corte.astimezone(ZoneInfo('Europe/Madrid')).date()>dt.date.fromisoformat(S.P.hoy_iso()):raise ValueError('Futuro296')
        if S.E.nucleo_bloqueado or S.E.crudo is not catalogo:raise ValueError('Epoch296')
        ps=actores();finalcounts=collections.Counter(c.get('id')for c in catalogo.get('clientes',[])if isinstance(c,dict))
        if any(finalcounts[cid]!=1 or S.ACT.es_activo_id(cid)is not True or any(S.P.ver(p,{'tipo':'cliente_detalle','cliente_id':cid},S.P.contexto(p,catalogo)).get('ok')is not True for p in ps)for cid in activos):raise ValueError('Cliente revocado296')
        for pid in personas:
            unica(catalogo.get('personas'),pid)
            if any(S.P.ver(p,{'tipo':'horas_persona','persona_id':pid},S.P.contexto(p,catalogo)).get('ok')is not True for p in ps):raise ValueError('Persona revocada296')
        return aplicar296(base,candidato,activos,personas,sha,SHA296)
    except (OSError,ValueError,TypeError,KeyError,AttributeError,ErrorRegistro):return base

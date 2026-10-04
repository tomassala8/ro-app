"""Candidato aislado offline. Sin IO al importar ni proveedor. No activa API467.

Únicamente CLI explícita puede leer caches existentes y escribir agregados en R.
Motor aislado y SHA requerido; no copia eventos/IDs privados en el depósito.
"""
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import tempfile
from collections import Counter
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

NUEVAS_INCIDENCIAS = frozenset({'event_id_ambito_conflictivo'})
MAX = 5_000_000

def sha(b): return hashlib.sha256(b).hexdigest()
def serial(d): return (json.dumps(d,sort_keys=True,ensure_ascii=False,allow_nan=False,separators=(',',':'))+'\n').encode()
def estricto(b):
    def pares(xs):
        d={}
        for k,v in xs:
            if k in d: raise ValueError('json_duplicado')
            d[k]=v
        return d
    return json.loads(b,object_pairs_hook=pares,parse_constant=lambda _: (_ for _ in ()).throw(ValueError('json_no_finito')))

def marca(p):
    p=Path(p)
    if not p.is_absolute() or '..' in p.parts: raise ValueError('ruta')
    for q in (p,*p.parents):
        if q.is_symlink(): raise ValueError('enlace')
    s=p.lstat()
    if not stat.S_ISREG(s.st_mode) or s.st_nlink!=1 or s.st_size>MAX: raise ValueError('archivo')
    return (s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns,s.st_mode,s.st_nlink)

def leer(p,privado=False):
    p=Path(p);before=marca(p)
    if privado and stat.S_IMODE(before[5])!=0o600: raise ValueError('modo_privado')
    fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    try:
        s=os.fstat(fd)
        if (s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns,s.st_mode,s.st_nlink)!=before: raise ValueError('rotacion')
        with os.fdopen(fd,'rb',closefd=False) as f: b=f.read(MAX+1)
        if len(b)>MAX or marca(p)!=before: raise ValueError('rotacion')
        return b
    finally: os.close(fd)

def puro(b,adaptador=None):
    tree=ast.parse(b)
    permitidos={'collections','datetime','re','hashlib','json','math'}
    nodes=[]
    for n in tree.body:
        if isinstance(n,(ast.Import,ast.ImportFrom)):
            mods=[a.name for a in n.names] if isinstance(n,ast.Import) else [n.module]
            if n.module=='embudo_eventos' if isinstance(n,ast.ImportFrom) else False:
                if adaptador is None or {x.name for x in n.names}!={'_hora','calcular'}: raise ValueError('import_motor')
                continue
            if any(m not in permitidos for m in mods): raise ValueError('import_no_puro')
            nodes.append(n)
        elif isinstance(n,(ast.FunctionDef,ast.Assign,ast.Expr)):
            if isinstance(n,ast.Expr) and not (isinstance(n.value,ast.Constant) and isinstance(n.value.value,str)): raise ValueError('efecto_top')
            if isinstance(n,ast.Assign) and any(isinstance(x,ast.Call) for x in ast.walk(n.value)): raise ValueError('efecto_top')
            nodes.append(n)
        else: raise ValueError('top_no_puro')
    ns={} if adaptador is None else {'_hora':adaptador['_hora'],'calcular':adaptador['calcular']}
    exec(compile(ast.Module(body=nodes,type_ignores=[]),'<puro669>','exec'),ns)
    return ns

def constantes_act(b):
    ns={}
    for n in ast.parse(b).body:
        if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name) and n.targets[0].id in {'TIPOS_ACTIVOS','BAJAS_CONFIRMADAS'}:
            ns[n.targets[0].id]=ast.literal_eval(n.value)
    if set(ns)!={'TIPOS_ACTIVOS','BAJAS_CONFIRMADAS'}: raise ValueError('act_contrato')
    return {k:set(v) for k,v in ns.items()}

def construir(app,motor,motor_sha,ahora):
    app=Path(app);motor=Path(motor)
    if not re.fullmatch('[a-f0-9]{64}',motor_sha): raise ValueError('pin_motor')
    paths={'ghl_vivo':app/'fuentes_crm/_privado/ghl_vivo.json','crm':app/'data/crm/crm.json','act':app/'data/verdad/estado_clientes.json'}
    codes={'adaptador466':app/'ghl_embudo_observado_466.py','embudo_eventos':motor}
    extra={'act_politica':app/'fuentes_verdad/clientes_activos.py'}
    bs={k:leer(p,k=='ghl_vivo') for k,p in paths.items()};cb={k:leer(p) for k,p in codes.items()};eb={k:leer(p) for k,p in extra.items()}
    if sha(cb['embudo_eventos'])!=motor_sha: raise ValueError('pin_motor')
    model=puro(cb['embudo_eventos']);ad=puro(cb['adaptador466'],model);actconf=constantes_act(eb['act_politica'])
    clock=model['_hora'](ahora)
    if clock is None: raise ValueError('reloj_explicito')
    raw,crm,act=(estricto(bs[k]) for k in ('ghl_vivo','crm','act'))
    naive=datetime.strptime(raw['hora'],'%Y-%m-%d %H:%M');zone=ZoneInfo('Europe/Madrid');corte=naive.replace(tzinfo=zone)
    if corte.utcoffset()!=naive.replace(tzinfo=zone,fold=1).utcoffset() or datetime.fromtimestamp(corte.timestamp(),zone).replace(tzinfo=None)!=naive or corte>clock: raise ValueError('fecha_fuente')
    fin=corte.replace(hour=0,minute=0,second=0,microsecond=0)-timedelta(microseconds=1);inicio=fin+timedelta(microseconds=1)-timedelta(days=30)
    rows=crm['subcuentas'];activos=act['activos'];subs=raw['subs']
    if not all(isinstance(x,list) and all(isinstance(r,dict) for r in x) for x in (rows,activos,subs)) or not isinstance(raw['vivo'],dict): raise ValueError('colecciones')
    def ids(rs,key):
        if any(not isinstance(r.get(key),str) for r in rs): raise ValueError('identidad_coleccion')
        return Counter(r[key] for r in rs)
    cids=Counter(r.get('cliente_id') for r in rows if r.get('tipo')=='cliente' and isinstance(r.get('cliente_id'),str));sids=ids(rows,'sub_id');aids=ids(activos,'id');rids=ids(subs,'id')
    bajas=set(act.get('bajas_ids') or [])|actconf['BAJAS_CONFIRMADAS'];operativos={r['id'] for r in activos if r.get('tipo') in actconf['TIPOS_ACTIVOS']}
    out=[];excluded=Counter()
    for row in rows:
        cid,sid=row.get('cliente_id'),row.get('sub_id')
        if row.get('tipo')!='cliente': excluded['no_cliente']+=1;continue
        if not isinstance(cid,str) or cids[cid]!=1 or aids[cid]!=1 or cid in bajas or cid not in operativos: excluded['act_o_identidad']+=1;continue
        if sids[sid]!=1 or rids[sid]!=1 or sid not in raw['vivo']: excluded['subcuenta']+=1;continue
        res=ad['preparar'](raw['vivo'][sid],cid,sid,inicio.isoformat(),fin.isoformat(),corte.isoformat())
        out.append({'cliente_id':cid,'subcuenta_huella':ad['_hash'](sid),'medicion':res['agregado'],'diagnosticos':res['diagnosticos'],'solo_observados':True})
    if not out: raise ValueError('sin_clientes_enlazados')
    d={'version':'466.1','hora_fuente':corte.isoformat(),'desde':inicio.isoformat(),'hasta':fin.isoformat(),'corte':corte.isoformat(),'clientes':sorted(out,key=lambda r:r['cliente_id']),'sin_pii':True,'cobertura':'parcial'}
    b=serial(d);m={'version':'466.1','sha256':sha(b),'codigo_sha256':{k:sha(v) for k,v in cb.items()},'fuentes_sha256':{k:sha(v) for k,v in bs.items()}}
    for inventory,data in ((paths,bs),(codes,cb),(extra,eb)):
        if any(leer(p,k=='ghl_vivo')!=data[k] for k,p in inventory.items()): raise ValueError('fuente_o_codigo_cambio')
    review={'version':'669.1','sha256':sha(b),'manifest_sha256':sha(serial(m)),'act_politica_sha256':sha(eb['act_politica']),'preparador_sha256':sha(leer(Path(__file__).resolve())),'clientes':len(out),'excluidos':dict(excluded),'promovido':False}
    return b,serial(m),serial(review)

def guardar(salida,app,archivos):
    salida=Path(salida);r=Path(app).parent/'RECUPERACION_CODEX_2026-10-03'
    if not salida.is_absolute() or salida.parent!=r or not re.fullmatch('staging_embudo_669_[A-Za-z0-9_-]+',salida.name) or salida.exists() or salida.is_symlink(): raise ValueError('deposito_nuevo_R')
    for p in (r,*r.parents):
        if p.is_symlink(): raise ValueError('enlace')
    tmp=Path(tempfile.mkdtemp(prefix='.embudo669-',dir=r));os.chmod(tmp,0o700)
    try:
        for nombre,b in zip(('candidato.json','manifest.json','revision669.json'),archivos):
            fd=os.open(tmp/nombre,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
            with os.fdopen(fd,'wb') as f:f.write(b);f.flush();os.fsync(f.fileno())
        os.rename(tmp,salida)
    except Exception:
        # Sólo temporales creados por este script, nunca depósito previo.
        for p in tmp.iterdir(): p.unlink()
        tmp.rmdir();raise
    return salida

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--app',required=True);parser.add_argument('--motor',required=True);parser.add_argument('--motor-sha',required=True);parser.add_argument('--ahora',required=True);parser.add_argument('--salida',required=True);a=parser.parse_args()
    try:
        archivos=construir(a.app,a.motor,a.motor_sha,a.ahora);guardar(a.salida,a.app,archivos)
        print(json.dumps({'estado':'candidato_privado','sha256':sha(archivos[0]),'manifest_sha256':sha(archivos[1]),'promovido':False}))
    except Exception:
        # No imprimir excepciones de JSON, rutas privadas ni payloads.
        print('{"estado":"rechazado","codigo":"validacion_offline_fallida"}');raise SystemExit(1)

"""Evidencia histórica aditiva de Método; lectura local, sin IO al importar."""
import hashlib
import json
import math
import os
import re
from pathlib import Path
from operaciones_registros_269 import unica, ErrorRegistro
import historial_reuniones_api as H
from evidencia_seguimiento_446 import proyectar

VERSION='452.1'
ESTADOS={'disponible','sin_configurar','no_autorizado','no_disponible'}


class CambioAutoridad(Exception):
    pass


def canonicas(S, rid, vid):
    try:
        if S.E.nucleo_bloqueado:raise CambioAutoridad()
        ps=[unica(S.E.crudo.get('personas'),pid) for pid in (rid,vid)]
        for p in ps:
            roles=p.get('puestos')
            if (not isinstance(roles,list) or not roles or len(set(roles))!=len(roles)
                    or any(not isinstance(x,str) or not re.fullmatch(r'[a-zA-Z0-9_-]{1,100}',x) for x in roles)):
                raise CambioAutoridad()
        if rid!=vid and S.P.ver(ps[0],{'tipo':'ver_como'},S.P.contexto(ps[0],S.E.crudo)).get('ok') is not True:
            raise CambioAutoridad()
        return ps
    except (ErrorRegistro,ValueError,TypeError,KeyError,AttributeError):
        raise CambioAutoridad() from None


def firma(S,rid,vid,politica):
    """Autoridad vigente; nunca se publica esta firma ni los datos que resume."""
    ps=canonicas(S,rid,vid)
    try:
        crudo=S.E.crudo
        clientes=crudo.get('clientes') or []
        activos=[(c.get('id'),S.ACT.es_activo_id(c.get('id')) is True) for c in clientes if isinstance(c,dict)]
        # Incluye puertas de módulos y decisiones P.ver actuales, no sólo los IDs.
        permisos=[]
        for p in ps:
            cp=S.P.contexto(p,crudo)
            permisos.append([S.ve_alguno(p,['reuniones']),
                [(cid,H.permitido(S,p,cid)) for cid,_ in activos]])
        return hashlib.sha256(json.dumps([crudo.get('personas'),clientes,crudo.get('asignaciones'),
            activos,S.P.REGLAS,politica,permisos,os.environ.get('RO_HISTORIAL_REUNIONES')],
            sort_keys=True,allow_nan=False).encode()).hexdigest()
    except (ValueError,TypeError,KeyError,AttributeError):
        raise CambioAutoridad() from None


def _pares(pares):
    d={}
    for k,v in pares:
        if k in d:raise ValueError('json_ambiguo')
        d[k]=v
    return d


def _float(v):
    f=float(v)
    if not math.isfinite(f):raise ValueError('json_no_finito')
    return f


def _json(raw):
    return json.loads(raw,object_pairs_hook=_pares,parse_float=_float,
                      parse_constant=lambda _:(_ for _ in ()).throw(ValueError('json_no_finito')))


def _marcas(base):
    return tuple((s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns,s.st_mode,s.st_nlink)
        for s in ((base/n).lstat() for n in ('manifest.json','reuniones.json')))


def leer_historial(raiz,hoy):
    """Valida el depósito entero antes de scope; sin IDs inventados desde DTO público."""
    base=Path(raiz)
    marcas=_marcas(base)
    mraw=H.privado(base/'manifest.json',base)
    manifest=_json(mraw)
    raw=H.privado(base/'reuniones.json',base)
    if (not isinstance(manifest,dict) or type(manifest.get('version')) is not int or manifest['version']!=1
            or not H.dia(manifest.get('asof')) or manifest['asof']>hoy
            or (manifest.get('archivos') or {}).get('reuniones.json')!=hashlib.sha256(raw).hexdigest()):
        raise ValueError('manifest_invalido')
    d=_json(raw)
    if (not isinstance(d,dict) or type(d.get('version')) is not int or d['version']!=1 or d.get('importado_el')!=manifest['asof']
            or d.get('cobertura')!='parcial' or not isinstance(d.get('clientes'),dict)):
        raise ValueError('deposito_invalido')
    ids=set();out={}
    for cid,rows in d['clientes'].items():
        if not isinstance(cid,str) or not re.fullmatch(r'[a-zA-Z0-9_-]{1,100}',cid) or not isinstance(rows,list):raise ValueError('cliente_invalido')
        out[cid]=[]
        for r in rows:
            if not isinstance(r,dict):raise ValueError('registro_invalido')
            rid=r.get('id');f=H.dia(r.get('fecha'))
            if (not isinstance(rid,str) or not re.fullmatch(r'fathom_[a-f0-9]{24}',rid)
                    or rid in ids or r.get('cliente_id')!=cid or not f or f>manifest['asof']
                    or type(r.get('fecha_ambigua')) is not bool
                    or r.get('registro')!='registro_historico' or r.get('celebrada_confirmada') is not False):
                raise ValueError('registro_ambiguo')
            ids.add(rid)
            out[cid].append({k:r[k] for k in ('id','cliente_id','fecha','fecha_ambigua','registro')})
    # Detecta rotación durante la lectura completa; no recurre a la copia anterior.
    if H.privado(base/'manifest.json',base)!=mraw or H.privado(base/'reuniones.json',base)!=raw or _marcas(base)!=marcas:
        raise ValueError('fuente_cambiada')
    return out,manifest['asof'],(hashlib.sha256(mraw).hexdigest(),hashlib.sha256(raw).hexdigest(),marcas)


def desconocida(estado):
    return dict(version=VERSION,estado_fuente=estado,cobertura='desconocida',importado_el=None,
        registros_historicos_observados=None,ultimo_registro_historico=None,responsable_historico=None,
        celebracion_confirmada=None,participacion_trafficker_confirmada=None,
        faltantes=['celebracion','participacion_trafficker','responsable_en_fecha','cobertura_intervalo'])


def enriquecer(S,rid,vid,dto,reglas,hoy):
    ps=canonicas(S,rid,vid)
    inicial=firma(S,rid,vid,reglas)
    crudo=S.E.crudo
    rows=dto.get('sugerencias') or []
    cs=crudo.get('clientes') or []
    def autorizado(cid):
        matches=[c for c in cs if isinstance(c,dict) and c.get('id')==cid]
        return (len(matches)==1 and matches[0].get('activo') is not False
            and matches[0].get('estado')!='baja' and S.ACT.es_activo_id(cid) is True
            and all(S.ve_alguno(p,['reuniones']) in ('todo','suyo','resumen')
                and H.permitido(S,p,cid) is True for p in ps))
    cids={r['cliente_id'] for r in rows if autorizado(r['cliente_id'])}
    disponibles={};estado='sin_configurar';asof=None;huellas=None
    fuente=os.environ.get('RO_HISTORIAL_REUNIONES')
    if cids and fuente:
        try:
            historial,asof,huellas=leer_historial(fuente,hoy)
            d=proyectar(reglas=reglas,historial=historial,clientes=cs,personas=crudo.get('personas') or [],
                asignaciones=crudo.get('asignaciones') or [],real_id=rid,vista_id=vid,hoy=hoy,
                activo=S.ACT.es_activo_id,permite=lambda p,c:c in cids and H.permitido(S,p,c) is True)
            # Ausencia de inventario por cliente no acredita cero registros.
            disponibles={r['cliente_id']:r for r in d['filas'] if r['cliente_id'] in historial};estado='disponible'
        except (OSError,ValueError,TypeError,KeyError,AttributeError,RecursionError):
            estado='no_disponible';huellas=None
    if inicial!=firma(S,rid,vid,reglas):raise CambioAutoridad()
    for row in rows:
        cid=row['cliente_id'];e=desconocida(estado if cid in cids else 'no_autorizado')
        if estado=='disponible' and cid in cids and cid not in disponibles:
            e=desconocida('no_disponible')
        if cid in disponibles:
            r=disponibles[cid]
            e.update(estado_fuente='disponible',cobertura='parcial',importado_el=asof,
                registros_historicos_observados=r['registros_historicos_observados'],
                ultimo_registro_historico=r['ultimo_registro_historico'])
        row['evidencia_por_revisar']=e
    def validar_final():
        if huellas is not None:
            try:
                base=Path(fuente)
                actual=tuple(hashlib.sha256(H.privado(base/n,base)).hexdigest()
                    for n in ('manifest.json','reuniones.json'))
                if actual!=huellas[:2] or _marcas(base)!=huellas[2]:raise CambioAutoridad()
            except (OSError,ValueError,TypeError):raise CambioAutoridad() from None
        if inicial!=firma(S,rid,vid,reglas):raise CambioAutoridad()
    validar_final()
    return dto,validar_final

"""199: manifest privado fijo validado; ninguna inferencia ni acceso a proveedores."""
from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import stat
try:
    from .crosswalk_confirmado import consolidar_confirmados, fecha
except ImportError:
    from crosswalk_confirmado import consolidar_confirmados, fecha

MAX_BYTES=262144

def opaco(x):
    return isinstance(x,str) and bool(re.fullmatch(r'[A-Za-z0-9_.:-]{1,160}',x))

def instante(x):
    if not isinstance(x,str):return None
    try:t=datetime.fromisoformat(x.replace('Z','+00:00'))
    except ValueError:return None
    return t.astimezone(timezone.utc) if t.tzinfo is not None and t.utcoffset() is not None else None

def identidad_observada(fuente,event_id,inicio,fin,owner_id=None,zona=None):
    """Zona literal no transforma un horario naïve en instante acreditado."""
    a,b=instante(inicio),instante(fin)
    valid=bool(a and b and b>a)
    return {'fuente':fuente,'source_event_id':event_id if opaco(event_id) else None,
            'source_owner_id':owner_id if opaco(owner_id) else None,
            'zona_fuente':zona if isinstance(zona,str) and re.fullmatch(r'[A-Za-z0-9_/+:-]{1,80}',zona) else None,
            'ventana_confirmada':valid,'inicio_utc':a.isoformat().replace('+00:00','Z') if valid else None,
            'fin_utc':b.isoformat().replace('+00:00','Z') if valid else None,
            'duracion_minutos':(b-a).total_seconds()/60 if valid else None}

def pares_unicos(pares):
    out={}
    for k,v in pares:
        if k in out:raise ValueError('Clave repetida')
        out[k]=v
    return out

def cargar_manifest(ruta,hoy):
    """Caller pasa ruta fija del servidor. No ruta de petición, evidencia ni errores en salida."""
    def invalid():return [],'invalido'
    p=Path(ruta)
    try:
        if p.parent.is_symlink():return invalid()
        pre=p.lstat()
        if not stat.S_ISREG(pre.st_mode):return invalid()
        fd=os.open(p,os.O_RDONLY|getattr(os,'O_NOFOLLOW',0)|getattr(os,'O_NONBLOCK',0))
    except FileNotFoundError:return [],'ausente'
    except OSError:return invalid()
    try:
        with os.fdopen(fd,'rb') as f:
            info=os.fstat(f.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_nlink!=1 or info.st_uid!=os.getuid() or info.st_mode & 0o077 or info.st_size>MAX_BYTES:return invalid()
            raw=f.read(MAX_BYTES+1)
        if len(raw)>MAX_BYTES:return invalid()
        m=json.loads(raw.decode('utf-8'),object_pairs_hook=pares_unicos)
        if (not isinstance(m,dict) or set(m)!={'version','confirmado','evidencia','registros'}
            or type(m['version']) is not int or m['version']!=1 or m['confirmado'] is not True):return invalid()
        limite=fecha(hoy);ev=m['evidencia'];records=m['registros']
        if (not limite or not isinstance(ev,dict) or set(ev)!={'tipo','registro_ref','fecha_verificacion'}
            or ev.get('tipo')!='revision_documental' or not opaco(ev.get('registro_ref'))
            or not fecha(ev.get('fecha_verificacion')) or fecha(ev['fecha_verificacion'])>limite
            or not isinstance(records,list) or len(records)>1000):return invalid()
        keys={'confirmado','referencia_reunion','persona_id','inicio','fin','fuente','event_id','evidencia','propietario_verificado','ventana_verificada'}
        for r in records:
            if (not isinstance(r,dict) or set(r)!=keys or r['confirmado'] is not True
                or r['propietario_verificado'] is not True or r['ventana_verificada'] is not True
                or any(not opaco(r.get(k)) for k in ('referencia_reunion','persona_id','event_id'))):return invalid()
            e=r['evidencia']
            if (not isinstance(e,dict) or set(e)!={'tipo','registro_ref','fecha_verificacion'}
                or e.get('tipo') not in ('verificacion_manual','identificador_compartido_proveedor')
                or not opaco(e.get('registro_ref')) or not fecha(e.get('fecha_verificacion'))
                or fecha(e['fecha_verificacion'])>limite):return invalid()
        return records,'validado'
    except (OSError,UnicodeError,ValueError,TypeError,KeyError,RecursionError):return invalid()

def integrar(eventos,ruta,hoy):
    records,estado=cargar_manifest(ruta,hoy)
    out,resumen=consolidar_confirmados(eventos,records,hoy)
    resumen.update(integracion_runtime=True,manifest_estado=estado)
    originales={(e.get('fuente'),e.get('id')):e for e in eventos if isinstance(e,dict)}
    for e in out:
        if not isinstance(e,dict):continue
        origins=e.get('origenes') if isinstance(e.get('origenes'),list) else [{'fuente':e.get('fuente'),'id':e.get('id')}]
        e['identidades_fuente']=[deepcopy(originales[(o.get('fuente'),o.get('id'))]['identidad_fuente'])
          for o in origins if isinstance(o,dict) and isinstance(originales.get((o.get('fuente'),o.get('id')),{}).get('identidad_fuente'),dict)]
    resumen['nota']=('Manifest confirmado aplicado sólo a referencias exactas; no certifica todo el inventario.' if estado=='validado'
      else 'Sin manifest confirmado válido: no se fusionan coincidencias de hora, nombre o sala.')
    return out,resumen

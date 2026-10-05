"""Histórico local de metadatos: depósito validado, sin texto, hosts ni acceso a proveedores."""
import hashlib
import json
import os
from pathlib import Path
import re
import stat
from datetime import date
from fuentes_historial_reuniones.normalizador import leer_privado

MAX_BYTES = 2_000_000
FECHA_FUENTE = {'recording_start_time','scheduled_start_time','documento_fecha','indice_fecha','cache_fecha','sin_fecha'}


def dia(v):
    if not isinstance(v,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',v):return None
    try:return date.fromisoformat(v).isoformat()
    except ValueError:return None


def privado(p,raiz):
    """Reusa lector110 y añade exigencia de permisos0600; tamaño/fd/NOFOLLOW/nlink en lector."""
    p=Path(p);raiz=Path(raiz)
    if not raiz.is_dir() or raiz.stat().st_mode & 0o077:raise ValueError('deposito_no_privado')
    if p.lstat().st_mode & 0o077:raise ValueError('archivo_no_privado')
    return leer_privado(p,raiz,MAX_BYTES,modo_privado=True)


def _json(p,raiz):return json.loads(privado(p,raiz))


def preparar_fuente(origen,destino,asof):
    """Opt-in offline sobre outputs120 ya normalizados: no extrae corpus ni lee contratos."""
    origen=Path(origen);destino=Path(destino)
    if not dia(asof):raise ValueError('fecha_importacion_invalida')
    manifest=_json(origen/'manifest_entregables.json',origen)
    if not isinstance(manifest,list):raise ValueError('manifest_invalido')
    hashes={}; verificados={}
    for nombre in ('catalogo_confirmado.json','reuniones_candidatas.json','validacion.json'):
        entradas=[e for e in manifest if isinstance(e,dict) and e.get('archivo')==str(origen/nombre)]
        if len(entradas)!=1:raise ValueError('manifest_duplicado_o_ausente')
        raw=privado(origen/nombre,origen);sha=hashlib.sha256(raw).hexdigest()
        if entradas[0].get('sha256')!=sha:raise ValueError('integridad_fuente_no_coincide')
        hashes[nombre]=sha; verificados[nombre]=json.loads(raw)
    catalogo=verificados['catalogo_confirmado.json']
    reuniones=verificados['reuniones_candidatas.json']
    validacion=verificados['validacion.json']
    if not isinstance(catalogo,dict) or not isinstance(reuniones,dict) or not isinstance(validacion,dict):raise ValueError('forma_fuente_invalida')
    if any(validacion.get(k) is not False for k in ('red','transcripciones_copiadas','contratos_completos_copiados')):raise ValueError('validacion_no_apta')
    confirmados={r.get('cliente_id') for r in catalogo.values() if isinstance(r,dict) and r.get('confirmado') is True and r.get('fuente') and isinstance(r.get('hash_fuente'),str) and len(r['hash_fuente'])==64}
    clientes={};ids={};descartados={}
    if not isinstance(reuniones.get('reuniones'),list):raise ValueError('reuniones_invalidas')
    for r in reuniones['reuniones']:
        if not isinstance(r,dict):continue
        cid=r.get('cliente_id');fecha=dia(r.get('fecha'));rid=r.get('id')
        if cid not in confirmados:continue
        if not fecha or fecha>asof or not isinstance(rid,str) or not re.fullmatch(r'fathom_[a-f0-9]{24}',rid) or r.get('enlace_cliente')!='catalogo_confirmado':
            descartados[cid]=descartados.get(cid,0)+1;continue
        evid=r.get('fechas_evidencia') if isinstance(r.get('fechas_evidencia'),dict) else {}
        fechas=sorted({v for k,valor in evid.items() for v in (valor if isinstance(valor,list) else [valor]) if dia(v)})
        fila={'id':rid,'cliente_id':cid,'fecha':fecha,'fuente':'Fathom · archivo local',
              'fecha_fuente':r.get('fecha_fuente') if r.get('fecha_fuente') in FECHA_FUENTE else 'sin_fecha',
              'fecha_ambigua':r.get('fecha_discrepancia') is True or len(fechas)>1,'fechas_documentadas':fechas,
              'registro':'registro_historico','celebrada_confirmada':False,
              'transcripcion_registrada':r.get('transcripcion_disponible') is True,
              'acceso_grabacion':'no_verificado','account_historico':'sin_evidencia'}
        if rid in ids:
            if ids[rid]!=fila:raise ValueError('identidad_historica_conflictiva')
            continue
        ids[rid]=fila;clientes.setdefault(cid,[]).append(fila)
    doc={'version':1,'importado_el':asof,'cobertura':'parcial','clientes':clientes,'descartados':descartados,'fuentes_sha256':hashes}
    if destino.exists():raise ValueError('deposito_destino_ya_existe')
    destino.mkdir(mode=0o700,parents=True)
    raw=json.dumps(doc,ensure_ascii=False,allow_nan=False).encode()
    contenido={'version':1,'asof':asof,'archivos':{'reuniones.json':hashlib.sha256(raw).hexdigest()}}
    for nombre,datos in [('reuniones.json',raw),('manifest.json',json.dumps(contenido).encode())]:
        fd=os.open(destino/nombre,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
        with os.fdopen(fd,'wb') as f:f.write(datos);f.flush();os.fsync(f.fileno())
    return {'clientes':len(clientes),'registros':len(ids),'descartados':sum(descartados.values()),'importado_el':asof}


def cargar_fuente(raiz,cid):
    base=Path(raiz)
    manifest=_json(base/'manifest.json',base)
    if not isinstance(manifest,dict) or manifest.get('version')!=1 or not dia(manifest.get('asof')):raise ValueError('manifest_invalido')
    raw=privado(base/'reuniones.json',base)
    if (manifest.get('archivos') or {}).get('reuniones.json')!=hashlib.sha256(raw).hexdigest():raise ValueError('integridad_deposito_no_coincide')
    doc=json.loads(raw)
    if not isinstance(doc,dict) or doc.get('version')!=1 or doc.get('importado_el')!=manifest['asof'] or not isinstance(doc.get('clientes'),dict):raise ValueError('deposito_invalido')
    filas=doc['clientes'].get(cid,[])
    if not isinstance(filas,list):raise ValueError('filas_invalidas')
    out=[];vistos=set()
    for r in filas:
        if not isinstance(r,dict) or r.get('cliente_id')!=cid or not dia(r.get('fecha')) or r['fecha']>manifest['asof']:raise ValueError('registro_invalido')
        rid=r.get('id')
        if not isinstance(rid,str) or not re.fullmatch(r'fathom_[a-f0-9]{24}',rid) or rid in vistos:raise ValueError('registro_duplicado_invalido')
        vistos.add(rid)
        out.append({'fecha':r['fecha'],'fuente':'Fathom · archivo local','registro':'Registro histórico',
                    'fecha_fuente':r.get('fecha_fuente') if r.get('fecha_fuente') in FECHA_FUENTE else 'sin_fecha',
                    'fecha_ambigua':r.get('fecha_ambigua') is True,
                    'fechas_documentadas':[d for d in r.get('fechas_documentadas',[]) if dia(d)] if isinstance(r.get('fechas_documentadas'),list) else [],
                    'account_historico':'Sin evidencia del account de esa fecha',
                    'transcripcion_registrada':r.get('transcripcion_registrada') is True,
                    'acceso_grabacion':'No verificado','celebrada_confirmada':False})
    return {'cliente_id':cid,'estado_fuente':'disponible','importado_el':manifest['asof'],'cobertura':'parcial',
            'nota':'Corpus local parcial. Un registro o transcripción no confirma celebración, tipo de reunión ni cumplimiento de cadencia.',
            'registros':sorted(out,key=lambda x:x['fecha'],reverse=True),'total':len(out)}


def permitido(S,p,cid):
    cp=S.P.contexto(p,S.E.crudo)
    roles=set(p.get('puestos') or [])
    rol_ok=bool(roles & {'direccion','operaciones'}) or ('account' in roles and cid in (cp.get('cartera_por_silla') or {}).get('account',set()))
    return rol_ok and S.P.ver(p,{'tipo':'cliente_detalle','cliente_id':cid},cp)['ok']


def enganchar(Manejador,S):
    original=Manejador._api_get
    def get(self,ruta,q,real,persona):
        if ruta!='/api/historial/reuniones':return original(self,ruta,q,real,persona)
        if S.E.nucleo_bloqueado:return self.responder(503,{'error':'Datos temporalmente bloqueados.'})
        if set(q)-{'cliente_id','yo','como'} or len(q.get('cliente_id') or [])!=1:return self.responder(400,{'error':'Selecciona un único cliente.'})
        cid=q['cliente_id'][0]
        if not isinstance(cid,str) or not S.ACT.es_activo_id(cid):return self.responder(404,{'error':'Cliente activo no encontrado.'})
        if not all(permitido(S,p,cid) for p in (real,persona)):return self.responder(403,{'error':'Histórico reservado a dirección, operaciones y account de la cartera confirmada.'})
        fuente=os.environ.get('RO_HISTORIAL_REUNIONES')
        if not fuente:return self.responder(200,{'cliente_id':cid,'estado_fuente':'sin_configurar','cobertura':'desconocida','registros':[],'total':None,'nota':'El depósito histórico todavía no está activado. No significa que el cliente no tenga reuniones.'})
        try:doc=cargar_fuente(fuente,cid)
        except (OSError,ValueError,TypeError,AttributeError):return self.responder(503,{'error':'El depósito histórico no está disponible o no supera la validación. No se puede concluir ausencia de reuniones.'})
        return self.responder(200,doc)
    Manejador._api_get=get

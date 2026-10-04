"""350: lectura local del agregado histórico revisado; no contactos, finanzas ni IO al importar."""
import hashlib,json,os,re,stat
from pathlib import Path
from datetime import datetime,timezone
from operaciones_registros_269 import unica,ErrorRegistro
RUTA='/api/operaciones/llamadas/historico'
VERSION='350.1'
HASH_CANDIDATO='4afc61a142faadf9631141c3a33109712cfd9ecfdf832a99e469731e970f5bc2'
PERIODO='2026-09'
MAX_BYTES=8_000_000
class ErrorHistorico(Exception):
 def __init__(self,codigo,texto):self.codigo=codigo;super().__init__(texto)
def _hash(x):return hashlib.sha256(json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
def ambito(S,rid,vid):
 if S.E.nucleo_bloqueado:raise ErrorHistorico(503,'Permisos actuales no disponibles.')
 try:ps=[unica(S.E.crudo.get('personas'),x) for x in (rid,vid)]
 except ErrorRegistro:raise ErrorHistorico(403,'Identidad activa no inequívoca.')
 if rid!=vid and S.P.ver(ps[0],{'tipo':'ver_como'},S.P.contexto(ps[0],S.E.crudo)).get('ok') is not True:raise ErrorHistorico(403,'Vista no autorizada.')
 contexts=[]
 for p in ps:
  roles=p.get('puestos')
  if not isinstance(roles,list) or any(not isinstance(x,str) for x in roles) or len(set(roles))!=len(roles) or not set(roles)&{'direccion','operaciones','account'} or not S.ve_alguno(p,['bandeja']):raise ErrorHistorico(403,'Histórico no disponible en esta sesión.')
  contexts.append(S.P.contexto(p,S.E.crudo))
 cs=S.E.crudo.get('clientes');cs=cs if isinstance(cs,list) else []
 counts={}
 for c in cs:
  cid=c.get('id') if isinstance(c,dict) else None
  if isinstance(cid,str):counts[cid]=counts.get(cid,0)+1
 ids=[]
 for c in cs:
  if not isinstance(c,dict):continue
  cid=c.get('id')
  if not isinstance(cid,str) or not re.fullmatch('[A-Za-z0-9_-]{1,150}',cid) or counts[cid]!=1 or c.get('activo') is False or c.get('estado')=='baja' or S.ACT.es_activo_id(cid) is not True:continue
  allowed=True
  for p,cp in zip(ps,contexts):
   if S.P.ver(p,{'tipo':'cliente_detalle','cliente_id':cid},cp).get('ok') is not True:allowed=False;break
   if not set(p['puestos'])&{'direccion','operaciones'}:
    if cid not in (cp.get('cartera_por_silla') or {}).get('account',[]):allowed=False;break
    #363: lectura de cartera concedida por P.ver; receptor confirmado sigue reservado a pedidos.
    # No se deduce responsabilidad actual ni autoría histórica de esta lectura.
  if allowed:ids.append(cid)
 ids=sorted(ids)
 # Capture authoritative source and actual grants; recheck after reading even without rows.
 signature=_hash([rid,vid,ids,S.E.crudo.get('personas'),S.E.crudo.get('asignaciones'),
   [[p['id'],S.ve_alguno(p,['bandeja']),[S.P.ver(p,{'tipo':'cliente_detalle','cliente_id':cid},cp).get('ok') is True for cid in ids]] for p,cp in zip(ps,contexts)]])
 return ids,signature

def leer_agregado(path):
 p=Path(path)
 try:
  fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW)
  with os.fdopen(fd,'rb') as f:
   before=os.fstat(f.fileno())
   if not stat.S_ISREG(before.st_mode) or before.st_nlink!=1 or before.st_size>MAX_BYTES:raise ValueError()
   raw=f.read(MAX_BYTES+1);after=os.fstat(f.fileno())
   if len(raw)>MAX_BYTES or (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):raise ValueError()
  doc=json.loads(raw.decode('utf8'),parse_constant=lambda _:(_ for _ in ()).throw(ValueError()))
  rows=doc.get('clientes') if isinstance(doc,dict) else None
  if not isinstance(rows,list):raise ValueError()
  result={};seen=set()
  for row in rows:
   if not isinstance(row,dict) or not isinstance(row.get('cliente_id'),str):raise ValueError()
   cid=row['cliente_id']
   if cid in seen:raise ValueError()
   seen.add(cid);h=row.get('historico_267')
   if h is None:continue
   if not isinstance(h,dict) or h.get('version')!='267.1' or h.get('periodo')!=PERIODO or h.get('cobertura')!='parcial' or h.get('verificacion_externa') is not False or h.get('cumplimiento') is not None or h.get('no_evalua_garantia') is not True or h.get('sha256_candidato')!=HASH_CANDIDATO:raise ValueError()
   n=h.get('llamadas30')
   if n is not None and (type(n) is not int or n<0):raise ValueError()
   result[cid]=n if h.get('fuente_llamadas')=='zadarma_cache_historica' and type(n) is int and n>0 else None
  return result
 except FileNotFoundError:return None
 except (OSError,ValueError,TypeError,UnicodeError,RecursionError):raise ErrorHistorico(503,'El agregado histórico no supera la validación. No acredita ausencia de llamadas.')

def listar(S,rid,vid,periodo,path=None):
 if not isinstance(periodo,str) or not re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])',periodo):raise ErrorHistorico(400,'Selecciona un único período mensual válido.')
 ids,firma=ambito(S,rid,vid)
 fuente=leer_agregado(path or Path(__file__).parent/'data/dinero_cliente/dinero_cliente.json') if periodo==PERIODO else None
 ids2,firma2=ambito(S,rid,vid)
 if (ids2,firma2)!=(ids,firma):raise ErrorHistorico(403,'El ámbito ha cambiado durante la lectura.')
 rows=[]
 for cid in ids:
  n=fuente.get(cid) if fuente is not None else None
  rows.append({'cliente_id':cid,'periodo':periodo,'llamadas_30s':n,'unidad':'llamadas_respondidas_30s','estado':'copia_historica' if n is not None else 'sin_dato','actor_id':None,'direccion':None,'registro':'historico','verificacion_externa':False,'cumplimiento':None})
 return {'version':VERSION,'generado':datetime.now(timezone.utc).isoformat(),'periodo':periodo,'estado':'copia_historica' if any(r['llamadas_30s'] is not None for r in rows) else 'sin_dato','cobertura':'parcial' if fuente is not None else 'desconocida','fuente':'Zadarma · agregado histórico local' if fuente is not None else None,'sha256_candidato':HASH_CANDIDATO if fuente is not None else None,'filas':rows,'nota':'Referencia histórica parcial. Actor, dirección y titular actual sin acreditar. No mide llamadas de esta semana ni cumplimiento.'}

def enganchar(H,S):
 original=H._api_get
 def get(self,ruta,q,real,persona):
  if ruta!=RUTA:return original(self,ruta,q,real,persona)
  if set(q)!={'periodo'} or not isinstance(q.get('periodo'),list) or len(q['periodo'])!=1:return self.responder(400,{'error':'Selecciona un único período.'})
  try:return self.responder(200,listar(S,real.get('id'),persona.get('id'),q['periodo'][0]))
  except ErrorHistorico as e:return self.responder(e.codigo,{'error':str(e)})
 H._api_get=get

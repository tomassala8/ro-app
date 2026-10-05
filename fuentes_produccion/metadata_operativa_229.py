"""229: ampliación opt-in privada. Textos215 y URL sólo catálogo explícito."""
import copy,re
from collections import Counter
from urllib.parse import urlsplit,unquote
from contexto_tarea import texto_operativo,CREDENCIALES
ID=re.compile(r'^[A-Za-z0-9_-]{1,120}$')

def nombre(v):
 if v is None:return {'nombre':None,'nombre_estado':'ausente'}
 if not isinstance(v,str):return {'nombre':None,'nombre_estado':'invalido'}
 limpio=texto_operativo(v,limite=401)
 # Checklist no necesita enlaces: no conservar rutas sensibles en títulos.
 limpio=re.sub(r'https?://[^\s"<>]+','[enlace omitido]',limpio,flags=re.I)
 return {'nombre':limpio[:400] or None,'nombre_estado':'truncado' if len(limpio)>400 else 'saneado' if limpio else 'vacio'}

def index(xs):
 xs=xs if isinstance(xs,list) else []
 ids=Counter(x.get('id') for x in xs if isinstance(x,dict) and isinstance(x.get('id'),str))
 return {x['id']:x for x in xs if isinstance(x,dict) and isinstance(x.get('id'),str) and ID.fullmatch(x['id']) and ids[x['id']]==1}

def url_permitida(v,hosts):
 if not isinstance(v,str) or len(v)>2048 or not isinstance(hosts,list) or not hosts:return None
 if re.search(r'\s|[\x00-\x1f\x7f]',v) or any(rx.search(v) for rx in CREDENCIALES):return None
 try:
  u=urlsplit(v)
  if u.scheme!='https' or u.username or u.password or u.query or u.fragment or u.port not in (None,443):return None
  host=u.hostname
  if not host or host not in hosts or any(not isinstance(h,str) or h!=h.lower() or not re.fullmatch(r'[a-z0-9.-]+',h) for h in hosts):return None
  path=u.path
  for _ in range(3):path=unquote(path)
  if re.search(r'(?:^|[/_-])(?:token|secret|password|start_url|zak|jwt|host_key)(?:[/_.-]|$)',path,re.I):return None
  if (host=='zoom.us' or host.endswith('.zoom.us')) and path.startswith('/s/'):return None
  # No transformar signed links/query/pwd: se rechazan completos.
  return v
 except ValueError:return None

def ampliar(raw,base,catalogo=None):
 out=copy.deepcopy(base);cs=index(raw.get('checklists'))
 for c in out.get('checklists',[]):
  original=cs.get(c['id'])
  if original is None:continue
  c.update(nombre(original.get('name')));items=index(original.get('items'))
  for i in c.get('items',[]):
   r=items.get(i['id'])
   if r is not None:i.update(nombre(r.get('name')))
 out['ampliacion_operativa']={'version':'229.1','titulos':'saneados215','entregable':'sin_catalogo','activacion_publica':False}
 lid=str((raw.get('list') or {}).get('id') or '') if isinstance(raw.get('list'),dict) else ''
 cat=catalogo.get(lid) if isinstance(catalogo,dict) else None
 # Campo por ID/tipo/lista/fuente explícitos, nunca nombre libre ni primer URL.
 if not isinstance(cat,dict) or cat.get('confirmado') is not True or cat.get('tipo')!='url' or cat.get('semantica')!='entregable_final' or not isinstance(cat.get('fuente'),str) or not cat['fuente'] or not isinstance(cat.get('campo_id'),str) or not ID.fullmatch(cat['campo_id']):
  return out
 campos=index(raw.get('custom_fields'));f=campos.get(cat.get('campo_id'))
 estado='campo_no_observado';v=None
 if f and f.get('type')=='url':
  if 'value' not in f:estado='valor_ausente'
  elif f['value'] is None or f['value']=='':estado='vacio_observado'
  else:
   v=url_permitida(f['value'],cat.get('hosts'));estado='url_admitida_politica' if v else 'url_rechazada'
 elif f:estado='tipo_incoherente'
 out['entregable_candidato']={'campo_id':cat.get('campo_id'),'lista_id':lid,'estado':estado,'url':v}
 out['ampliacion_operativa']['entregable']=estado
 return out

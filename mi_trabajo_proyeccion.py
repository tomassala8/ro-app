"""180: proyección estructural DESPUÉS de permisos y ACT, sin I/O ni permisos nuevos."""
def recortar(obj):
 if not isinstance(obj,dict):return obj
 out=dict(obj);por_id={}
 for r in obj.get('tareas') or []:
  if isinstance(r,dict) and isinstance(r.get('id'),str) and isinstance(r.get('lista_id'),str) and r['lista_id'] and 'cli' in r:
   por_id.setdefault(r['id'],[]).append(r)
 seguros={}
 for tid,filas in por_id.items():
  identidades={(str(r.get('cli')),r['lista_id']) for r in filas}
  personas=[r.get('persona_id') for r in filas]
  if len(identidades)==1 and all(isinstance(p,str) and p for p in personas) and len(set(personas))==len(personas):seguros[tid]=filas
 listas={r['lista_id'] for filas in seguros.values() for r in filas}
 for clave in ('estados_lista','estados_detalle'):
  if clave in out:out[clave]={k:v for k,v in (out[clave] or {}).items() if k in listas} if isinstance(out[clave],dict) else {}
 for clave in ('largas','raras_estimacion','raras_cliente','raras_cliente_n'):
  if clave not in out:continue
  def permitida(r):
   if not isinstance(r,dict):return False
   filas=seguros.get(r.get('tarea_id'))
   if not filas or r.get('persona_id') not in {t['persona_id'] for t in filas}:return False
   if r.get('cliente_id') not in (None,'') and r['cliente_id']!=filas[0].get('cli'):return False
   return True
  out[clave]=[r for r in out[clave] if permitida(r)] if isinstance(out[clave],list) else []
 return out

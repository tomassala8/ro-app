"""Proyección SEO local: puerta de SEO y cartera antes de evaluar cachés privadas."""
import json
import hashlib
import math
import os
import stat
from datetime import date
from acciones_lectura_544 import ambito
from seo_candidatos import proyectar as proyectar_candidatos
from urllib.parse import urlsplit, urlunsplit
from pathlib import Path
from fuentes_seo.seo_prioridades_fuentes import cargar_local

class ErrorSEO625(Exception):
 def __init__(self,codigo):self.codigo=codigo;super().__init__('Ámbito SEO no disponible.' if codigo==403 else 'Las fuentes SEO no superan la validación.')

def leer(p):
 def pares(xs):
  d={}
  for k,v in xs:
   if k in d:raise ValueError('JSON ambiguo')
   d[k]=v
  return d
 def constante(_):raise ValueError('JSON no finito')
 def flotante(v):
  n=float(v)
  if not math.isfinite(n):raise ValueError('JSON no finito')
  return n
 try:fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
 except FileNotFoundError:return {}
 try:
  st=os.fstat(fd)
  if not stat.S_ISREG(st.st_mode) or st.st_size>10*1024*1024:raise ErrorSEO625(503)
  with os.fdopen(fd,'rb',closefd=False) as f:b=f.read(10*1024*1024+1)
  if len(b)>10*1024*1024:raise ErrorSEO625(503)
  final=os.fstat(fd)
  if (st.st_ino,st.st_ctime_ns,st.st_mtime_ns,st.st_size)!=(final.st_ino,final.st_ctime_ns,final.st_mtime_ns,final.st_size):raise ErrorSEO625(503)
  return json.loads(b,object_pairs_hook=pares,parse_constant=constante,parse_float=flotante)
 finally:os.close(fd)

def _indice625(doc,clave,campo):
 if not isinstance(doc,dict) or not isinstance(doc.get(clave,[]),list):raise ErrorSEO625(503)
 out={};duplicados=set()
 for r in doc.get(clave,[]):
  if not isinstance(r,dict) or not isinstance(r.get(campo),str) or not r[campo]:raise ErrorSEO625(503)
  cid=r[campo]
  if cid in out:duplicados.add(cid)
  else:out[cid]=r
 for cid in duplicados:out.pop(cid,None)
 return out,duplicados

def _autoridad625(S,real,persona):
 if S.E.nucleo_bloqueado:raise ErrorSEO625(503)
 ps=[]
 for ident in (real,persona):
  pid=ident.get('id') if isinstance(ident,dict) else None
  rows=[p for p in S.E.crudo.get('personas') or [] if isinstance(p,dict) and p.get('id')==pid]
  if not isinstance(pid,str) or not pid or len(rows)!=1:raise ErrorSEO625(403)
  ps.append(rows[0])
 a=ambito(S.E,S.P,S.ACT,*ps)
 if a is None:raise ErrorSEO625(403)
 if any(not S.ve_alguno(p,[mod]) for p in a[0] for mod in ('seo-web','prioridades-cliente')):raise ErrorSEO625(403)
 if ps[0]['id']!=ps[1]['id'] and S.P.ver(ps[0],{'tipo':'ver_como'},a[1][0]).get('ok') is not True:raise ErrorSEO625(403)
 final=ambito(S.E,S.P,S.ACT,*ps)
 if final is None or final[2]!=a[2]:raise ErrorSEO625(403)
 return a

def _cliente625(S,cid,ps,cps):
 cs=[c for c in S.E.crudo.get('clientes') or [] if isinstance(c,dict) and c.get('id')==cid]
 return (len(cs)==1 and cs[0].get('activo') is not False and cs[0].get('estado')!='baja'
         and S.ACT.es_activo_id(cid) is True
         and all(S.P.ver(p,{'tipo':'cliente_detalle','cliente_id':cid},cp).get('ok') is True for p,cp in zip(ps,cps)))

def _marcas625(app):
 rutas=['fuentes_verdad/servicios_confirmados.json','fuentes_seo/contextos_confirmados.json','fuentes_seo/objetivos_candidatos.json',
        'fuentes_seo/_cache/seranking.json','fuentes_seo/_cache/gsc.json','fuentes_seo/_cache/seranking_motores.json','data/seo/seo.json']
 out=[]
 for rel in rutas:
  p=app/rel
  if not app.is_absolute() or app.resolve()!=app:raise ErrorSEO625(503)
  for ancestor in reversed((p,*p.parents)):
   if ancestor.is_symlink():raise ErrorSEO625(503)
  try:
   st=p.stat()
   if not stat.S_ISREG(st.st_mode) or st.st_size>10*1024*1024:raise ErrorSEO625(503)
   out.append((st.st_dev,st.st_ino,st.st_ctime_ns,st.st_mtime_ns,st.st_size))
  except FileNotFoundError:out.append(None)
 return tuple(out)

def _responsable625(S,cid,hoy):
 rows=[]
 for a in S.E.crudo.get('asignaciones') or []:
  if not isinstance(a,dict) or a.get('cliente_id')!=cid or a.get('silla')!='seo':continue
  for campo in ('desde','hasta'):
   v=a.get(campo)
   if v not in (None,''):
    try:
     if not isinstance(v,str) or date.fromisoformat(v).isoformat()!=v:return None
    except ValueError:return None
  if S.P._vigente(a,hoy):rows.append(a)
 if len(rows)!=1:return None
 a=rows[0]
 if a.get('principal') is not True or a.get('confianza')!='confirmada' or a.get('duda') or (a.get('suplencia') and not a.get('hasta')):return None
 ps=[p for p in S.E.crudo.get('personas') or [] if isinstance(p,dict) and p.get('id')==a.get('persona_id')]
 if len(ps)!=1 or ps[0].get('estado')!='activo' or ps[0].get('activo') is False:return None
 roles=ps[0].get('puestos')
 if not isinstance(roles,list) or not roles or not all(isinstance(r,str) and r in S.P.PUESTO for r in roles) or len(set(roles))!=len(roles):return None
 if 'seo' not in S.P._sillas_de(ps[0]):return None
 cp=S.P.contexto(ps[0],S.E.crudo)
 return ps[0]['id'] if S.P.ver(ps[0],{'tipo':'cliente_detalle','cliente_id':cid},cp).get('ok') is True else None

def url_publica(valor, web):
 """Solo páginas HTTP(S) del dominio exacto acreditado, con alias www."""
 try:
  referencia=urlsplit(str(web or ''))
  actual=urlsplit(str(valor or ''))
  canon=lambda h: (h or '').lower().removeprefix('www.')
  if referencia.scheme not in ('http','https') or not referencia.hostname:return None
  if actual.scheme not in ('http','https') or not actual.hostname:return None
  if canon(actual.hostname)!=canon(referencia.hostname):return None
  if actual.port not in (None,80,443):return None
  # La URL pública nunca incluye credenciales, query ni fragment.
  return urlunsplit((actual.scheme,actual.hostname,actual.path,'',''))
 except (TypeError,ValueError):return None

def sanear_urls(salida, web):
 """No exportar URLs privadas o de otra propiedad desde las cachés SEO."""
 def limpiar(valor):
  if isinstance(valor,list):return [limpiar(x) for x in valor]
  if not isinstance(valor,dict):return valor
  return {k:url_publica(v,web) if k in ('url','url_o_ficha') else limpiar(v) for k,v in valor.items()}
 salida=limpiar(salida)
 salida['prioridades']=[p for p in salida.get('prioridades',[]) if p.get('tipo')!='revisar_pagina' or p.get('url')]
 return salida

def generar(S,real,persona):
 app=Path(S.AQUI)
 ps,cps,firma=_autoridad625(S,real,persona)
 real,persona=ps;cp_real,cp=cps
 clientes_vigentes,_=_indice625(S.E.crudo,'clientes','id')
 datos=S.modulo_recortado(real,persona,cp,'seo/seo') or {}
 seo_id,dup_seo=_indice625(datos,'clientes','cliente_id')
 permitidos={cid for cid in seo_id if cid in clientes_vigentes and _cliente625(S,cid,ps,cps)}
 def vigente():
  actual=_autoridad625(S,real,persona)
  if actual[2]!=firma or any(not _cliente625(S,cid,actual[0],actual[1]) for cid in permitidos):raise ErrorSEO625(403)
  if _autoridad625(S,real,persona)[2]!=firma:raise ErrorSEO625(403)
 vigente()
 if not permitidos:return {'fecha':S.P.hoy_iso(),'clientes':[],'recomendaciones':[],'limite':'Solo SEO confirmado de tu cartera. Objetivos locales pendientes no se inventan.'}
 marcas=_marcas625(app)
 servicios=leer(app/'fuentes_verdad/servicios_confirmados.json')
 contextos=leer(app/'fuentes_seo/contextos_confirmados.json')
 candidatos=leer(app/'fuentes_seo/objetivos_candidatos.json')
 servicios_id,dup_servicios=_indice625(servicios,'clientes','cliente_id')
 contexto_id,dup_contexto=_indice625(contextos,'clientes','cliente_id')
 if not isinstance(candidatos,dict) or not isinstance(candidatos.get('candidatos',[]),list):raise ErrorSEO625(503)
 vigente()
 resultados=[];recomendaciones=[]
 for cid,fila in servicios_id.items():
  if cid not in permitidos or cid in dup_contexto:continue
  if not isinstance(fila.get('servicios',{}),dict):raise ErrorSEO625(503)
  if fila.get('servicios',{}).get('seo')!='sí':continue
  vigente()
  if not all(S.P.ver(p,{'tipo':'cliente_detalle','cliente_id':cid},ctx)['ok'] for p,ctx in ((real,cp_real),(persona,cp))):continue
  # No exportar contratos, importes ni enlaces del registro privado.
  confirmado=contexto_id.get(cid,{})
  contexto={**confirmado,'cliente_id':cid,'servicio_seo_confirmado':True,'fuente_servicio':'Cartera actual contrastada',
   'ciudades_verificadas':confirmado.get('ciudades_verificadas') or [],'servicios_reales':confirmado.get('servicios_reales') or []}
  web=clientes_vigentes[cid].get('web')
  salida=sanear_urls(cargar_local(app,contexto,S.P.hoy_iso()),web)
  vigente()
  salida['objetivos_historicos']=proyectar_candidatos(candidatos,cid,S.P.hoy_iso())
  resultados.append(salida)
  persona_seo=_responsable625(S,cid,S.P.hoy_iso())
  for propuesta in salida.get('prioridades',[]):
   ev=propuesta.get('evidencia') or {}
   etiqueta='Maps' if ev.get('canal')=='maps' else 'Orgánico'
   identidad='|'.join(str(v or '') for v in (cid,propuesta.get('tipo'),ev.get('consulta'),ev.get('consulta_medida'),ev.get('canal'),ev.get('medicion_id'),propuesta.get('url')))
   titulo={'medir':'Completar la medición SEO local','revisar_posicion':'Revisar la consulta objetivo','revisar_pagina':'Revisar una página con pérdida de clics','revisar_plan_contenido':'Revisar el plan editorial'}.get(propuesta['tipo'],'Revisar evidencia SEO')
   texto=f"{etiqueta}: {ev.get('consulta_medida') or ev.get('consulta') or 'Consulta pendiente'} · posición {ev.get('posicion') if ev.get('posicion') is not None else 'no disponible'}." if ev else 'La fuente registra una señal de contenido o clics que requiere contrastar.'
   if propuesta.get('verificar_contexto'):texto+=' Falta verificar dispositivo y ubicación del motor; no es una posición única acreditada.'
   recomendaciones.append({'cliente_id':cid,'regla_id':'seo_'+hashlib.sha256(identidad.encode()).hexdigest()[:16],'area':'seo','titulo':titulo,'motivo':texto,'accion':propuesta['accion'],'responsable_id':persona_seo,'responsable_role':'seo','certeza':'Revisar medición','criterio_entrega':'Consulta, URL o ficha, fecha, ubicación y dispositivo contrastados; evidencia del cambio o siguiente paso. Posición 1 es aspiración, no garantía.','evidencias':[{'fuente':ev.get('fuente') or propuesta.get('fuente') or 'SEO local','fecha':ev.get('fecha') or propuesta.get('fecha'),'texto':texto}]})
  if not salida['habilitado']:
   recomendaciones.append({'cliente_id':cid,'regla_id':'seo_confirmar_objetivo_local','area':'seo','titulo':'Confirmar el objetivo SEO local',
    'motivo':'SEO está confirmado; faltan ciudad objetivo y servicios reales verificados para comparar las consultas locales.',
    'accion':'Contrastar ciudad y servicios con el brief vigente. Registrar las consultas objetivo; después comparar orgánico y Maps por separado.',
    'responsable_id':persona_seo,'responsable_role':'seo','certeza':'Datos pendientes','criterio_entrega':'Ciudad y servicios con fuente vigente; objetivo de posición 1 como aspiración, sin promesa contractual.',
    'evidencias':[{'fuente':'Cartera actual contrastada','fecha':fila.get('leida'),'texto':'Servicio SEO declarado; no implica que la medición ni los objetivos estén completos.'}]+[{'fuente':c['fuente'],'fecha':c['fecha_documento'],'texto':f"Histórico pendiente de contraste: {c['tipo']} · {c['valor']}. No confirma vigencia ni activa consultas."} for c in salida['objetivos_historicos'][:9]]})
 vigente()
 if _marcas625(app)!=marcas:raise ErrorSEO625(503)
 vigente()
 return {'fecha':S.P.hoy_iso(),'clientes':resultados,'recomendaciones':recomendaciones,'limite':'Solo SEO confirmado de tu cartera. Objetivos locales pendientes no se inventan.'}

def enganchar(Manejador,S):
 original=Manejador._api_get
 def get(self,ruta,q,real,persona):
  if ruta!='/api/cerebro/seo':return original(self,ruta,q,real,persona)
  if S.E.nucleo_bloqueado:return self.responder(503,{'error':'Datos temporalmente bloqueados.'})
  if not isinstance(q,dict) or set(q)-{'yo','como'}:return self.responder(400,{'error':'Filtro no válido.'})
  try:
   _autoridad625(S,real,persona)
   doc=generar(S,real,persona)
   _autoridad625(S,real,persona)
   return self.responder(200,doc)
  except ErrorSEO625 as e:return self.responder(e.codigo,{'error':str(e)})
  except (OSError,ValueError,TypeError,KeyError,AttributeError,IndexError,OverflowError,RecursionError):
   return self.responder(503,{'error':'Las fuentes SEO no superan la validación.'})
 Manejador._api_get=get

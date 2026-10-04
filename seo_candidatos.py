"""Proyección mínima de objetivos históricos. No confirma ni activa consultas."""
from datetime import date
import re
TIPOS={'ciudad_objetivo':'Ciudad documentada','servicio_prioritario':'Servicio prioritario',
 'servicio_objetivo':'Servicio documentado','audiencia_objetivo':'Audiencia documentada',
 'servicio_brief':'Servicio del brief','servicio_prioritario_comercial':'Prioridad comercial',
 'servicios_cartera':'Servicios documentados','decision_estrategica':'Decisión pendiente'}
PRIVADO=re.compile(r'@|https?://|\b(?:CIF|NIF|token|password|secret|request_id)\b|[€$]|\b\d{7,}\b',re.I)
def texto(v,n=220):
 if not isinstance(v,str) or PRIVADO.search(v):return None
 return re.sub(r'\s+',' ',v).strip()[:n] or None

def proyectar(documento,cid,hoy):
 try:corte=date.fromisoformat(hoy)
 except (ValueError,TypeError):return []
 if not isinstance(documento,dict) or not isinstance(documento.get('candidatos'),list):return []
 salida=[]
 for c in documento['candidatos']:
  if not isinstance(c,dict) or c.get('cliente_id')!=cid or not isinstance(c.get('tipo'),str) or c.get('tipo') not in TIPOS:continue
  if c.get('estado')!='pendiente_contraste' or c.get('activar_consultas') is not False or c.get('benchmark_confirmado') is not False:continue
  try:fecha=date.fromisoformat(c.get('fecha_estado_historico')).isoformat()
  except (ValueError,TypeError):continue
  if date.fromisoformat(fecha)>corte:continue
  valor=texto(c.get('valor'));razones=c.get('razones_pendiente')
  if not valor:continue
  salida.append({'tipo':TIPOS[c['tipo']],'valor':valor,'fecha_documento':fecha,
   'estado':'Histórico; pendiente de contraste','fuente':'Documento local de objetivos del cliente',
   'razones':[t for t in (texto(v) for v in razones if isinstance(v,str)) if t][:5] if isinstance(razones,list) else [],
   'activar_consultas':False,'benchmark_confirmado':False})
 return salida[:20]

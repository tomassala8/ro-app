"""Candidato puro y acotado; no lee/escribe datos ni recalcula el resto de la verdad."""
from copy import deepcopy
from hashlib import sha256

GASTO = '100 € o más gastados en Meta en 7 días y 0 leads'
CAPTACION = 'Captación con problemas de publicidad o seguimiento'
BLOQUEO = 'Bloqueo callado: 51.7 días'

def preparar(documento, target_hash):
    """Sólo admite la estructura exacta revisada. Cualquier variación bloquea."""
    if not isinstance(documento,dict) or not isinstance(target_hash,str):raise ValueError('estructura_no_confirmada')
    detalles=documento.get('clientes');comunes=documento.get('comun');resumen=documento.get('resumen')
    if not isinstance(detalles,list) or not isinstance(comunes,list) or not isinstance(resumen,dict):raise ValueError('estructura_no_confirmada')
    matches=[v for v in detalles if isinstance(v,dict) and isinstance(v.get('cliente_id'),str) and sha256(v['cliente_id'].encode()).hexdigest()==target_hash]
    if len(matches)!=1:raise ValueError('identidad_no_unica')
    d=matches[0];cid=d['cliente_id'];cs=[v for v in comunes if isinstance(v,dict) and v.get('id')==cid]
    if len(cs)!=1:raise ValueError('identidad_no_unica')
    c=cs[0]
    if d.get('motivos')!=[GASTO,BLOQUEO,CAPTACION] or d.get('gravedad')!='critico' or d.get('salud')!=47 or d.get('bloqueo_callado')is not True or (d.get('bloqueos')or{}).get('dias_max')!=51.7 or c.get('gravedad')!='critico' or c.get('motivo')!='Gasto en publicidad sin leads' or c.get('n_motivos')!=3:raise ValueError('evidencia_distinta_revisar')
    for label in ('critico','atencion','bien'):
        value=resumen.get(label)
        if isinstance(value,bool) or not isinstance(value,int) or value!=sum(v.get('gravedad')==label for v in comunes):raise ValueError('resumen_incoherente')
    out=deepcopy(documento);dd=next(v for v in out['clientes'] if v['cliente_id']==cid);cc=next(v for v in out['comun'] if v['id']==cid)
    dd.update(motivos=[BLOQUEO],gravedad='atencion',salud=None,salud_sello='Sin puntuación acreditada; referencia anterior conservada',referencia_anterior_290={'generado':documento.get('generado'),'motivos_paid_no_acreditados':[GASTO,CAPTACION],'salud':47,'estado':'referencia_anterior_no_alerta_actual','cobertura':'Sin evidencia 220 suficiente ni cohorte de ventas; no recalculada'})
    cc.update(gravedad='atencion',motivo='Tareas bloqueadas',n_motivos=1)
    out['resumen']['critico']-=1;out['resumen']['atencion']+=1
    allowed=[f'/clientes/{detalles.index(d)}/{k}' for k in ('motivos','gravedad','salud','salud_sello','referencia_anterior_290')]+[f'/comun/{comunes.index(c)}/{k}' for k in ('gravedad','motivo','n_motivos')]+['/resumen/critico','/resumen/atencion']
    return out,{'version':'290.candidato.1','cliente_id':cid,'whitelist_paths':allowed,'cambios':{'detalles':1,'comunes':1,'referencias_paid':2,'critico_delta':-1,'atencion_delta':1},'promovido':False,'fecha_generado_preservada':documento.get('generado')}

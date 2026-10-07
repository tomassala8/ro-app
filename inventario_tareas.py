"""Paridad local de tareas: conservar backlog/futuro/completado y estados de lista reales."""
from datetime import date


def catalogo_listas(doc):
    out,detalle={},{}
    for lid,r in (doc.get('listas') or {}).items():
        if not r.get('ok'):
            continue
        estados=sorted((x for x in r.get('estados') or [] if isinstance(x,dict) and isinstance(x.get('status'),str)),key=lambda x:x.get('orderindex',0))
        out[str(lid)]=list(dict.fromkeys(x['status'] for x in estados))
        detalle[str(lid)]=[{'estado':x['status'],'tipo':x.get('type'),'orden':x.get('orderindex')} for x in estados]
    return out,detalle


def grupo(t,vence,hoy):
    if t.get('tipo_estado') in ('closed','done'):
        return 'completadas'
    if (t.get('estado') or '').lower() in ('backlog','planning mensual'):
        return 'backlog'
    if not vence:
        return 'sin_fecha'
    if vence < hoy:
        return 'vencidas'
    if vence == hoy:
        return 'hoy'
    if (vence-hoy).days <= 7:
        return 'semana'
    return 'futuro'


def extras(tareas,vistas,usuarios,por_carpeta,nombres,hoy,fecha_ms,limpiar_nombre,extra_de,prioridades):
    """Una fila por asignado conocido. No desaparece una tarea por fecha o estado.
    Los no asignados requieren endpoint específico con permisos de dirección/ops.
    """
    out=[]
    for t in tareas:
        vence=fecha_ms(t.get('vence'))
        vence=vence.date() if vence else None
        cli=por_carpeta.get(str(t.get('carpeta_id') or ''))
        pids=list(dict.fromkeys(usuarios.get(str(a.get('id'))) for a in t.get('asignados') or []))
        pids=[p for p in pids if p]
        for pid in pids:
            if (pid,t['id']) in vistas:
                continue
            fila={'persona_id':pid,'id':t['id'],'tarea':limpiar_nombre(t.get('nombre'))[:120],
                  'cli':cli[0] if cli else None,'cliente':(cli[1] or nombres.get(cli[0])) if cli else 'Personal',
                  'estado':t.get('estado'),'tipo_estado':t.get('tipo_estado'),'grupo':grupo(t,vence,hoy),
                  'prio_n':prioridades.get(t.get('prioridad'),5),'vence':str(vence) if vence else None,
                  'vencida':bool(vence and vence<hoy and t.get('tipo_estado') not in ('closed','done')),
                  'devuelta':False,'comparte':len(pids)>1,'extra':True,'padre':t.get('padre'),'cerrada':t.get('cerrada')}
            fila.update(extra_de(t['id'],pid))
            out.append(fila);vistas.add((pid,t['id']))
    return out

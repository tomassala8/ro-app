"""Baseline de funciones puras anterior a640, sólo para reproducción sintética."""
def dia(v):
    try:
        return date.fromisoformat(v) if isinstance(v, str) else None
    except ValueError:
        return None

def responsables(cid, asignaciones, personas, hoy):
    vigentes = []
    for a in asignaciones:
        if not isinstance(a, dict):
            continue
        if a.get('cliente_id') != cid or a.get('silla') != 'trafficker':
            continue
        (desde, hasta) = (dia(a.get('desde')), dia(a.get('hasta')) if a.get('hasta') else None)
        if not desde or (a.get('hasta') and (not hasta)):
            return []
        if desde > hoy or (hasta and hasta < hoy):
            continue
        vigentes.append(a)
    if len(vigentes) != 1:
        return []
    a = vigentes[0]
    p = personas.get(a.get('persona_id')) or {}
    roles = p.get('puestos')
    if not p or p.get('estado') != 'activo' or p.get('activo') is False or (p.get('id') != a.get('persona_id')) or (not isinstance(roles, list)) or any((not isinstance(x, str) or not x for x in roles)) or (len(set(roles)) != len(roles)) or ('trafficker' not in roles) or (a.get('principal') is not True) or (a.get('confianza') != 'confirmada') or a.get('duda') or (a.get('suplencia') and (not hasta)):
        return []
    return [p['id']]

def reglas_confirmadas(reglas):
    """Sólo política explícita compatible; conflictos no activan la cadencia."""
    if not isinstance(reglas, dict):
        return []
    regla = reglas.get('regla')
    if not isinstance(regla, dict) or regla.get('id') != REGLA_ID or type(regla.get('cadencia_dias')) is not int or (regla['cadencia_dias'] != 15) or (regla.get('responsable_role') != 'trafficker'):
        return []
    filas = reglas.get('clientes')
    if not isinstance(filas, list):
        return []
    cantidades = {}
    for r in filas:
        if isinstance(r, dict) and isinstance(r.get('cliente_id'), str):
            cid = r['cliente_id']
            cantidades[cid] = cantidades.get(cid, 0) + 1
    return [r for r in filas if isinstance(r, dict) and isinstance(r.get('cliente_id'), str) and r['cliente_id'] and (r['cliente_id'].strip() == r['cliente_id']) and (cantidades[r['cliente_id']] == 1) and (r.get('estado_cohorte') == 'confirmada') and (type(r.get('cadencia_dias')) is int) and (r['cadencia_dias'] == 15) and (r.get('responsable_role') == 'trafficker') and (r.get('tipo_cohorte') == 'metodo_actual_recurrente')]

def sugerencias(reglas, asignaciones, personas, reuniones, cobertura, hoy, puede_ver):
    """No declara ausencia/incumplimiento a partir de un feed incompleto.
    Reunión válida requiere identidad de cliente, celebración y rol verificados.
    """
    if not isinstance(hoy, date):
        raise ValueError('Falta el día de referencia.')
    cobertura = cobertura if isinstance(cobertura, dict) else {}
    out = []
    for r in reglas_confirmadas(reglas):
        cid = r.get('cliente_id')
        if not puede_ver(cid):
            continue
        owners = responsables(cid, asignaciones, personas, hoy)
        item = {'cliente_id': cid, 'regla_id': REGLA_ID, 'cadencia_dias': 15, 'responsable_role': 'trafficker', 'responsables_ids': owners, 'responsable_id': owners[0] if len(owners) == 1 else None, 'ultima_confirmada': None, 'proxima_revision': None, 'estado': 'sin_dato', 'incumplimiento': None, 'accion': 'confirmar_ultima_reunion', 'recomendacion': 'Confirma la última reunión celebrada con el especialista de publicidad; no hay evidencia suficiente para calcular la próxima.', 'fuentes_operativas': [{'tipo': 'decision_humana', 'fecha': '2026-10-03', 'detalle': 'Seguimiento cada 15 días con trafficker.'}]}
        if len(owners) != 1:
            item.update(estado='confirmar_responsable', accion='confirmar_responsable', recomendacion='Confirma el trafficker responsable de esta cuenta antes de programar su seguimiento.')
        eventos = []
        for ev in reuniones if isinstance(reuniones, list) else []:
            if not isinstance(ev, dict):
                continue
            f = dia(ev.get('fecha'))
            if ev.get('cliente_id') == cid and f and (f <= hoy) and (ev.get('celebrada') is True) and (ev.get('cliente_confirmado') is True) and (ev.get('rol_responsable_confirmado') == 'trafficker') and ev.get('fuente'):
                eventos.append((f, ev))
        if eventos:
            (f, ev) = max(eventos, key=lambda x: x[0])
            prox = f + timedelta(days=15)
            item['ultima_confirmada'] = f.isoformat()
            item['proxima_revision'] = prox.isoformat()
            item['fuentes_operativas'].append({'tipo': 'reunion_celebrada', 'fecha': f.isoformat(), 'fuente': ev['fuente'] if ev['fuente'] in ('zoom', 'fathom', 'ghl', 'registro_local') else 'evidencia interna verificada'})
            if len(owners) == 1:
                if hoy <= prox:
                    item.update(estado='en_cadencia', accion='preparar_seguimiento', recomendacion='Prepara el siguiente seguimiento con el trafficker responsable.')
                elif cobertura.get('completa') is True and dia(cobertura.get('hasta')) == hoy and dia(cobertura.get('desde')) and (dia(cobertura['desde']) <= f):
                    item.update(estado='revisar_cadencia', accion='proponer_seguimiento', recomendacion='La copia confirmada no muestra una reunión posterior dentro de la cadencia; revisa y propón el seguimiento. No se ha agendado ni enviado nada.')
                else:
                    item.update(estado='confirmar_recencia', accion='confirmar_ultima_reunion', recomendacion='La última reunión confirmada supera la cadencia, pero la cobertura es parcial: comprueba si hubo otra antes de proponer fecha.')
        out.append(item)
    return out

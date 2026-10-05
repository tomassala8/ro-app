"""Baseline mínimo de funciones/constantes AST; no importa productor ni lee datos."""
def inicio_dia(n):
    """ms del comienzo (00:00 de Madrid) del día de hace n días. Ventanas de días naturales cerrados, sin hoy."""
    d = HOY.date() - dt.timedelta(days=n)
    return int(dt.datetime.combine(d, dt.time(0), MAD).timestamp() * 1000)
MEDIOS_LEAD = {'form', 'facebook', 'instagram', 'survey', 'calendar', 'whatsapp', 'paid', 'cpc', 'ads', 'tiktok', 'google', 'linkedin'}
MEDIOS_NO = {'manual', 'csv_import', 'import', 'other', 'api', 'sin origen'}
RX_PRUEBA = re.compile('(no es un lead real|ejemplo demo|\\bprueba\\b|\\btest\\b|dummy)', re.I)
RX_NO_LEAD = re.compile('(candidatura|curso|cliente ro|reuni[oó]n|zoho bookings|creado por claude)', re.I)
RX_LANDING = re.compile('(landing|formulario|form\\b|agendar|web|bofu|home|captura|contacto|cont[aá]ctanos|lead magnet|gu[ií]a)', re.I)
RX_CORREO_PRUEBA = re.compile('(^test|^prueba|@example\\.|@test\\.|@mail-tester\\.|@mailinator\\.|\\+test@)', re.I)

def clasificar(lead, sid):
    """(es_lead, motivo). motivo = por qué no cuenta: otro_negocio, prueba, manual, importado, no_lead, sin_origen."""
    medio = (lead.get('medio') or '').strip()
    fuente = lead.get('fuente') or ''
    texto = f'{medio} {fuente}'
    tags = ' '.join(lead.get('tags') or [])
    exc = EXCLUSIONES.get(sid, {})
    if any((x.lower() in texto.lower() or x.lower() in tags.lower() for x in exc.get('origen_contiene', []))):
        return (False, 'otro_negocio')
    if RX_PRUEBA.search(texto) or RX_PRUEBA.search(tags) or RX_CORREO_PRUEBA.search(((lead.get('privado') or {}).get('correo') or '').strip()):
        return (False, 'prueba')
    if lead.get('manual'):
        return (False, 'manual')
    if medio.lower() in ('csv_import', 'import'):
        return (False, 'importado')
    if RX_NO_LEAD.search(texto):
        return (False, 'no_lead')
    if medio.lower() in MEDIOS_LEAD or RX_LANDING.search(medio):
        return (True, None)
    return (False, 'sin_origen')
COMUNICACION = {'TYPE_CALL', 'TYPE_SMS', 'TYPE_CUSTOM_SMS', 'TYPE_WHATSAPP', 'TYPE_EMAIL', 'TYPE_FACEBOOK', 'TYPE_INSTAGRAM', 'TYPE_GMB', 'TYPE_LIVE_CHAT', 'TYPE_CUSTOM_EMAIL', 'TYPE_CUSTOM_PROVIDER_SMS', 'TYPE_CUSTOM_PROVIDER_EMAIL', 'TYPE_CUSTOM_CALL', 'TYPE_IVR_CALL'}
AUTOMATICO = {'workflow', 'campaign', 'bulk_actions', 'bulk_action', 'automation', 'trigger'}

def iso_ms(s):
    if s is None:
        return None
    if isinstance(s, (int, float)):
        return int(s)
    try:
        return int(dt.datetime.fromisoformat(str(s).replace('Z', '+00:00')).timestamp() * 1000)
    except Exception:
        return None

def timestamp_mensaje(valor):
    """Epoch ms finito o ISO con zona explícita; no adivinar zona de un mensaje."""
    if isinstance(valor, (int, float)) and (not isinstance(valor, bool)):
        return int(valor) if math.isfinite(valor) and valor >= 0 else None
    if not isinstance(valor, str):
        return None
    try:
        fecha = dt.datetime.fromisoformat(valor.replace('Z', '+00:00'))
        return int(fecha.timestamp() * 1000) if fecha.tzinfo is not None else None
    except (ValueError, OverflowError, OSError):
        return None

def resumir_intentos(mensajes, creado, corte):
    """No usar conversaciones previas como intentos del lead recién creado.

    Si un mensaje no tiene fecha válida o está en el futuro, el conteo/primer
    intento son desconocidos; los mensajes fechados se conservan como observación.
    """
    (inicio, fin) = (timestamp_mensaje(creado), timestamp_mensaje(corte))
    if inicio is None or fin is None or inicio > fin:
        return {'primer_min': None, 'intentos_72h': None, 'intentos_observados': None, 'fechas_desconocidas': len(mensajes)}
    fechas = [timestamp_mensaje(x.get('dateAdded')) for x in mensajes]
    desconocidas = sum((t is None or t > fin for t in fechas))
    validas = sorted((t for t in fechas if t is not None and inicio <= t <= fin))
    return {'primer_min': (validas[0] - inicio) / 60000 if validas and (not desconocidas) else None, 'intentos_72h': sum((t <= inicio + 72 * 3600000.0 for t in validas)) if not desconocidas else None, 'intentos_observados': len(validas) if not desconocidas else None, 'fechas_desconocidas': desconocidas}

def intentos_medidos672(lead):
    """No certificar contadores de un cache legacy o de otro corte como actuales."""
    n = lead.get('intentos')
    m = lead.get('intentos_medicion')
    if type(n) is not int or not 0 <= n <= 9007199254740991 or (not isinstance(m, dict)):
        return False
    if set(m) != {'fuente', 'estado', 'desde_ms', 'hasta_ms', 'completa'} or m.get('fuente') != 'ghl_conversacion' or m.get('estado') != 'observado_parcial' or (m.get('completa') is not False):
        return False
    (desde, hasta) = (timestamp_mensaje(m.get('desde_ms')), timestamp_mensaje(m.get('hasta_ms')))
    return desde is not None and hasta is not None and (desde == timestamp_mensaje(lead.get('creado'))) and (desde <= hasta) and (hasta == AHORA_MS)

def ms_iso(ms):
    return dt.datetime.fromtimestamp(ms / 1000, MAD).strftime('%Y-%m-%d %H:%M') if ms else None

def pct(a, b):
    return round(a * 100 / b, 1) if b else None

def ref_de(*partes):
    return hashlib.sha1('·'.join(map(str, partes)).encode()).hexdigest()[:12]

def leer_subcuenta(g, loc):
    """Leads 30 días + su conversación, citas 90/30 días y prueba de flujos. Nada se escribe."""
    out = {'leads': [], 'citas': [], 'calendarios': [], 'flujos': None, 'errores': []}
    desde = dt.datetime.fromtimestamp(inicio_dia(VENTANA_LEADS + 1) / 1000, dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    tot = g.req(loc, 'POST', '/contacts/search', {'locationId': loc, 'pageLimit': 1})
    out['contactos_total'] = tot.get('total') if '_error' not in tot else None
    (contactos, pagina) = ([], 1)
    while pagina <= 3:
        r = g.req(loc, 'POST', '/contacts/search', {'locationId': loc, 'pageLimit': 100, 'page': pagina, 'filters': [{'field': 'dateAdded', 'operator': 'range', 'value': {'gte': desde}}], 'sort': [{'field': 'dateAdded', 'direction': 'desc'}]})
        if '_error' in r:
            out['errores'].append(f"contactos {r['_error']}")
            break
        cs = r.get('contacts', [])
        contactos += cs
        if len(cs) < 100:
            break
        pagina += 1
    cals = g.req(loc, 'GET', '/calendars/', locationId=loc)
    if '_error' in cals:
        out['errores'].append(f"calendarios {cals['_error']}")
    t0 = AHORA_MS - 90 * 86400000.0
    t1 = AHORA_MS + 30 * 86400000.0
    for cal in cals.get('calendars', []) or []:
        out['calendarios'].append({'id': cal.get('id'), 'nombre': cal.get('name'), 'activo': cal.get('isActive', True)})
        e = g.req(loc, 'GET', '/calendars/events', locationId=loc, calendarId=cal['id'], startTime=int(t0), endTime=int(t1))
        if '_error' in e:
            out['errores'].append(f"eventos {e['_error']}")
            continue
        for ev in e.get('events', []) or []:
            if ev.get('deleted'):
                continue
            out['citas'].append({'id': ev.get('id'), 'calendario': cal.get('name'), 'inicio': iso_ms(ev.get('startTime')), 'estado': (ev.get('appointmentStatus') or ev.get('appoinmentStatus') or 'sin_estado').lower(), 'contacto': ev.get('contactId'), 'creada': iso_ms(ev.get('dateAdded'))})
    con_cita = {c['contacto'] for c in out['citas'] if c['contacto']}
    for c in contactos[:150]:
        medio = ((c.get('attributionSource') or {}).get('medium') or '').lower() or None
        manual = medio == 'manual' or (c.get('attributionSource') or {}).get('sessionSource') == 'CRM UI'
        creado = iso_ms(c.get('dateAdded'))
        lead = {'contacto': c.get('id'), 'creado': creado, 'medio': medio or (c.get('source') or 'sin origen'), 'fuente': c.get('source'), 'manual': manual, 'cita': c.get('id') in con_cita, 'tags': c.get('tags') or [], 'privado': {'nombre': ' '.join((x for x in [c.get('firstName'), c.get('lastName')] if x)) or c.get('contactName'), 'telefono': c.get('phone'), 'correo': c.get('email')}}
        (lead['es_lead'], lead['descartado']) = clasificar(lead, loc)
        if lead['es_lead']:
            cv = g.req(loc, 'GET', '/conversations/search', locationId=loc, contactId=c.get('id'), limit=5)
            msgs = []
            conversaciones = cv.get('conversations') if isinstance(cv, dict) else None
            conversaciones_validas = isinstance(cv, dict) and '_error' not in cv and isinstance(conversaciones, list) and all((isinstance(x, dict) and isinstance(x.get('id'), str) and x['id'] for x in conversaciones))
            for conv in conversaciones[:2] if conversaciones_validas else []:
                m = g.req(loc, 'GET', f"/conversations/{conv['id']}/messages", limit=100)
                paquete = m.get('messages') if isinstance(m, dict) else None
                mensajes = paquete.get('messages') if isinstance(paquete, dict) else None
                if not isinstance(m, dict) or '_error' in m or (not isinstance(mensajes, list)) or any((not isinstance(x, dict) for x in mensajes)):
                    conversaciones_validas = False
                else:
                    msgs += mensajes
            com = [x for x in msgs if x.get('messageType') in COMUNICACION]
            sal = sorted([x for x in com if x.get('direction') == 'outbound' or (x.get('messageType') == 'TYPE_CALL' and x.get('direction') != 'inbound')], key=lambda x: timestamp_mensaje(x.get('dateAdded')) or 0)
            humanos = [x for x in sal if (x.get('source') or '').lower() not in AUTOMATICO]
            autos = [x for x in sal if (x.get('source') or '').lower() in AUTOMATICO]
            intentos_h = resumir_intentos(humanos, creado, AHORA_MS)
            intentos_a = resumir_intentos(autos, creado, AHORA_MS)
            wa = [x for x in sal if x.get('messageType') == 'TYPE_WHATSAPP']
            sms = [x for x in sal if x.get('messageType') in ('TYPE_SMS', 'TYPE_CUSTOM_SMS', 'TYPE_CUSTOM_PROVIDER_SMS')]
            lead.update({'humano_min': intentos_h['primer_min'] if conversaciones_validas else None, 'auto_min': intentos_a['primer_min'] if conversaciones_validas else None, 'mensajes_fecha_desconocida': intentos_h['fechas_desconocidas'] + intentos_a['fechas_desconocidas'], 'intentos': intentos_h['intentos_observados'] if conversaciones_validas else None, 'intentos_medicion': {'fuente': 'ghl_conversacion', 'estado': 'observado_parcial' if conversaciones_validas and intentos_h['intentos_observados'] is not None else 'desconocido', 'desde_ms': creado, 'hasta_ms': AHORA_MS, 'completa': False}, 'intentos_72h': intentos_h['intentos_72h'] if conversaciones_validas else None, 'llamadas': sum((1 for x in humanos if 'CALL' in (x.get('messageType') or ''))), 'respondio': any((x.get('direction') == 'inbound' for x in com)), 'wa_env': len(wa), 'wa_fallo': sum((1 for x in wa if (x.get('status') or '').lower() in ('failed', 'undelivered'))), 'sms_env': len(sms), 'sms_fallo': sum((1 for x in sms if (x.get('status') or '').lower() in ('failed', 'undelivered'))), 'mail_env': sum((1 for x in sal if x.get('messageType') == 'TYPE_EMAIL')), 'mail_fallo': sum((1 for x in sal if x.get('messageType') == 'TYPE_EMAIL' and (x.get('status') or '').lower() in ('failed', 'bounced', 'undelivered')))})
        out['leads'].append(lead)
    etapas = {}
    pl = g.req(loc, 'GET', '/opportunities/pipelines', locationId=loc)
    for p_ in pl.get('pipelines', []) or []:
        for st in p_.get('stages', []) or []:
            etapas[st.get('id')] = {'etapa': st.get('name'), 'embudo': p_.get('name')}
    (opps, pagina) = ([], 1)
    while pagina <= 3:
        r = g.req(loc, 'GET', '/opportunities/search', location_id=loc, status='open', limit=100, page=pagina)
        if '_error' in r:
            out['errores'].append(f"oportunidades {r['_error']}")
            break
        lo = r.get('opportunities', []) or []
        opps += lo
        if len(lo) < 100:
            break
        pagina += 1
    out['oportunidades'] = [{'id': o.get('id'), 'contacto': o.get('contactId'), 'creada': iso_ms(o.get('createdAt') or o.get('dateAdded')), 'ultimo_cambio': iso_ms(o.get('lastStageChangeAt') or o.get('lastStatusChangeAt') or o.get('updatedAt')), **(etapas.get(o.get('pipelineStageId')) or {'etapa': None, 'embudo': None})} for o in opps]
    f = g.req(loc, 'GET', '/workflows/', locationId=loc)
    out['flujos'] = {'leido': '_error' not in f, 'error': f.get('_error'), 'n': len(f.get('workflows', []) or []) if '_error' not in f else None, 'lista': [{'nombre': w.get('name'), 'estado': w.get('status')} for w in f.get('workflows') or []] if '_error' not in f else []}
    return out

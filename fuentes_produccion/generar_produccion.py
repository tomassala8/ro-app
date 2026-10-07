#!/usr/bin/env python3
"""generar_produccion.py · M10 Producción → data/produccion/produccion.json. SOLO LECTURA.

Lee: fuentes_produccion/_cache/tareas.json y horas.json (extraer_clickup.py, llave propia de ClickUp),
     PANEL_OPERACIONES_2026-10-01/build/tareas_flujo.json y planificacion.json (lo ya generado por cu.py),
     fuentes_captacion/anuncios.json (anuncios de Meta por cuenta, de M6; solo lectura),
     data/personas.json, data/asignaciones.json, data/clientes/<id>.json.
Recorte (lo hace servir.py, contrato de E0): filas con persona_id → la persona, su jefe, operaciones, RRHH y
dirección; filas con cliente_id → quien ve el detalle de ese cliente. En la cola de cada persona el cliente va
en «cli» (no en cliente_id) para que una persona de producción vea sus propias tareas aunque no lleve el cliente.
Sin euros: del anuncio solo salen índices (media de la cuenta = 100), nunca gasto ni coste.
"""
import re, statistics, math, datetime as dt
from collections import defaultdict
import sys as _sys
_sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parents[1]))
from permisos import sin_importes as _sin_importes   # R12 (seguridad): misma regla que el servidor


def limpiar_tarea(texto):
    """Título de tarea sin correos, teléfonos ni importes (facturas de RO, presupuestos de prueba…): Producción va sin
    euros y la ve gente que no ve el dinero de la empresa ni del cliente. El título completo sigue en ClickUp."""
    return _sin_importes(limpiar(texto))


from comun_equipo import (leer, escribir, personas, miembros_clickup, fecha_ms, norm,
                          DATA, CACHE, PANEL, APP, HOY, AHORA, ESTADOS_REVISION_INTERNA, ESTADOS_TRABAJO, tipo_tarea, limpiar, es_urgente)

from identidad_generadores_212 import identidades, clientes_directos

LUNES = HOY - dt.timedelta(days=HOY.weekday())
FIN_SEMANA = LUNES + dt.timedelta(days=7)
HACE30 = HOY - dt.timedelta(days=30)  # 30 días naturales cerrados: del día −30 a ayer (sin el día en curso)
MES1 = HOY.replace(day=1)
TOPE = {'account': 12, 'trafficker': 16, 'crm': 16}  # D-07
NO_COLA = {'backlog', 'planning mensual'}
ESPERA_CLIENTE = {'revisión cliente', 'enviar  cliente', 'enviar cliente', 'ver cliente', 'campaña en curso'}
from estados_catalogo import resolver_estado
GRUPOS_AHORA = ('vencida', 'hoy', 'semana', 'bloqueada')   # «tu cola ahora»: lo que depende de ti (R12, una sola definición)
PRIO = {'urgent': 1, 'high': 2, 'normal': 3, 'low': 4}
PRIO_TXT = {'urgent': 'Urgente', 'high': 'Alta', 'normal': 'Normal', 'low': 'Baja'}


def d_local(ms):
    f = fecha_ms(ms)
    return f.date() if f else None


def hist_desde(t):
    """{estado: datetime de entrada} (ClickUp da la primera entrada en cada estado y el tiempo total)."""
    out = {}
    for x in t.get('historial') or []:
        if x.get('desde') and x.get('estado'):
            out[x['estado']] = fecha_ms(x['desde'])
    return out


def es_final(t, catalogo):
    return resolver_estado(t, catalogo)['final_flujo']


def devuelta(t):
    """Está en un estado de trabajo y antes pasó por una revisión interna o del cliente → se la han devuelto."""
    if (t.get('estado') or '') not in ESTADOS_TRABAJO:
        return False
    h = hist_desde(t)
    act = fecha_ms(t.get('estado_desde'))
    revs = [v for k, v in h.items() if k in ESTADOS_REVISION_INTERNA | {'revisión cliente', 'ver cliente'}]
    return bool(revs and act and min(revs) < act)


def a_la_primera(t):
    """Pasó por revisión interna y, después de la primera revisión, no volvió a un estado de trabajo.
    Aproximado: ClickUp no dice cuántas veces se entra en un estado (ver _ESTADO_produccion.md)."""
    h = hist_desde(t)
    revs = [v for k, v in h.items() if k in ESTADOS_REVISION_INTERNA]
    if not revs:
        return None
    r0 = min(revs)
    return not any(v > r0 for k, v in h.items() if k in ESTADOS_TRABAJO)


def llegada(t, catalogo):
    """Primer hito operativo observado; no acredita aceptación ni resultado exitoso.
    Los nombres del historial sólo identifican revisión, nunca cierre.
    Una fecha cerrada sólo se admite si el estado actual es terminal en su lista.
    """
    h = hist_desde(t)
    cands = [v for k, v in h.items() if v and k in
             {'revisión project manager', 'revisión cliente', 'ver cliente', 'enviar  cliente'}]
    if es_final(t, catalogo) and t.get('cerrada'):
        cierre = fecha_ms(t['cerrada'])
        if cierre:
            cands.append(cierre)
    return min(cands) if cands else None


def medicion_revisiones_account(fila, sello, hoy):
    """Metadato puro: cero sólo medido con campos originales y sello válidos."""
    rev = fila.get('rev_pm') if isinstance(fila, dict) else None
    fecha = None
    if isinstance(sello, str):
        try:
            fecha = dt.datetime.fromisoformat(sello.replace('Z', '+00:00').replace(' ', 'T')).date()
        except ValueError:
            pass
    valido = isinstance(rev, dict) and all(type(rev.get(k)) is int and rev[k] >= 0 for k in ('n', 'mas48'))
    valido = valido and rev['mas48'] <= rev['n'] and fecha is not None and fecha <= hoy
    return {'estado': 'medido' if valido else 'sin_dato', 'fuente': 'flujo', 'fecha': sello if fecha is not None and fecha <= hoy else None}


def sumar_horas_cliente(entradas, por_carpeta, hoy):
    """Observaciones del mes y anterior; una carpeta sin registros queda desconocida."""
    mes = hoy.replace(day=1)
    anterior = (mes - dt.timedelta(days=1)).replace(day=1)
    actual, previo, descartadas = defaultdict(float), defaultdict(float), 0
    for e in entradas if isinstance(entradas, list) else []:
        if not isinstance(e, dict):
            descartadas += 1
            continue
        horas, inicio = e.get('horas'), e.get('inicio')
        if type(horas) not in (int, float) or not math.isfinite(horas) or horas < 0 or horas > 10:
            descartadas += 1
            continue
        try:
            if not isinstance(inicio, str):
                raise ValueError('fecha ausente')
            dia_e = dt.date.fromisoformat(inicio[:10])
        except ValueError:
            descartadas += 1
            continue
        c = por_carpeta.get(str(e.get('carpeta_id') or ''))
        if not c or dia_e > hoy:
            continue
        if dia_e >= mes:
            actual[c[0]] += horas
        elif dia_e >= anterior:
            previo[c[0]] += horas
    return actual, previo, descartadas


def main():
    T = leer(CACHE / 'tareas.json')
    if not T:
        raise SystemExit('Falta fuentes_produccion/_cache/tareas.json: lanza antes  python3 extraer_clickup.py')
    catalogo = leer(CACHE / 'estados_listas.json', {}) or {}
    H = leer(CACHE / 'horas.json', {'entradas': []})
    try:
        horas_disponibles = isinstance(H.get('entradas'), list) and isinstance(H.get('meta', {}).get('generado'), str) and dt.datetime.fromisoformat(H['meta']['generado'].replace('Z', '+00:00').replace(' ', 'T')).date() <= HOY
    except (ValueError, TypeError, KeyError):
        horas_disponibles = False
    personas_fuente = personas()
    P = {p['id']: p for p in personas_fuente}
    identidad = identidades(personas_fuente, miembros_clickup())
    U = identidad['por_usuario']
    por_carpeta, nombres = clientes_directos(DATA)
    # R12 · el nombre de cada cliente sale de la verdad única (lista común); si no está, el de su ficha
    try:
        _vc = leer(DATA / 'verdad/clientes.json', {}) or {}
        nombre_verdad = {c['id']: c.get('nombre') for c in _vc.get('comun', []) if c.get('id')}
    except Exception:
        nombre_verdad = {}
    nombre_cli = lambda cid: nombre_verdad.get(cid) or nombres.get(cid) or cid
    asig = leer(DATA / 'asignaciones.json', [])
    asig = asig if isinstance(asig, list) else asig.get('asignaciones', [])
    vigente = [a for a in asig if not a.get('hasta')]
    account_de = {}
    V = leer(DATA / 'verdad/clientes.json', {}) or {}
    for c in V.get('clientes', []):  # verdad única: el account principal vigente de asignaciones (null si no hay)
        account_de[c['cliente_id']] = c.get('account')
    for a in vigente if not account_de else []:
        if a['silla'] == 'account' and a.get('principal', True):
            account_de.setdefault(a['cliente_id'], a['persona_id'])

    tareas = T['tareas']
    # subtareas de plantilla y contenedores fuera: solo cuenta lo que tiene a alguien asignado
    cola, rev_cli, entregas = [], [], defaultdict(lambda: {'con_fecha': 0, 'en_fecha': 0, 'entregadas': 0, 'primera_si': 0, 'primera_base': 0})
    abiertas_p = defaultdict(lambda: defaultdict(int))
    proyectos_p = defaultdict(set)
    sin_asignar = 0
    for t in tareas:
        est = t.get('estado') or ''
        clasificacion = resolver_estado(t, catalogo)
        cli = por_carpeta.get(str(t.get('carpeta_id') or ''))
        pids = [U.get(str(a['id'])) for a in t.get('asignados') or []]
        pids = [p for p in pids if p]
        vence = d_local(t.get('vence'))
        desde = fecha_ms(t.get('estado_desde'))
        dias_estado = round((AHORA - desde).total_seconds() / 86400, 1) if desde else None
        # ---- revisiones por proyecto (cliente): lo que espera al account o a la revisión técnica ----
        if not es_final(t, catalogo) and cli and est in ('revisión project manager', 'revisión técnica', 'bloqueado'):
            rev_cli.append({'cliente_id': cli[0], 'id': t['id'], 'tarea': limpiar_tarea(t.get('nombre'))[:110], 'estado': est,
                            'dias': dias_estado, 'mas48': bool(dias_estado and dias_estado > 2),
                            'asignados': [P[p]['alias'] if P.get(p) else p for p in pids],
                            'revisa': 'account' if est == 'revisión project manager' else 'técnica' if est == 'revisión técnica' else 'cliente',
                            'account_id': account_de.get(cli[0])})
        # ---- entregas de los últimos 30 días (en fecha y a la primera) ----
        lg = llegada(t, catalogo)
        if lg and HACE30 <= lg.date() < HOY:
            for p in pids:
                e = entregas[p]
                e['entregadas'] += 1
                if vence:
                    e['con_fecha'] += 1
                    e['en_fecha'] += 1 if lg.date() <= vence else 0
                ap = a_la_primera(t)
                if ap is not None:
                    e['primera_base'] += 1
                    e['primera_si'] += 1 if ap else 0
        if es_final(t, catalogo):
            continue
        if not pids:
            sin_asignar += 0 if est in NO_COLA else 1
            continue
        for p in pids:
            abiertas_p[p][est] += 1
            if cli:
                proyectos_p[p].add(cli[0])
        if clasificacion['determinado'] and est in NO_COLA and not (vence and vence < FIN_SEMANA + dt.timedelta(days=7)):
            continue
        # grupo de la cola: hoy · semana · revisión (espera a otro) · bloqueada · después
        vencida = bool(vence and vence < HOY)
        olvidada = bool(vencida and (HOY - vence).days > 30)
        if est == 'bloqueado':
            grupo = 'bloqueada'
        elif est in ESTADOS_REVISION_INTERNA or est in ESPERA_CLIENTE:
            grupo = 'revision'
        elif olvidada:
            grupo = 'olvidada'
        elif vencida:
            grupo = 'vencida'
        elif (vence and vence == HOY) or est in ('diario', 'en curso', 'in progress'):
            grupo = 'hoy'
        elif (vence and vence < FIN_SEMANA) or est == 'planning semanal':
            grupo = 'semana'
        else:
            grupo = 'despues'
        dv = devuelta(t)
        for p in pids:
            cola.append({'persona_id': p, 'id': t['id'], 'tarea': limpiar_tarea(t.get('nombre'))[:120],
                         'cli': cli[0] if cli else None, 'cliente': nombre_cli(cli[0]) if cli else ('Personal' if (t.get('carpeta') or '') in ('hidden', '') and not t.get('espacio') else (t.get('carpeta') if t.get('carpeta') not in (None, 'hidden') else t.get('espacio') or 'Personal')),
                         'estado': est, 'grupo': grupo, 'lista_id': t.get('lista_id'),
                         'estado_determinado': clasificacion['determinado'], 'tipo_estado': clasificacion['tipo'],
                         'estado_nota': clasificacion['motivo'], 'prio_n': 1 if es_urgente(t.get('nombre')) else PRIO.get(t.get('prioridad'), 5),
                         'vence': str(vence) if vence else None, 'vencida': vencida,
                         'dias_estado': dias_estado, 'devuelta': dv, 'comparte': len(pids) > 1})
    cola.sort(key=lambda r: (r['persona_id'], {'vencida': 0, 'hoy': 1, 'bloqueada': 2, 'semana': 3, 'revision': 4, 'despues': 5, 'olvidada': 6}[r['grupo']],
                             not r['vencida'], r['vence'] or '9999', r['prio_n']))

    # ---- horas por persona (mes en curso, últimos 30 días) ----
    hmes, h30 = defaultdict(float), defaultdict(float)
    for e in H.get('entradas', []):
        p = U.get(str(e['usuario_id']))
        if not p or e['horas'] > 10:
            continue
        d = dt.date.fromisoformat(e['inicio'][:10])
        if d >= MES1:
            hmes[p] += e['horas']
        if HACE30 <= d < HOY:
            h30[p] += e['horas']

    # ---- carga de cada persona ----
    cartera_silla = defaultdict(lambda: defaultdict(set))
    for a in vigente:
        if a.get('principal', True):
            cartera_silla[a['persona_id']][a['silla']].add(a['cliente_id'])
    filas_p = []
    for pid, p in P.items():
        if p.get('estado') in ('baja',) or p.get('imputa_horas') == 'no' and not abiertas_p.get(pid):
            continue
        if 'setters' in (p.get('puestos') or []):
            continue
        ab = abiertas_p.get(pid, {})
        mi = [r for r in cola if r['persona_id'] == pid]
        e = entregas.get(pid, {})
        sillas = {s: len(v) for s, v in cartera_silla.get(pid, {}).items()}
        silla_tope = next((s for s in ('account', 'trafficker', 'crm') if s in sillas), None)
        filas_p.append({
            'persona_id': pid, 'nombre': p['nombre'], 'alias': p.get('alias'), 'puesto': p.get('puesto_principal'), 'puestos': p.get('puestos'),
            'jefe': p.get('jefe'), 'estado_persona': p.get('estado'),
            'abiertas': sum(ab.values()), 'por_estado': dict(sorted(ab.items(), key=lambda x: -x[1])),
            'hoy': sum(1 for r in mi if r['grupo'] == 'hoy'), 'semana': sum(1 for r in mi if r['grupo'] == 'semana'),
            'en_revision': sum(1 for r in mi if r['grupo'] == 'revision'), 'bloqueadas': sum(1 for r in mi if r['grupo'] == 'bloqueada'),
            # R12 · UNA definición de «tu cola» (la misma en Mi día y en Producción): GRUPOS_AHORA.
            # «vencidas» = grupo «vencida» (fecha pasada, en tu mano, sin entregar, hasta 30 días); las que esperan
            # revisión de otro o llevan más de 30 días («olvidadas») van aparte y no inflan la cifra.
            'vencidas': sum(1 for r in mi if r['grupo'] == 'vencida'), 'cola_ahora': sum(1 for r in mi if r['grupo'] in GRUPOS_AHORA),
            'fecha_pasada_todas': sum(1 for r in mi if r['vencida']), 'olvidadas': sum(1 for r in mi if r['grupo'] == 'olvidada'), 'devueltas': sum(1 for r in mi if r['devuelta']),
            'proyectos_con_tareas': len(proyectos_p.get(pid, ())),
            'cartera': sillas, 'silla_tope': silla_tope, 'tope': TOPE.get(silla_tope), 'en_cartera': sillas.get(silla_tope) if silla_tope else None,
            'entregadas_30d': e.get('entregadas', 0), 'con_fecha_30d': e.get('con_fecha', 0), 'en_fecha_30d': e.get('en_fecha', 0),
            'pct_en_fecha': round(e['en_fecha'] / e['con_fecha'] * 100) if e.get('con_fecha') else None,
            'revisadas_30d': e.get('primera_base', 0), 'a_la_primera_30d': e.get('primera_si', 0),
            'pct_primera': round(e['primera_si'] / e['primera_base'] * 100) if e.get('primera_base') else None,
            'horas_mes': round(hmes.get(pid, 0), 1), 'horas_30d': round(h30.get(pid, 0), 1),
        })
    filas_p.sort(key=lambda r: r['nombre'])

    # ---- proyectos (cliente): flujo del panel + lo calculado aquí ----
    flujo = leer(PANEL / 'build/tareas_flujo.json', {}) or {}
    plan = leer(PANEL / 'build/planificacion.json', {}) or {}
    hcli, hcli_ant, horas_descartadas = sumar_horas_cliente(H.get('entradas'), por_carpeta, HOY)
    proyectos = []
    for nom, f in flujo.items():
        if nom.startswith('_'):
            continue
        cid = por_carpeta.get(str(f.get('carpeta_id')), (None, None))[0]
        if not cid:
            continue
        rv = [r for r in rev_cli if r['cliente_id'] == cid]
        bl = [r for r in rv if r['estado'] == 'bloqueado']
        proyectos.append({
            'cliente_id': cid, 'cliente': nombres.get(cid, nom), 'account_id': account_de.get(cid),
            'abiertas': sum((f.get('abiertas_por_estado') or {}).values()),
            'revisiones_account': medicion_revisiones_account(f, (flujo.get('_meta') or {}).get('generado'), HOY),
            'rev_account': f['rev_pm']['n'] if medicion_revisiones_account(f, (flujo.get('_meta') or {}).get('generado'), HOY)['estado'] == 'medido' else 0, 'rev_account_48': f['rev_pm']['mas48'] if medicion_revisiones_account(f, (flujo.get('_meta') or {}).get('generado'), HOY)['estado'] == 'medido' else 0, 'rev_account_max': (f.get('rev_pm') if isinstance(f.get('rev_pm'), dict) else {}).get('max_dias', 0),
            'rev_tecnica': (f.get('rev_tecnica') or {}).get('n', 0), 'rev_tecnica_48': (f.get('rev_tecnica') or {}).get('mas48', 0), 'rev_tecnica_max': (f.get('rev_tecnica') or {}).get('max_dias', 0),
            'bloqueadas': len(bl), 'bloqueo_max': max((r['dias'] or 0 for r in bl), default=0),
            'no_planificadas': f.get('no_planificadas_semana', 0), 'no_planificadas_ant': f.get('no_planificadas_semana_ant', 0),
            'vencidas': f.get('vencidas', 0), 'sin_fecha': f.get('sin_fecha', 0),
            'creadas_mes': f.get('creadas_mes', 0), 'creadas_mes_ant': f.get('creadas_mes_ant', 0), 'sin_tareas_mes': bool(f.get('sin_tareas_mes')),
            'cerradas_semana': f.get('cerradas_semana', 0), 'cerradas_semana_ant': f.get('cerradas_semana_ant', 0),
            'horas_mes': round(hcli[cid], 1) if horas_disponibles and cid in hcli else None,
            'horas_mes_ant': round(hcli_ant[cid], 1) if horas_disponibles and cid in hcli_ant else None,
            'horas_medicion': {'estado': 'medido' if horas_disponibles and cid in hcli else 'sin_dato',
                'fuente': 'horas', 'periodo': HOY.strftime('%Y-%m'),
                'fecha': H.get('meta', {}).get('generado'), 'cobertura': 'parcial',
                'alcance': 'entradas_leidas', 'entradas_descartadas': horas_descartadas},
        })
    proyectos.sort(key=lambda r: (-(r['rev_account_48'] + r['rev_tecnica_48'] + r['bloqueadas']), r['cliente']))

    # trabajo no planificado por persona que crea (D-24: 3 o más por persona y semana)
    no_plan = []
    plan_sin_identidad = 0
    personas_unicas = {pid for pid in P if sum(p.get('id') == pid for p in personas_fuente) == 1}
    for quien, x in plan.items():
        if quien.startswith('_'):
            continue
        pid = x.get('persona_id') if isinstance(x, dict) else None
        if not isinstance(pid, str) or pid not in personas_unicas:
            plan_sin_identidad += 1
            continue
        no_plan.append({'persona_id': pid, 'semana': x['semana']['rompen'], 'semana_ant': x['semana_ant']['rompen'],
                        'creadas': x['semana']['creadas'], 'ejemplos': [{**e, 'tarea': limpiar_tarea(e.get('tarea'))} for e in x['semana']['ejemplos'][:3]]})

    plan_fecha = (plan.get('_meta') or {}).get('generado')
    try:
        plan_fecha_valida = isinstance(plan_fecha, str) and dt.datetime.fromisoformat(plan_fecha.replace('Z', '+00:00')).date() <= HOY
    except (ValueError, TypeError):
        plan_fecha_valida = False

    # ---- anuncios: índice frente a la media de su cuenta (sin euros) ----
    anuncios, resumen_anu = indices_anuncios(nombres, P)

    sello = T['meta']['generado']
    # R14 · sello único de frescura: cada fuente con su hora real, su nombre llano y su límite de horas (el mismo de
    # data/fuentes.json, que es el que usan los consejos y la cabecera: así nunca se contradicen).
    lim = {f.get('id'): f.get('limite_h') for f in (leer(DATA / 'fuentes.json', {}) or {}).get('fuentes', []) if isinstance(f, dict)}
    escribir(DATA / 'produccion/produccion.json', compacto=True, datos={
        'cobertura_identidad': {'fuente':identidad['fuente_identidad'], **identidad['conteos']},
        'no_planificado_cobertura': {'estado':'sin_dato' if plan_sin_identidad or not plan_fecha_valida else 'referencia_de_copia',
            'filas_sin_identidad':plan_sin_identidad, 'total_semana':None if plan_sin_identidad or not plan_fecha_valida else sum(f['semana'] for f in no_plan),
            'fecha':(plan.get('_meta') or {}).get('generado'), 'alcance':'filas_con_persona_id_explicito_unico'},
        'formato': 1, 'generado': AHORA.strftime('%Y-%m-%d %H:%M'), 'hoy': str(HOY), 'lunes': str(LUNES),
        'fuentes': {
            'tareas': {'fuente': 'ClickUp · tareas (llave propia)', 'nombre': 'Colas (tareas de ClickUp)', 'hora': sello, 'n': len(tareas), 'limite_h': lim.get('tareas') or 8},
            'horas': {'fuente': 'ClickUp · horas (llave propia)', 'nombre': 'Horas imputadas', 'hora': H.get('meta', {}).get('generado') if horas_disponibles else None, 'limite_h': lim.get('horas') or 3},
            'flujo': {'fuente': 'ClickUp · flujo por proyecto (cu.py del panel)', 'nombre': 'Revisiones y proyectos', 'hora': (flujo.get('_meta') or {}).get('generado'), 'limite_h': lim.get('tareas') or 8},
            'anuncios': {'fuente': 'Meta · anuncios por cuenta (M6)', 'nombre': 'Anuncios de Meta', 'hora': resumen_anu.get('hora'), 'limite_h': lim.get('meta') or 30},
        },
        'sin_asignar': sin_asignar,
        'cola': cola, 'personas': filas_p, 'proyectos': proyectos, 'revisiones': rev_cli, 'no_planificado': no_plan,
        'anuncios': anuncios, 'anuncios_resumen': resumen_anu,
        'definiciones': {
            'cola_ahora': {'grupos': list(GRUPOS_AHORA), 'texto': 'Tu cola ahora = vencidas + para hoy + esta semana + bloqueadas: lo que depende de ti. Lo que espera revisión de otro, lo de más adelante y lo olvidado (más de 30 días vencido) va aparte.'},
            'vencidas': 'Vencida = fecha límite pasada, en tu mano y sin entregar, hasta 30 días. Más de 30 días = olvidada.',
        },
        'notas': {
            'devueltas': 'Devuelta = está en un estado de trabajo (diario, en curso, planning semanal…) y antes pasó por una revisión (account, técnica, Mili, Tomás o cliente).',
            'a_la_primera': 'A la primera = pasó por revisión interna y después no volvió a un estado de trabajo. ClickUp da el tiempo total en cada estado, no cuántas veces se entra: una pieza devuelta dos veces cuenta como una. Para contar rondas exactas hace falta un estado «corrección» en ClickUp.',
            'entregas': 'Hitos operativos: primera revisión registrada o cierre con tipo done/closed verificado en la lista. No acreditan entrega aceptada ni éxito. En fecha compara ese hito con la fecha límite, sólo en tareas con fecha; últimos 30 días. Historial resumido y copia parcial.',
            'estados': {'fuente': 'ClickUp · catálogo de estados por lista', 'fecha': catalogo.get('leido'), 'texto': 'Un nombre no determina cierre. Sin catálogo exacto o ante contradicción, la tarea permanece no final y por contrastar.'},
            'anuncios': 'Índice = la pieza frente a la media de su misma cuenta (media = 100), 30 días, con más de 1.000 impresiones. Sin euros. Autor: iniciales en el nombre del anuncio.',
        },
    })
    print({'cola': len(cola), 'personas': len(filas_p), 'proyectos': len(proyectos), 'revisiones': len(rev_cli), 'anuncios': len(anuncios), 'sin_asignar': sin_asignar})


TORRE_A_APP = {'bit24': 'bit-24', 'musashi': 'musashi-consultores', 'aselegal': 'aselegal', 'gac': 'gac', 'ecom': 'ecom-advisory',
               'innova': 'innova-scala', 'ayg': 'ayg-asesores', 'consultingf': 'consulting-f', 'accompany': 'accompany',
               'busbac': 'busbac', 'kiosko': 'kiosko-box', 'gestanex': 'gestanex', 'akua': 'akua', 'orejana': 'orejana'}


def iniciales_equipo(P):
    out = {}
    for p in P.values():
        if not set(p.get('puestos') or []) & {'produccion', 'trafficker', 'jefa_publicidad', 'redes'}:
            continue
        partes = [x for x in re.split(r'\s+', re.sub(r'\(.*?\)', '', p.get('nombre') or '')) if x]
        if len(partes) >= 2:
            out.setdefault((partes[0][0] + partes[1][0]).upper(), p['id'])
    return out


def autor_de(nombre, inis):
    for tok in re.split(r'[\s_\-|·/\[\]()]+', nombre or ''):
        if re.fullmatch(r'[A-Z]{2}', tok) and tok in inis:
            return inis[tok]
    return None


def indices_anuncios(nombres, P):
    A = leer(APP / 'fuentes_captacion/anuncios.json', {}) or {}
    inis = iniciales_equipo(P)
    out, cuentas, con_autor = [], 0, 0
    for k, cta in (A.get('cuentas') or {}).items():
        cid = TORRE_A_APP.get(k) or k.replace('_', '-')
        if cid not in nombres:
            continue
        filas = [a for a in (cta.get('ventanas') or {}).get('30d', []) if (a.get('impresiones') or 0) >= 1000]
        if len(filas) < 1:
            continue
        cuentas += 1
        imp = sum(a['impresiones'] for a in filas); cl = sum(a['clics'] for a in filas)
        gasto = sum(a['gasto'] for a in filas); leads = sum(a['leads'] or 0 for a in filas)
        ctr_m = cl / imp if imp else None
        cpl_m = gasto / leads if leads else None
        for a in filas:
            ctr = a['clics'] / a['impresiones'] if a['impresiones'] else None
            cpl = a['gasto'] / a['leads'] if a.get('leads') else None
            i_ctr = round(ctr / ctr_m * 100) if (ctr is not None and ctr_m) else None
            i_cost = round(cpl_m / cpl * 100) if (cpl and cpl_m) else None
            partes = [x for x in (i_cost, i_ctr) if x is not None]
            indice = round(sum(partes) / len(partes)) if partes else None
            autor = autor_de(a['nombre'], inis)
            con_autor += 1 if autor else 0
            fila = {'cli': cid, 'cliente': nombres[cid], 'anuncio': limpiar(a['nombre'])[:80], 'campana': limpiar(a.get('campana'))[:60],
                    'indice': indice, 'indice_clics': i_ctr, 'indice_coste': i_cost, 'leads': a.get('leads') or 0,
                    'impresiones': a['impresiones'], 'frecuencia': a.get('frecuencia'),
                    'estado': None if indice is None else 'verde' if indice >= 100 else 'ambar' if indice >= 80 else 'rojo'}
            if autor:
                fila['persona_id'] = autor
            else:
                fila['cliente_id'] = cid
            out.append(fila)
    out.sort(key=lambda r: (r['cliente'], -(r['indice'] or 0)))
    return out, {'hora': A.get('generado'), 'cuentas': cuentas, 'anuncios': len(out), 'con_autor': con_autor,
                 'iniciales': {v: k for k, v in inis.items()}}


if __name__ == '__main__':
    main()

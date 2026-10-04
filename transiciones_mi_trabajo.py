"""Proyección local de transición: sin proveedores, escrituras ni permisos propios."""
import hashlib
import json
import sqlite3
import os
from datetime import datetime, timezone


def compatible(con):
    return isinstance(con, sqlite3.Connection)


def capacidad(con, real, vista):
    """Declaración honesta de escritura local; jamás habilita un proveedor."""
    from piloto_lectura import activo as piloto_activo
    motivo = None
    if piloto_activo():
        motivo = 'piloto_solo_lectura'
    elif not isinstance(real, dict) or not isinstance(vista, dict) or not real.get('id') or real.get('id') != vista.get('id'):
        motivo = 'ver_como'
    elif not compatible(con) or os.environ.get('DATABASE_URL'):
        motivo = 'base_no_validada'
    elif con.execute('PRAGMA query_only').fetchone()[0]:
        motivo = 'base_solo_lectura'
    return {'version': '191.1', 'activo': motivo is None, 'motivo': motivo}


def instante_utc(valor, *, registro=False):
    if not isinstance(valor, str):
        return None
    try:
        if registro:
            return datetime.strptime(valor, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
        d = datetime.fromisoformat(valor.replace('Z', '+00:00'))
        return d.astimezone(timezone.utc) if d.tzinfo is not None else None
    except ValueError:
        return None


def tarea_unica(D, tid, filas=None):
    filas = filas if filas is not None else [r for r in D.get('tareas') or [] if isinstance(r, dict) and r.get('id') == tid]
    if not filas or any('cli' not in r for r in filas):
        raise ValueError('Tarea sin identidad confirmada')
    identidades = {(r.get('cli'), r.get('lista_id'), r.get('estado')) for r in filas}
    personas = [r.get('persona_id') for r in filas]
    if len(identidades) != 1 or len(set(personas)) != len(personas) or any(not isinstance(p, str) or not p for p in personas):
        raise ValueError('Tarea ambigua')
    r = filas[0]
    if not isinstance(r.get('lista_id'), str) or not r['lista_id'] or not isinstance(r.get('estado'), str):
        raise ValueError('Lista o estado desconocido')
    return r


def catalogo(D, lista):
    filas = (D.get('estados_detalle') or {}).get(lista)
    nombres = (D.get('estados_lista') or {}).get(lista)
    if not isinstance(filas, list) or not filas or not isinstance(nombres, list):
        raise ValueError('Catálogo desconocido')
    tipos = {}
    for f in filas:
        if not isinstance(f, dict) or not isinstance(f.get('estado'), str) or not f['estado'] or f.get('tipo') not in ('open', 'unstarted', 'custom', 'done', 'closed') or f['estado'] in tipos:
            raise ValueError('Catálogo ambiguo')
        tipos[f['estado']] = f['tipo']
    if len(nombres) != len(set(nombres)) or set(nombres) != set(tipos):
        raise ValueError('Catálogos incoherentes')
    return tipos


def preparar_lectura(D, con, tids, filas_tarea=None):
    """Índices efímeros de UNA petición; lectura SQL acotada al scope recibido."""
    filas = filas_tarea
    if filas is None:
        filas = {}
        for r in D.get('tareas') or []:
            if isinstance(r, dict) and isinstance(r.get('id'), str):
                filas.setdefault(r['id'], []).append(r)
    tablas = {x[0] for x in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    resultado = {'filas': filas, 'catalogos': {}, 'acciones': {}, 'cambios': {}, 'pasos': {}}
    for lista in {r.get('lista_id') for tid in tids for r in filas.get(tid, []) if isinstance(r.get('lista_id'), str)}:
        try:
            resultado['catalogos'][lista] = catalogo(D, lista)
        except (ValueError, TypeError):
            resultado['catalogos'][lista] = None
    ids = sorted(tids)
    for inicio in range(0, len(ids), 400):
        bloque = ids[inicio:inicio+400]
        marcas = ','.join('?' for _ in bloque)
        if 'acciones' in tablas:
            for x in con.execute("SELECT id,tipo,vista_previa,objeto FROM acciones WHERE herramienta='clickup' AND objeto IN ("+marcas+") ORDER BY id", bloque):
                resultado['acciones'].setdefault(x['objeto'], []).append(dict(x))
        if 'sinc_cambios' in tablas:
            for x in con.execute("SELECT id,accion_id,cambio,objeto_ref FROM sinc_cambios WHERE canal='clickup' AND objeto_ref IN ("+marcas+") ORDER BY id", bloque):
                resultado['cambios'].setdefault(x['objeto_ref'], []).append(dict(x))
    cambios_ids = [x['id'] for cs in resultado['cambios'].values() for x in cs]
    if 'sinc_pasos' in tablas:
        for inicio in range(0, len(cambios_ids), 400):
            bloque = cambios_ids[inicio:inicio+400]
            marcas = ','.join('?' for _ in bloque)
            for x in con.execute("SELECT id,cambio_id,estado,hora,evento FROM sinc_pasos WHERE cambio_id IN ("+marcas+") AND evento NOT IN ('aviso','reintento_simulado','espera') ORDER BY id", bloque):
                p = dict(x);p.pop('cambio_id')
                resultado['pasos'][x['cambio_id']] = p
    return resultado


def proyectar(D, tid, con, indices=None):
    filas_tarea = indices['filas'].get(tid, []) if indices is not None else None
    r = tarea_unica(D, tid, filas_tarea)
    filas_tarea = filas_tarea if filas_tarea is not None else [x for x in D.get('tareas') or [] if isinstance(x, dict) and x.get('id') == tid]
    tipos = indices['catalogos'].get(r['lista_id']) if indices is not None else catalogo(D, r['lista_id'])
    if tipos is None:
        raise ValueError('Catálogo no confirmado')
    if r['estado'] not in tipos:
        raise ValueError('Estado de copia fuera de catálogo')
    tablas = {x[0] for x in con.execute("SELECT name FROM sqlite_master WHERE type='table'")} if indices is None else set()
    acciones = indices['acciones'].get(tid, []) if indices is not None else [dict(x) for x in con.execute("SELECT id,tipo,vista_previa FROM acciones WHERE herramienta='clickup' AND objeto=? ORDER BY id", (tid,))] if 'acciones' in tablas else []
    cambios = indices['cambios'].get(tid, []) if indices is not None else [dict(x) for x in con.execute('SELECT id,accion_id,cambio FROM sinc_cambios WHERE canal=\'clickup\' AND objeto_ref=? ORDER BY id', (tid,))] if 'sinc_cambios' in tablas else []
    mapa = {x['accion_id']: x for x in cambios if x['accion_id'] is not None}
    huellas, estado, bloqueada = [], r['estado'], False
    for a in acciones:
        if a['tipo'] not in ('cambiar_estado', 'marcar_hecha', 'pieza_aprobar', 'pieza_pedir_cambios', 'mover_tarea', 'mover_estado'):
            continue
        c = mapa.get(a['id'])
        paso = indices['pasos'].get(c['id']) if c and indices is not None else None
        if indices is None and c and 'sinc_pasos' in tablas:
            p = con.execute("SELECT id,estado,hora,evento FROM sinc_pasos WHERE cambio_id=? AND evento NOT IN ('aviso','reintento_simulado','espera') ORDER BY id DESC LIMIT 1", (c['id'],)).fetchone()
            paso = dict(p) if p else None
        vp = json.loads(a['vista_previa'] or '{}')
        cam = json.loads(c['cambio']) if c else {}
        destino = cam.get('valor') if cam.get('campo') == 'estado' else vp.get('a') if a['tipo'] == 'cambiar_estado' and isinstance(vp, dict) else None
        huellas.append([a['id'], a['tipo'], a['vista_previa'], c and c['id'], c and c['cambio'], paso])
        status = (paso or {}).get('estado')
        if status == 'descartado':
            continue
        if status == 'confirmado':
            estado = r['estado']  # La copia observada prevalece sobre capas anteriores.
            # Generado sólo fecha una regeneración local: no prueba lectura de ClickUp.
            lecturas = [instante_utc(x.get('estado_leido_utc')) if x.get('estado_fuente') == 'clickup' else None
                        for x in filas_tarea]
            verificado = instante_utc((paso or {}).get('hora'), registro=True)
            if not verificado or any(x is None or x <= verificado for x in lecturas) or (paso or {}).get('evento') == 'hecho_a_mano':
                bloqueada = True
            continue  # Nunca reescribir una copia fresca con una transición antigua.
        if (c and status not in ('simulado', 'pendiente', 'enviado', 'confirmado')) or destino not in tipos:
            bloqueada = True
        else:
            estado = destino  # Incluye acción duradera aún no proyectada a SINC.
    if any(c['accion_id'] is None or c['accion_id'] not in {a['id'] for a in acciones} for c in cambios if json.loads(c['cambio']).get('campo') == 'estado'):
        bloqueada = True  # Cola de otra puerta sin recibo de acción vinculable.
    base = [D.get('generado'), sorted((x.get('persona_id'), x.get('cli'), x.get('lista_id'), x.get('estado'), x.get('estado_fuente'), x.get('estado_leido_utc')) for x in filas_tarea), sorted(tipos.items()), huellas, bloqueada]
    revision = hashlib.sha256(json.dumps(base, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    return {'lista_id': r['lista_id'], 'expected_estado': estado, 'revision': revision, 'bloqueada': bloqueada}

#!/usr/bin/env python3
"""generar_mi_trabajo.py · «Mi trabajo» (3-oct-2026) → data/mi_trabajo/mi_trabajo.json. SOLO LECTURA.

Encargo de Tomás: que el equipo deje de usar ClickUp en el día a día y trabaje desde la app. Este generador NO llama a
ClickUp: lee lo que ya bajó extraer_clickup.py (llave propia, solo lectura) y lo que ya calculó Producción.

Lee: data/produccion/produccion.json (la cola de cada persona: misma regla de grupos que Producción y Mi día),
     fuentes_produccion/_privado/_cache/tareas.json y horas.json (quién pidió cada tarea, estimación, horas gastadas,
     estados de cada lista y las horas de cada persona por día), data/personas.json, data/asignaciones.json.
Escribe (recorte en servir.py, contrato de E0: filas con persona_id → la persona, su jefe, operaciones, RRHH y dirección):
  tareas[]          una fila por persona y tarea (la cola de Producción + lo de «planning mensual» o «backlog» que vence
                    este mes, para la vista Mes), con «pidio» (quien la creó), «est_h», «horas_t» y «lista_id».
                    El cliente va en «cli» (no en cliente_id), como en Producción: una persona de producción ve sus tareas
                    aunque no lleve el cliente.
  estados_lista{}   lista de ClickUp → estados que se han visto en ella (los únicos a los que se puede mover desde la app).
  horas_dia[]       persona → día (en SU zona) → horas de ClickUp de los últimos 35 días (sin el cronómetro olvidado > 10 h,
                    que va aparte en «largas»). «marcas» = huellas «ro:…» de horas que nacieron en la app (idempotencia).
  jornada[]         horas del mes (personas.json), días laborables del mes en su zona y horas por día.
  raras_estimacion[] tareas suyas con más del doble de lo estimado.
  raras_cliente_n[] horas en una tarea que no es suya de un cliente que no es de su cartera (sin el cliente: lo ve RRHH).
  raras_cliente[]   lo mismo con cliente_id (solo quien ve ese cliente).
Sin euros ni sueldos.
"""
import re
import sys
import datetime as dt
from collections import defaultdict
from pathlib import Path
from zoneinfo import ZoneInfo

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent / 'fuentes_produccion'))
sys.path.insert(0, str(AQUI.parent))
from comun_equipo import (leer, escribir, personas, miembros_clickup, fecha_ms, dias_lab,  # noqa: E402
                          limpiar, DATA, CACHE, HOY, AHORA)
from inventario_tareas import catalogo_listas, extras as extras_inventario
from lectura_estado_196 import sello_copia
from contexto_tarea import contexto_operativo  # noqa: E402
from permisos import sin_importes  # noqa: E402

from identidad_generadores_212 import identidades, clientes_directos

DIAS = 35
MARCA = re.compile(r'ro:[0-9a-f]{10}')
NO_COLA = {'backlog', 'planning mensual'}
FINALES = {'completado', 'complete', 'cerrado', 'closed', 'done', 'finalizado', 'hecho'}
PRIO = {'urgent': 1, 'high': 2, 'normal': 3, 'low': 4}
ORDEN_ESTADO = ['backlog', 'planning mensual', 'próximo sprint', 'planning semanal', 'diario', 'en curso', 'corrección', 'bloqueado',
                'revisión técnica', 'revisión project manager', 'revisión mili', 'revisión tomás', 'enviar  cliente', 'revisión cliente',
                'ver cliente', 'campaña en curso', 'complete']


def zona_de(p):
    try:
        return ZoneInfo(p.get('zona') or 'Europe/Madrid')
    except Exception:
        return ZoneInfo('Europe/Madrid')


def fin_de_mes(d):
    return (d.replace(day=28) + dt.timedelta(days=4)).replace(day=1)


def main():
    PR = leer(DATA / 'produccion/produccion.json')
    T = leer(CACHE / 'tareas.json')
    H = leer(CACHE / 'horas.json', {'entradas': []}) or {'entradas': []}
    if not PR or not T:
        raise SystemExit('Faltan data/produccion/produccion.json o la caché de ClickUp: lanza antes fuentes_produccion/extraer_clickup.py y generar_produccion.py')
    personas_fuente = personas()
    P = {p['id']: p for p in personas_fuente}
    identidad = identidades(personas_fuente, miembros_clickup())
    U = identidad['por_usuario']
    por_carpeta, nombres = clientes_directos(DATA)
    asig = leer(DATA / 'asignaciones.json', [])
    asig = asig if isinstance(asig, list) else asig.get('asignaciones', [])
    cartera = defaultdict(set)
    for a in asig:
        if not a.get('hasta'):
            cartera[a['persona_id']].add(a['cliente_id'])

    # un jefe «lleva» también los clientes de su gente; quien responde de todos (dirección, operaciones, proyectos, RRHH,
    # técnica de altas) no entra en la regla «cliente que no es suyo»
    for pid, p in P.items():
        for sub, q in P.items():
            if q.get('jefe') == pid:
                cartera[pid] |= cartera.get(sub, set())
    TODOS = {'direccion', 'operaciones', 'proyectos', 'rrhh', 'tecnico_altas'}
    responde_de_todos = {pid for pid, p in P.items() if set(p.get('puestos') or []) & TODOS}
    por_id = {t['id']: t for t in T['tareas']}
    # ---- horas gastadas por tarea (todo el equipo) ----
    horas_t = defaultdict(float)
    for e in H.get('entradas', []):
        if e.get('task_id') and 0 < (e.get('horas') or 0) <= 10:
            horas_t[e['task_id']] += e['horas']

    # Catálogo contractual de estados de la lista; nunca inferido de tareas/historial.
    catalogo = leer(CACHE / 'estados_listas.json', {}) or {}
    estados, estados_detalle = catalogo_listas(catalogo)

    def extra_de(tid, pid):
        t = por_id.get(tid) or {}
        pidio = U.get(str(t.get('creador') or ''))
        est = t.get('estimacion_ms')
        return {**contexto_operativo(t), 'pidio': pidio if pidio != pid else 'yo' if pidio else None,
                'est_h': round(int(est) / 3600000, 2) if est else None,
                'horas_t': round(horas_t.get(tid, 0), 2) or None,
                'lista_id': t.get('lista_id') or None, 'lista':sin_importes(limpiar(t.get('lista')))[:120],
                'carpeta_id':t.get('carpeta_id'), 'carpeta':sin_importes(limpiar(t.get('carpeta')))[:120],
                'espacio':sin_importes(limpiar(t.get('espacio')))[:120], 'prioridad':t.get('prioridad'),
                'etiquetas':[sin_importes(limpiar(x))[:80] for x in t.get('etiquetas') or [] if isinstance(x,str)],
                'padre':t.get('padre'), 'tipo_estado':t.get('tipo_estado'),
                'creada': str(fecha_ms(t['creada']).date()) if t.get('creada') else None}

    tareas, vistas = [], set()
    for r in PR.get('cola') or []:
        if not isinstance(r, dict) or not r.get('persona_id'):
            continue
        fila = {k: r.get(k) for k in ('persona_id', 'id', 'tarea', 'cli', 'cliente', 'estado', 'grupo', 'prio_n', 'vence', 'vencida', 'devuelta', 'comparte')}
        fila.update(extra_de(r['id'], r['persona_id']))
        tareas.append(fila)
        vistas.add((r['persona_id'], r['id']))

    adicionales = extras_inventario(T['tareas'], vistas, U, por_carpeta, nombres, HOY, fecha_ms,
                                  lambda texto: sin_importes(limpiar(texto)), extra_de, PRIO)
    tareas.extend(adicionales)
    extras = len(adicionales)
    #196: sólo evidencia de la extracción real, y únicamente del mismo estado.
    ahora_estado_utc = dt.datetime.now(dt.timezone.utc).isoformat()
    for f in tareas:
        f.update(sello_copia(por_id.get(f['id']), f.get('estado'), ahora_estado_utc))
    # Inventario privado completo conocido, incluyendo sin responsable. Nunca se sirve como fichero.
    inventario = {}
    for f in tareas:
        x = inventario.setdefault(f['id'], {k:v for k,v in f.items() if k != 'persona_id'})
        x.setdefault('asignados', []).append(f['persona_id'])
    for t in T['tareas']:
        if t['id'] in inventario:
            continue
        li = por_carpeta.get(str(t.get('carpeta_id') or ''))
        vence = fecha_ms(t.get('vence'))
        vence = vence.date() if vence else None
        from inventario_tareas import grupo
        inventario[t['id']] = {'id':t['id'],'tarea':sin_importes(limpiar(t.get('nombre')))[:120],
            'cli':li[0] if li else None,'cliente':li[1] if li else 'Personal','estado':t.get('estado'),
            'tipo_estado':t.get('tipo_estado'),'grupo':grupo(t,vence,HOY),'vence':str(vence) if vence else None,
            'asignados':[],'padre':t.get('padre'),'cerrada':t.get('cerrada'),**extra_de(t['id'],None),
            **sello_copia(t,t.get('estado'),ahora_estado_utc)}
    for t in T['tareas']:
        x=inventario[t['id']]
        x['_usuarios_asignados']=[str(a['id']) for a in t.get('asignados') or []]
        x['asignados_sin_identidad']=sum(not U.get(str(a['id'])) for a in t.get('asignados') or [])

    #212: el mismo contrato único para lectura y referencias de destinatario.
    usuarios_personas = identidad['usuario_unico_por_persona']
    escribir(CACHE / 'tablero_tareas.json', datos={'generado':AHORA.isoformat(),'tareas':list(inventario.values()),'usuarios_personas':usuarios_personas,
        'cobertura_identidad': {'fuente':identidad['fuente_identidad'], **identidad['conteos']},
        'cobertura':(T.get('meta') or {}).get('cobertura') or {'completa':False,'nota':'Caché anterior: no garantiza histórico completo ni archivadas.'}})
    usadas = {f['lista_id'] for f in tareas if f.get('lista_id')}
    estados_lista = {lid: estados[lid] for lid in usadas if lid in estados}
    detalle_lista = {lid: estados_detalle[lid] for lid in usadas if lid in estados_detalle}

    # ---- horas por persona y día en SU zona (últimos 35 días) ----
    desde = HOY - dt.timedelta(days=DIAS)
    hdia = defaultdict(lambda: defaultdict(float))
    marcas = defaultdict(list)
    largas = []
    cli_n, cli_d = [], []
    asignados_de = {t['id']: {U.get(str(a['id'])) for a in t.get('asignados') or []} for t in T['tareas']}
    for e in H.get('entradas', []):
        pid = U.get(str(e['usuario_id']))
        if not pid or pid not in P:
            continue
        try:
            dl = dt.datetime.fromisoformat(e['inicio']).astimezone(zona_de(P[pid])).date()
        except ValueError:
            continue
        if dl < desde:
            continue
        m = MARCA.search(e.get('descripcion') or '') or MARCA.search(e.get('marca_ro') or '')
        if m:
            marcas[pid].append(m.group(0))
        if (e.get('horas') or 0) > 10:
            largas.append({'persona_id': pid, 'dia': str(dl), 'horas': round(e['horas'], 1), 'tarea_id': e.get('task_id')})
            continue
        hdia[pid][str(dl)] += e.get('horas') or 0
        # cliente que no es suyo: la tarea no es suya y el cliente no está en su cartera (en ninguna silla)
        cli = por_carpeta.get(str(e.get('carpeta_id') or ''))
        tid = e.get('task_id')
        if cli and tid and pid not in responde_de_todos and pid not in asignados_de.get(tid, set()) and cli[0] not in cartera.get(pid, set()) and dl >= HOY - dt.timedelta(days=14):
            cli_n.append({'persona_id': pid, 'dia': str(dl), 'horas': round(e['horas'], 2), 'tarea_id': tid})
            cli_d.append({'persona_id': pid, 'dia': str(dl), 'horas': round(e['horas'], 2), 'tarea_id': tid, 'cliente_id': cli[0]})

    horas_dia = [{'persona_id': pid, 'dias': {d: round(v, 2) for d, v in sorted(x.items())}, 'marcas': sorted(set(marcas.get(pid, [])))}
                 for pid, x in hdia.items()]
    for pid in marcas:
        if pid not in hdia:
            horas_dia.append({'persona_id': pid, 'dias': {}, 'marcas': sorted(set(marcas[pid]))})

    # ---- jornada: horas del mes / días laborables del mes en su zona ----
    jornada = []
    for pid, p in P.items():
        if p.get('estado') == 'baja' or p.get('imputa_horas') != 'sí' or 'setters' in (p.get('puestos') or []):
            continue
        hoy_l = AHORA.astimezone(zona_de(p)).date()
        m1 = hoy_l.replace(day=1)
        lab = dias_lab(m1, fin_de_mes(hoy_l))
        hm = p.get('horas_mes') or 128
        jornada.append({'persona_id': pid, 'horas_mes': hm, 'dias_lab_mes': lab, 'horas_dia': round(hm / lab, 2) if lab else None,
                        'zona': p.get('zona') or 'Europe/Madrid', 'desde': p.get('fecha_ingreso')})

    # ---- tareas con más del doble de lo estimado ----
    raras_est = []
    for f in tareas:
        if f.get('est_h') and f.get('horas_t') and f['horas_t'] > 2 * f['est_h']:
            raras_est.append({'persona_id': f['persona_id'], 'tarea_id': f['id'], 'tarea': f['tarea'], 'est_h': f['est_h'], 'horas_t': f['horas_t']})

    escribir(DATA / 'mi_trabajo/mi_trabajo.json', compacto=True, datos={
        'cobertura_identidad': {'fuente':identidad['fuente_identidad'], **identidad['conteos']},
        'formato': 1, 'generado': AHORA.strftime('%Y-%m-%d %H:%M'), 'hoy': str(HOY),
        'fuentes': {'tareas': {'nombre': 'Tareas de ClickUp', 'hora': (T.get('meta') or {}).get('generado'), 'limite_h': 8},
                    'horas': {'nombre': 'Horas de ClickUp', 'hora': (H.get('meta') or {}).get('generado'), 'limite_h': 8},
                    'produccion': {'nombre': 'Colas de Producción', 'hora': PR.get('generado')}},
        'tareas': tareas, 'estados_lista': estados_lista, 'estados_detalle': detalle_lista,
        'cobertura_tareas': (T.get('meta') or {}).get('cobertura') or {'completa': False, 'nota': 'Caché anterior: abiertas y cerradas recientes; no confirma histórico completo ni archivadas.'},
        'cobertura_estados': catalogo.get('cobertura') or {'completa': False, 'nota': 'Sin catálogo leído de listas; no se permite inventar estados.'}, 'horas_dia': horas_dia, 'largas': largas, 'jornada': jornada,
        'raras_estimacion': raras_est, 'raras_cliente_n': cli_n, 'raras_cliente': cli_d,
        'notas': {
            'grupos': 'Cola de Producción más todas las tareas asignadas conocidas de la caché, incluyendo backlog, sin fecha, futuras y completadas. La cobertura se informa por separado.',
            'jornada': 'Horas de jornada = horas del mes de su ficha / días laborables (lunes a viernes) del mes en su zona. Todavía no se descuentan festivos ni ausencias.',
            'estados': 'Solo estados del catálogo real leído de cada lista; si falta, el cambio de estado queda bloqueado.',
        },
    })
    print({'tareas': len(tareas), 'extras_mes': extras, 'listas': len(estados_lista), 'personas_con_horas': len(horas_dia), 'estimacion': len(raras_est), 'cliente_no_suyo': len(cli_n)})


if __name__ == '__main__':
    main()

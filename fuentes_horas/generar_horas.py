#!/usr/bin/env python3
"""generar_horas.py · M11 Horas y productividad (puntos 4 y 5 de Mili) → data/horas/horas.json. SOLO LECTURA.

Lee: fuentes_produccion/_cache/horas.json y tareas.json (extraer_clickup.py, llave propia de ClickUp),
     PANEL_OPERACIONES_2026-10-01/build/datos.json → v7.anomalias (detector de horas raras de build.py),
     data/personas.json.
Reglas: horas esperadas = 128 h al mes menos ausencias (D-25; hoy no hay tabla de ausencias: 0), prorrateadas por
días laborables en el mes en curso. Sello «horas incompletas» (D-27): solo aviso. Productividad = tareas que
ENTRARON en «revisión project manager», «revisión cliente», «ver cliente» o completado en el mes, frente a horas;
cada uno se compara consigo mismo (mediana de sus 3 meses anteriores) y con su mismo tipo de tarea; nunca ranking.
Recorte (servir.py): filas con persona_id → la persona, su jefe, operaciones, RRHH y dirección. El cliente no sale
en las filas de persona (RRHH ve horas por persona y tipo de tarea; el cliente, solo en agregado, D-84): las horas
raras llevan el nombre de la tarea sin el cliente, y el cliente va aparte en «raras_cliente» con cliente_id.
Sin sueldos ni euros.
"""
import sys, re, json, statistics, datetime as dt
from zoneinfo import ZoneInfo
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'fuentes_produccion'))
from comun_equipo import (leer, escribir, personas, mapa_usuarios, miembros_clickup, clientes_app, fecha_ms, norm, dias_lab,
                          tipo_tarea, sin_cliente, nombre_mes, limpiar, DATA, CACHE, PANEL, HOY, AHORA, ESTADOS_PRODUCTIVOS)

from fuentes_horas.diario_238 import construir_diarios

HORAS_MES = 128  # D-25
CONTENEDOR = re.compile(r'reuni|daily|dailys|siempre|semanal|mensual|recurrent|formaci|gestion general|gestion de equipo|organizaci|tareas (agosto|septiembre|octubre)')
JEFAS = {'operaciones', 'proyectos', 'rrhh', 'jefa_publicidad', 'jefa_seo', 'jefa_crm', 'direccion'}
NOMBRE_PUESTO = {'account': 'Accounts', 'tecnico_altas': 'Técnica de altas', 'trafficker': 'Publicidad', 'especialista_ghl': 'CRM', 'outreach': 'Outreach',
                 'seo': 'SEO', 'ficha_google': 'SEO', 'web': 'Web', 'redes': 'Redes', 'produccion': 'Producción creativa',
                 'operaciones': 'Jefes y coordinación', 'proyectos': 'Jefes y coordinación', 'rrhh': 'Jefes y coordinación',
                 'jefa_publicidad': 'Jefes y coordinación', 'jefa_seo': 'Jefes y coordinación', 'jefa_crm': 'Jefes y coordinación'}


def meses_atras(n):
    m, out = HOY.replace(day=1), []
    for _ in range(n):
        out.append(m.strftime('%Y-%m'))
        m = (m - dt.timedelta(days=1)).replace(day=1)
    return list(reversed(out))


def lab_del_mes(mes):
    a = dt.date.fromisoformat(mes + '-01')
    b = (a + dt.timedelta(days=32)).replace(day=1)
    total = dias_lab(a, b)
    if mes == HOY.strftime('%Y-%m'):
        return total, dias_lab(a, HOY)  # hasta ayer: hoy aún no ha terminado
    return total, total


def main():
    H = leer(CACHE / 'horas.json')
    T = leer(CACHE / 'tareas.json')
    if not H or not T:
        raise SystemExit('Faltan los ficheros de fuentes_produccion/_cache: lanza  python3 ../fuentes_produccion/extraer_clickup.py')
    personas_fuente = personas()
    diarios_238 = construir_diarios(H, personas_fuente, miembros_clickup(), str(HOY))
    P = {p['id']: p for p in personas_fuente}
    U = mapa_usuarios(miembros_clickup())
    por_carpeta, nombres = clientes_app()
    MESES = meses_atras(7)  # 6 meses cerrados + el actual
    MES = MESES[-1]
    ayer = HOY - dt.timedelta(days=1)
    while ayer.weekday() >= 5:
        ayer -= dt.timedelta(days=1)
    lunes = HOY - dt.timedelta(days=HOY.weekday())
    # zona de cada persona: decide el DÍA de trabajo de cada registro (el mes y los totales, en Madrid)
    Z = json.loads((Path(__file__).resolve().parent / 'zonas.json').read_text())
    def zona(pid):
        z = (P.get(pid) or {}).get('zona') or (Z.get(pid) or {}).get('zona') or Z['_por_defecto']
        return ZoneInfo(z)
    def zona_txt(pid):
        if (P.get(pid) or {}).get('zona'):
            return {'zona': P[pid]['zona'], 'fuente': 'personas.json'}
        return {'zona': (Z.get(pid) or {}).get('zona') or Z['_por_defecto'], 'fuente': (Z.get(pid) or {}).get('fuente') or 'supuesta'}
    def dias_persona(pid):
        hoy_l = AHORA.astimezone(zona(pid)).date()
        ay = hoy_l - dt.timedelta(days=1)
        while ay.weekday() >= 5:
            ay -= dt.timedelta(days=1)
        return hoy_l, ay, hoy_l - dt.timedelta(days=hoy_l.weekday())
    hdia_mad = defaultdict(lambda: defaultdict(float))  # persona → día en Madrid (solo para el mes en curso)
    cambian_dia = 0

    # ---------------- horas ----------------
    hm = defaultdict(lambda: defaultdict(float))        # persona → mes → horas
    hdia = defaultdict(lambda: defaultdict(float))      # persona → día → horas
    htipo = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))  # persona → mes → tipo → horas
    hsin = defaultdict(lambda: defaultdict(float))      # persona → mes → horas sin tarea
    htask = defaultdict(lambda: defaultdict(float))     # persona → task_id → horas (para productividad)
    primera = {}
    descartadas = 0
    for e in H['entradas']:
        p = U.get(str(e['usuario_id']))
        if not p:
            continue
        if e['horas'] > 10:  # cronómetro olvidado: fuera de la suma (sale en horas raras)
            descartadas += 1
            continue
        d = dt.date.fromisoformat(e['inicio'][:10])          # día en Madrid (ClickUp se extrae en hora de Madrid)
        m = d.strftime('%Y-%m')                               # el mes se queda en Madrid: totales iguales a ClickUp
        dl = dt.datetime.fromisoformat(e['inicio']).astimezone(zona(p)).date()  # día de trabajo en su zona
        cambian_dia += 1 if dl != d else 0
        hm[p][m] += e['horas']
        hdia[p][str(dl)] += e['horas']
        hdia_mad[p][str(d)] += e['horas']
        tt = 'sin tarea' if not e.get('task_id') else tipo_tarea(e.get('tarea'))
        htipo[p][m][tt] += e['horas']
        if not e.get('task_id'):
            hsin[p][m] += e['horas']
        else:
            htask[p][e['task_id']] += e['horas']
        primera[p] = min(primera.get(p, m), m)

    # ---------------- productividad: tareas que entran en un estado «productivo» por mes ----------------
    tarea_info = {}
    entradas_prod = defaultdict(lambda: defaultdict(list))  # persona → mes → [task_id]
    for t in T['tareas']:
        if CONTENEDOR.search(norm(t.get('nombre'))):
            continue
        hist = {x['estado']: fecha_ms(x['desde']) for x in t.get('historial') or [] if x.get('desde') and x.get('estado')}
        cands = [v for k, v in hist.items() if k in ESTADOS_PRODUCTIVOS]
        if (t.get('tipo_estado') in ('closed', 'done')) and t.get('cerrada'):
            cands.append(fecha_ms(t['cerrada']))
        if not cands:
            continue
        m = min(cands).strftime('%Y-%m')
        if m not in MESES:
            continue
        tarea_info[t['id']] = {'tipo': tipo_tarea(t.get('nombre')), 'mes': m}
        for a in t.get('asignados') or []:
            p = U.get(str(a['id']))
            if p:
                entradas_prod[p][m].append(t['id'])

    # mediana del equipo por tipo de tarea: horas que costó cada tarea resuelta (con horas imputadas)
    por_tipo = defaultdict(list)
    for p, xs in entradas_prod.items():
        for m, ids in xs.items():
            for tid in ids:
                hh = htask[p].get(tid, 0)
                if hh > 0:
                    por_tipo[tarea_info[tid]['tipo']].append(hh)
    med_tipo = {k: {'mediana_h': round(statistics.median(v), 2), 'casos': len(v)} for k, v in por_tipo.items() if len(v) >= 5}

    # ---------------- filas por persona ----------------
    filas, raras_out, raras_cli = [], [], []
    total_imp = total_esp = 0
    for pid, p in P.items():
        puestos = p.get('puestos') or []
        if p.get('estado') == 'baja' or 'setters' in puestos or p.get('imputa_horas') == 'no' or pid in ('tomas', 'sofia'):
            continue
        hoy_p, ayer_p, lunes_p = dias_persona(pid)
        principal = p.get('puesto_principal') or (puestos[0] if puestos else '')
        grupo = 'Accounts' if principal == 'account' else 'Jefes y coordinación' if principal in JEFAS else 'Especialistas'
        meses = []
        for m in MESES:
            tot, hechos = lab_del_mes(m)
            esperadas = round(HORAS_MES * hechos / tot, 1) if tot else HORAS_MES
            ausencias = 0
            esperadas -= ausencias
            # en el mes en curso, hasta ayer (hoy no ha terminado): igual que las esperadas
            imp = round(sum(h for f, h in hdia_mad[pid].items() if f.startswith(m) and f < str(HOY)), 1) if m == MES else round(hm[pid].get(m, 0), 1)
            antes = primera.get(pid) is not None and m < primera[pid] and m < MES
            # días laborables sin imputar (hasta ayer)
            a = dt.date.fromisoformat(m + '-01'); b = min((a + dt.timedelta(days=32)).replace(day=1), hoy_p)
            sin_imp, d = [], a
            while d < b:
                if d.weekday() < 5 and hdia[pid].get(str(d), 0) < 0.25:
                    sin_imp.append(str(d))
                d += dt.timedelta(days=1)
            prod = entradas_prod[pid].get(m, [])
            h_en_prod = round(sum(htask[pid].get(t, 0) for t in prod), 1)
            tipos = sorted(htipo[pid][m].items(), key=lambda x: -x[1])
            meses.append({
                'mes': m, 'nombre_mes': nombre_mes(m), 'en_curso': m == MES, 'antes_de_imputar': antes,
                'imputadas': imp, 'esperadas': esperadas, 'ausencias': ausencias,
                'pct': None if antes or not esperadas else round(imp / esperadas * 100),
                'dias_lab': hechos, 'dias_sin_imputar': None if antes else len(sin_imp), 'fechas_sin_imputar': [] if antes else sin_imp[-12:],
                'sin_tarea_h': round(hsin[pid].get(m, 0), 1),
                'tareas': len(prod), 'horas_por_tarea': round(imp / len(prod), 1) if prod and imp else None,
                'horas_en_tareas_resueltas': h_en_prod,
                'tipos': [{'tipo': k, 'horas': round(v, 1)} for k, v in tipos[:8]],
            })
            if m != MES and not antes:
                total_imp += imp; total_esp += esperadas
        # su mediana de los 3 meses anteriores al último cerrado y al actual
        for i, x in enumerate(meses):
            prev = [y['horas_por_tarea'] for y in meses[max(0, i - 3):i] if y['horas_por_tarea']]
            x['mediana_propia'] = round(statistics.median(prev), 1) if len(prev) >= 2 else None
            x['desvio_pct'] = round((x['horas_por_tarea'] / x['mediana_propia'] - 1) * 100) if (x['horas_por_tarea'] and x['mediana_propia']) else None
            x['desvio'] = x['desvio_pct'] is not None and abs(x['desvio_pct']) > 50
        # por tipo de tarea (últimos 3 meses cerrados): horas por tarea resuelta frente a la mediana del equipo
        ult3 = MESES[-4:-1]
        tipos_p = defaultdict(lambda: {'tareas': 0, 'horas': 0.0})
        for m in ult3:
            for tid in entradas_prod[pid].get(m, []):
                hh = htask[pid].get(tid, 0)
                if hh <= 0:
                    continue
                k = tarea_info[tid]['tipo']
                tipos_p[k]['tareas'] += 1; tipos_p[k]['horas'] += hh
        comp_tipo = []
        for k, v in sorted(tipos_p.items(), key=lambda x: -x[1]['tareas']):
            if k not in med_tipo or v['tareas'] < 2:
                continue
            hpt = v['horas'] / v['tareas']
            comp_tipo.append({'tipo': k, 'tareas': v['tareas'], 'horas_por_tarea': round(hpt, 2), 'mediana_equipo': med_tipo[k]['mediana_h'],
                              'casos_equipo': med_tipo[k]['casos'], 'desvio_pct': round((hpt / med_tipo[k]['mediana_h'] - 1) * 100) if med_tipo[k]['mediana_h'] else None})
        comp_tipo = comp_tipo[:8]
        semana = round(sum(h for f, h in hdia[pid].items() if str(lunes_p) <= f < str(hoy_p)), 1)
        filas.append({
            'persona_id': pid, 'nombre': p['nombre'], 'alias': p.get('alias'), 'puesto': principal, 'puestos': puestos,
            'grupo': grupo, 'equipo': NOMBRE_PUESTO.get(principal, principal), 'jefe': p.get('jefe'), 'estado_persona': p.get('estado'),
            'ayer': round(hdia[pid].get(str(ayer_p), 0), 1), 'ayer_fecha': str(ayer_p), 'semana': semana,
            'dias_lab_semana': dias_lab(lunes_p, hoy_p), 'zona': zona_txt(pid),
            'meses': meses, 'por_tipo': comp_tipo,
            'primera_imputacion': primera.get(pid),
            **({'diario_238': diarios_238[pid]} if pid in diarios_238 else {}),
        })
    filas.sort(key=lambda r: (['Accounts', 'Especialistas', 'Jefes y coordinación'].index(r['grupo']), r['equipo'], r['nombre']))

    # ---------------- horas raras (detector de build.py) ----------------
    D = leer(PANEL / 'build/datos.json', {}) or {}
    nom_a_pid = {}
    for u in miembros_clickup():
        if str(u['id']) in U:
            nom_a_pid[u['nombre']] = U[str(u['id'])]
    por_nombre_cli = {norm(n): i for i, n in nombres.items()}
    car = leer(PANEL / '_crudo/clickup/cartera.json', {}) or {}
    for a in (D.get('v7') or {}).get('anomalias', []):
        pid = nom_a_pid.get(a.get('persona'))
        if not pid or pid not in P:
            continue
        raras_out.append({'persona_id': pid, 'id': a['id'], 'tipo': a['tipo'], 'tarea': limpiar(sin_cliente(a.get('tarea'))), 'horas': a.get('horas'),
                          'motivo': limpiar(a.get('motivo')), 'url': a.get('url'), 'fecha': a.get('fecha')})
        cid = por_nombre_cli.get(norm(a.get('cliente') or ''))
        if cid:
            raras_cli.append({'cliente_id': cid, 'persona_id': pid, 'id': a['id'], 'cliente': nombres[cid], 'tarea_completa': limpiar(a.get('tarea'))[:110]})

    pct_global = round(total_imp / total_esp * 100) if total_esp else None
    escribir(DATA / 'horas/horas.json', {
        'formato': 1, 'generado': AHORA.strftime('%Y-%m-%d %H:%M'), 'hoy': str(HOY), 'ayer': str(ayer), 'mes': MES, 'meses': MESES,
        'horas_mes': HORAS_MES,
        'fuentes': {'horas': {'fuente': 'ClickUp · horas (llave propia)', 'hora': H['meta']['generado'], 'desde': H['meta']['desde']},
                    'tareas': {'fuente': 'ClickUp · historial de estados (llave propia)', 'hora': T['meta']['generado']},
                    'raras': {'fuente': 'Detector de horas raras (build.py del panel)', 'hora': (lambda g: f'{g[6:10]}-{g[3:5]}-{g[0:2]} {g[11:16]}' if g and re.match(r'\d\d-\d\d-\d{4}', g) else g)(D.get('generado'))}},
        'zonas': {'registros_que_cambian_de_dia': cambian_dia, 'nota': 'El día de trabajo de cada registro se decide en la zona de la persona (Argentina, Venezuela o España). El mes y los totales, en hora de Madrid como ClickUp: no cambian.'},
        'sello': {'pct_imputado_6m': pct_global, 'texto': f'Ojo: solo se imputa el {pct_global} % de las horas esperadas (6 meses): úsalo para avisar, no para juzgar.' if pct_global is not None else None,
                  'registros_fuera': descartadas},
        'estados_productivos': sorted(ESTADOS_PRODUCTIVOS),
        'medianas_tipo': [{'tipo': k, **v} for k, v in sorted(med_tipo.items(), key=lambda x: -x[1]['casos'])[:60]],
        'personas': filas, 'raras': raras_out, 'raras_cliente': raras_cli,
        'notas': {
            'esperadas': 'Esperadas = 128 h al mes menos ausencias; en el mes en curso, prorrateadas por días laborables hasta ayer. Todavía no hay tabla de ausencias: cuentan 0.',
            'productividad': 'Tareas que entraron en el mes en revisión del account, revisión del cliente, «ver cliente» o completado (primera entrada, historial de ClickUp), con la persona asignada hoy. Fuera las tareas contenedor (reuniones, daily, formación, gestión general…), igual que el detector de horas raras.',
            'comparacion': 'Cada persona se compara con su propia mediana de los 3 meses anteriores y con la mediana del equipo en su mismo tipo de tarea. Desvío marcado si pasa de ±50 %. Nunca un ranking.',
            'antes': 'Meses antes de su primera imputación en ClickUp: sin dato (no cuentan como 0).',
        },
    })
    print({'personas': len(filas), 'raras': len(raras_out), 'raras_cliente': len(raras_cli), 'tipos_con_mediana': len(med_tipo), 'pct_6m': pct_global})


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""fuentes_objetivos/objetivos.py · A4 (2-oct) · UNA sola lectura del objetivo del cliente y del semáforo del lunes.

Dónde vive el dato (no hay otro sitio):
  · la tabla «acciones» de la base de la app (local.db; RO_DB en pruebas; Postgres con DATABASE_URL), modo simulación:
      - tipo «objetivo_alta»     → objetivo del cliente. Es el MISMO tipo que ya guardaba Clientes nuevos («Cargar objetivo»);
                                   la ficha escribe el mismo tipo. Campos: leads_mes, coste_lead, coste_cita, ventas_mes
                                   (ficha) y citas_mes, presupuesto (Clientes nuevos). Un campo que no viene en una fila se
                                   hereda de la anterior; uno que viene vacío (null) se borra.
      - tipo «semaforo_semanal»  → semáforo del lunes: color (verde | ambar | rojo) y una línea de nota. La semana es la del
                                   momento en que se guardó (lunes, hora de Madrid): no la pone el navegador.
  · nada se escribe aquí: escribe el servidor (POST /api/acciones, con rastro y la regla «editar_objetivo_cliente»).

Quién lo lee:
  · fuentes_captacion/generar_captacion.py → data/captacion/captacion.json (Captación y el número que manda de Mi día);
  · fuentes_ficha/generar_ficha.py → data/objetivos/objetivos.json (ficha y Clientes nuevos, recortado por el servidor:
    coste_* e inversion_* solo a quien ve la inversión del cliente), y en vivo, con la misma regla, modulos/objetivos_comun.js.

Uso suelto:  python3 fuentes_objetivos/objetivos.py        (escribe data/objetivos/objetivos.json)
"""
import json
import os
import re
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

APP = Path(__file__).resolve().parents[1]
DATA = APP / 'data'
SALIDA = DATA / 'objetivos' / 'objetivos.json'
MAD = ZoneInfo('Europe/Madrid')

TIPO_OBJETIVO = 'objetivo_alta'
TIPO_SEMAFORO = 'semaforo_semanal'
# Campos del objetivo. «presupuesto» de Clientes nuevos sale como «inversion_mes» (el servidor lo quita a quien no ve la inversión).
CAMPOS = ('leads_mes', 'coste_lead', 'coste_cita', 'ventas_mes', 'citas_mes', 'inversion_mes')
ALIAS = {'presupuesto': 'inversion_mes'}
PRINCIPALES = ('leads_mes', 'coste_lead', 'coste_cita', 'ventas_mes')   # «cargado» = al menos uno de estos
COLORES = ('verde', 'ambar', 'rojo')
SEMANAS_HISTORIAL = 12
# La nota del semáforo la ve todo el que abre la ficha: sin importes (la ficha tampoco deja escribirlos).
RE_IMPORTE = re.compile(r"\d[\d.,]*\s*(?:€|euros?|EUR\b)|€\s*\d[\d.,]*")


def _db_path():
    return Path(os.environ.get('RO_DB') or APP / 'local.db')


def _filas_de_la_base():
    sql = ("SELECT id, creada, quien, cliente_id, modulo, tipo, vista_previa FROM acciones "
           "WHERE tipo IN (?, ?) AND cliente_id IS NOT NULL ORDER BY id")
    if os.environ.get('DATABASE_URL'):           # Render: la misma interfaz sobre Postgres
        sys.path.insert(1, str(APP / 'despliegue'))
        import base as BASE_PG  # noqa: E402
        with BASE_PG.conectar() as con:
            return [dict(r) for r in con.execute(sql, (TIPO_OBJETIVO, TIPO_SEMAFORO)).fetchall()]
    p = _db_path()
    if not p.exists():
        return []
    con = sqlite3.connect(f'file:{p}?mode=ro', uri=True)
    con.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in con.execute(sql, (TIPO_OBJETIVO, TIPO_SEMAFORO)).fetchall()]
    finally:
        con.close()


def _hora_madrid(creada):
    """«creada» de SQLite es UTC sin zona ('2026-10-02 20:15:03')."""
    try:
        d = datetime.fromisoformat(str(creada).replace('T', ' ')[:19])
    except Exception:
        return None
    return d.replace(tzinfo=timezone.utc).astimezone(MAD)


def lunes_de(d):
    return (d.date() - timedelta(days=d.weekday())).isoformat()


def _num(v):
    if v is None or v == '':
        return None
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    if x < 0 or x != x or x > 1e7:
        return None
    return int(x) if x == int(x) else round(x, 2)


def normalizar(fila):
    """Fila de «acciones» → fila común (lo que viaja en objetivos.json y lo que reduce también objetivos_comun.js)."""
    try:
        vp = json.loads(fila.get('vista_previa') or '{}') if isinstance(fila.get('vista_previa'), str) else (fila.get('vista_previa') or {})
    except Exception:
        vp = {}
    if not isinstance(vp, dict):
        vp = {}
    h = _hora_madrid(fila.get('creada'))
    out = {'id': fila['id'], 'tipo': fila['tipo'], 'cliente_id': fila['cliente_id'], 'quien': fila.get('quien'), 'modulo': fila.get('modulo'),
           'cuando': h.strftime('%Y-%m-%d %H:%M') if h else None, 'semana': lunes_de(h) if h else None}
    if fila['tipo'] == TIPO_OBJETIVO:
        campos = {}
        for k, v in vp.items():
            k = ALIAS.get(k, k)
            if k in CAMPOS:
                campos[k] = _num(v)
        out['campos'] = campos
    else:
        color = str(vp.get('color') or '').strip().lower().replace('á', 'a')
        out['color'] = color if color in COLORES else None
        out['nota'] = re.sub(r'\s{2,}', ' ', RE_IMPORTE.sub('', str(vp.get('nota') or ''))).strip().replace('\n', ' ')[:200]
    return out


def reducir(filas):
    """Filas comunes (de cualquier módulo, en cualquier orden) → {cliente_id: {objetivo, historial_objetivo, semaforo, semanas}}.
    Es LA regla: modulos/objetivos_comun.js la repite línea a línea para lo guardado después de la última vuelta."""
    out = {}
    for f in sorted(filas, key=lambda x: x['id']):
        c = out.setdefault(f['cliente_id'], {'cliente_id': f['cliente_id'], 'objetivo': None, 'historial_objetivo': [], 'semaforo': None, 'semanas': []})
        if f['tipo'] == TIPO_OBJETIVO:
            prev = {k: v for k, v in (c['objetivo'] or {}).items() if k in CAMPOS}
            nuevo = {**prev, **(f.get('campos') or {})}
            c['objetivo'] = {**{k: nuevo.get(k) for k in CAMPOS},
                             'cargado': any(nuevo.get(k) is not None for k in PRINCIPALES),
                             'quien': f.get('quien'), 'cuando': f.get('cuando'), 'desde': f.get('modulo'), 'accion_id': f['id']}
            c['historial_objetivo'].insert(0, {'accion_id': f['id'], 'quien': f.get('quien'), 'cuando': f.get('cuando'), 'desde': f.get('modulo'),
                                               'campos': f.get('campos') or {}})
        elif f.get('color'):
            s = {'color': f['color'], 'nota': f.get('nota') or '', 'quien': f.get('quien'), 'cuando': f.get('cuando'), 'semana': f.get('semana'), 'accion_id': f['id']}
            c['semaforo'] = s
            c['semanas'] = [x for x in c['semanas'] if x['semana'] != s['semana']]
            c['semanas'].insert(0, s)
    for c in out.values():
        c['historial_objetivo'] = c['historial_objetivo'][:10]
        c['semanas'] = sorted(c['semanas'], key=lambda x: x['semana'] or '', reverse=True)[:SEMANAS_HISTORIAL]
    return out


def leer():
    """{cliente_id: {...}} con lo que hay AHORA en la base. Lo usan Captación (generar_captacion.py) y las pruebas."""
    filas = [normalizar(f) for f in _filas_de_la_base()]
    return reducir(filas), filas


def objetivo_de(cid, todos=None):
    todos = todos if todos is not None else leer()[0]
    return (todos.get(cid) or {}).get('objetivo')


def escribir(salida=SALIDA):
    todos, filas = leer()
    por_cliente = {}
    for f in filas:
        por_cliente.setdefault(f['cliente_id'], []).append(f)
    doc = {
        '_meta': {'generado': datetime.now(MAD).strftime('%Y-%m-%d %H:%M'), 'fuente': 'base de la app (tabla acciones, modo simulación)',
                  'tipos': [TIPO_OBJETIVO, TIPO_SEMAFORO], 'nota': 'Una fila por cliente (cliente_id): el servidor solo la manda a quien ve ese cliente '
                  'y quita coste_* e inversion_* a quien no ve su inversión. Lo guardado después de esta hora se lee en vivo de /api/acciones.'},
        'generado': datetime.now(MAD).strftime('%Y-%m-%d %H:%M'),
        'ultima_accion': max((f['id'] for f in filas), default=0),
        'resumen': {'clientes_con_objetivo': sum(1 for c in todos.values() if (c['objetivo'] or {}).get('cargado')),
                    'clientes_con_semaforo': sum(1 for c in todos.values() if c['semaforo'])},
        'clientes': [{**c, 'filas': por_cliente.get(cid, [])} for cid, c in sorted(todos.items())],
    }
    salida.parent.mkdir(parents=True, exist_ok=True)
    tmp = salida.with_suffix('.tmp')
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=1))
    tmp.replace(salida)
    return doc


if __name__ == '__main__':
    d = escribir()
    print(f"objetivos.json: {d['resumen']['clientes_con_objetivo']} clientes con objetivo, {d['resumen']['clientes_con_semaforo']} con semáforo "
          f"(última acción n.º {d['ultima_accion']})")

"""Cinco métricas del artifact, agrupadas orientativamente por título.

Puro: el caller acredita IDs actuales autorizados antes de llamar y revalida
el ámbito antes de devolver la proyección. No concede permisos ni taxonomía.
"""
import datetime as dt
import math
import re
import statistics
import unicodedata
from collections import Counter, defaultdict
from zoneinfo import ZoneInfo
from contexto_tarea import texto_operativo

ZONA = ZoneInfo('Europe/Madrid')


def clave(v):
    return isinstance(v, str) and re.fullmatch(r'[A-Za-z0-9_-]{1,150}', v) is not None


def instante(v):
    if not isinstance(v, str):
        return None
    try:
        d = dt.datetime.fromisoformat(v.replace('Z', '+00:00'))
        return d if d.tzinfo and d.utcoffset() is not None else None
    except (ValueError, OverflowError):
        return None


def normalizar(v):
    if not isinstance(v, str):
        return ''
    s = unicodedata.normalize('NFKD', v).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', ' ', s).strip()


def grupo_titulo(titulo, nombres_clientes):
    """Misma regla explícita del build original716: clientes/fechas/5 palabras."""
    operativo = texto_operativo(titulo, limite=2000)
    # No convertir una redacción de credencial/contacto en una categoría aparente.
    if re.search(r'\[(?:dato protegido|secreto|importe|correo|teléfono|enlace protegido) omitido\]', operativo):
        return ''
    s = normalizar(operativo)
    for nombre in sorted({normalizar(x) for x in nombres_clientes}, key=lambda x: (-len(x), x)):
        if len(nombre) > 3:
            s = s.replace(nombre, ' ')
    s = re.sub(r'\b(\d+|enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre|sep|oct|ago|semana|s\d+|v\d+)\b', ' ', s)
    return ' '.join(s.split()[:5])


def construir(entradas, tareas, *, cliente_ids, tarea_ids, usuario_ids,
              nombres_clientes, observado_hasta, fuente, tareas_internas=frozenset()):
    fin = instante(observado_hasta)
    leido = instante(fuente.get('leido')) if isinstance(fuente, dict) else None
    sha = fuente.get('sha256') if isinstance(fuente, dict) else None
    if not fin or not leido or leido > fin or not isinstance(sha, str) or not re.fullmatch('[a-f0-9]{64}', sha):
        raise ValueError('Fuente y corte explícitos requeridos')
    for ids in (cliente_ids, tarea_ids, usuario_ids, tareas_internas):
        if not isinstance(ids, (set, frozenset)) or not all(clave(x) for x in ids):
            raise ValueError('Scope explícito requerido')
    if not tareas_internas.issubset(tarea_ids) or not isinstance(nombres_clientes, list) or not all(isinstance(x, str) for x in nombres_clientes):
        raise ValueError('Internos y nombres deben estar acreditados por el caller')
    if not isinstance(entradas, list) or not isinstance(tareas, list):
        raise ValueError('Colecciones requeridas')
    fecha_fin = fin.astimezone(ZONA).date()
    desde = fecha_fin - dt.timedelta(days=59)
    cuentas = Counter(t.get('id') for t in tareas if isinstance(t, dict) and clave(t.get('id')))
    catalogo = {}
    for t in tareas:
        if not isinstance(t, dict) or not clave(t.get('id')) or cuentas[t['id']] != 1 or t['id'] not in tarea_ids:
            continue
        cid = t.get('cliente_id')
        interno = 'cliente_id' in t and cid in (None, '') and t['id'] in tareas_internas
        if not interno and (not clave(cid) or cid not in cliente_ids):
            continue
        titulo = t.get('nombre')
        if isinstance(titulo, str) and 0 < len(titulo) <= 2000:
            grupo = grupo_titulo(titulo, nombres_clientes)
            if grupo:
                catalogo[t['id']] = grupo
    # Dedupe global: una versión ajena del mismoID también invalida la entrada.
    versiones = defaultdict(list)
    for e in entradas:
        if isinstance(e, dict) and clave(e.get('id')):
            versiones[e['id']].append(e)
    por_caso = defaultdict(list)
    grandes = Counter()
    for filas in versiones.values():
        # JSON exacto de campos primitivos relevantes, sin coerciones de tipos.
        huellas = set()
        for e in filas:
            vals = [e.get(k) for k in ('usuario_id', 'task_id', 'inicio', 'horas')]
            if any(type(v) not in (str, int, float, type(None)) for v in vals):
                huellas.add(('invalido', id(e)))
            else:
                huellas.add(tuple((type(v).__name__, repr(v)) for v in vals))
        if len(huellas) != 1:
            continue
        e = filas[0]
        tid, uid, inicio, horas = e.get('task_id'), e.get('usuario_id'), instante(e.get('inicio')), e.get('horas')
        if not clave(tid) or tid not in catalogo or not clave(uid) or uid not in usuario_ids or not inicio or inicio > min(fin, leido):
            continue
        if not desde <= inicio.astimezone(ZONA).date() <= fecha_fin or type(horas) not in (int, float):
            continue
        try:
            if not math.isfinite(horas) or horas < 0:
                continue
        except OverflowError:
            continue
        caso = (uid, tid)
        por_caso[caso].append(horas)
        grandes[catalogo[tid]] += horas > 10
    grupos = defaultdict(list)
    for (_, tid), hs in por_caso.items():
        try:
            total = math.fsum(hs)
            if math.isfinite(total):
                grupos[catalogo[tid]].append(total)
        except (OverflowError, ValueError):
            continue
    salida = []
    for etiqueta, hs in grupos.items():
        if len(hs) < 5:
            continue
        try:
            total = math.fsum(hs)
            if not math.isfinite(total):
                continue
            mediana = statistics.median(hs)
            if not math.isfinite(mediana):
                continue
        except (OverflowError, ValueError):
            continue
        salida.append({'grupo': etiqueta, 'casos': len(hs), 'mediana_h': mediana,
                       'max_h': max(hs), 'total_h': total,
                       'registros_mas10h': grandes[etiqueta]})
    return {'version': '375.1', 'clasificacion': 'orientativa_por_titulo',
            'regla': 'artifact716_clientes_numeros_meses_cinco_palabras',
            'unidad_muestra': 'usuario_id+task_id', 'unidad_maximo': 'suma_por_caso',
            'ventana': {'desde': desde.isoformat(), 'hasta_exclusivo': (fecha_fin + dt.timedelta(days=1)).isoformat(),
                        'observado_hasta': fin.isoformat(), 'zona': 'Europe/Madrid', 'atribucion': 'inicio'},
            'fuente': {'sha256': sha, 'leido': leido.isoformat()},
            'cobertura': 'parcial', 'duracion_cerrada_confirmada': False,
            'tipo_historico_confirmado': False, 'tiempo_normativo': None,
            'filas': sorted(salida, key=lambda r: (-r['total_h'], r['grupo']))}

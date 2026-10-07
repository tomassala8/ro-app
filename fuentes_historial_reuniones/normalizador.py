"""Historial Fathom offline. Sin red, escrituras, clasificación difusa ni permisos UI.
La salida privada NO es un DTO público ni debe servirse sin política explícita.
"""
import hashlib
import json
import os
import stat
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

VERSION = 1
EXCLUIDAS = {'Reunion_Interna_Equipo', 'Reunion_de_Venta', '_Para_Eliminar', 'HR'}


def fecha(valor):
    try:
        d = datetime.fromisoformat(valor.replace('Z', '+00:00'))
        return d if d.tzinfo and d.utcoffset() is not None else None
    except (AttributeError, TypeError, ValueError):
        return None


def identidad(m):
    call = re.search(r'^https://fathom\.video/calls/(\d+)(?:[/?#]|$)', str(m.get('url', '')))
    rid = str(m.get('recording_id', ''))
    return ('call:' + call[1]) if call else ('recording:' + rid if rid.isdigit() else None)


def leer_privado(ruta, raiz, limite=120_000_000, *, modo_privado=False):
    """Archivo regular dentro de raíz; rechaza symlinks incluso en ancestros."""
    p, base = Path(ruta).absolute(), Path(raiz).absolute()
    if '..' in p.parts or '..' in base.parts:
        raise ValueError('ruta no permitida')
    try:
        p.relative_to(base)
    except ValueError:
        raise ValueError('ruta fuera de raíz') from None
    for node in (p, *p.parents):
        if node.is_symlink():
            raise ValueError('enlace simbólico no permitido')
    fd = os.open(p, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        st = os.fstat(fd)
        if modo_privado and st.st_mode & 0o077:
            raise ValueError('archivo no privado')
        if not stat.S_ISREG(st.st_mode) or st.st_nlink != 1 or st.st_size > limite:
            raise ValueError('archivo irregular, enlazado o demasiado grande')
        with os.fdopen(fd, 'rb', closefd=False) as archivo:
            contenido = archivo.read(limite + 1)
        if len(contenido) > limite:
            raise ValueError('archivo demasiado grande')
        return contenido
    finally:
        os.close(fd)



def account_en_fecha(cid, dia, asignaciones):
    """Sólo timeline cerrado explícitamente confirmado; jamás account actual implícito."""
    encontrados = []
    for a in asignaciones:
        if not isinstance(a, dict):
            continue
        if (a.get('cliente_id') != cid or a.get('silla') != 'account'
                or a.get('historico_confirmado') is not True or not a.get('fuente')):
            continue
        try:
            desde = datetime.strptime(a['desde'], '%Y-%m-%d').date()
            hasta = datetime.strptime(a['hasta'], '%Y-%m-%d').date()
        except (KeyError, TypeError, ValueError):
            continue
        if desde <= dia <= hasta and a.get('persona_id'):
            encontrados.append(a['persona_id'])
    ids = sorted(set(encontrados))
    return {'estado': 'confirmado' if len(ids) == 1 else ('ambiguo' if ids else 'sin_evidencia'),
            'persona_id': ids[0] if len(ids) == 1 else None}


def normalizar(cache, clasificacion, catalogo, clientes_ids, *, documentos=(), indice=(),
               asignaciones=(), hasta=None):
    """Catalogo exacto carpeta:{cliente_id,confirmado:true,fuente}. No nombres/dominios.
    documentos: {call_id,carpeta,hash,transcripcion_disponible,referencia_privada};
    índice antiguo: {id,fecha,carpeta}; categoría nunca acredita cliente ni realización.
    Devuelve metadatos enlazados + depósito privado separado + cobertura no exhaustiva.
    """
    invalidos = 0
    def objetos(valor):
        nonlocal invalidos
        if not isinstance(valor, (list, tuple)):
            invalidos += 1
            return []
        invalidos += sum(not isinstance(x, dict) for x in valor)
        return [x for x in valor if isinstance(x, dict)]
    cache, documentos, indice = objetos(cache), objetos(documentos), objetos(indice)
    asignaciones = objetos(asignaciones)
    if not isinstance(catalogo, dict):
        invalidos += 1
        catalogo = {}
    if not isinstance(clasificacion, dict):
        invalidos += 1
        clasificacion = {}
    clientes_ids = {c for c in clientes_ids if isinstance(c, str)} if isinstance(clientes_ids, (list, tuple, set)) else set()
    catalogo_valido = {k: v for k, v in catalogo.items() if isinstance(v, dict)
        and v.get('confirmado') is True and isinstance(v.get('fuente'), str) and v.get('fuente')
        and isinstance(v.get('cliente_id'), str) and v['cliente_id'] in clientes_ids and isinstance(k, str)}
    invalidos += len(catalogo) - len(catalogo_valido)
    docs = {}
    for d in documentos:
        if str(d.get('call_id', '')).isdigit():
            docs.setdefault('call:' + str(d['call_id']), []).append(d)
    grupos = {}
    rechazados = 0
    for m in cache:
        key = identidad(m)
        if not key:
            rechazados += 1
            continue
        grupos.setdefault(key, []).append(m)
    for key in docs:
        grupos.setdefault(key, [])
    # El índice puede recordar una reunión sin texto; nunca rellena cliente desde título.
    for i in indice:
        if str(i.get('id', '')).isdigit():
            grupos.setdefault('call:' + str(i['id']), [])
    filas, privados = [], {}
    cuenta = {'cache_registros': len(cache), 'identidades': len(grupos), 'rechazados': rechazados,
              'entradas_malformadas': invalidos, 'excluidos': 0, 'sin_cliente_confirmado': 0, 'conflictos': 0,
              'duplicados_cache': sum(max(0, len(g)-1) for g in grupos.values())}
    idx, idx_conflictos = {}, set()
    for i in indice:
        k = str(i.get('id'))
        if k in idx and any(idx[k].get(c) != i.get(c) for c in ('fecha', 'carpeta')):
            idx_conflictos.add(k)
        else:
            idx.setdefault(k, i)
    for key, registros in sorted(grupos.items()):
        call = key.split(':', 1)[1]
        if call in idx_conflictos:
            cuenta['conflictos'] += 1
            continue
        d = docs.get(key, [])
        i = idx.get(call, {})
        categoria = i.get('carpeta', '')
        if not isinstance(categoria, str):
            cuenta['entradas_malformadas'] += 1
            continue
        if categoria.split('/')[0] in EXCLUIDAS:
            cuenta['excluidos'] += 1
            continue
        hashes = {hashlib.sha256(json.dumps(m, sort_keys=True, ensure_ascii=False).encode()).hexdigest() for m in registros}
        if len(hashes) > 1:
            cuenta['conflictos'] += 1
            continue  # ninguna versión pisa silenciosamente otra
        m = registros[0] if registros else {}
        folder = clasificacion.get(call)
        if folder is not None and not isinstance(folder, str):
            cuenta['entradas_malformadas'] += 1
            continue
        if folder in {'NO', 'REVISAR'}:
            cuenta['excluidos' if folder == 'NO' else 'sin_cliente_confirmado'] += 1
            continue
        folders = {x['carpeta'] for x in d if isinstance(x.get('carpeta'), str) and x['carpeta']}
        if any(x.get('carpeta') is not None and not isinstance(x.get('carpeta'), str) for x in d):
            cuenta['entradas_malformadas'] += 1
            continue
        if folder:
            folders.add(folder)
        if len(folders) != 1:
            cuenta['conflictos' if folders else 'sin_cliente_confirmado'] += 1
            continue
        folder = next(iter(folders))
        binding = catalogo_valido.get(folder)
        if not binding:
            cuenta['sin_cliente_confirmado'] += 1
            continue
        t = fecha(m.get('recording_start_time'))
        def dia_valido(raw):
            try:
                return datetime.strptime(raw, '%Y-%m-%d').date()
            except (TypeError, ValueError):
                return None
        fechas_docs = {v for x in d if (v := dia_valido(x.get('fecha'))) is not None}
        fecha_idx = dia_valido(i.get('fecha'))
        fecha_cache = t.astimezone(ZoneInfo('Europe/Madrid')).date() if t else None
        fechas = fechas_docs | ({fecha_idx} if fecha_idx else set()) | ({fecha_cache} if fecha_cache else set())
        discrepancia = len(fechas) > 1
        if fecha_cache:
            dia, fecha_fuente = fecha_cache, 'recording_start_time'
        elif len(fechas_docs) == 1:
            dia, fecha_fuente = next(iter(fechas_docs)), 'documento_fecha'
        elif fecha_idx:
            dia, fecha_fuente = fecha_idx, 'indice_fecha'
        else:
            dia, fecha_fuente = None, None
        if hasta and dia and dia > hasta:
            continue
        fin = fecha(m.get('recording_end_time'))
        dur = (fin-t).total_seconds()/60 if t and fin and fin > t else None
        tr = m.get('transcript')
        hay_texto = isinstance(tr, list) and any(isinstance(s, dict) and str(s.get('text', '')).strip() for s in tr)
        disponible = hay_texto or any(x.get('transcripcion_disponible') is True for x in d)
        stable = 'fathom_' + hashlib.sha256(key.encode()).hexdigest()[:24]
        cid = binding['cliente_id']
        filas.append({'id': stable, 'cliente_id': cid, 'fecha': dia.isoformat() if dia else None,
            'inicio': t.isoformat() if t else None, 'fecha_fuente': fecha_fuente, 'fecha_discrepancia': discrepancia,
            'fechas_evidencia': {'cache': fecha_cache.isoformat() if fecha_cache else None, 'documentos': sorted(v.isoformat() for v in fechas_docs), 'indice': fecha_idx.isoformat() if fecha_idx else None},
            'duracion_minutos': dur, 'titulo': 'Reunión registrada',
            'estado_realizacion': 'grabacion_registrada' if dur else 'sin_confirmar',
            'celebrada_confirmada': False, 'tipo_reunion': 'sin_confirmar',
            'transcripcion_disponible': disponible, 'grabacion_acceso': 'no_verificado',
            'account_historico': account_en_fecha(cid, dia, asignaciones) if dia else {'estado':'sin_evidencia','persona_id':None},
            'fuente': 'fathom_local', 'hash_fuente': next(iter(hashes), None),
            'enlace_cliente': 'catalogo_confirmado'})
        privados[stable] = {'identidad_fuente': key, 'vinculo_cliente_evidencia': binding['fuente'], 'recording_id': m.get('recording_id'),
            'titulo': m.get('title') or m.get('meeting_title'), 'host': m.get('recorded_by'),
            'invitados': m.get('calendar_invitees'), 'transcripcion': tr if hay_texto else None,
            'resumen': m.get('default_summary'), 'enlace_grabacion': m.get('share_url'),
            'documentos': d}
    cuenta.update({'reuniones_enlazadas': len(filas), 'con_transcripcion': sum(f['transcripcion_disponible'] for f in filas),
                   'clientes_enlazados': len({f['cliente_id'] for f in filas}),
                   'exhaustiva': False, 'razon': 'Corpus local parcial; clasificación y enlaces pendientes, no todas las cuentas Fathom.'})
    return {'version': VERSION, 'reuniones': filas, 'privados': privados, 'cobertura': cuenta}

"""Proyección pura de disponibilidad de evidencia. No mide cumplimiento ni hace IO.

El llamador proporciona los catálogos actuales y los permisos vigentes por identidad.
Los registros históricos nunca se convierten en reuniones celebradas ni se atribuyen
al account/trafficker actual. No devuelve contratos, nombres, texto ni enlaces.
"""
from collections import Counter
from datetime import date
import re

ID = re.compile(r'^[a-zA-Z0-9_-]{1,100}$')


def _id(v):
    return isinstance(v, str) and bool(ID.fullmatch(v))


def _dia(v):
    if not isinstance(v, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', v):
        return None
    try:
        return date.fromisoformat(v)
    except ValueError:
        return None


def _unicos(filas, clave):
    filas = [r for r in filas if isinstance(r, dict) and _id(r.get(clave))]
    n = Counter(r[clave] for r in filas)
    return {r[clave]: r for r in filas if n[r[clave]] == 1}


def proyectar(*, reglas, historial, clientes, personas, asignaciones, real_id,
              vista_id, hoy, activo, permite):
    """DTO propuesto446. activo(cid) y permite(persona,cid) deben devolver True.

    No cubre producción/finanzas. El endpoint que eventualmente lo use debe exigir
    además su puerta de módulo y repetir autorización antes de enviar la respuesta.
    Cero registros leídos no demuestra que no hubo reuniones.
    """
    corte = _dia(hoy)
    if corte is None:
        raise ValueError('fecha_invalida')
    ps = _unicos(personas, 'id')
    def persona_valida(pid):
        p = ps.get(pid)
        roles = p.get('puestos') if p else None
        return (p is not None and p.get('estado') == 'activo'
                and p.get('activo') is not False and isinstance(roles, list)
                and bool(roles) and all(_id(x) for x in roles)
                and len(set(roles)) == len(roles))
    if not persona_valida(real_id) or not persona_valida(vista_id):
        return {'version': '446.1', 'fecha': hoy, 'filas': []}
    cs = _unicos(clientes, 'id')
    rs = _unicos(reglas, 'cliente_id')
    hist = historial if isinstance(historial, dict) else {}
    # Deduplicación global antes del scope: un ID con dos clientes no se atribuye.
    grupos = {}
    for cid, rows in hist.items():
        if not isinstance(rows, list):
            continue
        for r in rows:
            if isinstance(r, dict) and _id(r.get('id')):
                grupos.setdefault(r['id'], []).append((cid, r))
    validos = {}
    for rid, versiones in grupos.items():
        primera = versiones[0]
        if any(v != primera for v in versiones[1:]):
            continue
        cid, r = primera
        f = _dia(r.get('fecha'))
        if (r.get('cliente_id') == cid and f and f <= corte
                and r.get('fecha_ambigua') is False
                and r.get('registro') == 'registro_historico'):
            validos.setdefault(cid, []).append(r)
    out = []
    for cid, regla in sorted(rs.items()):
        if (cid not in cs or activo(cid) is not True
                or any(permite(ps[pid], cid) is not True for pid in (real_id, vista_id))
                or regla.get('estado_cohorte') != 'confirmada'
                or regla.get('tipo_cohorte') != 'metodo_actual_recurrente'
                or type(regla.get('cadencia_dias')) is not int
                or regla['cadencia_dias'] != 15
                or regla.get('responsable_role') != 'trafficker'):
            continue
        owners = set()
        for a in asignaciones:
            if not isinstance(a, dict):
                continue
            inicio, fin = _dia(a.get('desde')), _dia(a.get('hasta'))
            pid = a.get('persona_id')
            if (a.get('cliente_id') == cid and a.get('silla') == 'trafficker'
                    and not a.get('duda') and persona_valida(pid)
                    and inicio and inicio <= corte
                    and (not a.get('hasta') or (fin and fin >= corte))
                    and (not a.get('suplencia') or fin is not None)):
                owners.add(pid)
        filas = validos.get(cid, [])
        fechas = [r['fecha'] for r in filas]
        out.append({'cliente_id': cid, 'cadencia_dias': 15,
                    'responsable_role': 'trafficker',
                    'responsable_actual_id': next(iter(owners)) if len(owners) == 1 else None,
                    'responsable_actual_estado': 'unico' if len(owners) == 1 else 'por_confirmar',
                    'registros_historicos_observados': len(filas),
                    'ultimo_registro_historico': max(fechas) if fechas else None,
                    'fuente_registro': 'historial_local_129', 'cobertura': 'parcial',
                    'responsable_historico': None, 'celebracion_confirmada': None,
                    'participacion_trafficker_confirmada': None,
                    'ultima_reunion_confirmada': None, 'proxima_revision': None,
                    'cumplimiento': None,
                    'faltantes': ['celebracion', 'participacion_trafficker',
                                  'responsable_en_fecha', 'cobertura_intervalo'],
                    'accion_local': 'revisar_evidencia_del_registro' if filas else 'aportar_evidencia_de_reunion'})
    return {'version': '446.1', 'fecha': hoy, 'filas': out}

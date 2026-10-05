"""359: noventa fechas de duraciones personales observadas. Puro, sin IO/permisos.
No clientes ni títulos al DTO. No calendario laboral, objetivo ni evaluación.
"""
import datetime as dt
import math
import re
from collections import defaultdict
from zoneinfo import ZoneInfo
from identidad_generadores_212 import identidades

VERSION = '359.1'
DIAS = 90

def _id(x):
    return isinstance(x, (str, int)) and not isinstance(x, bool) and bool(re.fullmatch(r'[A-Za-z0-9_-]{1,150}', str(x)))

def _instante(x, zona=None):
    if not isinstance(x, str): return None
    try:
        d = dt.datetime.fromisoformat(x.replace('Z', '+00:00'))
        if d.tzinfo is None:
            if zona is None: return None
            z = ZoneInfo(zona)
            # Hora local ambigua o inexistente no se convierte por intuición.
            a, b = d.replace(tzinfo=z, fold=0), d.replace(tzinfo=z, fold=1)
            if a.utcoffset() != b.utcoffset() or a.astimezone(dt.timezone.utc).astimezone(z).replace(tzinfo=None) != d: return None
            d = a
        if abs(d.utcoffset().total_seconds()) > 14*3600: return None
        return d.astimezone(dt.timezone.utc)
    except (ValueError, TypeError, OverflowError, AttributeError, KeyError): return None

def construir_historial(cache, personas, usuarios, hoy, *, zona_sello=None):
    """La fecha del panel es explícita; ventana natural anterior a hoy, por zona personal.
    Naive source stamp sólo con zona_sello acreditada por caller; inicios siempre aware.
    Duración es observación de fuente atribuida al inicio, no fin ni jornada confirmados.
    """
    try:
        corte_fecha = dt.date.fromisoformat(hoy)
        if str(corte_fecha) != hoy: raise ValueError()
        fuente = _instante(cache['meta']['generado'], zona_sello)
        if not fuente or fuente.astimezone(ZoneInfo('Europe/Madrid')).date() > corte_fecha or not isinstance(cache.get('entradas'), list): raise ValueError()
    except (ValueError, TypeError, KeyError, AttributeError): raise ValueError('Corte o fuente no acreditados')
    ps = personas if isinstance(personas, list) else []
    grupos = defaultdict(list)
    for p in ps:
        if isinstance(p, dict) and isinstance(p.get('id'),str) and _id(p.get('id')): grupos[str(p['id'])].append(p)
    zonas = {}
    for pid, xs in grupos.items():
        if len(xs) != 1 or xs[0].get('estado') != 'activo' or xs[0].get('activo') is False or xs[0].get('zona_a_confirmar') is not False: continue
        try:
            if not isinstance(xs[0].get('zona'), str): continue
            zonas[pid] = ZoneInfo(xs[0]['zona'])
        except (ValueError, TypeError, KeyError): continue
    mapa = identidades(ps, usuarios)['por_usuario']
    dias = [str(corte_fecha-dt.timedelta(days=i)) for i in range(DIAS, 0, -1)]
    valores = defaultdict(list); conflictos = set(); versiones = defaultdict(list)
    conteos = {'entradas_fuente':len(cache['entradas']), 'invalidas':0, 'sin_identidad_activa_zona':0, 'fuera_ventana':0, 'replays':0, 'ids_invalidos_o_conflictivos':0}
    for e in cache['entradas']:
        if not isinstance(e, dict) or not _id(e.get('id')):
            conteos['invalidas'] += 1; continue
        eid = str(e['id']); inicio = _instante(e.get('inicio'))
        h = e.get('horas'); uid = str(e['usuario_id']) if _id(e.get('usuario_id')) else None
        pid = mapa.get(uid); dia = str(inicio.astimezone(zonas[pid]).date()) if inicio and pid in zonas else None
        try: valido = not isinstance(h, bool) and isinstance(h, (int,float)) and math.isfinite(h) and h >= 0
        except (OverflowError,ValueError): valido = False
        task_id = e.get('task_id')
        tarea_valida = task_id is None or _id(task_id)
        if not inicio or inicio > fuente or not valido or uid is None or not tarea_valida:
            conteos['invalidas'] += 1; versiones[eid].append((None, pid, dia)); continue
        # Se revisan IDs de todo el caché antes de proyectar personas: una colisión ajena no se ignora.
        fingerprint = (uid,inicio.isoformat(),float(h),None if task_id is None else str(task_id))
        versiones[eid].append((fingerprint,pid,dia))
    for xs in versiones.values():
        fingerprints = {x[0] for x in xs}
        if None in fingerprints or len(fingerprints) != 1:
            conteos['ids_invalidos_o_conflictivos'] += 1
            conflictos.update((pid,dia) for _,pid,dia in xs if pid in zonas and dia in dias)
            continue
        conteos['replays'] += len(xs)-1
        fp,pid,dia = xs[0]
        if pid not in zonas: conteos['sin_identidad_activa_zona'] += 1; continue
        if dia not in dias: conteos['fuera_ventana'] += 1; continue
        valores[pid,dia].append(fp[2])
    series = {}
    for pid,zona in zonas.items():
        filas = []
        for dia in dias:
            hs = valores.get((pid,dia),[])
            try: total = math.fsum(hs) if hs and (pid,dia) not in conflictos else None
            except (OverflowError,ValueError): total = None
            if total is not None and not math.isfinite(total): total = None
            redondeado = round(total,4) if total is not None else None
            if total is not None and total > 0 and redondeado == 0: redondeado = total
            filas.append({'fecha':dia,'horas':redondeado,'entradas':len(hs) if total is not None else None,'estado':'observado' if total is not None else 'sin_dato'})
        series[pid] = {'version':VERSION,'fuente':'ClickUp entradas','fecha_fuente_utc':fuente.isoformat(),'cobertura':'parcial','zona':str(zona),'zona_confirmada':True,'desde':dias[0],'hasta':dias[-1],'corte_fecha':hoy,'criterio_corte':'anterior_fecha_referencia','atribucion':'inicio','duracion_cerrada_confirmada':False,'sin_registros_no_equivale_a_cero':True,'dias':filas}
    return {'series':series,'diagnostico':conteos,'identidad':'correo_exacto_unico_204_212','dias_naturales':DIAS}

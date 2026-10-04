#!/usr/bin/env python3
"""generar_captacion.py · M6 Captación (Torre de Control dentro de la app). 0 llamadas a APIs.

Junta, en solo lectura, lo que ya está generado:
  · 20_FASE2_CAPTACION/captacion.json  (~/RO_HERRAMIENTAS/captacion/captacion.py: Meta + embudo y citas de GHL)
  · fuentes_captacion/anuncios.json     (anuncios_meta.py: anuncios, rechazados y aprendizaje)
  · Google Ads: MUESTRA MANUAL de septiembre de 14_GOOGLE_ADS_VIA_WINDSOR.md (Fountainhead = Accompany)
    hasta que exista windsor_api_key en el llavero (W2).
  · Foto de la Torre del 17-sep (torre-de-control-paid.zip) para la historia.
  · data/asignaciones.json, data/personas.json, data/clientes.json (E0) y data/clientes/*.json (ids, E1).

Escribe data/captacion/captacion.json, que servir.py sirve RECORTADO (reglas_permisos.json → datos_de_modulo):
  · cada fila de cliente lleva cliente_id → solo llega a quien ve ese cliente;
  · todo lo que es dinero va en claves gasto* / coste* / cpl* / inversion* / presupuesto_ads → se quita a quien
    no ve la inversión (D-81, D-87). Los textos con euros van en «gasto_texto»; «texto» va sin cifras de dinero.
  · ningún dato personal de leads: solo recuentos.
Uso:  python3 generar_captacion.py
"""
import json
import os
import re
import sys
import zipfile
from datetime import date, datetime, timedelta
from pathlib import Path

AQUI = Path(__file__).resolve().parent
APP = AQUI.parent
RAIZ = APP.parent
DATA = APP / 'data'
CAPTACION = RAIZ / '20_FASE2_CAPTACION' / 'captacion.json'
ANUNCIOS = AQUI / 'anuncios.json'
GHL_TOTALES = AQUI / 'ghl_totales.json'   # ghl_totales.py: contactos de cada subcuenta en toda su historia
sys.path.insert(1, str(Path(__file__).resolve().parents[1]))  # C5: rutas y secretos en config.py
import config  # noqa: E402
from fuentes_captacion.cpm_referencia_417 import proyectar as cpm_referencia417
from fuentes_verdad import clientes_activos as ACT
from fuentes_captacion.coherencia_crm_297 import proyectar as proyectar_crm, conteo, suma_observada
from fuentes_objetivos import objetivos as OBJETIVOS  # noqa: E402  (A4: el objetivo del cliente, de un solo sitio)
TORRE_ZIP = config.TORRE_ZIP
SALIDA = DATA / 'captacion' / 'captacion.json'

# ---------- parámetros firmados (11_DECISIONES y tabla U del plan v2) ----------
TECHO_CPL = 35.0          # €/lead: solo para clientes sin objetivo cargado (Torre; D-03)
ALARMA_CITA = 100.0       # €/cita: red de seguridad sin objetivo (D-03)
ARRANQUE_CITA = 45.0      # €/cita solo en el arranque (D-03)
FATIGA_FREC = 3.0         # D-39: frecuencia > 3 (ámbar) … solo cuenta con una segunda señal
FATIGA_CAIDA_CTR = 40.0   # D-39: … caída del porcentaje de clics ≥ 40 %
FATIGA_COSTE_X = 2.0      # D-39: … o coste por lead × 2
MIN_IMPRESIONES = 1000    # para comparar porcentajes de clics con sentido
GANADOR_VECES = 10        # D-40: cuenta en marcha: gasto ≥ 10 veces el objetivo con coste ≤ objetivo
GANADOR_ARRANQUE = (3, 45.0)  # D-40: arranque (protocolo v3): ≥ 3 contactos a ≤ 45 €
ROJOS_TRAFFICKER = (2, 4)     # D-41: ≤ 2 verde · 3-4 ámbar · ≥ 5 rojo
ASISTENCIA = (75, 60)         # D-45
CUENTAS_TRAFFICKER = 16       # D-07: 16 proyectos por trafficker (aviso desde 14)

# ---------- Google Ads · muestra manual (14_GOOGLE_ADS_VIA_WINDSOR.md, 2-oct, sesión de Windsor de gmb1@) ----------
GADS_PERIODO = ['2026-09-01', '2026-09-30']
GADS_MUESTRA = {  # cliente de la app: (cuenta, coste, clics, impresiones, conversiones, último día con gasto)
    'ayg-asesores': ('AyG Asesores', 1357.62, 768, 10985, 32, '2026-10-01'),
    'kiosko-box': ('Kiosko', 608.30, 1128, 12582, 321.1, '2026-10-01'),
    'accompany': ('Fountainhead Holding (= Accompany)', 308.10, 129, 3941, 2, '2026-09-28'),
    'consulting-f': ('Consulting F', 263.58, 170, 2960, 4, '2026-09-18'),
    'gac': ('GAC Economistas y Abogados', 222.55, 517, 24084, 2, '2026-09-15'),
    'busbac': ('Busbac Serveis', 151.92, 483, 9661, 0, '2026-10-01'),
}
GADS_PARADAS = {  # cuentas que Windsor ve sin gasto reciente: (cuenta, último día con gasto, gasto 2026)
    'aselegal': ('Aselegal', '2026-07-30', 2166), 'fitec-asesores': ('FITEC Consultores', '2026-06-03', 1554),
    'greconsult': ('Greconsult', '2026-05-25', 2272), 'centro-consulting': ('CE Consulting Zaragoza', '2026-05-18', 2492),
    'bit-24': ('BIT24', '2026-03-19', 511),
}
GADS_FUERA_DE_WINDSOR = ['asetra', 'oteca', 'mg-economistes']   # tienen Google Ads en Looker y no están en Windsor
GADS_SIN_CLIENTE = [  # en Windsor y sin cliente en la app
    {'cliente_id': 'taller-del-patinete', 'nombre': 'Taller del Patinete', 'cuenta': 'Taller del Patinete',
     'texto': 'Sigue gastando en Google Ads (activo el 1-oct) y es un cliente en cierre por impago: revisar si debe seguir encendido.',
     'gasto_texto': '53 € en septiembre; 5.191 clics y 0 conversiones medidas.', 'gasto_sep': 53.43, 'clics': 5191, 'conversiones': 0},
]

CLASE_TXT = {'paid': 'publicidad', 'seguimiento': 'seguimiento del despacho', 'integracion': 'integración', 'info': 'informativo', 'dato': 'dato pendiente'}
ETAPAS = ['nuevo', 'seguimiento', 'cita', 'presupuesto', 'cerrado', 'descartado']


def leer(p, defecto=None):
    try:
        return json.loads(Path(p).read_text())
    except Exception:
        return defecto


def r2(x):
    return None if x is None else round(x, 2)


def div(a, b):
    return (a / b) if b else None


def sin_euros(t):
    """Texto sin cifras de dinero (para quien no ve la inversión). El original va en gasto_texto."""
    s = re.sub(r'\s*\((\d[\d.,]*)\s*€ invertidos\)', ' con gasto', t)
    s = re.sub(r'\s*\([^)]*\d[\d.,]*\s*€[^)]*\)', '', s)
    s = re.sub(r'\s+de\s+\d[\d.,]*\s*€', '', s)
    s = re.sub(r'\d[\d.,]*\s*€', '…', s)
    return re.sub(r'\s{2,}', ' ', s).strip()


def con_motivo(m):
    t = m['texto']
    out = {'texto': sin_euros(t), 'clase_id': m.get('clase_id'), 'clase': CLASE_TXT.get(m.get('clase_id'), m.get('clase')), 'nivel': m.get('nivel')}
    if out['texto'] != t:
        out['gasto_texto'] = t
    return out


def torre():
    try:
        with zipfile.ZipFile(TORRE_ZIP) as z:
            html = z.read('torre-de-control-paid/torre-de-control-paid.html').decode()
        return json.loads(re.search(r'const SEED = (\{.*?\});\n', html, re.S).group(1))
    except Exception as e:
        print('Aviso: sin foto de la Torre:', e)
        return None


TORRE_A_APP = {'bit24': 'bit-24', 'musashi': 'musashi-consultores', 'aselegal': 'aselegal', 'gac': 'gac', 'ecom': 'ecom-advisory',
               'innova': 'innova-scala', 'ayg': 'ayg-asesores', 'consultingf': 'consulting-f', 'accompany': 'accompany',
               'busbac': 'busbac', 'kiosko': 'kiosko-box', 'gestanex': 'gestanex', 'akua': 'akua', 'orejana': 'orejana'}


def act_num_de(m):
    return (m.get('cuenta_id') or '').replace('act_', '')


def iniciales_equipo(personas):
    """Iniciales de producción y publicidad para reconocer al autor en el nombre del anuncio (D-43)."""
    out = {}
    for p in personas:
        if not set(p.get('puestos', [])) & {'produccion', 'trafficker', 'jefa_publicidad'}:
            continue
        partes = [x for x in re.split(r'\s+', re.sub(r'\(.*?\)', '', p.get('nombre') or '')) if x]
        if len(partes) >= 2:
            out[(partes[0][0] + partes[1][0]).upper()] = p['id']
    return out


def autor_de(nombre, inis):
    for tok in re.split(r'[\s_\-|·/\[\]()]+', nombre or ''):
        if re.fullmatch(r'[A-Z]{2}', tok) and tok in inis:
            return inis[tok]
    return None


def anuncios_de(cuenta, cli_nuevo, inis):
    """Cansadas (dos señales a la vez), en vigilancia (una señal), ganadoras (D-40), rechazadas y aprendizaje."""
    if not cuenta:
        return None
    v = cuenta.get('ventanas', {})
    previo = {a['ad_id']: a for a in v.get('7d_prev', [])}
    d30 = {a['ad_id']: a for a in v.get('30d', [])}
    filas = []
    for a in v.get('7d', []):
        p = previo.get(a['ad_id'])
        cpl = div(a['gasto'], a['leads']); cpl_p = div(p['gasto'], p['leads']) if p else None
        caida = None
        if p and p['impresiones'] >= MIN_IMPRESIONES and a['impresiones'] >= MIN_IMPRESIONES and p['ctr']:
            caida = round((1 - a['ctr'] / p['ctr']) * 100, 1)
        coste_x = round(cpl / cpl_p, 2) if (cpl and cpl_p) else None
        senales = []
        if (a['frecuencia'] or 0) > FATIGA_FREC:
            senales.append(f"frecuencia {str(a['frecuencia']).replace('.', ',')}")
        if caida is not None and caida >= FATIGA_CAIDA_CTR:
            senales.append(f"clics −{round(caida)} %")
        if coste_x and coste_x >= FATIGA_COSTE_X:
            senales.append(f"coste por lead ×{str(coste_x).replace('.', ',')}")
        a30 = d30.get(a['ad_id']) or a
        cpl30 = div(a30['gasto'], a30['leads'])
        ganador = bool(cpl30 is not None and cpl30 <= TECHO_CPL and a30['gasto'] >= GANADOR_VECES * TECHO_CPL) or \
            bool(cli_nuevo and a30['leads'] >= GANADOR_ARRANQUE[0] and cpl30 is not None and cpl30 <= GANADOR_ARRANQUE[1])
        filas.append({
            'nombre': a['nombre'], 'campana': a['campana'], 'conjunto': a['conjunto'], 'ad_id': a.get('ad_id'), 'campaign_id': a.get('campaign_id'),
            'impresiones_7d': a['impresiones'], 'clics_7d': a['clics'], 'ctr_7d': a['ctr'], 'ctr_previo': p['ctr'] if p else None,
            'caida_ctr_pct': caida, 'frecuencia_7d': a['frecuencia'], 'leads_7d': a['leads'], 'leads_30d': a30['leads'],
            'gasto_7d': a['gasto'], 'cpl_7d': r2(cpl), 'cpl_previo': r2(cpl_p), 'gasto_30d': a30['gasto'], 'cpl_30d': r2(cpl30),
            'senales': senales, 'cansada': len(senales) >= 2, 'vigilar': len(senales) == 1, 'ganadora': ganador,
            'autor': autor_de(a['nombre'], inis),
        })
    # ganadoras que no gastaron esta semana también cuentan (30 días)
    vistos = {f['nombre'] for f in filas}
    for a in v.get('30d', []):
        cpl30 = div(a['gasto'], a['leads'])
        if a['nombre'] in vistos or cpl30 is None:
            continue
        if (cpl30 <= TECHO_CPL and a['gasto'] >= GANADOR_VECES * TECHO_CPL) or (cli_nuevo and a['leads'] >= GANADOR_ARRANQUE[0] and cpl30 <= GANADOR_ARRANQUE[1]):
            filas.append({'nombre': a['nombre'], 'campana': a['campana'], 'conjunto': a['conjunto'], 'ad_id': a.get('ad_id'), 'campaign_id': a.get('campaign_id'), 'leads_30d': a['leads'], 'gasto_30d': a['gasto'],
                          'cpl_30d': r2(cpl30), 'frecuencia_7d': None, 'senales': [], 'cansada': False, 'vigilar': False, 'ganadora': True,
                          'sin_gasto_7d': True, 'autor': autor_de(a['nombre'], inis)})
    activos_30 = {a['nombre'] for a in v.get('30d', [])}
    hace30 = (date.today() - timedelta(days=30)).isoformat()
    problemas = [p for p in (cuenta.get('problemas') or []) if p['nombre'] in activos_30 or (p.get('desde') or '') >= hace30]
    conj = cuenta.get('conjuntos') or []
    limitados = sum(1 for s in conj if s.get('aprendizaje') == 'FAIL')
    con_dato = sum(1 for s in conj if s.get('aprendizaje'))
    filas.sort(key=lambda f: (not f['cansada'], not f['vigilar'], -(f.get('gasto_7d') or 0)))
    return {
        'anuncios': filas[:30], 'total_7d': len(v.get('7d', [])),
        'cansadas': sum(f['cansada'] for f in filas), 'vigilar': sum(f['vigilar'] for f in filas), 'ganadoras': sum(f['ganadora'] for f in filas),
        'sin_autor': sum(1 for f in filas if not f['autor']),
        'problemas': problemas[:12], 'problemas_total': len(problemas),
        'conjuntos_activos': len(conj), 'conjuntos_con_dato': con_dato, 'aprendizaje_limitado': limitados,
        'pct_limitado': round(limitados / con_dato * 100) if con_dato else None,
        'errores': cuenta.get('errores') or [], 'convertida_a_madrid': cuenta.get('convertida_a_madrid'), 'zona_horaria': cuenta.get('zona_horaria'),
    }


LIMITE_LECTOR_H = 7      # captacion.py va cada 3 h en la ligera: con más de 7 h, el dato es viejo
LIMITE_ANUNCIOS_H = 30   # anuncios_meta.py solo corre en la completa (6:00 y 14:00)


def estado_fuente(hora, limite_h, n_err, n_total, que):
    """Estado de una fuente de Captación (auditoría 35): «caida» si no respondió ninguna, «con_errores» si fallaron
    algunas, «dato_viejo» si su hora pasa del límite, «bien» si no. Con errores lleva «hora_error» = la hora de la
    lectura que falló: si fue en esta vuelta, la tubería lo cuenta como fallo de esa fuente y avisa."""
    out = {'estado': 'bien' if n_total > 0 else 'sin_dato'}
    try:
        edad = (datetime.now() - datetime.strptime(str(hora)[:16], '%Y-%m-%d %H:%M')).total_seconds() / 3600
    except (TypeError, ValueError):
        edad = None
    if edad is None or edad < 0 or edad > limite_h:
        out['estado'] = 'dato_viejo' if n_total > 0 else 'sin_dato'
    if n_err:
        out.update({'estado': 'caida' if n_total and n_err >= n_total else 'con_errores', 'error': f'{n_err} de {n_total} {que}',
                    'hora_error': str(hora)[:16] if hora else datetime.now().strftime('%Y-%m-%d %H:%M')})
    return out


def main():
    cap = leer(CAPTACION)
    if not cap:
        sys.exit(f'No encuentro {CAPTACION}: lanza antes ~/RO_HERRAMIENTAS/captacion/captacion.py')
    anu = leer(ANUNCIOS, {'cuentas': {}})
    n_meta = sum(1 for c in cap.get('clientes', []) if (c.get('meta') or {}).get('cuenta_id'))
    n_meta_err = sum(1 for c in cap.get('clientes', []) if (c.get('meta') or {}).get('cuenta_id') and (c.get('meta') or {}).get('error'))
    n_ghl = sum(1 for c in cap.get('clientes', []) if c.get('ghl'))
    n_ghl_err = sum(1 for c in cap.get('clientes', []) if (c.get('ghl') or {}).get('error'))
    n_anu_err = sum(1 for x in (anu.get('cuentas') or {}).values() if x.get('errores'))
    personas = leer(DATA / 'personas.json', [])
    personas = personas if isinstance(personas, list) else personas.get('personas', [])
    alias = {p['id']: p.get('alias') or p.get('nombre') for p in personas}
    asign = leer(DATA / 'asignaciones.json', [])
    asign = asign if isinstance(asign, list) else asign.get('asignaciones', [])
    base = leer(DATA / 'clientes.json', [])
    ids_base417 = [x.get('id') for x in (base if isinstance(base, list) else base.get('clientes', [])) if isinstance(x, dict)]
    base = {c['id']: c for c in (base if isinstance(base, list) else base.get('clientes', []))}
    cap_a_app = {}
    for f in (DATA / 'clientes').glob('*.json'):
        d = leer(f, {})
        if d.get('ids', {}).get('captacion'):
            cap_a_app[d['ids']['captacion']] = d['id']
    inis = iniciales_equipo(personas)
    # Verdad única (E0 ronda 5): equipo, «nuevo» y la fuga de integración salen de ahí; los leads que llegan a GHL,
    # de Salud del CRM (contactos nuevos no manuales en 7 días): UNA definición para toda la app (auditoría E-03).
    verdad = (leer(DATA / 'verdad' / 'clientes.json', {}) or {}).get('clientes') or []
    verdad = {v['cliente_id']: v for v in verdad} if isinstance(verdad, list) else verdad
    crm = {x['cliente_id']: x for x in (leer(DATA / 'crm' / 'crm.json', {}) or {}).get('subcuentas', []) if x.get('cliente_id')}
    totales = (leer(GHL_TOTALES, {}) or {}).get('subcuentas', {})
    seed = torre()
    torre_por_app = {TORRE_A_APP[c['id']]: c for c in (seed or {}).get('clientes', []) if c['id'] in TORRE_A_APP}

    def equipo(cid):
        v = verdad.get(cid)
        if v and v.get('equipo') is not None:
            out = {}
            for silla in ('trafficker', 'account', 'crm'):
                s = sorted(v['equipo'].get(silla) or [], key=lambda a: (not a.get('principal'), bool(a.get('suplencia'))))
                out[silla] = (v.get('account') if silla == 'account' else (s[0]['persona_id'] if s else None))
                out[silla + '_otros'] = [a['persona_id'] for a in s if a['persona_id'] != out[silla]]
                out[silla + '_confianza'] = None
            return out
        filas = [a for a in asign if a['cliente_id'] == cid and not a.get('hasta')]
        out = {}
        for silla in ('trafficker', 'account', 'crm'):
            s = sorted([a for a in filas if a['silla'] == silla], key=lambda a: (not a.get('principal'), a['persona_id']))
            out[silla] = s[0]['persona_id'] if s else None
            out[silla + '_otros'] = [a['persona_id'] for a in s[1:]]
            out[silla + '_confianza'] = s[0].get('confianza') if s else None
        return out

    caches_meta417 = {p.stem: leer(p, {}) for p in (APP / 'fuentes_paneles' / '_cache' / 'meta').glob('*.json')}
    cuentas417 = [str(x.get('cuenta', '')).removeprefix('act_') for x in caches_meta417.values() if isinstance(x, dict)]
    obj_app = OBJETIVOS.leer()[0]   # A4: base de la app (ficha y Clientes nuevos), la misma lectura para toda la app
    hoy = date.today()
    filas = []
    for c in cap['clientes']:
        cid = cap_a_app.get(c['id']) or c['id'].replace('_', '-')
        oa = (obj_app.get(cid) or {}).get('objetivo') or {}
        if oa.get('cargado'):   # A4: manda el objetivo cargado en la app sobre el del fichero de captación
            c['objetivo'] = {**(c.get('objetivo') or {}), 'coste_cita': oa.get('coste_cita'), 'cpl': oa.get('coste_lead'),
                             'origen': f"app · {alias.get(oa.get('quien'), oa.get('quien'))} · {oa.get('cuando')}"}
            if oa.get('coste_lead') is not None:
                c['cpl'] = {**(c.get('cpl') or {}), 'objetivo_usado': oa['coste_lead'], 'objetivo_origen': 'objetivo del cliente'}
        b = base.get(cid, {})
        m = c.get('meta') or {}
        g = c.get('ghl') or {}
        emb = (g.get('embudo') or {}) if g else {}
        cit = (g.get('citas') or {}) if g else {}
        cpc = c.get('coste_por_cita') or {}
        eq = equipo(cid)
        an = anuncios_de(anu['cuentas'].get(c['id']), bool((verdad.get(cid) or {}).get('nuevo', b.get('nuevo'))), inis)
        if an and act_num_de(m):
            for x in an['anuncios']:
                x['enlace'] = (f"https://adsmanager.facebook.com/adsmanager/manage/ads?act={act_num_de(m)}&selected_ad_ids={x['ad_id']}" if x.get('ad_id')
                               else f"https://adsmanager.facebook.com/adsmanager/manage/campaigns?act={act_num_de(m)}")
        leads_meta_7 = conteo((m.get('leads') or {}).get('7d'))
        cr = crm.get(cid) or {}
        ghl_7 = cr.get('leads_ghl_7d') if cr else None                # contactos nuevos no manuales en 7 días (Salud del CRM)
        tot = (totales.get(c['id']) or {}).get('contactos_total')
        v_cli = verdad.get(cid) or {}
        c14 = cit.get('14d') or {}
        cm = cit.get('mes_anterior') or {}
        medicion_crm = proyectar_crm(c, cr, tot, cap.get('generado'))
        leads_meta_7 = medicion_crm['leads_meta_7d']
        ghl_7 = medicion_crm['leads_ghl_7d']
        tot = medicion_crm['contactos_historia']
        sin_estado_14 = medicion_crm['sin_estado_14d']
        coste_cita_14 = cpc.get('coste_por_cita_14d')
        # Las reglas del lector anterior no prueban cohorte, vigencia de objetivos ni seguimiento.
        # Conservar las observaciones para contraste, sin convertirlas en un diagnóstico actual.
        diagnosticos_legacy = [dict(con_motivo(x), vigencia='referencia_legacy_no_validada')
                              for x in c.get('motivos', []) if isinstance(x, dict) and isinstance(x.get('texto'), str)]
        avisos_legacy = [dict(con_motivo(x), vigencia='referencia_legacy_no_validada')
                         for x in c.get('avisos', []) if isinstance(x, dict) and isinstance(x.get('texto'), str)]
        motivos = []
        avisos = [{'texto': medicion_crm['medicion_integracion']['nota'],
                   'clase_id': 'dato', 'clase': 'dato pendiente'}]
        if m.get('error') or g.get('error') or cr.get('error'):
            avisos.append({'texto': 'Lectura con errores: los recuentos afectados quedan desconocidos; contrastar la fuente antes de evaluar la cuenta.',
                           'clase_id': 'dato', 'clase': 'dato pendiente'})
        objetivo_cargado = bool(oa.get('cargado')) or bool((c.get('objetivo') or {}).get('coste_cita'))
        if not objetivo_cargado:
            avisos.append({'texto': 'Objetivo del cliente pendiente de confirmar: los umbrales del generador anterior son referencias históricas, no objetivos vigentes.',
                           'clase_id': 'dato', 'clase': 'dato pendiente', 'objetivo_sin_cargar': True})
        # Gasto de Meta / citas de un calendario no enlazado no es un coste de adquisición.
        alarma_cita = False
        if an and an['cansadas']:
            avisos.append({'texto': f"{an['cansadas']} anuncio{'s' if an['cansadas'] > 1 else ''} cansado{'s' if an['cansadas'] > 1 else ''} (dos señales a la vez): preparar el cambio de creatividad",
                           'clase_id': 'paid', 'clase': 'publicidad'})
        if an and an['problemas_total']:
            avisos.append({'texto': f"{an['problemas_total']} anuncio{'s' if an['problemas_total'] > 1 else ''} rechazado{'s' if an['problemas_total'] > 1 else ''} o con problemas en Meta",
                           'clase_id': 'paid', 'clase': 'publicidad'})
        severidad = 'dato'
        cuello = []
        fuga = None
        sin_uso = None
        if m.get('moneda') and m['moneda'] != 'EUR':
            avisos.append({'texto': f"La cuenta de Meta va en {m['moneda']}: su gasto no se suma al de la casa", 'clase_id': 'dato', 'clase': 'dato pendiente'})
        t = torre_por_app.get(cid)
        serie = [{'d': p['d'], 'gasto_meta': (p.get('meta') or [None, None])[0], 'leads_meta': (p.get('meta') or [None, None])[1]} for p in c.get('serie', [])]
        s7 = serie[:7]
        act_num = (m.get('cuenta_id') or '').replace('act_', '')
        sub = (c.get('ghl_subcuenta') or {}).get('id')
        gm = GADS_MUESTRA.get(cid)
        gp = GADS_PARADAS.get(cid)
        fila = {
            'cliente_id': cid, 'nombre': c['nombre'], 'id_captacion': c['id'], 'nicho': b.get('descripcion'),
            'coste_cpm_referencia_7d': cpm_referencia417(caches_meta417.get(cid), cid, m.get('cuenta_id'), cap.get('ventanas', {}).get('7d'), m.get('moneda'), activo=ACT.es_activo_id(cid) is True and ids_base417.count(cid) == 1 and cap_a_app.get(c.get('id')) == cid and sum(x.get('id') == c.get('id') for x in cap.get('clientes', []) if isinstance(x, dict)) == 1, cuenta_unica=cuentas417.count(str(m.get('cuenta_id', '')).removeprefix('act_')) == 1, error_fuente=bool(m.get('error'))),
            'nuevo': bool(v_cli['nuevo']) if 'nuevo' in v_cli else bool(b.get('nuevo')),
            'equipo': eq,
            'severidad': severidad, 'severidad_torre_reglas': c.get('severidad'), 'estado_evaluacion': 'sin_evaluacion', 'diagnosticos_legacy': diagnosticos_legacy, 'avisos_legacy': avisos_legacy, 'meta_activa': c.get('meta_activa'),
            'plataformas': sorted(set((c.get('plataformas') or []) + (['google'] if gm else []))),
            'cuello': cuello,
            'motivos': motivos, 'avisos': avisos,
            'objetivo': {'cargado': objetivo_cargado, 'origen': (c.get('objetivo') or {}).get('origen'),
                         'cpl_objetivo': (c.get('objetivo') or {}).get('cpl'), 'coste_cita_objetivo': (c.get('objetivo') or {}).get('coste_cita'),
                         'cpl_usado': (c.get('cpl') or {}).get('objetivo_usado'), 'cpl_usado_origen': (c.get('cpl') or {}).get('objetivo_origen'),
                         'leads_mes': oa.get('leads_mes'), 'ventas_mes': oa.get('ventas_mes'), 'quien': oa.get('quien'), 'cuando': oa.get('cuando'), 'accion_id': oa.get('accion_id')},
            'cuenta_meta': {'estado': m.get('estado_texto'), 'estado_num': m.get('estado_cuenta'), 'nombre_cuenta': m.get('cuenta_nombre'),
                            'ultimo_dia_con_gasto': m.get('ultimo_dia_con_gasto'), 'error': m.get('error'),
                            'enlace': f'https://adsmanager.facebook.com/adsmanager/manage/campaigns?act={act_num}' if act_num else None,
                            'moneda': m.get('moneda'), 'zona_horaria': m.get('zona_horaria'), 'convertida_a_madrid': m.get('convertida_a_madrid')},
            'leads': {k: None if m.get('error') else conteo(v) for k, v in (m.get('leads') or {}).items()}, 'gasto': m.get('gasto'), 'cpl': m.get('cpl'),
            'cpl_resumen': {k: (c.get('cpl') or {}).get(k) for k in ('ref', 'ref_base', 'delta_pct', 'fiable', 'veces_objetivo', 'nota_muestra')},
            'muestra': {'leads_7d': leads_meta_7, 'leads_7d_prev': (m.get('leads') or {}).get('7d_prev'), 'suficiente': (c.get('cpl') or {}).get('fiable'),
                        'nota': (c.get('cpl') or {}).get('nota_muestra') or (None if (c.get('cpl') or {}).get('fiable') else 'Referencia anterior del contador Meta: muestra y unidad pendientes de contraste')},
            'presupuesto_ads': c.get('presupuesto'),
            'metas': c.get('metas') or [],
            'serie': serie,
            'campanas': [{**x, 'enlace': (f'https://adsmanager.facebook.com/adsmanager/manage/campaigns?act={act_num}&selected_campaign_ids={x["campaign_id"]}'
                                          if act_num and x.get('campaign_id') else None)} for x in (c.get('campanas') or [])],
            'ghl': {'conectado': bool(sub), 'subcuenta': (c.get('ghl_subcuenta') or {}).get('nombre'),
                    'enlace': f'https://app.gohighlevel.com/v2/location/{sub}/opportunities/list' if sub else None,
                    'embudo': emb or None, 'citas': cit or None, 'calendarios': g.get('calendarios') if g else None},
            'coste_por_cita': {**cpc, 'alarma_100': False, 'medicion': 'referencia_legacy_sin_cohorte_enlazada'} if cpc else None,
            'despacho': {
                'leads_meta_7d': leads_meta_7, 'leads_ghl_7d': ghl_7,
                'pct_llegan_crm': None, 'medicion_integracion': medicion_crm['medicion_integracion'],
                'fuga': fuga, 'contactos_historia': tot, 'subcuenta_sin_uso': sin_uso,
                'definicion_llegan': ((leer(DATA / 'crm' / 'crm.json', {}) or {}).get('reglas') or {}).get('lead') or 'Contactos nuevos con origen formulario o anuncio (Salud del CRM)',
                'cohorte_30d': emb.get('cohorte_30d'), 'estancados_72h': emb.get('estancados_72h'), 'pct_estancado': emb.get('pct_estancado'),
                'horas_max_parado': emb.get('horas_max_parado'), 'pct_en_nuevo': emb.get('pct_en_nuevo'), 'sin_avance_90d': emb.get('sin_avance_90d'),
                'bolsa_historica_en_nuevo': emb.get('bolsa_historica_en_nuevo'),
                'citas_14d': c14.get('agendadas'), 'celebradas_14d': c14.get('celebradas'), 'no_vino_14d': c14.get('no_presentadas'),
                'sin_estado_14d': sin_estado_14, 'asistencia_14d': c14.get('asistencia_pct'),
                'asistencia_mes_anterior': cm.get('asistencia_pct'), 'citas_mes_anterior': cm.get('agendadas'),
                'proximas': cit.get('proximas') if cit else None,
                'velocidad': None, 'velocidad_porque': 'Velocidad de contacto e intentos (el despacho llama en 1 hora o menos y hace 4 intentos en 72 h): hace falta leer las conversaciones de cada lead; llega con los avisos en tiempo real de GoHighLevel.',
            },
            'quincenal': {
                'periodo': cap['ventanas']['14d'], 'leads_14d': (m.get('leads') or {}).get('14d'), 'gasto_14d': (m.get('gasto') or {}).get('14d'),
                'cpl_14d': (m.get('cpl') or {}).get('14d'), 'citas_14d': c14.get('agendadas'), 'celebradas_14d': c14.get('celebradas'),
                'asistencia_14d': c14.get('asistencia_pct'), 'coste_por_cita_14d': None, 'coste_por_cita_referencia_14d': coste_cita_14, 'sin_estado_14d': sin_estado_14,
            },
            'historia': {
                'torre_17sep': {'severidad': t['severidad'], 'leads_7d': t.get('leads_7d'), 'gasto_7d': t.get('spend_7d'), 'cpl_7d': t.get('cpl_7d'),
                                'motivos': [sin_euros(x['texto']) for x in t.get('motivos', [])], 'gasto_motivos': [x['texto'] for x in t.get('motivos', [])],
                                'pm_escrito_a_mano': t.get('pm')} if t else None,
                'hace_4_semanas': {'periodo': [s7[0]['d'], s7[-1]['d']], 'leads_meta': suma_observada([conteo(p['leads_meta']) for p in s7], 1),
                                   'gasto_meta': suma_observada([p['gasto_meta'] for p in s7], 2)} if len(s7) == 7 else None,
            },
            'anuncios': an,
            'google_ads': ({'muestra': 'muestra manual', 'periodo': GADS_PERIODO, 'cuenta': gm[0], 'coste': gm[1], 'clics': gm[2],
                            'impresiones': gm[3], 'conversiones': gm[4], 'ultimo_dia_con_gasto': gm[5],
                            'nota': 'Muestra manual de septiembre (Windsor, consultada el 2-oct). Sin campañas ni serie diaria hasta tener la clave de Windsor.'} if gm else
                           {'muestra': 'muestra manual', 'parada': True, 'cuenta': gp[0], 'ultimo_dia_con_gasto': gp[1], 'gasto_2026': gp[2],
                            'nota': 'Windsor ve la cuenta sin gasto reciente: campaña parada, no fallo de conexión.'} if gp else
                           {'muestra': 'fuera de Windsor', 'nota': 'Tiene Google Ads en Looker con el conector oficial y no está en Windsor: conectar.'} if cid in GADS_FUERA_DE_WINDSOR else None),
            'tiktok': None,
        }
        filas.append(fila)

    # clientes que solo tienen Google Ads y no están en captacion.json
    vistos = {f['cliente_id'] for f in filas}
    for cid, gm in GADS_MUESTRA.items():
        if cid in vistos:
            continue
        b = base.get(cid, {})
        filas.append({'cliente_id': cid, 'nombre': b.get('nombre', cid), 'solo_google': True, 'equipo': equipo(cid), 'severidad': 'inactivo',
                      'plataformas': ['google'], 'cuello': [], 'motivos': [], 'avisos': [{'texto': 'Solo Google Ads: muestra manual de septiembre hasta tener la clave de Windsor.', 'clase_id': 'dato', 'clase': 'dato pendiente'}],
                      'google_ads': {'muestra': 'muestra manual', 'periodo': GADS_PERIODO, 'cuenta': gm[0], 'coste': gm[1], 'clics': gm[2], 'impresiones': gm[3], 'conversiones': gm[4], 'ultimo_dia_con_gasto': gm[5]}})

    # resumen de la casa (sin dinero fuera de claves de dinero)
    act = [f for f in filas if f.get('meta_activa')]
    juzg = [f for f in act if (f.get('cpl_resumen') or {}).get('ref') is not None]
    en_techo = [f for f in juzg if f['cpl_resumen']['ref'] <= TECHO_CPL]
    calc_cita = [f for f in act if (f.get('coste_por_cita') or {}).get('coste_por_cita_14d') is not None]
    resumen = {
        'clientes_con_meta': sum(1 for f in filas if f.get('cuenta_meta')), 'meta_activa': len(act),
        'por_gravedad': {k: sum(1 for f in filas if f['severidad'] == k) for k in ('critico', 'atencion', 'ok', 'dato', 'inactivo')},
        'objetivos_cargados': sum(1 for f in act if (f.get('objetivo') or {}).get('cargado')),
        'cuentas_juzgables_cpl': None, 'cuentas_en_techo_cpl': None,
        'referencia_legacy_cuentas_cpl': {'con_ratio': len(juzg), 'en_techo_35': len(en_techo), 'vigencia': 'referencia_legacy_no_validada'},
        'cuentas_con_coste_por_cita': len(calc_cita),
        'gasto_7d_casa': round(sum((f.get('gasto') or {}).get('7d') or 0 for f in filas if (f.get('cuenta_meta') or {}).get('moneda') in (None, 'EUR')), 2),
        'gasto_mes_anterior_casa': round(sum((f.get('gasto') or {}).get('mes_anterior') or 0 for f in filas if (f.get('cuenta_meta') or {}).get('moneda') in (None, 'EUR')), 2),
        'leads_7d_casa': suma_observada([conteo((f.get('leads') or {}).get('7d')) for f in filas], 1),
        'leads_7d_casa_medicion': 'contador_meta_legacy_no_cualificados_ni_cohorte_crm',
    }
    # V2 (B-A3) · UNA cartera de publicidad por trafficker, con nombre, para Captación, Mi día y Personas › Carga.
    # Sale de la verdad única (carteras[] silla trafficker) cruzada con las filas de Captación; gravedad = la del cliente.
    verdad_doc = leer(DATA / 'verdad' / 'clientes.json', {}) or {}
    por_fila = {f['cliente_id']: f for f in filas}
    carteras_pub = {}
    for cv in verdad_doc.get('carteras') or []:
        if cv.get('silla') != 'trafficker':
            continue
        pri = list(cv.get('principal') or [])
        con_meta = [x for x in pri if x in por_fila and not por_fila[x].get('solo_google')]
        carteras_pub[cv['persona_id']] = {
            'cartera': len(pri), 'apoyo': len(cv.get('apoyo') or []),
            'con_meta': len(con_meta),
            'meta_encendida': sum(1 for x in con_meta if por_fila[x].get('meta_activa')),
            'criticos': sum(1 for x in con_meta if (verdad.get(x) or {}).get('gravedad') == 'critico'),
            'atencion': sum(1 for x in con_meta if (verdad.get(x) or {}).get('gravedad') == 'atencion'),
            'publicidad_urgente': sum(1 for x in con_meta if por_fila[x].get('severidad') == 'critico'),
            'principal': pri, 'apoyo_ids': list(cv.get('apoyo') or []), 'con_meta_ids': con_meta,
        }
    criticos_casa = sorted(f['cliente_id'] for f in filas if not f.get('solo_google') and (verdad.get(f['cliente_id']) or {}).get('gravedad') == 'critico')
    out = {
        'formato': 1, 'generado': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'carteras_publicidad': carteras_pub,
        'definiciones_publicidad': {
            'cartera': 'Clientes que la persona lleva como trafficker principal (verdad única, carteras[]).',
            'apoyo': 'Clientes en los que ayuda sin llevarlos (no suman a su cartera).',
            'con_meta': 'De su cartera, los que tienen cuenta de Meta en Captación («Mis cuentas»).',
            'meta_encendida': 'De esos, los que tienen pauta activa esta semana.',
            'criticos': 'De esos, los que tienen gravedad «crítico» en la verdad única (la de toda la app).',
            'criticos_casa': 'Cuentas de Meta de la casa con el cliente en crítico (verdad única). Es la cifra de «Fuegos» y la suma de «Por trafficker» más las cuentas sin trafficker.',
        },
        'criticos_casa': criticos_casa,
        'captacion_generado': cap['generado'], 'anuncios_generado': anu.get('generado'), 'datos_hasta': cap['datos_hasta'],
        'ventanas': cap['ventanas'], 'pct_mes': cap.get('pct_mes'), 'dias_transcurridos': cap.get('dias_transcurridos'),
        'parametros': {'techo_cpl': TECHO_CPL, 'alarma_cita': ALARMA_CITA, 'arranque_cita': ARRANQUE_CITA, 'min_leads_cpl': 4, 'estancado_horas': 72,
                       'fatiga': {'frecuencia': FATIGA_FREC, 'caida_ctr_pct': FATIGA_CAIDA_CTR, 'coste_x': FATIGA_COSTE_X},
                       'ganador': {'veces': GANADOR_VECES, 'arranque': GANADOR_ARRANQUE}, 'rojos_trafficker': ROJOS_TRAFFICKER,
                       'asistencia': ASISTENCIA, 'cuentas_trafficker': CUENTAS_TRAFFICKER,
                       'reglas_torre': cap['parametros'].get('reglas_inferidas')},
        'fuentes': [
            {'id': 'meta', 'fuente': 'Meta Ads', 'hora': cap['generado'], 'medicion': 'copia', 'nota': 'Marketing API, token del llavero, solo lectura (captacion.py)',
             **estado_fuente(cap['generado'], LIMITE_LECTOR_H, n_meta_err, n_meta, 'cuentas de Meta sin responder')},
            {'id': 'ghl', 'fuente': 'GoHighLevel (embudo y citas)', 'hora': cap['generado'], 'medicion': 'copia', 'nota': 'App privada de agencia, solo lectura (captacion.py)',
             **estado_fuente(cap['generado'], LIMITE_LECTOR_H, n_ghl_err, n_ghl, 'subcuentas de GHL sin responder')},
            {'id': 'anuncios', 'fuente': 'Meta Ads (anuncios)', 'hora': anu.get('generado'), 'medicion': 'copia' if anu.get('generado') else 'no', 'nota': 'anuncios_meta.py, solo lectura',
             **estado_fuente(anu.get('generado'), LIMITE_ANUNCIOS_H, n_anu_err, len(anu.get('cuentas') or {}), 'cuentas sin leer sus anuncios')},
            {'id': 'google_ads', 'fuente': 'Google Ads (Windsor)', 'hora': '2026-10-02 12:00', 'medicion': 'medias', 'nota': 'Muestra manual de septiembre: falta la clave de Windsor'},
            {'id': 'tiktok', 'fuente': 'TikTok Ads (Windsor)', 'hora': None, 'medicion': 'no', 'nota': 'Sin datos: la consulta se cortó; llega con la clave de Windsor'},
            {'id': 'torre', 'fuente': 'Torre de Control (foto 17-sep)', 'hora': '2026-09-17 06:00', 'medicion': 'historica', 'nota': 'Solo para la historia y la paridad'},
        ],
        'personas': {pid: alias.get(pid, pid) for f in filas for pid in [f['equipo'].get(s) for s in ('trafficker', 'account', 'crm')] + sum((f['equipo'].get(s + '_otros', []) for s in ('trafficker', 'account', 'crm')), []) if pid},
        'resumen': resumen,
        'clientes': sorted(filas, key=lambda f: (['critico', 'atencion', 'ok', 'dato', 'inactivo'].index(f['severidad']), f['nombre'])),
        'google_ads_sin_cliente': GADS_SIN_CLIENTE,
        'paridad_torre': [{'cliente_id': TORRE_A_APP[t['id']], 'nombre': t['nombre'], 'torre': t['severidad'], 'pm_escrito_a_mano': t.get('pm'),
                           'app': next((f['severidad'] for f in filas if f['cliente_id'] == TORRE_A_APP[t['id']]), None)}
                          for t in (seed or {}).get('clientes', []) if t['id'] in TORRE_A_APP],
    }
    # Auditoría 35 (A5): Captación nunca cae a 0 clientes con dato por una lectura caída. Si antes había clientes con
    # cuenta de Meta y ahora no queda ninguno (o ningún cliente), no se escribe: se queda el último dato bueno con su
    # hora y se sale con error (la tubería no lo sella «bien» y avisa).
    previo = leer(SALIDA, {}) or {}
    antes_n = ((previo.get('resumen') or {}).get('clientes_con_meta')) or 0
    if antes_n >= 4 and (not filas or not resumen['clientes_con_meta']):
        print(f"CAPTACIÓN SIN DATO: {len(filas)} clientes y {resumen['clientes_con_meta']} con Meta (antes {antes_n}) · "
              f"se queda data/captacion/captacion.json de {previo.get('generado')}", file=sys.stderr)
        sys.exit(3)
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    tmp = SALIDA.with_suffix('.tmp')
    tmp.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    tmp.replace(SALIDA)
    r = resumen
    print(f"Listo: {SALIDA.relative_to(APP)} · {len(filas)} clientes ({r['meta_activa']} con Meta activa) · "
          f"gravedad {r['por_gravedad']} · {r['por_gravedad'].get('dato', 0)} señales pendientes de contraste (sin unión Meta→CRM)")


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""generar_hilos.py · Bandeja v5 (3-oct-2026): el hilo legible de cada correo, para leerlo en la app sin ir a Desk.

Desde el 3-oct (tarde) cubre TODOS los correos abiertos de la Bandeja (data/bandeja/bandeja.json), no solo los 40 que leyó
la IA. Dos orígenes, por este orden:
  1. La caché por ticket de Desk (fuentes_bandeja/_cache_hilos/<número>.json), que rellena esta misma herramienta con
     --desk: SOLO LECTURA de Zoho Desk (zh.py, llavero), con un tope de tickets y de llamadas por vuelta para no saturar
     la API. Un ticket se vuelve a leer solo si su último correo del cliente («desde») o su estado en Desk han cambiado.
     Lo que se guarda en la caché ya va limpio (sin correos, teléfonos, credenciales ni pies legales).
  2. Los hilos que ya bajó la IA (data/ia/_privado/hilos.json: solo servidor), para los que aún no están en la caché.

Escribe data/bandeja/hilos.json con lo justo para leer: fecha, quién (entrante o saliente), nombre y el texto LIMPIO:
  · sin el pie legal («NOTA LEGAL», «PROTECCIÓN DE DATOS», «LEGAL NOTE»…),
  · sin la cadena citada del correo anterior («De: … Enviado el: …», «El … escribió:», «-----Original…»),
  · sin correos ni teléfonos (la puerta de secretos no los deja pasar).
Cada fila lleva cliente_id: servir.py solo la manda a quien ve ese cliente (las sin cliente, solo Operaciones y Dirección,
como en bandeja.json). Dado de alta en reglas_permisos.json → datos_de_modulo «bandeja/hilos».
Sin --desk no llama a ninguna herramienta (así lo lanza generar_bandeja.py al terminar).

  python3 fuentes_bandeja/generar_hilos.py                       # sin red: caché + IA → hilos.json
  python3 fuentes_bandeja/generar_hilos.py --desk                # una vuelta de lectura de Desk (tope 150 tickets)
  python3 fuentes_bandeja/generar_hilos.py --desk --tope 300 --max-llamadas 2500
  python3 fuentes_bandeja/generar_hilos.py --desk --hasta-completar   # vueltas seguidas hasta tener todos (con pausa)
"""
import argparse
import html
import json
import os
import re
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
import pathlib as _pl_l27, sys as _sys_l27  # L-27: rutas del Mac por config.py
if str(_pl_l27.Path(__file__).resolve().parents[1]) not in _sys_l27.path:
    _sys_l27.path.append(str(_pl_l27.Path(__file__).resolve().parents[1]))
import config as _cfg  # noqa: E402

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent
sys.path.insert(1, str(RAIZ))
ORIGEN = RAIZ / 'data/ia/_privado/hilos.json'
BANDEJA = RAIZ / 'data/bandeja/bandeja.json'
SALIDA = RAIZ / 'data/bandeja/hilos.json'
CACHE = AQUI / '_cache_hilos'
DESK = 'https://desk.zoho.eu/api/v1'
MAX_MENSAJES = 20          # los 20 últimos mensajes del hilo (como la IA)
TOPE_TICKETS = 150         # tickets leídos de Desk por vuelta
MAX_LLAMADAS = 1500        # llamadas a la API de Desk por vuelta (cada ticket: 1 + una por mensaje)
HILOS_A_LA_VEZ = 3

_CORREO = re.compile(r'[\w.+-]+@[\w-]+(?:\.[\w-]+)+')
_TEL = re.compile(r'(?:\+?\d[\d\s.\-]{7,}\d)')
_PIE = re.compile(r'(NOTA LEGAL|PROTECCI[ÓO]N DE DATOS\s*[-:.]|De conformidad con (?:el|lo dispuesto|la normativa|el Reglamento)|REGLAMENTO \(UE\) 2016/679|'
                  r'(?:es|son|tienen? car[áa]cter) (?:estrictamente |totalmente )?confidencial|Agencia Espa[ñn]ola de Protecci[óo]n de Datos|puede (?:poner|presentar) (?:una )?reclamaci[óo]n|si (?:lo|la|usted lo) ha recibido por error|ha recibido este (?:correo|mensaje) por error|'
                  r'Puede (?:acceder a|consultar) (?:la )?informaci[óo]n (?:adicional|sobre)|Este (?:mensaje|correo)(?: electr[óo]nico)? y (?:cualquier|sus|los) (?:archivo|fichero|anexo|adjunto|documento)|'
                  r'Per a informaci[óo] sobre protecci[óo] de dades|Este (?:e-?mail|correo(?: electr[óo]nico)?|mensaje) y,? (?:en su caso|la informaci[óo]n)|informaci[óo]n de car[áa]cter confidencial|Piense en el medio ambiente|se ruega que se notifique|Si (?:usted )?no es el destinatario|Si considera que sus derechos|Informaci[óo] addicional:|Pot obtenir informaci[óo]|Pol[íi]tica de [Pp]rivacidad|INFORMACI[ÓO]N CONFIDENCIAL|LEGAL NOTE|AVISO LEGAL|AVISO (?:DE|SOBRE) CONFIDENCIALIDAD|CONFIDENCIALIDAD:|-{8,}|'
                  r'Este (?:correo|mensaje)(?: electr[óo]nico)?(?: y sus (?:anexos|adjuntos))? (?:puede contener|es confidencial|contiene|va dirigido|se dirige)|'
                  r'La informaci[óo]n (?:contenida|incluida) en (?:este|el presente)|De acuerdo con (?:lo establecido en )?la (?:legislaci[óo]n|normativa) vigente|'
                  r'En cumplimiento de(?:l| la| lo)? (?:Reglamento|normativa|Ley|dispuesto)|Le informamos (?:de )?que (?:sus|los) datos|Antes de imprimir|'
                  r'[Ss]in la autorizaci[óo]n de|Este mensaje y (?:los|sus) archivos|De acuerdo con lo establecido en el art[íi]culo 13|'
                  r'(?:Los|Sus) datos (?:de car[áa]cter )?personales|datos de car[áa]cter personal|Protecci[óo]n de datos\.|tiene la consideraci[óo]n de responsable|Responsable del tratamiento|Informaci[óo]n b[áa]sica (?:sobre|de) protecci[óo]n de datos|'
                  r'Confidencialidad\.|La informaci[óo] continguda|Li recordem que les seves dades|Les (?:seves )?dades personals|AV[ÍI]S LEGAL|'
                  r'Aquest (?:missatge|correu)(?: electr[òo]nic)? (?:i|pot|[ée]s|cont[ée]|va adre)|Este correo electr[óo]nico y, en su caso)', re.I)
_CITA = re.compile(r'(\bDe:\s.{1,120}?\s(?:Enviado(?: el)?|Fecha|Sent):|\bDesde:\s.{1,120}?\sPara:|\bFrom:\s.{1,120}?\sSent:|\bEl\s.{4,140}?\sescribi[óo]:|\bOn\s.{4,140}?\swrote:|-{3,}\s*(?:Mensaje original|Original Message)|-{3,}\s*(?:en|el|on)\s+\w{3},\s*\d|_{6,})', re.I | re.S)
_SOLO_PIE = re.compile(r'\s*(?:\S+\s+)?(?:NOTA LEGAL|AVISO LEGAL|LEGAL NOTE|PROTECCI[ÓO]N DE DATOS|AVISO (?:DE|SOBRE) CONFIDENCIALIDAD)', re.I)
_CREDENCIAL = re.compile(r"(?i)\b(usuari[oa]s?|user(?:name)?|login|contrase(?:ñ|n)a|password|passw(?:or)?d|pass|clave|pwd|pin)(\s*[:=]\s*)(\S+)")


def _patrones():
    try:
        import escaner_secretos as E  # noqa: E402
        return E.PATRONES
    except Exception:
        return []


PATRONES = _patrones()


def limpio(t):
    t = str(t or '').replace('\r', '')
    if _SOLO_PIE.match(t):
        return ''                         # el mensaje entero es el pie legal («Enviado! NOTA LEGAL…»): no aporta nada
    for rx in (_CITA, _PIE):
        # el primer corte a partir del carácter 20 (si empieza por ahí, el mensaje entero es cita o pie: se deja y se ve)
        m = next((m for m in rx.finditer(t) if m.start() > (0 if rx is _PIE else 20)), None)
        if m:
            t = t[:m.start()]

    t = _TEL.sub('…', _CORREO.sub('[correo]', t))
    t = re.sub(r'[ \t]+', ' ', t)
    # los correos de Desk llegan en una sola línea: se parte en párrafos por frases de saludo y de cierre
    t = re.sub(r'\s+(Un saludo,|Saludos,|Gracias,|Muchas gracias|Quedo atent[oa]\.?|Atentamente,?)', r'\n\n\1', t)
    t = re.sub(r'^(Hola[^,\n]{0,40},|Buenos días[^,\n]{0,40},|Buenas tardes[^,\n]{0,40},|Saludos [^,\n]{0,30},)\s*', r'\1\n\n', t)
    return t.strip()


def limpio_desk(t):
    """Texto de un hilo de Desk tal y como se guarda en la caché: sin HTML, credenciales, secretos, citas ni pie legal."""
    t = html.unescape(re.sub(r'<[^>]+>', ' ', str(t or '')))
    t = _CREDENCIAL.sub(r'\1\2[quitado]', t)
    for nombre, pat in PATRONES:
        t = pat.sub('[correo]' if nombre == 'correo' else '…' if nombre == 'telefono' else '[quitado]', t)
    t = re.sub(r'[ \t\xa0]+', ' ', t)
    t = re.sub(r'\n\s*\n+', '\n\n', t).strip()
    return limpio(t)[:4000]


def _nombre(de):
    de = _CORREO.sub('', str(de or '')).strip(' <>"\'')
    for nombre, pat in PATRONES:
        de = pat.sub('', de)
    return de.strip()[:80]


# ------------------------------------------------------------------------------------------------ caché por ticket
def _fichero_cache(numero):
    return CACHE / (re.sub(r'[^\w.-]', '_', str(numero)) + '.json')


def leer_cache(numero):
    try:
        return json.loads(_fichero_cache(numero).read_text())
    except Exception:
        return None


def _huella(fila):
    """Lo que hace que un hilo cambie: el último correo del cliente y el estado del ticket en Desk."""
    return f"{fila.get('desde') or ''}|{fila.get('estado_desk') or ''}"


def guardar_cache(numero, entrada):
    CACHE.mkdir(parents=True, exist_ok=True)
    f = _fichero_cache(numero)
    tmp = f.with_suffix('.tmp')
    tmp.write_text(json.dumps(entrada, ensure_ascii=False, indent=1))
    try:
        import escaner_secretos as E  # noqa: E402  la caché tampoco guarda correos ni teléfonos (escaner --proyecto)
        if E.escanear_fichero(tmp):
            tmp.unlink()
            return False
    except ImportError:
        pass
    os.replace(tmp, f)
    return True


def _urgencia(x):
    """El orden de la Bandeja: lo vivo antes que lo viejo o automático; quejas, rojo y más horas arriba."""
    return (bool(x.get('auto')) or bool(x.get('boletin')), bool(x.get('viejo')), not x.get('cliente_id'),
            not x.get('queja'), x.get('gravedad') != 'rojo', -(x.get('horas') or 0))


def por_leer(correos):
    """(sin caché, con caché cambiada): primero los que nunca se leyeron, cada grupo por urgencia."""
    nuevos, cambiados = [], []
    for x in correos:
        c = leer_cache(x['numero'])
        if not c or c.get('error'):
            nuevos.append(x)
        elif c.get('huella') != _huella(x):
            cambiados.append(x)
    return sorted(nuevos, key=_urgencia) + sorted(cambiados, key=_urgencia)


class Desk:
    """Lectura de Zoho Desk (solo GET) con un contador de llamadas que corta la vuelta al llegar al tope."""

    def __init__(self, max_llamadas):
        sys.path.insert(0, str(_cfg.HERRAMIENTAS / 'zoho'))
        try:
            import config  # noqa: E402
            sys.path.insert(0, str(config.HERRAMIENTAS / 'zoho'))
        except Exception:
            pass
        import zh  # noqa: E402
        self.tk, _ = zh.acceso()
        self.max = max_llamadas
        self.n = 0
        self.parar = None           # motivo si la API pide parar (429) o el token cae (401)
        self._c = threading.Lock()
        o = self.g('/organizations')
        self.oid = str(((o or {}).get('data') or [{}])[0].get('id') or '')
        if not self.oid:
            raise RuntimeError(f"Desk no da la organización ({(o or {}).get('_error')})")

    def g(self, ruta):
        with self._c:
            if self.parar or self.n >= self.max:
                return {'_error': 'tope'}
            self.n += 1
        h = {'Authorization': 'Zoho-oauthtoken ' + self.tk}
        if getattr(self, 'oid', None):
            h['orgId'] = self.oid
        for intento in range(2):
            try:
                return json.load(urllib.request.urlopen(urllib.request.Request(DESK + ruta, headers=h), timeout=60))
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    self.parar = 'la API de Desk pide esperar (429)'
                elif e.code == 401:
                    self.parar = 'el token de Desk no vale (401)'
                return {'_error': e.code}
            except Exception as e:          # red: un reintento
                if intento:
                    return {'_error': type(e).__name__}
                time.sleep(2)
        return {'_error': 'red'}

    def hilo(self, fila):
        tid = (fila.get('url') or '').rstrip('/').split('/')[-1]
        if not tid.isdigit():
            return {'error': 'sin id de ticket'}
        conv = self.g(f'/tickets/{tid}/conversations?from=1&limit=100')
        if conv.get('_error'):
            return {'error': conv['_error']}
        hilos = sorted([m for m in conv.get('data', []) if m.get('type') == 'thread'], key=lambda m: m.get('createdTime') or '')[-MAX_MENSAJES:]
        msgs = []
        for m in hilos:
            th = self.g(f"/tickets/{tid}/threads/{m['id']}?include=plainText")
            if th.get('_error') == 'tope' or self.parar:
                return {'error': 'tope'}         # a medias no se guarda: en la vuelta siguiente se lee entero
            texto = th.get('plainText') or th.get('content') or m.get('summary') or ''
            autor = th.get('author') or m.get('author') or {}
            de = _nombre(autor.get('name') or autor.get('firstName') or '')
            nuestro = m.get('direction') != 'in' or str(autor.get('type') or '').upper() == 'AGENT' or 'ranking online' in de.lower()
            msgs.append({'fecha': (m.get('createdTime') or '')[:16].replace('T', ' '),
                         'direccion': 'saliente' if nuestro else 'entrante', 'de': de,
                         'texto': limpio_desk(texto), 'cortado': len(str(texto)) > 4000})
        return {'mensajes': msgs, 'ticket_id': tid}


def leer_desk(correos, tope, max_llamadas):
    """Una vuelta: lee de Desk hasta `tope` tickets pendientes (o `max_llamadas` llamadas). Devuelve un resumen."""
    pend = por_leer(correos)
    if not pend:
        return {'leidos': 0, 'pendientes': 0, 'llamadas': 0, 'parada': None}
    d = Desk(max_llamadas)
    lote = pend[:tope]
    hechos, fallos = [0], [0]
    candado = threading.Lock()

    def uno(x):
        if d.parar or d.n >= d.max:
            return
        r = d.hilo(x)
        if r.get('error') == 'tope':
            return
        entrada = {'numero': x['numero'], 'huella': _huella(x), 'leido': datetime.now().strftime('%Y-%m-%d %H:%M'),
                   'fuente': 'Zoho Desk (lectura)', **r}
        if guardar_cache(x['numero'], entrada) and not r.get('error'):
            with candado:
                hechos[0] += 1
        else:
            with candado:
                fallos[0] += 1

    with ThreadPoolExecutor(HILOS_A_LA_VEZ) as ex:
        list(ex.map(uno, lote))
    return {'leidos': hechos[0], 'fallos': fallos[0], 'pendientes': len(por_leer(correos)), 'llamadas': d.n, 'parada': d.parar}


# ------------------------------------------------------------------------------------------------ salida
def construir(correos):
    try:
        ia = (json.loads(ORIGEN.read_text()) or {}).get('hilos', {})
    except Exception:
        ia = {}
    filas = {c['numero']: c for c in correos}
    out, de_desk, de_ia, horas = [], 0, 0, []
    numeros = list(filas) + [n for n in sorted(ia) if n not in filas]
    for num in numeros:
        f = filas.get(num) or {}
        cid = f.get('cliente_id', (ia.get(num) or {}).get('cliente_id'))
        c = leer_cache(num)
        if c and not c.get('error') and c.get('mensajes') is not None:
            msgs = [dict(m, texto=limpio(m.get('texto'))) for m in c['mensajes'] if limpio(m.get('texto'))]
            origen = 'desk'
            horas.append(c.get('leido'))
        elif num in ia:
            msgs = []
            for m in ia[num].get('mensajes') or []:
                texto = limpio(m.get('texto'))
                if not texto:
                    continue
                msgs.append({'fecha': m.get('fecha'), 'direccion': 'saliente' if m.get('direccion') == 'saliente' else 'entrante',
                             'de': _CORREO.sub('[correo]', str(m.get('de') or ''))[:80], 'texto': texto[:4000],
                             'cortado': len(str(m.get('texto') or '')) >= 3000})
            origen = 'ia'
        else:
            continue
        if not msgs:
            continue
        de_desk += origen == 'desk'
        de_ia += origen == 'ia'
        fila = {'numero': num, 'cliente_id': cid or None, 'mensajes': msgs[-MAX_MENSAJES:]}
        if not cid:
            fila['persona_id'] = 'mili'      # como en bandeja.json: sin cliente, solo Operaciones y Dirección
        out.append(fila)
    horas = sorted(h for h in horas if h)
    generado = horas[-1] if horas else ((json.loads(ORIGEN.read_text()).get('generado')) if ORIGEN.exists() else None)
    return {'formato': 1, 'generado': generado,
            'fuente': 'Hilos de Zoho Desk (lectura por ticket, con caché) y, si aún no se han leído, los que leyó la IA; '
                      'limpios de pies legales, citas, correos y teléfonos',
            'cobertura': {'correos_abiertos': len(filas), 'con_hilo': sum(1 for x in out if x['numero'] in filas),
                          'de_desk': de_desk, 'de_ia': de_ia, 'leido_desde': horas[0] if horas else None},
            'hilos': out}


def main(argv=None):
    ap = argparse.ArgumentParser(description='Hilos legibles de la Bandeja')
    ap.add_argument('--desk', action='store_true', help='leer de Desk los tickets sin caché o cambiados (solo lectura)')
    ap.add_argument('--tope', type=int, default=TOPE_TICKETS, help='tickets por vuelta')
    ap.add_argument('--max-llamadas', type=int, default=MAX_LLAMADAS, help='llamadas a la API por vuelta')
    ap.add_argument('--hasta-completar', action='store_true', help='vueltas seguidas (con 60 s de pausa) hasta leerlos todos')
    a = ap.parse_args([] if argv is None else argv)
    try:
        correos = json.loads(BANDEJA.read_text()).get('correos', [])
    except Exception:
        correos = []
    if a.desk:
        while True:
            r = leer_desk(correos, a.tope, a.max_llamadas)
            print(f"Desk · {r['leidos']} hilos leídos · {r.get('fallos', 0)} con error · {r['llamadas']} llamadas · "
                  f"quedan {r['pendientes']}{' · parada: ' + r['parada'] if r.get('parada') else ''}")
            if not a.hasta_completar or not r['pendientes'] or r.get('parada') or not r['leidos']:
                break
            time.sleep(60)
    doc = construir(correos)
    import escaner_secretos as E  # noqa: E402  puerta de secretos antes de escribir
    tmp = SALIDA.with_suffix('.tmp')
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=1))
    hall = E.escanear_fichero(tmp)
    if hall:
        tmp.unlink()
        print('PUERTA DE SECRETOS: hilos.json no se escribe.', hall[:5])
        return 2
    os.replace(tmp, SALIDA)
    cb = doc['cobertura']
    print(f"hilos.json · {len(doc['hilos'])} hilos ({cb['con_hilo']} de {cb['correos_abiertos']} correos abiertos; "
          f"{cb['de_desk']} de Desk, {cb['de_ia']} de la IA) · {sum(len(x['mensajes']) for x in doc['hilos'])} mensajes")
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))

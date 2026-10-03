#!/usr/bin/env python3
"""fuentes_ia/extraer_hilos.py · N3 (IA) · 2-oct-2026.

Elige los correos más urgentes de la Bandeja (data/bandeja/bandeja.json) y baja su hilo de Zoho Desk
(SOLO LECTURA, con ~/RO_HERRAMIENTAS/zoho/zh.py) para que la IA tenga el contexto del correo.

Orden de urgencia (el mismo de la Bandeja): quejas arriba; luego en rojo; luego más horas sin contestar.
Fuera: avisos automáticos, correos sin cliente y los de más de 22 días laborables (salvo quejas).
Se incluyen además todos los de la cartera de Lucía que cumplan lo anterior (prueba de permisos).

Salida: data/ia/_privado/hilos.json (no se sirve nunca como fichero; solo lo lee ia.py en el servidor).
Correos y teléfonos se borran del texto (puerta de secretos); se guarda el nombre de quien escribe.

Uso: python3 fuentes_ia/extraer_hilos.py [--n 40]
"""
import html
import json
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

AQUI = Path(__file__).resolve().parent
APP = AQUI.parent
sys.path.insert(0, str(APP))
import config  # noqa: E402
import escaner_secretos as ESC  # noqa: E402

sys.path.insert(0, str(config.HERRAMIENTAS / 'zoho'))
DESK = 'https://desk.zoho.eu/api/v1'
SALIDA = APP / 'data/ia/_privado/hilos.json'


def elegir(n=40):
    d = json.loads((APP / 'data/bandeja/bandeja.json').read_text())
    c = [x for x in d['correos'] if not x.get('auto') and x.get('cliente_id') and (x.get('queja') or (x.get('dias_laborables') or 99) <= 22)]
    c.sort(key=lambda x: (not x.get('queja'), x.get('gravedad') != 'rojo', -(x.get('horas') or 0)))
    elegidos = c[:n]
    # todos los de Lucía entran (sustituyendo a los menos urgentes de otros)
    lucia = [x for x in c if x.get('account_id') == 'lucia' and x not in elegidos]
    for x in lucia:
        for i in range(len(elegidos) - 1, -1, -1):
            if elegidos[i].get('account_id') != 'lucia' and not elegidos[i].get('queja'):
                elegidos[i] = x
                break
    elegidos.sort(key=lambda x: (not x.get('queja'), x.get('gravedad') != 'rojo', -(x.get('horas') or 0)))
    return elegidos


RE_CREDENCIAL = re.compile(r"(?i)\b(usuari[oa]s?|user(?:name)?|login|contrase(?:ñ|n)a|password|passw(?:or)?d|pass|clave|pwd|pin)(\s*[:=]\s*)(\S+)")


def limpiar(t):
    t = html.unescape(re.sub(r'<[^>]+>', ' ', t or ''))
    t = RE_CREDENCIAL.sub(r'\1\2[quitado]', t)   # usuario/contraseña que a veces se mandan en el hilo
    for nombre, pat in ESC.PATRONES:
        t = pat.sub('[' + nombre + ' quitado]', t)
    t = re.sub(r'[ \t\xa0]+', ' ', t)
    t = re.sub(r'\n\s*\n+', '\n\n', t).strip()
    # fuera las citas del correo anterior (lo de «El … escribió:» en adelante) para no repetir el hilo
    t = re.split(r'\n(?:El .{5,120} escribió:|On .{5,120} wrote:|De: |From: |-----Original|________________)', t)[0]
    return t[:3000]


def main():
    n = int(sys.argv[sys.argv.index('--n') + 1]) if '--n' in sys.argv else 40
    import zh
    tk, _ = zh.acceso()

    def g(ruta, oid=None):
        h = {'Authorization': 'Zoho-oauthtoken ' + tk}
        if oid:
            h['orgId'] = oid
        try:
            return json.load(urllib.request.urlopen(urllib.request.Request(DESK + ruta, headers=h), timeout=60))
        except urllib.error.HTTPError as e:
            return {'_error': e.code}
    oid = str(g('/organizations')['data'][0]['id'])
    salida = {'generado': datetime.now().strftime('%Y-%m-%d %H:%M'), 'fuente': 'Zoho Desk (zh.py, lectura)', 'hilos': {}}
    for x in elegir(n):
        tid = (x.get('url') or '').rstrip('/').split('/')[-1]
        conv = g(f'/tickets/{tid}/conversations?from=1&limit=30', oid)
        msgs = []
        for m in sorted(conv.get('data', []), key=lambda m: m.get('createdTime') or ''):
            if m.get('type') != 'thread':
                continue
            th = g(f"/tickets/{tid}/threads/{m['id']}?include=plainText", oid)
            texto = th.get('plainText') or th.get('content') or m.get('summary') or ''
            autor = (th.get('author') or m.get('author') or {})
            msgs.append({
                'fecha': (m.get('createdTime') or '')[:16].replace('T', ' '),
                'direccion': 'entrante' if m.get('direction') == 'in' else 'saliente',
                'de': autor.get('name') or autor.get('firstName') or '',
                'tipo_autor': autor.get('type'),
                'texto': limpiar(texto),
            })
        salida['hilos'][x['numero']] = {
            'numero': x['numero'], 'ticket_id': tid, 'cliente_id': x['cliente_id'], 'asunto': x.get('asunto'),
            'account_id': x.get('account_id'), 'queja': x.get('queja'), 'horas': x.get('horas'),
            'dias_laborables': x.get('dias_laborables'), 'url': x.get('url'), 'mensajes': msgs[-8:],
            'error': conv.get('_error'),
        }
        print(x['numero'], x['cliente_id'], len(msgs), conv.get('_error') or '')
    SALIDA.write_text(json.dumps(salida, ensure_ascii=False, indent=1))
    print('→', SALIDA, len(salida['hilos']))


if __name__ == '__main__':
    main()

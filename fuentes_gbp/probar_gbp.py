#!/usr/bin/env python3
"""
probar_gbp.py · pruebas de la ficha de Google (Google Business Profile) sin tocar nada real.

  1. El generador sin llave escribe «pendiente_aprobacion» con los pasos (a un fichero temporal).
  2. Con datos INVENTADOS (--simulado): reseña mala sin responder, caída de llamadas y de rutas, ficha suspendida, datos
     cambiados por Google, ficha sin cliente; sin correos ni teléfonos en la salida.
  3. Motor de alertas con esos datos: dueño SEO/ficha de Google, copia al account, coherencia N = N.
  4. Servidor propio (127.0.0.1, puerto de RO_PUERTOS_PRUEBA, por defecto 9307-9309) con copia de local.db y RO_GBP_DOC:
     proponer (SEO, account sí; otra account y producción, 403), responder con hueco o bloqueo (400), responder bien
     (cola, «simulada»), «ver como» (403 al guardar) y la cola filtrada por cliente.
Uso: python3 fuentes_gbp/probar_gbp.py
"""
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

APP = Path(__file__).resolve().parent.parent
FALLOS = []


def ok(cond, txt):
    print(('✓ ' if cond else '✗ ') + txt)
    if not cond:
        FALLOS.append(txt)


def correr(args, env=None):
    return subprocess.run([sys.executable, *args], cwd=APP, capture_output=True, text=True, env={**os.environ, **(env or {})}, timeout=300)


def puerto_libre():
    ini, fin = (int(x) for x in os.environ.get('RO_PUERTOS_PRUEBA', '9307-9309').split('-'))
    for p in range(ini, fin + 1):
        with socket.socket() as s:
            try:
                s.bind(('127.0.0.1', p))
                return p
            except OSError:
                continue
    sys.exit('Sin puerto libre en ' + os.environ.get('RO_PUERTOS_PRUEBA', '9307-9309'))


def main():
    tmp = Path(tempfile.mkdtemp(prefix='gbp_'))
    # 1 · pendiente (sin llave: en este Mac no hay google_gbp_refresh_token)
    pend = tmp / 'pend.json'
    r = correr(['fuentes_gbp/generar_gbp.py', '--desde-cache', '--salida', str(pend)]) if not (APP / 'fuentes_gbp/_cache/volcado.json').exists() else None
    if r is not None:
        d = json.loads(pend.read_text())
        ok(d['_meta']['estado'] == 'pendiente_aprobacion' and d['_meta']['texto'].startswith('Pendiente de aprobación de Google · lo hace Tomás'),
           'sin acceso: «Pendiente de aprobación de Google · lo hace Tomás: …»')
        ok(len(d['_meta']['pasos']) == 5 and all(p.get('texto') for p in d['_meta']['pasos']), 'sin acceso: 5 pasos con enlace')
        ok(d['clientes'] == [] and d['alertas'] == [], 'sin acceso: no inventa clientes ni alertas')
    # 2 · simulado
    sim = tmp / 'sim.json'
    r = correr(['fuentes_gbp/generar_gbp.py', '--simulado', '--salida', str(sim)], {'RO_GBP_AHORA': '2026-10-03T07:00'})
    ok(r.returncode == 0, 'simulado: el generador termina bien')
    d = json.loads(sim.read_text())
    reglas = {a['regla'] for a in d['alertas']}
    ok({'resena_mala', 'caida_llamadas', 'caida_rutas', 'perfil_suspendido', 'datos_cambiados'} <= reglas, f'simulado: salen las 5 reglas ({sorted(reglas)})')
    ok(any(a['regla'] == 'resena_mala' and a['gravedad'] == 'rojo' for a in d['alertas']) and any(a['regla'] == 'resena_mala' and a['gravedad'] == 'ambar' for a in d['alertas']),
       'simulado: reseña mala roja pasadas 24 h y ámbar antes')
    ok(d['resumen']['fichas_sin_cliente'] == 1, 'simulado: la ficha sin cliente queda aparte')
    txt = sim.read_text()
    ok('[dato quitado]' in txt and not re.search(r'[\w.+-]+@[\w-]+\.\w', txt), 'simulado: sin correos ni teléfonos en la salida')
    ok(all(a.get('dueno_id') and a.get('copia_a') is not None for a in d['alertas'] if a.get('cliente_id')), 'simulado: cada alerta con dueño y copia al account')
    # no escribe datos inventados en data/
    r2 = correr(['fuentes_gbp/generar_gbp.py', '--simulado'])
    ok(r2.returncode != 0, 'simulado: sin --salida no escribe en data/')
    # 3 · motor de alertas
    sal = tmp / 'alertas'
    sal.mkdir()
    r = correr(['fuentes_alertas/generar_alertas.py'], {'RO_ALERTAS_GBP': str(sim), 'RO_ALERTAS_SALIDA': str(sal), 'RO_ALERTAS_ESTADO': str(tmp / 'estado.json')})
    ok(r.returncode == 0, 'alertas: el motor termina bien')
    al = json.loads((sal / 'alertas.json').read_text())
    g = [a for a in al['alertas'] if a['tipo'].startswith('gbp_')]
    coh = [c for c in al.get('coherencia', []) if 'ficha de Google' in c['que']]
    ok(coh and coh[0]['ok'] and coh[0]['cifra_alertas'] == len(g) > 0, f'alertas: coherencia de la ficha de Google ({len(g)} = {coh[0]["cifra_modulo"] if coh else "?"})')
    acc = {a['copia_a'][0] for a in g if a.get('copia_a')}
    vistas = all(any(x['id'] == a['id'] for x in json.loads((sal / f'p_{a["copia_a"][0]}.json').read_text())['alertas']) for a in g if a.get('copia_a'))
    ok(vistas and acc, f'alertas: el account del cliente la ve ({", ".join(sorted(acc))})')
    # 4 · servidor propio con copia de la base
    db = tmp / 'local.db'
    shutil.copy(APP / 'local.db', db)
    p = puerto_libre()
    env = {**os.environ, 'RO_DB': str(db), 'RO_GBP_DOC': str(sim), 'RO_AVISOS_SIN_BUCLE': '1'}
    srv = subprocess.Popen([sys.executable, 'servir.py', '--puerto', str(p), '--bind', '127.0.0.1'], cwd=APP, env=env,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(60):
            try:
                urllib.request.urlopen(f'http://127.0.0.1:{p}/api/gbp/estado?yo=tomas', timeout=2)
                break
            except Exception:
                time.sleep(0.5)

        def post(ruta, yo, cuerpo, como=None):
            h = {'X-RO-App': '1', 'Content-Type': 'application/json', 'X-RO-Yo': yo, 'Origin': f'http://127.0.0.1:{p}'}
            if como:
                h['X-RO-Como'] = como
            req = urllib.request.Request(f'http://127.0.0.1:{p}/api/gbp/{ruta}', data=json.dumps(cuerpo).encode(), headers=h, method='POST')
            try:
                with urllib.request.urlopen(req, timeout=20) as x:
                    return x.status, json.loads(x.read())
            except urllib.error.HTTPError as e:
                return e.code, json.loads(e.read() or b'{}')

        musashi = next((c for c in d['clientes'] if c['cliente_id'] == 'musashi-consultores'), d['clientes'][0])
        rid = next(r for f in musashi['fichas'] for r in f['resenas']['por_responder'] if (r['estrellas'] or 5) <= 3)['id']
        seo, account = musashi.get('seo_id') or 'jeronimo', musashi.get('account_id')
        otra = next(x for x in ('lucia', 'carla', 'dana', 'candela') if x != account)
        s, b = post('borrador', seo, {'resena_id': rid})
        ok(s == 200 and b.get('texto') and b.get('calidad', {}).get('bloqueos') == [], f'servidor: SEO/ficha de Google propone respuesta (nota {b.get("calidad", {}).get("nota")})')
        if account:
            s, _ = post('borrador', account, {'resena_id': rid})
            ok(s == 200, 'servidor: el account del cliente propone respuesta')
        s, _ = post('borrador', otra, {'resena_id': rid})
        ok(s == 403, 'servidor: otra account no (403)')
        s, _ = post('borrador', 'manuel', {'resena_id': rid})
        ok(s == 403, 'servidor: producción no (403)')
        s, b = post('responder', seo, {'resena_id': rid, 'texto': 'Hola. Gracias [completar: canal]. ' + musashi['cliente'], 'modulo': 'seo-web'})
        ok(s == 400, 'servidor: con [completar: …] no se guarda')
        s, b = post('responder', seo, {'resena_id': rid, 'texto': 'Hola. Gracias. Revisamos tu cuota de 60 €. ' + musashi['cliente'], 'modulo': 'seo-web'})
        ok(s == 400 and 'secreto' in b.get('error', '') + json.dumps(b.get('calidad', {}), ensure_ascii=False), 'servidor: con importes o datos del caso no se guarda')
        bueno = ('Hola. Gracias por contarlo. Sentimos de verdad que tu experiencia no haya sido buena. Para revisarlo bien y sin dar datos '
                 f'aquí, escríbenos por el correo del despacho y te atenderá la dirección.\n\nUn saludo,\n{musashi["cliente"]}')
        s, b = post('responder', seo, {'resena_id': rid, 'texto': bueno, 'modulo': 'seo-web'})
        ok(s == 200 and b.get('estado') == 'simulada' and 'SIN publicar' in b.get('texto', ''), 'servidor: responder queda en la cola en SIMULACIÓN (canal apagado)')
        s, _ = post('responder', 'tomas', {'resena_id': rid, 'texto': bueno, 'modulo': 'seo-web'}, como=seo)
        ok(s == 403, 'servidor: en «ver como» no se guarda (403)')
        cola = json.loads(urllib.request.urlopen(f'http://127.0.0.1:{p}/api/gbp/cola?yo={otra}', timeout=10).read())['cola']
        ok(all(x['cliente_id'] != musashi['cliente_id'] for x in cola), 'servidor: la cola de otra account no trae ese cliente')
    finally:
        srv.terminate()
        srv.wait(timeout=10)
        shutil.rmtree(tmp, ignore_errors=True)
    print('\nTODO BIEN' if not FALLOS else f'\n{len(FALLOS)} FALLO(S)')
    sys.exit(1 if FALLOS else 0)


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Prueba de M14 Incidencias con Chrome sin cabeza (Playwright): consola, desbordes, recorte por persona, pestañas,
ficha y capturas a 1440 y 390 px. Con --ciclo, además recorre el ciclo entero de UNA incidencia como Mili
(textos marcados «[prueba del ciclo]») y comprueba en local.db que no se borra nada.
Uso: con servir.py en marcha →  python3 probar_incidencias.py [puerto] [--ciclo]   (por defecto 8774)"""
import json
import sqlite3
import sys
import urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright

ARGS = [a for a in sys.argv[1:] if not a.startswith('--')]
PUERTO = ARGS[0] if ARGS else '8774'
BASE = f'http://127.0.0.1:{PUERTO}'
APP = Path(__file__).resolve().parent.parent
CAP = APP / 'capturas/incidencias'
CAP.mkdir(parents=True, exist_ok=True)
GENTE = ['tomas', 'mili', 'lucia', 'valeria', 'yessica', 'constanza', 'setter_ana']
fallos = []


def api(ruta, yo):
    with urllib.request.urlopen(f'{BASE}/api/{ruta}?yo={yo}') as r:
        return json.loads(r.read())


def oyente(pg, errores):
    pg.on('console', lambda m: errores.append(f"{m.text} @ {m.location.get('url', '')}") if m.type == 'error' else None)
    pg.on('pageerror', lambda e: errores.append(str(e)))


with sync_playwright() as p:
    nav = p.chromium.launch(channel='chrome', headless=True)
    for yo in GENTE:
        for ancho, alto in ((1440, 1000), (390, 844)):
            ctx = nav.new_context(viewport={'width': ancho, 'height': alto}, device_scale_factor=1 if ancho > 1000 else 2)
            pg = ctx.new_page()
            errores = []
            oyente(pg, errores)
            pg.goto(f'{BASE}/?yo={yo}#/incidencias', wait_until='networkidle')
            pg.wait_for_timeout(1200)
            texto = pg.inner_text('main') if pg.query_selector('main') else ''
            desborde = pg.evaluate('document.documentElement.scrollWidth - document.documentElement.clientWidth')
            pest = pg.eval_on_selector_all('[role=tab]', 'xs => xs.map(x => x.textContent.trim())')
            print(f'{yo:11} {ancho:5} px · errores {len(errores)} · desborde {desborde} px · pestañas {pest} · {texto[:80]!r}'.replace('\n', ' | '))
            if errores:
                fallos.append((yo, ancho, errores[:3]))
            if desborde > 0:
                fallos.append((yo, ancho, f'desborde horizontal {desborde}px'))
            pg.screenshot(path=str(CAP / f'{yo}_{ancho}.png'), full_page=False)
            if ancho == 1440 and yo in ('mili', 'lucia', 'tomas'):
                pg.screenshot(path=str(CAP / f'{yo}_{ancho}_completa.png'), full_page=True)
            # todas las pestañas (y su desborde)
            for k, nombre in enumerate(pest):
                pg.locator('[role=tab]').nth(k).click()
                pg.wait_for_timeout(350)
                d2 = pg.evaluate('document.documentElement.scrollWidth - document.documentElement.clientWidth')
                if d2 > 0:
                    fallos.append((yo, ancho, f'desborde {d2}px en «{nombre}»'))
                if yo in ('mili', 'lucia') or (yo == 'tomas' and ancho == 1440):
                    slug = '_'.join(''.join(ch for ch in w.lower() if ch.isalpha()) for w in nombre.split()[:2]).strip('_').replace('é', 'e').replace('ú', 'u')
                    pg.screenshot(path=str(CAP / f'{yo}_{ancho}_{slug}.png'), full_page=ancho == 1440)
            if pest:
                pg.locator('[role=tab]').first.click()
            if errores:
                fallos.append((yo, ancho, errores[:3]))
            ctx.close()

    # ficha de una incidencia de cliente (Mili) y de sistema, escritorio y móvil
    datos = api('modulo/incidencias/incidencias', 'mili')
    cli = next(i for i in datos['incidencias'] if i['origen'] == 'alarma' and i.get('historia'))
    sis = next(i for i in datos['incidencias'] if i['regla'] == 'desk_agente_baja')
    for ancho, alto in ((1440, 1000), (390, 844)):
        ctx = nav.new_context(viewport={'width': ancho, 'height': alto}, device_scale_factor=1 if ancho > 1000 else 2)
        pg = ctx.new_page()
        errores = []
        oyente(pg, errores)
        for nombre, inc in (('cliente', cli), ('sistema', sis)):
            pg.goto(f'{BASE}/?yo=mili#/incidencias/{inc["id"]}', wait_until='networkidle')
            pg.wait_for_timeout(900)
            d2 = pg.evaluate('document.documentElement.scrollWidth - document.documentElement.clientWidth')
            if d2 > 0:
                fallos.append(('mili ficha', ancho, f'desborde {d2}px'))
            pg.screenshot(path=str(CAP / f'mili_{ancho}_ficha_{nombre}.png'), full_page=True)
        # Lucía abre una incidencia de un cliente que no es suyo → no la recibe
        ajena = next(i for i in datos['incidencias'] if i.get('cliente_id') and i.get('responsable_id') not in ('lucia', None) and i['origen'] == 'desk')
        pg.goto(f'{BASE}/?yo=lucia#/incidencias/{ajena["id"]}', wait_until='networkidle')
        pg.wait_for_timeout(700)
        if 'no está en tu lista' not in pg.inner_text('main'):
            fallos.append(('lucia', ancho, 've una incidencia de un cliente ajeno'))
        if ancho == 1440:
            pg.screenshot(path=str(CAP / 'lucia_1440_ficha_ajena.png'))
        print(f'ficha {ancho}px · errores {errores}')
        if errores:
            fallos.append(('ficha', ancho, errores[:3]))
        ctx.close()

    # mapa de calor: pulsar una casilla filtra las alarmas
    ctx = nav.new_context(viewport={'width': 1440, 'height': 1000})
    pg = ctx.new_page()
    pg.goto(f'{BASE}/?yo=mili#/incidencias', wait_until='networkidle')
    pg.wait_for_timeout(800)
    pg.locator('[role=tab]').nth(1).click()
    pg.wait_for_timeout(300)
    pg.locator('.inc-calor button.inc-cel.r, .inc-calor button.inc-cel.rr').first.click()
    pg.wait_for_timeout(400)
    pg.screenshot(path=str(CAP / 'mili_1440_mapa_filtrado.png'), full_page=True)
    print('mapa filtrado:', pg.inner_text('.inc-calor ~ div')[:120].replace('\n', ' | ') if pg.query_selector('.inc-calor ~ div') else '—')
    ctx.close()

    # ciclo entero (opcional): como Mili, en una incidencia de sistema
    if '--ciclo' in sys.argv:
        objetivo = next(i for i in datos['incidencias'] if i['regla'] == 'zadarma_ext_sin_registrar')
        ctx = nav.new_context(viewport={'width': 1440, 'height': 1000})
        pg = ctx.new_page()
        errores = []
        oyente(pg, errores)
        url = f'{BASE}/?yo=mili#/incidencias/{objetivo["id"]}'
        pg.goto(url, wait_until='networkidle')
        pg.wait_for_timeout(800)

        def paso(boton, rellenar=None, enviar=None):
            pg.get_by_role('button', name=boton).first.click()
            pg.wait_for_timeout(250)
            if rellenar:
                rellenar()
            if enviar:
                pg.locator('form.inc-form button[type=submit]').click()
            pg.wait_for_timeout(900)

        paso('La he visto')
        paso('Avisar al responsable', lambda: pg.locator('form.inc-form input[type=url]').fill('https://app.clickup.com/90152357276/chat/r/2kyqzkcw-16055'), True)
        paso('Reiterar', None, True)
        paso('Escalar a Tomás · 48 h', None, True)
        pg.screenshot(path=str(CAP / 'mili_1440_ciclo_escalada.png'), full_page=True)
        paso('Resuelta (con prueba)', lambda: pg.locator('form.inc-form textarea').fill('[prueba del ciclo] Extensiones revisadas en Zadarma'), True)
        pg.screenshot(path=str(CAP / 'mili_1440_ciclo_resuelta.png'), full_page=True)
        ctx.close()
        con = sqlite3.connect(APP / 'local.db')
        filas = con.execute("SELECT id, tipo, quien FROM acciones WHERE modulo='incidencias' AND objeto=? ORDER BY id", (objetivo['id'],)).fetchall()
        print('ciclo en local.db:', [f[1] for f in filas])
        try:
            con.execute("DELETE FROM acciones WHERE id=?", (filas[0][0],))
            fallos.append(('ciclo', 0, 'local.db deja borrar una acción'))
        except sqlite3.DatabaseError as e:
            print('borrar una acción del ciclo →', e)
        con.close()
        print('errores del ciclo:', errores)
        # la escalada a Tomás aparece en «Para Tomás»
        ctx = nav.new_context(viewport={'width': 1440, 'height': 1000})
        pg = ctx.new_page()
        pg.goto(f'{BASE}/?yo=tomas#/incidencias', wait_until='networkidle')
        pg.wait_for_timeout(900)
        pg.screenshot(path=str(CAP / 'tomas_1440_para_tomas.png'))
        ctx.close()
    nav.close()

print('FALLOS:', fallos if fallos else 'ninguno')

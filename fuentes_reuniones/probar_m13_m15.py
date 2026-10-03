#!/usr/bin/env python3
"""Prueba de M13 Informes mensuales y M15 Reuniones con Chrome sin cabeza (Playwright): consola, desbordes,
recorte por persona (lo que llega del servidor), pestañas, botones en simulación y capturas a 1440 y 390 px.
Uso: con servir.py en marcha →  python3 probar_m13_m15.py [puerto]   (por defecto 8793)"""
import json
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

PUERTO = sys.argv[1] if len(sys.argv) > 1 else '8793'
BASE = f'http://127.0.0.1:{PUERTO}'
APP = Path(__file__).resolve().parent.parent
GENTE = ['tomas', 'mili', 'lucia', 'valeria', 'yessica', 'constanza', 'setter_ana']
MODS = {'informes-mensuales': APP / 'capturas/informes-mensuales', 'reuniones': APP / 'capturas/reuniones'}
for c in MODS.values():
    c.mkdir(parents=True, exist_ok=True)
fallos = []


def abrir(nav, yo, ruta, ancho, alto):
    ctx = nav.new_context(viewport={'width': ancho, 'height': alto}, device_scale_factor=1 if ancho > 1000 else 2)
    pg = ctx.new_page()
    errores = []
    # Se ignoran los 404 de módulos de OTROS agentes que aún se están construyendo (fichero dado de alta en indice.js
    # antes de existir: personas.js, decisiones.js, incidencias.js…). Los de M13 y M15 sí cuentan.
    ajeno = lambda m: '/modulos/' in str(m.location.get('url', '')) and not any(x in str(m.location.get('url', '')) for x in ('informes_mensuales.js', 'reuniones.js'))
    pg.on('console', lambda m: errores.append(f"{m.text} · {m.location.get('url', '')}") if m.type == 'error' and '403' not in m.text and not ajeno(m) else None)
    pg.on('pageerror', lambda e: errores.append(str(e)))
    pg.goto(f'{BASE}/?yo={yo}#/{ruta}', wait_until='networkidle')
    pg.wait_for_timeout(1100)
    return ctx, pg, errores


with sync_playwright() as p:
    nav = p.chromium.launch(channel='chrome', headless=True)
    for ruta, cap in MODS.items():
        for yo in GENTE:
            for ancho, alto in ((1440, 1000), (390, 844)):
                ctx, pg, errores = abrir(nav, yo, ruta, ancho, alto)
                texto = pg.inner_text('main') if pg.query_selector('main') else ''
                desborde = pg.evaluate('document.documentElement.scrollWidth - document.documentElement.clientWidth')
                filas = pg.eval_on_selector_all('table.densa tbody tr, .reu-it', 'xs => xs.length')
                print(f'{ruta:18} {yo:11} {ancho:5} px · errores {len(errores)} · desborde {desborde} · filas {filas} · {texto[:80]!r}'.replace('\n', ' | '))
                if errores:
                    fallos.append((ruta, yo, ancho, errores[:3]))
                if desborde > 0:
                    fallos.append((ruta, yo, ancho, f'desborde horizontal {desborde}px'))
                pg.screenshot(path=str(cap / f'r3_{yo}_{ancho}.png'), full_page=False)
                if yo in ('tomas', 'mili', 'lucia') :
                    pg.screenshot(path=str(cap / f'r3_{yo}_{ancho}_completa.png'), full_page=True)
                ctx.close()

    # ---- M13: chips, filtro por account, «Enviado por otra vía» (simulado), mes anterior ----
    ctx, pg, errores = abrir(nav, 'tomas', 'informes-mensuales', 1440, 1000)
    pg.locator('#inf-chips button[data-v="sin_tarea"]').click(); pg.wait_for_timeout(300)
    pg.locator('.inf-acc-f').first.click(); pg.wait_for_timeout(400)
    pg.screenshot(path=str(MODS['informes-mensuales'] / 'r3_tomas_1440_filtro_account.png'), full_page=False)
    pg.locator('#inf-chips button[data-v="pendientes"]').click(); pg.wait_for_timeout(300)
    b = pg.get_by_role('button', name='Enviado por otra vía').first
    if b.count():
        b.click(); pg.wait_for_timeout(200)
        pg.screenshot(path=str(MODS['informes-mensuales'] / 'r3_tomas_1440_otra_via_form.png'), full_page=False)
        pg.get_by_role('button', name='Cancelar').first.click()
    pg.get_by_role('button', name='Agosto', exact=True).click(); pg.wait_for_timeout(500)
    pg.screenshot(path=str(MODS['informes-mensuales'] / 'r3_tomas_1440_agosto.png'), full_page=True)
    pg.get_by_role('button', name='Septiembre · este ciclo').click(); pg.wait_for_timeout(300)
    print('M13 interacción, errores:', errores)
    if errores:
        fallos.append(('informes-mensuales', 'interacción', errores[:3]))
    ctx.close()

    # ---- M15: pestañas y desplegable de tipo (en «ver como» debe quedar en solo lectura) ----
    ctx, pg, errores = abrir(nav, 'tomas', 'reuniones', 1440, 1000)
    for pest in ('personas', 'clientes', 'dailies', 'lista'):
        pg.locator(f'[role=tab][id$="-{pest}"]').click()
        pg.wait_for_timeout(350)
        pg.screenshot(path=str(MODS['reuniones'] / f"r3_tomas_1440_{pest}.png"), full_page=True)
    pg.get_by_role('button', name='Septiembre', exact=True).click(); pg.wait_for_timeout(400)
    pg.screenshot(path=str(MODS['reuniones'] / 'r3_tomas_1440_septiembre.png'), full_page=True)
    pg.get_by_role('button', name='Octubre · en curso').click(); pg.wait_for_timeout(300)
    print('M15 interacción, errores:', errores)
    if errores:
        fallos.append(('reuniones', 'interacción', errores[:3]))
    ctx.close()

    # ver como: Tomás viendo a Mili → todo en solo lectura (no escribe)
    ctx, pg, errores = abrir(nav, 'tomas', 'reuniones', 1440, 1000)
    pg.goto(f'{BASE}/?yo=tomas&como=mili#/reuniones', wait_until='networkidle'); pg.wait_for_timeout(900)
    dis = pg.eval_on_selector_all('.reu-sin', 'xs => xs.map(x => x.getAttribute("aria-disabled"))')
    print('ver como mili · desplegables en solo lectura:', dis[:3], '· errores', errores)
    ctx.close()
    nav.close()

print('FALLOS:' if fallos else 'TODO BIEN', json.dumps(fallos, ensure_ascii=False)[:2000] if fallos else '')

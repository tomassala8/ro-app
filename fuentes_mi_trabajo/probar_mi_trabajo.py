#!/usr/bin/env python3
"""Prueba de «Mi trabajo» con Chrome sin cabeza (Playwright): consola, desbordes, textos < 12 px, flujo de acciones y capturas.
Uso: con servir.py en marcha SOBRE UNA COPIA de local.db (RO_DB=…) →  python3 probar_mi_trabajo.py [puerto]   (por defecto 9561)
Capturas .jpg en capturas/mi_trabajo/ (1440 y 390 px). El flujo de acciones escribe en la base de ESE servidor (la copia)."""
import json
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

PUERTO = sys.argv[1] if len(sys.argv) > 1 else '9561'
BASE = f'http://127.0.0.1:{PUERTO}'
APP = Path(__file__).resolve().parent.parent
CAP = APP / 'capturas' / 'mi_trabajo'
CAP.mkdir(parents=True, exist_ok=True)
GENTE = ['macarena', 'lucia', 'valeria', 'mili', 'cecilia', 'camilo', 'jeronimo', 'tomas']
fallos = []

MEDIR = """() => {
  const sw = document.documentElement.scrollWidth - document.documentElement.clientWidth;
  const main = document.querySelector('main') || document.body;
  const peq = [...main.querySelectorAll('*')].filter(e => e.childNodes.length && [...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim())
    && e.offsetParent !== null && parseFloat(getComputedStyle(e).fontSize) < 12).length;
  return { sw, peq, nul: /\\bnull\\b|undefined|NaN/.test(main.innerText), filas: document.querySelectorAll('[data-tarea]').length };
}"""


def abrir(nav, yo, ancho, alto, como=None):
    ctx = nav.new_context(viewport={'width': ancho, 'height': alto}, device_scale_factor=1)
    pg = ctx.new_page()
    errores = []
    pg.on('console', lambda m: errores.append(m.text) if m.type == 'error' and '404' not in m.text else None)
    pg.on('pageerror', lambda e: errores.append(str(e)))
    q = f'?yo={yo}' + (f'&como={como}' if como else '')
    pg.goto(f'{BASE}/{q}#/mi-trabajo', wait_until='networkidle')
    pg.wait_for_timeout(1500)
    return ctx, pg, errores


with sync_playwright() as p:
    nav = p.chromium.launch(channel='chrome', headless=True)
    for yo in GENTE:
        for ancho, alto in ((1440, 1000), (390, 844)):
            ctx, pg, errores = abrir(nav, yo, ancho, alto)
            m = pg.evaluate(MEDIR)
            texto = pg.inner_text('main')[:120].replace('\n', ' | ')
            print(f'{yo:10} {ancho:5} · errores {len(errores)} · desborde {m["sw"]} · <12px {m["peq"]} · null {m["nul"]} · filas {m["filas"]} · {texto!r}')
            if errores or 'ha fallado' in texto or m['sw'] > 0 or m['nul']:
                fallos.append((yo, ancho, errores[:3], m))
            pg.screenshot(path=str(CAP / f'{yo}_{ancho}.jpg'), type='jpeg', quality=80, full_page=False)
            for tab in pg.get_by_role('tab').all():
                tab.click()
                pg.wait_for_timeout(300)
                if pg.evaluate(MEDIR)['sw'] > 0:
                    fallos.append((yo, ancho, 'pestaña', tab.inner_text()))
            if yo in ('valeria', 'mili') and ancho == 1440 and pg.get_by_role('button', name='Mi equipo').count():
                pg.get_by_role('button', name='Mi equipo').click()
                pg.wait_for_timeout(500)
                pg.screenshot(path=str(CAP / f'{yo}_{ancho}_equipo.jpg'), type='jpeg', quality=80, full_page=False)
                pg.get_by_role('button', name='Mis tareas').click()
            ctx.close()

    # ---------- flujo: Macarena abre una tarea, apunta 15 min, cambia la fecha, cronómetro ----------
    ctx, pg, errores = abrir(nav, 'macarena', 1440, 1000)
    pg.locator('[data-tarea] button[aria-label="Más acciones"]').first.click()
    pg.wait_for_timeout(400)
    pg.screenshot(path=str(CAP / 'macarena_1440_tarea_abierta.jpg'), type='jpeg', quality=80, full_page=False)
    pg.get_by_role('button', name='15 min').first.click()
    pg.wait_for_timeout(9500)
    txt = pg.inner_text('main')
    ok_horas = 'Hoy llevas 15 min' in txt or '15 min' in txt
    print('flujo · 15 min apuntados:', ok_horas)
    if not ok_horas:
        fallos.append(('flujo', 'horas', txt[:200]))
    r = pg.evaluate("fetch('api/mi_trabajo?yo=macarena').then(r => r.json()).then(d => d.horas_app.length)")
    print('flujo · horas_app en el servidor:', r)
    if not r:
        fallos.append(('flujo', 'horas_app vacío'))
    pg.screenshot(path=str(CAP / 'macarena_1440_tras_apuntar.jpg'), type='jpeg', quality=80, full_page=False)
    ctx.close()

    ctx, pg, errores = abrir(nav, 'macarena', 390, 844)
    pg.screenshot(path=str(CAP / 'macarena_390_tras_apuntar.jpg'), type='jpeg', quality=80, full_page=False)
    pg.locator('[data-tarea] button[aria-label="Más acciones"]').first.click()
    pg.wait_for_timeout(400)
    pg.locator('[data-tarea] [aria-expanded="true"]').first.scroll_into_view_if_needed()
    if pg.evaluate(MEDIR)['sw'] > 0:
        fallos.append(('flujo', '390 con tarea abierta: desborde'))
    pg.screenshot(path=str(CAP / 'macarena_390_tarea_abierta.jpg'), type='jpeg', quality=80, full_page=False)
    ctx.close()

    # ---------- «ver como»: Tomás como Macarena no guarda ----------
    ctx, pg, errores = abrir(nav, 'tomas', 1440, 1000, como='macarena')
    r = pg.evaluate("""fetch('api/acciones?yo=tomas&como=macarena', {method: 'POST', headers: {'Content-Type': 'application/json', 'X-RO-App': '1', 'X-RO-Yo': 'tomas', 'X-RO-Como': 'macarena'},
      body: JSON.stringify({modulo: 'mi-trabajo', herramienta: 'clickup', tipo: 'comentario', objeto: 'x123', texto: 'hola'})}).then(r => r.status)""")
    print('ver como · POST acciones:', r)
    if r != 403:
        fallos.append(('ver_como', r))
    pg.screenshot(path=str(CAP / 'tomas_como_macarena_1440.jpg'), type='jpeg', quality=80, full_page=False)
    ctx.close()
    nav.close()

print('FALLOS:' if fallos else 'TODO BIEN', json.dumps(fallos, ensure_ascii=False, default=str)[:3000] if fallos else '')

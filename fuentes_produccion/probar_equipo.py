#!/usr/bin/env python3
"""Prueba de M10 Producción y M11 Horas con Chrome sin cabeza (Playwright): consola, desbordes, recorte y capturas.
Uso: con servir.py en marcha →  python3 probar_equipo.py [puerto]   (por defecto 8786)
Capturas en capturas/produccion/ y capturas/horas/ (1440 y 390 px). Ignora los 404 de módulos de otros agentes."""
import json, re, sys
from pathlib import Path
from playwright.sync_api import sync_playwright

PUERTO = sys.argv[1] if len(sys.argv) > 1 else '8786'
BASE = f'http://127.0.0.1:{PUERTO}'
APP = Path(__file__).resolve().parent.parent
GENTE = ['tomas', 'mili', 'lucia', 'valeria', 'yessica', 'constanza', 'setter_ana', 'camilo', 'cecilia']
MIOS = ('produccion.js', 'horas.js', 'produccion_comun.js')
fallos = []


def ajeno(m):
    """404 de un fichero de módulo que todavía construye otro agente: no es de este módulo."""
    url = str((m.location or {}).get('url', '')) if hasattr(m, 'location') else ''
    return ('404' in m.text or 'Failed to load resource' in m.text) and '/modulos/' in url and not url.endswith(MIOS)


with sync_playwright() as p:
    nav = p.chromium.launch(channel='chrome', headless=True)
    for mod in ('produccion', 'horas'):
        cap = APP / 'capturas' / mod
        cap.mkdir(parents=True, exist_ok=True)
        for yo in GENTE:
            for ancho, alto in ((1440, 1000), (390, 844)):
                ctx = nav.new_context(viewport={'width': ancho, 'height': alto}, device_scale_factor=1 if ancho > 1000 else 2)
                pg = ctx.new_page()
                errores = []
                pg.on('console', lambda m: errores.append(f'{m.text} @ {m.location}') if m.type == 'error' and not ajeno(m) else None)
                pg.on('pageerror', lambda e: errores.append(str(e)))
                pg.goto(f'{BASE}/?yo={yo}#/{mod}', wait_until='networkidle')
                pg.wait_for_timeout(1300)
                texto = pg.inner_text('main') if pg.query_selector('main') else ''
                desborde = pg.evaluate('document.documentElement.scrollWidth - document.documentElement.clientWidth')
                fallo_mod = 'ha fallado al pintarse' in texto
                print(f'{mod:10} {yo:11} {ancho:5} px · errores {len(errores)} · desborde {desborde} px · {texto[:110]!r}'.replace('\n', ' | '))
                if errores or fallo_mod:
                    fallos.append((mod, yo, ancho, errores[:3] or 'fallo al pintar'))
                if desborde > 0:
                    fallos.append((mod, yo, ancho, f'desborde horizontal {desborde}px'))
                pg.screenshot(path=str(cap / f'r3_{yo}_{ancho}.png'), full_page=False)
                if ancho == 1440 and yo in ('tomas', 'camilo', 'lucia', 'mili', 'cecilia'):
                    pg.screenshot(path=str(cap / f'r3_{yo}_{ancho}_completa.png'), full_page=True)
                # recorrer todas las pestañas: ninguna debe fallar
                for tab in pg.get_by_role('tab').all():
                    nombre = re.sub(r'\s*\d+$', '', tab.inner_text().strip())
                    tab.click()
                    pg.wait_for_timeout(350)
                    t2 = pg.inner_text('main')
                    d2 = pg.evaluate('document.documentElement.scrollWidth - document.documentElement.clientWidth')
                    if 'ha fallado' in t2 or d2 > 0:
                        fallos.append((mod, yo, ancho, f'pestaña {nombre}: desborde {d2}'))
                    if ancho == 1440 and yo in ('tomas', 'mili', 'camilo', 'lucia'):
                        slug = re.sub(r'[^a-z0-9]+', '_', nombre.lower().translate(str.maketrans('áéíóúñ', 'aeioun'))).strip('_')
                        pg.screenshot(path=str(cap / f'r3_{yo}_{ancho}_{slug}.png'), full_page=True)
                    if ancho == 390 and yo in ('tomas', 'camilo'):
                        slug = re.sub(r'[^a-z0-9]+', '_', nombre.lower().translate(str.maketrans('áéíóúñ', 'aeioun'))).strip('_')
                        pg.screenshot(path=str(cap / f'r3_{yo}_{ancho}_{slug}.png'), full_page=False)
                if errores:
                    fallos.append((mod, yo, ancho, 'tras pestañas', errores[:3]))
                ctx.close()
    nav.close()

print('FALLOS:' if fallos else 'TODO BIEN', json.dumps(fallos, ensure_ascii=False)[:2500] if fallos else '')

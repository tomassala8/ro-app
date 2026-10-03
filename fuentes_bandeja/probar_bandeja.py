#!/usr/bin/env python3
"""Prueba de M3 Bandeja con Chrome sin cabeza (Playwright): consola, desbordes, recorte por persona y capturas.
Uso: con servir.py en marcha →  python3 probar_bandeja.py [puerto]   (por defecto 8783)"""
import json
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

PUERTO = sys.argv[1] if len(sys.argv) > 1 else '8783'
BASE = f'http://127.0.0.1:{PUERTO}'
CAP = Path(__file__).resolve().parent.parent / 'capturas/bandeja'
CAP.mkdir(parents=True, exist_ok=True)
PRE = 'r4_'
GENTE = ['tomas', 'mili', 'lucia', 'valeria', 'yessica', 'sofia', 'setter_ana']
fallos = []

with sync_playwright() as p:
    nav = p.chromium.launch(channel='chrome', headless=True)
    for yo in GENTE:
        for ancho, alto in ((1440, 1000), (390, 844)):
            ctx = nav.new_context(viewport={'width': ancho, 'height': alto}, device_scale_factor=1 if ancho > 1000 else 2)
            pg = ctx.new_page()
            errores = []
            pg.on('console', lambda m: errores.append(m.text) if m.type == 'error' and 'nuevos.js' not in str(m.location) else None)
            pg.on('pageerror', lambda e: errores.append(str(e)))
            pg.goto(f'{BASE}/?yo={yo}#/bandeja', wait_until='networkidle')
            pg.wait_for_timeout(1200)
            texto = pg.inner_text('main') if pg.query_selector('main') else ''
            desborde = pg.evaluate('document.documentElement.scrollWidth - document.documentElement.clientWidth')
            items = pg.eval_on_selector_all('main [role=list] [data-id]', 'xs => xs.length')
            # guía de diseño (auditoría 30): nada de «null», ni hoja de estilos propia, ni texto por debajo de 12 px
            raro = [w for w in ('null', 'undefined', 'NaN') if w in texto.split() or f' {w} ' in texto]
            hoja = pg.evaluate("!!document.getElementById('bandeja-estilos')")
            chicos = pg.evaluate('''() => { const out = []; for (const el of document.querySelectorAll('main *')) {
              if (!el.childNodes.length || ![...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim())) continue;
              const cs = getComputedStyle(el); if (cs.display === 'none' || cs.visibility === 'hidden' || !el.getClientRects().length) continue;
              const f = parseFloat(cs.fontSize); if (f < 12 && !(f >= 11 && cs.textTransform === 'uppercase')) out.push(el.className + ':' + f); } return out.slice(0, 5); }''')
            ia = pg.eval_on_selector_all('[data-ia="borrador"]', 'xs => xs.length')
            linea = f'{yo:11} {ancho:5} px · errores {len(errores)} · desborde {desborde} px · filas {items} · IA {ia} · <12px {len(chicos)} · {texto[:70]!r}'
            if raro: fallos.append((yo, ancho, f'texto raro en pantalla: {raro}'))
            if hoja: fallos.append((yo, ancho, 'la Bandeja inyecta su propia hoja de estilos'))
            if chicos: fallos.append((yo, ancho, f'texto < 12 px: {chicos}'))
            print(linea.replace('\n', ' | '))
            if errores:
                fallos.append((yo, ancho, errores[:3]))
            if desborde > 0:
                fallos.append((yo, ancho, f'desborde horizontal {desborde}px'))
            pg.screenshot(path=str(CAP / f'{PRE}{yo}_{ancho}.png'), full_page=False)
            if yo in ('tomas', 'lucia') and ancho == 1440:
                pg.screenshot(path=str(CAP / f'{PRE}{yo}_{ancho}_completa.png'), full_page=True)
            ctx.close()

    # detalle y acción simulada (Tomás, real, no «ver como») + pestañas
    ctx = nav.new_context(viewport={'width': 1440, 'height': 1000})
    pg = ctx.new_page()
    errores = []
    pg.on('console', lambda m: errores.append(m.text) if m.type == 'error' and 'nuevos.js' not in str(m.location) else None)
    pg.on('pageerror', lambda e: errores.append(str(e)))
    pg.goto(f'{BASE}/?yo=tomas#/bandeja', wait_until='networkidle')
    pg.wait_for_timeout(1000)
    for pest in ('Sin responsable', 'WhatsApp', 'De dónde sale'):
        pg.get_by_role('tab', name=pest).click()
        pg.wait_for_timeout(400)
        pg.screenshot(path=str(CAP / f"{PRE}tomas_1440_{pest.split()[0].lower().replace('ó', 'o')}.png"), full_page=True)
    pg.get_by_role('tab', name='Correos y llamadas').click()
    pg.wait_for_timeout(400)
    pg.locator('[aria-label="Vista"] button[data-v="quejas"]').click()
    pg.wait_for_timeout(300)
    pg.locator('main [role=list] [data-id]').first.click()
    pg.wait_for_timeout(300)
    # IA: «Sugerir respuesta» en el correo; «Usar» pasa el borrador a la caja y NO envía nada
    n_antes = pg.evaluate("fetch('api/acciones?modulo=bandeja', {headers: {'X-RO-Yo': 'tomas'}}).then(r => r.json()).then(d => (d.acciones || []).length).catch(() => -1)")
    if pg.locator('[data-ia="borrador"] button:has-text("Sugerir respuesta")').count():
        pg.locator('[data-ia="borrador"] button:has-text("Sugerir respuesta")').first.click()
        pg.wait_for_timeout(1500)
        usar = pg.locator('[data-ia="borrador"] button:has-text("Usar este borrador")')
        if usar.count():
            usar.first.click(); pg.wait_for_timeout(500)
            caja = pg.locator('#bdj-texto').input_value()
            print('IA · borrador en la caja:', caja[:80].replace('\n', ' | '))
        else:
            print('IA · sin borrador (sin conectar o sin precalculado):', pg.locator('[data-ia="borrador"]').inner_text()[:120].replace('\n', ' | '))
        n_despues = pg.evaluate("fetch('api/acciones?modulo=bandeja', {headers: {'X-RO-Yo': 'tomas'}}).then(r => r.json()).then(d => (d.acciones || []).length).catch(() => -1)")
        print('IA · acciones en cola antes/después:', n_antes, n_despues)
        if n_despues != n_antes:
            fallos.append(('tomas', 'IA', 'el borrador ha puesto algo en la cola: no debe enviarse solo'))
    else:
        fallos.append(('tomas', 'IA', 'falta «Sugerir respuesta» en el correo'))
    pg.screenshot(path=str(CAP / (PRE + 'tomas_1440_ia_borrador.png')), full_page=False)
    pg.screenshot(path=str(CAP / (PRE + 'tomas_1440_queja_detalle.png')), full_page=False)
    # ruta directa a un correo antiguo (lo que hace el «Ir» de Mi día): se abre aunque no esté en «Para hoy»
    pg.goto(f'{BASE}/?yo=tomas#/bandeja/t-RO-6626', wait_until='networkidle')
    pg.wait_for_timeout(1200)
    abierto = pg.locator('[data-id][aria-current="true"]').inner_text() if pg.locator('[data-id][aria-current="true"]').count() else ''
    print('ruta directa RO-6626 →', abierto.replace('\n', ' | ')[:120])
    if 'RO-6626' not in abierto:
        fallos.append(('tomas', 'ruta', 'RO-6626 no se abre'))
    pg.screenshot(path=str(CAP / (PRE + 'tomas_1440_ruta_RO-6626.png')), full_page=False)
    print('errores tras pestañas y detalle:', errores)
    if errores:
        fallos.append(('tomas', 'pestañas', errores[:3]))
    ctx.close()

    # móvil: detalle en su propia ruta
    ctx = nav.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2)
    pg = ctx.new_page()
    pg.goto(f'{BASE}/?yo=lucia#/bandeja', wait_until='networkidle')
    pg.wait_for_timeout(1000)
    if pg.locator('main [role=list] [data-id]').count():
        pg.locator('main [role=list] [data-id]').first.click()
        pg.wait_for_timeout(800)
        d = pg.evaluate('document.documentElement.scrollWidth - document.documentElement.clientWidth')
        print('móvil detalle', pg.url, 'desborde', d)
        pg.screenshot(path=str(CAP / (PRE + 'lucia_390_detalle.png')), full_page=True)
    ctx.close()
    nav.close()

print('FALLOS:' if fallos else 'TODO BIEN', json.dumps(fallos, ensure_ascii=False)[:1500] if fallos else '')

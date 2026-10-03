#!/usr/bin/env python3
"""Prueba de M3 Bandeja v5 con Chrome sin cabeza (Playwright): consola, desbordes, recorte por persona, distribución de
trabajo (lista · conversación y editor · contexto), editor a la vista sin desplazarse, atajos, «Deshacer», huecos que
bloquean el envío, vistas secundarias y capturas .jpg en capturas/_bandeja_v5/.
Uso: con servir.py en marcha CON COPIA de la base (RO_DB=…) →  python3 probar_bandeja.py [puerto]   (por defecto 9230)"""
import json
import re
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

PUERTO = sys.argv[1] if len(sys.argv) > 1 else '9230'
BASE = f'http://127.0.0.1:{PUERTO}'
CAP = Path(__file__).resolve().parent.parent / 'capturas/_bandeja_v5'
CAP.mkdir(parents=True, exist_ok=True)
GENTE = ['tomas', 'mili', 'lucia', 'candela', 'yessica', 'valeria', 'sofia', 'setter_ana']
ANCHOS = ((1440, 900), (1024, 768), (390, 844))
fallos = []
JS_CHICOS = '''() => { const out = []; for (const el of document.querySelectorAll('main *')) {
  if (!el.childNodes.length || ![...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim())) continue;
  const cs = getComputedStyle(el); if (cs.display === 'none' || cs.visibility === 'hidden' || !el.getClientRects().length) continue;
  const f = parseFloat(cs.fontSize); if (f < 12 && !(f >= 11 && cs.textTransform === 'uppercase')) out.push(el.className + ':' + f); } return out.slice(0, 5); }'''


def nueva(nav, ancho, alto):
    ctx = nav.new_context(viewport={'width': ancho, 'height': alto}, device_scale_factor=1 if ancho > 1000 else 2)
    pg = ctx.new_page()
    errores = []
    pg.on('console', lambda m: errores.append(m.text) if m.type == 'error' and 'nuevos.js' not in str(m.location) else None)
    pg.on('pageerror', lambda e: errores.append(str(e)))
    return ctx, pg, errores


def en_vista(pg, sel):
    b = pg.locator(sel).first.bounding_box() if pg.locator(sel).count() else None
    return bool(b) and b['y'] >= 0 and b['y'] + b['height'] <= pg.viewport_size['height'] + 1


with sync_playwright() as p:
    nav = p.chromium.launch(channel='chrome', headless=True)
    for yo in GENTE:
        for ancho, alto in ANCHOS:
            ctx, pg, errores = nueva(nav, ancho, alto)
            pg.goto(f'{BASE}/?yo={yo}#/bandeja', wait_until='networkidle')
            pg.wait_for_timeout(1800)
            texto = pg.inner_text('main') if pg.query_selector('main') else ''
            desborde = pg.evaluate('document.documentElement.scrollWidth - document.documentElement.clientWidth')
            filas = pg.eval_on_selector_all('[data-bdj="lista"] [data-id]', 'xs => xs.length')
            raro = [w for w in ('null', 'undefined', 'NaN') if w in texto.split() or f' {w} ' in texto or f'{w}{w}' in texto]
            hoja = pg.evaluate("!!document.querySelector('style[id*=bandeja], #bandeja-estilos')")
            chicos = pg.evaluate(JS_CHICOS)
            editor = pg.locator('[data-bdj="editor"]').count()
            vista = en_vista(pg, '[data-bdj-enviar="siguiente"]') if editor and ancho > 1000 else None
            linea = f'{yo:11} {ancho:5} px · errores {len(errores)} · desborde {desborde} px · filas {filas} · editor {editor} · «Enviar y siguiente» a la vista {vista} · <12px {len(chicos)}'
            print(linea)
            if raro: fallos.append((yo, ancho, f'texto raro en pantalla: {raro}'))
            if hoja: fallos.append((yo, ancho, 'la Bandeja inyecta su propia hoja de estilos'))
            if chicos: fallos.append((yo, ancho, f'texto < 12 px: {chicos}'))
            if errores: fallos.append((yo, ancho, errores[:3]))
            if desborde > 0: fallos.append((yo, ancho, f'desborde horizontal {desborde}px'))
            if ancho > 1000 and filas and editor and not vista and yo != 'setter_ana':
                fallos.append((yo, ancho, '«Enviar y siguiente» no queda a la vista sin desplazarse'))
            pg.screenshot(path=str(CAP / f'{yo}_{ancho}.jpg'), type='jpeg', quality=72, full_page=False)
            ctx.close()

    # ---- Tomás (real): borrador de la IA dentro del editor sin tocar la cola, huecos que bloquean, atajos y «Deshacer»
    ctx, pg, errores = nueva(nav, 1440, 900)
    pg.goto(f'{BASE}/?yo=lucia#/bandeja', wait_until='networkidle')
    pg.wait_for_timeout(2500)
    cola = lambda: pg.evaluate("fetch('api/acciones?modulo=bandeja').then(r => r.json()).then(d => (d.acciones || []).length).catch(() => -1)")
    n0 = cola()
    valor = pg.locator('#bdj-texto').input_value()
    print('IA · borrador ya en el editor:', valor[:70].replace('\n', ' | '))
    if not valor.strip(): fallos.append(('lucia', 'IA', 'el editor sale vacío (sin borrador ni plantilla)'))
    if cola() != n0: fallos.append(('lucia', 'IA', 'cargar el borrador ha puesto algo en la cola'))
    calidad = pg.inner_text('[data-bdj="calidad"]') if pg.locator('[data-bdj="calidad"]').count() else ''
    print('calidad:', calidad.replace('\n', ' '))
    if 'Calidad' not in calidad: fallos.append(('lucia', 'IA', 'falta «Calidad del borrador»'))
    # huecos: no se envía con [..]
    pg.fill('#bdj-texto', 'Hola,\n\nTe llamo [día y hora].\n\nUn saludo,')
    pg.click('[data-bdj-enviar="siguiente"]'); pg.wait_for_timeout(400)
    err = pg.locator('[data-bdj="editor"] [data-error]').inner_text() if pg.locator('[data-bdj="editor"] [data-error]').count() else ''
    print('huecos →', err)
    if '[día y hora]' not in err or cola() != n0: fallos.append(('lucia', 'huecos', 'deja enviar con huecos [..]'))
    # atajos: j / k / e (despachado) / z (deshacer)
    pg.mouse.click(700, 30)
    cur = lambda: pg.eval_on_selector_all('[data-bdj="lista"] [aria-current="true"]', 'xs => xs.map(x => x.dataset.id)')
    c0 = cur(); pg.keyboard.press('j'); pg.wait_for_timeout(300); c1 = cur(); pg.keyboard.press('k'); pg.wait_for_timeout(300); c2 = cur()
    print('j/k:', c0, c1, c2)
    if not (c0 == c2 and c0 != c1): fallos.append(('lucia', 'atajos', 'j/k no mueven la selección'))
    pg.keyboard.press('e'); pg.wait_for_timeout(500); c3 = cur()
    des = pg.locator('[data-deshacer] button:has-text("Deshacer")').count()
    pg.keyboard.press('z'); pg.wait_for_timeout(500); c4 = cur()
    print('e →', c3, '· Deshacer visible', des, '· z →', c4)
    if c3 == c0 or c4 != c0 or not des: fallos.append(('lucia', 'deshacer', 'e / z no despachan y deshacen'))
    pg.wait_for_timeout(8500)
    if cola() != n0: fallos.append(('lucia', 'deshacer', 'lo deshecho ha llegado a la cola'))
    # «Enviar y siguiente»: va a la cola simulada a los 8 s y aparece en envíos (simulado). ⌘↵ hace el botón principal
    # (que es «Cerrar sin responder» cuando el cerebro dice que no hace falta responder).
    cerrar = pg.locator('[data-bdj-enviar="cerrar"]:not([hidden])').count()
    print('«Cerrar sin responder» como principal:', bool(cerrar))
    pg.locator('#bdj-texto').fill('Hola,\n\nRecibido, lo miro hoy.\n\nUn saludo,')
    obj = cur()
    num = obj[0].replace('t-', '') if obj else ''
    pg.locator('[data-bdj-enviar="siguiente"]').click(); pg.wait_for_timeout(600)
    print('Enviar y siguiente:', obj, '→', cur())
    if cur() == obj: fallos.append(('lucia', 'enviar', '«Enviar y siguiente» no pasa al siguiente'))
    pg.wait_for_timeout(8800)
    print('cola antes/después:', n0, cola())
    if cola() != n0 + 1: fallos.append(('lucia', 'enviar', 'la respuesta no ha llegado a la cola simulada'))
    env = pg.evaluate("fetch('api/envios').then(r => r.json()).then(d => (d.envios || []).map(e => e.estado + ' ' + (e.destinatario || {}).ref))")
    print('envíos:', env[:3])
    if f'simulado {num}' not in env: fallos.append(('lucia', 'enviar', f'sin envío simulado de {num} en /api/envios'))
    vis = pg.locator('[data-bdj="lista"] [data-id="t-' + num + '"]').count()
    pg.locator('[data-bdj="mas"] > button').click(); pg.wait_for_timeout(200)
    pg.locator('.menu-flot [role="menuitem"]', has_text='Ya hechos').first.click(); pg.wait_for_timeout(500)
    pg.locator(f'[data-bdj="lista"] [data-id="t-{num}"]').first.click(); pg.wait_for_timeout(1500)
    estado = pg.locator('[data-bdj="envios"]').inner_text() if pg.locator('[data-bdj="envios"]').count() else ''
    print('estado del envío en el hilo:', estado.replace('\n', ' · ')[:140])
    if 'Simulado' not in estado: fallos.append(('lucia', 'enviar', 'el hilo no enseña el estado del envío'))
    pg.screenshot(path=str(CAP / 'lucia_1440_tras_enviar.jpg'), type='jpeg', quality=72)
    if errores: fallos.append(('lucia', 'flujo', errores[:3]))
    ctx.close()

    # ---- Tomás: vistas secundarias desde «Más», hilo legible y ruta directa
    ctx, pg, errores = nueva(nav, 1440, 900)
    pg.goto(f'{BASE}/?yo=tomas#/bandeja/t-RO-6627', wait_until='networkidle')
    pg.wait_for_timeout(2500)
    msgs = pg.locator('[data-bdj="hilo"] details[data-msg]').count()
    print('hilo RO-6627 · mensajes:', msgs, '· abierto:', cur() if False else pg.eval_on_selector_all('[data-bdj="lista"] [aria-current="true"]', 'xs => xs.map(x => x.dataset.id)'))
    if not msgs: fallos.append(('tomas', 'hilo', 'el hilo de RO-6627 no se lee en la app'))
    pg.screenshot(path=str(CAP / 'tomas_1440_hilo_RO-6627.jpg'), type='jpeg', quality=72)
    pg.goto(f'{BASE}/?yo=tomas#/bandeja/t-RO-6626', wait_until='networkidle')
    pg.wait_for_timeout(1500)
    abierto = pg.eval_on_selector_all('[data-bdj="lista"] [aria-current="true"]', 'xs => xs.map(x => x.dataset.id)')
    print('ruta directa RO-6626 →', abierto)
    if abierto != ['t-RO-6626']: fallos.append(('tomas', 'ruta', 'RO-6626 no se abre'))
    for vista in ('Correos sin responsable', 'WhatsApp', 'De dónde sale'):
        pg.locator('[data-bdj="mas"] > button').click(); pg.wait_for_timeout(200)
        pg.locator('.menu-flot [role="menuitem"]', has_text=vista).first.click(); pg.wait_for_timeout(500)
        pg.screenshot(path=str(CAP / f"tomas_1440_{vista.split()[0].lower().replace('ó', 'o')}.jpg"), type='jpeg', quality=72, full_page=True)
        pg.locator('button:has-text("Volver a la bandeja")').click(); pg.wait_for_timeout(400)
    if errores: fallos.append(('tomas', 'vistas', errores[:3]))
    ctx.close()

    # ---- móvil: lista → conversación a pantalla completa con el editor fijo abajo
    ctx, pg, errores = nueva(nav, 390, 844)
    pg.goto(f'{BASE}/?yo=candela#/bandeja', wait_until='networkidle')
    pg.wait_for_timeout(1500)
    if pg.locator('[data-bdj="lista"] [data-id]').count():
        pg.locator('[data-bdj="lista"] [data-id]').first.click(); pg.wait_for_timeout(2500)
        d = pg.evaluate('document.documentElement.scrollWidth - document.documentElement.clientWidth')
        fijo = en_vista(pg, '[data-bdj-enviar="siguiente"]')
        print('móvil conversación', pg.url.split('#')[1], '· desborde', d, '· editor abajo a la vista', fijo)
        if d > 0: fallos.append(('candela', 390, f'desborde en la conversación {d}px'))
        if not fijo: fallos.append(('candela', 390, 'el editor no queda fijo abajo'))
        pg.screenshot(path=str(CAP / 'candela_390_conversacion.jpg'), type='jpeg', quality=72)
        pg.mouse.wheel(0, 600); pg.wait_for_timeout(300)
        pg.screenshot(path=str(CAP / 'candela_390_conversacion_bajando.jpg'), type='jpeg', quality=72)
    if errores: fallos.append(('candela', 'móvil', errores[:3]))
    ctx.close()
    nav.close()

print('FALLOS:' if fallos else 'TODO BIEN', json.dumps(fallos, ensure_ascii=False)[:2000] if fallos else '')
sys.exit(1 if fallos else 0)

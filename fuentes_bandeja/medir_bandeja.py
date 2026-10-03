#!/usr/bin/env python3
"""Medición de usabilidad de la Bandeja con personas reales (Chrome sin cabeza, Playwright).

Cuenta CLICS y DESPLAZAMIENTOS (una «rueda» = 80 % de la altura de la caja que hay que mover) para dos tareas:
  A · «leer el correo más antiguo y dejar la respuesta lista para enviar»
  B · «procesar 5 correos seguidos» (dejar la respuesta lista y enviarla, cinco veces; el envío va a la cola SIMULADA)
Teclear no cuenta como clic (escribir la respuesta es igual en los dos diseños). Solo vale contra un servidor con COPIA de
la base (RO_DB=…), porque la tarea B deja acciones simuladas en la cola.

  python3 medir_bandeja.py <puerto> despues [persona,persona…] [--ancho 1440] [--alto 900] [--json salida.json]
  python3 medir_bandeja.py <puerto> antes …     (solo con el bandeja.js de la v4 servido: lo que se midió el 3-oct)
"""
import json
import math
import sys
from playwright.sync_api import sync_playwright

PUERTO = sys.argv[1] if len(sys.argv) > 1 else '9230'
MODO = sys.argv[2] if len(sys.argv) > 2 else 'despues'
GENTE = (sys.argv[3].split(',') if len(sys.argv) > 3 and not sys.argv[3].startswith('--') else
         ['lucia', 'candela', 'mili', 'tomas', 'yessica'])
ALTO = int(sys.argv[sys.argv.index('--alto') + 1]) if '--alto' in sys.argv else 900
ANCHO = int(sys.argv[sys.argv.index('--ancho') + 1]) if '--ancho' in sys.argv else 1440
SALIDA = sys.argv[sys.argv.index('--json') + 1] if '--json' in sys.argv else None
BASE = f'http://127.0.0.1:{PUERTO}'

# Ruedas para dejar un elemento entero a la vista, mirando la página y cada caja con su propio desplazamiento.
JS_RUEDAS = '''el => {
  let ruedas = 0;
  const cajas = [];
  for (let p = el.parentElement; p; p = p.parentElement) {
    const cs = getComputedStyle(p);
    if (/(auto|scroll)/.test(cs.overflowY) && p.scrollHeight > p.clientHeight + 2) cajas.push(p);
  }
  for (const c of cajas) {
    const r = el.getBoundingClientRect(), rc = c.getBoundingClientRect();
    const d = r.top < rc.top ? rc.top - r.top : r.bottom > rc.bottom ? Math.min(r.bottom - rc.bottom, r.top - rc.top) : 0;
    if (d > 2) { ruedas += Math.ceil(d / (c.clientHeight * 0.8)); c.scrollTop += (r.top < rc.top ? -d : d); }
  }
  const r = el.getBoundingClientRect(), H = innerHeight;
  const d = r.top < 0 ? -r.top : r.bottom > H ? Math.min(r.bottom - H, r.top) : 0;
  if (d > 2) { ruedas += Math.ceil(d / (H * 0.8)); scrollBy(0, r.top < 0 ? -d : d); }
  return ruedas;
}'''


class Cuenta:
    def __init__(self, pg):
        self.pg, self.clics, self.ruedas, self.pasos = pg, 0, 0, []

    def ver(self, loc, que):
        n = loc.evaluate(JS_RUEDAS)
        if n:
            self.ruedas += n
            self.pasos.append(f'{n} rueda(s) hasta {que}')
        return n

    def clic(self, loc, que, espera=600):
        self.ver(loc, que)
        loc.click()
        self.clics += 1
        self.pasos.append(f'clic: {que}')
        self.pg.wait_for_timeout(espera)


def mas_antiguo(pg, quien):
    """El correo de cliente sin contestar que más horas lleva (con cliente: se puede contestar; sin automáticos, boletines,
    los de más de un mes ni lo que ya tiene algo en la cola)."""
    d = pg.evaluate("fetch('api/modulo/bandeja/bandeja', {headers: {'X-RO-Yo': '%s'}}).then(r => r.json())" % quien)
    acc = pg.evaluate("fetch('api/acciones?modulo=bandeja', {headers: {'X-RO-Yo': '%s'}}).then(r => r.json()).then(d => d.acciones || []).catch(() => [])" % quien)
    hechos = {str(a.get('objeto')) for a in acc}     # lo que ya tiene algo en la cola (lo despachado en una pasada anterior)
    xs = [x for x in d.get('correos', []) if x.get('cliente_id') and not x.get('auto') and not x.get('viejo') and str(x.get('numero')) not in hechos]
    xs.sort(key=lambda x: -(x.get('horas') or 0))
    return xs[0]['id'] if xs else None


# ------------------------------------------------------------------ v4 (antes)
def antes_lista_respuesta(c, pg):
    ia = pg.locator('[data-ia="borrador"] button:has-text("Sugerir respuesta")')
    if ia.count():
        c.clic(ia.first, '«Sugerir respuesta»', 1500)
        usar = pg.locator('[data-ia="borrador"] button:has-text("Usar este borrador")')
        if usar.count():
            c.clic(usar.first, '«Usar este borrador»')
    ta = pg.locator('#bdj-texto')
    if ta.count():
        c.ver(ta, 'la caja de respuesta')
        return True
    return False


def antes_A(pg, quien):
    c = Cuenta(pg)
    obj = mas_antiguo(pg, quien)
    fila = pg.locator(f'main [role=list] [data-id="{obj}"]')
    if not fila.count():                         # en otra vista: «Todo»
        c.clic(pg.locator('[aria-label="Vista"] button[data-v="todo"]'), 'vista «Todo»')
    fila = pg.locator(f'main [role=list] [data-id="{obj}"]')
    if fila.count():
        c.clic(fila.first, f'la fila {obj}')
    ok = antes_lista_respuesta(c, pg)
    return c, ok, obj


def antes_B(pg, quien):
    c = Cuenta(pg)
    hechos = 0
    for _ in range(5):
        fila = pg.locator('main [role=list] [data-id]:not(.hecho)').first
        if not fila.count():
            break
        if fila.get_attribute('aria-current') != 'true':
            c.clic(fila, 'el siguiente correo')
        if not antes_lista_respuesta(c, pg):
            break
        ta = pg.locator('#bdj-texto')
        if not ta.input_value().strip():
            ta.fill('Hola,\n\nRecibido, lo miro hoy.\n\nUn saludo,')
        env = pg.locator('button:has-text("Enviar con mi firma")')
        c.clic(env.first, '«Enviar con mi firma»', 300)
        c.clic(pg.locator('button:has-text("Sí, enviar")').first, '«Sí, enviar»', 1800)
        hechos += 1
    return c, hechos


# ------------------------------------------------------------------ v5 (después)
def despues_lista(c, pg):
    ta = pg.locator('[data-bdj="editor"] #bdj-texto')
    try:
        pg.wait_for_function("() => { const t = document.querySelector('#bdj-texto'); return t && (t.value.trim().length > 0 || t.dataset.modo === 'nota') && !document.querySelector('[data-bdj=\"editor\"] .ia-cargando'); }", timeout=6000)
    except Exception:
        pass
    if not ta.count():
        return False
    c.ver(ta, 'el editor')
    return bool(ta.input_value().strip()) or ta.get_attribute('data-modo') == 'nota'   # sin cliente: nota (se despacha)


def despues_A(pg, quien):
    c = Cuenta(pg)
    obj = mas_antiguo(pg, quien)
    sel = '[data-bdj="lista"] [data-id][aria-current="true"]'
    actual = lambda: pg.locator(sel).get_attribute('data-id') if pg.locator(sel).count() else None
    en_lista = lambda: pg.locator(f'[data-bdj="lista"] [data-id="{obj}"]').count() > 0
    if actual() != obj and not en_lista():               # en otro filtro: «Sin responder» (todos los pendientes)
        c.clic(pg.locator('[data-filtro="sin_responder"]'), 'filtro «Sin responder»')
    if actual() != obj and pg.locator('[data-orden="antiguo"]').get_attribute('aria-pressed') != 'true':
        c.clic(pg.locator('[data-orden="antiguo"]'), 'orden «Más antiguo»')
    if actual() != obj and en_lista():
        c.clic(pg.locator(f'[data-bdj="lista"] [data-id="{obj}"]').first, f'la fila {obj}')
    ok = despues_lista(c, pg) and actual() == obj
    return c, ok, obj


def despues_B(pg, quien):
    c = Cuenta(pg)
    hechos = 0
    for _ in range(5):
        if not pg.locator('[data-bdj="lista"] [data-id]').count() and pg.locator('[data-filtro="sin_responder"]').count():
            c.clic(pg.locator('[data-filtro="sin_responder"]'), 'filtro «Sin responder» (Míos a cero)')
        if not despues_lista(c, pg):
            break
        ta = pg.locator('#bdj-texto')
        if ta.get_attribute('data-modo') == 'nota':           # sin cliente: no se contesta; se despacha (1 clic)
            antes = pg.locator('[data-bdj="lista"] [data-id][aria-current="true"]').get_attribute('data-id')
            c.clic(pg.locator('[data-bdj-acc="despachado"]'), '«Despachado» (sin cliente)', 900)
            hechos += 1
            continue
        v = ta.input_value()
        if '[' in v:                              # lo que falta (huecos del borrador): se teclea, no son clics
            import re
            ta.fill(re.sub(r'\[[^\]]*\]', 'mañana a las 10:00', v))
        antes = pg.locator('[data-bdj="lista"] [data-id][aria-current="true"]').get_attribute('data-id')
        c.clic(pg.locator('[data-bdj-enviar="siguiente"]'), '«Enviar y siguiente»', 900)
        despues = pg.locator('[data-bdj="lista"] [data-id][aria-current="true"]').get_attribute('data-id') if pg.locator('[data-bdj="lista"] [data-id][aria-current="true"]').count() else None
        if despues == antes:
            break
        hechos += 1
    pg.wait_for_timeout(9000)                    # que salgan los envíos con «Deshacer» (8 s, _deshacer.js) a la cola simulada
    return c, hechos


def main():
    """Primero la tarea A de todas las personas (con la base intacta: cada una busca su correo más antiguo) y después la B."""
    filas = {q: {'persona': q, 'modo': MODO, 'ancho': ANCHO, 'alto': ALTO} for q in GENTE}
    with sync_playwright() as p:
        nav = p.chromium.launch(channel='chrome', headless=True)
        for tarea in ('A', 'B'):
            for quien in GENTE:
                ctx = nav.new_context(viewport={'width': ANCHO, 'height': ALTO})
                pg = ctx.new_page()
                pg.goto(f'{BASE}/?yo={quien}#/bandeja', wait_until='networkidle')
                pg.wait_for_timeout(1500)
                if tarea == 'A':
                    c, ok, obj = (antes_A if MODO == 'antes' else despues_A)(pg, quien)
                    filas[quien]['A'] = {'clics': c.clics, 'ruedas': c.ruedas, 'ok': ok, 'correo': obj, 'pasos': c.pasos}
                else:
                    c, n = (antes_B if MODO == 'antes' else despues_B)(pg, quien)
                    filas[quien]['B'] = {'clics': c.clics, 'ruedas': c.ruedas, 'hechos': n, 'pasos': c.pasos[:14]}
                ctx.close()
        nav.close()
    for quien, f in filas.items():
        print(f"{quien:8} A: {f['A']['clics']} clics · {f['A']['ruedas']} ruedas · {'listo' if f['A']['ok'] else 'NO'} ({f['A']['correo']})"
              f"   B: {f['B']['clics']} clics · {f['B']['ruedas']} ruedas · {f['B']['hechos']}/5")
    if SALIDA:
        open(SALIDA, 'w').write(json.dumps(list(filas.values()), ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()

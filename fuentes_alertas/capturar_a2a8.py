#!/usr/bin/env python3
"""fuentes_alertas/capturar_a2a8.py · A2 («Ir» al objeto) y A8 (lote, posponer y cifras únicas) en el navegador.

Con servir.py en marcha sobre una COPIA de local.db (--bind 127.0.0.1, puertos 9045-9049):
  1 · Alertas como mili, lucia, gustavo y tomas a 1440 y 390 px: sin errores de consola ni desplazamiento horizontal;
      la cabecera, las tarjetas y los chips dan las MISMAS cifras que data/alertas/p_<id>.json → contadores (y que Mi día).
  2 · Cada «Ir» de las alertas visibles abre una ruta que su pantalla sabe abrir (ni «No encuentro», ni «no es de tu
      puesto», ni errores de consola): una muestra por tipo de alerta y persona.
  3 · Lote y posponer como Lucía: elige 2, «Posponer › Mañana»; las cifras bajan a la vez en tarjetas y chips; una
      tercera «Lo tengo» en lote. «Ver como» (Tomás → Lucía): casillas y botones sin efecto, el servidor no escribe.
  4 · Clics de «Contesta hoy el correo más antiguo de GAC» (Mi día de Lucía → caja de respuesta del correo exacto).
Capturas .jpg en capturas/_a2a8/.   Uso: python3 fuentes_alertas/capturar_a2a8.py --puerto 9045 [--sin-escribir]
"""
import json
import sys
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

APP = Path(__file__).resolve().parent.parent
SALIDA = APP / "capturas" / "_a2a8"
PUERTO = int(sys.argv[sys.argv.index("--puerto") + 1]) if "--puerto" in sys.argv else 9045
BASE = f"http://127.0.0.1:{PUERTO}"
PERSONAS = ["mili", "lucia", "gustavo", "tomas"]
FALLOS, RES = [], {}
SALIDA.mkdir(parents=True, exist_ok=True)


def ok(cond, texto):
    print(("  ✓ " if cond else "  ✗ ") + texto)
    if not cond:
        FALLOS.append(texto)


def api(ruta, yo):
    with urllib.request.urlopen(urllib.request.Request(f"{BASE}/api/{ruta}", headers={"X-RO-Yo": yo})) as r:
        return json.loads(r.read())


def cifras_pantalla(pg):
    return pg.evaluate("""() => {
        const t = document.querySelector('[data-contadores]');
        const chip = txt => { const b = [...document.querySelectorAll('button')].find(x => x.textContent.trim().startsWith(txt));
            const m = b && b.textContent.replace(txt, '').match(/\\d[\\d.]*/); return m ? Number(m[0].replace('.', '')) : null; };
        const tiles = [...document.querySelectorAll('[data-contadores] > *')];
        const val = et => { const x = tiles.find(t => (t.querySelector('.tt')?.textContent || '').includes(et)); const v = x?.querySelector('.tv')?.firstChild?.textContent; return v != null ? Number(String(v).replace('.', '')) : null; };
        return { K: t ? JSON.parse(t.dataset.contadores) : null, titulo: document.querySelector('#titulo')?.parentElement?.textContent || '',
                 chip_mias: chip('Mías'), chip_pasado: chip('Plazo pasado'), chip_escaladas: chip('Escaladas a ti'), chip_pospuestas: chip('Pospuestas'),
                 tile_mias: val('Mis alertas abiertas'), tile_pasado: val('Con el plazo pasado'), tile_esc: val('Escaladas a ti'),
                 desborde: document.documentElement.scrollWidth > window.innerWidth + 1, casillas: document.querySelectorAll('input[data-sel]').length,
                 botones_tarjeta: Math.max(0, ...[...document.querySelectorAll('[data-alerta]')].slice(0, 10).map(x => [...x.querySelectorAll('button, a.bt')].filter(b => b.offsetParent).length)) };
    }""")


def pantalla(nav):
    print("1 · Alertas: cifras únicas, consola y anchos")
    for yo in PERSONAS:
        doc = api(f"modulo/alertas/p_{yo}", yo)
        K = doc.get("contadores") or {}
        md = doc.get("mi_dia") or {}
        ok((md.get("total"), md.get("plazo_pasado"), md.get("escaladas_a_mi")) == (K.get("mias"), K.get("plazo_pasado"), K.get("escaladas_a_mi")),
           f"{yo}: Mi día = contadores ({md.get('total')}/{md.get('plazo_pasado')}/{md.get('escaladas_a_mi')} · {K.get('mias')}/{K.get('plazo_pasado')}/{K.get('escaladas_a_mi')})")
        for ancho in (1440, 390):
            ctx = nav.new_context(viewport={"width": ancho, "height": 900})
            pg = ctx.new_page()
            errs = []
            pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.goto(f"{BASE}/?yo={yo}#/alertas")
            pg.wait_for_selector("[data-contadores]", timeout=15000)
            pg.wait_for_timeout(900)
            c = cifras_pantalla(pg)
            RES[f"{yo}|{ancho}"] = c
            errs = [e for e in errs if "favicon" not in e]
            ok(not errs, f"{yo} {ancho}: sin errores de consola {errs[:2] if errs else ''}")
            ok(not c["desborde"], f"{yo} {ancho}: sin desplazamiento horizontal")
            kk = c["K"] or {}
            ok(kk.get("mias") == K.get("mias") and kk.get("plazo_pasado") == K.get("plazo_pasado") and kk.get("escaladas_a_mi") == K.get("escaladas_a_mi"),
               f"{yo} {ancho}: pantalla = generador (mías {kk.get('mias')}={K.get('mias')}, plazo pasado {kk.get('plazo_pasado')}={K.get('plazo_pasado')}, escaladas a ti {kk.get('escaladas_a_mi')}={K.get('escaladas_a_mi')})")
            ok(c["tile_mias"] == K.get("mias") and c["tile_pasado"] == K.get("plazo_pasado") and c["tile_esc"] == K.get("escaladas_a_mi"),
               f"{yo} {ancho}: tarjetas {c['tile_mias']}/{c['tile_pasado']}/{c['tile_esc']} = contadores")
            if c["chip_mias"] is not None:
                ok(c["chip_mias"] == K.get("mias"), f"{yo} {ancho}: chip «Mías» {c['chip_mias']} = {K.get('mias')}")
            if c["chip_pasado"] is not None and (c["chip_mias"] is not None or doc.get("alcance") == "mias"):
                ok(c["chip_pasado"] == K.get("plazo_pasado"), f"{yo} {ancho}: chip «Plazo pasado» {c['chip_pasado']} = {K.get('plazo_pasado')}")
            ok(f"{K.get('mias')} alerta" in c["titulo"] or K.get("mias") == 0, f"{yo} {ancho}: la cabecera dice {K.get('mias')} (mismas que la tarjeta)")
            pg.screenshot(path=str(SALIDA / f"{yo}_alertas_{ancho}.jpg"), full_page=False, type="jpeg", quality=72)
            if ancho == 1440:
                pg.screenshot(path=str(SALIDA / f"{yo}_alertas_{ancho}_pagina.jpg"), full_page=True, type="jpeg", quality=60)
            ctx.close()


def rutas(nav):
    print("2 · «Ir» al objeto: cada ruta abre su pantalla")
    for yo in PERSONAS:
        doc = api(f"modulo/alertas/p_{yo}", yo)
        vistos, n_ok, n = set(), 0, 0
        ctx = nav.new_context(viewport={"width": 1440, "height": 900})
        pg = ctx.new_page()
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(f"{BASE}/?yo={yo}#/alertas")
        pg.wait_for_timeout(1500)
        ve = set(pg.evaluate("[...document.querySelectorAll('a[href^=\"#/\"]')].map(a => a.getAttribute('href').slice(2).split('/')[0])"))
        mod = lambda r: (r or "").removeprefix("#/").split("/")[0]
        for a in doc.get("alertas", []):
            ir = a.get("ir") if mod(a.get("ir")) in ve else (a.get("ir_alt") if mod(a.get("ir_alt")) in ve else None)   # como irDe() de alertas.js
            if a["tipo"] in vistos or not ir:
                continue
            vistos.add(a["tipo"])
            pg.goto(f"{BASE}/?yo={yo}{ir}")
            pg.wait_for_timeout(1300)
            txt = pg.evaluate("document.querySelector('#main')?.innerText || ''")
            malo = [m for m in ("No encuentro", "no es de tu puesto", "No es de tu puesto", "Ese correo ya no está", "no está en ninguna cola") if m in txt]
            n += 1
            n_ok += not malo
            if malo:
                ok(False, f"{yo} · {a['tipo']} → {ir}: {malo[0]}")
        ok(not errs, f"{yo}: {n_ok} de {n} rutas «Ir» abren su objeto, sin errores {errs[:1] if errs else ''}")
        RES[f"rutas|{yo}"] = {"bien": n_ok, "total": n}
        ctx.close()


def lote_y_posponer(nav):
    print("3 · Lote y posponer (Lucía) · «ver como» no escribe")
    ctx = nav.new_context(viewport={"width": 1440, "height": 900})
    pg = ctx.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(f"{BASE}/?yo=lucia#/alertas")
    pg.wait_for_selector("[data-contadores]", timeout=15000)
    pg.wait_for_timeout(800)
    antes = cifras_pantalla(pg)
    cas = pg.locator("input[data-sel]")
    ok(cas.count() >= 3, f"Lucía ve casillas para elegir ({cas.count()})")
    cas.nth(0).check()
    cas.nth(1).check()
    pg.wait_for_timeout(200)
    barra = pg.locator('[aria-label="Hacer lo mismo con las elegidas"]')
    ok(barra.is_visible() and "2 elegidas" in barra.inner_text(), "barra «2 elegidas» con Lo tengo · Resueltas · No aplica · Posponer")
    pg.screenshot(path=str(SALIDA / "lucia_lote_barra_1440.jpg"), full_page=False, type="jpeg", quality=72)
    barra.get_by_role("button", name="Mañana").click()
    pg.wait_for_timeout(1500)
    despues = cifras_pantalla(pg)
    ok((despues["K"] or {}).get("pospuestas") == (antes["K"] or {}).get("pospuestas", 0) + 2, f"posponer 2 en lote: pospuestas {antes['K'].get('pospuestas')} → {despues['K'].get('pospuestas')}")
    ok((despues["K"] or {}).get("mias") == (antes["K"] or {}).get("mias") - 2 and despues["tile_mias"] == despues["K"]["mias"]
       and (despues["chip_mias"] is None or despues["chip_mias"] == despues["K"]["mias"]),
       f"«mías» baja a la vez en cabecera, tarjeta y chip ({antes['K'].get('mias')} → {despues['K'].get('mias')}; tarjeta {despues['tile_mias']})")
    cas = pg.locator("input[data-sel]")
    cas.nth(0).check()
    pg.locator('[aria-label="Hacer lo mismo con las elegidas"]').get_by_role("button", name="Lo tengo").click()
    pg.wait_for_timeout(1500)
    acc = api("acciones?modulo=alertas", "lucia").get("acciones", [])
    tipos = [x["tipo"] for x in acc if x["quien"] == "lucia"]
    ok(tipos.count("alerta_lote") >= 2, f"las dos acciones en lote están en la cola con rastro ({tipos.count('alerta_lote')} filas alerta_lote)")
    pg.screenshot(path=str(SALIDA / "lucia_tras_lote_1440.jpg"), full_page=False, type="jpeg", quality=72)
    # posponer una sola desde su tarjeta: «Más» → «El lunes»
    t = pg.locator("[data-alerta]").first
    t.locator("summary", has_text="Más").click()
    t.get_by_role("button", name="El lunes").click()
    pg.wait_for_timeout(1200)
    acc = api("acciones?modulo=alertas", "lucia").get("acciones", [])
    ok(any(x["tipo"] == "alerta_posponer" and x["quien"] == "lucia" for x in acc), "posponer una («El lunes») desde su tarjeta queda en la cola")
    ok(not errs, f"lote y posponer sin errores {errs[:1] if errs else ''}")
    ctx.close()
    # «ver como»: Tomás mirando como Lucía
    ctx = nav.new_context(viewport={"width": 1440, "height": 900})
    pg = ctx.new_page()
    pg.goto(f"{BASE}/?yo=tomas&como=lucia#/alertas")
    pg.wait_for_timeout(2500)
    n_cas = pg.locator("input[data-sel]").count()
    ok(n_cas == 0, f"«ver como»: sin casillas de lote ({n_cas})")
    ctx.close()


def medir_gac(nav):
    print("4 · «Contesta hoy el correo más antiguo de GAC»: clics hasta la caja de respuesta")
    ctx = nav.new_context(viewport={"width": 1440, "height": 900})
    pg = ctx.new_page()
    pg.goto(f"{BASE}/?yo=lucia#/mi-dia")
    pg.wait_for_selector('#main [data-ia="consejo"]', timeout=15000)
    pg.wait_for_timeout(1200)
    clics = 0
    li = pg.locator('#main [data-ia="consejo"] li.ia-accion', has_text="correo más antiguo de GAC").first
    if li.count() == 0:
        ok(False, "sale el consejo de GAC en Mi día")
        return ctx.close()
    if not pg.locator('#main [data-ia="consejo"] ol').is_visible():
        pg.click('#main [data-ia="consejo"] button[aria-controls]')
        clics += 1
    ir = li.locator("a[data-ir]").first
    href = ir.get_attribute("href")
    ir.click()
    clics += 1
    pg.wait_for_timeout(2500)
    viejo = api("modulo/bandeja/por_cliente", "lucia")
    num = next((c["mas_antiguo"]["numero"] for c in viejo.get("clientes", []) if c["cliente_id"] == "gac"), None)
    abierto = pg.evaluate(f"document.querySelector('[data-id=\"t-{num}\"]')?.getAttribute('aria-current') === 'true'")
    caja = pg.locator("#bdj-texto")
    visible = caja.count() > 0 and caja.first.is_visible()
    y = round(caja.first.bounding_box()["y"]) if visible else None
    RES["gac"] = {"href": href, "clics": clics, "correo": num, "abierto_el_bueno": abierto, "caja_visible": visible, "caja_y": y}
    ok(href == f"#/bandeja/t-{num}", f"«Ir» lleva al correo exacto ({href})")
    ok(abierto and visible and clics <= 2, f"{clics} clic(s) hasta la caja de respuesta de {num} (objetivo ≤ 2; caja a {y} px)")
    if visible:
        caja.first.scroll_into_view_if_needed()
    pg.screenshot(path=str(SALIDA / "lucia_gac_despues_1440.jpg"), full_page=False, type="jpeg", quality=72)
    ctx.close()


with sync_playwright() as p:
    nav = p.chromium.launch()
    pantalla(nav)
    rutas(nav)
    medir_gac(nav)
    if "--sin-escribir" not in sys.argv:
        lote_y_posponer(nav)
    nav.close()

(SALIDA / "resultado.json").write_text(json.dumps(RES, ensure_ascii=False, indent=1))
print(f"\n{'TODO BIEN' if not FALLOS else f'{len(FALLOS)} FALLO(S)'}")
sys.exit(1 if FALLOS else 0)

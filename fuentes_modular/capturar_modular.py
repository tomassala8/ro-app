#!/usr/bin/env python3
"""fuentes_modular/capturar_modular.py · N5 Modular DS en el navegador (3-oct-2026).

Con servir.py en marcha (COPIA de local.db, --bind 127.0.0.1, puerto 9285-9289): entra como Jerónimo (jefe de SEO y web),
Macarena (web), Lucía (account) y Tomás (dirección) a 1440 y 390 px y guarda en capturas/_modular/*.jpg:
  · el tablero de webs (SEO, ficha y webs › Webs) de quien lo ve, y
  · el bloque «Estado de la web (Modular)» de la ficha del cliente (pestaña Web y SEO), una web en Modular y otra fuera.
Comprueba: consola sin errores, sin desplazamiento horizontal, el tablero solo para web / jefe / dirección, la primera fila
del tablero a menos de 300 px, «Entrar al WordPress» solo para web / jefe / dirección (y que responde «apagado»), y que el
bloque de la ficha sale con sus cifras o con «Añadir a Modular».

Uso: python3 fuentes_modular/capturar_modular.py --puerto 9285
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

APP = Path(__file__).resolve().parent.parent
SALIDA = APP / "capturas" / "_modular"
PUERTO = int(sys.argv[sys.argv.index("--puerto") + 1]) if "--puerto" in sys.argv else 9285
BASE = f"http://127.0.0.1:{PUERTO}"
SALIDA.mkdir(parents=True, exist_ok=True)

# (persona, ruta, qué se mira, ¿ve tablero / entrar?)
CASOS = [
    ("jeronimo", "seo-web/webs/", "tablero", True),
    ("macarena", "seo-web/webs/", "tablero", True),
    ("macarena", "ficha/accompany/web", "ficha", True),
    ("lucia", "seo-web/webs/", "sin_tablero", False),
    ("lucia", "ficha/fusterguell/web", "ficha", False),
    ("lucia", "ficha/joan-lluis-vives/web", "ficha_fuera", False),
    ("tomas", "seo-web/webs/", "tablero", True),
    ("tomas", "ficha/octoedro/web", "ficha", True),
]

LEER = """(que) => {
  const t = document.querySelector('[data-trabajo="webs-tablero"]');
  const f = document.querySelector('[data-modular]');
  const main = document.getElementById('main');
  const li = t ? t.querySelector('ol.primero > li') : null;
  const zona = que.startsWith('ficha') ? f : t;
  return {
    tablero: !!t, filas: t ? t.querySelectorAll('ol.primero > li').length : 0,
    primera: li && main ? Math.round(li.getBoundingClientRect().top - main.getBoundingClientRect().top) : null,
    ficha: !!f, ficha_cifras: f ? f.querySelectorAll('.tile').length : 0, ficha_fuera: f ? /no está en Modular/.test(f.innerText) : false,
    ficha_problemas: f ? f.querySelectorAll('ol.primero > li').length : 0,
    entrar: [...document.querySelectorAll('#main button')].filter(b => b.textContent.includes('Entrar al WordPress')).length,
    abrir: [...document.querySelectorAll('#main a')].filter(a => a.textContent.includes('Abrir en Modular')).length,
    desborde: document.documentElement.scrollWidth > window.innerWidth + 1,
    texto: zona ? zona.innerText.slice(0, 160) : null };
}"""

fallos = []


def ok(c, t):
    print(("✓ " if c else "✗ ") + t)
    if not c:
        fallos.append(t)


with sync_playwright() as p:
    nav = p.chromium.launch()
    for yo, ruta, que, ve in CASOS:
        for ancho in (1440, 390):
            ctx = nav.new_context(viewport={"width": ancho, "height": 900})
            pag = ctx.new_page()
            err = []
            pag.on("console", lambda m: err.append(m.text) if m.type == "error" else None)
            pag.on("pageerror", lambda e: err.append(str(e)))
            pag.goto(f"{BASE}/?yo={yo}#/{ruta}")
            sel = '[data-modular] .tile, [data-modular] .vacio, [data-modular] .vacio-linea' if que.startswith('ficha') else ('[data-trabajo="webs-tablero"] ol.primero > li' if que == 'tablero' else '#seo-pestanas')
            try:
                pag.wait_for_selector(sel, timeout=15000)
            except Exception:
                pass
            pag.wait_for_timeout(1500)
            r = pag.evaluate(LEER, que)
            nombre = f"{yo}_{que}_{ancho}"
            et = f"{yo} · {ruta} · {ancho}"
            ok(not err, f"{et}: consola sin errores {err[:2] if err else ''}")
            ok(not r["desborde"], f"{et}: sin desplazamiento horizontal")
            if que == "tablero":
                ok(r["tablero"] and r["filas"] > 0, f"{et}: tablero con {r['filas']} filas")
                ok(r["primera"] is not None and r["primera"] <= 300, f"{et}: primera fila a {r['primera']} px (≤ 300)")
                ok(r["abrir"] > 0, f"{et}: «Abrir en Modular ↗» a la vista ({r['abrir']})")
            if que == "sin_tablero":
                ok(not r["tablero"], f"{et}: un account no ve el tablero de todas las webs")
            if que == "ficha":
                ok(r["ficha"] and r["ficha_cifras"] >= 8 and r["ficha_problemas"] > 0, f"{et}: bloque de Modular con {r['ficha_cifras']} cifras y {r['ficha_problemas']} problemas con acción")
            if que == "ficha_fuera":
                ok(r["ficha"] and r["ficha_fuera"], f"{et}: «Esta web no está en Modular» con «Añadir a Modular»")
            ok((r["entrar"] > 0) == ve or que in ("ficha_fuera", "sin_tablero"), f"{et}: «Entrar al WordPress» {'sí' if ve else 'no'} ({r['entrar']})")
            # captura: el tablero o el bloque de la ficha
            zona = pag.query_selector('[data-modular]' if que.startswith('ficha') else '[data-trabajo="webs-tablero"]') if que != 'sin_tablero' else None
            if zona:
                zona.scroll_into_view_if_needed()
                pag.wait_for_timeout(300)
                if ancho == 390:
                    zona.screenshot(path=str(SALIDA / f"{nombre}.jpg"), type="jpeg", quality=78)
                else:
                    pag.evaluate("(el) => window.scrollBy(0, el.getBoundingClientRect().top - 72)", zona)
                    pag.wait_for_timeout(300)
                    pag.screenshot(path=str(SALIDA / f"{nombre}.jpg"), type="jpeg", quality=78)
            else:
                pag.screenshot(path=str(SALIDA / f"{nombre}.jpg"), type="jpeg", quality=78)
            if que == "tablero" and yo == "macarena" and ancho == 1440:   # «Entrar al WordPress» responde «apagado» (clave de solo lectura)
                b = pag.query_selector('[data-webs-detalle] button:has-text("Entrar al WordPress")')
                if b:
                    b.click()
                    pag.wait_for_timeout(1200)
                    t = pag.evaluate("() => document.querySelector('[data-webs-detalle]').innerText")
                    ok("apagado" in t, "macarena: «Entrar al WordPress» dice que el acceso de un clic está apagado")
            ctx.close()
    nav.close()
print(f"\n{'TODO BIEN' if not fallos else f'{len(fallos)} FALLO(S)'} · capturas en {SALIDA}")
sys.exit(1 if fallos else 0)

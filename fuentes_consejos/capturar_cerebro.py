#!/usr/bin/env python3
"""fuentes_consejos/capturar_cerebro.py · cerebro de decisiones v2 (3-oct-2026) en el navegador.

Con servir.py en marcha (COPIA de local.db, --bind 127.0.0.1, puerto 9265-9269): entra como 6 personas en Mi día y en su
pantalla de trabajo a 1440 y 390 px, guarda el bloque «Qué haría yo hoy aquí» en capturas/_cerebro/*.jpg y comprueba:
consola sin errores, sin desplazamiento horizontal, fila de valoración con «Primero porque…», criterio y los 3 botones;
pulsa «Útil» en el primer consejo de Lucía y mira que lo anota; en «ver como» los botones salen desactivados.

Uso: python3 fuentes_consejos/capturar_cerebro.py --puerto 9265
"""
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

APP = Path(__file__).resolve().parent.parent
SALIDA = APP / "capturas" / "_cerebro"
PUERTO = int(sys.argv[sys.argv.index("--puerto") + 1]) if "--puerto" in sys.argv else 9265
BASE = f"http://127.0.0.1:{PUERTO}"
RUTAS = {"lucia": ["mi-dia", "ficha/gac/resumen"], "lina": ["mi-dia", "captacion"], "gustavo": ["mi-dia", "salud-crm"],
         "valeria": ["mi-dia"], "tomas": ["mi-dia", "ventas-ro"], "mili": ["mi-dia"]}
SALIDA.mkdir(parents=True, exist_ok=True)

LEER = """() => {
  const b = document.querySelector('#main [data-ia="consejo"]');
  const vs = b ? [...b.querySelectorAll('[data-ia="valoracion"]')] : [];
  return { consejo: !!b, n: b ? b.querySelectorAll('.ia-accion').length : 0, filas: vs.length,
           motivo: vs[0]?.querySelector('span')?.textContent || null,
           criterio: vs.map(v => v.querySelector('[data-criterio]')?.textContent || null),
           botones: vs.length ? vs[0].querySelectorAll('[data-valorar]').length : 0,
           desactivados: vs.length ? [...vs[0].querySelectorAll('[data-valorar]')].every(x => x.disabled) : null,
           euros: b ? /\\d\\s?€/.test(b.innerText) : false,
           desborde: document.documentElement.scrollWidth > window.innerWidth + 1 };
}"""

res, fallos = {}, []
with sync_playwright() as p:
    nav = p.chromium.launch()
    casos = [(yo, r, a, None) for yo, rs in RUTAS.items() for r in rs for a in (1440, 390)] + [("tomas", "mi-dia", 1440, "lucia")]
    for yo, ruta, ancho, como in casos:
        ctx = nav.new_context(viewport={"width": ancho, "height": 900})
        if como:
            ctx.add_init_script(f"try {{ sessionStorage.setItem('ro.vercomo', '{yo}:{como}'); }} catch (e) {{}}")
        pag = ctx.new_page()
        err = []
        pag.on("console", lambda m: err.append(m.text) if m.type == "error" else None)
        pag.on("pageerror", lambda e: err.append(str(e)))
        pag.goto(f"{BASE}/?yo={yo}#/{ruta}")
        try:
            pag.wait_for_selector('#main [data-ia="consejo"]', timeout=12000)
        except Exception:
            pass
        pag.wait_for_timeout(800)
        for _ in range(2):                                     # plegado: «Ver los consejos» (Mi día lo vuelve a pintar al filtrar)
            hecho = pag.evaluate("""() => { const bt = document.querySelector('#main [data-ia="consejo"] .ia-cab button[aria-expanded="false"]');
                                         if (!bt) return false; bt.click(); return true; }""")
            if not hecho:
                break
            pag.wait_for_timeout(500)
        b = pag.query_selector('#main [data-ia="consejo"]')
        if b and not b.is_visible():
            b = None                      # Mi día oculta el bloque si todo lo suyo ya está en «Lo mío» (no es un fallo)
        d = pag.evaluate(LEER)
        nombre = f"{yo}{'_como_' + como if como else ''}_{ruta.replace('/', '_')}_{ancho}"
        if b:
            b.screenshot(path=str(SALIDA / f"{nombre}.jpg"), type="jpeg", quality=80)
        else:
            pag.screenshot(path=str(SALIDA / f"{nombre}.jpg"), type="jpeg", quality=70)
        if yo == "lucia" and ruta == "mi-dia" and ancho == 1440 and d["filas"] and b:
            pag.locator('#main [data-ia="valoracion"] [data-valorar="util"]:visible').first.click()
            pag.wait_for_timeout(800)
            d["tras_util"] = pag.evaluate("() => [...document.querySelectorAll('#main [data-ia=\"valoracion\"] [role=status]')].map(x => x.textContent).filter(Boolean).join(' ')")
            d["pulsado"] = pag.evaluate("() => [...document.querySelectorAll('#main [data-ia=\"valoracion\"] [data-valorar=\"util\"]')].some(x => x.getAttribute('aria-pressed') === 'true')")
            b.screenshot(path=str(SALIDA / f"{nombre}_tras_util.jpg"), type="jpeg", quality=80)
        if como:   # en «ver como», Mi día pide alertas/p_<vista> y el servidor responde 403 (solo_propio): ajeno al cerebro
            d["ignorado"] = [e for e in err if "status of 403" in e]
            err = [e for e in err if "status of 403" not in e]
        d["errores"] = err[:3]
        res[nombre] = d
        d["visible"] = bool(b)
        if err or d["desborde"] or (b and (d["filas"] != d["n"] or d["botones"] != 3)):
            fallos.append(nombre)
        if como and d["filas"] and not d["desactivados"]:
            fallos.append(f"{nombre}: botones activos en «ver como»")
        if yo in ("lina", "gustavo", "valeria") and d["motivo"] and "€/mes" in d["motivo"]:
            fallos.append(f"{nombre}: euros en el motivo")
        ctx.close()
    nav.close()

(SALIDA / "_resultado.json").write_text(json.dumps(res, ensure_ascii=False, indent=1))
for k, d in res.items():
    print(f"{'✗' if k in fallos else '✓'} {k}: {d['n']} consejos · motivo «{(d['motivo'] or '—')[:90]}» · errores {len(d['errores'])}"
          + (f" · tras «Útil»: {d.get('tras_util')} ({d.get('pulsado')})" if "tras_util" in d else ""))
print(f"\n{len(res) - len([f for f in fallos if ':' not in f])} bien · fallos: {fallos or 'ninguno'}")
sys.exit(1 if fallos else 0)

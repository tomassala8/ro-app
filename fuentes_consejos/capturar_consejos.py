#!/usr/bin/env python3
"""fuentes_consejos/capturar_consejos.py · N12 + V2-B · «Qué haría yo hoy aquí», el copiloto y ⌘K en el navegador.

Con servir.py en marcha (COPIA de local.db, --bind 127.0.0.1): entra como cada persona en su inicio y en sus pantallas
de trabajo, a 1440, 1024 y 390 px. Guarda capturas .jpg en capturas/_v2b/ y mira: consola, desplazamiento horizontal,
cuántos consejos salen, el primero, el sello (día y fuentes con retraso), el «null» del copiloto en la ficha, que
«Ir a «Llamar ya»» abre la pestaña y que «Contestar el correo más antiguo» abre el mismo correo que Mi día.

Uso: python3 fuentes_consejos/capturar_consejos.py --puerto 9135 [--anchos 1440,390]
"""
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

APP = Path(__file__).resolve().parent.parent
SALIDA = APP / "capturas" / "_v2b"
PUERTO = int(sys.argv[sys.argv.index("--puerto") + 1]) if "--puerto" in sys.argv else 8770
ANCHOS = [int(x) for x in (sys.argv[sys.argv.index("--anchos") + 1] if "--anchos" in sys.argv else "1440,1024,390").split(",")]
BASE = f"http://127.0.0.1:{PUERTO}"
RUTAS = {
    "lucia": ["mi-dia", "ficha/gac/resumen", "produccion"], "candela": ["mi-dia", "ficha/garmande/resumen"],
    "agustina": ["mi-dia", "clientes-nuevos"], "tomas": ["mi-dia", "ventas-ro", "asistente-ia"],
    "constanza": ["mi-dia", "en-rojo/gac"], "camilo": ["mi-dia", "produccion"], "eulimar": ["mi-dia", "prospeccion"],
    "yessica": ["mi-dia", "ficha/garmande/resumen"], "valeria": ["mi-dia", "captacion"], "jeronimo": ["mi-dia", "seo-web"],
    "macarena": ["ficha/fitec-asesores/resumen"], "lara": ["ficha/concilia/resumen"], "setter_ana": ["setters"],
}
SALIDA.mkdir(parents=True, exist_ok=True)
res = {}

LEER = """() => {
    const b = document.querySelector('#main [data-ia="consejo"]');
    const main = document.querySelector('#main');
    const texto = main?.innerText || '';
    return {
        consejo: !!b, n: b ? b.querySelectorAll('.ia-accion').length : 0,
        plegado: b ? b.querySelector('ol').hidden : null,
        textos: b ? [...b.querySelectorAll('.ia-accion > div > b')].map(x => x.textContent) : [],
        sello: b ? [...b.querySelectorAll('.ia-cab .chip, .ia-cab [class*="chip"]')].map(x => x.textContent) : [],
        avisar: b ? b.querySelectorAll('button').length : 0,
        null_suelto: /(^|[\\s>])null([\\s<]|$)/.test(texto) || /\\bundefined\\b|NaN/.test(texto),
        copiloto: !!document.querySelector('#main [data-ia="copiloto"]'),
        copiloto_chip: document.querySelector('#main [data-ia="copiloto"] .ia-cab')?.textContent || null,
        bloque_copiloto: !!document.querySelector('#main [data-ia="bloque"]'),
        desborde: document.documentElement.scrollWidth > window.innerWidth + 1,
    };
}"""

with sync_playwright() as p:
    nav = p.chromium.launch()
    for yo, rutas in RUTAS.items():
        for ruta in rutas:
            for ancho in ANCHOS:
                ctx = nav.new_context(viewport={"width": ancho, "height": 900})
                pag = ctx.new_page()
                errores = []
                pag.on("console", lambda m: errores.append(m.text) if m.type == "error" else None)
                pag.on("pageerror", lambda e: errores.append(str(e)))
                pag.goto(f"{BASE}/?yo={yo}#/{ruta}")
                try:
                    pag.wait_for_selector('#main [data-ia="consejo"]', timeout=9000)
                except Exception:
                    pass
                pag.wait_for_timeout(1800 if "ficha" in ruta or "asistente" in ruta else 1000)
                info = pag.evaluate(LEER)
                bt = pag.locator('#main [data-ia="consejo"] button[aria-controls]').first
                if info["consejo"] and info["plegado"] and bt.is_visible():   # en el móvil sale plegado: se abre para la captura
                    bt.click()
                    pag.wait_for_timeout(300)
                nombre = f"{yo}_{ruta.replace('/', '-')}_{ancho}.jpg"
                pag.screenshot(path=str(SALIDA / nombre), full_page=False, type="jpeg", quality=70)
                info["errores"] = [e for e in errores if "favicon" not in e]
                res[f"{yo}|{ruta}|{ancho}"] = info
                ctx.close()

    # «Ir a «Llamar ya»» (setter): deja elegida la pestaña de la lista
    ctx = nav.new_context(viewport={"width": 1440, "height": 900})
    pag = ctx.new_page()
    pag.goto(f"{BASE}/?yo=setter_ana#/setters")
    pag.wait_for_selector('#main [data-ia="consejo"]', timeout=9000)
    pag.wait_for_timeout(800)
    b = pag.locator('#main [data-ia="consejo"] [data-ir="pestana"]')
    if b.count():
        b.nth(min(1, b.count() - 1)).click()
        pag.wait_for_timeout(500)
    res["pestana_setter"] = pag.evaluate("() => document.querySelector('#main [role=tab][aria-selected=true]')?.textContent || null")
    ctx.close()

    # ⌘K «contestar gac» (Lucía): el mismo correo que «Lo mío» de Mi día da como más antiguo de GAC
    ctx = nav.new_context(viewport={"width": 1440, "height": 900})
    pag = ctx.new_page()
    pag.goto(f"{BASE}/?yo=lucia#/mi-dia")
    pag.wait_for_timeout(3500)
    mi_dia = pag.evaluate("""async () => {
        const LM = await import('./modulos/mi_dia_bloques.js');
        const RO = window.RO;
        const bj = await RO.api('modulo/bandeja/bandeja');
        const acc = await RO.api('acciones').catch(() => ({ acciones: [] }));
        const ctx = RO.ctxPara ? RO.ctxPara('mi-dia') : null;
        // la misma regla que bandejaComoPantalla: sin automáticos, sin viejos y sin lo despachado
        const hechos = new Set((acc.acciones || []).filter(a => a.modulo === 'bandeja').map(a => String(a.objeto)));
        const vivos = (bj.correos || []).filter(x => !x.auto && !x.viejo && !hechos.has(String(x.numero ?? x.id)) && x.cliente_id === 'gac');
        return vivos.sort((a, b) => (b.horas || 0) - (a.horas || 0))[0]?.id || null; }""")
    pag.keyboard.press("Meta+k")
    pag.wait_for_timeout(600)
    pag.keyboard.type("contestar gac")
    pag.wait_for_timeout(1500)
    accion = pag.evaluate("() => [...document.querySelectorAll('#paleta [role=option], #paleta li')].map(x => x.textContent).find(t => /correo más antiguo/i.test(t)) || null")
    pag.keyboard.press("Enter")
    pag.wait_for_timeout(1200)
    res["cmdk_gac"] = {"mi_dia_mas_antiguo": mi_dia, "accion": accion, "abre": pag.evaluate("location.hash")}
    pag.screenshot(path=str(SALIDA / "lucia_cmdk_contestar_gac_1440.jpg"), full_page=False, type="jpeg", quality=70)
    ctx.close()
    nav.close()

malos = {k: v for k, v in res.items() if isinstance(v, dict) and (v.get("errores") or v.get("desborde") or v.get("null_suelto"))}
print(json.dumps(res, ensure_ascii=False, indent=1))
print(f"\n{len(res)} comprobaciones · con problemas: {list(malos) or 'ninguna'}")
(SALIDA / "resultado.json").write_text(json.dumps(res, ensure_ascii=False, indent=1))

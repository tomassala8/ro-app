#!/usr/bin/env python3
"""fuentes_ia/capturar_ia.py · N3 · prueba en navegador y capturas del Asistente IA.

Con servir.py en marcha: entra como las 7 personas de la definición de «hecho» en #/asistente-ia (1440 y 390 px),
guarda capturas en capturas/asistente_ia/, mira la consola y el desplazamiento horizontal, y prueba el componente
botonIA con una caja de respuesta (lo que hará la Bandeja): «Sugerir respuesta» → «Usar» rellena la caja.

Uso: python3 fuentes_ia/capturar_ia.py --puerto 8783
"""
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

APP = Path(__file__).resolve().parent.parent
SALIDA = APP / "capturas" / "asistente_ia"
PUERTO = int(sys.argv[sys.argv.index("--puerto") + 1]) if "--puerto" in sys.argv else 8770
BASE = f"http://127.0.0.1:{PUERTO}"
PERSONAS = ["tomas", "mili", "lucia", "valeria", "yessica", "constanza", "setter_ana"]
SALIDA.mkdir(parents=True, exist_ok=True)
res = {}


def abrir(pag, yo, ruta, ancho):
    errores = []
    pag.on("console", lambda m: errores.append(m.text) if m.type == "error" else None)
    pag.on("pageerror", lambda e: errores.append(str(e)))
    pag.set_viewport_size({"width": ancho, "height": 900})
    pag.goto(f"{BASE}/?yo={yo}#/{ruta}")
    pag.wait_for_timeout(2500)
    return errores


with sync_playwright() as p:
    nav = p.chromium.launch()
    for yo in PERSONAS:
        for ancho in (1440, 390):
            ctx = nav.new_context()
            pag = ctx.new_page()
            err = abrir(pag, yo, "asistente-ia", ancho)
            info = pag.evaluate("""() => ({
                titulo: document.querySelector('#titulo')?.textContent,
                clientes: document.querySelectorAll('.asi-lista button').length,
                acciones: document.querySelectorAll('.ia-accion').length,
                vacio: document.querySelector('#main .vacio-g b, #main .vacio b')?.textContent || null,
                desborde: document.documentElement.scrollWidth > window.innerWidth + 1,
                texto: (document.querySelector('#main')?.innerText || '').slice(0, 160)
            })""")
            if yo in ("tomas", "lucia"):
                pag.screenshot(path=str(SALIDA / f"{yo}_copiloto_{ancho}.png"), full_page=True)
                b = pag.query_selector('button[role="tab"]:has-text("Borradores")')
                if b:
                    b.click(); pag.wait_for_timeout(1500)
                    info["borradores"] = pag.evaluate("document.querySelectorAll('.asi-lista button').length")
                    info["borrador_pintado"] = pag.evaluate("!!document.querySelector('.ia-caja textarea')")
                    info["desborde_borradores"] = pag.evaluate("document.documentElement.scrollWidth > window.innerWidth + 1")
                    pag.screenshot(path=str(SALIDA / f"{yo}_borradores_{ancho}.png"), full_page=True)
            info["errores"] = [e for e in err if "favicon" not in e]
            res[f"{yo}_{ancho}"] = info
            ctx.close()

    # El componente con una caja de respuesta, como lo usará la Bandeja (Lucía, ticket suyo)
    ctx = nav.new_context(); pag = ctx.new_page()
    err = abrir(pag, "lucia", "asistente-ia", 1440)
    lista = pag.evaluate("fetch('api/ia/lista', {headers: {'X-RO-Yo': 'lucia'}}).then(r => r.json())")
    ticket = lista["borradores"][0]["ticket"]
    pag.evaluate("""async (ticket) => {
        const { botonIA } = await import('./modulos/ia_componentes.js');
        const main = document.querySelector('#main');
        const ta = document.createElement('textarea'); ta.id = 'bdj-texto'; ta.style.width = '100%';
        const ctx = { api: (ruta, op = {}) => fetch('api/' + ruta, { method: op.metodo || 'GET', headers: { 'X-RO-App': '1', 'X-RO-Yo': 'lucia', 'Content-Type': 'application/json' }, body: op.cuerpo ? JSON.stringify(op.cuerpo) : undefined }).then(async r => { const d = await r.json(); if (!r.ok) { const e = new Error(d.error); e.status = r.status; throw e; } return d; }),
                      rastro: () => {}, veModulo: () => true, soloLectura: false, persona: { id: 'lucia' } };
        const caja = document.createElement('section'); caja.className = 'panel'; caja.style.padding = '16px';
        caja.append(botonIA(ctx, { ticket, destino: ta }), ta);
        main.replaceChildren(caja);
    }""", ticket)
    pag.click('button:has-text("Sugerir respuesta")'); pag.wait_for_timeout(1500)
    pag.screenshot(path=str(SALIDA / "componente_bandeja_1440.png"), full_page=True)
    pag.click('button:has-text("Usar este borrador")'); pag.wait_for_timeout(500)
    valor = pag.evaluate("document.querySelector('#bdj-texto').value")
    res["componente_usar"] = {"ticket": ticket, "caja_rellena": len(valor) > 20, "inicio": valor[:60], "errores": [e for e in err if "favicon" not in e]}
    ctx.close()
    nav.close()

print(json.dumps(res, ensure_ascii=False, indent=1))
(SALIDA / "resultado.json").write_text(json.dumps(res, ensure_ascii=False, indent=1))

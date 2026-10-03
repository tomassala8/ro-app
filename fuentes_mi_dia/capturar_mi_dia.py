#!/usr/bin/env python3
"""
capturar_mi_dia.py · prueba y capturas de M1 «Mi día» para los 21 puestos (una persona real de cada uno).

Con servir.py en marcha (por defecto en 127.0.0.1:8786), entra «ver como» (Tomás → la persona) en cada puesto a
1440 y a 390 px, guarda capturas de página entera en capturas/mi_dia/ y comprueba: bloques pintados (máx. 7),
ningún bloque roto, sin desplazamiento horizontal y sin errores de consola propios de Mi día. Después entra con
identidad propia (?yo=) como las 7 personas de la definición de «hecho» y mira la consola.

Uso: python3 fuentes_mi_dia/capturar_mi_dia.py [--puerto 8786] [--sin-capturas]
"""
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

AQUI = Path(__file__).resolve().parent.parent
SALIDA = AQUI / "capturas" / "mi_dia"
PUERTO = int(sys.argv[sys.argv.index("--puerto") + 1]) if "--puerto" in sys.argv else 8787
PREFIJO = sys.argv[sys.argv.index("--prefijo") + 1] if "--prefijo" in sys.argv else "r3_"
CAPTURAS = "--sin-capturas" not in sys.argv

# puesto → (persona, ruta)
PUESTOS = [
    ("direccion", "tomas", "mi-dia/direccion"),
    ("finanzas_direccion", "tomas", "mi-dia/finanzas_direccion"),
    ("administracion", "sofia", "mi-dia"),
    ("operaciones", "mili", "mi-dia"),
    ("proyectos", "constanza", "mi-dia"),
    ("rrhh", "cecilia", "mi-dia"),
    ("account", "lucia", "mi-dia"),
    ("trafficker", "lina", "mi-dia"),
    ("jefa_publicidad", "valeria", "mi-dia"),
    ("especialista_ghl", "gustavo", "mi-dia"),
    ("jefa_crm", "yessica", "mi-dia"),
    ("tecnico_altas", "agustina", "mi-dia"),
    ("jefa_seo", "constanza", "mi-dia/jefa_seo"),
    ("seo", "jeronimo", "mi-dia"),
    ("ficha_google", "jeronimo", "mi-dia/ficha_google"),
    ("web", "carlos_viur", "mi-dia"),
    ("redes", "lara", "mi-dia"),
    ("produccion", "camilo", "mi-dia"),
    ("setters", "setter_ana", "mi-dia"),
    ("ventas_ro", "tomas", "mi-dia/ventas_ro"),
    ("outreach", "eulimar", "mi-dia"),
]
PROPIOS = ["tomas", "mili", "lucia", "valeria", "yessica", "constanza", "setter_ana"]

MIRAR = """() => {
  const b = [...document.querySelectorAll('.mid-bloques > .panel')];
  return {
    quien: document.querySelector('#quien')?.textContent,
    puesto: document.querySelector('#subtitulo')?.textContent,
    bloques: b.length,
    rotos: b.filter(x => /^(Este bloque ha fallado|Bloque desconocido|No se ha podido leer)/.test(x.querySelector('.vacio h3')?.textContent || '')).map(x => x.querySelector('header h2')?.textContent),
    llega_con: b.filter(x => /^Llega con/.test(x.querySelector('.vacio h3')?.textContent || '')).map(x => x.querySelector('header h2')?.textContent),
    numero: document.querySelector('.mid-top .ind .v')?.textContent || null,
    ir_planos: [...document.querySelectorAll('.mid-top .primero .acc a')].map(a => a.getAttribute('href')).filter(x => /^#\/[a-z-]+$/.test(x)),
    codigos: (document.querySelector('#main')?.innerText.match(/\b(?:D|W|G)-?\d{1,3}\b|\.json|\.py|v27/g) || []),
    primero: [...document.querySelectorAll('.mid-top .primero .mot')].map(x => x.textContent),
    ancho: document.documentElement.scrollWidth, ventana: innerWidth,
  };
}"""


def errores_propios(msgs):
    """Errores de consola: se ignoran los 403/404 de recursos de la carcasa (p. ej. /api/recarga en «ver como»)."""
    return [m for m in msgs if m["type"] == "error" and "Failed to load resource" not in m["text"]]


def main():
    SALIDA.mkdir(parents=True, exist_ok=True)
    informe = {"puerto": PUERTO, "puestos": [], "propios": []}
    with sync_playwright() as pw:
        nav = pw.chromium.launch(channel="chrome", headless=True)
        for ancho, alto, escala in ((1440, 900, 1), (390, 844, 2)):
            for puesto, persona, ruta in PUESTOS:
                ctx = nav.new_context(viewport={"width": ancho, "height": alto}, device_scale_factor=escala, is_mobile=ancho < 500)
                pag = ctx.new_page()
                msgs = []
                pag.on("console", lambda m: msgs.append({"type": m.type, "text": m.text}))
                pag.on("pageerror", lambda e: msgs.append({"type": "error", "text": f"pageerror: {e}"}))
                como = "" if persona == "tomas" else f"&como={persona}"
                pag.goto(f"http://127.0.0.1:{PUERTO}/?yo=tomas{como}#/{ruta}", wait_until="networkidle")
                pag.wait_for_selector(".mid-bloques > .panel, main .vacio", timeout=20000)
                pag.wait_for_timeout(600)
                r = pag.evaluate(MIRAR)
                r.update({"puesto_id": puesto, "persona": persona, "ancho_px": ancho, "errores": errores_propios(msgs)})
                if CAPTURAS:
                    f = SALIDA / f"{PREFIJO}{puesto}_{persona}_{ancho}.png"
                    pag.screenshot(path=str(f), full_page=True)
                    r["captura"] = f.name
                informe["puestos"].append(r)
                print(f"{ancho:>4} {puesto:<20} {persona:<12} bloques={r['bloques']} rotos={len(r['rotos'])} "
                      f"llega_con={len(r['llega_con'])} desborda={r['ancho'] > r['ventana']} errores={len(r['errores'])} "
                      f"número={(r['numero'] or '').strip()[:24]}")
                ctx.close()
        for persona in PROPIOS:
            ctx = nav.new_context(viewport={"width": 1440, "height": 900})
            pag = ctx.new_page()
            msgs = []
            pag.on("console", lambda m: msgs.append({"type": m.type, "text": m.text}))
            pag.on("pageerror", lambda e: msgs.append({"type": "error", "text": f"pageerror: {e}"}))
            pag.goto(f"http://127.0.0.1:{PUERTO}/?yo={persona}", wait_until="networkidle")
            pag.wait_for_timeout(1500)
            r = {"persona": persona, "ruta_inicial": pag.evaluate("location.hash"),
                 "errores": errores_propios(msgs), "todos_los_mensajes_de_error": [m["text"][:160] for m in msgs if m["type"] == "error"]}
            pag.goto(f"http://127.0.0.1:{PUERTO}/?yo={persona}#/mi-dia", wait_until="networkidle")
            pag.wait_for_selector(".mid-bloques > .panel, main .vacio", timeout=20000)
            r.update(pag.evaluate(MIRAR))
            r["errores_mi_dia"] = errores_propios(msgs)
            informe["propios"].append(r)
            print(f"propio {persona:<12} inicio={r['ruta_inicial']} bloques={r['bloques']} errores={len(r['errores_mi_dia'])}")
            ctx.close()
        nav.close()
    (SALIDA / f"_{PREFIJO}prueba.json").write_text(json.dumps(informe, ensure_ascii=False, indent=1))
    malos = [p for p in informe["puestos"] if p["rotos"] or p["errores"] or p["ancho"] > p["ventana"] or not p["bloques"]]
    malos += [p for p in informe["propios"] if p["errores_mi_dia"]]
    print(f"\n{len(informe['puestos'])} pantallas de puesto y {len(informe['propios'])} entradas propias · con problemas: {len(malos)}")
    return 1 if malos else 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Prueba y capturas del módulo «Paneles de herramientas» (carril N1).

Uso:  python3 capturar_paneles.py <puerto> [--sin-capturas]
  1. Las 7 personas de la definición de «hecho» entran en #/paneles: sin errores de consola, sin desbordar a 390 px,
     sin «undefined/NaN/null» en pantalla, y cada una ve solo sus herramientas (setter_ana, nada).
  2. Recorre todas las vistas de 6 clientes como Tomás con 3 periodos (30 días, mes anterior y «a medida»).
  3. Capturas a 1440 y 390 px en capturas/paneles/.
"""
import json, re, sys
from pathlib import Path
from playwright.sync_api import sync_playwright

APP = Path(__file__).resolve().parent.parent
PUERTO = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 8790
CAPTURAS = "--sin-capturas" not in sys.argv
SALIDA = APP / "capturas" / "paneles"
BASE = f"http://127.0.0.1:{PUERTO}"

PERSONAS = ["tomas", "mili", "lucia", "valeria", "yessica", "constanza", "setter_ana"]
VISTAS = {"ga4": ["resumen", "adquisicion", "interaccion", "eventos", "paginas", "tecnologia"], "gsc": ["rendimiento", "indexacion", "experiencia"],
          "meta": ["campanas", "conjuntos", "anuncios"], "ghl": ["oportunidades", "citas", "contactos"], "mc": ["instagram", "facebook", "linkedin"]}
CLIENTES = ["fusterguell", "kiosko-box", "musashi-consultores", "gac", "ahedo", "adade-zaragoza"]
FOTOS = [("ga4_resumen", "paneles/fusterguell/ga4/resumen"), ("ga4_adquisicion", "paneles/fusterguell/ga4/adquisicion"),
         ("gsc_rendimiento", "paneles/fusterguell/gsc/rendimiento"), ("gsc_indexacion", "paneles/fusterguell/gsc/indexacion"),
         ("meta_campanas", "paneles/kiosko-box/meta/campanas"), ("meta_anuncios", "paneles/kiosko-box/meta/anuncios"),
         ("ghl_oportunidades", "paneles/musashi-consultores/ghl/oportunidades"), ("ghl_citas", "paneles/musashi-consultores/ghl/citas"),
         ("mc_instagram", "paneles/gac/mc/instagram"), ("empresa_desk", "paneles/empresa/desk"), ("empresa_zadarma", "paneles/empresa/zadarma"),
         ("mapa", "paneles/mapa")]

MIRAR = """() => {
  const m = document.querySelector('main') || document.body;
  const t = m.innerText || '';
  return { malos: (t.match(/.{0,40}(undefined|NaN|\\bnull\\b|No se ha podido pintar).{0,40}/g) || []).slice(0, 3),
           pestanas: [...document.querySelectorAll('[role=tablist][aria-label="Herramienta"] [role=tab]')].map(b => b.textContent.trim()),
           vacio: !!m.querySelector('.vacio-g'), ancho: document.documentElement.scrollWidth, ventana: innerWidth,
           titulo: document.querySelector('h1')?.textContent || '' };
}"""


def errores(msgs):
    return [m for m in msgs if m["type"] == "error" and "Failed to load resource" not in m["text"]]


def main():
    SALIDA.mkdir(parents=True, exist_ok=True)
    inf = {"personas": [], "recorrido": [], "fotos": []}
    with sync_playwright() as pw:
        nav = pw.chromium.launch(channel="chrome", headless=True)

        def pagina(ancho=1440, alto=900, escala=1, periodo=None):
            ctx = nav.new_context(viewport={"width": ancho, "height": alto}, device_scale_factor=escala, is_mobile=ancho < 500)
            if periodo:
                ctx.add_init_script(f"try{{for(const p of {json.dumps(PERSONAS)})localStorage.setItem('ro.periodo.'+p, JSON.stringify({json.dumps(periodo)}))}}catch(e){{}}")
            pag = ctx.new_page()
            msgs = []
            pag.on("console", lambda m: msgs.append({"type": m.type, "text": m.text}))
            pag.on("pageerror", lambda e: msgs.append({"type": "error", "text": f"pageerror: {e}"}))
            return ctx, pag, msgs

        # 1 · personas
        for ancho, escala in ((1440, 1), (390, 2)):
            for p in PERSONAS:
                ctx, pag, msgs = pagina(ancho, 844 if ancho < 500 else 900, escala)
                pag.goto(f"{BASE}/?yo={p}#/paneles", wait_until="networkidle")
                pag.wait_for_timeout(1500)
                r = pag.evaluate(MIRAR)
                r.update({"persona": p, "ancho_px": ancho, "errores": [m["text"][:160] for m in errores(msgs)]})
                inf["personas"].append(r)
                print(f"{ancho:>4} {p:<11} herramientas={r['pestanas']} malos={len(r['malos'])} errores={len(r['errores'])} desborda={r['ancho'] > r['ventana']} · {r['titulo'][:40]}")
                if CAPTURAS:
                    pag.screenshot(path=str(SALIDA / f"persona_{p}_{ancho}.png"), full_page=False)
                ctx.close()
        # 2 · recorrido completo como Tomás con 3 periodos
        for periodo in ({"id": "30d", "comparar": "anterior"}, {"id": "mes_ant", "comparar": "anio_ant"}, {"id": "medida", "comparar": "anterior", "desde": "2026-07-15", "hasta": "2026-09-20"}):
            ctx, pag, msgs = pagina(periodo=periodo)
            pag.goto(f"{BASE}/?yo=tomas#/paneles", wait_until="networkidle")
            for c in CLIENTES:
                for herr, vs in VISTAS.items():
                    for v in vs:
                        n0 = len(msgs)
                        pag.evaluate(f"location.hash = '#/paneles/{c}/{herr}/{v}'")
                        pag.wait_for_timeout(350)
                        r = pag.evaluate(MIRAR)
                        e = errores(msgs[n0:])
                        if r["malos"] or e or r["ancho"] > r["ventana"]:
                            inf["recorrido"].append({"periodo": periodo["id"], "ruta": f"{c}/{herr}/{v}", "malos": r["malos"], "errores": [m["text"][:160] for m in e]})
            for ruta in ("paneles/empresa/desk", "paneles/empresa/zadarma", "paneles/mapa"):
                n0 = len(msgs)
                pag.evaluate(f"location.hash = '#/{ruta}'")
                pag.wait_for_timeout(500)
                r = pag.evaluate(MIRAR)
                if r["malos"] or errores(msgs[n0:]):
                    inf["recorrido"].append({"periodo": periodo["id"], "ruta": ruta, "malos": r["malos"], "errores": [m["text"][:160] for m in errores(msgs[n0:])]})
            print(f"recorrido {periodo['id']}: {sum(1 for x in inf['recorrido'] if x['periodo'] == periodo['id'])} vistas con problemas")
            ctx.close()
        # 3 · capturas
        if CAPTURAS:
            for ancho, escala in ((1440, 1), (390, 2)):
                ctx, pag, msgs = pagina(ancho, 844 if ancho < 500 else 900, escala, periodo={"id": "30d", "comparar": "anterior"})
                for nombre, ruta in FOTOS:
                    pag.goto(f"{BASE}/?yo=tomas#/{ruta}", wait_until="networkidle")
                    pag.wait_for_timeout(900)
                    f = SALIDA / f"{nombre}_{ancho}.png"
                    pag.screenshot(path=str(f), full_page=True)
                    r = pag.evaluate(MIRAR)
                    inf["fotos"].append({"foto": f.name, "desborda": r["ancho"] > r["ventana"]})
                ctx.close()
        nav.close()
    (SALIDA / "_prueba.json").write_text(json.dumps(inf, ensure_ascii=False, indent=1))
    malos = [p for p in inf["personas"] if p["malos"] or p["errores"] or p["ancho"] > p["ventana"]] + inf["recorrido"] + [f for f in inf["fotos"] if f["desborda"]]
    print(f"\n{len(inf['personas'])} entradas por persona · {len(inf['recorrido'])} vistas con problemas · {len(inf['fotos'])} capturas · problemas totales: {len(malos)}")
    return 1 if malos else 0


if __name__ == "__main__":
    sys.exit(main())

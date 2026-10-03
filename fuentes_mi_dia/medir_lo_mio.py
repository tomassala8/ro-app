#!/usr/bin/env python3
"""
medir_lo_mio.py · A1 + A3 (43_IDEAS_MEJORA): mide Mi día antes y después de «Lo mío».

Con servir.py en marcha sobre una COPIA de local.db (--bind 127.0.0.1, puertos 9070-9074), entra con identidad propia
(?yo=) como lucia, mili, gustavo, camilo, jeronimo, setter_ana y tomas a 1440×900 y 390×844 y mide:
  · px desde arriba del documento hasta la PRIMERA fila de trabajo (antes: la primera de «Lo primero hoy» / «Mis alertas»;
    después: la primera de «Lo mío»), y si cae dentro de la primera pantalla;
  · bloques visibles (paneles de primer nivel que se ven sin abrir nada) y alto de la página;
  · el texto entero del bloque «El número que manda» (para comprobar que las cifras no cambian);
  · errores de consola, desplazamiento horizontal y, después, duplicados en «Lo mío».
Guarda capturas .jpg en capturas/mi_dia/a1/<etiqueta>_<persona>_<ancho>.jpg y el resumen en capturas/mi_dia/a1/<etiqueta>.json.

Uso: python3 fuentes_mi_dia/medir_lo_mio.py --puerto 9070 --etiqueta antes|despues [--comparar]
"""
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

AQUI = Path(__file__).resolve().parent.parent
SALIDA = AQUI / "capturas" / "mi_dia" / "a1"
PUERTO = int(sys.argv[sys.argv.index("--puerto") + 1]) if "--puerto" in sys.argv else 9070
ETIQUETA = sys.argv[sys.argv.index("--etiqueta") + 1] if "--etiqueta" in sys.argv else "despues"
PERSONAS = ["lucia", "mili", "gustavo", "camilo", "jeronimo", "setter_ana", "tomas"]
ANCHOS = ((1440, 900, 1), (390, 844, 2))

MIRAR = """() => {
  const main = document.querySelector('#main');
  const arriba = el => el.getBoundingClientRect().top + scrollY;
  const visible = el => !!el.offsetParent && !el.closest('details:not([open]) > :not(summary)');
  // bloques = paneles de primer nivel (no dentro de otro panel) que se ven sin abrir nada
  const paneles = [...main.querySelectorAll('.panel, [data-ia="consejo"]')].filter(p => !p.parentElement.closest('.panel, [data-ia="consejo"]') && visible(p) && !p.hidden);
  const mas = document.querySelector('[data-mas-de-tu-dia]');
  const loMio = document.querySelector('[data-lo-mio]');
  const filasLoMio = loMio ? [...loMio.querySelectorAll('[data-fila-mia]')] : [];
  const trabajo = filasLoMio.length ? filasLoMio : [...main.querySelectorAll('.primero > li')].filter(visible);
  const primera = trabajo.length ? Math.round(Math.min(...trabajo.map(arriba))) : null;
  const num = document.querySelector('#mid-num-t')?.closest('.panel');
  const claves = filasLoMio.map(f => f.dataset.filaMia);
  // objeto repetido = dos filas al mismo objeto salvo que las dos sean alertas (dos reglas distintas sobre la misma ficha cuentan las dos)
  const porObj = new Map(); let objRep = 0;
  for (const f of filasLoMio) { const o = f.dataset.objeto; if (!o) continue; const prev = porObj.get(o); if (prev && !(prev === 'alerta' && f.dataset.tipo === 'alerta')) objRep++; if (!prev || prev !== 'alerta') porObj.set(o, f.dataset.tipo); }
  return {
    ruta: location.hash,
    primera_fila: primera,
    en_primera_pantalla: primera !== null && primera < innerHeight,
    bloques: paneles.length,
    titulos: paneles.map(p => p.querySelector('header h2, .ia-cab b')?.textContent?.trim() || '(sin título)'),
    plegados: mas ? mas.querySelectorAll('.panel').length : 0,
    alto: document.documentElement.scrollHeight,
    numero: num ? num.innerText.replace(/\\s+/g, ' ').trim() : null,
    consejo: (() => { const c = document.querySelector('#main > [data-ia="consejo"]'); if (!c) return null;
      const vis = [...c.querySelectorAll('li.ia-accion')].filter(li => !li.hidden);
      const objs = new Set(filasLoMio.map(f => f.dataset.objeto));
      const deIr = a => decodeURIComponent((a || '').replace(/^#\//, '').split('?')[0]).replace(/\/+$/, '');
      return { visible: !c.hidden, filas: vis.length, repetidas: vis.filter(li => objs.has(deIr(li.querySelector('a[data-ir]')?.getAttribute('href')))).length,
               debajo: !!(loMio && (loMio.compareDocumentPosition(c) & Node.DOCUMENT_POSITION_FOLLOWING)) }; })(),
    lo_mio: loMio ? { filas: filasLoMio.length, total: Number(loMio.dataset.total || 0), alertas: Number(loMio.dataset.alertas || 0), revisiones: Number(loMio.dataset.revisiones || 0),
      duplicadas: claves.length - new Set(claves).size, objetos_duplicados: objRep,
      primeras: filasLoMio.slice(0, 5).map(f => f.querySelector('.mot')?.textContent?.trim()) } : null,
    desborde: document.documentElement.scrollWidth > innerWidth + 1,
  };
}"""


CRUCE_ALERTAS = """() => { const t = document.querySelector('[data-contadores]'); return t ? JSON.parse(t.dataset.contadores).mias : null; }"""
CRUCE_PROD = """() => { const b = [...document.querySelectorAll('button, [role=tab]')].find(x => /^\\s*Por revisar/.test(x.textContent));
  if (!b) return 0; const m = b.textContent.replace('Por revisar', '').match(/\\d[\\d.]*/); return m ? Number(m[0].replace('.', '')) : 0; }"""


def cruces(pag):
    """Lo mío frente a sus pantallas: «Mías» de Alertas y «Por revisar» (me toca) de Producción, en el mismo navegador."""
    out = {}
    for ruta, js, clave in (("alertas", CRUCE_ALERTAS, "alertas_mias"), ("produccion", CRUCE_PROD, "produccion_me_toca")):
        pag.goto(pag.url.split("#")[0] + f"#/{ruta}")
        pag.wait_for_timeout(3500)
        try:
            out[clave] = pag.evaluate(js)
        except Exception as e:  # noqa: BLE001
            out[clave] = f"error: {e}"
    return out


def main():
    SALIDA.mkdir(parents=True, exist_ok=True)
    res = {"puerto": PUERTO, "etiqueta": ETIQUETA, "medidas": []}
    with sync_playwright() as pw:
        nav = pw.chromium.launch(channel="chrome", headless=True)
        for ancho, alto, escala in ANCHOS:
            for yo in PERSONAS:
                ctx = nav.new_context(viewport={"width": ancho, "height": alto}, device_scale_factor=escala, is_mobile=ancho < 500)
                pag = ctx.new_page()
                errores = []
                pag.on("console", lambda m: errores.append(m.text) if m.type == "error" and "Failed to load resource" not in m.text else None)
                pag.on("pageerror", lambda e: errores.append(str(e)))
                pag.goto(f"http://127.0.0.1:{PUERTO}/?yo={yo}#/mi-dia", wait_until="domcontentloaded")
                try:
                    pag.wait_for_selector("#mid-num-t, [data-lo-mio], #main .vacio", timeout=25000)
                except Exception:
                    pass
                pag.wait_for_timeout(2500)
                m = pag.evaluate(MIRAR)
                m.update({"persona": yo, "ancho": ancho, "errores": errores[:5]})
                res["medidas"].append(m)
                pag.screenshot(path=str(SALIDA / f"{ETIQUETA}_{yo}_{ancho}.jpg"), type="jpeg", quality=70, full_page=False)
                if ancho == 1440 and m.get("lo_mio") is not None and "--cruces" in sys.argv:
                    m["cruces"] = cruces(pag)
                print(f"{yo:11} {ancho:4} · 1.ª fila {m['primera_fila']} px ({'1.ª pantalla' if m['en_primera_pantalla'] else 'abajo'}) · "
                      f"{m['bloques']} bloques (+{m['plegados']} plegados) · alto {m['alto']} · {m['ruta']}" + (f" · Lo mío {m['lo_mio']}" if m['lo_mio'] else "")
                      + (f" · cruces {m.get('cruces')}" if m.get('cruces') else "") + (f" · consejo {m.get('consejo')}" if m.get('consejo') else "")
                      + (f" · ERRORES {errores[:2]}" if errores else "") + (" · DESBORDE" if m["desborde"] else ""))
                ctx.close()
        nav.close()
    (SALIDA / f"{ETIQUETA}.json").write_text(json.dumps(res, ensure_ascii=False, indent=1))
    if "--comparar" in sys.argv:
        comparar()


def _sin_reloj(s):
    """El sello de frescura («hace 2,4 h») avanza solo entre una medida y otra: no es una cifra del número."""
    import re
    return re.sub(r"hace [\d.,]+ (?:h|min|d[ií]as?)", "hace … ", s or "")


def comparar():
    """Tabla antes/después y comprobación de que el texto del número que manda es idéntico (salvo el reloj del sello)."""
    a = {(m["persona"], m["ancho"]): m for m in json.loads((SALIDA / "antes.json").read_text())["medidas"]}
    d = {(m["persona"], m["ancho"]): m for m in json.loads((SALIDA / "despues.json").read_text())["medidas"]}
    fallos = 0
    print("\npersona     ancho | 1.ª fila antes → después | bloques antes → después | número que manda")
    for k in sorted(d):
        x, y = a.get(k, {}), d[k]
        igual = _sin_reloj(x.get("numero")) == _sin_reloj(y.get("numero"))
        fallos += 0 if igual else 1
        print(f"{k[0]:11} {k[1]:5} | {str(x.get('primera_fila')):>6} → {str(y.get('primera_fila')):>6} | "
              f"{str(x.get('bloques')):>3} → {str(y.get('bloques')):>3} | {'idéntico' if igual else 'CAMBIA'}")
        if not igual:
            print("   antes:  ", x.get("numero"))
            print("   después:", y.get("numero"))
    print(f"\nNúmero que manda: {'idéntico en todos (texto entero; solo avanza el «hace … h» del sello)' if not fallos else f'{fallos} distintos'}")
    sys.exit(1 if fallos else 0)


if __name__ == "__main__":
    if "--solo-comparar" in sys.argv:
        comparar()
    else:
        main()

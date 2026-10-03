#!/usr/bin/env python3
"""Prueba en Chrome sin cabeza (Playwright) de M20 Personas, M21 Decisiones y M22 Conexiones.
Recorre las 7 personas de la definición de «hecho», recoge errores de consola y hace capturas a 1440 y 390 px.
Uso: python3 fuentes_personas/probar_m20_m22.py [puerto]   (servir.py tiene que estar en marcha en ese puerto)"""
import json, sys
from pathlib import Path
from playwright.sync_api import sync_playwright

APP = Path(__file__).resolve().parent.parent
PUERTO = sys.argv[1] if len(sys.argv) > 1 else "8795"
BASE = f"http://127.0.0.1:{PUERTO}/"
QUIENES = ["tomas", "mili", "cecilia", "lucia", "valeria", "yessica", "constanza", "setter_ana"]
RUTAS = [("personas", "personas", None), ("decisiones", "decisiones", None), ("ajustes", "ajustes/conexiones", None)]
CAPTURAS = {  # (persona, ruta, pestaña a pulsar o None, nombre) · ronda 3: prefijo r3_. Sueldos: solo la pantalla sin abrir (nunca importes en una captura)
    ("tomas", "personas", "En alerta", "r3_personas_tomas_alerta"), ("cecilia", "personas", "Carga", "r3_personas_cecilia_carga"),
    ("cecilia", "personas", "Lista de salida", "r3_personas_cecilia_salida"), ("cecilia", "personas", "Sueldos", "r3_personas_cecilia_sueldos_cerrado"),
    ("lucia", "personas", None, "r3_personas_lucia_mi_ficha"), ("valeria", "personas", "Quién no imputa", "r3_personas_valeria_equipo"),
    ("tomas", "decisiones", "Con reloj", "r3_decisiones_tomas_reloj"), ("tomas", "decisiones", "Informe semanal", "r3_decisiones_tomas_informe"),
    ("mili", "decisiones", "Cierre de mes", "r3_decisiones_mili_cierre"), ("lucia", "decisiones", "Las 101 firmadas", "r3_decisiones_lucia_firmadas"),
    ("tomas", "ajustes/conexiones", None, "r3_ajustes_tomas_conexiones"),
}


def main():
    res = {}
    with sync_playwright() as p:
        nav = p.chromium.launch(channel="chrome", headless=True)
        for ancho in (1440, 390):
            ctxb = nav.new_context(viewport={"width": ancho, "height": 900}, device_scale_factor=1)
            for quien in QUIENES:
                for mod, ruta, _ in RUTAS:
                    pg = ctxb.new_page()
                    errores = []
                    pg.on("console", lambda m, e=errores: e.append(m.text) if m.type == "error" else None)
                    pg.on("pageerror", lambda ex, e=errores: e.append(str(ex)))
                    pg.goto(f"{BASE}?yo={quien}#/{ruta}")
                    pg.wait_for_timeout(1800)
                    texto = pg.inner_text("main") if pg.query_selector("main") else pg.inner_text("body")
                    desborde = pg.evaluate("document.documentElement.scrollWidth > window.innerWidth + 1")
                    tabs = pg.query_selector_all(".pestanas [role=tab]")
                    nombres = [t.inner_text().strip() for t in tabs]
                    for t in tabs:  # recorre todas las pestañas buscando errores (sin abrir sueldos)
                        t.click(); pg.wait_for_timeout(250)
                    textos = pg.inner_text('body')
                    crudos = [x for x in ('jefa/e:', 'D-2', 'D-7', 'data/', '.json', 'W1', 'W7', 'ley C-', 'auditoría C-') if x in textos]
                    clave = f"{ancho}:{quien}:{ruta}"
                    res[clave] = {"crudos": crudos, "errores": [e for e in errores if "favicon" not in e], "desborde": desborde, "pestanas": nombres, "inicio": texto[:140].replace("\n", " | ")}
                    for (q, r, pest, nombre) in CAPTURAS:
                        if q == quien and r == ruta:
                            pg.goto(f"{BASE}?yo={quien}#/{ruta}"); pg.wait_for_timeout(1500)
                            if pest:
                                el = pg.query_selector(f".pestanas [role=tab]:has-text('{pest}')")
                                if el: el.click(); pg.wait_for_timeout(400)
                            carpeta = APP / "capturas" / mod
                            carpeta.mkdir(parents=True, exist_ok=True)
                            pg.screenshot(path=str(carpeta / f"{nombre}_{ancho}.png"), full_page=True)
                    pg.close()
            ctxb.close()
        nav.close()
    malos = {k: v for k, v in res.items() if v["errores"] or v["desborde"]}
    for k, v in res.items():
        print(("✗ " if k in malos else "✓ ") + k, "·", " / ".join(v["pestanas"]) or v["inicio"][:80], ("· ERRORES: " + " || ".join(v["errores"][:3])) if v["errores"] else "", "· DESBORDE" if v["desborde"] else "")
    print(f"\n{len(res) - len(malos)} de {len(res)} sin errores ni desborde")


if __name__ == "__main__":
    main()

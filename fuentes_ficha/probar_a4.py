#!/usr/bin/env python3
"""fuentes_ficha/probar_a4.py · A4 (2-oct): objetivo y semáforo del lunes desde la cabecera de la ficha, de punta a punta.

Contra un servidor de PRUEBA (127.0.0.1, puerto 9050-9054) que sirve una COPIA de la app con una COPIA de local.db:
  RO_A4_BASE=http://127.0.0.1:9050  RO_A4_COPIA=<carpeta de la copia de la app>  RO_A4_DB=<copia de local.db>
Nunca contra la base real: escribe acciones (simuladas) y regenera captacion.json y objetivos.json DENTRO de la copia.

1. Lucía, Candela, Mili y Jerónimo a 1440 y 390: sin errores de consola, sin desplazamiento horizontal, quién edita y quién no.
2. Lucía pone el semáforo (2 clics) y carga el objetivo de GAC (2 clics); se ven con quién y cuándo.
3. Se regeneran captacion.json y objetivos.json en la copia: Captación y el número que manda de Lucía (Mi día) lo reflejan.
Capturas: capturas/ficha/a4_*.jpg (en la app real; solo imágenes).
"""
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

APP = Path(__file__).resolve().parents[1]
BASE = os.environ.get("RO_A4_BASE", "http://127.0.0.1:9050")
COPIA = Path(os.environ["RO_A4_COPIA"])
DB = os.environ["RO_A4_DB"]
assert BASE.startswith("http://127.0.0.1:90") and COPIA.resolve() != APP.resolve(), "solo contra la copia y en 127.0.0.1:9050-9054"
SALIDA = APP / "capturas" / "ficha"
SALIDA.mkdir(parents=True, exist_ok=True)
fallos = []


def ok(c, t):
    print(("✓ " if c else "✗ ") + t)
    if not c:
        fallos.append(t)


def api(ruta, yo):
    with urllib.request.urlopen(urllib.request.Request(f"{BASE}/api/{ruta}", headers={"X-RO-Yo": yo})) as r:
        return json.loads(r.read())


def abrir(nav, yo, cli, ancho, errs):
    ctx = nav.new_context(viewport={"width": ancho, "height": 1000})
    pg = ctx.new_page()
    pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(f"{BASE}/?yo={yo}#/ficha/{cli}/resumen")
    pg.wait_for_selector("section.detalle-cab", timeout=20000)
    pg.wait_for_timeout(1200)
    return ctx, pg


def desborde(pg):
    return pg.evaluate("document.documentElement.scrollWidth > window.innerWidth + 1")


def boton(pg, texto):
    return pg.locator("section.detalle-cab button.bt", has_text=texto).first


def cabecera_jpg(pg, nombre):
    pg.locator("section.detalle-cab").screenshot(path=str(SALIDA / nombre), type="jpeg", quality=78)


def regenerar():
    env = {**os.environ, "RO_DB": DB}
    # El orden de la tubería: captación → … → Mi día (su paquete por persona lleva captacion.json dentro)
    for cmd in (["python3", "fuentes_captacion/generar_captacion.py"], ["python3", "fuentes_objetivos/objetivos.py"], ["python3", "fuentes_mi_dia/generar_mi_dia.py"]):
        r = subprocess.run(cmd, cwd=COPIA, env=env, capture_output=True, text=True, timeout=600)
        ok(r.returncode == 0, f"regenerado en la copia: {' '.join(cmd[1:])} {r.stderr[-300:] if r.returncode else ''}")


def numero_que_manda(nav, yo="lucia"):
    ctx = nav.new_context(viewport={"width": 1440, "height": 1000})
    pg = ctx.new_page()
    pg.goto(f"{BASE}/?yo={yo}#/mi-dia")
    pg.wait_for_timeout(4000)
    t = pg.locator("body").inner_text()
    return ctx, pg, t


def main():
    with sync_playwright() as p:
        nav = p.chromium.launch()
        # ---- 0 · antes: el número que manda de Lucía
        ctx, pg, antes = numero_que_manda(nav)
        pg.screenshot(path=str(SALIDA / "a4_lucia_mi_dia_antes_1440.jpg"), type="jpeg", quality=72)
        ctx.close()
        cap0 = api("modulo/captacion/captacion", "lucia")
        g0 = next(c for c in cap0["clientes"] if c["cliente_id"] == "gac")
        ok(not (g0.get("objetivo") or {}).get("cargado"), "antes: GAC sin objetivo en Captación")

        # ---- 1 · quién edita y quién no, a 1440 y 390
        casos = (("lucia", "gac", True), ("candela", "emex", True), ("candela_ajeno", "gac", False), ("mili", "gac", True), ("jeronimo", "gac", False))
        for yo_c, cli, edita in casos:
            yo = yo_c.split("_")[0]
            if yo_c == "candela_ajeno":
                continue   # Candela no abre la ficha de GAC (no es de su cartera): lo prueba pruebas_seguridad.py en el servidor
            for ancho in (1440, 390):
                errs = []
                ctx, pg = abrir(nav, yo, cli, ancho, errs)
                bs, bo = boton(pg, "Semáforo del lunes"), boton(pg, "Objetivo")
                ok(bs.count() == 1 and bo.count() == 1, f"{yo} {cli} {ancho}: «Semáforo del lunes» y «Objetivo» en la cabecera")
                bs.click()
                pg.wait_for_timeout(300)
                n_col = pg.locator("section.detalle-cab button.bt", has_text="Rojo").count()
                ok((n_col == 1) == edita, f"{yo} {cli} {ancho}: {'puede' if edita else 'NO puede'} poner el semáforo ({n_col} botón de color)")
                ok(pg.locator("section.detalle-cab", has_text="Historial por semana").count() == 1, f"{yo} {ancho}: ve el historial semanal")
                ok(not desborde(pg), f"{yo} {cli} {ancho}: sin desplazamiento horizontal")
                pg.screenshot(path=str(SALIDA / f"a4_{yo}_{cli}_semaforo_{ancho}.jpg"), type="jpeg", quality=72)
                bo.click()
                pg.wait_for_timeout(300)
                n_g = pg.locator("section.detalle-cab button", has_text="Guardar objetivo").count()
                ok((n_g == 1) == edita, f"{yo} {cli} {ancho}: {'puede' if edita else 'NO puede'} cargar el objetivo")
                ok(not desborde(pg), f"{yo} {cli} {ancho}: sin desplazamiento horizontal con el objetivo abierto")
                pg.screenshot(path=str(SALIDA / f"a4_{yo}_{cli}_objetivo_{ancho}.jpg"), type="jpeg", quality=72)
                errs = [e for e in errs if "favicon" not in e]
                ok(not errs, f"{yo} {cli} {ancho}: sin errores de consola {errs[:2]}")
                ctx.close()

        # ---- 2 · Lucía: semáforo en 2 clics y objetivo en 2 clics
        errs = []
        ctx, pg = abrir(nav, "lucia", "gac", 1440, errs)
        boton(pg, "Semáforo del lunes").click()                                    # clic 1
        pg.locator("section.detalle-cab input[maxlength='140']").fill("Llamada con Patricia: piden más citas de herencias; el lunes, nueva campaña")
        pg.locator("section.detalle-cab button.bt", has_text="Ámbar").click()      # clic 2 (el color guarda)
        pg.wait_for_timeout(1500)
        cab = pg.locator("section.detalle-cab").inner_text()
        ok("Ámbar" in cab and "Lucía" in cab, "Lucía pone el semáforo en ámbar en 2 clics; la cabecera dice Ámbar y Lucía")
        cabecera_jpg(pg, "a4_lucia_gac_semaforo_puesto_1440.jpg")
        boton(pg, "Objetivo").click()                                               # clic 1
        pg.wait_for_timeout(300)
        campos = pg.locator("section.detalle-cab input[type='number']")
        for i, v in enumerate(("120", "3", "60", "4")):                             # leads/mes, €/lead, €/cita, ventas/mes
            campos.nth(i).fill(v)
        pg.locator("section.detalle-cab button", has_text="Guardar objetivo").click()  # clic 2
        pg.wait_for_timeout(1500)
        cab = pg.locator("section.detalle-cab").inner_text()
        ok("120 leads/mes" in cab and "3 € por lead" in cab, f"Lucía carga el objetivo en 2 clics; la cabecera lo enseña ({'120 leads/mes' in cab}, {'3 € por lead' in cab})")
        cabecera_jpg(pg, "a4_lucia_gac_objetivo_cargado_1440.jpg")
        pg.screenshot(path=str(SALIDA / "a4_lucia_gac_1440.jpg"), type="jpeg", quality=72)
        errs = [e for e in errs if "favicon" not in e]
        ok(not errs, f"Lucía guardando: sin errores de consola {errs[:2]}")
        ctx.close()
        # 390 tras guardar
        errs = []
        ctx, pg = abrir(nav, "lucia", "gac", 390, errs)
        boton(pg, "Semáforo del lunes").click()
        pg.wait_for_timeout(300)
        ok(not desborde(pg), "Lucía 390 tras guardar: sin desplazamiento horizontal")
        pg.screenshot(path=str(SALIDA / "a4_lucia_gac_390.jpg"), type="jpeg", quality=72, full_page=True)
        ctx.close()
        # Jerónimo ve el objetivo sin costes y el semáforo con quién lo puso
        errs = []
        ctx, pg = abrir(nav, "jeronimo", "gac", 1440, errs)
        cab = pg.locator("section.detalle-cab").inner_text()
        ok("Ámbar" in cab and "120 leads/mes" in cab and "por lead" not in cab, "Jerónimo ve el semáforo y el objetivo de GAC, sin costes y sin editar")
        pg.screenshot(path=str(SALIDA / "a4_jeronimo_gac_1440.jpg"), type="jpeg", quality=72)
        ctx.close()
        for ancho in (390,):
            errs = []
            ctx, pg = abrir(nav, "jeronimo", "gac", ancho, errs)
            pg.screenshot(path=str(SALIDA / f"a4_jeronimo_gac_{ancho}.jpg"), type="jpeg", quality=72, full_page=True)
            ctx.close()
        for yo, cli in (("candela", "emex"), ("mili", "gac")):
            for ancho in (1440, 390):
                errs = []
                ctx, pg = abrir(nav, yo, cli, ancho, errs)
                pg.screenshot(path=str(SALIDA / f"a4_{yo}_{cli}_{ancho}.jpg"), type="jpeg", quality=72, full_page=(ancho == 390))
                ctx.close()

        # ---- 3 · una sola fuente: tras la vuelta de datos (en la copia), Captación y el número que manda lo reflejan
        regenerar()
        cap1 = api("modulo/captacion/captacion", "lucia")
        g1 = next(c for c in cap1["clientes"] if c["cliente_id"] == "gac")
        o1 = g1.get("objetivo") or {}
        ok(o1.get("cargado") and o1.get("cpl_objetivo") == 3 and o1.get("coste_cita_objetivo") == 60 and o1.get("leads_mes") == 120 and o1.get("quien") == "lucia",
           f"Captación lee el objetivo de GAC de la base: {o1}")
        ok((cap1.get("resumen") or {}).get("objetivos_cargados", 0) >= 1, f"Captación: objetivos cargados {cap0['resumen'].get('objetivos_cargados')} → {cap1['resumen'].get('objetivos_cargados')}")
        ob = api("modulo/objetivos/objetivos", "lucia")
        og = next((c for c in ob["clientes"] if c["cliente_id"] == "gac"), {})
        ok((og.get("objetivo") or {}).get("coste_lead") == 3 and (og.get("semaforo") or {}).get("color") == "ambar", "objetivos.json (ficha y Clientes nuevos) = lo mismo")
        ctx, pg, despues = numero_que_manda(nav)
        pg.screenshot(path=str(SALIDA / "a4_lucia_mi_dia_despues_1440.jpg"), type="jpeg", quality=72)
        ctx.close()
        ok("GAC (coste por lead por encima del techo)" in despues and "1 objetivos del alta cargados" in despues,
           "Mi día de Lucía: el número que manda juzga GAC con su objetivo (fuera por coste por lead) y cuenta 1 objetivo cargado")
        ok(antes != despues, "el número que manda de Lucía cambia tras cargar el objetivo")
        ctx2 = nav.new_context(viewport={"width": 1440, "height": 1000})
        pg = ctx2.new_page()
        pg.goto(f"{BASE}/?yo=lucia#/captacion")
        pg.wait_for_timeout(4000)
        pg.screenshot(path=str(SALIDA / "a4_lucia_captacion_1440.jpg"), type="jpeg", quality=72)
        ctx2.close()
        nav.close()
    print(f"\n{'TODO BIEN' if not fallos else f'{len(fallos)} FALLO(S)'}")
    sys.exit(1 if fallos else 0)


if __name__ == "__main__":
    main()

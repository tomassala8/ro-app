#!/usr/bin/env python3
"""
pruebas_diseno.py · vigila la guía de estilo de la auditoría 30 (E0 ronda 9). HOY SOLO INFORMA: no falla.

Regla de oro de la guía: ningún módulo escribe un número de píxeles de letra, un color o una sombra; solo tokens
(estilos.css) y componentes (componentes.js). Esta prueba lo mide en cada modulos/*.js y en los ficheros comunes:

  1. Módulos con su propia hoja de estilos (<style> inyectado o hoja generada).
  2. Tamaños de letra fuera de la escala 12 · 13 · 15 · 20 · 24 · 32 (font-size y font: en px; desde la ronda 14, sin 11).
  3. Colores sueltos (#hex, rgb(), hsl()) fuera de los tokens de :root.
  4. Sombras y radios escritos con números (box-shadow / border-radius sin var(--…)).
  5. Espaciados que no son de la escala de 4 (padding, margin, gap: 2, 3, 5, 7, 9, 10, 11, 13…).

  python3 pruebas_diseno.py              # informe por módulo (sale siempre con 0)
  python3 pruebas_diseno.py --json       # el mismo informe en JSON (para el coordinador)
  python3 pruebas_diseno.py --estricto   # falla si queda algo (ronda 10: lo corre pruebas_e0.py)
  python3 pruebas_diseno.py --estricto --en-obra finanzas.js,dinero_comun.js   # esos ficheros solo avisan (dueño trabajando)
"""
import json
import re
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
ESCALA = {12, 13, 15, 20, 24, 32}   # ronda 14 (barrido 39): el 11 sale de la escala; nada de letra < 12 px
ESPACIOS_OK = {0, 1, 4, 6, 8, 12, 16, 20, 24, 28, 32, 40, 48, 56, 64}   # 1 = filete; 6 y 28 se toleran (no están prohibidos)
COMUNES = ["estilos.css", "componentes.js", "app.js", "carcasa.js", "ayudas.js", "index.html"]   # R15: ayudas.js (buscador, atajos, «Algo va mal»)

RE_HOJA = re.compile(r"""(createElement\(\s*['"]style['"]\s*\)|h\(\s*['"]style['"]|<style\b|id:\s*['"][\w-]*estilo[s]?['"]|['"]<style)""")
RE_FS = re.compile(r"font-size\s*:\s*['\"]?\s*([0-9.]+)px|fontSize\s*:\s*['\"]([0-9.]+)px|\bfont\s*:\s*['\"]?\s*(?:italic\s+)?\d{3}\s+([0-9.]+)px")
RE_COLOR = re.compile(r"(#[0-9a-fA-F]{3,8}\b|rgba?\([^)]*\)|hsla?\([^)]*\))")
RE_SOMBRA = re.compile(r"(box-shadow|boxShadow)\s*:\s*['\"]?\s*(?!var\(|none|inherit|0 0 0 \d+px var)([^;'\"}]*\d+px[^;'\"}]*)")
RE_RADIO = re.compile(r"(border-radius|borderRadius)\s*:\s*['\"]?\s*(?!var\(|50%|inherit)([0-9.]+px[^;'\"}]*)")
RE_ESP = re.compile(r"(?:padding|margin|gap|row-gap|column-gap)(?:-[a-z]+)?\s*:\s*([^;}\"'\n]+)")
RE_ROOT = re.compile(r":root\s*\{[^}]*\}", re.S)


def sin_comentarios(t, css=False):
    # Ronda 10: primero las líneas «// …» y LUEGO los bloques /* */. Al revés, un «/api/ia/*» dentro de un comentario de
    # línea abría un bloque falso que se comía media hoja (ia_componentes.js salía «limpio» con su <style> dentro).
    if not css:
        t = re.sub(r"(?m)^\s*//.*$", "", t)
    t = re.sub(r"/\*.*?\*/", "", t, flags=re.S)
    if not css:
        t = re.sub(r"(?<![:'\"\\])//[^\n'\"`]*$", "", t, flags=re.M)
    return t


def medir(ruta: Path):
    crudo = ruta.read_text(errors="ignore")
    css = ruta.suffix == ".css"
    t = sin_comentarios(crudo, css)
    if css:
        t = RE_ROOT.sub("", t)                       # los tokens de :root son la fuente: no cuentan como sueltos
    tam = []
    for m in RE_FS.finditer(t):
        v = next(x for x in m.groups() if x)
        if float(v) not in ESCALA:
            tam.append(v)
    colores = [c for c in RE_COLOR.findall(t) if c.lower() not in ("#fff", "#ffffff", "#000")]
    if ruta.name == "componentes.js":                # el SVG de la marca de RO lleva sus dos colores fijos
        colores = [c for c in colores if c.lower() not in ("#16205e",)]
    esp = []
    for m in RE_ESP.finditer(t):
        for n in re.findall(r"(-?[0-9.]+)px", m.group(1)):
            try:
                if abs(float(n)) not in ESPACIOS_OK:
                    esp.append(n)
            except ValueError:
                pass
    return {
        "hoja_propia": bool(RE_HOJA.search(t)) and not css and ruta.name not in ("componentes.js",),
        "letra_fuera_de_escala": sorted(set(tam), key=float), "n_letra": len(tam),
        "colores_sueltos": sorted(set(colores))[:12], "n_colores": len(colores),
        "sombras": len(RE_SOMBRA.findall(t)), "radios": len(RE_RADIO.findall(t)),
        "espaciado_fuera_de_escala": len(esp),
    }


def main():
    informe = {"comunes": {}, "modulos": {}}
    for n in COMUNES:
        f = AQUI / n
        if f.exists():
            informe["comunes"][n] = medir(f)
    for f in sorted((AQUI / "modulos").glob("*.js")):
        informe["modulos"][f.name] = medir(f)

    con_hoja = [k for k, v in informe["modulos"].items() if v["hoja_propia"]]
    resumen = {
        "modulos": len(informe["modulos"]),
        "con_hoja_propia": len(con_hoja),
        "letra_fuera_de_escala": sum(v["n_letra"] for v in informe["modulos"].values()),
        "colores_sueltos": sum(v["n_colores"] for v in informe["modulos"].values()),
        "sombras_y_radios_con_numero": sum(v["sombras"] + v["radios"] for v in informe["modulos"].values()),
        "espaciado_fuera_de_escala": sum(v["espaciado_fuera_de_escala"] for v in informe["modulos"].values()),
        "comunes_limpios": all(v["n_letra"] == 0 and v["n_colores"] == 0 for k, v in informe["comunes"].items() if k == "estilos.css"),
    }
    informe["resumen"] = resumen
    if "--json" in sys.argv:
        print(json.dumps(informe, ensure_ascii=False, indent=1))
    else:
        print("Guía de estilo (auditoría 30) · informe de pruebas_diseno.py — solo informa, no falla\n")
        print("FICHEROS COMUNES (E0)")
        for k, v in informe["comunes"].items():
            print(f"  {k:<16} letra fuera de escala {v['n_letra']:>3} · colores sueltos {v['n_colores']:>3} · sombras/radios con número {v['sombras'] + v['radios']:>3} · espaciado fuera {v['espaciado_fuera_de_escala']:>3}"
                  + (f"  {v['letra_fuera_de_escala']}" if v["letra_fuera_de_escala"] else ""))
        print("\nMÓDULOS (cada dueño aplica la guía en el suyo)")
        orden = sorted(informe["modulos"].items(), key=lambda kv: -(kv[1]["n_letra"] + kv[1]["n_colores"] + kv[1]["sombras"] + kv[1]["radios"] + (20 if kv[1]["hoja_propia"] else 0)))
        for k, v in orden:
            total = v["n_letra"] + v["n_colores"] + v["sombras"] + v["radios"]
            if not total and not v["hoja_propia"] and not v["espaciado_fuera_de_escala"]:
                continue
            print(f"  {k:<26} {'HOJA PROPIA · ' if v['hoja_propia'] else ''}letra {v['n_letra']:>3} {v['letra_fuera_de_escala'][:8] or ''} · "
                  f"colores {v['n_colores']:>3} · sombras {v['sombras']} · radios {v['radios']} · espaciado {v['espaciado_fuera_de_escala']}")
        limpios = [k for k, v in informe["modulos"].items() if not (v["n_letra"] + v["n_colores"] + v["sombras"] + v["radios"] + v["espaciado_fuera_de_escala"]) and not v["hoja_propia"]]
        print(f"\n  Limpios: {len(limpios)} de {resumen['modulos']} ({', '.join(limpios) or 'ninguno'})")
        print(f"\nRESUMEN · {resumen['con_hoja_propia']} módulos con hoja propia · {resumen['letra_fuera_de_escala']} tamaños de letra fuera de escala · "
              f"{resumen['colores_sueltos']} colores sueltos · {resumen['sombras_y_radios_con_numero']} sombras/radios con número · "
              f"{resumen['espaciado_fuera_de_escala']} espaciados fuera de la escala de 4")
    if "--estricto" in sys.argv:
        en_obra = set(sys.argv[sys.argv.index("--en-obra") + 1].split(",")) if "--en-obra" in sys.argv else set()
        culpables = [k for k, v in informe["modulos"].items() if k not in en_obra
                     and (v["hoja_propia"] or v["n_letra"] or v["n_colores"] or v["sombras"] or v["radios"])]
        if en_obra and "--json" not in sys.argv:
            print(f"\nEn obra (solo avisan): {', '.join(sorted(en_obra))}")
        if culpables and "--json" not in sys.argv:
            print(f"ESTRICTO · fallan: {', '.join(culpables)}")
        sys.exit(1 if culpables else 0)
    sys.exit(0)


if __name__ == "__main__":
    main()

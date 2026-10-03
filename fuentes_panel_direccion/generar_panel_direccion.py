#!/usr/bin/env python3
"""
fuentes_panel_direccion/generar_panel_direccion.py · datos del módulo «Panel de dirección» (solo Tomás).

Petición de Tomás (2-oct): «arrastra todo lo que ya tenemos en el panel de control de toda la empresa […] volcado a esta
herramienta, pero solamente con acceso para mí».

NO recalcula nada ni toca la carpeta del panel. Lee la SALIDA de sus generadores:
  ~/Downloads/PANEL_RESULTADOS_RO_2026-09-18/ENTREGA/panel_v2.html
     = build_dataset_ro.py + build_extra_ro.py + build_circuito.py + build_financiero.py + build_captacion_extra.py
       + atribucion_anuncios.py → _plantilla/montar_v2.py → render_v2.py  (la v29/v30 del artefacto WeCVRWFTxD3MMdU2jb9siH)
y hace dos cosas:
  1. Abre una COPIA con Chrome sin ventana, le pega extraer.js y deja que el render() del propio panel pinte cada pestaña
     (6 de la empresa + 6 de la captación × 5 periodos). Guarda el HTML de cada pestaña con las clases prefijadas (px-).
  2. Guarda el panel entero tal cual (para la pestaña «Panel original», con todos sus filtros).

SOLO DATOS (N6, 2-oct noche · dudas_pintura.md D-P-N6). Este generador escribe ÚNICAMENTE en data/panel_direccion/.
Nunca escribe estilos ni plantilla: ni modulos/panel_direccion_estilo.js (la hoja vieja de 78 tamaños y 52 colores ya
no se usa: el módulo se pinta con estilos.css y componentes.js), ni la plantilla del panel (_plantilla/, montar_v2.py),
que borraría la pestaña «Atribución» del v30.
Puerta antes de escribir: si falta alguna pestaña (en especial «De qué anuncio» / atr), alguna sale vacía o falta alguna
de las cifras de paridad, sale con código ≠ 0 SIN tocar nada y la tubería se queda con el último dato bueno.
La escritura es atómica: todo a una carpeta temporal dentro de data/ y luego se cambia fichero a fichero.

Salida (todo en data/panel_direccion/, alta en reglas_permisos.json → datos_de_modulo con {"puestos": ["direccion"]}):
  indice.json          · metadatos, periodos, rangos, frescura de cada fuente, pie, cifras de paridad
  empresa.json         · las 6 pestañas de «La empresa»
  captacion_<p>.json   · las 6 pestañas de «La captación» para el periodo p (sep, oct, todo, d14, d7)
  original.json        · el panel v30 entero (HTML), para la pestaña «Panel original»
Uso:  python3 fuentes_panel_direccion/generar_panel_direccion.py
"""
import hashlib
import html
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

AQUI = Path(__file__).resolve().parent
APP = AQUI.parent
ENTREGA = Path.home() / "Downloads/PANEL_RESULTADOS_RO_2026-09-18/ENTREGA"
PANEL = ENTREGA / "panel_v2.html"
SALIDA = APP / "data/panel_direccion"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


def extraer():
    """Ejecuta el render() del panel en Chrome sin ventana y devuelve lo que pinta cada pestaña."""
    pagina = PANEL.read_text(encoding="utf-8")
    script = (AQUI / "extraer.js").read_text(encoding="utf-8")
    assert "</script>" in pagina and pagina.rstrip().endswith("</script>"), "panel_v2.html ha cambiado de forma"
    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / "panel_extraer.html"
        f.write_text(pagina + "\n<script>\n" + script + "\n</script>\n", encoding="utf-8")
        r = subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--window-size=1280,2400",
                            "--virtual-time-budget=15000", "--run-all-compositor-stages-before-draw", "--dump-dom", f.as_uri()],
                           capture_output=True, text=True, timeout=300)
    m = re.search(r'<pre id="salida-extraccion">(.*?)</pre>', r.stdout, re.S)
    if not m:
        sys.exit("Chrome no devolvió la extracción. stderr: " + r.stderr[-800:])
    return json.loads(html.unescape(m.group(1)))


# Error de divisa del cierre de Sofía (25_AUDITORIA_CIERRE_SOFIA.md, 2-oct): las 695 facturas en dólares del equipo y de
# herramientas están sumadas como euros → gastos ene-ago inflados en 39.663 €. El panel v29/v30 copia el cierre tal cual, así
# que su gasto, beneficio, margen y peso del equipo NO se portan: el módulo los toma SOLO de Finanzas (M19, recalculado con Holded
# convertido). Aquí solo queda lo que decía el v29, para enseñarlo al lado («el v29 decía…»). Ingresos, cuota, caja y concentración valen.
CORRECCION_DIVISA = {
    "fuente": "25_AUDITORIA_CIERRE_SOFIA.md (2-oct-2026): Holded convertido con el tipo de cambio de cada factura",
    "efecto_gasto_ene_ago": 39663, "efecto_beneficio_ene_ago": 39209,
    "v29": {"gastos_ene_ago": 415988, "beneficio_ene_ago": 54425, "beneficio_real_ene_ago": 37325, "beneficio_ago": -61.06,
            "margen_bruto_pct": 28.9, "margen_pct": 11.6, "peso_equipo_pct": 72.5, "peso_equipo_ago_pct": 74.2, "meses_caja_31ago": 1.4},
    "no_usar": ["meses de caja 1,4 (usa todo el gasto como si no entrara nada)", "cobros de 1,17 M€ (incluyen ≈ 585.000 € de traspasos entre cuentas propias)"],
}


def cifras_paridad(ex):
    """Cinco cifras del panel para contrastar (se leen del HTML pintado, no se recalculan)."""
    txt = lambda h: re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", h)))
    out = {}
    fres = txt(ex["empresa"]["fres"])
    sep = txt(ex["captacion"]["sep"]["sum"])
    for clave, (fuente, rx) in {
        "inversion_meta_sep": (sep, r"Inversión en Meta ([\d.]+(?:,\d+)? €)"),
        "citas_reservadas_sep": (sep, r"Citas reservadas (\d+)"),
        "firmados_sep": (sep, r"Firmados · columna «Cliente» (\d+)"),
        "cuota_acumulada": (sep, r"Cuota mensual acumulada ([\d.]+ €)"),
        "caja": (fres, r"[Cc]aja[^0-9]{0,60}?([\d.,]+ (?:mil )?€)"),
    }.items():
        m = re.search(rx, fuente)
        out[clave] = m.group(1) if m else None
    return out


EMPRESA = ("fres", "fing", "cli", "fgas", "fcaja", "emp")
CAPTACION = ("sum", "pub", "atr", "res", "vent", "ope")
PERIODOS = ("sep", "oct", "todo", "d14", "d7")


def comprobar(ex, paridad):
    """Puerta: nunca se pierde una pestaña (sobre todo «De qué anuncio») ni una cifra de paridad. Devuelve la lista de fallos."""
    fallos = []
    for t in EMPRESA:
        if not (ex.get("empresa") or {}).get(t, "").strip():
            fallos.append(f"empresa/{t} vacía o ausente")
    for p in PERIODOS:
        tabs = (ex.get("captacion") or {}).get(p) or {}
        for t in CAPTACION:
            if not (tabs.get(t) or "").strip():
                fallos.append(f"captacion_{p}/{t} vacía o ausente")
        if p not in (ex.get("rangos") or {}):
            fallos.append(f"sin rango para {p}")
    if not (ex.get("etiquetas") or {}).get("atr"):
        fallos.append("el panel no trae la pestaña «Atribución» / «De qué anuncio» (atr): ¿se ha rehecho la plantilla con montar_v2.py?")
    for k, v in paridad.items():
        if v is None:
            fallos.append(f"cifra de paridad sin leer: {k}")
    return fallos


def main():
    if not PANEL.exists():
        sys.exit(f"No encuentro {PANEL}")
    ex = extraer()
    paridad = cifras_paridad(ex)
    fallos = comprobar(ex, paridad)
    if fallos:
        sys.exit("panel_direccion · NO se escribe nada (se queda el dato anterior):\n  · " + "\n  · ".join(fallos))
    ahora = datetime.now().strftime("%Y-%m-%d %H:%M")
    origen = {"panel": str(PANEL).replace(str(Path.home()), "~"), "panel_modificado": datetime.fromtimestamp(PANEL.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
              "sha256": hashlib.sha256(PANEL.read_bytes()).hexdigest()[:16], "artefacto": "https://claude.ai/artifact/WeCVRWFTxD3MMdU2jb9siH"}
    base = {"formato": 1, "modulo": "panel-direccion", "generado": ahora, "origen": origen}
    indice = {**base, "foto_panel": ex["generado"], "ventana": ex["ventana"], "fuentes": ex["fres"], "etiquetas": ex["etiquetas"],
              "periodos": ex["periodos"], "rangos": ex["rangos"], "pie": ex["pie"], "ltv_meses": ex["ltv_meses"], "paridad": paridad,
              "correccion_divisa": CORRECCION_DIVISA}
    salidas = {"indice": indice, "empresa": {**base, "pestanas": ex["empresa"]}}
    for p, tabs in ex["captacion"].items():
        salidas[f"captacion_{p}"] = {**base, "periodo": p, "rango": ex["rangos"][p], "pestanas": tabs}
    salidas["original"] = {**base, "html": PANEL.read_text(encoding="utf-8")}

    SALIDA.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=SALIDA.parent, prefix=".panel_direccion_tmp_") as tmp:
        for nombre, obj in salidas.items():
            (Path(tmp) / f"{nombre}.json").write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        for nombre in salidas:
            os.replace(Path(tmp) / f"{nombre}.json", SALIDA / f"{nombre}.json")
    tam = {f.name: f.stat().st_size // 1024 for f in sorted(SALIDA.glob("*.json"))}
    print("panel_direccion ·", ahora, "· foto del panel", ex["generado"], "·", tam)
    print("paridad:", json.dumps(paridad, ensure_ascii=False))


if __name__ == "__main__":
    main()

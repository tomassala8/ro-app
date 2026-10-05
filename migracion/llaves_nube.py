#!/usr/bin/env python3
"""migracion/llaves_nube.py · llevar a la nube las llaves de las APIs que hoy viven en el Mac, SIN repetir las altas.

Las llaves de hoy (llavero del Mac, ficheros .env, variables) ya llevan sus «refresh tokens»: copiarlas tal cual basta
para que la nube lea las mismas APIs. Solo la de GHL agencia rota en cada uso y va por su propio camino (llave_ghl.py).

  python3 migracion/llaves_nube.py                 # REVISAR: qué llaves hay, de dónde salen y si render.yaml las pide
  python3 migracion/llaves_nube.py --exportar      # (Tomás, en su Mac, el día del despliegue) escribe
                                                   # ~/RO_MIGRACION/ro-llaves.env (permiso 600) para pegarlo en Render
Nunca imprime un valor. --exportar se niega a escribir dentro del repositorio. Cursor NO lo ejecuta (regla de la noche).
"""
import os
import re
import stat
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
import config  # noqa: E402

# Llaves que se leen fuera de config.SECRETOS (revisión del 4-oct). Si el inventario de config.py las añade, sobran aquí.
EXTRA = {
    "ANTHROPIC_API_KEY": "IA (ia.py)", "ANTHROPIC_API_KEY_RESPALDO": "IA de respaldo (ia_gasto.py)",
    "MODULARDS_ACCESO_KEY": "Modular (acceso)", "GOOGLE_API_KEY": "Google PageSpeed (paneles)",
    "CLOUDFLARE_API_TOKEN": "Cloudflare", "GHL_PIT_WRITE": "GHL subcuenta de RO (escritura)",
    "CLICKUP_TOKEN_SERVICIO": "ClickUp (llave de servicio para escribir; no la del propietario)",
    "ZOHO_REFRESH_TOKEN_ESCRITURA": "Zoho (escritura, envíos de Desk)",
}


def inventario():
    nombres = dict(config.SECRETOS)
    for n, d in EXTRA.items():
        if n.lower() not in {k.lower() for k in nombres}:
            nombres[n] = d
    return nombres


def pedidas_por_render():
    pedidas = set()
    for f in (RAIZ / "v2" / "render.yaml", RAIZ / "despliegue" / "render.yaml"):
        if f.exists():
            pedidas |= set(re.findall(r"key:\s*([A-Z0-9_]+)", f.read_text()))
    return pedidas


def revisar():
    pedidas = pedidas_por_render()
    filas, faltan_en_render, no_estan = [], [], []
    for nombre, para in sorted(inventario().items(), key=lambda kv: kv[0].lower()):
        origen = config.de_donde(nombre)
        rota = nombre in config.ROTA
        en_render = nombre.upper() in pedidas
        if origen and not rota and not en_render:
            faltan_en_render.append(nombre.upper())
        if not origen:
            no_estan.append(nombre)
        filas.append(f"  {'✔' if origen else '·'} {nombre:<32} {origen or 'no está en este equipo':<22} "
                     f"{'rota: va por llave_ghl.py' if rota else ('en render.yaml' if en_render else 'FALTA en render.yaml')}  ({para})")
    print("Llaves de las APIs (nunca se enseña el valor):")
    print("\n".join(filas))
    print(f"\n{len(filas) - len(no_estan)} de {len(filas)} están en este equipo.")
    if faltan_en_render:
        print("Hay que añadirlas al grupo ro-llaves de render.yaml (sync: false): " + ", ".join(faltan_en_render))
        return 1
    return 0


def exportar():
    salida = Path(os.environ.get("RO_MIGRACION", "~/RO_MIGRACION")).expanduser() / "ro-llaves.env"
    if RAIZ in salida.resolve().parents:
        sys.exit("✘ Me niego a escribir llaves dentro del repositorio.")
    salida.parent.mkdir(parents=True, exist_ok=True)
    lineas, n = ["# ro-llaves · pegar en Render › Env Groups › ro-llaves › «Add from .env». BORRAR después."], 0
    for nombre in sorted(inventario(), key=str.lower):
        if nombre in config.ROTA:
            continue
        v = config.secreto(nombre)
        if v and "\n" not in v:
            lineas.append(f"{nombre.upper()}={v}")
            n += 1
    salida.touch(mode=0o600, exist_ok=True)
    os.chmod(salida, stat.S_IRUSR | stat.S_IWUSR)
    salida.write_text("\n".join(lineas) + "\n")
    print(f"✔ {n} llaves en {salida} (permiso 600). Pégalo en Render (grupo ro-llaves) y bórralo: rm '{salida}'")
    print("  La de GHL agencia (rota) no va ahí: después del despliegue, «llave_ghl.py sembrar» contra la base de la nube,")
    print("  y desde ese momento el Mac no vuelve a lanzar app.py, captacion.py ni externos.py (DESPLIEGUE.md, T6).")


if __name__ == "__main__":
    if "--exportar" in sys.argv:
        exportar()
    else:
        sys.exit(revisar())

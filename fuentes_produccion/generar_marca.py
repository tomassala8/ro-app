#!/usr/bin/env python3
"""
fuentes_produccion/generar_marca.py · Ronda U · U3 (3-oct, cambio #13 del 50): «brief y marca del cliente dentro de la tarea».

Producción (Camilo, Manuel, Alejandro, Emanuel y los de redes) no tiene que salir a ClickUp ni a Drive a buscar la marca:
la tarea abre, en su sitio, el logo, los colores, el tono, lo que nunca se dice, la carpeta del cliente y la última pieza
aprobada. Este script junta lo que ya existe, SOLO LECTURA:

  · tono y «lo que nunca se dice»: el _MANUAL_VOZ_ESTILO.md de cada cliente (carpetas de cartera y entregas del equipo
    en ~/Downloads); la primera frase del apartado «Tono de voz» y hasta 5 frases vetadas.
  · colores: los #RRGGBB del manual o de marca_<cliente>.json; si no hay, los 3 colores dominantes del logo (data/logos.json),
    con el sello «sacado del logo».
  · carpeta: el enlace de Drive del cliente (data/ficha/basica.json).
  · última pieza aprobada: la tarea de Producción del cliente que pasó la revisión interna más recientemente (estados de
    «revisión del cliente» / «enviar al cliente»), con su enlace a ClickUp.

Sale data/produccion/marca.json con «clientes» como LISTA de filas con cliente_id: servir.py la recorta por cliente
(cada uno recibe solo los clientes que puede abrir). Nada de correos ni teléfonos (se quitan del texto del manual).
"""
import base64
import io
import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

AQUI = Path(__file__).resolve().parent.parent
DATA = AQUI / "data"
SALIDA = DATA / "produccion" / "marca.json"
DESCARGAS = Path.home() / "Downloads"
CARPETAS_MANUALES = ["COTI_CARTERA_2026-09-04/clientes", "ENTREGA_EQUIPO"]
RX_MAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
RX_TEL = re.compile(r"(?:\+?\d[\d\s.-]{7,}\d)")
RX_HEX = re.compile(r"#[0-9A-Fa-f]{6}\b")


def norm(t):
    t = unicodedata.normalize("NFD", str(t or "").lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


def limpio(t, tope=320):
    t = RX_MAIL.sub("", RX_TEL.sub("", str(t or "")))
    t = re.sub(r"\*\*|__|`", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    return (t[: tope - 1] + "…") if len(t) > tope else t


def leer(f, defecto=None):
    try:
        return json.loads(Path(f).read_text(encoding="utf-8"))
    except Exception:
        return defecto


def clientes():
    c = leer(DATA / "clientes.json", [])
    return c if isinstance(c, list) else c.get("clientes", [])


def emparejar(nombre_carpeta, lista):
    n = norm(nombre_carpeta.replace("_", " "))
    if not n:
        return None
    mejor = None
    for c in lista:
        cn = norm(c["nombre"])
        if cn == n or c["id"].replace("-", " ") == n:
            return c["id"]
        primera = n.split(" ")[0]
        if len(primera) >= 4 and (cn.startswith(n) or n.startswith(cn) or cn.split(" ")[0] == primera):
            mejor = mejor or c["id"]
    return mejor


def seccion(texto, rx_titulo):
    """Líneas del apartado cuyo título (## …) casa con rx_titulo, hasta el siguiente ## o ---."""
    out, dentro = [], False
    for linea in texto.splitlines():
        if linea.startswith("## "):
            if dentro:
                break
            dentro = bool(re.search(rx_titulo, linea, re.I))
            continue
        if dentro:
            if linea.strip() == "---":
                break
            out.append(linea)
    return out


def tono_de(texto):
    lineas = seccion(texto, r"tono")
    parrafo = []
    for l in lineas:
        if not l.strip():
            if parrafo:
                break
            continue
        if l.lstrip().startswith(("- ", "* ", "#", "|")) and not parrafo:
            continue
        parrafo.append(l.strip())
    return limpio(" ".join(parrafo), 300) or None


def vetado_de(texto):
    frases, dentro = [], False
    for l in texto.splitlines():
        if re.search(r"(nunca se dice|nunca decir|no se dice|prohibid|vetad|evitar)", l, re.I) and not l.lstrip().startswith("-"):
            dentro = True
            continue
        if dentro:
            if l.startswith("## ") or l.strip() == "---":
                break
            if l.lstrip().startswith(("-", "*")):
                f = limpio(l.lstrip("-* ").strip(), 140)
                if f:
                    frases.append(f)
            elif l.strip() and frases:
                break
        if len(frases) >= 5:
            break
    if not frases:   # sin apartado propio: las viñetas con «NUNCA» del vocabulario
        frases = [limpio(l.lstrip("-* ").strip(), 140) for l in texto.splitlines() if l.lstrip().startswith("- ") and re.search(r"\bNUNCA\b", l)][:5]
    return frases[:5]


def dominantes(data_uri, n=3):
    try:
        from PIL import Image
    except Exception:
        return []
    try:
        cab, b64 = data_uri.split(",", 1)
        if "svg" in cab:
            return list(dict.fromkeys(RX_HEX.findall(base64.b64decode(b64).decode("utf-8", "ignore"))))[:n]
        im = Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGBA").resize((64, 64))
    except Exception:
        return []
    cuenta = {}
    for r, g, b, a in im.getdata():
        if a < 128:
            continue
        mx, mn = max(r, g, b), min(r, g, b)
        if mx > 235 and mn > 235:          # blanco de fondo
            continue
        if mx < 25:                        # negro puro: cuenta, pero pesa menos
            pass
        k = (r // 32 * 32 + 16, g // 32 * 32 + 16, b // 32 * 32 + 16)
        cuenta[k] = cuenta.get(k, 0) + 1
    orden = sorted(cuenta.items(), key=lambda x: -x[1])
    out = []
    for (r, g, b), _ in orden:
        h = f"#{min(r, 255):02X}{min(g, 255):02X}{min(b, 255):02X}"
        if all(abs(r - int(o[1:3], 16)) + abs(g - int(o[3:5], 16)) + abs(b - int(o[5:7], 16)) > 60 for o in out):
            out.append(h)
        if len(out) >= n:
            break
    return out


def main():
    lista = clientes()
    por_id = {c["id"]: c for c in lista}
    marca = {cid: {"cliente_id": cid, "nombre": c["nombre"]} for cid, c in por_id.items()}

    # 1 · manuales de voz y estilo
    vistos = set()
    for base in CARPETAS_MANUALES:
        raiz = DESCARGAS / base
        if not raiz.exists():
            continue
        for f in sorted(raiz.rglob("_MANUAL_VOZ_ESTILO.md")):
            carpeta = f.parent.name if f.parent.name != "PARA_SUBIR" else f.parent.parent.name
            cid = emparejar(carpeta, lista)
            if not cid or cid in vistos:
                continue
            texto = f.read_text(encoding="utf-8", errors="ignore")
            m = marca[cid]
            m["tono"] = tono_de(texto)
            m["vetado"] = vetado_de(texto)
            hexes = list(dict.fromkeys(RX_HEX.findall(texto)))[:4]
            if hexes:
                m["colores"], m["colores_de"] = hexes, "manual de marca"
            m["fuente_tono"] = "Manual de voz y estilo del cliente"
            vistos.add(cid)
    for f in DESCARGAS.glob("*/marca_*.json"):
        d = leer(f, {}) or {}
        cid = emparejar(d.get("NOMBRE_DESPACHO") or f.stem.replace("marca_", ""), lista)
        if cid and d:
            hexes = [d[k] for k in ("HEX_PRIMARIO", "HEX_SECUNDARIO", "HEX_ACENTO", "HEX_TEXTO") if RX_HEX.fullmatch(str(d.get(k) or ""))]
            if hexes:
                marca[cid]["colores"], marca[cid]["colores_de"] = list(dict.fromkeys(hexes)), "ficha de marca"
            if d.get("TIPOGRAFIA_TITULOS"):
                marca[cid]["tipografias"] = [x for x in (d.get("TIPOGRAFIA_TITULOS"), d.get("TIPOGRAFIA_CUERPO")) if x]

    # 2 · colores del logo cuando no hay manual de marca
    logos = leer(DATA / "logos.json", {}) or {}
    for cid, m in marca.items():
        uri = logos.get(cid) or (por_id[cid].get("logo") if isinstance(por_id[cid].get("logo"), str) else None)
        m["logo"] = bool(uri)
        if not m.get("colores") and uri and uri.startswith("data:"):
            cs = dominantes(uri)
            if cs:
                m["colores"], m["colores_de"] = cs, "sacado del logo"

    # 3 · carpeta de Drive
    for fila in (leer(DATA / "ficha" / "basica.json", {}) or {}).get("filas", []):
        for c in fila.get("clientes") or []:
            if c.get("ref") in marca and c.get("drive") and str(c["drive"]).startswith("https://"):
                marca[c["ref"]]["carpeta"] = c["drive"]
            if c.get("ref") in marca and c.get("web") and str(c["web"]).startswith("http"):
                marca[c["ref"]].setdefault("web", c["web"])

    # 4 · última pieza aprobada (pasó la revisión interna: espera o va al cliente)
    prod = leer(DATA / "produccion" / "produccion.json", {}) or {}
    aprobadas = {"revisión cliente", "enviar  cliente", "enviar cliente", "ver cliente", "complete", "completado"}
    for r in (prod.get("cola") or []) + (prod.get("revisiones") or []):
        cid = r.get("cli") or r.get("cliente_id")
        if cid not in marca or r.get("estado") not in aprobadas:
            continue
        dias = r.get("dias_estado", r.get("dias"))
        previa = marca[cid].get("ultima_aprobada")
        if previa is None or (dias is not None and (previa.get("dias") is None or dias < previa["dias"])):
            marca[cid]["ultima_aprobada"] = {"tarea": limpio(r.get("tarea"), 140), "id": r.get("id"), "url": f"https://app.clickup.com/t/{r.get('id')}",
                                             "estado": r.get("estado"), "dias": dias}

    filas = [m for m in marca.values() if any(m.get(k) for k in ("tono", "colores", "carpeta", "ultima_aprobada", "vetado"))]
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    SALIDA.write_text(json.dumps({"formato": 1, "generado": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                                  "_que_es": "Brief y marca por cliente para la tarea de Producción (generar_marca.py). Solo lectura.",
                                  "clientes": sorted(filas, key=lambda x: x["nombre"])}, ensure_ascii=False, indent=1), encoding="utf-8")
    # 5 · un fichero por persona (p_<id>): la marca de los clientes de SUS tareas de Producción y de su cartera. Las filas
    #     van con «cli» (no cliente_id): el fichero ya es solo de su dueño (solo_propio en reglas_permisos.json) y producción
    #     no «abre» el cliente (ámbito tareas), pero necesita su marca para hacer la pieza.
    por_persona = {}
    for r in prod.get("cola") or []:
        if r.get("persona_id") and r.get("cli") in marca:
            por_persona.setdefault(r["persona_id"], set()).add(r["cli"])
    for a in leer(DATA / "asignaciones.json", []) or []:
        if a.get("persona_id") and a.get("cliente_id") in marca and not a.get("hasta"):
            por_persona.setdefault(a["persona_id"], set()).add(a["cliente_id"])
    carpeta_p = SALIDA.parent / "marca"
    carpeta_p.mkdir(parents=True, exist_ok=True)
    for viejo in carpeta_p.glob("p_*.json"):
        viejo.unlink()
    validas = {m["cliente_id"] for m in filas}
    for pid, cids in por_persona.items():
        mias = [{**{k: v for k, v in marca[c].items() if k != "cliente_id"}, "cli": c} for c in sorted(cids) if c in validas]
        (carpeta_p / f"p_{pid}.json").write_text(json.dumps({"formato": 1, "persona_id": pid, "clientes": mias}, ensure_ascii=False, indent=1), encoding="utf-8")
    con_tono = sum(1 for m in filas if m.get("tono"))
    print(f"marca.json: {len(filas)} clientes · {con_tono} con tono · {sum(1 for m in filas if m.get('colores'))} con colores · "
          f"{sum(1 for m in filas if m.get('carpeta'))} con carpeta · {sum(1 for m in filas if m.get('ultima_aprobada'))} con pieza aprobada")


if __name__ == "__main__":
    main()

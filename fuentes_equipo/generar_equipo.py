#!/usr/bin/env python3
"""
fuentes_equipo/generar_equipo.py · quién está de verdad en el equipo y su zona horaria (E0 ronda 8, fuente de Tomás).

Fuentes, en este orden (SOLO LECTURA):
  1. ~/Downloads/Plantilla actual 2026.xlsx · hoja «Equipo 2026» (activos con rol, ingreso y dirección) y
     «Desvinculaciones y Salidas» (bajas con fecha de salida).
  2. ~/Downloads/SALARIOS EQUIPO (4).xlsx · hoja del último mes (SEPTIEMBRE 2026): SOLO los nombres de quién cobra.
     Los importes no se leen aquí (están en el almacén privado de sueldos).
  3. Miembros de ClickUp (~/RO_HERRAMIENTAS/clickup_api/cu.py, llave propia, 1 petición GET /team).

Regla: activo = está en «Equipo 2026» y (cobra en septiembre o es miembro de ClickUp). Además Tomás (dirección),
Sofía (administración: no está en la hoja; activa si cobra o está en ClickUp) y los setters que Mili activó.
Baja = está en «Desvinculaciones» (con fecha) → baja y a la lista de salida de accesos si sigue en alguna herramienta.
Zona horaria desde el país de la dirección (Argentina, Venezuela, España); sin país claro, Argentina «a confirmar».

PRIVACIDAD: de la plantilla solo entran nombre, rol, fecha de ingreso, país, zona y fecha de salida.
NO entran direcciones, teléfonos, correos personales ni la columna «Decisión». Regla de Tomás (2-oct): el cumpleaños
(SOLO día y mes, sin año) y la fecha de ingreso los ve todo el equipo → personas.json (cumple_dia_mes, fecha_ingreso).

Escribe: fuentes_equipo/equipo.json (lo lee build_data.py) · data/equipo/salida_accesos.json
"""
import json
import re
import sys
import unicodedata
from datetime import date, datetime
from pathlib import Path

AQUI = Path(__file__).resolve().parent
APP = AQUI.parent
PLANTILLA = Path.home() / "Downloads/Plantilla actual 2026.xlsx"
SALARIOS = Path.home() / "Downloads/SALARIOS EQUIPO (4).xlsx"
FASE0 = APP.parent / "20_FASE0_DATOS/personas.json"
CORREOS = Path.home() / "Downloads/Equipo - nombres y correos.xlsx"   # Tomás, 2-oct: correo de entrada (Cloudflare Access)
ZONAS = {"Argentina": "America/Argentina/Buenos_Aires", "Venezuela": "America/Caracas", "España": "Europe/Madrid"}
# Casos que Tomás ha explicado a mano (2-oct).
A_MANO = {"valeria": {"pais": "Venezuela", "zona": "America/Caracas", "a_confirmar": False,
                      "fuente": "Tomás, 2-oct: hora de Venezuela"},
          "sofia": {"pais": "España", "zona": "Europe/Madrid", "a_confirmar": False, "fuente": "Tomás, 2-oct: está en España"},
          "tomas": {"pais": "España", "zona": "Europe/Madrid", "a_confirmar": False, "fuente": "vive en España"}}


def norm(t):
    t = unicodedata.normalize("NFKD", str(t or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9@.]+", " ", t).strip()


def pais_de(direccion):
    t = norm(direccion)
    if re.search(r"venezuel|caracas|maracaibo|barquisimeto|carabobo|lara\b|zulia|merida", t):
        return "Venezuela"
    if re.search(r"argentin|buenos aires|caba|cordoba|rosario|mendoza|santa fe|la plata|tucuman|mar del plata|neuquen|salta", t):
        return "Argentina"
    if re.search(r"espana|spain|madrid|barcelona|sevilla|malaga|alicante", t):
        return "España"
    return None


def fecha(v):
    if isinstance(v, (datetime, date)):
        return v.strftime("%Y-%m-%d")
    m = re.fullmatch(r"\s*(\d{1,2})/(\d{1,2})/(\d{4})\s*", str(v or ""))
    return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}" if m else None


def main():
    import openpyxl
    personas = json.loads((APP / "data/personas.json").read_text())
    f0 = {p["id"]: p for p in json.loads(FASE0.read_text())["personas"]}
    claves, pila = {}, {}
    for p in personas:
        nombre = norm(p["nombre"])
        trozos = nombre.split()
        apellido = trozos[-1] if len(trozos) > 1 else ""
        alias = {norm(a) for a in [p.get("alias"), *(p.get("alias_todos") or [])] if a}
        for c in {nombre, " ".join(trozos[:2]), trozos[0] + " " + apellido if apellido else nombre,
                  *[f"{a} {apellido}".strip() for a in alias]}:
            claves.setdefault(c, p["id"])
        for a in {trozos[0], *alias}:
            pila.setdefault(a, set()).add(p["id"])
    for a, ids in pila.items():          # nombre de pila (o apodo) suelto, solo si no se repite: «Milagros», «Maca»
        if len(ids) == 1:
            claves.setdefault(a, next(iter(ids)))

    def quien(nombre):
        n = norm(nombre)
        if n in claves:
            return claves[n]
        t = n.split()
        for c in (" ".join(t[:2]), f"{t[0]} {t[-1]}" if len(t) > 1 else n):
            if c in claves:
                return claves[c]
        cand = {pid for k, pid in claves.items() if t and k.split()[0] == t[0] and len(t) > 1 and t[1] in k}
        return cand.pop() if len(cand) == 1 else None

    wb = openpyxl.load_workbook(PLANTILLA, data_only=True, read_only=True)
    equipo, salidas, cumples, sin_ficha = {}, {}, {}, []
    for ws in wb.worksheets:
        filas = [r for r in ws.iter_rows(values_only=True) if any(c is not None for c in r)]
        cab = [str(c or "").strip().lower() for c in filas[0]]
        col = lambda nombre: next((i for i, c in enumerate(cab) if c.startswith(nombre)), None)
        i_nom, i_rol, i_ing, i_dir = col("nombre"), col("rol"), col("fecha de ingreso"), col("dirección ") if col("dirección ") is not None else col("dirección")
        i_dir = next((i for i, c in enumerate(cab) if c == "dirección"), i_dir)
        i_sal, i_cum = col("fecha de salida"), col("fecha de cumpl")
        es_salida = ws.title.lower().startswith("desvinc")
        for r in filas[1:]:
            r = tuple(r) + (None,) * (len(cab) - len(r))          # filas más cortas que la cabecera
            if not r or not isinstance(r[i_nom], str) or not r[i_nom].strip():
                continue
            pid = quien(r[i_nom])
            pais = pais_de(r[i_dir] if i_dir is not None and isinstance(r[i_dir], str) else "")
            fila = {"nombre_hoja": r[i_nom].strip(), "rol": (r[i_rol] or "").strip() if isinstance(r[i_rol], str) else None,
                    "ingreso": fecha(r[i_ing]) if i_ing is not None else None, "pais": pais}
            if es_salida:
                fila["fecha_salida"] = fecha(r[i_sal]) if i_sal is not None else None
                (salidas.__setitem__(pid, fila) if pid else sin_ficha.append({**fila, "hoja": "Desvinculaciones"}))
            else:
                if i_cum is not None and isinstance(r[i_cum], (datetime, date)) and pid:
                    cumples[pid] = r[i_cum].strftime("%m-%d")          # sin año
                (equipo.__setitem__(pid, fila) if pid else sin_ficha.append({**fila, "hoja": "Equipo 2026"}))

    # 2 · Quién cobra en septiembre (solo nombres)
    cobra = set()
    ws = openpyxl.load_workbook(SALARIOS, data_only=True, read_only=True)["SEPTIEMBRE 2026"]
    filas = [r for r in ws.iter_rows(values_only=True) if any(c is not None for c in r)]
    i_p = [str(c or "").strip() for c in filas[0]].index("Persona")
    for r in filas[1:]:
        if isinstance(r[i_p], str) and r[i_p].strip() and not r[i_p].lower().startswith("salario"):
            pid = quien(r[i_p])
            if pid:
                cobra.add(pid)

    # 3 · Miembros de ClickUp (1 petición de lectura)
    clickup, error_cu = set(), None
    try:
        sys.path.insert(0, str(Path.home() / "RO_HERRAMIENTAS/clickup_api"))
        import cu
        equipo_cu = next((t for t in cu.get("/team").get("teams", []) if str(t.get("id")) == cu.TEAM), None) or {}
        por_correo = {}
        for p in personas:
            for c in [p.get("correo"), *(p.get("otros_correos") or [])]:
                if c:
                    por_correo[c.lower()] = p["id"]
        for m in equipo_cu.get("members", []):
            u = m.get("user") or {}
            pid = por_correo.get((u.get("email") or "").lower()) or quien(u.get("username") or "")
            if pid:
                clickup.add(pid)
    except Exception as e:
        error_cu = f"ClickUp no se pudo leer: {type(e).__name__}"

    # Correo de entrada (fuente oficial de Tomás, 2-oct): hoja «Equipo», columnas Nombre y Correo. Es el que va a Cloudflare Access.
    correos, correos_sin_ficha = {}, []
    if CORREOS.exists():
        wbc = openpyxl.load_workbook(CORREOS, read_only=True)
        wsc = wbc["Equipo"] if "Equipo" in wbc.sheetnames else wbc.worksheets[0]
        for r in list(wsc.iter_rows(values_only=True))[1:]:
            if not r or not r[0] or len(r) < 2 or not r[1]:
                continue
            pid = quien(str(r[0]))
            if pid:
                correos[pid] = str(r[1]).strip().lower()
            else:
                correos_sin_ficha.append(str(r[0]).strip())

    out = {}
    for p in personas:
        pid = p["id"]
        e, s_ = equipo.get(pid), salidas.get(pid)
        pais = (A_MANO.get(pid) or {}).get("pais") or (e or s_ or {}).get("pais")
        zona = (A_MANO.get(pid) or {}).get("zona") or ZONAS.get(pais) or ZONAS["Argentina"]
        a_conf = (A_MANO.get(pid) or {}).get("a_confirmar", pais is None)
        if s_ and not e:
            estado, motivo = "baja", f"Desvinculación con salida el {s_.get('fecha_salida') or 'sin fecha'}"
        elif pid == "tomas":
            estado, motivo = "activo", "dirección"
        elif pid.startswith("setter_"):
            estado, motivo = p.get("estado"), "setters: los activa Mili"
        elif pid == "sofia":
            estado, motivo = ("activo", "administración: cobra o está en ClickUp") if (pid in cobra or pid in clickup) else ("dudoso", "administración: ni cobra en septiembre ni está en ClickUp")
        elif e and (pid in cobra or pid in clickup):
            estado, motivo = "activo", "en «Equipo 2026» y " + ("cobra en septiembre" if pid in cobra else "activa en ClickUp")
        elif e:
            estado, motivo = "dudoso", "en «Equipo 2026» pero ni cobra en septiembre ni está en ClickUp"
        else:
            estado, motivo = ("baja" if p.get("estado") == "baja" else "dudoso"), "no está en la plantilla de 2026"
        out[pid] = {"estado": estado, "motivo": motivo, "rol": (e or s_ or {}).get("rol"), "ingreso": (e or s_ or {}).get("ingreso"),
                    "fecha_salida": (s_ or {}).get("fecha_salida"), "pais": pais, "zona": zona,
                    "zona_fuente": (A_MANO.get(pid) or {}).get("fuente") or (f"dirección en {pais} (plantilla 2026)" if pais else "sin país en la plantilla: Argentina por defecto"),
                    "zona_a_confirmar": bool(a_conf), "cobra_sep": pid in cobra, "clickup": pid in clickup if not error_cu else None,
                    "cumple_dia_mes": cumples.get(pid), "correo_entrada": correos.get(pid)}

    # Lista de salida: de baja y todavía en alguna herramienta (ClickUp en vivo; Desk, CRM y Zoom según la fase 0)
    salida = []
    for pid, d in out.items():
        if d["estado"] != "baja":
            continue
        herramientas = []
        if d["clickup"]:
            herramientas.append("ClickUp")
        fuentes = list((f0.get(pid) or {}).get("correo_fuente") or [])
        for o in (f0.get(pid) or {}).get("otros_correos") or []:
            fuentes += o.get("fuentes") or []
        for nombre, clave in (("Zoho Desk", "Desk"), ("Zoho CRM", "CRM"), ("Zoom", "Zoom")):
            if any(clave in x and "[active]" in x for x in fuentes):
                herramientas.append(nombre)
        salida.append({"persona_id": pid, "nombre": next(p["nombre"] for p in personas if p["id"] == pid), "fecha_salida": d["fecha_salida"],
                       "sigue_en": herramientas, "revisar_tambien": ["GoHighLevel", "Zadarma"],
                       "contradiccion": "sigue activa en ClickUp" if d["clickup"] else None})

    (AQUI / "_privado").mkdir(exist_ok=True)  # correos de entrada: ruta privada, fuera del escáner y de la subida
    (AQUI / "_privado" / "equipo.json").write_text(json.dumps({"generado": datetime.now().isoformat(timespec="minutes"), "error_clickup": error_cu,
                                                  "personas": out, "sin_ficha_en_la_app": sin_ficha,
                                                  "correos": {"fichero": CORREOS.name, "existe": CORREOS.exists(), "casados": len(correos),
                                                              "sin_ficha_en_la_app": correos_sin_ficha}}, ensure_ascii=False, indent=1))
    (APP / "data/equipo").mkdir(parents=True, exist_ok=True)
    (APP / "data/equipo/salida_accesos.json").write_text(json.dumps({"generado": datetime.now().isoformat(timespec="minutes"),
        "que_es": "Personas de baja (Desvinculaciones y Salidas) que pueden seguir con acceso: hay que quitárselo.", "personas": salida}, ensure_ascii=False, indent=1))
    print(f"equipo: {sum(1 for d in out.values() if d['estado'] == 'activo')} activas · {sum(1 for d in out.values() if d['estado'] == 'baja')} de baja · "
          f"{sum(1 for d in out.values() if d['estado'] == 'dudoso')} dudosas · cobran en sept {len(cobra)} · ClickUp {len(clickup)}{' (' + error_cu + ')' if error_cu else ''} · "
          f"sin ficha {len(sin_ficha)} · lista de salida {len(salida)} · correos de entrada {len(correos)}"
          f"{' (sin ficha: ' + ', '.join(correos_sin_ficha) + ')' if correos_sin_ficha else ''}")


if __name__ == "__main__":
    main()

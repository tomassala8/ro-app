#!/usr/bin/env python3
"""
fuentes_equipo/generar_primera_semana.py · A10 «Tu primera semana» (R15a, 2-oct-2026). SOLO LEE.

Para cada puesto, lo que una persona recién llegada necesita en sus primeros días, sacado de la guía del equipo
(../40_GUIA_EQUIPO/NN_*.md) y del índice de pantallas (modulos/indice.js, el mismo que decide el menú):
  · la guía de su puesto: para qué entra, qué ve al entrar y su número que manda (texto llano, sin rutas ni ficheros);
  · sus 3 pantallas principales (las primeras de su menú en el orden de trabajo de RO);
  · los 5 pasos de la primera semana (A10): leer la guía, abrir sus 3 pantallas, entender su número que manda,
    probar la búsqueda (⌘K) y mandar un «Algo va mal» de prueba.

Escribe data/primera_semana/guias.json (sin datos personales: es lo mismo para todo el puesto). Quién es nueva, su jefe y
sus clientes lo pone la pantalla con lo que la persona ya ve (personas y asignaciones de la sesión).
"""
import json
import re
import sys
from datetime import datetime
from pathlib import Path

AQUI = Path(__file__).resolve().parent
APP = AQUI.parent
GUIAS = APP.parent / "40_GUIA_EQUIPO"
SALIDA = APP / "data" / "primera_semana" / "guias.json"
sys.path.insert(0, str(APP))
import permisos as P  # noqa: E402

GUIA_DE_PUESTO = {
    "direccion": "01", "finanzas_direccion": "01", "ventas_ro": "01", "administracion": "02", "operaciones": "03",
    "proyectos": "04", "jefa_seo": "04", "rrhh": "05", "account": "06", "trafficker": "07", "jefa_publicidad": "07",
    "especialista_ghl": "08", "jefa_crm": "08", "tecnico_altas": "09", "seo": "10", "ficha_google": "10", "web": "11",
    "redes": "12", "produccion": "13", "setters": "14", "outreach": "15",
}
# Sus 3 pantallas: las de su oficio primero (si las ve); si falta alguna, se completa con el orden general.
PREFERIDAS = {
    "direccion": ["mi-dia", "panel-direccion", "decisiones"], "finanzas_direccion": ["finanzas", "panel-direccion", "mi-dia"],
    "administracion": ["finanzas", "mi-dia", "ficha"], "operaciones": ["mi-dia", "en-rojo", "alertas"],
    "proyectos": ["mi-dia", "incidencias", "ficha"], "rrhh": ["personas", "horas", "mi-dia"],
    "account": ["mi-dia", "bandeja", "ficha"], "trafficker": ["mi-dia", "captacion", "ficha"],
    "jefa_publicidad": ["mi-dia", "captacion", "alertas"], "especialista_ghl": ["mi-dia", "salud-crm", "ficha"],
    "jefa_crm": ["mi-dia", "salud-crm", "alertas"], "tecnico_altas": ["mi-dia", "clientes-nuevos", "conexiones"],
    "jefa_seo": ["mi-dia", "seo-web", "alertas"], "seo": ["mi-dia", "seo-web", "ficha"], "ficha_google": ["mi-dia", "seo-web", "ficha"],
    "web": ["mi-dia", "seo-web", "incidencias"], "redes": ["mi-dia", "redes", "produccion"], "produccion": ["mi-dia", "produccion", "horas"],
    "setters": ["setters", "agenda", "chat-equipo"], "ventas_ro": ["ventas-ro", "mi-dia", "agenda"], "outreach": ["mi-dia", "prospeccion", "produccion"],
}
ORDEN_PANTALLAS = ["mi-dia", "bandeja", "ficha", "alertas", "agenda", "en-rojo", "incidencias", "produccion", "horas"]


def plano(t):
    t = re.sub(r"`[^`]*\.(?:md|json|py|js|png|jpg)`", "", t)               # rutas de ficheros fuera
    t = re.sub(r"\*\*|__|`", "", t)
    t = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", t)
    t = re.sub(r"\s+", " ", t).strip()
    t = re.sub(r"\s+-\s+(?=[A-ZÁÉÍÓÚÑ¿])", " · ", t)          # viñetas de una lista aplanada
    return t


def recortar(t, n):
    t = plano(t)
    if len(t) <= n:
        return t
    corte = t[:n].rsplit(". ", 1)[0]
    return (corte if len(corte) > n * 0.5 else t[:n].rsplit(" ", 1)[0]) + "…"


def tabla_md(bloque):
    """R16: una tabla markdown («| Puesto | Número | Verde | Ámbar | Rojo |») → filas {cabecera: valor} en texto llano.
    None si el bloque no es una tabla."""
    lineas = [l.strip() for l in bloque.splitlines() if l.strip()]
    if len(lineas) < 2 or not all(l.startswith("|") for l in lineas):
        return None
    celdas = lambda l: [plano(c) for c in l.strip("|").split("|")]
    cab = [c.lower() for c in celdas(lineas[0])]
    filas = []
    for l in lineas[1:]:
        if re.match(r"^\|\s*:?-", l):
            continue
        v = celdas(l)
        filas.append({cab[i] if i < len(cab) else f"col{i}": v[i] for i in range(len(v)) if v[i]})
    return filas


def tabla_a_texto(filas):
    """«Beneficio del mes… (Dirección) · verde: en la trayectoria · ámbar: … · rojo: …», una frase por fila."""
    out = []
    for f in filas:
        quien = f.get("puesto") or f.get("quién") or f.get("quien") or ""
        num = f.get("número") or f.get("numero") or ""
        partes = [f"{num}{f' ({quien})' if quien else ''}".strip()]
        for k, n in (("verde", "verde"), ("ámbar", "ámbar"), ("ambar", "ámbar"), ("rojo", "rojo")):
            if f.get(k):
                partes.append(f"{n}: {f[k]}")
        out.append(" · ".join(p for p in partes if p))
    return ". ".join(out)


def secciones(md):
    out, actual = {}, None
    for linea in md.splitlines():
        m = re.match(r"^##\s+(\d+)\s*·\s*(.+)$", linea)
        if m:
            actual = int(m.group(1))
            out[actual] = {"titulo": m.group(2).strip(), "lineas": []}
        elif actual is not None and not linea.startswith("## "):
            out[actual]["lineas"].append(linea)
        elif linea.startswith("## "):
            actual = None
    return out


def leer_guia(num):
    f = next(iter(sorted(GUIAS.glob(f"{num}_*.md"))), None)
    if not f:
        return None
    md = f.read_text(errors="ignore")
    titulo = re.search(r"^#\s+(.+)$", md, re.M)
    titulo = titulo.group(1).split("·")[-1].strip() if titulo else f.stem
    para_que = re.search(r"^\*\*Para qué entras:\*\*\s*(.+)$", md, re.M)
    S = secciones(md)
    entrar = [plano(re.sub(r"^\s*[-*\d.]+\s*", "", l)) for l in S.get(1, {}).get("lineas", []) if l.strip().startswith(("-", "1", "2", "3", "4", "5", "6", "7"))]
    numero, numero_tabla = "", None
    for bloque in "\n".join(S.get(2, {}).get("lineas", [])).split("\n\n"):
        if bloque.strip():
            numero_tabla = tabla_md(bloque)
            # R16: la tabla del número que manda llegaba en bruto (con «|» a la vista): ahora, texto llano y filas aparte.
            numero = recortar(tabla_a_texto(numero_tabla), 360) if numero_tabla else recortar(bloque, 360)
            break
    cada = [l for l in S.get(3, {}).get("lineas", []) if l.startswith("|") and not re.match(r"^\|\s*-", l)][1:4]
    rutina = [" · ".join(plano(c) for c in l.strip("|").split("|") if plano(c)) for l in cada]
    return {
        "fichero_num": num, "titulo": titulo,
        "para_que": recortar(para_que.group(1), 240) if para_que else "",
        "al_entrar": [recortar(x, 200) for x in entrar if x][:6],
        "numero_que_manda": numero,
        **({"numero_tabla": numero_tabla[:6]} if numero_tabla else {}),
        "rutina": [recortar(x, 200) for x in rutina if x],
    }


def pantallas_de(puesto, modulos):
    persona = {"id": "_", "puestos": [puesto]}
    out = []
    for m in PREFERIDAS.get(puesto, []) + ORDEN_PANTALLAS:
        if m in modulos and m not in out and P._nivel_modulo(persona, modulos[m]):
            out.append(m)
    return out[:3]


def main():
    modulos = P.cargar_modulos()
    titulos = {m: t for m, t in re.findall(r"\{\s*id:\s*'([\w\-]+)'[^}]*?titulo:\s*'([^']+)'", (APP / "modulos" / "indice.js").read_text(), re.S)}
    puestos = {}
    cache = {}
    for pu in [p["id"] for p in P.REGLAS["puestos"]]:
        num = GUIA_DE_PUESTO.get(pu)
        g = cache.setdefault(num, leer_guia(num)) if num else None
        pant = pantallas_de(pu, modulos)
        puestos[pu] = {
            "guia": g,
            "pantallas": [{"id": m, "titulo": titulos.get(m, m), "ruta": f"#/{m}"} for m in pant],
        }
    doc = {
        "formato": "primera_semana.v1",
        "generado": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "dias_ventana": 14,
        "pasos": [
            {"n": 1, "id": "guia", "texto": "Lee la guía de tu puesto", "detalle": "Cinco minutos: qué ves al entrar, tu número que manda y tu rutina."},
            {"n": 2, "id": "pantallas", "texto": "Abre tus 3 pantallas", "detalle": "Las que más vas a usar. Ábrelas una vez y mira qué hay."},
            {"n": 3, "id": "numero", "texto": "Entiende tu número que manda", "detalle": "El que dice si tus clientes van bien. Si no lo entiendes, pregúntaselo a tu jefe."},
            {"n": 4, "id": "buscar", "texto": "Prueba la búsqueda (⌘K o Ctrl+K)", "detalle": "Busca un cliente tuyo y ábrelo desde ahí."},
            {"n": 5, "id": "algo_va_mal", "texto": "Manda un «Algo va mal» de prueba", "detalle": "Con el botón de arriba. Escribe «Prueba de mi primera semana»: así sabes cómo avisar."},
        ],
        "puestos": puestos,
        "fuente": "Guía del equipo (40_GUIA_EQUIPO) y menú de cada puesto (indice.js)",
    }
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    SALIDA.write_text(json.dumps(doc, ensure_ascii=False, indent=1))
    sin = [p for p, v in puestos.items() if not v["guia"]]
    print(f"primera semana: {len(puestos)} puestos · guía en {len(puestos) - len(sin)}" + (f" · sin guía: {', '.join(sin)}" if sin else ""))


if __name__ == "__main__":
    main()

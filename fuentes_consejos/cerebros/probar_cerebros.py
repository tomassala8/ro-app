#!/usr/bin/env python3
"""fuentes_consejos/cerebros/probar_cerebros.py · pruebas de los CEREBROS DE ÁREA (4-oct-2026). Sin servidor y sin IA.

Comprueba:
  1. Forma: cada <area>.json carga, tiene _meta, principios y situaciones con todos los campos del esquema.
  2. Profundidad: 3-6 causas, 3-7 pasos de diagnóstico, «si_falla» apunta a una causa de la ficha.
  3. Ids únicos en TODOS los cerebros y con el prefijo de su área.
  4. Disparadores reales: tipos de consejo (conocimiento/tipos.json), alertas (fuentes_alertas/generar_alertas.py),
     indicadores (indicadores.json) y reglas (conocimiento/reglas.json) existen en la app.
  5. Fuentes: cada fichero lleva prefijo de repo; si el repo está en este ordenador, el fichero existe y la línea cabe.
  6. Nada sensible: ni correos, ni teléfonos, ni contraseñas o claves.
  7. Cobertura: cada tipo de consejo de tipos.json tiene al menos una ficha.
  8. Buscador: cada ficha se encuentra por su propio título (top 3) y las consultas del equipo dan el área correcta.
  9. Tamaño: la ficha compacta que va a la IA cabe en ≈ 2.200 tokens.

  python3 fuentes_consejos/cerebros/probar_cerebros.py [--estricto]   (estricto: los avisos también fallan)
Repos locales: variables RO_EQUIPO, HCG, CENTRAL o carpetas conocidas (~/RO_EQUIPO, ~/ro-equipo, ...).
"""
import json
import os
import re
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
APP = AQUI.parent.parent
sys.path.insert(0, str(AQUI))
import buscar as B  # noqa: E402

PREFIJO = {"direccion": "dir_", "operaciones": "ope_", "account": "acc_", "comunicacion": "com_", "altas": "alt_",
           "publicidad": "pub_", "crm": "crm_", "setters": "set_", "seo_web": "seo_", "redes_produccion": "rp_",
           "ventas_ro": "ven_", "personas_admin": "per_"}
CAMPOS = ["id", "titulo", "puestos", "disparadores", "sintoma", "gravedad", "plazo", "diagnostico", "causas",
          "acciones_inmediatas", "que_no_hacer", "escalar", "exito", "fuentes"]
REPOS = {
    "ro-equipo": ["RO_EQUIPO", "~/RO_EQUIPO", "~/ro-equipo", "/home/claude/ro-equipo"],
    "hormozi-cole-gordon": ["HCG", "~/Hormozi-Cole-Gordon", "/home/claude/Hormozi-Cole-Gordon"],
    "central": ["CENTRAL", "~/Mac-Tom-s-la-Central", "/home/claude/Mac-Tom-s-la-Central"],
    "skills-compartidas": ["SKILLS_COMPARTIDAS", "~/skills-compartidas-entre-compas",
                           "/home/claude/skills-compartidas-entre-compas"],
    "ro-skills": ["RO_SKILLS", "~/ro-skills", "/home/claude/ro-skills"],
    "ro-app": [str(APP)],
}
RE_CORREO = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
RE_TEL = re.compile(r"(?<![\d.,])(?:\+34[\s-]?)?[6789]\d{2}[\s-]?\d{3}[\s-]?\d{3}(?![\d.,])")
# valor con pinta de secreto: lleva cifra o símbolo («ninguna contraseña: entramos con...» no cuenta)
RE_SECRETO = re.compile(r"(contrase[ñn]a|password|passwd|api[_ ]?key|token)\s*[:=]\s*(?=\S*[\d@#$%&*!])\S{6,}"
                        r"|sk-[A-Za-z0-9]{10,}", re.I)
# consultas como las haría el equipo → área esperada en el primer resultado
CONSULTAS = [
    ("los leads no se presentan a las citas", {"crm", "setters", "publicidad"}),
    ("el cliente está enfadado y quiere darse de baja", {"account", "comunicacion", "operaciones", "direccion"}),
    ("la campaña de meta no gasta", {"publicidad"}),
    ("el coste por lead se ha disparado", {"publicidad"}),
    ("la web se ha caído", {"seo_web"}),
    ("hemos bajado posiciones en google", {"seo_web"}),
    ("cómo contesto un correo de queja", {"comunicacion", "account"}),
    ("el cliente no nos da los accesos para el alta", {"altas"}),
    ("no ha pagado la factura", {"personas_admin", "account", "direccion", "operaciones"}),
    ("no publicamos en redes esta semana", {"redes_produccion"}),
    ("el prospecto dice que es caro", {"ventas_ro", "setters"}),
    ("un empleado no imputa horas", {"personas_admin", "operaciones"}),
    ("whatsapp desconectado en gohighlevel", {"crm"}),
    ("leads sin llamar en el crm", {"crm", "setters", "account"}),
]

# alerta de la app → área de la primera ficha
DISPAROS = [("crm_citas_sin_estado", "crm"), ("web_caida", "seo_web"), ("pub_critico", "publicidad"),
            ("acc_correos", "account"), ("seo_rojo", "seo_web"), ("redes_hueco", "redes_produccion"),
            ("alta_fuera_plazo", "altas")]


def raiz_repo(nombre):
    for c in REPOS.get(nombre, []):
        p = os.environ.get(c) if c.isupper() else os.path.expanduser(c)
        if p and Path(p).is_dir():
            return Path(p)
    return None


def ids_app():
    tipos = set(json.loads((APP / "fuentes_consejos/conocimiento/tipos.json").read_text())["tipos"])
    reglas = {r["id"] for r in json.loads((APP / "fuentes_consejos/conocimiento/reglas.json").read_text())["reglas"]}
    ga = (APP / "fuentes_alertas/generar_alertas.py").read_text()
    i = ga.find("REGLAS = [")
    alertas = set(re.findall(r'"id":\s*"([a-z0-9_]+)"', ga[i:])) if i >= 0 else set()
    ind = json.loads((APP / "indicadores.json").read_text())
    indic = {x["id"] for x in ind.get("indicadores", [])}
    return tipos, alertas, indic, reglas


def correr(estricto=False):
    errores, avisos = [], []
    tipos, alertas, indic, reglas = ids_app()
    lineas_cache = {}
    vistos = {}
    cb = B.cerebros()
    faltan = [a for a in B.AREAS if a not in cb]
    if faltan:
        errores.append(f"faltan cerebros: {', '.join(faltan)}")
    total = 0
    for area, c in cb.items():
        m = c.get("_meta", {})
        if m.get("area") != area:
            errores.append(f"{area}: _meta.area = {m.get('area')!r}")
        if not c.get("principios"):
            avisos.append(f"{area}: sin principios")
        for s in c.get("situaciones", []):
            total += 1
            sid = s.get("id", "?")
            donde = f"{area}/{sid}"
            for k in CAMPOS:
                if not s.get(k):
                    errores.append(f"{donde}: falta «{k}»")
            if sid in vistos:
                errores.append(f"{donde}: id repetido (también en {vistos[sid]})")
            vistos[sid] = area
            if not sid.startswith((area + "_", area.replace("_", "") + "_", PREFIJO[area], area.split("_")[0] + "_")):
                avisos.append(f"{donde}: no empieza por {area}_")
            if s.get("gravedad") not in ("alta", "media", "baja"):
                errores.append(f"{donde}: gravedad {s.get('gravedad')!r}")
            causas = s.get("causas", [])
            ncaus, ndiag = len(causas), len(s.get("diagnostico", []))
            if not 3 <= ncaus <= 6:
                avisos.append(f"{donde}: {ncaus} causas (3-6)")
            if not 3 <= ndiag <= 7:
                avisos.append(f"{donde}: {ndiag} pasos de diagnóstico (3-7)")
            cids = {x.get("id") for x in causas}
            for d in s.get("diagnostico", []):
                sf = d.get("si_falla")
                if sf and sf not in cids and not str(sf).startswith(("escalar", "ok", "seguir", "paso")):
                    avisos.append(f"{donde}: paso {d.get('paso')} si_falla={sf!r} no es una causa")
            for x in causas:
                if not x.get("solucion"):
                    errores.append(f"{donde}/{x.get('id')}: causa sin solución")
            d = s.get("disparadores", {})
            for lista, valido, nom in (("tipos_consejo", tipos, "tipo"), ("alertas", alertas, "alerta"),
                                        ("indicadores", indic, "indicador")):
                for x in d.get(lista, []) or []:
                    if x not in valido:
                        errores.append(f"{donde}: {nom} inexistente {x!r}")
            for x in s.get("reglas_relacionadas", []) or []:
                if x not in reglas:
                    errores.append(f"{donde}: regla inexistente {x!r}")
            if len(d.get("palabras_clave", []) or []) < 4:
                avisos.append(f"{donde}: pocas palabras clave")
            for f in s.get("fuentes", []):
                fi = str(f.get("fichero", ""))
                if fi == "criterio":
                    continue
                if ":" not in fi:
                    errores.append(f"{donde}: fuente sin prefijo de repo {fi!r}")
                    continue
                repo, ruta = fi.split(":", 1)
                if repo not in REPOS:
                    errores.append(f"{donde}: repo desconocido {repo!r}")
                    continue
                r = raiz_repo(repo)
                if not r:
                    continue
                p = r / ruta
                if not p.is_file():
                    errores.append(f"{donde}: no existe {fi}")
                    continue
                ln = f.get("linea")
                if isinstance(ln, int):
                    if p not in lineas_cache:
                        lineas_cache[p] = sum(1 for _ in p.open(encoding="utf-8", errors="ignore"))
                    if ln > lineas_cache[p]:
                        errores.append(f"{donde}: {fi} línea {ln} > {lineas_cache[p]}")
            texto = json.dumps(s, ensure_ascii=False)
            for rx, nom in ((RE_CORREO, "correo"), (RE_TEL, "teléfono"), (RE_SECRETO, "secreto")):
                hit = rx.search(texto)
                if hit:
                    errores.append(f"{donde}: posible {nom}: {hit.group(0)[:30]!r}")
            t = B.tokens_aprox(B.para_ia(dict(s, area=area)))
            if t > 2200:            # el diagnosticador maestro del embudo (7 tramos) ronda los 2.000: es su tamaño natural
                avisos.append(f"{donde}: ficha para IA de ≈{t} tokens")
    # cobertura de tipos
    ix = B.construir()
    sin = sorted(tipos - set(ix["tipo"]))
    if sin:
        avisos.append(f"tipos de consejo sin ficha ({len(sin)}): {', '.join(sin)}")
    # buscador: autoconsulta por título
    fallos = []
    for sid, meta in ix["situaciones"].items():
        top = [f["id"] for _, f in B.buscar(meta["titulo"], n=3)]
        if sid not in top:
            fallos.append(sid)
    if total and len(fallos) / total > 0.05:
        errores.append(f"buscador: {len(fallos)}/{total} fichas no salen por su título (máx 5 %): {fallos[:10]}")
    elif fallos:
        avisos.append(f"buscador: {len(fallos)} fichas no salen por su título: {fallos[:10]}")
    for q, esperadas in CONSULTAS:
        r = B.buscar(q, n=1)
        got = r[0][1]["area"] if r else None
        if got not in esperadas:
            avisos.append(f"consulta «{q}» → {got} (esperado {'/'.join(sorted(esperadas))})")
    for al, esperada in DISPAROS:
        r = B.por_disparador(alerta=al)
        if not r or r[0]["area"] != esperada:
            errores.append(f"alerta {al} → {r[0]['id'] if r else None} (esperado {esperada})")
    # reserva: una setter no ve fichas de dirección ni de personas que no sean suyas
    fuga = [f["id"] for _, f in B.buscar("salida de una persona del equipo despido", puesto="setters", n=10)
            if f["area"] in B.RESERVADAS and "setters" not in f.get("puestos", [])]
    fuga += [f["id"] for f in B.por_disparador(tipo="dir_decision", puesto="setters")
             if f["area"] in B.RESERVADAS and "setters" not in f.get("puestos", [])]
    if fuga:
        errores.append(f"reserva: fichas reservadas visibles para setters: {fuga[:5]}")
    print(f"{len(cb)} cerebros · {total} situaciones · {len(ix['tipo'])}/{len(tipos)} tipos cubiertos · "
          f"{len(ix['alerta'])}/{len(alertas)} alertas · {len(ix['indicador'])} indicadores")
    for a in avisos:
        print("  aviso:", a)
    for e in errores:
        print("  ERROR:", e)
    malo = errores or (estricto and avisos)
    print("FALLA" if malo else "OK", f"({len(errores)} errores, {len(avisos)} avisos)")
    return 0 if not malo else 1


if __name__ == "__main__":
    sys.exit(correr("--estricto" in sys.argv))

#!/usr/bin/env python3
"""migracion/revisar_plan.py · comprueba que migracion/PLAN_NOCHE.md cubre la noche entera, con la forma que espera el ejecutor.

    python3 migracion/revisar_plan.py              # dice qué falta; sale 1 si falta algo
    python3 migracion/revisar_plan.py --faltan     # solo los códigos que faltan, en orden, en una línea (lo usa planear.sh)
    python3 migracion/revisar_plan.py --seccion F2.3          # la sección de un paso, entera (la lee el ejecutor)
    python3 migracion/revisar_plan.py --seccion F5.10 L-03    # la de un fallo de F5.10

Lo que mira (sin modelos: es una comprobación mecánica, la de fondo la hacen las auditorías):
  · la primera línea empieza por «PLAN: »;
  · antes de los pasos, «## A0 · Análisis…» con sus cinco apartados, largo de verdad, y nombrando todo lo del 4-oct
    que tiene que entrar (Tomás, 4-oct: «que al inicio se dedique mucho tiempo a analizar lo que realmente queremos»);
  · cada paso de PROGRESO.md (F1.1 … F7.4) tiene su sección «## <código> · …»;
  · cada sección de paso tiene «Hecho cuando:» y «Plan B:» (el ejecutor no improvisa ni el cierre ni la salida);
  · en F5.10, cada fallo «abierto» de PENDIENTES_LOGICA.md tiene su «### <id> · …» (manda el estado de la copia de
    ~/RO_MIGRACION/PENDIENTES_LOGICA.md si existe, como en la noche);
  · nada que parezca una llave o un correo real.
"""
import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLAN = os.path.join(RAIZ, "migracion", "PLAN_NOCHE.md")
PROGRESO = os.path.join(RAIZ, "migracion", "PROGRESO.md")
PENDIENTES = os.path.join(RAIZ, "migracion", "PENDIENTES_LOGICA.md")
FUERA = os.environ.get("RO_MIGRACION") or os.path.expanduser("~/RO_MIGRACION")

# Una conexión con contraseña cuenta como llave salvo la del Postgres local de la noche (127.0.0.1/localhost/postgres).
LLAVES = re.compile(r"(sk-[A-Za-z0-9_-]{16,}|ghp_[A-Za-z0-9]{20,}|github_pat_|AKIA[0-9A-Z]{16}|xox[bap]-|-----BEGIN [A-Z ]*PRIVATE KEY"
                    r"|postgres(?:ql)?://[^:\s/]+:[^@\s<{$]+@(?!127\.0\.0\.1|localhost|postgres[:/]))")
# Correo: el dominio acaba en letras (así «shadcn@2.3.0», «prisma@7.10.0» o «ro@127.0.0.1» no cuentan).
CORREO = re.compile(r"(?<![\w/.+-])[\w.+-]+@[\w-]+(?:\.[\w-]+)*\.[A-Za-z]{2,}\b")
CORREO_FALSO = re.compile(r"(?:^git@github\.com$|@(?:[\w-]+\.)*(?:test|example|invalid|localhost)$|@ejemplo\.\w+$|@example\.\w+$|@users\.noreply\.github\.com$)", re.I)


# El análisis (A0): qué apartados lleva y qué tiene que nombrar sí o sí (lo trabajado el 4-oct).
APARTADOS_A0 = ("Qué queremos", "Lo que ya hay", "Todo lo del 4-oct que entra", "Riesgos y dudas", "Cómo sabremos que salió bien")
NOMBRA_A0 = ("PR #2", "PR #3", "PR #4", "contexto del cliente", "PENDIENTES_LOGICA", "L-01", "N-01", "MCP", "Supabase",
             "copias", "permisos", "entrega", "INTEGRAR.md", "Opus", "Grok")
LARGO_A0 = 6000   # caracteres: un resumen de diez líneas no es un análisis


def leer(ruta):
    with open(ruta, encoding="utf-8") as f:
        return f.read()


def pasos():
    return re.findall(r"^- \S+ (F\d+\.\d+)\b", leer(PROGRESO), re.M)


def estados(ruta):
    """id → estado (última columna de la tabla)."""
    if not os.path.exists(ruta):
        return {}
    salida = {}
    for linea in leer(ruta).splitlines():
        m = re.match(r"^\|\s*((?:L|N)-\d+)\s*\|", linea)
        if m:
            celdas = [c.strip() for c in linea.strip().strip("|").split("|")]
            salida[m.group(1)] = celdas[-1].lower() if celdas else ""
    return salida


def abiertos():
    juntos = estados(PENDIENTES)
    juntos.update(estados(os.path.join(FUERA, "PENDIENTES_LOGICA.md")))   # la de Tomás manda, como en la noche
    return [i for i, e in juntos.items() if e.startswith("abierto")]


def secciones(texto, nivel):
    """código → cuerpo de la sección (hasta la siguiente cabecera del mismo nivel o de uno más alto)."""
    marca = "#" * nivel
    partes = {}
    actual, cuerpo, en_codigo = None, [], False
    for linea in texto.splitlines():
        if linea.lstrip().startswith("```"):
            en_codigo = not en_codigo
        m = None if en_codigo else re.match(r"^(#{1,%d}) (\S+)" % nivel, linea)
        if m:
            if actual:
                partes[actual] = "\n".join(cuerpo)
            actual = m.group(2) if m.group(1) == marca else None
            cuerpo = []
        elif actual:
            cuerpo.append(linea)
    if actual:
        partes[actual] = "\n".join(cuerpo)
    return partes


def revisar():
    if not os.path.exists(PLAN):
        return ["no existe migracion/PLAN_NOCHE.md"], ["A0"] + pasos()
    texto = leer(PLAN)
    fallos, faltan = [], []
    if not texto.startswith("PLAN: "):
        fallos.append("la primera línea no empieza por «PLAN: »")
    de_paso = secciones(texto, 2)
    analisis = de_paso.get("A0")
    if analisis is None:
        faltan.append("A0")
    else:
        if len(analisis) < LARGO_A0:
            fallos.append(f"A0: el análisis es corto ({len(analisis)} caracteres; al menos {LARGO_A0})")
        apartados = secciones(analisis, 3)
        titulos = [k.lower() for k in re.findall(r"^### (.+)$", analisis, re.M)]
        for a in APARTADOS_A0:
            if not any(t.startswith(a.lower()) for t in titulos):
                fallos.append(f"A0: falta el apartado «### {a}»")
        for n in NOMBRA_A0:
            if n.lower() not in analisis.lower():
                fallos.append(f"A0: no nombra «{n}» (todo lo del 4-oct tiene que estar en el análisis)")
        if texto.find("\n## A0") > min([texto.find(f"\n## {c} ") for c in pasos() if texto.find(f"\n## {c} ") >= 0] or [len(texto)]):
            fallos.append("A0: el análisis va ANTES de los pasos")
    for codigo in pasos():
        cuerpo = de_paso.get(codigo)
        if cuerpo is None:
            faltan.append(codigo)
        else:
            for campo in ("Hecho cuando:", "Plan B:"):
                if campo not in cuerpo:
                    fallos.append(f"{codigo}: falta «{campo}»")
        if codigo == "F5.10":   # sus fallos van DENTRO de F5.10, justo después de él en la lista
            de_fallo = secciones(cuerpo or "", 3)
            faltan += [i for i in abiertos() if i not in de_fallo]
    for n, linea in enumerate(texto.splitlines(), 1):
        if LLAVES.search(linea):
            fallos.append(f"línea {n}: parece una llave o una conexión con contraseña")
        for correo in CORREO.findall(linea):
            if not CORREO_FALSO.search(correo):
                fallos.append(f"línea {n}: correo que parece real ({correo.split('@')[1]}); usa @ejemplo.test")
    return fallos, faltan


def main():
    if "--seccion" in sys.argv:
        resto = sys.argv[sys.argv.index("--seccion") + 1:]
        if not resto or not os.path.exists(PLAN):
            print("✘ uso: --seccion <paso> [id], con migracion/PLAN_NOCHE.md escrito")
            return 1
        cuerpo = secciones(leer(PLAN), 2).get(resto[0])
        if cuerpo is not None and len(resto) > 1:
            cuerpo = secciones(cuerpo, 3).get(resto[1])
        if cuerpo is None:
            print(f"✘ PLAN_NOCHE.md no tiene sección para {' '.join(resto)}: sigue PROMPTS_CURSOR.md y apúntalo en NOTAS_NOCHE.md")
            return 1
        print(f"{'#' * (1 + len(resto))} {' '.join(resto)}\n" + cuerpo.strip("\n"))
        return 0
    fallos, faltan = revisar()
    if "--faltan" in sys.argv:
        print(" ".join(faltan))
        return 0
    for f in fallos:
        print("✘", f)
    if faltan:
        print("✘ faltan secciones:", " ".join(faltan))
    if not fallos and not faltan:
        print(f"✔ PLAN_NOCHE.md cubre los {len(pasos())} pasos y los {len(abiertos())} fallos abiertos")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())

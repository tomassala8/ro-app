#!/usr/bin/env python3
"""
escalado.py · orden de escalado oficial de Ranking Online (encargo de Tomás, 3-oct-2026).

La cadena vive en UN solo sitio: data/escalado.json (ids de persona de data/personas.json). Este módulo la lee y la
aplica; lo usan:
  · avisos.py      → botón «Pedir ayuda / Escalar» (mensaje directo en el chat de la app con el contexto) y «Pasar a Tomás».
  · fuentes_alertas/generar_alertas.py → escalado por plazo: dueño → responsable del área → Mili → Tomás.
  · avisos_programados.py → a quién sube un recordatorio que nadie hace (el responsable de la persona).
  · ia.py          → el texto que la IA sigue cuando dice «avisa a…».

Orden (Tomás, literal en lo esencial):
  · Duda de estrategia del área        → responsable de su área: el jefe del departamento de su puesto
                                          (data/departamentos.json, «area_de_puesto»); si es ella misma o su puesto no
                                          tiene área, su jefe de personas.json; si no, Mili.
  · Duda transversal de cliente        → Coti.
  · Problema de operaciones            → Mili.
  · Problema de sistemas/herramientas  → Agus.
  · Algo que nadie está pudiendo resolver → primero Mili; si Mili no encuentra quién lo solucione → Tomás.
Nunca se salta directo a Tomás, salvo lo que ya va a dirección por norma (dinero y RRHH).

Sin dependencias del servidor: personas = lista de data/personas.json (o la que pase quien llama).
  python3 escalado.py            → enseña a quién va cada tipo para cada persona activa (prueba rápida)
"""
import json
import os
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RUTA = Path(os.environ.get("RO_ESCALADO") or AQUI / "data" / "escalado.json")
_CACHE = {"mt": None, "doc": None}

# Si el fichero faltara o viniera roto, la app no se queda sin cadena: la de Tomás del 3-oct.
POR_DEFECTO = {
    "personas": {"cliente_transversal": "constanza", "operaciones": "mili", "sistemas": "agustina", "atascado": "mili", "final": "tomas"},
    "tipos": [
        {"id": "estrategia", "texto": "Duda de estrategia de mi área", "corto": "Estrategia de mi área", "a": "area", "por_que": "Las dudas de estrategia del área las resuelve el responsable de tu área."},
        {"id": "cliente", "texto": "Duda de un cliente que toca a varias áreas", "corto": "Duda de cliente", "a": "cliente_transversal", "por_que": "Las dudas transversales de cliente las lleva Coti."},
        {"id": "operaciones", "texto": "Problema de operaciones", "corto": "Operaciones", "a": "operaciones", "por_que": "Los problemas de operaciones los lleva Mili."},
        {"id": "sistemas", "texto": "Problema de sistemas o herramientas", "corto": "Sistemas y herramientas", "a": "sistemas", "por_que": "Los problemas de sistemas y herramientas los lleva Agus."},
        {"id": "atascado", "texto": "Algo que nadie está pudiendo resolver", "corto": "Nadie lo resuelve", "a": "atascado", "si_no": "final", "por_que": "Si nadie lo está pudiendo resolver, primero Mili; si Mili no encuentra quién lo solucione, Tomás."},
    ],
    "si_eres_tu": ["atascado", "final"],
    "cadena_alertas": ["dueno", "jefe", "atascado", "final"],
    "directo_a_direccion": {"departamentos": ["administracion", "rrhh", "direccion"]},
}


def config():
    """data/escalado.json con caché por fecha de cambio (se puede cambiar en caliente)."""
    try:
        mt = RUTA.stat().st_mtime
    except OSError:
        return POR_DEFECTO
    if _CACHE["mt"] != mt:
        try:
            doc = json.loads(RUTA.read_text())
            if not isinstance(doc.get("personas"), dict) or not isinstance(doc.get("tipos"), list):
                raise ValueError("sin personas o tipos")
            _CACHE.update(mt=mt, doc=doc)
        except (OSError, ValueError):
            return _CACHE["doc"] or POR_DEFECTO
    return _CACHE["doc"]


def _personas_por_id(personas):
    if personas is None:
        try:
            personas = json.loads((AQUI / "data" / "personas.json").read_text())
        except (OSError, ValueError):
            personas = []
    if personas is None or isinstance(personas, (str, bytes, dict)) or not hasattr(personas, "__iter__"):
        return {}
    filas = [p for p in personas if isinstance(p, dict) and isinstance(p.get("id"), str) and p.get("id")]
    cuenta = {}
    for p in filas:
        cuenta[p["id"]] = cuenta.get(p["id"], 0) + 1
    return {p["id"]: p for p in filas if cuenta[p["id"]] == 1}


def activa(p):
    return isinstance(p, dict) and p.get("activo") is not False and p.get("estado") == "activo"


def papel(nombre, personas=None):
    """Id de la persona que ocupa un papel de la cadena («operaciones», «sistemas», «final»…)."""
    pid = (config().get("personas") or {}).get(nombre) or POR_DEFECTO["personas"].get(nombre)
    per = _personas_por_id(personas)
    if not activa(per.get(pid)):
        return None
    # El último escalón de la política es Tomás autorizado, no cualquier dirección.
    if nombre == "final" and (pid != "tomas" or "direccion" not in (per[pid].get("puestos") or [])):
        return None
    return pid


def jefe_de(pid, personas=None):
    """Responsable del área de una persona: su «jefe» de personas.json si está activo; si no, Mili (operaciones)."""
    per = _personas_por_id(personas)
    if not activa(per.get(pid)):
        return None
    j = (per.get(pid) or {}).get("jefe")
    if j and j != pid and activa(per.get(j)) and (j != "tomas" or papel("final", per.values()) == "tomas"):
        return j
    atascado = papel("atascado", per.values())
    return atascado if atascado and pid != atascado else papel("final", per.values()) if pid == atascado else None


AREA_POR_DEFECTO = {"jefa_seo": "seo", "seo": "seo", "ficha_google": "seo", "web": "web", "account": "accounts", "tecnico_altas": "altas",
                    "jefa_publicidad": "publicidad", "trafficker": "publicidad", "jefa_crm": "crm", "especialista_ghl": "crm",
                    "outreach": "crm", "redes": "redes", "administracion": "administracion", "rrhh": "rrhh"}


def _departamentos():
    ruta = Path(os.environ.get("RO_DEPARTAMENTOS") or AQUI / "data" / "departamentos.json")
    try:
        return json.loads(ruta.read_text()).get("departamentos") or {}
    except (OSError, ValueError):
        return {}


def area_de(pid, personas=None):
    """Departamento del área de una persona (primer puesto que tenga área) o None."""
    per = _personas_por_id(personas)
    mapa = {k: v for k, v in (config().get("area_de_puesto") or AREA_POR_DEFECTO).items() if not k.startswith("_")}
    for pu in (per.get(pid) or {}).get("puestos") or []:
        if pu in mapa:
            return mapa[pu]
    return None


def responsable_area(pid, personas=None):
    """Responsable del área: el jefe del departamento de su puesto (Ajustes › Departamentos). Si es ella misma, si su
    puesto no tiene área o ese jefe no está activo → su jefe de personas.json (y si no, Mili)."""
    per = _personas_por_id(personas)
    if not activa(per.get(pid)):
        return None
    dep = area_de(pid, per.values())
    j = (_departamentos().get(dep) or {}).get("jefe") if dep else None
    if j and j != pid and activa(per.get(j)) and (j != "tomas" or papel("final", per.values()) == "tomas"):
        return j
    return jefe_de(pid, per.values())


def tipos():
    return [dict(t) for t in config().get("tipos") or POR_DEFECTO["tipos"]]


def tipo(tid):
    return next((t for t in tipos() if t.get("id") == tid), None)


def _resolver(destino, pid, personas):
    if destino == "area":
        return responsable_area(pid, personas)
    if destino == "jefe":
        return jefe_de(pid, personas)
    return papel(destino, personas)


def a_quien(tid, pid, personas=None):
    """A quién va una petición de ayuda de tipo «tid» que hace «pid».
    → {"para": id, "siguiente": id | None, "tipo": {...}, "por_que": texto} o None si el tipo no existe.
    Si la persona que toca es quien pregunta (Mili con un problema de operaciones, Agus con uno de sistemas, Coti con un
    cliente…), sube por «si_eres_tu» (Mili y luego Tomás) saltándose a sí misma."""
    t = tipo(tid)
    if not t:
        return None
    per = _personas_por_id(personas)
    if not activa(per.get(pid)):
        return None
    para = _resolver(t.get("a"), pid, per.values())
    por_que = t.get("por_que") or ""
    if not para or para == pid or not activa(per.get(para)):
        for paso in config().get("si_eres_tu") or POR_DEFECTO["si_eres_tu"]:
            x = papel(paso, per.values())
            # No convertir una ausencia de Mili en un salto directo a dirección.
            if paso == "final" and pid != papel("atascado", per.values()):
                continue
            if x and x != pid and activa(per.get(x)):
                antes = para
                para = x
                por_que = (f"{por_que} Como eso eres tú, sube a quien sigue en la cadena." if antes == pid
                           else f"{por_que} Esa persona no está activa: sube a quien sigue en la cadena.").strip()
                break
    if not para or para == pid or not activa(per.get(para)):
        return None
    siguiente = papel(t["si_no"], per.values()) if t.get("si_no") else None
    if siguiente in (para, pid):
        siguiente = None
    return {"para": para, "siguiente": siguiente, "tipo": t, "por_que": por_que}


def cadena_alertas(departamento, dueno, jefe_departamento, personas=None):
    """Escalado por plazo de una alerta: dueño → responsable del área → Mili → Tomás (sin repetir a nadie).
    Lo de dirección por norma (dinero, RRHH: su responsable ya es Tomás) queda dueño → Tomás."""
    cfg = config()
    per = _personas_por_id(personas)
    if not activa(per.get(dueno)):
        return []
    direccion = set((cfg.get("directo_a_direccion") or {}).get("departamentos") or [])
    pasos = cfg.get("cadena_alertas") or POR_DEFECTO["cadena_alertas"]
    out = []
    for paso in pasos:
        x = dueno if paso == "dueno" else jefe_departamento if paso == "jefe" else papel(paso, per.values())
        if not activa(per.get(x)):
            continue
        if x == "tomas" and papel("final", per.values()) != "tomas":
            continue
        if paso == "final" and departamento not in direccion and papel("atascado", per.values()) not in out:
            continue
        if x and x not in out:
            out.append(x)
        if departamento in direccion and x == papel("final", per.values()):
            break                       # dinero y RRHH acaban en Tomás: no bajan a Mili después
    return out


def texto_para_ia(personas=None):
    """Lo que la IA tiene que seguir cuando dice a quién avisar (con nombres)."""
    per = _personas_por_id(personas)
    nom = lambda i: ((per.get(i) or {}).get("alias") or (per.get(i) or {}).get("nombre") or i)
    l = ["Orden de escalado oficial de RO (úsalo SIEMPRE que digas a quién avisar o a quién escalar):"]
    for t in tipos():
        if t.get("a") in ("jefe", "area"):
            deps = _departamentos()
            areas = [f"{d.get('nombre') or k}, {nom(d.get('jefe'))}" for k, d in deps.items()
                     if activa(per.get(d.get("jefe"))) and k in set((config().get("area_de_puesto") or AREA_POR_DEFECTO).values())]
            l.append(f"- {t['texto']}: al responsable de su área (el jefe de su departamento" + (f": {'; '.join(areas)}" if areas else "") + ").")
        elif t.get("si_no"):
            l.append(f"- {t['texto']}: primero {nom(papel(t['a'], per.values()))}; si {nom(papel(t['a'], per.values()))} no encuentra quién lo solucione, {nom(papel(t['si_no'], per.values()))}.")
        else:
            l.append(f"- {t['texto']}: {nom(papel(t['a'], per.values()))}.")
    l.append(f"- Nunca saltes directo a {nom(papel('final', per.values())) or 'dirección por confirmar'}, salvo dinero, precios, descuentos, pausas, bajas y RRHH, que van a dirección por norma.")
    return "\n".join(l)


def resumen(personas=None):
    """Para la pantalla: los tipos con a quién va (para quien mira lo decide a_quien)."""
    per = _personas_por_id(personas)
    nom = lambda i: ((per.get(i) or {}).get("alias") or i)
    return [{"id": t["id"], "texto": t["texto"], "corto": t.get("corto") or t["texto"], "por_que": t.get("por_que"),
             "a": t.get("a"), "a_nombre": None if t.get("a") in ("jefe", "area") else nom(papel(t["a"], per.values())),
             "si_no_nombre": nom(papel(t["si_no"], per.values())) if t.get("si_no") else None} for t in tipos()]


if __name__ == "__main__":
    per = _personas_por_id(None)
    for p in per.values():
        if not activa(p):
            continue
        fila = [f"{t['id']}→{(a_quien(t['id'], p['id']) or {}).get('para')}" for t in tipos()]
        print(f"{p['id']:<20} " + "  ".join(fila))
    print()
    print(texto_para_ia())

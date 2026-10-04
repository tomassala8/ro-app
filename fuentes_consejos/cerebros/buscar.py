#!/usr/bin/env python3
"""fuentes_consejos/cerebros/buscar.py · buscador de los CEREBROS DE ÁREA (4-oct-2026). Sin IA.

Doce cerebros (uno por área) con fichas de situación: síntoma, diagnóstico en orden, causas con su solución, guiones
en la voz de RO, qué no hacer, cuándo escalar y cómo se sabe que está resuelto. Cada afirmación lleva su fuente.

La app localiza la ficha SIN IA (por tipo de consejo, por alerta, por indicador o por texto libre) y, si hay clave,
le pasa a la IA SOLO esa ficha compacta (≈ 500-1.500 tokens) más los datos del cliente para que la adapte. Sin clave,
la ficha se enseña tal cual y ya sirve.

  import buscar as B
  B.por_disparador(tipo="diag_asistencia")          → [ficha, ...]
  B.por_disparador(alerta="crm_sin_tocar")
  B.por_disparador(indicador="setters.asistencia")
  B.buscar("los leads no se presentan a la reunión", puesto="setters")  → [(puntos, ficha), ...]
  B.ficha("crm_no_shows_altos")                      → ficha completa
  B.para_ia(ficha)                                   → dict compacto para el prompt

  python3 fuentes_consejos/cerebros/buscar.py "no vienen a las citas" [--puesto setters] [--n 3] [--ia]
"""
import json
import math
import re
import sys
import unicodedata
from functools import lru_cache
from pathlib import Path

AQUI = Path(__file__).resolve().parent
AREAS = ["direccion", "operaciones", "account", "comunicacion", "altas", "publicidad", "crm", "setters", "seo_web",
         "redes_produccion", "ventas_ro", "personas_admin"]

VACIAS = set("""a al algo ante antes con como cual cuando de del desde donde el ella ellos en entre es esa ese eso esta
este esto estan esta fue ha han hay la las le les lo los mas me mi mis muy no nos o para pero por que se sea ser si sin
sobre su sus tambien te tiene tienen todo un una uno unos unas y ya yo hace hacer qué cómo""".split())


def normal(t):
    t = unicodedata.normalize("NFKD", str(t).lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9 ]+", " ", t).strip()


def raiz(p):
    """Raíz pobre pero estable: quita plurales y algunas terminaciones verbales frecuentes."""
    for suf in ("aciones", "acion", "amente", "ando", "iendo", "ados", "idas", "idos", "adas", "ada", "ado", "ida", "ido",
                "es", "s"):
        if len(p) > len(suf) + 3 and p.endswith(suf):
            return p[: -len(suf)]
    return p


def fichas_de(texto):
    return [raiz(p) for p in normal(texto).split() if p not in VACIAS and len(p) > 1]


@lru_cache(maxsize=1)
def cerebros():
    """{area: cerebro} con los ficheros que existan."""
    out = {}
    for a in AREAS:
        f = AQUI / f"{a}.json"
        if f.exists():
            out[a] = json.loads(f.read_text(encoding="utf-8"))
    return out


@lru_cache(maxsize=1)
def indice():
    """Usa indice.json si está y es más nuevo que los cerebros; si no, lo construye en memoria."""
    f = AQUI / "indice.json"
    fuentes = [AQUI / f"{a}.json" for a in AREAS if (AQUI / f"{a}.json").exists()]
    if f.exists() and all(f.stat().st_mtime >= x.stat().st_mtime for x in fuentes):
        return json.loads(f.read_text(encoding="utf-8"))
    return construir()


def construir():
    sit, tipo, alerta, indic, regla, frases, docs = {}, {}, {}, {}, {}, {}, {}
    for area, c in cerebros().items():
        for s in c.get("situaciones", []):
            sid = s["id"]
            sit[sid] = {"area": area, "titulo": s.get("titulo", ""), "puestos": s.get("puestos", []),
                        "gravedad": s.get("gravedad", "")}
            d = s.get("disparadores", {})
            for k, dest in (("tipos_consejo", tipo), ("alertas", alerta), ("indicadores", indic)):
                for x in d.get(k, []) or []:
                    dest.setdefault(x, []).append(sid)
            for r in s.get("reglas_relacionadas", []) or []:
                regla.setdefault(r, []).append(sid)
            for p in d.get("palabras_clave", []) or []:
                n = normal(p)
                if n:
                    frases.setdefault(n, []).append(sid)
            # bolsa de palabras con pesos: palabras clave x3, título x2, síntoma x1
            bolsa = {}
            for texto, peso in ((" ".join(d.get("palabras_clave", []) or []), 3), (s.get("titulo", ""), 2),
                                (s.get("sintoma", ""), 1)):
                for t in fichas_de(texto):
                    bolsa[t] = bolsa.get(t, 0) + peso
            docs[sid] = bolsa
    df = {}
    for b in docs.values():
        for t in b:
            df[t] = df.get(t, 0) + 1
    n = max(1, len(docs))
    idf = {t: round(math.log(1 + n / v), 4) for t, v in df.items()}
    return {"situaciones": sit, "tipo": tipo, "alerta": alerta, "indicador": indic, "regla": regla, "frases": frases,
            "docs": docs, "idf": idf}


def ficha(sid):
    ix = indice()
    meta = ix["situaciones"].get(sid)
    if not meta:
        return None
    for s in cerebros().get(meta["area"], {}).get("situaciones", []):
        if s["id"] == sid:
            return dict(s, area=meta["area"])
    return None


def principios(area):
    return cerebros().get(area, {}).get("principios", [])


ORDEN_GRAVEDAD = {"alta": 0, "media": 1, "baja": 2}


def por_disparador(tipo=None, alerta=None, indicador=None, regla=None, puesto=None):
    ix = indice()
    ids = []
    for clave, valor in (("tipo", tipo), ("alerta", alerta), ("indicador", indicador), ("regla", regla)):
        if valor:
            ids += [i for i in ix[clave].get(valor, []) if i not in ids]
    out = [ficha(i) for i in ids]
    out = [f for f in out if f]
    if puesto:  # las del puesto primero, sin quitar las demás
        out.sort(key=lambda f: (puesto not in f.get("puestos", []), ORDEN_GRAVEDAD.get(f.get("gravedad"), 3)))
    else:
        out.sort(key=lambda f: ORDEN_GRAVEDAD.get(f.get("gravedad"), 3))
    return out


def buscar(texto, puesto=None, area=None, n=3, minimo=1.0):
    """Texto libre del equipo → [(puntos, ficha)], mejores primero. Frase exacta de palabra clave pesa más."""
    ix = indice()
    q = normal(texto)
    qt = set(fichas_de(texto))
    puntos = {}
    for frase, ids in ix["frases"].items():
        if frase and (f" {frase} " in f" {q} "):
            for i in ids:
                puntos[i] = puntos.get(i, 0) + 4 + len(frase.split())
    for sid, bolsa in ix["docs"].items():
        s = sum(bolsa[t] * ix["idf"].get(t, 0) for t in qt if t in bolsa)
        if s:
            puntos[sid] = puntos.get(sid, 0) + s
    res = []
    for sid, p in puntos.items():
        meta = ix["situaciones"][sid]
        if area and meta["area"] != area:
            continue
        if puesto and puesto in meta.get("puestos", []):
            p *= 1.25
        if p >= minimo:
            res.append((round(p, 2), sid))
    res.sort(key=lambda x: -x[0])
    return [(p, ficha(sid)) for p, sid in res[:n]]


def para_ia(f, con_guiones=True, max_causas=6):
    """Ficha → dict compacto para el prompt: sin notas de fuentes ni campos vacíos. La IA solo adapta esto."""
    if not f:
        return None
    out = {
        "situacion": f.get("titulo"), "area": f.get("area"), "sintoma": f.get("sintoma"),
        "gravedad": f.get("gravedad"), "plazo": f.get("plazo"),
        "diagnostico": [f"{d.get('paso')}. {d.get('comprueba')} ({d.get('donde')}) → si falla: {d.get('si_falla')}"
                        for d in f.get("diagnostico", [])],
        "causas": [{"id": c.get("id"), "causa": c.get("causa"), "confirmar": c.get("como_confirmar"),
                    "solucion": c.get("solucion"), "quien": c.get("quien")} for c in f.get("causas", [])[:max_causas]],
        "hoy": f.get("acciones_inmediatas"),
        "no_hacer": f.get("que_no_hacer"),
        "escalar": f.get("escalar"),
        "exito": f.get("exito"),
        "fuentes": [f"{x.get('fichero')}" + (f":{x.get('linea')}" if x.get("linea") else "") for x in f.get("fuentes", [])],
    }
    if con_guiones:
        out["guiones"] = f.get("guiones")
    return {k: v for k, v in out.items() if v}


def tokens_aprox(o):
    return len(json.dumps(o, ensure_ascii=False)) // 4


def _main(argv):
    import argparse
    ap = argparse.ArgumentParser(description="Busca la ficha de situación sin IA")
    ap.add_argument("texto", nargs="*")
    ap.add_argument("--puesto")
    ap.add_argument("--area")
    ap.add_argument("--tipo")
    ap.add_argument("--alerta")
    ap.add_argument("--indicador")
    ap.add_argument("--n", type=int, default=3)
    ap.add_argument("--ia", action="store_true", help="muestra el dict compacto que iría a la IA")
    a = ap.parse_args(argv)
    if a.tipo or a.alerta or a.indicador:
        res = [(None, f) for f in por_disparador(a.tipo, a.alerta, a.indicador, puesto=a.puesto)][: a.n]
    else:
        res = buscar(" ".join(a.texto), puesto=a.puesto, area=a.area, n=a.n)
    if not res:
        print("Sin ficha. Pregunta a tu responsable o reformula con otras palabras.")
        return 1
    for p, f in res:
        print(f"[{f['area']}] {f['id']} · {f['titulo']}" + (f"  ({p})" if p is not None else ""))
    if a.ia:
        c = para_ia(res[0][1])
        print(json.dumps(c, ensure_ascii=False, indent=1))
        print(f"≈ {tokens_aprox(c)} tokens")
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))

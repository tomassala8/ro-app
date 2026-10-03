"""Utilidades compartidas por los generadores de M20/M21/M22 (prefijo de este agente)."""
import json, re, unicodedata
from pathlib import Path

APP = Path(__file__).resolve().parent.parent
DATA = APP / "data"
import sys as _sys  # C5: rutas en config.py
_sys.path.insert(1, str(APP))
import config  # noqa: E402
BUILD = config.PANEL_BUILD


def norm(s):
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"\(.*?\)", "", s).strip()


def personas():
    return json.loads((DATA / "personas.json").read_text())


def emparejador():
    """nombre del panel/ClickUp → id de persona de la app."""
    idx = {}
    for p in personas():
        for n in [p["nombre"], p.get("alias")] + list(p.get("alias_todos") or []):
            if n:
                idx.setdefault(norm(n), p["id"])
        idx.setdefault(norm(p["nombre"]).split()[0], p["id"])
    def buscar(nombre):
        n = norm(nombre)
        if n in idx:
            return idx[n]
        if n.split() and n.split()[0] in idx:
            return idx[n.split()[0]]
        return None
    return buscar


def escribir(rel, obj):
    f = DATA / rel
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_suffix(".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=1))
    tmp.replace(f)
    return f

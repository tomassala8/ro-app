#!/usr/bin/env python3
"""
foto_diaria.py · historia de la app (E0 punto 6; M9 de la Torre: historia a 7, 30 y 90 días).

Copia cada día lo que generan build_data.py y E1 en historia/AAAA-MM-DD/ y escribe «cambios.json»:
lo que ha cambiado desde la última foto (salud, semáforo y responsable de cada cliente; alarmas nuevas y
cerradas; estado de cada fuente). Así «lo que ha cambiado desde ayer» y las series a 7/30/90 días tienen
de dónde salir aunque la fase 2 empiece más tarde.

  - Copia: data/*.json (salvo logos.json, que no cambia y pesa) y data/clientes/*.json.
  - NUNCA copia carpetas _privado/ (datos completos de leads): la historia no guarda datos personales.
  - Si ya hay foto de hoy, la rehace (la última del día manda). Las de días anteriores no se tocan.
  - Solo lectura de data/; escribe solo en historia/.

Uso: python3 foto_diaria.py [--fecha AAAA-MM-DD]
servir.py la lanza sola al arrancar si hoy aún no hay foto.
"""
import json
import shutil
import sys
from datetime import date
from pathlib import Path

AQUI = Path(__file__).resolve().parent
DATA = AQUI / "data"
HISTORIA = AQUI / "historia"
NO_COPIAR = {"logos.json"}


def _leer(p):
    try:
        return json.loads(p.read_text())
    except Exception:
        return None


def _resumen_clientes(carpeta):
    cl = _leer(carpeta / "clientes.json") or []
    return {c["id"]: {"nombre": c.get("nombre"), "salud": c.get("salud"), "semaforo": c.get("semaforo"),
                      "responsable_id": c.get("responsable_id"), "sin_account": c.get("sin_account")} for c in cl}


def _alarmas(carpeta):
    return {a["id"]: a for a in (_leer(carpeta / "alarmas.json") or [])}


def _fuentes(carpeta):
    f = _leer(carpeta / "fuentes.json")
    if isinstance(f, dict):
        f = f.get("fuentes", f)
    if isinstance(f, dict):
        return {k: (v.get("estado") if isinstance(v, dict) else v) for k, v in f.items()}
    if isinstance(f, list):
        return {x.get("fuente") or x.get("id"): x.get("estado") for x in f if isinstance(x, dict)}
    return {}


def comparar(antes, ahora):
    ca, cb = _resumen_clientes(antes), _resumen_clientes(ahora)
    clientes = []
    for cid, b in cb.items():
        a = ca.get(cid)
        if not a:
            clientes.append({"cliente_id": cid, "nombre": b["nombre"], "cambio": "nuevo en la app"})
            continue
        for campo in ("salud", "semaforo", "responsable_id", "sin_account"):
            if a.get(campo) != b.get(campo):
                clientes.append({"cliente_id": cid, "nombre": b["nombre"], "campo": campo, "antes": a.get(campo), "ahora": b.get(campo)})
    for cid in set(ca) - set(cb):
        clientes.append({"cliente_id": cid, "nombre": ca[cid]["nombre"], "cambio": "ya no está en la app"})
    aa, ab = _alarmas(antes), _alarmas(ahora)
    nuevas = [{"id": i, "cliente_id": ab[i].get("cliente_id"), "tipo": ab[i].get("tipo"), "gravedad": ab[i].get("gravedad")} for i in set(ab) - set(aa)]
    cerradas = [{"id": i, "cliente_id": aa[i].get("cliente_id"), "tipo": aa[i].get("tipo")} for i in set(aa) - set(ab)]
    fa, fb = _fuentes(antes), _fuentes(ahora)
    fuentes = [{"fuente": k, "antes": fa.get(k), "ahora": v} for k, v in fb.items() if fa.get(k) != v]
    return {"clientes": clientes, "alarmas_nuevas": nuevas, "alarmas_cerradas": cerradas, "fuentes": fuentes}


def hacer_foto(fecha=None):
    fecha = fecha or date.today().isoformat()
    destino = HISTORIA / fecha
    tmp = HISTORIA / f".{fecha}.tmp"
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True)
    copiados = 0
    for f in DATA.glob("*.json"):
        if f.name in NO_COPIAR or f.name.startswith("."):
            continue
        shutil.copy2(f, tmp / f.name)
        copiados += 1
    if (DATA / "clientes").exists():
        (tmp / "clientes").mkdir()
        for f in (DATA / "clientes").glob("*.json"):
            shutil.copy2(f, tmp / "clientes" / f.name)
            copiados += 1
    anteriores = sorted(p for p in HISTORIA.iterdir() if p.is_dir() and not p.name.startswith(".") and p.name < fecha)
    cambios = {"fecha": fecha, "comparado_con": anteriores[-1].name if anteriores else None}
    cambios.update(comparar(anteriores[-1], tmp) if anteriores else {"nota": "primera foto: no hay con qué comparar"})
    (tmp / "cambios.json").write_text(json.dumps(cambios, ensure_ascii=False, indent=1))
    if destino.exists():
        shutil.rmtree(destino)
    tmp.rename(destino)
    return {"fecha": fecha, "ficheros": copiados, "comparado_con": cambios["comparado_con"]}


def hay_foto_de_hoy():
    return (HISTORIA / date.today().isoformat()).exists()


if __name__ == "__main__":
    f = sys.argv[sys.argv.index("--fecha") + 1] if "--fecha" in sys.argv else None
    print(json.dumps(hacer_foto(f), ensure_ascii=False))

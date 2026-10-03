#!/usr/bin/env python3
"""fuentes_ia/precalcular.py · N3 (IA) · 2-oct-2026.

Hoy no hay clave de Anthropic. Para que la IA se vea funcionando, los borradores y el copiloto se generan una vez
FUERA de la app con exactamente el mismo contexto e instrucciones que usaría ia.py, y se guardan en
data/ia/_privado/ con fecha y el aviso «revisar antes de usar». La app los sirve con los mismos permisos que el
ticket o el cliente. Cuando haya clave, ia.py los genera al momento (y este script puede rehacerlos con --vivo).

  python3 fuentes_ia/precalcular.py --volcar <carpeta>    contexto de cada ticket y cliente (como lo vería su account)
  python3 fuentes_ia/precalcular.py --cargar <carpeta>    lee borradores.json y copiloto.json escritos a partir de ese
                                                          contexto, valida la forma y los deja en data/ia/_privado/
  python3 fuentes_ia/precalcular.py --vivo                con clave: los rehace todos llamando a Claude

Clientes del copiloto: los críticos de la verdad única + la cartera de Lucía. Tickets: los de hilos.json.
"""
import json
import os
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path

APP = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(APP))
_tmp = tempfile.mkdtemp()
if (APP / "local.db").exists():
    shutil.copy(APP / "local.db", Path(_tmp) / "local.db")
os.environ["RO_DB"] = str(Path(_tmp) / "local.db")      # no toca el rastro real
import servir as S  # noqa: E402
import ia as IA     # noqa: E402

IA.S = S
S.E.cargar()
PRIV = APP / "data/ia/_privado"
AVISO = "Propuesta del 2-oct (sin conexión a la IA). Revísala antes de usarla."


def persona(pid):
    return S.E.persona(pid) or S.E.persona("tomas")


def elegidos():
    hilos = json.loads((PRIV / "hilos.json").read_text())["hilos"]
    v = json.loads((APP / "data/verdad/clientes.json").read_text())["clientes"]
    clientes = [c["cliente_id"] for c in v if c.get("gravedad") == "critico"]
    clientes += [c["cliente_id"] for c in v if c.get("account") == "lucia" and c["cliente_id"] not in clientes]
    return hilos, clientes, {c["cliente_id"]: c for c in v}


def volcar(carpeta):
    carpeta = Path(carpeta); carpeta.mkdir(parents=True, exist_ok=True)
    hilos, clientes, ver = elegidos()
    out_b = {}
    for num, hh in hilos.items():
        acc = (ver.get(hh["cliente_id"]) or {}).get("account") or "tomas"
        p = persona(acc)
        ctx = IA.contexto_borrador(p, S.P.contexto(p, S.E.crudo), num)
        out_b[num] = {"firma_de": p["id"], "contexto": ctx}
    (carpeta / "ctx_borradores.json").write_text(json.dumps(out_b, ensure_ascii=False, indent=1))
    out_c = {}
    for cid in clientes:
        acc = (ver.get(cid) or {}).get("account") or "tomas"
        p = persona(acc)
        out_c[cid] = {"para": p["id"], "contexto": IA.contexto_copiloto(p, S.P.contexto(p, S.E.crudo), cid)}
    (carpeta / "ctx_copiloto.json").write_text(json.dumps(out_c, ensure_ascii=False, indent=1))
    print(len(out_b), "tickets ·", len(out_c), "clientes →", carpeta)


def validar_borrador(b):
    assert isinstance(b.get("asunto"), str) and isinstance(b.get("cuerpo"), str) and b["cuerpo"].strip()
    assert isinstance(b.get("puntos_del_cliente"), list) and isinstance(b.get("huecos"), list)
    for mala in ("¡", "no dudes en", "quedo a tu", "estimad", "atentamente", "cordialmente", "procederemos"):
        assert mala not in b["cuerpo"].lower(), f"tell prohibido «{mala}»"


def validar_copiloto(c, fuentes):
    assert c.get("color") in ("verde", "ambar", "rojo")
    assert len(c.get("diagnostico") or []) == 3
    assert len(c.get("acciones") or []) == 3
    for a in c["acciones"]:
        for k in ("que", "porque", "dato", "fuente", "quien", "cuando"):
            assert a.get(k), f"falta {k}"
        assert a["fuente"] == "verdad" or a["fuente"] in fuentes, f"fuente no válida «{a['fuente']}»"


def cargar(carpeta):
    carpeta = Path(carpeta)
    ctx_b = json.loads((carpeta / "ctx_borradores.json").read_text())
    ctx_c = json.loads((carpeta / "ctx_copiloto.json").read_text())
    bors = json.loads((carpeta / "borradores.json").read_text())
    cops = json.loads((carpeta / "copiloto.json").read_text())
    hoy = datetime.now().strftime("%Y-%m-%d %H:%M")
    sal_b = {}
    for num, b in bors.items():
        validar_borrador(b)
        x = ctx_b[num]
        sal_b[num] = {**b, "origen": "precalculado", "modelo": "Claude (sesión del 2-oct)", "generado": hoy, "aviso": AVISO,
                      "firma_de": x["firma_de"], "voz": "tomas" if x["firma_de"] == "tomas" else "ro",
                      "contexto_usado": {"hilo": x["contexto"]["hilo_disponible"], "mensajes": len(x["contexto"]["hilo"]), "verdad": bool(x["contexto"]["cliente_verdad_unica"])}}
    sal_c = {}
    for cid, c in cops.items():
        validar_copiloto(c, ctx_c[cid]["contexto"]["fuentes_validas_para_prueba"])
        sal_c[cid] = {**c, "origen": "precalculado", "modelo": "Claude (sesión del 2-oct)", "generado": hoy, "aviso": AVISO, "para": ctx_c[cid]["para"]}
    (PRIV / "borradores.json").write_text(json.dumps({"generado": hoy, "aviso": AVISO, "borradores": sal_b}, ensure_ascii=False, indent=1))
    (PRIV / "copiloto.json").write_text(json.dumps({"generado": hoy, "aviso": AVISO, "clientes": sal_c}, ensure_ascii=False, indent=1))
    print(len(sal_b), "borradores ·", len(sal_c), "copilotos →", PRIV)


def vivo():
    if not IA.estado()["conectada"]:
        sys.exit(IA.estado()["motivo"])
    hilos, clientes, ver = elegidos()
    tomas = persona("tomas"); cp = S.P.contexto(tomas, S.E.crudo)
    for num in hilos:
        r = IA.borrador(tomas, tomas, cp, num, nuevo=True); print(num, r.get("ok"), r.get("motivo") or "")
    for cid in clientes:
        r = IA.copiloto(tomas, tomas, cp, cid, nuevo=True); print(cid, r.get("ok"), r.get("motivo") or "")


if __name__ == "__main__":
    if "--volcar" in sys.argv:
        volcar(sys.argv[sys.argv.index("--volcar") + 1])
    elif "--cargar" in sys.argv:
        cargar(sys.argv[sys.argv.index("--cargar") + 1])
    elif "--vivo" in sys.argv:
        vivo()
    else:
        print(__doc__)

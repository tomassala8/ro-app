#!/usr/bin/env python3
"""
migracion/vectores_permisos.py · saca de permisos.py (el motor de HOY) la respuesta a cada pregunta de permisos,
para que el motor nuevo en TypeScript (v2/packages/permisos) tenga que dar EXACTAMENTE lo mismo.

  python3 migracion/vectores_permisos.py [--salida ~/RO_MIGRACION/vectores]

Necesita data/ y local.db (corre en el Mac, en la carpeta de la app). Escribe:
  permisos.json   por persona activa:
                    modulos      {modulo: nivel}            (nivel_modulo)
                    cartera      {silla: [clientes]}        (cartera_por_silla)
                    ver          {tipo|cliente|persona: {ok, nivel}}  para cada tipo de dato × (sin objeto, cada cliente, cada persona)
                    ver_como     lo mismo, pero Tomás viendo como esa persona (mínimo de las dos)
  recortes/<persona>.json   recortar(persona, crudo): lo que llega al navegador en /api/sesion
  crudo.json      la entrada (personas, asignaciones, clientes…) para que el motor nuevo calcule con lo mismo

⚠️ Son DATOS REALES. Fuera del repositorio siempre (por defecto ~/RO_MIGRACION/vectores).
"""
import argparse
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--salida", default="~/RO_MIGRACION/vectores")
    ap.add_argument("--sin-ver-como", action="store_true")
    a = ap.parse_args()
    salida = Path(a.salida).expanduser()
    (salida / "recortes").mkdir(parents=True, exist_ok=True)

    import permisos as P
    import servir as S
    S.E.cargar()
    crudo, modulos = S.E.crudo, S.E.modulos
    tipos = sorted(k for k in P.REGLAS["tipos"] if not k.startswith("_"))
    personas = [p for p in crudo["personas"] if p.get("estado") == "activo"]
    clientes = [c["id"] for c in crudo["clientes"]]
    ids_personas = [p["id"] for p in crudo["personas"]]
    tomas = next((p for p in personas if p["id"] == "tomas"), None)

    def preguntas(persona, cp):
        out = {}
        for t in tipos:
            out[f"{t}||"] = _res(P.ver(persona, {"tipo": t}, cp))
            for c in clientes:
                out[f"{t}|{c}|"] = _res(P.ver(persona, {"tipo": t, "cliente_id": c}, cp))
            for pid in ids_personas:
                out[f"{t}||{pid}"] = _res(P.ver(persona, {"tipo": t, "persona_id": pid}, cp))
        return out

    resultado = {"tipos": tipos, "clientes": clientes, "personas": ids_personas, "por_persona": {}}
    for p in personas:
        cp = P.contexto(p, crudo)
        fila = {
            "modulos": {m: P.nivel_modulo(p, mapa) for m, mapa in sorted(modulos.items())},
            "cartera": {s: sorted(v) for s, v in sorted(P.cartera_por_silla(p, crudo["asignaciones"]).items())},
            "ambito": P.ambito(p),
            "ver": preguntas(p, cp),
        }
        if tomas and not a.sin_ver_como and p["id"] != "tomas":
            with P.mirando_como(tomas, crudo):
                fila["ver_como"] = preguntas(p, cp)
                fila["modulos_ver_como"] = {m: P.nivel_modulo(p, mapa) for m, mapa in sorted(modulos.items())}
        resultado["por_persona"][p["id"]] = fila
        (salida / "recortes" / f"{p['id']}.json").write_text(
            json.dumps(P.recortar(p, crudo), ensure_ascii=False, sort_keys=True, indent=1, default=sorted))
        print(f"  {p['id']}: {len(fila['ver'])} preguntas")
    (salida / "permisos.json").write_text(json.dumps(resultado, ensure_ascii=False, sort_keys=True, default=sorted))
    (salida / "crudo.json").write_text(json.dumps(crudo, ensure_ascii=False, sort_keys=True, default=sorted))
    (salida / "modulos.json").write_text(json.dumps(modulos, ensure_ascii=False, sort_keys=True, default=sorted))
    print(f"Vectores en {salida} ({len(personas)} personas, {len(tipos)} tipos). Datos reales: no lo subas a git.")


def _res(r):
    return {k: r.get(k) for k in ("ok", "nivel", "desenmascarable") if r.get(k) is not None}


if __name__ == "__main__":
    main()

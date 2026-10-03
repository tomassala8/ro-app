#!/usr/bin/env python3
"""fuentes_ia/lote_nocturno.py · lo que puede esperar, de noche y a mitad de precio (Batch API) · 3-oct-2026.

El copiloto de cada cliente («qué haría hoy») no hace falta al segundo: se prepara de noche en UN lote con la Batch API
de Anthropic (50 % más barato; resultado en menos de 24 h, casi siempre en menos de 1 h) y por la mañana la app lo sirve
como «vivo». El lote pasa por ia_gasto: se reserva su peor caso contra los topes (si no cabe, no se envía), y al
recogerlo se apunta el coste real de cada cliente. Escribe en la base de la app de verdad (local.db, o RO_DB si se pasa).

  python3 fuentes_ia/lote_nocturno.py --enviar      (de noche, p. ej. 02:00) copiloto de todos los clientes, como lo ve su account
  python3 fuentes_ia/lote_nocturno.py --recoger     (cada 30 min hasta las 07:00) recoge los lotes terminados
  python3 fuentes_ia/lote_nocturno.py --estado      lotes en curso y su reserva

Sin clave de Anthropic no hace nada (lo dice y sale con 0).
"""
import os
import sys
from datetime import datetime
from pathlib import Path

APP = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(APP))
os.environ.setdefault("RO_AVISOS_SIN_BUCLE", "1")
import servir as S  # noqa: E402
import ia as IA     # noqa: E402

S.E.cargar()
if IA.S is None:
    IA.enganchar(S.Manejador, S)
G = IA.G


def enviar():
    e = IA.estado()
    if not e["conectada"]:
        print("Nada que enviar:", e["motivo"])
        return
    trabajos, quien_de = [], {}
    for c in S.E.crudo["clientes"]:
        v = IA._verdad(c["id"]) or {}
        p = S.E.persona(v.get("account")) or S.E.persona("tomas")
        cp = S.P.contexto(p, S.E.crudo)
        try:
            ctx = IA.contexto_copiloto(p, cp, c["id"])
        except IA.Denegado:
            continue
        trabajos.append((f"{c['id']}|{p['id']}", IA.SISTEMA_COPILOTO, ctx, IA.ESQ_COPILOTO, "high"))
    try:
        lid = G.lote_enviar("copiloto", trabajos)
    except RuntimeError as e:
        print("Lote NO enviado:", e)
        return
    print(f"Lote {lid} enviado: {len(trabajos)} clientes (reserva del peor caso a mitad de precio).")


def recoger():
    with S.conectar() as con:
        ids = [r[0] for r in con.execute("SELECT id FROM ia_lotes WHERE estado='enviado'").fetchall()]
    for lid in ids:
        out = G.lote_recoger(lid)
        if out is None:
            print(lid, "aún en marcha")
            continue
        for clave_obj, salida in out.items():
            IA._guardar_vivo("copiloto", clave_obj, {**salida, "origen": "vivo", "modelo": G.modelo_de("copiloto"), "lote": lid,
                                                     "generado": datetime.now().strftime("%Y-%m-%d %H:%M")})
        print(lid, f"recogido: {len(out)} copilotos")


if __name__ == "__main__":
    if "--enviar" in sys.argv:
        enviar()
    elif "--recoger" in sys.argv:
        recoger()
    else:
        with S.conectar() as con:
            for r in con.execute("SELECT id, creado, tarea, n, reservado_eur, estado FROM ia_lotes ORDER BY creado DESC LIMIT 10"):
                print(*r)

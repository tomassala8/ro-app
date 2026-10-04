#!/usr/bin/env python3
"""
migracion/validar_sqlite.py · mira la base SQLite ANTES de copiarla a Postgres (paso F2.3) y avisa de lo que
Postgres no va a tragar o va a guardar distinto. SQLite deja meter cualquier cosa en cualquier columna; Postgres no.

  python3 migracion/validar_sqlite.py --sqlite ~/RO_MIGRACION/local.db.antes
  DATABASE_URL=… python3 migracion/validar_sqlite.py --sqlite ~/RO_MIGRACION/local.db.antes --pg   # y contra las columnas de Postgres

Busca, columna a columna:
  ✘ bytes NUL (\\x00) en un texto          → Postgres rechaza la fila entera.
  ✘ texto que no es UTF-8 válido           → ídem.
  ✘ con --pg: un valor que no cabe en el tipo de Postgres (texto no numérico en INTEGER/BIGINT/NUMERIC/DOUBLE,
    número en BOOLEAN que no es 0/1, texto en JSON/JSONB que no es JSON).
  ⚠ tipos mezclados (p. ej. «12» como texto y 12 como número en la misma columna): se copia, pero comparar,
    ordenar o agrupar puede dar distinto que hoy. Se apunta en NOTAS_NOCHE.md con su decisión.
Nunca escribe en la base (la abre en solo lectura) ni imprime valores: solo tabla, columna, cuántos y el id de 3 filas.
Sale 1 si hay algún ✘.
"""
import argparse
import json
import os
import sqlite3
import sys

NUMERICOS = {"integer", "bigint", "smallint", "numeric", "double precision", "real"}


def tipos_pg(url):
    import psycopg
    with psycopg.connect(url) as pg:
        filas = pg.execute("SELECT table_name, column_name, data_type FROM information_schema.columns "
                           "WHERE table_schema='public'").fetchall()
    return {(t, c): d for t, c, d in filas}


def no_cabe(valor, tipo_pg):
    if valor is None or tipo_pg is None:
        return False
    if tipo_pg in NUMERICOS:
        if isinstance(valor, (int, float)):
            return False
        try:
            float(str(valor).strip())
            return False
        except ValueError:
            return True
    if tipo_pg == "boolean":
        return str(valor).strip().lower() not in {"0", "1", "true", "false", "t", "f"}
    if tipo_pg in {"json", "jsonb"} and isinstance(valor, (str, bytes)):
        try:
            json.loads(valor)
            return False
        except (ValueError, UnicodeDecodeError):
            return True
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sqlite", required=True)
    ap.add_argument("--pg", action="store_true", help="comparar también con las columnas de Postgres (DATABASE_URL)")
    a = ap.parse_args()
    tipos = tipos_pg(os.environ.get("DATABASE_URL") or sys.exit("Falta DATABASE_URL.")) if a.pg else {}
    con = sqlite3.connect(f"file:{a.sqlite}?mode=ro", uri=True)
    con.text_factory = bytes          # así se ve el texto que no es UTF-8 en vez de reventar
    tablas = [r[0].decode() for r in con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
    malos, avisos = 0, 0
    for t in tablas:
        cols = [r[1].decode() for r in con.execute(f'PRAGMA table_info("{t}")')]
        tiene_id = "id" in cols
        for c in cols:
            mezcla = {r[0].decode(): r[1] for r in con.execute(
                f'SELECT typeof("{c}"), count(*) FROM "{t}" GROUP BY 1')}
            de_verdad = {k: n for k, n in mezcla.items() if k != "null"}
            problemas = {"NUL": [], "no UTF-8": [], "no cabe en " + str(tipos.get((t, c))): []}
            sel = f'SELECT {"id" if tiene_id else "rowid"}, "{c}" FROM "{t}" WHERE "{c}" IS NOT NULL'
            for fid, v in con.execute(sel):
                if isinstance(v, bytes) and mezcla.get("text"):
                    if b"\x00" in v:
                        problemas["NUL"].append(fid)
                    try:
                        v = v.decode("utf-8")
                    except UnicodeDecodeError:
                        problemas["no UTF-8"].append(fid)
                        continue
                if tipos and no_cabe(v, tipos.get((t, c))):
                    problemas["no cabe en " + str(tipos.get((t, c)))].append(fid)
            for que, ids in problemas.items():
                if ids:
                    malos += 1
                    print(f"✘ {t}.{c}: {len(ids)} fila(s) con {que} (ids {', '.join(map(str, ids[:3]))}"
                          f"{'…' if len(ids) > 3 else ''})")
            if len(de_verdad) > 1 and set(de_verdad) != {"integer", "real"}:
                avisos += 1
                print(f"⚠ {t}.{c}: tipos mezclados {de_verdad}")
    print(f"\n{len(tablas)} tablas · {malos} ✘ · {avisos} ⚠")
    if malos:
        print("Arréglalos en la COPIA (~/RO_MIGRACION/local.db.antes no: haz otra, local.db.limpia), nunca en local.db,"
              " con la orden exacta apuntada en NOTAS_NOCHE.md, y copia desde esa.")
    sys.exit(1 if malos else 0)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
migracion/copiar_sqlite_a_pg.py · copia las filas de la base de hoy (SQLite: local.db y la del estado de la tubería)
a la base Postgres NUEVA, que ya tiene las tablas creadas por Prisma (pnpm db:deploy).

  DATABASE_URL="postgresql://127.0.0.1:5432/ro_app?user=ro&password=ro" python3 migracion/copiar_sqlite_a_pg.py --sqlite local.db
  DATABASE_URL=… python3 migracion/copiar_sqlite_a_pg.py --sqlite despliegue/estado/tuberia.db --renombrar avisos=tuberia_avisos

- Copia tabla a tabla las columnas que existen en los dos lados. Lo que sobra o falta lo dice, no lo inventa.
- Desactiva los disparadores SOLO durante la copia (session_replication_role = replica): el rastro imborrable
  no deja insertar con id fijo si no, y la copia tiene que ser idéntica. Al acabar vuelven solos.
- Pone los contadores (BIGSERIAL) detrás del id más alto, para que lo nuevo no choque.
- --vaciar borra antes esas tablas en Postgres (pide escribir «sí»). Sin --vaciar, si la tabla ya tiene filas, la salta.
- Al final compara el número de filas de cada tabla en los dos lados. Sale 1 si alguna no cuadra.
Nunca toca el fichero SQLite (lo abre en solo lectura).
"""
import argparse
import os
import sqlite3
import sys
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sqlite", action="append", required=True)
    ap.add_argument("--vaciar", action="store_true")
    ap.add_argument("--renombrar", action="append", default=[],
                    help="tabla_sqlite=tabla_pg, p. ej. avisos=tuberia_avisos para la base de la tubería (ver PLAN_MAESTRO §7.1)")
    a = ap.parse_args()
    url = os.environ.get("DATABASE_URL") or sys.exit("Falta DATABASE_URL.")
    import psycopg
    pg = psycopg.connect(url)
    cur = pg.cursor()
    cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE'")
    tablas_pg = {r[0] for r in cur.fetchall()} - {"_prisma_migrations"}
    if a.vaciar and input("Se BORRAN las filas de las tablas que se copian. Escribe «sí»: ").strip() != "sí":
        sys.exit("Nada hecho.")
    cur.execute("SET session_replication_role = replica")
    mal = []
    for ruta in a.sqlite:
        p = Path(ruta).expanduser().resolve()
        if not p.exists():
            sys.exit(f"No existe {p}")
        sq = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
        sq.row_factory = sqlite3.Row
        renombrar = dict(r.split("=", 1) for r in a.renombrar)
        for (t_sq,) in sq.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"):
            t = renombrar.get(t_sq, t_sq)
            if t not in tablas_pg:
                print(f"⚠ {t}: está en {p.name} pero no en Postgres (¿falta en schema.prisma?)")
                mal.append(t)
                continue
            cols_sq = [r[1] for r in sq.execute(f"PRAGMA table_info({t_sq})")]
            cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name=%s", (t,))
            tipos_pg = dict(cur.fetchall())
            comunes = [c for c in cols_sq if c in tipos_pg]
            sobran = [c for c in cols_sq if c not in tipos_pg]
            if sobran:
                print(f"⚠ {t}: columnas que no existen en Postgres y NO se copian: {sobran}")
            cur.execute(f'SELECT count(*) FROM "{t}"')
            if cur.fetchone()[0]:
                if not a.vaciar:
                    print(f"· {t}: ya tiene filas en Postgres, se salta (usa --vaciar)")
                    continue
                cur.execute(f'DELETE FROM "{t}"')
            filas = sq.execute(f"SELECT {', '.join(comunes)} FROM {t_sq}").fetchall()
            if filas:
                lista = ", ".join(f'"{c}"' for c in comunes)
                marcas = ", ".join(["%s"] * len(comunes))
                binarios = {i for i, c in enumerate(comunes) if tipos_pg[c] == "bytea"}
                datos = [tuple(bytes(v) if i in binarios and v is not None else v for i, v in enumerate(f)) for f in filas]
                cur.executemany(f'INSERT INTO "{t}" ({lista}) VALUES ({marcas})', datos)
            # contadores
            for col in ("id", "n"):
                if col in comunes and tipos_pg.get(col) == "bigint":
                    cur.execute("SELECT pg_get_serial_sequence(%s, %s)", (t, col))
                    seq = cur.fetchone()[0]
                    if seq:
                        cur.execute(f'SELECT setval(%s, GREATEST((SELECT COALESCE(max("{col}"), 0) FROM "{t}"), 1))', (seq,))
            cur.execute(f'SELECT count(*) FROM "{t}"')
            n_pg = cur.fetchone()[0]
            ok = "✔" if n_pg == len(filas) else "✘"
            if n_pg != len(filas):
                mal.append(t)
            print(f"{ok} {t_sq}{'' if t == t_sq else ' → ' + t}: {len(filas)} filas en SQLite, {n_pg} en Postgres")
        sq.close()
    cur.execute("SET session_replication_role = DEFAULT")
    pg.commit()
    pg.close()
    if mal:
        print(f"\nRevisar: {sorted(set(mal))}")
        sys.exit(1)
    print("\nCopia completa y cuadrada.")


if __name__ == "__main__":
    main()

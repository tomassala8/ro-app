#!/usr/bin/env python3
"""
migracion/crear_base_pg.py · crea en Postgres TODAS las tablas que usa hoy la app (con el SQL del inventario)
para que Prisma las lea con «prisma db pull» y salga el schema.prisma de partida, columna por columna.

  python3 migracion/inventario.py                       # primero, el inventario al día (tablas.sql)
  DATABASE_URL="postgresql://127.0.0.1:5432/ro_app?user=ro&password=ro" python3 migracion/crear_base_pg.py [--limpiar]

Traduce con la misma función que ya usa el servidor en Render (despliegue/base.py → esquema_postgres): AUTOINCREMENT
→ BIGSERIAL, datetime('now') → texto UTC igual que SQLite, y los disparadores del rastro imborrable → plpgsql.
--limpiar borra antes el esquema public ENTERO (solo para una base de pruebas: pide escribir «sí»).

Avisa de las tablas que se definen dos veces con columnas distintas (hoy: «avisos», en schema_v2.sql y en
despliegue/estado.py): en local viven en ficheros distintos, pero en una sola base Postgres chocan.
"""
import os
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "despliegue"))
import base as B  # noqa: E402

SQL = RAIZ / "migracion" / "inventario" / "tablas.sql"


PRIMERO = ("schema_v2.sql", "servir.py")   # las tablas de la app mandan sobre las de las tareas si se llaman igual
DISPARADOR_CON_CONDICION = re.compile(   # el mismo final tolerante que base.py («RAISE(ABORT,'…')», sin «;» final)
    r"CREATE TRIGGER IF NOT EXISTS (\w+)\s+BEFORE\s+(UPDATE|DELETE|INSERT)\s+ON\s+(\w+)\s+WHEN\s+(.+?)\s+"
    r"BEGIN\s+SELECT\s+RAISE\(\s*ABORT\s*,\s*'([^']*)'\s*\)\s*;\s*END\b;?",
    re.S)


def bloques():
    texto = SQL.read_text(encoding="utf-8")
    actual, lista = None, []
    for trozo in re.split(r"(?m)^-- (.+)$", texto):
        trozo = trozo.strip()
        if not trozo:
            continue
        if not trozo.upper().startswith(("CREATE", "ALTER")):
            actual = trozo
            continue
        lista.append((actual, trozo))
    # primero todas las tablas, luego las columnas añadidas con ALTER, y por fichero según PRIMERO
    lista.sort(key=lambda x: (x[1].upper().startswith("ALTER"), PRIMERO.index(x[0]) if x[0] in PRIMERO else len(PRIMERO)))
    yield from lista


def disparador_con_condicion(sql):
    """SQLite «BEFORE UPDATE … WHEN cond BEGIN RAISE … END» → función plpgsql. despliegue/base.py NO los traduce hoy:
    en Postgres esas protecciones («de una acción solo avanza el estado», «una decisión se contesta una vez»…) faltarían."""
    m = DISPARADOR_CON_CONDICION.fullmatch(sql.strip())
    if not m:
        return None
    nombre, cuando, tabla, cond, msg = m.groups()
    cond = re.sub(r"\bIS NOT ((?:OLD|NEW)\.)", r"IS DISTINCT FROM \1", cond)
    fila = "OLD" if cuando == "DELETE" else "NEW"
    return (f"CREATE OR REPLACE FUNCTION {nombre}_fn() RETURNS trigger LANGUAGE plpgsql AS $f$ BEGIN "
            f"IF ({' '.join(cond.split())}) THEN RAISE EXCEPTION '%', '{msg}'; END IF; RETURN {fila}; END $f$;\n"
            f"DROP TRIGGER IF EXISTS {nombre} ON {tabla};\n"
            f"CREATE TRIGGER {nombre} BEFORE {cuando} ON {tabla} FOR EACH ROW EXECUTE FUNCTION {nombre}_fn();")


def main():
    url = os.environ.get("DATABASE_URL")
    if not url:
        sys.exit("Falta DATABASE_URL (una base de PRUEBAS, nunca la de producción).")
    import psycopg
    vistas, chocan, hechas = {}, [], 0
    with psycopg.connect(url, autocommit=True) as con:
        cur = con.cursor()
        if "--limpiar" in sys.argv:
            if input("Esto BORRA todo el esquema public de esa base. Escribe «sí»: ").strip() != "sí":
                sys.exit("Nada hecho.")
            cur.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
        cur.execute(B.esquema_postgres("").strip())
        for origen, sql in bloques():
            m = re.match(r"CREATE\s+(?:UNIQUE\s+)?(TABLE|INDEX|TRIGGER|VIEW)\s+IF\s+NOT\s+EXISTS\s+(\w+)", sql, re.I) \
                or re.match(r"(ALTER)\s+TABLE\s+(\w+)", sql, re.I)
            tipo, nombre = m.group(1).upper(), m.group(2)
            if tipo == "ALTER" and vistas.get(nombre) not in (None, origen) and origen not in PRIMERO:
                continue      # columna de la otra tabla que se llama igual (ver «chocan»)
            if tipo == "TABLE":
                if nombre in vistas and vistas[nombre] != origen:
                    chocan.append((nombre, vistas[nombre], origen))
                    continue
                vistas[nombre] = origen
            sql = sql.replace("{pk}", "BIGSERIAL PRIMARY KEY").replace("{blob}", "BYTEA")
            # las claves automáticas pasan a BIGSERIAL: las columnas que apuntan a ellas, a BIGINT (si no, Prisma no casa tipos)
            sql = re.sub(r"\bINTEGER(\s+(?:NOT NULL\s+)?REFERENCES)", r"BIGINT\1", sql)
            pg = disparador_con_condicion(sql) if tipo == "TRIGGER" else None
            if pg is None:
                pg = B.esquema_postgres(sql)
                pg = pg[pg.index("\n") + 1:]      # sin la cabecera de ro_prohibido (ya creada)
            try:
                cur.execute(pg)
                hechas += 1
            except Exception as e:
                print(f"✘ {tipo} {nombre} ({origen}): {str(e).splitlines()[0]}")
    print(f"✔ {hechas} sentencias aplicadas, {len(vistas)} tablas.")
    for nombre, a, b in chocan:
        print(f"⚠ La tabla «{nombre}» se define en {a} y en {b} con columnas distintas: en una sola base Postgres "
              f"chocan. Se ha creado la de {a}. Hay que renombrar una de las dos antes de desplegar.")


if __name__ == "__main__":
    main()

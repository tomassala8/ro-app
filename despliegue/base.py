#!/usr/bin/env python3
"""despliegue/base.py · la base de servir.py en Postgres con la MISMA interfaz que sqlite3 (C5, documento 26).

servir.py habla con su base así: «with conectar() as con: con.execute(sql_con_?, args).fetchone()["campo"]»,
«cur.lastrowid», «con.executescript(schema_v2.sql)» y «PRAGMA table_info(t)». En local sigue siendo SQLite (local.db).
Con DATABASE_URL (Render), servir.conectar() devuelve una ConexionPG que traduce lo mínimo:
  ?                         → %s            (y los % del texto → %%)
  datetime('now')           → la misma hora UTC en texto «AAAA-MM-DD HH:MM:SS» que da SQLite
  date('now')               → la fecha de hoy en texto
  INSERT OR IGNORE INTO …   → INSERT INTO … ON CONFLICT DO NOTHING
  PRAGMA foreign_keys       → nada (Postgres ya las aplica)
  PRAGMA table_info(t)      → columnas de information_schema (fila[1] = nombre, como en SQLite)
  lastrowid                 → RETURNING id (o n en historial) añadido a los INSERT de tablas con clave automática
y el esquema (schema_v2.sql) se traduce solo con esquema_postgres(): AUTOINCREMENT → BIGSERIAL, las vistas, y los
disparadores que impiden borrar o cambiar el rastro → funciones plpgsql que lanzan el mismo mensaje.

⚠️ Sin probar contra un Postgres real (no hay ninguno en el Mac). Se prueba el primer día en el entorno de pruebas de
Render con «python3 despliegue/base.py --probar» (crea el esquema, inserta, comprueba que el rastro no se borra).
"""
import os
import re
import sys
from pathlib import Path

AHORA_PG = "to_char(now() AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI:SS')"
HOY_PG = "to_char(current_date, 'YYYY-MM-DD')"
CLAVE_AUTO = {"asignaciones": "id", "registro": "id", "acciones": "id", "incidencias": "id", "decisiones": "id",
              "recargas": "id", "avisos": "id", "historial": "n"}


def esquema_postgres(sql):
    sql = re.sub(r"(?m)^\s*PRAGMA[^;]*;\s*$", "", sql)
    sql = re.sub(r"INTEGER PRIMARY KEY AUTOINCREMENT", "BIGSERIAL PRIMARY KEY", sql)
    sql = sql.replace("(datetime('now'))", f"({AHORA_PG})").replace("datetime('now')", AHORA_PG).replace("date('now')", HOY_PG)
    sql = sql.replace("CREATE VIEW IF NOT EXISTS", "CREATE OR REPLACE VIEW")
    cab = ("CREATE OR REPLACE FUNCTION ro_prohibido() RETURNS trigger LANGUAGE plpgsql AS $f$ "
           "BEGIN RAISE EXCEPTION '%', TG_ARGV[0]; END $f$;\n")

    def disparador(m):
        nombre, cuando, tabla, msg = m.group(1), m.group(2), m.group(3), m.group(4)
        return (f"DROP TRIGGER IF EXISTS {nombre} ON {tabla};\n"
                f"CREATE TRIGGER {nombre} BEFORE {cuando} ON {tabla} FOR EACH ROW EXECUTE FUNCTION ro_prohibido('{msg}');")
    sql = re.sub(r"CREATE TRIGGER IF NOT EXISTS (\w+) BEFORE (UPDATE|DELETE) ON (\w+) BEGIN SELECT RAISE\(ABORT, '([^']*)'\); END;",
                 disparador, sql)
    return cab + sql


def traducir(sql):
    s = sql.strip()
    if re.match(r"(?i)^PRAGMA\s+foreign_keys", s):
        return None, None
    m = re.match(r"(?i)^PRAGMA\s+table_info\((\w+)\)", s)
    if m:
        return ("SELECT ordinal_position - 1 AS cid, column_name AS name, data_type AS type FROM information_schema.columns "
                "WHERE table_name = %s ORDER BY ordinal_position"), (m.group(1),)
    s = s.replace("%", "%%").replace("datetime('now')", AHORA_PG).replace("date('now')", HOY_PG)
    if re.match(r"(?i)^INSERT\s+OR\s+IGNORE\s+INTO", s):
        s = re.sub(r"(?i)^INSERT\s+OR\s+IGNORE\s+INTO", "INSERT INTO", s) + " ON CONFLICT DO NOTHING"
    s = _marcadores(s)
    m = re.match(r"(?i)^INSERT\s+INTO\s+(\w+)", s)
    if m and m.group(1) in CLAVE_AUTO and " RETURNING " not in s.upper():
        s += f" RETURNING {CLAVE_AUTO[m.group(1)]}"
    return s, ()


def _marcadores(s):
    """? → %s fuera de las cadenas entre comillas simples."""
    out, dentro = [], False
    for ch in s:
        if ch == "'":
            dentro = not dentro
        out.append("%s" if ch == "?" and not dentro else ch)
    return "".join(out)


class Fila(dict):
    """Como sqlite3.Row: por nombre y por posición."""
    def __init__(self, columnas, valores):
        super().__init__(zip(columnas, valores))
        self._v = list(valores)

    def __getitem__(self, k):
        return self._v[k] if isinstance(k, int) else dict.__getitem__(self, k)

    def keys(self):
        return list(dict.keys(self))


class CursorPG:
    def __init__(self, cur, lastrowid=None):
        self._c, self.lastrowid = cur, lastrowid
        self._pend = None

    def _cols(self):
        return [d[0] for d in (self._c.description or [])]

    def fetchone(self):
        if self._pend is not None:
            r, self._pend = self._pend, None
            return r
        if self._c is None or self._c.description is None:
            return None
        r = self._c.fetchone()
        return Fila(self._cols(), r) if r is not None else None

    def fetchall(self):
        if self._c is None or self._c.description is None:
            return []
        return [Fila(self._cols(), r) for r in self._c.fetchall()]

    def __iter__(self):
        return iter(self.fetchall())


class ConexionPG:
    def __init__(self, url):
        try:
            import psycopg as pg
        except ImportError:
            import psycopg2 as pg
        self._con = pg.connect(url)

    def execute(self, sql, args=()):
        q, extra = traducir(sql)
        if q is None:
            return CursorPG(None)
        cur = self._con.cursor()
        params = tuple(args) if args else extra
        if params:
            cur.execute(q, params)
        else:
            cur.execute(q.replace("%%", "%"))   # sin parámetros, psycopg no interpreta los %
        lastrowid = None
        if " RETURNING " in q.upper() and q.upper().lstrip().startswith("INSERT"):
            r = cur.fetchone()
            lastrowid = r[0] if r else None
            return CursorPG(None, lastrowid)
        return CursorPG(cur, lastrowid)

    def executescript(self, sql):
        cur = self._con.cursor()
        cur.execute(esquema_postgres(sql))
        self._con.commit()

    def cursor(self):
        return self

    def commit(self):
        self._con.commit()

    def close(self):
        self._con.close()

    def __enter__(self):
        return self

    def __exit__(self, tipo, *_):
        # como sqlite3: confirma si todo fue bien y deshace si hubo error. Además CIERRA: servir.py abre una conexión
        # por bloque «with» y en Postgres cada conexión abierta cuenta (el plan Basic admite pocas).
        try:
            (self._con.rollback if tipo else self._con.commit)()
        finally:
            self._con.close()
        return False

    def __del__(self):
        try:
            self._con.close()
        except Exception:
            pass


def conectar():
    return ConexionPG(os.environ["DATABASE_URL"])


if __name__ == "__main__":
    app = Path(__file__).resolve().parents[1]
    if "--esquema" in sys.argv:
        print(esquema_postgres((app / "schema_v2.sql").read_text()))
    elif "--probar" in sys.argv:
        conectar().executescript((app / "schema_v2.sql").read_text())
        with conectar() as con:
            rid = con.execute("INSERT INTO registro (quien, coleccion, accion) VALUES (?,?,?)", ("prueba_c5", "prueba", "alta")).lastrowid
        try:
            with conectar() as con:
                con.execute("DELETE FROM registro WHERE id=?", (rid,))
            print("✘ el rastro se ha podido borrar")
        except Exception as e:
            print("✔ el rastro no se borra:", str(e).splitlines()[0])
        with conectar() as con:
            print("✔ columnas de registro:", [r[1] for r in con.execute("PRAGMA table_info(registro)").fetchall()][:5])
    else:
        print(__doc__)

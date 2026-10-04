#!/usr/bin/env python3
"""despliegue/base.py · la base de servir.py en Postgres con la MISMA interfaz que sqlite3 (C5, documento 26).

servir.py habla con su base así: «with conectar() as con: con.execute(sql_con_?, args).fetchone()["campo"]»,
«cur.lastrowid», «con.executescript(schema_v2.sql)» y «PRAGMA table_info(t)». En local sigue siendo SQLite (local.db).
Con DATABASE_URL (Render), servir.conectar() devuelve una ConexionPG que traduce lo mínimo:
  ?                         → %s            (y los % del texto → %%)
  datetime('now')           → la misma hora UTC en texto «AAAA-MM-DD HH:MM:SS» que da SQLite
  date('now')               → la fecha de hoy en texto
  INSERT OR IGNORE INTO …   → INSERT INTO … ON CONFLICT DO NOTHING
  INSERT OR REPLACE INTO …  → INSERT INTO … ON CONFLICT (clave primaria) DO UPDATE SET …
  datetime('now', '-1 hour') y datetime('now', ?) → la hora UTC en texto desplazada (interval)
  FROM sqlite_master        → las tablas de information_schema (name, type)
  PRAGMA foreign_keys       → nada (Postgres ya las aplica)
  BEGIN IMMEDIATE           → candado de transacción (pg_advisory_xact_lock): un solo escritor del rastro a la vez
  PRAGMA table_info(t)      → columnas de information_schema (fila[1] = nombre, como en SQLite)
  lastrowid                 → RETURNING <columna con contador> añadido a los INSERT de cualquier tabla que la tenga
y el esquema (schema_v2.sql) se traduce solo con esquema_postgres(): AUTOINCREMENT → BIGSERIAL, las vistas, y los
disparadores que impiden borrar o cambiar el rastro (también los que llevan condición WHEN) → funciones plpgsql que
lanzan el mismo mensaje.

⚠️ Sin probar contra un Postgres real (no hay ninguno en el Mac). Se prueba el primer día en el entorno de pruebas de
Render con «python3 despliegue/base.py --probar» (crea el esquema, inserta, comprueba que el rastro no se borra).
"""
import os
import re
import sys
import threading
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
    def con_condicion(m):   # «BEFORE … WHEN cond BEGIN RAISE … END» (p. ej. «de una acción solo avanza el estado»)
        nombre, cuando, tabla, cond, msg = m.groups()
        cond = re.sub(r"\bIS NOT ((?:OLD|NEW)\.)", r"IS DISTINCT FROM \1", cond)
        fila = "OLD" if cuando == "DELETE" else "NEW"
        return (f"CREATE OR REPLACE FUNCTION {nombre}_fn() RETURNS trigger LANGUAGE plpgsql AS $f$ BEGIN "
                f"IF ({' '.join(cond.split())}) THEN RAISE EXCEPTION '%', '{msg}'; END IF; RETURN {fila}; END $f$;\n"
                f"DROP TRIGGER IF EXISTS {nombre} ON {tabla};\n"
                f"CREATE TRIGGER {nombre} BEFORE {cuando} ON {tabla} FOR EACH ROW EXECUTE FUNCTION {nombre}_fn();")
    sql = re.sub(r"CREATE TRIGGER IF NOT EXISTS (\w+) BEFORE (UPDATE|DELETE|INSERT) ON (\w+)\s+WHEN (.+?)\s+BEGIN "
                 r"SELECT RAISE\(ABORT, '([^']*)'\); END;", con_condicion, sql, flags=re.S)
    sql = re.sub(r"CREATE TRIGGER IF NOT EXISTS (\w+) BEFORE (UPDATE|DELETE) ON (\w+) BEGIN SELECT RAISE\(ABORT, '([^']*)'\); END;",
                 disparador, sql)
    return cab + sql


SQLITE_MASTER_PG = ("(SELECT table_name AS name, table_name AS tbl_name, 'table' AS type FROM information_schema.tables "
                    "WHERE table_schema = 'public') AS sqlite_master")


def traducir(sql, claves=None, auto=None):
    """claves(tabla) → columnas de la clave primaria (para INSERT OR REPLACE); auto(tabla) → su columna con contador
    (BIGSERIAL), para que lastrowid funcione en TODAS las tablas, no solo en las de CLAVE_AUTO. Las da ConexionPG."""
    s = sql.strip()
    if re.match(r"(?i)^PRAGMA\s+foreign_keys", s):
        return None, None
    if re.match(r"(?i)^BEGIN(\s+(IMMEDIATE|EXCLUSIVE|DEFERRED))?;?$", s):
        # SQLite «BEGIN IMMEDIATE» = un solo escritor a la vez entre procesos (la cadena de huellas del rastro).
        # En Postgres la transacción ya está abierta: un candado de transacción hace lo mismo y se suelta en el COMMIT.
        return "SELECT pg_advisory_xact_lock(7262)", ()
    m = re.match(r"(?i)^PRAGMA\s+table_info\((\w+)\)", s)
    if m:
        return ("SELECT ordinal_position - 1 AS cid, column_name AS name, data_type AS type FROM information_schema.columns "
                "WHERE table_name = %s ORDER BY ordinal_position"), (m.group(1),)
    s = s.replace("%", "%%").replace("datetime('now')", AHORA_PG).replace("date('now')", HOY_PG)
    # datetime('now', '-14 days') y datetime('now', ?) con «-14 days»: la misma hora UTC en texto, desplazada
    s = re.sub(r"datetime\('now',\s*'([^']*)'\)",
               lambda m: f"to_char((now() AT TIME ZONE 'UTC') + interval '{m.group(1)}', 'YYYY-MM-DD HH24:MI:SS')", s)
    s = re.sub(r"datetime\('now',\s*\?\)", "to_char((now() AT TIME ZONE 'UTC') + CAST(? AS interval), 'YYYY-MM-DD HH24:MI:SS')", s)
    s = re.sub(r"(?i)\bFROM\s+sqlite_master\b", "FROM " + SQLITE_MASTER_PG, s)
    if re.match(r"(?i)^INSERT\s+OR\s+IGNORE\s+INTO", s):
        s = re.sub(r"(?i)^INSERT\s+OR\s+IGNORE\s+INTO", "INSERT INTO", s) + " ON CONFLICT DO NOTHING"
    m = re.match(r"(?i)^INSERT\s+OR\s+REPLACE\s+INTO\s+(\w+)\s*\(([^)]*)\)", s)
    if m and claves:
        # INSERT OR REPLACE = si choca la clave primaria, la fila nueva sustituye a la vieja
        pk = claves(m.group(1))
        cols = [c.strip() for c in m.group(2).split(",")]
        resto = [c for c in cols if c not in pk] or cols[:1]
        s = (re.sub(r"(?i)^INSERT\s+OR\s+REPLACE\s+INTO", "INSERT INTO", s) + f" ON CONFLICT ({', '.join(pk)}) DO UPDATE SET "
             + ", ".join(f"{c} = EXCLUDED.{c}" for c in resto))
    s = _marcadores(s)
    m = re.match(r"(?i)^INSERT\s+INTO\s+(\w+)", s)
    if m and " RETURNING " not in s.upper():
        col = CLAVE_AUTO.get(m.group(1)) or (auto(m.group(1)) if auto else None)
        if col:
            s += f" RETURNING {col}"
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
    def __init__(self, cur, lastrowid=None, rowcount=-1):
        self._c, self.lastrowid = cur, lastrowid
        self._pend = None
        # como sqlite3: filas tocadas por el último INSERT/UPDATE/DELETE (-1 si no aplica)
        self.rowcount = cur.rowcount if cur is not None else rowcount

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
        cols = self._cols()   # una vez, no por fila: psycopg rehace description en cada llamada (era el 70 % del tiempo)
        return [Fila(cols, r) for r in self._c.fetchall()]

    def __iter__(self):
        return iter(self.fetchall())


_CLAVES, _AUTO = {}, {}


# Conexiones reutilizadas: abrir una conexión nueva a Postgres en cada bloque «with» cuesta una ida y vuelta de red y
# la autenticación (medido el 4-oct: /api/rastro/verificar pasaba de 17 ms en SQLite a 130 ms en Postgres local; en la
# nube, con TLS, es más). Se guardan unas pocas conexiones libres; antes de reutilizar una se comprueba que sigue viva,
# así que un reinicio de Postgres no da errores: la conexión rota se tira y se abre otra.
_LIBRES, _CANDADO = [], threading.Lock()
_MAX_LIBRES = int(os.environ.get("RO_PG_LIBRES", "4"))


def _abrir(url):
    try:
        import psycopg as pg
    except ImportError:
        import psycopg2 as pg
    return pg.connect(url)


def _sana(con):
    try:
        if con.closed:
            return False
        con.cursor().execute("SELECT 1")
        con.rollback()
        return True
    except Exception:
        return False


def _cerrar(con):
    try:
        con.close()
    except Exception:
        pass


def _devolver(con):
    if con is None:
        return
    try:
        con.rollback()   # nada a medias pasa a la siguiente petición (y suelta el candado de transacción)
    except Exception:
        return _cerrar(con)
    with _CANDADO:
        if len(_LIBRES) < _MAX_LIBRES:
            _LIBRES.append(con)
            return
    _cerrar(con)


# Esquemas «CREATE … IF NOT EXISTS» que varios módulos (envios.py, sincronia.py…) lanzan en CADA petición. En SQLite
# no cuesta nada; en Postgres, dos a la vez chocan («tuple concurrently updated», incluso «deadlock»): medido el 4-oct
# con 30 personas a la vez, 172 errores 500. Ahora van de uno en uno (candado de transacción) y, si el script solo
# crea lo que no existe, una vez por proceso y base.
_ESQUEMAS_HECHOS, _CANDADO_ESQUEMA = set(), 7263


def _solo_crea_si_no_existe(sql):
    sin_cuerpos = re.sub(r"(?is)\bBEGIN\b.*?\bEND\b", "", re.sub(r"--[^\n]*", "", sql))   # cuerpos de disparadores
    frases = [f.strip() for f in sin_cuerpos.split(";") if f.strip()]
    patron = r"(?is)^CREATE\s+(UNIQUE\s+)?(TABLE|INDEX|TRIGGER|VIEW)\s+IF\s+NOT\s+EXISTS\b"
    return bool(frases) and all(re.match(patron, f) for f in frases)


class ConexionPG:
    def __init__(self, url):
        self._url = url
        self._con = None
        while self._con is None:
            with _CANDADO:
                libre = _LIBRES.pop() if _LIBRES else None
            if libre is None:
                self._con = _abrir(url)
            elif _sana(libre):
                self._con = libre
            else:
                _cerrar(libre)

    def _claves(self, tabla):
        if tabla not in _CLAVES:
            cur = self._con.cursor()
            cur.execute("SELECT a.attname FROM pg_index i JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey) "
                        "WHERE i.indrelid = %s::regclass AND i.indisprimary ORDER BY a.attnum", (tabla,))
            _CLAVES[tabla] = [r[0] for r in cur.fetchall()]
        return _CLAVES[tabla]

    def _auto(self, tabla):
        if tabla not in _AUTO:
            cur = self._con.cursor()
            cur.execute("SELECT column_name FROM information_schema.columns WHERE table_schema = 'public' AND table_name = %s "
                        "AND column_default LIKE 'nextval(%%' ORDER BY ordinal_position LIMIT 1", (tabla,))
            r = cur.fetchone()
            _AUTO[tabla] = r[0] if r else None
        return _AUTO[tabla]

    def execute(self, sql, args=()):
        q, extra = traducir(sql, self._claves, self._auto)
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
            return CursorPG(None, lastrowid, cur.rowcount)
        return CursorPG(cur, lastrowid)

    def executescript(self, sql):
        clave = (self._url, sql) if _solo_crea_si_no_existe(sql) else None
        if clave in _ESQUEMAS_HECHOS:
            return
        cur = self._con.cursor()
        cur.execute(f"SELECT pg_advisory_xact_lock({_CANDADO_ESQUEMA})")
        cur.execute(esquema_postgres(sql))
        self._con.commit()
        if clave:
            _ESQUEMAS_HECHOS.add(clave)

    def cursor(self):
        return self

    def commit(self):
        self._con.commit()

    def close(self):
        _devolver(self._con)
        self._con = None

    def __enter__(self):
        return self

    def __exit__(self, tipo, *_):
        # como sqlite3: confirma si todo fue bien y deshace si hubo error. Además la DEVUELVE: servir.py abre una
        # conexión por bloque «with» y en Postgres cada conexión abierta cuenta (el plan Basic admite pocas): como
        # mucho quedan RO_PG_LIBRES libres; las demás se cierran.
        try:
            (self._con.rollback if tipo else self._con.commit)()
        except Exception:
            _cerrar(self._con)
            self._con = None
            raise
        finally:
            self.close()
        return False

    def __del__(self):
        if getattr(self, "_con", None) is not None:
            _cerrar(self._con)


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

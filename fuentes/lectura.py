#!/usr/bin/env python3
"""fuentes/lectura.py · copia propia de todo lo que llega de las APIs, y nunca ceros (F5.10, N-01).

Todos los lectores pasan por aquí:
  from fuentes.lectura import leer, marcar
  l = leer("gsc", cliente_id, lambda: pedir_search_console(cliente_id))
  datos = marcar(l)      # dict con «_viejo» y «_desde» si la API falló; None si nunca hubo dato

  · lectura buena → se guarda en fuente_lectura y se devuelve (estado «ok»);
  · error, vacío (None, {}, [], "") o todo a 0 donde la última buena no lo estaba → la última buena,
    estado «viejo», con su hora en «desde»; el error también se guarda;
  · nunca hubo dato → estado «sin_dato» y datos None. Nunca un 0.
  · sospechoso(nuevo, ultimo_bueno) → texto si la lectura no vale (comprobaciones propias de cada fuente).

La base es la de servir.py: Postgres con DATABASE_URL (despliegue/base.py) o SQLite en RO_DB o <repo>/local.db.
Las horas van en UTC, texto «AAAA-MM-DD HH:MM:SS», como el resto de schema_v2.sql.
"""
import hashlib
import json
import os
import sqlite3
import sys
from collections import namedtuple
from pathlib import Path

APP = Path(__file__).resolve().parent.parent
ESQUEMA = APP / "schema_v2.sql"
GUARDAR = 30            # lecturas buenas por fuente y recurso
DIAS_ERRORES = 30

Lectura = namedtuple("Lectura", "datos estado desde error")   # estado: ok | viejo | sin_dato
_PREPARADAS = set()


def conectar():
    if os.environ.get("DATABASE_URL"):
        sys.path.insert(1, str(APP / "despliegue"))
        import base as BASE_PG          # el mismo módulo que usa servir.py (comparte las conexiones)
        return BASE_PG.conectar()
    con = sqlite3.connect(os.environ.get("RO_DB") or APP / "local.db", timeout=10)
    con.row_factory = sqlite3.Row
    return con


def _bloque_ddl():
    """Solo el trozo de fuente_lectura de schema_v2.sql: el DDL vive en un sitio."""
    texto = ESQUEMA.read_text()
    ini = texto.rfind("\n-- ----", 0, texto.index("F5.10 · N-01")) + 1
    fin = texto.find("\n-- ----", ini + 10)
    return texto[ini:fin if fin > 0 else None]


def _preparar(con):
    clave = os.environ.get("DATABASE_URL") or os.environ.get("RO_DB") or "local"
    if clave not in _PREPARADAS:
        con.executescript(_bloque_ddl())
        _PREPARADAS.add(clave)


def huella(datos):
    return hashlib.sha256(_json(datos).encode()).hexdigest()


def _json(datos):
    return json.dumps(datos, sort_keys=True, ensure_ascii=False, default=str)


def _numeros(x):
    """Todas las hojas numéricas (sin booleanos)."""
    if isinstance(x, dict):
        for v in x.values():
            yield from _numeros(v)
    elif isinstance(x, (list, tuple)):
        for v in x:
            yield from _numeros(v)
    elif isinstance(x, (int, float)) and not isinstance(x, bool):
        yield x


def a_cero(x):
    """True si hay cifras y todas son 0."""
    nums = list(_numeros(x))
    return bool(nums) and all(n == 0 for n in nums)


def _ultimo_bueno(con, fuente, recurso):
    return con.execute("SELECT id, hora, cuerpo FROM fuente_lectura WHERE fuente=? AND recurso=? AND ok=1 "
                       "ORDER BY id DESC LIMIT 1", (fuente, recurso)).fetchone()


def _apuntar(con, fuente, recurso, ok, codigo=None, error=None, datos=None):
    cuerpo = None if datos is None else _json(datos)
    return con.execute("INSERT INTO fuente_lectura (fuente, recurso, ok, codigo, error, cuerpo, huella) VALUES (?,?,?,?,?,?,?)",
                       (fuente, recurso, ok, codigo, error, cuerpo, cuerpo and huella(datos))).lastrowid


def _fallo(datos, anterior, sospechoso):
    """(codigo, error) si la lectura no vale; None si es buena."""
    if datos is None or datos == {} or datos == [] or datos == "":
        return "vacio", "La API no devolvió nada"
    if isinstance(datos, dict) and datos.get("_error"):
        return "error", str(datos["_error"])[:300]
    if anterior is not None and a_cero(datos) and not a_cero(anterior):
        return "a_cero", "Todo a 0 y la última lectura buena no lo estaba"
    motivo = sospechoso(datos, anterior) if sospechoso else None
    if motivo:
        return "sospechoso", str(motivo)[:300]
    return None


def leer(fuente, recurso, funcion, *, sospechoso=None):
    """Llama a funcion(), guarda lo que trae y devuelve una Lectura. Nunca devuelve ceros inventados."""
    recurso = "" if recurso is None else str(recurso)
    try:
        datos, exc = funcion(), None
    except Exception as e:                      # la API cayó: se apunta y se sirve lo último bueno
        datos, exc = None, e
    con = conectar()
    try:
        with con:
            _preparar(con)
            previa = _ultimo_bueno(con, fuente, recurso)
            anterior = json.loads(previa["cuerpo"]) if previa else None
            if exc is not None:
                codigo = getattr(exc, "code", None) or getattr(exc, "status", None) or type(exc).__name__
                fallo = (str(codigo), " ".join(str(exc).split())[:300] or type(exc).__name__)
            else:
                fallo = _fallo(datos, anterior, sospechoso)
            if fallo is None:
                rid = _apuntar(con, fuente, recurso, 1, datos=datos)
                hora = con.execute("SELECT hora FROM fuente_lectura WHERE id=?", (rid,)).fetchone()["hora"]
                _podar_uno(con, fuente, recurso)
                return Lectura(datos, "ok", hora, None)
            _apuntar(con, fuente, recurso, 0, fallo[0], fallo[1], None if exc is not None or fallo[0] == "vacio" else datos)
            texto = f"{fallo[0]}: {fallo[1]}"
            if previa:
                return Lectura(anterior, "viejo", previa["hora"], texto)
            return Lectura(None, "sin_dato", None, texto)
    finally:
        con.close()


def marcar(lectura):
    """Convención del plan (§2.5): dict con «_viejo»: True y «_desde»: hora si va con dato viejo; None si no hay dato."""
    if lectura.estado == "sin_dato":
        return None
    if lectura.estado == "viejo" and isinstance(lectura.datos, dict):
        return {**lectura.datos, "_viejo": True, "_desde": lectura.desde}
    return lectura.datos


def _podar_uno(con, fuente, recurso):
    con.execute("DELETE FROM fuente_lectura WHERE fuente=? AND recurso=? AND ok=1 AND id NOT IN ("
                "SELECT id FROM fuente_lectura WHERE fuente=? AND recurso=? AND ok=1 ORDER BY id DESC LIMIT ?)",
                (fuente, recurso, fuente, recurso, GUARDAR))


def podar(con=None):
    """Deja las 30 últimas lecturas buenas de cada fuente y recurso y 30 días de errores. Devuelve las filas borradas."""
    propia = con is None
    con = con or conectar()
    try:
        _preparar(con)
        n = con.execute("DELETE FROM fuente_lectura WHERE ok=1 AND id NOT IN (SELECT id FROM ("
                        "SELECT id, ROW_NUMBER() OVER (PARTITION BY fuente, recurso ORDER BY id DESC) AS n "
                        "FROM fuente_lectura WHERE ok=1) t WHERE n <= ?)", (GUARDAR,)).rowcount
        n += con.execute(f"DELETE FROM fuente_lectura WHERE ok=0 AND hora < datetime('now', '-{DIAS_ERRORES} days')").rowcount
        if propia:
            con.commit()
        return n
    finally:
        if propia:
            con.close()

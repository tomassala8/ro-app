#!/usr/bin/env python3
"""despliegue/estado.py · la base de ESTADO de la tubería, con la misma interfaz en SQLite y en Postgres (C5).

Qué guarda (y nada más):
  · ejecuciones   una fila por vuelta (modo, inicio, fin, estado, resumen JSON)
  · pasos         una fila por paso e intento (duración, salida saneada, error)
  · llaves        las llaves que ROTAN (hoy solo ghl_app_refresh_token), con su número de rotaciones
  · tuberia_avisos  solo en el servidor sin local.db: misma regla que E0 (≤3 «para avisar» al día, sin repetir). Antes «avisos» (F2.1, 5-oct-2026: chocaba con la «avisos» de la app en Postgres)
  · sellos        «último dato bueno» por paso: cuándo fue bien por última vez y por qué es viejo

Dónde vive:
  · Sin DATABASE_URL → SQLite en RO_ESTADO_DIR/tuberia.db (Mac, Hetzner, pruebas).
  · Con DATABASE_URL=postgres://… → Postgres (Render, Cloud Run + Cloud SQL). Hace falta psycopg (v3) o psycopg2.

Bloqueos (misma llamada en los dos):  with E.bloqueo("tuberia"): …
  · SQLite: fcntl.flock sobre RO_ESTADO_DIR/<nombre>.lock (no bloqueante si espera=False).
  · Postgres: pg_try_advisory_lock / pg_advisory_lock en una conexión propia, que se suelta al salir.
"""
import fcntl
import hashlib
import json
import os
import sqlite3
import sys
import time
from contextlib import contextmanager
from datetime import date, datetime  # noqa: F401
from zoneinfo import ZoneInfo
from pathlib import Path

sys.path.insert(1, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402

TOPE_AVISOS_DIA = 3

ESQUEMA = """
CREATE TABLE IF NOT EXISTS ejecuciones (id {pk}, modo TEXT, quien TEXT, inicio TEXT, fin TEXT, estado TEXT, resumen TEXT);
CREATE TABLE IF NOT EXISTS pasos (id {pk}, ejecucion INTEGER, paso TEXT, intento INTEGER, inicio TEXT, segundos REAL,
                                  estado TEXT, salida TEXT, error TEXT);
CREATE TABLE IF NOT EXISTS llaves (nombre TEXT PRIMARY KEY, valor TEXT, rotada TEXT, rotaciones INTEGER DEFAULT 0, origen TEXT);
CREATE TABLE IF NOT EXISTS tuberia_avisos (id {pk}, dia TEXT, tipo TEXT, clave TEXT, texto TEXT, estado TEXT, creado TEXT);
CREATE TABLE IF NOT EXISTS sellos (paso TEXT PRIMARY KEY, ultimo_bueno TEXT, ultimo_intento TEXT, estado TEXT, motivo TEXT);
"""


def ahora_dt():
    return datetime.now(ZoneInfo("Europe/Madrid")).replace(tzinfo=None)


def ahora():
    """Hora de Madrid sin zona (R16): la base de estado y el registro de la tubería se leen en hora de Madrid aunque
    el Mac esté de viaje o el servidor vaya en UTC. Lo que va a «recargas» de local.db se pasa a UTC al guardarlo."""
    return ahora_dt().isoformat(timespec="seconds")


class _Base:
    ph = "?"

    # ---------------- utilidades comunes (mismo SQL en los dos motores, cambia el marcador)
    def q(self, sql):
        return sql.replace("?", self.ph)

    def ejecutar(self, sql, args=()):
        with self.conexion() as con:
            cur = con.cursor()
            cur.execute(self.q(sql), args)
            try:
                return cur.fetchall()
            except Exception:
                return []

    def insertar(self, sql, args=()):
        raise NotImplementedError

    # ---------------- API de la tubería
    def nueva_ejecucion(self, modo, quien):
        return self.insertar("INSERT INTO ejecuciones (modo, quien, inicio, estado) VALUES (?,?,?,?)",
                             (modo, quien, ahora(), "en_curso"))

    def cerrar_ejecucion(self, eid, estado, resumen):
        self.ejecutar("UPDATE ejecuciones SET fin=?, estado=?, resumen=? WHERE id=?",
                      (ahora(), estado, json.dumps(resumen, ensure_ascii=False), eid))

    def apuntar_paso(self, eid, paso, intento, inicio, segundos, estado, salida, error):
        self.insertar("INSERT INTO pasos (ejecucion, paso, intento, inicio, segundos, estado, salida, error) VALUES (?,?,?,?,?,?,?,?)",
                      (eid, paso, intento, inicio, segundos, estado, salida, error))

    def ultimas(self, n=10):
        return self.ejecutar("SELECT id, modo, quien, inicio, fin, estado FROM ejecuciones ORDER BY id DESC LIMIT ?", (n,))

    def sello(self, paso):
        r = self.ejecutar("SELECT paso, ultimo_bueno, ultimo_intento, estado, motivo FROM sellos WHERE paso=?", (paso,))
        return dict(zip(("paso", "ultimo_bueno", "ultimo_intento", "estado", "motivo"), r[0])) if r else None

    def sellar(self, paso, bien, motivo=""):
        previo = self.sello(paso)
        t = ahora()
        bueno = t if bien else (previo or {}).get("ultimo_bueno")
        estado = "bien" if bien else ("dato_viejo" if bueno else "sin_dato")
        if previo:
            self.ejecutar("UPDATE sellos SET ultimo_bueno=?, ultimo_intento=?, estado=?, motivo=? WHERE paso=?",
                          (bueno, t, estado, motivo, paso))
        else:
            self.ejecutar("INSERT INTO sellos (paso, ultimo_bueno, ultimo_intento, estado, motivo) VALUES (?,?,?,?,?)",
                          (paso, bueno, t, estado, motivo))
        return estado

    def sellos(self):
        return [dict(zip(("paso", "ultimo_bueno", "ultimo_intento", "estado", "motivo"), r))
                for r in self.ejecutar("SELECT paso, ultimo_bueno, ultimo_intento, estado, motivo FROM sellos ORDER BY paso")]

    # ---------------- llaves que rotan
    def leer_llave(self, nombre):
        r = self.ejecutar("SELECT valor, rotaciones FROM llaves WHERE nombre=?", (nombre,))
        return (r[0][0], r[0][1]) if r else (None, 0)

    def guardar_llave(self, nombre, valor, origen="rotacion"):
        if self.ejecutar("SELECT 1 FROM llaves WHERE nombre=?", (nombre,)):
            self.ejecutar("UPDATE llaves SET valor=?, rotada=?, rotaciones=rotaciones+1, origen=? WHERE nombre=?",
                          (valor, ahora(), origen, nombre))
        else:
            self.ejecutar("INSERT INTO llaves (nombre, valor, rotada, rotaciones, origen) VALUES (?,?,?,?,?)",
                          (nombre, valor, ahora(), 0, origen))

    # ---------------- tuberia_avisos (servidor sin local.db): misma regla que servir.calcular_avisos()
    def avisar(self, tipo, clave, texto):
        hoy = datetime.now(ZoneInfo("Europe/Madrid")).date().isoformat()   # día de Madrid, como E0 (R16)
        if self.ejecutar("SELECT 1 FROM tuberia_avisos WHERE dia=? AND tipo=? AND clave=?", (hoy, tipo, clave)):
            return None
        n = self.ejecutar("SELECT count(*) FROM tuberia_avisos WHERE dia=? AND estado='para_avisar'", (hoy,))[0][0]
        estado = "para_avisar" if n < TOPE_AVISOS_DIA else "retenido"
        self.insertar("INSERT INTO tuberia_avisos (dia, tipo, clave, texto, estado, creado) VALUES (?,?,?,?,?,?)",
                      (hoy, tipo, clave, texto, estado, ahora()))
        return estado


class SQLite(_Base):
    motor = "sqlite"

    def __init__(self, ruta=None):
        self.dir = config.ESTADO_DIR
        self.dir.mkdir(parents=True, exist_ok=True)
        self.ruta = Path(ruta or os.environ.get("RO_ESTADO_DB") or self.dir / "tuberia.db")
        with self.conexion() as con:
            con.executescript(ESQUEMA.format(pk="INTEGER PRIMARY KEY AUTOINCREMENT"))

    @contextmanager
    def conexion(self):
        con = sqlite3.connect(self.ruta, timeout=30)
        try:
            yield con
            con.commit()
        finally:
            con.close()

    def insertar(self, sql, args=()):
        with self.conexion() as con:
            return con.execute(sql, args).lastrowid

    @contextmanager
    def bloqueo(self, nombre, espera=False):
        f = open(self.dir / f"{nombre}.lock", "a+")
        try:
            fcntl.flock(f, fcntl.LOCK_EX | (0 if espera else fcntl.LOCK_NB))
        except BlockingIOError:
            f.close()
            raise Ocupado(nombre)
        try:
            f.seek(0), f.truncate(), f.write(f"{os.getpid()} {ahora()}\n"), f.flush()
            yield
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)
            f.close()


class Postgres(_Base):
    """⚠️ Sin probar en local (no hay Postgres en el Mac). Misma interfaz que SQLite."""
    motor = "postgres"
    ph = "%s"

    def __init__(self, url):
        self.url = url
        try:
            import psycopg as pg  # v3
        except ImportError:
            import psycopg2 as pg  # noqa: F401
        self.pg = pg
        with self.conexion() as con:
            cur = con.cursor()
            for sent in ESQUEMA.format(pk="BIGSERIAL PRIMARY KEY").split(";"):
                if sent.strip():
                    cur.execute(sent)

    @contextmanager
    def conexion(self):
        con = self.pg.connect(self.url)
        try:
            yield con
            con.commit()
        finally:
            con.close()

    def insertar(self, sql, args=()):
        sql = self.q(sql)
        devuelve = sql.strip().upper().startswith("INSERT INTO") and " RETURNING " not in sql.upper() and "llaves" not in sql
        with self.conexion() as con:
            cur = con.cursor()
            cur.execute(sql + (" RETURNING id" if devuelve else ""), args)
            return cur.fetchone()[0] if devuelve else None

    @contextmanager
    def bloqueo(self, nombre, espera=False):
        clave = int(hashlib.sha1(nombre.encode()).hexdigest()[:15], 16)
        con = self.pg.connect(self.url)
        con.autocommit = True
        cur = con.cursor()
        try:
            if espera:
                cur.execute("SELECT pg_advisory_lock(%s)", (clave,))
            else:
                cur.execute("SELECT pg_try_advisory_lock(%s)", (clave,))
                if not cur.fetchone()[0]:
                    raise Ocupado(nombre)
            yield
        finally:
            try:
                cur.execute("SELECT pg_advisory_unlock(%s)", (clave,))
            finally:
                con.close()


class Ocupado(Exception):
    """Ya hay otra vuelta con el mismo bloqueo."""


_ESTADO = None


def abrir():
    """La base de estado que toca en esta máquina."""
    global _ESTADO
    if _ESTADO is None:
        url = os.environ.get("DATABASE_URL", "")
        _ESTADO = Postgres(url) if url.startswith(("postgres://", "postgresql://")) else SQLite()
    return _ESTADO


if __name__ == "__main__":
    E = abrir()
    print("motor:", E.motor)
    for r in E.ultimas(10):
        print(" ", r)
    for s in E.sellos():
        print(" ", s["paso"], s["estado"], s["ultimo_bueno"], s["motivo"][:80] if s["motivo"] else "")

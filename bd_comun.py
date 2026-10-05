"""bd_comun.py · N-24: lo que comparten los módulos de Operaciones para hablar con la base.

Hasta ahora cada módulo se negaba (503) si había DATABASE_URL. Ahora hablan con la misma conexión que servir.py
(`S.conectar()`: SQLite en local, `despliegue/base.py` en la nube) y solo necesitan saber dos cosas:
  · `es_pg()`: ¿la conexión es Postgres? (la misma regla que `servir.conectar`: solo DATABASE_URL);
  · `ERRORES_BD`: los errores de la base que antes eran `sqlite3.Error` y ahora pueden ser de psycopg.
Sin IO al importar.
"""
import os
import sqlite3


def es_pg():
    return bool(os.environ.get('DATABASE_URL'))


def _errores():
    xs = [sqlite3.Error]
    for nombre in ('psycopg', 'psycopg2'):
        try:
            xs.append(__import__(nombre).Error)
            break
        except ImportError:
            continue
    return tuple(xs)


ERRORES_BD = _errores()


def conexion_valida(con):
    """Lo que antes era `isinstance(con, sqlite3.Connection)`: SQLite como siempre; con Postgres, la ConexionPG."""
    return isinstance(con, sqlite3.Connection) or (es_pg() and hasattr(con, 'execute') and hasattr(con, 'commit'))

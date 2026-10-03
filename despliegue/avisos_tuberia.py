#!/usr/bin/env python3
"""despliegue/avisos_tuberia.py · avisos de la tubería con el sistema de E0 (≤3 «para avisar» al día, sin repetir).

Dos casos:
  · Donde hay local.db (el Mac hoy, o Hetzner con servir.py): se REUTILIZA E0 tal cual.
      - Cada vuelta se apunta en la tabla «recargas» de local.db (la misma que llena «Actualizar ahora»), así
        Ajustes › Avisos y recargas la enseña y servir.calcular_avisos() dispara su «recarga_fallida» (dos fallos
        seguidos del mismo paso) y «fuente_rota / fuente_vieja» desde data/fuentes.json.
      - Los avisos propios de la tubería (llave de GHL, dato viejo del doble de su límite) entran en la tabla
        «avisos» con la MISMA regla (tope servir.TOPE_AVISOS_DIA y UNIQUE(dia, tipo, clave)).
  · Servidor sin local.db (Render con la app en Cloudflare): la tabla «avisos» de la base de estado
    (despliegue/estado.py), con la misma regla.

Nombre (R16, N15): se llamaba «avisos.py» y, con despliegue/ el primero en sys.path, tapaba al avisos.py de la raíz
(canales de N15): servir.py, importado desde aquí, recibía este módulo («module 'avisos' has no attribute 'enganchar'»).

Horas (R16, N16): en local.db todo se GUARDA en UTC con el formato de SQLite datetime('now') («AAAA-MM-DD HH:MM:SS»),
como hace servir.py en «recargas»; el día de los avisos es el de Madrid (permisos.hoy_iso). Se ENSEÑA en hora de Madrid.

Salida opcional hacia fuera (NO configurada en el prototipo; nada se envía si no existe la variable):
  RO_AVISOS_WEBHOOK  URL que recibe un POST JSON por cada aviso «para avisar» (correo/ClickUp los elige Tomás).
"""
import json
import os
import sqlite3
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

AQUI = Path(__file__).resolve().parent
APP = AQUI.parent
sys.path.insert(1, str(APP))


MADRID = ZoneInfo("Europe/Madrid")


def hoy_madrid():
    """El día de los avisos: el de Madrid (como permisos.hoy_iso de E0), aunque el Mac esté en otra zona."""
    return datetime.now(MADRID).date().isoformat()


def a_utc(hora):
    """Una hora de la tubería (ISO con zona, o sin zona = hora de Madrid) → UTC «AAAA-MM-DD HH:MM:SS», como
    datetime('now') de SQLite. Lo que no se entiende se deja tal cual."""
    try:
        d = hora if isinstance(hora, datetime) else datetime.fromisoformat(str(hora))
    except Exception:
        return hora
    if d.tzinfo is None:
        d = d.replace(tzinfo=MADRID)
    return d.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _db_e0():
    p = Path(os.environ.get("RO_DB") or APP / "local.db")
    return p if p.exists() and os.environ.get("RO_AVISOS") != "estado" else None


def _servir():
    """servir.py de E0, importado solo para reutilizar calcular_avisos() y TOPE_AVISOS_DIA (no arranca nada)."""
    try:
        import servir  # noqa: WPS433
        return servir
    except Exception:
        return None


def _hacia_fuera(texto, tipo, clave):
    url = os.environ.get("RO_AVISOS_WEBHOOK")
    if not url:
        return
    try:
        cuerpo = json.dumps({"tipo": tipo, "clave": clave, "texto": texto}).encode()
        urllib.request.urlopen(urllib.request.Request(url, data=cuerpo, method="POST",
                                                      headers={"Content-Type": "application/json"}), timeout=10)
    except Exception as e:  # un aviso que no sale no puede tumbar la tubería
        print(f"[avisos] no pude enviar el aviso hacia fuera: {e}", file=sys.stderr)


def avisar(tipo, clave, texto, E=None):
    """Devuelve 'para_avisar', 'retenido' o None (ya avisado hoy)."""
    db = _db_e0()
    if db:
        sv = _servir()
        tope = getattr(sv, "TOPE_AVISOS_DIA", 3)
        hoy = hoy_madrid()
        con = sqlite3.connect(db, timeout=10)
        try:
            if con.execute("SELECT 1 FROM avisos WHERE dia=? AND tipo=? AND clave=?", (hoy, tipo, clave)).fetchone():
                return None
            n = con.execute("SELECT count(*) FROM avisos WHERE dia=? AND estado='para_avisar'", (hoy,)).fetchone()[0]
            estado = "para_avisar" if n < tope else "retenido"
            con.execute("INSERT INTO avisos (dia, tipo, clave, texto, estado) VALUES (?,?,?,?,?)", (hoy, tipo, clave, texto, estado))
            con.commit()
        finally:
            con.close()
    else:
        import estado as ES
        estado = (E or ES.abrir()).avisar(tipo, clave, texto)
    if estado == "para_avisar":
        _hacia_fuera(texto, tipo, clave)
    return estado


def apuntar_vuelta_e0(modo, quien, pasos, inicio, fin):
    """La vuelta en «recargas» de local.db (formato de servir.py) y, después, los avisos de E0. «inicio» y «fin»
    llegan en hora de Madrid (o con zona) y se guardan en UTC, como «pedida» (datetime('now'))."""
    db = _db_e0()
    if not db or quien == "servir":      # si la pidió servir.py, la fila ya la lleva él
        return False
    con = sqlite3.connect(db, timeout=10)
    try:
        estado = "ok" if all(p["ok"] for p in pasos) else "con_fallos"
        con.execute("INSERT INTO recargas (quien, modo, estado, empezada, terminada, pasos) VALUES (?,?,?,?,?,?)",
                    (quien, "ligera" if modo == "ligero" else "completa", estado, a_utc(inicio), a_utc(fin),
                     json.dumps(pasos, ensure_ascii=False)))
        con.commit()
    finally:
        con.close()
    sv = _servir()
    if sv:
        try:
            sv.calcular_avisos()
        except Exception as e:
            print(f"[avisos] calcular_avisos de E0 falló: {e}", file=sys.stderr)
    return True

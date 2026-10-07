"""Archivo privado SQLite separado; no endpoint, proveedor ni BD de revisión.

El catálogo y actor proceden de código autorizado, nunca del cuerpo HTTP. El
llamador autentica ese actor y determina clientes de exportación. No se crea una
base real al importar. Límites conservadores para piloto y respaldo verificable.
"""
import hashlib
import json
import os
import re
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from embudo_eventos import ETAPAS, _hora, _public_id, _id

MAX_LOTE = 200
MAX_EVENTO = 32768
PROHIBIDOS = re.compile(r"password|passwd|contrase[nñ]a|secret|token|api.?key|authorization|cookie|credential", re.I)
VALOR_SECRETO = re.compile(r"\bBearer\s+\S+|\bsk-[A-Za-z0-9_-]{16,}|[?&](?:token|api_key|secret)=", re.I)


class ArchivoError(Exception):
    """Sin confirmación; tras error de commit, releer o repetir IDs antes de juzgar."""


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _seguro(value, nivel=0):
    if nivel > 8:
        return False
    if isinstance(value, dict):
        return all(isinstance(k, str) and not PROHIBIDOS.search(k) and _seguro(v, nivel + 1) for k, v in value.items())
    if isinstance(value, list):
        return len(value) <= 200 and all(_seguro(v, nivel + 1) for v in value)
    if isinstance(value, str):
        return not VALOR_SECRETO.search(value)
    return value is None or isinstance(value, (int, float, bool))


def _carpeta_privada(path):
    parent = Path(path).parent
    if not parent.exists():
        os.mkdir(parent, 0o700)  # Sólo la carpeta elegida; no crear/cambiar ancestros.
    if parent.is_symlink() or not parent.is_dir() or os.stat(parent).st_mode & 0o777 != 0o700:
        raise ValueError("Se requiere una carpeta privada0700; no se cambia una carpeta existente")


class ArchivoLeads:
    def __init__(self, path, catalogo):
        if str(path) == ":memory:":
            raise ValueError("Se requiere un archivo separado para persistencia y respaldo")
        self.path = Path(path)
        _carpeta_privada(self.path)
        if self.path.is_symlink():
            raise ValueError("El archivo de leads no puede ser un enlace simbólico")
        self.catalogo = {}
        for key, cfg in catalogo.items():
            if not _public_id(key) or not _public_id(cfg.get("cliente_id")) or not _public_id(cfg.get("source")):
                raise ValueError("Identidad de catálogo inválida")
            etapas = set(cfg.get("etapas") or [])
            actores = set(cfg.get("actores") or [])
            criterios = set(cfg.get("criterios") or [])
            privados = set(cfg.get("privado_campos") or [])
            if not etapas or not etapas <= set(ETAPAS) or not actores or not all(_public_id(x) for x in actores | criterios):
                raise ValueError("Política de catálogo inválida")
            if any(not isinstance(k, str) or PROHIBIDOS.search(k) for k in privados):
                raise ValueError("Campo privado de credenciales no permitido")
            if "cualificado" in etapas and not criterios:
                raise ValueError("Cualificación requiere criterios declarados en código")
            self.catalogo[key] = {"cliente_id": cfg["cliente_id"], "source": cfg["source"],
                "etapas": frozenset(etapas), "actores": frozenset(actores), "criterios": frozenset(criterios), "privado_campos": frozenset(privados)}
        # No abrir una BD existente de otra app, incluso si tiene tablas parecidas.
        conn = self._conectar(crear=True)
        try:
            with conn:
                tablas = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                if tablas and not tablas <= {"leads_eventos", "leads_recibos", "leads_meta"}:
                    raise ValueError("La base no es un archivo de leads separado")
                conn.execute("CREATE TABLE IF NOT EXISTS leads_meta (version INTEGER NOT NULL)")
                versions = [r[0] for r in conn.execute("SELECT version FROM leads_meta")]
                if versions and versions != [1]:
                    raise ValueError("Versión de archivo no compatible")
                if not versions:
                    conn.execute("INSERT INTO leads_meta VALUES (1)")
                conn.execute("""CREATE TABLE IF NOT EXISTS leads_eventos (
                    cliente_id TEXT NOT NULL, source TEXT NOT NULL, event_id TEXT NOT NULL,
                    payload TEXT NOT NULL, huella TEXT NOT NULL, actor_id TEXT NOT NULL,
                    fuente_key TEXT NOT NULL, registrado TEXT NOT NULL,
                    PRIMARY KEY(cliente_id,source,event_id))""")
                conn.execute("""CREATE TABLE IF NOT EXISTS leads_recibos (
                    recibo_id TEXT PRIMARY KEY, cliente_id TEXT NOT NULL, source TEXT NOT NULL,
                    event_id TEXT, actor_id TEXT NOT NULL, resultado TEXT NOT NULL,
                    motivo TEXT NOT NULL, registrado TEXT NOT NULL)""")
        finally:
            conn.close()

    def _conectar(self, crear=False):
        # No crea carpetas ni elige rutas de usuario por su cuenta.
        existe = self.path.exists()
        if existe and os.stat(self.path).st_mode & 0o777 != 0o600:
            raise ValueError("El archivo SQLite existente debe tener permisos0600")
        if not existe:
            if not crear:
                raise ArchivoError("Archivo ausente; recuperar el respaldo antes de continuar")
            fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.close(fd)
        conn = sqlite3.connect(str(self.path), timeout=5)
        conn.execute("PRAGMA busy_timeout=5000")
        return conn

    def _normalizar(self, raw, cfg):
        if not isinstance(raw, dict):
            return None, "evento_invalido"
        for key in ("cliente_id", "source"):
            if key in raw and raw[key] != cfg[key]:
                return None, "identidad_no_autorizada"
        if not _id(raw.get("event_id")) or not _id(raw.get("lead_id")):
            return None, "identificador_invalido"
        etapa, fecha = raw.get("etapa"), _hora(raw.get("fecha"))
        if etapa not in cfg["etapas"] or fecha is None:
            return None, "etapa_o_fecha_invalida"
        core = {"cliente_id": cfg["cliente_id"], "source": cfg["source"], "lead_id": raw["lead_id"],
                "event_id": raw["event_id"], "etapa": etapa, "fecha": fecha.isoformat()}
        if etapa in ("cualificado", "asistencia", "venta"):
            if raw.get("confirmado") is not True:
                return None, "resultado_no_confirmado"
            core["confirmado"] = True
        if etapa == "cualificado":
            if raw.get("criterio_version") not in cfg["criterios"]:
                return None, "criterio_no_autorizado"
            core["criterio_version"] = raw["criterio_version"]
        privados = raw.get("meta_privados", {})
        if not isinstance(privados, dict) or not set(privados) <= cfg["privado_campos"] or not _seguro(privados):
            return None, "metadatos_no_permitidos"
        if privados:
            core["meta_privados"] = privados
        try:
            if len(_json(core).encode("utf-8")) > MAX_EVENTO:
                return None, "evento_demasiado_grande"
        except (TypeError, ValueError, OverflowError):
            return None, "metadatos_invalidos"
        return core, ""

    def ingestar(self, fuente_key, actor_id, eventos):
        cfg = self.catalogo.get(fuente_key)
        if cfg is None or actor_id not in cfg["actores"]:
            raise PermissionError("Fuente o actor no autorizado")
        if not isinstance(eventos, (list, tuple)) or len(eventos) > MAX_LOTE:
            raise ValueError("Lote inválido o demasiado grande")
        # Validar antes de abrir la transacción y guardar sólo motivos estáticos.
        candidatos = [(raw, *self._normalizar(raw, cfg)) for raw in eventos]
        now = datetime.now(timezone.utc).isoformat()
        resultados = []
        conn = self._conectar()
        try:
            conn.execute("BEGIN IMMEDIATE")
            preparados, conflictos, hashes = [], set(), {}
            for raw, evento, motivo in candidatos:
                if evento is None:
                    preparados.append((raw, evento, motivo, None, None, None))
                    continue
                payload = _json(evento)
                huella = hashlib.sha256(payload.encode()).hexdigest()
                eid = evento["event_id"]
                previo = conn.execute("SELECT huella FROM leads_eventos WHERE cliente_id=? AND source=? AND event_id=?",
                    (cfg["cliente_id"], cfg["source"], eid)).fetchone()
                if (previo and previo[0] != huella) or (eid in hashes and hashes[eid] != huella):
                    conflictos.add(eid)
                hashes[eid] = huella
                preparados.append((raw, evento, motivo, payload, huella, previo))
            lote_rechazado = bool(conflictos) or any(e is None for _, e, _ in candidatos)
            insertados = set()
            for raw, evento, motivo, payload, huella, previo in preparados:
                event_id = raw.get("event_id") if isinstance(raw, dict) and _id(raw.get("event_id")) else None
                resultado = "rechazado"
                if evento is not None:
                    if event_id in conflictos:
                        resultado, motivo = "conflicto", "event_id_contenido_distinto"
                    elif previo or event_id in insertados:
                        resultado, motivo = "duplicado", "replay_identico"
                    elif lote_rechazado:
                        resultado, motivo = "rechazado", "lote_rechazado_sin_eventos_nuevos"
                    else:
                        conn.execute("INSERT INTO leads_eventos VALUES (?,?,?,?,?,?,?,?)", (cfg["cliente_id"], cfg["source"], event_id,
                            payload, huella, actor_id, fuente_key, now))
                        insertados.add(event_id)
                        resultado, motivo = "aceptado", "evento_archivado"
                recibo = str(uuid.uuid4())
                conn.execute("INSERT INTO leads_recibos VALUES (?,?,?,?,?,?,?,?)", (recibo, cfg["cliente_id"], cfg["source"], event_id, actor_id, resultado, motivo, now))
                resultados.append({"recibo_id": recibo, "event_id": event_id, "resultado": resultado, "motivo": motivo})
            conn.commit()
        except sqlite3.Error as exc:
            conn.rollback()
            raise ArchivoError("Lote no confirmado; repetir con los mismos IDs tras comprobar el archivo") from exc
        finally:
            conn.close()
        return {"confirmado": True, "lote_aceptado": not lote_rechazado, "resultados": resultados}

    def exportar(self, clientes_autorizados, incluir_privados=False, clientes_privados_autorizados=None):
        if not isinstance(clientes_autorizados, (set, frozenset, list, tuple)):
            raise PermissionError("Se requiere alcance de clientes autorizado explícito")
        permitidos = set(clientes_autorizados)
        if not all(_public_id(x) for x in permitidos):
            raise PermissionError("Alcance inválido")
        if not isinstance(incluir_privados, bool):
            raise PermissionError("La opción de datos privados debe ser explícita")
        if incluir_privados and (not isinstance(clientes_privados_autorizados, (set, frozenset, list, tuple)) or not permitidos <= set(clientes_privados_autorizados)):
            raise PermissionError("Datos privados requieren alcance adicional autorizado")
        if not permitidos:
            return {"eventos": [], "recibos": []}
        marks = ",".join("?" for _ in permitidos)
        conn = self._conectar()
        try:
            events = conn.execute(f"SELECT payload FROM leads_eventos WHERE cliente_id IN ({marks}) ORDER BY cliente_id,source,event_id", tuple(sorted(permitidos))).fetchall()
            rows = conn.execute(f"SELECT recibo_id,cliente_id,source,event_id,actor_id,resultado,motivo,registrado FROM leads_recibos WHERE cliente_id IN ({marks}) ORDER BY registrado,recibo_id", tuple(sorted(permitidos))).fetchall()
        finally:
            conn.close()
        salida = []
        for row in events:
            event = json.loads(row[0])
            if not incluir_privados:
                event.pop("meta_privados", None)
            salida.append(event)
        columnas = ("recibo_id", "cliente_id", "source", "event_id", "actor_id", "resultado", "motivo", "registrado")
        return {"eventos": salida, "recibos": [dict(zip(columnas, row)) for row in rows]}

    def respaldar(self, destino):
        destino = Path(destino)
        _carpeta_privada(destino)
        if destino.resolve() == self.path.resolve() or destino.exists():
            raise ValueError("El respaldo requiere un destino nuevo distinto del archivo")
        fd = os.open(destino, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(fd)
        src, dst = self._conectar(), sqlite3.connect(str(destino))
        try:
            src.backup(dst)
            if dst.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise ArchivoError("Respaldo sin integridad verificada")
        finally:
            src.close()
            dst.close()
        return {"verificado": True, "destino": str(destino)}

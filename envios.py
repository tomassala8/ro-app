#!/usr/bin/env python3
"""
envios.py · Envíos verificados (3-oct-2026). Encargo de Tomás: «cualquier correo que se envíe, asegurarnos de que se está
enviando bien; también desde la parte de atrás, para asegurarnos de que el sistema nunca está fallando».

HOY TODO VA EN SIMULACIÓN: nada sale de la app. Este fichero deja montado el sistema para que, el día que Tomás active los
envíos, cada uno quede verificado de punta a punta. Se engancha a servir.py como ia.py y avisos.py (envuelve _api_get y
api_post). Sin este fichero, nada cambia.

1. CICLO DE VIDA de cada envío en la base de la app (tablas `envios` y `envio_pasos`, imborrables):
     simulado → pendiente → enviado → confirmado | fallido | rebotado
   con la hora de cada paso, el canal (correo de Desk, WhatsApp, GHL), el destinatario RESUELTO POR EL SERVIDOR desde el
   objeto (ticket de la Bandeja, grupo del cliente, contacto del CRM; nunca una dirección del navegador), quién lo pidió
   y el rastro. Un envío nace de una acción de la cola (`acciones`) de un tipo que manda algo fuera (reglas_permisos.json
   → envios.tipos_envio). Clave única por envío (sha256 de la acción): nunca hay dos envíos de la misma acción.
2. EJECUTAR Y VERIFICAR (solo con los envíos reales activados): manda por el proveedor del canal, relee en la herramienta
   (solo lectura) que el mensaje está en el hilo con el texto y el destinatario correctos, detecta rebotes y errores,
   reintenta UNA vez lo que es seguro reintentar (error de red) y antes de reintentar mira si ya llegó (idempotencia:
   nunca duplica un correo). Si falla, aviso en llano al que lo envió y a Agus en #avisos-dirección (y copia en
   #avisos-altas, que es el canal de Agus, y en el del departamento de quien lo envió).
3. SALUD del sistema de envío (lectura): `conexion_salud()` es la conexión «Envío de correos» de
   despliegue/salud_conexiones.py: token de escritura de Desk, departamento, dirección de envío, firmas y cupo.
4. INTERRUPTOR: data/envios/interruptor.json (envios_reales + canales + activado_por = «tomas») Y la variable de entorno
   RO_ENVIOS_REALES=si al arrancar. Faltando cualquiera de las dos, todo queda «simulado». Ver ../46_ENVIOS_VERIFICADOS.md.

Rutas (permisos en reglas_permisos.json → envios):
  GET  /api/envios[?estado=&canal=]   la cola: cada uno ve los suyos; dirección, operaciones y el técnico (Agus), todos.
                                      El texto, solo si además puede abrir ese cliente. Tasas de confirmados a 7 y 30 días.
  GET  /api/envios/envio?id=N         un envío con todos sus pasos
  POST /api/envios/reintentar {id}    simulado hasta la activación (deja el paso «reintento simulado» y el rastro).
                                      El navegador NUNCA fija estado, destinatario ni remitente: se ignora lo que mande.
"""
import hashlib
import html
import json
import os
import re
import sqlite3
import sys
import threading
import time
import traceback
from datetime import datetime, timedelta, timezone
from pathlib import Path

AQUI = Path(__file__).resolve().parent
DATA = AQUI / "data"
CARPETA = DATA / "envios"
INTERRUPTOR = Path(os.environ.get("RO_ENVIOS_INTERRUPTOR") or CARPETA / "interruptor.json")
CANARIO = Path(os.environ.get("RO_ENVIOS_CANARIO") or CARPETA / "_privado" / "canario.json")
SALUD = DATA / "conexiones" / "salud.json"

ESTADOS = ("simulado", "pendiente", "enviado", "confirmado", "fallido", "rebotado")
FINALES = {"confirmado", "fallido", "rebotado"}
CANALES = {"desk": "Correo (Desk)", "whatsapp": "WhatsApp", "ghl": "GHL"}
# Desk: de dónde sale el correo. Lo decide el servidor (nunca el «de» que mande el navegador en la vista previa).
DESK_API = "https://desk.zoho.eu/api/v1"
DESK_DEPARTAMENTO = "Marketing Clientes"
DESK_REMITENTE = "marketing@rankingonline.com"
GRACIA_MIN = 10            # si a los 10 min el mensaje no aparece en el hilo → fallido (no se reintenta solo: no es seguro)
REVISAR_REBOTES_H = 48     # un rebote puede llegar después de «confirmado»: se sigue mirando 48 h
TIPOS_SEGUROS = {"red", "tiempo", "caida"}          # errores tras los que se puede reintentar UNA vez (tras mirar si llegó)

S = P = None               # servir y permisos, al enganchar
_CANDADO = threading.Lock()

TABLAS_SQL = """
CREATE TABLE IF NOT EXISTS envios (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  clave TEXT NOT NULL UNIQUE,                -- idempotencia: una por envío (sha256 de la acción); el proveedor la recibe
  accion_id INTEGER UNIQUE,                  -- la acción de la cola de la que nace (NULL en canario y pruebas)
  creado TEXT NOT NULL DEFAULT (datetime('now')),
  quien TEXT NOT NULL,
  canal TEXT NOT NULL CHECK (canal IN ('desk','whatsapp','ghl')),
  tipo TEXT NOT NULL,
  objeto TEXT NOT NULL,
  cliente_id TEXT,
  modulo TEXT,
  destinatario TEXT NOT NULL,                -- JSON resuelto por el SERVIDOR (tipo, ref, nombre); nunca una dirección escrita
  remitente TEXT,                            -- JSON: departamento y dirección de envío (los pone el servidor)
  asunto TEXT,
  texto TEXT,
  huella_texto TEXT NOT NULL,
  modo TEXT NOT NULL CHECK (modo IN ('simulado','real','prueba','canario'))
);
CREATE INDEX IF NOT EXISTS i_envios_quien ON envios(quien);
CREATE TABLE IF NOT EXISTS envio_pasos (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  envio_id INTEGER NOT NULL REFERENCES envios(id),
  estado TEXT NOT NULL CHECK (estado IN ('simulado','pendiente','enviado','confirmado','fallido','rebotado')),
  evento TEXT NOT NULL,
  hora TEXT NOT NULL DEFAULT (datetime('now')),
  quien TEXT,
  intento INTEGER NOT NULL DEFAULT 0,
  motivo TEXT,
  detalle TEXT
);
CREATE INDEX IF NOT EXISTS i_envio_pasos ON envio_pasos(envio_id, id);
CREATE TRIGGER IF NOT EXISTS envios_sin_update BEFORE UPDATE ON envios BEGIN SELECT RAISE(ABORT, 'Un envío no se cambia: se añade un paso'); END;
CREATE TRIGGER IF NOT EXISTS envios_sin_delete BEFORE DELETE ON envios BEGIN SELECT RAISE(ABORT, 'Un envío no se borra'); END;
CREATE TRIGGER IF NOT EXISTS envio_pasos_sin_update BEFORE UPDATE ON envio_pasos BEGIN SELECT RAISE(ABORT, 'Un paso no se cambia'); END;
CREATE TRIGGER IF NOT EXISTS envio_pasos_sin_delete BEFORE DELETE ON envio_pasos BEGIN SELECT RAISE(ABORT, 'Un paso no se borra'); END;
"""

# Motivos en llano (lo que lee quien envió y Agus en el aviso).
LLANO = {
    "token": "La llave de envío no vale (caducada o revocada): el mensaje NO ha salido. Lo arregla Tomás renovando la llave; luego se reintenta desde Envíos.",
    "permiso": "La llave de envío entra pero no tiene permiso para mandar: el mensaje NO ha salido. Tomás la renueva con permiso de escritura.",
    "rechazo": "La herramienta ha rechazado el mensaje (datos no válidos): NO ha salido. Revisa el ticket o el contacto.",
    "destinatario": "No sé a quién va: el ticket, el grupo o el contacto no existe ya en la herramienta. NO ha salido.",
    "red": "No se pudo mandar por un fallo de red, también al reintentarlo una vez. No se ha duplicado. Reintenta desde Envíos.",
    "tiempo": "La herramienta no contestó a tiempo, también al reintentarlo una vez. No se ha duplicado. Reintenta desde Envíos.",
    "caida": "La herramienta estaba caída, también al reintentarlo una vez. No se ha duplicado. Reintenta desde Envíos.",
    "rebote": "Ha rebotado: la dirección del contacto no existe o no acepta correo. Revisa el contacto en la herramienta.",
    "no_aparece": "La herramienta dijo que salió, pero a los 10 minutos no aparece en el hilo. No se reintenta solo para no duplicarlo: míralo en la herramienta.",
    "distinto": "Está en el hilo, pero con otro destinatario u otro texto del que se pidió. Míralo en la herramienta antes de hacer nada.",
    "apagado": "Este canal no tiene envío real conectado todavía: el mensaje no ha salido.",
    "canal_apagado": "Este canal no tiene envío real conectado todavía: el mensaje no ha salido.",
    "simulado": "Envíos en simulación: no ha salido nada. Los activa Tomás.",
}


# =================================================================== reloj, base y utilidades
def ahora_utc():
    """Hora UTC (como datetime('now') de la base). RO_RELOJ (hora de Madrid, como servir.py) la fija en pruebas."""
    fijo = os.environ.get("RO_RELOJ")
    if fijo:
        try:
            from zoneinfo import ZoneInfo
            return datetime.fromisoformat(fijo).replace(tzinfo=ZoneInfo("Europe/Madrid")).astimezone(timezone.utc).replace(tzinfo=None)
        except Exception:
            pass
    return datetime.now(timezone.utc).replace(tzinfo=None)


def txt_hora(d):
    return d.strftime("%Y-%m-%d %H:%M:%S")


def leer_hora(t):
    try:
        return datetime.strptime(str(t)[:19], "%Y-%m-%d %H:%M:%S")
    except Exception:
        return None


def iso_z(t):
    return (str(t).replace(" ", "T") + "Z") if t else None


def leer_json(f, defecto=None):
    try:
        return json.loads(Path(f).read_text())
    except Exception:
        return defecto


def ruta_db():
    return Path(os.environ.get("RO_DB") or AQUI / "local.db")


def conectar(db=None):
    if S is not None and db is None:
        return S.conectar()
    con = sqlite3.connect(str(db or ruta_db()), timeout=20)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA busy_timeout=20000")
    return con


def preparar(con):
    con.executescript(TABLAS_SQL)


def huella(texto):
    t = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html.unescape(str(texto or "")))).strip().lower()
    return hashlib.sha256(t.encode()).hexdigest()


def normal(texto):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html.unescape(str(texto or "")))).strip().lower()


def enmascarar(direccion):
    """«m•••@dominio.es»: lo único que se guarda de una dirección real (para comparar se usa su huella)."""
    d = str(direccion or "").strip()
    if "@" not in d:
        return "•••" if d else None
    u, dom = d.split("@", 1)
    return f"{u[:1]}•••@{dom}"


def reglas():
    if P is not None:
        return P.REGLAS.get("envios") or {}
    return (leer_json(AQUI / "reglas_permisos.json", {}) or {}).get("envios") or {}


# =================================================================== interruptor (los activa Tomás)
def interruptor():
    """Estado de los envíos reales. Hacen falta LAS DOS llaves: el fichero (envios_reales, canal activo y activado_por
    «tomas») y la variable RO_ENVIOS_REALES=si en el entorno del servidor o de la tubería."""
    cfg = leer_json(INTERRUPTOR, {}) or {}
    env = os.environ.get("RO_ENVIOS_REALES", "").strip().lower() == "si"
    fichero = bool(cfg.get("envios_reales")) and cfg.get("activado_por") == (reglas().get("activa") or "tomas")
    canales = {c: bool(fichero and env and (cfg.get("canales") or {}).get(c)) for c in CANALES}
    canario = cfg.get("canario") or {}
    return {"reales": any(canales.values()), "canales": canales, "fichero": fichero, "entorno": env,
            "activado_por": cfg.get("activado_por"), "activado_el": cfg.get("activado_el"),
            "canario": {"activo": bool(canario.get("activo")) and canario.get("encendido_por") == "tomas", "hora": canario.get("hora") or "08:00"},
            "texto": ("Envíos reales activos en " + ", ".join(CANALES[c] for c, v in canales.items() if v)) if any(canales.values())
            else "Envíos en simulación · los activa Tomás"}


def canal_real(canal):
    return interruptor()["canales"].get(canal, False)


# =================================================================== qué acciones son envíos y a quién van
def es_envio(herramienta, tipo):
    tipos = (reglas().get("tipos_envio") or {}).get(herramienta) or []
    return herramienta in CANALES and tipo in tipos


def _bandeja():
    return leer_json(DATA / "bandeja" / "bandeja.json", {}) or {}


def resolver_destinatario(canal, objeto):
    """El destinatario lo pone el SERVIDOR desde el objeto. Nunca una dirección o un teléfono: la dirección real se lee
    en la herramienta al enviar (el contacto del ticket en Desk) y aquí solo queda su referencia."""
    objeto = str(objeto or "")
    if canal == "desk":
        d = _bandeja()
        for f in (d.get("correos") or []) + (d.get("triaje") or []):
            if objeto in (str(f.get("id")), str(f.get("numero"))):
                return {"tipo": "ticket", "ref": f.get("numero") or objeto, "nombre": f"Contacto del ticket {f.get('numero') or objeto}",
                        "cliente": f.get("cliente"), "departamento": f.get("departamento"), "resuelto": True}
        return {"tipo": "ticket", "ref": objeto, "nombre": f"Contacto del ticket {objeto}", "resuelto": False}
    if canal == "whatsapp":
        w = leer_json(DATA / "whatsapp" / "whatsapp.json", {}) or {}
        fila = next((f for f in w.get("clientes") or [] if isinstance(f, dict) and f.get("cliente_id") == objeto), None)
        return {"tipo": "grupo", "ref": objeto, "nombre": f"Grupo de WhatsApp de {objeto}", "estado_grupo": (fila or {}).get("estado"),
                "resuelto": bool(fila)}
    if canal == "ghl":
        m = re.search(r"(?:lead|cita|oportunidad|contacto)\s+(\S+)$", objeto)
        ref = m.group(1) if m else objeto
        c = leer_json(DATA / "crm" / "crm.json", {}) or {}
        for lista in ("leads_sin_tocar", "citas_sin_estado", "oportunidades_paradas"):
            for f in c.get(lista) or []:
                if isinstance(f, dict) and str(f.get("ref")) in (ref, objeto):
                    return {"tipo": "contacto", "ref": str(f.get("ref")), "nombre": f"Contacto {f.get('ref')} de {f.get('subcuenta') or 'GHL'}",
                            "subcuenta": f.get("subcuenta"), "resuelto": True}
        return {"tipo": "contacto", "ref": ref, "nombre": f"Contacto {ref} de GHL", "resuelto": False}
    return {"tipo": "desconocido", "ref": objeto, "nombre": objeto, "resuelto": False}


def remitente_de(canal, quien):
    if canal == "desk":
        return {"departamento": DESK_DEPARTAMENTO, "direccion": DESK_REMITENTE, "firma_de": quien}
    if canal == "whatsapp":
        return {"numero": "WhatsApp de RO", "firma_de": quien}
    return {"subcuenta": "la del cliente", "firma_de": quien}


# =================================================================== crear envíos y añadir pasos
def paso(con, envio_id, estado, evento, *, quien="sistema", intento=0, motivo=None, detalle=None, hora=None):
    assert estado in ESTADOS, estado
    con.execute("INSERT INTO envio_pasos (envio_id, estado, evento, hora, quien, intento, motivo, detalle) VALUES (?,?,?,?,?,?,?,?)",
                (envio_id, estado, evento, txt_hora(hora or ahora_utc()), quien, intento, motivo,
                 json.dumps(detalle, ensure_ascii=False) if detalle is not None else None))


def crear_envio(con, *, clave, quien, canal, tipo, objeto, cliente_id=None, modulo=None, asunto=None, texto=None, accion_id=None,
                modo=None, destinatario=None, hora=None):
    """Crea el envío (si su clave no existe) con su primer paso. Devuelve (id, nuevo)."""
    previa = con.execute("SELECT id FROM envios WHERE clave=?", (clave,)).fetchone()
    if previa:
        return previa["id"], False
    modo = modo or ("real" if canal_real(canal) else "simulado")
    dest = destinatario or resolver_destinatario(canal, objeto)
    try:
        cur = con.execute("INSERT INTO envios (clave, accion_id, creado, quien, canal, tipo, objeto, cliente_id, modulo, destinatario, remitente, asunto, texto, huella_texto, modo) "
                          "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                          (clave, accion_id, txt_hora(hora or ahora_utc()), quien, canal, tipo, str(objeto), cliente_id, modulo,
                           json.dumps(dest, ensure_ascii=False), json.dumps(remitente_de(canal, quien), ensure_ascii=False),
                           (asunto or "")[:300] or None, texto, huella(texto), modo))
    except sqlite3.IntegrityError:        # otro hilo o proceso (tubería y servidor) lo creó a la vez: es el mismo envío
        previa = con.execute("SELECT id FROM envios WHERE clave=? OR (accion_id IS NOT NULL AND accion_id=?)", (clave, accion_id)).fetchone()
        return (previa["id"] if previa else None), False
    eid = cur.lastrowid
    if modo == "simulado":
        paso(con, eid, "simulado", "creado", quien=quien, motivo=LLANO["simulado"], hora=hora)
    else:
        paso(con, eid, "pendiente", "en_cola", quien=quien, motivo="En cola para salir: el servidor lo manda y lo comprueba al momento.", hora=hora)
    return eid, True


def sincronizar(con=None):
    """Acciones de la cola que mandan algo fuera → envíos (una por acción; idempotente por la clave)."""
    cerrar = con is None
    con = con or conectar()
    try:
        preparar(con)
        hechos = []
        herrs = tuple(CANALES)
        filas = con.execute(f"SELECT a.* FROM acciones a LEFT JOIN envios e ON e.accion_id = a.id WHERE e.id IS NULL AND a.herramienta IN ({','.join('?' * len(herrs))}) ORDER BY a.id",
                            herrs).fetchall()
        for a in filas:
            if not es_envio(a["herramienta"], a["tipo"]):
                continue
            try:
                vp = json.loads(a["vista_previa"] or "null") or {}
            except ValueError:
                vp = {}
            asunto = vp.get("asunto") if isinstance(vp, dict) else None
            eid, nuevo = crear_envio(con, clave=hashlib.sha256(f"accion:{a['id']}".encode()).hexdigest()[:32], quien=a["quien"],
                                     canal=a["herramienta"], tipo=a["tipo"], objeto=a["objeto"], cliente_id=a["cliente_id"],
                                     modulo=a["modulo"], asunto=asunto, texto=a["texto"], accion_id=a["id"],
                                     hora=leer_hora(a["creada"]) or None)
            if nuevo:
                hechos.append(eid)
        if cerrar:
            con.commit()
        return hechos
    finally:
        if cerrar:
            con.close()


def estado_actual(con, envio_id):
    r = con.execute("SELECT * FROM envio_pasos WHERE envio_id=? ORDER BY id DESC LIMIT 1", (envio_id,)).fetchone()
    return dict(r) if r else None


def pasos_de(con, envio_id):
    return [dict(r) for r in con.execute("SELECT * FROM envio_pasos WHERE envio_id=? ORDER BY id", (envio_id,))]


EVENTOS_NOTA = ("aviso", "reintento_simulado")   # pasos que no cambian nada del envío (solo dejan constancia)


def ultimo_hecho(ps):
    """El último paso que dice algo del envío (no un aviso ni un reintento simulado)."""
    return next((x for x in reversed(ps) if x["evento"] not in EVENTOS_NOTA), ps[-1] if ps else {})


def intentos_de(con, envio_id):
    return con.execute("SELECT count(*) FROM envio_pasos WHERE envio_id=? AND evento IN ('enviado','error_envio','reintento_envio')", (envio_id,)).fetchone()[0]


# =================================================================== proveedores
class ErrorEnvio(Exception):
    """tipo: token | permiso | rechazo | destinatario | apagado | red | tiempo | caida."""
    def __init__(self, tipo, texto=""):
        super().__init__(texto or tipo)
        self.tipo = tipo


class Proveedor:
    """Contrato de un proveedor de canal. buscar() y leer() SOLO leen; enviar() es lo único que escribe."""
    nombre = "base"
    real = False

    def buscar(self, envio):                 # ¿ya está en el hilo? → {"encontrado", "id_externo"}
        raise NotImplementedError

    def enviar(self, envio):                 # → {"id_externo"} o ErrorEnvio
        raise NotImplementedError

    def leer(self, envio):                   # → {"encontrado", "texto_ok", "destinatario_ok", "rebote", "destinatario_mascara"}
        raise NotImplementedError


class ProveedorSimulado(Proveedor):
    """Proveedor FALSO para las pruebas de extremo a extremo: un buzón en memoria. Nunca toca nada de fuera.
    guion = {clave_envio: {"enviar": ["red" | "red_pero_entregado" | "token" | "ok", …], "rebote": bool, "otro_destino": bool,
                           "perdido": bool}}"""
    nombre = "simulado"

    def __init__(self, guion=None):
        self.guion = guion or {}
        self.buzon = []          # mensajes que de verdad «llegaron»: {"clave", "texto", "destino", "rebote"}
        self.llamadas = []       # (operación, clave)

    def _g(self, envio):
        return self.guion.get(envio["clave"]) or {}

    def buscar(self, envio):
        self.llamadas.append(("buscar", envio["clave"]))
        m = [x for x in self.buzon if x["clave"] == envio["clave"]]
        return {"encontrado": bool(m), "id_externo": f"sim-{envio['id']}" if m else None}

    def enviar(self, envio):
        self.llamadas.append(("enviar", envio["clave"]))
        g = self._g(envio)
        guion = g.setdefault("_restante", list(g.get("enviar") or ["ok"]))
        accion = guion.pop(0) if guion else "ok"
        if accion == "token":
            raise ErrorEnvio("token", "401 · token caducado")
        if accion == "red":
            raise ErrorEnvio("red", "conexión cortada antes de llegar")
        destino = "otra" if g.get("otro_destino") else "contacto"
        if not g.get("perdido"):
            self.buzon.append({"clave": envio["clave"], "texto": envio.get("texto"), "destino": destino, "rebote": bool(g.get("rebote"))})
        if accion == "red_pero_entregado":
            raise ErrorEnvio("red", "conexión cortada DESPUÉS de llegar (no se sabe si salió)")
        return {"id_externo": f"sim-{envio['id']}"}

    def leer(self, envio):
        self.llamadas.append(("leer", envio["clave"]))
        m = [x for x in self.buzon if x["clave"] == envio["clave"]]
        if not m:
            return {"encontrado": False}
        x = m[-1]
        return {"encontrado": True, "texto_ok": huella(x["texto"]) == envio["huella_texto"], "destinatario_ok": x["destino"] == "contacto",
                "rebote": "rebote" if x["rebote"] else None, "destinatario_mascara": "c•••@cliente.es"}


class ProveedorDesk(Proveedor):
    """Zoho Desk con la llave de ESCRITURA (zoho_refresh_token_escritura, la de ~/RO_HERRAMIENTAS/zoho/zh_escribir.py).
    enviar() solo funciona con el canal «desk» activado (interruptor + RO_ENVIOS_REALES=si). buscar() y leer() leen."""
    nombre = "desk"
    real = True

    def __init__(self):
        self._tk = None
        self._org = None
        self._tickets = {}

    # -- llave y llamadas
    def token(self):
        if self._tk:
            return self._tk
        tk, _scope = token_escritura()
        self._tk = tk
        return tk

    def pide(self, metodo, ruta, cuerpo=None, lectura=True):
        import urllib.error
        import urllib.request
        if metodo != "GET" and not canal_real("desk"):
            raise ErrorEnvio("permiso", "envíos reales apagados: no se escribe en Desk")
        h = {"Authorization": "Zoho-oauthtoken " + self.token(), "Content-Type": "application/json"}
        if self._org:
            h["orgId"] = self._org
        req = urllib.request.Request(DESK_API + ruta, method=metodo, headers=h,
                                     data=json.dumps(cuerpo).encode() if cuerpo is not None else None)
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                cuerpo_r = r.read().decode() or "null"
                return json.loads(cuerpo_r)
        except urllib.error.HTTPError as e:
            raise ErrorEnvio({401: "token", 403: "permiso", 404: "destinatario", 400: "rechazo", 422: "rechazo", 429: "caida"}.get(e.code, "caida" if e.code >= 500 else "rechazo"),
                             f"Desk responde {e.code}")
        except (TimeoutError, OSError) as e:
            raise ErrorEnvio("tiempo" if "timed out" in str(e) else "red", type(e).__name__)

    def org(self):
        if not self._org:
            self._org = str(self.pide("GET", "/organizations")["data"][0]["id"])
        return self._org

    def ticket(self, envio):
        num = str(json.loads(envio["destinatario"]).get("ref") or envio["objeto"])
        if num in self._tickets:
            return self._tickets[num]
        self.org()
        n = re.sub(r"\D", "", num)
        d = self.pide("GET", f"/tickets/search?ticketNumber={n}&limit=1")
        t = ((d or {}).get("data") or [None])[0]
        if not t:
            raise ErrorEnvio("destinatario", f"no encuentro el ticket {num}")
        c = self.pide("GET", f"/contacts/{t['contactId']}") if t.get("contactId") else {}
        self._tickets[num] = {"id": t["id"], "departmentId": t.get("departmentId"), "correo": (c or {}).get("email") or t.get("email")}
        if not self._tickets[num]["correo"]:
            raise ErrorEnvio("destinatario", f"el ticket {num} no tiene correo de contacto")
        return self._tickets[num]

    def hilos(self, envio, desde=None):
        t = self.ticket(envio)
        d = self.pide("GET", f"/tickets/{t['id']}/threads?limit=30&from=0")
        out = []
        for x in (d or {}).get("data") or []:
            creado = str(x.get("createdTime") or "")[:19].replace("T", " ")
            if desde and creado and creado < desde:
                continue
            out.append(x)
        return t, out

    def _contenido(self, t, x):
        try:
            return self.pide("GET", f"/tickets/{t['id']}/threads/{x['id']}").get("content") or x.get("summary") or ""
        except ErrorEnvio:
            return x.get("summary") or ""

    def buscar(self, envio):
        r = self.leer(envio)
        return {"encontrado": r.get("encontrado", False), "id_externo": r.get("id_externo")}

    def enviar(self, envio):
        t = self.ticket(envio)
        desde = self.pide("GET", f"/mailReplyAddress?departmentId={t['departmentId']}").get("data") or []
        de = next((x["address"] for x in desde if DESK_REMITENTE in (x.get("address") or "")), None)
        if not de:
            raise ErrorEnvio("rechazo", "la dirección de envío de marketing no está en el departamento del ticket")
        cuerpo = {"channel": "EMAIL", "to": t["correo"], "fromEmailAddress": de, "contentType": "html",
                  "content": html.escape(envio.get("texto") or "").replace("\n", "<br>") + f"<span style=\"display:none\">ro-envio:{envio['clave'][:16]}</span>"}
        r = self.pide("POST", f"/tickets/{t['id']}/sendReply", cuerpo)
        return {"id_externo": (r or {}).get("id")}

    def leer(self, envio):
        t, hs = self.hilos(envio, desde=str(envio.get("creado") or "")[:19])
        marca = f"ro-envio:{envio['clave'][:16]}"
        propio, rebote = None, None
        for x in hs:
            remitente = str(x.get("fromEmailAddress") or x.get("author", {}).get("email") or "").lower()
            resumen = str(x.get("summary") or "")
            if x.get("direction") == "in" and (re.search(r"mailer-daemon|postmaster", remitente)
                                              or re.search(r"(?i)undeliver|delivery status|no se (ha )?pod(ido|ía) entregar|returned mail|failure notice", resumen)):
                rebote = "rebote"
            if x.get("direction") == "out" and propio is None:
                cont = self._contenido(t, x)
                if marca in cont or normal(envio.get("texto"))[:120] in normal(cont):
                    propio = (x, cont)
            if str(x.get("status") or "").upper() == "FAILED" and x.get("direction") == "out":
                rebote = rebote or "fallo_envio"
        if not propio:
            return {"encontrado": False, "rebote": rebote}
        x, cont = propio
        a = str(x.get("to") or "").lower()
        return {"encontrado": True, "id_externo": x.get("id"), "texto_ok": huella(envio.get("texto")) == huella(re.sub(re.escape(marca), "", cont)) or normal(envio.get("texto"))[:120] in normal(cont),
                "destinatario_ok": t["correo"].lower() in a, "rebote": rebote, "destinatario_mascara": enmascarar(t["correo"])}


class ProveedorApagado(Proveedor):
    """WhatsApp y GHL: hoy no hay envío real conectado. Nada sale; el envío queda «fallido · canal sin conectar»."""
    nombre = "apagado"

    def buscar(self, envio):
        return {"encontrado": False}

    def enviar(self, envio):
        raise ErrorEnvio("apagado", LLANO["canal_apagado"])

    def leer(self, envio):
        return {"encontrado": False}


def proveedor_de(canal):
    return ProveedorDesk() if canal == "desk" else ProveedorApagado()


def token_escritura():
    """(token de acceso, permisos concedidos) con la llave de escritura de Desk. Usa la caché compartida de tokens de 1 h
    (~/RO_HERRAMIENTAS/cache_tokens.py) para no gastar el cupo de tokens de Zoho. Nunca se imprime ni se guarda."""
    import urllib.parse
    import urllib.request
    herr = Path(os.environ.get("RO_HERRAMIENTAS") or Path.home() / "RO_HERRAMIENTAS")
    for d in (herr, herr / "zoho"):
        if str(d) not in sys.path:
            sys.path.append(str(d))
    import zh  # noqa: E402  (lector de solo lectura; aquí solo para leer las llaves del llavero)
    llave = zh.llave("zoho_refresh_token_escritura")

    def refrescar():
        datos = urllib.parse.urlencode({"grant_type": "refresh_token", "refresh_token": llave, "client_id": zh.llave("zoho_client_id"),
                                        "client_secret": zh.llave("zoho_client_secret")}).encode()
        with urllib.request.urlopen(urllib.request.Request(zh.ACC + "/oauth/v2/token", data=datos, method="POST"), timeout=30) as r:
            d = json.loads(r.read().decode())
        if "access_token" not in d:
            raise ErrorEnvio("token", f"Zoho rechaza la llave de escritura: {d.get('error')}")
        return d["access_token"], int(d.get("expires_in") or 3600), d.get("scope") or ""
    try:
        import cache_tokens as CT
        return CT.token("zoho_escritura", llave, refrescar)
    except ImportError:
        tk, _vida, scope = refrescar()
        return tk, scope


# =================================================================== ejecutar, verificar y avisar
def fila_envio(con, envio_id):
    r = con.execute("SELECT * FROM envios WHERE id=?", (envio_id,)).fetchone()
    return dict(r) if r else None


def ejecutar(con, envio_id, prov, quien="sistema"):
    """pendiente → enviado (y verificación al momento). Idempotente: antes de cada intento mira si ya está en el hilo;
    reintenta UNA vez solo los errores seguros (red, tiempo, caída); nunca reintenta llave, permiso ni rechazo."""
    e = fila_envio(con, envio_id)
    act = estado_actual(con, envio_id)
    if not e or not act or act["estado"] != "pendiente":
        return act and act["estado"]
    if getattr(prov, "real", False) and not canal_real(e["canal"]):        # un proveedor de verdad nunca escribe con el canal apagado
        paso(con, envio_id, "fallido", "apagado", quien=quien, motivo=LLANO["canal_apagado"])
        return "fallido"
    max_reintentos = int(reglas().get("reintentos_max", 1))
    intento = 0
    while True:
        ya = prov.buscar(e)                                   # idempotencia: ¿ya llegó (p. ej. tras un corte a medias)?
        if ya.get("encontrado"):
            paso(con, envio_id, "enviado", "ya_estaba", quien=quien, intento=intento,
                 motivo="Ya estaba en el hilo: no se vuelve a mandar (sin duplicar).", detalle={"id_externo": ya.get("id_externo")})
            break
        try:
            r = prov.enviar(e)
            paso(con, envio_id, "enviado", "enviado", quien=quien, intento=intento, motivo="La herramienta lo ha aceptado. Se comprueba en el hilo.",
                 detalle={"id_externo": (r or {}).get("id_externo"), "proveedor": prov.nombre})
            break
        except ErrorEnvio as x:
            if x.tipo in TIPOS_SEGUROS and intento < max_reintentos:
                paso(con, envio_id, "pendiente", "error_envio", quien=quien, intento=intento,
                     motivo=f"Fallo de {x.tipo}: se mira si llegó y, si no, se reintenta una vez.", detalle={"tipo": x.tipo})
                intento += 1
                continue
            if x.tipo in TIPOS_SEGUROS:                        # último intento: ¿llegó a pesar del error?
                ya = prov.buscar(e)
                if ya.get("encontrado"):
                    paso(con, envio_id, "enviado", "ya_estaba", quien=quien, intento=intento,
                         motivo="El último intento dio error, pero el mensaje está en el hilo: no se duplica.")
                    break
            paso(con, envio_id, "fallido", "error_envio", quien=quien, intento=intento, motivo=LLANO.get(x.tipo, LLANO["rechazo"]),
                 detalle={"tipo": x.tipo, "seguro_reintentar": x.tipo in TIPOS_SEGUROS})
            avisar(con, envio_id, x.tipo)
            return "fallido"
    return verificar(con, envio_id, prov)


def verificar(con, envio_id, prov, ahora=None):
    """enviado → confirmado | fallido | rebotado, releyendo en la herramienta (solo lectura). Los confirmados de las
    últimas 48 h se vuelven a mirar por si llega un rebote tarde."""
    e = fila_envio(con, envio_id)
    act = estado_actual(con, envio_id)
    if not e or not act:
        return None
    ahora = ahora or ahora_utc()
    if act["estado"] not in ("enviado", "confirmado"):
        return act["estado"]
    if act["estado"] == "confirmado":
        if (ahora - (leer_hora(act["hora"]) or ahora)).total_seconds() > REVISAR_REBOTES_H * 3600:
            return "confirmado"
    try:
        r = prov.leer(e)
    except ErrorEnvio as x:
        if x.tipo in ("token", "permiso"):
            avisar(con, envio_id, "verificar_" + x.tipo, solo_agus=True)
        return act["estado"]
    if r.get("rebote"):
        paso(con, envio_id, "rebotado", "rebote", motivo=LLANO["rebote"], detalle={"señal": r["rebote"]})
        avisar(con, envio_id, "rebote")
        return "rebotado"
    if act["estado"] == "confirmado":
        return "confirmado"
    if r.get("encontrado"):
        if r.get("texto_ok") and r.get("destinatario_ok"):
            paso(con, envio_id, "confirmado", "verificado", motivo="Está en el hilo con el texto y el destinatario correctos.",
                 detalle={"destinatario": r.get("destinatario_mascara"), "id_externo": r.get("id_externo")})
            return "confirmado"
        paso(con, envio_id, "fallido", "distinto", motivo=LLANO["distinto"],
             detalle={"texto_ok": bool(r.get("texto_ok")), "destinatario_ok": bool(r.get("destinatario_ok")), "seguro_reintentar": False})
        avisar(con, envio_id, "distinto")
        return "fallido"
    enviado_h = leer_hora(act["hora"]) or ahora
    if (ahora - enviado_h).total_seconds() >= GRACIA_MIN * 60:
        paso(con, envio_id, "fallido", "no_aparece", motivo=LLANO["no_aparece"], detalle={"seguro_reintentar": False})
        avisar(con, envio_id, "no_aparece")
        return "fallido"
    return "enviado"


def _publicar(con, canal_id, texto, clave, *, menciones=(), cliente_id=None, ver=None, datos=None):
    """Mensaje en un canal de avisos (tabla de avisos.py). Idempotente por clave. Si avisos.py está cargado, usa el suyo."""
    av = sys.modules.get("avisos")
    try:
        if av and hasattr(av, "publicar") and getattr(av, "S", None) is not None:
            return av.publicar(con, canal_id, "evento", texto, clave, quien=None, menciones=list(menciones), cliente_id=cliente_id,
                               dueno_id="agustina", ver=ver, datos=datos)
        if not con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='canal_mensajes'").fetchone():
            return None
        if con.execute("SELECT 1 FROM canal_mensajes WHERE clave=?", (clave,)).fetchone():
            return None
        cur = con.execute("INSERT INTO canal_mensajes (canal_id, tipo, quien, texto, menciones, clave, cliente_id, dueno_id, ver, datos, creado) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                          (canal_id, "evento", None, texto, json.dumps(list(menciones)), clave, cliente_id, "agustina",
                           json.dumps(ver) if ver is not None else None, json.dumps(datos, ensure_ascii=False) if datos else None, txt_hora(ahora_utc())))
        return cur.lastrowid
    except Exception:
        traceback.print_exc()
        return None


# Puesto → canal de avisos de su departamento (el mismo reparto de avisos.py, para avisar a quien envió).
DEP_AVISOS = {"account": "avisos-accounts", "tecnico_altas": "avisos-altas", "especialista_ghl": "avisos-crm", "jefa_crm": "avisos-crm",
              "outreach": "avisos-crm", "trafficker": "avisos-publicidad", "jefa_publicidad": "avisos-publicidad", "jefa_seo": "avisos-seo",
              "seo": "avisos-seo", "ficha_google": "avisos-seo", "web": "avisos-web", "redes": "avisos-redes", "produccion": "avisos-redes",
              "administracion": "avisos-administracion", "rrhh": "avisos-rrhh"}


def _persona(pid):
    if S is not None:
        return S.E.persona(pid) or {}
    for p in leer_json(DATA / "personas.json", []) or []:
        if p.get("id") == pid:
            return p
    return {}


def _cliente_nombre(cid):
    if not cid:
        return None
    for c in (S.E.crudo["clientes"] if S is not None else leer_json(DATA / "clientes.json", []) or []):
        if c.get("id") == cid:
            return c.get("nombre")
    return cid


def avisar(con, envio_id, tipo, solo_agus=False):
    """Aviso en llano a quien lo envió y a Agus en #avisos-dirección; copia en #avisos-altas (canal de Agus: hoy no es
    miembro de #avisos-dirección y solo Tomás la puede añadir) y en el canal del departamento de quien envió. Nunca lleva
    la dirección ni el texto del mensaje. Idempotente: un aviso por envío y motivo."""
    e = fila_envio(con, envio_id)
    if not e:
        return []
    conf = reglas()
    quien = _persona(e["quien"])
    alias = quien.get("alias") or e["quien"]
    dest = json.loads(e["destinatario"] or "{}")
    cli = _cliente_nombre(e["cliente_id"])
    que = {"verificar_token": "No puedo comprobar los envíos: la llave de envío no vale",
           "verificar_permiso": "No puedo comprobar los envíos: a la llave le falta permiso"}.get(tipo)
    if que:
        texto = f"{que}. Los envíos ya salidos no se pueden confirmar hasta que Tomás la renueve. Agus: mira Conexiones › Envío de correos."
    else:
        texto = (f"{CANALES[e['canal']]} de {alias} a «{dest.get('nombre') or e['objeto']}»" + (f" ({cli})" if cli else "")
                 + f" · {'ha rebotado' if tipo == 'rebote' else 'no ha salido bien'}: {LLANO.get(tipo, LLANO['rechazo'])} Envío n.º {envio_id}.")
    avisar_a = [x for x in (conf.get("avisar_a") or ["agustina"])]
    menciones = list(dict.fromkeys(([e["quien"]] if not solo_agus else []) + avisar_a))
    ver = {"puestos": conf.get("ven_todos_puestos") or ["direccion", "operaciones", "tecnico_altas"]}
    datos = {"icono": "alert", "ir": f"#/envios/{envio_id}", "envio_id": envio_id, "motivo": tipo}
    hechos = []
    canales = [conf.get("canal_avisos") or "avisos-direccion", conf.get("canal_avisos_copia") or "avisos-altas"]
    for canal in canales:
        if _publicar(con, canal, texto, f"envio:{envio_id}:{tipo}:{canal}", menciones=menciones, ver=ver, datos=datos):
            hechos.append(canal)
    if not solo_agus:
        dep = next((DEP_AVISOS[x] for x in quien.get("puestos") or [] if x in DEP_AVISOS), None)
        if dep and dep not in canales and _publicar(con, dep, texto, f"envio:{envio_id}:{tipo}:{dep}", menciones=[e["quien"]],
                                                    cliente_id=e["cliente_id"], datos=datos):
            hechos.append(dep)
    if hechos:
        paso(con, envio_id, estado_actual(con, envio_id)["estado"], "aviso", motivo=f"Avisados {alias if not solo_agus else ''} y Agus en " + ", ".join("#" + c for c in hechos),
             detalle={"canales": hechos, "menciones": menciones})
    return hechos


def reintentar(con, envio_id, quien, prov=None):
    """Reintento pedido por una persona. Con los envíos apagados: SOLO deja el paso «reintento simulado» (nada sale).
    Con el canal activo: solo un fallido que sea seguro reintentar; vuelve a «pendiente» y se ejecuta (mirando antes si
    ya llegó: nunca duplica)."""
    e = fila_envio(con, envio_id)
    act = estado_actual(con, envio_id)
    if not e or not act:
        return {"ok": False, "codigo": 404, "error": "No existe ese envío."}
    if e["modo"] == "simulado" or not canal_real(e["canal"]):
        paso(con, envio_id, act["estado"], "reintento_simulado", quien=quien,
             motivo="Reintento simulado: los envíos reales están apagados (los activa Tomás). No ha salido nada.")
        return {"ok": True, "simulado": True, "estado": act["estado"]}
    if act["estado"] != "fallido":
        return {"ok": False, "codigo": 409, "error": "Solo se reintenta un envío fallido."}
    hecho = ultimo_hecho(pasos_de(con, envio_id))
    ultimo = json.loads(hecho.get("detalle") or "{}") if hecho.get("detalle") else {}
    if not ultimo.get("seguro_reintentar"):
        return {"ok": False, "codigo": 409, "error": "Este fallo no es seguro reintentarlo (llave, rechazo, rebote o ya en el hilo con otros datos): míralo en la herramienta."}
    paso(con, envio_id, "pendiente", "reintento_pedido", quien=quien, motivo="Reintento pedido desde Envíos.")
    prov = prov or proveedor_de(e["canal"])
    return {"ok": True, "simulado": False, "estado": ejecutar(con, envio_id, prov, quien=quien)}


def vuelta(con, provs=None, ahora=None):
    """Lo que hace la tubería (despliegue/verificar_envios.py): sincroniza, ejecuta pendientes de canales activos y
    verifica enviados (y confirmados < 48 h). Con todo apagado solo sincroniza y cuenta."""
    preparar(con)
    nuevos = sincronizar(con)
    hechos = {"nuevos": len(nuevos), "ejecutados": 0, "verificados": 0, "cambios": []}
    provs = provs or {}
    ultimos = con.execute("SELECT e.id, e.canal, e.modo, (SELECT estado FROM envio_pasos p WHERE p.envio_id=e.id ORDER BY p.id DESC LIMIT 1) AS estado "
                          "FROM envios e WHERE e.modo != 'simulado'").fetchall()
    for r in ultimos:
        prov = provs.get(r["canal"]) if provs else None
        if prov is None:
            if not canal_real(r["canal"]):
                continue
            prov = provs.setdefault(r["canal"], proveedor_de(r["canal"]))
        antes = r["estado"]
        if antes == "pendiente":
            despues = ejecutar(con, r["id"], prov)
            hechos["ejecutados"] += 1
        elif antes in ("enviado", "confirmado"):
            despues = verificar(con, r["id"], prov, ahora=ahora)
            hechos["verificados"] += 1
        else:
            continue
        if despues != antes:
            hechos["cambios"].append({"id": r["id"], "de": antes, "a": despues})
    return hechos


def resumen(con, dias=None, quien=None):
    preparar(con)
    filas = con.execute("SELECT e.id, e.modo, e.creado, e.quien, (SELECT estado FROM envio_pasos p WHERE p.envio_id=e.id ORDER BY p.id DESC LIMIT 1) AS estado FROM envios e").fetchall()
    return {"total": len(filas), "por_estado": {s: sum(1 for f in filas if f["estado"] == s) for s in ESTADOS},
            "tasas": {str(d): tasa(filas, d) for d in (7, 30)}}


def tasa(filas, dias, ahora=None):
    ahora = ahora or ahora_utc()
    lim = ahora - timedelta(days=dias)
    reales = [f for f in filas if f["modo"] in ("real", "canario") and (leer_hora(f["creado"]) or ahora) >= lim]
    terminados = [f for f in reales if f["estado"] in FINALES]
    conf = sum(1 for f in terminados if f["estado"] == "confirmado")
    return {"dias": dias, "reales": len(reales), "terminados": len(terminados), "confirmados": conf,
            "fallidos": sum(1 for f in terminados if f["estado"] == "fallido"), "rebotados": sum(1 for f in terminados if f["estado"] == "rebotado"),
            "en_curso": len(reales) - len(terminados),
            "simulados": sum(1 for f in filas if f["modo"] == "simulado" and (leer_hora(f["creado"]) or ahora) >= lim),
            "pct": round(100 * conf / len(terminados), 1) if terminados else None}


# =================================================================== canario (solo con el sí de Tomás)
def canario(con, prov=None, ahora=None):
    """Envío de prueba DIARIO a una dirección interna que elige Tomás, verificado de punta a punta. Solo corre si: canal
    «desk» activo (interruptor + RO_ENVIOS_REALES=si), canario.activo = true y encendido_por = «tomas» en el
    interruptor, y data/envios/_privado/canario.json tiene la dirección (y su ticket de pruebas). Uno al día."""
    it = interruptor()
    cfg = leer_json(CANARIO, {}) or {}
    if not (it["canario"]["activo"] and it["canales"].get("desk")):
        return {"corre": False, "motivo": "Canario apagado: lo enciende Tomás (interruptor.canario.activo + encendido_por: tomas) con los envíos de Desk activos."}
    if not cfg.get("ticket"):
        return {"corre": False, "motivo": "Falta el ticket de pruebas del canario en data/envios/_privado/canario.json (lo crea Agus con la dirección que elija Tomás)."}
    dia = (ahora or ahora_utc()).strftime("%Y-%m-%d")
    preparar(con)
    eid, nuevo = crear_envio(con, clave=hashlib.sha256(f"canario:{dia}".encode()).hexdigest()[:32], quien="sistema", canal="desk",
                             tipo="canario", objeto=str(cfg["ticket"]), asunto=f"Canario de envíos {dia}", modo="canario",
                             texto=f"Canario diario de la app de RO ({dia}). Si lees esto, el envío de correos funciona de punta a punta.",
                             destinatario={"tipo": "ticket", "ref": str(cfg["ticket"]), "nombre": "Buzón interno del canario", "resuelto": True})
    if not nuevo:
        return {"corre": False, "motivo": f"El canario de hoy ya salió (envío n.º {eid}).", "envio_id": eid, "estado": estado_actual(con, eid)["estado"]}
    est = ejecutar(con, eid, prov or ProveedorDesk())
    return {"corre": True, "envio_id": eid, "estado": est}


# =================================================================== salud: conexión «Envío de correos»
def conexion_salud(pedir, secreto):
    """La conexión «Envío de correos» para despliegue/salud_conexiones.py (solo lectura): llave de escritura de Desk y sus
    permisos, departamento «Marketing Clientes», dirección de envío de marketing, firmas de quien contesta y cupo."""
    def prueba():
        t0 = time.time()
        tk, scope = token_escritura()
        h = {"Authorization": "Zoho-oauthtoken " + tk}
        orgs, cab, ms_desk = pedir(DESK_API + "/organizations", h)   # el tiempo que se enseña: el de Desk (como las demás)
        h["orgId"] = str(((orgs or {}).get("data") or [{}])[0].get("id"))
        deps, cab2, _ = pedir(DESK_API + "/departments?limit=50", h)
        dep = next((d for d in (deps or {}).get("data") or [] if str(d.get("name", "")).startswith(DESK_DEPARTAMENTO)), None)
        if not dep:
            raise RuntimeError(f"No existe el departamento «{DESK_DEPARTAMENTO}» en Desk: los correos no tendrían de dónde salir.")
        dirs, _, _ = pedir(DESK_API + f"/mailReplyAddress?departmentId={dep['id']}", h)
        if not any(DESK_REMITENTE in (x.get("address") or "") for x in (dirs or {}).get("data") or []):
            raise RuntimeError("La dirección de envío de marketing no está dada de alta en «Marketing Clientes».")
        ags, cab3, _ = pedir(DESK_API + "/agents?limit=100&status=ACTIVE", h)
        quienes = {str(p.get("correo") or "").lower(): p for p in leer_json(DATA / "personas.json", []) or []
                   if p.get("activo") and set(p.get("puestos") or []) & {"account", "direccion", "operaciones", "tecnico_altas"}}
        import concurrent.futures as cf
        suyos = [(a, quienes[str(a.get("emailId") or "").lower()]) for a in (ags or {}).get("data") or [] if str(a.get("emailId") or "").lower() in quienes]
        with cf.ThreadPoolExecutor(max_workers=8) as ex:     # una lectura por persona, a la vez (antes ~17 s en fila)
            firmas = list(ex.map(lambda ap: bool((pedir(DESK_API + f"/agents/{ap[0]['id']}/signatures", h)[0] or {}).get("customizedSignatures")), suyos))
        con_firma = sum(firmas)
        sin_firma = [p.get("alias") or p.get("nombre") for (_a, p), f in zip(suyos, firmas) if not f]
        escribe = any(x in (scope or "") for x in ("Desk.tickets.ALL", "Desk.tickets.UPDATE", "Desk.tickets.CREATE"))
        if scope and not escribe:
            e = RuntimeError("La llave de envío no tiene permiso de escritura en tickets (Desk.tickets.ALL).")
            e.code = 403
            raise e
        cupo = next((f"{k}: {v}" for c in (cab3, cab2, cab) for k, v in (c or {}).items() if "limit" in k.lower() and "remaining" in k.lower()), None)
        partes = ["llave de escritura válida" + (" con permiso de escritura en tickets" if escribe else " (permisos no informados: los confirma el canario)"),
                  f"departamento «{DESK_DEPARTAMENTO}» y dirección de envío de marketing en orden",
                  f"firma: {con_firma} de {con_firma + len(sin_firma)} personas que contestan" + (f" (sin firma: {', '.join(sin_firma[:6])})" if sin_firma else ""),
                  ("cupo · " + cupo) if cupo else "cupo diario de Desk según plan (no lo informa)",
                  "hoy " + ("con envíos reales" if interruptor()["reales"] else "en simulación (los activa Tomás)")]
        partes.append(f"comprobación entera en {time.time() - t0:.1f} s")
        out = {"ms": ms_desk, "detalle": " · ".join(partes)}
        if sin_firma:
            out["aviso_firma"] = sin_firma
        return out

    reales = interruptor()["canales"].get("desk", False)
    return dict(id="envio_correos", nombre="Envío de correos (Desk)", grupo="Zoho", icono="send",
                llaves=["zoho_refresh_token_escritura", "zoho_client_id", "zoho_client_secret"], prueba=prueba, dueno="tomas",
                critica=reales, que_da="mandar correos desde la app (hoy en simulación) y comprobar que llegan",
                modulos="Envíos, Bandeja (contestar)" + ("" if reales else " · hoy en simulación"),
                renovar={"url": "https://api-console.zoho.eu/", "donde": "Self Client › Generate Code con Desk.tickets.ALL, Desk.basic.READ y Desk.settings.READ (llave de escritura)"},
                pegar="python3 ~/RO_HERRAMIENTAS/zoho/zh_escribir.py canjear (antes, el código de 10 min en el llavero como zoho_grant_code_escritura)",
                caducidad="llave permanente · token de acceso de 1 h que se renueva solo", limite="cupo diario de Desk según plan")


def salud_envio():
    try:
        d = json.loads(SALUD.read_text())
        c = next((x for x in d.get("conexiones") or [] if x.get("id") == "envio_correos"), None)
        if c:
            return {k: c.get(k) for k in ("color", "titular", "detalle", "que_hacer", "quien", "ultima_prueba", "ultimo_ok")}
    except Exception:
        pass
    return None


# =================================================================== API (enganche a servir.py)
def ve_todos(p):
    return bool(set(p.get("puestos") or []) & set(reglas().get("ven_todos_puestos") or []))


def puede_reintentar(p, e):
    return e["quien"] == p["id"] or bool(set(p.get("puestos") or []) & set(reglas().get("reintentan_puestos") or []))


def _visible(real, persona, e):
    """Nadie ve envíos ajenos: los suyos, o todos si su puesto lo dice. En «ver como», lo que ven LAS DOS personas."""
    return all(e["quien"] == x["id"] or ve_todos(x) for x in (real, persona))


def _abre_cliente(persona, cid):
    if not cid:
        return True
    cp = P.contexto(persona, S.E.crudo)
    return P.ver(persona, {"tipo": "cliente_detalle", "cliente_id": cid}, cp)["ok"]


def a_json(con, e, real, persona, con_pasos=True):
    ps = pasos_de(con, e["id"])
    act = ps[-1] if ps else {}
    dest = json.loads(e["destinatario"] or "{}")
    ver_texto = _abre_cliente(persona, e["cliente_id"]) and _abre_cliente(real, e["cliente_id"])
    hecho = ultimo_hecho(ps)
    ultimo_motivo = hecho.get("motivo")
    detalle = json.loads(hecho.get("detalle") or "{}") if hecho.get("detalle") else {}
    q = _persona(e["quien"])
    return {
        "id": e["id"], "creado": iso_z(e["creado"]), "quien": e["quien"], "quien_alias": q.get("alias") or e["quien"],
        "canal": e["canal"], "canal_nombre": CANALES[e["canal"]], "tipo": e["tipo"], "modo": e["modo"], "modulo": e["modulo"],
        "cliente_id": e["cliente_id"], "cliente": _cliente_nombre(e["cliente_id"]) if ver_texto else None,
        "destinatario": {k: dest.get(k) for k in ("tipo", "ref", "nombre", "resuelto")},
        "asunto": e["asunto"] if ver_texto else None, "texto": e["texto"] if ver_texto else None, "texto_oculto": not ver_texto,
        "estado": act.get("estado"), "desde": iso_z(act.get("hora")), "motivo": ultimo_motivo,
        "intentos": sum(1 for x in ps if x["evento"] in ("enviado", "error_envio", "ya_estaba")),
        "avisado": any(x["evento"] == "aviso" for x in ps),
        "seguro_reintentar": bool(detalle.get("seguro_reintentar")),
        "puede_reintentar": puede_reintentar(real, e) and real["id"] == persona["id"],
        "pasos": [{"estado": x["estado"], "evento": x["evento"], "hora": iso_z(x["hora"]), "quien": x["quien"], "intento": x["intento"],
                   "motivo": x["motivo"]} for x in ps] if con_pasos else None,
    }


def _get(h, ruta, q, real, persona):
    with conectar() as con:
        preparar(con)
        with _CANDADO:
            sincronizar(con)
            con.commit()                 # que nada de esta lectura deje una escritura abierta mientras se responde
        filas = [dict(r) for r in con.execute("SELECT * FROM envios ORDER BY id DESC")]
        vis = [e for e in filas if _visible(real, persona, e)]
        if ruta == "/api/envios/envio":
            try:
                eid = int((q.get("id") or ["0"])[0])
            except ValueError:
                return h.responder(400, {"error": "«id» tiene que ser un número."})
            e = next((x for x in filas if x["id"] == eid), None)
            if not e or not _visible(real, persona, e):
                return h.responder(403 if e else 404, {"error": "Ese envío no es tuyo." if e else "No existe ese envío."})
            return h.responder(200, {"envio": a_json(con, e, real, persona)})
        estado = (q.get("estado") or [""])[0]
        canal = (q.get("canal") or [""])[0]
        lista = [a_json(con, e, real, persona) for e in vis[:500]]
        if estado:
            lista = [x for x in lista if x["estado"] == estado]
        if canal:
            lista = [x for x in lista if x["canal"] == canal]
        crudas = [{"modo": x["modo"], "creado": x["creado"].replace("T", " ").rstrip("Z"), "estado": x["estado"]} for x in lista]
        it = interruptor()
        return h.responder(200, {
            "modo": {"reales": it["reales"], "canales": it["canales"], "texto": it["texto"], "activa": "Tomás",
                     "como": "Hacen falta dos llaves: el interruptor de la app (data/envios/interruptor.json, lo firma Tomás) y RO_ENVIOS_REALES=si en el servidor."},
            "canario": {"activo": it["canario"]["activo"], "texto": "Canario encendido: un correo de prueba diario a un buzón interno, verificado de punta a punta."
                        if it["canario"]["activo"] else "Canario apagado: un correo de prueba diario a un buzón interno que elige Tomás. Solo se enciende con su sí."},
            "salud": salud_envio(),
            "ve_todos": ve_todos(real) and ve_todos(persona), "solo_lectura": real["id"] != persona["id"],
            "tasas": {str(d): tasa(crudas, d) for d in (7, 30)},
            "por_estado": {s: sum(1 for x in lista if x["estado"] == s) for s in ESTADOS},
            "envios": lista,
        })


def _post(h, ruta, real, persona, b):
    if real["id"] != persona["id"]:
        return h.responder(403, {"error": "Estás en «ver como»: es solo lectura. No se escribe nada."})
    if ruta != "/api/envios/reintentar":
        return h.responder(404, {"error": "No existe esa ruta de Envíos. Un envío solo nace de una acción de la cola."})
    try:
        eid = int(b.get("id"))
    except (TypeError, ValueError):
        return h.responder(400, {"error": "«id» tiene que ser un número."})
    # Lo único que manda el navegador es el id: estado, destinatario, remitente o texto se IGNORAN (los pone el servidor).
    # El rastro (S.registrar) abre su propia transacción: se escribe DESPUÉS de cerrar la nuestra (si no, se esperan).
    denegado, r, e = False, None, None
    with _CANDADO:
        with conectar() as con:
            preparar(con)
            e = fila_envio(con, eid)
            if e and (not _visible(real, persona, e) or not puede_reintentar(real, e)):
                denegado = True
            elif e:
                r = reintentar(con, eid, real["id"])
            con.commit()
    if not e:
        return h.responder(404, {"error": "No existe ese envío."})
    if denegado:
        S.registrar_agrupado(real["id"], "envios", "denegado", str(eid), {"motivo": "reintentar un envío ajeno"})
        return h.responder(403, {"error": "Ese envío no es tuyo: lo reintenta quien lo mandó, Agus, Mili o Tomás."})
    if not r.get("ok"):
        return h.responder(r.get("codigo", 400), {"error": r["error"]})
    S.registrar(real["id"], "envios", "envio_reintento_simulado" if r.get("simulado") else "envio_reintento", str(eid),
                {"envio_id": eid, "canal": e["canal"], "estado": r.get("estado"), "ignorado": sorted(k for k in b if k != "id")[:8]})
    with conectar() as con:
        return h.responder(200, {"ok": True, "simulado": r.get("simulado"), "envio": a_json(con, e, real, persona),
                                 "mensaje": "Reintento simulado: los envíos los activa Tomás. No ha salido nada." if r.get("simulado") else "Reintento hecho."})


def _tras_accion(ruta, b):
    """Tras cada acción de la cola: si es un envío, nace su fila; con el canal activo, sale y se verifica al momento."""
    if ruta != "/api/acciones" or not es_envio(str(b.get("herramienta") or ""), str(b.get("tipo") or "")):
        return
    try:
        with _CANDADO, conectar() as con:
            preparar(con)
            nuevos = sincronizar(con)
        if nuevos and canal_real(str(b.get("herramienta"))):
            threading.Thread(target=_al_momento, args=(nuevos,), daemon=True).start()
    except Exception:
        traceback.print_exc()


def _al_momento(ids):
    """Envío real: sale y se comprueba en el hilo AL MOMENTO (y otra vez a los 2 y 10 min si aún no aparece)."""
    provs = {}
    for espera in (0, 120, GRACIA_MIN * 60 + 5):
        time.sleep(espera)
        with _CANDADO, conectar() as con:
            for eid in ids:
                e = fila_envio(con, eid)
                if not e or e["modo"] != "real":
                    continue
                prov = provs.setdefault(e["canal"], proveedor_de(e["canal"]))
                est = estado_actual(con, eid)["estado"]
                if est == "pendiente":
                    ejecutar(con, eid, prov)
                elif est == "enviado":
                    verificar(con, eid, prov)
            if all(estado_actual(con, i)["estado"] in FINALES for i in ids):
                return


def enganchar(Manejador, servir):
    """Envuelve _api_get y api_post (como ia.py, avisos.py y altas_personas.py). Sin este fichero, nada cambia."""
    global S, P
    S, P = servir, servir.P
    with S.conectar() as con:
        preparar(con)
    get_orig, post_orig = Manejador._api_get, Manejador.api_post

    def _api_get(self, ruta, q, real, persona_):
        if ruta == "/api/envios" or ruta.startswith("/api/envios/"):
            if S.E.nucleo_bloqueado:
                return self.responder(503, {"error": "La puerta de secretos ha encontrado algo en los datos."})
            try:
                return _get(self, ruta, q, real, persona_)
            except Exception:
                if os.environ.get("RO_ENVIOS_TRAZA"):
                    Path(os.environ["RO_ENVIOS_TRAZA"]).write_text(traceback.format_exc())
                raise
        return get_orig(self, ruta, q, real, persona_)

    def api_post(self, ruta, real, persona_, b):
        if ruta.startswith("/api/envios"):
            return _post(self, ruta, real, persona_, b)
        r = post_orig(self, ruta, real, persona_, b)
        if real["id"] == persona_["id"]:
            _tras_accion(ruta, b)
        return r

    Manejador._api_get = _api_get
    Manejador.api_post = api_post

#!/usr/bin/env python3
"""
fuentes_modular/acceso.py · «Entrar al WordPress» desde la app (N5 Modular DS, 3-oct-2026).

Encargo de Tomás: «para el equipo de web el acceso a Modular de todos ellos». La API pública de Modular DS tiene
POST /sites/{id}/login: crea un enlace de UN SOLO USO (10 minutos) que entra al escritorio del WordPress sin contraseña.
Es una ESCRITURA en Modular (queda en su registro de actividad) y la clave que hay hoy es de SOLO LECTURA, así que:

  · La ruta existe y aplica todos los permisos, pero NO llama a Modular salvo que Tomás lo encienda a propósito:
      data/modular/interruptor.json → {"acceso_real": true, "activado_por": "tomas"}  +  RO_MODULAR_ACCESO=si en el entorno
      + una clave aparte con permiso de entrada en el llavero/secretos: «modulards_acceso_key» (nunca la de solo lectura).
    Apagado, responde 200 con {ok: false, apagado: true, texto} y la pantalla dice por qué y ofrece «Abrir en Modular ↗».
  · Solo la pide quien tenga el tipo «modular_acceso» (reglas_permisos.json: web, jefe de SEO y web, dirección), nunca en
    «ver como», solo para una web que esté en data/modular/webs.json, y como mucho 10 por persona y hora.
  · Cada petición deja rastro imborrable (modular_acceso / modular_acceso_denegado, solo servidor) con la web y el
    resultado. El enlace NO se guarda ni se escribe en ningún registro: va solo en la respuesta a esa persona.

Ruta:  POST /api/modular/acceso {modular_id}
Se engancha a servir.py como vigia.py (envuelve api_post). Sin este fichero, nada cambia.
"""
import json
import os
import re
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

AQUI = Path(__file__).resolve().parent
APP = AQUI.parent
WEBS = APP / "data" / "modular" / "webs.json"
INTERRUPTOR = APP / "data" / "modular" / "interruptor.json"
BASE = "https://api.modulards.com/api/public/v1"
LLAVE_ACCESO = "modulards_acceso_key"
TOPE_HORA = 10
RX_ID = re.compile(r"^\d{1,12}$")
_USO = {}
_CANDADO = threading.Lock()
APAGADO = ("El acceso de un clic está apagado: la clave de Modular de la app es de solo lectura y crear el enlace es una "
           "escritura en Modular. Mientras, «Abrir en Modular ↗» y entrar desde allí. Lo enciende Tomás (interruptor y clave aparte).")


def _leer(p, defecto=None):
    try:
        return json.loads(Path(p).read_text())
    except Exception:
        return defecto


def encendido():
    i = _leer(INTERRUPTOR, {}) or {}
    return bool(i.get("acceso_real") and i.get("activado_por") == "tomas" and os.environ.get("RO_MODULAR_ACCESO") == "si")


def _clave():
    d = os.environ.get("RO_SECRETOS_DIR")
    if d and (Path(d) / LLAVE_ACCESO).is_file():
        v = (Path(d) / LLAVE_ACCESO).read_text().strip()
        if v:
            return v
    v = (os.environ.get(LLAVE_ACCESO.upper()) or "").strip()
    if v:
        return v
    try:
        import pathlib as _pl_n14, sys as _sys_n14      # N-14: llavero por config.secreto()
        if str(_pl_n14.Path(__file__).resolve().parents[1]) not in _sys_n14.path:
            _sys_n14.path.append(str(_pl_n14.Path(__file__).resolve().parents[1]))
        import config as _cfg
        return _cfg.secreto(LLAVE_ACCESO) or None
    except Exception:
        return None


def _web(mid):
    doc = _leer(WEBS, {}) or {}
    for w in (doc.get("webs") or []) + (doc.get("sin_cliente") or []):
        if str(w.get("modular_id")) == mid:
            return w
    return None


def _tope(pid):
    ahora = time.time()
    with _CANDADO:
        L = [t for t in _USO.get(pid, []) if ahora - t < 3600]
        if len(L) >= TOPE_HORA:
            _USO[pid] = L
            return False
        L.append(ahora)
        _USO[pid] = L
        return True


def _pedir_enlace(mid):
    req = urllib.request.Request(f"{BASE}/sites/{mid}/login", data=b"{}", method="POST",
                                 headers={"Authorization": "Bearer " + (_clave() or ""), "Accept": "application/json",
                                          "Content-Type": "application/json", "User-Agent": "RO-modular/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            meta = (json.loads(r.read().decode() or "{}").get("meta") or {})
            return meta.get("login_url"), meta.get("expires_at"), None
    except urllib.error.HTTPError as e:
        return None, None, {400: "La web no está conectada o no tiene usuario de WordPress sincronizado.",
                            401: "La clave de acceso de Modular no vale.", 403: "La clave de Modular no permite crear accesos (es de solo lectura).",
                            404: "Tu usuario de Modular no puede entrar en esta web.", 503: "Modular no puede dar el enlace ahora: prueba en un momento."
                            }.get(e.code, f"Modular respondió {e.code}.")
    except urllib.error.URLError:
        return None, None, "Sin conexión con Modular DS."


def enganchar(Manejador, servir):
    S = servir
    post_orig = Manejador.api_post

    def api_post(self, ruta, real, persona, b):
        if ruta != "/api/modular/acceso":
            return post_orig(self, ruta, real, persona, b)
        mid = str((b or {}).get("modular_id") or "")
        if persona["id"] != real["id"]:
            return self.responder(403, {"error": "Estás en «ver como»: es solo lectura. No se pide ningún acceso."})
        cp = S.P.contexto(persona, S.E.crudo)
        if not S.P.ver(persona, {"tipo": "modular_acceso"}, cp)["ok"]:
            S.registrar_agrupado(real["id"], "modular", "modular_acceso_denegado", mid[:20] or None, {"motivo": "puesto sin acceso"})
            return self.responder(403, {"error": S.P.REGLAS["tipos"]["modular_acceso"]["no"]})
        if not RX_ID.match(mid):
            return self.responder(400, {"error": "Falta la web (modular_id)."})
        w = _web(mid)
        if not w:
            return self.responder(404, {"error": "Esa web no está en Modular DS (según la última lectura)."})
        if not _tope(real["id"]):
            S.registrar_agrupado(real["id"], "modular", "modular_acceso_denegado", mid, {"motivo": "tope por hora"})
            return self.responder(429, {"error": f"Como mucho {TOPE_HORA} accesos por hora: espera un poco."})
        datos = {"web": w.get("dominio"), "cliente_id": w.get("cliente_id")}
        if not encendido() or not _clave():
            S.registrar(real["id"], "modular", "modular_acceso", mid, {**datos, "resultado": "apagado"})
            return self.responder(200, {"ok": False, "apagado": True, "corto": "Acceso de un clic apagado", "texto": APAGADO,
                                        "panel": w.get("enlace_modular") or "https://app.modulards.com/"})
        url, caduca, error = _pedir_enlace(mid)
        S.registrar(real["id"], "modular", "modular_acceso", mid, {**datos, "resultado": "enlace" if url else "error", "error": error})
        if not url or not S.P.enlace_seguro(url):
            return self.responder(502, {"error": error or "Modular no ha dado un enlace válido."})
        return self.responder(200, {"ok": True, "url": url, "caduca": caduca})

    Manejador.api_post = api_post

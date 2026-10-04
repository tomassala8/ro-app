#!/usr/bin/env python3
"""
llamadas.py · videollamadas y llamadas de teléfono desde la app (encargo de Tomás, 3-oct-2026).

Lo usa avisos.py (rutas /api/canales/videollamada, /api/canales/llamar y /api/canales/llamadas). Interruptores en
data/llamadas.json (solo Tomás). Recomendación, riesgos y pasos en ../59_LLAMADAS_Y_VIDEOLLAMADAS.md.

Videollamada (equipo):
  · Hoy: Jitsi público (meet.jit.si) en una PESTAÑA NUEVA, sin coste. Sala con nombre aleatorio largo (128 bits), nunca
    con nombres de clientes ni personas en la dirección. La primera persona que entra se identifica con Google, GitHub o
    Facebook (norma de meet.jit.si); las demás entran con el enlace.
  · Dentro de la app (incrustada): solo con un Jitsi propio (Coolify en el servidor de RO) o JaaS. Apagado:
    video.incrustado_activo=false. meet.jit.si incrustado corta a los 5 minutos: por eso no se usa incrustado.
Videollamada con un cliente: enlace de Zoom (RO ya paga Zoom). Crear la reunión por API, apagado (video.zoom_api_activa).
Teléfono: «te llamo y te conecto» con la API de Zadarma (/v1/request/callback/): Zadarma llama primero a la extensión de
quien pulsa y, cuando descuelga, al cliente. Hoy SIMULADO: se apunta la acción (estado «simulada») y no se llama a nadie.
Encender: telefono.callback_activo=true + activado_por=tomas + RO_ZADARMA_CALLBACK=si + claves de Zadarma (Tomás).
"""
import json
import os
import re
import secrets
import unicodedata
from pathlib import Path

AQUI = Path(__file__).resolve().parent
DATA = AQUI / "data"
RUTA = Path(os.environ.get("RO_LLAMADAS") or DATA / "llamadas.json")
RX_SALA = re.compile(r"^RO[0-9a-f]{32}$")


def config():
    try:
        return json.loads(RUTA.read_text())
    except (OSError, ValueError):
        return {"video": {"proveedor": "jitsi_publico", "dominio": "meet.jit.si", "modo": "pestana", "incrustado_activo": False},
                "telefono": {"callback_activo": False}}


def _norm(t):
    return "".join(c for c in unicodedata.normalize("NFD", str(t or "").lower()) if unicodedata.category(c) != "Mn")


# =================================================================== videollamada
def sala_nueva():
    """Nombre de sala aleatorio y largo (RO + 32 cifras hexadecimales = 128 bits). Nunca lleva nombres."""
    return "RO" + secrets.token_hex(16)


def video():
    """Lo que la pantalla necesita saber (sin claves)."""
    v = config().get("video") or {}
    incr = bool(v.get("incrustado_activo")) and v.get("activado_por") == "tomas" and bool(v.get("incrustado_dominio"))
    return {"proveedor": v.get("proveedor") or "jitsi_publico", "dominio": (v.get("incrustado_dominio") if incr else v.get("dominio")) or "meet.jit.si",
            "incrustado": incr, "con_clientes": v.get("con_clientes") or "zoom_enlace",
            "zoom_api": bool(v.get("zoom_api_activa")) and v.get("activado_por") == "tomas"}


def enlace_sala(sala):
    if not RX_SALA.match(str(sala or "")):
        raise ValueError("sala no válida")
    return f"https://{video()['dominio']}/{sala}"


# =================================================================== teléfono (Zadarma)
def extensiones():
    """{persona_id: extensión} sacado del panel de Zadarma (data/paneles/empresa/zadarma.json → extensiones {ext: nombre}).
    Se empareja por el nombre de pila con las personas ACTIVAS; lo que no cuadra no se usa."""
    try:
        ext = (json.loads((DATA / "paneles" / "empresa" / "zadarma.json").read_text()).get("extensiones") or {})
        personas = json.loads((DATA / "personas.json").read_text())
    except (OSError, ValueError):
        return {}
    out = {}
    for num, nombre in ext.items():
        n = _norm(nombre).split("-")[0].strip()
        cand = [p for p in personas if p.get("activo") and (p.get("estado") or "activo") == "activo"
                and n in (_norm((p.get("nombre") or "").split(" ")[0]), _norm(p.get("alias")))]
        if len(cand) == 1 and str(num).isdigit():
            out[cand[0]["id"]] = str(num)
    return out


def telefono_activo():
    t = config().get("telefono") or {}
    return bool(t.get("callback_activo")) and t.get("activado_por") == "tomas" and os.environ.get("RO_ZADARMA_CALLBACK") == "si"


def tapar_numero(tel):
    t = str(tel or "")
    return (t[:6] + "·" * max(0, len(t) - 8) + t[-2:]) if len(t) > 8 else "··"


def telefonos_de_cliente(cid):
    """Teléfonos que la app tiene de ese cliente (contactos de la ficha, almacén privado). Solo esos se pueden marcar."""
    try:
        doc = json.loads((DATA / "ficha" / "_privado" / "contactos.json").read_text())
    except (OSError, ValueError):
        return set()
    d = ((doc.get("clientes") or {}).get(cid) or {}).get("datos") or {}
    out = {t.get("tel") for p in d.get("personas") or [] for t in p.get("telefonos") or [] if t.get("tel")}
    for f in d.get("fijos") or []:
        if isinstance(f, dict) and f.get("tel"):
            out.add(f["tel"])
        elif isinstance(f, str):
            out.add(f)
    return {x for x in out if isinstance(x, str)}


def plan_callback(pid, telefono):
    """Lo que haría Zadarma (sin hacerlo): parámetros del método /v1/request/callback/ (from = extensión, to = cliente)."""
    ext = extensiones().get(pid)
    return {"metodo": "/v1/request/callback/", "from": ext, "to": telefono, "predicted": None}


if __name__ == "__main__":
    print("Sala de ejemplo:", sala_nueva())
    print("Vídeo:", video())
    print("Extensiones:", extensiones())
    print("Callback encendido:", telefono_activo())

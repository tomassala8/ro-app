#!/usr/bin/env python3
"""despliegue/acceso_cf.py · valida el sello de Cloudflare Access en cada petición (error E49 del documento 26).

En el servidor (RO_MODO=servidor), servir.py SOLO cree a Cloudflare Access: la cabecera Cf-Access-Jwt-Assertion
(o la galleta CF_Authorization) es un JWT firmado con RS256 por el equipo de Cloudflare de RO. Se comprueba:
  · la firma, con las claves públicas del equipo (https://<equipo>.cloudflareaccess.com/cdn-cgi/access/certs,
    guardadas 1 h en memoria y recargadas si llega un «kid» nuevo);
  · la audiencia (RO_CF_AUD = la «Application Audience (AUD) Tag» de la aplicación de Access);
  · el emisor (https://<equipo>.cloudflareaccess.com), la caducidad y el «no antes de», con 60 s de margen;
  · y que lleva correo. De ahí sale la persona; ?yo=, X-RO-Yo y la galleta ro_yo NO valen en el servidor.
Sin sello válido → 403. Así, aunque alguien encuentre la dirección *.onrender.com, no entra (y además se
desactiva en Render: ver DESPLIEGUE.md).

Sin dependencias: la firma RS256 (RSASSA-PKCS1-v1_5 con SHA-256) se comprueba con la biblioteca estándar.
Fuente: https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/authorization-cookie/validating-json/

Variables:  RO_MODO=servidor · RO_CF_EQUIPO=<nombre del equipo de Zero Trust> · RO_CF_AUD=<etiqueta AUD>
Pruebas:    RO_CF_CERTS_FICHERO=<jwks.json local> (en vez de pedir las claves a Cloudflare)
"""
import base64
import hashlib
import hmac
import json
import os
import threading
import time
import urllib.request

_CLAVES = {}          # kid → (n, e)
_HASTA = 0.0
_CANDADO = threading.Lock()
MARGEN_S = 60
# DigestInfo de SHA-256 (RFC 8017, 9.2, nota 1)
_PREFIJO_SHA256 = bytes.fromhex("3031300d060960864801650304020105000420")


def activo():
    return os.environ.get("RO_MODO") == "servidor"


def _b64(s):
    s = s.encode() if isinstance(s, str) else s
    return base64.urlsafe_b64decode(s + b"=" * (-len(s) % 4))


def _entero(s):
    return int.from_bytes(_b64(s), "big")


def emisor():
    return f"https://{os.environ.get('RO_CF_EQUIPO', '')}.cloudflareaccess.com"


_ULTIMA_FORZADA = 0.0
RECARGA_MIN_S = 60       # R16 (B3): un «kid» desconocido recarga las claves como mucho una vez por minuto


def _cargar_claves(forzar=False):
    """Claves públicas del equipo. R16 (B3): un «kid» inventado no provoca una petición a Cloudflare en cada visita
    (como mucho una por minuto) y un fallo de red al pedirlas se controla: se siguen usando las que había."""
    global _CLAVES, _HASTA, _ULTIMA_FORZADA
    with _CANDADO:
        if _CLAVES and not forzar and time.time() < _HASTA:
            return _CLAVES
        if forzar and _CLAVES and time.time() - _ULTIMA_FORZADA < RECARGA_MIN_S:
            return _CLAVES
        if forzar:
            _ULTIMA_FORZADA = time.time()
        try:
            fichero = os.environ.get("RO_CF_CERTS_FICHERO")
            if fichero:
                with open(fichero) as fh:
                    jwks = json.load(fh)
            else:
                with urllib.request.urlopen(emisor() + "/cdn-cgi/access/certs", timeout=10) as r:
                    jwks = json.load(r)
            nuevas = {k["kid"]: (_entero(k["n"]), _entero(k["e"])) for k in jwks.get("keys", []) if k.get("kty") == "RSA"}
        except Exception:
            _HASTA = time.time() + RECARGA_MIN_S            # se reintenta en un minuto
            return _CLAVES
        if nuevas:
            _CLAVES = nuevas
            _HASTA = time.time() + 3600
        return _CLAVES


def _firma_valida(firmado, firma, n, e):
    k = (n.bit_length() + 7) // 8
    if len(firma) != k:
        return False
    em = pow(int.from_bytes(firma, "big"), e, n).to_bytes(k, "big")
    t = _PREFIJO_SHA256 + hashlib.sha256(firmado).digest()
    esperado = b"\x00\x01" + b"\xff" * (k - len(t) - 3) + b"\x00" + t
    return hmac.compare_digest(em, esperado)


def verificar(token):
    """(payload, None) si el sello vale; (None, motivo) si no."""
    aud = os.environ.get("RO_CF_AUD")
    if not aud or not os.environ.get("RO_CF_EQUIPO"):
        return None, "El servidor no tiene RO_CF_EQUIPO y RO_CF_AUD: no puede comprobar Access (no entra nadie)."
    try:
        cab, carga, firma = token.split(".")
        h = json.loads(_b64(cab))
        p = json.loads(_b64(carga))
        sig = _b64(firma)
    except Exception:
        return None, "Sello de Access mal formado."
    if h.get("alg") != "RS256":
        return None, "Sello de Access con un algoritmo no admitido."
    claves = _cargar_claves()
    if h.get("kid") not in claves:
        claves = _cargar_claves(forzar=True)          # Cloudflare rota sus claves: se recargan una vez
    if h.get("kid") not in claves:
        return None, "Sello de Access firmado con una clave desconocida."
    n, e = claves[h["kid"]]
    if not _firma_valida(f"{cab}.{carga}".encode(), sig, n, e):
        return None, "La firma del sello de Access no es válida."
    ahora = time.time()
    auds = p.get("aud") if isinstance(p.get("aud"), list) else [p.get("aud")]
    if aud not in auds:
        return None, "El sello de Access es de otra aplicación."
    if p.get("iss") != emisor():
        return None, "El sello de Access es de otro equipo de Cloudflare."
    if not p.get("exp") or p["exp"] < ahora - MARGEN_S:
        return None, "El sello de Access ha caducado: vuelve a entrar."
    if p.get("nbf") and p["nbf"] > ahora + MARGEN_S:
        return None, "El sello de Access aún no vale."
    if not p.get("email"):
        return None, "El sello de Access no trae correo (¿token de servicio?)."
    return p, None


def token_de(cabeceras):
    t = cabeceras.get("Cf-Access-Jwt-Assertion")
    if t:
        return t
    for trozo in (cabeceras.get("Cookie") or "").split(";"):
        if trozo.strip().startswith("CF_Authorization="):
            return trozo.strip().split("=", 1)[1]
    return None


def correo_validado(cabeceras):
    """(correo, None) o (None, motivo). Es lo único que servir.py usa en modo servidor."""
    t = token_de(cabeceras)
    if not t:
        return None, "Falta el sello de Cloudflare Access: entra por la dirección de la app."
    p, motivo = verificar(t)
    return (p["email"].lower(), None) if p else (None, motivo)

#!/usr/bin/env python3
"""despliegue/seguridad_nube.py · comprueba desde fuera que la app en la nube está cerrada (4-oct-2026).

Lo lanza Tomás (o Claude) desde cualquier ordenador SIN haber entrado en la app, después de cada despliegue:
  python3 despliegue/seguridad_nube.py --dominio panel.<dominio> --render ro-web-xxxx.onrender.com [--render …]

Comprueba, sin llaves y sin tocar nada:
  1. http:// redirige a https:// y la respuesta lleva HSTS.
  2. La app y su API piden entrar por Cloudflare Access: sin sesión, redirige al login de Access o da 401/403;
     nunca datos. (Cabeceras falsas tampoco valen: X-RO-Yo, ?yo=, X-Forwarded-For, el correo de Access a mano.)
  3. Las direcciones *.onrender.com no dan datos (deberían estar desactivadas, T8; si responden, la API tiene que
     negarse porque no llega el sello firmado de Access).
  4. Cloudflare va delante (cabecera cf-ray): sin él no hay WAF ni protección contra DDoS.
Sale con 1 si algo falla. No prueba el segundo factor: eso se comprueba entrando con una cuenta sin él (ver PLAN §2.12).
"""
import argparse
import sys
import urllib.error
import urllib.request

FALSAS = {"X-RO-Yo": "tomas", "X-Forwarded-For": "127.0.0.1", "Cf-Access-Authenticated-User-Email": "tomas@example.com",
          "Cookie": "ro_yo=tomas"}


class SinSeguir(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


ABRIR = urllib.request.build_opener(SinSeguir)


def pedir(url, cabeceras=None):
    req = urllib.request.Request(url, headers={"User-Agent": "ro-seguridad-nube", **(cabeceras or {})})
    try:
        with ABRIR.open(req, timeout=20) as r:
            return r.status, dict(r.headers), r.read(4000)
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read(4000)
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        return 0, {}, str(e).encode()


def cerrada(estado, cab, cuerpo):
    """Bien si no hay datos: redirección al login de Access, 401/403/404, o no responde."""
    destino = {k.lower(): v for k, v in cab.items()}.get("location", "")
    if estado in (301, 302, 303, 307, 308):
        return "cloudflareaccess.com" in destino or "/cdn-cgi/access/" in destino
    return estado in (0, 401, 403, 404, 405, 421, 502, 503)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dominio", required=True, help="panel.<dominio>, sin https://")
    ap.add_argument("--render", action="append", default=[], help="cada dirección *.onrender.com (web, api…)")
    a = ap.parse_args()
    fallos, d = [], a.dominio.strip("/")

    def mira(bien, texto):
        print(f"  {'✔' if bien else '✘'} {texto}")
        if not bien:
            fallos.append(texto)

    e, c, _ = pedir(f"http://{d}/")
    mira(e in (301, 302, 307, 308) and str({k.lower(): v for k, v in c.items()}.get("location", "")).startswith("https://"),
         f"http:// redirige a https:// ({e})")
    e, c, _ = pedir(f"https://{d}/")
    cl = {k.lower(): v for k, v in c.items()}
    mira("cf-ray" in cl, "Cloudflare va delante (cf-ray)")
    mira("strict-transport-security" in cl or e in (301, 302, 303, 307, 308), "HSTS o redirección a Access en la portada")
    for ruta in ("/", "/api/sesion", "/api/elegir", "/api/rastro", "/api/modulo/crm"):
        mira(cerrada(*pedir(f"https://{d}{ruta}")), f"sin sesión, {ruta} no da datos")
        mira(cerrada(*pedir(f"https://{d}{ruta}?yo=tomas", FALSAS)), f"con cabeceras falsas, {ruta} no da datos")
    for r in a.render:
        r = r.replace("https://", "").strip("/")
        for ruta in ("/api/sesion", "/api/elegir"):
            mira(cerrada(*pedir(f"https://{r}{ruta}", FALSAS)), f"{r}{ruta} (saltándose Cloudflare) no da datos")
    print(f"\n{'VERDE' if not fallos else 'ROJO'} · {len(fallos)} fallos")
    sys.exit(1 if fallos else 0)


if __name__ == "__main__":
    main()

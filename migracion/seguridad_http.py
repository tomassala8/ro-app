#!/usr/bin/env python3
"""migracion/seguridad_http.py · la app nueva es al menos tan segura como la de hoy, vista desde fuera.

  python3 migracion/seguridad_http.py --viejo http://127.0.0.1:8770 --nuevo http://127.0.0.1:3000

ROJO si la nueva:
  · pierde una cabecera de seguridad que la de hoy manda (CSP, X-Frame-Options, X-Content-Type-Options,
    Referrer-Policy, Permissions-Policy, Cache-Control en /api) o la debilita (valor distinto);
  · anuncia el servidor (X-Powered-By, Server con versión);
  · sirve algo que la de hoy no sirve: ficheros del repositorio (.py, .db, .env, .git, data/, despliegue/, migracion/);
  · responde a quien no se ha identificado algo que la de hoy deniega.
"""
import argparse
import sys
import urllib.error
import urllib.request

CABECERAS = ["content-security-policy", "x-frame-options", "x-content-type-options", "referrer-policy",
             "permissions-policy", "cross-origin-opener-policy", "strict-transport-security"]
SENSIBLES = ["/servir.py", "/local.db", "/.env", "/.git/config", "/data/clientes/", "/despliegue/base.py",
             "/migracion/PLAN_MAESTRO.md", "/reglas_permisos.json", "/fuentes_crm/_privado/", "/v2/.env",
             "/api/../servir.py", "/%2e%2e/servir.py", "/legacy/../servir.py"]
SIN_IDENTIFICAR = ["/api/sesion", "/api/perfil", "/api/indicadores", "/api/avisos", "/api/rastro"]


def pedir(base, ruta, cabeceras=None):
    req = urllib.request.Request(base.rstrip("/") + ruta, headers=cabeceras or {})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, {k.lower(): v for k, v in r.headers.items()}
    except urllib.error.HTTPError as e:
        return e.code, {k.lower(): v for k, v in e.headers.items()}
    except urllib.error.URLError as e:
        sys.exit(f"No responde {base}{ruta}: {e.reason}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--viejo", required=True)
    ap.add_argument("--nuevo", required=True)
    a = ap.parse_args()
    malos = []
    for ruta in ["/", "/api/sesion"]:
        _, hv = pedir(a.viejo, ruta)
        _, hn = pedir(a.nuevo, ruta)
        for c in CABECERAS:
            if c in hv and hv[c] != hn.get(c):
                malos.append(f"{ruta}: cabecera {c} {'falta' if c not in hn else 'cambia'} (hoy: {hv[c][:80]})")
        if ruta.startswith("/api") and "cache-control" in hv and hv["cache-control"] != hn.get("cache-control"):
            malos.append(f"{ruta}: Cache-Control cambia ({hv['cache-control']} → {hn.get('cache-control')})")
        if "x-powered-by" in hn:
            malos.append(f"{ruta}: anuncia X-Powered-By: {hn['x-powered-by']}")
        if any(ch.isdigit() for ch in hn.get("server", "")) and hn.get("server") != hv.get("server"):
            malos.append(f"{ruta}: anuncia la versión del servidor ({hn['server']})")
    for ruta in SENSIBLES:
        ev, _ = pedir(a.viejo, ruta)
        en, _ = pedir(a.nuevo, ruta)
        if en == 200 and ev != 200:
            malos.append(f"{ruta}: la nueva lo sirve (200) y la de hoy no ({ev})")
    for ruta in ["/data/_privado/x.json", "/local.db", "/api/sesion"]:
        req = urllib.request.Request(a.nuevo.rstrip("/") + ruta, method="HEAD")
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                malos.append(f"HEAD {ruta}: la nueva responde {r.status} (debe ser 405: HEAD se salta identidad y permisos, L-07)")
        except urllib.error.HTTPError as e:
            if e.code < 400:
                malos.append(f"HEAD {ruta}: {e.code}")
    for ruta in SIN_IDENTIFICAR:
        ev, _ = pedir(a.viejo, ruta)
        en, _ = pedir(a.nuevo, ruta)
        if en < 400 <= ev:
            malos.append(f"{ruta} sin identificarse: hoy {ev}, la nueva {en}")
    for m in malos:
        print("  ✘ " + m)
    if malos:
        sys.exit(1)
    print(f"Cabeceras, ficheros sensibles ({len(SENSIBLES)}) y accesos sin identificar: igual de seguro que hoy o más.")


if __name__ == "__main__":
    main()

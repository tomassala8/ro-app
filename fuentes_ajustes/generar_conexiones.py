#!/usr/bin/env python3
"""M22 Ajustes › Conexiones y avisos · genera data/ajustes/conexiones.json (formato de M22).

N11 (2-oct-2026): este fichero YA NO LLAMA A NINGUNA API. La única comprobación en vivo es la de
despliegue/salud_conexiones.py (lo primero de cada vuelta de la tubería, 26 conexiones, con tiempos, caducidad,
qué hacer y dueño), que deja data/conexiones/salud.json. Aquí se rehace, desde ese fichero, el formato antiguo de
M22 (estado bien/aviso/rota/sin_clave + avisos de caducidad, fuentes rotas y seguridad), para lo que aún lo lea.
Así no hay dos comprobaciones distintas que puedan decir cosas diferentes ni se gasta el cupo dos veces.
La versión anterior (con sus propias llamadas) está en generar_conexiones.py.antes_n11.

Uso: python3 fuentes_ajustes/generar_conexiones.py --desde-salud   (lo que corre la tubería)
     python3 fuentes_ajustes/generar_conexiones.py --en-vivo       (antes pasa la salud en vivo)
     (--sin-red se acepta por compatibilidad: igual que --desde-salud)
"""
import json, subprocess, sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "fuentes_personas"))
from comun import DATA, escribir  # noqa: E402

sys.path.insert(1, str(Path(__file__).resolve().parents[1]))  # C5: rutas y secretos en config.py
import config  # noqa: E402
HERR = config.HERRAMIENTAS
AHORA = datetime.now()
SALUD = DATA / "conexiones" / "salud.json"
VIEJO = {"verde": "bien", "ambar": "aviso", "rojo": "rota", "gris": "aviso"}


def main():
    if "--en-vivo" in sys.argv or not SALUD.exists():
        subprocess.run([sys.executable, str(Path(__file__).resolve().parents[1] / "despliegue" / "salud_conexiones.py")]
                       + (["--sin-red"] if "--sin-red" in sys.argv and SALUD.exists() else []), check=False)
    S = json.loads(SALUD.read_text())
    C = []
    for c in S["conexiones"]:
        estado = "sin_clave" if c["estado"] == "falta_clave" else VIEJO.get(c["color"], "aviso")
        C.append({**{k: c.get(k) for k in ("id", "nombre", "icono", "color", "titular", "detalle", "que_hacer", "quien", "quien_id", "desde",
                                           "ultimo_ok", "ms", "caduca", "dias_para_caducar", "caducidad_texto", "critica", "que_da", "modulos")},
                  "estado": estado, "vivo": c.get("ok"), "detalle_vivo": c.get("error_llano") or c.get("detalle"),
                  "llaves": c.get("llaves_total"), "llaves_faltan": c.get("llaves_faltan"),
                  "renovacion": c.get("caducidad_texto"), "quien": c.get("quien") or "—",
                  "renovar": RENOVAR.get(c["id"]) or c.get("renovar")})
    meta = next((c for c in S["conexiones"] if c["id"] == "meta"), {})
    caduca_meta = meta.get("caduca") or "2026-12-01"
    dias_meta = (date.fromisoformat(caduca_meta) - date.today()).days
    avisos = construir_avisos(C, dias_meta, caduca_meta)
    escribir("ajustes/conexiones.json", {
        "_meta": {"generado": S.get("generado") or AHORA.strftime("%Y-%m-%d %H:%M"), "en_vivo": S.get("en_vivo"),
                  "como": S.get("como"), "fuente": "data/conexiones/salud.json (despliegue/salud_conexiones.py)",
                  "recargar": "python3 despliegue/salud_conexiones.py"},
        "conexiones": C, "avisos": avisos})
    print(" · ".join(f"{c['id']}={c['estado']}" for c in C))
    print(f"{len(avisos)} avisos")


# Dónde se renueva cada llave (la consola de cada herramienta). «donde» = el camino dentro de la consola.
RENOVAR = {
    "meta": {"url": "https://developers.facebook.com/apps/2259450834839210/", "donde": "App «MCP Claude» › Herramientas › Explorador de la API; después pegar la llave con meta/pegar_llave.sh", "extra": {"url": "https://business.facebook.com/settings/system-users", "texto": "Usuarios del sistema"}},
    "ghl_agencia": {"url": "https://marketplace.gohighlevel.com/", "donde": "Mis apps › «Panel RO lectura subcuentas» › Autorización (solo si deja de rotar)"},
    "ghl_ro": {"url": "https://app.gohighlevel.com/", "donde": "Subcuenta de RO › Ajustes › Integraciones privadas › crear llave nueva con los permisos de escritura"},
    "google": {"url": "https://console.cloud.google.com/apis/credentials", "donde": "Credenciales › cliente OAuth de la app; volver a autorizar con la cuenta gmb1 de RO"},
    "clickup": {"url": "https://app.clickup.com/settings/apps", "donde": "Ajustes › Apps › Llave de API personal"},
    "zoho": {"url": "https://api-console.zoho.eu/", "donde": "Consola de API de Zoho › cliente de servidor › generar código y canjearlo con zoho/zh.py"},
    "zoom": {"url": "https://marketplace.zoom.us/user/build", "donde": "Gestionar › app de servidor a servidor › Credenciales"},
    "holded": {"url": "https://app.holded.com/", "donde": "Configuración › Desarrolladores › Llaves de API"},
    "airtable": {"url": "https://airtable.com/create/tokens", "donde": "Llaves personales › solo lectura de la base de facturación"},
    "snov": {"url": "https://app.snov.io/account/api", "donde": "Cuenta › API: identificador y secreto"},
    "metricool": {"url": "https://app.metricool.com/", "donde": "Ajustes de la cuenta › API (necesita el plan Advanced)"},
    "windsor": {"url": "https://onboard.windsor.ai/", "donde": "Cuenta › API key; guardarla en el llavero como windsor_api_key"},
    "seranking": {"url": "https://online.seranking.com/", "donde": "Ajustes › API › llave de proyectos (la de datos ya funciona)"},
    "zadarma": {"url": "https://my.zadarma.com/api/", "donde": "Ajustes › API: llave y secreto"},
}


def construir_avisos(C, dias_meta, caduca_meta):
    A = []
    for c in C:
        if c["estado"] == "rota" and c.get("critica"):
            A.append({"gravedad": "rojo", "icono": c["icono"], "titulo": f"{c['nombre']} no responde", "texto": c.get("detalle_vivo"), "quien": c.get("quien"), "ir": "conexiones"})
        elif c["estado"] == "sin_clave":
            A.append({"gravedad": "ambar", "icono": "key", "titulo": f"{c['nombre']}: falta la llave", "texto": c.get("que_hacer") or c.get("renovacion"), "quien": c.get("quien"), "ir": "conexiones"})
        elif c["estado"] in ("aviso", "rota") and c["id"] != "meta":
            A.append({"gravedad": "ambar", "icono": c["icono"], "titulo": c["nombre"], "texto": c.get("detalle_vivo"), "quien": c.get("quien"), "ir": "conexiones"})
    A.append({"gravedad": "rojo" if dias_meta <= 7 else "ambar" if dias_meta <= 30 else "gris", "icono": "clock",
              "titulo": f"La llave de Meta caduca el {caduca_meta} (en {dias_meta} días)",
              "texto": "Renovarla con meta/pegar_llave.sh. La ficha de Dirección pide aviso a 7 días; aquí sale desde 30.", "quien": "Tomás", "ir": "conexiones"})
    try:
        f = json.loads((DATA / "fuentes.json").read_text())
        for x in f["fuentes"]:
            if x.get("estado") in ("rota", "dato_viejo", "a_cero"):
                A.append({"gravedad": "rojo" if x["estado"] == "rota" else "ambar", "icono": "alert",
                          "titulo": f"Fuente «{x['nombre']}»: {x['estado'].replace('_', ' ')}",
                          "texto": x.get("error") or x.get("nota") or x.get("plan"), "quien": "Agus", "ir": "fuentes", "hora": x.get("hora")})
    except Exception:
        pass
    try:
        sys.path.insert(0, str(DATA.parent))
        import escaner_secretos as ESC  # noqa
        res = ESC.escanear(DATA) if hasattr(ESC, "escanear") else None
        if res:
            A.append({"gravedad": "rojo", "icono": "escudo", "titulo": "La puerta de secretos ha parado algún fichero", "texto": str(res)[:200], "quien": "Agus", "ir": "avisos"})
    except Exception:
        pass
    A.append({"gravedad": "ambar", "icono": "escudo", "titulo": "Contraseñas en claro fuera de la app",
              "texto": "Siguen abiertas en 7 tareas de ClickUp, en tickets de Desk y en un chat. La app no las enseña nunca; las limpia Tomás.",
              "quien": "Tomás", "ir": "avisos"})
    orden = {"rojo": 0, "ambar": 1, "gris": 2}
    return sorted(A, key=lambda a: orden.get(a["gravedad"], 3))


if __name__ == "__main__":
    main()

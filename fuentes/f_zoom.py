"""Zoom: reuniones grabadas en la nube por cliente (app «Panel RO lectura», solo lectura, desde el 2-oct).

Plan A (--en-vivo zoom): zm.py → /accounts/me/recordings de los últimos 30 días (1-2 llamadas).
        Se guarda una copia SANEADA en _cache/zoom_grabaciones.json (fecha, minutos, tema; sin enlaces,
        sin códigos de acceso, sin correos del anfitrión).
Plan B: esa copia.
Emparejado: por el nombre del cliente en el tema de la reunión (medición «a medias»: solo las reuniones
        con el cliente en el título; la norma de nombrar cada reunión con su tipo es la D-06).
"""
import importlib.util
from datetime import date, timedelta

from comun import AHORA, AQUI, HERR, bloque, edad_h, escribir, fecha, iso, leer, sanear, tokens

CACHE = AQUI / "_cache" / "zoom_grabaciones.json"
NOMBRE = "Reuniones grabadas en Zoom (30 días)"
FREQ, LIM = 24, 30


def plan_a():
    spec = importlib.util.spec_from_file_location("zm", HERR / "zoom" / "zm.py")
    zm = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(zm)
    tk = zm.token()
    hoy = date.today()
    crudas = zm.grabaciones(tk, (hoy - timedelta(days=30)).isoformat(), hoy.isoformat())
    limpias = [{"fecha": (m.get("start_time") or "")[:16], "minutos": m.get("duration"),
                "tema": sanear(m.get("topic")), "archivos": m.get("recording_count")} for m in crudas]
    escribir(CACHE, {"_meta": {"leido": iso(AHORA), "desde": (hoy - timedelta(days=30)).isoformat(),
                               "hasta": hoy.isoformat(), "fuente": "Zoom API (zm.py), solo lectura"},
                     "reuniones": limpias})


def cargar(universo, en_vivo=False):
    error, plan = None, "B · copia saneada en _cache/"
    if en_vivo:
        try:
            plan_a()
            plan = "A · Zoom en vivo"
        except SystemExit as e:
            error = f"zm.py: {str(e)[:120]}"
        except Exception as e:  # noqa: BLE001
            error = f"zm.py: {type(e).__name__}"
    c = leer(CACHE, None)
    if not c:
        bloques = {cid: {"zoom": bloque(NOMBRE, "sin_conectar", nota="aún no se ha leído Zoom (recargar con --en-vivo zoom)")}
                   for cid in universo}
        return {"fichas": [{"id": "zoom", "nombre": NOMBRE, "grupo": "reuniones", "lector": "~/RO_HERRAMIENTAS/zoom/zm.py",
                            "plan": plan, "error": error, "estado": "sin_conectar", "frecuencia_h": FREQ, "limite_h": LIM,
                            "hora": None, "edad_h": None, "clientes_con_dato": 0}], "bloques": bloques}
    hora = fecha(c["_meta"]["leido"])
    reus = c.get("reuniones", [])
    bloques, con_dato, sin_cliente = {}, 0, 0
    asignadas = set()
    for cid, u in universo.items():
        t_cli = {w for w in tokens(u["nombre"]) if len(w) >= 4}
        def casa(tema):
            comun_ = t_cli & tokens(tema)
            return bool(comun_) and (comun_ == t_cli or any(len(w) >= 6 for w in comun_))
        mias = [r for r in reus if casa(r["tema"])]
        if mias:
            con_dato += 1
            asignadas.update(id(r) for r in mias)
            bloques[cid] = {"zoom": bloque(NOMBRE, "bien", hora=iso(hora), medicion="medias",
                                           nota="solo reuniones con el nombre del cliente en el título",
                                           datos={"periodo": [c["_meta"]["desde"], c["_meta"]["hasta"]],
                                                  "reuniones": sorted(mias, key=lambda r: r["fecha"], reverse=True)})}
        else:
            bloques[cid] = {"zoom": bloque(NOMBRE, "a_cero", hora=iso(hora), medicion="medias",
                                           nota="ninguna grabación con su nombre en el título en 30 días")}
    sin_cliente = sum(1 for r in reus if id(r) not in asignadas)
    ed = edad_h(hora)
    return {"fichas": [{
        "id": "zoom", "nombre": NOMBRE, "grupo": "reuniones", "origen": "Zoom API (cuenta de RO)",
        "lector": "~/RO_HERRAMIENTAS/zoom/zm.py", "plan": plan, "error": error,
        "frecuencia_h": FREQ, "limite_h": LIM, "hora": iso(hora), "edad_h": ed,
        "estado": "dato_viejo" if ed > LIM else "bien", "clientes_con_dato": con_dato,
        "nota": f"{len(reus)} grabaciones en 30 días; {sin_cliente} sin cliente reconocible en el título (D-06)",
    }], "bloques": bloques}

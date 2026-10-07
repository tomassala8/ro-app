#!/usr/bin/env python3
"""fuentes_seo/sr_leer.py · posiciones de SE Ranking por la API de PROYECTOS, sin conector y sin créditos (3-oct-2026).

Por qué existe (Tomás, 3-oct: «SE Ranking se ha roto»):
  · La app leía SE Ranking en api4.seranking.com. SE Ranking unificó sus dos API en https://api.seranking.com/v1/ con
    UNA sola llave para las dos; el servidor viejo contesta 403 «No token» a cualquier llave. Por eso la salud decía
    «sin permiso» y las posiciones se habían cargado UNA vez a mano por el conector (1-sep → 2-oct) y se quedaron ahí.
  · La llave del llavero (seranking_project_key) está bien: con la dirección nueva lee los 70 proyectos.

Coste (documentación oficial, comprobado el 3-oct):
  · https://seranking.com/api/api-credits-system/ : «The Project API instead consumes the limits of your SE Ranking
    subscription». Los créditos solo los gasta la API de Datos. Leer posiciones no cuenta contra ningún límite del plan
    (los límites son palabras seguidas, páginas de auditoría…). Medido: créditos antes y después de leer un proyecto
    entero, la misma cifra (0 gastados).
  · Por eso se lee A DIARIO (paso «seranking» de despliegue/pasos.json, vuelta completa de las 6:00).
  · Lo que SÍ gasta: «Lanzar comprobación de posiciones» (recheck). Esto no lo hace nunca: solo lee.

Qué hace: por cada cliente emparejado (MAPA, el mismo que sr_condensar.py), UNA llamada
  GET https://api.seranking.com/v1/project-management/sites/positions?site_id=…&date_from=…&date_to=…
  (trae nombre, búsquedas y la posición de cada día de cada palabra en cada buscador del proyecto) y deja
  fuentes_seo/_cache/seranking.json con el MISMO formato que antes (hoy, ayer, hace 7 y 8 días, hace 30) más:
    · «dia_dato»: el día de la última comprobación COMPLETA (si la de hoy va a medias —menos de la mitad de palabras
      vistas que el día anterior— se usa la del día anterior: así una comprobación sin terminar no parece una caída);
    · «coste»: texto y enlace a la fuente oficial.
  Si algo falla, NO toca la caché buena, deja _cache/seranking_estado.json con el motivo en llano, avisa (E0, ≤ 3 al
  día, sin repetir) y sale con código ≠ 0 para que la tubería lo marque.

Uso: python3 fuentes_seo/sr_leer.py            (unas 40 llamadas, ~2 min; 5 por segundo como máximo)
     python3 fuentes_seo/sr_leer.py --sin-avisos
"""
import concurrent.futures as cf
import datetime as dt
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from zoneinfo import ZoneInfo

AQUI = os.path.dirname(os.path.abspath(__file__))
APP = os.path.dirname(AQUI)
sys.path.insert(0, APP)
import config  # noqa: E402  (secretos: carpeta privada → entorno → llavero; nunca se imprimen)

BASE = "https://api.seranking.com/v1/project-management"
CACHE = os.path.join(AQUI, "_cache", "seranking.json")
ESTADO = os.path.join(AQUI, "_cache", "seranking_estado.json")
DIAS = 32
COSTE = {
    "texto": "Leer posiciones es gratis: la API de proyectos de SE Ranking no gasta créditos (solo la API de datos los gasta). Por eso se lee cada día a las 6:00.",
    "fuente": "https://seranking.com/api/api-credits-system/",
    "fuente_texto": "SE Ranking · sistema de créditos de la API",
    "frecuencia": "diaria",
    "medido": "3-oct-2026: créditos antes y después de leer un proyecto entero, la misma cifra",
}
# cliente de la app → proyecto de SE Ranking (emparejado el 2-oct y comprobado con la primera palabra de cada proyecto)
MAPA = {
    'christian-sanchez': 12865235, 'octoedro': 10623737, 'accompany': 10910273, 'adade-zaragoza': 9763961, 'ahedo': 8646762,
    'aselegal': 11050775, 'asetra': 6959006, 'aster-asesoria': 9498275, 'avantik': 7534223, 'ayg-asesores': 9351863,
    'bit-24': 10115765, 'bonet-asesores': 9238427, 'busbac': 11705489, 'centro-consulting': 10821245, 'consulting-f': 11669846,
    'ecija-advisory': 8423390, 'ecom-advisory': 11506415, 'fitec-asesores': 10917917, 'fusterguell': 9497984, 'gac': 9126428,
    'gestanex': 12577964, 'greconsult': 11291615, 'innova-scala': 9848531, 'ip-forense': 7781501, 'j-d-consulting': 8475110,
    'joan-lluis-vives': 10930340, 'kiosko-box': 5962484, 'laver': 12925739, 'mg-economistes': 9503675,
    'musashi-consultores': 11080490, 'orejana': 12282629, 'oteca': 9413234, 'prodegest': 11172056, 'romero-martinez': 11508218,
    'segu-assessors': 9747227, 'sol-4': 12284627, 'torrevieja-consult': 9498149, 'tribulex': 12879914, 'xterna': 4928195,
    'deudot': 12991772,
}
SIN_AVISOS = "--sin-avisos" in sys.argv


class FalloLlano(Exception):
    def __init__(self, texto, quien="tomas", tecnico=None):
        super().__init__(texto)
        self.texto, self.quien, self.tecnico = texto, quien, tecnico


def llave():
    k = config.secreto("seranking_project_key") or config.secreto("seranking_data_key")
    if not k:
        raise FalloLlano("Falta la llave de SE Ranking en el llavero. Tomás: cópiala en SE Ranking › API › Panel y pégala con bash ~/RO_HERRAMIENTAS/seranking/pegar.sh.")
    return k


def pedir(ruta, k, q=None, intentos=3):
    url = BASE + ruta + ("?" + urllib.parse.urlencode(q) if q else "")
    for i in range(intentos):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"Authorization": "Token " + k, "Accept": "application/json"}), timeout=90) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                raise FalloLlano("SE Ranking no acepta la llave (caducada, revocada o de otra cuenta). Tomás: copia la de SE Ranking › API › Panel y pégala con bash ~/RO_HERRAMIENTAS/seranking/pegar.sh.", tecnico=f"HTTP {e.code}")
            if e.code == 404:
                raise FalloLlano("SE Ranking ha cambiado la dirección de su API (404). Agus: pídele a Claude que actualice fuentes_seo/sr_leer.py con la documentación de https://seranking.com/api/project/getting-started/.", quien="agustina", tecnico="HTTP 404")
            if e.code in (429, 500, 502, 503, 504) and i < intentos - 1:
                time.sleep(2 * (i + 1) ** 2)
                continue
            raise FalloLlano(f"SE Ranking no responde bien (error {e.code}). Se reintenta en la próxima vuelta; si sigue, Agus lo mira.", quien="agustina", tecnico=f"HTTP {e.code}")
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            if i < intentos - 1:
                time.sleep(2 * (i + 1) ** 2)
                continue
            raise FalloLlano("No hay conexión con SE Ranking (red o tiempo agotado). Se reintenta en la próxima vuelta.", quien="agustina", tecnico=type(e).__name__)


try:
    from .posiciones import seleccionar, posicion, fecha
except ImportError:
    from posiciones import seleccionar, posicion, fecha

def pos_en(posiciones, dia, campo="pos"):
    return seleccionar(posiciones, dia, campo)


def dia_completo(datos, hoy):
    """Último día con la comprobación terminada: el más reciente con palabras vistas, salvo que vea menos de la mitad
    que el día anterior (comprobación a medias) → el anterior."""
    vistas = Counter()
    for m in datos:
        for k in m.get("keywords") or []:
            for p in k.get("positions") or []:
                if posicion(p.get("pos"),p.get("pos_estado"),p.get("pos_centinela")) is not None and fecha(p.get("date")) and p["date"] <= str(hoy):
                    vistas[p["date"]] += 1
    if not vistas:
        return None
    dias = sorted(vistas)
    d = dias[-1]
    if len(dias) > 1 and vistas[dias[-2]] >= 4 and vistas[d] < 0.5 * vistas[dias[-2]]:
        d = dias[-2]
    return dt.date.fromisoformat(d)


def condensar(cid, proyecto, datos, hoy):
    dia = dia_completo(datos, hoy) or hoy
    motores = []
    for i, m in enumerate(datos):
        kws = []
        for k in m.get("keywords") or []:
            ps = k.get("positions") or []
            h, fh = pos_en(ps, dia)
            ayer, fa = pos_en(ps, dia - dt.timedelta(days=1))
            sem, fs = pos_en(ps, dia - dt.timedelta(days=7))
            sem2, fs2 = pos_en(ps, dia - dt.timedelta(days=8))
            mes, fm = pos_en(ps, dia - dt.timedelta(days=30))
            mapa, fmaps = pos_en(ps, dia, "map_position")
            kws.append({"k": k.get("name") or str(k.get("id")), "vol": k.get("volume") or 0, "hoy": h, "ayer": ayer, "sem": sem,
                        "sem2": sem2, "mes": mes, "mapa": mapa, "fechas":{"hoy":fh,"ayer":fa,"sem":fs,"sem2":fs2,"mes":fm,"mapa":fmaps}, "desde": min((p["date"] for p in ps if fecha(p.get("date"))), default=None), "ultima": fh})
        motores.append({"site_engine_id": m.get("site_engine_id"), "principal": i == 0, "palabras": kws})
    return {"proyecto": proyecto, "motores": motores, "ultima_comprobacion": str(dia),"cobertura_posiciones":"parcial; día seleccionado por observaciones, no certifica comprobación completa",
            "prueba": f"https://online.seranking.com/admin.site.rankings.site_id-{proyecto}.html"}


def avisar(texto, clave="seranking_lectura"):
    if SIN_AVISOS:
        return
    try:
        sys.path.insert(0, os.path.join(APP, "despliegue"))
        import avisos_tuberia as AV
        AV.avisar("fuente_caida", clave, texto[:400])
    except Exception:
        pass   # un aviso que no sale no puede tumbar el paso


def guardar(ruta, obj):
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    tmp = ruta + ".tmp"
    with open(tmp, "w") as f:
        json.dump(obj, f, ensure_ascii=False)
    os.replace(tmp, ruta)


def main():
    madrid = dt.datetime.now(ZoneInfo("Europe/Madrid"))
    hoy = madrid.date()
    ahora = madrid.strftime("%Y-%m-%d %H:%M")
    try:
        k = llave()
        sitios = pedir("/sites", k)
        activos = {s["id"]: s for s in sitios if isinstance(s, dict)}
        q0 = {"date_from": str(hoy - dt.timedelta(days=DIAS)), "date_to": str(hoy)}
        salida, faltan, errores = {}, [], []

        def uno(item):
            cid, pid = item
            if pid not in activos:
                return cid, None, "el proyecto ya no está en SE Ranking"
            return cid, condensar(cid, pid, pedir("/sites/positions", k, {"site_id": pid, **q0}), hoy), None

        with cf.ThreadPoolExecutor(max_workers=3) as ex:          # tope de SE Ranking: 5 por segundo
            for cid, fila, motivo in ex.map(uno, MAPA.items()):
                if fila:
                    salida[cid] = fila
                else:
                    faltan.append({"cliente_id": cid, "motivo": motivo})
        if len(salida) < 0.8 * len(MAPA):
            raise FalloLlano(f"SE Ranking solo ha devuelto {len(salida)} de {len(MAPA)} proyectos. Se deja el dato anterior.", quien="agustina")
        dias = Counter(c["ultima_comprobacion"] for c in salida.values())
        dia_dato = dias.most_common(1)[0][0]
        sin_emparejar = [{"id": s["id"], "titulo": s.get("title")} for s in sitios if s.get("is_active") and s["id"] not in MAPA.values()]
        doc = {"generado": ahora, "origen": "API de proyectos de SE Ranking (api.seranking.com/v1/project-management), sin créditos",
               "dia_dato": dia_dato, "dias_por_cliente": dict(dias), "ventana": q0, "coste": COSTE, "clientes": salida,
               "faltan": faltan, "proyectos_sin_emparejar": len(sin_emparejar), "llamadas": 1 + len(MAPA)}
        guardar(CACHE, doc)
        guardar(ESTADO, {"ok": True, "hora": ahora, "dia_dato": dia_dato, "clientes": len(salida), "faltan": faltan,
                         "coste": COSTE, "texto": f"Posiciones leídas: {len(salida)} clientes, comprobación del {dia_dato}."})
        print(f"SE Ranking: {len(salida)} clientes · comprobación del {dia_dato} · {len(faltan)} sin leer · {len(sin_emparejar)} proyectos sin emparejar · 0 créditos")
        return 0
    except FalloLlano as e:
        previo = {}
        try:
            previo = json.load(open(CACHE))
        except Exception:
            pass
        guardar(ESTADO, {"ok": False, "hora": ahora, "error": e.texto, "quien": e.quien, "tecnico": e.tecnico,
                         "dia_dato_anterior": previo.get("dia_dato") or (previo.get("generado") or "")[:10] or None, "coste": COSTE})
        avisar(f"SE Ranking no se ha podido leer: {e.texto} Las pantallas siguen con las posiciones del {previo.get('dia_dato') or 'último día bueno'}.")
        print("SE Ranking:", e.texto, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())

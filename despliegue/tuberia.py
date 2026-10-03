#!/usr/bin/env python3
"""despliegue/tuberia.py · UNA sola tubería para regenerar los datos de la app (carril C5, 2-oct-2026).

Sustituye a lanzar los generadores sueltos (riesgo R6 del estudio 23). Lee el grafo de despliegue/pasos.json y:
  · ordena por dependencias (primero lectores en bruto, luego la base y la capa E1, luego los módulos, al final la foto);
  · respeta el horario por fuente («cada_min»: no repite un paso que fue bien hace poco, salvo --forzar);
  · reintenta cada paso 3 veces con espera creciente (30 s, 2 min, 8 min) y con su tiempo máximo;
  · «último dato bueno»: antes de cada paso guarda sus salidas; si falla (código ≠ 0, JSON roto, o un secreto
    nuevo según escaner_secretos.py), RESTAURA la versión anterior entera y la sella como «dato_viejo»;
  · validación (auditoría 35, M3): también es un fallo una salida vacía ({}, o lista que se queda sin filas), sin sus
    «claves_minimas» o con un «recuento» que cae más de «caida_max» frente a la vuelta anterior; se restaura YA antes de
    cada reintento (M2), no solo al final;
  · fuentes caídas (A5): «vigilar_fuentes» (capa E1) → una fuente que estaba «bien» y sale «sin_conectar»/«rota» o
    pierde más de la mitad de sus clientes con dato (Meta caído, token caducado) = fallo: se restaura el último dato
    bueno, se marca «dato_viejo» con «caida» (desde, motivo) en fuentes.json y en cada ficha, y aviso «fuente_caida».
    Sus dependientes SÍ corren (dato coherente). Una baja a propósito: --aceptar-caida <id>;
  · «errores_de_fuente»: el generador apunta «hora_error» en la fuente que no pudo leer (conservando su último dato
    bueno); si es de esta vuelta, cuenta como fallo de esa fuente (sello «dato_viejo», aviso, vuelta «con_fallos»)
    sin restaurar ni bloquear;
  · si una dependencia falla, sus dependientes no corren y se quedan con su último dato bueno (sello con el motivo);
  · bloqueo: nunca dos vueltas a la vez (fcntl en local, bloqueo consultivo en Postgres);
  · la llave de GHL de agencia que rota la usa SOLO la tubería, prestada con bloqueo (despliegue/llave_ghl.py);
  · registro JSON por vuelta en estado/registros/ y en la base de estado (tablas ejecuciones y pasos);
  · avisos con el sistema de E0 (≤3 al día, sin repetir) — despliegue/avisos_tuberia.py;
  · publicación «todo o nada» de data/ en la base (despliegue/publicacion.py) si hay DATABASE_URL (Render);
  · opcionales por variable (si no existen, no hacen nada): SENTRY_DSN (errores con el SDK de Sentry; el DSN
    puede ser el de Better Stack, sin datos personales), RO_LATIDO_URL (latido de Better Stack),
    RO_PUBLICAR_CMD (otra publicación al acabar, si algún día hiciera falta).

Uso:
  python3 despliegue/tuberia.py --ligero                 cada hora de 7 a 23 h (sin créditos ni lecturas masivas)
  python3 despliegue/tuberia.py --completo               6:00 y 14:00 (todo en vivo, lectores en bruto incluidos)
  python3 despliegue/tuberia.py --ligero --desde-crudo   sin red: cada paso desde lo último guardado (pruebas)
  python3 despliegue/tuberia.py --plan [--completo]      enseña el orden sin ejecutar nada
  Otras: --solo a,b · --forzar · --quien <persona> · --esperas-cortas (pruebas) · --sin-avisos
Códigos de salida: 0 todo bien · 1 algún paso falló (se queda el dato anterior) · 75 ya hay otra vuelta en marcha.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

AQUI = Path(__file__).resolve().parent
APP = AQUI.parent
sys.path.insert(0, str(AQUI))
sys.path.insert(1, str(APP))
import config  # noqa: E402
import estado as ES  # noqa: E402
import llave_ghl  # noqa: E402
import avisos_tuberia as AV  # noqa: E402  (no «avisos»: taparía al avisos.py de la raíz, N15)

PASOS = Path(os.environ.get("RO_PASOS") or AQUI / "pasos.json")   # RO_PASOS solo para pruebas
RX_CORREO = re.compile(r"[\w.+-]+@[\w-]+(\.[\w-]+)+")
RX_TEL = re.compile(r"\+?\d[\d\s.-]{8,}\d")
RX_SECRETO = re.compile(r"(?i)(token|key|secret|password|access_token)=[^&\s]+")


def ahora_dt():
    """Ahora en hora de Madrid, sin zona (R16): lo que se enseña y lo que se compara con los sellos de estado.py, que
    van en la misma hora. Al guardar en «recargas» de local.db, avisos_tuberia.a_utc() lo pasa a UTC."""
    return ES.ahora_dt()


def ahora():
    return ahora_dt().isoformat(timespec="seconds")


def sanear(texto):
    """Una línea de salida sin correos, teléfonos ni llaves (va a la base, al registro y a la pantalla)."""
    texto = RX_SECRETO.sub(r"\1=[oculto]", texto or "")
    texto = RX_CORREO.sub("[correo]", texto)
    return RX_TEL.sub("[número]", texto)[:240]


def sanear_profundo(texto):
    """Como sanear() pero sin recortar (para eventos de error enteros)."""
    texto = RX_SECRETO.sub(r"\1=[oculto]", texto or "")
    return RX_TEL.sub("[número]", RX_CORREO.sub("[correo]", texto))


# ------------------------------------------------------------------ errores: SDK de Sentry apuntando a Better Stack (opcional)
def iniciar_sentry():
    dsn = os.environ.get("SENTRY_DSN")
    if not dsn:
        return None
    try:
        import sentry_sdk
        def limpiar(evento, _pista):   # E81: nada de correos, teléfonos ni llaves en lo que sale hacia Better Stack
            return json.loads(sanear_profundo(json.dumps(evento, default=str)))
        sentry_sdk.init(dsn=dsn, environment=os.environ.get("RO_ENTORNO", "local"), traces_sample_rate=0,
                        send_default_pii=False, before_send=limpiar)
        return sentry_sdk
    except Exception as e:
        print(f"[sentry] SENTRY_DSN existe pero no se pudo iniciar ({e}); sigo sin Sentry.", file=sys.stderr)
        return None


def latido(fallo=False):
    url = os.environ.get("RO_LATIDO_URL")
    if not url:
        return
    try:
        urllib.request.urlopen(url.rstrip("/") + ("/fail" if fallo else ""), timeout=10)
    except Exception as e:
        print(f"[latido] no llegó: {e}", file=sys.stderr)


# ------------------------------------------------------------------ grafo
def resolver(arg):
    return (arg.replace("{PY}", sys.executable).replace("{APP}", str(APP)).replace("{HERR}", str(config.HERRAMIENTAS))
            .replace("{PROYECTO}", str(config.PROYECTO)).replace("{CRUDOS}", str(config.CRUDOS))
            .replace("{ESTADO}", str(config.ESTADO_DIR)))


def ruta_salida(s):
    p = Path(resolver(s))
    return p if p.is_absolute() else APP / p


def plan(cfg, modo, desde_crudo, solo=None):
    """Lista de (paso, comando o None, motivo_si_no_corre) en orden de dependencias."""
    pasos = {p["id"]: p for p in cfg["pasos"]}
    elegidos = []
    for p in cfg["pasos"]:
        if desde_crudo == "donde_exista":
            cmd = p.get("crudo") or p.get(modo)
        else:
            cmd = p.get("crudo") if (modo == "crudo" or desde_crudo) else p.get(modo)
        motivo = None
        if p.get("activo") is False:
            motivo = p.get("motivo") or "inactivo"
        elif solo and p["id"] not in solo:
            motivo = "fuera de --solo"
        elif cmd is None:
            if desde_crudo and p.get(modo) is not None:
                motivo = "necesita red (sin modo «desde crudo»)"
            else:
                motivo = f"no corre en modo {modo}"
        elegidos.append((p, [resolver(x) for x in cmd] if cmd and not motivo else None, motivo))
    # orden topológico estable (respetando el orden del fichero cuando no hay dependencia)
    activos = {p["id"] for p, c, m in elegidos if c}
    hecho, orden = set(), []
    pendientes = list(elegidos)
    while pendientes:
        avance = False
        for item in list(pendientes):
            p = item[0]
            deps = [d for d in p.get("depende", []) if d in activos and d in pasos]
            if all(d in hecho for d in deps):
                orden.append(item)
                hecho.add(p["id"])
                pendientes.remove(item)
                avance = True
        if not avance:
            raise SystemExit(f"Dependencias en círculo: {[i[0]['id'] for i in pendientes]}")
    final = [i for i in orden if i[0].get("siempre_al_final")]
    return [i for i in orden if not i[0].get("siempre_al_final")] + final


# ------------------------------------------------------------------ último dato bueno
SIN_COPIA_PARTES = {"_cache", "_crudo", "_privado"}   # nunca se copian a la instantánea (datos personales o en bruto)


def _ficheros_de(s):
    p = ruta_salida(s)
    if p.is_dir():
        return [f for f in p.rglob("*") if f.is_file()]
    return [p] if p.exists() else []


def _guardable(f):
    """Regla de seguridad (2-oct): a la instantánea solo va lo que pasa la puerta de secretos de E0 y no es caché en
    bruto ni almacén privado. Lo demás se deja donde está (no se copia a ningún sitio)."""
    if SIN_COPIA_PARTES & set(f.parts):
        return False
    try:
        import escaner_secretos as ESC
        return not ESC.escanear_fichero(f)
    except Exception:
        return False


def guardar_instantanea(paso, salidas, destino):
    """Copia las salidas actuales del paso a una carpeta privada TEMPORAL fuera del proyecto (0700), que se borra al
    acabar el paso. Devuelve el manifiesto {fichero: copia | "sin_copia"}."""
    manifiesto, n = {}, 0
    carpeta = destino / paso
    carpeta.mkdir(parents=True, exist_ok=True)
    for s in salidas:
        for f in _ficheros_de(s):
            if _guardable(f):
                n += 1
                shutil.copy2(f, carpeta / str(n))
                manifiesto[str(f)] = str(carpeta / str(n))
            else:
                manifiesto[str(f)] = "sin_copia"
    return manifiesto


def restaurar(paso, salidas, destino, manifiesto):
    """Deja las salidas como estaban antes del paso: lo nuevo fuera, lo cambiado de vuelta. Lo que no se pudo copiar
    (cachés y _privado/) se queda como lo dejó el paso y se apunta."""
    sin_restaurar = []
    ahora_hay = {str(f) for s in salidas for f in _ficheros_de(s)}
    for f in ahora_hay - set(manifiesto):
        if SIN_COPIA_PARTES & set(Path(f).parts):
            sin_restaurar.append(f)
        else:
            Path(f).unlink()                                  # fichero nuevo a medias: fuera
    for f, copia in manifiesto.items():
        if copia == "sin_copia":
            sin_restaurar.append(f)
            continue
        Path(f).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(copia, f)
    return sin_restaurar


def ficheros_json(salidas):
    for s in salidas:
        p = ruta_salida(s)
        if p.is_dir():
            yield from (f for f in p.rglob("*.json") if "_privado" not in f.parts and not f.name.startswith("."))
        elif p.suffix == ".json" and p.exists():
            yield p


def hallazgos_secretos(salidas):
    """Cuántos hallazgos da la puerta de secretos de E0 en las salidas públicas del paso (no en _privado/)."""
    try:
        import escaner_secretos as ESC
    except Exception:
        return 0
    n = 0
    for f in ficheros_json(salidas):
        if APP in f.parents and (APP / "data") in f.parents:
            try:
                n += len(ESC.escanear_fichero(f))
            except Exception:
                pass
    return n


def _corto(f):
    f = Path(f)
    return str(f.relative_to(APP)) if APP in f.parents else f.name


def _leer_json(f):
    try:
        return json.loads(Path(f).read_text())
    except Exception:
        return None


def _previo(manifiesto, f):
    """La versión de antes del paso de un fichero de salida (de la instantánea), o None."""
    copia = manifiesto.get(str(f))
    return _leer_json(copia) if copia and copia != "sin_copia" else None


def _en_ruta(d, ruta):
    """Valor en una ruta con puntos («resumen.clientes_con_meta»); listas y diccionarios cuentan por su longitud."""
    for k in [x for x in (ruta or "").split(".") if x]:
        d = d.get(k) if isinstance(d, dict) else None
    if isinstance(d, (list, dict)):
        return len(d)
    return d if isinstance(d, (int, float)) and not isinstance(d, bool) else None


def validar(salidas, antes_secretos, existia, p=None):
    """Salida mala = JSON roto, salida desaparecida, secreto nuevo (como siempre) y, desde la auditoría 35 (M3):
      · un JSON vacío ({}, null, "") o una lista que se queda vacía cuando antes tenía filas (salvo «vacio_ok»);
      · le faltan las claves mínimas del paso («claves_minimas»: {salida: [claves]});
      · un recuento del paso cae más de lo permitido frente a la vuelta anterior («recuento»)."""
    p = p or {}
    for f in ficheros_json(salidas):
        try:
            d = json.loads(f.read_text())
        except Exception as e:
            return f"JSON roto en {_corto(f)}: {e}"
        if not p.get("vacio_ok"):
            if d in ({}, None, "") or (isinstance(d, str) and not d.strip()):
                return f"salida vacía en {_corto(f)}"
            if d == [] and _previo(existia, f):
                return f"{_corto(f)} se ha quedado sin filas (antes tenía)"
    for s in salidas:
        q = ruta_salida(s)
        if existia.get(str(q)) and not q.exists():
            return f"la salida {s} ha desaparecido"
    for s, claves in (p.get("claves_minimas") or {}).items():
        q = ruta_salida(s)
        d = _leer_json(q)
        if not isinstance(d, dict):
            return f"{_corto(q)} no existe o no es un objeto (claves mínimas {', '.join(claves)})"
        faltan = [k for k in claves if k not in d or d[k] is None]
        if faltan:
            return f"a {_corto(q)} le faltan las claves mínimas: {', '.join(faltan)}"
    for r in p.get("recuento") or []:
        q = ruta_salida(r["fichero"])
        antes, ahora_n = _en_ruta(_previo(existia, q), r.get("ruta")), _en_ruta(_leer_json(q), r.get("ruta"))
        if antes is None or antes < r.get("minimo_antes", 4):
            continue
        if ahora_n is None or ahora_n < antes * (1 - r.get("caida_max", 0.5)):
            return f"el recuento «{r.get('ruta') or _corto(q)}» de {_corto(q)} cae de {antes} a {ahora_n}"
    despues = hallazgos_secretos(salidas)
    if despues > antes_secretos:
        return f"la puerta de secretos encuentra {despues - antes_secretos} hallazgos nuevos"
    return None


# ------------------------------------------------------------------ fuentes caídas (auditoría 35, A5/A6)
CAIDA = {"sin_conectar", "rota"}


def fuentes_caidas(p, existia, aceptar=()):
    """«vigilar_fuentes» (capa E1): una fuente que antes estaba «bien» (o ya marcada caída por la tubería) y ahora
    sale «sin_conectar»/«rota», o pierde más de la mitad de sus clientes con dato, está CAÍDA. Devuelve
    [(id, motivo, clientes_con_dato_bueno)]. No es una caída lo que se acepta con --aceptar-caida."""
    v = p.get("vigilar_fuentes")
    if not v:
        return []
    f = ruta_salida(v["fichero"])
    antes = {x.get("id"): x for x in ((_previo(existia, f) or {}).get("fuentes") or []) if isinstance(x, dict)}
    ahora_ = {x.get("id"): x for x in ((_leer_json(f) or {}).get("fuentes") or []) if isinstance(x, dict)}
    out = []
    for fid, a in antes.items():
        if fid in aceptar or not (a.get("estado") == "bien" or a.get("caida")):
            continue
        n_antes = a.get("clientes_con_dato") or 0
        b = ahora_.get(fid)
        if b is None:
            out.append((fid, "ha desaparecido de fuentes.json", n_antes))
        elif b.get("estado") in CAIDA:
            out.append((fid, f"pasa a «{b.get('estado')}» ({_por_que(a, b)})", n_antes))
        elif n_antes >= v.get("minimo_antes", 4) and (b.get("clientes_con_dato") or 0) < n_antes * (1 - v.get("caida_max", 0.5)):
            out.append((fid, f"cae de {n_antes} a {b.get('clientes_con_dato') or 0} clientes con dato", n_antes))
    return out


def _por_que(antes, ahora_):
    """El motivo de una caída nunca sale vacío (R16, N16: «pasa a «sin_conectar» ()»). Primero lo que dice la fuente
    (error, error de la lectura directa, nota); si no dice nada, el hecho medible: con cuántos clientes estaba y está."""
    lectura = ahora_.get("lectura_directa") if isinstance(ahora_.get("lectura_directa"), dict) else {}
    for v in (ahora_.get("error"), lectura.get("error"), ahora_.get("nota")):
        texto = sanear(str(v)).strip() if v not in (None, "", "None") else ""
        if texto:
            return texto[:90]
    n_antes, n_ahora = antes.get("clientes_con_dato") or 0, ahora_.get("clientes_con_dato") or 0
    hora = ahora_.get("hora") or "sin hora"
    return (f"la fuente no dice por qué: tenía dato de {n_antes} clientes y ahora de {n_ahora}; "
            f"última lectura {hora}")


CODIGO_CAIDA = 4   # generador que detecta él mismo una fuente caída (fuentes/generar_datos.py): no sobrescribe, marca y sale con 4


def _motivo_lleno(motivo, n):
    """El generador de E1 (fuentes/generar_datos.py) escribe «pasa a «sin_conectar» ()» si la fuente no trae error ni
    nota: aquí se rellena para que el aviso y el sello nunca lleguen vacíos (R16)."""
    relleno = f"la fuente no dice por qué; se queda su último dato bueno de {n} clientes"
    motivo = (motivo or "").strip()
    if not motivo:
        return relleno
    return motivo[:-2] + f"({relleno})" if motivo.endswith("()") else motivo


def caidas_del_generador(lineas):
    """Lee la línea «FUENTES_CAIDAS [...]» que deja el generador al salir con CODIGO_CAIDA."""
    for x in reversed(lineas):
        if x.startswith("FUENTES_CAIDAS "):
            try:
                return [(c["id"], _motivo_lleno(c.get("motivo"), c.get("clientes_con_dato_bueno") or 0),
                         c.get("clientes_con_dato_bueno") or 0) for c in json.loads(x[15:])]
            except Exception:
                return []
    return []


def _escribir_atomico(f, d):
    f = Path(f)
    tmp = f.with_name(f".{f.name}.tubtmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False, indent=1))
    tmp.replace(f)


def marcar_caidas(p, caidas, hora):
    """Tras restaurar el último dato bueno, lo marca como tal: la fuente caída pasa de «bien» a «dato_viejo» con
    «caida» (desde cuándo, por qué) en data/fuentes.json y en cada ficha de data/clientes/. Así la app enseña el dato
    bueno con SU hora y el aviso, nunca un «bien» falso. Devuelve cuántos ficheros ha marcado."""
    v = p["vigilar_fuentes"]
    ids = {fid: motivo for fid, motivo, _ in caidas}
    n = 0

    def marca(bloque, fid):
        previa = bloque.get("caida") if isinstance(bloque.get("caida"), dict) else {}
        bloque["caida"] = {"desde": previa.get("desde") or hora, "comprobado": hora, "motivo": ids[fid],
                           "estado_antes": previa.get("estado_antes") or bloque.get("estado")}
        if bloque.get("estado") == "bien":
            bloque["estado"] = "dato_viejo"

    f = ruta_salida(v["fichero"])
    d = _leer_json(f)
    if isinstance(d, dict):
        for x in d.get("fuentes") or []:
            if isinstance(x, dict) and x.get("id") in ids:
                marca(x, x["id"])
        _escribir_atomico(f, d)
        n += 1
    if v.get("fichas"):
        for ff in sorted(ruta_salida(v["fichas"]).glob("*.json")):
            d = _leer_json(ff)
            if not isinstance(d, dict) or not isinstance(d.get("fuentes"), dict):
                continue
            tocado = False
            for fid in ids:
                b = d["fuentes"].get(fid)
                if isinstance(b, dict) and b.get("estado") not in (None, "no_aplica", "sin_conectar"):
                    marca(b, fid)
                    if isinstance(d.get("estado_fuentes"), dict) and fid in d["estado_fuentes"]:
                        d["estado_fuentes"][fid] = b["estado"]
                    tocado = True
            if tocado:
                _escribir_atomico(ff, d)
                n += 1
    return n


def _hora(t):
    try:
        return datetime.fromisoformat(str(t).replace("T", " ")[:19])
    except Exception:
        return None


def errores_de_fuente(salidas, desde):
    """«errores_de_fuente»: el generador apunta «hora_error» en la fuente que no pudo leer (y conserva su último dato
    bueno). Devuelve {fuente: [dónde]} de los apuntados en ESTA vuelta (hora_error ≥ «desde»)."""
    desde = desde.replace(second=0, microsecond=0)
    out = {}

    def recorrer(x, camino):
        if isinstance(x, dict):
            h = _hora(x.get("hora_error")) if x.get("hora_error") else None
            if h and h >= desde:
                fuente = x.get("fuente_id") or (camino[-1] if camino else "?")
                out.setdefault(str(fuente), []).append("/".join(camino[:-1])[-60:] or "raíz")
            for k, y in x.items():
                recorrer(y, camino + [str(k)])
        elif isinstance(x, list):
            for i, y in enumerate(x):
                recorrer(y, camino + [y.get("id") if isinstance(y, dict) and y.get("id") else str(i)])
    for f in ficheros_json(salidas):
        recorrer(_leer_json(f), [])
    return out


# ------------------------------------------------------------------ ejecución
# Una sola pasada coherente: todos los pasos, la misma hora. Va en la hora de la máquina (no en la de Madrid) porque
# los generadores apuntan «hora_error» con su datetime.now() y errores_de_fuente() compara con ella.
HORA_DATOS = datetime.now().isoformat(timespec="seconds")


def correr_paso(p, cmd, modo, E, eid, esperas, registro, instantaneas, sentry, aceptar=()):
    """Devuelve {"ok", "bloquea"}: «bloquea» = sus dependientes no deben correr. Una fuente caída con el último
    dato bueno restaurado entero, o una fuente con error apuntado por su generador, NO bloquea (los dependientes
    leen un dato coherente con su hora), pero la vuelta sale «con_fallos» y hay aviso."""
    pid = p["id"]
    salidas = p.get("salidas", [])
    usa_ghl = p.get("ghl_agencia") or modo in p.get("ghl_agencia_en", [])
    existia = guardar_instantanea(pid, salidas, instantaneas)
    antes = hallazgos_secretos(salidas)
    sin_restaurar = []
    intentos = []
    error = None
    caidas = []
    inicio_paso = datetime.now()
    marcado_por_generador = False
    veces = len(esperas) + 1
    for intento in range(1, veces + 1):
        t0, ini = time.time(), ahora()
        caidas = []
        try:
            entorno = {**os.environ, "RO_HORA_DATOS": HORA_DATOS, "RO_VUELTA": str(eid)}
            if usa_ghl:
                with llave_ghl.prestar(E) as extra:
                    r = subprocess.run(cmd, cwd=APP, capture_output=True, text=True, timeout=p.get("timeout", 300),
                                       env={**entorno, **extra})
            else:
                r = subprocess.run(cmd, cwd=APP, capture_output=True, text=True, timeout=p.get("timeout", 300), env=entorno)
            lineas = (r.stdout + r.stderr).strip().splitlines()
            error = None if r.returncode == 0 else f"código {r.returncode}: " + " | ".join(lineas[-2:])
            if r.returncode == CODIGO_CAIDA and p.get("vigilar_fuentes"):
                caidas = caidas_del_generador(lineas)
                marcado_por_generador = bool(caidas)
            if not error:
                error = validar(salidas, antes, existia, p)
            if not marcado_por_generador:
                caidas = [] if error else fuentes_caidas(p, existia, aceptar)
            if caidas:
                error = "fuente caída: " + "; ".join(f"{fid} {m}" for fid, m, _ in caidas)
        except subprocess.TimeoutExpired:
            lineas, error = [], f"se pasó de {p.get('timeout', 300)} s"
        except ES.Ocupado:
            lineas, error = [], "la llave de GHL está en uso por otro proceso"
        except Exception as e:
            lineas, error = [], f"{type(e).__name__}: {e}"
        seg = round(time.time() - t0, 1)
        salida = [sanear(x) for x in lineas[-3:]]
        E.apuntar_paso(eid, pid, intento, ini, seg, "ok" if not error else "fallo", json.dumps(salida, ensure_ascii=False),
                       sanear(error) if error else None)
        intentos.append({"intento": intento, "segundos": seg, "ok": not error, "error": sanear(error) if error else None, "salida": salida})
        if not error or marcado_por_generador:      # el generador ya dejó el último dato bueno marcado: no se reintenta
            break
        if intento < veces:
            espera = esperas[intento - 1]
            # M2: mientras espera el reintento, se sirve el último dato bueno, nunca el fichero roto o caído
            restaurar(pid, salidas, instantaneas, existia)
            print(f"   ↻ {pid}: {sanear(error)[:120]} · reintento en {espera} s")
            time.sleep(espera)
    marcados = 0
    con_error_fuente = {}
    if error:
        if marcado_por_generador:
            marcados = "lo marcó el generador"      # no escribió datos: solo marcó el último dato bueno; no se restaura
        else:
            sin_restaurar = restaurar(pid, salidas, instantaneas, existia)
            if caidas:
                marcados = marcar_caidas(p, caidas, ahora_dt().strftime("%Y-%m-%d %H:%M"))
        estado_sello = E.sellar(pid, False, sanear(error))
        if sentry:
            sentry.capture_message(f"tuberia · {pid} falló: {sanear(error)}", level="error")
    else:
        if p.get("errores_de_fuente"):   # errores apuntados en ESTA vuelta (por este paso o por el lector que lee)
            con_error_fuente = errores_de_fuente(salidas, min(inicio_paso, datetime.fromisoformat(HORA_DATOS)))
        if con_error_fuente:
            motivo = "fuente con error (se queda su último dato bueno): " + ", ".join(
                f"{k} ({len(v)})" for k, v in sorted(con_error_fuente.items()))
            estado_sello = E.sellar(pid, False, sanear(motivo))
        else:
            estado_sello = E.sellar(pid, True)
    shutil.rmtree(instantaneas / pid, ignore_errors=True)       # la instantánea solo vive lo que dura el paso
    ok = not error and not con_error_fuente
    bloquea = bool(error) and not (caidas and not sin_restaurar)
    paso = {"id": pid, "ok": ok, "intentos": intentos, "sello": estado_sello, "sin_restaurar": len(sin_restaurar),
            "ghl_agencia": bool(usa_ghl), "comando": " ".join(Path(c).name if c == sys.executable else c for c in cmd)}
    if caidas:
        paso["fuentes_caidas"] = [{"id": fid, "motivo": sanear(m), "clientes_con_dato_bueno": n} for fid, m, n in caidas]
        paso["marcados"] = marcados
    if con_error_fuente:
        paso["fuentes_con_error"] = {k: len(v) for k, v in con_error_fuente.items()}
        paso["intentos"][-1]["error"] = sanear("fuente con error: " + ", ".join(sorted(con_error_fuente)))
    if not bloquea and not ok:
        paso["no_bloquea"] = True
    registro["pasos"].append(paso)
    return {"ok": ok, "bloquea": bloquea, "caidas": [c[0] for c in caidas], "con_error": sorted(con_error_fuente)}


def fresco(E, p, forzar):
    """Horario por fuente: si el paso fue bien hace menos de «cada_min», no se repite."""
    if forzar or not p.get("cada_min"):
        return False
    s = E.sello(p["id"])
    if not s or not s.get("ultimo_bueno") or s.get("estado") != "bien":
        return False
    return datetime.fromisoformat(s["ultimo_bueno"]) > ahora_dt() - timedelta(minutes=p["cada_min"])


def escribir_salud(E):
    """Resumen por paso para la pantalla de salud (M22). C0 decide cómo servirlo (ver _ESTADO_C5.md)."""
    sellos = E.sellos()
    out = {"generado": ahora(), "motor_estado": E.motor, "pasos": sellos,
           "ultimas": [dict(zip(("id", "modo", "quien", "inicio", "fin", "estado"), r)) for r in E.ultimas(10)]}
    f = config.ESTADO_DIR / "salud.json"
    tmp = f.with_suffix(".tmp")
    tmp.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    tmp.replace(f)


def main():
    ap = argparse.ArgumentParser(description="Tubería única de la app de RO (C5)")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--ligero", action="store_true")
    g.add_argument("--completo", action="store_true")
    g.add_argument("--crudo", action="store_true", help="todo sin red (= --ligero --desde-crudo con los pasos del modo crudo)")
    ap.add_argument("--desde-crudo", action="store_true", help="cada paso en su variante sin red; los que no la tienen no corren")
    ap.add_argument("--crudo-donde-exista", action="store_true",
                    help="variante sin red si el paso la tiene; si no, su comando del modo (lecturas en vivo sin créditos)")
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--solo", default="")
    ap.add_argument("--forzar", action="store_true")
    ap.add_argument("--quien", default="tuberia")
    ap.add_argument("--esperas-cortas", action="store_true", help="reintentos a 1, 2 y 3 s (solo pruebas)")
    ap.add_argument("--sin-avisos", action="store_true")
    ap.add_argument("--aceptar-caida", default="", help="ids de fuente (data/fuentes.json) cuya caída es a propósito "
                    "(p. ej. se ha dado de baja la cuenta): no se restaura su último dato bueno")
    a = ap.parse_args()
    aceptar = {x.strip() for x in a.aceptar_caida.split(",") if x.strip()}
    modo = "completo" if a.completo else ("crudo" if a.crudo else "ligero")
    cfg = json.loads(PASOS.read_text())
    solo = {x.strip() for x in a.solo.split(",") if x.strip()} or None
    orden = plan(cfg, modo, "donde_exista" if a.crudo_donde_exista else a.desde_crudo, solo)

    if a.plan:
        print(f"Plan · modo {modo}{' · desde crudo' if a.desde_crudo else ''}")
        for p, cmd, motivo in orden:
            print(f"  {'▶' if cmd else '·'} {p['id']:<22} {' '.join(Path(c).name if c == sys.executable else c.replace(str(APP) + '/', '') for c in cmd) if cmd else '— ' + motivo}")
        return 0

    esperas = [1, 2, 3] if a.esperas_cortas else cfg.get("reintentos", {}).get("esperas_s", [30, 120, 480])
    E = ES.abrir()
    sentry = iniciar_sentry()
    try:
        cerrojo = E.bloqueo("tuberia", espera=False)
        cerrojo.__enter__()
    except ES.Ocupado:
        print("Ya hay una vuelta de la tubería en marcha: no se lanza otra (código 75).")
        return 75
    config.ESTADO_DIR.mkdir(parents=True, exist_ok=True)
    inicio = ahora()
    eid = E.nueva_ejecucion(modo + (" desde crudo" if a.desde_crudo else ""), a.quien)
    # Instantáneas: carpeta privada temporal FUERA del proyecto (nunca en despliegue/estado, nunca en el repositorio ni
    # en la base); se borra paso a paso. Se limpia cualquier resto de versiones anteriores de la tubería.
    shutil.rmtree(config.ESTADO_DIR / "instantaneas", ignore_errors=True)
    instantaneas = Path(tempfile.mkdtemp(prefix=f"ro_instantanea_{eid}_"))
    os.chmod(instantaneas, 0o700)
    registro = {"ejecucion": eid, "hora_datos": HORA_DATOS, "modo": modo, "desde_crudo": a.desde_crudo, "quien": a.quien, "inicio": inicio,
                "maquina": config.resumen()["maquina"], "motor_estado": E.motor, "pasos": [], "no_corren": []}
    fallidos = set()      # todo lo que no fue bien (vuelta «con_fallos», código 1, avisos)
    bloquean = set()      # lo que además deja sin correr a sus dependientes
    try:
        if os.environ.get("DATABASE_URL") or os.environ.get("RO_PUBLICAR_BASE") == "1":
            # Render: cada vuelta arranca con el disco vacío. Primero se baja lo último bueno de la base:
            # los datos a mano (crudos), las cachés de los lectores y data/ (para «último dato bueno»).
            import publicacion as PUB
            for esp in ("crudos", "cache", "data"):
                try:
                    v = PUB.bajar(esp, E=E)
                    registro.setdefault("bajado", {})[esp] = v
                except Exception as e:
                    print(f"  ✘ no pude bajar «{esp}» de la base: {sanear(str(e))}")
        print(f"Tubería · vuelta {eid} · modo {modo}{' · desde crudo' if a.desde_crudo else ''} · {inicio}")
        for p, cmd, motivo in orden:
            if not cmd:
                registro["no_corren"].append({"id": p["id"], "motivo": motivo})
                continue
            caidas = [d for d in p.get("depende", []) if d in bloquean]
            if caidas and not (p.get("siempre_al_final") or p.get("aunque_falle")):
                motivo = f"no corre porque falló {', '.join(caidas)}: se queda el último dato bueno"
                E.sellar(p["id"], False, motivo)
                fallidos.add(p["id"])
                bloquean.add(p["id"])
                registro["pasos"].append({"id": p["id"], "ok": False, "saltado": True, "motivo": motivo})
                print(f"  ✘ {p['id']:<22} {motivo}")
                continue
            if fresco(E, p, a.forzar):
                registro["no_corren"].append({"id": p["id"], "motivo": f"fue bien hace menos de {p['cada_min']} min"})
                continue
            t0 = time.time()
            r = correr_paso(p, cmd, modo, E, eid, esperas, registro, instantaneas, sentry, aceptar)
            ok = r["ok"]
            print(f"  {'✔' if ok else '✘'} {p['id']:<22} {round(time.time() - t0, 1)} s"
                  + ("" if ok else f" · {registro['pasos'][-1]['intentos'][-1]['error'][:110]} · se queda el dato anterior"
                     + ("" if r["bloquea"] else " (sus dependientes sí corren)")))
            if not ok:
                fallidos.add(p["id"])
            if r["bloquea"]:
                bloquean.add(p["id"])
            if not a.sin_avisos:
                # R16: UN aviso por paso con todas sus fuentes caídas (con el tope de 3 al día, una caída grande dejaba
                # 5 de 8 avisos «retenido»). Con una sola fuente, la clave sigue siendo «paso:fuente».
                if r["caidas"]:
                    fids = sorted(r["caidas"])
                    motivos = {x["id"]: x["motivo"] for x in registro["pasos"][-1].get("fuentes_caidas", [])}
                    detalle = "; ".join(f"«{fid}»: {motivos.get(fid) or 'sin motivo'}" for fid in fids)
                    AV.avisar("fuente_caida", f"{p['id']}:{'+'.join(fids)}",
                              ((f"{len(fids)} fuentes se han caído" if len(fids) > 1 else f"«{fids[0]}» se ha caído")
                               + f" ({p['id']}): la app sigue con su último dato bueno, marcado con su hora. {detalle}")[:400], E)
                if r["con_error"]:
                    fids = sorted(r["con_error"])
                    AV.avisar("fuente_caida", f"{p['id']}:{'+'.join(fids)}",
                              f"{', '.join('«' + x + '»' for x in fids)} no responde{'n' if len(fids) > 1 else ''} en "
                              f"{p['id']}: se queda su último dato bueno (con su hora de error).", E)
    finally:
        fin = ahora()
        estado = "ok" if not fallidos else "con_fallos"
        registro.update({"fin": fin, "estado": estado, "fallidos": sorted(fallidos)})
        E.cerrar_ejecucion(eid, estado, {"fallidos": sorted(fallidos), "pasos": len(registro["pasos"])})
        (config.ESTADO_DIR / "registros").mkdir(parents=True, exist_ok=True)
        nombre = f"{inicio.replace(':', '').replace('-', '')}_{modo}_{eid}.json"
        (config.ESTADO_DIR / "registros" / nombre).write_text(json.dumps(registro, ensure_ascii=False, indent=1))
        shutil.rmtree(instantaneas, ignore_errors=True)
        escribir_salud(E)
        if not a.sin_avisos:
            pasos_e0 = [{"id": x["id"], "ok": x["ok"], "segundos": sum(i["segundos"] for i in x.get("intentos", [])),
                         "salida": (x.get("intentos") or [{}])[-1].get("salida") or [x.get("motivo", "")]} for x in registro["pasos"]]
            AV.apuntar_vuelta_e0(modo, a.quien, pasos_e0, inicio, fin)
            for pid in sorted(fallidos):
                s = E.sello(pid) or {}
                bueno = s.get("ultimo_bueno")
                if not bueno or datetime.fromisoformat(bueno) < ahora_dt() - timedelta(hours=3):
                    AV.avisar("tuberia_dato_viejo", pid, f"La tubería no consigue «{pid}»: dato de {bueno or 'nunca'} "
                              f"({(s.get('motivo') or '')[:120]}).", E)
        if os.environ.get("DATABASE_URL") or os.environ.get("RO_PUBLICAR_BASE") == "1":
            # Render: el servicio web no ve este disco. Se publica data/ en la base como versión nueva (todo o nada);
            # los pasos que fallaron ya restauraron su versión anterior, así que lo publicado es siempre «dato bueno».
            try:
                import publicacion as PUB
                vc, _, _ = PUB.publicar("cache", origen=f"vuelta {eid} · {modo}", E=E)
                v, n, b = PUB.publicar("data", origen=f"vuelta {eid} · {modo}", E=E)
                registro["publicada"] = {"version": v, "ficheros": n, "bytes": b, "version_cache": vc}
                print(f"  ⇪ publicada la versión {v} de data/ ({n} ficheros) y la {vc} de las cachés")
            except Exception as e:
                print(f"  ✘ no se pudo publicar data/: {sanear(str(e))}")
                fallidos.add("publicar")
                AV.avisar("publicar", inicio[:10], f"La tubería no pudo publicar data/: {sanear(str(e))[:150]}", E)
        if os.environ.get("RO_PUBLICAR_CMD") and not fallidos:
            subprocess.run(os.environ["RO_PUBLICAR_CMD"], shell=True, cwd=APP)
        latido(fallo=bool(fallidos))
        cerrojo.__exit__(None, None, None)
        print(f"Fin · {estado} · registro {config.ESTADO_DIR / 'registros' / nombre}")
    return 0 if not fallidos else 1


if __name__ == "__main__":
    sys.exit(main())

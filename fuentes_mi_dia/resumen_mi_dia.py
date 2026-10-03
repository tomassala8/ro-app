#!/usr/bin/env python3
"""
resumen_mi_dia.py · N10 «carga rápida» (auditoría 37, causa 3): un fichero por persona con lo que pintan sus bloques.

Antes, Mi día pedía la configuración y después, en otra tanda, 10-15 ficheros enteros (captación, CRM, alertas…):
dos o tres viajes en serie y 150-450 KB. Ahora cada persona tiene data/mi_dia/p_<id>.json con:

  · config  → data/mi_dia/config.json recortado para ESA persona (como /api/modulo/mi_dia/config).
  · fuentes → cada fichero que usan los bloques de sus puestos (BLOQUES[..].usa y NUMERO[..].usa de
              modulos/mi_dia_bloques.js), RECORTADO EXACTAMENTE COMO LO RECORTA servir.py para esa persona
              (mismas funciones: entrada_datos_modulo, ve_alguno, recortar_modulo). Además se quitan las claves de
              primer nivel y los campos de las filas cuyo nombre no aparece en el código de Mi día (mi_dia.js,
              mi_dia_bloques.js, componentes.js) ni en config.json: no se pintan.
            Además, los de «Lo mío» (LO_MIO_USA: bandeja, producción y decisiones) cuando pueden traerle algo (A1).
  · faltan  → los ficheros que esa persona no puede leer o que no existen ({estado: 403|404|503, error}),
              para que el bloque diga lo mismo que antes sin preguntar.

Fuera del fichero (el navegador los pide aparte, a la vez): los que llevan «nombres_dueno» (ventas_ro/*: el nombre
completo del lead deja rastro y solo se abre en la petición de la persona) y los «solo_propio» (alertas/p_<id>).

Seguridad: el servidor sirve p_<id> con «solo_propio» (nadie lee el de otro, ni en «ver como») y lo vuelve a recortar
con las asignaciones de ESE momento (filas de clientes que ya no ve, dinero que ya no ve). Mi día en «ver como» no lo
usa: pide los ficheros uno a uno, como antes. Se rehace en cada vuelta de la tubería (paso mi_dia, el último).

Solo lectura de data/, reglas_permisos.json, modulos/ y local.db (no siembra tablas ni deja rastro). Escribe solo
data/mi_dia/p_<id>.json (el puesto que se abre primero) y data/mi_dia/puestos/<puesto>/p_<id>.json (cada puesto, para
quien cambia de puesto con los chips). Uso: python3 fuentes_mi_dia/resumen_mi_dia.py   (también lo llama generar_mi_dia.py)
"""
import json
import os
import re
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

AQUI = Path(__file__).resolve().parent.parent
DATA = AQUI / "data"
SALIDA = DATA / "mi_dia"
sys.path.insert(0, str(AQUI))

# Lo que el navegador pide aparte (ver arriba).
APARTE_POR_REGLA = ("nombres_dueno", "solo_propio")


def _usa_de_bloques():
    """{id_bloque: [fuentes]} y {id_numero: [fuentes]} leídos de modulos/mi_dia_bloques.js."""
    js = (AQUI / "modulos" / "mi_dia_bloques.js").read_text()
    lista = lambda s: re.findall(r"'([^']+)'", s)  # noqa: E731
    bloques = {m.group(1): lista(m.group(2)) for m in re.finditer(r"^def\('([\w\-]+)',\s*\[([^\]]*)\]", js, re.M)}
    numeros = {m.group(1): lista(m.group(2)) for m in re.finditer(r"^num\('([\w\-]+)',\s*\[([^\]]*)\]", js, re.M)}
    return bloques, numeros


def _lo_mio_usa():
    """A1 · «Lo mío»: los ficheros que lee además de los bloques (LO_MIO_USA de modulos/mi_dia_bloques.js)."""
    js = (AQUI / "modulos" / "mi_dia_bloques.js").read_text()
    m = re.search(r"^export const LO_MIO_USA = \[([^\]]*)\]", js, re.M)
    return re.findall(r"'([^']+)'", m.group(1)) if m else []


def _lo_mio_de(P, E, persona, rel):
    """¿Puede traer algo ese fichero a «Lo mío» de esta persona? (lo mismo que usaLoMio() de mi_dia.js, sin 403 de ruido)."""
    puestos = set(persona.get("puestos", []))
    if rel == "bandeja/bandeja":
        return bool(P.contexto(persona, E.crudo)["cartera_por_silla"].get("account"))
    if rel == "produccion/produccion":
        rp = (P.REGLAS.get("revision_piezas") or {}).get("por_estado") or {}
        return any((r.get("revisa") == "account" and puestos & {"account", "operaciones"}) or (r.get("revisa") == "persona" and r.get("persona") == persona["id"])
                   or (r.get("revisa") == "puestos" and (puestos & set(r.get("puestos") or []) or "operaciones" in puestos)) for r in rp.values())
    if rel == "decisiones/reloj":
        return bool(puestos & {"direccion", "proyectos"})
    return False


def _solo_revision(P, E, persona, doc):
    """Producción entra en el resumen SOLO por «Lo mío» (ningún bloque del puesto la lee): basta con las piezas que esperan
    revisión y que pueden tocarle (las de su cartera de account o, si es de operaciones, las que no tienen account; las de
    las reglas por persona o por puesto que le nombran), de 30 días o menos. mi_dia.js aplica después la regla exacta de
    Producción sobre este subconjunto, así que la cifra es la misma; solo pesa menos (Tomás: de 828 KB a unos pocos)."""
    if not isinstance(doc, dict):
        return doc
    rp = (P.REGLAS.get("revision_piezas") or {}).get("por_estado") or {}
    puestos = set(persona.get("puestos", []))
    cartera = set(P.contexto(persona, E.crudo)["cartera_por_silla"].get("account") or [])

    def puede(estado, cli, dias):
        r = rp.get(estado)
        if not r or (dias or 0) > 30:
            return False
        if r.get("revisa") == "account":
            return (cli in cartera) or "operaciones" in puestos
        if r.get("revisa") == "persona":
            return r.get("persona") == persona["id"]
        # V2: la técnica la revisa la jefa del área (revision_piezas.areas_tecnica); la que no tiene jefa de área, operaciones
        return bool(puestos & set(r.get("puestos") or [])) or "operaciones" in puestos
    return {**{k: v for k, v in doc.items() if k not in ("cola", "revisiones", "personas", "proyectos", "anuncios", "anuncios_resumen", "no_planificado", "sin_asignar")},
            "cola": [x for x in doc.get("cola") or [] if x.get("grupo") == "revision" and puede(x.get("estado"), x.get("cli"), x.get("dias_estado"))],
            "revisiones": [x for x in doc.get("revisiones") or [] if x.get("estado") != "bloqueado" and puede(x.get("estado"), x.get("cliente_id"), x.get("dias"))]}


def _solo_cartera(P, E, persona, doc):
    """La Bandeja entra SOLO por «Lo mío»: bastan los correos de su cartera de account (los que salen en «Lo mío»)."""
    if not isinstance(doc, dict):
        return doc
    cartera = set(P.contexto(persona, E.crudo)["cartera_por_silla"].get("account") or [])
    return {**{k: v for k, v in doc.items() if k not in ("correos", "llamadas", "triaje", "ruido")},
            "correos": [x for x in doc.get("correos") or [] if x.get("account_id") == persona["id"] or x.get("cliente_id") in cartera], "llamadas": []}


def _palabras_codigo():
    """Identificadores que aparecen en el código que pinta Mi día y en su configuración (lo que se puede leer)."""
    txt = "".join((AQUI / f).read_text() for f in ("modulos/mi_dia.js", "modulos/mi_dia_bloques.js", "componentes.js", "data/mi_dia/config.json"))
    return set(re.findall(r"[A-Za-z_$][\w$]*", txt))


def _podar(o, palabras, arriba=False):
    """Fuera las claves de primer nivel y los campos de fila (dicts dentro de listas) que el código no nombra.
    Los diccionarios que no son filas (mapas por id o por fecha) se dejan enteros."""
    if isinstance(o, dict):
        return {k: _podar(v, palabras) for k, v in o.items() if not arriba or k in palabras or k.startswith("_")}
    if isinstance(o, list):
        return [{k: _podar(v, palabras) for k, v in x.items() if k in palabras} if isinstance(x, dict) else _podar(x, palabras) for x in o]
    return o


def _cargar_servidor():
    """servir.py importado SIN arrancar: estado en memoria igual que E.cargar(), pero sin sembrar tablas ni escanear todo."""
    import servir as S
    P, E = S.P, S.E
    E.modulos = P.cargar_modulos()
    crudo = {n: json.loads((DATA / f"{n}.json").read_text()) for n in S.NUCLEO}
    crudo["para_confirmar"] = json.loads((DATA / "para_confirmar.json").read_text()) if (DATA / "para_confirmar.json").exists() else []
    ids = json.loads((DATA / "ids_clientes.json").read_text()) if (DATA / "ids_clientes.json").exists() else {}
    E.id_app = ids.get("portal_a_app") or {}
    E.aplicar_ajustes(crudo)          # lee historial y decisiones de local.db (Ajustes): las asignaciones de hoy
    E.crudo = crudo
    return S


def _servir_como(S, persona, rel, escaneados):
    """Lo mismo que GET /api/modulo/<rel> para «persona» sin «ver como» (servir.py, _api_get). (estado, objeto|error)."""
    P, E = S.P, S.E
    fichero = (DATA / f"{rel}.json").resolve()
    entrada = S.entrada_datos_modulo(rel)
    conf = entrada if isinstance(entrada, dict) else {"modulos": entrada}
    modulos, puestos_ok = conf.get("modulos") or [], conf.get("puestos")
    if not entrada or not (modulos or puestos_ok):
        return 403, "Sin regla en datos_de_modulo."
    if puestos_ok:
        nivel = "todo" if set(persona.get("puestos", [])) & set(puestos_ok) else None
    else:
        nivel = S.ve_alguno(persona, modulos)
    if conf.get("excluir_puestos") and set(persona.get("puestos", [])) <= set(conf["excluir_puestos"]):
        nivel = None
    if not nivel:
        return 403, "Estos datos son de una pantalla que no es de tu puesto."
    if not fichero.exists():
        return 404, f"No existe data/{rel}.json"
    if rel not in escaneados:
        pf = AQUI / "escaner_permitidos.json"
        permitidos = json.loads(pf.read_text()) if pf.exists() else {}
        escaneados[rel] = S.ESC.escanear_fichero(fichero, set(permitidos.get(f"data/{rel}.json", [])))
    if escaneados[rel]:
        return 503, "La puerta de secretos ha encontrado algo en este fichero: no se sirve."
    try:
        doc, aviso = S.leer_json_bueno(fichero)
    except S.DatoRoto as e:
        return 503, str(e)
    cp = P.contexto(persona, E.crudo)
    salida = S.recortar_modulo(persona, cp, doc, nivel, tuple(conf.get("solo_todo_sin_cliente", [])), tuple(conf.get("filas_lead", [])), conf)
    if aviso and isinstance(salida, dict):
        salida = {**salida, "_ultimo_dato_bueno": aviso}
    return 200, salida


def _escribir(ruta, obj):
    fd, tmp = tempfile.mkstemp(dir=ruta.parent, prefix=".tmp_", suffix=".json")
    with os.fdopen(fd, "w") as f:
        json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))
    os.chmod(tmp, 0o644)
    os.replace(tmp, ruta)


def _usa_de_puesto(config, bloques, numeros, puesto):
    """Ficheros que leen los bloques y el número que manda de un puesto (como mi_dia.js → render → «usa»)."""
    conf = config["puestos"][puesto]
    usa = []
    for b in conf.get("bloques", [])[: (config.get("comun") or {}).get("max_bloques", 7)]:
        usa += bloques.get(b if isinstance(b, str) else b.get("id"), [])
    num = conf.get("numero") or {}
    return list(dict.fromkeys(usa + numeros.get(num.get("calculo"), []) + numeros.get(num.get("proxy"), [])))


def mis_puestos(P, E, persona, config):
    """Los puestos con «Mi día» de la persona, en el orden de mi_dia.js (el primero es el que se abre en #/mi-dia).
    R12 (B-M06): el puesto de account sin cartera en esa silla no sale si tiene otro."""
    con_dia = [p for p in persona.get("puestos", []) if p in config.get("puestos", {})]
    cartera_account = P.contexto(persona, E.crudo)["cartera_por_silla"].get("account") or set()
    return [p for p in con_dia if not (p == "account" and not cartera_account)] if len(con_dia) > 1 else con_dia


def generar():
    t0 = time.time()
    S = _cargar_servidor()
    P, E = S.P, S.E
    config = json.loads((DATA / "mi_dia" / "config.json").read_text())
    bloques, numeros = _usa_de_bloques()
    lo_mio = _lo_mio_usa()
    palabras = _palabras_codigo()
    reglas = P.REGLAS.get("datos_de_modulo", {})
    aparte = {rel for rel, c in reglas.items() if isinstance(c, dict) and any(c.get(k) for k in APARTE_POR_REGLA)}
    es_aparte = lambda u: u in aparte or any("*" in k and re.fullmatch(k.replace("*", ".*"), u) for k in aparte)  # noqa: E731
    escaneados, hechos, kb, vigentes = {}, [], 0, set()
    for persona in E.crudo["personas"]:
        if persona.get("estado") != "activo" or not P.nivel_modulo(persona, E.modulos.get("mi-dia", {})):
            continue
        puestos = mis_puestos(P, E, persona, config)
        if not puestos:
            continue
        est, cfg = _servir_como(S, persona, "mi_dia/config", escaneados)
        if est != 200:
            continue
        servidas = {}
        for i, puesto in enumerate(puestos):
            usa = _usa_de_puesto(config, bloques, numeros, puesto)
            solo_lo_mio = {u for u in lo_mio if u not in usa and _lo_mio_de(P, E, persona, u)}
            usa += [u for u in lo_mio if u in solo_lo_mio]
            fuentes, faltan = {}, {}
            for rel in (u for u in usa if not es_aparte(u)):
                if rel not in servidas:
                    est, obj = _servir_como(S, persona, rel, escaneados)
                    servidas[rel] = (est, _podar(obj, palabras, arriba=True) if est == 200 else obj)
                est, obj = servidas[rel]
                if est == 200:
                    fuentes[rel] = (_solo_revision(P, E, persona, obj) if rel == "produccion/produccion" else _solo_cartera(P, E, persona, obj)
                                    if rel == "bandeja/bandeja" else obj) if rel in solo_lo_mio else obj
                else:
                    faltan[rel] = {"estado": est, "error": obj}
            doc = {"_meta": {"generado": datetime.now().isoformat(timespec="seconds"), "persona": persona["id"], "puesto": puesto,
                             "que_es": "Mi día de esta persona y puesto en un solo viaje (auditoría 37, causa 3). Cada fuente, recortada como la sirve servir.py y sin lo que no se pinta.",
                             "aparte": [u for u in usa if es_aparte(u)]},
                   "config": cfg, "fuentes": fuentes, "faltan": faltan}
            rutas = [SALIDA / "puestos" / puesto / f"p_{persona['id']}.json"] + ([SALIDA / f"p_{persona['id']}.json"] if i == 0 else [])
            for ruta in rutas:
                ruta.parent.mkdir(parents=True, exist_ok=True)
                _escribir(ruta, doc)
                vigentes.add(ruta)
                kb += ruta.stat().st_size / 1024
        hechos.append(persona["id"])
    # personas que ya no están activas o puestos que ya no tienen: fuera su fichero
    for viejo in [*SALIDA.glob("p_*.json"), *SALIDA.glob("puestos/*/p_*.json")]:
        if viejo not in vigentes:
            viejo.unlink()
    print(f"mi_dia: resumen de {len(hechos)} personas en data/mi_dia/p_<id>.json y puestos/<puesto>/p_<id>.json "
          f"({kb:,.0f} KB en total, {time.time() - t0:.1f} s)")
    return hechos


if __name__ == "__main__":
    generar()

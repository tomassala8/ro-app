"""Embudo agregado puro: identidad exacta, ventanas separadas, cobertura explícita.

No captura, API, archivos, DB ni datos personales de salida. Entradas previamente
autorizadas por el llamador. Un source es el espacio de identidad de origen;
adaptadores distintos deben conservarlo y resolver correlación en capa privada.
"""
from collections import Counter, defaultdict
from datetime import date, datetime, time, timedelta, timezone
import re

ETAPAS = ("recibido", "cualificado", "contacto", "respuesta", "cita", "asistencia", "venta")
UTC = timezone.utc


def _hora(value):
    try:
        if not isinstance(value, str):
            return None
        # No permitir que fromisoformat normalice offsets malformados (+02:99).
        m = re.fullmatch(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(Z|[+-]\d{2}:\d{2})", value)
        if m is None:
            return None
        offset = m.group(1)
        if offset != "Z":
            hours, minutes = int(offset[1:3]), int(offset[4:6])
            if minutes > 59 or hours > 14 or (hours == 14 and minutes != 0):
                return None
        x = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return x.astimezone(UTC) if x.tzinfo is not None else None
    except (TypeError, ValueError, OverflowError):
        return None


def _limite(value, fin=False):
    if isinstance(value, str) and len(value) == 10:
        try:
            return datetime.combine(date.fromisoformat(value), time.max if fin else time.min, UTC)
        except ValueError:
            return None
    return _hora(value)


def _id(value):
    # Identificadores opacos obligatorios. Nunca nombres/email/teléfono como join.
    return isinstance(value, str) and 0 < len(value) <= 160 and "@" not in value and not any(c.isspace() for c in value)


def _public_id(value):
    return _id(value) and re.fullmatch(r"[A-Za-z0-9_.:-]+", value) is not None and any(c.isalpha() for c in value)


def _cubierto(cobertura, clave, etapa, inicio, fin):
    intervals = []
    for c in cobertura:
        if not isinstance(c, dict) or (c.get("cliente_id"), c.get("source")) != clave:
            continue
        if c.get("completa") is not True or etapa not in (c.get("etapas") or []):
            continue
        a, b = _limite(c.get("desde")), _limite(c.get("hasta"), True)
        if a and b and a <= b:
            intervals.append((a, b))
    # Permite cobertura continua de varias páginas/días; huecos no son completos.
    cursor = inicio
    for a, b in sorted(intervals):
        if a > cursor:
            break
        if b >= fin:
            return True
        if b > cursor:
            cursor = b + timedelta(microseconds=1)
    return False


def _versiones_cobertura(cobertura, clave, inicio, fin):
    # Una regla de otro periodo no vuelve incomparable la ventana consultada.
    return {c.get("criterio_version") for c in cobertura
        if (c.get("cliente_id"), c.get("source")) == clave and c.get("completa") is True
        and "cualificado" in c["etapas"] and _public_id(c.get("criterio_version"))
        and _limite(c["desde"]) <= fin and _limite(c["hasta"], True) >= inicio}


def calcular(eventos, desde, hasta, corte, cobertura=None):
    """Devuelve JSON sin lead/event IDs: grupos, incidencias, limites.

    desde/hasta: fechas inclusivas UTC o timestamps con zona. corte: timestamp
    con zona >= hasta; explícito para replay determinista, nunca reloj del sistema.
    Cobertura: [{cliente_id,source,desde,hasta,etapas:[...],completa:true}].
    Una cobertura es una afirmación verificada del adaptador, no del usuario UI.
    """
    inicio, fin, observacion = _limite(desde), _limite(hasta, True), _hora(corte)
    if not inicio or not fin or not observacion or inicio > fin or observacion < fin:
        raise ValueError("Ventana inválida: timestamps con zona y corte >= hasta")
    incidencias = Counter()
    por_id, variantes, colisiones, claves = {}, defaultdict(Counter), set(), set()
    afectados, entrada_no_asignable = set(), False
    # La cobertura sólo puede ser una lista de contratos; membership en un texto
    # no acredita etapas completas. Conservar el resto de registros como parcial.
    raw_cobertura = [] if cobertura is None else cobertura
    cobertura = []
    if not isinstance(raw_cobertura, list):
        incidencias["cobertura_invalida"] += 1
        entrada_no_asignable = True
        raw_cobertura = []
    for c in raw_cobertura:
        scope = (c.get("cliente_id"), c.get("source")) if isinstance(c, dict) else (None, None)
        et = c.get("etapas") if isinstance(c, dict) else None
        a = _limite(c.get("desde")) if isinstance(c, dict) else None
        b = _limite(c.get("hasta"), True) if isinstance(c, dict) else None
        valid = (all(_public_id(x) for x in scope) and isinstance(et, list)
                 and all(isinstance(x, str) and x in ETAPAS for x in et)
                 and len(et) == len(set(et)) and type(c.get("completa")) is bool
                 and a is not None and b is not None and a <= b)
        if not valid:
            incidencias["cobertura_invalida"] += 1
            if all(_public_id(x) for x in scope):
                afectados.add(scope)
                claves.add(scope)
            else:
                entrada_no_asignable = True
            continue
        cobertura.append(c)
    # Primero resolver todos los conflictos, independiente del orden de llegada.
    for raw in eventos or []:
        if not isinstance(raw, dict):
            incidencias["evento_invalido"] += 1
            entrada_no_asignable = True
            continue
        cid, source, lead, eid = (raw.get(k) for k in ("cliente_id", "source", "lead_id", "event_id"))
        etapa, ts = raw.get("etapa"), _hora(raw.get("fecha"))
        if not _public_id(cid) or not _public_id(source) or not all(_id(x) for x in (lead, eid)) or etapa not in ETAPAS or ts is None:
            incidencias["evento_invalido"] += 1
            if _public_id(cid) and _public_id(source):
                afectados.add((cid, source))
                claves.add((cid, source))
            else:
                entrada_no_asignable = True
            continue
        clave = (cid, source)
        claves.add(clave)
        # Cualificación comercial debe estar definida, no inferida de campos llenos.
        version = raw.get("criterio_version") if etapa == "cualificado" else None
        confirmado = raw.get("confirmado") is True
        if etapa == "cualificado" and (not _public_id(version) or not confirmado):
            incidencias["cualificacion_sin_criterio_confirmado"] += 1
            afectados.add(clave)
            continue
        if etapa in ("asistencia", "venta") and not confirmado:
            incidencias["resultado_sin_confirmacion"] += 1
            afectados.add(clave)
            continue
        evento = (cid, source, lead, etapa, ts, version)
        identidad = (cid, source, eid)
        variantes[identidad][evento] += 1
    for identidad, contenidos in variantes.items():
        incidencias["replay_id"] += sum(n - 1 for n in contenidos.values())
        por_id[identidad] = next(iter(contenidos))
        if len(contenidos) > 1:
            colisiones.add(identidad)
    incidencias["event_id_conflictivo"] = len(colisiones)
    unicos = set()
    for eid, evento in por_id.items():
        if eid in colisiones:
            continue
        if evento in unicos:
            incidencias["replay_semantico"] += 1
            continue
        if evento[4] > observacion:
            incidencias["posterior_al_corte"] += 1
            continue
        unicos.add(evento)
    leads = defaultdict(list)
    for evento in unicos:
        leads[evento[:3]].append(evento)
    validos = defaultdict(list)
    cohortes = defaultdict(dict)
    afectados.update(e[:2] for ident, e in por_id.items() if ident in colisiones)
    for identidad, ev in leads.items():
        recibidos = [e[4] for e in ev if e[3] == "recibido"]
        if not recibidos:
            incidencias["lead_sin_recepcion"] += 1
            afectados.add(identidad[:2])
            continue
        recibido = min(recibidos)
        if len(recibidos) > 1:
            incidencias["recepcion_repetida"] += len(recibidos) - 1
        estados = set()
        for e in ev:
            if e[4] < recibido:
                incidencias["evento_antes_de_recepcion"] += 1
                afectados.add(identidad[:2])
                continue
            if e[3] == "recibido" and e[4] != recibido:
                continue
            validos[identidad[:2]].append(e)
            estados.add(e[3])
        if inicio <= recibido <= fin:
            cohortes[identidad[:2]][identidad[2]] = estados
    for c in cobertura:
        if isinstance(c, dict) and _public_id(c.get("cliente_id")) and _public_id(c.get("source")):
            claves.add((c["cliente_id"], c["source"]))
    if entrada_no_asignable:
        afectados.update(claves)
    grupos = []
    for clave in sorted(claves):
        cohorte = cohortes[clave]
        n = len(cohorte)
        versiones = {e[5] for e in validos[clave] if e[3] == "cualificado" and e[2] in cohorte}
        versiones_cobertura = _versiones_cobertura(cobertura, clave, inicio, observacion)
        criterio_comparable = len(versiones | versiones_cobertura) == 1 and bool(versiones_cobertura)
        cualificacion_cov = [c for c in cobertura if isinstance(c, dict) and c.get("criterio_version") in versiones_cobertura]
        completo_recibidos = _cubierto(cobertura, clave, "recibido", inicio, fin) and clave not in afectados
        etapas, periodo = {}, {}
        for etapa in ETAPAS:
            conocidos = sum(etapa in estados for estados in cohorte.values())
            limite = fin if etapa == "recibido" else observacion
            completo = completo_recibidos and _cubierto(cobertura, clave, etapa, inicio, limite) and clave not in afectados
            if etapa == "cualificado":
                completo = completo and criterio_comparable and _cubierto(cualificacion_cov, clave, etapa, inicio, limite)
            etapas[etapa] = {"observados": conocidos, "valor": conocidos if completo else None,
                "estado": "completo" if completo else "parcial" if conocidos else "desconocido",
                "denominador_recibidos": n if completo_recibidos else None,
                "tasa_sobre_recibidos": round(conocidos / n, 6) if completo and n else None}
            eventos_periodo = [e for e in validos[clave] if e[3] == etapa and inicio <= e[4] <= fin]
            cobertura_periodo = _cubierto(cobertura, clave, etapa, inicio, fin) and clave not in afectados
            if etapa == "cualificado":
                versiones_periodo = {e[5] for e in eventos_periodo}
                versiones_cov_periodo = _versiones_cobertura(cobertura, clave, inicio, fin)
                cobertura_periodo = cobertura_periodo and len(versiones_periodo | versiones_cov_periodo) == 1 and bool(versiones_cov_periodo) and _cubierto(cualificacion_cov, clave, etapa, inicio, fin)
            periodo[etapa] = {"eventos_observados": len(eventos_periodo),
                "leads_unicos_observados": len({e[2] for e in eventos_periodo}),
                "estado": "completo" if cobertura_periodo else "parcial" if eventos_periodo else "desconocido"}
        grupos.append({"cliente_id": clave[0], "source": clave[1],
            "cualificacion": {"criterios_observados": sorted(versiones), "criterio_comparable": criterio_comparable},
            "cohorte": {"recibidos_observados": n, "estado": "completo" if completo_recibidos else "parcial" if n else "desconocido", "etapas": etapas},
            "eventos_periodo": periodo})
    return {"version": 1, "ventana_recepcion": {"desde": inicio.isoformat(), "hasta": fin.isoformat()},
            "ventana_eventos": {"desde": inicio.isoformat(), "hasta": fin.isoformat()},
            "observado_hasta": observacion.isoformat(), "zona": "UTC", "grupos": grupos,
            "incidencias": dict(sorted((k, v) for k, v in incidencias.items() if v)),
            "limites": ["Tasas sólo sobre recibidos de la misma cohorte y con cobertura completa de ambas etapas.",
                "Etapas independientes: no se infiere contacto, cita ni asistencia a partir de una venta.",
                "Cualificación sin versión única compartida por eventos y cobertura no tiene tasa comparable.",
                "Venta confirmada no acredita cobro, margen, rentabilidad ni garantía contractual.",
                "No se unen distintas fuentes sin correlación explícita previa; faltantes no son ceros."]}

"""Gate puro de un aviso canónico de registros de horas; sin IO ni evaluación laboral."""
from datetime import datetime
import math
import re


def _fecha(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:\d{2})?)?", value):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        return None


def neutralizar_consejo_horas(candidato, hoy):
    """Protege reglas, precalculados y texto de IA únicamente de rrhh_no_imputa.

    Un descriptor futuro `medicion_horas` puede acreditar un registro observado,
    nunca trabajo realizado o jornada. Actualmente la fuente no lo proporciona.
    Permisos/dueño deben estar ya validados por el caller; este helper no concede acceso.
    """
    if not isinstance(candidato, dict) or candidato.get("tipo") != "rrhh_no_imputa":
        return candidato
    out = dict(candidato)
    m = candidato.get("medicion_horas")
    valid = False
    if isinstance(m, dict):
        periodo = m.get("periodo")
        desde = _fecha(periodo.get("desde")) if isinstance(periodo, dict) else None
        hasta = _fecha(periodo.get("hasta")) if isinstance(periodo, dict) else None
        lectura, limite = _fecha(m.get("fecha_fuente")), _fecha(hoy)
        horas = m.get("horas_registradas")
        valid = (m.get("fuente") == "ClickUp" and m.get("cobertura") in {"parcial", "completa"}
                 and isinstance(m.get("persona_id"), str) and bool(m["persona_id"])
                 and m.get("persona_id") == candidato.get("dueno")
                 and isinstance(horas, (int, float)) and not isinstance(horas, bool)
                 and math.isfinite(horas) and horas >= 0
                 and bool(desde and hasta and lectura and limite and desde <= hasta <= lectura <= limite))
    razon = ("Esta copia no acredita un recuento de horas con persona, periodo y cobertura verificados. "
             "Contrasta los registros en ClickUp antes de pedir una corrección. "
             "La ausencia de registros no demuestra ausencia de trabajo, incumplimiento de jornada ni disciplina.")
    evidencia = []
    if valid:
        razon = (f"La copia registra {m['horas_registradas']:g} h de {desde} a {hasta}; "
                 f"cobertura {m['cobertura']} y lectura {m['fecha_fuente']}. "
                 "Son horas registradas, no una medición del trabajo realizado ni del cumplimiento de jornada. "
                 "Contrasta el registro antes de pedir una corrección.")
        evidencia = [{"dato": f"{m['horas_registradas']:g} h registradas · {desde}–{hasta} · cobertura {m['cobertura']}",
                      "fecha": m["fecha_fuente"], "fuente": "ClickUp · registros de horas", "url": None}]
    # Ningún texto/cache de un modelo puede reintroducir la acusación ni su criterio disciplinario.
    out.update(que="Revisa los registros de horas en ClickUp", porque=razon,
               confianza="baja", confianza_porque="El registro no acredita trabajo realizado ni jornada; falta contrastar su cobertura y contexto.",
               gravedad="baja", orden=20, dato_en_duda=True, cifra=None, umbral=None,
               metrica=None, criterio=None, diagnostico=None, prioridad=None, prudencia=[],
               motivo_orden=None, motivo_linea=None, evidencia=evidencia, accion=None, cuando=None,
               medicion_horas={k: m[k] for k in ("persona_id", "fuente", "fecha_fuente", "horas_registradas", "cobertura")} | {"periodo": {"desde": desde, "hasta": hasta}} if valid else None,
               fuente={"texto": "ClickUp · registros de horas por contrastar", "url": None},
               ir_texto="Revisar registros", ir_alt=None)
    return out

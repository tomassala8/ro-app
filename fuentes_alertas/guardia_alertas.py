"""fuentes_alertas/guardia_alertas.py · A8 (2-oct-2026, noche) · guardia del servidor para «Posponer», el lote y (R16, N5)
«lo tengo», «resuelta», «no aplica» y «reabrir» de Alertas.

Nadie pospone (ni despacha en lote) alertas ajenas. El motor (generar_alertas.py) ya ignora esas filas y las deja en
«rechazadas»; esta guardia además las para en la puerta con 403 y rastro, antes de que entren en la cola.

Se engancha como ia.py, altas_personas.py y avisos.py (envuelve api_post de servir.py; el resto, igual que antes):

    # A8 (2-oct noche) · Alertas: nadie pospone ni despacha en lote alertas ajenas (fuentes_alertas/guardia_alertas.py)
    try:
        sys.path.insert(0, str(AQUI / "fuentes_alertas"))
        import guardia_alertas as GUARDIA_ALERTAS                  # noqa: E402
        GUARDIA_ALERTAS.enganchar(Manejador, sys.modules[__name__])
    except ImportError:
        pass

Pendiente de que el dueño de servir.py pegue esas líneas (../dudas_pintura.md, «A8 · guardia en servir.py»).
"""
import json
from datetime import datetime, timedelta
from pathlib import Path

AQUI = Path(__file__).resolve().parent.parent
# R16 (N5, auditoría 35b): también «lo tengo», «resuelta», «no aplica» y «reabrir» de una en una. Solo su dueño, su jefe,
# Mili y Tomás (o quien ve toda la agencia). «Vista» no cambia nada y no se guarda aquí.
TIPOS = {"alerta_posponer", "alerta_lote", "alerta_lo_tengo", "alerta_resuelta", "alerta_no_aplica", "alerta_reabrir"}
ACCIONES_LOTE = {"lo_tengo", "resuelta", "no_aplica", "posponer"}
MAX_DIAS = 31
MAX_LOTE = 200


def _fecha(s):
    try:
        return datetime.fromisoformat(str(s)[:16].replace("T", " "))
    except Exception:
        return None


def puede_actuar(persona, a):
    """La misma regla que el motor: su cadena (dueño → jefe → Mili/Tomás), el jefe del departamento o quien ve toda
    la agencia (dirección y operaciones)."""
    pid = persona["id"]
    return (pid in (a.get("escalado_cadena") or []) or pid == a.get("jefe_id")
            or bool(set(persona.get("puestos") or []) & {"direccion", "operaciones"}))


def revisar(persona, b, data=None):
    """None si la acción vale; si no, (código, motivo). Lee el fichero de alertas de ESA persona (solo lo suyo)."""
    data = Path(data or AQUI / "data")
    vp = b.get("vista_previa") if isinstance(b.get("vista_previa"), dict) else {}
    if b.get("tipo") == "alerta_lote":
        ids = [str(x) for x in (vp.get("ids") or [])]
        accion = vp.get("accion")
        if accion not in ACCIONES_LOTE or not ids or len(ids) > MAX_LOTE:
            return 400, f"Lote no válido: acción {sorted(ACCIONES_LOTE)} y de 1 a {MAX_LOTE} alertas."
        if accion == "no_aplica" and len(str(vp.get("motivo") or "").strip()) < 4:
            return 400, "«No aplica» necesita un motivo."
    else:
        ids, accion = [str(b.get("objeto") or "")], str(b.get("tipo") or "").replace("alerta_", "")
        if accion == "no_aplica" and len(str(vp.get("motivo") or b.get("texto") or "").strip()) < 4:
            return 400, "«No aplica» necesita un motivo."
    if accion == "posponer":
        hasta = _fecha(vp.get("hasta"))
        ahora = datetime.now()
        if not hasta or hasta <= ahora or hasta > ahora + timedelta(days=MAX_DIAS):
            return 400, f"Fecha de vuelta no válida: de mañana a {MAX_DIAS} días."
    try:
        doc = json.loads((data / "alertas" / f"p_{persona['id']}.json").read_text())
    except Exception:
        return 403, "No tienes alertas que gestionar."
    suyas = {a["id"]: a for a in doc.get("alertas") or []}
    ajenas = [i for i in ids if i not in suyas or not puede_actuar(persona, suyas[i])]
    if ajenas:
        return 403, f"No puedes cambiar alertas que no son tuyas ni de tu departamento ({len(ajenas)}): solo su dueño, su jefe, Mili y Tomás."
    return None


def enganchar(Manejador, servir):
    post_orig = Manejador.api_post

    def api_post(self, ruta, real, persona, b):
        # En «ver como» (persona ≠ real) servir.py ya contesta 403 de solo lectura: aquí solo lo propio.
        if (ruta == "/api/acciones" and isinstance(b, dict) and b.get("modulo") == "alertas" and b.get("tipo") in TIPOS
                and persona["id"] == real["id"]):
            r = revisar(real, b, getattr(servir, "DATA", None))
            if r:
                try:
                    servir.registrar_agrupado(real["id"], "alertas", "denegado", str(b.get("objeto"))[:80], {"motivo": r[1], "tipo": b.get("tipo")})
                except Exception:
                    pass
                return self.responder(r[0], {"error": r[1]})
        return post_orig(self, ruta, real, persona, b)

    Manejador.api_post = api_post

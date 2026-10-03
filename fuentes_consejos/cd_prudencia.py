#!/usr/bin/env python3
"""fuentes_consejos/cd_prudencia.py · Cerebro de decisiones v2 (3-oct-2026) · LO QUE UN CONSEJO NUNCA DICE.

Tres prohibiciones de RO (memoria de Tomás y decisiones firmadas), comprobadas en cada consejo (reglas o IA):
  1. Asesorar al cliente sobre su negocio o su contrato (feedback 25-sep: «Foco = campañas, no asesorar al cliente»).
  2. Prometer plazos o resultados (consejero-account-ro: «Nunca prometas resultados»; revisor-regulatorio-contenidos).
  3. Tocar precios, descuentos, pausas, altas o bajas (el «muro»: los decide dirección; se eleva con diagnóstico).
Y una de coherencia: nunca llamar «crítico» a un cliente que la verdad única no marca así (una sola vara de rojo).

revisar(c, grav_cliente, es_direccion) → (c_corregido, faltas[]). Si una frase cae, se sustituye por la versión segura;
si no hay versión segura, el consejo se descarta (None).
"""
import re

# (patrón, motivo, sustitución o None = descartar el consejo)
PROHIBIDO = [
    (re.compile(r"(?i)\b(rebaj|descuent|baja(r|le)? (el )?precio|cambi(a|ar) (el )?precio|sube (el )?precio|regala|gratis|bonifica)"),
     "tocar precios o descuentos (lo decide dirección)", "Eleva a dirección con el diagnóstico: el precio y los descuentos los decide Tomás"),
    (re.compile(r"(?i)\b(pausa(r|d)? (la |el )?(contrato|servicio|cuenta del cliente)|da(r|le)? de baja|cancela(r)? el contrato)"),
     "pausas, altas o bajas (lo decide dirección)", "Eleva a dirección con el diagnóstico: pausas y bajas las decide Tomás"),
    (re.compile(r"(?i)\b(garant[ií]za(le|r)?|te aseguro|aseg[uú]ra(le)?|prom[eé]te(le)?|en \d+ d[ií]as (tendr[aá]s?|llegar[aá]n?|habr[aá])|sin falta (tendr|lleg))"),
     "prometer plazos o resultados", None),
    (re.compile(r"(?i)\b(recomi[eé]nda(le)? (al cliente|al despacho) (que )?(contrate|cambie su|despida|suba sus tarifas|baje sus tarifas)|"
                r"dile al (cliente|despacho) c[oó]mo (llevar|gestionar) su (negocio|despacho|asesor[ií]a)|asesora(r|le)? (al cliente|al despacho) sobre su (negocio|contrato|fiscalidad))"),
     "asesorar al cliente sobre su negocio (el foco son las campañas)", None),
]
RE_CRITICO = re.compile(r"(?i)\bcr[ií]tic[oa]s?\b")


def revisar(c, grav_cliente=None, es_direccion=False):
    faltas = []
    out = dict(c)
    for campo in ("que", "porque"):
        t = str(out.get(campo) or "")
        for pat, motivo, sust in PROHIBIDO:
            if pat.search(t):
                if es_direccion and sust and "dirección" in sust:
                    continue                     # a dirección sí le toca decidir precio o baja: no se le «eleva» a sí misma
                faltas.append(motivo)
                if sust is None:
                    return None, faltas
                t = sust if campo == "que" else f"{sust}."
        out[campo] = t
    if out.get("cliente_id") and grav_cliente and grav_cliente != "critico":
        q = str(out.get("que") or "")
        if RE_CRITICO.search(q) and "crítico" in q:
            out["que"] = re.sub(r"[:,]?\s*es (un )?cliente cr[ií]tico", "", q).strip()
            faltas.append("«crítico» contra la verdad única")
    return out, faltas


def limpio_texto(t):
    """Para las salidas de la IA (y la prueba de lo servido): True si el texto no cae en NINGUNA prohibición. Lo que la IA
    escriba con un precio, un descuento, una baja o una promesa se descarta y queda el texto de la regla."""
    return not any(p.search(str(t or "")) for p, _m, _s in PROHIBIDO)

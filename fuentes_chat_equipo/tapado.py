"""tapado.py · el tapado de contraseñas y la limpieza de textos del chat, en un sitio que se puede importar.

Lo usan el generador del espejo de ClickUp (generar_chat_equipo.py) y los canales y grupos de la app (avisos.py, N15).
Antes vivía dentro de generar_chat_equipo.py, que al importarse pide la llave de ClickUp al llavero: por eso está aparte.
Mismas expresiones que la auditoría final (M4, punto 9): mejor tapar de más que de menos.
"""
import re

# Contraseñas y credenciales escritas en el chat («Usuario: … · Contraseña: …», «clave: | … |», «password=…»): se tapan
# ANTES de guardar nada. Solo con «:» o «=» detrás de la palabra, para no tocar la prosa («es clave que…»).
TAPADA = '•••• (tapada)'
RX_CREDENCIAL = re.compile(
    r'(?i)\b(usuari[oa]s?|user(?:name)?|login|contrase(?:ñ|n)as?|password|passw(?:or)?d|pass|clave|pwd|pin)'
    r'(\s*\**\s*[:=][\s|*`"\']*)'
    r'(?!…|\[correo\]|\[teléfono\]|••••)([^\s|*`"\'<>]+)')
RX_CLAVE_CERCA = re.compile(r'(contrase[ñn]a|password|passw|\bpass\b|\bclave\b|\bpwd\b|\bpin\b)', re.I)
RX_TRAS_DOS_PUNTOS = re.compile(r'((?:contrase[ñn]a|password|\bpass\b|\bclave\b|\bpwd\b|usuario|\buser\b)[^\n:]{0,80}?:\s*)(?!••••)([^\s,;)\]]+)', re.I)
RX_PAR = re.compile(r'(?<![/\w])([^\s():/@]{2,}):(?!//)([^\s()]{3,})')
# R16 (N1, N10): «la contraseña de su WordPress es Concilia2026!» (sin «:»). La misma expresión que servir.limpiar_texto():
# solo se tapa si lo de detrás parece una clave (cifra, símbolo, o mayúsculas y minúsculas con 8 o más), para no tocar
# «la clave es que…». Aquí la usa también el generador del espejo de ClickUp.
RX_CLAVE_ES = re.compile(r"(?i)\b(contrase(?:ñ|n)as?|password|passw(?:or)?d|clave|pass|pwd|pin|c[oó]digo de acceso)\b"
                         r"([^.\n]{0,50}?\b(?:es|era|será|sería|son|queda|nueva)\s+)(?!••••)([^\s,;)]+)")

RX_CORREO = re.compile(r'[\w.+-]+@[\w-]+(?:\.[\w-]+)+')
RX_TEL = re.compile(r'(?<![\w/])(?:\+34[\s.-]?|0034[\s.-]?)?[6789]\d{2}[\s.-]?\d{3}[\s.-]?\d{3}(?![\w/])')
RX_TEL_LARGO = re.compile(r'(?<![\w/])\+\d[\d\s.-]{8,16}\d(?![\w/])')     # +54 9 11 …, +58 …: el equipo es de tres países


def parece_clave(x):
    return bool(re.search(r"\d|[!@#$%&*_+=?¿¡]", x)) or (len(x) >= 8 and x != x.lower() and x != x.upper())


RX_SECRETO_URL = re.compile(r'(?i)([?&])(pwd|token|key|password|secret|access_token)=[^&\s)\]]+')


def tapar(t):
    # 1) «contraseña: X» directo; 2) «nueva contraseña de acceso de …: X» (palabras en medio);
    # 3) en un mensaje que habla de claves, cualquier «usuario:clave» suelto; 4) «la contraseña de … es X» sin «:»
    # (R16), solo si X parece una clave. Mejor tapar de más que de menos.
    if not isinstance(t, str):
        return t
    t = RX_CREDENCIAL.sub(lambda m: m.group(1) + m.group(2) + TAPADA, t)
    if RX_CLAVE_CERCA.search(t):
        t = RX_TRAS_DOS_PUNTOS.sub(lambda m: m.group(1) + TAPADA, t)
        t = RX_PAR.sub(lambda m: TAPADA if not m.group(1).isdigit() else m.group(0), t)
    t = RX_CLAVE_ES.sub(lambda m: m.group(1) + m.group(2) + (TAPADA if parece_clave(m.group(3)) else m.group(3)), t)
    return t


def tapar_todo(o):
    if isinstance(o, dict):
        return {k: tapar_todo(v) for k, v in o.items()}
    if isinstance(o, list):
        return [tapar_todo(v) for v in o]
    return tapar(o)


def limpiar(t, largo=2000):
    """Lo que escribe alguien en un canal de la app: contraseñas tapadas, sin correos, sin teléfonos y sin claves en enlaces."""
    t = str(t or '').replace('\r\n', '\n').strip()
    t = RX_SECRETO_URL.sub(r'\1\2=…', t)
    t = tapar(t)
    t = RX_CORREO.sub('[correo]', t)
    t = RX_TEL.sub('[teléfono]', t)
    t = RX_TEL_LARGO.sub('[teléfono]', t)
    return t[:largo]

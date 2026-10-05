"""Descripción operativa de una tarea. Allowlist y sanitización antes de caché/payload/prompt.
No carga adjuntos, contactos, campos personalizados ni instrucciones de otras tareas.
"""
import html
import re
from urllib.parse import urlsplit, urlunsplit
from permisos import sin_importes
from escaner_secretos import PATRONES


#215: mismos detectores de credenciales que la puerta de datos de la aplicación.
CREDENCIALES = tuple(rx for tipo, rx in PATRONES
                    if tipo in {'clave_api', 'jwt', 'bearer', 'clave_en_url', 'contrasena'})


SECRETOS = re.compile(r"contrase[ñn]a|password|credencial|secret|api[_ -]?key|access[_ -]?token|bearer\s|private[_ -]?key|sueldo|salario|n[oó]mina", re.I)


def texto_operativo(v, limite=12000):
    if not isinstance(v, str):
        return ""
    v = html.unescape(v)
    v = re.sub(r"<script\b[^>]*>.*?</script>", "", v, flags=re.I | re.S)
    v = re.sub(r"<[^>]*>", " ", v)
    v = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f\u202a-\u202e\u2066-\u2069]", "", v)
    def enlace(m):
        u = m[0]
        if SECRETOS.search(u):
            return "[enlace protegido omitido]"
        try:
            s = urlsplit(u)
            if s.username or s.password:
                return "[enlace protegido omitido]"
            return urlunsplit((s.scheme, s.netloc, s.path, "", ""))
        except ValueError:
            return "[enlace protegido omitido]"
    # Sanea enlaces completos antes de que otros redactores rompan su estructura.
    v = re.sub(r"https?://[^\s\"<>]+", enlace, v, flags=re.I)
    # Antes de separar líneas: las etiquetas markdown pueden ocupar varias líneas.
    for rx in CREDENCIALES:
        v = rx.sub("[dato protegido omitido]", v)
    v = "\n".join("[dato protegido omitido]" if SECRETOS.search(l) else l for l in v.splitlines())
    v = re.sub(r"\b(?:sk-[\w-]{12,}|gh[pousr]_[a-zA-Z0-9]{12,})\b", "[secreto omitido]", v)
    v = re.sub(r"[\w.+-]+@[\w.-]+\.[a-z]{2,}", "[correo omitido]", v, flags=re.I)
    v = re.sub(r"(?:\+\d{1,3}[ .-]?)?(?:\d[ .-]?){9,15}\b", "[teléfono omitido]", v)
    v = sin_importes(v)
    v = re.sub(r"(?:cuota|presupuesto|inversi[oó]n|facturaci[oó]n|coste)\s*[:=]?\s*\d[\d.,]*|\d[\d.,]*\s*(?:USD\b|d[oó]lares?\b)|\$\s*\d[\d.,]*", "[importe omitido]", v, flags=re.I)
    v = re.sub(r"https?://[^\s\"<>]+", enlace, v, flags=re.I)
    return v.strip()[:limite]


def contexto_operativo(t):
    """description o text_content llegan solo del registro exacto de ClickUp, no de entradas de horas."""
    if not isinstance(t, dict):
        return {"descripcion": ""}
    texto = texto_operativo(t.get("descripcion") or t.get("description") or t.get("text_content") or "", limite=12001)
    resultado = {"descripcion": texto[:12000]}
    if len(texto) > 12000 or t.get("descripcion_truncada") is True:
        resultado["descripcion_truncada"] = True
    return resultado

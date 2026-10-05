#!/usr/bin/env python3
"""
escaner_secretos.py · puerta de secretos (regla R16 del plan v2).

Antes de servir datos, busca en data/ (y en lo que se le pase) claves de API, tokens, contraseñas,
correos completos y teléfonos. Si encuentra algo, servir.py NO sirve ese fichero y avisa.

Permitido a propósito (no es una fuga):
  · Correos de RO (@rankingonline.com, @rankingonlinemarketing.com) SOLO en los campos «correo» y
    «otros_correos» de data/personas.json: son la llave con la que cada persona entra (Cloudflare Access)
    y servir.py no los manda a nadie salvo a Ajustes (Mili y Tomás).
  · Lo que diga escaner_permitidos.json ({"fichero": ["texto exacto permitido" | "sha256:<16 hex>", …]}), con su porqué.
    La forma «sha256:» permite un dato sin copiarlo (sha256 del texto encontrado, primeros 16 caracteres).

Uso:
  python3 escaner_secretos.py            # escanea data/ (sin _privado/) ; sale con 1 si hay hallazgos
  python3 escaner_secretos.py --json     # resultado en JSON (lo usa servir.py)
  python3 escaner_secretos.py --proyecto # todo el texto de la app (.json .md .js .py .txt .html .csv) salvo _privado,
                                         # _cache, _crudo, capturas e historia
"""
import ipaddress
import hashlib
import json
import re
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
DATA = AQUI / "data"
DOMINIOS_RO = ("@rankingonline.com", "@rankingonlinemarketing.com")
CAMPOS_CORREO_PERMITIDOS = {"correo", "otros_correos"}
DOMINIOS_RO_PROYECTO = DOMINIOS_RO + ("@rankingonline.es",)
DOMINIOS_EJEMPLO = re.compile(r"(?i)@(ejemplo|example)\.")
# Ficheros que SON una lista de correos por diseño (la lista de Cloudflare Access que genera build_data.py; no se sirve).
FICHEROS_LISTA_CORREOS = {"despliegue/lista_access.txt"}

PATRONES = [
    ("clave_api", re.compile(r"\b(sk-[A-Za-z0-9_-]{16,}|sk_live_[A-Za-z0-9]{16,}|pk_live_[A-Za-z0-9]{16,}|AKIA[0-9A-Z]{16}|AIza[0-9A-Za-z_-]{30,}|ghp_[A-Za-z0-9]{30,}|xox[abpr]-[A-Za-z0-9-]{10,}|pit-[0-9a-f]{8}-[0-9a-f-]{20,}|EAA[A-Za-z0-9]{40,})\b")),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}")),
    ("bearer", re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/-]{20,}")),
    ("clave_en_url", re.compile(r"(?i)[?&](api[_-]?key|access[_-]?token|token|key|secret|password)=[^&\s\"']{12,}")),
    ("correo", re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")),
    # M4/M6 (auditoría final, punto 9): contraseña escrita en un texto («Contraseña: …», «clave:\n| … |», «password=…»).
    # Solo con «:» o «=» detrás; lo ya tapado («•••• (tapada)», «…», «[oculto]») no cuenta.
    ("contrasena", re.compile(r"(?i)\b(?:contrase(?:ñ|n)as?|password|passw(?:or)?d|pass|clave|pwd)\s*\**\s*[:=][\s|*`\"']*(?!…|•|\[|\(|\{|\$|os\.|None\b|null\b|true\b|false\b)[^\s|*`\"'<>,;)\]}]{4,}")),
    ("telefono", re.compile(r"(?<![\w.\-/=#])(?:\+34[\s.-]?|0034[\s.-]?)?[6789]\d{2}[\s.-]?\d{3}[\s.-]?\d{3}(?![\w.\-/])")),
]
# Campos cuyo NOMBRE delata un secreto si tienen valor
CAMPOS_SECRETOS = re.compile(r"(?i)^(password|passwd|contrase(ñ|n)a|clave|secret|api_?key|token|access_token|refresh_token|pin|codigo_verificacion)$")


# Ronda 5: importes de sueldo. Solo pueden vivir en data/sueldos/_privado/ (que el escáner no recorre por ser _privado).
CAMPOS_SUELDO = re.compile(r"(?i)^(sueldo.*|salario.*|salary.*|nomina.*|bonus|coste_empresa|bruto|neto|salario_hora)$")


def _recorrer(obj, ruta=""):
    """Da (ruta, clave, valor_texto) de cada hoja de un JSON."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, (int, float)) and not isinstance(v, bool) and CAMPOS_SUELDO.match(str(k)):
                yield (f"{ruta}.{k}" if ruta else k, "__sueldo__", str(v))
            yield from _recorrer(v, f"{ruta}.{k}" if ruta else k)
            # «clave» con un identificador corto en minúsculas (p. ej. "ana") es una clave interna, no un secreto.
            if isinstance(v, (str, int)) and CAMPOS_SECRETOS.match(str(k)) and str(v).strip() \
                    and not (str(k).lower() == "clave" and (re.fullmatch(r"[a-z0-9_\-]{1,30}", str(v))
                                                         or re.fullmatch(r"[a-z0-9]+(?:[-_][a-z0-9]+){2,}", str(v)) and len(str(v)) <= 80)):
                yield (f"{ruta}.{k}" if ruta else k, "__campo__", str(v))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _recorrer(v, f"{ruta}[{i}]")
    elif isinstance(obj, str):
        yield (ruta, None, obj)


RX_VALOR_CLAVE = re.compile(r"^\w+\s*\**\s*[:=][\s|*`\"']*")


def _es_identificador(coincidencia):
    """«clave: 'ventas_ro'», «clave = fila.get(», «clave: `x:${…}`» son código o claves internas, no contraseñas.
    Un valor todo en minúsculas (con _ . - : y acentos) se da por identificador; una contraseña real lleva mayúsculas,
    cifras o símbolos. (Una contraseña toda en minúsculas se escaparía: se acepta a cambio de no ahogar el código.)"""
    v = RX_VALOR_CLAVE.sub("", coincidencia)
    if re.fullmatch(r"[A-Z][A-Z0-9_]{3,}", v):          # nombre de variable de entorno («Clave: ANTHROPIC_API_KEY»)
        return True
    return "${" in v or v.endswith("(") or bool(re.fullmatch(r"[a-záéíóúñü_][a-záéíóúñü0-9_.:\-]*\(?", v))


def _es_data_uri(texto):
    return texto.startswith("data:image/")


def _es_opcion_lsof(valor, coincidencia):
    """Opción -iTCP@IP[:puerto] / -iUDP@IP; nunca una excepción por dominio de correo."""
    texto = coincidencia.group(0)
    local, _, host = texto.partition("@")
    if local not in ("-iTCP", "-iUDP"):
        return False
    try:
        ipaddress.ip_address(host)
    except ValueError:
        return False
    antes = valor[coincidencia.start() - 1:coincidencia.start()] if coincidencia.start() else ""
    if antes and not (antes.isspace() or antes in "\"'`("):
        return False
    cola = valor[coincidencia.end():]
    if cola.startswith(":"):
        puerto = re.match(r":([0-9]{1,5})(?=$|[\s\"'`,;)])", cola)
        return bool(puerto and 1 <= int(puerto.group(1)) <= 65535)
    return not cola or cola[0].isspace() or cola[0] in "\"'`,;)"


def escanear_fichero(path, permitidos=(), correos_ro_ok=False):
    """correos_ro_ok: en el barrido del proyecto, los correos de RO (@rankingonline.com…) no son fuga."""
    hallazgos = []
    es_codigo = path.suffix.lower() in (".js", ".py")
    try:
        lista_correos = str(path.relative_to(AQUI)) in FICHEROS_LISTA_CORREOS
    except ValueError:
        lista_correos = False
    texto = path.read_text(errors="ignore")
    try:
        obj = json.loads(texto)
    except Exception:
        # Texto plano (.md, .py, .js…): una hoja por línea, con su número, para poder ir a arreglarla.
        obj = None
    if obj is None:
        hojas = ((f"línea {i}", None, l) for i, l in enumerate(texto.splitlines(), 1))
    else:
        hojas = _recorrer(obj)
    es_personas = path.name == "personas.json" and path.parent == DATA
    for ruta, marca, valor in hojas:
        if marca == "__sueldo__":
            hallazgos.append({"tipo": "sueldo", "ruta": ruta, "muestra": "[importe oculto]"})
            continue
        if marca == "__campo__":
            hallazgos.append({"tipo": "campo_secreto", "ruta": ruta, "muestra": "[oculto]"})
            continue
        if _es_data_uri(valor):
            continue
        for tipo, rx in PATRONES:
            for m in rx.finditer(valor):
                t = m.group(0)
                if t in permitidos or "sha256:" + hashlib.sha256(t.encode()).hexdigest()[:16] in permitidos:
                    continue
                if tipo == "correo":
                    if _es_opcion_lsof(valor, m):
                        continue
                    if correos_ro_ok and (t.lower().endswith(DOMINIOS_RO_PROYECTO) or DOMINIOS_EJEMPLO.search(t) or lista_correos):
                        continue
                    hoja = re.sub(r"\[\d+\]$", "", ruta).split(".")[-1]
                    if es_personas and hoja in CAMPOS_CORREO_PERMITIDOS and t.lower().endswith(DOMINIOS_RO):
                        continue
                if tipo == "contrasena" and (_es_identificador(t) or (es_codigo and t[:5].lower() == "clave")):
                    continue   # en .js/.py «clave» es un nombre de campo del código, no una contraseña
                if tipo == "telefono":
                    digitos = re.sub(r"\D", "", t)
                    # Fechas tipo 2026-10-02 o importes no casan con el patrón; descartamos ids largos pegados.
                    if len(digitos) not in (9, 11, 13) or len(set(digitos[-8:])) == 1:   # «600 000 000» es de relleno
                        continue
                muestra = "[oculto]" if tipo == "contrasena" else (t[:3] + "…" + t[-2:] if len(t) > 6 else "…")
                hallazgos.append({"tipo": tipo, "ruta": ruta, "muestra": muestra})
    return hallazgos


def es_privado(path):
    """Las carpetas _privado/ son almacenes solo del servidor (datos completos de leads para «ver datos»):
    servir.py no las sirve nunca en bloque; solo devuelve un campo con /api/ver_dato y deja rastro."""
    return "_privado" in Path(path).parts


def escanear(raiz=DATA, incluir_privado=False):
    permitidos_f = AQUI / "escaner_permitidos.json"
    permitidos = json.loads(permitidos_f.read_text()) if permitidos_f.exists() else {}
    resultado = {}
    for f in sorted(raiz.rglob("*.json")):
        if f.name.startswith(".") or (es_privado(f) and not incluir_privado):
            continue
        rel = str(f.relative_to(AQUI))
        h = escanear_fichero(f, set(permitidos.get(rel, [])))
        if h:
            resultado[rel] = h
    return resultado


# Ronda 7 (auditoría final, M6): el barrido del proyecto mira todo el texto que viajaría en una copia o un despliegue.
EXT_PROYECTO = {".json", ".md", ".js", ".py", ".txt", ".html", ".csv"}
CARPETAS_FUERA = {"_privado", "_cache", "_crudo", "capturas", "historia", "__pycache__", "node_modules", ".git", ".next", "dist", "generated", "legacy"}


def ficheros_proyecto(raiz=AQUI):
    for f in sorted(raiz.rglob("*")):
        if not f.is_file() or f.suffix.lower() not in EXT_PROYECTO or f.name.startswith("."):
            continue
        partes = f.relative_to(raiz).parts
        if CARPETAS_FUERA & set(partes) or f.stat().st_size > 30_000_000:
            continue
        yield f


def escanear_proyecto():
    """Todos los ficheros de texto de la app (.json .md .js .py .txt .html .csv), fuera de _privado/, _cache/, _crudo/,
    capturas/ e historia/. Cuenta correos (los de RO no) y teléfonos, claves, contraseñas escritas y sueldos.
    Antes solo miraba .json y, por un filtro mal hecho («om» + «ranking» en la ruta), dejaba pasar gmail.com y hotmail.com."""
    permitidos_f = AQUI / "escaner_permitidos.json"
    permitidos = json.loads(permitidos_f.read_text()) if permitidos_f.exists() else {}
    out = {}
    for f in ficheros_proyecto():
        rel = str(f.relative_to(AQUI))
        h = escanear_fichero(f, set(permitidos.get(rel, [])), correos_ro_ok=True)
        if h:
            out[rel] = h
    return out


def main():
    res = escanear_proyecto() if "--proyecto" in sys.argv else escanear()
    privados = sorted(str(f.relative_to(AQUI)) for f in DATA.rglob("*.json") if es_privado(f))
    if "--json" in sys.argv:
        print(json.dumps(res, ensure_ascii=False, indent=1))
    else:
        if not res:
            print("Escáner de secretos: limpio (" + ("proyecto" if "--proyecto" in sys.argv else "data/") + ").")
        if privados:
            print(f"Almacenes _privado/ (no se sirven nunca en bloque; esperado que lleven datos de leads): {len(privados)}")
            for p in privados:
                print(f"   · {p}")
        for f, hs in res.items():
            print(f"✗ {f}: {len(hs)} hallazgo(s)")
            for x in hs[:8]:
                print(f"   {x['tipo']:<14} {x['ruta']}  {x['muestra']}")
    sys.exit(1 if res else 0)


if __name__ == "__main__":
    main()

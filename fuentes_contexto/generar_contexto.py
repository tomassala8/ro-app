#!/usr/bin/env python3
"""fuentes_contexto/generar_contexto.py · Contexto del cliente para la Ficha (4-oct-2026). Sin red y sin IA.

Qué es: un resumen por cliente de quién es, qué hace, qué quiere y cómo trabajar con él. Lo prepara Claude a mano
fuera de la app (las «fichas de cliente») y llega como un JSON privado. Este generador lo valida, lo limpia y lo deja
en la app para que el account lo lea en la Ficha, en el bloque «Contexto del cliente» (solo lectura).

Lee (privado, nunca en el repositorio):
  1. la ruta de la variable RO_CONTEXTO_CLIENTES, si existe;
  2. si no, fuentes_contexto/_privado/contexto_clientes/fichas_clientes.json (carpeta _privado: fuera de git);
  3. si no, <RO_CRUDOS>/contexto_clientes/fichas_clientes.json (los datos a mano de config.py).
  Si no encuentra ninguno, avisa y sale con error SIN escribir nada: nunca pisa un fichero bueno con uno vacío.
Escribe:
  data/contexto/contexto_clientes.json   una fila por cliente con cliente_id (el servidor solo la manda a quien ve
                                         ese cliente; registrado en reglas_permisos.json → datos_de_modulo).

Privacidad (lo que se QUITA antes de escribir):
  · `quien_esta_detras` entero: nombres, papeles y notas de personas del despacho. Son datos personales y la Ficha ya
    tiene sus contactos por /api/ver_dato, con rastro.
  · `con_ro.account_ro`: el nombre de la persona de RO. Se queda solo `account_en_app` (sí/no).
  · En `lo_que_nos_han_dicho`, el campo `quien` (un nombre) se cambia por su `papel` si se reconoce; si no, nada.
  · Las personas de `quien_esta_detras` de TODAS las fichas (un solo mapa) se buscan en cualquier texto de cualquier
    cliente, sin importar tildes, mayúsculas ni espacios: nombre completo, y nombre de pila o apellido sueltos (≥3
    letras, con mayúscula, palabra entera). Se cambian por su papel en ese cliente, o por «[persona]». Ver Personas.
  · Todo lo que parezca un correo o un teléfono, en CUALQUIER texto, se cambia por «[dato quitado]».
  · `nombre`, `carpeta`, `bloque` y `fuentes` no pasan: el nombre ya lo tiene la app y las rutas no le sirven al account.
  Lo que NO se puede garantizar: un nombre que no esté en quien_esta_detras, un mote, o un nombre que también es palabra
  corriente a principio de frase («Paz», «Rosa»…). Por eso el texto lo revisa quien lo prepara.

Clientes: solo pasan los que existen en data/clientes.json (la lista de la app, como hace generar_whatsapp.py). Si el
id no coincide, se prueba por el nombre normalizado. Los que no casan se cuentan en `sin_emparejar` y sus ids salen
solo por pantalla, como aviso. Si la lista de la app no existe, pasan todos y la salida lo dice (`clientes_comprobados: false`).

  python3 fuentes_contexto/generar_contexto.py                      # escribe data/contexto/contexto_clientes.json
  python3 fuentes_contexto/generar_contexto.py --comprobar          # solo valida y cuenta; no escribe
  python3 fuentes_contexto/generar_contexto.py --entrada X --salida Y
  python3 fuentes_contexto/generar_contexto.py --forzar             # escribe aunque salgan muchos menos clientes
"""
import json
import os
import re
import sys
import tempfile
import unicodedata
from datetime import datetime
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
AQUI = Path(__file__).resolve().parent
sys.path.insert(1, str(APP))  # C5: rutas en config.py
import config  # noqa: E402

SALIDA = APP / "data" / "contexto" / "contexto_clientes.json"
LISTA_CLIENTES = APP / "data" / "clientes.json"
FUENTE = "fichas de cliente (privado)"
QUITADO = "[dato quitado]"

RE_CORREO = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
# Teléfono: prefijo opcional (+34, 0034, (+34)), y 8 a 13 cifras con espacios, puntos, barras, guiones, rayas o
# paréntesis entre medias. Luego _telefono() descarta lo que no lo es: menos de 9 cifras sin prefijo (años, dinero,
# CIF), fechas (18/09/2026, 2026-09-18) y rangos de años (2024-2025-2026).
RE_TELEFONO = re.compile(r"(?<!\d)(\(?(?:\+|00)\d{1,3}\)?[\s./\-–]{0,3})?\(?\d{2,3}\)?(?:[\s./()\-–]{0,3}\d){6,10}(?!\d)")
RE_FECHA = re.compile(r"(?<!\d)(?:(?:0?[1-9]|[12]\d|3[01])[/.\-](?:0?[1-9]|1[0-2])[/.\-](?:19|20)\d\d"
                      r"|(?:19|20)\d\d[/.\-](?:0?[1-9]|1[0-2])[/.\-](?:0?[1-9]|[12]\d|3[01]))(?!\d)")
RE_ID = re.compile(r"[a-z0-9][a-z0-9_-]*")
PERSONA = "[persona]"

LISTAS = ("objetivos", "les_gusta", "no_les_gusta", "como_trabajar_con_ellos", "huecos")
QUE_HACEN = ("a_que_se_dedican", "especialidad_o_nicho", "donde", "tamano", "web")

# Partículas de los nombres: nunca se buscan sueltas.
PARTICULAS = {"del", "las", "los", "san", "santa", "van", "von", "der"}
# Nombres que también son palabras corrientes con mayúscula a principio de frase o en títulos («Paz social», «Mar
# Menor», «Rosa de los vientos», «Claro, nos dijeron»). Sueltos solo se cambian con mayúscula y a MITAD de frase,
# donde casi seguro son la persona; a principio de frase se dejan (mejor un nombre de pila que un texto roto).
PALABRA_TAMBIEN = {"mar", "luz", "paz", "sol", "rosa", "pilar", "cruz", "blanca", "mercedes", "dolores", "angeles",
                   "rocio", "esperanza", "consuelo", "victoria", "gracia", "soledad", "nieves", "reyes", "santos",
                   "leon", "rey", "prado", "campos", "claro", "bueno", "bravo", "blanco", "moreno", "rubio", "franco",
                   "leal", "abril", "mayo", "cierto", "justo", "amor", "fe", "gloria", "salvador", "domingo"}


def _variantes():
    """{letra base: clase con todas sus variantes con tilde}, para buscar sin importar tildes ni mayúsculas."""
    g = {}
    for i in list(range(0x41, 0x5B)) + list(range(0x61, 0x7B)) + list(range(0xC0, 0x250)):
        ch = chr(i)
        b = unicodedata.normalize("NFKD", ch).encode("ascii", "ignore").decode().lower()
        if len(b) == 1 and b.isalpha():
            g.setdefault(b, set()).update({ch, ch.upper(), ch.lower()})
    return {b: "[" + "".join(sorted(v)) + "]" for b, v in g.items()}


VARIANTES = _variantes()


def rutas_entrada():
    """Orden de búsqueda de la entrada privada."""
    rutas = []
    if os.environ.get("RO_CONTEXTO_CLIENTES"):
        rutas.append(Path(os.environ["RO_CONTEXTO_CLIENTES"]).expanduser())
    rutas.append(AQUI / "_privado" / "contexto_clientes" / "fichas_clientes.json")
    rutas.append(config.CRUDOS / "contexto_clientes" / "fichas_clientes.json")
    return rutas


def norm(t):
    t = unicodedata.normalize("NFKD", t or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


def _patron(clave):
    """Clave normalizada («jose garcia») → patrón sin tildes ni mayúsculas, con espacios o guiones entre palabras."""
    return r"[\s\-]+".join("".join(VARIANTES.get(ch, re.escape(ch)) for ch in w) for w in clave.split())


def _telefono(m):
    t = m.group(0)
    nac = RE_FECHA.sub(" ", t[len(m.group(1) or ""):])
    grupos = re.findall(r"\d+", nac)
    if grupos and all(len(x) == 4 and x[:2] in ("19", "20") for x in grupos):
        return t                                               # 2024-2025-2026: años, no un teléfono
    if sum(map(len, grupos)) < (8 if m.group(1) else 9):
        return t                                               # fechas, dinero, CIF: se quedan
    return QUITADO


def _a_principio_de_frase(texto, i):
    antes = texto[:i].rstrip(" \t\"'«“(*·•-–—")
    return not antes or antes[-1] in ".!?¡¿:;\n"


class Personas:
    """Mapa ÚNICO de personas de TODAS las fichas (quien_esta_detras). Solo sirve para sustituir: no sale nunca.

    Se cambia, en cualquier texto de cualquier cliente y sin importar tildes, mayúsculas ni espacios:
      · el nombre completo (y sus variantes: sin el paréntesis, lo del paréntesis, cada uno de «A y B»);
      · el nombre de pila y cada apellido sueltos (≥3 letras), solo si van con mayúscula y como palabra entera;
        los de PALABRA_TAMBIEN, además, solo a mitad de frase; y no se tocan los que forman parte del nombre del propio
        cliente («García Abogados») ni de un sitio (`donde`): ahí casi siempre son la empresa o el lugar.
    Por qué se cambia: el papel de esa persona en ESE cliente si se sabe y es uno; si no, «[persona]».
    """

    def __init__(self, fichas):
        self.claves = {}       # clave normalizada → {"completo": bool, "papeles": {cliente_id: {papel}}}
        self.lugares, crudos = set(), []
        for c in fichas:
            if not isinstance(c, dict):
                continue
            cid = c.get("cliente_id")
            qh = c.get("que_hacen") if isinstance(c.get("que_hacen"), dict) else {}
            self.lugares.update(norm(str(qh.get("donde") or "")).split())
            for p in c.get("quien_esta_detras") or []:
                if isinstance(p, dict) and isinstance(p.get("nombre"), str) and p["nombre"].strip():
                    crudos.append((cid, p["nombre"], p.get("papel")))
        for cid, nombre, _ in crudos:
            for clave, completo in self._claves_de(nombre):
                self.claves.setdefault(clave, {"completo": completo, "papeles": {}})
        claves = sorted(self.claves, key=len, reverse=True)    # las largas primero: no partir una larga con una corta
        self.re = re.compile(r"(?<!\w)(?:" + "|".join(_patron(k) for k in claves) + r")(?!\w)", re.I) if claves \
            else None
        for cid, nombre, papel in crudos:   # el papel también se limpia: a veces nombra a otra persona
            papel = limpiar(papel, self) or "persona del despacho"
            for clave, _ in self._claves_de(nombre):
                self.claves[clave]["papeles"].setdefault(cid, set()).add(papel)

    @staticmethod
    def _claves_de(nombre):
        """Variantes de un nombre: [(clave normalizada, es_completo)]."""
        sin_par = re.sub(r"\([^)]*\)", " ", nombre)
        trozos = [nombre, sin_par] + re.findall(r"\(([^)]*)\)", nombre) + re.split(r"\s+[ye]\s+", sin_par)
        out = []
        for t in trozos:   # completo: al menos dos palabras con mayúscula («Juan de la Cruz» sí, «el de fiscal» no)
            k = norm(t)
            if sum(w[:1].isupper() for w in t.split()) >= 2 and not re.search(r"\s[ye]\s", f" {k} "):
                out.append((k, True))
        for w in re.findall(r"\w+", nombre):
            k = norm(w)
            if len(k) >= 3 and w[0].isupper() and k not in PARTICULAS:
                out.append((k, False))
        return out

    def papel(self, nombre, cid):
        """El papel de esa persona en ese cliente, o None si no se sabe o hay varios."""
        info = self.claves.get(norm(nombre or ""))
        ps = (info or {}).get("papeles", {}).get(cid) or set()
        return next(iter(ps)) if len(ps) == 1 else None

    def limpiar(self, texto, cid, propio=frozenset()):
        if not self.re or not texto:
            return texto

        def cambio(m):
            t, clave = m.group(0), norm(m.group(0))
            info = self.claves.get(clave)
            if info is None:
                return t
            if not info["completo"]:
                if not t[0].isupper() or clave in propio or clave in self.lugares:
                    return t
                if clave in PALABRA_TAMBIEN and _a_principio_de_frase(m.string, m.start()):
                    return t
            ps = (info["papeles"].get(cid) or set()) if cid else set()
            return next(iter(ps)) if len(ps) == 1 else PERSONA

        t = self.re.sub(cambio, texto)   # función, no cadena: una barra en el papel no rompe nada
        return re.sub(r"\[persona\](?:[\s\-]+\[persona\])+", PERSONA, t)   # «Josué Ficticio» suelto → uno solo


SIN_PERSONAS = Personas([])


def limpiar(texto, personas=SIN_PERSONAS, cid=None, propio=frozenset()):
    """Quita correos y teléfonos, y cambia los nombres conocidos por su papel. Devuelve None si queda vacío."""
    if texto is None:
        return None
    t = personas.limpiar(str(texto).strip(), cid, propio)
    t = RE_CORREO.sub(QUITADO, t)
    t = RE_TELEFONO.sub(_telefono, t)
    return t or None


def lista_textos(v, lim):
    if v is None:
        return []
    if isinstance(v, str):
        v = [v]
    if not isinstance(v, list):
        raise ValueError("no es una lista")
    return [x for x in (lim(i) for i in v if isinstance(i, (str, int, float))) if x]


def normalizar_cliente(c, actualizado, pers=SIN_PERSONAS):
    """Una ficha de entrada → una fila de salida. Lanza ValueError si la ficha no vale."""
    if not isinstance(c, dict):
        raise ValueError("la ficha no es un objeto")
    cid = c.get("cliente_id")
    if not isinstance(cid, str) or not RE_ID.fullmatch(cid):
        raise ValueError("cliente_id vacío o con forma rara")
    propio = frozenset(norm(c.get("nombre") or "").split())   # «García Abogados»: ahí García es la empresa
    lim = lambda t: limpiar(t, pers, cid, propio)  # noqa: E731
    qh = c.get("que_hacen") or {}
    if not isinstance(qh, dict):
        raise ValueError("que_hacen no es un objeto")
    cr = c.get("con_ro") or {}
    if not isinstance(cr, dict):
        raise ValueError("con_ro no es un objeto")
    dicho = []
    for d in c.get("lo_que_nos_han_dicho") or []:
        if isinstance(d, str):
            d = {"cita": d}
        if not isinstance(d, dict):
            continue
        cita = lim(d.get("cita"))
        if not cita:
            continue
        dicho.append({"cita": cita, "fecha": limpiar(d.get("fecha")),
                      "papel": pers.papel(d.get("quien"), cid) if isinstance(d.get("quien"), str) else None})
    fila = {
        "cliente_id": cid,
        "en_una_frase": lim(c.get("en_una_frase")),
        "que_hacen": {k: lim(qh.get(k)) for k in QUE_HACEN},
        "con_ro": {"servicios": lim(cr.get("servicios")),
                   "cliente_desde": limpiar(cr.get("cliente_desde")),
                   "account_en_app": cr.get("account_en_app") if isinstance(cr.get("account_en_app"), bool) else None},
        "lo_que_nos_han_dicho": dicho,
        "situacion_actual": lim(c.get("situacion_actual")),
        "estado": limpiar(c.get("estado")) or "activo",
        "actualizado": actualizado,
    }
    for k in LISTAS:
        try:
            fila[k] = lista_textos(c.get(k), lim)
        except ValueError:
            raise ValueError(f"{k} no es una lista")
    orden = ("cliente_id", "en_una_frase", "que_hacen", "con_ro", "objetivos", "lo_que_nos_han_dicho", "les_gusta",
             "no_les_gusta", "como_trabajar_con_ellos", "situacion_actual", "huecos", "estado", "actualizado")
    return {k: fila[k] for k in orden}


def clientes_app(ruta):
    """(ids, {nombre normalizado: id}) de la lista de la app, o (None, None) si no está."""
    try:
        lista = json.loads(Path(ruta).read_text())
    except (OSError, ValueError):
        return None, None
    if isinstance(lista, dict):
        lista = lista.get("clientes") or []
    ids = {c.get("id") or c.get("cliente_id") for c in lista if isinstance(c, dict)}
    por_nombre = {norm(c.get("nombre")): (c.get("id") or c.get("cliente_id")) for c in lista
                  if isinstance(c, dict) and c.get("nombre")}
    return ids - {None}, por_nombre


def construir(doc, lista_clientes=LISTA_CLIENTES):
    """Valida y normaliza el documento de entrada. Devuelve (salida, avisos)."""
    if not isinstance(doc, dict) or not isinstance(doc.get("clientes"), list):
        raise ValueError("la entrada no tiene la forma {generado, fuente, clientes: [...]}")
    actualizado = str(doc.get("generado") or "")[:10] or None
    ids, por_nombre = clientes_app(lista_clientes)
    pers = Personas(doc["clientes"])   # un solo mapa: el nombre de una persona puede salir en la ficha de otro cliente
    filas, avisos, sin_emparejar, vistos = [], [], [], set()
    for i, c in enumerate(doc["clientes"]):
        try:
            fila = normalizar_cliente(c, actualizado, pers)
        except ValueError as e:
            avisos.append(f"ficha {i}: {e} (se salta)")
            continue
        if ids is not None and fila["cliente_id"] not in ids:
            otro = por_nombre.get(norm(c.get("nombre")))
            if not otro:
                sin_emparejar.append(fila["cliente_id"])
                continue
            fila["cliente_id"] = otro
        if fila["cliente_id"] in vistos:
            avisos.append(f"{fila['cliente_id']}: repetido (se queda el primero)")
            continue
        vistos.add(fila["cliente_id"])
        filas.append(fila)
    salida = {
        "generado": datetime.now().isoformat(timespec="minutes"),
        "fuente": FUENTE,
        "actualizado": actualizado,
        "clientes_comprobados": ids is not None,
        "regla": "Solo lectura. Sin personas ni datos de contacto: esos van por «ver datos» en la Ficha.",
        "clientes": sorted(filas, key=lambda x: x["cliente_id"]),
        "sin_emparejar": len(sin_emparejar),   # solo el número: la salida la ven accounts sin esos clientes
    }
    if sin_emparejar:
        avisos.append("sin emparejar con la app: " + ", ".join(sorted(sin_emparejar)))
    return salida, avisos


def _arg(nombre):
    if nombre in sys.argv:
        i = sys.argv.index(nombre)
        if i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    return None


def main():
    entrada = Path(_arg("--entrada")).expanduser() if _arg("--entrada") else None
    salida_ruta = Path(_arg("--salida")).expanduser() if _arg("--salida") else SALIDA
    lista = Path(_arg("--lista-clientes")).expanduser() if _arg("--lista-clientes") else LISTA_CLIENTES  # pruebas
    candidatas = [entrada] if entrada else rutas_entrada()
    ruta = next((r for r in candidatas if r.is_file()), None)
    if ruta is None:
        print("contexto: no encuentro las fichas de cliente. Busqué en:", file=sys.stderr)
        for r in candidatas:
            print(f"  · {r}", file=sys.stderr)
        print("Pon la ruta en RO_CONTEXTO_CLIENTES o usa --entrada. No escribo nada.", file=sys.stderr)
        return 2
    try:
        doc = json.loads(ruta.read_text())
        salida, avisos = construir(doc, lista)
    except (OSError, ValueError) as e:
        print(f"contexto: la entrada no vale ({e}). No escribo nada.", file=sys.stderr)
        return 2
    for a in avisos:
        print(f"  aviso: {a}", file=sys.stderr)
    n = len(salida["clientes"])
    print(f"contexto: {n} clientes · sin emparejar {salida['sin_emparejar']} · avisos {len(avisos)}"
          f"{'' if salida['clientes_comprobados'] else ' · lista de la app no encontrada: pasan todos'}")
    if "--comprobar" in sys.argv:
        return 0 if n else 1
    if n == 0:
        print("contexto: 0 clientes válidos. No pisó la salida que hubiera.", file=sys.stderr)
        return 1
    # Red de seguridad: si salen muchos menos clientes que en la última vuelta, algo va mal en la entrada.
    try:
        antes = len(json.loads(salida_ruta.read_text()).get("clientes") or [])
    except (OSError, ValueError, AttributeError):
        antes = 0
    if antes and n < antes / 2 and "--forzar" not in sys.argv:
        print(f"contexto: salen {n} clientes y antes había {antes}. No escribo (usa --forzar si es correcto).",
              file=sys.stderr)
        return 1
    salida_ruta.parent.mkdir(parents=True, exist_ok=True)
    # Escritura atómica: temporal con nombre único en la misma carpeta, fsync y os.replace. Nunca queda a medias.
    with tempfile.NamedTemporaryFile("w", dir=salida_ruta.parent, prefix=salida_ruta.name + ".", suffix=".tmp",
                                     delete=False, encoding="utf-8") as f:
        try:
            f.write(json.dumps(salida, ensure_ascii=False, indent=1))
            f.flush()
            os.fsync(f.fileno())
        except BaseException:
            f.close()
            os.unlink(f.name)
            raise
    os.replace(f.name, salida_ruta)
    print(f"contexto: escrito {salida_ruta}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

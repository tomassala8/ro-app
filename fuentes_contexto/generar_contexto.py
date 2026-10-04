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
  · Los nombres completos de `quien_esta_detras` que aparezcan en cualquier texto del cliente se cambian por su papel.
  · Todo lo que parezca un correo o un teléfono, en CUALQUIER texto, se cambia por «[dato quitado]».
  · `nombre`, `carpeta`, `bloque` y `fuentes` no pasan: el nombre ya lo tiene la app y las rutas no le sirven al account.
  Lo que NO se puede garantizar: un nombre de pila suelto dentro de una cita. Por eso el texto lo revisa quien lo prepara.

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
# Teléfono: 9 a 13 cifras seguidas o con espacios, puntos o guiones, con o sin prefijo. Las fechas (8 cifras) no caen.
RE_TELEFONO = re.compile(r"(?<![\w/])(?:\+|00)?(?:\d[\s.-]?){8,12}\d(?![\w/])")
RE_ID = re.compile(r"[a-z0-9][a-z0-9_-]*")

LISTAS = ("objetivos", "les_gusta", "no_les_gusta", "como_trabajar_con_ellos", "huecos")
QUE_HACEN = ("a_que_se_dedican", "especialidad_o_nicho", "donde", "tamano", "web")


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


def limpiar(texto, personas=None):
    """Quita correos y teléfonos, y cambia los nombres conocidos por su papel. Devuelve None si queda vacío."""
    if texto is None:
        return None
    t = str(texto).strip()
    for nombre, papel in (personas or {}).items():
        t = re.sub(re.escape(nombre), papel, t, flags=re.I)
    t = RE_CORREO.sub(QUITADO, t)
    t = RE_TELEFONO.sub(QUITADO, t)
    return t or None


def lista_textos(v, personas):
    if v is None:
        return []
    if isinstance(v, str):
        v = [v]
    if not isinstance(v, list):
        raise ValueError("no es una lista")
    return [x for x in (limpiar(i, personas) for i in v if isinstance(i, (str, int, float))) if x]


def personas_de(c):
    """{nombre completo: papel} de quien_esta_detras. Solo para sustituir; no sale nunca en la salida."""
    out = {}
    for p in c.get("quien_esta_detras") or []:
        if isinstance(p, dict) and isinstance(p.get("nombre"), str) and len(p["nombre"].strip()) >= 5:
            out[p["nombre"].strip()] = (p.get("papel") or "persona del despacho").strip() or "persona del despacho"
    # los nombres largos primero, para no partir uno largo con uno corto
    return dict(sorted(out.items(), key=lambda kv: -len(kv[0])))


def normalizar_cliente(c, actualizado):
    """Una ficha de entrada → una fila de salida. Lanza ValueError si la ficha no vale."""
    if not isinstance(c, dict):
        raise ValueError("la ficha no es un objeto")
    cid = c.get("cliente_id")
    if not isinstance(cid, str) or not RE_ID.fullmatch(cid):
        raise ValueError("cliente_id vacío o con forma rara")
    pers = personas_de(c)
    qh = c.get("que_hacen") or {}
    if not isinstance(qh, dict):
        raise ValueError("que_hacen no es un objeto")
    cr = c.get("con_ro") or {}
    if not isinstance(cr, dict):
        raise ValueError("con_ro no es un objeto")
    papeles = {norm(n): p for n, p in pers.items()}
    dicho = []
    for d in c.get("lo_que_nos_han_dicho") or []:
        if isinstance(d, str):
            d = {"cita": d}
        if not isinstance(d, dict):
            continue
        cita = limpiar(d.get("cita"), pers)
        if not cita:
            continue
        dicho.append({"cita": cita, "fecha": limpiar(d.get("fecha")),
                      "papel": papeles.get(norm(d.get("quien") or "")) if d.get("quien") else None})
    fila = {
        "cliente_id": cid,
        "en_una_frase": limpiar(c.get("en_una_frase"), pers),
        "que_hacen": {k: limpiar(qh.get(k), pers) for k in QUE_HACEN},
        "con_ro": {"servicios": limpiar(cr.get("servicios"), pers),
                   "cliente_desde": limpiar(cr.get("cliente_desde")),
                   "account_en_app": cr.get("account_en_app") if isinstance(cr.get("account_en_app"), bool) else None},
        "lo_que_nos_han_dicho": dicho,
        "situacion_actual": limpiar(c.get("situacion_actual"), pers),
        "estado": limpiar(c.get("estado")) or "activo",
        "actualizado": actualizado,
    }
    for k in LISTAS:
        try:
            fila[k] = lista_textos(c.get(k), pers)
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
    filas, avisos, sin_emparejar, vistos = [], [], [], set()
    for i, c in enumerate(doc["clientes"]):
        try:
            fila = normalizar_cliente(c, actualizado)
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
    tmp = salida_ruta.with_suffix(".tmp")
    tmp.write_text(json.dumps(salida, ensure_ascii=False, indent=1))
    tmp.replace(salida_ruta)
    print(f"contexto: escrito {salida_ruta}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

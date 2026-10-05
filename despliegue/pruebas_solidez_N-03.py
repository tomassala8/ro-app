#!/usr/bin/env python3
"""despliegue/pruebas_solidez_N-03.py · N-03: Metricool. Un error de la API = el último dato bueno con aviso, nunca «0 publicaciones».

Uso:  python3 despliegue/pruebas_solidez_N-03.py
Sin red ni llaves: `mc` y `urllib.request.urlopen` son dobles; la base es un SQLite temporal (RO_DB); la caché y los
datos de clientes van a una carpeta temporal (nunca se toca `fuentes_redes/_cache` ni `data/`). `generar_redes` se importa, no se ejecuta.
(1) 1.ª vuelta buena: 2 marcas, 3 posts, estado ok.
(2) 2.ª vuelta con la API caída (URLError): las mismas 2 marcas y 3 posts, marcadas `_viejo` con `_desde`;
    `construir()` dice `estado_fuente: dato_viejo` y NO baja los programados a 0.
(3) Una marca que falla sola (las demás bien): esa vuelve con su último dato, las otras con el nuevo.
(4) Primera vuelta caída y sin nada guardado: `sin_dato` (también en la caché), ninguna marca inventada, `construir()` dice `sin_dato`.
(5) Primera vuelta caída con la caché de ficheros de ayer: se queda con ella (viejo), no la pisa con vacío.
(6) Con la API al día, `_meta` no lleva claves de aviso (el fichero sale como siempre).
Sale 0 si pasa; si no, 1.
"""
import io
import json
import os
import sys
import tempfile
import types
import urllib.error
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
os.environ.pop("DATABASE_URL", None)
tmpdb = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
tmpdb.close()
os.environ["RO_DB"] = tmpdb.name
os.environ["RO_SIN_LLAVES"] = "1"
sys.path.insert(0, str(RAIZ))
fallos = []


def ok(t):
    print(f"  ✔ {t}")


def mal(t):
    print(f"  ✘ {t}")
    fallos.append(t)


def borrar_db():
    # vaciar la tabla entre escenarios sin tocar nada más
    from fuentes import lectura as L
    con = L.conectar()
    try:
        with con:
            con.execute("DELETE FROM fuente_lectura")
    finally:
        con.close()


try:
    mc = types.ModuleType("mc")
    mc.llave = lambda n: "falsa"
    sys.modules["mc"] = mc
    from fuentes_redes import generar_redes as R

    carpeta = Path(tempfile.mkdtemp(prefix="n03_"))
    (carpeta / "data" / "clientes").mkdir(parents=True)
    (carpeta / "data" / "clientes" / "cli_falso.json").write_text(json.dumps(
        {"id": "cli_falso", "nombre": "Cliente Falso", "fuentes": {"metricool": {"emparejado": {"id": 1}}}}))
    (carpeta / "data" / "personas.json").write_text("[]")
    R.APP = str(carpeta)
    R.CACHE = str(carpeta / "metricool.json")

    estado = {"modo": "bien", "falla_marca": None}
    hoy = R.HOY

    def respuesta(obj):
        r = io.BytesIO(json.dumps(obj).encode())
        return r

    def post(i, marca):
        return {"id": f"{marca}-{i}", "publicationDate": {"dateTime": f"{hoy + R.dt.timedelta(days=i)}T10:00:00"},
                "text": f"Post {i} de la marca {marca}", "draft": False, "autoPublish": True,
                "providers": [{"network": "instagram", "status": "PENDING", "detailedStatus": "", "publicUrl": None}]}

    def urlopen_falso(req, timeout=None):
        if estado["modo"] == "caida":
            raise urllib.error.URLError("sin red (doble)")
        url = req.full_url
        if "simpleProfiles" in url:
            return respuesta([{"id": 1, "label": "Cliente Falso", "instagram": "x", "correo_dueno": "alguien@ejemplo.test"},
                              {"id": 2, "label": "Otra Marca", "instagram": "y"}])
        marca = int(url.split("blogId=")[1].split("&")[0])
        if estado["falla_marca"] == marca:
            raise urllib.error.URLError("marca caída (doble)")
        if "scheduler/posts" in url:
            return respuesta({"data": [post(1, marca), post(2, marca)] if marca == 1 else [post(3, marca)]})
        return respuesta({"data": []})

    real = urllib.request.urlopen
    urllib.request.urlopen = urlopen_falso
    try:
        # (1)
        a = R.leer_en_vivo()
        n_posts = sum(len(m["posts"]) for m in a["marcas"])
        if len(a["marcas"]) == 2 and n_posts == 3 and a["estado"] == "ok" and not any(m.get("_viejo") for m in a["marcas"]):
            ok("1.ª vuelta: 2 marcas, 3 posts, estado ok")
        else:
            mal(f"1.ª vuelta: marcas={len(a['marcas'])} posts={n_posts} estado={a.get('estado')}")
        # (6)
        d0 = R.construir(a)
        if not ({"estado_fuente", "dato_viejo_desde", "error_fuente", "marcas_sin_dato", "marcas_con_dato_viejo"} & set(d0["_meta"])):
            ok("con la API al día, _meta no lleva claves de aviso")
        else:
            mal(f"_meta con avisos sin motivo: {sorted(d0['_meta'])}")
        prog_ok = d0["resumen"]["programadas_14"]
        # (2)
        estado["modo"] = "caida"
        b = R.leer_en_vivo()
        n_b = sum(len(m["posts"]) for m in b["marcas"])
        if len(b["marcas"]) == 2 and n_b == 3 and b["estado"] == "viejo" and all(m.get("_viejo") and m.get("_desde") for m in b["marcas"]):
            ok("API caída: las mismas 2 marcas y 3 posts, con _viejo y _desde")
        else:
            mal(f"API caída: marcas={len(b['marcas'])} posts={n_b} estado={b.get('estado')} viejo={[m.get('_viejo') for m in b['marcas']]}")
        d1 = R.construir(b)
        if d1["_meta"].get("estado_fuente") == "dato_viejo" and d1["resumen"]["programadas_14"] == prog_ok and prog_ok > 0:
            ok("construir(): estado_fuente = dato_viejo y los programados no bajan a 0")
        else:
            mal(f"construir() con dato viejo: {d1['_meta'].get('estado_fuente')} programadas={d1['resumen']['programadas_14']} (antes {prog_ok})")
        # (3)
        estado["modo"] = "bien"
        estado["falla_marca"] = 1
        c = R.leer_en_vivo()
        por = {m["id"]: m for m in c["marcas"]}
        if len(por) == 2 and por[1].get("_viejo") and len(por[1]["posts"]) == 2 and not por[2].get("_viejo"):
            ok("una marca caída vuelve con su último dato; la otra, con el nuevo")
        else:
            mal(f"marca caída: {[(i, m.get('_viejo'), len(m['posts'])) for i, m in por.items()]}")
        estado["falla_marca"] = None
        # (4)
        borrar_db()
        Path(R.CACHE).unlink(missing_ok=True)
        estado["modo"] = "caida"
        e = R.leer_en_vivo()
        d2 = R.construir(e)
        if e["marcas"] == [] and e["estado"] == "sin_dato" and d2["_meta"].get("estado_fuente") == "sin_dato":
            ok("sin nada guardado y la API caída: sin_dato, ninguna marca inventada")
        else:
            mal(f"sin_dato: marcas={len(e['marcas'])} estado={e.get('estado')} meta={d2['_meta'].get('estado_fuente')}")
        c4 = json.loads(Path(R.CACHE).read_text()) if Path(R.CACHE).exists() else {}
        if c4.get("estado") == "sin_dato" and c4.get("marcas") == []:
            ok("la caché dice sin_dato (no una lista vacía que parezca «ninguna»)")
        else:
            mal(f"caché tras sin_dato: {str(c4)[:120]}")
        # (5)
        previa = {"leido": "2026-10-01 06:00", "marcas": [{"id": 1, "nombre": "Cliente Falso", "redes": ["instagram"],
                  "posts": [{"id": "p", "fecha": f"{hoy}T10:00:00", "texto": "ayer", "draft": False, "auto": True, "miniatura": None, "redes": []}],
                  "rendimiento": {}}]}
        Path(R.CACHE).write_text(json.dumps(previa))
        f = R.leer_en_vivo()
        if f["estado"] == "viejo" and len(f["marcas"]) == 1 and json.loads(Path(R.CACHE).read_text()) == previa:
            ok("API caída con caché de ficheros: se queda con ella y no la pisa")
        else:
            mal(f"caché de ayer: estado={f.get('estado')} marcas={len(f['marcas'])}")
    finally:
        urllib.request.urlopen = real

    t = (RAIZ / "fuentes_redes" / "generar_redes.py").read_text(encoding="utf-8")
    if "return {'_error': str(e)[:120]}" in t:
        mal("g() sigue devolviendo {'_error': …} en vez de lanzar")
    else:
        ok("g() lanza ante un error de la API")
finally:
    Path(tmpdb.name).unlink(missing_ok=True)

if fallos:
    print(f"\n✘ N-03: {len(fallos)} fallo(s)")
    sys.exit(1)
print("\n✔ N-03")

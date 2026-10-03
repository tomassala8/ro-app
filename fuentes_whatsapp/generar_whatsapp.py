#!/usr/bin/env python3
"""
fuentes_whatsapp/generar_whatsapp.py · grupos de WhatsApp de clientes como fuente de LECTURA (E0 ronda 3).

Petición de Tomás (18_PETICIONES_ANTERIORES_REPASO, contradicción 4): los grupos de WhatsApp cuentan como
contacto y como reunión, para no dar rojos falsos («sin contacto», «sin reunión»: Concilia, Gestanex).
Enviar por grupos sigue fuera (no hay vía oficial).

Lee (solo lectura, 0 llamadas):
  ~/Downloads/PANEL_OPERACIONES_2026-10-01/_crudo/whatsapp/por_cliente.json   (lo escribe la recarga del panel, RECARGA.md §22-23)
  ~/Downloads/PANEL_OPERACIONES_2026-10-01/build/whatsapp_mapa.json           (qué grupo o chat es de qué cliente)
Escribe:
  data/whatsapp/whatsapp.json            por cliente: nº de grupos, último mensaje nuestro y del cliente, horas
                                         pendientes y fechas de reuniones mencionadas. SIN textos ni nombres de grupo.
  data/whatsapp/_privado/textos.json     el último texto del cliente (80 caracteres) y los nombres de los grupos:
                                         solo con «ver datos» (/api/ver_dato), para quien lleva el cliente, y queda en el rastro.
Si por_cliente.json no existe, la fuente sale «sin_conectar» y cada cliente con grupo conocido lo dice.
"""
import json
import re
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

AQUI = Path(__file__).resolve().parent.parent
sys.path.insert(1, str(Path(__file__).resolve().parents[1]))  # C5: rutas y secretos en config.py
import config  # noqa: E402
PANEL = config.PANEL_OPERACIONES
CRUDO = PANEL / "_crudo/whatsapp/por_cliente.json"
MAPA = PANEL / "build/whatsapp_mapa.json"
SALIDA = AQUI / "data/whatsapp"


def norm(t):
    t = unicodedata.normalize("NFKD", t or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


def main():
    global CRUDO, SALIDA
    if "--crudo" in sys.argv:          # solo para pruebas: otro fichero de entrada y salida a una carpeta aparte
        CRUDO = Path(sys.argv[sys.argv.index("--crudo") + 1])
        SALIDA = Path(sys.argv[sys.argv.index("--salida") + 1])
    clientes = json.loads((AQUI / "data/clientes.json").read_text())
    por_nombre = {norm(c["nombre"]): c["id"] for c in clientes}

    def cliente_id(nombre):
        n = norm(nombre)
        if n in por_nombre:
            return por_nombre[n]
        cand = [cid for cn, cid in por_nombre.items() if n and (n in cn or cn in n or n.split()[0] == cn.split()[0])]
        return cand[0] if len(set(cand)) == 1 else None

    mapa = json.loads(MAPA.read_text()) if MAPA.exists() else {}
    crudo = json.loads(CRUDO.read_text()) if CRUDO.exists() else None
    ahora = datetime.now().isoformat(timespec="minutes")

    filas, textos, sin_emparejar = {}, {}, []
    for nombre, grupos in mapa.items():
        if nombre.startswith("_"):
            continue
        cid = cliente_id(nombre)
        if not cid:
            sin_emparejar.append(nombre)
            continue
        filas[cid] = {"cliente_id": cid, "grupos": len(grupos), "estado": "sin_conectar" if crudo is None else "sin_actividad",
                      "ultimo_nuestro": None, "ultimo_cliente": None, "pendiente_horas": None, "reuniones": []}
        textos[cid] = {"grupos": grupos, "ultimo_texto_cliente": None}

    for nombre, d in (crudo or {}).items():
        if nombre.startswith("_") or not isinstance(d, dict):
            continue
        cid = cliente_id(nombre)
        if not cid:
            sin_emparejar.append(nombre)
            continue
        fila = filas.setdefault(cid, {"cliente_id": cid, "grupos": 1, "reuniones": []})
        fila.update({
            "estado": "bien",
            "ultimo_nuestro": d.get("ultimo_nuestro"), "ultimo_cliente": d.get("ultimo_cliente"),
            "pendiente_horas": d.get("pendiente_horas"),
            "reuniones": sorted(set(x for x in (d.get("reuniones") or []) if re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(x)))),
        })
        t = textos.setdefault(cid, {"grupos": [d.get("grupo")] if d.get("grupo") else []})
        t["ultimo_texto_cliente"] = (d.get("ultimo_texto_cliente") or "")[:80] or None

    salida = {
        "generado": ahora,
        "fuente": {"id": "whatsapp", "nombre": "Grupos de WhatsApp de clientes (lectura)",
                   "estado": "sin_conectar" if crudo is None else "bien",
                   "hora": datetime.fromtimestamp(CRUDO.stat().st_mtime).isoformat(timespec="minutes") if crudo is not None else None,
                   "nota": None if crudo is not None else "Aún no existe _crudo/whatsapp/por_cliente.json: lo escribe la recarga del panel leyendo WhatsApp Web (RECARGA.md). Mientras, solo se sabe qué clientes tienen grupo."},
        "regla": "Cuenta como contacto y como reunión (no da rojo falso). Los textos solo con «ver datos» y para quien lleva el cliente.",
        "clientes": sorted(filas.values(), key=lambda x: x["cliente_id"]),
        "sin_emparejar": sin_emparejar,
    }
    (SALIDA / "_privado").mkdir(parents=True, exist_ok=True)
    for ruta, obj in ((SALIDA / "whatsapp.json", salida), (SALIDA / "_privado/textos.json", {"generado": ahora, "textos": textos})):
        tmp = ruta.with_suffix(".tmp")
        tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=1))
        tmp.replace(ruta)
    print(f"whatsapp: {len(filas)} clientes con grupo · fuente {salida['fuente']['estado']} · sin emparejar {len(sin_emparejar)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

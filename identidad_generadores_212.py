"""212: referencias canónicas de lectura, sin permisos ni heurísticas por nombre.

Identidad histórica inequívoca se conserva aunque hoy esté inactiva. El servidor
sigue exigiendo actor/cliente activos para operaciones y autoridad 204 para POST.
"""
import json
from pathlib import Path
from collections import defaultdict
from identidades_clickup_204 import resolver


def identidades(personas, usuarios):
    return resolver(personas, usuarios)


def carpetas_confirmadas(documentos):
    por_cliente = defaultdict(list)
    por_carpeta = defaultdict(list)
    for d in documentos if isinstance(documentos, list) else []:
        if isinstance(d, dict) and isinstance(d.get('id'), str) and d['id']:
            por_cliente[d['id']].append(d)
    nombres = {}
    for cid, filas in por_cliente.items():
        if len(filas) != 1:
            continue
        d = filas[0]
        nombres[cid] = d.get('nombre')
        datos = d
        for clave in ('fuentes', 'tareas', 'datos'):
            datos = datos.get(clave) if isinstance(datos, dict) else None
        folder = datos.get('carpeta_id') if isinstance(datos, dict) else None
        if isinstance(folder, (str, int)) and not isinstance(folder, bool) and str(folder):
            por_carpeta[str(folder)].append(cid)
    return ({folder: (cids[0], nombres[cids[0]]) for folder, cids in por_carpeta.items() if len(cids) == 1}, nombres)


def clientes_directos(data):
    """Sólo documentos locales directos; no alias, panel por nombre o red."""
    documentos = []
    for p in sorted((Path(data) / 'clientes').glob('*.json')):
        if p.is_symlink() or not p.is_file():
            raise ValueError('Ficha de cliente no regular')
        try:
            d = json.loads(p.read_text())
        except (OSError, ValueError, UnicodeError) as e:
            raise ValueError('Ficha de cliente no legible') from e
        if not isinstance(d, dict):
            raise ValueError('Ficha de cliente no válida')
        documentos.append(d)
    return carpetas_confirmadas(documentos)

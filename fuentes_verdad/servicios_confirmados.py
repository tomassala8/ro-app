"""Declaraciones de cartera revisadas: mismo catálogo en generación y servidor."""
import json
from pathlib import Path

FUENTE = Path(__file__).with_suffix('.json')

def aplicar(clientes, fuente=FUENTE, estado=None):
    if not Path(fuente).exists():
        return clientes
    evidencia = json.loads(Path(fuente).read_text())
    if estado is None:
        archivo = FUENTE.parent.parent / 'data/verdad/estado_clientes.json'
        estado = json.loads(archivo.read_text()) if archivo.exists() else {}
    bajas = set(estado.get('bajas_ids', [])) | {x.get('cliente_id') for x in estado.get('bajas', [])}
    por_id = {x['cliente_id']: x for x in evidencia.get('clientes', [])}
    for cliente in clientes:
        cid = cliente.get('id')
        fila = por_id.get(cid)
        if not fila or cid in bajas:
            continue
        servicios = cliente.setdefault('servicios', {})
        if servicios is None:
            servicios = cliente['servicios'] = {}
        for nombre, valor in fila.get('servicios', {}).items():
            if valor != 'sí':
                continue
            servicios[nombre] = valor
            servicios[nombre + '_fuente'] = f"{fila['fuente']} · fila {fila['fila']} · {fila['leida']}"
    return clientes

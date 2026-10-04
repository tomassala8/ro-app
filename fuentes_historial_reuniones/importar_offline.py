"""Inspección opt-in offline. No escritura de corpus ni importaciones del publicador."""
import argparse
import csv
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
try:
    from .normalizador import leer_privado, normalizar
except ImportError:
    from normalizador import leer_privado, normalizar


def documentos_locales(raiz):
    base = Path(raiz)
    salida = []
    for carpeta_base in ('10_CLIENTES', '15_NUEVOS_CLIENTES'):
        for f in (base/carpeta_base).rglob('*.md'):
            if '_fathom' not in f.parts:
                continue
            hit = re.search(r'_(\d+)\.md$', f.name)
            if not hit:
                continue
            contenido = leer_privado(f, base, 8_000_000)
            # Sólo índice privado de documentos; no copiar texto por heurísticas.
            fecha_doc = None
            fecha_match = re.search(rb'\*\*Fecha:\*\* (\d{2}-\d{2}-\d{4})', contenido[:3000])
            if fecha_match:
                try:
                    fecha_doc = datetime.strptime(fecha_match[1].decode(), '%d-%m-%Y').date().isoformat()
                except ValueError:
                    pass
            salida.append({'fecha': fecha_doc, 'call_id': hit[1], 'carpeta': f.relative_to(base).parts[1],
                'hash': hashlib.sha256(contenido).hexdigest(),
                'transcripcion_disponible': bool(re.search(rb'\d{1,2}:\d{2}(?::\d{2})?\s*-', contenido)),
                'referencia_privada': str(f.relative_to(base))})
    return salida


def inspeccionar(cache, clasificacion, catalogo, roster, equipo, indice, mapping):
    def j(p):
        return json.loads(leer_privado(p, Path(p).parent))
    filas = list(csv.DictReader(leer_privado(indice, Path(indice).parent).decode('utf-8-sig').splitlines()))
    # Categorías explícitas offline prevalecen para excluir; no nombre de cliente inferido.
    cats = {str(x['call_id']): x.get('category') for x in j(mapping)}
    existentes = {str(x['id']) for x in filas}
    for i in filas:
        if cats.get(str(i['id'])):
            i['carpeta'] = cats[str(i['id'])]
    for key, cat in cats.items():
        if key not in existentes:
            filas.append({'id': key, 'carpeta': cat})
    return normalizar(j(cache), j(clasificacion), j(catalogo), {c['id'] for c in j(roster)},
                      documentos=documentos_locales(equipo), indice=filas)


def main():
    p = argparse.ArgumentParser(description='Inspección agregada offline, sin escritura ni transcripciones en salida')
    for k in ('cache','clasificacion','catalogo','roster','equipo','indice','mapping'):
        p.add_argument('--'+k, required=True)
    a = p.parse_args()
    resultado = inspeccionar(**vars(a))
    print(json.dumps(resultado['cobertura'], ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

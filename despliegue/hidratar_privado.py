"""Valida un bundle privado y crea un destino NUEVO, separado del código.

La huella del manifiesto debe venir de un canal de confianza independiente.
No instala fuentes en la app ni configura montajes/publicación. Sin red.
"""
import argparse
import hashlib
import json
import os
import re
import stat
from pathlib import Path, PurePosixPath

try:
    from .empaquetado import PRIVADOS_REQUERIDOS, PRIVADOS_OPCIONALES
except ImportError:
    from empaquetado import PRIVADOS_REQUERIDOS, PRIVADOS_OPCIONALES

MANIFIESTO = 'manifiesto_privado.json'


def _sin_duplicadas(pares):
    out = {}
    for k, v in pares:
        if k in out: raise ValueError('JSON con claves duplicadas.')
        out[k] = v
    return out


def _json(b):
    return json.loads(b.decode('utf-8'), object_pairs_hook=_sin_duplicadas,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError('JSON no finito.')))


def _ruta(r):
    if not isinstance(r, str) or '\\' in r or not re.fullmatch(r'[A-Za-z0-9_./-]+', r):
        raise ValueError('Ruta privada no válida.')
    p = PurePosixPath(r)
    if p.is_absolute() or any(x in ('', '.', '..') for x in r.split('/')) or p.as_posix() != r:
        raise ValueError('Ruta privada no canónica.')
    permitida = r in (*PRIVADOS_REQUERIDOS, *PRIVADOS_OPCIONALES) or (
        (r.startswith('data/') or r.startswith('fuentes_seo/_cache/')) and p.suffix == '.json')
    if not permitida: raise ValueError('Fuente privada fuera de la lista permitida.')
    return r


def _sin_enlaces(p):
    p = Path(os.path.abspath(p))
    for x in (p, *p.parents):
        if x.is_symlink(): raise ValueError('No se admiten enlaces simbólicos.')
    return p


def _leer(p, limite):
    p = _sin_enlaces(p)
    fd = os.open(p, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode) or st.st_nlink != 1 or st.st_size > limite:
            raise ValueError('Fuente no regular, enlazada o demasiado grande.')
        with os.fdopen(fd, 'rb', closefd=False) as f: b = f.read(limite + 1)
        if len(b) > limite or len(b) != st.st_size: raise ValueError('Fuente cambió o excede el límite.')
        return b
    finally:
        os.close(fd)


def validar(bundle, sha256_manifiesto, *, max_bytes=256*1024*1024):
    """Lee una instantánea validada antes de escribir; no devuelve contenido por CLI."""
    if not isinstance(sha256_manifiesto, str) or not re.fullmatch('[0-9a-f]{64}', sha256_manifiesto):
        raise ValueError('Falta la huella externa confiable del manifiesto.')
    bundle = _sin_enlaces(bundle)
    mb = _leer(bundle/MANIFIESTO, 4*1024*1024)
    if hashlib.sha256(mb).hexdigest() != sha256_manifiesto: raise ValueError('Manifiesto alterado.')
    m = _json(mb)
    if not isinstance(m, dict) or type(m.get('version')) is not int or m.get('version') != 1 or m.get('privado') is not True or m.get('publicar_en_repositorio') is not False or m.get('hidratado') is not False:
        raise ValueError('Manifiesto privado incompatible.')
    fs = m.get('ficheros')
    if not isinstance(fs, list) or not fs or len(fs) > 10000: raise ValueError('Inventario no válido.')
    datos, total = {}, 0
    for e in fs:
        if not isinstance(e, dict) or set(e) != {'ruta', 'sha256', 'bytes'}: raise ValueError('Entrada no válida.')
        r = _ruta(e['ruta'])
        n, sha = e['bytes'], e['sha256']
        if r in datos or type(n) is not int or n < 0 or n > 64*1024*1024 or not isinstance(sha, str) or not re.fullmatch('[0-9a-f]{64}', sha):
            raise ValueError('Entrada duplicada, tamaño o huella no válidos.')
        total += n
        if total > max_bytes: raise ValueError('Paquete excede límite total.')
        b = _leer(bundle/r, n)
        if len(b) != n or hashlib.sha256(b).hexdigest() != sha: raise ValueError('Fuente alterada.')
        _json(b)
        datos[r] = b
    if not set(PRIVADOS_REQUERIDOS) <= set(datos): raise ValueError('Faltan fuentes obligatorias.')
    presentes = set()
    for p in bundle.rglob('*'):
        if p.is_symlink(): raise ValueError('Enlace no permitido dentro del paquete.')
        if p.is_file(): presentes.add(p.relative_to(bundle).as_posix())
        elif not p.is_dir(): raise ValueError('Entrada especial no permitida.')
    if presentes != set(datos) | {MANIFIESTO}: raise ValueError('Paquete con archivos adicionales o ausentes.')
    return bundle, mb, datos


def _escribir(p, b):
    fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as f:
        f.write(b); f.flush(); os.fsync(f.fileno())


def hidratar(bundle, destino, sha256_manifiesto, *, codigo_destino, max_bytes=256*1024*1024):
    bundle, mb, datos = validar(bundle, sha256_manifiesto, max_bytes=max_bytes)
    destino = _sin_enlaces(destino)
    codigo = _sin_enlaces(codigo_destino)
    if destino == codigo or codigo in destino.parents or destino in codigo.parents:
        raise ValueError('Destino privado debe quedar separado de la raíz de código.')
    if destino == bundle or bundle in destino.parents or destino in bundle.parents:
        raise ValueError('Destino debe estar separado del paquete.')
    if not destino.parent.is_dir(): raise ValueError('Directorio padre debe existir.')
    # mkdir exclusivo conserva cualquier destino preexistente, incluso vacío.
    destino.mkdir(mode=0o700)
    for r, b in datos.items():
        p = destino/r
        p.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        for d in (p.parent, *p.parent.parents):
            if d == destino or destino in d.parents: d.chmod(0o700)
        _escribir(p, b)
    _escribir(destino/MANIFIESTO, mb)
    recibo = {'version': 1, 'hidratacion_completa': True, 'sha256_manifiesto': sha256_manifiesto,
              'ficheros': len(datos), 'integrado_en_servidor': False, 'listo_para_desplegar': False,
              'bloqueantes': ['montaje_privado_y_loader_no_integrados', 'restauracion_destino_no_verificada']}
    # Sólo esta marca final permite considerar completo un directorio recién creado.
    _escribir(destino/'hidratacion_completa.json', (json.dumps(recibo)+'\n').encode())
    return recibo


def main():
    p = argparse.ArgumentParser(); p.add_argument('bundle'); p.add_argument('destino')
    p.add_argument('--codigo-destino', required=True); p.add_argument('--sha256-manifiesto', required=True); p.add_argument('--solo-validar', action='store_true')
    a = p.parse_args()
    if a.solo_validar:
        _, _, ds = validar(a.bundle, a.sha256_manifiesto)
        out = {'validado': True, 'ficheros': len(ds), 'listo_para_desplegar': False}
    else: out = hidratar(a.bundle, a.destino, a.sha256_manifiesto, codigo_destino=a.codigo_destino)
    print(json.dumps(out))


if __name__ == '__main__': main()

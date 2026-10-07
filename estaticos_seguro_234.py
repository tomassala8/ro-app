"""Lectura de assets regulares dentro de la raíz, sin seguir enlaces simbólicos."""
import os
import stat
from pathlib import Path

TOPE = 20 * 1024 * 1024

def ruta_estatica(raiz, rel):
    if not isinstance(rel, str) or not rel or rel.startswith('/'):
        raise PermissionError('Ruta no permitida')
    partes = rel.split('/')
    if any(p in ('', '.', '..', '_privado') for p in partes):
        raise PermissionError('Ruta no permitida')
    base = Path(raiz).absolute()
    if base.is_symlink():
        raise PermissionError('Raíz no permitida')
    p = base
    for parte in partes:
        p = p / parte
        if p.is_symlink():
            raise PermissionError('Enlace no permitido')
    p.resolve(strict=True).relative_to(base)
    if not p.is_file():
        raise FileNotFoundError('Asset no disponible')
    return p

def leer_estatico(raiz, rel):
    base = Path(raiz).absolute()
    ruta_estatica(base, rel)
    # Cada componente se abre respecto al descriptor anterior: cambiar un
    # directorio por un symlink después de validarlo tampoco amplía el alcance.
    if not hasattr(os, 'O_NOFOLLOW') or os.open not in os.supports_dir_fd:
        raise PermissionError('Lectura segura no disponible')
    nofollow = os.O_NOFOLLOW | getattr(os, 'O_CLOEXEC', 0)
    directorio = os.O_RDONLY | os.O_DIRECTORY | nofollow
    actual = os.open(str(base), directorio)
    archivo = None
    try:
        partes = rel.split('/')
        for parte in partes[:-1]:
            nuevo = os.open(parte, directorio, dir_fd=actual)
            os.close(actual)
            actual = nuevo
        archivo = os.open(partes[-1], os.O_RDONLY | nofollow | getattr(os, 'O_NONBLOCK', 0), dir_fd=actual)
        antes = os.fstat(archivo)
        if not stat.S_ISREG(antes.st_mode) or antes.st_size > TOPE:
            raise PermissionError('Asset no permitido')
        with os.fdopen(archivo, 'rb') as f:
            archivo = None
            datos = f.read(TOPE + 1)
            despues = os.fstat(f.fileno())
        marca = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
        if len(datos) > TOPE or marca(antes) != marca(despues):
            raise PermissionError('Asset cambió durante la lectura')
        return datos, marca(despues)
    finally:
        if archivo is not None:
            os.close(archivo)
        os.close(actual)

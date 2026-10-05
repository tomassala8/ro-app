"""Opt-in local de IA real. Sin IO al importar ni lectura de credenciales."""
import json
import os
import stat
from pathlib import Path

INTERRUPTOR = Path(__file__).resolve().parent / 'data' / 'ia' / 'interruptor.json'
MOTIVO = 'IA real desactivada: requiere RO_IA_REAL=si e interruptor explícito de Tomás. Seguimos con reglas y lo preparado.'

def _objeto(pares):
    out = {}
    for k, v in pares:
        if k in out:
            raise ValueError('Clave duplicada')
        out[k] = v
    return out

def autorizada():
    """Se relee cada vez; una clave presente o en caché nunca activa IA."""
    if os.environ.get('RO_IA_REAL') != 'si':
        return False
    fd = None
    try:
        fd = os.open(INTERRUPTOR, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        antes = os.fstat(fd)
        if not stat.S_ISREG(antes.st_mode) or antes.st_nlink != 1 or antes.st_size > 16384:
            return False
        contenido = os.read(fd, 16385)
        despues = os.fstat(fd)
        if len(contenido) > 16384 or (antes.st_ino, antes.st_size, antes.st_mtime_ns, antes.st_ctime_ns) != (despues.st_ino, despues.st_size, despues.st_mtime_ns, despues.st_ctime_ns):
            return False
        datos = json.loads(contenido, object_pairs_hook=_objeto,
                           parse_constant=lambda _: (_ for _ in ()).throw(ValueError('No finito')))
        return isinstance(datos, dict) and datos.get('ia_real') is True and datos.get('activado_por') == 'tomas'
    except (OSError, ValueError, TypeError, UnicodeError):
        return False
    finally:
        if fd is not None:
            os.close(fd)

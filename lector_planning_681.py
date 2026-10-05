"""Reader candidato opt-in sólo archivo local pinneado; no IO al importar."""
import hashlib,json,math,os,re,stat
from pathlib import Path

def leer_planning681(path,sha,limite=2097152):
    p=Path(path)
    if not p.is_absolute() or not isinstance(sha,str) or not re.fullmatch(r'[a-f0-9]{64}',sha):raise ValueError('Configuración no válida')
    fd=os.open('/',os.O_RDONLY|os.O_DIRECTORY)
    try:
        for part in p.parts[1:-1]:
            child=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd);os.close(fd);fd=child
        parent=os.fstat(fd)
        if parent.st_uid!=os.getuid() or stat.S_IMODE(parent.st_mode)!=0o700:raise ValueError('Depósito no privado')
        file=os.open(p.name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=fd)
        try:
            before=os.fstat(file)
            if not stat.S_ISREG(before.st_mode) or before.st_nlink!=1 or before.st_uid!=os.getuid() or stat.S_IMODE(before.st_mode)!=0o600 or not 0<before.st_size<=limite:raise ValueError('Archivo no válido')
            with os.fdopen(os.dup(file),'rb') as stream:raw=stream.read(limite+1)
            after=os.fstat(file)
            if len(raw)!=before.st_size or (before.st_ino,before.st_size,before.st_mtime_ns,before.st_ctime_ns)!=(after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns):raise ValueError('Fuente cambió')
        finally:os.close(file)
    finally:os.close(fd)
    if hashlib.sha256(raw).hexdigest()!=sha:raise ValueError('Pin inválido')
    def constante(_):raise ValueError('Número inválido')
    def pares(rows):
        out={}
        for k,v in rows:
            if k in out:raise ValueError('Clave duplicada')
            out[k]=v
        return out
    def decimal(texto):
        n=float(texto)
        if not math.isfinite(n):raise ValueError('Número no finito')
        return n
    try:return json.loads(raw,parse_constant=constante,parse_float=decimal,object_pairs_hook=pares)
    except RecursionError:raise ValueError('Profundidad no válida') from None

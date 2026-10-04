"""Demostrador aislado573, NO ejecutor de las baterías completas ni sandbox hostil."""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

BOOTSTRAP = r'''
import sys, os, runpy
sys.dont_write_bytecode=True
from pathlib import Path
raiz=Path(sys.argv[1]).resolve()
stdlib=Path(sys.base_prefix).resolve()
def dentro(p,r):
    return p==r or r in p.parents
def ruta(valor,escritura=False):
    if isinstance(valor,int):return
    p=Path(os.fsdecode(valor)).resolve()
    if dentro(p,raiz):return
    if not escritura and dentro(p,stdlib):return
    raise PermissionError('Ruta fuera del staging573')
def auditar(event,args):
    if event=='open':
        modo=args[1];flags=args[2]
        escritura=(isinstance(modo,str) and any(c in modo for c in 'wax+')) or (isinstance(flags,int) and bool(flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND)))
        ruta(args[0],escritura)
    elif event in ('os.listdir','os.scandir','sqlite3.connect'):
        ruta(args[0],event=='sqlite3.connect')
    elif event in ('os.remove','os.rmdir','os.mkdir','os.chmod','os.chown','os.truncate'):
        ruta(args[0],True)
    elif event in ('os.rename','os.link','os.symlink'):
        ruta(args[0],True);ruta(args[1],True)
    elif event.startswith('socket.') or event in ('subprocess.Popen','os.system','os.fork','os.posix_spawn','os.exec'):
        raise PermissionError('Efecto externo bloqueado573')
    elif event=='import' and args[0].split('.')[0] in ('ctypes','anthropic','requests','httpx'):
        raise PermissionError('Adaptador externo bloqueado573')
sys.addaudithook(auditar)
os.chdir(raiz)
sys.path.insert(0,str(raiz))
runpy.run_path(str(raiz/'probe.py'),run_name='__main__')
'''

def entorno_573(raiz):
    raiz=Path(raiz).resolve()
    return {'PATH':os.defpath,'HOME':str(raiz/'home'),'TMPDIR':str(raiz/'tmp'),
            'RO_DB':str(raiz/'fixture.db'),'RO_IA_REAL':'no','RO_CLICKUP_REAL':'no',
            'RO_ZOHO_REAL':'no','RO_FATHOM_REAL':'no'}

def ejecutar_probe_573(raiz,codigo):
    """Sólo probe controlado; no accepts fuente/ruta de suite ni copia datos reales."""
    raiz=Path(raiz)
    if raiz.is_symlink():raise ValueError('No symlink')
    raiz=raiz.resolve()
    temporal=Path(tempfile.gettempdir()).resolve()
    if raiz == temporal or temporal not in raiz.parents:
        raise ValueError('El probe exige un subdirectorio temporal, nunca la app')
    raiz.mkdir(exist_ok=True,mode=0o700)
    for p in ('home','tmp'):(raiz/p).mkdir(exist_ok=True,mode=0o700)
    probe=raiz/'probe.py'
    if probe.exists():raise ValueError('No sobrescribir probe existente')
    probe.write_text(codigo);probe.chmod(0o600)
    return subprocess.run([sys.executable,'-I','-c',BOOTSTRAP,str(raiz)],cwd=raiz,
                          env=entorno_573(raiz),capture_output=True,text=True,timeout=10)

"""Preparación optativa de una app AISLADA con fuentes privadas antes de servir.
No integra Docker/entrada.sh ni producción. Preparar no ejecuta el servidor.
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
try:
    from .empaquetado import copiar_codigo, plan_codigo
    from .hidratar_privado import validar, hidratar, _sin_enlaces, _leer, _escribir, _json
except ImportError:
    from empaquetado import copiar_codigo, plan_codigo
    from hidratar_privado import validar, hidratar, _sin_enlaces, _leer, _escribir, _json

RECIBO='arranque_preparado.json'

def _hash(b):return hashlib.sha256(b).hexdigest()

def _codigo(codigo):
    codigo=_sin_enlaces(codigo)
    if not codigo.is_dir() or not (codigo/'servir.py').is_file():raise ValueError('Falta raíz de código con servir.py.')
    return codigo,{r:_hash(_leer(codigo/r,64*1024*1024)) for r in plan_codigo(codigo)}

def _formas(datos):
    for nombre in ('personas','asignaciones','clientes','alarmas'):
        rows=_json(datos[f'data/{nombre}.json'])
        if not isinstance(rows,list) or any(not isinstance(r,dict) for r in rows):
            raise ValueError('Estructura nuclear incompatible.')
        if nombre in ('personas','clientes'):
            ids=[r.get('id') for r in rows]
            if any(not isinstance(i,str) or not i for i in ids) or len(set(ids))!=len(ids):
                raise ValueError('Identidades nucleares ausentes o duplicadas.')
    for nombre in ('logos','meta'):
        if not isinstance(_json(datos[f'data/{nombre}.json']),dict):raise ValueError('Metadatos nucleares incompatibles.')
    for rel in ('data/verdad/estado_clientes.json','fuentes_verdad/servicios_confirmados.json',
                'fuentes_metodo/reglas_operativas.json','fuentes_metodo/evidencias_reuniones.json'):
        if not isinstance(_json(datos[rel]),dict):raise ValueError('Registro privado incompatible.')


def preparar(codigo,bundle,raiz,sha256_manifiesto):
    """Destino nuevo, o reinicio de la misma instantánea íntegra; nunca sobrescribe."""
    codigo,hashes=_codigo(codigo)
    bundle,mb,datos=validar(bundle,sha256_manifiesto)
    _formas(datos)
    raiz=_sin_enlaces(raiz)
    for origen in (codigo,bundle):
        if raiz==origen or origen in raiz.parents or raiz in origen.parents:
            raise ValueError('Raíz aislada debe estar separada de los orígenes.')
    if raiz.exists():
        r=_json(_leer(raiz/RECIBO,4*1024*1024))
        if not isinstance(r,dict) or r.get('version')!=1 or r.get('sha256_manifiesto')!=sha256_manifiesto or r.get('codigo_sha256')!=hashes:
            raise ValueError('Destino existente no corresponde a esta instantánea.')
        if _leer(raiz/'privado'/'manifiesto_privado.json',len(mb))!=mb:
            raise ValueError('Manifiesto hidratado alterado.')
        marca=_json(_leer(raiz/'privado'/'hidratacion_completa.json',65536))
        if marca.get('hidratacion_completa') is not True or marca.get('sha256_manifiesto')!=sha256_manifiesto:
            raise ValueError('Montaje privado incompleto.')
        for rel,b in datos.items():
            if _leer(raiz/'privado'/rel,len(b))!=b:raise ValueError('Montaje privado alterado.')
        for rel,b in datos.items():
            if _leer(raiz/'app'/rel,len(b))!=b:raise ValueError('Fuente instalada alterada.')
        for rel,h in hashes.items():
            if _hash(_leer(raiz/'app'/rel,64*1024*1024))!=h:raise ValueError('Código instalado alterado.')
        for tree,expected in ((raiz/'app',set(hashes)|set(datos)),
                              (raiz/'privado',set(datos)|{'manifiesto_privado.json','hidratacion_completa.json'})):
            paths=set()
            for p in tree.rglob('*'):
                if p.is_symlink():raise ValueError('Enlace en runtime.')
                if p.is_file():paths.add(p.relative_to(tree).as_posix())
                elif not p.is_dir():raise ValueError('Entrada especial en runtime.')
            if paths!=expected:raise ValueError('Archivo adicional o ausente en runtime.')
        return {**r,'reutilizado':True}
    if not raiz.parent.is_dir():raise ValueError('Padre aislado debe existir.')
    raiz.mkdir(mode=0o700)
    copiar_codigo(codigo,raiz/'app')
    hidratar(bundle,raiz/'privado',sha256_manifiesto,codigo_destino=raiz/'app')
    # __file__/AQUI de los lectores necesita las fuentes junto al código AISLADO.
    # No enlaces a bundles mutables; instalar exclusivamente la instantánea validada.
    for rel,b in datos.items():
        p=raiz/'app'/rel;p.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
        for d in (p.parent,*p.parent.parents):
            if d==raiz or raiz in d.parents:d.chmod(0o700)
        _escribir(p,b)
    for rel,h in hashes.items():
        if _hash(_leer(raiz/'app'/rel,64*1024*1024))!=h:raise ValueError('Código cambió durante preparación.')
    (raiz/'estado').mkdir(mode=0o700)
    r={'version':1,'sha256_manifiesto':sha256_manifiesto,'codigo_sha256':hashes,
       'privados_sha256':{k:_hash(v) for k,v in datos.items()},'reutilizado':False,
       'preparado_local':True,'listo_para_desplegar':False,
       'limites':['solo_local','sin_refresco_automatico','restauracion_destino_no_verificada']}
    _escribir(raiz/RECIBO,(json.dumps(r,sort_keys=True)+'\n').encode())
    return r


def lanzamiento(raiz,puerto=8772):
    """Contrato cerrado: no hereda tokens, destino remoto, flags ni credenciales."""
    raiz=_sin_enlaces(raiz)
    if type(puerto) is not int or not 1024<=puerto<=65535:raise ValueError('Puerto local no válido.')
    if not (raiz/RECIBO).is_file():raise ValueError('Preparación incompleta.')
    env={'PATH':os.defpath,'TZ':'Europe/Madrid','PYTHONUNBUFFERED':'1','PYTHONDONTWRITEBYTECODE':'1',
         'RO_HOME':str(raiz/'estado'),'RO_CRUDOS':str(raiz/'estado'/'crudos'),
         'RO_HERRAMIENTAS':str(raiz/'estado'/'herramientas'),
         'RO_BANDEJA_GHL_CONFIG':str(raiz/'estado'/'config'),
         'RO_ESTADO_DIR':str(raiz/'estado'),'RO_DB':str(raiz/'estado'/'piloto.db'),
         'RO_APP':str(raiz/'app'),'RO_DATOS':str(raiz/'app'/'data'),
         'RO_PILOTO_LECTURA':'1','RO_AVISOS_SIN_BUCLE':'1',
         'RO_ANCLAS':str(raiz/'estado'/'anclas.jsonl'),
         'RO_LISTA_ACCESS':str(raiz/'estado'/'lista_access.txt'),
         'RO_DEPARTAMENTOS':str(raiz/'estado'/'departamentos.json'),
         'RO_CORREOS_ENTRADA':str(raiz/'estado'/'correos_entrada.json'),
         'RO_RECARGA_CONFIG':str(raiz/'estado'/'recarga.json'),
         'RO_MODULAR_ACCESO':'no','RO_COPIA_R2':'no',
         'RO_ENVIOS_REALES':'no','RO_CLICKUP_REAL':'no'}
    return {'args':[sys.executable,str(raiz/'app'/'servir.py'),'--puerto',str(puerto)],
            'cwd':str(raiz/'app'),'env':env}


def iniciar(codigo,bundle,raiz,sha256_manifiesto,*,puerto=8772,ejecutor=subprocess.run):
    preparar(codigo,bundle,raiz,sha256_manifiesto)
    # Volver a comprobar siempre: lanzamiento directo no es API de ejecución.
    return ejecutor(**lanzamiento(raiz,puerto),check=True)


def main():
    p=argparse.ArgumentParser();p.add_argument('codigo');p.add_argument('bundle');p.add_argument('raiz')
    p.add_argument('--sha256-manifiesto',required=True);p.add_argument('--puerto',type=int,default=8772)
    p.add_argument('--iniciar',action='store_true');a=p.parse_args()
    if a.iniciar:iniciar(a.codigo,a.bundle,a.raiz,a.sha256_manifiesto,puerto=a.puerto)
    else:
        r=preparar(a.codigo,a.bundle,a.raiz,a.sha256_manifiesto)
        print(json.dumps({k:v for k,v in r.items() if k not in ('codigo_sha256','privados_sha256')}))
if __name__=='__main__':main()

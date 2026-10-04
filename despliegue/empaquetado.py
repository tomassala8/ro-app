"""Separación explícita código/config pública y paquete de fuentes privadas.

Solo filesystem local, sin tokens/red/instalación/hidratación del servidor.
La preparación del paquete no demuestra que esté listo para desplegar.
"""
import argparse
import hashlib
import json
import shutil
from pathlib import Path

EXTENSIONES_CODIGO={'.py','.js','.css','.html','.sql','.sh','.yaml','.yml','.woff','.woff2','.ttf'}
ARCHIVOS_CODIGO={'Dockerfile','requirements.txt','robots.txt'}
JSON_CODIGO={'reglas_permisos.json','recarga.json','despliegue/pasos.json'}
CARPETAS_PRIVADAS={'data','historia','capturas','_cache','_crudo','_privado','_muestras','__pycache__','.git'}
PRIVADOS_REQUERIDOS=('data/personas.json','data/clientes.json','data/asignaciones.json',
 'data/alarmas.json','data/logos.json','data/meta.json',
 'data/verdad/estado_clientes.json','fuentes_verdad/servicios_confirmados.json',
 'fuentes_metodo/reglas_operativas.json','fuentes_metodo/evidencias_reuniones.json')
PRIVADOS_OPCIONALES=('fuentes_seo/contextos_confirmados.json','fuentes_seo/objetivos_candidatos.json',
 'fuentes_verdad/objetivos_clientes.json',
 # Catálogos operativos/criterios: privados hasta revisión de contenido, nunca código público.
 'indicadores.json','fuentes_consejos/conocimiento/reglas.json',
 'fuentes_consejos/conocimiento/tipos.json','fuentes_consejos/conocimiento/puestos.json',
 # Copia exacta de soporte de tareas; sin escanear otros caches ni documentos.
 'fuentes_produccion/_privado/_cache/tareas.json',
 'fuentes_produccion/_privado/_cache/estados_listas.json',
 'fuentes_produccion/_privado/_cache/tablero_tareas.json',
 'fuentes_contratos/_privado/indice_documentos.json')

FUENTES_POR_FUNCION={
 'catalogo_indicadores':('indicadores.json',),
 'criterios_cerebro':('fuentes_consejos/conocimiento/reglas.json','fuentes_consejos/conocimiento/tipos.json','fuentes_consejos/conocimiento/puestos.json'),
 'catalogo_estados_tareas':('fuentes_produccion/_privado/_cache/estados_listas.json',),
 'vistas_tareas':('fuentes_produccion/_privado/_cache/tablero_tareas.json','fuentes_produccion/_privado/_cache/estados_listas.json'),
 'evidencias_ejecucion':('data/mi_trabajo/mi_trabajo.json','fuentes_produccion/_privado/_cache/tareas.json','fuentes_produccion/_privado/_cache/estados_listas.json'),
 'saneamiento_contratos_word':('fuentes_contratos/_privado/indice_documentos.json',),
}

def disponibilidad_fuentes(archivos):
    """Inventario por función: presencia no prueba validez, permisos ni disponibilidad HTTP."""
    presentes=set(archivos)
    return {nombre:{'estado':'presente_sin_validar' if set(rutas)<=presentes else 'fuente_ausente',
                    'faltantes':sorted(set(rutas)-presentes),'operativo_verificado':False}
            for nombre,rutas in FUENTES_POR_FUNCION.items()}



def es_codigo(rel):
    p=Path(rel)
    if any(n in CARPETAS_PRIVADAS or n.startswith(('_cache','_crudo')) for n in p.parts):return False
    if p.parts[:2]==('despliegue','estado'):return False
    if p.as_posix()=='escaner_secretos.py':return True
    nombre=p.name.lower()
    if nombre.startswith('.env') or '.db' in nombre or any(x in nombre for x in ('llavero','secretos')):return False
    if p.suffix.lower()=='.json':return p.as_posix() in JSON_CODIGO
    return p.suffix.lower() in EXTENSIONES_CODIGO or p.name in ARCHIVOS_CODIGO


def plan_codigo(app):
    app=Path(app).resolve()
    return [p.relative_to(app).as_posix() for p in sorted(app.rglob('*'))
            if p.is_file() and not p.is_symlink() and app in p.resolve().parents and es_codigo(p.relative_to(app))]


def copiar_codigo(app,destino):
    app=Path(app).resolve();destino=Path(destino).resolve()
    if destino==app or app in destino.parents:raise ValueError('Destino de código debe estar fuera del árbol origen.')
    if destino.exists() and any(destino.iterdir()):raise ValueError('Destino de código debe estar vacío.')
    plan=plan_codigo(app)
    for rel in plan:
        target=destino/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(app/rel,target)
    return {'codigo_ficheros':len(plan),'json_codigo':sorted(r for r in plan if r.endswith('.json')),
        'listo_para_desplegar':False,'bloqueantes':['hidratacion_privada_no_implementada','restauracion_destino_no_verificada']}


def copiar_privado(app,destino,codigo_destino):
    """Bundle separado: datos+registros exactos y cachés SEO; nunca dentro del código."""
    app=Path(app).resolve();destino=Path(destino).resolve();codigo=Path(codigo_destino).resolve()
    if destino==app or app in destino.parents or destino==codigo or codigo in destino.parents or destino in codigo.parents:
        raise ValueError('El paquete privado debe estar separado del origen y del contexto de código.')
    if destino.exists() and any(destino.iterdir()):raise ValueError('Destino privado debe estar vacío.')
    faltan=[r for r in PRIVADOS_REQUERIDOS if not (app/r).is_file() or (app/r).is_symlink()]
    if faltan:raise ValueError('Faltan fuentes privadas obligatorias; no se prepara un paquete incompleto.')
    archivos={r for r in (*PRIVADOS_REQUERIDOS,*PRIVADOS_OPCIONALES) if (app/r).is_file()}
    for carpeta in ('data','fuentes_seo/_cache'):
        raiz=app/carpeta
        if raiz.is_symlink():raise ValueError('Carpeta privada enlazada no permitida.')
        for p in raiz.rglob('*'):
            if p.is_symlink():raise ValueError('Enlace privado no permitido.')
            if p.is_file() and p.suffix=='.json':archivos.add(p.relative_to(app).as_posix())
            elif not p.is_file() and not p.is_dir():raise ValueError('Entrada privada especial no permitida.')
    for rel in archivos:
        src=app/rel
        if src.is_symlink() or app not in src.resolve().parents or any(p.is_symlink() for p in src.parents if p!=app and app in p.parents):
            raise ValueError('Fuente privada enlazada no permitida.')
    manifiesto=[];destino.mkdir(parents=True,exist_ok=True);destino.chmod(0o700)
    for rel in sorted(archivos):
        src=app/rel
        if src.is_symlink() or app not in src.resolve().parents:raise ValueError('Fuente privada con enlace fuera del árbol autorizado.')
        target=destino/rel;target.parent.mkdir(parents=True,exist_ok=True)
        for carpeta in [target.parent,*target.parent.parents]:
            if carpeta==destino or destino in carpeta.parents:carpeta.chmod(0o700)
        shutil.copyfile(src,target);target.chmod(0o600)
        manifiesto.append({'ruta':rel,'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'bytes':target.stat().st_size})
    out={'version':1,'privado':True,'publicar_en_repositorio':False,'hidratado':False,'ficheros':manifiesto,'funciones_fuentes':disponibilidad_fuentes(archivos),
         'listo_para_desplegar':False,'bloqueantes':['hidratacion_privada_no_implementada','restauracion_destino_no_verificada']}
    manifest=destino/'manifiesto_privado.json';manifest.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');manifest.chmod(0o600)
    return {'privados_ficheros':len(manifiesto),'listo_para_desplegar':False,
            'funciones_fuentes':disponibilidad_fuentes(archivos)}


def main():
    p=argparse.ArgumentParser();p.add_argument('modo',choices=('plan','codigo','privado'));p.add_argument('app');p.add_argument('destino',nargs='?');p.add_argument('--codigo-destino')
    a=p.parse_args()
    if a.modo=='plan':out={'ficheros':plan_codigo(a.app),'listo_para_desplegar':False}
    elif a.modo=='codigo':
        if not a.destino:p.error('Falta destino.')
        out=copiar_codigo(a.app,a.destino)
    else:
        if not a.destino or not a.codigo_destino:p.error('Faltan destino privado y --codigo-destino.')
        out=copiar_privado(a.app,a.destino,a.codigo_destino)
    print(json.dumps(out,ensure_ascii=False,indent=2))
if __name__=='__main__':main()

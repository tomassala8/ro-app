#!/usr/bin/env python3
"""Permisos reales + proveedor fixture; no servidor/base ni llamadas de red."""
import json
import socket
from pathlib import Path
from types import SimpleNamespace
import permisos as P
import mi_trabajo as M
from contexto_tarea import contexto_operativo, texto_operativo

AQUI = Path(__file__).resolve().parent

def probar():
    def no_red(*a, **k): raise AssertionError('Red prohibida en la prueba')
    socket.socket.connect = no_red
    crudo = {k:json.loads((AQUI/'data'/f'{k}.json').read_text()) for k in ('personas','clientes','asignaciones')}
    mapa = P.cargar_modulos()
    M.P = P
    M.S = SimpleNamespace(E=SimpleNamespace(crudo=crudo,nucleo_bloqueado=False),ve_alguno=lambda p,ms:any(P.nivel_modulo(p,mapa.get(m,{})) for m in ms))
    persona=lambda pid:next(p for p in crudo['personas'] if p['id']==pid)
    carla,lucia,tomas,setter=[persona(x) for x in ('carla','lucia','tomas','setter_ana')]
    tasks=[{'id':'task-carla','persona_id':'carla','cli':'cli-exacto','descripcion':'Brief local operativo'}, {'id':'task-lucia','persona_id':'lucia','cli':'cli-otra'}]
    M.doc=lambda:{'tareas':tasks,'generado':'2026-10-03 02:56'}
    M._CTX_CACHE.clear()
    h=SimpleNamespace(responder=lambda codigo,obj:(codigo,obj))
    llamadas=[]
    raw={'id':'task-carla','description':'Revisar página y entregar diagnóstico.\npassword=SUPERSECRETO\nCorreo ana@example.test y +34 612 345 678, coste 500 EUR, presupuesto 6000\n<script>robar()</script>','custom_fields':[{'token':'OTRO SECRETO'}],'attachments':[{'url':'NUNCA'}]}
    def lector(tid):llamadas.append(tid);return raw
    q={'tarea':['task-carla'],'persona':['carla']}
    cod,r=M.contexto_ia(h,q,carla,carla,lector=lector)
    assert cod==200 and r['fuente']=='ClickUp en lectura' and llamadas==['task-carla']
    payload=json.dumps(r,ensure_ascii=False)
    for value in ['SUPERSECRETO','ana@example.test','612 345 678','500 EUR','6000','robar()','OTRO SECRETO','NUNCA','custom_fields','attachments']:
        assert value not in payload,value
    assert 'entregar diagnóstico' in payload and r['tarea']['id']=='task-carla' and r['tarea']['cli']=='cli-exacto'
    cod,r=M.contexto_ia(h,q,lucia,lucia,lector=lector);assert cod==403 and len(llamadas)==1 # caché no amplía permisos
    cod,r=M.contexto_ia(h,{'tarea':['task-lucia']},carla,carla,lector=lector);assert cod==403
    cod,r=M.contexto_ia(h,q,carla,tomas,lector=lector);assert cod==200 # intersección permite a Carla su propia tarea
    cod,r=M.contexto_ia(h,{'tarea':['task-lucia']},carla,tomas,lector=lector);assert cod==403 # ver como nunca permite expansión
    cod,r=M.contexto_ia(h,q,setter,carla,lector=lector);assert cod==403 # persona real sin módulo
    cod,r=M.contexto_ia(h,{'tarea':['../otra']},carla,carla,lector=lector);assert cod==400
    cod,r=M.contexto_ia(h,{'tarea':['task-inventada']},tomas,tomas,lector=lector);assert cod==403
    cod,r=M.contexto_ia(h,{'tarea':['task-carla'],'persona':['lucia']},tomas,tomas,lector=lector);assert cod==403
    M._CTX_CACHE.clear()
    def fallo(tid):raise TimeoutError('token secreto no puede salir en error')
    cod,r=M.contexto_ia(h,q,carla,carla,lector=fallo);assert cod==200 and r['fuente']=='Copia local' and 'Brief local operativo'==r['tarea']['descripcion'] and 'token secreto' not in json.dumps(r)
    cod,r=M.contexto_ia(h,q,carla,carla,lector=lambda tid:{'id':'otra','description':'NO LEER OTRA'});assert cod==200 and 'NO LEER OTRA' not in json.dumps(r)
    saneado=contexto_operativo({'text_content':raw['description'],'description':None});assert 'entregar diagnóstico' in saneado['descripcion'];assert list(saneado)==['descripcion']
    largo=contexto_operativo({'description':'a'*13000});assert largo['descripcion_truncada'] and len(largo['descripcion'])==12000
    assert '500' not in texto_operativo('Importe EUR 500; 2 mil euros; $500; sueldo 1234')
    # Ejecuta el extractor y el generador reales con fixtures, sin red ni escribir datos.
    import importlib.util, sys, io
    from contextlib import redirect_stdout
    from datetime import datetime
    cu_fixture=SimpleNamespace(tareas_equipo=lambda params:[{'id':'task-carla','name':'Revisar página','description':raw['description'],'assignees':[{'id':42}], 'status':{'status':'en curso'},'list':{'id':'lista'}}],tiempo_en_estado=lambda ids:{},ms=lambda d:0,NOW=datetime(2026,10,3))
    sys.modules['cu']=cu_fixture
    def cargar(nombre,ruta):
        spec=importlib.util.spec_from_file_location(nombre,AQUI/ruta);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod
    ex=cargar('extraer_clickup_fixture','fuentes_produccion/extraer_clickup.py')
    capturado={};ex.escribe=lambda nombre,datos:capturado.update({nombre:datos})
    assert ex.tareas({})==1
    saneada=capturado['tareas.json']['tareas'][0]
    assert 'entregar diagnóstico' in saneada['descripcion'] and 'SUPERSECRETO' not in saneada['descripcion']
    gen=cargar('generar_trabajo_fixture','fuentes_mi_trabajo/generar_mi_trabajo.py')
    pr={'cola':[{'id':'task-carla','persona_id':'carla','tarea':'Revisar página','estado':'en curso','grupo':'hoy'}]}
    gen.leer=lambda ruta,defecto=None:pr if str(ruta).endswith('produccion/produccion.json') else capturado['tareas.json'] if str(ruta).endswith('tareas.json') else {'entradas':[]} if str(ruta).endswith('horas.json') else []
    gen.personas=lambda:[carla];gen.mapa_usuarios=lambda xs:{'42':'carla'};gen.miembros_clickup=lambda:[];gen.clientes_app=lambda:({},{});salida={}
    gen.escribir=lambda ruta,datos,compacto=False:salida.update(datos)
    with redirect_stdout(io.StringIO()):gen.main()
    assert salida['tareas'][0]['descripcion']==saneada['descripcion']
    assert 'SUPERSECRETO' not in json.dumps(salida)
    M.S.E.nucleo_bloqueado=True
    cod,r=M.contexto_ia(h,q,carla,carla,lector=lector);assert cod==503
    print('OK: tarea exacta autorizada e intersección real/ver como; cliente servidor; caché sin expansión; descripción sin secretos/contactos/importes; proveedor con fallo/otra tarea cae a copia honesta; red prohibida.')

if __name__=='__main__':probar()

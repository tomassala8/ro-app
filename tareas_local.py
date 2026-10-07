"""Tablero local autorizado e idempotente. Esta fase nunca envía a ClickUp."""
import hashlib
import json
import os
from datetime import datetime,date
from zoneinfo import ZoneInfo
import re
import threading
from pathlib import Path
import inventario_tareas as IT
import vistas_tareas as VT

AQUI=Path(__file__).resolve().parent
CACHE=AQUI/'fuentes_produccion/_privado/_cache'
S=SN=None
LOCK=threading.Lock()
UUID=re.compile(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}')


def leer(path):
    try:return json.loads(path.read_text())
    except (OSError,ValueError):return {}


def inventario():
    return leer(CACHE/'tablero_tareas.json')


def puestos(p):return set(p.get('puestos') or [])


def visible(p,t,personas,permiso_cliente):
    autores=set(t.get('asignados') or [])
    equipo=autores | {personas.get(a,{}).get('jefe') for a in autores}
    amplio=bool(puestos(p)&{'direccion','operaciones'})
    if not autores:
        permitido=amplio or ('account' in puestos(p) and bool(t.get('cli')) and permiso_cliente(p,t['cli']))
    else:
        permitido=amplio or p['id'] in equipo
    return bool(permitido and (not t.get('cli') or permiso_cliente(p,t['cli'])))


def candidatos(p,t,personas,permiso_cliente):
    """Solo compañeros activos con alcance del cliente; tareas personales no amplían área."""
    autores=set(t.get('asignados') or [])
    amplios=bool(puestos(p)&{'direccion','operaciones'})
    return {pid:r for pid,r in personas.items() if r.get('estado')!='baja' and r.get('activo',True)
        and ((bool(t.get('cli')) and permiso_cliente(r,t['cli'])) or
             (not t.get('cli') and (amplios or pid in autores or pid==p['id'] or r.get('jefe')==p['id'])))}


def construir_cambio(b,t,actor,personas,permitidos,catalogo):
    """Contrato cerrado: identidades y usuarios ClickUp salen del servidor."""
    if not isinstance(b,dict) or not isinstance(b.get('clave'),str) or not UUID.fullmatch(b['clave']):
        raise ValueError('Falta una clave UUID de reintento.')
    a=b.get('accion');base={'clave','tarea','accion'}
    campos={'estado':{'estado'},'comentario':{'texto','menciones'},'entrega':{'enlace','texto','menciones'},'asignar':{'asignados'}}
    if a not in campos or set(b)-base-campos[a]:raise ValueError('Acción o campos no permitidos.')
    if str(b.get('tarea'))!=str(t['id']):raise ValueError('Tarea no válida.')
    if a=='estado':
        if not isinstance(b.get('estado'),str) or b['estado'] not in catalogo.get(t.get('lista_id'),[]):
            raise ValueError('Estado no confirmado en el catálogo de esta lista.')
        return {'campo':'estado','valor':b['estado']}
    if a=='asignar':
        ids=b.get('asignados')
        if not isinstance(ids,list) or len(ids)>30 or any(not isinstance(x,str) for x in ids) or len(set(ids))!=len(ids):
            raise ValueError('Lista de responsables no válida.')
        if not (puestos(actor)&{'direccion','operaciones'} or any(personas.get(x,{}).get('jefe')==actor['id'] for x in t.get('asignados') or [])):
            raise PermissionError('Solo su responsable, operaciones o dirección cambia responsables.')
        if any(x not in permitidos or not str(personas[x].get('clickup_id') or '').isdigit() for x in ids):
            raise ValueError('Responsable no autorizado o sin usuario ClickUp confirmado.')
        if t.get('asignados_sin_identidad'):
            raise ValueError('Hay responsables sin identidad de persona confirmada; no se reasignan a ciegas.')
        prev=set(t.get('asignados') or [])
        prev_u={str(personas[x].get('clickup_id')) for x in prev if x in personas and str(personas[x].get('clickup_id') or '').isdigit()}
        if len(prev_u)!=len(prev):raise ValueError('Hay responsables sin identidad ClickUp confirmada; no se reasignan a ciegas.')
        actual={str(personas[x]['clickup_id']) for x in ids}
        return {'campo':'asignados','personas':ids,'usuarios':sorted(actual)}
    texto=b.get('texto') or ''
    if not isinstance(texto,str) or len(texto)>2000 or (a=='comentario' and len(texto.strip())<2):raise ValueError('Comentario no válido (2 a 2000 caracteres).')
    menciones=b.get('menciones') or []
    if not isinstance(menciones,list) or len(menciones)>20 or any(not isinstance(x,str) for x in menciones) or len(set(menciones))!=len(menciones):raise ValueError('Menciones no válidas.')
    if any(x not in permitidos or not str(personas[x].get('clickup_id') or '').isdigit() for x in menciones):raise ValueError('Mención fuera del equipo autorizado o sin identidad ClickUp confirmada.')
    cam={'campo':'comentario','texto':SN.limpio(texto),'menciones':[{'persona':x,'usuario_clickup':str(personas[x]['clickup_id'])} for x in menciones]}
    if a=='entrega':
        from urllib.parse import urlparse
        url=b.get('enlace')
        if not isinstance(url,str) or len(url)>2000 or re.search(r'[\s\x00-\x1f]',url):raise ValueError('Enlace de entregable no válido.')
        u=urlparse(url)
        if u.scheme not in ('https','http') or not u.hostname or u.username or u.password:raise ValueError('Usa un enlace http o https sin credenciales.')
        cam['entrega']=url
        cam['texto']=(cam['texto']+'\nEntregable: '+url).strip()
    return cam


def guardar(con,actor,b,t,cambio):
    """Una UUID no puede reutilizarse con otro contenido; no falsa confirmación."""
    clave=hashlib.sha256(('tareas-local:'+actor['id']+':'+b['clave']).encode()).hexdigest()[:32]
    con.execute('BEGIN IMMEDIATE')
    previa=con.execute('SELECT * FROM sinc_cambios WHERE clave=?',(clave,)).fetchone()
    if previa:
        if str(previa['objeto_ref'])!=str(t['id']) or json.loads(previa['cambio'])!=cambio:
            con.rollback();raise ValueError('La clave de reintento ya corresponde a otro cambio.')
        con.commit();return previa['id'],False
    cid,nuevo=SN.crear_cambio(con,clave=clave,quien=actor['id'],canal='clickup',tipo=b['accion'],
        objeto={'tipo':'tarea','ref':t['id'],'nombre':t.get('tarea'),'resuelto':True},cambio=cambio,
        base={'estado':t.get('estado'),'asignados':t.get('_usuarios_asignados') or []},cliente_id=t.get('cli'),modulo='mi-trabajo',modo='simulado')
    con.commit();return cid,nuevo


def enganchar(Manejador,servir, *, solo_preferencias=True):
    global S,SN
    S=servir
    import sincronia
    SN=sincronia
    orig_get,orig_post=Manejador._api_get,Manejador.api_post
    def permiso(p,cid):
        # Un ámbito amplio no acredita existencia/vigencia del cliente.
        from fuentes_verdad import clientes_activos as ACT
        clientes = [c for c in S.E.crudo.get('clientes') or [] if c.get('id') == cid]
        return len(clientes) == 1 and ACT.es_activo_id(cid) and bool(S.P.ver(p,{'tipo':'cliente_detalle','cliente_id':cid},S.P.contexto(p,S.E.crudo))['ok'])
    def cambios_locales():
        out=[]
        with S.conectar() as con:
            if not con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='sinc_cambios'").fetchone():return out
            for r in con.execute("SELECT * FROM sinc_cambios WHERE modulo='mi-trabajo' ORDER BY id").fetchall():
                st=SN.estado_actual(con,r['id']) or {};cam=json.loads(r['cambio'])
                out.append({'id':r['id'],'tarea':r['objeto_ref'],'quien':r['quien'],'estado':st.get('estado'),'campo':cam.get('campo'),
                    'evento':st.get('evento'),'verificado':st.get('estado')=='confirmado' and st.get('evento')=='verificado','confirmacion_manual':st.get('evento')=='hecho_a_mano',
                    'valor':cam.get('valor'),'texto':cam.get('texto'),'menciones':cam.get('menciones'),'entrega':cam.get('entrega'),'asignados':cam.get('personas'),'creado':r['creado']})
        return out
    def datos(real,vista):
        d=inventario();ps={p['id']:{**p,'clickup_id':(d.get('usuarios_personas') or {}).get(p['id'])} for p in S.E.crudo.get('personas') or []}
        cambios=cambios_locales();por_id={str(t['id']):t for t in d.get('tareas') or []}
        for t in por_id.values():
            t['estado_clickup']=t.get('estado');t['asignados_clickup']=list(t.get('asignados') or [])
        for c in cambios:
            t=por_id.get(str(c['tarea']))
            if not t or c['estado'] not in ('simulado','pendiente','enviado','confirmado'):continue
            if c['campo']=='estado':
                t['estado_app']=c['valor'];t['estado']=c['valor'];t['cambio_estado']='confirmado_manual' if c.get('confirmacion_manual') else c['estado']
            elif c['campo']=='asignados':
                t['asignados']=list(c.get('asignados') or []);t['cambio_asignados']=c['estado']
        cat_est,cat_det=IT.catalogo_listas(leer(CACHE/'estados_listas.json'))
        try:hoy=datetime.now(ZoneInfo(vista.get('zona') or 'Europe/Madrid')).date()
        except Exception:hoy=datetime.now(ZoneInfo('Europe/Madrid')).date()
        for t in por_id.values():
            detalle=next((x for x in cat_det.get(t.get('lista_id'),[]) if x['estado']==t.get('estado')),None)
            if detalle:t['tipo_estado']=detalle.get('tipo')
            try:vence=date.fromisoformat(t['vence']) if t.get('vence') else None
            except ValueError:vence=None
            t['grupo']=IT.grupo(t,vence,hoy)
        ts=[t for t in por_id.values() if visible(vista,t,ps,permiso) and visible(real,t,ps,permiso)]
        refs={str(t['id']) for t in ts}
        return d,ps,ts,[c for c in cambios if str(c['tarea']) in refs]
    def get(self,ruta,q,real,vista):
        if ruta == '/api/tareas/vistas':
            if S.E.nucleo_bloqueado:return self.responder(503, {'error':'Datos temporalmente bloqueados.'})
            if os.environ.get('DATABASE_URL'):return self.responder(503, {'error':'Las vistas locales requieren SQLite.'})
            if real['id'] != vista['id']:return self.responder(403, {'error':'Las vistas guardadas solo se leen en tu sesión real.'})
            if not S.ve_alguno(real, ['mi-trabajo']):return self.responder(403, {'error':'No puedes ver tareas.'})
            if q:return self.responder(400, {'error':'Esta lectura no acepta filtros ni identidades.'})
            try:
                with S.conectar() as con:r = VT.listar(con, real['id'])
            except Exception:return self.responder(503, {'error':'No se pudieron leer las vistas guardadas.'})
            return self.responder(200, r)
        if solo_preferencias or ruta!='/api/tareas/tablero':return orig_get(self,ruta,q,real,vista)
        if S.E.nucleo_bloqueado:return self.responder(503,{'error':'Datos temporalmente bloqueados.'})
        if os.environ.get('DATABASE_URL'):return self.responder(503,{'error':'El tablero local requiere SQLite en esta primera fase.'})
        if not S.ve_alguno(vista,['mi-trabajo']):return self.responder(403,{'error':'No puedes ver tareas.'})
        d,ps,ts,cambios=datos(real,vista)
        cat=leer(CACHE/'estados_listas.json');est,det=IT.catalogo_listas(cat)
        listas={t.get('lista_id') for t in ts}
        ids={x for t in ts for x in t.get('asignados') or []}
        for t in ts:
            t['puede_editar']=real['id']==vista['id']
            t['puede_asignar']=t['puede_editar'] and (bool(puestos(real)&{'direccion','operaciones'}) or any(ps.get(x,{}).get('jefe')==real['id'] for x in t.get('asignados') or []))
            t['asignables']=[pid for pid,r in candidatos(real,t,ps,permiso).items() if r.get('clickup_id')]
            ids.update(candidatos(real,t,ps,permiso))
        return self.responder(200,{'tareas':[{k:v for k,v in t.items() if not k.startswith('_')} for t in ts],'personas':[{'id':pid,'nombre':ps[pid].get('alias') or ps[pid].get('nombre')} for pid in sorted(ids) if pid in ps],
            'estados_lista':{k:v for k,v in est.items() if k in listas},'estados_detalle':{k:v for k,v in det.items() if k in listas},
            'cobertura_tareas':d.get('cobertura'),'cobertura_estados':cat.get('cobertura'),'generado':d.get('generado'),
            'cobertura_contexto':{'descripcion':True,'comentarios_historicos':False,'adjuntos':False,'checklists':False,'custom_fields':False,'dependencias':False},
            'solo_lectura':real['id']!=vista['id'],'cambios':cambios[-1000:]})
    def post(self,ruta,real,vista,b):
        if ruta == '/api/tareas/vistas':
            if real['id'] != vista['id']:return self.responder(403, {'error':'Ver como es solo lectura.'})
            if S.E.nucleo_bloqueado:return self.responder(503, {'error':'Datos temporalmente bloqueados.'})
            if os.environ.get('DATABASE_URL'):return self.responder(503, {'error':'Las vistas locales requieren SQLite.'})
            if not S.ve_alguno(real, ['mi-trabajo']):return self.responder(403, {'error':'No puedes trabajar en tareas.'})
            try:
                ts = datos(real, vista)[2] if isinstance(b, dict) and b.get('accion') == 'guardar' else []
                with S.conectar() as con:r = VT.mutar(con, real['id'], b, ts)
            except VT.Conflicto:return self.responder(409, {'error':'La vista cambió o ya no está disponible. Recarga las vistas.'})
            except ValueError as e:return self.responder(400, {'error':str(e)})
            except Exception:return self.responder(503, {'error':'No se pudo guardar la preferencia. Reintenta después de recargar.'})
            return self.responder(200, r)
        if solo_preferencias or ruta!='/api/tareas/cambio':return orig_post(self,ruta,real,vista,b)
        if real['id']!=vista['id']:return self.responder(403,{'error':'Ver como es solo lectura.'})
        if S.E.nucleo_bloqueado:return self.responder(503,{'error':'Datos temporalmente bloqueados.'})
        if os.environ.get('DATABASE_URL'):return self.responder(503,{'error':'El tablero local requiere SQLite en esta primera fase.'})
        if not S.ve_alguno(real,['mi-trabajo']):return self.responder(403,{'error':'No puedes trabajar en tareas.'})
        if not isinstance(b,dict):return self.responder(400,{'error':'Cambio no válido.'})
        d,ps,ts,cambios=datos(real,vista);t=next((x for x in ts if str(x['id'])==str(b.get('tarea'))),None)
        if not t:return self.responder(403,{'error':'La tarea no está en tu inventario autorizado.'})
        try:
            est,_=IT.catalogo_listas(leer(CACHE/'estados_listas.json'))
            cam=construir_cambio(b,t,real,ps,candidatos(real,t,ps,permiso),est)
            with LOCK:
                with S.conectar() as con:
                    SN.preparar(con)
                    cid,nuevo=guardar(con,real,b,t,cam)
        except PermissionError as e:return self.responder(403,{'error':str(e)})
        except ValueError as e:return self.responder(400,{'error':str(e)})
        return self.responder(200,{'ok':True,'id':cid,'estado':'simulado','duplicado':not nuevo,'texto':'Guardado en la app; no enviado a ClickUp.'})
    Manejador._api_get,Manejador.api_post=get,post

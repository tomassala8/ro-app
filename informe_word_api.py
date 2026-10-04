"""GET privado DOCX: sólo fuentes locales ya recortadas. Sin red ni mutaciones."""
from io import BytesIO
import json
import math
import os
import re
import warnings
import informe_word as W
from meta_informe_291 import medir as medir_meta291
import informes_tareas_api as EVID

MOD='informe-cliente'
RUTA='/api/informes/word'
APARTADOS=[('mes','Cómo ha ido el mes'),('funciona','Lo que funciona'),('no_funciona','Lo que no funciona'),('pasos','Próximos pasos'),('perdidas','Llamadas perdidas o leads sin atender')]
PERFIL={'trafficker':{'meta','google_ads','embudo'},'jefa_publicidad':{'meta','google_ads','embudo'},'seo':{'ga4','gsc','seranking'},'jefa_seo':{'ga4','gsc','seranking'},'ficha_google':{'ga4','gsc','seranking'},'web':{'ga4','gsc','seranking'},'outreach':{'snov'},'jefa_crm':{'snov'},'especialista_ghl':{'embudo'}}
TODAS={'meta','google_ads','embudo','ga4','gsc','seranking','snov'}
CAMPOS={'ga4':[('usuarios','Usuarios'),('sesiones','Sesiones'),('conversiones','Conversiones registradas')],
'meta':[('impresiones','Impresiones'),('alcance','Alcance'),('leads','Resultados Meta · referencia')],
'google_ads':[('clics','Clics'),('impresiones','Impresiones'),('conversiones','Conversiones registradas')],
'embudo':[('recibidos','Recibidos'),('cualificados','Cualificados'),('citas','Citas'),('asistencias','Asistencias'),('ventas','Ventas registradas')],
'snov':[('enviados','Enviados'),('abiertos','Abiertos'),('respuestas','Respuestas')],
'seranking':[('palabras','Palabras observadas')]}


def bloques(p):
    ps=p.get('puestos') or [];res=set()
    for rol in ps:
        if rol=='produccion':continue
        if rol not in PERFIL:return TODAS.copy()
        res |= PERFIL[rol]
    return res


def analisis(filas,pid):
    todas=[]
    for f in filas:
        try:v=json.loads(f.get('vista_previa') or '{}') if isinstance(f.get('vista_previa'),str) else f.get('vista_previa') or {}
        except (ValueError,TypeError):continue
        if isinstance(v,dict):todas.append((f,v))
    anuladas={str(v['anula']) for _,v in todas if v.get('anula')}
    opciones=[(f,v) for f,v in todas if not v.get('anula') and str(f.get('id')) not in anuladas and v.get('periodo')==pid]
    opciones.sort(key=lambda x:(str(x[0].get('creada') or ''),int(x[0].get('id') or 0)),reverse=True)
    return opciones[0][1].get('apartados') or {} if opciones else {}


def logo_png(datos):
    if not isinstance(datos,bytes) or not datos or len(datos)>4*1024*1024:raise ValueError('El logo real del cliente no está disponible o es demasiado grande.')
    try:
        from PIL import Image
        with warnings.catch_warnings():
            warnings.simplefilter('error',Image.DecompressionBombWarning)
            with Image.open(BytesIO(datos)) as im:
                if im.format not in ('PNG','JPEG','WEBP','GIF') or not 0<im.width<=2048 or not 0<im.height<=2048:raise ValueError('Logo fuera del tamaño admitido.')
                im.seek(0);im.load();out=BytesIO();limpia=im.convert('RGBA');limpia.info.clear();limpia.save(out,format='PNG')
        data=out.getvalue();W.png_valido(data);return data
    except ImportError:raise RuntimeError('La conversión de logo no está disponible.')
    except Exception as e:raise ValueError('El logo real del cliente no se pudo validar.') from e


def adaptar(fila,cid,periodo,apartados,permitidos,hoy=None):
    if fila.get('cliente_id')!=cid:raise ValueError('Fuente de otro cliente.')
    av=fila.get('avisos') or []
    dto={'cliente_id':cid,'desde':periodo['desde'],'hasta':periodo['hasta'],'avisos':av,'apartados':[],'tablas':[]}
    for k,titulo in APARTADOS:
        v=apartados.get(k)
        if v:dto['apartados'].append({'titulo':titulo,'texto':W.texto(v,8000)})
    if not dto['apartados']:dto['apartados'].append({'titulo':'Análisis del equipo','texto':'El análisis guardado para este periodo está pendiente. No se ha sustituido por otro mes ni generado automáticamente.'})
    for fuente in sorted(permitidos):
        d=fila.get(fuente);estado=(fila.get('fuentes') or {}).get(fuente) or {}
        if estado.get('estado') in ('rota','sin_conectar','no_aplica','sin_acceso') or not isinstance(d,dict):
            dto['apartados'].append({'titulo':'Fuente '+fuente,'texto':'Sin indicadores disponibles para exportación en este periodo.'});continue
        actual=d.get('actual') if isinstance(d.get('actual'),dict) else d
        filas=[]
        campos=CAMPOS.get(fuente,[])
        if fuente=='gsc':
            actual=(d.get('web') or {}).get('actual') or {};campos=[('clics','Clics'),('impresiones','Impresiones')]
        for key,label in campos:
            n=actual.get(key)
            if fuente=='meta':
                mm=medir_meta291(actual,estado,periodo,hoy,fila)
                if key=='leads':n=mm['resultados'];label=mm['etiqueta']
                elif not mm['typed'] and (type(n) not in (int,float) or n<=0):n=None
            if type(n) in (int,float) and math.isfinite(n) and 0<=n<=1e12:filas.append([label,str(n)])
        if fuente=='meta':dto['apartados'].append({'titulo':'Definición de resultados Meta','texto':'Contador de la copia: sin descriptor compatible no acredita leads, compras ni coste por lead. No equivale a cualificados RO ni resultado comercial.'})
        if filas:dto['tablas'].append({'titulo':fuente,'columnas':['Indicador','Valor observado'],'filas':filas})
    dto['apartados'].append({'titulo':'Alcance del Word','texto':'Incluye análisis guardado, indicadores seleccionados y evidencia de ejecución autorizada del periodo. No incluye todos los gráficos, comparaciones o tablas del PDF; los datos observados no acreditan aceptación ni resultado comercial.'})
    return dto


def enganchar(H,S):
    previo=H._api_get
    def get(self,ruta,q,real,vista):
        if ruta!=RUTA:return previo(self,ruta,q,real,vista)
        if set(q)!={'cliente_id','periodo_id'} or any(not isinstance(v,list) or len(v)!=1 for v in q.values()):return self.responder(400,{'error':'Selecciona cliente y periodo exactos.'})
        cid,pid=q['cliente_id'][0],q['periodo_id'][0]
        if not isinstance(cid,str) or not re.fullmatch(r'[a-zA-Z0-9_-]{1,100}',cid) or not isinstance(pid,str) or not re.fullmatch(r'(?:\d{4}-\d{2}|u30|trim)',pid):return self.responder(400,{'error':'Cliente o periodo no válido.'})
        def canonicos():
            actores=[]
            for entrada in (real,vista):
                personas=[p for p in S.E.crudo.get('personas') or [] if p.get('id')==entrada.get('id')]
                if len(personas)!=1 or personas[0].get('estado')!='activo' or personas[0].get('activo') is False:return None
                actores.append(personas[0])
            return actores
        version=S.version_datos()
        inicial=canonicos()
        if inicial is None:return self.responder(403,{'error':'No puedes exportar este cliente en el contexto actual.'})
        real,vista=inicial
        firma_inicial=json.dumps([real,vista],sort_keys=True,ensure_ascii=False)
        def autorizado():
            if S.E.nucleo_bloqueado or S.version_datos()!=version:return False
            actuales=canonicos()
            if actuales is None or json.dumps(actuales,sort_keys=True,ensure_ascii=False)!=firma_inicial:return False
            cs=[c for c in S.E.crudo.get('clientes') or [] if c.get('id')==cid]
            return len(cs)==1 and cs[0].get('estado')!='baja' and cs[0].get('activo') is not False and S.ACT.es_activo_id(cid) is True and all(S.ve_alguno(p,[MOD]) and S.P.ver(p,{'tipo':'cliente_detalle','cliente_id':cid},S.P.contexto(p,S.E.crudo))['ok'] for p in actuales)
        if not autorizado():return self.responder(403,{'error':'No puedes exportar este cliente en el contexto actual.'})
        try:
            with S.P.mirando_como(real,S.E.crudo):
                cp=S.P.contexto(vista,S.E.crudo)
                comun=S.modulo_recortado(real,vista,cp,'informe/comun')
                periodos=[p for p in (comun or {}).get('periodos') or [] if p.get('id')==pid]
                if len(periodos)!=1:return self.responder(400,{'error':'Este periodo exacto no está disponible.'})
                periodo=periodos[0]
                doc=S.modulo_recortado(real,vista,cp,f'informe/c_{pid}/{cid}')
                if doc is None:doc=S.modulo_recortado(real,vista,cp,f'informe/p_{pid}')
                if not isinstance(doc,dict):return self.responder(403,{'error':'La fuente del informe no está autorizada o disponible.'})
                meta=doc.get('_meta') or {};mp=meta.get('periodo')
                if not isinstance(mp,dict) or any(mp.get(k)!=periodo.get(k) for k in ('id','desde','hasta')):return self.responder(409,{'error':'La fuente no corresponde al periodo solicitado.'})
                filas=[f for f in doc.get('filas') or [] if f.get('cliente_id')==cid]
                if len(filas)!=1:return self.responder(409,{'error':'No hay una fuente única para este cliente y periodo.'})
                with S.conectar() as con:
                    acciones=[dict(r) for r in con.execute("SELECT id,creada,vista_previa FROM acciones WHERE modulo=? AND cliente_id=? AND tipo='analisis_mes' ORDER BY id DESC LIMIT 500",(MOD,cid)).fetchall()]
                ap=analisis(acciones,pid)
                reducido=S.recortar_modulo(vista,cp,{'filas':[{'cliente_id':cid,'apartados':ap}]})
                ap=reducido['filas'][0].get('apartados') or {}
                dto=adaptar(filas[0],cid,periodo,ap,bloques(real)&bloques(vista),getattr(S,'hoy',lambda:None)())
                trabajo=S.modulo_recortado(real,vista,cp,'mi_trabajo/mi_trabajo')
                if isinstance(trabajo,dict):
                    cache,_=S.leer_json_bueno(S.AQUI/'fuentes_produccion/_privado/_cache/tareas.json')
                    catalogo,_=S.leer_json_bueno(S.AQUI/'fuentes_produccion/_privado/_cache/estados_listas.json')
                    ev=EVID.preparar(cid,periodo['desde'],periodo['hasta'],trabajo.get('tareas')or[],cache,catalogo)
                else:ev={}
                # La defensa JSON del router no intercepta un archivo binario.
                import contratos_privados as CP
                if not CP.permitido(real,vista):
                    indice=os.environ.get('RO_CONTRATOS_INDICE') or S.AQUI/'fuentes_contratos/_privado/indice_documentos.json'
                    ids=CP.indice_confirmado(indice)
                    dto=CP.sanear(dto,ids);ev=CP.sanear(ev,ids)
                lg=S.logo_de(cid)
                if not lg:return self.responder(409,{'error':'El informe Word requiere el logo real del cliente. Corrige su imagen antes de exportar.'})
                data=logo_png(lg[0])
                cliente=next(c for c in S.E.crudo['clientes'] if c['id']==cid)
                content=W.crear_docx({'id':cid,'nombre':cliente['nombre']},periodo,dto,ev,{'cliente_id':cid,'origen':'logo_cliente','contenido':data},autorizar=autorizado,vigente=lambda:S.version_datos()==version)
                if not autorizado():raise PermissionError()
            self.send_response(200)
            self.send_header('Content-Type','application/vnd.openxmlformats-officedocument.wordprocessingml.document')
            self.send_header('Content-Disposition',f'attachment; filename="informe-{cid}-{pid}.docx"')
            self.send_header('Cache-Control','private, no-store');self.send_header('X-Content-Type-Options','nosniff');self.send_header('Content-Length',str(len(content)))
            self.end_headers();self.wfile.write(content)
        except PermissionError:return self.responder(403,{'error':'El contexto cambió o ya no permite esta exportación.'})
        except ValueError:return self.responder(409,{'error':'Revisa el logo, la privacidad y el periodo antes de exportar.'})
        except Exception:return self.responder(503,{'error':'No se pudo preparar el Word con las fuentes locales.'})
    H._api_get=get

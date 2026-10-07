"""GET de borrador server-side: no persistencia, creación ni envíos externos.

El hook lo registra servir.py, no este módulo al importar. No acepta payload
cliente/lista/personas/recomendación del navegador; resuelve fuentes recortadas.
"""
import re
from cerebro_api import leer_fuentes
from cerebro_operativo import generar as generar_operativo
from propuestas_tarea import preparar
import metodo_cuentas
import cerebro_seo_api

_RUTA = '/api/cerebro/borrador'
_ID = re.compile(r'^[a-zA-Z0-9_-]{1,100}$')


def _parametro(q,nombre):
    valor=q.get(nombre)
    return valor[0] if isinstance(valor,list) and len(valor)==1 and isinstance(valor[0],str) and _ID.fullmatch(valor[0]) else None


def _cliente(S,cid,real,persona):
    filas=[c for c in S.E.crudo.get('clientes',[]) if isinstance(c,dict) and c.get('id')==cid]
    if len(filas)!=1:return None
    c=filas[0]
    if c.get('estado')=='baja' or c.get('activo_libro')=='Baja' or c.get('activo') is False:return None
    activos=getattr(S,'ACT',None)
    es_baja=getattr(activos,'es_baja_id',None)
    if callable(es_baja) and es_baja(cid):return None
    if not all(S.P.ver(p,{'tipo':'cliente_detalle','cliente_id':cid},S.P.contexto(p,S.E.crudo))['ok'] for p in (real,persona)):
        return None
    return c


def _metodo_a_recomendacion(item):
    evidencias=[]
    for ev in item.get('fuentes_operativas') or []:
        if not isinstance(ev,dict):continue
        # Doctrina operativa ya reducida: nunca ruta/contrato/precio ni body raw.
        evidencias.append({'fuente':'Decisión operativa vigente' if ev.get('tipo')=='decision_humana' else 'Reunión interna verificada',
            'fecha':ev.get('fecha'),'texto':'Seguimiento con trafficker cada 15 días.' if ev.get('tipo')=='decision_humana' else 'Hay evidencia de reunión celebrada con el rol verificado.'})
    return {'cliente_id':item.get('cliente_id'),'regla_id':item.get('regla_id'),'area':'accounts',
        'titulo':'Revisar seguimiento con el especialista de publicidad',
        'motivo':item.get('recomendacion'),'accion':item.get('recomendacion'),
        'responsable_id':item.get('responsable_id'),'responsable_role':'trafficker',
        'certeza':'Propuesta de seguimiento, no reunión agendada ni incumplimiento demostrado.',
        'criterio_entrega':'Última reunión celebrada y responsable contrastados; siguiente paso revisado con el trafficker. No se agenda ni envía automáticamente.',
        'evidencias':evidencias}


def resolver(S,real,persona,cid,regla):
    fuentes=leer_fuentes(S,real,persona)
    from consejo_metodo_308 import leer_metodo308,filtrar_recomendaciones308
    resultado=generar_operativo(*fuentes,hoy=S.P.hoy_iso(),metodo=leer_metodo308(S,real,persona))
    resultado=filtrar_recomendaciones308(S,real,persona,resultado)
    recomendaciones=list(resultado.get('recomendaciones') or [])
    if all(S.ve_alguno(p,['seo-web']) for p in (real,persona)):
        seo=cerebro_seo_api.generar(S,real,persona)
        recomendaciones.extend(seo.get('recomendaciones') or [])
    encontrados=[r for r in recomendaciones if isinstance(r,dict) and r.get('cliente_id')==cid and r.get('regla_id')==regla]
    return encontrados[0] if len(encontrados)==1 else None


def enganchar(Manejador,S):
    original=Manejador._api_get
    def get(self,ruta,q,real,persona):
        if ruta!=_RUTA:return original(self,ruta,q,real,persona)
        if S.E.nucleo_bloqueado:return self.responder(503,{'error':'Datos temporalmente bloqueados.'})
        if any(not S.ve_alguno(p,['prioridades-cliente']) for p in (real,persona)):
            return self.responder(403,{'error':'Esta vista no corresponde a tu puesto.'})
        if not isinstance(q,dict) or set(q)-{'yo','como','cliente_id','regla_id'}:
            return self.responder(400,{'error':'Filtro no válido.'})
        cid,regla=_parametro(q,'cliente_id'),_parametro(q,'regla_id')
        if cid is None or regla is None:return self.responder(400,{'error':'Filtro no válido.'})
        cliente=_cliente(S,cid,real,persona)
        if cliente is None:return self.responder(404,{'error':'Borrador no disponible.'})
        recomendacion=resolver(S,real,persona,cid,regla)
        if recomendacion is None:return self.responder(404,{'error':'Borrador no disponible.'})
        # No se aprovecha ningún mapping de persona/lista por nombre/título.
        contexto={'cliente_id':cid,'nombre':cliente.get('nombre') or '',
                  'fecha_revision':S.P.hoy_iso(),'responsables_verificados':[]}
        borrador=preparar(recomendacion,contexto,lista_validada=None,tareas_visibles=None)
        return self.responder(200,borrador)
    Manejador._api_get=get

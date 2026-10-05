"""621: puente opcional local, sin HTTP, proveedor, escrituras ni IO al importar."""
import os
from datetime import datetime,timezone
import crm_embudo_api_467 as E

class ErrorPuente621(Exception):
    def __init__(self,codigo):self.codigo=codigo;super().__init__('El ámbito actual cambió durante la consulta.')

def _crm_actual(S,rid,vid):
    ps=[E.unica(S.E.crudo.get('personas'),pid) for pid in (rid,vid)]
    conf=S.entrada_datos_modulo('crm/crm')
    mods=conf.get('modulos') if isinstance(conf,dict) else conf
    if not mods or not all(S.ve_alguno(p,mods) for p in ps):raise ErrorPuente621(403)
    return S.modulo_recortado(ps[0],ps[1],S.P.contexto(ps[1],S.E.crudo),'crm/crm')

def enriquecer_api621(S,resultado,crm,real,vista):
    configured=os.environ.get(E.ENV)
    if not configured:return resultado
    recos=resultado.get('recomendaciones') if isinstance(resultado,dict) else None
    if not isinstance(recos,list) or not isinstance(crm,dict) or not isinstance(crm.get('subcuentas'),list):return resultado
    candidatos={r.get('cliente_id') for r in recos if isinstance(r,dict) and r.get('regla_id')=='crm_citas_sin_estado' and E._id(r.get('cliente_id'))}
    objetivos=[]
    for cid in sorted(candidatos):
        rows=[r for r in crm['subcuentas'] if isinstance(r,dict) and r.get('cliente_id')==cid]
        if len(rows)!=1 or rows[0].get('tipo')!='cliente' or not E._id(rows[0].get('sub_id')):continue
        if sum(isinstance(r,dict) and r.get('sub_id')==rows[0]['sub_id'] for r in crm['subcuentas'])!=1:continue
        objetivos.append(cid)
    if not objetivos:return resultado
    rid,vid=real.get('id'),vista.get('id');firmas={};lecturas={};rechazados=set();pins=(E.SHA,E.MANIFEST_SHA)
    try:fuente=E._hash_objeto(crm)
    except (ValueError,TypeError,RecursionError):return resultado
    for cid in objetivos:
        try:firmas[cid]=E._ambito(S,rid,vid,cid)
        except E.ErrorEmbudo as e:
            if e.codigo==503:raise ErrorPuente621(503) from None
            rechazados.add(cid);continue
        try:lecturas[cid]=E.listar(S,rid,vid,cid)
        except E.ErrorEmbudo:
            # La fuente opcional no invalida una propuesta ya existente.
            # Su autoridad sí se comprueba otra vez, incluso tras error de IO.
            continue
    def vigente():
        for cid,firma in firmas.items():
            try:
                if E._ambito(S,rid,vid,cid)!=firma:raise ErrorPuente621(403)
            except E.ErrorEmbudo as e:raise ErrorPuente621(e.codigo) from None
        try:
            if not all(S.ve_alguno(E.unica(S.E.crudo.get('personas'),pid),['prioridades-cliente']) for pid in (rid,vid)):
                raise ErrorPuente621(403)
        except (E.ErrorRegistro,ValueError,KeyError,TypeError,AttributeError):raise ErrorPuente621(403) from None
    vigente()
    base=resultado
    if rechazados:
        base={**resultado,'recomendaciones':[r for r in recos if not isinstance(r,dict) or r.get('cliente_id') not in rechazados]}
        if isinstance(resultado.get('clientes'),list):
            base['clientes']=[c for c in resultado['clientes'] if not isinstance(c,dict) or c.get('cliente_id') not in rechazados]
    if not lecturas:return base
    try:actual=_crm_actual(S,rid,vid)
    except ErrorPuente621:raise
    except (E.ErrorRegistro,ValueError,KeyError,TypeError,AttributeError):raise ErrorPuente621(403) from None
    vigente()
    try:mismo=E._hash_objeto(actual)==fuente
    except (ValueError,TypeError,RecursionError):mismo=False
    if not mismo or configured!=os.environ.get(E.ENV) or pins!=(E.SHA,E.MANIFEST_SHA):return base
    from cerebro_reservas_620 import enriquecer_reservas620
    salida=enriquecer_reservas620(base,lecturas,S.P.hoy_iso(),ahora=datetime.now(timezone.utc).isoformat())
    # Última puerta después del ensamblado: no publicar destino revocado.
    vigente()
    if configured!=os.environ.get(E.ENV) or pins!=(E.SHA,E.MANIFEST_SHA):return base
    return salida

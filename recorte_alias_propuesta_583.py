"""Propuesta L04 aislada. No IO; no integración ni nuevos permisos."""
import re

ALIASES = {
 'cuota':{'cuota'},'fee':{'cuota'},'agency_fee':{'cuota'},
 'gasto':{'inversion'},'spend':{'inversion'},'ad_spend':{'inversion'},
 'budget_ads':{'inversion'},'presupuesto_ads':{'inversion'},'inversion':{'inversion'},
 'cost_per_lead':{'inversion'},'cost_per_click':{'inversion'},'cpl':{'inversion'},'cpm':{'inversion'},
 'revenue':{'cobros'},'invoice_total':{'cobros'},'cobrado':{'cobros'},'facturado':{'cobros'},
 'agency_profit':{'dinero_empresa'},'agency_margin':{'dinero_empresa'},'agency_cost':{'dinero_empresa'},
 'rentabilidad':{'dinero_empresa'},'margen':{'dinero_empresa'},'tarifa_hora':{'dinero_empresa'},
 'importe_publicidad':{'cuota','inversion'},'importe':{'cuota','inversion','cobros','dinero_empresa'},
}
SEGMENTOS = {'cuota':'cuota','fee':'cuota','inversion':'inversion','spend':'inversion','gasto':'inversion',
 'cpl':'inversion','cpm':'inversion','coste':'inversion','cobros':'cobros','facturado':'cobros',
 'cobrado':'cobros','impago':'cobros','revenue':'cobros','beneficio':'dinero_empresa','margen':'dinero_empresa'}
PII={'name','nombre','email','correo','phone','telefono','tel','lead_name','lead_email','lead_phone','nombre_lead','correo_lead','email_lead'}
LEAD_LISTAS={'leads','contactos_lead','leads_detalle'}
NO_MONETARIOS={'cuota_horas','horas_pautadas','tarifa_ruta','tarifa_busqueda','sobrecuota'}
CONTEXTOS={'operativo','cliente','empleado','hotel','lead'}

def familias_583(clave):
    if not isinstance(clave,str):return frozenset()
    k=clave.casefold()
    if k in NO_MONETARIOS:return frozenset()
    if k in ALIASES:return frozenset(ALIASES[k])
    partes=re.split(r'[_\-.]+',k)
    # Sólo tokens exactos; no coincidencia substring con tarifa/cuota en un nombre.
    familias={SEGMENTOS[p] for p in partes if p in SEGMENTOS}
    if partes and partes[0]=='importe':familias.update(('cuota','inversion','cobros','dinero_empresa'))
    return frozenset(familias)

def recortar_propuesta_583(obj, grants, *, contexto=None):
    """Contexto de esquema externo; jamás deducir tipo de persona por sus datos."""
    if contexto not in CONTEXTOS:contexto=None
    if isinstance(obj,list):return [recortar_propuesta_583(v,grants,contexto=contexto) for v in obj]
    if not isinstance(obj,dict):return obj
    out={}
    for k,v in obj.items():
        if not isinstance(k,str):continue
        normal=k.casefold();familias=familias_583(k)
        if familias and not all(grants.get(f) is True for f in familias):continue
        if normal in PII and contexto in (None,'lead'):continue
        # Aliases de lead explicitos tampoco se vuelven empleado por rootcontext.
        if normal in {'lead_name','lead_email','lead_phone','nombre_lead','correo_lead','email_lead'}:continue
        siguiente='lead' if normal in LEAD_LISTAS else contexto
        out[k]=recortar_propuesta_583(v,grants,contexto=siguiente)
    return out

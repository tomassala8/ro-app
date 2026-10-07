"""Propuesta pura576: no integración ni modificación de matriz de permisos."""
import math
import re

ALIAS = {
    'cuota':frozenset({'cuota'}), 'spend':frozenset({'inversion'}),
    'inversion':frozenset({'inversion'}), 'gasto':frozenset({'inversion'}),
    'fee':frozenset({'cuota'}), 'agency_fee':frozenset({'cuota'}),
    'budget_ads':frozenset({'inversion'}), 'ad_spend':frozenset({'inversion'}),
    'cost_per_lead':frozenset({'inversion'}), 'cost_per_click':frozenset({'inversion'}),
    'revenue':frozenset({'cobros'}), 'invoice_total':frozenset({'cobros'}),
    'agency_profit':frozenset({'dinero_empresa'}), 'agency_margin':frozenset({'dinero_empresa'}),
    'agency_cost':frozenset({'dinero_empresa'}),
    'importe_publicidad':frozenset({'cuota','inversion'}),
}
PII_LEAD=frozenset({'lead_name','lead_email','lead_phone','nombre_lead','email_lead','correo_lead','telefono','email','phone','name'})
TODO=frozenset({'cuota','inversion','cobros','dinero_empresa'})
MARCAS=(
    ('cuota',re.compile(r'\b(?:cuota|fee|honorarios|mantenimiento)\b',re.I)),
    ('inversion',re.compile(r'\b(?:inversi[oó]n|publicidad|gasto|Meta|Ads|CPL|CPM)\b',re.I)),
    ('cobros',re.compile(r'\b(?:facturado|cobrado|impagos?|revenue|cobros?)\b',re.I)),
    ('dinero_empresa',re.compile(r'\b(?:beneficio\s+(?:de\s+la\s+)?empresa|margen\s+empresa|coste\s+equipo|agency\s+profit)\b',re.I)),
)

def familias_alias_576(clave,valor,*,contexto=None,unidad=None):
    """Sólo aliases exactos y valores monetarios acreditados; no tarifa/cuota genéricas."""
    if not isinstance(clave,str):return frozenset()
    clave=clave.casefold()
    if contexto=='lead' and clave in PII_LEAD:return frozenset({'lead_privado'})
    economico=(type(valor) in (int,float) and math.isfinite(valor)) or unidad in ('EUR','USD')
    return ALIAS.get(clave,frozenset()) if economico else frozenset()

def admite_familias_576(familias,permiso):
    """Cada familia requiere su grant actual; lead claro exige puerta privada aparte."""
    if not familias:return True
    if 'lead_privado' in familias:return False
    return all(permiso(tipo) is True for tipo in familias)

def familia_texto_576(texto,ini,fin):
    """Prototipo: marcador más próximo en misma cláusula; desconocido no es inversión."""
    if not isinstance(texto,str) or type(ini) is not int or type(fin) is not int or not 0<=ini<fin<=len(texto):return TODO
    cortes=list(re.finditer(r';|\n|·|(?<=[.!?])\s+(?=[A-Za-zÁÉÍÓÚáéíóú])',texto))
    inicio=max([m.end() for m in cortes if m.end()<=ini] or [0])
    final=min([m.start() for m in cortes if m.start()>=fin] or [len(texto)])
    cercanos=[]
    for familia,rx in MARCAS:
        for m in rx.finditer(texto,inicio,final):
            if m.end()<=ini:distancia=ini-m.end()
            elif m.start()>=fin:distancia=m.start()-fin
            else:continue
            if distancia<=40:cercanos.append((distancia,familia))
    if not cercanos:return TODO
    distancia=min(d for d,_ in cercanos)
    return frozenset(f for d,f in cercanos if d==distancia)

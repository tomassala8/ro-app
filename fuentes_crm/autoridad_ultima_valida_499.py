"""Callback servidor para proyección agregada496. Sin IO al importar/construir.

No autoriza contactos individuales ni obtención/persistencia de payload proveedor.
leer_crm es una dependencia confiable del servidor, nunca datos del body HTTP.
"""
from crm_embudo_api_467 import _ambito, _hash_objeto, _id, ErrorEmbudo


def _mapping(doc):
    if not isinstance(doc,dict) or not isinstance(doc.get('subcuentas'),list):
        raise PermissionError('Fuente de autoridad no disponible.')
    rows=[];cids=set();sids=set()
    for r in doc['subcuentas']:
        if not isinstance(r,dict) or not _id(r.get('sub_id')):
            raise PermissionError('Mapping no disponible.')
        sid=r['sub_id']
        if sid in sids:raise PermissionError('Mapping ambiguo.')
        sids.add(sid)
        cid=r.get('cliente_id')
        if cid is None:
            if r.get('tipo') not in ('interna','prueba','sin_cliente'):
                raise PermissionError('Mapping no disponible.')
            continue
        if r.get('tipo')!='cliente' or not _id(cid) or cid in cids:
            raise PermissionError('Mapping ambiguo.')
        cids.add(cid);rows.append({'cliente_id':cid,'subcuenta_id':sid})
    return sorted(rows,key=lambda r:r['cliente_id'])


def construir_callback(S,real_id,vista_id,leer_crm):
    """Devuelve callable496 sin argumentos; recalcula autoridad en cada llamada."""
    if not _id(real_id) or not _id(vista_id) or not callable(leer_crm):
        raise PermissionError('Identidad no disponible.')

    def snapshot():
        if S.E.nucleo_bloqueado:raise PermissionError('Datos temporalmente bloqueados.')
        initial=_hash_objeto([S.E.crudo,S.P.REGLAS,S.E.modulos,S.P.hoy_iso()])
        doc=leer_crm();marca=_hash_objeto(doc);mapping=_mapping(doc)
        allowed=[];firmas=[]
        for row in mapping:
            try:firma=_ambito(S,real_id,vista_id,row['cliente_id'])
            except ErrorEmbudo as e:
                if e.codigo==403:continue
                raise PermissionError('Ámbito no disponible.') from None
            allowed.append(row);firmas.append(firma)
        if not allowed:raise PermissionError('Sin ámbito agregado autorizado.')
        # También firma exclusiones: una cartera o catálogo cambiante no puede
        # mantener la misma firma sólo porque el cliente antes era invisible.
        raw_firma=_hash_objeto([S.E.crudo,S.P.REGLAS,S.E.modulos,S.P.hoy_iso()])
        if S.E.nucleo_bloqueado or raw_firma!=initial:
            raise PermissionError('Ámbito cambió durante la lectura.')
        return {'actor_real':real_id,'actor_vista':vista_id,
                'firma_sha256':_hash_objeto([marca,raw_firma,allowed,firmas]),'clientes':allowed}

    def callback():
        try:
            first=snapshot();last=snapshot()
            if first!=last:raise PermissionError('Ámbito cambió durante la lectura.')
            return last
        except PermissionError:raise
        except (ValueError,TypeError,KeyError,AttributeError,RecursionError,OSError):
            raise PermissionError('Autoridad no disponible.') from None
    return callback

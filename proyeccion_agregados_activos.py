"""207: proyección pura POST permisos/ACT; no consultas, nombres inferidos ni reloj nuevo.

Los recuentos describen la copia visible. Una cartera asignada no se deduce de
subcuentas conectadas. Los indicadores de ventanas del generador legado carecen
de cobertura tipada y se devuelven desconocidos, nunca como cero ni garantía.
"""
from copy import deepcopy


def _filas(doc, clave, identidad):
    filas = doc.get(clave)
    if not isinstance(filas, list):
        return None
    if any(not isinstance(f, dict) or not isinstance(f.get(identidad), str) or not f[identidad] for f in filas):
        return None
    ids = [f[identidad] for f in filas]
    return filas if len(set(ids)) == len(ids) else None


def _cuenta(filas, clave, valor=True):
    if filas is None or any(type(f.get(clave)) is not bool for f in filas):
        return None
    return sum(f[clave] is valor for f in filas)


def _meta(doc):
    return {'version': '207.1', 'alcance': 'filas_visibles_post_permisos_y_act',
            'fuente_generado': doc.get('generado'), 'datos_hasta': doc.get('datos_hasta'),
            'periodo_certificado': False, 'estado': 'referencia_de_copia',
            'limitacion': 'No acredita lectura completa, cartera asignada, salud actual ni conversiones.'}


def verdad(doc):
    out = deepcopy(doc)
    comun = _filas(out, 'comun', 'id')
    detalle = _filas(out, 'clientes', 'cliente_id')
    # No conserva resúmenes globales recibidos antes del recorte de la persona.
    if 'resumen' in out:
        resumen = {k: None for k in out['resumen']} if isinstance(out['resumen'], dict) else {}
        conocidos = {'critico', 'atencion', 'bien'}
        estado_valido = comun is not None and all(f.get('gravedad') in conocidos for f in comun)
        for k in conocidos:
            resumen[k] = sum(f['gravedad'] == k for f in comun) if estado_valido else None
        resumen['estado_desconocido'] = (sum(f.get('gravedad') not in conocidos for f in comun)
                                         if comun is not None else None)
        for clave, filas in [('nuevos', comun), ('sin_account', comun),
                             ('sin_reunion_mes_pasado', detalle), ('bloqueo_callado', detalle)]:
            resumen[clave] = _cuenta(filas, 'nuevo' if clave == 'nuevos' else clave)
        out['resumen'] = resumen
    visibles = ({f['id'] for f in comun} if comun is not None else set()) | ({f['cliente_id'] for f in detalle} if detalle is not None else set())
    for c in out.get('carteras', []) if isinstance(out.get('carteras'), list) else []:
        if not isinstance(c, dict):
            continue
        for campo, contador in [('principal', 'n_principal'), ('apoyo', 'n_apoyo')]:
            ids = c.get(campo)
            valido = isinstance(ids, list) and all(isinstance(i, str) and i for i in ids) and len(set(ids)) == len(ids)
            if valido:
                c[campo] = [i for i in ids if i in visibles]
            else:
                c[campo] = []
            c[contador] = len(c[campo]) if valido and (comun is not None or detalle is not None) else None
        u = c.get('universo')
        if isinstance(u, dict):
            # Sólo un complemento completo y coherente acredita «dentro».
            fuera = u.get('fuera')
            if isinstance(fuera, list) and all(isinstance(i, str) and i for i in fuera):
                fuera = [i for i in fuera if i in visibles]
                u['fuera'] = fuera
            valido = (c['n_principal'] is not None and isinstance(fuera, list)
                      and all(isinstance(i, str) and i for i in fuera)
                      and len(set(fuera)) == len(fuera) and set(fuera) <= set(c['principal']))
            u['dentro'] = c['n_principal'] - len(fuera) if valido else None
            u['texto'] = ('Referencia de la copia: %s de %s clientes visibles en este universo.' % (u['dentro'], c['n_principal'])
                          if valido else 'Universo pendiente de verificar.')
    out['agregados_cobertura'] = _meta(doc)
    return out


# No se agregan ventanas textuales ni resultados parciales/default0 del legado.
_CRM_DESCONOCIDOS = ('verde', 'ambar', 'rojo', 'pct_verde', 'leads_30d', 'sin_tocar_24h',
                    'velocidad_pct_1h', 'velocidad_juzgables', 'despachos_cumplen_garantia',
                    'despachos_juzgables_garantia', 'asistencia_pct', 'estancados_72h',
                    'integracion_rota', 'encendidas_sin_especialista')


def crm(doc):
    out = deepcopy(doc)
    filas = _filas(out, 'subcuentas', 'sub_id')
    clientes = [f for f in filas if f.get('tipo') not in ('prueba', 'interna')] if filas is not None else None
    diagnostico = [f for f in filas if f.get('tipo') in ('prueba', 'interna')] if filas is not None else None
    if 'resumen' in out:
        r = {k: None for k in out['resumen']} if isinstance(out['resumen'], dict) else {}
        r.update({k: None for k in _CRM_DESCONOCIDOS})
        for key, fs in [('subcuentas', filas), ('de_clientes', clientes), ('pruebas_e_internas', diagnostico)]:
            r[key] = len(fs) if fs is not None else None
        r['encendidas'] = _cuenta(clientes, 'encendida')
        r['estado_desconocido'] = len(clientes) if clientes is not None else None
        r['citas_30d'] = {k: None for k in ('agendadas', 'celebradas', 'no_presentadas', 'sin_estado', 'canceladas', 'futuras')}
        r['citas_14d'] = {k: None for k in ('agendadas', 'celebradas', 'no_presentadas', 'sin_estado')}
        r['whatsapp'] = {'enviados': None, 'fallidos': None}
        out['resumen'] = r
    for e in out.get('especialistas', []) if isinstance(out.get('especialistas'), list) else []:
        if not isinstance(e, dict):
            continue
        # Preserva identidad/etiqueta ya recortada; no replica totales globales.
        for k in ('clientes', 'encendidas', 'verde', 'ambar', 'rojo', 'gris', 'sin_tocar', 'sin_estado', 'sin_subcuenta'):
            e[k] = None
        asignadas = ([f for f in clientes if f.get('especialista_id') == e.get('id')]
                     if clientes is not None and isinstance(e.get('id'), str) else None)
        e['subcuentas'] = len(asignadas) if asignadas is not None else None
        e['agregados_cobertura'] = {'estado': 'parcial', 'alcance': 'subcuentas_visibles',
                                   'cartera_asignada_confirmada': False,
                                   'fuente_generado': doc.get('generado')}
    out['agregados_cobertura'] = _meta(doc)
    return out

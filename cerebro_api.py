"""Diagnóstico de lectura sobre las mismas fuentes ya autorizadas de cada pantalla."""
FUENTES = ('captacion/captacion', 'crm/crm', 'objetivos/objetivos')


def leer_fuentes(S, real, persona):
    cp = S.P.contexto(persona, S.E.crudo)
    out = []
    for rel in FUENTES:
        entrada = S.entrada_datos_modulo(rel)
        conf = entrada if isinstance(entrada, dict) else {'modulos': entrada or []}
        # Nunca transformar permiso de ver una pantalla de resumen en acceso a otra.
        if not S.ve_alguno(real, conf.get('modulos') or []) or not S.ve_alguno(persona, conf.get('modulos') or []):
            out.append(None)
            continue
        out.append(S.modulo_recortado(real, persona, cp, rel))
    return out


def responsables_actuales(S, resultado, real, vista):
    """La referencia de la fuente no reasigna: confirma silla exacta o deja pendiente."""
    raw = S.E.crudo
    def unico(xs, identidad):
        filas = [p for p in xs or [] if isinstance(p, dict) and p.get('id') == identidad]
        return filas[0] if len(filas) == 1 else None
    def vigente(p):
        return bool(p and p.get('estado') == 'activo' and p.get('activo') is not False)
    real_actual = unico(raw.get('personas'), real.get('id'))
    vista_actual = unico(raw.get('personas'), vista.get('id'))
    recos = []
    for r in resultado.get('recomendaciones') or []:
        if 'responsable_id' not in r:
            recos.append(dict(r)); continue
        cid, pid, silla = r.get('cliente_id'), r.get('responsable_id'), r.get('responsable_role')
        p = unico(raw.get('personas'), pid)
        cliente = unico(raw.get('clientes'), cid)
        ok = vigente(p) and vigente(real_actual) and vigente(vista_actual) and bool(cliente and cliente.get('activo') is not False and cliente.get('estado') != 'baja')
        if ok:
            ok = getattr(S, 'ACT', None) is not None and S.ACT.es_activo_id(cid) is True
        if ok:
            ok = all(S.P.ver(actor, {'tipo':'cliente_detalle','cliente_id':cid}, S.P.contexto(actor,raw))['ok'] for actor in (real_actual,vista_actual))
        if ok:
            filas = [a for a in raw.get('asignaciones') or [] if a.get('persona_id') == pid and a.get('cliente_id') == cid and a.get('silla') == silla
                     and S.P._vigente(a,S.P.hoy_iso()) and not (a.get('suplencia') and not a.get('hasta'))]
            ok = len(filas) == 1 and cid in S.P.cartera_por_silla(p, filas, clientes=[cliente]).get(silla,set())
        recos.append({**r,'responsable_id':pid if ok else None,
                      'responsable_estado':'asignacion_confirmada' if ok else 'asignacion_pendiente',
                      'responsable_nota':None if ok else 'Confirmar responsable activo y silla vigente de este cliente; no se ha reasignado.'})
    return {**resultado,'recomendaciones':recos}


def enganchar(Manejador, S):
    original = Manejador._api_get

    def get(self, ruta, q, real, persona):
        if ruta != '/api/cerebro/operativo':
            return original(self, ruta, q, real, persona)
        if S.E.nucleo_bloqueado:
            return self.responder(503, {'error': 'Datos temporalmente bloqueados.'})
        if not S.ve_alguno(real, ['prioridades-cliente']) or not S.ve_alguno(persona, ['prioridades-cliente']):
            return self.responder(403, {'error': 'Esta vista no corresponde a tu puesto.'})
        if set(q) - {'area', 'yo', 'como'}:
            return self.responder(400, {'error': 'Filtro no válido.'})
        area = (q.get('area') or [''])[0]
        if area not in ('', 'paid', 'crm', 'accounts', 'seo'):
            return self.responder(400, {'error': 'Área no válida.'})
        from cerebro_operativo import generar
        fuentes = leer_fuentes(S, real, persona)
        from consejo_metodo_308 import leer_metodo308, filtrar_recomendaciones308
        resultado = responsables_actuales(S, generar(*fuentes, hoy=S.P.hoy_iso(), metodo=leer_metodo308(S,real,persona)), real, persona)
        resultado = filtrar_recomendaciones308(S,real,persona,resultado)
        if area:
            resultado = {**resultado, 'recomendaciones': [r for r in resultado.get('recomendaciones') or [] if r.get('area') == area]}
        from reservas_cerebro_api_621 import enriquecer_api621, ErrorPuente621
        try:
            resultado = enriquecer_api621(S, resultado, fuentes[1], real, persona)
        except ErrorPuente621 as e:
            return self.responder(e.codigo, {'error':str(e)})
        return self.responder(200, resultado)

    Manejador._api_get = get

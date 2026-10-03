#!/usr/bin/env python3
"""
fuentes_gbp/servidor_gbp.py · reseñas de la ficha de Google en la app (3-oct-2026). Se engancha a servir.py como
fuentes_modular/acceso.py (envuelve _api_get y api_post). Sin este fichero, nada cambia.

  GET  /api/gbp/estado                 estado de la conexión (pendiente de aprobación, conectado…), pasos de Tomás e interruptor
  POST /api/gbp/borrador {resena_id}   «Proponer respuesta»: borrador con el cerebro de reseñas (IA si hay clave y no es
                                       «ver como»; si no, por reglas) + nota de calidad. NO publica nada
  POST /api/gbp/responder {resena_id, texto, modulo}   deja la respuesta en la COLA DE ACCIONES (herramienta
                                       google_business, tipo responder_resena) en SIMULACIÓN: nada sale a Google
  GET  /api/gbp/cola[?cliente=]        respuestas en cola que la persona puede ver, con su estado

Reglas:
  · El cliente de la reseña lo saca el SERVIDOR de data/gbp/gbp.json (el navegador solo manda el id de la reseña).
  · Proponer y responder: tipo «gbp_responder» de reglas_permisos.json (SEO/ficha de Google de su cartera, su account,
    jefe de SEO, operaciones y dirección). Responder nunca en «ver como». Una respuesta con un bloqueo de calidad (correo o
    teléfono escrito, enlace, confirma que es cliente, importes, otro cliente) o con [completar: …] sin rellenar no entra.
  · INTERRUPTOR del canal Google (data/gbp/interruptor.json): apagado. Encendido exigiría «google_real: true» +
    «activado_por: tomas» + RO_GBP_REAL=si + una llave de escritura aparte; aun así, el publicador real NO está construido
    (gbp.py es de solo lectura por diseño): la acción queda «simulada» y lo dice.
  · Rastro imborrable: gbp_borrador, gbp_respuesta_simulada, gbp_denegado (solo servidor).
Pruebas: RO_GBP_DOC=<fichero> usa otro gbp.json (p. ej. el simulado de generar_gbp.py --simulado --salida …).
"""
import json
import os
import re
import sys
import time
from pathlib import Path

AQUI = Path(__file__).resolve().parent
APP = AQUI.parent
DOC = Path(os.environ.get('RO_GBP_DOC') or APP / 'data' / 'gbp' / 'gbp.json')
INTERRUPTOR = APP / 'data' / 'gbp' / 'interruptor.json'
RX_ID = re.compile(r'^r_[0-9a-f]{14}$')
MODULOS = ('seo-web', 'ficha')
APAGADO = ('Respuesta guardada en la app (cola de acciones) y SIN publicar: el canal de Google está apagado. '
           'Cópiala y publícala en business.google.com, o espera a que Tomás encienda el canal.')
sys.path.insert(0, str(APP / 'fuentes_ia' / 'cerebro_respuestas'))
import resenas as R  # noqa: E402


def _leer(p, defecto=None):
    try:
        return json.loads(Path(p).read_text())
    except Exception:
        return defecto


def interruptor():
    i = _leer(INTERRUPTOR, {}) or {}
    encendido = bool(i.get('google_real') and i.get('activado_por') == 'tomas' and os.environ.get('RO_GBP_REAL') == 'si')
    return {'encendido': encendido, 'publicador': False,
            'texto': 'Canal de Google apagado: nada se publica en Google desde la app.' if not encendido else
                     'Canal encendido por Tomás, pero el publicador real no está construido (la app es de solo lectura en Google).'}


def buscar(rid):
    """(reseña, cliente_id, cliente, ficha) sacados del fichero del servidor, o (None…)."""
    d = _leer(DOC, {}) or {}
    for c in d.get('clientes') or []:
        for f in c.get('fichas') or []:
            rs = f.get('resenas') or {}
            for r in (rs.get('por_responder') or []) + (rs.get('ultimas') or []):
                if r.get('id') == rid:
                    return r, c.get('cliente_id'), c.get('cliente'), f
    return None, None, None, None


def enganchar(Manejador, servir):
    S = servir
    get_orig, post_orig = Manejador._api_get, Manejador.api_post

    def ve_gbp(persona):
        return S.ve_alguno(persona, list(MODULOS))

    def puede(persona, cid):
        cp = S.P.contexto(persona, S.E.crudo)
        return bool(cid) and S.P.ver(persona, {'tipo': 'gbp_responder', 'cliente_id': cid}, cp)['ok'] \
            and S.P.ver(persona, {'tipo': 'cliente_detalle', 'cliente_id': cid}, cp)['ok']

    def otros(cid):
        return [c.get('nombre') for c in S.E.crudo.get('clientes', []) if c.get('id') != cid and c.get('nombre')]

    def denegar(h, real, persona, rid, motivo, codigo=403, texto=None):
        S.registrar_agrupado(real['id'], 'gbp', 'gbp_denegado', str(rid)[:20] or None, {'motivo': motivo},
                             como=persona['id'] if real['id'] != persona['id'] else None)
        return h.responder(codigo, {'error': texto or (S.P.REGLAS['tipos'].get('gbp_responder') or {}).get('no') or 'No puedes.'})

    def _api_get(self, ruta, q, real, persona):
        if ruta == '/api/gbp/estado':
            if not ve_gbp(persona):
                return self.responder(403, {'error': 'Esta pantalla no es de tu puesto.'})
            m = (_leer(DOC, {}) or {}).get('_meta') or {}
            return self.responder(200, {'estado': m.get('estado') or 'pendiente_aprobacion', 'titular': m.get('titular'),
                                        'texto': m.get('texto'), 'pasos': m.get('pasos') or [], 'generado': m.get('generado'),
                                        'interruptor': interruptor()})
        if ruta == '/api/gbp/cola':
            if not ve_gbp(persona):
                return self.responder(403, {'error': 'Esta pantalla no es de tu puesto.'})
            cid = str((q.get('cliente') or [''])[0])[:80] or None
            cp = S.P.contexto(persona, S.E.crudo)
            with S.conectar() as con:
                filas = [dict(x) for x in con.execute(
                    "SELECT id, creada, quien, objeto, cliente_id, texto, vista_previa, estado, detalle FROM acciones "
                    "WHERE herramienta='google_business' AND tipo='responder_resena' ORDER BY id DESC LIMIT 300").fetchall()]
            out = []
            for f in filas:
                if (cid and f['cliente_id'] != cid) or not S.P.ver(persona, {'tipo': 'cliente_detalle', 'cliente_id': f['cliente_id']}, cp)['ok']:
                    continue
                f['vista_previa'] = _leer_json_txt(f.get('vista_previa'))
                f['quien_nombre'] = (S.E.persona(f['quien']) or {}).get('nombre', f['quien']).split()[0]
                out.append(f)
            return self.responder(200, {'cola': out[:100], 'interruptor': interruptor()})
        return get_orig(self, ruta, q, real, persona)

    def api_post(self, ruta, real, persona, b):
        if ruta not in ('/api/gbp/borrador', '/api/gbp/responder'):
            return post_orig(self, ruta, real, persona, b)
        b = b or {}
        rid = str(b.get('resena_id') or '')
        if not RX_ID.match(rid):
            return self.responder(400, {'error': 'Falta la reseña.'})
        if not ve_gbp(persona):
            return denegar(self, real, persona, rid, 'pantalla que no ve', texto='Esta pantalla no es de tu puesto.')
        r, cid, cliente, ficha = buscar(rid)
        if not r:
            return self.responder(404, {'error': 'Esa reseña no está en la última lectura de Google.'})
        if not puede(persona, cid):
            return denegar(self, real, persona, rid, 'sin permiso en ese cliente')
        como = persona['id'] if real['id'] != persona['id'] else None
        despacho = cliente or ''
        if ruta == '/api/gbp/borrador':
            salida, origen, modelo = None, 'reglas', None
            IA = sys.modules.get('ia')
            if not como and IA is not None:
                try:
                    if IA.estado().get('conectada'):
                        ctx = R.contexto(r, despacho, ficha.get('nombre'))
                        salida, modelo = IA.llamar(R.SISTEMA, ctx, R.ESQUEMA, effort='medium', tarea='borrador')
                        cal = R.calidad(salida.get('texto'), r, despacho, otros(cid))
                        if cal['nota'] < 70 or cal['bloqueos']:
                            ctx2 = {**ctx, 'revision_de_calidad': {'anterior': salida.get('texto'), 'faltas': cal['faltas'] + cal['bloqueos']}}
                            s2, modelo = IA.llamar(R.SISTEMA, ctx2, R.ESQUEMA, effort='medium', tarea='borrador')
                            if R.calidad(s2.get('texto'), r, despacho, otros(cid))['nota'] >= cal['nota']:
                                salida = s2
                        origen = 'ia'
                except Exception:  # noqa: BLE001 · sin IA (topes, caída, ver como…) → reglas, sin coste
                    salida, origen = None, 'reglas'
            if not salida:
                salida = R.por_reglas(r, despacho)
            cal = R.calidad(salida.get('texto'), r, despacho, otros(cid))
            S.registrar(real['id'], 'gbp', 'gbp_borrador', rid, {'cliente_id': cid, 'origen': origen, 'nota': cal['nota']}, como=como)
            return self.responder(200, {'ok': True, 'resena_id': rid, 'cliente_id': cid, 'origen': origen, 'modelo': modelo,
                                        'tipo': salida.get('tipo'), 'texto': salida.get('texto'), 'recomendacion': salida.get('recomendacion')
                                        or R.RECOMENDACION.get(R.tipo(r)), 'calidad': cal,
                                        'aviso': 'Borrador: revísalo con el account y completa los huecos. Nada se publica solo.'})
        # ---------------------------------------------------------------- responder (simulado)
        if como:
            return self.responder(403, {'error': 'Estás en «ver como»: es solo lectura. No se guarda ninguna respuesta.'})
        texto = str(b.get('texto') or '').strip()
        modulo = str(b.get('modulo') or 'seo-web')
        if modulo not in MODULOS or not S.ve_alguno(persona, [modulo]):
            return self.responder(400, {'error': 'Falta el módulo (SEO › Ficha de Google o la ficha del cliente).'})
        if len(texto) < 2 or len(texto.encode()) > 4096:
            return self.responder(400, {'error': 'La respuesta tiene que tener entre 2 caracteres y 4.096 bytes (límite de Google).'})
        cal = R.calidad(texto, r, despacho, otros(cid))
        if cal['bloqueos']:
            return self.responder(400, {'error': 'No se puede guardar así: ' + ' '.join(cal['bloqueos']), 'calidad': cal})
        if cal['huecos']:
            return self.responder(400, {'error': 'Completa los huecos [completar: …] antes de guardarla.', 'calidad': cal})
        with S.conectar() as con:
            previa = con.execute("SELECT id FROM acciones WHERE herramienta='google_business' AND tipo='responder_resena' AND objeto=? "
                                 "AND quien=? AND texto=? AND creada >= datetime('now', '-120 seconds')", (rid, real['id'], texto)).fetchone()
            if previa:
                return self.responder(200, {'ok': True, 'id': previa[0], 'estado': 'simulada', 'repetida': True, 'texto': APAGADO})
            vp = {'resena': r.get('ref'), 'estrellas': r.get('estrellas'), 'ficha': ficha.get('nombre'), 'nota': cal['nota'],
                  'canal': 'google', 'interruptor': 'apagado' if not interruptor()['encendido'] else 'encendido_sin_publicador'}
            cur = con.execute("INSERT INTO acciones (quien, herramienta, tipo, objeto, cliente_id, modulo, texto, vista_previa, estado, detalle) "
                              "VALUES (?,?,?,?,?,?,?,?, 'simulada', ?)",
                              (real['id'], 'google_business', 'responder_resena', rid, cid, modulo, texto, json.dumps(vp, ensure_ascii=False),
                               'Canal de Google apagado: no se ha publicado nada en Google. Lo enciende Tomás (interruptor y llave de escritura aparte).'))
            aid = cur.lastrowid
        S.registrar(real['id'], 'gbp', 'gbp_respuesta_simulada', rid, {'accion_id': aid, 'cliente_id': cid, 'nota': cal['nota']})
        return self.responder(200, {'ok': True, 'id': aid, 'estado': 'simulada', 'texto': APAGADO, 'calidad': cal,
                                    'sincronia': {'id': aid, 'estado': 'simulado', 'texto': 'Hecho en la app · sin publicar en Google'}})

    Manejador._api_get = _api_get
    Manejador.api_post = api_post


def _leer_json_txt(t):
    try:
        return json.loads(t) if t else None
    except Exception:
        return None

"""Checklists genéricas curadas 134: propuestas de referencia, nunca autoridad ni ejecución."""
import hashlib
import json
import os
from pathlib import Path
import pathlib as _pl_l27, sys as _sys_l27  # L-27: rutas del Mac por config.py
if str(_pl_l27.Path(__file__).resolve().parents[0]) not in _sys_l27.path:
    _sys_l27.path.append(str(_pl_l27.Path(__file__).resolve().parents[0]))
import config as _cfg  # noqa: E402

VERSION = '134.1.0'
CATALOGO = {'schema_version': 1, 'catalog_version': '134.1.0', 'created_on': '2026-10-03', 'repository_head_local': '896bf06681750d5866fc1bf0173f7a3ba8190e21', 'status': 'candidato_no_integrado', 'role_tags_grant_access': False, 'precedence_guards': [{'path': '50_PRODUCTO/_AVISO_VIGENCIA.md', 'sha256': 'd47a02923ec93324b98b97c0a7bc7101837695b7173c40ec75006cd6be34818d'}, {'path': '20_METODO/METODO_ENTREGA_RO/14_PAQUETE_EQUIPO_METODO_V2/00_LEEME_PRIMERO.md', 'sha256': '0dd42cec587d6d6eb28dcd3531fce77de003cdfb2410edf5312cbd7d772dc8b0'}], 'resources': [{'id': 'paid_preflight', 'title': 'Paid: evidencia técnica antes de revisar lanzamiento', 'discipline': 'paid', 'role_tags': ['paid'], 'service_keys': ['publicidad'], 'state': 'propuesta', 'version': '134.1.0', 'reviewed_on': '2026-10-03', 'approval': None, 'source': {'repository': 'tomassala8/ro-equipo', 'path': '20_METODO/METODO_ENTREGA_RO/plantillas/PL-P2-08_checklist-paid-12-puntos.md', 'sha256': 'ce877b675758250a1289e89bfd61fec534fc1e7b8f0837934e3d528d72d28366', 'last_local_git_change': '2026-09-11', 'declared_version': None, 'sections': ['Plantilla puntos 4–7 y 12; notas de calidad']}, 'excerpt': {'steps': ['Probar landing o formulario en móvil y escritorio y conservar evidencia.', 'Comprobar que un envío de prueba produce una sola conversión y contrastarla con el CRM autorizado.', 'Revisar geografía e idioma de campaña, web y medición.', 'Comprobar llegada del formulario al pipeline y la notificación al despacho.', 'Documentar el canal operativo de feedback entre Account y Paid.'], 'delivery_qa': 'Adjuntar evidencias verificables de cada comprobación; los puntos sin evidencia quedan pendientes.'}, 'excerpt_sha256': '8ec7de639fdfa1dd0828721fbba211047f7e4a3e91651ee63372f28a705b5fec', 'limitations': ['Punto 8 antiguo y SOP CRM difieren en intentos; aviso septiembre cambia deberes.', 'No adoptar plazos, presupuestos, firma personal, promesas ni Google para venta nueva.'], 'classification': 'generic_curated_operational', 'source_is_authority': False}, {'id': 'crm_flow_check', 'title': 'CRM: revisión del flujo de punta a punta', 'discipline': 'crm', 'role_tags': ['crm'], 'service_keys': ['crm_ghl'], 'state': 'propuesta', 'version': '134.1.0', 'reviewed_on': '2026-10-03', 'approval': None, 'source': {'repository': 'tomassala8/ro-equipo', 'path': '20_METODO/METODO_ENTREGA_RO/P2_MOTOR_CAPTACION/SOP-P2-03_sistema-comercial-ghl-protocolo.md', 'sha256': '1f1c94de2e14c3e1b4cca56d8fb9a79ff114c0819e25efc52a42c1aa73b8d46a', 'last_local_git_change': '2026-09-11', 'declared_version': None, 'sections': ['Tarjeta de acción 2; tabla bloque C punto 11; QA de salida']}, 'excerpt': {'steps': ['Identificar la subcuenta y cada formulario autorizado antes de preparar la prueba.', 'Preparar una prueba de punta a punta: formulario, card del pipeline, confirmación, notificación y agenda.', 'Registrar qué pasos se observaron y cuáles quedaron sin verificar.', 'Separar configuración inicial, desarrollo incremental y seguimiento.'], 'delivery_qa': 'Evidencia por tramo del flujo; configuración declarada no equivale a prueba superada.'}, 'excerpt_sha256': '8635e99b9ecf3102aee242436e5d99e3fb840ba63f6fdf2ecf40d7491c7ae387', 'limitations': ['SOP mantiene compromisos y cláusulas antiguos; no importar números de intentos, tiempos o firmas.', 'Snapshot descrito no acredita que esté desplegado. Preparar prueba; su ejecución requiere autorización independiente.'], 'classification': 'generic_curated_operational', 'source_is_authority': False}, {'id': 'seo_page_qa', 'title': 'SEO: revisión de página local', 'discipline': 'seo', 'role_tags': ['seo', 'web'], 'service_keys': ['seo'], 'state': 'propuesta', 'version': '134.1.0', 'reviewed_on': '2026-10-03', 'approval': None, 'source': {'repository': 'tomassala8/ro-equipo', 'path': '20_METODO/METODO_ENTREGA_RO/plantillas/PL-P1-04_cadena-seo-local-checklists.md', 'sha256': '94b73575b60cb1adc006fc2931ab4874c618d9e380d528bc5d0e71496d5bebb6', 'last_local_git_change': '2026-09-11', 'declared_version': None, 'sections': ['Paso 1; paso 3; paso 4; notas de calidad']}, 'excerpt': {'steps': ['Comprobar intención de la consulta y posible canibalización con otra URL del sitio.', 'Revisar headings, title, meta, URL y canonical de la página.', 'Comprobar legibilidad y enlaces en móvil y escritorio.', 'Separar indexabilidad, presencia en sitemap y evidencia observada en Search Console.', 'Adjuntar URL, capturas y fecha del baseline de posiciones cuando exista.'], 'delivery_qa': 'Checklist con prueba por comprobación y faltantes explícitos; no convertir posiciones en ventas.'}, 'excerpt_sha256': '069b327f5ef53e4d609ba18a1825b608521b81f0ffc2e7083b3c026871de2d64', 'limitations': ['La plantilla distingue ítems literales y borradores por validar; no aprobar toda la cadena.', 'Excluir objetivos top-1, relojes, umbrales y cuotas de keywords como obligaciones vigentes.'], 'classification': 'generic_curated_operational', 'source_is_authority': False}, {'id': 'account_handoff', 'title': 'Account: revisión de continuidad en traspaso', 'discipline': 'account', 'role_tags': ['account', 'operaciones'], 'service_keys': ['seo', 'publicidad', 'crm_ghl', 'web', 'mantenimiento', 'redes', 'social_media'], 'state': 'propuesta', 'version': '134.1.0', 'reviewed_on': '2026-10-03', 'approval': None, 'source': {'repository': 'tomassala8/ro-equipo', 'path': '20_METODO/METODO_ENTREGA_RO/plantillas/PL-TR-01_checklist-handoff.md', 'sha256': '0b1b92c359d7d99dcdf7618041f634083a5bdd678a9ad1fc11439c30f51e6b83', 'last_local_git_change': '2026-09-11', 'declared_version': None, 'sections': ['Plantilla §§1–4, 6 y 8; notas de calidad']}, 'excerpt': {'steps': ['Comprobar actualización del brief y del registro de errores.', 'Conservar señales e incidencias actuales durante el traspaso.', 'Documentar herramientas exactas y tareas en curso con estado y fecha.', 'Dejar por escrito lo explicado en la reunión interna.', 'Registrar huecos detectados por el entrante y el artefacto que necesita completarse.'], 'delivery_qa': 'Brief, incidencias, detalles técnicos y pendientes trazables; responsable y revisión se resuelven desde la matriz actual.'}, 'excerpt_sha256': 'aa5ba637a8c1bf060d8675da274c4e98aae91884a97935c28b66809d1915e8c9', 'limitations': ['Excluir ejemplos de clientes, contactos, sensibilidad personal y rutas de acceso.', 'No adoptar nombres de julio, aprobación por silencio, tiempos ni envíos automáticos.'], 'classification': 'generic_curated_operational', 'source_is_authority': False}, {'id': 'content_qc', 'title': 'SEO: control de contenido antes de entrega', 'discipline': 'seo', 'role_tags': ['seo'], 'service_keys': ['seo'], 'state': 'propuesta', 'version': '134.1.0', 'reviewed_on': '2026-10-03', 'approval': None, 'source': {'repository': 'tomassala8/ro-equipo', 'path': '20_METODO/METODO_ENTREGA_RO/plantillas/PL-P1-12_qc-contenido-checklist.md', 'sha256': '3389e9754450684f9cb5709c6cd8ce16b3a176b844d7c7a87c2feff49d5440c2', 'last_local_git_change': '2026-09-11', 'declared_version': None, 'sections': ['Plantilla §§A,C,D; notas de calidad']}, 'excerpt': {'steps': ['Relacionar cada cifra, fecha, modelo o norma de la pieza con fuente oficial y fecha de consulta.', 'Marcar no aplicable cuando no existan datos fiscales.', 'Revisar voz e idioma contra el material autorizado de la tarea.', 'Comprobar enlaces y canal de destino.', 'Si falla la revisión, indicar la casilla concreta y preparar la corrección.'], 'delivery_qa': 'Veredicto con evidencia y pendientes antes de entrega; casilla sin fuente queda sin marcar.'}, 'excerpt_sha256': '439eccd000b59bad035a17f1f669f45df6d20a1c0230d918059ccf556b06d63a', 'limitations': ['No copiar datos fiscales de los ejemplos como actuales ni automatizar publicación o escalado.', 'No adoptar nombres, duración, segunda firma o reglas legales del texto como normativa validada.'], 'classification': 'generic_curated_operational', 'source_is_authority': False}]}

ROLES = {
    'paid': {'trafficker', 'jefa_publicidad', 'account', 'operaciones', 'proyectos', 'direccion', 'tecnico_altas'},
    'crm': {'especialista_ghl', 'jefa_crm', 'account', 'operaciones', 'proyectos', 'direccion', 'tecnico_altas'},
    'seo': {'seo', 'ficha_google', 'web', 'jefa_seo', 'account', 'operaciones', 'proyectos', 'direccion', 'tecnico_altas'},
}
DISCIPLINAS = {
    'paid': ('publicidad', 'captacion'),
    'crm': ('crm_ghl', 'salud-crm'),
    'seo': ('seo', 'seo-web'),
}


def fuente_integra(raiz, source):
    # Rutas constantes del catálogo curado; el navegador nunca decide rutas.
    try:
        raiz = Path(raiz).resolve(strict=True)
        p = raiz / source['path']
        if p.is_symlink() or not p.resolve(strict=True).is_relative_to(raiz):
            return False
        if not p.is_file() or p.stat().st_size > 256 * 1024:
            return False
        with p.open('rb') as archivo:
            data = archivo.read(256 * 1024 + 1)
        return len(data) <= 256 * 1024 and hashlib.sha256(data).hexdigest() == source['sha256']
    except (OSError, ValueError, KeyError):
        return False


def ampliar(payload, *, fila, real, vista, S, P, raiz=None, activo=None):
    """Amplía un DTO autorizado; sigue verificando permiso/servicio antes de mostrar propuestas."""
    bloque = {'version': VERSION, 'estado': 'propuesta', 'autoridad': 'datos_de_referencia',
              'ejecucion': 'preparar_y_revisar', 'aprobacion_comercial': False,
              'binding': {'tarea_id': str(fila.get('id') or ''), 'persona_id': fila.get('persona_id'), 'cliente_id': fila.get('cli')},
              'opciones': [], 'seleccion_automatica': False, 'cobertura': 'no_disponible',
              'aviso': 'No hay checklist propuesta disponible con evidencia y permisos actuales.'}
    salida = {**payload, 'procedimientos_ia': bloque}
    cid = fila.get('cli')
    canonicas = {p['id']: p for p in S.E.crudo.get('personas') or [] if isinstance(p.get('id'), str)}
    if any(p.get('id') not in canonicas or canonicas[p['id']].get('estado') == 'baja' for p in (real, vista)):
        return salida
    if fila.get('persona_id') not in canonicas:
        return salida
    clientes = [c for c in S.E.crudo.get('clientes') or [] if c.get('id') == cid]
    if len(clientes) != 1:
        return salida
    if activo is None:
        from fuentes_verdad import clientes_activos as ACT
        activo = ACT.es_activo_id
    try:
        if not activo(cid):
            return salida
        for p in (real, vista):
            if not S.ve_alguno(p, ['mi-trabajo']) or not P.ver(p, {'tipo': 'cliente_detalle', 'cliente_id': cid}, P.contexto(p, S.E.crudo))['ok']:
                return salida
    except Exception:
        return salida
    cliente = clientes[0]
    raiz = raiz or os.environ.get('RO_PROCEDIMIENTOS_RAIZ') or _cfg.HOME / 'RO_EQUIPO'
    if not all(fuente_integra(raiz, guard) for guard in CATALOGO['precedence_guards']):
        bloque['aviso'] = 'Las fuentes de referencia cambiaron o no están disponibles; confirmar la versión antes de proponer checklist.'
        return salida
    hay_servicio = any(cliente.get('servicios', {}).get(k) == 'sí' for k in ('seo', 'publicidad', 'crm_ghl', 'web', 'mantenimiento', 'redes', 'social_media'))
    def puede(r):
        if r['discipline'] == 'account':
            return hay_servicio and all(set(p.get('puestos') or []) & {'account', 'operaciones', 'proyectos', 'direccion', 'tecnico_altas'}
                                       and S.ve_alguno(p, ['ficha']) for p in (real, vista))
        servicio, modulo = DISCIPLINAS[r['discipline']]
        return cliente.get('servicios', {}).get(servicio) == 'sí' and all(set(p.get('puestos') or []) & ROLES[r['discipline']] and S.ve_alguno(p, [modulo]) for p in (real, vista))
    for r in CATALOGO['resources']:
        if not puede(r) or not fuente_integra(raiz, r['source']):
            continue
        excerpt = r['excerpt']
        digest = hashlib.sha256(json.dumps(excerpt, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()
        if digest != r['excerpt_sha256']:
            continue
        bloque['opciones'].append({'id': r['id'], 'titulo': r['title'], 'disciplina': r['discipline'], 'estado': 'propuesta',
            'version': VERSION, 'fuente': r['source']['path'].split('/')[-1], 'secciones': r['source']['sections'],
            'fuente_sha256': r['source']['sha256'], 'fecha_fuente': r['source']['last_local_git_change'],
            'extracto_sha256': digest, 'pasos': list(excerpt['steps']), 'revision_entrega': excerpt['delivery_qa'],
            'limites': list(r['limitations']), 'autoridad': 'datos_de_referencia', 'ejecucion': 'preparar_y_revisar',
            'conectores_necesarios': {'paid': ['ClickUp', 'Meta Ads', 'GoHighLevel'], 'crm': ['ClickUp', 'GoHighLevel'],
                'seo': ['ClickUp', 'Google Search Console'], 'account': ['ClickUp', 'Google Drive']}[r['discipline']]})
    bloque['cobertura'] = 'propuestas_curadas' if bloque['opciones'] else 'no_disponible'
    bloque['aviso'] = 'Checklists sugeridas, versión 134.1.0: selecciona una. No ratifican SOPs ni reglas comerciales; no conceden permisos ni ejecutan acciones.' if bloque['opciones'] else bloque['aviso']
    return salida

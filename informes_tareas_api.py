"""Evidencia de finalización para informes. Sólo lectura, nunca afirma aceptación."""
import re
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo
from fuentes_produccion.estados_catalogo import resolver_estado


def preparar(cliente_id, desde, hasta, tareas_autorizadas, cache, catalogo):
    inicio, fin = date.fromisoformat(desde), date.fromisoformat(hasta)
    if inicio > fin or (fin - inicio).days > 366:
        raise ValueError('El periodo debe abarcar como máximo un año.')
    seguras = {str(t['id']): t for t in tareas_autorizadas if isinstance(t, dict)
               and t.get('id') and t.get('cli') == cliente_id}
    grupos = {}
    for t in cache.get('tareas') or []:
        if isinstance(t, dict) and t.get('id'):
            grupos.setdefault(str(t['id']), []).append(t)
    filas = []
    for tid, t in seguras.items():
        candidatos = grupos.get(tid, [])
        if len(candidatos) != 1:
            continue
        original = candidatos[0]
        if not resolver_estado(original, catalogo)['final_flujo']:
            continue
        try:
            valor = original.get('cerrada')
            if isinstance(valor, bool) or not re.fullmatch(r'\d{10,16}', str(valor)):
                continue
            fecha = datetime.fromtimestamp(int(valor) / 1000, timezone.utc).astimezone(ZoneInfo('Europe/Madrid')).date()
        except (ValueError, TypeError, OverflowError, OSError):
            continue
        if not inicio <= fecha <= fin:
            continue
        # Nombre ya saneado por la fuente pública y recortado por los permisos originales.
        filas.append({'id': tid, 'cliente_id': cliente_id, 'nombre': t.get('tarea') or 'Tarea registrada',
                      'fecha_ejecucion': fecha.isoformat(),
                      'fuente_evidencia': 'ClickUp: fecha de cierre y estado terminal contrastado con su lista',
                      'tipo_evidencia': 'finalizacion_flujo', 'url': None})
    return {'cliente_id': cliente_id, 'desde': desde, 'hasta': hasta, 'fuente': 'Copia local de ClickUp',
            'fecha_lectura': (cache.get('meta') or {}).get('generado'), 'cobertura': 'parcial',
            'nota_cobertura': 'Sólo tareas autorizadas con cierre fechado y catálogo válido. No confirma aceptación ni todo el histórico.',
            'tareas': sorted(filas, key=lambda x: (x['fecha_ejecucion'], x['id']))}


def enganchar(Manejador, S):
    anterior = Manejador._api_get

    def get(self, ruta, q, real, persona):
        if ruta != '/api/informes/tareas_ejecutadas':
            return anterior(self, ruta, q, real, persona)
        if S.E.nucleo_bloqueado:
            return self.responder(503, {'error': 'La fuente de permisos y clientes no está disponible.'})
        cid = (q.get('cliente_id') or [''])[0]
        if not S.ACT.es_activo_id(cid):
            return self.responder(404, {'error': 'Cliente activo no encontrado.'})
        for p in (real, persona):
            cp = S.P.contexto(p, S.E.crudo)
            if not S.P.ver(p, {'tipo': 'cliente_detalle', 'cliente_id': cid}, cp)['ok']:
                return self.responder(403, {'error': 'No puedes consultar las tareas de este cliente.'})
        doc = S.modulo_recortado(real, persona, S.P.contexto(persona, S.E.crudo), 'mi_trabajo/mi_trabajo')
        if not isinstance(doc, dict):
            return self.responder(403, {'error': 'No tienes acceso a esta fuente de tareas.'})
        try:
            # No se publican nombres, descripciones ni vínculos de esta caché privada.
            cache, _ = S.leer_json_bueno(S.AQUI / 'fuentes_produccion/_privado/_cache/tareas.json')
            catalogo, _ = S.leer_json_bueno(S.AQUI / 'fuentes_produccion/_privado/_cache/estados_listas.json')
            salida = preparar(cid, (q.get('desde') or [''])[0], (q.get('hasta') or [''])[0],
                              doc.get('tareas') or [], cache, catalogo)
        except (ValueError, TypeError):
            return self.responder(400, {'error': 'Selecciona un periodo válido para el informe.'})
        except Exception:
            return self.responder(503, {'error': 'La evidencia de tareas no está disponible en esta copia local.'})
        return self.responder(200, salida)

    Manejador._api_get = get

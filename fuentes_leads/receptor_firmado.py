"""Validación pura de entrega WPForms. Sin IO, HTTP, reloj implícito o persistencia.

validar_entrega(bodybytes, cabeceras, catalogo, ahora_explicit) -> {ok,codigo,dto}
Catálogo privado por key_id: secret, actor_id, cliente_id, source_id,
formularios {form_id: {fuente_key, privado_campos:[nombres]}}. Ningún secreto sale en DTO.
La persistencia/dedup y el ACK son responsabilidad del caller, DESPUÉS de validar.
"""
import hashlib
import hmac
import json
import re
from datetime import datetime, timezone
from uuid import UUID

MAX_BYTES = 65536
VENTANA_SEGUNDOS = 300
_BODY_KEYS = {'schema_version', 'event', 'event_id', 'source_id', 'cliente_id',
              'form_id', 'entry_id', 'occurred_at', 'private_fields'}
_ID = re.compile(r'^[a-zA-Z0-9_-]{1,100}$')
_FIELD = re.compile(r'^[a-z][a-z0-9_]{0,39}$')
_PROHIBIDOS = re.compile(r'password|passwd|contrase[nñ]a|secret|token|api.?key|authorization|cookie|credential', re.I)
_VALOR_SECRETO = re.compile(r'\bBearer\s+\S+|\bsk-[A-Za-z0-9_-]{16,}|[?&](?:token|api_key|secret)=', re.I)
_RAW = {'raw', 'raw_post', 'post', 'request', 'headers'}
_HEADERS = ('x-ro-key-id', 'x-ro-timestamp', 'x-ro-signature', 'x-ro-event-id')


def _rechazar(codigo):
    return {'ok': False, 'codigo': codigo, 'dto': None}


def _objeto(pares):
    resultado = {}
    for clave, valor in pares:
        if clave in resultado:
            raise ValueError('duplicate_key')
        resultado[clave] = valor
    return resultado


def _constante(_):
    raise ValueError('non_finite_json')


def _id(v):
    return isinstance(v, str) and _ID.fullmatch(v) is not None


def validar_entrega(bodybytes, cabeceras, catalogo, ahora_explicit):
    """Firma PHP v1: hash_hmac('sha256', timestamp . '.' . payload, secret).

    Ahora es Unix int explícito. Firma se calcula sobre bytes originales, jamás
    JSON reserializado. Timestamp limita antigüedad de petición, no del lead.
    No puede impedir repetición dentro de ventana sin archivo duradero externo.
    """
    if isinstance(ahora_explicit, bool) or not isinstance(ahora_explicit, int):
        return _rechazar('reloj_invalido')
    try:
        received_at = datetime.fromtimestamp(ahora_explicit, timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    except (ValueError, OSError, OverflowError):
        return _rechazar('reloj_invalido')
    if not isinstance(bodybytes, bytes) or not 0 < len(bodybytes) <= MAX_BYTES:
        return _rechazar('tamano_o_tipo_invalido')
    if not isinstance(cabeceras, dict) or not isinstance(catalogo, dict):
        return _rechazar('cabeceras_invalidas')
    headers = {}
    for nombre, valor in cabeceras.items():
        if not isinstance(nombre, str) or not isinstance(valor, str):
            return _rechazar('cabeceras_invalidas')
        clave = nombre.lower()
        if clave in headers or '\r' in valor or '\n' in valor:
            return _rechazar('cabeceras_invalidas')
        headers[clave] = valor
    if any(k not in headers for k in _HEADERS):
        return _rechazar('cabeceras_invalidas')
    kid = headers['x-ro-key-id']
    if not re.fullmatch(r'[a-zA-Z0-9_-]{1,64}', kid):
        return _rechazar('autorizacion_denegada')
    cfg = catalogo.get(kid)
    if not isinstance(cfg, dict):
        return _rechazar('autorizacion_denegada')
    secret = cfg.get('secret')
    if not isinstance(secret, str) or len(secret) < 32:
        return _rechazar('configuracion_invalida')
    stamp = headers['x-ro-timestamp']
    if not re.fullmatch(r'[0-9]{1,19}', stamp):
        return _rechazar('timestamp_invalido')
    if abs(int(stamp) - ahora_explicit) > VENTANA_SEGUNDOS:
        return _rechazar('timestamp_fuera_ventana')
    signature = headers['x-ro-signature']
    if not re.fullmatch(r'v1=[0-9a-f]{64}', signature):
        return _rechazar('firma_invalida')
    try:
        expected = hmac.new(secret.encode('utf-8'), stamp.encode('ascii') + b'.' + bodybytes,
                            hashlib.sha256).hexdigest()
    except UnicodeEncodeError:
        return _rechazar('configuracion_invalida')
    if not hmac.compare_digest(signature[3:], expected):
        return _rechazar('firma_invalida')
    try:
        event = json.loads(bodybytes.decode('utf-8'), object_pairs_hook=_objeto,
                           parse_constant=_constante)
    except (ValueError, UnicodeDecodeError, RecursionError):
        return _rechazar('json_invalido')
    if not isinstance(event, dict) or set(event) != _BODY_KEYS:
        return _rechazar('esquema_invalido')
    if type(event['schema_version']) is not int or event['schema_version'] != 1:
        return _rechazar('esquema_invalido')
    if event['event'] != 'form_submission_accepted':
        return _rechazar('evento_invalido')
    event_id = event['event_id']
    if not isinstance(event_id, str):
        return _rechazar('identidad_invalida')
    try:
        uuid = UUID(event_id)
    except (ValueError, AttributeError):
        return _rechazar('identidad_invalida')
    if str(uuid) != event_id or uuid.version != 4 or not hmac.compare_digest(event_id, headers['x-ro-event-id']):
        return _rechazar('identidad_invalida')
    # Alcance procede de servidor, no lo escoge quien rellena el formulario.
    for k in ('cliente_id', 'source_id', 'actor_id'):
        if not _id(cfg.get(k)):
            return _rechazar('configuracion_invalida')
    if event['cliente_id'] != cfg['cliente_id'] or event['source_id'] != cfg['source_id']:
        return _rechazar('alcance_no_autorizado')
    form = event['form_id']
    if type(form) is not int or form <= 0:
        return _rechazar('formulario_no_autorizado')
    forms = cfg.get('formularios')
    if not isinstance(forms, dict):
        return _rechazar('configuracion_invalida')
    form_cfg = forms.get(form, forms.get(str(form)))
    if not isinstance(form_cfg, dict):
        return _rechazar('formulario_no_autorizado')
    fuente_key = form_cfg.get('fuente_key')
    if not _id(fuente_key):
        return _rechazar('configuracion_invalida')
    allowed = form_cfg.get('privado_campos')
    if not isinstance(allowed, list) or any(not isinstance(k, str) or not _FIELD.fullmatch(k) or _PROHIBIDOS.search(k) or k in _RAW for k in allowed):
        return _rechazar('configuracion_invalida')
    entry = event['entry_id']
    if entry is not None and (type(entry) is not int or entry <= 0):
        return _rechazar('identidad_invalida')
    fields = event['private_fields']
    # PHP array() vacío se serializa como []: permitido SOLO vacío y normalizado.
    if fields == []:
        fields = {}
    if not isinstance(fields, dict) or set(fields) - set(allowed):
        return _rechazar('campo_privado_no_autorizado')
    for nombre, valor in fields.items():
        if not isinstance(valor, str) or _VALOR_SECRETO.search(valor):
            return _rechazar('campo_privado_invalido')
        try:
            if len(valor.encode('utf-8')) > 2048:
                return _rechazar('campo_privado_invalido')
        except UnicodeEncodeError:
            return _rechazar('campo_privado_invalido')
    if len(json.dumps(fields, ensure_ascii=False, separators=(',', ':')).encode('utf-8')) > 16384:
        return _rechazar('campos_privados_demasiado_grandes')
    occurred = event['occurred_at']
    if not isinstance(occurred, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z', occurred):
        return _rechazar('fecha_evento_invalida')
    try:
        clock = datetime.strptime(occurred, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
    except ValueError:
        return _rechazar('fecha_evento_invalida')
    if clock.timestamp() > ahora_explicit + VENTANA_SEGUNDOS:
        return _rechazar('fecha_evento_futura')
    # Hash técnico estable, no teléfono/email. Lite identifica envío, no persona.
    identity = '{}:{}:{}:{}'.format(cfg['cliente_id'], cfg['source_id'], form, entry if entry is not None else event_id)
    lead_id = 'wp_' + hashlib.sha256(identity.encode('utf-8')).hexdigest()
    return {'ok': True, 'codigo': 'validado_no_persistido', 'dto': {
        'fuente_key': fuente_key, 'actor_id': cfg['actor_id'],
        'evento': {'event_id': event_id, 'lead_id': lead_id, 'etapa': 'recibido',
                   'fecha': occurred, 'meta_privados': dict(fields)},
        'metadata': {'cliente_id': cfg['cliente_id'], 'source_id': cfg['source_id'],
                     'form_id': form, 'entry_id': entry, 'received_at': received_at,
                     'stage_semantics': 'envio_aceptado_no_cualificacion_comercial',
                     'event_time_authority': 'origen_firmado_no_verificacion_independiente'}}}

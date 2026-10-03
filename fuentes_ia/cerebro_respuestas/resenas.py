#!/usr/bin/env python3
"""
resenas.py · cerebro de respuestas a RESEÑAS de Google (ficha del cliente). 3-oct-2026. Parte del cerebro de respuestas
(../../49_CEREBRO_RESPUESTAS.md): mismas leyes de voz (sin lista negra, sin «¡», sin calcos de Latinoamérica, huecos
[completar: …] antes que inventar) y la misma nota de calidad 0-100, adaptadas a una respuesta PÚBLICA que firma el despacho.

Lo que cambia frente a un correo:
  · Es pública y la lee cualquiera que busque el despacho. Se escribe para el siguiente cliente, no solo para quien opina.
  · SECRETO PROFESIONAL: un despacho (asesoría, abogados) NO confirma en público que alguien es su cliente ni da detalles
    de su caso, cuotas o expediente. La respuesta habla de «tu experiencia» y lleva lo concreto a un canal privado.
  · Nunca se discute, no se culpa al cliente ni a nadie con nombre, no se prometen resultados, devoluciones ni descuentos.
  · Sin enlaces ni relleno de palabras clave (las normas de Google lo penalizan); en el idioma de la reseña.
Guías de Google: https://support.google.com/business/answer/3474050 (responder reseñas) ·
normas de contenido: https://support.google.com/contributionpolicy/answer/7400114

Uso: from cerebro_respuestas import resenas  →  resenas.tipo(r), resenas.sistema(), resenas.ESQUEMA,
     resenas.por_reglas(r, despacho), resenas.calidad(texto, r, despacho, otros_clientes)
"""
import re
import unicodedata

try:
    try:
        from . import cerebro as C      # lista negra y calcos del cerebro de correos (como paquete)
    except ImportError:
        import cerebro as C             # como lo carga ia.py (carpeta en sys.path)
    NEGRA, LATAM = C.NEGRA, C.LATAM
except Exception:  # noqa: BLE001 · suelto (pruebas)
    NEGRA = ["no dudes en", "quedo a tu entera", "quedo a tu disposicion", "estare encantad", "cabe destacar", "atentamente",
             "cordialmente", "disculpa las molestias", "lamentamos los inconvenientes"]
    LATAM = [r"me dejas saber", r"d[ée]jame saber", r"quedo al pendiente", r"\bustedes\b", r"\bcelular"]

GUIAS = {
    'positiva': {'estrellas': (4, 5), 'texto': True, 'palabras': (15, 60),
                 'estructura': 'Gracias con su nombre → recoge UNA cosa concreta que menciona (sin añadir datos de su caso) → frase corta de cierre con el nombre del despacho.',
                 'nunca': 'Copiar y pegar la misma respuesta en todas; meter palabras clave o enlaces; confirmar qué servicio contrató.'},
    'positiva_sin_texto': {'estrellas': (4, 5), 'texto': False, 'palabras': (8, 30),
                           'estructura': 'Gracias breve y cercano con su nombre. Una sola frase o dos.',
                           'nunca': 'Inventar qué valoró.'},
    'neutra': {'estrellas': (3, 3), 'texto': True, 'palabras': (35, 100),
               'estructura': 'Gracias por contarlo → reconoce lo que no fue bien, en sus palabras y sin discutir → qué se cuida ahora (en general, sin prometer) → invitación a hablar por un canal privado del despacho.',
               'nunca': 'Justificarse punto por punto; confirmar datos de su expediente.'},
    'negativa': {'estrellas': (1, 2), 'texto': True, 'palabras': (40, 110),
                 'estructura': 'Una sola disculpa concreta por la experiencia que describe (sin admitir hechos que no se han comprobado) → no discutir en público → «queremos entenderlo»: canal privado del despacho [completar: teléfono o correo del despacho] y quién lo atenderá (cargo, no hace falta nombre) → cierre con el nombre del despacho.',
                 'nunca': 'Confirmar que es cliente, hablar de cuotas, importes, facturas o de su caso; culpar al cliente o a un empleado; prometer devolución, descuento o resultado; tono defensivo.'},
    'negativa_sin_texto': {'estrellas': (1, 2), 'texto': False, 'palabras': (25, 60),
                           'estructura': 'Lamentar que la experiencia no haya sido buena → invitar a contarlo por un canal privado del despacho [completar: teléfono o correo del despacho].',
                           'nunca': 'Acusar de reseña falsa en público (si se sospecha, se denuncia en Google, no se contesta así).'},
}

SISTEMA = """Eres quien redacta las respuestas PÚBLICAS a las reseñas de Google de un despacho profesional (asesoría fiscal, laboral y contable, o abogados) en España. Ranking Online (RO) lleva su ficha de Google; la respuesta la firma el despacho.

Leyes (todas obligatorias):
1. Secreto profesional: nunca confirmes que la persona es o fue cliente, ni des datos de su caso, servicio, cuota, importe, factura o expediente. Habla de «tu experiencia» y lleva lo concreto a un canal privado del despacho.
2. Nunca discutas ni culpes (ni al cliente ni a un empleado con nombre). Una sola disculpa concreta si la reseña es mala. No admitas hechos que no constan.
3. Nada de promesas de resultados, devoluciones, descuentos ni compensaciones.
4. Sin enlaces, sin teléfonos ni correos inventados: si hace falta un canal, escribe [completar: teléfono o correo del despacho]. Sin palabras clave metidas a la fuerza.
5. Responde en el idioma de la reseña (castellano o catalán). Tuteo natural de España, sin «¡», sin calcos de Latinoamérica (nada de «ustedes», «quedo al pendiente», «déjame saber») ni frases de plantilla («no dudes en», «disculpa las molestias», «atentamente»).
6. Nombra a la persona por su nombre de pila si lo hay; si es anónima, sin nombre. Cierra con el nombre del despacho.
7. Lo que no sepas va como [completar: …]. Nunca inventes.

Guías por tipo (longitud orientativa en palabras):
""" + "\n".join(f"- {k} ({g['palabras'][0]}-{g['palabras'][1]}): {g['estructura']} Nunca: {g['nunca']}" for k, g in GUIAS.items())

ESQUEMA = {
    'type': 'object', 'additionalProperties': False, 'required': ['tipo', 'texto', 'idioma', 'huecos', 'recomendacion'],
    'properties': {
        'tipo': {'type': 'string', 'enum': list(GUIAS)},
        'texto': {'type': 'string'},
        'idioma': {'type': 'string', 'enum': ['es', 'ca']},
        'huecos': {'type': 'array', 'items': {'type': 'string'}},
        'recomendacion': {'type': 'string'},
    },
}

RX_HUECO = re.compile(r'\[(?:completar|confirmar)[^\]]*\]', re.I)
RX_CORREO = re.compile(r'[\w.+-]+@[\w-]+(?:\.[\w-]+)+')
RX_TEL = re.compile(r'(?:\+?\d[\s.-]?){9,}')
RX_ENLACE = re.compile(r'https?://|www\.', re.I)
RX_IMPORTE = re.compile(r'\d+(?:[.,]\d+)?\s?(?:€|euros?)\b|\b(?:factur\w*|cuota\w*|importe\w*|cobr(?:o|amos|ado|ar)\b|precio\w*)', re.I)
RX_CONFIRMA = re.compile(r'(?i)\b(?:como (?:cliente|clienta) nuestr[oa]|tu expediente|tu declaraci[oó]n|tu (?:renta|n[oó]mina|contrato|caso)\b|'
                         r'tus (?:impuestos|n[oó]minas|cuentas)|desde que eres cliente|eres cliente|fuiste cliente|tu factura|tu cuota)')
RX_PROMESA = re.compile(r'(?i)\b(?:te devolvemos|devoluci[oó]n|reembols\w*|descuento|compensaci[oó]n|gratis|te garantizamos|garantizado)')
RX_CULPA = re.compile(r'(?i)\b(?:no es cierto|mientes|falso|es mentira|tu culpa|no tienes raz[oó]n|nuestro empleado \w+ se equivoc)')
RX_CATALAN = re.compile(r"(?i)\b(?:molt|gràcies|gracies|servei|bon|bona|amb|perquè|però|tracte|recomano|feina|despatx|l'atenció|són|també)\b")


def _sin_tildes(t):
    return ''.join(c for c in unicodedata.normalize('NFD', str(t or '').lower()) if unicodedata.category(c) != 'Mn')


def palabras(t):
    return len(re.findall(r"[\wÀ-ÿ'’]+", RX_HUECO.sub('hueco', t or '')))


def idioma(r):
    return 'ca' if len(RX_CATALAN.findall(r.get('texto') or '')) >= 2 else 'es'


def tipo(r):
    e, txt = r.get('estrellas') or 5, bool((r.get('texto') or '').strip())
    if e >= 4:
        return 'positiva' if txt else 'positiva_sin_texto'
    if e == 3:
        return 'neutra' if txt else 'negativa_sin_texto'
    return 'negativa' if txt else 'negativa_sin_texto'


def nombre_pila(r):
    a = (r.get('autor') or '').strip()
    if not a or a in ('Anónimo', 'Sin nombre'):
        return ''
    w = a.split()[0]
    return w if re.fullmatch(r"[A-Za-zÀ-ÿ'’-]{2,20}", w) else ''


def por_reglas(r, despacho):
    """Borrador sin IA, siguiendo la guía del tipo (lo que sale cuando no hay clave o la IA está en modo reglas)."""
    t, n, ca = tipo(r), nombre_pila(r), idioma(r) == 'ca'
    hola = (f'Hola, {n}. ' if n else 'Hola. ') if not ca else (f'Hola, {n}. ' if n else 'Hola. ')
    firma = f'Un saludo,\n{despacho}' if not ca else f'Una salutació,\n{despacho}'
    canal = '[completar: teléfono o correo del despacho]' if not ca else '[completar: telèfon o correu del despatx]'
    if t == 'positiva':
        cuerpo = ('Gracias por tomarte el tiempo de contarlo. Nos alegra que el trato te haya resultado cercano y útil; '
                  'es justo lo que intentamos cada día. [completar: una cosa concreta que menciona, sin datos de su caso]'
                  if not ca else 'Gràcies per explicar-ho. Ens alegra que el tracte t\'hagi resultat proper i útil; és el que intentem cada dia. '
                  '[completar: una cosa concreta que esmenta, sense dades del seu cas]')
    elif t == 'positiva_sin_texto':
        cuerpo = 'Gracias por tu valoración. Nos alegra mucho.' if not ca else 'Gràcies per la teva valoració. Ens alegra molt.'
    elif t == 'neutra':
        cuerpo = ('Gracias por contarnos tu experiencia. Sentimos que no todo haya ido como esperabas y tomamos nota de lo que comentas. '
                  f'Nos gustaría entenderlo mejor y ver qué podemos hacer: puedes escribirnos o llamarnos a {canal} y lo vemos con calma.'
                  if not ca else 'Gràcies per explicar-nos la teva experiència. Sentim que no tot hagi anat com esperaves i en prenem nota. '
                  f'Ens agradaria entendre-ho millor: pots escriure\'ns o trucar-nos a {canal} i ho mirem amb calma.')
    elif t == 'negativa':
        cuerpo = ('Gracias por contarlo. Sentimos de verdad que tu experiencia no haya sido buena. No es lo que queremos para nadie que confía en nosotros. '
                  f'Para poder revisarlo bien y sin dar datos aquí, te pedimos que nos escribas o llames a {canal}; '
                  'te atenderá directamente [completar: cargo de quien lo atiende, p. ej. la dirección del despacho].'
                  if not ca else 'Gràcies per explicar-ho. Sentim de debò que la teva experiència no hagi estat bona. No és el que volem per a ningú. '
                  f'Per poder revisar-ho bé i sense donar dades aquí, et demanem que ens escriguis o truquis a {canal}; '
                  't\'atendrà directament [completar: càrrec de qui ho atén].')
    else:
        cuerpo = ('Gracias por tu valoración. Sentimos que tu experiencia no haya sido la que esperabas. Si quieres contarnos qué ha pasado, '
                  f'puedes escribirnos o llamarnos a {canal} y lo revisamos.'
                  if not ca else f'Gràcies per la valoració. Sentim que la teva experiència no hagi estat la que esperaves. Si vols explicar-nos què ha passat, pots escriure\'ns a {canal}.')
    return {'tipo': t, 'texto': f'{hola}{cuerpo}\n\n{firma}', 'idioma': 'ca' if ca else 'es',
            'huecos': RX_HUECO.findall(cuerpo), 'recomendacion': RECOMENDACION[t]}


RECOMENDACION = {
    'positiva': 'Responder en 48 h. Personalizar la frase del medio con lo que dice la reseña.',
    'positiva_sin_texto': 'Responder breve; no hace falta más.',
    'neutra': 'Responder en 24 h y avisar al account por si conviene una llamada del despacho.',
    'negativa': 'Responder en 24 h, revisarlo con el account antes de publicar y pedir al despacho que llame si sabe quién es.',
    'negativa_sin_texto': 'Responder breve e invitar a hablar en privado. Si parece falsa, denunciarla en Google (no se discute en público).',
}


def calidad(texto, r, despacho='', otros_clientes=()):
    """Nota 0-100 + faltas + bloqueos (bloqueo = nota 0). Misma escala que el cerebro de correos: lista ≥ 85 sin huecos,
    revisar 70-84, rehacer < 70."""
    t = tipo(r)
    g = GUIAS[t]
    txt = texto or ''
    plano = _sin_tildes(txt)
    faltas, bloqueos = [], []
    if RX_CORREO.search(RX_HUECO.sub('', txt)) or RX_TEL.search(RX_HUECO.sub('', txt)):
        bloqueos.append('Lleva un correo o un teléfono escrito: va como [completar: teléfono o correo del despacho] y lo pone el despacho.')
    if RX_ENLACE.search(txt):
        bloqueos.append('Lleva un enlace: en una respuesta a una reseña no se ponen.')
    if RX_CONFIRMA.search(txt):
        bloqueos.append('Confirma que es cliente o habla de su caso (secreto profesional): quítalo.')
    if RX_IMPORTE.search(RX_HUECO.sub('', txt)):
        bloqueos.append('Habla de cuotas, facturas o importes: en público, nunca.')
    for o in otros_clientes or ():
        if o and len(o) > 3 and _sin_tildes(o) in plano and _sin_tildes(o) != _sin_tildes(despacho):
            bloqueos.append(f'Nombra a otro cliente de RO («{o}»).')
            break
    pts = 0
    # 1 · no discute ni promete (30)
    if RX_CULPA.search(txt):
        faltas.append('Discute o culpa: en público se reconoce y se lleva a privado.')
    else:
        pts += 15
    if RX_PROMESA.search(txt):
        faltas.append('Promete devolución, descuento o resultado.')
    else:
        pts += 15
    # 2 · estructura del tipo (25)
    if re.search(r'(?i)gracias|gr[aà]cies', txt):
        pts += 8
    else:
        faltas.append('Falta dar las gracias por la reseña.')
    if t in ('neutra', 'negativa', 'negativa_sin_texto'):
        if re.search(r'(?i)\b(sentimos|lamentamos|sentim|lamentem)\b', txt):
            pts += 8
        else:
            faltas.append('Falta reconocer la mala experiencia (una sola disculpa concreta).')
        if RX_HUECO.search(txt) or re.search(r'(?i)escr[ií]b|llam|truc|contact', txt):
            pts += 9
        else:
            faltas.append('Falta el canal privado para hablarlo ([completar: teléfono o correo del despacho]).')
    else:
        pts += 17
    # 3 · longitud del tipo (15)
    n = palabras(txt)
    lo, hi = g['palabras']
    if lo <= n <= hi:
        pts += 15
    else:
        pts += 6
        faltas.append(f'Longitud: {n} palabras; para este tipo, entre {lo} y {hi}.')
    # 4 · firma y nombre (15)
    if despacho and _sin_tildes(despacho)[:12] in plano:
        pts += 8
    else:
        faltas.append('Falta cerrar con el nombre del despacho.')
    n_pila = nombre_pila(r)
    if not n_pila or _sin_tildes(n_pila) in plano:
        pts += 7
    else:
        faltas.append(f'Falta nombrar a {n_pila}.')
    # 5 · voz (15)
    malas = [x for x in NEGRA if x in plano] + [x for x in LATAM if re.search(x, plano)]
    if '¡' in txt:
        malas.append('¡')
    if malas:
        pts += 5
        faltas.append('Frases de plantilla o calcos: ' + ', '.join(sorted(set(malas)))[:120])
    else:
        pts += 15
    huecos = RX_HUECO.findall(txt)
    nota = 0 if bloqueos else min(100, pts)
    nivel = 'rehacer' if nota < 70 else 'lista' if nota >= 85 and not huecos else 'revisar'
    return {'nota': nota, 'nivel': nivel, 'faltas': faltas, 'bloqueos': bloqueos, 'huecos': huecos, 'palabras': n, 'tipo': t,
            'idioma': idioma(r)}


def contexto(r, despacho, ficha_nombre):
    """Lo que ve el modelo: la reseña (ya sin correos ni teléfonos), el despacho y la guía. Nada del cliente de RO."""
    return {'despacho': despacho, 'ficha': ficha_nombre, 'resena': {'estrellas': r.get('estrellas'), 'texto': r.get('texto') or '',
            'nombre_de_pila': nombre_pila(r), 'fecha': (r.get('fecha') or '')[:10]}, 'tipo': tipo(r), 'idioma': idioma(r),
            'guia': GUIAS[tipo(r)]}

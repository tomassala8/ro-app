#!/usr/bin/env python3
"""partir_chat.py · N15 (2-oct) · auditoría de velocidad: el chat de Tomás era 1 MB en un solo fichero.

Parte lo que escribe generar_chat_equipo.py en:
  data/chat_equipo/p_<persona>.json          ÍNDICE ligero: sus canales (sin mensajes) con el último mensaje, las fechas y
                                             autores de los recientes (para «sin leer») y sus menciones. Lo sirve servir.py
                                             como siempre (solo_propio).
  data/chat_equipo/_privado/c_<canal>.json   los mensajes de cada canal (con sus hilos). Nunca se sirve en bloque: solo
                                             por /api/avisos/clickup (avisos.py), 50 mensajes por página y SOLO a quien es
                                             miembro de ese canal según su propio índice.

Sin red y sin llave. Se puede repetir: si un índice ya está partido, lo deja como está.
  python3 fuentes_chat_equipo/partir_chat.py
"""
import json
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
SAL_DEF = os.path.join(os.path.dirname(AQUI), 'data', 'chat_equipo')


def _hace_dias(gen, dias):
    from datetime import datetime, timedelta
    try:
        return (datetime.strptime(gen[:16], '%Y-%m-%d %H:%M') - timedelta(days=dias)).strftime('%Y-%m-%d %H:%M')
    except ValueError:
        return ''


def _escribir(ruta, doc):
    tmp = ruta + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(doc, f, ensure_ascii=False)
    os.replace(tmp, ruta)


def partir(sal=SAL_DEF):
    priv = os.path.join(sal, '_privado')
    os.makedirs(priv, exist_ok=True)
    canales, indices, ya = {}, 0, 0
    vivos = set()
    for f in sorted(os.listdir(sal)):
        if not (f.startswith('p_') and f.endswith('.json')):
            continue
        ruta = os.path.join(sal, f)
        doc = json.load(open(ruta, encoding='utf-8'))
        lista = doc.get('canales') or []
        if not any('mensajes' in c for c in lista):
            ya += 1
            vivos |= {c['id'] for c in lista}
            continue
        nuevos = []
        for c in lista:
            msgs = c.get('mensajes') or []
            vivos.add(c['id'])
            if c['id'] not in canales:
                canales[c['id']] = {'canal_id': c['id'], 'nombre': c.get('nombre'), 'generado': (doc.get('_meta') or {}).get('generado'),
                                    'mensajes': msgs}
            ult = msgs[-1] if msgs else None
            ligero = {k: v for k, v in c.items() if k != 'mensajes'}
            ligero['n_mensajes'] = len(msgs)
            # Para «sin leer» basta la fecha y el autor de cada mensaje de las dos últimas semanas (no el texto).
            gen = str((doc.get('_meta') or {}).get('generado') or '')
            corte = _hace_dias(gen, 14)
            ligero['recientes'] = [[m.get('fecha'), m.get('autor_pid')] for m in msgs if str(m.get('fecha') or '') >= corte]
            ligero['miembros'] = [{'nombre': g.get('nombre'), 'pid': g.get('pid')} for g in (c.get('miembros') or [])]
            ligero['ultimo_msg'] = ({'autor': ult.get('autor'), 'autor_pid': ult.get('autor_pid'), 'fecha': ult.get('fecha'),
                                     'texto': str(ult.get('texto') or '')[:90]} if ult else None)
            nuevos.append(ligero)
        doc['canales'] = nuevos
        doc.setdefault('_meta', {})['partido'] = 'índice ligero: los mensajes se piden por canal (50 por página)'
        _escribir(ruta, doc)
        indices += 1
    for cid, cdoc in canales.items():
        _escribir(os.path.join(priv, f'c_{cid}.json'), cdoc)
    # Canales que ya no están en ningún índice: fuera (no quedan mensajes sueltos de canales que nadie ve).
    quitados = 0
    for f in os.listdir(priv):
        if f.startswith('c_') and f.endswith('.json') and f[2:-5] not in vivos:
            os.remove(os.path.join(priv, f))
            quitados += 1
    return {'indices_partidos': indices, 'ya_partidos': ya, 'canales': len(canales), 'quitados': quitados}


if __name__ == '__main__':
    print(partir(sys.argv[1] if len(sys.argv) > 1 else SAL_DEF))

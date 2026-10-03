#!/usr/bin/env python3
"""ghl_totales.py · M6 Captación · cuántos contactos tiene cada subcuenta de GoHighLevel EN TODA SU HISTORIA. SOLO LECTURA.

Sirve para distinguir «integración rota» de «la subcuenta no se usa» (auditoría de cifras E-13: GAC tiene 1 contacto
en toda su historia y trabaja con otro CRM). Una llamada por subcuenta (/contacts/?limit=1 → meta.total).
El refresh token de GHL rota en cada uso: app.acceso() lo guarda en el llavero al momento (como app.py).
Salida: fuentes_captacion/ghl_totales.json (solo recuentos, ningún dato de contacto).
Uso:  python3 ghl_totales.py
"""
import json
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.expanduser('~/RO_HERRAMIENTAS/ghl_agencia'))
import app  # noqa: E402

AQUI = Path(__file__).resolve().parent
CAPTACION = AQUI.parent.parent / '20_FASE2_CAPTACION' / 'captacion.json'
SALIDA = AQUI / 'ghl_totales.json'


def main():
    cap = json.loads(CAPTACION.read_text())
    subs = {c['ghl_subcuenta']['id']: c['id'] for c in cap['clientes'] if c.get('ghl_subcuenta')}
    tk, est = app.acceso()
    co = est['companyId']
    out = {}
    for loc, cid in subs.items():
        try:
            lt = app.token_sub(tk, co, loc)
            r = app.get(lt, '/contacts/', locationId=loc, limit=1)
            out[cid] = {'sub_id': loc, 'contactos_total': (r.get('meta') or {}).get('total'), 'error': r.get('_msg')}
        except SystemExit as e:
            out[cid] = {'sub_id': loc, 'contactos_total': None, 'error': str(e)[:160]}
        print(f"  {cid}: {out[cid]['contactos_total']}")
    doc = {'generado': datetime.now().strftime('%Y-%m-%d %H:%M'), 'subcuentas': out}
    tmp = SALIDA.with_suffix('.tmp')
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=1))
    tmp.replace(SALIDA)
    print('Listo:', SALIDA)


if __name__ == '__main__':
    main()

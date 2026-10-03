#!/usr/bin/env python3
"""M13 · importa el histórico de la hoja «Informes mensuales» de Zoho Sheet (W5) a data/informes/historico.json.

Por API (llave de Zoho del llavero con ZohoSheet.dataAPI.READ, canjeada por Tomás el 2-oct; zh.acceso()):
  · Libro «CARTERA CLIENTES RO» (resource id fijo abajo). Se pide la LISTA de hojas (solo nombres) y se lee
    ÚNICAMENTE la hoja cuyo nombre normalizado es «informes mensuales» (en Zoho se llama «Informes mensuales », con un
    espacio al final; sheetid 22). Cualquier otra hoja, y en especial «Credenciales», se rechaza ANTES de llamar:
    no hay ninguna llamada que pueda leerla (ni rango, ni libro entero, ni exportación).
  · worksheet.content.get devuelve, por celda, el texto y el HIPERVÍNCULO («url»): así salen los enlaces reales a cada
    informe y a cada estadística, no solo el texto visible.
Formato de la hoja: fila 1 = el mes (no siempre sobre la primera columna del bloque); fila 2 = «Informe entregables · Informes estadísticas ·
informado a cliente · Enviado a cliente»; desde la fila 3, un cliente por fila. Casillas TRUE/FALSE.

Sin llave (o para probar con un CSV exportado a mano): python3 importar_hoja_w5.py <fichero.csv>
  columnas: cliente, mes, enlace_informe, enlace_estadisticas, informado_en_reunion, enviado
Uso normal:   python3 importar_hoja_w5.py --zoho            (y después: python3 generar_informes.py --ficheros)
Comprobar:    python3 importar_hoja_w5.py --zoho --probar   (solo cuenta filas y meses; no escribe)
"""
import csv
import importlib.util
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

AQUI = Path(__file__).resolve().parent
APP = AQUI.parent
sys.path.insert(0, str(APP / 'fuentes'))
from comun import escanear, escribir, leer, norm, sanear, tokens  # noqa: E402

SALIDA = APP / 'data/informes/historico.json'
ZH = Path.home() / 'RO_HERRAMIENTAS/zoho/zh.py'
LIBRO = 'h4owxade0a8fd840349be9d38b45d75ec0313'      # «CARTERA CLIENTES RO»
HOJA = 'informes mensuales'                          # nombre normalizado de la ÚNICA hoja que se lee
PROHIBIDAS = {'credenciales', 'credencial', 'contrasenas', 'passwords', 'accesos', 'claves'}
COLUMNAS = ['cliente', 'mes', 'enlace_informe', 'enlace_estadisticas', 'informado_en_reunion', 'enviado']
MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
SI = {'si', 'true', 'x', 'ok', 'yes', '1', 'verdadero', 'enviado', 'hecho'}
NO = {'no', 'false', '0', 'falso'}


def booleano(v):
    t = norm(v)
    return True if t in SI else False if t in NO else None


def enlace(celda):
    if not celda:
        return None
    u = celda.get('url') or (celda.get('content') if re.match(r'https?://', celda.get('content') or '') else None)
    return u.strip() if u else None


# ------------------------------------------------------------------ Zoho Sheet
def zoho():
    spec = importlib.util.spec_from_file_location('zh', ZH)
    zh = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(zh)
    tk = None
    for intento in range(4):  # Zoho limita los canjes de llave de acceso por minuto: se reintenta con espera
        try:
            tk, _ = zh.acceso()
            break
        except urllib.error.HTTPError:
            import time
            time.sleep(45)
    if not tk:
        sys.exit('Zoho no da llave de acceso ahora (cupo de canjes). Prueba en unos minutos.')

    def call(params):
        req = urllib.request.Request(f'https://sheet.zoho.eu/api/v2/{LIBRO}', data=urllib.parse.urlencode(params).encode(),
                                     headers={'Authorization': 'Zoho-oauthtoken ' + tk})
        try:
            return json.load(urllib.request.urlopen(req, timeout=60))
        except urllib.error.HTTPError as e:
            sys.exit(f'Zoho Sheet {e.code}: {e.read().decode()[:200]} (¿la llave tiene ZohoSheet.dataAPI.READ?)')

    hojas = call({'method': 'worksheet.list'}).get('worksheet_names', [])
    elegida = [x['worksheet_name'] for x in hojas if norm(x.get('worksheet_name')) == HOJA]
    if len(elegida) != 1:
        sys.exit(f'No encuentro una única hoja «Informes mensuales» en el libro (hay {len(elegida)}). No se lee nada.')
    nombre = elegida[0]
    if any(p in norm(nombre) for p in PROHIBIDAS):  # doble cierre: jamás «Credenciales»
        sys.exit('Hoja prohibida. No se lee nada.')
    # 1) tamaño usado de ESA hoja (una celda), 2) su rango completo con hipervínculos
    t = call({'method': 'worksheet.content.get', 'worksheet_name': nombre, 'start_row': 1, 'start_column': 1, 'end_row': 1, 'end_column': 1})
    filas, cols = t.get('used_row') or 0, t.get('used_column') or 0
    r = call({'method': 'worksheet.content.get', 'worksheet_name': nombre, 'start_row': 1, 'start_column': 1,
              'end_row': max(filas, 2), 'end_column': max(cols, 2)})
    rejilla = {}
    for f in r.get('range_details', []):
        for c in f.get('row_details', []):
            rejilla[(f['row_index'], c['column_index'])] = c
    return nombre, filas, cols, rejilla


PREFIJOS = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']


def mes_de(texto):
    t = norm(texto)
    for i, p in enumerate(PREFIJOS):          # por las tres primeras letras: aguanta «Septimebre»
        if re.match(rf'{p}', t) or re.search(rf'\b{p}', t):
            return i + 1
    return None


def leer_rejilla(rejilla, filas, cols):
    """La hoja no es regular (bloques de 4 a 7 columnas, la etiqueta del mes no siempre sobre la primera, «Septimebre»):
    cada bloque empieza en una columna «Informe entregables» de la fila 2 y sus columnas se reconocen por su cabecera."""
    cab = {c: norm((rejilla.get((2, c)) or {}).get('content')) for c in range(1, cols + 1)}
    inicios = [c for c in range(2, cols + 1) if cab[c].startswith('informe entregable')]
    etiquetas = sorted((c, mes_de((rejilla.get((1, c)) or {}).get('content'))) for c in range(2, cols + 1)
                       if mes_de((rejilla.get((1, c)) or {}).get('content')))
    bloques, anio, prev = [], 2025, None
    for i, ini in enumerate(inicios):
        fin = inicios[i + 1] - 1 if i + 1 < len(inicios) else cols
        m = next((mm for c, mm in etiquetas if ini <= c <= fin), None)
        if m is None and prev:
            m = prev % 12 + 1                   # bloque sin etiqueta: el mes siguiente al anterior
        if m is None:
            continue
        if prev and m < prev:
            anio += 1
        prev = m
        col = {'informe': ini}
        for c in range(ini + 1, fin + 1):
            if cab[c].startswith('informe') and 'estadistic' in cab[c]:
                col.setdefault('estad', c)
            elif cab[c].startswith('informado'):
                col.setdefault('informado', c)
            elif cab[c].startswith('enviado'):
                col.setdefault('enviado', c)
        bloques.append((f'{anio}-{m:02d}', col))
    out = []
    for f in range(3, filas + 1):
        nombre = ((rejilla.get((f, 1)) or {}).get('content') or '').strip()
        if not nombre:
            continue
        for mes, col in bloques:
            cel = {k: rejilla.get((f, c)) for k, c in col.items()}
            fila = {'cliente_hoja': sanear(nombre), 'mes': mes,
                    'enlace_informe': enlace(cel.get('informe')), 'enlace_estadisticas': enlace(cel.get('estad')),
                    'informado_en_reunion': booleano((cel.get('informado') or {}).get('content')),
                    'enviado': booleano((cel.get('enviado') or {}).get('content'))}
            if any(fila[k] is not None for k in ('enlace_informe', 'enlace_estadisticas', 'informado_en_reunion', 'enviado')):
                out.append(fila)
    return out, [m for m, _ in bloques]


# ------------------------------------------------------------------ CSV (plan B)
def leer_csv(ruta):
    with open(ruta, newline='', encoding='utf-8-sig') as f:
        lector = csv.reader(f)
        cab = [norm(c).replace(' ', '_') for c in next(lector)]
        idx = {c: (cab.index(c) if c in cab else i) for i, c in enumerate(COLUMNAS)}
        for r in lector:
            if any(r):
                v = {c: (r[idx[c]] if idx[c] < len(r) else '') for c in COLUMNAS}
                yield {'cliente_hoja': sanear(v['cliente']), 'mes': v['mes'], 'enlace_informe': v['enlace_informe'] or None,
                       'enlace_estadisticas': v['enlace_estadisticas'] or None,
                       'informado_en_reunion': booleano(v['informado_en_reunion']), 'enviado': booleano(v['enviado'])}


# ------------------------------------------------------------------ emparejar con los clientes de la app
def emparejar(filas):
    idx = (leer(APP / 'data/indice_clientes.json', {}) or {}).get('clientes', [])
    manual = {k: v for k, v in (leer(AQUI / 'emparejamiento_hoja.json', {}) or {}).items() if not k.startswith('_')}  # «-» = ninguno
    por_norm = {norm(c['nombre']): c['id'] for c in idx}
    sin = set()
    for f in filas:
        n = norm(f['cliente_hoja'])
        compacto = {norm(c['nombre']).replace(' ', ''): c['id'] for c in idx}
        cid = manual.get(f['cliente_hoja'].strip()) or por_norm.get(n) or compacto.get(n.replace(' ', ''))
        if not cid:
            tt = tokens(f['cliente_hoja']) | {w for w in n.split() if len(w) >= 3}
            cands = [c['id'] for c in idx if (tokens(c['nombre']) and tokens(c['nombre']) <= tt) or (n and n in norm(c['nombre']).split())
                     or (tokens(f['cliente_hoja']) and tokens(f['cliente_hoja']) <= tokens(c['nombre']))]
            cid = cands[0] if len(set(cands)) == 1 else None
        if cid == '-':
            cid, f['no_es_cliente'] = None, True
        f['cliente_id'] = cid
        f['cliente'] = next((c['nombre'] for c in idx if c['id'] == cid), f['cliente_hoja'])
        if not cid and not f.get('no_es_cliente'):
            sin.add(f['cliente_hoja'])
    return filas, sorted(sin)


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    if sys.argv[1] == '--reemparejar':  # sin llamar a Zoho: vuelve a casar los nombres de la última importación
        prev = leer(SALIDA) or sys.exit('No hay importación previa.')
        filas, meses, origen = prev['filas'], prev['meses'], prev['origen']
    elif sys.argv[1] == '--zoho':
        nombre, nf, nc, rejilla = zoho()
        filas, meses = leer_rejilla(rejilla, nf, nc)
        origen = f'Zoho Sheet por API · libro «CARTERA CLIENTES RO» · solo la hoja «{nombre.strip()}» (con hipervínculos)'
    else:
        filas, meses = list(leer_csv(sys.argv[1])), []
        meses = sorted({f['mes'] for f in filas})
        origen = f'CSV exportado a mano ({Path(sys.argv[1]).name})'
    filas, sin = emparejar(filas)
    salida = {'estado': 'importado', 'origen': origen, 'importado': datetime.now().strftime('%Y-%m-%d %H:%M'),
              'meses': meses, 'columnas': COLUMNAS, 'sin_emparejar': sin, 'filas': filas}
    con_enlace = sum(1 for f in filas if f['enlace_informe'] or f['enlace_estadisticas'])
    print(f'{len(filas)} filas cliente×mes · {len({f["cliente_hoja"] for f in filas})} clientes en la hoja · meses {meses[:1]}…{meses[-1:]} · '
          f'{con_enlace} con enlace · enviados {sum(1 for f in filas if f["enviado"])} · sin emparejar {len(sin)}: {sin[:12]}')
    if '--probar' in sys.argv:
        return
    hall = escanear(salida)
    if hall:
        sys.exit('Puerta de secretos: no se escribe.\n  ' + '\n  '.join(hall[:10]))
    escribir(SALIDA, salida)
    print(f'→ {SALIDA}. Ahora: python3 generar_informes.py --ficheros')


if __name__ == '__main__':
    main()

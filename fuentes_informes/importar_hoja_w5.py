#!/usr/bin/env python3
"""M13 · importa el histórico de la hoja «Informes mensuales» de Zoho Sheet (W5) a data/informes/historico.json.

Por API (llave de Zoho del llavero con ZohoSheet.dataAPI.READ, canjeada por Tomás el 2-oct; zh.acceso()):
  · Libro «CARTERA CLIENTES RO» (resource id fijo abajo). Se pide la LISTA de hojas (solo nombres) y se lee
    ÚNICAMENTE la hoja cuyo nombre normalizado es «informes mensuales» (en Zoho se llama «Informes mensuales », con un
    espacio al final; sheetid 22). Cualquier otra hoja, y en especial «Credenciales», se rechaza ANTES de llamar:
    no hay ninguna llamada que pueda leerla (ni rango, ni libro entero, ni exportación).
  · worksheet.content.get devuelve, por celda, el texto y el HIPERVÍNCULO («url»): así salen los enlaces reales a cada
    informe y a cada estadística, no solo el texto visible.
Formato de la hoja: fila 1 = el mes con año explícito (si falta, requiere --anio-confirmado YYYY) (no siempre sobre la primera columna del bloque); fila 2 = «Informe entregables · Informes estadísticas ·
informado a cliente · Enviado a cliente»; desde la fila 3, un cliente por fila. Casillas TRUE/FALSE.

Sin llave (o para probar con un CSV exportado a mano): python3 importar_hoja_w5.py <fichero.csv>
  columnas: cliente, mes, enlace_informe, enlace_estadisticas, informado_en_reunion, enviado
Uso normal:   python3 importar_hoja_w5.py --zoho            (y después: python3 generar_informes.py --ficheros)
Comprobar:    python3 importar_hoja_w5.py --zoho --probar   (solo cuenta filas y meses; no escribe)
"""
import argparse
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
import pathlib as _pl_l27, sys as _sys_l27  # L-27: rutas del Mac por config.py
if str(_pl_l27.Path(__file__).resolve().parents[1]) not in _sys_l27.path:
    _sys_l27.path.append(str(_pl_l27.Path(__file__).resolve().parents[1]))
import config as _cfg  # noqa: E402

SALIDA = APP / 'data/informes/historico.json'
ZH = _cfg.HERRAMIENTAS / 'zoho/zh.py'
LIBRO = 'h4owxade0a8fd840349be9d38b45d75ec0313'      # «CARTERA CLIENTES RO»
HOJA = 'informes mensuales'                          # nombre normalizado de la ÚNICA hoja que se lee
PROHIBIDAS = {'credenciales', 'credencial', 'contrasenas', 'passwords', 'accesos', 'claves'}
COLUMNAS = ['cliente', 'mes', 'enlace_informe', 'enlace_estadisticas', 'informado_en_reunion', 'enviado']
MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
SI = {'si', 'true', 'x', 'ok', 'yes', '1', 'verdadero', 'enviado', 'hecho'}
NO = {'no', 'false', '0', 'falso'}


def booleano(v):
    t = norm(v)
    if not t:
        return None
    if t in SI:
        return True
    if t in NO:
        return False
    raise ValueError('Marca booleana no reconocida; se requiere confirmación.')


def validar_enlace(v):
    if v is None or not str(v).strip():
        return None
    u = str(v).strip()
    try:
        partes = urllib.parse.urlsplit(u)
        valido = (partes.scheme in ('http', 'https') and partes.hostname
                  and not partes.username and not partes.password
                  and not any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in u)
                  and '\\' not in u)
        partes.port  # también rechaza puertos mal formados
    except ValueError:
        valido = False
    if not valido:
        raise ValueError('Enlace de informe inválido; se requiere una URL HTTP(S).')
    return u


def enlace(celda):
    if not celda:
        return None
    if celda.get('url'):
        return validar_enlace(celda['url'])
    contenido = str(celda.get('content') or '').strip()
    return validar_enlace(contenido) if re.match(r'https?://', contenido, re.I) else None


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
    meses = {i + 1 for i, p in enumerate(PREFIJOS) if re.search(rf'\b{p}[a-z]*\b', t)}
    if len(meses) > 1:
        raise ValueError('Cabecera de mes ambigua.')
    return next(iter(meses), None)


def validar_anio(anio):
    if anio is None:
        return None
    if isinstance(anio, bool) or not re.fullmatch(r'[0-9]{4}', str(anio)) or int(anio) == 0:
        raise ValueError('El año confirmado debe tener cuatro cifras y ser válido.')
    return int(anio)


def periodo_de(texto, anio_confirmado=None):
    """La fecha escrita manda; el parámetro solo completa años ausentes, nunca infiere un salto de año."""
    confirmado = validar_anio(anio_confirmado)
    t = str(texto or '').strip()
    if re.fullmatch(r'[0-9]{4}-[0-9]{2}', t):
        anio, mes = map(int, t.split('-'))
        if anio and 1 <= mes <= 12:
            return t
        raise ValueError('Periodo de informe inválido.')
    mes = mes_de(t)
    anios = re.findall(r'(?<![0-9])[0-9]{4}(?![0-9])', t)
    if len(anios) > 1:
        raise ValueError('Cabecera de año ambigua.')
    anio = validar_anio(anios[0]) if anios else confirmado
    if mes is None or anio is None:
        raise ValueError('Falta mes o año explícito; indique --anio-confirmado si el año ha sido confirmado.')
    return f'{anio:04d}-{mes:02d}'


def leer_rejilla(rejilla, filas, cols, *, anio_confirmado=None):
    """Bloques de anchura variable, etiquetas escritas y columnas opcionales reconocidas por cabecera."""
    validar_anio(anio_confirmado)
    cab = {c: norm((rejilla.get((2, c)) or {}).get('content')) for c in range(1, cols + 1)}
    inicios = [c for c in range(2, cols + 1) if cab[c].startswith('informe entregable')]
    if not inicios:
        raise ValueError('No hay bloques de informes reconocidos.')
    bloques, vistos = [], set()
    for i, ini in enumerate(inicios):
        fin = inicios[i + 1] - 1 if i + 1 < len(inicios) else cols
        etiquetas = [(rejilla.get((1, c)) or {}).get('content') for c in range(ini, fin + 1)
                     if mes_de((rejilla.get((1, c)) or {}).get('content'))
                     or re.fullmatch(r'[0-9]{4}-[0-9]{2}', str((rejilla.get((1, c)) or {}).get('content') or '').strip())]
        if not etiquetas:
            raise ValueError('Bloque de informe sin periodo escrito; no se infiere el mes siguiente.')
        periodos = {periodo_de(t, anio_confirmado) for t in etiquetas}
        if len(periodos) != 1:
            raise ValueError('Bloque con periodos ambiguos.')
        periodo = next(iter(periodos))
        if periodo in vistos:
            raise ValueError('Periodo duplicado en la hoja.')
        vistos.add(periodo)
        col = {'informe': ini}
        for c in range(ini + 1, fin + 1):
            clave = ('estad' if cab[c].startswith('informe') and 'estadistic' in cab[c]
                     else 'informado' if cab[c].startswith('informado')
                     else 'enviado' if cab[c].startswith('enviado') else None)
            if clave:
                if clave in col:
                    raise ValueError('Columna de informe ambigua dentro del bloque.')
                col[clave] = c
        bloques.append((periodo, col))
    out, clientes = [], set()
    for f in range(3, filas + 1):
        nombre = str((rejilla.get((f, 1)) or {}).get('content') or '').strip()
        if not nombre:
            continue
        if norm(nombre) in clientes:
            raise ValueError('Cliente duplicado en la hoja; revisar identidad antes de importar.')
        clientes.add(norm(nombre))
        for mes, col in bloques:
            cel = {k: rejilla.get((f, c)) for k, c in col.items()}
            fila = {'cliente_hoja': sanear(nombre), 'mes': mes,
                    'enlace_informe': enlace(cel.get('informe')), 'enlace_estadisticas': enlace(cel.get('estad')),
                    'informado_en_reunion': booleano((cel.get('informado') or {}).get('content')),
                    'enviado': booleano((cel.get('enviado') or {}).get('content'))}
            if any(fila[k] is not None for k in COLUMNAS[2:]):
                out.append(fila)
    return out, [m for m, _ in bloques]


# ------------------------------------------------------------------ CSV (plan B)
ALIAS_CSV = {
    'cliente': ('cliente', 'cliente_hoja', 'nombre_cliente'),
    'mes': ('mes', 'periodo', 'mes_informe'),
    'enlace_informe': ('enlace_informe', 'informe_entregables', 'informe_entregable', 'url_informe'),
    'enlace_estadisticas': ('enlace_estadisticas', 'informes_estadisticas', 'informe_estadisticas', 'url_estadisticas'),
    'informado_en_reunion': ('informado_en_reunion', 'informado_a_cliente', 'informado_al_cliente', 'informado'),
    'enviado': ('enviado', 'enviado_a_cliente', 'enviado_al_cliente'),
}


def leer_csv(ruta, *, anio_confirmado=None):
    validar_anio(anio_confirmado)
    aliases = {norm(a): campo for campo, nombres in ALIAS_CSV.items() for a in nombres}
    with open(ruta, newline='', encoding='utf-8-sig') as f:
        lector = csv.reader(f, strict=True)
        cab = next(lector, None)
        if not cab:
            raise ValueError('CSV sin cabecera.')
        idx = {}
        for i, nombre in enumerate(cab):
            campo = aliases.get(norm(nombre))
            if campo:
                if campo in idx:
                    raise ValueError('Cabeceras CSV ambiguas para una misma columna.')
                idx[campo] = i
        if not {'cliente', 'mes'} <= idx.keys():
            raise ValueError('El CSV requiere cabeceras cliente y mes/periodo.')
        vistos = set()
        for r in lector:
            if not any(v.strip() for v in r):
                continue
            if len(r) != len(cab):
                raise ValueError('Fila CSV con anchura distinta de la cabecera.')
            v = {c: r[idx[c]].strip() if c in idx else None for c in COLUMNAS}
            if not v['cliente']:
                raise ValueError('Fila CSV sin cliente.')
            mes = periodo_de(v['mes'], anio_confirmado)
            clave = (norm(v['cliente']), mes)
            if clave in vistos:
                raise ValueError('Periodo duplicado para el mismo cliente en CSV.')
            vistos.add(clave)
            yield {'cliente_hoja': sanear(v['cliente']), 'mes': mes,
                   'enlace_informe': validar_enlace(v['enlace_informe']),
                   'enlace_estadisticas': validar_enlace(v['enlace_estadisticas']),
                   'informado_en_reunion': booleano(v['informado_en_reunion']), 'enviado': booleano(v['enviado'])}


# ------------------------------------------------------------------ emparejar con los clientes de la app
def emparejar(filas):
    idx = (leer(APP / 'data/indice_clientes.json', {}) or {}).get('clientes', [])
    manual = {k: v for k, v in (leer(AQUI / 'emparejamiento_hoja.json', {}) or {}).items() if not k.startswith('_')}  # «-» = ninguno
    por_norm = {}
    for c in idx:
        por_norm.setdefault(norm(c['nombre']), set()).add(c['id'])
    ids = {c['id'] for c in idx}
    sin = set()
    for f in filas:
        n = norm(f['cliente_hoja'])
        f.pop('sugerencias_cliente_ids', None)
        f.pop('no_es_cliente', None)
        elegido = manual.get(f['cliente_hoja'].strip())
        if elegido not in (None, '-') and elegido not in ids:
            raise ValueError('Emparejamiento manual apunta a un cliente inexistente.')
        exactos = por_norm.get(n, set())
        cid = elegido or (next(iter(exactos)) if len(exactos) == 1 else None)
        if not cid:
            tt = tokens(f['cliente_hoja']) | {w for w in n.split() if len(w) >= 3}
            cands = {c['id'] for c in idx if norm(c['nombre']).replace(' ', '') == n.replace(' ', '')
                     or (tokens(c['nombre']) and tokens(c['nombre']) <= tt)
                     or (n and n in norm(c['nombre']).split())
                     or (tokens(f['cliente_hoja']) and tokens(f['cliente_hoja']) <= tokens(c['nombre']))}
            if cands:
                f['sugerencias_cliente_ids'] = sorted(cands)
        f['emparejamiento'] = 'manual' if elegido else 'nombre_exacto_unico' if cid else 'pendiente_confirmacion'
        if cid == '-':
            cid, f['no_es_cliente'] = None, True
        f['cliente_id'] = cid
        f['cliente'] = next((c['nombre'] for c in idx if c['id'] == cid), f['cliente_hoja'])
        if not cid and not f.get('no_es_cliente'):
            sin.add(f['cliente_hoja'])
    return filas, sorted(sin)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('csv', nargs='?')
    modo = parser.add_mutually_exclusive_group()
    modo.add_argument('--zoho', action='store_true')
    modo.add_argument('--reemparejar', action='store_true')
    parser.add_argument('--probar', action='store_true')
    parser.add_argument('--anio-confirmado', type=validar_anio)
    args = parser.parse_args()
    if bool(args.csv) == bool(args.zoho or args.reemparejar):
        parser.error('Elija un CSV, --zoho o --reemparejar.')
    if args.reemparejar:  # sin llamar a Zoho: vuelve a casar los nombres de la última importación
        prev = leer(SALIDA) or sys.exit('No hay importación previa.')
        filas, meses, origen = prev['filas'], prev['meses'], prev['origen']
    elif args.zoho:
        nombre, nf, nc, rejilla = zoho()
        filas, meses = leer_rejilla(rejilla, nf, nc, anio_confirmado=args.anio_confirmado)
        origen = f'Zoho Sheet por API · libro «CARTERA CLIENTES RO» · solo la hoja «{nombre.strip()}» (con hipervínculos)'
    else:
        filas, meses = list(leer_csv(args.csv, anio_confirmado=args.anio_confirmado)), []
        meses = sorted({f['mes'] for f in filas})
        origen = f'CSV exportado a mano ({Path(args.csv).name})'
    filas, sin = emparejar(filas)
    salida = {'estado': 'importado', 'origen': origen, 'importado': datetime.now().strftime('%Y-%m-%d %H:%M'),
              'meses': meses, 'columnas': COLUMNAS, 'sin_emparejar': sin, 'filas': filas}
    con_enlace = sum(1 for f in filas if f['enlace_informe'] or f['enlace_estadisticas'])
    print(f'{len(filas)} filas cliente×mes · {len({f["cliente_hoja"] for f in filas})} clientes en la hoja · meses {meses[:1]}…{meses[-1:]} · '
          f'{con_enlace} con enlace · enviados {sum(1 for f in filas if f["enviado"])} · sin emparejar {len(sin)}: {sin[:12]}')
    if args.probar:
        return
    hall = escanear(salida)
    if hall:
        sys.exit('Puerta de secretos: no se escribe.\n  ' + '\n  '.join(hall[:10]))
    escribir(SALIDA, salida)
    print(f'→ {SALIDA}. Ahora: python3 generar_informes.py --ficheros')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, csv.Error) as error:
        sys.exit(f'No se importa: {error}')

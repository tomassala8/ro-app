#!/usr/bin/env python3
"""
generar_cohortes.py · retención por cohorte de alta (paneles v4, 3-oct-2026). SOLO LECTURA: no abre ninguna herramienta.

Lee data/finanzas/direccion.json (lo escribe generar_dinero.py) y saca, para «Dinero por cliente» y «Finanzas»:
  · % de CLIENTES que siguen N meses después de su mes de alta (libro de clientes: altas_bajas[].qa / qb, cerrado con Tomás el 1-oct).
  · % de la CUOTA DE ENTRADA que sigue (puente de la cuota: puente[].qa / qb con el importe de cada alta y de cada baja).
    Sin subidas ni rebajas: el puente no las da cliente a cliente. Se dice en pantalla.
Filas = mes de alta (los 24 últimos meses cerrados) · columnas = mes 0..12 · fila «media» ponderada por clientes (o por euros).
Mes 0 = el propio mes de alta. Un cliente sigue al final del mes m+k si no tiene baja o su baja es de un mes posterior.
Solo meses cerrados (el mes en curso no cuenta: sus bajas aún no están).

Salida: data/dinero_cliente/cohortes.json (reglas_permisos.json → datos_de_modulo: dirección, operaciones y proyectos).
Sin nombres de cliente: solo recuentos y porcentajes por mes.

Uso: python3 fuentes_dinero/generar_cohortes.py   (generar_dinero.py lo lanza al terminar)
"""
import json, sys, datetime as dt
from pathlib import Path

AQUI = Path(__file__).resolve().parent
APP = AQUI.parent
sys.path.insert(0, str(APP / 'fuentes'))
from comun import escribir, escanear   # noqa: E402

DATA = APP / 'data'
FILAS = 24          # meses de alta que se enseñan
COLUMNAS = 13       # mes 0..12


def mes_mas(m, k):
    y, mm = int(m[:4]), int(m[5:7]) + k
    y += (mm - 1) // 12
    mm = (mm - 1) % 12 + 1
    return f'{y}-{mm:02d}'


def main():
    d = json.loads((DATA / 'finanzas' / 'direccion.json').read_text())
    dd = (d.get('direccion') or [{}])[0]
    ab = [x for x in dd.get('altas_bajas', []) if not x.get('curso')]
    pu = dd.get('puente', [])
    if not ab or not pu:
        print('Sin altas y bajas o sin puente en direccion.json: no escribo nada.'); sys.exit(1)
    ultimo = min(ab[-1]['m'], pu[-1]['m'])          # último mes cerrado en las dos fuentes

    # clientes (libro): primera alta y primera baja posterior
    alta, baja = {}, {}
    for x in ab:
        for n in x.get('qa') or []:
            alta.setdefault(n, x['m'])
        for n in x.get('qb') or []:
            if n in alta and n not in baja and x['m'] >= alta[n]:
                baja[n] = x['m']
    # cuota de entrada (puente): importe del alta y mes de la baja
    alta_c, baja_c = {}, {}
    for x in pu:
        for n, v in x.get('qa') or []:
            alta_c.setdefault(n, (x['m'], float(v or 0)))
        for n, _v in x.get('qb') or []:
            if n in alta_c and n not in baja_c and x['m'] >= alta_c[n][0]:
                baja_c[n] = x['m']

    meses = sorted({m for m in alta.values() if m <= ultimo})[-FILAS:]
    sigue = lambda b, m: b is None or b > m

    def tabla(grupos, peso, bajas):
        filas, num, den = [], [0.0] * COLUMNAS, [0.0] * COLUMNAS
        for m in meses:
            gente = grupos.get(m, [])
            base = sum(peso(n) for n in gente)
            if not gente or base <= 0:
                continue
            pct = []
            for k in range(COLUMNAS):
                mk = mes_mas(m, k)
                if mk > ultimo:
                    pct.append(None); continue
                v = sum(peso(n) for n in gente if sigue(bajas.get(n), mk))
                pct.append(round(100 * v / base, 1))
                num[k] += v; den[k] += base
            filas.append({'m': m, 'n': len(gente), 'base': round(base, 2), 'pct': pct})
        media = [round(100 * num[k] / den[k], 1) if den[k] else None for k in range(COLUMNAS)]
        return filas, media

    g_cli = {}
    for n, m in alta.items():
        g_cli.setdefault(m, []).append(n)
    g_cuo = {}
    for n, (m, _v) in alta_c.items():
        g_cuo.setdefault(m, []).append(n)
    filas_cli, media_cli = tabla(g_cli, lambda n: 1, baja)
    filas_cuo, media_cuo = tabla(g_cuo, lambda n: alta_c[n][1], baja_c)

    doc = {
        'formato': 1, 'modulo': 'dinero-cliente', 'generado': dt.datetime.now().strftime('%Y-%m-%d %H:%M'),
        'ultimo_mes': ultimo, 'columnas': COLUMNAS,
        'fuente': 'Libro de clientes (altas y bajas, cerrado con Tomás el 1-oct) y puente de la cuota de Holded',
        'regla': 'Mes 0 = el mes de alta. Un cliente sigue al final del mes si no se ha dado de baja. Solo meses cerrados.',
        'clientes': {'filas': filas_cli, 'media': media_cli, 'texto': '% de clientes que siguen'},
        'cuota_entrada': {'filas': filas_cuo, 'media': media_cuo,
                          'texto': '% de la cuota con la que entraron que sigue (sin subidas ni rebajas: el puente no las da cliente a cliente)'},
    }
    if escanear(doc):
        print('PUERTA DE SECRETOS: no escribo nada.', escanear(doc)[:5]); sys.exit(2)
    escribir(DATA / 'dinero_cliente' / 'cohortes.json', doc)
    print(json.dumps({'ultimo_mes': ultimo, 'filas': len(filas_cli), 'media_clientes': media_cli, 'media_cuota': media_cuo}, ensure_ascii=False))


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Condensa las respuestas del conector de SE Ranking (PROJECT_getKeywordStats, 1-sep → 2-oct-2026)
en fuentes_seo/_cache/seranking.json: por cliente, palabras con posición hoy, hace 7 días y hace ~30 días.
Las respuestas en bruto (una por proyecto, de 80 KB a 1 MB) se guardan fuera de la app; aquí solo lo útil.
Uso: python3 sr_condensar.py <carpeta_con_las_respuestas>"""
import json, glob, os, sys, datetime
CARPETA = sys.argv[1]
# fichero (marca de tiempo del conector) → cliente de la app. Se emparejó por orden de llamada y tamaño de respuesta,
# y se comprobó con la primera palabra de cada proyecto (p. ej. kiosko-box → «fotos imprimir»).
MAPA = {
 '1790947733552': ('christian-sanchez', 12865235), '1790947732818': ('octoedro', 10623737),
 '1790947753918': ('accompany', 10910273), '1790947753671': ('adade-zaragoza', 9763961), '1790947753750': ('ahedo', 8646762),
 '1790947753347': ('aselegal', 11050775), '1790947752820': ('asetra', 6959006), '1790947753014': ('aster-asesoria', 9498275),
 '1790947753307': ('avantik', 7534223), '1790947752878': ('ayg-asesores', 9351863), '1790947780893': ('bit-24', 10115765),
 '1790947780719': ('bonet-asesores', 9238427), '1790947782869': ('busbac', 11705489), '1790947782890': ('centro-consulting', 10821245),
 '1790947782886': ('consulting-f', 11669846), '1790947780960': ('ecija-advisory', 8423390), '1790947781279': ('ecom-advisory', 11506415),
 '1790947780917': ('fitec-asesores', 10917917), '1790947847138': ('fusterguell', 9497984), '1790947783273': ('gac', 9126428),
 '1790947799242': ('gestanex', 12577964), '1790947799509': ('greconsult', 11291615), '1790947800233': ('innova-scala', 9848531),
 '1790947799759': ('ip-forense', 7781501), '1790947799914': ('j-d-consulting', 8475110), '1790947799823': ('joan-lluis-vives', 10930340),
 '1790947800993': ('kiosko-box', 5962484), '1790947816588': ('laver', 12925739), '1790947817128': ('mg-economistes', 9503675),
 '1790947817549': ('musashi-consultores', 11080490), '1790947817245': ('orejana', 12282629), '1790947820169': ('oteca', 9413234),
 '1790947818183': ('prodegest', 11172056), '1790947817058': ('romero-martinez', 11508218), '1790947836325': ('segu-assessors', 9747227),
 '1790947836186': ('sol-4', 12284627), '1790947835827': ('torrevieja-consult', 9498149), '1790947835470': ('tribulex', 12879914),
 '1790947835974': ('xterna', 4928195), 'deudot': ('deudot', 12991772),
}
HOY = datetime.date(2026, 10, 2)
def pos_en(posiciones, dia, campo='pos'):
    """Posición en la fecha más cercana ≤ día (0 = fuera del top 100 → None)."""
    cand = [p for p in posiciones if p['date'] <= str(dia)]
    if not cand: return None, None
    p = max(cand, key=lambda x: x['date'])
    v = p.get(campo) or 0
    return (v if v > 0 else None), p['date']
salida = {}
for f in glob.glob(os.path.join(CARPETA, '*.txt')) + glob.glob(os.path.join(CARPETA, '*.json')):
    clave = os.path.basename(f).rsplit('-', 1)[-1].split('.')[0]
    if clave not in MAPA: continue
    cid, proyecto = MAPA[clave]
    d = json.load(open(f))
    motores = []
    for i, m in enumerate(d.get('data', [])):
        kws = []
        for k in m.get('keywords', []):
            ps = k.get('positions') or []
            hoy, fh = pos_en(ps, HOY)
            ayer, _ = pos_en(ps, HOY - datetime.timedelta(days=1))
            sem, _ = pos_en(ps, HOY - datetime.timedelta(days=7))
            sem2, _ = pos_en(ps, HOY - datetime.timedelta(days=8))
            mes, fm = pos_en(ps, HOY - datetime.timedelta(days=30))
            primera = min((p['date'] for p in ps), default=None)
            mapa, _ = pos_en(ps, HOY, 'map_position')
            kws.append({'k': k['name'], 'vol': k.get('volume') or 0, 'hoy': hoy, 'ayer': ayer, 'sem': sem, 'sem2': sem2, 'mes': mes, 'mapa': mapa,
                        'desde': primera, 'ultima': fh})
        motores.append({'site_engine_id': m['site_engine_id'], 'principal': i == 0, 'palabras': kws})
    fechas = sorted({k['ultima'] for m in motores for k in m['palabras'] if k['ultima']})
    salida[cid] = {'proyecto': proyecto, 'motores': motores, 'ultima_comprobacion': fechas[-1] if fechas else None,
                   'prueba': f'https://online.seranking.com/admin.site.rankings.site_id-{proyecto}.html'}
json.dump({'generado': datetime.datetime.now().strftime('%Y-%m-%d %H:%M'), 'origen': 'conector SE Ranking (PROJECT_getKeywordStats, 1-sep → 2-oct-2026)', 'clientes': salida},
          open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '_cache', 'seranking.json'), 'w'), ensure_ascii=False)
print(len(salida), 'clientes con posiciones')

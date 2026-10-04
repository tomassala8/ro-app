"""Semántica pura de posiciones observadas. Sin IO, proveedores ni reloj implícito."""
from datetime import date
import math


def fecha(v):
    if not isinstance(v,str) or len(v)!=10:
        return None
    try:
        d=date.fromisoformat(v)
        return d if d.isoformat()==v else None
    except ValueError:
        return None


def posicion(v, estado=None, centinela=None):
    """0/ausencia desconocidos. 101/>100 no se descartan sin sentinel explícito."""
    if estado in ('sin_dato','ausente','no_encontrada','sentinel'):
        return None
    if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<1 or not float(v).is_integer():
        return None
    if centinela is not None and v==centinela:
        return None
    return int(v)


def seleccionar(posiciones,dia,campo='pos'):
    """Fecha exacta; sin arrastrar una lectura anterior. Conflictos no se resuelven eligiendo la mejor."""
    objetivo=fecha(str(dia))
    if objetivo is None:
        return None,None
    candidatas=[p for p in posiciones if isinstance(p,dict) and fecha(p.get('date'))==objetivo]
    if not candidatas:
        return None,None
    valores={posicion(p.get(campo),p.get(campo+'_estado'),p.get(campo+'_centinela')) for p in candidatas}
    return (next(iter(valores)) if len(valores)==1 else None),objetivo.isoformat()


def preparar_motores(motores, hasta=None):
    salida=[]
    for motor in motores if isinstance(motores,list) else []:
        if not isinstance(motor,dict):
            continue
        palabras=[]
        for raw in motor.get('palabras',[]) if isinstance(motor.get('palabras'),list) else []:
            if not isinstance(raw,dict):continue
            p={**raw,'motor_id':motor.get('site_engine_id'),'fechas':dict(raw.get('fechas')) if isinstance(raw.get('fechas'),dict) else {}}
            for campo in ('hoy','ayer','sem','sem2','mes','mapa'):
                p[campo]=posicion(raw.get(campo),(raw.get('estados') if isinstance(raw.get('estados'),dict) else {}).get(campo),(raw.get('centinelas') if isinstance(raw.get('centinelas'),dict) else {}).get(campo))
                d=fecha(p['fechas'].get(campo))
                if d and fecha(str(hasta)) and d>fecha(str(hasta)):
                    p[campo]=None;d=None
                p['fechas'][campo]=d.isoformat() if d else None
            # Sólo la lectura actual orgánica puede usar el campo ultima legacy. Maps no hereda su fecha.
            if p['fechas']['hoy'] is None and fecha(raw.get('ultima')) and (fecha(str(hasta)) is None or fecha(raw['ultima'])<=fecha(str(hasta))):
                p['fechas']['hoy']=raw['ultima']
            p['hoy_d'],p['sem_d']=p['hoy'],p['sem']
            p['fechas_d']=dict(p['fechas'])
            for a,b in (('hoy','ayer'),('sem','sem2')):
                fa,fb=fecha(p['fechas'][a]),fecha(p['fechas'][b])
                if p[a] is not None and p[b] is not None and fa and fb and (fa-fb).days==1:
                    if p[b]<p[a]:p[a],p['fechas'][a]=p[b],p['fechas'][b]
            palabras.append(p)
        salida.append({**motor,'palabras':palabras})
    return salida


def comparar(p,antes='sem',hoy='hoy',dias=7):
    a,b=posicion(p.get(antes)),posicion(p.get(hoy))
    fa,fb=fecha((p.get('fechas') or {}).get(antes)),fecha((p.get('fechas') or {}).get(hoy))
    motor=p.get('motor_id')
    if a is None or b is None or not fa or not fb or (fb-fa).days!=dias or isinstance(motor,bool) or not (isinstance(motor,int) and motor>0 or isinstance(motor,str) and motor.isdecimal() and int(motor)>0):
        return None
    return a-b


def top(campo,n,palabras):
    observadas=[posicion(p.get(campo)) for p in palabras]
    observadas=[p for p in observadas if p is not None]
    return sum(p<=n for p in observadas) if observadas else None


def reparto_observado(palabras):
    comunes=[p for p in palabras if comparar(p,'mes','hoy',30) is not None]
    out={}
    for key,n in (('top1',1),('top3',3),('top5',5),('top10',10)):
        out[key]={'hoy':top('hoy',n,palabras),'mes':top('mes',n,comunes) if len(comunes)==sum(posicion(p.get('hoy')) is not None for p in palabras) else None,'mes_todas':top('mes',n,palabras),
                  'sin_ver_hoy':sum(posicion(p.get('hoy')) is None and posicion(p.get('mes')) is not None and posicion(p.get('mes'))<=n for p in palabras),
                  'hoy_comparable':top('hoy',n,comunes),'comparables':len(comunes),'cobertura':'parcial'}
    for campo in ('hoy','mes'):
        valores=[posicion(p.get(campo)) for p in palabras]
        vistos=[v for v in valores if v is not None]
        out.setdefault('fuera',{})[campo]=sum(v>10 for v in vistos) if vistos else None
        out.setdefault('sin_dato',{})[campo]=sum(v is None for v in valores)
    return out


def suma_medida(valores):
    vistos=[v for v in valores if isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) and v>=0]
    return sum(vistos) if vistos else None

"""Periodos comunes (carril N1 · D-P-N1). La MISMA regla que modulos/paneles_periodo.js: si cambias una, cambia la otra.

Ids: hoy · ayer · 7d · 30d · mes · mes_ant · trim · anio (· medida solo en el navegador, con la serie diaria).
Comparación: «anterior» (mismo número de días justo antes; mes → del 1 al mismo día del mes pasado; mes_ant → el mes
anterior entero; trim → mismos días del trimestre anterior; anio → mismo tramo del año pasado) y «anio_ant» (mismas
fechas un año antes).
"""
from datetime import date, timedelta

IDS = ["hoy", "ayer", "7d", "30d", "mes", "mes_ant", "trim", "anio"]
TEXTO = {"hoy": "Hoy", "ayer": "Ayer", "7d": "7 días", "30d": "30 días", "mes": "Este mes", "mes_ant": "Mes anterior",
         "trim": "Este trimestre", "anio": "Este año"}


def _menos_anio(d):
    try:
        return d.replace(year=d.year - 1)
    except ValueError:          # 29-feb
        return d.replace(year=d.year - 1, day=28)


def _menos_meses(d, n):
    m = d.month - 1 - n
    a, m = d.year + m // 12, m % 12 + 1
    import calendar
    return date(a, m, min(d.day, calendar.monthrange(a, m)[1]))


def rango(pid, hoy=None):
    hoy = hoy or date.today()
    ayer = hoy - timedelta(days=1)
    if pid == "hoy":
        return hoy, hoy
    if pid == "ayer":
        return ayer, ayer
    if pid == "7d":
        return hoy - timedelta(days=7), ayer
    if pid == "30d":
        return hoy - timedelta(days=30), ayer
    if pid == "mes":
        return hoy.replace(day=1), hoy
    if pid == "mes_ant":
        fin = hoy.replace(day=1) - timedelta(days=1)
        return fin.replace(day=1), fin
    if pid == "trim":
        return date(hoy.year, 3 * ((hoy.month - 1) // 3) + 1, 1), hoy
    if pid == "anio":
        return date(hoy.year, 1, 1), hoy
    raise ValueError(pid)


def comparacion(pid, a, b, modo="anterior"):
    if modo == "anio_ant":
        return _menos_anio(a), _menos_anio(b)
    if pid == "mes":
        a2 = _menos_meses(a, 1)
        return a2, _menos_meses(b, 1)
    if pid == "mes_ant":
        fin = a - timedelta(days=1)
        return fin.replace(day=1), fin
    if pid == "trim":
        a2 = _menos_meses(a, 3)
        return a2, a2 + (b - a)
    if pid == "anio":
        return _menos_anio(a), _menos_anio(b)
    n = (b - a).days + 1
    return a - timedelta(days=n), a - timedelta(days=1)


def todos(hoy=None):
    """[{id, texto, desde, hasta, anterior:[a,b], anio_ant:[a,b]}] en ISO."""
    out = []
    for pid in IDS:
        a, b = rango(pid, hoy)
        pa, pb = comparacion(pid, a, b, "anterior")
        ya, yb = comparacion(pid, a, b, "anio_ant")
        out.append({"id": pid, "texto": TEXTO[pid], "desde": a.isoformat(), "hasta": b.isoformat(),
                    "anterior": [pa.isoformat(), pb.isoformat()], "anio_ant": [ya.isoformat(), yb.isoformat()]})
    return out

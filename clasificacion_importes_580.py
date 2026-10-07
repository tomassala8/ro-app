"""Clasificación conservadora de texto monetario. Sin IO ni permisos propios."""
import re

MARCAS = (
    ('dinero_empresa', re.compile(r'\b(?:beneficio\s+(?:de\s+la\s+)?empresa|margen\s+(?:de\s+la\s+)?empresa|coste\s+(?:del?\s+)?equipo|agency\s+(?:profit|margin|cost))\b', re.I)),
    ('cobros', re.compile(r'\b(?:cobros?|cobrad[oa]s?|impagos?|revenue|invoice\s+total)\b', re.I)),
    ('cuota', re.compile(r'\b(?:cuotas?|fee|honorarios|mantenimiento|factur\w*|recurrente|mensual|al\s+mes)\b|/\s*mes\b', re.I)),
    ('inversion', re.compile(r'\b(?:inversi[oó]n|publicidad|gasto|Meta|Ads|CPL|CPM|coste\s+por\s+(?:lead|cita)|presupuesto\s+(?:ads|publicitario))\b', re.I)),
    ('regla', re.compile(r'\btecho\b', re.I)),
)
FAMILIAS = frozenset({'cuota', 'inversion', 'cobros', 'dinero_empresa'})

def clasificar_importe_580(texto, ini, fin):
    if not isinstance(texto, str) or type(ini) is not int or type(fin) is not int or not 0 <= ini < fin <= len(texto):
        return 'ambiguo'
    cortes = list(re.finditer(r';|\n|·|(?<=[.!?])\s+(?=[A-Za-zÁÉÍÓÚáéíóú])', texto))
    inicio = max([m.end() for m in cortes if m.end() <= ini] or [0])
    final = min([m.start() for m in cortes if m.start() >= fin] or [len(texto)])
    candidatos = []
    for familia, rx in MARCAS:
        for m in rx.finditer(texto, inicio, final):
            distancia = ini - m.end() if m.end() <= ini else m.start() - fin if m.start() >= fin else None
            if distancia is not None and distancia <= 40:
                candidatos.append((distancia, familia))
    if not candidatos:
        return 'ambiguo'
    minimo = min(d for d, _ in candidatos)
    familias = {f for d, f in candidatos if d == minimo}
    return next(iter(familias)) if len(familias) == 1 else 'ambiguo'

def fuera_importe_580(tipo, quitar):
    if tipo == 'ambiguo':
        return bool(FAMILIAS.intersection(quitar))
    return tipo in quitar or (tipo == 'regla' and 'inversion' in quitar)

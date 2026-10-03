# -*- coding: utf-8 -*-
"""V2 · ¿De qué cliente es una campaña de outreach? (Snov.io no lo dice: solo el nombre de la campaña.)

UNA regla para el generador (generar_ventas_ro.py) y para cualquier pantalla: la primera palabra del nombre del cliente
(verdad única, data/verdad/clientes.json › comun) aparece en el nombre de la campaña. Alias para los nombres cortos que usa
outreach («PGBA» = PGB Auditores). Sin coincidencia → None (campaña de RO o sin cliente claro: no se le da a nadie).
Con el cliente, la pantalla y el servidor recortan por la cartera de outreach (silla «outreach» de asignaciones).
"""
import json, os, re, unicodedata

APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ALIAS = {'pgba': 'pgb-auditores', 'ecom': 'ecom-advisory', 'musashi': 'musashi-consultores', 'ecija': 'ecija-advisory'}


def _norm(t):
    t = unicodedata.normalize('NFD', (t or '').lower())
    return re.sub(r'[^a-z0-9 ]', ' ', ''.join(c for c in t if not unicodedata.combining(c))).split()


def clientes():
    try:
        v = json.load(open(os.path.join(APP, 'data', 'verdad', 'clientes.json'), encoding='utf-8'))
        return [(c['id'], c.get('nombre') or c['id']) for c in v.get('comun', [])]
    except Exception:
        return []


def cliente_de(nombre_campana, lista=None):
    pal = _norm(nombre_campana)
    if not pal:
        return None
    for p in pal:
        if p in ALIAS:
            return ALIAS[p]
    lista = clientes() if lista is None else lista
    # el nombre más largo primero («Centro Consulting» antes que un «Consulting F»)
    for cid, nom in sorted(lista, key=lambda x: -len(x[1] or '')):
        n = _norm(nom)
        if not n:
            continue
        k = ' '.join(n[:2]) if len(n) > 1 and n[0] in ('centro', 'grupo', 'consulting') else n[0]
        if len(k) >= 3 and f' {k} ' in f" {' '.join(pal)} ":
            return cid
    return None

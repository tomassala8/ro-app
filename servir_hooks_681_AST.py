"""Sólo función actual recortada para fixture AST; no importar servidor."""
def modulo_recortado(real, persona, cp, rel):
    """El fichero data/<rel>.json ya recortado para esta persona, por la MISMA puerta que /api/modulo/<rel> (sin dejar
    «denegado» en el rastro: lo que no puede leer no entra en el índice). None si no puede o no existe."""
    pm = puerta_modulo(real, persona, rel, apuntar=False)
    if pm.get("error") or not pm["fichero"].exists():
        return None
    try:
        doc, aviso_dato_287 = leer_json_bueno(pm["fichero"])
    except Exception:
        return None
    if not modulo_vigente_581(real, persona, rel, pm, doc):
        return None
    conf = pm["conf"]
    salida = ACT.quitar_bajas(recortar_modulo(persona, cp, doc, pm["nivel"], tuple(conf.get("solo_todo_sin_cliente", [])), tuple(conf.get("filas_lead", [])), conf), rel)
    if rel == "produccion/produccion" and not aviso_dato_287:
        salida = EVIDENCIA_PRODUCCION_287.enriquecer287(salida, sys.modules[__name__], real, persona)
    return salida if modulo_vigente_581(real, persona, rel, pm, doc) else None


"""Semántica pura de estados: catálogo exacto de la lista, sin inferir por nombres."""
TIPOS = frozenset({"open", "custom", "unstarted", "done", "closed"})


def resolver_estado(tarea, catalogo):
    desconocido = {"determinado": False, "final_flujo": False, "tipo": None,
                   "motivo": "Estado por contrastar con la lista de ClickUp"}
    lid = str(tarea.get("lista_id") or "")
    lista = (catalogo.get("listas") or {}).get(lid)
    if not lid or not isinstance(lista, dict) or lista.get("ok") is not True:
        return desconocido
    filas = [r for r in lista.get("estados") or [] if isinstance(r, dict)
             and r.get("status") == tarea.get("estado")]
    if len(filas) != 1 or filas[0].get("type") not in TIPOS:
        return desconocido
    tipo = filas[0]["type"]
    observado = tarea.get("tipo_estado")
    if observado is not None and observado != tipo:
        return desconocido
    return {"determinado": True, "final_flujo": tipo in {"done", "closed"},
            "tipo": tipo, "motivo": "Final de flujo; no acredita entrega aceptada" if tipo in {"done", "closed"}
            else "Estado no final en esta lista"}

// Sólo copia autorizada: ninguna lectura, persistencia ni acción de proveedor.
export function prepararTableroTrabajo181(filas, listaId, resolver) {
  const validas = (Array.isArray(filas) ? filas : []).filter(t => typeof t?.id === 'string' && t.id);
  const listas = [...new Set(validas.map(t => t.lista_id).filter(id=>typeof id==='string' && id))].sort().map(id => {
    const nombres = [...new Set(validas.filter(t => t.lista_id === id).map(t => t.lista).filter(x => typeof x === 'string' && x))];
    return { id, nombre: nombres.length === 1 ? `${nombres[0]} · ${id}` : id };
  });
  if (!listaId || !listas.some(l => l.id === listaId)) return { listas, tareas: [], lista_disponible: false };
  const por = new Map();
  for (const t of validas) { if (!por.has(t.id)) por.set(t.id, []); por.get(t.id).push(t); }
  const tareas = [];
  // Metadata no idéntica => no elegir la última fila ni habilitar acciones sobre una identidad ambigua.
  const firma = t => JSON.stringify([t.lista_id, t.cli ?? null, t.estado ?? null, t.tipo_estado ?? null,
    t.vence ?? null, t.tarea ?? null, t.prioridad ?? null, [...(Array.isArray(t.etiquetas) ? t.etiquetas : [])].sort()]);
  for (const [id, rows] of por) {
    if (!rows.some(t => t.lista_id === listaId)) continue;
    const coherente = new Set(rows.map(firma)).size === 1;
    const t = rows.find(t => t.lista_id === listaId);
    const asignados = [...new Set(rows.filter(r => r.lista_id === listaId).map(r => r.persona_id).filter(p => typeof p === 'string' && p))].sort();
    const resolucion = coherente ? resolver(t) : { estado: 'indeterminado', final_flujo: false, tipo: null, motivo: 'Las filas de esta tarea no coinciden en lista, cliente o metadatos.' };
    tareas.push({ ...t, id, asignados, coherente, resolucion_estado: resolucion,
      columna_tablero: resolucion.estado === 'verificado' ? t.estado : null });
  }
  return { listas, tareas, lista_disponible: true };
}

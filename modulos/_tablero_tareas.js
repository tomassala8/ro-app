// Funciones del tablero: inventario autorizado, una tarjeta por ID y estados exactos de UNA lista.
export function tarjetasUnicas(tareas = []) {
  const mapa = new Map();
  for (const t of tareas) {
    if (!t?.id) continue;
    const asignados = [...new Set([...(Array.isArray(t.asignados) ? t.asignados.filter(x => typeof x === 'string') : []), ...(t.persona_id ? [t.persona_id] : [])])];
    const existente = mapa.get(String(t.id));
    if (existente) {
      existente.asignados = [...new Set([...existente.asignados, ...asignados])];
      if (['lista_id', 'cli', 'estado'].some(k => existente[k] !== t[k])) existente.inconsistente = true;
    } else mapa.set(String(t.id), { ...t, id: String(t.id), asignados });
  }
  return [...mapa.values()];
}
export function filtrarTarjetas(tareas, { vista = 'mia', yo, asignado = '', cliente = '', lista = '', buscar = '', proyecto = '', prioridad = '', etiqueta = '', preset = 'todo' }) {
  const q = buscar.trim().toLocaleLowerCase('es');
  return tareas.filter(t => (vista !== 'mia' || t.asignados.includes(yo))
    && (!asignado || (asignado === '__sin_asignar' ? !t.asignados.length : t.asignados.includes(asignado)))
    && (!cliente || (cliente === '__sin_cliente' ? !t.cli : t.cli === cliente))
    && (!lista || t.lista_id === lista)
    && (!proyecto || (t.proyecto || t.carpeta || '') === proyecto)
    && (!prioridad || String(t.prio_n || t.prioridad || '') === prioridad)
    && (!etiqueta || (t.etiquetas || []).includes(etiqueta))
    && (preset !== 'daily' || ['planning semanal', 'próximo sprint', 'diario', 'en curso'].includes(String(t.estado_app || t.estado).toLocaleLowerCase('es')))
    && (!q || `${t.tarea || ''} ${t.cliente || ''} ${t.id}`.toLocaleLowerCase('es').includes(q)));
}
export function estadosDeLista(datos, lid) {
  const detalle = (datos.estados_detalle?.[lid] || []).filter(s => typeof s.estado === 'string' && s.estado);
  if (detalle.length) return [...new Map(detalle.map(s => [s.estado, s])).values()].sort((a, b) => (a.orden ?? 100) - (b.orden ?? 100));
  // La lista de nombres solo basta si el backend confirma que el catálogo está completo, nunca estados inferidos.
  if (datos.cobertura_estados?.completa) return [...new Set(datos.estados_lista?.[lid] || [])].map((estado, orden) => ({ estado, orden, tipo: null }));
  return [];
}
export function columnasDeLista(tareas, estados) {
  const cols = estados.map(s => ({ ...s, tareas: tareas.filter(t => (t.estado_app || t.estado) === s.estado) }));
  const nombres = new Set(estados.map(s => s.estado));
  const fuera = tareas.filter(t => !nombres.has(t.estado_app || t.estado));
  return { columnas: cols, fuera };
}
export function textoSincronia(t) {
  const e = t.cambio_estado || t.sincronia_estado;
  if (e === 'confirmado') return 'Confirmado por ClickUp';
  if (e === 'fallido' || e === 'error' || e === 'rebotado') return 'No se pudo pasar a ClickUp';
  if (e === 'simulado' || e === 'simulada') return 'Guardado en la app · no enviado a ClickUp (simulación)';
  if (e === 'pendiente' || t.estado_app) return 'Guardado en la app · pendiente de ClickUp';
  return 'Estado leído de la copia de ClickUp';
}
export function puedeMover(t, datos, estados) {
  return !datos.solo_lectura && t.puede_editar === true && !t.inconsistente && estados.length > 0;
}
export function gestorMovimientos({ api, clave = () => globalThis.crypto.randomUUID(), alCambiar = () => {} }) {
  const pendientes = new Set(), intentos = new Map();
  return { pendientes, async mover(t, estado, datos, estados) {
    if (!puedeMover(t, datos, estados)) throw new Error('Esta tarea es de lectura o no tiene estados confirmados.');
    if (!estados.some(s => s.estado === estado)) throw new Error('Ese estado no pertenece a la lista de esta tarea.');
    if (pendientes.has(t.id) || estado === (t.estado_app || t.estado)) return null;
    let intento = intentos.get(t.id);
    if (!intento || intento.estado !== estado) { intento = { estado, clave: clave() }; intentos.set(t.id, intento); }
    pendientes.add(t.id); alCambiar();
    try {
      const r = await api('tareas/cambio', { metodo: 'POST', cuerpo: { clave: intento.clave, tarea: t.id, accion: 'estado', estado } });
      if (!r?.ok || !['simulado', 'simulada', 'pendiente', 'confirmado'].includes(r.estado)) throw new Error(r?.texto || 'No se pudo confirmar el guardado. Reintenta sin duplicar.');
      t.estado_clickup = t.estado_clickup || t.estado;
      t.estado_app = estado; t.cambio_estado = r.estado;
      if (r.estado === 'confirmado') { t.estado = estado; t.estado_clickup = estado; t.estado_app = null; }
      return r;
    } finally { pendientes.delete(t.id); alCambiar(); }
  } };
}

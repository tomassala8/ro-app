// Contratos de exportación: sólo fuentes autorizadas del servidor, nunca aceptación inferida.
export function logoInforme(cliente) {
  const uri = typeof cliente?.logo === 'string' ? cliente.logo : '';
  const id = String(cliente?.id || '');
  if (!/^[\w-]+$/.test(id)) return null;
  const esc = id.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  if (new RegExp(`^/?logos/${esc}\\.(?:jpg|png|webp|gif)(?:\\?v=[a-f0-9]{12})?$`).test(uri)) return uri;
  if (uri.length <= 4 * 1024 * 1024 && /^data:image\/(?:png|jpeg|webp|gif);base64,[A-Za-z0-9+/]+={0,2}$/.test(uri)) return uri;
  return null;
}
export function motivoExportacion(avisos, logo) {
  if (avisos?.some(a => a.color === 'rojo' && ['otro_cliente', 'datos_leads'].includes(a.tipo))) return 'Corrige los avisos de privacidad y de cuenta antes de exportar.';
  if (logo !== 'cargado') return logo === 'error' ? 'El logo del cliente no se pudo cargar. Corrige su imagen antes de exportar el informe final.' : 'El informe final requiere el logo real del cliente cargado. Las iniciales y el logo de RO no lo sustituyen.';
  return null;
}
const limpio = (v, n = 300) => typeof v === 'string' && !/[\w.+-]+@[\w-]+\.[\w.-]+|(?:\+34\s*)?[6789](?:[\s.-]?\d){8}|\b(?:token|secret|password|authorization)\s*[:=]/i.test(v) ? v.slice(0, n) : '';
const dia = v => {
  if (typeof v !== 'string' || !/^\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2}))?$/.test(v)) return null;
  const fecha = v.slice(0, 10), d = new Date(`${fecha}T00:00:00Z`);
  return !Number.isNaN(+d) && d.toISOString().slice(0, 10) === fecha && !Number.isNaN(Date.parse(v)) ? fecha : null;
};
export function evidenciaEjecucion(doc, clienteId, periodo) {
  const base = { tareas: [], cobertura: 'sin_datos', fuente: '', fecha: '', nota: 'No hay evidencia de ejecución disponible para este periodo. Esto no significa que no se haya trabajado.' };
  if (!doc || doc.cliente_id !== clienteId || doc.desde !== periodo.desde || doc.hasta !== periodo.hasta || !Array.isArray(doc.tareas)) return base;
  const frecuencia = new Map();
  for (const t of doc.tareas) frecuencia.set(t.id, (frecuencia.get(t.id) || 0) + 1);
  const tareas = doc.tareas.filter(t => t.cliente_id === clienteId && typeof t.id === 'string' && t.id && frecuencia.get(t.id) === 1 && ['finalizacion_flujo', 'ejecucion_documentada'].includes(t.tipo_evidencia) && dia(t.fecha_ejecucion) >= periodo.desde && dia(t.fecha_ejecucion) <= periodo.hasta && limpio(t.fuente_evidencia) && limpio(t.nombre)).map(t => ({
    id: t.id, nombre: limpio(t.nombre), fecha: dia(t.fecha_ejecucion), fuente: limpio(t.fuente_evidencia), tipo: t.tipo_evidencia,
    descripcion: limpio(t.descripcion_ejecutada, 1200), url: typeof t.url === 'string' && /^https:\/\/app\.clickup\.com\/t\/[\w-]+$/.test(t.url) ? t.url : null,
  }));
  const descartadas = doc.tareas.length - tareas.length;
  const completa = doc.cobertura === 'completa' && !descartadas;
  return { tareas, cobertura: completa ? 'completa' : 'parcial', fuente: limpio(doc.fuente), fecha: limpio(doc.fecha_lectura, 40),
    nota: completa ? 'Cobertura declarada completa por esta fuente y para este periodo; no acredita aceptación de entregables.' : 'Copia parcial de evidencias. Puede faltar trabajo ejecutado; no acredita aceptación de entregables.', descartadas };
}

// Las lecturas se comparten sólo durante una ventana corta. Un fallo o ausencia
// no queda memorizado; una respuesta vieja no invalida una petición posterior.
export function lecturaInforme(cache, clave, cargar, { ttl = 60000, ahora = Date.now } = {}) {
  const previo = cache.get(clave), instante = ahora();
  if (previo && instante >= previo.fecha && instante - previo.fecha < ttl) return previo.promesa;
  const entrada = { fecha: instante, promesa: null };
  entrada.promesa = Promise.resolve().then(cargar).then(valor => {
    if (cache.get(clave) === entrada) {
      if (valor == null) cache.delete(clave);
      else entrada.fecha = ahora();
    }
    return valor;
  }, error => {
    if (cache.get(clave) === entrada) cache.delete(clave);
    throw error;
  });
  cache.set(clave, entrada);
  return entrada.promesa;
}
export function exigirInformeVigente(ctx, nodo) {
  if ((ctx.vigente && !ctx.vigente()) || (nodo && !nodo.isConnected)) throw new Error('La pantalla ha cambiado. Vuelve al informe antes de guardar.');
}

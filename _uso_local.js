// Medición propia: categorías fijas, sin textos, URLs, teclas ni contenido de tareas.
export const CONTROLES_USO = new Set(['boton','enlace','pestana','filtro','campo','copiar-ia','preparar-ia','abrir-tarea','guardar','buscar','menu','periodo','volver','exportar','cambiar-vista','ninguno']);
export function controlUso(el) {
  const marcado = el?.closest?.('[data-uso]')?.getAttribute('data-uso');
  if (CONTROLES_USO.has(marcado)) return marcado;
  if (el?.closest?.('#buscar')) return 'buscar';
  if (el?.closest?.('#menu-btn')) return 'menu';
  if (el?.closest?.('#barra-ctx')) return 'periodo';
  if (el?.closest?.('[role="tab"]')) return 'pestana';
  if (el?.closest?.('button')) return 'boton';
  if (el?.closest?.('a')) return 'enlace';
  if (el?.closest?.('select')) return 'filtro';
  if (el?.closest?.('input,textarea,[contenteditable="true"]')) return 'campo';
  return 'ninguno';
}
export function crearMedidorUso({enviar, sesion, ahora, visible, identidad, pantallas}) {
  let anterior = ahora(), ultimaActividad = anterior, visibleAntes = visible();
  let activo = 0, secuencia = 0, pantalla = 'app', quien = identidad();
  let ultimoEvento = -Infinity;
  const avanzar = () => {
    const t = ahora();
    if (visibleAntes) activo += Math.max(0, Math.min(t, ultimaActividad + 60000) - anterior);
    anterior = t; visibleAntes = visible();
  };
  const emitir = (accion, control = 'ninguno') => {
    avanzar();
    const dato = {sesion, secuencia: ++secuencia, pantalla, accion, control: CONTROLES_USO.has(control) ? control : 'ninguno', activo_ms: Math.min(30000, Math.floor(activo))};
    activo = 0;
    // La medición nunca impide trabajar, ni reintenta con contenido de negocio.
    try { Promise.resolve(enviar(dato, quien)).catch(() => {}); } catch { /* opcional */ }
  };
  return {
    pantalla(id) {
      const nuevo = pantallas.has(id) ? id : 'app'; const persona = identidad();
      if (nuevo === pantalla && persona.real === quien.real && persona.como === quien.como) return;
      emitir('latido'); pantalla = nuevo; quien = persona; activo = 0;
      emitir('abrir');
    },
    actividad(control = 'ninguno', registrar = false) {
      avanzar(); if (!visible()) return;
      ultimaActividad = ahora();
      if (registrar && (ultimaActividad - ultimoEvento >= 1000 || ['copiar-ia','preparar-ia','abrir-tarea'].includes(control))) { ultimoEvento = ultimaActividad; emitir('interaccion', control); }
    },
    latido() { emitir('latido'); },
    visibilidad(forzar=false) { avanzar(); if (forzar || !visible()) emitir('ocultar'); if (forzar) visibleAntes=false; },
    evento(accion, control = 'ninguno') { if (accion === 'error') emitir(accion, control); },
    abrir() { emitir('abrir'); },
  };
}
export function iniciarUsoLocal({enviar, identidad, pantallas, documento = document, ventana = window}) {
  if (!ventana.crypto?.randomUUID) return null;
  const m = crearMedidorUso({enviar, identidad, pantallas, sesion: ventana.crypto.randomUUID(), ahora: () => ventana.performance.now(), visible: () => documento.visibilityState === 'visible'});
  const tocar = e => m.actividad(controlUso(e.target), e.type === 'click' || e.type === 'change');
  for (const tipo of ['pointerdown','keydown','click','change','scroll']) documento.addEventListener(tipo, tocar, {passive:true,capture:true});
  documento.addEventListener('visibilitychange', () => m.visibilidad());
  ventana.addEventListener('pagehide', () => m.visibilidad(true));
  ventana.addEventListener('pageshow', () => m.visibilidad());
  ventana.setInterval(() => m.latido(), 30000);
  m.abrir(); return m;
}

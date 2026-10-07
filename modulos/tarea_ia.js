import { h, icono } from '../componentes.js';
import { cargarObjetivos } from './objetivos_comun.js';
import { prepararTareaIA } from './_tarea_ia.js';

// Un resultado booleano explícito evita anunciar «copiado» cuando el navegador deniega el portapapeles.
export async function copiarInstrucciones(texto, { clipboard = globalThis.navigator?.clipboard, fallback = null } = {}) {
  try { if (clipboard?.writeText) { await clipboard.writeText(texto); return true; } } catch { /* selección manual abajo */ }
  try { return fallback ? fallback(texto) === true : false; } catch { return false; }
}
export function bloqueTareaIA(E, t) {
  const { ctx } = E;
  const contenido = h('div', { class: 'pila', style: { gap: 'var(--s-2)', minWidth: '0' } });
  const det = h('details', { class: 'panel', 'data-tarea-ia': '' },
    h('summary', { class: 'bt', 'data-uso': 'preparar-ia', style: { minHeight: '44px', whiteSpace: 'normal' } }, icono('spark'), 'Preparar esta tarea con IA'), contenido);
  const vigente = () => det.isConnected && (typeof ctx.vigente !== 'function' || ctx.vigente());
  const ruta = `mi_trabajo/contexto_ia?tarea=${encodeURIComponent(t.id)}&persona=${encodeURIComponent(t.persona_id)}`;
  const coincide = r => String(r?.tarea?.id || '') === String(t.id) && r?.tarea?.persona_id === t.persona_id && (r?.tarea?.cli || null) === (t.cli || null);
  let preparado = false, cargando = false;
  det.addEventListener('toggle', async () => {
    if (!vigente() || !det.open || preparado || cargando) return;
    if (!ctx.servidor) { contenido.replaceChildren(h('p', { class: 'sub' }, 'Necesitas el servidor de la app para preparar contexto con permisos.')); return; }
    cargando = true;
    contenido.replaceChildren(h('p', { class: 'sub', role: 'status' }, 'Preparando el contexto que puedes ver…'));
    try {
      const c = (ctx.clientesVisibles || []).find(x => x.id === t.cli);
      let ficha = null, objetivo = null, contextoError = '', contextoTarea = await ctx.api(ruta);
      if (!vigente()) return;
      if (!coincide(contextoTarea)) throw new Error('La tarea no coincide con el contexto autorizado.');
      if (contextoTarea?.aviso) contextoError = contextoTarea.aviso;
      if (c) {
        const resultados = await Promise.allSettled([ctx.api(`cliente/${encodeURIComponent(c.id)}`), cargarObjetivos(ctx)]);
        if (!vigente()) return;
        if (resultados[0].status === 'fulfilled') ficha = resultados[0].value?.fuentes;
        if (resultados[1].status === 'fulfilled') objetivo = resultados[1].value?.get(c.id);
        if (resultados.some(r => r.status === 'rejected')) contextoError += ' No se pudo completar la lectura del contexto del cliente. Revisa los datos pendientes antes de usar la IA.';
      }
      let seleccionado = '';
      const construir = () => {
        const tareasIA = (E.D.tareas || []).map(x => String(x.id) === String(t.id) && x.persona_id === t.persona_id ? { ...x,
          descripcion: contextoTarea.tarea.descripcion || x.descripcion,
          descripcion_truncada: contextoTarea.tarea.descripcion_truncada || x.descripcion_truncada } : x);
        return prepararTareaIA({ tarea: t, tareasVisibles: tareasIA, clientesVisibles: ctx.clientesVisibles || [],
          nombreAsignado: ctx.nombre(t.persona_id), hoy: ctx.hoy, fuenteFecha: E.D.generado || E.D.fuentes?.tareas?.hora,
          ficha, objetivo, contextoError, descripcionFuente: contextoTarea.fuente, descripcionFecha: contextoTarea.leido,
          procedimientosIA: contextoTarea.procedimientos_ia, procedimientoElegido: seleccionado });
      };
      let r = construir();
      const texto = h('textarea', { readOnly: true, rows: 12, 'aria-label': `Instrucciones para IA de ${t.tarea}`, style: { width: '100%', minWidth: '0', maxWidth: '100%', boxSizing: 'border-box', resize: 'vertical', font: 'inherit' } });
      texto.value = r.texto;
      const estado = h('p', { class: 'sub', role: 'status', 'aria-live': 'polite' });
      const opciones = Array.isArray(contextoTarea.procedimientos_ia?.opciones) ? contextoTarea.procedimientos_ia.opciones : [];
      const selector = h('select', { 'aria-label': 'Checklist sugerida para esta tarea', style: { minHeight: '44px', minWidth: '0', maxWidth: '100%' }, on: { change: e => {
        if (!vigente() || !e.target.isConnected) return;
        seleccionado = e.target.value;
        try { r = construir(); texto.value = r.texto; estado.textContent = seleccionado ? 'Propuesta seleccionada · versión 134.1.0. Revisa fuente y límites en el bloque.' : 'Sin checklist seleccionada.'; }
        catch (_) { texto.value = ''; estado.textContent = 'Checklist sin confirmar; vuelve a preparar el contexto.'; }
      } } }, h('option', { value: '' }, 'Sin checklist · elegir es opcional'), ...opciones.map(p => h('option', { value: p.id }, `${p.titulo} · propuesta 134.1.0`)));
      const copiar = h('button', { type: 'button', class: 'bt pri', 'data-uso': 'copiar-ia', 'aria-label': `Copiar instrucciones para IA de ${t.tarea}`, style: { minHeight: '44px', whiteSpace: 'normal' }, on: { click: async () => {
        if (!vigente() || !copiar.isConnected || copiar.disabled) return;
        copiar.disabled = true;
        selector.disabled = true;
        estado.textContent = 'Comprobando permisos y fuente antes de copiar…';
        try {
          const actual = await ctx.api(ruta);
          if (!vigente()) return;
          if (!coincide(actual)) throw new Error('Contexto distinto');
          contextoTarea = actual;
          contextoError = actual.aviso || '';
          const nuevo = construir();
          if (nuevo.texto !== texto.value) {
            texto.value = nuevo.texto; r = nuevo;
            estado.textContent = 'El contexto cambió. Revisa el bloque actualizado y pulsa Copiar otra vez.';
            return;
          }
          if (!vigente()) return;
          const ok = await copiarInstrucciones(nuevo.texto, { fallback: () => {
            if (!vigente()) return false;
            texto.focus(); texto.select(); return document.execCommand('copy');
          } });
          if (!vigente()) return;
          if (ok) estado.textContent = 'Instrucciones copiadas. Checklist propuesta, sin activar IA ni conectores.';
          else { estado.textContent = 'No se pudo copiar. El bloque está seleccionado: cópialo manualmente con Ctrl+C o ⌘C.'; texto.focus(); texto.select(); }
        } catch (_) {
          if (!vigente()) return;
          texto.value = '';
          estado.textContent = 'No se confirmó el contexto o la checklist actual. Cierra y vuelve a preparar antes de copiar.';
          preparado = false;
        } finally {
          if (vigente()) { copiar.disabled = false; selector.disabled = false; }
        }
      } } }, icono('copy'), 'Copiar instrucciones');
      if (!vigente()) return;
      contenido.replaceChildren(h('p', { class: 'sub' }, 'Tarea y contexto para continuar en tu IA. Los accesos se comprueban en la IA de destino; aquí no se activa ningún conector.'),
        h('label', { class: 'pila' }, h('b', {}, 'Checklist sugerida · propuesta'), selector),
        h('p', { class: 'sub' }, contextoTarea.procedimientos_ia?.aviso || 'Sin checklist disponible con servicio y permiso confirmados.'),
        r.faltan.length ? h('div', {}, h('b', {}, 'Falta confirmar'), h('ul', {}, r.faltan.map(s => h('li', {}, s)))) : null,
        texto, copiar, estado);
      preparado = true;
    } catch (_) {
      if (vigente()) contenido.replaceChildren(h('p', { class: 'sub', role: 'alert' }, 'No se pudo confirmar el contexto autorizado. Cierra y vuelve a abrir para reintentar.'));
    } finally { cargando = false; }
  });
  return det;
}

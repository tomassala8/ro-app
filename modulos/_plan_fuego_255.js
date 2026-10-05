// Plan local versionado. Las capacidades y el recibo proceden del servidor, no del puesto visual.
import { h, chipEstado, panel } from '../componentes.js';

export function panelPlanFuego255(ctx, cid) {
  const raiz = h('section', { 'data-plan-fuego-255': cid });
  const vigente = () => raiz.isConnected && (typeof ctx.vigente !== 'function' || ctx.vigente());
  const nombre = id => ctx.nombre(id) || 'Persona registrada';
  let dto = null, pendiente = null, ocupado = false, borradorLocal = null;
  const validarLectura = d => {
    if (d?.cliente_id !== cid || !Number.isInteger(d.version) || d.version < 0 || !d.capacidades || !Array.isArray(d.historial)
        || (d.revision && (!d.plan || d.revision.plan_version !== d.plan.version))) {
      throw new Error('No se pudo verificar el plan de este cliente. No se muestra una respuesta incompatible.');
    }
    return d;
  };
  const estado = h('p', { class: 'sub', role: 'status', 'aria-live': 'polite' }, 'Leyendo el plan local…');
  raiz.append(estado);

  function pintar() {
    if (!vigente()) return;
    const caps = dto.capacidades || {}, plan = dto.plan, rev = dto.revision;
    const puedeEditar = !!caps.editar && !ctx.soloLectura;
    const puedeRevisar = !!caps.revisar && !ctx.soloLectura && !!plan;
    const chip = !plan ? chipEstado('gris', 'Sin plan registrado') : rev?.estado === 'visto'
      ? chipEstado('verde', `Visto · versión ${plan.version}`) : rev?.estado === 'pedir_cambios'
        ? chipEstado('ambar', 'Cambios pedidos') : chipEstado('ambar', 'Pendiente de revisión');
    const contenido = h('div', { style: { display:'grid', gap:'var(--s-3)' } });
    contenido.append(h('div', { class:'fila' }, chip,
      plan ? h('span', { class:'sub' }, `${nombre(plan.responsable_id)} · plazo ${plan.plazo}`) : null));
    if (plan) contenido.append(h('p', { style: { margin:0, whiteSpace:'pre-wrap' } }, plan.que));
    if (rev?.nota) contenido.append(h('p', { class:'sub', style:{ margin:0 } }, `Revisión: ${rev.nota}`));
    contenido.append(h('p', { class:'sub', style:{ margin:0 } }, 'Local en RO. «Visto» revisa este plan; no acredita ejecución ni entrega aceptada.'));

    const mensaje = h('p', { class:'sub', role:'status', 'aria-live':'polite', style:{ margin:0 } });
    const controles = [];
    const recargar = h('button', { type:'button', class:'bt', hidden:true, on:{ click:async () => {
      if (ocupado || !vigente()) return;
      ocupado=true;recargar.disabled=true;
      try {
        const actual=await ctx.api(`en-rojo/planes?cliente_id=${encodeURIComponent(cid)}`);
        if (!vigente()) return;
        dto=validarLectura(actual);pendiente=null;pintar();
      } catch(e) { if (vigente()) mensaje.textContent=e?.message || 'No se pudo leer la versión actual. Tu texto sigue aquí.'; }
      finally {ocupado=false;if(vigente())recargar.disabled=false;}
    } } },'Leer versión actual sin perder mi borrador');
    async function enviar(cuerpo) {
      if (ocupado || !vigente() || ctx.soloLectura) return;
      // Reintento idéntico conserva UUID y contenido, aunque se perdiera la respuesta anterior.
      if (!pendiente || JSON.stringify(pendiente.cuerpo) !== JSON.stringify(cuerpo)) {
        if (!globalThis.crypto?.randomUUID) { mensaje.textContent='No se puede identificar la solicitud. Recarga en un navegador compatible.';return; }
        pendiente = { cuerpo, accion_id:globalThis.crypto.randomUUID() };
      }
      ocupado = true; controles.forEach(x => { x.disabled=true; }); mensaje.textContent='Guardando en RO…';
      try {
        if (!vigente()) return;
        const resultado = await ctx.api('en-rojo/planes', { metodo:'POST', cuerpo:{ ...pendiente.cuerpo, accion_id:pendiente.accion_id } });
        if (!vigente()) return;
        if (!resultado?.ok || resultado.cliente_id !== cid || resultado.origen !== 'local' || resultado.recibo?.accion_id !== pendiente.accion_id) throw new Error('No se recibió confirmación de guardado local. Reintenta la misma solicitud.');
        dto=validarLectura(resultado); pendiente=null; borradorLocal=null; pintar();
      } catch(e) {
        if (vigente()) {
          mensaje.textContent=e?.message || 'No se pudo confirmar el guardado. Tu texto sigue aquí; puedes reintentar.';
          if (e?.status===409) { borradorLocal=cuerpo;recargar.hidden=false; }
        }
      } finally {
        ocupado=false;
        if (vigente()) controles.forEach(x => { x.disabled=false; });
      }
    }

    if (puedeEditar) {
      const borrador = borradorLocal?.operacion==='plan' ? borradorLocal : plan;
      const que = h('textarea', { rows:3, maxLength:1500, 'aria-label':'Qué se hará', placeholder:'Qué se hará y qué evidencia quedará' });que.value=borrador?.que || '';
      const quien = h('select', { 'aria-label':'Responsable del plan' }, h('option', { value:'' }, 'Elige responsable'),
        (caps.responsables || []).map(p => h('option', { value:p.id }, nombre(p.id))));quien.value=borrador?.responsable_id || '';
      const plazo = h('input', { type:'date', 'aria-label':'Plazo del plan' });plazo.value=borrador?.plazo || '';
      const guardar = h('button', { type:'button', class:'bt pri', on:{ click:() => enviar({ cliente_id:cid, operacion:'plan', expected_version:dto.version, que:que.value, responsable_id:quien.value, plazo:plazo.value }) } }, 'Guardar plan en RO');
      controles.push(que,quien,plazo,guardar);
      contenido.append(h('details', {}, h('summary', {}, plan ? 'Editar el plan' : 'Añadir plan'),
        h('div', { style:{ display:'grid', gap:'var(--s-2)', paddingTop:'var(--s-2)' } },
          h('label', {}, 'Qué se hará',que),h('div', { class:'fila' },h('label', {},'Quién',quien),h('label', {},'Plazo',plazo)),guardar)));
    }
    if (puedeRevisar) {
      const nota=h('textarea', { rows:2, maxLength:500, 'aria-label':'Nota de revisión', placeholder:'Qué hay que cambiar, si procede' });
      nota.value=borradorLocal?.operacion==='revision' ? borradorLocal.nota || '' : '';
      const revisar = estado => enviar({ cliente_id:cid, operacion:'revision', expected_version:dto.version, plan_version:plan.version, estado, nota:nota.value });
      const visto=h('button', { type:'button', class:'bt', on:{ click:() => revisar('visto') } }, 'Dar visto a esta versión');
      const cambios=h('button', { type:'button', class:'bt', on:{ click:() => revisar('pedir_cambios') } }, 'Pedir cambios');
      controles.push(nota,visto,cambios);
      contenido.append(h('details', {},h('summary', {},'Revisar esta versión'),nota,h('div', { class:'fila' },visto,cambios)));
    }
    contenido.append(mensaje,recargar);
    contenido.append(h('details', {},h('summary', {},`Historial local · ${dto.historial?.length || 0} registros${dto.historial_truncado ? ' (últimos 100)' : ''}`),
      h('ul', {},(dto.historial || []).map(e => h('li', {},
        `${e.hora} · ${nombre(e.actor_id)} · versión ${e.version} · `,
        e.operacion==='plan' ? `Plan: ${e.que} · ${nombre(e.responsable_id)} · ${e.plazo}` : `Revisión del plan ${e.plan_version}: ${e.estado === 'visto' ? 'visto' : 'cambios pedidos'}${e.nota ? ` · ${e.nota}` : ''}`)))));
    raiz.replaceChildren(panel({ titulo:'Plan del cliente', icono:'fire' },contenido));
  }
  // Iniciar cuando el nodo ya está unido a la ruta; no escribir tras cambio de identidad/pantalla.
  Promise.resolve().then(async () => {
    if (!vigente()) return;
    try {
      const lectura=await ctx.api(`en-rojo/planes?cliente_id=${encodeURIComponent(cid)}`);
      if (vigente()) { dto=validarLectura(lectura);pintar(); }
    } catch(e) {
      if (vigente()) estado.textContent=ctx.soloLectura ? 'Plan local no disponible en esta vista de lectura.' : `No se pudo leer el plan local: ${e?.message || 'vuelve a intentarlo'}`;
    }
  });
  return raiz;
}

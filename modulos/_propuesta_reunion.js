// modulos/_propuesta_reunion.js · «Proponer fecha» con el correo YA REDACTADO (3-oct-2026, feedback de Tomás).
// Antes: «Proponer fecha» pedía «¿Mandar?» y mandaba un texto fijo que nadie veía. Ahora abre un editor grande con el correo
// de propuesta ya escrito (voz de RO, firma de quien lo manda, 2-3 huecos reales de su agenda, motivo según el tipo y enlace
// de agenda si lo tiene), su nota de calidad en vivo, y «Enviar» → «✓ Enviado · Deshacer (8)». Pasa por envios.py (hoy,
// simulado y verificado; el servidor rechaza cualquier hueco sin rellenar).
// Servidor: POST /api/reuniones/propuesta y /api/reuniones/propuesta/calidad (fuentes_reuniones/propuesta_reunion.py).
//
//   botonProponerFecha(ctx, { cliente_id, cliente, tipo?, mini? })  → botón que abre el editor
//   abrirPropuestaReunion(ctx, { cliente_id, cliente, tipo? })      → abre el editor
import { h, icono, chipEstado, copiar } from '../componentes.js';
import { botonDeshacer } from './_deshacer.js';

// el mismo criterio que envios.py (HUECO_SIN_RELLENAR): un hueco así nunca sale
const RX_HUECO = /\[\s*(?:(?:completar|confirmar|rellenar|insertar|añadir|poner|d[ií]as?|horas?|fechas?|nombres?|enlaces?|link|url|importes?|cifras?|n[uú]mero|tel[eé]fono|empresa|despacho|cliente|motivo|causa|tema|plazo|mes|datos?|firma|cargo|huecos?|x+)(?![\p{L}\p{N}_])[^\]\n]{0,60}|…|\.{3})\s*\](?!\()/iu;
const NIVEL = { lista: ['verde', 'Lista para enviar'], revisar: ['ambar', 'Revísala antes'], rehacer: ['rojo', 'Hay que rehacerla'] };

export function botonProponerFecha(ctx, o) {
  return h('button', { type: 'button', class: `bt${o.mini === false ? '' : ' mini'}`, title: 'Abre el correo de propuesta ya redactado para retocarlo y enviarlo',
    on: { click: e => { e.stopPropagation(); abrirPropuestaReunion(ctx, o); } } },
  icono('cal', { clase: 's' }), o.texto || 'Proponer fecha');
}

function dialogo(id, titulo, sub) {
  document.getElementById(id)?.remove();
  const previo = document.activeElement;
  const cuerpo = h('div', { class: 'pila', style: { gap: 'var(--s-3, 12px)' } });
  let fondo;
  const cerrar = () => { fondo.remove(); previo?.focus?.(); };
  const caja = h('div', { class: 'paleta dialogo', role: 'dialog', 'aria-modal': 'true', 'aria-labelledby': `${id}-t`,
    style: { width: 'min(880px, 100%)', maxHeight: '92vh' } },
  h('div', { class: 'dialogo-cab' }, h('div', {}, h('h2', { id: `${id}-t` }, titulo), sub ? h('p', {}, sub) : null),
    h('button', { type: 'button', class: 'bt icono', 'aria-label': 'Cerrar', on: { click: () => cerrar() } }, icono('cerrar'))),
  cuerpo);
  fondo = h('div', { class: 'paleta-fondo dialogo-fondo', id, style: { paddingTop: '4vh' } }, caja);
  fondo.addEventListener('click', e => { if (e.target === fondo) cerrar(); });
  fondo.addEventListener('keydown', e => {
    if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); cerrar(); return; }
    if (e.key !== 'Tab') return;
    const foc = [...caja.querySelectorAll('button, a[href], input, textarea, select')].filter(x => !x.disabled && x.offsetParent !== null);
    if (!foc.length) return;
    if (e.shiftKey && document.activeElement === foc[0]) { e.preventDefault(); foc[foc.length - 1].focus(); }
    else if (!e.shiftKey && document.activeElement === foc[foc.length - 1]) { e.preventDefault(); foc[0].focus(); }
  });
  document.body.append(fondo);
  return { fondo, caja, cuerpo, cerrar };
}

export async function abrirPropuestaReunion(ctx, o) {
  const d = dialogo('propuesta-reunion', `Proponer fecha a ${o.cliente || 'el cliente'}`,
    'El correo ya está redactado: retócalo si quieres y pulsa «Enviar». Tienes 8 segundos para deshacer. Hoy los envíos están en simulación: no sale nada.');
  const est = { tipo: o.tipo || null, otros: 0, r: null };
  const zona = d.cuerpo;

  const cargar = async () => {
    zona.replaceChildren(h('p', { class: 'sub', role: 'status' }, 'Preparando el correo con tus huecos libres…'));
    try {
      est.r = await ctx.api('reuniones/propuesta', { metodo: 'POST', cuerpo: { cliente_id: o.cliente_id, tipo: est.tipo, otros: est.otros } });
      est.tipo = est.r.motivo;
      pintar();
    } catch (e) {
      zona.replaceChildren(h('p', { class: 'estado error', role: 'alert' }, `No he podido preparar el correo: ${e?.message || e}`),
        h('button', { type: 'button', class: 'bt', on: { click: cargar } }, 'Probar otra vez'));
    }
  };

  function pintar() {
    const r = est.r;
    // tipo de reunión (cambia el motivo, el asunto y la duración)
    const tipos = h('div', { class: 'fila', role: 'group', 'aria-label': 'Tipo de reunión', style: { flexWrap: 'wrap', gap: 'var(--s-1, 4px)' } },
      r.tipos.map(t => h('button', { type: 'button', class: `chip${t.id === r.motivo ? ' activo' : ''}`, 'aria-pressed': String(t.id === r.motivo),
        style: { minHeight: '32px', cursor: 'pointer', ...(t.id === r.motivo ? { background: 'var(--accent-soft)', color: 'var(--accent-ink, var(--accent))', borderColor: 'var(--accent)', fontWeight: '600' } : {}) }, on: { click: () => { if (t.id !== est.tipo) { est.tipo = t.id; est.otros = 0; cargar(); } } } },
      `${t.nombre} · ${t.minutos} min`)));
    // huecos propuestos
    const huecos = h('div', { class: 'pila', style: { gap: 'var(--s-1, 4px)' } },
      h('div', { class: 'fila', style: { justifyContent: 'space-between', flexWrap: 'wrap', gap: 'var(--s-2, 8px)' } },
        h('span', { class: 'titulo-seccion' }, r.huecos.length ? `Huecos propuestos (hora peninsular)` : 'Sin huecos libres en las próximas dos semanas'),
        h('button', { type: 'button', class: 'bt mini', on: { click: () => { est.otros += 1; cargar(); } } }, icono('cal', { clase: 's' }), 'Otros huecos')),
      r.huecos.length ? h('div', { class: 'fila', style: { flexWrap: 'wrap', gap: 'var(--s-1, 4px)' } },
        r.huecos.map(x => h('span', { class: 'chip' }, x.texto + (x.suya ? ` · ${x.suya}` : '')))) : null,
      h('small', { class: 'sub' }, r.fuente_huecos));
    // asunto y cuerpo (editor grande)
    const asunto = h('input', { type: 'text', value: r.asunto, 'aria-label': 'Asunto', style: { width: '100%', font: 'inherit', fontSize: '15px', padding: '10px 12px', border: '1px solid var(--line)', borderRadius: 'var(--r-m, 8px)', background: 'var(--card)' } });
    const ta = h('textarea', { rows: 16, 'aria-label': 'Texto del correo', spellcheck: 'true',
      style: { width: '100%', minHeight: '340px', font: 'inherit', fontSize: '15px', lineHeight: '1.55', padding: '12px', border: '1px solid var(--line)', borderRadius: 'var(--r-m, 8px)', background: 'var(--card)', resize: 'vertical', boxSizing: 'border-box' } });
    ta.value = r.cuerpo;
    const firma = r.firma.en_texto ? null
      : h('div', { class: 'sub', style: { padding: '8px 12px', background: 'var(--card-2)', borderRadius: 'var(--r-m, 8px)' } },
        h('span', { style: { display: 'block', font: 'var(--t-eyebrow)', textTransform: 'uppercase', letterSpacing: '.06em' } }, 'Firma (la añade Desk al enviar)'),
        `${r.firma.nombre}${r.firma.puesto ? ` · ${r.firma.puesto}` : ''} · Ranking Online`);
    // calidad en vivo
    const notaCaja = h('div', { class: 'pila', role: 'status', 'aria-live': 'polite', style: { gap: 'var(--s-1, 4px)' } });
    const pintarNota = c => {
      const [color, txt] = NIVEL[c.nivel] || NIVEL.revisar;
      notaCaja.replaceChildren(...[h('div', { class: 'fila', style: { gap: 'var(--s-2, 8px)', flexWrap: 'wrap' } },
        chipEstado(color, `Calidad ${c.nota} · ${txt}`), h('small', { class: 'sub' }, `${c.palabras} palabras · ${c.huecos} huecos con día y hora`)),
      c.faltas?.length ? h('ul', { class: 'lista-i', style: { margin: 0 } }, c.faltas.slice(0, 6).map(f => h('li', {}, f))) : null].filter(Boolean));
    };
    pintarNota(r.calidad);
    const aviso = h('p', { class: 'estado error', role: 'alert', hidden: true });
    let t = 0;
    const revisar = () => {
      const m = (ta.value + '\n' + asunto.value).match(RX_HUECO);
      aviso.hidden = !m; aviso.textContent = m ? `Queda un hueco sin rellenar: ${m[0]}. Complétalo o bórralo: así no sale.` : '';
      clearTimeout(t);
      t = setTimeout(async () => {
        try { pintarNota(await ctx.api('reuniones/propuesta/calidad', { metodo: 'POST', cuerpo: { cliente_id: o.cliente_id, asunto: asunto.value, cuerpo: ta.value } })); }
        catch { /* la nota se queda como estaba */ }
      }, 600);
    };
    ta.addEventListener('input', revisar); asunto.addEventListener('input', revisar);

    const resultado = h('div', { class: 'sub', role: 'status', 'aria-live': 'polite' });
    const enviar = botonDeshacer({
      texto: 'Enviar', hecho: 'Enviado', icono: 'send', pri: true, mini: false, soloLectura: ctx.soloLectura,
      titulo: 'Deja el correo en la cola de envíos (hoy, simulado). 8 segundos para deshacer.',
      validar: () => {
        if (!ta.value.trim()) return 'El correo está vacío.';
        if (!asunto.value.trim()) return 'Falta el asunto.';
        const m = (ta.value + '\n' + asunto.value).match(RX_HUECO);
        if (m) return `Queda un hueco sin rellenar: ${m[0]}.`;
        ta.readOnly = true; asunto.readOnly = true;          // lo que sale es lo que se ve
        return null;
      },
      alAnular: () => { ta.readOnly = false; asunto.readOnly = false; ta.focus(); },
      alHacer: async () => {
        const a = await ctx.accion({ herramienta: 'desk', tipo: 'correo', objeto: r.objeto, cliente_id: o.cliente_id, texto: ta.value,
          vista_previa: { asunto: asunto.value, plantilla: 'propuesta_reunion', tipo_reunion: r.motivo, huecos: r.huecos.map(x => x.inicio),
            firma_en_texto: r.firma.en_texto, para: r.para } });
        try {
          const l = await ctx.api('envios');
          const e = (l.envios || []).filter(x => x.cliente_id === o.cliente_id && x.asunto === asunto.value).sort((x, y) => y.id - x.id)[0];
          resultado.textContent = e ? `En la cola de envíos (n.º ${e.id}) · ${e.estado === 'simulado' ? 'simulado: no ha salido' : e.estado} · para: ${e.destinatario?.nombre || r.para}. Lo ves en Sistema › Envíos.`
            : `En la cola de acciones (n.º ${a?.id ?? '—'}) · simulado: no ha salido.`;
        } catch { resultado.textContent = `En la cola (n.º ${a?.id ?? '—'}) · simulado: no ha salido.`; }
        return 'Enviado (simulado)';
      },
    });
    // la barra de «Enviar» queda pegada abajo del diálogo: se ve siempre, también en el móvil
    const acciones = h('div', { class: 'fila', style: { gap: 'var(--s-2, 8px)', flexWrap: 'wrap', alignItems: 'center', position: 'sticky', bottom: '-20px', background: 'var(--card)', padding: '12px 0', borderTop: '1px solid var(--line)', zIndex: '1' } },
      enviar,
      h('button', { type: 'button', class: 'bt', on: { click: () => copiar(`${asunto.value}\n\n${ta.value}`, 'Correo copiado') } }, icono('copy', { clase: 's' }), 'Copiar'),
      h('button', { type: 'button', class: 'bt', on: { click: () => cargar() } }, icono('spark', { clase: 's' }), 'Volver a redactar'));

    zona.replaceChildren(...[
      h('div', { class: 'fila', style: { gap: 'var(--s-3, 12px)', flexWrap: 'wrap' } },
        h('small', { class: 'sub' }, h('b', {}, 'Para: '), r.para),
        h('small', { class: 'sub' }, h('b', {}, 'Firma: '), r.firma.texto),
        r.otra_zona ? h('small', { class: 'sub' }, h('b', {}, 'Tu hora: '), 'los huecos van en hora peninsular (la del cliente); al lado, la tuya') : null),
      h('div', { class: 'pila', style: { gap: 'var(--s-1, 4px)' } }, h('span', { class: 'titulo-seccion' }, 'Tipo de reunión'), tipos),
      huecos,
      h('label', { class: 'pila', style: { gap: 'var(--s-1, 4px)' } }, h('span', { class: 'titulo-seccion' }, 'Asunto'), asunto),
      h('label', { class: 'pila', style: { gap: 'var(--s-1, 4px)' } }, h('span', { class: 'titulo-seccion' }, 'Correo'), ta),
      firma, aviso, notaCaja, resultado, acciones].filter(Boolean));
    ta.focus({ preventScroll: true });
    ta.setSelectionRange(0, 0);
  }
  await cargar();
}

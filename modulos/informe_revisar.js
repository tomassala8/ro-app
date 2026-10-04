import {metaInforme291} from './_meta_informe_291.js';
// modulos/informe_revisar.js · Ronda U (3-oct, carril U2 · cambio #8 del 50): «Revisar y preparar» el informe mensual en
// UNA pantalla. Lo usan Informes mensuales (acción de la fila) e Informe del cliente (barra de arriba).
//
// En el panel: las cifras del informe del mes frente al periodo anterior y al objetivo, los avisos que bloquean el PDF,
// el análisis del mes (5 apartados; «Proponer con las cifras» lo rellena; con la clave de Anthropic lo redactará la IA),
// «Marcar revisado» (interno: al primer clic, con Deshacer 8 s) y «Guardar borrador» en la app. El envío del PDF
// sigue pendiente: el descriptor del adjunto no es un archivo. Se descarga y envía desde Desk.
//
// Todo se guarda a nombre de la pantalla «Informe del cliente» (modulo informe-cliente) para que el análisis, la marca de
// revisado y el envío se vean igual desde las dos pantallas. Diseño estricto: clases comunes y tokens.

import { h, fmt, icono, chipEstado, vacioLinea, avisoFlotante, variacion } from '../componentes.js';

/** Cifra compacta para la columna estrecha del panel: icono, etiqueta, valor y ▲/▼ frente al mes anterior. */
function tile({ icono: ico, etiqueta, valor, comparacion, contexto }) {
  const d = comparacion?.delta;
  const bueno = d == null ? null : (comparacion.mejorSi === 'bajo' ? d <= 0 : d >= 0);
  return h('div', { style: { border: 'var(--borde-suave)', borderRadius: 'var(--r-m)', padding: 'var(--s-2) var(--s-3)', display: 'grid', gap: '2px', minWidth: '0' } },
    h('span', { class: 'sub', style: { display: 'inline-flex', alignItems: 'center', gap: 'var(--s-1)' } }, icono(ico, { clase: 's' }), etiqueta),
    h('b', { style: { font: 'var(--t-h2, var(--t-h3))' } }, valor ?? 'Sin dato'),
    d != null && Number.isFinite(d) ? h('span', { style: { font: 'var(--t-meta)', color: bueno ? 'var(--good-ink)' : 'var(--bad-ink)' } }, `${d >= 0 ? '▲' : '▼'} ${fmt.num(Math.abs(d), 0)} % ${comparacion.texto}`) : null,
    contexto ? h('span', { class: 'sub' }, contexto) : null);
}
import { logoInforme, exigirInformeVigente } from './_informe_evidencia.js';
import { botonDeshacer } from './_deshacer.js';
import { filaCliente, invalidarAccionesInforme, analisisDe, borrador, avisosDe, bloqueaPDF, APARTADOS, RE_LEAD, enlacePeriodo } from './informe.js';

const MOD = 'informe-cliente';
import { estadoInforme, textoEstadoInforme } from './_estado_informe.js';
export { estadoInforme } from './_estado_informe.js';
const MES3 = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];
const dia = iso => { if (!iso) return '—'; const d = new Date(String(iso).length <= 10 ? `${iso}T12:00:00` : String(iso).replace(' ', 'T')); return Number.isNaN(+d) ? String(iso) : `${d.getDate()}-${MES3[d.getMonth()]}`; };

/** Escribe una acción a nombre de «Informe del cliente» (sin pasar por el módulo que pinta). */
const accionInforme = (ctx, a, nodo) => { exigirInformeVigente(ctx, nodo); if (ctx.soloLectura) throw new Error('Esta vista es de consulta.'); return ctx.api('acciones', { metodo: 'POST', cuerpo: { modulo: MOD, ...a } }); };

export async function accionesInforme(ctx) {
  if (!ctx.servidor) return [];
  try { return (await ctx.api(`acciones?modulo=${MOD}`))?.acciones || []; } catch { return []; }
}


function cifras(ctx, c, f, P) {
  const inv = ctx.ver({ tipo: 'inversion', cliente_id: c.id }).ok;
  const cmp = (a, b, mejorSi) => (a != null && b ? { delta: variacion(a, b), pct: true, texto: 'frente al mes anterior', mejorSi } : null);
  const T = [], L = [];
  const g = f.ga4?.actual, ga = f.ga4?.anterior;
  if (g) { T.push(tile({ icono: 'globe', etiqueta: 'Usuarios de la web', valor: fmt.num(g.usuarios), comparacion: cmp(g.usuarios, ga?.usuarios), medible: 'hoy' })); L.push(`${fmt.num(g.usuarios)} usuarios en la web`); }
  const s = f.gsc?.web?.actual, sa = f.gsc?.web?.anterior;
  if (s) { T.push(tile({ icono: 'buscar', etiqueta: 'Clics desde Google', valor: fmt.num(s.clics), comparacion: cmp(s.clics, sa?.clics), medible: 'hoy' })); L.push(`${fmt.num(s.clics)} clics desde Google`); }
  const m = f.meta?.actual, ma = f.meta?.anterior;
  if (m) {
    const mm=metaInforme291(m,f.fuentes?.meta,P,ctx.hoy,c);
    T.push(tile({icono:'target',etiqueta:mm.etiqueta,valor:mm.resultados===null?'Sin dato':fmt.num(mm.resultados),contexto:mm.detalle})); L.push(`${mm.resultados===null?'Sin dato':fmt.num(mm.resultados)} ${mm.etiqueta.toLowerCase()}`);
    if(inv)T.push(tile({icono:'euro',etiqueta:'Coste por evento lead',valor:mm.cpl===null?'Sin dato':fmt.eur(mm.cpl,2),contexto:'Requiere evento, cuenta, moneda y periodo acreditados'}));
  }
  const ci = f.embudo?.citas;
  if (ci) { T.push(tile({ icono: 'cal', etiqueta: 'Citas en el CRM', valor: fmt.num(ci.agendadas || 0), contexto: `${fmt.num(ci.celebradas || 0)} celebradas`, medible: 'hoy' })); L.push(`${fmt.num(ci.agendadas || 0)} citas`); }
  return { T, L };
}

/**
 * panelRevisar(ctx, { c, pid, ticketAnterior }, { alCerrar, alCambio }) → <section> con todo el flujo.
 * c = cliente de ctx.clientes; pid = '2026-09'; ticketAnterior = n.º de Desk del informe anterior (para seguir el hilo).
 */
export async function panelRevisar(ctx, { c, pid, ticketAnterior } = {}, { alCerrar, alCambio } = {}) {
  const caja = h('section', { class: 'panel', 'data-revisar-informe': `${c.id}/${pid}`, 'aria-label': `Revisar y preparar el informe de ${c.nombre}`, style: { scrollMarginTop: '96px', minWidth: '0' } },
    h('div', { class: 'cuerpo' }, vacioLinea('Abriendo el informe del mes…', { icono: 'clock' })));
  const [comun, f, acc] = await Promise.all([ctx.datosModulo('informe/comun').catch(() => null), filaCliente(ctx, pid, c.id).catch(() => null), accionesInforme(ctx)]);
  if (ctx.vigente && !ctx.vigente()) return caja;
  const P = (comun?.periodos || []).find(p => p.id === pid) || { id: pid, texto: pid };
  const cerrar = h('button', { type: 'button', class: 'bt', 'aria-label': 'Cerrar el panel', on: { click: () => alCerrar?.() } }, icono('cerrar'), 'Cerrar');
  if (!f) {
    caja.replaceChildren(h('div', { class: 'cuerpo pila' }, h('div', { class: 'fila', style: { justifyContent: 'space-between' } }, h('b', {}, `Informe de ${c.nombre} · ${P.texto}`), cerrar),
      vacioLinea('Este cliente no tiene informe de la app para ese mes (sin cuentas emparejadas). Mándalo como siempre y márcalo «Enviado por otra vía».', { icono: 'plug', quien: 'Agus (emparejar sus cuentas)' })));
    return caja;
  }
  const ana = analisisDe(acc.filter(a => a.cliente_id === c.id), c.id, pid);
  const est = estadoInforme(acc, c.id, pid);
  const av = avisosDe(f, P, ana);
  const bloqueo = bloqueaPDF(av);
  const { T, L } = cifras(ctx, c, f, P);
  const S = { f, P };

  // ---- análisis: 5 apartados (los del informe), con lo guardado o vacío ----
  const campos = {};
  const form = h('div', { class: 'pila', style: { gap: 'var(--s-2)' } });
  for (const [k, t] of APARTADOS) {
    campos[k] = h('textarea', { rows: k === 'mes' ? 3 : 2, 'aria-label': t, maxLength: 800 });
    campos[k].value = ana.actual?.apartados?.[k] || '';
    form.append(h('label', { class: 'campo' }, h('span', { class: 'campo-et' }, t), campos[k]));
  }
  const err = h('p', { class: 'sub', role: 'alert', style: { margin: '0' } });
  const apartados = () => Object.fromEntries(Object.entries(campos).map(([k, el]) => [k, el.value.trim()]).filter(([, v]) => v));
  const cambiado = () => JSON.stringify(apartados()) !== JSON.stringify(Object.fromEntries(Object.entries(ana.actual?.apartados || {}).filter(([, v]) => v)));
  const guardarAnalisis = async () => {
    exigirInformeVigente(ctx, caja);
    const ap = apartados();
    const todo = Object.values(ap).join(' ');
    if (!todo) throw new Error('El análisis está vacío: escríbelo o pulsa «Proponer con las cifras».');
    if (RE_LEAD.test(todo)) throw new Error('El análisis lleva un correo o un teléfono: quítalo (los datos de leads no van en el informe).');
    if (!cambiado()) return null;
    const r = await accionInforme(ctx, { herramienta: 'app', tipo: 'analisis_mes', objeto: `informe/${c.id}/${pid}`, cliente_id: c.id, texto: todo.slice(0, 2000),
      vista_previa: { periodo: pid, periodo_texto: P.texto, apartados: ap, que_hace: 'Análisis del mes guardado desde «Revisar y preparar». No se envía a nadie: el envío del PDF desde la app está pendiente.' } }, caja);
    invalidarAccionesInforme(ctx);
    exigirInformeVigente(ctx, caja);
    ana.actual = { apartados: ap, quien: ctx.real.id, creada: new Date().toISOString() };
    pintarSub();
    return r;
  };
  const proponer = h('button', { type: 'button', class: 'bt', title: 'Rellena los huecos vacíos con las cifras del informe (reglas). Con la clave de Anthropic, lo redactará la IA.',
    on: { click: () => { const b = borrador(S); let n = 0; for (const k of Object.keys(b)) if (campos[k] && !campos[k].value.trim() && b[k]) { campos[k].value = b[k]; n += 1; } avisoFlotante(n ? 'Propuesta con las cifras en los huecos vacíos: revísala' : 'No había huecos vacíos'); } } },
  icono('spark'), 'Proponer con las cifras');

  // ---- borrador del correo para enviar desde Desk, adjuntando el PDF a mano ----
  const mesTxt = P.texto.replace(/ \d{4}$/, '').toLowerCase();
  const asunto = `Informe de resultados de ${mesTxt} · ${c.nombre}`;
  const pdf = `Informe ${c.nombre} · ${P.texto}.pdf`;
  const cuerpoCorreo = () => {
    const ap = apartados();
    return [`Hola,`, '', `Os mando el informe de resultados de ${mesTxt}${L.length ? `: ${L.join(', ')}` : ''}.`, ap.mes ? `\n${ap.mes}` : '', ap.pasos ? `\nPróximos pasos: ${ap.pasos}` : '',
      '', 'Lo tenéis entero en el PDF adjunto. Cualquier duda comentamos,', '', `${ctx.nombre(ctx.real.id)} · Ranking Online`].filter(x => x !== '').join('\n').replace(/\n{3,}/g, '\n\n');
  };
  const vista = h('pre', { style: { whiteSpace: 'pre-wrap', margin: '0', font: 'var(--t-cuerpo)', background: 'var(--card-2)', border: 'var(--borde-suave)', borderRadius: 'var(--r-m)', padding: 'var(--s-3)', maxHeight: '220px', overflow: 'auto' } });
  const refrescar = () => { vista.textContent = `Asunto: ${asunto}\nPDF para adjuntar desde Desk: ${pdf}\n\n${cuerpoCorreo()}`; };
  form.addEventListener('input', refrescar);
  refrescar();

  // ---- acciones de la barra ----
  const subAna = h('span', { class: 'sub', style: { display: 'block' } });
  const pintarSub = () => { subAna.textContent = ana.actual ? `Análisis de ${ctx.nombre(ana.actual.quien)} · ${dia(ana.actual.creada)}` : 'Sin análisis todavía: «Proponer con las cifras» lo empieza'; };
  pintarSub();
  const zonaRev = h('span', {});
  const pintarRev = () => zonaRev.replaceChildren(est.revisado
    ? chipEstado('verde', `Revisado · ${ctx.nombre(est.revisado.quien)} · ${dia(est.revisado.creada)}`)
    : botonDeshacer({ texto: 'Marcar revisado', icono: 'ok', hecho: 'Revisado', mini: false, soloLectura: ctx.soloLectura,
      titulo: 'Interno: guarda el análisis y deja tu firma de revisión. Tienes 8 s para deshacer',
      alHacer: async () => {
        exigirInformeVigente(ctx, caja);
        await guardarAnalisis();
        exigirInformeVigente(ctx, caja);
        const r = await accionInforme(ctx, { herramienta: 'app', tipo: 'marcar', objeto: `informe/${c.id}/${pid}:revisado`, cliente_id: c.id, texto: `Informe de ${P.texto} de ${c.nombre} revisado`, vista_previa: { periodo: pid, informe: `informe/${c.id}/${pid}` } }, caja);
        invalidarAccionesInforme(ctx);
        exigirInformeVigente(ctx, caja);
        est.revisado = { quien: ctx.real.id, creada: new Date().toISOString(), id: r?.id };
        await alCambio?.(est);
        exigirInformeVigente(ctx, caja);
        setTimeout(() => { if (caja.isConnected && (!ctx.vigente || ctx.vigente())) pintarRev(); }, 1600);
        return 'Revisado · queda en el rastro';
      } }));
  pintarRev();
  const zonaEnv = h('span', {});
  const pintarEnv = () => {
    const estadoTexto = textoEstadoInforme(est);
    const guardar = h('button', { type: 'button', class: 'bt pri', disabled: ctx.soloLectura || bloqueo || null,
      title: bloqueo ? 'Hay un aviso rojo: revisa las cuentas y los datos antes de preparar el informe' : 'Guarda el correo y la referencia del PDF en la app. No envía nada.',
      on: { click: async () => {
        if (!caja.isConnected || (ctx.vigente && !ctx.vigente()) || ctx.soloLectura || bloqueo) return;
        guardar.disabled = true;
        err.textContent = '';
        try {
          await guardarAnalisis();
          exigirInformeVigente(ctx, caja);
          const texto = cuerpoCorreo();
          const r = await accionInforme(ctx, { herramienta: 'app', tipo: 'borrador_informe', objeto: `informe/${c.id}/${pid}`, cliente_id: c.id, texto,
            vista_previa: { asunto, cuerpo: texto, informe: `informe/${c.id}/${pid}`, periodo: pid, periodo_texto: P.texto, hilo: ticketAnterior || null,
              apartados: apartados(), adjunto: { tipo: 'pdf', nombre: pdf, periodo: pid, pendiente: true,
                como: 'Descarga el PDF de este periodo y adjúntalo manualmente desde Desk.' } } }, caja);
          invalidarAccionesInforme(ctx);
          exigirInformeVigente(ctx, caja);
          est.borrador = { quien: ctx.real.id, creada: new Date().toISOString(), id: r?.id };
          avisoFlotante('Borrador guardado en la app · no enviado');
          await alCambio?.(est);
          exigirInformeVigente(ctx, caja);
          pintarEnv();
        } catch (e) { if (caja.isConnected && (!ctx.vigente || ctx.vigente())) err.textContent = `No se guardó el borrador: ${e.message}`; }
        finally { if (caja.isConnected && (!ctx.vigente || ctx.vigente())) guardar.disabled = !!ctx.soloLectura || bloqueo; }
      } } }, icono('doc'), 'Guardar borrador');
    zonaEnv.replaceChildren(...(estadoTexto ? [chipEstado(est.enviado ? 'verde' : est.fallido ? 'rojo' : 'ambar', estadoTexto)] : []), guardar);
  };
  pintarEnv();
  const verPdf = h('a', { class: 'bt', href: enlacePeriodo(P, 'ant', c.id) || `#/informe-cliente/${c.id}/${pid}/ant`, title: `Abrir ${P.texto} para descargar su PDF` }, icono('doc'), 'Abrir informe');

  const barra = h('div', { class: 'fila', role: 'toolbar', 'aria-label': 'Revisar y preparar', 'data-barra-acciones': '',
    style: { justifyContent: 'space-between', gap: 'var(--s-2) var(--s-3)', background: 'var(--card)', padding: 'var(--s-3) var(--relleno)', borderBottom: 'var(--borde-suave)' } },
    h('div', { style: { minWidth: '0', flex: '1 1 240px' } }, h('b', { style: { font: 'var(--t-h3)' } }, `Informe de ${c.nombre} · ${P.texto}`),
      subAna),
    h('div', { class: 'fila', style: { gap: 'var(--s-2)' } }, zonaRev, zonaEnv, verPdf, cerrar));

  caja.replaceChildren(barra,
    h('div', { class: 'cuerpo pila', style: { gap: 'var(--s-4)' } },
      h('div', { class: 'aviso info', role: 'status' }, icono('info'), h('span', {}, 'El envío del PDF desde la app está pendiente. El informe final exige el logo del cliente cargado y evidencia de ejecución con sus límites de cobertura. Descarga el PDF y envíalo desde Desk.')),
      !logoInforme(c) ? h('div', { class: 'aviso', role: 'alert' }, 'Falta el logo real del cliente. Puedes preparar el borrador interno; la exportación del informe final queda bloqueada hasta añadirlo.') : null,
      bloqueo ? h('div', { class: 'aviso', role: 'alert' }, h('span', { class: 'ico' }, icono('alert')), h('span', {}, h('b', {}, 'No se puede preparar: '), av.filter(a => a.color === 'rojo').map(a => a.texto).join(' '))) : null,
      h('div', { class: 'dos' },
        h('div', { class: 'pila', style: { minWidth: '0', gap: 'var(--s-3)' } },
          h('div', { class: 'fila', style: { justifyContent: 'space-between' } }, h('span', { class: 'titulo-seccion' }, 'Qué decirle al cliente este mes'), proponer), form, err),
        h('div', { class: 'pila', style: { minWidth: '0', gap: 'var(--s-3)' } },
          h('span', { class: 'titulo-seccion' }, `Cifras de ${mesTxt}`), T.length ? h('div', { style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 150px), 1fr))', gap: 'var(--s-2)' } }, T) : vacioLinea('Sin cifras para este cliente en el informe.', { icono: 'grafico' }),
          av.filter(a => a.color !== 'rojo').length ? h('p', { class: 'sub', style: { margin: '0' } }, `Avisos: ${av.filter(a => a.color !== 'rojo').map(a => a.texto).slice(0, 3).join(' · ')}`) : null,
          h('span', { class: 'titulo-seccion' }, 'Borrador para Desk (adjunta el PDF al enviarlo)'), vista))));
  queueMicrotask(() => { if (!caja.isConnected || (ctx.vigente && !ctx.vigente())) return; try { caja.scrollIntoView({ block: 'start' }); } catch { /* nada */ } });
  return caja;
}

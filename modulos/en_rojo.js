// modulos/en_rojo.js · M2 «En rojo» (inicio común, pedido por Mili).
// Ronda de arreglos (2-oct noche): se pinta con la VERDAD ÚNICA por cliente (data/verdad/clientes.json):
//   gravedad crítico · atención · bien, motivos, account, nuevo, encendido, reuniones, bloqueos callados y fuga.
//   Ya no con las alarmas del panel v27 (53 de 68 «en rojo» hacía que el rojo no significara nada).
// Lista común para todos (cliente, gravedad, motivo sin cifras y responsable; sin dinero ni datos de leads).
// Detalle (#/en-rojo/<cliente>) solo para quien puede abrir el cliente: motivos con cifras y atajos «Abrir en …».
// Atajos: data/en_rojo/atajos.json (fuentes_en_rojo/generar_atajos.py), recortado por cliente en servir.py.

import {
  h, fmt, tile, tiles, listaLoPrimero, tablaDensa, chipEstado, chipsFiltro, selectorCliente, barraEtapas,
  lineaTiempo, vacio, avisoParcial, logoCliente, candado, panel, frescura, icono, iniciales, limpiaTexto,
} from '../componentes.js';
// Ronda U (50 #4): «Marcar visto» al primer clic con «Deshacer» 8 s (antes «¿Lo has visto? Sí, visto»); el consejo de la
// IA, plegado y debajo de «Lo primero hoy»; y, para Coti, «Visto» también en cada fila crítica de la lista.
import { botonDeshacer } from './_deshacer.js';
import { consejoCompacto, filasFlexibles } from './_trabajo.js';
import { panelPlanFuego255 } from './_plan_fuego_255.js';
const filasLP = (...a) => filasFlexibles(listaLoPrimero(...a));   // Ronda U: botones debajo cuando no caben, a cualquier ancho

// Revisión 44 (textos cortados): lo que la pantalla corta con «…» (una línea o el límite de líneas) lleva el texto entero
// en el title, para que la regla de la tarjeta o el nombre largo no se pierdan. Mira el contenedor mientras se pinta.
const _SEL_CORTE = '.tile .tx, .tile .tt span, .tile em, .det, .mot, .sub, .t, td, .chip, summary, b, small';
function vigilarCortes(raiz) {
  if (!raiz || raiz.__cortes) return;
  raiz.__cortes = true;
  let t = 0;
  const mirar = () => { t = 0; for (const el of raiz.querySelectorAll(_SEL_CORTE)) {
    if (el.title || el.closest('[title]') !== null && el.closest('[title]') !== el || !el.isConnected) continue;
    if (el.scrollWidth > el.clientWidth + 1 || el.scrollHeight > el.clientHeight + 2) { const s = el.textContent.trim(); if (s && s.length > 8) el.title = s; } } };
  new MutationObserver(() => { if (!t) t = setTimeout(mirar, 400); }).observe(raiz, { childList: true, subtree: true });
  if (typeof ResizeObserver !== 'undefined') new ResizeObserver(() => { if (!t) t = setTimeout(mirar, 400); }).observe(raiz);
}

// Revisión 44 (§2.3): fechas con el formato único de la app: «2-oct» y «2-oct, 17:34» (nunca «2 oct» ni «sept»).
const _MES3 = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];
const _fechaDe = iso => (iso ? new Date(String(iso).length <= 10 ? `${iso}T12:00:00` : String(iso).replace(' ', 'T')) : null);
const fDiaRO = iso => { const d = _fechaDe(iso); return !d ? '—' : Number.isNaN(+d) ? String(iso) : `${d.getDate()}-${_MES3[d.getMonth()]}`; };
const fDiaHoraRO = iso => { const d = _fechaDe(iso); return !d ? '—' : Number.isNaN(+d) ? String(iso) : `${d.getDate()}-${_MES3[d.getMonth()]}, ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`; };

const GRAV = {
  critico: { texto: 'Crítico', color: 'rojo', orden: 0, icono: 'fire' },
  atencion: { texto: 'Vigilar', color: 'ambar', orden: 1, icono: 'ojo' },   // §2.1
  bien: { texto: 'Bien', color: 'verde', orden: 2, icono: 'ok' },
};
const grav = g => GRAV[g] || { texto: 'Sin dato', color: 'gris', orden: 3, icono: 'info' };

// Icono y atajo principal según de qué va el motivo (los textos salen de la verdad única).
function claseMotivo(t = '') {
  const m = t.toLowerCase();
  if (m.includes('fuga') || m.includes('no llegan al crm')) return { icono: 'plug', atajo: 'ghl' };
  if (m.includes('correo')) return { icono: 'mail', atajo: 'desk' };
  if (m.includes('alta') || m.includes('encend')) return { icono: 'rocket', atajo: 'meta' };
  if (m.includes('bloque')) return { icono: 'candado', atajo: 'clickup' };
  if (m.includes('reunión')) return { icono: 'video', atajo: 'clickup' };
  if (m.includes('account')) return { icono: 'persona', atajo: 'clickup' };
  if (m.includes('captación') || m.includes('publicidad') || m.includes('leads')) return { icono: 'target', atajo: 'meta' };
  return { icono: 'alert', atajo: 'clickup' };
}
// «Bloqueo callado: 50.8 días» → «Bloqueo callado: 51 días» (decimales con punto fuera; texto limpio de códigos).
/** Quita las señales que ya están dentro de otra compuesta («Correos … y su account lo marca en crítico»). */
export function contadoresMetaCrm290(v={},hoy) {
  const positivo=x=>typeof x==='number'&&Number.isFinite(x)&&x>0?x:null;
  const medido=v.meta_medicion_290;
  const dia=x=>typeof x==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(x)&&Number.isFinite(Date.parse(x+'T00:00:00Z'))&&new Date(x+'T00:00:00Z').toISOString().slice(0,10)===x;
  const typed=medido?.version==='290.1'&&dia(hoy)&&dia(medido.fecha_evaluacion)&&medido.fecha_evaluacion<=hoy&&dia(medido.desde)&&dia(medido.hasta)&&Date.parse(medido.hasta)-Date.parse(medido.desde)===6*864e5&&Date.parse(medido.fecha_evaluacion)-Date.parse(medido.hasta)===864e5&&['lead','onsite_conversion.lead_grouped','offsite_conversion.fb_pixel_lead','onsite_web_lead'].includes(medido.tipo_evento)&&medido.estado==='medido'&&medido.fuente==='meta_insights'&&medido.cohorte_crm_confirmada===false&&typeof medido.eventos_lead==='number'&&Number.isSafeInteger(medido.eventos_lead)&&medido.eventos_lead>=0;
  const meta=typed?medido.eventos_lead:positivo(v.leads_meta_7d),crm=positivo(v.leads_ghl_7d);
  return [tile({icono:'plug',etiqueta:typed?'Eventos lead Meta · 7 días':'Resultados Meta · 7 días',valor:meta,estado:'',
    contexto:typed?'Eventos de la cuenta en siete días cerrados; no contactos únicos, cualificados ni ventas.':'Contador observado; unidad y periodo pendientes de acreditar. No son leads cualificados ni compras.',medible:'medias'}),
    tile({icono:'plug',etiqueta:'Contador CRM · 7 días',valor:crm,estado:'',contexto:'Observación independiente. Sin unión documentada Meta→CRM no se calcula fuga ni porcentaje de llegada. Ausencia/cero heredado no acredita un censo vacío.',medible:'medias'})];
}

function senales(motivos = []) {
  const bajo = motivos.map(m => String(m).toLowerCase());
  return motivos.filter((m, i) => !bajo.some((o, j) => j !== i && o.length > bajo[i].length && o.includes(bajo[i])));
}
const textoMotivo = t => limpiaTexto(String(t || '').replace(/(\d+)\.(\d+)(?= días)/g, (_, a, b) => String(Math.round(Number(`${a}.${b}`)))));

const ICONO_ATAJO = { desk: 'inbox', clickup: 'check', ghl: 'base', meta: 'target', drive: 'drive', clickupFolder: 'check', analytics: 'grafico', searchConsole: 'globe' };
const NOMBRE_ATAJO = { desk: 'Desk', clickup: 'ClickUp', ghl: 'GHL', meta: 'Meta', drive: 'Drive', clickupFolder: 'Carpeta de ClickUp', analytics: 'Analytics', searchConsole: 'Search Console' };

function fuente(ctx, nombre) {
  const f = (ctx.datos.meta.fuentes || []).find(x => x.fuente.startsWith(nombre));
  return f ? { fuente: f.fuente, edad_h: f.edad_h, estado: f.estado } : { fuente: nombre, estado: 'sin datos' };
}

/** Atajos por cliente (solo llegan los de clientes que la persona puede abrir). */
let ATAJOS = null, ATAJOS_DE = null;   // se recarga al cambiar de persona («ver como»): el servidor recorta por persona
async function cargarAtajos(ctx) {
  const clave = `${ctx.real?.id || ''}|${ctx.persona.id}|${ctx.soloLectura ? 'lectura' : 'normal'}`;
  if (ATAJOS && ATAJOS_DE === clave) return ATAJOS;
  let atajos;
  try { const d = await ctx.datosModulo('en_rojo/atajos'); atajos = new Map((d.filas || []).map(f => [f.cliente_id, f])); }
  catch { atajos = new Map(); }
  if (typeof ctx.vigente === 'function' && !ctx.vigente()) return atajos;
  ATAJOS = atajos;
  ATAJOS_DE = clave;
  return ATAJOS;
}

/** «Abrir en X ↗» (pestaña nueva y rastro, sin datos personales). Si falta, gris «Falta emparejar · Mili». */
function atajo(ctx, cid, k, { mini = true, conTexto = true } = {}) {
  const f = ATAJOS?.get(cid);
  const a = f?.atajos.find(x => x.k === k);
  const nombre = NOMBRE_ATAJO[k] || k;
  if (!a) {
    return h('span', { class: `bt${mini ? ' mini' : ''}`, 'aria-disabled': 'true', title: `Falta emparejar ${nombre} con este cliente · lo hace Mili en Ajustes` },
      icono(ICONO_ATAJO[k] || 'ext'), conTexto ? `${nombre} · falta emparejar` : null);
  }
  return h('a', { class: `bt${mini ? ' mini' : ''}`, href: a.url, target: '_blank', rel: 'noopener', title: `Abrir en ${nombre}`, 'aria-label': `Abrir en ${nombre}`,
    on: { click: () => ctx.rastro({ accion: 'atajo', objeto: cid, detalle: `Abrir en ${nombre}` }) } },
  icono(ICONO_ATAJO[k] || 'ext'), conTexto ? `Abrir en ${nombre}` : null, conTexto ? icono('ext', { clase: 's' }) : null);
}

/** Enlace a la ficha del cliente (M4) si el puesto la ve; si no, al detalle de En rojo. */
const hrefFicha = (ctx, id) => (ctx.veModulo('ficha') ? `#/ficha/${id}` : `#/en-rojo/${id}`);

/** Filas de la lista común, ya con la verdad única. */
function filasVerdad(ctx) {
  const porId = new Map(ctx.clientes.map(c => [c.id, c]));
  return ctx.verdadComun().map(v => {
    const c = porId.get(v.id) || { id: v.id, nombre: v.nombre };
    const det = c.detalle ? ctx.verdad(v.id) : null;
    return {
      ...c, id: v.id, nombre: v.nombre || c.nombre, gravedad: v.gravedad, motivo: v.motivo || null,
      n_motivos: v.n_motivos || 0, responsable_id: v.responsable_id, sin_account: v.sin_account, nuevo: v.nuevo,
      responsable: v.responsable_id ? ctx.nombre(v.responsable_id) : null, det,
    };
  }).sort((a, b) => grav(a.gravedad).orden - grav(b.gravedad).orden || b.n_motivos - a.n_motivos || a.nombre.localeCompare(b.nombre, 'es'));
}

// ===================================================================== lista
async function pintarLista(cont, ctx) {
  await cargarAtajos(ctx);
  if (!cont.isConnected || (typeof ctx.vigente === 'function' && !ctx.vigente())) return;
  const filas = filasVerdad(ctx);
  const total = filas.length;
  const n = g => filas.filter(f => f.gravedad === g).length;
  const tieneCartera = ctx.carteraIds.size > 0;
  const mias = filas.filter(f => ctx.carteraIds.has(f.id));
  const operaciones = ctx.persona.puestos.some(p => ['direccion', 'operaciones', 'proyectos'].includes(p));
  const esCoti = ctx.persona.puestos.includes('proyectos');

  ctx.titulo('En rojo', `${n('critico')} críticos · ${n('atencion')} a vigilar · ${n('sin_dato')} por confirmar, de ${total} ${ctx.soloSuCartera ? 'clientes tuyos' : 'clientes'}.`);

  if (!total) {
    cont.append(vacio({ icono: 'plug', titulo: 'Sin la verdad única de clientes', texto: 'No ha llegado la lista única de clientes, así que no se puede decir quién está en rojo. Hay que lanzar la recarga de datos.', quien: 'Agus', borde: true }));
    return;
  }
  if (ctx.ambito === 'cartera' && !tieneCartera) {
    cont.append(avisoParcial('Tu puesto ve el detalle de sus clientes, pero todavía no tienes ninguno asignado. Mientras, ves la lista común. Las asignaciones las mantiene Mili.', { titulo: 'Sin cartera todavía.' }));
  }

  // ---- 1 · cifras: la gravedad única (lo de cada día, arriba) ----
  let chips;
  const ORDEN_CHIPS = ['critico', 'atencion', 'bien', 'sin_dato', ''];
  const elegir = g => { const b = cont.querySelectorAll('#chips-grav button')[ORDEN_CHIPS.indexOf(g)]; if (b && b.getAttribute('aria-pressed') !== 'true') b.click(); cont.querySelector('#chips-grav')?.scrollIntoView({ behavior: 'smooth', block: 'start' }); };
  const fichas = [];
  if (tieneCartera) {
    const mc = mias.filter(f => f.gravedad === 'critico').length;
    fichas.push(tile({ icono: 'persona', etiqueta: 'Mis clientes críticos', valor: mc, unidad: `de ${mias.length}`,
      estado: mc === 0 ? '' : 'rojo', contexto: mc ? 'Están en «Lo primero hoy»' : 'Sin señales críticas en esta copia; no acredita cobertura completa',
      medible: 'hoy', ir: 'Ver mis clientes', alPulsar: () => { filtrarMios(cont); elegir('critico'); } }));
  }
  fichas.push(tile({ icono: 'fire', etiqueta: 'Crítico · actúa hoy', valor: n('critico'), unidad: `de ${total}`, estado: n('critico') ? 'rojo' : '',
    contexto: 'Señales observadas; integración Meta→CRM pendiente de acreditar', medible: 'hoy', ir: 'Ver cuáles', alPulsar: () => elegir('critico') }));
  fichas.push(tile({ icono: 'ojo', etiqueta: 'Vigilar', valor: n('atencion'), unidad: `de ${total}`, estado: n('atencion') ? 'ambar' : '',
    contexto: 'Correos de más de 48 h, sin reunión o bloqueos callados', medible: 'hoy', ir: 'Ver cuáles', alPulsar: () => elegir('atencion') }));
  fichas.push(tile({ icono: 'info', etiqueta: 'Por confirmar', valor: n('sin_dato'), unidad: `de ${total}`, estado: '',
    contexto: 'Sin señales acreditadas; no equivale a cumplimiento completo', medible: 'medias', ir: 'Ver cuáles', alPulsar: () => elegir('sin_dato') }));
  const cifras = h('div', { class: 'tiles', role: 'list', 'aria-label': 'Cifras' }, fichas.map(f => { f.setAttribute('role', 'listitem'); return f; }));

  // La tabla es el puesto de trabajo. Resúmenes y recomendaciones quedan disponibles debajo.
  const resumenSecundario = h('div', {});
  // ---- 2 · lo primero hoy: los críticos (como mucho 7) ----
  // Guía 30 (3.6): lo que pide acción va arriba. Quien lleva cartera y además dirige (Tomás, Mili, Coti) ve los críticos
  // de la casa cuando los suyos están a cero: nunca una caja vacía donde hay trabajo.
  let primeras = [];
  const misCrit = tieneCartera ? mias.filter(f => f.gravedad === 'critico') : [];
  const deCasa = !misCrit.length && operaciones;
  if (misCrit.length) primeras = misCrit;
  else if (operaciones) primeras = filas.filter(f => f.gravedad === 'critico');
  primeras = primeras.slice(0, 7);
  if (tieneCartera || operaciones) {
    const quedan = (deCasa ? filas : mias).filter(f => f.gravedad === 'critico').length - primeras.length;
    const sub = !deCasa ? 'Tus clientes críticos, el más grave arriba (como mucho 7)'
      : `${tieneCartera ? 'Ninguno de tus clientes es crítico. ' : ''}Los críticos de la casa: a quién empujar hoy${quedan > 0 ? ` · ${quedan} más en la lista` : ''}`;
    resumenSecundario.append(panel({ titulo: 'Lo primero hoy', icono: 'zap', sub },
      filasLP(primeras.map(f => {
        const motivo = f.det?.motivos?.[0] ? textoMotivo(senales(f.det.motivos)[0]) : f.motivo;
        const cl = claseMotivo(motivo);
        return {
          estado: 'rojo', icono: cl.icono, motivo: `${f.nombre} · ${f.motivo || 'Crítico'}`,
          detalle: [f.det ? motivo : null, f.responsable ? `Lleva el cliente ${f.responsable}` : 'Sin account asignado'].filter(Boolean).join(' · '),
          botones: [
            f.detalle ? h('a', { class: 'bt mini pri', href: hrefFicha(ctx, f.id) }, icono('cli'), 'Abrir la ficha') : null,
            f.detalle ? atajo(ctx, f.id, cl.atajo) : null,
            f.detalle && ctx.veModulo('ficha') ? h('a', { class: 'bt mini', href: `#/en-rojo/${f.id}` }, icono('fire'), 'Por qué') : null,
            botonDeshacer({ texto: 'Señal vista', hecho: 'Señal vista', soloLectura: ctx.soloLectura,
              alHacer: () => { ctx.rastro({ accion: 'critico_visto', objeto: f.id }); return 'Señal vista · no revisa el plan'; } }),
          ],
        };
      }), { vacio: { titulo: 'Sin señales críticas en esta copia', porque: 'Repasa los de «Vigilar» y la cobertura pendiente de confirmar.', celebrar: false } })));

  }
  resumenSecundario.append(cifras);

  // ---- 3 · la lista común: chips de gravedad que se quedan (por defecto, crítico) ----
  // Tomás 3-oct: el account ya solo recibe sus clientes (recorte en el servidor): sin conmutador «Solo mis clientes».
  const soloMios = h('button', { type: 'button', class: 'bt', 'aria-pressed': 'false', id: 'solo-mios', hidden: !tieneCartera || ctx.soloSuCartera }, icono('persona'), 'Solo mis clientes');
  const caja = h('div', { id: 'tabla-rojo' });
  chips = chipsFiltro({
    etiqueta: 'Gravedad', clave: 'en-rojo.gravedad', valor: 'critico',
    opciones: [
      { valor: 'critico', texto: 'Crítico', icono: 'fire', cuenta: n('critico'), cuentaEstado: 'rojo' },
      { valor: 'atencion', texto: 'Vigilar', icono: 'ojo', cuenta: n('atencion') },
      { valor: 'bien', texto: 'Bien', icono: 'ok', cuenta: n('bien') },
      { valor: 'sin_dato', texto: 'Por confirmar', icono: 'info', cuenta: n('sin_dato') },
      { valor: '', texto: 'Todos', cuenta: total },
    ],
    alCambiar: () => pintarTabla(),
  });
  chips.id = 'chips-grav';

  const pintarTabla = () => {
    const mios = soloMios.getAttribute('aria-pressed') === 'true';
    const g = chips.valor();
    const base = (mios ? mias : filas).filter(f => !g || f.gravedad === g);
    caja.replaceChildren(tablaDensa({
      filas: base,
      buscar: { campos: ['nombre', 'responsable', 'motivo'], placeholder: 'Buscar cliente o account' },
      filtros: [{ clave: 'responsable', titulo: 'Account' }, { clave: 'motivo', titulo: 'Motivo' }],
      columnas: [
        { clave: 'nombre', titulo: 'Cliente', principal: true, celda: f => h('span', { class: 'celda-cli' }, logoCliente(f), f.nombre, f.nuevo ? chipEstado('azul', 'Nuevo', { punto: false }) : null) },
        { clave: 'gravedad', titulo: 'Gravedad', valor: f => grav(f.gravedad).orden, celda: f => chipEstado(grav(f.gravedad).color, grav(f.gravedad).texto) },
        { clave: 'motivo', titulo: 'Motivo', celda: f => f.motivo
          ? h('span', { class: 'fila', style: { gap: 'var(--s-2)', flexWrap: 'nowrap' } }, icono(claseMotivo(f.motivo).icono, { clase: 's' }), h('span', {}, f.motivo), f.det && senales(f.det.motivos).length > 1 ? h('span', { class: 'sub', title: senales(f.det.motivos).slice(1).map(textoMotivo).join(' · ') }, `+${senales(f.det.motivos).length - 1}`) : null)
          : h('span', { class: 'sub' }, 'Ninguna señal') },
        { clave: 'responsable', titulo: 'Account', celda: f => f.responsable_id
          ? h('span', { class: 'fila', style: { gap: 'var(--s-2)', flexWrap: 'nowrap' } }, h('span', { class: 'av s', 'aria-hidden': 'true' }, iniciales(f.responsable)), f.responsable)
          : h('span', { title: f.sin_account ? limpiaTexto(f.sin_account) : null }, chipEstado('ambar', 'Sin account')) },
        { clave: 'abrir', titulo: 'Abrir', ordenable: false, celda: f => f.detalle
          ? h('span', { class: 'fila', style: { gap: 'var(--s-1)', flexWrap: 'nowrap', justifyContent: 'flex-end' } },
              // Ronda U (50, En rojo): Coti da el «Visto» desde la propia lista, sin abrir la tarjeta
              esCoti && f.gravedad === 'critico' ? botonDeshacer({ texto: 'Señal vista', hecho: 'Señal vista', soloLectura: ctx.soloLectura, alHacer: () => { ctx.rastro({ accion: 'critico_visto', objeto: f.id }); return 'Señal vista · no revisa el plan'; } }) : null,
              h('a', { class: 'bt mini', href: hrefFicha(ctx, f.id), title: `Abrir la ficha de ${f.nombre}` }, icono('cli'), 'Ficha'),
              ['desk', 'clickup', 'ghl'].filter(k => ATAJOS?.get(f.id)?.atajos.some(a => a.k === k)).map(k => atajo(ctx, f.id, k, { conTexto: false })))
          : candado('Lo ve quien lo lleva') },
      ],
      alPulsar: f => ctx.navegar(`en-rojo/${f.id}`),
      puedePulsar: f => f.detalle,
      etiquetaFila: f => `${f.nombre}: ${grav(f.gravedad).texto}${f.motivo ? `, ${f.motivo}` : ''}, account ${f.responsable || 'sin asignar'}. Ver por qué`,
      vacio: { titulo: mios ? 'Ninguno de tus clientes en esta gravedad' : 'Ningún cliente en esta gravedad', porque: 'Cambia de chip para ver el resto; una copia sin señales no acredita cobertura completa.', celebrar: false },
    }));
  };
  soloMios.addEventListener('click', () => { soloMios.setAttribute('aria-pressed', soloMios.getAttribute('aria-pressed') === 'true' ? 'false' : 'true'); pintarTabla(); });
  pintarTabla();
  cont.append(panel({ titulo: ctx.soloSuCartera ? 'Tus clientes por gravedad' : 'Clientes por gravedad', icono: 'fire', sub: ctx.soloSuCartera ? 'Solo los clientes de tu cartera: gravedad y motivo. Sin importes ni datos de contactos. Pulsa una fila para ver por qué.' : 'Lo ve todo el equipo: gravedad, motivo y account. Sin importes ni datos de contactos. Pulsa una fila para ver por qué.', acciones: soloMios },
    h('div', { class: 'cuerpo', style: { paddingBottom: 'var(--s-1)' } }, chips), caja));

  consejoCompacto(cont, cont.lastElementChild);
  cont.append(h('details', { class: 'panel' },
    h('summary', { style: { padding: '12px 18px', cursor: 'pointer', minHeight: '44px', boxSizing: 'border-box' } }, 'Resumen y acciones recomendadas'), resumenSecundario));

  // ---- 4 · avisos de equipo (de persona, no de cliente; semanal, abajo y plegado) ----
  const dePersona = ctx.datos.alarmas.filter(a => a.ambito === 'persona' && a.gravedad === 'rojo');
  if (dePersona.length) {
    const nombreDe = a => (a.responsable_id ? ctx.nombre(a.responsable_id) : a.responsable) || 'Sin persona';
    cont.append(h('details', { class: 'panel', style: { padding: '0' } },
      h('summary', { style: { padding: 'var(--s-4) var(--relleno)', cursor: 'pointer', fontWeight: 700, display: 'flex', alignItems: 'center', gap: 'var(--s-2)' } }, icono('eq'), `Avisos de equipo · ${dePersona.length}`,
        h('span', { class: 'sub', style: { fontWeight: 400 } }, '· de una persona, no de un cliente')),
      h('ul', { class: 'lista-i cuerpo', style: { paddingTop: '0' } }, dePersona.map(a =>
        h('li', {},
          h('span', { class: 'av s', 'aria-hidden': 'true' }, iniciales(nombreDe(a))),
          h('span', { class: 't', style: { whiteSpace: 'normal' } }, h('b', {}, `${nombreDe(a)} · ${limpiaTexto(a.tipo)}`), h('span', { class: 'sub', style: { display: 'block' } }, limpiaTexto(a.texto || ''))),
          a.resumen ? chipEstado('ambar', limpiaTexto(a.resumen)) : null)))));
  }

  cont.append(h('p', { class: 'sub' }, 'Regla única de gravedad para toda la app (la misma que Captación, CRM, Nuevos, Reuniones y Producción). La lista común no lleva cifras; el detalle, sí.'));
}

function filtrarMios(cont) {
  const b = cont.querySelector('#solo-mios');
  if (b && b.getAttribute('aria-pressed') !== 'true') b.click();
}

/** Etapa desde la fecha de alta, como en la ficha v3: 0 firma (< 14 días) · 1 arranque (< 30) · 2 optimización (< 90) · 3 consolidado. */
function etapa(c) {
  if (!c.alta) return -1;
  const d = (Date.now() - new Date(c.alta + 'T12:00:00')) / 864e5;
  return d < 14 ? 0 : d < 30 ? 1 : d < 90 ? 2 : 3;
}

const ESTADO_ENCENDIDO = {
  en_plazo: ['verde', 'Encendida en plazo'], en_limite: ['ambar', 'Encendida en el límite'], tarde: ['ambar', 'Encendida tarde'],
  sin_encender_fuera_de_plazo: ['rojo', 'Sin encender, fuera de plazo'], pendiente_en_plazo: ['gris', 'Pendiente, aún en plazo'],
};

// =================================================================== detalle
async function pintarDetalle(cont, ctx, id) {
  await cargarAtajos(ctx);
  if (!cont.isConnected || (typeof ctx.vigente === 'function' && !ctx.vigente())) return;
  const c = ctx.clientes.find(x => x.id === id);
  const volver = h('a', { class: 'bt', href: '#/en-rojo' }, icono('volver'), 'Volver a En rojo');
  if (!c) { cont.append(vacio({ icono: 'buscar', titulo: 'No encuentro ese cliente', texto: 'No hay ningún cliente activo con ese identificador.', accion: volver, borde: true })); return; }
  const v = ctx.verdad(id);
  if (!c.detalle || !v?.motivos) {
    ctx.titulo(c.nombre, '');
    const resp = v?.responsable_id ? ctx.nombre(v.responsable_id) : null;
    cont.append(vacio({ icono: 'candado', titulo: 'El detalle de este cliente no es de tu puesto', texto: `En la lista común ves su gravedad, su motivo y su account; las cifras y los atajos solo los ve quien lleva el cliente.${resp ? ` Si necesitas algo de ${c.nombre}, habla con ${resp}.` : ''}`, quien: resp || 'Mili', accion: volver, borde: true }));
    return;
  }
  const g = grav(v.gravedad);
  const account = v.account ? ctx.nombre(v.account) : null;
  const sen = senales(v.motivos);
  ctx.titulo(c.nombre, `${g.texto} · ${sen.length ? `${sen.length} señal${sen.length === 1 ? '' : 'es'}` : 'sin señales'} · ${account ? `lleva el cliente ${account}` : 'sin account asignado'}`);

  cont.append(h('div', { class: 'fila', style: { justifyContent: 'space-between' } },
    h('nav', { class: 'migas', 'aria-label': 'Migas' }, h('a', { href: '#/en-rojo' }, icono('fire', { clase: 's' }), 'En rojo'), h('span', { 'aria-hidden': 'true' }, '›'), h('span', { 'aria-current': 'page' }, c.nombre)),
    selectorCliente({ clientes: ctx.clientesVisibles, actual: c.id, etiqueta: 'Cambiar de cliente',
      insignia: x => { const gx = grav(ctx.verdad(x.id)?.gravedad); return chipEstado(gx.color, gx.texto); },
      detalle: x => { const r = ctx.verdad(x.id); return r?.account ? ctx.nombre(r.account) : 'sin account'; },
      alElegir: x => ctx.navegar(`en-rojo/${x.id}`) })));

  const web = c.web ? c.web.replace(/^https?:\/\//, '').replace(/\/$/, '') : null;
  const e = etapa(c);
  const fila = ATAJOS?.get(id);
  cont.append(h('section', { class: 'detalle-cab', style: { display: 'grid', gap: 'var(--s-4)' }, 'aria-label': 'Cabecera del cliente' },
    h('div', { class: 'fila', style: { gap: 'var(--s-4)', alignItems: 'center' } },
      logoCliente(c, 'logo-cli xl'),
      h('div', { style: { minWidth: 0, flex: '1 1 260px' } },
        h('h2', {}, c.nombre),
        h('div', { class: 'meta-linea', style: { marginTop: 'var(--s-1)' } },
          account ? h('span', {}, h('span', { class: 'av s', 'aria-hidden': 'true' }, iniciales(account)), account) : h('span', {}, icono('persona'), 'Sin account asignado'),
          v.alta ? h('span', {}, icono('cal'), `Cliente desde ${fDiaRO(v.alta)} ${v.alta.slice(0, 4)}`) : null,
          c.descripcion ? h('span', {}, icono('maletin'), c.descripcion) : null,
          web ? h('span', {}, icono('link'), h('a', { href: c.web, target: '_blank', rel: 'noopener', style: { display: 'inline-flex', alignItems: 'center', minHeight: 'var(--s-8)', minWidth: 'var(--s-8)' } }, web)) : null),
        h('div', { class: 'fila', style: { marginTop: 'var(--s-3)', gap: 'var(--s-2)' } },
          chipEstado(g.color, g.texto),
          v.nuevo ? chipEstado('azul', `Cliente nuevo · día ${v.dia_alta ?? '—'}`) : null,
          v.sin_account ? chipEstado('ambar', 'Sin account') : null)),
      h('div', { class: 'fila' },
        // V2 (A-M15): quien viene a dar el «Visto» a un crítico lo tiene en la cabecera, sin bajar a 995 px
        v.gravedad === 'critico' ? botonDeshacer({ texto: 'Señal vista', hecho: 'Señal vista', mini: false, pri: !ctx.veModulo('ficha'), soloLectura: ctx.soloLectura,
          alHacer: () => { ctx.rastro({ accion: 'critico_visto', objeto: id }); return 'Señal vista · no revisa el plan'; } }) : null,
        ctx.veModulo('ficha') ? h('a', { class: 'bt pri', href: `#/ficha/${id}` }, icono('cli'), 'Abrir la ficha') : null)),
    h('div', { class: 'fila', style: { gap: 'var(--s-2)' }, 'aria-label': 'Abrir en las herramientas' },
      h('span', { class: 'sub', style: { fontWeight: 600, marginRight: 'var(--s-1)' } }, 'Abrir en'),
      (fila?.atajos || []).map(a => atajo(ctx, id, a.k, { conTexto: true })),
      (fila?.faltan || []).map(k => atajo(ctx, id, k, { conTexto: true }))),
    e >= 0 ? barraEtapas(null, e) : null));

  cont.append(panelPlanFuego255(ctx, id));
  consejoCompacto(cont, cont.lastElementChild);

  // ---- cifras del detalle (de la verdad única; sin dato = gris, nunca un verde falso) ----
  const t = [];
  const dc = v.correos_sin_responder_dias;
  t.push(tile({ icono: 'mail', etiqueta: 'Correo más antiguo sin contestar', valor: dc ?? 'Al día', unidad: dc ? 'días laborables' : null,
    estado: dc == null ? 'verde' : dc > 10 ? 'rojo' : dc > 2 ? 'ambar' : 'verde', contexto: 'Bien: menos de 48 h · crítico: más de 10 días con otra señal',
    medible: 'hoy', frescura: fuente(ctx, 'Desk'), ...(dc && fila?.atajos.some(a => a.k === 'desk') ? { href: fila.atajos.find(a => a.k === 'desk').url, ir: 'Abrir en Desk' } : {}) }));
  t.push(tile({ icono: 'video', etiqueta: 'Última reunión', valor: v.ultima_reunion ? fDiaRO(v.ultima_reunion) : null,
    estado: v.sin_reunion_mes_pasado ? 'ambar' : v.ultima_reunion ? 'verde' : '', contexto: v.sin_reunion_mes_pasado ? 'Sin reunión el mes pasado (CRM, Fathom y Zoom)' : v.reunion_estado === 'ok' ? 'Con reunión el mes pasado' : 'Sin dato de reuniones',
    medible: 'hoy' }));
  const bl = v.bloqueos || {};
  t.push(tile({ icono: 'candado', etiqueta: 'Tareas bloqueadas', valor: bl.tareas ?? null, unidad: bl.tareas ? `la más antigua, ${fmt.num(bl.dias_max)} días` : null,
    estado: bl.tareas == null ? '' : v.bloqueo_callado ? 'ambar' : 'verde', contexto: v.bloqueo_callado ? 'Bloqueo callado: más de 5 días sin moverse' : bl.tareas ? 'Ninguna lleva más de 5 días' : 'Ninguna tarea en «bloqueado»',
    medible: 'hoy', frescura: fuente(ctx, 'ClickUp') }));
  t.push(...contadoresMetaCrm290(v,ctx.hoy));
  if (v.nuevo && v.encendido) {
    const [col, txt] = ESTADO_ENCENDIDO[v.encendido.estado] || ['gris', 'Sin dato'];
    t.push(tile({ icono: 'rocket', etiqueta: 'Encendido del alta', valor: v.encendido.dia ? `Día ${v.encendido.dia}` : txt, estado: col,
      contexto: `Objetivo: día 10; límite: día 12. Hoy es el día ${v.dia_alta ?? '—'} desde el alta`, medible: 'hoy' }));
  }
  t.push(tile({ icono: 'heart', etiqueta: 'Salud', valor: v.salud ?? null, unidad: v.salud != null ? 'de 100' : null,
    // V2 (A-M15): una salud «verde» junto a «Crítico» confunde: la gravedad la dan las señales; la salud no la pinta en verde
    estado: '',
    contexto: v.salud == null ? 'Sin puntuación acreditada: faltan cohortes de resultados y ventas.' : 'Referencia provisional de una copia anterior; pendiente de revisar sus señales y cobertura.',
    medible: 'medias', medibleDetalle: 'Fórmula provisional, pendiente de validar' }));
  cont.append(tiles(t));

  cont.append(h('div', { class: 'dos' },
    panel({ titulo: `Por qué está en «${g.texto.toLowerCase()}»`, icono: 'alert', sub: 'Cada señal con su atajo a la herramienta donde se arregla' },
      filasLP(sen.map((m, i) => {
        const txt = textoMotivo(m); const cl = claseMotivo(txt);
        return { estado: v.gravedad === 'critico' && i === 0 ? 'rojo' : 'ambar', icono: cl.icono, motivo: txt,
          botones: [atajo(ctx, id, cl.atajo),
            botonDeshacer({ texto: 'Marcar visto', hecho: 'Visto', soloLectura: ctx.soloLectura,
              alHacer: () => { ctx.rastro({ accion: 'senal_vista', objeto: id, detalle: txt }); return 'Visto · queda en el rastro'; } })] };
      }), { vacio: { titulo: 'Sin señales acreditadas en esta copia', porque: 'Revisa la cobertura de las fuentes antes de confirmar cómo está el cliente.', celebrar: false } })),
    h('div', { class: 'pila' },
      panel({ titulo: 'Línea de tiempo', icono: 'hist' }, h('div', { class: 'cuerpo' }, lineaTiempo([
        c.prox_reunion ? { fecha: c.prox_reunion, titulo: 'Próxima reunión', estado: 'verde' } : null,
        v.ultima_reunion ? { fecha: v.ultima_reunion, titulo: 'Última reunión', detalle: 'CRM, Fathom o Zoom' } : null,
        v.nuevo && v.encendido?.dia && v.alta ? { fecha: new Date(new Date(v.alta + 'T12:00:00').getTime() + v.encendido.dia * 864e5).toISOString().slice(0, 10), titulo: 'Campaña encendida', detalle: `Día ${v.encendido.dia}` } : null,
        v.alta ? { fecha: v.alta, titulo: 'Alta del cliente' } : null,
      ].filter(Boolean)))),
      h('div', { class: 'fila' }, frescura(fuente(ctx, 'Desk')), frescura(fuente(ctx, 'ClickUp')), frescura(fuente(ctx, 'Meta'))))));
}

export default {
  id: 'en-rojo',
  titulo: 'En rojo',
  grupo: 'Hoy',
  // V2 (C-13): los setters solo trabajan la subcuenta de RO (guía 14): sin «En rojo» de los clientes de la agencia.
  // Lo manda el servidor (reglas_permisos.json › modulos «en-rojo»): pedido a R16 en dudas_pintura.md · V2.
  puestos_que_lo_ven: { '*': 'todo', setters: null },
  async render(contenedor, ctx) {
    const raiz = h('div', { 'data-en-rojo-ruta': '255' });
    contenedor.append(raiz);
    vigilarCortes(raiz);
    const [id] = ctx.params;
    if (id) await pintarDetalle(raiz, ctx, id);
    else await pintarLista(raiz, ctx);
  },
};

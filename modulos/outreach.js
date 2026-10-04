import { fechas as FECHAS_RO, fechaCorta as fechaCortaRO } from '../componentes.js';
// modulos/outreach.js · M17 «Prospección y outreach» (E6). Dos pestañas medidas por separado: campañas de clientes
// (primero) y campañas de RO. Respuestas de Snov.io de 30 días: se eligen varias y se asignan o clasifican de una vez.
// Linked Helper y Explee no tienen API: entran por la hoja semanal declarada, con su propio sello.

import { h, fmt, tile, tiles, vacioLinea, listaLoPrimero, tablaApilable, chipEstado, chipsFiltro, pestanas, vacio, botonConfirmar,
  avisoParcial, panel, frescura, icono, selloMedible, limpiaTexto, avisoFlotante, fechaCorta } from '../componentes.js';
import { cargar, fresco, cuandoTexto, encolar, leerCola, vistaPrevia, abrirEn, masAcciones, verDatos, abrirLinkedIn, campo, puedeAbrir, diaCorto } from './_ventas_comun.js';
import { franjaCifras } from './_trabajo.js';
import { pantallaAncha, franjaEnLinea } from './_trabajo_ancho.js';
import { conDeshacer, botonDeshacer } from './_deshacer.js';

const CLASES = [{ valor: 'positiva', texto: 'Positiva', icono: 'ok' }, { valor: 'negativa', texto: 'Negativa', icono: 'cerrar' },
  { valor: 'mas_tarde', texto: 'Más tarde', icono: 'clock' }, { valor: 'neutra', texto: 'Neutra', icono: 'info' },
  { valor: 'baja', texto: 'Baja / no molestar', icono: 'candado' }];

/** V5 · «Más acciones» con el nombre en aria-label (antes «Más» a secas, 225 por pantalla). V4: el menú parte línea. */
function masDe(nombre, ...botones) {
  const m = masAcciones(...botones);
  const s = m?.querySelector(':scope > summary');
  if (s) { s.lastChild.textContent = 'Más acciones'; s.setAttribute('aria-label', `Más acciones de ${nombre || 'esta respuesta'}`); }
  const f = m?.querySelector(':scope > .fila');
  if (f) Object.assign(f.style, { flexWrap: 'wrap', minWidth: '0', maxWidth: '100%' });
  return m;
}

/** Dueño y clase de cada respuesta: lo último apuntado manda (acciones del módulo, de todo el equipo). */
function estadoCola(cola) {
  const dueno = {}, clase = {}, hojas = [];
  for (const a of cola) {
    if (a.que === 'asignar_respuesta') dueno[a.sobre] = a.texto;
    if (a.que === 'clasificar_respuesta') clase[a.sobre] = a.texto;
    if (a.que === 'hoja_semanal') hojas.push(a);
  }
  return { dueno, clase, hojas };
}

async function pintar(cont, ctx) {
  const [o, meta] = await Promise.all([cargar(ctx, 'outreach'), cargar(ctx, 'meta')]);
  if (!o) {
    cont.append(vacio({ icono: 'send', titulo: 'Todavía no hay datos de outreach', texto: 'Falta generar los datos de hoy.', quien: 'Agus', tono: 'aviso' }));
    return;
  }
  // V2 (C-2/3) · Outreach ve SOLO sus campañas: las de los clientes de su cartera de outreach (silla «outreach» de
  // asignaciones; cliente de cada campaña por fuentes_ventas/campana_cliente.py). Jefa de CRM y dirección, todas.
  // El servidor también recorta por cliente_id (pedido a R16 en dudas_pintura.md · V2).
  const ve = ctx.persona.puestos;
  const soloMias = ve.includes('outreach') && !ve.some(x => ['direccion', 'jefa_crm', 'operaciones'].includes(x));
  const mia = ctx.carteraPorSilla?.outreach;
  const esMia = x => !soloMias || (!!x.cliente_id && !!mia && typeof mia.has === 'function' && mia.has(x.cliente_id));
  if (soloMias) {
    o.respuestas = (o.respuestas || []).filter(esMia);
    if (o.snov) o.snov = { ...o.snov, campañas: (o.snov.campañas || []).filter(esMia) };
    const nombres = new Set((mia ? [...mia] : []).map(id => (ctx.clientes.find(c => c.id === id) || {}).nombre).filter(Boolean).map(n => n.toLowerCase().split(' ')[0]));
    o.clientes = Object.fromEntries(Object.entries(o.clientes || {}).filter(([k]) => nombres.has(k.toLowerCase().split(' ')[0])));
  }
  const cola = await leerCola(ctx, 'prospeccion');
  const loc = estadoCola(cola);
  const gente = (ctx.datos.personas || []).filter(p => (p.puestos || []).some(x => x === 'outreach' || x === 'jefa_crm') && p.estado !== 'baja' && p.activo !== false);
  ctx.titulo('Prospección y outreach', soloMias ? `Tus campañas: las de tus ${mia?.size || 0} clientes de outreach · respuestas para clasificar y resultados` : 'Respuestas sin dueño, campañas y resultados · campañas de clientes y de RO por separado');
  const sinDueno = f => (o.respuestas || []).filter(r => r.frente === f && !loc.dueno[r.id]).length;
  // Ronda U (#1): molde a todo el ancho; el consejo de la IA va plegado debajo de la lista
  cont.append(pantallaAncha({ id: 'prospeccion', lista: pestanas({
    clave: 'prospeccion.pestana', etiqueta: 'Frente',
    pestanas: [
      { id: 'clientes', texto: 'Campañas de clientes', icono: 'cli', cuenta: sinDueno('clientes'), cuentaEstado: 'rojo' },
      { id: 'ro', texto: 'Campañas de RO', icono: 'megafono', cuenta: sinDueno('ro'), cuentaEstado: 'rojo' },
    ],
    pintar: (id, zona) => pintarFrente(zona, ctx, o, meta, id, loc, gente),
  }), contexto: [] }));
}

function pintarFrente(zona, ctx, o, meta, frente, loc, gente) {
  const resumen = ctx.nivel === 'resumen';
  const resp = (o.respuestas || []).filter(r => r.frente === frente);
  const camp = (o.snov?.campañas || []).filter(c => c.frente === frente);
  const fSnov = fresco(meta, 'Snov.io'), fMili = fresco(meta, 'Outreach de clientes', 'Informes de outreach');
  const positivas = () => resp.filter(r => loc.clase[r.id] === 'positiva');

  // R12 (C-A4): sin lectura de Snov.io no hay «0»: es «sin dato» y se dice por qué (antes enseñaba 0 campañas con 328 envíos en la tabla).
  const snovLeido = !!o.snov;
  const sinSnov = 'Snov.io todavía no se ha leído: se lee en la recarga completa (6:00 y 14:00)';
  const ctxN = [];   // Ronda U (#1): lo de leer (cifras grandes, campañas, resultados, hoja semanal) va DEBAJO de la lista

  ctxN.push(tiles([
    tile({ icono: 'inbox', etiqueta: 'Respuestas sin dueño', valor: snovLeido ? resp.filter(r => !loc.dueno[r.id]).length : null, sinDato: sinSnov, unidad: snovLeido ? `de ${resp.length} en 30 días` : '', estado: !snovLeido ? '' : resp.some(r => !loc.dueno[r.id]) ? 'rojo' : (resp.length ? 'verde' : ''),
      contexto: 'Si nadie las coge en 4 h, pasan a quien dirige outreach; a las 24 h, a Mili', medible: 'medias', medibleDetalle: 'Solo Snov.io; Explee y Linked Helper no tienen API', frescura: fSnov }),
    tile({ icono: 'ok', etiqueta: 'Positivas por pasar a GoHighLevel', valor: snovLeido ? positivas().length : null, sinDato: sinSnov, estado: positivas().length ? 'ambar' : '',
      contexto: 'Cada positiva se apunta en GoHighLevel como «outreach»', medible: 'medias' }),
    tile({ icono: 'send', etiqueta: 'Campañas activas', valor: snovLeido ? camp.filter(c => c.estado === 'Active').length : null, sinDato: sinSnov, unidad: snovLeido ? `${camp.length} activas o en pausa` : '',
      contexto: frente === 'ro' && snovLeido && !camp.length ? 'RO no tiene campañas en Snov.io' : `Snov.io${o.snov?.leido ? ` · leído ${cuandoTexto(o.snov.leido)}` : ''}`, frescura: fSnov }),
  ]));
  ctxN.push(vacioLinea('Todavía no se miden las citas por cada 1.000 contactos ni la tasa de respuesta del correo (bien desde el 5,5 %): salen de la hoja semanal y de la etiqueta «outreach» en GoHighLevel.', { icono: 'clock' }));

  // ---- 1 · respuestas: clasificar EN LA FILA (Ronda U, cambio #15 del 50) ----
  // Positiva · Negativa · Más tarde con un clic: la respuesta pasa a ser tuya (dueño = quien la clasifica) y sale de «Sin
  // dueño»; «Deshacer» 8 s. La barra para varias a la vez solo aparece al marcar 2 o más casillas. Todo interno (no se
  // contesta a nadie desde aquí).
  if (!resumen) {
    const elegidas = new Set();
    let filtro = 'sin_dueno', campana = '', tope = 15;
    const cuerpo = h('div');
    const barra = h('div', { class: 'pila', hidden: true, style: { gap: 'var(--s-3)', padding: 'var(--s-3) var(--relleno)', borderBottom: 'var(--borde-suave)', background: 'var(--card-2)' } });
    const yo = ctx.persona.id;
    let franja = null;
    const contar = () => ({ sin: resp.filter(r => !loc.dueno[r.id]).length, pos: positivas().length });
    const ponerFranja = () => {
      const n = contar();
      const nueva = franjaEnLinea(franjaCifras([
        { etiqueta: 'Sin dueño', valor: snovLeido ? n.sin : 'sin dato', estado: n.sin ? 'rojo' : '', activo: filtro === 'sin_dueno', alPulsar: () => { filtro = 'sin_dueno'; tope = 15; pintarLista(); } },
        { etiqueta: 'Positivas', valor: n.pos, activo: filtro === 'positivas', alPulsar: () => { filtro = 'positivas'; tope = 15; pintarLista(); } },
        { etiqueta: 'Todas', valor: resp.length, activo: filtro === 'todas', alPulsar: () => { filtro = 'todas'; tope = 15; pintarLista(); } },
        { etiqueta: 'Campañas activas', valor: snovLeido ? camp.filter(c => c.estado === 'Active').length : 'sin dato', titulo: sinSnov },
      ], { etiqueta: 'Respuestas (filtran la lista)' }));
      if (franja) franja.replaceWith(nueva);
      franja = nueva;
      return nueva;
    };
    const campanas = [...new Set(resp.map(r => r.campana))];
    const filtroCamp = campanas.length > 1 ? h('details', { class: 'que-es' }, h('summary', {}, `Campaña: todas (${campanas.length})`),
      h('div', { style: { marginTop: 'var(--s-2)' } }, chipsFiltro({ etiqueta: 'Campaña', valor: '', opciones: [{ valor: '', texto: 'Todas' },
        ...campanas.map(c => ({ valor: c, texto: c.length > 34 ? c.slice(0, 32) + '…' : c, cuenta: resp.filter(r => r.campana === c).length }))],
      alCambiar: v => { campana = v; tope = 15; filtroCamp.querySelector('summary').textContent = v ? `Campaña: ${v.length > 40 ? v.slice(0, 38) + '…' : v}` : `Campaña: todas (${campanas.length})`; pintarLista(); } }))) : null;

    /** Clasifica una o varias respuestas: optimista + Deshacer; al vencer, asigna (a quien clasifica) y clasifica en la cola. */
    const clasificar = (ids, clase, dueno = yo) => {
      const antes = ids.map(id => ({ id, d: loc.dueno[id], c: loc.clase[id] }));
      const texto = CLASES.find(x => x.valor === clase)?.texto || clase;
      conDeshacer({
        mensaje: ids.length === 1 ? `«${texto}» · ${nombreRespuesta(resp.find(r => r.id === ids[0]) || {})}` : `${ids.length} respuestas · «${texto}»`,
        optimista: () => { for (const id of ids) { if (dueno) loc.dueno[id] = dueno; loc.clase[id] = clase; elegidas.delete(id); } pintarLista(); },
        revertir: () => { for (const a of antes) { if (a.d) loc.dueno[a.id] = a.d; else delete loc.dueno[a.id]; if (a.c) loc.clase[a.id] = a.c; else delete loc.clase[a.id]; } pintarLista(); },
        hacer: async () => {
          for (const id of ids) {
            const r = resp.find(x => x.id === id);
            if (dueno && antes.find(a => a.id === id)?.d !== dueno) await encolar(ctx, { que: 'asignar_respuesta', sobre: id, texto: dueno, herramienta: 'app', vista: `Respuesta de «${r?.campana}» con dueño` });
            if (clase) await encolar(ctx, { que: 'clasificar_respuesta', sobre: id, texto: clase, herramienta: 'app', vista: 'Clase de la respuesta' });
          }
        },
      });
    };

    // barra para varias a la vez (solo con 2 o más elegidas)
    const pintarBarra = () => {
      barra.hidden = elegidas.size < 2;
      if (barra.hidden) return;
      let dueno = '', clase = '';
      const chipsD = chipsFiltro({ etiqueta: 'Asignar a', opciones: [{ valor: '', texto: 'A mí' }, ...gente.filter(p => p.id !== yo).map(p => ({ valor: p.id, texto: ctx.nombre(p.id), icono: 'persona' }))], valor: '', alCambiar: v => { dueno = v; } });
      const chipsC = chipsFiltro({ etiqueta: 'Clasificar', opciones: [{ valor: '', texto: 'Sin cambiar' }, ...CLASES], valor: '', alCambiar: v => { clase = v; } });
      const aplicar = h('button', { type: 'button', class: 'bt pri', 'aria-disabled': ctx.soloLectura ? 'true' : null, on: { click: () => {
        if (ctx.soloLectura) return;
        const ids = [...elegidas];
        if (!clase && !dueno) { aplicar.after(h('span', { class: 'sub', role: 'alert' }, ' Elige a quién asignar o cómo clasificar.')); return; }
        if (clase) clasificar(ids, clase, dueno || yo);
        else conDeshacer({ mensaje: `${ids.length} respuestas asignadas a ${ctx.nombre(dueno)}`,
          optimista: () => { ids.forEach(id => { loc.dueno[id] = dueno; elegidas.delete(id); }); pintarLista(); },
          revertir: () => { ids.forEach(id => { delete loc.dueno[id]; }); pintarLista(); },
          hacer: async () => { for (const id of ids) await encolar(ctx, { que: 'asignar_respuesta', sobre: id, texto: dueno, herramienta: 'app', vista: 'Respuesta con dueño' }); } });
      } } }, icono('ok'), `Aplicar a las ${elegidas.size} elegidas`);
      barra.replaceChildren(h('div', { class: 'fila' }, h('b', {}, `${elegidas.size} elegidas`), h('button', { type: 'button', class: 'bt mini', on: { click: () => { elegidas.clear(); pintarLista(); } } }, 'Quitar la selección')), chipsD, chipsC, h('div', { class: 'fila' }, aplicar));
    };

    function pintarLista() {
      ponerFranja();
      const filas = resp.filter(r => (filtro === 'sin_dueno' ? !loc.dueno[r.id] : filtro === 'positivas' ? loc.clase[r.id] === 'positiva' : true) && (!campana || r.campana === campana))
        .sort((a, b) => (b.fecha || '').localeCompare(a.fecha || ''));
      pintarBarra();
      cuerpo.replaceChildren(...[
        listaLoPrimero(filas.slice(0, tope).map(r => {
          // 3-oct: dirección, la jefa de CRM y quien lleva la campaña reciben del servidor nombre y empresa en claro
          const destino = h('span', {}, nombreRespuesta(r));
          const extracto = h('p', { class: 'sub', hidden: true, style: { margin: 'var(--s-1) 0 0', maxWidth: '72ch', whiteSpace: 'normal', display: '-webkit-box', WebkitLineClamp: '2', WebkitBoxOrient: 'vertical', overflow: 'hidden' } });
          const casilla = h('input', { type: 'checkbox', 'aria-label': `Elegir la respuesta de ${r.nombre_m}`, disabled: ctx.soloLectura || null, style: { width: 'var(--s-5)', height: 'var(--s-5)' } });
          casilla.checked = elegidas.has(r.id);
          casilla.addEventListener('change', () => { casilla.checked ? elegidas.add(r.id) : elegidas.delete(r.id); pintarBarra(); });
          const horas = edadRespuestaRO(r.fecha);
          const d = loc.dueno[r.id], c = loc.clase[r.id];
          const clasif = v => h('button', { type: 'button', class: `bt mini${v === 'positiva' ? ' pri' : ''}`, 'data-clase': v, 'aria-pressed': String(c === v), 'aria-disabled': ctx.soloLectura ? 'true' : null,
            title: ctx.soloLectura ? 'Estás en «ver como»: solo lectura' : `${CLASES.find(x => x.valor === v).texto}: pasa a ser tuya y sale de «Sin dueño»`,
            on: { click: () => { if (!ctx.soloLectura) clasificar([r.id], v); } } }, icono(CLASES.find(x => x.valor === v).icono), CLASES.find(x => x.valor === v).texto);
          return {
            estado: !d && horas !== null && horas >= 24 ? 'rojo' : 'ambar', icono: 'mail',
            motivo: [h('label', { style: { display: 'inline-flex', alignItems: 'center', gap: 'var(--s-2)', minHeight: 'var(--s-8)', cursor: 'pointer' } }, casilla, destino), ' ', c ? chipEstado(c === 'positiva' ? 'verde' : c === 'negativa' || c === 'baja' ? 'rojo' : 'gris', CLASES.find(x => x.valor === c)?.texto || c) : null,
              ' ', d ? chipEstado('azul', ctx.nombre(d)) : chipEstado('rojo', 'Sin dueño')],
            detalle: [`${r.campana} · ${cuandoTexto(r.fecha)}${horas !== null ? ` · hace ${horas < 48 ? horas + ' h' : Math.round(horas / 24) + ' días'}` : ''}${r.zona ? ' · ' + r.zona : ''}${r.ghl ? '' : ' · aún no está en GoHighLevel (se pasa cuando sea positiva)'}`, extracto],
            botones: [clasif('positiva'), clasif('negativa'), clasif('mas_tarde'), verRespuesta(ctx, r, destino, extracto),
              masDe(nombreRespuesta(r), clasif('neutra'), clasif('baja'),
                r.ghl ? abrirEn('GHL', r.ghl) : null,
                abrirLinkedIn(ctx, { almacen: 'outreach_respuestas', id: r.id, tiene: r.tiene_linkedin }),
                c === 'positiva' ? h('button', { type: 'button', class: 'bt mini', 'aria-disabled': 'true', title: 'Espera el permiso de escritura en GoHighLevel' }, icono('send'), 'Pasar a GHL') : null)],
          };
        }), { subir: false, vacio: { titulo: filtro === 'sin_dueno' ? 'Ninguna respuesta sin dueño' : 'Nada con este filtro', porque: frente === 'ro' ? 'RO no tiene campañas en Snov.io: si hace outreach por Linked Helper o Explee, entra por la hoja semanal.' : 'Todas tienen a alguien.', celebrar: filtro === 'sin_dueno' } }),
        filas.length > tope ? h('div', { class: 'tabla-mas', style: { padding: 'var(--s-2) var(--relleno) var(--s-4)' } }, h('button', { type: 'button', class: 'bt', on: { click: () => { tope += 15; pintarLista(); } } }, icono('mas'), `Ver ${Math.min(15, filas.length - tope) === 1 ? '1 respuesta más' : `${Math.min(15, filas.length - tope)} respuestas más`} (${filas.length - tope} sin ver)`)) : null].filter(Boolean));
    }
    pintarLista();
    zona.append(h('div', { class: 'pila', style: { gap: 'var(--s-3)', marginTop: 'var(--s-3)', minWidth: '0' } }, franja,
      panel({ titulo: 'Respuestas', icono: 'inbox', sub: 'Un clic clasifica y te la quedas. Marca 2 o más para varias a la vez.' },
        filtroCamp ? h('div', { style: { padding: 'var(--s-3) var(--relleno) 0' } }, filtroCamp) : null, ctx.soloLectura ? null : barra, cuerpo)));
  }

  // ---- 2 · campañas ----
  ctxN.push(panel({ titulo: 'Campañas y salud del envío', icono: 'send', sub: 'Snov.io: estado y respuestas. Rebotes y quejas por spam, todavía no.' },
    camp.length ? h('div', { class: 'cuerpo' }, tablaApilable({ filas: [...camp].sort((a, b) => b.respuestas_30d - a.respuestas_30d), columnas: [
      { clave: 'nombre', titulo: 'Campaña', principal: true },
      { clave: 'estado', titulo: 'Estado', celda: c => chipEstado(c.estado === 'Active' ? 'verde' : 'gris', c.estado === 'Active' ? 'Activa' : 'En pausa') },
      { clave: 'respuestas_30d', titulo: 'Respuestas 30 días', num: true }, { clave: 'respuestas_total', titulo: 'En total', num: true },
      { clave: 'ultima_respuesta', titulo: 'Última', celda: c => (c.ultima_respuesta ? cuandoTexto(c.ultima_respuesta) : '—') }] }),
      h('div', { class: 'fila', style: { marginTop: 'var(--s-3)' } }, frescura(fSnov), abrirEn('Snov.io', 'https://app.snov.io/')))
      : h('div', { class: 'cuerpo' }, vacioLinea(!snovLeido ? `${sinSnov}.` : `${frente === 'ro' ? 'RO no tiene campañas en Snov.io' : 'Sin campañas'}: ninguna activa o en pausa en este frente.`, { icono: 'send', quien: ctx.nombre('yessica') }))));

  // ---- 3 · resultados por cliente ----
  if (frente === 'clientes') {
    // Nombre del cliente desde la verdad única (clientes.json), nunca el escrito en el informe de outreach.
    const norm = t => String(t || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[^a-z0-9 ]/g, ' ').trim();
    const comun = ctx.verdadComun?.() || [];
    const oficial = n => { const k = norm(n).split(' ')[0]; const c = comun.find(x => norm(x.nombre).split(' ')[0] === k || norm(x.nombre).includes(norm(n))); return c?.nombre || n; };
    const filas = Object.entries(o.clientes || {}).map(([cliente, x]) => ({ cliente: oficial(cliente), canales: (x.canales || []).join(' + '), leads: x.sep?.leads, enviados: x.sep?.enviados,
      aceptaciones: x.sep?.aceptaciones, respuestas: x.sep?.respuestas, ultimo: x.ultimo_lead, prueba: x.prueba?.[0] }));
    const sd = v => (v === null || v === undefined ? h('span', { class: 'sub' }, 'sin dato') : fmt.num(v));
    ctxN.push(panel({ titulo: 'Resultados por cliente · septiembre', icono: 'cli', sub: 'Los informes de septiembre aún no existen: lo que no se sabe sale «sin dato».' },
      h('div', { class: 'cuerpo' }, tablaApilable({ filas: filas.sort((a, b) => (b.leads || 0) - (a.leads || 0)), columnas: [
        { clave: 'cliente', titulo: 'Cliente', principal: true }, { clave: 'canales', titulo: 'Canales' },
        { clave: 'leads', titulo: 'Leads', num: true, celda: f => sd(f.leads) }, { clave: 'enviados', titulo: 'Enviados', num: true, celda: f => sd(f.enviados) },
        { clave: 'aceptaciones', titulo: 'Aceptadas en LinkedIn', num: true, celda: f => sd(f.aceptaciones) }, { clave: 'respuestas', titulo: 'Respuestas', num: true, celda: f => sd(f.respuestas) },
        { clave: 'ultimo', titulo: 'Último lead', celda: f => (f.ultimo ? fechaCortaRO(FECHAS_RO.dia(f.ultimo)) : '—') },
        { clave: 'prueba', titulo: 'Atajo', celda: f => abrirEn('ClickUp', f.prueba, { motivo: 'Sin tarea de informe' }) }] }),
      avisoParcial('Leads contados a partir de los avisos en los chats del equipo y de las hojas públicas. Las hojas privadas de Linked Helper necesitan permiso de lectura de hojas.', { titulo: 'A medias.' }),
      h('div', { class: 'fila', style: { marginTop: 'var(--s-3)' } }, frescura(fMili)))));
  } else {
    ctxN.push(avisoParcial('Las citas que consigue el outreach de RO solo se pueden contar cuando cada lead interesado entre en GoHighLevel como «outreach», con su campaña y su canal. Hoy no hay ninguno.', { titulo: 'Citas de la semana: todavía no.' }));
  }

  // ---- 4 · hoja semanal declarada (los lunes, abierta arriba del contexto) ----
  const lunes = /^lun/i.test(String(ctx.fechas?.diaSemana?.(ctx.hoy) || ''));
  if (!resumen) (lunes ? ctxN.unshift.bind(ctxN) : ctxN.push.bind(ctxN))(hojaSemanal(ctx, camp, loc));
  for (const a of o.avisos || []) ctxN.push(avisoParcial(limpiaTexto(a), { tipo: 'info' }));
  zona.append(h('details', { class: 'que-es', open: lunes || resumen || null, style: { marginTop: 'var(--s-4)' } },
    h('summary', {}, lunes ? 'Hoja semanal (hoy es lunes), campañas y resultados' : 'Campañas, resultados y hoja semanal'),
    h('div', { class: 'pila', style: { marginTop: 'var(--s-3)', gap: 'var(--s-4)' } }, ctxN)));
}

/** 3-oct · nombre a la vista: «Nombre Apellido · empresa» (en claro si el servidor lo ha abierto para quien lo ve).
 *  Sin nombre: «Sin nombre · respuesta del 2-oct», nunca una letra suelta. */
function nombreRespuesta(r) {
  const n = String(r.nombre_m || '').trim();
  const vacio = !n || n === '(sin nombre)' || /^\S$/.test(n);
  const dia = diaCorto(r.fecha);
  const base = vacio ? `Sin nombre${dia ? ' · respuesta del ' + dia : ''}` : n;
  return `${base}${r.empresa_m ? ' · ' + r.empresa_m : ''}`;   // un dato: sin limpiaTexto (se comía el «···» final)
}

/** V2 (C-2) · «Ver respuesta»: nombre completo, correo y el extracto de lo que contestó, del almacén privado (por ver_dato:
 *  queda en el rastro). Así outreach clasifica sin salir a Snov.io o LinkedIn. Sin permiso, no sale el botón. */
function verRespuesta(ctx, r, destino, extracto) {
  if (!puedeAbrir(ctx, 'outreach_respuestas')) return null;
  const b = h('button', { type: 'button', class: 'bt mini' }, icono('ojo'), 'Ver respuesta');
  b.addEventListener('click', async () => {
    b.disabled = true;
    try {
      const leer = async campo => { try { return (await ctx.verDato({ almacen: 'ventas_ro/_privado/outreach_respuestas', ref: r.id, campo })).valor || ''; } catch (e) { if (e.status === 403) throw e; return ''; } };
      const [nombre, correo, texto] = [await leer('nombre'), await leer('correo'), await leer('extracto')];
      destino.replaceChildren(h('b', {}, nombre || r.nombre_m || '—'), correo ? h('span', { class: 'sub' }, ` · ${correo}`) : null);
      extracto.hidden = false;
      extracto.textContent = texto ? `«${texto}»` : 'Snov.io no ha dado todavía el texto de esta respuesta: llega con la próxima lectura. Mientras, ábrela en Snov.io.';
      b.remove();
    } catch (e) { b.disabled = false; b.replaceChildren(icono('candado'), e.status === 403 ? 'Esta respuesta no es de tus campañas' : (e.message || 'No permitido')); }
  });
  return b;
}

function hojaSemanal(ctx, camp, loc) {
  const lunes = ctx.fechas.semana().desde;   // V2-E: lunes de esta semana en el calendario de Madrid (antes UTC / zona del Mac)
  const f = {
    semana: campo({ etiqueta: 'Semana (lunes)', nombre: 'semana', tipo: 'date', valor: lunes }),
    contactos: campo({ etiqueta: 'Contactos únicos', nombre: 'contactos', tipo: 'number', valor: '0', min: 0 }),
    respuestas: campo({ etiqueta: 'Respuestas', nombre: 'respuestas', tipo: 'number', valor: '0', min: 0 }),
    positivas: campo({ etiqueta: 'Positivas', nombre: 'positivas', tipo: 'number', valor: '0', min: 0 }),
  };
  const elegido = { campana: '', canal: 'correo' };
  const chipsCamp = chipsFiltro({ etiqueta: 'Campaña', valor: '', alCambiar: v => { elegido.campana = v || ''; },
    opciones: [{ valor: '', texto: 'Sin elegir' }, ...[...camp.map(c => c.nombre), 'Linked Helper · otra', 'Explee · otra'].map(c => ({ valor: c, texto: c.length > 34 ? c.slice(0, 32) + '…' : c }))] });
  const chipsCanal = chipsFiltro({ etiqueta: 'Canal', valor: 'correo', alCambiar: v => { elegido.canal = v || 'correo'; },
    opciones: [{ valor: 'correo', texto: 'Correo', icono: 'mail' }, { valor: 'linkedin', texto: 'LinkedIn', icono: 'persona' }] });
  const val = n => (n in elegido ? elegido[n] : f[n].querySelector('input,select').value.trim());
  const declaradas = loc.hojas.slice(-8).reverse();
  return panel({ titulo: 'Hoja semanal', icono: 'doc', sub: 'El lunes antes de las 12:00, una fila por campaña. Estas cifras llevan el sello «declarada», distinto del automático.' },
    h('div', { class: 'cuerpo pila' },
      chipsCamp, chipsCanal,
      h('div', { style: { display: 'grid', gap: 'var(--s-3)', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 180px), 1fr))' } }, Object.values(f)),
      vistaPrevia('la fila queda guardada con tu nombre y la hora.'),
      botonDeshacer({ texto: 'Guardar fila', hecho: 'Fila guardada', mini: false, pri: true, soloLectura: ctx.soloLectura,
        validar: () => (!val('campana') ? 'Elige la campaña' : (+val('positivas') > +val('respuestas') || +val('respuestas') > +val('contactos')) ? 'Positivas ≤ respuestas ≤ contactos' : null),
        alHacer: async () => {
          await encolar(ctx, { que: 'hoja_semanal', sobre: val('campana'), herramienta: 'app',
            texto: `semana ${val('semana')} · ${val('canal')} · contactos ${val('contactos')} · respuestas ${val('respuestas')} · positivas ${val('positivas')}` });
          avisoFlotante('Fila guardada');
          return 'Fila guardada';
        } }),
      declaradas.length ? h('div', {}, h('p', { class: 'titulo-seccion' }, icono('hist'), 'Últimas filas ', selloMedible('medias', 'Declarada a mano')),
        h('ul', { class: 'lista-i', style: { marginTop: 'var(--s-1)' } }, declaradas.map(a => h('li', {}, h('span', { class: 'ico-c s gris' }, icono('doc')), h('span', { class: 't', style: { whiteSpace: 'normal' } }, h('b', {}, a.sobre), ` · ${a.texto}`))))) : null));
}

export default {
  id: 'prospeccion',
  titulo: 'Prospección y outreach',
  grupo: 'Ventas de RO',
  puestos_que_lo_ven: { direccion: 'todo', jefa_crm: 'todo', outreach: 'suyo', operaciones: 'resumen' },
  async render(contenedor, ctx) { await pintar(contenedor, ctx); },
};

function edadRespuestaRO(fecha) { const h = FECHAS_RO.horasDesde(fecha); return h === null || h < 0 ? null : Math.round(h); }

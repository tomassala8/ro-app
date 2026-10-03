// modulos/envios.js · Salidas a herramientas (3-oct-2026): un solo centro con pestañas Correos / ClickUp / Chat.
// · Correos (envíos verificados): encargo de Tomás «cualquier correo que se envíe, asegurarnos de que se está enviando bien;
//   también desde la parte de atrás, para asegurarnos de que el sistema nunca está fallando». GET /api/envios (envios.py):
//   cada envío con su estado (simulado → pendiente → enviado → confirmado | fallido | rebotado), sus pasos y avisos.
//   «Reintentar»: POST /api/envios/reintentar { id } — SIMULADO hasta que Tomás active los envíos.
// · ClickUp y Chat (sincronía con herramientas): encargo de Tomás «que todos los cambios que hace el equipo dentro de la
//   plataforma impactan en ClickUp, pero también se guardan como copia por si no llegaran a impactar; y lo mismo con el
//   chat». GET /api/sincronia (sincronia.py): cada cambio guardado en la base de la app (la copia segura) con su estado
//   (simulado | pendiente → enviado → confirmado | fallido | conflicto → descartado), el objeto de ClickUp y el cambio exacto
//   que puso el SERVIDOR. Fallidos y conflictos, arriba. En conflicto, las dos versiones y «¿cuál se queda?»
//   (POST /api/sincronia/elegir). «Reintentar» y «Ya está en ClickUp (a mano)», simulados mientras ClickUp esté apagado.
// Rutas: #/envios (Correos), #/envios/<id> (un envío), #/envios/clickup[/<id>], #/envios/chat[/<id>].
// El navegador nunca fija estado, destinatario, objeto ni cambio: solo manda el id (y «gana»).

import { fmt, tile, tiles, chipsFiltro, chipEstado, vacio, panel, avisoParcial, avisoFlotante, icono, pestanas, botonConfirmar } from '../componentes.js';
import { h } from './personas_comun.js';
import { llevarA } from './_ir.js';

const ESTADO = {
  fallido: ['rojo', 'Fallido'], rebotado: ['rojo', 'Rebotado'], pendiente: ['ambar', 'En cola'], enviado: ['ambar', 'Enviado · comprobando'],
  simulado: ['gris', 'Simulado'], confirmado: ['verde', 'Confirmado'],
};
const ORDEN = ['fallido', 'rebotado', 'pendiente', 'enviado', 'simulado', 'confirmado'];
const EVENTO = {
  creado: 'Pedido (simulado: no sale nada)', en_cola: 'En cola para salir', enviado: 'La herramienta lo acepta', ya_estaba: 'Ya estaba en el hilo: no se duplica',
  error_envio: 'Error al mandarlo', verificado: 'Comprobado en el hilo', rebote: 'Rebote detectado', no_aparece: 'No aparece en el hilo',
  distinto: 'En el hilo con otros datos', apagado: 'Canal sin envío real', aviso: 'Aviso a quien lo mandó y a Agus',
  reintento_simulado: 'Reintento simulado', reintento_pedido: 'Reintento pedido',
};
const ICONO_CANAL = { desk: 'mail', whatsapp: 'wa', ghl: 'base' };
const FILTROS = {
  problemas: x => x.estado === 'fallido' || x.estado === 'rebotado',
  curso: x => x.estado === 'pendiente' || x.estado === 'enviado',
  confirmado: x => x.estado === 'confirmado',
  simulado: x => x.estado === 'simulado',
  '': () => true,
};

const cuando = t => (t ? `${fmt.fecha(t)} ${new Date(t).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit', timeZone: 'Europe/Madrid' })}` : '—');

function cartel(D) {
  const reales = D.modo?.reales;
  return h('div', { class: `aviso${reales ? ' info' : ''}`, role: 'note', 'data-cartel': 'envios', style: { padding: '16px 20px', alignItems: 'center', gap: '16px' } },
    h('span', { class: 'ico', 'aria-hidden': 'true' }, icono(reales ? 'send' : 'escudo')),
    h('div', {},
      h('b', { style: { font: 'var(--t-h2)', display: 'block' } }, reales ? D.modo.texto : 'Envíos en simulación · los activa Tomás'),
      h('p', { style: { margin: '4px 0 0', font: 'var(--t-cuerpo)', maxWidth: '80ch' } },
        reales ? 'Cada envío sale, se comprueba en la herramienta al momento y, si falla, avisa a quien lo mandó y a Agus.'
          : 'Hoy no sale nada de la app: cada correo, WhatsApp o mensaje de GHL queda aquí como «simulado», con quién lo pidió y a quién iría. El día que Tomás los active, cada uno se comprobará en la herramienta (que está en el hilo, con el texto y el destinatario correctos) y, si falla o rebota, avisará a quien lo mandó y a Agus.')));
}

function tilesResumen(D) {
  const t7 = D.tasas?.['7'] || {};
  const t30 = D.tasas?.['30'] || {};
  const malos = (D.por_estado?.fallido || 0) + (D.por_estado?.rebotado || 0);
  const s = D.salud;
  const colorSalud = s ? ({ verde: 'verde', ambar: 'ambar', rojo: 'rojo' }[s.color] || '') : '';
  const pctTile = (t, dias) => tile({ icono: 'ok', etiqueta: `Confirmados · ${dias} días`, valor: t.pct === null || t.pct === undefined ? null : `${fmt.num(t.pct, 1)} %`,
    unidad: t.terminados ? `${t.confirmados} de ${t.terminados}` : '', estado: t.pct === null || t.pct === undefined ? '' : t.pct >= 98 ? 'verde' : t.pct >= 90 ? 'ambar' : 'rojo',
    sinDato: D.modo?.reales ? 'ningún envío terminado' : 'aún no sale ningún envío real',
    contexto: `${fmt.plural(t.simulados || 0, 'simulado')} en ${dias} días${t.en_curso ? ` · ${t.en_curso} en curso` : ''}`, medible: D.modo?.reales ? 'hoy' : 'no',
    medibleDetalle: D.modo?.reales ? null : 'Se medirá cuando Tomás active los envíos reales' });
  return tiles([
    pctTile(t7, 7), pctTile(t30, 30),
    tile({ icono: 'alert', etiqueta: 'Fallidos y rebotados', valor: malos, unidad: malos === 1 ? 'envío' : 'envíos', estado: malos ? 'rojo' : 'verde',
      contexto: malos ? 'Arriba en la lista, con el motivo en llano' : 'Ninguno: nada que mirar' }),
    tile({ icono: 'send', etiqueta: 'Envío de correos (Desk)', valor: s ? s.titular : null, estado: colorSalud, sinDato: 'falta la prueba de conexiones',
      contexto: s ? `Probado ${cuando(s.ultima_prueba ? s.ultima_prueba.replace(' ', 'T') : null)}` : 'Llave de escritura, departamento, dirección de envío y firmas',
      href: '#/conexiones/envio_correos', ir: 'Ver la conexión' }),
  ]);
}

function pasosDe(x) {
  return h('ol', { class: 'tiempo', style: { margin: '8px 0 0' } }, (x.pasos || []).map(p =>
    h('li', { class: ESTADO[p.estado]?.[0] || '' },
      h('div', { class: 'f' }, cuando(p.hora)),
      h('div', { class: 't' }, `${EVENTO[p.evento] || p.evento} · ${ESTADO[p.estado]?.[1] || p.estado}${p.intento ? ` · intento ${p.intento + 1}` : ''}`),
      p.motivo ? h('div', { class: 'd' }, p.motivo) : null)));
}

function tarjeta(x, ctx, D, alCambiar) {
  const [color, texto] = ESTADO[x.estado] || ['gris', x.estado];
  const estado = h('span', { class: 'sub', role: 'status', 'aria-live': 'polite' });
  const puede = x.puede_reintentar && (x.estado === 'simulado' || (x.estado === 'fallido' && (x.seguro_reintentar || !D.modo?.reales)));
  const bt = puede ? h('button', { type: 'button', class: 'bt mini', 'data-atajo': 'e', title: D.modo?.reales ? 'Lo vuelve a mandar, mirando antes si ya llegó (nunca duplica)' : 'Simulado: deja constancia, no sale nada' },
    icono('recargar'), D.modo?.reales ? 'Reintentar' : 'Reintentar (simulado)') : null;
  bt?.addEventListener('click', async () => {
    if (ctx.soloLectura) { estado.textContent = 'Estás en «ver como»: solo lectura.'; return; }
    bt.disabled = true;
    estado.textContent = 'Pidiendo el reintento…';
    try {
      const r = await ctx.api('envios/reintentar', { metodo: 'POST', cuerpo: { id: x.id } });
      estado.textContent = r.mensaje || 'Hecho.';
      avisoFlotante(r.mensaje || 'Hecho.', { icono: r.simulado ? 'escudo' : 'ok' });   // queda a la vista aunque la lista se repinte
      alCambiar?.();
    } catch (e) {
      bt.disabled = false;
      estado.textContent = `No se pudo: ${e.message}`;
    }
  });
  return h('article', { class: `pm-tarjeta ${color}`, 'data-envio': String(x.id), 'data-fila': '', style: { minWidth: 0, overflowWrap: 'anywhere' } },
    h('div', { class: 'pm-cab' }, h('span', { class: `ico-c ${color}` }, icono(ICONO_CANAL[x.canal] || 'send')),
      h('span', { class: 't' }, h('b', {}, x.destinatario?.nombre || '—'),
        h('span', {}, `${x.canal_nombre}${x.cliente ? ' · ' + x.cliente : ''} · pedido por ${x.quien_alias} ${fmt.hace(x.creado)}`)),
      h('span', { class: 'der' }, chipEstado(color, texto))),
    x.motivo ? h('p', { style: { margin: 0, font: 'var(--t-cuerpo)', maxWidth: '72ch' } }, x.motivo) : null,
    h('dl', { class: 'pm-kv' },
      h('dt', {}, 'Envío'), h('dd', {}, `n.º ${x.id} · ${x.modo === 'simulado' ? 'simulado' : x.modo}`),
      h('dt', {}, 'Desde'), h('dd', {}, `${texto} desde ${cuando(x.desde)}`),
      x.intentos ? [h('dt', {}, 'Intentos'), h('dd', {}, String(x.intentos))] : null,
      x.asunto ? [h('dt', {}, 'Asunto'), h('dd', {}, x.asunto)] : null,
      x.avisado ? [h('dt', {}, 'Aviso'), h('dd', {}, `Avisados ${x.quien_alias} y Agus`)] : null),
    h('details', { class: 'que-es' }, h('summary', {}, `Pasos (${(x.pasos || []).length}) y mensaje`),
      pasosDe(x),
      x.texto_oculto ? h('p', { class: 'sub' }, 'El texto no se enseña: no llevas este cliente.')
        : x.texto ? h('p', { style: { whiteSpace: 'pre-wrap', margin: '8px 0 0', font: 'var(--t-cuerpo)', maxWidth: '72ch' } }, x.texto) : null),
    bt ? h('div', { class: 'fila', style: { alignItems: 'center', gap: '12px', flexWrap: 'wrap' } }, bt, estado) : null);
}

async function cargar(ctx) {
  try { return await ctx.api('envios'); } catch (e) { return { error: e.message, status: e.status }; }
}

function cuerpo(ctx, D, repintar, objetivo) {
  const L = D.envios || [];
  const n = f => L.filter(FILTROS[f]).length;
  const caja = h('div', { class: 'pm-conex' });
  let filtro = '';
  const pintar = () => {
    const ls = L.filter(FILTROS[filtro] || FILTROS['']).sort((a, b) => ORDEN.indexOf(a.estado) - ORDEN.indexOf(b.estado) || String(b.creado).localeCompare(String(a.creado)));
    caja.replaceChildren(...(ls.length ? ls.map(x => tarjeta(x, ctx, D, repintar))
      : [vacio({ icono: filtro === 'problemas' ? 'ok' : 'send', tono: filtro === 'problemas' ? 'celebrar' : 'neutro',
        titulo: filtro === 'problemas' ? 'Ningún envío fallido ni rebotado' : 'Ningún envío aquí',
        texto: L.length ? 'Cambia el filtro para ver el resto.' : 'Cuando alguien conteste un correo, un WhatsApp o un contacto de GHL desde la app, saldrá aquí.' })]));
  };
  const chips = chipsFiltro({ clave: 'envios.filtro', etiqueta: 'Ver', valor: n('problemas') ? 'problemas' : '', opciones: [
    { valor: 'problemas', texto: 'Fallidos primero', icono: 'alert', cuenta: n('problemas'), cuentaEstado: 'rojo' },
    { valor: '', texto: 'Todos', cuenta: L.length },
    { valor: 'curso', texto: 'En curso', icono: 'clock', cuenta: n('curso') },
    { valor: 'confirmado', texto: 'Confirmados', icono: 'ok', cuenta: n('confirmado') },
    { valor: 'simulado', texto: 'Simulados', icono: 'escudo', cuenta: n('simulado') }],
  alCambiar: v => { filtro = v; pintar(); } });
  filtro = chips.valor();
  const obj = objetivo ? L.find(x => String(x.id) === String(objetivo)) : null;
  if (obj && !(FILTROS[filtro] || FILTROS[''])(obj)) filtro = '';
  pintar();
  return [
    cartel(D),
    tilesResumen(D),
    panel({ titulo: 'Cola de envíos', icono: 'send',
      sub: `${D.ve_todos ? 'Los de todo el equipo' : 'Los tuyos'} · lo que falla, arriba y con el motivo en llano. Cada paso lleva su hora.`,
      acciones: h('button', { type: 'button', class: 'bt mini', on: { click: () => repintar() } }, icono('recargar'), 'Actualizar') },
    h('div', { class: 'pm-pad' }, chips), caja),
    panel({ titulo: 'Cómo se comprueba cada envío', icono: 'escudo', sub: 'Lo hace el servidor, al momento y en cada vuelta de la tubería. Nada sale hasta que Tomás lo active.' },
      h('ol', { class: 'tiempo', style: { margin: '0', padding: '12px var(--relleno)' } },
        [['Se pide', 'Alguien contesta desde la app. El servidor pone el destinatario (el contacto del ticket, el grupo o el contacto del CRM) y la dirección de envío: nunca las escribe el navegador.'],
          ['Sale', 'Una clave única por envío: si algo se corta a medias, antes de reintentar se mira si ya llegó. Nunca se manda dos veces.'],
          ['Se comprueba', 'Se relee en la herramienta que está en el hilo con el texto y el destinatario correctos. Los rebotes se siguen mirando 48 h.'],
          ['Si falla', 'Un reintento solo si es seguro (fallo de red). Si no, «fallido» con el motivo y aviso a quien lo mandó y a Agus en #avisos-dirección.'],
          ['Canario', D.canario?.texto || 'Un correo de prueba diario a un buzón interno. Solo se enciende con el sí de Tomás.']]
          .map(([t, d]) => h('li', {}, h('div', { class: 't' }, t), h('div', { class: 'd' }, d))))),
    D.solo_lectura ? avisoParcial('Estás en «ver como»: ves lo que verían las dos personas y no se puede reintentar.', { tipo: 'info' }) : null,
  ].filter(Boolean);
}


// ===================================================================== ClickUp y Chat (sincronía con herramientas)
const ESTADO_S = {
  conflicto: ['rojo', 'Dos versiones: elige'], fallido: ['rojo', 'No está en ClickUp'], pendiente: ['ambar', 'Hecho en la app · pendiente de ClickUp'],
  enviado: ['ambar', 'Enviado · comprobando'], simulado: ['gris', 'Hecho en la app · pendiente de ClickUp'], confirmado: ['verde', 'En ClickUp (comprobado)'],
  descartado: ['gris', 'Se quedó lo de ClickUp'],
};
const ORDEN_S = ['conflicto', 'fallido', 'pendiente', 'enviado', 'simulado', 'confirmado', 'descartado'];
const EVENTO_S = {
  creado: 'Guardado en la app (simulación: ClickUp apagado)', en_cola: 'Guardado en la app y en cola para ClickUp', enviado: 'ClickUp lo acepta',
  ya_estaba: 'Ya estaba en ClickUp: no se repite', verificado: 'Comprobado en ClickUp', reintento_programado: 'ClickUp no responde: reintento programado',
  agotado: 'Sin respuesta tras varios intentos', llave: 'La llave de ClickUp no vale', error: 'ClickUp lo rechaza', apagado: 'ClickUp real apagado',
  no_aparece: 'No aparece al releer', no_soportado: 'Sin traductor: a mano', destinatario: 'Sin destino en ClickUp', conflicto: 'Alguien lo cambió en ClickUp',
  gana_app: 'Se queda lo de la app', gana_clickup: 'Se queda lo de ClickUp', hecho_a_mano: 'Pasado a mano en ClickUp', espera: 'Espera al cambio anterior de la tarea',
  reintento_simulado: 'Reintento simulado', reintento_pedido: 'Reintento pedido', reintento_tras_llave: 'La llave vuelve a valer: a la cola',
  aviso: 'Aviso a quien lo hizo y a Agus',
};
const FILTROS_S = {
  problemas: x => x.estado === 'fallido' || x.estado === 'conflicto',
  curso: x => x.estado === 'pendiente' || x.estado === 'enviado',
  simulado: x => x.estado === 'simulado',
  confirmado: x => x.estado === 'confirmado' || x.estado === 'descartado',
  '': () => true,
};
const malos = (L, f = FILTROS_S.problemas) => (L || []).filter(f).length;

function cartelSinc(S, canal) {
  const puente = S.modo?.chat_puente || 'apagado';
  const reales = canal === 'chat' ? S.modo?.canales?.chat : S.modo?.reales;
  const titulo = canal === 'chat'
    ? (puente === 'apagado' ? 'Chat del equipo: vive en la app · puente con ClickUp apagado' : puente === 'simulacion' ? 'Puente de chat en simulación' : 'Puente de chat activo')
    : (reales ? S.modo.texto : 'ClickUp en simulación · lo activa Tomás');
  const texto = canal === 'chat'
    ? (puente === 'apagado'
      ? 'Lo que el equipo escribe en los grupos de la app se guarda en la base de la app (imborrable) y no sale a ClickUp; el chat de ClickUp se ve en espejo de solo lectura. El puente app ↔ ClickUp está preparado con la misma cola, clave única y comprobación, y apagado. Aquí salen además los mensajes que se mandan a un canal de ClickUp desde una ficha.'
      : 'Los mensajes de los grupos emparejados se copian en la cola hacia el chat de ClickUp y lo de ClickUp entra en la app, una sola vez. Lo editado o borrado en ClickUp deja una nota; en la app nada se borra.')
    : (reales ? 'Cada cambio se guarda primero aquí, sale a ClickUp, se relee para confirmarlo y, si no está o alguien lo cambió allí, avisa con las dos versiones.'
      : 'Hoy no se escribe nada en ClickUp: cada cambio del equipo (mover o aprobar una tarea, comentar, imputar horas, asignar, crear una tarea) queda guardado aquí con quién, cuándo, qué tarea y el cambio exacto, como «hecho en la app · pendiente de ClickUp». Mientras esté apagado, se pasa a mano y se marca «Ya está en ClickUp».');
  return h('div', { class: `aviso${reales ? ' info' : ''}`, role: 'note', 'data-cartel': `sinc-${canal}`, style: { padding: '16px 20px', alignItems: 'center', gap: '16px' } },
    h('span', { class: 'ico', 'aria-hidden': 'true' }, icono(canal === 'chat' ? 'chat' : reales ? 'conexiones' : 'escudo')),
    h('div', {}, h('b', { style: { font: 'var(--t-h2)', display: 'block' } }, titulo),
      h('p', { style: { margin: '4px 0 0', font: 'var(--t-cuerpo)', maxWidth: '80ch' } }, texto)));
}

function tilesSinc(S, L) {
  const inf = S.informe || {};
  const pe = s => L.filter(x => x.estado === s).length;
  const sinRef = inf.total || 0;
  return tiles([
    tile({ icono: 'clock', etiqueta: `Sin reflejar · más de ${fmt.num(inf.horas || 4)} h`, valor: sinRef, unidad: sinRef === 1 ? 'cambio' : 'cambios',
      estado: sinRef ? (S.modo?.reales ? 'rojo' : 'ambar') : 'verde', contexto: sinRef ? (S.modo?.reales ? 'Hechos en la app y aún no en ClickUp' : 'En simulación: hay que pasarlos a mano') : 'Todo lo hecho en la app está en ClickUp' }),
    tile({ icono: 'alert', etiqueta: 'Conflictos', valor: pe('conflicto'), unidad: pe('conflicto') === 1 ? 'cambio' : 'cambios', estado: pe('conflicto') ? 'rojo' : 'verde',
      contexto: pe('conflicto') ? 'Dos versiones: elige cuál se queda' : 'Ninguno: nadie lo ha cambiado a la vez en ClickUp' }),
    tile({ icono: 'cerrar', etiqueta: 'Fallidos', valor: pe('fallido'), unidad: pe('fallido') === 1 ? 'cambio' : 'cambios', estado: pe('fallido') ? 'rojo' : 'verde',
      contexto: pe('fallido') ? 'Con el motivo en llano; siguen guardados aquí' : 'Ninguno' }),
    tile({ icono: 'ok', etiqueta: 'En ClickUp (comprobados)', valor: S.modo?.reales ? pe('confirmado') : null, unidad: 'cambios', estado: S.modo?.reales ? 'verde' : '',
      sinDato: 'aún no sale ningún cambio real', contexto: `${fmt.plural(pe('simulado'), 'cambio guardado', 'cambios guardados')} en simulación`,
      medible: S.modo?.reales ? 'hoy' : 'no', medibleDetalle: S.modo?.reales ? null : 'Se medirá cuando Tomás active ClickUp real' }),
  ]);
}

function pasosSinc(x) {
  return h('ol', { class: 'tiempo', style: { margin: '8px 0 0' } }, (x.pasos || []).map(p =>
    h('li', { class: ESTADO_S[p.estado]?.[0] || '' },
      h('div', { class: 'f' }, cuando(p.hora)),
      h('div', { class: 't' }, `${EVENTO_S[p.evento] || p.evento} · ${ESTADO_S[p.estado]?.[1] || p.estado}${p.intento ? ` · intento ${p.intento + 1}` : ''}`),
      p.motivo ? h('div', { class: 'd' }, p.motivo) : null)));
}

async function pedirSinc(ctx, ruta, cuerpo, estado, alCambiar) {
  if (ctx.soloLectura) { estado.textContent = 'Estás en «ver como»: solo lectura.'; return 'Solo lectura'; }
  const r = await ctx.api(`sincronia/${ruta}`, { metodo: 'POST', cuerpo });
  avisoFlotante(r.mensaje || 'Hecho.', { icono: r.simulado ? 'escudo' : 'ok' });
  setTimeout(() => alCambiar?.(), 600);
  return r.mensaje || 'Hecho';
}

function tarjetaSinc(x, ctx, S, alCambiar) {
  const [color, texto] = ESTADO_S[x.estado] || ['gris', x.estado];
  const estado = h('span', { class: 'sub', role: 'status', 'aria-live': 'polite' });
  const botones = [];
  if (x.estado === 'conflicto' && x.puede_tocar) {
    botones.push(botonConfirmar({ texto: 'Que se quede lo de la app', mini: true, soloLectura: ctx.soloLectura, confirmar: 'Sí, lo de la app',
      pregunta: `¿Pisar ClickUp con «${x.versiones?.app ?? '—'}»?`, alConfirmar: () => pedirSinc(ctx, 'elegir', { id: x.id, gana: 'app' }, estado, alCambiar) }));
    botones.push(botonConfirmar({ texto: 'Que se quede lo de ClickUp', mini: true, soloLectura: ctx.soloLectura, confirmar: 'Sí, lo de ClickUp',
      pregunta: `¿Dejar «${x.versiones?.clickup ?? '—'}» y no aplicar el cambio de la app?`, alConfirmar: () => pedirSinc(ctx, 'elegir', { id: x.id, gana: 'clickup' }, estado, alCambiar) }));
  }
  if (x.puede_tocar && (x.estado === 'simulado' || (x.estado === 'fallido' && (x.seguro_reintentar || !S.modo?.reales)))) {
    const bt = h('button', { type: 'button', class: 'bt mini', title: S.modo?.reales ? 'Lo vuelve a mandar, mirando antes si ya está (nunca duplica)' : 'Simulado: deja constancia, no escribe en ClickUp' },
      icono('recargar'), S.modo?.reales ? 'Reintentar' : 'Reintentar (simulado)');
    bt.addEventListener('click', async () => {
      bt.disabled = true; estado.textContent = 'Pidiendo el reintento…';
      try { estado.textContent = await pedirSinc(ctx, 'reintentar', { id: x.id }, estado, alCambiar); } catch (e) { bt.disabled = false; estado.textContent = `No se pudo: ${e.message}`; }
    });
    botones.push(bt);
  }
  if (x.puede_a_mano && ['simulado', 'fallido', 'pendiente'].includes(x.estado)) {
    botones.push(botonConfirmar({ texto: 'Ya está en ClickUp (a mano)', mini: true, soloLectura: ctx.soloLectura, confirmar: 'Sí, ya está',
      pregunta: '¿Lo has pasado tú a ClickUp? Queda en el rastro con tu nombre.', alConfirmar: () => pedirSinc(ctx, 'a_mano', { id: x.id }, estado, alCambiar) }));
  }
  const tituloObj = x.objeto?.url ? h('a', { href: x.objeto.url, target: '_blank', rel: 'noopener', title: 'Abrir en ClickUp' }, x.objeto?.nombre || x.objeto?.ref || '—')
    : h('b', {}, x.objeto?.nombre || x.objeto?.ref || '—');
  return h('article', { class: `pm-tarjeta ${color}`, 'data-cambio': String(x.id), 'data-fila': '', style: { minWidth: 0, overflowWrap: 'anywhere' } },
    h('div', { class: 'pm-cab' }, h('span', { class: `ico-c ${color}` }, icono(x.canal === 'chat' ? 'chat' : x.estado === 'conflicto' ? 'alert' : 'check')),
      h('span', { class: 't' }, tituloObj, h('span', {}, `${x.que}${x.cliente ? ' · ' + x.cliente : ''} · hecho por ${x.quien_alias} ${fmt.hace(x.creado)}`)),
      h('span', { class: 'der' }, chipEstado(color, texto))),
    x.motivo ? h('p', { style: { margin: 0, font: 'var(--t-cuerpo)', maxWidth: '72ch' } }, x.motivo) : null,
    x.estado === 'conflicto' && x.versiones ? h('dl', { class: 'pm-kv', 'data-versiones': '' },
      h('dt', {}, 'En la app'), h('dd', {}, h('b', {}, `«${x.versiones.app ?? '—'}»`), ` · lo hizo ${x.quien_alias} ${fmt.hace(x.creado)}`),
      h('dt', {}, 'En ClickUp'), h('dd', {}, h('b', {}, `«${x.versiones.clickup ?? '—'}»`), x.versiones.clickup_cambiado ? ` · cambiado allí ${fmt.hace(x.versiones.clickup_cambiado)}` : '')) : null,
    h('dl', { class: 'pm-kv' },
      h('dt', {}, 'Cambio'), h('dd', {}, `n.º ${x.id} · ${x.que}${x.modo === 'simulado' ? ' · simulado' : ''}`),
      h('dt', {}, 'Desde'), h('dd', {}, `${texto} desde ${cuando(x.desde)}`),
      x.intentos ? [h('dt', {}, 'Intentos'), h('dd', {}, String(x.intentos))] : null,
      x.ignorado?.length ? [h('dt', {}, 'Ignorado'), h('dd', {}, `La pantalla mandó ${x.ignorado.map(k => `«${k}»`).join(', ')}: el servidor no lo usa (la tarea y el cambio los pone él).`)] : null,
      x.avisado ? [h('dt', {}, 'Aviso'), h('dd', {}, `Avisados ${x.quien_alias} y Agus`)] : null),
    h('details', { class: 'que-es' }, h('summary', {}, `Pasos (${(x.pasos || []).length})${x.texto || x.texto_oculto ? ' y texto' : ''}`),
      pasosSinc(x),
      x.texto_oculto ? h('p', { class: 'sub' }, 'El texto no se enseña: no llevas este cliente.')
        : x.texto ? h('p', { style: { whiteSpace: 'pre-wrap', margin: '8px 0 0', font: 'var(--t-cuerpo)', maxWidth: '72ch' } }, x.texto) : null),
    botones.length ? h('div', { class: 'fila', style: { alignItems: 'center', gap: '12px', flexWrap: 'wrap' } }, ...botones, estado) : null);
}

function cuerpoSinc(ctx, S, canal, repintar, objetivo) {
  const L = (S.cambios || []).filter(x => x.canal === canal);
  const n = f => L.filter(FILTROS_S[f]).length;
  const caja = h('div', { class: 'pm-conex' });
  let filtro = '';
  const pintar = () => {
    const ls = L.filter(FILTROS_S[filtro] || FILTROS_S['']).sort((a, b) => ORDEN_S.indexOf(a.estado) - ORDEN_S.indexOf(b.estado) || String(b.creado).localeCompare(String(a.creado)));
    caja.replaceChildren(...(ls.length ? ls.map(x => tarjetaSinc(x, ctx, S, repintar))
      : [vacio({ icono: filtro === 'problemas' ? 'ok' : canal === 'chat' ? 'chat' : 'check', tono: filtro === 'problemas' ? 'celebrar' : 'neutro',
        titulo: filtro === 'problemas' ? 'Ningún fallido ni conflicto' : 'Ningún cambio aquí',
        texto: L.length ? 'Cambia el filtro para ver el resto.' : canal === 'chat' ? 'Cuando alguien mande un mensaje a un canal de ClickUp desde la app, saldrá aquí.'
          : 'Cuando alguien apruebe una pieza, mueva o comente una tarea desde la app, saldrá aquí al momento.' })]));
  };
  const chips = chipsFiltro({ clave: `sinc.${canal}.filtro`, etiqueta: 'Ver', valor: n('problemas') ? 'problemas' : '', opciones: [
    { valor: 'problemas', texto: 'Fallidos y conflictos', icono: 'alert', cuenta: n('problemas'), cuentaEstado: 'rojo' },
    { valor: '', texto: 'Todos', cuenta: L.length },
    { valor: 'curso', texto: 'Pendientes', icono: 'clock', cuenta: n('curso') },
    { valor: 'simulado', texto: 'Simulados', icono: 'escudo', cuenta: n('simulado') },
    { valor: 'confirmado', texto: 'Terminados', icono: 'ok', cuenta: n('confirmado') }],
  alCambiar: v => { filtro = v; pintar(); } });
  filtro = chips.valor();
  const obj = objetivo ? L.find(x => String(x.id) === String(objetivo)) : null;
  if (obj && !(FILTROS_S[filtro] || FILTROS_S[''])(obj)) filtro = '';
  pintar();
  const pasosComo = canal === 'chat'
    ? [['Se escribe', 'En un grupo de la app: se guarda en la base de la app (imborrable). Con el puente encendido, el mismo instante deja su copia en la cola.'],
      ['Sale', 'Una clave por mensaje: si se corta a medias, antes de reintentar se mira si ya está en el canal de ClickUp. Nunca se duplica.'],
      ['Vuelve', 'Lo que se escribe en ClickUp entra en el grupo de la app una vez. Si allí se edita o se borra, aquí queda una nota y el original.'],
      ['Apagado hoy', 'Lo decide Tomás: ver 51_SINCRONIA_Y_CHAT.md (recomendación: el chat del equipo vive en la app).']]
    : [['Se guarda', 'Al pulsar en la app, el cambio queda en la base de la app con quién, cuándo, qué tarea y el cambio exacto (lo decide el servidor, no la pantalla). Nunca se pierde.'],
      ['Sale', 'Una clave única por cambio y en orden por tarea. Antes de escribir se relee la tarea: si ya está, no se repite; si alguien la cambió después en ClickUp, no se pisa.'],
      ['Se comprueba', 'Se relee en ClickUp que el cambio está. Si ClickUp no responde, sigue pendiente, avisa y se reintenta con espera creciente.'],
      ['Si hay dos versiones', 'Aviso a quien lo hizo y a Agus con las dos; se elige aquí cuál se queda.'],
      ['Cada mañana', `Informe «cambios sin reflejar» (más de ${fmt.num(S.informe?.horas || 4)} h) para Agus y Mili en #avisos-altas.`]];
  return [
    cartelSinc(S, canal),
    canal === 'clickup' ? tilesSinc(S, L) : null,
    canal === 'clickup' && S.informe?.total ? avisoParcial(S.informe.texto, { tipo: S.modo?.reales ? 'parcial' : 'info', titulo: 'Sin reflejar en ClickUp' }) : null,
    panel({ titulo: canal === 'chat' ? 'Mensajes hacia el chat de ClickUp' : 'Cambios hacia ClickUp', icono: canal === 'chat' ? 'chat' : 'check',
      sub: `${S.ve_todos ? 'Los de todo el equipo' : 'Los tuyos'} · fallidos y conflictos arriba, con el motivo en llano. Cada paso lleva su hora.`,
      acciones: h('button', { type: 'button', class: 'bt mini', on: { click: () => repintar() } }, icono('recargar'), 'Actualizar') },
    h('div', { class: 'pm-pad' }, chips), caja),
    panel({ titulo: 'Cómo se asegura', icono: 'escudo', sub: 'Lo hace el servidor al momento y en cada vuelta de la tubería (solo lectura en ClickUp para comprobar).' },
      h('ol', { class: 'tiempo', style: { margin: '0', padding: '12px var(--relleno)' } },
        pasosComo.map(([t, d]) => h('li', {}, h('div', { class: 't' }, t), h('div', { class: 'd' }, d))))),
    S.solo_lectura ? avisoParcial('Estás en «ver como»: ves lo que verían las dos personas y no se puede tocar nada.', { tipo: 'info' }) : null,
  ].filter(Boolean);
}

async function cargarSinc(ctx) {
  try { return await ctx.api('sincronia'); } catch (e) { return { error: e.message, status: e.status, cambios: [] }; }
}

export default {
  id: 'envios',
  titulo: 'Envíos',
  grupo: 'Sistema',
  puestos_que_lo_ven: { direccion: 'todo', operaciones: 'todo', tecnico_altas: 'todo' },
  async render(cont, ctx) {
    ctx.titulo?.('Envíos', 'Todo lo que sale de la app a las herramientas: correos, ClickUp y chat · si salió, si llegó y quién lo pidió');
    const [p0, p1] = ctx.params || [];
    const tabRuta = p0 === 'clickup' || p0 === 'chat' ? p0 : p0 ? 'correos' : null;
    const objetivo = tabRuta === 'correos' ? p0 : p1 || null;
    const raiz = h('div', { class: 'envios' });
    cont.append(raiz);
    let pestana = tabRuta;
    const pintar = async () => {
      const [D, S] = await Promise.all([cargar(ctx), cargarSinc(ctx)]);
      const L = S.cambios || [];
      const cuentaCorreos = (D.por_estado?.fallido || 0) + (D.por_estado?.rebotado || 0);
      const cuentaCu = malos(L.filter(x => x.canal === 'clickup'));
      const cuentaChat = malos(L.filter(x => x.canal === 'chat'));
      if (!pestana) pestana = cuentaCu && !cuentaCorreos ? 'clickup' : cuentaChat && !cuentaCorreos && !cuentaCu ? 'chat' : 'correos';
      const tabs = pestanas({
        etiqueta: 'Salidas a herramientas', activa: pestana,
        pestanas: [
          { id: 'correos', texto: 'Correos', icono: 'mail', cuenta: cuentaCorreos || null, cuentaEstado: 'rojo' },
          { id: 'clickup', texto: 'ClickUp', icono: 'check', cuenta: cuentaCu || null, cuentaEstado: 'rojo' },
          { id: 'chat', texto: 'Chat', icono: 'chat', cuenta: cuentaChat || null, cuentaEstado: 'rojo' },
        ],
        alCambiar: id => { pestana = id; },
        pintar: (id, zona) => {
          if (id === 'correos') {
            if (D.error) { zona.append(vacio({ icono: 'send', tono: 'aviso', titulo: 'No se pudo leer la cola de envíos', texto: D.error, quien: 'Agus' })); return; }
            zona.append(...cuerpo(ctx, D, () => pintar(), id === tabRuta || tabRuta === null ? objetivo : null));
          } else {
            if (S.error) { zona.append(vacio({ icono: 'check', tono: 'aviso', titulo: 'No se pudo leer la sincronía con ClickUp', texto: S.error, quien: 'Agus' })); return; }
            zona.append(...cuerpoSinc(ctx, S, id, () => pintar(), id === tabRuta ? objetivo : null));
          }
        },
      });
      raiz.replaceChildren(tabs);
      if (objetivo) {
        const sel = pestana === 'correos' ? `[data-envio="${CSS.escape(String(objetivo))}"]` : `[data-cambio="${CSS.escape(String(objetivo))}"]`;
        if (raiz.querySelector(sel)) llevarA(raiz, r => r.querySelector(sel));
        else if (pestana === tabRuta) raiz.prepend(avisoParcial(pestana === 'correos' ? 'Ese envío no está en tu lista (no es tuyo o ya no existe).' : 'Ese cambio no está en tu lista (no es tuyo o ya no existe).', { titulo: 'No lo encuentro.' }));
      }
    };
    await pintar();
  },
};

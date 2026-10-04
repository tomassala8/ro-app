import {celdaImputa390,imputaVigente390} from './_imputa_personal_390.js';
// modulos/mi_dia.js · M1 «Mi día» (2-oct-2026): la pantalla de inicio de cada uno de los 21 puestos.
//
// Es un ORQUESTADOR. No recalcula nada que ya calcule otro módulo: pide a servir.py los datos que la persona ya
// puede ver (ctx.datosModulo, recortados por el servidor) y los resume en bloques. Qué bloques y en qué orden,
// por puesto, vive en data/mi_dia/config.json (se ajusta sin tocar código). Los bloques, en mi_dia_bloques.js.
//
// Arriba (A1, 2-oct noche): «Lo mío», UNA lista personal de avisos disponibles, sin duplicados (alertas tuyas, correos de tu
// cartera, piezas por revisar, menciones, decisiones y lo urgente de los bloques), ordenada por plazo y gravedad, con un
// botón por fila que abre el objeto exacto (+ «Lo tengo» y «Posponer» si es alerta). Funde «Lo primero hoy» y «Mis
// alertas». A su lado (debajo en el móvil), «el número que manda» con su umbral (catálogo de E0). Debajo, los bloques
// (máx. 7, orden de frecuencia), el copiloto de IA y los cumpleaños; en el móvil, 7 piezas a la vista como mucho y el
// resto plegado en «Más de tu día». El consejo de la IA de la carcasa va debajo de «Lo mío» y sin sus filas.
// Un dato que aún no existe sale vacío y útil («llega con <módulo>») y se pinta solo cuando existe.
// Diseño (auditoría 30, N6): SIN hoja de estilos propia. Solo clases y tokens comunes (panel, cifraPrincipal, primero,
// lista-i, chip, table.densa, barra-prog, vacioLinea) y la maquetación (rejillas) en estilo en línea con tokens --s-*.
//
// Ruta: #/mi-dia (puesto principal) o #/mi-dia/<puesto> (si la persona tiene varios: Tomás, Coti, Valeria, Yessica…).

import {
  h, fmt, icono, chipEstado, selloMedible, frescura, vacio, estadoVacio, barraProgreso, pieFase2,
  limpiaTexto, deDondeSale, panel, avisoFlotante, cifraPrincipal, vacioLinea, esqueleto, hoyMadrid,
} from '../componentes.js';
import { celdaControlEquipo313 } from './_control_equipo_313.js';
import { ambitoCadencia307 } from './_cadencia_metodo.js';
import { prepararControlCartera, resumirAccountsControl } from './control_cartera.js';
import { pintarMapaControl250, COLUMNAS_CONTROL_250 } from './_control_artifact_250.js';
import { prepararResumenEvidencias } from './_evidencias_resumen.js';
import { panelHerramientas } from './_herramientas_perfil.js';
import { puestoControl239, tituloControl239, renderControl239 } from './_control_cartera_ruta_239.js';
import { colorCifra } from '../componentes.js';
import { bloqueCopiloto, panelCerebro } from './ia_componentes.js';
// Ronda U (50 #3, #4): «Deshacer» en vez de «¿Seguro?» en lo interno, y el consejo de la IA plegado a una línea.
import { botonDeshacer } from './_deshacer.js';
import { plegarConsejo } from './_trabajo.js';
// R12: sin el hueco «[importe]» del recorte del servidor y sin la puntuación que deja al quitar un código («llega con .», «, )»)
// V2: y en llano (textoLlano): «478 h» → «20 días», sin «(RO-6625)» ni el paso técnico entre paréntesis, «» con espacios
// Revisión 44 (D6, D7, §2.1): glosario común en los textos que llegan de los datos: «lista de arranque» (no «onboarding»),
// «a los 5 días» (no «a las 5 días») y minúscula tras los dos puntos del cliente («Conficonsulting: sin lista…»).
const glosa = t => (typeof t === 'string' ? t.replace(/\blista de onboarding\b/gi, 'lista de arranque').replace(/\ba las (\d+) días\b/g, 'a los $1 días')
  .replace(/\bcliente en crítico\b/gi, m => (m[0] === 'C' ? 'Cliente crítico' : 'cliente crítico')).replace(/\bcliente en atención\b/gi, m => (m[0] === 'C' ? 'Cliente a vigilar' : 'cliente a vigilar'))
  .replace(/^([^:]{2,60}): (Sin|Con|Todavía) /, (m, a, b) => `${a}: ${b.toLowerCase()} `) : t);
const L = t => glosa(typeof t === 'string' ? textoLlano(limpiaTexto(sinImporte(t))).replace(/[,;\s]+\)/g, ')').replace(/\s+([.,;:])(?=\s|$)/g, '$1').replace(/\b(con|de|en|por)\s*\./g, '.') : t);
import { PUESTO } from '../permisos.js';
import { MODULOS } from './indice.js';
import { BLOQUES, NUMERO, edadH, diaCorto, MESES, sinImporte, LO_MIO_USA, alertasMias, temaAlerta, objetoDe, tramoPlazo, unirLoMio, repetidosLoMio,
  correosLoMio, piezasMeTocan, revisaPiezas, decisionesMias, textoLlano, apartadasLoMio } from './mi_dia_bloques.js';

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

const scopeDia = ctx => JSON.stringify([ctx.real?.id || '', ctx.persona?.id || '', !!ctx.soloLectura, !!ctx.servidor]);
const CACHE = new Map();          // persona|fichero → { t, ok, datos, motivo }
const VIDA_CACHE_MS = 5 * 60 * 1000;
let CONFIG = null;

const PALABRAS_DIA = ['domingo', 'lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado'];
const saludo = () => { const hh = new Date().getHours(); return hh < 14 ? 'Buenos días' : hh < 21 ? 'Buenas tardes' : 'Buenas noches'; };
const fechaLarga = () => { const d = new Date(`${hoyMadrid()}T12:00:00`); return `${PALABRAS_DIA[d.getDay()]} ${d.getDate()} de ${MESES[d.getMonth()]}`; };
// ---- maquetación en línea (solo tokens): rejillas que se pliegan solas, sin hoja propia ni media queries
const REJILLA = min => ({ display: 'grid', gridTemplateColumns: `repeat(auto-fit, minmax(min(100%, ${min}px), 1fr))`, gap: 'var(--s-4)', alignItems: 'start' });
const CORTA = { display: '-webkit-box', WebkitLineClamp: '2', WebkitBoxOrient: 'vertical', overflow: 'hidden' };
const TEXTO_FILA = { whiteSpace: 'normal', display: 'grid', gap: 'var(--s-1)', overflowWrap: 'anywhere' };
/** Rejilla sin huérfanas: si el número de piezas es impar, la última ocupa la fila entera. */
const sinHuerfana = l => { if (l.length > 1 && l.length % 2) l[l.length - 1].style.gridColumn = '1 / -1'; return l; };
const edadUTC = s => (s ? edadH(String(s).replace(' ', 'T') + (/[zZ]|[+-]\d\d:?\d\d$/.test(s) ? '' : 'Z')) : null);

// ================================================================== datos
function nombreModulo(id) { return MODULOS.find(m => m.id === id)?.titulo || id; }

/** Motivo de un fichero que no se pudo leer, por su código (igual para la petición suelta y para el resumen). */
const motivoDe = (status, error, modulo) => ({ ok: false, motivo: status === 404 ? 'no_existe' : status === 403 ? 'no_puesto' : 'error', error, modulo });

/** Carga perezosa y recortada de los ficheros de otros módulos, con motivo cuando no se puede.
 *  paquete = el resumen de la persona (data/mi_dia/p_<id>.json, recortado por servir.py): lo que trae no se pide;
 *  lo que no trae (p. ej. ventas_ro/*, que abre nombres con rastro) se pide suelto, como antes. */
function cargador(ctx, paquete = null, adelantados = {}) {
  const res = {};
  const sueltos = [];               // los que se pidieron aparte y llegaron (para adelantarlos la próxima vez)
  const fuentes = CONFIG?.fuentes || {};
  const firmaMetodo309=()=>typeof ctx.veModulo==='function'&&ctx.veModulo('reuniones')===true&&(!ctx.vigente||ctx.vigente())?JSON.stringify([ambitoCadencia307(ctx).firma,!!ctx.servidor,!!ctx.soloLectura]):null;
  const resultado309=nombre=>{const r=res[nombre];return nombre==='metodo/sugerencias'&&r?.ok&&(!r?.firma_metodo_309||r.firma_metodo_309!==firmaMetodo309())?motivoDe(403,'Contexto de reuniones cambiado.','reuniones'):r;};
  async function uno(nombre) {
    // Overlay de método: API recortada por identidad real + vista. No persistir en caché global ni paquete.
    if (nombre === 'metodo/sugerencias') {
      const antes=firmaMetodo309();
      if(!antes){res[nombre]=motivoDe(403,'Sin ámbito vigente de reuniones.','reuniones');return;}
      try { const datos=await ctx.api(nombre);res[nombre]=antes===firmaMetodo309()?{ok:true,datos,firma_metodo_309:antes}:motivoDe(403,'Contexto de reuniones cambiado.','reuniones'); }
      catch (e) { res[nombre] = motivoDe(e?.status, e?.message, 'reuniones'); }
      return;
    }
    const clave = `${scopeDia(ctx)}|${nombre}`;
    const c = CACHE.get(clave);
    if (c && Date.now() - c.t < VIDA_CACHE_MS) { res[nombre] = c; return; }
    const f = fuentes[nombre] || {};
    const mod = MODULOS.find(m => m.id === f.modulo);
    let r;
    if (f.puestos && !ctx.persona.puestos.some(p => f.puestos.includes(p))) r = { ok: false, motivo: 'no_puesto', modulo: f.modulo };
    else if (!f.puestos && f.modulo && !ctx.veModulo(f.modulo)) r = { ok: false, motivo: mod && mod.estado !== 'hecho' && !mod.fichero ? 'no_construido' : 'no_puesto', modulo: f.modulo };
    else if (paquete?.fuentes && Object.hasOwn(paquete.fuentes, nombre)) r = { ok: true, datos: paquete.fuentes[nombre] };
    else if (paquete?.faltan?.[nombre]) r = motivoDe(paquete.faltan[nombre].estado, paquete.faltan[nombre].error, f.modulo);
    else {
      try { r = { ok: true, datos: await (adelantados[nombre] || ctx.datosModulo(nombre)) }; sueltos.push(nombre); }
      catch (e) { r = motivoDe(e.status, e.message, f.modulo); }
    }
    r.t = Date.now();
    CACHE.set(clave, r);
    res[nombre] = r;
  }
  return {
    precargar: nombres => Promise.all([...new Set(nombres)].map(uno)),
    sueltos,
    dato(nombre) { const r = resultado309(nombre); if (r?.ok) return r.datos; throw { falta: nombre, ...(r || { motivo: 'no_existe' }) }; },
    opcional(nombre) { const r = resultado309(nombre); return r?.ok ? r.datos : null; },
  };
}

async function cargarConfig(ctx) {
  if (CONFIG) return CONFIG;
  CONFIG = await ctx.datosModulo('mi_dia/config');
  return CONFIG;
}

// Auditoría 37 (causa 3): Mi día en UN viaje. fuentes_mi_dia/resumen_mi_dia.py deja por persona y puesto la configuración
// y cada fichero que pintan sus bloques, recortado como lo sirve servir.py; el servidor lo vuelve a recortar al servirlo
// («solo_propio»). En «ver como» o sin servidor no se usa (se piden los ficheros sueltos, como antes). Un resumen de más
// de 3 h (la tubería lo rehace cada hora) tampoco: se piden los ficheros, que estarán más al día.
const VIDA_PAQUETE_H = 3;
const PAQUETES = new Map();       // persona|puesto → { t, p: Promise }
function pedirPaquete(ctx, puesto) {
  if (!ctx.servidor || ctx.soloLectura) return Promise.resolve(null);
  const clave = `${scopeDia(ctx)}|${puesto || ''}`;
  const c = PAQUETES.get(clave);
  if (c && Date.now() - c.t < VIDA_CACHE_MS) return c.p;
  const p = ctx.datosModulo(puesto ? `mi_dia/puestos/${puesto}/p_${ctx.persona.id}` : `mi_dia/p_${ctx.persona.id}`)
    .then(d => (d?.config && d?.fuentes && (edadH(d._meta?.generado) ?? 99) < VIDA_PAQUETE_H ? d : null))
    .catch(() => null);
  PAQUETES.set(clave, { t: Date.now(), p });
  return p;
}
// Lo que el resumen no puede traer (ventas_ro/*: abre nombres con rastro) se pide aparte. Se recuerda en el navegador
// qué fue, para pedirlo la próxima vez A LA VEZ que el resumen (solo nombres de fichero; nunca datos).
const claveAparte = (ctx, puesto) => `ro.midia.aparte.${scopeDia(ctx)}.${puesto || ''}`;
const leerAparte = k => { try { const l = JSON.parse(localStorage.getItem(k) || '[]'); return Array.isArray(l) ? l.filter(x => typeof x === 'string').slice(0, 6) : []; } catch { return []; } };
const guardarAparte = (k, l) => { try { localStorage.setItem(k, JSON.stringify(l)); } catch { /* sin almacenamiento: solo se pierde el adelanto */ } };

/** Bloque de config → { id, titulo, icono, ruta, alcance, … } (el catálogo «bloques» + lo que traiga el puesto). */
function resolverBloque(b) {
  const id = typeof b === 'string' ? b : b.id;
  return { id, ...(CONFIG.bloques[id] || { titulo: id, icono: 'vacio', desconocido: true }), ...(typeof b === 'object' ? b : {}) };
}

/** Qué dice un bloque al que le falta su dato. */
function textoFalta(f) {
  const nombre = CONFIG.fuentes?.[f.falta]?.nombre || nombreModulo(f.modulo) || f.falta;
  if (f.motivo === 'no_construido' || f.motivo === 'no_existe') return { titulo: `Llega con ${nombre}`, texto: 'Ese módulo todavía no ha dejado sus datos. Cuando existan, este bloque se pinta solo.', quien: 'quien construye ese módulo', icono: 'hist' };
  if (f.motivo === 'no_puesto') return { titulo: 'Este dato no es de tu puesto', texto: `Sale de «${nombre}», que tu puesto no ve. Si lo necesitas, pídeselo a Mili o a Tomás.`, icono: 'candado' };
  return { titulo: `No se ha podido leer ${nombre}`, texto: f.error || f.motivo || 'Error al leer el dato.', quien: 'Recarga; si sigue, avisa a Tomás', icono: 'alert', tono: 'aviso' };
}

// ================================================================== render
// Acciones de «Lo primero hoy»: servir.py solo acepta tipos de la lista común («avisar», «escalar»). Se leen también
// los nombres antiguos («pedido», «escalado») por si quedaron en la cola.
const T_PEDIDO = ['avisar', 'pedido'];

const MODULO = {
  id: 'mi-dia',
  titulo: 'Mi día',
  grupo: 'Hoy',

  async render(cont, ctx) {
    if (ctx.vigente && !ctx.vigente()) return;
    const raizDia = h('div', { 'data-mi-dia-raiz': '' });
    cont.replaceChildren(raizDia);
    cont = raizDia;
    const identidadDia = scopeDia(ctx);
    const rutaDia = typeof location !== 'undefined' ? location.hash : null;
    const vigente = () => raizDia.isConnected && scopeDia(ctx) === identidadDia && (typeof location === 'undefined' || location.hash === rutaDia) && (!ctx.vigente || ctx.vigente());
    vigilarCortes(cont);
    document.getElementById('mid-estilos')?.remove(); document.getElementById('mid-maqueta')?.remove();   // hojas de antes de la guía 30
    cont.append(esqueleto({ lineas: 4, tarjetas: 2 }));
    if (ctx.params[0] === 'control-cartera') {
      await renderControl239(cont, ctx, vigente, panelControlCartera, h, estadoVacio);
      if(vigente())vigilarConsejo(cont,cont,cont,{ctx,puesto:puestoControl239(ctx.real,ctx.persona,ctx.params[1]||null)});
      return;
    }
    // Auditoría 37 (causa 3): todo lo que no depende de la configuración sale A LA VEZ, en la primera tanda: el resumen
    // de la persona (configuración + ficheros de sus bloques), sus acciones, sus alertas, la lista del copiloto y, si
    // su puesto los ve, los avisos de fuentes y las acciones de prospección. Antes: configuración → ficheros → copiloto.
    const pidePuesto = ctx.params[0] && ctx.persona.puestos.includes(ctx.params[0]) ? ctx.params[0] : null;
    const tiene = l => ctx.persona.puestos.some(p => l.includes(p));
    const pPaquete = pedirPaquete(ctx, pidePuesto);
    const pAcciones = ctx.servidor ? ctx.api('acciones').then(r => r.acciones || []).catch(() => []) : Promise.resolve([]);
    const pAvisos = ctx.servidor && tiene(['direccion', 'operaciones']) && ctx.ver({ tipo: 'recargar' }).ok ? ctx.api('avisos').then(r => r.avisos || []).catch(() => []) : Promise.resolve([]);
    const pProspeccion = ctx.servidor && tiene(['outreach']) ? ctx.api('acciones?modulo=prospeccion').then(r => r.acciones || []).catch(() => []) : Promise.resolve([]);
    const veAlertas = ctx.veModulo('alertas');
    const promAlertas = veAlertas ? ctx.datosModulo(`alertas/p_${ctx.persona.id}`).catch(() => null) : Promise.resolve(null);
    // A1 · «Lo mío»: la cola de Alertas (la misma que lee la pantalla Alertas: lote, posponer y lo que marcan otros) y las
    // menciones del chat (la campana). Solo si la persona ve esas pantallas: nada de 403 de ruido.
    const pAccAlertas = ctx.servidor && veAlertas ? ctx.api('acciones?modulo=alertas').then(r => r.acciones || []).catch(() => []) : Promise.resolve([]);
    const pCampana = ctx.servidor && ctx.veModulo('chat-equipo') ? ctx.api('canales/campana').catch(() => null) : Promise.resolve(null);
    // V2: lo ya despachado en la Bandeja por CUALQUIERA (la cola de la Bandeja), para contar los correos como la pantalla Bandeja
    const pAccBandeja = ctx.servidor && ctx.veModulo('bandeja') ? ctx.api('acciones?modulo=bandeja').then(r => r.acciones || []).catch(() => []) : Promise.resolve([]);
    // Ronda U + cerebro de decisiones v2: la prioridad por objeto (data/prioridades/p_<id>.json, solo la propia; en «ver
    // como» da 403 y se ordena por puesto, como hasta ahora)
    const pPrio = ctx.servidor && !ctx.soloLectura ? ctx.api(`modulo/prioridades/p_${encodeURIComponent(ctx.persona.id)}`).catch(() => null) : Promise.resolve(null);
    const usaPaquete = ctx.servidor && !ctx.soloLectura;
    const adelantados = usaPaquete ? Object.fromEntries(leerAparte(claveAparte(ctx, pidePuesto)).map(n => [n, ctx.datosModulo(n)])) : {};
    Object.values(adelantados).forEach(p => p.catch(() => null));
    const paquete = await pPaquete;
    if (!vigente()) return;
    if (paquete && !CONFIG) CONFIG = paquete.config;
    try { await cargarConfig(ctx); }
    catch (e) { if (!vigente()) return; cont.replaceChildren(estadoVacio({ titulo: 'No se ha podido preparar tu día', porque: 'Falta la configuración de los bloques de Mi día.', que_hacer: 'Recarga la página; si sigue, avisa a Tomás.' })); return; }

    if (!vigente()) return;
    // R12 (B-M06): un puesto de account sin ningún cliente asignado en esa silla (p. ej. Agus desde el 1-oct) no sale
    // como «día» propio si la persona tiene otro puesto: sus bloques serían de clientes que ya no lleva.
    const sinCarteraAccount = p => p === 'account' && !!ctx.carteraPorSilla && !ctx.carteraPorSilla.account?.size;
    const conDia = ctx.persona.puestos.filter(p => CONFIG.puestos[p]);
    const misPuestos = conDia.length > 1 ? conDia.filter(p => !sinCarteraAccount(p)) : conDia;
    if (!misPuestos.length) {
      cont.replaceChildren(vacio({ icono: 'persona', titulo: 'Tu puesto todavía no tiene «Mi día»', texto: `${ctx.persona.alias} no tiene puesto asignado en la tabla de personas.`, quien: 'Mili (Ajustes › Personas)', borde: true }));
      return;
    }
    const puesto = misPuestos.includes(ctx.params[0]) ? ctx.params[0] : misPuestos[0];
    const conf = CONFIG.puestos[puesto];
    const nombrePuesto = PUESTO[puesto]?.nombre || puesto;
    const nombre = ctx.persona.alias || (ctx.persona.nombre || '').split(' ')[0];
    // El saludo va en la cabecera común (una sola línea de título), no en un H2 propio más grande que el título.
    ctx.titulo('Mi día', `${saludo()}, ${nombre} · ${nombrePuesto} · ${fechaLarga()}${ctx.soloLectura ? ' · viendo como (solo lectura)' : ''}`);

    // ---- qué hay que cargar
    const lista = conf.bloques.slice(0, CONFIG.comun?.max_bloques || 7).map(resolverBloque);
    const numCfg = conf.numero || {};
    const carteraControl = ['account', 'operaciones', 'direccion'].includes(puesto);
    const usaControl = []; // La matriz se carga en su subvista, no junto con toda la rutina.
    const usa = [...usaControl, ...lista.flatMap(b => BLOQUES[b.id]?.usa || []), ...(NUMERO[numCfg.calculo]?.usa || []), ...(NUMERO[numCfg.proxy]?.usa || []), ...usaLoMio(ctx)];
    // El resumen vale si es de este puesto (si no, sus ficheros se piden sueltos: mismo resultado, más viajes).
    const valePaquete = paquete?._meta?.puesto === puesto;
    const D = cargador(ctx, valePaquete ? paquete : null, adelantados);
    const [, acciones, avisosTodos, prospeccionTodas, alertas, accAlertas, campana, accionesBandeja, prio] = await Promise.all([D.precargar(usa), pAcciones, pAvisos, pProspeccion, promAlertas, pAccAlertas, pCampana, pAccBandeja, pPrio]);
    if (!vigente()) return;
    if (valePaquete) guardarAparte(claveAparte(ctx, pidePuesto), D.sueltos);
    const avisos = ['direccion', 'operaciones'].includes(puesto) ? avisosTodos : [];
    const accionesProspeccion = puesto === 'outreach' ? prospeccionTodas : [];
    const extra = { acciones, accionesProspeccion, accionesBandeja };

    // ---- cada bloque, aislado: si uno falla, los demás siguen
    const bloques = lista.map((b, i) => {
      const base = { ...b, orden: i };
      if (b.desconocido) return { ...base, r: { vacio: { titulo: `Bloque desconocido «${b.id}»`, texto: 'No está en la configuración de Mi día. Avisa a Tomás.', icono: 'alert', tono: 'aviso' }, estado: 'gris' } };
      if (b.pendiente || !BLOQUES[b.id]) return { ...base, r: { pendiente: true, estado: 'gris', medible: b.medible || 'no', vacio: { titulo: b.medible === 'medias' ? 'Se mide a medias' : 'Todavía no se puede medir', texto: b.texto || 'Este bloque espera un dato o un permiso.', quien: b.quien, icono: b.icono } } };
      try {
        const r = BLOQUES[b.id].hacer(ctx, D, b, extra) || {};
        // nada de verdes falsos: sin cifra ni filas, el bloque es gris «sin dato»
        if ((r.valor === null || r.valor === undefined || r.valor === '—') && !(r.filas || []).length && !r.ronda && !r.mapa && !r.barras && !r.pistas && !(r.tarjetas || []).length) r.estado = 'gris';
        return { ...base, r };
      }
      catch (e) {
        if (e && e.falta) return { ...base, r: { falta: true, estado: 'gris', vacio: textoFalta(e) } };
        console.error(`Mi día · bloque ${b.id}:`, e);
        return { ...base, r: { estado: 'gris', vacio: { titulo: 'Este bloque ha fallado', texto: String(e?.message || e), icono: 'alert', tono: 'aviso', quien: 'quien construye Mi día' } } };
      }
    });

    // ---- V2 (B-M7): sin cartera en la silla de este puesto (Miguel: 17 clientes como web y ninguno como GoHighLevel), los
    // bloques de «lo tuyo» no dicen «todo bien»: salen en gris con EL MISMO motivo que su «Lo mío» y que las demás pantallas.
    const vacioSilla = sinCarteraSilla(ctx, puesto);
    let primeroVacio = true;
    if (vacioSilla) for (const b of bloques) if (!b.r.pendiente && !b.desconocido && b.alcance !== 'todo') {
      b.r = { estado: 'gris', vacio: primeroVacio ? vacioSilla : { titulo: vacioSilla.titulo, texto: 'El mismo motivo que arriba.', icono: 'persona' } };
      primeroVacio = false;
    }

    // ---- número que manda
    let numero = null;
    try {
      const calc = NUMERO[numCfg.calculo];
      numero = vacioSilla && calc ? { valor: null, contexto: `${vacioSilla.titulo}: ${vacioSilla.texto}` } : calc ? calc.hacer(ctx, D) : { fase2: true };
      if (numCfg.proxy && NUMERO[numCfg.proxy] && !vacioSilla) { try { numero.proxy = NUMERO[numCfg.proxy].hacer(ctx, D); } catch { /* sin proxy */ } }
    } catch (e) { numero = e?.falta ? { falta: textoFalta(e) } : { error: String(e?.message || e) }; }

    // ---- A1 · «Lo mío»: señales disponibles para hoy (no inventario completo de tareas); V2: la de ESTA pestaña de puesto
    const lm = { ctx, D, A: alertas, accAlertas, acciones, extra, campana, bloques, avisos, local: new Map(), puesto, prio: prio?.persona_id === ctx.persona.id ? prio : null };
    const loMio = panelLoMio(lm);

    // V2-B: el copiloto («Tus clientes por gravedad · lo que propone la IA») solo al account, y plegado en «Más de tu día»
    const pCopiloto = puesto === 'account' && ctx.veModulo('asistente-ia') ? bloqueCopiloto(ctx, { max: 5 }) : null;
    // R15a · A10: «Tu primera semana · N de 5» para quien entró hace menos de 14 días (o está por incorporar)
    const pPrimera = await tarjetaPrimeraSemana(ctx).catch(() => null);
    if (!vigente()) return;
    const puestoControl = carteraControl ? puestoControl239(ctx.real, ctx.persona, puesto) : null;
    const control = puestoControl ? h('nav', { class:'chips-f', 'aria-label':'Abrir control de cartera' },
      h('a', { href:`#/mi-dia/control-cartera/${puestoControl}`, class:'btn' }, tituloControl239(puestoControl))) : null;

    // ---- pintar. Arriba: «Lo mío» (lo que pide acción) y, a su lado, el número que manda. V2 (M9): entre 641 y 1.180 px
    // (1.024) el número va ARRIBA como franja (antes caía a 950-1.300 px, debajo de «Lo mío»); en el móvil, «Lo mío» primero.
    // Debajo, los bloques del puesto (el «arriba» del puesto, p. ej. los resultados del account, el primero).
    // V2 (M9/M10): como mucho 7 piezas a la vista en TODOS los anchos (Lo mío + número + consejo de la IA + 4 bloques; en el
    // móvil, 3): el resto, plegado en «Más de tu día». El copiloto ya no está a la vista (era una tercera lista de «qué hacer»
    // con nombre casi igual): solo al account y dentro del pliegue. Los cumpleaños, al final del pliegue.
    const arriba = conf.arriba ? bloques.find(b => b.id === conf.arriba) : null;
    const hero = heroNumero(ctx, numCfg, numero, puesto);
    const piezas = [pPrimera, ...(arriba ? [tarjetaBloque(ctx, arriba)] : []), ...bloques.filter(b => b !== arriba).map(b => tarjetaBloque(ctx, b))].filter(Boolean);
    const movil = typeof matchMedia === 'function' && matchMedia('(max-width: 640px)').matches;
    const tableta = !movil && typeof matchMedia === 'function' && matchMedia('(max-width: 1180px)').matches;
    const nVista = (CONFIG.comun?.max_bloques_vista || {})[movil ? 'movil' : 'escritorio'] ?? (movil ? 3 : 4);
    const aLaVista = piezas.slice(0, nVista);
    // 4-oct · «Qué hago si…» (cerebros de área): buscar la ficha de una situación, sin IA. Primero del pliegue.
    const pCerebro = ctx.persona?.puestos?.length ? panelCerebro(ctx) : null;
    const plegadas = [pCerebro, ...piezas.slice(nVista), pCopiloto, panelCelebraciones(ctx)].filter(Boolean);
    const fila1 = tableta
      ? h('div', { class: 'pila', 'data-mid-arriba': '', style: { gap: 'var(--s-4)' } }, Object.assign(hero, { style: 'min-width: 0' }), Object.assign(loMio, { style: 'min-width: 0' }))
      : h('div', { class: 'fila', 'data-mid-arriba': '', style: { gap: 'var(--s-4)', alignItems: 'flex-start' } },
        Object.assign(loMio, { style: 'flex: 2 1 540px; min-width: 0' }),
        Object.assign(hero, { style: 'flex: 1 1 300px; min-width: 0' }));
    cont.replaceChildren(...[
      misPuestos.length > 1 ? chipsPuestos(ctx, puesto, misPuestos) : null,
      control,
      accesosTrabajo(ctx),
      panelHerramientas(ctx, vigente),
      fila1,
      h('div', { class: 'mid-bloques', style: REJILLA(420) }, sinHuerfana(aLaVista)),
      plegadas.length ? masDeTuDia(plegadas) : null,
      pie(ctx, puesto),
    ].filter(Boolean));
    vigilarConsejo(cont, loMio, fila1, { ctx, puesto });
  },
};
export default MODULO;

// ================================================================== V2 · sin cartera en la silla del puesto
/** Silla de las asignaciones que corresponde a cada puesto que lleva clientes. */
const SILLA_PUESTO = { account: 'account', trafficker: 'trafficker', especialista_ghl: 'crm', seo: 'seo', web: 'web', redes: 'redes' };
const NOMBRE_SILLA = { account: 'account', trafficker: 'trafficker', crm: 'GoHighLevel (CRM)', seo: 'SEO', web: 'web', redes: 'redes' };
/** Si la persona no tiene ningún cliente en la silla de ESTE puesto, el vacío que deben decir sus bloques: el mismo motivo
 *  que su aviso de «Lo mío» («Tus clientes están en otra silla») o, si no lo hay, uno común. null si tiene cartera. */
function sinCarteraSilla(ctx, puesto) {
  const s = SILLA_PUESTO[puesto];
  const cps = ctx.carteraPorSilla;
  if (!s || !cps || !(ctx.servidor || Object.keys(cps).length)) return null;
  const x = cps[s];
  if (x && (typeof x.size === 'number' ? x.size : (x.length || 0))) return null;
  const aviso = (ctx.datos.alarmas || []).find(a => a.ambito === 'persona' && a.responsable_id === ctx.persona.id && /otra silla|sin clientes|sin cartera/i.test(`${a.tipo} ${a.texto}`));
  return { titulo: `Aún no llevas clientes como ${NOMBRE_SILLA[s]}`, texto: aviso?.texto || `Los asigna Mili (o Tomás) en Ajustes; hasta entonces aquí no hay nada tuyo que medir.`, quien: 'Mili o Tomás', icono: 'persona' };
}

// ================================================================== cabecera
/** Quien tiene varios puestos (Tomás, Coti, Valeria, Yessica…) cambia de día con chips comunes. */
function chipsPuestos(ctx, puesto, misPuestos) {
  return h('nav', { class: 'chips-f', 'aria-label': 'Ver el día de otro de tus puestos' },
    h('span', { class: 'et' }, 'Tus puestos'),
    misPuestos.map(x => h('button', { type: 'button', 'aria-pressed': String(x === puesto), 'aria-current': x === puesto ? 'page' : null,
      on: { click: () => ctx.navegar(`mi-dia/${x}`) } }, PUESTO[x]?.nombre || x)));
}

/** Atajos sin nuevas lecturas ni cifras: cada destino conserva sus propios permisos y alcance. */
function accesosTrabajo(ctx) {
  const destinos = [
    { id: 'mi-trabajo', titulo: 'Mi trabajo · mis tareas', texto: 'Fechas, estados, comentarios y contexto para IA', icono: 'check' },
    { id: 'horas', titulo: 'Horas · registros por persona', texto: 'Último día, semana de la copia y mes seleccionado; capacidad sin confirmar', icono: 'clock' },
    { id: 'prioridades-cliente', titulo: 'Prioridades por cliente', texto: 'Revisar qué necesita atención y por qué', icono: 'flag' },
  ].filter(x => ctx.veModulo(x.id));
  if (!destinos.length) return null;
  return h('nav', { 'aria-label': 'Organizar mi trabajo', 'data-mid-accesos-trabajo': '',
    style: { display: 'flex', flexWrap: 'wrap', gap: 'var(--s-2)' } },
    destinos.map(x => h('a', { class: 'bt', href: `#/${x.id}`,
      style: { flex: '1 1 240px', minWidth: '0', minHeight: '44px', whiteSpace: 'normal',
        justifyContent: 'flex-start', textAlign: 'left', gap: 'var(--s-2)' } },
      icono(x.icono), h('span', { style: { minWidth: '0', overflowWrap: 'anywhere' } },
        h('b', { style: { display: 'block' } }, x.titulo),
        h('span', { class: 'sub', style: { display: 'block', whiteSpace: 'normal' } }, x.texto)))));
}

// 117: matriz cliente a cliente antes de las tarjetas; fuentes recortadas y sólo lectura.
function semanaDeclaracionesControl(hoy) {
  if(typeof hoy!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(hoy))return null;
  const d=new Date(`${hoy}T12:00:00Z`);
  if(!Number.isFinite(+d)||d.toISOString().slice(0,10)!==hoy)return null;
  d.setUTCDate(d.getUTCDate()-((d.getUTCDay()+6)%7));return d.toISOString().slice(0,10);
}
function ambitoDeclaracionesControl(ctx,semana) {
  const roles=p=>Array.isArray(p?.puestos)&&p.puestos.some(r=>['account','operaciones','direccion'].includes(r));
  if(!ctx.servidor||!roles(ctx.real)||!roles(ctx.persona)||typeof ctx.ver!=='function'||typeof ctx.veModulo!=='function'||!ctx.veModulo('mi-trabajo'))return null;
  // Catálogo ya recortado + permiso actual: incluye toda la cartera autorizada antes de filtros UI.
  const candidatos=ctx.clientes || ctx.clientesVisibles || [], ids=[], vistos=new Set();
  for(const c of candidatos){
    if(!c||typeof c.id!=='string'||vistos.has(c.id))return null;
    vistos.add(c.id);
    if(c.activo_confirmado===true&&ctx.ver({tipo:'cliente_detalle',cliente_id:c.id})?.ok===true)ids.push(c.id);
  }
  ids.sort();return {ids,firma:JSON.stringify([ctx.real.id,ctx.persona.id,ctx.real.puestos,ctx.persona.puestos,semana,ids])};
}
function proyectarDeclaracionesControl(respuesta,semana,ambito,actual,matrizIds,vigente) {
  const identidad={real_id:ambito?.real_id,vista_id:ambito?.vista_id,generacion:0};
  const doc=prepararResumenEvidencias({respuesta,semana_inicio:semana,cliente_ids:ambito?.ids || [],identidad,
    identidad_actual:actual?.firma===ambito?.firma?identidad:null,vigente});
  const mapa=new Map(doc.filas.map(f=>[f.cliente_id,f]));
  return new Map(matrizIds.map(cid=>[cid,mapa.get(cid) || null]));
}
function panelControlCartera(ctx, D, puesto, vigente) {
  const ops = ['direccion', 'operaciones'].includes(puesto);
  const permisosPauta = () => {
    if (!vigente() || !ctx.servidor || !ctx.real?.id || ctx.real.id !== ctx.persona?.id ||
        ctx.real.estado !== 'activo' || ctx.persona.estado !== 'activo' || !ctx.veModulo('dinero-cliente') || typeof ctx.ver !== 'function') return [];
    if (ctx.real.activo === false || ctx.persona.activo === false) return [];
    return (ctx.clientesVisibles || []).filter(c => c?.activo_confirmado === true &&
      ctx.ver({tipo:'cliente_detalle',cliente_id:c.id}).ok === true &&
      ctx.ver({tipo:'horas_pautadas',cliente_id:c.id}).ok === true).map(c => c.id);
  };
  const fuentes = { bandeja: D.opcional('bandeja/por_cliente'), produccion: D.opcional('produccion/produccion'), reuniones: D.opcional('reuniones/reuniones'), metodo: D.opcional('metodo/sugerencias'), nuevos: D.opcional('nuevos/nuevos'),
    dinero_cliente: permisosPauta().length ? D.opcional('dinero_cliente/dinero_cliente') : null };
  const rows = prepararControlCartera({ clientes: ctx.clientesVisibles, persona_id: ctx.persona.id, esOps: ops,
    carteraIds: [...(ctx.carteraPorSilla?.account || [])], asignaciones: ctx.datos?.asignaciones || [], personas:ctx.datos?.personas || [], fuentes, hoy: hoyMadrid(), permisosPautaIds:permisosPauta() });
  const semana=semanaDeclaracionesControl(hoyMadrid());let declaraciones=new Map();
  const declaracion=r=>declaraciones.get(r.cliente_id);
  const agregadoDeclarado=(g,campo)=>{
    const fs=rows.filter(r=>r.account_id===g.account_id).map(declaracion),validas=fs.filter(f=>f?.estado==='declarado');
    const suma=validas.reduce((n,f)=>n+f[campo],0);
    return {valor:validas.length&&Number.isSafeInteger(suma)?suma:null,filas:validas.length,total:fs.length};
  };
  const accountNombre = id => id ? (ctx.nombre?.(id) || (ctx.datos?.personas || []).find(p => p.id === id)?.alias || id) : 'Account por confirmar';
  const panelRaiz = h('section', { class: 'panel', 'data-control-cartera': '', 'aria-label': ops ? 'Control de todas las carteras autorizadas' : 'Control de mi cartera' });
  const cuerpo = h('div', { class: 'cuerpo pila', style: { minWidth: '0' } });panelRaiz.append(cuerpo);
  const buscador = h('input', { type: 'search', class: 'input', placeholder: 'Buscar cliente o servicio', 'aria-label': 'Buscar cliente en la matriz', style: { flex: '1 1 220px', minWidth: '0' } });
  const accounts = [...new Set(rows.map(r => r.account_id).filter(Boolean))].sort((a,b) => accountNombre(a).localeCompare(accountNombre(b), 'es'));
  const selector = h('select', { class: 'input', 'aria-label': 'Filtrar cartera por account' }, h('option', { value: '' }, 'Todos los accounts'),
    ...accounts.map(id => h('option', { value: id }, accountNombre(id))), h('option', { value: '__sin' }, 'Account por confirmar'));
  const servicio = h('select', { class: 'input', 'aria-label': 'Filtrar por servicio confirmado' }, h('option', {value:''}, 'Todos los servicios'),
    ...[...new Set(rows.flatMap(r=>r.servicios_lista))].sort().map(s=>h('option',{value:s},s)));
  const urgentes = h('input', { type: 'checkbox', 'aria-label': 'Sólo registros con más de 48 horas o fechas pasadas' });
  const etiquetaFiltro = h('label', { class: 'fila', style: { minHeight: '44px' } }, urgentes, 'Revisar >48h / fecha pasada');
  const zona = () => h('div', { class:'tabla-scroll', style:{maxWidth:'100%',overflowX:'auto'}, tabIndex:0, 'aria-label':'Tabla desplazable horizontalmente' });
  const tablaZona = h('div',{class:'tabla-scroll',style:{maxWidth:'100%',overflowX:'auto'},tabIndex:0,'aria-label':'Clientes y proyectos agrupados · tabla de la cartera filtrada'}), macroZona=zona();
  const resumen = h('p', { class: 'sub', role: 'status' });
  const restablecer = h('button', {type:'button',class:'bt',style:{minHeight:'44px'},on:{click:()=>{
    if(!vigente())return;buscador.value='';selector.value='';servicio.value='';urgentes.checked=false;pintar();buscador.focus?.();
  }}}, 'Restablecer filtros');
  const columnas = [['semaforo','Sem.','Semáforo registrado del cliente'],['pendientes','Pend.','Pendientes visibles'],['horas','h / ref.','Horas observadas / pauta económica de referencia'],['revisiones','Rev.','Tareas en revisión'],['tickets','Tk.','Tickets abiertos'],['contacto','Cont./sem.','Contactos declarados en la semana'],['reuniones','Reu./sem.','Reuniones declaradas en la semana'],['detalle','Detalle','Fuentes y detalle del cliente'],['servicios','Serv.','Servicios confirmados']];
  const href = (id, tab) => ctx.veModulo('ficha') ? `#/ficha/${encodeURIComponent(id)}/${tab}` : ctx.veModulo('prioridades-cliente') ? '#/prioridades-cliente' : null;
  const semaforoControl = r => {
    const v=ctx.verdad?.(r.cliente_id), ids=[v?.id,v?.cliente_id].filter(x=>x!=null);
    const mapa={critico:['rojo','Crítico'],atencion:['ambar','Vigilar'],bien:['verde','Bien']};
    if(!ids.length||ids.some(id=>id!==r.cliente_id)||!Object.hasOwn(mapa,v?.gravedad))return {estado:'gris',valor:'Por confirmar',detalle:'No hay un estado inequívoco de la verdad única autorizada. No se deduce de los KPI parciales.'};
    const [estado,valor]=mapa[v.gravedad];
    return {estado,valor,detalle:'Verdad única autorizada de clientes: misma gravedad que En rojo. Fecha del cálculo no incluida en este DTO; no acredita todos los KPI ni el semáforo manual de la ficha.'};
  };
  const celdaControl = (r,key) => {
    const d=declaracion(r),est=semaforoControl(r),estilo={padding:'5px 7px',verticalAlign:'middle',maxWidth:'155px',whiteSpace:'normal',fontSize:'12px',lineHeight:'1.25',overflowWrap:'break-word'};
    const mini=txt=>h('small',{class:'sub',style:{display:'block',fontSize:'11px',lineHeight:'1.25'}},txt);
    if(key==='semaforo')return h('td',{style:estilo},chipEstado(est.estado,est.valor));
    if(key==='servicios')return h('td',{style:estilo},r.servicios_lista.join(' / ')||'—');
    const cifra=(valor,estado,explicacion)=>h('td',{style:estilo,title:explicacion,'aria-label':explicacion},chipEstado(estado,valor));
    if(key==='pendientes')return cifra(Number.isSafeInteger(r.pendientes.total_visible)?String(r.pendientes.total_visible):'—',r.pendientes.fechas_pasadas>0?'ambar':'gris',`${r.pendientes.valor}. ${r.pendientes.detalle}`);
    if(key==='horas'){
      const m=r.horas.medicion,p=r.pauta_horas,total=typeof m?.total==='number'&&Number.isFinite(m.total)&&m.total>=0?m.total:/^\d+(?:\.\d+)? h observadas$/.test(r.horas.valor)?Number(r.horas.valor.split(' ')[0]):null;
      const compatible=p&&permisosPauta().includes(r.cliente_id)&&m?.periodo===p.periodo&&typeof p.horas==='number'&&Number.isFinite(p.horas)&&p.horas>=0;
      return cifra(`${total===null?'—':ntexto(total)} / ${compatible?ntexto(p.horas):'—'}`,'gris',`Horas observadas: ${r.horas.valor}. ${r.horas.detalle} ${compatible?'Pauta económica de referencia del mismo mes; no objetivo contractual confirmado.':'No hay pauta autorizada del mismo mes para comparar.'}`);
    }
    if(key==='revisiones'||key==='tickets'){
      const e=r[key],m=e.medicion,medida=Number.isSafeInteger(m?.total)&&m.total>=0&&Number.isSafeInteger(m?.mas_48)&&m.mas_48>=0&&m.mas_48<=m.total;
      const estado=!medida?'gris':key==='tickets'?(m.mas_48>0?'rojo':'gris'):(m.mas_48>=6?'rojo':m.mas_48>0?'ambar':'gris');
      return cifra(medida?String(m.total):'—',estado,`${key}: ${medida?`${m.total} en total; ${m.mas_48} >48h`:'sin medición acreditada'}. ${e.fuente} · ${e.fecha||'fecha no disponible'}. ${e.detalle}`);
    }
    if(key==='contacto')return cifra(d?.estado==='declarado'?String(d.contactos_declarados):'—','gris','Contactos declarados en la semana actual; no actividad externa verificada ni cumplimiento.');
    if(key==='reuniones')return cifra(d?.estado==='declarado'?String(d.reuniones_declaradas):'—','gris','Reuniones declaradas en la semana actual; la cadencia de 15 días y el histórico no son un conteo de reuniones celebradas.');
    const firmaDetalle=()=>JSON.stringify([ctx.real,ctx.persona,ctx.clientes,ctx.datos?.personas,ctx.datos?.asignaciones,permisosPauta(),ctx.ver?.({tipo:'cliente_detalle',cliente_id:r.cliente_id})?.ok]);
    const inicialDetalle=firmaDetalle();
    const detalle=h('details',{on:{toggle:()=>{if(!vigente()||firmaDetalle()!==inicialDetalle)detalle.replaceChildren();}}},h('summary',{'aria-label':`Fuente y detalle de ${r.nombre}`,class:'sub',style:{minHeight:'44px',cursor:'pointer',display:'flex',alignItems:'center'}},'Ver detalle'),
      mini(est.detalle),mini(r.owner_detalle),
      r.pauta_horas&&permisosPauta().includes(r.cliente_id)?mini(`Pauta de referencia: ${ntexto(r.pauta_horas.horas)} h · ${mesControl(r.pauta_horas.periodo)}. ${r.pauta_horas.detalle}`):null,
      r.reunion_historica?mini(`${r.reunion_historica.valor} · copia ${r.reunion_historica.fecha} · periodo ${mesControl(r.reunion_historica.periodo_fuente)}. ${r.reunion_historica.detalle}`):null,
      ...['servicios','pendientes','horas','presupuesto','revisiones','tickets','contacto','reuniones','altas'].map(k=>{const e=r[k],valor=k==='horas'&&/^\d+(?:\.\d+)? h (registradas|observadas)$/.test(e.valor)?`${ntexto(Number(e.valor.split(' ')[0]))} h ${e.valor.endsWith('observadas')?'observadas':'registradas'}`:e.valor;return h('p',{class:'sub',style:{margin:'6px 0',fontSize:'12px'}},h('b',{},`${k}: `),`${valor} · ${e.fuente} · ${e.fecha||'fecha no disponible'}. ${e.detalle}`);}),
      d?.estado==='declarado'?mini(`${d.contacto_texto}. ${d.reunion_texto}. Semana ${semana}; declaraciones del equipo sin verificación externa. ${d.motivo}`):null);
    return h('td',{style:estilo},detalle);
  };
  const ntexto = v => typeof v==='number' && Number.isFinite(v) ? new Intl.NumberFormat('es-ES',{maximumFractionDigits:1}).format(v) : 'Sin dato';
  const mesControl = v => /^\d{4}-(0[1-9]|1[0-2])$/.test(v || '') ? `${['ene','feb','mar','abr','may','jun','jul','ago','sep','oct','nov','dic'][Number(v.slice(5))-1]} ${v.slice(0,4)}` : 'mes sin confirmar';
  const tMacro = {padding:'6px 8px',verticalAlign:'top',whiteSpace:'normal',overflowWrap:'anywhere',fontSize:'13px',lineHeight:'1.25'};
  const breve = texto => h('small',{class:'sub',style:{display:'block',fontSize:'12px',lineHeight:'1.25'}},texto);
  const datoMacro = (principal,secundario) => h('td',{style:tMacro},h('span',{},principal),secundario?breve(secundario):null);
  const cobertura = m => `${m.medidos} medidos / ${m.sin_dato} sin dato`;
  const pintarMacro = () => {
    if (!ops || !vigente()) return;
    const grupos = resumirAccountsControl(rows).sort((a,b)=>(!a.account_id)-(!b.account_id)||accountNombre(a.account_id).localeCompare(accountNombre(b.account_id),'es'));
    const desconocido = detalle => ({valor:null,sub:'Sin dato',estado:'gris',detalle});
    const observado = (m, detalle,rojoDesde=1) => ({valor:m.valor,sub:`${m.medidos}/${m.medidos+m.sin_dato} clientes`,estado:m.valor>=rojoDesde?'rojo':m.valor>0?'ambar':'gris',detalle: `${detalle} ${cobertura(m)}. Copia parcial; cero observado no certifica cobertura completa.`});
    const filas = grupos.map(g => {
      const contacto = agregadoDeclarado(g,'contactos_declarados');
      return {id:g.account_id || "__sin",nombre:accountNombre(g.account_id),clientes:g.clientes,celdas:{
        imputa:celdaImputa390(ctx,D.opcional('horas_personales/390'),g.account_id),
        revisa:observado(g.revisiones48,'Tareas registradas en revision de account con mas de48h. Rojo desde6 tareas, amarillo de1 a5; umbral del mapa original.',6),
        llama:desconocido('No existe en esta copia una serie de llamadas salientes de7dias atribuida de forma canonica a esta persona.'),
        contesta:observado(g.tickets48,'Antiguedad de tickets registrados, no tiempo de respuesta de cada correo ni SLA certificado.'),
        reune:{...desconocido('Un registro historico no confirma celebracion. Cadencia y reuniones se contrastan por cliente.'),sub:g.reuniones15?`${g.reuniones15} regla15d`:'Sin confirmar'},
        contacto:{...desconocido('Contactos declarados del equipo, no actividad externa verificada. Cero declaraciones no significa ausencia de contacto.'),sub:contacto.valor===null?'Sin dato':`${contacto.valor} declarados`},
        abandonados:desconocido('No se ha acreditado conjuntamente ausencia de horas y contactos durante14dias.'),
        planifica:desconocido('La copia no acredita transiciones completas entre planning mensual, semanal y diario.'),
        tarde:desconocido('No hay serie verificada de reuniones celebradas desde las15h durante45dias.'),
      }};
    });
    const personal=D.opcional('horas_personales/390'),actual=imputaVigente390(ctx,personal);
    const columnas = COLUMNAS_CONTROL_250.map(c=>c.key==='contesta'?{...c,sub:'tickets abiertos >48h'}:c.key==='imputa'&&actual?{...c,sub:`horas · ${diaCorto(personal.desde)}–${diaCorto(personal.hasta)}`} :c);
    macroZona.replaceChildren(pintarMapaControl250({h,filas,columnas,vigente,
      celdaVigente:(_row,key)=>key!=='imputa'||!personal||imputaVigente390(ctx,personal),
      alSeleccionar:id=>{if(!vigente())return;selector.value=id||'__sin';buscador.value='';servicio.value='';urgentes.checked=false;pintar();tablaZona.focus?.();tablaZona.scrollIntoView?.({block:'nearest',behavior:'auto'});}}));
  };
  // La tabla inferior conserva su propia época: el mapa superior tiene otra guardia.
  const firmaInferior=()=>JSON.stringify([ctx.real,ctx.persona,ctx.clientes,ctx.clientesVisibles,ctx.datos?.personas,ctx.datos?.asignaciones,
    rows.map(r=>[r.cliente_id,ctx.ver?.({tipo:'cliente_detalle',cliente_id:r.cliente_id})?.ok]),permisosPauta()]);
  const epocaInferior=firmaInferior();
  const inferiorVigente=()=>{
    const clientes=ctx.clientes,personas=ctx.datos?.personas;
    const clientesValidos=!Array.isArray(clientes)||rows.every(r=>{
      const encontrados=clientes.filter(c=>c?.id===r.cliente_id);
      return encontrados.length===1&&encontrados[0].activo_confirmado===true;
    });
    const personasValidas=!Array.isArray(personas)||[ctx.real,ctx.persona].every(actor=>{
      const encontrados=personas.filter(p=>p?.id===actor?.id);
      const p=encontrados[0];
      return encontrados.length===1&&p.estado==='activo'&&p.activo!==false&&
        Array.isArray(p.puestos)&&Array.isArray(actor?.puestos)&&
        JSON.stringify([...p.puestos].sort())===JSON.stringify([...actor.puestos].sort());
    });
    if(vigente()&&clientesValidos&&personasValidas&&firmaInferior()===epocaInferior)return true;
    tablaZona.replaceChildren();return false;
  };
  const pintar = () => {
    if (!inferiorVigente()) return;
    const buscar = (buscador.value || '').trim().toLocaleLowerCase('es'),owner=ops?selector.value||'':'';
    const visibles=rows.filter(r=>(!buscar||`${r.nombre} ${r.servicios_lista.join(' ')}`.toLocaleLowerCase('es').includes(buscar))&&(!owner||(owner==='__sin'?!r.account_id:r.account_id===owner))&&(!servicio.value||r.servicios_lista.includes(servicio.value))&&(!urgentes.checked||r.tickets.estado==='rojo'||r.revisiones.estado==='ambar'||r.pendientes.fechas_pasadas>0)).sort((a,b)=>(!a.account_id)-(!b.account_id)||accountNombre(a.account_id).localeCompare(accountNombre(b.account_id),'es')||a.nombre.localeCompare(b.nombre,'es'));
    restablecer.disabled=!(buscar||owner||servicio.value||urgentes.checked);
    const detalleResumen=`${owner?`${accountNombre(owner==='__sin'?null:owner)} · `:''}${visibles.length} de ${rows.length} clientes activos confirmados. Proyectos agrupados por cliente: no hay desglose de subproyectos. Copias parciales; sin dato no significa cero ni cumplido.`;
    resumen.replaceChildren(h('span',{title:detalleResumen,'aria-label':detalleResumen},`${visibles.length} de ${rows.length} clientes activos`));
    tablaZona.replaceChildren(h('table',{class:'densa',style:{width:'100%',minWidth:'900px',tableLayout:'fixed'}},
      h('thead',{},h('tr',{},h('th',{scope:'col',style:{width:'160px',fontSize:'11px',padding:'6px 7px',whiteSpace:'normal',textTransform:'none',letterSpacing:'normal'}},'Cliente / account'),...columnas.map(([,t,explicacion])=>h('th',{scope:'col',title:explicacion,'aria-label':explicacion,style:{fontSize:'11px',padding:'6px 7px',whiteSpace:'normal',textTransform:'none',letterSpacing:'normal'}},t)))),
      h('tbody',{},...visibles.map(r=>h('tr',{},h('th',{scope:'row',style:{position:'static',minWidth:'140px',maxWidth:'190px',whiteSpace:'normal',padding:'5px 7px',fontSize:'12px',textTransform:'none',letterSpacing:'normal'}},href(r.cliente_id,'resumen')?h('a',{href:href(r.cliente_id,'resumen'),style:{display:'inline-flex',alignItems:'center',minHeight:'44px',whiteSpace:'normal'}},h('span',{},r.nombre,breve(accountNombre(r.account_id)))):h('span',{},r.nombre,breve(accountNombre(r.account_id))),null),...columnas.map(([key])=>celdaControl(r,key)))))));
    if(!visibles.length)tablaZona.append(vacioLinea(rows.length?'Ningún cliente coincide con estos filtros.':'No hay clientes activos confirmados en esta copia y cartera; no se habilitan vigencias desconocidas.',{icono:'cli'}));
  };
  buscador.addEventListener('input',pintar);selector.addEventListener('change',pintar);servicio.addEventListener('change',pintar);urgentes.addEventListener('change',pintar);
  cuerpo.append(...[h('div',{class:'fila',style:{justifyContent:'space-between',flexWrap:'wrap',gap:'var(--s-2)'}},
    h('h2',{},ops?'Control macro · accounts y proyectos':'Tu cartera · control por cliente'),
    ctx.veModulo?.('horas') ? h('a',{href:'#/horas',class:'bt mini',style:{minHeight:'44px'}},ops?'Ver horas por persona · día / semana / mes':'Ver mis horas · día / semana / mes') : null),
    ops?macroZona:null,
    ops?h('h3',{},'Clientes y proyectos agrupados'):null,
    h('div',{class:'fila',style:{justifyContent:'space-between',flexWrap:'wrap',gap:'var(--s-2)'}},
      h('small',{class:'sub'},`Horas por proyecto: ${[...new Set(rows.map(r=>r.horas.medicion?.periodo).filter(Boolean))].map(mesControl).join(' / ')||'periodo sin confirmar'} · declaraciones: semana ${semana||'sin confirmar'}`),
      h('details',{},h('summary',{class:'sub',style:{minHeight:'44px',display:'flex',alignItems:'center',cursor:'pointer'}},'Cómo interpretar'),h('p',{class:'sub'},'Proyectos agrupados por cliente: no hay desglose de subproyectos. Copias parciales; sin dato no significa cero ni cumplido. Gris: dato ausente, periodo sin confirmar o copia parcial; no acredita cumplimiento. h / ref.: horas observadas del proyecto y pauta económica autorizada del mismo mes, como referencia; no presupuesto ni objetivo contractual confirmado. Revisión y Tickets muestran totales; el color usa registros >48h (revisión: 1–5 amarillo, ≥6 rojo; tickets: >0 rojo). Contactos y reuniones son declaraciones de la semana actual, sin verificación externa. Cero declaraciones no significa ausencia de actividad; no certifica cumplimiento ni cadencia.'))),
    h('div',{class:'cartera-filtros','aria-label':'Filtros de clientes y proyectos'},buscador,ops?selector:null,servicio,etiquetaFiltro,restablecer),resumen,tablaZona,
    ctx.veModulo?.('dinero-cliente')?h('a',{href:'#/dinero-cliente/cierre-septiembre',class:'bt',style:{alignSelf:'flex-start',minHeight:'44px'}},'Cierre de septiembre'):null].filter(Boolean));
  pintarMacro();pintar();
  // Una consulta por panel: no refetch al cambiar filtros ni una petición por cliente.
  Promise.resolve().then(async()=>{
    if(!vigente()||!panelRaiz.isConnected||!semana)return;
    const scope=ambitoDeclaracionesControl(ctx,semana);
    if(!scope)return;
    const ambito={...scope,real_id:ctx.real.id,vista_id:ctx.persona.id};
    try{
      const respuesta=await ctx.api(`clientes/evidencias_kpi/resumen?semana_inicio=${encodeURIComponent(semana)}`);
      if(!vigente()||!panelRaiz.isConnected||!inferiorVigente()||semanaDeclaracionesControl(hoyMadrid())!==semana)return;
      const actual=ambitoDeclaracionesControl(ctx,semana);
      declaraciones=proyectarDeclaracionesControl(respuesta,semana,ambito,actual,rows.map(r=>r.cliente_id),true);
      if(!vigente()||actual?.firma!==ambito.firma)return;
      pintarMacro();pintar();
    }catch(_){if(vigente()&&panelRaiz.isConnected&&inferiorVigente()&&semanaDeclaracionesControl(hoyMadrid())===semana&&ambitoDeclaracionesControl(ctx,semana)?.firma===ambito.firma){declaraciones=new Map();pintarMacro();pintar();}}
  });return panelRaiz;
}

// ================================================================== el número que manda
function heroNumero(ctx, cfg, n, puesto) {
  // R13 (E0): el catálogo marca `el_que_manda`; la config de cada puesto lo nombra (hoy coinciden los 6 marcados).
  // Si un puesto no nombra indicador, se toma el que el catálogo marque para ese puesto.
  let ind = cfg.indicador ? ctx.indicador(cfg.indicador)
    : (puesto && typeof ctx.indicadores === 'function' ? ctx.indicadores().find(i => i.puesto === puesto && i.el_que_manda) || null : null);
  const coberturaCRM = cfg.calculo === 'crm_verde';
  if (coberturaCRM) {
    // 319A: este cálculo mide lectura autorizada, no la clasificación histórica de salud.
    const formula = 'Número de subcuentas cliente autorizadas con fuente de lectura reciente válida, dentro de la copia parcial actual.';
    cfg = { ...cfg, titulo: 'Cobertura de lectura CRM', formula, umbral: null, meta: null, medible: 'medias', fuente: 'GoHighLevel · fecha de la copia visible; actualización según la fuente' };
    ind = { ...ind, nombre: cfg.titulo, formula, umbral: null, medible: 'medias', medible_porque: 'Copia parcial: lectura reciente no acredita salud, actividad completa ni cumplimiento.' };
  }
  const medible = cfg.medible || ind?.medible || (n?.fase2 ? 'no' : 'medias');
  const umbralTodo = cfg.umbral || (ind?.umbral && !/^Ver /.test(ind.umbral) ? ind.umbral : null);
  // V2 (B3): el matiz entre paréntesis del umbral («propuesta sin firmar: la misma vara que la trafficker») va a «¿Qué es?»
  const umbral = umbralTodo ? umbralTodo.replace(/\s*\([^()]*\)\s*$/, '') : null;
  const matizUmbral = umbralTodo && umbral !== umbralTodo ? umbralTodo.slice(umbral.length).trim().replace(/^\(|\)$/g, '') : null;
  const enDuda = n?.duda ? chipEstado('gris', 'Dato en duda') : null;
  const fase2 = n?.fase2 || medible === 'no';
  const estado = fase2 ? 'gris' : (n?.estado || 'gris');
  const titulo = L(coberturaCRM ? cfg.titulo : n?.titulo || cfg.titulo || ind?.nombre || 'Sin número');
  let cuerpo;
  if (n?.falta) cuerpo = [h('h3', { class: 'cifra-et' }, titulo), vacioLinea(`${n.falta.titulo}. ${n.falta.texto}`, { icono: n.falta.icono || 'info', quien: n.falta.quien })];
  else if (n?.error) cuerpo = vacioLinea(`No se ha podido calcular: ${n.error}`, { icono: 'alert' });
  else if (!fase2 && (n?.valor === null || n?.valor === undefined || n?.valor === '—')) {
    // R12 (A-A5): sin cifra, nunca un «—» suelto: «Sin dato» y el porqué (y cuándo llega), con el sello y la frescura
    // V2 (B-M6): un solo «Sin dato» (nunca «Sin dato. Sin dato: …»), y sin cartera, el motivo tal cual
    const ctxTxt = n?.contexto || 'El dato todavía no existe.';
    cuerpo = [h('h3', { class: 'cifra-et' }, titulo), vacioLinea(L(/^(sin dato|sin citas|sin cartera|no tienes|aún no|todavía no|ninguno)/i.test(ctxTxt) ? ctxTxt : `Sin dato. ${ctxTxt}`), { icono: 'hist' }),
      h('div', { class: 'fila' }, selloMedible(medible, ind?.medible_porque || undefined), enDuda, n?.frescura ? frescura(n.frescura) : null),
      umbral ? h('p', { class: 'sub' }, `Umbral: ${L(umbral)}`) : null];
  }
  else if (fase2) {
    cuerpo = [cifraPrincipal({ etiqueta: titulo, valor: 'Fase 2', estado: 'gris' }),
      vacioLinea(L(ind?.medible_porque) || 'Todavía no se puede medir con lo conectado.', { icono: 'hist' }),
      h('div', { class: 'fila' }, selloMedible('no', ind?.medible_porque)),
      n?.proxy ? h('p', { class: 'sub' }, L(`Mientras: ${n.proxy.valor} ${n.proxy.unidad || ''}. ${n.proxy.contexto || ''}`)) : null];
  } else {
    // La cifra que manda a 32 px (cifraPrincipal); su color sale de la regla única (colorCifra en el bloque).
    const c = n.comparacion;
    const hayDelta = c && c.delta !== null && c.delta !== undefined && !Number.isNaN(c.delta);
    const deltaTxt = hayDelta ? `${c.delta > 0 ? '▲ +' : c.delta < 0 ? '▼ ' : '= '}${fmt.num(c.delta, c.dec || 0)}${c.pct ? ' %' : (c.unidad || '')}` : null;
    cuerpo = [cifraPrincipal({
      etiqueta: titulo, valor: n.valor, unidad: n.unidad || null, estado,
      comparacion: hayDelta ? [chipEstado(colorCifra('delta', c.delta, { mejorSi: c.mejorSi }), deltaTxt, { punto: false }), ` ${c.texto || ''}`] : (c?.texto ? c.texto : null),
    }),
    h('div', { class: 'fila' }, selloMedible(medible, ind?.medible_porque || undefined), enDuda, n.frescura ? frescura(n.frescura) : null),
    umbral ? h('p', { class: 'sub' }, `Umbral: ${L(umbral)}`) : null,
    n.contexto ? h('p', { class: 'sub' }, L(n.contexto)) : null,
    // R13: el segundo indicador del puesto (p. ej. la salud de la cartera del account), debajo y en pequeño; V2 (A4): con su
    // color (nunca verde con un cliente en crítico)
    n.proxy && n.proxy.valor !== null && n.proxy.valor !== undefined ? h('p', { class: 'sub fila', style: { gap: 'var(--s-1)' } }, `Segundo indicador: ${L(n.proxy.titulo || 'índices registrados · provisional')} ·`,
      chipEstado(n.proxy.estado || 'gris', `${n.proxy.valor}${n.proxy.unidad ? ` (${n.proxy.unidad})` : ''}`)) : null];
  }
  const queEs = h('details', { class: 'que-es' }, h('summary', {}, '¿Qué es?'),
    h('dl', {},
      h('dt', {}, 'Qué mide'), h('dd', {}, L(cfg.formula || ind?.formula || cfg.titulo || '—')),
      h('dt', {}, coberturaCRM ? 'Alcance' : 'Verde / ámbar / rojo'), h('dd', {}, coberturaCRM ? 'Lectura parcial autorizada, sin umbral de rendimiento ni semáforo contractual.' : [L(umbral) || '—', matizUmbral ? ` (${L(matizUmbral)})` : null]),
      n?.detalle ? [h('dt', {}, 'Detalle'), h('dd', {}, L(n.detalle))] : null,
      h('dt', {}, 'Fuente y frecuencia'), h('dd', {}, cfg.fuente ? L(cfg.fuente) : ind ? `${ind.fuente || '—'} · ${ind.frecuencia || '—'}` : '—'),
      cfg.meta ? [h('dt', {}, 'Meta'), h('dd', {}, L(cfg.meta))] : null));
  return panel({ titulo: 'El número que manda', icono: cfg.icono || 'target', id: 'mid-num-t' },
    h('div', { class: 'cuerpo pila' }, cuerpo, queEs));
}

// ================================================================== A1 · «Lo mío» (43_IDEAS_MEJORA)
// Una sola lista personal, arriba del todo, sin duplicados y ordenada por plazo (vencido · hoy · esta semana · sin fecha)
// y gravedad. Junta: tus alertas (la definición «mías» de Alertas con la cola viva: lote y posponer incluidos), los
// correos sin contestar de tu cartera, las piezas que te toca revisar, las menciones del chat sin leer, las decisiones que
// esperan tu sí y lo urgente que suben los bloques (antes «Lo primero hoy»). Cada fila: qué, de quién, por qué, plazo y UN
// botón con el verbo que abre el objeto exacto; si es alerta, además «Lo tengo» y «Posponer» (mismos tipos que Alertas).
// Ronda U (50 #3): filas compactas de ~60 px → 10 a la vista en escritorio y 8 en tableta y móvil (antes 6/3/4 de 142 px).
const LM_A_LA_VISTA = { escritorio: 10, tableta: 8, movil: 8 };
/** Qué va arriba en cada puesto (la línea bajo el título de «Lo mío»). */
const ORDEN_TXT = { direccion: 'arriba, tus decisiones con reloj y los cobros', finanzas_direccion: 'arriba, los cobros', administracion: 'arriba, lo que toca hoy de facturación y cobros',
  operaciones: 'arriba, lo que te llega escalado', proyectos: 'arriba, lo que espera tu decisión', jefa_publicidad: 'arriba, lo de tu equipo que necesita tu decisión',
  jefa_crm: 'arriba, lo de tu equipo que necesita tu decisión', jefa_seo: 'arriba, lo de tu equipo que necesita tu decisión', account: 'arriba, correos y clientes críticos',
  rrhh: 'arriba, las personas en alerta' };

/** Ronda U (50 #3): «Lo mío» en filas de ~60 px (icono · qué · plazo y por qué en una línea · verbo a la derecha), sobre la
 *  misma lista común (ol.primero: atajos j/k y «e» siguen igual). En el móvil, los botones secundarios solo con icono. */
function listaCompacta(items, { vacio: v, movil = false } = {}) {
  if (!items.length) return estadoVacio(v);
  const UNA = { whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', minWidth: '0' };
  // Flex con salto de línea (no rejilla): el texto pide al menos 240 px; si con los botones no cabe (480-700 px, o un panel
  // estrecho), los botones bajan a su línea, a la derecha. Nunca encima del texto ni el título reducido a «D».
  return h('ol', { class: 'primero', 'data-compacta': '' }, items.map(it => h('li', { class: it.estado || 'rojo',
    style: { display: 'flex', flexWrap: 'wrap', columnGap: 'var(--s-3)', rowGap: 'var(--s-1)', padding: `var(--s-2) ${movil ? 'var(--s-3)' : 'var(--s-4)'}`, alignItems: 'center' } },
  h('span', { class: 'num', 'aria-hidden': 'true', style: { flex: 'none' } }, it.icono ? icono(it.icono) : ''),
  h('div', { style: { minWidth: '0', flex: '1 1 240px' } },
    // en el móvil el qué puede ocupar 2 líneas (a 390 px una sola cortaba «Decidir: Extens…»)
    h('div', { class: 'mot', style: movil ? { ...CORTA, overflowWrap: 'anywhere' } : UNA, title: it.titulo || null }, it.motivo),
    h('div', { class: 'det', style: { display: 'flex', gap: 'var(--s-2)', alignItems: 'center', marginTop: '0', minWidth: '0' } },
      it.chip ? Object.assign(it.chip, { style: 'flex: none; white-space: nowrap' }) : null, h('span', { class: 'sub', style: UNA, title: it.porque || null }, it.porque || ''))),
  h('div', { class: 'acc', style: { flexWrap: 'nowrap', gridColumn: 'auto', marginTop: '0', marginLeft: 'auto', alignItems: 'center', flex: 'none', justifyContent: 'flex-end' } }, it.botones || []))));
}
const ICONO_TIPO = { alerta: 'campana', correo: 'mail', revision: 'check', mencion: 'chat', decision: 'flag', persona: 'persona', aviso: 'plug' };

/** Ficheros extra que lee «Lo mío», solo los que pueden traer algo para esta persona (sin 403 de ruido). */
function usaLoMio(ctx) {
  const p = ctx.persona.puestos || [];
  return LO_MIO_USA.filter(f => (f === 'bandeja/bandeja' ? !!ctx.carteraPorSilla?.account?.size && ctx.veModulo('bandeja')
    : f === 'produccion/produccion' ? ctx.veModulo('produccion') && revisaPiezas(ctx)
      : f === 'decisiones/reloj' ? ctx.veModulo('decisiones') && (p.includes('direccion') || p.includes('proyectos')) : false));
}
/** La decisión del reloj por su id (o su clave), si el fichero está cargado (dirección y proyectos). */
const decisionDe = (D, id) => (D.opcional('decisiones/reloj')?.decisiones || []).find(d => String(d.id) === String(id) || d.clave === id) || null;

// ---- Ronda U (50 #3): «Lo mío» ORDENADO POR PUESTO. Dentro de cada rango manda el orden de siempre (plazo y gravedad).
// Si una fila trae «prioridad» (el cerebro de decisiones v2 la publicará por objeto: número, o { valor | puntos, motivo }),
// manda esa prioridad; el orden por puesto queda de respaldo para lo que no la traiga.
const prioridadDe = x => { const p = x.prioridad; return typeof p === 'number' ? p : typeof p?.puntos === 'number' ? p.puntos : typeof p?.valor === 'number' ? p.valor : null; };
const motivoPrioridad = x => { const m = typeof x.prioridad === 'object' && x.prioridad?.motivo; return m ? `Primero porque ${/^(es|son|lleva|llevan|vence|vencen)\b/i.test(m) ? m[0].toLowerCase() + m.slice(1) : m}` : null; };
const esDecision = x => x.tipo === 'decision' || x.alerta?.tipo === 'dir_decision';
const esCobro = x => /^adm_/.test(x.alerta?.tipo || '') || /^(impago|cobro|firmado|devuelto)/.test(String(x.clave || '')) || (x.grupos || []).some(g => /^(factura|impago-cli)/.test(g || ''));
const esPersona = x => x.alerta?.tipo === 'rrhh_alerta' || x.tipo === 'persona';
const deArea = (x, deps) => !!x.alerta && (deps || []).includes(x.alerta.departamento);
const JEFAS = { jefa_publicidad: ['publicidad'], jefa_crm: ['crm'], jefa_seo: ['seo', 'web'] };
/** Rango de una fila en «Lo mío» según el puesto de la pestaña (0 primero). Lo dice el 50 §2 y el encargo de la ronda U. */
function rangoPuesto(puesto, x) {
  const rev = x.tipo === 'revision';
  if (puesto === 'direccion') return esDecision(x) ? 0 : esCobro(x) ? 1 : (x.escaladaAMi || esPersona(x)) ? 2 : x.tipo === 'aviso' ? 3 : rev ? 5 : 4;
  if (puesto === 'finanzas_direccion') return esCobro(x) ? 0 : esDecision(x) ? 1 : rev ? 3 : 2;
  if (puesto === 'proyectos') return esDecision(x) ? 0 : /^visto:/.test(String(x.clave)) || x.escaladaAMi ? 1 : rev ? 3 : 2;
  if (puesto === 'operaciones') return x.escaladaAMi || x.vuelve ? 0 : x.tipo === 'alerta' ? 1 : x.tipo === 'bloque' ? 2 : x.tipo === 'aviso' ? 3 : rev ? 4 : 2;
  if (JEFAS[puesto]) return x.escaladaAMi ? 0 : deArea(x, JEFAS[puesto]) || (x.tipo === 'bloque' && !rev) ? (x.grav === 'alta' ? 1 : 2) : rev ? 4 : 3;
  if (puesto === 'administracion') return x.alerta?.tipo === 'adm_sin_alta' ? 0 : esCobro(x) ? 1 : rev ? 3 : 2;
  if (puesto === 'account') return x.tipo === 'correo' || x.alerta?.tipo === 'acc_correos' ? 0 : x.alerta?.tipo === 'acc_critico' || /critico/.test(String(x.clave)) ? 1 : rev ? 3 : 2;
  if (puesto === 'rrhh') return esPersona(x) ? 0 : 1;
  return 0;
}
function ordenarPorPuesto(filas, puesto) {
  return filas.map((x, i) => ({ x, i, p: prioridadDe(x), r: rangoPuesto(puesto, x) }))
    .sort((a, b) => ((a.p === null) - (b.p === null)) || (a.p !== null && b.p !== null ? b.p - a.p : 0) || a.r - b.r || a.i - b.i)
    .map(o => o.x);
}
const finDeHoy = ahora => { const d = new Date(ahora); d.setHours(23, 59, 0, 0); return d; };
const nombreCli = (ctx, id) => (id ? ctx.clientes?.find(c => c.id === id)?.nombre || ctx.verdad?.(id)?.nombre || null : null);
const gravDePeso = p => (p >= 3 ? 'alta' : p >= 2.5 ? 'media' : 'baja');

/** Todas las filas candidatas (sin unir). Cada una: { tipo, clave, que, quien, porque, plazo, grav, ir|href, verbo, objeto, grupos }. */
/** V2 (A1 / B-A2): las alertas de Captación hablan de la PUBLICIDAD, no de la gravedad del cliente: «Akua · Captación en
 *  crítico» se lee «Akua · publicidad urgente (cliente en atención)», con la gravedad de la verdad única al lado. */
const TITULO_CAPTACION = { pub_critico: 'publicidad crítica', pub_atencion: 'publicidad a vigilar' };   // §2.1: «urgente» solo para plazos
const GRAV_TXT = { critico: 'cliente crítico', atencion: 'cliente a vigilar', bien: 'cliente bien' };
function tituloAlerta(ctx, a) {
  const t = TITULO_CAPTACION[a.tipo];
  if (!t) return a.titulo || a.motivo;
  const g = a.cliente_id ? ctx.verdad?.(a.cliente_id)?.gravedad : null;
  return g ? `${t} (${GRAV_TXT[g] || 'cliente sin estado'})` : t;
}
/** V2 (M12): adónde lleva una alerta: a la cosa concreta. «Persona en alerta» abre la ficha de ESA persona con «Anotar
 *  conversación y plan» abierto (#/personas/<id>?plan=1), no Personas en general; si la alerta trae una ruta ideal, esa. */
function irAlerta(ctx, a) {
  if (a.tipo === 'rrhh_alerta' && a.persona_id && ctx.veModulo('personas')) { const ir = `#/personas/${encodeURIComponent(a.persona_id)}?plan=1`; return { ir, verbo: 'Anotar el plan', objeto: objetoDe(ir) }; }
  const ir = !a.ir_objeto && a.ir_ideal && ctx.veModulo(String(a.ir_ideal).replace(/^#\//, '').split('/')[0]) ? a.ir_ideal : a.ir || null;
  return { ir, verbo: ir === a.ir ? a.ir_texto || null : null, objeto: objetoDe(ir) };
}
/** V2 · ¿Qué entra en «Lo mío» de ESTA pestaña de puesto? Quien tiene un solo puesto, todo. Quien tiene varios (Jerónimo,
 *  Valeria, Yessica, Coti, Tomás…), lo de ese puesto: las alertas de sus departamentos (config → comun.lo_mio_departamentos),
 *  los correos solo en «Account», las piezas por la regla de ese puesto y las decisiones solo en dirección / proyectos. Las
 *  menciones y los avisos a su nombre salen en todas. */
function alcanceLoMio(ctx, puesto) {
  const varios = (ctx.persona.puestos || []).length > 1;
  const deps = varios ? (CONFIG.comun?.lo_mio_departamentos || {})[puesto] : null;
  return {
    varios, puesto,
    alerta: a => !varios || deps === null || deps === undefined || deps.includes(a.departamento),
    correos: !varios || puesto === 'account',
    decision: x => !varios || (puesto === 'direccion' && x.tipo === 'para_tomas') || (puesto === 'proyectos' && x.tipo === 'para_coti'),
  };
}
function filasLoMio(lm, ahora) {
  const { ctx, D, A, accAlertas, acciones, extra, campana, bloques, avisos, local, puesto } = lm;
  const f = [];
  const al = alcanceLoMio(ctx, puesto);
  // 1 · alertas «mías» (las mismas que cuenta Alertas), las de esta pestaña de puesto
  const mias = alertasMias(A, accAlertas, { yo: ctx.persona.id, personas: ctx.datos.personas, ahora, local });
  lm.nAlertasTodas = mias.length;   // la cifra de «Mías» en Alertas (el botón la enseña tal cual)
  for (const x of mias.filter(y => al.alerta(y.a))) {
    const a = x.a;
    if (a.tipo === 'dir_decision' && lm.contestadas?.has(String(a.id).split(':').slice(1).join(':'))) continue;   // ya contestada aquí
    // V2 (M6): sin el id interno del departamento delante («administracion ·», «rrhh ·»): el motivo ya dice de quién es
    // Ronda U (50 #3): la decisión dice QUÉ hay que decidir y la recomendación (antes «Decisión con reloj»), y la persona en
    // alerta, de quién es (antes «Persona en alerta» diez veces). La decisión lleva su objeto para «Aprobar» en la fila.
    const dec = a.tipo === 'dir_decision' ? decisionDe(D, String(a.id).split(':').slice(1).join(':')) : null;
    const quienAl = !a.cliente && a.persona_id && ctx.nombre ? ctx.nombre(a.persona_id) : null;
    f.push({ tipo: 'alerta', clave: a.id, alerta: a, est: x.est, escaladaAMi: x.escaladaAMi, decision: dec, prioridad: a.prioridad ?? null, cliente_id: a.cliente_id || null,
      que: dec ? `Decidir: ${dec.titulo}` : a.cliente ? `${a.cliente} · ${tituloAlerta(ctx, a)}` : quienAl ? `${quienAl} · ${String(a.titulo || a.motivo).replace(/^Persona en alerta$/, 'en alerta')}` : (a.titulo || a.motivo), quien: null,
      porque: dec ? `Recomendación: ${dec.recomendacion || '—'}${dec.quien && ctx.nombre ? ` · la sube ${ctx.nombre(dec.quien)}` : ''}` : a.motivo, plazo: x.vence, grav: a.gravedad === 'alta' ? 'alta' : a.gravedad === 'baja' ? 'baja' : 'media',
      ...irAlerta(ctx, a), grupos: [temaAlerta(a)] });
  }
  // 2 · correos sin contestar de tu cartera (regla de la Bandeja), uno por cliente con el más antiguo
  for (const { x, n, quejas, espera } of al.correos ? correosLoMio(ctx, D, extra) : []) {
    const ir = ctx.veModulo('bandeja') ? `#/bandeja/${encodeURIComponent(x.id)}` : null;
    f.push({ tipo: 'correo', clave: `correo:${x.id}`, cliente_id: x.cliente_id || null, que: `${x.cliente || 'Sin cliente reconocido'} · contestar «${x.asunto}»`, quien: null,
      porque: `${n === 1 ? '1 correo sin contestar' : `${n} correos sin contestar`}${quejas ? ` (${quejas === 1 ? '1 queja' : `${quejas} quejas`})` : ''} · el más antiguo, ${espera}`,
      plazo: new Date(ahora.getTime() + (48 - (Number(x.horas) || 0)) * 36e5), grav: x.gravedad === 'rojo' || x.queja ? 'alta' : x.gravedad === 'ambar' ? 'media' : 'baja',
      ir, verbo: 'Contestar el correo', objeto: objetoDe(ir), grupos: [x.cliente_id ? `correo-cli:${x.cliente_id}` : null, `correo:${x.id}`] });
  }
  // 3 · piezas que te toca revisar (Producción › Por revisar), una fila por cliente: abre la que más espera y dice cuántas hay
  const porCli = new Map();
  for (const x of piezasMeTocan(ctx, D, { puesto })) { const k = x.cli || `interno:${x.clienteNombre}`; (porCli.get(k) || porCli.set(k, []).get(k)).push(x); }
  // V2 (B-A1): como mucho 2 filas de revisión (los dos clientes cuya pieza más espera) y una tercera que junta el resto y abre
  // Producción › Por revisar: las alertas de cada uno no quedan escondidas detrás de 6 filas de piezas.
  const masEspera = l => Math.max(...l.map(y => Number(y.dias) || 0));
  const grupos = [...porCli.entries()].sort((a, b) => masEspera(b[1]) - masEspera(a[1]));
  const resto = grupos.slice(2).flatMap(([, l]) => l);
  if (resto.length) {
    const x = resto.slice().sort((p, q) => (Number(q.dias) || 0) - (Number(p.dias) || 0))[0];
    const dias = Number(x.dias) || 0;
    const ir = ctx.veModulo('produccion') ? '#/produccion' : null;
    f.push({ tipo: 'revision', clave: 'rev:resto', n: resto.length, que: `Revisar ${fmt.plural(resto.length, 'pieza más', 'piezas más')} de ${fmt.plural(grupos.length - 2, 'cliente', 'clientes')}`, quien: null,
      porque: `La que más espera, «${x.tarea}» (${x.clienteNombre}), desde hace ${dias < 1 ? 'menos de un día' : fmt.plural(Math.round(dias), 'día', 'días')}; el plazo es de 48 h`,
      plazo: new Date(ahora.getTime() + (2 - dias) * 864e5), grav: dias > 2 ? 'media' : 'baja', ir, verbo: 'Abrir Por revisar', objeto: 'produccion:por-revisar', grupos: resto.map(y => `tarea:${y.id}`) });
  }
  for (const [k, l] of grupos.slice(0, 2)) {
    const x = l.slice().sort((p, q) => (Number(q.dias) || 0) - (Number(p.dias) || 0))[0];
    const ir = `#/produccion/${encodeURIComponent(x.id)}`;
    const dias = Number(x.dias) || 0;
    const espera = dias < 1 ? 'menos de un día' : `${fmt.num(dias, 0)} día${Math.round(dias) === 1 ? '' : 's'}`;
    f.push({ tipo: 'revision', clave: `rev:${k}`, n: l.length, cliente_id: x.cli || null, que: l.length === 1 ? `Revisar «${x.tarea}»` : `Revisar ${fmt.num(l.length)} piezas de ${x.clienteNombre}`, quien: l.length === 1 ? x.clienteNombre : null,
      porque: `${l.length === 1 ? 'Espera' : `La que más espera, «${x.tarea}»,`} tu visto bueno desde hace ${espera} (${x.estado}${x.autoresTxt ? `, de ${x.autoresTxt}` : ''}); el plazo es de 48 h`,
      plazo: new Date(ahora.getTime() + (2 - dias) * 864e5), grav: dias > 2 ? 'media' : 'baja', ir, verbo: l.length === 1 ? 'Revisar la pieza' : 'Revisar la primera',
      objeto: objetoDe(ir), grupos: l.map(y => `tarea:${y.id}`) });
  }
  // 4 · menciones del chat sin leer (la campana; los avisos de alertas ya están arriba como alertas)
  for (const x of (campana?.items || []).filter(y => y.tipo === 'mencion' && y.sin_leer)) {
    const ir = `#/chat-equipo/${encodeURIComponent(x.canal_id)}`;
    const hora = x.hora ? new Date(x.hora) : ahora;
    f.push({ tipo: 'mencion', clave: `men:${x.id}`, que: `${ctx.nombre ? ctx.nombre(x.quien) : x.quien} te menciona en ${x.canal}`, quien: x.canal,
      porque: `«${x.texto}»`, plazo: new Date(hora.getTime() + 24 * 36e5), grav: 'media', ir, verbo: 'Abrir el mensaje', objeto: `men:${x.id}`, grupos: [] });
  }
  // 5 · decisiones que esperan tu sí (reloj de 48 h)
  // Ronda U (50 #5): un solo destino por objeto: la decisión abre ESA decisión (#/decisiones/reloj/<id>), igual que su alerta.
  for (const x of decisionesMias(ctx, D).filter(al.decision).filter(y => !lm.contestadas?.has(String(y.id)))) {
    const ir = ctx.veModulo('decisiones') ? `#/decisiones/reloj/${encodeURIComponent(x.id)}` : null;
    f.push({ tipo: 'decision', clave: `dec:${x.id}`, que: `Decidir: ${x.titulo}`, quien: `subida por ${ctx.nombre ? ctx.nombre(x.quien) : x.quien}`, decision: decisionDe(D, x.id) || x,
      porque: `Recomendación: ${x.recomendacion || '—'}`, plazo: x.vence ? new Date(String(x.vence).replace(' ', 'T')) : null, grav: x.estado === 'en plazo' ? 'media' : 'alta',
      ir, verbo: 'Abrir la decisión', objeto: objetoDe(ir) || `dec:${x.id}`, grupos: [`dec:${x.id}`], prioridad: x.prioridad ?? null });
  }
  // 6 · lo urgente de los bloques (antes «Lo primero hoy»), los avisos de fuentes caídas y los avisos de persona
  for (const b of bloques) for (const c of b.r.primero || []) {
    const ir = c.ruta ? `#/${c.ruta}` : null;
    const cli = nombreCli(ctx, c.cliente_id);
    // V2 (C-10): si la cosa trae su fecha (una tarea vencida), el plazo es ESA fecha («Vencido hace 4 días»), nunca «Sin fecha»
    const pz = c.plazo ? new Date(String(c.plazo).length <= 10 ? `${c.plazo}T23:59:00` : String(c.plazo).replace(' ', 'T')) : null;
    f.push({ tipo: 'bloque', clave: c.clave, cliente_id: c.cliente_id || null, que: c.motivo, quien: cli && String(c.motivo).includes(cli) ? null : cli || b.titulo, porque: c.detalle || '', icono: c.icono, peso: c.peso, prioridad: c.prioridad ?? null,
      plazo: pz && !Number.isNaN(+pz) ? pz : c.peso >= 3 ? finDeHoy(ahora) : null, grav: gravDePeso(c.peso), ir, href: c.href || null, abrirEn: c.abrirEn, verbo: null,
      objeto: objetoDe(ir) || (c.href ? `ext:${c.href}` : null), grupos: [c.clave, c.grupo] });
  }
  for (const a of avisos.filter(x => x.estado === 'para_avisar' && x.dia === (ctx.hoy || hoyMadrid()) && !x.visto))
    f.push({ tipo: 'aviso', clave: `aviso:${a.tipo}:${a.clave}`, que: avisoLlano(a.texto), quien: 'Aviso del sistema', porque: 'Una fuente de datos no ha llegado a tiempo: las cifras que salen de ella pueden ser viejas', peso: 3.3,
      plazo: finDeHoy(ahora), grav: 'alta', ir: '#/ajustes/avisos', verbo: 'Abrir el aviso', objeto: `aviso:${a.tipo}:${a.clave}`, grupos: [] });
  // avisos de persona a su nombre (horas, carga…); los de account no salen a quien ya no lleva clientes como account (R12)
  const sinCuentas = !ctx.persona.puestos.includes('account') || (!!ctx.carteraPorSilla && !ctx.carteraPorSilla.account?.size);
  const deAccount = x => /account|informes de|semáforo sin rellenar|rompe el semanal/i.test(`${x.tipo || ''}`);
  // V2: con varios puestos, los avisos de account (semáforo, revisión del account, informes…) solo en la pestaña «Account»
  const otraPestana = x => al.varios && puesto !== 'account' && deAccount(x);
  for (const a of ctx.datos.alarmas.filter(x => x.ambito === 'persona' && x.responsable_id === ctx.persona.id && x.gravedad === 'rojo' && !(sinCuentas && deAccount(x)) && !otraPestana(x))) {
    const ir = a.enlace ? null : /imput/i.test(`${a.tipo} ${a.texto}`) && ctx.veModulo('horas') ? '#/horas' : `#/personas/${encodeURIComponent(ctx.persona.id)}`;
    f.push({ tipo: 'persona', clave: `persona:${a.id}`, que: a.tipo, quien: 'Tú', porque: a.texto || '', peso: 2.7, plazo: finDeHoy(ahora), grav: 'media',
      ir, href: a.enlace || null, abrirEn: a.enlace ? origenUrl(a.enlace) || 'su herramienta' : null, objeto: objetoDe(ir) || (a.enlace ? `ext:${a.enlace}` : null), grupos: [] });
  }
  // «Ya lo he pedido» (petición 19, cola de antes): lo pedido hace < 24 h no sale; a las 48 h vuelve como urgente
  const horasVuelve = CONFIG.comun?.vuelve_arriba_h || 48;
  const pedidos = new Map();
  for (const a of acciones.filter(x => x.modulo === 'mi-dia' && T_PEDIDO.includes(x.tipo))) if (!pedidos.has(a.objeto) || a.creada < pedidos.get(a.objeto).creada) pedidos.set(a.objeto, a);
  // V2 (B-M10): lo que trata de una alerta que has pospuesto (mismo tema u objeto) tampoco sale hasta que vuelva la alerta
  const apartadas = apartadasLoMio(A, accAlertas, { personas: ctx.datos.personas, ahora, local });
  const apartada = x => x.tipo !== 'alerta' && ((x.objeto && apartadas.has(`o:${x.objeto}`)) || (x.grupos || []).some(g => g && apartadas.has(`g:${g}`)));
  // Cerebro v2: alerta → por_alerta[id]; correo o revisión con cliente → por_cliente[cliente]; si no, por_objeto[ruta]
  const P = lm.prio;
  if (P) for (const x of f) {
    if (x.prioridad !== null && x.prioridad !== undefined) continue;
    const cid = x.alerta?.cliente_id || x.cliente_id || (x.grupos || []).map(g => /^correo-cli:(.+)$/.exec(g || '')?.[1]).find(Boolean) || null;
    x.prioridad = (x.tipo === 'alerta' ? P.por_alerta?.[x.clave] : null) || ((x.tipo === 'correo' || x.tipo === 'revision') && cid ? P.por_cliente?.[cid] : null) || (x.ir ? P.por_objeto?.[x.ir] : null) || null;
  }
  return f.filter(x => !apartada(x)).filter(x => {
    const p = x.tipo !== 'alerta' && pedidos.get(x.clave);
    if (!p) return true;
    const hh = edadUTC(p.creada);
    if (hh < 24) return false;
    if (hh >= horasVuelve) { x.vuelve = hh; x.grav = 'alta'; x.plazo = new Date(Math.min(+(x.plazo || ahora), +ahora)); }
    return true;
  });
}

/** V2 (M7): el aviso de una fuente caída, en llano: sin el código («(403)») ni la orden de terminal («--en-vivo»); el paso
 *  técnico está en Ajustes › Avisos, que es adonde lleva el botón. */
const avisoLlano = t => L(String(t || ''));
/** Texto del plazo: «Vencido hace 3 h» · «Vence hoy a las 17:53» · «Vence mañana a las 17:53» · «Vence el vie 9-oct» · «Sin fecha». */
function plazoTxt(plazo, ahora, tramo) {
  if (!plazo) return 'Sin fecha';
  const hora = plazo.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' });
  if (tramo === 0) { const hh = (ahora - plazo) / 36e5; return hh < 1 ? 'Vencido hace menos de 1 h' : hh < 48 ? `Vencido hace ${Math.round(hh)} h` : `Vencido hace ${Math.round(hh / 24)} días`; }
  // D1: es el plazo, no la hora del aviso: «Vence hoy a las 17:53» (como En rojo y Bandeja), nunca «Hoy, 17:53».
  if (tramo === 1) return hora === '23:59' ? 'Vence hoy' : `Vence hoy a las ${hora}`;
  const man = new Date(ahora); man.setDate(man.getDate() + 1);
  if (plazo.toDateString() === man.toDateString()) return hora === '23:59' ? 'Vence mañana' : `Vence mañana a las ${hora}`;
  return `Vence el ${PALABRAS_DIA[plazo.getDay()].slice(0, 3)} ${plazo.getDate()}-${MESES[plazo.getMonth()].slice(0, 3)}`;
}
const COLOR_TRAMO = ['rojo', 'ambar', 'azul', 'gris'];

/** El panel «Lo mío». Se repinta solo al marcar «Lo tengo» o «Posponer» (las cifras bajan a la vez que en Alertas). */
function panelLoMio(lm) {
  const { ctx } = lm;
  const sec = h('section', { class: 'panel', 'aria-labelledby': 'mid-lomio-t', 'data-lo-mio': '' });
  const movil = typeof matchMedia === 'function' && matchMedia('(max-width: 640px)').matches;
  lm.movil = movil;
  let abierto = false;
  const pintar = () => {
    const ahora = new Date();
    const unidas = unirLoMio(filasLoMio(lm, ahora), ahora);
    const quitadas = unidas.quitadas;
    const filas = ordenarPorPuesto(unidas.filas, lm.puesto);
    const mal = repetidosLoMio(filas);
    if (mal.length) console.warn('Lo mío · repetidos', mal);   // no debería pasar nunca: lo vigila pruebas_coherencia.py
    const n = t => filas.filter(x => x.tipo === t).length;
    const nAl = n('alerta');
    sec.dataset.total = String(filas.length);
    sec.dataset.alertas = String(nAl);
    sec.dataset.revisiones = String(filas.filter(x => x.tipo === 'revision').reduce((s, x) => s + (x.n || 1), 0));
    const partes = [
      nAl ? `${fmt.plural(nAl, 'alerta tuya', 'alertas tuyas')}${(lm.nAlertasTodas ?? nAl) !== nAl ? ` de esta pestaña (${fmt.num(lm.nAlertasTodas)} en Alertas)` : ' (las de Alertas)'}` : null,
      n('correo') ? fmt.plural(n('correo'), 'cliente con correos sin contestar', 'clientes con correos sin contestar') : null,
      n('revision') ? `${fmt.plural(filas.filter(x => x.tipo === 'revision').reduce((s, x) => s + (x.n || 1), 0), 'pieza espera', 'piezas esperan')} tu visto bueno (últimos 30 días, como Producción › Por revisar)` : null,
      n('mencion') ? fmt.plural(n('mencion'), 'mención', 'menciones') : null,
      n('decision') ? fmt.plural(n('decision'), 'decisión', 'decisiones') : null,
    ].filter(Boolean);
    const vencidas = filas.filter(x => tramoPlazo(x.plazo, ahora) === 0).length;
    // en una línea: cuántas y cuántas vencidas; el desglose, debajo y solo en escritorio (en el móvil, en el «title»)
    const sub = filas.length ? `${fmt.plural(filas.length, 'cosa', 'cosas')} para ti${vencidas ? ` · ${fmt.num(vencidas)} con el plazo pasado` : ''} · ${ORDEN_TXT[lm.puesto] || 'lo vencido y lo grave arriba'}` : 'Sin avisos disponibles en esta lista';
    const desglose = [...partes, quitadas ? `${fmt.plural(quitadas, 'aviso repetido', 'avisos repetidos')} en la misma fila` : null].filter(Boolean).join(' · ');
    const tableta = !movil && typeof matchMedia === 'function' && matchMedia('(max-width: 1180px)').matches;
    const tope = movil ? LM_A_LA_VISTA.movil : tableta ? LM_A_LA_VISTA.tableta : LM_A_LA_VISTA.escritorio;
    const lista = items => listaCompacta(items.map(x => itemLoMio(lm, x, ahora, pintar)), { movil, vacio: { titulo: 'No hay avisos disponibles para ti', porque: ctx.veModulo('mi-trabajo') ? 'Esta lista reúne avisos de las fuentes disponibles. Abre «Mi trabajo» arriba para revisar tus tareas, fechas y estados; consulta los bloques de abajo para ver datos pendientes.' : 'Esta lista reúne avisos de las fuentes disponibles. Consulta los bloques de abajo para ver qué se ha podido leer y qué datos están pendientes.' } });
    const marcarFilas = (ol, items) => { ol.querySelectorAll?.(':scope > li').forEach((li, i) => { const x = items[i]; if (!x) return; li.dataset.filaMia = x.clave; li.dataset.tipo = x.tipo; if (x.objeto) li.dataset.objeto = x.objeto; }); return ol; };
    const primeras = filas.slice(0, tope), resto = filas.slice(tope);
    const cuerpo = [marcarFilas(lista(primeras), primeras)];
    if (resto.length) {
      const det = h('details', { class: 'que-es', style: { padding: '0 var(--relleno) var(--s-3)' }, open: abierto || null },
        h('summary', {}, `Ver ${fmt.num(resto.length)} más`), marcarFilas(lista(resto), resto));
      det.addEventListener('toggle', () => { abierto = det.open; });
      cuerpo.push(det);
    }
    sec.replaceChildren(
      // Ronda U (50 #3): cabecera de una línea; el desglose («18 alertas tuyas · 2 piezas…») va en el title, no empuja la lista
      h('header', { style: { padding: `var(--s-3) ${movil ? 'var(--s-3)' : 'var(--relleno)'}` } }, h('div', { style: { minWidth: '0', flex: '1 1 260px' } }, h('h2', { id: 'mid-lomio-t' }, icono('zap'), 'Lo mío · avisos'), h('p', { class: 'sub', title: desglose || null }, sub)),
        ctx.veModulo('alertas') && (lm.nAlertasTodas ?? nAl) ? h('a', { class: 'bt mini', href: '#/alertas', title: 'La misma cifra que «Mías» en Alertas' }, `Alertas · ${fmt.num(lm.nAlertasTodas ?? nAl)}`, icono('derecha')) : null),
      ...cuerpo);
  };
  pintar();
  return sec;
}

/** Una fila de «Lo mío» para listaCompacta: qué · de quién · por qué · plazo · verbo (+ Lo tengo / Posponer si es alerta). */
function itemLoMio(lm, x, ahora, repintar) {
  const { ctx } = lm;
  const tramo = tramoPlazo(x.plazo, ahora);
  const a = x.alerta;
  const dec = x.decision || null;
  const puede = !!a && ctx.veModulo('alertas') && !ctx.soloLectura;
  const estado = x.est?.estado;
  // un solo chip: el plazo y, si hay, el estado («Vencido hace 2 h · te ha llegado escalada»)
  const extraEstado = [x.vuelve ? `toca escalarlo, lo pediste hace ${fmt.num(x.vuelve / 24, 0)} días` : null, estado === 'lo_tengo' ? 'lo tienes tú' : null,
    x.escaladaAMi ? 'te ha llegado escalada' : null, estado === 'reabierta' ? 'reabierta' : null].filter(Boolean);
  const chips = [chipEstado(x.vuelve || x.escaladaAMi || estado === 'reabierta' ? 'rojo' : estado === 'lo_tengo' && tramo ? 'azul' : COLOR_TRAMO[tramo],
    [plazoTxt(x.plazo, ahora, tramo), ...extraEstado].join(' · '))];
  const marcar = async (tipo, extra = {}) => {
    const hasta = extra.hasta || null;
    await ctx.accion({ herramienta: 'app', modulo: 'alertas', tipo, objeto: a.id, cliente_id: a.cliente_id || null,
      texto: (tipo === 'alerta_posponer' ? `Pospuesta hasta el ${fDiaHoraRO(hasta)}: ${a.motivo}` : `Lo tengo: ${a.motivo}`).slice(0, 400),
      vista_previa: { alerta: a.id, departamento: a.departamento, motivo: a.motivo, estado: tipo === 'alerta_posponer' ? 'pospuesta' : 'lo_tengo', ...extra, desde: 'mi-dia' } });
    lm.local.set(a.id, { estado: tipo === 'alerta_posponer' ? 'pospuesta' : 'lo_tengo', hasta });
    avisoFlotante(tipo === 'alerta_posponer' ? `Pospuesta hasta el ${fDiaHoraRO(hasta)}: no cuenta ni escala hasta entonces` : 'Anotado: lo tienes tú. El escalado se para.');
    setTimeout(repintar, 600);
  };
  const m = lm.movil;
  const verboTxt = x.ir ? x.verbo || verbo(String(x.ir).replace(/^#\//, '')) : `Abrir en ${x.abrirEn || 'origen'}`;
  // En el móvil el verbo va en icono (con su nombre para lectores de pantalla y en el title): la fila cabe en ~60 px.
  const soloIco = m || !!dec;   // la decisión: «Aprobar» en texto y «Abrir la decisión» en icono, para que quepa en una fila
  const ir = x.ir ? h('a', { class: `bt mini${dec ? '' : ' pri'}${soloIco ? ' icono' : ''}`, href: x.ir, title: `${verboTxt} · abre esto mismo, no la pantalla entera`, 'aria-label': soloIco ? verboTxt : null }, soloIco ? null : verboTxt, icono('derecha'))
    : x.href ? h('a', { class: `bt mini pri${m ? ' icono' : ''}`, href: x.href, target: '_blank', rel: 'noopener', title: verboTxt, 'aria-label': m ? verboTxt : null }, m ? null : verboTxt, icono('ext')) : null;
  // Ronda U (50 #4): «Lo tengo» al primer clic, con «Deshacer» 8 s (antes «¿Te encargas tú? Sí»).
  const loTengo = puede && !dec && estado !== 'lo_tengo' ? botonDeshacer({ texto: m ? '' : 'Lo tengo', icono: m ? 'check' : null, hecho: 'Lo tienes tú', titulo: 'Lo tengo: me encargo yo (se puede deshacer 8 s)',
    alHacer: async () => { await marcar('alerta_lo_tengo'); return 'Lo tienes tú'; } }) : null;
  if (loTengo && m) loTengo.querySelector('button')?.setAttribute('aria-label', 'Lo tengo');
  // Ronda U (50 #3/#20): la decisión se aprueba en la propia fila («Aprobar» = la recomendación), con «Deshacer» 8 s.
  // Rechazar o delegar piden motivo: eso, en la decisión (el botón de al lado la abre sola, con su barra de acciones).
  const aprobar = dec && puedeDecidir(ctx, dec) ? botonDeshacer({ texto: 'Aprobar', pri: true, icono: 'check', hecho: 'Aprobada', soloLectura: ctx.soloLectura,
    titulo: `Aprobar la recomendación: ${L(dec.recomendacion || '')}`.slice(0, 300),
    alHacer: async () => {
      const M = await import('./decisiones.js');
      await M.contestarDecision(ctx, dec, 'Aprobar la recomendación', null);
      (lm.contestadas ||= new Set()).add(String(dec.id));
      if (a) lm.local.set(a.id, { estado: 'resuelta', hasta: null });
      setTimeout(repintar, 400);
      return 'Aprobada · queda en el rastro';
    } }) : null;
  const que = L(x.que);
  const porque = L([x.quien, x.porque].filter(Boolean).join(' · '));
  return {
    estado: tramo === 0 || x.grav === 'alta' ? 'rojo' : x.grav === 'baja' ? 'gris' : 'ambar',
    icono: x.icono && x.tipo === 'bloque' ? x.icono : ICONO_TIPO[x.tipo] || 'zap',
    motivo: que, titulo: [que, motivoPrioridad(x)].filter(Boolean).join(' · '),
    porque, chip: chips[0],
    // en el móvil la decisión lleva solo «Aprobar» y «Abrir» (posponer, dentro de la decisión): nunca más botones que texto
    botones: [aprobar, ir, loTengo, puede && !(m && aprobar) ? botonPosponer(hasta => marcar('alerta_posponer', hasta), true) : null],
  };
}

/** ¿Puede contestar esta decisión quien mira? (dirección las de Tomás; proyectos las de Coti; nunca en «ver como»). */
function puedeDecidir(ctx, d) {
  const p = ctx.persona.puestos || [];
  return !ctx.soloLectura && !d.respondida && !d.respuesta && ((p.includes('direccion') && d.tipo !== 'para_coti') || (p.includes('proyectos') && d.tipo === 'para_coti'));
}

/** «Posponer» → Mañana · El lunes (a las 9:00), como en Alertas. Vuelve sola en su fecha; mientras, no cuenta ni escala. */
function botonPosponer(alElegir, soloIcono = false) {
  const caja = h('span', { class: 'confirmar' });
  const dos = n => String(n).padStart(2, '0');
  const texto = d => `${d.getFullYear()}-${dos(d.getMonth() + 1)}-${dos(d.getDate())} ${dos(d.getHours())}:${dos(d.getMinutes())}`;
  const vuelta = cuando => { const d = new Date(); d.setSeconds(0, 0); if (cuando === 'manana') d.setDate(d.getDate() + 1); else d.setDate(d.getDate() + (((8 - d.getDay()) % 7) || 7)); d.setHours(9, 0); return d; };
  // en el móvil, solo el reloj (con su nombre para lectores de pantalla): la fila cabe en una línea de botones
  const inicial = () => caja.replaceChildren(h('button', { type: 'button', class: soloIcono ? 'bt mini icono' : 'bt mini', title: 'Posponer: vuelve sola mañana o el lunes', 'aria-label': 'Posponer', on: { click: elegir } }, icono('clock'), soloIcono ? null : 'Posponer'));
  function elegir() {
    const op = (cuando, et) => h('button', { type: 'button', class: 'bt mini', on: { click: async ev => {
      ev.currentTarget.disabled = true;
      try { await alElegir({ hasta: texto(vuelta(cuando)), cuando }); caja.replaceChildren(h('span', { class: 'estado', role: 'status' }, '✓ Pospuesta')); }
      catch (e) { caja.replaceChildren(h('span', { class: 'estado error', role: 'alert' }, `No se pudo: ${e?.message || e}`)); setTimeout(inicial, 2500); }
    } } }, et);
    caja.replaceChildren(op('manana', 'Mañana'), op('lunes', 'El lunes'), h('button', { type: 'button', class: 'bt mini', on: { click: inicial } }, 'Cancelar'));
  }
  inicial();
  return caja;
}

/** Móvil: lo que no cabe en las 7 piezas a la vista, plegado (se abre con un toque y se recuerda en esta visita). */
function masDeTuDia(piezas) {
  const det = h('details', { class: 'que-es', 'data-mas-de-tu-dia': '' },
    h('summary', { class: 'bt', style: { width: '100%', justifyContent: 'center' } }, `Más de tu día · ${fmt.plural(piezas.length, 'bloque', 'bloques')}`),
    h('div', { style: { ...REJILLA(420), marginTop: 'var(--s-4)' } }, sinHuerfana(piezas)));
  return det;
}

/** El consejo de la IA («Qué haría yo hoy aquí») lo pone la carcasa arriba de cada pantalla. En Mi día va DEBAJO de
 *  «Lo mío» y sin las filas que ya están en «Lo mío» (mismo objeto o misma alerta); si no queda ninguna, se oculta (se
 *  queda en el DOM, oculto, para que la carcasa no lo vuelva a poner).
 *  V2: (1) con varios puestos, solo los consejos de ESTA pestaña (por adónde llevan: SEO, web, redes, publicidad, CRM…);
 *  (2) nada de trabajo ajeno: se queda lo que es «Tú» o de tu gente directa (en dirección, solo lo tuyo: lo de tu equipo ya
 *  está en sus pantallas); (3) «Imputa las horas» nunca va primero: si hay otro consejo, se quita (sigue en «Lo mío» como
 *  aviso a tu nombre). */
const DEP_DE_RUTA = [[/^seo-web\/webs\//, 'web'], [/^seo-web/, 'seo'], [/^redes/, 'redes'], [/^captacion/, 'publicidad'], [/^salud-crm/, 'crm'],
  [/^clientes-nuevos/, 'altas'], [/^(bandeja|ficha|informe|reuniones)/, 'accounts'], [/^finanzas/, 'administracion'], [/^(personas|horas)/, 'rrhh'], [/^decisiones/, 'direccion']];
function filtroConsejo(ctx, puesto) {
  const varios = (ctx.persona.puestos || []).length > 1;
  const deps = varios ? (CONFIG.comun?.lo_mio_departamentos || {})[puesto] : null;
  const yoAlias = ctx.persona.alias;
  const directos = new Set((ctx.datos.personas || []).filter(q => q.jefe === ctx.persona.id).map(q => q.alias));
  const direccion = (ctx.persona.puestos || []).includes('direccion');
  return li => {
    const ir = objetoDe(li.querySelector('a[data-ir]')?.getAttribute('href') || '') || '';
    const quien = (li.querySelector('.pie > span')?.textContent || '').trim();
    if (deps && ir) { const d = (DEP_DE_RUTA.find(([re]) => re.test(ir)) || [])[1]; if (d && !deps.includes(d)) return false; }
    if (quien && quien !== 'Tú' && quien !== yoAlias && quien !== '—' && (direccion || !directos.has(quien))) return false;
    return true;
  };
}
function vigilarConsejo(main, loMio, despuesDe, { ctx = null, puesto = null } = {}) {
  const deEstePuesto = ctx ? filtroConsejo(ctx, puesto) : () => true;
  // La carcasa añade su consejo a #main, fuera de la raíz aislada del módulo.
  const alcance = main.closest?.('#main') || main;
  const arreglar = () => {
    if (!loMio.isConnected || (ctx?.vigente && !ctx.vigente())) { obs.disconnect(); return; }
    const c = alcance.querySelector(':scope > [data-ia="consejo"]');
    if (!c) return;
    const objetos = new Set([...loMio.querySelectorAll('[data-objeto]')].map(x => x.dataset.objeto));
    const items = [...c.querySelectorAll('li.ia-accion')];
    const vale = li => { const ir = li.querySelector('a[data-ir]')?.getAttribute('href'); return !(ir && objetos.has(objetoDe(ir))) && deEstePuesto(li); };
    const esHoras = li => /^horas\b/.test(objetoDe(li.querySelector('a[data-ir]')?.getAttribute('href') || '') || '');
    const otros = items.filter(li => vale(li) && !esHoras(li)).length;
    let quedan = 0;
    for (const li of items) {
      const fuera = !vale(li) || (esHoras(li) && otros > 0);
      li.hidden = fuera;
      if (!fuera) li.querySelector('.n').textContent = String(++quedan);
    }
    const primera = items.find(li => !li.hidden)?.querySelector('b')?.textContent;
    const res = c.querySelector(':scope > .ia-sub');
    if (res && primera) res.replaceChildren(h('b', {}, primera), quedan > 1 ? ` · y ${quedan - 1} más` : '');
    const ocultar = !quedan;
    if (c.hidden !== ocultar) c.hidden = ocultar;
    // Ronda U (molde): el consejo nunca empuja la lista: va debajo de «Lo mío» y plegado a una línea (una vez: si la persona
    // lo abre, se queda abierto)
    if (!c.dataset.plegadoU) { c.dataset.plegadoU = '1'; plegarConsejo(c); }
    // Sigue como hijo directo de #main: la carcasa no debe recrear un segundo consejo.
    let ancla = despuesDe;
    while (ancla.parentElement && ancla.parentElement !== alcance) ancla = ancla.parentElement;
    if (ancla.isConnected && (ancla.compareDocumentPosition(c) & Node.DOCUMENT_POSITION_PRECEDING)) ancla.after(c);
  };
  let pend = null;
  const obs = new MutationObserver(() => { clearTimeout(pend); pend = setTimeout(arreglar, 30); });
  obs.observe(alcance, { childList: true });
  obs.observe(loMio, { childList: true });   // al marcar algo en «Lo mío», el consejo se vuelve a filtrar con sus filas nuevas
  arreglar();
}

/** Verbo + objeto según adónde lleva (guía 30, 3.13): nunca un «Ir» suelto. */
function verbo(ruta) {
  if (/^finanzas\/cobros\/./.test(String(ruta || ''))) return 'Abrir el cobro';   // Ronda U (50 #5): mismo verbo que su alerta
  if (/^decisiones\/reloj\/./.test(String(ruta || ''))) return 'Abrir la decisión';
  const m = String(ruta || '').split('/')[0];
  return ({ bandeja: 'Abrir correo', produccion: 'Abrir tarea', incidencias: 'Abrir incidencia', ficha: 'Abrir cliente', 'en-rojo': 'Abrir cliente',
    'clientes-nuevos': 'Abrir alta', captacion: 'Abrir cuenta', 'salud-crm': 'Abrir subcuenta', 'seo-web': 'Abrir web', redes: 'Abrir redes',
    decisiones: 'Abrir decisión', alertas: 'Abrir alerta', prospeccion: 'Abrir respuestas', finanzas: 'Abrir finanzas', personas: 'Abrir persona', ajustes: 'Abrir aviso', horas: 'Abrir horas', 'chat-equipo': 'Abrir mensaje' })[m] || 'Abrir';
}
// ================================================================== A10 · tu primera semana (R15a)
/** Tarjeta «Tu primera semana · N de 5» con el siguiente paso y el enlace a #/primera-semana. Solo para altas de menos de
 *  14 días (o «por incorporar»); el resto no paga nada: la comprobación es local y el módulo se carga solo si hace falta. */
async function tarjetaPrimeraSemana(ctx) {
  const p = (ctx.datos.personas || []).find(x => x.id === ctx.persona.id) || ctx.persona;
  const reciente = p?.estado === 'por_incorporar' || (p?.fecha_ingreso && (Date.now() - Date.parse(String(p.fecha_ingreso).slice(0, 10))) / 864e5 < 15);
  if (!reciente || !ctx.veModulo('primera-semana')) return null;
  const PS = await import('./primera_semana.js');
  const nueva = PS.altaNueva(p);
  if (!nueva) return null;
  const [hechos, G] = await Promise.all([PS.pasosHechos(ctx, p.id), ctx.datosModulo('primera_semana/guias').catch(() => null)]);
  const pasos = G?.pasos || [];
  const total = pasos.length || 5;
  const n = [...hechos].filter(x => !pasos.length || pasos.some(y => y.n === x)).length;
  const sig = pasos.find(x => !hechos.has(x.n));
  return panel({ titulo: `Tu primera semana · ${n} de ${total}`, icono: 'rocket', id: 'mid-primera-t',
    sub: nueva.por_incorporar ? 'Por incorporar: lo primero que harás en la app' : `Día ${nueva.dias + 1} de ${PS.DIAS_VENTANA} · cinco pasos para empezar con buen pie`,
    verTodo: { texto: 'Abrir tu primera semana', href: `#/${PS.ID}` } },
  h('div', { class: 'cuerpo pila' },
    barraProgreso({ valor: n, max: total, estado: n >= total ? 'verde' : null, etiqueta: `${n} de ${total} pasos hechos` }),
    sig ? h('p', { style: { margin: 0 } }, h('b', {}, `Siguiente: ${L(sig.texto)}`), sig.detalle ? h('span', { class: 'sub', style: { display: 'block' } }, L(sig.detalle)) : null)
      : vacioLinea('Los cinco pasos, hechos. Bienvenida al equipo.', { icono: 'ok' })));
}

// ================================================================== cumpleaños y aniversarios (todo el equipo)
function panelCelebraciones(ctx) {
  const l = typeof ctx.celebraciones === 'function' ? ctx.celebraciones({ dias: 14 }) : [];
  if (!l.length) return null;
  const cuando = c => (c.en_dias === 0 ? 'hoy' : c.en_dias === 1 ? 'mañana' : (() => { const d = new Date(`${c.fecha}T12:00`); return `el ${PALABRAS_DIA[d.getDay()]} ${d.getDate()} de ${MESES[d.getMonth()]}`; })());
  const filas = l.slice(0, 5).map(c => h('li', {},
    h('span', { class: `ico-c s ${c.en_dias === 0 ? 'verde' : 'gris'}` }, icono(c.tipo === 'cumple' ? 'heart' : 'crown')),
    h('span', { class: 't', style: TEXTO_FILA }, c.tipo === 'cumple'
      ? `${c.alias} cumple años ${cuando(c)}`
      : `${c.alias} cumple ${c.anios} año${c.anios === 1 ? '' : 's'} en RO ${cuando(c)}`),
    c.en_dias === 0 ? chipEstado('verde', 'Hoy') : null));
  return panel({ titulo: 'Cumpleaños y aniversarios', icono: 'heart', sub: 'Del equipo, en las próximas dos semanas · lo ve todo el equipo', id: 'mid-cel-t' },
    h('div', { class: 'cuerpo' }, h('ul', { class: 'lista-i' }, filas),
      l.length > 5 ? h('p', { class: 'sub' }, `y ${fmt.plural(l.length - 5, 'celebración', 'celebraciones')} más en las próximas dos semanas`) : null));
}

// ================================================================== bloques
/** Nombre de la herramienta de origen a partir del enlace (para «Abrir en …»). */
function origenUrl(u) {
  const t = [['desk.zoho', 'Desk'], ['clickup.com', 'ClickUp'], ['gohighlevel.com', 'GoHighLevel'], ['facebook.com', 'Meta'], ['holded.com', 'Holded'], ['metricool', 'Metricool'], ['zoom.us', 'Zoom'], ['instagram.com', 'Instagram']];
  return (t.find(([k]) => String(u).includes(k)) || [])[1] || null;
}
function filaBloque(f) {
  const ext = f.href && /^https?:/.test(f.href);
  const texto = f.href ? h('a', { href: f.href, target: ext ? '_blank' : null, rel: ext ? 'noopener' : null, style: { textDecoration: 'none' } }, L(f.texto)) : h('span', {}, L(f.texto));
  const donde = f.abrir?.href ? origenUrl(f.abrir.href) || f.abrir.texto : null;
  const abrir = f.abrir?.href ? h('a', { class: 'bt icono mini', href: f.abrir.href, target: '_blank', rel: 'noopener', title: `Abrir en ${donde}`, 'aria-label': `Abrir en ${donde}` }, icono('ext')) : null;
  // Ronda U (50 #5): la fila con verbo lleva su botón («Abrir el cobro»), al MISMO sitio que su fila de «Lo mío»
  const verboBt = f.verbo && f.href && !ext ? h('a', { class: 'bt mini', href: f.href }, f.verbo, icono('derecha', { clase: 's' })) : null;
  return h('li', {},
    h('span', { class: `ico-c s ${f.estado || 'gris'}` }, icono(f.icono || 'doc')),
    h('span', { class: 't', style: TEXTO_FILA }, texto, f.extra ? h('span', { class: 'sub' }, L(f.extra)) : null),
    verboBt || abrir || (ext ? icono('ext') : null), verboBt ? abrir : null);
}
const listaFilas = l => h('ul', { class: 'lista-i' }, l.map(filaBloque));

/** V2 (B2): «1 cambios bruscos» → «1 cambio brusco». Con la cifra 1, el primer tramo de la unidad (hasta « · » o « de »)
 *  pasa a singular con una tabla corta de las unidades de los bloques. */
const SINGULAR = [['cambios bruscos', 'cambio brusco'], ['circuitos rotos', 'circuito roto'], ['firmados sin alta', 'firmado sin alta'], ['registros', 'registro'],
  ['accesos que faltan', 'acceso que falta'], ['talleres', 'taller'], ['ausencias registradas', 'ausencia registrada'], ['movimientos', 'movimiento'],
  ['subcuentas', 'subcuenta'], ['decisiones', 'decisión'], ['arranques', 'arranque'], ['fuegos', 'fuego'], ['nichos', 'nicho'], ['revisiones', 'revisión'],
  ['tareas abiertas', 'tarea abierta'], ['traffickers', 'trafficker'], ['especialistas', 'especialista'], ['altas', 'alta'], ['clientes', 'cliente'],
  ['cuentas', 'cuenta'], ['leads', 'lead'], ['citas', 'cita'], ['webs', 'web'], ['correos', 'correo'], ['incidencias', 'incidencia'], ['personas', 'persona'],
  ['palabras', 'palabra'], ['mensajes fallidos', 'mensaje fallido'], ['borradores', 'borrador'], ['fallidas', 'fallida'], ['impagos', 'impago'],
  ['plazas', 'plaza'], ['piezas', 'pieza'], ['respuestas', 'respuesta'], ['positivas', 'positiva'], ['activas', 'activa'], ['contratos', 'contrato'],
  ['reuniones', 'reunión'], ['huecos', 'hueco'], ['bloqueadas', 'bloqueada'], ['devueltas', 'devuelta'], ['caídas', 'caída'], ['certificados caducan', 'certificado caduca'],
  ['lentas', 'lenta'], ['casillas', 'casilla'], ['marcadas', 'marcada'], ['vencidas', 'vencida'], ['tareas', 'tarea']];
function unidadDe(valor, unidad) {
  if (typeof unidad !== 'string' || !unidad || !(valor === 1 || valor === '1')) return unidad;
  const corte = unidad.search(/ · | de /);
  let cab = corte < 0 ? unidad : unidad.slice(0, corte);
  const resto = corte < 0 ? '' : unidad.slice(corte);
  for (const [pl, sg] of SINGULAR) cab = cab.replace(new RegExp(`(^|\\s)${pl}(?=\\s|$)`), `$1${sg}`);
  return cab + resto;
}
function tarjetaBloque(ctx, b) {
  const r = b.r;
  const max = CONFIG.comun?.max_filas || 5;
  const id = `mid-b-${b.id}-${b.orden}`;
  const cuerpo = [];
  const estado = r.estado || '';
  if (r.valor !== null && r.valor !== undefined && !r.falta && !r.pendiente) {
    cuerpo.push(h('p', { class: 'lead' }, chipEstado(estado === '' ? 'azul' : estado, String(r.valor), { punto: estado !== '' }), r.unidad ? ` ${L(unidadDe(r.valor, r.unidad))}` : null));
  }
  if (r.motivo) cuerpo.push(h('p', { class: 'sub', style: CORTA, title: L(r.motivo) }, L(r.motivo)));
  if (r.extra) cuerpo.push(h('div', {}, r.extra));
  if (r.ronda) cuerpo.push(ronda(ctx, r.ronda, max));
  if (r.mapa) cuerpo.push(mapaControl(r.mapa, max));
  if (r.tarjetas?.length) cuerpo.push(h('div', { class: 'rejilla' }, r.tarjetas), r.mas ? masEn(r.mas, objetoBloque(b, r), b.ruta ? nombreRuta(b.ruta) : 'el detalle', b.ruta) : null);
  if (r.pistas) cuerpo.push(pistas(r.pistas), r.mas ? masEn(r.mas, ['alta', 'altas'], 'Clientes nuevos', 'clientes-nuevos') : null);
  if (r.barras) cuerpo.push(h('div', { class: 'embudo-barras' }, r.barras.map(x => h('div', { class: 'et' }, h('span', {}, x.etiqueta),
    barraProgreso({ valor: x.valor, max: x.max, estado: x.valor > x.max ? 'rojo' : x.valor >= x.max * 0.875 ? 'ambar' : 'verde', marca: x.marca ?? null, etiqueta: `${x.etiqueta}: ${x.valor} de ${x.max}` }),
    h('span', { class: 'n' }, `${fmt.num(x.valor)}/${fmt.num(x.max)}`)))));
  const filas = r.filas || [];
  if (filas.length) {
    cuerpo.push(listaFilas(filas.slice(0, max)));
    if (filas.length > max) {
      if (r.plegar) cuerpo.push(h('details', { class: 'que-es' }, h('summary', {}, `Ver ${filas.length - max} más`), listaFilas(filas.slice(max))));
      else cuerpo.push(masEn(filas.length - max, objetoBloque(b, r), nombreRuta(b.ruta), b.ruta));
    }
  } else if (r.vacio && !r.ronda && !r.mapa && !r.tarjetas?.length && !r.pistas?.length && !r.barras?.length && !r.extra) {
    cuerpo.push(vacioLinea([h('b', {}, L(r.vacio.titulo)), r.vacio.texto ? ` · ${L(r.vacio.texto)}` : null], { icono: r.vacio.icono || (r.vacio.tono === 'celebrar' ? 'ok' : r.pendiente ? 'hist' : 'info'), quien: L(r.vacio.quien) }));
  } else if (r.tarjetas && !r.tarjetas.length && r.vacio) {
    cuerpo.push(vacioLinea([h('b', {}, L(r.vacio.titulo)), r.vacio.texto ? ` · ${L(r.vacio.texto)}` : null], { icono: 'cli', quien: L(r.vacio.quien) }));
  }
  const ver = b.ruta && ctx.veModulo(b.ruta.split('/')[0]) ? { texto: `Abrir ${nombreRuta(b.ruta)}`, href: `#/${b.ruta}` } : null;
  const sec = panel({ titulo: b.titulo, icono: b.icono || 'res', id: `${id}-t`, sub: b.frecuencia || null,
    acciones: r.medible && r.medible !== 'hoy' ? selloMedible(r.medible, r.medibleDetalle) : null,
    pie: r.frescura ? (Array.isArray(r.frescura) ? h('span', { class: 'fila', style: { gap: 'var(--s-2)' } }, r.frescura.map(f => frescura(f))) : frescura(r.frescura)) : null, verTodo: ver },
  h('div', { class: 'cuerpo pila' }, cuerpo));
  sec.id = id; sec.tabIndex = -1;
  sec.querySelector(':scope > .panel-pie')?.style.setProperty('flex-wrap', 'wrap');   // D5: en el móvil el botón baja de línea, no se sale
  return sec;
}
const nombreRuta = r => nombreModulo(String(r || '').split('/')[0]);
/** V3b / Ronda U: «y 3 impagos más en Finanzas» (con el objeto y, si la pantalla se ve, como enlace), nunca «y 3 más en su pantalla». */
function objetoBloque(b, r) {
  if(b.id==='reuniones_ciclo')return ['caso de seguimiento','casos de seguimiento'];
  if(b.id==='nuevos_resumen')return ['alta','altas'];
  const u = typeof r.unidad === 'string' && r.unidad ? r.unidad.split(/ · | de |, /)[0].trim() : '';
  const pl = /^(\d|—)/.test(u) || !u ? String(b.titulo || 'cosas').replace(/^./, c => c.toLowerCase()) : u;
  return [unidadDe(1, pl), pl];
}
function masEn(n, [sg, pl], donde, ruta) {
  const texto = `y ${fmt.num(n)} ${n === 1 ? sg : pl} más en ${donde}`;
  return h('p', { class: 'sub' }, ruta && !/^el detalle$/.test(donde) ? h('a', { href: `#/${ruta}` }, texto) : texto);
}

function ronda(ctx, { items, hechas, hoy }, max) {
  const fila = x => {
    const hecha = hechas.has(x.id);
    return h('li', {},
      h('span', { class: `ico-c s ${hecha ? 'verde' : 'gris'}` }, icono(hecha ? 'ok' : 'check')),
      h('span', { class: `t${hecha ? ' dim' : ''}`, style: TEXTO_FILA }, h('span', {}, x.que), x.referencia547 ? h('details', { class: 'que-es' }, h('summary', {}, 'Referencia histórica'), h('p', {}, x.referencia547), h('p', { class: 'sub' }, 'Regla anterior: no acredita jornada vigente ni incumplimiento.')) : null, h('span', { class: 'sub' }, [x.f, x.prueba ? `prueba: ${x.prueba}` : null].filter(Boolean).join(" · "))),
      // Ronda U (50 #4): «Hecho» al primer clic, con «Deshacer» 8 s (antes «¿Hecho? Sí»)
      hecha ? chipEstado('verde', 'Hecho') : botonDeshacer({ texto: 'Hecho', hecho: 'Hecho', soloLectura: ctx.soloLectura, atajo: 'e',
        alHacer: async () => { await ctx.accion({ herramienta: 'app', tipo: 'ronda', objeto: `${hoy}:${x.id}`, texto: x.que, vista_previa: { que: 'Marca este punto de la ronda como hecho hoy' } }); hechas.add(x.id); return 'Hecho · queda en el rastro'; } }));
  };
  const pend = items.filter(x => !hechas.has(x.id));
  const orden = [...pend, ...items.filter(x => hechas.has(x.id))];
  return h('div', {}, h('ul', { class: 'lista-i' }, orden.slice(0, max).map(fila)),
    orden.length > max ? h('details', { class: 'que-es' }, h('summary', {}, `${orden.length - max} puntos más de la ronda`), h('ul', { class: 'lista-i' }, orden.slice(max).map(fila))) : null);
}

/** Mapa de control por persona (de Incidencias): tabla densa común, el estado en un chip por celda. */
function mapaControl(filas, max) {
  const c=(x,key)=>{const d=celdaControlEquipo313(x,key),texto=d.valor===null?'—':`${fmt.num(d.valor,key==='imputa'?1:0)}${key==='imputa'?' h':''}${d.tipo==='referencia'?' ref.':''}`;return h('td',{class:'num',title:d.detalle},chipEstado('gris',texto));};
  return h('div', {}, h('div', { class: 'tabla-scroll' }, h('table', { class: 'densa' },
    h('thead', {}, h('tr', {}, h('th', { scope: 'col' }, 'Persona'), h('th', { scope: 'col', title: 'Registros del último día lunes–viernes de la copia; no evalúa calendario o jornada' }, 'Imputa'),
      h('th', { scope: 'col', title: 'Referencia de revisiones+48h' }, 'Revisa'), h('th', { scope: 'col', title: 'Referencia de correos+48h' }, 'Contesta'),
      h('th', { scope: 'col', title: 'Referencia mensual antigua, no celebración verificada' }, 'Reunión'), h('th', { scope: 'col', title: 'Referencia semanal antigua, no contacto verificado' }, 'Correo'))),
    h('tbody', {}, filas.slice(0, max).map(x => h('tr', {},h('th', { scope: 'row' }, x.nombre),c(x,'imputa'),c(x,'revisa'),c(x,'contesta'),c(x,'reunion'),c(x,'correo')))))),
    h('p',{class:'sub'},'Horas: registros parciales o referencia marcada; sin dato no es cero. Las demás cifras son referencias sin cobertura completa: no acreditan incumplimiento.'),
    filas.length > max ? h('p', { class: 'sub' }, `y ${fmt.plural(filas.length - max, 'persona', 'personas')} más en el mapa de Incidencias`) : null);
}

/** Altas en su pista de 90 días: barra común con la marca del día 10 (encendido; límite el 12). */
function pistas(l) {
  return h('ul', { class: 'lista-i' }, l.map(a => h('li', {},
    h('span', { class: `ico-c s ${a.estado || 'gris'}` }, icono('rocket')),
    h('span', { class: 't', style: TEXTO_FILA },
      h('a', { href: a.href, style: { textDecoration: 'none' } }, a.nombre), h('span', { class: 'sub' }, `día ${a.dia} · ${a.sig || 'sin hito'}`),
      barraProgreso({ valor: Math.min(a.dia, 90), max: 90, estado: a.estado || null, marca: 10, etiqueta: `Día ${a.dia} de 90; la campaña se enciende el día 10 (límite, el 12)` })))));
}

function pie(ctx, puesto) {
  const ind = (ctx.indicadores() || []).filter(i => i.puesto === puesto);
  return h('footer', { class: 'pila' },
    pieFase2(ind),
    h('p', { class: 'sub' }, icono('info'),
      ` Mi día no calcula nada: cada cifra viene de su pantalla, ya recortada para ${ctx.persona.alias}. Pulsa una fila para abrir esa cosa concreta.`),
    ctx.persona.puestos.includes('direccion') ? deDondeSale('Qué bloques salen y en qué orden lo decide la tabla de cada puesto (fichas de indicadores). Los cambios desde ayer y la ronda de Mili se calculan cada mañana y con «Actualizar ahora». Los correos sin contestar siguen la regla de la Bandeja (días laborables). Las alertas son las de tu departamento.') : null);
}

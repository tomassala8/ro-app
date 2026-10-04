import {cargarObjetivos374,celdaObjetivo374,renderObjetivos374} from './_objetivos_seo_374.js';
import {notaCompacta336} from './_nota_compacta_336.js';
import { normalizarAlertasSEO, parPosicionSEO, posicionSEO, conteoSEO, cambioPosicionSEO, filasSeoAutorizadas, contextoMotoresSEO, configuracionActualMotoresSEO, paginasSEO, resumenClicsCarteraSEO } from './_seo_mediciones.js';
import { oportunidadPagina332, ambitoOportunidades332 } from './_seo_oportunidades_332.js';
import { panelSeo, panelWeb } from './_panel_especialista.js';
// modulos/seo.js · M8 «SEO, ficha de Google y webs» (E8 del plan v2; fichas G3-1 a G3-4).
//
// Qué pinta (arriba lo de cada día, abajo lo de cada semana o mes):
//   #/seo-web                 → cifras con el número que manda de cada puesto + aviso de calidad del dato, y tres pestañas:
//                               SEO (lo primero hoy, semáforo de la cartera, su célula) · Webs (monitor desde la IP de RO,
//                               avisos de medición, velocidad) · Ficha de Google (se conecta; lo que ya da SE Ranking en Maps).
//   #/seo-web/<cliente>       → detalle de SEO de un cliente: las 15 palabras del informe, las que suben y bajan, clics e
//                               impresiones de Search Console con su serie, páginas, búsquedas, Analytics, su web y botones.
//
// Datos: data/seo/seo.json (filas con cliente_id → servir.py solo manda los clientes que la persona ve) y data/seo/webs.json
// (filas con «cliente», sin cliente_id: el estado de TODAS las webs lo ve todo el que ve el módulo, para cubrir guardias, G3-4).
// Los genera fuentes_seo/generar_seo.py (SE Ranking por el conector + Search Console + monitor + E1). Solo lectura.
// Botones: ctx.accion() → cola local «simulada» con vista previa. Nunca llama a SE Ranking, Google ni WordPress.
// Modular DS (N5): data/modular/webs.json (fuentes_modular/generar_modular.py, FORMATO.md). Complementa al monitor propio:
// copias, actualizaciones, seguridad y si la web responde desde fuera. Sin clave → «Modular sin conectar» y nunca un verde.
// Diseño (auditoría 30): sin hoja de estilos propia; clases comunes y tokens de la guía; cifras con punto de miles; nada < 12 px.
// N6 (2-oct noche): portada en pestañas por fuente (Posiciones · Ficha de Google · Webs) y detalle en pestañas (Posiciones ·
// Clics de Google · Web y ficha); tablas de 15 filas + «Ver más»; lo que no se mide y cómo se comprueba, plegado al pie.
// Periodo: no usa el común. Las cifras son ventanas fijas que da la fuente (posiciones de hoy frente a hace 7 y 30 días;
// clics de 7 y 28 días cerrados hasta el último día de Search Console) y así se dice junto a cada cifra.

import {
  h, fmt, semaforo, tile, listaLoPrimero, tablaDensa, chipEstado, chipsFiltro, selectorCliente, vacio, botonConfirmar,
  avisoParcial, logoCliente, panel, frescura, icono, iniciales, pestanas, grafico, variacion, rejillaTarjetas, vacioLinea,
  ventanas,
} from '../componentes.js';
import { llevarA, filaConTexto } from './_ir.js';
import { franjaCifras, pantallaTrabajo, barraAcciones } from './_trabajo.js';
import { pantallaAncha, franjaEnLinea } from './_trabajo_ancho.js';
import { botonDeshacer } from './_deshacer.js';
import { cargarTablero, revisadas, accionesWeb, estadoWeb, botonAbrirModular, botonEntrar, botonCrearTarea, botonAvisarAccount, fDiaHora as fMod } from './_modular.js';
import { pestanaFichaGoogle, bloqueFichaGoogle } from './_gbp_bloques.js';   // 3-oct · ficha de Google (Business Profile)

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

const JEFAS = ['direccion', 'finanzas_direccion', 'operaciones', 'proyectos', 'jefa_seo'];
const EST = { rojo: 0, ambar: 1, gris: 2, verde: 3 };
const TXT_EST = { rojo: 'Actuar', ambar: 'Vigilar', verde: 'Señal anterior favorable', gris: 'Sin dato' };
// números: siempre con el formateador común (punto de miles, coma decimal, signo «−»)
const num = n => fmt.num(n);
const numD = (n, d = 1) => fmt.num(n, d);
const pctTxt = n => (n === null || n === undefined ? '—' : `${n > 0 ? '+' : ''}${numD(n, Math.abs(n) < 10 ? 1 : 0)} %`);
const pos = n => (n ? String(n) : '—');
// tokens de la guía con su valor de hoy (mandan los de estilos.css cuando E0 los dé de alta)
const S = { 1: 'var(--s-1)', 2: 'var(--s-2)', 3: 'var(--s-3)', 4: 'var(--s-4)', 5: 'var(--s-5)' };
const PUNTO = { verde: 'var(--good)', ambar: 'var(--warn)', rojo: 'var(--bad)', gris: 'var(--off)' };
/** Estado de una celda: punto de 8 px + texto en tinta (guía 3.8), en vez de una pastilla en cada fila. */
const estadoTexto = (estado, texto, titulo) => h('span', { class: 'fila', title: titulo || null, style: { gap: S[2], flexWrap: 'nowrap', color: 'var(--ink)', whiteSpace: 'nowrap' } },
  h('span', { 'aria-hidden': 'true', style: { width: '8px', height: '8px', borderRadius: '50%', background: PUNTO[estado] || PUNTO.gris, flex: 'none', display: 'inline-block' } }), texto);
/** ▲ / ▼ en verde o rojo (texto de 12 px, 600). */
const delta = (bien, texto) => h('span', { style: { fontWeight: '600', color: bien ? 'var(--good-ink)' : 'var(--bad-ink)', whiteSpace: 'nowrap' } }, texto);
/** Una acción principal + «⋯» con el resto (details + .menu-flot comunes): nunca 3 botones en dos filas en el móvil. */
const masAcciones = (principal, ...resto) => {
  resto = resto.filter(Boolean);
  if (!resto.length) return [principal];
  return [principal, h('details', { style: { position: 'relative', display: 'flex' } },
    h('summary', { class: 'bt mini', 'aria-label': 'Más acciones', title: 'Más acciones', style: { listStyle: 'none', cursor: 'pointer', minWidth: '36px', justifyContent: 'center', flex: '1' } }, '⋯'),
    h('div', { class: 'menu-flot', role: 'menu', style: { left: 'auto', right: '0', minWidth: '200px' } }, resto))];
};
/** Rojo con cuentagotas (guía 3.4): en una lista, rojo solo el tercio de arriba (lo más urgente va primero); el resto, ámbar. */
const cuentagotas = (estado, i, n) => (estado === 'rojo' && i >= Math.max(1, Math.ceil(n / 3)) ? 'ambar' : estado);
/** Dos columnas: la clase común .dos, que desde la ronda 10 se apila de verdad en el móvil (R13: sin rejilla en línea). */
const dos = (...hijos) => h('div', { class: 'dos' }, ...hijos);
/** Explicaciones y «todavía no», plegadas al pie (guía 3.6). items: [[negrita, texto]] o nodos. */
const piePlegado = (titulo, items) => h('details', { class: 'pie-fase2' }, h('summary', {}, titulo),
  h('ul', {}, items.map(it => (Array.isArray(it) ? h('li', {}, h('b', {}, it[0]), ` · ${it[1]}`) : h('li', {}, it)))));
/** Motivo de la fila en 2 líneas como mucho: se recorta a 70 caracteres y el texto completo va en la burbuja. */
const motivo2 = t => { const s = String(t || ''); return h('span', { class: 'sub', title: s.length > 72 ? s : null, style: { maxWidth: '320px' } }, s.length > 72 ? `${s.slice(0, 70).trimEnd()}…` : s); };
const MODULAR_PASO = 'Falta un paso de Tomás: en Modular DS, crear una clave de solo lectura (Mi perfil → API) y ejecutar pegar.sh. Después se ven las copias, las actualizaciones, la seguridad y si la web responde desde fuera.';

function posCh(n) {
  const valor=posicionSEO(n);
  return h('span',{class:'chip sin-punto gris',title:valor===null?'Posición sin observación válida; no prueba estar fuera del top 100':`Posición observada ${valor}; no acredita objetivo cumplido`,style:{minWidth:'36px',justifyContent:'center'}},valor===null?'Sin dato':String(valor));
}
function deltaPos(antes,hoy) {
  const d=cambioPosicionSEO(antes,hoy);
  if(d===null)return h('span',{class:'sub'},'Sin comparación');
  if(d===0)return h('span',{class:'sub'},'=');
  return delta(d>0,`${d>0?'▲':'▼'} ${Math.abs(d)}`);
}

const nom = (ctx, id, completo) => (id ? (ctx.nombre ? ctx.nombre(id) : id) : null);
function esJefa(ctx) { return ctx.persona.puestos.some(p => JEFAS.includes(p)); }
function rol(ctx) {
  const p = ctx.persona.puestos;
  if (esJefa(ctx)) return 'jefa';
  if (p.includes('seo') || p.includes('ficha_google')) return 'seo';
  if (p.includes('web')) return 'web';
  return 'otro';
}

// =================================================================== datos
async function cargar(ctx) {
  const [seo, webs, modular, tablero, rev, objetivos374] = await Promise.all([
    ctx.datosModulo('seo/seo').catch(e => ({ _error: e.message })),
    ctx.datosModulo('seo/webs').catch(e => ({ _error: e.message })),
    // Modular DS: si el fichero no llega (sin generar o sin alta en el servidor), se trata como «sin conectar»
    ctx.datosModulo('modular/webs').catch(e => ({ _meta: { estado: 'sin_conectar', motivo: e.message }, webs: [] })),
    // Tablero del equipo web (3-oct): todas las webs de Modular, solo para web, jefe de SEO y web, operaciones y dirección
    cargarTablero(ctx),
    revisadas(ctx),
    cargarObjetivos374(ctx),
  ]);
  seo.clientes=filasSeoAutorizadas(seo.clientes,ctx.clientesVisibles).map(f=>normalizarAlertasSEO(f,seo._meta,ctx.hoy));
  for (const f of seo.clientes || []) f.seo_quien = nom(ctx, f.seo_id) || 'Sin asignar';
  for (const w of webs.webs || []) w.web_quien = nom(ctx, w.web_id) || 'Sin asignar';
  // cruce web propia ↔ Modular: por cliente_id y, si no, por dominio (con o sin www)
  const conectado = modular?._meta?.estado === 'conectado';
  const dom = u => String(u || '').replace(/^https?:\/\//, '').replace(/^www\./, '').replace(/\/.*$/, '').toLowerCase();
  const porCli = new Map(), porDom = new Map();
  if (conectado) for (const m of modular.webs || []) { if (m.cliente_id) porCli.set(m.cliente_id, m); if (m.dominio || m.url) porDom.set(dom(m.dominio || m.url), m); }
  for (const w of webs.webs || []) w.modular = conectado ? (porCli.get(w.cliente) || porDom.get(dom(w.url)) || null) : undefined;
  return { seo, webs, modular: { conectado, meta: modular?._meta || {}, resumen: modular?.resumen || null },
    tablero: conectado && tablero?._meta?.estado === 'conectado' ? tablero : null, rev, objetivos374 };
}

// =================================================================== portada
function pintarPortada(cont, ctx, d, { webObjetivo = null } = {}) {
  const r = rol(ctx);
  const filas = (d.seo.clientes || []);
  const mias = filas.filter(f => f.seo_id === ctx.persona.id || ctx.carteraIds.has(f.cliente_id) && r === 'seo');
  const base = r === 'seo' ? mias : filas;
  const webs = d.webs.webs || [];
  const misWebs = webs.filter(w => w.web_id === ctx.persona.id);
  // Las alertas de esta vista se resuelven con pares fechados; el resumen legado no acredita objetivos.
  const R = d.seo.resumen || {};
  const medibles = base.filter(f => f.estado !== 'gris');
  const baseVerde = medibles.length;
  const metaS = d.seo._meta || {};
  const metaW = d.webs._meta || {};
  const fresSR = { fuente: 'SE Ranking', fecha: (metaS.seranking || {}).leido };
  const fresGSC = { fuente: 'Search Console', fecha: (metaS.gsc || {}).leido };
  const fresMon = { fuente: 'Monitor (IP de RO)', fecha: (metaW.monitor || {}).leido };
  // V2 · con SE Ranking en duda (resumen.aviso_seranking) el número que manda va «a medias» y en gris, con el motivo:
  // nunca un verde (ni un rojo) que se apoye en ese dato. La misma regla que seo.json › resumen.estado_mostrado.
  const enDuda = Boolean(R.aviso_seranking);

  ctx.titulo('SEO, ficha y webs', r === 'seo' ? `Tus ${mias.length} clientes de SEO · posiciones, clics y webs` : r === 'web' ? `Estado de ${webs.length} webs (todas, para cubrir guardias) · ${misWebs.length} a tu nombre` : `${filas.length} clientes con SEO · ${webs.length} webs vigiladas`);

  // ---------- 1 · cifras: el número que manda de cada puesto, primero
  const cohorteClics=resumenClicsCarteraSEO(base,metaS,ctx.hoy);
  const sumSem=cohorteClics.actual,sumAnt=cohorteClics.anterior;
  const fuera = base.reduce((a, f) => a + f.alertas.filter(x=>x.tipo==='fuera_top10'&&x.acreditada===true).length, 0);
  const desap = base.reduce((a, f) => a + ((f.visibilidad || {}).desaparecen || 0), 0);
  const conTop5=base.filter(f=>conteoSEO(f.reparto?.top5?.hoy)!==null);
  const top5h=conTop5.length?conTop5.reduce((a,f)=>a+f.reparto.top5.hoy,0):null;
  const top5m=conTop5.length&&conTop5.every(f=>conteoSEO(f.reparto.top5.mes)!==null)?conTop5.reduce((a,f)=>a+f.reparto.top5.mes,0):null;       // R12: solo palabras que SE Ranking ve hoy
  const top5sin = base.reduce((a, f) => a + (f.reparto?.top5.sin_ver_hoy || 0), 0);
  const websRojo = webs.filter(w => w.estado === 'rojo');
  const avisosMed = webs.reduce((a, w) => a + w.avisos.length, 0);
  const caidas = webs.filter(w => w.estado === 'rojo' && !(w.comprobacion?.estado >= 200 && w.comprobacion?.estado < 400));
  const responden = webs.filter(w => w.comprobacion?.estado >= 200 && w.comprobacion?.estado < 400).length;
  const t = [];
  if (r === 'web') {
    t.push(tile({ icono: 'mundo_web', etiqueta: 'Webs que responden', valor: responden, unidad: `de ${webs.length}`, estado: caidas.length ? 'rojo' : 'verde',
      contexto: 'Número que manda · una comprobación hoy', medible: 'medias', medibleDetalle: 'Una comprobación desde la IP de RO; la de cada 5 minutos y desde fuera llega con el despliegue', frescura: fresMon,
      ir: 'Ver las caídas', alPulsar: () => irPestana(cont, 'webs', 'caidas') }));
  } else if (r === 'seo') {
    t.push(tile({ icono: 'star', etiqueta: 'Palabras en el top 5', valor:top5h===null?null:num(top5h), unidad: 'de las 15 por cliente', estado:'gris',
      comparacion:top5h!==null&&top5m!==null?{delta:top5h-top5m,texto:'frente a hace 30 días'}:null, contexto:`Recuento observado de la muestra; comparación de 30 días sólo con pares acreditados${top5sin ? ` · ${num(top5sin)} que estaban arriba hoy no las ve (no cuentan como caída)` : ''}`, medible: enDuda ? 'medias' : 'hoy', medibleDetalle: enDuda ? R.motivo_medible : null, frescura: fresSR,
      ir: 'Ver por cliente', alPulsar: () => irPestana(cont, 'seo') }));
  }
  if (r !== 'web') {
    t.push(tile({ icono: 'medidor', etiqueta:'Clientes con alertas acreditadas',valor:base.filter(f=>f.alertas.some(a=>a.acreditada===true)).length,unidad:`de ${base.length} visibles`, estado:'gris',
      contexto: `${enDuda ? 'A medias: SE Ranking en duda (abajo) · ' : ''}Alertas con evidencia fechada; no acredita objetivos SEO confirmados${base.length > baseVerde ? ` · ${base.length - baseVerde} sin dato fuera de la cuenta` : ''}`, medible: 'medias', medibleDetalle: R.motivo_medible || 'Las 15 palabras son provisionales (las de más búsquedas) y no todos tienen Search Console', frescura: fresGSC,
      ir: 'Ver el semáforo', alPulsar: () => irPestana(cont, 'seo') }));
    t.push(tile({ icono: 'baja', etiqueta:'Cambios fuera del top10 acreditados',valor:num(fuera),unidad:'consultas de la muestra',estado:fuera?'rojo':'gris',
      contexto:`Sólo pares fechados del mismo motor; ${num(desap)} ausencias anteriores por contrastar`,medible:'medias',medibleDetalle:'No acredita objetivo contratado ni ausencia de cambios fuera de la muestra', frescura: fresSR,
      ir: 'Ver cuáles', alPulsar: () => irPestana(cont, 'seo', 'rojo') }));
    t.push(tile({ icono: 'grafico', etiqueta: 'Clics · 7 días', valor:sumSem===null?null:num(sumSem),estado:'gris',
      comparacion:sumSem!==null&&sumAnt!==null?{delta:variacion(sumSem,sumAnt),pct:true,texto:'frente a los 7 anteriores'}:null,contexto:`${cohorteClics.clientes} de ${base.length} clientes con ventanas compatibles${cohorteClics.ventana ? ` · ${fDiaRO(cohorteClics.ventana[0])} → ${fDiaRO(cohorteClics.ventana[1])}` : ' · ventana pendiente'}${cohorteClics.otras_ventanas ? ` · ${cohorteClics.otras_ventanas} con otro periodo excluidos` : ''} · cobertura parcial`, medible: 'hoy', medibleDetalle: 'Google da los clics con 2-3 días de retraso', frescura: fresGSC }));
  }
  t.push(tile({ icono: 'alert', etiqueta: 'Webs en rojo', valor: websRojo.length, unidad: `de ${webs.length}`, estado: websRojo.length ? 'rojo' : 'verde',
    contexto: `${caidas.length} sin responder · ${websRojo.length - caidas.length} spam o certificado`, medible: 'medias', medibleDetalle: 'Desde la IP de RO; desde fuera llega con el despliegue', frescura: fresMon,
    ir: 'Ver webs', alPulsar: () => irPestana(cont, 'webs', 'rojo') }));
  t.push(tile({ icono: 'flag', etiqueta: 'Fallos de medición', valor: avisosMed, estado: avisosMed ? 'ambar' : 'verde', contexto: 'Analytics a cero o duplicado', medible: 'hoy', medibleDetalle: 'Revisión del 2-oct',
    ir: 'Ver avisos', alPulsar: () => irPestana(cont, 'webs', 'medicion') }));
  if (r === 'web') {
    const cert = webs.filter(w => (w.comprobacion?.cert_dias ?? 999) <= 30).length;
    t.push(tile({ icono: 'escudo', etiqueta: 'Certificados ≤ 30 días', valor: cert, estado: cert ? 'ambar' : 'verde', contexto: 'Actuar con 7 días o menos', medible: 'hoy', frescura: fresMon,
      ir: 'Ver cuáles', alPulsar: () => irPestana(cont, 'webs', 'cert') }));
  }
  const ctxN = [rejillaTarjetas(t)];   // Ronda U (#1): las tarjetas grandes y los avisos van debajo de la lista, plegados

  // ---------- aviso de calidad del dato (lo que NO es un problema del cliente)
  const totalDes = base.reduce((a, f) => a + ((f.visibilidad || {}).desaparecen || 0), 0);
  const conGsc = base.filter(f => f.clics);
  const suben = conGsc.filter(f => (f.clics.var_mes || 0) > 0).length;
  if (r !== 'web' && totalDes > 50) {
    // R12: el mismo texto que lee Mi día (resumen.aviso_seranking) cuando se mira toda la cartera
    ctxN.push(avisoParcial(`La copia anterior registra ${num(totalDes)} palabras sin posición. No acredita una caída ni su fecha. Los clics comparables de Google suben en ${suben} de ${conGsc.length} clientes con recuentos. La diferencia no identifica la causa: contrasta buscador, ubicación, dispositivo y fecha antes de tocar nada. Las palabras que hoy no ve no cuentan como caída.`, { titulo: 'Cuidado con el dato de SE Ranking.' }));
  }
  if (r !== 'web') ctxN.push(h('p', { class: 'sub', style: { margin: '0', maxWidth: '72ch' } }, 'Esta pantalla no cambia con el periodo: SE Ranking muestra posiciones guardadas (la mejor de dos comprobaciones seguidas), frente a 7 y 30 días. Search Console muestra clics de 7 y 28 días hasta su último día con datos; no son posiciones de Maps ni un promedio comparable con una palabra concreta.'));

  // ---------- 2 · pestañas (cada puesto abre en la suya)
  const inicial = r === 'web' ? 'webs' : 'seo';
  const p = pestanas({
    clave: `seo.${ctx.persona.id}`, activa: inicial, etiqueta: 'Secciones',
    pestanas: [
      { id: 'seo', texto: 'Posiciones', icono: 'star', cuenta: base.filter(f => f.estado === 'rojo').length, cuentaEstado: 'rojo' },
      { id: 'ficha', texto: 'Ficha de Google', icono: 'pin' },
      { id: 'webs', texto: 'Webs', icono: 'mundo_web', cuenta: websRojo.length, cuentaEstado: 'rojo' },
    ],
    pintar: (id, z) => (id === 'seo' ? pintarSeo(z, ctx, d, base, r) : id === 'webs' ? pintarWebs(z, ctx, d, r, webObjetivo) : pintarFicha(z, ctx, d, base)),
  });
  p.id = 'seo-pestanas';
  // franja de cifras (llevan a su pestaña y filtro): lo que pide acción, primero
  const franja = franjaEnLinea(franjaCifras([
    { etiqueta: 'Webs en rojo', valor: websRojo.length, estado: websRojo.length ? 'rojo' : '', alPulsar: () => irPestana(cont, 'webs', 'rojo') },
    { etiqueta: 'Sin responder', valor: caidas.length, estado: caidas.length ? 'rojo' : '', alPulsar: () => irPestana(cont, 'webs', 'caidas') },
    r !== 'web' ? { etiqueta: 'Cambios top10 acreditados', valor: fuera, titulo: 'Consultas de la muestra con pares fechados del mismo motor. Cobertura parcial: cero no acredita cumplimiento de objetivos ni ausencia de cambios fuera de la muestra.', estado: fuera ? 'rojo' : '', alPulsar: () => irPestana(cont, 'seo', 'rojo') } : null,
    r !== 'web' ? {etiqueta:'Señales anteriores por contrastar',valor:base.filter(f=>f._medicionSEO?.historicas>0).length,titulo:'Clientes con avisos de copia sin evidencia de comparación; no objetivos cumplidos', alPulsar: () => irPestana(cont, 'seo') } : null,
    { etiqueta: 'Fallos de medición', valor: avisosMed, alPulsar: () => irPestana(cont, 'webs', 'medicion') },
  ], { etiqueta: 'Cifras (llevan a su lista)' }));
  cont.append(pantallaAncha({ id: 'seo-web', filtros: franja, lista: p, contexto: ctxN, tituloContexto: 'Cifras, avisos del dato y cómo se mide' }));
  if (webObjetivo !== null) p.elegir('webs');
}

function irPestana(cont, id, chip) {
  const p = cont.querySelector('#seo-pestanas');
  if (!p) return;
  p.elegir(id);
  if (chip) {
    const b = [...p.querySelectorAll('.chips-f button')].find(x => x.dataset.v === chip);
    if (b && b.getAttribute('aria-pressed') !== 'true') b.click();
  }
  if (p.getBoundingClientRect().top > innerHeight * 0.6) p.scrollIntoView({ behavior: 'smooth', block: 'start' });
}
function marcarChips(chips, opciones) {
  [...chips.querySelectorAll('button')].forEach((b, i) => { if (opciones[i]) b.dataset.v = opciones[i].valor; });
  return chips;
}

// 3-oct (Tomás: «SE Ranking se ha roto») · la FECHA DEL DATO siempre a la vista, para que nadie confunda «dato del día» con
// La fecha de posiciones permanece visible; programación/créditos son referencias, no promesa de ejecución local. Si la última lectura
// falló o el dato tiene 2 días o más, aviso ámbar con el motivo (seo.json › _meta.seranking, de fuentes_seo/sr_leer.py).
function lineaDatoSR(d) {
  const m = d.seo?._meta?.seranking || {};
  if (!m.texto_dia) return null;
  const linea = h('div', { class: 'sub', style: { margin: '0', display: 'flex', alignItems: 'center', gap: 'var(--s-2, 8px)', flexWrap: 'wrap' } },
    icono('cal', { clase: 's' }), h('b', { style: { color: 'var(--ink)' } }, m.texto_dia),
    notaCompacta336(h,'Actualización y referencia de créditos',h('p',{},'La fecha indica la última lectura guardada. La ejecución automática local a las 6:00 no está acreditada; esta vista no garantiza próximas lecturas ni consumo gratuito.'),
      m.creditos?.fuente ? h('a', { href: m.creditos.fuente, target: '_blank', rel: 'noopener', title: m.creditos.texto || '' }, 'Referencia documental de créditos ↗') : h('span',{},'Sin referencia de créditos disponible.')));
  return m.aviso ? h('div', { class: 'pila', style: { gap: 'var(--s-2, 8px)' } }, avisoParcial(m.aviso, { titulo: 'Posiciones sin actualizar.' }), linea) : linea;
}

// 244 · Dos líneas por métrica, contexto completo en título/detalle; sin cálculos nuevos.
function celdaCompactaSEO244(principal, detalle, titulo = detalle) {
  return h('span', {title:titulo || '',style:{display:'block',minWidth:'0',lineHeight:'1.35'}},
    h('span',{},principal), detalle?h('small',{class:'sub',style:{display:'block',fontSize:'12px',maxWidth:'240px',overflow:'hidden',whiteSpace:'nowrap',textOverflow:'ellipsis'}},detalle):null);
}

// ------------------------------------------------------------------ pestaña SEO
function pintarSeo(z, ctx, d, base, r) {
  if (ctx.vigente && !ctx.vigente()) return;
  { const l = lineaDatoSR(d); if (l) z.append(l); }
  if (!base.length) {
    z.append(vacio({ icono: 'star', titulo: r === 'seo' ? 'No tienes clientes de SEO asignados' : 'No hay clientes de SEO que puedas ver', texto: 'Las asignaciones (silla «SEO») salen de la fase 0 y las confirma Mili. Si falta un cliente tuyo, díselo a Jerónimo (jefe de SEO).', quien: 'Mili', borde: true }));
    return;
  }
  // lo primero hoy (máx. 7)
  const prim=[...base.filter(f=>f.estado==='rojo'||f.estado==='ambar'),...base.filter(f=>f.estado==='gris'&&f._medicionSEO?.historicas>0)].slice(0,7);
  const recomendaciones = panel({ titulo: 'Lo primero hoy', icono: 'zap', sub:'Cambios observados acreditados primero; señales anteriores en gris para contrastar. No certifica objetivos cumplidos (máximo 7).' },
    listaLoPrimero(prim.map((f, i) => ({
      estado: cuentagotas(f.estado, i, prim.length), icono: f.alertas[0]?.tipo === 'clics' ? 'grafico' : f.alertas[0]?.tipo === 'visibilidad' ? 'ojo' : 'star',
      motivo:`${f.cliente} · ${f.estado==='gris'&&f._medicionSEO?.historicas>0?f.alertas.find(a=>!a.acreditada)?.texto:f.motivo}`,
      detalle: [nom(ctx, f.seo_id) ? `Lo lleva ${nom(ctx, f.seo_id)}` : 'Sin SEO asignado', f.n_alertas.rojo + f.n_alertas.ambar > 1 ? `${f.n_alertas.rojo + f.n_alertas.ambar - 1} avisos más` : null].filter(Boolean).join(' · '),
      botones: masAcciones(
        h('a', { class: 'bt mini', href: `#/seo-web/${f.cliente_id}` }, icono('cli'), 'Ver cliente'),
        f.seranking ? h('a', { href: f.seranking.prueba, target: '_blank', rel: 'noopener', role: 'menuitem' }, icono('ext', { clase: 's' }), 'Abrir en SE Ranking') : null,
        botonConfirmar({ texto: 'Crear tarea', pregunta: `¿Tarea en ClickUp para ${nom(ctx, f.seo_id) || 'el SEO'}?`, confirmar: 'Sí, crear', mini: true, soloLectura: ctx.soloLectura,
          alConfirmar: async () => { await ctx.accion({ herramienta: 'clickup', tipo: 'tarea', objeto: `SEO · ${f.cliente} · ${f.motivo}`.slice(0, 200), cliente_id: f.cliente_id, texto: f.motivo, vista_previa: `Tarea en la lista de SEO de ${f.cliente}: «${f.motivo}». Responsable: ${nom(ctx, f.seo_id) || 'sin asignar'}. Plazo 48 h.` }); return 'En la cola (simulación)'; } })),
    })), { vacio: { titulo:'Sin alertas actuales acreditadas en esta muestra',porque:'Revisa fecha, motor y cobertura; no demuestra ausencia de cambios ni cumplimiento.',celebrar:false } }));

  // semáforo de la cartera con chips que se quedan
  const cuenta = e => base.filter(f => f.estado === e).length;
  const ops = [
    { valor: '', texto: 'Todos', cuenta: base.length },
    { valor: 'rojo', texto: 'Actuar', icono: 'fire', cuenta: cuenta('rojo'), cuentaEstado: 'rojo' },
    { valor: 'ambar', texto: 'Vigilar', icono: 'alert', cuenta: cuenta('ambar') },
    { valor: 'verde', texto: 'Señal favorable', icono: 'info', cuenta: cuenta('verde') },
    { valor: 'sin_gsc', texto: 'Clics sin dato', icono: 'plug', cuenta: base.filter(f => !f.clics).length },
  ];
  const caja = h('div');
  const chips = marcarChips(chipsFiltro({ etiqueta: 'Estado', clave: `seo.estado.${ctx.persona.id}`, opciones: ops, alCambiar: () => pintar() }), ops);
  const pintar = () => {
    if (ctx.vigente && !ctx.vigente()) return;
    const v = chips.valor();
    const filas = base.filter(f => !v || (v === 'sin_gsc' ? !f.clics : f.estado === v)).map(f => ({ ...f, panelEspecialista: panelSeo({...f,clics:f.clics?{...f.clics,mes_ant:f._medicionSEO?.clics?.mes?f.clics.mes_ant:null}:null},d.seo._meta) }));
    caja.replaceChildren(tablaDensa({
      filas, porPagina: 15, apilable: true,
      buscar: { campos: ['cliente', 'seo_quien', 'motivo'], placeholder: 'Buscar cliente o persona' },
      filtros: r === 'jefa' ? [{ clave: 'seo_quien', titulo: 'Lo lleva' }] : [],
      columnas: [
        { clave: 'cliente', titulo: 'Cliente', principal: true, celda: f => h('span', { class: 'celda-cli' }, logoCliente({ nombre: f.cliente, logo: (ctx.clientes.find(c => c.id === f.cliente_id) || {}).logo }), f.cliente) },
        { clave:'objetivos',titulo:'Objetivo / páginas',ordenable:false,celda:f=>{
          const op=filas.filter(x=>x.cliente_id===f.cliente_id).length===1&&typeof d.oportunidadesScope332==='string'&&ambitoOportunidades332(ctx)?.firma===d.oportunidadesScope332?oportunidadPagina332(f,d.seo._meta,ctx):null;
          const objetivo=celdaObjetivo374(h,ctx,d.objetivos374,f.cliente_id);
          if(!op)return celdaCompactaSEO244(objetivo,f.panelEspecialista.paginas===null?'Páginas: sin dato':`${f.panelEspecialista.paginas} páginas GSC · 28 d`);
          const valido=()=>ambitoOportunidades332(ctx)?.firma===op.scope_firma;
          const motivo=op.tipo==='descenso'?` · -${op.perdidos} clics observados`:op.tipo==='impresiones_sin_clics'?' · Sin clics':'';
          return h('span',{},celdaCompactaSEO244(h('a',{href:`#/${op.ir}`,class:'sub enlace',title:`${op.accion} ${op.ventana.desde} → ${op.ventana.hasta}; lectura ${op.lectura}. ${op.nota}`,'aria-label':`Revisar página de ${f.cliente}: ${op.ruta}`,on:{click:e=>{if(!valido())e.preventDefault();}}},`Revisar ${op.ruta}`),`${op.clics} clics · ${op.impresiones} impresiones${motivo}`,op.accion),objetivo);
        } },
        { clave:'posiciones',titulo:'Consultas org. / Maps',ordenable:false,celda:f=>celdaCompactaSEO244(`Org: ${f.panelEspecialista.organico===null?'sin dato':f.panelEspecialista.organico} · Maps: ${f.panelEspecialista.maps===null?'sin dato':f.panelEspecialista.maps}`,`${f.panelEspecialista.consultas} consultas · ${f.panelEspecialista.sr || 'sin fecha'}`,`Consultas con posición observada, no posición media. Muestra provisional; ubicación y dispositivo en detalle. Fuente ${f.panelEspecialista.sr || 'sin fecha'}`) },
        { clave:'clics',titulo:'Clics · 28 d',num:true,valor:f=>f.panelEspecialista.trafico??-1,celda:f=>celdaCompactaSEO244(f.panelEspecialista.trafico===null?'Sin dato':`${num(f.panelEspecialista.trafico)} clics`,`Antes: ${f.panelEspecialista.antes===null?'sin dato':num(f.panelEspecialista.antes)} · hasta ${f.panelEspecialista.hasta || 'sin fecha'}`,'Search Console: 28 días y los 28 anteriores cuando hay comparación acreditada; no posiciones de Maps.') },
        { clave:'medicion',titulo:'Técnica / reseñas',ordenable:false,celda:f=>h('span',{},celdaCompactaSEO244('Schema: no medido',null),h('span',{class:'fila',style:{gap:S[1]}},h('a',{class:'sub enlace',href:`#/seo-web/webs/${f.cliente_id}`,'aria-label':`Revisar web de ${f.cliente}`},'Web'),h('button',{type:'button',class:'bt mini','aria-label':`Consultar reseñas de ${f.cliente}`,on:{click:()=>{if(ctx.vigente && !ctx.vigente())return;z.closest?.('#seo-pestanas')?.elegir?.('ficha');}}},'Reseñas'))) },
        { clave:'pendiente',titulo:'Detalle',ordenable:false,celda:f=>h('a',{href:`#/seo-web/${f.cliente_id}`,class:'bt mini',title:f.panelEspecialista.accion,'aria-label':`Revisar ${f.cliente}: ${f.panelEspecialista.accion}`},'Revisar cliente') },
        ...(r==='jefa'?[{clave:'seo_quien',titulo:'Lo lleva',celda:f=>nom(ctx,f.seo_id)||'Sin asignar'}]:[]),
      ],
      alPulsar: f => { if (!ctx.vigente || ctx.vigente()) ctx.navegar(`seo-web/${f.cliente_id}`); },
      etiquetaFila: f => `${f.cliente}: ${TXT_EST[f.estado]}, ${f.motivo}. Abrir detalle`,
      vacio: { titulo: 'Ningún cliente en este estado', porque: 'Cambia el filtro de arriba.' },
    }));
  };
  pintar();
  z.append(panel({ titulo: r==='seo'?'Mis clientes · revisión SEO':'Clientes · revisión SEO', icono: 'medidor', sub: 'Muestra parcial · objetivos por confirmar · orgánico y Maps separados. Pulsa un cliente para revisar fuente y contexto.' },
    h('div', { class: 'cuerpo', style: { paddingBottom: S[1] } }, chips), caja));
  z.append(renderObjetivos374(h,ctx,d.objetivos374));
  z.append(h('details',{},h('summary',{style:{minHeight:'44px'}},`Recomendaciones · ${prim.length} clientes de la muestra`),recomendaciones,
    h('p',{class:'sub'},'Objetivos por confirmar. SE Ranking usa consultas provisionales y la mejor posición entre dos comprobaciones; región y dispositivo pendientes de identificar. Orgánico y Maps separados. Un dato ausente no es cero.')));

  // su célula (solo jefas): carga y estado por persona
  if (r === 'jefa') {
    const por = new Map();
    for (const f of base) {
      const k = nom(ctx, f.seo_id) || 'Sin asignar';
      if (!por.has(k)) por.set(k, { rojo: 0, ambar: 0, verde: 0, gris: 0, n: 0 });
      const o = por.get(k); o[f.estado]++; o.n++;
    }
    z.append(panel({ titulo: 'Tu célula', icono: 'eq', sub: 'Clientes de SEO por persona y cómo van. Las horas, en «Horas y productividad» (solo como aviso).' },
      h('div', { class: 'cuerpo' }, h('div', { class: 'rejilla' }, [...por.entries()].sort((a, b) => b[1].rojo - a[1].rojo || b[1].n - a[1].n).map(([k, o]) =>
        h('div', { style: { border: '1px solid var(--line)', borderRadius: 'var(--r-sm)', padding: S[3], background: 'var(--card)', display: 'grid', gap: S[2], minWidth: '0' } },
          h('span', { class: 'fila', style: { gap: S[2], flexWrap: 'nowrap', fontWeight: '700', minWidth: '0' } }, h('span', { class: 'av s', 'aria-hidden': 'true' }, iniciales(k)), h('span', { style: { overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' } }, k)),
          h('span', { class: 'fila', style: { gap: `${S[1]} ${S[3]}` } }, estadoTexto('rojo', `${o.rojo} actuar`), estadoTexto('ambar', `${o.ambar} vigilar`), estadoTexto('verde', `${o.verde} señal favorable`)),
          h('span', { class: 'sub' }, `${num(o.n)} clientes de SEO`)))))));
  }

  // fase 2 al pie (lo que todavía no se mide: no se pinta como número), plegado
  z.append(piePlegado('Todavía no se mide · 5 cosas (fase 2)', [
    ['Páginas importantes indexadas y piezas nuevas a 14 días', 'falta la inspección de URL de Search Console con la lista de páginas de cada cliente'],
    ['404 y errores tras tocar la web', 'falta el informe de cobertura (no está en la API) y la auditoría de SE Ranking'],
    ['Cosecha trimestral (URL en posición 5-20 con 300 impresiones o más)', 'se calcula con Search Console por página; falta guardar qué URL se tocó'],
    ['Visibilidad en respuestas de IA', 'falta el seguimiento por cliente en SE Ranking'],
    ['Entregas SEO en plazo', 'faltan fecha y tipo en las tareas de ClickUp (módulo Producción)']]));
}

// ------------------------------------------------------------------ tablero del equipo web (Modular DS, 3-oct)
// Encargo de Tomás: «para el equipo de web el acceso a Modular de todos ellos». El molde de trabajo (modulos/_trabajo.js):
// franja de cifras que filtran · LA lista por urgencia (caídas, sin copia, vulnerabilidades críticas, certificados,
// actualizaciones) con sus acciones al lado · el detalle de la web elegida a la derecha (debajo en el móvil).
const PROB_FILTRO = {
  urgentes: (w, rev) => (w.urgencia || 0) > 0 && !rev.has(String(w.modular_id)),
  caidas: w => (w.problemas || []).some(p => p.clave === 'caida' || p.clave === 'caida_fuera'),
  copia: w => (w.problemas || []).some(p => p.clave === 'sin_copia' || p.clave === 'copia_atrasada'),
  critica: w => (w.vulnerabilidades?.criticas || 0) > 0,
  cert: w => (w.certificado?.dias ?? 999) <= 14,
  act: w => (w.actualizaciones?.pendientes || 0) >= 5,
  revisadas: (w, rev) => rev.has(String(w.modular_id)),
};
function pintarTablero(z, ctx, d, r) {
  const T = d.tablero, meta = T._meta || {}, rev = d.rev || new Map();
  const webs = T.webs || [], fuera = T.fuera_de_modular || [];
  const yo = ctx.persona.id;
  const mias = webs.filter(w => w.dueno_id === yo).length + fuera.filter(f => f.dueno_id === yo).length;
  let filtro = r === 'web' && mias ? 'mias' : 'urgentes';
  let elegida = null;
  const cuenta = k => webs.filter(w => PROB_FILTRO[k](w, rev)).length;
  const franjaCaja = h('div', { style: { minWidth: '0' } });
  const listaCaja = h('div', { class: 'pila', style: { gap: S[2], minWidth: '0' } });
  const detalleCaja = h('div', { class: 'pila', 'data-webs-detalle': '', style: { gap: S[3], minWidth: '0' } });
  const peor = w => ((w.problemas || []).find(p => p.gravedad === 'rojo') ? 'rojo' : (w.problemas || []).find(p => p.gravedad === 'ambar') ? 'ambar' : 'verde');
  const nombre = w => w.cliente_nombre || w.nombre || w.dominio;
  const pintarFranja = () => franjaCaja.replaceChildren(franjaEnLinea(franjaCifras([
    { etiqueta: 'Por urgencia', valor: cuenta('urgentes'), estado: cuenta('urgentes') ? 'rojo' : '', activo: filtro === 'urgentes', alPulsar: () => elegir('urgentes') },
    mias ? { etiqueta: 'Mis webs', valor: mias, activo: filtro === 'mias', alPulsar: () => elegir('mias') } : null,
    { etiqueta: 'Caídas', valor: cuenta('caidas'), estado: cuenta('caidas') ? 'rojo' : '', activo: filtro === 'caidas', alPulsar: () => elegir('caidas') },
    { etiqueta: 'Sin copia reciente', valor: cuenta('copia'), estado: cuenta('copia') ? 'rojo' : '', activo: filtro === 'copia', alPulsar: () => elegir('copia') },
    { etiqueta: 'Vulnerabilidad crítica', valor: cuenta('critica'), estado: cuenta('critica') ? 'rojo' : '', activo: filtro === 'critica', alPulsar: () => elegir('critica') },
    { etiqueta: 'Certificado < 15 días', valor: cuenta('cert'), estado: cuenta('cert') ? 'rojo' : '', activo: filtro === 'cert', alPulsar: () => elegir('cert') },
    { etiqueta: 'Actualizaciones ≥ 5', valor: cuenta('act'), activo: filtro === 'act', alPulsar: () => elegir('act') },
    { etiqueta: 'Fuera de Modular', valor: fuera.length, activo: filtro === 'fuera', alPulsar: () => elegir('fuera') },
    rev.size ? { etiqueta: 'Revisadas hoy', valor: rev.size, activo: filtro === 'revisadas', alPulsar: () => elegir('revisadas') } : null,
  ], { etiqueta: 'Webs por problema (filtran la lista)' })));
  const verDetalle = (w, llevar = true) => {
    elegida = w;
    detalleCaja.replaceChildren(
      barraAcciones({ titulo: nombre(w), sub: `${w.dominio} · lleva la web ${w.dueno || 'sin asignar'}`,
        acciones: [botonAbrirModular(w), botonEntrar(ctx, w), botonCrearTarea(ctx, w), w.sin_cliente ? null : botonAvisarAccount(ctx, w)] }),
      h('div', { class: 'panel' }, h('div', { class: 'cuerpo' }, estadoWeb(ctx, w, { meta, conAcciones: false, estrecho: true }))));
    if (llevar && matchMedia('(max-width: 900px)').matches) detalleCaja.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };
  const filaWeb = w => ({
    estado: peor(w), icono: (w.problemas || [])[0] ? ({ caida: 'mundo_web', caida_fuera: 'mundo_web', sin_copia: 'drive', copia_atrasada: 'drive', vulnerabilidad: 'escudo', certificado: 'candado', malware: 'escudo' })[w.problemas[0].clave] || 'alert' : 'ok',
    motivo: h('button', { type: 'button', class: 'enlace', title: 'Ver el estado completo de esta web', style: { background: 'none', border: '0', padding: '0', font: 'inherit', color: 'inherit', textAlign: 'left', cursor: 'pointer', ...TOQUE },
      on: { click: () => verDetalle(w) } }, `${nombre(w)} · ${(w.problemas || [])[0]?.titulo || 'sin problemas abiertos'}`),
    detalle: [w.dominio, `lleva la web ${w.dueno || 'sin asignar'}`, (w.problemas || []).filter(p => p.gravedad !== 'verde').length > 1 ? `${(w.problemas || []).filter(p => p.gravedad !== 'verde').length - 1} problemas más` : null,
      w.monitor_ro ? (w.monitor_ro.responde ? 'desde RO responde' : 'desde RO no responde') : null, w.sin_cliente ? 'sin cliente' : null,
      rev.get(String(w.modular_id)) ? `revisada por ${nom(ctx, rev.get(String(w.modular_id)).quien)} ${fMod(rev.get(String(w.modular_id)).cuando)}` : null].filter(Boolean).join(' · '),
    botones: accionesWeb(ctx, w, { revisado: rev.get(String(w.modular_id)) || null, verDetalle: () => verDetalle(w),
      alRevisar: () => { rev.set(String(w.modular_id), { quien: yo, cuando: new Date().toISOString() }); } }),
  });
  const filaFuera = f => ({
    estado: 'ambar', icono: 'plug', motivo: `${f.cliente_nombre} · no está en Modular`,
    detalle: [f.dominio, `lleva la web ${f.dueno || 'sin asignar'}`, f.monitor_ro ? (f.monitor_ro.responde ? 'desde RO responde' : `desde RO no responde (${f.monitor_ro.codigo || 'sin respuesta'})`) : null].filter(Boolean).join(' · '),
    botones: [botonCrearTarea(ctx, { ...f, nombre: f.cliente_nombre, problemas: [{ clave: 'fuera', gravedad: 'ambar', titulo: 'Añadir a Modular', detalle: `${f.dominio} no está en Modular DS: sin copias, actualizaciones vigiladas ni aviso de caídas desde fuera.`, accion: f.accion, dueno: f.dueno }] },
      { texto: 'Añadir a Modular' })],
  });
  const POR_PAG = 15;
  let pagina = 1;
  const pintarLista = () => {
    const filas = filtro === 'fuera' ? fuera
      : webs.filter(w => (filtro === 'mias' ? w.dueno_id === yo && (w.urgencia || 0) > 0 : PROB_FILTRO[filtro](w, rev)));
    const extraMias = filtro === 'mias' ? fuera.filter(f => f.dueno_id === yo) : [];
    const items = filtro === 'fuera' ? filas.map(filaFuera) : [...filas.map(filaWeb), ...extraMias.map(filaFuera)];
    const total = items.length;
    listaCaja.replaceChildren(
      items.length ? listaLoPrimero(items.slice(0, POR_PAG * pagina), { subir: false }) : vacioLinea(filtro === 'revisadas' ? 'Nada revisado en las últimas 24 h.' : 'Ninguna web con este problema. Buena señal.', { icono: 'ok' }),
      total > POR_PAG * pagina ? h('button', { type: 'button', class: 'bt mini', on: { click: () => { pagina += 1; pintarLista(); } } }, `Ver ${Math.min(POR_PAG, total - POR_PAG * pagina)} más (de ${total})`) : null);
    const primera = filtro === 'fuera' ? null : filas[0];
    if (!elegida || !filas.includes(elegida)) { if (primera) verDetalle(primera, false); else detalleCaja.replaceChildren(); }
  };
  function elegir(k) { filtro = k; pagina = 1; pintarFranja(); pintarLista(); }
  pintarFranja();
  pintarLista();
  const R = T.resumen || {};
  const cab = h('div', { class: 'fila sub', style: { gap: S[2] } }, frescura({ fuente: 'Modular DS', fecha: meta.leido || meta.generado }),
    h('span', {}, `${num(webs.length)} webs en Modular · ${num(R.caidas_ahora ?? 0)} caídas ahora · ${num(R.con_vulnerabilidad_critica ?? 0)} con vulnerabilidad crítica · ${num(fuera.length)} webs de clientes fuera de Modular`),
    meta.dato_viejo ? chipEstado('ambar', 'Dato de la última lectura buena') : null);
  // Ronda U (#1): la primera fila a menos de 300 px · el resumen y la hora del dato van al pie del tablero
  z.append(panel({ titulo: 'Tablero de webs (Modular)', icono: 'mundo_web', sub: 'La más urgente primero, con sus acciones. Pulsa el nombre para ver todo.' },
    h('div', { class: 'cuerpo pila', style: { gap: S[3] } },
      pantallaTrabajo({ id: 'webs-tablero', filtros: franjaCaja, lista: listaCaja, detalle: detalleCaja, consejo: false }), cab)));
}

// ------------------------------------------------------------------ pestaña Webs
function pintarWebs(z, ctx, d, r, webObjetivo = null) {
  if (ctx.vigente && !ctx.vigente()) return;
  const webs = d.webs.webs || [];
  const metaW = d.webs._meta || {};
  const M = d.modular || {};
  const responde = w => w.comprobacion?.estado >= 200 && w.comprobacion?.estado < 400;
  // V2 · una sola regla de «lenta» (webs.json → _meta.lenta, la misma que Mi día y Alertas)
  const esLenta = w => (w.lenta !== undefined ? w.lenta : responde(w) && (w.comprobacion?.ms || 0) >= ((metaW.lenta || {}).umbral_ms || 5000));
  // Tablero del equipo web (Modular DS): lo primero que se ve en la pestaña para web, jefe de SEO y web y dirección
  const tablero = d.tablero ? h('div') : null;
  if (tablero) pintarTablero(tablero, ctx, d, r);
  // lo primero: caídas, spam y certificados
  const rojas = webs.filter(w => w.estado === 'rojo').slice(0, 7);
  const recomendacionesWeb = panel({ titulo: d.tablero ? 'Monitor de RO · webs en rojo' : 'Lo primero hoy', icono: 'zap', sub: 'Webs en rojo desde la IP de RO (caídas, spam, certificados). «Lo tengo» evita que suba (a Agus, y a Mili a la hora).' },
    listaLoPrimero(rojas.map((w, i) => ({
      estado: cuentagotas('rojo', i, rojas.length), icono: w.motivo.includes('spam') ? 'escudo' : 'mundo_web',
      motivo: `${w.nombre} · ${w.motivo}`,
      detalle: [nom(ctx, w.web_id) ? `Web: ${nom(ctx, w.web_id)}` : 'Sin persona de web asignada', w.web_aviso && nom(ctx, w.web_id) ? w.web_aviso : null, w.con_campana ? 'tiene campaña encendida: avisar también a publicidad y CRM' : null, w.comprobacion?.hora ? `comprobado ${w.comprobacion.hora.slice(11, 16)}` : null,
        w.modular?.disponibilidad?.estado === 'up' && !responde(w) ? 'Modular la ve arriba desde fuera: bloqueada solo para RO' : null].filter(Boolean).join(' · '),
      // Ronda U (#4 y 50 §SEO): «Lo tengo» y «Avisar al account» a la vista en la fila, al primer clic con «Deshacer» 8 s
      // (son internos: nada sale al cliente). «Abrir la web» en «⋯».
      botones: [
        botonDeshacer({ texto: 'Lo tengo', hecho: 'Tuya', pri: true, icono: 'persona', soloLectura: ctx.soloLectura,
          alHacer: async () => { await ctx.accion({ herramienta: 'app', tipo: 'caida_lo_tengo', objeto: `${w.nombre} · ${w.motivo}`.slice(0, 200), texto: w.motivo, vista_previa: `${ctx.persona.nombre} coge «${w.motivo}» en ${w.url}. Se para la subida a Agus.` }); return 'Tuya · no sube a Agus'; } }),
        botonDeshacer({ texto: 'Avisar al account', hecho: 'Account avisado', icono: 'send', soloLectura: ctx.soloLectura,
          alHacer: async () => { await ctx.accion({ herramienta: 'app', tipo: 'aviso_account', objeto: w.nombre, texto: w.motivo, vista_previa: `Aviso interno al account de ${w.nombre}: «${w.motivo}». Nada sale al cliente.` }); return 'Registro local guardado; aviso al account sin confirmar'; } }),
        ...masAcciones(h('span'), h('a', { href: w.url, target: '_blank', rel: 'noopener', role: 'menuitem' }, icono('ext', { clase: 's' }), 'Abrir la web')).slice(1)],
    })), { subir: !d.tablero, vacio: { titulo: 'Ninguna web en rojo', porque: 'Todas responden desde la IP de RO, sin spam ni certificados a punto de caducar.', celebrar: true } }));   // con tablero, en el móvil no se sube encima de él

  // todas las webs con chips
  const ops = [
    { valor: '', texto: 'Todas', cuenta: webs.length },
    { valor: 'rojo', texto: 'En rojo', icono: 'fire', cuenta: webs.filter(w => w.estado === 'rojo').length, cuentaEstado: 'rojo' },
    { valor: 'caidas', texto: 'No responden', icono: 'mundo_web', cuenta: webs.filter(w => !responde(w)).length, cuentaEstado: 'rojo' },
    { valor: 'spam', texto: 'Spam', icono: 'escudo', cuenta: webs.filter(w => (w.comprobacion?.spam || []).length).length },
    { valor: 'cert', texto: 'Certificado ≤ 30 días', icono: 'candado', cuenta: webs.filter(w => (w.comprobacion?.cert_dias ?? 999) <= 30).length },
    { valor: 'lentas', texto: 'Lentas', icono: 'clock', cuenta: webs.filter(esLenta).length },
    { valor: 'medicion', texto: 'Fallos de medición', icono: 'flag', cuenta: webs.filter(w => w.avisos.length).length },
  ];
  if (M.conectado) ops.push({ valor: 'modular', texto: 'Copias, actualizaciones o seguridad', icono: 'escudo', cuenta: webs.filter(w => w.modular && w.modular.estado !== 'verde').length });
  if (webs.some(w => w.web_id === ctx.persona.id)) ops.push({ valor: 'mias', texto: 'Mis webs', icono: 'persona', cuenta: webs.filter(w => w.web_id === ctx.persona.id).length });
  const filtro = {
    rojo: w => w.estado === 'rojo', caidas: w => !responde(w), spam: w => (w.comprobacion?.spam || []).length,
    cert: w => (w.comprobacion?.cert_dias ?? 999) <= 30, lentas: esLenta, medicion: w => w.avisos.length, mias: w => w.web_id === ctx.persona.id,
    modular: w => w.modular && w.modular.estado !== 'verde',
  };
  // columnas de Modular DS (FORMATO.md): Copia · Actualizaciones · Seguridad · Fuera de RO. Sin conectar: una sola línea gris arriba.
  const sinModular = w => h('span', { class: 'sub', title: w.modular === null ? 'Esta web no está en Modular DS' : 'Modular sin conectar' }, w.modular === null ? 'no está en Modular' : '—');
  const colsModular = M.conectado ? [
    { clave: 'copia', titulo: 'Copia', num: true, valor: w => w.modular?.copias?.dias_sin_copia_buena ?? (w.modular?.copias ? 9999 : -1), celda: w => {
      const c = w.modular?.copias;
      if (!w.modular) return sinModular(w);
      if (!c) return h('span', { class: 'sub', title: 'La clave de Modular no ve las copias' }, 'sin acceso');
      if (!c.ultima_buena) return estadoTexto('rojo', 'nunca');
      const dd = c.dias_sin_copia_buena ?? 0;
      return estadoTexto(dd >= 7 ? 'rojo' : dd >= 2 ? 'ambar' : 'verde', dd < 1 ? 'hoy' : `hace ${num(dd)} ${dd === 1 ? 'día' : 'días'}`, `Última copia buena: ${fDiaHoraRO(c.ultima_buena)}`);
    } },
    { clave: 'act', titulo: 'Actualizaciones', num: true, valor: w => w.modular?.actualizaciones?.pendientes ?? -1, celda: w => {
      if (!w.modular) return sinModular(w);
      const n = w.modular.actualizaciones?.pendientes ?? null;
      return n === null ? h('span', { class: 'sub' }, 'sin dato') : estadoTexto(n >= 5 ? 'ambar' : 'verde', num(n), (w.modular.actualizaciones.detalle || []).slice(0, 8).map(x => `${x.nombre} ${x.de} → ${x.a}`).join(' · ') || null);
    } },
    { clave: 'seg', titulo: 'Seguridad', num: true, valor: w => (w.modular?.vulnerabilidades?.criticas || 0) * 100 + (w.modular?.vulnerabilidades?.altas || 0), celda: w => {
      if (!w.modular) return sinModular(w);
      const v = w.modular.vulnerabilidades;
      if (!v) return h('span', { class: 'sub' }, 'sin dato');
      if (!v.criticas && !v.altas) return estadoTexto('verde', 'sin fallos graves');
      return estadoTexto(v.criticas ? 'rojo' : 'ambar', `${num(v.criticas || 0)} críticas · ${num(v.altas || 0)} altas`, (v.lista || []).map(x => `${x.componente}: ${x.nombre}`).join(' · ') || null);
    } },
    { clave: 'fuera', titulo: 'Fuera de RO', valor: w => ({ down: 0, unknown: 1, up: 2 })[w.modular?.disponibilidad?.estado] ?? 3, celda: w => {
      if (!w.modular) return sinModular(w);
      const e = w.modular.disponibilidad?.estado;
      if (e === 'down') return estadoTexto('rojo', responde(w) ? 'caída desde fuera' : 'caída de verdad', w.modular.disponibilidad?.ultima_caida ? `Caída desde ${fDiaHoraRO(w.modular.disponibilidad.ultima_caida)}` : null);
      if (e === 'up') return estadoTexto(responde(w) ? 'verde' : 'ambar', responde(w) ? 'responde' : 'bloqueada solo para RO');
      return estadoTexto('gris', 'sin monitor');
    } },
  ] : [];
  const caja = h('div');
  const chips = marcarChips(chipsFiltro({ etiqueta: 'Ver', clave: `seo.webs.${ctx.persona.id}`, opciones: ops, alCambiar: () => pintar() }), ops);
  const pintar = () => {
    if (ctx.vigente && !ctx.vigente()) return;
    const v = chips.valor();
    const filas = webs.filter(w => !v || filtro[v]?.(w)).map(w=>({...w,panelEspecialista:panelWeb(w)}));
    caja.replaceChildren(tablaDensa({
      filas, porPagina: 15, apilable: false,
      buscar: { campos: ['nombre', 'url', 'web_quien', 'motivo'], placeholder: 'Buscar web o persona' },
      filtros: [{ clave: 'web_quien', titulo: 'Lleva la web' }],
      columnas: [
        { clave: 'nombre', titulo: 'Web', principal: true, minAncho: '180px', celda: w => h('span', { class: 'pila', style: { gap: S[1] } }, h('b', {}, w.nombre), h('a', { class: 'sub enlace', href: w.url, target: '_blank', rel: 'noopener', style: TOQUE }, w.url.replace(/^https?:\/\//, '').replace(/\/$/, ''))) },
        { clave: 'estado', titulo: 'Estado', valor: w => EST[w.estado], celda: w => h('span', { class: 'pila', style: { gap: S[1], minWidth: '120px',maxWidth:'180px' },title:w.motivo }, estadoTexto(w.estado, TXT_EST[w.estado]), h('small',{class:'sub',style:{fontSize:'12px',overflow:'hidden',whiteSpace:'nowrap',textOverflow:'ellipsis'}},w.motivo)) },
        { clave: 'http', titulo: 'Respuesta', num: true, valor: w => w.comprobacion?.estado || 0, celda: w => w.comprobacion?.estado ? String(w.comprobacion.estado) : h('span', { class: 'sub' }, 'sin respuesta') },
        { clave: 'ms', titulo: 'Respuesta HTML', num:true,valor:w=>w.panelEspecialista.ms??-1,celda:w=>h('span',{class:'pila',style:{gap:S[1]}},w.panelEspecialista.ms===null?'Sin dato':`${numD(w.panelEspecialista.ms/1000,1)} s`,h('span',{class:'sub'},`Desde RO · ${w.panelEspecialista.fechaMonitor || 'sin fecha'} · no es PageSpeed`)) },
        { clave: 'cert', titulo: 'Certificado', num: true, valor: w => w.comprobacion?.cert_dias ?? -1, celda: w => w.comprobacion?.cert_dias !== null && w.comprobacion?.cert_dias !== undefined ? estadoTexto(semaforo(w.comprobacion.cert_dias, { verde: 31, ambar: 8 }), `${num(w.comprobacion.cert_dias)} días`) : h('span', { class: 'sub' }, 'no se pudo leer') },
        ...colsModular,
        {clave:'plugins',titulo:'Plugins / rendimiento',ordenable:false,celda:w=>celdaCompactaSEO244(w.panelEspecialista.plugins===null?'Plugins: sin dato':`${w.panelEspecialista.plugins} plugins pendientes`,'PageSpeed: sin medición',`PageSpeed / LCP: sin medición · piloto bloqueado por cuota. Detalle Modular: ${w.panelEspecialista.fechaModular || 'sin fecha'}`)},
        {clave:'pendiente',titulo:'Siguiente revisión',ordenable:false,celda:w=>h('details',{},h('summary',{style:{minHeight:'44px',whiteSpace:'nowrap'}},'Ver revisión'),h('p',{class:'sub',style:{maxWidth:'240px'}},w.panelEspecialista.accion))},
        { clave: 'web_quien', titulo: 'Lleva la web', celda: w => h('span', { style: { display: 'grid', gap: 'var(--s-1)' } }, nom(ctx, w.web_id) ? nom(ctx, w.web_id) : h('span', { class: 'sub' }, 'sin asignar'),
          w.web_aviso ? h('span', { class: 'sub', style: { overflowWrap: 'anywhere' } }, w.web_aviso) : null) },
      ],
      vacio: { titulo: 'Ninguna web con este filtro', porque: 'Buena señal.' },
    }));
  };
  // R15a (A2): con una web pedida por ruta, el chip vuelve a «Todas» (si el guardado la escondía) y su fila se resalta
  const wObj = webObjetivo ? webs.find(w => w.cliente === webObjetivo) : null;
  if (wObj && chips.valor() && !filtro[chips.valor()]?.(wObj)) chips.querySelector('button[data-v=""]')?.click();
  pintar();
  if (wObj) llevarA(caja, rz => filaConTexto(rz, wObj.url.replace(/^https?:\/\//, '').replace(/\/$/, ''), 'tbody tr'));
  else if (webObjetivo) z.prepend(avisoParcial('Esa web no está entre las vigiladas.', { titulo: 'No la encuentro.' }));
  const lineaModular = M.conectado
    ? h('div', { class: 'fila sub', style: { gap: S[2] } }, frescura({ fuente: 'Modular DS', fecha: M.meta.leido || M.meta.generado }),
      M.resumen ? h('span', {}, `${num(M.resumen.emparejadas ?? 0)} webs en Modular · ${num(M.resumen.caidas_ahora ?? 0)} caídas ahora · ${num(M.resumen.vulnerabilidades_graves ?? 0)} fallos de seguridad graves · ${num(M.resumen.actualizaciones_pendientes ?? 0)} actualizaciones pendientes`) : null,
      (M.meta.errores_parciales || []).length ? h('span', { title: (M.meta.errores_parciales || []).map(x => (typeof x === 'string' ? x : x.texto || x.parte || '')).join(' · ') }, 'Algunas partes sin acceso') : null,
      M.meta.enlace ? h('a', { class: 'bt mini', href: M.meta.enlace, target: '_blank', rel: 'noopener' }, icono('ext'), 'Abrir Modular') : null)
    : h('div', { class: 'fila', style: { gap: S[2] } }, chipEstado('gris', 'Modular sin conectar'), h('span', { class: 'sub', style: { flex: '1 1 320px', minWidth: '0' } }, MODULAR_PASO));
  z.append(panel({ titulo: 'Todas las webs', icono: 'mundo_web', sub: 'Las de todos los clientes y la de RO: el equipo web cubre guardias de todas. Copia, actualizaciones, seguridad y «fuera de RO» salen de Modular DS.' },
    h('div', { class: 'cuerpo pila', style: { paddingBottom: S[1], gap: S[2] } }, lineaModular, chips), caja));
  z.append(h('details',{},h('summary',{style:{minHeight:'44px'}},`Incidencias y tareas web · ${rojas.length} avisos en la muestra`),recomendacionesWeb,...(tablero?[tablero]:[])));

  // avisos de medición
  const conAviso = webs.filter(w => w.avisos.length);
  z.append(panel({ titulo: 'Fallos de medición en las webs', icono: 'flag', sub: 'Analytics a cero o duplicado: no son fallos de la app, son de la web o de acceso. Van a la cola de web y a Agus.' },
    conAviso.length ? h('ul', { class: 'lista-i cuerpo' }, conAviso.flatMap(w => w.avisos.map(a => h('li', { style: { alignItems: 'flex-start' } }, h('span', { class: 'ico-c ambar s' }, icono('flag')), h('span', { style: { flex: '1', minWidth: '0' } }, h('b', {}, `${w.nombre} · ${a.titulo}. `), `${a.texto} Qué hacer: ${a.que_hacer} `, h('span', { class: 'sub' }, `(${a.fuente})`)))))) :
      h('div', { class: 'cuerpo' }, vacioLinea('Sin fallos de medición: ninguna web tiene Analytics a cero ni duplicado.', { icono: 'ok' }))));

  // cómo se comprueba: dos puntos de vista (lección de Hostinger, 2-oct), plegado al pie
  const mon = metaW.monitor || {};
  z.append(piePlegado('Cómo se comprueba cada web · desde dos sitios', [
    ['Desde la IP de RO', `una comprobación real de cada web desde el Mac de RO (${fDiaHoraRO(mon.leido)}): código de respuesta, redirección, tiempo, certificado y palabras de spam en la portada.`],
    M.conectado ? ['Desde fuera · Modular DS', 'vigila cada web desde fuera, sus copias, las actualizaciones y los fallos de seguridad. Caída de verdad = falla en los dos; si Modular la ve arriba y desde RO no responde, está «bloqueada solo para RO».']
      : ['Desde fuera · Modular sin conectar', MODULAR_PASO],
    ['Velocidad · PageSpeed', 'La respuesta HTML de RO no mide la carga visual. El lector PageSpeed está preparado; el piloto del 3-oct devolvió límite de cuota y todavía no hay puntuación. Debe habilitarse una clave con cuota antes de automatizar la cartera.'],
  ]));
}

// ------------------------------------------------------------------ pestaña Ficha de Google
function pintarFicha(z, ctx, d, base) {
  // lo que ya sale: posiciones en Maps donde SE Ranking las mide (15 como máximo)
  const conMapa = base.map(f => ({ ...f, mapa: (f.informe15 || []).filter(k => k.mapa) })).filter(f => f.mapa.length);
  const filas = conMapa.flatMap(f => f.mapa.map(k => ({ cliente: f.cliente, cliente_id: f.cliente_id, k: k.k, mapa: k.mapa })));
  // Ronda U (50 §SEO): una línea, y debajo lo que sí se puede hacer hoy (posición en Maps)
  const gz = h('div'); z.append(gz); pestanaFichaGoogle(gz, ctx);   // 3-oct · reseñas por responder, llamadas y rutas (o «pendiente de aprobación de Google»)
  z.append(panel({ titulo: 'Posiciones en Maps que ya da SE Ranking', icono: 'pin', sub: `Solo en los proyectos con buscador de Maps dado de alta. Posición de la última lectura · ${fmt.plural(filas.length, 'palabra', 'palabras')}, todas (la misma cuenta que Mi día).` },
    filas.length ? tablaDensa({ filas, porPagina: 15, apilable: false, columnas: [
      { clave: 'cliente', titulo: 'Cliente', principal: true, celda: x => h('a', { class: 'celda-cli', href: `#/seo-web/${x.cliente_id}`, style: { color: 'var(--ink)', textDecoration: 'none', ...TOQUE } }, x.cliente) },
      { clave: 'k', titulo: 'Palabra', celda: x => h('span', { style: { overflowWrap: 'anywhere' } }, x.k) },
      { clave: 'mapa', titulo: 'En Maps', num: true, celda: x => posCh(x.mapa) },
    ] })
      : h('div', { class: 'cuerpo' }, vacioLinea('Sin posiciones Maps observadas en esta muestra de hasta 15 consultas. No acredita ausencia de seguimiento; contrasta la configuración y la fecha en SE Ranking.', { icono: 'pin', quien: 'Jerónimo' }))));
  z.append(piePlegado('Lo que enseñará en cuanto se conecte · 5 cosas', [
    ['Reseñas nuevas sin responder', 'las de 1-3 estrellas arriba; 24 h → Jerónimo (jefe de SEO), 48 h → account'],
    ['Tasa de llamada de la ficha', 'clics de llamada ÷ vistas de la misma ventana; objetivo propio pendiente de ratificar, sin umbral universal'],
    ['Acciones desde la ficha', 'llamadas + rutas + clics a la web + mensajes, frente al mes anterior'],
    ['Actividad', 'fecha de la última publicación o foto y cadencia acordada; sin inventario no acredita cumplimiento'],
    ['Ficha a punto', 'las 9 casillas del ciclo mensual en ClickUp'],
  ]));
}

// =================================================================== detalle de un cliente
function pintarDetalle(cont, ctx, d, id) {
  const volver = h('a', { class: 'bt', href: '#/seo-web' }, icono('volver'), 'Volver a SEO');
  const f = (d.seo.clientes || []).find(x => x.cliente_id === id);
  const c = ctx.clientes.find(x => x.id === id);
  if (!f) {
    if (c && !c.detalle) {
      ctx.titulo(c.nombre, '');
      cont.append(vacio({ icono: 'candado', titulo: 'El SEO de este cliente no es de tu puesto', texto: `Lo ve quien lleva el cliente y el jefe de SEO (Jerónimo). Si necesitas algo de ${c.nombre}, habla con ${c.responsable}.`, quien: c.responsable, accion: volver, borde: true }));
    } else {
      ctx.titulo(c ? c.nombre : 'Cliente', '');
      cont.append(vacio({ icono: 'star', titulo:c?'SEO sin fuente visible confirmada':'No encuentro ese cliente',texto:c?'Esta copia no aporta una fila SEO autorizada y activa de este cliente; no acredita ausencia de servicio o seguimiento.' : `No hay cliente «${id}».`, accion: volver, borde: true }));
    }
    return;
  }
  const w = (d.webs.webs || []).find(x => x.cliente === id);
  ctx.titulo(f.cliente, `SEO · ${nom(ctx, f.seo_id) ? `lo lleva ${nom(ctx, f.seo_id)}` : 'sin SEO asignado'}${nom(ctx, f.web_id) ? ` · web: ${nom(ctx, f.web_id)}` : ''}`);
  const visibles = (d.seo.clientes || []).map(x => ctx.clientes.find(k => k.id === x.cliente_id)).filter(Boolean);
  cont.append(h('div', { class: 'fila', style: { justifyContent: 'space-between' } },
    h('nav', { class: 'migas', 'aria-label': 'Migas' }, h('a', { href: '#/seo-web' }, icono('globe', { clase: 's' }), 'SEO, ficha y webs'), h('span', { 'aria-hidden': 'true' }, '›'), h('span', { 'aria-current': 'page' }, f.cliente)),
    selectorCliente({ clientes: visibles, actual: id, etiqueta: 'Cambiar de cliente', alElegir: x => ctx.navegar(`seo-web/${x.id}`), insignia: x => { const y = d.seo.clientes.find(k => k.cliente_id === x.id); return y ? chipEstado(y.estado, TXT_EST[y.estado]) : null; } })));

  // cabecera
  cont.append(h('section', { class: 'detalle-cab', 'aria-label': 'Cabecera' },
    h('div', { class: 'fila', style: { gap: S[4], alignItems: 'center' } },
      logoCliente({ nombre: f.cliente, logo: c?.logo }, 'logo-cli xl'),
      h('div', { style: { minWidth: 0, flex: '1 1 260px' } },
        h('h2', {}, f.cliente),
        h('div', { class: 'meta-linea', style: { marginTop: S[1] } },
          f.web ? h('span', { style: { display: 'inline-flex', alignItems: 'center', gap: S[1], minWidth: '0', maxWidth: '100%' } }, icono('link'), h('a', { href: f.web, target: '_blank', rel: 'noopener', style: { display: 'inline-flex', alignItems: 'center', minHeight: 'var(--s-8)', minWidth: '0', maxWidth: '100%', overflowWrap: 'anywhere', whiteSpace: 'normal' } }, f.web.replace(/^https?:\/\//, '').replace(/\/$/, ''))) : null,
          f.seranking ? h('span', {}, icono('star'), `${num(f.seranking.seguidas)} palabras seguidas · ${f.seranking.buscadores} buscadores`) : null,
          nom(ctx, f.seo_id) ? h('span', {}, h('span', { class: 'av s', 'aria-hidden': 'true' }, iniciales(nom(ctx, f.seo_id))), nom(ctx, f.seo_id)) : null),
        h('div', { class: 'fila', style: { marginTop: S[3], gap: S[2] } }, chipEstado(f.estado, TXT_EST[f.estado]), h('span', { class: 'sub', style: { overflowWrap: 'anywhere', minWidth: 0 } }, f.motivo))),
      h('div', { class: 'fila' },
        f.seranking ? h('a', { class: 'bt', href: f.seranking.prueba, target: '_blank', rel: 'noopener' }, icono('ext'), 'Abrir en SE Ranking') : null,
        f.gsc ? h('a', { class: 'bt', href: `https://search.google.com/search-console/performance/search-analytics?resource_id=${encodeURIComponent(f.gsc.site)}`, target: '_blank', rel: 'noopener' }, icono('ext'), 'Search Console') : h('span', { class: 'bt', 'aria-disabled': 'true', title: 'Falta emparejar Search Console' }, icono('plug'), 'Search Console: falta emparejar'),
        f.ga4_enlace ? h('a', { class: 'bt', href: f.ga4_enlace, target: '_blank', rel: 'noopener' }, icono('ext'), 'Analytics') : h('span', { class: 'bt', 'aria-disabled': 'true', title: 'Falta emparejar Analytics' }, icono('plug'), 'Analytics: falta emparejar'),
        h('a', { class: 'bt', href: 'https://business.google.com/locations', target: '_blank', rel: 'noopener' }, icono('ext'), 'Ficha de Google')))));

  if (f.seranking) { const l = lineaDatoSR(d); if (l) cont.append(l); }
  // tarjetas (5 → una fila de 5). Ventanas fijas de la fuente, dichas en cada etiqueta.
  const k = f.clics;
  const t = [];
  const top5Hoy=conteoSEO(f.reparto?.top5?.hoy),top5Mes=conteoSEO(f.reparto?.top5?.mes),top10Hoy=conteoSEO(f.top10_15);
  t.push(tile({ icono: 'star', etiqueta: 'Palabras en el top 5', valor: top5Hoy===null?null:num(top5Hoy), unidad: top5Hoy===null?null:'de 15', estado:'gris',
    comparacion: top5Hoy!==null&&top5Mes!==null ? { delta: top5Hoy-top5Mes, texto: 'frente a hace 30 días' } : null, contexto: f.reparto ? `${top10Hoy===null?'Top 10 sin dato':`${num(top10Hoy)} de 15 en el top 10`}${f.reparto.top5?.sin_ver_hoy ? ` · ${num(f.reparto.top5.sin_ver_hoy)} que hoy SE Ranking no ve (no cuentan)` : ''}` : 'Sin dato · sin proyecto en SE Ranking', medible: f.reparto ? 'hoy' : 'no',
    medibleDetalle:'Recuento observado; no acredita objetivo de servicio + ciudad cumplido', frescura: f.seranking ? { fuente: 'SE Ranking', fecha: f.seranking.ultima } : null }));
  t.push(tile({ icono: 'grafico', etiqueta: 'Clics · 28 días', valor: k ? num(k.mes) : null, estado:'gris',
    comparacion: k ? { delta: k.var_mes, pct: true, texto: 'frente a los 28 anteriores' } : null, contexto: k ? `Últimos 7 días: ${num(k.semana)} (${pctTxt(k.var_sem)})` : `Sin dato · ${f.gsc_nota || 'Search Console sin conectar'}`, medible: k ? 'hoy' : 'no', frescura: k ? { fuente: 'Search Console', fecha: d.seo._meta.gsc.leido } : null }));
  t.push(tile({ icono: 'ojo', etiqueta: 'Impresiones · 28 días', valor: k ? num(k.impresiones) : null, comparacion: k ? { delta: k.var_impr, pct: true, texto: 'frente a los 28 anteriores' } : null, contexto: k ? `CTR ${numD(k.ctr, 2)} % · posición ${numD(k.posicion, 1)}` : 'Sin dato · Search Console sin conectar', medible: k ? 'hoy' : 'no' }));
  const vis=f._medicionSEO?.visibilidad,historica=f.visibilidad_original?.var;
  t.push(tile({icono:'medidor',etiqueta:vis?'Visibilidad estimada · par fechado':'Visibilidad anterior · por contrastar',valor:vis?.var!==null&&vis?.var!==undefined?pctTxt(vis.var):typeof historica==='number'&&Number.isFinite(historica)?pctTxt(historica):null,
    estado:'gris',contexto:vis?`${vis.pares} pares ${vis.desde}–${vis.hasta}; estimación, no tráfico real`:'Sin cohorte/motores/fechas verificables; no acredita una caída actual ni objetivo cumplido',medible:'medias',medibleDetalle:'La configuración de ubicación/dispositivo debe contrastarse aparte'}));
  const ga = f.ga4?.actual;
  t.push(tile({ icono: 'users', etiqueta: 'Usuarios · 30 días', valor: ga ? num(ga.usuarios) : null, comparacion: ga && f.ga4.anterior ? { delta: variacion(ga.usuarios, f.ga4.anterior.usuarios), pct: true, texto: 'frente a los 30 anteriores' } : null,
    contexto: ga ? `${num(ga.conversiones)} conversiones` : 'Sin dato · Analytics sin emparejar', medible: ga ? 'hoy' : 'no', frescura: f.ga4?.hora ? { fuente: 'Analytics', fecha: f.ga4.hora } : null }));
  // sin dato: fuera de la rejilla (nada de «—» grande) y dicho en una línea debajo
  const conDato = t.filter(x => !x.classList.contains('gris') || !x.querySelector('.tv')?.textContent.startsWith('—'));
  const sinDato = [!f.reparto ? 'posiciones (sin proyecto en SE Ranking)' : null, !k ? `clics e impresiones (${f.gsc_nota || 'Search Console sin conectar'})` : null,
    f.visibilidad?.var === null || f.visibilidad?.var === undefined ? 'visibilidad' : null, !ga ? 'usuarios (Analytics sin emparejar)' : null].filter(Boolean);
  cont.append(rejillaTarjetas(conDato));
  if (sinDato.length) cont.append(vacioLinea(`Sin dato · ${sinDato.join(' · ')}`, { icono: 'plug', quien: 'Agus' }));
  if (f.alertas.length) {
    cont.append(panel({ titulo: 'Avisos guardados y cambios acreditados', icono: 'alert' },
      listaLoPrimero(f.alertas.slice(0, 7).map((a, i, l) => ({ estado: cuentagotas(a.gravedad, i, l.length), icono: a.tipo === 'clics' ? 'grafico' : a.tipo === 'visibilidad' ? 'ojo' : 'star', motivo: a.texto,
        detalle: a.tipo === 'desaparece' ? 'Puede ser desindexación o un fallo de la comprobación de SE Ranking: buscar la palabra en Google en una ventana privada.' : a.acreditada?'Cambio observado; contrastar objetivo, contexto y siguiente revisión.':'Señal anterior sin par fechado acreditado; no se exige un plazo de respuesta desde esta copia.',
        botones: [botonDeshacer({ texto: 'Hecho / no aplica', hecho: 'Marcada', soloLectura: ctx.soloLectura, alHacer: () => { ctx.rastro({ accion: 'alerta_seo_vista', objeto: `${f.cliente_id}:${a.palabra || a.tipo}`, detalle: a.texto }); return 'Queda en el rastro'; } })] })))));
  }

  // pestañas por fuente: Posiciones (SE Ranking) · Clics de Google (Search Console) · Web y ficha
  const pintarPosiciones = z => {
    z.append(renderObjetivos374(h,ctx,d.objetivos374,f.cliente_id));
    const motores=contextoMotoresSEO(f);
    z.append(panel({titulo:'Contexto de las posiciones',icono:'info',sub:'Consultas provisionales; el objetivo #1 para asesoría/gestoría o cada servicio + ciudad debe confirmarse en Prioridades por cliente.'},
      h('div',{class:'cuerpo pila'},h('p',{class:'sub'},`Lectura posiciones: ${f.seranking?.ultima||'Sin fecha'}. Orgánico y Maps no son intercambiables. La mejor de dos comprobaciones no es una posición diaria única.`),
        motores.length?motores.map(m=>h('p',{class:'sub'},`${m.principal?'Motor principal: ':'Motor configurado: '}${m.buscador||'Buscador sin dato'} · ${m.dispositivo||'Dispositivo sin dato'} · ${m.region||'Localidad sin dato'} · contexto ${m.fecha||'sin fecha'}`)):vacioLinea('Dispositivo y localidad sin metadatos en esta copia; no se infieren de la palabra, el nombre del cliente ni su dirección.',{icono:'info'}),
        h('p',{class:'sub'},'La configuración de motores no vincula por sí sola cada celda Maps a un dispositivo/localidad. No es un geogrid.'),
        h('a',{class:'bt mini',href:`#/prioridades-cliente?cliente=${encodeURIComponent(f.cliente_id)}`},'Confirmar objetivo, servicios y ciudad'))));
    const tabla15 = f.informe15.length ? tablaDensa({ filas: f.informe15, porPagina: 0, apilable: false, columnas: [
      { clave: 'k', titulo: 'Palabra', principal: true, celda: p => h('span', { style: { fontWeight: '600', display: 'inline-block', minWidth: '180px' } }, p.k) },
      { clave: 'vol', titulo: 'Búsquedas', num: true, celda: p => num(p.vol) },
      { clave: 'hoy', titulo: 'Orgánico · mejor lectura', num: true, celda: p => posCh(p.hoy) },
      { clave: 'mapa', titulo: 'Maps · observado', num: true, celda: p => posCh(p.mapa) },
      { clave: 'sem', titulo: 'Hace 7 días', num: true, celda: p => pos(p.sem) },
      { clave: 'mes', titulo: 'Hace 30 días', num: true, celda: p => pos(p.mes) },
      {clave:'d',titulo:'Cambio acreditado · 7 d',num:true,celda:p=>parPosicionSEO(p,ctx.hoy)?deltaPos(p.sem,p.hoy):h('span',{class:'sub'},'Sin comparación')},
    ] })
      : vacioLinea('Posiciones: se conecta. Este cliente no tiene proyecto en SE Ranking emparejado; sin él no hay 15 palabras del informe ni alarma de top 10.', { icono: 'star', quien: nom(ctx, f.seo_id) || 'Jerónimo' });
    let rep = null;
    if (f.reparto) {
      rep = ventanas([['top3', 'Top 3'], ['top5', 'Top 5'], ['top10', 'Top 10'], ['fuera', 'Fuera']].map(([kk, tt]) => ({ titulo: tt, valor: conteoSEO(f.reparto[kk]?.hoy)===null?'Sin dato':num(f.reparto[kk].hoy), sub: `hace 30 días: ${conteoSEO(f.reparto[kk]?.mes)===null?'Sin dato':num(f.reparto[kk].mes)}` })));
      rep = h('div', { class: 'cuerpo', style: { paddingBottom: '0' } }, rep);
    }
    const mov=f.movimientos;
    const subidas=(mov?.suben||[]).filter(x=>parPosicionSEO({...x,sem:x.antes},ctx.hoy)?.delta>0);
    const bajadas=(mov?.bajan||[]).filter(x=>parPosicionSEO({...x,sem:x.antes},ctx.hoy)?.delta<0);
    const lista = (arr, sube) => arr.length ? h('ul', { class: 'lista-i' }, arr.map(m => h('li', {}, h('span', { style: { flex: '1', minWidth: '0', overflowWrap: 'anywhere' } }, m.k), h('span', { class: 'fila', style: { gap: S[2], flexWrap: 'nowrap' } }, h('span', { class: 'sub' }, `${pos(m.antes)} →`), posCh(m.hoy)))))
      : vacioLinea('Sin movimientos comparables en esta muestra; no acredita ausencia de cambios.', { icono: sube ? 'sube' : 'baja' });
    z.append(panel({ titulo: 'Las 15 palabras del informe', icono: 'star', sub: `${d.seo._meta.informe15 || ''} Mejor posición de dos comprobaciones frente a hace 7 y 30 días (ventanas fijas de SE Ranking).`.trim() }, rep, h('div', { class: 'cuerpo' }, tabla15)));
    const configuraciones=configuracionActualMotoresSEO(f,ctx.hoy);
    if(configuraciones.length)z.append(h('details',{class:'panel',style:{padding:'12px 18px'}},
      h('summary',{style:{cursor:'pointer',minHeight:'44px',display:'flex',alignItems:'center'}},'Configuración de SERanking observada'),
      h('p',{class:'sub'},'Esta lectura describe la configuración consultada. No acredita la ciudad, el dispositivo ni el canal de las posiciones históricas, ni el objetivo contratado.'),
      configuraciones.map(m=>h('p',{class:'sub'},`Motor ${m.motor} · ${m.buscador||'Buscador sin dato'} · ${m.region||'Localidad sin dato'} · ${m.dispositivo||'Dispositivo sin dato'} · ${m.idioma||'Idioma sin dato'} · ${m.maps} · lectura ${m.fecha}`))));
    z.append(mov ? dos(
      panel({ titulo: 'Suben · 7 días', icono: 'sube', sub:`${subidas.length} filas comparables de la muestra; no inventario completo`},h('div',{class:'cuerpo'},lista(subidas,true))),
      panel({ titulo: 'Bajan · 7 días', icono: 'baja', sub:`${bajadas.length} filas comparables de la muestra; no inventario completo`},h('div',{class:'cuerpo'},lista(bajadas,false))))
      : panel({ titulo: 'Suben y bajan · 7 días', icono: 'sube' }, h('div', { class: 'cuerpo' }, vacioLinea('Se conecta: sin proyecto en SE Ranking.', { icono: 'star' }))));
  };
  const pintarClics = z => {
    if (!f.gsc) {
      z.append(panel({ titulo: 'Search Console', icono: 'grafico' }, h('div', { class: 'cuerpo' }, vacioLinea(`${f.gsc_estado === 'a_cero' ? 'Search Console a cero' : 'Search Console sin conectar'}: ${f.gsc_nota || 'sin sitio emparejado'}. Hay que dar acceso de lectura a gmb1 de RO en la propiedad del cliente.`, { icono: 'plug', quien: 'Agus' }))));
      return;
    }
    const medicion=paginasSEO(f,d.seo._meta,ctx.hoy);
    z.append(h('p',{class:'sub'},`Search Console · lectura ${medicion.lectura||'sin fecha'} · ${medicion.ventana?`${medicion.ventana.desde} a ${medicion.ventana.hasta}`:'ventana sin confirmar'} · muestra parcial; clics no son leads ni ventas.`));
    z.append(h('p',{class:'sub'},'Publicaciones y artículos, frecuencia acordada, cambios de schema y entregas: sin inventario acreditado en esta fuente. Contrastar tareas y CMS antes de afirmar publicado, optimizado o cumplido.'));
    const v = f.clics?.ventanas?.mes || [];
    z.append(panel({ titulo: 'Clics diarios desde Google · 28 días', icono: 'grafico', sub: `${v.length ? `Del ${fDiaRO(v[0])} al ${fDiaRO(v[1])}` : 'Últimos 28 días'} · ventana fija de Search Console (va 2-3 días por detrás), no cambia con un periodo` },
      h('div', { class: 'cuerpo' }, grafico({ x: f.gsc.serie.map(([x]) => x), series: [{ nombre: 'Clics', y: f.gsc.serie.map(([, y]) => y) }], alto: 200, vacio: 'Sin clics en estos 28 días' }))));
    const tablaPag = tablaDensa({ filas: medicion.filas.map(x=>({...x,u:x.url,cl:x.clics,im:x.impresiones,ps:x.posicion,ant:x.anterior})), porPagina: 15, apilable: false, columnas: [
      { clave: 'u', titulo: 'Página', principal: true, celda: x => x.enlace?h('a', { href: x.enlace, target: '_blank', rel: 'noopener', class: 'enlace', style: { overflowWrap: 'anywhere', ...TOQUE, minWidth: '180px' } }, x.u.replace(/^https?:\/\/[^/]+/, '') || '/'):h('span',{},'URL no válida para abrir') },
      { clave: 'cl', titulo: 'Clics', num: true, celda: x => num(x.cl) },
      { clave: 'im', titulo: 'Impresiones', num: true, celda: x => num(x.im) },
      { clave: 'ps', titulo: 'Posición', num: true, celda: x => numD(x.ps, 1) },
      { clave: 'ant', titulo: 'Cambio', num: true, celda: x => x.perdidos===null?h('span',{class:'sub'},'Sin comparación'):h('span',{class:'sub'},`${num(x.perdidos)} clics menos observados`) },
      { clave:'accion',titulo:'Siguiente revisión',ordenable:false,celda:x=>h('span',{style:{maxWidth:'340px',overflowWrap:'anywhere'}},x.accion) },
    ] });
    const tablaBus = tablaDensa({ filas: f.gsc.busquedas.map(([q, cl, im, ps, ant]) => ({ q, cl, im, ps, ant })), porPagina: 15, apilable: false, columnas: [
      { clave: 'q', titulo: 'Búsqueda', principal: true, celda: x => h('span', { style: { fontWeight: '600', display: 'inline-block', minWidth: '180px' } }, x.q) },
      { clave: 'cl', titulo: 'Clics', num: true, celda: x => num(x.cl) },
      { clave: 'im', titulo: 'Impresiones', num: true, celda: x => num(x.im) },
      { clave: 'ps', titulo: 'Posición', num: true, celda: x => numD(x.ps, 1) },
      { clave: 'ant', titulo: 'Antes', num: true, celda: x => (x.ant ? numD(x.ant, 1) : '—') },
    ] });
    z.append(h('div', { class: 'pila' },   // R13: dos tablas de 5 columnas, una debajo de otra (en .dos la segunda quedaba cortada)
      panel({ titulo: 'Páginas · siguiente revisión', icono: 'doc', sub: 'Primero descensos observados; después impresiones. Comparación sólo con ventana acreditada; no objetivos cumplidos.' }, h('div', { class: 'cuerpo' }, medicion.filas.length ? tablaPag : vacioLinea('Sin páginas en la muestra disponible; no acredita cero clics en todo el sitio.', { icono: 'doc' }))),
      panel({ titulo: 'Búsquedas que traen clics', icono: 'buscar', sub: 'Posición media de 28 días y la de los 28 anteriores' }, h('div', { class: 'cuerpo' }, f.gsc.busquedas.length ? tablaBus : vacioLinea('Sin búsquedas en la muestra disponible; no acredita ausencia de búsquedas o clics.', { icono: 'buscar' })))));
  };
  const pintarWeb = z => {
    z.append(dos(
      panel({ titulo: 'Su web', icono: 'mundo_web', sub: 'Una comprobación desde la IP de RO' },
        w ? h('div', { class: 'cuerpo pila' },
          h('span', { class: 'fila' }, chipEstado(w.estado, TXT_EST[w.estado]), h('span', {}, w.motivo)),
          w.comprobacion ? h('span', { class: 'sub' }, `Respuesta ${w.comprobacion.estado || '—'} · ${numD(w.comprobacion.ms / 1000, 1)} s · certificado ${w.comprobacion.cert_dias ?? '—'} días · ${fDiaHoraRO(w.comprobacion.hora)}`) : null,
          w.modular ? h('span', { class: 'sub' }, `Modular DS: ${w.modular.disponibilidad?.estado === 'up' ? 'responde desde fuera' : w.modular.disponibilidad?.estado === 'down' ? 'caída desde fuera' : 'sin monitor'} · ${w.modular.copias?.ultima_buena ? `copia buena ${fDiaRO(w.modular.copias.ultima_buena)}` : 'sin copia buena'} · ${num(w.modular.actualizaciones?.pendientes ?? 0)} actualizaciones · ${num(w.modular.vulnerabilidades?.criticas ?? 0)} fallos críticos`)
            : w.modular === undefined ? h('span', { class: 'sub' }, 'Modular sin conectar: falta la clave de solo lectura de Tomás.') : h('span', { class: 'sub' }, 'Esta web no está en Modular DS.'),
          ...w.avisos.map(a => avisoParcial(`${a.texto} Qué hacer: ${a.que_hacer}`, { titulo: a.titulo + '.' })),
          h('div', { class: 'fila' },
            h('span', { class:'sub' }, 'PageSpeed: lector preparado; piloto bloqueado por cuota. Todavía sin medición.'),
            h('a', { class: 'bt mini', href: w.url, target: '_blank', rel: 'noopener' }, icono('ext'), 'Abrir la web')))
          : h('div', { class: 'cuerpo' }, vacioLinea('Sin web registrada: el portal no tiene la web de este cliente.', { icono: 'mundo_web' }))),
      bloqueFichaGoogle(ctx, f.cliente_id, { modulo: 'seo-web' })));   // 3-oct · ficha de Google (Business Profile)
  };
  cont.append(pestanas({
    clave: `seo.detalle.${ctx.persona.id}`, activa: ctx.params?.[1]==='clics'?'clics':'pos', etiqueta: 'Fuentes del cliente',
    pestanas: [
      { id: 'pos', texto: 'Posiciones', icono: 'star', cuenta:f.alertas.filter(a=>a.tipo==='fuera_top10'&&a.acreditada===true).length, cuentaEstado: 'rojo' },
      { id: 'clics', texto: 'Clics de Google', icono: 'grafico' },
      { id: 'web', texto: 'Web y ficha', icono: 'mundo_web', cuenta: w && w.estado === 'rojo' ? 1 : 0, cuentaEstado: 'rojo' },
    ],
    pintar: (id, z) => (id === 'pos' ? pintarPosiciones(z) : id === 'clics' ? pintarClics(z) : pintarWeb(z)),
  }));

  // botones de la semana (gastan créditos → doble confirmación)
  cont.append(panel({ titulo: 'Acciones', icono: 'zap', sub: 'Estas acciones dejan un registro local. No acreditan ejecución ni confirmación de SE Ranking, ClickUp o avisos al equipo.' },
    h('div', { class: 'cuerpo fila' },
      botonConfirmar({ texto: 'Lanzar comprobación de posiciones', pregunta: 'Gasta créditos de SE Ranking. ¿Seguro?', confirmar: 'Sí, gastar', mini: true, soloLectura: ctx.soloLectura || !f.seranking,
        alConfirmar: async () => { await ctx.accion({ herramienta: 'seranking', tipo: 'comprobar_posiciones', objeto: `proyecto ${f.seranking.proyecto}`, cliente_id: f.cliente_id, texto: 'Comprobación de posiciones', vista_previa: `SE Ranking · proyecto ${f.seranking.proyecto} (${f.cliente}) · ${f.seranking.seguidas} palabras · gasta créditos` }); return 'En la cola (simulación, doble confirmación hecha)'; } }),
      botonDeshacer({ texto: 'Avisar al account', hecho: 'Account avisado', soloLectura: ctx.soloLectura,
        alHacer: async () => { await ctx.accion({ herramienta: 'app', tipo: 'aviso_account', objeto: f.cliente, cliente_id: f.cliente_id, texto: f.motivo, vista_previa: `Aviso interno al account de ${f.cliente}: «${f.motivo}».` }); return 'Registro local guardado; aviso al account sin confirmar'; } }))));
}

/** Barrido v1: enlaces sueltos en tablas y líneas de datos con zona de toque de 32 px (WCAG 2.5.8). */
const TOQUE = { minHeight: 'var(--s-8)', minWidth: 'var(--s-8)', alignItems: 'center' };

export default {
  id: 'seo-web',
  titulo: 'SEO, ficha y webs',
  grupo: 'SEO, web y redes',
  puestos_que_lo_ven: { direccion: 'todo', finanzas_direccion: 'todo', operaciones: 'todo', proyectos: 'todo', jefa_seo: 'todo', tecnico_altas: 'resumen', jefa_publicidad: 'resumen', account: 'suyo', trafficker: 'suyo', seo: 'suyo', ficha_google: 'suyo', web: 'suyo' },
  async render(cont, ctx) {
    vigilarCortes(cont);
    const oportunidadesScope332=ambitoOportunidades332(ctx)?.firma||null;
    const d = await cargar(ctx);
    d.oportunidadesScope332=oportunidadesScope332;
    if (!cont.isConnected || (ctx.vigente && !ctx.vigente())) return;
    if (d.seo._error || d.webs._error) {
      cont.append(vacio({ icono: 'alert', tono: 'aviso', titulo: 'No llegan los datos de SEO', texto: `${d.seo._error || d.webs._error}. Se generan con fuentes_seo/generar_seo.py.`, quien: 'Agus', borde: true }));
      return;
    }
    cont.append(notaCompacta336(h,'SEO · seguimiento histórico; objetivos por confirmar',h('p',{},'Las consultas de esta vista son un seguimiento histórico; no todas son objetivos confirmados. Revisa los objetivos y la evidencia de cada cliente en Prioridades por cliente. Las posiciones de Google y Maps deben contrastarse por fecha y contexto.')));
    const [id] = ctx.params;
    // R15a (A2): #/seo-web/webs/<cliente> → pestaña «Webs» con la fila de esa web resaltada
    if (id === 'webs') pintarPortada(cont, ctx, d, { webObjetivo: ctx.params[1] || '' });
    else if (id) pintarDetalle(cont, ctx, d, id);
    else pintarPortada(cont, ctx, d);
  },
};

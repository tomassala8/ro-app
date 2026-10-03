// modulos/captacion.js · M6 «Captación» · la Torre de Control de Paid dentro de la app (E5 del plan v2, 13_TORRE…).
//
// Qué pinta (orden por frecuencia: arriba lo de cada día, abajo lo de cada semana):
//   #/captacion            → cifras del día (número que manda del trafficker, techo de 35 €/lead mientras no haya
//                            objetivos D-03, rojos, gasto, leads, leads que llegan al CRM, creatividades), «Lo primero hoy»
//                            y las cuentas con filtros que se quedan. Pestañas: Cuentas · Por trafficker (Valeria) ·
//                            Creatividades · El despacho · Google Ads · Paridad con la Torre.
//   #/captacion/<cliente>  → la tarjeta del cliente (T1-T13 + M1-M9): gravedad y motivos con su cuello de botella,
//                            gasto y leads por ventanas, coste por lead con muestra mínima, coste por cita, presupuesto
//                            y ritmo, metas, campañas, serie diaria, embudo de GHL a 90 días con estancados de 72 h,
//                            avisos de integración, creatividades, quincenal preparada, historia y botones (simulación).
//
// Datos: data/captacion/captacion.json (fuentes_captacion/generar_captacion.py, solo lectura), servido RECORTADO por
// servir.py: filas por cliente visible y sin claves de dinero a quien no ve la inversión. Si el recorte genérico quita
// el dinero a un trafficker o account de SU cliente (pasa hoy: ver dudas_pintura.md D-P-CAP1), se completa con la ficha
// de E1 (/api/cliente/<id>), que sí recorta cliente a cliente.
// Botones: ctx.accion() → cola local «simulada» con vista previa. Nunca llama a Meta, GHL ni ClickUp.
// Diseño (auditoría 30, 2-oct noche): sin hoja de estilos propia; barras, embudo y ventanas son los componentes comunes;
// el resto, clases de estilos.css y tokens de la guía (--s-*, con su valor por defecto). Cifras con punto de miles; nada < 12 px.
// Tiendas online (Kiosko, decisión del coordinador 2-oct): sus «leads» de Meta son conversiones del píxel. Fuera del total de
// leads de la casa y del techo de 35 € por lead; su tarjeta lo explica.

import { duenoConexion } from './ajustes_conexiones.js';
import { motivoSinCartera } from './ficha.js';   // V2 (B-M2): el dueño de cada conexión sale de un solo sitio
import {
  h, fmt, semaforo, tile, tiles, listaLoPrimero, tablaDensa, tablaApilable, chipEstado, chipsFiltro, selectorCliente,
  vacio, botonConfirmar, avisoParcial, logoCliente, candado, panel, frescura, icono, iniciales, pestanas, graficoSerie,
  variacion, fichaCatalogo, pieFase2, copiar, avisoFlotante, listaConIcono, selloMedible, limpiaTexto,
  barraProgreso, embudoBarras, ventanas, colorCifra, cifraPrincipal, vacioLinea, menuMas, esqueleto, rejillaTarjetas,
} from '../componentes.js';

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

// R12 (A2) · periodo común SOLO donde hay dato diario: la serie de Meta por día (gasto y leads, unos 35 días).
// Lo que se juzga (crítico, techo, CRM) sigue en su ventana fija de 7 días y lo dice.
const PERIODOS_CAPTACION = ['7d', '30d', 'mes', 'ayer'];
let PERIODO = null;
/** Leads (sin tiendas) y gasto de Meta en [desde, hasta] sumando la serie diaria; completo = la serie cubre todo el tramo. */
function sumaSerie(filas, desde, hasta, inicioSerie) {
  let leads = 0, gasto = 0, conGasto = false;
  for (const c of filas) {
    if (esTienda(c)) continue;
    for (const x of c.serie || []) {
      if (x.d < desde || x.d > hasta) continue;
      leads += x.leads_meta || 0;
      if (typeof x.gasto_meta === 'number') { gasto += x.gasto_meta; conGasto = true; }
    }
  }
  return { leads, gasto: conGasto ? gasto : null, completo: !inicioSerie || desde >= inicioSerie };
}

// ------------------------------------------------------------------ vocabulario
// V2 · UNA SOLA VARA. «Crítico / Atención / Bien» es SOLO la gravedad del cliente de la verdad única (ctx.verdad(id).gravedad),
// la misma del menú, Mi día, En rojo y la ficha. El estado de la cuenta de publicidad (severidad de captación, que alimenta
// esa gravedad como «captación en crítico o atención») va con OTRO nombre: «Publicidad urgente / a vigilar / en orden».
const GRAV_CLI = {
  critico: { t: 'Crítico', e: 'rojo', i: 'fire', o: 0 },
  atencion: { t: 'Vigilar', e: 'ambar', i: 'alert', o: 1 },   // §2.1: segundo nivel = «Vigilar»
  bien: { t: 'Bien', e: 'verde', i: 'ok', o: 2 },
  '': { t: 'Sin dato', e: 'gris', i: 'vacio', o: 3 },
};
const gc = c => GRAV_CLI[c?.gravedad || ''] || GRAV_CLI[''];
const chipCli = c => chipEstado(gc(c).e, gc(c).t);
const GRAV = {   // estado de la cuenta de publicidad (no es la gravedad del cliente)
  critico: { t: 'Publicidad crítica', e: 'rojo', i: 'fire', o: 0 },   // §2.1: «urgente» solo para plazos
  atencion: { t: 'Publicidad a vigilar', e: 'ambar', i: 'alert', o: 1 },
  ok: { t: 'Publicidad en orden', e: 'verde', i: 'ok', o: 2 },
  inactivo: { t: 'Sin pauta', e: 'gris', i: 'vacio', o: 3 },
};
const chipPub = c => chipEstado(GRAV[c.severidad]?.e || 'gris', GRAV[c.severidad]?.t || 'Sin dato', { punto: false });
const CUELLO = {
  paid: { t: 'Publicidad', i: 'target', quien: 'trafficker' },
  seguimiento: { t: 'Seguimiento del despacho', i: 'phone', quien: 'account' },
  integracion: { t: 'Integración', i: 'plug', quien: 'técnico (Agus)' },
  dato: { t: 'Dato pendiente', i: 'doc', quien: 'account' },
  info: { t: 'Informativo', i: 'info', quien: '' },
};
const JEFES = ['direccion', 'finanzas_direccion', 'operaciones', 'proyectos', 'jefa_publicidad'];
const nivelTxt = n => (n === 'critico' ? 'rojo' : n === 'atencion' ? 'ambar' : 'gris');
// Números: el formateador común (punto de miles siempre y «−»). Euros con céntimos solo por debajo de 100 €.
const num = (n, d = 0) => fmt.num(n, d);
const eur = n => fmt.eur(n, n !== null && n !== undefined && Math.abs(n) < 100 && n % 1 ? 2 : 0);
const pct = n => fmt.pct(n, n !== null && n !== undefined && Math.abs(n) < 10 && n % 1 ? 1 : 0);
// gasto_texto (con euros) solo si llega entero: si el servidor ha tapado importes, mejor la frase sin cifras de dinero.
const textoMot = m => limpiaTexto(m.gasto_texto && !m.gasto_texto.includes('[importe]') ? m.gasto_texto : m.texto)
  + (m.objetivo_sin_cargar && PARAMS ? ` (techo de ${PARAMS.techo_cpl} € por lead y red de seguridad de ${PARAMS.alarma_cita} € por cita)` : '');
let PARAMS = null;                 // parámetros de la casa (no son dinero de ningún cliente)
let NOMBRE_CTX = null;             // ctx.nombre(): el nombre de la persona como en toda la app
const JEFA_CRM = 'yessica';        // si un cliente no tiene especialista de CRM asignado, la tarea va a la jefa de CRM
/** V2 (B-B10): el mismo texto en «Lo primero hoy» y en la tarjeta cuando no hay especialista de CRM. */
const crmTexto = (d, c) => (c.equipo?.crm ? nombre(d, c.equipo.crm) : `sin especialista (cubre ${nombre(d, JEFA_CRM)})`);

// ------------------------------------------------------------------ sin hoja propia: tokens y piezas pequeñas
const S = { 1: 'var(--s-1, 4px)', 2: 'var(--s-2, 8px)', 3: 'var(--s-3, 12px)', 4: 'var(--s-4, 16px)', 5: 'var(--s-5, 20px)', 6: 'var(--s-6, 24px)' };
// Sin dato: tile({ valor: null }) común (ronda 10) pinta «Sin dato» pequeño y gris, nunca un «—» de 24 px (guía 3.7).
const NOWRAP = { whiteSpace: 'nowrap', fontVariantNumeric: 'tabular-nums' };
/** «Se rompe en: …» como chip gris con icono (antes .cap-cuello a 11,5 px). */
const chipCuello = (k, conPrefijo) => h('span', { class: 'chip gris sin-punto', title: `Se rompe en: ${CUELLO[k].t}` }, icono(CUELLO[k].i, { clase: 's' }), conPrefijo ? `Se rompe en: ${CUELLO[k].t}` : CUELLO[k].t);
/** Línea de fuentes en un solo chip «Datos al día» que se despliega (guía 3.6). */
function lineaFuentes(fuentes, ...extra) {
  const lista = fuentes.filter(Boolean);
  const viejas = lista.filter(f => f.estado && f.estado !== 'ok').length;
  const pto = h('span', { 'aria-hidden': 'true', style: { width: '8px', height: '8px', borderRadius: '50%', background: viejas ? 'var(--warn)' : 'var(--good)', display: 'inline-block' } });
  return h('details', { class: 'que-es', style: { minWidth: '0' } },
    h('summary', { style: { display: 'inline-flex', alignItems: 'center', gap: S[2], minHeight: '32px' } }, pto,
      viejas ? `${viejas} ${viejas === 1 ? 'fuente con retraso' : 'fuentes con retraso'}` : 'Datos al día', h('span', { class: 'sub' }, `· ${lista.length} fuentes`)),
    h('div', { class: 'fila', style: { marginTop: S[2], gap: `${S[2]} ${S[3]}`, flexWrap: 'wrap', minWidth: '0' } }, lista.map(f => { const e = frescura(f); Object.assign(e.style, { maxWidth: '100%', whiteSpace: 'normal', height: 'auto' }); return e; }), ...extra));   // P2: el chip largo parte línea, no se sale
}
/** El contenedor es una rejilla: que ningún hijo (tabla, pestañas) estire la página en el móvil. Antes, .cap-raiz. */
function sinDesborde(raiz) {
  const fija = el => { for (const x of el.querySelectorAll(':scope > *, .pila > *, .pestana-panel > *, [role=tabpanel] > *')) x.style.minWidth = '0'; };
  fija(raiz);
  new MutationObserver(() => fija(raiz)).observe(raiz, { childList: true, subtree: true });
}
// Tiendas online: los «leads» de Meta son conversiones del píxel (compras), no contactos de un despacho.
const TIENDAS_ONLINE = new Set(['kiosko-box']);
const esTienda = c => !!c.tienda_online || TIENDAS_ONLINE.has(c.cliente_id);
const NOTA_TIENDA = 'Tienda online: los «leads» de Meta de esta cuenta son conversiones del píxel (compras y pasos de la tienda), no contactos. Por eso no cuentan en el total de leads de la casa ni se juzgan con el techo de 35 € por lead (decisión del coordinador, 2 oct).';

// ------------------------------------------------------------------ datos
async function cargar(ctx) {
  let d;
  try {
    d = await ctx.datosModulo('captacion/captacion');
  } catch (e) {
    return { error: e.message || String(e) };
  }
  if (!d || !Array.isArray(d.clientes)) return { error: 'Todavía no hay datos de captación: falta la primera recarga de Meta y GoHighLevel.' };
  try { d.carteras = (await ctx.datosModulo('verdad/clientes'))?.carteras || []; } catch { d.carteras = []; }
  const logos = new Map(ctx.clientes.map(c => [c.id, c]));
  for (const c of d.clientes) {
    const b = logos.get(c.cliente_id);
    c.logo = b?.logo || null;
    c.enCartera = !!b?.enCartera;
    c.dinero = c.gasto !== undefined || (c.solo_google && c.google_ads?.coste !== undefined);
    const v = ctx.verdad ? ctx.verdad(c.cliente_id) : null;     // V2 · una sola vara: la gravedad del cliente es la de la verdad única
    c.gravedad = v?.gravedad || null;
    c.motivos_cliente = v?.motivos || (v?.motivo ? [v.motivo] : []);
    // V2 (B-A2): «en orden» nunca va con un problema de integración (Accompany: «CRM no conectado») → «a vigilar»
    if (c.severidad === 'ok' && (c.avisos || []).some(a => a.clase_id === 'integracion')) c.severidad = 'atencion';
  }
  // Dinero de SU cliente para trafficker y account: el recorte genérico de /api/modulo lo quita (no mira el cliente).
  if (ctx.servidor) {
    const faltan = d.clientes.filter(c => !c.dinero && (c.cuenta_meta || c.google_ads) && ctx.ver({ tipo: 'inversion', cliente_id: c.cliente_id }).ok);
    await Promise.all(faltan.map(async c => {
      try { completarDinero(c, (await ctx.api(`cliente/${c.cliente_id}`)).fuentes); } catch { /* sin ficha: se queda sin dinero */ }
    }));
    d.dinero_desde_ficha = faltan.filter(c => c.dinero).length;
  }
  return d;
}

/** Rellena el dinero de una fila con la ficha de E1 (bloques meta, captacion_ghl y google_ads, ya recortados por cliente). */
function completarDinero(c, f) {
  const m = f?.fuentes?.meta?.datos, g = f?.fuentes?.captacion_ghl?.datos, ga = f?.fuentes?.google_ads?.datos;
  if (m?.gasto) {
    c.gasto = m.gasto; c.cpl = m.cpl;
    if (m.cpl_resumen) c.cpl_resumen = m.cpl_resumen;
    if (m.presupuesto) c.presupuesto_ads = m.presupuesto;
    if (Array.isArray(m.serie)) c.serie = m.serie.map(p => ({ d: p.d, gasto_meta: (p.meta || [])[0] ?? null, leads_meta: (p.meta || [])[1] ?? null }));
    if (Array.isArray(m.campanas)) c.campanas = m.campanas;
    if (Array.isArray(m.motivos)) c.motivos = mezclarTextos(c.motivos, m.motivos);
    if (Array.isArray(m.avisos)) c.avisos = mezclarTextos(c.avisos, m.avisos);
    if (c.quincenal) { c.quincenal.gasto_14d = m.gasto['14d']; c.quincenal.cpl_14d = m.cpl?.['14d']; }
    c.dinero = true;
  }
  if (g?.coste_por_cita) {
    c.coste_por_cita = { ...g.coste_por_cita, alarma_100: (g.coste_por_cita.coste_por_cita_14d || 0) > 100 };
    if (c.quincenal) c.quincenal.coste_por_cita_14d = g.coste_por_cita.coste_por_cita_14d;
  }
  if (ga?.total?.coste !== undefined && c.google_ads && !c.google_ads.parada) c.google_ads.coste = ga.total.coste;
  if (c.solo_google && c.google_ads?.coste !== undefined) c.dinero = true;
}
/** Los motivos de la ficha traen el texto con euros: se ponen como gasto_texto del motivo equivalente. */
function mezclarTextos(mios, ficha) {
  return mios.map(m => {
    if (m.gasto_texto) return m;
    const x = ficha.find(f => f.texto !== m.texto && sinEuros(f.texto) === m.texto);
    return x ? { ...m, gasto_texto: x.texto } : m;
  });
}
/** Igual que sin_euros() de generar_captacion.py: el texto sin cifras de dinero. */
function sinEuros(t) {
  return String(t).replace(/\s*\((\d[\d.,]*)\s*€ invertidos\)/g, ' con gasto').replace(/\s*\([^)]*\d[\d.,]*\s*€[^)]*\)/g, '')
    .replace(/\s+de\s+\d[\d.,]*\s*€/g, '').replace(/\d[\d.,]*\s*€/g, '…').replace(/\s{2,}/g, ' ').trim();
}

function contexto(ctx, d) {
  const puestos = ctx.persona.puestos;
  const jefe = puestos.some(p => JEFES.includes(p));
  const cps = ctx.carteraPorSilla || {};
  // R12 · la cartera sale de la verdad única (carteras[]): lo que llevas (principal) y, aparte, donde ayudas (apoyo)
  const filasV = (d.carteras || []).filter(c => c.persona_id === ctx.persona.id && ['trafficker', 'account', 'crm'].includes(c.silla));
  const principal = new Set(filasV.flatMap(c => c.principal || []));
  const apoyo = new Set(filasV.flatMap(c => c.apoyo || []).filter(id => !principal.has(id)));
  const mias = filasV.length ? principal : new Set([...(cps.trafficker || []), ...(cps.account || []), ...(cps.crm || [])]);
  const esTrafficker = puestos.includes('trafficker');
  const cp = (d.carteras_publicidad || {})[ctx.persona.id] || null;
  // V2 (B-A3): la cartera de publicidad con sus nombres, la misma cifra que Mi día y Personas (captacion.json → carteras_publicidad)
  const universo = cp ? textoCartera(cp) : (filasV.find(c => c.silla === 'trafficker')?.universo?.texto || null);
  return { jefe, mias, apoyo, universo, esTrafficker, cp, nombres: d.personas || {} };
}
/** «Tu cartera de publicidad: 19 clientes (+2 de apoyo) · 14 con cuenta de Meta · 11 con Meta encendida · 2 en crítico». */
function textoCartera(cp) {
  const pl = (n, uno, varios) => `${fmt.num(n)} ${n === 1 ? uno : varios}`;
  return `Tu cartera de publicidad: ${pl(cp.cartera, 'cliente', 'clientes')}${cp.apoyo ? ` (+${fmt.num(cp.apoyo)} de apoyo)` : ''} · ${fmt.num(cp.con_meta)} con cuenta de Meta · ${fmt.num(cp.meta_encendida)} con Meta encendida · ${fmt.plural(cp.criticos || 0, 'crítico', 'críticos')}`;
}
/** V2 (B-B9): tres «AKUA_PRECIO-01» seguidos no se distinguen: campaña · conjunto · nº del anuncio (4 últimas cifras). */
const distingue = a => [a.campana, a.conjunto ? `conjunto ${a.conjunto}` : null, a.ad_id ? `anuncio …${String(a.ad_id).slice(-4)}` : null].filter(Boolean).join(' · ');
const nombre = (d, id) => (id ? (NOMBRE_CTX ? NOMBRE_CTX(id) : (d.personas?.[id] || 'persona sin ficha')) : null);
const crmDe = c => c.equipo?.crm || JEFA_CRM;
const fuenteDe = (d, id) => {
  const f = (d.fuentes || []).find(x => x.id === id);
  if (!f) return { fuente: id, estado: 'sin datos' };
  if (!f.hora) return { fuente: f.fuente, estado: 'sin datos' };
  const edad = (Date.now() - new Date(f.hora.replace(' ', 'T'))) / 36e5;
  return { fuente: f.fuente, edad_h: Math.max(0, edad), estado: f.medicion === 'medias' ? 'viejo' : edad > 30 ? 'viejo' : 'ok' };
};

// ------------------------------------------------------------------ cálculos sobre un conjunto de cuentas
function cifras(filas, d) {
  const activas = filas.filter(c => c.meta_activa);
  const conDinero = filas.filter(c => c.dinero);
  const tiendas = filas.filter(esTienda);
  const deLeads = filas.filter(c => !esTienda(c));       // leads de la casa: sin tiendas online
  const juzg = activas.filter(c => !esTienda(c) && c.cpl_resumen?.ref !== null && c.cpl_resumen?.ref !== undefined);
  const techo = d.parametros.techo_cpl;
  // Misma definición que Salud del CRM; fuera las subcuentas sin uso (no son fugas: GAC) y las que no tienen dato.
  const conGhl = activas.filter(c => c.ghl?.conectado && c.despacho?.leads_meta_7d && !c.despacho.subcuenta_sin_uso && c.despacho.leads_ghl_7d !== null && c.despacho.leads_ghl_7d !== undefined);
  const sumMeta = conGhl.reduce((s, c) => s + (c.despacho.leads_meta_7d || 0), 0);
  const sumGhl = conGhl.reduce((s, c) => s + Math.min(c.despacho.leads_ghl_7d || 0, c.despacho.leads_meta_7d || 0), 0);
  const suma = (k, v) => conDinero.reduce((s, c) => s + ((c[k] || {})[v] || 0), 0);
  return {
    activas, conDinero,
    criticos: filas.filter(c => c.gravedad === 'critico'),          // V2: gravedad del cliente (verdad única)
    atencion: filas.filter(c => c.gravedad === 'atencion'),
    pubUrgente: filas.filter(c => c.severidad === 'critico'),       // estado de la cuenta de publicidad
    juzg, enTecho: juzg.filter(c => c.cpl_resumen.ref <= techo),
    conObjetivo: activas.filter(c => c.objetivo?.cargado),
    alarmaCita: filas.filter(c => c.coste_por_cita?.alarma_100),
    gasto7: suma('gasto', '7d'), gasto7p: suma('gasto', '7d_prev'), gastoMesAnt: suma('gasto', 'mes_anterior'),
    leads7: deLeads.reduce((s, c) => s + (c.leads?.['7d'] || 0), 0), leads7p: deLeads.reduce((s, c) => s + (c.leads?.['7d_prev'] || 0), 0),
    tiendas, conversionesTienda7: tiendas.reduce((s, c) => s + (c.leads?.['7d'] || 0), 0),
    pctCrm: sumMeta ? Math.round(sumGhl / sumMeta * 100) : null, sumMeta, sumGhl, conGhl,
    cansadas: filas.reduce((s, c) => s + (c.anuncios?.cansadas || 0), 0),
    vigilar: filas.reduce((s, c) => s + (c.anuncios?.vigilar || 0), 0),
    rechazados: filas.reduce((s, c) => s + (c.anuncios?.problemas_total || 0), 0),
    paradas: activas.filter(c => (c.gasto?.ayer === 0) || (c.cuenta_meta?.ultimo_dia_con_gasto && c.cuenta_meta.ultimo_dia_con_gasto < d.datos_hasta)),
  };
}

// ================================================================== LISTA
async function pintarLista(cont, ctx, d) {
  const K = contexto(ctx, d);
  const todas = d.clientes;
  const misFilas = todas.filter(c => K.mias.has(c.cliente_id));
  const apoyoFilas = todas.filter(c => K.apoyo?.has(c.cliente_id));
  const alcanceInicial = K.jefe || !misFilas.length ? 'todas' : 'mias';
  const resumenNivel = ctx.nivel === 'resumen';
  ctx.titulo('Captación', `${todas.filter(c => c.meta_activa).length} de ${todas.length} cuentas con pauta · datos hasta el ${fDiaRO(d.datos_hasta)} (sin el día en curso)`);

  if (!todas.length) {
    cont.append(vacio({ icono: 'target', titulo: 'No tienes cuentas de publicidad que ver', borde: true,
      texto: ctx.carteraIds?.size ? 'Ningún cliente de tu cartera tiene cuenta de Meta o Google Ads conectada. Si debería tenerla, falta emparejarla (Agus).' : motivoSinCartera(ctx),
      quien: 'Mili' }));
    return;
  }

  // ---- frescura: un solo chip compacto en la fila del alcance (guía 3.6), que despliega el detalle ----
  const fuentes = lineaFuentes([fuenteDe(d, 'meta'), fuenteDe(d, 'ghl'), fuenteDe(d, 'anuncios'),
    { fuente: 'Google Ads · muestra manual de septiembre', estado: 'viejo', fecha: '2026-10-02' }, { fuente: 'TikTok', estado: 'sin datos' }]);

  // ---- alcance: mis cuentas / toda la casa (se queda) ----
  const alcance = chipsFiltro({
    etiqueta: 'Ver', clave: `captacion.alcance.${ctx.persona.id}`, valor: alcanceInicial,
    opciones: [
      ...(misFilas.length ? [{ valor: 'mias', texto: K.esTrafficker ? 'Mis cuentas' : 'Mis clientes', icono: 'persona', cuenta: misFilas.length }] : []),
      ...(apoyoFilas.length ? [{ valor: 'apoyo', texto: 'De apoyo', icono: 'users', cuenta: apoyoFilas.length }] : []),
      { valor: 'todas', texto: K.jefe ? 'Toda la casa' : 'Todo lo que veo', icono: 'res', cuenta: todas.length },
    ],
    alCambiar: () => repintar(),
  });
  const zona = h('div', { class: 'pila', style: { gap: S[6] } });
  sinDesborde(zona);
  cont.append(h('div', { class: 'fila', style: { justifyContent: 'space-between', alignItems: 'center', gap: `${S[2]} ${S[4]}` } }, h('div', { class: 'fila', style: { gap: `${S[2]} ${S[4]}`, alignItems: 'center' } }, alcance, fuentes),
    selectorCliente({ clientes: todas.map(c => ({ id: c.cliente_id, nombre: c.nombre, logo: c.logo, responsable: nombre(d, c.equipo?.trafficker) ? `Trafficker: ${nombre(d, c.equipo.trafficker)}` : 'sin trafficker', salud: null })),
      actual: null, etiqueta: 'Abrir la tarjeta de un cliente', detalle: c => c.responsable,
      insignia: c => chipCli(todas.find(x => x.cliente_id === c.id)),
      alElegir: c => ctx.navegar(`captacion/${c.id}`) })), zona);
  // el selector arranca con el primer cliente; lo dejamos como «buscar cliente»
  const sel = cont.querySelector('.selcli .sel-bt .t');
  if (sel) sel.replaceChildren(h('b', {}, 'Abrir un cliente'), h('span', {}, 'Buscar por nombre o trafficker'));

  const repintar = () => {
    const filas = alcance.valor() === 'mias' ? misFilas : alcance.valor() === 'apoyo' ? apoyoFilas : todas;
    zona.replaceChildren();
    if (alcance.valor() === 'mias' && K.universo) zona.append(h('p', { class: 'sub', style: { margin: '0', maxWidth: '72ch' } }, `${K.universo}.${K.cp ? ' «Mis cuentas» enseña las que tienen cuenta de Meta.' : ''}${apoyoFilas.length ? ` Las de apoyo, en «De apoyo».` : ''}`));
    pintarCuerpo(zona, ctx, d, filas, K, resumenNivel, alcance.valor());
  };
  repintar();
}

function pintarCuerpo(zona, ctx, d, filas, K, resumenNivel, alcance) {
  const C = cifras(filas, d);
  const techo = d.parametros.techo_cpl;
  const verDinero = C.conDinero.length > 0;
  const nAct = C.activas.length;

  // ---- 1 · lo primero hoy (máx. 7; 4 a la vista y el resto tras «Ver más») ----
  const primeras = [];
  for (const c of [...filas].sort((a, b) => gc(a).o - gc(b).o || GRAV[a.severidad].o - GRAV[b.severidad].o)) {
    for (const m of c.motivos || []) if (m.nivel === 'critico' || (c.severidad !== 'inactivo' && m.nivel === 'atencion')) primeras.push({ c, m });
    const integ = (c.avisos || []).find(a => a.clase_id === 'integracion');
    // Fuga grande (p. ej. GAC: 101 leads en Meta y 0 en GHL) cuenta como crítica aunque la publicidad vaya bien.
    const fugaGrande = c.despacho && (c.despacho.leads_meta_7d || 0) >= 10 && (c.despacho.pct_llegan_crm ?? 100) < 50;
    if (integ && c.severidad !== 'inactivo') primeras.push({ c, m: { ...integ, nivel: fugaGrande ? 'critico' : 'atencion' } });
  }
  const vistos = new Set();
  const lista = primeras.filter(({ c, m }) => { const k = c.cliente_id + (m.clase_id || ''); if (vistos.has(k)) return false; vistos.add(k); return true; })
    .sort((a, b) => gc(a.c).o - gc(b.c).o || (a.m.nivel === 'critico' ? 0 : 1) - (b.m.nivel === 'critico' ? 0 : 1) || GRAV[a.c.severidad].o - GRAV[b.c.severidad].o).slice(0, 7);
  const A_LA_VISTA = 4;
  const loPrimero = listaLoPrimero(lista.map(({ c, m }) => ({
    // V2: el color de la fila es la gravedad del CLIENTE (verdad única); el motivo dice qué falla en la publicidad
    estado: c.gravedad ? gc(c).e : nivelTxt(m.nivel), icono: CUELLO[m.clase_id]?.i || 'alert',
    motivo: `${c.nombre} · ${({ critico: 'cliente crítico · ', atencion: 'cliente a vigilar · ', bien: 'cliente bien · ' })[c?.gravedad] || ''}${CUELLO[m.clase_id]?.t || m.clase}`,
    detalle: `${textoMot(m)}${c.equipo?.trafficker ? ` — trafficker ${nombre(d, c.equipo.trafficker)}` : ''}${c.equipo?.account ? `, account ${nombre(d, c.equipo.account)}` : ''}, CRM ${crmTexto(d, c)}`,
    botones: botonesCaso(ctx, c, d, m),
  })), { vacio: { titulo: 'Nada urgente en publicidad', porque: 'Ninguna cuenta tiene un problema de publicidad ni una fuga de leads abierta.', celebrar: true } });
  const ocultas = [...loPrimero.querySelectorAll(':scope > li')].slice(A_LA_VISTA);
  ocultas.forEach(li => { li.hidden = true; });
  const verMas = ocultas.length ? h('button', { type: 'button', class: 'bt', 'aria-expanded': 'false', on: { click: e => {
    const abrir = ocultas[0].hidden; ocultas.forEach(li => { li.hidden = !abrir; });
    e.currentTarget.setAttribute('aria-expanded', String(abrir));
    e.currentTarget.firstChild.textContent = abrir ? 'Ver menos' : `Ver ${ocultas.length} más`;
  } } }, `Ver ${ocultas.length} más`) : null;
  // orden de la guía 3.6: lo que pide acción, primero; después la cifra que manda y 3 tarjetas de apoyo
  zona.append(panel({ titulo: 'Lo primero hoy', icono: 'zap', sub: `${alcance === 'mias' ? 'Tus cuentas' : alcance === 'apoyo' ? 'Cuentas en las que ayudas' : alcance === 'trafficker' ? 'Sus cuentas' : 'Toda la casa'}: lo más grave arriba, con dónde se rompe` }, loPrimero, verMas ? h('footer', { class: 'panel-pie' }, h('span', {}, `${lista.length} casos en total`), verMas) : null));

  // ---- 2 · la cifra que manda + 3 tarjetas de apoyo ----
  // Mientras ningún cliente tenga objetivo de coste por cita, manda el techo de 35 € por lead (no un «—»).
  const pctTecho = C.juzg.length ? Math.round(C.enTecho.length / C.juzg.length * 100) : null;
  const sinObjetivo = nAct - C.conObjetivo.length;
  const principal = h('div', { class: `tile ${C.juzg.length ? semaforo(pctTecho, { verde: 70, ambar: 50 }) : 'gris'}`, role: 'listitem' },
    cifraPrincipal({
      etiqueta: `Techo de ${techo} €`,
      valor: C.juzg.length ? num(C.enTecho.length) : h('small', { class: 'dim' }, 'Sin dato'), unidad: C.juzg.length ? `de ${num(C.juzg.length)}` : null,   // barrido v1: nunca «—» de 32 px
      estado: C.juzg.length ? semaforo(pctTecho, { verde: 70, ambar: 50 }) : 'gris',
      comparacion: C.juzg.length ? `${pct(pctTecho)} de las cuentas con muestra` : 'Sin dato · ninguna cuenta con 3 leads o más',
    }),
    h('span', { class: 'tx' }, sinObjetivo ? `Sin objetivo propio en ${num(sinObjetivo)} de ${num(nAct)}: manda el techo` : 'Todas las cuentas activas tienen objetivo cargado'));
  const t = [principal];
  t.push(tile({
    icono: 'fire', etiqueta: 'Clientes críticos', valor: C.criticos.length, unidad: `de ${filas.length}`,
    estado: C.criticos.length ? 'rojo' : 'verde',   // P6: crítico = rojo, como En rojo
    comparacion: { texto: `${fmt.num(C.atencion.length)} más a vigilar · gravedad del cliente, la de toda la app` },
    medible: 'hoy', ir: 'Ver cuáles', alPulsar: () => irAPestana(zona, 'cuentas', { gravedad: 'critico' }),
  }));
  t.push(tile({
    icono: 'plug', etiqueta: 'En el CRM', valor: C.pctCrm === null ? null : pct(C.pctCrm),
    estado: C.pctCrm === null ? 'gris' : semaforo(C.pctCrm, { verde: 100, ambar: 90 }),
    comparacion: C.pctCrm === null ? { texto: 'Sin dato · ninguna cuenta con GoHighLevel y leads' } : { texto: `${num(C.sumGhl)} de ${num(C.sumMeta)} · ${C.conGhl.length} cuentas` },
    medible: 'hoy', ir: 'Ver cuáles', alPulsar: () => irAPestana(zona, 'despacho', { fuga: true }),
  }));
  if (C.pctCrm === null) t.at(-1).setAttribute('aria-label', 'Leads que llegan al CRM: sin dato. Ver cuáles');
  // Leads y gasto del periodo de arriba (serie diaria de Meta); sin periodo, la ventana fija de 7 días de siempre.
  const P = PERIODO, ini = d.ventanas?.serie?.[0];
  const hastaDato = d.datos_hasta;
  const SP = P ? sumaSerie(filas, P.desde, P.hasta > hastaDato ? hastaDato : P.hasta, ini) : null;
  const SC = P?.comp ? sumaSerie(filas, P.comp.desde, P.comp.hasta, ini) : null;
  t.push(tile({
    icono: 'users', etiqueta: P ? `Leads · ${P.nombre.toLowerCase()}` : 'Leads · 7 días', valor: num(SP ? SP.leads : C.leads7),
    unidad: verDinero ? `· ${eur(SP ? SP.gasto : C.gasto7)}` : null,
    comparacion: SP ? (SC && SC.completo ? { delta: variacion(SP.leads, SC.leads), pct: true, texto: P.comp.texto } : { texto: SC ? `sin dato antes del ${fDiaRO(ini)} para comparar` : 'sin comparar' })
      : { delta: variacion(C.leads7, C.leads7p), pct: true, texto: 'frente a la semana anterior' },
    contexto: [SP && !SP.completo ? `Solo desde el ${fDiaRO(ini)} (no hay serie antes)` : null,
      C.tiendas.length ? `De Meta, sin ${C.tiendas.map(c => c.nombre).join(', ')} (tienda online)` : (verDinero ? 'Gasto de todas las cuentas, en hora de Madrid' : null)].filter(Boolean).join(' · ') || null,
    medible: 'hoy',
  }));
  zona.append(h('section', { class: 'pila', style: { gap: S[2] }, 'aria-label': 'Cifras del día' },
    rejillaTarjetas(t.map(x => { x.setAttribute('role', 'listitem'); return x; })),
    h('p', { class: 'sub', style: { margin: '0' } }, P ? `La tarjeta de leads y gasto sigue el periodo de arriba (${P.rango}, serie diaria de Meta hasta el ${fDiaRO(d.datos_hasta)}). Lo que se juzga va en ventana fija: crítico, techo y CRM a 7 días, coste por cita a 14 días y Google Ads de septiembre.`
      : 'Ventanas fijas: leads y gasto de los últimos 7 días frente a los 7 anteriores, coste por cita a 14 días y Google Ads de septiembre.')));
  zona.lastChild.firstChild.setAttribute('role', 'list');
  const avisoObjetivo = !resumenNivel && C.conObjetivo.length === 0 && nAct
    ? `Ningún cliente tiene cargado su objetivo de coste por cita ni de coste por lead. Hasta que el account lo cargue en el alta, se juzga con el techo general de ${techo} € por lead y con la red de seguridad de ${d.parametros.alarma_cita} € por cita; cada tarjeta de cliente lleva el aviso «objetivo sin cargar».` : null;

  // ---- 3 · pestañas (lo de cada día primero; Valeria y la paridad, abajo del todo) ----
  const pest = [
    { id: 'cuentas', texto: 'Cuentas', icono: 'res', cuenta: C.criticos.length, cuentaEstado: 'rojo' },   // críticos = gravedad del cliente
    ...(K.jefe || ctx.persona.puestos.includes('jefa_publicidad') ? [{ id: 'equipo', texto: 'Por trafficker', icono: 'eq' }] : []),
    { id: 'creatividades', texto: 'Creatividades', icono: 'spark', cuenta: C.cansadas + C.rechazados, cuentaEstado: 'rojo' },
    { id: 'despacho', texto: 'El despacho', icono: 'phone', cuenta: filas.filter(c => c.cuello?.includes('seguimiento')).length, cuentaEstado: 'rojo' },
    { id: 'google', texto: 'Google Ads', icono: 'globe' },
    ...(K.jefe ? [{ id: 'torre', texto: 'Paridad con la Torre', icono: 'check' }] : []),
  ];
  const caja = pestanas({
    pestanas: pest, clave: 'captacion.pestana', etiqueta: 'Secciones de captación',
    pintar: (id, el) => ({ cuentas: pCuentas, equipo: pEquipo, creatividades: pCreatividades, despacho: pDespacho, google: pGoogle, torre: pTorre })[id](el, ctx, d, filas, C, K),
  });
  caja.id = 'cap-pestanas';
  caja.ids = pest.map(p => p.id);
  zona.append(caja);

  // ---- 4 · cómo se mide (plegado al pie, con el aviso de objetivos y la regla de crítico) ----
  const inds = ['trafficker.de_cuentas_con_coste_por_cita_en_objetivo_el_que', 'trafficker.coste_por_lead_frente_al_objetivo_del_cliente', 'trafficker.leads_que_llegan_al_crm', 'trafficker.creatividad_cansada', 'jefa_publicidad.cuentas_en_rojo_por_trafficker']
    .map(id => ctx.indicador(id)).filter(Boolean);
  zona.append(h('details', { class: 'panel', style: { padding: '0' } },
    h('summary', { style: { padding: `${S[4]} ${S[5]}`, cursor: 'pointer', fontWeight: '700', display: 'flex', gap: S[2], alignItems: 'center', minHeight: '44px' } }, icono('medidor'), 'Cómo se mide cada cifra'),
    h('div', { class: 'cuerpo pila', style: { gap: S[3] } },
      avisoObjetivo ? avisoParcial(avisoObjetivo, { titulo: 'Objetivo sin cargar.' }) : null,
      h('p', { class: 'sub', style: { margin: '0' } }, 'Crítico, Atención y Bien son la gravedad del cliente: la misma en toda la app (menú, Mi día, En rojo y ficha). Un problema de publicidad cuenta en ella como «atención».'),
      h('p', { class: 'sub', style: { margin: '0' } }, `«Publicidad urgente» si: el lead cuesta 1,5 veces el máximo, 7 días sin leads gastando, el coste sube un 50 % o más, leads parados o la cuenta sin pagar. El techo cuenta solo cuentas con 3 leads o más${C.tiendas.length ? ' y sin tiendas online' : ''}. «Leads que llegan al CRM» son los contactos nuevos de la subcuenta en 7 días, la misma cifra que Salud del CRM.`),
      inds.length ? h('div', { class: 'rejilla' }, inds.map(i => fichaCatalogo(i, {
        valor: i.id.includes('en_objetivo') ? null : i.id.includes('leads_que_llegan') ? (C.pctCrm ?? null) : i.id.includes('cansada') ? C.cansadas : i.id.includes('rojo_por') ? null : (C.juzg.length ? `${C.enTecho.length}/${C.juzg.length}` : null),
        unidad: i.id.includes('leads_que_llegan') ? '%' : null,
      }))) : null)));
  const fase2 = (ctx.indicadores() || []).filter(i => i.modulo === 'captacion');
  const pie = pieFase2(fase2);
  if (pie) zona.append(pie);
}

/** Botones de un caso de «Lo primero hoy»: uno principal («Abrir tarjeta») y el resto en el menú «⋯»
 *  (Meta o GoHighLevel en otra pestaña, y la tarea al CRM con su confirmación). Antes eran 3 botones por caso. */
function botonesCaso(ctx, c, d, m) {
  const hueco = h('span', { class: 'fila', style: { gap: S[2] } });
  const items = [];
  if (c.cuenta_meta?.enlace && m.clase_id === 'paid') items.push({ texto: 'Abrir en Meta', icono: 'ext', alPulsar: () => window.open(c.cuenta_meta.enlace, '_blank', 'noopener') });
  if (c.ghl?.enlace && m.clase_id !== 'paid') items.push({ texto: 'Abrir en GoHighLevel', icono: 'ext', alPulsar: () => window.open(c.ghl.enlace, '_blank', 'noopener') });
  items.push({ texto: `Tarea al CRM (${nombre(d, crmDe(c))})`, icono: 'check', alPulsar: () => {
    const b = botonTarea(ctx, c, d, crmDe(c), `Tarea al CRM (${nombre(d, crmDe(c))})`, `${c.nombre}: ${textoMot(m)}`);
    hueco.replaceChildren(b);
    b.querySelector('button')?.click();           // abre la pregunta «¿Crear tarea…?» con Sí / No
  } });
  return [
    h('a', { class: 'bt mini pri', href: `#/captacion/${c.cliente_id}` }, icono('target'), 'Abrir tarjeta'),
    menuMas({ texto: '⋯', etiqueta: `Más acciones de ${c.nombre}`, items }),
    hueco,
  ];
}

/** Cambia de pestaña y, si hace falta, aplica un filtro de la pestaña de cuentas. */
function irAPestana(zona, id, filtro) {
  const caja = zona.querySelector('#cap-pestanas');
  if (!caja) return;
  if (filtro) try { sessionStorage.setItem('captacion.filtro', JSON.stringify(filtro)); } catch { /* nada */ }
  if (id === caja.activa()) {           // misma pestaña: se repinta para aplicar el filtro
    const otra = (caja.ids || []).find(x => x !== id);
    if (otra) caja.elegir(otra);
  }
  caja.elegir(id);
  caja.scrollIntoView({ behavior: 'smooth', block: 'start' });
}
function filtroPendiente() {
  try { const f = sessionStorage.getItem('captacion.filtro'); sessionStorage.removeItem('captacion.filtro'); return f ? JSON.parse(f) : null; } catch { return null; }
}

// ------------------------------------------------------------------ pestaña · cuentas (T1-T5, T13)
function pCuentas(el, ctx, d, filas, C, K) {
  const f = filtroPendiente();
  const n = k => filas.filter(c => (c.gravedad || 'sin') === k).length;
  const chipsG = chipsFiltro({
    etiqueta: 'Gravedad del cliente', clave: f ? null : 'captacion.gravedad.v2', valor: f?.gravedad ?? (f ? '' : undefined),
    opciones: [{ valor: '', texto: 'Todas', cuenta: filas.length }, ...['critico', 'atencion', 'bien'].map(k => ({ valor: k, texto: GRAV_CLI[k].t, icono: GRAV_CLI[k].i, cuenta: n(k), cuentaEstado: k === 'critico' ? 'rojo' : null })),
      ...(n('sin') ? [{ valor: 'sin', texto: 'Sin dato', icono: 'vacio', cuenta: n('sin') }] : [])],
    alCambiar: () => pintar(),
  });
  const chipsC = chipsFiltro({
    etiqueta: 'Dónde se rompe', clave: 'captacion.cuello', multiple: true,
    opciones: ['paid', 'seguimiento', 'integracion'].map(k => ({ valor: k, texto: CUELLO[k].t, icono: CUELLO[k].i, cuenta: filas.filter(c => c.cuello?.includes(k)).length })),
    alCambiar: () => pintar(),
  });
  const chipsP = chipsFiltro({
    etiqueta: 'Plataforma', clave: 'captacion.plataforma',
    opciones: [{ valor: '', texto: 'Todas' }, { valor: 'meta', texto: 'Meta', cuenta: filas.filter(c => c.plataformas?.includes('meta')).length },
      { valor: 'google', texto: 'Google Ads', cuenta: filas.filter(c => c.plataformas?.includes('google')).length }, { valor: 'tiktok', texto: 'TikTok', cuenta: 0 }],
    alCambiar: () => pintar(),
  });
  const caja = h('div');
  const techo = d.parametros.techo_cpl;
  // Móvil (< 641 px): los filtros (chips y desplegables de la tabla) van en un plegable de una fila «Filtros (n activos)».
  const movil = typeof matchMedia === 'function' && matchMedia('(max-width: 640px)').matches;
  const hueSel = h('div', { class: 'fila', style: { gap: S[2] } });
  const resumen = h('span', {}, 'Filtros');
  const contarActivos = () => {
    const sel = [...caja.querySelectorAll('.tabla-ctl select'), ...hueSel.querySelectorAll('select')].filter(x => x.value).length;
    const n = (chipsG.valor() ? 1 : 0) + chipsC.valor().length + (chipsP.valor() ? 1 : 0) + sel;
    resumen.textContent = n ? `Filtros (${n} ${n === 1 ? 'activo' : 'activos'})` : 'Filtros';
  };
  const pintar = () => {
    const g = chipsG.valor(), cu = chipsC.valor(), p = chipsP.valor();
    let base = filas.filter(c => (!g || (c.gravedad || 'sin') === g) && (!cu.length || cu.every(k => c.cuello?.includes(k))) && (!p || c.plataformas?.includes(p)));
    if (f?.aviso === 'objetivo') base = base.filter(c => c.meta_activa && !c.objetivo?.cargado);
    const filasT = base.map(c => ({
      ...c, grav: gc(c).o * 10 + GRAV[c.severidad].o, pub: GRAV[c.severidad].o, motivo: (c.motivos || [])[0] ? textoMot(c.motivos[0]) : ((c.avisos || []).find(a => a.clase_id === 'integracion') ? textoMot(c.avisos.find(a => a.clase_id === 'integracion')) : ''),
      trafficker: nombre(d, c.equipo?.trafficker) || 'sin trafficker', account: nombre(d, c.equipo?.account) || 'sin account',
      leads7: c.leads?.['7d'] ?? null, gasto7: c.gasto?.['7d'] ?? null, cplref: c.cpl_resumen?.ref ?? null, cita: c.coste_por_cita?.coste_por_cita_14d ?? null,
    }));
    caja.replaceChildren(tablaDensa({
      filas: filasT, orden: { clave: 'grav', dir: 'asc' }, porPagina: 12,
      buscar: { campos: ['nombre', 'trafficker', 'account', 'motivo'], placeholder: 'Buscar cliente, trafficker o motivo' },
      filtros: [{ clave: 'trafficker', titulo: 'Trafficker' }, { clave: 'account', titulo: 'Account' }],
      columnas: [
        { clave: 'nombre', titulo: 'Cliente', principal: true, celda: c => h('span', { class: 'celda-cli' }, logoCliente(c), c.nombre, c.nuevo ? chipEstado('azul', 'nuevo') : null, esTienda(c) ? h('span', { class: 'chip gris sin-punto', title: NOTA_TIENDA }, 'tienda online') : null) },
        { clave: 'grav', titulo: 'Gravedad del cliente', celda: c => chipCli(c) },
        { clave: 'pub', titulo: 'Publicidad', celda: c => chipPub(c) },
        { clave: 'motivo', titulo: 'Por qué', ordenable: false, celda: c => c.motivo ? h('span', { style: { display: 'grid', gap: S[1], minWidth: '240px' } }, h('span', {}, c.motivo),
          h('span', { class: 'fila', style: { gap: S[1] } }, (c.cuello || []).map(k => chipCuello(k)))) : h('span', { class: 'sub' }, c.meta_activa ? 'Publicidad sin motivos' : 'Sin pauta activa') },
        { clave: 'trafficker', titulo: 'Trafficker', celda: c => c.equipo?.trafficker ? h('span', { class: 'fila', style: { gap: S[2], flexWrap: 'nowrap' } }, h('span', { class: 'av s', 'aria-hidden': 'true' }, iniciales(c.trafficker)), c.trafficker) : chipEstado('ambar', 'sin trafficker') },
        { clave: 'leads7', titulo: 'Leads · gasto 7 d', num: true, celda: c => c.leads7 === null ? '—' : h('span', { style: { display: 'inline-grid', justifyItems: 'end', gap: S[1] } }, h('span', { style: NOWRAP, title: esTienda(c) ? 'Conversiones del píxel (tienda online)' : null }, num(c.leads7), ' ', deltaMini(c.leads?.['7d'], c.leads?.['7d_prev'])), h('span', { class: 'sub', style: NOWRAP }, esTienda(c) ? 'conversiones' : c.dinero ? eur(c.gasto7) : 'gasto no visible')) },
        { clave: 'cplref', titulo: 'Coste por lead', num: true, celda: c => celdaCpl(c, techo) },
        { clave: 'cita', titulo: 'Por cita 14 d', num: true, celda: c => celdaCita(c, d) },
      ],
      alPulsar: c => ctx.navegar(`captacion/${c.cliente_id}`),
      etiquetaFila: c => `${c.nombre}: cliente ${gc(c).t.toLowerCase()}, ${GRAV[c.severidad].t.toLowerCase()}. ${c.motivo}. Abrir tarjeta`,
      vacio: { titulo: 'Ninguna cuenta con estos filtros', porque: 'Cambia la gravedad o quita un filtro.' },
    }));
    if (movil) {
      const sels = [...caja.querySelectorAll('.tabla-ctl label')].filter(l => l.querySelector('select'));
      hueSel.replaceChildren(...sels);
      for (const sl of hueSel.querySelectorAll('select')) sl.addEventListener('change', contarActivos);
    }
    contarActivos();
  };
  pintar();
  const filtros = [chipsG, h('div', { class: 'fila', style: { gap: S[4] } }, chipsC, chipsP)];
  el.append(h('div', { class: 'panel' },
    h('div', { class: 'cuerpo pila', style: { gap: S[2] } },
      ...(movil ? [h('details', { class: 'que-es' },
        h('summary', { style: { display: 'flex', alignItems: 'center', gap: S[2], minHeight: '44px', fontWeight: '600' } }, icono('filtro', { clase: 's' }), resumen),
        h('div', { class: 'pila', style: { gap: S[2], marginTop: S[2] } }, ...filtros, hueSel))] : filtros),
      f?.aviso === 'objetivo' ? avisoParcial('Solo las cuentas activas sin objetivo de coste por cita cargado. Vuelve a «Captación» para quitar el filtro.', { tipo: 'info' }) : null),
    caja));
}
function deltaMini(a, b) {
  const v = variacion(a, b);
  if (v === null) return null;
  return h('span', { class: 'sub', title: 'Frente a los 7 días anteriores' }, `${v > 0 ? '▲' : v < 0 ? '▼' : '='} ${num(Math.abs(v))} %`);
}
function celdaCpl(c, techo) {
  if (!c.dinero) return candado('—');
  const r = c.cpl_resumen || {};
  if (r.ref === null || r.ref === undefined) return h('span', { class: 'sub', title: c.muestra?.nota || '' }, c.meta_activa ? 'sin muestra' : '—');
  if (esTienda(c)) return h('span', { style: { display: 'inline-grid', justifyItems: 'end', gap: S[1] }, title: NOTA_TIENDA }, h('span', { style: NOWRAP }, eur(r.ref)), h('span', { class: 'sub' }, 'por conversión · sin techo'));
  // Color único de la app para el coste por lead (colorCifra); con objetivo propio cargado, contra su objetivo.
  const obj = c.objetivo?.cpl_objetivo;
  const e = obj ? semaforo(r.ref, { verde: obj, ambar: obj * 1.5, mejorSi: 'bajo' }) : colorCifra('coste_lead', r.ref);
  return h('span', { style: { display: 'inline-grid', justifyItems: 'end', gap: S[1] } }, chipEstado(e, eur(r.ref)),
    h('span', { class: 'sub' }, `${r.ref_base}${r.fiable ? '' : ' · poca muestra'}`));
}
function celdaCita(c, d) {
  if (!c.dinero) return candado('—');
  const v = c.coste_por_cita?.coste_por_cita_14d;
  if (v === null || v === undefined) return h('span', { class: 'sub', title: c.coste_por_cita?.nota || '' }, c.meta_activa ? (c.ghl?.conectado ? 'sin citas' : 'sin GHL') : '—');
  return chipEstado(v > d.parametros.alarma_cita ? 'rojo' : v > d.parametros.arranque_cita ? 'ambar' : 'verde', eur(v));
}

// ------------------------------------------------------------------ pestaña · por trafficker (M8 · vista de Valeria)
function pEquipo(el, ctx, d, filas) {
  const por = new Map();
  for (const c of filas) {
    const t = c.equipo?.trafficker || '—';
    if (!por.has(t)) por.set(t, []);
    por.get(t).push(c);
  }
  const [verde, ambar] = d.parametros.rojos_trafficker;
  const filasT = [...por.entries()].map(([t, cs]) => {
    const Ct = cifras(cs, d);
    return {
      id: t, nombre: t === '—' ? 'Sin trafficker asignado' : nombre(d, t), cuentas: cs.length, activas: Ct.activas.length, cp: (d.carteras_publicidad || {})[t] || null,
      rojos: Ct.criticos.length, atencion: Ct.atencion.length, gasto7: Ct.conDinero.length ? Ct.gasto7 : null, gastoMes: Ct.conDinero.length ? Ct.gastoMesAnt : null,
      techo: Ct.juzg.length ? Math.round(Ct.enTecho.length / Ct.juzg.length * 100) : null, techoTxt: Ct.juzg.length ? `${Ct.enTecho.length} de ${Ct.juzg.length}` : '—',
      cansadas: Ct.cansadas, rechazados: Ct.rechazados, objetivos: `${Ct.conObjetivo.length} de ${Ct.activas.length}`,
    };
  }).sort((a, b) => b.rojos - a.rojos || b.activas - a.activas);
  const total = cifras(filas, d);

  el.append(tiles([
    tile({ icono: 'eq', etiqueta: 'Traffickers con 5 o más cuentas en rojo', valor: filasT.filter(x => x.id !== '—' && x.rojos >= ambar + 1).length, unidad: `de ${filasT.filter(x => x.id !== '—').length}`,
      estado: filasT.some(x => x.id !== '—' && x.rojos > ambar) ? 'rojo' : filasT.some(x => x.id !== '—' && x.rojos > verde) ? 'ambar' : 'verde',
      contexto: `Verde ≤ ${verde} · ámbar ${verde + 1}-${ambar} · rojo ≥ ${ambar + 1} cuentas críticas por trafficker`, medible: 'hoy', frescura: fuenteDe(d, 'meta') }),
    total.conDinero.length ? tile({ icono: 'cartera', etiqueta: 'Inversión gestionada · septiembre', valor: eur(total.gastoMesAnt), comparacion: { texto: `${eur(total.gasto7)} en los últimos 7 días` },
      contexto: 'Solo Meta. Google Ads va aparte (muestra manual) hasta la clave de Windsor.', medible: 'medias', medibleDetalle: 'Falta Google Ads y TikTok', frescura: fuenteDe(d, 'meta') }) : null,
    tile({ icono: 'flag', etiqueta: 'Cuentas paradas sin saberlo', valor: total.paradas.length, unidad: `de ${total.activas.length} activas`,
      estado: total.paradas.length ? 'rojo' : 'verde', contexto: 'Con pauta en la semana y sin gasto ayer o desde antes del último día con datos.', medible: 'hoy', frescura: fuenteDe(d, 'meta') }),
    tile({ icono: 'rocket', etiqueta: 'Arranques con ganador en el mes 1', valor: (() => { const n = filas.filter(c => c.nuevo && c.meta_activa); return n.length ? `${n.filter(c => c.anuncios?.ganadoras).length} de ${n.length}` : null; })(),
      estado: 'gris', contexto: 'En el arranque, 3 contactos o más a 45 € o menos.', medible: 'hoy', frescura: fuenteDe(d, 'anuncios') }),
  ].filter(Boolean)));

  el.append(panel({ titulo: 'Cuentas en rojo por trafficker', icono: 'eq', sub: 'Pulsa una fila para ver sus cuentas. Responsable = tabla de asignaciones (no el «PM» escrito a mano de la Torre).' },
    tablaApilable({
      filas: filasT,
      columnas: [
        { clave: 'nombre', titulo: 'Trafficker', principal: true, celda: x => h('span', { class: 'fila', style: { gap: S[2], flexWrap: 'nowrap' } }, h('span', { class: 'av s', 'aria-hidden': 'true' }, iniciales(x.nombre)), x.nombre) },
        // V2 (B-A3): la misma cartera con nombre que Mi día y Personas (carteras_publicidad)
        { clave: 'cuentas', titulo: 'Cartera', num: true, celda: x => (x.cp ? h('span', { style: { display: 'inline-grid', justifyItems: 'end' } }, `${x.cp.cartera} clientes${x.cp.apoyo ? ` + ${x.cp.apoyo} de apoyo` : ''}`, h('small', { class: 'sub' }, `${x.cp.con_meta} con Meta · ${x.cp.meta_encendida} encendidas`)) : `${x.activas} encendidas de ${x.cuentas}`) },
        { clave: 'rojos', titulo: 'Críticos', num: true, celda: x => chipEstado(x.id === '—' ? 'gris' : x.rojos > ambar ? 'rojo' : x.rojos > verde ? 'ambar' : 'verde', `${x.rojos}${x.atencion ? ` · +${x.atencion} a vigilar` : ''}`) },
        { clave: 'techo', titulo: `En el techo de ${d.parametros.techo_cpl} €`, num: true, celda: x => x.techoTxt },
        { clave: 'gasto7', titulo: 'Gasto 7 d', num: true, celda: x => (x.gasto7 === null ? candado('—') : eur(x.gasto7)) },
        { clave: 'gastoMes', titulo: 'Septiembre', num: true, celda: x => (x.gastoMes === null ? candado('—') : eur(x.gastoMes)) },
        { clave: 'cansadas', titulo: 'Anuncios', num: true, celda: x => `${x.cansadas} cansados · ${x.rechazados} rechazados` },
        { clave: 'objetivos', titulo: 'Objetivo cargado', num: true },
      ],
      alPulsar: x => { try { sessionStorage.setItem('captacion.filtro', JSON.stringify({ trafficker: x.id })); } catch { /* */ } ctx.navegar(`captacion/~trafficker/${x.id}`); },
      etiquetaFila: x => `${x.nombre}: ${fmt.plural(x.rojos, 'cuenta crítica', 'cuentas críticas')}. Ver sus cuentas`,
    })));

  // comparativa por nicho
  const nichos = new Map();
  for (const c of filas.filter(x => x.meta_activa)) {
    const k = c.nicho || 'Sin nicho';
    if (!nichos.has(k)) nichos.set(k, []);
    nichos.get(k).push(c);
  }
  const filasN = [...nichos.entries()].map(([k, cs]) => {
    const g = cs.filter(c => c.dinero).reduce((s, c) => s + (c.gasto?.['7d'] || 0), 0), l = cs.reduce((s, c) => s + (c.leads?.['7d'] || 0), 0);
    return { nicho: k, cuentas: cs.length, nombres: cs.map(c => c.nombre).join(', '), leads: l, cpl: cs.some(c => c.dinero) && l ? g / l : null, dinero: cs.some(c => c.dinero) };
  }).sort((a, b) => b.leads - a.leads);
  el.append(h('div', { class: 'dos' },
    panel({ titulo: 'Comparativa por nicho · 7 días', icono: 'capas', sub: 'Solo cuentas con pauta activa. El nicho sale de la descripción del cliente.' },
      tablaApilable({ filas: filasN, columnas: [
        { clave: 'nicho', titulo: 'Nicho', principal: true, celda: x => h('span', { style: { display: 'grid' } }, h('b', {}, x.nicho), h('small', { class: 'sub' }, x.nombres)) },
        { clave: 'cuentas', titulo: 'Cuentas', num: true },
        { clave: 'leads', titulo: 'Leads', num: true, celda: x => num(x.leads) },
        { clave: 'cpl', titulo: 'Coste por lead', num: true, celda: x => (x.dinero ? eur(x.cpl) : candado('—')) },
      ] })),
    pAuditoria(ctx, d, filas)));
}

/** Auditoría semanal: el trafficker apunta cortar / escalar / no tocar por cuenta (simulación, rastro). */
function pAuditoria(ctx, d, filas) {
  const activas = filas.filter(c => c.meta_activa);
  const lista = h('div', { class: 'pila', style: { gap: S[2] } });
  const hechas = h('div');
  const cargarHechas = async () => {
    if (!ctx.servidor) { hechas.replaceChildren(h('p', { class: 'sub' }, 'Sin servidor: las decisiones quedan solo en el rastro de esta sesión.')); return; }
    try {
      const r = await ctx.api('acciones?modulo=captacion');
      const semana = (r.acciones || []).filter(a => a.tipo === 'auditoria_semanal');
      hechas.replaceChildren(listaConIcono(semana.slice(0, 6).map(a => ({ icono: 'check', estado: 'verde', texto: `${a.objeto} · ${a.texto}`, extra: `${nombre(d, a.quien) || a.quien} · ${fDiaRO(a.creada || '')}` })),
        { vacio: { icono: 'check', titulo: 'Esta semana no hay decisiones apuntadas', texto: 'Cada trafficker apunta una por cuenta el día de la auditoría.' } }));
    } catch (e) { hechas.replaceChildren(h('p', { class: 'sub' }, `No se pudieron leer: ${e.message}`)); }
  };
  for (const c of activas.slice(0, 14)) {
    lista.append(h('div', { class: 'fila', style: { justifyContent: 'space-between', borderBottom: '1px solid var(--line-soft)', paddingBottom: S[2] } },
      h('span', { class: 'celda-cli' }, logoCliente(c), c.nombre, chipCli(c)),
      h('span', { class: 'fila', style: { gap: S[1] } }, ['Cortar', 'Escalar', 'No tocar'].map(dec => botonConfirmar({
        texto: dec, mini: true, pregunta: `¿${dec} en ${c.nombre}?`, confirmar: 'Apuntar', soloLectura: ctx.soloLectura,
        alConfirmar: async () => {
          await ctx.accion({ herramienta: 'app', tipo: 'auditoria_semanal', objeto: c.nombre, cliente_id: c.cliente_id, texto: dec,
            vista_previa: `Auditoría semanal: «${dec}» en ${c.nombre}. Queda en el rastro; Valeria lo ve en su vista.` });
          cargarHechas();
          return `«${dec}» apuntado (simulación)`;
        },
      })))));
  }
  cargarHechas();
  return panel({ titulo: 'Auditoría semanal', icono: 'check', sub: 'Una decisión por cuenta activa: cortar, escalar o no tocar. Queda en el rastro (el indicador «auditoría el mismo día» todavía no se mide).' },
    h('div', { class: 'cuerpo pila' }, activas.length ? lista : vacio({ icono: 'check', titulo: 'Sin cuentas activas que auditar' }), h('h3', { class: 'titulo-seccion' }, 'Últimas decisiones'), hechas));
}

// ------------------------------------------------------------------ pestaña · creatividades (M5 · D-39, D-40, D-43)
function pCreatividades(el, ctx, d, filas) {
  const ads = [];
  for (const c of filas) for (const a of c.anuncios?.anuncios || []) ads.push({ ...a, cliente: c.nombre, cliente_id: c.cliente_id, dinero: c.dinero, logo: c.logo,
    estado: a.cansada ? 'cansada' : a.vigilar ? 'vigilar' : a.ganadora ? 'ganadora' : 'normal' });
  const prob = filas.flatMap(c => (c.anuncios?.problemas || []).map(p => ({ ...p, cliente: c.nombre, cliente_id: c.cliente_id })));
  const cnt = k => ads.filter(a => a.estado === k).length;
  const chips = chipsFiltro({
    etiqueta: 'Estado', clave: 'captacion.anuncios',
    opciones: [{ valor: 'aviso', texto: 'Con señales', icono: 'alert', cuenta: cnt('cansada') + cnt('vigilar'), cuentaEstado: 'rojo' },
      { valor: 'cansada', texto: 'Cansadas', icono: 'baja', cuenta: cnt('cansada'), cuentaEstado: 'rojo' },
      { valor: 'ganadora', texto: 'Ganadoras', icono: 'star', cuenta: cnt('ganadora') }, { valor: '', texto: 'Todas', cuenta: ads.length }],
    alCambiar: () => pintar(),
  });
  const caja = h('div');
  const pintar = () => {
    const v = chips.valor();
    const base = ads.filter(a => !v || (v === 'aviso' ? ['cansada', 'vigilar'].includes(a.estado) : a.estado === v));
    caja.replaceChildren(tablaDensa({
      filas: base, orden: { clave: 'frecuencia_7d', dir: 'desc' },
      buscar: { campos: ['nombre', 'cliente', 'campana'], placeholder: 'Buscar anuncio o cliente' },
      filtros: [{ clave: 'cliente', titulo: 'Cliente' }],
      columnas: [
        { clave: 'nombre', titulo: 'Anuncio', principal: true, celda: a => h('span', { style: { display: 'grid', gap: S[1] } }, h('b', {}, a.nombre || '—'), h('small', { class: 'sub' }, `${a.cliente} · ${distingue(a)}`)) },
        { clave: 'estado', titulo: 'Estado', celda: a => h('span', { style: { display: 'grid', gap: S[1] } },
          chipEstado(a.estado === 'cansada' ? 'rojo' : a.estado === 'vigilar' ? 'ambar' : a.estado === 'ganadora' ? 'verde' : 'gris', a.estado === 'cansada' ? 'Cansada' : a.estado === 'vigilar' ? 'Vigilar' : a.estado === 'ganadora' ? 'Ganadora' : 'Normal'),
          a.senales?.length ? h('small', { class: 'sub' }, a.senales.join(' + ')) : null) },
        { clave: 'frecuencia_7d', titulo: 'Frecuencia', num: true, celda: a => (a.frecuencia_7d === null || a.frecuencia_7d === undefined ? '—' : chipEstado(a.frecuencia_7d > 4 ? 'rojo' : a.frecuencia_7d > 3 ? 'ambar' : 'gris', num(a.frecuencia_7d, 1), { punto: false })) },
        { clave: 'ctr_7d', titulo: '% de clics', num: true, celda: a => (a.ctr_7d === undefined ? '—' : h('span', { style: NOWRAP }, `${num(a.ctr_7d, 2)} %`, a.caida_ctr_pct !== null && a.caida_ctr_pct !== undefined ? h('small', { class: 'sub' }, ` (${a.caida_ctr_pct > 0 ? '−' : '+'}${num(Math.abs(a.caida_ctr_pct))} %)`) : null)) },
        { clave: 'leads_7d', titulo: 'Leads 7 d', num: true, celda: a => num(a.leads_7d ?? null) },
        { clave: 'cpl_7d', titulo: 'Coste por lead', num: true, celda: a => (!a.dinero ? candado('—') : a.cpl_7d ? eur(a.cpl_7d) : a.cpl_30d ? h('span', {}, eur(a.cpl_30d), h('small', { class: 'sub' }, ' 30 d')) : '—') },
        { clave: 'ir', titulo: 'Abrir', ordenable: false, celda: a => (a.enlace ? h('a', { class: 'bt mini', href: a.enlace, target: '_blank', rel: 'noopener' }, icono('ext'), 'Meta') : '—') },
        { clave: 'autor', titulo: 'Autor', celda: a => (a.autor ? nombre(d, a.autor) : h('span', { class: 'dim', title: 'Iniciales del autor en el nombre del anuncio desde el próximo lanzamiento' }, 'sin autor')) },
      ],
      alPulsar: a => ctx.navegar(`captacion/${a.cliente_id}`),
      etiquetaFila: a => `${a.nombre} de ${a.cliente}: ${a.estado}. Abrir tarjeta del cliente`,
      vacio: { titulo: 'Ningún anuncio con estas señales', porque: 'Bien: ninguna creatividad necesita cambio con la regla de dos señales.', celebrar: true },
    }));
  };
  pintar();
  el.append(panel({ titulo: 'Anuncios de las cuentas activas · 7 días', icono: 'spark', sub: 'Cansada = dos señales a la vez. Ganadora = gasto ≥ 10 veces el objetivo con coste ≤ objetivo; en el arranque, 3 contactos a ≤ 45 €.' },
    h('div', { class: 'cuerpo' }, chips), caja));
  const lim = filas.filter(c => c.anuncios?.conjuntos_con_dato).map(c => ({ ...c, lim: c.anuncios.aprendizaje_limitado, con: c.anuncios.conjuntos_con_dato }));
  el.append(h('div', { class: 'dos' },
    panel({ titulo: 'Rechazados o con problemas', icono: 'alert', sub: 'Activos en los últimos 30 días o marcados hace menos de 30 días. Verde 0 · rojo alguno más de 24 h.' },
      tablaApilable({ filas: prob, columnas: [
        { clave: 'nombre', titulo: 'Anuncio', principal: true, celda: p => h('span', { style: { display: 'grid' } }, h('b', {}, p.nombre), h('small', { class: 'sub' }, p.cliente)) },
        { clave: 'estado', titulo: 'Estado', celda: p => chipEstado(p.estado === 'DISAPPROVED' ? 'rojo' : 'ambar', p.estado === 'DISAPPROVED' ? 'Rechazado' : 'Con problemas') },
        { clave: 'desde', titulo: 'Desde', celda: p => fDiaRO(p.desde) },
        { clave: 'motivo', titulo: 'Motivo de Meta', celda: p => h('span', { class: 'sub' }, (p.motivo || 'Sin motivo en la respuesta').slice(0, 140)) },
      ], vacio: { titulo: 'Ningún anuncio rechazado', texto: 'Meta no marca problemas en las cuentas activas.', tono: 'celebrar', icono: 'ok' } })),
    panel({ titulo: 'Conjuntos en aprendizaje limitado', icono: 'medidor', sub: 'Verde < 20 % · ámbar 20-40 % · rojo > 40 % de los conjuntos activos con dato de Meta.' },
      tablaApilable({ filas: lim, columnas: [
        { clave: 'nombre', titulo: 'Cliente', principal: true, celda: c => h('span', { class: 'celda-cli' }, logoCliente(c), c.nombre) },
        { clave: 'lim', titulo: 'Limitados', num: true, celda: c => { const p = Math.round(c.lim / c.con * 100); return chipEstado(p > 40 ? 'rojo' : p >= 20 ? 'ambar' : 'verde', `${c.lim} de ${c.con} · ${p} %`); } },
      ], vacio: { titulo: 'Meta no da el dato de aprendizaje', texto: 'Ningún conjunto activo trae «learning_stage_info» en estas cuentas.' } }))));
}

// ------------------------------------------------------------------ pestaña · el despacho (M6 · D-45, D-46)
function pDespacho(el, ctx, d, filas) {
  const f = filtroPendiente();
  const conGhl = filas.filter(c => c.despacho && (c.ghl?.conectado || c.meta_activa));
  const [av, aa] = d.parametros.asistencia;
  const filasT = conGhl.map(c => ({
    ...c, llegan: c.despacho.pct_llegan_crm, estanc: c.despacho.estancados_72h, cohorte: c.despacho.cohorte_30d, sinEstado: c.despacho.sin_estado_14d,
    asis: c.despacho.asistencia_14d, citas: c.despacho.citas_14d,
    fuga: c.despacho.pct_llegan_crm !== null && c.despacho.pct_llegan_crm !== undefined && c.despacho.pct_llegan_crm < 90,
    sinGhl: !c.ghl?.conectado,
  }));
  const chips = chipsFiltro({
    etiqueta: 'Mirar', clave: f ? null : 'captacion.despacho', valor: f?.fuga ? 'fuga' : undefined,
    opciones: [{ valor: '', texto: 'Todas', cuenta: filasT.length },
      { valor: 'fuga', texto: 'Leads que no llegan al CRM', icono: 'plug', cuenta: filasT.filter(x => x.fuga).length, cuentaEstado: 'rojo' },
      { valor: 'estanc', texto: 'Estancados > 72 h', icono: 'clock', cuenta: filasT.filter(x => x.estanc).length, cuentaEstado: 'rojo' },
      { valor: 'sinestado', texto: 'Citas sin estado', icono: 'cal', cuenta: filasT.filter(x => x.sinEstado).length, cuentaEstado: 'rojo' },
      { valor: 'sincita', texto: 'Sin citas en 90 días', icono: 'alert', cuenta: filasT.filter(x => x.cuello?.includes('seguimiento') && x.despacho?.sin_avance_90d !== false).length },
      { valor: 'singhl', texto: 'Sin GHL', icono: 'base', cuenta: filasT.filter(x => x.sinGhl).length }],
    alCambiar: () => pintar(),
  });
  const caja = h('div');
  const pintar = () => {
    const v = chips.valor();
    const base = filasT.filter(x => !v || (v === 'fuga' && x.fuga) || (v === 'estanc' && x.estanc) || (v === 'sinestado' && x.sinEstado) || (v === 'singhl' && x.sinGhl)
      || (v === 'sincita' && x.cuello?.includes('seguimiento') && x.despacho?.sin_avance_90d !== false));
    caja.replaceChildren(tablaDensa({
      filas: base, orden: { clave: 'llegan', dir: 'asc' },
      buscar: { campos: ['nombre'], placeholder: 'Buscar cliente' },
      columnas: [
        { clave: 'nombre', titulo: 'Cliente', principal: true, celda: c => h('span', { class: 'celda-cli' }, logoCliente(c), c.nombre) },
        { clave: 'llegan', titulo: 'Llegan al CRM · 7 d', num: true, celda: c => (c.sinGhl ? chipEstado('gris', 'sin GHL') : c.despacho.subcuenta_sin_uso ? chipEstado('ambar', 'subcuenta sin usar') : c.llegan === null || c.llegan === undefined ? h('span', { class: 'dim' }, 'sin leads') : h('span', { style: { display: 'inline-grid', justifyItems: 'end' } }, chipEstado(semaforo(c.llegan, { verde: 100, ambar: 90 }), pct(c.llegan)), h('small', { class: 'sub' }, `${num(c.despacho.leads_ghl_7d)} de ${num(c.despacho.leads_meta_7d)}`))) },
        { clave: 'estanc', titulo: 'Parados > 72 h', num: true, celda: c => (c.sinGhl ? '—' : h('span', {}, `${num(c.estanc)} de ${num(c.cohorte)}`, c.despacho.horas_max_parado ? h('small', { class: 'sub', style: { display: 'block' } }, `el más parado: ${num(Math.round(c.despacho.horas_max_parado / 24))} días`) : null)) },
        { clave: 'citas', titulo: 'Citas 14 d', num: true, celda: c => (c.sinGhl ? '—' : num(c.citas)) },
        { clave: 'sinEstado', titulo: 'Sin estado', num: true, celda: c => (c.sinGhl ? '—' : c.sinEstado ? chipEstado('rojo', num(c.sinEstado)) : '0') },
        { clave: 'asis', titulo: 'Asistencia 14 d', num: true, celda: c => (c.asis === null || c.asis === undefined ? h('span', { class: 'dim' }, '—') : chipEstado(semaforo(c.asis, { verde: av, ambar: aa }), pct(c.asis))) },
      ],
      alPulsar: c => ctx.navegar(`captacion/${c.cliente_id}`),
      etiquetaFila: c => `${c.nombre}. Abrir tarjeta`,
      vacio: { titulo: 'Nada que mirar aquí', porque: 'Ningún despacho tiene este problema.', celebrar: true },
    }));
  };
  pintar();
  el.append(panel({ titulo: 'Qué hace el despacho con los leads', icono: 'phone', sub: `Embudo de GoHighLevel a 90 días y citas de 14 días. Asistencia: verde ≥ ${av} % · ámbar ${aa}-${av - 1} % · rojo < ${aa} %. Sin datos personales de leads: solo recuentos.` },
    h('div', { class: 'cuerpo' }, chips), caja));
  el.append(avisoParcial('La velocidad de contacto y los intentos por lead (el despacho llama en 1 hora o menos y hace 4 intentos en 72 h) necesitan leer las conversaciones de cada lead en GoHighLevel. Llegan con los avisos en tiempo real de GHL. Mientras, «parados más de 72 h» hace de señal.', { titulo: 'Todavía no se mide:' }));
}

// ------------------------------------------------------------------ pestaña · Google Ads (muestra manual hasta W2)
function pGoogle(el, ctx, d, filas) {
  const g = filas.filter(c => c.google_ads);
  const muestra = g.filter(c => c.google_ads.periodo && !c.google_ads.parada);
  const paradas = g.filter(c => c.google_ads.parada);
  const fuera = g.filter(c => c.google_ads.muestra === 'fuera de Windsor');
  el.append(avisoParcial(`Google Ads llega por Windsor. ${duenoConexion('windsor').texto}. Hasta entonces se enseña la MUESTRA MANUAL de septiembre consultada el 2-oct en la sesión de Windsor: totales del mes, sin campañas ni serie diaria. Fountainhead Holding es la cuenta de Accompany. TikTok no devolvió datos.`, { titulo: 'Muestra manual.' }));
  el.append(panel({ titulo: 'Septiembre 2026 · cuentas con gasto', icono: 'globe', sub: 'Fuente: Windsor, muestra manual consultada el 2-oct (no cambia con el periodo)', acciones: chipEstado('ambar', 'muestra manual') },
    tablaApilable({ filas: muestra, columnas: [
      { clave: 'nombre', titulo: 'Cliente', principal: true, celda: c => h('span', { class: 'celda-cli' }, logoCliente(c), h('span', { style: { display: 'grid' } }, h('b', {}, c.nombre), h('small', { class: 'sub' }, c.google_ads.cuenta))) },
      { clave: 'coste', titulo: 'Coste', num: true, celda: c => (c.google_ads.coste === undefined ? candado('—') : eur(c.google_ads.coste)) },
      { clave: 'clics', titulo: 'Clics', num: true, celda: c => num(c.google_ads.clics) },
      { clave: 'imp', titulo: 'Impresiones', num: true, celda: c => num(c.google_ads.impresiones) },
      { clave: 'conv', titulo: 'Conversiones', num: true, celda: c => h('span', {}, num(c.google_ads.conversiones, c.google_ads.conversiones % 1 ? 1 : 0), c.google_ads.conversiones === 0 || (c.google_ads.clics > 400 && c.google_ads.conversiones <= 2) ? h('small', { class: 'sub', style: { display: 'block' } }, 'revisar la medición') : null) },
      { clave: 'ult', titulo: 'Último gasto', celda: c => fDiaRO(c.google_ads.ultimo_dia_con_gasto) },
    ], vacio: { titulo: 'Ninguno de tus clientes tiene Google Ads con gasto en septiembre', texto: 'La muestra manual cubre 6 cuentas de clientes.' } })));
  const otras = [
    ...paradas.map(c => ({ icono: 'flag', estado: 'ambar', texto: `${c.nombre}: campaña parada desde el ${fDiaRO(c.google_ads.ultimo_dia_con_gasto)}`, extra: 'no es fallo de conexión' })),
    ...fuera.map(c => ({ icono: 'plug', estado: 'rojo', texto: `${c.nombre}: tiene Google Ads en Looker y no está en Windsor`, extra: 'conectar en Windsor' })),
    ...(d.google_ads_sin_cliente || []).map(x => ({ icono: 'alert', estado: 'rojo', texto: `${x.nombre}: ${x.texto}`, extra: x.gasto_sep !== undefined ? `${eur(x.gasto_sep)} en septiembre` : 'sin cliente en la app' })),
  ];
  el.append(panel({ titulo: 'Paradas, sin conectar y a revisar', icono: 'alert', sub: 'Lo que confirma Windsor (2-oct)' },
    h('div', { class: 'cuerpo' }, listaConIcono(otras, { vacio: { icono: 'ok', titulo: 'Nada parado ni sin conectar entre tus clientes' } }))));
}

// ------------------------------------------------------------------ pestaña · paridad con la Torre (T1-T13 + M1-M9)
const PARIDAD = [
  ['T1', 'Tarjeta por cliente con gravedad y motivos en frases', 'hecho', 'Tarjeta del cliente y «Lo primero hoy»'],
  ['T2', 'Cuello de botella de cada motivo (publicidad, despacho, integración)', 'hecho', 'Etiqueta en cada motivo y filtro «Dónde se rompe»'],
  ['T3', 'Filtros: gravedad, pauta activa, cuello, plataforma, responsable', 'hecho', 'Chips que se quedan + «Mis cuentas» por defecto + búsqueda'],
  ['T4', 'Gasto y leads: ayer, 7 días, 7 anteriores y mes', 'medias', 'Meta sí; Google Ads solo muestra manual y TikTok sin datos'],
  ['T5', 'Coste por lead con techo y muestra mínima', 'hecho', 'Techo 35 € mientras no haya objetivo; «aún sin muestra» con menos de 4 leads'],
  ['T6', 'Presupuesto y ritmo', 'medias', 'Presupuesto de septiembre de la Torre como referencia; el de octubre, sin cargar'],
  ['T7', 'Metas del cliente', 'medias', 'Metas de septiembre de la Torre; se cargarán en el alta (día 0)'],
  ['T8', 'Campañas', 'hecho', 'Por campaña; además anuncios con frecuencia y clics'],
  ['T9', 'Serie día a día', 'hecho', 'Gasto, leads y coste por lead de 7 días con el techo marcado'],
  ['T10', 'Embudo de GoHighLevel a 90 días con estancados de 72 h', 'hecho', 'Por API directa de GHL (no por Windsor)'],
  ['T11', 'Avisos de integración y de datos', 'hecho', 'En la tarjeta; botón de tarea a Agus (simulación)'],
  ['T12', 'Frescura', 'hecho', 'Hora de cada fuente a la vista; recarga a mano hasta programarla'],
  ['T13', 'Responsable por cliente', 'hecho', 'Tabla de asignaciones (trafficker, account y CRM), no el «PM» escrito a mano'],
  ['M1', 'Coste por cita como número que manda', 'medias', 'Calculado a 14 días; se juzga cuando haya objetivo. Red de seguridad > 100 €'],
  ['M2', 'Objetivo por cliente con alarma si falta', 'hecho', 'Aviso «objetivo sin cargar» en cada tarjeta'],
  ['M3', 'Botones: pausar, presupuesto, tareas, escalar', 'medias', 'En simulación; pausar y presupuesto esperan el permiso de Meta'],
  ['M4', 'Tiempo real para lo urgente', 'no', 'Llega con los avisos de GHL y el despliegue'],
  ['M5', 'Creatividades cansadas, ganadoras y autor', 'hecho', 'Dos señales a la vez y autor por las iniciales del nombre del anuncio'],
  ['M6', 'El despacho: velocidad, intentos, sin llamar, asistencia', 'medias', 'Estancados, citas sin estado y asistencia sí; velocidad e intentos con los avisos en tiempo real de GoHighLevel'],
  ['M7', 'Quincenal preparada', 'hecho', 'Pestaña «Quincenal» de la tarjeta, con copiar'],
  ['M8', 'Vista de Valeria', 'hecho', 'Pestaña «Por trafficker» y auditoría semanal'],
  ['M9', 'Historia 7, 30 y 90 días', 'medias', 'Últimos 7, anteriores, Torre del 17-sep y hace 4 semanas; 90 días cuando haya fotos diarias'],
];
function pTorre(el, ctx, d) {
  const ESTADO = { hecho: ['verde', 'Hecho'], medias: ['ambar', 'A medias'], no: ['gris', 'Espera acceso'] };
  el.append(panel({ titulo: 'Lo que hacía la Torre y lo que añade la app', icono: 'check', sub: 'Cuando todo esté en verde y Valeria lo confirme, la Torre se archiva.' },
    tablaApilable({ filas: PARIDAD.map(([id, que, e, donde]) => ({ id, que, e, donde })), columnas: [
      { clave: 'que', titulo: 'Qué', principal: true },
      { clave: 'e', titulo: 'Estado', celda: x => chipEstado(...ESTADO[x.e]) },
      { clave: 'donde', titulo: 'Dónde y cómo' },
    ] })));
  const pt = d.paridad_torre || [];
  el.append(panel({ titulo: 'Los 14 clientes de la Torre: 17-sep frente a hoy', icono: 'hist', sub: 'Gravedad recalculada con Meta y GHL. Las diferencias se explican en la tarjeta de cada cliente (pestaña Historia).' },
    tablaApilable({ filas: pt.map(x => ({ ...x, resp: nombre(d, d.clientes.find(c => c.cliente_id === x.cliente_id)?.equipo?.trafficker) || '—' })), columnas: [
      { clave: 'nombre', titulo: 'Cliente', principal: true },
      { clave: 'torre', titulo: 'Herramienta anterior · 17-sep', celda: x => chipEstado(GRAV[x.torre]?.e || 'gris', GRAV[x.torre]?.t || x.torre) },
      { clave: 'app', titulo: 'App hoy', celda: x => (x.app ? chipEstado(GRAV[x.app].e, GRAV[x.app].t) : candado('—')) },
      { clave: 'pm', titulo: '«PM» de la Torre', celda: x => x.pm_escrito_a_mano || '—' },
      { clave: 'resp', titulo: 'Trafficker (asignaciones)' },
    ], alPulsar: x => ctx.navegar(`captacion/${x.cliente_id}`), puedePulsar: x => !!d.clientes.find(c => c.cliente_id === x.cliente_id),
    vacio: { titulo: 'Ninguno de los 14 clientes de la Torre es tuyo' } })));
}

// ================================================================== TARJETA DEL CLIENTE
function pintarTarjeta(cont, ctx, d, id) {
  const c = d.clientes.find(x => x.cliente_id === id);
  const volver = h('a', { class: 'bt', href: '#/captacion' }, icono('volver'), 'Volver a Captación');
  if (!c) {
    const base = ctx.clientes.find(x => x.id === id);
    ctx.titulo(base?.nombre || 'Captación', '');
    cont.append(vacio({ icono: base ? 'candado' : 'buscar', borde: true, accion: volver,
      titulo: base ? (base.detalle ? `${base.nombre} no tiene cuenta de publicidad conectada` : 'Esta cuenta no es de tu puesto') : 'No encuentro ese cliente',
      texto: base ? (base.detalle ? 'No aparece entre las cuentas de Meta ni en la muestra de Google Ads. Si debería tener publicidad, falta emparejar su cuenta.' : `La tarjeta de captación solo la ve quien lleva el cliente. Si necesitas algo de ${base.nombre}, habla con ${base.responsable}.`) : `No hay ningún cliente con el identificador «${id}».`,
      quien: base?.detalle ? 'Agus (emparejar la cuenta)' : base?.responsable }));
    return;
  }
  const g = GRAV[c.severidad];
  ctx.titulo(c.nombre, `Estado: ${gc(c).t} · ${g.t.toLowerCase()} · trafficker ${nombre(d, c.equipo?.trafficker) || 'sin asignar'} · datos hasta el ${fDiaRO(d.datos_hasta)}`);

  cont.append(h('div', { class: 'fila', style: { justifyContent: 'space-between' } },
    h('nav', { class: 'migas', 'aria-label': 'Migas' }, h('a', { href: '#/captacion' }, icono('target', { clase: 's' }), 'Captación'), h('span', { 'aria-hidden': 'true' }, '›'), h('span', { 'aria-current': 'page' }, c.nombre)),
    selectorCliente({ clientes: d.clientes.map(x => ({ id: x.cliente_id, nombre: x.nombre, logo: x.logo, responsable: `Trafficker: ${nombre(d, x.equipo?.trafficker) || 'sin asignar'}`, salud: null })),
      actual: c.cliente_id, etiqueta: 'Cambiar de cliente', detalle: x => x.responsable,
      insignia: x => chipCli(d.clientes.find(y => y.cliente_id === x.id)),
      alElegir: x => ctx.navegar(`captacion/${x.id}`) })));

  // ---- cabecera ----
  const eq = c.equipo || {};
  cont.append(h('section', { class: 'detalle-cab', style: { display: 'grid', gap: S[3] }, 'aria-label': 'Cabecera de la cuenta' },
    h('div', { class: 'fila', style: { gap: S[4], alignItems: 'center' } },
      logoCliente(c, 'logo-cli xl'),
      h('div', { style: { minWidth: 0, flex: '1 1 260px' } },
        h('h2', {}, c.nombre),
        h('div', { class: 'meta-linea', style: { marginTop: S[1] } },
          ...['trafficker', 'account', 'crm'].map(s => h('span', { title: eq[s + '_confianza'] ? `Asignación con confianza ${eq[s + '_confianza']} (fase 0)` : null },
            h('span', { class: 'av s', 'aria-hidden': 'true' }, iniciales(nombre(d, eq[s]) || '?')), `${s === 'crm' ? 'CRM' : s === 'account' ? 'Account' : 'Trafficker'}: ${s === 'crm' ? crmTexto(d, c) : (nombre(d, eq[s]) || 'sin asignar')}`)),
          c.nicho ? h('span', {}, icono('maletin'), c.nicho) : null),
        h('div', { class: 'fila', style: { marginTop: S[3], gap: S[2] } },
          h('span', { class: `chip ${gc(c).e}`, title: (c.motivos_cliente || []).join(' · ') || 'Gravedad única del cliente (la de toda la app)' }, `Estado: ${gc(c).t}`),
          chipPub(c),
          esTienda(c) ? chipEstado('azul', 'Tienda online', { punto: false }) : null,
          ...(c.cuello || []).map(k => chipCuello(k, true)),
          ...(c.plataformas || []).map(p => chipEstado('azul', p === 'meta' ? 'Meta' : p === 'google' ? 'Google Ads' : p, { punto: false })),
          c.cuenta_meta?.estado && c.cuenta_meta.estado !== 'activa' ? chipEstado('rojo', `Cuenta de Meta: ${c.cuenta_meta.estado}`) : null,
          !c.objetivo?.cargado && c.cuenta_meta ? chipEstado('ambar', 'Objetivo sin cargar') : null,
          c.nuevo ? chipEstado('azul', 'Cliente nuevo') : null)),
      h('div', { class: 'fila' },
        c.cuenta_meta?.enlace ? h('a', { class: 'bt', href: c.cuenta_meta.enlace, target: '_blank', rel: 'noopener' }, icono('ext'), 'Abrir en Meta') : null,
        c.ghl?.enlace ? h('a', { class: 'bt', href: c.ghl.enlace, target: '_blank', rel: 'noopener' }, icono('ext'), 'Abrir en GHL') : null,
        h('a', { class: 'bt', href: `#/en-rojo/${c.cliente_id}` }, icono('cli'), 'Ficha')))));

  // ---- motivos y avisos con su cuello (T1, T2, T11) ----
  const items = [...(c.motivos || []).map(m => ({ ...m, tipo: 'motivo' })), ...(c.avisos || []).map(a => ({ ...a, tipo: 'aviso', nivel: a.clase_id === 'integracion' ? 'atencion' : 'info' }))];
  // motivos: borde izquierdo del color de su gravedad (antes .cap-mot), texto en tinta y quién lo mueve en .sub
  const bordeMot = { rojo: 'var(--bad)', ambar: 'var(--warn)', gris: 'var(--off)' };
  const liMot = (est, ...hijos) => h('li', { style: { display: 'flex', flexWrap: 'wrap', gap: `${S[2]} ${S[3]}`, alignItems: 'flex-start', padding: `${S[3]} ${S[3]}`, border: '1px solid var(--line)', borderLeft: `3px solid ${bordeMot[est]}`, borderRadius: 'var(--r-s)', background: 'var(--card)' } }, ...hijos);
  const motivos = h('ul', { style: { display: 'grid', gap: S[2], margin: '0', padding: '0', listStyle: 'none' } }, items.length ? items.map(m => { const est = m.nivel === 'critico' ? 'rojo' : m.nivel === 'atencion' ? 'ambar' : 'gris'; return liMot(est,
    h('span', { class: `ico-c s ${est}` }, icono(CUELLO[m.clase_id]?.i || 'info')),
    h('div', { style: { flex: '1 1 220px', minWidth: '0' } }, h('div', {}, textoMot(m)), h('div', { class: 'sub', style: { marginTop: S[1] } }, `${CUELLO[m.clase_id]?.t || m.clase}${CUELLO[m.clase_id]?.quien ? ` · lo mueve: ${quienArregla(m.clase_id, c, d)}` : ''}`)),
    m.clase_id === 'integracion' ? botonTarea(ctx, c, d, 'agustina', 'Tarea a Agus', `Revisar integración: ${textoMot(m)}`) : null); }) : [liMot('gris', h('span', { class: 'ico-c s verde' }, icono('ok')), h('div', {}, 'Sin motivos: la cuenta va bien.'))]);

  // ---- cifras (T4-T7, M1) ----
  const techo = d.parametros.techo_cpl;
  const r = c.cpl_resumen || {};
  const cpc = c.coste_por_cita || {};
  const t = [];
  if (c.dinero && c.cpl) {
    t.push(tile({ icono: 'target', etiqueta: 'Coste por cita · 14 días', valor: cpc.coste_por_cita_14d === null || cpc.coste_por_cita_14d === undefined ? null : eur(cpc.coste_por_cita_14d),
      estado: cpc.coste_por_cita_14d ? (cpc.coste_por_cita_14d > d.parametros.alarma_cita ? 'rojo' : cpc.coste_por_cita_14d > d.parametros.arranque_cita ? 'ambar' : 'verde') : 'gris',
      comparacion: { texto: `${num(cpc.citas_agendadas_14d)} citas · septiembre ${cpc.mes_anterior?.coste_por_cita ? eur(cpc.mes_anterior.coste_por_cita) : 'sin citas'}` },
      contexto: c.objetivo?.cargado ? `Objetivo del cliente: ${eur(c.objetivo.coste_cita_objetivo)}` : 'Objetivo sin cargar: alarma > 100 €, 45 € solo en el arranque.',
      medible: 'medias', medibleDetalle: 'Citas = todas las del calendario de la subcuenta, no solo las que vienen de Meta', frescura: fuenteDe(d, 'ghl') }));
    if (esTienda(c)) t.push(tile({ icono: 'euro', etiqueta: `Coste por conversión · ${r.ref_base || '7 días'}`, valor: r.ref === null || r.ref === undefined ? null : eur(r.ref), estado: 'gris',
      comparacion: r.delta_pct !== null && r.delta_pct !== undefined ? { delta: r.delta_pct, pct: true, texto: 'frente a los 7 anteriores', mejorSi: 'bajo' } : null,
      contexto: 'Tienda online: no se juzga con el techo de 35 € por lead.', medible: 'hoy', frescura: fuenteDe(d, 'meta') }));
    else t.push(tile({ icono: 'euro', etiqueta: `Coste por lead · ${r.ref_base || '7 días'}`, valor: r.ref === null || r.ref === undefined ? null : eur(r.ref),
      estado: c.objetivo?.cpl_objetivo ? semaforo(r.ref, { verde: c.objetivo.cpl_objetivo, ambar: c.objetivo.cpl_objetivo * 1.5, mejorSi: 'bajo' }) : colorCifra('coste_lead', r.ref),
      comparacion: r.delta_pct !== null && r.delta_pct !== undefined ? { delta: r.delta_pct, pct: true, texto: r.fiable ? 'frente a los 7 anteriores' : 'frente a los 7 anteriores · poca muestra', mejorSi: 'bajo' } : { texto: c.muestra?.nota || '' },
      contexto: `${c.objetivo?.cargado ? 'Objetivo del cliente' : 'Techo general (objetivo sin cargar)'}: ${eur(c.objetivo?.cpl_objetivo || techo)}. Muestra mínima: 4 leads por semana.`,
      medible: 'hoy', frescura: fuenteDe(d, 'meta') }));
  } else if (c.cuenta_meta) {
    t.push(h('div', { class: 'tile gris' }, h('span', { class: 'tt' }, h('span', { class: 'ico-c gris' }, icono('euro')), h('span', {}, 'Coste por lead y por cita')), candado('La inversión la ven publicidad, operaciones y quien lleva el cliente')));
  }
  t.push(tile({ icono: 'users', etiqueta: esTienda(c) ? 'Conversiones del píxel · 7 días' : 'Leads de Meta · 7 días', valor: c.leads ? num(c.leads['7d']) : null, estado: c.leads ? '' : 'gris',
    comparacion: c.leads ? { delta: variacion(c.leads['7d'], c.leads['7d_prev']), pct: true, texto: `frente a ${num(c.leads['7d_prev'])} los 7 anteriores` } : null,
    contexto: c.leads ? `Ayer ${num(c.leads.ayer)} · septiembre ${num(c.leads.mes_anterior)}` : 'Sin cuenta de Meta', medible: 'hoy', frescura: fuenteDe(d, 'meta') }));
  if (c.despacho) {
    const p = c.despacho.pct_llegan_crm;
    const mg = c.despacho.leads_meta_7d || 0, gh = c.despacho.leads_ghl_7d;
    const masQueMeta = c.ghl?.conectado && !c.despacho.subcuenta_sin_uso && gh !== null && gh !== undefined && gh > mg;   // V2 (B-M11): «100 % · 13 de 6» no se entiende
    if (masQueMeta) t.push(tile({ icono: 'plug', etiqueta: 'Leads que llegan al CRM', valor: num(gh), unidad: 'en GHL · 7 días', estado: 'verde',
      comparacion: { texto: `${num(mg)} de Meta + ${num(gh - mg)} de otras vías (web, Instagram u otra campaña)` },
      contexto: 'Llegan todos los de Meta y algunos más. Contactos nuevos de la subcuenta en 7 días (sin los creados a mano), la misma cifra que Salud del CRM.', medible: 'hoy', frescura: fuenteDe(d, 'ghl') }));
    else t.push(tile({ icono: 'plug', etiqueta: 'Leads que llegan al CRM', valor: c.ghl?.conectado && p !== null && p !== undefined ? pct(p) : null,
      estado: !c.ghl?.conectado ? 'rojo' : p === null || p === undefined ? 'gris' : semaforo(p, { verde: 100, ambar: 90 }),
      comparacion: { texto: c.despacho.subcuenta_sin_uso ? 'Sin dato: el cliente no usa GoHighLevel' : c.ghl?.conectado ? `${num(c.despacho.leads_ghl_7d)} en GHL de ${num(c.despacho.leads_meta_7d)} en Meta (7 días)` : 'Sin subcuenta de GHL emparejada' },
      contexto: c.despacho.subcuenta_sin_uso ? `La subcuenta no se usa: ${fmt.plural(c.despacho.contactos_historia || 0, 'contacto')} en toda su historia.` : 'Contactos nuevos de la subcuenta en 7 días (sin los creados a mano), la misma cifra que Salud del CRM.', medible: 'hoy', frescura: fuenteDe(d, 'ghl') }));
  }
  const pr = c.presupuesto_ads;
  if (pr && c.dinero) {
    const e = pr.pct_consumido > pr.pct_mes * 1.15 ? 'ambar' : 'verde';
    t.push(tile({ icono: 'cartera', etiqueta: 'Presupuesto del mes', valor: `${pct(pr.pct_consumido)}`, unidad: `de ${eur(pr.aprobado)}`, estado: d.dias_transcurridos < 5 ? '' : e,
      comparacion: { texto: `mes transcurrido ${pct(pr.pct_mes)}${pr.proyeccion !== null && pr.proyeccion !== undefined && d.dias_transcurridos >= 5 ? ` · proyección ${eur(pr.proyeccion)}` : ' · sin proyección hasta el día 5'}` },
      contexto: `${pr.origen}. Septiembre real: ${eur(pr.septiembre_real?.invertido)} (${pct(pr.septiembre_real?.pct_consumido)}). Ritmo y proyección no avisan hasta el día 5.`,
      medible: 'medias', medibleDetalle: 'Presupuesto de octubre sin cargar', frescura: fuenteDe(d, 'meta') }));
  }
  if (c.google_ads?.periodo) {
    t.push(tile({ icono: 'globe', etiqueta: 'Google Ads · septiembre', valor: c.google_ads.coste === undefined ? `${num(c.google_ads.clics)} clics` : eur(c.google_ads.coste),
      comparacion: { texto: `${num(c.google_ads.conversiones, 1)} conversiones · ${num(c.google_ads.clics)} clics` }, contexto: `${c.google_ads.cuenta} · muestra manual hasta la clave de Windsor`,
      medible: 'medias', medibleDetalle: 'Muestra manual de septiembre', estado: '', frescura: { fuente: 'Windsor · muestra manual', estado: 'viejo', fecha: '2026-10-02' } }));
  }

  if (esTienda(c)) cont.append(avisoParcial(NOTA_TIENDA, { tipo: 'info', titulo: 'No cuenta en los leads de la casa.' }));
  cont.append(tiles(t));
  if (c.cuenta_meta?.convertida_a_madrid) {
    cont.append(h('p', { class: 'sub', style: { margin: '0', display: 'flex', gap: S[2], alignItems: 'flex-start' } }, icono('info', { clase: 's' }),
      h('span', {}, `Hora de Madrid: Meta cuenta esta cuenta en ${c.cuenta_meta.zona_horaria}; aquí cada día va en hora de Madrid y puede no casar al céntimo con el Administrador de anuncios.`)));
  }

  cont.append(h('div', { class: 'dos' },
    panel({ titulo: 'Qué pasa y dónde se rompe', icono: 'alert', sub: 'Motivos de la gravedad y avisos de integración y de datos' }, h('div', { class: 'cuerpo' }, motivos)),
    panel({ titulo: 'Actuar', icono: 'zap', sub: 'Simulación: queda en la cola de acciones con su vista previa. No se toca Meta, GHL ni ClickUp.' }, h('div', { class: 'cuerpo' }, acciones(ctx, c, d)))));

  // ---- pestañas de la tarjeta (diario → semanal) ----
  const p = pestanas({
    clave: 'captacion.tarjeta', etiqueta: 'Detalle de la cuenta',
    pestanas: [
      { id: 'ventanas', texto: 'Gasto y leads', icono: 'grafico' },
      { id: 'embudo', texto: 'Embudo', icono: 'cap', cuenta: c.despacho?.estancados_72h || 0, cuentaEstado: 'rojo' },
      { id: 'campanas', texto: 'Campañas', icono: 'megafono', cuenta: (c.campanas || []).length },
      { id: 'anuncios', texto: 'Creatividades', icono: 'spark', cuenta: (c.anuncios?.cansadas || 0) + (c.anuncios?.problemas_total || 0), cuentaEstado: 'rojo' },
      { id: 'metas', texto: 'Metas', icono: 'flag' },
      { id: 'quincenal', texto: 'Quincenal', icono: 'doc' },
      { id: 'historia', texto: 'Historia', icono: 'hist' },
    ],
    pintar: (pid, el) => ({ ventanas: tVentanas, embudo: tEmbudo, campanas: tCampanas, anuncios: tAnuncios, metas: tMetas, quincenal: tQuincenal, historia: tHistoria })[pid](el, ctx, d, c),
  });
  cont.append(p);
  cont.append(lineaFuentes([fuenteDe(d, 'meta'), fuenteDe(d, 'ghl'), fuenteDe(d, 'anuncios')],
    h('span', { class: 'sub' }, icono('base', { clase: 's' }), c.ghl?.subcuenta ? ` Subcuenta de GHL: ${c.ghl.subcuenta}` : ' Sin subcuenta de GHL'),
    c.cuenta_meta?.nombre_cuenta ? h('span', { class: 'sub' }, icono('target', { clase: 's' }), ` Cuenta de Meta: ${c.cuenta_meta.nombre_cuenta}`) : null));
}

function quienArregla(clase, c, d) {
  if (clase === 'paid') return nombre(d, c.equipo?.trafficker) || 'trafficker';
  if (clase === 'seguimiento') return `${nombre(d, c.equipo?.account) || 'account'} con el despacho`;
  if (clase === 'integracion') return 'Agus (técnico)';
  if (clase === 'dato') return nombre(d, c.equipo?.account) || 'account';
  return '';
}

function botonTarea(ctx, c, d, para, texto, que) {
  return botonConfirmar({
    texto, mini: true, pregunta: `¿Crear tarea a ${nombre(d, para) || para}?`, confirmar: 'Crear (simulación)', soloLectura: ctx.soloLectura,
    alConfirmar: async () => {
      await ctx.accion({ herramienta: 'clickup', tipo: 'tarea', objeto: `${c.nombre} · ${que}`.slice(0, 200), cliente_id: c.cliente_id,
        texto: `Para ${nombre(d, para) || para}: ${que}`, vista_previa: `Crearía en ClickUp una tarea para ${nombre(d, para) || para} en el proyecto de ${c.nombre}: «${que}». En el prototipo no se crea.` });
      return 'En la cola (simulación)';
    },
  });
}

function acciones(ctx, c, d) {
  const eq = c.equipo || {};
  const presu = h('input', { type: 'number', min: '0', step: '10', inputmode: 'numeric', placeholder: '€ al día', 'aria-label': 'Nuevo presupuesto diario en euros', style: { width: '112px', minHeight: '32px', padding: `${S[1]} ${S[2]}`, border: '1px solid var(--line)', borderRadius: 'var(--r-s)', background: 'var(--card)' } });
  const accionSim = (texto, pregunta, tipo, herramienta, preview, objeto) => botonConfirmar({
    texto, mini: true, pregunta, confirmar: 'Sí (simulación)', soloLectura: ctx.soloLectura,
    alConfirmar: async () => {
      const prev = typeof preview === 'function' ? preview() : preview;
      if (prev === null) throw new Error('Pon una cifra válida');
      await ctx.accion({ herramienta, tipo, objeto: objeto || c.nombre, cliente_id: c.cliente_id, texto: prev, vista_previa: prev });
      return 'En la cola (simulación)';
    },
  });
  const campanas = (c.campanas || []).filter(x => (x.leads_7d !== undefined));
  const cansadas = (c.anuncios?.anuncios || []).filter(a => a.cansada || a.vigilar);
  const grupo = (titulo, ...hijos) => h('div', { class: 'fila', style: { gap: S[2] } }, h('span', { class: 'titulo-seccion', style: { minWidth: '120px' } }, titulo), ...hijos);
  return h('div', { style: { display: 'grid', gap: S[3] } },
    grupo('Publicidad',
      accionSim(cansadas.length ? `Pausar «${(cansadas[0].nombre || '').slice(0, 22)}»` : 'Pausar un anuncio', '¿Pausar el anuncio en Meta?', 'pausar_anuncio', 'meta',
        `Pausaría en Meta el anuncio «${cansadas[0]?.nombre || 'elegido'}» de ${c.nombre}. Espera el permiso de Meta (permiso para gestionar anuncios): en el prototipo no se toca nada.`),
      h('span', { class: 'fila', style: { gap: S[2], flexWrap: 'nowrap' } }, presu, accionSim('Cambiar presupuesto', '¿Cambiar el presupuesto diario?', 'cambiar_presupuesto', 'meta',
        () => { const v = Number(presu.value); return v > 0 && v < 5000 ? `Cambiaría el presupuesto diario de ${c.nombre} a ${num(v)} € en ${campanas[0]?.campana || 'la campaña activa'}. Espera el permiso de Meta.` : null; })),
      h('span', { class: 'sub' }, 'Pausar y presupuesto: esperan el permiso de Meta')),
    grupo('Tareas',
      botonTarea(ctx, c, d, crmDe(c), eq.crm ? `Tarea al CRM (${nombre(d, eq.crm)})` : `Tarea al CRM (${nombre(d, JEFA_CRM)}, sin especialista asignado)`, c.cuello?.includes('seguimiento') ? 'Revisar el seguimiento del despacho: leads parados y citas sin estado' : 'Revisar el embudo y los recordatorios de citas'),
      eq.account ? botonTarea(ctx, c, d, eq.account, `Tarea al account (${nombre(d, eq.account)})`, c.objetivo?.cargado ? 'Hablar con el despacho de la captación' : 'Cargar el objetivo de coste por cita y por lead en la ficha del alta') : null,
      eq.account ? accionSim('Avisar de una fuga al «Mi día» del account', '¿Avisar al account?', 'aviso_fuga', 'app',
        `Pondría en el «Mi día» de ${nombre(d, eq.account)}: «${c.nombre}: ${(c.motivos || [])[0]?.texto || 'revisar el embudo'}».`) : null),
    grupo('Escalar',
      accionSim('A Valeria', '¿Escalar a Valeria?', 'escalar', 'app', `Escalaría ${c.nombre} a Valeria (jefa de publicidad) con los motivos: ${(c.motivos || []).map(m => m.texto).join(' · ') || 'sin motivos'}.`),
      accionSim('A Mili', '¿Escalar a Mili?', 'escalar', 'app', `Escalaría ${c.nombre} a Mili (operaciones). Clasificación: dónde se rompe = ${(c.cuello || []).map(k => CUELLO[k].t).join(', ') || 'sin clasificar'}.`)),
    ctx.soloLectura ? h('p', { class: 'sub' }, 'Estás en «ver como»: los botones no hacen nada.') : null);
}

// ------------------------------------------------------------------ pestañas de la tarjeta
function tVentanas(el, ctx, d, c) {
  if (!c.leads && !c.google_ads) { el.append(vacio({ icono: 'target', titulo: 'Sin datos de Meta', texto: 'Este cliente no tiene cuenta de Meta emparejada.', quien: 'Agus' })); return; }
  if (c.leads) {
    const V = [['ayer', `Ayer · ${fDiaRO(d.ventanas.ayer)}`], ['7d', '7 días'], ['7d_prev', '7 anteriores'], ['mes_anterior', 'Septiembre']];
    const pal = esTienda(c) ? 'conversiones' : 'leads', por = esTienda(c) ? 'por conversión' : 'por lead';
    el.append(ventanas(V.map(([k, t]) => ({ titulo: t, valor: `${num(c.leads[k])} ${pal}`, sub: c.dinero ? `${eur(c.gasto?.[k])} · ${c.cpl?.[k] ? `${eur(c.cpl[k])} ${por}` : `sin ${pal}`}` : 'gasto no visible' }))));
  }
  const serie = c.serie || [];
  if (serie.length) {
    const techo = c.objetivo?.cpl_objetivo || d.parametros.techo_cpl;
    const movil = serie.map((p, i) => { const v = serie.slice(Math.max(0, i - 6), i + 1); const g = v.reduce((s, x) => s + (x.gasto_meta || 0), 0), l = v.reduce((s, x) => s + (x.leads_meta || 0), 0); return { x: p.d, y: i >= 6 && l ? Math.round(g / l * 100) / 100 : null }; });
    el.append(h('div', { style: { display: 'grid', gap: S[5], gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 280px), 1fr))', alignItems: 'start', marginTop: S[4] } },
      graficoSerie({ titulo: 'Leads de Meta por día', puntos: serie.map(p => ({ x: p.d, y: p.leads_meta })) }),
      c.dinero ? graficoSerie({ titulo: 'Gasto en Meta por día (€)', puntos: serie.map(p => ({ x: p.d, y: p.gasto_meta })), formato: n => `${num(n)} €` }) : null,
      c.dinero ? graficoSerie({ titulo: `Coste ${esTienda(c) ? 'por conversión' : 'por lead'} · 7 días móviles`, puntos: movil, umbral: esTienda(c) ? undefined : { y: techo, texto: `${c.objetivo?.cargado ? 'objetivo' : 'techo'} ${techo} €` }, formato: n => `${num(n)} €` })
        : panel({ titulo: 'Gasto', icono: 'candado' }, h('div', { class: 'cuerpo' }, candado('La inversión la ven publicidad, operaciones y quien lleva el cliente'))) ));
    el.append(h('p', { class: 'sub', style: { marginTop: S[2] } }, `Del ${fDiaRO(serie[0].d)} al ${fDiaRO(serie.at(-1).d)}. El día en curso no entra: llega incompleto.`));
  }
}

function tEmbudo(el, ctx, d, c) {
  const e = c.ghl?.embudo;
  if (!c.ghl?.conectado || !e) {
    el.append(vacio({ icono: 'base', titulo: 'Sin embudo: el CRM no está conectado', texto: 'No hay subcuenta de GoHighLevel emparejada con este cliente, así que no se ve qué pasa con los leads después de Meta.', quien: 'Agus (emparejar la subcuenta)' }));
    return;
  }
  const ET = [['nuevo', 'Nuevo', 'inbox'], ['seguimiento', 'Seguimiento', 'phone'], ['cita', 'Cita', 'cal'], ['presupuesto', 'Presupuesto', 'doc'], ['cerrado', 'Cerrado', 'star'], ['descartado', 'Descartado', 'cerrar']];
  const total = e.contactos_90d || 0;
  const max = Math.max(1, ...ET.map(([k]) => e.funnel?.[k] || 0));
  const cit = c.ghl.citas || {};
  el.append(h('div', { class: 'dos' },
    panel({ titulo: 'Embudo de GoHighLevel · 90 días', icono: 'cap', sub: `${num(total)} contactos; cada uno en su etapa más avanzada. Pipelines: ${Object.keys(e.pipelines_90d || {}).join(', ') || '—'}` },
      h('div', { class: 'cuerpo pila' },
        total ? embudoBarras(ET.map(([k, t, i]) => ({ etiqueta: t, icono: i, valor: e.funnel?.[k] || 0, estado: k === 'descartado' ? 'rojo' : k === 'cerrado' ? 'verde' : null, nota: `${num(e.funnel?.[k] || 0)} contactos` })), { max }) : vacio({ icono: 'inbox', titulo: 'Ningún contacto en 90 días', texto: 'GHL está conectado pero no tiene oportunidades: los leads de Meta no llegan al CRM.', quien: 'Agus', tono: 'aviso' }),
        h('div', { class: 'fila', style: { gap: S[2] } },
          chipEstado('gris', `Lead → cita ${pct(e.conv_lead_cita)}`, { punto: false }), chipEstado('gris', `Cita → presupuesto ${pct(e.conv_cita_pres)}`, { punto: false }),
          chipEstado('gris', `Presupuesto → cierre ${pct(e.conv_pres_cierre)}`, { punto: false }), chipEstado(e.pct_en_nuevo > 50 ? 'ambar' : 'gris', `${pct(e.pct_en_nuevo)} sigue en Nuevo`, { punto: false })))),
    h('div', { class: 'pila' },
      tiles([
        tile({ icono: 'clock', etiqueta: 'Parados más de 72 h', valor: `${num(e.estancados_72h)} de ${num(e.cohorte_30d)}`, estado: e.pct_estancado >= 50 ? 'rojo' : e.estancados_72h ? 'ambar' : 'verde',
          comparacion: { texto: e.horas_max_parado ? `el más parado lleva ${num(Math.round(e.horas_max_parado / 24))} días` : 'cohorte de 30 días' },
          contexto: `${num(e.bolsa_historica_en_nuevo)} oportunidades viejas en Nuevo (bolsa histórica, fuera de la alerta)`, medible: 'hoy', frescura: fuenteDe(d, 'ghl') }),
        tile({ icono: 'cal', etiqueta: 'Citas · 14 días', valor: num(cit['14d']?.agendadas), comparacion: { texto: `${num(cit['14d']?.celebradas)} celebradas · ${num(cit['14d']?.no_presentadas)} no vinieron · ${num(cit.proximas)} próximas` },
          contexto: cit['14d']?.sin_estado ? `${cit['14d'].sin_estado} sin marcar si vinieron: la asistencia no es fiable` : 'Todas con estado', estado: cit['14d']?.sin_estado ? 'ambar' : '', medible: 'hoy', frescura: fuenteDe(d, 'ghl') }),
        tile({ icono: 'users', etiqueta: 'Asistencia · 14 días', valor: cit['14d']?.asistencia_pct === null || cit['14d']?.asistencia_pct === undefined ? null : pct(cit['14d'].asistencia_pct), estado: cit['14d']?.asistencia_pct === null || cit['14d']?.asistencia_pct === undefined ? 'gris' : semaforo(cit['14d'].asistencia_pct, { verde: d.parametros.asistencia[0], ambar: d.parametros.asistencia[1] }),
          comparacion: { texto: `septiembre ${pct(cit.mes_anterior?.asistencia_pct)}` }, contexto: 'Verde ≥ 75 % · rojo < 60 %', medible: 'medias', medibleDetalle: 'Solo cuenta las citas con estado marcado', frescura: fuenteDe(d, 'ghl') }),
      ]),
      e.sin_avance_90d ? avisoParcial('Ningún lead ha pasado a cita en el embudo en 90 días.', { titulo: 'Embudo sin avance.' }) : null)));
}

function tCampanas(el, ctx, d, c) {
  const cs = c.campanas || [];
  el.append(panel({ titulo: 'Campañas de Meta', icono: 'megafono', sub: 'Gasto, leads y coste por lead: 7 días, mes en curso y septiembre' },
    tablaApilable({ filas: cs, columnas: [
      { clave: 'campana', titulo: 'Campaña', principal: true, celda: x => h('span', { style: { display: 'grid' } }, h('b', {}, x.campana), h('small', { class: 'sub' }, x.plataforma === 'meta' ? 'Meta' : x.plataforma)) },
      { clave: 'l7', titulo: 'Leads 7 d', num: true, celda: x => num(x.leads_7d) },
      { clave: 'g7', titulo: 'Gasto 7 d', num: true, celda: x => (x.gasto_7d === undefined ? candado('—') : eur(x.gasto_7d)) },
      { clave: 'c7', titulo: 'Coste por lead 7 d', num: true, celda: x => (x.gasto_7d === undefined ? candado('—') : x.cpl_7d ? eur(x.cpl_7d) : (x.gasto_7d ? 'sin leads' : '—')) },
      { clave: 'lm', titulo: 'Leads sept.', num: true, celda: x => num(x.leads_mes_anterior) },
      { clave: 'cm', titulo: 'Coste por lead sept.', num: true, celda: x => (x.gasto_mes_anterior === undefined ? candado('—') : x.cpl_mes_anterior ? eur(x.cpl_mes_anterior) : '—') },
      { clave: 'ir', titulo: 'Abrir', ordenable: false, celda: x => (x.enlace || c.cuenta_meta?.enlace ? h('a', { class: 'bt mini', href: x.enlace || c.cuenta_meta.enlace, target: '_blank', rel: 'noopener', title: 'Abre la campaña en el Administrador de anuncios; si Meta no la selecciona, abre la cuenta' }, icono('ext'), 'Abrir en Meta') : '—') },
    ], vacio: { titulo: 'Sin campañas con gasto en las últimas 5 semanas', texto: 'La cuenta no ha gastado en Meta desde finales de agosto.' } })));
  if (c.google_ads?.periodo) el.append(avisoParcial(`Google Ads (${c.google_ads.cuenta}): solo totales de septiembre, sin campañas, hasta la clave de Windsor.`, { tipo: 'info' }));
}

function tAnuncios(el, ctx, d, c) {
  const a = c.anuncios;
  if (!a) { el.append(vacio({ icono: 'spark', titulo: 'Sin anuncios que mirar', texto: c.meta_activa ? 'No se pudieron leer los anuncios de esta cuenta.' : 'La cuenta no tiene pauta activa: no hay anuncios con impresiones en 7 días.' })); return; }
  el.append(tiles([
    tile({ icono: 'baja', etiqueta: 'Cansadas', valor: a.cansadas, estado: a.cansadas ? 'rojo' : 'verde', contexto: 'Dos señales a la vez', medible: 'hoy' }),
    tile({ icono: 'ojo', etiqueta: 'Con una señal', valor: a.vigilar, estado: a.vigilar ? 'ambar' : 'verde', contexto: 'Vigilar: una señal sola no dispara', medible: 'hoy' }),
    tile({ icono: 'star', etiqueta: 'Ganadoras', valor: a.ganadoras, estado: '', contexto: 'Gasto ≥ 10 veces el objetivo con coste ≤ objetivo', medible: 'hoy' }),
    tile({ icono: 'alert', etiqueta: 'Rechazados o con problemas', valor: a.problemas_total, estado: a.problemas_total ? 'rojo' : 'verde', contexto: `${a.aprendizaje_limitado} de ${a.conjuntos_con_dato} conjuntos en aprendizaje limitado`, medible: 'hoy' }),
  ]));
  el.append(panel({ titulo: 'Anuncios · 7 días', icono: 'spark', sub: `${a.total_7d} con impresiones; ${a.sin_autor} sin iniciales de autor (desde el próximo lanzamiento)` },
    tablaApilable({ filas: a.anuncios, columnas: [
      { clave: 'nombre', titulo: 'Anuncio', principal: true, celda: x => h('span', { style: { display: 'grid' } }, h('b', {}, x.nombre), h('small', { class: 'sub' }, distingue(x))) },
      { clave: 'e', titulo: 'Estado', celda: x => h('span', { style: { display: 'grid', gap: S[1] } }, chipEstado(x.cansada ? 'rojo' : x.vigilar ? 'ambar' : x.ganadora ? 'verde' : 'gris', x.cansada ? 'Cansada' : x.vigilar ? 'Vigilar' : x.ganadora ? 'Ganadora' : 'Normal'), x.senales?.length ? h('small', { class: 'sub' }, x.senales.join(' + ')) : null) },
      { clave: 'f', titulo: 'Frecuencia', num: true, celda: x => (x.frecuencia_7d ? num(x.frecuencia_7d, 1) : '—') },
      { clave: 'ctr', titulo: '% de clics', num: true, celda: x => (x.ctr_7d === undefined ? '—' : `${num(x.ctr_7d, 2)} %${x.ctr_previo ? ` (antes ${num(x.ctr_previo, 2)})` : ''}`) },
      { clave: 'l', titulo: 'Leads 7 d', num: true, celda: x => num(x.leads_7d ?? null) },
      { clave: 'c', titulo: 'Coste por lead', num: true, celda: x => (!c.dinero || x.cpl_7d === undefined && x.cpl_30d === undefined ? candado('—') : x.cpl_7d ? eur(x.cpl_7d) : x.cpl_30d ? `${eur(x.cpl_30d)} (30 d)` : '—') },
      { clave: 'autor', titulo: 'Autor', celda: x => nombre(d, x.autor) || h('span', { class: 'dim' }, 'sin autor') },
      { clave: 'ir', titulo: 'Abrir', ordenable: false, celda: x => (x.enlace ? h('a', { class: 'bt mini', href: x.enlace, target: '_blank', rel: 'noopener', title: 'Abre el anuncio en el Administrador de anuncios; si Meta no lo selecciona, abre la cuenta' }, icono('ext'), 'Abrir en Meta') : '—') },
    ], vacio: { titulo: 'Ningún anuncio con impresiones esta semana' } })));
  if (a.problemas?.length) {
    el.append(panel({ titulo: 'Rechazados o con problemas', icono: 'alert' }, h('div', { class: 'cuerpo' }, listaConIcono(a.problemas.map(p => ({ icono: 'alert', estado: p.estado === 'DISAPPROVED' ? 'rojo' : 'ambar', texto: `${p.nombre} · ${p.estado === 'DISAPPROVED' ? 'rechazado' : 'con problemas'}`, extra: `desde ${fDiaRO(p.desde)}` }))))));
  }
}

function tMetas(el, ctx, d, c) {
  const ms = c.metas || [];
  if (!ms.length) { el.append(vacio({ icono: 'flag', titulo: 'Metas sin cargar', texto: 'Las metas del cliente (leads, leads cualificados, demos, pruebas gratis) se cargan en el alta, el día 0. La Torre tampoco las tenía para este cliente.', quien: nombre(d, c.equipo?.account) || 'el account' })); return; }
  el.append(avisoParcial('Metas de septiembre de la Torre (17-sep) como referencia: las de octubre no están cargadas. El ritmo no avisa hasta el día 5 del mes.', { titulo: 'Referencia.' }));
  el.append(h('div', { class: 'rejilla', style: { marginTop: S[3] } }, ms.map(m => {
    const sep = m.septiembre_pct;
    return h('div', { class: 'panel', style: { padding: `${S[4]} ${S[4]}`, display: 'grid', gap: S[2] } },
      h('div', { class: 'fila', style: { justifyContent: 'space-between' } }, h('b', {}, `${m.tipo[0].toUpperCase()}${m.tipo.slice(1)}`), chipEstado('gris', `meta ${num(m.cantidad)}`, { punto: false })),
      h('div', { style: { display: 'grid', gap: S[1] } }, h('span', { class: 'sub' }, 'Septiembre'), barraProgreso({ valor: Math.min(100, sep || 0), max: 100, estado: sep >= 100 ? 'verde' : sep >= 75 ? 'ambar' : 'rojo' }),
        h('span', { class: 'sub' }, `${num(m.septiembre_logrado)} de ${num(m.cantidad)} · ${pct(sep)}`)),
      h('div', { style: { display: 'grid', gap: S[1] } }, h('span', { class: 'sub' }, 'Octubre hasta ayer'), barraProgreso({ valor: Math.min(100, m.pct || 0), max: 100, marca: d.pct_mes, etiqueta: `${num(m.logrado)} de ${num(m.cantidad)}; la raya es lo transcurrido del mes` }),
        h('span', { class: 'sub' }, `${num(m.logrado)} de ${num(m.cantidad)} · faltan ${num(m.faltan)}`)),
      m.nota ? h('span', { class: 'sub' }, `Cómo se cuenta: ${m.nota}`) : null);
  })));
}

function tQuincenal(el, ctx, d, c) {
  const q = c.quincenal;
  if (!q) { el.append(vacio({ icono: 'doc', titulo: 'Sin quincenal', texto: 'Solo para cuentas con Meta.' })); return; }
  const [ini, fin] = q.periodo;
  const lineas = [
    `Quincenal de ${c.nombre} · del ${fDiaRO(ini)} al ${fDiaRO(fin)}`,
    `· Contactos de Meta: ${num(q.leads_14d)}`,
    c.dinero ? `· Inversión: ${eur(q.gasto_14d)} · coste por contacto ${q.cpl_14d ? eur(q.cpl_14d) : '—'}` : null,
    `· Citas agendadas: ${num(q.citas_14d)} · celebradas ${num(q.celebradas_14d)}${q.asistencia_14d !== null && q.asistencia_14d !== undefined ? ` · asistencia ${pct(q.asistencia_14d)}` : ''}`,
    c.dinero && q.coste_por_cita_14d ? `· Coste por cita: ${eur(q.coste_por_cita_14d)}` : null,
    q.sin_estado_14d ? `· Ojo: ${q.sin_estado_14d} citas pasadas sin marcar si vinieron` : null,
    (c.motivos || []).length ? `· A trabajar: ${(c.motivos || []).map(textoMot).join(' · ')}` : '· Sin alertas abiertas',
  ].filter(Boolean);
  el.append(h('div', { class: 'dos' },
    panel({ titulo: 'Quincenal preparada', icono: 'doc', sub: 'Gasto, contactos, citas, coste por cita y asistencia del periodo, lista para la reunión del trafficker con el cliente.',
      acciones: h('button', { type: 'button', class: 'bt mini', on: { click: () => copiar(lineas.join('\n'), 'Resumen copiado') } }, icono('copy'), 'Copiar') },
      h('div', { class: 'cuerpo' }, h('pre', { style: { whiteSpace: 'pre-wrap', fontFamily: 'var(--sans)', fontSize: 'var(--fs-13)', margin: 0, lineHeight: 1.6 } }, lineas.join('\n')))),
    panel({ titulo: 'Apuntar la quincenal', icono: 'check', sub: 'Indicador «quincenal hecha con informe» (a medias hasta que se apunte aquí)' },
      h('div', { class: 'cuerpo pila' },
        h('p', {}, 'Cuando la reunión esté hecha, apúntala: queda en el rastro con la hora.'),
        botonConfirmar({ texto: 'Quincenal hecha', pregunta: '¿Apuntar la quincenal como hecha?', confirmar: 'Sí, apuntar', soloLectura: ctx.soloLectura,
          alConfirmar: async () => { await ctx.accion({ herramienta: 'app', tipo: 'quincenal_hecha', objeto: c.nombre, cliente_id: c.cliente_id, texto: `Quincenal ${ini} a ${fin}`, vista_previa: lineas.join('\n') }); return 'Apuntada (simulación)'; } })))));
}

function tHistoria(el, ctx, d, c) {
  const hst = c.historia || {};
  const caja = (titulo, sub, cuerpo, est) => h('div', { style: { border: '1px solid var(--line)', borderRadius: 'var(--r-s)', padding: S[3], display: 'grid', gap: S[1], background: 'var(--card)', minWidth: '0' } },
    h('span', { class: 'sub', style: { fontWeight: '600' } }, titulo), est ? h('span', {}, chipEstado(GRAV[est]?.e || 'gris', GRAV[est]?.t || est)) : null, h('b', { style: NOWRAP }, cuerpo), sub ? h('span', { class: 'sub' }, sub) : null);
  const cols = [];
  if (hst.hace_4_semanas) cols.push(caja(`Hace 4 semanas · ${fDiaRO(hst.hace_4_semanas.periodo[0])} a ${fDiaRO(hst.hace_4_semanas.periodo[1])}`, c.dinero && hst.hace_4_semanas.gasto_meta !== undefined ? `${eur(hst.hace_4_semanas.gasto_meta)} de gasto` : null, `${num(hst.hace_4_semanas.leads_meta)} leads`));
  if (hst.torre_17sep) cols.push(caja('Foto del 17 de septiembre (herramienta anterior)', (c.dinero ? hst.torre_17sep.gasto_motivos : hst.torre_17sep.motivos)?.join(' · ') || 'sin motivos', `${num(hst.torre_17sep.leads_7d)} leads en 7 días`, hst.torre_17sep.severidad));
  if (c.leads) cols.push(caja('7 días anteriores', c.dinero ? `${eur(c.gasto?.['7d_prev'])} · ${c.cpl?.['7d_prev'] ? eur(c.cpl['7d_prev']) + ' por lead' : 'sin leads'}` : null, `${num(c.leads['7d_prev'])} leads`));
  if (c.leads) cols.push(caja('Últimos 7 días', c.dinero ? `${eur(c.gasto?.['7d'])} · ${c.cpl?.['7d'] ? eur(c.cpl['7d']) + ' por lead' : 'sin leads'}` : null, `${num(c.leads['7d'])} leads`, c.severidad));
  el.append(cols.length ? h('div', { class: 'rejilla' }, cols) : vacio({ icono: 'hist', titulo: 'Sin historia todavía' }));
  el.append(avisoParcial('A 90 días y «qué se cambió» llegan con las fotos diarias de la app (empezaron el 2-oct) y con el rastro de acciones. Mientras, la foto del 17 de septiembre de la herramienta anterior hace de punto de comparación.', { tipo: 'info', titulo: 'Historia.' }));
}

// ================================================================== módulo
export default {
  id: 'captacion',
  titulo: 'Captación',
  grupo: 'Captación y CRM',
  // R12 (A2): solo la lista (la tarjeta de un cliente va en ventanas fijas); solo periodos con serie diaria de Meta
  usa_periodo: params => (params && params.length ? false : PERIODOS_CAPTACION),
  async render(contenedor, ctx) {
    vigilarCortes(contenedor);
    NOMBRE_CTX = typeof ctx.nombre === 'function' ? ctx.nombre : null;
    PERIODO = ctx.periodo || null;
    PARAMS = null;
    const espera = esqueleto({ lineas: 4, tarjetas: 4 });
    contenedor.append(espera);
    const d = await cargar(ctx);
    espera.remove();
    if (d.error) {
      contenedor.append(vacio({ icono: 'alert', titulo: 'No se pudieron cargar los datos de captación', texto: d.error, quien: 'Agus (técnico)', borde: true, tono: 'aviso' }));
      return;
    }
    PARAMS = d.parametros || null;
    const [id, extra] = ctx.params;
    if (id === '~trafficker' && extra) {
      // atajo desde «Por trafficker»: lista filtrada por esa persona
      const filas = d.clientes.filter(c => (c.equipo?.trafficker || '—') === extra);
      const K = contexto(ctx, d);
      ctx.titulo(`Captación · ${extra === '—' ? 'sin trafficker' : nombre(d, extra)}`, `${filas.length} cuentas · datos hasta el ${fDiaRO(d.datos_hasta)}`);
      contenedor.append(h('nav', { class: 'migas', 'aria-label': 'Migas' }, h('a', { href: '#/captacion' }, icono('target', { clase: 's' }), 'Captación'), h('span', { 'aria-hidden': 'true' }, '›'), h('span', { 'aria-current': 'page' }, extra === '—' ? 'Sin trafficker' : nombre(d, extra))));
      const zona = h('div', { class: 'pila', style: { gap: S[6] } });
      sinDesborde(zona);
      contenedor.append(zona);
      pintarCuerpo(zona, ctx, d, filas, K, ctx.nivel === 'resumen', 'trafficker');
      for (const hijo of contenedor.children) hijo.style.minWidth = '0';
      return;
    }
    if (id) pintarTarjeta(contenedor, ctx, d, id);
    else await pintarLista(contenedor, ctx, d);
    // El contenedor es una rejilla: sin esto, un hijo ancho (tabla, pestañas) estira la página en móvil.
    for (const hijo of contenedor.children) hijo.style.minWidth = '0';
  },
};

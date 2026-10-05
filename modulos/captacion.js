import { sumaSeriePaid549, compararSeriesPaid549, fechaPaid549, minimoGastoPaid554 } from './_serie_paid_549.js';
import {ambitoPaid516,guardarPaid516,cargarLecturaPaid516} from './_intencion_paid_516.js';
import { conteoMeta508, deltaMeta508, creativosMatriz508, cuentaMetaError508 } from './_matriz_paid_508.js';
import { normalizarCita299, referenciaCita299, textoMetaQuincenal299 } from './_coste_cita_299.js';
import { medirCplPaid, normalizarPaid, cplMovilPaid285, resumenNichoPaid671 } from './_paid_mediciones.js';
import { medirEmbudoCRM, conteoCRM } from './_crm_mediciones.js';
import { panelPaid } from './_panel_especialista.js';
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
// El contador Meta legado no acredita tipo de evento; comercio queda fuera de CPL lead y de los totales de leads.

import {renderMetaDiaria386,ambitoMeta386} from './_meta_diaria_386.js';
import { duenoConexion } from './ajustes_conexiones.js';
import { motivoSinCartera } from './ficha.js';   // V2 (B-M2): el dueño de cada conexión sale de un solo sitio
import {
  h, fmt, semaforo, tile, tiles, listaLoPrimero, tablaDensa, tablaApilable, chipEstado, chipsFiltro, selectorCliente,
  vacio, botonConfirmar, avisoParcial, logoCliente, candado, panel, frescura, icono, iniciales, pestanas, graficoSerie,
  variacion, fichaCatalogo, pieFase2, copiar, avisoFlotante, listaConIcono, selloMedible, limpiaTexto,
  barraProgreso, embudoBarras, ventanas, colorCifra, cifraPrincipal, vacioLinea, menuMas, esqueleto, rejillaTarjetas,
  hoyMadrid, sumarDias,
} from '../componentes.js';
import { franjaCifras, barraAcciones } from './_trabajo.js';
import { pantallaAncha, franjaEnLinea } from './_trabajo_ancho.js';
import { conDeshacer, botonDeshacer } from './_deshacer.js';

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
// La matriz mantiene su ventana fija; los objetivos requieren evidencia compatible propia.
const PERIODOS_CAPTACION = ['7d', '30d', 'mes', 'ayer'];
let PERIODO = null;
/** Contador observado (sin comercio); huecos no son cero ni cobertura completa. */
function sumaSerie(filas, desde, hasta, inicioSerie, hoy=hoyMadrid(), corte=null) {
  return sumaSeriePaid549(filas,desde,hasta,hoy,corte);
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
  dato:{t:'Señal pendiente de contraste',e:'gris',i:'info',o:3},
  inactivo: { t: 'Sin pauta', e: 'gris', i: 'vacio', o: 3 },
};
const chipPub = c => chipEstado(GRAV[c.severidad]?.e || 'gris', (GRAV[c.severidad]?.t || 'Sin dato') + (c.estado_evaluacion === 'referencia_legacy_no_recalculada' ? ' · referencia anterior' : ''), { punto: false });
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
function contrastarMotivo(texto) {
  return String(texto || '')
    .replace(/: el despacho no trabaja los leads/g, ': falta confirmar el seguimiento con el despacho')
    .replace(/: el despacho no mueve las etapas/g, ': hay una diferencia entre calendario y etapas que debe revisarse')
    .replace(/en toda su historia/g, 'en la lectura disponible')
    .replace(/Ningún lead ha llegado a cita/g, 'No hay cita registrada')
    .replace(/Ningún lead ha pasado a cita/g, 'No hay paso a cita registrado')
    .replace(/Subcuenta de GoHighLevel sin usar/g, 'Subcuenta de GoHighLevel con pocos contactos registrados')
    .replace(/los (.*?) leads de Meta de 7 días no van a GoHighLevel/g, 'hay $1 leads de Meta en 7 días; su destino no está reconciliado por lead')
    .replace(/Ayer no gastó nada: campañas paradas, sin saldo o rechazadas/g, 'Ayer no hay gasto registrado; confirmar estado de campañas, saldo y lectura')
    .replace(/techo de (\d+(?:[.,]\d+)?) €/g, 'umbral anterior de $1 €');
}
const textoMot = m => contrastarMotivo(limpiaTexto(m.gasto_texto && !m.gasto_texto.includes('[importe]') ? m.gasto_texto : m.texto))
  + (m.objetivo_sin_cargar && PARAMS ? ` (techo de ${PARAMS.techo_cpl} € por lead y red de seguridad de ${PARAMS.alarma_cita} € por cita)` : '');
let PARAMS = null;                 // parámetros de la casa (no son dinero de ningún cliente)
let NOMBRE_CTX = null;             // ctx.nombre(): el nombre de la persona como en toda la app
/** V2 (B-B10): el mismo texto en «Lo primero hoy» y en la tarjeta cuando no hay especialista de CRM. */
const crmTexto = (d, c) => (c.equipo?.crm ? nombre(d, c.equipo.crm) : 'CRM · asignación pendiente');

// ------------------------------------------------------------------ sin hoja propia: tokens y piezas pequeñas
const S = { 1: 'var(--s-1, 4px)', 2: 'var(--s-2, 8px)', 3: 'var(--s-3, 12px)', 4: 'var(--s-4, 16px)', 5: 'var(--s-5, 20px)', 6: 'var(--s-6, 24px)' };
// Sin dato: tile({ valor: null }) común (ronda 10) pinta «Sin dato» pequeño y gris, nunca un «—» de 24 px (guía 3.7).
const NOWRAP = { whiteSpace: 'nowrap', fontVariantNumeric: 'tabular-nums' };
/** «Se rompe en: …» como chip gris con icono (antes .cap-cuello a 11,5 px). */
const chipCuello = (k, conPrefijo) => h('span', { class: 'chip gris sin-punto', title: `Se rompe en: ${CUELLO[k].t}` }, icono(CUELLO[k].i, { clase: 's' }), conPrefijo ? `Se rompe en: ${CUELLO[k].t}` : CUELLO[k].t);
/** Línea de fuentes en un solo chip «Datos al día» que se despliega (guía 3.6). */
function lineaFuentes(fuentes, ...extra) {
  const lista = (Array.isArray(fuentes)?fuentes:[]).filter(f=>f&&typeof f==='object');
  const avisos=lista.filter(f=>typeof f.estado==='string'&&!['ok','bien'].includes(f.estado)).length;
  const pto=h('span',{'aria-hidden':'true',style:{width:'8px',height:'8px',borderRadius:'50%',background:avisos?'var(--warn)':'var(--off)',display:'inline-block'}});
  return h('details',{class:'que-es',style:{minWidth:'0'}},
    h('summary',{style:{display:'inline-flex',alignItems:'center',gap:S[2],minHeight:'32px'}},pto,'Fuentes · copia',h('span',{class:'sub'},`· ${lista.length} fuentes${avisos?` · ${avisos} con aviso`:''}`)),
    h('div',{class:'fila',style:{marginTop:S[2],gap:`${S[2]} ${S[3]}`,flexWrap:'wrap',minWidth:'0'}},lista.map(f=>{
      const fecha=fechaPaid549(f.fecha),estado=typeof f.estado==='string'?f.estado:'sin estado',valida=fecha&&fecha<=hoyMadrid();
      return h('span',{class:'chip gris',title:`${f.fuente||'Fuente'} · lectura: ${f.fecha||'sin fecha'} · corte: ${f.datos_hasta||'sin corte'} · estado: ${estado}. No acredita cobertura ni actualidad de todos los recursos.`,style:{maxWidth:'100%',whiteSpace:'normal',height:'auto'}},`${f.fuente||'Fuente'} · ${valida?fDiaRO(fecha):'fecha por confirmar'} · ${estado}`);
    }),...extra));
}
/** 411: información secundaria disponible sin desplazar la tabla o el editor. */
function plegablePaid411(titulo, ...contenido) {
  return h('details', { class: 'que-es', 'data-paid-detalle': '411', style: { minWidth: '0' } },
    h('summary', { style: { minHeight: '44px', display: 'flex', alignItems: 'center', gap: S[2] } }, titulo),
    h('div', { class: 'pila', style: { marginTop: S[2], gap: S[2], minWidth: '0' } }, ...contenido));
}
function cabeceraPaid411(ctx, d, c) {
  const eq = c.equipo || {};
  return h('section', { class: 'detalle-cab', 'data-paid-cabecera': '411', style: { display: 'grid', gap: S[2] }, 'aria-label': 'Cabecera de la cuenta' },
    h('div', { class: 'fila', style: { gap: S[2], alignItems: 'center', justifyContent: 'space-between' } },
      h('div', { class: 'fila', style: { gap: S[2], minWidth: '0', flex: '1 1 240px' } },
        logoCliente(c, 'logo-cli'), h('strong', { style: { fontSize: 'var(--fs-base, 14px)', minWidth: '0' } }, c.nombre),
        h('span', { class: `chip ${gc(c).e}`, title: (c.motivos_cliente || []).join(' · ') || 'Gravedad única del cliente (la de toda la app)' }, `Estado: ${gc(c).t}`),
        chipPub(c),
        c.cuenta_meta?.estado && c.cuenta_meta.estado !== 'activa' ? chipEstado('rojo', `Cuenta de Meta: ${c.cuenta_meta.estado}`) : null,
        !c.objetivo?.cargado && c.cuenta_meta ? chipEstado('ambar', 'Objetivo sin cargar') : null),
      h('div', { class: 'fila', style: { gap: S[2] } },
        c.cuenta_meta?.enlace ? h('a', { class: 'bt', href: c.cuenta_meta.enlace, target: '_blank', rel: 'noopener' }, icono('ext'), 'Abrir en Meta') : null,
        c.ghl?.enlace ? h('a', { class: 'bt', href: c.ghl.enlace, target: '_blank', rel: 'noopener' }, icono('ext'), 'Abrir en GHL') : null,
        h('a', { class: 'bt', href: `#/en-rojo/${c.cliente_id}` }, icono('cli'), 'Ficha'))),
    plegablePaid411('Equipo y contexto',
      h('div', { class: 'meta-linea' },
        ...['trafficker', 'account', 'crm'].map(s => h('span', { title: eq[s + '_confianza'] ? `Asignación con confianza ${eq[s + '_confianza']} (fase 0)` : null },
          h('span', { class: 'av s', 'aria-hidden': 'true' }, iniciales(nombre(d, eq[s]) || '?')), `${s === 'crm' ? 'CRM' : s === 'account' ? 'Account' : 'Trafficker'}: ${s === 'crm' ? crmTexto(d, c) : (nombre(d, eq[s]) || 'sin asignar')}`)),
        c.nicho ? h('span', {}, icono('maletin'), c.nicho) : null),
      h('div', { class: 'fila', style: { gap: S[2] } },
        esTienda(c) ? chipEstado('azul', 'Tienda online', { punto: false }) : null,
        ...(c.cuello || []).map(k => chipCuello(k, true)),
        ...(c.plataformas || []).map(p => chipEstado('azul', p === 'meta' ? 'Meta' : p === 'google' ? 'Google Ads' : p, { punto: false })),
        c.nuevo ? chipEstado('azul', 'Cliente nuevo') : null)));
}
/** El contenedor es una rejilla: que ningún hijo (tabla, pestañas) estire la página en el móvil. Antes, .cap-raiz. */
function sinDesborde(raiz) {
  const fija = el => { for (const x of el.querySelectorAll(':scope > *, .pila > *, .pestana-panel > *, [role=tabpanel] > *')) x.style.minWidth = '0'; };
  fija(raiz);
  new MutationObserver(() => fija(raiz)).observe(raiz, { childList: true, subtree: true });
}
// Tiendas online: el contador legado no acredita compras ni contactos.
const TIENDAS_ONLINE = new Set(['kiosko-box']);
const esTienda = c => !!c.tienda_online || TIENDAS_ONLINE.has(c.cliente_id);
const NOTA_TIENDA = 'Tienda online: el contador Meta de esta copia no acredita el tipo de evento. No demuestra contactos, compras ni conversiones únicas; no se incorpora a leads ni se evalúa como CPL real.';

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
    c.coste_por_cita=normalizarCita299(c.coste_por_cita);
    if(c.quincenal){c.quincenal.coste_por_cita_referencia_14d=referenciaCita299(c.quincenal)??referenciaCita299(c.coste_por_cita);c.quincenal.coste_por_cita_14d=null;}
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
    c.coste_por_cita = normalizarCita299(g.coste_por_cita);
    if (c.quincenal) { c.quincenal.coste_por_cita_referencia_14d=referenciaCita299(c.coste_por_cita);c.quincenal.coste_por_cita_14d=null; }
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
const crmDe = c => c.equipo?.crm || null;
const fuenteDe = (d, id) => {
  const f=(d.fuentes||[]).find(x=>x.id===id);
  return f?{fuente:f.fuente||id,fecha:f.hora||null,datos_hasta:f.datos_hasta||null,estado:f.medicion==='medias'?'parcial':f.estado||'sin estado',medicion:f.medicion}:{fuente:id,estado:'sin datos'};
};

// Resumen de observaciones: ausencia no es cero y una muestra no acredita el universo.
function resumenObservadoPaid4(filas,d,hoy) {
  const conGravedad=filas.filter(c=>['critico','atencion','bien'].includes(c.gravedad));
  const muestras=filas.map(c=>creativosMatriz508(c,d,hoy)).filter(m=>m!==null);
  return {total:filas.length,gravedadConDato:conGravedad.length,
    criticos:conGravedad.length?conGravedad.filter(c=>c.gravedad==='critico').length:null,
    atencion:conGravedad.length?conGravedad.filter(c=>c.gravedad==='atencion').length:null,
    creativosConDato:muestras.length,senales:muestras.length?muestras.reduce((n,m)=>n+m.valor,0):null};
}

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
  const sumGhl = conGhl.reduce((s, c) => s + (c.despacho.leads_ghl_7d || 0), 0);
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
    pctCrm: null, comparacionRecuentos: conGhl.length > 0, sumMeta, sumGhl, conGhl,
    cansadas: filas.reduce((s, c) => s + (c.anuncios?.cansadas || 0), 0),
    vigilar: filas.reduce((s, c) => s + (c.anuncios?.vigilar || 0), 0),
    rechazados: filas.reduce((s, c) => s + (c.anuncios?.problemas_total || 0), 0),
    paradas: activas.filter(c => (c.gasto?.ayer === 0) || (c.cuenta_meta?.ultimo_dia_con_gasto && c.cuenta_meta.ultimo_dia_con_gasto < d.datos_hasta)),
  };
}

// 648: recuentos observados no certifican exhaustividad ni ausencia de señales.
function contadorObservado648(v) { return typeof v === 'number' && Number.isSafeInteger(v) && v >= 0 ? v : null; }
function resumenEquipo648(filas, d) {
  const gravedad = filas.filter(c => ['critico', 'atencion', 'bien'].includes(c?.gravedad));
  const dia = v => typeof v === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(v) && Number.isFinite(Date.parse(v+'T12:00:00Z')) && new Date(v+'T12:00:00Z').toISOString().slice(0,10) === v;
  const paradas = filas.filter(c => c?.meta_activa && ((typeof c.gasto?.ayer === 'number' && Number.isFinite(c.gasto.ayer) && c.gasto.ayer >= 0) || (dia(c.cuenta_meta?.ultimo_dia_con_gasto) && dia(d.datos_hasta) && c.cuenta_meta.ultimo_dia_con_gasto <= d.datos_hasta)));
  const n = paradas.filter(c => c.gasto?.ayer === 0 || (dia(c.cuenta_meta?.ultimo_dia_con_gasto) && dia(d.datos_hasta) && c.cuenta_meta.ultimo_dia_con_gasto < d.datos_hasta)).length;
  return { gravedad: gravedad.length, paradas: paradas.length ? n : null, paradasConDato: paradas.length };
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
    // Ronda U: la frase de la cartera va al contexto (debajo), no empuja la lista
    K.nodoUniverso = alcance.valor() === 'mias' && K.universo ? h('p', { class: 'sub', style: { margin: '0', maxWidth: '72ch' } }, `${K.universo}.${K.cp ? ' «Mis cuentas» enseña las que tienen cuenta de Meta.' : ''}${apoyoFilas.length ? ` Las de apoyo, en «De apoyo».` : ''}`) : null;
    pintarCuerpo(zona, ctx, d, filas, K, resumenNivel, alcance.valor());
  };
  repintar();
}

function pintarCuerpo(zona, ctx, d, filas, K, resumenNivel, alcance) {
  const C = cifras(filas, d);
  const observado4=resumenObservadoPaid4(filas,d,ctx.hoy||hoyMadrid());
  const techo = d.parametros.techo_cpl;
  const verDinero = C.conDinero.length > 0;
  const nAct = C.activas.length;

  // ---- 1 · lo primero hoy (máx. 7; 4 a la vista y el resto tras «Ver más») ----
  const primeras = [];
  for (const c of [...filas].sort((a, b) => gc(a).o - gc(b).o || GRAV[a.severidad].o - GRAV[b.severidad].o)) {
    for (const m of c.motivos || []) if (m.nivel === 'critico' || (c.severidad !== 'inactivo' && m.nivel === 'atencion')) primeras.push({ c, m });
    const integ = (c.avisos || []).find(a => a.clase_id === 'integracion');
    if (integ && c.severidad !== 'inactivo') primeras.push({c,m:{...integ,nivel:'dato'}});
  }
  const vistos = new Set();
  const lista = primeras.filter(({ c, m }) => { const k = c.cliente_id + (m.clase_id || ''); if (vistos.has(k)) return false; vistos.add(k); return true; })
    .sort((a, b) => gc(a.c).o - gc(b.c).o || (a.m.nivel === 'critico' ? 0 : 1) - (b.m.nivel === 'critico' ? 0 : 1) || GRAV[a.c.severidad].o - GRAV[b.c.severidad].o).slice(0, 7);
  const A_LA_VISTA = 4;
  const loPrimero = listaLoPrimero(lista.map(({ c, m }) => ({
    // V2: el color de la fila es la gravedad del CLIENTE (verdad única); el motivo dice qué falla en la publicidad
    estado:m.nivel==='dato'?'gris':(c.gravedad?gc(c).e:nivelTxt(m.nivel)), icono: CUELLO[m.clase_id]?.i || 'alert',
    motivo: `${c.nombre} · ${({ critico: 'cliente crítico · ', atencion: 'cliente a vigilar · ', bien: 'cliente bien · ' })[c?.gravedad] || ''}${CUELLO[m.clase_id]?.t || m.clase}`,
    detalle: `${textoMot(m)}${c.equipo?.trafficker ? ` — trafficker ${nombre(d, c.equipo.trafficker)}` : ''}${c.equipo?.account ? `, account ${nombre(d, c.equipo.account)}` : ''}, CRM ${crmTexto(d, c)}`,
    botones: botonesCaso(ctx, c, d, m),
  })), { vacio: { titulo:'Sin alerta actual acreditada en esta vista', porque: 'No hay alertas en la lectura disponible; no acredita ausencia de problemas ni entrega de todos los leads.', celebrar:false } });
  const ocultas = [...loPrimero.querySelectorAll(':scope > li')].slice(A_LA_VISTA);
  ocultas.forEach(li => { li.hidden = true; });
  const verMas = ocultas.length ? h('button', { type: 'button', class: 'bt', 'aria-expanded': 'false', on: { click: e => {
    const abrir = ocultas[0].hidden; ocultas.forEach(li => { li.hidden = !abrir; });
    e.currentTarget.setAttribute('aria-expanded', String(abrir));
    e.currentTarget.firstChild.textContent = abrir ? 'Ver menos' : `Ver ${ocultas.length} más`;
  } } }, `Ver ${ocultas.length} más`) : null;
  // orden de la guía 3.6: lo que pide acción, primero; después la cifra que manda y 3 tarjetas de apoyo
  const ctxN = K.nodoUniverso ? [K.nodoUniverso] : [];   // Ronda U: lo de leer va DEBAJO de la lista de cuentas (pantallaAncha), plegado
  ctxN.push(panel({ titulo: 'Lo primero hoy', icono: 'zap', sub: `${alcance === 'mias' ? 'Tus cuentas' : alcance === 'apoyo' ? 'Cuentas en las que ayudas' : alcance === 'trafficker' ? 'Sus cuentas' : 'Toda la casa'}: lo más grave arriba, con dónde se rompe` }, loPrimero, verMas ? h('footer', { class: 'panel-pie' }, h('span', {}, `${lista.length} casos en total`), verMas) : null));

  // El objetivo de CPL debe estar acreditado; el techo anterior no lo sustituye.
  const comparadas=filas.map(c=>medirCplPaid(c,d,ctx.hoy||hoyMadrid())).filter(m=>m.evaluable);
  const cumplen=comparadas.filter(m=>m.real<=m.objetivo);
  const principal=h('div',{class:'tile gris',role:'listitem'},cifraPrincipal({
    etiqueta:'CPL frente a objetivo propio',valor:comparadas.length?num(cumplen.length):h('small',{class:'dim'},'Sin comparación acreditada'),
    unidad:comparadas.length?`de ${num(comparadas.length)} cuentas comparables`:null,estado:'gris',
    comparacion:`${comparadas.length} de ${filas.length} cuentas con objetivo vigente y semana comparable`,
  }),h('span',{class:'tx'},'Los CPL y objetivos registrados siguen en la tabla; un techo anterior no ratifica cumplimiento.'));
  const t = [principal];
  t.push(tile({
    icono: 'fire', etiqueta: 'Clientes críticos', valor: observado4.criticos, unidad: observado4.gravedadConDato?`en ${observado4.gravedadConDato} de ${filas.length} cuentas con gravedad`:null,
    estado: observado4.criticos>0 ? 'rojo' : 'gris',
    comparacion: { texto: observado4.atencion===null?'Gravedad sin dato; no acredita ausencia de problemas':`${fmt.num(observado4.atencion)} más a vigilar · ${observado4.gravedadConDato} de ${filas.length} cuentas con gravedad, la de toda la app` },
    medible: 'hoy', ir: 'Ver cuáles', alPulsar: () => irAPestana(zona, 'cuentas', { gravedad: 'critico' }),
  }));
  t.push(tile({
    icono: 'plug', etiqueta: 'Meta y CRM · 7 días', valor: !C.comparacionRecuentos ? null : 'Recuentos',
    estado: 'gris',
    comparacion: !C.comparacionRecuentos ? { texto: 'Sin dato · ninguna cuenta con GoHighLevel y leads' } : { texto: `${num(C.conGhl.reduce((s, c) => s + (c.despacho.leads_ghl_7d || 0), 0))} contactos CRM · ${num(C.sumMeta)} contador Meta · ${C.conGhl.length} cuentas; sin unión por identidad` },
    medible: 'hoy', ir: 'Ver cuáles', alPulsar: () => irAPestana(zona, 'despacho'),
  }));
  if (!C.comparacionRecuentos) t.at(-1).setAttribute('aria-label', 'Comparación de recuentos Meta y CRM: sin dato. Ver cuáles');
  // Contador de la copia; no sustituir falta de serie por totales legacy.
  const P=PERIODO,w=P?[P.desde,P.hasta]:d.ventanas?.['7d'],prev=P?.comp?[P.comp.desde,P.comp.hasta]:P?null:d.ventanas?.['7d_prev'];
  const SP=sumaSerie(filas,w?.[0],w?.[1],null,ctx.hoy||hoyMadrid(),d.datos_hasta),SC=prev?sumaSerie(filas,prev[0],prev[1],null,ctx.hoy||hoyMadrid(),d.datos_hasta):null;
  const delta=compararSeriesPaid549(SP,SC),coverage=`${SP.dias_observados} de ${SP.dias_esperados??'—'} días-cuenta con contador observado; muestra no exhaustiva`;
  t.push(tile({
    icono:'users',etiqueta:P?`Contador Meta · ${P.nombre.toLowerCase()}`:'Contador Meta · 7 días',valor:SP.leads===null?null:SP.completo?num(SP.leads):`≥${num(SP.leads)}`,
    unidad:verDinero&&SP.gasto!==null?`· ${SP.gastoCompleto?num(SP.gasto,2):'≥'+minimoGastoPaid554(SP.gasto)} ${SP.moneda}`:null,estado:'gris',
    comparacion:delta===null?{texto:'Sin comparación acreditada'}:{delta,pct:true,texto:P?.comp?.texto||'frente a la semana anterior'},
    contexto:`${coverage}. Contador Meta: no contactos únicos ni cualificación.`,medible:'copia',
  }));
  const secCifras=h('section',{class:'pila',style:{gap:S[2]},'aria-label':'Cifras del día'},
    rejillaTarjetas(t.map(x=>{x.setAttribute('role','listitem');return x;})),
    h('p',{class:'sub',style:{margin:'0'},title:`Tarjeta: ${w?.join(' → ')||'ventana sin confirmar'}. Corte original de la copia: ${d.datos_hasta||'sin fecha'}. Cobertura de observaciones no acredita exhaustividad del proveedor. CPL sólo con objetivo propio vigente y medición compatible; coste por cita histórico sin cohorte no se juzga.`},`Tarjeta de contador: ${P?.rango||'7 días fijos'}. Matriz: 7 días fijos.`));
  secCifras.firstChild.setAttribute('role', 'list');
  ctxN.push(secCifras);
  const avisoObjetivo = !resumenNivel && C.conObjetivo.length === 0 && nAct
    ? `Ningún cliente tiene cargado su objetivo de coste por cita ni de coste por lead. Hasta que el account lo cargue en el alta, el generador anterior aplica como referencia (no objetivo acordado) el techo general de ${techo} € por lead y con la red de seguridad de ${d.parametros.alarma_cita} € por cita; cada tarjeta de cliente lleva el aviso «objetivo sin cargar».` : null;

  // ---- 3 · pestañas (lo de cada día primero; Valeria y la paridad, abajo del todo) ----
  const pest = [
    { id: 'cuentas', texto: 'Cuentas', icono: 'res', cuenta: observado4.criticos, cuentaEstado: observado4.criticos>0?'rojo':'gris' },   // críticos = gravedad del cliente
    ...(K.jefe || ctx.persona.puestos.includes('jefa_publicidad') ? [{ id: 'equipo', texto: 'Por trafficker', icono: 'eq' }] : []),
    { id: 'creatividades', texto: 'Creatividades', icono: 'spark', cuenta: observado4.senales, cuentaEstado: 'gris' },
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

  // ---- 4 · cómo se mide (plegado al pie, con el aviso de objetivos y la regla de crítico) ----
  const inds = ['trafficker.de_cuentas_con_coste_por_cita_en_objetivo_el_que', 'trafficker.coste_por_lead_frente_al_objetivo_del_cliente', 'trafficker.leads_que_llegan_al_crm', 'trafficker.creatividad_cansada', 'jefa_publicidad.cuentas_en_rojo_por_trafficker']
    .map(id => ctx.indicador(id)).filter(Boolean);
  ctxN.push(h('details', { class: 'panel', style: { padding: '0' } },
    h('summary', { style: { padding: `${S[4]} ${S[5]}`, cursor: 'pointer', fontWeight: '700', display: 'flex', gap: S[2], alignItems: 'center', minHeight: '44px' } }, icono('medidor'), 'Cómo se mide cada cifra'),
    h('div', { class: 'cuerpo pila', style: { gap: S[3] } },
      avisoObjetivo ? avisoParcial(avisoObjetivo, { titulo: 'Objetivo sin cargar.' }) : null,
      h('p', { class: 'sub', style: { margin: '0' } }, 'Crítico, Atención y Bien son la gravedad del cliente: la misma en toda la app (menú, Mi día, En rojo y ficha). Un problema de publicidad cuenta en ella como «atención».'),
      h('p', { class: 'sub', style: { margin: '0' } }, 'Los motivos anteriores se conservan como señales por contrastar, sin acreditar urgencia actual. El CPL sólo se evalúa con objetivo propio vigente, muestra fiable y semana cerrada comparable. Meta y CRM son recuentos independientes; no prueban conversión ni cualificación.'),
      inds.length ? h('div', { class: 'rejilla' }, inds.map(i => fichaCatalogo(i, {
        valor: i.id.includes('en_objetivo') ? null : i.id.includes('leads_que_llegan') ? null : i.id.includes('cansada') ? null : i.id.includes('rojo_por') ? null : (C.juzg.length ? `${C.enTecho.length}/${C.juzg.length}` : null),
        unidad: null,
      }))) : null)));
  const fase2 = (ctx.indicadores() || []).filter(i => i.modulo === 'captacion');
  const pie = pieFase2(fase2);
  if (pie) ctxN.push(pie);
  // franja de cifras (filtran la lista) · «Sin apuntar hoy» = cuentas con pauta sin bitácora de hoy
  const sinHoy = filas.filter(c => c.meta_activa && !hoyBit(ctx, d, c.cliente_id)).length;
  const franja = !resumenNivel ? franjaCifras([
    { etiqueta: 'Clientes críticos', valor: observado4.criticos??'sin dato', estado: observado4.criticos>0?'rojo':'gris', titulo:`Gravedad disponible en ${observado4.gravedadConDato} de ${filas.length} cuentas; no acredita ausencia de problemas en las demás.`, alPulsar: () => irAPestana(zona, 'cuentas', { gravedad: 'critico' }) },
    { etiqueta: 'Sin apuntar hoy', valor: sinHoy, estado: sinHoy ? 'rojo' : '', titulo: 'Cuentas con pauta sin «qué cambio hoy» apuntado', alPulsar: () => irAPestana(zona, 'cuentas', { sinHoy: true }) },
    { etiqueta: 'Anuncios señalados', valor: observado4.senales??'sin dato', estado:'gris', titulo:`Anuncios con señales en muestras de ${observado4.creativosConDato} de ${filas.length} cuentas; cobertura parcial, no inventario ni fatiga confirmada.`, alPulsar: () => irAPestana(zona, 'creatividades') },
    { etiqueta: 'Meta / CRM · recuentos', valor: !C.comparacionRecuentos ? 'sin dato' : 'ver', alPulsar: () => irAPestana(zona, 'despacho') },
  ], { etiqueta: 'Cifras del día (filtran la lista)' }) : null;
  if(franja)ctxN.unshift(franjaEnLinea(franja));
  zona.append(pantallaAncha({ id: 'captacion', lista: caja, contexto: ctxN, tituloContexto: 'Resumen, señales y cómo se mide' }));
}

/** Botones de un caso de «Lo primero hoy»: uno principal («Abrir tarjeta») y el resto en el menú «⋯»
 *  (Meta o GoHighLevel en otra pestaña, y la tarea al CRM con su confirmación). Antes eran 3 botones por caso. */
function botonesCaso(ctx, c, d, m) {
  const hueco = h('span', { class: 'fila', style: { gap: S[2] } });
  const items = [];
  if (c.cuenta_meta?.enlace && m.clase_id === 'paid') items.push({ texto: 'Abrir en Meta', icono: 'ext', alPulsar: () => window.open(c.cuenta_meta.enlace, '_blank', 'noopener') });
  if (c.ghl?.enlace && m.clase_id !== 'paid') items.push({ texto: 'Abrir en GoHighLevel', icono: 'ext', alPulsar: () => window.open(c.ghl.enlace, '_blank', 'noopener') });
  if (crmDe(c)) items.push({ texto: `Tarea al CRM (${nombre(d, crmDe(c))})`, icono: 'check', alPulsar: () => {
    if ((ctx.vigente && !ctx.vigente()) || !crmDe(c)) return;
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
  const detalleCuenta243=h('section',{'aria-label':'Detalle de la cuenta Paid',tabindex:-1,style:{scrollMarginTop:'90px'}});
  const cerrarDetalle415=()=>{detalleCuenta243._cerrar243?.();detalleCuenta243.replaceChildren();};
  // Los controles de tablaDensa repintan dentro de caja, sin llamar pintar().
  caja.addEventListener('input',cerrarDetalle415);
  caja.addEventListener('change',cerrarDetalle415);
  caja.addEventListener('click',e=>{if(e.target?.closest?.('.tabla-ctl,.tabla-filtros,.tabla-mas,thead'))cerrarDetalle415();});
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
    detalleCuenta243._cerrar243?.();detalleCuenta243.replaceChildren();
    const g = chipsG.valor(), cu = chipsC.valor(), p = chipsP.valor();
    let base = filas.filter(c => (!g || (c.gravedad || 'sin') === g) && (!cu.length || cu.every(k => c.cuello?.includes(k))) && (!p || c.plataformas?.includes(p)));
    if (f?.aviso === 'objetivo') base = base.filter(c => c.meta_activa && !c.objetivo?.cargado);
    if (f?.sinHoy) base = base.filter(c => c.meta_activa && !hoyBit(ctx, d, c.cliente_id));
    const filasT = base.map(c => ({
      ...c, panelEspecialista:{...panelPaid(c,d,ctx.hoy||hoyMadrid()),real:medirCplPaid(c,d,ctx.hoy||hoyMadrid()).real,referenciaAnterior:medirCplPaid(c,d,ctx.hoy||hoyMadrid()).referenciaAnterior}, grav: gc(c).o * 10 + GRAV[c.severidad].o, pub: GRAV[c.severidad].o, motivo: (c.motivos || [])[0] ? textoMot(c.motivos[0]) : ((c.avisos || []).find(a => a.clase_id === 'integracion') ? textoMot(c.avisos.find(a => a.clase_id === 'integracion')) : ''),
      trafficker: nombre(d, c.equipo?.trafficker) || 'sin trafficker', account: nombre(d, c.equipo?.account) || 'sin account',
      leads7: cuentaMetaError508(c)?null:conteoMeta508(c.leads?.['7d']), deltaMeta508:deltaMeta508(c,d,ctx.hoy||hoyMadrid()), creativos508:creativosMatriz508(c,d,ctx.hoy||hoyMadrid()), gasto7: c.gasto?.['7d'] ?? null, cplref: c.cpl_resumen?.ref ?? null, cita: c.coste_por_cita?.coste_por_cita_14d ?? null,
    }));
    const soloUnTrafficker = new Set(filasT.map(c => c.trafficker)).size <= 1;
    caja.replaceChildren(tablaDensa({
      filas: filasT, orden: { clave: 'grav', dir: 'asc' }, porPagina: 12, apilable:true,
      buscar: { campos: ['nombre', 'trafficker', 'account', 'motivo'], placeholder: 'Buscar cliente, trafficker o motivo' },
      filtros: [new Set(filasT.map(c => c.trafficker)).size > 1 ? { clave: 'trafficker', titulo: 'Trafficker' } : null, { clave: 'account', titulo: 'Account' }].filter(Boolean),
      columnas: [
        { clave: 'nombre', titulo: 'Cliente', principal: true, celda: c => h('span', { class: 'celda-cli' }, logoCliente(c), h('span',{class:'paid-nombre-401'},c.nombre), esTienda(c) ? h('span', { class: 'chip gris sin-punto', title: NOTA_TIENDA }, 'tienda online') : null) },
        { clave: 'grav', titulo: 'Estado', tituloCompleto:'Semáforo del cliente', celda: c => h('span', { title: `Gravedad del cliente; Paid: ${GRAV[c.severidad]?.t || 'Sin dato'}. Consulta el detalle para la evidencia de publicidad.` }, chipCli(c)) },
        { clave: 'trafficker', titulo: 'Traf.', tituloCompleto:'Trafficker responsable', celda: c => c.equipo?.trafficker ? h('span', {title:c.trafficker}, c.trafficker) : chipEstado('ambar', 'sin trafficker') },
        { clave: 'leads7', titulo: 'Meta 7d', tituloCompleto:'Contador de resultados Meta · 7 días; no acredita cualificación', num: true, celda: c => c.panelEspecialista.cuentaError ? '—' : c.leads7 === null ? '—' : h('span', { style: NOWRAP, title:'Contador Meta de siete días; tipo de evento y cualificación en el detalle.' }, num(c.leads7), c.deltaMeta508===null?null:h('span',{class:'sub',title:'Variación de eventos Meta del mismo tipo, dos ventanas de siete días consecutivas acreditadas; no cualificación ni conversión CRM.'},` ${c.deltaMeta508>0?'▲':c.deltaMeta508<0?'▼':'='} ${num(Math.abs(c.deltaMeta508))} %`)) },
        { clave: 'gasto7', titulo:'Gasto', tituloCompleto:'Gasto Meta · 7 días, moneda de la cuenta', num:true, celda:c=>{
          if(!c.dinero)return candado('Reservado');
          const v=c.gasto7,moneda=c.cuenta_meta?.moneda;
          if(c.panelEspecialista.cuentaError||typeof v!=='number'||!Number.isFinite(v)||v<0)return '—';
          return h('span',{style:NOWRAP,title:`Gasto Meta · ${d.ventanas?.['7d']?.join(' a ')||'ventana de siete días'} · moneda ${moneda||'por confirmar'}`},moneda==='EUR'?eur(v):`${num(v,2)}${typeof moneda==='string'&&/^[A-Z]{3}$/.test(moneda)?' '+moneda:''}`);
        } },
        { clave: 'cplref', titulo: 'CPL', tituloCompleto:'Coste por lead · objetivo y evidencia en el detalle', num:true, celda:c=>{
          if(!c.dinero)return candado('Reservado');
          const p=c.panelEspecialista,m=c._cplMedicion;
          const valor=p.real===null?(p.referenciaAnterior==null?'—':`${eur(p.referenciaAnterior)}†`):eur(p.real);
          const objetivo=p.objetivo===null?'—':`${eur(p.objetivo)}${m?.objetivoVigente?'':'‡'}`;
          return h('span',{class:`chip ${m?.evaluable?m.estado:'gris'} sin-punto`,title:`${m?.nota||'CPL sin comparación acreditada'}. Objetivo: ${objetivo}. Datos hasta ${p.hasta||'sin fecha'}. † Referencia anterior: unidad pendiente, no CPL real. ‡ Objetivo pendiente de ratificar. — Sin dato.`},`${valor}`);
        } },
        { clave:'cpm',titulo:'CPM',tituloCompleto:'Coste por mil impresiones · referencia de cuenta en copia local',num:true,ordenable:false,celda:c=>{
          if(!c.dinero)return candado('Reservado');
          const r=referenciaCpm417(c,d);
          return r?h('span',{class:'chip gris sin-punto',title:`CPM de cuenta en copia local: ${r.desde} a ${r.hasta}. Lectura ${r.fecha_lectura}; zona y cobertura originales pendientes. § Referencia histórica, no medición actual ni cumplimiento.`},`${eur(r.coste_por_mil)}§`):h('span',{title:'Sin referencia CPM válida para esta cuenta y ventana.'},'—');
        } },
        { clave:'objetivoCpl',titulo:'Obj. CPL',tituloCompleto:'Objetivo propio de coste por lead; vigencia y evidencia en el detalle',num:true,ordenable:false,celda:c=>{
          if(!c.dinero)return candado('Reservado');
          const m=c._cplMedicion,v=m?.objetivo;
          if(typeof v!=='number'||!Number.isFinite(v)||v<=0)return h('span',{title:'Sin objetivo propio válido; no se aplica un objetivo por defecto.'},'—');
          return h('span',{class:'chip gris sin-punto',title:m.objetivoVigente?'Objetivo propio con vigencia acreditada; no acredita cumplimiento del CPL.':'‡ Objetivo registrado pendiente de ratificar vigencia; no acredita cumplimiento del CPL.'},`${eur(v)}${m.objetivoVigente?'':'‡'}`);
        } },
        { clave:'creativos',titulo:'Anun.',tituloCompleto:'Anuncios con señales en muestra parcial; cada anuncio se cuenta una vez, no cantidad de señales',ordenable:false,celda:c=>h('span',{title:`Anuncios con señales observadas en la muestra del generador; cada anuncio se cuenta una vez, no la cantidad de señales; cobertura parcial; no confirma fatiga ni inventario completo. Lectura de anuncios: ${lecturaAnunciosPaid4(d,ctx.hoy||hoyMadrid())||'sin fecha válida'}. Antigüedad del creativo: sin dato.`},c.creativos508===null?'—':num(c.creativos508.valor)) },
        { clave:'pendiente',titulo:'Ver',tituloCompleto:'Detalle de cuenta y registro de trabajo',ordenable:false,celda:c=>celdaRevisionCompacta243(ctx,d,c,detalleCuenta243) },
      ].filter(Boolean).filter(col => !(col.clave === 'trafficker' && soloUnTrafficker)),
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
    h('div', { class: 'pila', style: { gap: S[2], padding: `${S[2]} var(--relleno) 0` } },
      h('small',{class:'sub',title:'Esta matriz conserva su ventana de siete días de la copia; el selector general de periodo no cambia sus cifras. CPL y CPM pueden ser referencias con otra cobertura: consulta el detalle.'},'Matriz Meta · 7 días de la copia · periodo fijo'),
      // Ronda U: los filtros, en una línea plegada también en el ordenador (antes 3 filas de chips encima de la tabla)
      h('details', { class: 'que-es' },
        h('summary', { style: { display: 'flex', alignItems: 'center', gap: S[2], minHeight: '36px', fontWeight: '600' } }, icono('filtro', { clase: 's' }), resumen,
          h('span', { class: 'sub', style: { fontWeight: '400' } }, '· gravedad, dónde se rompe y plataforma')),
        h('div', { class: 'pila', style: { gap: S[2], marginTop: S[2] } }, ...filtros, movil ? hueSel : null)),
      f?.aviso === 'objetivo' ? avisoParcial('Solo las cuentas activas sin objetivo de coste por cita cargado. Vuelve a «Captación» para quitar el filtro.', { tipo: 'info' }) : null),
    caja,detalleCuenta243,
    h('p',{class:'sub',style:{padding:'10px 16px',margin:'0',fontSize:'12px'}},`Copia hasta ${fDiaRO(d.datos_hasta)} · Gasto: inversión Meta · CPL: coste por evento lead · CPM: coste por mil impresiones · Obj. CPL: objetivo propio · Anun.: anuncios con señales en muestra parcial · — sin dato · † referencia anterior, unidad pendiente · ‡ objetivo por confirmar · § CPM histórico, zona y cobertura pendientes. Creativos: señales por contrastar. Abre una fila para revisar fuentes y acciones.`),
    h('style',{}, `@media(min-width:641px){[data-paid-cuentas-243] .tabla-densa table{table-layout:fixed;width:100%;min-width:900px}[data-paid-cuentas-243] table.densa th,[data-paid-cuentas-243] table.densa td{padding:5px 6px;font-size:13px;line-height:1.3;overflow-wrap:anywhere}[data-paid-cuentas-243] table.densa th{white-space:normal;overflow-wrap:normal;word-break:normal}[data-paid-cuentas-243] table.densa th button{display:block;padding:0;white-space:normal;max-width:100%;min-width:0;font-size:inherit;letter-spacing:0;line-height:1.3;overflow-wrap:normal;word-break:normal}[data-paid-cuentas-243] table.densa th:first-child{width:18%}[data-paid-cuentas-243] table.densa th:last-child{width:10%}[data-paid-cuentas-243] .celda-cli{gap:4px;min-width:0;flex-wrap:wrap}[data-paid-cuentas-243] .paid-nombre-401{min-width:80px;flex:1;overflow-wrap:normal;word-break:normal}[data-paid-cuentas-243] table.densa td .chip{max-width:100%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}[data-paid-cuentas-243] .tabla-ctl{padding:12px 16px;gap:10px}[data-paid-cuentas-243] .tabla-ctl input,[data-paid-cuentas-243] .tabla-ctl select{border-radius:10px;min-height:42px}[data-paid-cuentas-243] table.densa td{height:42px}}`)));
  el.lastElementChild?.setAttribute('data-paid-cuentas-243','');
}
// Fecha de lectura del generador; no fecha de publicación ni antigüedad del creativo.
function lecturaAnunciosPaid4(d,hoy) {
  const stamp=d?.anuncios_generado||d?.fuentes?.find?.(f=>f.id==='anuncios')?.hora;
  const dia=fechaPaid549(stamp),actual=fechaPaid549(hoy);
  return dia&&actual&&dia<=actual?stamp:null;
}
//417 · nunca convierte un agregado legacy en medición actual ni en semáforo de rendimiento.
function referenciaCpm417(c,d){
  const r=c.coste_cpm_referencia_7d,w=d.ventanas?.['7d'];
  if(!c.dinero||c.panelEspecialista?.cuentaError||c.cuenta_meta?.error||!r||r.version!=='417.1'||r.cliente_id!==c.cliente_id||r.moneda!=='EUR'||c.cuenta_meta?.moneda!=='EUR'||r.fuente!=='cache_legacy'||r.nivel!=='account_agregado_legacy'||r.estado!=='referencia_observada'||r.medicion_actual!==false||r.zona!==null||r.cobertura!=='presencia_original_no_acreditada'||!Array.isArray(w)||w.length!==2||r.desde!==w[0]||r.hasta!==w[1])return null;
  const n=x=>typeof x==='number'&&Number.isFinite(x)&&x>=0;
  if(!n(r.gasto_observado)||!Number.isSafeInteger(r.impresiones_observadas)||r.impresiones_observadas<=0||!n(r.coste_por_mil)||typeof r.fecha_lectura!=='string'||!/^\d{4}-\d{2}-\d{2}[T ]/.test(r.fecha_lectura)||typeof r.cuenta_id!=='string'||!/^[1-9][0-9]{0,29}$/.test(r.cuenta_id))return null;
  const dia=x=>{if(typeof x!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(x))return null;const t=Date.parse(x+'T00:00:00Z');return Number.isFinite(t)&&new Date(t).toISOString().slice(0,10)===x?t:null;};
  const desde=dia(r.desde),hasta=dia(r.hasta),m=/^(\d{4}-\d{2}-\d{2})[T ](\d{2}):(\d{2})(?::(\d{2})(?:\.\d{1,6})?)?(?:Z|([+-])(\d{2}):(\d{2}))?$/.exec(r.fecha_lectura);
  if(desde===null||hasta===null||hasta-desde!==6*86400000||!m||dia(m[1])===null||dia(m[1])<=hasta||+m[2]>23||+m[3]>59||+(m[4]||0)>59||m[5]&&(+m[6]>14||+m[7]>59||+m[6]===14&&+m[7]!==0))return null;
  const calculado=1000*r.gasto_observado/r.impresiones_observadas;
  if(!Number.isFinite(calculado)||Math.abs(calculado-r.coste_por_mil)>Math.max(1,calculado)*1e-10)return null;
  return r;
}
/** Ámbito del detalle Paid: no requiere mediciones Meta ni permiso de inversión. */
function ambitoDetallePaid415(ctx,cid) {
  try {
    const ids=x=>typeof x==='string'&&/^[A-Za-z0-9_-]{1,100}$/.test(x);
    if(ctx.vigente?.()===false||ctx.veModulo?.('captacion')!==true||!ids(cid))return null;
    const ps=Array.isArray(ctx.datos?.personas)?ctx.datos.personas:[];
    for(const p of [ctx.real,ctx.persona]) {
      const xs=ps.filter(x=>x?.id===p?.id);
      if(!ids(p?.id)||xs.length!==1||p.estado!=='activo'||p.activo===false||xs[0].estado!=='activo'||xs[0].activo===false||!Array.isArray(p.puestos)||!p.puestos.length||!p.puestos.every(ids)||new Set(p.puestos).size!==p.puestos.length||!Array.isArray(xs[0].puestos)||JSON.stringify([...p.puestos].sort())!==JSON.stringify([...xs[0].puestos].sort()))return null;
    }
    const cs=[ctx.clientes,ctx.clientesVisibles].map(xs=>Array.isArray(xs)?xs.filter(x=>x?.id===cid):[]);
    if(cs.some(xs=>xs.length!==1||xs[0].activo_confirmado!==true||xs[0].detalle===false)||ctx.ver?.({tipo:'cliente_detalle',cliente_id:cid})?.ok!==true)return null;
    return JSON.stringify([ctx.real,ctx.persona,ps,ctx.clientes,ctx.clientesVisibles,ctx.nivel,ctx.soloLectura,ctx.ver({tipo:'cliente_detalle',cliente_id:cid}),ctx.ver({tipo:'inversion',cliente_id:cid}),ctx.veModulo('captacion')]);
  } catch {return null;}
}
/** Detalle bajo demanda: el botón conserva teclado y evita la navegación de la fila. */
function celdaRevisionCompacta243(ctx,d,c,destino=null) {
  const p=c.panelEspecialista;
  const firma415=ctx.servidor===true?ambitoDetallePaid415(ctx,c.cliente_id):null;
  const vigente415=()=>ctx.vigente?.()!==false&&(ctx.servidor!==true||(firma415&&ambitoDetallePaid415(ctx,c.cliente_id)===firma415));
  const guard415=e=>{if(vigente415())return true;destino?._cerrar243?.();destino?.replaceChildren();detalle.replaceChildren();detalle.hidden=true;boton.setAttribute('aria-expanded','false');e?.preventDefault?.();e?.stopPropagation?.();return false;};
  const detalle=h('div',{hidden:true,style:{marginTop:'6px',minWidth:'0',textAlign:'left'},on:{click:e=>e.stopPropagation(),keydown:e=>e.stopPropagation()}});
  const boton=h('button',{type:'button',class:'bt mini','aria-expanded':'false',on:{click:e=>{
    if(!guard415(e))return;
    e.stopPropagation();const abierto=detalle.hidden;detalle.hidden=!abierto;boton.setAttribute('aria-expanded',String(abierto));
    if(abierto&&!detalle.childNodes.length)detalle.append(
      h('b',{},'Por qué'),h('p',{},c.motivo||'Sin motivo registrado'),
      h('span',{class:'fila'},(c.cuello||[]).map(k=>chipCuello(k))),
      h('p',{},p.accion),
      c.dinero?h('p',{},`CPL: datos hasta ${p.hasta||'sin fecha'}${p.datoVigente?'':' · lectura anterior'}. Objetivo ${p.objetivo===null?'sin confirmar':`${eur(p.objetivo)} · ${c.objetivo?.cuando||'fecha por confirmar'} · ${c._cplMedicion?.objetivoVigente?'vigente acreditado':'pendiente de ratificar'}`}`):null,
      (r=>r?h('p',{},`CPM histórico: ${eur(r.coste_por_mil)} · ${num(r.impresiones_observadas)} impresiones · gasto ${eur(r.gasto_observado)} · ${r.desde} a ${r.hasta}. Lectura ${r.fecha_lectura}; zona y cobertura pendientes. No medición actual.`):null)(referenciaCpm417(c,d)),
      h('p',{},`Días sin resultados Meta: ${p.racha==null||cuentaMetaError508(c)?'sin dato':`${p.racha.completa?'':'≥ '}${p.racha.dias}`} · hasta ${p.racha?.hasta||'sin fecha'}. Contador de la copia; no acredita ausencia de leads.`),
      h('p',{},`Lectura de anuncios: ${lecturaAnunciosPaid4(d,ctx.hoy||hoyMadrid())||'sin fecha válida'}. Antigüedad del creativo: sin dato. Muestra parcial del generador; contrastar, no certifica fatiga.`),
      h('p',{},'CPC y CTR de cuenta: sin fuente compatible en esta matriz. CPC: coste por clic; CTR: porcentaje de clics. No se reconstruyen a partir de anuncios ni de otra cuenta.'),
      h('p',{},'Leads recibidos; cualificación no instrumentada aquí.'),
      ctx.nivel==='resumen'?null:celdaHoy(ctx,d,c),
      h('a',{href:`#/captacion/${c.cliente_id}`},'Abrir cuenta y fuentes'));
    if(destino){
      if(abierto){
        destino._cerrar243?.();detalle.hidden=false;boton.setAttribute('aria-expanded','true');
        const cerrar=()=>{detalle.hidden=true;boton.setAttribute('aria-expanded','false');destino.replaceChildren();destino._cerrar243=null;};
        destino._cerrar243=cerrar;
        destino.replaceChildren(h('div',{class:'pila',style:{padding:'16px',borderTop:'1px solid var(--line)',gap:'12px'}},h('div',{class:'fila',style:{justifyContent:'space-between'}},h('h3',{},c.nombre),h('button',{type:'button',class:'bt mini',on:{click:()=>{cerrar();boton.focus?.();}}},'Cerrar detalle')),detalle));
        destino.focus?.({preventScroll:true});destino.scrollIntoView?.({block:'start',behavior:'smooth'});
      }else{destino._cerrar243?.();}
    }
  }}},ctx.nivel!=='resumen'&&c.meta_activa&&!ctx.soloLectura?'Ver':'Ver');
  boton.setAttribute('title',p.accion);
  detalle.addEventListener('click',e=>guard415(e),true);
  detalle.addEventListener('keydown',e=>guard415(e),true);
  return h('span',{class:'pila',style:{gap:'2px'}},boton,destino?null:detalle);
}
/** Celda «Qué cambió hoy»: lo apuntado hoy o el último apunte, y «Apuntar» (editor en la propia fila, sin abrir la tarjeta). */
function celdaHoy(ctx, d, c) {
  const caja = h('span', { style: { display: 'grid', gap: S[1], minWidth: '200px', maxWidth: '280px' }, on: { click: e => e.stopPropagation(), keydown: e => e.stopPropagation() } });
  const pintar = () => {
    const l = d.bitacora?.get(c.cliente_id) || [];
    const hoyA = l.find(a => !a._recibo516 && diaDe(a) && ctx.fechas?.esHoy?.(diaDe(a)));
    const ult = hoyA || l[0];
    const texto = ult ? h('span', { class: hoyA ? null : 'sub', style: { whiteSpace: 'normal', overflowWrap: 'anywhere' } }, hoyA ? '✓ ' : '', ult.texto, h('span', { class: 'sub' }, ` · ${cuandoBit(ctx, ult)}`))
      : h('span', { class: 'sub' }, c.meta_activa ? 'Sin apuntar hoy' : 'Sin pauta');
    const ed = h('div', { hidden: true });
    const b = c.meta_activa && !ctx.soloLectura ? h('button', { type: 'button', class: 'bt mini', 'aria-expanded': 'false', on: { click: () => {
      const abrir = ed.hidden; ed.hidden = !abrir; b.setAttribute('aria-expanded', String(abrir));
      if (abrir && !ed.childNodes.length) ed.append(editorBitacora(ctx, d, c, { compacto: true, alHecho: pintar }));
      if (abrir) ed.querySelector('input')?.focus();
    } } }, icono('editar'), hoyA ? 'Añadir' : 'Apuntar') : null;
    caja.replaceChildren(texto, ...(b ? [h('span', {}, b)] : []), ed);
  };
  pintar();
  return caja;
}
function deltaMini(a, b) {
  const v = variacion(a, b);
  if (v === null) return null;
  return h('span', { class: 'sub', title: 'Frente a los 7 días anteriores' }, `${v > 0 ? '▲' : v < 0 ? '▼' : '='} ${num(Math.abs(v))} %`);
}
function celdaCpl(c, techo, d={}) {
  if (!c.dinero) return candado('—');
  const r = c.cpl_resumen || {};
  if (r.ref === null || r.ref === undefined) return h('span', { class: 'sub', title: c.muestra?.nota || '' }, c.meta_activa ? 'sin muestra' : '—');
  // Color único de la app para el coste por lead (colorCifra); con objetivo propio cargado, contra su objetivo.
  const medicion=medirCplPaid(c,d,hoyMadrid());
  const e=medicion.estado;
  const valor=medicion.real??medicion.referenciaAnterior;
  return h('span', { style: { display: 'inline-grid', justifyItems: 'end', gap: S[1] } }, valor===null?'Sin dato':chipEstado(e, eur(valor)),
    h('span', { class: 'sub' }, `${medicion.real===null?'Referencia anterior · ':''}${r.ref_base||'ventana sin confirmar'} · ${medicion.nota}`));
}
function celdaCita(c, d) {
  if (!c.dinero) return candado('—');
  const v=referenciaCita299(c.coste_por_cita);
  return h('span',{title:'Gasto y citas sin unión por identidad: referencia anterior, no coste de captación ni cumplimiento.'},v===null?'Sin dato':chipEstado('gris',`${eur(v)} · ref.`));
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
  const observado648 = resumenEquipo648(filas, d);

  const cifrasEquipo416=tiles([
    tile({ icono: 'eq', etiqueta: 'Traffickers con 5 o más cuentas en rojo', valor: observado648.gravedad ? filasT.filter(x => x.id !== '—' && x.rojos >= ambar + 1).length : null, unidad: `de ${filasT.filter(x => x.id !== '—').length}`,
      estado: filasT.some(x => x.id !== '—' && x.rojos > ambar) ? 'rojo' : filasT.some(x => x.id !== '—' && x.rojos > verde) ? 'ambar' : 'gris',
      contexto: `Señales observadas en ${observado648.gravedad} de ${filas.length} cuentas; referencia ámbar ${verde + 1}-${ambar} y rojo ≥ ${ambar + 1}. Cobertura no exhaustiva; cero no acredita ausencia de críticos.`, medible: 'medias', frescura: fuenteDe(d, 'meta') }),
    total.conDinero.length ? tile({ icono: 'cartera', etiqueta: 'Inversión gestionada · septiembre', valor: eur(total.gastoMesAnt), comparacion: { texto: `${eur(total.gasto7)} en los últimos 7 días` },
      contexto: 'Solo Meta. Google Ads va aparte (muestra manual) hasta la clave de Windsor.', medible: 'medias', medibleDetalle: 'Falta Google Ads y TikTok', frescura: fuenteDe(d, 'meta') }) : null,
    tile({ icono: 'flag', etiqueta: 'Señales de cuentas paradas', valor: observado648.paradas, unidad: `en ${observado648.paradasConDato} de ${total.activas.length} activas con dato`,
      estado: observado648.paradas > 0 ? 'rojo' : 'gris', contexto: 'Gasto ayer cero o último gasto anterior al corte: señal guardada por contrastar. Cobertura no exhaustiva; no confirma campañas paradas.', medible: 'medias', frescura: fuenteDe(d, 'meta') }),
    tile({ icono: 'rocket', etiqueta: 'Arranques con ganador en el mes 1', valor: (() => { const n = filas.filter(c => c.nuevo && c.meta_activa); return n.length ? `${n.filter(c => c.anuncios?.ganadoras).length} de ${n.length}` : null; })(),
      estado: 'gris', contexto: 'En el arranque, 3 contactos o más a 45 € o menos.', medible: 'hoy', frescura: fuenteDe(d, 'anuncios') }),
  ].filter(Boolean));

  el.append(h('section', {'data-paid-equipo':'416',style:{minWidth:'0'}},
    h('style',{},'[data-paid-equipo="416"] .tabla-scroll{overflow-x:auto;max-width:100%}[data-paid-equipo="416"] table.densa{table-layout:fixed;width:100%;min-width:940px}[data-paid-equipo="416"] table.densa th,[data-paid-equipo="416"] table.densa td{padding:5px 6px;font-size:13px;line-height:1.3;overflow-wrap:normal;word-break:normal}[data-paid-equipo="416"] table.densa th:first-child{width:180px}[data-paid-equipo="416"] table.densa th:nth-child(2){width:160px}[data-paid-equipo="416"] table.densa th{white-space:normal}[data-paid-equipo="416"] table.densa td{height:44px}[data-paid-equipo="416"] table.densa td:first-child>span{white-space:normal}'),
    panel({ titulo: 'Cuentas por trafficker', icono: 'eq', sub: 'Pulsa una fila para ver sus cuentas. Referencia de coste anterior; no objetivo acordado.' },
    tablaApilable({
      filas: filasT,
      columnas: [
        { clave: 'nombre', titulo: 'Trafficker', principal: true, celda: x => h('span', { class: 'fila', style: { gap: S[2], flexWrap: 'nowrap' } }, h('span', { class: 'av s', 'aria-hidden': 'true' }, iniciales(x.nombre)), x.nombre) },
        // V2 (B-A3): la misma cartera con nombre que Mi día y Personas (carteras_publicidad)
        { clave: 'cuentas', titulo: 'Cartera', num: true, celda: x => (x.cp ? h('span', { style: { display: 'inline-grid', justifyItems: 'end' } }, `${x.cp.cartera} clientes${x.cp.apoyo ? ` + ${x.cp.apoyo} de apoyo` : ''}`, h('small', { class: 'sub' }, `${x.cp.con_meta} con Meta · ${x.cp.meta_encendida} encendidas`)) : `${x.activas} encendidas de ${x.cuentas}`) },
        { clave: 'rojos', titulo: 'Críticos', num: true, celda: x => chipEstado('gris',`${x.rojos}${x.atencion?` · +${x.atencion} a vigilar`:''}`) },
        { clave: 'techo', titulo:'Ref. coste', num: true, celda: x => h('span',{title:`Referencia anterior ${d.parametros.techo_cpl} € · no objetivo: ${x.techoTxt}`},x.techoTxt) },
        { clave: 'gasto7', titulo: 'Gasto 7 d', num: true, celda: x => (x.gasto7 === null ? candado('—') : eur(x.gasto7)) },
        { clave: 'gastoMes', titulo: 'Septiembre', num: true, celda: x => (x.gastoMes === null ? candado('—') : eur(x.gastoMes)) },
        { clave: 'cansadas', titulo: 'Señales / rechazos', num: true, celda: x => h('span',{title:`${x.cansadas} anuncios con señal de cansada · ${x.rechazados} rechazados`},`${x.cansadas} / ${x.rechazados}`) },
        { clave: 'objetivos', titulo: 'Objetivos', num: true, celda:x=>h('span',{title:'Cuentas con objetivo cargado / activas; no acredita objetivo ratificado ni cumplimiento.'},x.objetivos) },
      ],
      alPulsar: x => { try { sessionStorage.setItem('captacion.filtro', JSON.stringify({ trafficker: x.id })); } catch { /* */ } ctx.navegar(`captacion/~trafficker/${x.id}`); },
      etiquetaFila: x => `${x.nombre}: ${fmt.plural(x.rojos, 'cuenta crítica', 'cuentas críticas')}. Ver sus cuentas`,
    }))));
  el.append(plegablePaid411('Cifras y referencias por trafficker',cifrasEquipo416,
    h('p',{class:'sub'},`Ref. coste: comparación anterior con ${d.parametros.techo_cpl} €; no objetivo acordado. Responsable: tabla de asignaciones, no el «PM» escrito a mano de la Torre. Señales / rechazos conserva los recuentos de anuncios; no confirma fatiga actual.`)));

  // comparativa por nicho
  const nichos = new Map();
  for (const c of filas.filter(x => x.meta_activa)) {
    const k = c.nicho || 'Sin nicho';
    if (!nichos.has(k)) nichos.set(k, []);
    nichos.get(k).push(c);
  }
  const filasN = [...nichos.entries()].map(([k, cs]) => {
    const resumen = resumenNichoPaid671(cs,d,ctx.hoy||hoyMadrid());
    return { nicho: k, nombres: cs.map(c => c.nombre).join(', '), ...resumen };
  }).sort((a, b) => (b.leads??-1) - (a.leads??-1));
  el.append(plegablePaid411('Comparativa por nicho · 7 días',
    panel({ titulo: 'Comparativa por nicho · 7 días', icono: 'capas', sub: 'Solo cuentas con pauta activa. El nicho sale de la descripción del cliente.' },
      tablaApilable({ filas: filasN, columnas: [
        { clave: 'nicho', titulo: 'Nicho', principal: true, celda: x => h('span', { style: { display: 'grid' } }, h('b', {}, x.nicho), h('small', { class: 'sub' }, x.nombres)) },
        { clave: 'cuentas', titulo: 'Cuentas', num: true },
        { clave: 'leads', titulo: 'Leads obs.', num: true, celda: x => x.leads===null?'—':num(x.leads) },
        { clave: 'conDato', titulo: 'Datos', tituloCompleto:'Cuentas con descriptor válido / cuentas del nicho; no acredita cobertura total de Meta', num:true, celda:x=>`${x.conDato}/${x.cuentas}` },
        { clave: 'cpl', titulo: 'CPL', tituloCompleto:'Misma semana, evento lead y moneda EUR; todas las cuentas con gasto autorizado. No mide cualificación ni ventas', num: true, celda: x => x.cpl===null?'—':eur(x.cpl) },
      ] }))));
  el.append(plegablePaid411('Auditoría semanal',pAuditoria(ctx, d, filas)));
}

/** Auditoría semanal: el trafficker apunta cortar / escalar / no tocar por cuenta (simulación, rastro). */
function pAuditoria(ctx, d, filas) {
  const activas = filas.filter(c => c.meta_activa);
  const lista = h('div', { class: 'pila', style: { gap: S[2] } });
  const hechas = h('div');
  const resto = h('div', { class: 'pila', style: { gap: S[2] } });
  let desplegable;
  let raiz,lectura=0;
  const firma=()=>JSON.stringify([ctx.real?.id,ctx.persona?.id,[...(ctx.real?.puestos||[])].sort(),[...(ctx.persona?.puestos||[])].sort()]);
  const identidad=firma();
  const vivo=()=>{
    if(!raiz?.isConnected)return false;
    if(ctx.vigente?.()===false||firma()!==identidad){lectura++;lista.replaceChildren();resto.replaceChildren();desplegable?.replaceChildren();hechas.replaceChildren();return false;}
    return true;
  };
  const cargarHechas = async () => {
    if(!vivo())return;
    const turno=++lectura;
    if (!ctx.servidor) { hechas.replaceChildren(h('p', { class: 'sub' }, 'Sin servidor: las decisiones quedan solo en el rastro de esta sesión.')); return; }
    try {
      const r = await ctx.api('acciones?modulo=captacion');
      if(!vivo()||turno!==lectura)return;
      const decisiones = (r.acciones || []).filter(a => a.tipo === 'auditoria_semanal');
      hechas.replaceChildren(decisiones.length
        ? listaConIcono(decisiones.slice(0, 6).map(a => ({ icono: 'check', estado: 'verde', texto: `${a.objeto} · ${a.texto}`, extra: `${nombre(d, a.quien) || a.quien} · ${fDiaRO(a.creada || '')}` })))
        : h('div', {}, h('p', { class: 'sub' }, 'Sin decisiones en la respuesta disponible'),
          h('p', { class: 'sub' }, 'Esta lectura no aplica un filtro de semana.')));
    } catch (e) { if(!vivo()||turno!==lectura)return;hechas.replaceChildren(h('p', { class: 'sub' }, `No se pudieron leer: ${e.message}`)); }
  };
  for (const [indice,c] of activas.entries()) {
    (indice<6?lista:resto).append(h('div', { class: 'fila', style: { justifyContent: 'space-between', borderBottom: '1px solid var(--line-soft)', paddingBottom: S[2] } },
      h('span', { class: 'celda-cli' }, logoCliente(c), c.nombre, chipCli(c)),
      h('span', { class: 'fila', style: { gap: S[1] } }, ['Cortar', 'Escalar', 'No tocar'].map(dec => botonConfirmar({
        texto: dec, mini: true, pregunta: `¿${dec} en ${c.nombre}?`, confirmar: 'Apuntar', soloLectura: ctx.soloLectura,
        alConfirmar: async () => {
          if(!vivo()||ctx.soloLectura)throw new Error('La vista ha cambiado; no se confirma esta decisión.');
          await ctx.accion({ herramienta: 'app', tipo: 'auditoria_semanal', objeto: c.nombre, cliente_id: c.cliente_id, texto: dec,
            vista_previa: `Auditoría semanal: «${dec}» en ${c.nombre}. Queda en el rastro; Valeria lo ve en su vista.` });
          if(!vivo()||ctx.soloLectura)throw new Error('La vista ha cambiado; no se confirma esta decisión.');
          await cargarHechas();
          if(!vivo()||ctx.soloLectura)throw new Error('La vista ha cambiado; no se confirma esta decisión.');
          return `«${dec}» apuntado (simulación)`;
        },
      })))));
  }
  if(activas.length>6){
    desplegable=h('details', { on: { toggle: () => { if(!vivo())desplegable.replaceChildren(); } } },
      h('summary', {}, `Resto de cuentas activas · ${activas.length-6}`), resto);
    lista.append(desplegable);
  }
  raiz=panel({ titulo: 'Auditoría semanal', icono: 'check', sub: 'Una decisión por cuenta activa: cortar, escalar o no tocar. Queda en el rastro (el indicador «auditoría el mismo día» todavía no se mide).' },
    h('div', { class: 'cuerpo pila' }, activas.length ? lista : vacio({ icono: 'check', titulo: 'Sin cuentas activas que auditar' }), h('h3', { class: 'titulo-seccion' }, 'Últimas decisiones'), hechas));
  queueMicrotask(()=>{if(vivo())cargarHechas();});
  return raiz;
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
    opciones: [{ valor: 'aviso', texto: 'Con señales', icono: 'alert', cuenta: cnt('cansada') + cnt('vigilar'), cuentaEstado: 'gris' },
      { valor: 'cansada', texto: 'Cansadas', icono: 'baja', cuenta: cnt('cansada'), cuentaEstado: 'gris' },
      { valor: 'ganadora', texto: 'Ganadoras', icono: 'star', cuenta: cnt('ganadora') }, { valor: '', texto: 'Todas', cuenta: ads.length }],
    alCambiar: () => pintar(),
  });
  const caja = h('div');
  const pintar = () => {
    if(ctx.vigente?.()===false){caja.replaceChildren();return;}
    const v = chips.valor();
    const base = ads.filter(a => !v || (v === 'aviso' ? ['cansada', 'vigilar'].includes(a.estado) : a.estado === v));
    caja.replaceChildren(tablaDensa({
      filas: base, orden: { clave: 'frecuencia_7d', dir: 'desc' },
      buscar: { campos: ['nombre', 'cliente', 'campana'], placeholder: 'Buscar anuncio o cliente' },
      filtros: [{ clave: 'cliente', titulo: 'Cliente' }],
      columnas: [
        { clave: 'nombre', titulo: 'Anuncio', principal: true, celda: a => h('span', { title:`${a.nombre||'Sin nombre'} · ${a.cliente} · ${distingue(a)}`, style: { display: 'grid', gap: S[1] } }, h('b', {}, a.nombre || '—'), h('small', { class: 'sub' }, a.cliente)) },
        { clave: 'estado', titulo: 'Estado', celda: a => h('span', { style: { display: 'grid', gap: S[1] } },
          chipEstado('gris', a.estado === 'cansada' ? 'Cansada' : a.estado === 'vigilar' ? 'Vigilar' : a.estado === 'ganadora' ? 'Ganadora' : 'Normal'),
          a.senales?.length ? h('span', { title:a.senales.join(' + '),class:'sub' }, `${a.senales.length} ${a.senales.length===1?'señal':'señales'}`) : null) },
        { clave: 'frecuencia_7d', titulo: 'Frec.', tituloCompleto:'Frecuencia de impresión · 7 días', num: true, celda: a => (typeof a.frecuencia_7d!=='number'||!Number.isFinite(a.frecuencia_7d)||a.frecuencia_7d<0 ? '—' : h('span',{title:'Frecuencia registrada en la copia; referencia sin evaluación de fatiga.'},chipEstado('gris', num(a.frecuencia_7d, 1), { punto: false }))) },
        { clave: 'ctr_7d', titulo: 'CTR', tituloCompleto:'Porcentaje de clics · 7 días; caída frente al periodo anterior', num: true, celda: a => (typeof a.ctr_7d!=='number'||!Number.isFinite(a.ctr_7d)||a.ctr_7d<0 ? '—' : h('span', { style: NOWRAP }, `${num(a.ctr_7d, 2)} %`, a.caida_ctr_pct !== null && a.caida_ctr_pct !== undefined ? h('small', { class: 'sub' }, ` (${a.caida_ctr_pct > 0 ? '−' : '+'}${num(Math.abs(a.caida_ctr_pct))} %)`) : null)) },
        { clave: 'leads_7d', titulo: 'Meta 7d', tituloCompleto:'Contador Meta · 7 días; tipo de evento y cualificación pendientes', num: true, celda: a => a.leads_7d==null?'—':num(a.leads_7d) },
        { clave: 'cpl_7d', titulo: 'Coste†', tituloCompleto:'Coste registrado · unidad pendiente; no acredita CPL real', num: true, celda: a => {
          if(!a.dinero)return candado('—');
          const valido=v=>typeof v==='number'&&Number.isFinite(v)&&v>=0;
          return valido(a.cpl_7d)?h('span',{title:'Referencia de coste registrada · 7 días; unidad pendiente.'},`${eur(a.cpl_7d)}†`):valido(a.cpl_30d)?h('span',{title:'Referencia de coste registrada · 30 días; unidad pendiente.'},`${eur(a.cpl_30d)}† · 30d`):'—';
        } },
        { clave: 'ir', titulo: 'Abrir', ordenable: false, celda: a => (a.enlace ? h('a', { class: 'bt mini', href: a.enlace, target: '_blank', rel: 'noopener' }, icono('ext'), 'Meta') : '—') },
        { clave: 'autor', titulo: 'Autor', celda: a => (a.autor ? nombre(d, a.autor) : h('span', { class: 'dim', title: 'Iniciales del autor en el nombre del anuncio desde el próximo lanzamiento' }, 'sin autor')) },
      ],
      alPulsar: a => {if(ctx.vigente?.()!==false)ctx.navegar(`captacion/${a.cliente_id}`);},
      etiquetaFila: a => `${a.nombre} de ${a.cliente}: ${a.estado}. Abrir tarjeta del cliente`,
      vacio: { titulo: 'Ningún anuncio con estas señales', porque: 'No hay anuncios en este filtro de la copia disponible; no acredita ausencia de señales ni necesidad de cambios.', celebrar: false },
    }));
  };
  pintar();
  el.append(panel({ titulo: 'Anuncios de las cuentas activas · 7 días', icono: 'spark', sub: 'Señales de la copia; abre una cuenta para revisar fuentes y acciones.' },
    h('div', { class: 'cuerpo' },typeof matchMedia==='function'&&matchMedia('(max-width:640px)').matches?h('details',{class:'que-es'},h('summary',{},'Filtros de esta vista'),chips):chips), caja,h('details',{class:'que-es',style:{padding:'8px 16px'}},h('summary',{},'Reglas de referencia'),h('p',{},'Cansada: dos señales a la vez. Ganadora: gasto ≥ 10 veces el objetivo con coste ≤ objetivo; regla anterior de arranque: 3 contactos a ≤ 45 €. Son etiquetas de la copia, pendientes de contraste; no acreditan rendimiento actual ni cualificación.')),h('p',{class:'sub',style:{padding:'8px 16px'}},`Muestra parcial de anuncios recibidos; no inventario completo. Lectura de anuncios: ${lecturaAnunciosPaid4(d,ctx.hoy||hoyMadrid())||'sin fecha válida'}. Antigüedad del creativo: sin dato. Señales de la copia, pendientes de contraste. † Coste registrado con unidad pendiente; no CPL real ni compras. Meta7d no acredita cualificación. Abre la cuenta para revisar fuentes y acciones.`)));
  el.lastElementChild?.setAttribute('data-paid-creatividades-425','');
  el.append(h('style',{},`@media(min-width:641px){[data-paid-creatividades-425] table.densa{table-layout:fixed;width:100%;min-width:900px}[data-paid-creatividades-425] table.densa th:first-child{width:25%}[data-paid-creatividades-425] table.densa th,[data-paid-creatividades-425] table.densa td{padding-left:6px;padding-right:6px;overflow-wrap:anywhere}[data-paid-creatividades-425] table.densa th button{padding-left:6px;padding-right:6px;white-space:normal}[data-paid-creatividades-425] table.densa td .chip{max-width:100%;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}`));
  const lim = filas.filter(c => c.anuncios?.conjuntos_con_dato).map(c => ({ ...c, lim: c.anuncios.aprendizaje_limitado, con: c.anuncios.conjuntos_con_dato }));
  el.append(h('div', { class: 'dos' },
    panel({ titulo: 'Rechazados o con problemas', icono: 'alert', sub: 'Señales de rechazo guardadas; fechas y cobertura por contrastar.' },
      tablaApilable({ filas: prob, columnas: [
        { clave: 'nombre', titulo: 'Anuncio', principal: true, celda: p => h('span', { style: { display: 'grid' } }, h('b', {}, p.nombre), h('small', { class: 'sub' }, p.cliente)) },
        { clave: 'estado', titulo: 'Estado', celda: p => chipEstado(p.estado === 'DISAPPROVED' ? 'rojo' : 'ambar', p.estado === 'DISAPPROVED' ? 'Rechazado' : 'Con problemas') },
        { clave: 'desde', titulo: 'Desde', celda: p => fDiaRO(p.desde) },
        { clave: 'motivo', titulo: 'Motivo de Meta', celda: p => h('span', { class: 'sub' }, (p.motivo || 'Sin motivo en la respuesta').slice(0, 140)) },
      ], vacio: { titulo: 'Sin rechazos en esta copia', texto: 'La cobertura parcial no acredita ausencia de problemas actuales.',celebrar:false } })),
    panel({ titulo: 'Conjuntos en aprendizaje limitado', icono: 'medidor', sub: 'Recuento de la copia; fechas y cobertura pendientes de contraste.' },
      tablaApilable({ filas: lim, columnas: [
        { clave: 'nombre', titulo: 'Cliente', principal: true, celda: c => h('span', { class: 'celda-cli' }, logoCliente(c), c.nombre) },
        { clave: 'lim', titulo: 'Limitados', num: true, celda: c => { const p = Math.round(c.lim / c.con * 100); return chipEstado('gris', `${c.lim} de ${c.con} · ${p} %`); } },
      ], vacio: { titulo: 'Meta no da el dato de aprendizaje', texto: 'Ningún conjunto activo trae «learning_stage_info» en estas cuentas.' } }))));
}

// ------------------------------------------------------------------ pestaña · el despacho (M6 · D-45, D-46)
function pDespacho(el, ctx, d, filas) {
  const f = filtroPendiente();
  const conGhl = filas.filter(c => c.despacho && (c.ghl?.conectado || c.meta_activa));
  const filasT = conGhl.map(c => { const m=medirEmbudoCRM(c.ghl,(d.fuentes||[]).find(x=>x.id==='ghl'),ctx.hoy||hoyMadrid()); return ({
    ...c, llegan: null, estanc:m.parados,cohorte:m.cohorte,sinEstado:m.sinEstado,
    asis:m.asistencia,citas:m.agendadas,lecturaCRM:m,
    fuga: false, // Sin unión por identidad/cohorte: el ratio legado no prueba pérdidas.
    sinGhl: !c.ghl?.conectado,
  }); });
  const chips = chipsFiltro({
    etiqueta: 'Mirar', clave: f ? null : 'captacion.despacho', valor: f?.fuga ? '' : undefined,
    opciones: [{ valor: '', texto: 'Todas', cuenta: filasT.length },
      { valor: 'estanc', texto: 'Estancados > 72 h', icono: 'clock', cuenta: filasT.filter(x => x.estanc).length, cuentaEstado:'ambar' },
      { valor: 'sinestado', texto: 'Citas sin estado', icono: 'cal', cuenta: filasT.filter(x => x.sinEstado).length, cuentaEstado:'ambar' },
      { valor: 'sincita', texto:'Sin avance de cita observado', icono: 'alert', cuenta: filasT.filter(x => x.cuello?.includes('seguimiento') && x.despacho?.sin_avance_90d === true).length },
      { valor: 'singhl', texto: 'Sin GHL', icono: 'base', cuenta: filasT.filter(x => x.sinGhl).length }],
    alCambiar: () => pintar(),
  });
  const caja = h('div');
  const pintar = () => {
    if(ctx.vigente?.()===false){caja.replaceChildren();return;}
    const elegido = chips.valor(), v=['estanc','sinestado','singhl','sincita'].includes(elegido)?elegido:'';
    const base = filasT.filter(x => !v || (v === 'estanc' && x.estanc) || (v === 'sinestado' && x.sinEstado) || (v === 'singhl' && x.sinGhl)
      || (v === 'sincita' && x.cuello?.includes('seguimiento') && x.despacho?.sin_avance_90d === true));
    caja.replaceChildren(tablaDensa({
      filas: base, orden: { clave: 'llegan', dir: 'asc' },
      buscar: { campos: ['nombre'], placeholder: 'Buscar cliente' },
      columnas: [
        { clave: 'nombre', titulo: 'Cliente', principal: true, celda: c => h('span', { class: 'celda-cli' }, logoCliente(c), c.nombre) },
        { clave: 'llegan', titulo: 'Meta / CRM', tituloCompleto:'Recuentos independientes Meta y CRM · 7 días; sin unión por identidad', num: true, celda: c => (c.sinGhl ? chipEstado('gris', 'sin GHL') : h('span', { title:`Recuentos de 7 días independientes, sin unión por identidad${c.despacho.subcuenta_sin_uso?' · uso de subcuenta por confirmar':''}.`, style:NOWRAP }, `${c.despacho.leads_meta_7d==null?'—':num(c.despacho.leads_meta_7d)} / ${c.despacho.leads_ghl_7d==null?'—':num(c.despacho.leads_ghl_7d)}`)) },
        { clave: 'estanc', titulo:'Parados >72h',tituloCompleto:'Leads sin avance observado en la etapa durante más de 72 horas; no ausencia de trabajo', num: true, celda: c => (c.sinGhl ? '—' : h('span', {title:`Sin avance observado / cohorte registrada; no ausencia de trabajo. Mayor espera registrada: ${c.despacho.horas_max_parado?num(Math.round(c.despacho.horas_max_parado/24))+' días':'sin dato'}.`,style:NOWRAP}, `${c.estanc==null?'—':num(c.estanc)} / ${c.cohorte==null?'—':num(c.cohorte)}`)) },
        { clave: 'citas', titulo: 'Citas 14d',tituloCompleto:'Citas agendadas observadas · 14 días', num: true, celda: c => (c.sinGhl ? '—' : num(c.citas)) },
        { clave: 'sinEstado', titulo: 'Sin estado', num: true, celda: c => (c.sinGhl ? '—' : c.sinEstado===null?'—':chipEstado('gris',num(c.sinEstado))) },
        { clave: 'asis', titulo: 'Asist. 14d',tituloCompleto:'Asistencia sobre resultados registrados · 14 días; no conversión', num: true, celda: c => (c.asis === null || c.asis === undefined ? h('span', { class: 'dim' }, '—') : chipEstado('gris',pct(c.asis))) },
      ],
      alPulsar: c => {if(ctx.vigente?.()!==false)ctx.navegar(`captacion/${c.cliente_id}`);},
      etiquetaFila: c => `${c.nombre}. Abrir tarjeta`,
      vacio: { titulo: 'Nada que mirar aquí', porque: 'No hay casos en el filtro de la lectura disponible; no acredita ausencia de problemas.', celebrar:false },
    }));
  };
  pintar();
  el.append(panel({ titulo: 'Qué hace el despacho con los leads', icono: 'phone', sub:'Recuentos observados, con cobertura parcial. Asistencia sólo sobre resultados registrados; no mide conversión ni ventas.' },
    h('div', { class: 'cuerpo' },typeof matchMedia==='function'&&matchMedia('(max-width:640px)').matches?h('details',{class:'que-es'},h('summary',{},'Filtros de esta vista'),chips):chips), caja,h('p',{class:'sub',style:{padding:'8px 16px'}},'Meta / CRM: recuentos independientes de 7 días, sin unión por lead. Parados: sin avance observado / cohorte; no acredita ausencia de trabajo. — sin dato.')));
  el.append(avisoParcial('Esta copia no acredita llamadas, respuesta real ni cuatro intentos por lead. Contrasta conversaciones y registros del despacho; «sin avance observado >72 h» es sólo una señal de la etapa, no de ausencia de trabajo.', { titulo: 'Todavía no se mide:' }));
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
  ['M1', 'Coste por cita atribuido', 'medias', 'Pendiente de enlazar gasto y citas; ratio anterior sólo de referencia, sin alarma de100€'],
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
  ctx.titulo(c.nombre, `Estado: ${gc(c).t} · ${g.t.toLowerCase()}${c.estado_evaluacion === 'referencia_legacy_no_recalculada' ? ' (referencia anterior)' : ''} · trafficker ${nombre(d, c.equipo?.trafficker) || 'sin asignar'} · datos hasta el ${fDiaRO(d.datos_hasta)}`);

  cont.append(h('div', { class: 'fila', style: { justifyContent: 'space-between' } },
    h('nav', { class: 'migas', 'aria-label': 'Migas' }, h('a', { href: '#/captacion' }, icono('target', { clase: 's' }), 'Captación'), h('span', { 'aria-hidden': 'true' }, '›'), h('span', { 'aria-current': 'page' }, c.nombre)),
    selectorCliente({ clientes: d.clientes.map(x => ({ id: x.cliente_id, nombre: x.nombre, logo: x.logo, responsable: `Trafficker: ${nombre(d, x.equipo?.trafficker) || 'sin asignar'}`, salud: null })),
      actual: c.cliente_id, etiqueta: 'Cambiar de cliente', detalle: x => x.responsable,
      insignia: x => chipCli(d.clientes.find(y => y.cliente_id === x.id)),
      alElegir: x => ctx.navegar(`captacion/${x.id}`) })));

  // 411: estado y enlaces a mano; equipo y contexto en una sola línea plegada.
  cont.append(cabeceraPaid411(ctx, d, c));

  // ---- motivos y avisos con su cuello (T1, T2, T11) ----
  const items = [...(c.motivos || []).map(m => ({ ...m, tipo: 'motivo' })), ...(c.avisos || []).map(a => ({ ...a, tipo: 'aviso', nivel: a.clase_id === 'integracion' ? 'atencion' : 'info' }))];
  // motivos: borde izquierdo del color de su gravedad (antes .cap-mot), texto en tinta y quién lo mueve en .sub
  const bordeMot = { rojo: 'var(--bad)', ambar: 'var(--warn)', gris: 'var(--off)' };
  const liMot = (est, ...hijos) => h('li', { style: { display: 'flex', flexWrap: 'wrap', gap: `${S[2]} ${S[3]}`, alignItems: 'flex-start', padding: `${S[3]} ${S[3]}`, border: '1px solid var(--line)', borderLeft: `3px solid ${bordeMot[est]}`, borderRadius: 'var(--r-s)', background: 'var(--card)' } }, ...hijos);
  const motivos = h('ul', { style: { display: 'grid', gap: S[2], margin: '0', padding: '0', listStyle: 'none' } }, items.length ? items.map(m => { const est = m.nivel === 'critico' ? 'rojo' : m.nivel === 'atencion' ? 'ambar' : 'gris'; return liMot(est,
    h('span', { class: `ico-c s ${est}` }, icono(CUELLO[m.clase_id]?.i || 'info')),
    h('div', { style: { flex: '1 1 220px', minWidth: '0' } }, h('div', {}, textoMot(m)), h('div', { class: 'sub', style: { marginTop: S[1] } }, `${CUELLO[m.clase_id]?.t || m.clase}${CUELLO[m.clase_id]?.quien ? ` · lo mueve: ${quienArregla(m.clase_id, c, d)}` : ''}`)),
    m.clase_id === 'integracion' ? botonTarea(ctx, c, d, 'agustina', 'Tarea a Agus', `Revisar integración: ${textoMot(m)}`) : null); }) : [liMot('gris', h('span',{class:'ico-c s gris'},icono('info')),h('div',{},'Sin motivos en esta copia; no acredita ausencia de problemas.'))]);

  // ---- cifras (T4-T7, M1) ----
  const techo = d.parametros.techo_cpl;
  const r = c.cpl_resumen || {};
  const cpc = c.coste_por_cita || {};
  const lecturaCpl=medirCplPaid(c,d,hoyMadrid());
  const t = [];
  if (c.dinero && c.cpl) {
    t.push(tile({ icono: 'target', etiqueta: 'Gasto / citas · referencia anterior', valor: referenciaCita299(cpc)===null?null:eur(referenciaCita299(cpc)),
      estado:'gris',
      comparacion: {texto:'Sin cohorte enlazada por identidad'},
      contexto:'Ratio heredado de recuentos independientes. No mide el coste atribuido a una cita ni el cumplimiento de un objetivo.',
      medible: 'medias', medibleDetalle: 'Citas = todas las del calendario de la subcuenta, no solo las que vienen de Meta', frescura: fuenteDe(d, 'ghl') }));
    if (esTienda(c)) t.push(tile({ icono: 'euro', etiqueta: `Coste registrado · unidad pendiente · ${r.ref_base || '7 días'}`, valor: lecturaCpl.referenciaAnterior===null?null:eur(lecturaCpl.referenciaAnterior), estado: 'gris',
      comparacion: {texto:'Referencia anterior; no es CPL real'},
      contexto: NOTA_TIENDA, medible: 'hoy', frescura: fuenteDe(d, 'meta') }));
    else t.push(tile({ icono: 'euro', etiqueta: `Coste por lead · ${r.ref_base || '7 días'}`, valor:lecturaCpl.real===null?null:eur(lecturaCpl.real),
      estado:lecturaCpl.estado,
      comparacion: { texto: lecturaCpl.referenciaAnterior===null?'Sin referencia anterior':`Referencia anterior ${eur(lecturaCpl.referenciaAnterior)} · comparación entre ventanas sin acreditar` },
      contexto:`${lecturaCpl.nota}. Objetivo registrado: ${lecturaCpl.objetivo===null?'sin dato':eur(lecturaCpl.objetivo)}; fecha ${lecturaCpl.fechaObjetivo||'sin confirmar'}.`,
      medible: 'hoy', frescura: fuenteDe(d, 'meta') }));
  } else if (c.cuenta_meta) {
    t.push(h('div', { class: 'tile gris' }, h('span', { class: 'tt' }, h('span', { class: 'ico-c gris' }, icono('euro')), h('span', {}, 'Coste por lead y por cita')), candado('Inversión reservada para tu acceso')));
  }
  t.push(tile({ icono: 'users', etiqueta: lecturaCpl.unidadAcreditada ? 'Eventos lead Meta · 7 días' : 'Contador Meta · 7 días', valor: c.leads ? num(c.leads['7d']) : null, estado: c.leads ? '' : 'gris',
    comparacion: c.leads ? { delta: variacion(c.leads['7d'], c.leads['7d_prev']), pct: true, texto: `frente a ${num(c.leads['7d_prev'])} los 7 anteriores` } : null,
    contexto: c.leads ? `Ayer ${num(c.leads.ayer)} · septiembre ${num(c.leads.mes_anterior)}` : 'Sin cuenta de Meta', medible: 'hoy', frescura: fuenteDe(d, 'meta') }));
  if (c.despacho) {
    t.push(tile({ icono: 'plug', etiqueta: 'Meta y CRM · 7 días', valor: c.ghl?.conectado ? num(c.despacho.leads_ghl_7d ?? null) : null,
      unidad: 'contactos CRM leídos', estado: 'gris',
      comparacion: { texto: `${num(c.despacho.leads_meta_7d ?? null)} contador Meta; recuento independiente` },
      contexto: 'Sin unión por lead/origen: no se puede afirmar cuántos leads de Meta llegaron, ni atribuir el exceso a otras vías. Contactos recibidos no equivalen a cualificados. Cobertura CRM parcial; pocos contactos no acreditan que el cliente no lo use.', medible: 'medias', frescura: fuenteDe(d, 'ghl') }));
  }
  const pr = c.presupuesto_ads;
  if (pr && c.dinero) {
    const valido4=v=>typeof v==='number'&&Number.isFinite(v)&&v>=0;
    t.push(tile({ icono: 'cartera', etiqueta: 'Presupuesto histórico · confirmar vigencia', valor: valido4(pr.pct_consumido)?pct(pr.pct_consumido):null, unidad: valido4(pr.aprobado)?`de ${eur(pr.aprobado)}`:null, estado:'gris',
      comparacion: { texto: `mes transcurrido ${pct(pr.pct_mes)}${pr.proyeccion !== null && pr.proyeccion !== undefined && d.dias_transcurridos >= 5 ? ` · proyección ${eur(pr.proyeccion)}` : ' · sin proyección hasta el día 5'}` },
      contexto: `${pr.origen}. Septiembre real: ${eur(pr.septiembre_real?.invertido)} (${pct(pr.septiembre_real?.pct_consumido)}). Ritmo y proyección no avisan hasta el día 5.`,
      medible: 'medias', medibleDetalle: 'Presupuesto de octubre sin cargar', frescura: fuenteDe(d, 'meta') }));
  }
  if (c.google_ads?.periodo) {
    t.push(tile({ icono: 'globe', etiqueta: 'Google Ads · septiembre', valor: c.google_ads.coste === undefined ? `${num(c.google_ads.clics)} clics` : eur(c.google_ads.coste),
      comparacion: { texto: `${num(c.google_ads.conversiones, 1)} conversiones · ${num(c.google_ads.clics)} clics` }, contexto: `${c.google_ads.cuenta} · muestra manual hasta la clave de Windsor`,
      medible: 'medias', medibleDetalle: 'Muestra manual de septiembre', estado: '', frescura: { fuente: 'Windsor · muestra manual', estado: 'viejo', fecha: '2026-10-02' } }));
  }

  // Ronda U (#11 y #14): arriba la barra de trabajo del trafficker (qué cambio hoy · pedir creatividades) y las pestañas;
  // el resumen (cifras, motivos y «Actuar») es la primera pestaña, ya no empuja nada.
  if (!(ctx.nivel === 'resumen')) cont.append(barraTarjeta(ctx, d, c));
  const tResumen = el => {
    if (esTienda(c)) el.append(avisoParcial(NOTA_TIENDA, { tipo: 'info', titulo: 'No cuenta en los leads de la casa.' }));
    el.append(tiles(t));
    if (c.cuenta_meta?.convertida_a_madrid) {
      el.append(h('p', { class: 'sub', style: { margin: '0', display: 'flex', gap: S[2], alignItems: 'flex-start' } }, icono('info', { clase: 's' }),
        h('span', {}, `Hora de Madrid: Meta cuenta esta cuenta en ${c.cuenta_meta.zona_horaria}; aquí cada día va en hora de Madrid y puede no casar al céntimo con el Administrador de anuncios.`)));
    }
    el.append(h('div', { class: 'pila', style: { marginTop: S[3], gap: S[3], minWidth: '0' } },
      plegablePaid411(`Señales y avisos (${items.length})`,
        panel({ titulo: 'Qué pasa y dónde se rompe', icono: 'alert', sub: 'Motivos de la gravedad y avisos de integración y de datos' }, h('div', { class: 'cuerpo' }, motivos))),
      panel({ titulo: 'Actuar', icono: 'zap', sub: 'Simulación: queda en la cola de acciones con su vista previa. No se toca Meta, GHL ni ClickUp.' }, h('div', { class: 'cuerpo' }, acciones(ctx, c, d)))));
  };

  // ---- pestañas de la tarjeta (diario → semanal) ----
  const p = pestanas({
    clave: 'captacion.tarjeta.v2', etiqueta: 'Detalle de la cuenta',
    pestanas: [
      { id: 'resumen', texto: 'Resumen', icono: 'res', cuenta: (c.motivos || []).length, cuentaEstado: 'rojo' },
      { id: 'ventanas', texto: 'Gasto y leads', icono: 'grafico' },
      { id: 'embudo', texto: 'Embudo', icono: 'cap', cuenta: c.despacho?.estancados_72h || 0, cuentaEstado: 'rojo' },
      { id: 'campanas', texto: 'Campañas', icono: 'megafono', cuenta: (c.campanas || []).length },
      { id: 'anuncios', texto: 'Creatividades', icono: 'spark', cuenta: (c.anuncios?.cansadas || 0) + (c.anuncios?.problemas_total || 0), cuentaEstado: 'rojo' },
      { id: 'metas', texto: 'Metas', icono: 'flag' },
      { id: 'quincenal', texto: 'Quincenal', icono: 'doc' },
      { id: 'historia', texto: 'Historia', icono: 'hist' },
    ],
    pintar: (pid, el) => (pid === 'resumen' ? tResumen(el) : ({ ventanas: tVentanas, embudo: tEmbudo, campanas: tCampanas, anuncios: tAnuncios, metas: tMetas, quincenal: tQuincenal, historia: tHistoria })[pid](el, ctx, d, c)),
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
  const presu = h('input', { type: 'number', min: '0', step: '10', inputmode: 'numeric', placeholder: '€ al día', 'aria-label': 'Nuevo presupuesto diario en euros', style: { width: '112px', minWidth: '0', maxWidth: '100%', boxSizing: 'border-box', minHeight: '32px', padding: `${S[1]} ${S[2]}`, border: '1px solid var(--line)', borderRadius: 'var(--r-s)', background: 'var(--card)' } });
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
      h('span', { class: 'fila', style: { gap: S[2], flexWrap: 'wrap', minWidth: '0', maxWidth: '100%' } }, presu, accionSim('Cambiar presupuesto', '¿Cambiar el presupuesto diario?', 'cambiar_presupuesto', 'meta',
        () => { const v = Number(presu.value); return v > 0 && v < 5000 ? `Cambiaría el presupuesto diario de ${c.nombre} a ${num(v)} € en ${campanas[0]?.campana || 'la campaña activa'}. Espera el permiso de Meta.` : null; })),
      h('span', { class: 'sub' }, 'Pausar y presupuesto: esperan el permiso de Meta')),
    grupo('Tareas',
      crmDe(c) ? botonTarea(ctx, c, d, crmDe(c), `Tarea al CRM (${nombre(d, crmDe(c))})`, c.cuello?.includes('seguimiento') ? 'Revisar el seguimiento del despacho: leads parados y citas sin estado' : 'Revisar el embudo y los recordatorios de citas') : h('span', { class: 'sub', role: 'status' }, 'CRM · asignación pendiente: confirmar especialista antes de preparar una tarea'),
      eq.account ? botonTarea(ctx, c, d, eq.account, `Tarea al account (${nombre(d, eq.account)})`, c.objetivo?.cargado ? 'Hablar con el despacho de la captación' : 'Cargar el objetivo de coste por cita y por lead en la ficha del alta') : null,
      eq.account ? accionSim('Pedir contraste de recuentos al account', '¿Avisar al account?', 'aviso_fuga', 'app',
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
    const pal = 'contador Meta', por = 'coste registrado · unidad pendiente';
    el.append(ventanas(V.map(([k, t]) => ({ titulo: t, valor: `${num(c.leads[k])} ${pal}`, sub: c.dinero ? `${eur(c.gasto?.[k])} · ${c.cpl?.[k] ? `${eur(c.cpl[k])} ${por}` : `sin ${pal}`}` : 'gasto no visible' }))));
  }
  const serie = c.serie || [];
  if (serie.length) {
    const objetivoGrafico=medirCplPaid(c,d,hoyMadrid());
    const movil = cplMovilPaid285(c,serie,ctx.hoy||hoyMadrid());
    el.append(h('div', { style: { display: 'grid', gap: S[5], gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 280px), 1fr))', alignItems: 'start', marginTop: S[4] } },
      graficoSerie({ titulo: 'Contador Meta por día · tipo de evento pendiente', puntos: serie.map(p => ({ x: p.d, y: p.leads_meta })) }),
      c.dinero ? graficoSerie({ titulo: 'Gasto en Meta por día (€)', puntos: serie.map(p => ({ x: p.d, y: p.gasto_meta })), formato: n => `${num(n)} €` }) : null,
      c.dinero ? graficoSerie({ titulo: 'CPL Meta acreditado · 7 días móviles', puntos: movil, umbral:!objetivoGrafico.unidadAcreditada||!objetivoGrafico.objetivoVigente?undefined:{y:objetivoGrafico.objetivo,texto:'Objetivo propio vigente'}, formato: n => `${num(n)} €` })
        : panel({ titulo: 'Gasto', icono: 'candado' }, h('div', { class: 'cuerpo' }, candado('Inversión reservada para tu acceso'))) ));
    el.append(h('p', { class: 'sub', style: { marginTop: S[2] } }, `Del ${fDiaRO(serie[0].d)} al ${fDiaRO(serie.at(-1).d)}. El día en curso no entra: llega incompleto.`));
  }
}

function tEmbudo(el, ctx, d, c) {
  if (!c.ghl?.conectado) {
    el.append(vacio({ icono: 'base', titulo: 'Sin embudo: el CRM no está conectado', texto: 'No hay subcuenta de GoHighLevel emparejada con este cliente. No se evalúa el seguimiento sin esa fuente.', quien: 'Agus (emparejar la subcuenta)' }));
    return;
  }
  const m = medirEmbudoCRM(c.ghl, (d.fuentes || []).find(x => x.id === 'ghl'), ctx.hoy || hoyMadrid());
  const ET = [['nuevo', 'Nuevo', 'inbox'], ['seguimiento', 'Seguimiento', 'phone'], ['cita', 'Cita', 'cal'], ['presupuesto', 'Presupuesto', 'doc'], ['cerrado', 'Cierre registrado en etapa', 'star'], ['descartado', 'Descartado', 'cerrar']];
  const conocidas=m.etapas.filter(x=>x.n!==null);
  const fuente = `${m.fuente} · lectura ${m.fecha || 'sin fecha válida'} · cobertura parcial`;
  const mostrar=n=>n===null?'Sin dato':num(n);
  el.append(h('div', { class: 'dos' },
    panel({ titulo: 'Etapas observadas · oportunidades creadas en 90 días', icono: 'cap', sub: `${mostrar(m.total)} contactos en la copia · ${fuente}` },
      h('div', { class: 'cuerpo pila' },
        conocidas.some(x=>x.n>0) ? embudoBarras(conocidas.map(x=>{const [,t,i]=ET.find(e=>e[0]===x.id);return {etiqueta:t,icono:i,valor:x.n,estado:'gris',nota:`${num(x.n)} contactos observados`};}), { max:Math.max(1,...conocidas.map(x=>x.n)) }) : vacio({ icono: 'inbox', titulo: m.total===null?'Embudo sin medición confirmada':'Cero contactos observados en esta lectura', texto:'No acredita ausencia de oportunidades reales. Contrasta periodo, paginación y fuente antes de decidir.', quien:'CRM', tono:'aviso' }),
        conocidas.length<ET.length ? h('p',{class:'sub'},'Hay etapas sin recuento; no se han rellenado con cero.') : null,
        h('p',{class:'sub'},m.aviso),
        h('p',{class:'sub'},'Etapa de cierre no acredita venta, cobro ni fecha de cierre. Falta historial por oportunidad para medir conversiones de cohortes.'))),
    h('div', { class: 'pila' }, tiles([
      tile({ icono:'clock',etiqueta:'Sin avance observado >72 h',valor:m.parados===null?null:`${num(m.parados)} de ${num(m.cohorte)}`,estado:'gris',
        contexto:`Señal del registro, no prueba falta de contacto o trabajo. ${fuente}`,medible:'medias',frescura:fuenteDe(d,'ghl') }),
      tile({ icono:'cal',etiqueta:'Citas creadas en la lectura · 14 días',valor:m.agendadas===null?null:num(m.agendadas),estado:'gris',
        comparacion:{texto:`${mostrar(m.celebradas)} con asistencia registrada · ${mostrar(m.ausencias)} con ausencia registrada · ${mostrar(m.proximas)} próximas`},
        contexto:m.sinEstado===null?`Estado de las citas sin medir. ${fuente}`:`${num(m.sinEstado)} sin resultado registrado en esta lectura; no acredita que todas estén marcadas. ${fuente}`,medible:'medias',medibleDetalle:'Citas creadas por fecha de alta; asistencia/ausencia por fecha de la cita. No son la misma cohorte.',frescura:fuenteDe(d,'ghl') }),
      tile({ icono:'users',etiqueta:'Asistencia observada · 14 días',valor:m.asistencia===null?null:pct(m.asistencia),estado:'gris',
        comparacion:{texto:m.marcadas===null?'Sin denominador válido':`${num(m.marcadas)} citas con asistencia/ausencia registrada`},
        contexto:`Sólo sobre resultados registrados; no son todos los leads ni una conversión atribuida a Paid. ${fuente}`,medible:'medias',frescura:fuenteDe(d,'ghl') }),
    ]))));
}

function tCampanas(el, ctx, d, c) {
  const cs = c.campanas || [];
  el.append(panel({ titulo: 'Campañas de Meta', icono: 'megafono', sub: 'Gasto y contador Meta; costes registrados con unidad pendiente. Ventanas independientes, sin conversión CRM.' },
    tablaApilable({ filas: cs, columnas: [
      { clave: 'campana', titulo: 'Campaña', principal: true, celda: x => h('span', { style: { display: 'grid' } }, h('b', {}, x.campana), h('small', { class: 'sub' }, x.plataforma === 'meta' ? 'Meta' : x.plataforma)) },
      { clave: 'l7', titulo: 'Leads 7 d', num: true, celda: x => num(x.leads_7d) },
      { clave: 'g7', titulo: 'Gasto 7 d', num: true, celda: x => (x.gasto_7d === undefined ? candado('—') : eur(x.gasto_7d)) },
      { clave: 'c7', titulo: 'Coste registrado 7 d · unidad pendiente', num: true, celda: x => (x.gasto_7d === undefined ? candado('—') : x.cpl_7d ? eur(x.cpl_7d) : (x.gasto_7d ? 'sin leads' : '—')) },
      { clave: 'lm', titulo: 'Leads sept.', num: true, celda: x => num(x.leads_mes_anterior) },
      { clave: 'cm', titulo: 'Coste registrado sept. · unidad pendiente', num: true, celda: x => (x.gasto_mes_anterior === undefined ? candado('—') : x.cpl_mes_anterior ? eur(x.cpl_mes_anterior) : '—') },
      { clave: 'ir', titulo: 'Abrir', ordenable: false, celda: x => (x.enlace || c.cuenta_meta?.enlace ? h('a', { class: 'bt mini', href: x.enlace || c.cuenta_meta.enlace, target: '_blank', rel: 'noopener', title: 'Abre la campaña en el Administrador de anuncios; si Meta no la selecciona, abre la cuenta' }, icono('ext'), 'Abrir en Meta') : '—') },
    ], vacio: { titulo: 'Sin campañas con gasto en las últimas 5 semanas', texto: 'La cuenta no ha gastado en Meta desde finales de agosto.' } })));
  if (c.google_ads?.periodo) el.append(avisoParcial(`Google Ads (${c.google_ads.cuenta}): solo totales de septiembre, sin campañas, hasta la clave de Windsor.`, { tipo: 'info' }));
}

function tAnuncios(el, ctx, d, c) {
  const a = c.anuncios;
  if (!a) { el.append(vacio({ icono: 'spark', titulo: 'Sin anuncios que mirar', texto: c.meta_activa ? 'No se pudieron leer los anuncios de esta cuenta.' : 'La cuenta no tiene pauta activa: no hay anuncios con impresiones en 7 días.' })); return; }
  el.append(tiles([
    tile({ icono: 'baja', etiqueta: 'Cansadas', valor: contadorObservado648(a.cansadas), estado: contadorObservado648(a.cansadas) > 0 ? 'rojo' : 'gris', contexto: 'Dos señales guardadas a la vez; cobertura no exhaustiva, cero no acredita ausencia.', medible: 'medias' }),
    tile({ icono: 'ojo', etiqueta: 'Con una señal', valor: contadorObservado648(a.vigilar), estado: contadorObservado648(a.vigilar) > 0 ? 'ambar' : 'gris', contexto: 'Una señal guardada para revisar; cobertura no exhaustiva, cero no acredita ausencia.', medible: 'medias' }),
    tile({ icono: 'star', etiqueta: 'Ganadoras', valor: a.ganadoras, estado: '', contexto: 'Gasto ≥ 10 veces el objetivo con coste ≤ objetivo', medible: 'hoy' }),
    tile({ icono: 'alert', etiqueta: 'Rechazados o con problemas', valor: contadorObservado648(a.problemas_total), estado: contadorObservado648(a.problemas_total) > 0 ? 'rojo' : 'gris', contexto: 'Rechazos o problemas guardados; cobertura no exhaustiva, cero no acredita ausencia.', medible: 'medias' }),
  ]));
  if (!ctx.soloLectura && ctx.nivel !== 'resumen') el.append(panel({ titulo: 'Pedir nuevas a producción', icono: 'send', sub: 'Con la cansada adjunta y el brief ya escrito.' }, h('div', { class: 'cuerpo' }, formPedido(ctx, d, c))));
  el.append(panel({ titulo: 'Anuncios · 7 días', icono: 'spark', sub: `${a.total_7d} con impresiones; ${a.sin_autor} sin iniciales de autor (desde el próximo lanzamiento)` },
    tablaApilable({ filas: a.anuncios, columnas: [
      { clave: 'nombre', titulo: 'Anuncio', principal: true, celda: x => h('span', { style: { display: 'grid' } }, h('b', {}, x.nombre), h('small', { class: 'sub' }, distingue(x))) },
      { clave: 'e', titulo: 'Estado', celda: x => h('span', { style: { display: 'grid', gap: S[1] } }, chipEstado(x.cansada ? 'rojo' : x.vigilar ? 'ambar' : x.ganadora ? 'verde' : 'gris', x.cansada ? 'Cansada' : x.vigilar ? 'Vigilar' : x.ganadora ? 'Ganadora' : 'Normal'), x.senales?.length ? h('small', { class: 'sub' }, x.senales.join(' + ')) : null) },
      { clave: 'f', titulo: 'Frecuencia', num: true, celda: x => (x.frecuencia_7d ? num(x.frecuencia_7d, 1) : '—') },
      { clave: 'ctr', titulo: '% de clics', num: true, celda: x => (x.ctr_7d === undefined ? '—' : `${num(x.ctr_7d, 2)} %${x.ctr_previo ? ` (antes ${num(x.ctr_previo, 2)})` : ''}`) },
      { clave: 'l', titulo: 'Leads 7 d', num: true, celda: x => num(x.leads_7d ?? null) },
      { clave: 'c', titulo: 'Coste registrado · unidad pendiente', num: true, celda: x => (!c.dinero || x.cpl_7d === undefined && x.cpl_30d === undefined ? candado('—') : x.cpl_7d ? eur(x.cpl_7d) : x.cpl_30d ? `${eur(x.cpl_30d)} (30 d)` : '—') },
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
  const [ini,fin]=Array.isArray(q.periodo)?q.periodo:['sin fecha','sin fecha'];
  const crm=medirEmbudoCRM(c.ghl,(d.fuentes||[]).find(x=>x.id==='ghl'),ctx.hoy||hoyMadrid());
  const observado=n=>n===null?'Sin dato':num(n);
  const lineas = [
    `Quincenal de ${c.nombre} · del ${fDiaRO(ini)} al ${fDiaRO(fin)}`,
    ...textoMetaQuincenal299(q,c.dinero,eur),
    `· Citas creadas observadas: ${observado(crm.agendadas)} · asistencia registrada: ${observado(crm.celebradas)} · ausencia registrada: ${observado(crm.ausencias)} · asistencia sobre resultados: ${crm.asistencia===null?'Sin dato':pct(crm.asistencia)}`,
    `· Citas sin resultado registrado: ${observado(crm.sinEstado)}. No acredita que estén todas marcadas.`,
    `· CRM leído ${crm.fecha||'sin fecha válida'}; cobertura parcial. Citas creadas y asistencia usan fechas distintas: no son una misma cohorte ni conversiones. Etapas/citas no acreditan ventas.`,
    [...(c.motivos || []), ...(c.avisos || [])].length ? `· Señales por contrastar: ${[...new Set([...(c.motivos || []), ...(c.avisos || [])].map(textoMot))].join(' · ')}` : '· Sin alertas en la copia; no acredita ausencia de problemas',
    ...(() => {   // Ronda U: lo que se cambió en la cuenta en el periodo (bitácora del trafficker)
      const l = (d.bitacora?.get(c.cliente_id) || []).filter(a => diaDe(a)>=ini && diaDe(a)<=fin);
      return l.length ? ['· Declaraciones locales (no acreditan ejecución externa):', ...l.slice(0, 8).reverse().map(a => `   ${fDiaRO(diaDe(a))}: ${a.texto}`), d.lecturaPaid516?.aviso||'Lectura local sin fecha acreditada.'] : [d.lecturaPaid516?.estado==='observada'?'· Sin apuntes en la lectura disponible; historial limitado.':`· Bitácora: ${d.lecturaPaid516?.aviso||'pendiente de lectura'}`];
    })(),
  ].filter(Boolean);
  el.append(h('div', { class: 'dos' },
    panel({ titulo: 'Quincenal preparada', icono: 'doc', sub: 'Resultados Meta de referencia y citas observadas por separado; revisar datos, fechas y atribución antes de la reunión.',
      acciones: h('button', { type: 'button', class: 'bt mini', on: { click: () => copiar(lineas.join('\n'), 'Resumen copiado') } }, icono('copy'), 'Copiar') },
      h('div', { class: 'cuerpo' }, h('pre', { style: { whiteSpace: 'pre-wrap', fontFamily: 'var(--sans)', fontSize: 'var(--fs-13)', margin: 0, lineHeight: 1.6 } }, lineas.join('\n')))),
    panel({ titulo: 'Apuntar la quincenal', icono: 'check', sub: 'Indicador «quincenal hecha con informe» (a medias hasta que se apunte aquí)' },
      h('div', { class: 'cuerpo pila' },
        h('p', {}, 'Cuando la reunión esté hecha, apúntala: queda en el rastro con la hora.'),
        botonConfirmar({ texto: 'Quincenal hecha', pregunta: '¿Apuntar la quincenal como hecha?', confirmar: 'Sí, apuntar', soloLectura: ctx.soloLectura,
          alConfirmar: async () => { await ctx.accion({ herramienta: 'app', tipo: 'quincenal_hecha', objeto: c.nombre, cliente_id: c.cliente_id, texto: `Quincenal ${ini} a ${fin}`, vista_previa: lineas.join('\n') }); return 'Apuntada (simulación)'; } })))));
}

function tHistoria(el, ctx, d, c) {
  // Ronda U: la bitácora «qué cambio hoy» (y los pedidos de creatividades) arriba de la historia
  const pedidos = (d.pedidos?.get(c.cliente_id) || []).slice(0, 5);
  el.append(h('div', { class: 'dos', style: { marginBottom: S[4] } },
    panel({ titulo: 'Bitácora · qué se cambió', icono: 'editar', sub: 'Lo que el trafficker apunta cada día. Queda en el rastro.' }, h('div', { class: 'cuerpo' }, listaBitacora(ctx, d, c, 15))),
    panel({ titulo: 'Pedidos locales de creatividades', icono: 'spark' }, h('div', { class: 'cuerpo' }, h('p',{class:'sub',title:d.lecturaPaid516?.leido_en||'Fecha HTTP desconocida'},d.lecturaPaid516?.aviso||'Registro pendiente de lectura; no acredita envío ni creación en ClickUp.'), pedidos.length ? listaConIcono(pedidos.map(p => ({ icono: 'spark', texto: p.texto, extra: `${cuandoBit(ctx, p)} · ${nombre(d, p.quien) || 'alguien'} · registro local` }))) : h('p', { class: 'sub', style: { margin: '0' } }, d.lecturaPaid516?.estado==='observada'?'Sin pedidos en la lectura disponible; historial limitado.':'Pedidos pendientes de lectura.')))));
  const hst = c.historia || {};
  const caja = (titulo, sub, cuerpo, est) => h('div', { style: { border: '1px solid var(--line)', borderRadius: 'var(--r-s)', padding: S[3], display: 'grid', gap: S[1], background: 'var(--card)', minWidth: '0' } },
    h('span', { class: 'sub', style: { fontWeight: '600' } }, titulo), est ? h('span', {}, chipEstado(GRAV[est]?.e || 'gris', GRAV[est]?.t || est)) : null, h('b', { style: NOWRAP }, cuerpo), sub ? h('span', { class: 'sub' }, sub) : null);
  const cols = [];
  if (hst.hace_4_semanas) cols.push(caja(`Hace 4 semanas · ${fDiaRO(hst.hace_4_semanas.periodo[0])} a ${fDiaRO(hst.hace_4_semanas.periodo[1])}`, c.dinero && hst.hace_4_semanas.gasto_meta !== undefined ? `${eur(hst.hace_4_semanas.gasto_meta)} de gasto` : null, `${num(hst.hace_4_semanas.leads_meta)} leads`));
  if (hst.torre_17sep) cols.push(caja('Foto del 17 de septiembre (herramienta anterior)', (c.dinero ? hst.torre_17sep.gasto_motivos : hst.torre_17sep.motivos)?.join(' · ') || 'sin motivos', `${num(hst.torre_17sep.leads_7d)} leads en 7 días`, hst.torre_17sep.severidad));
  if (c.leads) cols.push(caja('7 días anteriores', c.dinero ? `${eur(c.gasto?.['7d_prev'])} · ${c.cpl?.['7d_prev'] ? eur(c.cpl['7d_prev']) + ' · coste registrado, unidad pendiente' : 'sin leads'}` : null, `${num(c.leads['7d_prev'])} leads`));
  if (c.leads) cols.push(caja('Últimos 7 días', c.dinero ? `${eur(c.gasto?.['7d'])} · ${c.cpl?.['7d'] ? eur(c.cpl['7d']) + ' · coste registrado, unidad pendiente' : 'sin leads'}` : null, `${num(c.leads['7d'])} leads`, c.severidad));
  el.append(cols.length ? h('div', { class: 'rejilla' }, cols) : vacio({ icono: 'hist', titulo: 'Sin historia todavía' }));
  el.append(avisoParcial('A 90 días y «qué se cambió» llegan con las fotos diarias de la app (empezaron el 2-oct) y con el rastro de acciones. Mientras, la foto del 17 de septiembre de la herramienta anterior hace de punto de comparación.', { tipo: 'info', titulo: 'Historia.' }));
}

// ================================================================== Ronda U · U3 (3-oct, cambio #11 del 50) · trafficker
// 1) Bitácora diaria «qué cambio hoy» por cuenta: acción interna bitacora_cuenta (herramienta app, con rastro). Se ve en la
//    lista de cuentas (columna «Hoy»), arriba de la tarjeta, en Historia y en la quincenal. La ficha del cliente la lee con
//    el mismo dato (acciones del módulo captacion) desde bitacoraCuenta() exportada abajo.
// 2) «Pedir creatividades»: brief a producción. Acción clickup/tarea con vista_previa.pedido_creatividad → sincronia.py la
//    guarda como «crear tarea en la lista del cliente» (hoy simulado) y avisos.py la publica en #avisos-redes (producción).
//    Es interno mientras la sincronía esté apagada: sin «¿Seguro?», con «Deshacer» 8 s.
const CAMBIOS_RAPIDOS = ['Bajo el presupuesto', 'Subo el presupuesto', 'Pauso el anuncio cansado', 'Cambio el público', 'Pruebo una creatividad nueva', 'Sin cambios: dejo que aprenda'];
const FORMATOS = [{ valor: 'estaticos', texto: 'Estáticos 4:5 y 9:16' }, { valor: 'video', texto: 'Vídeo corto' }, { valor: 'carrusel', texto: 'Carrusel' }];

/** Lee las acciones del módulo (bitácora y pedidos), una vez por pantalla. */
async function cargarBitacora(ctx, d) {
  await cargarLecturaPaid516(ctx,d);
}
/** La hora de la cola de acciones viene en UTC («2026-10-03 03:36:12»): día y hora en Madrid. */
const madridDe = t => {
  const s = String(t || '');
  const d = new Date(s.replace(' ', 'T') + (/[zZ]$|[+-]\d\d:?\d\d$/.test(s) ? '' : 'Z'));
  if (!s || Number.isNaN(+d)) return { dia: s.slice(0, 10), hora: s.slice(11, 16) };
  const p = Object.fromEntries(new Intl.DateTimeFormat('en-CA', { timeZone: 'Europe/Madrid', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hourCycle: 'h23' })
    .formatToParts(d).map(x => [x.type, x.value]));
  return { dia: `${p.year}-${p.month}-${p.day}`, hora: `${p.hour}:${p.minute}` };
};
const diaDe = a => (a?._recibo516 ? '' : a?._local ? String(a.creada || '').slice(0, 10) : madridDe(a?.creada).dia);
const horaDe = a => (a?._local ? String(a.creada || '').slice(11, 16) : madridDe(a?.creada).hora);
/** «hoy 10:12», «ayer 18:03», «2-oct». */
function cuandoBit(ctx, a) {
  if(a?._recibo516)return 'recibo local confirmado · fecha por consultar';
  const dia = diaDe(a);
  if (ctx.fechas?.esHoy?.(dia)) return `hoy ${horaDe(a)}`;
  if (ctx.fechas?.esAyer?.(dia)) return `ayer ${horaDe(a)}`;
  return fDiaRO(dia);
}
const hoyBit = (ctx, d, cid) => (d.bitacora?.get(cid) || []).find(a => !a._recibo516 && diaDe(a) && ctx.fechas?.esHoy?.(diaDe(a)));

/**516: una declaración sólo se pinta guardada tras el recibo local194. */
async function apuntarCambio(ctx,d,c,texto,alHecho) {
  const receipt=await guardarPaid516(ctx,{herramienta:'app',tipo:'bitacora_cuenta',objeto:`${c.nombre} · qué cambió hoy`,cliente_id:c.cliente_id,texto,
    vista_previa:`Bitácora de ${c.nombre} (${ctx.nombre(ctx.persona.id)}), día ${ctx.hoy||hoyMadrid()}: «${texto}». Declaración local; no acredita ejecución externa.`});
  if(!ambitoPaid516(ctx,c.cliente_id,true))throw Error('El acceso cambió; revisa Envíos antes de reintentar.');
  const a={id:receipt.accion_id,tipo:'bitacora_cuenta',cliente_id:c.cliente_id,texto,quien:ctx.real.id,creada:null,_recibo516:true,estado:'simulada'};
  const l=d.bitacora.get(c.cliente_id)||[];if(!l.some(x=>x.id===a.id))l.unshift(a);d.bitacora.set(c.cliente_id,l);alHecho?.();return receipt;
}

/** Editor «qué cambio hoy»: cambios rápidos (un clic los escribe) + texto + «Apuntar». */
function editorBitacora(ctx,d,c,{alHecho,compacto}={}) {
  const scope=ambitoPaid516(ctx,c.cliente_id,true),caja=h('div',{class:'pila',style:{gap:S[2],minWidth:'0'}});
  const vivo=()=>ctx.vigente?.()!==false&&scope!==null&&ambitoPaid516(ctx,c.cliente_id,true)?.firma===scope.firma;
  const status=h('span',{class:'sub',role:'status'},scope?'':'Registro local no disponible para esta sesión.');
  const campo=h('input',{type:'text',maxlength:'300',placeholder:'Qué cambias hoy en esta cuenta y por qué','aria-label':`Qué cambio hoy en ${c.nombre}`,style:{flex:'1 1 260px',minWidth:'0',minHeight:'44px'}});
  let enviando=false;
  const apuntar=h('button',{type:'button',class:'bt pri',disabled:!scope,on:{click:async()=>{
    if(enviando)return;if(!vivo()){caja.replaceChildren();return;}
    const t=campo.value.trim();if(t.length<3){campo.focus?.();campo.setAttribute('aria-invalid','true');return;}
    campo.removeAttribute('aria-invalid');enviando=true;apuntar.disabled=true;status.textContent='Guardando intención local…';
    try{await apuntarCambio(ctx,d,c,t,alHecho);if(!vivo()){caja.replaceChildren();return;}if(campo.value.trim()===t)campo.value='';status.textContent='Intención local guardada; no confirma cambios en Meta.';}
    catch(e){if(!vivo()){caja.replaceChildren();return;}status.textContent=e?.message||'Resultado pendiente de comprobar. Reintenta el mismo contenido.';}
    finally{enviando=false;apuntar.disabled=!vivo();}
  }}},icono('editar'),'Apuntar');
  campo.addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();apuntar.click();}});
  const rapidos=h('div',{class:'fila',style:{flexWrap:'wrap',gap:S[1]}},CAMBIOS_RAPIDOS.map(t=>h('button',{type:'button',class:'bt mini',disabled:!scope,on:{click:()=>{if(!vivo()){caja.replaceChildren();return;}campo.value=t;campo.focus?.();}}},t)));
  caja.append(h('div',{class:'fila',style:{gap:S[2],flexWrap:'wrap'}},campo,apuntar),compacto?null:rapidos,status,h('a',{href:'#/envios',on:{click:e=>{if(!vivo()){e.preventDefault();caja.replaceChildren();}}}},'Consultar Envíos'));
  return caja;
}

/** Últimos apuntes de la bitácora (lista con icono). */
function listaBitacora(ctx,d,c,n=3) {
  const l=(d.bitacora?.get(c.cliente_id)||[]).slice(0,n),estado=d.lecturaPaid516;
  const aviso=estado&&estado.estado!=='observada'?h('p',{class:'sub',role:'status',title:estado.leido_en||'Fecha HTTP desconocida'},estado.aviso):null;
  const rows=l.length?listaConIcono(l.map(a=>({icono:'editar',texto:a.texto,extra:`${cuandoBit(ctx,a)} · ${nombre(d,a.quien)||'Autor por confirmar'} · registro local, no ejecución externa`}))):h('p',{class:'sub',style:{margin:'0'}},estado?.estado==='observada'?'Sin apuntes en la lectura disponible; historial limitado.':'Registro local pendiente de lectura.');
  return h('div',{class:'pila',style:{gap:S[1]}},aviso,rows);
}

/** Formulario «Pedir creatividades a producción», con el brief ya escrito con lo que dice la cuenta. */
function formPedido(ctx, d, c, { anuncio } = {}) {
  const cansadas = (c.anuncios?.anuncios || []).filter(a => a.cansada || a.vigilar);
  const base = anuncio || cansadas[0] || null;
  const para = (() => { let f = ctx.hoy || hoyMadrid(); let n = 0; while (n < 3) { f = sumarDias(f, 1); const dw = new Date(f + 'T12:00:00').getDay(); if (dw !== 0 && dw !== 6) n++; } return f; })();
  const motivos = (c.motivos || []).map(textoMot).slice(0, 2).join(' · ');
  const brief = [
    base ? `Sustituir «${base.nombre}» (${base.cansada ? 'cansada' : 'a vigilar'}${base.frecuencia_7d ? `, frecuencia ${num(base.frecuencia_7d, 1)}` : ''}${base.ctr_7d !== undefined ? `, ${num(base.ctr_7d, 2)} % de clics` : ''}).` : 'Creatividades nuevas para refrescar la cuenta.',
    motivos ? `Qué pasa: ${motivos}.` : null,
    c.nicho ? `Nicho: ${c.nicho}.` : null,
    'Mantener la marca del cliente (logo, colores y tono en la tarea de producción).',
  ].filter(Boolean).join(' ');
  let formatos = ['estaticos'];
  const chips = chipsFiltro({ etiqueta: 'Qué pides', multiple: true, valor: formatos, opciones: FORMATOS, alCambiar: v => { formatos = v; } });
  const texto = h('textarea', { rows: 3, maxlength: '900', 'aria-label': 'Brief para producción', style: { width: '100%', padding: `${S[2]} ${S[3]}`, border: '1px solid var(--line)', borderRadius: 'var(--r-s)', background: 'var(--card)', font: 'var(--t-cuerpo)' } }, brief);
  const fecha = h('input', { type: 'date', value: para, min: ctx.hoy || hoyMadrid(), 'aria-label': 'Para cuándo', style: { minHeight: 'var(--s-10)', padding: `${S[1]} ${S[2]}`, border: '1px solid var(--line)', borderRadius: 'var(--r-s)', background: 'var(--card)' } });
  const yaPedidos = (d.pedidos?.get(c.cliente_id) || []).slice(0, 2);
  const scope=ambitoPaid516(ctx,c.cliente_id,true),caja=h('div',{class:'pila',style:{gap:S[2]}});
  const vivo=()=>ctx.vigente?.()!==false&&scope!==null&&ambitoPaid516(ctx,c.cliente_id,true)?.firma===scope.firma;
  const status=h('p',{class:'sub',role:'status'},scope?'':'Registro local no disponible para esta sesión.');let enviando=false;
  const enviar=h('button',{type:'button',class:'bt pri',disabled:!scope,on:{click:async()=>{
    if(enviando)return;if(!vivo()){caja.replaceChildren();return;}
    if(!formatos.length||texto.value.trim().length<10){status.textContent='Elige formatos y escribe el brief.';return;}
    if(!/^\d{4}-\d{2}-\d{2}$/.test(fecha.value)||!Number.isFinite(Date.parse(fecha.value+'T00:00:00Z'))||new Date(fecha.value+'T00:00:00Z').toISOString().slice(0,10)!==fecha.value){status.textContent='Elige una fecha válida.';return;}
    const contenido=texto.value.trim(),txt=`${FORMATOS.filter(f=>formatos.includes(f.valor)).map(f=>f.texto).join(' + ')} para el ${fDiaRO(fecha.value)}. ${contenido}`;
    const payload={herramienta:'clickup',tipo:'tarea',objeto:`Pedido de creatividades · ${c.nombre}`.slice(0,200),cliente_id:c.cliente_id,texto:txt,
      vista_previa:{pedido_creatividad:true,tarea:`Creatividades nuevas · ${c.nombre}`,para:fecha.value,formatos:[...formatos],anuncio:base?.nombre||null,brief:contenido.slice(0,900),de:ctx.persona.id}};
    enviando=true;enviar.disabled=true;status.textContent='Guardando intención local…';
    try{const receipt=await guardarPaid516(ctx,payload);if(!vivo()){caja.replaceChildren();return;}
      const l=d.pedidos.get(c.cliente_id)||[];if(!l.some(x=>x.id===receipt.accion_id))l.unshift({id:receipt.accion_id,texto:txt,creada:null,_recibo516:true,quien:ctx.real.id,estado:'simulada'});d.pedidos.set(c.cliente_id,l);
      status.textContent='Intención local guardada; creación en ClickUp y comunicación a producción sin confirmar.';
    }catch(e){if(!vivo()){caja.replaceChildren();return;}status.textContent=e?.message||'Resultado pendiente de comprobar. Reintenta el mismo contenido.';}
    finally{enviando=false;enviar.disabled=!vivo();}
  }}},icono('send'),'Guardar pedido local');
  caja.append(chips,texto,h('div',{class:'fila',style:{gap:S[2]}},h('label',{class:'fila sub',style:{gap:S[2]}},'Para cuándo',fecha),enviar),status,
    h('p',{class:'sub',style:{margin:'0'}},'Guarda una intención local con este brief. No acredita envío a un canal ni creación de tarea en ClickUp.'),
    h('a',{href:'#/envios',on:{click:e=>{if(!vivo()){e.preventDefault();caja.replaceChildren();}}}},'Consultar Envíos'),
    d.lecturaPaid516&&d.lecturaPaid516.estado!=='observada'?h('p',{class:'sub',role:'status',title:d.lecturaPaid516.leido_en||'Fecha HTTP desconocida'},d.lecturaPaid516.aviso):null,
    yaPedidos.length?h('p',{class:'sub',style:{margin:'0'}},`Registros locales leídos: ${yaPedidos.map(p=>`${cuandoBit(ctx,p)} (${nombre(d,p.quien)||'Autor por confirmar'})`).join(' · ')}`):null);
  return caja;

}

/** Barra de la tarjeta (molde: barraAcciones arriba y pegada): «Qué cambio hoy» y «Pedir creatividades». */
function barraTarjeta(ctx, d, c) {
  const zonaPedido = h('div', { hidden: true, style: { marginTop: S[3] } });
  const zonaLista = h('div', { style: { marginTop: S[2] } });
  const pintarLista = () => zonaLista.replaceChildren(listaBitacora(ctx, d, c, 2));
  const botonPedir = h('button', { type: 'button', class: 'bt', 'aria-expanded': 'false', 'aria-disabled': ctx.soloLectura ? 'true' : null, on: { click: () => {
    if (ctx.soloLectura) return;
    const abrir = zonaPedido.hidden; zonaPedido.hidden = !abrir; botonPedir.setAttribute('aria-expanded', String(abrir));
    if (abrir && !zonaPedido.childNodes.length) zonaPedido.append(formPedido(ctx, d, c));
  } } }, icono('spark'), 'Pedir creatividades');
  pintarLista();
  const hoyA = hoyBit(ctx, d, c.cliente_id);
  const barra = barraAcciones({ titulo: hoyA ? `Hoy en ${c.nombre}: ${hoyA.texto}` : `Qué cambio hoy en ${c.nombre}`, sub: hoyA ? `Apuntado ${cuandoBit(ctx, hoyA)}` : 'La guía pide apuntarlo cada mañana: se ve en la ficha y en la quincenal.',
    acciones: [c.cuenta_meta?.enlace ? h('a', { class: 'bt', href: c.cuenta_meta.enlace, target: '_blank', rel: 'noopener' }, icono('ext'), 'Abrir en Meta') : null, botonPedir] });
  barra.querySelector('.fila')?.after(h('div', { style: { marginTop: S[3] } }, editorBitacora(ctx, d, c, { alHecho: () => { pintarLista(); const t = barra.querySelector('b'); const n = hoyBit(ctx, d, c.cliente_id); if (t && n) t.textContent = `Hoy en ${c.nombre}: ${n.texto}`; } }), zonaLista, zonaPedido));
  barra.style.position = 'static';   // el editor es alto: pegada arriba taparía la tarjeta; va la primera bajo la cabecera
  barra.id = 'cap-barra';
  return barra;
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
    if (!contenedor.isConnected || (ctx.vigente && !ctx.vigente())) return;
    espera.remove();
    if (d.error) {
      contenedor.append(vacio({ icono: 'alert', titulo: 'No se pudieron cargar los datos de captación', texto: d.error, quien: 'Agus (técnico)', borde: true, tono: 'aviso' }));
      return;
    }
    const avisoPaid401=h('details', {class:'que-es'}, h('summary',{style:{minHeight:'36px',display:'flex',alignItems:'center'}},'Fuentes y señales de Paid'), avisoParcial('Esta vista conserva reglas anteriores. Sus alertas requieren contraste: no demuestran pérdida de leads, falta de seguimiento ni cumplimiento de un objetivo acordado. Consulta Prioridades por cliente para la metodología vigente.', { tipo: 'info' }));
    PARAMS = d.parametros || null;
    await cargarBitacora(ctx, d);
    if (!contenedor.isConnected || (ctx.vigente && !ctx.vigente())) return;
    d.clientes=d.clientes.map(c=>normalizarPaid(c,d,ctx.hoy||hoyMadrid()));
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
      contenedor.append(avisoPaid401);
      for (const hijo of contenedor.children) hijo.style.minWidth = '0';
      return;
    }
    if (id) pintarTarjeta(contenedor, ctx, d, id);
    else await pintarLista(contenedor, ctx, d);
    if(id&&d.clientes.some(c=>c.cliente_id===id)){
      const firmaMeta=ambitoMeta386(ctx,id);
      if(firmaMeta){const diarioMeta=await renderMetaDiaria386(h,ctx,id);
        if(contenedor.isConnected&&(!ctx.vigente||ctx.vigente())&&ambitoMeta386(ctx,id)===firmaMeta&&diarioMeta.querySelector('table'))contenedor.append(diarioMeta);
      }
    }
    contenedor.append(avisoPaid401);
    // El contenedor es una rejilla: sin esto, un hijo ancho (tabla, pestañas) estira la página en móvil.
    for (const hijo of contenedor.children) hijo.style.minWidth = '0';
  },
};

import { secundariosCRM317, textoConteo317, referenciaAlta317 } from './_crm_secundario_317.js';
import { prepararControlEquipo313 } from './_control_equipo_313.js';
import { separarCadencias, textoCadencia, estadoCadencia, ambitoCadencia307 } from './_cadencia_metodo.js';
// modulos/mi_dia_bloques.js · M1 «Mi día»: los bloques (uno por id de data/mi_dia/config.json → bloques) y
// «el número que manda» de cada puesto. Es un ORQUESTADOR: nada se recalcula; cada bloque lee lo que su módulo
// ya sirve recortado por servir.py (ctx.datosModulo) y lo resume en una cifra, un motivo y 5 filas como mucho.
//
// Contrato de un bloque:  BLOQUES[id] = { usa: ['carpeta/fichero', …], hacer(ctx, D, b) → resultado }
//   resultado = { valor, unidad, estado, comparacion, motivo, filas: [{ texto, extra, estado, icono, href }],
//                 extra: Node, vacio: { titulo, texto, quien, tono }, medible, medibleDetalle, frescura,
//                 primero: [{ peso, icono, motivo, detalle, ruta, clave, cliente_id }] }
//   D.dato(nombre) → los datos (o lanza «falta», que el orquestador pinta como «llega con <módulo>»).
//   D.opcional(nombre) → los datos o null (para un dato de apoyo que no es imprescindible).
// Sin sueldos, sin datos de leads (los nombres vienen enmascarados de origen) y sin dinero que el servidor no mande.

import { h, fmt, semaforo, icono, barraProgreso, embudoBarras, tarjetaCliente, chipEstado, colorCifra, fechas as FECHAS, hoyMadrid } from '../componentes.js';
import { REGLAS } from '../permisos.js';
import { alDia, revisionesDelAccount } from './produccion_comun.js';
import { clientesDia314, metaDia314, totalMetaDia314, resultadosFilaDia314, crmDia314, fuenteCrmDia314 } from './_resultados_dia_314.js';
import { normalizarPaid } from './_paid_mediciones.js';
import { instanteRO, diaRO, horaRO } from '../_fechas_ro.js';   // L-18: los textos sin zona son Madrid, no la zona del navegador

// ------------------------------------------------------------------ utilidades
// V2 · «hoy» = el día de la agencia en Madrid (helper común de fechas, V2-E), nunca el reloj del Mac (Tomás en Bali)
const hoyISO = () => hoyMadrid();
export const MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'];
const mesActual = () => hoyISO().slice(0, 7);
/** L-19: el nombre del mes en curso sale del «hoy» de Madrid, no del reloj del navegador. */
const nombreMesActual = () => MESES[Number(mesActual().slice(5)) - 1];
/** Día de la semana (0 = domingo) y día del mes de HOY en Madrid (no del reloj del Mac). */
const hoyDia = () => new Date(`${hoyISO()}T12:00:00`);
const mesAnterior = () => { const [a, m] = hoyISO().split('-').map(Number); return m === 1 ? `${a - 1}-12` : `${a}-${String(m - 1).padStart(2, '0')}`; };
/** V2 · texto llano para lo que llega de otros generadores (alertas, incidencias, avisos): horas grandes en días («478 h» →
 *  «20 días», con la antigüedad común), sin números de ticket sueltos («(RO-6625)»: el botón ya abre ese correo), sin el
 *  paso técnico entre paréntesis («(… --en-vivo seranking)», «(403)», «FIN §6») y con espacio alrededor de «». */
export function textoLlano(t) {
  if (typeof t !== 'string' || !t) return t;
  return t
    .replace(/\b(\d{2,})\s?h\b(?!\s+laborables)/g, (m, n) => (Number(n) > 48 ? FECHAS.antiguedad(Number(n)) : m))
    .replace(/\s*\(RO-\d{2,}\)/g, '').replace(/\(RO-\d{2,},\s*/g, '(').replace(/\bRO-\d{2,}\s*·\s*/g, '')
    .replace(/\s*\(\d{3}\)/g, '')
    .replace(/\s*\([^()]*(?:--[a-z]|\.sh\b|\.py\b|security |bash |§)[^()]*\)/g, '')
    .replace(/([\p{L}\d])«/gu, '$1 «').replace(/»([\p{L}\d])/gu, '» $1')
    .replace(/\s+([.,;:])/g, '$1').replace(/\s{2,}/g, ' ').trim();
}
// L-18: instante en Madrid si el texto no trae zona (antes, en la zona del navegador). Un día sin hora no depende de la zona.
const fecha = s => { if (!s) return null; const d = instanteRO(s); if (d) return d; if (/\d{2}:\d{2}/.test(String(s))) return null; const l = new Date(String(s).replace(' ', 'T')); return Number.isNaN(+l) ? null : l; };
export const edadH = s => { const d = fecha(s); return d ? Math.max(0, (Date.now() - d) / 36e5) : null; };
// Sin `diaRO` (las pruebas `.cjs` cargan este trozo sin imports) queda el día del propio texto.
export const diaCorto = s => { const dia = s ? (typeof diaRO === 'function' ? diaRO(String(s)) : String(s).slice(0, 10)) : null; return dia ? `${Number(dia.slice(8))}-${MESES[Number(dia.slice(5, 7)) - 1].slice(0, 3)}` : (s || '—'); };
const horaCorta = s => { const d = fecha(s); return d ? horaRO(d) : ''; };
const cuandoTxt = s => { const d = fecha(s); if (!d) return s || '—'; const hoy = hoyISO(); const iso = diaRO(String(s)) || String(s).slice(0, 10); return iso === hoy ? `hoy, ${horaCorta(s)}` : `${diaCorto(iso)}, ${horaCorta(s)}`; };   // «2-oct, 17:34» (44 §2.3)
const n0 = v => Number(v) || 0;
/** Euros con el formateador común (punto de miles siempre y «−»): 3.860 € · 3.859,87 €. */
const eurG = n => fmt.eur(n);
const eurC = n => fmt.eur(n, 2);
const suma = (l, f) => l.reduce((a, x) => a + n0(f(x)), 0);
const pct = (a, b) => (b ? Math.round((a / b) * 100) : null);
const plural = (n, s, p) => `${fmt.num(n)} ${n === 1 ? s : (p || s + 's')}`;
const generado = d => d?.generado || d?._meta?.generado || d?.meta?.generado || null;
/** Sello de frescura desde el «generado» de un fichero. Ámbar si pasa de 24 h. */
export function fresco(fuente, d) {
  const g = typeof d === 'string' ? d : generado(d);
  // un día sin hora («2026-10-02») no da horas: «hoy» / «ayer» (R12: antes salía «hace 19 h»)
  if (typeof g === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(g)) return { fuente, fecha: g, estado: g === hoyISO() ? 'ok' : 'viejo' };
  const e = edadH(g);
  return e === null ? { fuente, estado: 'sin datos' } : { fuente, edad_h: Math.round(e * 10) / 10, estado: e > 24 ? 'viejo' : 'ok' };
}
const yo = ctx => ctx.persona.id;
const miSetter = ctx => (ctx.persona.id.startsWith('setter_') ? ctx.persona.id.replace('setter_', '') : null);
const alias = (ctx, id) => (ctx.datos.personas || []).find(p => p.id === id)?.alias || id || 'sin asignar';
/** Enlace a un cliente: su ficha (en la pestaña pedida) si el puesto la ve; si no, su detalle de «En rojo». */
export const hrefCliente = (ctx, id, pestana) => (!id ? null : ctx.veModulo('ficha') && ctx.clientesVisibles.some(c => c.id === id) ? `#/ficha/${id}${pestana ? '/' + pestana : ''}` : `#/en-rojo/${id}`);
/** Rutas profundas: cada «Ir» abre la cosa concreta, no la portada del módulo (auditoría F-03). */
const ir = (ctx, modulo, id, alt) => (id && ctx.veModulo(modulo) ? `#/${modulo}/${String(id).split('/').map(encodeURIComponent).join('/')}` : alt || (ctx.veModulo(modulo) ? `#/${modulo}` : null));
/** A1 · la ficha de ESA persona (#/personas/<id>), no la pantalla entera. */
const hrefPersona = (ctx, id, { plan = false } = {}) => (id && ctx.veModulo('personas') ? `#/personas/${encodeURIComponent(id)}${plan ? '?plan=1' : ''}` : '#/personas');
// Ronda U (50 #5): UN SOLO DESTINO POR OBJETO. El mismo objeto lleva siempre a la misma ruta exacta, la de su alerta en
// «Lo mío»: una decisión → #/decisiones/reloj/<id> (la abre sola, con su barra de acciones); un firmado sin alta o un cobro →
// #/finanzas/cobros/<cliente o factura> (la fila con «Alta hecha» / «Reclamado»); un alta o su taller → #/clientes-nuevos/<id>;
// la rentabilidad de un cliente → #/dinero-cliente/<id>. La ficha queda para lo que es del cliente entero.
const hrefDecision = (ctx, id) => ir(ctx, 'decisiones', id ? `reloj/${id}` : 'reloj');
const hrefCobro = (ctx, clave, alt) => ir(ctx, 'finanzas', clave ? `cobros/${clave}` : null, alt);
const hrefCap = (ctx, id) => ir(ctx, 'captacion', id, hrefCliente(ctx, id, 'resultados'));
const sinAlmohadilla = href => (href && href.startsWith('#/') ? href.slice(2) : null);
/** Tiempo esperando como en la Bandeja: horas contadas de lunes a viernes. */
/** Espera de un correo con la regla de la Bandeja: días laborables (lunes a viernes) o, si es de hoy, horas laborables. */
const esperaTxt = x => (n0(x.dias_laborables) >= 1 ? `${plural(n0(x.dias_laborables), 'día laborable', 'días laborables')} esperando` : `${relojTxt(x.horas)} laborables esperando`);
const relojTxt = horas => { if (horas === null || horas === undefined) return '—'; const hr = Math.round(horas); return hr < 24 ? `${hr} h` : `${Math.floor(hr / 24)} d ${hr % 24} h`; };
const nombre = (ctx, id) => (ctx.nombre ? ctx.nombre(id) : alias(ctx, id));
const verdad = (ctx, id) => (ctx.verdad ? ctx.verdad(id) : null);
const top = (l, n = 5) => l.slice(0, n);
const peor = { rojo: 0, critico: 0, ambar: 1, atencion: 1, gris: 2, verde: 3, ok: 3 };
const ordenEstado = (a, b) => (peor[a.estado] ?? 2) - (peor[b.estado] ?? 2);
const escala = (rojo, ambar) => (rojo ? 'rojo' : ambar ? 'ambar' : 'verde');
/** ¿Es este cliente «mío» para el alcance pedido? (cartera de la silla, o el equipo que trae el propio dato). */
function esMio(ctx, cid, equipo = []) {
  return (cid && ctx.carteraIds.has(cid)) || equipo.filter(Boolean).includes(yo(ctx));
}
const alcance = (b, def = 'todo') => b.alcance || def;

// ------------------------------------------------------------------ R12 · una sola verdad (auditoría final)
/** Cartera de una silla por ASIGNACIONES (ctx.carteraPorSilla, la misma que Personas y Dinero por cliente). null sin dato. */
const silla = (ctx, s) => {
  const cps = ctx.carteraPorSilla; const x = cps?.[s];
  if (x && typeof x.has === 'function') return x;
  return cps && (ctx.servidor || Object.keys(cps).length) ? new Set() : null;   // sin filas vigentes en esa silla = cartera vacía
};
/** Salud y gravedad de la verdad única (la misma que la ficha y En rojo), nunca la «salud» vieja de la sesión. */
export const saludV = (ctx, id) => { const s = verdad(ctx, id)?.salud; return typeof s === 'number' ? s : null; };
const GRAV_TXT = { critico: 'crítico', atencion: 'a vigilar', bien: 'bien' };   // glosario 44 §2.1: Crítico / Vigilar / Bien
const GRAV_EST = { critico: 'rojo', atencion: 'ambar', bien: 'verde' };
export const GRAV_CLI = { critico: 'cliente crítico', atencion: 'cliente a vigilar', bien: 'cliente bien' };
/** Texto sin el hueco «[importe]» que deja el recorte del servidor: la frase sin la cifra (la cifra va aparte si se puede ver). */
export const sinImporte = t => (typeof t !== 'string' || !t.includes('[importe]') ? t
  : t.replace(/\s*(?:de|por|con|en|a)?\s*\[importe\](?:\s*\/\s*\w+)?/g, '').replace(/\s+([,.;)])/g, '$1').replace(/\(\s*\)/g, '').replace(/\s{2,}/g, ' ').trim());
/** Estado de arranque de un alta, de la verdad única (verdad.encendido), no de la ficha de Clientes nuevos. */
export function arranqueV(ctx, a) {
  const v = verdad(ctx, a.cliente_id); const e = v?.encendido;
  if (!e?.estado) return { estado: a.plazo?.estado || 'gris', texto: a.plazo?.texto || '', sinEncender: a.plazo?.estado === 'rojo' };
  const dia = v.dia_alta ?? a.dia;
  return ({
    sin_encender_fuera_de_plazo: { estado: 'rojo', texto: `sin encender pasado el día 12 (va por el día ${dia})`, sinEncender: true },
    tarde: { estado: 'ambar', texto: `encendida tarde, el día ${e.dia}`, sinEncender: false },
    en_limite: { estado: 'ambar', texto: `encendida en el límite, el día ${e.dia}`, sinEncender: false },
    en_plazo: { estado: 'verde', texto: `encendida en plazo, el día ${e.dia}`, sinEncender: false },
    pendiente_en_plazo: { estado: 'gris', texto: `por encender, en plazo (va por el día ${dia})`, sinEncender: false },
  })[e.estado] || { estado: 'gris', texto: e.estado, sinEncender: false };
}
/** Nombre de un cliente por su id (verdad común o sesión); nunca «—». */
const nomCli = (ctx, id) => (id ? ctx.clientes.find(c => c.id === id)?.nombre || verdad(ctx, id)?.nombre || null : null);

// ============================================================ BLOQUES
export const BLOQUES = {};
const def = (id, usa, hacer) => { BLOQUES[id] = { usa, hacer }; };

// ------------------------------------------------------------- Dirección
def('cambios_ayer', ['mi_dia/cambios'], (ctx, D) => {
  const c = D.dato('mi_dia/cambios');
  const l = c.lineas || [];
  return {
    valor: l.length, unidad: l.length === 1 ? 'cambio' : 'cambios',
    estado: escala(l.some(x => x.estado === 'rojo'), l.some(x => x.estado === 'ambar')),
    motivo: c._meta?.comparado_con ? `Frente a la foto del ${diaCorto(c._meta.comparado_con)}, sin IA.` : 'Hoy es la primera foto diaria: se resume lo que cada módulo trae de ayer. Desde mañana, cliente a cliente.',
    filas: l.map(x => ({ texto: x.texto, extra: x.fuente, estado: x.estado, icono: x.icono, href: x.ruta ? `#/${x.ruta}` : null })),
    plegar: true, frescura: fresco('Fotos diarias + módulos', c._meta?.generado), medible: 'hoy',
  };
});

def('decisiones_48h', ['decisiones/reloj'], (ctx, D, b) => {
  const r = D.dato('decisiones/reloj');
  const puestos = ctx.persona.puestos;
  const tipo = b.tipo || (puestos.includes('direccion') ? 'para_tomas' : puestos.includes('proyectos') ? 'para_coti' : null);
  const l = (r.decisiones || []).filter(x => !x.respuesta && (tipo ? x.tipo === tipo : x.quien === yo(ctx)))
    .sort((a, b2) => n0(b2.horas) - n0(a.horas));
  const fuera = l.filter(x => x.estado !== 'en plazo');
  return {
    valor: l.length, unidad: l.length === 1 ? 'esperando' : 'esperando', estado: l.length ? (fuera.length ? 'rojo' : 'ambar') : 'verde',
    motivo: l.length ? `Reloj de ${l[0].reloj_h || 48} h: ${fuera.length ? `${fuera.length} fuera de plazo` : 'todas en plazo'}. Cada una trae problema, recomendación y fecha.` : 'Nada esperando tu decisión.',
    filas: l.map(x => ({ texto: x.titulo, extra: `vence ${cuandoTxt(x.vence)} · subida por ${nombre(ctx, x.quien)}`, estado: x.estado === 'en plazo' ? 'ambar' : 'rojo', icono: 'flag', href: hrefDecision(ctx, x.id) })),
    vacio: { titulo: 'Sin decisiones pendientes', texto: 'Cuando Mili, Coti, Cecilia o Sofía suban una, aparece aquí con su reloj.', tono: 'celebrar' },
    frescura: fresco('Decisiones', r), medible: 'hoy',
    primero: l.map(x => ({ peso: x.estado === 'en plazo' ? 2.5 : 4, icono: 'flag', motivo: `Decidir: ${x.titulo}`, detalle: `Recomendación: ${x.recomendacion || '—'} · vence ${cuandoTxt(x.vence)}`, ruta: sinAlmohadilla(hrefDecision(ctx, x.id)) || 'decisiones/reloj', clave: `dec:${x.id}` })),
  };
});

function resultadosClientes(ctx,D,b,defAlcance){
 const cap=D.dato('captacion/captacion'),hoy=ctx.hoy||hoyISO(),al=alcance(b,defAlcance);
 const cl=clientesDia314(ctx,cap.clientes).filter(c=>c.meta_activa&&(al==='todo'||esMio(ctx,c.cliente_id,[c.equipo?.account,c.equipo?.trafficker,c.equipo?.crm])));
 const filas=cl.map(c=>{const m=resultadosFilaDia314(c,cap,hoy);return {texto:c.nombre,extra:m.extra,estado:m.estado,icono:'target',href:hrefCap(ctx,c.cliente_id)};});
 const primero=cl.map(c=>({c,m:resultadosFilaDia314(c,cap,hoy)})).filter(x=>x.m.cpl.evaluable&&x.m.cpl.estado==='rojo').map(({c,m})=>({peso:3,icono:'target',motivo:`${c.nombre} · CPL frente a objetivo propio`,detalle:m.cpl.nota,ruta:sinAlmohadilla(hrefCap(ctx,c.cliente_id)),clave:`cpl:${c.cliente_id}`,cliente_id:c.cliente_id}));
 const crm=D.opcional('crm/crm');
 if(crm){const subs=(crm.subcuentas||[]).filter(s=>cl.some(c=>c.cliente_id===s.cliente_id)).map(s=>crmDia314(s,crm,hoy)).filter(s=>s.sin_tocar_24h>0);
 if(subs.length)filas.push({texto:`${plural(suma(subs,s=>s.sin_tocar_24h),'contacto')} sin intento registrado en24h; contrastar con el despacho`,extra:'Lectura CRM parcial; no mide respuesta ni cualificación',estado:'ambar',icono:'phone',href:ir(ctx,'salud-crm',subs[0].sub_id)});}
 const ayer=totalMetaDia314(cl.map(c=>metaDia314(c,cap,'ayer',hoy)));
 return {valor:ayer===null?null:fmt.num(ayer),unidad:`eventos lead Meta ayer · ${plural(cl.length,'cuenta')}`,estado:filas.some(f=>f.estado==='rojo')?'rojo':filas.some(f=>f.estado==='ambar')?'ambar':'gris',comparacion:null,
 motivo:'Referencias anteriores separadas de eventos acreditados. No mide contactos únicos, cualificación ni ventas.',filas,primero,vacio:{titulo:'Sin observaciones en la copia autorizada',texto:'No acredita ausencia de problemas ni resultados.'},frescura:fresco('Meta + GoHighLevel',cap),medible:'medias'};
}
def('resultados_ayer', ['captacion/captacion', 'crm/crm'], (ctx, D, b) => resultadosClientes(ctx, D, b, 'todo'));
/** R12 (auditoría A3): lo PRIMERO del account son los resultados de sus despachos: leads, citas, coste por lead y ventas
 *  de cada cliente de su cartera (asignaciones), de Captación (Meta + GoHighLevel). La salud va después. */
def('resultados_mios', ['captacion/captacion','crm/crm'], (ctx,D,b)=>{
 const base=resultadosClientes(ctx,D,b,'mio'),cap=D.dato('captacion/captacion'),hoy=ctx.hoy||hoyISO(),cartera=silla(ctx,'account')||ctx.carteraIds;
 const activos=clientesDia314(ctx,cap.clientes).filter(c=>cartera.has(c.cliente_id)&&c.meta_activa),l7=totalMetaDia314(activos.map(c=>metaDia314(c,cap,'7d',hoy)));
 return {...base,valor:l7===null?null:fmt.num(l7),unidad:`eventos lead Meta en7 días · ${plural(activos.length,'cuenta')}`,comparacion:null,
 filas:activos.map(c=>{const m=resultadosFilaDia314(c,cap,hoy);return {texto:c.nombre,extra:m.extra,estado:m.estado,icono:'target',href:hrefCap(ctx,c.cliente_id)};}).concat(base.filas.filter(f=>f.icono==='phone'))};
});

def('captacion_ro', ['ventas_ro/ventas_ro', 'finanzas/finanzas', 'finanzas/direccion'], (ctx, D) => {
  const v = D.dato('ventas_ro/ventas_ro');
  const m = v.meses?.[mesActual()] || {};
  const a = v.meses?.[mesAnterior()] || {};
  const coste = m.firmados && m.inversion !== undefined ? m.inversion / m.firmados : null;
  const costeA = a.firmados && a.inversion !== undefined ? a.inversion / a.firmados : null;
  const est = c => colorCifra('coste_cliente', c);
  const filas = [
    { texto: `${nombreMesActual()[0].toUpperCase() + nombreMesActual().slice(1)}: ${fmt.num(m.citas)} citas, ${fmt.num(m.celebradas)} celebradas, ${fmt.num(m.propuestas)} propuestas, ${fmt.num(m.firmados)} firmados`, extra: coste !== null ? `${eurG(coste)} por cliente` : 'sin firmados aún', estado: est(coste), icono: 'megafono', href: '#/ventas-ro' },
    { texto: `${MESES[Number(mesAnterior().slice(5)) - 1]}: ${fmt.num(a.firmados)} firmados de ${fmt.num(a.celebradas)} celebradas`, extra: costeA !== null ? `${eurG(costeA)} por cliente` : '', estado: est(costeA), icono: 'hist', href: '#/ventas-ro' },
  ];
  if (m.sin_marcar) filas.push({ texto: `${plural(m.sin_marcar, 'cita')} pasada${m.sin_marcar === 1 ? '' : 's'} sin marcar si vino`, estado: 'ambar', icono: 'flag', href: '#/ventas-ro' });
  const f = D.opcional('finanzas/finanzas');
  const cr = (D.opcional('finanzas/direccion')?.direccion?.[0] || f?.direccion?.[0])?.cuota_recurrente;
  const tres = cuotaTres(D, ctx);
  if (tres.length) {
    if (cr?.si_firman) tres[0] = { ...tres[0], extra: `${tres[0].extra} · si firman los ${(cr.pendientes || []).length} pendientes: ${eurG(cr.si_firman)}` };
    filas.unshift(...tres);
  } else if (cr?.actual) filas.unshift({ texto: `Cuota firmada: ${eurG(cr.actual)} al mes con ${cr.clientes} clientes`, extra: cr.si_firman ? `si firman los ${(cr.pendientes || []).length} pendientes: ${eurG(cr.si_firman)}` : '', estado: 'verde', icono: 'sube', href: '#/finanzas' });
  return {
    valor: fmt.num(m.firmados), unidad: `firmados de ${v.objetivo_firmados_mes ?? '—'}`, estado: est(coste),
    motivo: `Publicidad ${eurG(m.inversion)} → ${fmt.num(m.contactos)} contactos → ${fmt.num(m.citas)} citas → ${fmt.num(m.celebradas)} celebradas → ${fmt.num(m.firmados)} firmados. Coste por cliente: bien ≤ 700 € (D-13).`,
    extra: embudoBarras([
      { etiqueta: 'Contactos', valor: m.contactos, icono: 'users' }, { etiqueta: 'Citas', valor: m.citas, icono: 'cal' },
      { etiqueta: 'Celebradas', valor: m.celebradas, icono: 'video' }, { etiqueta: 'Propuestas', valor: m.propuestas, icono: 'doc' },
      { etiqueta: 'Firmados', valor: m.firmados, icono: 'editar', estado: 'verde' }]),
    filas, frescura: fresco('GoHighLevel de RO', v), medible: 'hoy',
  };
});

def('caja', ['finanzas/finanzas', 'finanzas/direccion'], (ctx, D) => {
  const f = D.dato('finanzas/finanzas');
  const a = f.admin || {}; const c = a.caja || {}; const dir = D.opcional('finanzas/direccion')?.direccion?.[0] || f.direccion?.[0] || {};
  const meses = dir.caja?.meses ?? null;
  const ct = a.cuota_tres || {}; const imp = a.impagos || {};
  const filas = (c.cuentas || []).map(x => ({ texto: x.banco, extra: x.moneda === 'EUR' ? eurG(x.eur) : `${fmt.num(x.saldo)} ${x.moneda} · ${eurG(x.eur)}`, estado: 'gris', icono: 'cartera' }));
  if (ct.cobrada !== undefined) filas.push({ texto: `Cuota cobrada: ${eurG(ct.cobrada)} de ${eurG(ct.facturada)} facturada (${fmt.pct(ct.cobrado_pct)})`, extra: `septiembre: ${fmt.pct(ct.cobrado_pct_sep)} cobrada`, estado: 'gris', icono: 'euro', href: '#/finanzas' });
  const filasImp = (imp.filas || []).filter(x => n0(x.dias) > 30);
  if (filasImp.length) filas.unshift({ texto: `${plural(filasImp.length, 'impago')} de más de 30 días`, extra: eurG(suma(filasImp, x => x.importe)), estado: filasImp.some(x => x.dias > 60) ? 'rojo' : 'ambar', icono: 'alert', href: '#/finanzas' });
  return {
    valor: eurG(c.total_eur), unidad: 'en bancos', estado: meses === null ? 'gris' : meses >= 2 ? 'verde' : meses >= 1 ? 'ambar' : 'rojo',
    motivo: `${meses === null ? '—' : fmt.num(meses, 1)} meses de caja (bien desde 2; gasto medio ${eurG(dir.caja?.gasto_medio)} al mes). ${eurG(a.devueltos?.length ? suma(a.devueltos, x => x.importe) : 0)} devueltos.`,
    filas, frescura: fresco('Holded', c.fecha || f), medible: 'hoy',
    primero: filasImp.filter(x => x.dias > 60).map(x => ({ peso: 3, icono: 'euro', motivo: `Impago de ${x.nombre} · ${x.dias} días`, detalle: `${eurG(x.importe)} · a 60 días decide Tomás (D-21).`, ruta: `finanzas/cobros/${encodeURIComponent(x.doc)}`, clave: `impago:${x.doc}`, cliente_id: x.cliente_id, grupo: `factura:${x.doc}` })),
  };
});

def('equipo_tomas', ['personas_m20/equipo', 'dinero_cliente/dinero_cliente'], (ctx, D) => {
  const e = D.dato('personas_m20/equipo');
  const alerta = (e.personas || []).filter(p => p.alerta);
  const filas = alerta.map(p => ({ texto: `${p.alias} · ${(p.alerta.motivos || [])[0] || 'en alerta'}`, extra: `desde ${diaCorto(p.alerta.desde)}`, estado: 'rojo', icono: 'alert', href: hrefPersona(ctx, p.persona_id) }));
  const dc = D.opcional('dinero_cliente/dinero_cliente');
  const huecos = dc ? suma(dc.por_account || [], x => x.huecos) : null;
  if (huecos !== null) filas.push({ texto: `Huecos libres en accounts: ${fmt.num(huecos)}`, extra: 'aviso con 5 o menos (D-07)', estado: huecos <= 5 ? 'ambar' : 'verde', icono: 'users', href: '#/dinero-cliente' });
  const sobre = (e.personas || []).filter(p => (p.sobre_capacidad || []).length);
  if (sobre.length) filas.push({ texto: `${plural(sobre.length, 'persona')} por encima de su capacidad`, extra: sobre.map(p => p.alias).slice(0, 3).join(', '), estado: 'ambar', icono: 'medidor', href: '#/personas' });
  return {
    valor: alerta.length, unidad: alerta.length === 1 ? 'persona en alerta' : 'personas en alerta', estado: alerta.length ? 'rojo' : 'verde',
    motivo: `${e._meta?.nota || ''}`.trim() || 'Personas en alerta, huecos en accounts y carga.',
    filas: filas.sort(ordenEstado), frescura: fresco('Personas', e), medible: 'medias', medibleDetalle: 'Horas incompletas (D-27): solo como aviso',
  };
});

def('encargos_fuegos', ['incidencias/incidencias'], (ctx, D) => {
  const inc = D.dato('incidencias/incidencias');
  const l = (inc.incidencias || []).filter(i => i.gravedad === 'rojo')
    .sort((a, b) => (b.queja ? 1 : 0) - (a.queja ? 1 : 0) || String(b.detectada).localeCompare(String(a.detectada)));
  const quejas = l.filter(i => i.queja);
  return {
    valor: l.length, unidad: `incidencias en rojo · ${plural(quejas.length, 'queja')}`, estado: l.length ? 'rojo' : 'verde',
    motivo: 'Fuegos abiertos con su responsable; los escalados a ti llevan reloj de 48 h. Los encargos de Tomás con fecha todavía no se apuntan en ninguna herramienta (se suben como decisión).',
    filas: l.map(i => ({ texto: `${i.cliente || 'Sin cliente'} · ${i.titulo}`, extra: `${nombre(ctx, i.responsable_id)} · desde ${diaCorto(i.detectada)}`, estado: i.queja ? 'rojo' : 'ambar', icono: i.queja ? 'megafono' : 'fire', href: ir(ctx, 'incidencias', i.id), abrir: i.prueba ? { href: i.prueba, texto: 'la prueba' } : null })),
    frescura: fresco('Incidencias', inc), medible: 'hoy',
    primero: quejas.slice(0, 2).map(i => ({ peso: 3.5, icono: 'megafono', motivo: `Queja · ${i.cliente || 'sin cliente'}`, detalle: i.texto, ruta: `incidencias/${i.id}`, clave: `inc:${i.id}`, cliente_id: i.cliente_id })),
  };
});

// ------------------------------------------------------------- Finanzas de dirección (solo Tomás)
/** Datos de dirección (solo Tomás): data/finanzas/direccion.json → direccion[0]; antes venían dentro de finanzas.json. */
const fdir = D => D.opcional('finanzas/direccion')?.direccion?.[0] || D.opcional('finanzas/finanzas')?.direccion?.[0] || (() => { throw { falta: 'finanzas/direccion', motivo: D.opcional('finanzas/finanzas') ? 'no_puesto' : 'no_existe' }; })();
/** Las tres cifras de cuota del mes, de finanzas.json → admin.cuota_tres (las mismas que Finanzas): recurrente firmada,
 *  cuota del mes (con proyectos) y facturable. Nunca se suman. servir.py quita las claves cuota_* a quien no ve la cuota:
 *  para esa persona no hay filas (ni ceros). */
function cuotaTres(D, ctx) {
  // Ronda 9 (D-P-DIN): la cuota única de la empresa (ctx.cuotaEmpresa()); el fichero de Finanzas, solo de respaldo.
  const ce = ctx?.cuotaEmpresa?.();
  const ct = ce && ce.recurrente !== undefined ? ce : D.opcional('finanzas/finanzas')?.admin?.cuota_tres;
  if (!ct || ct.recurrente === undefined) return [];
  const mes = ct.mes ? MESES[Number(ct.mes.slice(5)) - 1] : 'este mes';
  return [
    { texto: 'Cuota recurrente firmada', extra: `${eurG(ct.recurrente)} al mes`, estado: 'gris', icono: 'editar', href: '#/finanzas' },
    { texto: `Cuota de ${mes}, con proyectos`, extra: eurG(ct.cuota_mes), estado: 'gris', icono: 'euro', href: '#/finanzas' },
    { texto: `Facturable en ${mes}`, extra: eurG(ct.facturable), estado: 'gris', icono: 'doc', href: '#/finanzas' },
  ];
}
/** Beneficio del año hasta el último mes cerrado (direccion[0].anio.bai, el de Finanzas): «enero-agosto: 93.492 €». */
function acumulado(D) {
  const d = fdir(D); const a = d.anio || {};
  const meses = (d.pyg || []).filter(x => x.bai !== undefined && x.bai !== null).map(x => x.m).sort();
  if (a.bai === undefined || !meses.length) return null;
  const nom = m => MESES[Number(m.slice(5)) - 1];
  return { bai: a.bai, real: a.real, plan: a.plan_res, texto: meses.length > 1 ? `${nom(meses[0])}-${nom(meses[meses.length - 1])}` : nom(meses[0]) };
}
/** Beneficio: el MISMO número y la misma etiqueta que Finanzas (direccion[0].numero = último mes cerrado). */
function beneficio(D) {
  const d = fdir(D); const n = d.numero || {};
  const mes = n.mes || d.mes_cerrado;
  const p = (d.pyg || []).filter(x => x.bai !== undefined && x.bai !== null);
  const i = p.findIndex(x => x.m === mes);
  return { n, mes, nombreMes: mes ? MESES[Number(mes.slice(5)) - 1] : '', ant: i > 0 ? p[i - 1] : null, serie: p };
}
def('fin_beneficio', ['finanzas/finanzas', 'finanzas/direccion'], (ctx, D) => {
  const { n, nombreMes, serie } = beneficio(D);
  const acu = acumulado(D);
  return {
    valor: eurG(n.beneficio), unidad: `beneficio de ${nombreMes}`, estado: colorTrayectoria(n),
    motivo: `Plan del mes: ${eurG(n.plan_res)}. Ingresos ${eurG(n.ingresos)}, gastos ${eurG(n.gastos)}. Contando el gasto sin factura (${eurG(n.sin_factura)}): ${eurG(n.beneficio_real)}.`,
    filas: [
      ...(acu ? [{ texto: `Beneficio ${acu.texto}`, extra: `${eurG(acu.bai)} · plan ${eurG(acu.plan)} · con el gasto sin factura ${eurG(acu.real)}`, estado: colorCifra('beneficio', acu.bai), icono: 'sube', href: '#/finanzas' }] : []),
      ...serie.slice(-4).reverse().map(x => ({ texto: MESES[Number(x.m.slice(5)) - 1], extra: `${eurG(x.bai)} · con el gasto sin factura ${eurG(x.real)} · plan ${eurG(x.plan_res)}`, estado: colorCifra('beneficio', x.bai), icono: 'euro', href: '#/finanzas' }))],
    frescura: fresco('Holded', D.opcional('finanzas/direccion') || D.dato('finanzas/finanzas')), medible: 'medias', medibleDetalle: 'Último mes cerrado; el cierre lo hace Sofía el día 10',
  };
});
def('fin_rentabilidad', ['dinero_cliente/dinero_cliente'], (ctx, D) => {
  const dc = D.dato('dinero_cliente/dinero_cliente');
  const r = (dc.rentabilidad || []).filter(x => x.coste?.margen_pct !== undefined).sort((a, b) => a.coste.margen_pct - b.coste.margen_pct);
  const perd = r.filter(x => x.coste.margen_pct < 0);
  return {
    valor: perd.length, unidad: `en pérdida de ${r.length}`, estado: perd.length >= 3 ? 'rojo' : perd.length ? 'ambar' : 'verde',
    motivo: `A ${fmt.num(dc.tarifa_hora, 2)} €/h. ${dc.imputacion?.texto || ''}`,
    filas: r.map(x => ({ texto: `${x.nombre} · ${x.account || 'sin account'}`, extra: `${fmt.pct(x.coste.margen_pct)} · ${fmt.num(x.coste.horas, 1)} h`, estado: x.coste.margen_pct < 0 ? 'rojo' : x.coste.margen_pct < 10 ? 'ambar' : 'verde', icono: 'grafico', href: ir(ctx, 'dinero-cliente', x.cid, hrefCliente(ctx, x.cid)) })),
    frescura: fresco('Holded + Airtable + ClickUp', dc), medible: 'medias', medibleDetalle: `Horas incompletas: ${fmt.pct(dc.imputacion?.pct)} imputado`,
  };
});
def('fin_caja_meses', ['finanzas/finanzas', 'finanzas/direccion'], (ctx, D) => {
  const d = fdir(D); const c = d.caja || {};
  return {
    valor: fmt.num(c.meses, 1), unidad: 'meses de caja', estado: c.meses >= 2 ? 'verde' : c.meses >= 1 ? 'ambar' : 'rojo',
    motivo: `Caja ${eurG(c.total)} ÷ ${c.gasto_medio_texto || 'gasto medio'} ${eurG(c.gasto_medio)}. Bien desde 2 meses.`,
    filas: [{ texto: 'Cierre del 31 de agosto', extra: `${eurG(c.cierre_31ago)} · ${fmt.num(c.meses_31ago, 1)} meses`, estado: 'gris', icono: 'hist' }],
    frescura: fresco('Holded', D.dato('finanzas/finanzas')), medible: 'hoy',
    primero: c.meses < 2 ? [{ peso: c.meses < 1 ? 3.2 : 2.3, icono: 'cartera', motivo: `${fmt.num(c.meses, 1)} meses de caja`, detalle: `Por debajo de 2 meses, que es el mínimo. Caja ${eurG(c.total)}; gasto medio ${eurG(c.gasto_medio)} al mes.`, ruta: 'finanzas', clave: 'caja:meses' }] : [],
  };
});
def('fin_equipo', ['finanzas/finanzas', 'finanzas/direccion'], (ctx, D) => {
  const d = fdir(D); const areas = d.equipo?.areas || [];
  const coste = suma(areas, a => a.coste_mes);
  const p = (d.pyg || []).filter(x => x.ing); const ing = p[p.length - 1]?.ing;
  const peso = ing ? Math.round((coste / ing) * 100) : null;
  return {
    valor: fmt.pct(peso), unidad: 'de los ingresos', estado: peso === null ? 'gris' : peso <= 55 ? 'verde' : peso <= 65 ? 'ambar' : 'rojo',
    motivo: `Coste del equipo ${eurG(coste)} al mes, solo por áreas de 3 o más personas (D-89).`,
    filas: areas.map(a => ({ texto: `${a.area} · ${plural(a.personas, 'persona')}`, extra: eurG(a.coste_mes), estado: 'gris', icono: 'eq' })),
    frescura: fresco('Holded', D.dato('finanzas/finanzas')), medible: 'hoy',
  };
});
def('fin_recurrente', ['finanzas/finanzas', 'finanzas/direccion'], (ctx, D) => {
  const cr = fdir(D).cuota_recurrente || {};
  const tres = cuotaTres(D, ctx);
  return {
    valor: eurG(cr.actual), unidad: `cuota firmada al mes · ${plural(cr.clientes || 0, 'cliente')}`, estado: '',
    motivo: `Si firman los ${(cr.pendientes || []).length} pendientes: ${eurG(cr.si_firman)} al mes de cuota firmada. Lo que hay en facturación (Airtable): ${eurG(cr.facturacion_airtable)}. Firmada, facturada y cobrada nunca se suman.`,
    filas: [...tres.slice(1), ...(cr.pendientes || []).map(p => ({ texto: p.nombre_m, extra: `${eurG(p.cuota)} · ${p.dias} días · ${p.abierta ? 'abierta' : 'sin abrir'}`, estado: p.abierta ? 'gris' : 'ambar', icono: 'editar', href: '#/ventas-ro' }))],
    frescura: fresco('Airtable + GHL de RO', D.dato('finanzas/finanzas')), medible: 'hoy',
  };
});
def('fin_valor_cliente', ['finanzas/finanzas', 'finanzas/direccion'], (ctx, D) => {
  const k = fdir(D).kpi || {};
  return {
    valor: eurG(k.ltv_media), unidad: 'de valor medio por cliente', estado: '',
    motivo: `Mediana ${eurG(k.ltv_mediana)}; bajas: ${fmt.num(k.churn_n, 1)} % al mes; retención neta ${fmt.pct(k.nrr)} (bien ≥ 90, D-15).`,
    filas: [
      { texto: 'Cuota media', extra: eurG(k.cuota_media), icono: 'euro', estado: 'gris' },
      { texto: 'Vida media de los activos', extra: `${fmt.num(k.vida_act_media, 1)} meses`, icono: 'clock', estado: 'gris' },
      { texto: 'Vida mediana de las bajas', extra: `${fmt.num(k.vida_baja_mediana, 1)} meses`, icono: 'baja', estado: 'gris' },
      { texto: 'Ingresos por persona (12 meses)', extra: eurG(k.ing_persona), icono: 'eq', estado: 'gris' },
      { texto: 'Retención neta de ingresos', extra: fmt.pct(k.nrr), icono: 'heart', estado: semaforo(k.nrr, { verde: 90, ambar: 85 }) },
    ],
    frescura: fresco('Holded + libro de bajas', D.dato('finanzas/finanzas')), medible: 'medias',
  };
});

// ------------------------------------------------------------- Administración (Sofía)
const fadm = D => D.dato('finanzas/finanzas').admin || {};
def('adm_calendario', ['finanzas/finanzas'], (ctx, D) => {
  // V2 (M13): «hoy» es el día de verdad (calendario común), no el del fichero: el «Día 2 · hoy» de un día 3 pasa a «pendiente
  // desde el vie 2» si nadie lo ha marcado hecho.
  const a = fadm(D); const hoyD = hoyISO();
  const l = (a.calendario || []).map(x => ({ ...x, est: x.estado === 'hecho' ? 'hecho' : !x.fecha ? x.estado : x.fecha === hoyD ? 'hoy' : x.fecha < hoyD ? 'atrasado' : 'proximo' }));
  const hoy = l.filter(x => x.est === 'hoy'), atr = l.filter(x => x.est === 'atrasado');
  return {
    valor: hoy.length, unidad: `${hoy.length === 1 ? 'cosa para hoy' : 'cosas para hoy'}${atr.length ? ` · ${plural(atr.length, 'pendiente', 'pendientes')} de días pasados` : ''}`, estado: atr.length ? 'rojo' : hoy.length ? 'ambar' : 'verde',
    motivo: [hoy.length ? `Hoy: ${hoy.map(x => x.que).join(' · ')}.` : 'Hoy no toca nada del calendario.', atr.length ? `Sin marcar hecho: ${atr.map(x => `${x.que} (día ${x.dia})`).join(' · ')}.` : null].filter(Boolean).join(' '),
    filas: l.map(x => ({ texto: `Día ${x.dia} · ${x.que}`, extra: `${x.donde} · ${x.est === 'hecho' ? 'hecho' : x.est === 'hoy' ? 'hoy' : x.est === 'atrasado' ? `pendiente desde el ${FECHAS.diaSemana(x.fecha)} ${diaCorto(x.fecha)}` : diaCorto(x.fecha)}`, estado: x.est === 'hecho' ? 'verde' : x.est === 'atrasado' ? 'rojo' : x.est === 'hoy' ? 'ambar' : 'gris', icono: 'cal' })),
    frescura: fresco('Holded', D.dato('finanzas/finanzas')), medible: 'hoy',
  };
});
def('adm_cobros', ['finanzas/finanzas'], (ctx, D) => {
  const a = fadm(D); const ct = a.cuota_tres || {}; const dv = a.devueltos || [];
  return {
    valor: fmt.pct(ct.cobrado_pct), unidad: 'de lo facturado', estado: hoyDia().getDate() < 10 ? 'gris' : semaforo(ct.cobrado_pct, { verde: 95, ambar: 85 }),
    motivo: ct.nota || 'Firmada, facturada y cobrada: tres cifras que nunca se suman (D-12).',
    filas: [
      { texto: 'Firmada', extra: eurG(ct.firmada), icono: 'editar', estado: 'gris' },
      { texto: `Facturada · ${plural(ct.facturas_n || 0, 'factura')}`, extra: eurG(ct.facturada), icono: 'doc', estado: 'gris' },
      { texto: 'Cobrada', extra: eurG(ct.cobrada), icono: 'euro', estado: 'gris' },
      ...dv.map(x => ({ texto: `Devuelto · ${x.nombre || x.cliente || ''}`, extra: eurG(x.importe), estado: 'rojo', icono: 'alert' })),
    ],
    frescura: fresco('Holded', D.dato('finanzas/finanzas')), medible: 'hoy', medibleDetalle: 'Se juzga el día 10',
  };
});
def('adm_impagos', ['finanzas/finanzas'], (ctx, D) => {
  const im = fadm(D).impagos || {};
  const l = (im.filas || []).filter(x => n0(x.dias) > 0).sort((a, b) => b.dias - a.dias);
  return {
    valor: eurG(im.vencido_total), unidad: `vencido · ${plural(im.vencido_n || 0, 'factura')}`, estado: n0(im.mas_60) ? 'rojo' : n0(im.mas_30) ? 'ambar' : 'verde',
    motivo: 'Aviso a 30 días, decisión de Tomás a 60, nunca más de 2 cuotas (D-21).',
    filas: l.map(x => ({ texto: `${x.nombre} · ${x.doc}`, extra: `${x.dias} días · ${eurG(x.importe)}${x.aviso ? ' · ' + x.aviso : ''}`, estado: x.dias > 60 ? 'rojo' : x.dias > 30 ? 'ambar' : 'gris', icono: 'alert', href: hrefCobro(ctx, x.doc, x.holded || null), verbo: 'Abrir el cobro', abrir: x.holded ? { href: x.holded, texto: 'Holded' } : null })),
    frescura: fresco('Holded', D.dato('finanzas/finanzas')), medible: 'hoy',
    // V2 (M13): la misma factura que la alerta «Factura vencida sin cobrar» abre el mismo cobro (finanzas/cobros/<factura>):
    // «Lo mío» las junta en una fila, nunca dos veces IP Forense A-26-001
    primero: l.filter(x => x.dias > 30).slice(0, 2).map(x => ({ peso: x.dias > 60 ? 3 : 2, icono: 'euro', motivo: `Impago · ${x.nombre} · ${x.dias} días`, detalle: `${eurG(x.importe)} · ${x.aviso || 'aviso a 30 días'}`, ruta: `finanzas/cobros/${encodeURIComponent(x.doc)}`, clave: `impago:${x.doc}`, cliente_id: x.cliente_id, grupo: `factura:${x.doc}` })),
  };
});
def('adm_firmas', ['finanzas/finanzas'], (ctx, D) => {
  const l = fadm(D).firmas_sin_alta || [];
  return {
    valor: l.length, unidad: 'firmados sin alta', estado: l.some(x => x.dia0_pasado) ? 'rojo' : l.length ? 'ambar' : 'verde',
    motivo: 'Del contrato en Zoho Sign al alta en facturación antes del día 0.',
    filas: l.map(x => ({ texto: x.nombre, extra: `firmado el ${diaCorto(x.firma)} · día 0: ${diaCorto(x.alta)} · ${x.account || 'sin account'}`, estado: x.dia0_pasado ? 'rojo' : 'ambar', icono: 'doc', href: hrefCobro(ctx, x.cliente_id, hrefCliente(ctx, x.cliente_id)), verbo: 'Abrir el cobro' })),
    vacio: { titulo: 'Todos los firmados tienen su alta', tono: 'celebrar' },
    frescura: fresco('Zoho Sign + Airtable', D.dato('finanzas/finanzas')), medible: 'hoy',
  };
});
def('adm_bajas', ['finanzas/finanzas'], (ctx, D) => {
  const l = fadm(D).bajas_cambios || [];
  return {
    valor: l.length, unidad: 'bajas y cambios', estado: '', motivo: 'Lo que tiene que reflejar la facturación de este mes.',
    filas: l.map(x => ({ texto: x.nombre, extra: eurG(x.importe), estado: x.importe < 0 ? 'ambar' : 'gris', icono: x.importe < 0 ? 'baja' : 'sube' })),
    frescura: fresco('Doc de octubre para Sofía', D.dato('finanzas/finanzas')), medible: 'hoy',
  };
});
def('adm_meta', ['finanzas/finanzas'], (ctx, D) => {
  const m = fadm(D).meta_sin_factura || {};
  // V2 (A6): un dato tapado nunca es «nada pendiente»: si hay mes y el importe no llega a su puesto, se dice qué hacer, en llano
  const oculto = m.mes && m.gasto_meta === undefined;
  const mes = m.mes ? MESES[Number(m.mes.slice(5)) - 1] : '';
  const limpio = String(m.texto || '').replace(/\s*\([^()]*(?:§|panel)[^()]*\)/g, '').trim();
  return {
    valor: oculto ? null : eurG(m.gasto_meta), unidad: m.mes ? `de ${mes}` : '', estado: oculto ? 'ambar' : m.gasto_meta ? 'ambar' : 'verde',
    motivo: oculto ? `Hay facturas de Meta de ${mes} por contabilizar: Meta cobra por tarjeta y las facturas se bajan del administrador de anuncios. No ves el importe por tu puesto (lo ve dirección): pídeselo a Tomás.` : (limpio || 'Gasto de Meta sin factura en la contabilidad.'),
    filas: oculto ? [{ texto: `Facturas de Meta de ${mes} por contabilizar`, extra: 'no ves el importe por tu puesto: pídeselo a Tomás', estado: 'ambar', icono: 'doc' }] : [],
    vacio: m.mes ? { titulo: `Sin gasto de Meta pendiente en ${mes}`, tono: 'celebrar' } : { titulo: 'Sin dato de Meta', texto: 'Llega con el cierre del mes.' },
    frescura: fresco('Holded frente a Meta', D.dato('finanzas/finanzas')), medible: 'hoy',
  };
});
def('adm_conciliacion', ['finanzas/finanzas'], (ctx, D) => {
  const c = fadm(D).caja || {}; const s = c.sin_conciliar || {};
  const tot = c.sin_conciliar_total ?? suma(Object.values(s), x => x);
  return {
    valor: fmt.num(tot), unidad: 'movimientos sin conciliar', estado: tot === 0 ? 'verde' : tot < 50 ? 'ambar' : 'rojo',
    motivo: '0 al cierre · menos de 50 · 50 o más.',
    filas: Object.entries(s).sort((a, b) => b[1] - a[1]).map(([k, v]) => ({ texto: k, extra: plural(v, 'movimiento'), estado: v >= 50 ? 'rojo' : v ? 'ambar' : 'verde', icono: 'base' })),
    frescura: fresco('Holded', c.fecha), medible: 'hoy',
  };
});

// ------------------------------------------------------------- Operaciones (Mili)
def('ronda_mili', ['mi_dia/ronda_mili'], (ctx, D, b, extra) => {
  const r = D.dato('mi_dia/ronda_mili');
  const dia = hoyDia().getDay();
  const items = (r.items || []).filter(x => x.f === 'Cada día' || (x.f === 'Cada semana' && (dia === 1 || dia === 5))).map(x => x.id === 'r1' && x.donde === 'equipo' && x.que === 'Que nadie del equipo se quede sin imputar: quien ayer no llegó a 8 h, avisado.' ? { ...x, que: 'Revisar los registros de horas del equipo y aclarar los datos pendientes.', prueba: 'Registros observados y cobertura; sin jornada confirmada no se evalúa una obligación de 8 h.', referencia547: x.que } : x);
  const hechas = new Set((extra.acciones || []).filter(a => a.tipo === 'ronda' && String(a.objeto).startsWith(hoyISO())).map(a => String(a.objeto).split(':')[1]));
  const n = items.filter(x => hechas.has(x.id)).length;
  return {
    valor: `${n}/${items.length}`, unidad: 'hechas hoy', estado: n === items.length ? 'verde' : n ? 'ambar' : 'gris',
    // V2 (B7): sin las fechas de origen entre paréntesis («(22-jul, 11-sep)») y la fuente con su nombre de pantalla
    motivo: String((r.principios || [])[0] || 'Tu ronda de cada día, en orden.').replace(/\s*\((?:\d{1,2}-[a-zé]{3,4}\.?(?:,\s*|\s+y\s+)?)+\)/g, ''),
    ronda: { items, hechas, hoy: hoyISO() },
    frescura: fresco('Ronda de Mili', r), medible: 'hoy', medibleDetalle: 'Se marca aquí y queda en el rastro',
  };
});

def('clientes_esperando', ['bandeja/bandeja'], (ctx, D, b, extra) => {
  // V2 (M4): la regla de la pantalla Bandeja (bandejaComoPantalla: sin automáticos, ni viejos, ni lo ya despachado) y el account
  // de la verdad única: «Lucía · 13» aquí = los 13 de la Bandeja de Lucía (antes 14, contando lo que su Bandeja ya no enseña).
  const { bj, c, ll: llVivas } = bandejaComoPantalla(ctx, D, extra);
  const rojos = c.filter(x => x.gravedad === 'rojo');
  const porAcc = new Map();
  for (const x of rojos.slice().sort((a, b2) => b2.horas - a.horas)) { const pid = verdad(ctx, x.cliente_id)?.account ?? x.account_id ?? null; const k = pid || x.account || 'sin account'; const e = porAcc.get(k) || { n: 0, viejo: x, pid }; e.n += 1; porAcc.set(k, e); }
  const quejas = c.filter(x => x.queja);
  const filas = [...porAcc.entries()].sort((a, b2) => b2[1].n - a[1].n).map(([acc, e]) => ({ texto: `${e.pid ? nombre(ctx, e.pid) : acc} · ${plural(e.n, 'correo')} de más de 48 h`, extra: `el más viejo: ${e.viejo.cliente || 'sin cliente'}, ${esperaTxt(e.viejo)}`, estado: 'rojo', icono: 'mail', href: ir(ctx, 'bandeja', e.viejo.id) }));
  const ll = llVivas.filter(x => x.gravedad !== 'verde');
  if (ll.length) filas.unshift({ texto: `${plural(ll.length, 'llamada')} de clientes sin devolver`, extra: ll.map(x => x.cliente || 'número desconocido').slice(0, 3).join(', '), estado: 'rojo', icono: 'phone', href: ir(ctx, 'bandeja', ll[0].id) });
  if ((bj.triaje || []).length) filas.push({ texto: `${plural(bj.triaje.length, 'ticket')} sin asignar con propuesta`, estado: 'ambar', icono: 'inbox', href: '#/bandeja' });
  return {
    valor: rojos.length, unidad: `correos > 48 h · ${plural(quejas.length, 'queja')}`, estado: rojos.length ? 'rojo' : 'verde',
    motivo: 'Pídeselo al account, no lo contestes tú. Bien < 24 h · vigilar 24-48 h · crítico > 48 h.',
    filas, frescura: fresco('Desk + Zadarma', bj), medible: 'hoy',
    primero: quejas.slice(0, 2).map(x => ({ peso: 3.5, icono: 'megafono', motivo: x.cliente ? `Queja sin contestar · ${x.cliente}` : `Queja sin contestar · «${x.asunto}»`, detalle: `${x.cliente ? `«${x.asunto}» · ` : 'Sin cliente reconocido · '}${esperaTxt(x)} · ${x.account}`, ruta: `bandeja/${encodeURIComponent(x.id)}`, clave: `correo:${x.id}`, cliente_id: x.cliente_id })),
  };
});

/** Correos sin contestar por cliente con la regla de la Bandeja (sin automáticos ni ruido, días laborables):
 *  data/bandeja/por_cliente.json. Sustituye a la alarma «Sin responder» del panel de las 07:00. */
const SIN_RESPONDER = 'Sin responder';
function correosCliente(ctx, D) {
  const pc = D.opcional('bandeja/por_cliente');
  if (!pc) return null;
  return (pc.clientes || []).filter(x => n0(x.sin_contestar) > 0).map(x => {
    const c = ctx.clientes.find(y => y.id === x.cliente_id);
    const estado = n0(x.mas_48) || n0(x.quejas) ? 'rojo' : n0(x.entre_24_48) ? 'ambar' : 'verde';
    const ticket = x.mas_antiguo?.numero ? `t-${x.mas_antiguo.numero}` : null;
    return { ...x, nombre: c?.nombre || x.cliente_id, estado, ticket, generado: pc.generado,
      texto: `${plural(x.sin_contestar, 'correo')} sin contestar${n0(x.quejas) ? ` · ${plural(x.quejas, 'queja')}` : ''}`,
      detalle: `El más antiguo lleva ${plural(n0(x.dias_laborables_max), 'día laborable', 'días laborables')}${x.mas_antiguo?.asunto ? ` («${x.mas_antiguo.asunto}»)` : ''}.` };
  });
}
/** V2 · UNA vara de «rojo»: crítico de la verdad única (la misma gravedad de En rojo, la ficha y el menú). Clientes de un
 *  alcance con su gravedad, motivo y account; lo crítico primero. */
const PESO_GRAV = { critico: 0, atencion: 1, bien: 2 };
function porGravedad(ctx, soloMios) {
  return ctx.clientes.filter(c => !soloMios || ctx.carteraIds.has(c.id)).map(c => { const v = verdad(ctx, c.id) || {}; return { c, cid: c.id, v, grav: v.gravedad || null, mot: (v.motivos || [])[0] || '' }; })
    .sort((a, b2) => (PESO_GRAV[a.grav] ?? 3) - (PESO_GRAV[b2.grav] ?? 3) || String(a.c.nombre).localeCompare(String(b2.c.nombre), 'es'));
}
def('rojos_cartera', ['verdad/clientes'], (ctx, D, b) => {
  const todos = porGravedad(ctx, alcance(b, 'todo') === 'mio');
  const l = todos.filter(x => x.grav === 'critico');
  return {
    valor: l.length, unidad: `${l.length === 1 ? 'crítico' : 'críticos'} de ${plural(todos.length, 'cliente')} · ${todos.filter(x => x.grav === 'atencion').length} a vigilar`, estado: l.length ? 'rojo' : 'verde',
    motivo: 'La misma gravedad que En rojo y la ficha (verdad única). Cada uno con su motivo y su account; el plan escrito y el «Visto» de Coti, en En rojo.',
    filas: l.map(x => ({ texto: `${x.c.nombre} · ${x.mot || 'crítico'}`, extra: x.v.account ? nombre(ctx, x.v.account) : 'sin account', estado: 'rojo', icono: 'fire', href: `#/en-rojo/${x.cid}` })),
    vacio: { titulo: 'Ningún cliente crítico', tono: 'celebrar' },
    frescura: fresco('Verdad única de clientes', D.opcional('verdad/clientes')), medible: 'hoy',
  };
});

function altasNuevos(ctx, D, b, def2) {
  const n = D.dato('nuevos/nuevos');
  const al = alcance(b, def2);
  const l = (n.altas || []).filter(a => al === 'todo' || esMio(ctx, a.cliente_id, [a.dueno?.id, a.account?.id, a.trafficker?.id, a.crm?.id]));
  return { n, l };
}
def('nuevos_resumen', ['nuevos/nuevos'], (ctx, D, b) => {
  const { n, l } = altasNuevos(ctx, D, b, 'todo');
  const enc = a => verdad(ctx, a.cliente_id)?.encendido?.estado;
  const fuera = l.filter(a => (enc(a) ? enc(a) === 'sin_encender_fuera_de_plazo' : a.plazo?.estado === 'rojo'));
  return {
    valor: fuera.length, unidad: `fuera de plazo de ${l.length} altas`, estado: fuera.length ? 'rojo' : 'verde',
    motivo: 'Encendido el día 10, límite 12, desde el alta del contrato (D-28). Account asignado el día 0.',
    filas: l.slice().sort((a, b2) => ordenEstado({ estado: a.plazo?.estado }, { estado: b2.plazo?.estado }) || b2.dia - a.dia)
      .map(a => ({ texto: `${a.nombre} · día ${a.dia}`, extra: `${a.siguiente?.nombre || 'sin hito'} · ${a.dueno?.nombre || '—'}`, estado: a.plazo?.estado || 'gris', icono: 'rocket', href: ir(ctx, 'clientes-nuevos', a.cliente_id) })),
    frescura: fresco('Sign + ClickUp + Meta', n), medible: 'hoy',
    primero: fuera.slice(0, 2).map(a => ({ peso: 3, icono: 'rocket', motivo: `${a.nombre} · día ${a.dia} sin encender`, detalle: a.plazo?.texto || '', ruta: `clientes-nuevos/${a.cliente_id}`, clave: `alta:${a.cliente_id}`, cliente_id: a.cliente_id })),
  };
});

def('produccion_ops', ['produccion/produccion'], (ctx, D) => {
  const p = D.dato('produccion/produccion');
  const pr = p.proyectos || [];
  const ra = suma(pr, x => x.rev_account_48), rt = suma(pr, x => x.rev_tecnica_48);
  const bloq = pr.filter(x => (verdad(ctx, x.cliente_id)?.bloqueo_callado ?? n0(x.bloqueo_max) > 5));
  const filas = pr.filter(x => n0(x.rev_account_48) + n0(x.rev_tecnica_48) > 0).sort((a, b2) => (b2.rev_account_48 + b2.rev_tecnica_48) - (a.rev_account_48 + a.rev_tecnica_48))
    .map(x => ({ texto: `${x.cliente} · ${fmt.num(x.rev_account_48)} del account y ${fmt.num(x.rev_tecnica_48)} técnicas > 48 h`, extra: nombre(ctx, x.account_id), estado: x.rev_account_48 > 5 ? 'rojo' : 'ambar', icono: 'capas', href: hrefCliente(ctx, x.cliente_id, 'trabajo') || '#/produccion' }));
  if (bloq.length) filas.unshift({ texto: `${plural(bloq.length, 'proyecto')} con bloqueos del cliente de más de 5 días`, extra: bloq.slice(0, 3).map(x => x.cliente).join(', '), estado: 'rojo', icono: 'candado', href: hrefCliente(ctx, bloq[0].cliente_id, 'trabajo') || '#/produccion' });
  return {
    valor: fmt.num(ra + rt), unidad: 'revisiones de más de 48 h', estado: ra + rt ? 'rojo' : 'verde',
    motivo: `${fmt.num(ra)} del account y ${fmt.num(rt)} técnicas. El viernes, todo a cero.`,
    filas, frescura: fresco('ClickUp', p), medible: 'hoy',
  };
});

def('equipo_control', ['incidencias/incidencias', 'horas/horas', 'bandeja/bandeja', 'produccion/produccion'], (ctx, D, b, extra) => {
  const inc = D.dato('incidencias/incidencias');
  const ctl = (inc.control || []).map(x => {
    if (!x.persona_ref) return x;
    const cp = controlPersona(ctx, D, x.persona_ref, extra);
    return { ...x, contesta: cp.contesta ? { ...x.contesta, mas48: cp.contesta.mas48, correos: cp.contesta.total } : x.contesta, revisa: cp.revisa ? { ...x.revisa, mas48: cp.revisa.mas48, total: cp.revisa.total } : x.revisa };
  });
  const filas=prepararControlEquipo313(ctx,ctl,D.opcional('horas/horas'));
  const medidas=filas.filter(x=>x.control_313.celdas.imputa.tipo==='observado').length;
  const referencias=filas.filter(x=>x.control_313.celdas.imputa.tipo==='referencia').length;
  const dia=filas[0]?.control_313.fecha;
  return {
    valor: filas.length||null, unidad: 'personas en el ámbito autorizado', estado: 'gris',
    motivo: `Mapa de registros por persona. ${medidas?`${medidas} con horas observadas del ${dia} (última fecha lunes–viernes; calendario no acreditado).`:'Horas diarias: sin observaciones tipadas suficientes.'} ${referencias?`${referencias} con referencia heredada marcada.`:''} Cobertura parcial: no se evalúa jornada, ausencia ni cumplimiento desde huecos de la copia.`,
    filas: [], mapa: filas, frescura: fresco('Incidencias · horas autorizadas', inc), medible: 'medias',
  };
});

def('para_tomas', ['decisiones/reloj', 'nuevos/nuevos', 'incidencias/incidencias'], (ctx, D) => {
  const r = D.dato('decisiones/reloj');
  const mias = (r.decisiones || []).filter(x => x.quien === yo(ctx) || ctx.persona.puestos.includes('direccion'));
  const abiertas = mias.filter(x => !x.respuesta);
  const n = D.opcional('nuevos/nuevos');
  const inc = D.opcional('incidencias/incidencias');
  // V2 (M4): el Nº 1 es EL MISMO cálculo que el número que manda de Mili (altas_en_plazo, verdad única): mismo «1 de 8 (13 %)»
  let n1 = null; try { n1 = n ? NUMERO.altas_en_plazo.hacer(ctx, D) : null; } catch { n1 = null; }
  const sinAviso = inc ? (inc.incidencias || []).filter(i => i.gravedad === 'rojo' && !(i.historia || []).length).length : null;
  const filas = [
    { texto: `Nº 1 · Altas encendidas el día 10: ${n1?.valor ? `${n1.valor} ${n1.unidad.replace(/^encendidas el día 10\s*/, '')}` : 'sin dato'}`, extra: 'día 10, límite 12 · el mismo número que manda de Operaciones', estado: n1?.estado || 'gris', icono: 'rocket', href: '#/clientes-nuevos' },
    { texto: 'Nº 2 · Horas por cuenta nueva', extra: 'a medias: horas incompletas (D-27)', estado: 'gris', icono: 'clock', href: '#/horas' },
    { texto: `Nº 3 · Fuegos en rojo sin aviso apuntado: ${sinAviso ?? '—'}`, extra: 'compromisos vencidos sin aviso', estado: sinAviso ? 'rojo' : 'verde', icono: 'alert', href: '#/incidencias' },
    ...abiertas.map(x => ({ texto: `Decisión subida: ${x.titulo}`, extra: `vence ${cuandoTxt(x.vence)}`, estado: x.estado === 'en plazo' ? 'ambar' : 'rojo', icono: 'flag', href: hrefDecision(ctx, x.id) })),
  ];
  return {
    valor: abiertas.length, unidad: 'decisiones sin contestar', estado: abiertas.some(x => x.estado !== 'en plazo') ? 'rojo' : abiertas.length ? 'ambar' : 'verde',
    motivo: 'Los 3 números del viernes y lo que le has subido con problema, recomendación y fecha. A Tomás, decisiones; no informes.',
    filas, frescura: fresco('Decisiones', r), medible: 'hoy',
  };
});

// ------------------------------------------------------------- Proyectos y oferta (Coti)
def('rojos_visto_coti', ['verdad/clientes'], (ctx, D) => {
  // V2 (A1): «rojo» = crítico de la verdad única (antes, la alarma del semáforo de las 07:00, con clientes en atención)
  const l = porGravedad(ctx, false).filter(x => x.grav === 'critico');
  return {
    valor: l.length, unidad: l.length === 1 ? 'cliente crítico' : 'clientes críticos', estado: l.length ? 'rojo' : 'verde',
    motivo: 'Los críticos de la verdad única (los mismos de En rojo). Antes de hablar con el cliente, tu «Visto» con números y plan (lo marcas en En rojo).',
    filas: l.map(x => ({ texto: `${x.c.nombre} · ${x.mot || 'crítico'}`, extra: x.v.account ? nombre(ctx, x.v.account) : 'sin account', estado: 'rojo', icono: 'ojo', href: `#/en-rojo/${x.cid}` })),
    vacio: { titulo: 'Ningún cliente crítico', tono: 'celebrar' },
    frescura: fresco('Verdad única de clientes', D.opcional('verdad/clientes')), medible: 'hoy',
    primero: l.slice(0, 2).map(x => ({ peso: 2.8, icono: 'ojo', motivo: `${x.c.nombre} · cliente crítico`, detalle: `${x.mot ? `${x.mot}. ` : ''}Falta tu «Visto» antes de la comunicación al cliente.`, ruta: `en-rojo/${x.cid}`, clave: `visto:${x.cid}`, cliente_id: x.cid, grupo: `critico:${x.cid}` })),
  };
});
def('nuevos_garantia', ['nuevos/nuevos'], (ctx, D, b) => {
  const { n, l } = altasNuevos(ctx, D, b, 'todo');
  const g = a => (a.hitos || []).find(h2 => h2.id === 'garantia');
  const aviso25 = l.filter(a => a.dia >= 20 && a.dia <= 30 && g(a)?.estado !== 'no_aplica');
  return {
    valor: l.filter(a => a.dia <= 30).length, unidad: 'altas en los primeros 30 días', estado: aviso25.length ? 'ambar' : '',
    motivo: `Taller día 1-3, encendido día 10/12 y aviso de la garantía el día 25 (D-31). ${aviso25.length ? `${aviso25.length} con aviso del día 25.` : ''}`,
    filas: l.slice().sort((a, b2) => a.dia - b2.dia).map(a => ({ texto: `${a.nombre} · día ${a.dia}`, extra: `${a.siguiente?.nombre || '—'} · garantía ${g(a)?.estado === 'no_aplica' ? 'no firmada' : g(a)?.estado || '—'}`, estado: a.plazo?.estado || 'gris', icono: 'rocket', href: ir(ctx, 'clientes-nuevos', a.cliente_id) })),
    frescura: fresco('Sign + ClickUp + Meta', n), medible: 'medias', medibleDetalle: 'La garantía solo aplica a quien la firmó (D-30)',
  };
});
def('resultados_nuevos', ['captacion/captacion'], (ctx, D) => {
  const cap = D.dato('captacion/captacion');
  const l = (cap.clientes || []).filter(c => c.nuevo);
  return {
    valor: fmt.num(suma(l, c => c.leads?.['7d'])), unidad: `${suma(l, c => c.leads?.['7d']) === 1 ? 'lead' : 'leads'} en 7 días · ${plural(l.length, 'nuevo')}`, estado: l.some(c => c.severidad === 'critico') ? 'rojo' : '',
    motivo: 'Leads, citas y reuniones desde el encendido, frente a la garantía.',
    filas: l.map(c => ({ texto: c.nombre, extra: `${plural(n0(c.leads?.['7d']), 'lead')} en 7 días · ${plural(n0(c.ghl?.citas?.mes?.agendadas), 'cita')} en el mes`, estado: c.severidad === 'critico' ? 'rojo' : c.severidad === 'atencion' ? 'ambar' : 'verde', icono: 'target', href: hrefCliente(ctx, c.cliente_id) })),
    frescura: fresco('Meta + GoHighLevel', cap), medible: 'hoy',
  };
});
def('semaforo_cartera', ['verdad/clientes'], (ctx, D) => {
  // V2 (A1): la cartera por GRAVEDAD de la verdad única (crítico · atención · bien), la misma vara que En rojo; la salud
  // (saludV, la de la ficha) va al lado de cada cliente, no decide el color. Antes: «94 % en verde · 0 en rojo» con 10 críticos.
  const l = porGravedad(ctx, false).map(x => ({ ...x, salud: saludV(ctx, x.cid) }));
  const n = g => l.filter(x => x.grav === g).length;
  const cr = n('critico'), at = n('atencion'), bi = n('bien');
  return {
    valor: fmt.pct(pct(bi, l.length)), unidad: `bien de ${l.length} · ${cr} ${cr === 1 ? 'crítico' : 'críticos'}`, estado: cr ? 'rojo' : at ? 'ambar' : 'verde',
    motivo: `${bi} bien, ${at} a vigilar y ${cr} ${cr === 1 ? 'crítico' : 'críticos'}: la misma gravedad que En rojo y la ficha.`,
    extra: l.length ? h('div', { class: 'fila', role: 'group', 'aria-label': `${cr} ${cr === 1 ? 'crítico' : 'críticos'}, ${at} a vigilar, ${bi} bien` },
      chipEstado('rojo', `${cr} ${cr === 1 ? 'crítico' : 'críticos'}`), chipEstado('ambar', `${at} a vigilar`), chipEstado('verde', `${bi} bien`)) : null,
    filas: l.map(x => ({ texto: `${x.c.nombre} · ${GRAV_TXT[x.grav] || 'sin estado'}`, extra: [x.mot, typeof x.salud === 'number' ? `salud ${x.salud}` : null, x.v.account ? nombre(ctx, x.v.account) : 'sin account'].filter(Boolean).join(' · '), estado: GRAV_EST[x.grav] || 'gris', icono: 'heart', href: hrefCliente(ctx, x.cid) })),
    frescura: fresco('Verdad única de clientes', D.opcional('verdad/clientes')), medible: 'medias', medibleDetalle: 'Reglas de gravedad de la verdad única; la salud, fórmula provisional',
  };
});
def('resultados_nicho',['captacion/captacion'],(ctx,D)=>{
 const cap=D.dato('captacion/captacion'),g=new Map();
 for(const c of clientesDia314(ctx,cap.clientes).filter(c=>c.meta_activa)){const k=c.nicho||'Sin nicho';if(!g.has(k))g.set(k,[]);g.get(k).push(c);}
 return {valor:g.size,unidad:'nichos con Meta encendida',estado:'gris',motivo:'Recuentos por cliente; no se combinan eventos de unidad desconocida ni costes de ventanas distintas.',
 filas:[...g].map(([k,cs])=>({texto:`${k} · ${plural(cs.length,'cuenta')}`,extra:cs.map(c=>`${c.nombre}: ${resultadosFilaDia314(c,cap,ctx.hoy||hoyISO()).extra}`).join(' · '),estado:'gris',icono:'capas',href:'#/captacion'})),frescura:fresco('Meta',cap),medible:'medias'};
});
def('gatillos_motor', ['dinero_cliente/dinero_cliente', 'captacion/captacion'], (ctx, D) => {
  const dc = D.dato('dinero_cliente/dinero_cliente');
  const cap = D.opcional('captacion/captacion');
  const embudo = new Map((cap?.clientes || []).map(c => [c.cliente_id, c.ghl?.embudo?.funnel]));
  const l = (dc.clientes || []).filter(c => n0(c.vida_meses) >= 1 && n0(c.vida_meses) < 3).map(c => ({ ...c, f: embudo.get(c.cliente_id) }))
    .filter(c => !c.f || !n0(c.f.cerrado));
  return {
    valor: l.length, unidad: 'en el mes 2-3 sin cierre registrado o sin dato', estado: l.length ? 'ambar' : 'verde',
    motivo: 'La regla del generador anterior avisa en meses 2-3 si falta etapa de cierre o dato. No acredita cero ventas: contrastar resultado comercial; una etapa «cerrado» tampoco confirma venta.',
    filas: l.map(c => ({ texto: c.nombre, extra: `mes ${Math.floor(n0(c.vida_meses)) + 1} · ${c.f ? `${n0(c.f.cita)} citas, ${n0(c.f.presupuesto)} presupuestos` : 'sin embudo en GHL'}`, estado: n0(c.vida_meses) >= 2 ? 'rojo' : 'ambar', icono: 'zap', href: hrefCliente(ctx, c.cliente_id) })),
    frescura: fresco('Airtable + GoHighLevel', dc), medible: 'medias', medibleDetalle: 'Cobertura de etapas de GHL; no confirma ventas ni ausencia de ventas',
  };
});

// ------------------------------------------------------------- RRHH (Cecilia)
const equipo = D => D.dato('personas_m20/equipo');
const txtCap = x => (typeof x === 'string' ? x : x?.texto || x?.silla || JSON.stringify(x));
/** V2 (M5): UNA definición de «en alerta sin plan», la de la pantalla Personas: plan = un apunte de tipo «plan»; «vencida» =
 *  7 días o más desde que entró en alerta (en días del calendario común). Mi día y Personas cuentan lo mismo (10 de 11). */
const planDe = p => (p.apuntes || []).filter(a => a.tipo === 'plan').slice(-1)[0] || null;
function alertaPersonas(e) {
  const en = (e.personas || []).filter(p => p.alerta);
  const sin = en.filter(p => !planDe(p));
  return { en, sin, vencidas: sin.filter(p => (FECHAS.diasDesde(p.alerta.desde) ?? 0) >= 7) };
}
/** Tope por silla (D-07): 12 proyectos por account, 16 por trafficker y CRM. */
const TOPE_SILLA = { account: 12, trafficker: 16, crm: 16 };
const cargaTxt = p => (p.sobre_capacidad || []).map(x => { const k = txtCap(x); const n = p.cartera?.[k]; return n !== undefined && TOPE_SILLA[k] ? `${n} de ${TOPE_SILLA[k]} como ${k === 'crm' ? 'CRM' : k}` : k; }).join(' · ');
def('personas_alerta', ['personas_m20/equipo'], (ctx, D) => {
  const e = equipo(D); const { en, sin } = alertaPersonas(e);
  return {
    valor: sin.length, unidad: `sin plan todavía · ${en.length} en alerta y ${en.length - sin.length} con plan`, estado: sin.length ? 'rojo' : en.length ? 'ambar' : 'verde',
    motivo: 'Lo mismo que la pestaña «En alerta» de Personas. Con su motivo y desde cuándo; si a los 7 días no tienen conversación y plan, suben al número que manda.',
    filas: en.slice().sort((a, b) => (planDe(a) ? 1 : 0) - (planDe(b) ? 1 : 0)).map(p => ({ texto: `${p.alias} · ${(p.alerta.motivos || []).join(' · ')}`, extra: `desde ${diaCorto(p.alerta.desde)} · ${planDe(p) ? 'con plan' : 'sin plan'}`, estado: planDe(p) ? 'ambar' : 'rojo', icono: 'alert', href: hrefPersona(ctx, p.persona_id, { plan: !planDe(p) }) })),
    vacio: { titulo: 'Nadie en alerta', tono: 'celebrar' }, frescura: fresco('Personas en alerta', e), medible: 'hoy',
    primero: sin.slice().sort((a, b) => String(a.alerta.desde).localeCompare(String(b.alerta.desde))).slice(0, 2)
      .map(p => ({ peso: 2.8, icono: 'alert', motivo: `${p.alias} en alerta sin plan`, detalle: `${(p.alerta.motivos || []).join(' · ')} · desde ${diaCorto(p.alerta.desde)}. Conversación y plan antes de 7 días.`, ruta: sinAlmohadilla(hrefPersona(ctx, p.persona_id, { plan: true })), clave: `alerta:${p.persona_id}`, grupo: `rrhh-persona:${p.persona_id}` })),
  };
});
def('carga_personas', ['personas_m20/equipo'], (ctx, D) => {
  // V2 (M5): solo quien PASA su tope, con su cifra («21 de 16 como trafficker»); los que están cerca, aparte y en una línea
  const e = equipo(D);
  const sobre = (e.personas || []).filter(p => (p.sobre_capacidad || []).length);
  const cerca = (e.personas || []).filter(p => !(p.sobre_capacidad || []).length && (p.cerca_capacidad || []).length);
  return {
    valor: sobre.length, unidad: 'por encima de su capacidad', estado: sobre.length ? 'rojo' : cerca.length ? 'ambar' : 'verde',
    motivo: `12 proyectos por account, 16 por trafficker y CRM, 128 h al mes (D-07, D-25).${cerca.length ? ` Cerca del tope, sin pasarlo: ${cerca.map(p => p.alias).join(', ')} (por eso Contratación no pide más accounts).` : ''}`,
    filas: sobre.map(p => ({ texto: p.alias, extra: cargaTxt(p), estado: 'rojo', icono: 'medidor', href: hrefPersona(ctx, p.persona_id) })),
    vacio: { titulo: 'Nadie por encima de su capacidad', tono: 'celebrar' }, frescura: fresco('Asignaciones + horas', e), medible: 'hoy',
    primero: sobre.slice(0, 1).map(p => ({ peso: 2.5, icono: 'medidor', motivo: `${p.alias} por encima de su capacidad`, detalle: cargaTxt(p), ruta: sinAlmohadilla(hrefPersona(ctx, p.persona_id)), clave: `carga:${p.persona_id}` })),
  };
});
def('imputa_ayer', ['personas_m20/equipo', 'horas/horas'], (ctx, D) => {
  const e = equipo(D); const l = (e.personas || []).filter(p => p.imputa && p.estado !== 'baja');
  const no = l.filter(p => n0(p.horas?.ayer) === 0);
  return {
    valor: no.length, unidad: `de ${l.length} sin imputar ayer`, estado: no.length > 3 ? 'rojo' : no.length ? 'ambar' : 'verde',
    motivo: 'Como aviso, nunca como nota (D-27). El recordatorio va solo a quien no imputó.',
    filas: no.map(p => ({ texto: p.alias, extra: `${(p.horas?.dias_sin_imputar_5 || []).length} de los últimos 5 días sin imputar`, estado: (p.horas?.dias_sin_imputar_5 || []).length >= 3 ? 'rojo' : 'ambar', icono: 'clock', href: '#/horas' })),
    // V2 (M5): la misma hora de «ClickUp · horas» que el bloque de registros por revisar (el fichero de Horas)
    frescura: fresco('ClickUp · horas', D.opcional('horas/horas') || e._meta?.corte_horas || e), medible: 'medias', medibleDetalle: 'Horas incompletas: solo aviso',
  };
});
def('ausencias', ['personas_m20/equipo'], (ctx, D) => {
  const e = equipo(D); const l = e.ausencias || [];
  return {
    valor: l.length, unidad: 'ausencias registradas', estado: '',
    motivo: 'Hoy y las próximas 2 semanas, con su suplente. Cada ausencia crea una suplencia que caduca sola.',
    filas: l.map(a => ({ texto: `${alias(ctx, a.persona_id)} · ${diaCorto(a.desde)} → ${diaCorto(a.hasta)}`, extra: a.suplente ? `suplente ${alias(ctx, a.suplente)}` : 'sin suplente', estado: a.suplente ? 'verde' : 'rojo', icono: 'cal' })),
    vacio: { titulo: 'Ninguna ausencia registrada', texto: 'No existe aún una tabla de ausencias fuera de la app: se apuntan en Personas.', quien: 'Cecilia' },
    frescura: fresco('Personas', e), medible: 'medias', medibleDetalle: 'Solo las que se apuntan en la app',
  };
});
def('horas_raras', ['horas/horas'], (ctx, D) => {
  const hr = D.dato('horas/horas'); const l = (hr.raras || []).slice().sort((a, b) => String(b.fecha).localeCompare(String(a.fecha)));
  return {
    valor: l.length, unidad: 'registros por revisar', estado: l.length ? 'ambar' : 'verde',
    motivo: 'Más de 8 h en un registro, solapes y horas sin tarea. Se validan con Correcto, Hablar o Error.',
    filas: l.map(x => ({ texto: `${nombre(ctx, x.persona_id)} · ${x.tipo}`, extra: `${diaCorto(x.fecha)} · ${x.motivo}`, estado: 'ambar', icono: 'clock', href: '#/horas', abrir: x.url ? { href: x.url, texto: 'ClickUp' } : null })),
    frescura: fresco('ClickUp · horas', hr), medible: 'hoy',
  };
});
def('contratacion', ['personas_m20/contratacion'], (ctx, D) => {
  const c = D.dato('personas_m20/contratacion'); const l = c.vacantes || [];
  return {
    valor: suma(l, v => v.plazas), unidad: `plazas en ${plural(l.length, 'vacante')}`, estado: '',
    motivo: c.resumen?.texto || 'Plan de fichajes del trimestre.',
    filas: l.map(v => ({ texto: `${v.puesto} · ${plural(v.plazas, 'plaza')} (oleada ${v.oleada})`, extra: `${v.fase || '—'} · entra ${diaCorto(v.entra)}`, estado: v.candidatos ? 'verde' : 'ambar', icono: 'users', href: '#/ajustes' })),
    frescura: fresco('Plan de fichajes Q4', c._meta?.generado), medible: 'medias', medibleDetalle: 'Los candidatos los rellena Cecilia el lunes',
  };
});
def('uno_a_uno', ['personas_m20/equipo'], (ctx, D) => {
  const e = equipo(D); const r = e._meta?.ronda_jefas || {};
  return {
    valor: diaCorto(r.proxima), unidad: 'próxima ronda con las jefas', estado: '',
    motivo: `Cada ${r.cada_dias || 14} días. Registradas: ${r.registradas ?? 0}.`,
    filas: [], vacio: { titulo: 'Los 1:1 todavía no se apuntan en ninguna herramienta', texto: 'Se anotan en Personas (1:1 y plan); desde ahí salen aquí.', quien: 'Cecilia' },
    frescura: fresco('Personas', e), medible: 'no', medibleDetalle: 'Hasta que se apunten en la app',
  };
});

// ------------------------------------------------------------- Account
/** La cosa concreta de una alarma: su correo más viejo, su alta, sus revisiones o su pestaña de la ficha. */
const PESTANA_ALARMA = { 'Sin responder': 'comunicacion', 'Sin correo esta semana': 'comunicacion', 'Sin reunión en septiembre': 'comunicacion',
  'Revisión del account >48 h': 'trabajo', 'Bloqueo sin resolver': 'trabajo', 'Bloqueo callado más de 5 días': 'trabajo', 'Trabajo no planificado': 'trabajo', 'Informes de septiembre pendientes': 'trabajo',
  'Gasto sin leads': 'resultados', 'Coste por lead alto': 'resultados' };
function hrefAlarma(ctx, D, a) {
  if (a._ticket) return ir(ctx, 'bandeja', a._ticket, hrefCliente(ctx, a.cliente_id, 'comunicacion'));
  const bj = D.opcional('bandeja/bandeja');
  if (a.tipo === 'Sin responder' && bj) {
    const c = (bj.correos || []).filter(x => x.cliente_id === a.cliente_id && !x.auto).sort((x, y) => y.horas - x.horas)[0];
    if (c) return ir(ctx, 'bandeja', c.id);
  }
  if (/^Cliente nuevo/.test(a.tipo)) return ir(ctx, 'clientes-nuevos', a.cliente_id);
  return hrefCliente(ctx, a.cliente_id, PESTANA_ALARMA[a.tipo] || 'resumen');
}
def('primero_cartera', ['bandeja/bandeja', 'bandeja/por_cliente'], (ctx, D) => {
  // Correos sin contestar: de la Bandeja (bandeja/por_cliente, días laborables), no de la alarma de las 07:00.
  const correos = correosCliente(ctx, D);
  const deCorreo = (correos || []).filter(x => ctx.carteraIds.has(x.cliente_id) && x.estado !== 'verde')
    .map(x => ({ id: `correos:${x.cliente_id}`, cliente_id: x.cliente_id, cliente: x.nombre, tipo: x.texto, texto: x.detalle, accion: x.detalle, gravedad: x.estado, _ticket: x.ticket, enlace: x.mas_antiguo?.url || null }));
  const l = [...ctx.datos.alarmas.filter(a => a.ambito === 'cliente' && a.texto !== undefined && ctx.carteraIds.has(a.cliente_id) && !(correos && a.tipo === SIN_RESPONDER)), ...deCorreo]
    .sort((a, b) => (a.gravedad === b.gravedad ? 0 : a.gravedad === 'rojo' ? -1 : 1));
  const rojas = l.filter(a => a.gravedad === 'rojo');
  return {
    valor: rojas.length, unidad: `rojas · ${plural(l.length - rojas.length, 'ámbar', 'ámbar')}`, estado: rojas.length ? 'rojo' : l.length ? 'ambar' : (ctx.carteraIds.size ? 'verde' : 'gris'),
    motivo: ctx.carteraIds.size ? 'Lo de tus clientes, lo más grave arriba, con lo que toca hacer. Cada fila abre la cosa concreta.' : 'Aún no tienes clientes asignados: las asignaciones las mantiene Mili.',
    filas: l.map(a => ({ texto: `${a.cliente} · ${a.tipo}`, extra: a.accion || a.texto, estado: a.gravedad, icono: 'fire', href: hrefAlarma(ctx, D, a), abrir: a.enlace ? { href: a.enlace, texto: 'la prueba' } : null })),
    vacio: { titulo: 'Nada en rojo en tu cartera', texto: 'Ninguno de tus clientes tiene alarmas abiertas hoy.', tono: 'celebrar' },
    frescura: fresco('Alarmas del panel de operaciones', ctx.datos.meta?.construido), medible: 'hoy',
    primero: rojas.map(a => ({ peso: 3, icono: 'fire', motivo: `${a.cliente} · ${a.tipo}`, detalle: a.texto, ruta: sinAlmohadilla(hrefAlarma(ctx, D, a)), clave: `alarma:${a.id}`, cliente_id: a.cliente_id, grupo: a.tipo === SIN_RESPONDER || a._ticket ? `correo-cli:${a.cliente_id}` : null })),
  };
});
def('clientes_tarjetas', ['verdad/clientes'], (ctx, D) => {
  // R12 (C1): salud, estado y motivo de la verdad única: lo mismo que dice la ficha de cada cliente
  const peso = { critico: 0, atencion: 1, bien: 2 };
  const l = ctx.clientes.filter(c => c.enCartera).map(c => { const v = verdad(ctx, c.id) || {}; return { ...c, salud: Number.isFinite(v.salud) && v.salud >= 0 ? v.salud : null, grav: v.gravedad, mot: (v.motivos || [])[0] }; })
    .sort((a, b) => (peso[a.grav] ?? 3) - (peso[b.grav] ?? 3));
  const conSalud = l.filter(c => typeof c.salud === 'number');
  const crit = l.filter(c => c.grav === 'critico').length;
  return {
    valor: l.length, unidad: `clientes · ${conSalud.length} con índice registrado · ${crit} ${crit === 1 ? 'crítico' : 'críticos'}`, estado: crit ? 'rojo' : l.some(c => c.grav === 'atencion') ? 'ambar' : l.length && l.every(c => c.grav === 'bien') ? 'verde' : 'gris',
    motivo: 'Estado registrado: lo crítico arriba. El índice registrado es provisional; no acredita desempeño, cobertura ni cumplimiento.',
    filas: l.map(c => ({ texto: `${c.nombre} · ${GRAV_TXT[c.grav] || 'sin estado'}${typeof c.salud === 'number' ? ` · índice registrado ${c.salud}` : ''}`, extra: c.mot || '', estado: GRAV_EST[c.grav] || 'gris', icono: 'cli', href: hrefCliente(ctx, c.id) })),
    vacio: { titulo: 'Sin clientes asignados', texto: 'Cuando Mili te asigne clientes en Ajustes, salen aquí.', quien: 'Mili' },
    frescura: fresco('Verdad única de clientes', D.opcional('verdad/clientes')), medible: 'medias', medibleDetalle: 'Índice provisional; el color procede del estado registrado, no del índice',
  };
});
/** R12 (A4): los correos y llamadas pendientes con la MISMA regla que la pantalla Bandeja (lo que el servidor manda a
 *  la persona, sin automáticos, sin los viejos y sin lo que ya está en la cola de la Bandeja). Un solo contador. */
const SACAN_DE_BANDEJA = new Set(['responder', 'cerrar', 'no_aplica', 'despachado', 'llamada_devuelta', 'esperando_cliente']);
function bandejaComoPantalla(ctx, D, extra) {
  const bj = D.dato('bandeja/bandeja');
  // Solo lo que SACA el correo en la Bandeja (bandeja.js → TERMINALES + «esperando al cliente»): una nota, una tarea,
  // un aviso o una asignación no lo despachan.
  const hechos = new Set([...(extra?.acciones || []), ...(extra?.accionesBandeja || [])].filter(a => a.modulo === 'bandeja' && SACAN_DE_BANDEJA.has(a.tipo)).map(a => String(a.objeto)));
  const vivo = x => !x.auto && !x.viejo && !hechos.has(String(x.numero ?? x.id));
  const c = (bj.correos || []).filter(vivo);
  const ll = (bj.llamadas || []).filter(x => !x.viejo && !hechos.has(String(x.numero ?? x.id)));
  return { bj, c, ll, rojo: c.filter(x => x.gravedad === 'rojo'), ambar: c.filter(x => x.gravedad === 'ambar') };
}
/** Frescura como la pantalla Bandeja: Desk y Zadarma por separado, cada una con su hora. */
const fresBandeja = bj => ['desk', 'zadarma'].map(k => { const f = bj.fuentes?.[k]; const e = f ? edadH(f.hora) : null; return f ? { fuente: k === 'desk' ? 'Desk' : 'Zadarma', edad_h: e === null ? null : Math.round(e * 10) / 10, estado: f.estado === 'bien' ? 'ok' : 'viejo' } : { fuente: k === 'desk' ? 'Desk' : 'Zadarma', estado: 'sin datos' }; });
/** Clientes sin la reunión del mes pasado: la regla de Reuniones con la verdad única («Reuniones» y «Tu cumplimiento»). */
function reunionesCartera(ctx, D, al = 'mio') {
  const r = D.dato('reuniones/reuniones');
  const metodo = D.opcional('metodo/sugerencias');
  const { historicos, seguimiento } = separarCadencias(r.clientes || [], metodo,ambitoCadencia307(ctx));
  const l = historicos.filter(c => (al === 'todo' || c.account_id === yo(ctx) || ctx.carteraIds.has(c.cliente_id)) && !['exento', 'no_aplica'].includes(c.estado));
  const actuales = seguimiento.filter(c => al === 'todo' || ctx.carteraIds.has(c.cliente_id) || c.responsable_id === yo(ctx));
  const sinR = c => { const v = verdad(ctx, c.cliente_id); return v && v.sin_reunion_mes_pasado !== undefined ? v.sin_reunion_mes_pasado : c.estado === 'sin_reunion'; };
  return { r, l, metodo, actuales, sinR, sin: l.filter(sinR) };
}
def('bandeja_mia', ['bandeja/bandeja'], (ctx, D, b, extra) => {
  const { bj, c, ll, rojo, ambar } = bandejaComoPantalla(ctx, D, extra);
  const filas = [...ll.map(x => ({ texto: `Llamada sin devolver · ${x.cliente || 'desconocido'}`, extra: `${x.llamadas} llamadas · ${cuandoTxt(x.ultima)}`, estado: x.gravedad, icono: 'phone', href: ir(ctx, 'bandeja', x.id) })),
    ...c.slice().sort((a, b) => ordenEstado(a, b) || b.horas - a.horas).map(x => ({ texto: `${x.cliente || 'Sin cliente'} · «${x.asunto}»`, extra: `${x.queja ? 'queja · ' : ''}${esperaTxt(x)}`, estado: x.gravedad, icono: x.queja ? 'megafono' : 'mail', href: ir(ctx, 'bandeja', x.id), abrir: x.url ? { href: x.url, texto: 'Desk' } : null }))];
  return {
    valor: rojo.length, unidad: `correos de más de 48 h · ${ambar.length} entre 24 y 48 h · ${plural(c.length, 'correo')} sin contestar`, estado: rojo.length ? 'rojo' : ambar.length ? 'ambar' : 'verde',
    motivo: `Las mismas cifras que tu Bandeja: correos de Desk con cuenta atrás y llamadas de Zadarma sin devolver. WhatsApp uno a uno: ${bj.whatsapp?.estado === 'sin_conectar' ? 'llega cuando se conecte WhatsApp Business, no antes del 16 de octubre' : 'en la Bandeja'}.`,
    filas, vacio: { titulo: 'Bandeja a cero', tono: 'celebrar' }, frescura: fresBandeja(bj), medible: 'hoy',
    primero: c.filter(x => x.gravedad === 'rojo').sort((a, b) => (b.queja ? 1 : 0) - (a.queja ? 1 : 0) || b.horas - a.horas).slice(0, 2)
      .map(x => ({ peso: x.queja ? 3.6 : 3.1, icono: x.queja ? 'megafono' : 'mail', motivo: x.cliente ? `${x.cliente} · correo sin contestar` : `Correo sin contestar · «${x.asunto}»`, detalle: `${x.cliente ? `«${x.asunto}» · ` : 'Sin cliente reconocido · '}${esperaTxt(x)}`, ruta: `bandeja/${encodeURIComponent(x.id)}`, clave: `correo:${x.id}`, cliente_id: x.cliente_id, grupo: x.cliente_id ? `correo-cli:${x.cliente_id}` : null })),
  };
});
def('reuniones_ciclo', ['reuniones/reuniones', 'metodo/sugerencias'], (ctx, D, b) => {
  const { r, l, metodo, actuales, sinR, sin } = reunionesCartera(ctx, D, alcance(b, 'mio'));
  const sinProx = l.filter(c => !c.proxima);
  const inventario = l.length + actuales.length;
  const cadenciaConfirmada = c => /^\d{4}-\d{2}-\d{2}$/.test(c.ultima_confirmada || '') && c.ultima_confirmada <= ctx.hoy && /^\d{4}-\d{2}-\d{2}$/.test(c.proxima_revision || '') && c.proxima_revision >= ctx.hoy;
  return {
    valor: inventario ? sin.length : null, unidad: `sin registro mensual del periodo ${/^\d{4}-\d{2}$/.test(r._meta?.mes_pasado || '') ? r._meta.mes_pasado : 'no confirmado'} (registro histórico)`, estado: actuales.some(c => estadoCadencia(c) === 'ambar') ? 'ambar' : actuales.some(c => estadoCadencia(c) === 'gris' || !cadenciaConfirmada(c)) || l.length > 0 || !(l.length + actuales.length) || !metodo || metodo.hoy !== ctx.hoy || !r._meta?.generado ? 'gris' : 'verde',
    motivo: `Registros mensuales de otras cuentas: ${plural(sinProx.length, 'cliente')} sin próxima fecha; fuentes parciales, no incumplimiento. ${actuales.length} cuentas de seguimiento15d con trafficker, separadas. ${metodo ? '' : 'Overlay no disponible: confirmar cadencia vigente.'} ${!inventario ? 'Sin inventario suficiente: no se acredita cumplimiento.' : l.length ? 'Registros mensuales históricos: no acreditan una obligación vigente.' : ''}`,
    filas: [...actuales.map(c => ({ texto: c.cliente || nomCli(ctx, c.cliente_id) || c.cliente_id, extra: `Seguimiento cada15d con trafficker · ${textoCadencia(c)}`, estado: estadoCadencia(c), icono: 'video', href: '#/prioridades-cliente' })), ...[...sin, ...sinProx.filter(c => !sin.includes(c))].map(c => ({ texto: c.cliente, extra: sinR(c) ? `sin registro · última ${c.ultima ? diaCorto(c.ultima) : 'sin dato'}` : `sin próxima fecha · última ${c.ultima ? diaCorto(c.ultima) : '—'}`, estado: 'gris', icono: 'video', href: hrefCliente(ctx, c.cliente_id, 'comunicacion') }))],
    vacio: { titulo: 'Sin casos en los registros disponibles', texto: 'No acredita cobertura completa ni cumplimiento de reunión.' }, frescura: fresco('Zoom + CRM + Fathom', r), medible: 'hoy',
  };
});
def('trabajo_account', ['produccion/produccion', 'informes/informes'], (ctx, D, b, extra) => {
  // V2 (A5): «revisiones del account» = la definición única de Producción (revisionesDelAccount, vía controlPersona): las mismas
  // cifras en «Trabajo», «Tu cumplimiento», el mapa de Mili e Incidencias. «Lo mío» cuenta otra cosa y la nombra distinto:
  // las piezas que esperan tu visto bueno de los últimos 30 días (Producción › Por revisar).
  const p = D.dato('produccion/produccion');
  const R = controlPersona(ctx, D, yo(ctx), extra).revisa || { filas: [], total: 0, mas48: 0 };
  const rev = R.filas.slice();
  const inf = D.opcional('informes/informes');
  const ciclo = inf?._meta?.ciclo || {};
  const pend = (inf?.filas || []).filter(x => (x.account_id === yo(ctx) || ctx.carteraIds.has(x.cliente_id)) && x.mes === ciclo.mes && ['en_curso', 'sin_tarea', 'pendiente'].includes(x.estado));
  const proy = (p.proyectos || []).filter(x => x.account_id === yo(ctx) && n0(x.bloqueo_max) > 2);
  const filas = [
    ...(pend.length ? [{ texto: `${plural(pend.length, 'informe')} de ${MESES[Number(ciclo.mes.slice(5)) - 1]} sin enviar`, extra: `límite: ${diaCorto(ciclo.limite)}`, estado: n0(ciclo.dias_para_limite) <= 1 ? 'rojo' : 'ambar', icono: 'doc', href: '#/informes-mensuales' }] : []),
    ...proy.map(x => ({ texto: `${x.cliente} · bloqueo del cliente de ${fmt.num(x.bloqueo_max)} días`, estado: x.bloqueo_max > 5 ? 'rojo' : 'ambar', icono: 'candado', href: hrefCliente(ctx, x.cliente_id, 'trabajo') || '#/produccion' })),
    ...rev.sort((a, b) => n0(b.dias) - n0(a.dias)).map(x => ({ texto: `Revisar · ${x.tarea}`, extra: `${nomCli(ctx, x.cliente_id) || 'sin cliente'} · ${plural(Math.round(n0(x.dias)), 'día')} esperando${(x.asignados || []).length ? ` · de ${x.asignados.join(', ')}` : ''}`, estado: 'rojo', icono: 'capas', href: ir(ctx, 'produccion', x.id, x.url), abrir: x.url ? { href: x.url, texto: 'ClickUp' } : null })),
  ];
  return {
    valor: rev.length, unidad: `de tus ${plural(R.total, 'revisión del account', 'revisiones del account')} llevan más de 48 h · ${plural(pend.length, 'informe')} pendiente${pend.length === 1 ? '' : 's'}`, estado: rev.length || proy.some(x => x.bloqueo_max > 5) ? 'rojo' : pend.length ? 'ambar' : 'verde',
    motivo: 'Revisiones del account de más de 48 h (todas, como «Revisiones 48 h» de Producción; las piezas de los últimos 30 días están en «Lo mío»), bloqueos del cliente de más de 2 días e informe mensual pendiente.',
    filas, vacio: { titulo: 'Trabajo al día', tono: 'celebrar' }, frescura: fresco('ClickUp + Desk', p), medible: 'hoy',
  };
});
def('cumplimiento', ['incidencias/incidencias', 'bandeja/bandeja', 'produccion/produccion', 'reuniones/reuniones', 'metodo/sugerencias'], (ctx, D, b, extra) => {
  const inc = D.dato('incidencias/incidencias');
  const c = (inc.control || []).find(x => x.persona_id === yo(ctx));
  if (!c) return { valor: null, unidad: '', estado: 'gris', motivo: 'Todavía no hay mapa de control para ti.', filas: [], vacio: { titulo: 'Sin datos de control', texto: 'El mapa de control sale de Incidencias (M14) para quien lleva clientes.' }, frescura: fresco('Incidencias', inc), medible: 'medias' };
  // R12 (A4): contesta, revisa y se reúne con la MISMA regla (y la misma cifra) que Bandeja, Trabajo y Reuniones de esta pantalla.
  // V2: contesta y revisa con controlPersona (bandejaComoPantalla + revisionesDelAccount), la misma vara que el mapa de Mili e Incidencias
  const cp = controlPersona(ctx, D, yo(ctx), extra);
  const ru = D.opcional('reuniones/reuniones') ? reunionesCartera(ctx, D) : null;
  const contesta = cp.contesta || { mas48: c.contesta?.mas48, total: c.contesta?.correos };
  const revisa = cp.revisa || { mas48: c.revisa?.mas48, total: c.revisa?.total };
  const sinReunion = ru ? ru.sin.length : c.reune?.sin_reunion;
  const filas = [
    { texto: 'Imputa', extra: `ayer ${fmt.num(c.imputa?.ayer, 1)} h · semana ${fmt.pct(c.imputa?.pct_sem)}`, estado: n0(c.imputa?.ayer) ? 'verde' : 'ambar', icono: 'clock' },
    { texto: 'Contesta', extra: `${fmt.num(contesta.mas48)} de ${plural(n0(contesta.total), 'correo')} sin contestar llevan más de 48 h (como tu Bandeja)`, estado: n0(contesta.mas48) ? 'rojo' : 'verde', icono: 'mail' },
    { texto: 'Revisa', extra: `${fmt.num(revisa.mas48)} de tus ${plural(n0(revisa.total), 'revisión del account', 'revisiones del account')} llevan más de 48 h (como Producción)`, estado: n0(revisa.mas48) > 5 ? 'rojo' : n0(revisa.mas48) ? 'ambar' : 'verde', icono: 'capas' },
    { texto: 'Coordina registros y escribe', extra: `${plural(n0(sinReunion), 'cliente')} sin registro mensual antiguo (fuentes parciales; no incumplimiento) · ${ru?.actuales?.length || 0} cuentas15d con trafficker separadas · ${fmt.num(c.reune?.sin_correo_sem)} sin correo esta semana`, estado: n0(sinReunion) ? 'rojo' : n0(c.reune?.sin_correo_sem) ? 'ambar' : 'verde', icono: 'video' },
    { texto: 'Llama', extra: `${fmt.num(c.llama?.sem)} llamadas esta semana`, estado: 'gris', icono: 'phone' },
  ];
  const rojos = filas.filter(f => f.estado === 'rojo').length;
  return {
    valor: `${filas.filter(f => f.estado === 'verde').length}/${filas.length - 1}`, unidad: 'reglas en verde', estado: rojos ? 'rojo' : 'verde',
    motivo: 'Lo que mira Mili cada día. La nota 0-100 todavía no tiene fórmula: aquí, regla a regla.',
    filas, frescura: fresco('Incidencias · mapa de control', inc), medible: 'medias', medibleDetalle: 'Sin nota 0-100 todavía',
  };
});

// ------------------------------------------------------------- Publicidad (trafficker y Valeria)
function cuentas(ctx, D, b, def2) {
  const original = D.dato('captacion/captacion');
  const cap = {...original,clientes:clientesDia314(ctx,original.clientes).map(c=>normalizarPaid(c,original,ctx.hoy||hoyISO()))};
  const al = alcance(b, def2);
  // R12 (B-A04): «mis cuentas» = la cartera de trafficker de las ASIGNACIONES (la misma de Personas y Dinero por cliente)
  // V2 (B-A3): con la cifra única de Captación (carteras_publicidad[persona]: principal + apoyo), la misma de «Mis cuentas»
  const cp = cap.carteras_publicidad?.[yo(ctx)];
  const mia = cp ? new Set([...(cp.principal || []), ...(cp.apoyo_ids || [])]) : silla(ctx, 'trafficker');
  const esMia = c => (mia ? mia.has(c.cliente_id) : c.equipo?.trafficker === yo(ctx) || (c.equipo?.trafficker_otros || []).includes(yo(ctx)));
  return { cap, l: (cap.clientes || []).filter(c => al === 'todo' || esMia(c)) };
}
const sev = s => (s === 'critico' ? 'rojo' : s === 'atencion' ? 'ambar' : s === 'ok' ? 'verde' : 'gris');
/** Tiendas online sin leads de despacho (la misma lista que Captación: captacion.js → TIENDAS_ONLINE). */
const TIENDAS_ONLINE = new Set(['kiosko-box']);
/** R12 (B-A02): si el servidor tapó un importe del texto («[importe]»), la frase va sin él y la cifra, aparte, de los
 *  campos que la persona sí recibe (coste por lead de 7 días y techo usado). Nunca un texto con hueco. */
function motivoCuenta(c) {
  const m = (c.motivos || [])[0] || {};
  const crudo = m.gasto_texto || m.texto || '';
  if (!crudo.includes('[importe]')) return { texto: crudo, cifra: null };
  const cpl = c.cpl?.['7d'], techo = c.objetivo?.cpl_usado;
  const cifra = cpl !== undefined && cpl !== null ? `${eurC(cpl)} por lead${techo ? ` · techo ${eurG(techo)}` : ''}` : null;
  return { texto: sinImporte(crudo), cifra };
}
def('cuentas_problema', ['captacion/captacion'], (ctx, D, b) => {
  // V2 (A1 / B-A2 / B-A3): «rojo» = cliente en CRÍTICO de la verdad única con cuenta de Meta: las cifras únicas de Captación
  // (captacion.json → criticos_casa para toda la casa; carteras_publicidad[persona].criticos para su cartera). La alarma de la
  // cuenta de Meta con el cliente en atención (Akua) es «publicidad a vigilar», aparte y en ámbar: nunca «crítica».
  const { cap, l } = cuentas(ctx, D, b, 'mio');
  const todo = alcance(b, 'mio') !== 'mio';
  const cp = cap.carteras_publicidad?.[yo(ctx)];
  const ids = new Set(todo ? (cap.criticos_casa || []) : (cp ? [...(cp.con_meta_ids || cp.principal || [])].filter(id => verdad(ctx, id)?.gravedad === 'critico') : l.filter(c => verdad(ctx, c.cliente_id)?.gravedad === 'critico').map(c => c.cliente_id)));
  const porId = new Map((cap.clientes || []).map(c => [c.cliente_id, c]));
  const crit = [...ids].filter(id=>porId.has(id)).map(id=>porId.get(id));
  const urgentes = l.filter(c => c.severidad === 'critico' && !ids.has(c.cliente_id));
  const mia = !todo ? silla(ctx, 'trafficker') : null;
  const motivoMeta = c => sinImporte((c.motivos || [])[0]?.texto) || '';
  const fila = (c, est) => { const m = motivoMeta(c); const v = verdad(ctx, c.cliente_id); return { texto: `${c.nombre} · ${est === 'rojo' ? (v?.motivos || [])[0] || 'cliente crítico' : m || 'publicidad a vigilar'}`,
    extra: [est === 'rojo' ? (m ? `Meta: ${m}` : null) : GRAV_CLI[v?.gravedad] || null, motivoCuenta(c).cifra, c.equipo?.trafficker ? nombre(ctx, c.equipo.trafficker) : null].filter(Boolean).join(' · '),
    estado: est, icono: est === 'rojo' ? 'fire' : 'alert', href: hrefCap(ctx, c.cliente_id) }; };
  return {
    valor: crit.length, unidad: `${crit.length === 1 ? 'cliente crítico' : 'clientes críticos'} con cuenta de Meta${urgentes.length ? ` · ${plural(urgentes.length, 'cuenta', 'cuentas')} con publicidad a vigilar` : ''}${cp && !todo ? ` · tu cartera: ${plural(cp.cartera, 'cliente')}${cp.apoyo ? ` (+${cp.apoyo} de apoyo)` : ''}` : mia ? ` · tu cartera: ${plural(mia.size, 'cuenta')}` : ''}`,
    estado: crit.length ? 'rojo' : urgentes.length ? 'ambar' : 'verde',
    motivo: `${todo ? 'Clientes críticos (verdad única) con cuenta de Meta en toda la casa: la misma cifra que «Por trafficker» y que Captación.' : 'Tus clientes críticos (verdad única) con cuenta de Meta: la misma cifra que «Mis cuentas» de Captación.'} Aparte, la publicidad a vigilar: tarjeta o impago, anuncios rechazados, gasto 0, píxel caído o coste fuera del techo con el cliente a vigilar.`,
    filas: [...crit.map(c => fila(c, 'rojo')), ...urgentes.map(c => fila(c, 'ambar'))],
    vacio: { titulo: 'Ningún cliente crítico ni publicidad a vigilar', tono: 'celebrar' }, frescura: fresco('Meta + verdad única', cap.captacion_generado || cap), medible: 'hoy',
    primero: [...crit.slice(0, 2).map(c => ({ peso: 3.2, icono: 'fire', motivo: `${c.nombre} · cliente crítico`, detalle: [(verdad(ctx, c.cliente_id)?.motivos || [])[0], motivoMeta(c) ? `Meta: ${motivoMeta(c)}` : null].filter(Boolean).join(' · '), ruta: sinAlmohadilla(hrefCap(ctx, c.cliente_id)), clave: `cuenta:${c.cliente_id}`, cliente_id: c.cliente_id, grupo: `critico:${c.cliente_id}` })),
      ...urgentes.slice(0, 1).map(c => { const m = motivoCuenta(c); return { peso: 2.6, icono: 'alert', motivo: `${c.nombre} · publicidad a vigilar`, detalle: [GRAV_CLI[verdad(ctx, c.cliente_id)?.gravedad], m.texto, m.cifra].filter(Boolean).join(' · '), ruta: sinAlmohadilla(hrefCap(ctx, c.cliente_id)), clave: `cuenta:${c.cliente_id}`, cliente_id: c.cliente_id }; })],
  };
});
def('tabla_cuentas', ['captacion/captacion'], (ctx, D, b) => {
  const { cap, l } = cuentas(ctx, D, b, 'mio');
  const a = l.filter(c => c.meta_activa).sort((x, y) => ordenEstado({ estado: sev(x.severidad) }, { estado: sev(y.severidad) }));
  return {
    valor: a.length, unidad: 'cuentas con Meta encendida', estado: a.some(c=>c.severidad==='critico')?'rojo':a.some(c=>c.severidad==='atencion')?'ambar':'gris',
    motivo: 'Resultados observados y referencias anteriores separados. El CPL requiere unidad, ventana y objetivo propios confirmados.',
    filas: a.map(c => {const m=resultadosFilaDia314(c,cap,ctx.hoy||hoyISO());return { texto:c.nombre,extra:m.extra,estado:m.estado,icono:'res',href:hrefCap(ctx,c.cliente_id)};}),
    frescura: fresco('Meta', cap.captacion_generado || cap), medible: 'hoy',
  };
});
def('anomalias', ['captacion/captacion'], (ctx, D, b) => {
  const { cap, l } = cuentas(ctx, D, b, 'mio');
  const an = [];
  for (const c of l) for (const m of c.motivos || []) if (/subió|bajó|cayó|frente a/i.test(m.texto)) an.push({ c, m });
  an.sort((x, y) => n0(y.c.gasto?.['7d']) - n0(x.c.gasto?.['7d']));
  return {
    valor: an.length, unidad: 'señales anteriores por contrastar', estado:'gris',
    motivo: 'Frente a su media de 7 días, ordenados por dinero en juego.',
    filas: an.map(x => ({ texto: `${x.c.nombre} · ${x.m.texto}`, extra: nombre(ctx, x.c.equipo?.trafficker), estado:'gris',icono:'sube',href:hrefCap(ctx,x.c.cliente_id)})),
    vacio: { titulo:'Sin señales en la copia autorizada'},frescura:fresco('Meta',cap.captacion_generado||cap),medible:'medias',
  };
});
def('embudo_cuentas',['captacion/captacion','crm/crm'],(ctx,D,b)=>{
 const {cap,l}=cuentas(ctx,D,b,'mio'),crm=D.opcional('crm/crm'),ids=new Set(l.map(c=>c.cliente_id));
 const subs=clientesDia314(ctx,crm?.subcuentas).filter(s=>ids.has(s.cliente_id)).map(s=>crmDia314(s,crm,ctx.hoy||hoyISO()));
 return {valor:subs.length,unidad:'subcuentas observadas · no conversión',estado:'gris',motivo:'Stock actual de etapas CRM; no es una cohorte de leads Meta, cualificación ni ventas.',
 filas:subs.map(s=>({texto:s.nombre,extra:Object.entries(s.embudo?.funnel||{}).map(([k,v])=>`${k}: ${v===null?'Sin dato':v}`).join(' · ')||'Etapas: Sin dato',estado:'gris',icono:'cap',href:ir(ctx,'salud-crm',s.sub_id)})),frescura:fresco('GoHighLevel',crm),medible:'medias'};
});
def('creatividades', ['produccion/produccion'], (ctx, D) => {
  const p = D.dato('produccion/produccion');
  const a = (p.anuncios || []);
  const malas = a.filter(x => x.estado === 'rojo'), buenas = a.filter(x => x.estado === 'verde' && n0(x.indice) >= 120);
  return {
    valor: malas.length, unidad: `por debajo · ${plural(buenas.length, 'ganadora')}`, estado: malas.length ? 'ambar' : 'verde',
    motivo: `Índice frente a la media de la cuenta (100), sin euros. Cansada = dos señales a la vez (D-39). ${p.anuncios_resumen?.con_autor === 0 ? 'Ningún anuncio lleva aún las iniciales del autor (D-43).' : ''}`,
    filas: [...malas, ...buenas].map(x => ({ texto: `${x.cliente} · ${x.anuncio}`, extra: `índice ${fmt.num(x.indice)} · frecuencia ${fmt.num(x.frecuencia, 1)}`, estado: x.estado, icono: x.estado === 'rojo' ? 'baja' : 'star', href: hrefCap(ctx, x.cliente_id) })),
    frescura: fresco('Meta (anuncios)', p.anuncios_resumen?.hora || p), medible: 'medias', medibleDetalle: 'Sin autor en el nombre del anuncio',
  };
});
def('arranques', ['nuevos/nuevos'], (ctx, D, b) => {
  const n = D.dato('nuevos/nuevos');
  const al = alcance(b, 'mio');
  const l = (n.altas || []).filter(a => a.dia <= 45 && (al === 'todo' || a.trafficker?.id === yo(ctx) || ctx.carteraIds.has(a.cliente_id))).map(a => ({ ...a, arr: arranqueV(ctx, a) }));
  return {
    valor: l.length, unidad: 'arranques en curso', estado: l.some(a => a.arr.sinEncender) ? 'rojo' : '',
    motivo: 'Días 1-4 a 50 €/día y el fondo de RO de hasta 300 € si no hay ganador. El estado de la campaña es el de la verdad única.',
    filas: l.sort((a, b2) => b2.dia - a.dia).map(a => ({ texto: `${a.nombre} · día ${a.dia} · ${a.arr.texto}`, extra: a.meta ? `${plural(n0(a.meta.leads_desde_alta), 'lead')} desde el alta · cuenta publicitaria ${a.meta.estado || 'sin estado'}` : 'sin cuenta de Meta', estado: a.arr.estado, icono: 'rocket', href: ir(ctx, 'clientes-nuevos', a.cliente_id) })),
    vacio: { titulo: 'Sin arranques ahora', tono: 'celebrar' }, frescura: fresco('Sign + Meta', n), medible: 'hoy',
  };
});
/** R12 (B-A04): la cartera de cada trafficker es la de las ASIGNACIONES vigentes (verdad.equipo.trafficker, cualquier
 *  persona de la silla, como «Tu cartera» de Personas y Dinero por cliente). Captación solo pone el estado de cada cuenta. */
function porTrafficker(ctx, D) {
  // V2 (B-A3): las cifras ÚNICAS de Captación (captacion.json → carteras_publicidad, definiciones_publicidad): cartera
  // (principal) + apoyo, con cuenta de Meta, con Meta encendida y en crítico (verdad única). La suma de «en crítico» de las
  // traffickers + las cuentas sin trafficker = criticos_casa (la cifra de «Fuegos»). Sin ese dato, las asignaciones como antes.
  const cap = D.dato('captacion/captacion');
  const capPor = new Map((cap.clientes || []).map(c => [c.cliente_id, c]));
  const g = new Map();
  const CP = cap.carteras_publicidad;
  if (CP && Object.keys(CP).length) {
    const conTr = new Set();
    for (const [t, x] of Object.entries(CP)) {
      [...(x.principal || [])].forEach(id => conTr.add(id));
      g.set(t, { cuentas: n0(x.cartera), apoyo: n0(x.apoyo), conMeta: n0(x.con_meta), activas: n0(x.meta_encendida), criticas: n0(x.criticos), leads: suma(x.principal || [], id => capPor.get(id)?.leads?.['7d']), unica: true });
    }
    const sinTr = (cap.criticos_casa || []).filter(id => !conTr.has(id));
    const sinC = (cap.clientes || []).filter(c => !conTr.has(c.cliente_id) && c.cuenta_meta !== false && verdad(ctx, c.cliente_id)?.equipo && !(verdad(ctx, c.cliente_id).equipo.trafficker || []).length);
    if (sinTr.length || sinC.length) g.set('sin trafficker', { cuentas: sinC.length, apoyo: 0, conMeta: sinC.length, activas: sinC.filter(c => c.meta_activa).length, criticas: sinTr.length, leads: suma(sinC, c => c.leads?.['7d']), unica: true });
    return { cap, g, tope: cap.parametros?.cuentas_trafficker || 16 };
  }
  const sumar = (t, c, principal = true) => {
    const e = g.get(t) || { cuentas: 0, activas: 0, criticas: 0, leads: 0, apoyo: 0 };
    if (principal) e.cuentas += 1; else e.apoyo += 1;
    if (principal && c?.meta_activa) e.activas += 1; if (principal && verdad(ctx, c?.cliente_id)?.gravedad === 'critico') e.criticas += 1; if (principal) e.leads += n0(c?.leads?.['7d']);
    g.set(t, e);
  };
  const ids = new Set([...ctx.clientes.map(c => c.id), ...capPor.keys()]);
  for (const id of ids) {
    const eq = verdad(ctx, id)?.equipo;
    if (!eq) continue;
    const ts = eq.trafficker || [];
    const pri = ts.find(x => x.principal)?.persona_id || ts[0]?.persona_id;
    if (ts.length) ts.forEach(x => sumar(x.persona_id, capPor.get(id) || { cliente_id: id }, x.persona_id === pri)); else if (capPor.get(id)) sumar('sin trafficker', capPor.get(id));
  }
  return { cap, g, tope: cap.parametros?.cuentas_trafficker || 16 };
}
def('tabla_trafficker', ['captacion/captacion'], (ctx, D) => {
  const { cap, g } = porTrafficker(ctx, D);
  const l = [...g.entries()].sort((a, b) => b[1].criticas - a[1].criticas);
  return {
    valor: l.filter(([t]) => t !== 'sin trafficker').length, unidad: 'traffickers', estado: l.some(([, e]) => e.criticas >= 5) ? 'rojo' : l.some(([, e]) => e.criticas >= 3) ? 'ambar' : 'verde',
    motivo: 'Las cifras únicas de Captación: cartera de cada trafficker (como principal) y en qué ayuda, cuántos tienen cuenta de Meta y encendida, y cuántos son críticos (verdad única): bien ≤ 2 · vigilar 3-4 · crítico ≥ 5. La suma de críticos es la de «Fuegos».',
    filas: l.map(([t, e]) => ({ texto: `${t === 'sin trafficker' ? 'Sin trafficker asignado' : nombre(ctx, t)} · ${plural(e.cuentas, 'cliente')}${e.apoyo ? ` (+${e.apoyo} de apoyo)` : ''}${e.conMeta !== undefined ? ` · ${e.conMeta} con cuenta de Meta` : ''} · ${e.activas} con Meta encendida`, extra: `${e.criticas} ${e.criticas === 1 ? 'crítico' : 'críticos'} · ${plural(e.leads, 'lead')} en 7 días`, estado: e.criticas >= 5 ? 'rojo' : e.criticas >= 3 ? 'ambar' : 'verde', icono: 'persona', href: ir(ctx, 'captacion', `~trafficker/${t}`) })),
    frescura: fresco('Meta', cap.captacion_generado || cap), medible: 'hoy',
  };
});
def('carga_trafficker', ['captacion/captacion'], (ctx, D) => {
  const { cap, g, tope } = porTrafficker(ctx, D);
  const l = [...g.entries()].filter(([t]) => t !== 'sin trafficker').sort((a, b) => b[1].cuentas - a[1].cuentas);
  return {
    valor: l.length ? l[0][1].cuentas : 0, unidad: `cuentas la más cargada · tope ${tope}`, estado: l.some(([, e]) => e.cuentas > tope) ? 'rojo' : l.some(([, e]) => e.cuentas >= 14) ? 'ambar' : 'verde',
    motivo: `Tope de ${tope} cuentas por trafficker; aviso desde 14 (D-07). Horas, solo como aviso.`,
    barras: l.map(([t, e]) => ({ etiqueta: nombre(ctx, t), valor: e.cuentas, max: tope })),
    frescura: fresco('Asignaciones + Meta', cap), medible: 'hoy',
  };
});

// ------------------------------------------------------------- CRM (especialista y Yessica)
function subcuentas(ctx, D, b, def2) {
  const original=D.dato('crm/crm');
  const crm={...original,subcuentas:clientesDia314(ctx,original.subcuentas).map(s=>crmDia314(s,original,ctx.hoy||hoyISO()))};
  const al = alcance(b, def2);
  return { crm, l: (crm.subcuentas || []).filter(s => s.tipo === 'cliente' && (al === 'todo' || s.especialista_id === yo(ctx) || ctx.carteraIds.has(s.cliente_id))) };
}
def('circuito_roto', ['crm/crm', 'captacion/captacion'], (ctx, D, b) => {
  const { crm, l } = subcuentas(ctx, D, b, 'mio');
  const cap = D.opcional('captacion/captacion');
  const ids = new Set(l.map(s => s.cliente_id));
  const integ = (cap?.clientes || []).filter(c => ids.has(c.cliente_id)).flatMap(c => (c.avisos || []).filter(a => a.clase_id === 'integracion').map(a => ({ c, a })));
  const rotas = (crm.resumen?.integracion_rota || []).filter(nm => l.some(s => s.nombre === nm));
  return {
    valor:integ.length+rotas.length?integ.length+rotas.length:null, unidad: 'referencias de integración por contrastar', estado:'gris',
    motivo:'Sin unión de eventos Meta y contactos CRM no se acredita fuga. Contrasta las referencias de integración antes de diagnosticar.',
    filas: [...rotas.map(nm => ({ texto: `${nm} · referencia de integración`, estado:'gris', icono: 'plug', href: ir(ctx, 'salud-crm', l.find(s => s.nombre === nm)?.sub_id) })), ...integ.map(x => ({ texto: `${x.c.nombre} · ${x.a.texto}`, estado:'gris', icono: 'plug', href: ir(ctx, 'salud-crm', l.find(s => s.cliente_id === x.c.cliente_id)?.sub_id) }))],
    vacio: { titulo: 'Ningún circuito roto detectado', tono: 'celebrar' }, frescura: fresco('Meta + GHL', crm), medible: 'medias', medibleDetalle: 'El circuito de punta a punta espera un permiso de GoHighLevel',
  };
});
def('leads_sin_tocar', ['crm/crm'], (ctx, D, b) => {
  const crm = D.dato('crm/crm');
  const al = alcance(b, 'mio');
  const ids=new Set(clientesDia314(ctx,crm.subcuentas).map(s=>s.cliente_id)),medido=fuenteCrmDia314(crm,ctx.hoy||hoyISO());
  const l = (crm.leads_sin_tocar || []).filter(x => ids.has(x.cliente_id)&&(al === 'todo' || x.especialista_id === yo(ctx) || ctx.carteraIds.has(x.cliente_id)));
  const g = new Map(); for (const x of l) { const e = g.get(x.sub_id) || { s: x.subcuenta, n: 0 }; e.n += 1; g.set(x.sub_id, e); }
  const filas = [...g.entries()].sort((a, b2) => b2[1].n - a[1].n).map(([sid, e]) => ({ texto: `${e.s} · ${plural(e.n, 'lead')} sin ningún intento`, estado: e.n > 5 ? 'rojo' : 'ambar', icono: 'clock', href: ir(ctx, 'salud-crm', sid) }));
  return {
    valor:l.length?l.length:null,unidad:medido?'contactos observados sin intento registrado':'referencias anteriores de contactos por contrastar',estado:l.length&&medido?'ambar':'gris',
    motivo:'Registros de la copia; no acredita respuesta, cualificación o ausencia total de intentos.',
    filas:filas.map(f=>({...f,estado:medido?'ambar':'gris'})),vacio:{titulo:'Sin observaciones en la copia autorizada'},frescura:fresco('GoHighLevel',crm),medible:'medias',primero:[],
  };
});
def('citas_sin_estado', ['crm/crm'], (ctx, D, b) => {
  const crm = D.dato('crm/crm');
  const al = alcance(b, 'mio');
  const ids=new Set(clientesDia314(ctx,crm.subcuentas).map(s=>s.cliente_id)),medido=fuenteCrmDia314(crm,ctx.hoy||hoyISO());
  const l = (crm.citas_sin_estado || []).filter(x => ids.has(x.cliente_id)&&(al === 'todo' || x.especialista_id === yo(ctx) || ctx.carteraIds.has(x.cliente_id)));
  const g = new Map(); for (const x of l) { const e = g.get(x.sub_id) || { s: x.subcuenta, n: 0 }; e.n += 1; g.set(x.sub_id, e); }
  return {
    valor:l.length?l.length:null,unidad:medido?'citas observadas sin estado de asistencia':'referencias anteriores de citas por contrastar',estado:l.length&&medido?'ambar':'gris',
    motivo: 'Sin estado no hay asistencia: es el número que manda del especialista.',
    filas: [...g.entries()].sort((a,b2)=>b2[1].n-a[1].n).map(([sid,e])=>({texto:`${e.s} · ${plural(e.n,'cita')}`,estado:medido?'ambar':'gris',icono:'cal',href:ir(ctx,'salud-crm',sid)})),
    vacio:{titulo:'Sin observaciones en la copia autorizada'},frescura:fresco('GoHighLevel',crm),medible:'medias',
  };
});
def('whatsapp_fallidos', ['crm/crm'], (ctx, D, b) => {
  const { crm, l } = subcuentas(ctx, D, b, 'mio');
  const f = l.filter(s => n0(s.whatsapp?.fallidos) > 0).sort((a, b2) => b2.whatsapp.fallidos - a.whatsapp.fallidos);
  return {
    valor: suma(f, s => s.whatsapp.fallidos), unidad: `mensajes fallidos en ${plural(f.length, 'subcuenta')}`, estado: f.some(s => n0(s.whatsapp.pct_fallo) > 10) ? 'rojo' : f.length ? 'ambar' : 'verde',
    motivo: 'Número mal, fuera de ventana o número desconectado (el estado del número todavía no se puede leer: falta un permiso de GoHighLevel).',
    filas: f.map(s => ({ texto: s.nombre, extra: `${s.whatsapp.fallidos} de ${s.whatsapp.enviados} (${fmt.num(s.whatsapp.pct_fallo, 1)} %)`, estado: n0(s.whatsapp.pct_fallo) > 10 ? 'rojo' : 'ambar', icono: 'wa', href: ir(ctx, 'salud-crm', s.sub_id) })),
    vacio: { titulo: 'Ningún WhatsApp fallido', tono: 'celebrar' }, frescura: fresco('GoHighLevel', crm), medible: 'hoy',
  };
});
def('montajes', ['crm/crm'], (ctx, D, b) => {
  const crm = D.dato('crm/crm');
  const al = alcance(b, 'mio');
  const l = (crm.montajes || []).filter(m => al === 'todo' || m.crm === ctx.persona.alias || ctx.carteraIds.has(m.cliente_id));
  return {
    valor: l.length, unidad: 'subcuentas en montaje', estado: l.some(m => (m.casillas || []).some(c => c.estado === 'rojo')) ? 'ambar' : '',
    motivo: 'Snapshot, calendario, embudo, primer lead, flujos validados y formación (capacidad: 5-6 montajes a la semana).',
    filas: l.map(m => ({ texto: `${m.nombre} · día ${m.dia}`, extra: `${(m.casillas || []).filter(c => c.estado === 'verde').length} de ${(m.casillas || []).length} casillas${m.crm ? ` · ${m.crm}` : ""}`, estado: (m.casillas || []).some(c => c.estado === 'rojo') ? 'ambar' : 'verde', icono: 'base', href: m.enlace || '#/salud-crm' })),
    vacio: { titulo: 'Ningún montaje en curso' }, frescura: fresco('GoHighLevel', crm), medible: 'medias', medibleDetalle: 'Los flujos validados esperan un permiso de GoHighLevel',
  };
});
def('subcuentas_rojo', ['crm/crm'], (ctx, D, b) => {
  const { crm, l } = subcuentas(ctx, D, b, 'todo');
  const r = l.filter(s => s.estado === 'rojo');
  return {
    valor: r.length, unidad: `en rojo de ${plural(l.length, 'subcuenta')} de clientes`, estado: r.length ? 'rojo' : 'verde',
    motivo: `Con quién la lleva y el motivo principal. ${plural(l.filter(s => s.encendida).length, 'encendida')}.`,
    filas: r.sort((a, b2) => n0(b2.sin_tocar_24h) - n0(a.sin_tocar_24h)).map(s => ({ texto: `${s.nombre} · ${(s.motivos || [])[0]?.texto || 'en rojo'}`, extra: s.especialista || 'sin especialista', estado: 'rojo', icono: 'base', href: ir(ctx, 'salud-crm', s.sub_id) })),
    frescura: fresco('GoHighLevel', crm), medible: 'hoy',
    primero: r.filter(s => s.encendida).slice(0, 2).map(s => ({ peso: 3, icono: 'base', motivo: `${s.nombre} · CRM en rojo`, detalle: `${(s.motivos || [])[0]?.texto || ''} · ${s.especialista || 'sin especialista'}`, ruta: sinAlmohadilla(ir(ctx, 'salud-crm', s.sub_id)), clave: `sub:${s.sub_id}`, cliente_id: s.cliente_id })),
  };
});
def('tabla_especialista', ['crm/crm'], (ctx, D) => {
  const crm=D.dato('crm/crm'),r=secundariosCRM317(ctx,crm);
  return {valor:r.especialistas.length||null,unidad:'especialistas con subcuentas autorizadas',estado:'gris',
    motivo:'Recuentos de la copia dentro del ámbito actual; sin clasificación automática verde/rojo ni evaluación de rendimiento.',
    filas:r.especialistas.map(e=>({texto:`${e.nombre} · ${plural(e.subcuentas,'subcuenta')} en el ámbito`,extra:`Contactos sin intento registrado: ${textoConteo317(e.sin_tocar)} · Citas sin estado (14 días): ${textoConteo317(e.sin_estado)}`,estado:'gris',icono:'persona',href:'#/salud-crm'})),
    frescura:fresco('GoHighLevel',crm),medible:'medias'};
});
def('asistencia_velocidad', ['crm/crm'], (ctx, D) => {
  const crm=D.dato('crm/crm'),r=secundariosCRM317(ctx,crm);
  return {valor:r.asistencia===null?null:fmt.pct(r.asistencia),unidad:'asistencia entre citas con resultado registrado (30 días)',estado:'gris',
    motivo:`Copia parcial autorizada: ${r.asistencia_base} citas con resultado en ${r.asistencia_subcuentas} subcuentas comparables. No es conversión de leads ni tasa sobre todas las citas; no evalúa garantía contractual.`,
    filas:[{texto:'Primer intento registrado en menos de 1 h',extra:r.velocidad===null?'Sin dato':`${fmt.pct(r.velocidad)} de ${r.velocidad_base} contactos juzgables · ${r.velocidad_subcuentas} subcuentas comparables`,estado:'gris',icono:'zap'},
      ...[['agendadas','Citas agendadas'],['celebradas','Citas con asistencia registrada'],['no_presentadas','Citas marcadas como no presentadas'],['sin_estado','Citas sin resultado registrado']].map(([k,texto])=>({texto:`${texto} · ventana de 30 días`,extra:textoConteo317(r.citas[k]),estado:'gris',icono:'cal'}))],
    frescura:fresco('GoHighLevel',crm),medible:'medias',medibleDetalle:'Fuente vigente por subcuenta; cobertura parcial, ceros sólo observados.'};
});
def('fuegos_crm', ['incidencias/incidencias'], (ctx, D) => {
  const inc = D.dato('incidencias/incidencias');
  const l = (inc.incidencias || []).filter(i => ['integracion', 'despacho'].includes(i.donde));
  return {
    valor: l.length, unidad: 'fuegos de despacho o integración', estado: l.some(i => i.gravedad === 'rojo') ? 'rojo' : l.length ? 'ambar' : 'verde',
    motivo: 'Escalados por tu equipo, con el reloj de 48 h.',
    filas: l.map(i => ({ texto: `${i.cliente || nomCli(ctx, i.cliente_id) || 'Sin cliente'} · ${i.titulo}`, extra: `${nombre(ctx, i.responsable_id)} · ${diaCorto(i.detectada)}`, estado: i.gravedad, icono: 'fire', href: ir(ctx, 'incidencias', i.id) })),
    vacio: { titulo: 'Sin fuegos de despacho o integración', tono: 'celebrar' }, frescura: fresco('Incidencias', inc), medible: 'hoy',
    primero: l.filter(i => i.gravedad === 'rojo').slice(0, 1).map(i => ({ peso: 2.8, icono: 'fire', motivo: `${i.cliente || 'Sin cliente'} · ${i.titulo}`, detalle: i.texto, ruta: `incidencias/${i.id}`, clave: `inc:${i.id}`, cliente_id: i.cliente_id })),
  };
});
def('carga_crm', ['crm/crm'], (ctx, D) => {
  const crm = D.dato('crm/crm'); const l = (crm.especialistas || []).slice().sort((a, b) => b.clientes - a.clientes);
  return {
    valor: l.length ? l[0].clientes : 0, unidad: 'clientes el más cargado · tope 16', estado: l.some(e => e.clientes > 16) ? 'rojo' : l.some(e => e.clientes >= 14) ? 'ambar' : 'verde',
    motivo: 'Clientes por especialista frente al tope de 16 (D-07); horas, solo como aviso.',
    barras: l.map(e => ({ etiqueta: e.nombre, valor: e.clientes, max: 16 })), frescura: fresco('Asignaciones', crm), medible: 'hoy',
  };
});

// ------------------------------------------------------------- Técnico de altas (Agus)
def('altas_linea', ['nuevos/nuevos'], (ctx, D, b) => {
  // R12 (B-C01): el estado de arranque sale de la verdad única (encendido), no del plazo de la ficha de altas:
  // «sin encender» solo si de verdad no se ha encendido (Laver se encendió tarde, el día 18).
  const { n, l } = altasNuevos(ctx, D, b, 'todo');
  const o = l.map(a => ({ ...a, arr: arranqueV(ctx, a) })).sort((a, b2) => ordenEstado(a.arr, b2.arr) || b2.dia - a.dia);
  const sinEnc = o.filter(a => a.arr.sinEncender);
  return {
    valor: l.length, unidad: `altas en curso · ${sinEnc.length} sin encender fuera de plazo`, estado: sinEnc.length ? 'rojo' : o.some(a => a.arr.estado === 'ambar') ? 'ambar' : 'verde',
    motivo: 'Del día 0 al 90, cada una con su estado de arranque y su siguiente hito.',
    // V2 (B-M5): «siguiente paso: encender (objetivo día 10, límite 12)», nunca «Encendido · encendido el día 10» (parecía hecho)
    pistas: o.slice(0, 5).map(a => { const porEncender = a.arr.sinEncender || verdad(ctx, a.cliente_id)?.encendido?.estado === 'pendiente_en_plazo';
      const sig = a.siguiente?.nombre ? `siguiente paso: ${a.siguiente.nombre.toLowerCase()}` : 'sin siguiente paso';
      return { nombre: a.nombre, dia: a.dia, estado: a.arr.estado, sig: `${a.arr.texto} · ${sig}${porEncender ? ' (objetivo encender el día 10, límite 12)' : ''}`, href: ir(ctx, 'clientes-nuevos', a.cliente_id) }; }),
    mas: Math.max(0, o.length - 5), frescura: fresco('Sign + ClickUp + Meta', n), medible: 'hoy',
    primero: sinEnc.slice(0, 2).map(a => ({ peso: 3, icono: 'rocket', motivo: `${a.nombre} · día ${a.dia} sin encender`, detalle: `Siguiente: ${a.siguiente?.nombre || 'sin hito'}${a.siguiente?.quien ? ` (${a.siguiente.quien})` : ''}. Pasado el día 12 sin campaña encendida.`, ruta: `clientes-nuevos/${a.cliente_id}`, clave: `alta:${a.cliente_id}`, cliente_id: a.cliente_id })),
  };
});
def('accesos_pendientes', ['nuevos/nuevos'], (ctx, D) => {
  const n = D.dato('nuevos/nuevos');
  const l = (n.altas || []).map(a => ({ a, f: (a.accesos || []).filter(x => x.estado !== 'dado') })).filter(x => x.f.length).sort((x, y) => y.f.length - x.f.length);
  return {
    valor: n.resumen?.accesos_falta ?? suma(l, x => x.f.length), unidad: 'accesos que faltan', estado: l.length ? 'ambar' : 'verde',
    motivo: '«Dado / falta / quién lo tiene / desde cuándo», nunca la clave. Encargo de tratamiento firmado antes de pedirlos.',
    filas: l.map(x => ({ texto: `${x.a.nombre} · ${plural(x.f.length, 'acceso')}`, extra: x.f.slice(0, 3).map(r => r.recurso.split(' (')[0]).join(', '), estado: x.a.dia > 7 ? 'rojo' : 'ambar', icono: 'key', href: ir(ctx, 'clientes-nuevos', x.a.cliente_id) })),
    frescura: fresco('ClickUp', n), medible: 'hoy',
  };
});
def('casillas_tecnicas', ['nuevos/nuevos'], (ctx, D) => {
  const n = D.dato('nuevos/nuevos');
  const l = (n.altas || []).map(a => ({ a, r: (a.casillas || []).filter(c => c.estado === 'rojo') })).filter(x => x.r.length).sort((x, y) => y.r.length - x.r.length);
  return {
    valor: suma(l, x => x.r.length), unidad: `casillas en rojo en ${plural(l.length, 'alta')}`, estado: l.length ? 'rojo' : 'verde',
    motivo: 'Píxel, dominio verificado, DNS (SPF, DKIM, DMARC), WhatsApp, calendario y snapshot.',
    filas: l.map(x => ({ texto: x.a.nombre, extra: x.r.map(c => c.texto).join(' · '), estado: 'rojo', icono: 'check', href: ir(ctx, 'clientes-nuevos', x.a.cliente_id) })),
    vacio: { titulo: 'Todas las casillas en verde', tono: 'celebrar' }, frescura: fresco('Meta + DNS + GHL', n), medible: 'hoy',
  };
});
def('conexiones_caidas', ['nuevos/nuevos'], (ctx, D) => {
  const n = D.dato('nuevos/nuevos');
  const l = (n.subcuentas || []).filter(s => s.estado === 'rojo');
  return {
    valor: l.length, unidad: `caídas de ${n.resumen?.subcuentas ?? '—'} subcuentas`, estado: l.length ? 'rojo' : 'verde',
    motivo: `WhatsApp con fallos, calendario sin usuario, dominio sin verificar y píxel sin eventos. ${plural(n0(n.resumen?.subcuentas_aviso), 'subcuenta más', 'subcuentas más')} con aviso.`,
    filas: l.map(s => ({ texto: `${s.cliente || s.subcuenta} · ${(s.problemas || [])[0]?.texto || 'caída'}`, extra: s.dueno, estado: 'rojo', icono: 'plug', href: s.cliente ? ir(ctx, 'clientes-nuevos', s.cliente) : '#/clientes-nuevos' })),
    frescura: fresco('GoHighLevel', n), medible: 'hoy',
  };
});
def('talleres_semana', ['nuevos/nuevos'], (ctx, D) => {
  const n = D.dato('nuevos/nuevos');
  const l = (n.talleres || []).filter(t => !t.pasado).sort((a, b) => String(a.inicio).localeCompare(String(b.inicio)));
  return {
    valor: l.length, unidad: 'talleres por delante', estado: '',
    motivo: `Las 48 h de la víspera: si no contesta, se llama. ${n.talleres_nota || ''}`.trim(),
    filas: l.map(t => ({ texto: `${t.cliente} · ${t.titulo}`, extra: cuandoTxt(t.inicio), estado: 'gris', icono: 'video', href: ir(ctx, 'clientes-nuevos', t.cliente_id, hrefCliente(ctx, t.cliente_id)) })),
    vacio: { titulo: 'Ningún taller agendado por delante', texto: 'Salen del calendario de RO en GoHighLevel (foto del 1-oct).' }, frescura: fresco('GHL de RO', n), medible: 'medias',
  };
});
def('bloqueos_meta', ['nuevos/nuevos'], (ctx, D) => {
  const n = D.dato('nuevos/nuevos');
  const l = (n.altas || []).filter(a => a.meta && (a.meta.estado !== 'activa' || n0(a.meta.motivo_bloqueo) || a.meta.con_pago === false));
  return {
    valor: l.filter(a => a.meta.estado !== 'activa' || n0(a.meta.motivo_bloqueo)).length, unidad: `bloqueadas · ${l.filter(a => a.meta.con_pago === false).length} sin método de pago`, estado: l.some(a => a.meta.estado !== 'activa') ? 'rojo' : l.length ? 'ambar' : 'verde',
    motivo: 'Estado de la cuenta publicitaria de cada alta y su motivo (Meta).',
    filas: l.map(a => ({ texto: `${a.nombre} · cuenta publicitaria ${a.meta.estado} · campaña ${arranqueV(ctx, a).texto}`, extra: a.meta.con_pago === false ? 'sin método de pago' : `motivo ${a.meta.motivo_bloqueo}`, estado: a.meta.estado !== 'activa' ? 'rojo' : 'ambar', icono: 'candado', href: ir(ctx, 'clientes-nuevos', a.cliente_id), abrir: a.meta.prueba ? { href: a.meta.prueba, texto: 'Meta' } : null })),
    vacio: { titulo: 'Sin bloqueos de Meta', tono: 'celebrar' }, frescura: fresco('Meta', n), medible: 'hoy',
  };
});
def('carga_altas', ['nuevos/nuevos'], (ctx, D) => {
  const n=D.dato('nuevos/nuevos'),r=referenciaAlta317(n);
  return {valor:r.carga===null?null:fmt.num(r.carga),unidad:'altas · referencia del generador anterior',estado:'gris',
    motivo:`Carga semanal heredada: periodo y cobertura por contrastar${r.tope===null?'':` · tope de referencia ${r.tope}`}. ${r.mediana===null?'Primer resultado: Sin dato.':`Mediana heredada hasta el «primer lead»: ${fmt.num(r.mediana)} días; evento y cohorte no acreditados, no resultado cualificado RO.`}`,
    barras:[],frescura:fresco('ClickUp · referencia de altas',n),medible:'medias'};
});

// ------------------------------------------------------------- SEO, web y ficha de Google
function seoClientes(ctx, D, b, def2) {
  const s = D.dato('seo/seo');
  const al = alcance(b, def2);
  const mia = silla(ctx, 'seo');
  return { s, l: (s.clientes || []).filter(c => al === 'todo' || c.seo_id === yo(ctx) || (mia && mia.has(c.cliente_id)) || (al === 'equipo' && c.seo_id)) };
}
def('seo_rojos', ['seo/seo'], (ctx, D, b) => {
  const { s, l } = seoClientes(ctx, D, b, 'todo');
  const r = l.filter(c => c.estado === 'rojo');
  return {
    valor: r.length, unidad: `en rojo de ${l.length}`, estado: r.length ? 'rojo' : 'verde',
    motivo: 'Cada uno con su motivo en una frase y quién lo lleva.',
    filas: r.map(c => ({ texto: `${c.cliente} · ${c.motivo}`, extra: c.seo_nombre?.split(' ')[0] || 'sin SEO', estado: 'rojo', icono: 'fire', href: ir(ctx, 'seo-web', c.cliente_id) })),
    vacio: { titulo: 'Ningún cliente de SEO en rojo', tono: 'celebrar' }, frescura: fresco('SE Ranking + Search Console', s._meta?.generado), medible: 'hoy',
    primero: r.slice(0, 2).map(c => ({ peso: 2.9, icono: 'globe', motivo: `${c.cliente} · SEO en rojo`, detalle: c.motivo, ruta: sinAlmohadilla(ir(ctx, 'seo-web', c.cliente_id)), clave: `seo:${c.cliente_id}`, cliente_id: c.cliente_id })),
  };
});
def('seo_mis_clientes', ['seo/seo'], (ctx, D, b) => {
  const { s, l } = seoClientes(ctx, D, b, 'mio');
  return {
    valor: l.filter(c => c.estado === 'rojo').length, unidad: `en rojo de ${plural(l.length, 'cliente')}`, estado: l.some(c => c.estado === 'rojo') ? 'rojo' : l.some(c => c.estado === 'ambar') ? 'ambar' : 'verde',
    motivo: 'Tus clientes con su semáforo y el motivo en una frase.',
    filas: l.slice().sort(ordenEstado).map(c => ({ texto: `${c.cliente} · ${c.motivo || 'sin avisos'}`, extra: typeof c.clics?.var_sem === 'number' ? `clics ${c.clics.var_sem > 0 ? '+' : ''}${fmt.num(c.clics.var_sem, 1)} % semana` : 'clics: sin Search Console', estado: c.estado, icono: 'globe', href: ir(ctx, 'seo-web', c.cliente_id) })),
    vacio: { titulo: 'Sin clientes de SEO asignados', texto: 'Los asigna Coti en Ajustes.', quien: 'Coti' }, frescura: fresco('SE Ranking + Search Console', s._meta?.generado), medible: 'hoy',
    primero: l.filter(c => c.estado === 'rojo').slice(0, 2).map(c => ({ peso: 2.9, icono: 'globe', motivo: `${c.cliente} · en rojo`, detalle: c.motivo, ruta: sinAlmohadilla(ir(ctx, 'seo-web', c.cliente_id)), clave: `seo:${c.cliente_id}`, cliente_id: c.cliente_id })),
  };
});
def('palabras_mov', ['seo/seo'], (ctx, D, b) => {
  const { s, l } = seoClientes(ctx, D, b, 'mio');
  const fuera = l.flatMap(c => (c.alertas || []).filter(a => a.tipo === 'fuera_top10').map(a => ({ c, a })));
  const suben = l.flatMap(c => (c.movimientos?.suben || []).filter(m => m.antes !== null && m.antes !== undefined).map(m => ({ c, m }))).sort((a, b2) => b2.m.delta - a.m.delta);
  return {
    valor: fuera.length, unidad: `salen del top 10 · ${plural(suben.length, 'sube', 'suben')}`, estado: fuera.length ? 'rojo' : 'verde',
    motivo: 'Desde la última comprobación de SE Ranking, cartera agrupada por persona.',
    filas: [...fuera.map(x => ({ texto: `«${x.a.palabra}» · ${x.c.cliente}`, extra: `${x.a.antes} → ${x.a.hoy} · ${x.c.seo_nombre?.split(' ')[0] || '—'}`, estado: 'rojo', icono: 'baja', href: ir(ctx, 'seo-web', x.c.cliente_id) })),
      ...suben.slice(0, 3).map(x => ({ texto: `«${x.m.k}» · ${x.c.cliente}`, extra: `${x.m.antes} → ${x.m.hoy}`, estado: 'verde', icono: 'sube', href: ir(ctx, 'seo-web', x.c.cliente_id) }))],
    frescura: fresco('SE Ranking', s._meta?.seranking?.leido || s._meta?.generado), medible: 'hoy',
  };
});
def('mes1_sin_palabras', ['seo/seo'], (ctx, D) => {
  const s = D.dato('seo/seo'); const l = (s.clientes || []).filter(c => c.mes1_sin_palabras);
  return {
    valor: l.length, unidad: 'altas sin palabras en seguimiento', estado: l.length ? 'rojo' : 'verde',
    motivo: 'Altas en el mes 1 sin palabras clave en seguimiento o con Search Console / Analytics sin conectar.',
    filas: l.map(c => ({ texto: c.cliente, extra: c.seo_nombre || 'sin SEO', estado: 'rojo', icono: 'rocket', href: ir(ctx, 'seo-web', c.cliente_id) })),
    vacio: { titulo: 'Todas las altas tienen palabras en seguimiento', tono: 'celebrar' }, frescura: fresco('SE Ranking', s._meta?.generado), medible: 'hoy',
  };
});
function celula(ctx, D) {
  const p = D.dato('produccion/produccion');
  return { p, l: (p.personas || []).filter(x => x.jefe === yo(ctx) && x.estado_persona !== 'baja') };
}
def('celula', ['produccion/produccion'], (ctx, D) => {
  const { p, l } = celula(ctx, D);
  return {
    valor: suma(l, x => x.vencidas), unidad: `tareas vencidas en ${plural(l.length, 'persona')}`, estado: suma(l, x => x.vencidas) ? 'ambar' : 'verde',
    motivo: 'Tareas vencidas, revisiones de más de 48 h y piezas devueltas de tu gente.',
    filas: l.slice().sort((a, b) => b.vencidas - a.vencidas).map(x => ({ texto: x.alias, extra: `${x.vencidas} vencidas · ${x.en_revision} en revisión · ${x.devueltas} devueltas`, estado: x.vencidas > 10 ? 'rojo' : x.vencidas ? 'ambar' : 'verde', icono: 'persona', href: '#/produccion' })),
    vacio: { titulo: 'Sin personas a tu cargo en la tabla de personas' }, frescura: fresco('ClickUp', p), medible: 'hoy',
  };
});
def('carga_gente', ['produccion/produccion'], (ctx, D) => {
  const { p, l } = celula(ctx, D);
  return {
    valor: suma(l, x => x.abiertas), unidad: 'tareas abiertas en tu gente', estado: '',
    motivo: 'Tareas abiertas por persona; horas solo como aviso de quién no imputa.',
    barras: l.slice().sort((a, b) => b.abiertas - a.abiertas).map(x => ({ etiqueta: x.alias, valor: x.abiertas, max: Math.max(...l.map(y => y.abiertas), 1) })),
    frescura: fresco('ClickUp', p), medible: 'hoy',
  };
});
/** R12 (C-M2): «mis webs» = las de los clientes de su cartera de web (y de SEO) en las ASIGNACIONES; el resto de la casa,
 *  aparte, solo como guardia. */
function idsMisWebs(ctx, D) {
  const w = silla(ctx, 'web'), s = silla(ctx, 'seo');
  if (w || s) return new Set([...(w || []), ...(s || [])]);
  const sd = D.opcional('seo/seo');
  return new Set((sd?.clientes || []).filter(c => c.seo_id === yo(ctx) || c.web_id === yo(ctx)).map(c => c.cliente_id));
}
function webs(ctx, D, b) {
  const w = D.dato('seo/webs');
  const al = alcance(b, 'todo');
  const ids = al === 'mio' ? idsMisWebs(ctx, D) : null;
  const todas = w.webs || [];
  return { w, l: todas.filter(x => !ids || ids.has(x.cliente)), resto: ids ? todas.filter(x => !ids.has(x.cliente)) : [] };
}
const esSpam = x => (x.comprobacion?.spam || []).length > 0;
def('webs_caidas', ['seo/webs', 'seo/seo'], (ctx, D, b) => {
  const { w, l, resto } = webs(ctx, D, b);
  const r = l.filter(x => x.estado === 'rojo'), a = l.filter(x => x.estado === 'ambar');
  const guardia = resto.filter(x => x.estado === 'rojo');
  const filasGuardia = guardia.length && ctx.persona.puestos.includes('web') ? [{ texto: `Guardia: ${plural(guardia.length, 'web')} del resto de la casa en rojo`, extra: guardia.slice(0, 3).map(x => x.nombre).join(', '), estado: 'gris', icono: 'mundo_web', href: ctx.veModulo('seo-web') ? '#/seo-web' : null }] : [];
  return {
    valor: r.length, unidad: `en rojo de ${plural(l.length, 'web')}${resto.length ? ' tuyas' : ''} · ${plural(a.length, 'aviso')}`, estado: r.length ? 'rojo' : a.length ? 'ambar' : 'verde',
    motivo: `Desde la IP de RO (${diaCorto(w._meta?.monitor?.leido)} ${horaCorta(w._meta?.monitor?.leido)}). La vista «desde fuera», para separar «caída» de «bloqueada solo para RO», llega cuando la app esté en la nube.`,
    filas: [...[...r, ...a].map(x => ({ texto: `${x.nombre} · ${x.motivo}`, extra: x.con_campana ? 'con campaña encendida' : '', estado: x.estado, icono: 'mundo_web', href: x.cliente && x.cliente !== '_ro' ? ir(ctx, 'seo-web', x.cliente) : x.url, abrir: x.url ? { href: x.url, texto: 'la web' } : null }))].flatMap((f, i) => (i === r.length - 1 ? [f, ...filasGuardia] : [f])).concat(r.length ? [] : filasGuardia),
    vacio: { titulo: 'Todas las webs responden', tono: 'celebrar' }, frescura: fresco('Monitor desde RO', w._meta?.monitor?.leido || w._meta?.generado), medible: 'medias', medibleDetalle: 'Solo desde la IP de RO de momento',
    primero: r.filter(x => x.con_campana).slice(0, 2).map(x => ({ peso: 3.8, icono: 'mundo_web', motivo: `${x.nombre} · ${esSpam(x) ? 'spam en la portada, con campaña' : 'web caída con campaña'}`, detalle: x.motivo, ruta: sinAlmohadilla(ir(ctx, 'seo-web', x.cliente)), clave: `web:${x.cliente}` })),
  };
});
def('tecnico_web', ['seo/webs', 'seo/seo'], (ctx, D) => BLOQUES.webs_caidas.hacer(ctx, D, { alcance: 'mio' }));
def('certificados', ['seo/webs'], (ctx, D, b) => {
  const { w, l } = webs(ctx, D, b);
  const c = l.filter(x => x.comprobacion?.cert_dias !== null && x.comprobacion?.cert_dias !== undefined && x.comprobacion.cert_dias < 30).sort((a, b2) => a.comprobacion.cert_dias - b2.comprobacion.cert_dias);
  return {
    valor: c.length, unidad: 'certificados caducan en < 30 días', estado: c.some(x => x.comprobacion.cert_dias <= 7) ? 'rojo' : c.length ? 'ambar' : 'verde',
    motivo: 'Bien > 30 días · vigilar 8-30 · crítico ≤ 7 o caducado.',
    filas: c.map(x => ({ texto: x.nombre, extra: `caduca ${diaCorto(x.comprobacion.cert_caduca)} · ${x.comprobacion.cert_dias} días`, estado: x.comprobacion.cert_dias <= 7 ? 'rojo' : 'ambar', icono: 'candado', href: x.cliente && x.cliente !== '_ro' ? ir(ctx, 'seo-web', x.cliente) : x.url, abrir: x.url ? { href: x.url, texto: 'la web' } : null })),
    vacio: { titulo: 'Ningún certificado caduca pronto', tono: 'celebrar' }, frescura: fresco('Monitor desde RO', w._meta?.monitor?.leido), medible: 'medias', medibleDetalle: 'Monitor desde RO; dominios, sin lector',
  };
});
def('webs_lentas', ['seo/webs'], (ctx, D, b) => {
  // V2 (C-9): UNA regla de «lenta», la de webs.json (lenta = responde y tarda 5 s o más desde RO), sobre TODAS las webs como
  // el chip «Lentas» de la pantalla Webs; las tuyas, al lado.
  const { w, l } = webs(ctx, D, b);
  const umbral = (w._meta?.lenta || {}).umbral_ms || 5000;
  const esLenta = x => (x.lenta !== undefined ? !!x.lenta : (x.responde ?? true) && n0(x.comprobacion?.ms) >= umbral);
  const todas = (w.webs || []).filter(esLenta).sort((a, b2) => n0(b2.comprobacion?.ms) - n0(a.comprobacion?.ms));
  const ids = new Set(l.map(x => x.cliente)); const tuyas = todas.filter(x => ids.has(x.cliente));
  const s = alcance(b, 'todo') === 'mio' ? [...tuyas, ...todas.filter(x => !ids.has(x.cliente))] : todas;
  return {
    valor: todas.length, unidad: `lentas de ${plural((w.webs || []).length, 'web')}${alcance(b, 'todo') === 'mio' ? ` · ${tuyas.length} tuyas` : ''}`, estado: todas.length ? 'ambar' : 'verde',
    motivo: `${(w._meta?.lenta || {}).texto || 'Lenta = responde, pero tarda 5 s o más en servir la portada desde la IP de RO.'} La misma cuenta que el filtro «Lentas» de Webs.`,
    filas: s.map(x => ({ texto: `${x.nombre}${ids.has(x.cliente) && s !== todas ? ' · tuya' : ''}`, extra: `${fmt.num(n0(x.comprobacion?.ms) / 1000, 1)} s`, estado: 'ambar', icono: 'clock', href: x.cliente && x.cliente !== '_ro' ? ir(ctx, 'seo-web', x.cliente) : x.url, abrir: x.url ? { href: x.url, texto: 'la web' } : null })),
    vacio: { titulo: 'Ninguna portada lenta', tono: 'celebrar' }, frescura: fresco('Monitor desde RO', w._meta?.monitor?.leido), medible: 'medias', medibleDetalle: 'PageSpeed, a petición',
  };
});
def('spam_web', ['seo/webs'], (ctx, D, b) => {
  const { w, l } = webs(ctx, D, b);
  const s = l.filter(x => (x.comprobacion?.spam || []).length);
  return {
    valor: s.length, unidad: 'webs con spam inyectado', estado: s.length ? 'rojo' : 'verde',
    motivo: 'Casinos, apuestas o URL ajenas en la portada (caso Geslabor).',
    filas: s.map(x => ({ texto: x.nombre, extra: (x.comprobacion.spam || []).slice(0, 3).join(', '), estado: 'rojo', icono: 'escudo', href: x.cliente && x.cliente !== '_ro' ? ir(ctx, 'seo-web', x.cliente) : x.url, abrir: x.url ? { href: x.url, texto: 'la web' } : null })),
    vacio: { titulo: 'Sin spam detectado', tono: 'celebrar' }, frescura: fresco('Monitor desde RO', w._meta?.monitor?.leido), medible: 'medias',
    primero: s.slice(0, 1).map(x => ({ peso: 3.4, icono: 'escudo', motivo: `${x.nombre} · spam en la portada`, detalle: (x.comprobacion.spam || []).join(', '), ruta: sinAlmohadilla(ir(ctx, 'seo-web', x.cliente)), clave: `spam:${x.cliente}` })),
  };
});
def('maps_posicion', ['seo/seo'], (ctx, D, b) => {
  // V2 (C-23): la misma cuenta que «Posiciones en Maps» de SEO, ficha y webs: la jefa ve todas; el resto, sus clientes; solo
  // palabras con posición (k.mapa)
  const jefa = (ctx.persona.puestos || []).some(q => ['jefa_seo', 'direccion', 'operaciones', 'proyectos'].includes(q));
  const { s, l } = seoClientes(ctx, D, jefa ? { ...b, alcance: 'todo' } : b, 'mio');
  const f = l.flatMap(c => (c.informe15 || []).filter(k => k.mapa).map(k => ({ c, k })));
  return {
    valor: f.length, unidad: 'palabras con posición en Maps', estado: '',
    motivo: 'Solo donde SE Ranking sigue Maps. La ficha de Google en sí llega cuando se conecte.',
    filas: f.sort((a, b2) => a.k.mapa - b2.k.mapa).map(x => ({ texto: `«${x.k.k}» · ${x.c.cliente}`, extra: `Maps ${x.k.mapa}`, estado: x.k.mapa <= 3 ? 'verde' : 'ambar', icono: 'pin', href: ir(ctx, 'seo-web', x.c.cliente_id) })),
    vacio: { titulo: 'Ninguna palabra con Maps en seguimiento', texto: 'Se añade en el proyecto de SE Ranking del cliente.' }, frescura: fresco('SE Ranking', s._meta?.generado), medible: 'medias',
  };
});

// ------------------------------------------------------------- Redes
/** R12 (C-A2): «mis clientes de redes» = la cartera de redes de las ASIGNACIONES (la que dice la ficha: «tú llevas las
 *  redes»), no el responsable que trae Metricool. Los de su cartera que no están en Metricool se cuentan aparte. */
function redes(ctx, D, b) {
  const r = D.dato('redes/redes');
  const al = alcance(b, 'mio');
  const mia = silla(ctx, 'redes');
  const esMio = c => (mia && mia.size ? mia.has(c.cliente_id) : c.redes_id === yo(ctx) || c.account_id === yo(ctx));
  const l = (r.clientes || []).filter(c => al === 'todo' || esMio(c));
  const enMetricool = new Set((r.clientes || []).map(c => c.cliente_id));
  const fuera = al === 'todo' || !mia ? [] : [...mia].filter(id => !enMetricool.has(id));
  return { r, l, fuera };
}
def('redes_huecos', ['redes/redes'], (ctx, D, b) => {
  const { r, l, fuera } = redes(ctx, D, b);
  const h7 = l.filter(c => (c.huecos || []).some(x => x.en_7));
  const h14 = l.filter(c => (c.huecos || []).length);
  return {
    valor: h14.length, unidad: `con huecos de ${plural(l.length, 'cliente')} · ${h7.length} en 7 días`, estado: h7.length ? 'rojo' : h14.length ? 'ambar' : 'verde',
    motivo: `Huecos de ${r._meta?.hueco_dias || 4} días o más en los próximos 14 (Metricool).`,
    filas: [...h14.map(c => ({ texto: c.cliente, extra: (c.huecos || []).map(x => `${diaCorto(x.desde)} → ${diaCorto(x.hasta)}`).slice(0, 2).join(' · '), estado: (c.huecos || []).some(x => x.en_7) ? 'rojo' : 'ambar', icono: 'cal', href: ir(ctx, 'redes', c.cliente_id) })),
      ...(fuera.length ? [{ texto: `${plural(fuera.length, 'cliente')} de tu cartera sin calendario en Metricool`, extra: fuera.map(id => nomCli(ctx, id) || id).slice(0, 4).join(', '), estado: 'gris', icono: 'cal' }] : [])],
    vacio: { titulo: '14 días cubiertos', tono: 'celebrar' }, frescura: fresco('Metricool', r._meta?.leido_metricool), medible: 'hoy',
    primero: h7.slice(0, 1).map(c => ({ peso: 2.6, icono: 'cal', motivo: `${c.cliente} · hueco en los próximos 7 días`, detalle: `${c.programadas_14} programadas en 14 días.`, ruta: sinAlmohadilla(ir(ctx, 'redes', c.cliente_id)), clave: `hueco:${c.cliente_id}`, cliente_id: c.cliente_id })),
  };
});
def('redes_fallidas', ['redes/redes'], (ctx, D, b) => {
  const { r, l } = redes(ctx, D, b);
  const f = l.filter(c => n0(c.fallidas_7));
  return {
    valor: suma(f, c => c.fallidas_7), unidad: 'fallidas en 7 días', estado: f.length ? 'rojo' : 'verde',
    motivo: 'Fallidas o desconectadas: hay que volver a publicarlas.',
    filas: f.map(c => ({ texto: c.cliente, extra: `${c.fallidas_7} fallidas · ${(c.fallidas || [])[0]?.redes?.[0]?.red || ''}`, estado: 'rojo', icono: 'alert', href: ir(ctx, 'redes', c.cliente_id) })),
    vacio: { titulo: 'Todo salió', tono: 'celebrar' }, frescura: fresco('Metricool', r._meta?.leido_metricool), medible: 'hoy',
  };
});
def('redes_aprobacion', ['redes/redes'], (ctx, D, b) => {
  const { r, l } = redes(ctx, D, b);
  const p = l.filter(c => n0(c.borradores));
  return {
    valor: suma(p, c => c.borradores), unidad: 'borradores por aprobar', estado: p.length ? 'ambar' : 'verde',
    motivo: r._meta?.aprobaciones || 'Del account o del cliente, con los días que llevan.',
    filas: p.map(c => ({ texto: c.cliente, extra: plural(c.borradores, 'borrador', 'borradores'), estado: 'ambar', icono: 'check', href: ir(ctx, 'redes', c.cliente_id) })),
    vacio: { titulo: 'Nada esperando aprobación', tono: 'celebrar' }, frescura: fresco('Metricool', r._meta?.leido_metricool), medible: 'medias',
  };
});
def('redes_mejor_peor', ['redes/redes'], (ctx, D, b) => {
  const { r, l } = redes(ctx, D, b);
  const f = [];
  for (const c of l) {
    if (c.mejor?.tasa !== undefined) f.push({ texto: `${c.cliente} · mejor en ${c.mejor.red}`, extra: `${fmt.num(c.mejor.tasa, 1)} % (umbral ${fmt.num(c.mejor.umbral, 1)} %)`, estado: c.mejor.tasa >= c.mejor.umbral ? 'verde' : 'ambar', icono: 'star', href: c.mejor.url });
    if (c.peor?.tasa !== undefined) f.push({ texto: `${c.cliente} · peor en ${c.peor.red}`, extra: `${fmt.num(c.peor.tasa, 1)} %`, estado: c.peor.tasa >= c.peor.umbral ? 'verde' : 'rojo', icono: 'baja', href: c.peor.url });
  }
  return {
    valor: l.length, unidad: 'clientes', estado: '', motivo: 'Interacción sobre alcance de la última semana frente al umbral de cada canal (D-59).',
    filas: f, frescura: fresco('Metricool', r._meta?.leido_metricool), medible: 'hoy',
  };
});

// ------------------------------------------------------------- Producción y tareas de cada uno
/** V2 (C-6): la cola con el «hoy» de verdad, con alDia() de produccion_comun.js (la MISMA regla que Producción y el
 *  generador): lo que vencía ayer ya está vencido aunque el fichero sea de ayer («vence 2-oct» un día 3 no es «para hoy»). */
function cola(ctx, D) {
  const p = alDia(D.dato('produccion/produccion'), hoyISO());
  return { p, l: (p.cola || []).filter(x => x.persona_id === yo(ctx)) };
}
const ORD_GRUPO = { vencida: 0, hoy: 1, bloqueada: 2, revision: 3, semana: 4, despues: 5 };
function bloqueCola(ctx, D, filtro, opciones) {
  const { p, l } = cola(ctx, D);
  const f = l.filter(filtro).sort((a, b) => (ORD_GRUPO[a.grupo] ?? 9) - (ORD_GRUPO[b.grupo] ?? 9) || n0(a.prio_n) - n0(b.prio_n) || String(a.vence).localeCompare(String(b.vence)));
  return {
    ...opciones(f, l),
    filas: f.map(x => ({ texto: x.tarea, extra: `${x.cliente || nomCli(ctx, x.cli) || 'sin cliente'} · ${x.grupo === 'vencida' ? `venció ${diaCorto(x.vence)}` : x.vence ? `vence ${diaCorto(x.vence)}` : 'sin fecha'}${x.devuelta ? ' · devuelta' : ''}`, estado: x.grupo === 'vencida' ? 'rojo' : x.grupo === 'hoy' ? 'ambar' : x.grupo === 'bloqueada' ? 'ambar' : 'gris', icono: x.grupo === 'bloqueada' ? 'candado' : 'check', href: ir(ctx, 'produccion', x.id, x.url), abrir: x.url ? { href: x.url, texto: 'ClickUp' } : null })),
    frescura: fresco('ClickUp', p), medible: 'hoy',
  };
}
const tareas = (ctx, D) => bloqueCola(ctx, D, x => ['vencida', 'hoy', 'semana', 'bloqueada'].includes(x.grupo), (f) => {
  const v = f.filter(x => x.grupo === 'vencida').length, h2 = f.filter(x => x.grupo === 'hoy').length;
  return {
    valor: h2, unidad: `para hoy · ${v} vencidas`, estado: v ? 'rojo' : h2 ? 'ambar' : 'verde',
    motivo: 'Por fecha y prioridad: primero lo vencido, luego hoy y la semana.',
    vacio: { titulo: 'Nada para hoy ni vencido', tono: 'celebrar' },
    primero: f.filter(x => x.grupo === 'vencida').slice(0, 1).map(x => ({ peso: 2.2, icono: 'check', motivo: `Tarea vencida · ${x.tarea}`, detalle: `${x.cliente || nomCli(ctx, x.cli) || 'sin cliente'} · venció el ${FECHAS.diaSemana(x.vence)} ${diaCorto(x.vence)}`, ruta: sinAlmohadilla(ir(ctx, 'produccion', x.id)), clave: `tarea:${x.id}`, plazo: FECHAS.dia(x.vence) })),
  };
});
def('cola_mia', ['produccion/produccion'], tareas);
def('tareas_mias', ['produccion/produccion'], tareas);
def('devueltas', ['produccion/produccion'], (ctx, D) => bloqueCola(ctx, D, x => x.devuelta, f => ({
  valor: f.length, unidad: 'piezas devueltas', estado: f.length ? 'ambar' : 'verde', motivo: 'Con su comentario en ClickUp; las rondas se cuentan aproximadas (ClickUp no guarda cuántas veces vuelve).',
  vacio: { titulo: 'Ninguna pieza devuelta', tono: 'celebrar' },
})));
// V2 (C-17): «bloqueada por el cliente» solo si es de un cliente de verdad: fuera las internas de RO («Ranking Online
// Organización», «ADMIN», «Diseño organigrama»…), que no esperan a nadie de fuera
const esInterna = x => !x.cli && /ranking online|^admin$|^interno|^ro\b/i.test(String(x.cliente || '').trim());
def('bloqueadas', ['produccion/produccion'], (ctx, D) => bloqueCola(ctx, D, x => x.grupo === 'bloqueada' && !esInterna(x) && !!(x.cli || x.cliente), f => ({
  valor: f.length, unidad: f.length === 1 ? 'bloqueada por el cliente' : 'bloqueadas por el cliente', estado: f.length ? 'ambar' : 'verde', motivo: 'Por falta de material del cliente, con el account avisado. Las tareas internas de RO no cuentan aquí.',
  vacio: { titulo: 'Nada bloqueado', tono: 'celebrar' },
})));
def('piezas_rendimiento', ['produccion/produccion'], (ctx, D) => {
  const p = D.dato('produccion/produccion'); const r = p.anuncios_resumen || {};
  const ini = r.iniciales?.[yo(ctx)];
  return {
    valor: null, unidad: '', estado: 'gris',
    motivo: `Ganadoras y cansadas en índice, sin euros (D-82). ${r.con_autor === 0 ? `Ninguno de los ${r.anuncios} anuncios lleva aún las iniciales del autor en el nombre (D-43)` : ''}${ini ? `: las tuyas son «${ini}».` : '.'}`,
    filas: [], vacio: { titulo: 'Sin autor no hay rendimiento por persona', texto: `Pon tus iniciales${ini ? ` («${ini}»)` : ''} en el nombre de cada anuncio y aquí sale cómo rinde.`, quien: 'Trafficker al publicar' },
    frescura: fresco('Meta (anuncios)', r.hora || p), medible: 'medias', medibleDetalle: '0 anuncios con autor',
  };
});
def('horas_mias', ['horas/horas', 'personas_m20/equipo'], (ctx, D) => {
  const hr = D.opcional('horas/horas');
  const p = (hr?.personas || []).find(x => x.persona_id === yo(ctx));
  if (p) {
    const m = (p.meses || [])[p.meses.length - 1] || {};
    return {
      valor: fmt.num(p.ayer, 1), unidad: `h ayer · ${fmt.num(p.semana, 1)} h esta semana`, estado: n0(p.ayer) ? 'verde' : 'ambar',
      motivo: n0(p.ayer) ? 'Imputado. Las horas son solo un aviso (D-27).' : `Ayer no imputaste. ${m.dias_sin_imputar ? `${m.dias_sin_imputar} día(s) sin imputar este mes.` : ''} Solo un aviso (D-27).`,
      filas: (m.fechas_sin_imputar || []).map(f => ({ texto: `${diaCorto(f)} sin imputar`, estado: 'ambar', icono: 'clock', href: '#/horas' })),
      vacio: { titulo: 'Ningún día sin imputar este mes', tono: 'celebrar' }, frescura: fresco('ClickUp · horas', hr), medible: 'medias', medibleDetalle: hr?.sello?.texto || 'Horas incompletas',
    };
  }
  const e = D.dato('personas_m20/equipo');
  const q = (e.personas || []).find(x => x.persona_id === yo(ctx));
  if (!q) throw { falta: 'horas/horas', motivo: 'sin ficha de horas' };
  return {
    valor: fmt.num(q.horas?.ayer, 1), unidad: 'h ayer', estado: q.horas?.no_imputa ? '' : n0(q.horas?.ayer) ? 'verde' : 'ambar',
    motivo: q.horas?.motivo || 'Solo un aviso (D-27).', filas: (q.horas?.dias_sin_imputar_5 || []).map(f => ({ texto: `${diaCorto(f)} sin imputar`, estado: 'ambar', icono: 'clock' })),
    frescura: fresco('ClickUp · horas', e._meta?.corte_horas), medible: 'medias',
  };
});

// ------------------------------------------------------------- Setters (los datos ya llegan solo con lo suyo)
const sdat = (ctx, D) => { const s = D.dato('ventas_ro/setters'); const k = miSetter(ctx); const f = x => !k || x.setter === k; return { s, f, k }; };
const contacto = x => `${x.nombre_m || '—'}${x.despacho_m ? ` (${x.despacho_m})` : ''}`;
def('setter_llamar', ['ventas_ro/setters'], (ctx, D) => {
  const { s, f } = sdat(ctx, D);
  const l = (s.leads || []).filter(x => f(x) && n0(x.intentos) === 0).sort((a, b) => String(b.entro).localeCompare(String(a.entro)));
  return {
    valor: l.length, unidad: 'leads sin ninguna llamada', estado: l.length ? 'rojo' : 'verde',
    motivo: 'El más nuevo arriba. Bien si el primer intento llega en menos de 5 minutos.',
    filas: l.map(x => ({ texto: contacto(x), extra: `entró ${cuandoTxt(x.entro)}${x.motivo ? ' · ' + x.motivo : ''}`, estado: 'rojo', icono: 'phone', href: x.ghl })),
    vacio: { titulo: 'Todos llamados', tono: 'celebrar' }, frescura: fresco('GoHighLevel de RO', s), medible: 'hoy',
    primero: l.slice(0, 1).map(x => ({ peso: 4, icono: 'phone', motivo: `Llamar ya · ${contacto(x)}`, detalle: `Entró ${cuandoTxt(x.entro)}. ${x.motivo || ''}`, href: x.ghl, abrirEn: 'GHL', clave: `lead:${x.id}` })),
  };
});
def('setter_segundas', ['ventas_ro/setters'], (ctx, D) => {
  const { s, f } = sdat(ctx, D);
  const l = (s.leads || []).filter(x => f(x) && x.segunda_vence).sort((a, b) => String(a.segunda_vence).localeCompare(String(b.segunda_vence)));
  return {
    valor: l.length, unidad: 'segundas llamadas que vencen', estado: l.length ? 'ambar' : 'verde', motivo: 'Segunda llamada en 48 h o menos.',
    filas: l.map(x => ({ texto: contacto(x), extra: `vence ${cuandoTxt(x.segunda_vence)} · ${x.intentos} intentos`, estado: 'ambar', icono: 'clock', href: x.ghl })),
    vacio: { titulo: 'Ninguna segunda pendiente', tono: 'celebrar' }, frescura: fresco('GoHighLevel de RO', s), medible: 'hoy',
  };
});
def('setter_citas', ['ventas_ro/setters'], (ctx, D) => {
  const { s, f } = sdat(ctx, D);
  const l = (s.citas || []).filter(x => f(x) && !x.confirmada_tel);
  return {
    valor: l.length, unidad: 'citas por confirmar', estado: l.length ? 'ambar' : 'verde', motivo: 'Confirmar por teléfono 24-48 h antes.',
    filas: l.map(x => ({ texto: contacto(x), extra: `${x.dia || ''} ${horaCorta(x.cuando)}`, estado: 'ambar', icono: 'cal', href: x.ghl })),
    vacio: { titulo: 'Todas confirmadas', tono: 'celebrar' }, frescura: fresco('GoHighLevel de RO', s), medible: 'hoy',
  };
});
def('setter_pasadas', ['ventas_ro/setters'], (ctx, D) => {
  const { s, f } = sdat(ctx, D);
  const l = (s.pasadas || []).filter(f);
  return {
    valor: l.length, unidad: 'sin resultado marcado', estado: l.length ? 'rojo' : 'verde', motivo: 'Se marca el mismo día (D-66): vino, no vino o reprogramada.',
    filas: l.map(x => ({ texto: contacto(x), extra: `${cuandoTxt(x.cuando)} · ${x.etapa}`, estado: 'rojo', icono: 'flag', href: x.ghl })),
    vacio: { titulo: 'Todo marcado', tono: 'celebrar' }, frescura: fresco('GoHighLevel de RO', s), medible: 'hoy',
  };
});
def('setter_marcador', ['ventas_ro/setters'], (ctx, D) => {
  const { s, f } = sdat(ctx, D);
  const l = (s.marcador || []).filter(f);
  const hoy = l.find(x => x.periodo === 'hoy') || {};
  return {
    valor: fmt.num(hoy.citas), unidad: 'citas hoy', estado: n0(hoy.citas) >= 2 ? 'verde' : n0(hoy.citas) === 1 ? 'ambar' : 'gris',
    motivo: 'Marcaciones, conversaciones con sentido (bien ≥ 17 %) y citas (bien ≥ 2 al día). Solo los setters ven los marcadores (D-83).',
    filas: l.map(x => ({ texto: `${x.periodo === 'hoy' ? 'Hoy' : 'Esta semana'}${s.setters?.length > 1 && !miSetter(ctx) ? ` · ${x.setter}` : ''}`, extra: `${x.marcaciones} marcaciones · ${x.conversaciones} conversaciones · ${x.citas} citas`, estado: 'gris', icono: 'medidor' })),
    frescura: fresco('Zadarma + GHL', s), medible: 'hoy',
  };
});
def('setter_perdidas', ['ventas_ro/setters'], (ctx, D) => {
  const { s, f } = sdat(ctx, D);
  const l = (s.perdidas || []).filter(x => !x.setter || f(x));
  return {
    valor: l.length, unidad: 'llamadas perdidas', estado: l.length ? 'ambar' : 'verde', motivo: 'También las de números sin ficha en GoHighLevel.',
    filas: l.map(x => ({ texto: `${x.tel_m}${x.sin_ficha ? ' · sin ficha' : ''}`, extra: cuandoTxt(x.cuando), estado: x.sin_ficha ? 'rojo' : 'ambar', icono: 'phone', href: x.ghl })),
    vacio: { titulo: 'Ninguna perdida', tono: 'celebrar' }, frescura: fresco('Zadarma', s), medible: 'hoy',
  };
});
def('setter_informe', ['ventas_ro/setters'], (ctx, D) => {
  const { s } = sdat(ctx, D);
  return {
    valor: null, unidad: '', estado: 'gris', motivo: 'Cada tarde, en tu pantalla de setter: lo que has hecho y lo que queda.',
    filas: [], vacio: { titulo: 'Se escribe en «Mi día del setter»', texto: 'El formulario de fin de día vive allí y queda en el rastro.', quien: 'Tú' },
    frescura: fresco('Mi día del setter', s), medible: 'no', medibleDetalle: 'Formulario local',
  };
});

// ------------------------------------------------------------- Ventas de RO (Tomás como closer)
const vro = D => D.dato('ventas_ro/ventas_ro');
// R13: las reuniones ya pasadas (`pasada` del dato, o su hora + 45 min ya cumplida) no suben a «Lo primero hoy»;
// en la lista salen con su resultado (`celebrada` · `no_se_presento` · `sin_marcar` → «apunta si se celebró»).
const RES_REU = { celebrada: ['celebrada', 'verde'], no_se_presento: ['no se presentó', 'rojo'], sin_marcar: ['apunta si se celebró', 'ambar'] };
const reuPasada = x => x.pasada === true || (() => { const d = fecha(x.cuando); return d ? d.getTime() + 45 * 60000 < Date.now() : false; })();
def('vro_hoy', ['ventas_ro/ventas_ro'], (ctx, D) => {
  const v = vro(D); const l = (v.hoy || []).slice().sort((a, b) => String(a.cuando).localeCompare(String(b.cuando)));
  const quedan = l.filter(x => !reuPasada(x)); const sinMarcar = l.filter(x => reuPasada(x) && (x.resultado || 'sin_marcar') === 'sin_marcar');
  return {
    valor: quedan.length, unidad: quedan.length === 1 ? `reunión por delante · ${l.length} hoy` : `reuniones por delante · ${l.length} hoy`, estado: sinMarcar.length ? 'ambar' : '',
    motivo: `Con la ficha del setter: cinco filtros, notas y la grabación de la cualificación.${sinMarcar.length ? ` ${plural(sinMarcar.length, 'reunión')} ya pasada${sinMarcar.length === 1 ? '' : 's'}: apunta si se celebró.` : ''}`,
    filas: [...quedan, ...l.filter(reuPasada)].map(x => {
      const pas = reuPasada(x); const r = pas ? (RES_REU[x.resultado] || RES_REU.sin_marcar) : null;
      return { texto: `${horaCorta(x.cuando)} · ${contacto(x)}`, extra: `${x.calendario} · ${x.segunda ? 'segunda' : 'primera'} · ${x.setter_alias || 'sin setter'}${r ? ` · ${r[0]}` : ''}`, estado: r ? r[1] : 'gris', icono: 'video', href: x.ghl };
    }),
    vacio: { titulo: 'Sin reuniones hoy' }, frescura: fresco('GoHighLevel de RO', v), medible: 'hoy',
    primero: quedan.slice(0, 1).map(x => ({ peso: 2.4, icono: 'video', motivo: `Reunión ${horaCorta(x.cuando)} · ${contacto(x)}`, detalle: `${x.calendario} · ${x.etapa}`, href: x.ghl, abrirEn: 'GHL', clave: `reu:${x.id}` })),
  };
});
def('vro_propuestas', ['ventas_ro/ventas_ro'], (ctx, D) => {
  const v = vro(D); const l = (v.propuestas || []).filter(x => (!x.abierta && x.dias >= 3) || x.dias >= 7).sort((a, b) => b.dias - a.dias);
  return {
    valor: l.length, unidad: `de ${v.propuestas?.length || 0} propuestas`, estado: l.length ? 'ambar' : 'verde', motivo: 'Sin abrir a las 72 h o sin respuesta a los 7 días.',
    filas: l.map(x => ({ texto: x.nombre_m, extra: `${x.dias} días · ${x.abierta ? 'abierta' : 'sin abrir'} · ${eurG(x.cuota_mensual)}/mes`, estado: x.dias >= 14 ? 'rojo' : 'ambar', icono: 'doc', href: x.ghl })),
    frescura: fresco('GoHighLevel de RO', v), medible: 'hoy',
  };
});
def('vro_contratos', ['ventas_ro/ventas_ro'], (ctx, D) => {
  const v = vro(D); const l = (v.contratos || []).slice().sort((a, b) => b.dias - a.dias);
  return {
    valor: l.length, unidad: 'contratos sin firmar', estado: l.length ? 'ambar' : 'verde', motivo: 'Con el día de la secuencia de urgencia (7 días).',
    filas: l.map(x => ({ texto: x.nombre_m, extra: `día ${x.dias} · ${x.abierta ? 'abierto' : 'sin abrir'} · ${eurG(x.cuota_mensual)}/mes`, estado: x.dias > 7 ? 'rojo' : 'ambar', icono: 'editar', href: x.ghl })),
    frescura: fresco('GoHighLevel de RO + Sign', v), medible: 'hoy',
  };
});
def('vro_embudo', ['ventas_ro/ventas_ro'], (ctx, D) => {
  const v = vro(D); const m = v.meses?.[mesActual()] || {};
  const [aH, mH, dH] = hoyISO().split('-').map(Number); const dias = new Date(Date.UTC(aH, mH, 0)).getUTCDate();   // L-19: hoy de Madrid
  const ritmo = Math.round((n0(v.objetivo_firmados_mes) * dH) / dias * 10) / 10;
  return {
    valor: fmt.num(m.firmados), unidad: `firmados · ritmo ${fmt.num(ritmo, 1)} de ${v.objetivo_firmados_mes}`, estado: n0(m.firmados) >= ritmo ? 'verde' : n0(m.firmados) >= ritmo * 0.85 ? 'ambar' : 'rojo',
    motivo: 'Citas → celebradas → propuesta → firmado, frente al objetivo del mes. Bien ≥ 100 % del ritmo · vigilar 85-99 %.',
    extra: embudoBarras([{ etiqueta: 'Citas', valor: m.citas, icono: 'cal' }, { etiqueta: 'Celebradas', valor: m.celebradas, icono: 'video' }, { etiqueta: 'Propuestas', valor: m.propuestas, icono: 'doc' }, { etiqueta: 'Firmados', valor: m.firmados, icono: 'editar', estado: 'verde' }]),
    filas: [], frescura: fresco('GoHighLevel de RO', v), medible: 'hoy',
  };
});
def('vro_costes', ['ventas_ro/ventas_ro'], (ctx, D) => {
  const v = vro(D);
  const fila = (k, nombre) => { const m = v.meses?.[k] || {}; const cc = m.citas ? m.inversion / m.citas : null; const cf = m.firmados ? m.inversion / m.firmados : null; return { m, cc, cf, nombre }; };
  const a = fila(mesActual(), nombreMesActual()), b2 = fila(mesAnterior(), MESES[Number(mesAnterior().slice(5)) - 1]);
  const ref = a.cf !== null ? a : b2;
  return {
    valor: eurG(ref.cf), unidad: `por cliente (${ref.nombre})`, estado: colorCifra('coste_cliente', ref.cf),
    motivo: 'Por cliente: bien ≤ 700 € (D-13). Por cita reservada: bien ≤ 40 €.',
    filas: [a, b2].map(x => ({ texto: x.nombre[0].toUpperCase() + x.nombre.slice(1), extra: `${eurG(x.cc)} por cita · ${eurG(x.cf)} por cliente`, estado: x.cc === null ? 'gris' : x.cc <= 40 ? 'verde' : x.cc <= 60 ? 'ambar' : 'rojo', icono: 'euro' })),
    frescura: fresco('Meta de RO + GHL', v), medible: 'hoy',
  };
});
def('vro_huecos', ['ventas_ro/ventas_ro'], (ctx, D) => {
  const v = vro(D); const hu = v.huecos || {}; const l = Object.entries(hu.por_dia || {});
  return {
    valor: suma(l, x => x[1]), unidad: `huecos de ${hu.calendario || '45 min'} · ${hu.citas_ya ?? '—'} citas ya`, estado: '',
    motivo: 'Huecos libres en las próximas dos semanas frente a las citas que hacen falta (bien si se usa ≤ 80 %).',
    filas: l.map(([d, n]) => ({ texto: diaCorto(d), extra: plural(n, 'hueco'), estado: n ? 'verde' : 'gris', icono: 'cal' })),
    frescura: fresco('Calendario de RO', v), medible: 'hoy',
  };
});
def('vro_bajas', ['ventas_ro/ventas_ro'], (ctx, D) => {
  const v = vro(D); const b2 = v.bajas_tempranas || {};
  return {
    valor: b2.n ?? 0, unidad: `de ${b2.firmados_desde_agosto ?? '—'} firmados desde agosto`, estado: n0(b2.n) >= 2 ? 'rojo' : n0(b2.n) ? 'ambar' : 'verde',
    motivo: 'Bajas en los primeros 90 días de clientes que vendiste. Bien 0 · vigilar 1 · crítico 2 o más al trimestre.',
    filas: (b2.detalle || []).map(x => ({ texto: x.cliente, extra: x.mes, estado: 'ambar', icono: 'baja' })),
    frescura: fresco('Libro de bajas', b2.libro_leido || v), medible: 'medias',
  };
});

// ------------------------------------------------------------- Outreach
const outr = D => D.dato('ventas_ro/outreach');
def('out_sin_dueno', ['ventas_ro/outreach'], (ctx, D, b, extra) => {
  const o = outr(D);
  const asignadas = new Set((extra.accionesProspeccion || []).filter(a => a.tipo === 'asignar_respuesta' || a.tipo === 'dueno').map(a => String(a.objeto)));
  const l = (o.respuestas || []).filter(x => !x.dueno && !asignadas.has(x.id)).sort((a, b2) => String(b2.fecha).localeCompare(String(a.fecha)));
  return {
    valor: l.length, unidad: 'respuestas sin dueño', estado: l.length ? 'rojo' : 'verde', motivo: 'Las positivas arriba, con reloj de 24 h.',
    filas: l.map(x => ({ texto: `${x.campana} · ${x.nombre_m}`, extra: `${cuandoTxt(x.fecha)} · ${x.clase}`, estado: edadH(x.fecha) > 24 ? 'rojo' : 'ambar', icono: 'chat', href: '#/prospeccion' })),
    vacio: { titulo: 'Todas tienen dueño', tono: 'celebrar' }, frescura: fresco('Snov.io', o), medible: 'medias',
    primero: l.slice(0, 1).map(x => ({ peso: 2.6, icono: 'chat', motivo: `${plural(l.length, 'respuesta')} sin dueño`, detalle: `La más reciente: ${x.campana} (${cuandoTxt(x.fecha)}).`, ruta: 'prospeccion', clave: `resp:${x.id}` })),
  };
});
def('out_positivas', ['ventas_ro/outreach'], (ctx, D) => {
  const o = outr(D);
  const pos = (o.respuestas || []).filter(x => /positiv|interes/i.test(x.clase || ''));
  return {
    valor: pos.length, unidad: `positivas · ${o.ro?.en_ghl_origen_outreach ?? 0} con origen outreach en GHL`, estado: pos.length && !o.ro?.en_ghl_origen_outreach ? 'ambar' : '',
    motivo: 'El cruce con GoHighLevel es por el origen del contacto, que hoy nadie marca.',
    filas: pos.map(x => ({ texto: `${x.campana} · ${x.nombre_m}`, extra: cuandoTxt(x.fecha), estado: 'ambar', icono: 'plug', href: '#/prospeccion' })),
    vacio: { titulo: 'Sin positivas clasificadas', texto: 'Las respuestas se clasifican en Prospección.' }, frescura: fresco('Snov.io', o), medible: 'medias',
  };
});
def('out_salud', ['ventas_ro/outreach'], (ctx, D) => {
  const o = outr(D);
  return {
    valor: o.snov?.activas ?? null, unidad: 'campañas activas en Snov.io', estado: '',
    motivo: 'Rebotes y quejas por spam no salen todavía por la API de Snov.io; buzones y LinkedIn en pausa, con la hoja declarada.',
    filas: (o.avisos || []).map(a => ({ texto: a, estado: 'ambar', icono: 'alert' })), frescura: fresco('Snov.io', o), medible: 'medias',
  };
});
def('out_campanas', ['ventas_ro/outreach'], (ctx, D) => {
  const o = outr(D); const l = (o.snov?.campañas || []).filter(c => c.estado === 'Active').sort((a, b) => n0(b.respuestas_30d) - n0(a.respuestas_30d));
  return {
    valor: l.length, unidad: `activas · ${o.snov?.activas_ro ?? 0} de RO`, estado: '', motivo: 'Lotes que salen hoy y respuestas de 30 días por campaña.',
    filas: l.map(c => ({ texto: c.nombre, extra: `${fmt.num(c.respuestas_30d)} respuestas en 30 días · ${c.frente}`, estado: n0(c.respuestas_30d) ? 'verde' : 'gris', icono: 'send', href: '#/prospeccion' })),
    frescura: fresco('Snov.io', o), medible: 'hoy',
  };
});
def('out_hoja', ['ventas_ro/outreach'], (ctx, D) => {
  const o = outr(D); const lunes = hoyDia().getDay() === 1;
  return {
    valor: null, unidad: '', estado: lunes ? 'ambar' : 'gris', motivo: lunes ? 'Hoy es lunes: toca la hoja semanal declarada (D-71).' : 'La hoja semanal declarada se rellena los lunes (D-71).',
    filas: [], vacio: { titulo: lunes ? 'Rellena la hoja de esta semana' : 'Nada hasta el lunes', texto: 'Se rellena en Prospección y outreach.', quien: 'Outreach' },
    frescura: fresco('Prospección', o), medible: 'no', medibleDetalle: 'Hoja declarada',
  };
});

// ============================================================ EL NÚMERO QUE MANDA
// NUMERO[calculo](ctx, D) → { valor, unidad, estado, comparacion, contexto, frescura, usa }
export const NUMERO = {};
const num = (id, usa, f) => { NUMERO[id] = { usa, hacer: f }; };
num('fase2', [], () => ({ fase2: true }));
// R13 (outreach): el número que manda de Eulimar deja de ser «Fase 2». Es lo que hoy se puede medir con Snov.io:
// respuestas de prospección de 30 días que nadie ha clasificado (positiva, no, más tarde…), con las reuniones conseguidas
// al lado (contactos con origen outreach en GoHighLevel; hoy nadie marca ese origen, y se dice).
num('out_por_clasificar', ['ventas_ro/outreach'], (ctx, D) => {
  const o = D.dato('ventas_ro/outreach'); const r = o.respuestas || [];
  const sin = r.filter(x => !x.dueno && /sin clasificar/i.test(x.clase || 'sin clasificar'));
  const viejas = sin.filter(x => edadH(x.fecha) > 24).length; const hoy = sin.filter(x => String(x.fecha).slice(0, 10) === hoyISO()).length;
  const reu = o.ro?.en_ghl_origen_outreach;
  return { valor: fmt.num(sin.length), unidad: `de ${fmt.num(r.length)} respuestas de 30 días`, estado: viejas ? 'rojo' : sin.length ? 'ambar' : 'verde',
    comparacion: { texto: `${plural(hoy, 'nueva')} hoy · ${plural(viejas, 'respuesta')} con más de 24 h` },
    contexto: `Reuniones conseguidas por outreach: ${reu ? fmt.num(reu) : 'ninguna medida'} (contactos con origen outreach en GoHighLevel${reu ? '' : '; hoy nadie marca ese origen'}). Clasifica cada respuesta en Prospección: las positivas pasan a reunión. ${o.snov?.activas ?? 0} campañas activas en Snov.io.`,
    frescura: fresco('Snov.io', o) };
});
/** V2 (M1): color del beneficio según la TRAYECTORIA (catálogo: verde en la trayectoria · ámbar 10-25 % por debajo · rojo
 *  más de 25 % por debajo o negativo). Sin curva de trayectoria cargada, la del mes es el plan del mes, y se juzga el beneficio
 *  contando el gasto sin factura (el honesto): positivo con factura y negativo de verdad no sale en verde. */
function colorTrayectoria(n) {
  const real = n.beneficio_real ?? n.beneficio; const plan = n.plan_res;
  if (real === undefined || real === null) return 'gris';
  if (real < 0) return 'rojo';
  if (plan === undefined || plan === null || plan <= 0) return 'verde';
  return real >= plan ? 'verde' : real >= plan * 0.75 ? 'ambar' : 'rojo';
}
num('beneficio_mes', ['finanzas/finanzas', 'finanzas/direccion'], (ctx, D) => {
  const { n, nombreMes, ant } = beneficio(D);
  const acu = acumulado(D);
  const norte = n.objetivo_norte;
  return { titulo: `Beneficio de ${nombreMes}`, valor: eurG(n.beneficio), unidad: '', estado: colorTrayectoria(n),
    comparacion: ant ? { delta: Math.round(n.beneficio - ant.bai), unidad: ' €', texto: `frente a ${MESES[Number(ant.m.slice(5)) - 1]}` } : null,
    contexto: `Con el gasto sin factura: ${eurG(n.beneficio_real)}.${norte ? ` A ${eurG(norte - n.beneficio)} del norte (${eurG(norte)} al mes a final de 2027).` : ''}`,
    detalle: `${acu ? `Beneficio ${acu.texto}: ${eurG(acu.bai)}. ` : ''}Gasto sin factura de ${nombreMes}: ${eurG(n.sin_factura)}. Plan del mes: ${eurG(n.plan_res)}. Último mes cerrado: el mismo número que Finanzas. El color sale de la trayectoria (el plan del mes) con el gasto sin factura.`,
    frescura: fresco('Holded', D.dato('finanzas/finanzas')) };
});
num('beneficio_pct', ['finanzas/finanzas', 'finanzas/direccion'], (ctx, D) => {
  const k = fdir(D).kpi || {}; const s = k.bai_serie || [];
  return { valor: fmt.pct(k.bai), unidad: 'últimos 6 meses', estado: k.bai >= 20 ? 'verde' : k.bai >= 0 ? 'ambar' : 'rojo', comparacion: s.length > 1 ? { delta: Math.round((s[s.length - 1] - s[s.length - 2]) * 10) / 10, unidad: ' pt', dec: 1, texto: 'el último mes frente al anterior' } : null,
    contexto: 'Solo «Bien» está firmado (≥ 20 %). Margen bruto ' + fmt.pct(k.mb) + '.', frescura: fresco('Holded', D.dato('finanzas/finanzas')) };
});
num('cuota_cobrada', ['finanzas/finanzas'], (ctx, D) => {
  const ct = fadm(D).cuota_tres || {}; const antes10 = hoyDia().getDate() < 10;
  return { valor: fmt.pct(ct.cobrado_pct), unidad: 'de lo facturado', estado: antes10 ? 'gris' : semaforo(ct.cobrado_pct, { verde: 95, ambar: 85 }),
    comparacion: { texto: `septiembre: ${fmt.pct(ct.cobrado_pct_sep)}` }, contexto: antes10 ? 'Se juzga el día 10; hoy es orientativo (el cargo SEPA entra el día 2).' : 'Bien ≥ 95 % · vigilar 85-95 %.', frescura: fresco('Holded', D.dato('finanzas/finanzas')) };
});
num('altas_en_plazo', ['nuevos/nuevos'], (ctx, D) => {
  // verdad única: encendido = { dia, estado } (en_plazo · en_limite · tarde · sin_encender_fuera_de_plazo · pendiente_en_plazo)
  const n = D.dato('nuevos/nuevos');
  const est = (n.altas || []).map(a => verdad(ctx, a.cliente_id)?.encendido?.estado).filter(Boolean);
  if (!est.length) { const e = n.resumen?.en_plazo_dia12 || {}; return { valor: `${e.si ?? '—'} de ${e.de ?? '—'}`, unidad: `(${fmt.pct(e.pct)})`, estado: n0(n.resumen?.fuera_de_plazo) ? 'rojo' : 'verde', contexto: 'Encendido el día 10, límite 12, desde el alta del contrato.', frescura: fresco('Sign + Meta', n) }; }
  const juz = est.filter(x => x !== 'pendiente_en_plazo');
  const ok = juz.filter(x => x === 'en_plazo').length, lim = juz.filter(x => x === 'en_limite').length, fuera = juz.filter(x => x === 'sin_encender_fuera_de_plazo' || x === 'tarde').length;
  // V2 (B-M5): por qué 8, 16 y 17 en una línea: altas de los últimos 90 días → con dato de encendido → ya juzgables
  const total = (n.altas || []).length; const sinDato = total - est.length;
  return { valor: `${ok} de ${juz.length}`, unidad: `encendidas el día 10 (${fmt.pct(pct(ok, juz.length))})`, estado: fuera ? 'rojo' : lim ? 'ambar' : juz.length ? 'verde' : 'gris',
    contexto: `De ${plural(total, 'alta')} en curso, ${juz.length} ya se pueden juzgar (se encendieron o pasaron el día 12) y ${est.length - juz.length} siguen en plazo${sinDato ? `; ${sinDato} sin dato de encendido` : ''}. De las ${juz.length}: ${juz.filter(x => x === 'sin_encender_fuera_de_plazo').length} sin encender pasado el día 12, ${juz.filter(x => x === 'tarde').length} encendidas tarde y ${lim} en el límite (días 11-12).`,
    frescura: fresco('Sign + Meta', n) };
});
num('garantia', ['nuevos/nuevos'], (ctx, D) => {
  const n = D.dato('nuevos/nuevos'); const g = (n.altas || []).map(a => (a.hitos || []).find(x => x.id === 'garantia')).filter(x => x && x.estado !== 'no_aplica');
  const ok = g.filter(x => x.estado === 'hecho').length; const juz = g.filter(x => ['hecho', 'tarde'].includes(x.estado)).length;
  // R12 (A-A5): sin ninguna alta juzgable no hay cifra; se dice por qué y cuándo llega, nunca un «—» suelto
  const sinLlegar = g.length - juz;
  return { valor: juz ? fmt.pct(pct(ok, juz)) : null, unidad: juz ? `${ok} de ${juz}` : '', estado: juz ? (ok === juz ? 'verde' : 'rojo') : 'gris',
    contexto: juz ? `${plural(g.length, 'alta')} con garantía firmada; ${sinLlegar} todavía sin llegar al día 30. Las demás no la firmaron.`
      : g.length ? `Todavía no hay ninguna alta que juzgar: ${plural(g.length, 'alta tiene', 'altas tienen')} la garantía firmada y ${sinLlegar === 1 ? 'aún no ha llegado' : 'aún no han llegado'} al día 30. La cifra sale ese día. Las demás altas no firmaron la garantía.`
        : 'Ninguna alta de los últimos 90 días tiene la garantía firmada: no hay nada que medir.',
    frescura: fresco('Sign + GHL', n) };
});
num('alerta_sin_plan', ['personas_m20/equipo'], (ctx, D) => {
  const e = equipo(D); const { en, sin, vencidas } = alertaPersonas(e);
  return { valor: vencidas.length, unidad: `de ${sin.length} en alerta sin plan`, estado: vencidas.length ? 'rojo' : sin.length ? 'ambar' : 'verde',
    contexto: `${en.length} en alerta: ${sin.length} sin plan todavía y ${en.length - sin.length} con plan (como Personas). Cuentan aquí cuando pasan 7 días sin plan.`, frescura: fresco('Personas en alerta', e) };
});
num('cartera_salud', ['verdad/clientes'], (ctx, D) => {
  const l = ctx.clientes.filter(c => c.enCartera);
  const registrados = l.filter(c => { const s = verdad(ctx, c.id)?.salud; return Number.isFinite(s) && s >= 0; });
  return { titulo: 'Índices registrados · provisional', valor: registrados.length, unidad: `de ${l.length} clientes`, estado: 'gris',
    contexto: 'Cobertura de índices registrados en la copia. No evalúa salud, desempeño ni cumplimiento y no aplica el umbral anterior de 60.',
    frescura: fresco('Verdad única de clientes', D.opcional('verdad/clientes')) };
});
function citaObjetivo(ctx,D,todas){
 const cap=D.dato('captacion/captacion'),l=clientesDia314(ctx,cap.clientes).filter(c=>c.meta_activa&&(todas||c.equipo?.trafficker===yo(ctx)));
 const refs=l.filter(c=>c.dinero&&typeof c.coste_por_cita?.coste_por_cita_14d==='number'&&c.coste_por_cita.coste_por_cita_14d>0);
 return {valor:null,unidad:'Coste por cita por confirmar',estado:'gris',contexto:`${refs.length} referencias anteriores en ${l.length} cuentas. Sin cohorte enlazada de gasto y citas no se evalúa el coste ni cumplimiento del objetivo.`,frescura:fresco('Meta + GoHighLevel',cap)};
}
num('resultados_cartera', ['captacion/captacion','crm/crm'], (ctx,D)=>{
 const cap=D.dato('captacion/captacion'),cartera=silla(ctx,'account')||ctx.carteraIds,hoy=ctx.hoy||hoyISO();
 const act=clientesDia314(ctx,cap.clientes).filter(c=>cartera.has(c.cliente_id)&&c.meta_activa),ms=act.map(c=>resultadosFilaDia314(c,cap,hoy).cpl),evaluables=ms.filter(m=>m.evaluable),ok=evaluables.filter(m=>m.real<=m.objetivo).length;
 return {valor:evaluables.length?fmt.pct(pct(ok,evaluables.length)):null,unidad:`${ok} de ${evaluables.length} cuentas comparables con objetivo propio`,estado:evaluables.length?ok===evaluables.length?'verde':'ambar':'gris',
 contexto:`CPL observado frente a objetivo vigente en semana cerrada. ${act.length-evaluables.length} cuentas pendientes de medir o confirmar objetivo. No acredita cualificación ni ventas; no aplica el umbral general anterior50/70%.`,frescura:fresco('Meta',cap)};
});
num('cita_objetivo_mias', ['captacion/captacion'], (ctx, D) => citaObjetivo(ctx, D, false));
num('cita_objetivo_casa', ['captacion/captacion'], (ctx, D) => citaObjetivo(ctx, D, true));
num('asistencia_mia', ['crm/crm'], (ctx, D) => {
  const crm=D.dato('crm/crm');
  const propias=clientesDia314(ctx,crm.subcuentas).filter(s=>s.especialista_id===yo(ctx));
  const r=secundariosCRM317(ctx,{...crm,subcuentas:propias});
  return {valor:r.asistencia===null?null:fmt.pct(r.asistencia),unidad:`${r.asistencia_base} citas con resultado · 30 días`,estado:'gris',
    contexto:`${r.asistencia_subcuentas} subcuentas propias comparables de ${r.filas.length} autorizadas. Sólo citas con resultado registrado, no todas las agendadas ni conversión de leads. ${r.asistencia===null?'Sin base comparable suficiente; ausencia de registros no acredita ausencia de citas. ':''}Cobertura parcial; sin evaluación de rendimiento ni garantía contractual.`,frescura:fresco('GoHighLevel',crm)};
});
num('crm_verde', ['crm/crm'], (ctx, D) => {
  const crm=D.dato('crm/crm'),r=secundariosCRM317(ctx,crm),recientes=r.filas.filter(s=>s._medicionCRM?.fechaValida===true).length;
  return {valor:recientes?fmt.num(recientes):null,unidad:`subcuentas con lectura reciente de ${r.filas.length} autorizadas`,estado:'gris',
    contexto:`Cobertura de la copia CRM, no porcentaje de salud verde. ${recientes?'Revisa contactos, intentos y resultados de citas en las tablas autorizadas.':'Sin lectura reciente suficiente; no se interpreta como cero actividad ni ausencia de leads.'} Los objetivos históricos de asistencia/velocidad no evalúan rendimiento ni garantía contractual.`,frescura:fresco('GoHighLevel',crm)};
});
/** R12 (B-A06): el aviso de SEO, igual que en su pantalla, cuando SE Ranking deja de ver muchas palabras de golpe. */
function avisoSeRanking(l) {
  const des = suma(l, c => c.visibilidad?.desaparecen);
  const conGsc = l.filter(c => c.clics);
  const suben = conGsc.filter(c => n0(c.clics.var_mes) > 0).length;
  return des > 50 ? `Cuidado con el dato de SE Ranking: dejó de ver ${fmt.num(des)} palabras de golpe esta semana y los clics de Google suben en ${suben} de ${conGsc.length} clientes. La diferencia no identifica la causa: contrasta buscador, ubicación, dispositivo y fecha antes de tocar nada.` : null;
}
num('seo_verde', ['seo/seo'], (ctx, D) => {
  // R12 (B-A05): la misma cifra, base, umbral y sello que «Clientes en verde» de SEO, ficha y webs (medibles = sin los grises)
  const s = D.dato('seo/seo'); const l = s.clientes || [];
  const med = l.filter(c => c.estado !== 'gris'); const v = med.filter(c => c.estado === 'verde').length;
  const p = med.length ? Math.round((v / med.length) * 100) : null;
  const aviso = avisoSeRanking(l);
  // V2 (B-M8): con el dato de SE Ranking en duda (el mismo aviso que su pantalla), la cifra va en gris «dato en duda», no en rojo
  const R = s.resumen || {};
  const duda = !!(R.aviso_seranking || aviso);
  // el estado que pinta su pantalla (resumen.estado_mostrado: «gris» con el dato en duda) y su motivo, tal cual
  return { valor: p === null ? null : fmt.pct(p), unidad: `${v} de ${med.length}`, estado: p === null ? 'gris' : duda ? (R.estado_mostrado || 'gris') : semaforo(p, { verde: 80, ambar: 60 }), duda,
    contexto: `${duda ? `${R.motivo_medible || 'Dato en duda: compruébalo en Google antes de tocar nada.'} ` : ''}${med.filter(c => c.estado === 'rojo').length} en rojo y ${med.filter(c => c.estado === 'ambar').length} en ámbar; ${l.length - med.length} sin conectar no cuentan.${aviso && !R.motivo_medible ? ` ${aviso}` : ''}`,
    frescura: fresco('Search Console', s._meta?.gsc?.leido || s._meta?.generado) };
});
num('top5_mios', ['seo/seo'], (ctx, D) => {
  // R12 (B-A05/A06): la misma base y regla que «Palabras en el top 5» de su pantalla (sus clientes de SEO por asignación), con el aviso de SE Ranking
  const s = D.dato('seo/seo'); const mia = silla(ctx, 'seo');
  const l = (s.clientes || []).filter(c => c.seo_id === yo(ctx) || (mia && mia.has(c.cliente_id)));
  const hoy = suma(l, c => c.reparto?.top5?.hoy), mes = suma(l, c => c.reparto?.top5?.mes);
  const aviso = avisoSeRanking(l);
  const duda = !!(s.resumen?.aviso_seranking || aviso);   // V2 (B-M8): dato en duda → gris
  return { valor: fmt.num(hoy), unidad: `en top 5 · ${plural(l.length, 'cliente')}`, estado: !l.length || duda ? 'gris' : hoy >= mes ? 'verde' : mes - hoy <= 2 ? 'ambar' : 'rojo', duda, comparacion: { delta: hoy - mes, texto: 'frente a hace 30 días' },
    contexto: duda ? `Dato en duda: compruébalo en Google antes de tocar nada.${aviso ? ` ${aviso} La caída del top 5 puede no ser real.` : ''}` : 'Bien si sube o se mantiene el número en top 5 frente a hace 30 días.', frescura: fresco('SE Ranking', s._meta?.seranking?.leido || s._meta?.generado) };
});
num('webs_verde', ['seo/webs', 'seo/seo'], (ctx, D) => {
  // V2 (C-8): el número que manda de web es el de su pantalla de trabajo: «Webs que responden 60 de 64» (todas las webs, como
  // la guardia), con la misma regla «responde» del monitor (webs.json → responde / resumen.responden). Las suyas, al lado.
  const w = D.dato('seo/webs'); const r = w.resumen || {}; const todas = w.webs || [];
  const responde = x => (x.responde !== undefined ? !!x.responde : x.comprobacion?.estado >= 200 && x.comprobacion?.estado < 400);
  const n = r.responden ?? todas.filter(responde).length; const tot = r.webs ?? todas.length;
  const caidas = todas.filter(x => x.estado === 'rojo' && !responde(x));
  const mias = ctx.persona.puestos.includes('web') ? webs(ctx, D, { alcance: 'mio' }).l : null;
  return { titulo: 'Webs que responden', valor: `${n} de ${tot}`, unidad: 'webs responden desde RO', estado: caidas.length ? 'rojo' : 'verde',
    contexto: `${plural(caidas.length, 'caída', 'caídas')}${caidas.length ? ` (${caidas.slice(0, 4).map(x => x.nombre).join(', ')}${caidas.length > 4 ? ` y ${plural(caidas.length - 4, 'web más', 'webs más')}` : ''})` : ''}; ${r.rojo ?? '—'} en rojo y ${r.ambar ?? '—'} con aviso.${mias ? ` Tuyas: ${mias.filter(responde).length} de ${mias.length} responden.` : ''} Una comprobación desde la IP de RO; la disponibilidad desde fuera llega con el despliegue.`,
    frescura: fresco('Monitor desde RO', w._meta?.monitor?.leido) };
});
num('redes_14', ['redes/redes'], (ctx, D) => {
  // R12 (C-A2): sobre su cartera de redes de las asignaciones; los que no están en Metricool se dicen, no se esconden
  const esRedes = ctx.persona.puestos.includes('redes');
  const { r, l, fuera } = esRedes ? redes(ctx, D, { alcance: 'mio' }) : { r: D.dato('redes/redes'), l: D.dato('redes/redes').clientes || [], fuera: [] };
  const v = l.filter(c => c.estado_14 === 'verde').length;
  const nomF = fuera.map(id => nomCli(ctx, id) || id);
  return { valor: l.length ? fmt.pct(pct(v, l.length)) : null, unidad: `${v} de ${plural(l.length, 'cliente')} con calendario en Metricool`, estado: !l.length ? 'gris' : v === l.length ? 'verde' : 'rojo',
    contexto: `Un cliente con un hueco de ${r._meta?.hueco_dias || 4} días o más ya no cuenta.${fuera.length ? ` Tu cartera de redes tiene ${l.length + fuera.length} clientes: ${plural(fuera.length, 'no está', 'no están')} en Metricool y no se pueden medir (${nomF.slice(0, 4).join(', ')}${nomF.length > 4 ? ` y ${plural(nomF.length - 4, 'cliente más', 'clientes más')}` : ''}).` : ''}`,
    frescura: fresco('Metricool', r._meta?.leido_metricool) };
});
num('indice_piezas', ['produccion/produccion'], (ctx, D) => {
  const p = D.dato('produccion/produccion'); const r = p.anuncios_resumen || {};
  return { valor: null, unidad: '', estado: 'gris', contexto: `${r.con_autor ?? 0} de ${r.anuncios ?? '—'} anuncios llevan las iniciales del autor (D-43): sin ellas no se sabe qué pieza es tuya.`, frescura: fresco('Meta (anuncios)', r.hora || p) };
});
num('setter_celebradas', ['ventas_ro/setters'], (ctx, D) => {
  const { s, f } = sdat(ctx, D); const sem = (s.marcador || []).filter(x => f(x) && x.periodo === 'semana');
  return { valor: null, unidad: '', estado: 'gris', contexto: `Empezamos el lunes 5 de octubre. Esta semana: ${suma(sem, x => x.citas)} citas agendadas. Las celebradas cuentan cuando se marca «vino» en GHL (marcarlo desde aquí espera un permiso de GoHighLevel).`, frescura: fresco('GoHighLevel de RO', s) };
});
num('cierre_celebradas', ['ventas_ro/ventas_ro'], (ctx, D) => {
  const v = vro(D); const m = v.meses?.[mesActual()] || {}; const a = v.meses?.[mesAnterior()] || {};
  const usar = n0(m.celebradas) >= 5 ? m : a; const nombre = usar === m ? nombreMesActual() : MESES[Number(mesAnterior().slice(5)) - 1];
  const p = pct(n0(usar.firmados), n0(usar.celebradas));
  return { valor: fmt.pct(p), unidad: `${usar.firmados ?? 0} de ${usar.celebradas ?? 0} en ${nombre}`, estado: p === null ? 'gris' : semaforo(p, { verde: 33, ambar: 20 }),
    contexto: usar === m ? 'Bien ≥ 33 % · vigilar 20-32 % (D-63).' : `Este mes aún no hay 5 celebradas: se enseña ${nombre}. Bien ≥ 33 % · vigilar 20-32 % (D-63).`, frescura: fresco('GoHighLevel de RO', v) };
});

// ============================================================ A1 · «Lo mío» (43_IDEAS_MEJORA, 2-oct noche)
// UNA lista personal arriba de Mi día con lo que cada persona tiene que hacer HOY: sus alertas (definición única de
// Alertas + la cola viva, respetando «alerta_lote» y «alerta_posponer»), los correos sin contestar de su cartera, las
// piezas que le toca revisar (Producción › Por revisar), las menciones del chat sin leer y las decisiones que esperan su
// sí, más lo que los bloques suben como urgente. Sin duplicados: una alerta manda sobre cualquier otra fila del mismo
// objeto o del mismo tema; el resto, uno por objeto. Orden: vencido · hoy · esta semana · sin fecha, y dentro, lo grave.
// El trozo entre <lo-mio> y </lo-mio> es puro (sin imports ni ctx): pruebas_coherencia.py lo ejecuta en Chromium con
// los ficheros de alertas y comprueba que las alertas de «Lo mío» = el contador «mías» de Alertas y que no repite nada.
/** Ficheros que lee «Lo mío» además de los de los bloques (fuentes_mi_dia/resumen_mi_dia.py los mete en el resumen). */
export const LO_MIO_USA = ['bandeja/bandeja', 'produccion/produccion', 'decisiones/reloj'];
// <lo-mio>
// ------------------------------------------------- <contar> · copia LITERAL del bloque de modulos/alertas.js (prueba de coherencia)
// No se cambia aquí: la definición vive en fuentes_alertas/generar_alertas.py (DEFINICIONES y CONTADORES) y llega en
// D.definiciones y D.contadores_def. Esto solo la interpreta, igual que el generador. pruebas_coherencia.py ejecuta
// este bloque en el navegador con los ficheros y comprueba que da lo mismo que el generador y que Mi día.
function cumpleDef(defs, nombre, H, yo) {
  return ((defs[nombre] || {}).si || []).every(c => condDef(defs, c, H, yo));
}
function condDef(defs, c, H, yo) {
  if (c.length === 1) return cumpleDef(defs, c[0], H, yo);
  if (c[0] === 'alguna') return c[1].some(x => condDef(defs, x, H, yo));
  const [campo, op, v0] = c;
  const v = v0 === 'yo' ? yo : v0;
  const x = H[campo];
  if (op === '=') return x === v;
  if (op === '!=') return x !== v;
  if (op === 'en') return v.includes(x);
  if (op === '>') return (x || 0) > v;
  return false;
}
function cumpleTodas(defs, nombres, H, yo) { return nombres.every(d => cumpleDef(defs, d, H, yo)); }
// </contar>
const LM_DE_ACCION = { alerta_vista: 'vista', alerta_lo_tengo: 'lo_tengo', alerta_resuelta: 'resuelta', alerta_no_aplica: 'no_aplica', alerta_reabrir: 'nueva', alerta_posponer: 'pospuesta' };
const LM_DE_LOTE = { lo_tengo: 'lo_tengo', resuelta: 'resuelta', no_aplica: 'no_aplica', posponer: 'pospuesta' };
const lmFecha = s => (s ? (s instanceof Date ? s : (instanteRO(String(s)) || (/\d{2}:\d{2}/.test(String(s)) ? new Date(NaN) : new Date(String(s).replace(' ', 'T'))))) : null);   // L-18: sin zona = Madrid
/** Quién puede posponer o despachar en lote (la regla de Alertas y del generador): su cadena, su jefe, dirección u operaciones. */
function lmPuedeActuar(pid, a, personas) {
  const p = (personas || []).find(x => x.id === pid);
  return (a.escalado_cadena || []).includes(pid) || a.jefe_id === pid || !!(p && (p.puestos || []).some(x => x === 'direccion' || x === 'operaciones'));
}
/** Estado vivo de cada alerta, como la pantalla Alertas: lo pulsado aquí (local), la cola «acciones?modulo=alertas» si es
 *  posterior al fichero (con lote y posponer; nadie pospone ni despacha en lote alertas ajenas) o el fichero. */
function lmEstados(A, acciones, personas, local) {
  const porId = new Map((A.alertas || []).map(a => [a.id, a]));
  const gen = lmFecha(A.generado);
  const viva = new Map();
  for (const x of [...(acciones || [])].sort((p, q) => (Number(p.id) || 0) - (Number(q.id) || 0))) {
    if (x.modulo && x.modulo !== 'alertas') continue;
    const hora = new Date(String(x.creada).replace(' ', 'T') + 'Z');
    let vp = {};
    try { vp = typeof x.vista_previa === 'string' ? JSON.parse(x.vista_previa || '{}') || {} : x.vista_previa || {}; } catch { vp = {}; }
    const entradas = x.tipo === 'alerta_lote'
      ? (LM_DE_LOTE[vp.accion] ? (vp.ids || []).map(id => ({ id: String(id), estado: LM_DE_LOTE[vp.accion], lote: true })) : [])
      : (LM_DE_ACCION[x.tipo] ? [{ id: x.objeto, estado: LM_DE_ACCION[x.tipo] }] : []);
    for (const en of entradas) {
      const a = porId.get(en.id);
      if (!a) continue;
      if ((en.estado === 'pospuesta' || en.lote) && !lmPuedeActuar(x.quien, a, personas)) continue;
      if (en.estado === 'pospuesta') {
        const ha = lmFecha(vp.hasta);
        if (!ha || ha <= hora || ha - hora > (A.posponer_max_dias || 31) * 864e5) continue;
      }
      viva.set(en.id, { estado: en.estado, hora, hasta: en.estado === 'pospuesta' ? vp.hasta : null });
    }
  }
  const out = new Map();
  for (const a of porId.values()) {
    let e = local && local.get(a.id);
    if (!e) { const v = viva.get(a.id); e = v && (!gen || v.hora > gen) ? v : { estado: a.estado || 'nueva', hasta: (a.pospuesta && a.pospuesta.hasta) || null }; }
    out.set(a.id, e);
  }
  return out;
}
/** Lo pospuesto vuelve solo en su fecha; al volver, el plazo empieza de nuevo (como Alertas y el generador). */
const lmVivo = (e, ahora) => (e.estado === 'pospuesta' && e.hasta && lmFecha(e.hasta) <= ahora ? { ...e, estado: 'nueva', volvio: true } : e);
function lmVence(a, est) {
  const base = lmFecha(a.vence_antes || a.vence);
  if (!base) return null;
  if (est.hasta && a.plazo_h) { const v2 = new Date(lmFecha(est.hasta).getTime() + a.plazo_h * 36e5); return v2 > base ? v2 : base; }
  return base;
}
function lmNivel(a, est, ahora) {
  if (!['nueva', 'vista', 'reabierta'].includes(est.estado)) return 0;
  const v = lmVence(a, est);
  if (!v) return 0;
  const p = (a.plazo_h || 24) * 36e5;
  let n = 0;
  if (ahora >= v) n = 1;
  if (ahora - v >= p) n = 2;
  return Math.min(n, (a.escalado_cadena || []).length - 1);
}
/** Las alertas «mías» con la MISMA definición que Alertas (contadores_def.mias), con su estado vivo, su plazo y si te
 *  llegó escalada. ahora: el reloj (la prueba de coherencia usa la hora del fichero, como el generador). */
function alertasMias(A, acciones, { yo, personas = [], ahora = new Date(), local = null } = {}) {
  if (!A || !A.alertas) return [];
  const est = lmEstados(A, acciones, personas, local);
  const defs = A.definiciones || {};
  const mias = (A.contadores_def || {}).mias || ['abierta', 'mia'];
  return A.alertas.map(a => {
    const e = lmVivo(est.get(a.id), ahora);
    const nivel = lmNivel(a, e, ahora);
    const v = lmVence(a, e);
    const H = { estado: e.estado, gravedad: a.gravedad, dueno: a.dueno_id, responsable: (a.escalado_cadena || [])[nivel] || a.dueno_id, nivel, vencida: !!(v && v <= ahora) };
    return { a, est: e, H, vence: v, escaladaAMi: nivel > 0 && H.responsable === yo && a.dueno_id !== yo };
  }).filter(x => cumpleTodas(defs, mias, x.H, yo));
}
/** V2 (B-M10): temas y objetos de las alertas que la persona ha APARTADO (pospuestas hasta una fecha que aún no llega). La
 *  alarma de un bloque sobre el mismo cliente y motivo («Akua · alarma en su cuenta de Meta») tampoco sale en «Lo mío»: si no,
 *  posponer no serviría. → Set de claves «g:<tema>» y «o:<objeto>». */
function apartadasLoMio(A, acciones, { personas = [], ahora = new Date(), local = null } = {}) {
  const out = new Set();
  if (!A || !A.alertas) return out;
  const est = lmEstados(A, acciones, personas, local);
  for (const a of A.alertas) {
    const e = lmVivo(est.get(a.id), ahora);
    if (!e || e.estado !== 'pospuesta') continue;
    const t = temaAlerta(a); if (t) out.add(`g:${t}`);
    const o = objetoDe(a.ir); if (o) out.add(`o:${o}`);
  }
  return out;
}
/** El tema de una alerta, con la clave que usan los bloques de Mi día para lo mismo («correo-cli:gac», «dec:acc-12»…). */
const LM_TEMA = { acc_correos: 'correo-cli', acc_sin_agente: 'inc', acc_config: 'inc', dir_decision: 'dec', web_caida: 'web', web_spam: 'spam', seo_rojo: 'seo',
  alta_fuera_plazo: 'alta', pub_critico: 'cuenta', crm_sin_tocar: 'sintocar-cli', adm_impago: 'impago-cli', acc_critico: 'critico', rrhh_alerta: 'rrhh-persona' };
function temaAlerta(a) {
  const t = LM_TEMA[a.tipo];
  const resto = String(a.id).split(':').slice(1);
  if (!t) return null;
  if (t === 'inc') return `inc:${a.incidencia_id || resto[0]}`;
  if (t === 'dec') return `dec:${resto[0]}`;
  return `${t}:${a.cliente_id || resto[0]}`;
}
/** Objeto al que lleva un «Ir»: la ruta sin «#/», sin parámetros ni barra final («bandeja/t-RO-6590»). */
const objetoDe = ir => { if (!ir || !String(ir).startsWith('#/')) return null; try { return decodeURIComponent(String(ir).slice(2).split('?')[0]).replace(/\/+$/, ''); } catch { return String(ir).slice(2); } };
/** Tramo de plazo: 0 vencido · 1 hoy · 2 esta semana · 3 más adelante o sin fecha. */
function tramoPlazo(plazo, ahora) {
  if (!plazo) return 3;
  if (plazo <= ahora) return 0;
  const fin = instanteRO(`${diaRO(ahora)} 23:59:59.999`) || (() => { const d = new Date(ahora); d.setHours(23, 59, 59, 999); return d; })();   // L-18: el fin del día de Madrid
  if (plazo <= fin) return 1;
  return plazo - ahora <= 7 * 864e5 ? 2 : 3;
}
const LM_GRAV = { alta: 0, media: 1, baja: 2 };
const ordenLoMio = ahora => (x, y) => tramoPlazo(x.plazo, ahora) - tramoPlazo(y.plazo, ahora) || (LM_GRAV[x.grav] ?? 1) - (LM_GRAV[y.grav] ?? 1)
  || (x.plazo ? +x.plazo : 9e15) - (y.plazo ? +y.plazo : 9e15) || (y.peso || 0) - (x.peso || 0) || String(x.clave).localeCompare(String(y.clave));
/** Une las filas sin repetir: todas las alertas (cada una cuenta en Alertas) y, de lo demás, solo lo que no trate el mismo
 *  objeto o tema que algo ya dentro (la más urgente se queda). Devuelve { filas, quitadas }. */
function unirLoMio(filas, ahora = new Date()) {
  const vistos = new Set();
  const marcar = f => { vistos.add(`c:${f.clave}`); if (f.objeto) vistos.add(`o:${f.objeto}`); for (const g of f.grupos || []) if (g) vistos.add(`g:${g}`); };
  const repetida = f => vistos.has(`c:${f.clave}`) || (f.objeto && vistos.has(`o:${f.objeto}`)) || (f.grupos || []).some(g => g && vistos.has(`g:${g}`));
  const out = [];
  let quitadas = 0;
  for (const f of filas.filter(x => x.tipo === 'alerta')) { if (vistos.has(`c:${f.clave}`)) { quitadas++; continue; } out.push(f); marcar(f); }
  // las alertas pueden compartir objeto entre ellas (dos avisos distintos sobre la misma ficha): cuentan las dos
  for (const f of filas.filter(x => x.tipo !== 'alerta').sort(ordenLoMio(ahora))) { if (repetida(f)) { quitadas++; continue; } out.push(f); marcar(f); }
  return { filas: out.sort(ordenLoMio(ahora)), quitadas };
}
/** Comprobación que usan la pantalla (en desarrollo) y pruebas_coherencia.py: claves únicas y ningún objeto ni tema
 *  repetido fuera de las alertas. Devuelve la lista de repetidos (vacía = bien). */
function repetidosLoMio(filas) {
  const mal = [];
  const claves = new Set();
  const usados = new Map();
  for (const f of filas) {
    if (claves.has(f.clave)) mal.push(`clave ${f.clave}`);
    claves.add(f.clave);
    for (const k of [f.objeto ? `o:${f.objeto}` : null, ...(f.grupos || []).filter(Boolean).map(g => `g:${g}`)].filter(Boolean)) {
      const otro = usados.get(k);
      if (otro && !(otro.tipo === 'alerta' && f.tipo === 'alerta')) mal.push(`${k} en ${otro.clave} y ${f.clave}`);
      if (!otro || otro.tipo !== 'alerta') usados.set(k, f);
    }
  }
  return mal;
}
// </lo-mio>
export { alertasMias, apartadasLoMio, temaAlerta, objetoDe, tramoPlazo, ordenLoMio, unirLoMio, repetidosLoMio };

// ------------------------------------------------------------- A1 · las fuentes de «Lo mío» que no son alertas
/** Correos sin contestar de TU cartera (silla de account), con la regla de la pantalla Bandeja (sin automáticos, viejos ni
 *  lo ya despachado en la Bandeja), uno por cliente: el más antiguo abre el correo exacto y dice cuántos hay. */
export function correosLoMio(ctx, D, extra) {
  if (!D.opcional('bandeja/bandeja')) return [];
  const cart = silla(ctx, 'account');
  const { c } = bandejaComoPantalla(ctx, D, extra);
  const mios = c.filter(x => x.account_id === yo(ctx) || (x.cliente_id && cart?.has(x.cliente_id)));
  const porCli = new Map();
  for (const x of mios) { const k = x.cliente_id || `sin:${x.id}`; (porCli.get(k) || porCli.set(k, []).get(k)).push(x); }
  return [...porCli.values()].map(l => {
    const x = l.slice().sort((a, b) => n0(b.horas) - n0(a.horas))[0];
    return { x, n: l.length, quejas: l.filter(y => y.queja).length, espera: esperaTxt(x) };
  });
}
/** V2 · ¿Quién revisa una pieza en «revisión técnica»? La jefa del ÁREA del autor (reglas_permisos.json → revision_piezas.
 *  areas_tecnica: jefa_publicidad → trafficker; jefa_crm → especialista_ghl y outreach; jefa_seo → seo, ficha_google y web),
 *  o la jefa que el autor tiene de jefe directo: la MISMA regla que aplica servir.py (puede_revisar_pieza) al aprobar. Nunca
 *  las tres jefas a la vez. Una pieza sin autor de un área conocida, o cuyo autor es la propia jefa del área, va a
 *  operaciones (Mili). → { jefas: Set de ids, operaciones: bool }. Producción › Por revisar debe leer esta misma función. */
export function revisorTecnica(ctx, autores, regla = null) {
  const RP = REGLAS.revision_piezas || {};
  const areas = RP.areas_tecnica || {};
  const personas = ctx.datos?.personas || [];
  const puestosDe = id => personas.find(q => q.id === id)?.puestos || [];
  const jefasDe = j => personas.filter(q => (q.puestos || []).includes(j) && q.estado !== 'baja').map(q => q.id);
  const deRegla = regla?.puestos || Object.keys(areas);
  const jefas = new Set();
  for (const aid of autores || []) {
    if (!aid) continue;
    const pa = puestosDe(aid);
    const jefe = personas.find(q => q.id === aid)?.jefe || null;
    for (const j of deRegla) {
      const oficios = areas[j] || [];
      const delArea = pa.some(x => oficios.includes(x));
      const suJefa = jefe && puestosDe(jefe).includes(j) ? jefe : null;
      if (suJefa && suJefa !== aid) jefas.add(suJefa);
      else if (delArea) for (const q of jefasDe(j)) if (q !== aid) jefas.add(q);
    }
  }
  return { jefas, operaciones: !jefas.size };
}
/** Piezas que te toca revisar: la regla de Producción › Por revisar («Me toca revisar»: tu account, la jefa del ÁREA en la
 *  técnica (V2: revisorTecnica), Mili o Tomás por nombre; nadie se revisa a sí mismo; las de más de 30 días van aparte, como
 *  allí). V2 · puesto: quien tiene varios puestos ve en cada pestaña solo lo de ese puesto (la técnica, en su jefatura; las del
 *  account, en «Account»; las de Mili/Tomás por nombre, en operaciones/dirección). */
/** Las piezas en revisión (cola de cada persona + revisiones del panel), una por tarea, con sus autores. */
function piezasRevision(ctx, p) {
  const porNombre = new Map();
  for (const q of ctx.datos?.personas || []) for (const f of [q.alias, q.nombre, (q.nombre || '').split(' ')[0]]) if (f) porNombre.set(f.trim().toLowerCase(), q.id);
  const m = new Map();
  for (const r of p.cola || []) {
    if (r.grupo !== 'revision') continue;
    const x = m.get(r.id) || { id: r.id, tarea: r.tarea, cli: r.cli || null, cliente: r.cliente, estado: r.estado, dias: r.dias_estado, url: r.url, autores: new Set() };
    x.autores.add(r.persona_id);
    m.set(r.id, x);
  }
  for (const r of p.revisiones || []) {
    if (r.estado === 'bloqueado') continue;
    const x = m.get(r.id) || { id: r.id, tarea: r.tarea, cli: r.cliente_id, cliente: r.cliente_id, estado: r.estado, dias: r.dias, url: r.url, autores: new Set() };
    for (const n of r.asignados || []) { const pid = porNombre.get(String(n).trim().toLowerCase()); if (pid) x.autores.add(pid); }
    x.cli = x.cli || r.cliente_id;
    m.set(r.id, x);
  }
  return [...m.values()];
}
const conNombres = (ctx, l) => l.map(x => ({ ...x, clienteNombre: nomCli(ctx, x.cli) || x.cliente || 'Interno', autoresTxt: [...x.autores].map(id => alias(ctx, id)).join(', ') }));
export function piezasMeTocan(ctx, D, { puesto = null } = {}) {
  const p = D.opcional('produccion/produccion');
  if (!p) return [];
  const RP = REGLAS.revision_piezas || {};
  const esperaCliente = new Set(RP.espera_cliente || []);
  const porEstado = RP.por_estado || {};
  const todos = ctx.persona.puestos || [];
  const puestos = puesto && todos.length > 1 ? [puesto] : todos;
  const cartAcc = ctx.carteraPorSilla?.account;
  const llevoCuenta = id => !!id && !!cartAcc && (typeof cartAcc.has === 'function' ? cartAcc.has(id) : (cartAcc.includes?.(id) || false));
  const accountDe = id => (ctx.verdad ? ctx.verdad(id)?.account : null) ?? null;
  const yoId = yo(ctx);
  const personaPuesto = { mili: ['operaciones'], tomas: ['direccion'] };
  return conNombres(ctx, piezasRevision(ctx, p).filter(x => {
    const regla = porEstado[x.estado];
    if (esperaCliente.has(x.estado) || !regla || x.autores.has(yoId) || (x.dias || 0) > 30) return false;
    const acc = x.cli ? (accountDe(x.cli) ?? ctx.verdad?.(x.cli)?.responsable_id ?? null) : null;
    if (regla.revisa === 'account') return puestos.some(q => q === 'account' || q === 'operaciones') && (acc ? acc === yoId || (puestos.includes('account') && llevoCuenta(x.cli)) : puestos.includes('operaciones'));
    if (regla.revisa === 'persona') return regla.persona === yoId && (puestos.length === todos.length || puestos.some(q => (personaPuesto[yoId] || todos).includes(q)));
    if (regla.revisa === 'puestos') {
      const mias = puestos.filter(q => (regla.puestos || []).includes(q));
      const rv = revisorTecnica(ctx, [...x.autores], regla);
      return (mias.length && rv.jefas.has(yoId)) || (rv.operaciones && puestos.includes('operaciones'));
    }
    return false;
  }));
}
/** V2 · UNA vara para «Contesta» y «Revisa» de una persona: «Tu cumplimiento» y «Trabajo» (la propia), el mapa de control
 *  del día de Mili y el de Incidencias (las de todos). Correos = la regla de la pantalla Bandeja (bandejaComoPantalla: sin
 *  automáticos, ni viejos, ni lo ya despachado en la cola de la Bandeja) de los clientes que lleva como account; revisiones =
 *  las REVISIONES DEL ACCOUNT de Producción (revisionesDelAccount de produccion_comun.js, la misma que «Revisiones 48 h» de
 *  Producción y el generador de Incidencias): todas las suyas y, de ellas, las de más de 48 h. Ojo: no son las «piezas por
 *  revisar» de «Lo mío» (Producción › Por revisar, últimos 30 días); por eso se nombran distinto. → { contesta, revisa }
 *  con { mas48, total } o null si falta ese dato. */
export function controlPersona(ctx, D, pid, extra) {
  const accountDe = id => (ctx.verdad ? ctx.verdad(id)?.account : null) ?? null;
  let contesta = null, revisa = null;
  if (D.opcional('bandeja/bandeja')) {
    const cart = pid === yo(ctx) ? silla(ctx, 'account') : null;
    const { c } = bandejaComoPantalla(ctx, D, extra);
    const suyos = c.filter(x => x.account_id === pid || (x.cliente_id && (cart ? cart.has(x.cliente_id) : accountDe(x.cliente_id) === pid)));
    contesta = { mas48: suyos.filter(x => x.gravedad === 'rojo').length, total: suyos.length };
  }
  const p = D.opcional('produccion/produccion');
  if (p) { const r = revisionesDelAccount(p, pid); revisa = { mas48: r.mas48.length, total: r.todas.length, filas: r.mas48 }; }
  return { contesta, revisa };
}
/** ¿Puede tocarle revisar algo a esta persona? (para no pedir Producción a quien nunca revisa). */
export function revisaPiezas(ctx) {
  const RP = REGLAS.revision_piezas || {};
  const puestos = ctx.persona.puestos || [];
  return Object.values(RP.por_estado || {}).some(r => (r.revisa === 'account' && (puestos.includes('account') || puestos.includes('operaciones')))
    || (r.revisa === 'persona' && r.persona === yo(ctx)) || (r.revisa === 'puestos' && (puestos.some(q => (r.puestos || []).includes(q)) || puestos.includes('operaciones'))));
}
/** Decisiones que esperan TU sí (reloj de 48 h): las «para Tomás» a dirección, las «para Coti» a proyectos. */
export function decisionesMias(ctx, D) {
  const r = D.opcional('decisiones/reloj');
  if (!r) return [];
  const p = ctx.persona.puestos || [];
  const tipos = [p.includes('direccion') ? 'para_tomas' : null, p.includes('proyectos') ? 'para_coti' : null].filter(Boolean);
  return (r.decisiones || []).filter(x => !x.respuesta && tipos.includes(x.tipo));
}

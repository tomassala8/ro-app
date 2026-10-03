// modulos/personas.js · M20 Personas (E7 + ficha de Cecilia, RRHH, en 10_FICHAS/G1).
// Número que manda de Cecilia: personas en alerta sin conversación ni plan en 7 días (verde 0 · ámbar 1 · rojo 2+).
// Cada uno ve lo suyo; su jefa, su equipo; Cecilia, Mili y Tomás, todos. El recorte lo hace servir.py por persona_id
// (reglas horas_persona / notas_persona / alarma_persona, D-83). Sin sueldos ni dinero, nunca.
// Datos: data/personas_m20/equipo.json y, solo para quien ve Ajustes (Mili, Tomás, Cecilia), data/personas_m20/contratacion.json
// (fuentes_personas/generar_personas.py). Lo que se apunta (ausencias, planes, 1:1, notas) va a la cola simulada de local.db.

import {
  fmt, tile, tiles, pestanas, chipsFiltro, chipEstado, tablaApilable, vacio, vacioLinea, panel, avisoParcial, botonConfirmar,
  barraProgreso, lineaTiempo, copiar, avisoFlotante, icono, frescura, selloMedible, limpiaTexto, graficoSerie, deDondeSale, hoyMadrid,
} from '../componentes.js';
import { PUESTO } from '../permisos.js';
import { h, elegir, estilosLocales, cabPersona, campo, dias, leerCola, vp } from './personas_comun.js';
import { llevarA } from './_ir.js';
import { lineaZona } from './mi_perfil.js';   // V3a: zona y hora local de cada persona («Caracas · 21:14 ahora»)

const CAP = { account: 12, trafficker: 16, crm: 16 };
let CARTERAS = [];
/** R12 · fila de la verdad única para persona y silla, o null. */
const carteraV = (pid, silla) => CARTERAS.find(c => c.persona_id === pid && c.silla === silla) || null;
/** «19 tuyos + 2 de apoyo» (o nada si no hay apoyo) · sin mezclar con el universo de la pantalla. */
let YO = null;   // V2: «tuyos» solo en tu fila; en la de otra persona, «suyos»
const repartoTxt = (pid, silla) => { const c = carteraV(pid, silla); return c ? `${c.n_principal} ${pid === YO ? 'tuyos' : 'suyos'}${c.n_apoyo ? ` + ${c.n_apoyo} de apoyo` : ''}` : ''; };
const SILLA_TXT = { account: 'proyectos de account', trafficker: 'cuentas de Meta', crm: 'subcuentas de CRM', seo: 'clientes SEO', web: 'webs', redes: 'marcas de redes', outreach: 'campañas de outreach', produccion: 'clientes de producción' };
const PUNTUAN = ['direccion', 'operaciones', 'jefa_publicidad', 'jefa_seo', 'jefa_crm'];   // D-74: Mili y las jefas (y Tomás)
/** V3a · celda «Persona» de las tablas del equipo: alias, puesto y su zona con la hora de allí ahora (lineaZona de Mi perfil).
 *  La zona solo ENSEÑA la hora: vencidas, «hoy» y plazos siguen en Madrid (V2-E). */
const celdaPersona = (ctx, p) => h('span', { style: { display: 'grid', gap: '2px', minWidth: '0' } },
  h('b', {}, p.alias), h('span', { class: 'sub' }, puestosTxt(p)), lineaZona(ctx, p.persona_id));
const hoyISO = () => hoyMadrid();   // V2: «hoy» real de Madrid (helper común), no el día UTC

export default {
  id: 'personas',
  titulo: 'Personas',
  grupo: 'Equipo',
  puestos_que_lo_ven: { '*': 'suyo', direccion: 'todo', operaciones: 'todo', rrhh: 'todo' },

  async render(cont, ctx) {
    estilosLocales();
    // Auditoría 37 (causa 4): las cinco lecturas salen A LA VEZ (antes, una detrás de otra: ~3 s en 4G lenta).
    const verCola = ['direccion', 'operaciones', 'rrhh'].some(p => ctx.persona.puestos.includes(p));
    const pE = ctx.datosModulo('personas_m20/equipo');
    pE.catch(() => null);
    const pC = ctx.servidor && verCola ? ctx.datosModulo('personas_m20/contratacion').catch(() => null) : Promise.resolve(null);
    const pCola = leerCola(ctx, verCola ? 'ajustes' : null);
    const pVE = ctx.datosModulo('verdad/equipo').catch(() => null);
    const pCarteras = ctx.datosModulo('verdad/clientes').then(v => v?.carteras || []).catch(() => []);
    let E;
    try { E = await pE; }
    catch (e) {
      cont.append(vacio({ icono: 'eq', titulo: 'No se pudieron leer los datos de personas', texto: e.message, quien: 'Agus', tono: 'aviso',
        accion: h('span', { class: 'sub' }, 'Falta generar los datos de personas de hoy.') }));
      return;
    }
    // Apuntes de la app: los de los ficheros + la cola viva (Mili, Tomás y Cecilia ven la de RRHH; los demás, la suya).
    const [C, colaTodas, VE, carteras] = await Promise.all([pC, pCola, pVE, pCarteras]);
    CARTERAS = carteras;
    // V2 (petición de V2-C1, B-A3): la cartera de publicidad es UNA, la de Captación y Mi día (verdad carteras[] = captacion.json ›
    // carteras_publicidad): los clientes que LLEVA (principal); el apoyo va aparte y no cuenta contra el tope de 16.
    // Antes Personas sumaba principal + apoyo (Lina 21, Valeria 19 «por encima»); ahora Lina 19 (+2 de apoyo), Valeria 11 (+8).
    let CP = null; try { CP = ctx.veModulo?.('captacion') ? (await ctx.datosModulo('captacion/captacion'))?.carteras_publicidad || null : null; } catch { CP = null; }
    const cola = colaTodas.filter(a => (a.tipo || '').startsWith('personas_'));
    const P = E.personas.map(p => {
      const x = { ...p, cartera: { ...(p.cartera || {}) } };
      const v = carteraV(p.persona_id, 'trafficker');
      if (v && x.cartera.trafficker !== undefined) {
        const cp = CP?.[p.persona_id];
        x.cartera.trafficker = v.n_principal;
        x.publicidad = { apoyo: v.n_apoyo, con_meta: cp?.con_meta ?? v.universo?.dentro ?? null, encendida: cp?.meta_encendida ?? null };
        const sobreT = v.n_principal > CAP.trafficker, cercaT = !sobreT && v.n_principal >= CAP.trafficker - 2;
        x.sobre_capacidad = (x.sobre_capacidad || []).filter(s => s !== 'trafficker').concat(sobreT ? ['trafficker'] : []);
        x.cerca_capacidad = (x.cerca_capacidad || []).filter(s => s !== 'trafficker').concat(cercaT ? ['trafficker'] : []);
      }
      return x;
    });
    const porId = Object.fromEntries(P.map(p => [p.persona_id, p]));
    for (const a of cola) {
      const v = vp(a); const p = porId[v.persona_id || a.objeto];
      if (p && !p.apuntes.some(x => x.id === a.id)) p.apuntes.push({ id: a.id, tipo: a.tipo.replace('personas_', ''), creada: a.creada, quien: a.quien, texto: a.texto, datos: v, estado: a.estado });
    }
    const ausencias = [...(E.ausencias || [])];
    for (const p of P) for (const a of p.apuntes.filter(x => x.tipo === 'ausencia')) ausencias.push({ ...a.datos, persona_id: p.persona_id, alias: p.alias, simulada: true, quien: a.quien, creada: a.creada });

    const yo = ctx.persona.id;
    YO = yo;
    const equipo = P.length > 1 || !porId[yo];
    const nombre = Object.fromEntries((ctx.datos.personas || []).map(p => [p.id, p.alias || p.nombre]));
    const fr = { fuente: 'ClickUp · horas', fecha: E._meta.corte_horas, estado: 'ok' };

    ctx.titulo('Personas', equipo
      ? `${P.length} personas que puedes ver · alertas, carga, imputación, ausencias, 1:1 y nota del mes${veSueldos(ctx) ? ' · sueldos en su pestaña, con rastro' : ''}`
      : 'Tu ficha: tus horas, tu carga, tus ausencias, tus 1:1 y tus notas. Solo la ven tú, tu jefa, Cecilia, Mili y Tomás.');

    const enAlerta = P.filter(p => p.alerta);
    const plan = p => p.apuntes.filter(a => a.tipo === 'plan').slice(-1)[0];
    const sinPlan = enAlerta.filter(p => !plan(p));
    const vencidas = sinPlan.filter(p => dias(p.alerta.desde) >= 7);
    // Misma regla que Horas (verdad única): activos que imputan, sin dudosos, bajas ni setters; «sin imputar» = 0 h el último día laborable.
    // VE (verdad/equipo) y CARTERAS (R12 · la cartera de cada persona sale de la verdad única: principal, apoyo y cuántos
    // entran en cada pantalla) ya llegaron arriba, en la misma tanda.
    const sinSetters = p => !(p.puestos || []).includes('setters');
    const imputan = P.filter(p => p.imputa && p.estado === 'activo' && sinSetters(p));
    const ceroIds = new Set((VE?.no_imputan_ayer || []).map(x => x.persona_id));
    const ceroAyer = VE ? imputan.filter(p => ceroIds.has(p.persona_id)) : imputan.filter(p => !p.horas.ayer);
    const noAyer = imputan.filter(p => (p.horas.ayer ?? 0) < 8);
    // V2 (B-M12): la base es la gente que ves. Valeria ve a su equipo (4): «0 de 4», no «0 de 28» de toda la empresa.
    const cuentanEquipo = equipo && verCola && VE?.cuentan ? VE.cuentan : imputan.length;
    const sobre = P.filter(p => p.sobre_capacidad.length);
    const horasSobre = P.filter(p => p.estado !== 'baja' && !p.sobre_capacidad.length && p.imputa && (p.horas?.pct_128 ?? 0) > 100).length;
    const hoy = hoyISO();
    const en14 = new Date(Date.now() + 14 * 864e5).toISOString().slice(0, 10);
    const ausProx = ausencias.filter(a => a.hasta >= hoy && a.desde <= en14);
    const mesNota = new Date(Date.now() - 864e5 * 5).toISOString().slice(0, 7);
    const conNota = P.filter(p => p.apuntes.some(a => a.tipo === 'nota' && (a.datos.mes || '').startsWith(mesNota)));
    const trimestre = `${new Date().getFullYear()}-T${Math.floor(new Date().getMonth() / 3) + 1}`;
    const con1a1 = P.filter(p => p.apuntes.some(a => a.tipo === '1a1' && (a.datos.trimestre === trimestre)));
    const activas = P.filter(p => p.estado === 'activo');

    // A1/A2 · #/personas/<id> abre ESA persona (desde «Lo mío», ⌘K o un aviso). Solo entre las que el servidor ya te
    // manda (tú; tu equipo si eres jefa; Cecilia, Mili y Tomás, todas): otra id dice que no la puedes ver, sin datos.
    let pid = null;
    try { pid = ctx.params?.[0] ? decodeURIComponent(String(ctx.params[0]).split('?')[0]) : null; } catch { pid = null; }
    if (pid && pid !== yo) {
      const otra = porId[pid];
      ctx.titulo('Personas', otra ? `${otra.alias} · ${puestosTxt(otra)} · su ficha: horas, carga, ausencias, 1:1 y notas` : 'Persona no disponible');
      cont.append(h('p', {}, h('a', { class: 'bt mini', href: '#/personas' }, icono('izquierda'), equipo ? 'Todas las personas' : 'Tu ficha')));
      if (!otra) {
        cont.append(vacio({ icono: 'candado', titulo: 'No puedes ver a esa persona', texto: 'O no existe, o no es de tu equipo. Cada uno ve su ficha; su jefa, su equipo; Cecilia, Mili y Tomás, a todas.', quien: 'Mili (Ajustes › Personas)' }));
        return;
      }
      pintarMiFicha(cont, ctx, otra, ausencias, fr, mesNota, trimestre, { plan: plan(otra) });
      // V2 (A-M12): #/personas/<id>?plan=1 (desde «Lo mío» de Cecilia) abre «Anotar conversación y plan» con el foco
      const quiere = new URLSearchParams((location.hash || '').split('?')[1] || '');
      const abrir = quiere.get('plan') === '1' && !ctx.soloLectura ? cont.querySelector('[data-abrir-plan]') : null;
      if (abrir) { abrir.click(); llevarA(cont, '.pm-tarjeta'); }
      else llevarA(cont, '.detalle-cab');   // R15a: resaltada, centrada y con el foco (ayudante común de «Ir al objeto»)
      return;
    }
    if (!equipo || pid === yo) { pintarMiFicha(cont, ctx, porId[yo], ausencias, fr, mesNota, trimestre); return; }

    // ---- 1 · cifras (lo de cada día arriba) ----
    let tabs;
    const ir = id => () => { tabs?.elegir(id); tabs?.scrollIntoView({ behavior: 'smooth', block: 'start' }); };
    cont.append(tiles([
      tile({ icono: 'alert', etiqueta: 'En alerta y sin plan pasados 7 días', valor: vencidas.length, unidad: `de ${enAlerta.length} en alerta`,
        estado: vencidas.length === 0 ? 'verde' : vencidas.length === 1 ? 'ambar' : 'rojo',
        // V2 (A-M5): las tres cifras juntas y con su nombre: en alerta (todas) · sin plan (aún en plazo) · pasadas de 7 días
        contexto: sinPlan.length ? `${enAlerta.length} en alerta: ${sinPlan.length} sin plan todavía (el primer plazo vence el ${fmt.fecha(addDias(minFecha(sinPlan.map(p => p.alerta.desde)), 7))}) y ${enAlerta.length - sinPlan.length} con plan` : 'Todas con conversación y plan',
        medible: 'hoy', medibleDetalle: 'La alerta sale del panel; el plan se anota aquí', frescura: fr, ir: 'Ver personas en alerta', alPulsar: ir('alerta') }),
      tile({ icono: 'capas', etiqueta: 'Por encima de su capacidad', valor: sobre.length, unidad: 'personas',
        estado: sobre.length === 0 ? 'verde' : sobre.length === 1 ? 'ambar' : 'rojo', contexto: `Cartera: accounts > 12 proyectos · trafficker y CRM > 16${horasSobre ? ` · aparte, ${fmt.plural(horasSobre, 'persona', 'personas')} con más del 100 % de horas (solo aviso)` : ''}`,
        medible: 'hoy', ir: 'Ver la carga', alPulsar: ir('carga') }),
      tile({ icono: 'clock', etiqueta: 'Ayer sin imputar', valor: ceroAyer.length, unidad: `de ${cuentanEquipo}`,
        estado: ceroAyer.length === 0 ? 'verde' : ceroAyer.length <= 3 ? 'ambar' : 'rojo', contexto: `Misma regla que Horas: 0 h el último día laborable · ${noAyer.length} por debajo de 8 h`,
        medible: 'medias', medibleDetalle: 'Imputación del equipo ~52 %: orientativo', frescura: fr, ir: 'Ver quién no imputa', alPulsar: ir('imputa') }),
      tile({ icono: 'cal', etiqueta: 'Ausencias en 14 días', valor: ausProx.length, unidad: ausProx.length === 1 ? 'ausencia' : 'ausencias',
        estado: ausProx.some(a => !a.suplente) ? 'ambar' : '', contexto: ausProx.length ? `${ausProx.filter(a => !a.suplente).length} sin suplente` : 'Ninguna registrada todavía',
        medible: 'hoy', medibleDetalle: 'Tabla propia de la app', ir: 'Ver ausencias', alPulsar: ir('ausencias') }),
      tile({ icono: 'star', etiqueta: 'Nota del mes y 1:1', valor: conNota.length, unidad: `de ${activas.length} con nota`,
        estado: conNota.length >= activas.length ? 'verde' : new Date().getDate() > 5 ? 'rojo' : 'ambar',
        contexto: `Nota de ${mesTxt(mesNota)}: 100 % el día 5 · 1:1 del ${trimTxt(trimestre)}: ${con1a1.length} de ${activas.length}`,
        medible: 'hoy', ir: 'Ver notas', alPulsar: ir('notas') }),
    ]));

    // ---- 2 · pestañas por frecuencia: diario → semanal → mensual ----
    const lista = [
      { id: 'alerta', texto: 'En alerta sin plan', icono: 'alert', cuenta: sinPlan.length, cuentaEstado: 'rojo' },
      { id: 'imputa', texto: 'Quién no imputa', icono: 'clock', cuenta: ceroAyer.length, cuentaEstado: 'rojo' },
      { id: 'ausencias', texto: 'Ausencias', icono: 'cal', cuenta: ausProx.length },
      { id: 'carga', texto: 'Carga', icono: 'capas', cuenta: sobre.length, cuentaEstado: 'rojo' },
      { id: '1a1', texto: '1:1 y ronda', icono: 'users' },
      { id: 'notas', texto: 'Nota del mes', icono: 'star' },
      ...(C ? [{ id: 'contratacion', texto: 'Contratación', icono: 'maletin', cuenta: C.vacantes.reduce((s, v) => s + v.plazas, 0) }] : []),
      ...(C ? [{ id: 'salida', texto: 'Lista de salida', icono: 'candado' }] : []),
      ...(veSueldos(ctx) ? [{ id: 'sueldos', texto: 'Sueldos', icono: 'euro' }] : []),
    ];
    tabs = pestanas({ pestanas: lista, clave: 'personas', etiqueta: 'Secciones de Personas', unaFila: true, pintar: (id, z) => {
      if (id === 'alerta') z.append(...vistaAlerta(ctx, enAlerta, plan, fr));
      if (id === 'imputa') z.append(...vistaImputa(ctx, imputan, P, fr));
      if (id === 'ausencias') z.append(...vistaAusencias(ctx, P, ausencias, nombre));
      if (id === 'carga') z.append(...vistaCarga(ctx, P, fr));
      if (id === '1a1') z.append(...vista1a1(ctx, P, E, trimestre));
      if (id === 'notas') z.append(...vistaNotas(ctx, P, mesNota));
      if (id === 'contratacion') z.append(...vistaContratacion(ctx, C, P));
      if (id === 'salida') z.append(...vistaSalida(ctx, P, cola));
      if (id === 'sueldos') vistaSueldos(ctx, P, z);
    } });
    cont.append(tabs);
    const cel = panelCelebraciones(ctx);
    if (cel) cont.append(cel);
    cont.append(h('p', { class: 'sub', style: { marginTop: 'var(--s-4)' } }, icono('candado', { clase: 's' }), veSueldos(ctx) ? ' Los sueldos solo se abren en su pestaña y queda en el rastro. Horas solo como aviso. ' : ' Sin sueldos ni dinero. Horas solo como aviso. ',
      `Datos: horas de ClickUp (corte ${E._meta.corte_horas}, hora de Madrid) · alertas del panel de Mili · generado ${E._meta.generado}.`));
  },
};

// ======================================================================== cumpleaños y aniversarios (lo ve todo el equipo)
/** Próximas dos semanas, de ctx.celebraciones (cumpleaños solo con día y mes; aniversarios de entrada en RO). */
function panelCelebraciones(ctx) {
  const l = typeof ctx.celebraciones === 'function' ? ctx.celebraciones({ dias: 14 }) : [];
  const DIAS = ['domingo', 'lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado'];
  const cuando = c => (c.en_dias === 0 ? 'hoy' : c.en_dias === 1 ? 'mañana' : (() => { const d = new Date(`${c.fecha}T12:00`); return `el ${DIAS[d.getDay()]} ${d.getDate()} de ${MESES[d.getMonth()]}`; })());
  const cuerpo = !l.length ? vacioLinea('Ningún cumpleaños ni aniversario en las próximas dos semanas.', { icono: 'heart' })
    : h('ul', { class: 'lista-i' }, l.slice(0, 8).map(c => h('li', {},
      h('span', { class: `ico-c s ${c.en_dias === 0 ? 'verde' : 'gris'}` }, icono(c.tipo === 'cumple' ? 'heart' : 'crown')),
      h('span', { class: 't', style: { whiteSpace: 'normal', minWidth: '0' } }, h('b', {}, c.alias), c.tipo === 'cumple'
        ? ` cumple años ${cuando(c)}` : ` cumple ${c.anios} año${c.anios === 1 ? '' : 's'} en RO ${cuando(c)}`),
      c.en_dias === 0 ? chipEstado('verde', 'Hoy') : null)));
  return panel({ titulo: 'Cumpleaños y aniversarios', icono: 'heart', sub: 'Del equipo, en las próximas dos semanas' },
    h('div', { class: 'cuerpo' }, cuerpo, l.length > 8 ? h('p', { class: 'sub' }, `y ${l.length - 8} más`) : null));
}

// ======================================================================== utilidades
const MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'];
const mesTxt = m => m ? `${MESES[Number(m.slice(5, 7)) - 1]} ${m.slice(0, 4)}` : '—';
const trimTxt = tr => (/T(\d)$/.test(tr || '') ? `${tr.slice(-1)}.º trimestre` : tr);
function addDias(iso, n) { const d = new Date(iso + 'T12:00:00'); d.setDate(d.getDate() + n); return d.toISOString().slice(0, 10); }
function minFecha(l) { return l.filter(Boolean).sort()[0] || hoyISO(); }
const motivoTxt = m => limpiaTexto(String(m).replace(/(\d)\.(\d)/g, '$1,$2'));
const puestosTxt = p => (p.puestos || []).map(x => PUESTO[x]?.nombre || x).join(' · ');

async function apuntar(ctx, tipo, persona_id, texto, datos) {
  await ctx.accion({ modulo: 'ajustes', herramienta: 'app', tipo: `personas_${tipo}`, objeto: persona_id, texto,
    vista_previa: { persona_id, ...datos, nota: 'Prototipo: queda en la cola simulada de la app; se guardará en la tabla de personas al publicarla.' } });
  avisoFlotante('Apuntado en la cola simulada');
  setTimeout(() => location.reload(), 900);
  return 'Apuntado (simulado)';
}

// ======================================================================== En alerta
function vistaAlerta(ctx, enAlerta, plan, fr) {
  if (!enAlerta.length) return [vacio({ icono: 'ok', tono: 'celebrar', titulo: 'Nadie en alerta', texto: 'Cuando el panel marque a alguien (tareas arrastradas, revisiones o correos de más de 48 h…) aparece aquí con su motivo. Las horas imputadas son solo aviso.' })];
  let filtro = '';
  const caja = h('div', { class: 'pm-tarjetas' });
  const mas = h('div', { class: 'tabla-mas', style: { padding: '0 var(--relleno) var(--relleno)' } });
  let tope = 9;   // 3 filas de 3: lo más grave a la vista, el resto con un clic (página corta también en el móvil)
  const pintar = () => {
    const ls = enAlerta.filter(p => !filtro || (filtro === 'sin' ? !plan(p) : !!plan(p)))
      .sort((a, b) => (!!plan(a) - !!plan(b)) || b.alerta.peso - a.alerta.peso);
    caja.replaceChildren(...(ls.length ? ls.slice(0, tope).map(p => tarjetaAlerta(ctx, p, plan(p))) : [vacioLinea('Nadie con este filtro.', { icono: 'filtro' })]));
    mas.replaceChildren(...(ls.length > tope ? [h('button', { type: 'button', class: 'bt', on: { click: () => { tope = ls.length; pintar(); } } }, icono('mas'), `Ver las ${ls.length} personas`)] : []));
  };
  const chips = chipsFiltro({ clave: 'personas.alerta', etiqueta: 'Ver', opciones: [
    { valor: '', texto: 'Todas', cuenta: enAlerta.length },
    { valor: 'sin', texto: 'Sin plan', icono: 'alert', cuenta: enAlerta.filter(p => !plan(p)).length, cuentaEstado: 'rojo' },
    { valor: 'con', texto: 'Con plan', icono: 'check', cuenta: enAlerta.filter(p => plan(p)).length }],
    alCambiar: v => { filtro = v; tope = 9; pintar(); } });
  filtro = chips.valor();
  pintar();
  return [
    avisoParcial('Protocolo del 13-ago: aviso claro, plazo de reacción y solo después la decisión. A los 7 días sin conversación ni plan, sube a Tomás. Las horas imputadas no ponen a nadie en alerta (regla de Tomás): salen como aviso en «Quién no imputa».', { tipo: 'info', titulo: 'Qué se hace' }),
    panel({ titulo: 'Personas en alerta', icono: 'alert', sub: 'Más grave arriba; sin plan primero. Desde = primera foto en la que aparece (hay fotos desde el 2-oct).' }, h('div', { class: 'pm-pad' }, chips), caja, mas),
  ];
}

function tarjetaAlerta(ctx, p, pl) {
  const d = dias(p.alerta.desde);
  const estado = pl ? 'verde' : d >= 7 ? 'rojo' : 'ambar';
  const puede = ['direccion', 'operaciones', 'rrhh'].some(x => ctx.persona.puestos.includes(x)) || p.jefe === ctx.persona.id;
  const form = h('div', { hidden: true });
  const txt = h('textarea', { placeholder: 'Qué se habló, qué se le pide y para cuándo', 'aria-label': `Plan para ${p.alias}` });
  const rev = h('input', { type: 'date', value: addDias(hoyISO(), 7), 'aria-label': 'Fecha de revisión' });
  form.append(h('div', { class: 'pm-form' }, campo('Conversación y plan', txt, { ancho: true }), campo('Revisar el', rev),
    botonConfirmar({ texto: 'Guardar plan', pregunta: `¿Guardar el plan de ${p.alias}?`, confirmar: 'Sí, guardar', soloLectura: ctx.soloLectura,
      alConfirmar: () => { if (!txt.value.trim()) throw new Error('escribe la conversación y el plan'); return apuntar(ctx, 'plan', p.persona_id, txt.value.trim(), { plan: txt.value.trim(), revision: rev.value }); } })));
  return h('article', { class: `pm-tarjeta ${estado}` },
    cabPersona(p.nombre, puestosTxt(p), chipEstado(estado, pl ? 'con plan' : d >= 7 ? `${d} días sin plan` : `Plan pendiente · quedan ${7 - d} días`)),
    h('ul', { class: 'pm-motivos' }, p.alerta.motivos.map(m => h('li', {}, icono('alert'), motivoTxt(m)))),
    (p.avisos || []).length ? h('p', { class: 'sub' }, icono('clock', { clase: 's' }), ` Aviso, no alerta: ${p.avisos.map(motivoTxt).join(' · ')}`) : null,
    h('div', { class: 'meta-linea' }, h('span', {}, icono('cal'), `En alerta desde el ${fmt.fecha(p.alerta.desde)}`),
      h('span', {}, icono('flag'), `${p.alerta.peso} ${p.alerta.peso === 1 ? 'motivo' : 'motivos'}`), p.jefe ? h('span', {}, icono('persona'), `Responde ante: ${ctx.nombre(p.jefe)}`) : null),
    pl ? h('div', { class: 'pm-dec' }, h('p', { class: 'rec' }, h('b', {}, 'Plan: '), pl.texto), h('span', { class: 'sub' }, `Anotado por ${pl.quien} · ${fmt.fecha(pl.creada)} · revisar el ${fmt.fecha(pl.datos.revision)}${pl.estado === 'simulada' ? ' · simulado' : ''}`)) : null,
    puede ? h('div', { class: 'fila' },
      h('button', { type: 'button', class: 'bt mini', 'data-abrir-plan': '1', disabled: ctx.soloLectura || null, title: ctx.soloLectura ? 'Ver como: solo lectura' : null,
        on: { click: () => { form.hidden = !form.hidden; if (!form.hidden) txt.focus(); } } }, icono('editar'), pl ? 'Cambiar el plan' : 'Anotar conversación y plan'),
      h('a', { class: 'bt mini', href: '#/horas' }, icono('clock'), 'Ver sus horas'), atajosPersona(p)) : null,
    form);
}

// ======================================================================== Quién no imputa
function vistaImputa(ctx, imputan, P, fr) {
  const noImputan = P.filter(p => !p.imputa);
  let filtro = 'ayer';
  const zona = h('div');
  const pintar = () => {
    const filas = imputan.filter(p => filtro === 'todos' || (filtro === 'cero' ? !p.horas.ayer : filtro === 'ayer' ? (p.horas.ayer ?? 0) < 8 : (p.horas.dias_sin_imputar_5 || []).length >= 3))
      .sort((a, b) => (a.horas.ayer ?? 0) - (b.horas.ayer ?? 0) || b.horas.dias_sin_imputar_5.length - a.horas.dias_sin_imputar_5.length);
    zona.replaceChildren(tablaApilable({
      filas,
      vacio: { icono: 'ok', titulo: 'Todos imputaron', texto: 'Nadie en este filtro.' },
      columnas: [
        { clave: 'alias', titulo: 'Persona', principal: true, celda: p => celdaPersona(ctx, p) },
        { clave: 'ayer', titulo: `Ayer (${fmt.fecha(P[0]?.horas?.ayer_fecha)})`, num: true, celda: p => chipEstado(!p.horas.ayer ? 'rojo' : p.horas.ayer < 8 ? 'ambar' : 'verde', `${fmt.num(p.horas.ayer, 1)} h`) },
        { clave: 'semana', titulo: 'Esta semana', num: true, celda: p => `${fmt.num(p.horas.semana, 1)} h de ${p.horas.semana_dias * 8}` },
        { clave: 'sin', titulo: 'Días sin imputar (últimos 5)', num: true, celda: p => chipEstado(p.horas.dias_sin_imputar_5.length >= 3 ? 'rojo' : p.horas.dias_sin_imputar_5.length ? 'ambar' : 'verde', String(p.horas.dias_sin_imputar_5.length)) },
        { clave: 'ult', titulo: 'Último día con horas', celda: p => p.horas.ultimo_dia_con_horas ? fmt.hace(p.horas.ultimo_dia_con_horas) : chipEstado('rojo', 'nunca (desde ago)') },
        { clave: 'acc', titulo: '', celda: p => h('button', { type: 'button', class: 'bt mini', on: { click: () => copiar(recordatorio(p), 'Recordatorio copiado') } }, icono('copy'), 'Copiar recordatorio') },
      ],
    }));
  };
  const chips = chipsFiltro({ clave: 'personas.imputa', etiqueta: 'Ver', opciones: [
    { valor: 'cero', texto: 'Ayer sin horas', icono: 'alert', cuenta: imputan.filter(p => !p.horas.ayer).length, cuentaEstado: 'rojo' },
    { valor: 'ayer', texto: 'Ayer < 8 h', icono: 'clock', cuenta: imputan.filter(p => (p.horas.ayer ?? 0) < 8).length, cuentaEstado: 'rojo' },
    { valor: '3dias', texto: '3+ días sin imputar', icono: 'alert', cuenta: imputan.filter(p => p.horas.dias_sin_imputar_5.length >= 3).length, cuentaEstado: 'rojo' },
    { valor: 'todos', texto: 'Todos', cuenta: imputan.length }], alCambiar: v => { filtro = v; pintar(); } });
  filtro = chips.valor();
  pintar();
  return [
    avisoParcial('Las horas son solo un aviso de disciplina: con el 52 % imputado no miden rendimiento. Copia el recordatorio y mándaselo solo a quien no imputó. Pronto se enviará desde aquí.', { tipo: 'parcial', titulo: 'Horas incompletas.' }),
    panel({ titulo: 'Quién no imputa', icono: 'clock', sub: 'Ayer y esta semana, frente a 8 h al día', acciones: frescura(fr) }, h('div', { class: 'pm-pad' }, chips), zona,
      h('div', { class: 'fila', style: { marginTop: 'var(--s-3)' } },
        h('button', { type: 'button', class: 'bt', disabled: true, title: 'Pronto: envío de recordatorios por ClickUp o correo' }, icono('send'), 'Enviar a todos (pronto)'),
        noImputan.length ? h('span', { class: 'sub' }, `No imputan por puesto: ${noImputan.map(p => p.alias).join(', ')}.`) : null)),
  ];
}

function recordatorio(p) {
  const n = p.horas.dias_sin_imputar_5.length;
  return `Hola ${p.alias.split(' ')[0]}, ayer imputaste ${fmt.num(p.horas.ayer, 1)} h en ClickUp${n ? ` y llevas ${n} de los últimos 5 días laborables sin horas` : ''}. ¿Puedes dejarlas apuntadas hoy antes de las 15:00? Gracias.`;
}

// ======================================================================== Ausencias
function vistaAusencias(ctx, P, ausencias, nombre) {
  const hoy = hoyISO();
  const filas = ausencias.filter(a => a.hasta >= hoy).sort((a, b) => a.desde.localeCompare(b.desde));
  const pasadas = ausencias.filter(a => a.hasta < hoy);
  const per = h('select', {}, P.filter(p => p.estado !== 'baja').map(p => h('option', { value: p.persona_id }, p.alias)));
  const tipo = elegir(['Vacaciones', 'Baja médica', 'Permiso', 'Formación', 'Otro']);
  const desde = h('input', { type: 'date', value: hoy });
  const hasta = h('input', { type: 'date', value: addDias(hoy, 4) });
  const sup = h('select', {}, h('option', { value: '' }, '— sin suplente —'), P.filter(p => p.estado === 'activo').map(p => h('option', { value: p.persona_id }, p.alias)));
  const nota = h('input', { type: 'text', placeholder: 'Opcional' });
  const form = panel({ titulo: 'Registrar una ausencia', icono: 'mas', sub: 'Quien lleva clientes necesita suplente antes de empezar: la suplencia se crea en Asignaciones y caduca sola. Simulado hasta publicar la app.' },
    h('div', { class: 'pm-form' }, campo('Persona', per), campo('Tipo', tipo), campo('Desde', desde), campo('Hasta', hasta), campo('Suplente', sup), campo('Nota', nota),
      botonConfirmar({ texto: 'Registrar ausencia', pregunta: '¿Registrar la ausencia?', confirmar: 'Sí, registrar', soloLectura: ctx.soloLectura,
        alConfirmar: () => {
          if (hasta.value < desde.value) throw new Error('la fecha de fin es anterior al inicio');
          const p = P.find(x => x.persona_id === per.value);
          const lleva = Object.keys(p?.cartera || {}).length > 0;
          if (lleva && !sup.value) throw new Error(`${p.alias} lleva clientes: elige suplente`);
          return apuntar(ctx, 'ausencia', per.value, `${tipo.value} de ${p.alias} del ${desde.value} al ${hasta.value}${sup.value ? ` · suplente ${sup.value}` : ''}`,
            { tipo: tipo.value, desde: desde.value, hasta: hasta.value, suplente: sup.value || null, nota: nota.value || null });
        } })));
  const tabla = filas.length ? tablaApilable({ filas, columnas: [
    { clave: 'alias', titulo: 'Persona', principal: true },
    { clave: 'tipo', titulo: 'Tipo' },
    { clave: 'desde', titulo: 'Desde', celda: a => fmt.fecha(a.desde) },
    { clave: 'hasta', titulo: 'Hasta', celda: a => fmt.fecha(a.hasta) },
    { clave: 'suplente', titulo: 'Suplente', celda: a => a.suplente ? (nombre[a.suplente] || a.suplente) : chipEstado('ambar', 'sin suplente') },
    { clave: 'estado', titulo: 'Estado', celda: a => chipEstado(a.desde <= hoy ? 'azul' : 'gris', a.desde <= hoy ? 'hoy fuera' : 'prevista') },
  ] }) : vacio({ icono: 'cal', titulo: 'No hay ausencias registradas', texto: 'Hasta ahora las vacaciones no estaban en ninguna herramienta. Regístralas aquí y restan capacidad en la carga que ve Mili.', quien: 'Cecilia' });
  return [panel({ titulo: 'Hoy y próximas semanas', icono: 'cal', sub: `${filas.length} vigentes o previstas · ${pasadas.length} pasadas` }, tabla), form];
}

// ======================================================================== Carga
function vistaCarga(ctx, P, fr) {
  const filas = P.filter(p => p.estado !== 'baja').map(p => {
    const silla = Object.keys(p.cartera).sort((a, b) => (CAP[b] ? 1 : 0) - (CAP[a] ? 1 : 0) || p.cartera[b] - p.cartera[a])[0];
    return { ...p, silla, n: silla ? p.cartera[silla] : 0, cap: CAP[silla] || null, h: p.imputa ? p.horas.mes_anterior : null, pct: p.imputa ? p.horas.pct_128 : null };
  }).sort((a, b) => (b.sobre_capacidad.length - a.sobre_capacidad.length) || ((b.cap ? b.n / b.cap : 0) - (a.cap ? a.n / a.cap : 0)) || (b.pct ?? -1) - (a.pct ?? -1));
  const mes = mesTxt(P.find(p => p.imputa)?.horas?.mes_anterior_txt);
  return [panel({ titulo: 'Carga frente a capacidad', icono: 'capas', sub: `Proyectos frente a 12 (account) y 16 (trafficker y CRM) · horas de ${mes} frente a 128 h`, acciones: frescura(fr) },
    tablaApilable({ filas, etiquetaFila: p => p.alias, columnas: [
      { clave: 'alias', titulo: 'Persona', principal: true, celda: p => celdaPersona(ctx, p) },
      { clave: 'n', titulo: 'Cartera', celda: p => !p.silla ? h('span', { class: 'sub' }, 'sin cartera asignada') : h('div', { class: 'pm-barra' },
        p.cap ? barraProgreso({ valor: p.n, max: Math.max(p.cap, p.n), marca: p.cap, estado: p.n > p.cap ? 'rojo' : p.n >= (p.cap === 12 ? 7 : 14) ? 'ambar' : 'verde', etiqueta: `${p.n} de ${p.cap}` }) : h('span', {}),
        h('span', {}, `${p.n}${p.cap ? ` / ${p.cap}` : ''} clientes${repartoTxt(p.persona_id, p.silla) ? ` (${repartoTxt(p.persona_id, p.silla)})` : ''} · ${p.silla === 'trafficker' && p.publicidad ? `${p.publicidad.con_meta ?? '—'} con Meta${p.publicidad.encendida != null ? `, ${p.publicidad.encendida} encendidas` : ''} (como Captación)` : SILLA_TXT[p.silla] || p.silla}`)) },
      { clave: 'pct', titulo: 'Horas del mes', celda: p => p.h === null ? h('span', { class: 'sub' }, 'no imputa') : h('div', { class: 'pm-barra' },
        barraProgreso({ valor: p.h, max: Math.max(128, p.h), marca: 128, estado: p.pct > 100 ? 'rojo' : p.pct >= 70 ? 'verde' : 'ambar', etiqueta: `${fmt.num(p.h, 1)} h de 128` }),
        h('span', {}, `${fmt.num(p.h, 0)} h · ${fmt.pct(p.pct)}`)) },
      { clave: 'abrir', titulo: 'Abrir en', celda: p => atajosPersona(p, true) },
      // V2 (B-M12): la MISMA banda para todos. Cartera por encima del tope → rojo con su cifra; horas > 100 % del mes → rojo
      // (la banda de la barra: > 100 % rojo), aunque la cartera esté bien. Emanuel con 136 % ya no sale «bien».
      { clave: 'aviso', titulo: 'Aviso', celda: p => p.sobre_capacidad.length || (p.cap && p.n > p.cap) ? chipEstado('rojo', `por encima · ${p.n} de ${p.cap}`) : p.pct !== null && p.pct > 100 ? chipEstado('rojo', `horas por encima · ${fmt.pct(p.pct)}`) : p.cerca_capacidad.length ? chipEstado('ambar', 'cerca del tope') : p.pct !== null && p.pct < 60 ? chipEstado('gris', 'horas bajas o sin imputar') : chipEstado('verde', 'bien') },
    ] }),
    h('p', { class: 'sub' }, 'Banda de carga: del 70 al 90 % de las horas, verde; más del 100 %, rojo (en la cartera y en las horas, la misma regla para todos). Solo 1 de cada 10 tareas tiene estimación: la carga planificada todavía no se puede medir; aquí va la imputada.'))];
}

// ======================================================================== 1:1 y ronda
function vista1a1(ctx, P, E, trimestre) {
  const r = E._meta.ronda_jefas;
  const puede = ['direccion', 'operaciones', 'rrhh', 'jefa_publicidad', 'jefa_seo', 'jefa_crm'].some(x => ctx.persona.puestos.includes(x));
  const filas = P.filter(p => p.estado === 'activo').map(p => {
    const ult = p.apuntes.filter(a => a.tipo === '1a1').slice(-1)[0];
    return { ...p, ult, hecho: !!(ult && ult.datos.trimestre === trimestre) };
  }).sort((a, b) => a.hecho - b.hecho || a.alias.localeCompare(b.alias, 'es'));
  const per = h('select', {}, filas.map(p => h('option', { value: p.persona_id }, p.alias)));
  const puntos = h('textarea', { placeholder: 'Puntos hablados y acuerdos' });
  const sig = h('textarea', { placeholder: 'Lo que pasa al siguiente 1:1' });
  return [
    tiles([
      tile({ icono: 'users', etiqueta: `1:1 del ${trimTxt(trimestre)}`, valor: filas.filter(f => f.hecho).length, unidad: `de ${filas.length}`, estado: filas.every(f => f.hecho) ? 'verde' : 'rojo', contexto: 'Mínimo uno por persona al trimestre', medible: 'hoy' }),
      tile({ icono: 'cal', etiqueta: 'Próxima ronda con las jefas', valor: fmt.fecha(r.proxima), contexto: `Cada ${r.cada_dias} días · ${r.origen}`, estado: '', medible: 'medias', medibleDetalle: 'Hoy no se registraba: se anota aquí' }),
    ]),
    panel({ titulo: '1:1 por persona', icono: 'users', sub: 'Sin 1:1 este trimestre, arriba. Patrón Lattice: los puntos pendientes pasan al siguiente.' },
      tablaApilable({ filas, columnas: [
        { clave: 'alias', titulo: 'Persona', principal: true },
        { clave: 'puestos', titulo: 'Puesto', celda: p => h('span', { class: 'sub' }, puestosTxt(p)) },
        { clave: 'ult', titulo: 'Último 1:1', celda: p => p.ult ? `${fmt.fecha(p.ult.creada)} · ${p.ult.quien}` : chipEstado('gris', 'sin registro') },
        { clave: 'hecho', titulo: trimTxt(trimestre), celda: p => chipEstado(p.hecho ? 'verde' : 'ambar', p.hecho ? 'hecho' : 'pendiente') },
        { clave: 'sig', titulo: 'Pasa al siguiente', celda: p => p.ult?.datos?.siguiente || '—' },
      ] })),
    puede ? panel({ titulo: 'Anotar un 1:1 o la ronda', icono: 'editar', sub: 'Queda en la cola de la app con tu nombre y la hora (simulado hasta publicarla).' },
      h('div', { class: 'pm-form' }, campo('Con', per), campo('Puntos', puntos, { ancho: true }), campo('Pasa al siguiente', sig, { ancho: true }),
        botonConfirmar({ texto: 'Guardar 1:1', pregunta: '¿Guardar el 1:1?', confirmar: 'Sí, guardar', soloLectura: ctx.soloLectura,
          alConfirmar: () => { if (!puntos.value.trim()) throw new Error('escribe los puntos'); return apuntar(ctx, '1a1', per.value, puntos.value.trim(), { trimestre, puntos: puntos.value.trim(), siguiente: sig.value.trim() || null }); } }))) : null,
  ].filter(Boolean);
}

// ======================================================================== Nota del mes
function vistaNotas(ctx, P, mes) {
  const puede = PUNTUAN.some(x => ctx.persona.puestos.includes(x));
  const filas = P.filter(p => p.estado === 'activo').map(p => {
    const n = p.apuntes.filter(a => a.tipo === 'nota' && (a.datos.mes || '').startsWith(mes)).slice(-1)[0];
    return { ...p, n };
  }).sort((a, b) => !!a.n - !!b.n || a.alias.localeCompare(b.alias, 'es'));
  const per = h('select', {}, filas.filter(p => p.persona_id !== ctx.persona.id).map(p => h('option', { value: p.persona_id }, p.alias)));
  const nota = h('input', { type: 'number', min: '1', max: '10', step: '1', value: '7' });
  const hecho = h('textarea', { placeholder: 'El hecho que la justifica (con fecha o enlace)' });
  const accion = h('input', { type: 'text', placeholder: 'Qué se le pide el mes que viene' });
  return [
    avisoParcial('Puntúan Mili y las jefas (y Tomás); Cecilia consolida y vigila que esté hecha el día 5. Cada persona ve solo las suyas.', { tipo: 'info' }),
    panel({ titulo: `Nota 1-10 de ${mesTxt(mes)}`, icono: 'star', sub: `${filas.filter(f => f.n).length} de ${filas.length} puntuadas · siempre con un hecho y una acción` },
      tablaApilable({ filas, columnas: [
        { clave: 'alias', titulo: 'Persona', principal: true },
        { clave: 'puestos', titulo: 'Puesto', celda: p => h('span', { class: 'sub' }, puestosTxt(p)) },
        { clave: 'n', titulo: 'Nota', num: true, celda: p => p.n ? chipEstado(p.n.datos.nota >= 7 ? 'verde' : p.n.datos.nota >= 5 ? 'ambar' : 'rojo', String(p.n.datos.nota)) : chipEstado('gris', 'sin nota') },
        { clave: 'hecho', titulo: 'Hecho', celda: p => p.n ? p.n.datos.hecho : '—' },
        { clave: 'quien', titulo: 'La puso', celda: p => p.n ? p.n.quien : '—' },
      ], vacio: { titulo: 'Sin personas' } })),
    puede ? panel({ titulo: 'Puntuar', icono: 'editar', sub: 'Queda con tu nombre y la hora (simulado hasta publicar la app).' },
      h('div', { class: 'pm-form' }, campo('Persona', per), campo('Nota (1-10)', nota), campo('Hecho', hecho, { ancho: true }), campo('Acción', accion, { ancho: true }),
        botonConfirmar({ texto: 'Guardar nota', pregunta: '¿Guardar la nota?', confirmar: 'Sí, guardar', soloLectura: ctx.soloLectura,
          alConfirmar: () => {
            const n = Number(nota.value);
            if (!(n >= 1 && n <= 10)) throw new Error('la nota va de 1 a 10');
            if (!hecho.value.trim()) throw new Error('la nota necesita un hecho');
            return apuntar(ctx, 'nota', per.value, `${n} · ${hecho.value.trim()}`, { mes, nota: n, hecho: hecho.value.trim(), accion: accion.value.trim() || null });
          } }))) : null,
  ].filter(Boolean);
}

// ======================================================================== Contratación
function vistaContratacion(ctx, C, P = []) {
  const fases = C.fases;
  // V2 (A-M5): «Accounts: 0» frente a accounts «por encima» en Carga. El plan mira la capacidad TOTAL de accounts; la carga,
  // a cada persona. Se dice en la tarjeta: se reparte la cartera, no se ficha.
  const acc = P.filter(p => p.estado !== 'baja' && p.cartera?.account !== undefined);
  const accSobre = acc.filter(p => p.cartera.account > CAP.account).length;
  const accHueco = acc.filter(p => p.cartera.account < CAP.account - 2).length;
  const total = C.vacantes.reduce((s, v) => s + v.plazas, 0);
  const hoy = hoyISO();
  return [
    tiles([
      tile({ icono: 'megafono', etiqueta: 'Traffickers por fichar', valor: C.resumen.traffickers, unidad: 'en el trimestre', contexto: '4 en octubre (13-oct) y 3 en noviembre', estado: '' }),
      tile({ icono: 'base', etiqueta: 'Especialistas de CRM', valor: C.resumen.crm, unidad: 'en el trimestre', contexto: '2 en octubre y 1 en noviembre', estado: '' }),
      tile({ icono: 'eq', etiqueta: 'Accounts', valor: C.resumen.accounts, unidad: 'fichajes', contexto: accSobre ? `Sobra capacidad en total, pero mal repartida: ${accSobre} por encima de ${CAP.account} y ${accHueco} con hueco (pestaña Carga). Se reparte la cartera, no se ficha; reconvertir 1-2 a trafficker.` : 'Sobra capacidad: reconvertir 1-2 a trafficker', estado: accSobre ? 'ambar' : 'verde' }),
      tile({ icono: 'maletin', etiqueta: 'Candidatos registrados', valor: C.vacantes.some(v => v.candidatos !== null) ? C.vacantes.reduce((s, v) => s + (v.candidatos || 0), 0) : null,
        contexto: 'Lo rellena Cecilia cada lunes', medible: 'medias', medibleDetalle: 'El plan existe; el seguimiento, todavía no' }),
    ]),
    panel({ titulo: 'Vacantes del plan', icono: 'maletin', sub: `${total} plazas · plan de fichajes del cuarto trimestre (borrador de Operaciones, 28 sept)` },
      tablaApilable({ filas: C.vacantes, columnas: [
        { clave: 'puesto', titulo: 'Puesto', principal: true, celda: v => `${v.puesto} · oleada ${v.oleada}` },
        { clave: 'plazas', titulo: 'Plazas', num: true },
        { clave: 'abre', titulo: 'Abierta', celda: v => `${fmt.fecha(v.abre)} · ${dias(v.abre)} días` },
        { clave: 'entra', titulo: 'Entra', celda: v => chipEstado(v.entra < hoy ? 'rojo' : dias(hoy, v.entra) <= 14 ? 'ambar' : 'gris', fmt.fecha(v.entra)) },
        { clave: 'fase', titulo: 'Fase', celda: v => h('span', { class: 'fila', title: fases.join(' → ') }, chipEstado('azul', v.fase), h('span', { class: 'sub' }, `paso ${fases.indexOf(v.fase) + 1} de ${fases.length}`)) },
        { clave: 'candidatos', titulo: 'Candidatos', num: true, celda: v => v.candidatos ?? chipEstado('gris', 'sin dato') },
        { clave: 'acc', titulo: '', celda: v => botonConfirmar({ texto: 'Actualizar', mini: true, pregunta: `¿Marcar ${v.puesto} (oleada ${v.oleada}) en «entrevistas»?`, confirmar: 'Sí', soloLectura: ctx.soloLectura,
          alConfirmar: () => apuntar(ctx, 'vacante', v.id, `${v.puesto} oleada ${v.oleada} → entrevistas`, { vacante: v.id, fase: 'entrevistas' }) }) },
      ] })),
    panel({ titulo: 'Calendario de reclutamiento', icono: 'cal', sub: 'Plan del 28-sep: todos formados antes de Accountex (18-19 nov)' },
      lineaTiempo(C.calendario.map(c => ({ fecha: c.fecha, titulo: c.texto, detalle: c.hasta ? `hasta el ${fmt.fecha(c.hasta)}` : null, estado: (c.hasta || c.fecha) < hoy ? 'verde' : c.fecha <= hoy ? 'ambar' : '' })))),
    h('p', { class: 'sub' }, `Cuentas en activo previstas: hoy ${C.cuentas.hoy} → oct ${C.cuentas.oct} → nov ${C.cuentas.nov} → dic ${C.cuentas.dic} (con publicidad: ${C.cuentas.con_publicidad.hoy} → ${C.cuentas.con_publicidad.dic}). Sin sueldos: la contratación no enseña salarios.`),
  ];
}

// ======================================================================== Mi ficha (cada persona, lo suyo)
/** La ficha de una persona: la tuya o, con «otra» ({ plan }), la de alguien de tu equipo (#/personas/<id>). */
function pintarMiFicha(cont, ctx, p, ausencias, fr, mesNota, trimestre, otra = null) {
  if (!p) {
    cont.append(vacio({ icono: 'persona', titulo: 'No hay datos tuyos todavía', texto: 'Tu ficha sale de la tabla de personas. Si falta, que Mili te dé de alta en Ajustes › Personas.', quien: 'Mili' }));
    return;
  }
  const notas = p.apuntes.filter(a => a.tipo === 'nota');
  const unos = p.apuntes.filter(a => a.tipo === '1a1');
  const mias = ausencias.filter(a => a.persona_id === p.persona_id);
  const silla = Object.keys(p.cartera)[0];
  // de otra persona: «su» en vez de «tu», sin el formulario de pedir ausencia (lo pide cada uno) y con su tarjeta de alerta
  const T = otra ? { tu: 'Su', tus: 'Sus' } : { tu: 'Tu', tus: 'Tus' };
  cont.append(h('div', { class: 'detalle-cab panel', style: { padding: 'var(--s-4) var(--relleno)' } }, cabPersona(p.nombre, puestosTxt(p), p.alerta ? chipEstado('rojo', 'en alerta') : chipEstado('verde', 'sin alertas')),
    h('p', { style: { margin: 'var(--s-2) 0 0' } }, lineaZona(ctx, p.persona_id), h('a', { class: 'bt mini', href: otra ? `#/mi-perfil/${p.persona_id}` : '#/mi-perfil', style: { marginLeft: 'var(--s-2)' } }, otra ? 'Ver su zona' : 'Cambiar mi zona'))));
  cont.append(tiles([
    p.imputa ? tile({ icono: 'clock', etiqueta: 'Horas ayer', valor: fmt.num(p.horas.ayer, 1), unidad: 'h de 8', estado: !p.horas.ayer ? 'rojo' : p.horas.ayer < 8 ? 'ambar' : 'verde', contexto: `Esta semana ${fmt.num(p.horas.semana, 1)} h`, medible: 'medias', medibleDetalle: 'Solo aviso', frescura: fr })
      : tile({ icono: 'clock', etiqueta: 'Horas', valor: 'no imputa', contexto: `${T.tu} puesto no imputa horas` }),
    p.imputa ? tile({ icono: 'capas', etiqueta: `Horas de ${mesTxt(p.horas.mes_anterior_txt)}`, valor: fmt.num(p.horas.mes_anterior, 0), unidad: 'de 128 h', estado: p.horas.pct_128 > 100 ? 'rojo' : p.horas.pct_128 >= 70 ? 'verde' : 'ambar', contexto: `${fmt.pct(p.horas.pct_128)} de ${T.tu.toLowerCase()} capacidad` }) : null,
    silla ? tile({ icono: 'cartera', etiqueta: `${T.tu} cartera`, valor: p.cartera[silla], unidad: CAP[silla] ? `clientes · tope ${CAP[silla]}` : 'clientes', estado: p.sobre_capacidad.length ? 'rojo' : p.cerca_capacidad.length ? 'ambar' : 'verde',
      contexto: [repartoTxt(p.persona_id, silla), carteraV(p.persona_id, silla)?.universo?.texto].filter(Boolean).join(' · ') || SILLA_TXT[silla] || silla }) : null,
    tile({ icono: 'star', etiqueta: `${T.tu} nota de ${mesTxt(mesNota)}`, valor: notas.filter(n => (n.datos.mes || '').startsWith(mesNota)).slice(-1)[0]?.datos?.nota ?? null, unidad: '/ 10', contexto: `La ponen Mili o ${T.tu.toLowerCase()} jefa con un hecho`, estado: '' }),
    tile({ icono: 'users', etiqueta: `1:1 del ${trimTxt(trimestre)}`, valor: unos.some(u => u.datos.trimestre === trimestre) ? 'Hecho' : 'Falta', estado: unos.some(u => u.datos.trimestre === trimestre) ? 'verde' : 'ambar', contexto: 'Mínimo uno al trimestre' }),
  ].filter(Boolean)));
  if ((p.avisos || []).length) cont.append(avisoParcial(`${p.avisos.map(motivoTxt).join(' · ')}. Las horas son solo un aviso: no ponen a nadie en alerta.`, { tipo: 'info', titulo: 'Aviso de horas.' }));
  if (p.alerta && otra) cont.append(h('div', { class: 'pm-tarjetas' }, tarjetaAlerta(ctx, p, otra.plan)));
  else if (p.alerta) cont.append(panel({ titulo: 'Por qué estás en alerta', icono: 'alert', sub: `Desde el ${fmt.fecha(p.alerta.desde)} · lo hablarás con tu jefa o con Cecilia` }, h('ul', { class: 'pm-motivos' }, p.alerta.motivos.map(m => h('li', {}, icono('alert'), motivoTxt(m))))));
  const desde = h('input', { type: 'date', value: hoyISO() }), hasta = h('input', { type: 'date', value: addDias(hoyISO(), 4) });
  const tipo = elegir(['Vacaciones', 'Permiso', 'Formación', 'Otro']);
  cont.append(h('div', { class: 'dos' },
    panel({ titulo: `${T.tus} ausencias`, icono: 'cal' },
      mias.length ? tablaApilable({ filas: mias, columnas: [{ clave: 'tipo', titulo: 'Tipo', principal: true }, { clave: 'desde', titulo: 'Desde', celda: a => fmt.fecha(a.desde) }, { clave: 'hasta', titulo: 'Hasta', celda: a => fmt.fecha(a.hasta) }] })
        : vacio({ icono: 'cal', titulo: 'Sin ausencias registradas', texto: otra ? `${p.alias} las pide desde su ficha; las aprueba Cecilia y, si lleva clientes, Mili pone suplente.` : 'Pide aquí tus vacaciones; las aprueba Cecilia y, si llevas clientes, Mili pone suplente.' }),
      otra ? null : h('div', { class: 'pm-form', style: { marginTop: 'var(--s-3)' } }, campo('Tipo', tipo), campo('Desde', desde), campo('Hasta', hasta),
        botonConfirmar({ texto: 'Pedir ausencia', pregunta: '¿Enviar la petición?', confirmar: 'Sí, pedir', soloLectura: ctx.soloLectura,
          alConfirmar: () => apuntar(ctx, 'ausencia', p.persona_id, `${tipo.value} del ${desde.value} al ${hasta.value} (petición)`, { tipo: tipo.value, desde: desde.value, hasta: hasta.value, suplente: null, peticion: true }) }))),
    panel({ titulo: `${T.tus} notas y 1:1`, icono: 'star', sub: otra ? `Solo las ven ${p.alias}, su jefa, Cecilia, Mili y Tomás` : 'Solo las ves tú, tu jefa, Cecilia, Mili y Tomás' },
      notas.length || unos.length ? lineaTiempo([...notas.map(n => ({ fecha: n.creada, titulo: `Nota ${n.datos.nota} · ${n.datos.mes}`, detalle: `${n.datos.hecho}${n.datos.accion ? ' · Acción: ' + n.datos.accion : ''}` })),
        ...unos.map(u => ({ fecha: u.creada, titulo: `1:1 con ${u.quien}`, detalle: u.datos.puntos }))].sort((a, b) => b.fecha.localeCompare(a.fecha)))
        : vacio({ icono: 'star', titulo: 'Todavía no hay notas ni 1:1', texto: 'La nota del mes sale el día 5 con un hecho y una acción; el 1:1, al menos una vez al trimestre.' }))));
  const cel = otra ? null : panelCelebraciones(ctx);
  if (cel) cont.append(cel);
  cont.append(h('p', { class: 'sub', style: { marginTop: 'var(--s-3)' } }, icono('candado', { clase: 's' }), otra
    ? ` Nadie del equipo ve sus horas ni sus notas salvo su jefa, Cecilia, Mili y Tomás. Sin sueldos aquí.`
    : ' Nadie del equipo ve tus horas ni tus notas salvo tu jefa, Cecilia, Mili y Tomás. Sin sueldos en la app.'));
}

// ======================================================================== Atajos a las herramientas de la persona
const CU = 'https://app.clickup.com/90152357276';
/** «Abrir en …» de una persona. ClickUp no tiene enlace por usuario: abre la hoja de horas del espacio (filtrar por la persona). */
function atajosPersona(p, mini = false) {
  const a = (href, ico, txt, title) => h('a', { class: `bt mini${mini ? '' : ''}`, href, target: '_blank', rel: 'noopener', title }, icono(ico), txt);
  const out = [a(`${CU}/timesheets`, 'check', 'ClickUp ↗', `Hoja de horas de ClickUp: filtra por ${p.alias}`)];
  if (!mini) {
    out.push(a('https://zoom.us/recording', 'video', 'Zoom ↗', `Grabaciones de Zoom (busca a ${p.alias})`));
    if ((p.puestos || []).some(x => ['account', 'direccion', 'operaciones', 'jefa_publicidad', 'jefa_seo', 'jefa_crm', 'tecnico_altas'].includes(x)))
      out.push(a('https://desk.zoho.eu/agent/rankingonline836', 'inbox', 'Desk ↗', `Tickets de ${p.alias} en Zoho Desk`));
  }
  return h('span', { class: 'fila', style: { gap: 'var(--s-2)' } }, out);
}

// ======================================================================== Lista de salida (quien se va)
const SALIDA = [
  { id: 'app', texto: 'App de RO', href: '#/ajustes/personas', donde: 'Ajustes › Personas: estado «baja» (deja de entrar)', siempre: true },
  { id: 'clickup', texto: 'ClickUp', href: `${CU}/settings/users`, donde: 'Ajustes › Personas del espacio: quitar o pasar a invitado', siempre: true },
  { id: 'zoho', texto: 'Zoho (Desk, CRM y Sign)', href: 'https://directory.zoho.eu/', donde: 'Zoho Directory › Usuarios: desactivar', puestos: ['account', 'direccion', 'operaciones', 'administracion', 'tecnico_altas', 'jefa_publicidad', 'jefa_seo', 'jefa_crm'] },
  { id: 'google', texto: 'Google (correo y Drive)', href: 'https://admin.google.com/ac/users', donde: 'Consola de administración › Usuarios: suspender y pasar sus archivos', siempre: true },
  { id: 'ghl', texto: 'GoHighLevel', href: 'https://app.gohighlevel.com/settings/team', donde: 'Ajustes › Equipo de la agencia y de cada subcuenta', puestos: ['account', 'trafficker', 'especialista_ghl', 'jefa_crm', 'jefa_publicidad', 'setters', 'tecnico_altas'] },
  { id: 'meta', texto: 'Meta Business', href: 'https://business.facebook.com/settings/people', donde: 'Configuración del negocio › Personas: quitar de RO y de las cuentas de clientes', puestos: ['trafficker', 'jefa_publicidad', 'account', 'produccion', 'tecnico_altas'] },
  { id: 'zoom', texto: 'Zoom', href: 'https://zoom.us/account/user', donde: 'Gestión de usuarios: desactivar (las grabaciones se quedan en la cuenta)', siempre: true },
  { id: 'zadarma', texto: 'Zadarma', href: 'https://my.zadarma.com/mypbx/', donde: 'Centralita › Extensiones: quitar o reasignar su extensión', puestos: ['account', 'setters', 'direccion', 'operaciones'] },
  { id: 'metricool', texto: 'Metricool', href: 'https://app.metricool.com/', donde: 'Ajustes › Equipo: quitar acceso a las marcas', puestos: ['redes', 'produccion', 'jefa_seo'] },
  { id: 'snov', texto: 'Snov.io', href: 'https://app.snov.io/', donde: 'Equipo: quitar el puesto', puestos: ['outreach', 'jefa_crm'] },
];

function vistaSalida(ctx, P, cola) {
  const per = h('select', { 'aria-label': 'Persona que se va' }, P.filter(p => p.persona_id !== ctx.persona.id && !(p.puestos || []).includes('direccion')).map(p => h('option', { value: p.persona_id }, `${p.alias} · ${puestosTxt(p)}`)));
  const zona = h('div', { class: 'pila' });
  const hechos = pid => new Set(cola.filter(a => a.tipo === 'personas_salida' && (vp(a).persona_id === pid)).map(a => vp(a).herramienta));
  const pintar = () => {
    const p = P.find(x => x.persona_id === per.value);
    if (!p) return;
    const ya = hechos(p.persona_id);
    const filas = SALIDA.map(s => ({ ...s, aplica: s.siempre || (s.puestos || []).some(x => (p.puestos || []).includes(x)), hecho: ya.has(s.id) }))
      .sort((a, b) => b.aplica - a.aplica);
    zona.replaceChildren(
      h('p', { class: 'sub pm-pad' }, `${filas.filter(f => f.aplica).length} herramientas que seguramente usa por su puesto, arriba. Cada casilla queda en el rastro con tu nombre y la hora. ${Object.keys(p.cartera || {}).length ? 'Lleva clientes: reasígnalos antes en Ajustes › Asignaciones.' : ''}`),
      tablaApilable({ filas, porPagina: 0, columnas: [
        { clave: 'texto', titulo: 'Herramienta', principal: true, celda: f => h('span', {}, h('b', {}, f.texto), f.aplica ? null : h('span', { class: 'sub' }, ' · por si acaso')) },
        { clave: 'donde', titulo: 'Qué hacer', celda: f => h('span', { class: 'sub' }, f.donde) },
        { clave: 'href', titulo: 'Abrir en', celda: f => h('a', { class: 'bt mini', href: f.href, target: f.href.startsWith('#') ? null : '_blank', rel: f.href.startsWith('#') ? null : 'noopener' }, icono('ext'), f.href.startsWith('#') ? 'Abrir' : `${f.texto.split(' ')[0]} ↗`) },
        { clave: 'hecho', titulo: 'Quitado', celda: f => f.hecho ? chipEstado('verde', 'quitado') : botonConfirmar({ texto: 'Marcar quitado', mini: true, soloLectura: ctx.soloLectura,
          pregunta: `¿Acceso a ${f.texto} quitado a ${p.alias}?`, confirmar: 'Sí',
          alConfirmar: () => apuntar(ctx, 'salida', p.persona_id, `Acceso a ${f.texto} quitado a ${p.alias}`, { herramienta: f.id }) }) },
      ] }));
  };
  per.addEventListener('change', pintar);
  pintar();
  return [
    avisoParcial('Cuando alguien se va, sigue entrando en las herramientas hasta que alguien le quita el acceso. Esta lista sale de su puesto; el acceso se quita en cada herramienta (la app no lo hace sola).', { tipo: 'info', titulo: 'Para qué sirve.' }),
    panel({ titulo: 'Lista de salida', icono: 'candado', sub: 'Elige a la persona que se va' }, h('div', { class: 'pm-form' }, campo('Persona', per)), zona),
  ];
}

// ======================================================================== Sueldos (solo dirección y RRHH)
const veSueldos = ctx => ['direccion', 'rrhh'].some(x => ctx.persona.puestos.includes(x));
const ALM = 'sueldos/_privado/sueldos';
const usd = n => (n === null || n === undefined || Number.isNaN(Number(n))) ? '—' : `${fmt.num(Number(n), 0)} $`;

function vistaSueldos(ctx, P, z) {
  z.append(avisoParcial('Solo los ven dirección y RRHH. Cada vez que se abren queda en el rastro con tu nombre y la hora. Las cuentas bancarias no entran nunca en la app.', { tipo: 'parcial', titulo: 'Dato sensible.' }));
  // 1 · coste por área (se abre con un clic: deja rastro)
  const area = h('div', { class: 'pila' });
  const abrirArea = h('button', { type: 'button', class: 'bt pri', on: { click: async () => {
    abrirArea.disabled = true;
    try {
      const { valor } = await ctx.verDato({ almacen: ALM, ref: 'analisis', campo: 'filas' });
      const filas = (valor || []).slice().sort((a, b) => (b['Inversión ($)'] || 0) - (a['Inversión ($)'] || 0));
      const tot = filas.reduce((s, f) => s + (f['Inversión ($)'] || 0), 0);
      area.replaceChildren(tablaApilable({ filas, porPagina: 0, columnas: [
        { clave: 'Área', titulo: 'Área', principal: true, celda: f => limpiaTexto(f['Área']) },
        { clave: 'Miembros', titulo: 'Personas', num: true, celda: f => fmt.num(f.Miembros, 0) },
        { clave: 'Inversión ($)', titulo: 'Coste al mes', num: true, celda: f => usd(f['Inversión ($)']) },
        { clave: 'Salario medio ($)', titulo: 'Medio por persona', num: true, celda: f => usd(f['Salario medio ($)']) },
        { clave: '% del total', titulo: 'Peso', celda: f => h('div', { class: 'pm-barra' }, barraProgreso({ valor: (f['% del total'] || 0) * (f['% del total'] <= 1 ? 100 : 1), max: 100 }), h('span', {}, fmt.pct((f['% del total'] || 0) * (f['% del total'] <= 1 ? 100 : 1)))) },
      ] }), h('p', { class: 'sub' }, `Total: ${usd(tot)} al mes en ${filas.length} áreas (hoja «Análisis» del Excel de sueldos, en dólares).`));
    } catch (e) { area.replaceChildren(vacio({ icono: 'candado', titulo: 'No se pudo abrir', texto: e.message, tono: 'aviso' })); }
  } } }, icono('ojo'), 'Ver el coste por área');
  z.append(panel({ titulo: 'Coste por área', icono: 'eq', sub: 'Lo que cuesta cada área al mes y el sueldo medio' }, h('div', { class: 'pm-pad' }, abrirArea), area));

  // 2 · una persona: evolución mensual y proyección 2026
  const conSueldo = P.filter(p => p.estado !== 'baja' && !(p.puestos || []).includes('setters'));
  const per = h('select', { 'aria-label': 'Persona' }, conSueldo.map(p => h('option', { value: p.persona_id }, p.alias)));
  const zonaP = h('div', { class: 'pila' });
  const verPersona = async () => {
    zonaP.replaceChildren(h('p', { class: 'sub' }, 'Abriendo…'));
    const p = conSueldo.find(x => x.persona_id === per.value);
    let meses = null, proy = null;
    try { meses = (await ctx.verDato({ almacen: ALM, ref: p.persona_id, campo: 'meses' })).valor; } catch { meses = null; }
    try { proy = (await ctx.verDato({ almacen: ALM, ref: p.persona_id, campo: 'proyeccion' })).valor; } catch { proy = null; }
    if (!meses) { zonaP.replaceChildren(vacio({ icono: 'vacio', titulo: `Sin sueldo de ${p.alias} en el Excel`, texto: 'No figura en las hojas mensuales (o entró con otro nombre). Lo comprueba Cecilia.', quien: 'Cecilia' })); return; }
    const ms = Object.entries(meses).sort(([a], [b]) => a.localeCompare(b));
    const num = v => typeof v === 'number' ? v : null;
    zonaP.replaceChildren(
      graficoSerie({ titulo: `Sueldo de ${p.alias} por mes (dólares)`, puntos: ms.map(([m, v]) => ({ x: m + '-01', y: num(v.salario_usd) })), formato: n => usd(n) }),
      tablaApilable({ filas: ms.map(([m, v]) => ({ mes: m, ...v })), porPagina: 0, columnas: [
        { clave: 'mes', titulo: 'Mes', principal: true, celda: f => mesTxt(f.mes) },
        { clave: 'rol', titulo: 'Puesto', celda: f => limpiaTexto(f.rol || '—') },
        { clave: 'salario_usd', titulo: 'Sueldo', num: true, celda: f => typeof f.salario_usd === 'number' ? usd(f.salario_usd) : (f.salario_usd || '—') },
        { clave: 'euros', titulo: 'En euros', num: true, celda: f => f.euros === null || f.euros === undefined ? '—' : fmt.eur(f.euros) },
        { clave: 'bonus', titulo: 'Bonus', celda: f => f.bonus || '—' },
        { clave: 'pagado', titulo: 'Pagado', celda: f => chipEstado(f.pagado ? 'verde' : 'ambar', f.pagado ? 'sí' : 'pendiente') },
      ] }),
      proy ? panel({ titulo: 'Proyección 2026', icono: 'sube', sub: 'Propuesta de la hoja de proyección: sueldo base sin bonos' },
        h('dl', { class: 'pm-kv' }, h('dt', {}, 'Puesto'), h('dd', {}, limpiaTexto(proy.rol || '—')), h('dt', {}, 'Sueldo base'), h('dd', {}, usd(proy.salario_base_usd)),
          h('dt', {}, 'Por hora'), h('dd', {}, proy.salario_hora ? `${fmt.num(proy.salario_hora, 2)} $` : '—'), h('dt', {}, 'Bonus'), h('dd', {}, proy.bonus || '—'),
          h('dt', {}, 'Detalle'), h('dd', {}, limpiaTexto(proy.detalle || '—'))))
        : h('p', { class: 'sub' }, 'Sin proyección 2026 para esta persona.'));
  };
  z.append(panel({ titulo: 'Por persona', icono: 'persona', sub: 'Evolución de enero a septiembre y proyección 2026' },
    h('div', { class: 'pm-form' }, campo('Persona', per), h('button', { type: 'button', class: 'bt pri', on: { click: verPersona } }, icono('ojo'), 'Ver su sueldo')), zonaP));

  // 3 · evolución del equipo (suma de las personas de la app)
  const zonaT = h('div', { class: 'pila' });
  z.append(panel({ titulo: 'Evolución mensual del equipo', icono: 'grafico', sub: 'Suma de las personas que están en la app; los externos sin ficha cuentan en el coste por área' },
    h('div', { class: 'pm-pad' }, h('button', { type: 'button', class: 'bt', on: { click: async ev => {
      ev.target.disabled = true; zonaT.replaceChildren(h('p', { class: 'sub' }, `Abriendo ${conSueldo.length} fichas (queda en el rastro)…`));
      const tot = {}; let proyTot = 0, conProy = 0;
      for (const p of conSueldo) {
        try { for (const [m, v] of Object.entries((await ctx.verDato({ almacen: ALM, ref: p.persona_id, campo: 'meses' })).valor || {})) if (typeof v.salario_usd === 'number') tot[m] = (tot[m] || 0) + v.salario_usd; } catch { /* sin ficha */ }
        try { const pr = (await ctx.verDato({ almacen: ALM, ref: p.persona_id, campo: 'proyeccion' })).valor; if (pr && typeof pr.salario_base_usd === 'number') { proyTot += pr.salario_base_usd; conProy += 1; } } catch { /* sin proyección */ }
      }
      const ms = Object.entries(tot).sort(([a], [b]) => a.localeCompare(b));
      zonaT.replaceChildren(
        tiles([tile({ icono: 'euro', etiqueta: `Equipo en ${mesTxt(ms.at(-1)?.[0])}`, valor: usd(ms.at(-1)?.[1]), comparacion: ms.length > 1 ? { delta: ms.at(-1)[1] - ms.at(-2)[1], unidad: ' $', texto: 'frente al mes anterior', mejorSi: 'bajo' } : null, estado: '' }),
          tile({ icono: 'sube', etiqueta: 'Proyección 2026 al mes', valor: usd(proyTot), contexto: `${conProy} personas con propuesta · sueldo base, sin bonos`, estado: '' })]),
        graficoSerie({ titulo: 'Sueldos del equipo por mes (dólares)', puntos: ms.map(([m, v]) => ({ x: m + '-01', y: v })), formato: n => usd(n) }));
    } } }, icono('ojo'), 'Calcular la evolución')), zonaT));
}

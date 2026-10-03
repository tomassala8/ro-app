// modulos/horas.js · M11 Horas y productividad (E7 del plan v2 · puntos 4 y 5 de Mili · fichas G1 de Mili y Cecilia).
// Horas por persona y mes separando accounts de especialistas · imputado frente a esperado (128 h menos ausencias,
// D-25) con el sello «horas incompletas» (D-27: solo aviso) · días sin imputar · horas raras (detector de build.py)
// · horas por tipo de tarea · productividad = tareas que entraron en revisión del account / revisión del cliente /
// ver cliente / completado frente a horas, comparando a cada persona consigo misma y con su tipo de tarea.
// NUNCA un ranking general (D-83): cada uno ve la suya; la comparación, jefes, Mili, Cecilia y Tomás.
// Datos: data/horas/horas.json (fuentes_horas/generar_horas.py; ClickUp con la llave propia). Sin sueldos ni euros.
// El servidor recorta por persona (horas_persona); el cliente de una hora rara solo llega a quien ve ese cliente.

import {
  h, fmt, tile, tiles, chipEstado, chipsFiltro, pestanas, vacio, avisoParcial, panel, frescura, icono, iniciales,
  tablaDensa, copiar, fichaCatalogo, vacioLinea,
} from '../componentes.js';
import { botonDeshacer } from './_deshacer.js';   // Ronda U (50 #4)
import { selectorPersona, barras, barraMini, S, R, punto, estadoTexto, lineaFuentes, zonaTxt, ancharBuscador, dosColumnas, esMovil } from './produccion_comun.js';

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

const ID = 'horas';
const GRUPOS = ['Accounts', 'Especialistas', 'Jefes y coordinación'];   // revisión 44 (H1): con Jerónimo dentro, «Jefes»
const OBJ = 90; // objetivo de imputación de Mili para el 9-oct (ficha G1); por debajo, aviso (D-27: nunca rojo)
const estPct = p => (p === null || p === undefined ? 'gris' : p >= OBJ ? 'verde' : 'ambar');
const TIPOS_RARA = { 'Tarea con horas fuera de lo normal': 'medidor', 'Registro de más de 8 h seguidas': 'clock', 'Horas sin tarea': 'vacio', 'Horas solapadas': 'capas' };

export default {
  id: ID,
  titulo: 'Horas y productividad',
  grupo: 'Equipo',
  async render(cont, ctx) {
    vigilarCortes(cont);
    let D;
    try { D = await ctx.datosModulo('horas/horas'); } catch (e) {
      cont.append(vacio({ icono: 'alert', tono: 'aviso', titulo: 'No se han podido leer las horas', texto: String(e.message || e), quien: 'quien mantiene la app' }));
      return;
    }
    const yo = ctx.persona.id;
    // Zona horaria de cada persona: personas.json (ctx.zona) manda; si no, la que dejó el generador. Valeria → Venezuela, Sofía → España.
    const zonaDe = (pid, respaldo) => ((ctx.datos?.personas || []).find(x => x.id === pid)?.zona) || respaldo || (typeof ctx.zona === 'function' ? ctx.zona(pid) : null);
    const zonaP = p => zonaTxt(zonaDe(p.persona_id, p.zona?.zona));
    const puestos = ctx.persona.puestos || [];
    const comparar = ctx.ver({ tipo: 'comparar_personas' }).ok;
    const validar = puestos.some(p => ['direccion', 'operaciones', 'rrhh'].includes(p)) || comparar;
    // Revisión 44 (H1, H2): «Jefes y coordinación» (hay jefes y jefas) y la técnica de altas con las especialistas, no
    // con los accounts. Se corrige aquí también para los datos ya generados.
    const personas = (D.personas || []).map(p => {
      const grupo = p.grupo === 'Jefas y coordinación' ? 'Jefes y coordinación' : p.puesto === 'tecnico_altas' && p.grupo === 'Accounts' ? 'Especialistas' : p.grupo;
      const equipo = p.equipo === 'Jefas y coordinación' ? 'Jefes y coordinación' : p.puesto === 'tecnico_altas' && p.equipo === 'Accounts' ? 'Técnica de altas' : p.equipo;
      return grupo === p.grupo && equipo === p.equipo ? p : { ...p, grupo, equipo };
    });
    const propia = personas.find(p => p.persona_id === yo);
    const clienteRara = new Map((D.raras_cliente || []).map(r => [r.id, r]));
    const MESES = D.meses || [];
    const ultCerrado = MESES[MESES.length - 2];
    const nomMes = m => (personas[0]?.meses || []).find(x => x.mes === m)?.nombre_mes || m;

    ctx.titulo('Horas y productividad', comparar ? 'Por persona y mes · accounts y especialistas por separado · solo para avisar, nunca un ranking' : 'Tus horas y tu productividad frente a ti mismo · solo para avisar');

    // cola de validaciones de horas raras ya hechas (simuladas)
    const hechas = new Map();
    if (ctx.servidor) {
      try { const r = await ctx.api(`acciones?modulo=${ID}`); for (const a of (r.acciones || []).slice().reverse()) hechas.set(String(a.objeto), a); } catch { /* sin cola */ }
    }

    const F = D.fuentes || {};
    cont.append(h('div', { class: 'fila', style: { justifyContent: 'space-between', gap: `${S[2]} ${S[3]}` } },
      lineaFuentes([{ fuente: 'ClickUp horas', nombre: 'Horas', fecha: F.horas?.hora, limite_h: F.horas?.limite_h || 3 }, { fuente: 'ClickUp estados', nombre: 'Estados', fecha: F.tareas?.hora, limite_h: F.tareas?.limite_h || 8 }, F.raras?.hora ? { fuente: 'Horas raras', fecha: F.raras.hora } : null], { quien: 'Mili', como: '«Actualizar ahora»' }),
      h('span', { class: 'fila', style: { gap: S[2] } },
        h('span', { class: 'sub', title: 'De personas.json' }, `Tu zona: ${zonaTxt(zonaDe(yo, propia?.zona?.zona))}`),
        h('a', { class: 'bt mini', href: 'https://app.clickup.com/90152357276/timesheets', target: '_blank', rel: 'noopener' }, icono('ext'), 'Abrir mis horas en ClickUp'))));
    cont.append(avisoParcial(D.sello?.texto || 'Solo para avisar: lo que no se imputa no existe para la app.', { titulo: 'Horas incompletas.' }));
    const comoSeCuenta = h('details', { class: 'que-es', style: { marginTop: S[6] } },
      h('summary', { style: { minHeight: '32px', display: 'inline-flex', alignItems: 'center' } }, 'Cómo se cuentan las horas'),
      h('p', { class: 'sub', style: { maxWidth: '72ch', marginTop: S[2] } }, 'Las horas esperadas son 128 h al mes menos ausencias (todavía no hay tabla de ausencias). El día de cada registro se cuenta en la zona horaria de cada persona (la de su ficha: Argentina, Venezuela o España); el mes, en hora de España, como ClickUp.'),
      h('p', { class: 'sub', style: { maxWidth: '72ch', marginTop: S[2] } }, 'Periodo: las horas se guardan por mes completo, así que esta pantalla elige el mes con sus propios botones y no cambia con el periodo de otras pantallas. «Ayer» y «esta semana» son ventanas fijas (último día laborable y semana en curso hasta ayer); las horas raras, los últimos 30 días.'));

    if (!personas.length) {
      cont.append(vacio({ icono: 'clock', titulo: 'No hay horas tuyas que enseñar', texto: `Tu puesto no imputa horas en ClickUp (dirección y administración) o todavía no tienes registros. Tu día de trabajo se cuenta en ${zonaTxt(zonaDe(yo))}.`, quien: 'Cecilia (RRHH)' }));
      return;
    }

    // mes elegido (se queda): por defecto el último cerrado. Solo en las vistas por mes; «Ayer y esta semana» no lo usa.
    let mes = ultCerrado;
    const chipsMes = () => {
      const c = chipsFiltro({ etiqueta: 'Mes', clave: `${ID}.mes`, valor: ultCerrado,
        opciones: MESES.slice().reverse().map(m => ({ valor: m, texto: nomMes(m)[0].toUpperCase() + nomMes(m).slice(1) + (m === MESES.at(-1) ? ' (hasta ayer)' : '') })),
        alCambiar: v => { mes = v; rehacer(); } });
      mes = c.valor() || ultCerrado;
      return h('div', { class: 'fila', style: { marginTop: S[4], gap: `${S[2]} ${S[3]}` } }, c, h('span', { class: 'sub' }, 'Mes completo (ClickUp guarda las horas por mes)'));
    };
    { const c = chipsMes(); void c; }
    // filtro por puesto (Mili): account, publicidad, CRM, SEO, web, redes, producción…; se queda
    let puesto = '';
    const chipsPuesto = alCambiar => {
      const cuenta = new Map();
      for (const p of personas) cuenta.set(p.equipo, (cuenta.get(p.equipo) || 0) + 1);
      const c = chipsFiltro({ etiqueta: 'Puesto', clave: `${ID}.puesto`, opciones: [{ valor: '', texto: 'Todos', cuenta: personas.length },
        ...[...cuenta.entries()].sort((a, b) => a[0].localeCompare(b[0], 'es')).map(([e, n]) => ({ valor: e, texto: e, cuenta: n }))],
        alCambiar: v => { puesto = v; alCambiar(); } });
      puesto = c.valor();
      return c;
    };
    const dePuesto = ps => ps.filter(p => !puesto || p.equipo === puesto);
    const nom = id => ctx.nombre ? ctx.nombre(id) : id;

    let verDe = propia ? yo : personas[0].persona_id;
    const raras = D.raras || [];
    const pend = raras.filter(r => !hechas.has(r.id));
    const P = {
      imputa: { id: 'imputa', texto: 'Ayer y esta semana', icono: 'check' },
      equipo: { id: 'equipo', texto: 'Equipo por mes', icono: 'eq' },
      persona: { id: 'persona', texto: personas.length > 1 ? 'Por persona' : 'Mis horas', icono: 'persona' },
      raras: { id: 'raras', texto: 'Horas raras', icono: 'alert', cuenta: pend.length || null, cuentaEstado: 'rojo' },
    };
    const orden = (comparar && personas.length > 1) ? ['imputa', 'equipo', 'persona', 'raras'] : ['persona', 'raras'];
    const M = (p, m = mes) => (p.meses || []).find(x => x.mes === m) || {};
    let tabs;
    const zonaTabs = h('div');
    const rehacer = () => { const act = tabs?.activa(); zonaTabs.replaceChildren(); tabs = crearTabs(act); zonaTabs.append(tabs); };
    const crearTabs = act => pestanas({
      pestanas: orden.map(k => P[k]), activa: act, clave: `${ID}.pestana.${yo}`, etiqueta: 'Vistas de horas',
      pintar: (id, z) => ({ imputa: pintarImputa, equipo: pintarEquipo, persona: pintarPersona, raras: pintarRaras })[id](z),
    });
    tabs = crearTabs();
    zonaTabs.append(tabs);
    cont.append(zonaTabs, comoSeCuenta);
    const irAPersona = pid => { verDe = pid; tabs.elegir('persona'); };

    for (const el of cont.children) el.style.minWidth = '0'; // main es una rejilla: que nada estire la página en móvil

    // ================================================================ ayer y esta semana (Mili y Cecilia, diario; sin selector de mes)
    function pintarImputa(z) {
      // Definición única de la app («no imputan ayer»): personas activas que imputan horas (sin bajas ni setters),
      // 0 h el último día laborable en SU zona horaria. La misma lista que cuenta Personas.
      const cuentan = personas.filter(p => p.estado_persona === 'activo');
      const caja = h('div', { class: 'pila' });
      const chips = chipsPuesto(() => pinta());
      const fechaAyer = fDiaRO(D.ayer);
      const pinta = () => {
        const ps = dePuesto(cuentan);
        const cero = ps.filter(p => !p.ayer);
        const bajo8 = ps.filter(p => p.ayer > 0 && p.ayer < 8);
        const diasSem = ps[0]?.dias_lab_semana || 0;
        const semImp = ps.reduce((s, p) => s + p.semana, 0), semEsp = 8 * diasSem * ps.length;
        const mc = MESES.at(-1);
        const mesImp = ps.reduce((s, p) => s + (M(p, mc).imputadas || 0), 0), mesEsp = ps.reduce((s, p) => s + (M(p, mc).antes_de_imputar ? 0 : (M(p, mc).esperadas || 0)), 0);
        const indRRHH = ctx.indicador('rrhh.imputacion_del_dia_aviso_de_disciplina');
        const nBajo = cero.length + bajo8.length;
        caja.replaceChildren(...[ // lo que pide acción primero (guía 3.6): quién está por debajo; luego las cifras
          panel({ titulo: `No imputaron nada ayer · ${cero.length}`, icono: 'vacio', sub: 'A estas personas, el recordatorio. Se copia y se manda; enviarlo desde la app llegará más adelante.',
            acciones: cero.length ? h('button', { type: 'button', class: 'bt', on: { click: () => copiar(`Hola, ayer (${fechaAyer}) no imputaste horas en ClickUp. ¿Lo revisas hoy? Gracias.`, 'Recordatorio copiado') } }, icono('copy'), 'Copiar recordatorio') : null },
            cero.length ? listaPersonas(cero.sort((a, b) => a.nombre.localeCompare(b.nombre, 'es')), p => [estadoTexto('ambar', 'sin imputar'), h('span', { class: 'x' }, p.semana ? `${fmt.num(p.semana, 1)} h esta semana` : 'nada esta semana')])
              : h('div', { class: 'cuerpo' }, vacioLinea('Todos imputaron ayer: nadie a quien recordar.', { icono: 'ok' }))),
          bajo8.length ? panel({ titulo: `Imputaron menos de 8 h · ${bajo8.length}`, icono: 'clock', sub: 'Solo como aviso: puede ser media jornada o una ausencia.' },
            listaPersonas(bajo8.sort((a, b) => a.ayer - b.ayer), p => [estadoTexto('gris', `${fmt.num(p.ayer, 1)} h ayer`), h('span', { class: 'x' }, `${fmt.num(p.semana, 1)} h esta semana`)])) : null,
          tiles([
            tile({ icono: 'vacio', etiqueta: 'Sin imputar ayer', valor: cero.length, unidad: `de ${ps.length}`, estado: cero.length ? 'ambar' : 'verde',
              contexto: `0 h el ${fechaAyer}, en la zona de cada persona`, medible: 'medias', medibleDetalle: 'Mide disciplina, no rendimiento', frescura: { fuente: 'Horas de ClickUp', fecha: F.horas?.hora } }),
            tile({ icono: 'clock', etiqueta: 'Ayer por debajo de 8 h', valor: nBajo, unidad: `de ${ps.length}`, estado: nBajo === 0 ? 'verde' : nBajo <= 3 ? 'ambar' : 'rojo',
              contexto: 'Bien: 0 · vigilar: 1 a 3 · actuar: más de 3' }),
            tile({ icono: 'cal', etiqueta: 'Esta semana', valor: semEsp ? fmt.pct(semImp / semEsp * 100) : null, unidad: `${fmt.num(semImp)} h`, estado: semEsp ? estPct(semImp / semEsp * 100) : 'gris', contexto: `${diasSem} días laborables hasta ayer × 8 h` }),
            tile({ icono: 'res', etiqueta: `${nomMes(mc)[0].toUpperCase() + nomMes(mc).slice(1)} hasta ayer`, valor: mesEsp ? fmt.pct(mesImp / mesEsp * 100) : null, unidad: `${fmt.num(mesImp)} de ${fmt.num(mesEsp)} h`, estado: mesEsp ? estPct(mesImp / mesEsp * 100) : 'gris', contexto: `Objetivo de Mili: ${OBJ} % el 9 de octubre` }),
          ]),
          // el indicador del catálogo de RRHH es la tarjeta «Ayer por debajo de 8 h» (mismo número y umbral): no se repite; su «¿Qué es?», plegado al pie
          indRRHH ? h('details', { class: 'que-es' }, h('summary', { style: { minHeight: '32px', display: 'inline-flex', alignItems: 'center' } }, 'Qué es «Ayer por debajo de 8 h»'),
            h('p', { class: 'sub', style: { maxWidth: '72ch', marginTop: S[2] } }, [indRRHH.que_es || indRRHH.descripcion || indRRHH.formula, 'Indicador del catálogo de RRHH (aviso de disciplina): bien 0 · vigilar 1 a 3 · actuar más de 3.'].filter(Boolean).join(' '))) : null,
        ].filter(Boolean)); // replaceChildren pinta «null» si le llega un null: fuera
      };
      pinta();
      z.append(h('div', { class: 'pila', style: { marginTop: S[4] } },
        h('div', { class: 'fila' }, chips),
        h('p', { class: 'sub', style: { maxWidth: '72ch' } }, `Cuentan ${cuentan.length} personas: las activas que imputan horas (sin bajas ni setters). Es la misma lista que usa Personas. «Ayer» es el último día laborable en la zona horaria de cada persona (la de su ficha).`),
        caja));
    }

    // lista de personas con 8 a la vista y «Ver todas (N)» que despliega el resto (guía 3.8)
    function listaPersonas(ps, extra, visibles = 8) {
      const ul = listaPersonasTodas(ps, extra);
      if (ps.length <= visibles) return ul;
      const resto = [...ul.children].slice(visibles);
      resto.forEach(li => { li.hidden = true; });
      const bt = h('button', { type: 'button', class: 'bt', 'aria-expanded': 'false', on: { click: () => {
        const abrir = bt.getAttribute('aria-expanded') !== 'true';
        resto.forEach(li => { li.hidden = !abrir; });
        bt.setAttribute('aria-expanded', String(abrir));
        bt.replaceChildren(...(abrir ? ['Ver menos'] : [icono('mas', { clase: 's' }), `Ver todas (${fmt.num(ps.length)})`]));
      } } }, icono('mas', { clase: 's' }), `Ver todas (${fmt.num(ps.length)})`);
      return h('div', {}, ul, h('div', { class: 'cuerpo fila', style: { justifyContent: 'space-between' } }, h('span', { class: 'sub' }, `${fmt.num(visibles)} de ${fmt.num(ps.length)} a la vista`), bt));
    }
    function listaPersonasTodas(ps, extra) {
      return h('ul', { class: 'lista-i cuerpo', style: { paddingTop: S[1], paddingBottom: S[1] } }, ps.map(p => {
        const li = h('li', { tabindex: '0', style: { cursor: 'pointer' }, 'aria-label': `Ver las horas de ${p.nombre}` },
          h('span', { class: 'av s', 'aria-hidden': 'true' }, iniciales(p.nombre)),
          h('span', { class: 't pila', style: { gap: 'var(--s-1)' } }, h('b', {}, p.nombre), h('span', { class: 'sub' }, `${p.equipo} · ${zonaP(p)}`)), ...extra(p));
        li.addEventListener('click', e => { if (!e.target.closest('a,button')) irAPersona(p.persona_id); });
        li.addEventListener('keydown', e => { if (e.key === 'Enter') irAPersona(p.persona_id); });
        return li;
      }));
    }

    // ================================================================ equipo por mes (comparación: solo jefes, Mili, Cecilia y Tomás)
    function pintarEquipo(z) {
      let grupo = '';
      const chips = chipsFiltro({ etiqueta: 'Grupo', clave: `${ID}.grupo`, opciones: [{ valor: '', texto: 'Todos', cuenta: personas.length }, ...GRUPOS.map(g => ({ valor: g, texto: g, icono: g === 'Accounts' ? 'cli' : g === 'Especialistas' ? 'aj' : 'crown', cuenta: personas.filter(p => p.grupo === g).length }))],
        alCambiar: v => { grupo = v; pintarT(); } });
      grupo = chips.valor();
      const chipsP = chipsPuesto(() => pintarT());
      // serie de 7 meses por grupo (agregado de las personas que ve)
      const serie = g => MESES.map(m => {
        const ps = personas.filter(p => p.grupo === g && !M(p, m).antes_de_imputar);
        const imp = ps.reduce((s, p) => s + (M(p, m).imputadas || 0), 0), esp = ps.reduce((s, p) => s + (M(p, m).esperadas || 0), 0);
        const pct = esp ? imp / esp * 100 : null;
        return { etiqueta: nomMes(m).slice(0, 3), valor: pct === null ? null : Math.round(pct), ref: 100, estado: estPct(pct), curso: m === MESES.at(-1) };
      });
      const graf = dosColumnas( ...['Accounts', 'Especialistas'].filter(g => personas.some(p => p.grupo === g)).map(g =>
        panel({ titulo: `${g} · % imputado`, icono: 'grafico', sub: '6 meses y el actual (en claro). La raya es el 100 % de lo esperado.' },
          h('div', { class: 'cuerpo' }, barras({ puntos: serie(g), formato: v => `${fmt.num(v)} %`, titulo: `${g}: porcentaje imputado por mes`, nombreBarras: '% imputado', textoRef: '100 % de lo esperado' })))));
      const caja = h('div');
      function pintarT() {
        const ps = dePuesto(personas.filter(p => !grupo || p.grupo === grupo)).map(p => ({ ...p, m: M(p), puestoTxt: p.equipo, zonaTxt: zonaP(p) }));
        caja.replaceChildren(ancharBuscador(tablaDensa({ porPagina: esMovil() ? 8 : 15,
          filas: ps, buscar: { campos: ['nombre', 'puestoTxt'], placeholder: 'Buscar persona' }, filtros: [{ clave: 'puestoTxt', titulo: 'Equipo' }, { clave: 'zonaTxt', titulo: 'Zona' }],
          columnas: [
            { clave: 'nombre', titulo: 'Persona', principal: true, celda: p => h('span', { class: 'fila', style: { gap: S[2], flexWrap: 'nowrap' } }, h('span', { class: 'av s', 'aria-hidden': 'true' }, iniciales(p.nombre)), p.nombre) },
            { clave: 'puestoTxt', titulo: 'Equipo' },
            { clave: 'zonaTxt', titulo: 'Zona horaria' },
            { clave: 'imp', titulo: `Imputado en ${nomMes(mes)}`, ordenable: false, celda: p => p.m.antes_de_imputar ? chipEstado('gris', 'aún no imputaba') : barraMini(p.m.imputadas || 0, p.m.esperadas || 1, estPct(p.m.pct), `${fmt.num(p.m.imputadas, 0)} de ${fmt.num(p.m.esperadas, 0)} h · ${fmt.pct(p.m.pct)}`) },
            { clave: 'sin', titulo: 'Días sin imputar', num: true, ordenable: false, celda: p => p.m.dias_sin_imputar === null || p.m.dias_sin_imputar === undefined ? '—' : p.m.dias_sin_imputar ? estadoTexto('ambar', `${p.m.dias_sin_imputar} de ${p.m.dias_lab}`) : estadoTexto('verde', '0') },
            { clave: 'sintarea', titulo: 'Sin tarea', num: true, ordenable: false, celda: p => p.m.sin_tarea_h ? `${fmt.num(p.m.sin_tarea_h, 1)} h` : '—' },
            { clave: 'tareas', titulo: 'Tareas resueltas', num: true, ordenable: false, celda: p => p.m.tareas ?? '—' },
            { clave: 'hpt', titulo: 'Horas por tarea · frente a su mediana', ordenable: false, celda: p => p.m.horas_por_tarea ? h('span', { class: 'fila', style: { gap: S[2] } }, `${fmt.num(p.m.horas_por_tarea, 1)} h`, p.m.mediana_propia ? h('span', { class: 'sub' }, `(${fmt.num(p.m.mediana_propia, 1)} h)`) : null, p.m.desvio ? estadoTexto('ambar', `${p.m.desvio_pct > 0 ? '+' : ''}${fmt.num(p.m.desvio_pct)} %`) : null) : '—' },
          ],
          alPulsar: p => irAPersona(p.persona_id), etiquetaFila: p => `Ver las horas de ${p.nombre}`,
          vacio: { titulo: 'Nadie en este grupo', porque: '' },
        })));
      }
      pintarT();
      z.append(chipsMes(), h('div', { class: 'pila', style: { marginTop: S[4] } }, graf,
        panel({ titulo: `Personas · ${nomMes(mes)}`, icono: 'eq', sub: 'Por grupo y por orden alfabético: no es un ranking. La productividad se compara con la mediana de la propia persona (±50 % marca desvío). Pulsa una fila para ver su detalle.' },
          h('div', { class: 'cuerpo pila', style: { paddingBottom: S[1], gap: S[2] } }, chips, chipsP), caja)));
    }

    // ================================================================ una persona (cada uno ve la suya)
    function pintarPersona(z) {
      const cab = h('div', { class: 'fila', style: { marginTop: S[4], justifyContent: 'space-between' } });
      const zonaCab = h('span', { class: 'sub' });
      const dentro = h('div', { class: 'pila', style: { marginTop: S[4] } });
      z.append(chipsMes(), cab, dentro);
      if (personas.length > 1) cab.append(selectorPersona({ personas: personas.map(p => ({ ...p, grupo: p.grupo })), actual: verDe, etiqueta: 'Horas de', alElegir: pid => { verDe = pid; pintarP(); } }));
      cab.append(zonaCab);
      const pintarP = () => {
        dentro.replaceChildren();
        const p = personas.find(x => x.persona_id === verDe) || personas[0];
        zonaCab.replaceChildren(icono('clock', { clase: 's' }), ` Su día de trabajo se cuenta en ${zonaP(p)}`);
        const m = M(p);
        const yoMismo = p.persona_id === yo;
        const ant = (p.meses || [])[MESES.indexOf(mes) - 1];
        dentro.append(tiles([
          tile({ icono: 'clock', etiqueta: `Imputadas en ${nomMes(mes)}`, valor: m.antes_de_imputar ? null : fmt.num(m.imputadas, 1), unidad: m.antes_de_imputar ? '' : `de ${fmt.num(m.esperadas, 0)} h`,
            estado: estPct(m.pct), comparacion: ant && !ant.antes_de_imputar && !m.antes_de_imputar ? { delta: Math.round((m.pct || 0) - (ant.pct || 0)), unidad: ' puntos', texto: `frente a ${ant.nombre_mes}` } : null,
            contexto: m.antes_de_imputar ? 'Antes de su primera imputación' : `${fmt.pct(m.pct)} de lo esperado · objetivo ${OBJ} %`, medible: 'medias', medibleDetalle: 'Horas incompletas: solo para avisar', frescura: { fuente: 'ClickUp', fecha: F.horas?.hora } }),
          tile({ icono: 'hoy', etiqueta: `Ayer (${fDiaRO(p.ayer_fecha || D.ayer)})`, valor: p.ayer ? fmt.num(p.ayer, 1) : 'Sin imputar', unidad: p.ayer ? 'de 8 h' : '', estado: p.ayer >= 8 ? 'verde' : 'ambar', contexto: `En su día de trabajo (${zonaP(p)}). 8 h al día, solo para el aviso de imputar` }),
          tile({ icono: 'cal', etiqueta: 'Esta semana', valor: fmt.num(p.semana, 1), unidad: `de ${8 * p.dias_lab_semana} h`, estado: p.dias_lab_semana ? estPct(p.semana / (8 * p.dias_lab_semana) * 100) : 'gris', contexto: `${p.dias_lab_semana} días laborables hasta ayer` }),
          tile({ icono: 'vacio', etiqueta: 'Días sin imputar', valor: m.dias_sin_imputar ?? null, unidad: m.dias_lab ? `de ${m.dias_lab}` : '', estado: m.dias_sin_imputar ? 'ambar' : m.dias_sin_imputar === 0 ? 'verde' : 'gris', contexto: 'Días laborables con menos de 15 min' }),
          tile({ icono: 'check', etiqueta: 'Tareas resueltas', valor: m.tareas ?? null, unidad: m.horas_por_tarea ? `${fmt.num(m.horas_por_tarea, 1)} h por tarea` : '',
            comparacion: m.desvio_pct !== null && m.desvio_pct !== undefined ? { delta: m.desvio_pct, pct: true, texto: 'horas por tarea frente a su mediana', mejorSi: 'bajo' } : { texto: m.mediana_propia ? '' : 'Sin mediana propia todavía (hacen falta 2 meses)' },
            contexto: 'Entraron en revisión del account, del cliente, «ver cliente» o completado', medible: 'medias', medibleDetalle: D.notas?.productividad }),
          tile({ icono: 'alert', etiqueta: 'Horas raras', valor: raras.filter(r => r.persona_id === p.persona_id).length, estado: raras.some(r => r.persona_id === p.persona_id && !hechas.has(r.id)) ? 'ambar' : 'verde', contexto: '> 8 h seguidas, solapes, sin tarea o fuera de lo normal', ir: 'Ver las horas raras', alPulsar: () => tabs.elegir('raras') }),
        ]));
        if (m.desvio) dentro.append(avisoParcial(`En ${nomMes(mes)} ${yoMismo ? 'has necesitado' : 'ha necesitado'} ${fmt.num(m.horas_por_tarea, 1)} h por tarea resuelta frente a ${fmt.num(m.mediana_propia, 1)} h de ${yoMismo ? 'tu' : 'su'} mediana de los 3 meses anteriores (${m.desvio_pct > 0 ? '+' : ''}${m.desvio_pct} %). Es un aviso para hablarlo, no una nota: el tamaño de las tareas cambia mucho.`, { titulo: 'Desvío de más del 50 %.' }));
        // serie de 7 meses: imputado frente a esperado
        const pts = (p.meses || []).map(x => ({ etiqueta: x.nombre_mes.slice(0, 3), valor: x.antes_de_imputar ? null : x.imputadas, ref: x.antes_de_imputar ? null : x.esperadas, estado: x.antes_de_imputar ? 'gris' : estPct(x.pct), curso: x.en_curso }));
        dentro.append(dosColumnas(
          panel({ titulo: 'Horas por mes', icono: 'grafico', sub: 'Barra: imputadas. Raya: esperadas (128 h menos ausencias; el mes en curso, hasta ayer).' },
            h('div', { class: 'cuerpo pila' }, barras({ puntos: pts, formato: v => fmt.num(v), titulo: `Horas imputadas por mes de ${p.nombre}` }),
              h('p', { class: 'sub' }, `Objetivo de Mili: el ${OBJ} % de lo esperado (por debajo, solo aviso).`))),
          panel({ titulo: `En qué se fueron las horas · ${nomMes(mes)}`, icono: 'capas', sub: 'Por tipo de tarea (sin el cliente), como el detector de horas raras.' },
            h('div', { class: 'cuerpo' }, (m.tipos || []).length ? h('div', { style: { display: 'grid', gap: S[2] } }, m.tipos.map(t => h('div', { style: { display: 'grid', gridTemplateColumns: 'minmax(0,1fr) minmax(56px,128px) auto', gap: S[3], alignItems: 'center' } },
              h('span', { title: t.tipo, style: { overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' } }, t.tipo === 'sin tarea' ? h('b', {}, 'Sin tarea') : t.tipo[0].toUpperCase() + t.tipo.slice(1)),
              barraMini(t.horas, m.tipos[0].horas, t.tipo === 'sin tarea' ? 'ambar' : '', ''), h('span', { style: { textAlign: 'right', color: 'var(--mid)', fontWeight: '600', whiteSpace: 'nowrap' } }, `${fmt.num(t.horas, 1)} h`))))
              : vacioLinea('Sin horas este mes: no hay registros de tiempo en ClickUp.', { icono: 'vacio', quien: yoMismo ? 'tú (imputar en ClickUp)' : p.nombre })))));
        if ((m.fechas_sin_imputar || []).length) dentro.append(panel({ titulo: `Días sin imputar en ${nomMes(mes)}`, icono: 'cal', sub: 'Laborables con menos de 15 minutos. Pueden ser vacaciones o ausencias: todavía no hay tabla de ausencias.' },
          h('div', { class: 'cuerpo fila', style: { gap: S[1] } }, m.fechas_sin_imputar.map(d => chipEstado('gris', fDiaRO(d), { punto: false })))));
        // productividad: consigo misma y con su tipo de tarea
        const filasM = (p.meses || []).filter(x => !x.antes_de_imputar).slice().reverse();
        dentro.append(dosColumnas(
          panel({ titulo: 'Productividad frente a sí misma', icono: 'medidor', sub: 'Horas imputadas ÷ tareas resueltas en el mes, frente a su mediana de los 3 meses anteriores. ±50 % marca desvío.' },
            tablaDensa({ filas: filasM, apilable: true, columnas: [
              { clave: 'nombre_mes', titulo: 'Mes', principal: true, ordenable: false, celda: x => x.nombre_mes + (x.en_curso ? ' (en curso)' : '') },
              { clave: 'tareas', titulo: 'Tareas', num: true, ordenable: false },
              { clave: 'imputadas', titulo: 'Horas', num: true, ordenable: false, celda: x => fmt.num(x.imputadas, 1) },
              { clave: 'horas_por_tarea', titulo: 'h por tarea', num: true, ordenable: false, celda: x => x.horas_por_tarea ? fmt.num(x.horas_por_tarea, 1) : '—' },
              { clave: 'mediana_propia', titulo: 'Su mediana', num: true, ordenable: false, celda: x => x.mediana_propia ? fmt.num(x.mediana_propia, 1) : '—' },
              { clave: 'desvio_pct', titulo: 'Desvío', num: true, ordenable: false, celda: x => x.desvio_pct === null || x.desvio_pct === undefined ? '—' : estadoTexto(x.desvio ? 'ambar' : 'gris', `${x.desvio_pct > 0 ? '+' : ''}${fmt.num(x.desvio_pct)} %`) },
            ], vacio: { titulo: 'Sin meses con horas', porque: 'Todavía no hay registros.' } })),
          panel({ titulo: 'Con su mismo tipo de tarea', icono: 'capas', sub: 'Últimos 3 meses cerrados: horas por tarea resuelta frente a la mediana del equipo en ese mismo tipo (5 casos o más). Nunca frente a otras personas.' },
            (p.por_tipo || []).length ? tablaDensa({ filas: p.por_tipo, apilable: true, columnas: [
              { clave: 'tipo', titulo: 'Tipo de tarea', principal: true, ordenable: false, celda: x => x.tipo[0].toUpperCase() + x.tipo.slice(1) },
              { clave: 'tareas', titulo: 'Tareas', num: true, ordenable: false },
              { clave: 'horas_por_tarea', titulo: 'h por tarea', num: true, ordenable: false, celda: x => fmt.num(x.horas_por_tarea, 1) },
              { clave: 'mediana_equipo', titulo: 'Mediana del tipo', num: true, ordenable: false, celda: x => `${fmt.num(x.mediana_equipo, 1)} (${x.casos_equipo})` },
              { clave: 'desvio_pct', titulo: 'Desvío', num: true, ordenable: false, celda: x => x.desvio_pct === null ? '—' : estadoTexto(Math.abs(x.desvio_pct) > 50 ? 'ambar' : 'gris', `${x.desvio_pct > 0 ? '+' : ''}${fmt.num(x.desvio_pct)} %`) },
            ] }) : h('div', { class: 'cuerpo' }, vacioLinea('Sin tipos comparables: hacen falta 2 tareas resueltas con horas de un tipo que el equipo haya hecho 5 veces o más.', { icono: 'capas' })))));
        const misRaras = raras.filter(r => r.persona_id === p.persona_id);
        if (misRaras.length) dentro.append(panel({ titulo: 'Sus horas raras', icono: 'alert', sub: 'Del detector del panel de Mili (últimos 30 días).' }, listaRaras(misRaras)));
      };
      pintarP();
    }

    // ================================================================ horas raras (validar: Mili, Cecilia, jefes y Tomás)
    function pintarRaras(z) {
      if (!raras.length) { z.append(h('div', { style: { marginTop: S[4] } }, vacio({ icono: 'ok', tono: 'celebrar', titulo: 'Sin horas raras', texto: 'Nada fuera de lo normal en los últimos 30 días.' }))); return; }
      let tipo = '';
      const tipos = [...new Set(raras.map(r => r.tipo))];
      const chips = chipsFiltro({ etiqueta: 'Tipo', clave: `${ID}.rara`, opciones: [{ valor: '', texto: 'Todas', cuenta: raras.length }, { valor: '__pend', texto: 'Sin revisar', cuenta: pend.length, cuentaEstado: 'rojo' }, ...tipos.map(t => ({ valor: t, texto: t, icono: TIPOS_RARA[t] || 'alert', cuenta: raras.filter(r => r.tipo === t).length }))],
        alCambiar: v => { tipo = v; pinta(); } });
      tipo = chips.valor();
      const caja = h('div');
      const pinta = () => caja.replaceChildren(listaRaras(raras.filter(r => !tipo || (tipo === '__pend' ? !hechas.has(r.id) : r.tipo === tipo))));
      pinta();
      const revisadas = raras.length - pend.length;
      z.append(h('div', { class: 'pila', style: { marginTop: S[4] } },
        tiles([
          tile({ icono: 'alert', etiqueta: 'Horas raras', valor: fmt.num(raras.length), contexto: 'Últimos 30 días' }),
          tile({ icono: 'check', etiqueta: 'Revisadas', valor: fmt.pct(revisadas / raras.length * 100), unidad: `${fmt.num(revisadas)} de ${fmt.num(raras.length)}`, estado: revisadas === raras.length ? 'verde' : revisadas / raras.length > 0.5 ? 'ambar' : 'rojo', contexto: 'Catálogo de RRHH: 100 % · > 50 % · < 50 %', medible: 'hoy' }),
        ]),
        panel({ titulo: 'Horas raras por revisar', icono: 'alert', sub: validar ? 'Lo que marques (Correcto, Hablar o Error) queda en la cola simulada con tu nombre y la hora. La tarea va sin el cliente; el cliente solo lo ve quien lo lleva.' : 'Las revisa Mili, Cecilia o tu jefa. Si alguna es un error, corrígela en ClickUp.' },
          h('div', { class: 'cuerpo', style: { paddingBottom: S[1] } }, chips), caja)));
    }

    function listaRaras(rs) {
      if (!rs.length) return h('div', { class: 'cuerpo' }, vacioLinea('Nada en este filtro.', { icono: 'ok' }));
      const alias = id => personas.find(p => p.persona_id === id)?.nombre || id;
      // guía 3.8: 15 a la vista y «Ver más» (antes, hasta 120 seguidas: 22.000 px en el móvil)
      const POR = esMovil() ? 8 : 15;
      let vistas = POR;
      const ul = h('ul', { style: { listStyle: 'none', margin: '0', padding: '0', display: 'grid' } });
      const pie = h('div', { class: 'cuerpo fila', style: { justifyContent: 'space-between' } });
      const pintarL = () => {
        ul.replaceChildren(...rs.slice(0, vistas).map(filaRara));
        pie.replaceChildren(h('span', { class: 'sub' }, `${fmt.num(Math.min(vistas, rs.length))} de ${fmt.num(rs.length)}`),
          ...(vistas < rs.length ? [h('button', { type: 'button', class: 'bt', on: { click: () => { vistas += POR; pintarL(); } } }, icono('mas'), `Ver ${Math.min(POR, rs.length - vistas)} más`)] : []));
      };
      const filaRara = r => {
        const c = clienteRara.get(r.id);
        const hecha = hechas.get(r.id);
        return h('li', { style: { display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: `${S[2]} ${S[3]}`, padding: `${S[3]} ${S[5]}`, borderBottom: '1px solid var(--line-soft)' } },
          h('span', { class: 'ico-c s ambar', title: r.tipo }, icono(TIPOS_RARA[r.tipo] || 'alert', { clase: 's' })),
          h('div', { style: { flex: '1 1 260px', minWidth: '0', display: 'grid', gap: S[1] } },
            h('b', { style: { overflowWrap: 'anywhere' } }, `${alias(r.persona_id)} · ${fmt.num(r.horas, 1)} h · ${r.tipo}`),
            h('div', { class: 'fila sub', style: { gap: `${S[1]} ${S[3]}` } },
              h('span', { style: { overflowWrap: 'anywhere' } }, c ? c.tarea_completa : r.tarea),
              c ? h('span', { class: 'fila', style: { gap: S[1], flexWrap: 'nowrap', fontWeight: '600', color: 'var(--mid)' } }, icono('cli', { clase: 's' }), c.cliente) : null,
              h('span', {}, fDiaRO(r.fecha))),
            h('div', { class: 'sub' }, r.motivo)),
          h('div', { class: 'fila', style: { gap: S[2], flex: 'none' } },
            r.url ? h('a', { class: 'bt mini', href: r.url, target: '_blank', rel: 'noopener' }, icono('ext'), 'ClickUp') : null,
            hecha ? chipEstado('verde', `${(hecha.tipo || '').replace('hora_rara_', '')} · ${hecha.quien}`) :
              // Ronda U (50 #4): Correcto / Hablar / Error al primer clic, con «Deshacer» 8 s (antes «¿Marcar como…? Sí»)
              validar ? ['Correcto', 'Hablar', 'Error'].map(dec => botonDeshacer({ texto: dec, hecho: dec, soloLectura: ctx.soloLectura, pri: dec === 'Correcto',
                alHacer: async () => { await ctx.accion({ herramienta: 'app', tipo: `hora_rara_${dec.toLowerCase()}`, objeto: r.id, texto: dec, vista_previa: { decision: dec, registro: r.id } }); hechas.set(r.id, { tipo: `hora_rara_${dec.toLowerCase()}`, quien: ctx.persona.alias || 'tú' }); return 'Apuntado (simulación)'; } })) : chipEstado('gris', 'Sin revisar')));
      };
      pintarL();
      return h('div', {}, ul, rs.length > POR ? pie : null);
    }
  },
};

import { panelPlanningObservado360 } from './_planning_observado_360.js';
import { panelComparacionSemanal296 } from './_produccion_creadas_287.js';
import { metricasProyectoBaseline, sumarMetricaBaseline, planificacionBaseline, tablaProduccionBaseline, fuenteProduccionBaseline, CSS_PRODUCCION_BASELINE } from './_produccion_baseline.js';
import { resumirAccountsProduccion237, textoRevisionAccount237 } from './_produccion_accounts_237.js';
// modulos/produccion.js · M10 Producción (E7 del plan v2; ficha G3 «Producción creativa»; Mili, bloque 5 de su «Mi día»).
// Cola de cada persona (hoy y semana, por fecha y prioridad) · revisión del account y técnica (48 h) · bloqueadas ·
// devueltas · piezas a la primera y en fecha · trabajo no planificado (D-24) · carga frente a 12/16 (D-07) ·
// rendimiento de sus anuncios en índice, sin euros (D-82), con el aviso «parcial: no consta quién hizo cada pieza».
// Datos: data/produccion/produccion.json (fuentes_produccion/generar_produccion.py, ClickUp con la llave propia).
// El servidor recorta: cola y carga por persona (la suya; jefes, su gente; Mili, Cecilia y Tomás, todo);
// proyectos y revisiones por cliente (quien ve ese cliente). Botones: ctx.accion() → cola «simulada»; nada se escribe en ClickUp.

import { llevarA } from './_ir.js';
import { TOPE_CARTERA } from './_constantes_ro.js';   // L-34
import { prepararRevisionProduccion206, crearIntencionRevision206, validarReciboRevision206 } from './_transicion_produccion_206.js';
import {
  h, fmt, tile, tiles, chipEstado, chipsFiltro, pestanas, vacio, avisoParcial, panel, frescura, icono, iniciales,
  tablaDensa, logoCliente, botonConfirmar, fichaCatalogo, pieFase2, semaforo, vacioLinea, campoTexto,
} from '../componentes.js';
import { REGLAS } from '../permisos.js';
import { botonDeshacer } from './_deshacer.js';
import { fichaMarca } from './produccion_comun.js';
import { pantallaAncha, franjaEnLinea } from './_trabajo_ancho.js';
import { selectorPersona, barraMini, prioridad, vence, chipDias, estadoTxt, PUESTO_TXT, S, R, punto, estadoTexto, lineaFuentes, etiquetasDe, cuentagotas, ancharBuscador, esMovil, GRUPOS_AHORA, alDia, diaCortoTxt, revisionesDelAccount } from './produccion_comun.js';

// 137 · Contadores de proyecto sólo con medición específica, nunca con defaults heredados.
const fechaRevision137 = (sello, hoy) => {
  if (typeof sello !== 'string' || typeof hoy !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(hoy)) return false;
  const dia = sello.slice(0, 10);
  if (!/^\d{4}-\d{2}-\d{2}$/.test(dia) || dia > hoy) return false;
  const d = new Date(`${dia}T00:00:00Z`);
  return !Number.isNaN(+d) && d.toISOString().slice(0, 10) === dia && !Number.isNaN(+new Date(sello.replace(' ', 'T')));
};
export function medicionRevisionProyecto137(p, fuentes, hoy, tipo = 'account') {
  const m = p?.[`revisiones_${tipo}`], fecha = fuentes?.flujo?.hora;
  const n = p?.[`rev_${tipo}`], mas48 = p?.[`rev_${tipo}_48`];
  return m?.estado === 'medido' && m.fuente === 'flujo' && m.fecha === fecha && fechaRevision137(fecha, hoy)
    && Number.isInteger(n) && n >= 0 && Number.isInteger(mas48) && mas48 >= 0 && mas48 <= n ? { n, mas48, fecha } : null;
}
export function prepararRevisionesProyectos137(filas, fuentes, hoy) {
  return (Array.isArray(filas) ? filas : []).filter(p => p && typeof p === 'object').map(p => {
    const a = medicionRevisionProyecto137(p, fuentes, hoy), t = medicionRevisionProyecto137(p, fuentes, hoy, 'tecnica');
    return { ...p, rev_account: a?.n ?? null, rev_account_48: a?.mas48 ?? null,
      rev_tecnica: t?.n ?? null, rev_tecnica_48: t?.mas48 ?? null, _revision_account: a, _revision_tecnica: t };
  });
}
export function resumenRevisionesProyectos137(filas) {
  const conRevision = filas.filter(p => (p._revision_account?.mas48 || 0) > 0 || (p._revision_tecnica?.mas48 || 0) > 0);
  const sinDato = filas.filter(p => !p._revision_account || !p._revision_tecnica).length;
  return { conRevision, sinDato, valor: conRevision.length || (!sinDato && filas.length ? 0 : null),
    estado: conRevision.length ? 'ambar' : sinDato || !filas.length ? 'gris' : 'verde',
    detalle: `${filas.length - sinDato} proyectos con ambas mediciones · ${sinDato} con alguna revisión sin dato. Copia parcial; no acredita inventario completo.` };
}
export function medicionFilasRevision137(filas, fuentes, hoy) {
  const fuenteValida = Array.isArray(filas) && fechaRevision137(fuentes?.tareas?.hora, hoy);
  const edadesValidas = Array.isArray(filas) && filas.every(r => typeof r.dias === 'number' && Number.isFinite(r.dias) && r.dias >= 0 && typeof r.mas48 === 'boolean');
  const medido = fuenteValida && edadesValidas;
  return { medido, valor: medido ? filas.filter(r => r.mas48).length : null,
    estado: medido && filas.some(r => r.mas48) ? 'ambar' : 'gris',
    detalle: medido ? `${filas.length} filas observadas en la copia de ${fuentes.tareas.hora}; cobertura parcial.` : 'Sin medición de edad acreditada: falta sello de tareas o campos de las filas. No equivale a cero.' };
}

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

const ID = 'produccion';
const urlTarea = r => r.url || `https://app.clickup.com/t/${encodeURIComponent(r.id)}`; // atajo «Abrir en ClickUp»
const GRUPOS = [
  { valor: 'vencida', texto: 'Vencidas', icono: 'alert' },
  { valor: 'hoy', texto: 'Para hoy', icono: 'zap' },
  { valor: 'semana', texto: 'Esta semana', icono: 'cal' },
  { valor: 'bloqueada', texto: 'Bloqueadas', icono: 'candado' },
  { valor: 'revision', texto: 'Esperando revisión', icono: 'clock' },
  { valor: 'despues', texto: 'Más adelante', icono: 'capas' },
  { valor: 'olvidada', texto: 'Olvidadas (> 30 días)', icono: 'hist' },
];

// La raíz pertenece a una única navegación e identidad; el contenedor principal se reutiliza.
export function montarVistaVigente(cont, ctx) {
  const raiz = h('div', { class: 'pila', 'data-vista-operativa': ID });
  cont.replaceChildren(raiz);
  const identidad = [ctx.persona?.id, ctx.real?.id, !!ctx.soloLectura];
  const ruta = typeof location === 'undefined' ? null : location.hash;
  const vigente = () => raiz.isConnected && raiz.parentNode === cont &&
    (typeof ctx.vigente !== 'function' || ctx.vigente()) &&
    (ruta === null || location.hash === ruta) &&
    identidad[0] === ctx.persona?.id && identidad[1] === ctx.real?.id && identidad[2] === !!ctx.soloLectura;
  return { raiz, vigente };
}

export function estadoAccionLocal(a) {
  const estado = a?.envio_estado !== undefined && a.envio_estado !== null
    ? a.envio_estado : a?.estado;
  const remoto = a?.envio_estado !== undefined && a.envio_estado !== null;
  const conocido = remoto || ['simulada', 'simulado', 'pendiente', 'ok'].includes(estado);
  const textos = { simulada: 'Simulación local · sin envío confirmado', simulado: 'Simulación local · sin envío confirmado',
    pendiente: 'Pendiente · sin envío confirmado', enviado: 'Enviado · confirmación pendiente',
    confirmado: 'Envío confirmado · contrastar resultado en ClickUp', ok: 'Registro local · sin confirmación del proveedor' };
  return { valida: conocido && Object.hasOwn(textos, estado), estado, texto: (conocido && textos[estado]) || 'Acción no confirmada; revisar Envíos',
    confirmada: a?.envio_estado === 'confirmado' };
}

export function decisionesVisibles(acciones, bases, tipos) {
  const permitidas = new Map(bases.map(x => [String(x.id), x]));
  const out = new Map();
  // GET acciones devuelve id DESC. La última acción sustituye la anterior, incluso si falla.
  for (const a of (acciones || []).slice().reverse()) {
    const id = String(a.objeto), base = permitidas.get(id);
    if (!base || !tipos.includes(a.tipo)) continue;
    const cli = base.cli ?? base.cliente_id;
    if (a.cliente_id && a.cliente_id !== cli) continue;
    const estado = estadoAccionLocal(a);
    out.delete(id);
    if (estado.valida) out.set(id, { ...a, seguimiento: estado });
  }
  return out;
}

export async function registrarAccionVigente(ctx, vigente, accion) {
  if (!vigente() || ctx.soloLectura || !ctx.servidor) throw new Error('Vista obsoleta o sólo lectura: no se guarda la acción.');
  const respuesta = await ctx.accion(accion);
  if (!vigente()) throw new Error('La vista ha cambiado; revisa el registro local en Envíos.');
  if (respuesta?.ok !== true || !estadoAccionLocal(respuesta).valida) throw new Error('La acción no tiene un registro válido confirmado por el servidor; revisa Envíos.');
  return respuesta;
}

//211: intenciones en memoria de la pestaña, separadas por identidad y tarea.
//No persiste comentarios en almacenamiento del navegador ni fabrica confirmaciones.
const INTENCIONES_REVISION211 = new Map();
export function piezaRevision211(t, datos) {
  const token = datos?.transiciones_revision?.[t?.id];
  if (!token || token.modulo !== 'produccion' || token.tarea_id !== t?.id || token.cliente_id !== t?.cli
      || token.expected_estado !== t?.estado || typeof token.lista_id !== 'string' || typeof token.tipo_estado !== 'string'
      || (t.lista_id != null && t.lista_id !== token.lista_id) || (t.tipo_estado != null && t.tipo_estado !== token.tipo_estado)) return null;
  return { ...t, lista_id: token.lista_id, tipo_estado: token.tipo_estado };
}
export function crearControlRevision211(ctx, vigente, datos, uuid = () => globalThis.crypto?.randomUUID?.()) {
  const identidad = JSON.stringify([ctx.real?.id, ctx.persona?.id, !!ctx.soloLectura, !!ctx.pilotoLectura]);
  const key = t => JSON.stringify([identidad, t?.id]);
  const actual = () => vigente() && ctx.servidor && !ctx.soloLectura && !ctx.pilotoLectura
    && ctx.real?.id === ctx.persona?.id && ctx.veModulo?.('produccion') === true;
  const permiso = (t, tipo) => {
    const p = piezaRevision211(t, datos);
    return p ? prepararRevisionProduccion206(ctx, p, tipo, datos?.capacidad_revision,
      datos?.transiciones_revision?.[t.id], datos?.estados_detalle) : { ok: false, motivo: 'No hay copia y permiso de revisión confirmados para esta pieza. Abrir en ClickUp o actualizar.' };
  };
  const estado = t => INTENCIONES_REVISION211.get(key(t));
  async function enviar(t, tipo, comentario = '') {
    if (!actual() || datos?.capacidad_revision?.activo !== true) throw Error('Revisión no habilitada o pantalla obsoleta: no se guarda.');
    let req = estado(t);
    if (req?.enCurso) throw Error('Esta intención ya está en curso.');
    if (req && (req.pieza.cli !== t.cli || (t.lista_id != null && req.pieza.lista_id !== t.lista_id))) throw Error('La pieza cambió de cliente o lista: revisar Envíos, sin reenviar este contenido.');
    if (req?.resultado) return req.resultado;
    if (req && req.intento.payload.tipo !== tipo) throw Error('Hay otra intención sin confirmar para esta pieza. Revisar Envíos antes de decidir otra cosa.');
    if (!req) {
      const p = permiso(t, tipo);
      if (!p.ok) throw Error(p.motivo);
      const intento = crearIntencionRevision206(ctx, piezaRevision211(t, datos), p, uuid(), comentario);
      req = { intento: JSON.parse(JSON.stringify(intento)), pieza: { cli: t.cli, lista_id: piezaRevision211(t, datos).lista_id }, enCurso: false, resultado: null };
      INTENCIONES_REVISION211.set(key(t), req);
    }
    req.enCurso = true;
    try {
      // Retry siempre conserva payload, comentario, revisión y UUID originales.
      const respuesta = await ctx.accion(JSON.parse(JSON.stringify(req.intento.payload)));
      if (!actual()) throw Error('La vista cambió: revisar Envíos. La respuesta no se aplica a esta pantalla.');
      const recibo = validarReciboRevision206(respuesta, req.intento);
      if (!recibo.valido) throw Error(respuesta?.requiere_revision
        ? 'Guardado local sin cambio enviable confirmado: revisar fuente y Envíos. No crear otra intención.'
        : 'Sin recibo durable confirmado: revisar Envíos o reintentar la misma intención.');
      const textos = {simulado:'Registrado en RO · simulación, sin envío confirmado a ClickUp',pendiente:'Registrado en RO · pendiente de ClickUp',
        enviado:'Enviado · pendiente de comprobar en ClickUp',confirmado:recibo.confirmacion_remota?'Releído y confirmado en ClickUp':'Registro local confirmado; sin confirmación remota acreditada',
        fallido:'Cambio fallido · revisar Envíos',conflicto:'Conflicto · revisar Envíos',descartado:'Cambio descartado · revisar Envíos'};
      req.resultado = { ...recibo, tipo, texto: textos[recibo.estado], respuesta };
      return req.resultado;
    } finally { req.enCurso = false; }
  }
  return { permiso, estado, enviar };
}

export default {
  id: ID,
  titulo: 'Producción',
  grupo: 'Equipo',
  async render(cont, ctx) {
    const vista = montarVistaVigente(cont, ctx);
    const vigente = vista.vigente;
    cont = vista.raiz;
    vigilarCortes(cont);
    // 351 · Las fuentes se leen antes de pintar; una espera no debe parecer una página vacía.
    const carga351 = h('p', { class: 'sub', role: 'status', 'data-produccion-carga': '351' }, 'Cargando producción y revisiones…');
    cont.append(carga351);
    let D;
    try { D = alDia(await ctx.datosModulo('produccion/produccion'), ctx.hoy || undefined); } catch (e) {
      if (!vigente()) return;
      carga351.remove();
      cont.append(vacio({ icono: 'alert', tono: 'aviso', titulo: 'No se han podido leer los datos de producción', texto: String(e.message || e), quien: 'quien mantiene la app' }));
      return;
    }
    if (!vigente()) return;
    let datosRevision = { capacidad_revision: { activo: false, version: '206.1' }, transiciones_revision: {}, estados_detalle: {} };
    if (ctx.servidor && ctx.api) {
      try { datosRevision = await ctx.api('produccion/transiciones'); } catch { /* capacidad desconocida: sin botones mutantes */ }
      if (!vigente()) return;
    }
    const controlRevision = crearControlRevision211(ctx, vigente, datosRevision);
    const accionRevision = (t, tipo, comentario = '') => {
      const caja = h('span', { class: 'pila', style: { gap: S[1] } });
      const pintar = () => {
        if (!vigente()) return;
        const req = controlRevision.estado(t), p = controlRevision.permiso(t, tipo);
        const enviado = req?.resultado;
        const mismo = !req || req.intento.payload.tipo === tipo;
        const listo = mismo && !req?.enCurso && (req ? datosRevision?.capacidad_revision?.activo === true && !ctx.soloLectura && !ctx.pilotoLectura : p.ok);
        const b = h('button', { type: 'button', class: 'bt mini', disabled: !listo || !!enviado,
          title: !mismo ? 'Otra intención pendiente: revisar Envíos.' : p.motivo || '', on: { click: async () => {
            if (!vigente() || !caja.isConnected) return;
            b.disabled = true;
            try { await controlRevision.enviar(t, tipo, comentario); } catch (e) {
              if (vigente() && caja.isConnected) { pintar(); caja.append(h('span', { class: 'estado error', role: 'alert' }, e?.message || 'Sin recibo confirmado: revisar Envíos.')); }
              return;
            }
            if (vigente() && caja.isConnected) pintar();
          } } }, req && !enviado ? 'Reintentar misma intención' : tipo === 'pieza_aprobar' ? 'Aprobar' : tipo === 'pieza_pedir_cambios' ? 'Guardar petición' : 'A revisión');
        caja.replaceChildren(b);
        if (enviado) caja.append(h('span', { class: 'sub', role: 'status' }, enviado.texto));
        else if (req) caja.append(h('span', { class: 'sub' }, req.enCurso ? 'Guardando; aún sin recibo confirmado…' : 'Hay una intención sin recibo confirmado. El reintento conserva el contenido original.'));
        else if (!p.ok) caja.append(h('span', { class: 'sub' }, p.motivo));
        if (req) caja.append(h('a', { href: '#/envios', class: 'sub' }, 'Revisar Envíos'));
      };
      pintar(); return caja;
    };
    const yo = ctx.persona.id;
    const puestos = ctx.persona.puestos || [];
    // Ronda U (#13): marca y brief del cliente dentro de la tarea (data/produccion/marca.json, recortado por cliente) y los
    // pedidos de creatividades de publicidad (acciones de Captación que la persona puede ver).
    const MARCA = new Map();
    // primero el fichero propio (clientes de tus tareas y tu cartera); quien ve los clientes (dirección, jefas), el general
    try { const r = await ctx.datosModulo(`produccion/marca/p_${yo}`); if (!vigente()) return; for (const m of r?.clientes || []) MARCA.set(m.cli, m); } catch { /* sin fichero propio */ }
    if (!vigente()) return;
    try { const r = await ctx.datosModulo('produccion/marca'); if (!vigente()) return; for (const m of r?.clientes || []) if (!MARCA.has(m.cliente_id)) MARCA.set(m.cliente_id, m); } catch { /* sin marca: la fila lo dice */ }
    if (!vigente()) return;
    const PEDIDOS = new Map();
    if (ctx.servidor && ctx.api && ctx.veModulo?.('captacion')) {
      try {
        const r = await ctx.api('acciones?modulo=captacion');
        if (!vigente()) return;
        for (const a of r.acciones || []) {
          if (a.tipo !== 'tarea' || !String(a.vista_previa || '').includes('pedido_creatividad') || !a.cliente_id) continue;
          let vp = {}; try { vp = JSON.parse(a.vista_previa); } catch { /* texto */ }
          (PEDIDOS.get(a.cliente_id) || PEDIDOS.set(a.cliente_id, []).get(a.cliente_id)).push({ ...a, vp });
        }
      } catch { /* sin pedidos */ }
    }
    // Producción no «abre» el cliente: los pedidos le llegan por #avisos-redes (avisos.py los publica para su puesto con el brief)
    if (ctx.servidor && ctx.api) {
      try {
        const r = await ctx.api('canales/canal?id=avisos-redes');
        if (!vigente()) return;
        for (const msg of r.mensajes || []) {
          const pd = msg.pedido;
          if (!pd?.cliente_id || [...(PEDIDOS.get(pd.cliente_id) || [])].some(a => String(a.id) === String(pd.id))) continue;
          (PEDIDOS.get(pd.cliente_id) || PEDIDOS.set(pd.cliente_id, []).get(pd.cliente_id)).push({ id: pd.id, cliente_id: pd.cliente_id, quien: pd.quien, creada: pd.creada, texto: pd.brief,
            vp: { pedido_creatividad: true, para: pd.para, formatos: pd.formatos, anuncio: pd.anuncio, brief: pd.brief } });
        }
      } catch { /* sin canal: solo los de Captación */ }
    }
    if (!vigente()) return;
    carga351.remove();
    const comparar = ctx.ver({ tipo: 'comparar_personas' }).ok;
    const soloRRHH = puestos.includes('rrhh') && !puestos.some(p => ['direccion', 'operaciones'].includes(p));
    const dir = puestos.some(p => ['direccion', 'operaciones', 'proyectos'].includes(p));
    const cliNombre = new Map(ctx.clientes.map(c => [c.id, c]));
    const alias = id => (ctx.nombre ? ctx.nombre(id) : id);
    const accountDe = id => (ctx.verdad ? ctx.verdad(id)?.account : null) ?? null; // verdad única: account principal vigente
    // «transversal» (personas.json → etiquetas): trabaja para varias áreas, responde ante su jefe y no tiene cartera propia (Camilo, copy).
    const transversal = id => etiquetasDe(ctx, id).includes('transversal');
    const personas = (D.personas || []).map(p => ({ ...p, grupo: PUESTO_TXT[p.puesto] || p.puesto, transversal: transversal(p.persona_id) }));
    // V2: en tu propia cola, en segunda persona y sin la palabra «transversal» (jerga)
    const notaTransversal = p => (p.persona_id === yo
      ? `Escribes para varias áreas y respondes ante ${p.jefe ? alias(p.jefe) : 'tu jefa'}. No llevas clientes propios: tu carga es tu cola.`
      : `Escribe para varias áreas y responde ante ${p.jefe ? alias(p.jefe) : 'su jefa'}. No lleva clientes propios: su carga es su cola.`);
    const propia = personas.find(p => p.persona_id === yo);

    ctx.titulo('Producción', 'Tareas, revisiones y plazos de tu equipo');

    // ---- cabecera: frescura de cada fuente ----
    // R14 · UN solo sello: la hora real de cada fuente y su límite (el de data/fuentes.json, el mismo de los consejos).
    // Antes decía «Datos al día» aunque las revisiones vinieran del panel de las 09:16 y el consejo avisara «hace 12 h».
    const F = D.fuentes || {};
    const LIMITE = { tareas: 8, horas: 3, flujo: 8, anuncios: 30 };   // por si el JSON es de antes de R14
    const NOMBRE_F = { tareas: 'Colas', horas: 'Horas', flujo: 'Revisiones y proyectos', anuncios: 'Anuncios de Meta' };
    const fuenteDe = k => (F[k]?.hora || k !== 'anuncios') ? { fuente: F[k]?.fuente || k, nombre: NOMBRE_F[k], fecha: F[k]?.hora || null, limite_h: F[k]?.limite_h || LIMITE[k] } : null;
    const ctxN = [];   // Ronda U (#1): fuentes, avisos e indicadores DEBAJO de la cola (pantallaAncha); el consejo de la IA, plegado ahí
    ctxN.push(lineaFuentes(['tareas', 'flujo', 'horas', 'anuncios'].map(fuenteDe),
      h('p', { class: 'sub', style: { margin: '0', maxWidth: '72ch' } }, `Foto de ClickUp, no un periodo: los porcentajes son de los últimos 30 días y no cambian con el periodo de otras pantallas. Pantalla preparada el ${fDiaHoraRO(D.generado)}.`),
      { quien: 'Mili', como: '«Actualizar ahora»' }));
    if (D.notas?.estados?.fecha) ctxN.push(lineaFuentes([{ fuente: D.notas.estados.fuente, nombre: 'Estados por lista', fecha: D.notas.estados.fecha, limite_h: LIMITE.tareas }], { quien: 'Mili', como: 'Contrastar catálogo y tareas en ClickUp' }));
    ctxN.push(avisoParcial('Copia parcial de tareas. Los hitos de revisión o cierre no acreditan entrega aceptada ni rendimiento personal. Backlog sin fecha cercana y tareas no asignadas quedan fuera de esta cola; usa ClickUp para el inventario completo. Los porcentajes históricos requieren contrastar estados por lista.', { tipo: 'info', titulo: 'Alcance de esta vista.' }));
    if (D.dato_de && D.dato_de < D.hoy) ctxN.push(avisoParcial(`Las tareas son de ClickUp del ${diaCortoTxt(D.dato_de)}. Las fechas se cuentan con hoy, ${diaCortoTxt(D.hoy)}: lo que vencía el ${diaCortoTxt(D.dato_de)} ya sale en «Vencidas».`, { tipo: 'info' }));

    // ---- pestañas por frecuencia de uso de cada puesto ----
    const proyectos = prepararRevisionesProyectos137(D.proyectos, F, D.hoy);
    const revisiones = D.revisiones || [];
    // V2 (A-A5): a un account, la pestaña cuenta SUS revisiones de más de 48 h (la misma cifra que Mi día); a quien dirige, todas
    const revMias = revisionesDelAccount(D, yo);
    const esAccountSolo = puestos.includes('account') && !puestos.some(p => ['direccion', 'operaciones', 'proyectos'].includes(p));
    const cuentaRev = medicionFilasRevision137(Array.isArray(D.revisiones) ? (esAccountSolo ? revMias.todas : D.revisiones) : undefined, F, D.hoy).valor;
    const piezas = piezasPorRevisar();
    const meToca = piezas.filter(x => x.toca && x.vigente).length;
    const P = {
      porrevisar: { id: 'porrevisar', texto: 'Por revisar', icono: 'check', cuenta: meToca || null },
      cola: { id: 'cola', texto: personas.length > 1 ? 'Colas' : 'Mi cola', icono: 'capas', cuenta: (propia?.vencidas || 0) || null, cuentaEstado: 'rojo' },
      revisiones: { id: 'revisiones', texto: 'Revisiones 48 h', icono: 'clock', cuenta: cuentaRev || null, cuentaEstado: 'rojo' },
      proyectos: { id: 'proyectos', texto: 'Por proyecto', icono: 'cli' },
      equipo: { id: 'equipo', texto: 'Carga del equipo', icono: 'eq' },
      anuncios: { id: 'anuncios', texto: 'Mis piezas en Meta', icono: 'grafico' },
    };
    let orden;
    if (soloRRHH) orden = ['equipo', 'cola'];
    else if (dir) orden = ['revisiones', 'proyectos', 'equipo', 'cola', 'anuncios'];
    else if (puestos.includes('account') && !comparar) orden = ['revisiones', 'cola', 'proyectos', 'anuncios']; // lo que le toca a un account: sus revisiones en 48 h
    else if (comparar) orden = ['equipo', 'cola', 'revisiones', 'proyectos', 'anuncios'];
    else orden = ['cola', 'revisiones', 'proyectos', 'anuncios'];
    if (!proyectos.length && !revisiones.length) orden = orden.filter(x => x !== 'revisiones' && x !== 'proyectos');
    if (!personas.length) orden = orden.filter(x => x !== 'cola' && x !== 'equipo');
    if (!comparar && !soloRRHH) orden = orden.filter(x => x !== 'equipo');
    if (!orden.includes('anuncios') && !soloRRHH) orden.push('anuncios');
    if (soloRRHH) orden = orden.filter(x => x !== 'anuncios');
    // R14 · «Por revisar»: primera para quien revisa (account, jefas, Mili, Tomás); segunda para quien produce (sus piezas
    // esperando a otros). RRHH no revisa piezas.
    if (!soloRRHH && piezas.length) {
      if (meToca || dir) orden.unshift('porrevisar');
      else orden.splice(Math.min(1, orden.length), 0, 'porrevisar');
    }
    if (!(dir || comparar)) P.anuncios.texto = 'Mis piezas en Meta'; else P.anuncios.texto = 'Piezas en Meta';
    if (!orden.length) {
      cont.append(vacio({ icono: 'capas', titulo: 'No hay producción que enseñarte', texto: 'Tu puesto no tiene tareas en ClickUp ni clientes con trabajo abierto.', quien: 'Mili (asignaciones)' }));
      return;
    }

    let colaDe = propia ? yo : personas[0]?.persona_id;
    // #/produccion/<id de tarea> o #/produccion/tarea/<id> (R15a, «Ir» de los consejos): abre la cola de su dueño y la señala
    // Ronda U (#5 y #11): #/produccion/pedido/<id> (el aviso de #avisos-redes) abre ESE pedido de creatividades con su brief
    // y la marca del cliente, arriba de la cola.
    let pedidoAbierto = null;
    if (ctx.params?.[0] === 'pedido') {
      const idp = String(ctx.params?.[1] || '');
      for (const l of PEDIDOS.values()) for (const a of l) if (String(a.id) === idp) pedidoAbierto = a;
      if (!pedidoAbierto) cont.append(avisoParcial('Ese pedido de creatividades no es de un cliente que puedas abrir (o ya no está en los últimos días).', { titulo: 'No lo encuentro.' }));
    }
    let resaltar = ctx.params?.[0] === 'pedido' ? null : (ctx.params?.[0] === 'tarea' ? ctx.params?.[1] : ctx.params?.[0]) || null;
    if (resaltar) {
      const fila = (D.cola || []).find(r => r.id === resaltar && r.persona_id === yo) || (D.cola || []).find(r => r.id === resaltar);
      if (fila) { colaDe = fila.persona_id; try { sessionStorage.setItem(`ro.chips.${ID}.grupo`, JSON.stringify([fila.grupo])); sessionStorage.setItem(`ro.pestana.${ID}.pestana.${yo}`, 'cola'); } catch { /* sin almacenamiento */ } }
      else { cont.append(avisoParcial('Esta tarea no está en ninguna cola que puedas ver (puede estar cerrada, pendiente sin fecha o ser de otra persona).', { titulo: 'No la encuentro.' })); resaltar = null; }
    }
    let tabs;
    const irACola = pid => { colaDe = pid; tabs.elegir('cola'); tabs.querySelector('[role=tabpanel]')?.scrollIntoView({ behavior: 'smooth', block: 'start' }); };

    tabs = pestanas({
      pestanas: orden.map(k => P[k]), clave: `${ID}.pestana.${yo}${ctx.operacionesVista ? '.operaciones' : ''}`, activa:ctx.operacionesVista === 'proyectos' ? 'proyectos' : undefined, etiqueta: 'Vistas de producción', unaFila: true,
      pintar: (id, z) => {
        if (id === 'porrevisar') pintarPorRevisar(z);
        if (id === 'cola') pintarCola(z);
        if (id === 'revisiones') pintarRevisiones(z);
        if (id === 'proyectos') pintarProyectos(z);
        if (id === 'equipo') pintarEquipo(z);
        if (id === 'anuncios') pintarAnuncios(z);
      },
    });

    // indicadores del catálogo del puesto (producción) al pie, con su «¿Qué es?» y la fase 2
    const inds = ['produccion.entregas_en_fecha', 'produccion.rondas_de_revision_por_pieza', 'produccion.indice_de_rendimiento_de_sus_anuncios'].map(i => ctx.indicador(i)).filter(Boolean);
    if (inds.length && (propia?.puesto === 'produccion' || (propia?.puestos || []).includes('produccion') || dir)) {
      const yoP = propia || {};
      ctxN.push(panel({ titulo: 'Indicadores del puesto', icono: 'medidor', sub: 'Del catálogo firmado: umbral, origen y si se mide hoy. Pulsa «¿Qué es?».' },
        h('div', { class: 'cuerpo' }, h('div', { class: 'rejilla' },
          fichaCatalogo(ctx.indicador('produccion.entregas_en_fecha'), { valor: yoP.pct_en_fecha ?? null, unidad: yoP.con_fecha_30d ? `% de ${yoP.con_fecha_30d}` : '', estado: semaforo(yoP.pct_en_fecha, { verde: 90, ambar: 75 }), frescura: { fuente: 'ClickUp', fecha: F.tareas?.hora }, parcial: yoP.con_fecha_30d ? 'Solo tareas con fecha límite; últimos 30 días.' : 'Sin tareas con fecha en 30 días.' }),
          fichaCatalogo(ctx.indicador('produccion.rondas_de_revision_por_pieza'), { valor: yoP.pct_primera ?? null, unidad: yoP.revisadas_30d ? `% a la primera (${yoP.revisadas_30d})` : '', estado: semaforo(yoP.pct_primera, { verde: 80, ambar: 60 }), medible: 'medias', medibleDetalle: 'ClickUp da el tiempo en cada estado, no cuántas veces se entra', parcial: D.notas?.a_la_primera }),
          fichaCatalogo(ctx.indicador('produccion.indice_de_rendimiento_de_sus_anuncios'), { valor: null, parcial: 'Parcial: no consta quién hizo cada pieza. Propuesta firmada: iniciales del autor en el nombre del anuncio.' }),
        )), pieFase2(ctx.indicadores().filter(i => i.modulo === 'produccion'))));
    }

    const panelPedido = pedidoAbierto ? panel({ titulo: `Pedido de creatividades · ${cliNombre.get(pedidoAbierto.cliente_id)?.nombre || pedidoAbierto.cliente_id}`, icono: 'spark',
      sub: `De ${alias(pedidoAbierto.quien)} · ${fDiaHoraRO(new Date(String(pedidoAbierto.creada || '').replace(' ', 'T') + 'Z').toLocaleString('sv-SE', { timeZone: 'Europe/Madrid' }))} · tarea en ClickUp por la sincronía (hoy simulada)` },
    h('div', { class: 'cuerpo' }, fichaMarca({ cliente: cliNombre.get(pedidoAbierto.cliente_id) || { id: pedidoAbierto.cliente_id, nombre: pedidoAbierto.cliente_id }, marca: MARCA.get(pedidoAbierto.cliente_id), pedidos: [pedidoAbierto], alias }))) : null;
    cont.append(pantallaAncha({ id: ID, lista: panelPedido ? h('div', { class: 'pila', style: { minWidth: '0' } }, panelPedido, tabs) : tabs, contexto: ctxN, tituloContexto: 'Datos, consejos e indicadores del puesto' }));
    for (const el of cont.children) el.style.minWidth = '0'; // main es una rejilla: que nada estire la página en móvil

    // ================================================================ cola
    function pintarCola(z) {
      if (!personas.length) { z.append(vacio({ icono: 'capas', titulo: 'Sin colas que ver', texto: 'No tienes tareas asignadas en ClickUp.' })); return; }
      const cab = h('div', { class: 'fila', style: { gap: `${S[2]} ${S[3]}`, justifyContent: 'space-between' } });
      if (personas.length > 1) {
        z.append(h('div', { style: { paddingTop: S[4] } }, cab));
        cab.append(selectorPersona({ personas, actual: colaDe, etiqueta: 'Cola de', alElegir: pid => { colaDe = pid; pintarDentro(); } }));
      }
      const dentro = h('div', { class: 'pila', style: { marginTop: S[2] } });
      z.append(dentro);
      const pintarDentro = () => {
        dentro.replaceChildren();
        const p = personas.find(x => x.persona_id === colaDe) || personas[0];
        const notaTrans = p.transversal ? h('p', { class: 'sub', style: { maxWidth: '72ch', margin: '0' } }, notaTransversal(p)) : null;
        const filas = (D.cola || []).filter(r => r.persona_id === p.persona_id);
        // V2: «por el cliente» solo si la tarea tiene un cliente de verdad; las internas (ADMIN, organigrama, RO) van aparte
        const bloqueadas = filas.filter(r => r.grupo === 'bloqueada');
        const bloqCliente = bloqueadas.filter(r => r.cli && cliNombre.has(r.cli)).length;
        const quien = p.persona_id === yo ? 'Tu cola' : `Cola de ${p.alias || p.nombre}`;
        // V2: «A la primera» mira lo revisado en 30 días; «devueltas», lo que hoy está en la cola. Se dice cada ventana para que
        // «100 % · 1 devuelta» no parezca una contradicción.
        const calidad = [p.pct_primera === null || p.pct_primera === undefined ? null : `A la primera en 30 días: ${fmt.pct(p.pct_primera)}${p.revisadas_30d ? ` de ${fmt.num(p.revisadas_30d)}` : ''}`, p.devueltas ? `${fmt.plural(p.devueltas, 'devuelta', 'devueltas')} en la cola ahora` : null].filter(Boolean).join(' · ');
        // Ronda U (#1): la lista primero; las tarjetas de cifras van debajo (los chips de «Mostrar» ya filtran con su cuenta)
        const cifrasCola = (tiles([
          tile({ icono: 'alert', etiqueta: 'Vencidas', valor: filas.filter(r => r.grupo === 'vencida').length, estado: filas.some(r => r.grupo === 'vencida') ? 'rojo' : 'verde',
            contexto: 'Fecha pasada y sin entregar', ir: 'Ver las vencidas', alPulsar: () => elegir('vencida') }),
          tile({ icono: 'zap', etiqueta: 'Para hoy', valor: filas.filter(r => r.grupo === 'hoy').length, contexto: `Diario, en curso o con fecha hoy (${diaCortoTxt(D.hoy)}), sin las vencidas · ${fmt.num(filas.filter(r => r.grupo === 'semana').length)} esta semana`, ir: 'Ver las de hoy', alPulsar: () => elegir('hoy') }),
          tile({ icono: 'candado', etiqueta: 'Bloqueadas', valor: bloqueadas.length, estado: bloqueadas.length ? 'ambar' : 'verde', contexto: `${fmt.num(bloqCliente)} ${bloqCliente === 1 ? 'espera' : 'esperan'} material del cliente · ${fmt.plural(bloqueadas.length - bloqCliente, 'interna', 'internas')} · ${fmt.num(p.en_revision)} en revisión`, ir: 'Ver las bloqueadas', alPulsar: () => elegir('bloqueada') }),
          tile({ icono: 'check', etiqueta: 'Hitos en fecha (30 días)', valor: p.pct_en_fecha === null ? null : fmt.pct(p.pct_en_fecha), unidad: p.con_fecha_30d ? `de ${p.con_fecha_30d}` : '',
            estado: semaforo(p.pct_en_fecha, { verde: 90, ambar: 75 }), contexto: calidad || 'Últimos 30 días, ventana fija', medible: p.con_fecha_30d ? 'hoy' : 'medias', medibleDetalle: D.notas?.entregas }),
        ]));
        // R12 · una sola cifra de «tu cola»: la de Mi día (GRUPOS_AHORA). Lo que espera a otros va aparte y se ve con «Todo».
        const ahora = filas.filter(r => GRUPOS_AHORA.includes(r.grupo));
        const aparte = filas.length - ahora.length;
        const notaCola = (h('p', { class: 'sub', style: { maxWidth: '72ch', margin: '0' } },
          `${p.persona_id === yo ? 'Tu cola ahora' : `Cola de ${p.alias || p.nombre} ahora`}: ${fmt.num(ahora.length)} ${ahora.length === 1 ? 'tarea' : 'tareas'} (vencidas, para hoy, esta semana y bloqueadas), la misma cifra que en Mi día.`
          + (aparte ? ` Aparte, ${fmt.num(aparte)} que no dependen de ti ahora: esperando revisión, más adelante u olvidadas.` : '')));
        let filtro;
        const conteo = g => filas.filter(r => r.grupo === g).length;
        const chips = chipsFiltro({
          etiqueta: 'Mostrar', clave: `${ID}.grupo`,
          opciones: [{ valor: '', texto: 'Ahora', cuenta: ahora.length }, ...GRUPOS.map(g => ({ ...g, cuenta: conteo(g.valor), cuentaEstado: ['bloqueada', 'vencida'].includes(g.valor) ? 'rojo' : undefined })), { valor: 'todo', texto: 'Todo', cuenta: filas.length }],
          alCambiar: v => { filtro = v; lista(); },
        });
        filtro = chips.valor();
        function elegir(v) {
          const t = v ? GRUPOS.find(g => g.valor === v).texto : 'Ahora';
          [...chips.querySelectorAll('button')].find(x => x.textContent.startsWith(t))?.click();
          chips.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
        // al cambiar de grupo, se vuelve a la primera página
        chips.addEventListener('click', () => { paginas = 1; }, true);
        const caja = h('div');
        let paginas = 1;
        const POR_PAGINA = esMovil() ? 15 : 20; // guía 3.8: pocas filas a la vista y «Ver más»
        const lista = () => {
          const base = filas.filter(r => (!filtro ? GRUPOS_AHORA.includes(r.grupo) : filtro === 'todo' || r.grupo === filtro));
          let quedan = POR_PAGINA * paginas;
          if (!base.length) {
            caja.replaceChildren(h('div', { class: 'cuerpo' }, vacioLinea(filtro ? 'Nada en este grupo. Prueba con «Todo».' : 'Nada que dependa de ti ahora. Con «Todo» ves lo que espera revisión y lo de más adelante.', { icono: 'ok' })));
            return;
          }
          const corte = cuentagotas(base.map(r => vence(r.vence).dias || 0), 14); // rojo con cuentagotas: como mucho un tercio de las filas
          const ul = h('ul', { style: { listStyle: 'none', margin: '0', padding: '0', display: 'grid' } });
          for (const g of GRUPOS) {
            const xs = base.filter(r => r.grupo === g.valor);
            if (!xs.length) continue;
            if (quedan <= 0) break;
            ul.append(h('li', { class: 'titulo-seccion', role: 'presentation', style: { padding: `${S[3]} ${S[5]} ${S[2]}`, background: 'var(--card-2)', borderBottom: '1px solid var(--line-soft)' } }, icono(g.icono, { clase: 's' }), g.texto, h('span', {}, `· ${fmt.num(xs.length)}`)));
            for (const r of xs.slice(0, quedan)) ul.append(filaTarea(r, p.persona_id === yo, corte));
            quedan -= xs.length;
          }
          const vistas = Math.min(base.length, POR_PAGINA * paginas);
          caja.replaceChildren(ul, h('div', { class: 'cuerpo fila', style: { justifyContent: 'space-between' } },
            h('span', { class: 'sub' }, `${fmt.num(vistas)} de ${fmt.num(base.length)}`),
            vistas < base.length ? h('button', { type: 'button', class: 'bt', on: { click: () => { paginas += 1; lista(); } } }, icono('mas'), `Ver ${Math.min(POR_PAGINA, base.length - vistas)} más`) : null));
          if (resaltar) {   // R15a: el común de «Ir» (resalta, centra y da el foco cuando la fila ya está en la página)
            const id = resaltar; resaltar = null;
            llevarA(caja, c => c.querySelector(`[data-tarea="${CSS.escape(id)}"]`));
          }
        };
        lista();
        dentro.append(panel({ titulo: quien, icono: 'capas' },
          h('div', { class: 'cuerpo', style: { paddingBottom: S[2], minWidth: '0' } }, franjaEnLinea(chips)), caja));
        dentro.append(h('details', { class: 'que-es' }, h('summary', {}, 'Cifras de la cola'), h('div', { class: 'pila', style: { marginTop: S[3] } }, notaTrans, cifrasCola, notaCola)));
      };
      pintarDentro();
    }

    // ================================================================ por revisar (R14 · idea B2, en simulación)
    // Las piezas que esperan revisión, juntas: las de las colas (grupo «Esperando revisión») y las del flujo por cliente.
    // Quién revisa sale de reglas_permisos.json → revision_piezas (las mismas reglas que comprueba servir.py al recibir
    // la acción). Aprobar y Pedir cambios dejan la acción en la cola «acciones» en SIMULACIÓN, con su rastro; escribir en
    // ClickUp lo activa Tomás.
    function piezasPorRevisar() {
      const RP = REGLAS.revision_piezas || {};
      const esperaCliente = new Set(RP.espera_cliente || []);
      const porEstado = RP.por_estado || {};
      const siempre = puestos.some(p => (RP.siempre || []).includes(p));
      const cartAcc = ctx.carteraPorSilla?.account;
      const llevoCuenta = id => !!id && !!cartAcc && (typeof cartAcc.has === 'function' ? cartAcc.has(id) : (cartAcc.includes?.(id) || false));
      const areas = RP.areas_tecnica || {};
      const personaDe = id => (ctx.datos?.personas || []).find(p => p.id === id) || null;
      const porNombre = new Map();
      for (const p of ctx.datos?.personas || []) for (const f of [p.alias, p.nombre, (p.nombre || '').split(' ')[0]]) if (f) porNombre.set(f.trim().toLowerCase(), p.id);
      const m = new Map();
      for (const r of D.cola || []) {
        if (r.grupo !== 'revision') continue;
        const x = m.get(r.id) || { id: r.id, tarea: r.tarea, cli: r.cli || null, cliente: r.cliente, estado: r.estado, dias: r.dias_estado, url: r.url, autores: new Set() };
        x.autores.add(r.persona_id);
        m.set(r.id, x);
      }
      for (const r of revisiones) {
        if (r.estado === 'bloqueado') continue;
        const x = m.get(r.id) || { id: r.id, tarea: r.tarea, cli: r.cliente_id, cliente: r.cliente_id, estado: r.estado, dias: r.dias, url: r.url, autores: new Set() };
        for (const n of r.asignados || []) { const pid = porNombre.get(String(n).trim().toLowerCase()); if (pid) x.autores.add(pid); }
        x.cli = x.cli || r.cliente_id;
        m.set(r.id, x);
      }
      return [...m.values()].map(x => {
        const regla = porEstado[x.estado];
        const externo = esperaCliente.has(x.estado) || !regla;
        // account del cliente: el de la verdad única; si este puesto solo ve la línea común, su responsable
        const acc = x.cli ? (accountDe(x.cli) ?? ctx.verdad?.(x.cli)?.responsable_id ?? null) : null;
        let revisor;
        if (externo) revisor = { clave: 'cliente', texto: x.estado === 'enviar  cliente' || x.estado === 'enviar cliente' ? 'Lista para enviar al cliente' : 'Espera al cliente' };
        else if (regla.revisa === 'account') revisor = acc ? { clave: `p:${acc}`, texto: `${alias(acc)} (account)`, persona: acc } : { clave: 'sin-account', texto: 'Account sin asignar' };
        else if (regla.revisa === 'persona') revisor = { clave: `p:${regla.persona}`, texto: alias(regla.persona), persona: regla.persona };
        else {
          // V2: la jefa del área del autor (publicidad, CRM o SEO), no «las tres jefas»
          const jefa = Object.keys(RP.areas_tecnica || {}).find(j => [...x.autores].some(a => (((ctx.datos?.personas || []).find(p => p.id === a) || {}).puestos || []).some(q => (RP.areas_tecnica[j] || []).includes(q))));
          const NOMBRE_JEFA = { jefa_publicidad: 'Jefa de publicidad', jefa_crm: 'Jefa de CRM', jefa_seo: 'Jefe de SEO' };
          revisor = jefa ? { clave: `tecnica:${jefa}`, texto: `Revisión técnica · ${NOMBRE_JEFA[jefa] || jefa}` } : { clave: 'tecnica', texto: 'Revisión técnica · área sin dueña: la recoge operaciones' };
        }
        const mia = x.autores.has(yo);
        // V2 (B-A1 + R16) · revisión técnica POR ÁREA: la jefa solo revisa piezas de su área (revision_piezas.areas_tecnica:
        // el autor tiene un puesto del área o tiene a esa jefa de jefe). El servidor ya da 403 a la jefa de otra área.
        const deMiArea = regla?.revisa !== 'puestos' || [...x.autores].some(a => {
          const pa = personaDe(a); if (!pa) return false;
          return pa.jefe === yo || puestos.some(mp => (areas[mp] || []).some(q => (pa.puestos || []).includes(q)));
        });
        // «me toca»: soy quien la revisa por regla (su account, la jefa del área, Mili o Tomás por nombre; lo que no
        // tiene account lo recoge operaciones). «puedo»: además, quien puede decidir en todas (revision_piezas.siempre).
        const toca = !externo && !mia && ((regla.revisa === 'account' && (acc ? acc === yo || llevoCuenta(x.cli) : puestos.includes('operaciones')))
          || (regla.revisa === 'persona' && regla.persona === yo) || (regla.revisa === 'puestos' && deMiArea && puestos.some(p => (regla.puestos || []).includes(p))));
        let puedo = false;
        if (!externo && !mia) {
          if (siempre) puedo = true;
          else if (regla.revisa === 'account') puedo = llevoCuenta(x.cli);
          else if (regla.revisa === 'puestos') puedo = deMiArea && puestos.some(p => (regla.puestos || []).includes(p));
          else if (regla.revisa === 'persona') puedo = regla.persona === yo;
        }
        const c = x.cli ? cliNombre.get(x.cli) : null;
        return { ...x, externo, revisor, mia, puedo: puedo || toca, toca, vigente: (x.dias || 0) <= 30, a: regla?.a || null, clienteNombre: c ? c.nombre : (x.cliente || 'Interno'), autoresTxt: [...x.autores].map(alias).join(', ') || 'sin autor en ClickUp' };
      });
    }

    function pintarPorRevisar(z) {
      const decididas = new Map();   // objeto → acción ya apuntada (de /api/acciones?modulo=produccion)
      const hayMias = piezas.some(x => x.mia);
      const internas = piezas.filter(x => !x.externo);
      const opciones = [
        { valor: 'toca', texto: 'Me toca revisar', icono: 'check', cuenta: meToca },
        { valor: 'mias', texto: 'Mis piezas', icono: 'persona', cuenta: piezas.filter(x => x.mia && x.vigente).length },
        { valor: 'internas', texto: 'Toda la revisión interna', icono: 'capas', cuenta: internas.filter(x => x.vigente).length },
        { valor: 'cliente', texto: 'Esperando al cliente', icono: 'cli', cuenta: piezas.filter(x => x.externo && x.vigente).length },
      ].filter(o => o.cuenta || o.valor === 'toca' || o.valor === 'internas');
      const porDefecto = meToca ? 'toca' : hayMias ? 'mias' : 'internas';
      let alcance = porDefecto;
      let agrupar = 'cliente';
      const chipsA = chipsFiltro({ etiqueta: 'Mostrar', clave: `${ID}.porrevisar.${yo}`, valor: porDefecto, opciones, alCambiar: v => { alcance = v || porDefecto; pintarLista(); } });
      alcance = chipsA.valor() || porDefecto;
      const chipsG = chipsFiltro({ etiqueta: 'Agrupar por', clave: `${ID}.agrupar`, valor: 'cliente', opciones: [
        { valor: 'cliente', texto: 'Cliente', icono: 'cli' }, { valor: 'revisa', texto: 'Quién revisa', icono: 'persona' }], alCambiar: v => { agrupar = v || 'cliente'; pintarLista(); } });
      agrupar = chipsG.valor() || 'cliente';
      const mas48 = internas.filter(x => x.vigente && (x.dias || 0) > 2).length;
      let conOlvidadas = false;   // más de 30 días esperando: aparte, como «olvidadas» en las demás pestañas
      const cajaLista = h('div');
      z.append(h('div', { class: 'pila', style: { marginTop: S[4] } },
        tiles([
          tile({ icono: 'check', etiqueta: 'Me toca revisar', valor: meToca, estado: meToca ? 'ambar' : 'verde', contexto: meToca ? 'Esperan tu visto bueno (últimos 30 días)' : 'Nada que dependa de tu visto bueno', ir: meToca ? 'Ver' : null, alPulsar: meToca ? () => elegirAlcance('toca') : null }),
          tile({ icono: 'clock', etiqueta: 'Toda la revisión interna > 48 h', valor: mas48, unidad: `de ${fmt.num(internas.filter(x => x.vigente).length)}`, estado: semaforo(mas48, { verde: 5, ambar: 20, mejorSi: 'bajo' }), contexto: `Objetivo: 5 o menos · últimos 30 días; ${fmt.num(internas.filter(x => !x.vigente).length)} olvidadas aparte`, medible: 'hoy' }),
          hayMias ? tile({ icono: 'persona', etiqueta: 'Mis piezas esperando', valor: piezas.filter(x => x.mia && x.vigente).length, contexto: `${fmt.num(piezas.filter(x => x.mia && x.vigente && x.externo).length)} esperan al cliente`, ir: 'Ver mis piezas', alPulsar: () => elegirAlcance('mias') }) : null,
        ].filter(Boolean)),
        avisoParcial('Las revisiones se registran en RO. Comprueba su envío a ClickUp en Envíos; el registro no supone que el entregable esté aceptado. Si no aparece confirmación, revisa el seguimiento antes de volver a guardar.', { tipo: 'info', titulo: 'Revisión con seguimiento.' }),
        panel({ titulo: 'Por revisar', icono: 'check', sub: 'Piezas que esperan un visto bueno, juntas por cliente o por quién las revisa. Las que más llevan esperando, arriba. Pulsa el título para abrirla en ClickUp.' },
          h('div', { class: 'cuerpo pila', style: { paddingBottom: S[1], gap: S[2] } }, chipsA, chipsG), cajaLista)));
      function elegirAlcance(v) { const t = opciones.find(o => o.valor === v)?.texto; [...chipsA.querySelectorAll('button')].find(b => t && b.textContent.startsWith(t))?.click(); }
      const abiertos = new Map();   // grupo → cuántas filas a la vista
      let gruposVista = esMovil() ? 6 : 10;
      function pintarLista() {
        if (!vigente()) return;
        const todas = piezas.filter(x => alcance === 'toca' ? x.toca : alcance === 'mias' ? x.mia : alcance === 'cliente' ? x.externo : !x.externo);
        const base = conOlvidadas ? todas : todas.filter(x => x.vigente);
        const olvidadas = todas.length - todas.filter(x => x.vigente).length;
        const botonOlv = olvidadas ? h('button', { type: 'button', class: 'bt mini', 'aria-pressed': String(conOlvidadas), on: { click: () => { conOlvidadas = !conOlvidadas; pintarLista(); } } },
          icono('hist'), conOlvidadas ? 'Quitar las olvidadas' : `Ver también ${fmt.num(olvidadas)} olvidadas (más de 30 días)`) : null;
        if (!base.length) {
          cajaLista.replaceChildren(h('div', { class: 'cuerpo' }, vacioLinea(alcance === 'toca' ? 'Ahora no hay ninguna pieza esperando tu visto bueno.' : alcance === 'mias' ? 'No tienes piezas esperando revisión.' : 'Nada en este grupo.', { icono: 'ok' }), botonOlv));
          return;
        }
        const grupos = new Map();
        for (const x of base) {
          const k = agrupar === 'cliente' ? (x.cli || 'interno') : x.revisor.clave;
          const g = grupos.get(k) || { clave: k, filas: [], titulo: agrupar === 'cliente' ? x.clienteNombre : x.revisor.texto, cli: agrupar === 'cliente' ? x.cli : null, persona: agrupar === 'revisa' ? x.revisor.persona : null };
          g.filas.push(x);
          grupos.set(k, g);
        }
        const lista = [...grupos.values()].map(g => ({ ...g, filas: g.filas.sort((a, b) => (b.dias || 0) - (a.dias || 0)), viejo: Math.max(...g.filas.map(f => f.dias || 0)) }))
          .sort((a, b) => (a.clave === 'cliente') - (b.clave === 'cliente') || b.filas.length - a.filas.length || b.viejo - a.viejo);
        const corte = cuentagotas(base.map(x => x.dias || 0), 14);
        const ul = h('ul', { style: { listStyle: 'none', margin: '0', padding: '0', display: 'grid' } });
        for (const g of lista.slice(0, gruposVista)) {
          const c = g.cli ? cliNombre.get(g.cli) : null;
          const fuera = g.filas.filter(f => (f.dias || 0) > 2).length;
          ul.append(h('li', { class: 'titulo-seccion', role: 'presentation', style: { padding: `${S[3]} ${S[5]} ${S[2]}`, background: 'var(--card-2)', borderBottom: '1px solid var(--line-soft)', gap: S[2] } },
            agrupar === 'cliente' ? (c ? logoCliente(c) : icono('cli', { clase: 's' })) : g.persona ? h('span', { class: 'av s', 'aria-hidden': 'true' }, iniciales(alias(g.persona))) : icono(g.clave === 'cliente' ? 'cli' : 'aj', { clase: 's' }),
            g.titulo, h('span', { style: { textTransform: 'none', letterSpacing: '0' } }, `· ${fmt.num(g.filas.length)}${fuera ? ` · ${fmt.num(fuera)} con más de 48 h` : ''}`)));   // X8: la cifra y la «h» en minúscula
          const n = abiertos.get(g.clave) || (esMovil() ? 3 : 5);
          for (const x of g.filas.slice(0, n)) ul.append(filaPieza(x, corte));
          if (g.filas.length > n) ul.append(h('li', { style: { padding: `${S[2]} ${S[5]}`, borderBottom: '1px solid var(--line-soft)' } },
            h('button', { type: 'button', class: 'bt mini', on: { click: () => { abiertos.set(g.clave, n + 10); pintarLista(); } } }, icono('mas'), `Ver ${fmt.num(Math.min(10, g.filas.length - n))} más de ${g.titulo}`)));
        }
        cajaLista.replaceChildren(ul, h('div', { class: 'cuerpo fila', style: { justifyContent: 'space-between' } },
          h('span', { class: 'fila', style: { gap: S[3] } }, h('span', { class: 'sub' }, `${fmt.num(base.length)} ${base.length === 1 ? 'pieza' : 'piezas'} en ${fmt.num(lista.length)} ${lista.length === 1 ? 'grupo' : 'grupos'}`), botonOlv),
          lista.length > gruposVista ? h('button', { type: 'button', class: 'bt', on: { click: () => { gruposVista += 10; pintarLista(); } } }, icono('mas'), `Ver ${fmt.num(Math.min(10, lista.length - gruposVista))} grupos más`) : null));
      }
      function filaPieza(x, corte) {
        const una = { overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', minWidth: '0' };
        const otra = agrupar === 'cliente' ? `Revisa: ${x.revisor.texto}` : x.clienteNombre;
        const estDias = (x.dias || 0) > corte ? 'rojo' : (x.dias || 0) > 2 ? 'ambar' : 'verde';
        const meta = h('div', { class: 'fila sub', style: { gap: `${S[1]} ${S[3]}` } },
          estadoTexto(x.externo ? 'gris' : estDias, x.dias === null || x.dias === undefined ? estadoTxt(x.estado) : `${estadoTxt(x.estado)} · ${x.dias < 1 ? `${Math.round(x.dias * 24)} h` : `${fmt.num(x.dias, x.dias < 10 ? 1 : 0)} días`}`),
          h('span', {}, `De ${x.autoresTxt}`), h('span', {}, otra));
        const acciones = h('div', { class: 'fila', style: { gap: S[2], flex: 'none' } });
        const pintarAcciones = () => {
          if (!vigente()) return;
          const ya = decididas.get(String(x.id));
          const permisoActual = controlRevision.permiso(x, 'pieza_aprobar').ok || controlRevision.permiso(x, 'pieza_pedir_cambios').ok;
          if (ya && !permisoActual && !controlRevision.estado(x)) { acciones.replaceChildren(estadoTexto('azul', `${ya.tipo === 'pieza_aprobar' ? 'Aprobación propuesta' : 'Cambios propuestos'} por ${alias(ya.quien)} · ${ya.seguimiento.texto}`, ya.seguimiento.texto)); return; }
          if (!x.puedo && !permisoActual && !controlRevision.estado(x)) { acciones.replaceChildren(h('span', { class: 'sub' }, x.externo ? 'No se aprueba desde aquí' : x.mia ? `Es tuya: la revisa ${x.revisor.texto}` : `La revisa ${x.revisor.texto}`)); return; }
          const aprobar = accionRevision(x, 'pieza_aprobar');
          const permisoCambios = controlRevision.permiso(x, 'pieza_pedir_cambios');
          const motivoCambios = permisoCambios.ok ? null : controlRevision.permiso(x, 'pieza_aprobar').ok
            ? 'No hay un destino de devolución confirmado en esta lista. Solicita los cambios desde ClickUp y actualiza la copia.'
            : permisoCambios.motivo;
          const pedir = h('button', { type: 'button', class: 'bt mini', disabled: !permisoCambios.ok,
            title: motivoCambios, 'aria-description': motivoCambios,
            on: { click: () => { if (vigente() && !ctx.soloLectura && !ctx.pilotoLectura) formularioCambios(); } } }, 'Pedir cambios');
          acciones.replaceChildren(aprobar, pedir);
        };
        const formularioCambios = () => {
          let texto = '';
          const error = h('p', { class: 'sub', role: 'alert', style: { margin: '0', color: 'var(--bad-ink)' } });
          const guardar = h('div');
          const prepararPeticion = () => {
            if (!vigente()) return;
            guardar.replaceChildren(texto.trim().length >= 3 && texto.length <= 2000
              ? accionRevision(x, 'pieza_pedir_cambios', texto)
              : h('span', { class: 'sub' }, 'Explica los cambios en 3 a 2.000 caracteres.'));
          };
          acciones.replaceChildren(h('div', { class: 'pila', style: { gap: S[2], minWidth: 'min(100%, 320px)' } },
            campoTexto({ etiqueta: 'Qué hay que cambiar', filas: 2, requerido: true, placeholder: 'Describe la corrección para el autor', alCambiar: v => { texto = v; error.textContent = ''; prepararPeticion(); } }),
            error, guardar, h('button', { type: 'button', class: 'bt mini', on: { click: pintarAcciones } }, 'Volver')));
          prepararPeticion();
          acciones.querySelector('textarea')?.focus();
        };
        pintarAcciones();
        return h('li', { 'data-pieza': x.id, style: { display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: `${S[2]} ${S[3]}`, padding: `${S[3]} ${S[5]}`, borderBottom: '1px solid var(--line-soft)' } },
          h('div', { style: { flex: '1 1 260px', minWidth: '0', display: 'grid', gap: S[1] } },
            h('a', { href: urlTarea(x), target: '_blank', rel: 'noopener', title: `${x.tarea} · abrir en ClickUp`, style: { color: 'var(--ink)', fontWeight: '600', textDecoration: 'none', ...(esMovil() ? una : { overflowWrap: 'anywhere' }), display: 'block', minHeight: '32px', lineHeight: esMovil() ? '32px' : null } }, x.tarea),
            meta),
          acciones);
      }
      pintarLista();
      // las ya apuntadas (de cualquiera que vea Producción): sin botones, con quién y que es simulación
      if (ctx.api) ctx.api(`acciones?modulo=${ID}`).then(r => {
        if (!vigente()) return;
        const resueltas = decisionesVisibles(r?.acciones, piezas, ['pieza_aprobar', 'pieza_pedir_cambios']);
        for (const [id, a] of resueltas) if (!decididas.has(id)) decididas.set(id, a);
        if (decididas.size) pintarLista();
      }).catch(() => { /* sin servidor: solo las de esta sesión */ });
    }

    function filaTarea(r, mia, corte = 14) {
      const v = vence(r.vence);
      const estV = v.estado === 'rojo' && !(v.dias > corte) ? 'ambar' : v.estado;
      const c = r.cli ? cliNombre.get(r.cli) : null;
      const puedeRev = controlRevision.permiso(r, 'mover_estado').ok || controlRevision.estado(r)?.intento.payload.tipo === 'mover_estado';
      const accionRev = () => accionRevision(r, 'mover_estado');
      // Ronda U (#13): «Brief y marca» en la propia tarea (logo, colores, tono, lo vetado, carpeta y última pieza aprobada)
      const hueMarca = h('div', { hidden: true, style: { flexBasis: '100%', minWidth: '0' } });
      const botonMarca = r.cli ? h('button', { type: 'button', class: 'bt mini', 'aria-expanded': 'false', 'data-marca': r.cli, on: { click: () => {
        const abrir = hueMarca.hidden; hueMarca.hidden = !abrir; botonMarca.setAttribute('aria-expanded', String(abrir));
        if (abrir && !hueMarca.childNodes.length) hueMarca.append(fichaMarca({ cliente: c || { id: r.cli, nombre: r.cliente }, marca: MARCA.get(r.cli), pedidos: PEDIDOS.get(r.cli) || [], tarea: r, alias }));
      } } }, icono('spark'), 'Brief y marca') : null;
      const accionAvisar = () => botonConfirmar({ texto: 'Avisar', pregunta: '¿Dejar un comentario al account pidiendo el material?', confirmar: 'Sí, avisar', mini: true, soloLectura: ctx.soloLectura,
        alConfirmar: async () => { await registrarAccionVigente(ctx, vigente, { herramienta: 'clickup', tipo: 'comentario', objeto: r.id, texto: `Bloqueada por falta de material del cliente (${r.cliente}). ¿Lo pides tú?`, vista_previa: { tarea: urlTarea(r) } }); return 'Comentario en la cola simulada'; } });
      if (esMovil()) {
        // móvil: fila compacta de 2 líneas · título (enlace a ClickUp) + acción, y una línea meta: punto y plazo · cliente · estado
        const una = { overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', minWidth: '0' };
        const accion = puedeRev ? accionRev() : r.grupo === 'bloqueada' && mia ? accionAvisar() : null;
        return h('li', { 'data-tarea': r.id, style: { display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) auto', alignItems: 'center', gap: `${S[1]} ${S[2]}`, padding: `${S[2]} ${S[4]}`, borderBottom: '1px solid var(--line-soft)' } },
          h('a', { href: urlTarea(r), target: '_blank', rel: 'noopener', title: `${r.tarea} · abrir en ClickUp`, style: { ...una, color: 'var(--ink)', fontWeight: '600', textDecoration: 'none', display: 'block', minHeight: '32px', lineHeight: '32px' } }, r.tarea),
          accion || h('span'),
          h('div', { class: 'sub', style: { ...una, gridColumn: '1 / -1', display: 'flex', alignItems: 'center', gap: S[2] } },
            estadoTexto(estV || (r.grupo === 'bloqueada' ? 'ambar' : 'gris'), v.texto),
            h('span', { style: una }, `· ${c ? c.nombre : (r.cliente || 'Interno')} · ${estadoTxt(r.estado)}${r.estado_determinado === false ? ' · estado por contrastar en ClickUp' : ''}${r.devuelta ? ' · revisión previa registrada' : ''}`)),
          botonMarca ? h('div', { style: { gridColumn: '1 / -1' } }, botonMarca) : null,
          h('div', { style: { gridColumn: '1 / -1', minWidth: '0' } }, hueMarca));
      }
      // fila: título en tinta 600 (no pared azul), metadatos en .sub, estado con punto
      return h('li', { 'data-tarea': r.id, style: { display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: `${S[2]} ${S[3]}`, padding: `${S[3]} ${S[5]}`, borderBottom: '1px solid var(--line-soft)' } },
        prioridad(r),
        h('div', { style: { flex: '1 1 260px', minWidth: '0', display: 'grid', gap: S[1] } },
          h('a', { href: urlTarea(r), target: '_blank', rel: 'noopener', title: `${r.tarea} · abrir en ClickUp`, style: { color: 'var(--ink)', fontWeight: '600', textDecoration: 'none', overflowWrap: 'anywhere', display: 'block', minHeight: '32px', padding: '6px 0' } }, r.tarea),
          h('div', { class: 'fila sub', style: { gap: `${S[1]} ${S[3]}` } },
            h('span', { class: 'fila', style: { gap: S[2], flexWrap: 'nowrap', fontWeight: '600', color: 'var(--mid)' } }, c ? logoCliente(c) : icono('cli', { clase: 's' }), c ? c.nombre : (r.cliente || 'Interno')),
            estadoTexto(r.grupo === 'bloqueada' ? 'ambar' : r.grupo === 'revision' ? 'azul' : 'gris', `${estadoTxt(r.estado)}${r.estado_determinado === false ? ' · por contrastar' : ''}`),
            estadoTexto(estV || 'gris', v.texto),
            r.dias_estado !== null && r.dias_estado !== undefined ? h('span', {}, `${fmt.num(r.dias_estado, r.dias_estado < 10 ? 1 : 0)} días en este estado`) : null,
            r.devuelta ? chipEstado('ambar', 'Devuelta') : null,
            r.comparte ? h('span', { title: 'Tarea con más de una persona asignada' }, icono('users', { clase: 's' })) : null)),
        h('div', { class: 'fila', style: { gap: S[2], flex: 'none' } },
          botonMarca,
          puedeRev ? accionRev() : null,
          r.grupo === 'bloqueada' && mia ? accionAvisar() : null,
          h('a', { class: 'bt mini', href: urlTarea(r), target: '_blank', rel: 'noopener' }, icono('ext'), 'ClickUp')),
        hueMarca);
    }

    // ================================================================ revisiones
    function pintarRevisiones(z) {
      const esAccount = puestos.includes('account');
      const rpm = revisiones.filter(r => r.estado === 'revisión project manager');
      const rtec = revisiones.filter(r => r.estado === 'revisión técnica');
      const bloq = revisiones.filter(r => r.estado === 'bloqueado');
      const mias = revisiones.filter(r => (accountDe(r.cliente_id) ?? r.account_id) === yo);
      const medAccount = medicionFilasRevision137(Array.isArray(D.revisiones) ? rpm : undefined, F, D.hoy), medTecnica = medicionFilasRevision137(Array.isArray(D.revisiones) ? rtec : undefined, F, D.hoy), medMias = medicionFilasRevision137(Array.isArray(D.revisiones) ? revMias.todas : undefined, F, D.hoy);
      const callados = [...new Set(bloq.map(r => r.cliente_id))].filter(id => ctx.verdad?.(id)?.bloqueo_callado).length;
      let filtro = '';
      let solo = false;
      const tl = tiles([
        tile({ icono: 'persona', etiqueta: 'Account > 48 h', valor: medAccount.valor ?? 'Sin dato', unidad: medAccount.medido ? `${rpm.length} filas en copia` : 'Copia sin medición', estado: medAccount.estado,
          contexto: medAccount.detalle, medible: 'hoy', ir: 'Ver las revisiones', alPulsar: () => fijar('revisión project manager') }),
        tile({ icono: 'aj', etiqueta: 'Técnica > 48 h', valor: medTecnica.valor ?? 'Sin dato', unidad: medTecnica.medido ? `${rtec.length} filas en copia` : 'Copia sin medición', estado: medTecnica.estado,
          contexto: medTecnica.detalle, medible: 'hoy', ir: 'Ver las revisiones', alPulsar: () => fijar('revisión técnica') }),
        tile({ icono: 'candado', etiqueta: 'Bloqueadas (cliente)', valor: bloq.length, unidad: callados ? `${fmt.num(callados)} con bloqueo callado` : '',
          estado: !bloq.length ? 'verde' : callados ? 'rojo' : 'ambar',
          contexto: 'Callado si la más antigua pasa de 5 días', medible: 'hoy', ir: 'Ver las bloqueadas', alPulsar: () => fijar('bloqueado') }),
        esAccount ? tile({ icono: 'cli', etiqueta: 'Tus revisiones > 48 h', valor: medMias.valor ?? 'Sin dato', unidad: medMias.medido ? `${revMias.todas.length} filas en copia` : 'Copia sin medición', estado: medMias.estado,
          contexto: medMias.detalle, ir: 'Ver las revisiones', alPulsar: () => { solo = true; boton.setAttribute('aria-pressed', 'true'); fijar('revisión project manager'); } }) : null,
      ].filter(Boolean));
      const boton = h('button', { type: 'button', class: 'bt', 'aria-pressed': 'false', hidden: !esAccount }, icono('persona'), 'Solo mis clientes');
      boton.addEventListener('click', () => { solo = boton.getAttribute('aria-pressed') !== 'true'; boton.setAttribute('aria-pressed', String(solo)); tabla(); });
      const chips = chipsFiltro({ etiqueta: 'Espera a', opciones: [
        { valor: '', texto: 'Todo', cuenta: medicionFilasRevision137(D.revisiones, F, D.hoy).medido ? revisiones.length : null },
        { valor: 'revisión project manager', texto: 'Al account', icono: 'persona', cuenta: medAccount.medido ? rpm.length : null },
        { valor: 'revisión técnica', texto: 'Técnica', icono: 'aj', cuenta: medTecnica.medido ? rtec.length : null },
        { valor: 'bloqueado', texto: 'Al cliente (bloqueada)', icono: 'candado', cuenta: bloq.length, cuentaEstado: 'rojo' },
      ], alCambiar: v => { filtro = v; tabla(); } });
      function fijar(v) { const t = { 'revisión project manager': 'Al account', 'revisión técnica': 'Técnica', bloqueado: 'Al cliente' }[v]; [...chips.querySelectorAll('button')].find(b => b.textContent.startsWith(t))?.click(); }
      let edad = '';
      const chipsEdad = chipsFiltro({ etiqueta: 'Antigüedad', clave: `${ID}.edad`, valor: 'reciente', opciones: [
        { valor: '', texto: 'Todas', cuenta: medicionFilasRevision137(D.revisiones, F, D.hoy).medido ? revisiones.length : null },
        { valor: 'reciente', texto: 'Hasta 30 días', icono: 'clock', cuenta: revisiones.filter(r => (r.dias || 0) <= 30).length },
        { valor: 'olvidada', texto: 'Más de 30 días (olvidadas)', icono: 'hist', cuenta: revisiones.filter(r => (r.dias || 0) > 30).length, cuentaEstado: 'rojo' },
      ], alCambiar: v => { edad = v; tabla(); } });
      edad = chipsEdad.valor();
      const caja = h('div');
      function tabla() {
        const base = revisiones.filter(r => (!filtro || r.estado === filtro) && (!solo || (accountDe(r.cliente_id) ?? r.account_id) === yo)
          && (!edad || (edad === 'reciente' ? (r.dias || 0) <= 30 : (r.dias || 0) > 30)));
        const corte = cuentagotas(base.map(r => r.dias), 14);
        caja.replaceChildren(ancharBuscador(tablaDensa({ porPagina: esMovil() ? 8 : 15,
          filas: base.map(r => ({ ...r, cliente: cliNombre.get(r.cliente_id)?.nombre || r.cliente_id, quien: (r.asignados || []).join(', '), espera: estadoTxt(r.estado), account: (accountDe(r.cliente_id) ?? r.account_id) ? alias(accountDe(r.cliente_id) ?? r.account_id) : 'sin account' })),
          orden: { clave: 'dias', dir: 'desc' },
          buscar: { campos: ['cliente', 'tarea', 'quien', 'account'], placeholder: 'Buscar cliente o tarea' },
          filtros: [{ clave: 'account', titulo: 'Account' }],
          columnas: [
            { clave: 'cliente', titulo: 'Cliente', principal: true, celda: r => h('span', { class: 'celda-cli' }, logoCliente(cliNombre.get(r.cliente_id) || { nombre: r.cliente }), r.cliente) },
            { clave: 'tarea', titulo: 'Tarea', celda: r => h('span', { style: { color: 'var(--ink)', fontWeight: '600', overflowWrap: 'anywhere' } }, r.tarea) },
            { clave: 'espera', titulo: 'Espera a' },
            { clave: 'quien', titulo: 'La hizo' },
            { clave: 'account', titulo: 'Account' },
            { clave: 'dias', titulo: 'Tiempo', num: true, celda: r => fechaRevision137(F.tareas?.hora, D.hoy) && typeof r.dias === 'number' && Number.isFinite(r.dias) && r.dias >= 0 ? chipDias(r.dias, { ambar: corte }) : estadoTexto('gris', 'Sin dato') },
          ],
          alPulsar: r => window.open(urlTarea(r), '_blank', 'noopener'), etiquetaFila: r => `${r.tarea}: abrir en ClickUp`,
          vacio: { titulo: 'Sin filas de revisión en este filtro', porque: 'La copia y sus filtros no acreditan que no haya otras revisiones; contrasta ClickUp.', celebrar: false },
        })));
      }
      tabla();
      z.append(h('div', { class: 'pila', style: { marginTop: S[4] } }, tl,
        panel({ titulo: 'Esperando revisión o al cliente', icono: 'clock', sub: 'Tiempo desde que entró en el estado (ClickUp). 48 h es el plazo del account y de la revisión técnica. Rojo solo para el tercio que más lleva esperando (y siempre más de 14 días). Pulsa una fila para abrirla en ClickUp.', acciones: boton },
          h('div', { class: 'cuerpo pila', style: { paddingBottom: S[1], gap: S[2] } }, chips, chipsEdad), caja)));
    }

    // ================================================================ proyectos
    function pintarProyectos(z) {
      if (!vigente()) return;
      if (!proyectos.length) { z.append(vacio({ icono:'cli',titulo:'Sin proyectos que ver',texto:'No hay proyectos disponibles en esta proyección autorizada.' }));return; }
      let accountSel='',buscar='';
      const hoyOwners=new Intl.DateTimeFormat('sv-SE',{timeZone:'Europe/Madrid',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
      const matrizAccounts=()=>resumirAccountsProduccion237({proyectos,
        clientes:(ctx.clientesVisibles||[]).filter(c=>ctx.ver({tipo:'cliente_detalle',cliente_id:c.id}).ok),
        personas:ctx.datos?.personas||[],asignaciones:ctx.datos?.asignaciones||[],hoy:hoyOwners});
      const nombreAccount=id=>id?alias(id):'Account por confirmar';
      const root=h('div',{class:'prod-baseline pila',style:{marginTop:S[4]}}),zonaAccounts=h('div'),zonaPlanningObservado=h('div',{'data-inventario-produccion-405':''}),zonaProyectos=h('div',{tabindex:'-1','aria-label':'Proyectos filtrados por account'}),zonaPlan=h('div');
      const fuenteVisible=()=>fuenteProduccionBaseline(matrizAccounts().proyectos,D);
      const seleccionar=id=>{
        if(!vigente())return;
        const g=matrizAccounts().grupos.find(g=>(g.account_id||'__sin')===id);if(!g)return;
        accountSel=id;pintar();zonaProyectos.focus?.({preventScroll:true});zonaProyectos.scrollIntoView?.({block:'start',behavior:'auto'});
      };
      const metrica=(p,key)=>metricasProyectoBaseline(p,D)[key];
      const claves=['bloqueadas','cliente','sin_mes','creadas_semana','no_plan','cerradas_semana'];
      const cuenta=(g,key)=>sumarMetricaBaseline(g.proyectosFilas.map(p=>metrica(p,key)),g.proyectos);
      function pintar(){
        if(!vigente())return;
        const alcance=matrizAccounts(),owners=new Map(alcance.grupos.flatMap(g=>g.clientes_ids.map(id=>[id,g.account_id])));
        const grupos=alcance.grupos.map(g=>({...g,proyectosFilas:alcance.proyectos.filter(p=>g.clientes_ids.includes(p.cliente_id))})).sort((a,b)=>Number(!a.account_id)-Number(!b.account_id)||nombreAccount(a.account_id).localeCompare(nombreAccount(b.account_id),'es'));
        if(accountSel&&!grupos.some(g=>(g.account_id||'__sin')===accountSel))accountSel='';
        const revision=(g,tipo,edad=false)=>sumarMetricaBaseline(g.proyectosFilas.map(p=>metrica(p,tipo)),g.proyectos,edad?'mas48':'valor');
        zonaAccounts.replaceChildren(tablaProduccionBaseline({h,ambito:'account',titulo:'Por account',sub:fuenteVisible(),filas:grupos,vigente,alFila:g=>seleccionar(g.account_id||'__sin'),columnas:[
          {titulo:'Account',valor:g=>nombreAccount(g.account_id)}, {titulo:'Proyectos',num:true,valor:g=>g.proyectos},
          {titulo:'Rev. account',num:true,valor:g=>revision(g,'account')},{titulo:'+48 h',clave:'account_48',num:true,valor:g=>revision(g,'account',true)},
          {titulo:'Rev. técnica',num:true,valor:g=>revision(g,'tecnica')},{titulo:'+48 h',clave:'tecnica_48',num:true,valor:g=>revision(g,'tecnica',true)},
          ...claves.map((key,i)=>({titulo:['Bloqueadas','En el cliente','Sin tareas este mes','Creadas semana','No planificadas','Cerradas semana'][i],clave:key,num:true,valor:g=>cuenta(g,key)}))]}));
        const select=h('select',{'aria-label':'Filtrar proyectos por account',on:{change:e=>{if(!vigente())return;accountSel=e.target.value;pintar();}}},
          h('option',{value:'',selected:!accountSel},'Todos'),grupos.map(g=>h('option',{value:g.account_id||'__sin',selected:accountSel===(g.account_id||'__sin')},nombreAccount(g.account_id))));
        const reset=h('button',{type:'button',class:'bt mini',disabled:!accountSel&&!buscar,on:{click:()=>{if(!vigente())return;accountSel='';buscar='';pintar();zonaProyectos.focus?.({preventScroll:true});}}},'Restablecer account');
        const input=h('input',{type:'search',value:buscar,placeholder:'Buscar proyecto','aria-label':'Buscar proyecto autorizado',on:{input:e=>{if(!vigente())return;buscar=e.target.value;pintarProyectosFiltrados();}}});
        const filtros=h('div',{class:'pb-filtros'},h('span',{},'Account'),select,input,reset);
        const caja=h('div');
        function pintarProyectosFiltrados(){
          if(!vigente())return;
          const actual=matrizAccounts(),permitidos=new Set(actual.proyectos.map(p=>p.cliente_id));
          const ids=new Set(actual.grupos.filter(g=>!accountSel||(g.account_id||'__sin')===accountSel).flatMap(g=>g.clientes_ids));
          const base=alcance.proyectos.filter(p=>permitidos.has(p.cliente_id)&&ids.has(p.cliente_id)).map(p=>({...p,cliente:cliNombre.get(p.cliente_id)?.nombre||p.cliente,account:nombreAccount(owners.get(p.cliente_id))})).filter(p=>!buscar||String(p.cliente).toLocaleLowerCase('es').includes(buscar.toLocaleLowerCase('es')));
          reset.disabled=!accountSel&&!buscar;
          caja.replaceChildren(tablaProduccionBaseline({h,ambito:'proyecto',titulo:'Por proyecto',sub:accountSel?`Proyectos de ${nombreAccount(grupos.find(g=>(g.account_id||'__sin')===accountSel)?.account_id)}`:'Todos los accounts autorizados',filas:base,vigente,
            alFila:p=>{if(vigente()&&ctx.ver({tipo:'cliente_detalle',cliente_id:p.cliente_id}).ok)ctx.navegar(`ficha/${p.cliente_id}`);},columnas:[
              {titulo:'Proyecto',valor:p=>p.cliente},...['account','tecnica','bloqueadas','cliente','creadas_mes','creadas_semana','no_plan','cerradas_semana'].map((key,i)=>({titulo:['Rev. account','Rev. técnica','Bloqueadas','En el cliente','Creadas mes','Creadas semana','No planificadas','Cerradas semana'][i],clave:key,num:true,valor:p=>metrica(p,key)}))]}));
        }
        pintarProyectosFiltrados();zonaProyectos.replaceChildren(filtros,caja);
        const plan=planificacionBaseline(D,ctx.datos?.personas||[]);
        zonaPlan.replaceChildren(tablaProduccionBaseline({h,titulo:'Disciplina de planificación',sub:`Mensual → semanal → diario · semana del ${plan.lunes||'Sin dato'}`,filas:plan.filas,vigente,columnas:[
          {titulo:'Quién crea',valor:x=>alias(x.persona_id)},
          {titulo:'Creadas',num:true,valor:x=>({valor:x.creadas,referencia:true,detalle:plan.detalle})},
          {titulo:'Al planning',num:true,valor:()=>({valor:null,detalle:'Campo no incluido en el DTO autorizado.'})},
          {titulo:'Fuegos directos',num:true,valor:()=>({valor:null,detalle:'Campo no incluido en el DTO autorizado.'})},
          {titulo:'Rompen el semanal',num:true,valor:x=>({valor:x.semana,referencia:true,detalle:'Clasificación heredada de la copia; no juicio disciplinario.'})},
          {titulo:'Semana pasada',num:true,valor:x=>({valor:Number.isSafeInteger(x.semana_ant)&&x.semana_ant>=0?x.semana_ant:null,referencia:true,detalle:'Referencia de la copia anterior.'})},
          {titulo:'Ejemplos',valor:x=>(x.ejemplos||[]).map(e=>e.tarea).filter(Boolean).slice(0,2).join(' · ')||'Sin dato'},
        ]}),h('details',{class:'pb-nota'},h('summary',{},'Fuentes y disponibilidad de los indicadores'),
          h('p',{},`${plan.detalle}${plan.faltan_identidades?` ${plan.faltan_identidades} filas de planificación sin identidad canónica; no se atribuyen por nombre.`:''}`),
          h('p',{},'Revisiones: descriptor de fuente y cobertura parcial. Bloqueadas: filas visibles con ID único. Un cero heredado sin descriptor se presenta — (sin dato). Referencia copia conserva valores positivos antiguos, sin certificar periodo, inventario o entrega aceptada.'),
          h('p',{},'La tabla principal no trae revisión del cliente/pendientes de envío, al planning ni fuegos. La comparación adicional muestra creaciones y finales cuando hay una fuente acreditada. No se promete que aparezcan en la próxima recarga.')));
      }
      pintar();root.append(h('style',{},CSS_PRODUCCION_BASELINE),zonaAccounts,h('details',{class:'pb-nota',on:{toggle:()=>{if(!vigente())root.replaceChildren();}}},h('summary',{},'Leyenda de colores y datos'),h('p',{},'— sin dato. Colores de referencia del panel original: ámbar / rojo por account: revisión account +48 h 1 / 6; técnica +48 h 3 / 10; bloqueadas 1 / 5; sin tareas del mes 1 / 2; no planificadas 3 / 8. Por proyecto, edad observada +48 h en revisión/bloqueo se destaca en rojo. La copia es parcial; el gris no certifica cumplimiento.')),zonaProyectos,zonaPlanningObservado,zonaPlan,panelComparacionSemanal296(ctx,D));z.append(root);
      if(ctx.servidor===true)Promise.resolve().then(()=>{if(vigente()&&zonaPlanningObservado.isConnected){const scoped=Object.create(ctx);Object.defineProperty(scoped,'vigente',{value:()=>vigente()&&zonaPlanningObservado.isConnected});return panelPlanningObservado360(zonaPlanningObservado,scoped);}}).catch(()=>{if(vigente()&&zonaPlanningObservado.isConnected)zonaPlanningObservado.replaceChildren(h('p',{class:'sub'},'Inventario observado no disponible. No acredita ausencia de tareas.'));});
    }

    // ================================================================ equipo (solo quien puede comparar · D-83)
    function pintarEquipo(z) {
      const ps = personas;
      if (!ps.length) { z.append(vacio({ icono: 'eq', titulo: 'No tienes a nadie a cargo', texto: 'Esta vista enseña la carga de tu gente.' })); return; }
      const sobre = ps.filter(p => p.tope && p.en_cartera > p.tope);
      const cerca = ps.filter(p => p.tope && p.en_cartera <= p.tope && p.en_cartera >= p.tope - (p.silla_tope === 'account' ? 1 : 2));
      const tl = tiles([
        tile({ icono: 'eq', etiqueta: 'Por encima del tope', valor: sobre.length, estado: semaforo(sobre.length, { verde: 0, ambar: 1, mejorSi: 'bajo' }), contexto: `Tope: ${TOPE_CARTERA.account} por account, ${TOPE_CARTERA.trafficker} en publicidad y CRM`, medible: 'hoy' }),
        tile({ icono: 'alert', etiqueta: 'Con tareas vencidas', valor: ps.filter(p => p.vencidas).length, unidad: `de ${ps.length}`, estado: ps.some(p => p.vencidas > 5) ? 'rojo' : ps.some(p => p.vencidas) ? 'ambar' : 'verde', contexto: 'Vencidas en su mano, sin entregar (la misma cifra que su Mi día)' }),
        tile({ icono: 'volver', etiqueta: 'Piezas devueltas', valor: ps.reduce((s, p) => s + p.devueltas, 0), contexto: 'Volvieron de revisión a trabajo', medible: 'medias', medibleDetalle: D.notas?.devueltas }),
        dir ? tile({ icono: 'persona', etiqueta: 'Tareas sin nadie', valor: D.sin_asignar, estado: D.sin_asignar ? 'ambar' : 'verde', contexto: 'En ClickUp, sin persona asignada' }) : null,
      ].filter(Boolean));
      const filas = ps.map(p => ({ ...p, puestoTxt: (PUESTO_TXT[p.puesto] || p.puesto) + (p.transversal ? ' · transversal' : ''), carteraTxt: p.tope ? `${p.en_cartera} de ${p.tope}` : '—' }));
      // rojo con cuentagotas (guía 3.4): vencidas y «en fecha», rojo solo para el tercio peor
      const corteV = cuentagotas(ps.map(p => p.vencidas || 0), 5);
      const corteF = cuentagotas(ps.map(p => (p.pct_en_fecha === null || p.pct_en_fecha === undefined ? null : 100 - p.pct_en_fecha)), 25);
      const tabla = tablaDensa({ porPagina: esMovil() ? 8 : 15,
        filas, orden: { clave: 'nombre', dir: 'asc' },
        buscar: { campos: ['nombre', 'puestoTxt'], placeholder: 'Buscar persona o puesto' }, filtros: [{ clave: 'puestoTxt', titulo: 'Puesto' }],
        columnas: [
          { clave: 'nombre', titulo: 'Persona', principal: true, celda: p => h('span', { class: 'fila', style: { gap: S[2], flexWrap: 'nowrap' } }, h('span', { class: 'av s', 'aria-hidden': 'true' }, iniciales(p.nombre)), p.nombre) },
          { clave: 'puestoTxt', titulo: 'Puesto', celda: p => p.transversal ? h('span', { class: 'fila', style: { gap: S[2] }, title: notaTransversal(p) }, PUESTO_TXT[p.puesto] || p.puesto, chipEstado('azul', 'varias áreas', { punto: false })) : p.puestoTxt },
          { clave: 'abiertas', titulo: 'Abiertas', num: true },
          { clave: 'hoy', titulo: 'Hoy', num: true, celda: p => p.vencidas ? h('span', { class: 'fila', style: { gap: S[2], flexWrap: 'nowrap', justifyContent: 'flex-end' } }, fmt.num(p.hoy), estadoTexto(p.vencidas > corteV ? 'rojo' : 'ambar', fmt.plural(p.vencidas, 'vencida'))) : fmt.num(p.hoy) },
          { clave: 'bloqueadas', titulo: 'Bloqueadas', num: true, celda: p => p.bloqueadas ? estadoTexto('ambar', fmt.num(p.bloqueadas)) : '0' },
          { clave: 'devueltas', titulo: 'Devueltas', num: true },
          { clave: 'en_cartera', titulo: 'Cartera', num: true, celda: p => p.transversal ? h('span', { class: 'sub', title: notaTransversal(p) }, 'sin cartera propia') : p.tope ? barraMini(p.en_cartera, p.tope, p.en_cartera > p.tope ? 'rojo' : p.en_cartera >= p.tope - (p.silla_tope === 'account' ? 1 : 2) ? 'ambar' : 'verde', p.carteraTxt) : '—' },
          { clave: 'pct_en_fecha', titulo: 'En fecha 30 d', num: true, ordenable: false, celda: p => p.pct_en_fecha === null ? '—' : estadoTexto(((e) => (e === 'rojo' && !(100 - p.pct_en_fecha > corteF) ? 'ambar' : e))(semaforo(p.pct_en_fecha, { verde: 90, ambar: 75 })), fmt.pct(p.pct_en_fecha)) },
          { clave: 'pct_primera', titulo: 'A la primera', num: true, ordenable: false, celda: p => p.pct_primera === null ? '—' : estadoTexto(semaforo(p.pct_primera, { verde: 80, ambar: 60 }), fmt.pct(p.pct_primera)) },
          { clave: 'horas_mes', titulo: 'Horas del mes', num: true, ordenable: false, celda: p => fmt.num(p.horas_mes, 1) },
        ],
        alPulsar: p => irACola(p.persona_id), etiquetaFila: p => `Ver la cola de ${p.nombre}`,
      });
      ancharBuscador(tabla);
      const np = (D.no_planificado || []).filter(x => x.semana >= 3 || x.semana_ant >= 3).sort((a, b) => b.semana - a.semana);
      const transv = ps.filter(p => p.transversal);
      z.append(h('div', { class: 'pila', style: { marginTop: S[4] } }, tl,
        transv.length ? avisoParcial(transv.map(p => `${p.alias || p.nombre}: ${notaTransversal(p)}`).join(' '), { tipo: 'info', titulo: 'Trabaja para varias áreas.' }) : null,
        panel({ titulo: 'Carga de cada persona', icono: 'eq', sub: 'Por orden alfabético: no es un ranking. Pulsa una fila para ver su cola. «En fecha» y «a la primera», últimos 30 días; no se ordenan.' }, tabla),
        cerca.length ? avisoParcial(`${cerca.map(p => p.alias || p.nombre).join(', ')} ${cerca.length === 1 ? 'está' : 'están'} a uno o dos clientes del tope (aviso con 5 huecos o menos en accounts y desde 14 en publicidad y CRM).`, { titulo: 'Cerca del tope.' }) : null,
        panel({ titulo: 'Trabajo no planificado por persona', icono: 'capas', sub: 'Aviso con 3 o más tareas por persona y semana que entran directas al semanal o al diario sin ser fuegos.' },
          np.length ? h('ul', { class: 'lista-i cuerpo' }, np.slice(0, esMovil() ? 6 : np.length).map(x => h('li', {},
            h('span', { class: 'av s', 'aria-hidden': 'true' }, iniciales(alias(x.persona_id))),
            h('span', { class: 't', style: { whiteSpace: 'normal' } }, h('b', {}, alias(x.persona_id)), h('span', { class: 'sub', style: { display: 'block' } }, (x.ejemplos || []).map(e => e.tarea).join(' · '))),
            estadoTexto(x.semana >= 3 ? 'ambar' : 'gris', `${fmt.num(x.semana)} esta semana`), h('span', { class: 'x' }, `${fmt.num(x.semana_ant)} la anterior`))), esMovil() && np.length > 6 ? h('li', { class: 'sub' }, `y ${fmt.num(np.length - 6)} personas más (en el ordenador se ven todas)`) : null)
            : h('div', { class: 'cuerpo' }, vacioLinea('Nadie rompe el semanal: nadie pasa de 2 tareas no planificadas por semana.', { icono: 'ok' })))));
    }

    // ================================================================ anuncios (índice, sin euros · D-82)
    function pintarAnuncios(z) {
      const A = D.anuncios || [];
      const R = D.anuncios_resumen || {};
      const misIni = R.iniciales?.[yo];
      const mios = A.filter(a => a.persona_id === yo);
      const deCliente = A.filter(a => a.cliente_id);
      const bloque = h('div', { class: 'pila', style: { marginTop: S[4] } });
      bloque.append(avisoParcial(`No consta quién hizo cada pieza: de ${R.anuncios ?? 0} anuncios con más de 1.000 impresiones en 30 días (${R.cuentas ?? 0} cuentas), ${R.con_autor ?? 0} llevan las iniciales de su autor. Propuesta firmada: poner las iniciales del autor al final del nombre del anuncio desde el próximo lanzamiento, por ejemplo «AKUA_PANEL-01_${misIni || 'CA'}».`, { titulo: 'Parcial.' }));
      if (!(dir || comparar) || mios.length || misIni) {
        if (mios.length) bloque.append(panel({ titulo: 'Mis piezas', icono: 'star', sub: 'Índice frente a la media de su misma cuenta (media = 100), últimos 30 días, sin euros.' }, tablaAnuncios(mios)));
        else bloque.append(vacioLinea(misIni ? `Todavía no hay piezas tuyas reconocibles en Meta. Cuando los anuncios lleven «_${misIni}» en el nombre, aquí verás cómo rinden frente a la media de cada cuenta, sin euros.` : 'Todavía no hay piezas tuyas reconocibles en Meta: hace falta que los anuncios lleven las iniciales de su autor en el nombre.',
          { icono: 'grafico', quien: 'Valeria (jefa de publicidad) y quien sube el anuncio' }));
      }
      if (deCliente.length) {
        const verde = deCliente.filter(a => a.estado === 'verde').length, ambar = deCliente.filter(a => a.estado === 'ambar').length, rojo = deCliente.filter(a => a.estado === 'rojo').length;
        bloque.append(tiles([
          tile({ icono: 'star', etiqueta: 'Por encima de la media', valor: verde, estado: 'verde', contexto: 'Índice ≥ 100' }),
          tile({ icono: 'medidor', etiqueta: 'Algo por debajo', valor: ambar, estado: ambar ? 'ambar' : 'verde', contexto: 'Índice 80-99' }),
          tile({ icono: 'baja', etiqueta: 'Muy por debajo', valor: rojo, estado: rojo ? 'rojo' : 'verde', contexto: 'Índice < 80: candidata a reemplazo' }),
        ]));
        bloque.append(panel({ titulo: 'Piezas de tus clientes', icono: 'grafico', sub: 'Media de la cuenta = 100. El índice junta coste por resultado y porcentaje de clics, sin euros. Más de 1.000 impresiones en 30 días.' }, tablaAnuncios(deCliente, true)));
      } else if (dir || comparar) {
        bloque.append(vacioLinea('No hay anuncios disponibles de tus clientes en esta copia. Contrasta cobertura y fecha de Meta.', { icono: 'grafico' }));
      }
      z.append(bloque);
    }

    function tablaAnuncios(filas, conCliente) {
      return ancharBuscador(tablaDensa({ porPagina: esMovil() ? 8 : 15,
        filas: filas.map(a => ({ ...a, cliente: cliNombre.get(a.cli)?.nombre || a.cliente })), orden: { clave: 'indice', dir: 'asc' },
        buscar: { campos: ['cliente', 'anuncio', 'campana'], placeholder: 'Buscar cliente o anuncio' }, filtros: conCliente ? [{ clave: 'cliente', titulo: 'Cliente' }] : [],
        columnas: [
          { clave: 'anuncio', titulo: 'Anuncio', principal: true, celda: a => h('span', {}, h('b', {}, a.anuncio), h('span', { class: 'sub', style: { display: 'block' } }, a.campana)) },
          conCliente ? { clave: 'cliente', titulo: 'Cliente', celda: a => h('span', { class: 'celda-cli' }, logoCliente(cliNombre.get(a.cli) || { nombre: a.cliente }), a.cliente) } : null,
          { clave: 'indice', titulo: 'Índice', num: true, celda: a => a.indice === null ? '—' : estadoTexto(a.estado, fmt.num(a.indice)) },
          { clave: 'indice_coste', titulo: 'Coste (índice)', num: true, celda: a => a.indice_coste ?? '—' },
          { clave: 'indice_clics', titulo: 'Clics (índice)', num: true, celda: a => a.indice_clics ?? '—' },
          { clave: 'leads', titulo: 'Resultados', num: true },
          { clave: 'frecuencia', titulo: 'Frecuencia', num: true, celda: a => a.frecuencia ? fmt.num(a.frecuencia, 1) : '—' },
        ].filter(Boolean),
        vacio: { titulo: 'Sin anuncios', porque: '' },
      }));
    }
  },
};

// app.js · carcasa de la app: identidad, «ver como», menú por puesto, router por módulos, cmd+K y rastro.
// Los módulos no tocan nada de esto: reciben ctx en render(contenedor, ctx). Contrato en LEEME.md.

import { iniciarUsoLocal } from './_uso_local.js';
import { falloEntrada562 } from './_entrada_error_562.js';
import { puestoControl239, tituloControl239, menuActual239 } from './modulos/_control_cartera_ruta_239.js';

import { PUESTOS, PUESTO, nivelModulo, ver } from './permisos.js';
import { cargarCrudo, recortar, cargarServidor, adaptarSesion, cabeceras, pedirDato, fijarPersonas, olvidarTodo, olvidarTrasCambio, alCambiarDato, alCambiarEstadoDato } from './datos.js';
import { MODULOS, GRUPOS } from './modulos/indice.js';
import { h, icono, esqueleto, estadoVacio, frescura, chipEstado, configurarVista, formatoTexto, ICONO_MODULO, ICONO_GRUPO, selectorPeriodo, leerPeriodo, guardarPeriodo, PERIODO_IDS,
  fechas, fechasDe, fijarHoy, quitaPrefijoDepartamento, fmt } from './componentes.js';

const $ = sel => document.querySelector(sel);
const guardar = (k, v) => { try { v === null ? sessionStorage.removeItem(k) : sessionStorage.setItem(k, v); } catch { /* sin almacenamiento: no pasa nada */ } };
const leer = k => { try { return sessionStorage.getItem(k); } catch { return null; } };
const leerLocal = k => { try { return localStorage.getItem(k); } catch { return null; } };
const guardarLocal = (k, v) => { try { localStorage.setItem(k, v); } catch { /* sin almacenamiento */ } };

let medidorUso = null;
const estado = {
  servidor: false,    // true = datos recortados por servir.py (como hará el Worker); false = modo estático
  sesion: null,       // última respuesta de /api/sesion
  indicadores: null,  // catálogo de indicadores (recortado a sus puestos si no es Mili o Tomás)
  crudo: null,
  real: null,         // quien entra (en producción: el correo que da Cloudflare Access)
  persona: null,      // a quién se está viendo (real o «ver como»)
  datos: null,        // lo recortado para estado.persona
  modulos: [],        // metadatos + código cargado
  rastro: [],         // en producción: tabla `registro` de D1, inmutable
};

// --------------------------------------------------------------- arranque
/** Ronda 6 (C2): «¿Quién eres?» del prototipo. Solo en 127.0.0.1 / localhost; en el servidor entra Cloudflare Access. */
async function pintarElegir() {
  const local = ['127.0.0.1', 'localhost'].includes(location.hostname);
  $('#titulo').textContent = '¿Quién eres?';
  if (!local) { $('#main').replaceChildren(estadoVacio({ titulo: 'Entra por la dirección de la app', porque: 'Sin identificar no se ve nada.' })); return; }
  let lista = [];
  try { lista = (await (await fetch('api/elegir', { cache: 'no-store' })).json()).personas || []; } catch { /* sin lista */ }
  const ir = id => { document.cookie = `ro_yo=${encodeURIComponent(id)}; path=/; SameSite=Strict`; guardar('ro.vercomo', null); location.search = `?yo=${encodeURIComponent(id)}`; };
  $('#main').replaceChildren(h('section', { class: 'panel' }, h('header', {}, h('div', {}, h('h2', {}, 'Prototipo local · elige quién eres'),
    h('p', { class: 'sub' }, 'Solo en este Mac. En la app de verdad entras con tu correo de RO (Cloudflare Access) y esto no existe.'))),
    h('div', { class: 'fila', style: { padding: '14px 18px', flexWrap: 'wrap' } }, lista.map(p => h('button', { type: 'button', class: 'bt', on: { click: () => ir(p.id) } }, p.alias)))));
}

async function arrancar() {
  const params = new URLSearchParams(location.search);
  // V2-E: ?hoy=AAAA-MM-DD solo en el prototipo local, para probar «hoy», «vencida» y «esta semana» un lunes o un fin de mes.
  if (params.get('hoy') && ['127.0.0.1', 'localhost'].includes(location.hostname)) fijarHoy(params.get('hoy'));
  // Ronda 6 (C2): sin identidad no se entra como nadie. ?yo= o la galleta del prototipo; si no, «¿Quién eres?».
  const galleta = (document.cookie.match(/(?:^|; )ro_yo=([^;]*)/) || [])[1];
  const yo = params.get('yo') || (galleta ? decodeURIComponent(galleta) : null);
  // Ronda 14 (causa 4): con la identidad del prototipo ya se sabe de quién es lo guardado; se confirma con la sesión.
  const comoIni = params.get('como') || comoGuardado(yo);
  // Ronda 14 (causa 7): el código de la pantalla de entrada se pide ya, a la vez que la sesión (el código no es secreto;
  // los datos sí, y esos los decide el servidor). Sin pantalla en la dirección, Mi día.
  const idIni = (location.hash || '').replace(/^#\/?/, '').split(/[/?]/)[0] || (/^setter_/.test(comoIni || yo || '') ? 'setters' : 'mi-dia');   // 3-oct: la setter entra directa a su pantalla
  const mIni = MODULOS.find(x => x.id === idIni && x.fichero && x.estado === 'hecho');
  if (mIni) import(`./modulos/${mIni.fichero.replace('./', '')}`).catch(() => { /* se reintenta al abrirla */ });
  // …y la verdad y el catálogo, a la vez que la sesión (antes iban después). Quedan en la memoria con la misma clave
  // que pedirá ponerPersona; si el servidor dice otra cosa (401/403), se descartan sin más.
  // V2-E: la verdad única solo la recibe quien ve «En rojo» (las setters no: 403 y error en la consola). Se recuerda de la
  // última vez por persona; si no se sabe, no se pide a una setter. La decisión de verdad la toma cargarVerdad().
  const veVerdadAntes = leerLocal(`ro.verdad.${comoIni || yo}`);
  const pedirVerdad = veVerdadAntes === '1' || (veVerdadAntes === null && !/^setter/.test(comoIni || yo || ''));
  if (yo) for (const r of [pedirVerdad ? 'modulo/verdad/clientes' : null, 'indicadores'].filter(Boolean)) pedirDato(r, { yo, como: comoIni || yo }).catch(() => {});
  const listoDisco = fijarPersonas(yo, comoIni || yo, { provisional: true });
  try {
    // 1) Con servir.py: identidad y recorte en el servidor.
    // «Ver como» guardado solo vale para la misma persona real (propuesta 5 de E6); si el servidor lo niega, se entra sin él.
    let s;
    try { s = await cargarServidor(yo, params.get('como') || comoGuardado(yo)); }
    catch (e) { if (comoGuardado(yo) && !params.get('como')) { guardar('ro.vercomo', null); s = await cargarServidor(yo, null); } else throw e; }
    if (s) {
      estado.servidor = true;
      estado.sesion = s;
      estado.crudo = { personas: s.datos.personas, meta: s.datos.meta };
      ponerCookie(s.real.id, s.persona.id);
    } else {
      // 2) Sin servidor (http.server): modo estático de respaldo (no protege nada; solo para desarrollar pantallas).
      estado.crudo = await cargarCrudo();
    }
  } catch (e) {
    if (e.status === 401) { olvidarTodo(); return pintarElegir(); }
    if (e.status === 403) olvidarTodo();
    const fallo = falloEntrada562(e);
    $('#titulo').textContent = fallo.titulo;
    $('#subtitulo').textContent = '';
    document.title = `${fallo.titulo} · App RO`;
    $('#main').replaceChildren(estadoVacio(fallo));
    return;
  }
  await listoDisco;
  // Ronda 14 (auditoría 37, causa 1): con servir.py el menú sale de los permisos que manda el servidor (modulos_puestos,
  // leídos de indice.js y de cada fichero) y el código de cada pantalla se importa al abrirla (cargarModulo). Sin
  // servidor (modo estático) se importan todos, como antes.
  const puestosServidor = estado.servidor ? estado.sesion.modulos_puestos : null;
  if (puestosServidor) {
    estado.modulos = MODULOS.filter(m => Object.hasOwn(puestosServidor, m.id))
      .map(m => ({ ...m, puestos_que_lo_ven: puestosServidor[m.id] || {} }));
  } else {
    estado.modulos = MODULOS.map(m => ({ ...m }));
    await Promise.all(estado.modulos.map(cargarModulo));
  }

  // Identidad. Prototipo: ?yo=<id> (por defecto Tomás). Producción: Cloudflare Access.
  const porId = id => estado.crudo.personas.find(p => p.id === id);
  if (estado.servidor) {
    estado.real = porId(estado.sesion.real.id) || estado.sesion.real;
    await fijarPersonas(estado.sesion.real.id, estado.sesion.persona.id);   // el servidor dice quién es: lo guardado, solo suyo
    await ponerPersona(porId(estado.sesion.persona.id) || estado.sesion.persona, { registrar: false, sesion: estado.sesion });
  } else {
    estado.real = porId(yo) || porId('tomas') || estado.crudo.personas[0];   // solo modo estático
    const como = puedeVerComo() ? porId(params.get('como') || comoGuardado(estado.real.id)) : null;
    await ponerPersona(como || estado.real, { registrar: false });
  }

  try { $('#rastro-n').textContent = JSON.parse(sessionStorage.getItem('ro.rastro') || '[]').length; $('#yo-pop-n').textContent = $('#rastro-n').textContent; } catch { /* opcional */ }
  pintarVerComo();
  pintarRecarga();
  conectarMenuYo();
  conectarTeclado();
  conectarMenuMovil();
  window.addEventListener('hashchange', () => ruta(true));
  alCambiarDato(datoCambiado);
  const navegacionAlArrancar = navegacionActual;
  let medirUso = false;
  if (estado.servidor && !estado.sesion?.pilotoLectura) {
    try { medirUso = (await api('uso/aviso', { rastrear: false })).disponible !== false; } catch { /* sin medición, se puede trabajar */ }
  }
  if (medirUso) medidorUso = iniciarUsoLocal({
    identidad: () => ({real: estado.real.id, como: estado.persona.id}),
    pantallas: new Set(MODULOS.map(m => m.id)),
    enviar: (dato, quien) => fetch('api/uso', {method: 'POST', cache: 'no-store', keepalive: true,
      headers: cabeceras(quien.real, quien.como), body: JSON.stringify(dato)}),
  });
  // La persona puede navegar mientras se prepara la medición: ese destino ya está pintado.
  if (navegacionAlArrancar === navegacionActual) await ruta(false);
  else if (pintura.id) medidorUso?.pantalla(pintura.id);
  precargarEnReposo();
  // R15: buscador, atajos, contadores y «Algo va mal», con el navegador libre (no frenan la entrada).
  setTimeout(() => (self.requestIdleCallback ? requestIdleCallback(() => ayudas().catch(() => {}), { timeout: 2500 }) : ayudas().catch(() => {})), 400);
}

// --------------------------------------------- ronda 14 · código de cada pantalla bajo demanda
/** Importa el código de una pantalla «hecha» (una sola vez) y deja sus metadatos sobre los del índice. */
const _importando = new Map();
function cargarModulo(m) {
  if (!m || typeof m.render === 'function' || !m.fichero || (m.estado && m.estado !== 'hecho')) return Promise.resolve(m);
  if (!_importando.has(m.id)) {
    _importando.set(m.id, import(`./modulos/${m.fichero.replace('./', '')}`).then(x => {
      const num = m.num;
      Object.assign(m, x.default, { num, estado: 'hecho' });
      return m;
    }).catch(e => {
      console.warn(`Módulo ${m.id} no carga:`, e);
      Object.assign(m, { estado: 'roto', error: String(e) });
      _importando.delete(m.id);
      return m;
    }));
  }
  return _importando.get(m.id);
}

/** Con el navegador libre, el código de las demás pantallas de esa persona (en orden de menú, de dos en dos). Medido en
 *  4G lenta: mejor que rel=prefetch (que se baja dos veces por el modo del módulo) y que no precargar. */
function precargarEnReposo() {
  if (!estado.servidor) return;
  // Ronda 14: sw.js guarda solo la página (sin datos) para no esperar a «¿ha cambiado?» al entrar. Solo con servir.py.
  try { if ('serviceWorker' in navigator && isSecureContext) navigator.serviceWorker.register('sw.js').catch(() => {}); } catch { /* sin él, igual */ }
  const cola = modulosVisibles().filter(m => m.estado === 'hecho' && typeof m.render !== 'function');
  const libre = fn => (self.requestIdleCallback ? requestIdleCallback(fn, { timeout: 4000 }) : setTimeout(fn, 400));
  const siguiente = () => {
    const lote = cola.splice(0, 2);
    if (!lote.length) return;
    Promise.all(lote.map(cargarModulo)).then(() => libre(siguiente));
  };
  setTimeout(() => libre(siguiente), 1500);
}

// ------------------------------------- ronda 14 · lo refrescado detrás cambia → se repinta la pantalla
const pintura = { usadas: new Set(), estadosLectura: new Map(), enCurso: false, repintar: false, id: null };
let _repintarT = null;
function datoCambiado(r) {
  if (r === 'modulo/verdad/clientes' || r === 'indicadores') {   // la carcasa se actualiza; sólo sus consumidores se repintan
    const consumida = pintura.usadas.has(r);
    const navegacion = navegacionActual;
    const identidad = `${estado.real?.id}|${estado.persona?.id}`;
    estado.indicadores = null;
    Promise.all([cargarVerdad(), catalogoIndicadores()]).then(() => {
      if (identidad !== `${estado.real?.id}|${estado.persona?.id}`) return;
      pintarMenu();
      // Actualizar el menú no debe reiniciar filtros/borradores de una pantalla que no usa esta fuente.
      if (consumida && navegacion === navegacionActual) repintarLuego();
    });
    return;
  }
  if (!pintura.usadas.has(r)) return;
  repintarLuego();
}
function repintarLuego() {
  if (pintura.enCurso) { pintura.repintar = true; return; }
  clearTimeout(_repintarT);
  _repintarT = setTimeout(() => {
    const id = (location.hash || '').replace(/^#\/?/, '').split(/[/?]/)[0];
    if (!pintura.id || id === pintura.id || !id) ruta(false, { refresco: true });
  }, 120);
}
// 487 · sólo estado de transporte: sin repintar módulos ni lanzar nuevas lecturas.
function fuenteLectura487(ruta) {
  if (/^modulo\/crm\//.test(ruta)) return 'CRM';
  if (/^modulo\/captacion\//.test(ruta)) return 'Captación';
  if (/^modulo\/produccion\//.test(ruta)) return 'Producción';
  if (/^modulo\/mi_trabajo\//.test(ruta)) return 'Mi trabajo';
  if (/^modulo\/seo\//.test(ruta)) return 'SEO';
  if (/^cliente\//.test(ruta)) return 'Detalle de cliente';
  return 'Lectura de esta pantalla';
}
function estadoGuardado487() {
  const fallos = [...pintura.estadosLectura.values()].filter(x => x.falloActualizacion);
  return fallos.sort((a,b) => a.hora-b.hora)[0] || pintura.guardado || null;
}
function detalleLecturas487() {
  const destino = document.getElementById('frescura');
  if (!destino) return;
  destino.querySelector('[data-lecturas-487]')?.remove();
  const filas = [...pintura.estadosLectura.entries()].filter(([,e]) => e.falloActualizacion);
  if (!filas.length) return;
  destino.append(h('div', { class:'pila', 'data-lecturas-487':'1', style:{gap:'4px',marginTop:'6px'} },
    filas.map(([ruta,e]) => h('span', {title:'Hora de recepción HTTP en RO; no es la fecha de observación del proveedor.'},
      `${fuenteLectura487(ruta)} · lectura válida ${fechas.hora(new Date(e.hora).toISOString())} · último intento ${fechas.hora(new Date(e.ultimoIntento).toISOString())}: sin confirmar`))));
}
function estadoDatoCambiado487(ruta, info) {
  if (ruta === null) { pintura.estadosLectura.clear(); pintura.guardado = null; }
  else {
    if (!pintura.usadas.has(ruta)) return;
    if (info?.falloActualizacion && Number.isFinite(info.hora) && Number.isFinite(info.ultimoIntento)
        && Number.isFinite(new Date(info.hora).getTime()) && Number.isFinite(new Date(info.ultimoIntento).getTime()))
      pintura.estadosLectura.set(ruta, {hora:info.hora,ultimoIntento:info.ultimoIntento,falloActualizacion:true});
    else pintura.estadosLectura.delete(ruta);
    if (info === null && pintura.guardado?.ruta === ruta) pintura.guardado = null;
  }
  marcarGuardado(estadoGuardado487());
  detalleLecturas487();
}
// 489 · en móvil el chip de cabecera está oculto: banda independiente del título.
function avisoMovil489(info) {
  let banda = document.getElementById('lectura-fallo-489');
  if (!banda && info?.falloActualizacion) {
    const cabecera = document.querySelector?.('.topbar');
    if (!cabecera) return;
    banda = h('div', {id:'lectura-fallo-489',class:'lectura-fallo-489 no-imprimir',role:'status','aria-live':'polite',hidden:true});
    cabecera.after(banda);
  }
  if (!banda) return;
  if (!info?.falloActualizacion) { banda.hidden = true; banda.textContent = ''; return; }
  const fecha = new Date(info.hora);
  const dia = fecha.toLocaleDateString('es-ES',{day:'2-digit',month:'2-digit',timeZone:'Europe/Madrid'});
  banda.textContent = `Última lectura válida ${dia}, ${fechas.hora(fecha.toISOString())} · actualización sin confirmar`;
  banda.title = 'Recepción de la respuesta en RO; no es la fecha de observación del proveedor. Se conserva la última lectura válida.';
  banda.hidden = false;
}
function marcarGuardado(info) {
  avisoMovil489(info);
  const el = document.getElementById('dato-guardado');
  if (!el) return;
  if (!info) { el.hidden = true; el.textContent = ''; return; }
  // V2-E (40_A M8): «Guardado 00:50» no lo entendía nadie. Ahora lo dice entero y en el móvil no sale (estilos.css).
  const hh = fechas.hora(new Date(info.hora).toISOString());
  el.textContent = info.falloActualizacion ? `Última lectura válida ${hh} · actualización sin confirmar` : `Datos guardados a las ${hh}`;
  el.title = info.falloActualizacion ? 'Hora de recepción de la respuesta en RO, no de observación del proveedor. No se pudo confirmar la actualización.' : `Se enseñan los datos guardados a las ${hh} mientras se comprueba si hay algo nuevo; si lo hay, la pantalla se actualiza sola.`;
  el.hidden = false;
}
alCambiarEstadoDato(estadoDatoCambiado487);
// Fin 487 · estado de transporte.

/** «Ver como»: Mili y Tomás (reglas_permisos.json → ver_como). Con servidor, lo decide el servidor. */
/** «Ver como» guardado en la pestaña, solo si lo guardó esta misma persona real. */
function comoGuardado(yo) {
  const v = leer('ro.vercomo') || '';
  const [quien, como] = v.split(':');
  return quien === yo && como ? como : null;
}

function puedeVerComo() {
  if (estado.servidor) return !!estado.sesion?.puedeVerComo;
  return !!estado.real && ver(estado.real, { tipo: 'ver_como' }).ok;
}

/** Identidad del prototipo también en cookie, para que un fetch() de un módulo llegue identificado a servir.py. */
function ponerCookie(yo, como) {
  try {
    document.cookie = `ro_yo=${encodeURIComponent(yo)}; path=/; SameSite=Strict`;
    document.cookie = `ro_como=${encodeURIComponent(como && como !== yo ? como : '')}; path=/; SameSite=Strict`;
  } catch { /* sin cookies: los módulos deben usar ctx.api */ }
}

async function ponerPersona(p, { registrar = true, sesion = null } = {}) {
  const viendo = p.id !== estado.real.id;
  if (estado.servidor) {
    // El servidor recorta para la persona vista (y apunta el «ver como» en el rastro, con hora del servidor).
    const s = sesion || await cargarServidor(estado.real.id, viendo ? p.id : null);
    estado.sesion = s;
    estado.datos = adaptarSesion(s.datos);
    ponerCookie(estado.real.id, p.id);
    await fijarPersonas(estado.real.id, p.id);   // ronda 14: en «ver como» lo guardado vive solo en memoria
  } else {
    estado.datos = recortar(p, estado.crudo);
  }
  estado.persona = p;
  configurarVista({ direccion: (p.puestos || []).includes('direccion') });   // ronda 6: lo técnico solo para dirección
  estado.indicadores = null;   // el catálogo se pide de nuevo: depende de los puestos de la persona vista
  // Ronda 5: una sola verdad por cliente. Ronda 14 (causa 4): verdad y catálogo A LA VEZ (antes, uno detrás de otro).
  await Promise.all([cargarVerdad(), catalogoIndicadores()]);
  guardar('ro.vercomo', viendo ? `${estado.real.id}:${p.id}` : null);
  if (viendo && registrar && !estado.servidor) apuntar({ accion: 'ver_como', objeto: p.id, detalle: `${estado.real.alias} ve como ${p.alias} (solo lectura)` });
  if (viendo && registrar && estado.servidor) apuntarLocal({ accion: 'ver_como', objeto: p.id, detalle: `${estado.real.alias} ve como ${p.alias} (solo lectura) · en el rastro del servidor` });
  pintarBanda();
  if (_ayudas) { estado.contadores = {}; estado.fijados = undefined; _ayudas.then(m => m.alCambiarPersona()).catch(() => {}); }   // R15
  pintarMenu();
}

// ------------------------------------------------------------- API (servir.py)
/** Llama a servir.py con la identidad del prototipo. En producción, Cloudflare Access pone la identidad. */
async function api(ruta, { metodo = 'GET', cuerpo, sinComo = false, vigente = () => true, rastrear = true, info: infoPeticion } = {}) {
  if (!estado.servidor) throw new Error('Sin servidor: arranca «python3 servir.py» para usar esta función.');
  // Ronda 14 (causa 4): las lecturas pasan por la memoria por persona (datos.js · pedirDato); las escrituras, no.
  if (metodo === 'GET') {
    const limpia = ruta.replace(/^\/?(api\/)?/, '');
    if (rastrear && vigente()) pintura.usadas.add(limpia);
    const usadas = pintura.usadas;
    const info = infoPeticion || {};
    let d;
    try { d = await pedirDato(limpia, { yo: estado.real.id, como: sinComo ? null : estado.persona?.id, info }); }
    catch (e) { medidorUso?.evento('error'); throw e; }
    if (rastrear && vigente() && usadas === pintura.usadas && info.guardado) pintura.guardado = {guardado:true,hora:info.hora,ruta:limpia};
    if (rastrear && vigente() && usadas === pintura.usadas) estadoDatoCambiado487(limpia, info);
    return d;
  }
  const identidadPOST529 = JSON.stringify([estado.real?.id, estado.persona?.id]);
  const comprobarPOST529 = () => {
    if (!vigente() || JSON.stringify([estado.real?.id, estado.persona?.id]) !== identidadPOST529) {
      const e = new Error('La vista ha cambiado. El resultado de esta petición no se muestra aquí; comprueba su estado antes de repetirla.');
      e.status = 409;
      throw e;
    }
  };
  comprobarPOST529();
  olvidarTrasCambio(ruta);
  const r = await fetch(`api/${ruta.replace(/^\/?(api\/)?/, '')}`, {
    method: metodo, cache: 'no-store',
    headers: cabeceras(estado.real.id, sinComo ? null : estado.persona?.id),
    body: cuerpo === undefined ? undefined : JSON.stringify(cuerpo),
  });
  const d = await r.json().catch(() => ({}));
  comprobarPOST529();
  if (!r.ok) { medidorUso?.evento('error', 'guardar'); const e = new Error(d.error || `Error ${r.status}`); e.status = r.status; throw e; }
  if (_ayudas && !/^\/?(api\/)?(rastro|opinion|ia\/)/.test(ruta)) _ayudas.then(m => m.trasCambio()).catch(() => {});   // R15: contadores al día
  return d;
}

/** Ronda 5 · la verdad única por cliente (fuentes_verdad/generar_verdad.py → data/verdad/clientes.json). */
async function cargarVerdad() {
  const identidad = `${estado.real?.id}|${estado.persona?.id}`;
  // V2-E: sin «En rojo» en el puesto, el servidor no da la verdad única (403): no se pide y el menú no pinta su número.
  const veVerdad = !estado.servidor || estado.modulos.some(m => m.id === 'en-rojo' && nivelModulo(estado.persona, m));
  if (estado.persona?.id) guardarLocal(`ro.verdad.${estado.persona.id}`, veVerdad ? '1' : '0');
  if (!veVerdad) { estado.verdad = { porId: {}, comunPorId: {}, definiciones: {} }; return; }
  try {
    const v = estado.servidor ? await api('modulo/verdad/clientes', { rastrear: false }) : await (await fetch('data/verdad/clientes.json', { cache: 'no-cache' })).json();
    if (identidad !== `${estado.real?.id}|${estado.persona?.id}`) return;
    estado.verdad = { ...v, porId: Object.fromEntries((v.clientes || []).map(c => [c.cliente_id, c])), comunPorId: Object.fromEntries((v.comun || []).map(c => [c.id, c])) };
  } catch { if (identidad === `${estado.real?.id}|${estado.persona?.id}`) estado.verdad = { porId: {}, comunPorId: {}, definiciones: {} }; }
}

async function catalogoIndicadores() {
  if (estado.indicadores) return estado.indicadores;
  const identidad = `${estado.real?.id}|${estado.persona?.id}`;
  let leidos;
  try {
    leidos = estado.servidor ? await api('indicadores', { rastrear: false })
      : await (await fetch('indicadores.json', { cache: 'no-cache' })).json();
  } catch { leidos = { indicadores: [], _meta: { error: 'sin catálogo' } }; }
  if (identidad !== `${estado.real?.id}|${estado.persona?.id}`) return estado.indicadores;
  estado.indicadores = leidos;
  estado.indicadores.porId = Object.fromEntries((estado.indicadores.indicadores || []).map(i => [i.id, i]));
  return estado.indicadores;
}

// ----------------------------------------------------------------- rastro
/** Apunta una acción. En producción: POST /api/rastro, inmutable (quién, qué, cuándo, antes/después). */
function apuntar(ev) {
  // Con servidor: el rastro va a local.db (hora del servidor, imborrable). En «ver como» no se escribe.
  if (estado.servidor && estado.persona && estado.persona.id === estado.real.id) {
    api('rastro', { metodo: 'POST', cuerpo: ev }).catch(e => console.warn('Rastro no guardado:', e.message));
  }
  return apuntarLocal(ev);
}
function apuntarLocal(ev) {
  const fila = { cuando: new Date().toISOString(), quien: estado.real.id, como: estado.persona?.id, ...ev };
  estado.rastro.push(fila);
  try { const prev = JSON.parse(sessionStorage.getItem('ro.rastro') || '[]'); prev.push(fila); sessionStorage.setItem('ro.rastro', JSON.stringify(prev.slice(-200))); } catch { /* opcional */ }
  const n = $('#rastro-n'); if (n) n.textContent = Number(n.textContent || 0) + 1;
  const n2 = $('#yo-pop-n'); if (n2 && n) n2.textContent = n.textContent;
  return fila;
}

// ----------------------------------------------- «Actualizar ahora» (E0 ronda 3)
/** Botón de la cabecera, solo Mili y Tomás (regla «recargar») y solo con servir.py. Pide una recarga ligera
 *  (recarga.json), enseña «Pedida a las…», el avance y «Datos de las…», y recarga la sesión al terminar. */
function pintarRecarga() {
  if (!estado.servidor || !ver(estado.real, { tipo: 'recargar' }).ok || document.getElementById('recarga-btn')) return;
  const hhmm = iso => (iso || '').replace(' ', 'T').slice(11, 16);
  const local = iso => { try { return new Date(iso.replace(' ', 'T') + 'Z').toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' }); } catch { return hhmm(iso); } };
  // Ronda 9 (auditoría 30): «Actualizar ahora» es un icono ↻ en la cabecera; la hora de los datos, en su burbuja y en el menú de la persona.
  const estadoTxt = h('span', { class: 'sub', id: 'recarga-estado', 'aria-live': 'polite' });
  const AYUDA = 'Actualizar ahora: relanza los generadores locales en modo ligero (Desk, ClickUp, una consulta de Zadarma y lo ya guardado). Solo Mili y Tomás.';
  const btn = h('button', { type: 'button', class: 'bt icono recarga-btn', id: 'recarga-btn', title: AYUDA, 'aria-label': 'Actualizar ahora' }, icono('recargar'));
  new MutationObserver(() => { btn.title = `${estadoTxt.textContent ? estadoTxt.textContent + ' · ' : ''}${AYUDA}`; }).observe(estadoTxt, { childList: true, characterData: true, subtree: true });
  let sondeo = null;
  const pintar = r => {
    if (!r) { estadoTxt.textContent = ''; btn.removeAttribute('aria-busy'); return; }
    const pasos = r.pasos || [];
    if (r.estado === 'pendiente') estadoTxt.textContent = `Pedida a las ${local(r.pedida)}`;
    else if (r.estado === 'en_curso') estadoTxt.textContent = `Actualizando… ${pasos.length} pasos hechos`;
    else estadoTxt.textContent = `${r.estado === 'ok' ? 'Datos de las' : 'Con fallos · datos de las'} ${local(r.terminada)}`;
    const viva = ['pendiente', 'en_curso'].includes(r.estado);
    btn.toggleAttribute('disabled', viva);
    viva ? btn.setAttribute('aria-busy', 'true') : btn.removeAttribute('aria-busy');
    return viva;
  };
  const mirar = async (recargarAlAcabar = false) => {
    try {
      const d = await api('recarga', { sinComo: true });   // ronda 6: siempre como la persona real (sin error en «ver como»)
      const viva = pintar(d.recargas[0]);
      if (viva && !sondeo) sondeo = setInterval(() => mirar(true), 5000);
      if (!viva && sondeo) { clearInterval(sondeo); sondeo = null; if (recargarAlAcabar) { await ponerPersona(estado.persona, { registrar: false }); ruta(false); } }
    } catch { /* sin permiso o sin servidor: no se enseña nada */ }
  };
  btn.addEventListener('click', async () => {
    try { const r = await api('recarga', { metodo: 'POST', cuerpo: {}, sinComo: true }); pintar(r.recarga); mirar(true); }
    catch (e) { estadoTxt.textContent = `No se pudo: ${e.message}`; }
  });
  $('#topbar-acc').append(btn);
  const pop = $('#yo-pop-recarga');
  pop.replaceChildren(h('span', { class: 'yo-pop-t' }, 'Datos'), estadoTxt);
  pop.hidden = false;
  mirar();
}

// -------------------------------------------- menú de la persona (avatar ▾)
// Ronda 9 (auditoría 30, P0-3): la cabecera cabe en una fila de 64 px; lo que no cabe va aquí: «Ver como»,
// la hora de los datos y el rastro. Se abre con clic o teclado y se cierra con Esc o al pulsar fuera.
function conectarMenuYo() {
  const btn = $('#yo-btn'), pop = $('#yo-pop');
  if (!btn || btn.dataset.conectado) return;
  btn.dataset.conectado = '1';
  const abrir = si => { pop.hidden = !si; btn.setAttribute('aria-expanded', String(si)); if (si) pop.querySelector('select, a, button')?.focus(); };
  btn.addEventListener('click', e => { e.stopPropagation(); abrir(pop.hidden); });
  pop.addEventListener('keydown', e => { if (e.key === 'Escape') { abrir(false); btn.focus(); } });
  document.addEventListener('click', e => { if (!pop.hidden && !$('#yo-menu').contains(e.target)) abrir(false); });
}
function pintarMenuYo() {
  const p = estado.persona;
  $('#yo-pop-nombre').textContent = p.id === estado.real.id ? (p.nombre || p.alias) : `${p.alias} (viendo como)`;
  $('#yo-pop-puesto').textContent = p.puestos.map(x => PUESTO[x]?.nombre).join(' · ');
  const r = $('#yo-pop-rastro');
  r.hidden = !modulosVisibles().some(m => m.id === 'decisiones' && m.estado === 'hecho');
}

// ------------------------------------------------ periodo común (D-P-N1)
// El módulo que exporte usa_periodo: true (o una lista de ids) recibe ctx.periodo y la carcasa pinta el selector en la
// barra de contexto, bajo la cabecera. Se recuerda por persona (localStorage ro.periodo.<persona>) y el enlace admite
// ?p=30d&c=anterior (y &desde=&hasta= para «A medida») para compartir la vista exacta.
const periodoVivo = { valor: null, oyentes: [] };
function periodoDeEnlace() {
  const q = new URLSearchParams(location.search);
  const hq = (location.hash.split('?')[1] || '');
  const qh = new URLSearchParams(hq);
  const id = qh.get('p') || q.get('p');
  if (!id || !PERIODO_IDS.includes(id)) return null;
  return { id, comparar: qh.get('c') || q.get('c') || 'anterior', desde: qh.get('desde') || q.get('desde') || undefined, hasta: qh.get('hasta') || q.get('hasta') || undefined };
}
function escribirEnlacePeriodo(v) {
  try {
    const u = new URL(location.href);
    u.searchParams.set('p', v.id); u.searchParams.set('c', v.comparar || 'anterior');
    if (v.id === 'medida') { u.searchParams.set('desde', v.desde); u.searchParams.set('hasta', v.hasta); } else { u.searchParams.delete('desde'); u.searchParams.delete('hasta'); }
    history.replaceState(null, '', u.toString());
  } catch { /* sin history: no pasa nada */ }
}
// Ronda 10: usa_periodo puede ser una función (params) => true | false | [ids], para sub-rutas que no dependen del periodo
// (Paneles › «Dónde está cada panel»). periodos_con_datos (lista o función (params)) o ctx.periodosConDatos(lista) en el
// render añaden «Con datos» al menú «Más» (meses cerrados del Informe, etc.).
function usaPeriodo(m, params = []) {
  if (!m || m.estado !== 'hecho' || !m.usa_periodo) return false;
  try { return typeof m.usa_periodo === 'function' ? m.usa_periodo(params) || false : m.usa_periodo; } catch (e) { console.error(e); return false; }
}
function conDatosDe(m, params = []) {
  try { const v = typeof m?.periodos_con_datos === 'function' ? m.periodos_con_datos(params) : m?.periodos_con_datos; return Array.isArray(v) ? v : []; } catch { return []; }
}
function pintarBarraPeriodo(m, params = [], conDatos = null) {
  const barra = $('#barra-ctx'), dentro = $('#barra-ctx-in');
  if (!conDatos) periodoVivo.oyentes = [];
  const usa = usaPeriodo(m, params);
  if (!usa) { barra.hidden = true; dentro.replaceChildren(); periodoVivo.valor = null; return null; }
  const persona = estado.persona.id;
  const enlace = conDatos ? null : periodoDeEnlace();
  const ids = Array.isArray(usa) ? usa : undefined;
  const inicial = conDatos && periodoVivo.valor ? periodoVivo.valor : (enlace || leerPeriodo(persona));
  if (enlace) guardarPeriodo(persona, enlace);
  const sel = selectorPeriodo({ comun: true, persona, ids, valorInicial: inicial, conDatos: conDatos || conDatosDe(m, params), alCambiar: v => {
    periodoVivo.valor = v;
    escribirEnlacePeriodo(v);
    const oyentes = periodoVivo.oyentes.slice();
    if (oyentes.length) oyentes.forEach(fn => { try { fn(v); } catch (e) { console.error(e); } });
    else ruta(false);                        // si el módulo no escucha, se vuelve a pintar con el periodo nuevo
  } });
  periodoVivo.valor = sel.valor();
  dentro.replaceChildren(sel);
  barra.hidden = false;
  return periodoVivo.valor;
}

// ----------------------------------------------------------- «ver como»
function pintarVerComo() {
  const caja = $('#vercomo');
  if (!puedeVerComo()) { caja.hidden = true; return; }
  const sel = h('select', { id: 'vercomo-sel', 'aria-describedby': 'vercomo-ayuda' },
    h('option', { value: estado.real.id }, `Yo (${estado.real.alias})`),
    PUESTOS.map(pu => h('optgroup', { label: pu.nombre },
      estado.crudo.personas.filter(p => p.puestos.includes(pu.id) && p.id !== estado.real.id && p.estado !== 'baja')
        .map(p => h('option', { value: p.id }, `${p.alias}${p.prueba ? ' · prueba' : ''} — ${pu.nombre}`)))));
  sel.value = estado.persona.id;
  sel.addEventListener('change', async () => {
    const p = estado.crudo.personas.find(x => x.id === sel.value);
    await ponerPersona(p);
    ruta(false);
  });
  caja.replaceChildren(h('label', { for: 'vercomo-sel' }, 'Ver como'), sel,
    h('span', { id: 'vercomo-ayuda', class: 'sr' }, 'Solo para pruebas y para Tomás. Es de solo lectura y queda en el rastro.'));
  caja.hidden = false;
}

function pintarBanda() {
  const banda = $('#banda');
  const p = estado.persona;
  if (p.id === estado.real.id) { banda.hidden = true; return; }
  const puestos = p.puestos.map(x => PUESTO[x]?.nombre).join(' + ');
  banda.replaceChildren(
    h('span', {}, h('b', {}, `Viendo como ${p.alias}`), ` (${puestos}) · solo lectura · queda en el rastro`),
    h('button', { type: 'button', on: { click: async () => { await ponerPersona(estado.real); $('#vercomo-sel').value = estado.real.id; ruta(false); } } }, 'Volver a mí'));
  banda.hidden = false;
}

// ------------------------------------------------------------------ menú
// Ronda 8 (E6): pantalla de inicio por puesto. Setters → su «Mi día del setter»; el resto → «Mi día».
// Si TODOS los puestos de la persona tienen inicio propio, «Mi día» general sale del menú (nada de dos «Mi día»).
const INICIO_POR_PUESTO = { setters: 'setters' };
// 3-oct (Tomás): pantalla de inicio preferida sin quitar «Mi día» del menú. Proyectos (Coti, directora de producto) → Dirección de producto.
const INICIO_PREFERIDO = { proyectos: 'producto' };
function inicioPropio(p) {
  const propios = (p.puestos || []).map(x => INICIO_POR_PUESTO[x]).filter(Boolean);
  return propios.length && propios.length === (p.puestos || []).length ? propios[0] : null;
}
function modulosVisibles() {
  const propio = inicioPropio(estado.persona);
  const vistos = new Set();
  return estado.modulos.filter(m => {
    if (vistos.has(m.id) || !nivelModulo(estado.persona, m)) return false;   // sin entradas repetidas en el menú
    if (propio && m.id === 'mi-dia') return false;
    vistos.add(m.id);
    return true;
  });
}

// R15 (A6) · etiquetas de los contadores (las mismas que usa ayudas.js) y «Mis clientes» del menú.
const ETIQUETA_CONTADOR = {
  alertas: n => `${n} ${n === 1 ? 'alerta tuya abierta' : 'alertas tuyas abiertas'}`,
  bandeja: n => `${n} ${n === 1 ? 'correo sin contestar' : 'correos sin contestar'} de tu cartera`,
  'chat-equipo': n => `${n} ${n === 1 ? 'mención sin leer' : 'menciones sin leer'}`,
  produccion: n => `${n} ${n === 1 ? 'tarea vencida' : 'tareas vencidas'} en tu mano`,
  decisiones: n => `${n} ${n === 1 ? 'decisión espera' : 'decisiones esperan'} tu sí`,
};
// V3a (44 §2.1) + glosario del coordinador (3-oct): los tres niveles se llaman Crítico · Vigilar · Bien en toda la app
// (el dato interno sigue siendo critico/atencion/bien); «cliente crítico», nunca «en crítico».
const COLOR_GRAVEDAD = { critico: ['rojo', 'crítico'], atencion: ['ambar', 'vigilar'], bien: ['verde', 'bien'] };
function idsMisClientes() {
  if (Array.isArray(estado.fijados)) return estado.fijados;
  const g = { critico: 0, atencion: 1, bien: 2 };
  return (estado.datos?.clientes || []).filter(c => c.detalle && estado.datos.carteraIds?.has?.(c.id))
    .sort((a, b) => (g[estado.verdad?.porId?.[a.id]?.gravedad] ?? 3) - (g[estado.verdad?.porId?.[b.id]?.gravedad] ?? 3) || a.nombre.localeCompare(b.nombre, 'es'))
    .slice(0, 12).map(c => c.id);
}
/** V2-E · gravedad de un cliente para el menú: la de la verdad única (la misma vara que En rojo), nunca otra. */
const gravedadVerdad = id => estado.verdad?.porId?.[id]?.gravedad || estado.verdad?.comunPorId?.[id]?.gravedad || null;
// V2-E (40_C 19): «Mis clientes» va al final del menú (la pantalla de trabajo queda arriba) con 5 a la vista, los más
// graves primero, y «Ver los N» para el resto. Abierto o plegado se recuerda en la pestaña.
const MIS_A_LA_VISTA = 5;
function misClientesMenu(vis) {
  if (!estado.servidor) return null;
  const porId = new Map((estado.datos?.clientes || []).filter(c => c.detalle).map(c => [c.id, c]));
  const ids = idsMisClientes().filter(id => porId.has(id));
  if (!ids.length) return null;
  const veFicha = vis.some(m => m.id === 'ficha' && m.estado === 'hecho');
  const fijados = Array.isArray(estado.fijados);
  const sobran = ids.length - MIS_A_LA_VISTA;
  const abierto = leer('ro.mis.abierto') === '1';
  const criticos = ids.filter(id => gravedadVerdad(id) === 'critico').length;
  const caja = h('div', { class: `ng ng-mis${sobran > 0 && !abierto ? ' plegado' : ''}`, role: 'group', 'aria-labelledby': 'ng-mis' },
    h('div', { class: 'ngt', id: 'ng-mis', title: fijados ? 'Los que has fijado (desde la ficha o el buscador)' : 'Tu cartera; fija o quita desde la ficha o el buscador' },
      h('span', {}, 'Mis clientes'), criticos ? h('span', { class: 'n r', 'aria-label': `${criticos} ${criticos === 1 ? 'cliente crítico' : 'clientes críticos'} (la misma regla que En rojo)`, title: `${criticos} ${criticos === 1 ? 'cliente crítico' : 'clientes críticos'} (la misma regla que En rojo)` }, criticos) : null),
    ids.map((id, i) => {
      const c = porId.get(id);
      const [col, txt] = COLOR_GRAVEDAD[gravedadVerdad(id)] || ['', 'sin dato'];
      return h('a', { href: veFicha ? `#/ficha/${id}` : `#/en-rojo/${id}`, 'data-cli': id, class: i >= MIS_A_LA_VISTA ? 'extra' : null, title: `${c.nombre} · ${txt}` },
        h('span', { class: `punto ${col}`, 'aria-hidden': 'true' }), h('span', { class: 'nl' }, c.nombre), h('span', { class: 'sr' }, ` · ${txt}`));
    }),
    sobran > 0 ? h('button', { type: 'button', class: 'mis-mas', 'aria-expanded': String(abierto), on: { click: e => {
      const g = e.currentTarget.closest('.ng-mis'); const ahora = g.classList.toggle('plegado');
      e.currentTarget.setAttribute('aria-expanded', String(!ahora)); e.currentTarget.lastChild.textContent = ahora ? `Ver los ${ids.length}` : 'Ver menos';
      guardar('ro.mis.abierto', ahora ? null : '1');
    } } }, icono('chev', { clase: 's' }), h('span', {}, abierto ? 'Ver menos' : `Ver los ${ids.length}`)) : null);
  return caja;
}
function marcarActual() {
  const [, id, p0, p1] = (location.hash || '').replace(/^#/, '').split('?')[0].split('/');
  const cli = ['ficha', 'en-rojo'].includes(id) ? decodeURIComponent(p0 || '') : '';
  const solicitado = id === 'mi-dia' ? (p0 === 'control-cartera' ? p1 : ['account','operaciones','direccion'].includes(p0) ? p0 : null) : null;
  const puesto = puestoControl239(estado.real, estado.persona, solicitado);
  document.querySelectorAll('#nav a[data-subruta="control-cartera"]').forEach(a => {
    if (!puesto) return;
    a.setAttribute('href', `#/mi-dia/control-cartera/${puesto}`);
    const texto = a.querySelector('.nl');
    if (texto) texto.textContent = tituloControl239(puesto);
  });
  document.querySelectorAll('#nav a[data-id]').forEach(a => menuActual239({id:a.dataset.id,subruta:a.dataset.subruta}, pintura.id || id, p0) ? a.setAttribute('aria-current', 'page') : a.removeAttribute('aria-current'));
  document.querySelectorAll('#nav a[data-cli]').forEach(a => (cli && a.dataset.cli === cli ? a.setAttribute('aria-current', 'true') : a.removeAttribute('aria-current')));
}

function pintarMenu() {
  const p = estado.persona;
  queueMicrotask(pintarMenuYo);
  $('#quien').textContent = p.alias;
  const puestoTxt = p.puestos.map(x => PUESTO[x]?.nombre).filter(Boolean).join(' · ');
  $('#quien-puesto').textContent = puestoTxt;
  // V2-E (40_A B11, 40_B B5): bajo el logo, el puesto real de quien mira (antes «Operaciones» para todos).
  const marca = document.querySelector('.brand small');
  if (marca) { marca.textContent = puestoTxt || 'Ranking Online'; marca.title = puestoTxt; }
  document.querySelector('.brand')?.setAttribute('aria-label', `Ranking Online${puestoTxt ? ` · ${puestoTxt}` : ''}, ir al inicio`);
  // Ronda 8 (D-P03): el número del menú «En rojo» son los clientes en crítico de la verdad única, como la pantalla.
  // V2-E: sin verdad única no se inventa otra vara (antes caía a las alarmas, que daban 40 de 68): el número no sale.
  const rojos = estado.verdad?.comun?.length ? estado.verdad.comun.filter(c => c.gravedad === 'critico').length : null;
  const misRojos = rojos !== null && estado.datos.carteraIds?.size ? estado.verdad.comun.filter(c => c.gravedad === 'critico' && estado.datos.carteraIds.has(c.id)).length : null;
  const txtRojos = rojos === null ? '' : `${rojos} ${rojos === 1 ? 'cliente crítico' : 'clientes críticos'} en la agencia${misRojos !== null ? ` · ${misRojos} de tu cartera` : ''}`;
  const vis = modulosVisibles();
  const puestoControl = puestoControl239(estado.real, estado.persona);
  const nav = $('#nav');
  // R15 (A6): lo pendiente de cada pantalla (ayudas.js lo cuenta con la definición de «Lo mío», Alertas, Producción y la
  // campana) y «Mis clientes» fijados (o, si nunca ha fijado, su cartera) con un punto según la gravedad de la verdad única.
  const C = estado.contadores || {};
  const contador = m => {
    const n = C[m.id];
    if (!(n > 0) || m.estado !== 'hecho') return null;
    const txt = ETIQUETA_CONTADOR[m.id]?.(n) || `${n} pendientes`;
    return h('span', { class: `n${['alertas', 'produccion'].includes(m.id) ? ' r' : ''}`, 'aria-label': txt, title: txt }, n > 99 ? '99+' : n);
  };
  const grupos = GRUPOS.map(g => {
    const ms = vis.filter(m => m.grupo === g);
    if (!ms.length) return null;
    return h('div', { class: 'ng', role: 'group', 'aria-labelledby': `ng-${g}` },
      h('div', { class: 'ngt', id: `ng-${g}` }, g),
      ms.map(m => [h('a', { href: `#/${m.id}`, 'data-id': m.id },
        icono(ICONO_MODULO[m.id] || ICONO_GRUPO[m.grupo] || 'res'),   // D-P02: el icono lo pone el menú (carcasa.js queda de respaldo)
        h('span', { class: 'nl' }, m.id === inicioPropio(estado.persona) ? 'Mi día' : m.titulo),   // 3-oct (Tomás): el «Mi día» de la setter ES su pantalla
        m.id === 'en-rojo' ? (rojos ? h('span', { class: 'n r', 'aria-label': txtRojos, title: txtRojos }, rojos) : null) : contador(m),
        m.estado !== 'hecho' ? h('span', { class: 'prev' }, m.estado === 'roto' ? 'error' : 'previsto') : null),
        m.id === 'mi-dia' && puestoControl ? h('a', {href:`#/mi-dia/control-cartera/${puestoControl}`, 'data-id':'mi-dia', 'data-subruta':'control-cartera'},
          icono('res'), h('span', {class:'nl'}, tituloControl239(puestoControl))) : null]));
  });
  const mis = misClientesMenu(vis);
  if (mis) { const iSis = GRUPOS.indexOf('Sistema'); grupos.splice(iSis >= 0 ? iSis : grupos.length, 0, mis); }
  nav.replaceChildren(...grupos.filter(Boolean));
  marcarActual();

  // frescura
  const f = (estado.datos.meta || estado.crudo.meta).fuentes || [];
  const malas = f.filter(x => x.estado !== 'ok').length;
  // V2-E (40_A B12, 40_C 6): una sola hora de datos, y si no son de hoy se dice el día («Datos del vie 2, 23:14»).
  const gen = (estado.datos.meta || estado.crudo.meta).generado || '';
  const dd = fechas.diaDatos(gen), hhGen = fechas.hora(gen) || gen.slice(-5);
  const txtDatos = dd.esHoy || !dd.dia ? `Datos de las ${hhGen}` : `Datos ${dd.texto.startsWith('datos de ayer') ? 'de ayer' : `del ${fechas.diaSemana(dd.dia)} ${Number(dd.dia.slice(8, 10))}`}, ${hhGen}`;
  $('#frescura').replaceChildren(
    h('summary', {}, txtDatos, malas ? h('b', {}, ` · ${malas} con aviso`) : '', estado.servidor ? '' : h('b', {}, ' · sin servidor')),
    h('div', { class: 'pila', style: { gap: '4px', marginTop: '6px' } }, f.map(x => frescura({ fuente: x.fuente, edad_h: x.edad_h, estado: x.estado }))));
  detalleLecturas487();
}

// ---------------------------------------------------------------- router
let navegacionActual = 0;
async function ruta(porUsuario, { refresco = false } = {}) {
  const token = ++navegacionActual;
  pintura.estadosLectura.clear();
  pintura.guardado = null;
  marcarGuardado(null); detalleLecturas487();
  const vigente = () => token === navegacionActual;
  clearTimeout(_repintarT);
  const [, id, ...resto] = (location.hash || '').replace(/^#/, '').split('?')[0].split('/');
  const vis = modulosVisibles();
  let m = vis.find(x => x.id === id);
  if (!m) {
    const propio = inicioPropio(estado.persona);
    const preferido = (estado.persona.puestos || []).map(x => INICIO_PREFERIDO[x]).find(id => vis.some(x => x.id === id && x.estado === 'hecho'));
    const inicio = (propio && vis.find(x => x.id === propio)) || (preferido && vis.find(x => x.id === preferido)) || vis.find(x => x.id === 'mi-dia' && x.estado === 'hecho') || vis.find(x => x.id === 'en-rojo') || vis[0];
    if (id && estado.modulos.some(x => x.id === id)) {
      pintura.id = id; pintura.usadas = new Set(); pintura.guardado = null;
      pintura.enCurso = false; pintura.repintar = false; periodoVivo.oyentes = [];
      marcarGuardado(null);
      return pintarSinPermiso(estado.modulos.find(x => x.id === id), inicio);
    }
    if (inicio && location.hash !== `#/${inicio.id}`) history.replaceState(null, '', `#/${inicio.id}`);
    m = inicio;
  }
  if (!m) return;
  document.querySelectorAll('#nav a[data-id]').forEach(a => a.dataset.id === m.id ? a.setAttribute('aria-current', 'page') : a.removeAttribute('aria-current'));
  document.querySelectorAll('#nav a[data-cli]').forEach(a => (['ficha', 'en-rojo'].includes(m.id) && a.dataset.cli === resto[0] ? a.setAttribute('aria-current', 'true') : a.removeAttribute('aria-current')));
  cerrarMenuMovil();
  const main = $('#main');
  const scroll = refresco ? window.scrollY : null;
  // Cada ruta conserva su propio destino. Al navegar, el anterior queda desconectado aunque su render siga esperando.
  // display:contents mantiene la disposición de los hijos en el grid/flex de #main y los selectores de sus descendientes.
  const cont = h('div', { 'data-ruta': m.id, style: { display: 'contents' } });
  main.replaceChildren(cont);
  $('#titulo').textContent = m.titulo;
  $('#subtitulo').textContent = m.resumen || '';
  document.title = `${m.titulo} · App RO`;
  pintura.usadas = new Set(); pintura.id = m.id; pintura.guardado = null;
  medidorUso?.pantalla(m.id);
  pintura.enCurso = false; pintura.repintar = false;
  periodoVivo.oyentes = [];
  if (!refresco) marcarGuardado(null);
  if (m.estado === 'hecho' && typeof m.render !== 'function' && m.fichero) {
    const esqCarga = setTimeout(() => { if (vigente() && cont.isConnected && !refresco) cont.replaceChildren(esqueleto({ tarjetas: 4, lineas: 4 })); }, 150);
    try { await cargarModulo(m); } finally { clearTimeout(esqCarga); }
    if (!vigente()) return;
    if (m.estado === 'roto') pintarMenu();
    cont.replaceChildren();
  }
  if (m.estado !== 'hecho' || typeof m.render !== 'function') {
    pintarBarraPeriodo(null); pintarBarraPeriodo.ultimo = null;
    cont.append(estadoVacio({
      titulo: m.estado === 'roto' ? `${m.titulo} no carga` : `${m.titulo} está previsto (fase ${m.fase})`,
      porque: m.estado === 'roto' ? 'Esta pantalla no ha cargado.' : m.resumen,
      que_hacer: m.estado === 'roto' ? 'Recarga la página; si sigue, avisa a Tomás.' : `Llega en la fase ${m.fase}.`,
      tecnico: m.estado === 'roto' ? String(m.error || '') : `modulos/${m.id.replace(/-/g, '_')}.js`,
    }));
  } else {
    await catalogoIndicadores();
    if (!vigente()) return;
    const clavePeriodo = `${m.id}|${JSON.stringify(usaPeriodo(m, resto))}|${location.search || ''}|${m.id === 'informe-cliente' ? JSON.stringify(resto.slice(1)) : ''}`;
    if (pintarBarraPeriodo.ultimo !== clavePeriodo || (usaPeriodo(m, resto) && !periodoVivo.valor)) { pintarBarraPeriodo(m, resto); pintarBarraPeriodo.ultimo = clavePeriodo; }
    const ctx = crearCtx(m, resto, vigente);
    let miEsq = null;
    const esq = setTimeout(() => { if (vigente() && cont.isConnected && !cont.childElementCount) { miEsq = esqueleto({ tarjetas: 4, lineas: 4 }); cont.append(miEsq); } }, 300);
    pintura.enCurso = true; pintura.repintar = false;
    try { await m.render(cont, ctx); }
    catch (e) {
      if (vigente()) {
        medidorUso?.evento('error');
        console.error(e);
        cont.replaceChildren(estadoVacio({ titulo: 'Este módulo ha fallado al pintarse', porque: String(e.message || e), que_hacer: 'Recarga; si sigue, avisa a quien lo construye.' }));
      }
    } finally { clearTimeout(esq); miEsq?.remove(); }
    if (!vigente()) return;
    pintura.enCurso = false;
    marcarGuardado(estadoGuardado487());
    if (scroll !== null) window.scrollTo(0, scroll);
    if (pintura.repintar) { pintura.repintar = false; repintarLuego(); }
    else if (pintura.guardado) setTimeout(() => { if (vigente() && !estadoGuardado487()?.falloActualizacion) marcarGuardado(null); }, 6000);
  }
  if (vigente() && porUsuario) main.focus({ preventScroll: true });
}

function pintarSinPermiso(m, inicio) {
  pintarBarraPeriodo(null); pintarBarraPeriodo.ultimo = null;
  $('#titulo').textContent = m.titulo;
  $('#subtitulo').textContent = '';
  document.title = `${m.titulo} · App RO`;
  $('#main').replaceChildren(estadoVacio({
    titulo: 'Esta pantalla no es de tu puesto',
    porque: `«${m.titulo}» no está en el menú de ${estado.persona.puestos.map(x => PUESTO[x]?.nombre).join(' + ')}.`,
    que_hacer: 'Si crees que la necesitas, pídeselo a Mili o a Tomás.',
    accion: inicio ? h('a', { class: 'bt', href: `#/${inicio.id}` }, `Ir a ${inicio.titulo}`) : null,
  }));
}

async function ctx_accion(persona, a, modulo) {
  if (persona.id !== estado.real.id) throw new Error('«Ver como» es solo lectura: no se hace nada.');
  if (!estado.servidor) { apuntarLocal({ modulo, accion: 'accion_simulada', objeto: a.objeto, detalle: a.texto }); return { ok: true, estado: 'simulada', local: true }; }
  return api('acciones', { metodo: 'POST', cuerpo: { modulo, ...a } });
}

/** Cumpleaños (solo día y mes) y aniversarios de entrada en la agencia de las personas activas, en los próximos días. */
function celebraciones(personas, dias) {
  const [ha, hm, hd] = fechas.hoy().split('-').map(Number);   // V2-E: el «hoy» común (Madrid), no el del Mac
  const hoy = new Date(ha, hm - 1, hd);
  const out = [];
  for (const p of personas) {
    if (p.estado && p.estado !== 'activo') continue;
    const cuenta = (mmdd, tipo, desde) => {
      if (!mmdd) return;
      const [m, d] = mmdd.split('-').map(Number);
      let f = new Date(hoy.getFullYear(), m - 1, d);
      if (f < hoy) f = new Date(hoy.getFullYear() + 1, m - 1, d);
      const en = Math.round((f - hoy) / 864e5);
      if (en > dias) return;
      const anios = desde ? f.getFullYear() - Number(desde.slice(0, 4)) : null;
      if (tipo === 'aniversario' && !(anios >= 1)) return;
      out.push({ persona_id: p.id, alias: p.alias || p.nombre, tipo, en_dias: en, anios,
        fecha: `${f.getFullYear()}-${String(m).padStart(2, '0')}-${String(d).padStart(2, '0')}` });
    };
    cuenta(p.cumple_dia_mes, 'cumple');
    cuenta(p.fecha_ingreso ? p.fecha_ingreso.slice(5, 10) : null, 'aniversario', p.fecha_ingreso);
  }
  return out.sort((a, b) => a.en_dias - b.en_dias);
}

/** ctx que recibe cada módulo. Ver contrato completo en LEEME.md. */
function crearCtx(m, resto, vigente = () => true, { rastrear = true } = {}) {
  const persona = estado.persona;
  const d = estado.datos;
  const cpPermisos = { carteraIds: d.carteraIds, carteraPorSilla: d.carteraPorSilla, personas: d.personas || estado.crudo.personas, clientesPorId: Object.fromEntries(d.clientes.map(c => [c.id, c])) };
  const comun = (ruta, valor) => { if (rastrear && vigente()) pintura.usadas.add(ruta); return valor; };
  return {
    vigente,                                            // identidad y navegación de esta renderización
    persona,                                            // { id, nombre, alias, puestos: [...] }
    real: estado.real,                                  // quien está de verdad delante
    puestos: persona.puestos.map(x => PUESTO[x]),       // objetos de PUESTOS
    nivel: nivelModulo(persona, m),                     // 'todo' | 'suyo' | 'resumen'
    pilotoLectura: !!estado.sesion?.pilotoLectura,
    soloLectura: persona.id !== estado.real.id || (estado.servidor && !!estado.sesion?.soloLectura),         // «ver como» = nunca escribir
    clientes: d.clientes,                               // todos, ya recortados (c.detalle dice si es suyo)
    clientesVisibles: d.clientes.filter(c => c.detalle),// los que puede abrir
    carteraIds: d.carteraIds,                           // los asignados a su silla (Set)
    ambito: d.ambito,                                   // 'todos' | 'disciplina' | 'cartera' | 'tareas' | 'ninguno'
    soloSuCartera: !!d.soloSuCartera,                   // Tomás 3-oct: account sin ámbito mayor → el servidor solo manda SUS clientes
    datos: { alarmas: d.alarmas, personas: d.personas, meta: d.meta, asignaciones: d.asignaciones || [] },
    ver: dato => ver(persona, dato, cpPermisos),
    // ---- Añadido en E0 (compatible hacia atrás: lo anterior no cambia) ----
    servidor: estado.servidor,                          // true = datos recortados por servir.py
    veModulo: id => modulosVisibles().some(x => x.id === id && x.estado === 'hecho'),   // (ronda 3) ¿ve esa pantalla?
    // ---- Ronda 5: una sola verdad por cliente y nombres únicos ----
    /** verdad(id) → detalle de la verdad única del cliente (si lo puede abrir) o, si no, su línea común
     *  { gravedad: 'critico'|'atencion'|'bien', motivo, responsable_id, sin_account, nuevo }. null si no existe. */
    verdad: id => comun('modulo/verdad/clientes', estado.verdad?.porId?.[id] || estado.verdad?.comunPorId?.[id] || null),
    verdadComun: () => comun('modulo/verdad/clientes', estado.verdad?.comun || []),
    definiciones: () => comun('modulo/verdad/clientes', estado.verdad?.definiciones || {}),
    /** Ronda 9 (D-P-DIN) · cuotaEmpresa() → { mes, recurrente, cuota_mes, facturable, ajustes_mes, coherente, aviso } de
     *  fuentes_dinero/cuotas.json (la misma fuente que la cuota de cada cliente). null si tu puesto no ve la cuota.
     *  Mi día, Finanzas y el Panel de dirección deben leer esta, no calcular la suya (octubre: 67.291 · 70.781 · 70.581 €). */
    cuotaEmpresa: () => comun('modulo/verdad/clientes', estado.verdad?.cuota_empresa || null),
    /** nombre(id) → nombre corto de personas.json («mili» → «Mili»). Nunca enseñar ids crudos. */
    /** Ronda 8 · celebraciones({ dias = 7 }) → cumpleaños (día y mes) y aniversarios de entrada de las personas activas en
     *  los próximos «dias» días (hoy incluido): [{ persona_id, alias, tipo: 'cumple'|'aniversario', fecha: 'AAAA-MM-DD',
     *  en_dias, anios }] por fecha. Lo ve todo el equipo (regla de Tomás, 2-oct). */
    celebraciones: ({ dias = 7 } = {}) => celebraciones(d.personas || [], dias),
    /** avisosCelebraciones() → solo para RRHH y dirección: lo que cae HOY o dentro de exactamente 7 días. */
    avisosCelebraciones: () => (persona.puestos || []).some(x => x === 'rrhh' || x === 'direccion')
      ? celebraciones(d.personas || [], 7).filter(c => c.en_dias === 0 || c.en_dias === 7) : [],
    /** zona(id) → zona horaria de la persona («Europe/Madrid», «America/Argentina/Buenos_Aires»…); sin id, la de quien se ve. */
    zona: id => (d.personas || []).find(x => x.id === (id || persona.id))?.zona || 'Europe/Madrid',
    // ---- V2-E (3-oct): UNA SOLA VARA de fechas para toda la app (ver LEEME › Fechas) ----
    /** hoy · 'AAAA-MM-DD' del calendario de la agencia (Madrid), el mismo en todas las pantallas. Es un TEXTO (no función). */
    hoy: fechas.hoy(),
    /** fechas · hoy(), ayer(), dia(t), diasDesde(t), vencida(t), venceHoy(t), estaSemana(t), semana(), ultimoLaborable(),
     *  relativo(t) («hoy», «ayer», «el vie 2»), hora(t), diaDatos(generado) («datos de ayer (vie 2)»), antiguedad(h). */
    fechas,
    /** diaDatos() → { dia, esHoy, texto } del día de los datos de la sesión: si no son de hoy, dilo con texto. */
    diaDatos: () => fechas.diaDatos(d.meta?.generado || estado.crudo?.meta?.generado),
    /** fechasDe(zona) · lo mismo con la zona de una persona, solo para enseñarle SU hora («a las 9 de tu mañana»). */
    fechasDe,
    /** plural(n, 'cita') → «1 cita» / «3 citas» (fmt.plural; nunca «1 citas»). */
    plural: (n, uno, varios) => fmt.plural(n, uno, varios),
    nombre: id => { const p = (d.personas || []).find(x => x.id === id); return id ? (p ? (p.alias || p.nombre) : 'persona sin ficha') : '—'; },
    carteraPorSilla: d.carteraPorSilla || {},           // { account: Set, trafficker: Set, … }
    indicador: id => comun('indicadores', estado.indicadores?.porId?.[id] || null),   // ficha del catálogo (fórmula, umbral, origen, medible)
    indicadores: () => comun('indicadores', estado.indicadores?.indicadores || []),   // los que le tocan (todos para Mili y Tomás)
    api: (ruta, op) => api(ruta, { ...op, vigente, rastrear }),                   // servir.py con la identidad de la sesión
    /** Datos de un módulo: data/<nombre>.json recortado por el servidor (o el fichero tal cual sin servidor). */
    datosModulo: async nombre => estado.servidor ? api(`modulo/${nombre}`, { vigente, rastrear })   // ronda 14: con memoria por persona y ETag
      : (await fetch(`data/${nombre}.json`, { cache: 'no-cache' })).json(),
    /** «Ver datos» de un lead (D-88): devuelve el valor completo y queda en el rastro; error si no lo trabaja. */
    verDato: ({ almacen, ref, campo, cliente_id }) => api('ver_dato', { metodo: 'POST', cuerpo: { almacen, ref, campo, cliente_id }, vigente, rastrear }),
    /** Botón: deja la acción en la cola local «simulada» con su vista previa (nunca llama a una API externa). */
    accion: async a => {
      if (!vigente()) throw new Error('La pantalla ha cambiado. Revisa la vista actual antes de guardar.');
      if (estado.servidor && estado.sesion?.soloLectura) throw new Error('Este piloto es de consulta: no se guardan cambios.');
      return ctx_accion(persona, a, m.id);
    },
    params: resto.map(decodeURIComponent),              // #/en-rojo/<cliente> → ['<cliente>']
    navegar: ruta2 => { if (vigente()) location.hash = `#/${ruta2}`; },
    rastro: ev => apuntar({ modulo: m.id, ...ev }),     // apunta una acción (en producción, servidor)
    // ---- Ronda 9 (D-P-N1): periodo común. null si el módulo no declara usa_periodo. ----
    /** { id, desde, hasta, dias, nombre, rango, comparar: 'anterior'|'anio_ant'|'no', comp: { desde, hasta, rango } | null, texto } */
    periodo: usaPeriodo(m, resto) ? periodoVivo.valor : null,
    /** periodosConDatos([{ nombre, desde, hasta }]) · ronda 10: «Con datos» en el menú «Más» del periodo (p. ej. los meses
     *  con informe cerrado). Elegir uno deja el periodo «A medida» con esas fechas y avisa como cualquier cambio. */
    periodosConDatos: lista => { if (vigente() && usaPeriodo(m, resto) && Array.isArray(lista)) pintarBarraPeriodo(m, resto, lista); },
    /** alCambiarPeriodo(fn) → fn(periodo) cuando la persona cambia el periodo (sin volver a pintar todo). Sin oyentes, la
     *  carcasa vuelve a pintar el módulo entero con el periodo nuevo. Devuelve una función para dejar de escuchar. */
    alCambiarPeriodo: fn => { if (!vigente()) return () => {}; const escuchar = v => { if (vigente()) fn(v); }; periodoVivo.oyentes.push(escuchar); return () => { periodoVivo.oyentes = periodoVivo.oyentes.filter(x => x !== escuchar); }; },
    titulo: (t, sub) => { if (!vigente()) return; if (t) $('#titulo').textContent = t; if (sub !== undefined) $('#subtitulo').textContent = sub; if (t) document.title = `${t} · App RO`; },
  };
}

// --------------------------------------------------------------- cmd+K, atajos, contadores y «Algo va mal» (R15)
// Desde la ronda 15 viven en ayudas.js (buscador que busca dentro y hace cosas, contadores y «Mis clientes» del menú,
// «Algo va mal / Tengo una idea» y atajos). Se carga con el navegador libre; ⌘K, «/» y la lupa lo piden al momento.
let _ayudas = null;
function ayudas() {
  if (!_ayudas) {
    _ayudas = import('./ayudas.js').then(m => {
      m.iniciar({
        estado, api: (ruta, op) => api(ruta, { ...op, rastrear: false }), apuntar, modulosVisibles, pintarMenu, puedeVerComo, PUESTO, idsMisClientes,
        ctxPara: id => crearCtx(estado.modulos.find(x => x.id === id) || modulosVisibles()[0], [], () => true, { rastrear: false }),
      });
      return m;
    }).catch(e => { console.warn('ayudas.js no carga:', e); _ayudas = null; throw e; });
  }
  return _ayudas;
}
const conAyudas = fn => ayudas().then(fn).catch(() => {});

function conectarTeclado() {
  $('#buscar').addEventListener('click', () => conAyudas(m => m.abrirPaleta()));
  document.addEventListener('keydown', e => {
    const enCampo = /^(INPUT|SELECT|TEXTAREA)$/.test(document.activeElement?.tagName) || !!document.activeElement?.isContentEditable;
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); conAyudas(m => m.alternarPaleta()); }
    else if (e.key === '/' && !enCampo && $('#paleta').hidden && !document.querySelector('.dialogo-fondo')) { e.preventDefault(); conAyudas(m => m.abrirPaleta()); }
    else if (e.key === 'Escape' && document.querySelector('.app').classList.contains('menu-abierto')) cerrarMenuMovil(true);
  });
  const mac = /Mac|iPhone|iPad/.test(navigator.platform || navigator.userAgent);
  $('#kbd-k').textContent = mac ? '⌘K' : 'Ctrl K';
}

// -------------------------------------------------------------- móvil
function conectarMenuMovil() {
  $('#menu-btn').addEventListener('click', () => {
    const abierto = document.querySelector('.app').classList.toggle('menu-abierto');
    $('#menu-btn').setAttribute('aria-expanded', abierto);
    $('#velo').hidden = !abierto;
    if (abierto) $('#nav a')?.focus();
  });
  $('#velo').addEventListener('click', () => cerrarMenuMovil(true));
}
function cerrarMenuMovil(devolverFoco) {
  const app = document.querySelector('.app');
  if (!app.classList.contains('menu-abierto')) return;
  app.classList.remove('menu-abierto');
  $('#menu-btn').setAttribute('aria-expanded', 'false');
  $('#velo').hidden = true;
  if (devolverFoco) $('#menu-btn').focus();
}

// Ronda 6 (auditoría 29, F-15): todo texto pintado en la pantalla pasa por el formato es-ES común
// (fechas legibles, decimales con coma, miles con punto, nada de «(s)» ni dos puntos sueltos), aunque el módulo
// lo haya escrito a mano. No toca campos de formulario ni lo que va entre «».
// Ronda 14 (barrido 39, piezas comunes): nunca a la vista rutas de datos («ficha/_privado/contactos#gac», «alertas/p_tomas»),
// nombres de fichero ni códigos de obra (M14, W1, D-27, SP14…), los pinte quien los pinte. Lo de entre «» no se toca, ni
// el plegado técnico «¿De dónde sale?» (solo dirección) ni el catálogo de componentes.
const RUTA_PRIVADA = /\b[a-z_]+\/_privado\/([\w-]+)(?:#([\w-]+))?/g;
const RUTA_PERSONAL = /\b([a-z_]+)\/p_([a-z0-9_]+)\b/g;
const FICHERO = /\b[\w./-]+\.(?:json|py|md|js|csv|xlsx|sql|db)\b/g;
const CODIGO_OBRA = /\s*\((?:(?:SP|[DGWCEMPBI])-?\d{1,3}[a-z]?(?:[,·/ y]+)?)+\)|\b(?!M365\b)(?:SP|[DGWCEMPBI])-?\d{1,3}\b(?:\s*§\s*\d+)?/g;   // «GA4» o «B2B» no son códigos
function sinCodigos(x) {
  return x.split(/(«[^»]*»)/).map(t => {
    if (t.startsWith('«')) return t;
    const y = t
      .replace(RUTA_PRIVADA, (_, q, de) => `${q.replace(/_/g, ' ')}${de ? ` · ${de.replace(/[_-]/g, ' ')}` : ''}`)
      .replace(RUTA_PERSONAL, (_, q, de) => `${q.replace(/_/g, ' ')} de ${de.replace(/^setter_/, '').replace(/_/g, ' ')}`)
      .replace(FICHERO, '')
      // V3a (44 §0.2): si quitar el código deja la frase coja («llega con .»), se reescribe o se quita la preposición
      .replace(/\b(llega|llegan|llegará|llegarán|vendrá|vendrán|irá|irán|saldrá|saldrán|estará|estarán)\s+con\s+(?!M365\b)(?:SP|[DGWCEMPBI])-?\d{1,3}\b/g, '$1 más adelante')
      .replace(/\s+(?:con|en|de|tras|hasta|desde|por|para|a|según)\s+(?!M365\b)(?:SP|[DGWCEMPBI])-?\d{1,3}\b(?=\s*(?:[.,;:)]|$))/g, '')
      .replace(CODIGO_OBRA, '');
    return y === t ? t : y.replace(/\(\s*\)/g, '').replace(/:\s*:/g, ':').replace(/\s+([:,.;)])/g, '$1').replace(/ {2,}/g, ' ');
  }).join('');
}
// V3a (44 §2.2): mayúsculas solo en las cabeceras de estilo «eyebrow» (tablas, separadores) y, aun ahí, los nombres
// propios (Desk, Mili, LinkedIn…) van como se escriben: se envuelven en <span class="propio"> (text-transform: none).
const PROPIOS_FIJOS = ['Desk', 'Zoho', 'LinkedIn', 'Instagram', 'Facebook', 'Meta', 'Google', 'GoHighLevel', 'HighLevel', 'ClickUp', 'Looker',
  'Fathom', 'Zadarma', 'WhatsApp', 'Metricool', 'Search Console', 'Analytics', 'Ziflow', 'Airtable', 'Holded', 'Snov.io', 'TikTok', 'YouTube', 'Tomás', 'Mili'];
const MAYUS = 'th, .titulo-seccion, .periodo-menu-t, .atajos-t, .yo-pop-t';
let _rePropios = null, _propiosDe = null;
function rePropios() {
  const ps = estado.datos?.personas || [];
  if (_rePropios && _propiosDe === ps) return _rePropios;
  const alias = ps.map(p => p.alias).filter(a => a && a.length > 2 && /^[A-ZÁÉÍÓÚÑ]/.test(a));
  const todos = [...new Set([...PROPIOS_FIJOS, ...alias])].sort((a, b) => b.length - a.length).map(x => x.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
  _propiosDe = ps;
  _rePropios = new RegExp(`(^|[^\\wáéíóúñÁÉÍÓÚÑ])(${todos.join('|')})(?![\\wáéíóúñ])`, 'g');
  return _rePropios;
}
function propiosSinMayusculas(n) {
  const el = n.parentElement;
  if (!el || el.classList.contains('propio') || !el.closest(MAYUS)) return;
  const re = rePropios(); re.lastIndex = 0;
  const t = n.nodeValue;
  if (!re.test(t)) return;
  re.lastIndex = 0;
  const frag = document.createDocumentFragment();
  let i = 0, m;
  while ((m = re.exec(t))) {
    const ini = m.index + m[1].length;
    if (ini > i) frag.append(t.slice(i, ini));
    frag.append(h('span', { class: 'propio' }, m[2]));
    i = ini + m[2].length;
  }
  if (i < t.length) frag.append(t.slice(i));
  n.replaceWith(frag);
}
function formatearTextos(raiz) {
  const recorrido = document.createTreeWalker(raiz, NodeFilter.SHOW_TEXT, {
    acceptNode: n => (n.parentElement?.closest('input,textarea,select,script,style,code,pre,[contenteditable]') ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT),
  });
  const tecnico = el => !!el?.closest('.que-es, [data-tecnico], .catalogo-vivo');
  const enCatalogo = /^#\/componentes/.test(location.hash || '');
  const nodos = [];
  while (recorrido.nextNode()) nodos.push(recorrido.currentNode);
  for (const n of nodos) {
    const t = n.nodeValue;
    if (!t) continue;
    let nuevo = t;
    if (!enCatalogo && /\/|\.|\d/.test(t) && !tecnico(n.parentElement)) nuevo = sinCodigos(nuevo);
    if (/\d|\(s\)|\s:\s|en crítico|sept/i.test(nuevo)) nuevo = formatoTexto(nuevo);   // V3a: glosario y «sep»
    if (/^\s*[a-z]/.test(nuevo)) nuevo = quitaPrefijoDepartamento(nuevo);   // V2-E (40_A M6): «administracion · …» → «Administración · …»
    if (nuevo !== t.trim() && nuevo !== t) n.nodeValue = (t.match(/^\s*/)[0]) + nuevo.trim() + (t.match(/\s*$/)[0]);
    propiosSinMayusculas(n);
  }
}
let _pendiente = null;
new MutationObserver(() => {
  clearTimeout(_pendiente);
  _pendiente = setTimeout(() => { const m = document.getElementById('main'); if (m) formatearTextos(m); }, 60);
}).observe(document.getElementById('main'), { childList: true, subtree: true });

// V3a (44 §0.1): cabecera común de impresión (PDF de cualquier pantalla): logo y nombre de RO, título de la pantalla y la
// fecha de hoy (Madrid). En pantalla no se ve (.cab-impresion); se rehace cada vez que cambia el título.
function cabeceraImpresion() {
  const main = document.getElementById('main');
  if (!main) return;
  let c = document.getElementById('cab-impresion');
  if (!c) { c = h('div', { class: 'cab-impresion', id: 'cab-impresion', 'aria-hidden': 'true' }); main.before(c); }
  const marca = document.querySelector('.brand .marca')?.cloneNode(true);
  const titulo = (document.getElementById('titulo')?.textContent || '').trim();
  const sub = (document.getElementById('subtitulo')?.textContent || '').trim();
  const hoy = formatoTexto(fechas.hoy());
  c.replaceChildren(...[marca, h('div', {}, h('span', { class: 'marca-t' }, 'Ranking Online'), h('b', {}, titulo === 'Cargando…' ? '' : titulo),
    h('span', {}, [sub, `Impreso el ${hoy}`].filter(Boolean).join(' · ')))].filter(Boolean));
}
{
  const t = document.getElementById('titulo');
  if (t) new MutationObserver(cabeceraImpresion).observe(t, { childList: true, characterData: true, subtree: true });
  window.addEventListener('beforeprint', cabeceraImpresion);
  cabeceraImpresion();
}

arrancar();

// Para depurar en consola (solo prototipo).
window.RO = { estado, chipEstado, api };

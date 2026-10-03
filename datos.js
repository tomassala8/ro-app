// datos.js · capa de datos de la app.
//
// Dos modos (E0, 2-oct):
//  · SERVIDOR (python3 servir.py): el navegador NO descarga data/*.json (servir.py los niega con 403).
//    Pide /api/sesion y recibe ya recortado lo de la persona (o de la vista con «ver como»).
//    Es lo mismo que hará el Worker de Cloudflare con W1.
//  · ESTÁTICO (python3 -m http.server): modo de respaldo para desarrollar sin servidor; descarga todo y
//    recorta aquí con la misma regla. NO protege nada; solo sirve para probar pantallas.
// Los módulos NUNCA leen los JSON crudos: solo ctx (ver LEEME.md).

import { ver, cartera, carteraPorSilla, ambito } from './permisos.js';

const FICHEROS = ['personas', 'asignaciones', 'clientes', 'alarmas', 'logos', 'meta'];

/** Cabeceras de identidad del prototipo (en producción las pone Cloudflare Access). */
export function cabeceras(yo, como) {
  // Ronda 6 (C2): X-RO-App en todas las peticiones a servir.py (los POST sin ella se rechazan).
  const h = { 'Content-Type': 'application/json', 'X-RO-App': '1' };
  if (yo) h['X-RO-Yo'] = yo;
  if (como && como !== yo) h['X-RO-Como'] = como;
  return h;
}

/**
 * cargarServidor(yo, como) → la sesión de servir.py, o null si no hay servidor (modo estático).
 * Lanza error con el mensaje del servidor si responde 403/503 (persona de baja, puerta de secretos…).
 */
export async function cargarServidor(yo, como) {
  let r;
  // Ronda 14 (causa 7): la primera vez, la sesión que index.html ya pidió en paralelo (misma dirección, sin cabeceras
  // propias, para que el navegador la reutilice). La identidad va en la dirección (?yo=) o en Access, como siempre.
  const pre = cargarServidor.usada ? null : precargaSesion(como, yo);
  cargarServidor.usada = true;
  try { r = pre ? await fetch(pre) : await fetch('api/sesion', { headers: cabeceras(yo, como), cache: 'no-store' }); }
  catch { return null; }
  const tipo = r.headers.get('Content-Type') || '';
  if (r.status === 404 || r.status === 501 || !tipo.includes('json')) return null;  // http.server: no hay API
  const cuerpo = await r.json();
  if (!r.ok) { const e = new Error(cuerpo.error || `El servidor ha respondido ${r.status}`); e.status = r.status; throw e; }
  return cuerpo;
}

/** Convierte lo que manda el servidor en lo mismo que devuelve recortar() (Sets en vez de listas). */
export function adaptarSesion(d) {
  return {
    ...d,
    carteraIds: new Set(d.carteraIds || []),
    carteraPorSilla: Object.fromEntries(Object.entries(d.carteraPorSilla || {}).map(([k, v]) => [k, new Set(v)])),
  };
}

/** Modo estático: carga los JSON del prototipo. Si falta alguno, lo dice. */
export async function cargarCrudo() {
  const crudo = {};
  await Promise.all(FICHEROS.map(async f => {
    const r = await fetch(`data/${f}.json`, { cache: 'no-cache' });
    if (!r.ok) throw new Error(`No se pudo leer data/${f}.json (${r.status}). ¿Has ejecutado build_data.py? Con servir.py los datos salen de /api/.`);
    crudo[f] = await r.json();
  }));
  return crudo;
}

/**
 * recortar(persona, crudo) → { clientes, alarmas, personas, asignaciones, meta, carteraIds, carteraPorSilla, ambito }
 * Mismo resultado que permisos.py recortar() (servir.py). Si cambias uno, cambia el otro.
 *  · clientes: TODOS con lo común (nombre, logo, responsable, salud) porque «En rojo» es común (D-90);
 *    con `detalle: true` y los campos de detalle solo si ver(cliente_detalle); cuota e inversión según ver().
 *  · alarmas de cliente: lista común; texto, acción y enlace solo con detalle. De persona: ver(alarma_persona).
 */
export function recortar(persona, crudo) {
  const porSilla = carteraPorSilla(persona, crudo.asignaciones);
  const carteraIds = cartera(persona, crudo.asignaciones);
  const cp = { carteraIds, carteraPorSilla: porSilla, personas: crudo.personas };
  const v = dato => ver(persona, dato, cp);
  const nombrePersona = Object.fromEntries(crudo.personas.map(p => [p.id, p.alias || p.nombre]));

  const COMUNES = ['id', 'nombre', 'responsable_id', 'responsable_texto', 'salud', 'salud_fuente', 'semaforo', 'nuevo', 'sin_account', 'tipo_negocio'];
  const DETALLE = ['web', 'descripcion', 'descripcion_completa', 'alta', 'tickets_abiertos', 'pend_horas', 'dias_sin_reunion', 'ult_reunion', 'prox_reunion',
    'informe_anterior', 'revision48', 'enlace_clickup', 'equipo', 'servicios'];

  const clientes = crudo.clientes.map(c => {
    const out = {};
    for (const k of COMUNES) out[k] = c[k];
    out.logo = crudo.logos[c.id] || null;
    out.responsable = c.responsable_id ? nombrePersona[c.responsable_id] : (c.responsable_texto || 'sin responsable');
    out.enCartera = carteraIds.has(c.id);
    out.detalle = v({ tipo: 'cliente_detalle', cliente_id: c.id }).ok;
    if (out.detalle) for (const k of DETALLE) out[k] = c[k];
    out.cuota = v({ tipo: 'cuota', cliente_id: c.id }).ok ? c.cuota : undefined;
    out.cuota_fuente = out.cuota !== undefined ? c.cuota_fuente : undefined;   // ronda 8: fuente única de la cuota
    out.publicidad_30d = v({ tipo: 'inversion', cliente_id: c.id }).ok ? c.publicidad_30d : undefined;
    return out;
  });
  const porId = Object.fromEntries(clientes.map(c => [c.id, c]));

  const alarmas = [];
  for (const a of crudo.alarmas) {
    const responsable = a.responsable_id ? nombrePersona[a.responsable_id] : (a.responsable_texto || 'sin responsable');
    if (a.ambito === 'cliente') {
      const conDetalle = porId[a.cliente_id]?.detalle && v({ tipo: 'alarma_detalle', cliente_id: a.cliente_id }).ok;
      alarmas.push({
        id: a.id, ambito: 'cliente', cliente_id: a.cliente_id, cliente: a.cliente, gravedad: a.gravedad,
        tipo: a.tipo, desde: a.desde, responsable_id: a.responsable_id, responsable,
        ...(conDetalle ? { texto: a.texto, accion: a.accion, enlace: a.enlace } : {}),
      });
    } else {
      // Sin responsable asignado: solo dirección y operaciones (las reparten).
      const ok = a.responsable_id
        ? v({ tipo: 'alarma_persona', persona_id: a.responsable_id }).ok
        : persona.puestos.some(p => ['direccion', 'operaciones'].includes(p));
      if (ok) alarmas.push({ ...a, responsable });
    }
  }

  return {
    clientes, alarmas, carteraIds, carteraPorSilla: porSilla, ambito: ambito(persona),
    personas: crudo.personas.map(p => ({ id: p.id, nombre: p.nombre, alias: p.alias, puestos: p.puestos, prueba: p.prueba, estado: p.estado, activo: p.activo, jefe: p.jefe, zona: p.zona, rol: p.rol, pais: p.pais, fecha_ingreso: p.fecha_ingreso, cumple_dia_mes: p.cumple_dia_mes, etiquetas: p.etiquetas || [] })),
    asignaciones: crudo.asignaciones.filter(a => a.persona_id === persona.id),
    meta: crudo.meta,
  };
}

// =====================================================================================================================
// Ronda 14 (E0 · velocidad, auditoría 37 causas 4 y 7): memoria de respuestas por persona + precarga de la sesión.
//
//  · pedirDato(ruta, { yo, como }) → GET a /api/<ruta> con «pinta lo guardado y refresca detrás» (stale-while-revalidate):
//    si ya se bajó en esta sesión (o, para la persona REAL, en la anterior: IndexedDB), se devuelve al momento y se
//    pregunta al servidor detrás con If-None-Match (ETag de servir.py: 304 sin cuerpo si no ha cambiado). Si cambia, se
//    guarda y se avisa (alCambiarDato) para repintar la pantalla.
//  · Seguridad: la clave lleva persona real + persona vista. En «ver como» solo memoria (nunca a disco). Al entrar otra
//    persona real se borra TODO lo guardado. Nunca se guarda: POST (ver datos de un lead, sueldos), _privado/, sueldos.
//    Un 401/403 borra esa entrada (y con 401 todo). Cualquier POST olvida las listas que cambian con acciones.
// =====================================================================================================================
const RUTAS_CON_MEMORIA = /^(modulo\/|indicadores$|acciones(\?|$)|avisos$|decisiones$|ia\/(lista|estado)$|cliente\/|ajustes$|altas$|buscar\/indice$|contadores$|preferencias$)/;   // R15: índice del buscador, contadores y «Mis clientes»
const NUNCA_GUARDAR = /_privado|sueldo|ver_dato|contrase|clave/i;
const SOLO_MEMORIA = /^(ajustes|altas)$/;          // pantallas de edición de personas: nunca al disco del navegador
const SIN_CAMBIO_DE_DATOS = /^(rastro|ia\/(consejo|copiloto|borrador)|ver_dato|opinion$|opiniones\/estado$)/;   // R15: «Algo va mal» no cambia datos  // POST que solo leen o apuntan (rastro, IA, «ver datos»)
const QUEDAN_TRAS_POST = /^(modulo\/|indicadores$|cliente\/)/;   // ficheros de datos: los cambia el servidor, lo dice su ETag
const COMPROBAR_CADA_MS = 5000;           // no se pregunta al servidor dos veces por lo mismo en 5 s
const MAX_TEXTO_DISCO = 4_000_000;        // ficheros enormes (informe de 2 MB) solo en memoria
const MEM = new Map();                    // clave → { texto, etag, hora, comprobado }
const oyentes = new Set();
let dueno = null;                         // persona real confirmada por el servidor (o la del prototipo, ?yo=)
let vista = null;                         // persona vista
let idb = null;                           // promesa de la base IndexedDB (null = sin disco)

const claveDe = (ruta, yo, como) => `${yo || '?'}|${como || yo || '?'}|${ruta}`;
const disco = (yo, como) => !!idb && !!yo && (!como || como === yo) && yo === dueno;

function abrirDisco() {
  try {
    if (!('indexedDB' in self)) return null;
    return new Promise(res => {
      const r = indexedDB.open('ro-datos', 1);
      r.onupgradeneeded = () => r.result.createObjectStore('datos');
      r.onsuccess = () => res(r.result);
      r.onerror = () => res(null);
      r.onblocked = () => res(null);
    });
  } catch { return null; }
}
async function tx(modo, fn) {
  try {
    const db = await idb; if (!db) return null;
    return await new Promise(res => {
      const t = db.transaction('datos', modo); const st = t.objectStore('datos');
      let out = null; const r = fn(st);
      if (r) r.onsuccess = () => { out = r.result; };
      t.oncomplete = () => res(out); t.onerror = () => res(null); t.onabort = () => res(null);
    });
  } catch { return null; }
}
const leerDisco = k => tx('readonly', st => st.get(k));
const escribirDisco = (k, v) => tx('readwrite', st => st.put(v, k));
const borrarDisco = k => tx('readwrite', st => st.delete(k));
const vaciarDisco = () => tx('readwrite', st => st.clear());

/**
 * fijarPersonas(realId, personaId) · la carcasa lo llama al entrar y al cambiar de persona vista. Si la persona real no es
 * la dueña de lo guardado en el disco, se borra todo antes de leer nada. Al cambiar de persona vista se vacía la memoria.
 * provisional = true cuando aún no lo ha confirmado el servidor (prototipo con ?yo=): solo se usa si coincide con el dueño.
 */
export async function fijarPersonas(realId, personaId, { provisional = false } = {}) {
  if (!idb) idb = abrirDisco();
  if (vista !== null && vista !== personaId) MEM.clear();
  vista = personaId;
  if (!realId) { dueno = null; return; }
  const guardado = await tx('readonly', st => st.get('__dueno'));
  if (guardado && guardado !== realId) {
    if (provisional) { dueno = null; return; }      // no se toca hasta que el servidor diga quién es
    await olvidarTodo();
  }
  if (!provisional || guardado === realId) {
    dueno = realId;
    if (!guardado || guardado !== realId) await escribirDisco('__dueno', realId);
  }
}

/** Borra todo lo guardado (persona de baja, sin identidad, otra persona). */
export async function olvidarTodo() {
  MEM.clear();
  if (!idb) idb = abrirDisco();
  await vaciarDisco();
  dueno = null;
  try { if (self.caches) await caches.delete('ro-pagina-v1'); } catch { /* sin caché de la página */ }   // la de sw.js
}

/** Tras un POST (salvo el rastro de navegar): acciones, avisos, decisiones, IA, Ajustes… se vuelven a pedir. */
export function olvidarTrasCambio(rutaPost = '') {
  if (SIN_CAMBIO_DE_DATOS.test(String(rutaPost).replace(/^\/?(api\/)?/, ''))) return;
  for (const k of [...MEM.keys()]) if (!QUEDAN_TRAS_POST.test(k.split('|').slice(2).join('|'))) { MEM.delete(k); borrarDisco(k); }
}

/** alCambiarDato(fn) → fn(ruta) cuando lo refrescado detrás trae algo distinto de lo que se pintó. */
export function alCambiarDato(fn) { oyentes.add(fn); return () => oyentes.delete(fn); }

/** ¿Se guarda esta ruta? (memoria siempre; disco solo para la persona real y sin nada sensible). */
export const conMemoria = ruta => RUTAS_CON_MEMORIA.test(ruta) && !NUNCA_GUARDAR.test(ruta);

function errorDe(r, cuerpo) {
  const e = new Error((cuerpo && cuerpo.error) || `Error ${r.status}`); e.status = r.status; return e;
}

async function bajar(ruta, yo, como, etag) {
  const h = cabeceras(yo, como);
  delete h['Content-Type'];
  if (etag) h['If-None-Match'] = etag;
  const r = await fetch(`api/${ruta}`, { headers: h, cache: 'no-store' });
  if (r.status === 304) return { noCambia: true };
  const texto = await r.text();
  if (!r.ok) { let c = {}; try { c = JSON.parse(texto); } catch { /* sin cuerpo */ } throw errorDe(r, c); }
  return { texto, etag: r.headers.get('ETag'), hora: Date.now() };
}

function guardar(k, e, yo, como) {
  MEM.set(k, e);
  if (disco(yo, como) && e.texto.length <= MAX_TEXTO_DISCO && !SOLO_MEMORIA.test(k.split('|').slice(2).join('|'))) escribirDisco(k, e);
}

const enVuelo = new Map();
function comprobar(k, ruta, yo, como, e) {
  if (enVuelo.has(k) || Date.now() - (e.comprobado || 0) < COMPROBAR_CADA_MS) return;
  const p = bajar(ruta, yo, como, e.etag).then(n => {
    if (n.noCambia) { e.comprobado = Date.now(); return; }
    n.comprobado = Date.now();
    const sinHora = t => t.replace(/"hora": ?"[^"]*"/g, '');   // la hora de la respuesta no es un cambio del dato
    const cambia = sinHora(n.texto) !== sinHora(e.texto);
    guardar(k, n, yo, como);
    if (cambia) oyentes.forEach(fn => { try { fn(ruta); } catch { /* el oyente no rompe nada */ } });
  }).catch(err => {
    if (err.status === 401) { olvidarTodo(); oyentes.forEach(fn => fn(ruta)); return; }
    if ([403, 404].includes(err.status)) { MEM.delete(k); borrarDisco(k); oyentes.forEach(fn => fn(ruta)); }
    // sin red: se queda lo guardado
  }).finally(() => enVuelo.delete(k));
  enVuelo.set(k, p);
}

/**
 * pedirDato(ruta, { yo, como }) → objeto JSON. Con memoria: lo guardado al momento (y comprueba detrás). Sin memoria
 * (ruta no permitida o nada guardado): al servidor. Lanza Error con .status si el servidor dice que no.
 * info (opcional): se le pone { guardado: true, hora } si se ha servido de lo guardado.
 */
export async function pedirDato(ruta, { yo, como, info } = {}) {
  ruta = ruta.replace(/^\/?(api\/)?/, '');
  if (!conMemoria(ruta)) {
    const n = await bajar(ruta, yo, como, null);
    return JSON.parse(n.texto);
  }
  const k = claveDe(ruta, yo, como);
  let e = MEM.get(k);
  if (!e && disco(yo, como)) { e = await leerDisco(k); if (e) { e.comprobado = 0; MEM.set(k, e); } }
  if (e) {
    comprobar(k, ruta, yo, como, e);
    if (info) Object.assign(info, { guardado: Date.now() - e.hora > COMPROBAR_CADA_MS, hora: e.hora });
    return JSON.parse(e.texto);
  }
  if (enVuelo.has(k)) await enVuelo.get(k).catch(() => {});
  e = MEM.get(k);
  if (e) return JSON.parse(e.texto);
  const p = bajar(ruta, yo, como, null);
  enVuelo.set(k, p.catch(() => {}));
  try {
    const n = await p;
    n.comprobado = Date.now();
    guardar(k, n, yo, como);
    return JSON.parse(n.texto);
  } finally { enVuelo.delete(k); }
}

/**
 * Sesión precargada (causa 7): index.html servido por servir.py trae <link id="precarga-sesion" rel="preload" as="fetch">
 * con la misma dirección; este fetch la recoge sin un segundo viaje. Solo sin «ver como» (la precarga es de la persona real).
 */
export function precargaSesion(como, yo) {
  const l = document.getElementById('precarga-sesion');
  if (!l || como) return null;
  const href = l.getAttribute('href');
  // Solo si es de la misma persona que entra (la página puede venir guardada por sw.js de otra entrada).
  const suyo = new URLSearchParams(href.split('?')[1] || '').get('yo');
  return (suyo || null) === (yo || null) ? href : null;
}

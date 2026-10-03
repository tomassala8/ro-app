// modulos/paneles.js · «Paneles de herramientas» (carril N1, 2-oct noche · diseño N6).
//
// Petición de Tomás: «que todos los dashboards de todas las herramientas se puedan reproducir desde dentro, que se
// puedan actualizar los periodos, que se pueda ver toda la info con claridad». Este módulo reúne las vistas estándar
// que el equipo mira en cada herramienta y que no tenían casa en otro módulo, por cliente y con periodo común:
//   · Meta Ads (administrador de anuncios: campañas, conjuntos y anuncios con sus columnas)
//   · GoHighLevel (panel de la subcuenta: oportunidades por embudo y etapa, citas por estado, contactos y conversaciones)
//   · Google Analytics 4 (informes estándar: resumen, adquisición, interacción, eventos clave, páginas, tecnología y lugar)
//   · Search Console (rendimiento, indexación y experiencia)
//   · Metricool (analítica por red)
//   · Empresa (dirección y operaciones): Zoho Desk (tickets y plazos) y Zadarma (llamadas)
//   · «Dónde está cada panel»: el mapa de paridad (herramienta → pantalla de la app)
// Rutas: #/paneles/<cliente>/<herramienta>/<vista> · #/paneles/empresa/<desk|zadarma> · #/paneles/mapa
//
// Datos: data/paneles/ (fuentes_paneles/generar_paneles.py, solo lectura). Un fichero por cliente y herramienta con
// {filas:[{cliente_id,…}]}: servir.py solo lo manda si la persona ve ese cliente y quita gasto/coste/cpl/inversión a quien
// no ve la inversión de ESE cliente.
// Periodo (N6): el COMÚN de la carcasa (usa_periodo + ctx.periodo + ctx.alCambiarPeriodo). Sin selector propio.
// Diseño (N6, auditoría 30): sin hoja propia; solo tokens y componentes comunes; gráficos con grafico().
import {
  h, fmt, icono, tile, tiles, panel, pestanas, chipsFiltro, selectorCliente, vacio, vacioLinea, frescura, tablaApilable, avisoParcial,
  chipEstado, variacion, grafico, embudoBarras, colorCifra, sumarSerie, serieDelPeriodo, fechaCorta,
  rangoPeriodo, hoyMadrid, periodoCompleto, leerPeriodo, sumarDias, menuMas,
} from '../componentes.js';
import { consejoCompacto } from './_trabajo.js';

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

const DIR = ['direccion', 'finanzas_direccion', 'operaciones', 'proyectos'];
const HERR = {
  meta: { texto: 'Meta Ads', icono: 'megafono', fuente: 'Meta', puestos: [...DIR, 'jefa_publicidad', 'account', 'trafficker', 'tecnico_altas'] },
  ghl: { texto: 'GoHighLevel', icono: 'base', fuente: 'GoHighLevel', puestos: [...DIR, 'jefa_crm', 'especialista_ghl', 'account', 'trafficker', 'tecnico_altas', 'jefa_publicidad'] },
  ga4: { texto: 'Analytics', icono: 'grafico', fuente: 'Analytics', puestos: [...DIR, 'jefa_seo', 'seo', 'web', 'account', 'trafficker', 'jefa_publicidad', 'ficha_google'] },
  gsc: { texto: 'Search Console', icono: 'buscar', fuente: 'Search Console', puestos: [...DIR, 'jefa_seo', 'seo', 'web', 'account', 'ficha_google'] },
  mc: { texto: 'Metricool', icono: 'heart', fuente: 'Metricool', puestos: [...DIR, 'redes', 'account', 'jefa_seo'] },
};
// orden por frecuencia de uso según el puesto (lo que más visita, primero)
const ORDEN = {
  trafficker: ['meta', 'ghl', 'ga4'], jefa_publicidad: ['meta', 'ghl', 'ga4'], especialista_ghl: ['ghl'], jefa_crm: ['ghl'],
  seo: ['gsc', 'ga4'], jefa_seo: ['gsc', 'ga4', 'mc'], web: ['ga4', 'gsc'], ficha_google: ['gsc', 'ga4'], redes: ['mc'],
  account: ['meta', 'ghl', 'ga4', 'gsc', 'mc'], tecnico_altas: ['meta', 'ghl'],
};
const EMPRESA = ['direccion', 'operaciones', 'proyectos'];

// ------------------------------------------------------------------------------------------- utilidades
// cifras: el formateador común (punto de miles siempre y «−» tipográfico)
const n0 = x => fmt.num(x);
const n1 = x => (x === null || x === undefined ? '—' : Number.isInteger(Math.round(x * 10) / 10) ? fmt.num(x) : fmt.num(x, 1));
const pc = x => (x === null || x === undefined || Number.isNaN(x) ? '—' : fmt.pct(x * 100, x * 100 < 10 ? 1 : 0));
const eur = x => (x === null || x === undefined ? '—' : fmt.eur(x, x < 100 && x % 1 ? 2 : 0));
const dur = s => { if (s === null || s === undefined || Number.isNaN(s)) return '—'; s = Math.round(s); const m = Math.floor(s / 60); return m ? `${m} min ${String(s % 60).padStart(2, '0')} s` : `${s} s`; };
const div = (a, b) => (b ? a / b : null);
const veHerr = (ctx, k) => ctx.persona.puestos.some(p => HERR[k].puestos.includes(p));
const esEmpresa = ctx => ctx.persona.puestos.some(p => EMPRESA.includes(p));
const PRESET = new Set(['hoy', 'ayer', '7d', '30d', 'mes', 'mes_ant', 'trim', 'anio']);
const claveComp = P => (P.comparar === 'anio_ant' ? 'c' : P.comparar === 'no' ? null : 'b');
/** «el periodo anterior» / «el año anterior»: corto, porque las fechas exactas ya están en la barra del periodo. */
const ante = P => (P.comparar === 'anio_ant' ? 'el año anterior' : 'el periodo anterior');
const frente = P => (P.comparar === 'anio_ant' ? 'frente al año anterior' : 'frente al periodo anterior');
const pila = (...hijos) => h('div', { class: 'pila', style: { gap: 'var(--s-4)' } }, ...hijos);
const enCuerpo = (...hijos) => h('div', { class: 'cuerpo' }, ...hijos);
const diasEntre = (a, b) => Math.round((Date.parse(b) - Date.parse(a)) / 864e5);
/** tabla común con clave en todas las columnas (tablaDensa la necesita para ordenar y paginar). */
const tabla = o => tablaApilable({ ...o, columnas: o.columnas.map((c, i) => ({ clave: `c${i}`, ...c })) });
/** explicaciones plegadas al pie (guía 3.6): «De dónde sale», «Qué se ve aquí»… */
const pliegue = (titulo, texto) => h('details', { class: 'que-es' }, h('summary', {}, titulo), h('p', { class: 'sub' }, texto));

/** tarjeta: sin dato → gris y «Sin dato» pequeño (nunca un «—» gigante). */
function tarjeta(o) {
  if (o.valor === null || o.valor === undefined || o.valor === '') return tile({ ...o, valor: h('small', {}, 'Sin dato'), estado: 'gris', comparacion: null, alPulsar: o.alPulsar, activo: o.activo });
  return tile(o);
}
function compTile(a, b, P, mejorSi) {
  if (!P.comp || a === null || a === undefined) return null;
  if (b === null || b === undefined) return { texto: `sin dato en ${ante(P)}` };
  if (!b && a) return { texto: `nuevo ${frente(P)}` };
  return { delta: variacion(a, b), pct: true, texto: frente(P), mejorSi };
}
const COLOR_SENTIDO = { bien: 'var(--good-ink)', mal: 'var(--bad-ink)', igual: 'var(--dim)' };
function delta(a, b, mejorSi = 'alto') {
  if (a === null || a === undefined || b === null || b === undefined) return null;
  const caja = (s, txt, title) => h('span', { title, style: { display: 'block', font: 'var(--t-meta)', fontWeight: 600, color: COLOR_SENTIDO[s], whiteSpace: 'nowrap' } }, txt);
  if (!b) return a ? caja('igual', 'nuevo', 'Antes no había') : null;
  const v = variacion(a, b);
  if (v === null) return null;
  // mejorSi 'neutro': subir o bajar no es bueno ni malo (reparto por persona o canal): sin color, rojo con cuentagotas
  const s = v === 0 || mejorSi === 'neutro' ? 'igual' : (v > 0) === (mejorSi !== 'bajo') ? 'bien' : 'mal';
  return caja(s, `${v > 0 ? '▲' : v < 0 ? '▼' : '='} ${fmt.num(Math.abs(v), Math.abs(v) < 10 ? 1 : 0)} %`, `Antes: ${fmt.num(b, b % 1 ? 1 : 0)}`);
}
function celda(a, b, f = n0, mejorSi) {
  return h('span', {}, a === null || a === undefined ? '—' : f(a), b !== undefined ? delta(a, b, mejorSi) : null);
}

/** gráfico del periodo (azul) con la comparación (gris discontinuo), con el motor común grafico(). */
function graficoDoble({ actual, comp, formato = n0, P, titulo }) {
  if (!actual?.length) return vacioLinea('Sin días en este periodo: elige uno más largo.', { icono: 'grafico' });
  if (actual.length === 1) return vacioLinea(`Un solo día: ${formato(actual[0].y)}${comp?.length ? ` · ${ante(P)}: ${formato(comp[0].y)}` : ''}. El gráfico diario sale con 2 días o más.`, { icono: 'grafico' });
  const series = [{ nombre: P?.rango || 'Periodo', y: actual.map(p => p.y) }];
  if (comp?.length) series.push({ nombre: P?.comp?.rango || 'Comparación', y: actual.map((_, i) => comp[i]?.y ?? null), ant: true });
  return grafico({ titulo, x: actual.map(p => p.x), series, formato, alto: 200 });
}

function tablaComp({ filas, columnas, P, vacioTxt, primera = 'Nombre', etiqueta }) {
  if (!filas?.length) return enCuerpo(vacioLinea(`${vacioTxt || 'Nada en este periodo'}: la herramienta no devuelve filas para estas fechas.`, { icono: 'vacio' }));
  return tablaApilable({
    porPagina: window.matchMedia?.('(max-width: 640px)').matches ? 10 : 15,
    columnas: [{ clave: 'nombre', titulo: primera, principal: true, celda: r => h('span', { style: { display: 'block', minWidth: 'min(200px, 100%)', overflowWrap: 'anywhere' } }, r.nombre) },
      ...columnas.map((c, n) => ({ clave: `c${n}`, valor: r => r.a?.[c.i] ?? null, titulo: c.titulo, num: true, celda: r => celda(r.a?.[c.i], P.comp && r.c !== undefined ? r.c?.[c.i] ?? null : undefined, c.f || n0, c.mejorSi) }))],
    filas, etiquetaFila: etiqueta,
  });
}

/** Con «A medida» las tablas de la herramienta no existen (vienen calculadas para los periodos fijos): se dice en una línea. */
function avisoPeriodoTablas() {
  return vacioLinea('Con «A medida», las cifras de arriba y el gráfico salen exactos día a día, pero las tablas de la herramienta solo existen para los periodos fijos (7 días, 30 días, este mes…). Elige uno para verlas.', { icono: 'cal' });
}

// =========================================================================================== Analytics
const GA_VISTAS = [
  { id: 'resumen', texto: 'Resumen', icono: 'res' }, { id: 'adquisicion', texto: 'Adquisición', icono: 'target' },
  { id: 'interaccion', texto: 'Interacción', icono: 'zap' }, { id: 'eventos', texto: 'Eventos clave', icono: 'flag' },
  { id: 'paginas', texto: 'Páginas', icono: 'doc' }, { id: 'tecnologia', texto: 'Tecnología y lugar', icono: 'mundo_web' },
];
const GA_DIA = { usuarios: 0, nuevos: 1, sesiones: 2, con_interaccion: 3, eventos_clave: 4, vistas: 5, eventos: 6, tiempo: 7 };
const GA_TOT = { usuarios: 0, nuevos: 1, sesiones: 2, con_interaccion: 3, tasa: 4, duracion: 5, vistas: 6, eventos_clave: 7, eventos: 8, rebote: 9 };

function gaTotales(f, P) {
  const k = claveComp(P);
  if (PRESET.has(P.id) && f.periodos?.[P.id]?.tot?.a) {
    const t = f.periodos[P.id].tot;
    const g = (r, x) => (r ? r[GA_TOT[x]] : null);
    const mk = r => r && { usuarios: g(r, 'usuarios'), nuevos: g(r, 'nuevos'), sesiones: g(r, 'sesiones'), con_interaccion: g(r, 'con_interaccion'), tasa: g(r, 'tasa'),
      duracion: g(r, 'duracion'), vistas: g(r, 'vistas'), eventos_clave: g(r, 'eventos_clave'), eventos: g(r, 'eventos'), rebote: g(r, 'rebote') };
    return { a: mk(t.a), b: k ? mk(t[k]) || (k ? {} : null) : null, exacto: true };
  }
  const suma = r => { const s = sumarSerie(f.serie, r); if (!s) return null; return { usuarios: null, nuevos: s[1], sesiones: s[2], con_interaccion: s[3], tasa: div(s[3], s[2]), duracion: div(s[7], s[2]), vistas: s[5], eventos_clave: s[4], eventos: s[6], rebote: s[2] ? 1 - s[3] / s[2] : null }; };
  return { a: suma(P), b: P.comp ? suma(P.comp) : null, exacto: false };
}

function pintarGA(z, f, P, vista, ctx, estado) {
  const T = gaTotales(f, P);
  const a = T.a || {}, b = T.b || {};
  const metricas = [
    ['usuarios', 'Usuarios activos', 'users', n0], ['nuevos', 'Usuarios nuevos', 'persona', n0], ['sesiones', 'Sesiones', 'grafico', n0],
    ['eventos_clave', 'Eventos clave', 'flag', n1], ['tasa', 'Tasa de interacción', 'zap', pc], ['duracion', 'Duración media de la sesión', 'clock', dur],
    ['vistas', 'Vistas', 'ojo', n0], ['rebote', 'Porcentaje de rebote', 'baja', pc],
  ];
  const sel = estado.gaMet || 'sesiones';
  const tl = metricas.map(([k, et, ic, f_]) => tarjeta({
    icono: ic, etiqueta: et, valor: a[k] === null || a[k] === undefined ? null : f_(a[k]), activo: ['usuarios', 'nuevos', 'sesiones', 'eventos_clave', 'vistas'].includes(k) ? sel === k : undefined,
    alPulsar: ['usuarios', 'nuevos', 'sesiones', 'eventos_clave', 'vistas'].includes(k) ? () => { estado.gaMet = k; estado.repintar(); } : null,
    comparacion: compTile(a[k], b[k], P, k === 'rebote' ? 'bajo' : 'alto'),
    contexto: k === 'usuarios' && !T.exacto && P.id === 'medida' ? 'Con «A medida» los usuarios únicos no se pueden sumar por días' : null,
  }));
  if (metricas.every(([k]) => a[k] === null || a[k] === undefined)) {
    const ult = ultimoDato('ga4', f);
    z.append(vacioLinea(ult && ult < P.desde
      ? `Analytics no tiene datos de esta web desde el ${fechaCorta(ult)}: el periodo de arriba no cambia nada aquí hasta que vuelva a medir.`
      : 'Analytics no devuelve datos de esta web en este periodo (ni por días ni en los informes).', { icono: 'grafico', quien: 'Web' }));
    return;
  }
  if (vista === 'resumen') {
    z.append(tiles(tl));
    const idx = GA_DIA[sel];
    z.append(panel({ titulo: `${metricas.find(m => m[0] === sel)[1]} por día`, icono: 'grafico', sub: 'Pulsa una tarjeta de arriba para cambiar la línea' },
      enCuerpo(graficoDoble({ actual: serieDelPeriodo(f.serie, P, idx), comp: P.comp ? serieDelPeriodo(f.serie, P.comp, idx) : null, P }))));
    // canales por día del periodo (sesiones): tabla resumen a partir de la serie por canal (sirve también con «A medida»)
    const filas = Object.entries(f.serie_canal || {}).map(([canal, s]) => ({ nombre: canal, a: sumarSerie(s, P), c: P.comp ? sumarSerie(s, P.comp) || [0, 0, 0, 0] : undefined }))
      .filter(r => r.a && r.a[0]).sort((x, y) => y.a[0] - x.a[0]);
    z.append(panel({ titulo: 'Sesiones por canal', icono: 'target', sub: 'El informe «Adquisición de tráfico» de Analytics, resumido' },
      tablaComp({ filas, P, primera: 'Canal', columnas: [{ titulo: 'Sesiones', i: 0 }, { titulo: 'Con interacción', i: 1 }, { titulo: 'Eventos clave', i: 2, f: n1 }, { titulo: 'Usuarios nuevos', i: 3 }] })));
    return;
  }
  const per = PRESET.has(P.id) ? f.periodos?.[P.id] : null;
  if (!per) { z.append(avisoPeriodoTablas(P)); return; }
  const k = claveComp(P);
  const T_ = (t, cols, primera, titulo, ic, sub) => {
    const filas = (per[t] || []).map(([nombre, A, B, Cc]) => ({ nombre, a: A, c: k ? (k === 'b' ? B : Cc) : undefined }));
    return panel({ titulo, icono: ic, sub }, tablaComp({ filas, P, primera, columnas: cols }));
  };
  if (vista === 'adquisicion') {
    z.append(tiles(tl.slice(0, 4)));
    z.append(T_('canales', [{ titulo: 'Usuarios', i: 0 }, { titulo: 'Sesiones', i: 1 }, { titulo: 'Con interacción', i: 2 }, { titulo: 'Eventos clave', i: 3, f: n1 }, { titulo: 'Duración media', i: 4, f: dur }], 'Canal', 'Adquisición de tráfico · canal de la sesión', 'target'),
      h('div', { class: 'rejilla' },
        T_('fuentes', [{ titulo: 'Sesiones', i: 1 }, { titulo: 'Con interacción', i: 2 }, { titulo: 'Eventos clave', i: 3, f: n1 }], 'Fuente / medio', 'Fuente y medio de la sesión', 'link'),
        T_('primer_canal', [{ titulo: 'Usuarios nuevos', i: 0 }, { titulo: 'Usuarios', i: 1 }, { titulo: 'Eventos clave', i: 2, f: n1 }], 'Primer canal', 'Adquisición de usuarios · primer canal', 'persona')),
      T_('campanas', [{ titulo: 'Sesiones', i: 0 }, { titulo: 'Con interacción', i: 1 }, { titulo: 'Eventos clave', i: 2, f: n1 }], 'Campaña', 'Campañas (etiquetas de la URL)', 'megafono'));
  } else if (vista === 'interaccion') {
    z.append(tiles([tl[4], tl[5], tl[6], tl[7]]));
    z.append(T_('eventos', [{ titulo: 'Veces', i: 0 }, { titulo: 'Usuarios', i: 1 }, { titulo: 'Eventos clave', i: 2, f: n1 }], 'Evento', 'Eventos', 'zap', 'Lo que se hace en la web: vistas, clics, envíos de formulario, llamadas'));
  } else if (vista === 'eventos') {
    z.append(tiles([tl[3], tl[2]]));
    const ev = (per.eventos || []).filter(r => (r[1]?.[2] || 0) > 0 || (r[2]?.[2] || 0) > 0);
    z.append(panel({ titulo: 'Eventos clave (conversiones)', icono: 'flag', sub: 'Los eventos marcados como clave en Analytics: formularios, llamadas, WhatsApp…' },
      tablaComp({ filas: ev.map(([nombre, A, B, Cc]) => ({ nombre, a: A ? [A[2], A[1]] : null, c: k ? ((k === 'b' ? B : Cc) ? [(k === 'b' ? B : Cc)[2], (k === 'b' ? B : Cc)[1]] : null) : undefined })),
        P, primera: 'Evento clave', vacioTxt: 'Ningún evento clave en este periodo', columnas: [{ titulo: 'Eventos clave', i: 0, f: n1 }, { titulo: 'Usuarios', i: 1 }] })),
      T_('canales', [{ titulo: 'Eventos clave', i: 3, f: n1 }, { titulo: 'Sesiones', i: 1 }], 'Canal', 'Eventos clave por canal', 'target'));
  } else if (vista === 'paginas') {
    z.append(T_('paginas', [{ titulo: 'Vistas', i: 0 }, { titulo: 'Usuarios', i: 1 }, { titulo: 'Tiempo de interacción', i: 2, f: s => dur(s) }, { titulo: 'Eventos clave', i: 3, f: n1 }], 'Página', 'Páginas y pantallas', 'doc', 'Sin parámetros de la URL'),
      T_('destino', [{ titulo: 'Sesiones', i: 0 }, { titulo: 'Usuarios', i: 1 }, { titulo: 'Con interacción', i: 2 }, { titulo: 'Eventos clave', i: 3, f: n1 }], 'Página de destino', 'Páginas de destino (por donde se entra)', 'flecha'));
  } else if (vista === 'tecnologia') {
    z.append(h('div', { class: 'rejilla' },
      T_('dispositivos', [{ titulo: 'Usuarios', i: 0 }, { titulo: 'Sesiones', i: 1 }, { titulo: 'Eventos clave', i: 3, f: n1 }], 'Dispositivo', 'Dispositivo', 'medidor'),
      T_('paises', [{ titulo: 'Usuarios', i: 0 }, { titulo: 'Sesiones', i: 1 }, { titulo: 'Eventos clave', i: 2, f: n1 }], 'País', 'País', 'mundo_web')),
    T_('ciudades', [{ titulo: 'Usuarios', i: 0 }, { titulo: 'Sesiones', i: 1 }, { titulo: 'Eventos clave', i: 2, f: n1 }], 'Ciudad', 'Ciudad', 'pin'));
  }
}

// =========================================================================================== Search Console
const GSC_VISTAS = [{ id: 'rendimiento', texto: 'Rendimiento', icono: 'grafico' }, { id: 'indexacion', texto: 'Indexación', icono: 'capas' }, { id: 'experiencia', texto: 'Experiencia', icono: 'medidor' }];

function gscTot(serie, r) {
  if (!serie || !r) return null;
  let cl = 0, im = 0, pos = 0, dias = 0;
  for (const [d, v] of Object.entries(serie)) { if (d < r.desde || d > r.hasta) continue; cl += v[0]; im += v[1]; pos += (v[2] || 0) * v[1]; dias++; }
  return dias ? { clics: cl, impresiones: im, ctr: div(cl, im), posicion: im ? pos / im : null } : null;
}

function pintarGSC(z, f, P, vista, ctx, estado) {
  if (vista === 'indexacion') return pintarIndexacion(z, f);
  if (vista === 'experiencia') return pintarExperiencia(z, f);
  if (!f.serie) { z.append(vacio({ icono: 'buscar', titulo: 'Sin datos de rendimiento', texto: 'Search Console no devuelve datos de este sitio.' })); return; }
  const hasta = f.hasta;
  const Pc = { ...P, hasta: P.hasta > hasta ? hasta : P.hasta };
  const corte = P.hasta > hasta ? diasEntre(P.desde, hasta) : null;
  const comp = P.comp ? { ...P.comp, hasta: corte !== null && corte >= 0 ? (() => { const r = rangoPeriodo('medida', { desde: P.comp.desde, hasta: P.comp.hasta }); return r.hasta; })() : P.comp.hasta } : null;
  const a = gscTot(f.serie, Pc) || {}, b = comp ? gscTot(f.serie, comp) || {} : {};
  const sel = estado.gscMet || 'clics';
  const met = [['clics', 'Clics', 'flecha', n0, 0], ['impresiones', 'Impresiones', 'ojo', n0, 1], ['ctr', 'CTR (clics ÷ impresiones)', 'target', pc, null], ['posicion', 'Posición media', 'sube', n1, null]];
  z.append(tiles(met.map(([k, et, ic, fm, idx]) => tarjeta({
    icono: ic, etiqueta: et, valor: a[k] === null || a[k] === undefined ? null : fm(a[k]), activo: idx !== null ? sel === k : undefined,
    alPulsar: idx !== null ? () => { estado.gscMet = k; estado.repintar(); } : null,
    comparacion: compTile(a[k], b[k], P, k === 'posicion' ? 'bajo' : 'alto'),
    contexto: k === 'posicion' ? 'Más baja es mejor (1 = primer resultado)' : null,
  }))));
  if (P.hasta > hasta || P.id === 'hoy' || P.id === 'ayer') z.append(vacioLinea(`Search Console va 2-3 días por detrás: hay datos hasta el ${fechaCorta(hasta, true)} (datos definitivos, como en Looker y el Informe del cliente).`, { icono: 'clock' }));
  const idx = sel === 'impresiones' ? 1 : 0;
  z.append(panel({ titulo: `${sel === 'impresiones' ? 'Impresiones' : 'Clics'} por día`, icono: 'grafico', sub: 'Pulsa «Clics» o «Impresiones» para cambiar la línea' },
    enCuerpo(graficoDoble({ actual: serieDelPeriodo(f.serie, Pc, idx), comp: P.comp ? serieDelPeriodo(f.serie, P.comp, idx).slice(0, serieDelPeriodo(f.serie, Pc, idx).length) : null, P }))));
  const per = PRESET.has(P.id) ? f.periodos?.[P.id] : null;
  if (!per) { z.append(PRESET.has(P.id) ? vacioLinea('Hoy y ayer todavía no tienen datos en Search Console: elige 7 días o más.', { icono: 'clock' }) : avisoPeriodoTablas(P)); return; }
  const k = claveComp(P);
  const fila = ([nombre, A, B, Cc]) => {
    const conv = x => (x ? [x[0], x[1], x[1] ? x[0] / x[1] : null, x[2]] : null);
    return { nombre, a: conv(A), c: k ? conv(k === 'b' ? B : Cc) : undefined };
  };
  const cols = [{ titulo: 'Clics', i: 0 }, { titulo: 'Impresiones', i: 1 }, { titulo: 'CTR', i: 2, f: pc }, { titulo: 'Posición', i: 3, f: n1, mejorSi: 'bajo' }];
  const sinAnio = t => (k === 'c' && !['consultas', 'paginas'].includes(t));
  const T_ = (t, primera, titulo, ic) => panel({ titulo, icono: ic, sub: sinAnio(t) ? 'Sin comparación con el año anterior en esta tabla' : null },
    tablaComp({ filas: (per[t] || []).map(fila).map(r => (sinAnio(t) ? { ...r, c: undefined } : r)), P: sinAnio(t) ? { ...P, comp: null } : P, primera, columnas: cols }));
  z.append(pestanas({
    etiqueta: 'Tablas de rendimiento', clave: 'pp.gsc.tabla', pestanas: [
      { id: 'consultas', texto: 'Consultas', icono: 'buscar', cuenta: per.consultas?.length }, { id: 'paginas', texto: 'Páginas', icono: 'doc', cuenta: per.paginas?.length },
      { id: 'paises', texto: 'Países', icono: 'mundo_web' }, { id: 'dispositivos', texto: 'Dispositivos', icono: 'medidor' }, { id: 'apariencia', texto: 'Aparición en la búsqueda', icono: 'star' }],
    pintar: (id, c) => c.replaceChildren(T_(id, { consultas: 'Consulta', paginas: 'Página', paises: 'País', dispositivos: 'Dispositivo', apariencia: 'Tipo de resultado' }[id],
      { consultas: 'Consultas principales', paginas: 'Páginas principales', paises: 'Países', dispositivos: 'Dispositivos', apariencia: 'Aparición en la búsqueda' }[id],
      { consultas: 'buscar', paginas: 'doc', paises: 'mundo_web', dispositivos: 'medidor', apariencia: 'star' }[id])),
  }));
}

const COBERTURA_OK = /indexada|indexed/i;
function pintarIndexacion(z, f) {
  const ix = f.indexacion;
  if (!ix) { z.append(vacio({ icono: 'capas', titulo: 'Sin lectura de indexación', texto: 'Este sitio no tiene Search Console emparejado.', quien: 'SEO' })); return; }
  const ins = (ix.inspeccion || []).filter(x => !x._error);
  const ok = ins.filter(x => x.veredicto === 'PASS').length;
  const malas = ins.filter(x => x.veredicto && x.veredicto !== 'PASS');
  const urls = (ix.sitemaps || []).filter(s => !s.es_indice).reduce((a, s) => a + s.urls, 0) || (ix.sitemaps || []).reduce((a, s) => a + s.urls, 0);
  const errSm = (ix.sitemaps || []).reduce((a, s) => a + s.errores, 0);
  const viejo = ins.filter(x => x.rastreo && diasEntre(x.rastreo, hoyMadrid()) > 60).length;
  z.append(tiles([
    tarjeta({ icono: 'check', etiqueta: 'Páginas principales indexadas', valor: ins.length ? `${ok} de ${ins.length}` : null, estado: !ins.length ? 'gris' : ok === ins.length ? 'verde' : ok >= ins.length - 2 ? 'ambar' : 'rojo', contexto: 'Inspección de URL de las páginas con más clics en 30 días', medible: 'hoy' }),
    tarjeta({ icono: 'capas', etiqueta: 'URL enviadas en sitemaps', valor: (ix.sitemaps || []).length ? n0(urls) : null, contexto: `${(ix.sitemaps || []).length} sitemaps`, medible: 'hoy' }),
    tarjeta({ icono: 'alert', etiqueta: 'Errores en sitemaps', valor: (ix.sitemaps || []).length ? errSm : null, estado: errSm ? 'rojo' : 'verde', contexto: 'Bien solo con 0', medible: 'hoy' }),
    tarjeta({ icono: 'hist', etiqueta: 'Sin rastrear en más de 60 días', valor: ins.length ? viejo : null, estado: !ins.length ? 'gris' : viejo ? 'ambar' : 'verde', contexto: 'De las páginas inspeccionadas', medible: 'hoy' }),
  ]));
  if (malas.length) z.append(avisoParcial(`${malas.length} de las páginas que más clics traen no están indexadas o tienen avisos: ${malas.map(x => x.url.replace(/^https?:\/\/[^/]+/, '')).slice(0, 4).join(', ')}.`, { titulo: 'Para SEO.' }));
  z.append(panel({ titulo: 'Páginas principales · estado en Google', icono: 'capas', sub: `Inspeccionadas el ${fDiaHoraRO(ix.leido)}` },
    tabla({
      porPagina: 0, filas: ins, vacio: { titulo: 'Sin páginas inspeccionadas', texto: 'Search Console no devolvió la inspección (cupo diario o sin permiso).' },
      columnas: [
        { titulo: 'Página', principal: true, celda: r => h('a', { href: r.url, target: '_blank', rel: 'noopener', style: { overflowWrap: 'anywhere' } }, r.url.replace(/^https?:\/\/[^/]+/, '') || '/') },
        { titulo: 'Estado', celda: r => chipEstado(r.veredicto === 'PASS' ? 'verde' : r.veredicto === 'NEUTRAL' ? 'ambar' : r.veredicto ? 'rojo' : 'gris', r.cobertura || r.veredicto || '—') },
        { titulo: 'Último rastreo', celda: r => (r.rastreo ? fechaCorta(r.rastreo, true) : '—') },
        { titulo: 'Canónica', celda: r => (r.canonica_google && r.canonica_usuario && r.canonica_google !== r.canonica_usuario ? chipEstado('ambar', 'Google elige otra') : chipEstado('verde', 'La suya')) },
      ],
    })));
  z.append(panel({ titulo: 'Sitemaps', icono: 'doc' }, tabla({
    porPagina: 0, filas: ix.sitemaps || [], vacio: { titulo: 'Sin sitemaps enviados', texto: 'Ningún sitemap en Search Console: conviene enviar el de la web.' },
    columnas: [
      { titulo: 'Sitemap', principal: true, celda: r => h('span', { style: { overflowWrap: 'anywhere' } }, r.ruta) },
      { titulo: 'URL', num: true, celda: r => n0(r.urls) }, { titulo: 'Enviado', celda: r => fechaCorta(r.enviado, true) }, { titulo: 'Leído por Google', celda: r => fechaCorta(r.leido, true) },
      { titulo: 'Estado', celda: r => chipEstado(r.errores ? 'rojo' : r.avisos ? 'ambar' : 'verde', r.errores ? `${r.errores} errores` : r.avisos ? `${r.avisos} avisos` : 'Correcto') },
    ],
  })));
  z.append(pliegue('Qué se ve aquí', 'La API de Search Console no da el informe completo de «Páginas» (indexadas y no indexadas de toda la web): da los sitemaps y la inspección página a página. Aquí van las 15 páginas que más clics traen; el resto, en Search Console.'));
}

const CWV = [['LARGEST_CONTENTFUL_PAINT_MS', 'Carga del contenido principal', v => `${fmt.num(v / 1000, 1)} s`, 'Bien hasta 2,5 s'],
  ['INTERACTION_TO_NEXT_PAINT', 'Respuesta al tocar o pulsar', v => `${fmt.num(v)} ms`, 'Bien hasta 200 ms'],
  ['CUMULATIVE_LAYOUT_SHIFT_SCORE', 'Estabilidad (que nada salte)', v => fmt.num(v / 100, 2), 'Bien hasta 0,1']];
const CAT = { FAST: ['verde', 'Bien'], AVERAGE: ['ambar', 'Mejorable'], SLOW: ['rojo', 'Mal'] };
function pintarExperiencia(z, f) {
  const e = f.experiencia;
  if (!e || e._error) { z.append(vacio({ icono: 'medidor', titulo: 'Sin medición de experiencia', texto: e?._error === 'sin web' ? 'El cliente no tiene web en la ficha.' : 'PageSpeed no devolvió datos de esta web.', quien: 'Web' })); return; }
  const cupo = ['mobile', 'desktop'].every(k => e[k]?._error === 429);
  if (cupo) { z.append(vacio({ icono: 'key', tono: 'aviso', titulo: 'Falta la clave de PageSpeed', texto: 'Google solo deja unas pocas mediciones al día sin clave y hoy ya se han gastado. Con una clave de API de Google (gratis, 2 minutos) se miden todas las webs cada día.', quien: 'Tomás' })); return; }
  for (const [est, txt, ic] of [['mobile', 'Móvil', 'phone'], ['desktop', 'Ordenador', 'medidor']]) {
    const x = e[est];
    if (!x || x._error) { z.append(panel({ titulo: txt, icono: ic }, enCuerpo(vacioLinea('Sin dato: PageSpeed no respondió para esta versión.', { icono: 'medidor' })))); continue; }
    const nota = x.nota === null || x.nota === undefined ? null : Math.round(x.nota * 100);
    const cards = [tarjeta({ icono: 'medidor', etiqueta: 'Nota de velocidad (laboratorio)', valor: nota, unidad: 'de 100', estado: nota === null ? 'gris' : nota >= 90 ? 'verde' : nota >= 50 ? 'ambar' : 'rojo', contexto: 'Bien desde 90 · mal por debajo de 50', medible: 'hoy' })];
    for (const [k, et, fm, ctxTxt] of CWV) {
      const c = x.campo?.[k];
      cards.push(tarjeta({ icono: 'clock', etiqueta: et, valor: c?.p75 !== undefined && c?.p75 !== null ? fm(c.p75) : null, estado: c ? CAT[c.cat]?.[0] || 'gris' : 'gris',
        contexto: c ? `${CAT[c.cat]?.[1] || '—'} · ${ctxTxt}${x.campo_origen ? ' · dato de todo el dominio' : ''}` : 'Sin tráfico suficiente de Chrome para medirlo', medible: c ? 'hoy' : 'no' }));
    }
    z.append(panel({ titulo: txt, icono: ic, sub: x.campo_global ? `Usuarios reales: ${CAT[x.campo_global]?.[1] || x.campo_global}` : 'Sin datos de usuarios reales: solo laboratorio' }, enCuerpo(tiles(cards))));
  }
  z.append(pliegue('De dónde sale', `Es el informe «Métricas web principales» de Search Console: datos de usuarios reales de Chrome de los últimos 28 días (si la web tiene tráfico suficiente) y la nota de laboratorio de PageSpeed. Se mide la portada. Medido el ${fDiaHoraRO(e.leido)} · ${e.url}`));
}

// =========================================================================================== Meta Ads
const META_VISTAS = [{ id: 'campanas', texto: 'Campañas', icono: 'megafono' }, { id: 'conjuntos', texto: 'Conjuntos de anuncios', icono: 'capas' }, { id: 'anuncios', texto: 'Anuncios', icono: 'star' }];
const ESTADO_META = { ACTIVE: ['verde', 'Activa'], PAUSED: ['gris', 'Pausada'], CAMPAIGN_PAUSED: ['gris', 'Campaña pausada'], ADSET_PAUSED: ['gris', 'Conjunto pausado'], ARCHIVED: ['gris', 'Archivada'], DELETED: ['gris', 'Borrada'], WITH_ISSUES: ['rojo', 'Con problemas'], DISAPPROVED: ['rojo', 'Rechazado'], PENDING_REVIEW: ['ambar', 'En revisión'], IN_PROCESS: ['ambar', 'En proceso'] };

function metaSuma(f, r, ids) {
  if (!r) return null;
  const out = {};
  for (const [cid, s] of Object.entries(f.serie || {})) {
    if (ids && !ids.has(cid)) continue;
    const v = sumarSerie(s, r);
    const g = f.gasto_serie ? sumarSerie(f.gasto_serie[cid] || {}, r) : null;
    if (!v && !g) continue;
    out[cid] = { impresiones: v?.[0] || 0, clics: v?.[1] || 0, clics_enlace: v?.[2] || 0, leads: v?.[3] || 0, gasto: g ?? undefined };
  }
  return out;
}
const sumar = o => Object.values(o || {}).reduce((t, x) => { for (const k of ['impresiones', 'clics', 'clics_enlace', 'leads', 'gasto']) if (x[k] !== undefined) t[k] = (t[k] || 0) + x[k]; return t; }, {});

function pintarMeta(z, f, P, vista, ctx, estado) {
  const verDinero = !!f.gasto_serie;
  const exacto = PRESET.has(P.id) ? f.periodos?.[`${P.desde}|${P.hasta}`] : null;
  const exactoC = P.comp && P.comparar === 'anterior' && PRESET.has(P.id) ? f.periodos?.[`${P.comp.desde}|${P.comp.hasta}`] : null;
  const a = exacto?.cuenta || sumar(metaSuma(f, P)), b = P.comp ? (exactoC?.cuenta || sumar(metaSuma(f, P.comp))) : {};
  const cpl = x => (x && x.gasto !== undefined && x.leads ? x.gasto / x.leads : null);
  const ctr = x => (x && x.impresiones ? x.clics_enlace / x.impresiones : null);
  const sel = estado.metaMet || (verDinero ? 'gasto' : 'leads');
  const tienda = estado.cli?.tipo_negocio === 'tienda_online';   // Kiosko: fuera del techo de 35 €/lead (D-P-CAP5)
  const cards = [
    verDinero ? tarjeta({ icono: 'euro', etiqueta: 'Importe gastado', valor: a.gasto === undefined ? null : eur(a.gasto), activo: sel === 'gasto', alPulsar: () => { estado.metaMet = 'gasto'; estado.repintar(); }, comparacion: compTile(a.gasto, b.gasto, P) }) : null,
    tarjeta({ icono: 'users', etiqueta: 'Clientes potenciales (leads)', valor: n0(a.leads || 0), activo: sel === 'leads', alPulsar: () => { estado.metaMet = 'leads'; estado.repintar(); }, comparacion: compTile(a.leads || 0, b.leads, P) }),
    verDinero ? tarjeta({ icono: 'target', etiqueta: 'Coste por lead', valor: cpl(a) === null ? null : eur(cpl(a)), estado: tienda ? '' : colorCifra('coste_lead', cpl(a)), comparacion: compTile(cpl(a), cpl(b), P, 'bajo'), contexto: tienda ? 'Tienda online: sin el techo de 35 €' : 'Techo de la casa: 35 € por lead' }) : null,
    tarjeta({ icono: 'ojo', etiqueta: 'Impresiones', valor: n0(a.impresiones || 0), activo: sel === 'impresiones', alPulsar: () => { estado.metaMet = 'impresiones'; estado.repintar(); }, comparacion: compTile(a.impresiones || 0, b.impresiones, P) }),
    tarjeta({ icono: 'persona', etiqueta: 'Alcance', valor: exacto?.cuenta ? n0(exacto.cuenta.alcance) : null, contexto: exacto?.cuenta ? `Frecuencia ${fmt.num(exacto.cuenta.frecuencia, 2)}` : 'Exacto solo en los periodos fijos', comparacion: exactoC?.cuenta ? compTile(exacto?.cuenta?.alcance, exactoC.cuenta.alcance, P) : null }),
    tarjeta({ icono: 'flecha', etiqueta: 'CTR (clics en el enlace)', valor: ctr(a) === null ? null : pc(ctr(a)), comparacion: compTile(ctr(a), ctr(b), P) }),
  ].filter(Boolean);
  z.append(tiles(cards));
  if (!verDinero) z.append(vacioLinea('Tu puesto no ve la inversión de este cliente: aquí van impresiones, clics y leads, sin euros.', { icono: 'candado' }));
  // gráfico diario
  const serieTot = {};
  const fuenteS = sel === 'gasto' ? f.gasto_serie : f.serie;
  const idx = { leads: 3, impresiones: 0 }[sel];
  for (const s of Object.values(fuenteS || {})) for (const [d, v] of Object.entries(s)) serieTot[d] = (serieTot[d] || 0) + (sel === 'gasto' ? v : v[idx]);
  z.append(panel({ titulo: `${{ gasto: 'Importe gastado', leads: 'Leads', impresiones: 'Impresiones' }[sel]} por día`, icono: 'grafico' },
    enCuerpo(graficoDoble({ actual: serieDelPeriodo(serieTot, P), comp: P.comp ? serieDelPeriodo(serieTot, P.comp) : null, formato: sel === 'gasto' ? x => `${fmt.num(x)} €` : n0, P }))));
  // tabla del administrador de anuncios
  const nivel = { campanas: 'campaign', conjuntos: 'adset', anuncios: 'ad' }[vista];
  const meta = { campanas: f.campanas, conjuntos: f.conjuntos, anuncios: f.anuncios }[vista] || {};
  let filas;
  if (vista === 'campanas' && !exacto) {
    const A = metaSuma(f, P) || {}, B = P.comp ? metaSuma(f, P.comp) || {} : {};
    filas = Object.entries(A).map(([id, x]) => ({ id, x, y: B[id] }));
  } else if (exacto) {
    const A = exacto[nivel] || {}, B = exactoC?.[nivel] || {};
    filas = Object.entries(A).map(([id, x]) => ({ id, x, y: P.comp ? B[id] || (exactoC ? null : undefined) : undefined }));
  } else { z.append(avisoPeriodoTablas(P)); return; }
  filas = filas.filter(r => r.x.impresiones || r.x.gasto).map(r => ({ ...r, m: meta[r.id] || {} }));
  const soloActivas = estado.metaActivas ?? false;
  const filtradas = soloActivas ? filas.filter(r => r.m.estado === 'ACTIVE') : filas;
  filtradas.sort((p, q) => (q.x.gasto ?? q.x.impresiones) - (p.x.gasto ?? p.x.impresiones));
  const conComp = !!P.comp && filtradas.some(r => r.y);
  const col = (titulo, fn, fm = n0, mejorSi) => ({ titulo, num: true, valor: r => fn(r.x) ?? null, celda: r => celda(fn(r.x), conComp ? (r.y ? fn(r.y) : null) : undefined, fm, mejorSi) });
  const columnas = [
    { titulo: { campanas: 'Campaña', conjuntos: 'Conjunto', anuncios: 'Anuncio' }[vista], principal: true, valor: r => r.m.nombre || '', celda: r => h('span', { style: { display: 'block', minWidth: 'min(220px, 100%)' } }, h('span', { style: { font: 'var(--t-h3)', overflowWrap: 'anywhere' } }, r.m.nombre || 'Sin nombre (borrada)'),
      vista !== 'campanas' && r.m.campana && f.campanas?.[r.m.campana] ? h('span', { style: { display: 'block', font: 'var(--t-meta)', color: 'var(--dim)' } }, f.campanas[r.m.campana].nombre) : null) },
    { titulo: 'Entrega', celda: r => { const e = ESTADO_META[r.m.estado] || ['gris', r.m.estado ? r.m.estado.toLowerCase() : 'sin dato']; return chipEstado(e[0], e[1]); } },
    verDinero ? col('Importe gastado', x => x.gasto, eur) : null,
    col('Leads', x => x.leads), verDinero ? col('Coste por lead', x => cpl(x), eur, 'bajo') : null,
    col('Impresiones', x => x.impresiones),
    exacto ? col('Alcance', x => x.alcance) : null, exacto ? col('Frecuencia', x => x.frecuencia, v => fmt.num(v, 2), 'bajo') : null,
    col('Clics en el enlace', x => x.clics_enlace), col('CTR', x => ctr(x), pc),
    verDinero && vista !== 'anuncios' ? { titulo: 'Presupuesto', num: true, celda: r => (r.m.inversion_diaria ? `${eur(r.m.inversion_diaria)}/día` : r.m.inversion_total ? `${eur(r.m.inversion_total)} total` : '—') } : null,
  ].filter(Boolean);
  const activas = filas.filter(r => r.m.estado === 'ACTIVE').length;
  z.append(panel({ titulo: { campanas: 'Campañas', conjuntos: 'Conjuntos de anuncios', anuncios: 'Anuncios' }[vista], icono: { campanas: 'megafono', conjuntos: 'capas', anuncios: 'star' }[vista],
    sub: `Con entrega en el periodo · ${conComp ? `la flecha compara con ${ante(P)}` : 'sin comparación'}` },
  enCuerpo(chipsFiltro({ etiqueta: 'Entrega', valor: soloActivas ? 'activas' : '', opciones: [{ valor: '', texto: 'Todas', cuenta: filas.length }, { valor: 'activas', texto: 'Activas ahora', cuenta: activas, icono: 'zap' }],
    alCambiar: v => { estado.metaActivas = v === 'activas'; estado.repintar(); } })),
  filtradas.length ? tabla({ porPagina: 15, columnas, filas: filtradas }) : enCuerpo(vacioLinea('Sin entrega en este periodo: ninguna gastó ni tuvo impresiones en estas fechas.', { icono: 'vacio' }))));
}

// =========================================================================================== GoHighLevel
const GHL_VISTAS = [{ id: 'oportunidades', texto: 'Oportunidades', icono: 'target' }, { id: 'citas', texto: 'Citas', icono: 'cal' }, { id: 'contactos', texto: 'Contactos y conversaciones', icono: 'chat' }];
const EST_OPP = { open: ['azul', 'Abiertas'], won: ['verde', 'Ganadas'], lost: ['rojo', 'Perdidas'], abandoned: ['gris', 'Abandonadas'] };
const EST_CITA = { confirmed: 'Confirmadas', showed: 'Se presentó', noshow: 'No se presentó', cancelled: 'Canceladas', new: 'Nuevas', invalid: 'No válidas', sin_estado: 'Sin estado' };

function pintarGHL(z, f, P, vista, ctx, estado) {
  const enP = (d, r) => r && d && d >= r.desde && d <= r.hasta;
  const opps = (f.oportunidades || []).map(o => ({ creada: o[0], embudo: o[1], etapa: o[2], estado: o[3], valor: o[4] || 0, origen: o[5] || 'Sin origen', cambio: o[6] }));
  if (vista === 'oportunidades') {
    const embudos = f.embudos || [];
    const conOpps = embudos.map(e => ({ ...e, n: opps.filter(o => o.embudo === e.id && enP(o.creada, P)).length }));
    const elegido = estado.ghlEmbudo && embudos.some(e => e.id === estado.ghlEmbudo) ? estado.ghlEmbudo : '';
    const base = o => !elegido || o.embudo === elegido;
    const A = opps.filter(o => base(o) && enP(o.creada, P)), B = P.comp ? opps.filter(o => base(o) && enP(o.creada, P.comp)) : [];
    const cuenta = (L, e) => L.filter(o => o.estado === e).length;
    const valor = L => L.reduce((t, o) => t + o.valor, 0);
    const conv = L => (L.length ? cuenta(L, 'won') / L.length : null);
    z.append(chipsFiltro({ etiqueta: 'Embudo', valor: elegido, opciones: [{ valor: '', texto: 'Todos los embudos', cuenta: conOpps.reduce((t, e) => t + e.n, 0) }, ...conOpps.filter(e => e.n || e.id === elegido).map(e => ({ valor: e.id, texto: e.nombre, cuenta: e.n }))],
      alCambiar: v => { estado.ghlEmbudo = v; estado.repintar(); } }));
    z.append(tiles([
      tarjeta({ icono: 'target', etiqueta: 'Oportunidades creadas', valor: n0(A.length), comparacion: compTile(A.length, P.comp ? B.length : null, P) }),
      tarjeta({ icono: 'check', etiqueta: 'Ganadas', valor: n0(cuenta(A, 'won')), estado: cuenta(A, 'won') ? 'verde' : '', comparacion: compTile(cuenta(A, 'won'), P.comp ? cuenta(B, 'won') : null, P) }),
      tarjeta({ icono: 'cerrar', etiqueta: 'Perdidas', valor: n0(cuenta(A, 'lost')), comparacion: compTile(cuenta(A, 'lost'), P.comp ? cuenta(B, 'lost') : null, P, 'bajo') }),
      tarjeta({ icono: 'sube', etiqueta: 'Tasa de cierre', valor: conv(A) === null ? null : pc(conv(A)), contexto: 'Ganadas ÷ creadas en el periodo', comparacion: compTile(conv(A), conv(B), P) }),
      tarjeta({ icono: 'euro', etiqueta: 'Valor de las oportunidades', valor: valor(A) ? eur(valor(A)) : '0 €', contexto: valor(A) ? 'Lo que el despacho ha puesto como valor' : 'Nadie rellena el valor en esta subcuenta', comparacion: valor(A) ? compTile(valor(A), valor(B), P) : null }),
    ]));
    // embudo por etapa (las oportunidades creadas en el periodo, en la etapa en que están hoy)
    const etapas = (elegido ? embudos.filter(e => e.id === elegido) : embudos).flatMap(e => e.etapas.map(s => ({ ...s, embudo: e.nombre })));
    const porEtapa = etapas.map(s => ({ ...s, n: A.filter(o => o.etapa === s.id).length, v: valor(A.filter(o => o.etapa === s.id)) })).filter(s => s.n || elegido);
    const max = Math.max(1, ...porEtapa.map(s => s.n));
    const grupos = [...new Set(porEtapa.map(s => s.embudo))];
    z.append(panel({ titulo: 'Embudo por etapa', icono: 'capas', sub: 'Oportunidades creadas en el periodo, en la etapa en la que están hoy (como el panel de la subcuenta)' },
      enCuerpo(porEtapa.length ? h('div', { class: 'pila', style: { gap: 'var(--s-5)' } }, grupos.map(g => h('div', { class: 'pila', style: { gap: 'var(--s-2)' } },
        grupos.length > 1 ? h('p', { style: { font: 'var(--t-eyebrow)', letterSpacing: '.06em', textTransform: 'uppercase', color: 'var(--dim)' } }, g) : null,
        embudoBarras(porEtapa.filter(s => s.embudo === g).map(s => ({ etiqueta: s.nombre, valor: s.n, nota: s.v ? `Valor: ${eur(s.v)}` : null })), { max }))))
        : vacioLinea('Sin oportunidades en este periodo: no se creó ninguna en estas fechas.', { icono: 'target' }))));
    const estados = Object.keys(EST_OPP).map(k => ({ nombre: EST_OPP[k][1], a: [cuenta(A, k), valor(A.filter(o => o.estado === k))], c: P.comp ? [cuenta(B, k), valor(B.filter(o => o.estado === k))] : undefined }));
    const origenes = {};
    for (const o of A) { (origenes[o.origen] ||= { a: [0, 0], c: [0, 0] }).a[0]++; if (o.estado === 'won') origenes[o.origen].a[1]++; }
    for (const o of B) { if (origenes[o.origen]) { origenes[o.origen].c[0]++; if (o.estado === 'won') origenes[o.origen].c[1]++; } }
    z.append(h('div', { class: 'rejilla' },
      panel({ titulo: 'Por estado', icono: 'flag' }, tablaComp({ filas: estados, P, primera: 'Estado', columnas: [{ titulo: 'Oportunidades', i: 0 }, { titulo: 'Valor', i: 1, f: eur }] })),
      panel({ titulo: 'Por origen', icono: 'link' }, tablaComp({ filas: Object.entries(origenes).map(([nombre, v]) => ({ nombre, a: v.a, c: P.comp ? v.c : undefined })).sort((x, y) => y.a[0] - x.a[0]), P, primera: 'Origen', columnas: [{ titulo: 'Creadas', i: 0 }, { titulo: 'Ganadas', i: 1 }] }))));
    if ((f.oportunidades || []).length >= 4000) z.append(vacioLinea('Se leen como mucho 4.000 oportunidades por subcuenta (las más nuevas).'));
  } else if (vista === 'citas') {
    const sumaC = r => { const t = {}; for (const [d, x] of Object.entries(f.citas || {})) if (enP(d, r)) for (const [k, n] of Object.entries(x)) t[k] = (t[k] || 0) + n; return t; };
    const A = sumaC(P), B = P.comp ? sumaC(P.comp) : {};
    const tot = x => Object.values(x).reduce((s, n) => s + n, 0);
    const marcadas = x => (x.showed || 0) + (x.noshow || 0);
    const asis = x => (marcadas(x) ? (x.showed || 0) / marcadas(x) : null);
    z.append(tiles([
      tarjeta({ icono: 'cal', etiqueta: 'Citas', valor: n0(tot(A)), comparacion: compTile(tot(A), P.comp ? tot(B) : null, P) }),
      tarjeta({ icono: 'check', etiqueta: 'Se presentó', valor: n0(A.showed || 0), comparacion: compTile(A.showed || 0, P.comp ? B.showed || 0 : null, P) }),
      tarjeta({ icono: 'cerrar', etiqueta: 'No se presentó', valor: n0(A.noshow || 0), comparacion: compTile(A.noshow || 0, P.comp ? B.noshow || 0 : null, P, 'bajo') }),
      tarjeta({ icono: 'users', etiqueta: 'Asistencia', valor: asis(A) === null ? null : pc(asis(A)), estado: asis(A) === null ? 'gris' : asis(A) >= 0.75 ? 'verde' : asis(A) >= 0.6 ? 'ambar' : 'rojo', contexto: marcadas(A) ? `${marcadas(A)} de ${tot(A)} citas marcadas · bien desde el 75 %` : 'Nadie marca «se presentó» en estas citas', medible: 'medias' }),
    ]));
    const serie = {}; for (const [d, x] of Object.entries(f.citas || {})) serie[d] = tot(x);
    z.append(panel({ titulo: 'Citas por día', icono: 'grafico', sub: 'Por el día de la cita (también las futuras)' }, enCuerpo(graficoDoble({ actual: serieDelPeriodo(serie, P), comp: P.comp ? serieDelPeriodo(serie, P.comp) : null, P }))));
    z.append(panel({ titulo: 'Por estado', icono: 'flag' }, tablaComp({ filas: Object.keys({ ...A, ...B }).map(k => ({ nombre: EST_CITA[k] || k, a: [A[k] || 0], c: P.comp ? [B[k] || 0] : undefined })).sort((x, y) => y.a[0] - x.a[0]), P, primera: 'Estado', columnas: [{ titulo: 'Citas', i: 0 }], vacioTxt: 'Sin citas en este periodo' })));
    if (!f.calendarios) z.append(vacioLinea('Esta subcuenta no tiene calendarios creados.', { icono: 'cal', quien: 'CRM' }));
  } else {
    const cn = PRESET.has(P.id) ? f.contactos_nuevos?.[P.id] : null;
    const k = claveComp(P);
    const cv = f.conversaciones || {};
    z.append(tiles([
      tarjeta({ icono: 'persona', etiqueta: 'Contactos nuevos', valor: cn ? n0(cn.a) : null, comparacion: cn && k ? compTile(cn.a, cn[k], P) : null, contexto: cn ? 'Contactos creados en el periodo' : 'Solo en los periodos fijos' }),
      tarjeta({ icono: 'users', etiqueta: 'Contactos en total', valor: n0(f.contactos_total), contexto: 'Toda la subcuenta, hoy' }),
      tarjeta({ icono: 'chat', etiqueta: 'Conversaciones sin leer', valor: cv.sin_leer ?? null, estado: cv.sin_leer ? 'ambar' : 'verde', contexto: `De las ${cv.muestra || 0} con el último mensaje más reciente · ${n0(cv.mensajes_sin_leer || 0)} mensajes`, medible: 'hoy' }),
      tarjeta({ icono: 'clock', etiqueta: 'Último mensaje', valor: cv.ultima ? fDiaHoraRO(new Date(cv.ultima).toISOString().slice(0, 16).replace('T', ' ')) : null, contexto: 'Entrante o saliente, cualquier canal' }),
    ]));
    const TIPO = { TYPE_WHATSAPP: 'WhatsApp', TYPE_EMAIL: 'Correo', TYPE_CAMPAIGN_EMAIL: 'Correo de campaña', TYPE_SMS: 'SMS', TYPE_CALL: 'Llamada', TYPE_FACEBOOK: 'Facebook', TYPE_INSTAGRAM: 'Instagram', TYPE_NO_SHOW: 'Aviso de no presentado', TYPE_ACTIVITY_OPPORTUNITY: 'Actividad', TYPE_LIVE_CHAT: 'Chat de la web', TYPE_GMB: 'Ficha de Google' };
    z.append(panel({ titulo: 'Canal del último mensaje', icono: 'chat', sub: 'Conversaciones más recientes de la subcuenta (foto de ahora, no depende del periodo)' },
      tabla({ porPagina: 0, filas: Object.entries(cv.por_tipo || {}).map(([t, n]) => ({ t: TIPO[t] || t || 'Otro', n })).sort((x, y) => y.n - x.n),
        columnas: [{ titulo: 'Canal', principal: true, clave: 't' }, { titulo: 'Conversaciones', num: true, celda: r => n0(r.n) }], vacio: { titulo: 'Sin conversaciones' } })));
  }
}

// =========================================================================================== Metricool
const RED = { instagram: ['Instagram', 'heart'], facebook: ['Facebook', 'users'], linkedin: ['LinkedIn', 'maletin'] };
const MC_MET = {
  followers: ['Seguidores', 'users', 'nivel'], reach: ['Alcance', 'persona', 'suma'], impressions: ['Impresiones', 'ojo', 'suma'], pageImpressions: ['Impresiones de la página', 'ojo', 'suma'],
  postsInteractions: ['Interacciones', 'heart', 'suma'], interactions: ['Interacciones', 'heart', 'suma'], profileViews: ['Visitas al perfil', 'persona', 'suma'], pageViews: ['Visitas a la página', 'persona', 'suma'], postsCount: ['Publicaciones', 'doc', 'suma'],
};
function nivelEn(s, r) { const d = Object.keys(s).filter(x => x <= r.hasta).sort(); return d.length ? s[d.at(-1)] : null; }
function pintarMC(z, f, P, vista, ctx, estado) {
  const redes = Object.keys(f.redes || {});
  const red = redes.includes(vista) ? vista : redes[0];
  if (!red) { z.append(vacio({ icono: 'heart', titulo: 'Sin analítica de redes', texto: 'Metricool no devuelve métricas de esta marca.', quien: 'Redes' })); return; }
  const m = f.redes[red];
  const sel = estado.mcMet && m[estado.mcMet] ? estado.mcMet : Object.keys(m).find(k => MC_MET[k]?.[2] === 'suma') || Object.keys(m)[0];
  const cards = Object.entries(m).filter(([k]) => MC_MET[k]).map(([k, s]) => {
    const [et, ic, tipo] = MC_MET[k];
    const a = tipo === 'nivel' ? nivelEn(s, P) : sumarSerie(s, P);
    const b = P.comp ? (tipo === 'nivel' ? nivelEn(s, P.comp) : sumarSerie(s, P.comp)) : null;
    return tarjeta({ icono: ic, etiqueta: et, valor: a === null ? null : n0(a), activo: sel === k, alPulsar: () => { estado.mcMet = k; estado.repintar(); },
      comparacion: tipo === 'nivel' && a !== null && b !== null && P.comp ? { delta: a - b, texto: frente(P) } : compTile(a, b, P), contexto: tipo === 'nivel' ? `Al final del periodo (${fechaCorta(P.hasta, true)})` : null });
  });
  z.append(tiles(cards));
  const [et] = MC_MET[sel] || [sel];
  z.append(panel({ titulo: `${et} por día · ${RED[red]?.[0] || red}`, icono: 'grafico', sub: 'Pulsa una tarjeta para cambiar la línea' },
    enCuerpo(graficoDoble({ actual: serieDelPeriodo(m[sel], P), comp: P.comp ? serieDelPeriodo(m[sel], P.comp) : null, P }))));
  z.append(h('div', { class: 'fila', style: { justifyContent: 'space-between' } }, h('p', { class: 'sub' }, 'Lo programado, los huecos y el rendimiento de cada publicación están en Redes.'), h('a', { class: 'bt', href: `#/redes/${estado.cli?.id || ctx.params[0] || ''}` }, icono('heart'), 'Abrir en Redes')));
}

// =========================================================================================== Empresa: Desk y Zadarma
function pintarDesk(z, d, P) {
  const T = d.tickets || [];
  const en = (x, r) => r && x && x >= r.desde && x <= r.hasta;
  const A = T.filter(t => en(t.creado, P)), B = P.comp ? T.filter(t => en(t.creado, P.comp)) : [];
  const cerrA = T.filter(t => en(t.cerrado, P)).length, cerrB = P.comp ? T.filter(t => en(t.cerrado, P.comp)).length : null;
  const abiertos = T.filter(t => !t.cerrado && (t.estado || '').toLowerCase() !== 'closed');
  const vencidos = abiertos.filter(t => t.vencido).length;
  const durC = L => { const v = L.filter(t => t.cerrado).map(t => diasEntre(t.creado, t.cerrado)); return v.length ? v.reduce((a, x) => a + x, 0) / v.length : null; };
  z.append(tiles([
    tarjeta({ icono: 'inbox', etiqueta: 'Tickets nuevos', valor: n0(A.length), comparacion: compTile(A.length, P.comp ? B.length : null, P, 'bajo') }),
    tarjeta({ icono: 'check', etiqueta: 'Cerrados', valor: n0(cerrA), comparacion: compTile(cerrA, cerrB, P) }),
    tarjeta({ icono: 'alert', etiqueta: 'Abiertos ahora', valor: n0(abiertos.length), estado: abiertos.length ? 'ambar' : 'verde', contexto: `${vencidos} fuera de plazo`, medible: 'hoy' }),
    tarjeta({ icono: 'clock', etiqueta: 'Días hasta cerrar (media)', valor: durC(A) === null ? null : n1(durC(A)), comparacion: compTile(durC(A), durC(B), P, 'bajo'), contexto: 'De los creados en el periodo que ya están cerrados' }),
  ]));
  const serie = {}; for (const t of T) serie[t.creado] = (serie[t.creado] || 0) + 1;
  z.append(panel({ titulo: 'Tickets nuevos por día', icono: 'grafico' }, enCuerpo(graficoDoble({ actual: serieDelPeriodo(serie, P), comp: P.comp ? serieDelPeriodo(serie, P.comp) : null, P }))));
  const agrupar = (L, k) => L.reduce((o, t) => ((o[t[k] || 'Sin dato'] = (o[t[k] || 'Sin dato'] || 0) + 1), o), {});
  const tab = (k, primera, titulo, ic) => { const a = agrupar(A, k), b = agrupar(B, k); return panel({ titulo, icono: ic }, tablaComp({ filas: Object.keys(a).map(x => ({ nombre: x, a: [a[x]], c: P.comp ? [b[x] || 0] : undefined })).sort((x, y) => y.a[0] - x.a[0]), P, primera, columnas: [{ titulo: 'Tickets nuevos', i: 0, mejorSi: 'neutro' }] })); };
  z.append(h('div', { class: 'rejilla' }, tab('agente', 'Persona', 'Por persona asignada', 'persona'), tab('canal', 'Canal', 'Por canal', 'mail')), tab('dep', 'Departamento', 'Por departamento', 'inbox'));
  z.append(pliegue('Qué departamentos se ven', `La llave de lectura abre ${d.legibles?.length || 0} de ${d.departamentos || 0} departamentos de Desk (${(d.legibles || []).join(', ') || 'ninguno'}). Lo que es «sin contestar» con su plazo está en la Bandeja.`));
}

function pintarZadarma(z, d, P) {
  const L = d.llamadas || [];
  const desde = L.length ? L.map(x => x.dia).sort()[0] : null;
  const en = (x, r) => r && x >= r.desde && x <= r.hasta;
  const A = L.filter(x => en(x.dia, P)), B = P.comp ? L.filter(x => en(x.dia, P.comp)) : [];
  const ent = X => X.filter(x => x.sentido === 'entrante');
  const perd = X => ent(X).filter(x => x.estado !== 'answered');
  const cont = X => X.filter(x => x.estado === 'answered');
  const media = X => { const c = cont(X); return c.length ? c.reduce((a, x) => a + x.seg, 0) / c.length : null; };
  z.append(tiles([
    tarjeta({ icono: 'phone', etiqueta: 'Llamadas', valor: n0(A.length), comparacion: compTile(A.length, P.comp ? B.length : null, P) }),
    tarjeta({ icono: 'auricular', etiqueta: 'Entrantes', valor: n0(ent(A).length), comparacion: compTile(ent(A).length, P.comp ? ent(B).length : null, P) }),
    tarjeta({ icono: 'alert', etiqueta: 'Entrantes sin contestar', valor: n0(perd(A).length), estado: perd(A).length ? 'ambar' : 'verde', comparacion: compTile(perd(A).length, P.comp ? perd(B).length : null, P, 'bajo'), contexto: 'Las que hay que devolver están en la Bandeja' }),
    tarjeta({ icono: 'clock', etiqueta: 'Duración media contestadas', valor: dur(media(A)), comparacion: compTile(media(A), media(B), P) }),
  ]));
  if (desde && P.desde < desde) z.append(vacioLinea(`Hay llamadas desde el ${fechaCorta(desde, true)} (Zadarma se lee por tramos de 95 días).`, { icono: 'clock' }));
  const serie = {}; for (const x of L) serie[x.dia] = (serie[x.dia] || 0) + 1;
  z.append(panel({ titulo: 'Llamadas por día', icono: 'grafico' }, enCuerpo(graficoDoble({ actual: serieDelPeriodo(serie, P), comp: P.comp ? serieDelPeriodo(serie, P.comp) : null, P }))));
  const ext = {}; for (const x of A) { const k = x.ext || 'Sin extensión'; (ext[k] ||= [0, 0, 0]); ext[k][0]++; if (x.estado === 'answered') ext[k][1]++; ext[k][2] += x.seg; }
  const horas = {}; for (const x of ent(A)) { horas[x.hora] ||= [0, 0]; horas[x.hora][0]++; if (x.estado !== 'answered') horas[x.hora][1]++; }
  z.append(h('div', { class: 'rejilla' },
    panel({ titulo: 'Por extensión', icono: 'auricular' }, tabla({ porPagina: 0, filas: Object.entries(ext).sort((a, b) => b[1][0] - a[1][0]).map(([k, v]) => ({ k: d.extensiones?.[k] ? `${d.extensiones[k]} (${k})` : k, v })),
      columnas: [{ titulo: 'Extensión', principal: true, clave: 'k' }, { titulo: 'Llamadas', num: true, celda: r => n0(r.v[0]) }, { titulo: 'Contestadas', num: true, celda: r => n0(r.v[1]) }, { titulo: 'Minutos', num: true, celda: r => n0(r.v[2] / 60) }], vacio: { titulo: 'Sin llamadas' } })),
    panel({ titulo: 'Entrantes por hora del día', icono: 'clock' }, tabla({ porPagina: 0, filas: Object.entries(horas).sort().map(([k, v]) => ({ k: `${k}:00`, v })),
      columnas: [{ titulo: 'Hora', principal: true, clave: 'k' }, { titulo: 'Entrantes', num: true, celda: r => n0(r.v[0]) }, { titulo: 'Sin contestar', num: true, celda: r => celda(r.v[1], undefined) }], vacio: { titulo: 'Sin entrantes' } }))));
}

// =========================================================================================== mapa de paridad
const MAPA = [
  ['Meta Ads', 'Administrador de anuncios: campañas, conjuntos y anuncios con importe, leads, coste por lead, alcance, frecuencia y CTR', 'paneles', 'Paneles › Meta Ads', 'hecho'],
  ['Meta Ads', 'Torre de control: coste por cita contra el objetivo, metas, gasto y leads por cliente y trafficker', 'captacion', 'Captación', 'hecho'],
  ['GoHighLevel', 'Panel de la subcuenta: oportunidades por embudo y etapa, ganadas, perdidas, valor y origen', 'paneles', 'Paneles › GoHighLevel', 'hecho'],
  ['GoHighLevel', 'Calendarios: citas por estado y asistencia', 'paneles', 'Paneles › GoHighLevel › Citas', 'hecho'],
  ['GoHighLevel', 'Leads sin tocar, velocidad, citas sin estado, oportunidades paradas, flujos', 'salud-crm', 'Salud del CRM', 'hecho'],
  ['GoHighLevel', 'Conversaciones: sin leer y canal', 'paneles', 'Paneles › GoHighLevel › Contactos', 'a_medias'],
  ['Analytics', 'Informes estándar: resumen, adquisición, interacción, eventos clave, páginas, tecnología y lugar', 'paneles', 'Paneles › Analytics', 'hecho'],
  ['Analytics', 'Las páginas de Analytics de los Looker de cliente', 'informe-cliente', 'Informe del cliente', 'hecho'],
  ['Search Console', 'Rendimiento: consultas, páginas, países, dispositivos y aparición', 'paneles', 'Paneles › Search Console', 'hecho'],
  ['Search Console', 'Indexación: sitemaps e inspección de las páginas principales', 'paneles', 'Paneles › Search Console › Indexación', 'a_medias'],
  ['Search Console', 'Experiencia: métricas web principales (móvil y ordenador)', 'paneles', 'Paneles › Search Console › Experiencia', 'hecho'],
  ['SE Ranking', 'Posiciones, top 5/10, suben y bajan, visibilidad', 'seo-web', 'SEO, ficha y webs', 'hecho'],
  ['SE Ranking', 'Competencia (posiciones de los competidores)', null, 'Falta: la clave de proyectos da 403', 'falta'],
  ['Metricool', 'Planificación: calendario de 14 días, huecos, fallidas, por aprobar', 'redes', 'Redes', 'hecho'],
  ['Metricool', 'Analítica por red: seguidores, alcance, impresiones, interacciones', 'paneles', 'Paneles › Metricool', 'hecho'],
  ['ClickUp', 'Tareas por persona, revisiones, bloqueadas, carga', 'produccion', 'Producción', 'hecho'],
  ['ClickUp', 'Horas imputadas por persona y cliente', 'horas', 'Horas y productividad', 'hecho'],
  ['ClickUp', 'Chat de los canales internos', 'chat-equipo', 'Chat del equipo', 'hecho'],
  ['Zoho Desk', 'Correos sin contestar con su plazo, por account', 'bandeja', 'Bandeja', 'hecho'],
  ['Zoho Desk', 'Tickets nuevos y cerrados, abiertos, fuera de plazo, por persona, canal y departamento', 'paneles', 'Paneles › Empresa › Zoho Desk', 'hecho'],
  ['Zadarma', 'Llamadas sin devolver', 'bandeja', 'Bandeja', 'hecho'],
  ['Zadarma', 'Llamadas por día, extensión y hora', 'paneles', 'Paneles › Empresa › Zadarma', 'hecho'],
  ['Zoom', 'Reuniones, horas y reunión del ciclo con cada cliente', 'reuniones', 'Reuniones', 'hecho'],
  ['Holded', 'Facturas, cobros, impagos, caja', 'finanzas', 'Finanzas de la empresa', 'hecho'],
  ['Looker Studio', 'Los 22 informes de cliente, con comparación página a página', 'informe-cliente', 'Informe del cliente › Comparación con Looker', 'hecho'],
  ['Panel de Mili', 'Su ronda, mapa de control por persona, alarmas', 'mi-dia', 'Mi día (Mili) · Incidencias · En rojo', 'hecho'],
  ['Panel de dirección', 'El panel de resultados v29/v30 entero', 'panel-direccion', 'Panel de dirección', 'hecho'],
  ['Google Ads', 'Campañas, términos de búsqueda, llamadas', 'informe-cliente', 'Muestra de septiembre; falta la clave de Windsor', 'a_medias'],
  ['Ficha de Google', 'Llamadas, rutas, visitas y reseñas', null, 'Falta el permiso de Business Profile', 'falta'],
];
function pintarMapa(z, ctx) {
  const n = { hecho: MAPA.filter(x => x[4] === 'hecho').length, a_medias: MAPA.filter(x => x[4] === 'a_medias').length, falta: MAPA.filter(x => x[4] === 'falta').length };
  z.append(tiles([
    tarjeta({ icono: 'check', etiqueta: 'Vistas que ya están en la app', valor: n.hecho, unidad: `de ${MAPA.length}`, estado: 'verde' }),
    tarjeta({ icono: 'alert', etiqueta: 'A medias', valor: n.a_medias, estado: n.a_medias ? 'ambar' : 'verde' }),
    tarjeta({ icono: 'cerrar', etiqueta: 'Faltan', valor: n.falta, estado: n.falta ? 'rojo' : 'verde', contexto: 'Esperan una llave o un permiso' }),
  ]));
  const EST = { hecho: ['verde', 'En la app'], a_medias: ['ambar', 'A medias'], falta: ['rojo', 'Falta'] };
  z.append(panel({ titulo: 'Dónde está cada panel de cada herramienta', icono: 'capas', sub: 'Lo que el equipo miraba en cada herramienta y dónde se mira ahora. No depende del periodo.' },
    tabla({ porPagina: 0, filas: MAPA.map(([herr, que, mod, donde, est]) => ({ herr, que, mod, donde, est })),
      columnas: [
        { titulo: 'Herramienta', principal: true, clave: 'herr' }, { titulo: 'Vista', clave: 'que' },
        { titulo: 'Estado', celda: r => chipEstado(...EST[r.est]) },
        { titulo: 'Dónde', celda: r => (r.mod && ctx.veModulo?.(r.mod) !== false ? h('a', { class: 'bt mini', href: `#/${r.mod}` }, icono('derecha', { clase: 's' }), r.donde) : h('span', { class: 'sub' }, r.donde)) },
      ] })));
}

// =========================================================================================== pantalla
let quitarOyente = null;
const periodoDe = ctx => ctx.periodo || periodoCompleto(leerPeriodo(ctx.persona.id));
/** escucha el periodo común sin acumular oyentes al navegar dentro de Paneles (cliente, herramienta o vista). */
function escuchar(ctx, fn) { try { quitarOyente?.(); } catch { /* */ } quitarOyente = fn && ctx.alCambiarPeriodo ? ctx.alCambiarPeriodo(fn) : null; }

/** «Otros paneles ▾»: el mapa y, para dirección y operaciones, Zoho Desk y Zadarma de la empresa. */
function otrosPaneles(ctx, activo) {
  const items = [];
  if (activo) items.push({ texto: 'Paneles por cliente', icono: 'cli', href: '#/paneles' });
  items.push({ texto: 'Dónde está cada panel', icono: 'capas', href: '#/paneles/mapa', activo: activo === 'mapa' });
  if (esEmpresa(ctx)) items.push({ texto: 'Zoho Desk de la empresa', icono: 'inbox', href: '#/paneles/empresa/desk', activo: activo === 'desk' },
    { texto: 'Zadarma de la empresa', icono: 'phone', href: '#/paneles/empresa/zadarma', activo: activo === 'zadarma' });
  return menuMas({ texto: 'Otros paneles', etiqueta: 'Otros paneles', items, activo: Boolean(activo) });   // ronda 10: el común ya no pinta «null»
}
/** Último día con dato de la serie diaria de la herramienta (Analytics y Search Console), o null. */
function ultimoDato(herr, f) {
  const serie = ['ga4', 'gsc'].includes(herr) ? f?.serie : null;
  if (!serie || typeof serie !== 'object') return null;
  const ks = Object.keys(serie).filter(k => /^\d{4}-\d{2}-\d{2}$/.test(k));
  return ks.length ? ks.sort().pop() : null;
}
const filaEntre = (...hijos) => h('div', { class: 'fila', style: { justifyContent: 'space-between' } }, ...hijos);

export default {
  id: 'paneles',
  titulo: 'Paneles de herramientas',
  grupo: 'Clientes',
  usa_periodo: params => params?.[0] !== 'mapa',   // «Dónde está cada panel» no depende del periodo: sin barra de periodo
  puestos_que_lo_ven: {
    direccion: 'todo', finanzas_direccion: 'todo', operaciones: 'todo', proyectos: 'todo', jefa_publicidad: 'todo', jefa_seo: 'todo', jefa_crm: 'todo', tecnico_altas: 'todo',
    account: 'suyo', trafficker: 'suyo', especialista_ghl: 'suyo', seo: 'suyo', ficha_google: 'suyo', web: 'suyo', redes: 'suyo',
  },
  // Ronda U (#1): pantalla de consulta; el consejo de la IA no empuja el selector ni el panel: va plegado al pie
  async render(cont, ctx) {
    await this.pintar(cont, ctx);
    const ultimo = cont.lastElementChild;
    if (ultimo) consejoCompacto(cont, ultimo);   // el consejo, plegado y detrás del panel
  },
  async pintar(cont, ctx) {
    vigilarCortes(cont);
    const [a0, a1, a2] = ctx.params || [];
    escuchar(ctx, null);
    if (a0 === 'mapa') {
      ctx.titulo('Paneles de herramientas', 'Dónde está cada panel de cada herramienta');
      cont.append(filaEntre(h('span'), otrosPaneles(ctx, 'mapa')));
      const z = pila(); cont.append(z); pintarMapa(z, ctx); return;
    }
    let indice;
    try { indice = await ctx.datosModulo('paneles/indice'); } catch (e) { cont.append(vacio({ icono: 'alert', titulo: 'No se pueden leer los paneles', texto: String(e.message || e), quien: 'Tomás' })); return; }
    if (a0 === 'empresa') return pintarEmpresa(cont, ctx, a1 || 'desk', indice);
    const filas = (indice.filas || []).filter(f => Object.entries(f.fuentes || {}).some(([k, x]) => veHerr(ctx, k) && x.estado !== 'sin_conectar'));
    const visibles = (ctx.clientesVisibles || []).filter(c => filas.some(f => f.cliente_id === c.id));
    const mis = visibles.filter(c => ctx.carteraIds?.has(c.id));
    if (!visibles.length) {
      ctx.titulo('Paneles de herramientas', 'Las vistas de cada herramienta, por cliente');
      cont.append(filaEntre(h('span'), otrosPaneles(ctx)));
      cont.append(vacio({ icono: 'capas', titulo: 'Ningún cliente tuyo tiene herramientas conectadas', texto: 'Cuando tus clientes tengan Meta, GoHighLevel, Analytics, Search Console o Metricool emparejados, sus paneles salen aquí.', quien: 'Agus' }));
      return;
    }
    let recordado = null; try { recordado = localStorage.getItem(`ro.paneles.cli.${ctx.persona.id}`); } catch { /* */ }
    const cli = visibles.find(c => c.id === a0) || visibles.find(c => c.id === recordado) || mis[0] || visibles[0];
    try { localStorage.setItem(`ro.paneles.cli.${ctx.persona.id}`, cli.id); } catch { /* */ }
    const fila = filas.find(f => f.cliente_id === cli.id);
    const orden = [...new Set([...(ctx.persona.puestos.flatMap(p => ORDEN[p] || [])), 'meta', 'ghl', 'ga4', 'gsc', 'mc'])].filter(k => veHerr(ctx, k));
    const herrs = orden.filter(k => fila.fuentes[k] && fila.fuentes[k].estado !== 'sin_conectar');
    const sinConectar = orden.filter(k => !herrs.includes(k));
    const herr = herrs.includes(a1) ? a1 : herrs[0];
    // el nombre del cliente sale una vez: en el selector (guía 3.6)
    ctx.titulo('Paneles de herramientas', 'Las vistas de cada herramienta, por cliente y con el periodo de arriba');

    const estado = { repintar: () => {}, cli };
    const sc = selectorCliente({ clientes: visibles, actual: cli.id, etiqueta: 'Cambiar de cliente', alElegir: c => ctx.navegar(`paneles/${c.id}/${herr}${a2 ? '/' + a2 : ''}`) });
    cont.append(filaEntre(sc, otrosPaneles(ctx)));
    const fx = fila.fuentes[herr] || {};
    const nav = h('div', { class: 'pila' });
    if (herrs.length) {
      nav.append(pestanas({
        etiqueta: 'Herramienta', pestanas: herrs.map(k => ({ id: k, texto: HERR[k].texto, icono: HERR[k].icono, cuenta: ['rota'].includes(fila.fuentes[k].estado) ? 1 : undefined, cuentaEstado: 'rojo' })),
        activa: herr, alCambiar: id => ctx.navegar(`paneles/${cli.id}/${id}`),
      }));
    }
    const zona = pila();
    cont.append(nav, zona);
    const pieSinConectar = () => (sinConectar.length && herr ? cont.append(h('p', { class: 'sub' }, `Sin conectar para este cliente: ${sinConectar.map(k => HERR[k].texto).join(', ')}.`)) : null);
    if (!herr) { zona.append(vacio({ icono: 'plug', titulo: 'Este cliente no tiene herramientas conectadas', texto: sinConectar.map(k => `${HERR[k].texto}: ${fila.fuentes[k]?.nota || 'sin emparejar'}`).join(' · '), quien: 'Agus' })); return; }
    if (fx.estado === 'rota' || fx.estado === 'sin_leer') { zona.append(vacio({ icono: 'alert', tono: 'aviso', titulo: `${HERR[herr].texto} no responde para este cliente`, texto: fx.nota || 'La última lectura falló. Se reintenta en la próxima recarga.', quien: 'Agus' })); pieSinConectar(); return; }
    let datos;
    try { datos = (await ctx.datosModulo(`paneles/${herr}/${cli.id}`))?.filas?.[0]; } catch { datos = null; }
    if (!datos) { zona.append(vacio({ icono: 'vacio', titulo: 'Sin datos de esta herramienta', texto: fx.nota || 'La herramienta no devolvió datos de este cliente.', quien: 'Agus' })); pieSinConectar(); return; }
    // R12 (A2) · si la herramienta elegida por defecto no tiene datos recientes, el periodo no cambiaría nada: se abre la
    // siguiente con datos (p. ej. ECIJA: Analytics sin datos desde el 31-jul → Search Console).
    if (!a1 && ultimoDato(herr, datos) && ultimoDato(herr, datos) < sumarDias(hoyMadrid(), -14)) {
      const otra = herrs.find(k => k !== herr && ['bien'].includes(fila.fuentes[k]?.estado));
      if (otra) { ctx.navegar(`paneles/${cli.id}/${otra}`); return; }
    }
    const VISTAS = { ga4: GA_VISTAS, gsc: GSC_VISTAS, meta: META_VISTAS, ghl: GHL_VISTAS, mc: Object.keys(datos.redes || {}).map(k => ({ id: k, texto: RED[k]?.[0] || k, icono: RED[k]?.[1] || 'heart' })) }[herr];
    const vista = VISTAS.some(v => v.id === a2) ? a2 : VISTAS[0]?.id;
    const PINTA = { ga4: pintarGA, gsc: pintarGSC, meta: pintarMeta, ghl: pintarGHL, mc: pintarMC }[herr];
    // vistas de la herramienta (chips) a la izquierda; frescura y «Abrir en …» a la derecha, en la misma fila
    nav.append(filaEntre(
      VISTAS.length > 1 ? chipsFiltro({ etiqueta: 'Vista', valor: vista, opciones: VISTAS.map(v => ({ valor: v.id, texto: v.texto, icono: v.icono })), alCambiar: id => ctx.navegar(`paneles/${cli.id}/${herr}/${id}`) }) : h('span'),
      h('span', { class: 'fila' },
        fx.hora ? frescura({ fuente: HERR[herr].fuente, fecha: fx.hora }) : null,
        fx.abrir ? h('a', { class: 'bt mini', href: fx.abrir, target: '_blank', rel: 'noopener', title: fx.nombre || null }, icono('ext', { clase: 's' }), `Abrir en ${HERR[herr].texto}`) : null)));
    let P = periodoDe(ctx);
    estado.repintar = () => {
      zona.replaceChildren();
      try { PINTA(zona, datos, P, vista, ctx, estado); } catch (e) { console.error(e); zona.append(vacio({ icono: 'alert', titulo: 'No se ha podido pintar esta vista', texto: String(e.message || e) })); }
    };
    escuchar(ctx, nuevo => { P = nuevo; estado.repintar(); });
    estado.repintar();
    pieSinConectar();
  },
};

async function pintarEmpresa(cont, ctx, cual) {
  ctx.titulo('Paneles de herramientas', cual === 'zadarma' ? 'Zadarma · llamadas de la centralita' : 'Zoho Desk · tickets y plazos');
  if (!esEmpresa(ctx)) { cont.append(filaEntre(h('span'), otrosPaneles(ctx, cual))); cont.append(vacio({ icono: 'candado', titulo: 'Solo dirección y operaciones', texto: 'Estos paneles comparan a personas del equipo.' })); return; }
  let d;
  try { d = await ctx.datosModulo(`paneles/empresa/${cual === 'zadarma' ? 'zadarma' : 'desk'}`); } catch { d = null; }
  const nombre = cual === 'zadarma' ? 'Zadarma' : 'Zoho Desk';
  cont.append(filaEntre(
    d?.leido ? h('span', { class: 'fila' }, frescura({ fuente: nombre, fecha: d.leido }),
      h('a', { class: 'bt mini', href: cual === 'zadarma' ? 'https://my.zadarma.com/' : 'https://desk.zoho.eu/agent/rankingonline836', target: '_blank', rel: 'noopener' }, icono('ext', { clase: 's' }), `Abrir en ${nombre}`)) : h('span'),
    otrosPaneles(ctx, cual)));
  const z = pila();
  cont.append(z);
  let P = periodoDe(ctx);
  const pintar = () => {
    z.replaceChildren();
    if (!d) { z.append(vacio({ icono: 'plug', titulo: 'Sin lectura todavía', texto: 'La próxima recarga de los paneles lo trae.', quien: 'Tomás' })); return; }
    try { (cual === 'zadarma' ? pintarZadarma : pintarDesk)(z, d, P); } catch (e) { console.error(e); z.append(vacio({ icono: 'alert', titulo: 'No se ha podido pintar', texto: String(e.message || e) })); }
  };
  escuchar(ctx, nuevo => { P = nuevo; pintar(); });
  pintar();
}

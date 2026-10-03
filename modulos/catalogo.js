// modulos/catalogo.js · catálogo vivo de componentes (solo Tomás y quien construye módulos).
// Cada ejemplo usa la misma llamada que tendría un módulo real. Los valores de ejemplo van marcados.

import {
  h, fichaIndicador, tarjetaCliente, listaLoPrimero, tablaDensa, chipEstado, selloMedible, frescura,
  lineaTiempo, graficoSerie, estadoVacio, botonConfirmar, avisoParcial, candado, panel,
  // ola 0 · sistema visual
  ICONOS, icono, tile, tiles, chipsFiltro, selectorPeriodo, pestanas, vacio, selectorCliente, tablaApilable,
  botonesContacto, barraEtapas, listaConIcono, avisoFlotante,
  // ronda 9 · guía de estilo (auditoría 30)
  grafico, colorCifra, cifraPrincipal, vacioLinea, menuMas, campoTexto, esqueleto, fmt,
} from '../componentes.js';

/** Barrido v1: el esqueleto de ejemplo ya no se pinta al entrar (la página parecía «cargando» para siempre y el
 *  barrido esperaba 10 s). Se enseña al pulsar y se quita solo a los 3 s. */
function demoEsqueleto() {
  const caja = h('div', { class: 'pila' });
  const bt = h('button', { type: 'button', class: 'bt', on: { click: () => {
    bt.disabled = true;
    const sk = esqueleto({ lineas: 2, tarjetas: 0 });
    caja.append(sk);
    setTimeout(() => { sk.remove(); bt.disabled = false; }, 3000);
  } } }, 'Ver el esqueleto de carga (3 s)');
  caja.append(bt);
  return caja;
}

/** La guía de estilo en vivo (auditoría 30, §3): lo único que un módulo puede usar. Todo sale de tokens de estilos.css. */
function guiaEstilo() {
  const fila = (...x) => h('div', { class: 'fila', style: { gap: 'var(--s-3)', alignItems: 'baseline', flexWrap: 'wrap' } }, ...x);
  const nota = t => h('span', { style: { font: 'var(--t-meta)', color: 'var(--dim)' } }, t);
  const TIPOS = [
    ['--t-display', '32 / 40 · 700', 'Solo la cifra que manda (una por pantalla)', '3.860 €'],
    ['--t-cifra', '24 / 32 · 700', 'Cifra de tarjeta', '1.072'],
    ['--t-h1', '20 / 28 · 700', 'Título de página (cabecera)', 'Captación'],
    ['--t-h2', '15 / 22 · 700', 'Título de panel o bloque', 'Correos y llamadas'],
    ['--t-h3', '13 / 20 · 600', 'Título de fila o tarjeta', 'Queja · Consulting F'],
    ['--t-cuerpo', '13 / 20 · 400', 'Texto normal y celdas', 'Texto de lectura, 72 caracteres por línea como mucho'],
    ['--t-meta', '12 / 16 · 500', 'Etiquetas, fuentes y fechas', 'Desk · hace 13 h'],
    ['--t-eyebrow', '11 / 16 · 700 · MAYÚSCULAS', 'Solo cabeceras de tabla y separadores', 'CLIENTE · 2 OCT'],
  ];
  const tipografia = h('div', { class: 'pila', style: { gap: 'var(--s-3)' } }, TIPOS.map(([tok, med, uso, ej]) => h('div', {
    style: { display: 'grid', gap: 'var(--s-1) var(--s-4)', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 220px), 1fr))', alignItems: 'baseline', paddingBottom: 'var(--s-3)', borderBottom: 'var(--borde-suave)' } },
    h('span', { style: { font: `var(${tok})`, ...(tok === '--t-eyebrow' ? { textTransform: 'uppercase', letterSpacing: '.06em', color: 'var(--dim)' } : {}), ...(tok === '--t-display' || tok === '--t-cifra' ? { letterSpacing: '-.02em' } : {}) } }, ej),
    h('span', { style: { font: 'var(--t-h3)' } }, tok, ' ', nota(med)), nota(uso))));
  const ESP = [1, 2, 3, 4, 5, 6, 8, 10, 12, 16];
  const espacios = fila(...ESP.map(n => h('span', { class: 'pila', style: { gap: 'var(--s-1)', justifyItems: 'center' } },
    h('i', { 'aria-hidden': 'true', style: { display: 'block', width: `var(--s-${n})`, height: `var(--s-${n})`, background: 'var(--accent-soft)', border: '1px solid var(--accent-line)', borderRadius: 'var(--r-s)' } }),
    nota(`--s-${n} · ${n * 4}`))));
  const radios = fila(...[['--r-s', 'chips, celdas'], ['--r-m', 'botones, campos'], ['--r-l', 'tarjetas, paneles'], ['--r-full', 'pastillas, avatares']].map(([r, uso]) =>
    h('span', { class: 'pila', style: { gap: 'var(--s-1)' } }, h('i', { 'aria-hidden': 'true', style: { display: 'block', width: 'var(--s-16)', height: 'var(--s-10)', background: 'var(--card)', border: 'var(--borde)', borderRadius: `var(${r})` } }), nota(`${r} · ${uso}`))));
  const sombras = fila(...[['--sombra-1', 'tarjeta en reposo'], ['--sombra-2', 'al pasar el ratón y menús'], ['--sombra-3', 'modal y ⌘K']].map(([s, uso]) =>
    h('span', { class: 'pila', style: { gap: 'var(--s-2)', minWidth: '0', flex: '1 1 120px' } }, h('i', { 'aria-hidden': 'true', style: { display: 'block', width: 'min(100%, calc(var(--s-16) * 2))', height: 'var(--s-12)', background: 'var(--card)', border: 'var(--borde)', borderRadius: 'var(--r-l)', boxShadow: `var(${s})` } }), nota(`${s} · ${uso}`))));
  const colores = fila(...[['verde', 'va bien contra su objetivo'], ['ambar', 'vigilar'], ['rojo', 'actuar hoy'], ['gris', 'sin dato'], ['azul', 'informativo']].map(([c, uso]) => h('span', { class: 'fila', style: { gap: 'var(--s-2)' } }, chipEstado(c, c === 'ambar' ? 'ámbar' : c), nota(uso))));
  const ejColor = fila(
    tile({ icono: 'euro', etiqueta: 'Beneficio · colorCifra (ejemplo)', valor: fmt.eurSigno ? fmt.eurSigno(3860) : fmt.eur(3860), estado: colorCifra('beneficio', 3860), contexto: "colorCifra('beneficio', 3860)" }),
    tile({ icono: 'users', etiqueta: 'Coste por cliente (ejemplo)', valor: fmt.eur(735), estado: colorCifra('coste_cliente', 735), contexto: "colorCifra('coste_cliente', 735): umbral 700 €" }),
    tile({ icono: 'target', etiqueta: 'Coste por lead (ejemplo)', valor: fmt.eur(31), estado: colorCifra('coste_lead', 31), contexto: "colorCifra('coste_lead', 31): techo 35 €" }));
  ejColor.className = 'tiles';
  return [
    panel({ titulo: 'Guía de estilo · tipografía', icono: 'componentes', sub: 'Montserrat y 7 tamaños: 11 · 12 · 13 · 15 · 20 · 24 · 32. Nada por debajo de 12 salvo la ceja en mayúsculas. Jerarquía: H1 20 > H2 15 > H3 13.' },
      h('div', { class: 'cuerpo' }, tipografia)),
    h('div', { style: { display: 'grid', gap: 'var(--s-6)', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', alignItems: 'start' } },
      panel({ titulo: 'Espaciado · escala de 4', icono: 'capas', sub: 'Relleno de tarjeta y panel: --relleno (20, 16 en el móvil). Entre tarjetas 16; entre bloques 24.' }, h('div', { class: 'cuerpo' }, espacios)),
      panel({ titulo: 'Radios y sombras', icono: 'capas', sub: 'O borde o sombra fuerte, nunca las dos en el mismo nivel.' }, h('div', { class: 'cuerpo pila' }, radios, sombras))),
    panel({ titulo: 'Color con significado · colorCifra()', icono: 'filtro', sub: 'El mismo número tiene el mismo color en todas las pantallas: la regla vive en colorCifra() y semaforo(), nunca en el módulo.' },
      h('div', { class: 'cuerpo pila' }, colores, ejColor)),
    panel({ titulo: 'Cifra que manda, vacíos y carga', icono: 'target', sub: 'cifraPrincipal() una vez por pantalla · vacioLinea() dentro de un bloque · esqueleto() mientras carga' },
      h('div', { class: 'cuerpo pila', style: { gap: 'var(--s-6)' } },
        cifraPrincipal({ etiqueta: 'Beneficio de septiembre (ejemplo)', valor: fmt.eur(3860), estado: colorCifra('beneficio', 3860), comparacion: '▲ 12 % frente a agosto' }),
        vacioLinea('Web (Analytics) · todo a cero en septiembre (ejemplo).', { icono: 'globe', quien: 'Agus' }),
        demoEsqueleto())),
    panel({ titulo: 'Gráfico · grafico()', icono: 'grafico', sub: 'El único motor: mide su caja, letra de 12 px fija, marcas redondas, burbuja al pasar el ratón y umbral discontinuo.' },
      h('div', { class: 'cuerpo' }, grafico({ titulo: 'Leads por semana (ejemplo)', x: ['2026-08-31', '2026-09-07', '2026-09-14', '2026-09-21', '2026-09-28'],
        series: [{ nombre: 'Este periodo', y: [38, 44, 51, 47, 58] }, { nombre: 'Periodo anterior', y: [30, 35, 41, 39, 40], ant: true }], umbral: { y: 45, texto: 'Objetivo 45' } }))),
    panel({ titulo: 'Menú «Más» y campos', icono: 'menu', sub: 'menuMas() para acciones secundarias o pestañas que no caben · campoTexto() para formularios' },
      h('div', { class: 'cuerpo pila' },
        h('div', { class: 'fila' }, menuMas({ texto: 'Abrir', etiqueta: 'Abrir en otra herramienta', items: [{ texto: 'Contacto en GHL', icono: 'ext', href: '#/componentes' }, { texto: 'Evento en Zoho CRM', icono: 'cal', href: '#/componentes' }] })),
        h('div', { style: { display: 'grid', gap: 'var(--s-3)', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 220px), 1fr))' } },
          campoTexto({ etiqueta: 'Nombre (ejemplo)', nombre: 'n6_ej_nombre', placeholder: 'Ana' }), campoTexto({ etiqueta: 'Nota (ejemplo)', nombre: 'n6_ej_nota', ayuda: 'Ayuda en letra de metadatos' })))),
  ];
}

const bloque = (titulo, firma, ...cuerpo) => panel({ titulo, icono: 'componentes', sub: firma }, h('div', { class: 'cuerpo pila' }, cuerpo));

export default {
  id: 'componentes',
  titulo: 'Componentes',
  grupo: 'Sistema',
  puestos_que_lo_ven: { direccion: 'todo' },
  render(cont, ctx) {
    const meta = ctx.datos.meta;
    const c0 = ctx.clientes.find(c => c.logo) || ctx.clientes[0];

    cont.append(avisoParcial('Los ejemplos con cifras inventadas llevan «ejemplo». Los demás usan datos reales del panel v27.', { tipo: 'info', titulo: 'Catálogo vivo.' }));
    cont.append(...guiaEstilo());

    // ---------------- ola 0 · sistema visual (2-oct) ----------------
    const vis = ctx.clientesVisibles.length ? ctx.clientesVisibles : ctx.clientes;
    cont.append(bloque('Iconos', `icono(nombre, { clase: 's' | 'l', titulo }) · ${Object.keys(ICONOS).length} iconos de trazo 1,8 px (base: objeto P de la ficha v3)`,
      h('div', { class: 'fila', style: { gap: 'var(--s-2)' } }, Object.keys(ICONOS).map(n => h('span', { class: 'chip gris sin-punto', title: n }, icono(n, { clase: 's' }), n)))));

    const salida = h('span', { class: 'sub', 'aria-live': 'polite' }, 'Pulsa un tile: el gráfico de debajo cambiaría a esa métrica.');
    cont.append(bloque('Tile (indicador de la ficha v3)', 'tile({ icono, etiqueta, valor, unidad, estado, comparacion: { delta, pct, texto, mejorSi }, contexto, medible, frescura, alPulsar | href, activo, ir })',
      tiles([
        tile({ icono: 'target', etiqueta: 'Leads · 30 días (ejemplo)', valor: 214, comparacion: { delta: 6.5, pct: true, texto: 'frente a agosto' }, contexto: 'Septiembre: 201', activo: true, alPulsar: () => { salida.textContent = 'Elegido: leads (ejemplo)'; } }),
        tile({ icono: 'euro', etiqueta: 'Coste por lead (ejemplo)', valor: '3,52 €', comparacion: { delta: -8, pct: true, texto: 'frente a agosto', mejorSi: 'bajo' }, contexto: 'Gasto 30 días: 753 €', activo: false, alPulsar: () => { salida.textContent = 'Elegido: coste por lead (ejemplo)'; } }),
        tile({ icono: 'mail', etiqueta: 'Sin responder (ejemplo)', valor: 20, unidad: 'días', estado: 'rojo', contexto: '37 tickets abiertos', medible: 'hoy', frescura: { fuente: 'Desk', edad_h: 4.1 }, ir: 'Ver correos', href: '#/componentes' }),
        tile({ icono: 'clock', etiqueta: 'Horas · septiembre (ejemplo)', valor: 109, unidad: 'h', estado: 'ambar', comparacion: { delta: 71, unidad: ' h', texto: 'sobre las pautadas', mejorSi: 'bajo' }, medible: 'medias', medibleDetalle: 'Con el 52 % de horas imputadas' }),
        tile({ icono: 'globe', etiqueta: 'Posición media (sin dato)', valor: null, contexto: 'Falta conectar SE Ranking a este cliente' }),
      ]), salida));

    const chipsSalida = h('span', { class: 'sub', 'aria-live': 'polite' });
    const chUnico = chipsFiltro({ etiqueta: 'Vista', clave: 'catalogo.vista', opciones: [{ valor: '', texto: 'Todos', cuenta: 66 }, { valor: 'mios', texto: 'Mis clientes', icono: 'persona', cuenta: 12 }, { valor: 'rojo', texto: 'En rojo', icono: 'fire', cuenta: 9, cuentaEstado: 'rojo' }, { valor: 'nuevos', texto: 'Nuevos', icono: 'rocket', cuenta: 16 }], alCambiar: v => { chipsSalida.textContent = `Vista: «${v || 'Todos'}» (se recuerda al volver)`; } });
    const chVarios = chipsFiltro({ multiple: true, etiqueta: 'Servicio', opciones: [{ valor: 'meta', texto: 'Meta', icono: 'target' }, { valor: 'seo', texto: 'SEO', icono: 'globe' }, { valor: 'redes', texto: 'Redes', icono: 'heart' }, { valor: 'crm', texto: 'CRM', icono: 'base' }], alCambiar: v => { chipsSalida.textContent = `Servicios: ${v.join(', ') || 'ninguno'}`; } });
    cont.append(bloque('Chips de filtro y periodo', 'chipsFiltro({ opciones: [{ valor, texto, cuenta, cuentaEstado, icono }], multiple, clave, alCambiar }) · selectorPeriodo({ opciones, valor, clave, alCambiar })',
      chUnico, chVarios, chipsSalida, selectorPeriodo({ clave: 'catalogo', alCambiar: v => { chipsSalida.textContent = `Periodo: ${v}`; } })));

    cont.append(bloque('Pestañas', 'pestanas({ pestanas: [{ id, texto, icono, cuenta, cuentaEstado }], activa, clave, pintar(id, contenedor) }) · teclado ← → Inicio Fin',
      pestanas({ clave: 'catalogo', etiqueta: 'Ficha de ejemplo', pestanas: [
        { id: 'resumen', texto: 'Resumen', icono: 'res', cuenta: 2, cuentaEstado: 'rojo' }, { id: 'contactos', texto: 'Contactos', icono: 'users' },
        { id: 'resultados', texto: 'Resultados', icono: 'target' }, { id: 'web', texto: 'Web y SEO', icono: 'globe' }, { id: 'chat', texto: 'Chat', icono: 'chat' },
        { id: 'trabajo', texto: 'Trabajo', icono: 'check', cuenta: 14, cuentaEstado: 'rojo' }, { id: 'rastro', texto: 'Rastro', icono: 'hist' }],
        pintar: (id, z) => z.append(id === 'contactos'
          ? h('div', { style: { display: 'grid', gap: 'var(--s-6)', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 360px), 1fr))', alignItems: 'start' } },
              botonesContacto({ nombre: 'Ana Ejemplo', telefono: '600 000 000', correo: 'ana@ejemplo.es', fuente: 'ejemplo, número inventado' }),
              botonesContacto({ nombre: 'Ana Ejemplo', telefono: '600 000 000', correo: 'ana@ejemplo.es', modo: 'cabecera' }))
          : vacio({ icono: 'vacio', titulo: `Pestaña «${id}» de ejemplo`, texto: 'Cada módulo pinta aquí su contenido. Cambiar de pestaña es instantáneo.' })) })));

    cont.append(bloque('Selector de cliente y barra de etapas', 'selectorCliente({ clientes: ctx.clientesVisibles, actual, alElegir, detalle, insignia }) · barraEtapas(etapas?, actual)',
      selectorCliente({ clientes: vis, actual: vis[0]?.id, alElegir: c => avisoFlotante(`Cliente elegido: ${c.nombre}`, { icono: 'cli' }) }),
      barraEtapas(null, 1)));

    cont.append(bloque('Estado vacío grande, tabla apilable y lista con icono', 'vacio({ icono, titulo, texto, quien, accion, tono, borde }) · tablaApilable({ columnas, filas, alPulsar }) · listaConIcono([{ icono, texto, extra, href, estado }])',
      h('div', { style: { display: 'grid', gap: 'var(--s-6)', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 360px), 1fr))', alignItems: 'start' } },
        vacio({ icono: 'plug', titulo: 'Este cliente no tiene Search Console conectado', texto: 'Sin la propiedad no hay clics ni búsquedas. Se da acceso a gmb1@rankingonline.es en Search Console.', quien: 'Constanza', borde: true }),
        vacio({ tono: 'celebrar', titulo: 'Bandeja a cero', texto: 'No te queda ningún correo de cliente sin contestar.', borde: true })),
      tablaApilable({
        filas: ctx.clientes.slice(0, 5),
        columnas: [{ clave: 'nombre', titulo: 'Cliente', principal: true, celda: c => h('span', { class: 'celda-cli' }, c.nombre) }, { clave: 'responsable', titulo: 'Account' }, { clave: 'salud', titulo: 'Salud', num: true }],
      }),
      listaConIcono([
        { icono: 'video', texto: 'GAC + Ranking Online (ejemplo)', extra: '23 sept · CRM' },
        { icono: 'mail', estado: 'rojo', texto: 'RV: Tengo problemas para enviar correos (ejemplo)', extra: '20 días sin respuesta' },
      ])));

    cont.append(bloque('Ficha de indicador', 'fichaIndicador({ titulo, valor, unidad, estado, tendencia, umbral, medible, frescura, prueba })',
      h('div', { class: 'rejilla' },
        fichaIndicador({ titulo: 'Ejemplo · verde', valor: '82 %', estado: 'verde', tendencia: { delta: 4, unidad: ' pt', texto: 'frente al mes pasado' }, umbral: 'verde ≥ 80 %', medible: 'hoy', frescura: { fuente: 'ClickUp', edad_h: 0.5 } }),
        fichaIndicador({ titulo: 'Ejemplo · ámbar', valor: 31, unidad: 'h', estado: 'ambar', tendencia: { delta: 6, unidad: ' h', texto: 'frente a ayer', mejorSi: 'bajo' }, medible: 'medias', medibleDetalle: 'Solo el 52 % de horas imputadas', frescura: { fuente: 'Desk', edad_h: 4.1, estado: 'viejo' } }),
        fichaIndicador({ titulo: 'Ejemplo · rojo con prueba', valor: 7, unidad: 'de 16', estado: 'rojo', medible: 'hoy', prueba: { texto: 'Ver las 7', href: '#/en-rojo' } }),
        fichaIndicador({ titulo: 'Ejemplo · todavía no', valor: null, estado: 'gris', medible: 'no', medibleDetalle: 'Google Business Profile sin conectar', frescura: { fuente: 'GBP', estado: 'sin datos' } }))));

    cont.append(bloque('Chip de estado, sello y frescura', 'chipEstado(estado, texto) · selloMedible(medible, detalle) · frescura({fuente, edad_h, estado})',
      h('div', { class: 'fila' }, ['verde', 'ambar', 'rojo', 'gris', 'azul'].map(e => chipEstado(e, e))),
      h('div', { class: 'fila' }, selloMedible('hoy'), selloMedible('medias', 'qué falta'), selloMedible('no')),
      h('div', { class: 'fila' }, (meta.fuentes || []).slice(0, 6).map(f => frescura({ fuente: f.fuente, edad_h: f.edad_h, estado: f.estado }))),
      h('div', { class: 'fila' }, candado(), candado('Solo quien lleva el cliente'))));

    cont.append(bloque('Tarjeta de cliente', 'tarjetaCliente({ nombre, logo, salud, motivo, extra, onAbrir })',
      h('div', { class: 'rejilla' },
        tarjetaCliente({ ...c0, motivo: 'Sin responder', extra: `lleva ${c0.responsable}`, onAbrir: () => ctx.navegar(`en-rojo/${c0.id}`) }),
        tarjetaCliente({ nombre: 'Despacho sin logo (ejemplo)', salud: 72, motivo: 'Al día' }))));

    cont.append(bloque('Lo primero hoy', 'listaLoPrimero([{ motivo, detalle, estado, botones }], { vacio })',
      listaLoPrimero([
        { motivo: 'Ejemplo · Cliente A · Sin responder', detalle: '3 correos; el más antiguo, 5 días', botones: [h('button', { class: 'bt mini', type: 'button' }, 'Responder')] },
        { estado: 'ambar', motivo: 'Ejemplo · Cliente B · Informe sin enviar', detalle: 'Límite: día 5' },
      ]),
      listaLoPrimero([], { vacio: { titulo: 'Bandeja a cero', porque: 'No te queda nada urgente hoy.', celebrar: true } })));

    cont.append(bloque('Tabla densa', 'tablaDensa({ columnas, filas, filtros, buscar, orden, alPulsar, puedePulsar, vacio }) · en móvil se apila',
      tablaDensa({
        filas: ctx.clientes.slice(0, 8),
        buscar: { campos: ['nombre', 'responsable'] },
        filtros: [{ clave: 'responsable', titulo: 'Responsable' }],
        orden: { clave: 'salud', dir: 'asc' },
        columnas: [
          { clave: 'nombre', titulo: 'Cliente', principal: true },
          { clave: 'responsable', titulo: 'Responsable' },
          { clave: 'salud', titulo: 'Salud', num: true },
        ],
      })));

    cont.append(bloque('Línea de tiempo y gráfico de serie', 'lineaTiempo([{ fecha, titulo, detalle, estado }]) · graficoSerie({ puntos, titulo, umbral })',
      h('div', { style: { display: 'grid', gap: 'var(--s-6)', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 360px), 1fr))', alignItems: 'start' } },
        lineaTiempo([
          { fecha: '2026-10-02', titulo: 'Ejemplo · alarma roja', detalle: 'Sin responder', estado: 'rojo' },
          { fecha: '2026-09-15', titulo: 'Ejemplo · reunión', estado: 'verde' },
          { fecha: '2025-12-01', titulo: 'Ejemplo · alta' },
        ]),
        h('div', { class: 'pila', style: { minWidth: '0' } },
          graficoSerie({ titulo: 'Ejemplo · alarmas rojas por día (cifras inventadas)', umbral: { y: 60, texto: 'objetivo' },
            puntos: [88, 91, 97, 102, 95, 90, 84, 79, 81, 72].map((y, i) => ({ x: `2026-09-${String(20 + i).padStart(2, '0')}`, y })) }),
          graficoSerie({ titulo: 'Real · alarmas rojas por día (histórico del panel)', puntos: (meta.historico || []).map(p => ({ x: p.fecha, y: p.rojas })) })))));

    cont.append(bloque('Estado vacío, confirmación y aviso', 'estadoVacio({ titulo, porque, que_hacer, accion, celebrar }) · botonConfirmar({...}) · avisoParcial(texto, {tipo})',
      estadoVacio({ titulo: 'Este cliente aún no tiene objetivo de coste por cita', porque: 'Sin objetivo, el semáforo de publicidad usa la red de seguridad de 100 €.', que_hacer: 'Pídeselo al trafficker en la ficha del alta (D-03).' }),
      h('div', { class: 'fila' },
        botonConfirmar({ texto: 'Marcar hecho', pregunta: '¿Marcar como hecho?', confirmar: 'Sí, hecho', soloLectura: ctx.soloLectura, alConfirmar: () => { ctx.rastro({ accion: 'demo' }); return 'Hecho (demo) · queda en el rastro'; } }),
        botonConfirmar({ texto: 'Quitar asignación', pregunta: '¿Seguro? Se nota en su cartera.', confirmar: 'Sí, quitar', peligro: true, soloLectura: ctx.soloLectura, alConfirmar: () => { throw new Error('ejemplo de fallo de la API'); } })),
      avisoParcial('Con el 52 % de las horas imputadas: orientativo.', { titulo: 'Dato a medias.' }),
      avisoParcial('Esto es una nota informativa.', { tipo: 'info' })));
  },
};

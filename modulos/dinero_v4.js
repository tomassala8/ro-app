// modulos/dinero_v4.js · paneles v4 (3-oct-2026): lo común de los paneles de dinero (Finanzas, Dinero por cliente y, después,
// Panel de dirección y Ventas de RO). No es un módulo (no está en indice.js) y no trae estilos: solo datos de referencia y
// cálculos puros sobre lo que ya llega por ctx.datosModulo(). Nada de datos propios.
//   · FUENTES: las fuentes abiertas y leídas el 3-oct de ../48_BENCHMARK_DASHBOARDS.md (umbrales de mercado y patrones).
//   · UMBRALES: el texto, las fuentes y si colorea, por métrica (48 §3). Los de RO (indicadores.json, decisiones) mandan;
//     los de SaaS o «sin fuente fiable» van con colorea: false (referencia gris).
//   · puenteCuota(): la fuga mensual de la cuota (rebajas, bajas y subidas) sobre el puente de Holded.
//   · puntosPrevisionCaja(): la caja a 90 días (cobros del día 2 y gasto medio repartido), con sus supuestos en texto.

import { h, fmt, enlaceFuente, icono } from '../componentes.js';

export const FUENTES = {
  baker: { fuente: 'David C. Baker', href: 'https://www.linkedin.com/pulse/eight-performance-benchmarks-your-financial-dashboard-david-c-baker', que: 'ocho referencias financieras para agencias' },
  ami: { fuente: 'Agency Management Institute', href: 'https://www.linkedin.com/pulse/metrics-matter-agency-drew-mclellan', que: 'métricas que importan en una agencia' },
  ami_personal: { fuente: 'Agency Management Institute', href: 'https://agencymanagementinstitute.com/video/payroll-ratios-whats-too-low/', que: 'peso del personal sobre el ingreso' },
  parakeeto: { fuente: 'Parakeeto', href: 'https://www.parakeeto.com/blog/measuring-and-improving-your-agencys-profitabilty-the-2023-guide/', que: 'rentabilidad de agencias' },
  scoro: { fuente: 'Scoro', href: 'https://www.scoro.com/blog/agency-metrics/', que: 'métricas de agencia' },
  promethean: { fuente: 'Promethean Research', href: 'https://prometheanresearch.com/how-profitable-are-digital-agencies/', que: 'rentabilidad de agencias digitales 2025' },
  saascapital: { fuente: 'SaaS Capital', href: 'https://www.saas-capital.com/blog-posts/benchmarking-metrics-for-bootstrapped-saas-companies/', que: 'retención en SaaS autofinanciadas 2026' },
  chartmogul_ret: { fuente: 'ChartMogul', href: 'https://chartmogul.com/reports/saas-retention-report/', que: 'informe de retención SaaS' },
  chartmogul_ltv: { fuente: 'ChartMogul', href: 'https://chartmogul.com/saas-metrics/ltv/', que: 'valor de vida ÷ coste de captar' },
  geckoboard: { fuente: 'Geckoboard', href: 'https://www.geckoboard.com/best-practice/kpi-examples/cac-payback-period/', que: 'plazo para recuperar la captación' },
  sakas_conc: { fuente: 'Sakas & Co.', href: 'https://sakasandcompany.com/client-concentration/', que: 'concentración de clientes' },
  sakas_rot: { fuente: 'Sakas & Co.', href: 'https://sakasandcompany.com/client-turnover-rates/', que: 'rotación de clientes en agencias' },
  pmcm: { fuente: 'PMcM', href: 'https://pmcm.es/85-grandes-companias-incumple-plazos-pago-y-financia-parte-costa-pymes-segun-pmcm-linea-advertencias-gobernador-banco-espana/', que: 'plazos de pago en España 2025' },
  productive: { fuente: 'Productive.io', href: 'https://productive.io/blog/employee-utilization/', que: 'utilización en agencias' },
  databox: { fuente: 'Databox', href: 'https://help.databox.com/article/245-overview-visualization-types', que: 'bandas contra objetivo' },
  quickbooks_caja: { fuente: 'QuickBooks', href: 'https://quickbooks.intuit.com/learn-support/en-us/help-article/budget-forecast-reports/use-cash-flow-planner-quickbooks-online/L2l59mIqe_US_en_US', que: 'planificador de caja con mínimo' },
  quickbooks_tramos: { fuente: 'QuickBooks', href: 'https://quickbooks.intuit.com/r/payments/accounts-receivable-aging-report/', que: 'antigüedad de cobros por tramos' },
  chartmogul_mov: { fuente: 'ChartMogul', href: 'https://help.chartmogul.com/article/158-chart-mrr-movements', que: 'movimientos de la cuota' },
  chartmogul_coh: { fuente: 'ChartMogul', href: 'https://help.chartmogul.com/article/161-cohort-analysis', que: 'cohortes en mapa de calor' },
  pigment: { fuente: 'Pigment', href: 'https://kb.pigment.com/docs/waterfall-charts', que: 'cascada de variación' },
  baremetrics: { fuente: 'Baremetrics', href: 'https://baremetrics.com/academy/saas-calculate-mrr', que: 'desglose de la cuota' },
};
const F = k => ({ fuente: FUENTES[k].fuente, href: FUENTES[k].href });

/** Umbrales por métrica (48 §3). texto = lo que se escribe en la tarjeta; colorea: false = referencia gris. */
export const UMBRALES = {
  meses_caja: { texto: 'verde ≥ 2 meses · ámbar 1-2 · rojo < 1 (agencias: 2 meses de gasto fijo)', fuentes: [F('baker'), F('ami')] },
  margen_bruto: { texto: 'verde ≥ 35 % · rojo < 25 % (regla de la app) · agencias: ≥ 50 % del ingreso neto', fuentes: [F('parakeeto'), F('scoro')] },
  margen_neto: { texto: 'beneficio positivo = verde (regla de la app) · agencias digitales: media real 13 %, objetivo 20 %', fuentes: [F('promethean'), F('ami')] },
  peso_equipo: { texto: 'verde ≤ 55 % · ámbar 55-65 % · rojo > 65 % (agencias: 55 % con cargas)', fuentes: [F('ami_personal')] },
  vencido: { texto: 'RO: aviso al account a 30 días, decide Tomás a 60 · rojo con recibos de más de 60 días' },
  dias_cobro: { texto: 'España: máximo legal 60 días entre empresas; media real del sector privado 67 días (2025) · sin dato de agencias', fuentes: [F('pmcm')] },
  cuota_objetivo: { texto: 'RO: 150.000 € en diciembre · contra el plan del mes: < 75 % rojo, 75-99 % ámbar, ≥ 100 % verde', fuentes: [F('databox')] },
  retencion_neta: { texto: 'RO: verde ≥ 90 % · rojo < 85 % · SaaS, no agencias: mediana 103 %', fuentes: [F('saascapital'), F('chartmogul_ret')] },
  perdida_cuota: { texto: 'SaaS (no agencias): pérdida bruta mediana ≈ 0,8 % al mes · sin fuente fiable de agencias', fuentes: [F('saascapital')], colorea: false },
  bajas_mes: { texto: 'agencias de cuota: ≤ 20 % al año (≈ 1,8 % al mes)', fuentes: [F('sakas_rot')] },
  concentracion: { texto: 'el mayor: verde < 20 % · ámbar 20-25 % · rojo > 25 % (ningún cliente por encima del 20 %; Baker: máx. 25 %) · 5 y 10 mayores: sin fuente fiable, no colorean', fuentes: [F('ami'), F('sakas_conc'), F('baker')] },
  cobrada_dia10: { texto: 'RO: verde ≥ 95 % · ámbar 85-95 % · rojo < 85 % (el color sale el día 10)' },
  recuperacion: { texto: 'SaaS: ≤ 12 meses · sin fuente fiable de agencias', fuentes: [F('geckoboard')], colorea: false },
  ltv_cac: { texto: 'SaaS: ≥ 3 veces · sin dato de agencias (suelo razonable)', fuentes: [F('chartmogul_ltv')], colorea: false },
  horas_imputadas: { texto: 'aviso, nunca rojo de cliente: por debajo del 70 % el margen no es fiable · agencias: media 65 % de utilización', fuentes: [F('productive')], colorea: false },
};

/** Estado de color de una métrica con su umbral (solo las que colorean). */
export const ESTADO = {
  meses_caja: v => (v === null || v === undefined ? 'gris' : v >= 2 ? 'verde' : v >= 1 ? 'ambar' : 'rojo'),
  margen_bruto: v => (v === null || v === undefined ? 'gris' : v >= 35 ? 'verde' : v >= 25 ? 'ambar' : 'rojo'),
  peso_equipo: v => (v === null || v === undefined ? 'gris' : v <= 55 ? 'verde' : v <= 65 ? 'ambar' : 'rojo'),
  retencion_neta: v => (v === null || v === undefined ? 'gris' : v >= 90 ? 'verde' : v >= 85 ? 'ambar' : 'rojo'),
  concentracion: v => (v === null || v === undefined ? 'gris' : v < 20 ? 'verde' : v <= 25 ? 'ambar' : 'rojo'),
  cobrada_dia10: v => (v === null || v === undefined ? 'gris' : v >= 95 ? 'verde' : v >= 85 ? 'ambar' : 'rojo'),
  dias_cobro: v => (v === null || v === undefined ? 'gris' : v <= 60 ? 'verde' : 'rojo'),
};

/** fuentesAlPie(claves, { titulo }) · la lista de fuentes al final de la pantalla (cada una con «Ver fuente ↗»). */
export function fuentesAlPie(claves, { titulo = 'Fuentes de los umbrales y de cómo se dibuja' } = {}) {
  const ks = [...new Set(claves)].filter(k => FUENTES[k]);
  if (!ks.length) return null;
  return h('details', { class: 'que-es' },
    h('summary', {}, `${titulo} (${ks.length})`),
    h('ul', { class: 'pila' }, ks.map(k => h('li', {}, `${FUENTES[k].fuente} · ${FUENTES[k].que}: `, enlaceFuente(FUENTES[k].href)))),
    h('p', { class: 'sub' }, 'Abiertas y leídas el 3-oct-2026. Casi todas son de EE. UU. o Reino Unido y muchas de SaaS: solo colorean las que valen para agencias; las demás salen como referencia gris. Los umbrales de RO mandan sobre los de mercado.'));
}

/** Mes 'AAAA-MM' de n meses antes/después. */
export function mesMas(m, n) {
  let [y, mm] = String(m).split('-').map(Number); mm += n;
  y += Math.floor((mm - 1) / 12); mm = ((mm - 1) % 12 + 12) % 12 + 1;
  return `${y}-${String(mm).padStart(2, '0')}`;
}

/**
 * puenteCuota(puente, n = 6) → { meses, rebajas_pct, bajas_pct, subidas_pct, perdida_pct, rebajas_12, bajas_12, subidas_12 }
 *   Media mensual de los n últimos meses de cada movimiento sobre la cuota al empezar el mes (48 §1.3: rebajas 4,0 %, bajas
 *   3,3 %) y euros de los 12 últimos meses (30.940 € de rebajas frente a 20.727 € de bajas).
 */
export function puenteCuota(puente = [], n = 6) {
  const ult = puente.slice(-n), d12 = puente.slice(-12);
  // rebajas y bajas cuentan solo lo que resta (una «baja» positiva es una reactivación); subidas y altas, solo lo que suma
  const val = (x, k) => (k === 'bajadas' || k === 'bajas' ? -Math.min(0, x[k] || 0) : Math.max(0, x[k] || 0));
  const media = k => (ult.length ? ult.reduce((a, x) => a + val(x, k) / (x.ini || 1), 0) / ult.length * 100 : null);
  const suma = k => d12.reduce((a, x) => a + val(x, k), 0);
  const r = media('bajadas'), b = media('bajas'), s = media('subidas');
  return { meses: ult.map(x => x.m), rebajas_pct: r, bajas_pct: b, subidas_pct: s, perdida_pct: r + b,
    rebajas_12: suma('bajadas'), bajas_12: suma('bajas'), subidas_12: suma('subidas'), altas_12: suma('altas') };
}

/**
 * puntosPrevisionCaja({ caja, fecha, gastoMedio, cobroPendiente, cuotaMes, tasaCobro, dias = 90 }) → { puntos, eventos, supuestos }
 *   Caja de hoy − gasto medio repartido cada día + los cobros de cuota: lo emitido y aún sin cobrar entra el día 6 del mes en
 *   curso (el cargo SEPA es el día 2 y tarda en verse en el banco) y, los meses siguientes, la cuota recurrente el día 5; las dos
 *   por la parte que se cobró en la primera semana del último mes (tasaCobro). Sin IVA. Falta el calendario real de nóminas y
 *   proveedores (48 §3): por eso el gasto va repartido.
 */
export function puntosPrevisionCaja({ caja, fecha, gastoMedio, cobroPendiente, cuotaMes, tasaCobro = 1, dias = 90 } = {}) {
  if (!Number.isFinite(caja) || !Number.isFinite(gastoMedio) || !fecha) return { puntos: [], eventos: [], supuestos: [] };
  const diario = (gastoMedio * 12) / 365;
  const ini = new Date(`${fecha}T12:00:00Z`);
  const puntos = [], eventos = [];
  let saldo = caja;
  for (let i = 0; i < dias; i++) {
    const d = new Date(ini.getTime() + i * 864e5);
    const f = d.toISOString().slice(0, 10);
    const dia = d.getUTCDate();
    if (i > 0) saldo -= diario;
    const mismoMes = f.slice(0, 7) === fecha.slice(0, 7);
    if (mismoMes && dia === Math.max(6, Number(fecha.slice(8, 10)) + 1) && cobroPendiente) {
      const v = cobroPendiente * tasaCobro; saldo += v;
      eventos.push({ fecha: f, texto: `Entran las cuotas emitidas este mes: ${fmt.eur(v)} (${fmt.pct(tasaCobro * 100)} de ${fmt.eur(cobroPendiente)})` });
    } else if (!mismoMes && dia === 5 && cuotaMes) {
      const v = cuotaMes * tasaCobro; saldo += v;
      eventos.push({ fecha: f, texto: `Cobro de la cuota del mes: ${fmt.eur(v)} (${fmt.pct(tasaCobro * 100)} de ${fmt.eur(cuotaMes)})` });
    }
    puntos.push({ fecha: f, saldo: Math.round(saldo) });
  }
  const supuestos = [
    `Caja de hoy: ${fmt.eur(caja)} (Holded en vivo).`,
    `Gasto: ${fmt.eur(gastoMedio)} al mes repartido cada día (el gasto medio de enero a agosto, con los dólares convertidos). Falta el calendario real de nóminas y proveedores.`,
    `Cobros: lo emitido y aún sin cobrar este mes (${fmt.eur(cobroPendiente)}) y, después, la cuota recurrente firmada (${fmt.eur(cuotaMes)}) el día 5, por la parte que se cobró en la primera semana de septiembre (${fmt.pct(tasaCobro * 100)}).`,
    'Sin IVA (el IVA que entra con cada cobro se paga a Hacienda cada trimestre) y sin altas nuevas.',
  ];
  return { puntos, eventos, supuestos };
}

/** notaSupuestos(supuestos) · plegado «Cómo se calcula» con la lista de supuestos de una estimación. */
export function notaSupuestos(supuestos = [], titulo = 'Cómo se calcula esta previsión') {
  if (!supuestos.length) return null;
  return h('details', { class: 'que-es' }, h('summary', {}, titulo), h('ul', { class: 'pila' }, supuestos.map(t => h('li', { class: 'sub' }, t))));
}

/** cabeceraPorque(texto) · separador «El porqué» entre las cifras y los gráficos (48 §4: cifra · tarjetas · el porqué). */
export function separador(texto, ico = 'grafico') {
  return h('div', { class: 'titulo-seccion' }, icono(ico, { clase: 's' }), texto);
}

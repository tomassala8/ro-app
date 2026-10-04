// Proyecciones de lectura: sólo datos ya autorizados, sin consultas o umbrales de rendimiento nuevos.
export const numeroMedido = v => typeof v === 'number' && Number.isFinite(v) && v >= 0 ? v : null;
export const conteoMedido = v => numeroMedido(v) !== null && Number.isInteger(v) ? v : null;
export function fechaMedida(v) {
  if (typeof v !== 'string') return null;
  const s = v.slice(0,10), m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(s);
  if (!m) return null;
  const d = new Date(`${s}T12:00:00Z`);
  return Number.isFinite(+d) && d.toISOString().slice(0,10) === s ? s : null;
}
export function rachaSinLeads(serie, hasta, hoy) {
  const fin = fechaMedida(hasta), actual = fechaMedida(hoy);
  if (!fin || !actual || fin >= actual || !Array.isArray(serie)) return null;
  const porDia = new Map();
  for (const x of serie) {
    const dia = fechaMedida(x?.d), n = conteoMedido(x?.leads_meta);
    if (!dia) continue;
    if (porDia.has(dia) && porDia.get(dia) !== n) return null; // replay contradictorio
    porDia.set(dia,n);
  }
  let dia=fin, n=0;
  while (porDia.has(dia) && porDia.get(dia) === 0) {
    n++;
    const d=new Date(`${dia}T12:00:00Z`);d.setUTCDate(d.getUTCDate()-1);dia=d.toISOString().slice(0,10);
  }
  if (!porDia.has(fin) || porDia.get(fin) === null) return null;
  return { dias:n, hasta:fin, completa:porDia.has(dia) && porDia.get(dia) !== null && porDia.get(dia) > 0 };
}
export function panelPaid(c,d,hoy) {
  const hasta=fechaMedida(d?.datos_hasta), actual=fechaMedida(hoy);
  const cuentaError=!!c?.cuenta_meta?.error;
  const datoVigente=!!hasta && !!actual && (new Date(`${actual}T12:00:00Z`) - new Date(`${hasta}T12:00:00Z`)) === 864e5;
  const serie=cuentaError ? null : rachaSinLeads(c.serie,hasta,actual);
  const objetivo=c.dinero && c.objetivo?.cargado === true && c.objetivo?.vigente !== false ? numeroMedido(c.objetivo?.cpl_objetivo) : null;
  const obj=objetivo && fechaMedida(c.objetivo?.cuando) && fechaMedida(c.objetivo.cuando) <= actual ? objetivo : null;
  const real=c.dinero && !cuentaError ? numeroMedido(c.cpl_resumen?.ref) : null;
  const creativos=Array.isArray(c.anuncios?.anuncios) ? c.anuncios.anuncios : null;
  const errorCreativos=(c.anuncios?.errores || []).length > 0;
  const revisar=creativos && !errorCreativos ? creativos.filter(a => a.vigilar || a.cansada).length : null;
  let accion=cuentaError ? 'Revisar lectura de la cuenta Meta antes de decidir.'
    : !datoVigente ? 'Actualizar la lectura de Paid; estos datos no son el último día cerrado.'
    : obj === null && c.dinero ? 'Confirmar y registrar el objetivo de CPL propio con su fecha.'
    : serie?.dias > 0 ? 'Revisar campañas, formulario y recepción del último tramo sin leads registrados.'
    : revisar > 0 ? 'Revisar muestra y ventanas comparables de los creativos señalados antes de cambiarlos.'
    : 'Revisar la cuenta y dejar el próximo cambio documentado.';
  return { hasta, datoVigente, cuentaError, objetivo:obj, real, racha:serie, creativos:revisar,
    fechaCreativos:fechaMedida(d?.anuncios_generado), accion,
    objetivoEstado:!c.dinero?'reservado':obj===null?'sin_confirmar':'registrado' };
}
export function panelSeo(f, meta) {
  const palabras=Array.isArray(f.informe15)?f.informe15:[];
  const valida=v=>conteoMedido(v)!==null && v>0;
  const organic=palabras.filter(k=>valida(k.hoy)).length, maps=palabras.filter(k=>valida(k.mapa)).length;
  const trafico=conteoMedido(f.clics?.mes), antes=conteoMedido(f.clics?.mes_ant);
  const hasta=fechaMedida(f.clics?.hasta), sr=fechaMedida(f.seranking?.ultima || meta?.seranking?.dia_dato);
  const paginas=Array.isArray(f.gsc?.paginas)?f.gsc.paginas.length:null;
  return { consultas:palabras.length, organico:organic || null, maps:maps || null, trafico, antes, hasta, sr, paginas,
    accion:trafico===null?'Verificar acceso y periodo de Search Console antes de evaluar tráfico.'
      : antes!==null && trafico<antes?'Revisar páginas y consultas de los 28 días que han perdido clics; contrastar el objetivo.'
      :'Confirmar páginas, servicios y ciudad objetivo antes de juzgar las consultas provisionales.' };
}
export function panelWeb(w) {
  const ms=numeroMedido(w.comprobacion?.ms), plugins=conteoMedido(w.modular?.actualizaciones?.plugins);
  const criticas=conteoMedido(w.modular?.vulnerabilidades?.criticas), altas=conteoMedido(w.modular?.vulnerabilidades?.altas);
  const incidencia=(w.modular?.incidencias || []).find(i=>i.que_hacer);
  const accion=incidencia?.que_hacer || (w.comprobacion?.error?'Contrastar la respuesta desde fuera de RO antes de declarar caída.'
    : plugins>0?'Revisar compatibilidad y copia antes de actualizar los plugins pendientes.'
    : 'Revisar la medición de rendimiento y documentar el siguiente mantenimiento.');
  return { ms, plugins, criticas, altas, fechaMonitor:fechaMedida(w.comprobacion?.hora), fechaModular:fechaMedida(w.modular?.detalle_leido), accion };
}

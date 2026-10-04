// Política pura: nunca concede permisos ni convierte un snapshot en cumplimiento.
const gris258 = razon => ({estado:'gris',clasificacion:'desconocido',razon,cumplimiento:null});
const finito258 = x => typeof x === 'number' && Number.isFinite(x) && x >= 0;
function instante258(x) {
  if (typeof x !== 'string' || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{3})?Z$/.test(x)) return null;
  const n=Date.parse(x); return Number.isFinite(n) && new Date(n).toISOString() === (x.includes('.')?x:x.replace('Z','.000Z')) ? n : null;
}
export function evaluarSemaforo258(evidencia,regla,ahora) {
  const e=evidencia,r=regla,now=instante258(ahora);
  if (!e || !r || now === null || e.autorizada !== true) return gris258('Sin evidencia autorizada vigente.');
  if (typeof e.fuente !== 'string' || !e.fuente.trim() || typeof r.fuente !== 'string' || !r.fuente.trim() || typeof r.id !== 'string' || !r.id.trim()) return gris258('Falta procedencia de medición o criterio.');
  const fecha=instante258(e.fecha);
  if (fecha === null || fecha > now || !finito258(r.max_edad_horas) || now-fecha > r.max_edad_horas*3600000) return gris258('Fecha inválida, futura o fuera de la vigencia definida.');
  if (!['completa','parcial'].includes(e.cobertura) || e.verificacion !== 'observada' || !['conteo','medida','ratio'].includes(e.tipo)) return gris258('Cobertura o naturaleza de la evidencia sin acreditar.');
  if (typeof r.periodo !== 'string' || !r.periodo || e.periodo !== r.periodo) return gris258('La ventana medida no coincide con el criterio.');
  if (typeof e.alcance !== 'string' || !e.alcance || e.alcance !== r.alcance || e.tipo !== r.tipo) return gris258('Alcance o unidad del criterio incompatible.');
  if (e.cobertura === 'completa' && e.exhaustividad_confirmada !== true) return gris258('La etiqueta completa no demuestra exhaustividad.');
  let valor=e.valor;
  if (e.tipo === 'ratio') {
    if (e.cobertura !== 'completa' || !finito258(e.numerador) || !finito258(e.denominador) || e.denominador === 0 || e.numerador > e.denominador || !Number.isSafeInteger(e.numerador) || !Number.isSafeInteger(e.denominador) || typeof e.cohorte !== 'string' || !e.cohorte || e.cohorte !== e.cohorte_denominador || e.periodo !== e.periodo_denominador) return gris258('Ratio sin denominador, cohorte o cobertura compatible.');
    valor=e.numerador/e.denominador;
  } else if (!finito258(valor) || (e.tipo === 'conteo' && !Number.isSafeInteger(valor))) return gris258('Valor ausente o inválido; no se sustituye por cero.');
  if (!['lte','gte'].includes(r.operador) || !finito258(r.limite) || (r.aviso_desde !== undefined && !finito258(r.aviso_desde))) return gris258('Criterio inválido o no compatible.');
  if ((e.tipo === 'conteo' && (!Number.isSafeInteger(r.limite) || (r.aviso_desde !== undefined && !Number.isSafeInteger(r.aviso_desde)))) || (r.aviso_desde !== undefined && (r.operador === 'lte' ? r.aviso_desde > r.limite : r.aviso_desde < r.limite))) return gris258('Bandas del criterio incoherentes.');
  const completo=e.cobertura === 'completa';
  const inferior = completo || e.acotacion === 'inferior';
  const exceso=r.operador === 'lte' ? inferior && valor > r.limite : completo && valor < r.limite;
  const aviso=r.aviso_desde !== undefined && (r.operador === 'lte' ? inferior && valor >= r.aviso_desde : completo && valor <= r.aviso_desde);
  if (r.autoridad !== 'confirmada') {
    if (r.autoridad === 'referencia_visual' && (exceso || aviso)) return {estado:'ambar',clasificacion:'revision',razon:'Señal de revisión según referencia visual; no acredita incumplimiento.',cumplimiento:null};
    return gris258('Criterio pendiente de confirmar para esta ventana y alcance.');
  }
  if (exceso) return {estado:'rojo',clasificacion:'exceso_observado',razon:completo?'Incumplimiento del criterio confirmado en la ventana medida.':'El mínimo observado ya supera el límite confirmado; la copia sigue siendo parcial.',cumplimiento:false};
  if (aviso) return {estado:'ambar',clasificacion:'aviso',razon:'Zona de aviso del criterio confirmado.',cumplimiento:null};
  if (!completo) return gris258('Copia parcial: la ausencia de exceso observado no acredita cumplimiento.');
  return {estado:'verde',clasificacion:'cumplimiento',razon:'Criterio confirmado y cobertura completa de la ventana.',cumplimiento:true};
}

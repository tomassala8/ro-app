// Baseline exacto del agregador antes684; sólo funciones puras.
const lista = v => Array.isArray(v) ? v : [];
const numero = v => typeof v === 'number' && Number.isFinite(v) && v >= 0 ? v : null;
export function resumirAccountsControl(filas) {
  const grupos = new Map();
  for (const fila of lista(filas)) {
    const id = fila.account_id || null;
    if (!grupos.has(id)) grupos.set(id, []);
    grupos.get(id).push(fila);
  }
  return [...grupos].map(([account_id, rows]) => {
    const agregar = (key, campo) => {
      const medidas = rows.map(r => r[key]?.medicion?.[campo]).filter(v => numero(v) !== null);
      return {valor:medidas.length ? medidas.reduce((a,b)=>a+b,0) : null, medidos:medidas.length, sin_dato:rows.length-medidas.length};
    };
    const horasRows = rows.filter(r => numero(r.horas?.medicion?.total) !== null);
    const periodos = [...new Set(horasRows.map(r=>r.horas.medicion.periodo))];
    const horas = periodos.length === 1 ? {...agregar('horas','total'),periodo:periodos[0]} : {valor:null,medidos:0,sin_dato:rows.length,periodo:null};
    return {account_id,clientes:rows.length,asignaciones_confirmadas:rows.filter(r=>r.owner_confirmado).length,asignaciones_por_confirmar:rows.filter(r=>r.account_id&&!r.owner_confirmado).length,contacto_sin_dato:rows.length,
      tickets:agregar('tickets','total'),tickets24:agregar('tickets','entre_24_48'),tickets48:agregar('tickets','mas_48'),
      revisiones:agregar('revisiones','total'),revisiones48:agregar('revisiones','mas_48'),horas,
      reuniones15:rows.filter(r=>r.reuniones?.valor==='Trafficker · 15 días').length,
      reuniones_revisar:rows.filter(r=>r.reuniones?.valor==='Trafficker · 15 días' && r.reuniones.estado==='ambar').length,
      reuniones_confirmar:rows.filter(r=>r.reuniones?.valor==='Trafficker · 15 días' && r.reuniones.estado==='gris').length,
      reuniones_historicas:rows.filter(r=>r.reuniones?.fuente==='Zoom/CRM/Fathom').length,
      presupuesto_sin_dato:rows.length};
  });
}

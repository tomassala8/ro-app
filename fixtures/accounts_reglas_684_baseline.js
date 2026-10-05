// Función exacta anterior684; auxiliares de celda del mismo módulo.
const numero=v=>typeof v==='number'&&Number.isFinite(v)&&v>=0;
const sinDato=detalle=>({valor:'—',estado:'gris',detalle:detalle||'Sin evidencia suficiente en las fuentes autorizadas.'});
const observacion=(valor,detalle,estado='gris')=>({valor:String(valor),estado,detalle});
export function agregar263(rows,fn,detalle) {
  const xs=rows.map(fn),medidas=xs.filter(x=>numero(x));
  return medidas.length?observacion(medidas.reduce((a,b)=>a+b,0),`${detalle} ${medidas.length}/${rows.length} clientes medidos; el resto sin dato. Copia parcial.`):sinDato(detalle+' Ningún cliente tiene medición acreditada.');
}


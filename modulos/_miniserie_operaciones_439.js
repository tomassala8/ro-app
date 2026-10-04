//439 · geometría pequeña para serie329 validada, sin IO ni referencias legacy.
export function modeloMiniserie439(r){
 if(r?.estado!=='comparacion_observada'||!['rojas','revision48'].includes(r.id)||!Array.isArray(r.serie)||r.serie.length<2||r.serie.length>12||r.unidad!==({rojas:'alarmas',revision48:'tareas'})[r.id])return null;
 const serie=r.serie;const stamps=serie.map(p=>typeof p?.corte==='string'?Date.parse(p.corte):NaN);
 if(serie.some((p,i)=>!Number.isSafeInteger(p?.valor)||p.valor<0||!Number.isFinite(stamps[i])||(i>0&&stamps[i]<=stamps[i-1])))return null;
 const ultimo=serie.at(-1),previo=serie.at(-2);
 if(ultimo.valor!==r.actual||previo.valor!==r.anterior||ultimo.corte!==r.cortes?.actual||previo.corte!==r.cortes?.anterior||r.actual-r.anterior!==r.delta)return null;
 const lo=Math.min(...serie.map(p=>p.valor)),hi=Math.max(...serie.map(p=>p.valor)),range=hi-lo;
 const puntos=serie.map((p,i)=>({x:4+88*(stamps[i]-stamps[0])/(stamps.at(-1)-stamps[0]),y:range?22-18*((p.valor-lo)/range):13}));
 const segmentos=puntos.slice(1).map((p,i)=>{const a=puntos[i],dx=p.x-a.x,dy=p.y-a.y;return {x:a.x,y:a.y,largo:Math.hypot(dx,dy),angulo:Math.atan2(dy,dx)*180/Math.PI};});
 const detalle=`${serie.length} cortes compatibles · ${r.unidad}${r.parcial?' · copia parcial':''}. `+serie.map(p=>`${p.corte}: ${p.valor}`).join('; ')+`. Variación última ${r.delta>0?'+':''}${r.delta}; no acredita ejecución ni cumplimiento.`;
 return {puntos,segmentos,detalle};
}
export function pintarMiniserie439(h,r,vigente){
 const m=modeloMiniserie439(r);if(!m||vigente?.()===false)return null;
 return h('span',{'data-miniserie-439':r.id,role:'img','aria-label':m.detalle,title:m.detalle,style:{display:'inline-block',position:'relative',width:'96px',height:'26px',verticalAlign:'middle',marginRight:'8px'}},
  ...m.segmentos.map(s=>h('i',{'aria-hidden':'true',style:{position:'absolute',left:s.x+'px',top:s.y+'px',width:s.largo+'px',height:'2px',background:'#68708a',transform:`rotate(${s.angulo}deg)`,transformOrigin:'0 0'}})),
  ...m.puntos.map(p=>h('i',{'aria-hidden':'true',style:{position:'absolute',left:(p.x-2)+'px',top:(p.y-2)+'px',width:'4px',height:'4px',borderRadius:'50%',background:'#68708a'}})));
}

// Referencia económica del artifact: pauta mensual × laborables del rango / 21.
// Recibe sólo una pauta ya autorizada; no lee importes ni carga datos.
const fecha306=s=>typeof s==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(s)&&Number.isFinite(+new Date(s+'T00:00:00Z'))&&new Date(s+'T00:00:00Z').toISOString().slice(0,10)===s;
const numero306=n=>typeof n==='number'&&Number.isFinite(n)&&n>=0;
export function pautaProporcional306(p,r,hoy,m){
 if(!p||p.origen!=='referencia_economica'||p.presupuesto_confirmado!==false||!numero306(p.horas)||!fecha306(hoy)||!fecha306(r?.desde)||!fecha306(r?.hasta)||r.desde>r.hasta||r.hasta>hoy||r.desde.slice(0,7)!==p.periodo||r.hasta.slice(0,7)!==p.periodo)return null;
 let laborables=0,d=new Date(r.desde+'T00:00:00Z'),fin=new Date(r.hasta+'T00:00:00Z');
 while(d<=fin){if(d.getUTCDay()>0&&d.getUTCDay()<6)laborables++;d.setUTCDate(d.getUTCDate()+1);}
 const horas=p.horas*laborables/21;
 return {...p,mensual_ref:p.horas,laborables,horas,porcentaje:m?.periodo===p.periodo&&numero306(m.valor)&&horas>0?m.valor/horas*100:null,
 detalle:`Referencia del artifact: ${p.horas} h mensuales × ${laborables} laborables / 21. ${r.desde} → ${r.hasta}. No considera festivos, jornada ni presupuesto contractual; horas observadas parciales.`};
}

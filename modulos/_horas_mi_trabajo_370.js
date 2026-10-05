// Sumas observadas de una copia parcial; ausencia no es cero ni ausencia de trabajo.
const numero370=v=>typeof v==='number'&&Number.isFinite(v)&&v>=0;
export function horasDiaTrabajo370(E,pid,dia){
 const x=E.V.dias?.[pid]?.[dia],typed=x&&Object.hasOwn(x,'cu_observado')&&Object.hasOwn(x,'app_observado');
 // Legacy app=0 era un relleno del GET: sólo un flag explícito acredita RO cero.
 const cu=numero370(x?.cu)&&(typed?x.cu_observado===true:x.cu>0)?x.cu:null;
 const app=numero370(x?.app)&&(typed?x.app_observado===true:x.app>0)?x.app:null;
 const valores=(E.local||[]).filter(y=>y.campo==='horas'&&y.dia===dia&&y.quien===pid&&numero370(y.minutos)).map(y=>y.minutos/60);
 const pendientes=valores.reduce((s,y)=>s+y,0),roTotal=(app??0)+pendientes;
 const ro=(app!==null||valores.length>0)&&numero370(roTotal)?roTotal:null;
 const invalido=x?.cu_invalido===true||x?.app_invalido===true||[x?.cu,x?.app].some(v=>v!==null&&v!==undefined&&!numero370(v));
 const sum=(cu??0)+(ro??0),overflow=invalido||!numero370(pendientes)||!numero370(roTotal)||!numero370(sum)||x?.app_invalido===true;
 const observado=cu!==null||ro!==null;
 return {valor:observado&&!overflow?sum:null,cu,ro,parcial:true,datos_invalidos:overflow};
}
export function textoHorasTrabajo370(x){
 if(x.valor===null)return x.datos_invalidos?'Suma pendiente de verificar':'Sin registros en la copia';
 if(x.valor>0&&x.valor<0.1)return '<0,1 h observadas';
 return `${x.valor>0?'≥ ':''}${x.valor.toLocaleString('es-ES',{maximumFractionDigits:1})} h observadas`;
}

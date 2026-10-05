const MAX=5*1024*1024;
const MIME='application/vnd.openxmlformats-officedocument.wordprocessingml.document';

function identidad(ctx){return JSON.stringify([ctx.real?.id || '',ctx.persona?.id || '']);}

function puerta(ctx,cid,nodo,firma){
  if((firma!==undefined && identidad(ctx)!==firma) || !ctx.servidor || (ctx.vigente && !ctx.vigente()) || (nodo && !nodo.isConnected) || !ctx.clientes?.some(c=>c.id===cid) || ctx.ver({tipo:'cliente_detalle',cliente_id:cid}).ok!==true) throw new Error('La pantalla o los permisos han cambiado. Vuelve al informe antes de descargar.');
}

// Transporte binario con la misma identidad/cookie de sesión que las lecturas JSON.
export async function obtenerWord(ctx,cid,pid,nodo,fetcher=fetch){
  const firma=identidad(ctx);
  puerta(ctx,cid,nodo,firma);
  if(!/^[a-zA-Z0-9_-]{1,100}$/.test(cid) || !/^(?:\d{4}-\d{2}|u30|trim)$/.test(pid)) throw new Error('Selecciona un cliente y periodo exactos.');
  const r=await fetcher(`/api/informes/word?cliente_id=${encodeURIComponent(cid)}&periodo_id=${encodeURIComponent(pid)}`,{
    method:'GET',cache:'no-store',credentials:'same-origin',redirect:'error',
    headers:{'X-RO-App':'1','X-RO-Yo':ctx.real.id,...(ctx.persona.id!==ctx.real.id?{'X-RO-Como':ctx.persona.id}:{})}});
  puerta(ctx,cid,nodo,firma);
  if(!r.ok){const d=await r.json().catch(()=>({}));puerta(ctx,cid,nodo,firma);throw new Error(typeof d.error==='string'?d.error:'No se ha podido preparar el Word.');}
  if(r.headers.get('Content-Type')?.split(';')[0]!==MIME) throw new Error('La respuesta no es un documento Word válido.');
  const length=r.headers.get('Content-Length');
  if(length!==null && (!/^\d+$/.test(length)||+length>MAX)) throw new Error('El documento supera el tamaño permitido.');
  const lector=r.body?.getReader();if(!lector) throw new Error('No se puede comprobar la descarga en este navegador.');
  const partes=[];let bytes=0;
  try{
    while(true){const {done,value}=await lector.read();puerta(ctx,cid,nodo,firma);if(done)break;bytes+=value.byteLength;if(bytes>MAX)throw new Error('El documento supera el tamaño permitido.');partes.push(value);}
  }catch(e){await lector.cancel().catch(()=>{});throw e;}
  const blob=new Blob(partes,{type:MIME}),magic=new Uint8Array(await blob.slice(0,4).arrayBuffer());
  puerta(ctx,cid,nodo,firma);
  if(magic[0]!==80||magic[1]!==75||magic[2]!==3||magic[3]!==4)throw new Error('El archivo recibido no tiene el formato Word esperado.');
  return blob;
}

// Un enlace visible conserva el gesto del usuario, incluso si el navegador
// bloquea descargas iniciadas automáticamente después de una consulta asíncrona.
export function presentarDescargaWord(ctx,cid,pid,nodo,blob){
  const firma=identidad(ctx);puerta(ctx,cid,nodo,firma);
  const url=URL.createObjectURL(blob),enlace=document.createElement('a');
  enlace.href=url;enlace.download=`informe-${cid}-${pid}.docx`;
  enlace.className='bt pri';enlace.textContent='Guardar el Word preparado';
  let disponible=true;
  const retirar=()=>{if(!disponible)return;disponible=false;URL.revokeObjectURL(url);enlace.removeAttribute('href');enlace.removeAttribute('download');enlace.textContent='Enlace caducado · prepara el Word de nuevo';};
  enlace.addEventListener('click',e=>{try{if(!disponible)throw new Error('Enlace caducado.');puerta(ctx,cid,nodo,firma);}catch(_){e.preventDefault();retirar();}});
  nodo.replaceChildren(enlace);
  const reloj=setTimeout(retirar,60000);
  return ()=>{clearTimeout(reloj);retirar();};
}

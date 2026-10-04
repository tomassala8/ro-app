import {ambitoViernes347} from './_viernes_accounts_347.js';
import {accountFuego346} from './_account_fuegos_346.js';
// El account actual presenta la incidencia; nunca prueba quién la originó.
export const ambitoRepartir352=ctx=>ambitoViernes347(ctx);
export function atribuirReparto352(ctx,filas){
 const ambito=ambitoRepartir352(ctx);if(!ambito)return [];
 const clientes=new Map(ambito.clientes.map(c=>[c.id,c]));
 return (Array.isArray(filas)?filas:[]).filter(r=>clientes.has(r?.cliente_id)).map(r=>{
  const owner=accountFuego346(ctx,clientes.get(r.cliente_id));
  return {...r,account_id:owner.id,account_texto:owner.texto,account_confirmado:owner.confirmado};
 });
}

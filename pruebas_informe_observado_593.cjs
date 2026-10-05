// Ejecuta el modelo y renderer reales con el harness DOM existente, sólo fixtures.
const fs593=require('fs'),path593=require('path');
let fuente593=fs593.readFileSync(path593.join(__dirname,'pruebas_operaciones_accounts_263.cjs'),'utf8');
fuente593=fuente593.replace('prepararAccounts263,renderAccounts263,KPIS263','informe263,prepararAccounts263,renderAccounts263,KPIS263');
const extras593=String.raw`
 const doc593=()=>({informes:{_meta:{generado:'2026-10-03T10:00:00Z'},filas:[{cliente_id:'c1',mes:'2026-09',estado:'enviado',account_id:'a1',enviado:{fecha:'2026-10-02',ticket:'42',url:'https://desk.zoho.eu/support/tickets/42',asunto:'Informe mensual septiembre',pdf:true,metodo:'Desk en vivo'}}]}});
 const medir593=x=>informe263(x,'c1','2026-10-03');
 check('593 fecha sola antes acreditaba envío: ahora registro por contrastar',()=>{const x=doc593();x.informes.filas[0].enviado={fecha:'2026-10-02'};const z=medir593(x);assert.equal(z.medicion,undefined);assert.match(z.valor,/Registro/);assert.match(z.detalle,/por contrastar/);assert.equal(z.estado,'gris');});
 check('593 salida Desk mensual observada positiva, sin autor ni SLA',()=>{const z=medir593(doc593());assert.equal(z.valor,'1 obs.');assert.equal(z.medicion.observados,1);assert.equal(z.medicion.autor,null);assert.equal(z.medicion.cumplimiento,null);assert.equal(z.estado,'gris');assert.match(z.detalle,/ticket 42/);});
 for(const [caso,mutar] of [
 ['preparado',r=>r.estado='hecho'],['programado',r=>r.estado='programado'],['manual legado',r=>r.enviado.metodo='verificado a mano el 2-oct (panel)'],
 ['sin prueba',r=>delete r.enviado.url],['URL ajena',r=>r.enviado.url='https://evil.test/42'],['URL con credencial',r=>r.enviado.url='https://u:p@desk.zoho.eu/42'],
 ['sin ticket',r=>delete r.enviado.ticket],['sin tipo mensual',r=>r.enviado.asunto='Otro mensaje'],['semanal',r=>r.enviado.asunto='Informe semanal septiembre'],['mes discordante',r=>r.enviado.asunto='Informe mensual agosto'],
 ['fecha futura',r=>r.enviado.fecha='2026-10-04'],['fecha posterior lectura',r=>r.enviado.fecha='2026-10-03'],['calendario imposible',r=>r.enviado.fecha='2026-09-31'],['periodo ausente',r=>delete r.mes]]){
  check('593 no cuenta '+caso,()=>{const x=doc593();mutar(x.informes.filas[0]);if(caso==='fecha posterior lectura')x.informes._meta.generado='2026-10-02T10:00:00Z';const z=medir593(x);assert.equal(z.medicion,undefined);assert.notEqual(z.valor,'0');});
 }
 check('593 filas duplicadas y cliente ajeno sin ganador',()=>{const x=doc593();x.informes.filas.push({...x.informes.filas[0]});assert.equal(medir593(x).valor,'—');x.informes.filas=[{...x.informes.filas[0],cliente_id:'otro'}];assert.equal(medir593(x).valor,'—');});
 check('593 autor histórico distinto del account no se atribuye',()=>{const x=doc593();x.informes.filas[0].enviado.autor_id='historico';const z=prepararAccounts263(ctx(),x).rows[0].kpis[0];assert.equal(z.medicion.autor,null);assert.doesNotMatch(z.detalle,/historico/);});
 for(const [caso,mutar] of [['ACT',c=>c.clientes[0].activo_confirmado=false],['permiso',c=>c.ver=()=>({ok:false})],['vista',c=>c.persona.puestos=['seo']],['duplicado',c=>c.clientes.push({...c.clientes[0]})]])check('593 modelo actual niega '+caso,()=>{const c=ctx();mutar(c);assert.equal(prepararAccounts263(c,doc593()).rows.length,0);});
`;
const punto593=' const d=prepararAccounts263(ctx(),docs);';
if(!fuente593.includes(punto593)||!fuente593.includes('informe263,prepararAccounts263'))throw Error('Harness cambió: adaptar sin omitir pruebas');
fuente593=fuente593.replace(punto593,extras593+'\n'+punto593);
new Function('require','__dirname',fuente593)(require,__dirname);

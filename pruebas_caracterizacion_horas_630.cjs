//630→631: caracterización histórica actualizada para exigir el mínimo corregido.
const fs630=require('fs');
const prefix630=fs630.readFileSync(__dirname+'/pruebas_operaciones_equipo_262.cjs','utf8').split('(async()=>{')[0];
const bands630=fs630.readFileSync(__dirname+'/pruebas_bandas_horas_381.cjs','utf8');
const history630=bands630.slice(bands630.indexOf('function dto381('),bands630.indexOf('(async()=>{',bands630.indexOf('function dto381(')));
new Function('require','__dirname',prefix630+'\n'+history630+String.raw`
(async()=>{
const x=ctx381([1.06,null,null,null,null]),n=new N('main');await c.renderEquipo262(n,x,'horas');all(n,z=>z.tag==='button'&&text(z)==='Semana pasada')[0].events.click();
const row=all(n,z=>z.tag==='tbody')[0].children[0],cell=row.children[1];
assert.equal(text(cell),'≥1');assert(Number(text(cell).slice(1).replace(',','.'))<=1.06);assert(cell.children[0].attrs.title.includes('parcial'));
console.log('FIX631: valor parcial1.06 mostrado≥1; no eleva el límite inferior.');
const y=ctx381([1,null,null,null,null]),control=new N('main');await c.renderEquipo262(control,y,'horas');all(control,z=>z.tag==='button'&&text(z)==='Semana pasada')[0].events.click();assert.equal(text(all(control,z=>z.tag==='tbody')[0].children[0].children[1]),'≥1');
console.log('CONTROL630: entero explícito1 mantiene≥1. Control de enteros conservado.');
})().catch(e=>{console.error(e);process.exitCode=1;});
`)(require,__dirname);

const fs631=require('fs');
const prefix631=fs631.readFileSync(__dirname+'/pruebas_operaciones_equipo_262.cjs','utf8').split('(async()=>{')[0];
const bands631=fs631.readFileSync(__dirname+'/pruebas_bandas_horas_381.cjs','utf8');
const history631=bands631.slice(bands631.indexOf('function dto381('),bands631.indexOf('(async()=>{',bands631.indexOf('function dto381(')));
new Function('require','__dirname',prefix631+'\n'+history631+String.raw`
(async()=>{
const read=t=>Number(t.replace(/^≥/,'').replace(/\./g,'').replace(',','.').replace(/ %.*/,''));
async function render(v){const root=new N('main');await c.renderEquipo262(root,ctx381([v,null,null,null,null]),'horas');all(root,z=>z.tag==='button'&&text(z)==='Semana pasada')[0].events.click();return{root,row:all(root,z=>z.tag==='tbody')[0].children[0]};}
await test('partial1.06 never asserts1.1 or2.7percent',async()=>{const {root,row}=await render(1.06);assert.equal(text(row.children[1]),'≥1');assert.equal(text(row.children[2]),'≥2,6 %');assert(text(root).includes('≥2,6 % ref.'));assert(!text(row).includes('≥1,1'));assert(row.children[1].children[0].attrs.title.includes('parcial'));assert(row.children[2].children[0].attrs.title.includes('no capacidad contractual'));});
for(const v of [0,1,5.99,7.99,36,1e308])await test('finite minimum bounded '+v,async()=>{const {root,row}=await render(v);const t=text(row.children[1]);assert(t.startsWith('≥'));assert(Number.isFinite(read(t)));assert(read(t)<=v);assert(!text(root).includes('Infinity'));assert(!text(root).includes('NaN'));});
await test('small value remains positive bound notzero',async()=>{const {row}=await render(.006);assert.equal(text(row.children[1]),'<0,1');assert.equal(text(row.children[2]),'<0,1 %');});
await test('unknown no zero or band',async()=>{const {row}=await render(null);assert.equal(text(row.children[1]),'—');assert.equal(text(row.children[2]),'—');assert(!text(row).includes('≥0'));});
await test('normal daily observation retains nearest format',async()=>{const root=new N('main');await c.renderEquipo262(root,ctx381([3.14,null,null,null,null]),'equipo-dia');const cells=all(root,z=>z.attrs.class?.includes('banda381-'));assert(cells.some(z=>text(z)==='3,1'));});
await test('overflow percentage stays unknown',async()=>{const {row}=await render(1e308);assert.equal(text(row.children[2]),'—');});
await test('threshold color preserved and display below60',async()=>{const {row}=await render(23.996);assert.equal(text(row.children[2]),'≥59,99 %');assert(row.children[2].children[0].attrs.class.includes('banda381-rojo'));});
console.log(checks+' grupos631 PASS: renderer real, mínimos, fronteras, unknown y finitud.');
})().catch(e=>{console.error(e);process.exitCode=1;});
`)(require,__dirname);

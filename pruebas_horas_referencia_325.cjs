const fs325=require('node:fs'),path325=require('node:path');
const base325=fs325.readFileSync(path325.join(__dirname,'pruebas_operaciones_equipo_262.cjs'),'utf8').split('(async()=>{')[0];
new Function('require','__dirname',base325+`
(async()=>{
 let n=new N('main');await c.renderEquipo262(n,make(),'equipo-dia');let spans=all(n,x=>x.attrs.class?.includes('oe-observado'));assert.equal(spans.length,1);assert.equal(text(spans[0].children[0]),'14');assert(text(spans[0]).includes('Ref. alta'));assert(!all(n,x=>/ref-(rojo|verde|ambar)/.test(x.attrs.class||'')).length);assert(text(n).includes('Última fecha laboral 2026-10-02'));
 n=new N('main');await c.renderEquipo262(n,make(),'horas');spans=all(n,x=>x.attrs.class?.includes('oe-observado'));assert.equal(spans.length,1);assert(text(spans[0]).includes('% ref.'));assert(!all(n,x=>/ref-(rojo|verde|ambar)/.test(x.attrs.class||'')).length);assert(text(n).includes('Al menos 90 % ref.'));
 const ctx=make();ctx.hoy='2026-10-12';n=new N('main');await c.renderEquipo262(n,ctx,'equipo-dia');assert(text(n).includes('10-09'));assert(text(n).includes('Última fecha laboral 2026-10-09'));assert.equal(all(n,x=>x.attrs.class?.includes('oe-observado')).length,0);assert(!text(n).includes('Ayer por debajo'));
 const zero=JSON.parse(JSON.stringify(H));zero.personas[0].diario_238.dias[0].horas=0;ctx.hoy=H.hoy;ctx.datosModulo=async p=>p==='horas/horas'?zero:docs[p];n=new N('main');await c.renderEquipo262(n,ctx,'equipo-dia');spans=all(n,x=>x.attrs.class?.includes('oe-observado'));assert.equal(text(spans[0].children[0]),'0');assert(text(spans[0]).includes('Ref. baja'));assert.equal(spans.length,1);assert(!all(n,x=>/ref-(rojo|verde|ambar)/.test(x.attrs.class||'')).length);

 const mixed={...H.personas[0],meses:[{mes:'2026-09',imputadas:0}]};const med=c.horasRango262(mixed,H,{desde:'2026-09-01',hasta:'2026-09-30'});assert.equal(med.valor,14);assert.equal(med.tipo,'observado_diario');assert(med.detalle.includes('Suma sólo'));assert(!med.detalle.includes('Total mensual'));
 const legacy=c.horasRango262(H.personas[0],H,{desde:'2026-09-01',hasta:'2026-09-30'});assert.equal(legacy.tipo,'referencia_mensual');assert(legacy.detalle.includes('sin descriptor'));assert.equal(legacy.dias,1);assert.equal(legacy.ultima,'2026-09-28');
 const duplicate=c.horasRango262({...H.personas[0],meses:[{mes:'2026-09',imputadas:90},{mes:'2026-09',imputadas:99}]},H,{desde:'2026-09-01',hasta:'2026-09-30'});assert.equal(duplicate.valor,14);assert.equal(duplicate.tipo,'observado_diario');
 console.log('7 grupos325 PASS: referencia explícita381, fechas actuales, copia antigua y cero observado.');
})().catch(e=>{console.error(e);process.exitCode=1;});
`)(require,__dirname);

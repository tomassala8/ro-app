const fs=require('fs'),vm=require('vm'),path=require('path');
const base=fs.readFileSync(path.join(__dirname,'pruebas_produccion_baseline.cjs'),'utf8');
const harness=base.slice(0,base.indexOf('let live='));
const pruebas=`
const tabla=m=>c.tablaProduccionBaseline({h,titulo:'Fixture',filas:[{}],columnas:[{titulo:'Métrica',valor:()=>m}]});
let checks=0;const check=fn=>{fn();checks++;};
check(()=>{const t=tabla({valor:null,medidos:0,total:8,detalle:'Copia parcial'});assert.equal(text(t).includes('0/8'),false);const x=all(t,n=>n.tag==='span')[0];assert(x.attrs['aria-label'].includes('0/8'));assert(x.attrs.class.includes('pb-unknown'));assert.equal(all(t,n=>n.tag==='small').length,0);});
check(()=>{const t=tabla({valor:12,medidos:2,total:8,detalle:'Copia parcial'});assert.equal(text(t).includes('con dato'),false);assert.equal(all(t,n=>n.tag==='small').length,0);assert(all(t,n=>n.tag==='span')[0].attrs.title.includes('2/8'));});
check(()=>{const x=all(tabla({valor:6,mas48:6,referencia:false,detalle:'Edad observada'}),n=>n.tag==='span')[0];assert(x.attrs.class.includes('pb-cell-ambar'));assert(x.attrs['aria-label'].includes('no certifica incumplimiento'));assert(text(x).includes('6 +48 h'));});
check(()=>{for(const m of [{valor:0,mas48:0},{valor:null,mas48:6},{valor:2,mas48:6},{valor:7,mas48:6,referencia:true}]){const x=all(tabla(m),n=>n.tag==='span')[0];assert(!x.attrs.class.includes('pb-cell-ambar'));assert(!x.attrs.class.includes('verde'));assert(!x.attrs.class.includes('rojo'));}});
check(()=>{const x=all(tabla({valor:7,referencia:true,detalle:'Fuente antigua'}),n=>n.tag==='span')[0];assert(!text(x).includes('Ref.'));assert(x.attrs.title.includes('Referencia de copia')); assert(x.attrs.title.includes('Fuente antigua'));assert(x.attrs.class.includes('pb-reference'));});
check(()=>{assert(vm.runInContext('CSS_PRODUCCION_BASELINE',c).includes('pb-cell-ambar'));assert(vm.runInContext('CSS_PRODUCCION_BASELINE',c).includes('table-layout:fixed'));});
console.log(checks+' grupos render colores/densidad258 PASS');
`;
vm.runInNewContext(harness+pruebas,{require,__dirname,console},{filename:__filename});

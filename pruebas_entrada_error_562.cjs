const fs=require('node:fs'),assert=require('node:assert/strict');
(async()=>{
 const src=fs.readFileSync('app.js','utf8'),helper=fs.readFileSync('_entrada_error_562.js','utf8');
 const {falloEntrada562}=await import('data:text/javascript;base64,'+Buffer.from(helper).toString('base64'));
 const begin=src.indexOf('    if (e.status === 401) { olvidarTodo(); return pintarElegir(); }'),end=src.indexOf('  await listoDisco;',begin);
 assert(begin>0&&end>begin);const body=src.slice(begin,end).replace(/\n  }\n$/, '\n');
 const run=new Function('e','$','estadoVacio','olvidarTodo','pintarElegir','document','falloEntrada562',body);
 let n=0;
 for(const status of [403,500,503,undefined,404]){
  const elements={'#titulo':{textContent:'Cargando…'},'#subtitulo':{textContent:'Texto anterior'},'#main':{replaceChildren(v){this.child=v;}}},doc={title:'App RO'};let clears=0;
  run({status,message:'PRIVATE ERROR /secret/path python3'},s=>elements[s],x=>x,()=>clears++,()=>{throw Error('selector inesperado');},doc,falloEntrada562);
  assert.equal(elements['#titulo'].textContent,status===403?'No tienes acceso':'La app no responde');assert.equal(elements['#subtitulo'].textContent,'');assert.equal(doc.title,elements['#titulo'].textContent+' · App RO');assert.equal(clears,status===403?1:0);
  const rendered=JSON.stringify(elements['#main'].child);assert(!/PRIVATE|python|secret|Cargando/.test(rendered));assert(/Mili/.test(rendered));n++;
 }
 let cleared=0,selected=0;run({status:401},()=>{throw Error('No pinta error tras401');},()=>{},()=>cleared++,()=>selected++,{},falloEntrada562);assert.equal(cleared,1);assert.equal(selected,1);n++;
 assert.deepEqual(falloEntrada562(null),{titulo:'La app no responde',porque:'Avisa a Mili para que pueda revisarlo.'});n++;
 console.log(n+' grupos562 PASS · handler real, errores públicos, título y401 preservado');
})().catch(e=>{console.error(e);process.exitCode=1});

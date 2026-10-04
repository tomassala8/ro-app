// Caracterización de un defecto pendiente. PASS demuestra el hueco, no su corrección.
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const source=fs.readFileSync('modulos/informe.js','utf8');
const click=source.match(/on: \{ click: (\(\) => \{[^\n]*window\.print\(\); \})/);
assert(click,'Se extrae el callback PDF actual, sin reproducir una copia del algoritmo.');
const helper=fs.readFileSync('modulos/_informe_evidencia.js','utf8').replace(/export /g,'');
let prints=0,notes=[],rastro=[];
const s={zona:{isConnected:true},ctx:{vigente:()=>true,rastro:x=>rastro.push(x)},av:[],estadoLogo:'ausente',c:{id:'fixture'},P:{id:'2026-09'},window:{print:()=>prints++},avisoFlotante:x=>notes.push(x)};
vm.createContext(s);vm.runInContext(helper+'\nglobalThis.pdfClick='+click[1],s);
s.pdfClick();assert.equal(prints,0);assert.match(notes[0],/logo real del cliente/);
s.estadoLogo='cargado';
// La consulta de ejecución sigue pendiente: no hay respuesta/filas acreditadas.
s.trabajos={textContent:'Consultando evidencias del periodo…'};
s.pdfClick();assert.equal(prints,1);assert.equal(s.trabajos.textContent,'Consultando evidencias del periodo…');assert.equal(rastro.length,1);
console.log('608: 2 caracterizaciones PASS. Logo ausente bloquea; logo cargado permite imprimir con evidencia todavía pendiente (defecto reproducido, NO fix).');

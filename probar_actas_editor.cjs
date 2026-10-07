const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const webcrypto = require('node:crypto').webcrypto;
const file=require('node:path').join(__dirname,'modulos','ficha_equipo.js');
const source=fs.readFileSync(file,'utf8');
const editor=source.slice(source.indexOf('function editorActa('),source.indexOf('\nfunction guionTexto('));
class Element {
 constructor(tag,attrs={},children=[]) {this.tag=tag;this.attrs=attrs;this.children=children.flat().filter(Boolean);this.value=attrs.value||'';this.disabled=false;this.textContent='';this.on=attrs.on||{};}
 append(x){this.children.push(x)}
 querySelectorAll(sel) {const all=this.children.flatMap(c=>c instanceof Element?[c,...c.querySelectorAll('*')]:[]);if(sel==='*')return all;return all.filter(e=>sel==='[data-acuerdo]'?Object.hasOwn(e.attrs,'data-acuerdo'):sel==='textarea'?e.tag==='textarea':e.tag==='select'||e.tag==='input'&&['text','date'].includes(e.attrs.type));}
 querySelector(sel){return this.querySelectorAll(sel)[0]}
 focus(){} remove(){}
}
const scope={crypto:webcrypto,TextEncoder,Uint8Array,h:(t,a,...c)=>new Element(t,a,c),campoTexto:()=>new Element('div',{},[new Element('textarea')]),equipoAvisable:()=>[],icono:()=>null,dia:x=>x,fmt:{plural:(n,s,p)=>`${n} ${n===1?s:p}`},avisoFlotante:()=>{},SILLA:{}};
vm.createContext(scope);vm.runInContext(editor+';globalThis.runEditor=editorActa',scope);
(async()=>{
 let fail=true,calls=[],refreshes=0;
 const ctx={real:{id:'lucia'},nombre:x=>x,hoy:'2026-10-03',api:async(r,opt)=>{calls.push([r,structuredClone(opt)]);if(fail)throw Error('Fallo segundo acuerdo');return {tareas:[2,3],repetida:calls.length>1};}};
 const section=scope.runEditor(ctx,{c:{id:'cliente'}},{},async()=>{refreshes++});
 const all=section.querySelectorAll('*');const notes=all.find(e=>e.tag==='textarea');notes.value='Mis notas';
 const rows=section.querySelectorAll('[data-acuerdo]');rows[0].querySelectorAll('input[type=text], select, input[type=date]')[0].value='Primer acuerdo';
 const save=all.find(e=>e.tag==='button'&&e.children.includes('Guardar'));
 const status=all.find(e=>e.attrs.role==='status');
 await save.on.click();assert.match(status.textContent,/Tus notas y acuerdos siguen aquí/);assert.equal(notes.value,'Mis notas');assert.equal(refreshes,0);assert.equal(save.disabled,false);
 fail=false;await save.on.click();assert.equal(refreshes,1);assert.equal(calls.length,2);assert.equal(calls[0][0],'ficha/acta');assert.deepEqual(calls[0],calls[1]);assert.match(calls[0][1].cuerpo.clave,/^acta_[a-f0-9]{64}$/);
 await save.on.click();assert.equal(calls.length,2,'Doble clic no debe repetir una petición durante guardado');
 // Solo lectura: ni hash ni solicitud.
 ctx.soloLectura=true;const ro=scope.runEditor(ctx,{c:{id:'cliente'}},{},async()=>{});const bt=ro.querySelectorAll('*').find(e=>e.tag==='button'&&e.children.includes('Guardar'));await bt.on.click();assert.equal(calls.length,2);
 console.log('OK: editor real conserva notas tras error; reintento idéntico estable; una petición por lote; doble clic y solo lectura bloqueados.');
})().catch(e=>{console.error(e);process.exit(1)});

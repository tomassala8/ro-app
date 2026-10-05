// Reusa sólo el entorno DOM sintético111; ejecuta nuevas assertions contra agenda.js real.
const fs=require('fs'),path=require('path');
const base=fs.readFileSync(path.join(__dirname,'pruebas_agenda_111.cjs'),'utf8').split('const evento=')[0];
const comprobar=`
let casos=0;
const e={id:'crm_123',persona_id:'tomas',titulo:'Reunión sintética',inicio:'2099-10-03 10:00',fin:'2099-10-03 11:00',zoom_privado_disponible:true,atajos:[]};
const S={ctx:{real:{id:'tomas',puestos:['direccion']},persona:{id:'tomas',puestos:['direccion']},vigente:()=>true}};
let a=c.accionesCita(S,e,false,{abrir:'Zoho'}), link=buscar(a,n=>n.attrs?.class==='bt pri')[0];
assert.equal(link.attrs.href,'/api/agenda/zoom?evento_id=crm_123&yo=tomas');assert(text(a).includes('Abrir mi sala de Zoom'));assert(!text(a).includes('Iniciar'));casos++;
for(const ctx of [{real:{id:'ops',puestos:['operaciones']},persona:{id:'ops',puestos:['operaciones']}},{real:{id:'tomas',puestos:['direccion']},persona:{id:'otra',puestos:['account']}},{real:{id:'homonimo',puestos:['direccion']},persona:{id:'homonimo',puestos:['direccion']}},{real:{id:'tomas',puestos:['seo']},persona:{id:'tomas',puestos:['seo']}}]){
 a=c.accionesCita({ctx},e,false,{abrir:'Zoho'});assert(!buscar(a,n=>n.attrs?.href?.startsWith('/api/agenda/zoom')).length);casos++;
}
for(const change of [{persona_id:'otra'},{id:'../escape'},{id:null},{zoom_privado_disponible:false}]){assert.equal(c.salaPrivadaAgenda(S.ctx,{...e,...change}),false);casos++;}
let denied=0;S.ctx.vigente=()=>false;link.attrs.on.click({preventDefault(){denied++;}});assert.equal(denied,1);S.ctx.vigente=()=>true;S.ctx.persona={id:'otra',puestos:['direccion']};link.attrs.on.click({preventDefault(){denied++;}});assert.equal(denied,2);casos++;
for(const join_url of ['https://zoom.us/j/123?zak=hostsecret','https://zoom.us/j/123?ZaK=hostsecret','https://zoom.us/s/123','https://zoom.us/j/123/extra','https://zoom.us/j/%2fsecret','https://zoom.us/j/123?access_token=secret','https://zoom.us/j/123\\n']){assert.equal(c.enlaceZoom({join_url}),null);casos++;}
const join='https://us02web.zoom.us/j/123?pwd=fixture';assert.equal(c.enlaceZoom({join_url:join,atajos:[{h:'zoom',url:join}]}),join);casos++;
assert.equal(c.enlaceZoom({join_url:join,zoom_url:'https://zoom.us/j/456'}),null);casos++;
a=c.accionesCita({ctx:{real:{id:'other'},persona:{id:'other'}}},{...e,join_url:join,zoom_url:'https://zoom.us/j/456',atajos:[{h:'zoom',url:'https://zoom.us/s/123?zak=secret'}]},false,{abrir:'Zoho'});
assert(text(a).includes('Varios enlaces de Zoom'));assert(!buscar(a,n=>n.attrs?.class==='bt pri').length);assert(!buscar(a,n=>n.tag==='menu').length);casos++;
const w={D:{_meta:{desde:'2026-09-19',hasta:'2026-10-24'}},ctx:{clientesVisibles:[],verdad:()=>null},semana:'2026-09-28',dia:'2026-10-03',quien:'other',nombres:{},pintar(tab){this.last=tab;}};
const week=c.vistaSemana(w,[{...e,inicio:'2026-09-28 10:00',fin:'2026-09-28 11:00',tipo:'cliente'},{...e,id:'otro',inicio:'2026-09-28 10:00',fin:'2026-09-28 11:00',tipo:'cliente'}],'2026-10-03',630);
assert.equal(buscar(week,n=>n.attrs?.class?.startsWith('agenda-evento ')).length,2,'dos citas a misma hora/nombre no desaparecen');
buscar(week,n=>n.attrs?.class==='agenda-col-titulo')[0].attrs.on.click();assert.equal(w.dia,'2026-09-28');assert.equal(w.last,'hoy');casos++;
const fuentes=c.vistaFuentes({D:{eventos:[e]}},{fuentes:[{id:'dedup',n:209,estado:'bien',fuente:'Lectura sintética',detalle:'Metadato previo'}],generado:'2026-10-03 04:40'});assert(text(fuentes).includes('no conserva referencias compartidas'));assert(!text(fuentes).includes('le falta el permiso'));casos++;
console.log(casos+' casos164 pasan: nominal, host no público, identidad tardía, enlaces ambiguos y calendario sin dedup heurístico.');
`;
new Function('require','__dirname',base+comprobar)(require,__dirname);

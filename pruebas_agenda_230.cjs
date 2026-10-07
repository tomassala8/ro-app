const fs=require('node:fs');
const base=fs.readFileSync(__dirname+'/pruebas_agenda_111.cjs','utf8').split('const evento=')[0];
new Function('require','__dirname',base+`
let casos=0;
const e={id:'fixture',persona_id:'fixture',titulo:'Cita sintética',tipo:'cliente',inicio:'2026-10-03 22:00',fin:'2026-10-04 01:00'};
assert.equal(c.estadoTemporal(e,'2026-10-03',14*60),'proxima');assert.equal(c.estadoTemporal(e,'2026-10-03',23*60),'ahora');assert.equal(c.estadoTemporal(e,'2026-10-04',30),'ahora');assert.equal(c.estadoTemporal(e,'2026-10-04',60),'pasada');casos++;
for(const fin of [undefined,'2026-10-03 21:00','2026-10-03 22:00','no-fin','2026-10-03 99:99']){assert.equal(c.estadoTemporal({...e,fin},'2026-10-03',23*60),'fin_desconocido');assert.equal(c.estadoTemporal({...e,fin},'2026-10-03',21*60),'proxima');casos++;}
for(const inicio of [undefined,'2026-02-30 10:00','2026-10-03 99:00','2026-10-03T10:00:00+25:00'])assert.equal(c.estadoTemporal({...e,inicio},'2026-10-03',23*60),'sin_hora');casos++;
assert.equal(c.estadoTemporal(e,'no-fecha',10),'sin_hora');assert.equal(c.estadoTemporal(e,'2026-10-03',NaN),'sin_hora');casos++;
assert.equal(c.estadoTemporal({...e,inicio:'2026-10-03T08:00:00Z',fin:'2026-10-03T09:00:00Z'},'2026-10-03',10*60+30),'ahora');casos++;
const S={ctx:{real:{id:'fixture',puestos:['account']},persona:{id:'fixture',puestos:['account']},clientesVisibles:[],vigente:()=>true},nombres:{}};
let tarjeta=c.tarjeta(S,e,{hoy:'2026-10-03',ahoraMin:23*60});assert(text(tarjeta).includes('3 h'));assert(text(tarjeta).includes('Fin dom 4 oct · 01:00'));assert(text(tarjeta).includes('Ahora'));casos++;
tarjeta=c.tarjeta(S,{...e,fin:undefined},{hoy:'2026-10-03',ahoraMin:23*60});assert(text(tarjeta).includes('Sin duración registrada'));assert(!text(tarjeta).includes('Ahora'));casos++;
tarjeta=c.tarjeta(S,{...e,inicio:null,fin:null},{hoy:'2026-10-03',ahoraMin:23*60});assert(text(tarjeta).includes('Hora por confirmar'));casos++;
let opens=0;c.window={open:()=>opens++};c.menuMas=o=>h('menu',{config:o},o.items.map(x=>x.texto));const evento={...e,atajos:[{h:'crm',url:'https://example.com/evento'},{h:'zoom',url:'https://zoom.us/rec/share/fixture'}],join_url:'https://zoom.us/j/123'};
let a=c.accionesCita(S,evento,true,{abrir:'Zoho'});const recording=buscar(a,n=>n.attrs?.['aria-label']==='Ver grabación: Cita sintética')[0];const menu=buscar(a,n=>n.tag==='menu')[0];assert(recording&&menu);menu.attrs.config.items[0].alPulsar();assert.equal(opens,1);casos++;
let denied=0;S.ctx.vigente=()=>false;recording.attrs.on.click({preventDefault(){denied++}});menu.attrs.config.items[0].alPulsar();assert.equal(opens,1);assert.equal(denied,1);casos++;
S.ctx.vigente=()=>true;S.ctx.persona.id='otra';recording.attrs.on.click({preventDefault(){denied++}});menu.attrs.config.items[0].alPulsar();assert.equal(denied,2);assert.equal(opens,1);casos++;
S.ctx.persona.id='fixture';S.ctx.persona.puestos=['seo'];recording.attrs.on.click({preventDefault(){denied++}});menu.attrs.config.items[0].alPulsar();assert.equal(denied,3);assert.equal(opens,1);casos++;
S.ctx.persona.puestos=['account'];a=c.accionesCita(S,{...evento,atajos:[{h:'zoom',url:'https://zoom.us:444/rec/share/fixture'}]},false,{abrir:'Zoho'});assert(!text(a).includes('Ver grabación'));casos++;
assert.equal(c.urlSegura('https://example.com/evento'),'https://example.com/evento');assert.equal(c.urlSegura('https://user:password@example.com/evento'),null);assert.equal(c.enlaceZoom({join_url:'https://zoom.us/s/123?zak=fixture'}),null);casos++;
tarjeta=c.tarjeta(S,{...e,fuente:'desconocida'},{hoy:'2026-10-03',ahoraMin:23*60});assert(text(tarjeta).includes('Fuente por confirmar'));assert(!text(tarjeta).includes('Zoho'));casos++;
console.log(casos+' casos230 PASS: medianoche/fin ausente/inválidos, tarjeta real, fechas Madrid, acciones con identidad/rol/vigencia y URL segura.');
`)(require,__dirname);

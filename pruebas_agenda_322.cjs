const fs=require('node:fs'),path=require('node:path');
const base=fs.readFileSync(path.join(__dirname,'pruebas_agenda_111.cjs'),'utf8').split('const evento=')[0];
new Function('require','__dirname',base+`
const minutos=x=>Number(x.slice(0,2))*60+Number(x.slice(3));
const e=(id,min,fin)=>({evento:{id,tipo:'cliente',titulo:'Cita '+id,inicio:'2026-09-28 '+min,fin:'2026-09-28 '+fin},inicio_min:minutos(min),fin_min:minutos(fin)});
const chain=[e('larga','08:00','19:00'),e('a','08:00','08:15'),e('b','08:00','08:30'),e('c','10:00','11:00'),e('d','11:00','12:00'),e('e','14:00','15:00')];
const before=JSON.stringify(chain),bs=c.bloquesVisualesAgenda322(chain);
assert.equal(bs.length,4);assert.equal(bs[0].segmentos.length,3);assert.equal(bs[0].fin_visual,515);assert.equal(bs[1].inicio_min,600);assert.equal(bs[1].fin_visual,660);assert.equal(JSON.stringify(chain),before);
assert.equal(bs.flatMap(b=>b.segmentos).length,chain.length);assert.equal(new Set(bs.flatMap(b=>b.segmentos.map(s=>s.evento.id))).size,chain.length);
const second=c.bloquesVisualesAgenda322([e('larga','08:00','18:00'),e('solo','09:00','10:00'),e('c1','12:00','12:15'),e('c2','12:00','12:15'),e('c3','12:00','12:15')]);
assert.equal(second.length,3);assert.equal(second[2].columnas,2);assert.notEqual(second[0].columna,second[2].columna);assert.equal(second[2].fin_visual,755);
const boundary=c.bloquesVisualesAgenda322([e('a','10:00','10:05'),e('b','10:15','10:20'),e('c','10:35','10:40')]);assert.equal(boundary.length,3);assert(boundary.every(b=>!b.agrupado));
const S={D:{_meta:{desde:'2026-09-20',hasta:'2026-10-20'}},ctx:{clientesVisibles:[],verdad:()=>null,vigente:()=>true},quien:'yo',nombres:{},semana:'2026-09-28',dia:'2026-09-28',pintar(){}};
const w=c.vistaSemana(S,chain.map(s=>s.evento),'2026-10-03',630),groups=buscar(w,n=>n.attrs?.class==='agenda-evento agenda-grupo-visual');assert.equal(groups.length,1);assert.equal(groups[0].attrs.style.height,'42px');assert(text(groups[0]).includes('3 citas'));groups[0].attrs.on.click();for(const id of ['larga','a','b'])assert(text(S.abrirEn).includes('Cita '+id));assert(text(S.abrirEn).includes('19:00'));
const ayuda=buscar(w,n=>n.attrs?.class==='agenda-horario-ayuda')[0];assert(ayuda&&ayuda.tag==='details');assert(!ayuda.attrs.open);assert(text(ayuda).includes('no representa duración ni disponibilidad'));
console.log('Agenda322: 6 grupos PASS; cadenas, carriles, fronteras, todos los registros y ayuda plegada.');
`)(require,__dirname);

const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const s={URL,Date,Number,JSON,Map,Set};vm.createContext(s);
const med=fs.readFileSync('modulos/_seo_mediciones.js','utf8').replace(/export /g,'');Object.assign(s,vm.runInContext('(()=>{'+med+';return {paginasSEO,fechaSEO};})()',s));
vm.runInContext(fs.readFileSync('modulos/_seo_oportunidades_332.js','utf8').replace(/^import .*;$/mg,'').replace(/export /g,''),s);
const ps={id:'seo',estado:'activo',puestos:['seo']};function ctx(){return {servidor:true,real:{...ps},persona:{...ps},datos:{personas:[{...ps}]},clientesVisibles:[{id:'c',activo_confirmado:true,detalle:true}],hoy:'2026-10-03',vigente:()=>true,veModulo:()=>true,ver:()=>({ok:true})};}
const meta={gsc:{leido:'2026-10-03 01:00'}};
const f={cliente_id:'c',gsc_estado:'bien',clics:{hasta:'2026-09-30',ventanas:{mes:['2026-09-03','2026-09-30'],mes_ant:['2026-08-06','2026-09-02']}},gsc:{paginas:[['https://example.invalid/a',10,100,8,30],['https://example.invalid/b',0,400,8,0],['https://example.invalid/c',20,600,8,10]]}};
assert.equal(s.oportunidadPagina332({...f,gsc:{paginas:[['https://example.invalid/zero',0,0,null,0]]}},meta,ctx()),null);
let c=ctx(),n=1,op=s.oportunidadPagina332(f,meta,c);assert.equal(op.ruta,'/a');assert.equal(op.perdidos,20);assert.equal(op.ir,'seo-web/c/clics');assert.equal(op.cobertura,'parcial');n++;
op=s.oportunidadPagina332({...f,gsc:{paginas:f.gsc.paginas.slice(1)}},meta,c);assert.equal(op.ruta,'/b');assert.equal(op.clics,0);assert.equal(op.tipo,'impresiones_sin_clics');n++;
op=s.oportunidadPagina332({...f,gsc:{paginas:[f.gsc.paginas[2]]}},meta,c);assert.equal(op.tipo,'exposicion');n++;
op=s.oportunidadPagina332({...f,clics:{...f.clics,ventanas:{mes:f.clics.ventanas.mes}},gsc:{paginas:[f.gsc.paginas[0]]}},meta,c);assert.equal(op.anterior,null);assert.equal(op.tipo,'exposicion');n++;
for(const patch of [{gsc:{paginas:[f.gsc.paginas[0],f.gsc.paginas[0]]}},{gsc:{error:'fail',paginas:f.gsc.paginas}},{cliente_id:'foreign'},{clics:{...f.clics,ventanas:{mes:['2026-09-04','2026-09-30']}}}]){assert.equal(s.oportunidadPagina332({...f,...patch},meta,c),null);n++;}
for(const url of ['https://example.invalid/a?token=bad','https://user:secret@example.invalid/a','https://example.invalid/%74oken','javascript:alert(1)']){assert.equal(s.oportunidadPagina332({...f,gsc:{paginas:[[url,2,100,8,4]]}},meta,c),null);n++;}
for(const change of [c=>c.ver=()=>({ok:false}),c=>c.real.estado='inactivo',c=>c.clientesVisibles[0].activo_confirmado=false,c=>c.clientesVisibles.push({...c.clientesVisibles[0]}),c=>c.vigente=()=>false]){c=ctx();change(c);assert.equal(s.oportunidadPagina332(f,meta,c),null);n++;}
class N{constructor(tag,attrs={},...kids){this.tag=tag;this.attrs=attrs;this.children=kids.flat(Infinity).filter(x=>x!=null);this.isConnected=true;}append(...xs){this.children.push(...xs.flat(Infinity));}replaceChildren(...xs){this.children=xs.flat(Infinity);}querySelectorAll(){return [];}closest(){return null;}setAttribute(k,v){this.attrs[k]=v;}}
const h=(...xs)=>new N(...xs),text=n=>typeof n==='object'?(n?.children||[]).map(text).join(' '):String(n??''),all=n=>typeof n==='object'&&n?[n,...(n.children||[]).flatMap(all)]:[];let tables=[];
Object.assign(s,{h,Intl,encodeURIComponent,document:{},fmt:{num:x=>String(x)},icono:()=>'',logoCliente:()=>'',panel:(o,...xs)=>h('panel',{},o.titulo,...xs),listaLoPrimero:()=>h('list'),tablaDensa:o=>{tables.push(o);return h('table',{},o.filas.map(r=>h('tr',{},o.columnas.map(col=>col.celda?col.celda(r):r[col.clave]))));},chipsFiltro:()=>({valor:()=>'',querySelectorAll:()=>[]}),botonConfirmar:()=>h('button'),botonDeshacer:()=>h('button'),chipEstado:(e,t)=>t,vacioLinea:t=>h('empty',{},t),avisoParcial:t=>h('note',{},t)});
Object.assign(s,vm.runInContext('(()=>{'+fs.readFileSync('modulos/_panel_especialista.js','utf8').replace(/export /g,'')+';return {panelSeo};})()',s));
Object.assign(s,vm.runInContext('(()=>{'+fs.readFileSync(__dirname+'/modulos/_objetivos_seo_374.js','utf8').replace(/export /g,'')+';return {cargarObjetivos374,celdaObjetivo374,renderObjetivos374};})()',s));
const source=fs.readFileSync('modulos/seo.js','utf8').replace(/^import[\s\S]*?from ['"][^'"]+['"];[^\n]*\n/gm,'').replace('export default {','const modulo={');vm.runInContext(source,s);
c=ctx();Object.assign(c,{clientes:c.clientesVisibles,carteraIds:new Set(['c']),nombre:()=>null,soloLectura:true});const row={...f,cliente:'Client',seo_id:'seo',estado:'gris',alertas:[],_medicionSEO:{clics:{mes:true}},informe15:[],motivo:'Partial',n_alertas:{},seranking:null};
const d={seo:{_meta:meta},oportunidadesScope332:s.ambitoOportunidades332(c).firma},root=h('root');s.pintarSeo(root,c,d,[row],'seo');assert(text(root).includes('Revisar /a'));assert(text(root).includes('-20 clics observados'));assert(text(root).includes('10 clics · 100 impresiones'));const link=all(root).find(x=>x.tag==='a'&&x.attrs.href==='#/seo-web/c/clics');assert(link);assert(link.attrs.title.includes('20 clics menos'));assert(link.attrs.title.includes('2026-09-03'));n++;
const zeroRoot=h('root');s.pintarSeo(zeroRoot,c,d,[{...row,gsc:{paginas:[f.gsc.paginas[1]]}}],'seo');assert(text(zeroRoot).includes('Revisar /b'));assert(text(zeroRoot).includes('0 clics · 400 impresiones · Sin clics'));n++;
c.ver=()=>({ok:false});let prevented=false;link.attrs.on.click({preventDefault:()=>prevented=true});assert(prevented);n++;
const root2=h('root');s.pintarSeo(root2,c,d,[row],'seo');assert(!text(root2).includes('/a'));n++;
// Ruta real reconoce segundo parámetro y abre la pestaña existente Clics (no selector ficticio).
assert(source.includes("activa: ctx.params?.[1]==='clics'?'clics':'pos'"));
console.log(n+' grupos332 PASS: selector/periodos/scope/URL y celda real SEO sin proveedor/POST.');

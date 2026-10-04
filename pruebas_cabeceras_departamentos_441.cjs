const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const maps=[["Registro del último laborable", "Reg. últ. laborable"], ["Semana de la fuente", "Sem. fuente"], ["Días con 0 en la foto (últimos 5)", "Días 0 foto (últ.5)"], ["Revisión de cartera", "Rev. cartera"], ["Configuración básica", "Config. básica"], ["Estado y paso (equipo)", "Estado/paso equipo"], ["Terminada (Madrid)", "Fin (Madrid)"], ["Aceptadas en LinkedIn", "Acept. LinkedIn"], ["Errores al guardar o cargar", "Errores guardar/cargar"], ["Cambio en sesiones", "Δ sesiones"], ["Eventos por sesión", "Eventos/sesión"], ["Resultados Meta · referencia", "Res. Meta (ref.)"], ["Coste por evento lead", "Coste/evento lead"], ["Impresiones sep (web)", "Impr. sep (web)"], ["Impresiones sep (por página)", "Impr. sep/pág."], ["Consultas org. / Maps", "Cons. org./Maps"], ["Plugins / rendimiento", "Plugins/rend."]];
const base=fs.readFileSync(__dirname+'/pruebas_revision_cabeceras_421.cjs','utf8').split('let n=0;')[0];
vm.runInNewContext(base+`
let count441=0;
const corpus441=fs.readdirSync('modulos').filter(f=>f.endsWith('.js')).map(f=>fs.readFileSync('modulos/'+f,'utf8')).join(' ');
for(const [full,short] of globalThis.maps441){
 assert(corpus441.includes("titulo: '"+full+"'")||corpus441.includes("titulo:'"+full+"'"),'Título real: '+full);
 const c={clave:'f',titulo:full,num:true,valor:r=>r.v,celda:r=>r.v,ordenable:true};const a=e.cabeceraCompacta421(c);assert.equal(a.titulo,short);assert.equal(a.tituloCompleto,full);assert.equal(a.celda,c.celda);assert.equal(a.valor,c.valor);assert.equal(c.titulo,full);
 for(const table of ['tablaDensa','tablaApilable']){const root=e[table]({columnas:[c],filas:[{v:0}],porPagina:0}),th=all(root,x=>x.tag==='th')[0],td=all(root,x=>x.tag==='td')[0];assert.equal(th.textContent,short);assert.equal(th.attrs.title,full);assert.equal(th.attrs['aria-label'],full);assert.equal(td.attrs['data-l'],short);assert.equal(td.attrs.title,full);assert.equal(td.textContent,'0');}
 count441++;
}
for(const full of ['Días con 0 en la foto (últimos 30)','Impresiones sep (por página) extra','Resultados Meta · referencia 7d','Consultas org. / Maps 30d','Equipo','Llama 7d','Imputa 7d']){const c={titulo:full};assert.equal(e.cabeceraCompacta421(c),c);count441++;}
const c441={titulo:'Impresiones sep (por página)',tituloCompleto:'Fuente íntegra · periodo septiembre · por página',tituloMovil:'Impr. sep/pág.'};
for(const table of ['tablaDensa','tablaApilable']){const root=e[table]({columnas:[{...c441,clave:'v'}],filas:[{v:2}],porPagina:0}),th=all(root,x=>x.tag==='th')[0],td=all(root,x=>x.tag==='td')[0];assert.equal(th.attrs.title,c441.tituloCompleto);assert.equal(td.attrs.title,c441.tituloCompleto);assert.equal(td.attrs['data-l'],c441.tituloMovil);}count441++;
console.log(count441+' grupos441 PASS:17títulos reales/2componentes, unidades/periodos/metadatos/móvil/cero y no coincidencias difusas.');
`,{require,console,process,__dirname:process.cwd(),maps441:maps},{filename:__filename});

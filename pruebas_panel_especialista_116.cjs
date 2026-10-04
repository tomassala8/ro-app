const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
(async()=>{
 const m=await import('data:text/javascript;base64,'+Buffer.from(fs.readFileSync(path.join(__dirname,'modulos/_panel_especialista.js'))).toString('base64'));
 assert.equal(m.numeroMedido(null),null);assert.equal(m.numeroMedido(false),null);assert.equal(m.numeroMedido(NaN),null);assert.equal(m.conteoMedido(2.5),null);assert.equal(m.conteoMedido(0),0);
 assert.equal(m.fechaMedida('2026-02-30'),null);
 assert.equal(m.rachaSinLeads([{d:'2026-10-02',leads_meta:null}],'2026-10-02','2026-10-03'),null);
 assert.equal(m.rachaSinLeads([{d:'2026-10-03',leads_meta:0}],'2026-10-03','2026-10-03'),null);
 let r=m.rachaSinLeads([{d:'2026-10-02',leads_meta:0},{d:'2026-10-01',leads_meta:0},{d:'2026-09-30',leads_meta:2}],'2026-10-02','2026-10-03');assert.equal(r.dias,2);assert.equal(r.completa,true);
 r=m.rachaSinLeads([{d:'2026-10-02',leads_meta:0},{d:'2026-09-30',leads_meta:0}],'2026-10-02','2026-10-03');assert.equal(r.dias,1);assert.equal(r.completa,false);
 assert.equal(m.rachaSinLeads([{d:'2026-10-02',leads_meta:0},{d:'2026-10-02',leads_meta:2}],'2026-10-02','2026-10-03'),null);
 const c={dinero:false,cpl_resumen:{ref:12},objetivo:{cargado:true,cpl_objetivo:25,cuando:'2026-10-01'},serie:[{d:'2026-10-02',leads_meta:0}],cuenta_meta:{error:'HTTP403'}};
 let p=m.panelPaid(c,{datos_hasta:'2026-10-02'},'2026-10-03');assert.equal(p.real,null);assert.equal(p.objetivo,null);assert.equal(p.racha,null);
 p=m.panelPaid({...c,dinero:true,cuenta_meta:{}},{datos_hasta:'2026-09-30'},'2026-10-03');assert.equal(p.datoVigente,false);assert(p.accion.includes('Actualizar'));
 p=m.panelPaid({...c,dinero:true,cuenta_meta:{},objetivo:{cpl_usado:35,cargado:false}},{datos_hasta:'2026-10-02'},'2026-10-03');assert.equal(p.objetivo,null);
 const s=m.panelSeo({informe15:[{hoy:3,mapa:null},{hoy:null,mapa:2}],clics:{mes:0,mes_ant:5,hasta:'2026-09-29'},gsc:{paginas:[{}]}},{});assert.equal(s.organico,1);assert.equal(s.maps,1);assert.equal(s.trafico,0);assert(s.accion.includes('28 días'));assert.equal(m.panelSeo({},{}).trafico,null);
 assert.equal(m.panelWeb({}).plugins,null);assert.equal(m.panelWeb({comprobacion:{ms:0},modular:{actualizaciones:{plugins:0}}}).ms,0);
 console.log('116: autorización de dinero, unknown, rachas cerradas/contiguas, replay, fechas, orgánico/Maps, plugins OK');
})();

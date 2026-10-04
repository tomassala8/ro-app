# 677 — entradas, intentos y cobertura CRM

Candidato aislado, NO integrado APP. Sólo fixtures ficticios; sin navegador, proveedor ni lectura de contactos. BaselineCRM corresponde al cierre673.

## Defectos y alcance

La columna El lead escribió de pintarLeads presenta respondio:true legado como Sí, revisar. El productor anterior tomaba cualquier inbound de conversación, incluso previo al lead y sin distinguir llamadas; no acredita que el lead escribiera desde su creación. No hay tasa de respuesta visible hoy, ni se crea una nueva. Primer intento consume pct_1h calculado desde pares legados sin descriptor de medición, y Sin intento usa como denominador todos los leads aunque sólo una parte tenga lectura válida.

Candidato modulos/crm.js con un import nuevo y cambios localizados en sumar, columna respondio, columnas Sin intento24h/Intento<1h, franja de primer intento y detalle de esos mismos indicadores. Nuevo helper _contacto_observado_677.js. No cambia canales597, acciones531, revisiones369/334, montajes, entregabilidad673, scopes/grants ni score. No altera payloads de acciones.

Legacy respondio:true sin evidencia=>Por confirmar gris; false/null=>—, no ausencia. Con descriptor676 reducido y vínculo exacto cliente_id/sub_id/ref, entrada positiva=>Entrada obs. gris; fecha última escrita en title/ARIA. No confirma respuesta humana, llamada, calidad ni venta. Desconocido nunca se sustituye por0.

Primero<1h legado conserva par numérico N/K y referencia gris en title/ARIA, sin porcentaje ni tasa vigente. Pares malformados/num>denom=>—. Sin intento conserva número guardado como referencia si no hay descriptor, y sólo descriptor672 exacto fuente/cobertura/parcial con conteos tipados acredita n/N de lectura. Suma de coberturas excluye subcuentas duplicadas, overflow=>null; agregados heterogéneos no adquieren semáforo actual por tener algún registro compatible. Señales con descriptor siguen contrastando llamadas externas.

## Contrato676 coordinado, sujeto al RELEASE definitivo

lead.respuesta_medicion676: version676.1, fuenteghl_conversacion, estadoobservado_parcial, desde_ms/hasta_ms, completa:false, entradas_observadas entero positivo, ultima_entrada_ms, cliente_id/sub_id/ref exactos; respuesta_humana_confirmada:null y resultado_comercial_confirmado:null. No incluye contacto ni IDmensaje. Campo lead.creado_iso676 UTCaware necesario: creado legacy es Madrid naïve y pierde segundos.

Helper exige desde_ms==creado_iso676 exacto, última entre desde/hasta, hasta no futuro respecto hoyMadrid válido y coherencia con sello fuente GHL al minuto. Fuente naïve se interpreta explícitamente Madrid con correspondencia de zona y rechaza horas DST ambiguas/inexistentes; no Date.parse dependiente de timezone del navegador. Un error fuente, vínculo ajeno o fecha inválida conserva referencia/desconocido. No exige conteos_acreditados del raw privado para acreditar sólo entrada positiva: el descriptor público reducido certifica ese mínimo, no censo.

## Evidencia

42 escenarios PASS usando helper real y funciones completas pintarLeads/pintarSubcuentas; antes/después reproduce Sí sin descriptor y100%legacy→N/K. Negativas: links de identidad, bool/string/NaN/Infinity/overflow, cortes futuros/incompatibles, hoy ausente/imposible, falta creado_iso676, fuente error/offset inválido;0 explícito y2/5parcial se conservan; duplicados no suman. Fixture de mediciones actual copiado sin cambio. No prueba de navegador, APIreal ni persistencia.

Aún pendiente cerrar fixture público676 real al RELEASE, y raíz debe autorizar integración. Hasta entonces el candidato no es comportamiento de APP.

## Revisión WIP raíz:46 escenarios

Corregido universo agregado: valor y n/N sólo parejas válidas del mismo subconjunto; referencias legadas excluidas. Cuando ninguna pareja es válida se conserva referencia gris sin cobertura. Fixture1con2/5+legacy7=>1con2/5, no8. Leadselegibles debe coincidir con f.leads_30d cuando existe; desconocido/malformado no se aproxima. Entrada admite cuarto argumento ahoraMs(defaultDate.now) únicamente como validación del corte, nunca fecha de lectura;+5min futuro del mismo día bloqueado con reloj fixture determinista. Pendiente slotsfinales676 de periodo/fuente para agregado: no declarar integración ni currentcoverage hastaRelease.

## RELEASE definitivo: puente676.3 y portableAPP

66 escenarios677 PASS+4247+59717=90. Fuente676.3 fijada SHA f93f924a4bfd4730f2f67086e871c93dccb1fc7a0943dfd607e27bfded8ae2c0. Puente ejecuta publico_fixture676 y asignaciones AST reales de fuente, rama sin_tocar y constructor sin_tocar_publico676; no importar generador ni main. Entrada pública y cobertura pública finales llegan a helper/renderer, y los vínculos ajenos, hora original distinta y descriptor ausente permanecen desconocidos/referencia. Ahora se comprueba también ficha de indicador del puesto: N/K gris, no porcentaje vigente.

SinIntento exige versión676.1, CID/SID,30d cerrados naturalesMadrid desde/cohorte_hasta, cut/horaoriginal coherentes, relojvalidación y elegibles==leads30d. Legacy672 sincut conserva número como referencia gris pero NON/K acreditado. Subset observado y N/K se suman del mismo universo; fallback referencia sólo si no hay valor medido y suma safeint (overflowunknown). Hoy/vigente se separa de observado: captura deayer1con2/5 se conserva con fecha en título pero colorgris; hoy equivalente ámbar si señal positiva acreditada, nunca verde por0parcial. Unidaddetalle no utiliza todos los leads para subset.

Artefactos de integración dentro portable_APP: modulos/crm.js y modulos/_contacto_observado_677.js; prueba propia probar_contacto_crm_677.cjs; puente_publico_crm_677.py; fixturebaseline_crm_677.js contiene sólo dos funciones renderer anteriores, no fuente completa; fixture_harness_crm_677.cjs contiene DOM ficticio. Puenteportable importa probar_mensajes_crm_676 relativo y éste usa fuentes_crm/generar_crm.py; NOpathsR ni hashcandidateWIP hardcoded. Las copias fuente676/helpermediciones en staging son dependencias de prueba, NO artefactos para sobreescribirlos en APP.

Regresiones424/597 sólo necesitan añadir dependencia real677 a sus loaders; se han adaptado en copiaaislada sin relajar ni cambiar assertions. Raíz puede hacerlo durante integración. SintaxisESM de helper/candidatoPASS. APP CRM baseline sigue da833562… intacto. NoGit/provider/publicación/runtime.

Comando desde depósito: node portable_APP/probar_contacto_crm_677.cjs. Desde APP trasintegración: node probar_contacto_crm_677.cjs. Manifest_677.json contiene hashes finales. Las secciones WIP anteriores conservan el proceso de revisión, pero este cierre sustituye los pins/casos y pendientes decontrato allí descritos. Limitación: no obtiene nuevas conversaciones ni convierte el snapshotlegacy actual en lecturavigente.

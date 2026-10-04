# 671B · Revisión independiente de comparativa por nicho

Fuentes revisadas: modulos/_paid_mediciones.js/resumenNichoPaid671 y captacion.js/pEquipo comparativa por nicho. Sólo lectura; transporte/estado/provider/APP sin cambios.

## P2 reproducido: ventana no acredita siete días cerrados

Función actual acepta descriptor220.1 cuyos desde/hasta coinciden con d.ventanas[7d], pero sólo comprueba desde<=hasta. El nombre de clave no acredita duración ni cierre. Fixture idéntica en EUR/gasto100/leads10/IDs válidos da CPL10 y completa:true tanto en semana correcta27sep–3oct como en11sep–3oct (23fechas),3oct–3oct (1fecha),28sep–4oct (incluye hoy abierto, reloj4oct). La UI rotula siempre «Comparativa por nicho ·7d» y CPL «Misma semana». No hay bypass de grants demostrado; es precisión temporal del agregado.

Propuesta mínima: fecha explícita hoy válida; intervalo exactamente6 días entre límites (7fechas) y hasta<hoy. Si contrato exige copia última semana cerrada, hasta=hoy−1, consistente con medirCplPaid. Rechazo conserva unknown/null, no fabrica0 ni altera filas/Score. Añadir negativos1día/23d/hoy y positivo7cerrados. No implementado por auditor.

Reproducción: R/probar_revision_nichos_paid_671B.cjs usa función real importada y sólo datos ficticios; cuatro casos verifican comportamiento actual. Ejecución propia probar_nichos_paid_671.cjs:14PASS. Sus negativos moneda/ocultación financiera/overflow/duplicados dentro grupo/descriptores/unknown y0legítimo siguen pasando.

## Límites revisados

Helper no autoriza cartera; consume filas que el caller considera scoped y dinero===true. Es correcto no sumar gasto si cualquier cuenta del grupo carece de grant; no hay CPL mezclando unidades o monedas distintas. El callsite agrupa antes por nicho, por tanto la unicidad del helper sólo dentro de cada grupo no detecta mismo CID con nichos distintos: riesgo de integridad adicional si fuente contiene filas duplicadas; no probado en renderer completo y no fuga demostrada. Recomendable filtro/denegación global antes agrupación como defensa futura, sin inventar identidad.

No prueba de API/DOM de aplicación completa, permisos revocados en vivo, autenticación productiva o productor fuente. No datos reales, credenciales, red, Git ni runtime.


## Retest posterior — RELEASE independiente

ROOT corrige en APP semana exactamente6d entre extremos y hasta=hoy−1. Fuente revisada: gate `semana` antecede descriptor y conteos. 15 pruebas671 PASS y4 independientes PASS: semana correcta conserva CPL10/leads10/completa:true;23d/1d/hoy abierto devuelven CPL/leads null y completa:false. No se exige datos_hasta adicional ni se cambia el contrato220.1. Corrección temporal aceptada; límites de autoridad upstream y posible duplicidad entre nichos siguen siendo los descritos, sin bypass probado. APP no modificada por auditor.

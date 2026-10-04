# 673 — Revisión local CRM: entregabilidad de RO

Candidato original aislado, posteriormente integrado en APP con autorización; ver cierre, sin navegador ni datos privados ni llamadas externas. Alcance exclusivo bloque final Entregabilidad del correo de pintarFlujos (crm.js635–639). No cambios en tabla7columnas, métricas, acciones531, leads369, citas334, permisos ni score.

Defecto reproducido con función render real y semaforo real congelado: rebote_pct='0' o false aparece verde y0%, aunque no es número observado. Un valor1 con fecha histórica también aparece verde. Ausente y null ya eran grises/—; no se atribuye ese defecto a esos dos casos. NaN generaba rojo, no señal acreditada.

Autoridad de la referencia: fuentes_crm/generar_crm.py681 fija una auditoría2.4 con fecha1Oct; línea682 aclara que las subcuentas cliente no proporcionan rebote por API. Se conserva esa auditoría como referencia de RO, no como salud actual acreditada ni de clientes.

Candidato: tipos number finitos0–100 y fecha calendario exacta YYYY-MM-DD; sin ellos—gris. Cero explícito y positivos se conservan como números de referencia grises. Encabezado breve identifica auditoría anterior, fuente+fecha visibles; reglas y nota original pasan a Fuente y límites cerrado. No se inventa descriptor de completitud, quejas ni ventana. No se usa fecha de lectura global para rejuvenecer auditoría.

20 escenarios PASS: missing/null/string/boolean/NaN/Infinity/negative/outofrange/containers,0/1/2.4/100, fechas imposibles/malformadas, revocación vigente y datos de entrada inmutables.3 fixtures ejecutan baseline y demuestran verdes previos. Sintaxis ESM candidata PASS. Formatter numérico de fixture reproduce coerción; lo decisivo en negativos es estado y tipo antes de formatear. Render completo pintarFlujos y semaforo congelado provienen de fuente actual. No test de integración backend ni navegador realizado.

Baseline SHA cd69bdcee47e35ef9fc93e49e8605bf341576b5e2d0b4ef17a5ed32087de1ea1.
Candidato SHA1a62666620e1eb5574211881e0ddc3833bb6e64a73a9ca7ca9325b56b41185a2.
Diff candidato.diff; prueba portable probar_entregabilidad_673.cjs; manifest.json. No integrar sin comparar baseline actual y autorización de ownership.


## Cierre673: integración autorizada

Renombrado depósito para no colisionar670 cerrado. Se añade hoy válido exacto y auditoría<=hoy: fecha futura/sin hoy/fecha hoy imposible ocultan sólo número; fecha documental válida se conserva como referencia.25 escenarios PASS y3 reproducciones baseline; regresiones4247 y59717 PASS, sintaxis ESM PASS. Archivo APP sólo modulos/crm.js y tres nuevos fixtures/test; sin otros cambios de producto ni runtime. Prueba portableAPP usa fixturebaseline_crm_673.js y fixture_semaforo_673.js, sin importsR. SHA CRM integrado da833562b3bad2fa2692c0aa33834bcc911e674c61e1358457f24d84a0e1ffa5. Baseline cd69… comprobado antes de copia. No endpoint ni permisos ni métricas de otras tablas modificados.

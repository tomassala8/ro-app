# 632 · Recorte económico estructurado de lecturas

RELEASE. Sólo servir.py/recorte_importes_lectura588, adaptación de dependencias reales del harness588 y prueba nueva probar_recorte_estructurado_632.py. No se modifican matrices, persistencia, escrituras, proveedores, migración/v2, runtime ni UI. No commit ni push.

## Cambio

El helper que ambas rutas ya llaman después del scope compone la unión de patrones económicos existentes de quitar_para para las dos identidades actuales. Excluye el patrón de leads: esta reparación sólo cubre los cuatro grants financieros. Aplica recortar_doc a la fila estructurada y al JSON decodificado de vista_previa antes del saneado textual. No convierte números a strings. Datos aplanados de decisiones, respuestas anidadas y arrays de vista_previa quedan incluidos.

Se conserva la representación original de vista_previa cuando el contenido no cambia. Se mantienen id/estado/recibos, horarios y números operativos. Administración conserva cuota/cobros, Trafficker CPC autorizado, Dirección importes autorizados; ver como Account no eleva autoridad. Permanecen las guardias actuales544/550 de identidad, clientes y revisión final del ámbito. No se modifica el contrato de lectura de rastro ni otras rutas.

## Evidencia

Antes del parche: cinco de seis pruebas nuevas fallaban por conservar los campos económicos; el positivo Dirección pasaba. Después: seis pruebas nuevas PASS. Ejecutadas con funciones actuales extraídas por AST, reglas P reales y SQLite temporal. Cubren los cuatro grants denegados, aliases conocidos, anidación/respuestas, array serializado, Administración/Trafficker/Dirección, intersección real-vista, horas/horas pautadas y cero operativo.

119 PASS en total:632 (6),588 (10),589 (20),581 (24),603 (29),607 (19),579 (11). Sintaxis servir.py validada con AST sin importar el servidor. El harness588 ahora carga recortar_doc/quitar_para y constantes reales del extractor589; no relaja ninguna aserción.

No se acredita circuito HTTP productivo ni inexistencia de importes residuales en campos desconocidos/textos sin tipado. La auditoría629 identifica el problema; este RELEASE repara sólo ese contrato reproducido. Reinicio y publicación quedan a cargo de raíz.

## SHA-256 del RELEASE

- servir.py: 4d95c777df2ce95abee1761f47f52af6e9db24a124b2f19a69ada986d3b68624
- probar_recorte_estructurado_632.py: dd2e590873d3c67a626fb2be1c0980f980e22bad4e5070b7ed1a71a4906b466d
- probar_importes_acciones_decisiones_588.py: 91e274ca395d5bd6aea29994e6051829c465bd02f5c31a87fdf9b30678094570

## Compatibilidad de harness AST tras integración central

Se añadieron las dependencias reales589 a probar_lectura_acciones_538.py, probar_contrato_acciones_crm_533.py y probar_lecturas_sincronia_585.py. Es compatibilidad de extracción de funciones; producto sin cambios adicionales, sin stubs ni aserciones relajadas. 61 PASS:558/538/533/536/588/632/585.

- probar_lectura_acciones_538.py: 11a631bbd49ee3d569b65745221878c2c76d609d118389da82724c55ff9d8052
- probar_contrato_acciones_crm_533.py: 31e57606cc67923e444de422a75b01281b2c0514e38d1d5f1dbb8e20d4f5f525
- probar_lecturas_sincronia_585.py: 92388dd3ee0b259af12eafe5c2e7cb41a0f6ea2b26bfb5b4b5f1582fbf2c11a9

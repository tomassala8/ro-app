# Entrega 658 a Cursor · evidencia y papeles del encargo Accounts

Nota portable: las rutas siguientes son relativas a la carpeta de entrega del código. No contiene datos reales ni requiere credenciales, proveedores, API o base principal. **658 no está implementado.** No cruzar el cambio de presentación/entrega con la revalidación657.

## Reproducción mínima y ubicaciones

- `consejo_metodo_308.py:68` → `recomendaciones_metodo308`.
- `consejo_metodo_308.py:79`: comprobador_role=account, ejecutor_operativo=trafficker; responsable_id identifica al ejecutor actual, no al comprobador ni al participante histórico.
- `consejo_metodo_308.py:81`: evidencias contienen regla/fecha de consulta, aunque metodo_308 conserve fechas de reunión/revisión.
- `modulos/_prioridades_contexto_337.js:39` → encargoPrioridades337 no serializa metodo_308 ni los papeles separados.
- `modulos/prioridades_cliente.js:159`: «Responsable» se muestra desde responsable_id; no se distingue el comprobador.

Fixture no empresarial: cliente_id=`fixture`; persona activa `paid_fixture` con puesto trafficker y asignación principal/confirmada vigente; otra persona activa `account_fixture` con puesto account. Documento de consulta2026-10-04, última celebración2026-10-01 con fuente Zoom, próxima revisión calculada2026-10-16; cobertura parcial. Proyectar mediante funciones puras308, elegir recomendación area=accounts y pasársela a encargoPrioridades337 con nombre `Cliente fixture`.

Resultado reproducido: metodo_308 mantiene ambas fechas y agenda/incumplimiento=null. El encargo dice «Última celebración registrada» pero no contiene2026-10-01 ni2026-10-16; sí contiene2026-10-04 como evidencia de regla/consulta. El texto tampoco distingue comprobador y ejecutor. No demuestra envío/asignación errónea: borrador actual sin responsables_verificados mantiene bloqueos.

Prueba disponible en el depósito auxiliar `revision_accounts_metodo_658/probar_accounts_metodo_658.py`: seis casos de funciones308 AST y helpers JS reales. Su ruta al binario Node pertenece al entorno local original: para otro equipo resolver Node mediante PATH antes de ejecutar; no presentar ese script como portátil sin esa adaptación. La reproducción anterior y los datos ficticios son independientes de máquina.

## Criterio seguro de corrección

1. Conservar en el encargo la última celebración ya validada y su fuente/fecha, separada de la fecha de consulta/regla. Sólo incluirla si el modelo validado la permite; sin fuente/fecha, desconocido. No reconstruir eventos por títulos/nombres.
2. Mostrar la próxima fecha como **revisión calculada**, nunca cita agendada ni celebración futura confirmada. No usar programación para satisfacer entrega de reunión celebrada.
3. Hacer explícitos «Comprobador: account» y «Ejecutor operativo: trafficker». Resolver IDs de comprobador únicamente desde silla actual canónica y confirmada; no reutilizar responsable_id de ejecución para afirmar autoría/participación histórica ni cambiar assignees automáticamente.
4. Mantener contacto semanal, reunión mensual y seguimiento quincenal como reglas distintas. Cobertura parcial no prueba ausencia de reunión ni incumplimiento.
5. Prueba de aceptación: encargo conserva ambas fechas con sus etiquetas/fuentes y papeles; sin celebración no inventa fechas; revisión/agendada e incumplimiento siguen separados; revocación mantiene las guardas existentes. Sin ampliar permisos ni crear tareas/envíos.

## Corte local: integrado frente a pendiente

| Frente | Estado comprobado localmente | Siguiente paso Cursor |
|---|---|---|
|640/641/644|Integrados por ROOT en corte645: eventos con ID/fuente tipados, conflictos globales/replay y propietario actual;644 portable13 pruebas. No acredita participación histórica ni cobertura exhaustiva.|Conservar contrato/negativas y no migrar eventos antiguos por inferencia.|
|657|Código APP coincide con candidato657 SHA f7028bc76b34c4a89ddd0e02ee548140c16a0ceb86938ee2eefda8569ec4b047. Doc657 inicial hablaba de candidato; esta comparación confirma incorporación de fuente, no nueva QA/runtime.|No revertir guards de ámbitos/roles/lecturas al implementar658. Revalidar pruebas del corte.|
|658|Auditoría/fixture; entrega pierde fechas y papeles. Sin parche de producto.|Implementar el criterio de arriba en308/encargo337/labels de Prioridades, con guards intactas.|
|652|Propuesta aislada NO integrada: fuente APP conserva baseline fd41b8c6540dd46572ceeb780c93a5e86b3d1a5843bcd2fb9c546e5fd5e53c47.26 pruebas sintéticas del candidato documentadas.|Revisar/aplicar patch652: totales/metadatos inválidos no completitud; conflictos ID entre location/status antes del filtro. No activar lector ni convertir stock won en venta/cobro/fecha cierre.|
|653|Propuesta aislada NO integrada: embudo_eventos.py APP conserva baseline656c5ce7d91d8d95dce385b25f41ae734e910dd8568c80d86b3a4458cce5a3f9.22 pruebas sintéticas candidato.|Revisar preflight global por(source,event_id), namespace de proveedor/tenant y whitelist de nuevo diagnóstico antes de integrar. API467 actual no soporta venta/asistencia/cualificación: no ampliar etapas ni tasas por aplicar el patch.|

652 está en `RECUPERACION_CODEX_2026-10-03/revision_cerradas_652`;653 en `RECUPERACION_CODEX_2026-10-03/revision_embudo_integridad_653`. Son depósitos de revisión separados: no copiarlos a producto ni activar por simple reemplazo. No se afirma cobertura100%, capacidad contractual ni ejecución de reuniones/ventas.

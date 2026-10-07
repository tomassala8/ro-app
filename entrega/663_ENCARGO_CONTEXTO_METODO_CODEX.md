# 663 · Contexto metodológico verificable en encargo IA

RELEASE helper y test locales. Sólo se modificó modulos/_prioridades_contexto_337.js; raíz es propietario del callsite de prioridades_cliente.js y agregó el cuarto argumento ctx.hoy. No backend308 ni permisos/helpers compartidos/Git/runtime/proveedores.

Firma: encargoPrioridades337(r,nombre,areas={},hoyActual=''). La sección adicional sólo existe con hoyActual ISO calendario válido e idéntico al hoy propio de método308. Sin cuarto argumento conserva encargo genérico; nunca usa reloj de lectura ni Date.now para renovar historia.

## Contrato

Regla/área paid o accounts exactas, cadencia15 entera, cliente canónico tipado y coherente entre recomendación/método, responsable_confirmado=true y responsable_id coherente (el ID no se imprime). Ejecutor_operativo debe ser trafficker y comprobador_role account para accounts o trafficker para paid. Fuente_regla exacta decision_humana_metodo_vigente; una evidencia metodológica actual con fecha igual al corte; agenda/incumplimiento null. Contacto semanal y reunión mensual siguen separados.

Última celebración: fecha calendario válida <=hoy; fuente de celebración del allowlist308. Revisión: fecha exactamente +15 días, calculada, explícitamente no cita ni programación. Si ambas fechas/fuente son null y estado confirmar_programacion, se escribe pendiente de evidencia sin inventar fecha; cobertura completa con celebración ausente se rechaza. Estado consistente con próxima revisión/cobertura; malformed, roles, fechas futuras/imposibles, regla ajena o reloj no coincidente omiten toda la sección nueva. Se conservan las evidencias genéricas autorizadas: una referencia histórica no se convierte en actualidad por este añadido.

No se serializan persona_id ni eventIDs ni se infiere el ID del comprobador. Fuente textual nueva sólo procede del allowlist, y utiliza textoSeguro real. No se añade HTML ni acciones.

## Verificación

43 grupos nuevos portables PASS: helper _tarea_ia+337 reales, fechas/reglas/owner/papeles/unknown/inmutabilidad/privacidad, generar real→308 actual662→encargo, textarea y copia reales en paid/accounts. 27 grupos regresión337 PASS. ESM/helper y sintaxis del test PASS. Todas las fixtures son ficticias; no red ni escrituras de negocio.

## Pendiente separado de ámbito

Por encargo explícito de raíz no se amplió ambitoPrioridades337 en este lote. Todavía se apoya sólo en clientesVisibles y filtra roles malformados en lugar de rechazarlos, sin intersección con catálogo actual ctx.clientes ni rechazo explícito activo:false/baja en ambos conjuntos. Es un hallazgo independiente para665; esta sección no añade concesiones ni sustituye autorización del servidor/caller. No se afirma cierre global de scopes.

## SHA-256

- `modulos/_prioridades_contexto_337.js`: `92c6605364e8a7ddaf2d415609468ec8a10a333ceed38a85a091095be91f6cbd`
- `pruebas_encargo_metodo_663.cjs`: `be81a88c2cf9a85d139e5a7f8d9a81c474a048ed3a2f5d58b9a61f34546fab25`

Pulido final de copy: «Ejecutor operativo: Trafficker» y «Comprobador: Account/Trafficker», sin nombres técnicos de campos. Misma validación y43 grupos PASS.

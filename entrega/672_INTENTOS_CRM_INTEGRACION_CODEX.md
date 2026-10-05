# 672 · Integración de intentos CRM


## Resultado

Fuente APP integrada tras verificar baselineSHA exacto. Se añadió probar_intentos_crm_672.py portable (APP=HERE) y fixture_intentos_crm_672.py mínimo con funciones/constantes y ramas anteriores, sin imports/config/IO del productor.13 pruebas nuevas +12 regresiones pruebas_cobertura_crm.py PASS. No se importó ni ejecutó main.

La revisión de compatibilidad añade intentos_medidos672: exige descriptor explícito, creación y corte compatibles. Un int0/int1 legacy sin descriptor o de otro corte conserva su dato original, pero no se certifica ni se usa para sin_tocar/medias corregidos. Caso adicional prueba ambas cifras y corte distinto. Fuentes actuales y snapshots no se regeneraron; por tanto las pantallas existentes conservan sus snapshots anteriores.

Consumidores revisados: crm.js sumar usa conteoCRM y todosdesconocidos devuelveNone; celda detalle719 admiteNone. pesoSub104 y orden269 usan or0 sólo para ranking (no se cambiaron). En el productor, tres agregados legacy584/626/761 de sin_tocar aún emplean or0: no excepción pero potencial0 agregado sin cobertura. Es una deuda separada, no declarada corregida ni usada para certificar saludglobal. en_1h/cuatro72h y clasificación del origen humano siguen limitados conforme nota anterior.

SHA fuente APP final: `351e948f005f93a0092a634b94118e0584e586595d21fd8aeb7c0a11dedf6724`. La sección inicial de este documento describe el primer candidato; la versión integrada incorpora la puerta de descriptor y13casos indicada aquí.

Detalle/reproducción: RECUPERACION_CODEX_2026-10-03/revision_intentos_crm_672/672_INTENTOS_CRM_CANDIDATO_CODEX.md.

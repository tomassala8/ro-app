# 654 · Resiliencia localizada del cerebro Paid/CRM

RELEASE de candidato aislado. No APP, Git, runtime, fuentes privadas, proveedores ni migración/v2. Cambian sólo copias cerebro_operativo.py y meta_informe_291.py; paid_mediciones_331.py se incluye byteidéntico como dependencia pura.

## Fallos reproducidos

La función generar real se interrumpe al recibir secciones dict con forma string/list/bool/número (equipo, velocidad, citas, anuncios, etc.), una fila no dict dentro de anuncios o float(10**1000). La dependencia real medición291 también lanza OverflowError en math.isfinite de enteros enormes en series Paid. Ello elimina el resultado de todos los clientes de la llamada. Además los IDs numéricos/bool se convertían a strings e inventaban identidades.

`python3 probar_resiliencia_654.py --antes` carga las fuentes originales APP y reproduce 48 errores y un fallo en nueve métodos (exit1 deliberado, no FIX). La misma prueba con el candidato: **9 métodos PASS**, con múltiples subcasos. Las **27 regresiones originales probar_cerebro_operativo PASS** cargando candidato y dependencias reales. Python AST de tres fuentes: PASS.

## Corrección localizada

Se comprueban tipos de los contenedores antes de acceder con get. Cada sección inválida se convierte en objeto sin medición para esa sección únicamente y añade un límite `estructura_invalida_<campo>` sin datos raw. Las otras secciones y otros clientes se conservan; la prueba mínima usa un CRM con velocidad malformada y WhatsApp válido: conserva la recomendación WhatsApp de ese cliente y las Paid/CRM del cliente bueno. Un anuncio inválido no impide revisar otro anuncio válido de la misma lista.

Los documentos/colecciones no estructurados quedan explícitos en cobertura.estructuras_invalidas. No se interpreta CSV textual, no se adivinan claves ni se convierte texto en medición; su importador deberá producir el contrato de contenedores. cliente_id debe ser string explícito; no se fabrica identidad por coerción.

OverflowError se captura únicamente en las dos conversiones numéricas. El dato enorme es unknown, no cero. Si falla leads pero el gasto cero sigue acreditado, su comprobación específica se conserva; si falla gasto, no se emite sin-gasto. No hay catch alrededor de generar ni se silencian excepciones generales. hoy inválido sigue produciendo ValueError.

Fechas, columnas de recomendaciones, responsables válidos, criterios, umbrales Paid331 y reglas de comparabilidad permanecen. No se añade cobertura ni aprobación contractual ni se infieren ventas. Las fechas propias de cada fuente no se rejuvenecen.

## Límites y adopción

Propuesta para revisión Cursor/root, no función activada. La validación de ámbito sigue siendo responsabilidad del llamador anterior a generar. No es parser CSV ni auditoría de todas las dependencias arbitrarias; errores de programación ajenos a las conversiones/tipos identificados siguen visibles. Aplicar sólo el diff de las dos fuentes tras revisar hashes y ejecutar las suites en el destino.

## SHA-256

- `cerebro_operativo.py`: baseline `3291bd92f0fa6919d05329ac562f255052760049c928ed14295779de9582c3e3`; candidato `63378e62935d7ae388489ec8be88a837a0de7f8711d88c59a32a30977f114eae`
- `meta_informe_291.py`: baseline `3a074f5bf69ec3480dc75f76801b5f8efcd37a4cd9687aef827162e0b9982114`; candidato `a9b22a185f98504c033b335f9c768e08b0de85f5079f37640eae54fe77836258`
- `paid_mediciones_331.py`: baseline `1f5a298341f76e28e77a677e71755bbb330718ab9cf85c40347aea6d279721c5`; candidato `1f5a298341f76e28e77a677e71755bbb330718ab9cf85c40347aea6d279721c5`

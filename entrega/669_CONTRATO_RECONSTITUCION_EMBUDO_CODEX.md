# 669 · Contrato y reconstitución offline del embudo

Sólo candidato R. APP, lector activo, pins, caches, launcher y depósito470 intactos. No proveedor, credencial, HTTP ni regenerador. No se ejecutó el preparador sobre fuentes privadas reales: se verificó mediante caches sintéticos temporales.

## Cambio mínimo antes de integrar653/668

Única incidencia nueva del motor: `event_id_ambito_conflictivo` (contador entero seguro ≥0). Añadirla exclusivamente a `crm_embudo_api_467.INCIDENCIAS_MOTOR`; propuesta exacta en `467_whitelist_669.diff`. No añadirla a `DIAGNOSTICOS` de466/620: éstos describen el adaptador y el DTO público no expone incidencias del motor.

El lector467 actual rechaza esa incidencia cuando existe; el caso de contrato reproduce el rechazo y la aceptación tras modificar sólo la whitelist en un namespace aislado. Su ausencia sigue siendo válida: el motor omite contadores0. No inventar incidencias ausentes ni aceptar códigos desconocidos. No añadir ventas, asistencia o cualificación a etapas acreditadas:467 y620 siguen rechazando sus positivos; las reservas son creación histórica (incluidas canceladas), no celebración, asistencia, venta o cobro.

## Pins y fuentes

Manifest470 contiene hashes de `adaptador466` y `embudo_eventos`, más fuentes exactas `ghl_vivo`, `crm`, `act`. Su motor sigue anclado a656c5… . El motor668 nuevo esfa0186… . Aunque el agregado quede byte a byte idéntico, cambia el manifest de código: debe revisarse un NUEVO depósito y sus dos pins. Nunca aceptar el código antiguo para evitar reconstituir ni reescribir470.

| Fuente/código | SHA256 verificado |
|---|---|
| embudo_eventos APP (baseline) | 656c5ce7d91d8d95dce385b25f41ae734e910dd8568c80d86b3a4458cce5a3f9 |
| motor aislado668/653 | fa0186a9c7f8122c9eb0efa281d6999f4e777305c449e14af6d18b5949777e2d |
| adaptador466 APP | bc7791e800257929690313643573065df79bd867c4e8b9a31355a39211ea87a2 |
| lector467 APP | f72f2671200a6ee0776b3504abf40f65da98f5d4c39ba44411366ce601bc90c9 |
| helper620 APP | 1030ee3115497a441c258e1837e6f99311546ca73a7aaee1cc0305b2bee84d6e |
| puente621 APP | 89e247bc53a2e77810056bf70af60a181fcfe0559cfcb8cb1b54e93c2adacb20 |
| preparador669 | caca2232915fe39a817b4531b4b4fa1d3768516c29d572c9313ad282de1ba91a |

## Preparador reviewable

`preparar_embudo_offline_669.py` carga mediante AST únicamente módulos puros del motor y adaptador466, sin importar productor, API o lector de secretos. Requiere motor y SHA explícitos. Extrae sólo constantes ACT de código; no ejecuta su generador. Lee tres caches locales exactos por NOFOLLOW, sin symlinks en la ruta, archivos regulares únicos ≤5MB, raw privado0600; JSON duplicado/NaN rechazado. Relee fuentes y código antes de devolver candidato; cambio de contenido aborta.

Enlaces por cliente/subcuenta exactos y únicos más ACT actual; ninguna heurística de nombre. La preparación no concede permisos de lectura:467 mantiene ACT y real∩vista, módulo y cliente_detalle antes/después del IO.621 mantiene su revalidación de fuentes, grants y pins antes/después de enriquecer.

Fecha original `hora` del cache se interpreta Europe/Madrid sólo si no es ambigua/inexistente/futura respecto a `--ahora` aware explícito. Conserva hora_fuente/corte originales; ventana30d cerrados hasta el día anterior al corte. No usa la fecha de reconstitución como frescura. La ausencia de eventos permanece desconocida y completaFalse; no se inventan0completos ni tasas.

Salida únicamente agregados466.1 (sin arrays de eventos, IDs de contactos o citas), manifest exacto compatible467, más `revision669.json` con hashes del preparador/políticaACT y conteos agregados. Publicación por renombrado de carpeta nueva dentro R:700 y archivos600; depósito existente se rechaza. No escribe caches ni paths fuera R. Los hashes/fingerprints privados de subcuenta siguen sólo en el candidato privado, nunca se publican a UI.

Ejemplo de ejecución futura por root, con variables de ruta definidas localmente:

```sh
python3 -B "$SCRIPT669" --app "$APP" --motor "$MOTOR668" --motor-sha fa0186a9c7f8122c9eb0efa281d6999f4e777305c449e14af6d18b5949777e2d --ahora "$RELOJ_UTC_AWARE" --salida "$R/staging_embudo_669_revision1"
```

No se invocó esta CLI en esta entrega. Si falta cualquier cache, está corrupto, hay un join ambiguo sin filas o fuente/código cambió, aborta con código fijo sin volcar contenido. No requiere proveedor para reconstituir evidencia existente; no puede obtener nueva frescura, etapas nuevas o cobertura exhaustiva sin otra captura autorizada.

## Verificación

13 pruebas669 PASS; 18 lector467,20 helper620 y12 puente621 PASS (63 total). La suite620 requiere cwdAPP; primera ejecución fueraAPP falló sólo por su path relativo, repetición enAPP PASS sin editarla.

Seis contratos principales cubiertos: (1) nuevo diagnóstico rechazado por lector antiguo y aceptado sólo tras whitelist aislada, (2) diagnóstico ausente compatible, (3) unknown/bool/negativo rechazado, (4) etapas no acreditadas rechazadas, (5) manifest motorSHA explícito/fuente conservada, (6) permisos/rotación de fuente del lector y puente existentes conservados. Además: candidate668 por466 real con namespaceSID, vacío desconocido, fuente futura, JSON ambiguo, identidadACT duplicada, sourcechanged, symlink/mode, publicación privada y no sobrescritura.

El preparador no activa467 ni conecta UI. Pendiente root: aplicar motor668 y whitelist467, ejecutar reconstitución local, auditar candidato/manifiesto y recortes, actualizar pins con los bytes finales y verificar runtime autorizado/revocado. No hay certificado global de paridad o de ejecución externa.

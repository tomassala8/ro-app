# Cuaderno de la noche · migración 4→5-oct-2026

ESTADO: SIN EMPEZAR

Leyenda: ⬜ pendiente · 🔄 en curso · ✅ hecho (puerta verde) · ⚠ plan B aplicado (ver motivo).
Cada paso: detalle en `migracion/PROMPTS_CURSOR.md` (mismo código). Hasta 3 intentos con enfoques distintos; luego, su plan B.
Formato al cerrar: `✅ F1.2 · 23:14 · <resultado en una línea> · puerta: ~/RO_MIGRACION/puertas/f1.md`

## En curso

(nada)

## Fase 1 · Referencia

- ⬜ F1.1 Inventario del código del Mac y notas de la noche. Plan B: si `--comparar` falla, inventario sin comparar y apuntarlo.
- ⬜ F1.2 Escáner de secretos sin falsos positivos de v2 (commit propio). Plan B: dejarlo como estaba y apuntar los falsos positivos.
- ⬜ F1.3 Instantánea del código del Mac en la rama `migracion/v2` (tras el escáner) y copia de la base. Plan B: si el escáner marca algo, NO se commitea ese fichero; se apunta y se sigue.
- ⬜ F1.4 Servicios de referencia y grabaciones: contrato, vectores, fotos. Plan B: si las fotos de una pantalla salen vacías o con error en la app de hoy, se apunta y esa pantalla queda fuera de la comparación de fotos (no de la del contrato).
- ⬜ F1.5 Casos de escritura (todos los POST de servir.py: uno que funciona y uno que se deniega). Plan B: ninguno; es imprescindible.
- ⬜ F1.6 `migracion/baterias.sh` con todas las baterías que admiten puerto, verde contra la app de hoy (8770). Plan B: las que fallan ya contra la app de hoy se apuntan y se quedan fuera (no se arreglan esta noche).
- ⬜ F1.7 `bash migracion/puerta.sh f1` en VERDE. Push de la rama. Plan B: ninguno; repetir lo que falte.

## Fase 2 · Base Postgres y la app de hoy sobre ella

- ⬜ F2.1 Tabla `avisos` de la tubería → `tuberia_avisos` en `despliegue/estado.py` (commit propio). Plan B: dejarla y copiar solo `local.db` (la tubería empieza vacía en Postgres); apuntarlo.
- ⬜ F2.2 Si el inventario trae tablas o columnas nuevas: `rehacer_base.sh` y revisar el diff de `schema.prisma`. Plan B: ninguno; sin esto se pierden columnas.
- ⬜ F2.3 Postgres arriba, `pnpm db:deploy`, copia «cuadrada» de `local.db.antes` (y `tuberia.db.antes`), `publicacion.py publicar data`.
- ⬜ F2.4 Legado (servir.py sobre Postgres) arrancado y `bash migracion/puerta.sh f2` en VERDE, arreglando `despliegue/base.py` lo que haga falta (commits propios, cada uno con su prueba). Plan B: rutas que no cuadran tras 3 intentos → `~/RO_MIGRACION/excepciones.txt` con el motivo; apuntadas como bloqueo para el piloto.

## Fase 3 · La app nueva entera (por el proxy)

- ⬜ F3.1 `servicios.sh arrancar` (api y web) y `bash migracion/puerta.sh f3` en VERDE. Push. Plan B: arreglar fontanería del proxy; si no, apuntar y seguir con la fase 4.

## Fase 4 · Motor de permisos en TypeScript

- ⬜ F4.1 `permisos.py` → `v2/packages/permisos` función a función, con «ver como» explícito, y enchufarlo como el motor de `v2/apps/api/src/permisos/` (sustituye a `MotorSinPortar`). `bash migracion/puerta.sh f4` al 100 %. Máximo 90 minutos. Plan B: apuntar los vectores que fallan y saltar la fase 5 entera (⚠ en F5.*).

## Fase 5 · Rutas a Nest (un grupo cada vez; cada uno: módulo + RUTAS_EN_NEST + puerta f5)

- ⬜ F5.1 identidad (guarda global) + sesion
- ⬜ F5.2 datos (`/api/modulo/**`)
- ⬜ F5.3 clientes y logos
- ⬜ F5.4 buscar, contadores e indicadores
- ⬜ F5.5 perfil y preferencias
- ⬜ F5.6 rastro (lectura, escritura y verificar)
- ⬜ F5.7 decisiones y opiniones
- ⬜ F5.8 ajustes y ver_dato
- ⬜ F5.9 acciones, avisos y canales
Plan B de cada grupo: quitar sus rutas de `RUTAS_EN_NEST` (vuelven al proxy), guardar el módulo en la rama `intento/<grupo>`, ⚠ y siguiente grupo.
Reloj: si faltan menos de 2 h para `RO_FIN_NOCHE`, los grupos que queden → ⚠ «sin tiempo» y a F5.10.
- ⬜ F5.10 Fallos pendientes de `migracion/PENDIENTES_LOGICA.md` (o de `~/RO_MIGRACION/PENDIENTES_LOGICA.md` si existe), de seguridad a presentación: cada uno con su prueba, su commit «L-n · …» y su estado en la lista. Máximo 90 min, pero los de seguridad se hacen aunque falte tiempo (antes de la fase 7). Plan B por fallo: se queda como estaba, con la prueba marcada pendiente, y va al informe (seguridad = bloqueo para el piloto).

## Fase 6 · Front en React + shadcn

- ⬜ F6.1 shadcn init (sin tocar el tema ni el CSS sin preflight), `src/lib/ctx.ts` (40 campos) y `PantallaPuente`.
- ⬜ F6.2 Carcasa en React en `/carcasa` con el puente para las 37 pantallas; fotos de `/carcasa` iguales que las de «/».
- ⬜ F6.3 Mudar la carcasa a «/» y `bash migracion/puerta.sh f6` en VERDE. Plan B: la carcasa se queda en `/carcasa` y «/» sigue siendo el front de hoy.
- ⬜ F6.4 Pantallas en React, una cada vez, de menos a más riesgo (lista en PROMPTS_CURSOR.md). Plan B por pantalla: se queda con el puente.
Reloj: si falta menos de 1 h para `RO_FIN_NOCHE`, lo que quede → ⚠ «sin tiempo» y a la fase 7.

## Fase 7 · Cierre (la última hora, pase lo que pase)

- ⬜ F7.1 `docker compose --profile completo up --build` y puerta f3 contra los contenedores. Plan B: apuntar qué falla en el contenedor; la puerta se pasa contra los servicios locales.
- ⬜ F7.2 `v2/render.yaml` (ro-web, ro-api, ro-legado una sola copia, ro-base), sin llaves. Plan B: ninguno; es solo escribir.
- ⬜ F7.3 `migracion/INFORME_NOCHE.md` para Tomás (con el estado de cada fallo de `PENDIENTES_LOGICA.md`) y `bash migracion/puerta.sh f7` (incluye el ensayo de restauración).
- ⬜ F7.4 Commit, `git push origin migracion/v2` y `ESTADO: TERMINADO`.

## Intentos y notas

(aquí, por paso: «F2.4 · intento 1 · hipótesis → resultado»)

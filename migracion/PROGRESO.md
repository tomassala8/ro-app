# Cuaderno de la noche · migración 4→5-oct-2026

ESTADO: SIN EMPEZAR

Leyenda: ⬜ pendiente · 🔄 en curso · ✅ hecho (puerta verde) · ⚠ plan B aplicado (ver motivo).
Cada paso: su sección en `migracion/PLAN_NOCHE.md` (el plan de la noche, escrito y revisado antes) y el detalle en `migracion/PROMPTS_CURSOR.md` (mismo código). Hasta 3 intentos con enfoques distintos; luego, su plan B.
Formato al cerrar: `✅ F1.2 · 23:14 · <resultado en una línea> · puerta: ~/RO_MIGRACION/puertas/f1.md`
Mientras dura: `🔄 F2.4 · 01:10 · intento 2/3 · <qué estás probando>` (el número de intento va en la línea del paso: si te relanzan, sigues por ahí). En F5.10, con el fallo en curso: `🔄 F5.10 · 01:10 · L-03 · intento 2/3 · <qué>`.
Al retomar, arranca solo lo de fases cerradas: `viejo` tras F1.4, `legado` tras F2.3, `api` y `web` tras F3.1. Nunca un `servicios.sh arrancar` a secas antes de F2.3: crearía tablas en `ro_app` vacía.

Fin de la noche: (si `RO_FIN_NOCHE` está vacío, escribe aquí la hora de empezar + 8 h en la primera vuelta y úsala como fin)

Cortes del reloj (se miran con `date` al empezar CADA vuelta, no solo al principio):
- F5.1–F5.9: hasta **4 h** antes del fin. Lo que quede → ⚠ «sin tiempo».
- F5.10: hasta **3 h** antes del fin, todos (los de seguridad van primero en el orden; no tienen prórroga).
- F5.11: hasta **2 h** antes del fin.
- Fase 6: hasta **1 h** antes del fin.
- Fase 7: la última hora, pase lo que pase.

## En curso

(nada)

## Fase 1 · Referencia

- ⬜ F1.1 Inventario del código del Mac y notas de la noche. Plan B: si `--comparar` falla, inventario sin comparar y apuntarlo.
- ⬜ F1.2 Escáner de secretos sin falsos positivos de v2 (commit propio). Plan B: dejarlo como estaba y apuntar los falsos positivos.
- ⬜ F1.3 Instantánea del código del Mac en la rama `migracion/v2` (tras el escáner), las ramas de `migracion/RAMAS_A_JUNTAR.txt` juntadas (PR #2, #3 y #4 del 4-oct), copia de la base y copia congelada de la app de hoy en `~/RO_MIGRACION/ref`. Plan B: si el escáner marca algo, NO se commitea ese fichero; se apunta y se sigue.
- ⬜ F1.4 Servicios de referencia y grabaciones: contrato, vectores, fotos (con sus tiempos), y `excepciones_solidez.txt` con los fallos heredados conocidos (N-13). Plan B: si las fotos de una pantalla salen vacías o con error en la app de hoy, se apunta y esa pantalla queda fuera de la comparación de fotos (no de la del contrato).
- ⬜ F1.5 Casos de escritura (todos los POST de servir.py: uno que funciona y uno que se deniega). Plan B: ninguno; es imprescindible.
- ⬜ F1.6 `migracion/baterias.sh` con todas las baterías que admiten puerto, más `despliegue/pruebas_noche.py --solo-solidez` (último dato bueno de las fuentes), verde contra la app de hoy (8770). Plan B: las que fallan ya contra la app de hoy se apuntan y se quedan fuera (no se arreglan esta noche).
- ⬜ F1.7 `bash migracion/puerta.sh f1` en VERDE. Push de la rama. Plan B: ninguno; repetir lo que falte.

## Fase 2 · Base Postgres y la app de hoy sobre ella

- ⬜ F2.1 Tabla `avisos` de la tubería → `tuberia_avisos` en `despliegue/estado.py` (commit propio; `despliegue/pruebas_noche.py` ya lee los dos nombres: no lo toques). Plan B: dejarla y copiar solo `local.db` (la tubería empieza vacía en Postgres); apuntarlo.
- ⬜ F2.2 Si el inventario trae tablas o columnas nuevas: `rehacer_base.sh` y revisar el diff de `schema.prisma`. Plan B: ninguno; sin esto se pierden columnas.
- ⬜ F2.3 Postgres arriba, `pnpm db:deploy`, copia «cuadrada» de `local.db.antes` (y `tuberia.db.antes`), `publicacion.py publicar data`.
- ⬜ F2.4 Legado (servir.py sobre Postgres) arrancado y `bash migracion/puerta.sh f2` en VERDE, arreglando `despliegue/base.py` lo que haga falta (commits propios, cada uno con su prueba). Plan B: rutas que no cuadran tras 3 intentos → `~/RO_MIGRACION/excepciones.txt` con el motivo; apuntadas como bloqueo para el piloto.

## Fase 3 · La app nueva entera (por el proxy)

- ⬜ F3.1 `servicios.sh arrancar` (api y web) y `bash migracion/puerta.sh f3` en VERDE. Push. Plan B: arreglar fontanería del proxy; si no, apuntar y seguir con la fase 4. **Si F3.1 queda ⚠: F5.1–F5.9 y F6.x → ⚠ sin intentarlo; F5.10 se cierra con su prueba + `puerta.sh f2`.**

## Fase 4 · Motor de permisos en TypeScript

- ⬜ F4.1 `permisos.py` → `v2/packages/permisos` función a función, con «ver como» explícito, y enchufarlo como el motor de `v2/apps/api/src/permisos/` (sustituye a `MotorSinPortar`). `bash migracion/puerta.sh f4` al 100 %. Máximo 90 minutos. Plan B: apuntar los vectores que fallan y saltar los grupos de rutas (⚠ en F5.1–F5.9). F5.10 (arreglando solo en el legado: `servir.py`, `permisos.py`, `reglas_permisos.json`) y F5.11 siguen.
- ⬜ F4.2 Pruebas de permisos que impiden volver atrás (anexo de `PENDIENTES_LOGICA.md`, punto 8), en `test/*.e2e-spec.ts` (las lanza `puerta.sh` f3/f5/f6/f7). Plan B: `it.todo` con su motivo.

## Fase 5 · Rutas a Nest (un grupo cada vez; cada uno: módulo + RUTAS_EN_NEST + puerta f5)

- ⬜ F5.1 identidad (guarda global) + escritor del rastro de «ver como» (`RASTRO_VER_COMO`) + sesion. **Si F5.1 queda ⚠, F5.2–F5.9 → ⚠ sin intentarlo** (sin identidad ni rastro, toda ruta de Nest falla) y a F5.10.
- ⬜ F5.2 rastro (lectura, escritura y verificar)
- ⬜ F5.3 datos (`/api/modulo/**`)
- ⬜ F5.4 clientes y logos
- ⬜ F5.5 buscar, contadores e indicadores
- ⬜ F5.6 perfil y preferencias
- ⬜ F5.7 decisiones y opiniones
- ⬜ F5.8 ajustes y ver_dato
- ⬜ F5.9 acciones, avisos y canales
Detalle de los nueve: sección «F5.x» de `PROMPTS_CURSOR.md`.
Plan B de cada grupo: quitar sus rutas de `RUTAS_EN_NEST` (vuelven al proxy), guardar el módulo en la rama `intento/<grupo>` (cómo, en «F5.x»; también si ya hiciste commit), ⚠ y siguiente grupo.
Reloj: ver «Cortes del reloj» arriba (grupos hasta 4 h antes del fin).
- ⬜ F5.10 Fallos pendientes (L-01…L-49 del hilo de feedback y N-01…N-22; L-01 y L-21 primero; D1–D8 ya contestadas, lo «pendiente» no se toca) (N-01 a N-12 son la copia propia de las APIs y «nunca ceros»: `PLAN_MAESTRO.md` §2.5) de `migracion/PENDIENTES_LOGICA.md` (o de `~/RO_MIGRACION/PENDIENTES_LOGICA.md` si existe), de seguridad a presentación: cada uno con su prueba, su commit «<id> · …» (L-n o N-n) y su estado en la lista. Por fallo: su prueba + `puerta.sh f5 --rapido`; la puerta completa, una vez al acabar cada bloque (seguridad, datos, funcional, presentación). Las pruebas nuevas o cambiadas van en ficheros NUEVOS (`migracion/pruebas_L-<n>.py`, `despliegue/pruebas_solidez_N-<n>.py`); nunca se tocan los `pruebas_*.py` ni `pruebas_noche.py` que ya existen (juzgan). Intentos: hasta 3 **por fallo**, no por paso, contados en «Intentos y notas» («F5.10 · L-07 · intento 2 · …»); la línea del paso dice qué fallo llevas. Reloj: hasta 3 h antes del fin. Plan B por fallo: se queda como estaba, con la prueba marcada pendiente, y va al informe (seguridad = bloqueo para el piloto).
- ⬜ F5.11 Ensayo de escalados sobre Postgres (`migracion/escalados.py`, `PLAN_MAESTRO.md` §2.9): alerta y aviso automático vencidos → «sube a X» a la persona correcta, una vez. Plan B: apuntar qué no escala como bloqueo para el piloto.

## Fase 6 · Front en React + shadcn

- ⬜ F6.1 shadcn init con versión fijada (sin tocar el tema ni el CSS sin preflight; tokens nuevos a `ro-tema.css`), `src/lib/ctx.ts` (40 campos) y `PantallaPuente`.
- ⬜ F6.2 Carcasa en React en `src/app/carcasa/`, con el puente para las 37 pantallas; con `RO_CARCASA=1` «/» la enseña sin cambiar la dirección (sin la variable, «/» sigue siendo el front de hoy); fotos con la variable iguales que las de hoy.
- ⬜ F6.3 La carcasa encendida por defecto y `bash migracion/puerta.sh f6` en VERDE. Plan B: la carcasa se queda apagada (solo con `RO_CARCASA=1`) y «/» sigue siendo el front de hoy.
- ⬜ F6.4 Pantallas en React, una cada vez, de menos a más riesgo (lista en PROMPTS_CURSOR.md). Plan B por pantalla: se queda con el puente.
Reloj: hasta 1 h antes del fin; lo que quede → ⚠ «sin tiempo» y a la fase 7.

## Fase 7 · Cierre (la última hora, pase lo que pase)

- ⬜ F7.1 `bash migracion/servicios.sh parar web api` y `docker compose --profile completo up --build`: que los contenedores arranquen y respondan (la web del contenedor, en 127.0.0.1:3100: `/vivo`, `/api/elegir`). Después, `docker compose --profile completo stop api web`: la puerta f7 se pasa siempre contra los servicios locales (los vuelve a arrancar ella). Plan B: apuntar qué falla en el contenedor (p. ej. `RO_LEGADO_URL`, «Host no permitido») como bloqueo para el piloto.
- ⬜ F7.2 `v2/render.yaml` (ro-web, ro-api, ro-legado una sola copia con los bucles y el vigía, ro-base), sin llaves, con el grupo `ro-llaves` completo (`llaves_nube.py` sale con 0), sin `RO_AVISOS_SIN_BUCLE` y con el cron de copias cada hora (§2.10). Plan B: ninguno; es solo escribir.
- ⬜ F7.3 `migracion/INFORME_NOCHE.md` para Tomás (con el estado de cada fallo de `PENDIENTES_LOGICA.md`) y `bash migracion/puerta.sh f7` (incluye el ensayo de restauración).
- ⬜ F7.4 Commit, `git push origin migracion/v2` y `ESTADO: TERMINADO`.

## Intentos y notas

(aquí, por paso: «F2.4 · intento 1 · hipótesis → resultado»)

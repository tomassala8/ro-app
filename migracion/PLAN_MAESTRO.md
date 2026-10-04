# Plan maestro · la app de RO a Next + Nest + Postgres

**4-oct-2026 · versión 2.** Para que Cursor lo ejecute solo la noche del 4 al 5 de octubre, unas 8 horas, sin parar y sin nadie delante. Objetivo: que el 5 por la mañana la app nueva tenga **la misma cara, las mismas funciones y los mismos permisos**, sobre una base que escale, y un informe que diga con pruebas qué está listo para un piloto y qué no.

Stack de destino: **Next.js 16** (web) · **NestJS 12** (API) · **PostgreSQL 16 + Prisma 7** (base) · **shadcn/ui + Tailwind 4** (interfaz). Monorepo con **pnpm** en `v2/`.

> **Qué cambió respecto a la versión 1 (misma mañana del 4-oct).** La versión 1 pasaba todo de golpe y se paraba en cada puerta roja. La 2 sigue la técnica del «estrangulador»: **la app nueva está completa desde el minuto 0** porque, de entrada, Next y Nest pasan todo a la app de hoy, que ya corre sobre Postgres. Después, cada ruta y cada pantalla se muda a Nest y a React **solo cuando su puerta sale verde**. Si no sale, se queda como estaba y Cursor sigue con la siguiente. Nunca se para. Ensayado aquí con datos inventados: la app nueva entera responde **595 de 595** peticiones igual que la de hoy.

---

## 0. Las seis reglas que mandan sobre todo lo demás

1. **Nada cambia para quien usa la app.** Mismas pantallas, textos, colores, direcciones (`/#/mi-dia`), rutas de API, respuestas y 403. Si algo se ve o responde distinto, es un fallo, no una mejora. **La única excepción** son los fallos de lógica de `migracion/PENDIENTES_LOGICA.md`: esos se arreglan sí o sí (paso F5.10), cada uno con su prueba y su línea en las excepciones.
2. **Se demuestra, no se supone.** Una pieza solo se da por hecha con `bash migracion/puerta.sh <fase>` en **VERDE**. La puerta guarda su informe en `~/RO_MIGRACION/puertas/`.
3. **La app nueva siempre funciona entera.** Lo que no está migrado lo atiende la app de hoy a través del proxy. Una pieza migrada sustituye a la vieja solo con su puerta en verde; si no, se deshace y se queda la vieja.
4. **Cursor nunca se para y nunca pregunta.** Si algo falla, lo intenta otra vez con otro enfoque (hasta 3). Si sigue sin salir, aplica el **plan B** de ese paso (§5), lo apunta y pasa al siguiente. Las dudas se resuelven con la opción más conservadora y se apuntan para Tomás.
5. **Los datos reales no salen del Mac.** Grabaciones, vectores, fotos, casos y copias de la base van a `~/RO_MIGRACION/`. En el repositorio, solo datos inventados.
6. **Nada sale fuera.** Sin envíos, sin ClickUp real, sin bucles de avisos (`servicios.sh` y `puerta.sh` lo fuerzan). Nada de desplegar, ni tocar proveedores, ni `git push` a `main`.

---

## 1. Qué hay hoy

Lo genera `python3 migracion/inventario.py` en `migracion/inventario/` desde el código **del Mac** (incluidos los ficheros nuevos aún sin commit). Cifras a 4-oct en GitHub:

| Pieza | Hoy | Cuánto |
|---|---|---|
| Pantallas | `modulos/*.js` (JS sin framework, `render(contenedor, ctx)`) | 37 en el menú, 61 ficheros, ~36.000 líneas |
| Carcasa | `index.html` (con mapa de versiones, CSP y precarga), `app.js`, `carcasa.js`, `ayudas.js` | menú por puesto, «ver como», ⌘K |
| Diseño | `estilos.css` + `componentes.js` | 107 componentes |
| Servidor | `servir.py` + 11 ficheros «enchufados» | 37 + 62 rutas |
| Permisos | `reglas_permisos.json` + `permisos.py` + `permisos.js` | 21 puestos, 39 tipos, 92 ficheros con permiso, 133 acciones |
| Base | SQLite `local.db`; en la nube, Postgres vía `despliegue/base.py` | 40 tablas, rastro imborrable encadenado |
| Datos | la «tubería» `fuentes_*/generar_*.py` → `data/*.json` | 50 pasos, 86 generadores |
| Pruebas | `pruebas_*.py`, `despliegue/pruebas_noche.py` y las focalizadas de Astra | 16 baterías + las nuevas |

**La copia del Mac va por delante de GitHub** (nota de Astra, `migracion/NOTA_ASTRA.md`): triaje, horas, campañas, números semanales, método e histórico, reuniones, cabeceras. Por eso la noche parte del **código del Mac**, que la fase 1 guarda en una instantánea (commit en la rama `migracion/v2`, nunca en `main`) después de pasar el escáner de secretos.

---

## 2. La arquitectura nueva

```
navegador ──► Next (3000) ──► Nest (4000) ──► Postgres
                 │  páginas propias    │  rutas propias (RUTAS_EN_NEST)
                 │  (cuando pasan      │
                 │   sus fotos)        └──► proxy de legado ──► servir.py de hoy sobre Postgres (8771)
                 └── lo demás (/, app.js, modulos/…) ──► Nest ──► proxy ──► servir.py
```

```
v2/
├── apps/web          Next 16. next.config.ts › fallback: lo que no es página propia va a Nest.
│   ├── src/app/carcasa/        banco de trabajo de la carcasa en React; se muda a «/» al pasar sus fotos
│   ├── src/lib/ctx.ts          (fase 6) el MISMO ctx de app.js, 40 campos, en TypeScript
│   ├── src/components/ro/      (fase 6) componentes.js en React, mismas clases
│   ├── src/components/ui/      shadcn con el tema de RO (src/styles/ro-tema.css)
│   └── public/legacy/          copia automática del front de hoy (para el puente de pantallas)
├── apps/api          Nest 12. src/legado/: proxy + RUTAS_EN_NEST (la lista de lo que ya es de Nest).
├── packages/db       Prisma 7: 40 modelos + migración 0_base (CHECK, vista, disparadores). Sacado de la base real.
├── packages/permisos (fase 4) el motor de permisos en TypeScript. La matriz sigue en reglas_permisos.json.
├── packages/compat   lo que Python hace distinto de JS (round, json.dumps, huella del rastro, textos, orden, reloj), probado contra Python
├── tools/capturas    fotos de cada pantalla, vieja y nueva, y comparación píxel a píxel.
└── docker-compose.yml Postgres local en 127.0.0.1:5432 (y, con --profile completo, api + web).
```

### 2.1 El estrangulador, en una frase por capa

- **Datos:** la base pasa a Postgres en la fase 2 (`0_base` + copia de `local.db`), y la app de hoy pasa a usarla. Comprobado: lee y escribe igual que sobre SQLite.
- **API:** Nest atiende solo las rutas de `v2/apps/api/src/legado/rutas-en-nest.ts`. Lo demás va tal cual a `servir.py` (mismo método, ruta, cabeceras y cuerpo). Una ruta entra en la lista solo con su contrato de lectura **y** de escritura en verde.
- **Front:** Next no tiene aún página en «/», así que enseña el `index.html` de hoy tal cual (con su CSP, mapa de versiones y precarga). La carcasa en React se construye en `/carcasa` y se muda a «/» solo cuando sus fotos salen iguales. Cada pantalla, igual.
- **Segundo plano:** la tubería, los avisos, los envíos, la sincronía y el vigía se quedan en Python (el mismo `servir.py` de legado, una sola copia). Pasarlos a Nest es trabajo de después (§8).

### 2.2 Backend: módulos de Nest (orden de mudanza en la fase 5)

| Grupo | Rutas (idénticas a hoy) | Viene de |
|---|---|---|
| `identidad` (guarda global) | todas las de Nest | `servir.py › _quien`, `despliegue/acceso_cf.py` |
| `sesion` | `GET /api/sesion` | `servir.py` |
| `datos` | `GET /api/modulo/**` | `servir.py`, `despliegue/publicacion.py` |
| `clientes` | `GET /api/cliente/:id`, `GET /logos/:id` | `servir.py` |
| `buscar`, `indicadores` | `GET /api/buscar`, `/api/buscar/indice`, `/api/contadores`, `/api/indicadores` | `servir.py` |
| `perfil`, `preferencias` | `GET /api/perfil`, `GET/POST /api/preferencias`, `POST /api/perfil/zona` | `servir.py`, `altas_personas.py` |
| `rastro` | `GET/POST /api/rastro`, `GET /api/rastro/verificar` | `servir.py` (+ `registro_huellas`) |
| `decisiones`, `opiniones` | `/api/decisiones`, `/api/respuestas_mili`, `/api/opinion`, `/api/opiniones/*` | `servir.py` |
| `ajustes`, `ver-dato` | `/api/ajustes/*`, `POST /api/ver_dato` | `servir.py` |
| `acciones`, `avisos` | `/api/acciones`, `/api/avisos*`, `/api/canales/*` | `servir.py`, `avisos.py`, `avisos_programados.py` |
| Se quedan en el legado esta noche | `/api/recarga`, `/api/envios/*`, `/api/sincronia/*`, `/api/ia/*`, `/api/gbp/*`, `/api/modular/*`, `/api/vigia/*`, `/api/altas/*`, triaje | hablan con proveedores o tienen transacciones verificadas solo en SQLite |

Reglas del backend (para cada ruta que se muda):
- **Mismo contrato:** método, ruta, códigos, mensajes de error, claves JSON en `snake_case`, fechas en texto UTC, cabeceras que importan (`ETag`, `Cache-Control`; `X-RO-App` obligatoria en POST).
- **Identidad:** `RO_IDENTIDAD=local` (`X-RO-Yo` / `?yo=` / galleta `ro_yo`, solo en 127.0.0.1) o `access` (solo el sello firmado de Cloudflare Access). Solo entra quien está `activo`. Mientras una ruta va por el proxy, la identidad la sigue comprobando `servir.py`.
- **«Ver como»:** solo lectura, la intersección de las dos personas, y lo leído queda en el rastro.
- **Permisos en un solo sitio** (Tomás, 4-oct). Ya está montado en `v2/apps/api/src/permisos/` y probado:
  - cada ruta declara su permiso con una línea: `@Permiso({ modulo: 'crm' })`, o `@Publico('motivo')` si no tiene datos;
  - una guarda global deniega toda ruta sin declarar (403) y pregunta al motor;
  - **lo seguro va por defecto** (auditoría del hilo de feedback, parte 2):
    - toda respuesta sale recortada salvo `sinRecorte: '<motivo>'`;
    - todo método que no sea GET es escritura, y «ver como» no puede escribir salvo `lecturaPorPost: '<motivo>'`;
    - toda petición en «ver como» deja rastro desde la guarda, y si no se puede apuntar, 503;
    - `HEAD` y `OPTIONS` no pasan del proxy (405).
  - el motor es UNO (`@ro/permisos`, que lee `reglas_permisos.json`); hasta la fase 4, deniega todo;
  - `rutas-declaradas.spec.ts` rompe la compilación si una ruta no declara permiso o si alguien fuera de `src/permisos` decide mirando puestos.
  Así, cambiar quién ve qué es tocar la matriz o una línea, nunca buscar comprobaciones por el código.
- **Autoridad en el servidor y en cada lectura** (Astra): se revalida persona, puesto, cartera y ámbito en cada petición; nada se fía de ocultar en el navegador.
- **Desconocido no es cero** (Astra): ausencia de dato, error de fuente, cobertura parcial y cero medido son estados distintos y se conservan tal cual.
- **Rastro imborrable:** disparadores en la base (ya en `0_base`) y la cadena de huellas calculada igual, con un solo escritor a la vez (candado de transacción, como `BEGIN IMMEDIATE` hoy).

### 2.3 Base de datos

- `schema.prisma` **no se escribe a mano**: sale de crear en Postgres las tablas que usa hoy la app (incluidas las columnas que se añaden al arrancar con `ALTER TABLE`) y leerlas con `prisma db pull` (`v2/packages/db/scripts/rehacer_base.sh`).
- `0_base` incluye lo que Prisma no expresa: `CHECK`, la vista `v_cartera_hoy` y los disparadores del rastro y de «solo avanza el estado».
- Esta noche los tipos se quedan **como hoy** (texto para fechas, 0/1) porque la app de hoy escribe en las mismas tablas. Tipos de verdad: después (§8).

### 2.4 Frontend

- **Direcciones iguales que hoy** (`/#/mi-dia`). Pasar a rutas de verdad (`/mi-dia`) es para otro día: el front de hoy hace `fetch` relativos (`api/…`, `data/…`) que dependen de estar en «/».
- **Carcasa en React + shadcn** en `/carcasa` con **las mismas clases de `estilos.css`** (que se carga tal cual; Tailwind sin «preflight»; el tema de shadcn apunta a los tokens de RO). Se muda a «/» cuando `puerta.sh f6` sale verde con ella.
- **Puente de pantallas** (`<PantallaPuente fichero="mi_dia.js" />`): importa el módulo de hoy desde `/legacy/modulos/` y llama a `render(contenedor, ctx)`. Así la carcasa nueva lleva las 37 pantallas desde el primer día.
- **Pantallas en React:** una a una, de menos a más riesgo. Una pantalla sustituye al puente solo con sus fotos ≤ 0,5 % para todas las personas y tamaños, y el contrato y las baterías en verde.
- Sin Google Fonts. Claro siempre, nunca modo oscuro.

### 2.5 Fuentes: copia propia de todo lo que llega de las APIs, y nunca ceros (Tomás, 4-oct)

Regla: **lo que manda una API se guarda en nuestra base antes de usarlo. Si la API falla, se enseña lo último bueno con su hora y el aviso «Sin datos en tiempo real», nunca un 0 ni un vacío.**

Cómo está hoy (revisado el 4-oct, detalle en `PENDIENTES_LOGICA.md` N-01 a N-12):
- **Bien:** si un paso de la tubería falla entero, sus ficheros se restauran y se marca `dato_viejo`. Holded, GBP, Modular, Nuevos y Ventas ya sirven el último dato bueno. La ficha del cliente distingue «bien», «a cero» y «dato viejo».
- **Mal:** lo que llega de las APIs solo vive en ficheros sueltos, no en la base.
- **Mal:** cuando un lector se traga el error y escribe ceros, la tubería no lo ve. Pasa en SEO, Redes, CRM por subcuenta, Hostinger y Paneles.
- **Mal:** el aviso de dato viejo no llega a las pantallas.
- **Mal:** unos 200 `?? 0` en el front convierten «no sé» en «0».

Cómo queda (paso F5.10, fallos N-01 a N-12):
- **Tabla `fuente_lectura`** (se escribe solo, no se borra): fuente, recurso (cliente o cuenta), hora, ok, código, error, cuerpo (jsonb comprimido) y huella.
  - Vista `fuente_ultimo_bueno` con la última lectura buena de cada fuente y recurso.
  - Se guardan las 30 últimas lecturas buenas por recurso y 30 días de errores.
- **Un solo `fuentes/lectura.py › leer(fuente, recurso, funcion)`**, que generaliza el `con_cache` de Holded:
  - lectura buena → se guarda y se devuelve;
  - error, vacío sospechoso o todo a 0 donde antes no lo estaba → devuelve la última buena marcada `{"_viejo": true, "_desde": hora}`;
  - si nunca hubo dato → «sin dato», nunca 0.
  - Todos los lectores pasan por aquí.
- **Tubería:** cada paso declara sus claves mínimas y su recuento. Las cachés también se copian y se restauran. No se publica una versión si no se pudo bajar la anterior, ni una mucho más pequeña que la vigente.
- **Pantalla:**
  - un aviso común «Sin datos en tiempo real: lo último es de las HH:MM» en cada pantalla con alguna fuente vieja;
  - el sello del menú sale de la tubería;
  - «—» en vez de 0, y los totales dicen cuántos faltan.
  - En React (fase 6) está prohibido `?? 0` / `|| 0` sobre una cifra que se pinta.
- **Puerta:** las pruebas de solidez de `despliegue/pruebas_noche.py --solo-solidez`, más una por fuente en un fichero NUEVO (`despliegue/pruebas_solidez_N-<n>.py`; `pruebas_noche.py` juzga y no se toca) (API falsa caída → último dato bueno + aviso, ningún 0), dentro de `baterias.sh`. Además, `nunca_ceros.mjs` cuenta los `?? 0` del front, y ese número solo puede bajar.

En la nube, `ro-legado` (una sola copia) sigue siendo quien lee las APIs. La tabla vive en la misma Postgres, así que la copia de seguridad y la restauración de la fase 7 la cubren.

### 2.6 Rápida, a prueba de caídas y segura (Tomás, 4-oct)

Cada una con su puerta medible, en `puerta.sh` f3, f5, f6 y f7:

| Qué | Cómo se mide | Pasa si |
|---|---|---|
| **Rápida** | `migracion/rendimiento.py`: cada GET del contrato (3 personas × 5 veces) y el tiempo hasta que cada pantalla está pintada (`capturar.mjs` → `_tiempos.json`), en la de hoy y en la nueva | ninguna ruta o pantalla es más de un 25 % más lenta que hoy (con un margen de 100 ms en la API y 300 ms en pantalla), y nada pasa de 1,5 s (API) o 3 s (pantalla) si hoy no pasaba |
| **No se cae** | `migracion/caidas.sh`: ráfaga de 200 peticiones (20 a la vez); peticiones raras (ruta inexistente, JSON roto, 3 MB, Host ajeno, POST sin cabecera de la app); se cae el legado, se cae Nest, se reinicia Postgres | ningún 5xx ni cuelgue en la ráfaga; respuestas raras con 4xx limpio y sin la pila de errores; sin legado, 502 con mensaje en < 6 s y vuelta sola en < 60 s; lo mismo con Nest y con Postgres |
| **30 personas a la vez** | `migracion/rendimiento.py carga`: 30 personas abren la app a la vez (todas sus rutas, 6 en paralelo como el navegador, dos vueltas), primero en la de hoy y luego en la nueva, vigilando las conexiones a Postgres | ningún 5xx ni cuelgue; p95/p99 no peores que hoy (25 % y 100 ms de margen) si pasan de 1,5/3 s; menos de 60 conexiones a Postgres |
| **Segura** | `migracion/seguridad_http.py`: cabeceras (CSP, X-Frame-Options, etc.), 13 rutas a ficheros sensibles (`.py`, `.db`, `.env`, `.git`, `data/`, `../`), accesos sin identificarse | ninguna cabecera perdida ni debilitada, nada sensible servido, nada que hoy se deniega y la nueva deja ver. Además de lo que ya había: permisos en un solo sitio (§2.2), vectores al 100 % y `pruebas_seguridad.py` en las baterías |

**Planes B que ya están en la app nueva:**
- el proxy contesta 413 a un cuerpo de más de 200 KB y 504 si el legado tarda más de 60 s;
- Nest sigue vivo aunque se caiga el legado;
- `despliegue/base.py` reutiliza conexiones a Postgres y tira las rotas, así que un reinicio de Postgres no da errores;
- la guarda de permisos deniega lo no declarado;
- todo va compilado (`next build` + `next start`), como en la nube.

**Ensayado el 4-oct:**
- caídas en verde, con un fallo heredado (JSON roto → 500, N-13);
- seguridad en verde;
- 30 personas a la vez: la nueva daba **172 errores 500** de 2.340 peticiones (`envios.py` y `sincronia.py` crean sus tablas en cada petición y en Postgres eso choca). Arreglado en `base.py` (N-21): 0 errores en 3 pasadas, p95 igual que hoy (1,68 s frente a 1,66 s en este contenedor), p99 mejor (2,9 s frente a 4,2 s), 15–17 conexiones a Postgres. Una vez salieron 7 respuestas 504 justo tras reiniciar el legado; no se repitió.
- velocidad: el legado sobre Postgres era hasta 7 veces más lento que SQLite (17 → 130 ms en `/api/rastro/verificar`), porque abría una conexión por petición. Con la reutilización, 59 ms y puerta en verde.

### 2.7 Las conexiones con las APIs, a la nube sin repetir las altas (Tomás, 4-oct)

Hoy todas las llaves salen de un único sitio, `config.py › secreto()`, que las busca en este orden: carpeta privada → variable de entorno → `.env` → llavero del Mac. En la nube basta con dárselas como variables de entorno: **se copian las mismas llaves, con sus «refresh tokens», y no hay que repetir ninguna alta**.

- `python3 migracion/llaves_nube.py` dice qué llaves hay en el Mac, de dónde salen y si `render.yaml` las pide, **sin enseñar valores**. Hoy faltan 12 en el grupo `ro-llaves` (N-16).
- **Excepciones:**
  - GHL agencia: su llave rota en cada uso. Va a la base de la nube con `despliegue/llave_ghl.py sembrar`, una sola vez. Desde ese momento el Mac no vuelve a usarla, o deja de valer.
  - Meta: el token caduca el 1-dic. Hay que cambiarlo por el de usuario de sistema (ya lo dice `config.py`).
- **Esta noche Cursor no mueve ninguna llave** (línea roja). Deja `render.yaml` completo (N-16) y arregla los lectores que solo funcionan en un Mac (N-14 llavero, N-15 rutas a `~/Downloads`).
- **El día del despliegue (Tomás, unos 10 minutos):**
  1. `python3 migracion/llaves_nube.py --exportar` escribe `~/RO_MIGRACION/ro-llaves.env` (permiso 600, fuera del repositorio).
  2. En Render › Env Groups › `ro-llaves` › «Add from .env», se pega y después se borra el fichero.
  3. `DATABASE_URL=<la de Supabase> python3 despliegue/llave_ghl.py sembrar`
  4. `despliegue/salud_conexiones.py` en la nube: las 27 conexiones en verde.
- **Los lectores de verdad** (`~/RO_HERRAMIENTAS`: zh.py, hd.py, mt.py, gg.py…) no están en el repositorio. Los mete en la imagen `despliegue/preparar_contexto.sh`, como hasta ahora.

### 2.8 ClickUp en la app nueva

**No cambia nada:** los envíos a ClickUp siguen siendo de `sincronia.py`, dentro del legado.
- Cada botón guarda su acción y deja un cambio en la cola `sinc_cambios`, que no se puede borrar. La pantalla dice «Hecho en la app · pendiente de ClickUp».
- El envío lleva una marca `ro:<clave>`, así que nunca se duplica. Reintenta los fallos de red durante unas 5 horas, y si alguien tocó la tarea en ClickUp, pregunta qué versión vale.
- Escribe estados, comentarios, horas, asignados y mensajes de chat.

Hoy todo va **simulado**. Para encenderlo hacen falta tres cosas: el interruptor activado por Tomás, `RO_CLICKUP_REAL=si` y la llave de servicio `CLICKUP_TOKEN_SERVICIO`, que no puede ser la del propietario. Esta noche se queda apagado.

Antes de encenderlo en la nube hay que arreglar:
- N-17: el reconciliador lee SQLite en vez de Postgres;
- N-19: crear tarea no funciona en modo real;
- N-20: el interruptor vive en `data/`.

### 2.9 Escalados («sube a X persona»)

Hay tres mecanismos, y los tres publican **dentro de la app** (canal y campana; nada de correo, WhatsApp ni ClickUp):
1. **Alertas:** dueño → jefe del departamento → Mili → Tomás, como mucho 3 niveles. Solo escala si pasa el plazo; lo marcado «Lo tengo» o pospuesto no escala. Se ve en Mi día («Escaladas a ti») y en la campana.
2. **Avisos automáticos** (`avisos_programados.py`): si un aviso sigue sin hacerse pasadas sus horas, sube a la jefa, a Mili o a Tomás.
3. **Vigía de conexiones:** si cae una conexión, avisa a Agus; si sigue en rojo más de 60 minutos, a Mili y Tomás.

Los cerebros por área (PR #2) aún no escalan nada: su consejo «escalar» es una nota para la IA. Cuando se conecten, irán por el mismo `avisos.publicar`.

Para que funcionen de verdad en la nube:
- **Los bucles tienen que correr.** Esta noche se apagan a propósito con `RO_AVISOS_SIN_BUCLE=1`, para que no salga nada fuera.
  - En `v2/render.yaml` esa variable **no puede aparecer**: lo comprueba la puerta 7.
  - El legado va en **una sola copia**: con dos, los bucles irían dobles; las claves únicas evitan mensajes repetidos, pero no trabajo doble.
  - El vigía tiene que correr en la nube (N-18).
- **Puerta (F5.11):** un ensayo de escalados sobre Postgres. Usa la copia `ro_esc`, un legado aparte con los bucles encendidos y las salidas apagadas, y el reloj adelantado. Se crea una alerta y un aviso automático vencidos, y comprueba que el mensaje «sube a X» llega al canal y a la campana de la persona correcta, una sola vez. Además entran en `baterias.sh` las pruebas que ya existen: `pruebas_seguridad.py` (`alertas_a8`, `avisos_automaticos`, `sincronia_clickup`) y `fuentes_alertas/probar_alertas.py`.

### 2.10 Copia de seguridad cada hora, 7 días (Tomás, 4-oct)

- **Qué:** `python3 despliegue/copia_base.py --hora`. Vuelca la Postgres entera (`pg_dump`), **la abre entera** y cuenta las filas de cada tabla contra la base viva (una copia que no se ha leído no cuenta), deja `manifiesto.json` (tamaño, huella sha256, filas por tabla) y la sube a Cloudflare R2 (otro proveedor: si cae Render, la copia sigue).
- **Cuánto se guarda:** 7 días de copias de cada hora (168). Las más viejas se borran solas, en disco y en R2; la última nunca. **Se cambia con `RO_COPIAS_DIAS`** en `render.yaml` (por ejemplo 14 o 30); el coste en R2 es pequeño (la base de prueba ocupa 0,4 MB por copia).
- **Copia inmutable diaria (4-oct, juntado con el hilo de buenas prácticas):** R2 cada hora durante 7 días para recuperar rápido (bloqueo de 7 días), **y** a las 3 y a las 15 UTC la misma copia a **Backblaze B2** en una cuenta aparte, con Object Lock «compliance» de 30 días. R2 protege de un error o de alguien con la llave de la app; B2, de alguien que se haga con Cloudflare o con todas nuestras llaves. Sustituye a la copia semanal en un disco desenchufado (si se quiere, una al mes sigue siendo buena idea). Sin `RO_B2_*` no sube y, en producción, la copia de esas horas sale en rojo.
- **Dónde corre:** cron `ro-copias` cada hora en `despliegue/render.yaml` (y en `v2/render.yaml`, F7.2). Sin las llaves de R2 sale **en rojo**: en Render el disco de un cron se borra al terminar y la copia no sobreviviría. Las llaves de R2 (`RO_R2_*`) las crea Tomás en Cloudflare; hoy no existen.
- **Restaurar:** `pg_restore --no-owner -d <base nueva> postgres.dump` de la hora que se quiera. Lo ensaya entero la puerta 7 (volcar, restaurar en otra base, misma API) y `copia_base.py --probar` el día 1 de cada mes.
- **Además:** la base va en **Supabase** (Tomás, 4-oct). Sus copias diarias son un plan B; la vuelta a un minuto concreto (PITR) es un complemento de pago, y restaura en el mismo proyecto. Las nuestras (R2 cada hora, B2 inmutable) restauran en cualquier Postgres: por eso el volcado lleva solo el esquema `public` y sin permisos. El cliente `pg_dump` de la imagen es el 17 (vuelca 15, 16 y 17). **Antes del piloto, ensayo de restauración desde R2 en una base nueva.** La app de hoy en SQLite sigue con su copia diaria verificada (`copia_seguridad.py`).
- **Antes de cada despliegue que cambie la base**, una copia a mano (botón «Trigger Run» del cron `ro-copias` en Render) y después `prisma migrate deploy` como paso que **bloquea el despliegue** si falla (`preDeployCommand` de `ro-api`).
- **Ensayado el 4-oct** sobre la Postgres de prueba: 41 tablas y 4.742 filas, iguales que la base viva; borra las de más de 7 días y no toca lo que no es una copia. Arreglado de paso: la imagen instalaba `pg_dump` 15, que no puede volcar una Postgres 16 (N-22). La imagen no la he podido construir aquí.

### 2.11 Lo que se copia de herramientas hechas con este mismo stack (4-oct)

Referencias revisadas: Twenty (CRM de código abierto, Nest + Postgres; clonado y leído el 4-oct), Teable, cal.com, Ghostfolio, Hoppscotch y Documenso (estudio del hilo «Repos de referencia del stack»). El zip del otro CRM que tiene Tomás va a `~/RO_MIGRACION/referencias/` (fuera del repo); Cursor lo puede leer para inspirarse, nunca copiar código tal cual.

**Ya en la rama (4-oct, con pruebas):**
- Lo imborrable tampoco se vacía de golpe: los disparadores de fila no paran un `TRUNCATE`; ahora cada tabla con «sin_delete» lleva su `BEFORE TRUNCATE` (migración `1_sin_truncate` y `base.py`). Probado: `TRUNCATE registro` → «El rastro no se borra».
- El mismo tope de cuerpo en todas partes: 200 KB en `servir.py`, el proxy y las rutas de Nest (antes Nest aceptaba 2 MB).
- `/api` con `Cache-Control: no-store` también en las rutas de Nest.
- Filtro global de errores con la forma de `servir.py` (`{"error": …}`): Prisma P2002 → 409, P2025 → 404, P2003 → 400; JSON roto → 400 y cuerpo grande → 413 (N-13 en las rutas de Nest); nunca la pila ni el SQL; solo los 5xx van al registro como error.
- El entorno se comprueba al arrancar (`src/entorno.ts`): sin base o sin identidad no arranca; en producción, ni `RO_IDENTIDAD=local` (cualquiera podría hacerse pasar por otro) ni `RO_RELOJ` (el reloj fijo de la noche).
- Cierre ordenado al parar (`enableShutdownHooks`), tope de conexiones de la API a Postgres (`RO_PG_POOL_MAX`, 10) y la imagen de la API sin root (`USER node`).
- **Cuenta de conexiones a Postgres en la nube:** API ≤ 10 + legado (medido: 15-17 en el pico de 30 personas, Nest incluido) + tubería (crons ligera, completa y noche, uno a la vez por el bloqueo) + copias (1). Tiene que quedar por debajo del 70 % del tamaño del pool de sesión de Supabase (Database › Connection pooling; DESPLIEGUE T1b pide ≥ 40) y de su `max_connections` (mirarlo en el panel antes del piloto: no lo he podido comprobar). La puerta de carga falla si se pasa de 60.
- La lista de rutas con su permiso guardada en el repositorio (`src/permisos/rutas-permisos.txt`, idea de Twenty): una ruta nueva o un permiso cambiado se ve en el diff.

**En la fase 5 (reglas de cada ruta nueva):**
- **El permiso también dentro de la consulta** (Documenso, Twenty): el servicio filtra por la cartera de la vista en el `WHERE`; si el recurso no es de la persona, 404 (como si no existiera), nunca leerlo y luego mirar. Defensa contra quien cambia el id en la URL.
- El servicio recibe siempre la vista (quién pregunta) como argumento obligatorio: sin ella no hay consulta ni rastro.
- La escritura y su anotación en el rastro, en la misma transacción.
- Cambios de base solo hacia delante y en dos pasos (columna opcional → rellenar → obligatoria); una migración aplicada no se edita nunca.

**Después del piloto:** que la app no sea dueña de las tablas (un usuario de base sin `TRUNCATE`, `UPDATE` ni `DELETE` sobre el rastro; en Supabase, un papel propio en vez de `postgres`), colas de trabajos en Postgres (pg-boss) con reintentos e idempotencia, logs estructurados con id de petición (nestjs-pino), contrato zod compartido front/back, `/listo` que compruebe base y cadena del rastro, dinero en `Decimal`, fechas `timestamptz`, permisos por campo en la capa de datos.

**No encaja (para 30 personas):** un esquema de base por cliente, GraphQL, Redis para caché o permisos, réplicas de lectura, tokens en `localStorage`, CORS abierto.

### 2.12 Seguridad en la nube: secuestro de datos, accesos y ataques (Tomás, 4-oct)

| Riesgo | Qué lo para | Ya está | Lo activa Tomás | Cómo se comprueba |
|---|---|---|---|---|
| **Secuestro de datos (ransomware)**: alguien entra y cifra o borra la base | Copias cada hora fuera de Render, en R2 (otro proveedor). La app **solo sube**: no lista ni borra. El **bloqueo del bucket** (Bucket Lock de R2) impide borrar o sobrescribir una copia durante 7 días, aunque roben la llave. Las reglas de borrado del bucket quitan lo viejo, no la app | `copia_base.py --hora` (§2.10), sin borrar en R2 | Bucket `ro-copias` en UE con: bloqueo de 7 días en `copias/`, regla de borrado a 7 días en `copias/horas/` y a 30 en el resto, y una llave solo para ese bucket | Con la llave de la app, intentar borrar una copia → tiene que fallar. Y el ensayo de restauración (puerta 7 y `--probar` cada mes) |
| Que el atacante (o un agente con llaves) tenga también la cuenta de Cloudflare | **Copia inmutable en otra casa:** dos veces al día la copia sube también a **Backblaze B2** (UE), en una cuenta aparte con otro correo y su propio segundo factor, con **Object Lock «compliance» de 30 días**: nadie, ni el dueño, la borra antes. La llave de la app es «solo escribir» | `copia_base.py --hora` (3 y 15 UTC, `RO_B2_*`); en producción sale en rojo si a esa hora no sube | T3b de `DESPLIEGUE.md` | Con la llave de la app, borrar o leer una copia de B2 → tiene que fallar. Restaurar una de B2 en el Mac una vez al mes |
| **Entrar sin ser del equipo** | Cloudflare Access delante de todo. La app solo cree el sello firmado de Access (firma, `aud`, caducidad), nunca una cabecera; en producción no arranca en modo «local» ni con el reloj fijo | `acceso_cf.py`, `src/entorno.ts`, F5.1 | — | `python3 despliegue/seguridad_nube.py --dominio … --render …` tras cada despliegue: sin sesión o con cabeceras falsas, ninguna ruta da datos |
| **Contraseña robada de un empleado** | **Segundo factor obligatorio**, impuesto por Google (Google Authenticator o la app de Google), no por la app. Access solo deja entrar con Google: sin el «One-time PIN» de Cloudflare, que con un código al correo se saltaría el segundo factor | — | Google Workspace › verificación en dos pasos **obligatoria** para todos. En Access: método de entrada solo Google, **quitar One-time PIN** | Entrar con una cuenta de prueba sin segundo factor → Google no deja pasar. En la pantalla de Access no aparece «enviar código» |
| Un empleado que se va | Quitarlo del grupo de Access (y de Google): pierde el acceso al momento | Solo Tomás da y quita accesos (D2) | Al dar de baja a alguien | Probar su correo → no entra |
| **Ataques de denegación (DDoS)** y bots | Cloudflare en modo «proxied» absorbe el tráfico; Access corta en el borde a quien no ha entrado, antes de llegar a Render | — | En Cloudflare: Bot Fight Mode, reglas gestionadas del WAF (gratis), «Under Attack Mode» solo en emergencia, y una regla de límite de peticiones en `/api/` **por persona o muy alta por IP** (las 30 personas salen por la misma IP de la oficina: un límite bajo os bloquearía a vosotros) | `seguridad_nube.py` ve `cf-ray`. La carga de 30 personas (§2.6) da la cifra para el límite |
| Saltarse Cloudflare por la dirección de Render | Desactivar las direcciones `*.onrender.com` (T8). `ro-api` y `ro-legado` como **servicios privados** (sin dirección pública): solo `ro-web` da la cara | Plan F7.2 | T8 en cada servicio público | `seguridad_nube.py --render …` |
| **La base, abierta por internet** (Supabase) | Data API de Supabase **desactivada** (si no, las tablas de `public` se leen con la llave anónima); SSL obligatorio y verificado (`RO_PG_CA`); restricciones de red: solo las IP de salida de Render; solo el pooler de sesión | `entorno.ts` no arranca con el pooler 6543 ni sin certificado en producción | T1b de `DESPLIEGUE.md` | Desde una IP que no es de Render, conectar a la base → rechazado. `curl https://<proyecto>.supabase.co/rest/v1/registro` → sin datos |
| Algo parecido a Wordfence | El WAF de Cloudflare hace ese papel (reglas contra ataques conocidos, bots, límites). Dentro de la app: permisos en un solo sitio, errores sin detalles, cuerpo máximo de 200 KB, cabeceras de seguridad, escáner de secretos | Sí (dentro de la app) | WAF, como arriba | `seguridad_http.py` en cada puerta |
| Llaves robadas del repositorio | Nunca llaves en el repo (escáner de secretos); en Render, variables `sync: false` | Sí | — | `escaner_secretos.py --proyecto` |

No lo he podido probar en la nube de verdad: la cuenta de Render, el dominio y las llaves de R2 aún no existen. Los nombres de los ajustes de Cloudflare y R2 son los de su panel a fecha de hoy; si alguno ha cambiado, el sitio es el mismo.

### 2.13 Un agente solo toda la noche: lo que no puede tocar (4-oct)

Cursor trabaja 8 horas con tu usuario del Mac y aprobando sus propias órdenes (`--force`). Eso le da, sin querer, acceso a tus llaves y a las pruebas que le juzgan. Lo que lo impide:

| Riesgo | Qué lo para | Dónde |
|---|---|---|
| Lee llaves reales del llavero y llama a un proveedor de verdad | `RO_SIN_LLAVES=1` (config.secreto() no devuelve nada) y una orden `security` falsa delante en el PATH que niega leer contraseñas | `noche.sh` |
| «Arregla» una prueba para pasarla | Huellas sha256 de los ficheros que juzgan, guardadas al lanzar fuera del repo y de solo lectura; regla expresa en el prompt; y por la mañana `comprobar_manana.sh` las compara, vuelve a la versión de antes si alguna cambió, reinicia todo y repite las puertas completas desde cero | `noche.sh`, `PROMPT_NOCHE.md`, `comprobar_manana.sh` |
| Reescribe la referencia (contrato, fotos, base de partida) para que coincida | Solo lectura tras la puerta 1 (F1.7) | `PROMPTS_CURSOR.md` |
| Datos de SQLite que Postgres no traga (byte NUL, texto no UTF-8, tipos mezclados) | `validar_sqlite.py` antes de copiar (F2.3) | `PROMPTS_CURSOR.md` |
| Borra o empuja donde no debe | Solo `git push origin migracion/v2`; protección de `main` en GitHub | Tomás (abajo) |

La orden `security` falsa es una barrera de PATH: quien llame a `/usr/bin/security` con la ruta entera la salta. La barrera de verdad es que el llavero esté bloqueado o que Cursor corra con otro usuario. Por eso lo de abajo.

**Antes de lanzar (Tomás, 10 minutos):**
1. GitHub › ro-app › Settings › Branches: regla de protección en `main` (sin push directo, sin force-push, sin borrar).
2. Una copia de Time Machine del Mac justo antes de lanzar.
3. Cursor › Settings › Agents › Auto-Run: «File-Deletion Protection» y «Dotfile Protection» activadas. En el ensayo de 1 hora (`bash migracion/ensayo.sh`, en una copia de la app), prueba `migracion/cursor_cli_permisos.json` como `.cursor/cli.json` (sin probar aquí: si `cursor-agent` se queja, se quita).
4. Opcional, lo más seguro: lanzar la noche desde otro usuario de macOS sin tus llaves (con su propio `cursor-agent login`), o bloquear el llavero antes de irte (Acceso a Llaveros › Archivo › Bloquear llavero «inicio de sesión»).
5. Por la mañana, antes de creerte PROGRESO.md: `bash ~/RO_MIGRACION/comprobar_manana.sh` (la copia de fuera: la del repo la podría haber tocado el agente).

**Next en modo autónomo:** `next.config.ts` usa `output: "standalone"`, así que se sirve con `node .next/standalone/apps/web/server.js` (con `public` y `.next/static` copiados al lado), no con `next start`. Lo hace `servicios.sh` y lo hace la imagen de Docker: lo que pasa las puertas es lo mismo que irá a la nube.

### 2.14 El servidor MCP de la app: cada uno desde su Claude, con su alcance (Tomás, 4-oct)

Decisión de Tomás: no habrá una API pública. La app tendrá **su propio servidor MCP** y cada miembro del equipo lo conecta
desde **su** Claude (su propia cuenta paga la IA). Cada token solo puede hacer lo que la persona puede hacer en la app, y
dentro de eso, solo lo que ese token tenga permitido. **No se construye esta noche**: necesita las rutas ya en Nest (F5).

| Pieza | Cómo |
|---|---|
| Dónde | Módulo `mcp` de Nest con el SDK oficial (`@modelcontextprotocol/sdk`, transporte HTTP «streamable»), en `https://mcp.rankingonline.app/mcp`. Otro nombre que la app: Claude lo llama desde sus servidores, así que no puede ir detrás del inicio de sesión de Access |
| Cómo se entra | OAuth 2.1 con PKCE y registro dinámico de clientes, que es lo que pide un conector personalizado de Claude. La pantalla de autorizar vive en `app.rankingonline.app/mcp/autorizar`, **detrás de Access** (Google + segundo factor): solo quien ya entra en la app puede crear un token. Sin comprobar: si Access de Cloudflare puede hacer él de servidor OAuth para MCP, sobra la pantalla propia |
| El token | Aleatorio, guardado solo su huella (tabla `mcp_token`: persona, nombre, alcances, creado, caduca a los 30 días, último uso, revocado y por quién). Se renueva rotando. «Mis conexiones» en Mi perfil para verlos y revocarlos; Tomás revoca los de cualquiera; al dar de baja a una persona se revocan todos solos |
| El alcance | Cada token lleva una lista de herramientas elegida al autorizar, y nunca más de lo que la persona ve. En **cada** llamada se vuelve a mirar con el motor de permisos de siempre (`@ro/permisos`): si a alguien le cambian el puesto, su token lo nota al momento. «Ver como», nunca. Por defecto, solo lectura |
| Las herramientas | Las mismas funciones de la app, no la API entera: buscar cliente, ficha, Mi día, En rojo, riesgo de baja, «Qué hago si…», contexto del cliente, agenda… Cada una llama al MISMO servicio de Nest que su pantalla (permiso en el `WHERE`, recorte de importes). Ninguna herramienta de SQL ni «llamar a cualquier ruta» |
| Alimentar la app | Las de escritura (por ejemplo, dejar una nota de reunión en un cliente o marcar una acción) solo si el token tiene ese alcance y la persona puede hacerlo en la app; pasan por la misma guarda y dejan su línea en el rastro |
| Auditoría | Cada llamada deja una línea en el rastro (`coleccion = 'mcp'`, la herramienta, el token y la persona). Límite por token (por ejemplo 60 llamadas por minuto y un tope diario) y regla de Cloudflare para `mcp.` |
| Lo que vuelve | Datos, nunca instrucciones: los textos de clientes van marcados como datos; sin llaves, sin correos de personas que esa persona no vería |

Pruebas que lo cierran: un token de un account no ve un cliente ajeno por ninguna herramienta; un token de solo lectura no
escribe; cambiar el puesto de la persona cambia lo que ve su token en la siguiente llamada; un token revocado o caducado da
401; cada llamada está en el rastro.

---

## 3. Las redes de seguridad (hechas y ensayadas el 4-oct)

| Herramienta | Qué demuestra |
|---|---|
| `migracion/puerta.sh f1…f7` | junta todo lo de abajo en una orden por fase y dice VERDE o ROJO |
| `migracion/servicios.sh` | arranca siempre igual la app de hoy (8770), el legado sobre Postgres (8771), Nest (4000) y Next (3000), todo en 127.0.0.1 y con las salidas externas apagadas |
| `migracion/inventario.py --comparar` | que no se olvida ninguna pantalla, ruta, tabla, columna, regla o componente, y qué ha cambiado hoy |
| `migracion/contrato.py` | que cada GET responde **lo mismo** a cada persona (y a Tomás «viendo como» cada una), incluidos los 403 |
| `migracion/contrato_escritura.py` | que cada POST responde lo mismo **y deja la base igual**, partiendo de la misma copia |
| `migracion/vectores_permisos.py` | que el motor de permisos en TypeScript da las mismas respuestas que `permisos.py` |
| `v2/tools/capturas` | que cada pantalla **se ve igual** (≤ 0,5 % de píxeles) y no tiene errores de página nuevos |
| `migracion/baterias.sh` (la monta Cursor en la fase 1) | que las baterías de hoy y las focalizadas de Astra siguen verdes contra la app nueva |
| `migracion/rendimiento.py`, `migracion/caidas.sh`, `migracion/seguridad_http.py` | velocidad, caídas y seguridad (§2.6) |
| `migracion/validar_sqlite.py` | que los datos de SQLite caben en Postgres antes de copiarlos |
| `migracion/comprobar_manana.sh` | por la mañana: que nadie tocó las puertas esta noche, y todas otra vez desde cero |
| restauración (en `puerta.sh f7`) | que una copia de la base se restaura y responde igual (lo pide Astra antes de cualquier piloto) |

**Ensayo del 4-oct** (en la nube de Claude, con datos inventados):
- La app de hoy sobre Postgres frente a SQLite: **595/595** lecturas iguales y escrituras iguales (`puerta.sh f2` en VERDE), después de arreglar 8 fallos de Postgres que habrían roto el despliegue en Render (§7).
- La app nueva entera (Next → Nest → legado): **595/595** lecturas iguales.
- Grabar dos veces la misma app: 0 diferencias y 0,00 % de píxeles. Lo que marquen las puertas esta noche es real.

---

## 4. La noche, paso a paso

Cursor trabaja con **un solo prompt** (`migracion/PROMPT_NOCHE.md`) y un cuaderno de bitácora (`migracion/PROGRESO.md`). En cada vuelta lee el cuaderno, hace el siguiente paso pendiente, pasa su puerta, hace commit, apunta y sigue con el siguiente. `migracion/noche.sh` lo vuelve a lanzar si se le acaba el contexto o se cae, hasta que el cuaderno diga `ESTADO: TERMINADO` o se acabe el tiempo. Los pasos y sus planes B están en `PROGRESO.md`; aquí, el porqué.

| Fase | Qué | Tiempo orientativo | Puerta |
|---|---|---|---|
| **0 · tarde (Tomás)** | traer el plan al Mac, `preparar_noche.sh --instalar` hasta LISTO, `planear.sh` (Fable escribe y audita `PLAN_NOCHE.md`), `ensayo.sh` (1 hora en una copia), lanzar `noche.sh` | varias horas | LISTO y «PLAN: AUDITADO» |
| **1 · referencia** | inventario del Mac, escáner, instantánea del código + los PR #2, #3 y #4 (`RAMAS_A_JUNTAR.txt`), copia de la base y de la app de hoy (`~/RO_MIGRACION/ref`), servicios, grabar contrato, vectores, fotos, casos de escritura, `baterias.sh` | 60 min | `puerta.sh f1` |
| **2 · base** | arreglo `avisos`→`tuberia_avisos`, `rehacer_base.sh` si cambiaron tablas, Postgres, copia, publicar `data`, la app de hoy sobre Postgres; arreglar `base.py` hasta que lea y escriba igual | 60–90 min | `puerta.sh f2` |
| **3 · app nueva entera** | Nest y Next con proxy a la app de hoy. Debería salir verde a la primera: ya está ensayado | 20 min | `puerta.sh f3` |
| **4 · permisos** | `permisos.py` → `@ro/permisos`, función a función | 60–90 min | `puerta.sh f4` (100 %) |
| **4.2 · pruebas de permisos** | las que impiden volver atrás (anexo de `PENDIENTES_LOGICA.md`, punto 8), como e2e que lanzan todas las puertas siguientes | 30–45 min | e2e en `puerta.sh` f3/f5/f6/f7 |
| **5 · API a Nest** | grupos de §2.2, uno a uno, empezando por identidad + rastro de «ver como» (sin ellos, ninguna ruta de Nest puede pasar): se escribe el módulo, se añaden sus rutas a `RUTAS_EN_NEST`, puerta; si no sale en 3 intentos, se quitan de la lista | hasta 4 h antes del final | `puerta.sh f5` por grupo |
| **5.10 · fallos pendientes** | los 71 de `PENDIENTES_LOGICA.md` (L-01…L-49 del hilo de feedback y N-01…N-22 de la migración), L-01 y L-21 primero y luego de seguridad a presentación, con su prueba | hasta 3 h antes del final (los de seguridad van primero) | la prueba de cada fallo + `puerta.sh f5 --rapido`; la completa por bloque |
| **5.11 · escalados** | ensayo de escalados sobre Postgres | hasta 2 h antes del final | `escalados.py` |
| **6 · front en React** | carcasa en `/carcasa` (y en «/» con `RO_CARCASA=1`), `ctx.ts`, puente; carcasa por defecto con fotos iguales; pantallas una a una | hasta 1 h antes del final | `puerta.sh f6` por pieza |
| **7 · cierre** | contenedores (`docker compose --profile completo`), `v2/render.yaml`, ensayo de restauración, `INFORME_NOCHE.md`, `git push` de la rama `migracion/v2` | la última hora, pase lo que pase | `puerta.sh f7` |

**Reloj:** `noche.sh` exporta `RO_FIN_NOCHE`. Si faltan menos de 60 minutos, Cursor deja lo que esté haciendo (con su puerta verde, o deshecho) y pasa a la fase 7. Lo que no dé tiempo sigue otro día con el mismo sistema.

### La mañana del 5 (Tomás)

Leer `migracion/INFORME_NOCHE.md` y revisar la rama `migracion/v2`. Como dice Astra, **la noche no promete un despliegue**: un piloto necesita permisos verificados con datos reales (fases 2–4), la restauración ensayada (fase 7), las fuentes necesarias disponibles y las funciones críticas probadas. El informe dice cuáles de esas condiciones se cumplen, con el enlace a cada puerta. Hasta el «sí» de Tomás, la app de hoy sigue siendo la buena.

---

## 5. Si algo se tuerce: reintento y plan B (nunca «paro»)

Regla general: **tres intentos con enfoques distintos** (cada uno apuntado en `PROGRESO.md` con la hipótesis y el resultado). Si el tercero falla, el plan B del paso y seguir.

| Si… | Plan B |
|---|---|
| Una diferencia en la puerta 2 (la app de hoy sobre Postgres) no se arregla en `base.py` | Se apunta la ruta en `~/RO_MIGRACION/excepciones.txt` con el motivo («función bloqueada en Postgres») y se sigue. Va al informe como **bloqueo para el piloto**, no como migrada. Ejemplo ya conocido: el triaje responde 503 en Postgres a propósito (Astra). |
| La puerta 3 no sale verde | Es fontanería (cabeceras, Host, compresión): arreglar en `src/legado/proxy.ts` o `next.config.ts`. Si tras 3 intentos sigue, apuntar y seguir con la fase 4 (que no depende de la 3). |
| El motor de permisos no llega al 100 % en 90 minutos | Se guarda lo hecho, se apunta qué vectores fallan y **no se muda a Nest ninguna ruta que dependa de permisos** (casi todas): se saltan los grupos de rutas (F5.1–F5.9). Los fallos de F5.10 se arreglan igual, en el legado, y F5.11 se hace. La app sigue entera por el proxy. |
| Un grupo de rutas no pasa su puerta | Se quitan de `RUTAS_EN_NEST` (vuelven al proxy), se deja el código del módulo en una rama `intento/<grupo>` y se sigue con el siguiente grupo. |
| La carcasa o una pantalla en React no queda igual | Se queda la de hoy. Una pantalla a medias nunca sustituye a la vieja. |
| La velocidad, las caídas o la seguridad salen en rojo por algo que ya pasa en la app de hoy | Se arregla si es de la parte nueva (proxy, Nest, Next, `base.py`). Si es heredado, va a `PENDIENTES_LOGICA.md`, y mientras tanto su línea va a `~/RO_MIGRACION/excepciones_solidez.txt` (caídas) o `excepciones_rendimiento.txt` (velocidad) con su L-n. Así no bloquea la noche y queda en el informe. |
| Un fallo de `PENDIENTES_LOGICA.md` no sale en 3 intentos | Se deja como estaba, con la prueba que lo demuestra marcada como pendiente (no borrada), y va al informe. Si es de **seguridad**, es **bloqueo para el piloto**. |
| Algo de Cursor se cuelga (servidor que no responde, orden que no vuelve) | `bash migracion/servicios.sh parar todo && bash migracion/servicios.sh arrancar` y repetir el paso. |
| Se rompe algo de la app de hoy | `git restore` de lo tocado; la base real nunca se toca (todo va sobre copias en `~/RO_MIGRACION/`). |
| Hace falta una decisión de Tomás | La opción más conservadora (la que no cambia nada visible y se deshace fácil), apuntada en «Preguntas para Tomás» de `NOTAS_NOCHE.md`. |
| No da tiempo a todo | Normal. Lo que no pasó su puerta sigue por el proxy o el puente: la app está entera igual. |

Líneas rojas que **ni el plan B cruza**: tocar `local.db` o `data/` reales, encender envíos o ClickUp real, `git push` a `main` o con `--force`, credenciales en ficheros, servidores fuera de 127.0.0.1, borrar pruebas o relajarlas para que pasen.

---

## 6. Con qué modelo y cómo lanzarlo

**Fable planea y audita; Grok Fast construye (Tomás, 4-oct 10:09).** Tres piezas:

1. **`bash migracion/planear.sh`, por la tarde** (en cuanto Astra deje de tocar el código). Fable 5.1 escribe `migracion/PLAN_NOCHE.md`: el plan COMPLETO de la noche, paso a paso y con detalle extremo (órdenes exactas, qué tiene que salir, qué hacer si sale otra cosa, intentos 2 y 3, plan B, y una sección por cada fallo abierto de F5.10). Lo escribe en varias vueltas (`migracion/PROMPT_PLAN.md`) hasta que `revisar_plan.py` confirma que cubre los 33 pasos y los fallos abiertos. Después lo **audita** (`migracion/PROMPT_AUDITA.md`) con cuatro enfoques, uno por vuelta: A ¿existe lo que nombra?, B ¿encaja la noche de principio a fin?, C ¿lo puede hacer un modelo rápido sin equivocarse?, D ¿respeta las líneas rojas? Cada auditor corrige en el propio plan y apunta qué cambió. Sigue auditando hasta que una sale «SIN CAMBIOS» (mínimo 4, máximo 8: `RO_AUDITORIAS_MIN`, `RO_AUDITORIAS`). El planificador solo puede tocar el plan: si cambia otro fichero, `planear.sh` para. Se puede cortar (Ctrl+C corta también la vuelta en curso) y relanzar: sigue donde lo dejó. Si `noche.sh` tiene que planear porque el plan no estaba hecho, le da como mucho 3 horas (`RO_HORAS_PLAN`) y empieza con lo que haya. Si el código cambia después (Astra, `juntar_plan.sh`), la siguiente vez hace solo una auditoría de puesta al día sobre lo que cambió.
2. **`bash migracion/noche.sh`.** Junta el plan con el código del Mac, comprueba que el plan está auditado y al día (si no, llama a `planear.sh`; las 8 horas cuentan desde que el plan está listo), guarda huellas y copia de los jueces, y lanza al ejecutor vuelta tras vuelta. **El ejecutor es Grok Fast** (`RO_MODELO`, por defecto `grok-code-fast-1`): cada vuelta lee la sección de su paso (`revisar_plan.py --seccion F2.3`) y la sigue al pie de la letra. Si el ejecutor cambia `PLAN_NOCHE.md`, `noche.sh` lo devuelve al auditado.
3. **Fable de guardia durante la noche** (`migracion/PROMPT_REPLAN.md`): cuando un paso falla una vez, cuando el ejecutor marca su plan como gastado o cuando dos vueltas no avanzan, Fable diagnostica y escribe `migracion/PLAN_VUELTA.md` para ese paso. Si Fable no responde dos veces, la noche sigue sin él y se le vuelve a probar a la media hora.

**El riesgo de un modelo rápido, dicho claro.** Un modelo rápido sigue bien un plan detallado y se equivoca más cuando tiene que decidir. Las decisiones están en el plan y las puertas no dejan pasar nada que no cuadre, así que el riesgo principal es perder tiempo (más intentos, más planes B). Las puertas paran casi todo lo demás, pero no todo: solo comprueban lo que se grabó y los vectores que hay. Donde un detalle mal hecho abre un agujero (motor de permisos, identidad y rastro, fallos de seguridad), va un modelo más fuerte solo en esos pasos: `RO_PASOS_FUERTES="F4.1 F4.2 F5.1 F5.10"` con `RO_MODELO_FUERTE` (por defecto `claude-sonnet-5-5`). Tomás decidió el 4-oct que esos 4 pasos vayan con Sonnet: es el valor por defecto. `RO_PASOS_FUERTES=""` lo deja todo con Grok Fast.

**Nombres de los modelos.** Son los que muestra tu Cursor: `bash migracion/preparar_noche.sh --probar-cursor` prueba los tres y, si uno no responde, lista los que tu Cursor conoce. Cada vuelta tiene tope de tiempo (90 min la del ejecutor, 30 la de guardia, 60 la del planificador): una vuelta colgada se corta y se sigue. Para vigilar el gasto: Cursor › Settings › Usage, al acabar el ensayo de 1 hora.

**El ensayo de 1 hora: `bash migracion/ensayo.sh`.** Copia la app a `~/RO_ENSAYO/app` (en el disco del Mac es un clon instantáneo), sin push, y lanza ahí una hora de noche con el plan que haya. Mientras dura, `~/RO_MIGRACION` apunta a la carpeta del ensayo (los pasos la nombran tal cual) y el Postgres de verdad se para; al acabar, todo vuelve solo. Por eso **no puede ir a la vez que `planear.sh` o `noche.sh`** (se niegan a arrancar). Si se corta a lo bruto: `bash migracion/ensayo.sh --cerrar`. Para ver la comprobación de la mañana sobre el ensayo: `--comprobar`. Al acabar: `--borrar`.

**Cómo se lanza (dos maneras, la primera es la buena para 8 horas sin nadie):**

1. **`bash migracion/noche.sh`** (usa la orden de terminal de Cursor, `cursor-agent`). Mantiene el Mac despierto (`caffeinate`), vuelve a lanzar a Cursor cada vez que termina una vuelta, y para solo al acabar o al llegar la hora. Registros en `~/RO_MIGRACION/logs/`. `preparar_noche.sh` comprueba que la orden existe y acepta las opciones; si no, dice cómo instalarla.
2. **Desde la ventana de Cursor** (si la orden de terminal no está): un chat de agente nuevo, el modelo elegido, «Auto-run» activado para la terminal, y pegar `migracion/PROMPT_NOCHE.md`. Funciona igual, pero si Cursor se detiene (límite de la conversación), nadie lo relanza hasta la mañana.

En los dos casos: el Mac **enchufado y con la tapa abierta**, Docker Desktop abierto y sin otras apps pesadas.

---

## 7. Cosas encontradas al preparar el plan (4-oct)

Arregladas ya en este PR (cada una en `despliegue/base.py` o en las herramientas de `migracion/`):

1. **La app de hoy no arrancaba sobre Postgres**: `base.py` no traducía los 4 disparadores con condición (`CREATE TRIGGER IF NOT EXISTS … WHEN`). El despliegue en Render habría fallado al arrancar.
2. **Ninguna anotación del rastro se podía escribir en Postgres**: `BEGIN IMMEDIATE` no existe ahí. Ahora es un candado de transacción (un solo escritor de la cadena de huellas a la vez, como hoy).
3. **`INSERT OR REPLACE`**, **`datetime('now', '-1 hour')`** y **`sqlite_master`** no se traducían: fijar clientes, el límite de opiniones por hora, la IA y la sincronía fallaban en Postgres.
4. **`lastrowid` solo funcionaba en 8 tablas**: el resto (p. ej. `opiniones`) devolvía `None` y rompía avisos y rastro. Ahora vale para cualquier tabla con contador. Y faltaba `rowcount`.
5. **La columna `registro.huella_previa` se perdía al pasar a Postgres** (se añade con `ALTER TABLE` al arrancar): sin ella, la cadena del rastro no se puede verificar. El inventario ya recoge los `ALTER TABLE … ADD COLUMN`, `0_base` la incluye, y la copia ahora **falla** si alguna columna no se copia.
6. **Los contadores quedaban uno por delante tras la copia** en tablas vacías (el primer id salía 2).
7. **El proxy necesita** que `servir.py` reciba su propio `Host` y acepte el origen de Next (`RO_ORIGEN_APP`); ya lo hace `servicios.sh`.
8. **Nest anunciaba `X-Powered-By: Express`**: quitado (paridad y seguridad).

Pendientes para la noche (están en `PROGRESO.md`):

9. **La tabla `avisos` está dos veces con columnas distintas** (`schema_v2.sql` y `despliegue/estado.py`). Se renombra la de la tubería a `tuberia_avisos`, en su commit (fase 2).
10. **El escáner de secretos recorre lo que genera v2** (`.next`, `dist`, `generated`, `legacy`) y da falsos positivos. Se añaden a `CARPETAS_FUERA`, en su commit (fase 1).
11. **Cinco bucles corren dentro del servidor** (avisos, avisos programados, envíos, sincronía, vigía). En la nube, el legado debe ser **una sola copia** hasta que pasen a un worker.
12. **La tubería depende de `~/RO_HERRAMIENTAS`** (27 lectores fuera del repo). El contenedor del legado los necesita, como ya hace `despliegue/preparar_contexto.sh`.
13. **Triaje** (Astra): su exclusión está verificada solo en SQLite y en Postgres responde 503 a propósito. Va a `excepciones.txt` y al informe como bloqueo conocido.

---

## 8. Después de la noche (para que escale)

- **Servidor MCP** (§2.14): primero tras el piloto, cuando las rutas de lectura estén en Nest. Ficha en `migracion/INTEGRAR.md` §6.
- **Funciones nuevas** (cerebros, diagnósticos, riesgo de baja, contexto del cliente, copia propia de las APIs): una ficha por función en `migracion/INTEGRAR.md`, con su contrato, permisos, datos, pruebas y qué falta. Esta noche viajan como están; se mudan con su grupo.
- Pasar a Nest lo que quedó en el legado (tubería y bucles con `@nestjs/schedule` y una cola; envíos, sincronía, IA, triaje con sus transacciones en Postgres), con las mismas puertas.
- Pasar la matriz de permisos a tablas (`puestos`, `reglas`, `permisos_por_puesto`) con su pantalla en Ajustes y su rastro. El motor ya estará en un solo sitio (`@ro/permisos`).
- Tipos de verdad en la base (`timestamptz`, `boolean`, `jsonb`) cuando nada escriba ya en texto.
- Rutas de verdad (`/mi-dia`) en vez de `#/mi-dia`, con redirección de las viejas.
- Las puertas en cada PR (GitHub Actions con datos inventados).
- Comprobaciones extra en esas puertas (no esta noche: necesitan red y paquetes nuevos): `squawk` sobre cada migración nueva (bloqueos largos y cambios peligrosos en Postgres), `knip` (código y dependencias sin usar), `eslint-plugin-security` y `pnpm audit --prod`.

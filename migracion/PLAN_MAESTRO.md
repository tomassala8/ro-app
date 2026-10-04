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
- **Puerta:** las pruebas de solidez de `despliegue/pruebas_noche.py --solo-solidez`, más una por fuente (API falsa caída → último dato bueno + aviso, ningún 0), dentro de `baterias.sh`. Además, `nunca_ceros.mjs` cuenta los `?? 0` del front, y ese número solo puede bajar.

En la nube, `ro-legado` (una sola copia) sigue siendo quien lee las APIs. La tabla vive en la misma Postgres, así que la copia de seguridad y la restauración de la fase 7 la cubren.

### 2.6 Rápida, a prueba de caídas y segura (Tomás, 4-oct)

Cada una con su puerta medible, en `puerta.sh` f3, f5, f6 y f7:

| Qué | Cómo se mide | Pasa si |
|---|---|---|
| **Rápida** | `migracion/rendimiento.py`: cada GET del contrato (3 personas × 5 veces) y el tiempo hasta que cada pantalla está pintada (`capturar.mjs` → `_tiempos.json`), en la de hoy y en la nueva | ninguna ruta o pantalla es más de un 25 % más lenta que hoy (con un margen de 100 ms en la API y 300 ms en pantalla), y nada pasa de 1,5 s (API) o 3 s (pantalla) si hoy no pasaba |
| **No se cae** | `migracion/caidas.sh`: ráfaga de 200 peticiones (20 a la vez); peticiones raras (ruta inexistente, JSON roto, 3 MB, Host ajeno, POST sin cabecera de la app); se cae el legado, se cae Nest, se reinicia Postgres | ningún 5xx ni cuelgue en la ráfaga; respuestas raras con 4xx limpio y sin la pila de errores; sin legado, 502 con mensaje en < 6 s y vuelta sola en < 60 s; lo mismo con Nest y con Postgres |
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
  3. `DATABASE_URL=<la de Render> python3 despliegue/llave_ghl.py sembrar`
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
| **0 · tarde (Tomás)** | traer el plan al Mac, `preparar_noche.sh --instalar` hasta LISTO, lanzar `noche.sh` | — | LISTO |
| **1 · referencia** | inventario del Mac, escáner, instantánea del código, copia de la base, servicios, grabar contrato, vectores, fotos, casos de escritura, `baterias.sh` | 60 min | `puerta.sh f1` |
| **2 · base** | arreglo `avisos`→`tuberia_avisos`, `rehacer_base.sh` si cambiaron tablas, Postgres, copia, publicar `data`, la app de hoy sobre Postgres; arreglar `base.py` hasta que lea y escriba igual | 60–90 min | `puerta.sh f2` |
| **3 · app nueva entera** | Nest y Next con proxy a la app de hoy. Debería salir verde a la primera: ya está ensayado | 20 min | `puerta.sh f3` |
| **4 · permisos** | `permisos.py` → `@ro/permisos`, función a función | 60–90 min | `puerta.sh f4` (100 %) |
| **5 · API a Nest** | grupos de §2.2, uno a uno: se escribe el módulo, se añaden sus rutas a `RUTAS_EN_NEST`, puerta; si no sale en 3 intentos, se quitan de la lista | lo que quede hasta 2 h antes del final | `puerta.sh f5` por grupo |
| **4.2 · pruebas de permisos** | las que impiden volver atrás (anexo de `PENDIENTES_LOGICA.md`, punto 8) | 30–45 min | `puerta.sh f4` |
| **5.10 · fallos pendientes** | los 69 de `PENDIENTES_LOGICA.md` (L-01…L-49 del hilo de feedback y N-01…N-20 de la migración), L-01 y L-21 primero y luego de seguridad a presentación, con su prueba | hasta 90 min; los de seguridad no se saltan por reloj | `puerta.sh f5` + la prueba de cada fallo |
| **6 · front en React** | carcasa en `/carcasa`, `ctx.ts`, puente; carcasa a «/» con fotos iguales; pantallas una a una | lo que quede hasta 1 h antes del final | `puerta.sh f6` por pieza |
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
| El motor de permisos no llega al 100 % en 90 minutos | Se guarda lo hecho, se apunta qué vectores fallan y **no se muda a Nest ninguna ruta que dependa de permisos** (casi todas): se salta la fase 5 y se pasa a la 6. La app sigue entera por el proxy. |
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

**Recomendado: Claude Fable 5.1**, si tu Cursor lo ofrece: es el más capaz de Anthropic para trabajos largos y autónomos de programación. **Alternativa: Claude Opus 5.5.** No uses modelos «rápidos» ni el modo automático: en la fase 4 un detalle mal traducido abre un agujero de permisos. No he podido comprobar desde aquí qué modelos tiene tu Cursor; si no ves ninguno de los dos, elige el Claude más reciente de la lista.

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

- Pasar a Nest lo que quedó en el legado (tubería y bucles con `@nestjs/schedule` y una cola; envíos, sincronía, IA, triaje con sus transacciones en Postgres), con las mismas puertas.
- Pasar la matriz de permisos a tablas (`puestos`, `reglas`, `permisos_por_puesto`) con su pantalla en Ajustes y su rastro. El motor ya estará en un solo sitio (`@ro/permisos`).
- Tipos de verdad en la base (`timestamptz`, `boolean`, `jsonb`) cuando nada escriba ya en texto.
- Rutas de verdad (`/mi-dia`) en vez de `#/mi-dia`, con redirección de las viejas.
- Las puertas en cada PR (GitHub Actions con datos inventados).

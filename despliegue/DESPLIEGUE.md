# Despliegue de la app de RO · guía paso a paso

**2-oct-2026 · carril C5.** Destino decidido en el documento 26: **todo en Render (Frankfurt)** y **Cloudflare solo delante** (Access, dominio, copia en R2 y página de emergencia). Vigilancia: **solo Better Stack**. La alternativa con servidor propio (Hetzner) usa la misma imagen y está al final.

Todavía no se ha desplegado nada ni se ha creado ninguna cuenta.

---

## Cómo queda, en cinco líneas

1. **Una imagen** (`Dockerfile`) para todo: el servicio web y las tres tareas.
2. **El servicio web `ro-app`** es `servir.py` con los mismos permisos de hoy. En el servidor **solo vale el sello firmado de Cloudflare Access**: sin él responde 403 a todo (`despliegue/acceso_cf.py`).
3. **Tres tareas programadas:**
   - `ro-ligera`: cada hora de 7 a 23 h.
   - `ro-completa`: a las 6:00 y a las 14:00.
   - `ro-noche`: a las 3:00, con la copia de la base y las pruebas.

   Todas lanzan **una sola tubería** (`despliegue/tuberia.py`) con orden, reintentos, bloqueo y «último dato bueno».
4. **Una sola base Postgres, en Supabase** (Frankfurt; decisión de Tomás del 4-oct, en lugar de la base de Render) guarda:
   - El rastro, las decisiones y las asignaciones de `servir.py` (por `despliegue/base.py`).
   - El estado de la tubería.
   - La llave de GHL que rota, con bloqueo.
   - Los datos de cada módulo por versión (`despliegue/publicacion.py`). La web los baja cada minuto.
5. **Better Stack** recibe:
   - Un latido al final de cada vuelta (si no llega, avisa).
   - Los errores, con el SDK de Sentry apuntando a Better Stack y sin datos personales.
   - La vigilancia desde fuera de la dirección de la app.

---

## Lo que hace Tomás (unos 60-75 minutos en total)

| # | Qué | Dónde | Tiempo |
|---|---|---|---|
| T1 | Abrir **Render** a nombre de la empresa, plan **Pro**, con la tarjeta de la empresa. Firmar su acuerdo de tratamiento de datos (DPA) | render.com | 10 min |
| T1b | En **Supabase**: cuenta de la empresa con **segundo factor**. Proyecto en **Frankfurt (eu-central-1)**, plan **Pro** (el gratis se pausa a los 7 días sin uso) y cómputo **Small** o mayor (30 personas a la vez). Contraseña de la base larga y nueva. Luego, en el proyecto: (1) **Data API desactivada** (Settings › API: si no, las tablas de `public` quedan expuestas por internet con la llave anónima); (2) **SSL obligatorio**; (3) **Network restrictions**: solo las IP de salida de Render en Frankfurt (Render › servicio › Outbound) y nada más; (4) en Database › Connection pooling, tamaño del pool ≥ 40. Pasar a Claude: la cadena del **Session pooler** (puerto **5432**, nunca el 6543) para `DATABASE_URL` del grupo `ro-base`, el **certificado SSL** (Database › SSL › Download) para `RO_PG_CA`, y la versión de Postgres (Settings › Infrastructure) | supabase.com | 20 min |
| T2 | Abrir **Better Stack** con la región de la UE. Crear 1 monitor de la dirección de la app, 1 latido («tubería») y 1 fuente de errores. Pasar a Claude sus tres direcciones (el latido, el DSN de errores y la página de estado) | betterstack.com | 10 min |
| T3 | En **Cloudflare**: dejar a Agus como segundo administrador. Crear un bucket de **R2 en jurisdicción UE** (`ro-copias`) con: **bloqueo del bucket** de 7 días en `copias/` (nadie puede borrar ni sobrescribir una copia antes, ni con la llave), regla de borrado a 7 días en `copias/horas/` y a 30 en el resto, y una llave de API solo para ese bucket. Comprobar: con esa llave, borrar una copia tiene que fallar (ver `migracion/PLAN_MAESTRO.md` §2.12) | dash.cloudflare.com | 15 min |
| T3b | En **Backblaze B2**, una cuenta NUEVA con otro correo (no el de Cloudflare ni el de Google de RO) y su segundo factor. Bucket privado en la **región UE**, con cifrado del servidor y **Object Lock en modo «compliance», 30 días por defecto** (ni el dueño puede borrar antes). Una llave de aplicación **solo escribir** («Write Only») para ese bucket. Guardar el acceso a esa cuenta fuera del Mac del día a día. Pasar a Claude el endpoint, el bucket y la llave (van en `RO_B2_*` de `ro-vigilancia`). Comprobar: con esa llave, borrar o leer una copia tiene que fallar | backblaze.com | 15 min |
| T4 | En Render: **New › Blueprint**, elegir el repositorio privado y aceptar. Se crean `ro-app`, `ro-ligera`, `ro-completa`, `ro-noche` y `ro-copias`. La base no: es Supabase (T1b) | Render | 5 min |
| T5 | Pegar las llaves en el grupo **`ro-llaves`** (la lista exacta está en `render.yaml`; los nombres son los del llavero en mayúsculas). **Meta: el token del usuario de sistema** sin caducidad (T5 del estudio 23), no el de 60 días | Render › Env Groups | 15 min |
| T6 | **Sembrar la llave de GHL de agencia en la base** (un solo dueño a partir de ese momento). En el Mac, cópiala: `security find-generic-password -s ghl_app_refresh_token -w \| pbcopy`. Después, en Render › `ro-app` › Shell, ejecuta `GHL_SEMILLA="<pegar>" python3 despliegue/llave_ghl.py sembrar`. **Desde ese momento no lances `app.py`, `captacion.py` ni `externos.py` en el Mac**: la llave rotaría y el servidor se quedaría fuera | Mac + Render | 5 min |
| T7 | En Cloudflare Zero Trust: crear la aplicación de **Access** para `panel.<dominio>` (solo correos de RO) y otra para `emergencia.<dominio>`. Método de entrada: **solo Google Workspace**; **quitar el «One-time PIN»** (un código al correo saltaría el segundo factor). En **Google Workspace › Seguridad › Verificación en dos pasos: obligatoria** para todos (Google Authenticator o la app de Google); el segundo factor lo impone Google, no la app. En el dominio: Bot Fight Mode y las reglas gestionadas del WAF. Pasar a Claude el **nombre del equipo** y la **etiqueta AUD** (van en `RO_CF_EQUIPO` y `RO_CF_AUD` de `ro-app`) | one.dash.cloudflare.com, admin.google.com | 15 min |
| T8 | Dominio propio en `ro-app`. Primero en «solo DNS» para que Render emita el certificado, después en «proxied». Luego, en `ro-app` › Settings, **desactivar la dirección `*.onrender.com`** ([Ver fuente ↗](https://render.com/docs/custom-domains) · [Ver fuente ↗](https://render.com/docs/configure-cloudflare-dns)) | Render + Cloudflare | 10 min |
| T9 | Dar el «sí» a la primera publicación cuando Claude enseñe la batería en verde en la vista previa **y `python3 despliegue/seguridad_nube.py --dominio panel.<dominio> --render <cada *.onrender.com>` en VERDE** (sin sesión ni con cabeceras falsas sale ningún dato) | — | 2 min |

**La llave de GHL nunca va en una variable de entorno.** Rota en cada uso: si se queda en una variable, la siguiente vuelta usaría una ya gastada.

---

## Lo que hace Claude

### Antes de la cuenta (hecho el 2-oct)

- `config.py`: rutas y llaves en un solo sitio. En el Mac, el llavero como siempre; en el servidor, variables de entorno.
- 15 lectores de `~/RO_HERRAMIENTAS` leen primero la variable de entorno, si existe. En el Mac no cambia nada.
- 21 ficheros de generadores de módulos cerrados ya sacan sus rutas de `config.py`. Sus salidas, comparadas antes y después, son iguales: 153 de 153 ficheros.
- `tuberia.py`, `pruebas_noche.py`, `publicacion.py`, `llave_ghl.py`, `acceso_cf.py`, `base.py`, `copia_base.py` y `emergencia.py`, probados en local (ver `_ESTADO_C5.md`).

### El día de la cuenta, en este orden

1. **Repositorio.**
   - `sh despliegue/preparar_contexto.sh` arma `ro-app/`: código de la app y de los lectores, `Dockerfile`, `render.yaml` y `.gitignore`. **Sin datos ni llaves**; tiene su propia puerta de secretos.
   - Se sube a un repositorio **privado** de la empresa.
   - ⚠️ Antes de subir, revisar 6 ficheros que mencionan correos de clientes como ejemplo (lista en `_ESTADO_C5.md`).
2. **Primera carga de datos a mano.**
   - Desde el Mac, con la IP de Tomás añadida un momento a las restricciones de red de Supabase (y quitada al acabar), se ejecuta `python3 despliegue/publicacion.py publicar crudos`.
   - Sube los 9 datos a mano y las carpetas hermanas (94 MB, 19 MB comprimidos en la base).
   - Después se vuelve a cerrar la dirección externa.
   - Se repite cada vez que cambie un dato a mano, hasta que cada uno pase a lector en vivo o a una tabla de Ajustes (riesgo R7).
3. **Comprobar la base.** En el Shell de `ro-app`, `python3 despliegue/base.py --probar` crea el esquema en Postgres y comprueba que el rastro no se puede borrar. ⚠️ Es la primera vez que corre contra Postgres.
4. **Comprobar la llave de GHL.** `python3 despliegue/llave_ghl.py estado` debe decir «llave en la base: sí».
5. **Primera vuelta a mano.** En `ro-completa` › «Trigger run». Se mira el registro y que `publicacion.py versiones` enseña una versión «vigente» de `data`.
6. **Batería.** Se lanza `ro-noche` a mano. Tiene que salir verde, incluido el apartado «acceso en modo servidor (E49)».
7. **Better Stack.** Se ponen `RO_LATIDO_URL` y `SENTRY_DSN` en el grupo `ro-vigilancia`. Simulacro: se pausa `ro-ligera` 2 h y se comprueba que avisa.
8. **Copia.**
   - Se ponen las variables `RO_R2_*`.
   - `ro-noche` sube cada noche `postgres.dump` a R2.
   - El día 1 de cada mes, `copia_base.py --probar` restaura la última copia aparte y la comprueba.
9. **Página de emergencia.**
   - La tubería completa la deja en `despliegue/estado/emergencia/`:
     - `sitio/`, para Cloudflare Pages detrás de Access.
     - `marcadores/`, un fichero por persona.
     - `clickup/`, un texto por puesto.
   - Subirla a Cloudflare Pages y a ClickUp necesita el permiso de Tomás la primera vez. Después se automatiza.

### Tokens de acceso (Zoho, Google, Zoom, Snov)

- Cada proceso reutiliza el token de 1 hora que haya en la caché (`~/RO_HERRAMIENTAS/cache_tokens.py`), en vez de pedir uno nuevo en cada llamada.
- En la nube la caché está en la tabla `tokens_acceso` de la base (Supabase) y se crea sola.
- Si alguna vez hiciera falta apagarla: `RO_SIN_CACHE_TOKENS=1`.

### Cada semana (turno de Claude)

- Leer las ejecuciones fallidas: `python3 despliegue/estado.py`, los registros JSON y los errores en Better Stack.
- Arreglar en la vista previa y publicar solo con la batería en verde.

---

## El vigía: que siempre haya alguien mirando (3-oct)

`despliegue/vigia.py` comprueba **cada 10 minutos** que todo funciona, **aparte de la tubería** (la vigila a ella también). Lo enseña la pantalla **«Salud del sistema»** (Agus, Mili y Tomás).

- **Qué mira.** Las 27 conexiones (una lectura barata cada una, sin gastar créditos; la llave de GoHighLevel que rota no se usa nunca, solo se mira su última rotación) y la app por dentro: la app web, la última vuelta de la tubería, envíos pendientes o fallidos, cambios sin reflejar en ClickUp y conflictos, la IA frente a su tope (en %), el disco, la base y la copia del día.
- **Avisos** en `#avisos-altas`, agrupados: cuando algo pasa a rojo, a Agus; si sigue más de 1 h, a Mili y Tomás; cuando vuelve, aviso de recuperación. Nunca uno cada 10 minutos.
- **Ajustes** en `data/vigia/config.json` (`cada_min`, `escalar_min`, cada cuánto se prueba lo que tiene cupo corto). Variables: `RO_VIGIA_APP_URL` (dirección interna de la app; vacío = no se mira), `RO_VIGIA_LATIDO_URL` (latido de Better Stack: si el vigía se para, avisa desde fuera).

### En el Mac (local)

```bash
cd ~/Downloads/APP_RO_ROLES_Y_PERMISOS_2026-10-02/30_APP_PROTOTIPO
python3 despliegue/vigia.py --bucle          # en una pestaña del Terminal; Ctrl+C para parar
python3 despliegue/vigia.py                  # una sola vuelta
python3 despliegue/vigia.py --solo clickup   # solo una fila (lo mismo que «Probar ahora»)
python3 despliegue/vigia.py --prueba         # simulacro de caídas sobre una COPIA de la base (no avisa a nadie de verdad)
```

El bucle lanza cada vuelta en su propio proceso: si una se cuelga, la siguiente entra igual. Si dos coinciden, la segunda sale sin hacer nada (código 75).

### En el servidor (Coolify): tarea programada cada 10 min

En el recurso de la app › **Scheduled Tasks** › **Add**:

| Campo | Valor |
|---|---|
| Name | `vigia` |
| Command | `python3 despliegue/vigia.py --quien coolify` |
| Frequency | `*/10 * * * *` |
| Container | el de la app (`app`): así escribe en el mismo `data/vigia/` que lee la web |

Variables del recurso: `RO_VIGIA_APP_URL=http://localhost:<PUERTO>/` y, cuando exista, `RO_VIGIA_LATIDO_URL` (un latido nuevo en Better Stack con periodo de 10 min y gracia de 15). La zona horaria del servidor en Coolify debe ser `Europe/Madrid` para que el cron cuadre con las horas de la pantalla (las horas del vigía ya van en hora de Madrid aunque no lo esté).

Con cron normal (Hetzner sin Coolify): `*/10 * * * * cd /app && python3 despliegue/vigia.py --quien cron >> despliegue/estado/registros/vigia.log 2>&1`.

---

## Volver atrás

| Qué | Cómo | Quién |
|---|---|---|
| Código | Render › `ro-app` › Deploys › «Rollback» a la versión anterior (reutiliza la imagen ya construida) | Agus o Claude |
| Datos de la app | `python3 despliegue/publicacion.py versiones` y luego `… volver <id>`. La web la baja en menos de 1 min | Claude (Agus con la guía) |
| La base entera | Supabase › Database › Backups (diarias; vuelta a un minuto concreto solo con el complemento PITR). Lo nuestro: `pg_restore` de la copia de R2 (cada hora, 7 días) o de B2 (2 al día, 30 días, inmutable) en una base nueva y cambiar `DATABASE_URL` | Claude |

---

## Qué pasa si…

| Si… | Lo que hace el sistema | Lo que hace la persona |
|---|---|---|
| Una herramienta no responde | Se reintenta 3 veces (30 s, 2 min, 8 min). Si sigue fallando, ese módulo **se queda con su último dato bueno** y su sello pasa a «dato_viejo». Nada a medias | Nada. Si dura más de 3 h, llega un aviso (≤3 al día) |
| Dos vueltas coinciden | La segunda ve el bloqueo y sale sin hacer nada (código 75, que `entrada.sh` trata como bien) | Nada |
| La llave de GHL se pierde | 401 en el paso del CRM y aviso | Tomás vuelve a autorizar la app y repite T6 |
| Se cae Render | La app no carga. Better Stack avisa | El equipo usa la página de emergencia (Cloudflare Pages, ClickUp o marcadores) |
| Alguien encuentra la dirección de Render | Responde 403 sin sello de Access (y además está desactivada) | — |

---

## Alternativa: servidor propio (Hetzner) con la misma imagen

- `docker-compose.yml`:
  - `base`: Postgres 16 con volumen.
  - `app`: `servir.py` en modo servidor.
  - `tunel`: Cloudflare Tunnel, sin ningún puerto abierto en el servidor.
- Las tareas las lanza **systemd**:
  - `servidor/ro-tarea@.service`, con `docker compose run --rm tarea <modo>`.
  - Los tres `.timer`, que van en hora de Madrid.
- También vale cron: `servidor/crontab.ejemplo`.
- La copia sigue yendo a R2.
- Hay que mantener el sistema operativo: actualizaciones automáticas y reinicio programado. Por eso el documento 26 prefiere Render.

## Otra alternativa: Google Cloud Run

Ver `CLOUD_RUN.md`.

## Pendiente de otros carriles

- **C0 (`servir.py`):**
  - En Render, el botón «Actualizar ahora» no puede lanzar la tubería dentro de la web. Debe pedir una vuelta de `ro-ligera` por la API de Render: ⚠️ `POST /v1/cron-jobs/{id}/runs`, sin comprobar.
  - En local ya usa la tubería: desde el 2-oct, `recarga.json` lanza `despliegue/tuberia.py`.
- **C0:** servir la salud de la tubería (`despliegue/estado/salud.json` y la tabla `sellos`) en Ajustes › Conexiones.
- **C1:** cuando cierre cada módulo en obra (mi día, agenda, chat del equipo, dinero, panel de dirección), poner `"activo": true` en su paso de `despliegue/pasos.json` y quitar sus rutas fijas por `config.py`.

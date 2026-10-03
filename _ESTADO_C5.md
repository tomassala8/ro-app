# C5 · Servidor · _ESTADO

**2-oct-2026, 17:25.** La app queda lista para subirla a un servidor sin desplegar nada.

- No se ha creado ninguna cuenta y no se ha escrito en ninguna herramienta externa.
- Destino según el documento 26: **todo en Render (Frankfurt)**, con Cloudflare solo delante y vigilancia solo con Better Stack.
- La misma imagen sirve para un servidor propio (Hetzner) o para Cloud Run.
- La guía para Tomás y para Claude está en `despliegue/DESPLIEGUE.md`.

## Qué hay

| Pieza | Fichero | Qué hace |
|---|---|---|
| Rutas y llaves | `config.py` | Única fuente de rutas (`RO_HOME`, `RO_CRUDOS`, `RO_HERRAMIENTAS`, `RO_DATOS`, `RO_ESTADO_DIR`). Incluye los 9 datos a mano con su dueño y su edad máxima, y las 32 llaves con lo que necesita cada lector (`SECRETOS_POR_LECTOR`). Orden de búsqueda de cada llave: carpeta privada → variable de entorno (nombre en mayúsculas) → `.env` → llavero del Mac. `python3 config.py` enseña qué hay, sin enseñar ningún valor |
| Tubería única | `despliegue/tuberia.py` + `pasos.json` | Ver el detalle debajo de la tabla |
| Estado (SQLite ↔ Postgres) | `despliegue/estado.py` | Una sola interfaz: SQLite en local y Postgres con `DATABASE_URL`. Tablas `ejecuciones`, `pasos`, `llaves`, `avisos` y `sellos`. Bloqueo con `fcntl` o con el bloqueo consultivo de Postgres |
| Llave de GHL que rota | `despliegue/llave_ghl.py` | Ver el detalle debajo de la tabla |
| Datos por versión | `despliegue/publicacion.py` | Espacios `data`, `cache` y `crudos` en la base, con contenido deduplicado y comprimido. La versión vigente cambia en una sola operación. Vuelta atrás con `volver <id>`. La web baja `data` cada minuto |
| Sello de Access (E49) | `despliegue/acceso_cf.py` + 5 enganches en `servir.py` | Con `RO_MODO=servidor` solo vale un JWT RS256 firmado por el equipo de Cloudflare: comprueba firma, audiencia, emisor y caducidad. `?yo=`, `X-RO-Yo` y la cabecera de correo no valen. `/vivo` responde 200 sin datos. Sin dependencias externas |
| `servir.py` sobre Postgres | `despliegue/base.py` | Traduce lo mínimo de SQLite a Postgres (`?`, `datetime('now')`, `INSERT OR IGNORE`, `PRAGMA`, `lastrowid`). Pasa `schema_v2.sql` a Postgres, incluidos los disparadores que impiden borrar el rastro. ⚠️ Sin probar contra un Postgres real |
| Batería nocturna | `despliegue/pruebas_noche.py` | Ver el detalle debajo de la tabla |
| Copia de la base | `despliegue/copia_base.py` | Copia SQLite coherente o `pg_dump`, a disco (14 días) y a R2. `--probar` restaura aparte y compara filas |
| Página de emergencia | `despliegue/emergencia.py` + `emergencia_enlaces.json` | Una página y un fichero de marcadores por persona, y un texto de ClickUp por puesto. Solo enlaces, sin cifras, correos ni teléfonos |
| Despliegue | `Dockerfile`, `entrada.sh`, `render.yaml` (principal), `docker-compose.yml` + `servidor/*.timer`, `ro-tarea@.service`, `crontab.ejemplo` (Hetzner), `CLOUD_RUN.md`, `requirements.txt`, `preparar_contexto.sh` | `preparar_contexto.sh` arma el repositorio con solo código: 3,6 MB, sin datos ni llaves y con su propia puerta de secretos |

**`tuberia.py` en detalle:**
- Grafo de 34 pasos (29 corren en la completa y 23 en la ligera sin red; 5 de módulos en obra, apagados): lectores en bruto → base → capa E1 → módulos → verdad → catálogo → emergencia → foto.
- Modos `--ligero`, `--completo` y `--desde-crudo` (sin red).
- 3 reintentos (30 s, 2 min, 8 min), tiempo máximo por paso y horario por fuente (`cada_min`).
- Bloqueo: nunca dos vueltas a la vez; la segunda sale con el código 75.
- «Último dato bueno»: guarda las salidas, valida (código, JSON y secretos nuevos) y, si falla, restaura la versión anterior y la sella como «dato_viejo». Sus dependientes no corren.
- Registro JSON por vuelta y avisos E0.
- Opcionales: Sentry/Better Stack con filtro de datos personales, latido y publicación en la base.

**`llave_ghl.py` en detalle:**
- Dueño único: la tubería. La llave vive en la base con bloqueo.
- Se presta a cada paso en una carpeta temporal 0700. `app.guarda()` escribe ahí y, al acabar, la llave nueva vuelve a la base.
- En el Mac solo pone el bloqueo; el llavero sigue igual.
- `sembrar` (T6), `estado` y `prueba-simulada`.

**`pruebas_noche.py` en detalle:**
- Las 8 `pruebas_*.py` / `probar_*.py` / `comprobar.py` que existen.
- **Humo:** cada módulo hecho responde 200 por puesto.
- **Fuga:** matriz completa puesto × fichero contra `reglas_permisos.json`.
- **Acceso E49:** un `servir.py` en modo servidor, con sellos firmados con `openssl`.
- **Cuadre:** 3 cifras cruzadas entre Captación, CRM, verdad y ficha.
- Arranca su propio `servir.py` con una copia de la base y nunca toca la de producción.
- Deja el informe en JSON y Markdown y avisa si sale en rojo.

**Avisos:** se reutiliza E0 tal cual.
- Cada vuelta se apunta en `recargas` de `local.db`, y `servir.calcular_avisos()` dispara «recarga_fallida» y «fuente_rota» o «fuente_vieja».
- Los avisos propios («tuberia_dato_viejo», «pruebas_noche», «publicar») entran en `avisos` con el mismo tope de 3 al día y sin repetir.
- En un servidor sin `local.db`, van a la tabla `avisos` de la base de estado con la misma regla.
- Hacia fuera solo salen si existe `RO_AVISOS_WEBHOOK`.

## Cambios fuera de `despliegue/` (mínimos y compatibles)

- **`~/RO_HERRAMIENTAS`, 15 lectores** (`hd`, `ga`, `app`, `gads`, `gg`, `zh`, `mt`, `mc`, `zm`, `sr`, `ws`, `captacion`, `sv`, `chat`, `zd`). `llave()` mira primero `RO_SECRETOS_DIR/<nombre>` y la variable en mayúsculas. Si no hay ninguna, usa el llavero como hoy. `ghl_app_refresh_token` nunca sale de una variable. `app.guarda()` escribe en la carpeta privada solo si existe `RO_SECRETOS_DIR`. Copia de los originales en el bloc temporal de la sesión.
- **21 ficheros de generadores de módulos cerrados.** Cambian las rutas fijas `~/Downloads/…` y `~/RO_HERRAMIENTAS` por `config.*`, y nada más:
  - `build_data.py` y `fuentes/comun.py`.
  - Decisiones, personas (`comun.py` y `generar_personas.py`), redes, incidencias, bandeja, WhatsApp, ficha, nuevos, CRM.
  - Captación (`generar_captacion.py` y `anuncios_meta.py`), producción (`comun_equipo.py` y `extraer_clickup.py`).
  - Reuniones, SEO, informes, conexiones y ventas.

  En `generar_conexiones.py`, fuera del Mac, la llave sale de `config.secreto()`. **No se han tocado** informe, finanzas, `dinero_cliente`, mi día, agenda, chat del equipo ni panel de dirección.
- **`servir.py` (por orden del coordinador, 5 enganches con la marca «C5»):**
  - Importa `acceso_cf`.
  - `quien()` usa solo el sello en modo servidor.
  - `do_GET` exige el sello también para la carcasa y deja `/vivo` abierto.
  - `main()` escucha en `0.0.0.0:$PORT` y arranca la sincronización de `data/` en modo servidor.
  - `conectar()` usa Postgres si existe `DATABASE_URL`.

  Sin esas variables, todo sigue igual que antes.

## Pruebas hechas en local (sin gastar cupos)

Todas en **copias exactas** de la app, en el bloc temporal de la sesión, para no pisar `data/` mientras los demás carriles trabajan. En la app real solo se ha creado `despliegue/estado/tuberia.db`.

| Prueba | Resultado |
|---|---|
| Mismas salidas antes y después del cambio de rutas: 18 generadores sin red en una copia «antes» y otra «después», con las horas normalizadas | **153 de 153 ficheros iguales** |
| Rutas de `config.py` frente a las fijas de antes (12 rutas) | **Todas iguales** |
| Lectores con llavero y con variable de entorno (Zoho); `ghl_app_refresh_token` ignora la variable | Bien |
| Tubería `--ligero --desde-crudo` (21-23 pasos según la hora) | **ok en 13 s**; vuelta final de las 17:19 en verde |
| Fallo provocado: 3 reintentos, salida parcial restaurada, dependiente sin correr, sello «dato_viejo», avisos E0 en `local.db`, segunda vuelta a la vez → 75 | Bien |
| Llave de GHL: 24 rotaciones seguidas con el `app.py` real y una llave falsa en una base aparte; un segundo préstamo a la vez queda bloqueado | **Bien** |
| Contenedor vacío simulado: baja de la base crudos, cachés y `data`, y regenera todo | **Bien** (el único fallo era de otro carril, ver abajo) |
| Publicar y bajar `data` (187 ficheros); volver a una versión anterior | Iguales byte a byte |
| Sello de Access en `servir.py` (modo servidor): 16 casos (sin sello, `?yo=`, `X-RO-Yo`, correo falsificado, caducado, otra audiencia, otro equipo, firma rota, clave desconocida, correo fuera de personas, carcasa, `/vivo`, galleta) | **16 de 16** |
| Batería nocturna completa (16:52, con Chrome) | Las 8 baterías existentes en verde · humo 362 bien · E49 8/8 · cuadre 0 diferencias |
| Copia de la base y prueba de restauración | Bien (integridad ok, filas iguales) |
| Página de emergencia | 30 páginas, 30 ficheros de marcadores y 20 textos de puesto; 0 correos y 0 teléfonos fuera de los enlaces |
| `render.yaml` y `docker-compose.yml` | YAML válido |
| `preparar_contexto.sh` | 3,6 MB; ningún JSON con hallazgos del escáner |

## Lo que ha encontrado la batería (de otros carriles, para el coordinador)

1. **Fuga transitoria a las 16:52:** Mili recibía `panel_direccion/*`, `finanzas`, `mi_dia/cambios` y Lina `ajustes/conexiones` y `personas_m20/contratacion`. A las 17:09 y a las 17:19 da **0 problemas** con las reglas actuales. Fue un estado intermedio de C0/C2. La prueba de fuga ya lo vigila cada noche.
2. **Cuadre a las 17:19:**
   - **Kiosko Box:** Captación da 0 leads y 0 € el mes anterior, y la ficha (E1) da 1.419 leads y 4.801,48 €.
   - **Account de Garmande y de Musashi:** la verdad dice Candela y Natalia, y Captación y CRM dicen Casiana y Agustina.
3. **`pruebas_coherencia.py`** en rojo a las 17:19 (agenda: 18 diferencias en «cliente en rojo con reunión»).
4. **`generar_informes.py --ficheros`** cayó un rato (hacia las 17:10) porque `personas[].correos` llegó como objeto. La tubería **conservó el último dato bueno**. A las 17:19 ya iba bien.

## Añadido después (2-oct, 17:25-18:00), a petición del coordinador

- **La tubería sigue el orden de E1 y lleva todos los módulos:**
  - Orden: `externos.py` → `snov/por_cliente.py` → `captacion.py` → `build_data.py` → `generar_datos.py --en-vivo meta` → todos los generadores de módulo (incluidos la cadena del panel de dirección, agenda, chat del equipo, el importador por API de la hoja de informes, dinero, sueldos y atajos) → `generar_verdad.py` → catálogo, emergencia y foto → **Mi día al final**. Son 39 pasos.
  - Una sola pasada coherente: todos los pasos reciben la misma hora de datos (`RO_HORA_DATOS`).
  - **`recarga.json` ya no tiene pasos sueltos.** «Actualizar ahora» lanza `despliegue/tuberia.py` (la copia anterior está en el bloc temporal de la sesión).
- **Cadena del panel de dirección.** `rehacer_v2.sh` **NO se usa tal cual**: su `_plantilla/montar_v2.py` rehace la plantilla desde `_plantilla/` y **borra la pestaña «Atribución» (atr) del v30**, que solo existe en `panel_template_v2.html`. Me pasó a las 17:24 en una prueba: lo restauré a las 17:27 desde la copia de los datos a mano de las 17:12 y el generador del panel volvió a funcionar. El paso `panel_v29` hace `build_financiero` → `build_captacion_extra` → `render_v2` (sin montar ni zsh) y conserva el v30.
- **Caché del token de acceso** (Zoho dio 400 por crear demasiados).
  - `~/RO_HERRAMIENTAS/cache_tokens.py` es compartido entre procesos y tiene bloqueo:
    - En el Mac, va en `~/.cache/ro_tokens/` (0700/0600).
    - En el servidor, en la tabla `tokens_acceso` de la base.
    - `RO_SIN_CACHE_TOKENS=1` la apaga.
  - La usan `zh.acceso()`, `gg.acceso()`, `gads.acceso()`, `zm.token()` y `sv.token()`. Es un cambio compatible: si falta el módulo, todo funciona como antes.
  - `generar_conexiones.py` ya no pide tokens por su cuenta: usa los de los lectores.
  - **Prueba real: 21 `zh.acceso()` = 1 refresco y Desk responde.** `despliegue/pruebas_tokens.py`: 20 lecturas = 1 refresco · 20 procesos a la vez = 1 refresco · dentro del margen se refresca · todo bien.
  - Queda fuera `zh_escribir.py` (escritura, fuera de la tubería).
- **Instantáneas (regla de seguridad).**
  - Ya no van a `despliegue/estado/instantaneas/`. Van a una carpeta temporal privada **fuera del proyecto** (0700), que **se borra al acabar cada paso**. Al empezar cada vuelta se borra cualquier resto antiguo.
  - **Solo se copia lo que pasa la puerta de secretos de E0.** Nunca se copian `_cache/`, `_crudo/` ni `_privado/`: si el paso falla, se quedan como los dejó y se apunta en el registro (`sin_restaurar`).
  - Nunca entran en el repositorio (`preparar_contexto.sh` excluye `despliegue/estado/`) ni en la base (`publicacion.py` no las incluye).
  - La instantánea de `vuelta_1` con 4 teléfonos ya no existe: se borró al acabar su vuelta, a las 17:38.

## Cierre (2-oct, 19:15)

- **Tubería: 42 pasos.** Se han añadido:
  - `paneles`: en la ligera, desde la caché; en la completa, en vivo, con la llave de GHL prestada.
  - `modular`: sin clave escribe «sin conectar» y no falla.
  - `alertas`: al final, justo antes de Mi día.
  - Bandeja e informes pasan a un tiempo máximo de 900 s. Externos y Snov, como mucho cada 6 h en la ligera (tardan 11 min y 2 min).
- **Vueltas en local:**
  - La de las 17:42, en vivo, se paró a mano a las 18:52 porque Desk iba muy lento (bandeja agotó sus 300 s cuatro veces). Quedó marcada como «interrumpida» y no dejó nada a medias: informes, el paso que estaba en marcha, quedó igual que su copia previa.
  - **Vuelta 3 (18:53-19:10, ligera con variante sin red donde existe): 34 pasos bien, 0 fallos** (más 5 que no tocan en la ligera y 3 que no tocaban todavía por su horario). Antes, la vuelta 1 (17:28) dio 33 bien.
- **Instantáneas:** se borraron todas las de `despliegue/estado/instantaneas/`, incluidas las de agenda y redes. Desde ahora son temporales, fuera del proyecto, pasan el escáner y no incluyen cachés.
- **Pruebas finales:**
  - `pruebas_coherencia.py`: **0 errores, 0 avisos**.
  - `pruebas_tokens.py`: **todo bien**.
  - `pruebas_e0.py`: **1 fallo, que no es de C5.** Gustavo (GHL), al abrir accompany, recibe `fuentes.meta.datos.serie`: E1 añadió la serie de Meta a las 17:50 y el recorte de `servir.py` no la quita para ese puesto. Lo tiene que arreglar E1 (no generarla) o C0 (recortarla).
  - `escaner_secretos.py --proyecto`: **8 ficheros con hallazgos, todos de otros módulos**: cachés en bruto de producción, nuevos, dinero y ficha, y `fuentes_equipo/equipo.json`, `fuentes/emparejamientos_manual.json` y `fuentes_ficha/contactos_manual.json`. Ninguno sale de `despliegue/`.
  - `preparar_contexto.sh` ahora **para la subida** si un `.json` del código da hallazgos: hoy bloquea esos 3 ficheros manuales, que deben pasar a la base (espacio «crudos») o limpiarse.

## Pendiente

**De Tomás (ver `DESPLIEGUE.md`):** cuentas de Render Pro, Better Stack y R2 UE · llaves en `ro-llaves` · token de sistema de Meta · sembrar la llave de GHL (T6) · Access, AUD y equipo · dominio y apagar `*.onrender.com`.

**Del coordinador o C0:**
- «Actualizar ahora» en Render debe pedir una vuelta a `ro-ligera` por la API de Render. ⚠️ La ruta de la API está sin comprobar.
- Servir la salud de la tubería en Ajustes.
- Antes de subir el código, revisar 6 ficheros con correos de cliente como ejemplo: `_ESTADO_informe.md`, `fuentes_ficha/personas_cliente.py`, `modulos/catalogo.js`, `modulos/ficha.js`, `fuentes_captacion/generar_captacion.py`, `fuentes_seo/generar_seo.py`.

**De C1:** al cerrar cada módulo en obra, poner `"activo": true` en su paso y cambiar sus rutas fijas por `config.py`. `chat_equipo` y `dinero` leen el llavero directamente.

**⚠️ Sin probar:**
- `base.py` y `estado.py` contra un Postgres real: se comprueba el primer día con `base.py --probar`.
- La construcción de la imagen (no hay Docker en el Mac).
- La subida a R2.
- El SDK de Sentry apuntando a Better Stack.

## Solidez de datos (2-oct, 20:50-21:15) · auditoría 35, puntos A5, A6, M2, M3 y M8

Todo probado **provocando cada fallo sobre copias** (carpeta temporal; red cortada o módulos falsos). No se escribió en Meta, Desk, Google ni GHL, ni en `data/`, `~/Downloads` o `~/RO_HERRAMIENTAS` reales. Copias de lo tocado en el bloc temporal (`solidez/antes/`) y, en herramientas, `externos.py.antes_solidez_2026-10-02` y `ghl_agencia/app.py.antes_solidez_2026-10-02`.

| Fallo | Antes | Ahora |
|---|---|---|
| **Meta caído / token caducado** | `generar_datos.py` salía con 0 y la tubería sellaba «bien». Captación de GHL pasaba de 21 a 0 clientes con dato y no había aviso | La tubería vigila `data/fuentes.json` (`vigilar_fuentes` en `capa_e1`). Una fuente que estaba «bien» y pasa a «sin_conectar» o «rota», o pierde más de la mitad de sus clientes, es un fallo. Entonces restaura el último dato bueno, que conserva su hora (18:05), y lo marca «dato_viejo» con `caida` (desde y motivo) en `fuentes.json` y en cada ficha. Además avisa con «fuente_caida». Sus dependientes sí corren. Si sigue caído en la vuelta siguiente, sigue igual y `caida.desde` no cambia. Una baja a propósito se acepta con `--aceptar-caida <id>`. Por su parte, `anuncios_meta.py` sale con código 3 sin tocar `anuncios.json` y conserva lo anterior de cada cuenta que falla. `generar_captacion.py` no escribe si la Captación cae a 0 (código 3) y marca la fuente «caida» o «con_errores» con `hora_error` |
| **Desk caído** | La Bandeja volvía siempre al panel de las 04:59 | Vuelve al dato bueno **más reciente**: su propia salida anterior si es más nueva que el panel. Recalcula las horas sin contestar, marca «dato_viejo» con la hora del dato y apunta `hora_error`, que la tubería cuenta como fallo de Desk y avisa. Con `--ficheros` (sin red a propósito) no hay error. Zadarma también apunta `hora_error` |
| **`externos.py`** | Sin bloqueo ni escritura atómica, y mezclaba con lo leído al empezar. Un `_error` de Google se daba por bueno | Bloqueo de proceso único en `<salida>/.externos.lock`: si hay otro, sale con 75. Escribe en un temporal, hace fsync y luego `os.replace`. Bajo el bloqueo **relee el fichero actual** justo antes de escribir: con argumentos solo cambia esos clientes, y sin argumentos conserva lo que añaden otros (el `outreach` de Snov). Cada fuente se lee por su lado: si una falla, el resto sigue. Con `_error` (GA y GSC ya lo devuelven en todas sus llamadas), conserva el último dato bueno del **mismo** emparejamiento, con `error`, `hora_error` y `dato_de`. El paso `lector_externos` lleva `errores_de_fuente`. Las rutas salen de `RO_CRUDOS` y `RO_HERRAMIENTAS` |
| **Salida vacía o incompleta** | `{}` se sellaba «bien» | Es un fallo y se restaura: `{}`, null, una lista que se queda sin filas, las `claves_minimas` del paso o un `recuento` que cae más del 50 %. Están puestas en los lectores, `base`, `capa_e1`, `bandeja` y `captacion`. Además, la tubería **restaura antes de cada reintento** (M2) |
| **Llave de GHL que rota** | Solo protegida dentro de la tubería | `app.acceso()` toma un bloqueo de fichero (`ghl_agencia/.llave.lock`) también fuera de la tubería. `llave_ghl.prestar()` toma ese mismo bloqueo y se lo pasa a su paso (`RO_GHL_BLOQUEO_HEREDADO`), para que no se espere a sí mismo. La llave nueva se guarda **antes** de usar el acceso: primero un respaldo atómico 0600 y luego el llavero. Si el llavero falla, `llave()` la lee del respaldo, y el respaldo se borra al guardar bien |
| `pasos.json` | `panel_direccion` restauraba `modulos/panel_direccion_estilo.js` | Quitado de sus salidas |

**Pruebas** (en `despliegue/pruebas_noche.py`, sección 5; solo esta parte: `--solo-solidez`): **37 de 37** casos.
- Tubería: vacío, sin claves, recuento, lista sin filas, Meta caído (sello, hora, marca, 21 clientes, ficha, dependientes, aviso, segunda vuelta) y errores de fuente.
- Bandeja: Desk caído con salida más nueva, con panel más nuevo y con `--ficheros`.
- `anuncios_meta.py` y Captación con Meta caído.
- `externos.py`: 401 de Google, los 4 Search Console sin pisar, `outreach`, sin temporales, vuelta parcial con escritura a mitad y bloqueo con código 75.
- Llave de GHL: 6 procesos a la vez sin perder la llave, un control sin bloqueo que sí la pierde, el llavero que falla y el préstamo dentro y fuera de la tubería.
- `llave_ghl.py prueba-simulada`: bien.

**Vuelta y baterías finales:**
- Vuelta real `--ligero --desde-crudo` (21:07, vuelta 5): **31 pasos bien, 0 fallos**.
- `pruebas_e0.py`: **60/60 TODO BIEN**, contra un servidor propio en 127.0.0.1:8930 con una copia de `local.db`, ya parado.
- `pruebas_coherencia.py`: **0 errores y 0 avisos**.
- `escaner_secretos.py --proyecto`: **limpio**.

**Pendientes cerrados (2-oct, 21:15-21:30, encargo del coordinador):**
- **`~/RO_HERRAMIENTAS/snov/por_cliente.py`** (copia en `.antes_solidez_2026-10-02`): usa el mismo `.externos.lock` que `externos.py`. Espera como mucho `RO_EXTERNOS_ESPERA_S` (600 s) y, si no lo consigue, sale con 75 sin escribir. Bajo el bloqueo relee el fichero actual y escribe con temporal, fsync y `os.replace`. Ruta por `RO_CRUDOS`.
- **`fuentes/generar_datos.py`**: si una fuente que estaba «bien» (o ya marcada caída) sale «sin_conectar» o «rota», o pierde más de la mitad de sus clientes con dato, **no sobrescribe nada**. Marca el último dato bueno «dato_viejo» con `caida` en `fuentes.json` y en las fichas, imprime `FUENTES_CAIDAS […]` y sale con **4**. Las bajas a propósito se aceptan con `--aceptar-caida`. La tubería entiende el 4 (`CODIGO_CAIDA`): no reintenta ni restaura, no sella «bien», avisa y deja correr a los dependientes.
- **Bandeja con Zadarma caído**: vuelve a sus llamadas de la vuelta anterior si son más nuevas que el crudo del panel. Recalcula horas, gravedad y account, y apunta `hora_error`.
- **Reinstalar la llave de GHL a mano**: `pegar.sh instalar` aparta el respaldo pendiente a `.respaldo.viejo` antes de instalar (copia en `.antes_solidez_2026-10-02`). `pegar_llave.sh` **no se toca**: guarda la llave de agencia `ghl_agency_pit`, que no rota ni usa respaldo. Borrar ahí el respaldo podría perder la única copia buena de la llave que rota. Además, `app.py instalar` ya pisa el respaldo con la llave nueva antes de guardarla.
- **Pruebas:**
  - `pruebas_noche.py --solo-solidez`: **44 de 44**. Son 7 casos nuevos: Zadarma, `generar_datos` a mano y en la tubería, Snov con bloqueo y escritura, y `pegar.sh`.
  - Vuelta real `--ligero --desde-crudo` (21:17, vuelta 6): **31 de 31 bien**.
  - `pruebas_coherencia`: 0 errores.
  - `escaner_secretos --proyecto`: limpio.
  - `pruebas_e0` (servidor propio en 127.0.0.1:8930 con copia de `local.db`, ya parado): **59 de 60**. Antes, a las 21:09, había dado 60 de 60. El fallo es «Gustavo (GHL) abre accompany: € en `fuentes.meta`». Sale del texto «techo general de 35 €» de las alertas de Meta, que `P.sin_importes` no quita. Es del recorte de la ficha: `servir.py`, `permisos.py` y `reglas_permisos.json`, que otro carril cambió entre las 21:16 y las 21:18. No sale de los ficheros de este carril.

**Queda (de otros dueños):**
- `captacion.py` no apunta `hora_error` por cliente. Su error se ve en Captación (`cuenta_meta.error`) y la tubería lo avisa cuando es de esa vuelta.
- Si alguien pega a mano el `ghl_app_refresh_token` en el llavero, sin `pegar.sh instalar`, mientras haya un respaldo pendiente, se usaría el respaldo.

## R16b · cabos sueltos (3-oct, madrugada)
- **`despliegue/avisos.py` → `despliegue/avisos_tuberia.py`** (N15): con `despliegue/` el primero en `sys.path` tapaba al `avisos.py` de la raíz y `servir.py`, importado desde la tubería, fallaba con «module 'avisos' has no attribute 'enganchar'». Importaciones cambiadas en `tuberia.py`, `salud_conexiones.py` y `pruebas_noche.py`.
- **Motivo de caída nunca vacío:** `tuberia._por_que()` usa error → error de la lectura directa → nota y, si la fuente no dice nada, el hecho («tenía dato de 28 clientes y ahora de 0; última lectura …»). Lo que llega vacío del generador de E1 (`fuentes/generar_datos.py`, «pasa a «sin_conectar» ()») se rellena en `_motivo_lleno()`; **el arreglo de raíz es del dueño de E1** (misma línea que la tubería).
- **Un aviso por paso** con todas sus fuentes caídas (clave `paso:f1+f2`): con el tope de 3 al día, una caída grande ya no deja 5 de 8 «retenido».
- **Horas (N16):** en `recargas` de local.db la tubería guarda `empezada`/`terminada` en **UTC** «AAAA-MM-DD HH:MM:SS», como `pedida` y como `servir.py` (`avisos_tuberia.a_utc`). El día de los avisos es el de **Madrid** (también en `estado.py`). La base de estado, el registro y la consola van en **hora de Madrid** (`estado.ahora_dt()`), aunque el Mac esté fuera. `RO_HORA_DATOS` sigue en la hora de la máquina porque los generadores apuntan `hora_error` con su `datetime.now()`. Enseñar las recargas en hora de Madrid es de `ajustes.js` (hoy pone «Pedida (UTC)» / «Terminada (UTC)»: ya es verdad para todas las filas nuevas).
- `pruebas_noche.py` arranca su servidor con `--bind 127.0.0.1`; casos nuevos: aviso agrupado y motivo sin «()».
- **`pasos.json · crm` en ligero = `--desde-crudo`** (antes `--sin-vivo`): la vuelta ligera dejaba la Salud del CRM sin leads sin tocar ni citas (0 de 179) hasta la completa; ahora usa la última lectura en vivo de GHL (`fuentes_crm/_privado/ghl_vivo.json`, con su hora).
- Vueltas de prueba (3-oct): 9 (ligera entera, 01:22-02:07 Madrid, ok), 10 (crm), 11 (módulos sin lectores, para que converjan). Tras medianoche, `pruebas_coherencia` deja 1 error de **personas** («no imputan ayer»: `personas_m20` cuenta 0 h el 2-oct con el panel de ClickUp del 2-oct a las 09:16; la verdad usa la definición única de Horas). Es de los dueños de Personas/Verdad, no de la tubería.

## Fase 2 · recarga completa en vivo (3-oct, 02:28-05:36 Madrid)
- **Vuelta 13 `--completo`** (02:53-05:18): 40 pasos, 38 bien; `lector_anuncios_meta` y `captacion` «con errores» (no restaurados): Meta devuelve «An unknown error occurred» en la ventana de 30 días de **Kiosko Box** (1 de 16 cuentas); se queda su dato anterior. Repetido en la vuelta 14 (`--solo` anuncios y dependientes, 05:20): mismo error de Meta. Lectores externos, Snov, captación y hoja de informes no corrieron por horario (`cada_min`): su lectura en vivo es de 01:22-01:42.
- La vuelta 12 se paró a mano (02:53, «interrumpida»): `lector_clickup_equipo` no cabía en 1200 s (tardó 1470 s).
- **Arreglos (copia `.antes_recarga` de cada fichero):** `pasos.json` (timeout de `lector_clickup_equipo` 3600 s y de `nuevos` 1200 s; `personas` depende de `horas`) · `fuentes_redes/generar_redes.py` (faltaba `from pathlib import Path` en `--en-vivo`) · `fuentes_incidencias/generar_incidencias.py` (f-string con comillas anidadas, inválida en Python 3.9) · `fuentes_personas/generar_personas.py` («ayer» = último laborable de Madrid y las horas de ayer de `data/horas/horas.json`, la definición única de la verdad) · `modulos/ajustes.js` (recargas «Pedida/Terminada (Madrid)», convertidas desde UTC) · `fuentes/generar_datos.py` (motivo de caída nunca «()»: `_por_que` como la tubería) · `pruebas_coherencia.py` (V2-C1 acepta `sinTerminal(<var>.que_hacer)`) · `modulos/ficha_equipo.js` (sin `new Date().toISOString()` como «hoy»).
- **Pruebas** (servidor propio 127.0.0.1:9180 sobre copia de `local.db`, ya parado): `pruebas_e0` TODO BIEN · `pruebas_seguridad` TODO BIEN · `pruebas_coherencia` 0 errores, 0 avisos · `probar_ia` 193/0 · `probar_alertas` TODO BIEN · `pruebas_noche --solo-solidez` 105/105 · `escaner_secretos --proyecto` limpio.
- Los pasos nuevos `verificar_envios` y `reconciliar_clickup` (de otro carril, añadidos a las 04:53) **no corrieron** en esta recarga.

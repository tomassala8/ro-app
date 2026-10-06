# App de RO · base común (prototipo local)

**Puesto al día el 3-oct-2026 (06:30).** Prototipo local completo: carcasa, sistema de diseño, permisos en el servidor y los módulos de los 21 puestos con datos reales. **Nada desplegado y nada sale de la app:** envíos, ClickUp, reseñas de Google y acceso a WordPress están programados pero en simulación hasta que Tomás los active. Código en GitHub (privado): repositorio `tomassala8/ro-app` (por SSH), rama `main`, **sin datos** (ver «Qué no se sube»).

## Estado a 3-oct-2026 · el mapa en una pantalla

| Parte | Estado | Dónde se cuenta |
|---|---|---|
| Piezas comunes (`_trabajo.js`, `_deshacer.js`, `_bitacora.js`, `_ir.js`, `_legible.js`, `capaFlotante`, paneles v4 + `dinero_v4.js`, `ayudas.js` con ⌘K) | Hecho | «Piezas comunes» (abajo) y secciones de cada ronda |
| Envíos verificados (`envios.py`, `despliegue/verificar_envios.py`, interruptores) | Hecho, **en simulación** | `_ESTADO_envios.md` · `../46_ENVIOS_VERIFICADOS.md` |
| Sincronía con ClickUp (`sincronia.py`, `despliegue/reconciliar_clickup.py`, copia en la base) | Hecho, **en simulación** | `_ESTADO_sincronia.md` · `../51_SINCRONIA_Y_CHAT.md` |
| Avisos y canales (`avisos.py`, `avisos_programados.py`, 11 reglas) | Hecho; reloj dentro del servidor | `_ESTADO_avisos.md` · `../54_AUTOMATIZACIONES_INVENTARIO.md` |
| Vigía + «Salud del sistema» + `despliegue/copia_seguridad.py` | Hecho; el bucle local lo arranca quien diga Tomás | «Vigía y copias» (abajo) |
| IA con topes (`ia.py`, `ia_gasto.py`: 150 €/mes, 10 €/día, corte a reglas) | Hecho; **sin clave**, hoy gasto 0 € | `_ESTADO_ia.md` · `../52_IA_COSTE_Y_TOPES.md` · `../55_COSTE_IA_POR_DIA.md` |
| Cerebro de respuestas de correo y cerebro de decisiones v2 | Hecho (precalculado y por reglas sin clave) | `_ESTADO_ia.md` · `../49_CEREBRO_RESPUESTAS.md` · `../53_CEREBRO_DECISIONES.md` |
| Modular (ficha del cliente + tablero de webs + 4 reglas de alerta) | Hecho y **conectado** (lectura); acceso de un clic **apagado** | `_ESTADO_modular.md` |
| Hostinger | Hecho y probado con datos inventados; **falta el token** | `_ESTADO_hostinger.md` · `../56_INTEGRACIONES_HOSTINGER_Y_OTRAS.md` |
| Google Business Profile (ficha de Google, reseñas) | **En curso** (otro carril lo está terminando); hoy «pendiente de aprobación» de Google | «Google Business Profile y teléfonos» (abajo) |
| Teléfonos en formato internacional (`telefono.py`, `modulos/_telefono.js`) | **En curso** (otro carril lo está aplicando en pantallas) | «Google Business Profile y teléfonos» (abajo) |
| Baterías de prueba | Hecho | «Baterías de prueba» (abajo) |
| Lo que solo puede hacer Tomás | — | «Lo que solo puede hacer Tomás» (abajo) |

*Origen (2-oct): carcasa, sistema de diseño, capa de permisos y un módulo de ejemplo («En rojo») con datos reales del panel v27 de Mili.*

> ✅ **Desde E0 (2-oct) los permisos se aplican en un servidor local, `servir.py`**, con la misma lógica que irá al Worker de Cloudflare (W1): identidad, «ver como», recorte por persona, 403 para clientes ajenos, rastro imborrable y puerta de secretos. Con `servir.py`, `data/` **no se sirve nunca como fichero**. El modo estático (`python3 -m http.server`) sigue funcionando para desarrollar pantallas, pero ahí el navegador descarga todo y **no protege nada**. Nada se publica: solo en este Mac (127.0.0.1).

---

## Cómo abrirlo

```bash
cd ~/Downloads/APP_RO_ROLES_Y_PERMISOS_2026-10-02/30_APP_PROTOTIPO
python3 build_data.py            # panel v27 + fase 0 (+ respuestas de Mili si existen) → data/*.json (solo lectura)
python3 generar_catalogo.py      # fichas G1-G3 + umbrales firmados → indicadores.json
python3 servir.py --bind 127.0.0.1 --puerto 8770   # y abre http://127.0.0.1:8770 (permisos en el servidor)
                                 # SIEMPRE --bind 127.0.0.1: nunca a la wifi (2-oct se expusieron correos y teléfonos)
python3 pruebas_e0.py            # con servir.py en marcha: pruebas de aceptación de E0
# modo de respaldo, sin permisos de verdad:  python3 -m http.server 8765
```

- Hace falta servidor (los módulos son ES modules y los datos se piden con `fetch`); abrir el fichero con doble clic no funciona.
- Entras como Tomás. `?yo=lucia` entra como otra persona (simula el correo que daría Cloudflare Access).
- **Ver como** (arriba a la derecha, solo Mili y Tomás, regla `ver_como`): los 21 puestos con sus personas (sin las de baja). Es **solo lectura** (el servidor rechaza cualquier escritura) y cada cambio queda en el rastro del servidor con su hora. También desde Sistema › Ajustes › Ver como.
- **⌘K / Ctrl K** o **/** abre el buscador: pantallas del puesto y clientes cuyo detalle puede abrir. Nada más.
- Móvil: menú lateral plegable con el botón «Menú»; tablas que se apilan en tarjetas por debajo de 640 px.

## Estructura

```
30_APP_PROTOTIPO/
├── index.html          carcasa (menú lateral marino con la marca de RO, cabecera, buscador ⌘K, «ver como», paleta)
├── carcasa.js          ola 0: iconos del menú y de ⌘K y avatar, observando lo que pinta app.js (no cambia app.js)
├── estilos.css         tokens (claro siempre, Montserrat; Geist Mono para código) y clases de componentes
├── componentes.js      componentes reutilizables, documentados en el propio fichero
├── reglas_permisos.json  (E0) LA matriz de permisos: 21 puestos, sillas, equivalencias, reglas por tipo de dato
├── permisos.js         intérprete de reglas_permisos.json en el navegador (y en el Worker con W1)
├── permisos.py         (E0) el mismo intérprete en Python + recortar() para servir.py (paridad comprobada)
├── datos.js            sesión de servir.py (/api/sesion) o, sin servidor, data/*.json + recortar()
├── app.js              identidad, «ver como», menú por puesto, router, ctx, cmd+K, rastro
├── ayudas.js           (E0, R15) buscador que busca dentro y hace cosas, contadores y «Mis clientes» del menú,
│                       «Algo va mal / Tengo una idea» y atajos; se carga con el navegador libre
├── build_data.py       panel v27 + 20_FASE0_DATOS (+ respuestas_mili.json) → data/*.json
├── generar_catalogo.py (E0) fichas G1-G3 + tabla U → indicadores.json (228 + 23 de fase 2)
├── servir.py           (E0) servidor local 127.0.0.1:8770: identidad, recorte, 403, rastro, acciones, Ajustes
├── schema_v2.sql       (E0) base local.db y D1 (NO desplegada): personas, asignaciones, registro, historial,
│                       acciones, incidencias, decisiones, docs; rastro imborrable por disparadores
├── local.db            (E0) la base local (la crea servir.py); no se sirve
├── escaner_secretos.py (E0) puerta de secretos (R16) sobre data/
├── foto_diaria.py      (E0) historia/AAAA-MM-DD/ + cambios.json (lo que ha cambiado desde la última foto)
├── pruebas_e0.py       (E0) pruebas de aceptación contra servir.py
├── data/               clientes, alarmas, logos, personas, asignaciones, para_confirmar, ids_clientes, meta
│   ├── clientes/       un fichero por cliente (E1; no lo toca E0)
│   └── <carpeta>/_privado/  datos completos de leads: solo servidor, solo con /api/ver_dato y rastro
├── historia/           fotos diarias (no se sirve)
└── modulos/
    ├── indice.js       M1-M22: metadatos, grupo, puestos_que_lo_ven, fase, estado
    ├── en_rojo.js      M2 «En rojo» (hecho: verdad única + atajos)
    ├── ajustes.js      (E0) M22 Personas · Asignaciones · Para confirmar · Ver como
    ├── indicadores.js  (E0) catálogo de indicadores (Mili y Tomás)
    ├── rastro.js       (E0) M21 Decisiones y rastro
    └── catalogo.js     catálogo vivo de componentes (solo Dirección)
```

## Contrato de un módulo

Un módulo es **un fichero en `modulos/`** que exporta por defecto:

```js
export default {
  id: 'bandeja',                       // = ruta #/bandeja y clave en modulos/indice.js
  titulo: 'Bandeja',
  grupo: 'Hoy',                        // uno de GRUPOS en indice.js
  puestos_que_lo_ven: {                // puesto → 'todo' (●) | 'suyo' (◐) | 'resumen' (○)
    '*': 'suyo', direccion: 'todo',    // '*' = el resto de puestos; null = excluido
  },
  render(contenedor, ctx) { ... },     // puede ser async; pinta dentro de contenedor
};
```

Para darlo de alta: en `modulos/indice.js`, en su entrada, `fichero: './bandeja.js'` y `estado: 'hecho'`. El menú, el buscador y la ruta salen solos.

**Lo que recibe `ctx`:**

| Campo | Qué es |
|---|---|
| `persona` | `{ id, nombre, alias, puestos[] }` de quien se está viendo (real o «ver como») |
| `real` | quien está delante de verdad |
| `puestos` | objetos de `PUESTOS` de esa persona |
| `nivel` | `'todo' \| 'suyo' \| 'resumen'` para este módulo |
| `soloLectura` | `true` en «ver como»: **no escribir nunca** (pásalo a `botonConfirmar`) |
| `clientes` | todos los clientes **ya recortados**: lo común (nombre, logo, responsable, salud) para todos; `detalle: true` y campos de detalle solo si los puede ver; `cuota` y `publicidad_30d` son `undefined` si no le tocan |
| `clientesVisibles` | los que puede abrir (`detalle: true`) |
| `carteraIds` | `Set` con los clientes asignados a su silla (más suplencias vigentes) |
| `ambito` | `'todos' \| 'disciplina' \| 'cartera' \| 'tareas' \| 'ninguno'` |
| `datos` | `{ alarmas, personas, meta }` ya recortados; `meta.fuentes` trae la frescura por fuente |
| `ver(dato)` | la regla de permisos para preguntar caso a caso (ver abajo) |
| `params` | trozos de la ruta tras el id: `#/en-rojo/gac` → `['gac']` |
| `navegar(ruta)` | `ctx.navegar('en-rojo/gac')` |
| `rastro(ev)` | apunta una acción `{ accion, objeto, detalle }` (en producción, tabla `registro`) |
| `titulo(t, sub)` | cambia el título y subtítulo de la cabecera |
| **Añadido en E0** (compatible hacia atrás: nada de lo anterior cambia) | |
| `servidor` | `true` si los datos vienen recortados de `servir.py`; `false` en modo estático |
| `carteraPorSilla` | `{ account: Set, trafficker: Set, crm: Set, … }` (la cartera por silla) |
| `datos.asignaciones` | las filas de asignaciones de la persona vista |
| `indicador(id)` | ficha del catálogo (`indicadores.json`): nombre, fórmula, umbral, `umbral_origen`, `decision`, `medible` (`hoy`/`medias`/`no`), `medible_porque`, fuente, frecuencia. `null` si no es de su puesto (salvo Mili y Tomás, que reciben todos) |
| `indicadores()` | lista de los indicadores que le tocan |
| `api(ruta, { metodo, cuerpo })` | llama a `servir.py` con la identidad de la sesión (lanza error con el motivo si 403) |
| `datosModulo(nombre)` | `data/<nombre>.json` **recortado por el servidor** (o el fichero tal cual sin servidor). Úsalo en vez de `fetch('data/…')`: desde la ronda 14 tiene memoria por persona (lo ya bajado sale al momento y se comprueba detrás con ETag; si cambia, la pantalla se repinta sola). Cada llamada devuelve un objeto nuevo: puedes modificarlo |
| `verDato({ almacen, ref, campo, cliente_id })` | «Ver datos» de un lead (D-88): devuelve `{ valor }` desde `data/<…>/_privado/<almacen>.json` solo si lo trabaja, y deja rastro |
| `accion({ herramienta, tipo, objeto, cliente_id, texto, vista_previa })` | botón: deja la acción en la cola `acciones` con estado «simulada» (nunca llama a una API externa). En «ver como», error |
| **V2-E (3-oct) · fechas comunes** | ver «Fechas: una sola vara» abajo |
| `hoy` | `'AAAA-MM-DD'` de **hoy en Madrid** (calendario de la agencia), el mismo en todas las pantallas. Es un **texto**, no una función |
| `fechas` | `hoy()`, `ayer()`, `manana()`, `dia(t)`, `diasDesde(t)`, `esHoy(t)`, `esAyer(t)`, `vencida(t)`, `venceHoy(t)`, `semana()`, `estaSemana(t)`, `laborable(t)`, `ultimoLaborable()`, `diaSemana(t)`, `relativo(t)`, `hora(t)`, `plazo(t)` («mañana a las 10:00», en punto), `diaDatos(generado)`, `antiguedad(horas)` |
| `diaDatos()` | `{ dia, esHoy, texto }` del día de los datos de la sesión (`meta.generado`): si `!esHoy`, escribe `texto` («datos de ayer (vie 2)») |
| `fechasDe(zona)` | lo mismo con la zona de una persona (`ctx.zona(id)`), **solo** para enseñarle su hora; nunca para decidir si algo vence |
| `plural(n, 'cita')` | «1 cita» / «3 citas» (`fmt.plural`); nunca «1 citas» ni «cita(s)» |

**Datos de un módulo (contrato del servidor, E0).** Si tu módulo genera `data/<carpeta>/<fichero>.json`, **dalo de alta en `reglas_permisos.json → datos_de_modulo`** con el módulo (o módulos) que da derecho a leerlo; si no, no se sirve. `servir.py` solo lo manda a quien ve ese módulo (según `puestos_que_lo_ven`) y lo sirve **recortado** en `/api/modulo/<carpeta>/<fichero>` (y también si haces `fetch('data/<carpeta>/<fichero>.json')`, gracias a la cookie de identidad del prototipo): en cualquier lista, las filas con `cliente_id` solo llegan si la persona ve ese cliente; con `persona_id`, solo si puede ver las horas de esa persona; con `setter`, solo las suyas (salvo dirección, ventas de RO, jefa de CRM y operaciones). Y a cualquier profundidad se quitan las claves de dinero que no le tocan (`cuota*`, `facturas*`, `gasto*`, `coste*`, `cpl*`, `inversion*`) y `telefono`/`nombre_lead`/`correo_lead`. Lo que no cabe en esa regla general, pídeselo a E0. **Nunca** pongas datos completos de leads fuera de una carpeta `_privado/`: allí no se sirven en bloque, solo con `ctx.verDato()`, y cada almacén se declara en `reglas_permisos.json → almacenes_privados` (regla y módulo). Las acciones de un módulo se leen con `ctx.api('acciones?modulo=<id>')`.

**Ronda 4 (E0):** `datos_de_modulo` admite `{ "puestos": [...] }` (fichero solo para esos puestos) y `"filas_lead": [listas]` (con nivel «resumen» no viajan filas de leads). Decisiones en vivo: `GET/POST /api/decisiones` (`operacion: nueva | responder`). La carcasa solo importa módulos con `estado: 'hecho'`.

**Componentes nuevos (E0, ronda 3):** `barraProgreso()`, `embudoBarras()` y `ventanas()` (de Captación). `ctx.veModulo(id)` dice si el puesto ve una pantalla. «Actualizar ahora» (cabecera, Mili y Tomás) usa la cola de `servir.py` y los pasos de `recarga.json`; los avisos de fuentes están en Ajustes › Avisos y recargas. La tipografía es **Montserrat** (decisión D-P01; la R12 del plan decía Geist).

**Componentes nuevos (E0):** `fichaCatalogo(ctx.indicador(id), { valor, unidad, estado, tendencia, frescura, prueba, parcial })` pinta la tarjeta con el umbral firmado, el sello de medición y «¿Qué es?» (fórmula, umbral, origen, fuente). Si el catálogo dice «todavía no», **no pinta número** (va a Fase 2). `pieFase2(indicadores)` lista al pie lo que todavía no se mide.

**Reglas del módulo:** cliente primero (D-26); cada cifra con su sello «se mide hoy / a medias / todavía no» y su frescura; del número a la prueba en un clic; ninguna lectura de `data/` directa (solo `ctx`); nada de `alert/confirm/prompt`; todo lo que se pulsa es `<button>` o `<a>`; solo tokens de `estilos.css`; probar con «ver como» de 3 puestos distintos.

## Seguridad (E0 ronda 6, auditoría 27) · lo que tiene que saber quien construye

- **Identidad:** sin `?yo=`, cabecera o galleta → 401 y «¿Quién eres?» (solo en local). Solo entran personas `activo`.
- **POST:** siempre por `ctx.api` / `ctx.accion` / `ctx.verDato` (llevan `X-RO-App: 1` y JSON). Un `fetch` propio sin esa cabecera da 403.
- **«Ver como»:** el servidor da el mínimo entre la persona real y la vista; lo leído queda en el rastro.
- **Acciones:** solo los tipos de `reglas_permisos.json → acciones_permitidas` (añade el tuyo ahí). `decidir` solo el destinatario; `responder` exige cliente de su cartera.
- **Rastro desde el navegador:** solo las acciones de `rastro_navegador`; lo demás entra como `nav:<accion>`.
- **Datos privados:** el cliente de un dato lo decide el servidor (`cliente` en `almacenes_privados`). `dueno: "fichero"` + tipo `solo_lo_tuyo` = solo su dueño.
- **`datos_de_modulo`:** además de `modulos`, `puestos`, `solo_todo_sin_cliente`, `filas_lead`, `excluir_puestos`: `solo_propio` (fichero `p_<id>`), `regla_persona`, `filas_solo_tipo`, `textos_sin_importes_salvo`, `claves_solo_tipo` y `resumen`. Admite patrones (`chat_equipo/p_*`). Las filas con `miembros` solo llegan a sus miembros.
- **Enlaces:** `h()` solo admite http, https, mailto, tel, sip, anclas y rutas relativas.
- **Cachés:** nada de correos o teléfonos de leads o contactos fuera de `_privado/` (también en `fuentes_*/`). `python3 escaner_secretos.py --proyecto` lo comprueba.
- **Pruebas:** `python3 pruebas_seguridad.py` (servidor propio, copia de la base) reproduce cada fallo de la auditoría.

## Una sola verdad por cliente (E0 ronda 5) · qué campo usar en cada caso

`fuentes_verdad/generar_verdad.py` → `data/verdad/clientes.json` (y `equipo.json`). Desde un módulo: **`ctx.verdad(clienteId)`** (detalle si puede abrir el cliente; si no, su línea común), `ctx.verdadComun()` (la lista común de los 68, sin cifras) y `ctx.definiciones()`. `pruebas_coherencia.py` compara cada módulo con la verdad: los módulos de `ADOPTADOS` fallan si no coinciden; el resto sale como aviso para su dueño.

| Si necesitas… | Usa | Definición |
|---|---|---|
| Account del cliente | `verdad.account` (y `sin_account`) | El principal vigente de asignaciones. Si no hay, `null`: nunca el de la Cartera ni el del CRM |
| Equipo por silla | `verdad.equipo` | Asignaciones vigentes, responsable primero |
| ¿Es nuevo? | `verdad.nuevo`, `dia_alta`, `alta` | Está en Clientes nuevos (alta en los últimos 90 días). La misma lista en todas las pantallas |
| Encendido de un alta | `verdad.encendido` = `{dia, estado}` | `en_plazo` (≤ día 10) · `en_limite` (11-12) · `tarde` · `sin_encender_fuera_de_plazo` · `pendiente_en_plazo` |
| Campaña activa | `verdad.campana_activa` | Meta activa (Captación) |
| Fuga de integración | `verdad.fuga_integracion` | **grave**: ≥ 10 leads de Meta en 7 días y llega a GoHighLevel menos de la mitad · **leve**: menos del 80 % |
| Sin reunión | `verdad.sin_reunion_mes_pasado` | Ninguna reunión el mes pasado en CRM, Fathom y Zoom (salvo exentos) |
| Bloqueos | `verdad.bloqueos` (`tareas`, `dias_max`) y `bloqueo_callado` | Tareas en «bloqueado»; «callado» = la más antigua > 5 días. La alarma del panel «Bloqueo sin resolver» es otra regla (> 2 días): llamarlo así |
| Gravedad del cliente | `verdad.gravedad` + `motivos` | **crítico** · **atención** · **bien** (reglas en el propio fichero). Una fuga grave nunca es «bien» |
| Salud 0-100 | `verdad.salud` | Provisional D-02: 40 resultados + 30 atención + 30 arranque. Sello «a medias» |
| No imputan ayer | `data/verdad/equipo.json` | Activos que imputan (sin dudosos, bajas ni setters), 0 h el último día laborable |
| Nombre de una persona | `ctx.nombre(id)` | El nombre corto de personas.json. Nunca el id («mili») ni un alias escrito a mano |

**Regla de textos (ronda 5):** en pantalla, nada de códigos de obra (D-xx, G2, W3, C-D3, E10…), nombres de fichero, ⭐ ni ⚠️. `limpiaTexto()` (componentes.js) los quita y ya la aplican `tile`, `fichaIndicador`, `avisoParcial`, `panel`, `selloMedible` y `estadoVacio`; lo que va entre «» (texto del cliente) no se toca. La referencia, si hace falta, en `deDondeSale(texto)` (plegado). Iconos: solo los del sistema (`icono()`).

**Paginación:** `tablaDensa` y `tablaApilable` enseñan 50 filas y «Ver 50 más» (`porPagina`, 0 = sin paginar).

**Sueldos (regla nueva de Tomás, 2-oct):** entran en la app solo para dirección y RRHH. Almacén `data/sueldos/_privado/sueldos.json` (`fuentes_sueldos/generar_sueldos.py`; la hoja «Cuentas bancarias» no se abre nunca), solo con `ctx.verDato({ almacen: 'sueldos/_privado/sueldos', ref: <persona_id>, campo: 'meses' | 'proyeccion' })` y con rastro. El escáner para cualquier importe de sueldo fuera de ese almacén.

## Componentes (`componentes.js`)

Todos devuelven un `HTMLElement` (nunca HTML en texto, para que un asunto de correo no inyecte código). Ejemplos en vivo: entra como Tomás → Sistema → **Componentes**.

| Componente | Para qué |
|---|---|
| `fichaIndicador({ titulo, valor, unidad, estado, tendencia, umbral, medible, frescura, prueba })` | KPI con verde/ámbar/rojo, tendencia, sello de medible, frescura y clic a la prueba |
| `tarjetaCliente({ nombre, logo, salud, motivo, extra, onAbrir })` | logo, salud 0-100 y motivo |
| `listaLoPrimero(items, { vacio })` | «Lo primero hoy»: motivo + detalle + botones (máx. 7) |
| `tablaDensa({ columnas, filas, filtros, buscar, orden, alPulsar, puedePulsar, vacio })` | tabla con orden, filtros y búsqueda; filas pulsables con teclado; en móvil se apila |
| `chipEstado(estado, texto)` | verde · ámbar · rojo · gris · azul |
| `selloMedible('hoy' \| 'medias' \| 'no', detalle)` | sello de medible |
| `frescura({ fuente, edad_h \| fecha, estado })` | «Desk · hace 4,1 h», en ámbar si va con retraso |
| `lineaTiempo([{ fecha, titulo, detalle, estado }])` | historia de un cliente o una persona |
| `graficoSerie({ puntos, titulo, umbral })` | línea + área en SVG, sin librerías; con menos de 2 puntos, estado vacío |
| `estadoVacio({ titulo, porque, que_hacer, accion, celebrar })` | por qué está vacío y qué hacer; celebra si es buena noticia |
| `botonConfirmar({ texto, pregunta, confirmar, alConfirmar, peligro, soloLectura })` | confirmación en la propia página (Sí/No, Esc), con resultado o error |
| `avisoParcial(texto, { tipo, titulo })` | aviso de dato parcial o nota informativa |
| `candado(texto)`, `saludCliente(n)`, `logoCliente(c)`, `panel(...)`, `h(...)`, `fmt`, `semaforo()` | utilidades |

Ampliaciones compatibles de la ola 0 (las llamadas antiguas siguen igual): `fichaIndicador({ …, icono })` añade el cuadrado de icono; `estadoVacio({ …, icono, quien })`; `panel({ …, icono })` pone el icono en azul junto al título; en `listaLoPrimero`, cada elemento admite `icono` en lugar del número; `avisoParcial` lleva icono.

### Sistema visual · ola 0 (2-oct-2026) — úsalo en todos los módulos nuevos

Referencia: la ficha de cliente v3 que Tomás aprobó (`~/Downloads/HERRAMIENTA_RO_2026-10-02/plantilla.html`) y `herramienta_ro_diseno.html`. Comparación en `capturas/ola0/` (`referencia_ficha_v3_1440.png` frente a `ola0_*`).

**Reglas de pintura** (sección 3 del `16_SUPERPROMPT_PINTURA_TOTAL.md`): siempre en claro · color solo con significado (verde va bien, ámbar vigila, rojo actúa, gris sin dato; el resto en marino y grises) · iconos en todo (menú, pestañas, cabeceras de panel, indicadores, botones y vacíos) · arriba lo de cada día, abajo lo de cada semana o mes (máximo 7 bloques en «Mi día») · nunca una caja en blanco · móvil a 390 px sin desplazamiento horizontal · la hora del dato siempre a la vista.

| Componente | Para qué |
|---|---|
| `icono(nombre, { clase: 's' \| 'l', titulo })` | el único juego de iconos (77, trazo 1,8 px; base: objeto `P` de la ficha v3). Lista completa en `ICONOS` y en el catálogo vivo. Sin `titulo` es decorativo (`aria-hidden`) |
| `ICONO_MODULO`, `ICONO_GRUPO` | icono de cada pantalla del menú y de cada grupo. **Si creas un módulo nuevo, añade aquí su icono** (o pídeselo a E0) |
| `tile({ icono, etiqueta, valor, unidad, estado, comparacion, contexto, medible, medibleDetalle, frescura, alPulsar \| href, activo, ir })` | el indicador de la ficha v3: icono en cuadrado suave según estado + etiqueta + cifra grande + ▲/▼ frente al periodo anterior (`comparacion: { delta, pct, unidad, texto, mejorSi: 'bajo' }` invierte el color cuando bajar es bueno) + una línea de contexto. Pulsable: lleva a su detalle. Con `activo` es un interruptor (patrón Analytics: el tile elige la métrica del gráfico). `tiles([...])` hace la rejilla (2 columnas en móvil). `variacion(actual, anterior)` calcula el %. Para indicadores del catálogo con «¿Qué es?» sigue `fichaCatalogo` |
| `chipsFiltro({ opciones: [{ valor, texto, cuenta, cuentaEstado, icono }], valor, multiple, clave, etiqueta, alCambiar })` | filtros como chips con su contador (vistas de Zoho Desk). Con `clave` **se quedan** al recargar o volver. «Todos» = opción con `valor: ''`. Valor inicial: `el.valor()` |
| `selectorPeriodo({ opciones, valor, clave, alCambiar })` | un periodo único arriba con su comparación («30 días · frente a los 30 anteriores»). `el.valor()` |
| `pestanas({ pestanas: [{ id, texto, icono, cuenta, cuentaEstado }], activa, clave, pintar(id, contenedor), alCambiar })` | pestañas con icono y contador rojo, teclado ← → Inicio Fin; con `pintar` el cambio es instantáneo; con `clave` recuerda la pestaña. `el.activa()`, `el.elegir(id)` |
| `selectorCliente({ clientes, actual, alElegir, detalle, insignia, etiqueta })` | el de la ficha v3: logo, nombre y account; buscador por nombre o account; ↑ ↓ Intro Esc. **Pásale solo `ctx.clientesVisibles`.** Al cambiar de cliente, quédate en la misma pestaña |
| `vacio({ icono, titulo, texto, quien, accion, tono: 'neutro' \| 'celebrar' \| 'aviso', borde })` | estado vacío grande: icono + frase + **quién lo arregla**. Para huecos de pestañas y paneles («sin dato: falta la cuenta de Meta»). `estadoVacio` queda para el formato compacto |
| `tablaApilable({ columnas, filas, alPulsar, puedePulsar, etiquetaFila, vacio, controles })` | tabla sencilla que en móvil se apila en tarjetas (`principal: true` hace de título). Con `controles`, `buscar` o `filtros` es `tablaDensa` |
| `botonesContacto({ nombre, telefono, correo, modo: 'lista' \| 'cabecera', whatsapp, fuente })` | lo del portal de clientes: llamar (`sip:…@sip.zadarma.com`, app de Zadarma), WhatsApp (`wa.me`), correo (`mailto:`) y copiar. `cabecera` = «Llamar a Ana» + WhatsApp + Correo. El clic directo con «callback» llega en W1 y solo cambia este componente. **El módulo decide con `ctx.ver` si puede enseñar el teléfono** (nunca datos de leads sin enmascarar) |
| `normalizarTelefono(t)`, `copiar(texto, que)`, `avisoFlotante(texto)` | teléfono a +34 · copiar al portapapeles con aviso (nunca contraseñas ni claves, R10) · aviso breve abajo |
| `barraEtapas(etapas?, actual)` | Firma → Arranque · 14 días → Optimización · día 90 → Cliente consolidado (las de la ficha v3 por defecto) |
| `listaConIcono([{ icono, texto, extra, href, estado }])` | filas con icono («últimos movimientos», accesos, correos) |
| `marcaRO()`, `iniciales(nombre)` | logo de RO en blanco para fondo marino · iniciales para avatares |

**Clases útiles** (solo tokens): `tiles`, `ico-c` (+ `verde`/`ambar`/`rojo`/`gris`, `s`), `av` / `av s` (avatar), `meta-linea` (datos con icono bajo un título), `detalle-cab` (cabecera de registro como la de la ficha v3), `logo-cli xl`, `bt` / `bt pri` / `bt mini`, `titulo-seccion`. Botón con icono: `h('a', { class: 'bt' }, icono('ext'), 'Abrir en ClickUp')`.

**Carcasa (ola 0).** Menú lateral marino con la marca de RO, grupos en mayúscula espaciada, activo en `#3040b5`, icono por pantalla y un punto hueco para las pantallas previstas (leyenda al pie). Barra superior con buscador ⌘K (también `/`), «ver como» y avatar. Los iconos del menú y de ⌘K los pone `carcasa.js` observando lo que pinta `app.js`, para no tocar `app.js` mientras E0 trabaja en él; si un día `app.js` pinta el icono, `carcasa.js` no lo duplica. Tipografía: Montserrat (la de la web de RO y la ficha v3), en lugar de Geist; ver `dudas_pintura.md`.

**Comprobación ola 0 (2-oct, Chrome sin cabeza, `python3 -m http.server`):** `?yo=tomas`, `?yo=lucia`, `?yo=camilo` a 1440 y 390 px sin errores de consola (solo el 404 esperado de `/api/sesion` en modo sin servidor) y sin desplazamiento horizontal; 16 pruebas de teclado y clic pasadas: iconos en las 25 entradas del menú, ⌘K con iconos y Intro, selector de cliente con teclado y Esc, chips que se quedan al recargar, pestañas con flechas, enlaces de llamar/WhatsApp/correo, menú móvil con foco y Esc.

## Permisos (`permisos.js`)

Tres llaves del 00: **puesto** (qué pantallas: `puestos_que_lo_ven`) × **cartera** (qué clientes: tabla `asignaciones`, con suplencias que caducan solas) × **sensibilidad** (`ver()`).

**Desde E0 las reglas viven en `reglas_permisos.json`** (D-10, D-80 a D-92), que interpretan igual `permisos.js` (navegador y Worker) y `permisos.py` (servir.py). La paridad está comprobada: 14.400 casos (40 personas × 24 tipos × 5 clientes × 3 personas) dan la misma huella SHA-256 en los dos (`pruebas_e0.py` imprime la de Python). Cambios de contrato, todos compatibles: `cuota` e `inversion` del account o trafficker miran la cartera **de su silla** (`carteraPorSilla`); una suplencia sin fecha de fin ya no da cartera; tipos nuevos `horas_cliente` (D-84), `rendimiento_pieza` (D-82), `responder_cliente` (D-91), `ver_como`, `ajustes_editar`, `catalogo_indicadores` y `rastro_todo`; el jefe se reconoce también por el campo `jefe` de la persona.

`ver(persona, { tipo, cliente_id?, persona_id? })` → `{ ok, nivel: 'completo'|'enmascarado'|'resumen'|'no', motivo }`:

| Tipo | Regla (00 §3, D-80 a D-92) |
|---|---|
| `sueldo`, `contrasena` | **Nunca**, para nadie |
| `cliente_lista` | Todos (D-90: lista en rojo con motivo y responsable) |
| `cliente_detalle` | Ámbito «todos» o «disciplina», o cliente en su cartera |
| `cuota` | Dirección, operaciones, proyectos, administración y el account de ese cliente |
| `inversion` | Dirección, operaciones, jefa de publicidad, y account o trafficker del cliente |
| `rentabilidad_cliente` | Dirección y operaciones (31,47 €/h, sin caja ni beneficio · D-85) |
| `cobros`, `caja` | Dirección y administración (D-86) |
| `dinero_empresa` | Solo Tomás |
| `lead` | Siempre enmascarado; quien lo trabaja puede desenmascarar con un clic que queda en el rastro (D-88) |
| `horas_persona`, `notas_persona`, `alarma_persona` | La persona, su jefe, operaciones, RRHH y dirección |
| `comparar_personas` | Jefes, operaciones, RRHH y dirección; setters, solo su marcador (D-83) |
| `grabacion` | Participantes, su jefe y dirección |
| `horas_cliente` | Quien lleva el cliente, sus jefas, operaciones y dirección; RRHH en resumen (D-84) |
| `rendimiento_pieza` | Publicidad y quien lleva el cliente; producción en índice, sin euros (D-82) |
| `responder_cliente` | Su account, las jefas, operaciones y dirección (D-91) |
| `ver_como`, `ajustes_editar`, `catalogo_indicadores` | Mili y Tomás |
| `rastro_todo` | Tomás (cada uno ve el suyo) |
| cualquier otro | **No** (por defecto se niega) |

## Datos (`build_data.py`)

- Lee `~/Downloads/PANEL_OPERACIONES_2026-10-01/build/datos.json` (+ `portal_logos.json`) y escribe 66 clientes, 152 alarmas (120 de cliente, 32 de persona), 59 logos.
- **Fuera:** contactos, teléfonos, correos (se sanean también dentro de los textos y el script falla si queda alguno), contraseñas, detalle de tareas y reuniones.
- **Salud 0-100 provisional** = 100 − riesgo del panel v27 (`build.py` 233-251). La D-02 está firmada (40 puntos para resultados del cliente, horas fuera) pero sin construir: sale con sello «a medias».
- **Personas y asignaciones (E0):** salen de `20_FASE0_DATOS/` (40 personas, 30 activas; 372 asignaciones en 7 sillas con fuente y confianza). Los puestos del organigrama se traducen a los 21 de la app con `equivalencias_fase0` de `reglas_permisos.json` (soporte → account, crm → especialista_ghl, copy/diseño/vídeo/UX → producción, seo → seo + ficha_google, setter → setters; Tomás suma finanzas de dirección y ventas de RO). Los ids del portal se traducen a los de la app con `ids.fase0` de E1 (`data/ids_clientes.json`). Entran Jenasa y Think Value (están en el portal y no en el panel): 68 clientes.
- **Respuestas de Mili:** si existe `20_FASE0_DATOS/respuestas_mili.json` (formato en `respuestas_mili.ejemplo.json`), se aplican: la asignación sustituida se cierra con fecha, la confirmada pasa a «confirmada», la persona cambia de estado o de puesto. También se pueden contestar en Ajustes › Para confirmar (quedan en local.db y se exportan en ese mismo formato en `/api/respuestas_mili`).
- Cada cliente lleva `equipo` (silla → personas), `servicios` y, si no tiene account, `sin_account` («mantenimiento sin account» o «sin account · para confirmar (Axx)»).
- Las jefas de disciplina (publicidad, SEO, CRM) ven hoy todos los clientes porque no existe el dato «servicio contratado por cliente»; cuando exista, se filtra por disciplina.

## Módulos previstos (00 §2)

| # | Módulo | Fase | Estado |
|---|---|---|---|
| **M1** | **Mi día** | 1 | **hecho** · `mi_dia.js` + `mi_dia_bloques.js`, ruta `#/mi-dia/<puesto>`: inicio de los 21 puestos. Orquestador: no calcula nada propio, lee los datos ya recortados de los demás módulos (`ctx.datosModulo`). Arriba saludo, «el número que manda» del puesto (catálogo de E0, umbral y «¿Qué es?») y «Lo primero hoy» (máx. 3; lo marcado «Pedido» vuelve arriba a las 48 h con «Toca escalarlo» y, si ya no sale, cuenta como resuelto); debajo, tiles y hasta 7 bloques por puesto (máx. 5 filas, motivo, botón a su pantalla, frescura y sello de medición; vacío «llega con <módulo>» si el dato no existe). Tomás: cambios desde ayer y decisiones 48 h; Mili: su ronda (rol_mili) y mapa de control por persona. Ronda 19:00: «Mis alertas» (N4) con Lo tengo/Resuelta/No aplica, copiloto IA, cumpleaños y aniversarios, correos de `bandeja/por_cliente.json`, beneficio ene-ago y cuota en tres cifras, sin hoja de estilos propia (guía 30). Configuración por puesto en `data/mi_dia/config.json`; `fuentes_mi_dia/generar_mi_dia.py` → `data/mi_dia/cambios.json` (solo dirección), `ronda_mili.json` y el resumen por persona `p_<id>.json` para abrir en un viaje (`resumen_mi_dia.py`, auditoría 37); prueba y capturas con `fuentes_mi_dia/capturar_mi_dia.py`. Ver `_ESTADO_mi_dia.md` |
| **M2** | **En rojo** | 1 | **hecho** · ronda de arreglos 2-oct: pinta la verdad única (`ctx.verdadComun()` / `ctx.verdad(id)`: crítico, atención o bien, motivo y account), chips de gravedad (crítico por defecto), «Abrir la ficha» y «Abrir en …» desde `data/en_rojo/atajos.json` (`fuentes_en_rojo/generar_atajos.py`: portal, captación, CRM, alarmas de Desk y Cartera). Estado en `_ESTADO_en_rojo.md` |
| **M3** | **Bandeja** | 1 | **hecho** · `bandeja.js`: correos de clientes sin contestar (Desk en vivo con `zh.py`, «pendiente» y horas L-V del panel v27; ruido fuera con `filtro_ruido.py`), llamadas sin devolver (Zadarma en vivo con `zd.py`), quejas arriba, por account y día; contestar con firma, nota, asignar, cerrar y «no aplica» a la cola simulada; triaje sin agente (`triaje_desk.json`); hueco WhatsApp W6. Datos: `fuentes_bandeja/generar_bandeja.py` → `data/bandeja/bandeja.json`. Ver `_ESTADO_bandeja.md` |
| **M4** | **Ficha del cliente** | 1 | **hecho** · `ficha.js`, ruta `#/ficha/<cliente>/<pestaña>`, con migas. Pestañas ordenadas por puesto, cabecera con «Llamar a…»/WhatsApp/correo y «Abrir en» (ClickUp, Drive, Meta, Analytics, Search Console, GoHighLevel, Metricool, SE Ranking y Desk). Periodo de 7 días por defecto. Account, equipo, gravedad y salud de la verdad única. Cuota de la fuente única (Airtable, como Dinero por cliente). Correos sin contestar = copia de la Bandeja. Contactos agrupados por persona con su cargo y su fuente (`fuentes_ficha/agenda_md.py`, `personas_cliente.py` y `roles_contactos.py`, en almacén privado, solo su account, operaciones y dirección). Administración ve solo contrato y rastro; producción, una ficha básica. Pestaña «Informes» con el histórico mes a mes (hoja de Zoho, seguimiento de M13, Looker e informe de la app). Datos: `data/clientes/<id>.json` y `fuentes_ficha/generar_ficha.py` → `data/ficha/{portal,web,correos,basica,informes}.json` + `_privado/{contactos,chat}.json`. Ver `_ESTADO_ficha.md` |
| **M5** | **Informe del cliente (sustituye a Looker)** · `modulos/informe.js` · 13 bloques con selector de 6 periodos y comparación (anterior / año anterior), sellos y avisos de fuente, análisis del mes firmado (cola `acciones`) y comparador de paridad de los 22 Looker. Datos: `fuentes_informe/generar_informe.py` → `data/informe/` (GA4 y Search Console en vivo con gg.py; Meta en vivo con mt.py; Snov.io con sv.py; SE Ranking por el conector, `_cache/seranking/`; Google Ads, muestra sellada de `14`; embudo GHL de E1). Estado en `_ESTADO_informe.md` | 3 | **hecho** |
| **M6** | **Captación** | 2 | **hecho** (`modulos/captacion.js`): la Torre de Control dentro de la app (T1-T13 + M1-M9), por trafficker, Valeria y tarjeta por cliente. Datos: `data/captacion/captacion.json` ← `fuentes_captacion/generar_captacion.py` (captacion.json de Meta + GHL, `anuncios_meta.py` para anuncios, Google Ads = muestra manual de septiembre de `14_…`, foto de la Torre del 17-sep, asignaciones de E0). Ver `_ESTADO_captacion.md` |
| **M7** | **Salud del CRM** | 2 | **hecho** (`modulos/crm.js`, ruta `#/salud-crm` y `#/salud-crm/<subcuenta>`): las 66 subcuentas de GHL con estado verde/vigilar/rojo y motivo, % en verde (número de Jessi), asistencia (número del especialista; hoy sin dato porque nadie marca «se presentó»), leads sin tocar > 24 h, primer intento < 1 h e intentos en 72 h, citas sin estado (14 días), paradas 72 h, WhatsApp fallido, carga por especialista (tope 16), montajes de altas con casillas; flujos y número de WhatsApp «no medibles» con botón a GHL; mover oportunidad, nota, marcar/reprogramar cita y tarea al account en cola simulada (W3). Datos: `fuentes_crm/generar_crm.py` (GHL en vivo con `ghl_agencia/app.py` + `captacion.json` + asignaciones + `nuevos.json`) → `data/crm/crm.json` y `data/crm/_privado/leads.json` (solo `ver_dato`, tipo `lead`). Ver `_ESTADO_crm.md` |
| **M8** | **SEO, ficha de Google y webs** | 4 | **hecho** (`modulos/seo.js`, ruta `#/seo-web`): semáforo SEO por cliente (15 palabras del informe, suben y bajan, clics semana contra semana, visibilidad), detalle con Search Console (serie, páginas, búsquedas) y Analytics, monitor de webs (una comprobación real desde la IP de RO: código, tiempo, certificado, spam) con avisos de medición del `17_…`, y ficha de Google «se conecta». Datos: `data/seo/seo.json` y `webs.json` ← `fuentes_seo/generar_seo.py` (SE Ranking por el conector → `sr_condensar.py`, Search Console con `gg.py`, E1). Ver `_ESTADO_seo.md` |
| **M9** | **Redes** | 4 | **hecho** (`modulos/redes.js`): % de clientes con 14 días cubiertos, huecos, fallidas, por aprobar, calendario de 14 días de todos los clientes, rendimiento de 30 días y detalle con programar/mover en simulación. Datos: `data/redes/redes.json` ← `fuentes_redes/generar_redes.py` (Metricool con `mc.py`). Ver `_ESTADO_redes.md` |
| **M10** | **Producción** | 1 | **hecho** (E7, 2-oct): cola de cada persona por fecha y prioridad, revisión del account y técnica en 48 h, bloqueadas, devueltas, a la primera, no planificado (D-24), carga frente a 12/16 (D-07) y piezas en Meta en índice sin euros. Datos: ClickUp con la llave propia (`fuentes_produccion/extraer_clickup.py` → `generar_produccion.py` → `data/produccion/produccion.json`), flujo del panel de Mili y anuncios de M6. `_ESTADO_produccion.md` |
| **M11** | **Horas y productividad** | 1 | **hecho** (E7, 2-oct): horas por persona y mes (accounts y especialistas aparte), imputado frente a 128 h menos ausencias con el sello «horas incompletas» (D-27), quién imputa ayer, días sin imputar, horas raras (detector de build.py) con Correcto/Hablar/Error simulado, horas por tipo de tarea y productividad frente a sí mismo y a su tipo de tarea, nunca ranking (D-83). Datos: `fuentes_horas/generar_horas.py` → `data/horas/horas.json`. `_ESTADO_horas.md` |
| **M12** | **Clientes nuevos** | 1 | **hecho** (`modulos/nuevos.js`): cada alta de la firma al día 90 (día 0 = alta del contrato en Zoho Sign; encendido día 10, límite 12), % de tareas de su lista «Onboarding —» de ClickUp, vencidas, bloqueadas, hito siguiente, alertas del punto 6 de Mili, línea de tiempo por semanas, accesos, casillas técnicas (píxel, DNS, WhatsApp, calendario), conexiones caídas de las 66 subcuentas, garantía D-30, objetivo del alta y fechas D+N «se aplicará cuando haya escritura». Datos: `fuentes_nuevos/generar_nuevos.py` (Sign `zh.py`, ClickUp `cu.py`, Meta `mt.py`, GHL `app.py`, DNS `dig`) → `data/nuevos/nuevos.json`. Ver `_ESTADO_nuevos.md` |
| **M13** | **Informes mensuales** | 1 | **hecho** (`modulos/informes_mensuales.js`): por cliente y mes, hecho (tarea del informe cerrada en ClickUp, `cu.py`), enviado (correo saliente en Desk de los 30 departamentos con el mes en el asunto, `zh.py`; con PDF pero sin el mes = «posible», nunca «enviado») y pendiente; día 5 verde, día 6 rojo con «Avisar a Mili»; exentos de mantenimiento; «Enviado por otra vía» con motivo (cola simulada); por account; histórico de la hoja de Zoho importado por API (`importar_hoja_w5.py --zoho`: solo la hoja «Informes mensuales», con los hipervínculos de cada celda; 650 filas de oct-2025 a sep-2026) y cuadrado con ClickUp y Desk (diferencias marcadas); account desde la verdad única. Datos: `fuentes_informes/generar_informes.py` → `data/informes/informes.json`. Ver `_ESTADO_informes_reuniones.md` |
| **M14** | **Incidencias** | 1 | **hecho** (`modulos/incidencias.js`): ficha de incidencia con ciclo detectada → avisada → reiterada → escalada (a Tomás con reloj de 48 h, a Coti 24 h) → resuelta con prueba → comprobada con el dato del día siguiente (si sigue, se reabre); lo avisado vuelve arriba a los 2 días; causa R13 en dos campos (dónde / por qué), la marca quien escala y Tomás la cambia; «Para Tomás», mensaje listo, «La he visto». Pestañas: Quién falla en qué (mapa de calor accounts × reglas y mapa de control por persona del panel v27), Incongruencias ClickUp ↔ Desk ↔ CRM con decidir/no aplica + accesos de quien ya no está, Traspasos de cartera (fecha, prueba, revisión a 14 días, estado en app/Desk/CRM), Quién vio primero, El mes (causas, tiempo de resolución, informe de Operaciones generado, revisión mensual de Zadarma). Datos: `fuentes_incidencias/generar_incidencias.py` (bandeja de Desk de E3, agentes de Desk y usuarios del CRM con `zh.py`, miembros de ClickUp con `cu.py`, extensiones con `zd.py`, `zadarma_crudo.json` y `datos.json` del panel v27, rastro de Mili en `rastro_operaciones.json`) → `data/incidencias/incidencias.json`. El ciclo se guarda como acciones del módulo en local.db. Ver `_ESTADO_incidencias.md` |
| **M15** | **Reuniones** | 5 | **hecho** (`modulos/reuniones.js`): reuniones del Zoom de RO de toda la cuenta (`zm.py`: grabaciones + participantes + resumen; las no grabadas esperan W4, dicho en pantalla), internas / con cliente / con gente de fuera por los dominios de los participantes, tipo por el prefijo del nombre (D-06) o «sin tipo» con desplegable, horas y % de 128 h por persona y mes, reunión del ciclo con cada cliente el mes pasado (misma regla que En rojo y la verdad única: CRM + Fathom + verificación + Zoom ≥ 20 min + grupos de WhatsApp cuando estén conectados; mantenimiento exento; account de la verdad; atajos a Fathom, evento del CRM de Zoho y grabación de Zoom); Sofía no la tiene en el menú, actas enlazadas y «subir acta» simulado, dailies. Datos: `fuentes_reuniones/generar_reuniones.py` → `data/reuniones/reuniones.json`. Ver `_ESTADO_informes_reuniones.md` |
| M16 | Ventas de RO | 5 | previsto |
| M17 | Prospección | 5 | previsto |
| **M18** | **Dinero por cliente** | 5 | **hecho** (`modulos/dinero_cliente.js`): cuota con una sola regla (Airtable de octubre → proyecto → factura de Holded → firmado sin ficha; exportada en `fuentes_dinero/cuotas.json`), horas de septiembre frente a pautadas = cuota ÷ 31,47 (pautadas solo para quien ve la cuota), atajos a Holded y Airtable, rentabilidad a 31,47 €/h (Tomás, Mili, Coti) y con coste real por hora (solo Tomás, de M19); Sofía, cuota y línea en facturación; account, sus clientes; publicidad, horas sin euros. Datos: `fuentes_dinero/generar_dinero.py` → `data/dinero_cliente/dinero_cliente.json`. Ver `_ESTADO_dinero.md` |
| **M19** | **Finanzas de la empresa** | 5 | **hecho** (`modulos/finanzas.js`): Tomás: beneficio del mes, cuota recurrente acumulada con escenario «si firman», caja y meses de reserva, ingresos y altas/bajas desde dic-2022, top 20 clientes y proveedores, equipo agregado (áreas ≥ 3), cobros. Sofía: «Mi día» administrativo (calendario, impagos por antigüedad, firmas sin alta, bajas y cambios, caja por banco). Holded en vivo + Airtable lectura + panel financiero v29 → `data/finanzas/finanzas.json`. **v3 (3-oct):** beneficio mes a mes arriba (con/sin gasto sin factura), altas y bajas separadas de los activos, coste del equipo mes a mes por fuente, pestañas «Impagos» y «Cuadre de fuentes» (Sofía: impagos y cuadre de lo facturado) con `fuentes_dinero/generar_cuadre.py` → `data/finanzas/cuadre*.json` e `impagos*.json`; decisiones en `../45_CUADRE_FINANZAS.md`. M16 suma los bloques 8 (anuncio exacto) y 9 (previsión de altas frente a huecos) con `modulos/dinero_m16_anuncios.js` → `data/ventas_ro_extra/anuncios.json` |
| **C2** | **Panel de dirección** (`#/panel-direccion`, solo Tomás) | 5 | **hecho** (`modulos/panel_direccion.js`): el panel de resultados v29/v30 entero dentro de la app. **La captación** (Resumen · Publicidad · De qué anuncio · Agenda · Ventas · Operativa) en 5 periodos, con la cadena del coste en tiles; **La empresa** (Resumen financiero · Clientes · Plan y año · Ingresos · Gastos · Caja · Coste del equipo por persona con «ver datos» y rastro); **Panel original**: enlace al artefacto privado y descarga del .html (la CSP no admite marcos). Las cifras las pinta el propio `render()` del panel en Chrome sin ventana (paridad por construcción): `fuentes_panel_direccion/generar_panel_direccion.py` lee `PANEL_RESULTADOS_RO_2026-09-18/ENTREGA/panel_v2.html` → `data/panel_direccion/` + `modulos/panel_direccion_estilo.js`. Gasto, beneficio, margen, peso del equipo y meses de caja: **solo de M19** (`data/finanzas/direccion.json`), corregidos por el error del dólar del cierre (`25_AUDITORIA_CIERRE_SOFIA.md`). Ver `_ESTADO_panel_direccion.md` |
| **M20** | **Personas** | 5 | **hecho** · `personas.js`: personas en alerta con motivo, desde cuándo y plan (número que manda de Cecilia: en alerta sin plan en 7 días), quién no imputa (ayer y 5 días, recordatorio para copiar), ausencias con suplente (formulario simulado), carga frente a 12/16 proyectos y 128 h, 1:1 trimestral y ronda quincenal, nota 1-10 con hecho, contratación del plan Q4, **lista de salida** (accesos a quitar con atajo y casilla) y, solo dirección y RRHH, **Sueldos** (coste por área, evolución mensual y proyección 2026 vía `ver_dato`, con rastro). «Ayer sin imputar» con la regla única de `verdad/equipo`; atajos a ClickUp, Zoom y Desk. Cada uno ve su ficha; jefas, su equipo; Cecilia, Mili y Tomás, todos (recorte por `persona_id`). Datos: `fuentes_personas/generar_personas.py` (panel v7 `horas_dia`/`alerta`/`anomalias` de ClickUp, asignaciones, `PLAN_FICHAJES_Q4_2026`) → `data/personas_m20/`. Ver `_ESTADO_personas_decisiones_ajustes.md` |
| **M21** | **Decisiones y rastro** | 0 | **hecho** · `decisiones.js` (id `decisiones`, sustituye a la entrada `rastro`; `rastro.js` de E0 va intacto en su pestaña): decisiones con reloj de 48 h (Tomás) y 24 h (Coti) en vivo con `/api/decisiones` (subir y contestar) más las detectadas con las reglas de la ficha de Mili sobre la verdad única (altas: sin encender frente a encendidas tarde); las 101 firmadas con buscador; informe semanal para Tomás y cierre de mes de Operaciones (exigencias 48 y 49) copiables. Datos: `fuentes_decisiones/generar_decisiones.py` → `data/decisiones/` |
| **M22** | **Ajustes** | 0 | **hecho** · E0 (personas, asignaciones, para confirmar, ver como, avisos y recargas) + pestaña **Conexiones y caducidad** (`ajustes_conexiones.js`): 14 conexiones comprobadas con una lectura mínima (Meta caduca 1-dic, GHL rota solo, Windsor sin llave, SE Ranking 403, Desk 30 departamentos, ClickUp con su cupo…) con enlace a la consola donde se renueva cada llave, y avisos de caducidad, fuentes y seguridad. Datos: `fuentes_ajustes/generar_conexiones.py` → `data/ajustes/conexiones.json` |
| **M23** | **Agenda** | 1 | **hecho** (`modulos/agenda.js`, ruta `#/agenda`): el calendario de cada persona con Hoy (línea de ahora, «Ficha del cliente», abrir en Zoho/GHL/Zoom), Semana (rejilla 8-20 h; lista en móvil), Huecos libres (L-V 9-18, copiar), Mi equipo / Todo el equipo y Fuentes; cliente en rojo con reunión hoy; prospectos con iniciales y «Ver nombres» solo para el dueño (`ver_dato`, rastro). Datos: `fuentes_agenda/generar_agenda.py` → `data/agenda/agenda.json` (Zoho CRM Events con `zh.py`; Zoho Bookings de todo el personal y Zoho Calendar de Tomás con `~/RO_HERRAMIENTAS/zoho/zbookings.py`; GHL de RO, calendarios de Tomás; Zoom grabado de M15; la misma cita en varias herramientas se junta en una con todos sus atajos) y `data/agenda/_privado/<persona>.json` (el dueño recibe los nombres completos; el resto, iniciales). «En rojo» = verdad única. Ver `_ESTADO_agenda.md` |
| **M24** | **Chat del equipo** | 1 | **hecho** (`modulos/chat_equipo.js`, ruta `#/chat-equipo/<canal>`): canales internos de ClickUp (no los de clientes), grupos y directos de Tomás; hilos, búsqueda, menciones y no leídos (desde tu última visita); escribir y responder a la cola simulada; videollamada Zoom en directos; cómo será el envío con la cuenta de cada uno (OAuth por usuario). Datos: `fuentes_chat_equipo/generar_chat_equipo.py` (llave propia de ClickUp, API v3) → `data/chat_equipo/p_<persona>.json`, solo los canales de los que es miembro. Ver `_ESTADO_chat_equipo.md` |
| **N1** | **Paneles de herramientas** | 3 | **hecho** (`modulos/paneles.js` + `paneles_periodo.js`, rutas `#/paneles/<cliente>/<herramienta>/<vista>`, `#/paneles/empresa/<desk\|zadarma>`, `#/paneles/mapa`): las vistas estándar de Meta Ads (campañas, conjuntos, anuncios), GoHighLevel (embudo por etapa, citas, contactos y conversaciones), Analytics (resumen, adquisición, interacción, eventos clave, páginas, tecnología y lugar), Search Console (rendimiento, indexación, experiencia) y Metricool (analítica por red), con periodo común (hoy … año y a medida, comparación con anterior o año anterior, recordado por persona); Zoho Desk y Zadarma solo dirección, operaciones y proyectos; «Dónde está cada panel». Datos: `fuentes_paneles/generar_paneles.py` (gg, mt, app.py de GHL, mc, zh, zd; solo lectura) → `data/paneles/<herramienta>/<cliente>.json`. Mapa de paridad en `../33_PARIDAD_PANELES_HERRAMIENTAS.md`. Ver `_ESTADO_paneles.md` |
| **N3** | **Asistente IA** | 1 | **hecho** (`modulos/asistente_ia.js`, ruta `#/asistente-ia/<cliente>`; servicio `ia.py` enganchado en `servir.py`, rutas `/api/ia/*`; componentes `modulos/ia_componentes.js`: `botonIA`, `panelCopiloto`, `bloqueCopiloto`, `iaDe` = `ctx.ia`): borrador de respuesta a correos de Desk en la voz de RO y «Qué haría hoy» del account (diagnóstico + 3 acciones con prueba). Contexto armado en el servidor con los permisos de quien pide; nunca envía; rastro de cada sugerencia. Sin clave de Anthropic, «IA sin conectar» y precalculados del 2-oct (40 borradores, 22 clientes) en `data/ia/_privado/` (`fuentes_ia/extraer_hilos.py`, `precalcular.py`; pruebas `probar_ia.py`, `capturar_ia.py`). Ver `_ESTADO_ia.md` |
| **N4** | **Alertas del departamento** | 1 | **hecho** (`modulos/alertas.js`, ruta `#/alertas`): motor único que NO recalcula: reúne las alertas que ya calculan Webs/SEO, Salud del CRM, Captación, Redes, En rojo y verdad única, Bandeja, Reuniones, Informes, Incidencias, Clientes nuevos, Finanzas, Personas, Horas y Decisiones (303 hoy, 29 de 29 cifras iguales a su módulo) y las reparte en 10 departamentos con dueño (silla del cliente en asignaciones o jefe), motivo, desde, plazo, gravedad, «Abrir en …», «Ir» y escalado dueño → jefe → Mili (→ Tomás). Estados nueva/vista/lo tengo/resuelta (se comprueba con el dato siguiente)/no aplica en la cola simulada con rastro (tipos `alerta_*`). Resumen diario por persona y bloque `mi_dia` para Mi día. Datos: `fuentes_alertas/generar_alertas.py` → `data/alertas/p_<persona>.json` (solo_propio) y `alertas.json` (dirección y operaciones); pruebas `fuentes_alertas/probar_alertas.py`. Modular DS entra solo cuando deje `data/modular/modular.json`. Ver `_ESTADO_alertas.md` |

Los previstos ya salen en el menú de cada puesto con la etiqueta «previsto» y una página vacía que explica qué serán.

## Comprobación de E0 (2-oct, servir.py en 127.0.0.1:8770)

`pruebas_e0.py`: todo bien. «Ver como» recorrido en el navegador interno con 9 puestos (Mili, Lucía, Lina, Gustavo, Camilo, Ana setter, Sofía, Coti, Cecilia) mirando la respuesta del servidor, no la pantalla; detalle en `_ESTADO_E0.md`.

## Comprobación hecha (2-oct, navegador interno, servidor local en el puerto 8765)

- **Consola sin errores ni avisos** en carga, navegación, «ver como» y catálogo.
- **«Ver como» recorrido con las 40 personas:** ninguna pantalla falla. Ejemplos: Lucía ve 17 entradas de menú, detalle de 13 clientes (los suyos), cuota de 13 y sus 4 avisos de persona; Camilo (producción) ve 10 entradas y ningún detalle ni cuota; Valeria ve la inversión de todos y ninguna cuota; Sofía ve todas las cuotas y ninguna inversión; Cecilia, avisos de persona y ningún cliente.
- **Recorte comprobado:** como Lucía, 0 alarmas de clientes ajenos llevan texto, acción o enlace; abrir `#/en-rojo/musashi-consultores` dice «no es de tu puesto».
- **Móvil 375 px:** sin desplazamiento horizontal; menú plegable con foco y Esc; tabla apilada en tarjetas; cabecera no fija para no comerse la pantalla.
- **Teclado:** ⌘K, flechas, Intro y Esc en la paleta; Intro en una fila de la tabla abre el detalle; «Sí / No» de la confirmación con foco en «No»; enlace «Saltar al contenido».
- **Buscador limitado:** como Camilo, buscar «gac» no devuelve nada (no puede abrir ese cliente).

## Pendiente para la fase 0 de verdad

1. W1: copiar `permisos.js` + `reglas_permisos.json` al Worker y portar las rutas de `servir.py`; identidad por Cloudflare Access (`servir.py` ya entiende la cabecera `Cf-Access-Authenticated-User-Email`).
2. W1: aplicar `schema_v2.sql` en D1 y cargar personas y asignaciones (ya probado en `local.db`).
3. Hecho en local: rastro imborrable en servidor (`registro`, disparadores). Falta en D1.
4. Fórmula de salud de la D-02 en `build.py`.

## Ronda 8 (2-oct): cambios de contrato (compatibles hacia atrás)
- **ctx.personas[]**: campos nuevos `zona`, `rol`, `pais`, `fecha_ingreso`, `cumple_dia_mes` (MM-DD, sin año) y `etiquetas` (p. ej. Camilo, «transversal»). Los saca build_data de `fuentes_equipo/equipo.json`.
- **Correos de entrada**: van en `data/_privado/correos_entrada.json`. Solo los lee servir.py y nunca se sirven. La lista para Cloudflare está en `despliegue/lista_access.txt`.
- **ctx.clientes[]**: lleva `cuota_fuente` junto a `cuota`. La fuente única es `fuentes_dinero/cuotas.json`. La verdad única lleva también `cuota` y `cuota_fuente`, que el servidor recorta.
- **POST /api/acciones** exige `modulo` y que quien manda la acción vea ese módulo. `ctx.accion()` ya manda el módulo.
- **/api/ver_dato** sin fila responde 200 con `{valor:null, sin_dato:true}`.
- **Inicio por puesto**: `INICIO_POR_PUESTO` en app.js (setters → setters). Para que un puesto tenga inicio propio, se añade ahí.
- **gzip**: servir.py comprime lo que pase de 1 KB si el navegador lo acepta.

## Ronda 9 (2-oct, noche): cambios de contrato (compatibles hacia atrás)
- **Periodo común:** exporta `usa_periodo: true` (o `['7d','30d','mes',…]`) en tu módulo y lee `ctx.periodo` = `{ id, desde, hasta, dias, nombre, rango, comparar, comp: { desde, hasta, rango } | null, texto }`. `ctx.alCambiarPeriodo(fn)` para repintar solo lo tuyo (si no escuchas, la carcasa repinta el módulo). Utilidades en `componentes.js`: `sumarSerie`, `serieDelPeriodo`, `deltaPeriodo`, `rangoPeriodo`, `rangoComparacion`. No pintes tu propio selector.
- **Cuota de la empresa:** `ctx.cuotaEmpresa()` → `{ recurrente, cuota_mes, facturable, coherente }` (de `fuentes_dinero/cuotas.json`; null si tu puesto no ve la cuota). La de cada cliente sigue en `ctx.clientes[].cuota`.
- **Tiendas online:** `c.tipo_negocio === 'tienda_online'` (Kiosko) → fuera de totales de leads y del techo de 35 €/lead.
- **Diseño (auditoría 30):** solo tokens de `estilos.css` (`--t-*`, `--fs-*`, `--s-*`, `--relleno`, `--r-s/m/l/full`, `--sombra-1/2/3`, `--borde`) y componentes: `grafico()` (único motor de gráficos), `colorCifra()` (color de beneficio, coste por cliente y coste por lead), `rejillaTarjetas()`, `cifraPrincipal()`, `vacioLinea()`, `panel({ verTodo })`, `menuMas()`, `campoTexto()`, `esqueleto()`. `fmt` ya agrupa miles siempre. Nada de `<style>` propio. `python3 pruebas_diseno.py` dice qué queda en tu módulo.
- **Cabecera:** una fila de 64 px; «Ver como» está en el menú de la persona (avatar ▾) con el mismo id `#vercomo-sel`.
- **Datos de Modular DS:** `data/modular/webs.json` dado de alta para `seo-web`.

## Ronda 10 (2-oct, noche): contrato (compatible hacia atrás) y parches locales que ya sobran
**Lo común nuevo o cambiado (`componentes.js`, `estilos.css`, `app.js`):**
- **`menuMas()`** ya no pinta «null» con el menú cerrado (arreglado por el coordinador; comprobado). El selector de periodo tenía el mismo fallo con `comparar: false`: arreglado. **`poner(el, ...hijos)`** sustituye a `el.replaceChildren(...)` cuando un hijo puede faltar (salta null, undefined, false y '').
- **`tablaDensa()`**: columnas sin `clave` ya no rompen (no se ordenan salvo que traigan `valor()`); filtros sin `<select>` nativo: chips si hay ≤ 4 opciones, si no **`menuElegir()`** («Puesto: Todos ▾», con buscador a partir de 11 opciones; `filtros[i].menu: true` lo fuerza); en el móvil los filtros se pliegan tras **«Filtros ▾»** y la tabla apilada se ordena con «Ordenar por ▾»; la cabecera ordenable es la celda entera (≥ 32 px); buscador de 280 px; `verTodas: true` → «Ver las N filas»; `columna.minAncho: '160px'` (en vez de envolver celdas en un span). La cabecera oculta de la tabla apilable ya no cuenta como desborde a 390.
- **`tile()`** y **`fichaIndicador()`** sin valor: «Sin dato» pequeño y gris; `sinDato: 'falta emparejar Search Console'` dice por qué. Un nodo como valor ya no sale «[object …]» en la etiqueta accesible. La «i» de la tarjeta va arriba a la derecha (sin línea propia).
- **`.tiles`** en el móvil: rejilla 2 × 2 (la impar, a todo el ancho), no carrusel. **`.dos`** se apila de verdad a 390 (la regla 2fr/1fr solo vale por encima de 900 px). **`.bt.mini`** y chips a 32 px de alto.
- **`grafico()`**: la última fecha del eje ya no pisa a la anterior (mide el texto). **`barraApilada({ partes, etiqueta })`** nuevo. **`cuentagotas(valores, umbral, { mejorSi })`** común (el corte del rojo: como mucho el tercio peor; lo aplica el dueño).
- **`pestanas({ …, unaFila: true })`**: lo que no cabe va a «Más (n) ▾» (es el `pestanasEnUnaFila()` de la ficha).
- **`selectorPersona({ personas, actual, alElegir })`** con buscador y avatares; **`selectorCliente({ placeholder, nada, logo })`**.
- **`listaLoPrimero(items, { subir: false })`** no sube el panel arriba en el móvil; estados `gris` e `info` además de `rojo` y `ambar`.
- **Periodo**: `usa_periodo` admite una función `(params) => true | false | [ids]` (sub-rutas que no dependen del periodo); `periodos_con_datos` (lista o función) o **`ctx.periodosConDatos([{ nombre, desde, hasta }])`** en el render añaden «Con datos» al menú «Más» (elegir uno deja «A medida» con esas fechas).
- **`@media print`** común: fuera menú, cabecera, barra de periodo, controles de tabla y todo lo marcado `.no-imprimir`; paneles sin sombra y sin cortarse.
- **IA**: la hoja de `modulos/ia_componentes.js` vive en `estilos.css` («IA · ia_componentes.js»), ya en la escala; `estilos()` queda vacía.
- **Guía de estilo obligatoria**: `pruebas_e0.py` corre `pruebas_diseno.py --estricto`. Si tu módulo trae `<style>`, letra fuera de escala, colores sueltos o sombras/radios con número, la batería de E0 falla. (`--en-obra a.js,b.js` deja avisar sin fallar mientras su dueño trabaja; la lista `EN_OBRA` de `pruebas_e0.py` está vacía.)

**Parches locales que cada dueño PUEDE QUITAR ya** (no los toco: son sus ficheros):
| Dónde | Parche | Por qué sobra |
|---|---|---|
| ficha.js, bandeja.js | `menuMasLimpio()` | `menuMas()` común ya no escribe «null» |
| ficha.js | `pestanasEnUnaFila()` | `pestanas({ unaFila: true })` |
| agenda.js | `menuAbrir()` propio con `.menu-flot` | `menuMas()` común; selector de persona → `selectorPersona()` |
| paneles.js, nuevos.js | `<details class="periodo-mas menu-mas">` + `.menu-flot` | `menuMas()` común; Paneles › «Dónde está cada panel» puede usar `usa_periodo: params => …` |
| captacion.js | observador `sinNull`; nodo «Sin dato» con `toString` | `menuMas()` arreglado; `tile({ valor: null, sinDato })` |
| crm.js | «Sin dato» con `toString`; lista propia de Hallazgos | `tile({ sinDato })`; `listaLoPrimero(items, { subir: false })` con estado `gris`/`info` |
| produccion_comun.js / horas.js | `cuentagotas()`, `dosColumnas()`, `ancharBuscador()`, `selectorPersona()` propios | `cuentagotas()` y `selectorPersona()` comunes; `.dos` se apila; buscador a 280 px |
| seo.js, redes.js, nuevos.js | `.dos` con `gridTemplateColumns` en línea | `.dos` ya se apila en el móvil |
| informe.js | enlaces «Otros periodos con informe» | `ctx.periodosConDatos([...])` |
| quien use `tablaDensa` con `porPagina` | — | `verTodas: true` si quiere «Ver las N filas» |

## Ronda 11 (2-oct, noche): seguridad de la auditoría 35 y ajustes de las auditorías 34 (contrato compatible)
- **«Ver como» y ficheros privados.** `solo_propio` (chat_equipo/p_*, alertas/p_*) y las filas con `miembros` se miran con la persona vista **y** con la real: en «ver como» nadie lee el chat ni las alertas propias de otro (ni Mili ni Tomás). Mi día en «ver como» se queda sin «Mis alertas» de la otra persona (403 esperado).
- **Importes en textos.** `P.sin_importes(o, quitar=("cuota","inversion"))` ya **no deja «[importe]»**: quita la frase, el paréntesis o la cifra con su preposición. Distingue cuota (palabras «/mes», «cuota», «factura»…) de gasto; el techo general de coste por lead solo lo ve quien ve la inversión. `P.importes_a_quitar(ve_cuota, ve_inversion)`. Se aplica en `recortar()`, `recortar_modulo`, la ficha (`servir.ficha_sin_importes`) y la IA.
- **IA.** El contexto del copiloto usa las alarmas ya recortadas (`P.recortar`). Precalculados y borradores se sirven recortados por persona (`ia.recortar_dinero`: sin importes que no ve y, sin «cobros», sin frases de facturas/cobros/impagos). `/api/ia/*` da a quien no es dirección «La IA está sin conectar; lo activa Tomás.».
- **Ajustes.** `reglas_permisos.json → puestos_solo_tomas` (dirección, finanzas de dirección, RRHH, operaciones, ventas de RO, administración): darlos o quitarlos, y cambiar puestos, estado, jefe o correo de quien ya tiene uno, solo Tomás. `GET /api/ajustes` añade `puestos_solo_tomas` y `realEsDireccion` (la pantalla los desactiva).
- **Acciones.** `responder` exige que el servidor sepa el cliente del objeto (`servir.cliente_de_objeto`: Desk → Bandeja, WhatsApp → grupo por cliente_id, GHL → ref del CRM); si no, 403. `acciones_solo_puestos` (bajas, cobros, quitar accesos…) por puesto de la persona real. La misma acción en 120 s (`acciones_repetidas_segundos`) devuelve la fila anterior con `repetida: true`.
- **Rastro.** Denegados agrupados por persona, ruta y minuto (tope 30 + una fila «rastro_limitado»); el navegador, 60 filas por minuto (luego 429). Tabla `rastro_incidencias` (imborrable): cortes 1289 y 1571 y filas 1-692 sin huella, anotados. `python3 servir.py --verificar-rastro` (entera + desde la anotación + anclas), `--ancla-diaria [AAAA-MM-DD]` (añade a `despliegue/estado/anclas_rastro.jsonl`; `RO_ANCLAS` para otra ruta), `--anotar-incidencia <corte|sin_huella|nota> <desde> <hasta> "<motivo>"`. `/api/rastro/verificar` devuelve también `tras_anotacion` y `anclas`; `?desde=anotado`.
- **Datos rotos.** `/api/modulo/*` y `/api/cliente/*`: fichero roto, de 0 bytes o vacío → último dato bueno en memoria con `_ultimo_dato_bueno: {dato_de, motivo}`; sin uno anterior, 503 legible (nunca 500).
- **Mi día.** `datos_de_modulo["mi_dia/config"].ramas_sin_importes_salvo = {"puestos.direccion": "dinero_empresa"}` (nuevo: tapa importes solo en esa rama).
- **Comunes de diseño.** `tarjetaCliente` sin nombres partidos (la salud baja de línea); zonas de toque de 32 px en el móvil; `.embudo-barras .et` con la cifra en `minmax(54px, max-content)`; `.que-es summary` con `max-width: 100%`; `selectorPeriodo` (no común) salta de línea; `tile({ crudo: true })` no limpia el contexto.
- **Despliegue.** `render.yaml → ro-app`: `RO_ORIGEN_APP=https://app.rankingonline.app`.
- **Pruebas.** `pruebas_seguridad.py` usa un puerto de 8920-8929 y `--bind 127.0.0.1`; casos «R11» por hallazgo (algunos con un segundo servidor sobre una copia de la app para estropear ficheros a propósito).

## Ronda 12 (2-oct, noche · pendientes R13 de E0): contrato compatible
- **Búsquedas enteras.** `P.CLAVES_TEXTO_LIBRE` (consultas, búsquedas, keywords, palabras clave, términos, queries…): lo que hay debajo de esas claves es texto de quien busca y **no** pasa por `sin_importes` (ni en `recortar_modulo`, ni en la ficha, ni en la IA). Solo se quita un importe con símbolo (`€0,00`, `$500`: coste de Google Ads colado) a quien no ve la inversión (`P.sin_importes_libre`). «delito fiscal 120.000 euros anuales» llega entera. Si tu lista de búsquedas se llama de otra forma, añade el nombre a la expresión de `permisos.py`.
- **Descripción del cliente.** `ctx.clientes[].descripcion` es corta y sin importes; `descripcion_completa` (solo si la original lleva importes, hoy Deudot) llega recortada por el servidor como el resto del detalle. Igual que `portal.descripcion` / `portal.descripcion_completa` de la ficha.
- **Componentes.** `.pie-fase2 summary` a 32 px en el móvil. `selectorPeriodo({ comun })`: con ≤ 4 periodos (sin contar «A medida») todos a la vista; «A medida» y «Con datos» siguen en «Más».
- **Catálogo.** 229 de puesto (+23 de fase 2). Campo nuevo `el_que_manda` (uno por puesto donde la ficha lo marca) y, para indicadores de varias partes, `partes: [{ que, medible, porque }]` («¿se mide hoy?» de cada una; `fichaCatalogo()` las pinta en «¿Qué es?»). **Account:** manda `account.resultados_de_su_cartera_frente_a_objetivo` (leads, citas y ventas de su cartera frente a objetivo; regla de Tomás «cada puesto mide primero los resultados de sus clientes»); la salud queda de segundo (`segundo_de`, mismo id de antes). Léelo con `ctx.indicadores().find(i => i.puesto === p && i.el_que_manda)`.
- **Pruebas.** `RO_PUERTOS_PRUEBA=8965-8969 python3 pruebas_seguridad.py` elige el rango de puertos (por defecto 8920-8929).

## N9 (2-oct, noche): altas y bajas de personas desde Ajustes (contrato compatible)
- **Ajustes › Altas y bajas** (`modulos/ajustes.js`, servidor `altas_personas.py`, enganchado a `servir.py` como `ia.py`): añadir persona (nombre, puesto con plantilla, jefe, zona, entrada, cumpleaños día/mes, correo de entrada, cartera por silla), cambiar puesto/jefe/zona/rol/país/ingreso/correo/cartera, dar de baja con propuesta de reparto, tareas de Cloudflare Access para Tomás, jefes de departamento y dudas de Tomás. Mismas reglas de mando que Ajustes (`puestos_solo_tomas`).
- **Rutas:** `GET /api/altas`, `/api/altas/comprobar?id=`, `/api/altas/guia?puesto=`; `POST /api/altas/alta | cambio | baja | repartir | departamento | tarea_hecha`. Las altas viven en `historial` (`personas · crear`) y se reaplican en `Estado.aplicar_ajustes`. Tabla nueva `altas_tareas` (no se borra; solo se marca «hecha»).
- **Correo de entrada:** solo en `data/_privado/correos_entrada.json` (`correos` + `desde_la_app`); `build_data.py` lo conserva al regenerar (`fusionar_altas_app`). `despliegue/lista_access.txt` se reescribe con lo activo y deja al pie lo pendiente de pasar a Access. Cloudflare no se toca.
- **Datos editables (antes en código):** `fuentes_equipo/correcciones_equipo.json` (puestos, jefes, etiquetas y notas que aplica build_data), `data/departamentos.json` (jefe de cada departamento; lo lee `generar_alertas.py`; solo Tomás lo cambia) y `fuentes_equipo/dudas_roles.json`.
- **Pruebas sin tocar lo real:** `RO_DB`, `RO_CORREOS_ENTRADA`, `RO_LISTA_ACCESS`, `RO_DEPARTAMENTOS` apuntan a copias (`pruebas_seguridad.py` ya lo hace; casos «N9»).

## N15 (2-oct, noche): canales de avisos, grupos de la app y campana (contrato compatible)
- **Servidor:** `avisos.py`, enganchado a `servir.py` como `ia.py`. Rutas `GET /api/canales`, `/api/canales/canal?id=&antes=`, `/campana`, `/buscar?q=`, `/clickup?canal=&antes=`; `POST /api/canales/mensaje | leido | estado | preferencias | grupo | miembro | campana_vista`. **`/api/avisos` sigue siendo lo de E0.** Tablas nuevas `canal_*` (mensajes, miembros y grupos imborrables).
- **Avisos:** cada alerta de N4 se publica en `#avisos-<departamento>` con dueño, plazo y mención; «Lo tengo»/«Resuelta» escriben la misma acción del módulo `alertas`. Para añadir un evento del sistema: `_sync_eventos()` en `avisos.py` (clave única, `ver` = `{alerta}` / `{puestos}` o cliente_id).
- **Chat de ClickUp partido:** `data/chat_equipo/p_<id>.json` es un índice ligero (sin `mensajes`; `recientes`, `ultimo_msg`); los mensajes, en `data/chat_equipo/_privado/c_<canal>.json` por `/api/canales/clickup` (50 por página). `fuentes_chat_equipo/tapado.py` tiene `tapar()` y `limpiar()` para quien los necesite.
- **Carcasa:** campana `#campana` junto al avatar (refresca con el evento `ro:avisos`).

## Ronda 14 (2-oct, noche · velocidad, auditoría 37): contrato compatible
- **Código bajo demanda.** Con `servir.py`, el menú sale de `modulos_puestos` de `/api/sesion` y el código de cada pantalla se importa al abrirla (y el resto, con el navegador libre). Un módulo **no debe tener efectos al importarse** (todo dentro de `render`). Sin servidor se importan todos, como antes.
- **Versiones.** `index.html` lo reescribe `servir.py`: mapa de versiones (import map), `?v=<huella>` en cada fichero propio y caché de un año. Nada que hacer en los módulos: los `import` relativos ya pasan por el mapa. Un fichero nuevo en `modulos/` entra solo.
- **Memoria de datos.** `ctx.datosModulo()` y los GET de `ctx.api()` (`modulo/*`, `indicadores`, `acciones`, `avisos`, `decisiones`, `ia/lista`, `cliente/*`) pintan lo guardado y refrescan detrás; cualquier POST olvida acciones, avisos, decisiones e IA. Persona real: también en el disco del navegador (IndexedDB), que se borra al entrar otra persona; «ver como»: solo memoria. Nunca `_privado/`, sueldos ni «ver datos».
- **Servidor.** `/api/modulo/*` e `/api/indicadores` guardan lo ya recortado y comprimido por (persona real, vista, fichero, versión de reglas/base/módulos, día) con ETag (304). Logos en `/logos/<cliente>.jpg?v=…` (fuera de la sesión). Fuentes en `fuentes_web/` (sin Google). `python3 servir.py --help` enseña la ayuda y sale.
- **Textos.** La carcasa quita de cualquier texto de la pantalla rutas de datos (`…/_privado/…`, `…/p_<persona>`), nombres de fichero y códigos de obra (M14, W1, D-27, SP14). Lo de entre «» y el plegado «¿De dónde sale?» no se tocan.


## Ronda 15 (2-oct, noche · facilidad de uso): contrato compatible
- **`ayudas.js` (nuevo, común).** Lo carga `app.js` con el navegador libre (no está en la entrada) y al momento si alguien pulsa ⌘K, «/» o la lupa. Tiene el buscador, los contadores y «Mis clientes» del menú, «Algo va mal / Tengo una idea» y los atajos. Exporta `vistaOpiniones({ api, todas, soloLectura })` para montar la lista en Ajustes.
- **Buscador (⌘K, «/»).** Además de pantallas, clientes y personas (`#/personas/<id>`), busca tareas, correos (asunto y n.º de ticket), alertas, webs, campañas, reuniones, decisiones e incidencias con `GET /api/buscar/indice`: un índice por persona que sale de los ficheros **ya recortados por su puerta** (`puerta_modulo()` de `servir.py`, la misma de `/api/modulo/*`); alertas solo las propias (`p_<id>`), y en «ver como» sin alertas. `GET /api/buscar?q=` filtra el mismo índice. Acciones: «Contestar el correo más antiguo (de X)» → `#/bandeja/<id>?contestar=1`, «Ir a la ficha de X», «Semáforo del lunes de X» (abre la ficha y pulsa el botón), «Crear un grupo en el chat» (pulsa «Nuevo grupo»), «Posponer hasta mañana/el lunes a las 9: …» (acción `alerta_posponer`, con la guardia), «Fijar/Quitar X de Mis clientes», «Algo va mal», «Ver los atajos», «Ver como…». Teclado: ↑ ↓, Tab / Mayús+Tab o AvPág/RePág por grupo, Ctrl+Inicio/Fin, ↵, Esc (borra y cierra).
- **Contadores del menú.** Alertas = «mías» con `alertasMias` de `mi_dia_bloques.js` (la misma de «Lo mío» y de Alertas); Bandeja = correos de tu cartera de `correosLoMio`; Decisiones = `decisionesMias`; Producción = **vencidas tras `alDia()` con el hoy de Madrid** (la cifra de «Mi cola»: `vencidas_al_dia()` de `servir.py` aplica la misma regla que `alDia()` de `produccion_comun.js` sobre la cola ya recortada; si el fichero es de otro día, lo que vencía antes de hoy pasa a vencida y lo de más de 30 días a olvidada; con el dato de hoy, `personas[].vencidas`), por `GET /api/contadores`, sin bajar el fichero de 0,9 MB; cambia a medianoche de Madrid; Chat = menciones sin leer de la campana. Se recuentan cada minuto, tras cada POST y con `ro:avisos`. **Si alguien cambia la firma de esas tres funciones de `mi_dia_bloques.js`, que avise a E0** (`pruebas_coherencia.py` lo vigila).
- **«Mis clientes».** Sección del menú con un punto de color por la gravedad de la verdad única; si la persona nunca ha fijado nada, su cartera (12 como mucho, lo más grave arriba). Se fija o quita con el botón de la cabecera en las pantallas de un cliente (ficha, En rojo…) o desde el buscador. `GET/POST /api/preferencias` (`{ fijados: [ids] }`, 30 como mucho, solo clientes que abre; tabla `preferencias`, con rastro `cliente_fijado` / `cliente_desfijado`).
- **«Algo va mal / Tengo una idea».** Botón en la cabecera. `POST /api/opinion` (`tipo` fallo|idea, `prioridad` rojo|ambar|gris, `texto`, `esperaba`, `ruta`, `pantalla`, `ancho`, `alto`, `frescura`, `captura` opcional: JPEG en data URL ≤ 190 KB hecha con el permiso del navegador). Quién y cuándo los pone el servidor; tabla `opiniones` (no se borra ni cambia de autor), rastro `opinion_enviada` y aviso en #avisos-dirección (solo dirección y operaciones). `GET /api/opiniones` (Mili y Tomás todas; el resto, las suyas), `/api/opiniones/captura?id=`, `POST /api/opiniones/estado` (vista/resuelta, solo Mili y Tomás). Tope 20 por hora y persona.
- **Atajos.** «?» chuleta · ⌘K y «/» buscar · g+d Mi día · g+b Bandeja · g+a Alertas · g+c Chat · g+f Ficha · g+p Producción · j/k fila siguiente/anterior (filas de tabla, `.primero > li`, `[data-fila]`, `[role=listitem]`) · ↵ abre la fila · e pulsa el botón `[data-atajo="e"]` de la fila o el que diga «Hecho», «Lo tengo» o «Resuelta». Nunca dentro de un campo. Un módulo que quiera que «e» haga otra cosa pone `data-atajo="e"` en ese botón; para que una lista propia se recorra con j/k, `data-fila` en cada fila.
- **Componentes.** `menuMas({ items: [{ texto, alPulsar, confirmar: '¿…?', si: 'Sí, quitar' }] })` pregunta dentro del menú antes de hacer algo que no se deshace. `.dos.iguales` = dos columnas iguales (se apila por debajo de 901 px). Iconos nuevos `conexiones`, `opinion`, `fijar`, `teclado`; `ICONO_MODULO.conexiones`.
- **Conexiones.** «Probar ahora» lo puede pulsar Agus (`probar_conexiones`: dirección, operaciones y técnico de altas): `POST /api/recarga { modo: 'conexiones' }` (o sin modo si no puede recargar) lanza **solo** `despliegue/salud_conexiones.py` (paso `conexiones` de `recarga.json`); la recarga entera sigue siendo de Mili y Tomás.
- **Alertas.** La guardia de `fuentes_alertas/guardia_alertas.py` está enganchada en `servir.py`: nadie pospone ni despacha en lote alertas ajenas (403) ni pospone a más de 31 días (400), y el motor lo vuelve a rechazar si llegara a la base.
- **Buscador por ruta (nota R16).** El buscador ya no pulsa botones por su texto: cada fila lleva su ruta exacta (`ir`) y la pantalla la abre. Reuniones: `id` = la reunión e `ir` = `#/reuniones/<id>` (la pantalla de Reuniones tiene que abrir esa ruta; si no, cae en `#/reuniones`).

## Ronda 16 (3-oct, madrugada · seguridad y solidez, auditoría 35b): contrato compatible
- **Fechas.** Las horas de la base siguen en UTC (`datetime('now')`); las FECHAS de negocio (hoy, desde/hasta de asignaciones, bajas, foto) van siempre en hora de Madrid: `P.hoy_iso()` / `servir.hoy()` / `altas_personas.hoy()`, igual en el Mac que en Render. Nadie compara una fecha de negocio con `date('now')`. `RO_RELOJ=AAAA-MM-DDTHH:MM` (hora de Madrid) fija el reloj en las pruebas.
- **Ancla del rastro.** `--ancla-diaria` cubre un **rango de ids** (desde la fila siguiente a la última anclada hasta la última), sin depender de la zona: vale a las 00:30 y a las 01:59. Con fecha (`--ancla-diaria AAAA-MM-DD`), las filas de ese día de Madrid pasado a UTC. Las anclas viejas se siguen comprobando por su fecha. `RO_ANCLAS_COPIA=<ruta>` escribe además una copia (otro disco o volumen de fuera).
- **Textos libres.** `servir.limpiar_texto()` = `tapado.limpiar()` + «la contraseña de … es X» sin dos puntos. Lo usan «Algo va mal» (texto, esperaba, pantalla y frescura, ANTES de guardar, del aviso y del rastro, que lleva solo tipo y largo) y los canales. Una captura hecha en Sueldos no se guarda. `GET /api/opiniones` trae además `equipo: {persona: {alguna, primera}}` de la gente que tiene a quien mira de jefe directo (solo el hecho, nunca el texto).
- **Canales.** Lo que dice lo que cobra alguien (palabra de sueldo o «cobrar», «brutos», «netos» con una cifra, también en letra; o el nombre de una persona del equipo con un importe y «al mes», «subida»… sin un cliente nombrado) se rechaza con 400. Lo guardado de antes se ve sin cifras salvo dirección y RRHH. A **Equipo/avisos de RRHH y Dirección** añade solo Tomás (y Cecilia en RRHH); al resto de equipos, su jefe, operaciones o dirección (`puede_anadir` en `/api/canales`).
- **Acciones** (`reglas_permisos.json → acciones_con_efecto_fuera`). WhatsApp, correo, llamadas, GHL, Metricool, Zoom, chat de ClickUp… exigen un cliente que la persona REAL lleve (su cartera o `lleva_puestos`); en WhatsApp/correo/llamar el objeto no puede ser una dirección o un teléfono escritos a mano, y en WhatsApp y GHL el servidor tiene que reconocer el grupo o el contacto (en GHL vale «… · cita|lead|oportunidad <ref>»). En ClickUp, `mover_estado`, `mover_tarjeta`, `mover` y `comentario` solo sobre una tarea de Producción del que actúa, de su equipo, operaciones o dirección; una pieza que espera revisión solo cambia con `pieza_aprobar`/`pieza_pedir_cambios`. `asignacion` (dirección y operaciones) y `asignar` (más proyectos) van por puesto. `primera_semana_paso` solo con objeto `<tu id>:<paso>`. La vista previa no admite `javascript:` a ninguna profundidad.
- **Revisión técnica por área** (`revision_piezas.areas_tecnica`): cada jefa revisa solo piezas de su área (puesto del autor o que el autor la tenga de jefa directa).
- **Alertas.** La guardia y el motor cubren también `alerta_lo_tengo`, `alerta_resuelta`, `alerta_no_aplica` y `alerta_reabrir`: solo su dueño, su jefe, Mili y Tomás.
- **Importes.** `P.sin_importes` entiende también «1,5 k€», «1470 eur», «EUR 500», «10-11 k €/mes» y cifras en letra («mil ochocientos euros»). Guías de la primera semana: `textos_sin_importes_salvo: dinero_empresa`; el número que manda llega en texto llano (y `numero_tabla` con las filas). `/api/indicadores`: umbrales en euros solo para quien ve cuota o inversión en general.
- **Varios.** A una persona con puesto de mando, cualquier campo (también alias y horas) solo lo cambia Tomás. El navegador solo apunta en el rastro con la colección de una pantalla que ve (o «app»), sin nombrar almacenes privados; `anula_a` no numérico → 400. Cabecera `Server: RO`. Las negativas a arrancar van antes de la foto y la base. La recarga pendiente se toma con un UPDATE condicional. Access: un `kid` desconocido recarga las claves como mucho una vez por minuto y un fallo de red no tumba la petición.
- **Pruebas.** `pruebas_seguridad.py → ronda16` (55 comprobaciones que fallaban antes del arreglo) y la del ancla a la hora real, a las 00:30 y a las 01:59. `pruebas_noche.py` copia también `fuentes_objetivos` (sin él, el caso «Meta con todas las cuentas en error» no llegaba a correr).

## V2-E (3-oct · lo común): fechas, plural, cabecera, periodo y menú — contrato compatible

### Fechas: una sola vara
«Hoy», «ayer», «vencida», «esta semana» y «último laborable» significan **lo mismo en toda la app**: el calendario de la agencia **en hora de Madrid**, aunque el Mac o la persona estén en otra zona (Tomás en Bali, accounts en Argentina). Es la misma regla que ya usa el servidor (`servir.hoy()`, ronda 16).
- En un módulo: `ctx.hoy` (texto) y `ctx.fechas` (funciones). Fuera de un módulo: `import { fechas, fechasDe, hoyMadrid } from './componentes.js'`.
- **Prohibido** calcular «hoy» con `new Date().toISOString().slice(0, 10)` (es UTC: de 00:00 a 02:00 en Madrid da AYER), con `new Date()` + `getDate()` (zona del Mac) o con el `hoy`/`generado` de un JSON de datos (eso es el día en que se LEYÓ la fuente, no hoy).
- **Vencida** = su día es anterior a hoy (`fechas.vencida(t)`): lo que vencía ayer ya está vencido; lo que vence hoy, no (va en «para hoy»). Un filtro «Para hoy» no lleva vencidas: si las quiere, se llama «Hoy y vencidas».
- **Esta semana** = de lunes a domingo de la semana de hoy (`fechas.semana()`, `fechas.estaSemana(t)`).
- **«Ayer» de las horas imputadas** = `fechas.ultimoLaborable()` (sábado 3 → viernes 2), nunca «el día de antes» a secas.
- **Si los datos no son de hoy, se dice**: `ctx.diaDatos()` → «datos de ayer (vie 2)». Nada de «Reuniones de hoy» con las del viernes un sábado: «Reuniones del vie 2 · datos de ayer».
- Las fechas de los datos sin zona («2026-10-02 23:14») ya están en hora de Madrid: `fechas.dia()` toma su día tal cual. Las ISO con zona («…T20:39:35Z») se pasan a Madrid.
- Texto relativo común: `fechas.relativo(t)` → «hoy», «ayer», «mañana», «el vie 2» (±6 días) o «28-sep». Antigüedad: `fmt.antiguedad(h)` → «5 h» hasta 48 h y luego «3 días» (nunca «478 h»). `fmt.hace(t)` ya cuenta por días de Madrid.
- **Pruebas:** `?hoy=AAAA-MM-DD` (solo en 127.0.0.1/localhost) fija el «hoy» de todas las pantallas para probar un lunes o un fin de mes; en el servidor, `RO_RELOJ`.

### Plural común
`fmt.plural(n, 'cita')` (o `ctx.plural`) forma el plural solo (cita → citas, mes → meses, acción → acciones, vez → veces) y nunca dice «1 citas». Además, la carcasa corrige al pintar «1 correos», «1 leads», «hace 1 días», «1 cambios bruscos»… (lista en `componentes.js → SINGULAR`), pero eso es la red: escribe bien desde el módulo.

### Cabecera, periodo y menú
- **Cabecera a 390:** «Datos guardados a las HH:MM» solo sale en pantallas de más de 720 px; el título nunca baja de 64 px y nada de la cabecera ensancha la página (antes medía 425 px).
- **Periodo común:** hasta 1.180 px es **un botón** («Este mes · frente al anterior ▾», 40 px de alto) que abre periodos, comparación, «A medida» y «Con datos» en un menú. En ancho, lo de siempre. El módulo no cambia nada (sigue leyendo `ctx.periodo`).
- **Menú:** bajo el logo sale el **puesto real** de quien mira (antes «Operaciones» para todos). «En rojo» cuenta los críticos de la verdad única (la misma cifra que el título de En rojo; la etiqueta dice además cuántos son de tu cartera); sin verdad única no se pinta número. «Mis clientes» va **al final** del menú, con los críticos de la verdad única en su cabecera, 5 a la vista (los más graves primero) y «Ver los N».
- **Departamentos:** nunca el id interno a la vista. `nombreDepartamento(id)` («administracion» → «Administración», «rrhh» → «RRHH»); la carcasa cambia además «administracion · …» al principio de un texto y `estadoVacio({ quien: 'rrhh' })` dice «RRHH».
- **Catálogo (`fichaCatalogo`, «¿Qué es?»):** sin códigos de obra (D-58, C-G1-15, SOP-TR-02, «07 §1») y con los enlaces Markdown convertidos en enlaces cortos («Ziflow ↗»); el texto largo se parte y no ensancha la tarjeta.
- **Zonas de toque en el móvil (≤ 900 px o táctil):** enlaces de ticket «RO-1234» y enlaces dentro de «¿Qué es?» crecen a 32 px sin mover la línea; etiquetas con casilla (`label.chip`, `label > input[type=checkbox]`) de 32 px; casillas de 20 px; opciones de menús flotantes y pestañas de 40 px. Una casilla suelta sin `<label>` alrededor no llega a 32 px: envuélvela en una etiqueta.

### Páginas largas en el móvil: plegado común (V2-E, 40_A M17)
- `plegadoMovil(seccion, { titulo, resumen })` envuelve UNA sección secundaria: en el móvil (≤ 640 px) sale como una fila plegada con su título y una línea de resumen (por defecto, el subtítulo del panel) y se abre con un toque; en ancho sale tal cual, abierta y sin la fila.
- `plegarSecundarias(raiz, { desde = 2 })` o `plegarSecundarias(raiz, { titulos: /^(Por año|Por account)/ })` lo aplica a los paneles de una pantalla: a partir del n.º `desde` o los que casan con `titulos`. **Solo actúa en el móvil.** Llámalo al final del pintado y en cada pestaña que se pinte después.
- **Nunca se pliega** lo que pide acción: «Lo primero», el número que manda, impagos, altas sin facturar, devueltos, alertas. Sí: históricos, gráficos de meses, rankings, desgloses, «Todavía no se mide», fiabilidad.
- Ya lo usan Finanzas (Cobros de Sofía por título; las pestañas de Tomás desde la 3.ª sección), Panel de dirección (cada pestaña del informe, desde la 3.ª) y Dinero por cliente (gráfico, los 10 que más dejan, por account, fase 2).

## Mi perfil (3-oct · zona horaria de cada persona): contrato compatible
Encargo de Tomás: «que el equipo pueda actualizar su timezone».
- **Pantalla** `#/mi-perfil` (la tuya) y `#/mi-perfil/<persona>` (`modulos/mi_perfil.js`, grupo «Perfil», fuera del menú principal). Se llega desde el menú del avatar («Mi perfil y zona horaria», con tu ciudad y tu hora; `carcasa.js`) y con ⌘K. Arriba: «Tu hora ahora: 21:14 (Caracas) · Madrid: 03:14 del sáb 4». Lista corta de las zonas reales del equipo (Madrid, Canarias, Caracas, Bogotá, Buenos Aires, Ciudad de México, Lima, Santiago, Montevideo, Asunción, Santo Domingo, Bali) con la hora de cada una y buscador de todas las zonas IANA. Debajo: tu resumen diario (hora y canales silenciados de N15, con enlace a Chat del equipo para cambiarlos), «Qué cambia con la zona», tu equipo (jefes, Mili y Tomás: zona y hora ahora de cada uno) y los últimos cambios de zona.
- **Quién** (`reglas_permisos.json → zona_horaria`): cada persona cambia la suya; la de otra, su jefe directo, Mili (operaciones) y Tomás. A una persona con puesto de mando (`puestos_solo_tomas`) solo se la cambia Tomás (ella la suya sí). Cecilia (RRHH) ve perfiles, no los cambia. En «ver como» no se escribe (403) y la pantalla lo dice.
- **Servidor** (lógica en `altas_personas.py`, rutas mínimas en `servir.py`): `GET /api/perfil?id=` → `{ persona, propia, puede, motivo, zonas_equipo, todas, resumen, equipo, cambios, solo_lectura }`; `POST /api/perfil/zona { id?, zona }`. Guarda en `historial` (`personas · cambiar`: zona, país si se sabe, `zona_fuente` «Mi perfil (ella misma | su jefe | operaciones | dirección)»), rastro `zona_cambiada` (solo del servidor: está en `rastro_solo_servidor`) y recarga en el servidor **solo** lo de esa persona (V3a, recarga parcial). Ajustes › Altas y bajas acepta ya cualquier zona IANA y su desplegable trae las zonas que tiene alguien (antes, una zona fuera de la lista se habría cambiado sin querer al guardar otro dato).
- **Se aplica al momento:** la pantalla pone la zona nueva en lo que la carcasa tiene en memoria (`ctx.zona(id)`, `ctx.datos.personas`, la persona de la sesión), lanza `ro:avisos` (la campana pide de nuevo el resumen) y el servidor pone a cero el reloj de resúmenes de `avisos.py`. Al regenerar, `build_data.py` (vía `fusionar_altas_app`) lleva la última zona del historial a `data/personas.json`, así que `generar_horas.py` cuenta el día de cada registro con la zona nueva.
- **Qué cambia con la zona de la persona:** lo que se le ENSEÑA en su hora (`ctx.fechasDe(ctx.zona())`: su reloj, «a las 9 de tu mañana»), la hora a la que le llega el resumen diario de la campana (su `hora_resumen` en su zona) y el día de trabajo de sus registros en Horas (y el «Tu zona» de Horas).
- **Qué NO cambia (V2-E):** «hoy», «ayer», vencida, «esta semana», último laborable, plazos de alertas, informes del día 5, cierres de mes, el mes y los totales de horas (como ClickUp), la hora de los datos y las del rastro: todo sigue el calendario de la agencia en Madrid (`ctx.hoy`, `ctx.fechas`). Nunca uses `fechasDe(zona)` para decidir si algo vence.
- **Para Personas:** `import { lineaZona, relojTexto, ciudad } from './mi_perfil.js'` → `lineaZona(ctx, pid)` pinta «Caracas · 21:14 ahora». **Desde V3a Personas la enseña** en la ficha de cada uno (con «Cambiar mi zona» / «Ver su zona») y en la columna «Persona» de las tablas del equipo (Carga, Quién no imputa).
- **Pruebas:** `pruebas_seguridad.py → mi_perfil` (propia sí, otra no, jefe sí, Mili sí salvo mando, Tomás sí, «ver como» no, rastro e historial). Capturas en `capturas/_perfil/`.

## V3a (3-oct): «Lo mío» a cualquier ancho, títulos de tarjeta a 390, zona en Personas y guardado rápido — contrato compatible
- **Chip largo de una fila** (`listaLoPrimero`, p. ej. «Vencido hace 5 h · te ha llegado escalada» en «Lo mío»): parte línea dentro de la tarjeta a cualquier ancho (antes `nowrap`: se salía a ~706 y a 390 px). Solo CSS (`.primero .det .chip`).
- **Tarjeta pequeña (`tile`) a ≤ 640 px:** el icono va arriba (a la izquierda de la «i») y el título debajo a todo el ancho, en 2 líneas y sin elipsis («Reuniones por confirmar»). El módulo no cambia nada.
- **Personas:** zona y hora local de cada persona con `lineaZona` (ficha y tablas del equipo). La zona solo enseña la hora; vencidas y plazos siguen en Madrid.
- **Guardar en Ajustes, Altas y bajas o Mi perfil = recarga parcial** (`Estado.recargar_personas()` en `servir.py`): no vuelve a pasar la puerta de secretos por todo `data/` (≈ 6 s, lo que hacía tardar ~4 s cada «Guardar») ni relee módulos; relee personas, asignaciones, clientes y para_confirmar, reaplica el historial y siembra las tablas. **Seguridad antes que velocidad:** la versión de la base sube y la memoria de recortes se vacía entera (barato), así ningún recorte ni ETag anterior se vuelve a servir (`pruebas_seguridad › R14`). Si algún fichero del núcleo cambió en disco, hace la carga entera. Cambio de zona: ~20-30 ms (antes ~4 s). La recarga de datos (Mili y Tomás) y el arranque siguen haciendo la entera.
- **Tapado:** `servir.limpiar_texto()` usa `RX_CLAVE_ES` y `parece_clave` de `fuentes_chat_equipo/tapado.py`; la expresión propia queda de respaldo.
- **Barrido:** `despliegue/barrido_total.py` mira también 768 y 700 px (pestañas, periodo, «Más» y plegables siguen a 1440 y 390) y, en cada pantalla y ancho, **abre cada desplegable** y falla con `desplegable_recortado`, `desplegable_sin_scroll` o `desplegable_no_cierra`.

### Desplegables: capa por encima de todo (V3a, encargo de Tomás)
- **Todos** los desplegables comunes (`selectorCliente`/`selectorPersona`, `menuElegir` y filtros de `tablaDensa`, `menuMas`, «Más periodos» y el botón de periodo del móvil, el menú del avatar y los «⋯» con `<details>` + `.menu-flot` de los módulos) se abren como **capa** (`capaFlotante()` de `componentes.js`): capa superior del navegador (popover; si no, `fixed` con z-index 1000), fuera de cualquier `overflow` de su tarjeta. Debajo del botón o encima si abajo no cabe; nunca se sale por los lados; altura máxima = el sitio que hay, con scroll dentro y el buscador fijo arriba. A ≤ 640 px, **hoja inferior** a todo lo ancho con velo (tocar el velo cierra sin pulsar lo de debajo). Se cierra al elegir, al pulsar fuera y con Esc (también con el foco en el botón); ↑ ↓ Inicio Fin recorren las opciones; el foco vuelve al botón.
- **Nada que hacer en un módulo:** `vigilarCapas()` lo aplica solo a `.menu-flot`, `.selcli > .pop` y `#yo-pop` en cuanto aparecen. Un menú que deba quedarse en línea lleva `style: { position: 'static' }` (como el «⋯» de CRM). Un desplegable propio nuevo: usa las piezas comunes o llama a `capaFlotante(el, boton, { derecha, cerrar })` tras meterlo en el DOM.
- Comprobado con Playwright como tomas, mili, lucia, valeria y setter_ana a 1440, 1024, 768, 700 y 390 (capturas antes/después en `capturas/_v3a/desplegables/`).

### Detalle fino (44) en lo común
- **Glosario:** el nivel se llama **Crítico · Atención · Bien**; «cliente crítico», nunca «en crítico» (la carcasa corrige «clientes en crítico» y «3 en crítico»); un `chipEstado('ambar', '…crítico…')` sale en rojo. «Nada urgente hoy» → «Nada crítico hoy».
- **Mayúsculas:** solo en cabeceras «eyebrow» (tablas, separadores); los nombres propios (Desk, LinkedIn, Mili, Tomás, alias del equipo…) se envuelven en `.propio` y van como se escriben.
- **Fechas:** un solo formato: «2-oct», «2-oct, 17:34», «1-dic-2025»; «sep» siempre (la red cambia «sept.», «sept» y «2 oct» → «2-oct»). `fmt.fecha`, `fmt.fechaHora` y `fechaCorta` ya lo dan. «El vie 2» de `fechas.relativo` y `diaDatos` se queda así (contrato V2-E que vigila `pruebas_coherencia`; pasar a «vie 2-oct» es cambiar esa prueba a la vez).
- **Plurales:** «1 indicador que todavía no se puede medir»; la red añade «tickets», el adjetivo suelto («1 vencidas» → «1 vencida») y «1 de 1 tickets» → «1 de 1 ticket».
- **Limpiador de códigos sin huecos:** «llega con W1.» → «llega más adelante.»; «… en G2.» → «….» (app.js y `limpiaTexto`).
- **Textos cortados** con «…» (CSS o line-clamp): la carcasa les pone `title` con el texto entero. El menú no corta «Alertas del departamento» ni el puesto bajo el logo (hasta 2 líneas). El fondo marino del menú llega hasta abajo. Anillo de foco en todo campo (`:focus-visible`). «Saltar al contenido» ya es lo primero al tabular al entrar; al cambiar de pantalla el foco va al contenido.
- **Impresión común (`@media print`):** fuera formularios, buscadores, botones, avisos internos, plegados técnicos y desplegables; cabecera con el logo y el nombre de RO, el título de la pantalla y «Impreso el …» (`#cab-impresion`, app.js); bloques, filas y títulos sin partir; fechas sin cortar.

## Envíos verificados (3-oct · encargo de Tomás «que el sistema nunca esté fallando»): contrato compatible
**Hoy todo en simulación: nada sale.** Detalle, activación y canario en `../46_ENVIOS_VERIFICADOS.md`.
- **Servidor:** `envios.py`, enganchado a `servir.py` como `avisos.py`. Tablas `envios` (clave única por envío = sha256 de la acción) y `envio_pasos` (imborrables, un paso por cambio con su hora). Estados: simulado → pendiente → enviado → confirmado | fallido | rebotado. Un envío nace **solo** de una acción de la cola (`acciones`) de un tipo de `reglas_permisos.json → envios.tipos_envio` (desk/whatsapp/ghl). Destinatario y remitente los pone el servidor (ticket de la Bandeja, grupo del cliente, contacto del CRM; Desk sale de «Marketing Clientes»); el `de`/`para` de la vista previa se ignoran.
- **Rutas:** `GET /api/envios[?estado=&canal=]` (cada uno los suyos; `ven_todos_puestos` = dirección, operaciones, técnico, todos; el texto solo si además abre el cliente; tasas de confirmados 7/30 días, salud y canario), `GET /api/envios/envio?id=`, `POST /api/envios/reintentar { id }` (simulado hasta la activación: paso `reintento_simulado` + rastro `envio_reintento_simulado`, solo del servidor). En «ver como», lo de las dos personas y nada se escribe.
- **Verificador:** `despliegue/verificar_envios.py` = paso `verificar_envios` de `pasos.json` (tras la salud de conexiones). Con un canal activo: manda pendientes, relee el hilo en la herramienta (texto y destinatario), detecta rebotes (48 h), reintenta UNA vez lo seguro mirando antes si ya llegó, y avisa a quien lo mandó y a Agus (#avisos-dirección, copia en #avisos-altas y en el canal del departamento del remitente). Al momento tras cada envío real lo hace `servir.py` solo. `--prueba-e2e` = extremo a extremo con un proveedor simulado sobre una copia de la base (también en `pruebas_noche.py --solo-solidez`).
- **Salud:** conexión `envio_correos` («Envío de correos (Desk)») en `despliegue/salud_conexiones.py` (la define `envios.conexion_salud`, solo lectura): llave de escritura y su permiso, departamento, dirección de envío, firmas y cupo.
- **Activar (solo Tomás):** `data/envios/interruptor.json` (`envios_reales`, canal y `activado_por: "tomas"`) **y** `RO_ENVIOS_REALES=si` en el entorno. Canario: `interruptor.canario` + `data/envios/_privado/canario.json`.
- **Pantalla:** `modulos/envios.js` (`#/envios`, `#/envios/<id>`, grupo Sistema; Tomás, Mili y Agus). Capturas en `capturas/_envios/`. Pruebas: `pruebas_seguridad.py → envios_verificados`.

## Ronda U (3-oct · usabilidad por tareas, `../50_USABILIDAD_POR_TAREAS.md`): dos piezas comunes nuevas — contrato compatible
Principio de Tomás: «la info colocada para que la gente la UTILICE de verdad». Dos ficheros nuevos en `modulos/` (no tocan `componentes.js` ni `estilos.css`, que otros carriles están cambiando). Solo clases comunes y tokens.

### `modulos/_trabajo.js` · molde de pantalla de trabajo (cambio #1)
Regla: la **primera fila accionable a ≤ 300 px** desde arriba del contenido, a 1440 y a 390, sin desplazarse antes del primer clic útil.
- `pantallaTrabajo({ id, filtros, pestanas, lista, detalle, contexto: [nodos], tituloContexto, abiertoContexto, consejo = true })` → `<div data-trabajo>` con la clase común `.dos` (dos columnas desde 901 px; una debajo de otra en el móvil). Izquierda (2/3): `filtros` (franja ≤ 64 px), `pestanas` y **la lista**. Derecha (1/3, `sticky` bajo la cabecera): `detalle` del objeto elegido con su barra de acciones y `contexto` en un plegable «Contexto y cifras» (abierto en ancho, cerrado en el móvil). El consejo de la IA baja a justo después del bloque, plegado. Las tarjetas grandes de cifras, «Cómo se mide» y gráficos van al contexto, nunca encima de la lista.
- `barraAcciones({ titulo, sub, acciones: [nodos], volver: { href, texto } })` → barra de un **detalle** pegada arriba (sticky) con sus verbos («Escalar», «Resolver», «No aplica», «Aprobar»…). Cambio #14: el ciclo de una incidencia, «Guardar nota», «Aprobar» de una decisión… nunca a 1.400 px.
- `franjaCifras([{ etiqueta, valor, estado, activo, alPulsar, titulo }])` → cifras pequeñas que **son los filtros** de la lista (chips con `aria-pressed`).
- `consejoCompacto(raiz, destino)` → el «Qué haría yo hoy aquí» que pone la carcasa se coloca **justo después del hijo de `#main` que contiene a `destino`** y se pliega a una línea, una vez (sin cambiar la preferencia guardada; si la persona lo abre, se queda abierto). **Sigue siendo hijo directo de `#main`**: si se mete dentro de otra caja, la carcasa no lo encuentra y pinta otro (se apilaban; arreglado a las 05:00 del 3-oct). `plegarConsejo(c)` lo pliega sin moverlo (también lo hace `_plegar_consejo.js` de U2). Lo usa `pantallaTrabajo` solo; exportado para maquetas propias.

### `modulos/_deshacer.js` · «Deshacer» en vez de «¿Seguro?» (cambio #4)
- **Acciones internas** (Hecho, Visto, Lo tengo, Reclamado, Aprobar, A revisión, Correcto…): se ven hechas al primer clic y sale «✓ Hecho · Deshacer (8)». A los **8 s** se escribe (`alHacer` → `ctx.accion`/`ctx.api`); «Deshacer» lo anula y no se escribe nada. Si la persona cambia de ruta, cierra o deja la pestaña antes, lo pendiente se escribe en ese momento (`hashchange`, `pagehide`, `visibilitychange`).
- `botonDeshacer({ texto, hecho, alHacer, alAnular, plazo, mini, pri, icono, soloLectura, atajo, titulo })`: el botón en su sitio. `soloLectura` («ver como») lo deja apagado con el motivo.
- `conDeshacer({ mensaje, hacer, optimista, revertir, plazo })`: para filas que **desaparecen** al marcarlas (Lo mío, alertas): `optimista()` la quita, aviso flotante «… · Deshacer», `hacer()` a los 8 s, `revertir()` si se deshace o falla. Un segundo `conDeshacer` escribe el anterior al momento.
- **El «¿Seguro?» (`botonConfirmar`) queda solo** para lo que sale fuera (envíos reales: correo, WhatsApp, GoHighLevel, Desk) o borra. `pendientes()` y `encolarTodo()` para pruebas.
- Adoptado en (carril U1): Mi día, Incidencias, Alertas, En rojo, Decisiones, Personas, Horas, Panel de dirección y Ventas de RO. U2 y U3 lo adoptan en sus pantallas.

### Carril U3 · piezas y datos nuevos (contrato compatible)
- `modulos/_trabajo_ancho.js` · `pantallaAncha({ id, filtros, lista, contexto, tituloContexto })`: el molde a **todo el ancho** para listas que son tablas anchas (Salud del CRM, Captación, SEO y webs, Outreach, Producción, Redes). Arriba franja + pestañas + lista; debajo, plegado, «Contexto y cifras»; el consejo, plegado detrás (`consejoCompacto`). `franjaEnLinea(franja)`: la franja en una sola línea también a 390 (se desliza dentro, la página no).
- `modulos/_bitacora.js` · `bitacoraCuenta(ctx, clienteId, { dias })` y `panelBitacora(ctx, clienteId)`: la bitácora diaria del trafficker («qué cambio hoy», acción interna `bitacora_cuenta` de Captación) para leerla en otras pantallas (ficha, informes). Horas de la cola en UTC → Madrid.
- **Acciones nuevas** (`reglas_permisos.json › acciones_permitidas`): `salud-crm: revisado_lead, revisado_cita` («Revisado · motivo», la fila sale de la lista) · `captacion: bitacora_cuenta, pedido_creatividad` · `redes: hueco_lo_cubro` (vista_previa `{ desde, hasta, dias[] }`). El **pedido de creatividades** se manda como `clickup/tarea` con `vista_previa.pedido_creatividad: true` → `sincronia.py` lo guarda como «crear tarea en la lista del cliente» (simulado) y `avisos.py` lo publica en `#avisos-redes` para producción, redes, publicidad, operaciones y dirección (campo `pedido` en el mensaje; «Ir» → `#/produccion/pedido/<id>`).
- **Marca del cliente en la tarea de Producción:** `fuentes_produccion/generar_marca.py` → `data/produccion/marca.json` (filas con `cliente_id`, recortado por cliente) y `data/produccion/marca/p_<persona>.json` (solo su dueño: los clientes de sus tareas y su cartera, filas con `cli`). Tono y «lo que nunca se dice» del `_MANUAL_VOZ_ESTILO.md` de cada cliente, colores del manual o del logo, carpeta de Drive, última pieza aprobada. `fichaMarca({ cliente, marca, pedidos, tarea, alias })` en `produccion_comun.js`.
- Setters: el resultado se guarda con herramienta `app` (con `ghl` el servidor lo rechazaba con 403: los leads de RO no son de un cliente); las citas pasadas, tipo `resultado`.

## Paneles v4 (3-oct · encargo de Tomás «todo a nivel de dashboards tiene que mejorar»): contrato compatible
Especificación: `../48_BENCHMARK_DASHBOARDS.md` (QuickBooks, Xero, ChartMogul, Pigment, Databox… y las métricas de agencia con fuente). Orden de toda pantalla de dinero: **la cifra que manda arriba · 4-6 tarjetas con su línea de 12 meses, su comparación y su umbral con fuente · lo que pide decisión · el porqué (gráficos) · tablas plegadas al final**. Cada bloque lleva su acción al lado (reclamar, ver cobros, pedir revisión), no solo el dato.

**Componentes nuevos (`componentes.js`, bloque «PANELES V4»; estilos en `estilos.css`, bloque «Paneles v4»; ejemplos en Sistema › Componentes):**
| Componente | Para qué |
|---|---|
| `tarjetaKpi({ icono, etiqueta, valor, num, unidad, estado, mejorSi: 'alto'\|'bajo'\|'neutro', serie, serieX, umbralSerie, comparar, comparaciones: { mes_ant, anio_ant, objetivo: { ref, num?, texto, modo: 'pct'\|'abs'\|'puntos', formato, sinDato } }, umbral: { texto, fuentes: [{ fuente, href }], colorea }, fuente: { texto, href }, nota, contexto, medible, frescura, alPulsar, ir })` | La tarjeta estándar: cifra, minilínea de 12 meses, «▲/▼ contra qué» con el color según la dirección buena, umbral escrito con «Ver fuente ↗» y el dato con su fuente. `colorea: false` = «Referencia, no colorea» (gris). No es un botón entero (lleva enlaces): `alPulsar` pone «ir» al pie |
| `selectorComparar({ clave, alCambiar })` · `COMPARAR_CON` | «Comparar con: Mes anterior · Mismo mes del año pasado · Objetivo o plan» (se recuerda). La pantalla repinta sus tarjetas con `comparar` |
| `lineaComparacion({ num, ref, modo, mejorSi, texto, formato })` | La línea «▲ 12 % frente a julio» suelta (para la cifra que manda: `cifraPrincipal({ comparacion })`) |
| `minilinea(valores, { x, formato, umbral, etiqueta, alto })` | La línea pequeña de tendencia; null con < 2 valores |
| `cascada({ pasos: [{ texto, valor, tipo: 'total'\|'cambio', estado: 'sube'\|'sube2'\|'ambar'\|'baja' }], formato, zoom, anchoFilas = 440 })` | Puente: saldos en gris, sube verde, baja rojo. `zoom: true` = el eje no empieza en 0 (cuota) y lo dice. Por debajo de 440 px, en filas |
| `barrasGanadoPerdido({ x, ganado: [{ nombre, y, clase }], perdido, enCurso, notaCurso, detalle })` | Lo ganado sobre cero, lo perdido bajo cero, línea del neto y el periodo en curso **rayado** (ChartMogul) |
| `mapaCalor({ columnas, vistas: [{ valor, texto, filas: [{ etiqueta, n, valores }], media, nota }], clave })` | Cohortes: filas = mes de alta, columnas = mes 0..N, fila «Media», un solo color (`--calor-1..5`), interruptor % clientes / % cuota; scroll dentro de su caja |
| `barraObjetivo({ valor, objetivo, max, marcas, extra, bandas, colorea, formato })` · `bandasObjetivo()` · `estadoObjetivo()` · `FUENTE_BANDAS` | Bullet: bandas de Databox (< 75 % rojo, 75-99 ámbar, ≥ 100 verde), cifra en barra oscura, objetivo como marca, `extra` en trazo fino («si firman») |
| `previsionCaja({ puntos: [{ fecha, saldo }], minimo, eventos, textoMinimo })` | Caja proyectada con la línea del mínimo y el tramo rojo por debajo (QuickBooks/Xero) |
| `barrasDivergentes({ filas: [{ etiqueta, sub, valor, estado }], formato, alPulsar })` | Ranking con el cero en medio: negativas a la izquierda en rojo |
| `enlaceFuente(href, quien)` | «Quién · Ver fuente ↗» (fuera, en otra pestaña) |
| `barraApilada` | admite `estado: 'rojo-claro'` (tramo 61-90 días) |

**Lo común de los paneles de dinero (`modulos/dinero_v4.js`, no es un módulo):** `FUENTES` (las 21 del 48, abiertas el 3-oct), `UMBRALES` (texto, fuentes y `colorea` por métrica; los de SaaS o sin fuente fiable, `colorea: false`), `ESTADO` (color por métrica con umbral), `fuentesAlPie(claves)` (lista de fuentes al final), `puenteCuota(puente)` (fuga mensual: rebajas, bajas, subidas), `puntosPrevisionCaja({...})` (caja a 90 días con sus supuestos en texto), `notaSupuestos()`, `separador()`, `mesMas()`. **El Panel de dirección y Ventas de RO deben reutilizar esto** (no copiar umbrales).

**Datos nuevos:** `data/dinero_cliente/cohortes.json` ← `fuentes_dinero/generar_cohortes.py` (lo lanza `generar_dinero.py` al terminar; solo lee `direccion.json`): % de clientes y % de la cuota de entrada que siguen por mes de alta (24 filas, mes 0-12, media ponderada). `reglas_permisos.json → datos_de_modulo["dinero_cliente/cohortes"]`: dirección, operaciones y proyectos (`solo_real`). Acciones nuevas en la lista blanca: `revisar_rebajas`, `revisar_rebajas_deshecho` (Finanzas: «Pedir a Mili que lo revise», patrón «Hecho · Deshacer»; cuando exista `modulos/_deshacer.js` del carril U1, pasar a usarlo).

**Retención neta:** fórmula propuesta (cuota de hoy de los clientes que ya estaban hace 12 meses ÷ su cuota de entonces, por trimestres) = el 60,5 % de `kpi.nrr`; en pantalla, **«Fórmula pendiente de confirmar por Tomás»**.

**De paso (lo común, 44 y glosario del coordinador):** I9 `grafico()` pega al borde la primera/última etiqueta de un eje de barras y el SVG nunca es más ancho que su caja (PDF); el texto del umbral se aparta si pisa el valor final. V4 los botones del «Más» de una fila (`.mas-acc`) y los menús flotantes ya no se salen de la tarjeta. Glosario **Crítico · Vigilar · Bien**: `chipEstado('ambar', 'Atención')` sale «Vigilar»; la red de textos cambia «cliente en atención» → «cliente a vigilar», «3 en atención» → «3 a vigilar» y «Crítico, Atención…» → «Crítico, Vigilar…»; el menú «Mis clientes» dice «vigilar». N6: las cabeceras con nombres propios ya salen como se escriben (app.js; comprobado en Incidencias › Traspasos).

## Sincronía con ClickUp (3-oct · encargo de Tomás «que los cambios impacten en ClickUp y se guarden como copia»): contrato compatible
**Hoy todo en simulación: nada se escribe en ClickUp.** Detalle, encendido y chat en `../51_SINCRONIA_Y_CHAT.md`.
- **Servidor:** `sincronia.py`, enganchado a `servir.py` tras `envios.py`. Toda acción de la cola con `herramienta: 'clickup'` crea al momento su cambio en `sinc_cambios` + `sinc_pasos` (imborrables; clave única por acción). Estados: simulado | pendiente → enviado → confirmado | fallido | conflicto → descartado. La tarea y el cambio los pone el servidor (Producción, `revision_piezas`); lo demás del navegador se ignora y se anota. La respuesta de `POST /api/acciones` trae `sincronia: {id, estado, texto, ir}` («Hecho en la app · pendiente de ClickUp»): úsalo en tu pantalla si quieres enseñarlo.
- **Rutas:** `GET /api/sincronia[?canal=&estado=]`, `/api/sincronia/cambio?id=`, `/api/sincronia/objeto?ref=<tarea>` (estado de los cambios de una tarea, para pintar insignias); `POST /api/sincronia/reintentar|elegir {id, gana}|a_mano`.
- **Tubería:** paso `reconciliar_clickup` (`despliegue/reconciliar_clickup.py`): despacha, relee (solo lectura), conflicto, reintentos, informe diario «sin reflejar» en #avisos-altas. `--prueba-e2e` con ClickUp simulado (también en `pruebas_noche.py --solo-solidez`).
- **Interruptor:** `data/sincronia/interruptor.json` (`clickup_real` + `activado_por: "tomas"`) + `RO_CLICKUP_REAL=si` + llave `clickup_token_servicio` (usuario de servicio, nunca la de propietario). Puente de chat (`chat_puente`, `data/sincronia/puente_chat.json`): apagado; enganche en `avisos.py`.
- **Pantalla:** `modulos/envios.js` con pestañas Correos / ClickUp / Chat (`#/envios/clickup[/<id>]`, `#/envios/chat`). Capturas en `capturas/_sincronia/`. Pruebas: `pruebas_seguridad.py → sincronia_clickup`.

## Cerebro de decisiones v2 (3-oct · encargo de Tomás «mejorar el cerebro que alimenta las decisiones»): contrato compatible
Diseño completo, árbol, reglas por puesto y ejemplos: `../53_CEREBRO_DECISIONES.md`.
- **Dónde vive:** `fuentes_consejos/cerebro_decisiones.py` (orquesta) + `cd_diagnostico.py` (árbol por síntoma), `cd_prioridad.py` (impacto · urgencia · esfuerzo · motivo), `cd_prudencia.py` (nada de precios, plazos ni asesorar al cliente), `cd_aprendizaje.py` (valoraciones, seguimiento a 7/14 días, ajuste por regla, informe semanal). Conocimiento en `fuentes_consejos/conocimiento/`: `reglas.json` (178 reglas con autor, fichero, línea y enlace a GitHub; lo genera `construir_reglas.py` desde `reglas_minadas.json`), `tipos.json` (tipo → tema, esfuerzo, regla) y `puestos.json` (los 21 puestos: foco, pesos, reglas del jefe).
- **Cada consejo trae además** (`/api/ia/consejo`): `prioridad {puntos, impacto{nivel, euros_mes*, cuota*, gravedad}, urgencia, esfuerzo, aprendizaje_pts}`, `motivo_orden` y `motivo_linea` («Primero porque…»), `criterio {id, regla, autor, url (GitHub), fichero}`, `evidencia [{dato, fecha, fuente, url}]`, `confianza` (alta/media/baja) + `confianza_porque`, `diagnostico {sintoma, causa, camino}` si aplica, `metrica`, `valoracion`. *Solo si quien lee ve la cuota de ese cliente (sin cliente: dirección, finanzas, operaciones, administración y ventas de RO).
- **Rutas nuevas (ia.py):** `POST /api/ia/consejo/valorar {consejo, valor: util|no_util|hecho, pantalla}` (el servidor busca el consejo entre los de esa persona y apunta `consejo_valorado` con su métrica; nunca en «ver como»; `consejo_valorado` está en `rastro_solo_servidor`); `GET /api/ia/consejo/informe` (solo dirección, persona real). El copiloto sin clave sale **por reglas** (`origen: "reglas"`, diagnóstico en 3 líneas, 3 acciones, `arbol`).
- **Contrato para «Lo mío» (carril U1):** `data/prioridades/p_<id>.json` (`datos_de_modulo["prioridades/p_*"]`, `solo_propio`, módulo `mi-dia`) = `{orden, por_alerta{id_alerta: P}, por_cliente{cliente_id: P}, por_objeto{"#/…": P}}`, P = `{puntos, nivel, urgencia, dias_retraso, esfuerzo_min, motivo, confianza, regla, criterio_url, delegado, euros_mes*}`. Ordenar por `puntos` desc.
- **Tubería:** `fuentes_consejos/generar_consejos.py` (después de alertas y verdad) ahora: evalúa el aprendizaje → `data/consejos/_privado/{aprendizaje.json, informe_semanal.json, informe_semanal.md}`, escribe consejos y prioridades, y guarda la foto diaria `data/consejos/_privado/historia/AAAA-MM-DD.json`.
- **Componente:** `modulos/ia_componentes.js` solo añade la fila de valoración bajo cada consejo (motivo, «Criterio … · Ver fuente ↗», confianza, «Útil / No útil / Ya hecho»).
- **Pruebas:** `fuentes_ia/probar_ia.py` sección 11 → `fuentes_consejos/probar_cerebro.py`; navegador: `fuentes_consejos/capturar_cerebro.py --puerto 9265` (capturas en `capturas/_cerebro/`).

## Vigía y copias (3-oct · encargo de Tomás «que siempre haya un validador de que todo funciona»)
- **Vigía:** `despliegue/vigia.py` cada 10 min, aparte de la tubería: 27 conexiones (lectura barata; la llave de GHL que rota no se usa) + la app por dentro (app web, tubería, envíos, ClickUp, IA en %, disco, base, copia) con 24 h de historia → `data/vigia/estado.json`. Pantalla **«Salud del sistema»** (`modulos/ajustes_conexiones.js`, `#/conexiones` y Ajustes; Agus, Mili y Tomás) por `GET /api/vigia`; «Probar ahora» de una fila = `POST /api/vigia/probar {id}` (regla `probar_conexiones`). Avisos agrupados en #avisos-altas: cae → Agus; > 1 h → Mili y Tomás; vuelve → recuperación. Local: `python3 despliegue/vigia.py --bucle` (lo arranca quien decida Tomás); servidor: tarea de Coolify cada 10 min (`despliegue/DESPLIEGUE.md`). Simulacro sobre una copia: `--prueba`. Capturas en `capturas/_salud/`.
- **Tabla de avisos de la tubería:** `tuberia_avisos` (en `tuberia.db` y en Postgres, F2.1, 5-oct-2026); antes se llamaba `avisos` y chocaba con la `avisos` de la app (`servir.py`, E0). No es la misma tabla.
- **Copias:** `despliegue/copia_seguridad.py` (paso `copia_seguridad` de la tubería, una vez al día): local.db y tuberia.db con la API de copia de SQLite, verificadas (integridad y filas, también tras comprimir), en `despliegue/estado/copias/AAAA-MM-DD/` con `manifiesto.json`; 7 diarias + 4 semanales, tope 800 MB, nunca con menos de 1 GB libre; R2 apagado hasta `RO_COPIA_R2=si` con su llave. `--estado` y `--restaurar <día> <destino>`.

## Avisos automáticos (3-oct · encargo de Tomás «que en el chat de la app estén todas [las automatizaciones]»): contrato compatible
**Nada sale de la app:** los avisos se publican en los canales de avisos (avisos.py) y en la campana; no se escribe en ClickUp ni en ninguna herramienta. Inventario de lo que había (90 días, solo lectura) en `../54_AUTOMATIZACIONES_INVENTARIO.md` y `data/avisos_programados/inventario.json`; lo que conviene apagar fuera queda como recomendación para Tomás en cada regla (`apagar_en_origen`).
- **Servidor:** `avisos_programados.py`, enganchado a `servir.py` justo después de `avisos.py`. Reglas en `data/avisos_programados/reglas.json` (11: horas de ayer, semáforo del lunes, cómo va el semáforo, informe mensual, cierre de facturación a Sofía, resumen de publicidad, resumen semanal a dirección, tareas vencidas, arranque de clientes nuevos, aviso del cierre semanal y factura del equipo; `no_se_hace_aun` = lo del inventario que aún no puede hacer y por qué). Cada regla: `tipo` (generador), canal, a quién, `cuando` (días, hora, `zona: persona|madrid`, ventana), umbrales editables, texto con `{…}`, botones, escalado. Para añadir un tipo: una función `gen_<tipo>(r, t, con)` → envíos (+ `sigue_<tipo>` si escala) en `GENERADORES`.
- **Reloj:** hilo del servidor cada 2 min (`RO_AVISOS_SIN_BUCLE` lo apaga); `RO_RELOJ` lo fija (avisos.py también lo respeta ahora). Clave única por regla, persona y día: nunca repite. Solo avisa si hace falta (el dato dice que falta); si el dato no cubre ese día, no avisa («sin dato» en la vista previa). Escalado: pasadas `tras_horas`, si el dato dice que sigue y nadie pulsó «Ya lo he hecho», menciona a quien sube (en el hilo si ve el canal; si no, en el suyo).
- **Permisos:** recordatorio personal con `ver = {"personas": [persona, jefa]}` (nuevo en `Vista.ve_fila` de avisos.py; en «ver como», lo de las dos); dinero solo a canales de quien lo ve y sin importes. Cambian reglas la jefa del departamento (`departamentos.json`: jefe o dueña fija) y Mili y Tomás; tablas `avisos_prog_cambios` y `avisos_prog_hechos` imborrables + rastro (`aviso_programado_cambio`, `aviso_programado_hecho`, `avisos_programados*`: solo del servidor).
- **Rutas:** `GET /api/avisos_programados`, `/vista_previa?id=`; `POST /cambiar {id, campo: activa|hora|umbral.<k>|escalado_horas, valor}`, `/hecho {regla, objetivo, dia}`, `/ejecutar` (Mili y Tomás).
- **Botones en los mensajes:** `datos.botones` (`[{texto, ir: '#/…'} | {texto, url: 'https://…'}]`, hasta 5) → `botones` en `fila_a_json`; `chat_equipo.js` los pinta en los eventos (si no hay, el «Abrir el mensaje» de siempre) y respeta los saltos de línea.
- **Pantalla:** `modulos/ajustes_avisos.js` (`#/avisos-automaticos`, grupo Sistema; todos ven lo que les llega, las jefas editan lo suyo; «Ver cómo quedaría»; inventario para Mili y Tomás; `#/avisos-automaticos/hecho/<regla>/<persona>/<dia>`). Capturas en `capturas/_avisos_auto/`. Pruebas: `pruebas_seguridad.py → avisos_automaticos` (37, con relojes fijados). Sin servidor: `python3 avisos_programados.py --simular --reloj 2026-10-05T09:00`.

---

## Piezas comunes · índice rápido (3-oct)
Antes de escribir algo propio en un módulo, mira si ya existe aquí. Detalle de cada una en su ronda (más arriba).
| Pieza | Para qué |
|---|---|
| `componentes.js` | Todos los componentes (tablas, tarjetas, chips, gráficos, paneles v4, `capaFlotante`, `botonConfirmar`…), documentados en el propio fichero; ejemplos vivos en Sistema › Componentes |
| `capaFlotante(el, ancla, { derecha, cerrar })` | Todo desplegable se abre como capa por encima de todo (hoja inferior a ≤ 640 px); `vigilarCapas()` lo aplica solo |
| `modulos/_trabajo.js` · `_trabajo_ancho.js` | Molde de pantalla de trabajo: primera fila accionable a ≤ 300 px; lista + detalle + «Contexto y cifras» plegado |
| `modulos/_deshacer.js` | «Hecho · Deshacer (8)» en vez de «¿Seguro?» para lo interno; el «¿Seguro?» solo para lo que sale fuera o borra |
| `modulos/_bitacora.js` | Bitácora diaria del trafficker para leerla en ficha e informes |
| `modulos/_ir.js` | Abrir una ruta profunda y resaltar el objeto exacto (pestaña, «Ver más», foco) |
| `modulos/_legible.js` | Textos de datos en claro: tickets de Desk como enlace, sin códigos internos, «Yessica» |
| `modulos/_plegar_consejo.js` | Pliega el «Qué haría yo hoy aquí» sin moverlo |
| `modulos/_telefono.js` (+ `telefono.py`) | Regla común de teléfonos (ver más abajo; en curso) |
| `modulos/_modular.js` | Estado de la web (Modular) en ficha y tablero de webs |
| Paneles v4 + `modulos/dinero_v4.js` | Tarjeta KPI con línea de 12 meses, comparación y umbral con fuente; fuentes y umbrales comunes de dinero |
| `ayudas.js` | Buscador ⌘K / Ctrl K / «/» que busca dentro y hace cosas, contadores del menú, «Mis clientes», «Algo va mal / Tengo una idea» y atajos |

## IA con topes (3-oct) · `ia.py` + `ia_gasto.py`
- **Hoy no hay clave:** la IA sirve lo precalculado y los consejos por reglas; **gasto 0 €**. Con clave, usa la API de Anthropic con clave de la Console (una suscripción Max no vale para la app: `../52_IA_COSTE_Y_TOPES.md`).
- **Topes:** 150 €/mes y 10 €/día por defecto (los fija Tomás en Sistema › Gasto de IA, `#/gasto-ia`, solo él), 2 €/persona/día, tope por función y 40 generaciones/hora/persona. Antes de cada llamada se reserva su peor caso; si no cabe, no sale. Aviso al 80 % en #avisos-dirección; al 100 %, **modo reglas** solo (vuelve al día siguiente o el día 1). «Ver como» nunca gasta.
- Modelo por tarea (Haiku para consejos, Opus para borradores, Sonnet para el copiloto), caché de prompts, lote nocturno a mitad de precio (`fuentes_ia/lote_nocturno.py`), llave de respaldo solo ante caída.
- **Aviso del 55:** con estos topes solo cabe el paquete «Básico» (~113 €/mes); el «Recomendado» pediría 420 €/mes y 22 €/día. Lo decide Tomás.
- Pruebas: `fuentes_ia/probar_ia.py` (incluye `probar_gasto.py` y `fuentes_consejos/probar_cerebro.py`). Detalle en `_ESTADO_ia.md`.

## Cerebro de respuestas de correo (3-oct)
`fuentes_ia/cerebro_respuestas/cerebro.py`: clasifica el correo (13 tipos), saca las preguntas del cliente, aplica la guía y la longitud de ese tipo (medidas en Desk) y pone una **nota de calidad 0-100** con «Lo que falta» antes de enseñar el borrador. Nada se envía. Ejemplos anonimizados en `ejemplos.json`. Diseño en `../49_CEREBRO_RESPUESTAS.md`; el cerebro de decisiones v2, más arriba.

## Modular (3-oct) · ficha + tablero de webs
Conectado en **solo lectura** (última pasada 3-oct 06:16: 29 webs con cliente, 34 en el tablero). Bloque «Estado de la web (Modular)» en la ficha del cliente y pestaña «Webs» en SEO, ficha y webs. 4 reglas de alerta en N4: web caída, copia atrasada o ninguna, vulnerabilidad crítica y certificado a < 15 días. **«Entrar al WordPress» de un clic: apagado** (la clave es de solo lectura). Detalle en `_ESTADO_modular.md`.

## Hostinger (3-oct)
Lector construido (`fuentes_hostinger/generar_hostinger.py`, paso `hostinger` de la tubería; alertas por `de_hostinger`) y probado con datos inventados (`--simulado`). **Falta el token** (lo crea Tomás): hoy `data/hostinger/hostinger.json` dice «sin conectar». Detalle en `_ESTADO_hostinger.md`.

## Google Business Profile y teléfonos (3-oct) · **en curso**
Otros carriles los están terminando mientras se escribe esto; cuando cierren, tendrán su propio `_ESTADO`.
- **Ficha de Google:** `fuentes_gbp/generar_gbp.py` (solo lectura; paso `gbp` de la tubería) y `fuentes_gbp/servidor_gbp.py` («Proponer respuesta» a reseñas con el cerebro de reseñas y nota de calidad; «Responder» queda en la cola **en simulación**; interruptor `data/gbp/interruptor.json` apagado y el publicador real no está construido). Hoy «pendiente de aprobación» de Google. Emparejamientos a mano en `fuentes_gbp/emparejar.json`.
- **Teléfonos:** `telefono.py` y su gemelo `modulos/_telefono.js`: se guardan con prefijo internacional y sin espacios (`+34` + 9 cifras), la extensión en su campo, se enseñan con espacios y lo dudoso no se guarda. Por qué: Zadarma pone el 34 delante si falta el «+» (26 llamadas fallidas en 90 días). `python3 telefono.py --probar`. Pendiente: aplicarlo en todas las pantallas que guardan o enseñan teléfonos.

## Baterías de prueba · cómo lanzarlas
Todas en 127.0.0.1 y, las que escriben, sobre una **copia** de la base. Antes de un cambio grande, como mínimo las cuatro primeras.
```bash
python3 escaner_secretos.py --proyecto        # puerta de secretos sobre todo el texto (los _privado se cuentan aparte)
python3 pruebas_seguridad.py                  # permisos, recortes, envíos, sincronía, avisos automáticos… (arranca su servidor, puertos 8920-8929)
python3 pruebas_coherencia.py                 # cifras y textos coherentes entre módulos (solo lee ficheros)
python3 pruebas_diseno.py --estricto          # ningún módulo se sale de la guía visual
python3 pruebas_e0.py --puerto 8770           # aceptación de E0 contra servir.py ya arrancado
python3 despliegue/pruebas_noche.py           # la de cada noche (su propio servidor y copia); --solo-solidez = envíos y ClickUp extremo a extremo
python3 despliegue/barrido_total.py --vuelta vN --personas lucia,tomas   # recorrido en navegador por personas y anchos
python3 fuentes_ia/probar_ia.py               # IA, gasto y cerebro de decisiones
python3 fuentes_bandeja/probar_bandeja.py     # Bandeja
python3 despliegue/verificar_envios.py --prueba-e2e      # envíos con proveedor simulado
python3 despliegue/reconciliar_clickup.py --prueba-e2e   # ClickUp simulado (36 casos)
python3 despliegue/vigia.py --prueba          # simulacro de caídas sobre una copia
python3 avisos_programados.py --simular --reloj 2026-10-05T09:00   # avisos programados sin servidor
python3 telefono.py --probar                  # regla de teléfonos
```

## Qué no se sube a GitHub
El repositorio lleva solo código, reglas y documentación. Fuera (`.gitignore`): `data/` entera salvo `data/mi_dia/config.json`, `data/departamentos.json` y `data/envios/interruptor.json`; `historia/`, `capturas/`, `*.db`, `_privado/`, `_cache/`, `_crudo/`, `despliegue/estado/` (copias de la base), `.env` y copias `*.antes*`. Las llaves viven en el llavero del Mac o en los secretos del servidor, nunca en el repositorio. Los datos se regeneran con la tubería.

## Lo que solo puede hacer Tomás
Nada de esto lo hace un agente ni nadie del equipo sin su sí por escrito.
1. **Activar envíos reales** (correo de Desk, WhatsApp, GoHighLevel): `data/envios/interruptor.json` con `activado_por: "tomas"` + `RO_ENVIOS_REALES=si`; y elegir el buzón del canario.
2. **Activar ClickUp real:** `data/sincronia/interruptor.json` + `RO_CLICKUP_REAL=si` + llave de un usuario de servicio (`clickup_token_servicio`); decidir si se enciende el puente de chat.
3. **IA:** crear los dos espacios en la Console de Anthropic con su límite de gasto, pegar las claves (`bash fuentes_ia/pegar.sh`) y fijar los topes (o subirlos si elige otro paquete del 55).
4. **Hostinger:** crear el token con caducidad en hPanel y `bash ~/RO_HERRAMIENTAS/hostinger/pegar.sh`.
5. **Google Business Profile:** que Google apruebe el proyecto y ejecutar `~/RO_HERRAMIENTAS/google/gbp.py instalar`.
6. **Modular · acceso de un clic:** interruptor `data/modular/interruptor.json` + `RO_MODULAR_ACCESO=si` + clave aparte con permiso de entrada (`modulards_acceso_key`).
7. **Copias fuera del Mac:** `RO_COPIA_R2=si` con su llave de R2.
8. **Vigía:** decidir quién y dónde arranca `python3 despliegue/vigia.py --bucle` (o la tarea de Coolify cada 10 min).
9. **Puestos sensibles:** dar o quitar dirección, finanzas de dirección, RRHH, operaciones, ventas de RO y administración (`puestos_solo_tomas`).
10. **Fórmulas pendientes:** confirmar la fórmula de retención neta (paneles v4) y la de salud del cliente.
11. **Canales:** añadir a Agus a #avisos-dirección.
12. **Despliegue:** publicar la app fuera de este Mac (Cloudflare Access, Worker, base en la nube); hoy solo corre en 127.0.0.1.

## Flecos del 3-oct (revisión final)

- **Capa E1 en vivo:** cartera, horas, tareas, Desk, reuniones y alarmas de `data/clientes/<id>.json` salen de los módulos (verdad única, Producción, Bandeja, Reuniones y Alertas) con `fuentes/f_vivo.py`; cada bloque lleva `origen` y, si algún campo aún es del panel de Mili, `del_panel {campos, hora}`. Detalle en `fuentes/FORMATO.md`.
- **Bandeja · hilos para todos:** `fuentes_bandeja/generar_hilos.py --desk` lee de Desk (solo lectura) los hilos de todos los correos abiertos con caché por ticket (`fuentes_bandeja/_cache_hilos/`, ya limpia: sin correos, teléfonos, credenciales ni pies legales) y tope por vuelta (`--tope 150 --max-llamadas 1500`); solo vuelve a leer un ticket si cambia su último correo o su estado. Sin `--desk` (como lo lanza `generar_bandeja.py`) no usa la red.
- **Envíos:** el servidor rechaza con 400 y motivo llano cualquier envío (acción de un tipo de `tipos_envio`) cuyo texto o asunto lleve `[completar…]`, `[…]` o `[...]` sin rellenar (`envios.py → hueco_sin_rellenar`).
- **Mi día:** un correo cuenta como despachado solo con respuesta, cierre, «no aplica», despachado, llamada devuelta o «esperando al cliente» (la regla de la Bandeja); una nota, tarea, aviso o asignación no lo saca.
- **`pruebas_seguridad.py`:** cada servidor de prueba arranca con `arrancar()` (puerto del rango con SO_REUSEADDR, espera hasta 150 s y comprueba con `lsof` que quien escucha es su propio proceso); nada sale ya del rango de `RO_PUERTOS_PRUEBA`.

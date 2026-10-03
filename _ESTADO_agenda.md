# _ESTADO · M23 Agenda (2-oct-2026)

## Ronda 3 (2-oct noche) · fallos de las auditorías → qué se ha hecho

| Fallo (auditoría) | Estado |
|---|---|
| F-04 (29): un 403 se disfrazaba de «sin datos» | **Arreglado**: 403 → «No puedo leer tu agenda ahora mismo. Recarga en un minuto…» con botón Recargar; otro error → «La agenda no ha cargado». |
| F-05 (29): «Lo arregla: Tomás (regenerar con fuentes_agenda/generar_agenda.py)» a la vista | **Arreglado**: textos humanos, sin ficheros ni códigos (W1, D-xx). |
| 70 (29): nombres escritos a mano («Yessica», «Natalia») | **Arreglado**: todos los nombres de personas con `ctx.nombre(id)`. |
| 26 parte C: faltaban atajos por cita | **Arreglado**: cada cita lleva todos los suyos: Contacto y Calendario en GHL, Evento y Contacto en Zoho CRM, Zoho Bookings, Zoho Calendar (evento exacto) y Grabación de Zoom. |
| Dueño de la cita ve el nombre completo (F-10, común) | **Adaptado**: E0 ya manda el nombre completo al dueño; he añadido la regla para el título (`nombres_dueno` → `titulos`). Quien no es dueño ve iniciales (probado: Tomás sí, Mili ve «C···» en la agenda de Tomás; Tomás pidiendo la de Agus → 403). «Ver nombres» queda solo como respaldo. |
| Verdad única (regla 1 de la ronda) | **Adoptada**: «cliente en rojo» = `gravedad: critico` de `data/verdad/clientes.json` (generador y pantalla con `ctx.verdad`). Agenda añadida a `ADOPTADOS` con su comprobación en `pruebas_coherencia.py`: 0 errores. |
| 27 · RRHH recibía todas las agendas | **Arreglado por E0** (`regla_persona: agenda_persona`). |
| Escáner: 92 «correos» en enlaces de `agenda.json` | **Arreglado**: eran los uid de Zoho Calendar («…@zoho.eu») dentro del enlace; ahora `%40`. `escaner_secretos.py` limpio en mis ficheros. Queda una **copia vieja** en `despliegue/estado/instantaneas/vuelta_1/agenda/` (no es mía: la hizo el despliegue a las 16:27). |
| Bookings y Calendar directos | **Hecho**: Tomás canjeó la llave (17:10). `zbookings.py comprobar` → bookings ok, calendar ok. |
| Iconos repetidos en el menú | No aplica a mi módulo (`ICONO_MODULO` es común: pedido a E0). |

**Agenda regenerada (17:40):** 356 citas de 17 personas: GHL 130 · CRM 86 · Bookings 61 · Calendar 52 · Zoom 27. Las copias de la misma cita (misma persona y misma hora en GHL, Bookings, CRM y Calendar) se juntan en una con todos sus atajos (228), y 14 grabaciones de Zoom se pegan a su cita. Dos citas de la misma herramienta a la misma hora no se juntan (doble reserva).

**Tres citas de Bookings contrastadas con la API** (`zbookings.citas`): #RA-01293 Constanza, 18-sep 11:30-12:15 (Kiosko Box) · #RA-01373 Carla, 21-sep 13:00-13:45 (Oteca) · #RA-01345 Tomás, 18-sep 12:15-13:15 = filas `bk-RA-01293`, `bk-RA-01373` y `bk-RA-01345` de la agenda, con los mismos inicios y fines.

**Pruebas:** 7 personas × 1440 y 390 sin errores de consola (salvo los 403 provocados a propósito) ni desplazamiento horizontal · `pruebas_coherencia.py` 0 errores · `pruebas_e0.py` 1 fallo ajeno (escáner sobre `data/personas.json`, común). Capturas nuevas: `capturas/agenda/r3_*`.

**Límites que quedan:** el enlace de Bookings abre Zoho Bookings, no la cita exacta (la API no da la ruta de administración de una cita; la de «resumen» es la del cliente y permite cancelar, así que no se usa) · Calendar es solo el de Tomás (la llave es suya) · Zoom programado sigue sin permiso `meeting:read:list_meetings:admin` · Zoho limita las llaves seguidas: el lector usa una sola por pasada.

---


**Hecho.** `modulos/agenda.js` (ruta `#/agenda`, grupo «Hoy»), datos con `fuentes_agenda/generar_agenda.py`, lector preparado `~/RO_HERRAMIENTAS/zoho/zbookings.py`.

## Qué hace
- **Arriba (cada día):** de quién es la agenda (Mi agenda + su equipo para jefes; todos para Mili y Tomás) · 5 indicadores: citas hoy, próxima, **clientes en rojo con reunión hoy**, huecos libres hoy, esta semana · filtro «Con quién» (cliente · prospecto · interna · de fuera) con contador, que se queda.
- **Pestañas por frecuencia:** Hoy (por hora, línea roja de «ahora», «Ficha del cliente» si la puedes abrir, «Abrir en Zoho CRM / GHL / Ver grabación», chip «En rojo · motivo») + «Lo siguiente» · Semana (rejilla 8-20 h con solapes por grupo, pulsar = detalle; en móvil, lista por día) · Huecos libres (L-V 9-18, tramos de 15 min o más; verde ≥ 30 min; «Copiar huecos») · Mi equipo / Todo el equipo (tabla pulsable) · Fuentes (estado de cada fuente y el paso para Tomás).
- **Prospectos:** en el fichero público solo iniciales con la plantilla de la reunión («Reunión de 45 min con Tomás Sala · C···»). Los títulos completos en `data/agenda/_privado/<persona>.json`; «Ver nombres» los abre con `ctx.verDato` (una lectura, queda en el rastro).

## De dónde sale cada dato
| Fuente | Cómo | Hoy |
|---|---|---|
| Zoho CRM · Events | `zh.py` (llave propia zoho.eu), COQL de hace 14 días a dentro de 21; dueño → persona por correo; cuenta/contacto → cliente por nombre corto | 267 eventos; las citas de **Zoho Bookings ya entran por aquí** (título «<cliente> and <servicio>», se enseña «<servicio> · <cliente>») |
| GHL de RO | `repartir_setters.py` (E6): 5 calendarios de Tomás (45 min, 15 min, taller de la oferta, curso Claude, antiguo), sin canceladas; si el contacto lleva `setter:<x>`, también en la agenda de esa setter | 130 citas |
| Copias GHL ↔ CRM | misma persona y misma hora → se queda la de GHL (trae estado y enlace) | 152 quitadas |
| Zoom | `data/reuniones/reuniones.json` (M15): reuniones grabadas, por asistente | 41 |
| Zoho Bookings / Calendar directos | `zbookings.py`: 401 y INVALID_OAUTHSCOPE con la llave actual | sin conectar |

Resultado: 286 filas (83 con cliente, 166 con prospecto, 32 de fuera, 5 internas) de 17 personas.

## Cifras contrastadas a mano
1. **Lucía, viernes 2-oct 12:29, 1 h 9 min** en la agenda = asistencia de Zoom de M15 (`2026-10-02 12:29`, 69 min).
2. **Lucía, jueves 8-oct 14:00 «Octoedro + Ranking Online»** = evento del CRM (COQL, `2026-10-08T14:00+02:00`, Octoedro).
3. **267 eventos del CRM** en la ventana = la consulta COQL directa (`count` por páginas) · **286 filas** = 267 + 130 + 41 − 152 copias.

## Permisos (probado contra el servidor, no la pantalla)
- Filas con `persona_id` → regla `horas_persona` de servir.py: Lucía recibe solo `lucia`; Coti, `constanza` + `jeronimo`; Ana (setter), 0 filas (aún no hay citas con `setter:ana`); Mili y Tomás, todas.
- `cliente_ref` (no `cliente_id`) para que tu reunión con un cliente que no llevas no desaparezca de tu agenda; el enlace a la ficha solo sale si lo puedes abrir.
- Lucía pidiendo los nombres de Tomás (`ver_dato agenda/_privado/tomas`) → **403**.
- «Ver como» es solo lectura; «Ver nombres» queda en el rastro como cualquier `ver_dato`.

## Lo que falta / dudas (también en `dudas_pintura.md`, D-P-AGE)
1. **Paso para Tomás (2 min) para Bookings y Calendar:** api-console.zoho.eu › Self Client › Generate Code con los scopes de siempre más `zohobookings.data.READ,zohobookings.data.CREATE,ZohoCalendar.calendar.READ,ZohoCalendar.event.READ` → guardar como `zoho_grant_code` en el llavero → `python3 ~/RO_HERRAMIENTAS/zoho/zh.py canjear` → `python3 ~/RO_HERRAMIENTAS/zoho/zbookings.py comprobar` → `python3 fuentes_agenda/generar_agenda.py`. (`data.CREATE` lo exige Zoho para *leer* citas: «Fetch Appointment» es un POST. El lector no crea nada.) Documentación: [Fetch Appointment](https://www.zoho.com/bookings/help/api/v1/fetch-appointment.html), [Fetch Staff](https://www.zoho.com/bookings/help/api/v1/fetch-staff.html), [Calendar list](https://www.zoho.com/calendar/help/api/get-calendar-list.html), [Events list](https://www.zoho.com/calendar/help/api/get-events-list.html) (máx. 31 días por consulta). Calendar solo da los calendarios del dueño de la llave: el de cada persona llega con su propio acceso al publicar la app.
2. **Zoom próximas reuniones:** a la app «Panel RO lectura» le falta `meeting:read:list_meetings:admin` (probado: error 4711). Con él, salen también las reuniones de Zoom programadas.
3. **«Ver nombres» para accounts y especialistas:** la regla `lead` solo deja desenmascarar a setters, ventas de RO y dirección sin cliente. Pedido a E0: tipo `agenda_propia` (`propio` + `desenmascarable`) y que `/api/ver_dato` pase `persona_id` = nombre del almacén. Mientras, el botón no sale y dice «Prospectos con iniciales».
4. **RRHH (Cecilia) recibe del servidor todas las agendas** (regla `horas_persona`); la pantalla le enseña solo la suya. Recomendación a E0: regla propia para la agenda (persona, jefe, operaciones y dirección).
5. **Setters:** no hay aún contactos con `setter:ana|javier` (empiezan el lunes 5-oct); su agenda sale vacía con la explicación.
6. Icono del menú: `ICONO_MODULO.agenda` no existe en componentes.js (sale el del grupo «Hoy»). Pedido: `agenda: 'cal'`.

## Capturas (`capturas/agenda/`)
`<persona>_1440.png` y `<persona>_390.png` para tomas, mili, lucia, valeria, yessica, constanza y setter_ana · `tomas_semana_1440.png`, `tomas_huecos_1440.png`, `tomas_equipo_1440.png`, `tomas_fuentes_1440.png`. Consola sin errores en las 14 cargas; sin desplazamiento horizontal a 390 px (Chrome sin cabeza, servidor `servir.py` en el puerto 8823 sobre una copia del prototipo).

## Regenerar
`python3 fuentes_agenda/generar_agenda.py` (≈ 3 min: lee los contactos de GHL de cada cita). Solo lectura.

## N6 · diseño 10/10 (2-oct)
**Qué cambié (solo presentación; datos, permisos, «Ver nombres», rastro y enlaces intactos):**
- Fuera la hoja inyectada: clases comunes (tiles, chips-f, pestanas, panel, bt, chip, ico-c, selcli, menu-flot, tablaApilable) y estilos en línea con tokens. Limpio en `pruebas_diseno.py`.
- Los 3-4 botones con borde por cita → «Ficha del cliente» (cuando se puede abrir) + la grabación como ▶ (32 × 32) + **un botón «Abrir ▾»** con el resto de atajos (Contacto/Calendario en GHL, Evento en Zoho CRM, Bookings…). Con un solo atajo, botón «Abrir» directo.
- La fila de 15 avatares-chip → **selector de persona con buscador** (`selectorCliente`: ↑ ↓ Intro Esc), con «N citas hoy» y aviso «En rojo».
- Avatares a 26 px/12 px (nunca < 12); horas de la rejilla, bloques de la semana, duraciones y metadatos a 12 px en `--dim`; separadores de día en eyebrow 11 mayúsculas 700. Bloques de la semana con alto mínimo de 24 px.
- Rejilla de semana en ordenador y lista por días en móvil decididas con `matchMedia` (se repinta al cambiar de ancho). Navegación de semana con `bt icono` de 32 px.
- Vacíos dentro de panel con `vacioLinea`; «Próxima» sin dato → «Ninguna» en gris (sin «—» grande); «Ninguno / Sin citas» en la tabla del equipo; plurales «1 cita»; fecha de lectura «2 oct, 17:12»; quitado el código de permiso de Zoom de la pantalla (queda en la burbuja).
- No usa periodo común: es un calendario por día/semana.

**Revisión (n6_revisar, 7 personas × 1440/1024/390):** antes 15 pantallas con fallos (53 textos < 12 px con Tomás, avatares a 10 px, desborde a 1024); después 0, sin errores de consola ni scroll horizontal. Probado a mano: menú «Abrir» (3 enlaces, Esc cierra), selector de persona, las 5 pestañas, detalle de cita en la semana. Capturas en `capturas/_n6/agenda/`.

**Peticiones a E0 (en ../dudas_pintura.md, D-P-N6-agenda):** `menuMas()` pinta «null» cuando está cerrado (`replaceChildren(btn, null)`); por eso agenda usa su `menuAbrir()` con las mismas clases. Y un `placeholder` en `selectorCliente` (hoy dice «Buscar cliente o account…» también para personas).
**Queda:** «Abrir ▾» se ve siempre (no solo al pasar el ratón), a propósito para el móvil y el teclado; los bloques cortos de la semana recortan el título (sale entero en la burbuja y al pulsar). Duraciones raras («4 h 45» en COMIDA) son del dato.
**Nota:** 6,5 → **9,2**/10.

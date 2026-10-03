# M20 Personas · M21 Decisiones y rastro · M22 Ajustes (conexiones) · _ESTADO

**2-oct-2026, 16:20.** Nada escrito en ninguna herramienta externa. Los botones dejan acciones «simuladas» en `local.db`.

## Qué hay
| Módulo | Fichero | Datos | Generador |
|---|---|---|---|
| M20 Personas (`#/personas`) | `modulos/personas.js` | `data/personas_m20/equipo.json` (filas con `persona_id`), `contratacion.json` (solo quien ve Ajustes) | `fuentes_personas/generar_personas.py` |
| M21 Decisiones (`#/decisiones`) | `modulos/decisiones.js` (+ `rastro.js` de E0 intacto en la pestaña Rastro) | `data/decisiones/firmadas.json`, `reloj.json`, `direccion.json` (solo Tomás y Mili) | `fuentes_decisiones/generar_decisiones.py` |
| M22 Ajustes › Conexiones y caducidad | `modulos/ajustes_conexiones.js` + 3 líneas en `ajustes.js` | `data/ajustes/conexiones.json` | `fuentes_ajustes/generar_conexiones.py` (`--sin-red` sin llamadas) |
| Común de los tres | `modulos/personas_comun.js` | — | — |

Ediciones localizadas en comunes: `modulos/indice.js` (entrada `personas` → hecho; entrada `rastro` → `decisiones`), `reglas_permisos.json` (6 ficheros en `datos_de_modulo`), `LEEME.md` (3 filas), `dudas_pintura.md` (D-P-PER1).

**M20.** Número que manda de Cecilia: personas en alerta sin plan en 7 días (hoy 0 de 22: la primera vence el 9-oct). Pestañas por frecuencia: En alerta (motivos del panel v7, desde, plan) · Quién no imputa (ayer y 5 días, recordatorio para copiar; enviar = W7) · Ausencias (tabla propia, formulario simulado; si lleva clientes exige suplente) · Carga (12/16 proyectos y 128 h) · 1:1 y ronda quincenal · Nota del mes (puntúan Mili, jefas y Tomás; D-74) · Contratación (plan Q4: 7 traffickers + 3 CRM, calendario). Cada persona ve su ficha; jefas su equipo; Cecilia, Mili, Tomás todos. Sin sueldos ni dinero.
**M21.** Reloj 48 h (Tomás) / 24 h (Coti) con estado en plazo / por caducar / caducada; fuentes: tabla `decisiones` de local.db (tipo ≠ para_confirmar: **así entran las de M14**), cola `acciones` (`decision_nueva`, `decidir`, `escalar*` para tomas/coti) y reglas de la ficha de Mili (hoy 4: 7 altas fuera de plazo, AyG, ECIJA y Kiosko Box piden hablar con Tomás). Botones simulados: Subir una decisión (exige recomendación), Aprobar / Rechazar / Delegar con motivo. 101 firmadas con buscador y filtro por tema. Informe semanal (exigencia 48) y cierre de septiembre (exigencia 49: 11 altas y 2 bajas cruzadas con facturas de Holded, horas por account, informes, rojos), copiables.
**M22.** 14 conexiones: 11 funcionan, Windsor sin llave, SE Ranking (proyectos 403) y GHL de RO (escritura caducada) con aviso. Meta caduca el 1-dic (60 días). ClickUp 998 de 1.000 por minuto. Desk 30 departamentos con la llave propia. GHL de agencia y Zadarma no se llaman en vivo (rotación y cupo). 8 avisos.

## Comprobado
- `fuentes_personas/probar_m20_m22.py` (Chrome sin cabeza): 8 personas (tomas, mili, cecilia, lucia, valeria, yessica, constanza, setter_ana) × 3 pantallas × 1440 y 390 px, todas las pestañas pulsadas: **48 de 48 sin errores de consola ni desplazamiento horizontal**. Capturas en `capturas/personas/`, `capturas/decisiones/`, `capturas/ajustes/`.
- Recorte en servidor (curl a `/api/modulo`): Lucía y Ana reciben solo su fila; Valeria 6 (su equipo), Jessi 4, Coti 8; Cecilia, Mili y Tomás 37. Contratación y conexiones: solo Tomás, Mili, Cecilia. Informe y cierre: solo Tomás y Mili. Reloj: Cecilia 0 (llevan cliente), Lucía 0, Mili y Tomás 4.
- `escaner_secretos.py`: limpio (al principio paró `conexiones.json` por un correo; quitado).
- Prueba de botón: plan de Facundo anotado como Tomás → acción simulada en local.db, Facundo pasa a «con plan» (21 sin plan).

## Cifras contrastadas con su fuente
1. Horas de septiembre de Gustavo: 177,4 h en la app = 177,4 h en ClickUp (`/team/…/time_entries`, cu.py, 2-oct).
2. Meta: 74 cuentas y 68 activas en vivo = las del superprompt 16 §2.3.
3. Bit 24, septiembre: 97,9 h reales frente a 40,4 h pautadas = el cierre de Mili (`cierre_mes_sep.txt`).
4. Altas de septiembre: EMEX 1.078 € facturado el primer mes = factura de Holded del libro corregido.

## Falta / dudas (D-P-PER1 en dudas_pintura.md)
- `/api/decisiones` en servir.py (E0): hasta entonces lo nuevo se ve al regenerar `reloj.json`; Coti no ve en vivo lo que le suben.
- Icono `decisiones` en `ICONO_MODULO`. La ruta antigua `#/rastro` ya no está en el menú (nadie la enlazaba).
- Notas 1-10, 1:1 y ausencias: no había ninguna registrada (la colección `equipo` del panel v7 está vacía): arrancan a cero.
- «Desde» de la alerta = primera foto diaria (hay fotos desde el 2-oct); con los días se afina solo.
- Pendiente revisión con Coti, Mili y Agus (R15).

## Recargar
```
python3 fuentes_personas/generar_personas.py && python3 fuentes_decisiones/generar_decisiones.py && python3 fuentes_ajustes/generar_conexiones.py
```

---

## Ronda de arreglos (2-oct noche) · fallo de la auditoría → qué se ha hecho

| Fallo (auditoría) | Estado |
|---|---|
| B-04 (22) · Decisiones decía «7 altas sin encender» con Laver y Deudot encendidas tarde | **Arreglado**: la regla lee `data/verdad/clientes.json` (`encendido.estado`): «7 altas fuera de plazo: 5 sin encender y 2 encendidas tarde», con cada nombre y su día. El informe semanal usa la misma lista. `pruebas_coherencia.py` con `decisiones` en ADOPTADOS |
| I-11 (22) / 29 · «jefa/e: mili» en crudo | **Arreglado**: «Responde ante: Mili» con `ctx.nombre()`; en Decisiones, todos los nombres con `ctx.nombre()` |
| I-09 (22) / 29 · Personas 22/28 frente a Horas 27/33 | **Arreglado**: «Ayer sin imputar» = `data/verdad/equipo.json` (9 de 28, la misma regla que Horas); setters fuera de la imputación. `personas` en ADOPTADOS y en verde |
| 29 · «imputó 1.7 h», «peso 4», «día 0 de 7» | **Arreglado**: «1,7 h», «4 motivos», «Plan pendiente · quedan 7 días» |
| 29 / regla 2 · Códigos internos (D-xx, G1, W1, W7, exigencia NN, ley C-D3, auditoría C-14, nombres de fichero) | **Arreglado** en los tres módulos: `limpiaTexto()` sobre textos de datos; las 101 firmadas se numeran «n.º 74» y la referencia va plegada en «¿De dónde sale?» (solo dirección). La prueba propia busca textos crudos en las 48 pantallas: cero |
| P-07 (22) · Títulos de Decisiones cortados y campo «Motivo» nativo | **Arreglado**: título a 2 líneas (`pm-dos`) y campo con el estilo de formulario |
| P-06 (22) · Alias distintos («Vale», «Jessi») | **Arreglado en mis pantallas**: siempre `ctx.nombre()` o el alias de `personas.json` |
| A4 (27) · Enlace `javascript:` en «Subir una decisión» | **Arreglado**: se sube por `POST /api/decisiones` (el servidor valida https o `#/`), y la detectada solo manda `#/…` |
| A5 (27) · «decidir» de cualquiera por la cola de acciones | **Arreglado**: contestar va por `POST /api/decisiones` `responder` (solo el destinatario). Una detectada se registra primero en la tabla con su clave y conserva su hora de detección |
| A1 (27) · Dinero de la empresa en `decisiones/firmadas` | **Ya resuelto por E0** en `reglas_permisos.json` (`filas_solo_tipo` + `textos_sin_importes_salvo`) |
| 26 C · Personas sin atajos | **Arreglado**: «ClickUp ↗» (hoja de horas), «Zoom ↗», «Desk ↗» por persona; **lista de salida** con atajo por herramienta (App, ClickUp, Zoho, Google, GHL, Meta, Zoom, Zadarma, Metricool, Snov.io) y casilla «Marcar quitado» con rastro |
| 26 C · Ajustes sin atajos | **Arreglado**: «Renovar la llave ↗» a la consola de Meta, GHL (agencia y RO), Zoho, Zoom, Google, ClickUp, Windsor, SE Ranking, Metricool, Holded, Airtable, Snov.io y Zadarma, con el camino dentro de cada una |
| Regla 4 · Zonas horarias | **Arreglado**: las horas de la base son UTC y se pintan en hora de Madrid («(hora de Madrid)» a la vista); las detectadas se generan en UTC |
| Regla 6 · Verdes falsos | Revisado: sin dato = «—» gris; «Ausencias» sin color cuando no hay ninguna |
| 28 E-16 · Día cortado a la hora de Madrid para el equipo de Argentina | **No aplica aquí todavía**: depende del campo `zona` de `personas.json` (vacío) y del lector de horas de E1/E7 |
| 22 · Pestañas de Ajustes sin icono | **No es mío**: la barra de pestañas es de `ajustes.js` (E0); mi pestaña se añadió con el mismo patrón |
| Nuevo encargo · Sueldos | **Hecho** (pestaña solo para dirección y RRHH): coste por área, sueldo por persona de enero a septiembre con su gráfico, proyección 2026 y evolución del equipo, todo con `ctx.verDato` (rastro por cada apertura). Comprobado: Tomás y Cecilia abren; Mili y Lucía reciben 403. La hoja de cuentas bancarias no se toca. **Ninguna captura enseña importes** (solo la pestaña cerrada) |

**Pruebas de la ronda:** `probar_m20_m22.py` 48 de 48 sin errores ni desborde y sin textos crudos (capturas `r3_*` en `capturas/personas/`, `capturas/decisiones/` y `capturas/ajustes/`); flujo en una **copia** de la base (puerto 8796): Tomás contesta la detectada → `db-1` con su respuesta; Lina sube una → `db-2`; Cecilia abre área (17 filas), persona y evolución. `pruebas_coherencia.py`: `decisiones` y `personas` en verde (el único error es de Agenda). `pruebas_e0.py`: todo bien salvo el escáner, que para `data/agenda/agenda.json` (no es mío). `escaner_secretos.py`: mis ficheros, limpios.

**Avisos:**
- Para probar la lista blanca dejé 4 acciones de prueba en la base real (`personas_salida`, objeto `prueba_sin_persona`). No salen en pantalla porque no casan con ninguna persona. Son imborrables.
- `POST /api/acciones` no comprueba que quien manda una acción vea el módulo que pone en `modulo`: Lucía puede dejar una `personas_*` con `modulo: 'ajustes'`. Lo apunto para E0 (D-P-PER2).
- «Calcular la evolución» pide la ficha de cada persona. Las que no figuran en el Excel devuelven 404, que sale en la consola solo al pulsar el botón. Arreglarlo exige un índice en el almacén de sueldos (E0).
- Zoho Desk responde 400 en la comprobación en vivo de esta noche. Puede ser el tope de renovaciones de Zoho (10 cada 10 min) con varios agentes a la vez. Sale en Avisos.
- Los sueldos entran porque `reglas_permisos.json` y el LEEME recogen una «regla nueva de Tomás (2-oct)». La memoria permanente seguía diciendo «sin sueldos». Conviene que Tomás lo confirme.

## N6 · diseño 10/10 (2-oct, noche)
Solo presentación: los datos, los permisos, las acciones y el teclado funcionan igual.
**Ficheros:** `personas_comun.js`, `personas.js`, `decisiones.js`, `rastro.js`, `ajustes.js`, `ajustes_conexiones.js` y `catalogo.js` (pantalla «Componentes»). Los siete salen limpios en `pruebas_diseno.py`.

- **`personas_comun.js` ya no inyecta su hoja (`pm-css`).**
  - Las piezas `pm-*` se pintan con atributos de estilo que usan solo tokens (`--t-*`, `--s-*`, `--r-*`, `--sombra-*` y los colores de `:root`).
  - Lo hace el `h()` de este fichero (el común más esas piezas). Personas, Decisiones, Ajustes y Conexiones importan ese `h`.
  - `estilosLocales()` queda vacía, para que las llamadas antiguas sigan funcionando.
  - Las rejillas usan `minmax(min(100%, …))`, así que el móvil funciona sin `@media`.
- **Campos de formulario.**
  - `campo()` usa la clase común `.campo` / `.campo-et`, con campos de 40 px de alto.
  - El nuevo `elegir()` sustituye los desplegables de pocas opciones por `chipsFiltro()`: tipo de ausencia, «Para Tomás / Coti», ¿imputa?, estado. Se lee igual que antes, con `.value`.
  - Los desplegables de persona y de cliente (30-60 opciones, dentro de formularios de edición) siguen siendo nativos, pero con el estilo de `.campo`.
- **Personas.**
  - Bloque nuevo «Cumpleaños y aniversarios» (`ctx.celebraciones({ dias: 14 })`) en la vista del equipo y en «mi ficha».
  - Las tarjetas «En alerta» muestran 9 y un botón «Ver las N personas»: la página mide menos de la mitad.
  - La cabecera de cada tarjeta parte la línea en vez de aplastar el nombre (eran 504 desbordes, ahora 0).
  - El trimestre sale en llano («4.º trimestre», no «2026-T4»).
  - «Pendiente» pasa a «Falta», que cabe en la tarjeta.
  - Fuera la ruta de fichero del plan de fichajes y el comando para regenerar.
- **Decisiones.**
  - «Ver en la app» pasa de 20 px a botón de 32 px.
  - Formulario con campos comunes y «Para» con chips.
- **Rastro.**
  - Fechas «2 oct, 17:12» en hora de Madrid, en vez del ISO en UTC con letra de código.
  - Paneles con icono.
- **Ajustes.**
  - Los paneles llevan icono y el relleno común.
  - La tarjeta de cada duda tiene el título sin código (la A1 sigue en la burbuja), texto a 72 caracteres de ancho, controles en rejilla con etiqueta y nota con campo común.
  - Fuera «(auditoría C-03)», el nombre de fichero `respuestas_mili.json` y el comando de arranque.
- **Componentes (catálogo).** Al principio va la guía de estilo en vivo (auditoría 30 §3):
  - escala tipográfica con sus 8 tokens;
  - espaciado, radios y sombras;
  - color con significado y `colorCifra()`;
  - `cifraPrincipal()`, `vacioLinea()`, `esqueleto()`, `grafico()`, `menuMas()` y `campoTexto()`.
  Las rejillas de dos columnas ya no desbordan a 390.

**Comprobado:** `n6_revisar` con 7 personas × 1440/1024/390, y todas las pestañas de Personas, Decisiones y Ajustes a 1440 y 390. No hay errores de consola, scroll horizontal ni texto < 12 px. Capturas en `capturas/_n6/{personas,decisiones,ajustes,catalogo}/`.

**Queda (de lo común, no lo parcheo):**
- Las cabeceras ordenables de `tablaDensa` miden 16 px de alto.
- Los filtros de `tablaDensa` son `<select>` nativos.
- Las tarjetas en carrusel cortado a ≤ 640 px (`main#main .tiles`).
- La fila de cabecera oculta de la tabla apilable cuenta como «desborde» a 390.

**Peticiones a E0:**
1. Cabecera de tabla de ≥ 32 px (toda la celda como botón).
2. Un selector de persona con buscador (como `selectorCliente`) para los formularios de Ajustes y Personas.
3. Que `.tiles` pueda ser rejilla de 2 en 2 en el móvil (opción `movil: 'rejilla'`).

**Nota que me pongo (escala exigente de la auditoría 30):**

| Pantalla | Antes | Después |
|---|---|---|
| Personas | 5,5 | 8,8 |
| Decisiones y rastro | 6,5 | 9,0 |
| Ajustes | 5,5 | 8,5 |
| Componentes | — | 9,0 |

Ajustes sigue siendo una herramienta de edición larga, con selects de persona nativos.

## R12 · arreglos tras la auditoría final (carril E, 2-oct noche)
- **A-A7 «22 de 28 en alerta, casi todo por horas» → arreglado.** Regla de Tomás (D-27): las horas son solo aviso. `fuentes_personas/generar_personas.py` separa los motivos de horas («imputó X h», «registros de horas fuera de lo normal») en `avisos`; la alerta queda solo con señales reales (tareas arrastradas, revisiones y correos de +48 h). Los correos de +48 h de una cartera de account que la persona ya no lleva (Agus) también pasan a aviso. Resultado: 11 en alerta (antes 22) y 11 personas solo con aviso. Personas enseña el aviso en gris («Aviso, no alerta») en la tarjeta y en la ficha propia.
- Falta en otro carril: `fuentes_alertas` debe regenerarse para que «rrhh_alerta» baje a 11 y «rrhh_no_imputa» debería ser aviso (apuntado en dudas_pintura.md, R12).
- **Cartera (pedido del carril de asignaciones) → hecho:** Personas lee `verdad/clientes › carteras[]`: «21 clientes · tope 16 · 19 tuyos + 2 de apoyo · 14 de tus 19 clientes con cuenta de Meta en Captación…» (antes «21 de 16 cuentas de Meta»), también en «Carga».

## Ronda de velocidad (2-oct noche, auditoría 37 causa 4)
- `personas.js`: las 5 lecturas (equipo, contratación, cola, verdad/equipo, verdad/clientes) salen a la vez. 4G lenta, 390 px: tomas 3.017 → 760 ms, lucia 2.386 → 694, valeria 2.386 → 684 (1 tanda en vez de 3-4). Texto de pantalla idéntico antes y después (tomas, lucia, valeria, mili, cecilia).

## V2 · carril V2-C2 · Personas (3-oct)
- **B-M12** Valeria «0 de 28» → «0 de 4» (la gente que ves; toda la empresa solo RRHH, operaciones y dirección) · «suyos» en filas ajenas · la misma banda para todos: cartera por encima con su cifra («21 de 16»), horas > 100 % en rojo («136 %»).
- **A-M5** las tres cifras de alerta juntas («11 en alerta: 10 sin plan todavía y 1 con plan»), pestaña «En alerta sin plan»; la tarjeta de capacidad dice además quién pasa del 100 % de horas; Contratación explica «Accounts: 0» frente a los accounts por encima (mal repartida: se reparte, no se ficha).
- **A-M12** `#/personas/<id>?plan=1` abre «Anotar conversación y plan» con el foco (el «Ir» de Mi día, pedido a su dueño).
- **A-B9** pestañas en una fila con «Más» · **barrido v1** nombre y puesto en dos renglones (sin solape) · fuera «(04 §3)» y «Promethean y Productive, 07 §2» · «hoy» de Madrid.

## V2-C1 · Conexiones y Ajustes (3-oct)
- **A-M7 / B-M3 · arreglado:** sin órdenes de terminal a la vista: «Qué hacer: Lo hace Tomás: pegar la clave de X; después Agus comprueba que llegan los datos» y «Lo hace: Tomás · lo comprueba: Agus». La orden técnica solo para Tomás, en «Más · Paso técnico». `duenoConexion()` exportada: Captación la lee (B-M2).
- **B-M3 móvil · arreglado:** a 390 las conexiones que funcionan van plegadas («21 conexiones funcionan · ver»).
- **39b-10/11 · arreglado:** «Dónde se renueva» con zona de 32 px; `label.chip` de Ajustes con `min-height: 32px`.
- **V2 (petición de V2-C1, B-A3) cartera de publicidad única → hecho.** Personas (Carga y ficha) cuenta los clientes que LLEVA el trafficker (verdad `carteras[]` = `captacion.json › carteras_publicidad`); el apoyo va aparte y no cuenta contra 16. Lina 19 / 16 (+2 de apoyo, 14 con Meta, 9 encendidas), Valeria 11 / 16 (+8): ya no sale «por encima». Prueba V2 en `pruebas_coherencia.py`.

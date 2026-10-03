# _ESTADO · M8 «SEO, ficha de Google y webs» (2-oct-2026)

## Hecho
- `modulos/seo.js` (ruta `#/seo-web`; se dejó el id de `indice.js` y de `ICONO_MODULO` para no tocar ficheros comunes). Pestañas SEO por cliente · Webs · Ficha de Google; detalle `#/seo-web/<cliente>`.
- Cada puesto abre en lo suyo: Constanza y dirección → % de clientes de SEO en verde + su célula; SEO asignado (Jero, Francina, Yadibeth) → top 5 de las 15 en sus clientes; web → webs que responden, certificados, «Lo tengo»; account y trafficker → sus clientes (recorte del servidor).
- Datos: `fuentes_seo/generar_seo.py` → `data/seo/seo.json` (filas con `cliente_id`, recortadas por cliente) y `data/seo/webs.json` (filas con `cliente`, sin `cliente_id`: el equipo web ve el estado de todas las webs para cubrir guardias, G3-4). Alta en `reglas_permisos.json → datos_de_modulo` (`seo/seo`, `seo/webs` → `seo-web`).
- **SE Ranking**: la clave de proyectos del llavero da 403, pero el **conector** funciona. Se leyeron las posiciones 1-sep → 2-oct de los 40 proyectos emparejados (`PROJECT_getKeywordStats`); las respuestas en bruto (80 KB-1 MB cada una) quedan fuera de la app y `fuentes_seo/sr_condensar.py` deja `fuentes_seo/_cache/seranking.json`. Para refrescar: volver a pedir las 40 respuestas por el conector y pasar `sr_condensar.py <carpeta>` (el emparejamiento fichero → cliente está en el script).
- **Search Console en vivo** (`gg.py`): semana 23-29 sep frente a 16-22 sep, 28 días frente a 28, serie diaria, 12 páginas y 12 búsquedas con su dato anterior. 31 de 41 clientes de SEO.
- **Monitor de webs**: una comprobación real (2-oct, 15:4x) de las 63 webs de clientes + rankingonline.com desde este Mac (= IP de RO): código HTTP, tiempo, certificado y palabras de spam en la portada. Diseño de la comprobación doble (desde RO y desde fuera) explicado en pantalla; lo de fuera llega con W1.
- Avisos de medición del `17_ANALYTICS_A_CERO_REVISION.md` (FusterGüell, Musashi, ECIJA, Busbac) en la pestaña Webs y en el detalle.
- PageSpeed: «se conecta» (no hay clave); botón «Medir velocidad» deja la petición en la cola. Ficha de Google: hueco «se conecta» con lo que enseñará + posiciones en Maps donde SE Ranking las mide.
- Botones (cola simulada): Crear tarea, Lo tengo, Avisar al account, Medir velocidad, Lanzar comprobación de posiciones (gasta créditos: doble confirmación), Hecho / no aplica (rastro).

## Hallazgos reales para Tomás
1. **Musashi tiene spam inyectado en la portada**: enlace oculto a «casinos online con pasaporte» (mma.es/apuestas). Geslabor sigue con bet365, casinos y tragaperras en la portada.
2. **No responden desde la IP de RO**: Busbac (error SSL), TST Consulting (error TLS), Marlex (el dominio no existe en DNS), Abner (404 en la portada). Falta la vista desde fuera para saber si es solo para RO.
3. **Certificados a ≤ 30 días**: Proincentiva y Segú (15 días), Laver (21), Ahedo (26), J&D (27), Torrevieja (29).
4. **SE Ranking dejó de encontrar 601 palabras de golpe** en 34 proyectos esta semana mientras los clics de Search Console suben en 25 de 31 clientes: parece fallo de la comprobación. Por eso «no aparece» va en ámbar y solo cuenta como roja la palabra medida fuera del top 10 dos días seguidos (Asetra «asetra» 2 → 47; Bit24 «bitrix24 login» 6 → 17).

## Cifras contrastadas con su fuente
1. GAC en SE Ranking: top 5 = 0, top 10 = 2, top 30 = 7 de 186 palabras, igual que `PROJECT_getSummary` del conector (0 · 2 · 7).
2. Laver, clics de Search Console en 28 días: 3.029, igual que la capa E1 (`data/clientes/laver.json`, 3.029) leída por otra llamada.
3. Palabras seguidas por proyecto (GAC 186, Asetra 204, Kiosko Box 191, Segú 272): iguales a `palabras_seguidas` de E1.

## Falta / dudas (se siguió con la recomendación)
- **Las 15 palabras del informe** no están marcadas en ningún sitio: provisionalmente, las 15 de más búsquedas del buscador principal. Recomendación: que cada SEO cree el grupo «Informe» en SE Ranking y el generador lea ese grupo.
- Visibilidad: calculada con las posiciones (búsquedas × clic esperado), no la nota de SE Ranking (el resumen solo da la de hoy).
- 404, indexación, cosecha y visibilidad en IA: «todavía no» al pie.
- Monitor cada 5 min, desde fuera, formulario → GHL y PageSpeed: W1 + clave de PageSpeed.
- Revisión con Coti, Mili y Agus (R15): pendiente.

## Pruebas
- Recorte en el servidor (`/api/modulo/seo/seo`): Tomás y Constanza 41 clientes, Jerónimo 37, Carlos Viur 28, Lara 22, Lucía 12; Yessica y Ana (setter) 403.
- Sin errores de consola con `?yo=` tomas, mili, lucia, valeria, constanza, jeronimo, carlos_viur, lara (portada y detalle); yessica y setter_ana ven «no es de tu puesto».
- `escaner_secretos.py`: sin hallazgos en `data/seo/` (el único hallazgo es `data/ajustes/conexiones.json`, que no es de este módulo).
- Capturas en `capturas/seo/` (1440 y 390).

## Ronda 3 de arreglos (2-oct noche) · fallo de la auditoría → qué se ha hecho

| Fallo (auditoría) | Estado |
|---|---|
| Cifras E-09: «verde» con 0 de 15 en el top 10 (Laver, Innova, Consulting F) | **Arreglado.** Si ninguna de las 15 está en el top 10 → ámbar «Ninguna de las 15 palabras del informe está en el top 10». El verde dice «ninguna ha salido del top 10 · N de 15 en el top 10». Prueba en `pruebas_coherencia.py` |
| Cifras E-09: «verde» con 0 clics frente a 0 (Consulting F) | **Arreglado.** 0 clics en los dos periodos = sin dato. Sin clics medidos nunca hay verde: gris «Clics sin dato» |
| Cifras: Consulting F apunta a la landing info.consultingf.com | **Arreglado** en mi lado: si el sitio de Search Console no es el dominio de la web → «sin conectar» con nota. E1 ya lo ha quitado y lo regeneré después |
| Cifras E-10: retraso de 2-3 días de Search Console | **Arreglado.** Cada sitio se compara hasta su último día con dato (hoy, 29-sep): 7 días cerrados frente a los 7 anteriores y 28 frente a 28. En pantalla: «datos hasta el 29 sept». Kiosko pasa de −21 % a −14 % |
| Cifras E-22: Analytics que deja de medir (mes anterior > 50 usuarios, este 0) | **Arreglado** en el generador: rojo «La etiqueta de Analytics dejó de medir», a web. Hoy no hay ningún caso: Musashi ya tenía 0 el mes anterior y sigue con su aviso del banner de cookies |
| Arquitectura parte C: faltan atajos a Analytics y a la ficha de Google | **Arreglado.** Botón Analytics en la cabecera y en cada fila; SE Ranking en cada fila; Search Console en la cabecera. Si falta el emparejamiento: botón gris «falta emparejar». Ficha de Google: botón gris «se conecta» (no hay identificador) |
| Experiencia: «−51.9 %», «−100.0 %», «5214» en formato inglés | **Arreglado.** Números con separador de miles y coma decimal en la pantalla y en los textos del generador |
| Experiencia: aviso de SE Ranking demasiado largo | **Arreglado** con el texto propuesto |
| Regla 1: verdad única | **Adoptada.** SEO, web, redes y account salen de `verdad/clientes.json` (equipo vigente, principal primero). `seo-web` y `redes` están en ADOPTADOS y sus 3 comprobaciones pasan |
| Regla 2: textos sin códigos y nombres con ctx.nombre() | **Arreglado.** Fuera D-27, D-54, G3-x, W1 y el nombre del fichero 17. Nombres con `ctx.nombre(id)`. Las notas de E1 sin ids crudos |
| Regla 4: zona horaria | No aplica: el monitor guarda la hora de este Mac (Madrid) y Metricool se pide en Europe/Madrid |
| Regla 6: nada de verdes falsos | Arreglado (ver arriba): hoy hay 1 cliente en verde de 38 medibles y 3 en gris |
| Seguridad 27 | No aplica a M8: no sirve cuotas ni servicios |

**Para E1:** Asetra cambió de https://asetra.net/ (171 clics por semana) a https://www.asetra.net/, que da 0. En pantalla sale «sin dato». Hay que devolverlo a la propiedad buena.

Pruebas de la ronda: `pruebas_e0.py` TODO BIEN · `pruebas_coherencia.py`: seo-web y redes en verde (los 2 errores son de agenda y bandeja) · consola limpia con 10 personas · capturas `capturas/seo/r3_*`.

## Ronda 4 · guía de diseño (auditoría 30) y encargos del coordinador · 2-oct noche
- Fuera las hojas de estilos propias (`seo-estilos`, `cap-estilos`, `eq-estilos`): clases comunes (fila, pila, sub, chip, lista-i, rejilla, titulo-seccion) y estilo en línea solo con tokens (`var(--s-*, valor)`), nada por debajo de 12 px, cifras con punto de miles. Estado de fila = punto + texto en tinta. Línea de fuentes → un chip «Datos al día» que se despliega.
- Gráficos: `barras()` de `produccion_comun.js` usa ya el motor común `grafico()` de componentes.js; barras de progreso, embudo y ventanas, los comunes.
- SEO/web: pestaña Webs con columnas de Modular DS (Copia · Actualizaciones · Seguridad · Fuera de RO, con «bloqueada solo para RO»); hoy «Modular sin conectar» con el paso de Tomás (clave de solo lectura + pegar.sh). Camino conectado probado con datos simulados en el navegador.
- Horas: zona horaria de cada persona desde personas.json (Valeria hora de Venezuela, Sofía hora de España) en cabecera, listas, tabla y ficha.
- Producción: Camilo con la etiqueta «transversal» (copy, responde ante Mili), «sin cartera propia».
- Captación: Kiosko (tienda online) fuera de los leads de la casa (143 en vez de 1.562) y del techo de 35 € (4 de 8 en vez de 5 de 9), con nota en su tarjeta.
- Pruebas: 7 personas × 1440/390 × 7 rutas con todas las pestañas: 0 errores, 0 desbordes, 0 textos < 12 px · coherencia 0 errores · escáner limpio · pruebas_e0: 1 fallo ajeno (/api/cliente de Gustavo, «serie»).

## N6 · diseño 10/10 (2-oct, noche)
- **Portada en pestañas por fuente**: Posiciones · Ficha de Google · Webs (antes «SEO por cliente» y todo seguido). Tablas de 15 filas + «Ver 15 más» (semáforo de 41 clientes, 64 webs, Maps), sin apilar en el móvil (se desplazan dentro de la tabla). Motivo de cada fila recortado a 2 líneas, el texto entero en la burbuja.
- **Lo que no se mide, «cómo se comprueba cada web» y «lo que enseñará la ficha»**: plegados al pie. Vacíos dentro de bloque con `vacioLinea()`.
- **Detalle del cliente en pestañas**: Posiciones (15 palabras a todo el ancho + Suben | Bajan) · Clics de Google (gráfico con `grafico()`, páginas, búsquedas) · Web y ficha; Acciones al pie. Tarjetas sin dato fuera de la rejilla (nada de «—» grande) y dichas en una línea.
- Tarjetas con etiquetas de una línea («Clics · 7 días», «Fuera del top 10»…), umbrales a la burbuja. Formateador común `fmt` (fuera los `Intl` propios). «>100» en gris (rojo con cuentagotas).
- **Periodo: no usa el común.** Todo son ventanas fijas de la fuente (posiciones de hoy frente a hace 7 y 30 días; clics de 7 y 28 días cerrados hasta el último día de Search Console, que va 2-3 días por detrás; usuarios de 30 días) y así se dice junto a cada cifra. La serie diaria de clics solo tiene 28 días y acaba el 29-sep: un periodo de 7 días «hasta hoy» enseñaría días sin dato.
- Medidas (Tomás): 1440 → 5.793 a 2.927 px; móvil → 16.131 a 4.518 px. 75 pantallas (7 personas × 1440/1024/390, portada y 2 detalles) + todas las pestañas: 0 errores de consola, 0 scroll horizontal, 0 textos < 12 px, 0 «null». Capturas en `capturas/_n6/seo-web/`.
- **Nota contra la auditoría 30: 6,0 → 8,5.** Falta: la regla común `.dos` no se apila en el móvil (apuntado en `dudas_pintura.md`; aquí va una rejilla por ancho mientras tanto) y la cabecera de la ficha de cliente sigue repitiendo el nombre (migas + selector + cabecera), que es el patrón común de detalle.
- **N6 · segunda pasada:** «Lo primero hoy» (SEO y Webs) y «Avisos de esta semana» con el rojo con cuentagotas (solo el tercio de arriba; el resto, ámbar). Cada fila de esas listas lleva 1 acción principal + «⋯» (`details` + `.menu-flot` comunes) en lugar de 3 botones en dos filas en el móvil. Se repitieron las 60 pantallas y todas las pestañas: 0 problemas. **Nota: 9,0.**

## R12 · Quién lleva qué (2-oct noche)
- Ver la tabla R12 en `_ESTADO_E0.md` (carril «asignaciones y verdad única»). En este módulo: C-A3 **arreglado** (dueño = principal de la silla web; `web_aviso` en cada web; 16 sin dueño como duda R12-WEB).

## R12 · arreglos tras la auditoría final (carril E, 2-oct noche)
- **B-A05 número que manda con un solo umbral y una sola medida → arreglado.** `resumen` de `data/seo/seo.json` es la definición única: base = clientes medibles (`clientes_seo` = 38, `clientes_total` = 41), `umbral` firmado de la ficha G3 (80/60), `estado` y `sello`. SEO lo lee tal cual para toda la cartera; Mi día (otro carril) ya lee la misma base.
- **B-A06 «top 5 −43» sin aviso → arreglado.** «Hoy frente al mes anterior» solo cuenta palabras que SE Ranking ve hoy (`reparto.top5.mes`); las que estaban arriba y hoy no se ven van en `sin_ver_hoy` (79) y no cuentan como caída (`mes_todas` guarda la cifra bruta). Aviso único `resumen.aviso_seranking` (601 palabras, clics suben en 22 de 24), el mismo texto en SEO y en Mi día.
- **A2 periodo → no aplica, dicho:** línea llana «Esta pantalla no cambia con el periodo…» (Search Console solo guarda 28 días por día; SE Ranking da ventanas fijas).
- Botones < 32 px: el único que queda es «Todavía no se mide · fase 2» (`pieFase2`, de componentes.js; apuntado para E0).
- **`web_aviso` (pedido del carril de asignaciones) → hecho:** se pinta en «Lleva la web» de la tabla de Webs y en el detalle de «Lo primero hoy».

## V2 · carril V2-C2 (3-oct)
- **C-9 lentas 3/10/14 → arreglado en el dato.** `generar_seo.py`: `LENTA_MS` y `w.lenta`/`w.responde` por web, `resumen.lentas` y `resumen.responden`, `_meta.lenta`. `seo.js` cuenta con `esLenta` (la regla del fichero). Mi día: pedido a su dueño (dudas V2).
- **B-M8 número que manda con SE Ranking en duda → arreglado.** `resumen.estado_mostrado` = gris, `medible` «medias» y `motivo_medible`; en SEO, «Clientes en verde» y «Palabras en el top 5» van en gris «A medias: SE Ranking en duda».
- **C-18 −100 % con clics subiendo → arreglado.** `visibilidad.fiable` (≤ 3 palabras que SE Ranking dejó de ver); la columna y la tarjeta del detalle dicen «sin dato fiable» en gris.
- **C-23 Maps 10 frente a 11 → arreglado en SEO** (todas las palabras, no 4 por cliente). «Lo arregla Agus / lo revisa Jerónimo» es de Mi día.
- **C-8 número que manda de web en Mi día → pedido** (dudas V2): `resumen.responden`.
- **C-21 guardias de web:** 5 webs sin persona de web → ya lo dice la tabla («pendiente de Mili»); dar la pestaña Web de la ficha a quien hace guardia es de permisos (R16) y del reparto de Mili: no aplica en este carril.
- **Jefe de SEO = Jerónimo:** fuera «Constanza» de los textos (escalados, reseñas, «díselo a…»).

## Puesta al día 3-oct-2026
- **Pestaña «Webs» con el tablero de Modular:** todas las webs con disponibilidad desde fuera, copias, actualizaciones, seguridad y certificado, cruzadas con el monitor propio de RO; acciones Crear tarea, Avisar al account y Marcar revisado. Solo web, jefe de SEO y web, operaciones y dirección. Detalle en `_ESTADO_modular.md`.
- **Ficha de Google (Google Business Profile): en curso** en otro carril (`fuentes_gbp/`); hoy «pendiente de aprobación» de Google. Responder reseñas queda en simulación.

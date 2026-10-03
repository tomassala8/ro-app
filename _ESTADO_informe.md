# M5 · Informe del cliente (sustituto de Looker) + comparador de paridad · estado 2-oct-2026

## Hecho
- `modulos/informe.js` (id `informe-cliente`). Rutas `#/informe-cliente/<cliente>/<periodo>/<ant|anio|no>` (enlace con las fechas, se recuerda el último por persona) y `#/informe-cliente/paridad`.
- **13 bloques** (G4 §2): resumen (hasta 8 tarjetas + 3 líneas del análisis) · embudo hasta la venta (Meta + Google Ads + GHL, costes, «dónde se rompe», % de citas sin marcar) · Analytics (6 tarjetas, usuarios por día con la línea del periodo anterior, URLs con %Δ, embudo de eventos, eventos por día, canal × evento, eventos por canal en el tiempo) · Search Console **por web y por página** (tarjetas, clics y CTR por día con el periodo anterior, dispositivos, consultas y URLs con buscador y %Δ) · SE Ranking (filtro por buscador, posición media en puestos, top 10, «15 del informe en el top 5», tabla con variación mensual, historia) · Google Ads (muestra sellada) · Meta (6 tarjetas, leads y gasto por día, campañas y conjuntos) · correo en frío (Snov.io, periodo o todo el histórico, umbral 5,5 % de D-70) · LinkedIn (hueco con último dato de su Looker) · ficha de Google (hueco «fase 2») · análisis del mes (5 apartados, borrador con las cifras, firma y fecha, banda si es de otro mes, bloqueo si lleva correo o teléfono) · glosario.
- Los bloques sin fuente para ese cliente no se pintan vacíos: van juntos en «Sin fuente para este cliente» con qué falta y quién lo arregla.
- **Selector**: 6 periodos cerrados (sep [defecto], ago, jul, jun, últimos 30 días, 3.er trimestre) × comparar con periodo anterior / año anterior / sin comparar. «Nuevo» y «sin actividad» cuando el anterior es 0. Bajar es verde en coste, CPL, rebote, frecuencia y posición.
- **Sellos de fuente** en la cabecera fija (estado + hora, al pulsar baja al bloque) y **avisos** (G4 §4): rota, a cero, caída > 80 %, dato viejo, cuenta de otro cliente (bloquea el PDF), cifras que no cuadran (suma de conjuntos de Meta), análisis de otro mes, datos de leads en el texto (bloquea el PDF y el guardado).
- **Arreglos detectados como avisos**: Innova (Google Ads de AyG: el bloque no se pinta), Bit24 (Search Console −85 %; además gmb1@ no ve ninguna propiedad de Bit24), AyG (leads en un texto de su Looker), Avantik (Looker sin acceso), AseLegal (análisis de junio), FITECC (rango mezclado), Oteca (no cuadra), Consulting F (sin SEO), Centro Consulting (sin GA4), MG (fuera de Windsor), Xterna (tarjetas). Nuevo: **6 clientes de Looker cuya propiedad de Google no ve la cuenta de la app** (Ahedo GA4+GSC, Bit24 GA4+GSC, Aster GA4, Bonet GA4, Centro Consulting GSC, Xterna GSC) → «darle acceso de lector a gmb1@».
- **Paridad**: los 22 Looker con chips por tanda (1-5), cada página de su Looker → bloque de la app (igual · mejor · a medias · falta, con el porqué), cifras de septiembre de Looker frente a la app con las tolerancias de G4 y los **6 criterios**; «Firmar un mes en paralelo» solo account del cliente, Mili y Tomás (cola simulada). Hoy: 60 bloques iguales o mejores (6 mejoran a Looker), 5 a medias, 32 faltan; 1 cliente con los criterios 1-5 (FusterGüell, por el análisis de prueba), 0 listos para archivar.
- **Botones**: guardar análisis y firmar paridad → `ctx.accion` (estado «simulada», nunca una API externa); PDF = imprimir del navegador con estilos de impresión; «ver como» = solo lectura.
- **Permisos** (G4 §1): account y dirección ven todo; trafficker y jefa de publicidad: resumen, embudo, Google Ads, Meta, análisis; SEO: resumen, Analytics, Search Console, SE Ranking, ficha, análisis; outreach y jefa de CRM: resumen, correo, LinkedIn, análisis; especialista de GHL: resumen y embudo. El servidor recorta filas por cartera y quita gasto/coste/cpl a quien no ve la inversión (comprobado en la respuesta de red: Lucía 12 clientes; Jerónimo y Yessica sin claves de dinero; setter_ana 403).

## Datos
`fuentes_informe/generar_informe.py` (solo lectura, ≈20 min en vivo; `--cache` rehace en segundos) → `data/informe/p_<periodo>.json` (una fila por cliente con `cliente_id`), `paridad.json`, `comun.json`. Dado de alta en `reglas_permisos.json → datos_de_modulo`.
- GA4 y Search Console **en vivo** con gg.py (33 clientes con GA4, 28 con Search Console; FusterGüell en properties/480200463). Totales por web (`byProperty`) y por página (`byPage`).
- Meta **en vivo** con mt.py `/insights` (28 cuentas): totales por periodo, conjuntos y serie diaria.
- Snov.io con sv.py, por campaña (11 clientes).
- SE Ranking: **la clave de proyectos da 403**; las posiciones de los 22 proyectos de Looker se leyeron con el conector de SE Ranking (30-sep y 31-ago, historia semanal jun-sep) en `fuentes_informe/_cache/seranking/`. Solo sale con «Septiembre» y «Últimos 30 días».
- Google Ads: muestra sellada de septiembre de `14_GOOGLE_ADS_VIA_WINDSOR.md` (sin clave de Windsor en el llavero). Campañas paradas con su fecha.
- Embudo de GHL: `captacion_ghl` de E1, solo septiembre (mes anterior) y 90 días.

## Cifras contrastadas con su fuente (Looker visto el 2-oct, `05` §3, y captacion.json)
1. Adade · usuarios de septiembre: app **790** = Looker 790. Impresiones de Search Console 71.034 = Looker «71 mil».
2. FusterGüell · usuarios: app **2.131** ≈ Looker «2,1 mil»; palabras en SE Ranking 145 = 145.
3. Aster · impresiones de Search Console (por web): app **172.855** ≈ Looker 172,9 mil.
4. Ahedo · palabras en SE Ranking: app **110** = Looker 110.
5. Consulting F · Meta septiembre: **465,85 € y 16 leads** = `captacion.json` (mes anterior).

## Comprobación
- 408 pantallas (68 clientes × 6 periodos, rotando las 3 comparaciones) como Tomás sin errores de JavaScript ni «null/NaN/undefined» en pantalla. Paridad e informe abiertos como tomas, mili, lucia, valeria, yessica, constanza y jeronimo; setter_ana no lo ve (403). Los únicos 404 de consola son `modulos/personas.js` y `modulos/decisiones.js` (otros módulos, aún sin fichero).
- `escaner_secretos.py`: sin hallazgos en `data/informe/` (los nombres de eventos y consultas se sanean; las URL pierden los valores de sus parámetros; el canal «Email» se llama «Correo electrónico»).
- Capturas en `capturas/informe/` (1440 y 390).
- Queda en local.db un análisis de prueba de FusterGüell (septiembre, firmado por Tomás): el rastro no se borra.

## Falta / dudas (también en dudas_pintura.md)
- Google Ads completo (W2): clave de Windsor (Tomás, 30 s) o token de Google Ads. Asetra, Oteca y MG no están en Windsor.
- LinkedIn y el correo en hoja: enlaces de las hojas de Linked Helper / correo de cada cliente (Yessica y Bautista). El permiso de leer hojas ya está en gg.py.
- Acceso de lector para gmb1@ en las 6 propiedades de arriba; sin eso Ahedo y Xterna (tanda 1) no pueden llegar a paridad.
- **SE Ranking a revisar**: desde el 25-26-sep casi todas las palabras de Google escritorio salen del top 100 en todos los proyectos a la vez (Bing y móvil aguantan). Parece un cambio de Google o un fallo de lectura, no una caída real; el bloque lo avisa cuando quedan menos de la mitad dentro.
- Las 15 palabras del informe mensual: hoy, las 15 de más volumen hasta que el account marque las suyas.
- Ventas del despacho: GHL no las tiene marcadas; el escalón sale «—».
- Periodos libres (personalizado, año, histórico de Analytics) llegan con W1 (lectura en vivo desde el servidor).
- Sesión de revisión con Coti, Mili y Agus (R15): pendiente.

## Ronda de arreglos (2-oct noche) · fallo de la auditoría → qué se ha hecho

| Fallo (auditoría) | Estado |
|---|---|
| Cifras E-01 · Kiosko emparejado con «Kiosko II» (0 €) | **Arreglado**: cuenta real «Josep SG» (act_292218051469540) leída en vivo. 30 días: 4.793,45 € y 5.340 leads, igual que la auditoría (4.793,44 € y 5.340). Septiembre: 4.801,48 € y 5.363 leads |
| Cifras · FusterGüell con la propiedad vieja 375352860 | **Arreglado**: properties/480200463 «FusterGA4 New» (2.131 usuarios en septiembre) |
| Cifras · Consulting F con Analytics y Search Console de la landing info. | **Arreglado**: «sin conectar» con la nota «falta acceso a consultingf.com», ni «a cero» ni verde. Corrección en `CORRECCIONES` del generador hasta que E1 la recoja |
| Cifras E-10 · retraso de Search Console (2-3 días) | **Arreglado**: se pide el último día con datos de cada sitio (hoy, 29-sep) y el periodo actual, el anterior y el del año pasado se cortan a los mismos días. 27 clientes recortados en septiembre y en 30 días. La cabecera dice «Search Console hasta el 29-sep» y el bloque explica el corte |
| Cifras E-22 · Analytics que deja de medir sale «a cero» gris | **Arreglado**: más de 50 usuarios antes y 0 ahora → rojo «la etiqueta de Analytics dejó de medir». Hoy no le pasa a ningún cliente de septiembre |
| Ceros en verde | **Arreglado**: respuestas al correo sin envíos → gris; Google Ads parado → «a medias», no «igual»; tarjetas de la comparación en gris o neutras con 0 |
| Análisis de prueba de FusterGüell firmado como Tomás | **Anulado** con la acción 16 (`anula: 4`, `prueba: true`). La 4 sigue en el rastro, pero no se pinta ni cuenta para la comparación (FusterGüell pasa de 5 a 4 criterios) |
| Experiencia · abre en un cliente sin fuentes | **Arreglado**: abre en el último cliente que se miró si tiene datos; si no, en el de su cartera con más fuentes |
| Experiencia · desplegables nativos | **Arreglado**: periodo y comparación con botones del sistema |
| Experiencia · «Paridad con Looker» | **Arreglado**: pasa a «Comparación con Looker» |
| Experiencia · fecha «2026-10-02 16:04» | **Arreglado**: «2-oct, 17:12 · hora de Madrid» |
| Experiencia · «Yessica» y nombres escritos a mano | **Arreglado**: nombres con `ctx.nombre()` y equipo desde `ctx.verdad(id).equipo` |
| Textos con códigos (G4, D-03, D-70, W2, W7, P1…) y la cuenta de Google de la app | **Arreglado**: fuera de pantalla, en el módulo y en el generador |
| Cifras sin punto de miles («4801») | **Arreglado**: formato con punto también en las de 4 cifras |
| Atajos, parte C | **Arreglado**: Analytics, Search Console, SE Ranking y Meta en cada bloque. Nuevos: GHL y Meta en el embudo, columna «Abrir» en «Sin fuente» y su Looker en la cabecera. La campaña concreta de Meta no se enlaza porque el formato no está documentado |
| Seguridad · `_cache/vivo.json` con URL de WooCommerce `?key=` | **Arreglado**: la caché se guarda sin valores de parámetros. `escaner_secretos.py --proyecto` sin hallazgos del módulo |
| Verdad única | **Adoptada**: account y equipo desde la verdad; `informe-cliente` está en ADOPTADOS con la prueba «account» en verde |
| Zona horaria de Meta | Los días de Meta salen en la zona de cada cuenta. No se convierten: todas las de cliente son de España; queda apuntado |
| Ventanas de 7 días | No aplica: el informe va por meses cerrados y 30 días hasta ayer |

Pruebas: `pruebas_e0.py` TODO BIEN · `pruebas_coherencia.py`: la mía en verde. Sale 1 error, que es de «agenda», no de este módulo · 7 personas sin errores de JavaScript; setter_ana no ve el módulo · capturas nuevas en `capturas/informe/r3_*` (1440 y 390).

## N6 · Diseño 10/10 (2-oct, noche) · nota que me pongo: **8,5 / 10** (auditoría 30: 6,0)
- Sin hoja propia (fuera ~90 reglas de `informe-estilos`): tarjetas `rejillaTarjetas()`, tablas `tablaApilable()` (cabecera común, 15 filas + «Ver las N filas»), avisos `.aviso`, campos `.campo`, rejillas en línea con tokens.
- Un solo motor: `lineas()` ahora es un envoltorio de `grafico()` (letra de 12 px a cualquier ancho, marcas redondas, burbuja). `barras()` y la escalera del embudo usan `barraProgreso()`.
- **Periodo común**: `usa_periodo: ['30d', 'mes_ant', 'medida']`; fuera los dos segmentados propios. El informe casa la barra con su periodo cerrado (igual de fechas, «30 días» → últimos 30, o el de más solape y lo dice en un aviso) y la comparación (`anterior/anio_ant/no`). Enlaces «Otros periodos con informe: septiembre · agosto · julio · junio · 3.er trimestre» que abren la barra en «A medida». La ruta queda `#/informe-cliente/<cliente>` (los enlaces viejos con periodo siguen abriendo el cliente).
- Cabecera: el selector de cliente ES el título (el nombre sale una vez; fuera de la cabecera de la página), 9 chips de fuente a 9,6 px → un solo chip «Datos: 4 de 9 fuentes al día» que despliega el detalle. Arriba del resumen, una frase de 15 px con lo que más pesa.
- **Bloques sin datos plegados en una línea**: los sin fuente siguen juntos en «Sin fuente para este cliente»; los conectados con todo a cero (Analytics de ECIJA, Meta sin anuncios, correo sin envíos) son un `details` de una línea «Web (Analytics) · todo a cero en … · Ver por qué». Vacíos internos con `vacioLinea()`.
- Coste por lead con `colorCifra('coste_lead')`. Fuera códigos en textos (id de cuenta, «clave de proyectos 403», «gg.py»). Arreglado de paso: `const URL` tapaba `window.URL` (los enlaces no se construían).
- Pruebas: `pruebas_diseno.py` limpio; 7 personas × 3 anchos sin errores, sin scroll horizontal, sin texto < 12 px. Capturas en `capturas/_n6/informe/`.
- Por qué no 10: el PDF pierde su regla de impresión hasta que E0 ponga `@media print` común (pedido en dudas_pintura); en gráficos estrechos se pisan las dos últimas fechas (es de `grafico()`, pedido a E0); la tarjeta de Meta en móvil sigue en carrusel común.

## Ronda de velocidad (2-oct noche, auditoría 37 causa 5) · informe partido
- `fuentes_informe/partir_informe.py` (lo llama `generar_informe.py` al final; se puede lanzar suelto) deja `data/informe/i_<periodo>.json` (índice: qué fuentes trae cada cliente, 4 KB) y `data/informe/c_<periodo>/<cliente>.json` (la fila del cliente dentro de `filas`, para que servir.py la recorte igual: un cliente ajeno llega con `filas: []`). Alta en `reglas_permisos.json` (`informe/i_*`, `informe/c_*/*`). `p_<periodo>` se queda para la paridad y de respaldo.
- `informe.js`: comun, paridad y acciones a la vez; al abrir, índice + fila del cliente (y la del último abierto, adelantada). 4G lenta, 390 px: 4,7 s → 1,9 s y 378 KB → 21-27 KB (tabla en `_ESTADO_mi_dia.md`). Texto de pantalla idéntico en 36 casos.
- Pedido del coordinador: las «consultas» de Search Console que son filas de exportación de Google Ads (`fuentes/comun.consulta_basura`) se quitan al partir (también en `p_<periodo>`) y en `generar_informe.py`: Octoedro 30-46 por periodo, Bonet 3-4, Écija 1 (julio).

## V2-C1 (3-oct, barrido v1)
- Meta todo a cero → una línea «Sin actividad en Meta en este periodo: 0 impresiones y 0 leads» en vez de seis tarjetas con «—». «Posición media» sin palabras dentro → «Fuera del top 100». «Su Looker» y los meses de «Otros periodos con informe» con zona de toque de 32 px (C-20).

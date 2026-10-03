# _ESTADO · M11 Horas y productividad (E7 · puntos 4 y 5 de Mili) · 2-oct-2026

## Hecho
- `modulos/horas.js` · alta en `indice.js` y `reglas_permisos.json → datos_de_modulo["horas/horas"]`.
- Datos: `fuentes_horas/generar_horas.py` (lee la caché de `fuentes_produccion/extraer_clickup.py`, llave propia; anomalías de `build/datos.json → v7.anomalias`, el detector de horas raras de build.py) → `data/horas/horas.json`.
- Pestañas: **Quién imputa** (ayer por debajo de 8 h con el umbral del catálogo de RRHH, sin nada, semana, mes; copiar recordatorio, envío en W7; accounts y especialistas aparte), **Equipo por mes** (% imputado de 7 meses por grupo en barras; tabla alfabética sin ordenar por productividad · D-83), **Por persona / Mis horas** (imputadas frente a 128 h menos ausencias, ayer, semana, días sin imputar, tareas resueltas con desvío frente a su mediana de 3 meses; barras de 7 meses con raya de esperadas; horas por tipo de tarea sin cliente; productividad frente a sí misma y frente a la mediana del equipo en su tipo de tarea), **Horas raras** (Correcto / Hablar / Error en cola simulada; % revisadas con el umbral del catálogo de RRHH).
- Sello «horas incompletas» siempre arriba (69 % imputado en 6 meses; D-27: verde desde el 90 %, si no ámbar; nunca rojo). Mes en curso hasta ayer. Meses antes de la primera imputación, sin dato (no cuentan como 0).
- Recorte: Lucía y Camilo, solo lo suyo; Valeria 6 personas, Yessica 4, Constanza 8 (su gente, regla del jefe); Mili, Cecilia y Tomás, 33. El cliente de una hora rara va en `raras_cliente` con `cliente_id` + `persona_id`: Cecilia recibe 98 horas raras y 0 clientes (D-84); Lucía, 0. Sin sueldos ni euros.

## Cifras contrastadas
Horas por persona y mes iguales a la extracción independiente de cu.py (`_crudo/clickup/horas.json`): Camilo sep 182,2 · ago 173,0; Lina sep 104,6; Jerónimo sep 145,1; Gustavo sep 177,4.
Pendiente la prueba de aceptación de Mili (tareas de septiembre contadas a mano en ClickUp, ±1): Camilo 143, Lara 147, Jerónimo 145 según la app.

## Pruebas
`fuentes_produccion/probar_equipo.py`: 9 personas × 2 anchos × todas las pestañas, 0 errores propios, 0 desbordes. Capturas en `capturas/horas/`.

## Falta / dudas
- Tabla de ausencias (M20): hoy las esperadas no descuentan nada. «Ver cliente» no existe como estado en ClickUp. Las etiquetas «formación» y «fuera de alcance» (exigencias 25 y 65) no existen todavía (W7).
- Revisión con Coti, Mili y Agus (R15): pendiente.

## Ronda de arreglos (2-oct noche) · fallo de la auditoría → qué se ha hecho
| Fallo | Origen | Estado |
|---|---|---|
| El día se corta a la hora de Madrid: registros de Argentina y Venezuela cambian de día (Carlos Viur, ayer 8,1 frente a 6,6) | 28 · E-16 | **Arreglado**: cada registro va al día de trabajo en la zona de su persona (`fuentes_horas/zonas.json`: Argentina por defecto, Yadibeth Venezuela, Manuel y Tomás Madrid; cuando personas.json tenga «zona», manda esa). El mes y los totales siguen en Madrid, como ClickUp: no cambian (Carlos Viur septiembre 145,3 h igual). 423 registros cambian de día. «Ayer» y «esta semana», por persona. Carlos Viur ayer: 6,6 h |
| `ReferenceError: Cannot access 'M'` (línea 102, pestaña Imputa) | dudas_pintura | **Arreglado** (ya en la primera ronda; probado otra vez con las 9 personas) |
| «No imputan» 9/28 en Personas frente a 14/33 en Horas | 22 · I-09 | **Arreglado**: definición única (activas que imputan, sin bajas ni setters, 0 h el último día laborable en su zona). Horas, Personas y la verdad dan 9 de 28; `pruebas_coherencia.py` en verde |
| El filtro dice «Septiembre» y los tiles enseñan «Ayer (1 oct)» | 22 · I-12 / 29 | **Arreglado**: pestaña «Ayer y esta semana» sin selector de mes; el mes solo en «Equipo por mes» y «Por persona» |
| Mili no puede filtrar por puesto | 29 | **Arreglado**: chips por puesto (Accounts, Publicidad, CRM, Outreach, SEO, Web, Redes, Producción creativa, Jefas) en «Ayer y esta semana» y en «Equipo por mes»; se quedan al recargar |
| «D-27», «W7», «02-10-2026 11:06» en pantalla | 29 | **Arreglado**: textos en llano; la hora del detector ahora sale como «hoy» |
| 0 h pintado como «0,0 h» | 26 · E82 | **Arreglado**: «sin imputar» |
| Atajo a las horas de ClickUp | 26 parte C | **Hecho**: «Abrir mis horas en ClickUp» (enlace a Timesheets del espacio, por comprobar a mano que abre la vista de la persona) y la tarea de cada hora rara |
| Tipos de acción de horas raras no permitidos | 27 / ronda 6 | **Arreglado**: `hora_rara_correcto/hablar/error` en `acciones_permitidas` |
| Denominadores sin explicar | 22 | **Arreglado**: «Cuentan 28 personas: las activas que imputan horas (sin bajas ni setters). Es la misma lista que usa Personas.» |

Pruebas: las mismas que Producción; capturas `capturas/horas/r3_*`.

## Ronda 4 · guía de diseño (auditoría 30) y encargos del coordinador · 2-oct noche
- Fuera las hojas de estilos propias (`seo-estilos`, `cap-estilos`, `eq-estilos`): clases comunes (fila, pila, sub, chip, lista-i, rejilla, titulo-seccion) y estilo en línea solo con tokens (`var(--s-*, valor)`), nada por debajo de 12 px, cifras con punto de miles. Estado de fila = punto + texto en tinta. Línea de fuentes → un chip «Datos al día» que se despliega.
- Gráficos: `barras()` de `produccion_comun.js` usa ya el motor común `grafico()` de componentes.js; barras de progreso, embudo y ventanas, los comunes.
- SEO/web: pestaña Webs con columnas de Modular DS (Copia · Actualizaciones · Seguridad · Fuera de RO, con «bloqueada solo para RO»); hoy «Modular sin conectar» con el paso de Tomás (clave de solo lectura + pegar.sh). Camino conectado probado con datos simulados en el navegador.
- Horas: zona horaria de cada persona desde personas.json (Valeria hora de Venezuela, Sofía hora de España) en cabecera, listas, tabla y ficha.
- Producción: Camilo con la etiqueta «transversal» (copy, responde ante Mili), «sin cartera propia».
- Captación: Kiosko (tienda online) fuera de los leads de la casa (143 en vez de 1.562) y del techo de 35 € (4 de 8 en vez de 5 de 9), con nota en su tarjeta.
- Pruebas: 7 personas × 1440/390 × 7 rutas con todas las pestañas: 0 errores, 0 desbordes, 0 textos < 12 px · coherencia 0 errores · escáner limpio · pruebas_e0: 1 fallo ajeno (/api/cliente de Gustavo, «serie»).

## N6 · diseño 10/10 (2-oct, noche)
- **Fuera el «null»** pintado en «Ayer y esta semana» (Valeria, Yessica, Jerónimo…): `replaceChildren` recibía un `null` cuando no había panel de «menos de 8 h» o indicador; ahora se filtra.
- Gráfico: solo el motor común `grafico()` (fuera el dibujo SVG propio de respaldo `barrasLocal` de produccion_comun.js). Radios solo con tokens (`--r-s/m/full`).
- Dos columnas propias que se apilan en el móvil (`dosColumnas()`): la clase común `.dos` no se apilaba a 390 px y cortaba «En qué se fueron las horas» y «Con su mismo tipo de tarea» (apuntado en dudas_pintura.md).
- Aviso «Horas incompletas» de una línea arriba; la explicación (128 h, zonas horarias, periodo) plegada al pie en «Cómo se cuentan las horas». Fuera la ficha del catálogo que repetía el 23 de «Ayer por debajo de 8 h» (su «qué es», plegado). Vacíos en bloque con `vacioLinea()`. Tarjeta «Sin imputar ayer» de una línea.
- Horas raras: 15 a la vista y «Ver más» (8 en el móvil): Tomás 390 px de 21.920 → 2.822 px. Tabla del equipo a 15 filas (8 en el móvil) y buscador a 280 px.
- Periodo: **no usa `usa_periodo`**. Las horas solo existen por mes completo (ClickUp), así que se queda el selector de mes propio, con la frase «Mes completo (ClickUp guarda las horas por mes)»; «Ayer» y «Esta semana» son ventanas fijas y las horas raras, últimos 30 días (dicho en «Cómo se cuentan las horas»).
- Medidas: 7 personas × 1440/1024/390, todas las pestañas: 0 errores, 0 scroll horizontal, 0 textos < 12 px, 0 «null». Capturas en `capturas/_n6/horas/`.
- Nota contra la auditoría 30: **6,0 → 8,5**. Falta: «Ayer y esta semana» con 9 + 14 personas en lista sigue siendo larga, y las tablas apilables de productividad en el móvil ocupan mucho.
- **N6 · segunda pasada:** «Ayer y esta semana» abre con quien está por debajo (sin imputar y menos de 8 h), 8 personas a la vista en cada lista y «Ver todas (N)» que despliega el resto; las cifras van después. Tomás 1440: 1.828 px; 390: 2.083. n6_cap 42 pantallas, 0 con problemas; pruebas_diseno limpio. **Nota: 9,0.**

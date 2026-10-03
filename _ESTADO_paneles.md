# N1 · Paneles de herramientas · estado 2-oct-2026 (noche)

## Hecho
- **Mapa de paridad**: `../33_PARIDAD_PANELES_HERRAMIENTAS.md`. 55 vistas que el equipo usa de verdad: **45 en la app, 7 a medias, 3 faltan** (antes: 28 completas y 2 a medias; esta noche entran 17 completas y 5 a medias). También dentro de la app: `#/paneles/mapa`.
- **Periodos**: inventario por módulo en el 33 §2; petición a E0 del selector común `ctx.periodo` con la especificación exacta en `../dudas_pintura.md` → **D-P-N1**. Hoy solo 6 módulos tienen selector; el resto, ventanas fijas.
- **Módulo nuevo `paneles`** (grupo Clientes), alta en `modulos/indice.js` y en `reglas_permisos.json → datos_de_modulo` (un patrón por herramienta con `excluir_puestos`; Desk y Zadarma solo `direccion`, `operaciones`, `proyectos`). No toqué ningún módulo de otro dueño: todos tenían el `_ESTADO` editado en la última hora (ronda de arreglos).
  - Meta Ads: tarjetas, gasto/leads/impresiones por día, tabla de campañas, conjuntos y anuncios con importe, leads, coste por lead, impresiones, alcance, frecuencia, clics, CTR, presupuesto y entrega; chips «Activas ahora».
  - GoHighLevel: embudo por etapa (número y valor) con chips por embudo, ganadas/perdidas/tasa de cierre/valor, por estado y por origen; citas por estado, asistencia y por día; contactos nuevos, total, conversaciones sin leer y canal.
  - Analytics: Resumen (8 tarjetas, gráfico conmutable, sesiones por canal), Adquisición (canal, fuente/medio, primer canal, campañas), Interacción (eventos), Eventos clave, Páginas (páginas y destino), Tecnología y lugar.
  - Search Console: Rendimiento (4 tarjetas, gráfico, consultas, páginas, países, dispositivos, aparición), Indexación (sitemaps + inspección de las 15 páginas con más clics), Experiencia (PageSpeed: campo y laboratorio, móvil y ordenador).
  - Metricool: por red, seguidores, alcance, impresiones, interacciones, visitas y publicaciones por día.
  - Empresa: Zoho Desk (nuevos, cerrados, abiertos, fuera de plazo, días hasta cerrar, por persona, canal y departamento) y Zadarma (llamadas, entrantes, sin contestar, duración, por extensión con nombre y por hora).
- **Periodo común local** (`modulos/paneles_periodo.js` y su gemela `fuentes_paneles/periodos.py`): hoy, ayer, 7 d, 30 d, este mes, mes anterior, trimestre, año, a medida; comparar con periodo anterior, año anterior o sin comparar; recordado por persona en `localStorage`. Con «a medida», tarjetas y gráfico exactos desde la serie diaria; las tablas piden un periodo fijo (dicho en pantalla).

## Datos (`fuentes_paneles/generar_paneles.py`, solo lectura)
Analytics 32 clientes · Search Console 30 (27 con datos; Busbac, Optimalia y Romero Martínez dan 403) · Meta 28 cuentas (series por tramos de 90 días) · GHL 39 subcuentas (ids cortos e1/s1, sin nombres de contactos; la llave rota y se guarda sola; token de acceso en `~/.cache/ro_tokens/`, fuera del proyecto) · Metricool 23 marcas · Desk 5.000 tickets desde 24-nov-2025 (1 de 30 departamentos legible) · Zadarma 774 llamadas en 95 días. `--cache` rehace `data/paneles/` en segundos. Search Console con datos definitivos (`final`), como Looker y el Informe.

## Cifras contrastadas
1. Kiosko Box · Meta 30 días: **4.793,45 € y 5.340 leads** = auditoría de cifras y Informe del cliente (4.793,45 € / 5.340).
2. FusterGüell · Analytics septiembre: **2.131 usuarios** = Informe del cliente (2.131) ≈ Looker «2,1 mil».
3. Adade · Search Console septiembre: **71.034 impresiones** = Looker 71.034 (con datos «all» salían 73.127: por eso se usa «final»).
4. Musashi · GoHighLevel: **2.481 contactos** = `externos.json` y Salud del CRM (2.481).

## Pruebas
`fuentes_paneles/capturar_paneles.py <puerto>`: 7 personas (tomas, mili, lucia, valeria, yessica, constanza, setter_ana) a 1440 y 390 px sin errores de consola, sin desbordar y cada una con sus herramientas (Yessica solo GoHighLevel; setter_ana nada); recorrido de 6 clientes × 18 vistas × 3 periodos (30 d, mes anterior con año anterior, a medida) + Desk, Zadarma y mapa: **0 problemas**. Servidor: Lucía recibe 12 clientes; Desk a Lucía 403; Meta a Yessica 403; Search Console a Valeria 403; setter_ana 403. `escaner_secretos.py --proyecto`: nada de paneles. Capturas: `capturas/paneles/` (24 + 14 por persona).

## Falta / para Tomás
- **Clave de PageSpeed** (`google_api_key` en el llavero): sin ella Google corta (hoy 429 en las 36 webs) → Experiencia vacía con aviso «Falta la clave».
- SE Ranking competencia (clave de proyectos 403), Google Ads (Windsor), ficha de Google (Business Profile), lector en 6 propiedades y en Search Console de Busbac, Optimalia y Romero Martínez, departamentos de Desk.
- **E0**: `ctx.periodo` (D-P-N1) e icono `paneles: 'capas'` en `ICONO_MODULO` (hoy cae al del grupo). Cuando esté, el módulo borra `paneles_periodo.js`.
- Recarga: añadir `python3 fuentes_paneles/generar_paneles.py` a `recarga.json` (≈15 min en vivo; GHL y Search Console son lo lento).

## N6 · diseño 10/10 (2-oct, noche)
- **Periodo común**: `usa_periodo: true`; lee `ctx.periodo` y escucha `ctx.alCambiarPeriodo` (repinta solo la vista, sin acumular oyentes al cambiar de cliente o herramienta). **Fuera el selector propio y `modulos/paneles_periodo.js` borrado** (nada lo importaba; solo comentarios en `componentes.js` y `fuentes_paneles/periodos.py`). Search Console con «Hoy/Ayer» lo dice en una línea; con «A medida» las tablas de cada herramienta (que solo existen para los periodos fijos) lo dicen en una línea.
- **Sin hoja propia**: fuera `estilos()` y las clases `pp-*`; solo componentes y tokens. Gráficos con `grafico()` (letra de 12 px a cualquier ancho; antes 4,9 px en el móvil). Cifras con `fmt` (fuera el formateador propio). Embudo de GoHighLevel con `embudoBarras()` (por embudo, con su separador en mayúsculas).
- **Composición**: selector de cliente (el nombre sale una vez) + «Otros paneles ▾» (mapa, Desk y Zadarma) en una fila; pestañas de herramienta; vistas como chips con la frescura y «Abrir en …» en la misma fila; tarjetas → gráfico → tablas; explicaciones plegadas al pie («Qué se ve aquí», «De dónde sale», «Qué departamentos se ven»); «Sin conectar» al final.
- **Tarjetas**: sin «—» gigante (gris y «Sin dato»); «frente al periodo anterior» corto (las fechas están en la barra); coste por lead con `colorCifra('coste_lead')` (techo 35 €; Kiosko fuera). Analytics sin ningún dato → una sola línea en vez de 8 tarjetas vacías.
- **Tablas**: 15 filas + «Ver más», `clave` en todas las columnas (ordenables por la cifra), nombre con ancho mínimo (no palabra por línea), deltas a 12 px; reparto de tickets por persona/canal sin rojo (rojo con cuentagotas).
- **Pruebas**: `pruebas_diseno.py` → paneles.js limpio. 7 personas (tomas, mili, valeria, yessica, jeronimo, lucia, camilo) × 1440/1024/390 × 4 rutas (cliente, mapa, Desk, Zadarma): 72 pantallas, 0 errores de consola, 0 desbordes, 0 textos < 12 px, 0 «null». Capturas en `capturas/_n6/paneles/` (antes en `capturas/_n6/_antes/paneles/`).
- **Nota (auditoría 30)**: no tenía nota propia (módulo nuevo); con los criterios de la guía, **antes ≈ 5,5 → ahora 9**. Falta para el 10: el menú «Más ▾» común sin el «null» (dudas_pintura D-P-N6) y que la barra del periodo se oculte en el mapa.

## R12 · arreglos tras la auditoría final (carril E, 2-oct noche)
- **A2 «7 días no cambia nada» (Tomás) → arreglado.** El cliente por defecto de Tomás (ECIJA) no tiene Analytics desde el 31-jul: el periodo no podía cambiar nada. Ahora, sin herramienta en el enlace, si la primera no tiene datos en los últimos 14 días se abre la siguiente con datos (Search Console), y en Analytics se dice «no tiene datos desde el 31-jul: el periodo de arriba no cambia nada aquí hasta que vuelva a medir». Probado: Hoy, 7 días, 30 días y este mes cambian el contenido.

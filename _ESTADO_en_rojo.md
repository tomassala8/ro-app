# _ESTADO · M2 «En rojo» (ronda de arreglos, 2-oct noche)

**Dueño:** sesión de la ola 0 (sistema visual). Ficheros: `modulos/en_rojo.js`, `fuentes_en_rojo/generar_atajos.py` → `data/en_rojo/atajos.json`.
Ediciones localizadas permitidas: alta de `en_rojo/atajos` en `reglas_permisos.json` (`datos_de_modulo`), «en-rojo» en `ADOPTADOS` y tres comprobaciones en `pruebas_coherencia.py`, fila del LEEME y `dudas_pintura.md` (D-P03, D-P04).

## Qué hace ahora
- **Lista común (todo el equipo):** la verdad única de los 68 clientes: **11 críticos · 43 en atención · 14 bien**. Gravedad, motivo sin cifras y account (`ctx.nombre`). Sin importes ni datos de contactos.
- **Chips de gravedad que se quedan.** Por defecto se ve «Crítico» (11), para que el rojo signifique algo; con un toque se pasa a Atención, Bien o Todos. También se filtra por account, por motivo y con «Solo mis clientes».
- **Lo primero hoy:** solo los críticos (de su cartera o, para operaciones y dirección, de la casa), como mucho 7. Cada uno con «Abrir la ficha», el atajo de la herramienta donde se arregla, «Por qué» y «Marcar visto».
- **Cada fila** con «Ficha» y los atajos de Desk, ClickUp y GHL (solo si la persona puede abrir el cliente; si no, el candado).
- **Detalle:** cabecera con gravedad, account, alta y «Abrir la ficha», más una barra «Abrir en …» con 8 herramientas. Las que faltan salen en gris con «falta emparejar» (las empareja Mili). Debajo, tiles de la verdad: correo más antiguo, última reunión, bloqueos, leads de Meta que llegan al CRM, encendido del alta y salud con sello «a medias». Cada señal lleva su atajo. Las señales repetidas dentro de una compuesta se juntan en una.

## Cifras contrastadas a mano (2-oct)
| Cifra en pantalla | Fuente | Resultado |
|---|---|---|
| 11 / 43 / 14 | `data/verdad/clientes.json → resumen` | ✓ igual |
| GAC: 0 de 101 leads llegan al CRM (fuga grave, crítico) | verdad: `leads_meta_7d 101`, `leads_ghl_7d 0` | ✓ |
| GAC: correo más antiguo 20 días laborables | verdad: `correos_sin_responder_dias 20` | ✓ |
| Lucía: 1 cliente suyo en crítico de 12 | verdad y cartera de Lucía (12 con detalle en `pruebas_e0`) | ✓ |

## Fallo de la auditoría → estado
| Auditoría | Fallo | Estado |
|---|---|---|
| 22 · I-04, 26 · E93, 29 | 53 de 68 «en rojo»: el rojo no significa nada | **Arreglado.** Gravedad única (11 críticos). Por defecto se ven solo los críticos y «Lo primero hoy» lleva como mucho 7 |
| 22 · B-03 · tabla fila 69, 29 | «Cliente nuevo sin account» con account al lado (AGC, Marlex, Imfor, Billeo, TST) | **Arreglado.** «Sin account» solo si la verdad no tiene account (comprobación nueva en `pruebas_coherencia.py`, en verde) |
| 22 · tabla fila 68 | Emex con Candela y a la vez sin account | **Arreglado** en pantalla: account y «sin account» salen de la misma fila de la verdad |
| 22 · tabla fila 67, 29 | «7 de 16 nuevos» frente a 17 | **Arreglado.** «Nuevo» sale de `verdad.nuevo` (la misma lista que Clientes nuevos). Se quitó el tile del panel |
| 22 · tabla fila 72 | «Sin reunión»: 1 frente a 6 | **Arreglado.** `verdad.sin_reunion_mes_pasado` (la misma regla que Reuniones) |
| 22 · I-09, 26 · E34 | «Bloqueo sin resolver» (más de 2 días) frente a bloqueos de Producción | **Arreglado** en En rojo: solo «bloqueo callado» de más de 5 días (regla de la verdad). La alarma del panel sigue en `alarmas.json` (es de E0): D-P04 |
| 22 · I-04 | «Salud 100» con alarma roja (Akua) | **Arreglado.** La salud de la verdad (fórmula provisional, sello «a medias») solo sale en el detalle, junto a la gravedad |
| 29 · glosario 1 y 6, regla de textos | «Propuesta ⚠️: verde 0», «(D-90)», «(G2)», «1 tarea(s)» | **Arreglado.** Textos nuevos sin códigos ni emojis, `limpiaTexto` en los motivos, «50.8 días» pasa a «51 días». La prueba busca D-, G2, ⭐, ⚠️, (B5), (A8): no sale ninguno |
| 26 · C.3 | Faltaba la barra de atajos del cliente (Meta, GHL, Desk, Drive) | **Arreglado.** 8 atajos: Desk 35, ClickUp 61, GHL 38, Meta 28, Drive 55, carpeta 56, Analytics 26 y Search Console 31 de 68. Los que faltan, en gris. Cada clic queda en el rastro |
| 29 | Tabla cortada por la derecha a 1024 | **Mejorado.** Dos columnas menos (Alarmas y Salud); la tabla común ya tiene desplazamiento propio |
| 28 · E-05 | Cuota de `clientes.json` distinta de Airtable | **No aplica ya:** En rojo no enseña la cuota |
| 28 · E-20 | Avisar si el account no imputa en 30 días | **No aplica aquí:** lo lleva la verdad de equipo (Horas y Personas). Queda propuesto para un tile de En rojo cuando la verdad dé el campo por cliente |
| 27 · M2 | Lo leído en «ver como» no deja huella | **No aplica** (es de `servir.py`, E0 ronda 6). Los clics en atajos y «Marcar visto» sí dejan rastro |
| 22 · P-12, P-14 | Inicio por puesto; primer Tab | **No aplica** (es de `app.js`; Mi día ya es el inicio) |
| — | El contador del menú sigue en 53 | **Pendiente de E0** (es de `app.js`): D-P03 |

## Pruebas (2-oct noche, `servir.py --puerto 8791`)
- `pruebas_e0.py --puerto 8791`: **TODO BIEN**. La setter recibe 68 filas comunes y 0 con detalle; Lucía 12; Tomás 68.
- `pruebas_coherencia.py`: las 3 comprobaciones de en-rojo en verde. Queda 1 ERROR de **agenda** («cliente en rojo con reunión = crítico»), que no es de este módulo.
- Atajos recortados por el servidor: Ana y Camilo 0, Lucía 12, Tomás 68.
- Las 7 personas (Tomás, Mili, Lucía, Valeria, Yessica, Constanza y Ana) a 1440 y 390 px sin errores de este módulo. Los únicos avisos son de `prospeccion` y `ventas-ro`, que E6 está editando (`_ventas_comun.js`).
- Teclado: Intro en una fila abre el detalle. Los chips cambian la lista (11, 43) y se recuerdan.
- Capturas: `capturas/en_rojo/r3_*` (20).

## Recarga
`python3 fuentes_en_rojo/generar_atajos.py` después de la ficha (portal), Captación y CRM. Solo lee ficheros y no llama a ninguna API.

## N6 · Diseño 10/10 (2-oct, noche) · nota que me pongo: **8,5 / 10** (auditoría 30: 6,0)
- `pruebas_diseno.py` limpio; espaciados en línea pasados a la escala de 4 (12/16/18 → tokens).
- «Lo primero hoy» arriba y las cifras debajo. Quien lleva cartera y además dirige (Tomás, Mili, Coti) ve los críticos de la casa cuando los suyos están a cero, en vez de una caja vacía grande. Texto llano (fuera el nombre de fichero).
- 7 personas × 3 anchos sin errores, sin scroll horizontal, sin texto < 12 px. Capturas en `capturas/_n6/en_rojo/`.
- Por qué no 10: cabeceras de tabla y filtros `<select>` son de `tablaDensa` (comunes); en «Crítico» todas las pastillas son rojas por definición (en «Todos» son el 15 %).

## V2 · carril V2-C2 (3-oct)
- **A-M15** «Marcar visto» en la cabecera del crítico · «Sin dato de GHL · 104 en Meta» en vez de «— de 104» · la salud no sale verde junto a «Crítico» (lo explica). Consejo de frescura: `ia.py`.
- **C-13** setters fuera (`setters: null`); lo manda `reglas_permisos.json`: pedido a R16.

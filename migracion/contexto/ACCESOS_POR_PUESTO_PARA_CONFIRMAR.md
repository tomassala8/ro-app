> **Estado a 4-oct: CONFIRMADA entera por dirección (09:42 y 09:45).** No queda nada por confirmar. Dónde está apuntado: `migracion/PENDIENTES_LOGICA.md` › tabla de decisiones (D1 dinero de proyectos, D2 jefaturas/proyectos/técnico de altas solo los da dirección, D3 Bandeja de la jefatura de SEO, D4 Captación de producción y traffickers, D5 menús de 8-12 entradas = L-40) › «Cambios de matriz decididos…» (lista exacta de valores de `reglas_permisos.json` e `indice.js`) › fila L-25 (silla `altas` del técnico de altas). Lo que va en **negrita** abajo es lo que cambia; lo demás es la matriz de hoy y no se toca. Si Astra no lo cerró (L-25 sin «arreglado hoy»), lo aplica Cursor en el motor nuevo (F4.1/F4.2) y en F5.10, con `migracion/pruebas_L-25.py`.
> **Copia saneada para Cursor (4-oct-2026).** Fuente: `/mnt/project-files/feedback_herramienta/`. Personas por su puesto.

# Accesos por puesto · para que dirección los confirme (4-oct-2026)

Sacado de `reglas_permisos.json` e `indice.js` de la app (versión del 3-oct). Incluye ya las respuestas de dirección a D1-D8, a las tres preguntas de las 09:42 y a los supuestos de las 09:45. **Cerrada.** Lo que cambia respecto a hoy va en **negrita**.

**Leyenda:** **Todos** = todos los clientes · **Suyos** = solo los clientes que lleva · **Resumen** = sin detalle · **No** = no lo ve.

## 1. Lo que ya está decidido

- **Por puesto (opción B).** Cada uno ve solo lo de su rol, para no distraerse, aunque los permisos sean más complejos.
- **Siempre cerrado:**
  - sueldos, que solo ven dirección y RRHH;
  - los datos personales de los leads, que salen tapados y quedan apuntados en el rastro si alguien los abre;
  - el dinero de la agencia: facturación total, caja y beneficio. **Solo lo ven dirección y administración.**
- **Proyectos** ve la cuota y la inversión de cada cliente y, cuando exista, el beneficio por cliente. No es prioridad montarlo.
- **Finanzas de dirección** no se asigna a nadie más que a dirección.
- **Traffickers** ven la Captación de todos los clientes.

## 2. Tabla por puesto

| Puesto | Clientes (ficha, paneles, En rojo) | Bandeja (correos de clientes) | Su trabajo | Ventas de RO | Dinero de cada cliente | Dinero de la agencia | Sueldos | Ajustes y sistema |
|---|---|---|---|---|---|---|---|---|
| Dirección | Todos | Todos | Todo | Todo | Sí | Sí | Sí | Sí |
| Finanzas de dirección (solo la persona de dirección) | Todos | Todos | Todo | No | Sí | Sí | No | No |
| Administración y cobros | Resumen (cabecera, cuota, contrato, accesos) | No | Cobros | No | Cuota y cobros de cada cliente | Sí, también los totales | No | No |
| Operaciones | Todos | Todos | Todo | Resumen | Cuota, inversión y rentabilidad | No | No | Sí, **pero no da jefaturas, proyectos ni técnico de altas** |
| Proyectos | Todos | Todos | Todo | Resumen | **Cuota, inversión y beneficio por cliente cuando exista** | No | No | No |
| RRHH | No (solo En rojo) | No | Personas, horas | No | No | No | Sí | Resumen |
| Account | Suyos | Suyos | Suyos | No | Cuota e inversión de sus clientes | No | No | No |
| Trafficker de Meta | Suyos | Suyos | **Captación de todos** | No | **Inversión de todos** | No | No | No |
| Jefa de publicidad | Todos | Todos | Captación de todos | No | Inversión de todos | No | No | No |
| Especialista GHL | Suyos | Suyos | CRM de sus clientes | No | No | No | No | No |
| Jefa de CRM y outreach | Todos | Todos | CRM y prospección | Resumen | No | No | No | No |
| Técnico de altas | Todos | **Los clientes en alta** | Altas, conexiones, envíos | No | No | No | No | Conexiones |
| Jefe de SEO | Todos | **Solo quejas de SEO y web** | SEO y web de todos | No | No | No | No | No |
| SEO, Ficha de Google, Web | Suyos | No | Suyos | No | No | No | No | No |
| Redes | Resumen | No | Redes de sus clientes | No | No | No | No | No |
| Producción creativa | Resumen | No | Producción, **sin Captación** | No | No | No | No | No |
| Setters | No | No | Sus leads | Lo suyo | No | No | No | No |
| Ventas de RO | No | No | Ventas | Todo | No | No | No | No |
| Outreach | Informes de los suyos | No | Prospección suya | Resumen | No | No | No | No |

**Menús:** de 8 a 12 entradas por puesto, con lo que más usa cada uno. El resto va en «Más».

## 3. Estado

dirección la confirmó el 4-oct a las 09:45. Astra aplica hoy los cambios de la sección 6 del súper prompt, y lo que no cierre lo recoge Cursor esta noche.

# Diagnósticos de calidad · catálogo (4-oct-2026)

Segunda familia de funciones, hermana del semáforo de riesgo de baja. No miran **cuánto** llega, miran **qué** llega.
Cada diagnóstico da rojo, ámbar, verde o «sin dato» (poca muestra), una frase y sus cifras, y apunta a su ficha en el
cerebro `calidad` (`fuentes_consejos/cerebros/calidad.json`), que dice qué hacer.

Leyenda: **✅ construido** en este PR · **🟡 se puede construir ya** (el dato existe en la app) · **⚪ falta el dato**.

## CRM y embudo (GoHighLevel)

| Diagnóstico | La señal | El dato | ¿Hoy? |
|---|---|---|---|
| Leads no calificados | % sin teléfono, teléfono mal escrito o de fuera de España, correo falso o de usar y tirar, spam, duplicados, WhatsApp que falla | Contactos de 30 días (`ghl_vivo.json`) | ✅ |
| El despacho no atiende | % con intento de una persona en 24 h, sin tocar, p90, cuántos responden; avisa si llama fuera del CRM | Conversaciones de cada lead | ✅ |
| Los leads no avanzan | % que llega a cita, oportunidades que no se movieron en 7 días y en qué etapa se quedan, asistencia | Oportunidades y citas | ✅ |
| **Veredicto del embudo** | leads malos · despacho no atiende · contacta pero no agenda · no vienen · sano | Los tres anteriores, de arriba abajo | ✅ |
| Motivos de pérdida | % de Perdidos por «yo no he pedido nada», «fuera de perímetro», «solo precio» | Oportunidades perdidas (hoy la app solo lee las abiertas) | 🟡 |

## Publicidad (Meta)

| Diagnóstico | La señal | El dato | ¿Hoy? |
|---|---|---|---|
| Leads baratos pero malos | Coste por lead en objetivo, pero el coste por lead **que se puede llamar** se pasa más de un 30 % | Captación + calidad del lead | ✅ |
| Leads de fuera de España | Prefijos +52, +57, +54… (segmentación por idioma) | Dentro de «leads no calificados» | ✅ |
| Formulario instantáneo frente a landing | Calidad del lead según de dónde entra | Origen del contacto en GHL (a veces solo dice «facebook») | 🟡 |
| El anuncio que trae la basura | Calidad por campaña o anuncio | Falta guardar la campaña en el contacto (UTM) | ⚪ |

## SEO

| Diagnóstico | La señal | El dato | ¿Hoy? |
|---|---|---|---|
| Mucho tráfico, pero de blog | % de clics de Google que van al blog frente a servicio y portada | Search Console, páginas (este PR sube de 12 a 250) | ✅ |
| Intención de las búsquedas | % de clics que son dudas («qué es», «modelo 303»), solo marca o gente que quiere contratar | Search Console, búsquedas | ✅ |
| Tráfico de fuera de la zona | Clics de otros países o provincias | Search Console por país (una llamada más) | 🟡 |
| Visitas orgánicas que no piden cita | Clics que suben y leads de origen orgánico que no | GHL origen + Search Console | 🟡 |

## Ficha de Google

| Diagnóstico | La señal | El dato | ¿Hoy? |
|---|---|---|---|
| Vistas sin acciones | Muchas vistas en Búsqueda y Maps, pocas llamadas, rutas o clics a la web | Rendimiento de la ficha | ⚪ Google aún no ha aprobado el acceso |
| Solo nos encuentran por el nombre | Búsquedas de marca frente a búsquedas de servicio | Términos de búsqueda de la ficha | ⚪ ídem |

## Web

| Diagnóstico | La señal | El dato | ¿Hoy? |
|---|---|---|---|
| Formularios con spam | Nombres sin sentido, enlaces, correos de usar y tirar | Dentro de «leads no calificados» | ✅ |
| Visitas que no convierten | Sesiones que suben y leads de la web que no | GA4 (ficha E1) + GHL | 🟡 |

## Redes

| Diagnóstico | La señal | El dato | ¿Hoy? |
|---|---|---|---|
| Alcance sin interacción | Publicaciones que se ven pero nadie comenta ni guarda, frente a su media | Metricool, 30 días | 🟡 |
| Redes que no traen a nadie | Leads con origen en redes orgánicas | GHL origen | 🟡 parcial |

## Setters y ventas de RO (nuestro propio embudo)

| Diagnóstico | La señal | El dato | ¿Hoy? |
|---|---|---|---|
| Nuestros leads no calificados | Lo mismo que en clientes, sobre la subcuenta de RO | `generar_ventas_ro.py` (reutiliza la función) | 🟡 |
| Citas que no cierran por perfil | Motivo de no cierre (tamaño, presupuesto, decisor) | No hay campo de motivo | ⚪ |

## Producción

| Diagnóstico | La señal | El dato | ¿Hoy? |
|---|---|---|---|
| Piezas que vuelven | % de piezas devueltas por el cliente, por cliente y por persona | Módulo de producción (devueltas) | 🟡 |

## Account y relación

Lo lleva el hilo «Semáforo de riesgo de baja» (resultados, silencio y quejas). Encaje: el eje de resultados puede leer el
veredicto del embudo para separar «resultados flojos por leads malos» de «por el despacho».

## Dirección (reservado)

| Diagnóstico | La señal | El dato | ¿Hoy? |
|---|---|---|---|
| Cliente que factura pero se come las horas | Horas imputadas frente a la cuota del cliente | Horas + dinero | 🟡 |

## Lo que tiene que decidir Tomás

1. ~~Umbrales de calidad del lead~~ Firmado 4-oct: ámbar 20 %, rojo 35 %.
2. ~~Gmail o Hotmail~~ Firmado 4-oct: no restan calidad de entrada; se cuentan como señal secundaria.
3. Blog: firmado 4-oct ámbar 50 % y rojo 70 %, pero si las páginas de servicio y portada suman al menos 100 clics en 28 días y el 25 % del total, baja un escalón (firmado 4-oct). Búsquedas informativas 60 % y marca 70 %, pendientes.

Todos están en `diagnosticos.py → UMBRALES`, con su fuente. Los que vienen del árbol del embudo (atención 90 % en 24 h,
cita 25 %, asistencia 60 % con 8 citas) ya están firmados en `ro-equipo:30_SKILLS/diagnostico-embudo-despacho`.

## Cómo se usa

```
python3 fuentes_diagnosticos/generar_diagnosticos.py        # lee lo ya generado → data/diagnosticos/diagnosticos.json
python3 fuentes_diagnosticos/probar_diagnosticos.py         # pruebas con datos inventados
python3 fuentes_consejos/cerebros/buscar.py --diagnostico crm_leads_no_calificados   # su ficha
```

Orden: `generar_crm.py` y `generar_seo.py` primero (dejan `ghl_vivo.json` y `gsc.json`), después este. Sin llamadas a APIs.
Privacidad: los correos y teléfonos de los leads se leen en memoria; a la salida solo van recuentos. El dinero va en
claves `cpl*` y `coste*`, que `servir.py` recorta a quien no ve la inversión.

Falta para verlo en pantalla: dar de alta el módulo en `reglas_permisos.json` y pintarlo en la ficha del cliente. Si
entra en la migración a Next + Nest, va como tabla `diagnostico` (cliente, id, estado, evidencia en JSON, fecha).

# Capa de datos (E1) · formato para los módulos

**2-oct-2026.** Los módulos **no llaman a ninguna API**: leen lo que deja `fuentes/generar_datos.py` en `data/`. En producción, `servir.py` (E0) y después el Worker recortan estos ficheros por persona antes de servirlos; un módulo nunca los lee directamente desde el navegador (regla R8).

## Ficheros

| Fichero | Qué es |
|---|---|
| `data/indice_clientes.json` | Lista de clientes: `id`, `nombre`, `activo_libro`, `en_panel`, `fichero`, `cobertura` y `estado_fuentes` (una letra por fuente). Para tablas y semáforos sin abrir 68 ficheros. |
| `data/clientes/<id>.json` | Todo lo de un cliente, con un bloque por fuente. |
| `data/fuentes.json` | Salud de las fuentes: estado, hora, edad, plan usado (A en vivo · B último fichero · C muestra manual), cuántos clientes tienen dato y reparto por estado. Es la pantalla «salud de las fuentes» (no «incidencias», X-06). |
| `data/emparejamientos.json` | Cliente ↔ cuenta de cada herramienta, con el identificador y el método. `copiados_entre_clientes` debe estar vacío. |
| `fuentes/dudas_emparejamiento.md` | Lo que tiene que mirar Agus. |

## Identificador del cliente

`id` = `slug(nombre del panel)`, el mismo que usa `build_data.py` (`gac`, `musashi-consultores`, `bit-24`). Los dos clientes que solo están en el portal (Think Value, JENASA) llevan el id del portal.

Cada fichero trae `ids` con el identificador del mismo cliente en las otras tablas:

```json
"ids": {"app": "abner-advisory", "panel": "Abner Advisory", "portal": "abner", "fase0": "abner",
        "captacion": "abner_advisory", "libro": "Abner Advisory"}
```

> **Ojo E0:** `20_FASE0_DATOS/asignaciones.json` usa el id del **portal** (`abner`, `ayg`, `kioskobox`), no el de la app (`abner-advisory`, `ayg-asesores`, `kiosko-box`). Para unir asignaciones con clientes, usar `ids.fase0`.

## Un fichero de cliente

```json
{
  "formato": 1,
  "id": "gac", "nombre": "GAC", "web": "https://gacgrup.com/",
  "activo_libro": "Activo",            // estado en el libro corregido (D-16): Activo · Baja · Proyecto · Extras sueltos · null
  "en_panel": true, "en_portal": true,
  "ids": { ... },
  "generado": "2026-10-02 14:29",
  "estado_fuentes": {"cartera": "bien", "desk": "dato_viejo", "seranking": "rota", ...},
  "alertas": [ … ],                   // todas las alertas de sus fuentes, con «fuente»
  "cobertura": {"con_dato": 20, "aplicables": 23, "bien": 17, "dato_viejo": 2, "rota": 1, ...},
  "fuentes": {
    "<fuente>": {
      "fuente": "Meta Ads",            // nombre legible
      "estado": "bien",                // bien · a_cero · rota · dato_viejo · sin_conectar · no_aplica
      "hora": "2026-10-02 14:16",      // hora del último dato de esa fuente (pintarla junto a la cifra, R5)
      "medicion": "hoy",               // hoy · medias · no   → sello «se mide hoy / a medias / todavía no»
      "nota": "…",                     // por qué está a medias, a cero o sin conectar (para el estado vacío útil)
      "emparejado": {"id": "act_28911839", "nombre": "GAC", "metodo": "…"},   // o null
      "prueba": "https://…",           // enlace al origen cuando lo hay (del número a la prueba, R7)
      "abrir": {"texto": "Abrir en Meta", "url": "https://…"},   // atajo; url null + "falta" = botón gris «Falta emparejar»
      "alertas": [{"gravedad": "rojo", "texto": "…", "dueno": "account"}],   // avisos que salen de la propia fuente
      "datos": { … }                   // propio de cada fuente (abajo)
    }
  }
}
```

**Regla para pintar:** `bien` y `dato_viejo` se pintan (el viejo, con la frescura en ámbar); `a_cero` se pinta como 0 con la nota; `rota` y `sin_conectar` van a estado vacío con la `nota`; `no_aplica` no se enseña. `medicion: "no"` nunca se pinta como número (va a «Fase 2», R5).

## Fuentes y su `datos`

| id | Qué | `datos` (campos principales) | Sensible (lo recorta `ver()`) |
|---|---|---|---|
| `cartera` | ClickUp Cartera | `account`, `semaforo`, `cuota`, `nuevo`, `riesgo_panel`, `agente_desk`, `rojo_manual{motivo, nota_tomas}` | `cuota` |
| `horas` | ClickUp horas | `horas_presup_mes`, `horas_mes`, `horas_mes_ant`, `pct_horas` (a medias: 52 % imputado) | rentabilidad |
| `tareas` | ClickUp tareas | `abiertas_por_estado`, `rev_pm`, `rev_tecnica`, `revision_mas_48h`, `creadas_mes(_ant)`, `no_planificadas_semana`, `vencidas`, `en_revision_detalle[]` | — |
| `informes` | Informes mensuales | `{ago, sep: {estado, fecha_envio, prueba, url, responsable}}` | — |
| `desk` | Zoho Desk | `tickets_abiertos`, `pendientes_horas`, `ult_correo_saliente`, `correo_esta_semana`, `sin_contestar[]`, `sin_agente[]` (número, asunto saneado, días, url) | — |
| `zadarma` | Llamadas | `septiembre`, `octubre` {contestadas, ≥30 s, intentos sin contestar, minutos, última, `por_persona`}, `resumen_panel`. **Sin números de teléfono.** | — |
| `reuniones` | CRM + Fathom + verificación | `ult_reunion`, `prox_reunion`, `dias_sin_reunion`, `historial[]`, `fathom_septiembre[]`, `verificacion_septiembre` | — |
| `outreach` | Chats, hojas | `canales`, `sep`, `oct` (muchos null), `nota` | — |
| `alarmas` | Panel de Mili | lista `{id, gravedad, tipo, texto, accion, enlace, desde, responsable}` | — |
| `arranque` | Altas nuevas | `firma`, `alta`, `dia`, `estado`, `hitos[]` | — |
| `chat` | Canal de ClickUp | `canal_id` | — |
| `ga4` | Google Analytics 4 (si midió el periodo anterior y ahora nada: estado `rota` con alerta roja «dejó de medir», nunca un cero gris) | `periodo`, `actual`, `anterior` {usuarios, sesiones, conversiones…}, `serie_usuarios`, `paginas`, `canales` | — |
| `gsc` | Search Console | `periodo`, `periodo_anterior`, `datos_hasta` (Google va 2-3 días por detrás: las dos ventanas de 30 días se cierran en el último día con datos), `actual`, `anterior` {clics, impresiones, ctr, posicion}, `serie_clics_impresiones`, `consultas` | — |
| `metricool` | Redes | `redes[]`, `instagram`/`linkedin` {seguidores, hace30} (programado: todavía no) | — |
| `ghl` | Subcuenta GHL (resumen) | `contactos`, `opp_open`, `opp_won`, `opp_lost` | — |
| `snov` | Correo en frío | `actual`, `anterior`, `campanas[]` | — |
| `meta` | Meta Ads (captacion.json) | `gasto`, `leads`, `cpl` por ventana (ayer, 7d, 7d_prev, 14d, mes, mes_anterior, 35d), `objetivo`, `presupuesto`, `metas`, `campanas[]`, `serie[]`, `severidad`, `motivos[]`, `avisos[]`, `zona`, `moneda` (plan B: `d30`, `sep`). Alertas: pago pendiente (rojo), zona horaria distinta de Madrid y moneda distinta del euro (ámbar). `excluidas`: cuentas duplicadas que nadie debe emparejar | inversión |
| `captacion_ghl` | Embudo GHL 90 d | `embudo`, `citas{7d,14d,mes,mes_anterior}`, `coste_por_cita` | inversión |
| `google_ads` | Windsor | `periodo`, `total{impresiones, clics, coste, conversiones}`, `cuentas[]` (hoy: muestra manual de septiembre) | inversión |
| `tiktok` | Windsor | `periodo`, `total` (hoy sin datos) | inversión |
| `seranking` | SE Ranking | `dominio`, `palabras_seguidas`, `proyecto_activo`, `resumen` (cuando la clave funcione) | — |
| `zoom` | Grabaciones | `periodo`, `reuniones[]{fecha, minutos, tema}` (sin enlaces ni códigos) | grabación |
| `libro` | Libro + Holded | `estado`, `segmento`, `cuota_actual`, `meses{AAAA-MM: €}`, `ltv`, `vida_meses`, `fecha_baja`, `motivo`, `facturas_holded[]` | `cuota`, `cobros` |
| `asignaciones` | Fase 0 (borrador) | `sillas{…}` sin personas de baja (pasa el siguiente de la silla), `servicios` (publicidad «sí» si su cuenta de Meta gastó, con `publicidad_fuente`), `huecos`, `filas[]`, `fuera_por_baja[]` | — |

## Cómo se regenera

```bash
cd 30_APP_PROTOTIPO/fuentes
python3 generar_datos.py                          # 0 llamadas: lee lo último de cada lector
python3 generar_datos.py --en-vivo meta,zoom      # o «todo»: externos, meta, windsor, seranking, zoom
python3 comprobar.py                              # prueba de aceptación (10 clientes + Meta en vivo, 3 llamadas)
```

Escribe a temporal y renombra (nunca un JSON a medias). Si el escáner de secretos encuentra un correo, un teléfono o una clave, **no escribe nada** y sale con código 2.

## Correcciones de emparejamiento

Todas en `fuentes/emparejamientos_manual.json`, por identificador: `meta` (cuenta buena), `meta_excluir`, `meta_sin_cliente_conocidas`, `ga4`, `gsc` (null = «sin conectar» con su motivo en la clave `_<cliente>`), `metricool` (id de marca), `ghl`, `google_ads`, `seranking`. Las de GA4, Search Console, Metricool y GHL se copian también al manual de la herramienta RO (`HERRAMIENTA_RO_2026-10-02/emparejamientos_manual.json`), que es el que usa `externos.py` para leer. Si una corrección todavía no se ha leído, el bloque sale `rota` con «corregida a mano y todavía sin leer», nunca con el dato de la cuenta mala.

## Orden de la recarga completa (una sola pasada)

1. `~/RO_HERRAMIENTAS/externos.py` (diario: Analytics, Search Console, Metricool y GHL; ~25-40 min).
2. `~/RO_HERRAMIENTAS/captacion/captacion.py` (Meta y embudo de GHL; lo mantiene Captación).
3. `build_data.py` (base).
4. `fuentes/generar_datos.py --en-vivo meta` (esta capa; 2 llamadas a Meta). En la recarga ligera, sin `--en-vivo`.
5. Los generadores de módulos que leen esta capa (bandeja, informes, captación, ficha, nuevos, CRM, SEO, redes, informe, reuniones, agenda, chat, dinero, producción).
6. `fuentes_verdad/generar_verdad.py`, después el catálogo y la foto diaria (`foto_diaria.py` copia `data/clientes/`).

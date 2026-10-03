# _ESTADO_hostinger · Hostinger en la app (3-oct-2026)

Encargo de Tomás: integrar Hostinger para avisar de servidores, webs, dominios y renovaciones. Estudio completo (con lo que da la API y por qué no hay token de solo lectura): `../56_INTEGRACIONES_HOSTINGER_Y_OTRAS.md`.

## Estado: construido y probado con datos inventados · **falta el token**
- `data/hostinger/hostinger.json` (3-oct 05:58): estado «sin conectar», con la instrucción para Tomás. No inventa nada.
- Todo en **solo lectura**: no se escribe nada en Hostinger.
- Ojo: Hostinger **no tiene tokens de solo lectura**; el token puede lo mismo que el usuario. Hay que crearlo con caducidad y guardarlo en el llavero.

## Qué hay
| Pieza | Fichero | Qué hace |
|---|---|---|
| Lector | `fuentes_hostinger/generar_hostinger.py` (paso `hostinger` de la tubería) | VPS (estado, CPU, memoria, disco, copias, acciones fallidas, malware), webs del hosting compartido (activa o suspendida), dominios (estado y caducidad) y suscripciones (renovación). `--ssl` añade el certificado de cada web. Empareja webs y dominios con su cliente por dominio. El VPS del gestor de contraseñas se marca como «interno» y solo se lee |
| Alertas | `fuentes_alertas/generar_alertas.py → de_hostinger()` | Las de la web de un cliente, a su persona de web; las de servidores, a Agus; renovaciones y dominios de RO, a Tomás |
| Prueba | `--simulado [--salida <fichero>]` | Datos inventados, nunca a `data/` salvo que se pida |

## Pendiente (solo Tomás)
1. hPanel → Perfil → API → crear token **con caducidad** y ejecutar `bash ~/RO_HERRAMIENTAS/hostinger/pegar.sh`.
2. Tras la primera pasada real, revisar el emparejamiento de webs y dominios con clientes.

# Notas para Google Cloud Run (alternativa, no elegida)

**2-oct-2026 · C5.** El código ya es portable: la misma imagen (`Dockerfile`) y las mismas variables que en Render. Si algún día se lleva a Google Cloud (región `europe-west1`, Bélgica), esto es lo que cambia. Nada está montado.

| Pieza en Render | En Google Cloud | Nota |
|---|---|---|
| Servicio web `ro-app` | **Cloud Run (servicio)**, `--command despliegue/entrada.sh --args web`, puerto en `$PORT` | Mínimo 1 instancia para no pagar el arranque en frío. Entrada solo por el balanceador con Cloudflare delante; `servir.py` sigue validando el sello de Access |
| `ro-ligera`, `ro-completa`, `ro-noche` | **Cloud Run Jobs** (`entrada.sh ligera\|completa\|noche`) + **Cloud Scheduler** con zona `Europe/Madrid` (aquí sí hay zona horaria) | 3 tareas de Scheduler: entran en las 3 gratis. Tiempo máximo por tarea: subirlo a 3 h en la completa |
| `ro-base` | **Cloud SQL para PostgreSQL 16**, máquina dedicada (las compartidas no tienen garantía y Google no las recomienda en producción) | Vuelta a un minuto concreto: 7 días (Enterprise). Conexión por el conector de Cloud SQL; `DATABASE_URL` igual |
| Grupo `ro-llaves` | **Secret Manager**, montado como variables de entorno en los Jobs | ⚠️ **La llave de GHL que rota NO va en Secret Manager:** cada rotación crearía una versión (unas 720 al mes, unos 43 $). Se queda en Postgres con bloqueo, igual que en Render (`llave_ghl.py`) |
| Copia nocturna | La misma (`copia_base.py` → R2) y, además, las copias automáticas de Cloud SQL | — |
| Errores y latidos | Los mismos (Better Stack por variables) | — |

**Pasos (Claude, unos 2-3 días):**
1. Proyecto `ro-app` con presupuesto y alerta de gasto.
2. Artifact Registry y `gcloud builds submit` desde la carpeta de `preparar_contexto.sh`.
3. Cloud SQL y la cuenta de servicio con el rol «Cloud SQL Client».
4. El servicio, los 3 Jobs y sus 3 Schedulers.
5. Los secretos.

Después, las mismas comprobaciones de `DESPLIEGUE.md` (pasos 3 a 8).

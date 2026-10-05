# App de RO · guía para agentes (Cursor, Claude)

App interna de Ranking Online: 21 puestos, permisos por persona, datos de clientes. Repositorio privado. **Sin datos**: `data/`, `local.db` y las llaves viven solo en el Mac de Tomás.

## Dónde está cada cosa

| Qué | Dónde |
|---|---|
| La app de hoy (Python + JS sin framework) | raíz: `servir.py`, `app.js`, `modulos/`, `estilos.css`, `componentes.js`, `reglas_permisos.json`… Cómo funciona: `LEEME.md` |
| La app nueva (Next + Nest + Postgres + shadcn) | `v2/` (ver `v2/README.md`) |
| El plan de la migración | `migracion/PLAN_MAESTRO.md` |
| El prompt de la noche (uno solo) | `migracion/PROMPT_NOCHE.md` (lo lanza `migracion/noche.sh`) |
| El cuaderno: qué está hecho y qué toca | `migracion/PROGRESO.md` |
| El detalle de cada paso | `migracion/PROMPTS_CURSOR.md` |
| Notas, preguntas y bloqueos | `migracion/NOTAS_NOCHE.md` (se crea en F1.1) |
| Arrancar todo / puertas | `migracion/servicios.sh`, `migracion/puerta.sh` |
| Inventario automático | `migracion/inventario/` (`python3 migracion/inventario.py`) |
| Redes de seguridad | `migracion/contrato.py`, `migracion/contrato_escritura.py`, `migracion/vectores_permisos.py`, `v2/tools/capturas/` |
| Proxy a la app de hoy (estrangulador) | `v2/apps/api/src/legado/` (`rutas-en-nest.ts` = lo que ya atiende Nest) |
| Despliegue de hoy | `despliegue/DESPLIEGUE.md` |
| Reglas para el agente | `.cursor/rules/` |

## Órdenes

```bash
# app de hoy
python3 servir.py --bind 127.0.0.1 --puerto 8770      # siempre 127.0.0.1
python3 pruebas_e0.py --puerto 8770

# todo junto, como esta noche (8770 hoy · 8771 legado sobre Postgres · 4000 Nest · 3000 Next)
bash migracion/servicios.sh arrancar
bash migracion/puerta.sh f3          # ¿la app nueva responde, escribe y se ve igual que la de hoy?

# solo v2
cd v2
pnpm install
pnpm db:up && pnpm db:deploy                           # Postgres en Docker (127.0.0.1:5432)
pnpm build && pnpm test && pnpm lint
```

## Reglas cortas

- Castellano. Frases cortas. Fechas absolutas.
- Lo que se ve y lo que responde la API no cambia: se comprueba con las redes de `migracion/`.
- Datos reales solo en `~/RO_MIGRACION/`, nunca en el repo ni en el chat. Nunca credenciales en ficheros.
- Servidores solo en `127.0.0.1` en local.

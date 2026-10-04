# Fallos de lógica pendientes · lista para la migración

**Regla de Tomás (4-oct-2026):** todo fallo de lógica que no quede arreglado hoy en la app actual se arregla **sí o sí** en la migración. Esta lista es la fuente. La alimenta el hilo «Feedback completo de la herramienta».

Cómo se usa:
- Un fallo arreglado en la app de hoy: estado `arreglado hoy` y el commit. Cursor solo comprueba que su prueba pasa en la app nueva.
- Un fallo abierto: Cursor lo arregla en el paso **F5.10** (ver `PROMPTS_CURSOR.md`), donde viva la ruta esa noche: en el módulo de Nest si ya se mudó, en `servir.py` si sigue por el proxy, y en la matriz (`reglas_permisos.json`) si es de permisos. Siempre con una prueba que falla antes y pasa después.
- Si hay una copia más nueva en `~/RO_MIGRACION/PENDIENTES_LOGICA.md`, manda esa.
- Sin datos reales: ni nombres de clientes, ni correos, ni importes. «Persona con puesto X» o «cliente de prueba».

Gravedad: **seguridad** (alguien ve o cambia lo que no debe) · **datos** (un número o estado sale mal) · **funcional** (algo no hace lo que debe) · **presentación**.
Orden de arreglo: seguridad → datos → funcional → presentación.

| Id | Gravedad | Dónde (pantalla, ruta o fichero) | Qué pasa | Qué debería pasar | Cómo se comprueba | Estado |
|---|---|---|---|---|---|---|
| L-0 | ejemplo | `GET /api/…` | (ejemplo, bórralo) | | | abierto |

# 644 · Contrato de eventos quincenales incorporado por ROOT

Fixtures liberados: `30_APP_PROTOTIPO/pruebas_metodo_cuentas.py` añade ID opaco a la reunión sintética legítima, sin cambiar sus aserciones; `30_APP_PROTOTIPO/probar_eventos_cadencia_644.py` extrae funciones de APP actual por AST y compara el baseline congelado640, sin importar lectores.

Después de la incorporación de640/641 a APP por ROOT: 13 pruebas644 PASS (conflictos globales/celebración/cliente, fuente objeto, fuentes admitidas, ID ausente/inválido, replay, NaN, controles y responsable histórico distinto del actual). 21 regresiones sintéticas Metodo/131/305 PASS; se omitieron explícitamente sólo los dos casos existentes que leen configuración real de14 cuentas, para conservar el alcance sin lecturas de fuentes reales. Ninguna aserción de esos casos se modificó ni se declara ejecutada.

No se acredita participación histórica de una persona mediante el rol declarado ni verificación externa de la reunión. El código640 cambia aceptación de eventos; no genera eventos nuevos. Sin base principal, fuentes JSON reales, runtime, proveedores, GitHub ni migración/v2. APP productiva fue modificada únicamente por ROOT, no por esta revisión.
